import assert from 'node:assert/strict';
import { MODES, TONNETZ, TRIANGLES, pitchClass, foldPosition, spiralPosition,
  weightedCells, createHarmonyState, intervalFamily } from '../arsenal/web/piano/harmony-model.js';

assert.equal(Object.keys(MODES).length,9,'eight new modes plus the existing atmosphere');
for(const triangle of TRIANGLES){
  const pcs=triangle.ids.map(i=>TONNETZ[i].pc);
  assert.equal(new Set(pcs).size,3);
  const expected=triangle.minor?[0,3,7]:[0,4,7];
  assert(expected.every(n=>pcs.includes((triangle.root+n)%12)),'every filled face is an actual triad');
}
assert(TRIANGLES.length>12);
assert.equal(pitchClass({letter:5,acc:0}),9);
const e=foldPosition('E'),eb=foldPosition('Eb'),es=foldPosition('E#');
assert.equal(e.x,eb.x);assert.equal(e.y,es.y);assert(eb.z<e.z&&e.z<es.z);
const c=spiralPosition(0),g=spiralPosition(7),e2=spiralPosition(4);
assert(Math.abs(e2.x-c.x)<1e-9&&Math.abs(e2.z-c.z)<1e-9,'major thirds lie above each other');
assert(g.y>c.y&&e2.y>g.y);
const sites=[{x:-.5,y:0,weight:0},{x:.5,y:0,weight:0}];
let cells=weightedCells(sites);
assert(cells[0].every(p=>p[0]<=1e-8));assert(cells[1].every(p=>p[0]>=-1e-8));
cells=weightedCells([{...sites[0],weight:.5},sites[1]]);
assert(Math.max(...cells[0].map(p=>p[0]))>.2,'more energy displaces a shared boundary');
for(const poly of cells)for(const p of poly)assert(p.every(Number.isFinite));
assert.equal(intervalFamily(7),'fifth');assert.equal(intervalFamily(1),'tension');

const state=createHarmonyState();let time=0;
const notes=new Map([[57,{midi:57,velocity:40,at:0,end:null,held:true}],[60,{midi:60,velocity:40,at:0,end:null,held:true}],[64,{midi:64,velocity:40,at:0,end:null,held:true}]]);
function tick(n=1){for(let i=0;i<n;i++){time+=1/60;state.update(notes,1/60,time)}}
tick(60);const a=state.voices.find(v=>v.midi===57),eVoice=state.voices.find(v=>v.midi===64),id=eVoice.id,born=eVoice.born;
const phase=eVoice.phase;notes.get(64).at=time;notes.get(64).velocity=120;state.update(notes,0,time);
assert.equal(eVoice.id,id);assert.equal(eVoice.born,born);assert.equal(eVoice.phase,phase);assert(eVoice.heat>.7);
notes.get(64).end=time;notes.set(65,{midi:65,velocity:70,at:time,end:null,held:true});tick();
assert.equal(state.voices.find(v=>v.midi===65).id,id);assert.equal(state.voices.find(v=>v.midi===57),a);
notes.get(57).held=false;tick(60);assert(a.active,'pedalled released note remains active while end is null');
// The inherited resonance envelope has a 1.5-second time constant, not a
// five-second lifetime: allow its level to reach the .003 retirement threshold.
notes.get(57).end=time;tick(600);assert(!state.voices.includes(a),'released resonance eventually leaves');
for(let i=0;i<500;i++){notes.get(65).at=time;tick()}
assert(state.voices.every(v=>v.pulses.length<=6));
state.update(new Map(),.01,-1);assert.equal(state.voices.length,0,'backward seek clears previous parts');
console.log('PASS eight harmony modes: musical topology, power cells, continuous voices, repeat energy, pedal, bounded memory, seek');
