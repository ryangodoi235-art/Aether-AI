"""No hosted AI/voice: local artifacts, Piper/Whisper optional, Ollama optional."""
import os,sys,subprocess,webbrowser
from pathlib import Path
root=Path(__file__).resolve().parent
for name in ['FISH_API_KEY','AETHER_FISH_API_KEY','OPENAI_API_KEY','AETHER_GPT_ENABLED']:os.environ.pop(name,None)
os.environ['AETHER_LOCAL_NLU']='1'
os.environ.setdefault('AETHER_GENERAL_LLM','1')
os.environ['PYTHONUTF8']='1'
print('Aether neural local: MLP de intenção e consumo. Sem API Fish/OpenAI.')
print('Voz disponível apenas se Piper local estiver preparado. Microfone requer Whisper local.')
print('Abra http://127.0.0.1:8000/painel — Ctrl+C encerra.')
try:raise SystemExit(subprocess.call([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000'],cwd=root))
except KeyboardInterrupt:pass
