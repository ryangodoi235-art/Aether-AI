from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field,ConfigDict
from .neural_runtime import load,classify,predict_energy,NeuralError
class Text(BaseModel):
 model_config=ConfigDict(extra='forbid')
 text:str=Field(min_length=1,max_length=800)
class Energy(BaseModel):
 model_config=ConfigDict(extra='forbid')
 features:list=Field(min_length=11,max_length=11)
def setup(api,root):
 @api.get('/api/v1/neural/status')
 def status():
  try:return {'ready':True,'models':[load('intent')['version'],load('energy')['version']],'execution':'local','metrics':load('metrics'),'notice':'Dados de avaliação sintéticos. Não comprova entendimento geral, sensores físicos ou economia.'}
  except NeuralError as e:raise HTTPException(503,str(e))
 @api.post('/api/v1/neural/classify')
 def intent(body:Text):
  try:return classify(body.text)
  except NeuralError as e:raise HTTPException(422,str(e))
 @api.post('/api/v1/neural/forecast')
 def forecast(body:Energy):
  try:return predict_energy(body.features)
  except NeuralError as e:raise HTTPException(422,str(e))
 @api.get('/neural',include_in_schema=False)
 def lab():return FileResponse(Path(root)/'frontend/neural_lab.html',headers={'Cache-Control':'no-store'})
 @api.get('/neural-assets/home.js',include_in_schema=False)
 def home():return FileResponse(Path(root)/'frontend/neural_home.js',media_type='application/javascript',headers={'Cache-Control':'no-store'})
