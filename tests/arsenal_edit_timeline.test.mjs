// The editor's timeline model (arsenal/web/edit/timeline.js): layout, snapping, trim, split, linked audio, the mixer's
// gain rule, the ruler, visible-range peaks and the local undo stack. Zero dependencies, synthetic documents only:
//   node --test tests/arsenal_edit_timeline.test.mjs
// Contract: Vandor's EDITOR v0 CONTRACT (project document arsenal.media.timeline/v0; one writer by revision). Edits
// ripple by exactly the length they change, so a gap another writer left survives; edit.render plays a gap as black
// and silence. The browser half (saving, 409s, gestures, the Export panel) is driven in headless Chrome against the
// real server by tests/test_arsenal_edit_ui_smoke.py; here only the pure rules, plus the Export panel's QC words.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as T from '../arsenal/web/edit/timeline.js';
import { qcSummary } from '../arsenal/web/edit/render.js';

const close = (a, b, eps = 1e-9) => Math.abs(a - b) <= eps;
const deepFreeze = (o) => { if (o && typeof o === 'object' && !Object.isFrozen(o)) { Object.freeze(o); Object.values(o).forEach(deepFreeze); } return o; };

// A probe sidecar as arsenal.media.probe writes it (PRIMITIVES-SPEC P2): one OBS recording, three titled tracks.
const SIDECAR = {
  id: 'aaaaaaaaaaaaaaaa', path: 'E:\\Video Output E\\2026-10-11 17-51-11.mp4', size: 2_400_000_000, duration_s: 120,
  container: 'mov,mp4,m4a,3gp,3g2,mj2', recorded_at: '2026-10-11T17:51:11', encoder: 'OBS Studio (32.2.2)', kind: 'league_replay',
  video: { codec: 'hevc', w: 1920, h: 1080, fps: 60, vfr: false, has_b_frames: 0, keyint_s: 4.17, keyframes_n: 29 },
  audio: [
    { index: 1, codec: 'opus', channels: 2, sample_rate: 48000, title: 'OBS Audio Handler', house_name: 'Mix' },
    { index: 2, codec: 'opus', channels: 1, sample_rate: 48000, title: 'Voice' },
    { index: 3, codec: 'opus', channels: 2, sample_rate: 48000, title: null, house_name: 'Game' },
  ],
  links: { practice_session: '20261011-165503-f62d348c' },
};
const MEDIA = T.normalizeMedia(SIDECAR);
const SHORT = T.normalizeMedia({ id: 'bbbbbbbbbbbbbbbb', path: 'C:/x/short.mkv', duration: '10', video: { codec_name: 'h264', width: 1280, height: 720, rate: '30000/1001' }, audio: [{ codec_name: 'aac' }] });
const KEYFRAMES = Array.from({ length: 29 }, (_, i) => +(i * 4.1666667).toFixed(4)); // OBS: one every 250 frames

function threeClips() {
  let d = T.emptyProject({ id: 'p1', name: 'Draven' });
  d = T.appendClip(d, MEDIA, { id: 'c1', src_in: 0, src_out: 10 }).doc;
  d = T.appendClip(d, SHORT, { id: 'c2', src_in: 2, src_out: 6 }).doc;
  d = T.appendClip(d, MEDIA, { id: 'c3', src_in: 30, src_out: 45 }).doc;
  return d;
}
const ats = (d) => T.videoClips(d).map((c) => [c.id, +c.at.toFixed(6)]);

test('time words: m:ss on the ruler, frames under the monitor, OBS rates parsed', () => {
  assert.equal(T.formatTime(0), '0:00');
  assert.equal(T.formatTime(65.4), '1:05');
  assert.equal(T.formatTime(59.999), '1:00', 'rounds once: never 0:60');
  assert.equal(T.formatTime(3725.25, 2), '1:02:05.25');
  assert.equal(T.formatTime(-3), '0:00');
  assert.equal(T.formatTimecode(61.5, 60), '0:01:01:30', 'four fields: never mistaken for 1 h 1 min 30 s');
  assert.equal(T.formatTimecode(3725.5, 30), '1:02:05:15');
  assert.equal(T.formatTimecode(12.999, 60), '0:00:13:00', 'rounds once: frame 60 carries into the second');
  assert.ok(close(T.parseFps('30000/1001'), 29.97002997, 1e-6));
  assert.equal(T.parseFps('60/1'), 60);
  assert.ok(Number.isNaN(T.parseFps('0/0')));
  assert.equal(T.quantize(1.0083, 60), 1);
});

test('normalizeMedia reads the probe sidecar and an older probe alike; generic track titles fall back to the house map', () => {
  assert.equal(MEDIA.name, '2026-10-11 17-51-11.mp4');
  assert.equal(MEDIA.duration, 120);
  assert.deepEqual([MEDIA.video.codec, MEDIA.video.w, MEDIA.video.h, MEDIA.video.fps, MEDIA.video.keyint_s], ['hevc', 1920, 1080, 60, 4.17]);
  assert.deepEqual(MEDIA.audio.map((a) => a.label), ['Mix', 'Voice', 'Game'], '"OBS Audio Handler" is a muxer default, not a name');
  assert.equal(MEDIA.links.practice_session, '20261011-165503-f62d348c');
  assert.equal(SHORT.name, 'short.mkv');
  assert.deepEqual([SHORT.duration, SHORT.video.w, SHORT.video.h], [10, 1280, 720]);
  assert.ok(close(SHORT.video.fps, 29.97, 1e-3));
  assert.deepEqual(SHORT.audio.map((a) => a.label), ['Mix']);
  assert.equal(T.trackLabel({}, 7), 'Track 8');
  assert.equal(T.normalizeMedia(null), null);
  // the server's media record (arsenal/media/editapi.py media_view): its own label, and start_s from the demux
  const served = T.normalizeMedia({ id: 'cccccccccccccccc', name: 'x.mp4', duration_s: 5, video: { codec: 'h264', w: 2, h: 2, fps: 30 },
    audio: [{ track: 0, title: null, label: 'Track 1' }, { track: 1, label: 'Commentary', start_s: 0.021 }] });
  assert.deepEqual(served.audio.map((a) => a.label), ['Mix', 'Commentary'], '"Track n" is no name; a real label is kept');
  assert.deepEqual(served.audio.map((a) => a.start_s), [0, 0.021]);
});

test('append: appends build the video lane end to end, every source track becomes a linked entry on lane A(n+1)', () => {
  const d = threeClips();
  assert.deepEqual(ats(d), [['c1', 0], ['c2', 10], ['c3', 14]]);
  assert.equal(T.totalDuration(d), 29);
  assert.deepEqual(d.lanes.audio.map((l) => [l.id, l.label]), [['A1', 'Mix'], ['A2', 'Voice'], ['A3', 'Game']]);
  assert.deepEqual(d.clips.find((c) => c.id === 'c1').audio.map((a) => [a.src_track, a.lane]), [[0, 'A1'], [1, 'A2'], [2, 'A3']]);
  assert.deepEqual(d.clips.find((c) => c.id === 'c2').audio.map((a) => a.lane), ['A1'], 'a one-track source fills A1 only');
  assert.deepEqual(T.validate(d), []);
  const whole = T.appendClip(T.emptyProject(), MEDIA, { id: 'w' }).doc.clips[0];
  assert.deepEqual([whole.src_in, whole.src_out], [0, 120], 'a plain append takes the whole file');
  assert.throws(() => T.appendClip(T.emptyProject(), { id: 'x', duration_s: 0 }), /duration/);
});

test('insert by drop position: before the first clip whose middle lies after the drop', () => {
  const d = threeClips();
  assert.equal(T.insertionIndex(d, 0), 0);
  assert.equal(T.insertionIndex(d, 4.9), 0);
  assert.equal(T.insertionIndex(d, 5.1), 1);
  assert.equal(T.insertionIndex(d, 100), 3);
  const r = T.insertClip(d, SHORT, 1, { id: 'n', src_in: 0, src_out: 3 });
  assert.deepEqual(ats(r.doc), [['c1', 0], ['n', 10], ['c2', 13], ['c3', 17]]);
  const first = T.insertClip(d, SHORT, 0, { id: 'f', src_in: 0, src_out: 1 }).doc;
  assert.deepEqual(ats(first), [['f', 0], ['c1', 1], ['c2', 11], ['c3', 15]]);
});

test('trim ripples: the dragged edge moves on the source frame grid, later clips close up, audio follows', () => {
  const d = deepFreeze(threeClips());
  const a = T.trimClip(d, 'c1', 'in', 2.004, { mediaDuration: 120, fps: 60 });
  const c1 = a.clips.find((c) => c.id === 'c1');
  assert.deepEqual([c1.src_in, c1.src_out], [2, 10], '2.004 s lands on frame 120');
  assert.deepEqual(ats(a), [['c1', 0], ['c2', 8], ['c3', 12]]);
  assert.equal(c1.audio.length, 3, 'the linked entries carry no times of their own: they trim with the clip');
  const b = T.trimClip(d, 'c2', 'out', 9.5, { mediaDuration: 10, fps: 30 });
  assert.equal(b.clips.find((c) => c.id === 'c2').src_out, 9.5);
  assert.deepEqual(ats(b), [['c1', 0], ['c2', 10], ['c3', 17.5]]);
  const past = T.trimClip(d, 'c2', 'out', 99, { mediaDuration: 10 });
  assert.equal(past.clips.find((c) => c.id === 'c2').src_out, 10, 'never past the end of the file');
  const neg = T.trimClip(d, 'c1', 'in', -5, { mediaDuration: 120 });
  assert.equal(neg, d, 'already at 0: nothing changes, the same object comes back');
  const squeeze = T.trimClip(d, 'c1', 'in', 50, { mediaDuration: 120, fps: 60 });
  const s1 = squeeze.clips.find((c) => c.id === 'c1');
  assert.ok(close(s1.src_out - s1.src_in, 1 / 60), 'never shorter than one frame');
  assert.equal(T.trimClip(d, 'nope', 'in', 1), d);
  assert.throws(() => T.trimClip(d, 'c1', 'middle', 1), /edge/);
  assert.deepEqual(T.validate(a), []);
});

test('split at the playhead: two clips meet on a source frame, the right half gets the new id and its own linked audio', () => {
  const d = deepFreeze(threeClips());
  const s = T.splitClip(d, 20.005, { newId: 'c3b' });
  assert.deepEqual(ats(s), [['c1', 0], ['c2', 10], ['c3', 14], ['c3b', 20]], '20.005 s rounds to the frame at 20 s on the timeline');
  const left = s.clips.find((c) => c.id === 'c3'), right = s.clips.find((c) => c.id === 'c3b');
  assert.deepEqual([left.src_in, left.src_out, right.src_in, right.src_out], [30, 36, 36, 45]);
  assert.deepEqual(right.audio, left.audio);
  assert.notEqual(right.audio, left.audio, 'copied, not shared');
  assert.equal(T.totalDuration(s), T.totalDuration(d), 'a split changes nothing you hear or see');
  assert.equal(T.splitClip(d, 14.005), d, 'within a frame of an edge: no sliver clip');
  assert.equal(T.splitClip(d, 99), d, 'past the end: nothing');
});

test('delete and move ripple; the document order follows the timeline order', () => {
  const d = deepFreeze(threeClips());
  const del = T.deleteClip(d, 'c2');
  assert.deepEqual(ats(del), [['c1', 0], ['c3', 10]]);
  assert.equal(T.deleteClip(d, 'zz'), d);
  const mv = T.moveClip(d, 'c3', 0);
  assert.deepEqual(ats(mv), [['c3', 0], ['c1', 15], ['c2', 25]]);
  assert.deepEqual(mv.clips.map((c) => c.id), ['c3', 'c1', 'c2']);
  assert.equal(T.moveClip(d, 'c1', 0), d, 'already there');
  const end = T.moveClip(d, 'c1', 9);
  assert.deepEqual(ats(end), [['c2', 0], ['c3', 4], ['c1', 19]]);
});

test('a gap someone else left (the CLI can place a clip anywhere; the renderer plays it as black) survives edits elsewhere', () => {
  const base = threeClips(); // c1 0..10, c2 10..14, c3 14..29
  const withGap = deepFreeze({ ...base, clips: base.clips.map((c) => (c.id === 'c1' ? c : { ...c, at: c.at + 3 })) });
  assert.deepEqual(T.gaps(withGap), [[10, 13]]);
  const trimmed = T.trimClip(withGap, 'c1', 'out', 8, { mediaDuration: 120 });
  assert.deepEqual(ats(trimmed), [['c1', 0], ['c2', 11], ['c3', 15]], 'the later clips move by 2 s, the gap keeps its 3 s');
  assert.deepEqual(T.gaps(trimmed), [[8, 11]]);
  assert.deepEqual(T.gaps(T.splitClip(withGap, 20, { newId: 's' })), [[10, 13]]);
  assert.deepEqual(T.gaps(T.deleteClip(withGap, 'c3')), [[10, 13]]);
  const ins = T.insertClip(withGap, SHORT, 1, { id: 'n', src_in: 0, src_out: 5 }).doc;
  assert.deepEqual(ats(ins), [['c1', 0], ['n', 13], ['c2', 18], ['c3', 22]], 'an insert takes the next clip\'s place, after the gap');
  assert.deepEqual(T.gaps(ins), [[10, 13]]);
  assert.deepEqual(T.validate(ins), []);
  assert.deepEqual(ats(T.pack(withGap)), [['c1', 0], ['c2', 10], ['c3', 14]], 'pack() closes gaps, and only when asked');
  assert.deepEqual(T.gaps(threeClips()), [], 'a timeline built here has none');
  assert.equal(T.clipAtTime(withGap, 11.5), null, 'nothing plays in a gap');
});

test('clipAtTime maps timeline time to a source time; the very end belongs to the last clip', () => {
  const d = threeClips();
  const h = T.clipAtTime(d, 12.5);
  assert.equal(h.clip.id, 'c2');
  assert.equal(h.srcT, 4.5);
  assert.equal(T.clipAtTime(d, 10).clip.id, 'c2', 'a boundary belongs to the clip that starts there');
  const e = T.clipAtTime(d, 29);
  assert.deepEqual([e.clip.id, e.srcT], ['c3', 45]);
  assert.equal(T.clipAtTime(d, 29.5), null);
  assert.equal(T.clipAtTime(T.emptyProject(), 0), null);
});

test('a cut where the previous clip ends a nanosecond past the next one\'s at still belongs to the next clip', () => {
  // the 2026-10-12 browser proof: split at 11.0667 s, the middle deleted, the next clip rippled to at 11.066666666
  // (rounded to 1e-9) while the first clip's src_out - src_in is 11.066666666666667: playback stalled on the cut
  let d = T.emptyProject({ id: 'p2', name: 'cut' });
  d = T.appendClip(d, MEDIA, { id: 'a', src_in: 2.8666666666666667, src_out: 13.933333333333334 }).doc;
  d = T.appendClip(d, SHORT, { id: 'b', src_in: 0, src_out: 5 }).doc;
  const b = d.clips.find((c) => c.id === 'b');
  b.at = 11.066666666;
  assert.ok(T.clipEnd(d.clips.find((c) => c.id === 'a')) > b.at, 'the fixture overshoots');
  assert.deepEqual([T.clipAtTime(d, b.at).clip.id, T.clipAtTime(d, b.at).srcT], ['b', 0]);
  assert.equal(T.clipAtTime(d, 11.0).clip.id, 'a');
});

test('snapping: shots and keyframes map through the clip placement, the playhead wins a tie, nothing beyond the threshold', () => {
  const d = threeClips();
  const c3 = d.clips.find((c) => c.id === 'c3'); // at 14, src 30..45
  const targets = T.trimSnapTargets(c3, { shots: [{ t: 33.0, score: 0.9, source: 'content' }, 31.5], keyframes: KEYFRAMES, playhead: 18.98 });
  const shot = targets.find((g) => g.kind === 'shot' && g.src === 33);
  assert.equal(shot.t, 17, 'source 33 s sits at timeline 14 + (33 - 30)');
  assert.deepEqual(T.snap(17.05, targets, 0.1), { t: 17, kind: 'shot' });
  assert.deepEqual(T.snap(17.5, targets, 0.1), { t: 17.5, kind: null });
  const kf = KEYFRAMES.find((k) => k > 30);
  assert.deepEqual(T.snap(14 + (kf - 30) + 0.02, targets, 0.05), { t: 14 + (kf - 30), kind: 'keyframe' });
  const tie = T.snap(19, [{ t: 19.01, kind: 'keyframe' }, { t: 18.99, kind: 'playhead' }], 0.05);
  assert.equal(tie.kind, 'playhead');
});

test('trim cost: lossless on a keyframe, else the head a smart cut re-encodes, in the words the hint shows', () => {
  assert.deepEqual(T.cutCost(KEYFRAMES, KEYFRAMES[3], 60), { lossless: true, head_s: 0, keyframe: KEYFRAMES[3] });
  const c = T.cutCost(KEYFRAMES, KEYFRAMES[3] + 2.7667, 60);
  assert.equal(c.lossless, false);
  assert.ok(close(c.head_s, 1.4, 1e-3));
  assert.equal(T.costHint(c), 're-encodes the first 1.4 s');
  // cut.plan's rule: the cut starts on the first frame at or after start - 1 ms, lossless when that frame is a keyframe
  assert.equal(T.costHint(T.cutCost(KEYFRAMES, KEYFRAMES[3] - 0.004, 60)), 'lossless', 'just before a keyframe starts on it');
  assert.equal(T.costHint(T.cutCost(KEYFRAMES, KEYFRAMES[3] + 0.0009, 60)), 'lossless', 'within the 1 ms slack');
  assert.equal(T.cutCost(KEYFRAMES, KEYFRAMES[3] + 0.004, 60).lossless, false, 'after it: the cut starts one frame later');
  assert.equal(T.cutCost(KEYFRAMES, KEYFRAMES[3] + 0.5 / 60, 60).lossless, false, 'half a frame after: not on it');
  assert.equal(T.cutCost([], 3), null);
  // cut.plan's own answer (PRIMITIVES-SPEC P5) says the same thing in its own keys
  assert.equal(T.costHint({ mode_suggested: 'copy', start_keyframe: 12.5, head_reencode_s: 0 }), 'lossless');
  assert.equal(T.costHint({ mode_suggested: 'smart', start_keyframe: 12.5, head_reencode_s: 1.43 }), 're-encodes the first 1.4 s');
  assert.equal(T.costHint({ mode_suggested: 'exact' }), 're-encodes the whole clip');
  assert.equal(T.costHint(null), '');
});

test('mixer rule: lane gain + clip gain in dB; mute, solo and a muted entry silence it (the renderer applies the same rule)', () => {
  let d = threeClips();
  const c1 = d.clips.find((c) => c.id === 'c1');
  const [mix, voice, game] = c1.audio;
  assert.equal(T.effectiveGain(d, mix), 1);
  d = T.setLane(d, 'A1', { gain_db: -6 });
  assert.ok(close(T.effectiveGain(d, d.clips[0].audio[0]), 0.501187, 1e-6));
  d = T.setClipAudio(d, 'c1', 0, { gain_db: 6 });
  assert.ok(close(T.effectiveGain(d, d.clips[0].audio[0]), 1, 1e-12), '-6 + 6 = 0 dB');
  d = T.setLane(d, 'A2', { solo: true });
  assert.equal(T.effectiveGain(d, d.clips[0].audio[0]), 0, 'another lane is soloed');
  assert.equal(T.effectiveGain(d, d.clips[0].audio[1]), 1);
  d = T.setLane(d, 'A2', { mute: true });
  assert.equal(T.effectiveGain(d, d.clips[0].audio[1]), 0, 'mute beats solo');
  d = T.setLane(T.setLane(d, 'A2', { solo: false, mute: false }), 'A3', { gain_db: 40 });
  assert.equal(d.lanes.audio[2].gain_db, 12, 'gain clamps to +12 dB');
  d = T.setClipAudio(d, 'c1', 2, { mute: true });
  assert.equal(T.effectiveGain(d, d.clips[0].audio[2]), 0);
  assert.equal(T.setLane(d, 'A1', { gain_db: d.lanes.audio[0].gain_db }), d, 'same value: no edit');
  assert.equal(T.setLane(d, 'A9', { mute: true }), d);
  assert.ok(voice && game);
});

test('layout rows: ruler, V1, then one row per audio lane; rowAt finds them', () => {
  const L = T.layoutRows(threeClips(), { ruler: 24, video: 56, audio: 44 });
  assert.deepEqual(L.rows.map((r) => [r.id, r.y, r.h]), [['ruler', 0, 24], ['V1', 24, 56], ['A1', 80, 44], ['A2', 124, 44], ['A3', 168, 44]]);
  assert.equal(L.height, 212);
  assert.equal(L.rows[2].label, 'A1 Mix');
  assert.equal(T.rowAt(L, 100).id, 'A1');
  assert.equal(T.rowAt(L, 500), null);
});

test('ruler ticks keep labels apart at every zoom, and zoomAround keeps the time under the pointer', () => {
  for (const pps of [0.3, 2, 12, 60, 300, 2400]) {
    const r = T.rulerTicks(0, 1600 / pps, pps, 84);
    assert.ok(r.step * pps >= 84, `labels ${r.step * pps} px apart at ${pps} px/s`);
    assert.ok(r.major.length >= 1 && r.major.length <= 21, `${r.major.length} labels at ${pps} px/s`);
  }
  assert.deepEqual(T.rulerTicks(0, 30, 10).major.slice(0, 3).map((m) => m.label), ['0:00', '0:10', '0:20']);
  assert.equal(T.rulerTicks(0, 1, 2400).major[1].label, '0:00.1');
  const v = { pxPerSec: 10, scrollLeft: 500 };
  const z = T.zoomAround(v, 2, 300);
  assert.ok(close((v.scrollLeft + 300) / v.pxPerSec, (z.scrollLeft + 300) / z.pxPerSec), 'the anchor time stays put');
  assert.equal(T.zoomAround({ pxPerSec: 10, scrollLeft: 0 }, 0.5, 0).scrollLeft, 0);
  const lim = T.zoomLimits(2028, 1500);
  assert.equal(lim.max, T.ZOOM_MAX_PPS);
  assert.ok(lim.max * 2028 <= T.MAX_CONTENT_PX);
  assert.ok(T.zoomLimits(4 * 3600 * 10, 1500).max * 4 * 3600 * 10 <= T.MAX_CONTENT_PX + 1, 'a 40-hour timeline still fits the layout limit');
  assert.equal(T.zoomAround(v, 1e9, 0, lim).pxPerSec, lim.max);
});

test('peaks: per-column min/max over the visible source range equals a brute-force scan; columns past the data are empty', () => {
  const sr = 48000, spp = 512, bins = 5000; // ~53 s
  const data = new Float32Array(bins * 2);
  let seed = 7;
  const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648);
  for (let b = 0; b < bins; b++) { const a = rnd(), c = rnd(); data[2 * b] = -Math.max(a, c); data[2 * b + 1] = Math.min(a, c); }
  const P = T.toPeaks({ sample_rate: sr, spp, data: Array.from(data) });
  assert.equal(P.bins, bins);
  const s0 = 3.21, s1 = 41.7, cols = 733;
  const got = T.peaksColumns(P, s0, s1, cols);
  const secPerBin = spp / sr, span = (s1 - s0) / cols;
  for (const c of [0, 1, 100, 366, 732]) {
    const a = s0 + c * span;
    const b0 = Math.floor(a / secPerBin), b1 = Math.max(b0 + 1, Math.ceil((a + span) / secPerBin));
    let lo = Infinity, hi = -Infinity;
    for (let b = b0; b < Math.min(b1, bins); b++) { lo = Math.min(lo, data[2 * b]); hi = Math.max(hi, data[2 * b + 1]); }
    assert.equal(got[2 * c], lo, `column ${c} min`);
    assert.equal(got[2 * c + 1], hi, `column ${c} max`);
  }
  const past = T.peaksColumns(P, 50, 60, 10);
  assert.ok(!Number.isNaN(past[0]) && Number.isNaN(past[18]), 'data ends at 53.3 s');
  const zoomedIn = T.peaksColumns(P, 1, 1.01, 100);
  assert.ok(zoomedIn.every((x) => !Number.isNaN(x)), 'more columns than bins: each column shows its own bin');
  assert.equal(T.toPeaks({ spp: 0 }), null);
  // a track that starts 0.5 s into the source: its first bin sits at source 0.5 s, nothing before it
  const late = T.toPeaks({ sample_rate: sr, spp, data: Array.from(data), start_s: 0.5 });
  const lc = T.peaksColumns(late, 0, 1, 2);
  assert.ok(Number.isNaN(lc[0]), 'source 0..0.5 s is before the track');
  assert.equal(lc[2], Math.min(...Array.from({ length: Math.ceil(0.5 / secPerBin) }, (_, b) => data[2 * b])));
});

test('waveform heights are on a dB scale: -35 dBFS game audio fills a third of the lane, the floor is silence, gain moves it', () => {
  const at = (db) => Math.pow(10, db / 20);
  assert.equal(T.waveHeight(1), 1);
  assert.ok(close(T.waveHeight(at(-35)), 19 / 54, 1e-9), 'linear would draw it at 1.8 % of the lane');
  assert.ok(close(T.waveHeight(-at(-27)), -0.5, 1e-9), 'the sign is kept');
  assert.equal(T.waveHeight(at(-60)), 0);
  assert.equal(T.waveHeight(0), 0);
  assert.equal(T.waveHeight(at(-6), 4), 1, 'never past the lane edge');
  assert.ok(close(T.waveHeight(at(-35), T.dbToGain(-6)), 13 / 54, 1e-9), 'a -6 dB fader lowers it by 6/54');
});

test('undo stack: a no-op records nothing, undo/redo walk whole documents, a new edit drops the redo branch, the cap holds', () => {
  const d0 = threeClips();
  let h = T.createHistory(d0, 3);
  h = T.commit(h, d0);
  assert.equal(h.past.length, 0, 'the same object is not an edit');
  const d1 = T.splitClip(d0, 5, { newId: 'x' });
  const d2 = T.deleteClip(d1, 'c2');
  h = T.commit(T.commit(h, d1), d2);
  assert.equal(h.present, d2);
  h = T.undo(h);
  assert.equal(h.present, d1);
  assert.ok(T.canRedo(h));
  h = T.redo(h);
  assert.equal(h.present, d2);
  h = T.commit(T.undo(h), T.moveClip(d1, 'c3', 0));
  assert.ok(!T.canRedo(h), 'a new edit after an undo drops the old future');
  for (let i = 0; i < 10; i++) h = T.commit(h, T.rename(h.present, `n${i}`));
  assert.equal(h.past.length, 3, 'the cap holds');
  const saved = T.replacePresent(h, { ...h.present, rev: 9 });
  assert.equal(saved.past.length, 3);
  assert.equal(saved.present.rev, 9);
  assert.equal(T.undo(T.createHistory(d0)).present, d0);
});

test('validate names structural problems (the server checks these and more, such as a clip past its media)', () => {
  const d = threeClips();
  const bad = JSON.parse(JSON.stringify(d));
  bad.clips[1].at = 5; // overlaps c1
  bad.clips[2].audio[0].lane = 'A9';
  bad.clips.push({ ...bad.clips[0] }); // repeated id
  const p = T.validate(bad);
  assert.ok(p.some((x) => /overlap/.test(x)));
  assert.ok(p.some((x) => /A9/.test(x)));
  assert.ok(p.some((x) => /repeated/.test(x)));
  assert.ok(T.validate({ api: 'x', clips: [] }).some((x) => /api/.test(x)));
});

test('purity: no edit mutates its input, and a JSON round trip of the document is lossless', () => {
  const d = deepFreeze(threeClips());
  const before = JSON.stringify(d);
  T.trimClip(d, 'c1', 'out', 5); T.splitClip(d, 3, { newId: 'q' }); T.deleteClip(d, 'c1'); T.moveClip(d, 'c1', 2);
  T.setLane(d, 'A1', { mute: true }); T.setClipAudio(d, 'c1', 0, { gain_db: -3 }); T.insertClip(d, SHORT, 1, { id: 'i' });
  T.rename(d, 'other'); T.pack(d); T.ensureAudioLanes(d, SHORT);
  assert.equal(JSON.stringify(d), before);
  assert.deepEqual(JSON.parse(JSON.stringify(d)), d);
});

test('scale: 200 clips append, split, trim and pack inside one frame budget each', () => {
  let d = T.emptyProject();
  const t0 = performance.now();
  for (let i = 0; i < 200; i++) d = T.appendClip(d, MEDIA, { id: `k${i}`, src_in: i % 50, src_out: (i % 50) + 3 }).doc;
  const tAppend = (performance.now() - t0) / 200;
  assert.equal(T.totalDuration(d), 600);
  const t1 = performance.now();
  const s = T.splitClip(d, 301.5, { newId: 'split' });
  const tr = T.trimClip(s, 'k10', 'in', 11, { mediaDuration: 120 });
  const packed = T.pack(tr);
  const tOps = performance.now() - t1;
  assert.equal(s.clips.length, 201);
  assert.equal(T.totalDuration(tr), 599);
  assert.equal(packed, tr, 'edits made here leave nothing to pack');
  assert.deepEqual(T.validate(tr), []);
  assert.ok(tAppend < 8 && tOps < 16, `append ${tAppend.toFixed(2)} ms/clip, split+trim+pack ${tOps.toFixed(2)} ms`);
});

// multitrack_test.mp4 and excerpt_600_720.mp4 (media-oracles): the video stream starts at 0.025 s, so frame k sits at
// 0.025 + k / 60 and the keyframes (probe.keyframes) at 0.025, 4.191667, 8.358333, 12.525.
const OFFSET = T.normalizeMedia({ id: 'dddddddddddddddd', name: 'multitrack_test.mp4', duration_s: 16,
  video: { codec: 'h264', w: 1280, h: 720, fps: 60, start_s: 0.025 }, audio: [{ title: 'Mix' }, { title: 'Mic' }] });
const OFFSET_KF = [0.025, 4.191667, 8.358333, 12.525];

test('frame grid: a stream that starts at 0.025 s puts trims and splits on its own frames, where cut.plan cuts', () => {
  const grid = T.frameGrid(OFFSET, OFFSET_KF);
  assert.deepEqual(grid, { fps: 60, start_s: 0.025 });
  assert.ok(close(T.quantize(4.19, 60, 0.025), 4.191667, 1e-6), 'frame 250 of this stream');
  assert.ok(close(T.quantize(4.19, 60), 251 / 60, 1e-9), 'a grid from 0 has no frame at 4.191667 s');
  const d = T.appendClip(T.emptyProject({ id: 'p' }), OFFSET, { id: 'A' }).doc;
  const c = d.clips[0];
  // the trim gesture: snap the in-edge to the keyframe at 4.191667 s, then trim on the source's grid
  const s = T.snap(4.19, T.trimSnapTargets(c, { keyframes: OFFSET_KF }), 0.2);
  assert.equal(s.kind, 'keyframe');
  const tr = T.trimClip(d, 'A', 'in', c.src_in + (s.t - c.at), { mediaDuration: 16, ...grid });
  const src_in = tr.clips[0].src_in;
  assert.ok(close(src_in, 0.025 + 250 / 60, 1e-9), `src_in ${src_in} is frame 250, not 4.2`);
  assert.equal(T.costHint(T.cutCost(OFFSET_KF, src_in, 60)), 'lossless');
  const old = T.trimClip(d, 'A', 'in', 4.191667, { mediaDuration: 16, fps: 60 }).clips[0].src_in;
  assert.equal(old, 4.2, 'without the start the grid is off by half a frame');
  assert.equal(T.cutCost(OFFSET_KF, old, 60).lossless, false, 'and the cost rule agrees with cut.plan (frame 251, smart)');
  // a split lands on the same grid; an in-edge dragged before the first frame means the file's start
  const sp = T.splitClip(d, 6.0, { newId: 'B', ...grid });
  assert.ok(close(sp.clips[1].src_in, 0.025 + 359 / 60, 1e-9), `split at ${sp.clips[1].src_in}`);
  const head = T.trimClip(tr, 'A', 'in', 0.004, { mediaDuration: 16, ...grid });
  assert.equal(head.clips[0].src_in, 0);
  // no start from the server: the first keyframe stands in for it (a stream's first frame is a keyframe)
  const bare = T.normalizeMedia({ id: 'e', duration_s: 16, video: { fps: 60 }, audio: [] });
  assert.equal(bare.video.start_s, null);
  assert.deepEqual(T.frameGrid(bare, OFFSET_KF), { fps: 60, start_s: 0.025 });
  assert.deepEqual(T.frameGrid(bare, []), { fps: 60, start_s: 0 });
  assert.deepEqual(T.frameGrid(null, [], 30), { fps: 30, start_s: 0 });
});

// An MPEG-TS remuxed to MKV keeps its container clock: file time 0 sits at 1.4 s on it and the first frame 0.021 s into
// the file (arsenal/media/README.md, "The house clock"; tests/test_arsenal_media_house_clock.py pins the server's half,
// tests/test_arsenal_edit_ui_smoke.py the browser's).
const TS_REMUX = T.normalizeMedia({ id: '1111111111111111', name: 'clock 1.4.mkv', duration_s: 8.02, container_start_s: 1.4,
  video: { codec: 'h264', w: 320, h: 180, fps: 30, start_s: 0.021333 }, audio: [{ title: null, start_s: 0 }] });

test('a source whose container clock starts at 1.4 s: the document speaks file times, its <video> element its own clock', () => {
  assert.equal(TS_REMUX.container_start_s, 1.4);
  assert.ok(close(T.elementTime(TS_REMUX, 2.0), 3.4, 1e-12), 'file time 2.0 is currentTime 3.4');
  assert.ok(close(T.sourceTime(TS_REMUX, 3.4), 2.0, 1e-12));
  for (const t of [0, 0.021333, 2.5, 7.9]) assert.ok(close(T.sourceTime(TS_REMUX, T.elementTime(TS_REMUX, t)), t, 1e-12));
  // the OBS recordings start at 0, and a server from before the ruling sends no container_start_s: nothing moves
  assert.equal(T.elementTime(MEDIA, 601.5), 601.5);
  assert.equal(T.sourceTime(T.normalizeMedia({ id: 'x', video: { fps: 60 }, audio: [] }), 3), 3);
  assert.equal(T.elementTime(null, 3), 3);
  // the frame grid is on the file clock: frame 90 sits at 3.021333 s, where cut.plan and edit.render put it
  const grid = T.frameGrid(TS_REMUX, [0.021333, 2.021333]);
  assert.deepEqual(grid, { fps: 30, start_s: 0.021333 });
  assert.ok(close(T.quantize(3.01, 30, grid.start_s), 0.021333 + 90 / 30, 1e-9));
  assert.equal(TS_REMUX.audio[0].start_s, 0, 'the sound starts with the file');
  assert.deepEqual(T.normalizeMedia(TS_REMUX), TS_REMUX);
});

test('a raw server media record goes straight onto the timeline (normalizeMedia is idempotent)', () => {
  const raw = { id: 'ffffffffffffffff', duration_s: 10, video: { fps: '60/1', start_s: 0 }, audio: [{ index: 1 }, { index: 2, title: 'Mic' }] };
  const r = T.appendClip(T.emptyProject(), raw, { id: 'a' });
  assert.deepEqual([r.doc.clips[0].src_out, r.doc.lanes.audio.map((l) => l.label)], [10, ['Mix', 'Mic']]);
  assert.deepEqual(T.normalizeMedia(MEDIA), MEDIA);
  assert.deepEqual(T.normalizeMedia(OFFSET), OFFSET);
  assert.deepEqual(T.ensureAudioLanes(T.emptyProject(), raw).lanes.audio.map((l) => l.id), ['A1', 'A2']);
});

test('a gesture replays on the document as it is at release: a save or a key mid-drag is kept, a vanished clip is a no-op', () => {
  const pressed = deepFreeze(threeClips());
  const trim = { kind: 'trim', id: 'c3', edge: 'out', srcT: 40, mediaDuration: 120, fps: 60, start_s: 0 };
  const atPress = T.applyGesture(pressed, trim);
  assert.equal(atPress.clips.find((c) => c.id === 'c3').src_out, 40);
  // a save landed mid-drag (new rev) and S split c1 meanwhile: both survive the release
  const now = deepFreeze({ ...T.splitClip(pressed, 5, { newId: 'c1b' }), rev: 7, name: 'named elsewhere' });
  const released = T.applyGesture(now, trim);
  assert.deepEqual([released.rev, released.name, released.clips.length], [7, 'named elsewhere', 4]);
  assert.equal(released.clips.find((c) => c.id === 'c3').src_out, 40);
  assert.deepEqual(T.validate(released), []);
  // the dragged clip was deleted mid-drag: nothing to do, the same document comes back
  const gone = deepFreeze(T.deleteClip(pressed, 'c3'));
  assert.equal(T.applyGesture(gone, trim), gone);
  // a move to the end, replayed after a split added a clip before it
  const move = { kind: 'move', id: 'c1', t: 100 };
  assert.deepEqual(ats(T.applyGesture(now, move)).map(([id]) => id), ['c1b', 'c2', 'c3', 'c1']);
  assert.equal(T.applyGesture(now, { kind: 'move', id: 'zz', t: 0 }), now);
  assert.equal(T.applyGesture(now, null), now);
});

test('Export panel QC words: "QC clean" only when audio.qc ran, found nothing, and the duration matched', () => {
  const ran = { path: 'X:/a.mp4', duration_s: 24, duration_expected_s: 24, duration_ok: true,
    qc: { ok: true, problems: [], I: -18.84, TP: -12.04, duration_s: 24 } };
  assert.deepEqual(qcSummary(ran), { kind: 'ok', text: '-18.8 LUFS · -12.0 dBTP · 24.00 s · QC clean' });
  const errored = { path: 'X:/out.mp4', duration_s: 3.2, duration_expected_s: 4.0, duration_ok: false, qc: { error: 'RuntimeError: ffmpeg exited 1' } };
  const e = qcSummary(errored);
  assert.equal(e.kind, 'warn');
  assert.equal(e.text, '3.20 s · duration 3.20 s, expected 4.00 s · QC failed to run: RuntimeError: ffmpeg exited 1');
  assert.deepEqual(qcSummary({ duration_ok: true, qc: { skipped: 'arsenal.media.audio not built yet' } }),
    { kind: 'warn', text: 'QC skipped: arsenal.media.audio not built yet' });
  assert.deepEqual(qcSummary({ duration_s: 4, duration_ok: true, qc: null }), { kind: 'warn', text: '4.00 s · QC not run' });
  assert.equal(qcSummary({ qc: { ok: false, problems: ['true peak -0.5 dBTP is over -1'] } }).text, 'QC: true peak -0.5 dBTP is over -1');
  assert.equal(qcSummary({ qc: { I: -14 } }).kind, 'warn', 'no problems list is no verdict, not a pass');
  const late = qcSummary({ ...ran, duration_ok: false, duration_s: 23.5 });
  assert.equal(late.kind, 'warn');
  assert.match(late.text, /duration 23\.50 s, expected 24\.00 s · QC passed the audio checks$/);
});
