#!/usr/bin/env bash
# Start de app altijd met de Python uit de venv, ook als de terminal
# de virtuele omgeving niet geactiveerd heeft.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x "env/bin/python" ]; then
    echo "Fout: env/bin/python niet gevonden." >&2
    echo "Maak eerst de virtuele omgeving aan met: python3.12 setup.py (optie 1)" >&2
    exit 1
fi

exec "env/bin/python" app.py "$@"
