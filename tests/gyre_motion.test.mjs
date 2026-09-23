import { test } from 'node:test';
import assert from 'node:assert/strict';
import { armPoint, positionAt, emitterAt, windOffset, riderPose, rotateAt, bufferSize, PRESETS, WORLD_DEFAULTS } from '../arsenal/web/piano/gyre-motion.mjs';
const close = (a,b) => assert.ok(Math.abs(a-b)<1e-9, `${a} != ${b}`);
test('axial spin leaves the long stem fixed and circles the bent tip around it', () => {
  const state={...PRESETS.ember,motion:'axial',spin:.25,precession:0,tilt:0,wobble:0};
  for(const t of [0,.5,1,2,4]) {
    const stem=positionAt(t,.25,state);
    close(stem[0],0); close(stem[1],1.7); close(stem[2],0);
    const tip=positionAt(t,1,state);
    close(tip[1],3.25); close(Math.hypot(tip[0],tip[2]),1.6);
  }
  const tip=positionAt(1,1,state);
  close(tip[0],1.6); close(tip[2],0);
});

test('spin stays on the long stem after tilting the axis', () => {
  const state={...PRESETS.ember,motion:'axial',precession:0,wobble:0};
  const initial=positionAt(0,.25,state);
  for(const t of [.5,2,10])positionAt(t,.25,state).forEach((v,i)=>close(v,initial[i]));
});
test('rotation preserves the radius of every emitter across presets and time', () => {
  for(const preset of Object.values(PRESETS)) for(const motion of ['axial','sweep']) for(const t of [-100,0,.17,30,10000]) for(const u of [0,.25,.62,1]) {
    close(Math.hypot(...positionAt(t,u,{...preset,motion})),Math.hypot(...armPoint(u,undefined,true,preset.stem,preset.reach)));
  }
});
test('the optional planar sweep retains the original perpendicular spin', () => {
  const state={...PRESETS.silk,motion:'sweep',spin:.25,precession:0,tilt:0,wobble:0};
  positionAt(0,1,state).forEach((v,i)=>close(v,[3.25,0,1.6][i]));
  positionAt(1,1,state).forEach((v,i)=>close(v,[1.6,0,-3.25][i]));
});
test('independent segment lengths keep the bend joined and the spinning tip on its shaft', () => {
  for(const stem of [.8,3.25,6]) for(const reach of [.2,1.6,4.5]) {
    const elbow=(stem-.65)/(stem+reach-.65);
    armPoint(elbow,undefined,true,stem,reach).forEach((v,i)=>close(v,[0,stem,0][i]));
    armPoint(1,undefined,false,stem,reach).forEach((v,i)=>close(v,[stem,0,reach][i]));
    const state={...PRESETS.silk,stem,reach,tilt:0,wobble:0,precession:0};
    for(const t of [0,.17,9]){
      const tip=positionAt(t,1,state);close(tip[1],stem);close(Math.hypot(tip[0],tip[2]),reach);
    }
  }
});
test('zero tilt and wobble collapse spin and precession onto one axis', () => {
  const a={...PRESETS.silk,tilt:0,wobble:0};
  const b={...a,spin:a.spin+a.precession,precession:0};
  for(const t of [0,.53,4,9]) positionAt(t,.8,a).forEach((v,i)=>close(v,positionAt(t,.8,b)[i]));
});
test('precession alone moves a tilted rotor out of its original plane', () => {
  const s={...PRESETS.silk,spin:0,wobble:0,precession:.25,tilt:60};
  const a=positionAt(0,0,s), b=positionAt(1,0,s);
  close(a[2],0); close(b[0],0); close(a[1],b[1]); assert.ok(Math.abs(b[2])>.3);
});
test('4K fit preserves aspect, native uses device pixels, zero-sized layouts stay valid', () => {
  assert.deepEqual(bufferSize(1920,1080,2),[3840,2160]);
  assert.deepEqual(bufferSize(1000,1000,1,'4k'),[2160,2160]);
  assert.deepEqual(bufferSize(2000,1000,1,'4k'),[3840,1920]);
  assert.deepEqual(bufferSize(0,0,1),[1,1]);
});

test('original world stays exactly on the existing arm path',()=>{
  const s={...WORLD_DEFAULTS,...PRESETS.ember,stem:3.25,reach:2.5};
  for(const t of [0,31,107.3])for(const u of [.1,.6,.98])assert.deepEqual(emitterAt(t,u,s),positionAt(t,u,s));
});
test('new emitter paths remain finite and bounded across controls and long runs',()=>{
  for(const preset of [PRESETS.braid,PRESETS.pendulum])for(const petals of [2,5,9])for(const weave of [0,1])for(const t of [0,.1,31,100000])for(const u of [.01,.4,.99]){
    const point=emitterAt(t,u,{...WORLD_DEFAULTS,...preset,petals,weave},undefined,[1,1,1]);
    assert.ok(point.every(Number.isFinite));assert.ok(Math.hypot(...point)<8);
  }
});
test('the braid has three separate strands and harmony changes its form continuously',()=>{
  const s={...WORLD_DEFAULTS,...PRESETS.braid};
  const points=[0,1,2].map(i=>emitterAt(1,(i+.5)/s.count,s));
  assert.ok(Math.hypot(...points[0].map((x,i)=>x-points[1][i]))>.5);
  const base=emitterAt(1,.4,s),near=emitterAt(1,.4,s,undefined,[.001,.001,0]),open=emitterAt(1,.4,s,undefined,[1,1,0]);
  assert.ok(Math.hypot(...base.map((x,i)=>x-near[i]))<.01);assert.notDeepEqual(base,open);
});
test('wind never displaces a live head and grows smoothly into older light',()=>{
  const s={...WORLD_DEFAULTS,...PRESETS.wind,turbulence:0};
  for(const t of [0,31,1000]){
    close(Math.hypot(...windOffset(0,t,.5,s)),0);
    close(Math.hypot(...windOffset(2,t,.5,s)),s.wind*3);
    const noWind=windOffset(8,t,.4,{...s,wind:0});close(Math.hypot(...noWind),0);
  }
});
test('rider camera is rigidly attached to the final leg through every rotation',()=>{
  const s={...WORLD_DEFAULTS,...PRESETS.wind};let distance;
  for(const t of [0,.13,3,90,10000]){
    const pose=riderPose(t,s),tip=positionAt(t,1,s),offset=pose.position.map((x,i)=>x-tip[i]);
    const length=Math.hypot(...offset);if(distance===undefined)distance=length;else close(length,distance);
    close(Math.hypot(...pose.up),1);assert.ok(pose.position.every(Number.isFinite));
    const x=rotateAt(t,[1,0,0],s),z=rotateAt(t,[0,0,1],s);close(x.reduce((sum,v,i)=>sum+v*z[i],0),0);
    assert.ok(Math.hypot(...pose.target.map((x,i)=>x-pose.position[i]))>5);
  }
});
