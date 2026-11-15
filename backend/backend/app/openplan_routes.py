"""Preview-only adapters; commits use existing revision-checked maquette action."""
import json
from pathlib import Path
from fastapi import Request,Query,HTTPException
from fastapi.responses import FileResponse,Response
from starlette.concurrency import run_in_threadpool
from .plan_files import limited
from .openplan_adapter import to_openplan,from_openplan
from .pdf_rooms import detect

def setup(api,get_scene,root):
 @api.get('/plantas-local',include_in_schema=False)
 def page():return FileResponse(Path(root)/'frontend/plantas_local.html',headers={'Cache-Control':'no-store'})
 @api.get('/plantas-local.js',include_in_schema=False)
 def script():return FileResponse(Path(root)/'frontend/plantas_local.js',media_type='application/javascript',headers={'Cache-Control':'no-store'})
 @api.get('/plantas-home.js',include_in_schema=False)
 def home():return FileResponse(Path(root)/'frontend/plantas_home.js',media_type='application/javascript',headers={'Cache-Control':'no-store'})
 @api.get('/api/v1/maquette/openplan/export')
 def export():return Response(json.dumps(to_openplan(get_scene()),ensure_ascii=False),media_type='application/json',headers={'Content-Disposition':'attachment; filename="Aether.openplan.json"','Cache-Control':'no-store'})
 @api.post('/api/v1/maquette/openplan/preview')
 async def preview(request:Request):
  raw=await limited(request)
  try:doc=json.loads(raw)
  except (ValueError,UnicodeError):raise HTTPException(422,'JSON inválido.')
  scene=get_scene()
  try:document=from_openplan(doc,scene,scene['catalog'])
  except HTTPException:raise
  except (TypeError,ValueError,KeyError,OverflowError):raise HTTPException(422,'Estrutura de projeto inválida.')
  return dict(document=document,base_revision=scene['revision'],notice='Geometria compatível. Estados, RGB e sensores atuais preservados. Anotações do editor não comandam aparelhos.')
 @api.post('/api/v1/maquette/pdf/preview')
 async def pdf(request:Request,page:int=Query(1,ge=1,le=100),width_m:float=Query(...,ge=3,le=100)):
  raw=await limited(request);scene=get_scene()
  result=await run_in_threadpool(detect,raw,page-1,width_m,scene)
  result['base_revision']=scene['revision'];return result
