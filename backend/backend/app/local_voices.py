"""Two local Brazilian Kokoro voices. Never downloads models during synthesis."""
import io
import importlib.util
import shutil
import threading
from pathlib import Path

class LocalVoices:
    IDS={'female':'pf_dora','male':'pm_alex'}
    def __init__(self,root):
        self.folder=Path(root)/'models/kokoro'
        self.lock=threading.Lock()
        self.engine=None
        self.g2p=None
    def ready(self):
        return all((self.folder/f).is_file() for f in ('kokoro-v1.0.onnx','voices-v1.0.bin')) and all(importlib.util.find_spec(m) is not None for m in ('kokoro_onnx','misaki','soundfile')) and shutil.which('espeak-ng') is not None
    def options(self):
        ready=self.ready()
        return [{'id':k,'name':n,'ready':ready} for k,n in [('female','Dora · feminina'),('male','Alex · masculina')]]
    def speak(self,text,voice='male'):
        if voice not in self.IDS:raise RuntimeError('Escolha female ou male.')
        if not self.ready():raise RuntimeError('Prepare as duas vozes com preparar_duas_vozes.py e instale espeak-ng.')
        with self.lock:
            try:
                if self.engine is None:
                    # AETHER_ESPEAK_UBUNTU
                    import ctypes.util
                    import subprocess
                    import espeakng_loader
                    library = ctypes.util.find_library("espeak-ng")
                    files = subprocess.check_output(
                        ["dpkg", "-L", "espeak-ng-data"], text=True
                    ).splitlines()
                    phontab = next(
                        (Path(f) for f in files
                         if f.endswith("/phontab") and Path(f).is_file()),
                        None
                    )
                    if not library or phontab is None:
                        raise RuntimeError("Instalação do eSpeak Ubuntu incompleta.")
                    espeakng_loader.get_library_path = lambda: library
                    espeakng_loader.get_data_path = lambda: str(phontab.parent)
                    from kokoro_onnx import Kokoro
                    from misaki.espeak import EspeakG2P
                    self.engine=Kokoro(str(self.folder/'kokoro-v1.0.onnx'),str(self.folder/'voices-v1.0.bin'))
                    self.g2p=EspeakG2P(language='pt-br')
                import soundfile as sf
                phonemes,_=self.g2p(text)
                samples,rate=self.engine.create(phonemes,self.IDS[voice],speed=0.92,is_phonemes=True)
                out=io.BytesIO()
                sf.write(out,samples,rate,format='WAV',subtype='PCM_16')
                raw=out.getvalue()
                if not raw or len(raw)>10_000_000:raise ValueError('Áudio fora do limite')
                return raw
            except Exception as exc:
                self.engine=None;self.g2p=None
                raise RuntimeError('Falha na síntese local. Execute preparar_duas_vozes.py --testar; veja os detalhes no terminal.') from exc
