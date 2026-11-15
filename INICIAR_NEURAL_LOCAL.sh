#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
PYTHON=./backend/.venv-ubuntu/bin/python
if [[ ! -x "$PYTHON" ]]; then echo 'Ambiente backend/.venv-ubuntu não encontrado.'; exit 1; fi
exec "$PYTHON" ./backend/iniciar_neural_local.py
