"""Run inside the production container; prints evidence without credential values."""
import json
import os
from pathlib import Path
import google.auth
from backend import database

names=('agency','calendar','calendar_dates','feed_info','metadata','routes','shapes',
       'stop_times','stops','transfers','trips','gis_stations','gis_metadata','uploads')
with database.connect() as db:
    counts={name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in names}
    migrations=[dict(r) for r in db.execute('SELECT version,sha256,applied_at FROM schema_migrations')]
    identity=db.execute('SELECT current_user,inet_server_addr()::text,inet_client_addr()::text').fetchone()
credentials,project=google.auth.default()
files=[str(path) for base in ('/app','/home','/tmp') for path in Path(base).rglob('.env*') if path.is_file()]
secret_environment_names=[name for name in os.environ if any(token in name for token in ('API_KEY','PASSWORD','GOOGLE_APPLICATION_CREDENTIALS'))]
result={'database_backend':'postgresql','database_user':identity[0],
    'connection_transport':'Cloud SQL Python Connector with IPTypes.PRIVATE',
    'instance_connection_name':os.environ.get('INSTANCE_CONNECTION_NAME'),
    'postgres_backend_socket_address':identity[1],
    'table_counts':counts,'migrations':migrations,
    'credential_type':type(credentials).__module__+'.'+type(credentials).__name__,
    'dotenv_files':files,'secret_environment_variable_names':secret_environment_names,
    'upload_bucket':os.environ.get('UPLOAD_BUCKET')}
print(json.dumps(result,indent=2,default=str))
database.engine().dispose()
if database._connector is not None:
    database._connector.close()
if files or secret_environment_names or not database.managed():
    raise SystemExit('Deployment verification failed')
