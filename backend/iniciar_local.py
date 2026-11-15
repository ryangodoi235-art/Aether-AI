"""Start the local interpreter; no GPT key and no cloud language model."""
import os,sys,json,shutil,subprocess,socket,time,urllib.request,getpass
from pathlib import Path
root=Path(__file__).resolve().parent
for name in ['OPENAI_API_KEY','AETHER_GPT_ENABLED','AETHER_OPENAI_MODEL']:os.environ.pop(name,None)
os.environ['AETHER_LOCAL_NLU']='1'
model=os.environ.get('AETHER_LOCAL_MODEL','qwen2.5:3b')
owned=None
# Same endpoint as the interpreter; prohibit remote LLM endpoints.
from urllib.parse import urlsplit
url=os.environ.get('AETHER_OLLAMA_URL','http://127.0.0.1:11434').rstrip('/')
u=urlsplit(url)
if u.scheme!='http' or u.hostname not in {'127.0.0.1','localhost','::1'} or u.username or u.password or u.path:raise SystemExit('Use um endereço HTTP local para o Ollama.')
def models():
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url+'/api/tags',timeout=3) as r:return json.load(r).get('models',[])
try:
 with socket.socket() as s:
  try:s.bind(('127.0.0.1',8000))
  except OSError:raise SystemExit('Porta 8000 ocupada. Pare o Aether anterior antes de iniciar.')
 try:available=models()
 except Exception:
  exe=shutil.which('ollama')
  if not exe:raise SystemExit('Ollama não encontrado. Instale o Ollama para usar a interpretação local.')
  owned=subprocess.Popen([exe,'serve'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for i in range(20):
   try:available=models();break
   except Exception:
    if owned.poll() is not None:raise SystemExit('O Ollama não conseguiu iniciar. Confira o serviço local.')
    time.sleep(.5)
  else:raise SystemExit('O Ollama local não respondeu a tempo.')
 entry=next((x for x in available if x.get('name')==model or x.get('model')==model),None)
 if not entry:raise SystemExit('Baixe o modelo antes de iniciar: ollama pull '+model)
 if entry.get('remote_host') or entry.get('remote_model') or model.endswith(':cloud'):raise SystemExit('Selecione um modelo baixado localmente, não cloud.')
 print('Aether local: '+model+'. Nenhuma chave GPT necessária e nenhuma cobrança por tokens.')
 print('A primeira interpretação pode demorar enquanto o modelo carrega na memória.')
 if not os.environ.get('FISH_API_KEY') and sys.stdin.isatty():
  fish=getpass.getpass('Chave Fish Audio para voz Jarvis (Enter para manter sem chave nesta execução): ').strip()
  if fish:os.environ['FISH_API_KEY']=fish
 print('A voz Fish Audio, se utilizada, continua sendo um serviço externo.')
 print('Abra http://127.0.0.1:8000/painel?v=14 • Ctrl+C encerra.')
 subprocess.call([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000'],cwd=root)
except KeyboardInterrupt:pass
finally:
 if owned and owned.poll() is None:
  owned.terminate()
  try:owned.wait(timeout=5)
  except subprocess.TimeoutExpired:owned.kill();owned.wait()
