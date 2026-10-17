"""One-time operator migration: .env credentials -> Secret Manager, no values logged.

Uses the operator's existing gcloud login (not a service account key). The
application itself reads secrets using its attached VM service account.
"""
import base64
import json
import secrets
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

PROJECT = 'metroai-vm-milestone-20260922'
ACCOUNT = f'serviceAccount:metroai-runtime@{PROJECT}.iam.gserviceaccount.com'
NAMES = {'OPENROUTER_API_KEY':'metroai-openrouter-api-key', 'METRO_API_KEY':'metroai-metro-api-key',
         'METRO_TRANSIT_DATA_API_KEY':'metroai-transit-data-api-key'}


def api(method, url, payload=None):
    token = subprocess.check_output(['gcloud','auth','print-access-token'], text=True).strip()
    request = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Authorization':'Bearer '+token, 'Content-Type':'application/json'}, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def put(name, value):
    base = f'https://secretmanager.googleapis.com/v1/projects/{PROJECT}'
    try:
        api('POST',base+'/secrets?secretId='+name, {'replication':{'automatic':{}}})
    except urllib.error.HTTPError as error:
        if error.code != 409:
            raise RuntimeError('Secret creation failed: '+name) from None
        # Idempotent: do not overwrite an existing secret version during recovery.
        print('Existing secret retained:', name)
        return
    api('POST',base+'/secrets/'+name+':addVersion', {'payload':{'data':base64.b64encode(value.encode()).decode()}})
    print('Secret stored:', name)


if __name__ == '__main__':
    values = {}
    for line in Path('.env').read_text().splitlines():
        if '=' in line and not line.strip().startswith('#'):
            name,value = line.split('=',1)
            values[name.strip()] = value.strip().strip('\"\'')
    for name, identifier in NAMES.items():
        if not values.get(name):
            raise RuntimeError('Missing local credential: '+name)
        put(identifier, values[name])
    put('metroai-db-password', secrets.token_urlsafe(40))
    put('metroai-db-admin-password', secrets.token_urlsafe(40))
    for identifier in list(NAMES.values()) + ['metroai-db-password']:
        subprocess.run(['gcloud','secrets','add-iam-policy-binding',identifier,'--project='+PROJECT,
            '--member='+ACCOUNT,'--role=roles/secretmanager.secretAccessor','--quiet','--format=value(etag)'],check=True)
