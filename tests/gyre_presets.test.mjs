import test from 'node:test';
import assert from 'node:assert/strict';
import {loadPresets,savePreset,PRESET_STORAGE_KEY} from '../arsenal/web/piano/gyre-presets.mjs';
import {WORLD_DEFAULTS,PRESETS} from '../arsenal/web/piano/gyre-motion.mjs';
import {RAY_DEFAULTS,RAY_STYLES} from '../arsenal/web/piano/gyre-light-rays.mjs';
import {FLIGHT_DEFAULTS} from '../arsenal/web/piano/gyre-flight-motion.mjs';

const storage = () => {const values=new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v)};};
const preset = (id='one') => ({id,name:'Golden wings',study:'ember',resolution:'native',mechanism:true,orbit:false,time:31,
  settings:{spin:.54,precession:-.066,tilt:88,wobble:28,memory:6.2,pulse:0,count:24,style:'beads',palette:'ember',motion:'axial',stem:3.25,reach:2.5,tail:'flicker',tailAmount:.75,tailRate:6},
  camera:{position:[10,6.3,13.5],target:[0,.3,0]}});

test('round-trips the user sculpture, camera, zero pulse and reverse precession',()=>{
  const s=storage(),p=preset();savePreset(s,p);assert.deepEqual(loadPresets(s),[{...p,settings:{...FLIGHT_DEFAULTS,...RAY_DEFAULTS,...WORLD_DEFAULTS,...p.settings}}]);
  p.settings.reach=4;assert.equal(loadPresets(s)[0].settings.reach,2.5);
});
test('an old library gets additive defaults without rewriting any stored bytes',()=>{
  const s=storage(),raw=JSON.stringify({version:1,presets:[preset()]});s.setItem(PRESET_STORAGE_KEY,raw);
  const p=loadPresets(s)[0];assert.equal(p.settings.wind,0);assert.equal(p.settings.view,'outside');assert.equal(p.settings.sculpture,'gyre');
  assert.equal(s.getItem(PRESET_STORAGE_KEY),raw);
  assert.equal(p.settings.radiance,1);assert.equal(p.settings.blackout,false);assert.equal(p.settings.style,'beads');
});
test('new world and rider controls survive save and reload alongside an old preset',()=>{
  const s=storage();savePreset(s,preset());
  const p={...preset('ride'),study:'wind',settings:{...FLIGHT_DEFAULTS,...RAY_DEFAULTS,...WORLD_DEFAULTS,...preset().settings,...PRESETS.wind,reactive:true}};
  savePreset(s,p);assert.deepEqual(loadPresets(s)[1],p);assert.equal(loadPresets(s)[0].settings.wind,0);
});
test('an update replaces only its selected preset and new saves retain previous versions',()=>{
  const s=storage();savePreset(s,preset());savePreset(s,preset('two'));
  const p=preset();p.settings.reach=3;savePreset(s,p);
  assert.equal(loadPresets(s).length,2);assert.equal(loadPresets(s)[1].settings.reach,2.5);
  assert.equal(loadPresets(s)[0].settings.reach,3);
});
test('malformed or future libraries are left intact when saving fails',()=>{
  for(const raw of ['{broken','{"version":2,"presets":[]}']){
    const s=storage();s.setItem(PRESET_STORAGE_KEY,raw);assert.throws(()=>savePreset(s,preset()));assert.equal(s.getItem(PRESET_STORAGE_KEY),raw);
  }
});
test('invalid geometry, names and cameras cannot overwrite a valid library',()=>{
  const s=storage();savePreset(s,preset());const before=s.getItem(PRESET_STORAGE_KEY);
  for(const mutate of [p=>p.settings.reach=NaN,p=>p.settings.count=10000,p=>p.name=' ',p=>p.camera.position=[0,.3,0]]){
    const p=preset();mutate(p);assert.throws(()=>savePreset(s,p));assert.equal(s.getItem(PRESET_STORAGE_KEY),before);
  }
});
test('storage exhaustion reports failure without claiming a saved preset',()=>{
  const s=storage();savePreset(s,preset());const before=s.getItem(PRESET_STORAGE_KEY);
  s.setItem=()=>{throw new Error('Quota exceeded');};assert.throws(()=>savePreset(s,preset('two')),/Quota/);
  assert.equal(s.getItem(PRESET_STORAGE_KEY),before);
});

test('new ray materials and OLED settings round trip without replacing old records',()=>{
 const s=storage();savePreset(s,preset());
 for(const style of RAY_STYLES){const p=preset(style);p.settings={...FLIGHT_DEFAULTS,...RAY_DEFAULTS,...WORLD_DEFAULTS,...p.settings,style,raySpread:.83,radiance:.7,blackout:true};savePreset(s,p);assert.deepEqual(loadPresets(s).at(-1),p);}
 assert.equal(loadPresets(s).length,4);assert.equal(loadPresets(s)[0].settings.style,'beads');
 const raw=s.getItem(PRESET_STORAGE_KEY);
 for(const patch of [{style:'unknown'},{raySpread:NaN},{radiance:20},{blackout:'true'}]){const p=preset('invalid');Object.assign(p.settings,patch);assert.throws(()=>savePreset(s,p));assert.equal(s.getItem(PRESET_STORAGE_KEY),raw);}
});
test('flight settings and lap position persist without enabling old presets',()=>{
 const s=storage();savePreset(s,preset());assert.equal(loadPresets(s)[0].settings.flightEnabled,false);
 const p=preset('flight');p.settings={...FLIGHT_DEFAULTS,...RAY_DEFAULTS,...WORLD_DEFAULTS,...p.settings,flightEnabled:true,view:'pilot',flightCount:13,flightSpread:.6};p.flight={distance:123.5,clock:76};savePreset(s,p);assert.deepEqual(loadPresets(s).at(-1),p);
 const raw=s.getItem(PRESET_STORAGE_KEY);for(const patch of [{flightCount:99},{flightSpeed:Infinity},{formation:'unknown'},{flightEnabled:false,view:'chase'}]){const bad=structuredClone(p);Object.assign(bad.settings,patch);assert.throws(()=>savePreset(s,bad));assert.equal(s.getItem(PRESET_STORAGE_KEY),raw);}
 const bad=structuredClone(p);bad.flight.clock=NaN;assert.throws(()=>savePreset(s,bad));
 p.flight.frame={right:[1,0,0],tangent:[0,0,1]};savePreset(s,p);assert.deepEqual(loadPresets(s).at(-1).flight,p.flight);
 for(const frame of [null,{right:[0,0,0],tangent:[0,0,1]},{right:[1,0,0],tangent:[1,0,0]}]){const bad=structuredClone(p);bad.flight.frame=frame;assert.throws(()=>savePreset(s,bad));}
});
