#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port "${PORT:-8000}"
