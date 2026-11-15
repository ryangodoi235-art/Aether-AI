import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:11434"
MODEL = "qwen2.5:3b"


def models():
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({})
    )
    with opener.open(URL + "/api/tags", timeout=3) as response:
        return json.load(response).get("models", [])


def main():
    owned = None
    try:
        # Confere a porta antes de iniciar outro servidor.
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", 8000))
            except OSError:
                print("A porta 8000 esta ocupada. Encerre o Aether anterior.")
                return 1

        try:
            available = models()
        except Exception:
            executable = shutil.which("ollama")
            if not executable:
                print("Instale o Ollama para Linux antes de continuar.")
                print("Depois execute: ollama pull " + MODEL)
                return 1

            owned = subprocess.Popen(
                [executable, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(30):
                try:
                    available = models()
                    break
                except Exception:
                    if owned.poll() is not None:
                        print("O Ollama nao conseguiu iniciar.")
                        return 1
                    time.sleep(1)
            else:
                print("O Ollama nao respondeu a tempo.")
                return 1

        if not any(item.get("name") == MODEL for item in available):
            print("Modelo ausente. Execute: ollama pull " + MODEL)
            return 1

        print("Abra http://127.0.0.1:8000/painel")
        print("Ctrl+C encerra o Aether.")
        return subprocess.call(
            [
                sys.executable, "-m", "uvicorn",
                "backend.app.main:app",
                "--host", "127.0.0.1",
                "--port", "8000",
            ],
            cwd=ROOT,
        )
    except KeyboardInterrupt:
        return 0
    finally:
        if owned is not None and owned.poll() is None:
            owned.terminate()
            try:
                owned.wait(timeout=5)
            except subprocess.TimeoutExpired:
                owned.kill()
                owned.wait()


if __name__ == "__main__":
    raise SystemExit(main())
