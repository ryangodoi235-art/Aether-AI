"""Start a single cloud/local API worker, respecting the hosting provider's PORT."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Backend protegido do Aether para o Netlify.')
    parser.add_argument('--local', action='store_true', help='Escuta somente 127.0.0.1; use atrás de um proxy HTTPS.')
    args = parser.parse_args()
    try:
        port = int(os.environ.get('PORT', '8000'))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        parser.error('PORT deve ser um inteiro entre 1 e 65535.')
    os.chdir(Path(__file__).resolve().parent)
    # Import before Uvicorn to fail clearly if the mandatory token is missing.
    from backend.app.cloud import app
    import uvicorn
    uvicorn.run(app, host='127.0.0.1' if args.local else '0.0.0.0', port=port, workers=1)


if __name__ == '__main__':
    main()
