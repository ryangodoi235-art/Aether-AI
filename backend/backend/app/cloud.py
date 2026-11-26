"""Protected Python API for Netlify; one explicitly shared simulation per server."""
import os
import secrets
import shutil
from pathlib import Path

from fastapi.responses import JSONResponse


def validated_token(value):
    if (not isinstance(value, str) or not 32 <= len(value) <= 512
            or not value.isascii() or any(c.isspace() for c in value)):
        raise RuntimeError('Defina AETHER_API_TOKEN com 32–512 caracteres ASCII, sem espaços. Use o mesmo token no Netlify.')
    return value


def create_cloud_app():
    token = validated_token(os.environ.get('AETHER_API_TOKEN', ''))
    root = Path(__file__).resolve().parents[2]
    data_dir = Path(os.environ.get('AETHER_DATA_DIR') or root / 'data').resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    config = Path(os.environ.get('AETHER_CONFIG_PATH') or data_dir / 'house.json')
    if not config.exists():
        config.parent.mkdir(parents=True, exist_ok=True)
        # Bootstrap once. Restarting must not overwrite the resident's catalog.
        shutil.copyfile(root / 'config/house.json', config)
    os.environ.setdefault('AETHER_LOCAL_NLU', '1')
    os.environ.setdefault('AETHER_GENERAL_LLM', '0')
    os.environ.setdefault('AETHER_LOCAL_TIMEOUT', '40')
    # This entrypoint must never silently use hosted language or voice APIs.
    for name in ('FISH_API_KEY', 'AETHER_FISH_API_KEY', 'OPENAI_API_KEY', 'AETHER_GPT_ENABLED'):
        os.environ.pop(name, None)
    from .main import create_app
    app = create_app(config_path=config, db_path=data_dir / 'aether.sqlite3')

    @app.middleware('http')
    async def authenticate(request, call_next):
        if request.url.path != '/healthz':
            received = request.headers.get('x-aether-token', '')
            if not secrets.compare_digest(received.encode('utf-8'), token.encode('ascii')):
                return JSONResponse({'detail': 'Não autorizado.'}, status_code=401,
                                    headers={'Cache-Control': 'no-store'})
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/healthz', include_in_schema=False)
    def health():
        return {'status': 'ok', 'mode': 'shared_simulation', 'storage': 'sqlite',
                'notice': 'API disponível. Não comprova disponibilidade de voz, Ollama ou sensores físicos.'}

    @app.get('/api/v1/deployment/status')
    def deployment_status():
        from .neural_runtime import load, NeuralError
        try:
            load('intent'); load('energy')
            neural_ready = True
        except NeuralError:
            neural_ready = False
        return {'mode': 'shared_simulation', 'storage': 'sqlite', 'neural_ready': neural_ready,
                'general_ollama_enabled': os.environ.get('AETHER_GENERAL_LLM') == '1',
                'multiuser_isolation': False, 'physical_sensors': False,
                'notice': 'MongoDB no Netlify guarda cópias JSON; não substitui este SQLite.'}

    return app


app = create_cloud_app()
