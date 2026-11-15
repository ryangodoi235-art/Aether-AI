from pathlib import Path
from urllib.request import urlretrieve
import winsound
import soundfile as sf
from kokoro_onnx import Kokoro

pasta = Path(__file__).resolve().parent / "amostras_kokoro"
pasta.mkdir(exist_ok=True)

base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
for nome in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
    destino = pasta / nome
    if not destino.exists():
        print(f"Baixando {nome}. Aguarde...", flush=True)
        temporario = destino.with_suffix(destino.suffix + ".part")
        urlretrieve(base + nome, temporario)
        temporario.replace(destino)

kokoro = Kokoro(
    str(pasta / "kokoro-v1.0.onnx"),
    str(pasta / "voices-v1.0.bin"),
)

texto = (
    "Olá, Ryan. Eu sou o Aether. "
    "Estou aqui para ajudar você a cuidar da sua casa. "
    "Pode ficar tranquilo. Vamos fazer uma coisa de cada vez. "
    "Quer que eu acenda a luz da sala?"
)

for voz in ("pm_alex", "pm_santa"):
    print(f"Gerando a voz {voz}...", flush=True)
    audio, taxa = kokoro.create(
        texto, voice=voz, speed=0.95, lang="pt-br"
    )
    arquivo = pasta / f"{voz}.wav"
    sf.write(str(arquivo), audio, taxa, subtype="PCM_16")
    print(f"Reproduzindo: {arquivo}", flush=True)
    winsound.PlaySound(str(arquivo), winsound.SND_FILENAME)

print("Concluído. As duas amostras estão em:", pasta)
