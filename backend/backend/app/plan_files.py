"""Local file adapters. PDF is a tracing reference; DXF contains explicit room rectangles."""
import io,math
from fastapi import HTTPException,Request,Query
from fastapi.responses import Response

async def limited(request,limit=8_000_000):
 raw=bytearray()
 async for chunk in request.stream():
  raw.extend(chunk)
  if len(raw)>limit:raise HTTPException(413,'Arquivo deve ter até 8 MB.')
 if not raw:raise HTTPException(422,'Arquivo vazio.')
 return bytes(raw)

def dxf_document(raw,scene):
 try:import ezdxf
 except ImportError:raise HTTPException(503,'Instale requirements-maquete-v19.txt para usar DXF.')
 try:
  text=raw.decode('utf-8-sig')
 except UnicodeDecodeError:text=raw.decode('cp1252',errors='replace')
 try:
  doc=ezdxf.read(io.StringIO(text));units=doc.header.get('$INSUNITS',0)
  scale={6:1,4:.001,5:.01}.get(units)
  if scale is None:raise HTTPException(422,'Defina unidades DXF em metros, centímetros ou milímetros antes de importar.')
  if len(doc.modelspace())>20000:raise HTTPException(422,'DXF muito complexo: limite de 20 mil entidades.')
  rooms=[]
  for e in doc.modelspace():
   if e.dxftype()!='LWPOLYLINE' or e.dxf.layer!='AETHER_ROOMS':continue
   if not e.closed or len(e)!=4 or any(abs(v[4])>1e-8 for v in e.get_points()):raise HTTPException(422,'Use retângulos fechados sem arcos na camada AETHER_ROOMS.')
   pts=[(round(float(v[0])*scale,6),round(float(v[1])*scale,6)) for v in e.get_points()]
   xs=sorted(set(x for x,y in pts));ys=sorted(set(y for x,y in pts))
   if len(xs)!=2 or len(ys)!=2 or len(set(pts))!=4 or any(pts[i][0]!=pts[(i+1)%4][0] and pts[i][1]!=pts[(i+1)%4][1] for i in range(4)):raise HTTPException(422,'Somente cômodos retangulares alinhados aos eixos nesta versão.')
   rooms.append(dict(id='cad-'+str(len(rooms)+1),name='Cômodo '+str(len(rooms)+1),x=xs[0],z=-ys[1],w=xs[1]-xs[0],d=ys[1]-ys[0]))
   if len(rooms)>20:raise HTTPException(422,'Máximo de 20 cômodos.')
  if not rooms:raise HTTPException(422,'Nenhum retângulo de cômodo na camada AETHER_ROOMS. Use o DXF de exemplo ou prepare essa camada no CAD; paredes soltas não são reconhecidas automaticamente.')
  minx=min(r['x'] for r in rooms);minz=min(r['z'] for r in rooms)
  for r in rooms:r['x']-=minx;r['z']-=minz
  result={'schema_version':'aether-floorplan-1','project':dict(model=scene['model'],rooms=rooms,devices=[],tariff=scene['tariff'],goal=scene['goal'])}
  return result
 except HTTPException:raise
 except Exception:raise HTTPException(422,'DXF não pôde ser lido. Use DXF ASCII com retângulos na camada AETHER_ROOMS.') from None

def setup(api,get_scene):
 @api.post('/api/v1/maquette/files/pdf-reference')
 async def pdf_reference(request:Request,page:int=Query(1,ge=1,le=100)):
  raw=await limited(request)
  try:import fitz
  except ImportError:raise HTTPException(503,'Instale requirements-maquete-v19.txt para abrir PDF.')
  try:
   with fitz.open(stream=raw,filetype='pdf') as doc:
    if doc.needs_pass:raise HTTPException(422,'Remova a senha do PDF antes de importar.')
    if page>len(doc):raise HTTPException(422,'Página inexistente no PDF.')
    p=doc[page-1]
    if not math.isfinite(p.rect.width+p.rect.height) or min(p.rect.width,p.rect.height)<=0:raise HTTPException(422,'Página PDF inválida.')
    pix=p.get_pixmap(matrix=fitz.Matrix(min(1.5,1400/max(p.rect.width,p.rect.height)),min(1.5,1400/max(p.rect.width,p.rect.height))),alpha=False)
    return Response(pix.tobytes('png'),media_type='image/png',headers={'Cache-Control':'no-store','X-Aether-Pages':str(len(doc))})
  except HTTPException:raise
  except Exception:raise HTTPException(422,'PDF inválido ou não renderizável.') from None
 @api.post('/api/v1/maquette/files/dxf-preview')
 async def dxf_preview(request:Request):
  document=dxf_document(await limited(request),get_scene())
  from .plan_format import validate_document
  from .maquette import CATALOG
  p=validate_document(document,CATALOG)
  return dict(document=document,rooms=len(p['rooms']),notice='Somente contornos retangulares. Aparelhos e sensores não são importados do DXF. Revise antes de substituir a planta.')
 @api.get('/api/v1/maquette/files/export.dxf')
 def export_dxf():
  try:import ezdxf
  except ImportError:raise HTTPException(503,'Instale requirements-maquete-v19.txt para exportar DXF.')
  s=get_scene();doc=ezdxf.new('R2010');doc.header['$INSUNITS']=6;doc.layers.new('AETHER_ROOMS');doc.layers.new('AETHER_LABELS');space=doc.modelspace()
  for r in s['rooms']:
   x,z,w,d=[r[k] for k in ['x','z','w','d']]
   space.add_lwpolyline([(x,-z),(x+w,-z),(x+w,-z-d),(x,-z-d)],close=True,dxfattribs={'layer':'AETHER_ROOMS'})
   space.add_text(r['name'],dxfattribs={'layer':'AETHER_LABELS','height':.18,'insert':(x+.2,-z-.3)})
  buf=io.StringIO();doc.write(buf)
  return Response(buf.getvalue().encode('utf-8'),media_type='application/dxf',headers={'Content-Disposition':'attachment; filename="Aether_planta.dxf"','Cache-Control':'no-store'})
 @api.get('/api/v1/maquette/files/export.pdf')
 def export_pdf():
  try:
   from reportlab.pdfgen.canvas import Canvas
   from reportlab.lib.pagesizes import A4,landscape
  except ImportError:raise HTTPException(503,'Instale requirements-maquete-v19.txt para exportar PDF.')
  s=get_scene();buf=io.BytesIO();size=landscape(A4);c=Canvas(buf,pagesize=size);W,H=size
  c.setTitle('Aether — planta fictícia');c.setFont('Helvetica-Bold',18);c.drawString(35,H-35,'Aether | Planta fictícia e sensores simulados')
  maxx=max(r['x']+r['w'] for r in s['rooms']);maxz=max(r['z']+r['d'] for r in s['rooms']);scale=min((W-80)/maxx,(H-140)/maxz)
  for r in s['rooms']:
   x=40+r['x']*scale;y=H-75-(r['z']+r['d'])*scale;w=r['w']*scale;h=r['d']*scale
   c.setStrokeColorRGB(.1,.45,.5);c.rect(x,y,w,h);c.setFont('Helvetica',min(10,max(5,scale*.18)));c.drawString(x+4,y+h-13,r['name'][:50]);c.drawString(x+4,y+h-25,f"{r['w']} x {r['d']} m | sensor T/UR/presenca (simulado)")
   for i,d in enumerate(q for q in s['devices'] if q['room_id']==r['id']):
    name=s['catalog'][d['kind']]['name'];c.drawString(x+4,y+h-39-i*11,name+(' ON' if d['on'] else ' OFF'))
  c.setFont('Helvetica',9);c.drawString(35,40,'Geometria ilustrativa. PDF sem escala de impressão garantida; valores dimensionais declarados em metros.')
  c.drawString(35,25,'Para continuar editando, exporte também o JSON. Sensores e consumos não são medições físicas.');c.showPage();c.save()
  return Response(buf.getvalue(),media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="Aether_planta.pdf"','Cache-Control':'no-store'})
