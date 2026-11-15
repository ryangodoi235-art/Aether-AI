"""Catalog, routines, local scheduler, physical bridge and measured energy."""
import json,os,re,threading,hashlib,math
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from uuid import uuid4
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import HTTPException,Query
from pydantic import BaseModel,Field,ConfigDict
from . import hardware
from .voice import setup as setup_voice

class Catalog(BaseModel):
    model_config=ConfigDict(extra='forbid')
    revision:str
    house:dict
class Run(BaseModel):
    request_id:str=Field(default_factory=lambda:uuid4().hex,min_length=1,max_length=100)
class Routine(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(pattern=r'^[a-z0-9-]{1,60}$')
    name:str=Field(min_length=1,max_length=80)
    actions:list[dict]=Field(min_length=1,max_length=50)
    enabled:bool=False
    time:str|None=Field(default=None,pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]$')
    timezone:str='America/Sao_Paulo'

class EnergySample(BaseModel):
    model_config=ConfigDict(extra='forbid')
    request_id:str=Field(default_factory=lambda:uuid4().hex,min_length=1,max_length=100)
    meter_id:str=Field(min_length=1,max_length=100)
    timestamp:datetime
    cumulative_kwh:float=Field(ge=0,allow_inf_nan=False)


def validate_catalog(h):
    if set(h)-{'id','name','rooms','devices'}:raise HTTPException(422,'Campos extras no cadastro.')
    if not isinstance(h.get('name'),str) or not 1<=len(h['name'])<=100:raise HTTPException(422,'Nome da casa inválido.')
    rooms=h.get('rooms');ds=h.get('devices')
    if not isinstance(rooms,list) or not isinstance(ds,list) or not rooms or len(rooms)>500 or len(ds)>5000:raise HTTPException(422,'Informe até500 cômodos e5000 dispositivos.')
    for group in [rooms,ds]:
        if any(not isinstance(d,dict) or not re.fullmatch('[a-z0-9-]{1,100}',str(d.get('id',''))) or not isinstance(d.get('name'),str) or not 1<=len(d['name'])<=100 for d in group):raise HTTPException(422,'Use IDs únicos em minúsculas, números/hífen e nomes de1–100 caracteres.')
        if len({d['id'] for d in group})!=len(group):raise HTTPException(422,'IDs duplicados.')
    room_ids={r['id'] for r in rooms}
    for d in ds:
        if d.get('room_id') not in room_ids or not isinstance(d.get('available'),bool):raise HTTPException(422,'Cômodo/disponibilidade inválidos.')
        kind=d.get('kind','light' if str(d['name']).lower().startswith(('luz','lâmpada')) else 'switch')
        if kind not in {'light','switch','temperature_sensor','energy_sensor'}:raise HTTPException(422,'Tipo desconhecido.')
        caps=d.get('capabilities',[])
        expected={'temperature_sensor':{'read_temperature'},'energy_sensor':{'read_energy'}}.get(kind)
        if expected is not None:
            if set(caps)!=expected:raise HTTPException(422,'Capacidades incompatíveis com sensor.')
        elif d.get('initial_state') not in {'on','off'} or not set(caps)<={'turn_on','turn_off','set_brightness','set_color'} or not caps:
            raise HTTPException(422,'Estado/capacidades inválidos.')
        if kind=='switch' and set(caps)-{'turn_on','turn_off'}:raise HTTPException(422,'Tomada suporta ligar/desligar.')
        source=d.get('source','simulation')
        if source not in {'simulation','home_assistant'}:raise HTTPException(422,'Origem desconhecida.')
        if source=='home_assistant':
            domain='sensor' if expected else 'light' if kind=='light' else 'switch'
            if not re.fullmatch(domain+r'\.[a-z0-9_]+',str(d.get('entity_id',''))):raise HTTPException(422,'entity_id incompatível com tipo.')
    return h


def setup(api,connect,config,devices,config_file,list_devices,send,root,lock):
    stop=threading.Event();worker=None
    validate_catalog(config)
    from .multi_command import make_multi_handler
    multi_handler=make_multi_handler(connect,config,devices,send,lock)
    with connect() as c:
        c.execute('CREATE TABLE IF NOT EXISTS routines (id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS routine_runs (id TEXT PRIMARY KEY,routine_id TEXT NOT NULL,result TEXT NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS energy_samples (request_id TEXT PRIMARY KEY,meter_id TEXT NOT NULL,timestamp TEXT NOT NULL,cumulative_kwh REAL NOT NULL,source TEXT NOT NULL,UNIQUE(meter_id,timestamp))')
    def revision():return hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    @api.get('/api/v1/catalog')
    def catalog():return {'revision':revision(),'house':config}
    @api.put('/api/v1/catalog')
    def save_catalog(body:Catalog):
        h=validate_catalog(body.house)
        with lock:
            if body.revision!=revision():raise HTTPException(409,'Cadastro mudou; atualize antes de salvar.')
            if h.get('id')!=config.get('id'):raise HTTPException(422,'Mantenha o ID da casa.')
            old={d['id']:d for d in config['devices']};new={d['id']:d for d in h['devices']}
            # IDs are durable references: deactivate devices instead of deleting/reassigning them.
            if not set(old)<=set(new):raise HTTPException(422,'Desative dispositivos em vez de remover IDs com histórico.')
            for ident,d in old.items():
                n=new[ident]
                if (d.get('kind'),d.get('source','simulation'),d.get('entity_id'))!=(n.get('kind'),n.get('source','simulation'),n.get('entity_id')):
                    raise HTTPException(422,'Tipo/origem/entidade de um ID existente são fixos; crie outro dispositivo.')
            backup=config_file.with_name(config_file.name+'.before-edit')
            backup.write_bytes(config_file.read_bytes())
            temp=config_file.with_name(config_file.name+'.tmp')
            temp.write_text(json.dumps(h,ensure_ascii=False,indent=2),encoding='utf-8')
            with connect() as c:
                for d in h['devices']:
                    if d.get('kind') not in {'temperature_sensor','energy_sensor'}:c.execute('INSERT OR IGNORE INTO states(id,state) VALUES (?,?)',(d['id'],d['initial_state']))
            os.replace(temp,config_file);config.clear();config.update(h);devices.clear();devices.update(new)
        return catalog()

    def validate_actions(actions):
        for action in actions:
            d=devices.get(action.get('device_id'))
            if set(action)-{'device_id','action','brightness','color'} or not d or not d['available'] or action.get('action') not in d['capabilities']:raise HTTPException(422,'Ação/dispositivo inválido ou indisponível na rotina.')
            a=action['action'];b=action.get('brightness');rgb=action.get('color')
            if a not in {'turn_on','turn_off','set_brightness','set_color'}:raise HTTPException(422,'Ação não suportada pela rotina.')
            if (a=='set_brightness')!=(b is not None) or b is not None and (type(b)!=int or not 0<=b<=100):raise HTTPException(422,'Brilho inválido.')
            if (a=='set_color')!=(rgb is not None) or rgb is not None and (not isinstance(rgb,list) or len(rgb)!=3 or any(type(x)!=int or not 0<=x<=255 for x in rgb)):raise HTTPException(422,'Cor inválida.')
    @api.get('/api/v1/routines')
    def routines():
        with connect() as c:return [json.loads(r[0]) for r in c.execute('SELECT payload FROM routines ORDER BY id')]
    @api.put('/api/v1/routines/{ident}')
    def save_routine(ident:str,body:Routine):
        if ident!=body.id:raise HTTPException(422,'IDs divergentes.')
        validate_actions(body.actions)
        try:ZoneInfo(body.timezone)
        except Exception:raise HTTPException(422,'Fuso inválido ou tzdata ausente. Instale requirements-features.txt.')
        with connect() as c:c.execute('INSERT OR REPLACE INTO routines VALUES (?,?)',(ident,body.model_dump_json()))
        return body.model_dump()
    @api.delete('/api/v1/routines/{ident}')
    def remove_routine(ident:str):
        with connect() as c:c.execute('DELETE FROM routines WHERE id=?',(ident,))
        return {'status':'removed'}
    def run(ident,rid):
        with lock:
            with connect() as c:
                old=c.execute('SELECT routine_id,result FROM routine_runs WHERE id=?',(rid,)).fetchone()
                if old:
                    if old['routine_id']!=ident:raise HTTPException(409,'ID de execução já utilizado.')
                    return json.loads(old['result'])
                row=c.execute('SELECT payload FROM routines WHERE id=?',(ident,)).fetchone()
                if not row:raise HTTPException(404,'Rotina não encontrada.')
                routine=json.loads(row[0]);validate_actions(routine['actions'])
                result={'id':rid,'routine_id':ident,'name':routine['name'],'status':'running','timestamp':datetime.now(timezone.utc).isoformat(),'steps':[]}
                c.execute('INSERT INTO routine_runs VALUES (?,?,?)',(rid,ident,json.dumps(result)))
            for i,action in enumerate(routine['actions']):
                try:
                    cmd=send({**action,'request_id':'routine:'+hashlib.sha256((rid+':'+str(i)).encode()).hexdigest()})
                    result['steps'].append(cmd)
                except HTTPException as exc:
                    result['steps'].append({'status':'failed','detail':exc.detail});result['status']='partial' if i else 'failed';break
            else:result['status']='confirmed'
            with connect() as c:c.execute('UPDATE routine_runs SET result=? WHERE id=?',(json.dumps(result),rid))
            return result
    @api.post('/api/v1/routines/{ident}/run')
    def run_manual(ident:str,body:Run):return run(ident,'manual:'+body.request_id)
    @api.get('/api/v1/routines/runs/history')
    def runs(limit:int=Query(20,ge=1,le=100)):
        with connect() as c:return [json.loads(r[0]) for r in c.execute('SELECT result FROM routine_runs ORDER BY rowid DESC LIMIT ?',(limit,))]
    def tick(now=None):
        now=now or datetime.now(timezone.utc)
        for r in routines():
            if not r['enabled'] or not r['time']:continue
            local=now.astimezone(ZoneInfo(r['timezone']))
            if local.strftime('%H:%M')!=r['time']:continue
            try:run(r['id'],'schedule:'+r['id']+':'+local.strftime('%Y-%m-%d'))
            except Exception:pass # Other routines remain available; failed steps are in history.
    api.state.scheduler_tick=tick
    def loop():
        while not stop.wait(10):tick()
    @asynccontextmanager
    async def lifespan(app):
        nonlocal worker
        stop.clear();worker=threading.Thread(target=loop,daemon=True);worker.start()
        try:yield
        finally:
            stop.set()
            if worker:worker.join(timeout=6)
    api.router.lifespan_context=lifespan
    @api.get('/api/v1/hardware/status')
    def hardware_status():
        try:hardware.settings();hardware.request('/api/');return {'status':'ready','message':'Home Assistant local disponível; confira cada entidade.'}
        except HTTPException as exc:return {'status':'unavailable','message':exc.detail}

    def add_energy(body,source):
        if body.timestamp.tzinfo is None:raise HTTPException(422,'Informe timestamp com fuso.')
        t=body.timestamp.astimezone(timezone.utc)
        if t>datetime.now(timezone.utc)+timedelta(minutes=5):raise HTTPException(422,'Leitura no futuro.')
        timestamp=t.isoformat()
        with connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM energy_samples WHERE request_id=?',(body.request_id,)).fetchone()
            record=dict(request_id=body.request_id,meter_id=body.meter_id,timestamp=timestamp,cumulative_kwh=body.cumulative_kwh,source=source)
            if row:
                if dict(row)!=record:raise HTTPException(409,'ID usado com outra amostra.')
                return dict(row)
            previous=c.execute('SELECT cumulative_kwh FROM energy_samples WHERE meter_id=? AND timestamp<? ORDER BY timestamp DESC LIMIT 1',(body.meter_id,timestamp)).fetchone()
            following=c.execute('SELECT cumulative_kwh FROM energy_samples WHERE meter_id=? AND timestamp>? ORDER BY timestamp LIMIT 1',(body.meter_id,timestamp)).fetchone()
            if previous and previous[0]>body.cumulative_kwh or following and following[0]<body.cumulative_kwh:raise HTTPException(422,'Medidor cumulativo diminuiu. Use outro ID para novo medidor/reset.')
            try:c.execute('INSERT INTO energy_samples VALUES (?,?,?,?,?)',tuple(record.values()))
            except Exception:raise HTTPException(409,'Já existe leitura para esse medidor/horário.')
        return record
    @api.post('/api/v1/energy/readings',status_code=201)
    def manual_energy(body:EnergySample):return add_energy(body,'manual_unverified')
    @api.post('/api/v1/hardware/sync/{ident}')
    def sync(ident:str):
        d=devices.get(ident)
        if not d or d.get('source')!='home_assistant':raise HTTPException(404,'Dispositivo físico não encontrado.')
        item=hardware.read(d)
        if not item['available']:raise HTTPException(503,'Dispositivo físico indisponível.')
        if d.get('kind')=='temperature_sensor':
            if item.get('unit') not in {'°C','C'}:raise HTTPException(422,'Temperatura precisa estar em °C.')
            with connect() as c:
                same=c.execute('SELECT id FROM temperature_readings WHERE device_id=? AND timestamp=?',(ident,item['observed_at'])).fetchone()
                if not same:c.execute('INSERT INTO temperature_readings(device_id,value,timestamp) VALUES (?,?,?)',(ident,item['value'],item['observed_at']))
        elif d.get('kind')=='energy_sensor':
            if item.get('unit')!='kWh':raise HTTPException(422,'Use sensor cumulativo de energia em kWh, não potência em W.')
            add_energy(EnergySample(request_id='ha:'+hashlib.sha256((ident+str(item['observed_at'])).encode()).hexdigest(),meter_id=ident,timestamp=item['observed_at'],cumulative_kwh=item['value']),'home_assistant')
        return item
    @api.get('/api/v1/energy/readings')
    def energy_readings(meter_id:str,limit:int=Query(100,ge=1,le=500)):
        with connect() as c:return [dict(r) for r in c.execute('SELECT * FROM energy_samples WHERE meter_id=? ORDER BY timestamp DESC LIMIT ?',(meter_id,limit))]
    @api.get('/api/v1/energy/summary')
    def energy_summary(meter_id:str):
        rows=list(reversed(energy_readings(meter_id,100)))
        if len(rows)<3:return {'status':'insufficient_data','message':'Registre ao menos3 amostras cumulativas em horários diferentes.','meter_id':meter_id}
        first,last=rows[0],rows[-1];hours=(datetime.fromisoformat(last['timestamp'])-datetime.fromisoformat(first['timestamp'])).total_seconds()/3600
        if hours<=0:raise HTTPException(422,'Intervalo inválido.')
        amount=last['cumulative_kwh']-first['cumulative_kwh']
        recent=(datetime.now(timezone.utc)-datetime.fromisoformat(last['timestamp'])).total_seconds()<=900
        return {'status':'estimated','meter_id':meter_id,'observed_consumption_kwh':round(amount,6),'window_start':first['timestamp'],'window_end':last['timestamp'],
            'next_hour_estimate_kwh':round(amount/hours,6),'method':'mean_rate_baseline_v1','samples':len(rows),'fresh_within_15_minutes':recent,'sources':sorted({r['source'] for r in rows}),
            'message':'Consumo do intervalo e extrapolação de uma hora pela taxa média. Sem validação preditiva/intervalo de confiança; dados manuais não verificados. Não é a previsão histórica UCI nem medição instantânea.'}
    setup_voice(api,root)
    def text_route(text,rid):
        multi_result=multi_handler(text,rid)
        if multi_result is not None:return multi_result
        phrase=text.lower().strip(' .?!')
        m=re.fullmatch(r'(?:qual (?:e )?o )?consumo (?:medido|real) (?:do medidor |do )?([a-z0-9-]+)',phrase)
        if m:
            data=energy_summary(m.group(1));return {'status':'answered','message':json.dumps(data,ensure_ascii=False)}
        found=[r for r in routines() if phrase in {'execute '+r['name'].lower(),'executar '+r['name'].lower(),r['name'].lower()}]
        if len(found)!=1:return None
        result=run(found[0]['id'],'chat:'+rid)
        return {'status':'confirmed' if result['status']=='confirmed' else 'failed','message':'Rotina '+result['name']+': '+result['status']+'. Consulte o histórico de etapas.','routine':result,'actions_executed':any(s.get('status')=='confirmed' for s in result['steps'])}
    return {'text':text_route,'send':send,'rooms':lambda:config['rooms']}
