import pytest
from backend.stations import Catalog,ResolutionError

@pytest.fixture
def catalog():
    names=[('u1','Uh South University Oaks NB',29.71615,-95.34116),('u2','Uh South University Oaks SB',29.71609,-95.34119),
           ('f1','Fannin South Stn NB',29.67358,-95.40280),('f2','Fannin South Stn SB',29.67358,-95.40286),
           ('park','Fannin South PR',29.67381,-95.40213),('wrong','Fannin St @ Southmore Blvd',29.72816,-95.38651),
           ('d1','Central Station Capitol WB',29.759,-95.364),('d2','Central Station Rusk EB',29.759,-95.3641),
           ('d3','Central Stn Main NB',29.759,-95.3642),('d4','Central Stn Main SB',29.759,-95.3643),
           ('r1','Hermann Park/Rice U Stn NB',29.721,-95.390),('r2','Hermann Park/Rice U Stn SB',29.7211,-95.390),
           ('w1','Wheeler Stn NB',29.73,-95.38),('w2','Wheeler Stn SB',29.7301,-95.38),
           ('s1','Houston Stadium NB',29.69,-95.403),('s2','Houston Stadium SB',29.6901,-95.403),
           ('a','Main St @ First St',29.7,-95.4),('b','Main St @ First St',29.7001,-95.4),
           ('n','Westheimer Rd @ 123 St',29.7,-95.3)]
    return Catalog([{'stop_id':id,'stop_code':id,'stop_name':name,'stop_lat':lat,'stop_lon':lon,'location_type':'0','parent_station':''} for id,name,lat,lon in names])

@pytest.mark.parametrize('name',['UH','University of Houston','UH main campus','uh central'])
def test_uh_aliases_are_real_platforms(catalog,name):
    assert {s['stop_id'] for s in catalog.resolve(name)['stops']}=={'u1','u2'}

@pytest.mark.parametrize('name',['Fannin South','fanin south','Fannin South Station','fannn south','Fannin Soth','  FANNIN   SOUTH  '])
def test_fannin_typos_never_select_southmore_or_park(catalog,name):
    assert {s['stop_id'] for s in catalog.resolve(name)['stops']}=={'f1','f2'}

@pytest.mark.parametrize('name',['Downtown','downtown houston','Central Station'])
def test_downtown_includes_the_verified_station_complex(catalog,name):
    assert {s['stop_id'] for s in catalog.resolve(name)['stops']}=={'d1','d2','d3','d4'}

@pytest.mark.parametrize('name',['NRG','NRG Stadium','Stadium Park Astrodome'])
def test_stadium_alias_uses_current_feed_name(catalog,name):
    assert {s['stop_id'] for s in catalog.resolve(name)['stops']}=={'s1','s2'}

@pytest.mark.parametrize('name',['Wheeler','Wheeler Station','Rice University'])
def test_named_station_groups(catalog,name):
    assert len(catalog.resolve(name)['stops'])==2

def test_explicit_platform_and_id_are_preserved(catalog):
    assert [s['stop_id'] for s in catalog.resolve('Fannin South Stn SB')['stops']]==['f2']
    assert [s['stop_id'] for s in catalog.resolve('f1')['stops']]==['f1']

@pytest.mark.parametrize('name',['Fannin','neverland','Westheimer Rd @ 124 St','Main St @ First St'])
def test_unknown_broad_numeric_or_ambiguous_places_are_not_guessed(catalog,name):
    with pytest.raises(ResolutionError):catalog.resolve(name)

def test_hints_are_actual_feed_names(catalog):
    hints=catalog.hints('Take me from UH to fanin south')
    assert 'Fannin South Stn NB' in hints
    assert all(name in {r['stop_name'] for r in catalog.rows} for name in hints)

def test_far_apart_station_names_not_merged():
    rows=[{'stop_id':str(i),'stop_code':str(i),'stop_name':'Example Station '+direction,'stop_lat':lat,'stop_lon':-95.4,'location_type':'0','parent_station':''} for i,direction,lat in [(1,'NB',29.7),(2,'SB',29.9)]]
    with pytest.raises(ResolutionError):Catalog(rows).resolve('Example Station')
