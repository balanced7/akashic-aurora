// Versioned browser storage. A failed read/write never replaces an existing library.
import {WORLD_DEFAULTS,PRESETS} from './gyre-motion.mjs';
import {RAY_DEFAULTS,RAY_STYLES} from './gyre-light-rays.mjs';
import {FLIGHT_DEFAULTS,FLIGHT_RANGES,FORMATIONS} from './gyre-flight-motion.mjs';
export const PRESET_STORAGE_KEY = 'piano.gyre.presets.v1';
const ranges = {spin:[-1.5,1.5],precession:[-.3,.3],tilt:[0,88],wobble:[0,28],memory:[.4,14],pulse:[0,4],stem:[.8,6],reach:[.2,4.5],tailAmount:[0,1],tailRate:[.5,12],weave:[0,1],petals:[2,9],wind:[0,3],turbulence:[0,1],raySpread:[0,1],radiance:[.25,1.5]};
const choices = {motion:['axial','sweep'],style:['silk','beads','sparks',...RAY_STYLES],palette:['tide','prism','ember','violet','opal'],tail:['fade','flicker','dissolve'],count:[12,18,24,32,40],sculpture:['gyre','braid','pendulum'],view:['outside','ride']};
const finite = (n,min,max) => typeof n === 'number' && Number.isFinite(n) && n >= min && n <= max;
Object.assign(ranges,FLIGHT_RANGES);choices.formation=FORMATIONS;choices.flightCount=[5,9,13];choices.view.push('chase','pilot');
export function validatePreset(value) {
  if (!value || typeof value.id !== 'string' || !value.id || value.id.length > 100 || typeof value.name !== 'string' || !value.name.trim() || value.name.length > 64) throw new Error('This preset has an invalid name or ID.');
  if (!Object.hasOwn(PRESETS,value.study) || !['native','4k'].includes(value.resolution)) throw new Error('This preset uses an unknown study or resolution.');
  const s={...FLIGHT_DEFAULTS,...RAY_DEFAULTS,...WORLD_DEFAULTS,...value.settings};
  if (!value.settings || Object.entries(ranges).some(([key,[min,max]]) => !finite(s[key],min,max)) || Object.entries(choices).some(([key,options]) => !options.includes(s[key])) || typeof s.reactive!=='boolean'||typeof s.blackout!=='boolean') throw new Error('This preset contains invalid sculpture settings.');
  if(typeof s.flightEnabled!=='boolean'||(['chase','pilot'].includes(s.view)&&!s.flightEnabled))throw new Error('This preset contains invalid flight settings.');
  if(value.flight!==undefined&&(!value.flight||!finite(value.flight.distance,0,1e9)||!finite(value.flight.clock,0,1e9)))throw new Error('This preset contains invalid flight playback.');
  if(value.flight?.frame!==undefined){
    const f=value.flight.frame,v=[f?.right,f?.tangent];
    if(v.some(a=>!Array.isArray(a)||a.length!==3||a.some(n=>!finite(n,-1.001,1.001))||Math.abs(Math.hypot(...a)-1)>.001)||Math.abs(v[0].reduce((sum,n,i)=>sum+n*v[1][i],0))>.001)throw new Error('This preset contains an invalid flight orientation.');
  }
  if (typeof value.mechanism !== 'boolean' || typeof value.orbit !== 'boolean' || !finite(value.time,0,1e9)) throw new Error('This preset contains invalid playback settings.');
  const vectors=[value.camera?.position,value.camera?.target];
  if (vectors.some(v => !Array.isArray(v) || v.length !== 3 || v.some(n => !finite(n,-10000,10000))) || vectors[0].every((n,i)=>n === vectors[1][i])) throw new Error('This preset contains an invalid camera.');
  return {...value,name:value.name.trim(),settings:s};
}
export function loadPresets(storage) {
  const raw=storage.getItem(PRESET_STORAGE_KEY);
  if (raw === null) return [];
  let data;
  try {data=JSON.parse(raw);} catch {throw new Error('Saved presets could not be read. Your stored library has been left untouched.');}
  if (data?.version !== 1 || !Array.isArray(data.presets)) throw new Error('This preset library uses an unsupported format.');
  const presets=data.presets.map(validatePreset);
  if (new Set(presets.map(p=>p.id)).size !== presets.length) throw new Error('This preset library contains duplicate IDs.');
  return presets;
}
export function savePreset(storage,preset) {
  const next=validatePreset(preset),presets=loadPresets(storage),index=presets.findIndex(p=>p.id === next.id);
  if (index < 0) presets.push(next); else presets[index]=next;
  storage.setItem(PRESET_STORAGE_KEY,JSON.stringify({version:1,presets}));
  return presets;
}
