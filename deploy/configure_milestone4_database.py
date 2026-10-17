"""Operator setup: initialize managed DB users from Secret Manager, no key files."""
import base64
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bootstrap_milestone4_secrets import api, PROJECT


def wait(operation):
    for _ in range(60):
        status=api('GET', f'https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/operations/{operation["name"]}')
        if status['status']=='DONE':
            if status.get('error'):
                raise RuntimeError('Database configuration operation failed')
            return
        time.sleep(2)
    raise RuntimeError('Database operation still pending')


def value(name):
    data=api('GET', f'https://secretmanager.googleapis.com/v1/projects/{PROJECT}/secrets/{name}/versions/latest:access')
    return base64.b64decode(data['payload']['data']).decode()


if __name__=='__main__':
    base=f'https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/instances/metroai-postgres'
    wait(api('PUT',base+'/users?name=postgres',{'name':'postgres','password':value('metroai-db-admin-password')}))
    print('Administrator credential initialized from Secret Manager.')
    wait(api('POST',base+'/users',{'name':'metroai_app','password':value('metroai-db-password')}))
    print('Application credential initialized from Secret Manager.')
    wait(api('POST',base+'/databases',{'name':'metroai'}))
    print('Managed database created.')
