// Virtual Stage v0, the beat grid: arsenal/web/stage/grid.js (pure ES module). Tests: tests/stage_grid.test.mjs.
//
// ONE beat position for everything: the page grid of the Lasers v2 spec (section 3.2), pos(t) = anchor + (t - tAnchor)
// / period, in beats, monotonic. The fixtures' effects, the kinetics, the lasers and the camera all read it, so they can
// never disagree about where the ONE is.
//
// The engine (arsenal/keylab/vj.py, Server-Sent Events) sends each beat ~250 ms ahead: {t: "beat", due_ms, bpm, n, conf}
// and, from the S1 beat clock on, bar (1..4, 0 = unknown) with bar_src, and ver (bumped on every hard re-anchor, for
// instance a tap on the KeyLab's Tap button). For each prediction the grid compares where it would have put that beat
// (p^ = pos(due)) with the nearest whole beat:
//   ver changed          hard re-anchor AT THAT BEAT: pos(due) is a whole beat from then on;
//   |error| <= 0.25 beat slew: the next beat is stretched or squeezed by at most 10 % so the error is gone by the beat
//                        after this one; pos stays continuous and never runs backward;
//   |error| > 0.25 beat  hard re-anchor.
// A hard re-anchor never moves pos backward either: if the new grid is behind, pos holds still until the new grid
// catches up (at most half a beat), then runs on it.
//
// It also keeps the bar (from the engine's bar field, or from a tap / DROP NOW on a ONE; a guess otherwise) and the
// phrase (8 bars, counted from the last drop or ONE). Light is evaluated at the presentation time tEval = rafNow +
// presentLagMs, as Lasers v2 does. The same object is the Lasers clock: {bpm, conf, posAt, phaseAt, nextBeatAt, alive}.

export const GRID_API = "arsenal.stage-grid/v1";
export const SLEW_MAX_ERROR = 0.25;
export const SLEW_STRETCH = 0.10;
export const PHRASE_BARS = 8;

export class BeatGrid {
  constructor({ bpm = 150, presentLagMs = 1000 / 60, flywheelMs = 4000, t0 = 0 } = {}) {
    this.bpm = bpm;
    this.period = 60000 / bpm;
    this.t0 = t0; this.p0 = 0; this.rate = 1 / this.period;   // the running segment
    this.hold = -Infinity;                                       // a floor on pos after a hard re-anchor that went back
    this.ver = null;
    this.conf = 0;
    this.locked = false;
    this.lastRecv = -Infinity;
    this.flywheelMs = flywheelMs;
    this.presentLagMs = presentLagMs;
    this.barAnchor = 0;           // a beat position where a bar's ONE falls
    this.barSrc = "guess";
    this.phraseAnchor = 0;
    this.stats = { beats: 0, slews: 0, hard: 0, held: 0, vers: 0 };
    this.log = [];                // [{t, kind, err}] bounded, for receipts
  }
  _seg(t) { return this.p0 + (t - this.t0) * this.rate; }
  posAt(t) { const p = this._seg(t); return p < this.hold ? this.hold : p; }
  phaseAt(t) { const p = this.posAt(t); return p - Math.floor(p); }
  nextBeatAt(t) {
    const p = this.posAt(t), next = Math.floor(p) + 1;
    const tSeg = this.t0 + (Math.max(next, this.hold) - this.p0) / this.rate;
    return Math.max(t, tSeg);
  }
  alive(t) { return t - this.lastRecv < this.flywheelMs; }
  // the bar beat 1..4 and the fraction through the bar at t
  barAt(t) {
    const q = this.posAt(t) - this.barAnchor;
    const b = ((Math.floor(q) % 4) + 4) % 4;
    return { beat: b + 1, bar: Math.floor(q / 4), frac: (q / 4) - Math.floor(q / 4) };
  }
  phraseAt(t) {
    const q = (this.posAt(t) - this.phraseAnchor) / (4 * PHRASE_BARS);
    return { phrase: Math.floor(q), frac: q - Math.floor(q) };
  }
  // The beat position of the next bar line (a ONE) strictly after pos p.
  nextBarPos(p) { return this.barAnchor + 4 * (Math.floor((p - this.barAnchor) / 4 + 1e-9) + 1); }
  nextPhrasePos(p) {
    const L = 4 * PHRASE_BARS;
    return this.phraseAnchor + L * (Math.floor((p - this.phraseAnchor) / L + 1e-9) + 1);
  }
  // Mark the beat nearest t as a ONE (a tap on the downbeat, DROP NOW landing): bar and phrase count from it.
  markOne(t, { phrase = true } = {}) {
    const p = Math.round(this.posAt(t));
    this.barAnchor = p;
    this.barSrc = "mark";
    if (phrase) this.phraseAnchor = p;
    return p;
  }
  _note(t, kind, err) { if (this.log.length < 512) this.log.push({ t: +t.toFixed(2), kind, err: +err.toFixed(4) }); }
  _hard(T, target, nowMs) {
    // pos(T) = target on the new grid; never backward from where pos is now
    const before = this.posAt(nowMs);
    this.p0 = target; this.t0 = T; this.rate = 1 / this.period;
    const after = this._seg(nowMs);
    this.hold = after < before ? before : -Infinity;
    if (after < before) this.stats.held++;
    this.stats.hard++;
  }
  // A parsed beat event (vj-core parseEvent fields plus bar, bar_src, ver), received at nowMs.
  beat(ev, nowMs) {
    const P = 60000 / ev.bpm;
    const due = Math.max(-P / 2, Math.min(ev.due_ms, 4000));
    const T = nowMs + due;
    this.bpm = ev.bpm; this.period = P;
    this.conf = ev.conf ?? 0.5;
    this.lastRecv = nowMs;
    this.stats.beats++;
    const verChanged = Number.isInteger(ev.ver) && ev.ver >= 0 && this.ver !== null && ev.ver !== this.ver;
    if (Number.isInteger(ev.ver) && ev.ver >= 0) { if (verChanged) this.stats.vers++; this.ver = ev.ver; }
    const pHat = this.posAt(T);
    let target = Math.round(pHat);
    const err = target - pHat;
    if (!this.locked) {
      // the first beat: put it on the next whole beat at or after where pos is, so pos only ever moves forward
      target = Math.ceil(pHat - 1e-9);
      this._hard(T, target, nowMs);
      this.locked = true;
      this._note(T, "lock", 0);
    } else if (verChanged || Math.abs(err) > SLEW_MAX_ERROR) {
      this._hard(T, target, nowMs);
      this._note(T, verChanged ? "ver" : "hard", err);
    } else {
      // slew: from (now, pos(now)) reach target + 1 at T + P, the rate held within +-10 % of the tempo's
      const pNow = this.posAt(nowMs);
      const span = T + P - nowMs;
      let r = span > 1 ? (target + 1 - pNow) / span : 1 / P;
      r = Math.min((1 + SLEW_STRETCH) / P, Math.max((1 - SLEW_STRETCH) / P, r));
      this.p0 = pNow; this.t0 = nowMs; this.rate = r; this.hold = -Infinity;
      this.stats.slews++;
      if (Math.abs(err) > 1e-6) this._note(T, "slew", err);
    }
    if (Number.isInteger(ev.bar) && ev.bar >= 1 && ev.bar <= 4) {
      this.barAnchor = target - (ev.bar - 1);
      this.barSrc = ev.bar_src || "engine";
    }
    return { T, target, err };
  }
  // Free-run at a tempo with no engine (the demo, a dead link): only the rate changes, at the current position.
  setTempo(bpm, nowMs) {
    const p = this.posAt(nowMs);
    this.bpm = bpm; this.period = 60000 / bpm;
    this.p0 = p; this.t0 = nowMs; this.rate = 1 / this.period; this.hold = -Infinity;
  }
  clock() {
    return {
      get bpm() { return this._g.bpm; }, get conf() { return this._g.conf; }, _g: this,
      posAt: (t) => this.posAt(t), phaseAt: (t) => this.phaseAt(t), nextBeatAt: (t) => this.nextBeatAt(t),
      alive: () => true,
    };
  }
}

// The extra S1 fields of a raw beat event (master's vj-core parseEvent drops them): bar 1..4 and ver.
export function beatExtras(obj) {
  const bar = Number(obj && obj.bar), ver = Number(obj && obj.ver);
  return {
    bar: Number.isInteger(bar) && bar >= 1 && bar <= 4 ? bar : 0,
    bar_src: obj && typeof obj.bar_src === "string" ? obj.bar_src.slice(0, 8) : "",
    ver: Number.isInteger(ver) && ver >= 0 ? ver : -1,
  };
}

// ------------------------------------------------------------------------------------------------ the demo clock --
// Beats with no engine: the same event shape the engine sends, announced `leadMs` ahead, deterministic. A tempo ramp
// (from, to, over beats) and a tap (a ver bump with a phase shift) can be scripted, for the receipts.
export class DemoBeats {
  constructor({ bpm = 150, leadMs = 220, startMs = 0, ramp = null, taps = [] } = {}) {
    this.bpm0 = bpm;
    this.leadMs = leadMs;
    this.startMs = startMs;
    this.ramp = ramp;          // {fromBeat, toBeat, toBpm}
    this.taps = taps;          // [{beat, shiftMs}] a tap moves the beat by shiftMs from that beat on, and bumps ver
    this.next = 0;
    this.times = [];           // the true beat times (ms), for receipts
  }
  bpmAt(i) {
    const r = this.ramp;
    if (!r || i <= r.fromBeat) return this.bpm0;
    if (i >= r.toBeat) return r.toBpm;
    return this.bpm0 + (r.toBpm - this.bpm0) * (i - r.fromBeat) / (r.toBeat - r.fromBeat);
  }
  // the true time of beat i (ms)
  timeOf(i) {
    while (this.times.length <= i) {
      const k = this.times.length;
      const t = k === 0 ? this.startMs : this.times[k - 1] + 60000 / this.bpmAt(k - 1);
      this.times.push(t);
    }
    let shift = 0;
    for (const tp of this.taps) if (i >= tp.beat) shift += tp.shiftMs;
    return this.times[i] + shift;
  }
  verOf(i) { let v = 0; for (const tp of this.taps) if (i >= tp.beat) v++; return v; }
  tick(nowMs, emit) {
    while (this.timeOf(this.next) - this.leadMs <= nowMs) {
      const i = this.next++;
      const due = this.timeOf(i) - nowMs;
      emit({ t: "beat", due_ms: due, bpm: this.bpmAt(i), conf: 0.95, n: i, on_beat: 0.9, bar: (i % 4) + 1, bar_src: "guess",
             ver: this.verOf(i), src: "demo" });
    }
  }
}
