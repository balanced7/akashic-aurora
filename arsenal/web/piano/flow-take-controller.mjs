import {FlowClip,clipPosition} from '../lib/flow/flow-clip.mjs';
import {saveTake,getTake,listTakes} from './flow-take-store.mjs';
const MODEL='khronos-car-concept-4.8-v1';

export function createTakeController({getScene,restoreScene,onPair,onTime,onDraw,requestPause,setWorkerRunning,setCapture,onLive}){
 const $=id=>document.getElementById(id),canvas=$('stage');
 let mode='live',clip=null,id='',capture=null,packer=null,elapsed=0,position=0,pair=-1,a=null,b=null,disposed=false,enabled=false,running=false,indexRevision=0,uiTime=0;
 const busy=()=>mode==='capture'||mode==='packing',say=s=>{$('take-status').textContent=s;};
 function urlTake(value){const u=new URL(location.href);if(value)u.searchParams.set('take',value);else u.searchParams.delete('take');history.replaceState(null,'',u);}
 function controls(){
  for(const e of document.querySelectorAll('#clearance,#wake,#density,#yaw,[data-look]'))e.disabled=mode!=='live';
  $('take-record').disabled=!enabled||mode!=='live';$('take-live').disabled=mode==='live'||busy();$('take-cancel').hidden=!busy();
  for(const key of ['take-name','take-duration','take-library','take-import'])$(key).disabled=busy();
  $('take-replay').disabled=!clip||busy();$('take-export').disabled=!clip||busy();$('take-player').hidden=mode!=='replay';canvas.dataset.flowMode=mode;
 }
 function show(t,redraw=false){
  if(!clip)return;position=Math.max(0,Math.min(clip.duration,t));const sample=clip.bracket(position);
  if(pair!==sample.a){a=clip.decodeFrame(sample.a,'paths',a?.length===clip.pathLength?a:undefined);b=clip.decodeFrame(sample.b,'paths',b?.length===clip.pathLength?b:undefined);onPair(a,b);pair=sample.a;}
  onTime(sample.alpha,clip.header.metadata.phase+position);
  if(redraw||performance.now()-uiTime>100){uiTime=performance.now();$('take-seek').value=String(position);$('take-time').textContent=position.toFixed(1)+' / '+clip.duration.toFixed(1)+' s';canvas.dataset.replay=JSON.stringify({id,time:position,duration:clip.duration,left:sample.a,right:sample.b,blend:sample.alpha,frames:clip.header.frames,bytes:clip.buffer.byteLength});}
  if(redraw)onDraw();
 }
 function seekClock(t){return $('take-loop').value==='bounce'?Math.acos(1-2*Math.max(0,Math.min(1,t/clip.duration)))*clip.duration/Math.PI:t;}
 function adopt(buffer,key=''){
  const candidate=new FlowClip(buffer),meta=candidate.header.metadata;
  if(meta?.model!==MODEL||candidate.header.segments!==384||![48,72,108].includes(candidate.header.streams))throw new Error('This take belongs to a different scene or path layout.');
  if(!meta.settings||meta.settings.density!==candidate.header.streams||!Number.isFinite(meta.phase)||Math.abs(meta.phase)>1e7||typeof meta.name!=='string'||meta.name.length>64)throw new Error('This take is missing valid scene settings.');
  // No state changes until the complete recording has passed validation.
  setWorkerRunning(false);mode='replay';clip=candidate;id=key;elapsed=0;pair=-1;
  restoreScene(meta);urlTake(id);$('take-library').value=id;$('take-seek').max=String(clip.duration);enabled=true;controls();show(0,true);
  $('solver-status').textContent='Recorded flow · solver asleep';$('solver-detail').textContent=`${clip.header.frames} snapshots · ${(buffer.byteLength/1048576).toFixed(1)} MB · 3D paths + velocity + pressure samples`;
  canvas.dataset.solverMode='recorded';
  say(`Playing “${meta.name}”.`);
 }
 async function refreshLibrary(selected=id){
  const revision=++indexRevision,items=await listTakes();if(disposed||revision!==indexRevision)return;
  $('take-library').replaceChildren(new Option('Choose a recording…',''));
  for(const r of items)$('take-library').add(new Option(`${r.name} · ${r.duration.toFixed(1)} s`,r.id));$('take-library').value=selected;
 }
 async function persist(buffer,name){
  const key='flow-'+Date.now().toString(36)+'-'+crypto.randomUUID().slice(0,8),record={id:key,name,created:Date.now(),duration:clip.duration,bytes:buffer.byteLength,buffer};
  try{await saveTake(record);id=key;urlTake(id);await refreshLibrary(id);say(`Saved “${name}” in this browser. Save file for a portable copy.`);}
  catch(e){say('The browser could not save this take: '+e.message+'. It is still playable; use Save file.');}
 }
 function live(){if(busy())return;mode='live';pair=-1;urlTake('');controls();canvas.dataset.solverMode='live';onLive();setWorkerRunning(running);say('Live flow. Record a take when you find a motion you like.');}
 function cancel(){
  if(!busy())return;packer?.terminate();packer=null;capture=null;setCapture(false);mode='live';controls();setWorkerRunning(running);say('Capture cancelled. Your previous takes are unchanged.');
 }
 function finish(){
  if(mode!=='capture')return;mode='packing';setCapture(false);setWorkerRunning(false);controls();say('Packing the motion and flow fields…');
  const data={streams:capture.metadata.settings.density,segments:384,grid:capture.grid,metadata:capture.metadata,frames:capture.frames};capture=null;
  packer=new Worker(new URL('../lib/flow/flow-clip-worker.mjs',import.meta.url),{type:'module'});
  function failed(message){packer?.terminate();packer=null;mode='live';controls();setWorkerRunning(running);say('Could not pack this take: '+message);}
  packer.onmessage=async({data:m})=>{
   if(disposed||mode!=='packing')return;if(m.error){failed(m.error);return;}packer.terminate();packer=null;
   try{adopt(m.buffer);await persist(m.buffer,clip.header.metadata.name);}catch(e){failed(e.message);}
  };
  packer.onerror=e=>failed(e.message);packer.postMessage(data,data.frames.flatMap(f=>[f.paths.buffer,f.field.buffer]));
 }
 $('take-record').addEventListener('click',()=>{
  if(mode!=='live'||!enabled)return;mode='capture';capture={frames:[],clock:0,zero:0,duration:Number($('take-duration').value)};controls();say('Waiting for the first flow sample…');requestPause(false);setCapture(true);
 });
 $('take-cancel').addEventListener('click',cancel);$('take-live').addEventListener('click',live);
 $('take-replay').addEventListener('click',()=>{if(clip&&!busy()){adopt(clip.buffer,id);requestPause(false);}});
 $('take-seek').addEventListener('input',()=>{if(clip){const t=Number($('take-seek').value);elapsed=seekClock(t);show(t,true);}});
 $('take-loop').addEventListener('change',()=>{if(clip)elapsed=seekClock(position);});
 $('take-library').addEventListener('change',async()=>{const key=$('take-library').value;if(!key||busy())return;try{const r=await getTake(key);if(!r)throw new Error('That take is unavailable.');adopt(r.buffer,key);say(`Playing “${r.name}”.`);}catch(e){say(e.message);}});
 $('take-export').addEventListener('click',()=>{
  if(!clip)return;const name=(clip.header.metadata.name||'violet-flow').replace(/[^a-z0-9_-]+/gi,'-').slice(0,64),url=URL.createObjectURL(new Blob([clip.buffer],{type:'application/octet-stream'})),link=document.createElement('a');
  link.href=url;link.download=name+'-'+(id||'take')+'.flowclip';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);say('Flow file prepared for download. It contains the 3D animation and sampled fields.');
 });
 $('take-import').addEventListener('change',async()=>{
  const file=$('take-import').files?.[0];$('take-import').value='';if(!file||busy())return;
  try{if(file.size>128*1048576)throw new Error('This file is larger than the 128 MB take limit.');const buffer=await file.arrayBuffer();adopt(buffer);await persist(buffer,clip.header.metadata.name||file.name);}catch(e){say('Could not load this file: '+e.message);}
 });
 return {
  get mode(){return mode;},get playback(){return mode==='replay';},
  async initial(){try{await refreshLibrary();const key=new URLSearchParams(location.search).get('take');if(key){const r=await getTake(key);if(!r)throw new Error('Saved take not found in this browser. Use Load file for a portable copy.');adopt(r.buffer,key);say(`Playing “${r.name}”.`);return true;}}catch(e){say(e.message);}return false;},
  ready(){enabled=true;controls();},
  packet(m){
   if(mode!=='capture'||!m.volume||!capture)return;
   if(!capture.frames.length){capture.zero=capture.clock;const scene=getScene();capture.metadata={model:MODEL,name:$('take-name').value.trim()||'Violet current',...scene,source:'Violet visual-fluid solver',pressureUnits:'pressure impulse p*dt/rho',stepSeconds:.065};capture.grid=m.grid;}
   const t=capture.clock-capture.zero;
   if(!capture.frames.length||t>capture.frames.at(-1).t+.05)capture.frames.push({t,simTime:m.diagnostics.simTime,paths:m.paths,field:m.volume});capture.metadata.diagnostics=m.diagnostics;
   say(`Recording ${t.toFixed(1)} / ${capture.duration} s · ${capture.frames.length} flow samples`);canvas.dataset.recording=JSON.stringify({seconds:t,frames:capture.frames.length,fieldValues:m.volume.length});
   if(t>=capture.duration||capture.frames.length>=100)finish();
  },
  tick(dt){if(mode==='capture'&&capture)capture.clock+=dt;if(mode==='replay'&&clip){elapsed+=dt*Number($('take-rate').value);show(clipPosition(elapsed,clip.duration,$('take-loop').value));if($('take-loop').value==='once'&&elapsed>=clip.duration&&running)requestPause(true);}},
  setRunning(v){running=v;setWorkerRunning(v&&(mode==='live'||mode==='capture'));},
  dispose(){disposed=true;packer?.terminate();}
 };
}
