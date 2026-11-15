"""Uma regra local de temperatura, avaliada atomicamente a cada nova amostra."""
import json
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Rule(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool = Field(strict=True)
    sensor_id: str = Field(min_length=1,max_length=100)
    target_id: str = Field(min_length=1,max_length=100)
    on_at: float = Field(ge=-50,le=100,allow_inf_nan=False,strict=True)
    off_at: float = Field(ge=-50,le=100,allow_inf_nan=False,strict=True)

    @model_validator(mode='after')
    def thresholds(self):
        if self.off_at >= self.on_at:
            raise ValueError('O limite para desligar deve ser menor que o limite para ligar.')
        return self

def setup(api, connect, devices):
    with connect() as con:
        con.execute('CREATE TABLE IF NOT EXISTS automation_rule (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS automation_events (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL)')
        default = dict(enabled=False,sensor_id='sensor-temperatura-sala',target_id='tomada-sala',on_at=28.0,off_at=26.0)
        con.execute('INSERT OR IGNORE INTO automation_rule VALUES (1,?)',(json.dumps(default),))

    def validate(rule):
        sensor=devices.get(rule['sensor_id']); target=devices.get(rule['target_id'])
        if not sensor or sensor.get('kind')!='temperature_sensor':
            return 'sensor_invalido'
        if not target or not {'turn_on','turn_off'} <= set(target['capabilities']):
            return 'destino_sem_ligar_desligar'
        if sensor.get('source')=='home_assistant' or target.get('source')=='home_assistant':return 'regra_termica_apenas_simulada_use_rotinas_para_hardware'
        if not sensor['available'] or not target['available']:
            return 'dispositivo_indisponivel'
        return None

    @api.get('/api/v1/automation')
    def get_rule():
        with connect() as con:
            rule=json.loads(con.execute('SELECT payload FROM automation_rule WHERE id=1').fetchone()[0])
        return {**rule,'source':'simulation','issue':validate(rule)}

    @api.post('/api/v1/automation')
    def save_rule(body: Rule):
        rule=body.model_dump()
        # Desativar permanece possível mesmo após remoção de um dispositivo.
        issue=validate(rule)
        if rule['enabled'] and issue:
            raise HTTPException(422,issue)
        with connect() as con:
            con.execute('BEGIN IMMEDIATE')
            con.execute('UPDATE automation_rule SET payload=? WHERE id=1',(json.dumps(rule),))
            event={'timestamp':datetime.now(timezone.utc).isoformat(),'status':'configured','rule':rule,'source':'simulation'}
            con.execute('INSERT INTO automation_events(payload) VALUES (?)',(json.dumps(event),))
        return {**rule,'source':'simulation','issue':issue}

    @api.get('/api/v1/automation/events')
    def events(limit:int=Query(20,ge=1,le=100),offset:int=Query(0,ge=0)):
        with connect() as con:
            rows=con.execute('SELECT id,payload FROM automation_events ORDER BY id DESC LIMIT ? OFFSET ?',(limit,offset)).fetchall()
        return [{'id':r['id'],**json.loads(r['payload'])} for r in rows]

    def evaluate(con,sensor_id,value,reading_id,timestamp):
        rule=json.loads(con.execute('SELECT payload FROM automation_rule WHERE id=1').fetchone()[0])
        if not rule['enabled'] or rule['sensor_id']!=sensor_id:return
        state='on' if value>=rule['on_at'] else 'off' if value<=rule['off_at'] else None
        if state is None:return
        issue=validate(rule)
        current=con.execute('SELECT state,brightness FROM states WHERE id=?',(rule['target_id'],)).fetchone()
        if not issue and current and current['state']==state:return
        if not issue and not current:issue='estado_nao_encontrado'
        event=dict(timestamp=timestamp,source='simulation',trigger='automation',sensor_id=sensor_id,value=value,reading_id=reading_id,device_id=rule['target_id'],action='turn_'+state,rule=rule,status='failed' if issue else 'confirmed')
        if issue:event['error']=issue
        else:
            request_id='auto-'+uuid4().hex
            event.update(request_id=request_id,state=state)
            con.execute('UPDATE states SET state=? WHERE id=?',(state,rule['target_id']))
            if state=='on' and current['brightness']==0:
                con.execute('UPDATE states SET brightness=100 WHERE id=?',(rule['target_id'],))
            payload=json.dumps(dict(request_id=request_id,device_id=rule['target_id'],action='turn_'+state),sort_keys=True)
            con.execute('INSERT INTO commands VALUES (?,?,?,?)',(request_id,payload,200,json.dumps(event)))
        con.execute('INSERT INTO automation_events(payload) VALUES (?)',(json.dumps(event),))
    return evaluate
