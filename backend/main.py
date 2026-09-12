import asyncio
import json
import logging
import time
from collections import defaultdict,deque
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Literal
import httpx
from fastapi import FastAPI,HTTPException,Query,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from . import alerts,intent,routing,ingest
from .config import ROOT,DB

async def refresh_loop():
    while True:
        try:await asyncio.to_thread(alerts.refresh)
        except Exception:logging.warning('Alert refresh failed; last successful snapshot retained')
        await asyncio.sleep(300)

async def schedule_loop():
    while True:
        await asyncio.sleep(86400)
        try:await asyncio.to_thread(ingest.download)
        except Exception:logging.warning('Schedule refresh failed; last validated feed retained')

@asynccontextmanager
async def lifespan(app):
    task=asyncio.create_task(refresh_loop())
    schedules=asyncio.create_task(schedule_loop())
    yield
    schedules.cancel()
    task.cancel()
    try:await task
    except asyncio.CancelledError:pass
    try:await schedules
    except asyncio.CancelledError:pass

app=FastAPI(title='MetroAI',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:3000','http://127.0.0.1:3000'],allow_methods=['GET','POST'],allow_headers=['Content-Type'])

@app.get('/api/health')
def health():return {'status':'ok' if DB.exists() else 'needs_data','timezone':'America/Chicago'}

@app.get('/api/status')
def status():
    if not DB.exists():return {'ready':False,'alerts':alerts.snapshot()}
    with routing.connect() as db:
        meta={r['key']:json.loads(r['value']) for r in db.execute('SELECT * FROM metadata')}
        coverage=db.execute('SELECT feed_start_date,feed_end_date FROM feed_info LIMIT 1').fetchone()
    a=alerts.snapshot()
    return {'ready':True,**meta,'coverage':list(coverage),'alerts':{'status':a['status'],'fetched_at':a['fetched_at'],'count':len(a['alerts']),'source':a['source']}}

@app.get('/api/stops')
def stops(q:str=Query(min_length=1,max_length=100)):
    try:
        with routing.connect() as db:return routing.stop_search(db,q)
    except ValueError as e:raise HTTPException(503,str(e))

@app.get('/api/routes')
def routes(q:str=Query(default='',max_length=100)):
    try:
        with routing.connect() as db:
            return [dict(r) for r in db.execute('SELECT * FROM routes WHERE route_short_name LIKE ? OR route_long_name LIKE ? ORDER BY CAST(route_short_name AS INTEGER) LIMIT 150',(f'%{q}%',f'%{q}%'))]
    except ValueError as e:raise HTTPException(503,str(e))

@app.get('/api/vehicles')
async def vehicles(route_id:str=Query(pattern=r'^[0-9]{1,4}$')):
    from .vehicles import positions
    return await positions(route_id)

@app.get('/api/alerts')
def get_alerts():return alerts.snapshot()

class ParseRequest(BaseModel):text:str=Field(min_length=5,max_length=800)
rate=defaultdict(deque)

@app.post('/api/interpret')
async def interpret(body:ParseRequest,request:Request):
    # Deliberately bounded public demo use; never rotate keys to evade provider limits.
    now=time.monotonic();host=request.client.host if request.client else 'unknown'
    for k in [host,'global']:
        while rate[k] and rate[k][0]<now-60:rate[k].popleft()
        if len(rate[k]) >= (5 if k==host else 15):raise HTTPException(429,'Too many AI requests. Please use the stop controls or try again shortly.')
    rate[host].append(now);rate['global'].append(now)
    try:return await intent.parse(body.text)
    except (ValueError,httpx.HTTPError) as e:
        message=str(e) if isinstance(e,ValueError) else 'AI request timed out. Use the stop and time controls.'
        raise HTTPException(503,message)

class JourneyRequest(BaseModel):
    origin_ids:list[str]=Field(min_length=1,max_length=12)
    destination_ids:list[str]=Field(min_length=1,max_length=12)
    departure:datetime
    mode:Literal['any','bus','rail']='any'
    max_transfers:Literal[0,1]=1
    prefer:Literal['fastest','fewer_transfers']='fastest'
    avoid_alerts:bool=False

@app.post('/api/journeys')
def journeys(body:JourneyRequest):
    if body.departure.tzinfo is None:raise HTTPException(422,'Departure must include a timezone offset.')
    a=alerts.snapshot()
    if body.avoid_alerts and a['status']!='current':raise HTTPException(503,'Current alerts are unavailable. Turn off avoid alerts or try again later.')
    try:
        with routing.connect() as db:
            route_rows=[dict(r) for r in db.execute('SELECT * FROM routes')]
            matched={r['route_id']:alerts.for_route(a['alerts'],r) for r in route_rows}
            exclude=[rid for rid,items in matched.items() if items] if body.avoid_alerts else []
            options=routing.plan(db,body.origin_ids,body.destination_ids,body.departure,body.mode,body.max_transfers,body.prefer,exclude)
            for journey in options:
                found={x['id']:x for leg in journey['legs'] for x in matched.get(leg['route_id'],[])}
                journey['alerts']=list(found.values())
        return {'journeys':options,'alerts_status':a['status'],'alerts_fetched_at':a['fetched_at'],
            'notice':'Scheduled times in Houston time. Alerts describe current conditions; future disruptions may change.',
            'search_window_hours':4,'transfer_policy':'Same stop or GTFS-declared transfer; minimum 3 minutes; maximum wait 60 minutes.'}
    except ValueError as e:raise HTTPException(422,str(e))

if (ROOT/'frontend/out').exists():app.mount('/',StaticFiles(directory=ROOT/'frontend/out',html=True),name='frontend')
