"""Entrypoint for an isolated shared test house behind Netlify."""
import os
import secrets
from fastapi.responses import JSONResponse

TOKEN=os.environ.get('AETHER_API_TOKEN','')
if len(TOKEN)<32:
    raise RuntimeError('Configure AETHER_API_TOKEN com pelo menos 32 caracteres aleatórios.')

from .main import app

@app.middleware('http')
async def api_token(request,call_next):
    if request.url.path.startswith('/api/') and not secrets.compare_digest(request.headers.get('x-aether-token','').encode(),TOKEN.encode()):
        return JSONResponse({'detail':'Não autorizado.'},status_code=401)
    return await call_next(request)

@app.get('/healthz')
def health():
    return {'status':'ok','mode':'shared_test_house'}
