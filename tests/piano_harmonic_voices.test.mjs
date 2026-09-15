import assert from 'node:assert/strict';
import {createHarmonicVoices,FIFTHS,fifthIndex,packVoiceLabels} from '../arsenal/web/piano/harmonic-voices.js';
const notes=(...pitches)=>new Map(pitches.map(midi=>[midi,{midi,velocity:70,end:null}]));
const tracker=createHarmonicVoices();
tracker.update(notes(57,60,64),.1,0);
const [a,c,e]=tracker.voices, eid=e.id;
for(let i=1;i<=10;i++)tracker.update(notes(57,60,64),.1,i*.1);
const phase=e.phase, x=e.x;
tracker.update(notes(57,60,65),0,1.01);
assert.equal(tracker.voices.find(v=>v.midi===57),a);
assert.equal(tracker.voices.find(v=>v.midi===60),c);
assert.equal(tracker.voices.find(v=>v.midi===65).id,eid);
assert.equal(e.phase,phase);assert.equal(e.x,x,'changing pitch never teleports a part');
tracker.update(notes(57,60,65),.1,1.11);assert(e.x>x&&e.x<65);
assert.equal(e.moves,1);assert.equal(e.previousMidi,64);
const age=e.born;tracker.update(notes(57,60,65),.1,1.21);assert.equal(e.born,age);
// Pedalled old pitches remain separate; there is no false common-tone reassignment.
tracker.update(notes(57,60,65,67),.1,1.31);assert.equal(tracker.voices.filter(v=>v.active).length,4);
tracker.update(notes(),.1,2);
tracker.update(notes(68),.1,3);assert.notEqual(tracker.voices.find(v=>v.midi===68).id,eid);
for(let i=0;i<300;i++)tracker.update(notes(),.1,3.1+i*.1);
assert.equal(tracker.voices.length,0);
assert.deepEqual(FIFTHS.map(fifthIndex),Array.from({length:12},(_,i)=>i));
assert.equal((fifthIndex(7)-fifthIndex(0)+12)%12,1);
assert.equal((fifthIndex(5)-fifthIndex(0)+12)%12,11);
const dense=createHarmonicVoices();
for(let i=0;i<200;i++)dense.update(notes(...Array.from({length:44},(_,n)=>21+n*2+i%2)),.1,i*.1);
assert(dense.voices.length<=88);
assert.equal(dense.voices.filter(v=>v.active).length,44);
dense.update(notes(60),.1,-1);assert.equal(dense.voices.length,1,'seek resets stale identities');
const soft=createHarmonicVoices(),hard=createHarmonicVoices();
const played=(velocity,style=0,end=null)=>new Map([[84,{midi:84,velocity,style,end}]]);
for(let i=0;i<120;i++){soft.update(played(38),1/60,i/60);hard.update(played(119),1/60,i/60);}
assert(hard.voices[0].height>soft.voices[0].height*2.6,'velocity changes spatial reach');
const id=hard.voices[0].id,born=hard.voices[0].born,phaseBefore=hard.voices[0].phase,heightBefore=hard.voices[0].height;
hard.update(played(110),0,2.01);
assert.equal(hard.voices[0].id,id);assert.equal(hard.voices[0].born,born);
assert.equal(hard.voices[0].phase,phaseBefore);assert.equal(hard.voices[0].height,heightBefore);
const dry=createHarmonicVoices(),wet=createHarmonicVoices();
for(let i=0;i<12;i++){dry.update(played(95),1/60,i/60);wet.update(played(95),1/60,i/60);}
for(let i=12;i<42;i++){dry.update(played(95,1,.2),1/60,i/60);wet.update(played(95,2),1/60,i/60);}
assert(dry.voices[0].level<wet.voices[0].level*.5,'dry staccato decays while pedalled notes remain');
assert(dry.voices[0].height<wet.voices[0].height,'dry staccato settles while pedalled notes float');
for(const aspect of [9/16,16/9])for(const count of [1,6,12,30,88]){
  const placed=packVoiceLabels(Array.from({length:count},()=>({x:0,y:.42})),aspect);
  assert.equal(placed.filter(Boolean).length,count);
  for(let i=0;i<placed.length;i++){const a=placed[i];assert(a.x>=-.88&&a.x<=.88&&a.y>=-.46&&a.y<=.48);
    for(let j=i+1;j<placed.length;j++){const b=placed[j];assert(Math.abs(a.x-b.x)>=a.width*.98||Math.abs(a.y-b.y)>=a.height*.98,'dense labels remain separate');}}
}
console.log('PASS persistent common tones, neighbouring voice motion, repeats, pedal, phrase gaps, capacity, seek and fifths mapping');
