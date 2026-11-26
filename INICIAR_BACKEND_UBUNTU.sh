#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -f .env.backend ]]; then
    echo 'Execute primeiro: bash PREPARAR_BACKEND_UBUNTU.sh'
    exit 1
fi
set -a
source ./.env.backend
set +a
backend_python="${AETHER_BACKEND_PYTHON:-./backend/.venv-cloud/bin/python}"
if [[ ! -x "$backend_python" ]]; then
    echo 'Ambiente Python não encontrado. Execute PREPARAR_BACKEND_UBUNTU.sh.'
    exit 1
fi
echo 'Backend protegido em http://127.0.0.1:8000; /healthz verifica o serviço.'
echo 'Para uso pelo Netlify, disponibilize a API por HTTPS. Ctrl+C encerra.'
exec "$backend_python" ./backend/serve_cloud.py --local
