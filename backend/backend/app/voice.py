"""Optional local Whisper/Piper. No browser cloud speech services."""
import os,importlib.util,threading,tempfile,subprocess,sys,io,wave
from pathlib import Path
from fastapi import HTTPException,Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel,Field
from typing import Literal
from .local_voices import LocalVoices

class Speech(BaseModel):
    text:str=Field(min_length=1,max_length=1500)
    voice:Literal["female","male"]="male"

def setup(api,root):
    lock=threading.Lock();model=None
    voices=LocalVoices(root)
    def paths():
        return Path(os.environ.get('AETHER_WHISPER_MODEL',str(root/'models/whisper-tiny'))),Path(os.environ.get('AETHER_PIPER_MODEL',str(root/'models/pt_BR-faber-medium.onnx')))
    @api.get('/api/v1/voice/status')
    def status():
        whisper,piper=paths()
        return {'recognition_ready':all((whisper/f).is_file() for f in ['model.bin','config.json','tokenizer.json']) and importlib.util.find_spec('faster_whisper') is not None,
                'speech_ready':voices.ready(), 'voices':voices.options(), 'engine':'kokoro_onnx_local',
                'readiness_scope':'Arquivos e pacotes presentes. Execute TESTAR_VOZ.bat para verificar inferência.',
                'message':'Dora feminina e Alex masculina, síntese local. Prepare com preparar_duas_vozes.py. Reconhecimento usa Whisper separado.'}
    def transcribe(raw):
        nonlocal model
        if not status()['recognition_ready']:raise HTTPException(503,'Whisper local não preparado. Execute preparar_voz.py na raiz do projeto.')
        if not lock.acquire(blocking=False):raise HTTPException(429,'Voz ocupada; aguarde.')
        try:
            from faster_whisper import WhisperModel
            if model is None:model=WhisperModel(str(paths()[0]),device='cpu',compute_type='int8',local_files_only=True,cpu_threads=4)
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'audio.webm';p.write_bytes(raw)
                # Decode and enforce duration before model inference.
                from faster_whisper.audio import decode_audio
                samples=decode_audio(str(p),sampling_rate=16000)
                if len(samples)>16000*30:raise HTTPException(413,'Grave até 30 segundos.')
                segments,_=model.transcribe(samples,language='pt',beam_size=1,condition_on_previous_text=False)
                text=' '.join(s.text.strip() for s in segments).strip()
                if not text:raise HTTPException(422,'Nenhuma fala reconhecida.')
                return {'text':text[:800],'source':'local_whisper','notice':'Revise a transcrição e pressione Enviar; gravação não executa comandos.'}
        except HTTPException:raise
        except Exception:
            __import__('logging').getLogger('aether.voice').exception('Falha na transcricao local')
            raise HTTPException(422,'Não foi possível transcrever este áudio localmente. Consulte o terminal do Aether.')
        finally:lock.release()
    @api.post('/api/v1/voice/transcribe')
    async def transcribe_route(request:Request):
        raw=bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw)>8_000_000:raise HTTPException(413,'Áudio deve ter até 8 MB/30 segundos.')
        if not raw:raise HTTPException(422,'Áudio vazio.')
        return await run_in_threadpool(transcribe,bytes(raw))
    @api.post('/api/v1/voice/speak')
    def speak(body:Speech):
        try:
            return Response(voices.speak(body.text, body.voice),media_type='audio/wav',headers={'Cache-Control':'no-store'})
        except RuntimeError as exc:
            raise HTTPException(503,str(exc))
