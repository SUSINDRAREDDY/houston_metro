"""Resolve AI place names to actual GTFS stops; never manufacture stop IDs."""
import re
import threading
import time
import unicodedata
from difflib import SequenceMatcher
from . import routing

ALIASES = {
    'uh': 'uh south university oaks', 'university of houston': 'uh south university oaks',
    'uh main campus': 'uh south university oaks', 'uh central': 'uh south university oaks',
    'downtown': 'central station', 'downtown houston': 'central station', 'central': 'central station',
    'medical center': 'dryden tmc', 'texas medical center': 'dryden tmc', 'tmc': 'dryden tmc',
    'fannin south': 'fannin south', 'fanin south': 'fannin south',
    'rice university': 'hermann park rice u', 'rice university station': 'hermann park rice u',
    'nrg': 'houston stadium', 'nrg park': 'houston stadium',
    'nrg stadium': 'houston stadium', 'stadium park astrodome': 'houston stadium',
}
_DIRECTION = re.compile(r'\b(?:nb|sb|eb|wb|northbound|southbound|eastbound|westbound)$')

def normalize(value):
    value=unicodedata.normalize('NFKD',value).encode('ascii','ignore').decode().lower()
    value=re.sub(r'\b(station|stn)\b',' ',value)
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',value).split())


def base_name(value):
    return _DIRECTION.sub('',normalize(value)).strip()


def close(a,b,meters=250):
    return routing.distance(a,b)<=meters


class ResolutionError(ValueError):
    def __init__(self,query,endpoint,ambiguous=False):
        self.code='ambiguous_place' if ambiguous else 'unmatched_place'
        self.query=query;self.endpoint=endpoint
        action='Use a more specific station name or select a stop in the controls.'
        super().__init__(f'Could not safely match the {endpoint} "{query}". {action}')


class Catalog:
    def __init__(self,rows):
        self.rows=[dict(r) for r in rows if str(r['location_type'] or '') in ('','0')]
        self.by_id={str(r['stop_id']):r for r in self.rows}
        self.groups={}
        for row in self.rows:
            name=row['stop_name'];parent=row.get('parent_station')
            # Do not merge opposite sides of a street merely because names match.
            station=bool(re.search(r'\b(?:stn|station)\b',name,re.I)) or base_name(name) in set(ALIASES.values())
            key=('parent:'+parent) if parent else ('station:'+base_name(name) if station and '@' not in name else 'stop:'+str(row['stop_id']))
            group=self.groups.setdefault(key,[])
            if group and not close(group[0],row):
                key+=':'+str(row['stop_id']);group=self.groups.setdefault(key,[])
            group.append(row)
        self.entries=[(key,base_name(rows[0]['stop_name']),rows) for key,rows in self.groups.items()]

    def _result(self,query,rows,kind):
        rows=sorted(rows,key=lambda r:(r['stop_name'],str(r['stop_id'])))
        return {'query':rows[0]['stop_name'],'input':query,'match':kind,
                'stops':[{k:r[k] for k in ('stop_id','stop_code','stop_name','stop_lat','stop_lon')} for r in rows]}

    def resolve(self,query,endpoint='place'):
        raw=query.strip();q=normalize(raw)
        if not q:raise ResolutionError(raw,endpoint)
        if raw in self.by_id:return self._result(raw,[self.by_id[raw]],'stop_id')
        exact=[r for r in self.rows if normalize(r['stop_name'])==q]
        if exact:
            if len(exact)>1 and (not all(close(exact[0],r) for r in exact) or '@' in raw):
                raise ResolutionError(raw,endpoint,True)
            return self._result(raw,exact,'exact')
        term=normalize(ALIASES.get(q,q))
        if term=='central':
            # Normalization removes "stn"; these are verified station platforms.
            matches=[r for r in self.rows if base_name(r['stop_name']) in ('central station capitol','central station rusk','central capitol','central rusk','central main')]
            if matches and all(close(matches[0],r,500) for r in matches):return self._result(raw,matches,'alias')
        matches=[entry for entry in self.entries if entry[1]==term]
        # Station suffixes such as "Station" are normalized, directions remain explicit.
        if len(matches)==1:return self._result(raw,matches[0][2],'alias' if q in ALIASES else 'station')
        if len(matches)>1:raise ResolutionError(raw,endpoint,True)
        if len(term)<5 or term.isdigit():raise ResolutionError(raw,endpoint)
        scored=[]
        for key,name,rows in self.entries:
            # Numeric street/stop identifiers must not change under fuzzy matching.
            if re.findall(r'\d+',term)!=re.findall(r'\d+',name):continue
            score=SequenceMatcher(None,term,name).ratio()
            # Broad one-word street names are never auto-selected from a longer name.
            if len(term.split())==1 and len(name.split())>1:continue
            scored.append((score,key,rows))
        scored.sort(key=lambda item:(-item[0],item[1]))
        if not scored or scored[0][0]<0.89:raise ResolutionError(raw,endpoint)
        if len(scored)>1 and scored[0][0]-scored[1][0]<0.08:raise ResolutionError(raw,endpoint,True)
        return self._result(raw,scored[0][2],'spelling')

    def hints(self,text):
        # A compact list of real station names plus relevant street stops grounds the AI.
        known=[rows[0]['stop_name'] for key,name,rows in self.entries if key.startswith(('station:','parent:'))]
        words=set(normalize(text).split())
        scores=[]
        for key,name,rows in self.entries:
            if key.startswith(('station:','parent:')):continue
            tokens=set(name.split());overlap=tokens & words
            if len(overlap)>=2:scores.append((len(overlap)/max(1,len(tokens)),rows[0]['stop_name']))
        scores.sort(reverse=True)
        return sorted(set(known))[:70]+[name for score,name in scores[:8]]

_lock=threading.Lock();_catalog=None;_loaded=0.0;_revision=None

def load():
    global _catalog,_loaded,_revision
    with _lock:
        if _catalog is not None and time.monotonic()-_loaded<60:return _catalog
        with routing.connect() as db:
            revision=db.execute("SELECT value FROM metadata WHERE key='sha256'").fetchone()
            revision=revision[0] if revision else None
            if _catalog is None or revision!=_revision:
                _catalog=Catalog(db.execute('SELECT stop_id,stop_code,stop_name,stop_lat,stop_lon,location_type,parent_station FROM stops'))
                _revision=revision
        _loaded=time.monotonic()
        return _catalog
