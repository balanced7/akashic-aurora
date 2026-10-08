// The Rescan hint's decision model (arsenal/web/piano/midi-hint-model.mjs): which gentle hint, if any, answers a press
// of Rescan. Zero dependencies, synthetic facts only:
//   node --test tests/piano_midi_hint.test.mjs
// Acceptance: docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md (H1, A1-A2), pre-registered before
// the model was written. Design: docs/library/design/20261007_second-press-gentle-hints_db25d1.md ("the second press is
// a question"). The incident it answers: on 2026-10-07 the KeyLab reconnected while Brave was running, Windows listed
// it, Brave did not, and Rescan re-read a stale list in silence.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  decideMidiHint, footerStatus, displayName, heardTitle, matchEgg, BANTER,
  SECOND_PRESS_WINDOW_MS, SOUND_CHECK_AFTER_MS, STILL_SILENT_AFTER_MS,
} from '../arsenal/web/piano/midi-hint-model.mjs';

const T0 = 10_000_000;
const KEYLAB = 'KeyLab 88 mk3 MIDI';
const WIN_KEYLAB = { ok: true, inputs: [KEYLAB, 'KeyLab 88 mk3 DAW'], service: { state: 'running' } };
const WIN_NONE = { ok: true, inputs: [], service: { state: 'running' } };
const facts = (over = {}) => ({
  now: T0, trigger: 'press', presses: [T0], permission: 'granted', access: true,
  inputs: [], bound: [], remembered: null, eventsAtPress: 0, events: 0, rec: 'idle',
  windows: null, browser: { name: 'Brave', restartUrl: 'brave://restart' }, shown: {}, open: null,
  ...over,
});
const keylabIn = [{ name: KEYLAB, state: 'connected' }];

test('calibration: the night\'s own incident produces a hint (fails if decide always returns null)', () => {
  const v = decideMidiHint(facts({ windows: WIN_KEYLAB }));
  assert.ok(v, 'a stale browser list with Windows seeing the KeyLab must produce a verdict');
  assert.equal(v.cause, 'stale-browser-list');
});

test('a healthy bound keyboard gets no hint on a press', () => {
  assert.equal(decideMidiHint(facts({ inputs: keylabIn, bound: [KEYLAB] })), null);
});

test('the stale-list hint names the keyboard, the browser and the restart door', () => {
  const v = decideMidiHint(facts({ windows: WIN_KEYLAB }));
  assert.equal(v.level, 1);
  assert.equal(v.tone, 'hint');
  assert.match(v.title, /KeyLab 88 mk3/);
  assert.doesNotMatch(v.title, /mk3 MIDI/, 'the trailing " MIDI" port suffix is dropped for display');
  assert.match(v.title, /Brave/);
  assert.match(v.body, /Windows sees it/);
  assert.equal(v.action.copy, 'brave://restart');
});

test('Windows seeing no keyboard points at power and cable', () => {
  const v = decideMidiHint(facts({ windows: WIN_NONE }));
  assert.equal(v.cause, 'windows-sees-none');
  assert.match(v.body, /USB cable/);
});

test('a stopped MIDI service is named when Windows lists nothing', () => {
  const v = decideMidiHint(facts({ windows: { ok: true, inputs: [], service: { state: 'stopped' } } }));
  assert.equal(v.cause, 'service-stopped');
});

test('without the endpoint the hint does not claim what Windows sees', () => {
  for (const windows of [null, { ok: false, reason: 'unavailable' }]) {
    const v = decideMidiHint(facts({ windows }));
    assert.equal(v.cause, 'browser-sees-none');
    assert.doesNotMatch(`${v.title} ${v.body}`, /Windows sees/);
  }
});

test('a DAW control port alone is not a keyboard, on either side', () => {
  const winDawOnly = { ok: true, inputs: ['KeyLab 88 mk3 DAW'], service: { state: 'running' } };
  assert.equal(decideMidiHint(facts({ windows: winDawOnly })).cause, 'windows-sees-none');
  const v = decideMidiHint(facts({ inputs: [{ name: 'KeyLab 88 mk3 DAW', state: 'connected' }], windows: WIN_KEYLAB }));
  assert.equal(v.cause, 'stale-browser-list');
});

test('denied permission is answered on the first press', () => {
  const v = decideMidiHint(facts({ permission: 'denied', access: false }));
  assert.equal(v.cause, 'permission-denied');
  assert.equal(v.level, 1);
});

test('a visible but unselected keyboard waits for the second press', () => {
  assert.equal(decideMidiHint(facts({ inputs: keylabIn })), null);
  const v = decideMidiHint(facts({ inputs: keylabIn, presses: [T0 - 10_000, T0] }));
  assert.equal(v.cause, 'not-selected');
  assert.match(v.body, /Studio/);
});

test('a press outside the second-press window starts over', () => {
  const v = decideMidiHint(facts({ inputs: keylabIn, presses: [T0 - SECOND_PRESS_WINDOW_MS - 1, T0] }));
  assert.equal(v, null);
});

test('the third press adds the signal chain, dimming the step where the signal stops', () => {
  const v = decideMidiHint(facts({ windows: WIN_KEYLAB, presses: [T0 - 20_000, T0 - 10_000, T0] }));
  assert.equal(v.level, 2);
  assert.deepEqual(v.chain.map((n) => n.id), ['windows', 'browser', 'page']);
  assert.equal(v.chain.find((n) => n.status !== 'ok').id, 'browser');
  assert.equal(v.chain[1].status, 'stale');
});

test('a second press after a shown hint also escalates to the chain', () => {
  const v = decideMidiHint(facts({ windows: WIN_KEYLAB, presses: [T0 - 5_000, T0], shown: { 'stale-browser-list': 1 } }));
  assert.equal(v.level, 2);
});

test('a problem hint never pops up on its own', () => {
  const v = decideMidiHint(facts({
    trigger: 'tick', windows: WIN_KEYLAB, presses: [T0 - 30_000], shown: { 'stale-browser-list': 1 }, open: null,
  }));
  assert.equal(v, null);
});

test('bound but silent after a Rescan gets a sound check, then "Heard you"', () => {
  const silent = facts({
    trigger: 'tick', inputs: keylabIn, bound: [KEYLAB], presses: [T0 - SOUND_CHECK_AFTER_MS - 1], eventsAtPress: 5, events: 5,
  });
  const v = decideMidiHint(silent);
  assert.equal(v.cause, 'sound-check');
  assert.equal(v.tone, 'check');
  assert.match(v.body, /Play any key/);
  const heard = decideMidiHint({ ...silent, events: 6, open: 'sound-check' });
  assert.equal(heard.tone, 'success');
  assert.match(heard.title, /Heard you/);
});

test('playing right after the press needs no sound check', () => {
  const v = decideMidiHint(facts({
    trigger: 'tick', inputs: keylabIn, bound: [KEYLAB], presses: [T0 - SOUND_CHECK_AFTER_MS - 1], eventsAtPress: 5, events: 9,
  }));
  assert.equal(v, null);
});

test('a long silence escalates the sound check once', () => {
  const v = decideMidiHint(facts({
    trigger: 'tick', inputs: keylabIn, bound: [KEYLAB], presses: [T0 - STILL_SILENT_AFTER_MS - 1], eventsAtPress: 5, events: 5,
    open: 'sound-check', shown: { 'sound-check': 1 },
  }));
  assert.equal(v.level, 2);
  assert.match(v.title, /Still nothing/);
});

test('finding the keyboard closes a problem hint with a moment of success', () => {
  const v = decideMidiHint(facts({ trigger: 'change', inputs: keylabIn, bound: [KEYLAB], open: 'stale-browser-list' }));
  assert.equal(v.tone, 'success');
  assert.match(v.title, /There it is/);
  assert.match(v.body, /KeyLab 88 mk3/);
});

test('recording defers every hint and shows no success', () => {
  const v = decideMidiHint(facts({ rec: 'recording', windows: WIN_KEYLAB }));
  assert.equal(v.defer, true);
  assert.equal(v.title, undefined, 'a deferred verdict carries nothing to render');
  assert.equal(decideMidiHint(facts({ rec: 'recording', trigger: 'change', inputs: keylabIn, bound: [KEYLAB], open: 'stale-browser-list' })), null);
});

test('a hint deferred by REC is re-offered when recording ends, however long the take ran', () => {
  assert.equal(decideMidiHint(facts({ rec: 'recording', windows: WIN_KEYLAB })).defer, true);
  const after = decideMidiHint(facts({ trigger: 'resume', windows: WIN_KEYLAB, presses: [T0 - 10 * SECOND_PRESS_WINDOW_MS] }));
  assert.equal(after.cause, 'stale-browser-list');
  assert.equal(decideMidiHint(facts({ trigger: 'tick', windows: WIN_KEYLAB, presses: [T0 - 10 * SECOND_PRESS_WINDOW_MS] })), null,
    'without the resume trigger the same facts stay quiet');
});

test('the sound check names what it heard, with the right article (Daniel: "thats a c.. thats an e....")', () => {
  assert.equal(heardTitle(null), 'Heard you');
  assert.equal(heardTitle({ notes: [] }), 'Heard you');
  assert.equal(heardTitle({ notes: ['C'] }), "That's a C");
  assert.equal(heardTitle({ notes: ['E'] }), "That's an E");
  assert.equal(heardTitle({ notes: ['F♯'] }), "That's an F♯");
  assert.equal(heardTitle({ notes: ['A♭'] }), "That's an A♭");
  assert.equal(heardTitle({ notes: ['B♭'] }), "That's a B♭");
  assert.equal(heardTitle({ notes: ['C', 'E'] }), "That's a C and an E");
  assert.equal(heardTitle({ notes: ['C', 'E', 'G', 'B'], chord: 'Cmaj7' }), 'Cmaj7, loud and clear');
  assert.equal(heardTitle({ notes: ['C', 'D', 'E'], chord: null }), "That's a chord, loud and clear");
});

test('"Heard you" names the first note, then narrates new ones while it lingers', () => {
  const base = facts({ trigger: 'tick', inputs: keylabIn, bound: [KEYLAB], presses: [T0 - 10_000], eventsAtPress: 5 });
  const first = decideMidiHint({ ...base, events: 6, open: 'sound-check', heard: { notes: ['C'] } });
  assert.equal(first.cause, 'heard');
  assert.equal(first.title, "That's a C");
  const next = decideMidiHint({ ...base, events: 7, open: 'heard', heardShown: "That's a C", heard: { notes: ['E'] } });
  assert.equal(next.title, "That's an E");
  assert.equal(decideMidiHint({ ...base, events: 7, open: 'heard', heardShown: "That's an E", heard: { notes: ['E'] } }), null,
    'the same sound does not re-render');
  assert.equal(decideMidiHint({ ...base, events: 7, open: 'heard', heardShown: "That's an E", heard: null }), null,
    'silence leaves the card to its own fade');
  assert.equal(decideMidiHint({ ...base, rec: 'recording', events: 8, open: 'heard', heardShown: "That's an E", heard: { notes: ['G'] } }), null,
    'no narration during a take');
});

test('pressed again after a success, Rescan climbs the deadpan ladder and then goes quiet', () => {
  const healthy = facts({ inputs: keylabIn, bound: [KEYLAB] });
  const yes = decideMidiHint({ ...healthy, banter: 1, lastHeard: 'C' });
  assert.equal(yes.cause, 'banter');
  assert.equal(yes.tone, 'wry');
  assert.equal(yes.title, '…yes?');
  assert.match(yes.body, /That was a C a moment ago/);
  assert.equal(decideMidiHint({ ...healthy, banter: 1, lastHeard: 'E' }).body.includes('an E'), true);
  assert.equal(decideMidiHint({ ...healthy, banter: 1 }).body, 'Still here. Still working.');
  BANTER.forEach((line, i) => assert.equal(decideMidiHint({ ...healthy, banter: i + 1 }).title, line.title));
  assert.equal(decideMidiHint({ ...healthy, banter: BANTER.length + 1 }), null, 'the joke ends; it goes quiet');
  assert.equal(decideMidiHint({ ...healthy, banter: 1, rec: 'recording' }), null, 'no banter during a take');
  assert.equal(decideMidiHint({ ...healthy, banter: 0 }), null, 'no success yet: the ordinary press stays silent');
});

test('F-A-G-D-A-D in any octave plays the Periphery egg; anything short of it does not', () => {
  assert.equal(matchEgg([53, 57, 55, 50, 57, 62]).id, 'fagdad');           // F3 A3 G3 D3 A3 D4
  assert.equal(matchEgg([41, 45, 43, 38, 45, 38]).id, 'fagdad');           // the same, an octave down
  assert.equal(matchEgg([60, 64, 53, 57, 55, 50, 57, 62]).id, 'fagdad');   // after other notes
  assert.equal(matchEgg([53, 57, 55, 50, 57]), null);                      // five strings in: not yet
  assert.equal(matchEgg([53, 57, 55, 50, 57, 61]), null);                  // a C♯ at the end: not it
  assert.equal(matchEgg([]), null);
});

test('the egg links its verified original, and the link and thumbnail name the same video', () => {
  const { source } = matchEgg([53, 57, 55, 50, 57, 62]);
  const id = new URL(source.url).searchParams.get('v');
  assert.equal(id, 'z7K8Vjm8jLU');
  assert.equal(source.thumb, `https://i.ytimg.com/vi/${id}/hqdefault.jpg`);
});

test('displayName drops the trailing MIDI port suffix only', () => {
  assert.equal(displayName('KeyLab 88 mk3 MIDI'), 'KeyLab 88 mk3');
  assert.equal(displayName('MIDI Fighter Twister'), 'MIDI Fighter Twister');
});

test('the footer stops calling a missing keyboard "ready"', () => {
  assert.equal(footerStatus({ boundName: KEYLAB, remembered: KEYLAB, visible: [KEYLAB] }), null);
  assert.equal(footerStatus({ boundName: null, remembered: KEYLAB, visible: [] }),
    'KeyLab 88 mk3 not found · computer keyboard ready');
  assert.equal(footerStatus({ boundName: null, remembered: KEYLAB, visible: [KEYLAB] }),
    'KeyLab 88 mk3 not selected · computer keyboard ready');
  assert.equal(footerStatus({ boundName: null, remembered: null, visible: [] }), 'Computer keyboard ready');
  assert.equal(footerStatus({ boundName: null, remembered: '__all__', visible: [] }), 'Computer keyboard ready');
});
