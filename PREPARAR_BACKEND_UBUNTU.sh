#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
python3 -m venv backend/.venv-cloud
backend/.venv-cloud/bin/python -m pip install -r backend/requirements-cloud.txt
backend/.venv-cloud/bin/python - <<'PY'
import os
import secrets
from pathlib import Path

target = Path('.env.backend')
try:
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
except FileExistsError:
    print('.env.backend já existe; token e configurações preservados.')
else:
    with os.fdopen(descriptor, 'w') as output:
        output.write('AETHER_API_TOKEN=' + secrets.token_hex(32) + '\n')
        output.write('AETHER_LOCAL_NLU=1\nAETHER_GENERAL_LLM=1\nPORT=8000\n')
    print('Token criado em .env.backend, com acesso restrito ao proprietário.')
print('Execute: bash INICIAR_BACKEND_UBUNTU.sh')
print('Nunca envie .env.backend para o GitHub ou para o chat.')
PY
