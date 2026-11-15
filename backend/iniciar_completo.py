"""Start local backend and reuse/start Ollama. Only stops processes it owns."""
from pathlib import Path
import subprocess,urllib.request,json,shutil,time,sys,os
root=Path(__file__).resolve().parent
os.chdir(root)
def ollama_ready():
 try:
  with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2) as r:
   return any(m.get('name')=='qwen2.5:3b' for m in json.load(r).get('models',[]))
 except Exception:return False
owned=None
try:
 if not ollama_ready():
  exe=shutil.which('ollama')
  if not exe:sys.exit('Instale Ollama e baixe qwen2.5:3b antes de iniciar.')
  # An existing server without the model must not be killed or replaced.
  try:urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=2).close()
  except Exception:owned=subprocess.Popen([exe,'serve'])
  for _ in range(15):
   if ollama_ready():break
   time.sleep(1)
  if not ollama_ready():sys.exit('Ollama/modelo indisponível. Execute: ollama pull qwen2.5:3b')
 print('Abra http://127.0.0.1:8000/painel. Ctrl+C encerra o servidor.')
 subprocess.run([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000'],check=True)
except KeyboardInterrupt:pass
finally:
 if owned is not None:owned.terminate()
