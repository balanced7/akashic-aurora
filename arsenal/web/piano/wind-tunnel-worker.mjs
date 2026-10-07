import {bakeColumnHull} from '../lib/flow/distance-volume.mjs';
import {FluidGrid} from '../lib/flow/fluid-grid.mjs';
import {traceStreamlines,fanSeeds} from '../lib/flow/streamlines.mjs';
import {oscillatingWake} from '../lib/flow/forces.mjs';

let body,field,settings,revision=0,running=false,timer=0,lastPublish=0,stepMs=0,force,capturing=false;
const wind=yaw=>[Math.cos(yaw*Math.PI/180),0,Math.sin(yaw*Math.PI/180)];
function configure(s){
 const old=settings;settings=s;
 if(field&&old?.yaw!==s.yaw){field.resetWind(wind(s.yaw));field.project(160);}
 force=oscillatingWake({center:[3.8,.85,0],radius:[1.4,1.1,1.25],strength:s.wake*.8,frequency:1.2});
}
function publish(){
 const before=performance.now();
 const direction=wind(settings.yaw),seeds=fanSeeds({count:settings.density,origin:[-4.9*direction[0],.055,-4.9*direction[2]],right:[-direction[2],0,direction[0]]});
 const result=traceStreamlines(field,body,{seeds,end:6.9,clearance:.065+settings.clearance*.3});
 const probe=field.velocity(0,1.9,0);
 let volume=null,grid=null;
 if(capturing){volume=new Float32Array(field.length*4);for(let i=0;i<field.length;i++){for(let a=0;a<3;a++)volume[i*4+a]=field.faces[a].values[i];volume[i*4+3]=field.q[i];}
  grid={size:[field.nx+1,field.ny+1,field.nz+1],cells:[field.nx,field.ny,field.nz],origin:field.origin,h:field.h,layout:'MAC-uvwp'};
 }
 self.postMessage({type:'paths',revision,paths:result.paths,volume,grid,diagnostics:{...field.diagnostics(),stepMs,traceMs:performance.now()-before,clearance:.065+settings.clearance*.3,minDistance:result.minDistance,corrections:result.corrections,probe,collider:{grid:[body.nx,body.ny,body.nz],cellSize:body.h}}},volume?[result.paths.buffer,volume.buffer]:[result.paths.buffer]);
 lastPublish=performance.now();
}
function tick(){
 timer=0;if(!running||!field)return;
 try{
  const now=performance.now();field.step(.065,{iterations:44,force});stepMs=performance.now()-now;
  if(performance.now()-lastPublish>550)publish();
  timer=setTimeout(tick,Math.max(12,90-stepMs));
 }catch(e){running=false;self.postMessage({type:'error',message:e.stack||String(e)});}
}
self.onmessage=({data:m})=>{
 try{
  if(m.type==='init'){
   revision=m.revision;configure(m.settings);const before=performance.now();
   body=bakeColumnHull(m.triangles);
   field=new FluidGrid({distance:(x,y,z)=>body.sample(x,y,z)-.055,wind:wind(settings.yaw)});
   field.project(200,1e-5);stepMs=performance.now()-before;publish();running=m.running;if(running)tick();
  }else if(m.type==='configure'){
   revision=m.revision;configure(m.settings);if(field)publish();
  }else if(m.type==='capture'){
   capturing=m.value;if(capturing&&field)publish();
  }else if(m.type==='running'){
   running=m.value;clearTimeout(timer);timer=0;if(running)tick();else self.postMessage({type:'paused',steps:field?.steps??0});
  }
 }catch(e){running=false;self.postMessage({type:'error',message:e.stack||String(e)});}
};
