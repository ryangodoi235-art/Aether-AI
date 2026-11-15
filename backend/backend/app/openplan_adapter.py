"""Conservative local interchange. Native openPlan3D centimetres ↔ Aether metres."""
import copy,math
from fastapi import HTTPException
from .plan_format import export_document,validate_document

def bad(message):raise HTTPException(422,message)
def number(x):
 if type(x) not in (int,float) or not math.isfinite(x) or abs(x)>100000:bad('Coordenada inválida no projeto.')
 return x

def to_openplan(scene):
 floor=dict(id='aether-ground',name='Aether',level=0,walls=[],rooms=[],furniture=[],doors=[],windows=[])
 # Shared identical segments reuse IDs. No arbitrary catalog IDs: devices are annotations;
 # Aether retains the authoritative electrical objects in a separate snapshot.
 segments={}
 for r in scene['rooms']:
  x,z,w,d=[r[k]*100 for k in ('x','z','w','d')];pts=[(x,z),(x+w,z),(x+w,z+d),(x,z+d)];ids=[]
  for i,a in enumerate(pts):
   b=pts[(i+1)%4];key=tuple(sorted((a,b)))
   if key not in segments:
    ident='wall-'+str(len(segments)+1);segments[key]=ident
    floor['walls'].append(dict(id=ident,start=dict(x=a[0],y=a[1]),end=dict(x=b[0],y=b[1]),thickness=12,height=270))
   ids.append(segments[key])
  floor['rooms'].append(dict(id=r['id'],name=r['name'],walls=ids))
 floor['textAnnotations']=[]
 for d in scene['devices']:
  r=next(r for r in scene['rooms'] if r['id']==d['room_id'])
  floor['textAnnotations'].append(dict(id='device-'+d['id'],x=(r['x']+r['w']*d.get('u',.5))*100,y=(r['z']+r['d']*d.get('v',.5))*100,text=scene['catalog'][d['kind']]['name']+' [Aether]',fontSize=14))
 return dict(id='aether-'+scene['model'],name='Aether '+scene['model'],activeFloorId=floor['id'],floors=[floor],aetherBridge=dict(version=1,document=export_document(scene)))

def from_openplan(data,scene,catalog):
 if not isinstance(data,dict):bad('Projeto deve ser JSON.')
 floors=data.get('floors')
 if not isinstance(floors,list) or len(floors)!=1:bad('A ponte aceita exatamente um pavimento.')
 floor=floors[0]
 if not isinstance(floor,dict):bad('Pavimento inválido.')
 for key in ['stairs','columns','doors','windows','furniture','entourage','groups']:
  if floor.get(key):bad('O Aether ainda não importa '+key+'. Mantenha o JSON completo no editor; não será convertido com perda silenciosa.')
 walls=floor.get('walls');rs=floor.get('rooms')
 if not isinstance(walls,list) or len(walls)>1000 or not isinstance(rs,list) or not 1<=len(rs)<=20:bad('Informe até 20 cômodos com metadados e paredes.')
 byid={}
 for wall in walls:
  if not isinstance(wall,dict) or not isinstance(wall.get('id'),str) or wall['id'] in byid:bad('Paredes com IDs inválidos ou duplicados.')
  if wall.get('curvePoint'):bad('Paredes curvas não são suportadas nesta ponte.')
  byid[wall['id']]=wall
 rooms=[];used=set()
 for r in rs:
  if not isinstance(r,dict) or not isinstance(r.get('walls'),list) or len(r['walls'])!=4:bad('Cada cômodo deve ter quatro paredes retas, formando um retângulo.')
  if len(set(r['walls']))!=4:bad('Paredes repetidas no cômodo.')
  edges=[]
  for ident in r['walls']:
   if ident not in byid:bad('Cômodo referencia parede inexistente.')
   wall=byid[ident];used.add(ident)
   try:a=tuple(round(number(wall['start'][k]),5) for k in ('x','y'));b=tuple(round(number(wall['end'][k]),5) for k in ('x','y'))
   except (KeyError,TypeError):bad('Extremos da parede inválidos.')
   edges.append(tuple(sorted((a,b))))
  pts=set(p for edge in edges for p in edge);xs=sorted({p[0] for p in pts});ys=sorted({p[1] for p in pts})
  if len(xs)!=2 or len(ys)!=2 or len(pts)!=4:bad('Cômodo irregular ou rotacionado: a ponte aceita retângulos alinhados aos eixos.')
  a,b,c,d=(xs[0],ys[0]),(xs[1],ys[0]),(xs[1],ys[1]),(xs[0],ys[1])
  if set(edges)!={tuple(sorted(e)) for e in [(a,b),(b,c),(c,d),(d,a)]}:bad('Contorno de cômodo aberto ou cruzado.')
  rooms.append(dict(id=r.get('id'),name=r.get('name'),x=xs[0]/100,z=ys[0]/100,w=(xs[1]-xs[0])/100,d=(ys[1]-ys[0])/100))
 if used!=set(byid):bad('Há paredes soltas que não podem ser representadas no Aether.')
 bridge=data.get('aetherBridge',{})
 # Keep current states, RGB and sensor choices: never restore stale embedded states.
 if bridge and (not isinstance(bridge,dict) or bridge.get('version')!=1):bad('Versão de ponte inválida.')
 ids={r['id'] for r in rooms};missing={d['room_id'] for d in scene['devices']}-ids
 if missing:bad('A planta remove cômodos que ainda têm aparelhos. Remova ou transfira os aparelhos no Aether antes de importar.')
 p=copy.deepcopy(export_document(scene));p['project']['rooms']=rooms
 p['project']['sensor_presence']={k:v for k,v in scene.get('sensor_presence',{}).items() if k in ids}
 validate_document(p,catalog)
 return p
