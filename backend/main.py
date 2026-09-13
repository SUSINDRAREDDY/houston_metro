import asyncio
import json
import logging
import os
import time
from collections import defaultdict,deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Literal
import httpx
from fastapi import FastAPI,HTTPException,Query,Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from . import alerts,intent,routing,ingest,cloud_data,connected
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
    tasks=[]
    if cloud_data.enabled():
        await asyncio.to_thread(cloud_data.sync, True)
    if not os.getenv('K_SERVICE') and not cloud_data.enabled():
        tasks=[asyncio.create_task(refresh_loop()),asyncio.create_task(schedule_loop())]
    try:
        yield
    finally:
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)

app=FastAPI(title='MetroAI',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:3000,http://127.0.0.1:3000').split(','),allow_methods=['GET','POST'],allow_headers=['Content-Type'])

@app.middleware('http')
async def cloud_refresh(request, call_next):
    if request.url.path.startswith('/api/') and request.url.path != '/api/health':
        if cloud_data.enabled():
            await asyncio.to_thread(cloud_data.sync)
        if os.getenv('K_SERVICE') or cloud_data.enabled():
            if request.url.path in ('/api/status','/api/alerts','/api/journeys'):
                await asyncio.to_thread(alerts.ensure_current)
    return await call_next(request)

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
    max_transfers:Literal[0,1,2,3]=1
    leave_now:bool=False
    allow_walking:bool=True
    prefer:Literal['fastest','fewer_transfers']='fastest'
    avoid_alerts:bool=False

@app.post('/api/journeys')
async def journeys(body:JourneyRequest):
    if body.departure.tzinfo is None:raise HTTPException(422,'Departure must include a timezone offset.')
    now=datetime.now(routing.TZ)
    if body.leave_now:body.departure=now
    elif body.departure<now-timedelta(minutes=1):raise HTTPException(422,'That departure time has passed. Choose Leave now or a future time.')
    a=alerts.snapshot()
    if body.avoid_alerts and a['status']!='current':raise HTTPException(503,'Current alerts are unavailable. Turn off avoid alerts or try again later.')
    try:
        with routing.connect() as db:
            route_rows=[dict(r) for r in db.execute('SELECT * FROM routes')]
            matched={r['route_id']:alerts.for_route(a['alerts'],r) for r in route_rows}
            exclude=[rid for rid,items in matched.items() if items] if body.avoid_alerts else []
            if body.allow_walking:
                points={r['stop_id']:dict(r) for r in db.execute('SELECT * FROM stops')}
                if any(s not in points for s in body.origin_ids+body.destination_ids):raise ValueError('Choose valid stops.')
                options=await connected.plan(points[body.origin_ids[0]],points[body.destination_ids[0]],body.departure,body.mode,body.max_transfers,body.prefer,exclude,body.avoid_alerts)
            else:
                if body.max_transfers>1:raise ValueError('Enable walking and connected journeys for more than one transfer.')
                options=routing.plan(db,body.origin_ids,body.destination_ids,body.departure,body.mode,body.max_transfers,body.prefer,exclude)
            for journey in options:
                colors={r['route_id']:r['route_color'] for r in route_rows}
                for leg in journey['legs']:leg['color']=colors.get(leg['route_id'],'')
                found={x['id']:x for leg in journey['legs'] for x in matched.get(leg['route_id'],[])}
                journey['alerts']=list({x['header'].strip().lower():x for x in journey.get('alerts',[])+list(found.values())}.values())
        return {'journeys':options,'alerts_status':a['status'],'alerts_fetched_at':a['fetched_at'],
            'searched_departure':body.departure.isoformat(),'empty_message':'No bus or rail journey matches this time and your preferences within the next four hours. Try another time or allow more transfers.' if not options else None,
            'notice':'Houston time. Connected journeys use METRO planner paths and available live updates; local journeys use schedules.',
            'search_window_hours':4,'transfer_policy':('METRO planner connections; up to 3 transfers and 1.2 km total walking.' if body.allow_walking else 'Same stop or GTFS-declared transfer; minimum 3 minutes; maximum wait 60 minutes.')}
    except ValueError as e:raise HTTPException(422,str(e))

if (ROOT/'frontend/out').exists():app.mount('/',StaticFiles(directory=ROOT/'frontend/out',html=True),name='frontend')
