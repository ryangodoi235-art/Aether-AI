"""Execute na raiz do projeto. Download inicial; fala posterior inteiramente local."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--testar',action='store_true');args=ap.parse_args()
    root=Path(__file__).resolve().parent
    target=root/'backend/models/kokoro';target.mkdir(parents=True,exist_ok=True)
    base='https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/'
    manifest={}
    for name in ['kokoro-v1.0.onnx','voices-v1.0.bin']:
        p=target/name
        if not p.exists():
            print('Baixando',name,'(somente preparação inicial)…',flush=True)
            tmp=p.with_suffix(p.suffix+'.part')
            try:
                with urllib.request.urlopen(base+name,timeout=120) as response,tmp.open('wb') as out:
                    while chunk:=response.read(1024*1024):out.write(chunk)
                if tmp.stat().st_size<1_000_000:raise ValueError('Download incompleto')
                tmp.replace(p)
            finally:tmp.unlink(missing_ok=True)
        manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (target/'downloads.json').write_text(json.dumps(manifest,indent=2))
    print('Arquivos preparados. Hashes locais em downloads.json (não são assinatura do autor).')
    if args.testar:
        sys.path.insert(0,str(root/'backend'))
        from backend.app.local_voices import LocalVoices
        voices=LocalVoices(root/'backend')
        for key in ['female','male']:
            p=root/('teste_'+key+'.wav')
            p.write_bytes(voices.speak('Olá, Ryan. Vamos cuidar da sua casa com calma e economizar energia.',key))
            print('Ouça e compare:',p)
if __name__=='__main__':main()
