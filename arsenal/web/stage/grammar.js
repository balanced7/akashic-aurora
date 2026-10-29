// Virtual Stage, the chord phrasing: arsenal/web/stage/grammar.js. A PURE recogniser (no DOM, no WebGL, no clock of its
// own): the page hands it normalised inputs and gets back decisions, synchronously, on the same call. Tests:
// tests/stage_grammar.test.mjs (every deterministic case of the round-3 design's table that this slice covers).
//
// Daniel, 2026-10-28, after recording two takes: "for parts of it i played the "wrong" buttons on my keyboard but it felt
// like an intuitive way to express fade in and fade out for the calmer moments" / "i mean like 8 7 6 5 4 then 456789";
// "like 5 7 6 could become laser sections 1-4 sections 8-12 then everything in the middle, then all of them could flash
// together"; "1 lets do A, i love that idea!" (option A: combos). 2026-10-29: "lets also land the chord phrasing."
//
// The design of record: docs/library/design/20261028_kick-vocabulary-round3-codex-2026-10-28_4a3a13.md (Codex, reviewed),
// section 4 "Recognition with immediate singles". Its numbers are design constants to test, not thresholds the takes
// established (G below, every one named).
//
// INPUT  {source, control, down, t, velocity, level, id}
//   source    "key" (a physical keyboard), "phone" (the phone's pad bar and strips), "midi" (the KeyLab through the engine):
//             a chord is SOURCE-LOCAL -- two devices never make one chord
//   control   "1".."9", "0" (number position 10), "C" (camera: a chord member, never a run member), "B" (the explicit
//             BREATH modifier, held)
//   t         the source's monotonic timestamp, ms (never the frame's arrival)
//   id        a unique press id; a release names it (or, without one, the control's current press)
//
// DECISIONS (each down is decided ON ITS OWN CALL: nothing ever waits to see whether more keys come)
//   press       dispatch this control's action now, as member `member` of lineage `lineage` (kind single/chord/strum)
//   reclassify  a lineage grew: single -> chord, or chord/single -> strum (absorbed: lineages of the run merged into it)
//   breath      a fade: phase start/step/end, delta (signed, in level units), explicit (the B modifier) or a slow sweep;
//               the sweep's start names the run's earlier presses (cancel) whose still-pending commands may be withdrawn
//   release     a press let go (dispatched: its action was dispatched and needs its legacy release)
//   walk        a moving interval: two-key states of the same gap, translated (start/step/end)
//   settle      a lineage can no longer grow: the semantic gesture is final (counted once)
//
// THE RULES (design section 4; the precedence for the CONTINUATION, never for withholding a single):
//   1. single   an unclaimed down dispatches once, immediately. OS auto-repeat (a down for a control already held) is
//               ignored.
//   2. chord    distinct downs within W = clamp(B/4, 60, 110) ms of the lineage's FIRST down (not a sliding window) join
//               it: one ensemble, one attack identity. W is frozen when the lineage begins.
//   3. strum    three or more ADJACENT number positions in one direction, every interval <= 90 ms, span <= 300 ms: the
//               lineage of the run's first key is reclassified as a strum (lineages of the run in between merge into it)
//               and the run's later keys join it in their measured order. A reversal closes it. Any other distinct key
//               within W of the strum's first down joins it too (one gesture, one attack).
//   4. sweep    three adjacent directional positions, each interval in [max(110, 0.28 B), min(450, 0.95 B)] ms: the THIRD
//               down establishes BREATH and does not fire its own single; the run's movement so far is the fade's first
//               move; from then on any adjacent down within 450 ms of the last is a fader step (either direction), never a
//               single; a gap over 450 ms or a non-adjacent down ends it (that down is then decided as usual).
//               Only when the fade can move the level that way (canFade): a run up the row at full level, or down it
//               at black, is ordinary playing and every key fires; a step that cannot move it ends the sweep ("limit").
//               NB the continuation takes ANY adjacent key within 450 ms, a deliberate hit included (design constant).
//               Descending positions fade out, ascending fade in (Daniel's "8 7 6 5 4 then 456789").
//   5. BREATH   B held: the number row is a fader from the first key -- no single fires; the first key anchors, each next
//               key moves the level by (position - previous position) / 9.
//   6. walk     two consecutive two-key chords of the same gap with a moved centre, the next pair beginning within
//               min(800, 2B) ms of the previous pair's first down: one moving interval (each pair is still a chord).
//   Adjacency (strums, sweeps) is the PC number row's: only sources whose controls sit in a row (positional, "key" by
//   default). The phone bar's pads are not in number order and the KeyLab's 12-pad geometry is not captured (design 8):
//   there, chords only.
//   B (beat ms) is read when a candidate begins, from beatMs() (a fresh clock) or 400 ms without one; a tempo change never
//   reclassifies keys already played.

export const GRAMMAR_API = "arsenal.stage-grammar/v1";
export const G = Object.freeze({
  fallbackBeatMs: 400,            // B when no clock is trustworthy (gesture windows only: never a beat anchor)
  chordFrac: 0.25, chordMinMs: 60, chordMaxMs: 110,
  strumGapMs: 90, strumSpanMs: 300, strumKeys: 3,
  slowFrac: 0.28, slowFloorMs: 110, slowCeilFrac: 0.95, slowCeilMs: 450, sweepKeys: 3, sweepEndMs: 450,
  walkBeats: 2, walkCapMs: 800,
  breathStep: 1 / 9,              // a fader step: one number position
  settleSlackMs: 50,              // a lineage stays open this long past W: a key event handled after a frame's settle can
                                  // carry an earlier timestamp still inside W (main-thread delay; review F6, 2026-10-29)
});
export const BREATH_CONTROL = "B";
export const CAMERA_CONTROL = "C";
// number position 1..10 (0 sits at 10, as on the keyboard), else null
export function positionOf(control) {
  const c = String(control);
  return /^[0-9]$/.test(c) ? (c === "0" ? 10 : Number(c)) : null;
}
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
// the windows a candidate freezes when it begins
export function windowsFor(B, o = G) {
  return { B, W: clamp(B * o.chordFrac, o.chordMinMs, o.chordMaxMs), slowMin: Math.max(o.slowFloorMs, o.slowFrac * B),
           slowMax: Math.min(o.slowCeilMs, o.slowCeilFrac * B), walk: Math.min(o.walkCapMs, o.walkBeats * B) };
}

export class Grammar {
  // beatMs(): ms per beat from a fresh, valid clock, or null; positional(source): its controls sit in a row;
  // canFade(dir, source): can a fade in this direction (+1 in, -1 out) still move the level? A slow run that cannot move
  // it (up at full, down at black) is ordinary playing: its keys fire as usual (review F4, 2026-10-29)
  constructor({ beatMs = () => null, positional = (source) => source === "key", canFade = () => true, opts = {} } = {}) {
    this.o = { ...G, ...opts };
    this.beatMs = beatMs;
    this.positional = positional;
    this.canFade = canFade;
    this.src = new Map();
    this.seq = 0;
    this.counts = { downs: 0, repeats: 0, dispatched: 0, suppressed: 0, singles: 0, chords: 0, strums: 0, walks: 0, sweeps: 0,
                    explicit: 0, breathSteps: 0, cancels: 0 };
  }
  B() { const b = this.beatMs ? this.beatMs() : null; return Number.isFinite(b) && b >= 200 && b <= 2000 ? b : this.o.fallbackBeatMs; }
  _s(source) {
    let s = this.src.get(source);
    if (!s) {
      s = { held: new Map(), byControl: new Map(), lineage: null, open: [], fast: { list: [] }, slow: { list: [], win: null },
            sweep: null, explicit: null, pair: null, walk: null };
      this.src.set(source, s);
    }
    return s;
  }
  input(ev) { return ev.down ? this._down(ev) : this._up(ev); }

  _down(ev) {
    const o = this.o, out = [];
    const source = String(ev.source || "key"), control = String(ev.control), t = Number(ev.t);
    const s = this._s(source);
    // the BREATH modifier, held
    if (control === BREATH_CONTROL) {
      if (s.explicit) { this.counts.repeats++; return out; }
      out.push(...this.settle(t, source));
      if (s.sweep) out.push(this._endSweep(s, t, "explicit"));
      s.explicit = { id: ev.id ?? `${source}:B:${++this.seq}`, last: null, t0: t };
      s.fast = { list: [] }; s.slow = { list: [], win: null };
      this.counts.explicit++;
      out.push({ type: "breath", phase: "arm", explicit: true, source, t, delta: 0 });
      return out;
    }
    // OS auto-repeat: a down for a control (or a press id) already held
    if (s.byControl.has(control) || (ev.id != null && s.held.has(ev.id))) { this.counts.repeats++; return out; }
    this.counts.downs++;
    const id = ev.id ?? `${source}:${control}:${++this.seq}`;
    const press = { id, source, control, pos: positionOf(control), t, velocity: ev.velocity ?? 0.8, dispatched: false, lineage: null };
    s.held.set(id, press); s.byControl.set(control, id);
    out.push(...this.settle(t, source));
    const pos = this.positional(source) ? press.pos : null;     // adjacency only where the controls sit in a row
    const step = o.breathStep;
    // 1. explicit BREATH (B held): a fader from the first key
    if (s.explicit && press.pos !== null) {
      const prev = s.explicit.last;
      s.explicit.last = press.pos;
      press.owner = "breath"; this.counts.suppressed++;
      if (prev !== null) this.counts.breathSteps++;
      out.push({ type: "breath", phase: prev === null ? "start" : "step", explicit: true, source, t, id, control,
                 delta: prev === null ? 0 : (press.pos - prev) * step });
      return out;
    }
    // 2. an established slow sweep owns adjacent downs within its gap
    if (s.sweep) {
      const stepDir = pos === null ? 0 : pos - s.sweep.last;
      if (pos !== null && Math.abs(stepDir) === 1 && t - s.sweep.lastT <= o.sweepEndMs && this.canFade(stepDir, source)) {
        const delta = (pos - s.sweep.last) * step;
        s.sweep.last = pos; s.sweep.lastT = t; s.sweep.steps++;
        press.owner = "breath"; this.counts.suppressed++; this.counts.breathSteps++;
        out.push({ type: "breath", phase: "step", explicit: false, source, t, id, control, delta, sweep: s.sweep.id });
        return out;
      }
      out.push(this._endSweep(s, t, pos === null ? "other" : t - s.sweep.lastT > o.sweepEndMs ? "gap" : Math.abs(stepDir) !== 1 ? "jump" : "limit"));
    }
    // 3. the runs this down extends (fast: a strum candidate; slow: a sweep candidate)
    if (pos !== null) {
      s.fast = this._extend(s.fast, press, (a, b, run) => b.t - a.t <= o.strumGapMs && b.t - run.list[0].t <= o.strumSpanMs);
      s.slow = this._extend(s.slow, press, (a, b, run) => { const iv = b.t - a.t; return iv >= run.win.slowMin && iv <= run.win.slowMax; });
      if (s.slow.list.length === 1) s.slow.win = windowsFor(this.B(), o);
    } else { s.fast = { list: [] }; s.slow = { list: [], win: null }; }
    // 4. a slow sweep takes over on its third key (that key fires no single) -- when the fade can move the level that way
    if (s.slow.list.length >= o.sweepKeys && this.canFade(Math.sign(s.slow.list[1].pos - s.slow.list[0].pos), source)) {
      const L = s.slow.list, dir = Math.sign(L[1].pos - L[0].pos);
      s.sweep = { id: `sweep${++this.seq}`, dir, last: pos, lastT: t, steps: L.length - 1, keys: L.map((p) => p.control) };
      press.owner = "breath"; this.counts.suppressed++; this.counts.sweeps++; this.counts.breathSteps += L.length - 1;
      const earlier = L.slice(0, -1);
      // the run's earlier keys already spoke (their singles); their lineages are the sweep's now (counted once, as the fade)
      for (const p of earlier) if (p.lineage) p.lineage.absorbedBy = s.sweep.id;
      out.push({ type: "breath", phase: "start", explicit: false, source, t, id, control, sweep: s.sweep.id, delta: (L.length - 1) * dir * step,
                 cancel: earlier.map((p) => ({ id: p.id, control: p.control, lineage: p.lineage ? p.lineage.id : null })) });
      s.slow = { list: [], win: null }; s.fast = { list: [] };
      return out;
    }
    // 5. a fast strum: the run's first key's lineage, reclassified, takes this key in its measured order
    if (s.fast.list.length >= o.strumKeys) {
      const L = s.fast.list, root = L[0].lineage;
      if (root && root.kind !== "strum") {
        const absorbed = [];
        for (const p of L.slice(1, -1)) if (p.lineage && p.lineage !== root && !absorbed.includes(p.lineage)) absorbed.push(p.lineage);
        for (const a of absorbed) this._merge(root, a);
        const from = root.kind;
        root.kind = "strum";
        out.push({ type: "reclassify", source, lineage: root.id, from, to: "strum", absorbed: absorbed.map((a) => a.id), t });
      }
      if (root) {
        if (s.walk) out.push(this._endWalk(s, t, "strum"));
        this._join(root, press, out); s.lineage = root;
        return out;
      }
    }
    // 6. a chord: a distinct control within W of the lineage's first down -- a strum's lineage too (a mash 4 5 6 and 1
    //    inside W is one gesture, one attack: review F2, 2026-10-29); it stays a strum, the key joins it as a member
    const cur = s.lineage;
    if (cur && !cur.closed && t - cur.t0 <= cur.win.W && !cur.members.some((m) => m.control === control)) {
      if (cur.kind === "single") { cur.kind = "chord"; out.push({ type: "reclassify", source, lineage: cur.id, from: "single", to: "chord", absorbed: [], t }); }
      this._join(cur, press, out);
      this._pairs(s, cur, t, out);
      return out;
    }
    // 7. a single: a new lineage, dispatched now
    const L = { id: `g${++this.seq}`, source, kind: "single", t0: t, win: windowsFor(this.B(), o), members: [], closed: false, settled: false,
                walk: null, absorbedBy: null };
    s.lineage = L; s.open.push(L);
    this._join(L, press, out);
    return out;
  }
  // a run (adjacent positions, one direction, each step passing ok) extended by press, or a new run of press alone
  _extend(run, press, ok) {
    const list = run.list, last = list[list.length - 1];
    if (last && Math.abs(press.pos - last.pos) === 1) {
      const dir = Math.sign(press.pos - last.pos);
      const sameDir = list.length < 2 || Math.sign(last.pos - list[list.length - 2].pos) === dir;
      if (sameDir && ok(last, press, run)) return { ...run, list: [...list, press] };
    }
    return { list: [press], win: null };
  }
  _join(L, press, out) {
    press.lineage = L; press.dispatched = true;
    L.members.push(press);
    this.counts.dispatched++;
    out.push({ type: "press", source: press.source, id: press.id, control: press.control, velocity: press.velocity, t: press.t,
               lineage: L.id, kind: L.kind, member: L.members.length - 1 });
  }
  _merge(root, other) {
    for (const m of other.members) { m.lineage = root; root.members.push(m); }
    root.members.sort((a, b) => a.t - b.t);
    other.members = []; other.absorbedBy = root.id; other.closed = true;
  }
  // moving intervals: two-key chords of one gap whose centre moves
  _pairs(s, L, t, out) {
    const nums = L.members.filter((m) => m.pos !== null);
    if (L.members.length === 2 && nums.length === 2) {
      const gap = Math.abs(nums[0].pos - nums[1].pos), centre = (nums[0].pos + nums[1].pos) / 2;
      const prev = s.pair;
      const cont = prev && prev.lineage !== L && prev.lineage.members.length === 2 && prev.gap === gap && prev.centre !== centre &&
                   L.t0 - prev.t0 <= (s.walk ? s.walk.win : prev.lineage.win.walk);
      if (cont) {
        if (s.walk && s.walk.last === prev.lineage) {
          s.walk.pairs++; s.walk.last = L; L.walk = s.walk.id;
          out.push({ type: "walk", phase: "step", source: L.source, walk: s.walk.id, gap, centre, pairs: s.walk.pairs, t });
        } else {
          if (s.walk) out.push(this._endWalk(s, t, "new"));
          s.walk = { id: `walk${++this.seq}`, gap, pairs: 2, last: L, win: prev.lineage.win.walk };
          prev.lineage.walk = s.walk.id; L.walk = s.walk.id;
          out.push({ type: "walk", phase: "start", source: L.source, walk: s.walk.id, gap, centre, pairs: 2, t });
        }
      } else if (s.walk && s.walk.last !== L) out.push(this._endWalk(s, t, "mismatch"));
      s.pair = { gap, centre, t0: L.t0, lineage: L };
    } else if (L.members.length > 2) {
      if (L.walk && s.walk && s.walk.id === L.walk) { L.walk = null; s.walk.pairs--; out.push(this._endWalk(s, t, "three")); }
      if (s.pair && s.pair.lineage === L) s.pair = null;
    }
  }
  _endWalk(s, t, why) {
    const w = s.walk; s.walk = null;
    if (w.pairs >= 2) this.counts.walks++;
    return { type: "walk", phase: "end", walk: w.id, pairs: w.pairs, why, t };
  }
  _endSweep(s, t, why) {
    const w = s.sweep; s.sweep = null;
    return { type: "breath", phase: "end", explicit: false, sweep: w.id, steps: w.steps, why, t, delta: 0 };
  }
  _up(ev) {
    const out = [];
    const source = String(ev.source || "key"), control = String(ev.control), t = Number(ev.t);
    const s = this._s(source);
    if (control === BREATH_CONTROL) {
      if (!s.explicit) return out;
      s.explicit = null;
      out.push({ type: "breath", phase: "end", explicit: true, source, t, delta: 0, why: "release" });
      return out;
    }
    const id = ev.id != null ? ev.id : s.byControl.get(control);
    const press = id != null ? s.held.get(id) : null;
    if (!press) return out;                          // an old session's release, or a duplicate: nothing to let go
    s.held.delete(id);
    if (s.byControl.get(press.control) === id) s.byControl.delete(press.control);
    out.push({ type: "release", source, id, control: press.control, t, dispatched: press.dispatched, lineage: press.lineage ? press.lineage.id : null });
    return out;
  }
  // blur, visibility loss, pointer cancel, a lost link: every press of the source lets go, every prefix is abandoned
  cancel(source, t) {
    const s = this._s(String(source)), out = [];
    this.counts.cancels++;
    for (const [id, p] of s.held) out.push({ type: "release", source, id, control: p.control, t, dispatched: p.dispatched, lineage: p.lineage ? p.lineage.id : null, cancel: true });
    s.held.clear(); s.byControl.clear();
    if (s.sweep) out.push(this._endSweep(s, t, "cancel"));
    if (s.explicit) { s.explicit = null; out.push({ type: "breath", phase: "end", explicit: true, source, t, delta: 0, why: "cancel" }); }
    if (s.walk) out.push(this._endWalk(s, t, "cancel"));
    s.fast = { list: [] }; s.slow = { list: [], win: null }; s.pair = null;
    out.push(...this.settle(Infinity, source));
    s.lineage = null;
    return out;
  }
  // the tick: lineages that can no longer grow settle (once), a sweep past its gap ends, a walk past its window ends
  settle(t, only = null) {
    const o = this.o, out = [];
    for (const [source, s] of this.src) {
      if (only !== null && source !== only) continue;
      if (s.sweep && t - s.sweep.lastT > o.sweepEndMs) out.push(this._endSweep(s, t, "gap"));
      const fl = s.fast.list, fLast = fl[fl.length - 1];
      const fastLive = fLast && t - fLast.t <= o.strumGapMs && t - fl[0].t <= o.strumSpanMs;
      const sl = s.slow.list, sLast = sl[sl.length - 1];
      const slowLive = sLast && s.slow.win && t - sLast.t <= s.slow.win.slowMax;
      const keep = [];
      for (const L of s.open) {
        const growing = t <= L.t0 + L.win.W + o.settleSlackMs || (fastLive && fl.some((p) => p.lineage === L)) || (slowLive && sl.some((p) => p.lineage === L));
        if (growing && t !== Infinity) { keep.push(L); continue; }
        L.settled = true; L.closed = true;
        if (L.absorbedBy) continue;
        if (!L.walk) this.counts[L.kind === "single" ? "singles" : L.kind === "chord" ? "chords" : "strums"]++;
        out.push({ type: "settle", source, lineage: L.id, kind: L.kind, walk: L.walk, controls: L.members.map((m) => m.control), t0: L.t0,
                   span: L.members.length ? L.members[L.members.length - 1].t - L.t0 : 0 });
        if (s.walk && L.members.length !== 2 && !L.walk) out.push(this._endWalk(s, t, "unrelated"));
      }
      s.open = keep;
      if (s.walk && t !== Infinity && t - s.walk.last.t0 > s.walk.win) out.push(this._endWalk(s, t, "timeout"));
    }
    return out;
  }
  // what the HUD and the receipts read
  status() {
    const src = {};
    for (const [k, s] of this.src) src[k] = { held: [...s.byControl.keys()], lineage: s.lineage ? { id: s.lineage.id, kind: s.lineage.kind, controls: s.lineage.members.map((m) => m.control) } : null,
                                               sweep: s.sweep ? { id: s.sweep.id, steps: s.sweep.steps } : null, explicit: !!s.explicit, walk: s.walk ? { id: s.walk.id, pairs: s.walk.pairs } : null };
    return { api: GRAMMAR_API, counts: { ...this.counts }, sources: src };
  }
}
