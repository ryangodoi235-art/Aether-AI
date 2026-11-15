"""Run explicitly once: downloads local speech models. Daily use stays offline."""
import subprocess,sys,os
from pathlib import Path
root=Path(__file__).resolve().parent
os.chdir(root)
if not (root/'backend/app/main.py').is_file():sys.exit('Execute na raiz do Aether.')
subprocess.run([sys.executable,'-m','pip','install','--only-binary=:all:','faster-whisper','av<19','piper-tts','huggingface_hub'],check=True)
from huggingface_hub import snapshot_download
(root/'models').mkdir(exist_ok=True)
snapshot_download('Systran/faster-whisper-tiny',local_dir=str(root/'models/whisper-tiny'))
subprocess.run([sys.executable,'-m','piper.download_voices','pt_BR-faber-medium','--download-dir',str(root/'models')],check=True)
print('Voz preparada. Reinicie o Aether e confira o status de voz no painel.')

subprocess.run([sys.executable,str(root/'testar_voz_local.py')],check=True)
