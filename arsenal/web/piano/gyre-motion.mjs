// A kinematic light sculpture: independent spin, precession, and nutation.
export const TAU = Math.PI * 2;
export const WORLD_DEFAULTS = Object.freeze({sculpture:'gyre',view:'outside',weave:.6,petals:5,wind:0,turbulence:.25,reactive:false});
export const PRESETS = {
  silk: { name: 'Silk orbit', spin: .58, precession: .087, tilt: 54, wobble: 9, memory: 7.5, pulse: 1.4, count: 24, style: 'silk', palette: 'tide' },
  lattice: { name: 'Prismatic lattice', spin: .83, precession: .14, tilt: 67, wobble: 3, memory: 5.8, pulse: 2.8, count: 32, style: 'beads', palette: 'prism' },
  ember: { name: 'Ember garden', spin: .31, precession: -.095, tilt: 72, wobble: 17, memory: 10, pulse: 1.1, count: 24, style: 'sparks', palette: 'ember' },
  bloom: { name: 'Violet bloom', spin: -.46, precession: .065, tilt: 38, wobble: 22, memory: 11, pulse: .7, count: 18, style: 'silk', palette: 'violet' },
  braid: {name:'Tidal braid',spin:.12,precession:.018,tilt:42,wobble:6,memory:13,pulse:0,count:24,style:'silk',palette:'opal',sculpture:'braid',view:'outside',weave:.74,petals:5,wind:0,turbulence:.2,tail:'dissolve',tailAmount:.6,tailRate:2,stem:3.25,reach:2.5},
  pendulum: {name:'Pendulum garden',spin:.15,precession:-.016,tilt:28,wobble:10,memory:13,pulse:0,count:24,style:'silk',palette:'violet',sculpture:'pendulum',view:'outside',weave:.7,petals:5,wind:0,turbulence:.2,tail:'flicker',tailAmount:.8,tailRate:3,stem:3.25,reach:2.5},
  wind: {name:'Solar wind',spin:.12,precession:-.023,tilt:72,wobble:12,memory:9,pulse:0,count:32,style:'silk',palette:'ember',sculpture:'gyre',view:'ride',weave:.6,petals:5,wind:1.4,turbulence:.5,tail:'dissolve',tailAmount:.8,tailRate:4,stem:3.25,reach:2.5},
};
export function armPoint(u, out = [0, 0, 0], axial = true, stem = 3.25, reach = 1.6) {
  const d = .65 + Math.max(0, Math.min(1, u)) * (stem + reach - .65);
  out[0] = axial ? 0 : Math.min(d, stem);
  out[1] = axial ? Math.min(d, stem) : 0; out[2] = Math.max(0, d - stem);
  return out;
}
export function anglesAt(t, state, out = [0, 0, 0]) {
  out[0] = t * TAU * state.precession;
  out[1] = (state.tilt + state.wobble * Math.sin(t * TAU * .19)) * Math.PI / 180;
  out[2] = t * TAU * state.spin;
  return out;
}
export function positionAt(t, u, state, out = [0, 0, 0]) {
  armPoint(u, out, state.motion !== 'sweep', state.stem, state.reach);
  return rotateAt(t,out,state,out);
}
export function rotateAt(t, point, state, out = [0,0,0]) {
  const spin = t * TAU * state.spin, precession = t * TAU * state.precession;
  const tilt = (state.tilt + state.wobble * Math.sin(t * TAU * .19)) * Math.PI / 180;
  const x = Math.cos(spin) * point[0] + Math.sin(spin) * point[2];
  const z = -Math.sin(spin) * point[0] + Math.cos(spin) * point[2];
  const tx = Math.cos(tilt) * x - Math.sin(tilt) * point[1];
  const ty = Math.sin(tilt) * x + Math.cos(tilt) * point[1];
  out[0] = Math.cos(precession) * tx + Math.sin(precession) * z;
  out[1] = ty;
  out[2] = -Math.sin(precession) * tx + Math.cos(precession) * z;
  return out;
}
// CPU head positions and the trail shader use the same parametric paths.
export function emitterAt(t,u,state,out=[0,0,0],harmony=[0,0,0]) {
  const kind=state.sculpture||'gyre',weave=state.weave??.6,petals=state.petals??5;
  if(kind==='gyre') {
    positionAt(t,u,state,out);
  } else {
    const phase=t*TAU*state.spin,open=1+harmony[0]*.22;
    if(kind==='braid') {
      const led=Math.floor(u*state.count),strand=led%3,lane=Math.floor(led/3)/Math.max(1,Math.ceil(state.count/3)-1)-.5;
      const a=phase+lane*.1,b=phase*(petals*.5+harmony[1]*.3)+strand*TAU/3+lane*.3;
      const r=(.45+weave*.9+lane*.18)*open,R=1+state.reach*.5+Math.cos(b)*r;
      out[0]=R*Math.cos(a);out[1]=Math.sin(b)*r;out[2]=R*Math.sin(a);
    } else {
      const a=phase+u*.35,R=(.6+u*.65)*(1.7+state.reach*.5)*open,petal=petals-1+harmony[1]*.15;
      out[0]=R*(.72*Math.cos(a)+.28*Math.cos(petal*a));
      out[2]=R*(.72*Math.sin(a)-.28*Math.sin(petal*a));
      out[1]=-.8+weave*.9*Math.sin(a*2+u*2.5);
    }
    const tilt=(state.tilt+state.wobble*Math.sin(t*TAU*.19))*Math.PI/180*.35,x=out[0],y=out[1];
    out[0]=Math.cos(tilt)*x-Math.sin(tilt)*y;out[1]=Math.sin(tilt)*x+Math.cos(tilt)*y;
    const p=t*TAU*state.precession,z=out[2];out[2]=-Math.sin(p)*out[0]+Math.cos(p)*z;out[0]=Math.cos(p)*out[0]+Math.sin(p)*z;
  }
  return out;
}
export function windOffset(age,t,u,state,out=[0,0,0]) {
  const wind=state.wind||0,flutter=(state.turbulence??.25)*wind*age*.3;
  out[0]=Math.sin(t*1.7+u*17+age*.8)*flutter;
  out[1]=Math.sin(t*.9+u*23-age*.6)*flutter;
  out[2]=-wind*age*1.5;
  return (state.sculpture||'gyre')==='gyre'?rotateAt(t,out,state,out):out;
}
export function riderPose(t,state) {
  const stem=state.stem??3.25,reach=state.reach??1.6,axial=state.motion!=='sweep';
  const x=axial?0:stem,y=axial?stem:0;
  return {position:rotateAt(t,[x+.32,y+.35,reach+.65],state),target:rotateAt(t,[x,y-.4,reach-6],state),up:rotateAt(t,[0,1,0],state)};
}
export function bufferSize(cssWidth, cssHeight, dpr, mode = 'native') {
  const w = Math.max(1, cssWidth), h = Math.max(1, cssHeight);
  const scale = mode === '4k' ? Math.min(3840 / w, 2160 / h) : Math.max(1, dpr);
  return [Math.max(1, Math.round(w * scale)), Math.max(1, Math.round(h * scale))];
}
