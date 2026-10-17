#!/usr/bin/env bash
# Run on a replacement VM in metroai-vpc with the metroai-runtime identity.
# Docker + the Compose plugin must be installed. No database or secret files needed.
set -euo pipefail
cd "$(dirname "$0")"
# The short-lived registry login is discarded after pulling the image.
export DOCKER_CONFIG
DOCKER_CONFIG=$(mktemp -d)
trap 'rm -rf "$DOCKER_CONFIG"' EXIT
python3 - <<'PY' | docker login --username oauth2accesstoken --password-stdin us-central1-docker.pkg.dev
import json,urllib.request
request=urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',headers={'Metadata-Flavor':'Google'})
with urllib.request.urlopen(request,timeout=15) as response:
    print(json.load(response)['access_token'])
PY
docker compose -p metroai-m4 -f docker-compose.milestone4.yml pull
docker compose -p metroai-m4 -f docker-compose.milestone4.yml up -d --no-build
docker compose -p metroai-m4 -f docker-compose.milestone4.yml ps
