"""Portable Aether JSON format. No images, code, URLs or binary assets."""
import math,re
from fastapi import HTTPException
SCHEMA='aether-floorplan-1'
def invalid(msg):raise HTTPException(422,msg)
def number(v,lo,hi):
 if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:invalid('Medida ou valor fora dos limites.')
 return v

def validate_document(doc,catalog):
 if not isinstance(doc,dict) or set(doc)!={'schema_version','project'} or doc['schema_version']!=SCHEMA:invalid('Use um JSON de planta Aether no formato aether-floorplan-1. Imagens, PDF e DWG não são convertidos automaticamente.')
 p=doc['project']
 if not isinstance(p,dict) or (set(p)-{'model','rooms','devices','tariff','goal','sensor_presence'} or not {'model','rooms','devices','tariff','goal'}<=set(p)):invalid('Campos do projeto inválidos.')
 if not isinstance(p['model'],str) or p['model'] not in {'house','apartment'}:invalid('Modelo deve ser house ou apartment.')
 rs=p['rooms'];ds=p['devices']
 if not isinstance(rs,list) or not 1<=len(rs)<=20 or not isinstance(ds,list) or len(ds)>100:invalid('Use 1–20 cômodos e até 100 aparelhos.')
 ids=set();names=set()
 for r in rs:
  if not isinstance(r,dict) or set(r)!={'id','name','x','z','w','d'}:invalid('Campos de cômodo inválidos.')
  if not isinstance(r['id'],str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',r['id']) or r['id'] in ids:invalid('IDs de cômodo devem ser únicos e alfanuméricos.')
  ids.add(r['id'])
  if not isinstance(r['name'],str) or not 1<=len(r['name'].strip())<=50 or r['name'].strip().casefold() in names:invalid('Nomes de cômodo devem ser únicos e ter até 50 caracteres.')
  r['name']=r['name'].strip();names.add(r['name'].casefold())
  for k in ['x','z']:number(r[k],0,200)
  for k in ['w','d']:number(r[k],2,12)
 for i,a in enumerate(rs):
  for b in rs[i+1:]:
   if a['x']<b['x']+b['w']-.001 and a['x']+a['w']>b['x']+.001 and a['z']<b['z']+b['d']-.001 and a['z']+a['d']>b['z']+.001:invalid('Os cômodos não podem se sobrepor.')
 seen=set();counts={r:0 for r in ids}
 for d in ds:
  if not isinstance(d,dict) or (set(d)-{'id','kind','room_id','on','hours','rgb_enabled','color','brightness','u','v'} or not {'id','kind','room_id','on','hours'}<=set(d)):invalid('Campos de aparelho inválidos.')
  if not isinstance(d['id'],str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',d['id']) or d['id'] in seen:invalid('IDs de aparelho devem ser únicos.')
  seen.add(d['id'])
  if not isinstance(d['kind'],str) or not isinstance(d['room_id'],str) or d['kind'] not in catalog or d['room_id'] not in ids or type(d['on']) is not bool:invalid('Aparelho, cômodo ou estado inválido.')
  counts[d['room_id']]+=1
  if counts[d['room_id']]>6:invalid('Limite de seis aparelhos por cômodo.')
  number(d['hours'],0,24)
  for k in ['u','v']:
   if k in d:number(d[k],.15,.85)
  if any(k in d for k in ['rgb_enabled','brightness','color']) and d['kind']!='lights':invalid('RGB e brilho são exclusivos das luzes.')
  if 'rgb_enabled' in d and type(d['rgb_enabled']) is not bool:invalid('Capacidade RGB inválida.')
  if 'brightness' in d:number(d['brightness'],0,100)
  if 'color' in d and (not isinstance(d['color'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',d['color'])):invalid('Cor inválida.')
 presence=p.get('sensor_presence',{})
 if not isinstance(presence,dict) or any(k not in ids or type(v) is not bool for k,v in presence.items()):invalid('Configuração de sensores inválida.')
 number(p['tariff'],.01,10);number(p['goal'],1,80)
 return p

def export_document(project):return {'schema_version':SCHEMA,'project':{**{k:project[k] for k in ['model','rooms','devices','tariff','goal']},**({'sensor_presence':project['sensor_presence']} if 'sensor_presence' in project else {})}}
