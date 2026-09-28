// The metronome: arsenal/web/piano/metronome.js (ES module; takes an AudioContext, touches no DOM).
//
// WHY THIS EXISTS, and why it is a measuring instrument rather than a convenience.
//
// The 2026-09-27 review of the score lane found one defect underneath every expressive claim the
// system can make: THE BEAT GRID IS WELDED TO THE PLAYER'S OWN ONSETS. beat.js snaps each emitted
// beat 80% onto the nearest onset group (phaseGain 0.8, beat.js:74, :198), so 78.9% of exported
// beat times ARE his note times and ~half of all on-beat notes carry exactly 0.000 ms of
// deviation. Against that grid "am I ahead of or behind the beat" is not hard to answer, it is
// UNANSWERABLE IN PRINCIPLE -- the ruler is cut from the thing being measured. Every per-note feel
// number the lane produces today measures its own anchoring.
//
// The fix is an external reference the tracker is not allowed to move: a click the human plays to.
// score/index.js:102 already accepts one -- `beats`, an array of >=3 beat times, the "jam rung"
// that bypasses the tracker entirely -- and nothing has ever supplied it (score_cli.mjs:97 returns
// `beats: null`, hardcoded). This module supplies it. That is the point of the file; the presets
// and the volume slider are so it is pleasant enough to actually use.
//
//   const m = createMetronome({ ctx, onClick });
//   m.setBpm(96); m.setMeter(4); m.setFeel("triplet"); m.setSound("woodblock"); m.setVolume(0.6);
//   m.tap(performance.now());        // tap four times to set the tempo
//   m.start(); ... m.stop();
//
// TIMEKEEPING, stated exactly, because a reference clock that is casually wrong is worse than none.
//
// 1. SCHEDULING. setTimeout/rAF cannot place a sound accurately; WebAudio can. So a 25 ms poll
//    schedules every click falling in the next 120 ms at an exact AudioContext time (the standard
//    two-clock pattern). Jitter in the poll therefore cannot reach the sound.
// 2. WHAT TIME A CLICK *IS*. A click scheduled at context time T is not heard at T: it leaves the
//    output `ctx.outputLatency` seconds later (plus `baseLatency` of graph delay). The review
//    named unmeasured audio output latency as one of two systematic biases "of exactly the size
//    being reported" (+2..20 ms). So the time reported for a beat is the AUDIBLE time,
//    T + outputLatency, never the scheduled time.
// 3. MAPPING AUDIO TIME TO PAGE TIME. The log and every note event count in page-clock ms, so a
//    click must be expressed there. `ctx.getOutputTimestamp()` returns a matched
//    {contextTime, performanceTime} pair and is exactly the right instrument; it is re-read on
//    every poll, so the mapping tracks clock drift instead of assuming a single anchor holds for a
//    ten-minute take. Where it is missing (older Safari) a fresh anchor is taken per poll, which is
//    poorer but never stale.
// 4. WHAT IS NOT CORRECTED. Sensorimotor negative mean asynchrony -- a human tapping to a click
//    lands 20-50 ms early, reliably, and it is a property of the human, not the clock. This module
//    does NOT subtract it. It is the signal, not an error; a drummer's relationship to the click is
//    the thing being measured, so nothing here may quietly absorb it.
//
// onClick receives every scheduled click BEFORE it sounds:
//   { n, bar, beatInBar, sub, subs, isBeat, isDownbeat, audio_ms, page_ms, bpm, latency_ms }
// `n` counts beats from start (fractional for subdivisions). page_ms is the AUDIBLE time. Only
// clicks with isBeat === true belong in a `beats` array for score/index.js.

const POLL_MS = 25;
const LOOKAHEAD_S = 0.12;
const TAP_TIMEOUT_MS = 2500;   // a gap longer than this starts a new tap group rather than averaging across a pause
const TAP_MIN_MS = 150;        // 400 bpm; faster than this is a double-hit, not a tempo
const TAP_MAX_MS = 3000;       // 20 bpm
export const BPM_MIN = 20, BPM_MAX = 300;

//: The feels. `subs` is how many clicks fall in one beat; `at` gives each click's position inside
//: the beat as a fraction. A swing feel is NOT a triplet: it sounds two clicks where a triplet
//: sounds three, with the second one late by the swing ratio. Both are offered because the review
//: showed the difference between them is precisely what the analysis cannot resolve on its own.
export const FEELS = {
  straight:    { label: "Straight (beats)",     at: [0] },
  eighths:     { label: "Eighths",              at: [0, 1 / 2] },
  sixteenths:  { label: "Sixteenths",           at: [0, 1 / 4, 1 / 2, 3 / 4] },
  triplet:     { label: "Triplets",             at: [0, 1 / 3, 2 / 3] },
  swing:       { label: "Swing (2:1)",          at: [0, 2 / 3] },
  shuffle:     { label: "Hard shuffle (3:1)",   at: [0, 3 / 4] },
  sixeight:    { label: "6/8 (two dotted)",     at: [0, 1 / 3, 2 / 3] },
};

//: Synthesised so the thing works with no assets on disk and no network. Each preset returns the
//: nodes for one hit; `accent` is 1 on a downbeat, 0.62 on other beats, 0.34 on a subdivision, so a
//: bar has shape without the offbeats disappearing under a piano.
const SOUNDS = {
  woodblock: { label: "Woodblock", make: (ctx, t, g, a, hz) => tone(ctx, t, g, a, hz * 2.4, "square", 0.028, 1800, 3.0) },
  click:     { label: "Click",     make: (ctx, t, g, a, hz) => noise(ctx, t, g, a, 0.010, hz * 6, 9.0) },
  rim:       { label: "Rim",       make: (ctx, t, g, a, hz) => noise(ctx, t, g, a, 0.022, hz * 4, 4.5) },
  cowbell:   { label: "Cowbell",   make: (ctx, t, g, a, hz) => bell(ctx, t, g, a, hz) },
  beep:      { label: "Beep",      make: (ctx, t, g, a, hz) => tone(ctx, t, g, a, hz * 2, "sine", 0.055, 4000, 1.0) },
  tick:      { label: "Tick-tock", make: (ctx, t, g, a, hz) => tone(ctx, t, g, a, hz * 1.6, "triangle", 0.035, 2600, 2.0) },
};
export const SOUND_NAMES = Object.keys(SOUNDS);
export const FEEL_NAMES = Object.keys(FEELS);

function env(ctx, t, gain, dur, curve) {
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(Math.max(0.0002, gain), t + 0.0012);   // 1.2 ms attack: a click, not a thud
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur * curve);
  return g;
}
function tone(ctx, t, gain, accent, hz, type, dur, lp, curve) {
  const o = ctx.createOscillator(); o.type = type; o.frequency.setValueAtTime(hz, t);
  const f = ctx.createBiquadFilter(); f.type = "lowpass"; f.frequency.setValueAtTime(lp, t);
  const g = env(ctx, t, gain * accent, dur, curve);
  o.connect(f); f.connect(g);
  o.start(t); o.stop(t + dur * curve + 0.02);
  return g;
}
function noiseBuffer(ctx) {
  if (ctx.__metroNoise) return ctx.__metroNoise;                 // one buffer per context, not per click
  const n = Math.floor(ctx.sampleRate * 0.2), b = ctx.createBuffer(1, n, ctx.sampleRate), d = b.getChannelData(0);
  let seed = 12345;
  for (let i = 0; i < n; i++) { seed = (seed * 1103515245 + 12345) & 0x7fffffff; d[i] = (seed / 0x3fffffff) - 1; }
  ctx.__metroNoise = b;                                          // deterministic: two runs sound identical
  return b;
}
function noise(ctx, t, gain, accent, dur, hz, curve) {
  const s = ctx.createBufferSource(); s.buffer = noiseBuffer(ctx);
  const f = ctx.createBiquadFilter(); f.type = "bandpass"; f.frequency.setValueAtTime(hz, t); f.Q.setValueAtTime(2.2, t);
  const g = env(ctx, t, gain * accent, dur, curve);
  s.connect(f); f.connect(g);
  s.start(t); s.stop(t + dur * curve + 0.02);
  return g;
}
function bell(ctx, t, gain, accent, hz) {
  const g = env(ctx, t, gain * accent, 0.16, 1.0);
  const f = ctx.createBiquadFilter(); f.type = "bandpass"; f.frequency.setValueAtTime(hz * 3.2, t); f.Q.setValueAtTime(3.5, t);
  for (const mul of [1.0, 1.4983]) {                             // the classic 808 inharmonic pair
    const o = ctx.createOscillator(); o.type = "square"; o.frequency.setValueAtTime(hz * 3.2 * mul, t);
    o.connect(f); o.start(t); o.stop(t + 0.18);
  }
  f.connect(g);
  return g;
}

export function createMetronome({ ctx, onClick = null, destination = null } = {}) {
  if (!ctx) throw new Error("createMetronome needs an AudioContext");
  const out = ctx.createGain();
  out.gain.value = 0.6;
  out.connect(destination || ctx.destination);

  let bpm = 100, meter = 4, feel = "straight", sound = "woodblock", running = false;
  let sample = null;                       // an AudioBuffer the player chose, or null for a preset
  let timer = null, nextBeat = 0, startCtx = 0, beatIndex = 0;
  let taps = [];
  //: The run's output latency, sampled once and then FROZEN. Measured 2026-09-27 in the browser
  //: pane: re-reading ctx.outputLatency per click put 72 ms of jitter into the reported beat times
  //: (interval_min exactly 500.0000 ms, interval_max 572.0000) because the device's own latency
  //: settles after the graph starts. For a reference grid a constant offset is harmless and
  //: auditable; jitter is not, and it is indistinguishable downstream from the player rushing.
  //: So: sample at start, keep updating only while it still reads 0 (a device that has not
  //: reported yet), freeze on the first real value, and carry it on every event so any consumer
  //: can undo it.
  let runLatency = 0, latencyFrozen = false;
  const scheduled = [];                    // every click this run has placed, newest last

  const spb = () => 60 / bpm;
  const at = () => (FEELS[feel] || FEELS.straight).at;

  //: Audio time -> page time, re-read every poll so a long take tracks drift instead of assuming
  //: one anchor holds. See header note 3.
  function toPage(audioSec) {
    let cT = ctx.currentTime, pT = performance.now();
    if (typeof ctx.getOutputTimestamp === "function") {
      try {
        const ts = ctx.getOutputTimestamp();
        if (ts && Number.isFinite(ts.contextTime) && Number.isFinite(ts.performanceTime)) {
          cT = ts.contextTime; pT = ts.performanceTime;
        }
      } catch { /* an unimplemented getOutputTimestamp must not stop the metronome */ }
    }
    return pT + (audioSec - cT) * 1000;
  }
  const latencySec = () => (Number(ctx.outputLatency) || 0) + (Number(ctx.baseLatency) || 0);

  function fire(when, accent, hz) {
    const gain = 1;
    if (sample) {
      const s = ctx.createBufferSource(); s.buffer = sample;
      const g = env(ctx, when, gain * accent, Math.min(0.5, sample.duration), 1.0);
      s.connect(g); g.connect(out); s.start(when);
      return;
    }
    const node = (SOUNDS[sound] || SOUNDS.woodblock).make(ctx, when, gain, accent, hz);
    node.connect(out);
  }

  function place(beatN, whenSec) {
    const subs = at();
    for (let i = 0; i < subs.length; i++) {
      const when = whenSec + subs[i] * spb();
      const isBeat = i === 0;
      const beatInBar = ((beatN % meter) + meter) % meter;
      const isDownbeat = isBeat && beatInBar === 0;
      const accent = isDownbeat ? 1 : isBeat ? 0.62 : 0.34;
      const hz = isDownbeat ? 440 : isBeat ? 330 : 262;
      fire(when, accent, hz);
      const audible = when + runLatency;
      const ev = {
        n: beatN + subs[i], bar: Math.floor(beatN / meter), beatInBar, sub: i, subs: subs.length,
        isBeat, isDownbeat, audio_ms: audible * 1000, page_ms: toPage(audible),
        bpm, latency_ms: runLatency * 1000,
      };
      scheduled.push(ev);
      if (scheduled.length > 20000) scheduled.splice(0, 10000);
      if (onClick) { try { onClick(ev); } catch { /* a listener must never stop the clock */ } }
    }
  }

  function poll() {
    if (!latencyFrozen) {
      const l = latencySec();
      if (l > 0) { runLatency = l; latencyFrozen = true; }
    }
    while (nextBeat < ctx.currentTime + LOOKAHEAD_S) {
      place(beatIndex, nextBeat);
      nextBeat += spb();
      beatIndex += 1;
    }
  }

  return {
    start() {
      if (running) return;
      if (ctx.state === "suspended") ctx.resume();
      running = true; beatIndex = 0; scheduled.length = 0;
      runLatency = latencySec(); latencyFrozen = runLatency > 0;
      startCtx = ctx.currentTime + 0.08;             // a beat's headroom so the first click is not late
      nextBeat = startCtx;
      poll();
      timer = setInterval(poll, POLL_MS);
      return this;
    },
    stop() {
      running = false;
      if (timer) clearInterval(timer);
      timer = null;
      return this;
    },
    //: Tap tempo. The median of the gaps, not the mean: one late tap in four should not move the
    //: tempo by a quarter of its error, and a drummer's taps are exactly where an outlier appears.
    tap(pageMs = performance.now()) {
      const t = Number(pageMs);
      if (!Number.isFinite(t)) return { bpm, taps: taps.length };
      if (taps.length && t - taps[taps.length - 1] > TAP_TIMEOUT_MS) taps = [];
      taps.push(t);
      if (taps.length > 8) taps.shift();
      const gaps = [];
      for (let i = 1; i < taps.length; i++) {
        const d = taps[i] - taps[i - 1];
        if (d >= TAP_MIN_MS && d <= TAP_MAX_MS) gaps.push(d);
      }
      if (gaps.length < 2) return { bpm, taps: taps.length, set: false };
      gaps.sort((a, b) => a - b);
      const mid = gaps.length % 2 ? gaps[(gaps.length - 1) / 2]
                                 : (gaps[gaps.length / 2 - 1] + gaps[gaps.length / 2]) / 2;
      this.setBpm(60000 / mid);
      return { bpm, taps: taps.length, set: true, gaps: gaps.length };
    },
    clearTaps() { taps = []; return this; },
    setBpm(x) {
      const v = Number(x);
      if (!Number.isFinite(v)) return bpm;
      bpm = Math.min(BPM_MAX, Math.max(BPM_MIN, v));
      return bpm;
    },
    setMeter(n) { const v = Math.round(Number(n)); if (v >= 1 && v <= 16) meter = v; return meter; },
    setFeel(name) { if (FEELS[name]) feel = name; return feel; },
    setSound(name) { if (SOUNDS[name]) { sound = name; sample = null; } return sound; },
    setVolume(v) {
      const x = Math.min(1, Math.max(0, Number(v)));
      if (Number.isFinite(x)) out.gain.setTargetAtTime(x, ctx.currentTime, 0.01);   // ramped: a step pops
      return x;
    },
    //: A player's own sample. Decoding can fail on a file the browser cannot read; that must
    //: surface, not leave the metronome silently on the previous preset.
    async loadSample(arrayBuffer, name = "custom") {
      const buf = await ctx.decodeAudioData(arrayBuffer.slice(0));
      sample = buf; sound = name;
      return { name, duration: buf.duration, channels: buf.numberOfChannels, rate: buf.sampleRate };
    },
    clearSample() { sample = null; sound = "woodblock"; return sound; },
    //: The beat times of this run, in page ms, AUDIBLE (latency included) -- the array
    //: score/index.js:102 wants. Subdivision clicks are excluded: they are not beats.
    beats() { return scheduled.filter((e) => e.isBeat).map((e) => e.page_ms); },
    clicks() { return scheduled.slice(); },
    state() {
      return { running, bpm, meter, feel, sound, custom: !!sample, volume: out.gain.value,
               latency_ms: (latencyFrozen ? runLatency : latencySec()) * 1000,
               latency_frozen: latencyFrozen, beats: scheduled.filter((e) => e.isBeat).length };
    },
    sounds: () => Object.entries(SOUNDS).map(([k, v]) => ({ name: k, label: v.label })),
    feels: () => Object.entries(FEELS).map(([k, v]) => ({ name: k, label: v.label, subs: v.at.length })),
  };
}
