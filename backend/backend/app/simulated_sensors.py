"""On-demand simulation, never physical telemetry. No background worker."""
import math,time,json
from datetime import datetime,timezone

def watts(device,catalog):
 base=catalog[device['kind']]['watts']
 return base*(device.get('brightness',100)/100 if device['kind']=='lights' else 1) if device['on'] else 0

def snapshot(project,connect,catalog,now=None):
 now=time.time() if now is None else now
 power=sum(watts(d,catalog) for d in project['devices'])
 with connect() as c:
  c.execute('CREATE TABLE IF NOT EXISTS maquette_sensor_samples (id INTEGER PRIMARY KEY AUTOINCREMENT,model TEXT NOT NULL,created REAL NOT NULL,payload TEXT NOT NULL)')
  c.execute('BEGIN IMMEDIATE')
  row=c.execute('SELECT created,payload FROM maquette_sensor_samples WHERE model=? ORDER BY id DESC LIMIT 1',(project['model'],)).fetchone()
  old=json.loads(row['payload']) if row else None
  elapsed=max(0,min(30,now-row['created'])) if row else 0
  energy=(old['energy_kwh'] if old else 0)+(old['power_w'] if old else 0)*elapsed/3600000
  rooms=[]
  for i,r in enumerate(project['rooms']):
   active=[d['kind'] for d in project['devices'] if d['room_id']==r['id'] and d['on']]
   present=project.get('sensor_presence',{}).get(r['id'],True)
   temp=round(25+i*.25+math.sin(now/90+i)*.4-(2 if 'ac' in active else 0)+(1 if 'shower' in active else 0),1)
   humidity=round(52+math.sin(now/100+i)*2+(12 if 'shower' in active else 0)-(5 if 'ac' in active else 0),1)
   rooms.append(dict(room_id=r['id'],temperature_c=temp,humidity_percent=humidity,presence=present,power_w=round(sum(watts(d,catalog) for d in project['devices'] if d['room_id']==r['id']),2),sensor_id='sim-'+r['id']))
  data=dict(source='simulation',physical=False,timestamp=datetime.fromtimestamp(now,timezone.utc).isoformat(),model=project['model'],revision=project['revision'],voltage_v=220,power_w=round(power,2),current_a=round(power/220,3),energy_kwh=energy,integration_seconds=elapsed,rooms=rooms,notice='Sensores fictícios. Atualização sob demanda; 220 V e fator de potência 1 são hipóteses. Energia integra a potência anterior por até 30 s entre amostras; pausas maiores não são contabilizadas.')
  # Save at most one sample every 4 seconds, but return current state immediately.
  if not row or now-row['created']>=4:
   c.execute('INSERT INTO maquette_sensor_samples(model,created,payload) VALUES (?,?,?)',(project['model'],now,json.dumps(data)))
   c.execute('DELETE FROM maquette_sensor_samples WHERE model=? AND id NOT IN (SELECT id FROM maquette_sensor_samples WHERE model=? ORDER BY id DESC LIMIT 600)',(project['model'],project['model']))
 return data
