#!/usr/bin/env bash
# GCE startup script. The VM must have metroai-runtime and cloud-platform scope.
set -euo pipefail
apt-get update -qq
apt-get install -y docker.io docker-compose-v2
systemctl enable --now docker
mkdir -p /opt/metroai
python3 - <<'PY'
import json,urllib.request
from pathlib import Path
metadata='http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token'
request=urllib.request.Request(metadata,headers={'Metadata-Flavor':'Google'})
token=json.load(urllib.request.urlopen(request,timeout=20))['access_token']
for name in ['docker-compose.milestone4.yml','start_milestone4.sh','metroai-milestone4.service']:
    url='https://storage.googleapis.com/metroai-vm-milestone-20260922-uploads/recovery/'+name
    request=urllib.request.Request(url,headers={'Authorization':'Bearer '+token})
    Path('/opt/metroai',name).write_bytes(urllib.request.urlopen(request,timeout=30).read())
PY
cp /opt/metroai/metroai-milestone4.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now metroai-milestone4
