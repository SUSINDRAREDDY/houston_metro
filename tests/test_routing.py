from datetime import datetime
import pytest
from backend import routing
from backend.ingest import seconds


def test_after_midnight_time():
    assert seconds('25:10:00') == 90600
    with pytest.raises(ValueError): seconds('12:61:00')


def test_real_direct_and_transfer():
    with routing.connect() as db:
        o=[s['stop_id'] for s in routing.stop_search(db,'UH')]
        d=[s['stop_id'] for s in routing.stop_search(db,'Downtown')]
        result=routing.plan(db,o,d,datetime.fromisoformat('2026-09-12T17:00:00-05:00'))
        assert any(j['transfers']==0 for j in result)
        assert any(j['transfers']==1 for j in result)
        for j in result:
            for leg in j['legs']:
                rows=db.execute('SELECT departure_secs,arrival_secs,stop_id FROM stop_times WHERE trip_id=? ORDER BY stop_sequence',(leg['trip_id'],)).fetchall()
                assert any(r['stop_id']==leg['from']['stop_id'] for r in rows)
                assert any(r['stop_id']==leg['to']['stop_id'] for r in rows)
                assert datetime.fromisoformat(leg['departure'])>=datetime.fromisoformat('2026-09-12T17:00:00-05:00')
            if j['transfers']:
                assert (datetime.fromisoformat(j['legs'][1]['departure'])-datetime.fromisoformat(j['legs'][0]['arrival'])).total_seconds()>=180


def test_mode_and_direct_only():
    with routing.connect() as db:
        result=routing.plan(db,['25080'],['25054'],datetime.fromisoformat('2026-09-12T17:00:00-05:00'),mode='rail',max_transfers=0)
        assert result
        assert all(j['transfers']==0 and all(l['mode']=='rail' for l in j['legs']) for j in result)


def test_outside_coverage():
    with routing.connect() as db:
        with pytest.raises(ValueError,match='coverage'):
            routing.plan(db,['25080'],['25054'],datetime.fromisoformat('2030-09-12T17:00:00-05:00'))


def test_calendar_exceptions():
    import sqlite3
    db=sqlite3.connect(':memory:')
    db.executescript('CREATE TABLE calendar(service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date); CREATE TABLE calendar_dates(service_id,date,exception_type);')
    db.execute("INSERT INTO calendar VALUES ('regular',1,1,1,1,1,1,1,'20260101','20261231')")
    db.executemany('INSERT INTO calendar_dates VALUES (?,?,?)',[('regular','20260912',2),('special','20260912',1)])
    assert routing.active_services(db,datetime(2026,9,12).date())=={'special'}

def test_downtown_includes_red_line():
    import sqlite3
    from backend.routing import stop_search
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE stops(stop_id TEXT,stop_code TEXT,stop_name TEXT,stop_lat REAL,stop_lon REAL)')
    for i,name in enumerate(['Central Station Capitol WB','Central Station Rusk EB','Central Stn Main NB','Central Stn Main SB','Fulton North Central SB']):
        db.execute('INSERT INTO stops VALUES (?,?,?,?,?)',(str(i),str(i),name,29.75,-95.36))
    assert len(stop_search(db,'Downtown'))==4
    db.close()
