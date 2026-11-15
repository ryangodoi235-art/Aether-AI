"""Local raster conversion with conservative rectangular enclosed-space detection.
Not a neural model, not universal CAD reconstruction. Preview only; never mutates state.
"""
import math
from fastapi import HTTPException

def detect(raw,page,width_m,scene):
 try:
  import fitz
  import numpy as np
  from scipy import ndimage
 except ImportError:raise HTTPException(503,'Instale requirements-ponte-v22.txt no ambiente do Aether.')
 try:
  with fitz.open(stream=raw,filetype='pdf') as doc:
   if doc.needs_pass or not 0<=page<len(doc):raise HTTPException(422,'PDF com senha ou página inexistente.')
   p=doc[page]
   if not math.isfinite(p.rect.width+p.rect.height) or min(p.rect.width,p.rect.height)<=0:raise HTTPException(422,'Página inválida.')
   scale=min(2,1400/max(p.rect.width,p.rect.height))
   pix=p.get_pixmap(matrix=fitz.Matrix(scale,scale),colorspace=fitz.csGRAY,alpha=False)
   image=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width)
   # Small closing repairs raster cracks, not door-sized openings. No hallucinated walls.
   ink=ndimage.binary_closing(image<140,structure=np.ones((3,3)))
   components,n=ndimage.label(~ink);boxes=ndimage.find_objects(components)
   factor=width_m/pix.width;rooms=[];warnings=[]
   words=p.get_text('words')
   for label,box in enumerate(boxes,1):
    if box is None:continue
    y,x=box;w=x.stop-x.start;h=y.stop-y.start
    if x.start<3 or y.start<3 or x.stop>pix.width-3 or y.stop>pix.height-3:continue
    if w*h<image.size*.008:continue
    fill=float(np.count_nonzero(components[box]==label))/(w*h)
    if fill<.88:continue
    wm,dm=w*factor,h*factor
    if not (2<=wm<=12 and 2<=dm<=12):continue
    inside=[v[4] for v in words if x.start<=((v[0]+v[2])/2)*scale<=x.stop and y.start<=((v[1]+v[3])/2)*scale<=y.stop]
    name=' '.join(inside)[:45].strip() or 'Cômodo '+str(len(rooms)+1)
    if any(r['name'].casefold()==name.casefold() for r in rooms):name='Cômodo '+str(len(rooms)+1)
    rooms.append(dict(id='pdf-room-'+str(len(rooms)+1),name=name,x=round(x.start*factor,3),z=round(y.start*factor,3),w=round(wm,3),d=round(dm,3)))
   if not rooms:raise HTTPException(422,'Não identifiquei cômodos retangulares fechados de 2–12 m. Confira a largura da página; use traçado manual para portas abertas ou plantas irregulares.')
   if len(rooms)>20:raise HTTPException(422,'Mais de 20 áreas candidatas. Use uma página com apenas a planta.')
   # Preserve devices only for an unambiguous room-name match; report every unmatched item.
   import unicodedata,copy
   def norm(v):return ''.join(c for c in unicodedata.normalize('NFD',v.casefold()) if unicodedata.category(c)!='Mn')
   old={r['id']:r for r in scene['rooms']};devices=[];unmatched=[]
   for d in scene['devices']:
    found=[r for r in rooms if norm(r['name'])==norm(old[d['room_id']]['name'])]
    if len(found)==1:
     item=copy.deepcopy(d);item['room_id']=found[0]['id'];devices.append(item)
    else:unmatched.append(d['id'])
   if unmatched:warnings.append(f'{len(unmatched)} aparelhos não têm cômodo correspondente e seriam removidos desta planta. Cancele se quiser mantê-los; o projeto anterior fica no backup de importação.')
   presence={}
   for r in scene['rooms']:
    found=[new for new in rooms if norm(new['name'])==norm(r['name'])]
    if len(found)==1 and r['id'] in scene.get('sensor_presence',{}):presence[found[0]['id']]=scene['sensor_presence'][r['id']]
   document=dict(schema_version='aether-floorplan-1',project=dict(model=scene['model'],rooms=rooms,devices=devices,tariff=scene['tariff'],goal=scene['goal'],sensor_presence=presence))
   from .plan_format import validate_document
   validate_document(document,scene['catalog'])
   return dict(document=document,page=page+1,pages=len(doc),page_width_m=width_m,rooms=len(rooms),unmatched_device_ids=unmatched,warnings=warnings,notice='Rascunho por imagem. Revise nomes, medidas e áreas: o detector não conhece escala real, portas, janelas nem móveis. Largura informada corresponde à página inteira do PDF.')
 except HTTPException:raise
 except Exception as exc:raise HTTPException(422,'Não foi possível converter este PDF. Use uma página simples de planta baixa.') from exc
