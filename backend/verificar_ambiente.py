"""Read-only preflight. No automatic device commands or audio capture."""
import argparse,json,sys,urllib.request,urllib.error,os
from pathlib import Path

def run(base):
    report={'version':'0.14-RC2','checks':{},'ready_for_full_test':False}
    for name,path in [('backend','/api/v1/devices'),('assistant','/api/v1/assistant/status'),('voice','/api/v1/voice/status')]:
        try:
            headers={}
            if os.environ.get('AETHER_API_TOKEN'):headers['X-Aether-Token']=os.environ['AETHER_API_TOKEN']
            with urllib.request.urlopen(urllib.request.Request(base.rstrip('/')+path,headers=headers),timeout=15) as r:report['checks'][name]={'reachable':True,'result':json.load(r)}
        except Exception as e:report['checks'][name]={'reachable':False,'error':str(e)}
    voice=report['checks']['voice'].get('result',{})
    # Presence checks cannot certify inference or microphone/audio playback.
    report['next_step']='Testar conversa livre, gravação, transcrição e áudio no navegador. Status não certifica o fluxo completo.'
    report['voice_files_present']=bool(voice.get('recognition_ready') and voice.get('speech_ready'))
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8000');args=p.parse_args()
    result=run(args.url);Path('diagnostico_aether.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if all(v['reachable'] for v in result['checks'].values()) else 1)
