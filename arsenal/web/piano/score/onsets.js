// Onset groups for live sheet music: arsenal/web/piano/score/onsets.js (pure ES module: no DOM, nothing reads a clock).
// Stage T1 of research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (section 6.1), amended by
// plan-amendments.md in the same folder. Every time is event time in ms (performance or session ms; one timebase per
// instance). The caller passes "now" to flush(); a group is handed out once no later note can change it.
//
//   const on = createOnsets();                 // or createOnsets(LANE_ONSET_PARAMS) for the tempo lane's 40 ms groups
//   on.noteOn(60, 90, 1000.0); on.noteOn(64, 80, 1012.0); on.pedal(true, 1100.0); on.noteOff(60, 1400.0);
//   on.flush(1200.0)   // -> [{ t: 1000, notes: [...], low: 60, hi: 64, s: 1.73.., kind: "chord", avail: 1120, ... }]
//
// Rules (plan 6.1; start values, retuned on LS9 labelled takes):
// - Chord: a note-on within chordMs (40) of the open group's first note joins it (performance.py ONSET_MERGE_MS).
// - Near-chord across hands: within nearMs (60) of the group's first note and nearGap (7) or more semitones outside the
//   group's range, the note joins too (the section 3 run's rule).
// - Rolled chord: rollMin (3) or more notes, pitch-monotonic in time order, first-to-last spread rollMinSpreadMs (50) to
//   rollSpanMs (120), every gap under rollGapMs (60), and every earlier note still held (or the pedal down) at the last
//   note: the groups merge into one, kind "roll". Reading of the plan's "chained within 120 ms": the whole chain lies
//   inside 120 ms, and a gap of 60 ms or more starts a run instead (next rule), so a run is never a roll.
// - Broken-chord run: runMin (4) or more single-note groups, runGapMinMs-runGapMaxMs (60-300) apart, pitch-monotonic:
//   each is flagged run: true and keeps its own rhythm.
// - Grace candidate: a single-note group held under graceHeldMs (110), graceLeadMinMs-graceLeadMaxMs (30-120) before a
//   group holding a note 1-2 semitones away. Flagged grace: { to, leadMs }; the grid test (the main note on a slot, the
//   grace off it) belongs to T3 (LS2). Within one 40 ms chord group no grace is looked for in v1.
// - Salience (for beat.js): sqrt(sum(0.4 + vel/127)), + bassBonus (0.5) if the lowest note is at or below bassNote (G3).
//
// Finality: a group is handed out at avail = its first note + max(chordMs, nearMs), later when a roll could still form
// (first note + rollSpanMs, and the last candidate group's own window). LANE_ONSET_PARAMS (chord window only) gives
// avail = t + 40 ms, which is the tempo lane tracker's group; S3_ONSET_PARAMS is the section 3 quantizer's grouping.

export const ONSETS_API = "arsenal.piano.score.onsets/v0";

export const ONSET_PARAMS = Object.freeze({
  chordMs: 40, nearMs: 60, nearGap: 7,
  rollMin: 3, rollMinSpreadMs: 50, rollSpanMs: 120, rollGapMs: 60,
  runMin: 4, runGapMinMs: 60, runGapMaxMs: 300,
  graceHeldMs: 110, graceLeadMinMs: 30, graceLeadMaxMs: 120, graceStepMin: 1, graceStepMax: 2,
  bassNote: 55, bassBonus: 0.5,
});

// The tempo lane's tracker grouping (tracker.mjs makeGroups): 40 ms chords only.
export const LANE_ONSET_PARAMS = Object.freeze({ ...ONSET_PARAMS, nearMs: 0, rollSpanMs: 0 });
// The section 3 quantizer's grouping (quant.mjs groupsOf): 40 ms chords plus the near-chord rule, no roll merge.
export const S3_ONSET_PARAMS = Object.freeze({ ...ONSET_PARAMS, rollSpanMs: 0 });

const KEEP_DONE = 64;

export function salienceOf(notes, params = ONSET_PARAMS) {
  let raw = 0, low = 999;
  for (const n of notes) { raw += 0.4 + n.vel / 127; if (n.note < low) low = n.note; }
  return Math.sqrt(raw) + (low <= params.bassNote ? params.bassBonus : 0);
}

export function createOnsets(params = {}) {
  const c = { ...ONSET_PARAMS, ...params };
  const win = Math.max(c.chordMs, c.nearMs);
  const open = [];              // groups still able to change, oldest first
  const done = [];              // the last KEEP_DONE handed-out groups (run and grace look-back)
  const held = new Map();       // midi -> note records without a release, newest last
  const pedalLog = [];          // [{ t, down }] in time order
  let nextNote = 0, nextGroup = 0;

  const pedalDownAt = (t) => {
    let down = false;
    for (const p of pedalLog) { if (p.t > t) break; down = p.down; }
    return down;
  };

  function newGroup(n) {
    const g = { id: nextGroup++, t: n.t, notes: [n], lo: n.note, hi: n.note, avail: null, kind: "single", run: false, grace: null };
    n.group = g;
    return g;
  }

  function noteOn(note, vel, t) {
    const n = { id: nextNote++, note, vel, t, off: null, soundEnd: null, by: null, group: null };
    const list = held.get(note);
    if (list) list.push(n); else held.set(note, [n]);
    const g = open[open.length - 1];
    const join = g && (t - g.t <= c.chordMs
      || (c.nearMs > 0 && t - g.t <= c.nearMs && (note >= g.hi + c.nearGap || note <= g.lo - c.nearGap)));
    if (join) {
      g.notes.push(n); n.group = g;
      if (note > g.hi) g.hi = note;
      if (note < g.lo) g.lo = note;
    } else {
      open.push(newGroup(n));
      for (const x of done.slice(-4)) graceCheck(x);
    }
    return n;
  }

  function noteOff(note, t) {
    const list = held.get(note);
    if (!list || !list.length) return null;
    const n = list.pop();
    if (!list.length) held.delete(note);
    n.off = t;
    if (n.group && n.group.avail != null) graceCheck(n.group);
    return n;
  }

  function soundEnd(note, t, by = null) {
    // the newest note of this pitch that has no sound end yet
    for (let i = done.length - 1; i >= 0; i--) for (const n of done[i].notes) if (n.note === note && n.soundEnd == null) { n.soundEnd = t; n.by = by; return n; }
    for (let i = open.length - 1; i >= 0; i--) for (const n of open[i].notes) if (n.note === note && n.soundEnd == null) { n.soundEnd = t; n.by = by; return n; }
    return null;
  }

  function pedal(down, t) { pedalLog.push({ t, down: !!down }); if (pedalLog.length > 256) pedalLog.splice(0, 128); }

  function isRoll(groups) {
    const ns = groups.flatMap((g) => g.notes).sort((a, b) => a.t - b.t || a.note - b.note);
    if (ns.length < c.rollMin) return false;
    const spread = ns[ns.length - 1].t - ns[0].t;
    if (spread < c.rollMinSpreadMs || spread > c.rollSpanMs) return false;
    let up = true, downward = true;
    for (let i = 1; i < ns.length; i++) {
      if (ns[i].t - ns[i - 1].t >= c.rollGapMs) return false;
      if (ns[i].note < ns[i - 1].note) up = false;
      if (ns[i].note > ns[i - 1].note) downward = false;
    }
    if (!up && !downward) return false;
    const last = ns[ns.length - 1].t;
    const pedalled = pedalDownAt(last);
    return ns.every((n) => n === ns[ns.length - 1] || n.off == null || n.off >= last || pedalled);
  }

  function finish(g, avail) {
    g.notes.sort((a, b) => a.t - b.t || a.note - b.note);
    g.avail = avail;
    g.low = g.lo;
    g.s = salienceOf(g.notes, c);
    g.pcs = new Set(g.notes.map((n) => ((n.note % 12) + 12) % 12));
    g.spread = g.notes[g.notes.length - 1].t - g.t;
    if (g.kind !== "roll") g.kind = g.notes.length > 1 ? "chord" : "single";
    done.push(g);
    if (done.length > KEEP_DONE) done.splice(0, done.length - KEEP_DONE);
    markRun();
    graceCheck(g);
    for (const x of done.slice(-4, -1)) graceCheck(x);
    return g;
  }

  function markRun() {
    const n = done.length;
    if (n < c.runMin) return;
    const tail = done.slice(n - c.runMin);
    if (!tail.every((g) => g.notes.length === 1)) return;
    let up = true, downward = true;
    for (let i = 1; i < tail.length; i++) {
      const gap = tail[i].t - tail[i - 1].t;
      if (gap < c.runGapMinMs || gap > c.runGapMaxMs) return;
      if (tail[i].notes[0].note <= tail[i - 1].notes[0].note) up = false;
      if (tail[i].notes[0].note >= tail[i - 1].notes[0].note) downward = false;
    }
    if (up || downward) for (const g of tail) g.run = true;
  }

  function graceCheck(x) {
    if (!x || x.grace || x.notes.length !== 1) return;
    const n = x.notes[0];
    if (n.off == null || n.off - n.t >= c.graceHeldMs) return;
    for (const y of [...done, ...open]) {
      if (y === x) continue;
      const lead = y.t - x.t;
      if (lead < c.graceLeadMinMs || lead > c.graceLeadMaxMs) continue;
      const hit = y.notes.find((m) => { const d = Math.abs(m.note - n.note); return d >= c.graceStepMin && d <= c.graceStepMax; });
      if (hit) { x.grace = { to: hit.note, leadMs: lead }; return; }
    }
  }

  // Hand out every group no note at or before nowMs can still change. Call after delivering every event with t <= nowMs.
  function flush(nowMs) {
    const out = [];
    while (open.length) {
      const a = open[0];
      if (nowMs < a.t + win) break;
      let avail = a.t + win;
      if (c.rollSpanMs > 0) {
        if (nowMs < a.t + c.rollSpanMs) break;
        let k = 1;
        while (k < open.length && open[k].t <= a.t + c.rollSpanMs) k++;
        if (k > 1 && nowMs < open[k - 1].t + win) break;
        avail = Math.max(avail, a.t + c.rollSpanMs, k > 1 ? open[k - 1].t + win : 0);
        for (let m = k - 1; m >= 1; m--) {
          const cand = open.slice(0, m + 1);
          if (!isRoll(cand)) continue;
          for (const g of cand.slice(1)) for (const nn of g.notes) { a.notes.push(nn); nn.group = a; a.lo = Math.min(a.lo, nn.note); a.hi = Math.max(a.hi, nn.note); }
          a.kind = "roll";
          open.splice(1, m);
          break;
        }
      }
      open.shift();
      out.push(finish(a, avail));
    }
    return out;
  }

  return {
    noteOn, noteOff, soundEnd, pedal, flush,
    pending: () => open.length,
    recent: () => done.slice(),
    params: () => ({ ...c }),
  };
}

// Offline: every group of a note list ([{ t, note, vel, off? }] or practice-log events with t_ms), in time order.
export function groupNotes(items, params = {}) {
  const on = createOnsets(params);
  const evs = [];
  for (const x of items) {
    if (x.kind === undefined) { evs.push({ t: x.t, kind: "on", note: x.note, vel: x.vel }); if (x.off != null) evs.push({ t: x.off, kind: "off", note: x.note }); }
    else if (x.kind === "on" || x.kind === "off" || x.kind === "pedal") evs.push({ ...x, t: x.t_ms });
  }
  const order = { off: 0, pedal: 1, on: 2 };
  evs.sort((a, b) => a.t - b.t || order[a.kind] - order[b.kind]);
  const out = [];
  for (const e of evs) {
    out.push(...on.flush(e.t - 1e-9));
    if (e.kind === "on") on.noteOn(e.note, e.vel, e.t);
    else if (e.kind === "off") on.noteOff(e.note, e.t);
    else on.pedal(e.down, e.t);
  }
  out.push(...on.flush(Infinity));
  return out;
}
