import {createTakeController} from './flow-take-controller.mjs';
// Browser/scene adapter. The reusable primitives live in lib/flow and need no DOM.
export function createWindTunnel({triangles,settings,onPaths,onReplayFrame,onReplayTime,getScene,restoreScene,requestPause,onDraw,onError}){
 let worker=null;
 const canvas=document.getElementById('stage'),label=document.getElementById('solver-status'),yaw=document.getElementById('yaw'),out=document.getElementById('yaw-value');
 let revision=0,started=false,running=false,disposed=false,resolve,reject,debounce=0,previewRevision=-1,current={...settings};
 const ready=new Promise((a,b)=>{resolve=a;reject=b;});
 const parsed=Number(new URLSearchParams(location.search).get('yaw')??0);yaw.value=String(Math.max(-25,Math.min(25,Number.isFinite(parsed)?parsed:0)));
 function config(){return {...current,yaw:Number(yaw.value)};}
 function send(){clearTimeout(debounce);if(disposed||!worker||take.mode!=='live')return;revision++;if(!running)previewRevision=revision;label.textContent='Shaping the current…';worker.postMessage({type:'configure',revision,settings:config()});}
 yaw.addEventListener('input',()=>{out.textContent=yaw.value+'°';const url=new URL(location.href);url.searchParams.set('yaw',yaw.value);history.replaceState(null,'',url);clearTimeout(debounce);debounce=setTimeout(send,140);});out.textContent=yaw.value+'°';
 const take=createTakeController({getScene:()=>({...getScene(),settings:{...getScene().settings,yaw:Number(yaw.value)}}),
  restoreScene:meta=>{clearTimeout(debounce);current={...meta.settings};yaw.value=String(Math.max(-25,Math.min(25,Number(meta.settings.yaw)||0)));out.textContent=yaw.value+'°';restoreScene(meta);},
  onPair:onReplayFrame,onTime:onReplayTime,onDraw,requestPause,
  setWorkerRunning:value=>worker?.postMessage({type:'running',value}),setCapture:value=>{clearTimeout(debounce);if(value&&worker)worker.postMessage({type:'configure',revision:++revision,settings:config()});worker?.postMessage({type:'capture',value});},
  onLive:()=>{current={...getScene().settings};if(!worker)startWorker();else send();}
 });
 function startWorker(){
 worker=new Worker(new URL('./wind-tunnel-worker.mjs',import.meta.url),{type:'module'});
 worker.onmessage=({data:m})=>{
  if(disposed)return;
  if(m.type==='error'){const e=new Error(m.message);reject(e);onError(e);return;}
  if(m.type==='paused'){canvas.dataset.solverPaused=String(m.steps);return;}
  if(m.type!=='paths'||m.revision!==revision||take.playback||take.mode==='packing')return;
  // Pause is a true freeze; a step already in flight may finish in the worker,
  // but it cannot change the displayed geometry after the user pauses.
  if(started&&!running&&m.revision!==previewRevision)return;previewRevision=-1;
  canvas.dataset.solver=JSON.stringify(m.diagnostics);delete canvas.dataset.solverPaused;
  label.textContent=`3D flow · ${m.diagnostics.grid.join(' × ')} · step ${m.diagnostics.steps}${running?'':' · paused'}`;
  document.getElementById('solver-detail').textContent=`Divergence RMS ${m.diagnostics.divergenceRms.toExponential(2)} · solve/transport ${m.diagnostics.stepMs.toFixed(0)} ms · surface ${m.diagnostics.collider.cellSize.toFixed(3)} units`;
  onPaths(m.paths,m.diagnostics);if(!started){started=true;resolve();}take.ready();take.packet(m);
 };
 worker.onerror=e=>{const error=new Error(e.message);reject(error);onError(error);};
 worker.postMessage({type:'init',revision,settings:config(),triangles,running},[triangles.buffer]);triangles=null;
 }
 take.initial().then(loaded=>{if(disposed)return;if(loaded){started=true;resolve();}else startWorker();}).catch(onError);
 return {ready,
  get playback(){return take.playback;},
  tick(dt){take.tick(dt);},
  configure(s){current={...s};if(take.mode==='live'){clearTimeout(debounce);debounce=setTimeout(send,100);}},
  setRunning(value){running=value;take.setRunning(value);if(!take.playback)label.textContent=value?'3D flow · evolving':'3D flow · paused';},
  dispose(){disposed=true;clearTimeout(debounce);worker?.terminate();take.dispose();}
 };
}
