'use client';
import {useEffect,useMemo,useRef,useState,type CSSProperties} from 'react';
import {ArrowRight,ArrowDownUp,BusFront,TrainFront,MapPin,Clock3,ArrowUpRight,Sparkles,Search,TriangleAlert,ChevronDown,Navigation,Footprints,Route as RouteIcon,LoaderCircle} from 'lucide-react';
import type {Map as LeafletMap,LayerGroup} from 'leaflet';
import FilesPanel from './FilesPanel';

type Stop={stop_id:string;stop_name:string;stop_lat:number;stop_lon:number;stop_code:string};
type Endpoint={query:string;stops:Stop[]};
type Alert={id:string;header:string;description:string;routes:string[];effect:string};
type Leg={color?:string;route:string;route_id:string;name:string;mode:string;headsign:string;from:Stop;to:Stop;departure:string;arrival:string;stop_count:number|null;distance_meters?:number;steps?:{distance:number;relativeDirection:string;streetName:string}[];realtime?:boolean;geometry:number[][];stops:Stop[]};
type Journey={travel_modes?:string;highlights?:string[];legs:Leg[];departure:string;arrival:string;duration_minutes:number;transfers:number;transfer_wait_minutes:number;walking_meters?:number;source?:string;timing?:string;alerts:Alert[]};
type Status={ready:boolean;counts?:Record<string,number>;coverage?:string[];alerts?:{status:string;count:number;fetched_at:string}};
const API=typeof window!=='undefined'&&window.location.port==='3000'?'http://127.0.0.1:8000':'';
async function api(path:string,body?:unknown,signal?:AbortSignal){
 const controller=new AbortController();const cancel=()=>controller.abort();
 if(signal?.aborted)controller.abort();else signal?.addEventListener('abort',cancel,{once:true});
 const timer=setTimeout(()=>controller.abort(),38000);
 try{
  const r=await fetch(API+'/api/'+path,{...(body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{}),signal:controller.signal});
  let d;try{d=await r.json()}catch{throw new Error('The travel service returned an invalid response. Please try again.')}
  if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:'Check the selected stops and departure time.');return d;
 }catch(e){if(e instanceof Error&&e.name==='AbortError')throw new Error(signal?.aborted?'Search cancelled.':'The service took too long. Try again or use the stop controls.');throw e}
 finally{clearTimeout(timer);signal?.removeEventListener('abort',cancel)}
}
const clock=(s:string)=>new Date(s).toLocaleTimeString('en-US',{timeZone:'America/Chicago',hour:'numeric',minute:'2-digit'});
function transitColor(mode:string,color?:string,route=''){
 if(mode==='walk')return '#596773';
 const official:Record<string,string>={'700':'EF0000','800':'3E7E00','900':'40007E'};
 const hex=color?.replace('#','')||official[route];
 return hex&&/^[0-9a-f]{6}$/i.test(hex)?'#'+hex:mode==='rail'?'#555B73':'#1766A5';
}
function transitStyle(mode:string,color?:string,route=''):CSSProperties{
 const value=transitColor(mode,color,route);
 return {'--transit-color':value,backgroundColor:value+'18',color:value,borderColor:value+'55'} as CSSProperties;
}
function ModeIcon({mode,size=16}:{mode:string;size?:number}){return mode==='walk'?<Footprints size={size}/>:mode==='rail'?<TrainFront size={size}/>:<BusFront size={size}/>}
function localNow(){const parts=new Intl.DateTimeFormat('sv-SE',{timeZone:'America/Chicago',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date());return parts.replace(' ','T')}
function chicagoISO(value:string){const probe=new Date(value+'Z');const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/Chicago',timeZoneName:'shortOffset'}).formatToParts(probe);const offset=parts.find(p=>p.type==='timeZoneName')?.value==='GMT-5'?'-05:00':'-06:00';return value+':00'+offset}
function StopInput({label,value,onChange}:{label:string;value:Endpoint;onChange:(v:Endpoint)=>void}){
 const [open,setOpen]=useState(false);
 const [matches,setMatches]=useState<{query:string;stops:Stop[];error?:string}>();
 const {query}=value;

 useEffect(()=>{
  if(!open||query.trim().length<2)return;
  let cancelled=false;
  const timer=setTimeout(async()=>{
   try{
    const stops:Stop[]=await api('stops?q='+encodeURIComponent(query));
    if(!cancelled)setMatches({query,stops,error:stops.length?undefined:'No matching stops. Try a street or station name.'});
   }catch{
    if(!cancelled)setMatches({query,stops:[],error:'Stop search is unavailable.'});
   }
  },250);
  return()=>{cancelled=true;clearTimeout(timer)};
 },[query,open]);

 const suggestions=open&&query.trim().length>=2&&matches?.query===query?matches:undefined;
 return <div className="stop-field" onBlur={e=>{
  if(!e.currentTarget.contains(e.relatedTarget))setOpen(false);
 }}>
  <label>{label}<div className="stop-control"><MapPin size={18}/><input
   value={query} placeholder={label==='From'?'Station, stop, or UH':'Where are you going?'}
   onFocus={()=>setOpen(true)}
   onChange={e=>{onChange({query:e.target.value,stops:[]});setOpen(true)}}
   aria-label={label} autoComplete="off"/></div></label>
  {suggestions&&<div className="suggestions">
   {suggestions.stops.map(stop=><button key={stop.stop_id} type="button"
    onMouseDown={e=>e.preventDefault()}
    onClick={()=>{onChange({query:stop.stop_name,stops:[stop]});setOpen(false)}}>
    <MapPin size={15}/><span>{stop.stop_name}<small>Stop {stop.stop_code||stop.stop_id}</small></span>
   </button>)}
   {suggestions.error&&<p>{suggestions.error}</p>}
  </div>}
 </div>
}

function TransitMap({journey}:{journey?:Journey}){
 const vehicleLayer=useRef<LayerGroup|null>(null);const [liveStatus,setLiveStatus]=useState('');
 const el=useRef<HTMLDivElement>(null);const map=useRef<LeafletMap|null>(null);const layer=useRef<LayerGroup|null>(null);const [ready,setReady]=useState(false);
 useEffect(()=>{let cancelled=false;import('leaflet').then(L=>{if(cancelled||!el.current)return;const m=L.map(el.current,{zoomControl:false}).setView([29.745,-95.369],12);map.current=m;L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',maxZoom:19}).addTo(m);L.control.zoom({position:'bottomright'}).addTo(m);layer.current=L.layerGroup().addTo(m);setReady(true)});return()=>{cancelled=true;map.current?.remove();map.current=null}},[]);
 useEffect(()=>{if(!ready||!map.current||!layer.current)return;import('leaflet').then(L=>{layer.current?.clearLayers();if(!journey)return;const bounds:L.LatLngTuple[]=[];journey.legs.forEach((leg,i)=>{const color=transitColor(leg.mode,leg.color,leg.route_id);const pts=leg.geometry.map(p=>[p[1],p[0]] as L.LatLngTuple);bounds.push(...pts);L.polyline(pts,{color,weight:5,opacity:.85,dashArray:leg.mode==='walk'?'4 7':undefined}).addTo(layer.current!);[leg.from,leg.to].forEach(s=>{L.circleMarker([s.stop_lat,s.stop_lon],{radius:6,color,fillColor:'#fff',fillOpacity:1,weight:3}).bindTooltip(s.stop_name).addTo(layer.current!);});});if(bounds.length)map.current?.fitBounds(bounds,{padding:[45,45],maxZoom:15})})},[journey,ready]);
 useEffect(()=>{if(!ready||!journey)return;let cancelled=false;let timer:ReturnType<typeof setTimeout>;const ids=[...new Set(journey.legs.filter(l=>l.mode!=='walk').map(l=>l.route_id))];async function refresh(){try{const results=await Promise.all(ids.map(id=>api('vehicles?route_id='+encodeURIComponent(id))));if(cancelled)return;const L=await import('leaflet');if(cancelled||!map.current)return;if(!vehicleLayer.current)vehicleLayer.current=L.layerGroup().addTo(map.current);vehicleLayer.current.clearLayers();let count=0;results.forEach(r=>r.vehicles.forEach((v:{id:string;label:string;lat:number;lon:number;updated_at:number})=>{if(Date.now()/1000-v.updated_at>120)return;count++;const tip=document.createElement('span');tip.textContent=`Route ${r.route_id} · Vehicle ${v.label} · updated ${Math.max(0,Math.round(Date.now()/1000-v.updated_at))}s ago`;L.marker([v.lat,v.lon],{icon:L.divIcon({className:'live-vehicle-icon',html:(()=>{const leg=journey?.legs.find(l=>l.route_id===r.route_id);const color=transitColor(leg?.mode||'bus',leg?.color,r.route_id);const node=document.createElement('div');node.className='vehicle-symbol';node.style.backgroundColor=color;node.innerHTML=leg?.mode==='rail'?'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="3" width="14" height="15" rx="4"/><path d="M5 10h14M9 18l-3 4m9-4 3 4M9 14h.01M15 14h.01"/></svg>':'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="3" width="16" height="16" rx="3"/><path d="M4 10h16M8 19v3m8-3v3M8 15h.01M16 15h.01"/></svg>';return node})(),iconSize:[32,32],iconAnchor:[16,16]})}).bindTooltip(tip).addTo(vehicleLayer.current!)}));setLiveStatus(count?`${count} live route vehicles · refreshes every 20s`:results.some(r=>r.status==='unauthorized')?'Vehicle API access needs configuration':results.some(r=>r.status==='unavailable')?'Live vehicle feed unavailable':journey?.legs.filter(l=>l.mode!=='walk').every(l=>l.mode==='rail')?'METRO is not reporting live train locations for this trip · schedule shown':'METRO is not reporting fresh vehicle locations for this trip · schedule shown');}catch{if(!cancelled){vehicleLayer.current?.clearLayers();setLiveStatus('Live vehicle feed unavailable')}}finally{if(!cancelled)timer=setTimeout(refresh,20000)}}setLiveStatus('Checking live vehicle positions…');refresh();return()=>{cancelled=true;clearTimeout(timer);vehicleLayer.current?.clearLayers()}},[journey,ready]);
 return <div className="map-wrap"><div ref={el} className="map"/><div className="map-label"><Navigation size={16}/><span>Houston, Texas</span></div>{journey&&<div className="live-status" role="status">{liveStatus}</div>}<div className="map-note">{journey?(journey.source?'Paths from METRO planner · vehicle markers show current positions':'Stop connections shown · not street directions'):'Choose your trip to see stops on the map'}</div></div>
}
export default function Home(){
 const activeRequest=useRef<AbortController|null>(null);
 const [sortBy,setSortBy]=useState<'duration'|'arrival'|'transfers'|'walking'>('duration');
 useEffect(()=>()=>activeRequest.current?.abort(),[]);
 const [leaveNow,setLeaveNow]=useState(true);const [walking,setWalking]=useState(true);const [searchedAt,setSearchedAt]=useState('');const [emptyMessage,setEmptyMessage]=useState('');const [tab,setTab]=useState('plan');const [origin,setOrigin]=useState<Endpoint>({query:'',stops:[]});const [dest,setDest]=useState<Endpoint>({query:'',stops:[]});const [departure,setDeparture]=useState('');const [mode,setMode]=useState('any');const [prefer,setPrefer]=useState('fastest');const [transfers,setTransfers]=useState(1);const [avoid,setAvoid]=useState(false);const [text,setText]=useState('');const [status,setStatus]=useState<Status|null>(null);const [journeys,setJourneys]=useState<Journey[]>([]);const [selected,setSelected]=useState(0);const [busy,setBusy]=useState('');const [error,setError]=useState('');const [searched,setSearched]=useState(false);const [message,setMessage]=useState('');const [allAlerts,setAllAlerts]=useState<Alert[]>([]);const [routes,setRoutes]=useState<{route_id:string;route_short_name:string;route_long_name:string;route_type:number;route_color?:string}[]>([]);const [routeQuery,setRouteQuery]=useState('');
 useEffect(()=>{setDeparture(localNow());api('status').then(setStatus).catch(()=>setError('The transit service is unavailable. Please try again shortly.'));api('alerts').then(d=>setAllAlerts(d.alerts)).catch(()=>{});api('routes').then(setRoutes).catch(()=>{})},[]);
 useEffect(()=>{if(!leaveNow)return;setDeparture(localNow());const timer=setInterval(()=>setDeparture(localNow()),30000);return()=>clearInterval(timer)},[leaveNow]);
 async function search(o=origin.stops,d=dest.stops,at=departure,m=mode,p=prefer,tr=transfers,av=avoid,ln=leaveNow,walk=walking,existing?:AbortController){
  if(!o.length||!d.length){setMessage('');setError('Choose both stops from the search suggestions.');return}
  const controller=existing||new AbortController();
  if(!existing){activeRequest.current?.abort();activeRequest.current=controller}
  if(controller.signal.aborted)return;
  setBusy('Finding journeys');setError('');setMessage('');setJourneys([]);setSearched(false);
  try{
   const result=await api('journeys',{origin_ids:o.map(s=>s.stop_id),destination_ids:d.map(s=>s.stop_id),departure:chicagoISO(at),mode:m,prefer:p,max_transfers:tr,avoid_alerts:av,leave_now:ln,allow_walking:walk},controller.signal);
   if(activeRequest.current!==controller||controller.signal.aborted)return;
   setSearchedAt(result.searched_departure);setEmptyMessage(result.empty_message||'No matching bus or rail journeys.');if(ln)setDeparture(localNow());setJourneys(result.journeys);setSelected(0);setSearched(true);setMessage(result.alternatives_notice||'');
   setTimeout(()=>document.getElementById('journey-results')?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'nearest'}),100);
  }catch(e){if(activeRequest.current===controller&&!controller.signal.aborted)setError((e as Error).message)}
  finally{if(activeRequest.current===controller){activeRequest.current=null;setBusy('')}}
 }
 async function understand(request=text){
  activeRequest.current?.abort();const controller=new AbortController();activeRequest.current=controller;
  const defaults={mode,max_transfers:transfers,prefer,avoid_alerts:avoid,allow_walking:walking,departure:departure?chicagoISO(departure):null,leave_now:leaveNow};
  setBusy('Understanding your trip');setJourneys([]);setSearched(false);setSearchedAt('');setError('');setMessage('');
  setOrigin({query:'',stops:[]});setDest({query:'',stops:[]});
  try{
   const result=await api('interpret',{text:request,defaults},controller.signal);
   if(activeRequest.current!==controller||controller.signal.aborted)return;
   const i=result.intent;
   if(!result.validated||!result.origin?.stops?.length||!result.destination?.stops?.length)throw new Error('The station matches could not be verified. Use the stop controls.');
   const at=i.date+'T'+i.time;const leavingNow=result.leave_now===true;
   setLeaveNow(leavingNow);setDeparture(at);setMode(i.mode);setPrefer(i.prefer);setTransfers(i.max_transfers);setAvoid(i.avoid_alerts);setWalking(i.allow_walking);
   setOrigin(result.origin);setDest(result.destination);
   await search(result.origin.stops,result.destination.stops,at,i.mode,i.prefer,i.max_transfers,i.avoid_alerts,leavingNow,i.allow_walking,controller);
  }catch(e){if(activeRequest.current===controller&&!controller.signal.aborted)setError((e as Error).message)}
  finally{if(activeRequest.current===controller){activeRequest.current=null;setBusy('')}}
 }
 const orderedJourneys=useMemo(()=>[...journeys].sort((a,b)=>{
  const arrival=new Date(a.arrival).getTime()-new Date(b.arrival).getTime();
  if(sortBy==='arrival')return arrival||a.duration_minutes-b.duration_minutes;
  if(sortBy==='transfers')return a.transfers-b.transfers||a.duration_minutes-b.duration_minutes||arrival;
  if(sortBy==='walking')return (a.walking_meters||0)-(b.walking_meters||0)||a.duration_minutes-b.duration_minutes||arrival;
  return a.duration_minutes-b.duration_minutes||arrival;
 }),[journeys,sortBy]);
 const shortestTrip=Math.min(...journeys.map(j=>j.duration_minutes));
 const tripHighlights=(j:Journey)=>[...(j.duration_minutes===shortestTrip?['Shortest trip']:[]),...(j.highlights||[]).map(h=>h==='Fastest arrival'?'Arrives first':h)].join(' · ');
 const current=orderedJourneys[selected];
 return <><header><a className="brand" href="/" aria-label="MetroAI home"><span className="brand-mark">m<span>↗</span></span>metro<span className="brand-ai">ai</span></a><nav aria-label="Main navigation">{[['plan','Plan a trip'],['routes','Routes'],['alerts','Service alerts'],['files','Files']].map(([id,label])=><button className={tab===id?'active':''} onClick={()=>setTab(id)} key={id}>{label}{id==='alerts'&&allAlerts.length>0&&<span className="count">{allAlerts.length}</span>}</button>)}</nav><span className="houston">HOUSTON <span> / </span> TX</span></header>
 <main><div className="page-heading"><div><div className="eyebrow">YOUR CITY. YOUR NEXT STOP.</div><h1>{tab==='plan'?'Your city. One simple trip.':tab==='routes'?'Find your line.':tab==='files'?'Keep your trip together.':'Know before you go.'}</h1><p>{tab==='plan'?'Tell us where. We’ll find the stops, the lines, and your way there.':tab==='routes'?'Explore bus and rail routes in the loaded METRO schedule.':tab==='files'?'Save the files you need for your next journey.':'Current notices from METRO, with the details that matter.'}</p></div><div className="data-badge"><span className="badge-icon"><Clock3 size={19}/></span><div>METRO journey data<small>All times in Houston time</small></div></div></div>
 {tab==='plan'?<div className="workspace"><section className="planner"><fieldset disabled={!!busy} className="planner-fields"><div className="panel-title"><h2>Where to?</h2><span>01 / PLAN</span></div><div className="ai-box"><label htmlFor="prompt"><Sparkles size={16}/> Where can we take you?</label><textarea id="prompt" value={text} onChange={e=>setText(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.nativeEvent.isComposing){e.preventDefault();if(text.length>=5&&!busy)understand()}}} placeholder="UH to Downtown after 5 PM, fewer transfers" maxLength={800}/><div className="ai-bottom"><span>Enter to plan · Shift + Enter for a new line</span><button aria-label="Plan this trip" disabled={!!busy||text.length<5} onClick={()=>understand()}>{busy?<LoaderCircle size={18} className="spin"/>:<><span>Plan my trip</span><ArrowRight size={18}/></>}</button></div></div><div className="quick-trips"><button disabled={!!busy} onClick={()=>{const q='UH to Downtown, leave now, fewer transfers';setText(q);understand(q)}}>UH → Downtown <ArrowUpRight size={14}/></button><button disabled={!!busy} onClick={()=>{const q='Downtown to Medical Center, leave now';setText(q);understand(q)}}>Downtown → TMC <ArrowUpRight size={14}/></button></div><div className="divider"><span>or choose your stops</span></div><StopInput label="From" value={origin} onChange={setOrigin}/><button className="swap" aria-label="Swap origin and destination" onClick={()=>{setOrigin(dest);setDest(origin)}}><ArrowDownUp size={16}/></button><StopInput label="To" value={dest} onChange={setDest}/><div className="departure-toggle"><button className={leaveNow?'chosen':''} onClick={()=>{setLeaveNow(true);setDeparture(localNow())}}>Leave now</button><button className={!leaveNow?'chosen':''} onClick={()=>setLeaveNow(false)}>Choose a time</button></div><label className="date-label">{leaveNow?'Departing now · Houston time':'Leave after · Houston time'}<input disabled={leaveNow} type="datetime-local" value={departure} onChange={e=>{setLeaveNow(false);setDeparture(e.target.value)}}/></label><details className="preferences"><summary>Trip preferences <span>{mode==='any'?'Bus + rail':mode} · {transfers?`up to ${transfers} transfer${transfers===1?'':'s'}`:'direct'}</span><ChevronDown size={16}/></summary><label className="field-label">Travel by</label><div className="mode-options">{[['any','Any',RouteIcon],['bus','Bus',BusFront],['rail','Rail',TrainFront]].map(([id,label,Icon])=><button key={id as string} className={mode===id?'chosen':''} onClick={()=>setMode(id as string)} aria-pressed={mode===id}>{typeof Icon!=='string'&&<Icon size={17}/>} {label as string}</button>)}</div><div className="two-fields"><label>Priority<select value={prefer} onChange={e=>setPrefer(e.target.value)}><option value="fastest">Earliest arrival</option><option value="fewer_transfers">Fewer transfers</option></select></label><label>Transfers<select value={transfers} onChange={e=>setTransfers(+e.target.value)}><option value={1}>Up to one</option><option value={0}>Direct only</option><option value={2}>Up to two</option><option value={3}>Up to three</option></select></label></div><label className="checkbox"><input type="checkbox" checked={walking} onChange={e=>setWalking(e.target.checked)}/> Include walking connections (up to 1.2 km total)</label><label className="checkbox"><input type="checkbox" checked={avoid} onChange={e=>setAvoid(e.target.checked)}/> Avoid routes with current alerts</label></details><button className="primary" disabled={!!busy} onClick={()=>search()}>{busy?<LoaderCircle size={18} className="spin"/>:<Search size={18}/>} {busy||'Find journeys'}{!busy&&<ArrowRight size={18}/>}</button>{error&&<div className="feedback error" role="alert">{error}</div>}{message&&<div className="feedback" role="status">{message}</div>}<p className="planner-note">Compares different routes within your walking and transfer limits. Searches the next 4 hours. Walking connections use METRO’s trip planner. Start and end at the selected stops.</p></fieldset>{busy&&<button type="button" className="cancel-search" onClick={()=>{activeRequest.current?.abort();activeRequest.current=null;setBusy('');setMessage('Search cancelled. You can change the trip controls.')}}>Cancel search</button>}</section>
 <section className="right-panel"><TransitMap journey={current}/><div className="results" id="journey-results" aria-live="polite">{searchedAt&&<p className="search-context">Depart after {clock(searchedAt)} · {new Date(searchedAt).toLocaleDateString('en-US',{timeZone:'America/Chicago'})} · Houston time</p>}<div className="results-heading"><h2>{searched?`${journeys.length} ways to get there`:'Houston is yours to explore'}</h2>{searched&&journeys.length>1&&<label className="result-sort">Sort by<select aria-label="Sort routes by" value={sortBy} onChange={e=>{setSortBy(e.target.value as typeof sortBy);setSelected(0)}}><option value="duration">Fastest trip</option><option value="arrival">Earliest arrival</option><option value="transfers">Fewest transfers</option><option value="walking">Least walking</option></select></label>}</div>{!searched&&!busy&&<div className="empty"><div className="empty-icon"><RouteIcon size={25}/></div><div><h3>Less guesswork. More going.</h3><p>Pick your stops or describe your trip above.<br/>We’ll find connections from actual transit schedules.</p><button disabled={!!busy} onClick={()=>{const q='UH to Downtown, leave now, fewer transfers';setText(q);understand(q)}}>Try UH → Downtown <ArrowUpRight size={15}/></button></div></div>}{busy&&<div className="empty"><LoaderCircle className="spin"/><p>{busy}…</p></div>}{searched&&!journeys.length&&<div className="empty"><RouteIcon/><p>{emptyMessage}</p></div>}{orderedJourneys.map((j,index)=><article key={index} className={'journey '+(index===selected?'selected':'')}><button className="journey-summary" onClick={()=>setSelected(index)} aria-expanded={index===selected}><div className="option-label">{index===0?'Recommended · ':''}{tripHighlights(j)||'Another route'} <span>{j.travel_modes||'Transit'}</span></div><div className="journey-top"><span className="journey-time">{clock(j.departure)} <span>→</span> {clock(j.arrival)}</span><strong>{j.duration_minutes} <small>min</small></strong></div><div className="journey-bottom"><div className="leg-chips">{j.legs.map((l,i)=><span key={i} className={'route-chip '+l.mode} style={transitStyle(l.mode,l.color,l.route_id)} title={l.mode==='walk'?'Walk':l.name} aria-label={l.mode==='walk'?`Walk ${l.distance_meters} metres`:`${l.mode==='rail'?'Train':'Bus'} ${l.route} ${l.name}`}>{l.mode==='walk'?<Footprints size={15}/>:l.mode==='rail'?<TrainFront size={15}/>:<BusFront size={15}/>} {l.mode==='walk'?`${l.distance_meters} m`:l.route}</span>)}<span>{j.transfers?`${j.transfers} transfer${j.transfers===1?'':'s'}`:'Direct'}</span></div>{j.alerts.length>0?<span className="alert-chip"><TriangleAlert size={14}/> {j.alerts.length} alerts</span>:<span className="scheduled">{j.timing==='live_updates'?'Live timing':'Scheduled'}</span>}<ChevronDown size={16}/></div></button>{index===selected&&<div className="journey-detail">{j.legs.map((l,i)=><div key={i}>{i>0&&<div className="transfer"><ArrowDownUp size={14}/> {l.mode==='walk'?(i===j.legs.length-1?'Walk to your destination':'Walk to the next stop'):`Board next service · ${Math.max(0,Math.round((new Date(l.departure).getTime()-new Date(j.legs[i-1].arrival).getTime())/60000))} min after previous leg`}</div>}<div className="timeline" style={{'--transit-color':transitColor(l.mode,l.color,l.route_id)} as CSSProperties}><div><strong>{clock(l.departure)}</strong><span className="timeline-dot"/><div><strong>{l.from.stop_name}</strong><p>{l.mode==='walk'?`Walk ${l.distance_meters} m to ${l.to.stop_name}`:<>Board {l.route} {l.name} · toward {l.headsign}</>}</p></div></div><div className="ride"><span/ ><span className="timeline-line"/><small><ModeIcon mode={l.mode}/>{l.stop_count!==null?`${l.stop_count} stops · `:''}{l.mode==='walk'?'Walking':l.mode==='rail'?'Rail':'Bus'}</small></div><div><strong>{clock(l.arrival)}</strong><span className="timeline-dot end"/><div><strong>{l.to.stop_name}</strong>{(l.to.stop_code||l.to.stop_id)&&<p>Stop {l.to.stop_code||l.to.stop_id}</p>}</div></div></div>{l.mode==='walk'&&!!l.steps?.length&&<details className="walking-directions"><summary>Walking directions</summary><ol>{l.steps.map((step,k)=><li key={k}>{step.relativeDirection.replaceAll('_',' ').toLowerCase()} on {step.streetName} · {Math.round(step.distance)} m</li>)}</ol></details>}</div>)}{j.alerts.map(a=><details className="journey-alert" key={a.id}><summary><TriangleAlert size={15}/>{a.header}</summary><p>{a.description}</p></details>)}</div>}</article>)}</div></section></div>:
 tab==='files'?<FilesPanel/>:tab==='routes'?<section className="browse-panel"><label className="route-search"><Search size={19}/><input placeholder="Search route number or name" value={routeQuery} onChange={e=>setRouteQuery(e.target.value)}/></label><div className="route-grid">{routes.filter(r=>(r.route_short_name+' '+r.route_long_name).toLowerCase().includes(routeQuery.toLowerCase())).map(r=><div className="route-tile" key={r.route_id}><span className={'route-chip '+(r.route_type===3?'bus':'rail')} style={transitStyle(r.route_type===3?'bus':'rail',r.route_color,r.route_id)}>{r.route_type===3?<BusFront size={18}/>:<TrainFront size={18}/>} {r.route_short_name}</span><strong>{r.route_long_name}</strong></div>)}</div>{!routes.length&&<p>Route data is not loaded yet.</p>}</section>:<section className="browse-panel"><div className="alerts-meta"><TriangleAlert size={18}/>{status?.alerts?.status==='current'?'Current alerts':`Alerts ${status?.alerts?.status||'unavailable'}`} · {status?.alerts?.fetched_at?'Checked '+clock(status.alerts.fetched_at):'Not yet refreshed'}<a href="https://www.ridemetro.org/alerts" target="_blank" rel="noreferrer">View at METRO <ArrowUpRight size={14}/></a></div>{allAlerts.map(a=><details className="alert-card" key={a.id}><summary><span className="alert-type">{a.effect}</span><strong>{a.header}</strong><ChevronDown size={18}/></summary><p>{a.description||'See METRO for further information.'}</p></details>)}{!allAlerts.length&&<p>{status?.alerts?.status==='current'?'No current notices returned.':'Alerts are unavailable. Check METRO before travelling.'}</p>}</section>}
 <div className="service-strip"><div><span className="small-symbol"><BusFront size={18}/></span><strong>{status?.counts?.routes||'—'}</strong> scheduled routes</div><div><MapPin size={18}/><strong>{status?.counts?.stops?.toLocaleString()||'—'}</strong> transit stops</div><div><TriangleAlert size={18}/> Alerts {status?.alerts?.status||'loading'}</div><a href="https://www.ridemetro.org/alerts" target="_blank" rel="noreferrer">Check METRO before you travel <ArrowUpRight size={14}/></a></div></main><footer><span>Route and arrival data provided by permission of METRO</span><span>Independent student project · Group 2</span><p>* METRO is the registered trademark of the Metropolitan Transit Authority of Harris County, Texas. All rights reserved.</p></footer></>
}
