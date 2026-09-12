#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python -m backend.ingest
.venv/bin/python -m backend.alerts
