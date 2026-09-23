import test from 'node:test';
import assert from 'node:assert/strict';
import {FlightCourse,FLIGHT_DEFAULTS,formationOffset,fleetPose} from '../arsenal/web/piano/gyre-flight-motion.mjs';
import {WORLD_DEFAULTS,emitterAt,windOffset} from '../arsenal/web/piano/gyre-motion.mjs';
const state={...WORLD_DEFAULTS,...FLIGHT_DEFAULTS,spin:.18,precession:.008,tilt:88,wobble:28,memory:10.2,count:24,motion:'axial',stem:3.75,reach:4.5,tail:'flicker',tailAmount:1};
const distance=(a,b)=>Math.hypot(...a.map((x,i)=>x-b[i]));
const dot=(a,b)=>a.reduce((n,x,i)=>n+x*b[i],0);
test('the main course span follows the same ray history, including wind',()=>{
 const s={...state,wind:.7},c=new FlightCourse().update(31,s),u=(Math.round(s.flightTrack*(s.count-1))+.5)/s.count;
 for(const i of [0,50,130,192]){const age=1-i/c.steps,p=emitterAt(31-age*s.memory,u,s),w=windOffset(age*s.memory,31,u,s);assert(distance(Array.from(c.positions.slice(i*3,i*3+3)),p.map((v,k)=>v+w[k]))<1e-5);}
});
test('loop position and transported orientation join without a lap teleport',()=>{
 const c=new FlightCourse().update(31,state),a=c.sample(c.length-.00001),b=c.sample(.00001);
 assert(distance(a.position,b.position)<.0001);assert(dot(a.forward,b.forward)>.999);assert(dot(a.right,b.right)>.999);
 assert(distance(c.sample(2).position,c.sample(2+c.length*4).position)<1e-8);
});
test('spark and firefly courses include their material-specific particle drift',()=>{
 const led=Math.round(state.flightTrack*(state.count-1)),u=(led+.5)/state.count,age=.5,seconds=age*state.memory,t=31-seconds,seed=led*17.13+t*1.7,base=emitterAt(t,u,state);
 for(const style of ['sparks','fireflies']){
  const s={...state,style,raySpread:.55},c=new FlightCourse().update(31,s);
  const drift=style==='sparks'?[Math.sin(seed)*.1+Math.sin(seconds*1.7+seed)*.025,.12+Math.sin(seconds*.7+seed)*.025,Math.cos(seed*.83)*.1+Math.cos(seconds*1.2+seed)*.025]:[Math.sin(seed)*.06*.95+Math.sin(seed+seconds*.7)*.018,.08*.95+Math.cos(seed*.8+seconds*.5)*.018,Math.cos(seed*.83)*.06*.95+Math.sin(seed*.7)*.018];
  assert(distance(Array.from(c.positions.slice(96*3,97*3)),base.map((v,k)=>v+drift[k]*seconds))<1e-5);
 }
});
test('camera frames remain orthonormal across time, tight loops and reverse spin',()=>{
 for(const spin of [-.5,0,.18]){const c=new FlightCourse();for(let t=0;t<12;t+=.37){c.update(t,{...state,spin});for(let i=0;i<20;i++){const f=c.sample(i*c.length/20);for(const key of ['forward','right','up'])assert(Math.abs(Math.hypot(...f[key])-1)<1e-6);assert(Math.abs(dot(f.forward,f.up))<1e-6);assert(Math.abs(dot(f.forward,f.right))<1e-6);assert(f.position.every(Number.isFinite));}}}
});
test('a completely still ray stays finite and does not invent travel',()=>{
 const c=new FlightCourse().update(31,{...state,spin:0,precession:0,wobble:0});assert(c.stationary);assert.deepEqual(c.sample(0),c.sample(1000));
});
test('spacing axes act independently and choreography blends across cycle boundaries',()=>{
 const s={...state,formation:'arrowhead',flightBreak:0},a=formationOffset(3,0,s),b=formationOffset(3,0,{...s,flightSpread:s.flightSpread*2});assert.equal(b[0],a[0]*2);assert.equal(b[1],a[1]);assert.equal(b[2],a[2]);
 for(let t=10;t<=80;t+=10)for(let i=0;i<13;i++)assert(distance(formationOffset(i,t-.0001,state),formationOffset(i,t+.0001,state))<.001);
 const c=new FlightCourse().update(31,state);for(let i=0;i<13;i++)assert(fleetPose(c,4,31,i,state).position.every(Number.isFinite));
});
