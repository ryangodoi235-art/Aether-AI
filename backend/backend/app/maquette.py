"""Persistent, explicitly simulated residence shared by chat and WebGL UI."""
import json,re,unicodedata,hashlib,threading,time
from uuid import uuid4
from pathlib import Path
from datetime import datetime,timezone
from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field,ConfigDict
CATALOG={'fridge':{'name':'Geladeira','watts':150,'hours':8},'tv':{'name':'Televisão','watts':120,'hours':4},'ac':{'name':'Ar-condicionado','watts':1000,'hours':6},'shower':{'name':'Chuveiro elétrico','watts':5500,'hours':.4},'stove':{'name':'Fogão elétrico','watts':1800,'hours':1},'microwave':{'name':'Micro-ondas','watts':1200,'hours':.2},'washer':{'name':'Máquina de lavar','watts':500,'hours':1},'lights':{'name':'Luz','watts':10,'hours':5},'fan':{'name':'Ventilador','watts':65,'hours':6}}
ALIASES={'fridge':['geladeira'],'tv':['televisao','tv'],'ac':['ar condicionado','ar-condicionado'],'shower':['chuveiro eletrico','chuveiro'],'stove':['fogao eletrico','fogao'],'microwave':['micro ondas','micro-ondas'],'washer':['maquina de lavar','lavadora'],'lights':['lampada','luz'],'fan':['ventilador']}
def norm(s):return ' '.join(''.join(c for c in unicodedata.normalize('NFD',s.lower()) if unicodedata.category(c)!='Mn').strip(' .?!').split())
class Action(BaseModel):
 model_config=ConfigDict(extra='forbid')
 request_id:str=Field(default_factory=lambda:uuid4().hex,min_length=1,max_length=100)
 project:str
 revision:int=Field(ge=0)
 op:str
 data:dict=Field(default_factory=dict)
def template(kind):
 rooms=[dict(id='sala',name='Sala',x=0,z=0,w=5 if kind=='house' else 4,d=4),dict(id='quarto',name='Quarto',x=5 if kind=='house' else 4,z=0,w=4,d=4),dict(id='cozinha',name='Cozinha',x=0,z=4,w=5 if kind=='house' else 4,d=3),dict(id='banheiro',name='Banheiro',x=5 if kind=='house' else 4,z=4,w=4,d=3)]
 devices=[]
 for k,r in [('tv','sala'),('ac','quarto'),('fridge','cozinha'),('stove','cozinha'),('shower','banheiro'),('lights','sala')]:devices.append(dict(id=uuid4().hex,kind=k,room_id=r,on=False,hours=CATALOG[k]['hours']))
 return dict(model=kind,rooms=rooms,devices=devices,tariff=1.0,goal=20,revision=0)
def setup(api,connect,root):
 from .simulated_sensors import watts,snapshot
 lock=threading.RLock()
 with connect() as c:
  c.execute('CREATE TABLE IF NOT EXISTS maquette_projects (id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS maquette_settings (id INTEGER PRIMARY KEY,active TEXT NOT NULL)')
  c.execute("INSERT OR IGNORE INTO maquette_settings VALUES (1,'house')")
  c.execute('CREATE TABLE IF NOT EXISTS maquette_requests (id TEXT PRIMARY KEY,payload TEXT NOT NULL,result TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS maquette_import_backups (id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT NOT NULL,model TEXT NOT NULL,payload TEXT NOT NULL)')
  c.execute('CREATE TABLE IF NOT EXISTS maquette_pending (session TEXT PRIMARY KEY,payload TEXT NOT NULL,created REAL NOT NULL)')
  for k in ['house','apartment']:c.execute('INSERT OR IGNORE INTO maquette_projects VALUES (?,?)',(k,json.dumps(template(k))))
 def load(c):
  active=c.execute('SELECT active FROM maquette_settings WHERE id=1').fetchone()[0]
  s=json.loads(c.execute('SELECT payload FROM maquette_projects WHERE id=?',(active,)).fetchone()[0])
  for d in s['devices']:
   if d['kind']=='lights':
    d.setdefault('rgb_enabled',False);d.setdefault('color','#ffffff');d.setdefault('brightness',100)
  s.setdefault('sensor_presence',{})
  return s
 def public(s):
  total=sum(watts(d,CATALOG)/1000*d['hours']*30 for d in s['devices']);base=sum(CATALOG[d['kind']]['watts']/1000*d['hours']*30 for d in s['devices'])
  return {**s,'catalog':CATALOG,'source':'simulation','monthly_kwh':round(total,3),'monthly_cost':round(total*s['tariff'],2),'baseline_cost':round(base*s['tariff'],2),'goal_cost':round(base*s['tariff']*(1-s['goal']/100),2)}
 @api.get('/api/v1/maquette')
 def get_scene():
  with connect() as c:return public(load(c))
 @api.get('/api/v1/maquette/sensors')
 def sensors():
  with connect() as c:s=load(c)
  return snapshot(s,connect,CATALOG)
 @api.get('/maquete',include_in_schema=False)
 def page():return FileResponse(Path(root)/'frontend/maquette.html',headers={'Cache-Control':'no-store'})
 @api.get('/maquette-assets/{name}',include_in_schema=False)
 def assets(name:str):
  if name not in {'app.js','style.css','LICENSE-blueprint.txt','LICENSE-three.txt'}:raise HTTPException(404)
  return FileResponse(Path(root)/'frontend/maquette'/name,headers={'Cache-Control':'no-store'})
 def number(value,lo,hi):
  if isinstance(value,bool) or not isinstance(value,(int,float)) or not lo<=value<=hi:raise HTTPException(422,'Valor fora do intervalo.')
  return value
 def add(s,k,r):
  if len(s['devices'])>=100:raise HTTPException(422,'Limite de 100 aparelhos.')
  if sum(d['room_id']==r for d in s['devices'])>=6:raise HTTPException(422,'Limite de seis aparelhos por cômodo para preservar a visualização.')
  d=dict(id=uuid4().hex,kind=k,room_id=r,on=False,hours=CATALOG[k]['hours']);s['devices'].append(d);return d
 def mutate(s,op,data):
  if op=='add_device':
   k=data.get('kind');r=data.get('room_id')
   if k not in CATALOG or r not in {r['id'] for r in s['rooms']}:raise HTTPException(422,'Aparelho ou cômodo inválido.')
   d=add(s,k,r)
   if data.get('rgb_enabled') is not None:
    if k!='lights' or type(data['rgb_enabled']) is not bool:raise HTTPException(422,'RGB só é configurável em luzes.')
    d.update(rgb_enabled=data['rgb_enabled'],color='#ffffff',brightness=100)
  elif op in {'device','remove_device'}:
   d=next((d for d in s['devices'] if d['id']==data.get('id')),None)
   if not d:raise HTTPException(404,'Aparelho não encontrado.')
   if op=='remove_device':s['devices'].remove(d)
   else:
    if 'on' in data:
     if type(data['on']) is not bool:raise HTTPException(422,'Estado inválido.')
     d['on']=data['on']
    if 'hours' in data:d['hours']=number(data['hours'],0,24)
    if any(k in data for k in ['color','rgb_enabled','brightness']) and d['kind']!='lights':raise HTTPException(422,'Cor e brilho exigem uma luz compatível.')
    if 'rgb_enabled' in data:
     if type(data['rgb_enabled']) is not bool:raise HTTPException(422,'Capacidade RGB inválida.')
     d['rgb_enabled']=data['rgb_enabled']
    if 'brightness' in data:d['brightness']=number(data['brightness'],0,100)
    if 'color' in data:
     if not d.get('rgb_enabled'):raise HTTPException(422,'Esta luz não tem capacidade RGB.')
     if not isinstance(data['color'],str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',data['color']):raise HTTPException(422,'Cor hexadecimal inválida.')
     d['color']=data['color'].lower()
    for k in ['u','v']:
     if k in data:d[k]=number(data[k],.15,.85)
  elif op=='remove_room':
   r=next((r for r in s['rooms'] if r['id']==data.get('id')),None)
   if not r:raise HTTPException(404,'Cômodo não encontrado.')
   if len(s['rooms'])==1:raise HTTPException(422,'Mantenha ao menos um cômodo na maquete.')
   contained=[d for d in s['devices'] if d['room_id']==r['id']]
   if contained and data.get('confirm') is not True:raise HTTPException(409,'Confirme a remoção do cômodo e de seus aparelhos.')
   s.setdefault('sensor_presence',{}).pop(r['id'],None)
   s['rooms'].remove(r);s['devices']=[d for d in s['devices'] if d['room_id']!=r['id']]
  elif op in {'room','add_room'}:
   if op=='add_room':
    if len(s['rooms'])>=20:raise HTTPException(422,'Limite de 20 cômodos.')
    r=dict(id=uuid4().hex,name='Novo cômodo',x=0,z=max(r['z']+r['d'] for r in s['rooms']),w=3,d=3);s['rooms'].append(r)
   else:
    r=next((r for r in s['rooms'] if r['id']==data.get('id')),None)
    if not r:raise HTTPException(404,'Cômodo não encontrado.')
   name=data.get('name',r['name'])
   if not isinstance(name,str) or not 1<=len(name.strip())<=50:raise HTTPException(422,'Nome inválido.')
   name=name.strip();others={norm(q['name']) for q in s['rooms'] if q['id']!=r['id']}
   if norm(name) in others:
    if op=='room':raise HTTPException(422,'Já existe um cômodo com esse nome. Escolha outro nome.')
    base=name;i=2
    while norm(name) in others:name=base+' '+str(i);i+=1
   r.update(name=name,w=number(data.get('w',r['w']),2,12),d=number(data.get('d',r['d']),2,12))
   if data.get('manual_position') is True:
    r.update(x=number(data.get('x',r['x']),0,200),z=number(data.get('z',r['z']),0,200))
    from .plan_format import validate_document,export_document
    validate_document(export_document(s),CATALOG)
    return
   # Repack the two-column layout using dimensions to prevent room overlap.
   z=0
   for i in range(0,len(s['rooms']),2):
    a=s['rooms'][i];a.update(x=0,z=z);pair=s['rooms'][i:i+2]
    if len(pair)==2:pair[1].update(x=a['w'],z=z)
    z+=max(q['d'] for q in pair)
  elif op=='sensor_presence':
   if data.get('room_id') not in {r['id'] for r in s['rooms']} or type(data.get('present')) is not bool:raise HTTPException(422,'Presença simulada inválida.')
   s.setdefault('sensor_presence',{})[data['room_id']]=data['present']
  elif op=='settings':
   s['tariff']=number(data.get('tariff',s['tariff']),.01,10);s['goal']=number(data.get('goal',s['goal']),1,80)
  else:raise HTTPException(422,'Operação desconhecida.')
 @api.post('/api/v1/maquette/action')
 def action(body:Action):
  encoded=body.model_dump_json()
  with lock,connect() as c:
   c.execute('BEGIN IMMEDIATE');cached=c.execute('SELECT payload,result FROM maquette_requests WHERE id=?',(body.request_id,)).fetchone()
   if cached:
    if cached[0]!=encoded:raise HTTPException(409,'Identificador usado com outro conteúdo.')
    return json.loads(cached[1])
   s=load(c)
   if s['model']!=body.project or s['revision']!=body.revision:raise HTTPException(409,'A maquete mudou. Atualize a tela.')
   if body.op=='model':
    k=body.data.get('model')
    if k not in {'house','apartment'}:raise HTTPException(422,'Modelo inválido.')
    c.execute('UPDATE maquette_settings SET active=? WHERE id=1',(k,));s=load(c)
   else:
    if body.op=='import_plan':
     from .plan_format import validate_document
     imported=validate_document(body.data.get('document'),CATALOG)
     if imported['model']!=s['model']:raise HTTPException(409,'Selecione o mesmo modelo do arquivo antes de importar.')
     if body.data.get('confirm') is not True:raise HTTPException(409,'Confirme a substituição da planta do projeto ativo.')
     c.execute('INSERT INTO maquette_import_backups(timestamp,model,payload) VALUES (?,?,?)',(datetime.now(timezone.utc).isoformat(),s['model'],json.dumps(s)))
     s={**imported,'revision':s['revision']}
    else:mutate(s,body.op,body.data)
    s['revision']+=1;c.execute('UPDATE maquette_projects SET payload=? WHERE id=?',(json.dumps(s),s['model']))
   if body.op in {'remove_room','remove_device','import_plan'}:c.execute('DELETE FROM maquette_pending')
   result=public(s);c.execute('INSERT INTO maquette_requests VALUES (?,?,?)',(body.request_id,encoded,json.dumps(result)));return result
 @api.get('/api/v1/maquette/export')
 def export_plan():
  from .plan_format import export_document
  return export_document(get_scene())
 @api.post('/api/v1/maquette/import-preview')
 async def import_preview(request:Request):
  raw=bytearray()
  async for chunk in request.stream():
   raw.extend(chunk)
   if len(raw)>1_000_000:raise HTTPException(413,'Planta deve ter até 1 MB.')
  try:doc=json.loads(raw)
  except Exception:raise HTTPException(422,'Arquivo JSON inválido.')
  from .plan_format import validate_document
  p=validate_document(doc,CATALOG)
  return {'model':p['model'],'rooms':len(p['rooms']),'devices':len(p['devices']),'document':doc}
 def chat(text,rid,session):
  phrase=norm(text);marker=re.search(r'\b(?:na |a |a |da )?(?:maquete|marquete)\b',phrase)
  with lock,connect() as c:
   c.execute('BEGIN IMMEDIATE');pending=c.execute('SELECT payload,created FROM maquette_pending WHERE session=?',(session,)).fetchone();p=json.loads(pending[0]) if pending and time.time()-pending[1]<300 else None
   key='chat:'+rid;encoded=json.dumps([text,session]);old=c.execute('SELECT payload,result FROM maquette_requests WHERE id=?',(key,)).fetchone()
   if old:
    if old[0]!=encoded:raise HTTPException(409,'Identificador usado com outro pedido.')
    return json.loads(old[1])
   if not marker:
    if not p:return None
    permitted={norm(r['name']) for r in load(c)['rooms']}
    reply=re.sub(r'^(?:na |no |a |o |em )','',phrase)
    if reply not in permitted and phrase not in {'cancelar','cancele'}:return None
   s=load(c);changed=False;answer='';op=None;k=None
   if p and p.get('model')!=s['model']:
    p=None
    if not marker:return None
   if phrase in {'cancelar','cancele'}:answer='Cancelei o pedido da maquete.'
   elif re.search(r'\b(nao|nunca|exceto)\b',phrase):answer='Não alterei a maquete. Envie uma ação afirmativa por vez.'
   elif marker and re.search(r'\b(consumo|gasta|gastando)\b',phrase):
    active=[d for d in s['devices'] if d['on']]
    ranked=sorted(active,key=lambda d:CATALOG[d['kind']]['watts']*d['hours'],reverse=True)
    amount=public(s)['monthly_kwh'];answer=f'No cenário fictício atual, o consumo calculado é de {amount:.2f} kWh por mês.'
    if ranked:answer+=' O maior consumo estimado é de '+CATALOG[ranked[0]['kind']]['name'].lower()+'.'
   elif marker:
    clean=re.sub(r'\b(?:(?:na|a|da) )?(?:maquete|marquete)\b','',phrase).strip()
    room_request=re.fullmatch(r'(?:adicione|adicionar|inclua|incluir) (?:um |uma )?(quarto|sala|cozinha|banheiro|escritorio|comodo)(?: chamado (.+))?',clean)
    if room_request:
     title=(room_request[2] or room_request[1]).strip().capitalize()
     existing={norm(r['name']) for r in s['rooms']};base=title;n=2
     while norm(title) in existing:title=base+' '+str(n);n+=1
     mutate(s,'add_room',{'name':title});s['revision']+=1;changed=True
     c.execute('UPDATE maquette_projects SET payload=? WHERE id=?',(json.dumps(s),s['model']))
     answer='Pronto, adicionei '+title+' à maquete. Você pode ajustar as medidas no painel.'
    if not answer and re.search(r'\b(adicione|adicionar|inclua|incluir)\b',clean):op='add'
    elif re.match(r'^(ligue|liga|ligar|acenda)\b',clean):op='on'
    elif re.match(r'^(desligue|desliga|desligar|apague)\b',clean):op='off'
    kinds=[key for key,names in ALIASES.items() if any(re.search(r'\b'+re.escape(n)+r'\b',clean) for n in names)]
    if len(kinds)==1:k=kinds[0]
    if answer:pass
    elif len(kinds)>1 or re.search(r'\b(?:e|depois)\b',clean):answer='Envie um aparelho por vez para a maquete.'
    elif not op or not k:answer='Para a maquete, diga por exemplo: adicione uma geladeira à maquete na cozinha.'
   elif p:op=p['op'];k=p['kind'];clean=phrase
   else:clean=phrase
   if op and k and not answer:
    clean=locals().get('clean',phrase)
    matches=[r for r in s['rooms'] if re.search(r'(?<!\w)'+re.escape(norm(r['name']))+r'(?!\w)',clean)]
    # Prefer the longest exact room name: Quarto 2 must not also select Quarto.
    if matches:
     longest=max(len(norm(r['name'])) for r in matches);matches=[r for r in matches if len(norm(r['name']))==longest]
    if len(matches)!=1:
     c.execute('INSERT OR REPLACE INTO maquette_pending VALUES (?,?,?)',(session,json.dumps(dict(op=op,kind=k,model=s['model'])),time.time()))
     answer='Em qual cômodo da maquete? '+', '.join(r['name'] for r in s['rooms'])+'.'
    else:
     room=matches[0]
     if op=='add':
      add(s,k,room['id']);answer=f"Pronto, adicionei {CATALOG[k]['name'].lower()} em {room['name']} na maquete. O aparelho começa desligado."
     else:
      ds=[d for d in s['devices'] if d['kind']==k and d['room_id']==room['id']]
      if len(ds)==1:ds[0]['on']=op=='on';answer=f"Na maquete, {'liguei' if op=='on' else 'desliguei'} {CATALOG[k]['name'].lower()} em {room['name']}."
      elif not ds:answer='Esse aparelho ainda não está nesse cômodo da maquete.'
      else:answer='Há mais de um aparelho desse tipo no cômodo. Selecione o desejado nos controles da maquete.'
     if op=='add' or len(ds)==1:
      changed=True;s['revision']+=1;c.execute('UPDATE maquette_projects SET payload=? WHERE id=?',(json.dumps(s),s['model']))
   if changed or answer.startswith(('Cancelei','Não alterei','Envie','Para a maquete','Esse aparelho','Há mais')):c.execute('DELETE FROM maquette_pending WHERE session=?',(session,))
   result=dict(id=key,request_id=rid,session_id=session,status='confirmed' if changed else 'answered',answer=answer,actions_executed=changed,response_source='maquette_simulation',model='rules',prompt_version='maquette-v12',timestamp=datetime.now(timezone.utc).isoformat(),context={'source':'simulation','maquette':public(s)},notice='Somente a maquete fictícia foi consultada ou alterada.')
   if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assistant_history'").fetchone():
    cur=c.execute('INSERT INTO assistant_history(timestamp,question,answer,model,prompt_version,context,response_source,session_id) VALUES(?,?,?,?,?,?,?,?)',(result['timestamp'],text,answer,'rules','maquette-v12',json.dumps(result['context']),'maquette_simulation',session));result['id']=cur.lastrowid
   c.execute('INSERT INTO maquette_requests VALUES (?,?,?)',(key,encoded,json.dumps(result)))
   return result
 api.state.maquette_chat=chat
 api.state.maquette_get=get_scene
 api.state.maquette_action=action

 from .plan_files import setup as setup_plan_files
 setup_plan_files(api,get_scene)
 from .openplan_routes import setup as setup_openplan
 setup_openplan(api,get_scene,root)
