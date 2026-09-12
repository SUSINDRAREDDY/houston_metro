"""Import the public METRO rail station GIS layer as a separate reference database."""
import json,sqlite3,os
from datetime import datetime,timezone
import httpx
from .config import DATA
URL='https://services5.arcgis.com/p8QKnlioaN3sruqA/arcgis/rest/services/METRO_transit_layers/FeatureServer/0/query'
def refresh():
    r=httpx.get(URL,params={'where':'1=1','outFields':'*','outSR':4326,'f':'geojson'},timeout=30);r.raise_for_status();data=r.json()
    if data.get('type')!='FeatureCollection' or not data.get('features'):raise ValueError('Invalid GIS response')
    if data.get('exceededTransferLimit'):raise ValueError('GIS response is truncated')
    stage=DATA/'gis.building.sqlite3';stage.unlink(missing_ok=True)
    with sqlite3.connect(stage) as db:
        db.execute('CREATE TABLE stations(id TEXT PRIMARY KEY,name TEXT,longitude REAL,latitude REAL,properties TEXT)')
        for f in data['features']:
            lon,lat=f['geometry']['coordinates'][:2]
            if not (-96<lon<-94 and 29<lat<31):raise ValueError('Unexpected GIS coordinates')
            db.execute('INSERT INTO stations VALUES (?,?,?,?,?)',(str(f['id']),f['properties']['Stat_Name'],lon,lat,json.dumps(f['properties'])))
        db.execute('CREATE TABLE metadata(source TEXT,fetched_at TEXT)')
        db.execute('INSERT INTO metadata VALUES (?,?)',(URL,datetime.now(timezone.utc).isoformat()))
    os.replace(stage,DATA/'gis.sqlite3')
    print(f"Imported {len(data['features'])} GIS stations")
if __name__=='__main__':refresh()
