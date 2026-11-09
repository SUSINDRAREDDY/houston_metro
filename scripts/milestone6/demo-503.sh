#!/usr/bin/env bash
set -euo pipefail
context=gke_metroai-vm-milestone-20260922_us-central1_metroai-gke
kubectl --context "$context" -n metroai exec -i deployment/metroai -c app -- python - <<'PY'
from urllib.error import HTTPError
from urllib.request import Request, urlopen

request = Request('http://127.0.0.1:8000/api/internal/demo-503', method='POST')
for _ in range(5):
    try:
        urlopen(request, timeout=10)
    except HTTPError as error:
        if error.code != 503:
            raise
        print(f'HTTP {error.code}  Request ID {error.headers["X-Request-ID"]}')
    else:
        raise SystemExit('Expected HTTP 503')
PY
