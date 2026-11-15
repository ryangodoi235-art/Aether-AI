"""Fictional appliance inventory; never sends hardware commands."""
import json,re,unicodedata
from fastapi import HTTPException
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal

CATALOG={
 'lights':dict(name='Lâmpada LED',room=1,watts=9,hours=6),
 'tv':dict(name='Televisão',room=0,watts=100,hours=4),
 'fridge':dict(name='Geladeira',room=2,watts=150,hours=8),
 'stove':dict(name='Fogão elétrico',room=2,watts=2000,hours=1),
 'microwave':dict(name='Micro-ondas',room=2,watts=1200,hours=.2),
 'washer':dict(name='Máquina de lavar',room=2,watts=500,hours=.5),
 'ac':dict(name='Ar-condicionado',room=1,watts=1000,hours=4),
 'fan':dict(name='Ventilador',room=0,watts=60,hours=6),
 'shower':dict(name='Chuveiro elétrico',room=3,watts=5500,hours=.5),
}
ROOMS=['Sala','Quarto','Cozinha','Banheiro']
class Device(BaseModel):
 model_config=ConfigDict(extra='forbid')
 kind:Literal['lights','tv','fridge','stove','microwave','washer','ac','fan','shower']
 room:int=Field(strict=True,ge=0,le=3)
 on:bool=Field(strict=True)
 hours:float=Field(ge=0,le=24,allow_inf_nan=False)
class Scene(BaseModel):
 model_config=ConfigDict(extra='forbid')
 revision:int=Field(strict=True,ge=0)
 devices:list[Device]=Field(max_length=36)
class Command(BaseModel):
 model_config=ConfigDict(extra='forbid')
 text:str=Field(min_length=1,max_length=300)
def norm(t):return ''.join(c for c in unicodedata.normalize('NFD',t.lower()) if unicodedata.category(c)!='Mn').strip(' .!?')
def default_devices():return [dict(kind=k,room=r,on=True,hours=h) for k,r,h in [('tv',0,4),('lights',1,6),('lights',2,5),('shower',3,.5)]]
def setup(api,connect):
 with connect() as c:
  c.execute('CREATE TABLE IF NOT EXISTS energy_coach_scene (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, payload TEXT NOT NULL)')
  c.execute('INSERT OR IGNORE INTO energy_coach_scene VALUES (1,0,?)',(json.dumps(default_devices()),))
 def read(c):
  row=c.execute('SELECT revision,payload FROM energy_coach_scene WHERE id=1').fetchone()
  return dict(revision=row[0],devices=json.loads(row[1]),catalog=CATALOG,rooms=ROOMS,source='fictional_demo')
 def write(c,items):
  c.execute('UPDATE energy_coach_scene SET revision=revision+1,payload=? WHERE id=1',(json.dumps(items),))
  return read(c)
 @api.get('/api/v1/energy-coach/scene')
 def get_scene():
  with connect() as c:return read(c)
 @api.put('/api/v1/energy-coach/scene')
 def put_scene(body:Scene):
  items=[d.model_dump() for d in body.devices]
  if len({(d['kind'],d['room']) for d in items})!=len(items):raise HTTPException(422,'Já existe esse tipo de aparelho no cômodo.')
  with connect() as c:
   c.execute('BEGIN IMMEDIATE')
   if read(c)['revision']!=body.revision:raise HTTPException(409,'A maquete mudou. Atualize antes de tentar novamente.')
   return write(c,items)
 def add_profile(kinds):
  with connect() as c:
   c.execute('BEGIN IMMEDIATE');s=read(c);items=s['devices'];changed=False
   for k in kinds:
    if k in CATALOG and not any(d['kind']==k for d in items):
     v=CATALOG[k];items.append(dict(kind=k,room=v['room'],on=False,hours=v['hours']));changed=True
   if changed:write(c,items)
 @api.post('/api/v1/energy-coach/scene/command')
 def command(body:Command):
  t=norm(body.text)
  if not re.search(r'\bna maquete\b',t):raise HTTPException(422,'Inclua “na maquete” para operar o exemplo fictício.')
  t=re.sub(r'\bna maquete\b','',t).strip(' ,')
  m=re.fullmatch(r'(ligue|liga|ligar|desligue|desliga|desligar|adicione|adicionar|coloque) (?:a |o |um |uma )?(.+)',t)
  if not m:return dict(answer='Na maquete, use por exemplo: “Adicione uma geladeira na maquete” ou “Ligue a geladeira na maquete”.',source='fictional_demo',actions_executed=False,scene=get_scene())
  verb,target=m.groups();room=None
  for i,r in enumerate(ROOMS):
   match=re.search(r' (?:da|do|na|no) '+norm(r)+r'$',target)
   if match:room=i;target=target[:match.start()];break
  aliases={'luz':'lights','lampada':'lights','lampada led':'lights','televisao':'tv','tv':'tv','geladeira':'fridge','fogao':'stove','fogao eletrico':'stove','micro-ondas':'microwave','microondas':'microwave','maquina de lavar':'washer','ar-condicionado':'ac','ar condicionado':'ac','ventilador':'fan','chuveiro':'shower','chuveiro eletrico':'shower'}
  k=aliases.get(target)
  if not k:return dict(answer='Não identifiquei esse aparelho. Escolha um dos tipos disponíveis na maquete.',source='fictional_demo',actions_executed=False,scene=get_scene())
  with connect() as c:
   c.execute('BEGIN IMMEDIATE');s=read(c);items=s['devices'];matches=[d for d in items if d['kind']==k and (room is None or d['room']==room)]
   if verb in {'adicione','adicionar','coloque'}:
    room=CATALOG[k]['room'] if room is None else room
    if any(d['kind']==k and d['room']==room for d in items):answer='Esse aparelho já está nesse cômodo da maquete.'
    else:items.append(dict(kind=k,room=room,on=False,hours=CATALOG[k]['hours']));s=write(c,items);answer=f"Adicionei {CATALOG[k]['name']} em {ROOMS[room]} na maquete, inicialmente desligado."
   elif len(matches)!=1:answer='Informe o cômodo do aparelho na maquete.' if matches else 'Esse aparelho ainda não está na maquete. Adicione-o primeiro.'
   else:
    matches[0]['on']=verb in {'ligue','liga','ligar'};s=write(c,items);answer=f"Na maquete, {CATALOG[k]['name']} em {ROOMS[matches[0]['room']]} está {'ligado' if matches[0]['on'] else 'desligado'}."
   return dict(answer=answer,source='fictional_demo',actions_executed=False,scene=s)
 return add_profile
