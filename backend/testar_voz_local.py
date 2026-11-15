"""Exercise installed Whisper and Piper with synthesized Portuguese, no microphone."""
import os,sys,subprocess,tempfile,wave,json,unicodedata
from pathlib import Path
root=Path(__file__).resolve().parent
phrase='Aether pronto. Ligue a luz do quarto.'
try:
 from faster_whisper import WhisperModel
 from faster_whisper.audio import decode_audio
 whisper=Path(os.environ.get('AETHER_WHISPER_MODEL',root/'models/whisper-tiny'))
 piper=Path(os.environ.get('AETHER_PIPER_MODEL',root/'models/pt_BR-faber-medium.onnx'))
 with tempfile.TemporaryDirectory() as temp:
  wav=Path(temp)/'teste.wav'
  subprocess.run([sys.executable,'-m','piper','-m',str(piper),'-f',str(wav)],input=phrase.encode(),check=True,timeout=120,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
  samples=decode_audio(str(wav),sampling_rate=16000)
  if len(samples)<1600:raise RuntimeError('Áudio gerado vazio ou curto demais.')
  model=WhisperModel(str(whisper),device='cpu',compute_type='int8',local_files_only=True)
  segments,_=model.transcribe(samples,language='pt',beam_size=1)
  text=' '.join(s.text for s in segments).strip()
  normal=''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c)!='Mn')
  if not all(w in normal for w in ['luz','quarto']):raise RuntimeError('Transcrição não preservou o comando: '+text)
 print('Piper e Whisper executaram o teste de áudio sintético. Transcrição:',text)
 print('Ainda é necessário testar seu microfone e a reprodução automática no navegador.')
except Exception as e:
 print('Teste de voz falhou:',str(e));sys.exit(1)
