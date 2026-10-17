import hashlib
import json
import os
import threading
import time
import logging
from datetime import datetime, timezone
import httpx
from .config import DATA
from . import database

PUBLIC_URL='https://www.ridemetro.org/metro-api/alerts'
API_URL='https://api.ridemetro.org/v2alerts/alerts'
CACHE=DATA/'alerts.json'

def refresh():
    from .secrets import get
    key=get('METRO_API_KEY')
    url=API_URL if key else PUBLIC_URL
    with httpx.Client(timeout=25) as client:
        r=client.get(url,headers={'Ocp-Apim-Subscription-Key':key} if key else {})
        r.raise_for_status();raw=r.json()
    if isinstance(raw,dict) and isinstance(raw.get('alerts'),list):raw=raw['alerts']
    if not isinstance(raw,list):raise ValueError('Unexpected alert response; previous alerts retained')
    alerts=[]
    for a in raw:
        if key:
            if 'header_text' not in a:raise ValueError('Unexpected subscription alert schema')
            routes=[str(s['route_id']) for s in a.get('affected_services',{}).get('services',[])]
            header=a['header_text'];description=a.get('description_text',a.get('service_effect_text',''))
            effect=a.get('effect_name','Service alert');updated=a.get('last_modified_dt');route_kind='id'
        else:
            if 'HeaderText' not in a:raise ValueError('Unexpected public alert schema')
            routes=[str(a['RouteId'])] if a.get('RouteId') else []
            header=a['HeaderText'];description=a.get('DescriptionText') or ''
            effect=a.get('EffectName','Service alert');updated=a.get('LastModified');route_kind='short_name'
        alerts.append({'id':hashlib.sha256((str(routes)+header).encode()).hexdigest()[:16],
            'routes':routes,'route_kind':route_kind,'header':header.strip(),'description':description.strip(),
            'effect':effect,'updated':updated,'periods':a.get('effect_periods',[])})
    result={'fetched_at':datetime.now(timezone.utc).isoformat(),'source':url,'alerts':alerts}
    if database.managed():
        database.state_put('metro_alerts', result)
    else:
        tmp=CACHE.with_suffix('.tmp');tmp.write_text(json.dumps(result));os.replace(tmp,CACHE)
    return result

def snapshot():
    if database.managed():
        data=database.state_get('metro_alerts')
    else:
        data=json.loads(CACHE.read_text()) if CACHE.exists() else None
    if not data:return {'status':'unavailable','fetched_at':None,'source':PUBLIC_URL,'alerts':[]}
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(data['fetched_at'])).total_seconds()
    data['status']='current' if age<=900 else 'stale'
    return data

def normalized(value):
    return value.lstrip('0') or '0'

def for_route(alerts,route):
    return [a for a in alerts if not a['routes'] or
        (route['route_id'] in a['routes'] if a['route_kind']=='id' else normalized(route['route_short_name']) in [normalized(r) for r in a['routes']])]

if __name__=='__main__':
    r=refresh();print(json.dumps({'fetched_at':r['fetched_at'],'count':len(r['alerts']),'source':r['source']}))


_refresh_lock = threading.Lock()
_last_attempt = 0.0

def ensure_current():
    global _last_attempt
    with _refresh_lock:
        if time.monotonic() - _last_attempt < 300:
            return
        _last_attempt = time.monotonic()
        try:
            refresh()
        except Exception:
            logging.warning('Alert refresh failed; cached alerts retain their freshness label')
