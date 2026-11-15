"""Compatibility launcher: this now starts the local Ollama interpreter."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name('iniciar_local.py')),run_name='__main__')
