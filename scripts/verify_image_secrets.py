"""Check an exported Docker image without printing credential values.

Usage: python3 scripts/verify_image_secrets.py /tmp/image.tar
Checks every saved layer, image configuration, and build history against
nonempty KEY/TOKEN/SECRET/PASSWORD values from the local .env file.
"""
import io
import gzip
import json
import re
import sys
import tarfile
import argparse
import base64
import subprocess
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('image_tar')
parser.add_argument('--secret-project')
args=parser.parse_args()
values = []
if args.secret_project:
    for identifier in ('metroai-openrouter-api-key','metroai-metro-api-key','metroai-transit-data-api-key','metroai-db-password','metroai-db-admin-password'):
        payload=subprocess.check_output(['gcloud','secrets','versions','access','latest','--secret='+identifier,'--project='+args.secret_project])
        if len(payload)<8:
            raise RuntimeError('Refusing incomplete credential scan')
        values.append(payload)
env = Path('.env')
if env.exists():
    for line in env.read_text().splitlines():
        m = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
        if m and re.search(r'KEY|TOKEN|SECRET|PASSWORD', m[1], re.I):
            value = m[2].strip().strip('\"\'')
            if len(value) >= 8:
                values.append(value.encode())
values = list(dict.fromkeys(values))
hits = 0
env_files = 0
files = 0
layer_bytes = 0
with tarfile.open(args.image_tar) as image:
    manifest = json.load(image.extractfile('manifest.json'))[0]
    config = image.extractfile(manifest['Config']).read()
    hits += sum(v in config for v in values)
    for name in manifest['Layers']:
        blob = image.extractfile(name).read()
        raw = gzip.decompress(blob) if blob[:2] == b'\x1f\x8b' else blob
        layer_bytes += len(raw)
        hits += sum(v in raw for v in values)
        with tarfile.open(fileobj=io.BytesIO(blob), mode='r:*') as layer:
            for member in layer:
                if member.isfile():
                    files += 1
                    if Path(member.name).name == '.env':
                        env_files += 1
    cfg = json.loads(config)
    baked_names = [e.split('=', 1)[0] for e in cfg.get('config', {}).get('Env', [])
                   if re.search(r'KEY|TOKEN|SECRET|PASSWORD', e.split('=', 1)[0], re.I)
                   and e.split('=', 1)[0] != 'GPG_KEY']
result = dict(layers=len(manifest['Layers']), files=files,
              runtime_credentials_checked=len(values), credential_matches=hits,
              dotenv_files=env_files, baked_credential_variable_names=baked_names,
              uncompressed_layer_tar_bytes=layer_bytes)
print(json.dumps(result, indent=2))
if hits or env_files or baked_names or not values:
    sys.exit(1)
