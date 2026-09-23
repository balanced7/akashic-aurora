import {emitterAt,windOffset} from './gyre-motion.mjs';
export const FLIGHT_DEFAULTS=Object.freeze({flightEnabled:false,formation:'ballet',flightCount:9,flightSpeed:1.6,flightSpread:.38,flightSpacing:.4,flightHeight:.18,flightBreak:.45,flightBank:.25,flightTrack:.86});
export const FLIGHT_RANGES=Object.freeze({flightSpeed:[.2,5],flightSpread:[.1,1.4],flightSpacing:[.15,1.5],flightHeight:[0,1],flightBreak:[0,1],flightBank:[0,1],flightTrack:[0,1]});
export const FORMATIONS=['ballet','arrowhead','fan','file','helix'];
const TAU=Math.PI*2,clamp=(x,a,b)=>Math.max(a,Math.min(b,x)),mix=(a,b,t)=>a+(b-a)*t;
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const normal=(a,fallback=[0,0,1])=>{const l=Math.hypot(...a);return l>1e-9?a.map(v=>v/l):[...fallback];};
const sub=(a,b)=>a.map((v,i)=>v-b[i]);
const read=(a,i)=>Array.from(a.subarray(i*3,i*3+3));
function rotate(v,axis,angle){const c=Math.cos(angle),s=Math.sin(angle),w=cross(axis,v),d=dot(axis,v)*(1-c);return v.map((n,i)=>n*c+w[i]*s+axis[i]*d);}
function transport(r,a,b){const axis=cross(a,b),length=Math.hypot(...axis),cos=clamp(dot(a,b),-1,1);let next=length>1e-8?rotate(r,axis.map(v=>v/length),Math.atan2(length,cos)):r;return normal(next.map((v,i)=>v-b[i]*dot(next,b)),r);}
const smooth=t=>{t=clamp(t,0,1);return t*t*t*(t*(t*6-15)+10);};

// A renderer-independent, closed rail. The first span is the visible historical
// centreline; the last span is an explicit smooth return, never a modulo teleport.
export class FlightCourse {
 constructor(steps=192,bridge=48){this.steps=steps;this.bridge=bridge;this.count=steps+bridge;const n=this.count+1;this.positions=new Float32Array(n*3);this.tangents=new Float32Array(n*3);this.rights=new Float32Array(n*3);this.distances=new Float64Array(n);this.length=0;this.stationary=false;this.firstRight=null;this.firstTangent=null;}
 update(time,state,harmony=[0,0,0]){
  const {steps,bridge,count}=this,led=Math.round(state.flightTrack*(state.count-1)),u=(led+.5)/state.count,wind=[0,0,0],windState={...state,turbulence:state.turbulence+harmony[1]*.25};
  for(let i=0;i<=steps;i++){
   const age=1-i/steps,t=time-age*state.memory,p=emitterAt(t,u,state,undefined,harmony);windOffset(age*state.memory,time,u,windState,wind);
   for(let k=0;k<3;k++)p[k]+=wind[k];
   if(state.tail==='dissolve'){const s=led*2.31+t*2,h=clamp((age-.55)/.45,0,1),drift=h*h*(3-2*h)*state.tailAmount*.28;p[0]+=Math.sin(s+age*5)*drift;p[1]+=Math.cos(s*.7+age*3)*drift;p[2]+=Math.sin(s*.8-age*4)*drift;}
   // Match each material's continuous centreline. Filigree's three strands
   // surround this rail; fireflies are discrete samples along its drift field.
   const seconds=age*state.memory,seed=led*17.13+t*1.7;
   if(state.style==='sparks'){
    p[0]+=(Math.sin(seed)*.1+Math.sin(seconds*1.7+seed)*.025)*seconds;
    p[1]+=(.12+Math.sin(seconds*.7+seed)*.025)*seconds;
    p[2]+=(Math.cos(seed*.83)*.1+Math.cos(seconds*1.2+seed)*.025)*seconds;
   }else if(state.style==='fireflies'){
    const spread=.4+(state.raySpread??.55);
    p[0]+=(Math.sin(seed)*.06*spread+Math.sin(seed+seconds*.7)*.018)*seconds;
    p[1]+=(.08*spread+Math.cos(seed*.8+seconds*.5)*.018)*seconds;
    p[2]+=(Math.cos(seed*.83)*.06*spread+Math.sin(seed*.7)*.018)*seconds;
   }
   this.positions.set(p,i*3);
  }
  const start=read(this.positions,0),end=read(this.positions,steps),d0=normal(sub(read(this.positions,1),start)),d1=normal(sub(end,read(this.positions,steps-1))),gap=Math.hypot(...sub(end,start)),handle=Math.max(.15,Math.min(3,gap*.55));
  for(let j=1;j<=bridge;j++){const t=j/bridge,t2=t*t,t3=t2*t;this.positions.set(end.map((v,k)=>(2*t3-3*t2+1)*v+(t3-2*t2+t)*d1[k]*handle+(-2*t3+3*t2)*start[k]+(t3-t2)*d0[k]*handle),(steps+j)*3);}
  this.positions.set(start,count*3);this.distances[0]=0;
  for(let i=1;i<=count;i++)this.distances[i]=this.distances[i-1]+Math.hypot(...sub(read(this.positions,i),read(this.positions,i-1)));
  this.length=this.distances[count];this.stationary=this.distances[steps]<.01;
  for(let i=0;i<count;i++){const prev=read(this.positions,(i-1+count)%count),next=read(this.positions,(i+1)%count);this.tangents.set(normal(sub(next,prev)),i*3);}this.tangents.set(this.tangents.subarray(0,3),count*3);
  const first=read(this.tangents,0);let right=this.firstRight?transport(this.firstRight,this.firstTangent,first):normal(cross(Math.abs(first[1])>.9?[1,0,0]:[0,1,0],first));
  this.firstRight=[...right];this.firstTangent=first;this.rights.set(right,0);
  for(let i=1;i<=count;i++){right=transport(right,read(this.tangents,i-1),read(this.tangents,i));this.rights.set(right,i*3);}
  const initial=read(this.rights,0),last=read(this.rights,count),twist=Math.atan2(dot(first,cross(last,initial)),dot(last,initial));
  for(let i=1;i<=count;i++)this.rights.set(rotate(read(this.rights,i),read(this.tangents,i),twist*this.distances[i]/Math.max(.001,this.length)),i*3);
  this.rights.set(initial,count*3);return this;
 }
 sample(distance){
  const d=this.stationary?0:((distance%this.length)+this.length)%this.length;let lo=0,hi=this.count;
  while(hi-lo>1){const m=(lo+hi)>>1;if(this.distances[m]<=d)lo=m;else hi=m;}
  const f=(d-this.distances[lo])/Math.max(1e-9,this.distances[hi]-this.distances[lo]);
  const blend=a=>read(a,lo).map((v,k)=>mix(v,a[hi*3+k],f)),forward=normal(blend(this.tangents)),raw=blend(this.rights),right=normal(raw.map((v,k)=>v-forward[k]*dot(raw,forward)),[1,0,0]);
  return {position:blend(this.positions),forward,right,up:normal(cross(forward,right),[0,1,0])};
 }
}
export function formationOffset(index,time,state){
 if(index===0)return [0,0,0];const rank=Math.ceil(index/2),side=index%2?1:-1;
 const shapes={arrowhead:[side*rank,rank%2*.35,-rank],fan:[side*rank*1.35,0,-rank*.23],file:[side*.12,side*.18,-index*1.1],helix:[Math.cos(index*2.4+time*.25)*1.5,Math.sin(index*2.4+time*.25)*1.7,-index*.7]};
 let shape=shapes[state.formation];
 if(!shape){const names=['arrowhead','fan','helix','file'],phase=((time/10)%4+4)%4,k=Math.floor(phase),w=smooth((phase-k-.45)/.55);shape=shapes[names[k]].map((v,i)=>mix(v,shapes[names[(k+1)%4]][i],w));}
 const departure=Math.pow(.5-.5*Math.cos(time*TAU/22-rank*.55),3)*state.flightBreak;
 return [(shape[0]+side*departure*1.7)*state.flightSpread,(shape[1]+departure*Math.sin(index*1.9)*1.2)*state.flightHeight,shape[2]*state.flightSpacing];
}
export function fleetPose(course,distance,time,index,state){
 const offset=formationOffset(index,time,state),frame=course.sample(distance+offset[2]);
 frame.position=frame.position.map((v,k)=>v+frame.right[k]*offset[0]+frame.up[k]*offset[1]);return frame;
}
