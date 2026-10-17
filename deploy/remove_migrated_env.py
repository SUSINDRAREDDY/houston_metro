"""Remove only a MetroAI .env whose credentials match Secret Manager.

Run on the VM after deploying Milestone 4. Uses metadata identity; neither the
environment file contents nor secret values are printed or copied elsewhere.
"""
import base64
import json
import urllib.request
from pathlib import Path

project='metroai-vm-milestone-20260922'
path=Path('/home/sunny/metroai/.env')
if not path.exists():
    print('PASS: old deployment .env already absent')
    raise SystemExit(0)
request=urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token',headers={'Metadata-Flavor':'Google'})
token=json.load(urllib.request.urlopen(request,timeout=15))['access_token']
values={}
for line in path.read_text().splitlines():
    if '=' in line and not line.strip().startswith('#'):
        name,value=line.split('=',1);values[name.strip()]=value.strip().strip('\"\'')
mapping={'OPENROUTER_API_KEY':'metroai-openrouter-api-key','METRO_API_KEY':'metroai-metro-api-key','METRO_TRANSIT_DATA_API_KEY':'metroai-transit-data-api-key'}
for name,identifier in mapping.items():
    request=urllib.request.Request(f'https://secretmanager.googleapis.com/v1/projects/{project}/secrets/{identifier}/versions/latest:access',headers={'Authorization':'Bearer '+token})
    remote=base64.b64decode(json.load(urllib.request.urlopen(request,timeout=20))['payload']['data']).decode()
    if values.get(name)!=remote:
        raise RuntimeError('Credential mismatch; old environment file retained: '+name)
path.unlink()
print('PASS: three credentials match Secret Manager; old deployment .env removed')
