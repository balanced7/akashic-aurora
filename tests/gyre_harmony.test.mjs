import test from 'node:test';
import assert from 'node:assert/strict';
import {harmonyTarget,createMidiNotes,CHORD_PREVIEWS} from '../arsenal/web/piano/gyre-harmony.mjs';
test('silence returns the base form and chord previews have distinct bounded targets',()=>{
  assert.deepEqual(harmonyTarget([]).shape,[0,0,0]);
  const targets=Object.values(CHORD_PREVIEWS).map(c=>harmonyTarget(c.notes));
  assert.equal(new Set(targets.map(t=>t.shape.join(','))).size,4);
  for(const t of targets)assert.ok(t.shape.every(n=>Number.isFinite(n)&&Math.abs(n)<=1));
});
test('duplicate notes and input order do not alter geometry',()=>{
  assert.deepEqual(harmonyTarget([60,64,67]).shape,harmonyTarget([67,60,64,60]).shape);
});
test('MIDI pedal latches releases, restrikes do not duplicate and pedal-up clears only released notes',()=>{
  const s=createMidiNotes();s.message([144,60,90]);s.message([176,64,127]);s.message([128,60,0]);assert.deepEqual(s.notes(),[60]);
  s.message([144,60,80]);s.message([176,64,0]);assert.deepEqual(s.notes(),[60]);s.message([144,60,0]);assert.deepEqual(s.notes(),[]);
});
test('pedal and all-notes-off are scoped to their MIDI channel',()=>{
  const s=createMidiNotes();s.message([144,60,90]);s.message([145,64,90]);s.message([176,64,127]);s.message([128,60,0]);
  s.message([177,123,0]);assert.deepEqual(s.notes(),[60]);s.message([176,121,0]);assert.deepEqual(s.notes(),[]);
});
test('disconnect cleanup leaves no stuck notes or pedal state',()=>{
  const s=createMidiNotes();s.message([144,60,90]);s.message([176,64,127]);s.clear();assert.deepEqual(s.notes(),[]);
  s.message([144,67,90]);s.message([128,67,0]);assert.deepEqual(s.notes(),[]);
});
test('a release from before connection or an invalid packet cannot invent a latched note',()=>{
  const s=createMidiNotes();s.message([176,64,127]);s.message([128,60,0]);s.message([144,200,90]);s.message([144]);assert.deepEqual(s.notes(),[]);
});
