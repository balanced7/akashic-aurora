// Node tests for the KeyLab page client (arsenal/web/lib/keylab-client.js). Zero dependencies:
//   node tests/keylab_client.test.mjs
//
// What they hold: both control maps (DAW mode: faders CC 105-113 absolute, knobs relative; MIDI mode: faders 73, 75,
// 79 ... and knobs 74, 71, 76 ... absolute), the VJ engine's events normalised the same way as raw Web MIDI, the
// relative/absolute learner, the engine-or-Web-MIDI source switch (never a permission prompt nobody asked for), and
// the binder: fader pickup, fine knobs, learn on move and on touch, persistence, snapshots on pads, scenes on pads,
// the chord root on hue, and smoothing. A fake clock drives every timer; nothing touches a device.
import {
  PAD_NOTE, SURFACE, controlLabel, createBinder, createKeyLabClient, createKindLearner, fifthsTurn, nameChord, resolveCC,
} from "../arsenal/web/lib/keylab-client.js";

let fail = 0, pass = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? " -- " + detail : ""}`);
}
const near = (a, b, eps = 1e-6) => typeof a === "number" && Math.abs(a - b) <= eps;

// ------------------------------------------------------------------------------------------- a fake clock --
function fakeClock() {
  let t = 1000, seq = 0;
  const timers = new Map();
  const frames = [];
  return {
    now: () => t,
    setTimeout: (fn, ms) => { const id = ++seq; timers.set(id, { at: t + Math.max(0, ms || 0), fn }); return id; },
    clearTimeout: (id) => { timers.delete(id); },
    raf: (fn) => { frames.push(fn); },
    advance(ms, frameMs = 16) {
      const end = t + ms;
      while (t < end) {
        t = Math.min(end, t + frameMs);
        for (const [id, x] of [...timers].sort((a, b) => a[1].at - b[1].at)) if (x.at <= t) { timers.delete(id); x.fn(); }
        const run = frames.splice(0);
        for (const fn of run) fn(t);
      }
    },
    async settle() { for (let i = 0; i < 5; i++) await Promise.resolve(); },
  };
}

function memoryStorage() {
  const m = new Map();
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k), m };
}

// ------------------------------------------------------------------------------------------- the maps --
{
  const r = (port, cc) => resolveCC(port, cc);
  check("daw fader 1 = CC 105, absolute", r("daw", 105).control === "fader1" && r("daw", 105).prior === "abs");
  check("daw fader 9 = CC 113", r("daw", 113).control === "fader9");
  check("daw knob 1 = CC 91, relative", r("daw", 91).control === "knob1" && r("daw", 91).prior === "rel");
  check("daw knob 3 = CC 94 (93 skipped)", r("daw", 94).control === "knob3");
  check("daw knob 9 = CC 104", r("daw", 104).control === "knob9");
  check("daw fader 5 touch = CC 33 (32 skipped)", r("daw", 33).control === "fader5" && r("daw", 33).role === "touch");
  check("daw knob 4 touch = CC 11 on the DAW port", r("daw", 11).control === "knob4" && r("daw", 11).role === "touch");
  check("midi CC 11 = expression", r("midi", 11).control === "expression");
  check("midi fader 1 = CC 73", r("midi", 73).control === "fader1" && r("midi", 73).prior === "abs");
  check("midi fader 4 = CC 72", r("midi", 72).control === "fader4");
  check("midi fader 9 = CC 85", r("midi", 85).control === "fader9");
  check("midi knob 5 = CC 93, absolute", r("midi", 93).control === "knob5" && r("midi", 93).prior === "abs");
  check("midi knob 9 = CC 17", r("midi", 17).control === "knob9");
  check("dial: daw 116 relative, midi 114", r("daw", 116).control === "dial" && r("midi", 114).control === "dial");
  check("transport: daw 21 = play, 23 = tap", r("daw", 21).control === "play" && r("daw", 23).control === "tap");
  check("screen buttons: daw 45 = screen1, midi 60 = screen5", r("daw", 45).control === "screen1" && r("midi", 60).control === "screen5");
  check("port-less 107 = fader 3", r(null, 107).control === "fader3");
  check("port-less 75 = midi fader 2", r(null, 75).control === "fader2");
  check("an unknown CC is still a learnable control", r("midi", 20).control === "cc20.midi" && r("midi", 20).role === "cc");
  // the two maps never give one CC two meanings on a port
  for (const port of ["daw", "midi"]) {
    const s = SURFACE[port];
    const all = [...s.faders, ...s.knobs, ...s.faderTouch, ...s.knobTouch, s.dial, s.dialClick, ...Object.keys(s.buttons).map(Number)];
    check(`${port} map has no duplicate CCs`, new Set(all).size === all.length, all.join(","));
  }
  check("labels", controlLabel("fader3") === "Fader 3" && controlLabel("knob9") === "Knob 9" && controlLabel("cc20.midi") === "CC 20 (midi)");
  check("pad notes: pad 1 = 44, pad 9 = 36", PAD_NOTE[1] === 44 && PAD_NOTE[9] === 36);
}

// ------------------------------------------------------------------------------------------- chords --
{
  const n = (m) => nameChord(m);
  check("C major", n([60, 64, 67])?.name === "C" && n([60, 64, 67]).root === 0);
  check("A minor", n([57, 60, 64])?.name === "Am");
  check("G7", n([55, 59, 62, 65])?.name === "G7");
  check("Dbmaj7", n([61, 65, 68, 72])?.name === "Dbmaj7");
  check("C/E first inversion keeps root C", n([64, 67, 72])?.root === 0, JSON.stringify(n([64, 67, 72])));
  check("Cmaj7 without its fifth", n([60, 64, 71])?.name === "Cmaj7", JSON.stringify(n([60, 64, 71])));
  check("one note is not a chord", n([60]) === null);
  check("fifths: C = 0, G = 1/12, F = 11/12", fifthsTurn(0) === 0 && near(fifthsTurn(7), 1 / 12) && near(fifthsTurn(5), 11 / 12));
}

// ------------------------------------------------------------------------------------------- kind learner --
{
  const L = createKindLearner();
  let k;
  for (let i = 0; i < 4; i++) k = L.feed("x", null, 65, 1000 + i * 10).kind;
  check("an unknown control repeating 65 is learned relative", k === "rel");
  const M = createKindLearner();
  for (const v of [0, 20, 40, 60, 80, 100, 127]) k = M.feed("y", null, v, 1000).kind;
  check("a control sweeping 0..127 stays absolute", k === "abs");
  const N = createKindLearner();
  check("a known relative knob starts relative", N.feed("z", "rel", 66, 1000).kind === "rel");
  const P = createKindLearner();
  check("a known fader at mid travel stays absolute", P.feed("w", "abs", 64, 1000).kind === "abs" && P.feed("w", "abs", 64, 1001).kind === "abs");
}

// ------------------------------------------------------------------------------------------- engine events --
{
  const clk = fakeClock();
  const kl = createKeyLabClient({ EventSource: null, requestMIDIAccess: null, now: clk.now, setTimeout: clk.setTimeout, clearTimeout: clk.clearTimeout, fallback: "off" });
  const got = [];
  kl.on("*", (e) => got.push(e));
  kl.feedEngine({ t: "ctl", id: "cc107", kind: "abs", value: 0.5, delta: 3, port: "daw", ch: 1 });
  let c = got.find((e) => e.type === "control");
  check("engine fader 3", c && c.control === "fader3" && c.kind === "abs" && c.value === 0.5 && c.raw === 64);
  got.length = 0;
  kl.feedEngine({ t: "ctl", id: "cc92", kind: "rel", value: 0.52, delta: 3, port: "daw", ch: 1 });
  c = got.find((e) => e.type === "control");
  check("engine knob 2 relative: delta 3", c && c.control === "knob2" && c.kind === "rel" && c.delta === 3 && c.value === null);
  got.length = 0;
  kl.feedEngine({ t: "ctl", id: "cc29", kind: "abs", value: 1, delta: 127, port: "daw", ch: 1 });
  check("engine fader 2 touch", got[0]?.type === "touch" && got[0].control === "fader2" && got[0].on === true);
  got.length = 0;
  kl.feedEngine({ t: "ctl", id: "cc73", kind: "abs", value: 1, delta: 0, port: "midi", ch: 1 });
  check("engine MIDI-mode fader 1", got[0]?.control === "fader1");
  got.length = 0;
  kl.feedEngine({ t: "ctl", id: "pb", kind: "abs", value: 0.75, delta: 100, port: "midi", ch: 1 });
  check("engine pitch wheel", got[0]?.control === "pitch" && got[0].value === 0.75);
  got.length = 0;
  kl.feedEngine({ t: "ctl", id: "pad3_at", kind: "abs", value: 0.4, delta: 0, port: "daw", ch: 10 });
  check("engine pad pressure", got[0]?.type === "pressure" && got[0].pad === 3);
  got.length = 0;
  kl.feedEngine({ t: "pad", pad: 7, vel: 0.8, on: true, src: "bank" });
  check("engine pad", got[0]?.type === "pad" && got[0].pad === 7 && got[0].vel === 0.8);
  got.length = 0;
  kl.feedEngine({ t: "chord", src: "keys", name: "Dbmaj7", root: 1, quality: "maj7", pcs: [0, 1, 5, 8], changed: true });
  check("engine chord", got[0]?.type === "chord" && got[0].root === 1 && got[0].name === "Dbmaj7");
  got.length = 0;
  const beats = [];
  kl.onBeat((b) => beats.push(b));
  kl.feedEngine({ t: "beat", due_ms: 240, bpm: 128, conf: 0.9, n: 17, on_beat: 0.8 });
  check("beat-ahead arrives at once with its landing time", got.some((e) => e.type === "beat-ahead" && e.at === clk.now() + 240));
  clk.advance(200);
  check("the beat hook waits for the beat", beats.length === 0);
  clk.advance(60);
  check("the beat hook fires on the beat", beats.length === 1 && beats[0].bpm === 128 && beats[0].n === 17);
}

// ------------------------------------------------------------------------------------------- Web MIDI decode --
{
  const clk = fakeClock();
  const kl = createKeyLabClient({ EventSource: null, requestMIDIAccess: null, now: clk.now, setTimeout: clk.setTimeout, clearTimeout: clk.clearTimeout, fallback: "off" });
  const got = [];
  kl.on("*", (e) => got.push(e));
  kl.feedMidi("daw", [0xb0, 105, 100], 0);
  check("raw DAW fader 1", got[0]?.control === "fader1" && got[0].kind === "abs" && near(got[0].value, 100 / 127));
  got.length = 0;
  kl.feedMidi("daw", [0xb0, 91, 66], 0); kl.feedMidi("daw", [0xb0, 91, 66], 5);
  check("raw DAW knob 1 is relative: +2", got.length === 2 && got.every((e) => e.control === "knob1" && e.kind === "rel" && e.delta === 2));
  got.length = 0;
  kl.feedMidi("daw", [0xb0, 91, 61], 10);
  check("raw DAW knob 1 counter-clockwise: -3", got[0]?.delta === -3);
  got.length = 0;
  kl.feedMidi("midi", [0xb0, 74, 100], 0);
  check("raw MIDI-mode knob 1 is absolute", got[0]?.control === "knob1" && got[0].kind === "abs" && near(got[0].value, 100 / 127));
  got.length = 0;
  kl.feedMidi("daw", [0x99, 2, 100], 1000);
  check("raw DAW pad: note 2 = pad 3", got[0]?.type === "pad" && got[0].pad === 3 && got[0].src === "daw");
  got.length = 0;
  kl.feedMidi("midi", [0x99, 44, 90], 2000);
  kl.feedMidi("daw", [0x99, 0, 90], 2010);
  check("a pad seen on both inputs within 40 ms counts once", got.filter((e) => e.type === "pad").length === 1 && got[0].pad === 1);
  got.length = 0;
  kl.feedMidi("midi", [0x99, 48 + 8, 90], 3000);
  check("bank B note 56 = pad 1 of bank B", got[0]?.pad === 1 && got[0].bank === "B", JSON.stringify(got[0]));
  got.length = 0;
  kl.feedMidi("daw", [0xb0, 30, 127], 0);
  check("raw DAW fader 3 touch", got[0]?.type === "touch" && got[0].control === "fader3" && got[0].on);
  got.length = 0;
  for (const n of [60, 64, 67]) kl.feedMidi("midi", [0x90, n, 80], clk.now());
  check("keys arrive as notes", got.filter((e) => e.type === "note").length === 3);
  clk.advance(50);
  const ch = got.find((e) => e.type === "chord");
  check("keys settle into one chord: C", ch && ch.name === "C" && ch.root === 0 && got.filter((e) => e.type === "chord").length === 1);
  got.length = 0;
  kl.feedMidi("midi", [0xb0, 64, 127], 0);
  for (const n of [60, 64, 67]) kl.feedMidi("midi", [0x80, n, 0], clk.now());
  clk.advance(50);
  check("sustain: released keys still sound, no new chord", got.some((e) => e.type === "pedal" && e.on) && !got.some((e) => e.type === "chord"));
  got.length = 0;
  kl.feedMidi("midi", [0x90, 69, 80], clk.now());   // A over the held C E G = C6 or Am7/C
  clk.advance(50);
  check("a sustained chord plus a new key is renamed", got.some((e) => e.type === "chord"), JSON.stringify(got.filter((e) => e.type === "chord")));
}

// ------------------------------------------------------------------------------------------- source switching --
function fakeES() {
  const made = [];
  class ES {
    constructor(url) { this.url = url; this.readyState = 0; made.push(this); }
    close() { this.readyState = 2; this.closed = true; }
    open() { this.readyState = 1; this.onopen && this.onopen(); }
    send(obj) { this.onmessage && this.onmessage({ data: JSON.stringify(obj) }); }
    fail() { this.onerror && this.onerror(); }
  }
  return { ES, made };
}
function fakeMidi(names) {
  const inputs = new Map(names.map((name, i) => [String(i), { name, state: "connected", onmidimessage: null }]));
  let asked = 0;
  return { access: { inputs, onstatechange: null }, request: async () => { asked++; return { inputs, onstatechange: null }; }, asked: () => asked, inputs };
}
{
  const clk = fakeClock();
  const { ES, made } = fakeES();
  const midi = fakeMidi(["KeyLab 88 mk3 MIDI", "KeyLab 88 mk3 DAW", "Some Other Synth"]);
  const kl = createKeyLabClient({ EventSource: ES, requestMIDIAccess: midi.request, permissions: { query: async () => ({ state: "granted" }) },
    now: clk.now, setTimeout: clk.setTimeout, clearTimeout: clk.clearTimeout, url: "http://127.0.0.1:8999/api/events" });
  const sources = [];
  kl.on("source", (e) => sources.push(e.source));
  kl.start();
  check("the engine is tried first", made.length === 1 && made[0].url === "http://127.0.0.1:8999/api/events");
  clk.advance(1600);
  await clk.settle();
  check("no engine after 1.5 s: Web MIDI opens (permission already granted)", midi.asked() === 1 && kl.source === "webmidi", `${kl.source} asked=${midi.asked()}`);
  const ins = [...midi.inputs.values()];
  check("both KeyLab inputs are opened, the other synth is not", !!ins[0].onmidimessage && !!ins[1].onmidimessage && !ins[2].onmidimessage);
  const got = [];
  kl.on("control", (e) => got.push(e));
  ins[1].onmidimessage({ data: [0xb0, 107, 90], timeStamp: 5 });
  check("a message on the DAW input is decoded with the DAW map", got[0]?.control === "fader3" && got[0].port === "daw");
  check("the silent engine's stream is closed (no retry noise every 3 s)", made[0].closed === true);
  clk.advance(8100);
  check("... and the engine is asked again after retryMs", made.length === 2 && !made[1].closed);
  made[1].open();
  check("the engine arrives: it becomes the source and Web MIDI lets go", kl.source === "engine" && !ins[0].onmidimessage && !ins[1].onmidimessage);
  made[1].send({ t: "ctl", id: "cc105", kind: "abs", value: 0.25, delta: 0, port: "daw", ch: 1 });
  check("engine events flow", got.length === 2 && got[1].control === "fader1");
  made[1].fail();
  clk.advance(3000);
  await clk.settle();
  check("the engine goes away: back to Web MIDI after the grace period", kl.source === "webmidi" && !!ins[0].onmidimessage, kl.source);
  check("sources in order", sources.join(",") === "webmidi,engine,webmidi", sources.join(","));
  kl.stop();
}
{
  const clk = fakeClock();
  const { ES } = fakeES();
  const midi = fakeMidi(["KeyLab 88 mk3 MIDI", "KeyLab 88 mk3 DAW"]);
  const kl = createKeyLabClient({ EventSource: ES, requestMIDIAccess: midi.request, permissions: { query: async () => ({ state: "prompt" }) },
    now: clk.now, setTimeout: clk.setTimeout, clearTimeout: clk.clearTimeout });
  kl.start();
  clk.advance(1600);
  await clk.settle();
  check("permission not yet given: no prompt is popped, the page is told", midi.asked() === 0 && kl.status().midi === "needs-permission" && kl.source === "none");
  await kl.connectMidi();
  check("the page's button opens Web MIDI", midi.asked() === 1 && kl.source === "webmidi");
  kl.stop();
}

// ------------------------------------------------------------------------------------------- the screen hook --
{
  const clk = fakeClock();
  const { ES, made } = fakeES();
  const calls = [];
  let answer = 200;
  const fetchFn = async (url, init) => { calls.push({ url, body: JSON.parse(init.body) }); return { ok: answer === 200, status: answer }; };
  const kl = createKeyLabClient({ EventSource: ES, requestMIDIAccess: null, fetch: fetchFn, now: clk.now, setTimeout: clk.setTimeout,
    clearTimeout: clk.clearTimeout, url: "http://127.0.0.1:8999/api/events", fallback: "off" });
  check("no screen request while the engine is not up", kl.postScreen({ screen: "fader", name: "x", value: "1", level: 1 }) === false);
  kl.start(); made[0].open();
  kl.postScreen({ screen: "fader", name: "flow", value: "10%", level: 13 });
  kl.postScreen({ screen: "fader", name: "flow", value: "20%", level: 25 });
  kl.postScreen({ screen: "knob", name: "sphere → cube", value: "84°", level: 300 });
  clk.advance(100); await clk.settle();
  check("screen: three asks inside 80 ms are one request, the latest", calls.length === 1 && calls[0].body.value === "84 deg" && calls[0].body.screen === "knob", JSON.stringify(calls));
  check("screen: the route is the engine's /api/screen", calls[0].url === "http://127.0.0.1:8999/api/screen");
  check("screen: text is plain ASCII and the bar is clamped to 0..127", calls[0].body.name === "sphere -> cube" && calls[0].body.level === 127, JSON.stringify(calls[0].body));
  answer = 404;
  kl.postScreen({ screen: "fader", name: "a", value: "1", level: 1 });
  clk.advance(100); await clk.settle();
  check("screen: an engine without the route answers 404 and the status says so", kl.status().screen === "unsupported");
  const n = calls.length;
  check("screen: after a 404 the client stops asking for a minute", kl.postScreen({ screen: "fader", name: "b", value: "2", level: 2 }) === false);
  clk.advance(61_000, 1000); await clk.settle();
  answer = 200;
  kl.postScreen({ screen: "fader", name: "c", value: "3", level: 3 });
  clk.advance(100); await clk.settle();
  check("screen: and asks again after it", calls.length === n + 1);
  kl.stop();
}

// ------------------------------------------------------------------------------------------- the binder --
function fakeHost() {
  const values = { k1: 0.4, k2: 0.6, k3: 0.5, hue: 0, intensity: 0.8 };
  const scenes = [{ id: "a", label: "Alpha", colour: "#ff00ff" }, { id: "b", label: "Beta" }, { id: "c", label: "Gamma" }];
  let scene = "a";
  const sets = [];
  const host = {
    params: () => [
      { id: "k1", label: "zoom" }, { id: "k2", label: "spin" }, { id: "k3", label: "glow" },
      { id: "hue", label: "Hue", min: 0, max: 360, unit: "deg", step: 1, role: "hue" },
      { id: "intensity", label: "Intensity", role: "master", step: 0.01 },
    ],
    get: (id) => values[id],
    set: (id, v) => { values[id] = v; sets.push([id, v]); },
    scenes: () => scenes, scene: () => scene, selectScene: (id) => { scene = id; return true; },
    pulses: [], pulse(v) { this.pulses.push(v); },
  };
  return { host, values, sets, get scene() { return scene; } };
}
{
  const clk = fakeClock();
  const kl = createKeyLabClient({ EventSource: null, requestMIDIAccess: null, now: clk.now, setTimeout: clk.setTimeout, clearTimeout: clk.clearTimeout, fallback: "off" });
  const H = fakeHost();
  const storage = memoryStorage();
  const b = createBinder(kl, H.host, { namespace: "t", storage, now: clk.now, raf: clk.raf, setTimeout: clk.setTimeout, clearTimeout: clk.clearTimeout, options: { smoothMs: 0 } });
  const fader = (n, v) => kl.feedEngine({ t: "ctl", id: `cc${104 + n}`, kind: "abs", value: v, delta: 0, port: "daw", ch: 1 });
  const knob = (n, d) => kl.feedEngine({ t: "ctl", id: `cc${SURFACE.daw.knobs[n - 1]}`, kind: "rel", value: 0.5, delta: d, port: "daw", ch: 1 });
  const readouts = [];
  b.on("readout", (r) => readouts.push(r));

  check("desk layout: fader 1 drives the first parameter", b.bindingFor("fader1")?.param === "k1" && b.bindingFor("fader1").how === "desk");
  check("desk layout: fader 9 = master, knob 9 = hue", b.bindingFor("fader9")?.param === "intensity" && b.bindingFor("knob9")?.param === "hue");
  check("desk layout: knob 2 is a fine trim of the second parameter", b.bindingFor("knob2")?.param === "k2" && b.bindingFor("knob2").fine);

  fader(1, 0.9); clk.advance(20);
  check("pickup: a fader far above the value does not move it", H.values.k1 === 0.4);
  check("pickup: the readout says which way to go", readouts.at(-1)?.pending?.dir === "down" && near(readouts.at(-1).pending.want, 0.4));
  fader(1, 0.6); clk.advance(20);
  check("pickup: still above, still not caught", H.values.k1 === 0.4);
  fader(1, 0.3); clk.advance(20);
  check("pickup: the fader passes the value and takes over", near(H.values.k1, 0.3), String(H.values.k1));
  fader(1, 0.8); clk.advance(20);
  check("pickup: once caught it follows", near(H.values.k1, 0.8));
  knob(1, -100); clk.advance(20);
  check("a fine knob trims 100 ticks = 100/384 of the range", near(H.values.k1, 0.8 - 100 / 384, 1e-9), String(H.values.k1));
  knob(1, -150); clk.advance(20);
  fader(1, 0.85); clk.advance(20);
  check("a knob moved the value away: the fader let go of it", near(H.values.k1, 0.8 - 250 / 384, 1e-9), String(H.values.k1));
  fader(1, 0.12); clk.advance(20);
  check("... and catches it again on the way past", near(H.values.k1, 0.12));

  // learn on move
  b.learn("k3");
  check("learn is armed", b.learning === "k3");
  fader(5, 0.05); clk.advance(20);
  check("the next control binds and does not fire", b.bindingFor("fader5")?.param === "k3" && b.bindingFor("fader5").how === "learned" && H.values.k3 === 0.5);
  check("learned bindings persist", JSON.parse(storage.getItem("arsenal.keylab.bindings.v1:t")).bindings.fader5 === "k3");
  fader(5, 0.52); clk.advance(20);
  check("a learned fader needs pickup too", near(H.values.k3, 0.52));
  // learn on touch
  b.learn("k2");
  kl.feedEngine({ t: "ctl", id: "cc14", kind: "abs", value: 1, delta: 0, port: "daw", ch: 1 });   // knob 7 touch
  check("touch binds without moving anything", b.bindingFor("knob7")?.param === "k2" && H.values.k2 === 0.6);
  // a second fader learned to the same param replaces the first
  b.learn("k3"); fader(6, 0.5); clk.advance(20);
  check("one learned fader per parameter", b.bindingFor("fader6")?.param === "k3" && b.bindingFor("fader5")?.how !== "learned");
  // a fresh binder reads the bindings back
  const b2 = createBinder(kl, H.host, { namespace: "t", storage, now: clk.now, raf: clk.raf, options: { smoothMs: 0 } });
  check("bindings survive a reload", b2.bindingFor("fader6")?.param === "k3" && b2.bindingFor("knob7")?.param === "k2");
  b2.destroy();

  // chord root on hue (around the circle of fifths)
  kl.feedEngine({ t: "chord", src: "keys", name: "G", root: 7, quality: "maj", pcs: [2, 7, 11] });
  clk.advance(3000);
  check("chord G puts hue at one fifth = 30 degrees", near(H.values.hue, 30), String(H.values.hue));
  b.setOption("chordHue", false);
  kl.feedEngine({ t: "chord", src: "keys", name: "D", root: 2, quality: "maj", pcs: [2, 6, 9] });
  clk.advance(3000);
  check("chord to hue can be switched off", near(H.values.hue, 30));
  b.setOption("chordHue", true);

  // scenes on pads 1-8, a pulse with the velocity
  kl.feedEngine({ t: "pad", pad: 2, vel: 0.7, on: true, src: "daw" });
  check("pad 2 selects the second scene", H.scene === "b" && H.host.pulses.at(-1) === 0.7);
  kl.feedEngine({ t: "ctl", id: "cc116", kind: "rel", value: 0.5, delta: 1, port: "daw", ch: 1 });
  check("the dial steps to the next scene", H.scene === "c");
  kl.feedEngine({ t: "ctl", id: "cc25", kind: "abs", value: 1, delta: 0, port: "daw", ch: 1 });
  check("rewind steps back", H.scene === "b");

  // snapshots on pads 9-12: hold stores, tap recalls (with a glide)
  H.values.k1 = 0.25; b.notifyExternal("k1");
  kl.feedEngine({ t: "pad", pad: 9, vel: 0.5, on: true });
  clk.advance(700);
  kl.feedEngine({ t: "pad", pad: 9, vel: 0, on: false });
  check("holding pad 9 stores snapshot A", b.hasSnapshot(1));
  H.values.k1 = 0.9; b.notifyExternal("k1");
  b.setOption("smoothMs", 0);
  kl.feedEngine({ t: "pad", pad: 9, vel: 0.5, on: true });
  clk.advance(100);
  kl.feedEngine({ t: "pad", pad: 9, vel: 0, on: false });
  clk.advance(40);
  check("tapping pad 9 starts the glide back", H.values.k1 < 0.9 && H.values.k1 > 0.25, String(H.values.k1));
  clk.advance(3000);
  check("... and lands on the snapshot", near(H.values.k1, 0.25, 1e-3), String(H.values.k1));
  check("snapshots persist per scene", !!JSON.parse(storage.getItem("arsenal.keylab.snapshots.v1:t")).b["1"]);
  kl.feedEngine({ t: "pad", pad: 10, vel: 0.5, on: true });
  kl.feedEngine({ t: "pad", pad: 10, vel: 0, on: false });
  check("an empty snapshot says how to fill it", /hold the pad/.test(readouts.at(-1)?.label || ""));
  check("pad colours: 12, the current scene bright", b.padColors().length === 12 && b.padColors()[1] !== "#000000");
  b.destroy();
}
// smoothing with a real time constant
{
  const clk = fakeClock();
  const kl = createKeyLabClient({ EventSource: null, requestMIDIAccess: null, now: clk.now, setTimeout: clk.setTimeout, clearTimeout: clk.clearTimeout, fallback: "off" });
  const H = fakeHost();
  const b = createBinder(kl, H.host, { namespace: "s", storage: null, now: clk.now, raf: clk.raf, options: { smoothMs: 80 } });
  kl.feedEngine({ t: "ctl", id: "cc105", kind: "abs", value: 0.4, delta: 0, port: "daw", ch: 1 });   // caught at once
  kl.feedEngine({ t: "ctl", id: "cc105", kind: "abs", value: 1.0, delta: 0, port: "daw", ch: 1 });
  clk.advance(16);
  const first = H.values.k1;
  check("smoothing: the first frame moves part of the way", first > 0.4 && first < 0.7, String(first));
  clk.advance(1000);
  check("smoothing: it arrives", near(H.values.k1, 1, 1e-6), String(H.values.k1));
  check("smoothing stops asking for frames once it arrives", (() => { const n = H.sets.length; clk.advance(200); return H.sets.length === n; })());
  // hue wraps the short way round: 350 -> 10 goes up through 360, never down through 180
  H.values.hue = 350;
  b.setValue("hue", 10, { tauMs: 80 });
  const seen = [];
  for (let i = 0; i < 40; i++) { clk.advance(16); seen.push(H.values.hue); }
  check("hue glides the short way round", seen.every((h) => h >= 340 || h <= 10.0001) && near(seen.at(-1), 10, 1e-3), seen.slice(0, 6).map((x) => x.toFixed(1)).join(" "));
  b.destroy();
}

console.log(`keylab client: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
