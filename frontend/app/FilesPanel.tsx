'use client';
import {useEffect,useRef,useState} from 'react';
import {FileText,Upload,Download,LoaderCircle} from 'lucide-react';

type UploadedFile={id:string;filename:string;size_bytes:number;sha256:string;created_at:string};
const API=typeof window!=='undefined'&&window.location.port==='3000'?'http://127.0.0.1:8000':'';

export default function FilesPanel(){
 const [files,setFiles]=useState<UploadedFile[]>([]);
 const [selected,setSelected]=useState<File|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState('');
 const [notice,setNotice]=useState('');
 const input=useRef<HTMLInputElement>(null);
 async function refresh(){
  const response=await fetch(API+'/api/uploads');
  if(!response.ok)throw new Error('Saved files are unavailable. Please try again.');
  setFiles(await response.json());
 }
 useEffect(()=>{refresh().catch(e=>setError(e.message))},[]);
 async function upload(){
  if(!selected)return;
  if(selected.size===0||selected.size>5*1024*1024){setError('Choose a nonempty file up to 5 MB.');return}
  setBusy(true);setError('');setNotice('');
  try{
   const response=await fetch(API+'/api/uploads',{method:'POST',headers:{'Content-Type':selected.type||'application/octet-stream','X-Filename':encodeURIComponent(selected.name)},body:selected});
   const result=await response.json();
   if(!response.ok)throw new Error(typeof result.detail==='string'?result.detail:'Upload failed. Please try again.');
   setNotice(result.filename+' was saved.');setSelected(null);
   if(input.current)input.current.value='';
   await refresh();
  }catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 return <section className="browse-panel files-panel" aria-labelledby="files-title">
  <h2 id="files-title">Your travel files</h2>
  <p>Keep a timetable, route guide, or trip note here. Files stay available when you return.</p>
  <div className="file-upload">
   <label htmlFor="travel-file">Choose a file <small>Up to 5 MB</small></label>
   <input ref={input} id="travel-file" type="file" disabled={busy} onChange={e=>{setSelected(e.target.files?.[0]||null);setError('');setNotice('')}}/>
   <button className="primary" disabled={!selected||busy} onClick={upload}>{busy?<LoaderCircle size={18} className="spin"/>:<Upload size={18}/>} {busy?'Saving file…':'Upload file'}</button>
  </div>
  {error&&<p className="feedback error" role="alert">{error}</p>}
  {notice&&<p className="feedback" role="status">{notice}</p>}
  <div className="saved-files"><h3>Saved files</h3>
   {!files.length&&<p>Your uploaded files will appear here.</p>}
   {files.map(file=><article className="saved-file" key={file.id}>
    <FileText size={24}/><div><strong>{file.filename}</strong><p>{Math.ceil(file.size_bytes/1024)} KB · {new Date(file.created_at).toLocaleString('en-US',{timeZone:'America/Chicago'})}</p></div>
    <a href={API+'/api/uploads/'+file.id} aria-label={'Download '+file.filename}><Download size={18}/> Download</a>
   </article>)}
  </div>
 </section>
}
