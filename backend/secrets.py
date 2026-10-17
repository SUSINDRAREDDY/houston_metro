"""Read credentials through Application Default Credentials; never write a file."""
import os
import threading
import time

SECRET_IDS = {
    'OPENROUTER_API_KEY': 'metroai-openrouter-api-key',
    'METRO_API_KEY': 'metroai-metro-api-key',
    'METRO_TRANSIT_DATA_API_KEY': 'metroai-transit-data-api-key',
    'DB_PASSWORD': 'metroai-db-password',
}
_cache = {}
_lock = threading.Lock()


def get(name):
    project = os.getenv('SECRET_PROJECT_ID')
    if not project:
        # Explicit environment variables support tests and local development.
        return os.getenv(name, '')
    if name not in SECRET_IDS:
        raise ValueError('Unknown credential name')
    with _lock:
        cached = _cache.get(name)
        if cached and time.monotonic() - cached[0] < 300:
            return cached[1]
        from google.cloud import secretmanager
        response = secretmanager.SecretManagerServiceClient().access_secret_version(
            request={'name': f'projects/{project}/secrets/{SECRET_IDS[name]}/versions/latest'},
            timeout=20,
        )
        value = response.payload.data.decode('utf-8')
        if not value:
            raise ValueError('Required secret is empty')
        _cache[name] = (time.monotonic(), value)
        return value
