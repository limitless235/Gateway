#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/gateway"

if [[ ! -d .venv ]]; then
  echo "Creating .venv with Python 3.13 via uv..."
  uv venv --python 3.13 .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  uv pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export PYTHONPATH="$ROOT/gateway${PYTHONPATH:+:$PYTHONPATH}"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload