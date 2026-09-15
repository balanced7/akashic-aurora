import { createClaudeVoice, createCuePlayer } from "./cues.js";
import Theory from "./replay-theory.js";

// A standalone listener: no MIDI access, cue stream, practice logger or shared-tab voice arbitration.
const $ = (id) => document.getElementById(id);
if (new URLSearchParams(location.search).get("embed") === "1") document.body.classList.add("embedded");
const controls = [$("play"), $("stop"), $("speed"), $("seek")];
let clip, voice, player, playing = false, offset = 0, began = 0, speed = 1, generation = 0, frame = null;
let chords = [], hovered = null, selected = null, previewed = null, chordTimer = null;
const pretty = (text) => String(text).replace(/#/g, "♯").replace(/b/g, "♭");
const noteName = (midi) => `${["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"][midi % 12]}${Math.floor(midi / 12) - 1}`;
const clock = (ms) => `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, "0")}`;
const position = () => Math.min(clip?.seconds * 1000 || 0, offset + (playing ? (performance.now() - began) * speed : 0));

export function sliceCue(cue, offsetMs, rate) {
  const steps = cue.steps.flatMap((s) => {
    const end = s.at_ms + s.hold_ms;
    if (end <= offsetMs) return [];
    const start = Math.max(s.at_ms, offsetMs);
    return [{ ...s, at_ms: Math.round((start - offsetMs) / rate), hold_ms: Math.max(1, Math.round((end - start) / rate)) }];
  });
  return { ...cue, steps };
}

function pause(reset = false) {
  ++generation;
  clearTimeout(chordTimer); chordTimer = null;
  if (frame !== null) cancelAnimationFrame(frame);
  frame = null;
  offset = reset ? 0 : position();
  playing = false;
  player?.clear();
  voice?.allOff();
  $("play").textContent = "Play passage";
  $("status").textContent = reset ? "Ready to listen again." : "Paused.";
  draw();
}

async function unlockVoice() {
  if (!voice) {
    voice = createClaudeVoice({ exclusive: false, unlockTarget: null, polyphony: 128,
                               lowLift: 0, volume: 0.65, timbre: "keys" });
    player = createCuePlayer({ voice, startDelayMs: 0, bassDouble: false, onError: fail });
  }
  await voice.unlock();
  if (voice.context?.state !== "running") throw new Error("Audio is paused by the browser. Click again to listen.");
}

async function play() {
  if (!clip) return;
  if (playing) { pause(); return; }
  const request = ++generation;
  try {
    await unlockVoice();
    if (request !== generation) return;
    clearTimeout(chordTimer); chordTimer = null;
    player.clear(); voice.allOff(); selected = null;
    if (offset >= clip.seconds * 1000 - 10) offset = 0;
    const cue = sliceCue(clip.cue, offset, speed);
    began = performance.now();
    playing = true;
    if (cue.steps.length) player.handle(cue);
    $("play").textContent = "Pause";
    $("status").textContent = speed === 1 ? "Playing at your original pace." : `Playing at ${speed}× speed; pitch stays the same.`;
    tick();
  } catch (error) { fail(error); }
}

async function audition(chord) {
  pause();
  selected = chord;
  $("status").classList.remove("error");
  const request = generation;
  draw();
  try {
    await unlockVoice();
    if (request !== generation) return;
    player.handle({ type: "sequence", source: "replay", label: chord.label,
      steps: chord.notes.map(note => ({ type: "play", notes: [note], at_ms: 0,
        hold_ms: 1800, arpeggio_ms: 0, velocity: chord.velocities[note] || 75 })) });
    $("status").textContent = `Sounding ${chord.label}. The passage is paused where you left it.`;
    chordTimer = setTimeout(() => {
      chordTimer = null;
      if (request === generation) $("status").textContent = `Heard ${chord.label}. Press Play passage to continue.`;
    }, 1900);
  } catch (error) { fail(error); }
}

function renderChords() {
  chords = (clip.chords || []).map((chord, index) => {
    const info = Theory.detect(chord.notes);
    const label = pretty(info?.name || chord.notes.map(noteName).join(" · "));
    return { ...chord, index, info, label };
  });
  $("chords").replaceChildren();
  for (const chord of chords) {
    const button = document.createElement("button");
    button.className = "chord";
    button.dataset.index = chord.index;
    button.setAttribute("aria-label", `Play ${chord.label} at ${clock(clip.start_ms + chord.start_ms)}`);
    const time = document.createElement("small"), name = document.createElement("span");
    time.textContent = clock(clip.start_ms + chord.start_ms); name.textContent = chord.label;
    button.append(time, name);
    button.addEventListener("pointerenter", () => { hovered = chord; draw(); });
    button.addEventListener("pointerleave", () => { hovered = null; draw(); });
    button.addEventListener("focus", () => { hovered = chord; draw(); });
    button.addEventListener("blur", () => { hovered = null; draw(); });
    button.addEventListener("click", () => void audition(chord));
    chord.button = button;
    $("chords").append(button);
  }
  if (!chords.length) $("chords").textContent = "No sustained harmony in this short passage.";
}

function showChord(chord) {
  if (previewed === chord) return;
  previewed = chord;
  $("chord-keys").replaceChildren();
  $("chord-name").textContent = chord?.label || "Between chords";
  $("chord-time").textContent = chord ? `${clock(clip.start_ms + chord.start_ms)}–${clock(clip.start_ms + chord.end_ms)}` : "";
  const names = chord?.info?.notes?.map(n => `${pretty(n.name)}${n.octave}`) || chord?.notes.map(noteName) || [];
  $("chord-notes").textContent = names.join(" · ") || "Hover a chord to see its notes; click to hear it.";
  $("chord-detail").textContent = chord ? (chord.texture === "line" || chord.texture === "bass line"
    ? "Moving notes in this window; click to hear them together."
    : "Harmony reading from ringing notes, including sustain. Click to hear the voicing together.") : "";
  if (!chord) return;
  const low = Math.floor(Math.min(...chord.notes) / 12) * 12, high = Math.ceil((Math.max(...chord.notes) + 1) / 12) * 12 - 1;
  const whites = [];
  for (let m = low; m <= high; m++) if (![1, 3, 6, 8, 10].includes(m % 12)) whites.push(m);
  let whiteCount = 0;
  for (let m = low; m <= high; m++) {
    const black = [1, 3, 6, 8, 10].includes(m % 12), key = document.createElement("span");
    key.className = `key ${black ? "black" : "white"}${chord.notes.includes(m) ? " lit" : ""}`;
    key.style.left = `${(black ? whiteCount - .31 : whiteCount) / whites.length * 100}%`;
    key.style.width = `${(black ? .62 : 1) / whites.length * 100}%`;
    key.title = noteName(m);
    key.dataset.midi = m;
    if (!black) whiteCount++;
    $("chord-keys").append(key);
  }
  $("chord-keys").setAttribute("aria-label", `${chord.label}: ${names.join(", ")}`);
}

function fail(error) {
  pause();
  $("status").textContent = error.message || String(error);
  $("status").classList.add("error");
}

function draw() {
  if (!clip) return;
  const canvas = $("roll"), rect = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
  const width = Math.max(1, Math.round(rect.width * dpr)), height = Math.max(1, Math.round(rect.height * dpr));
  if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const w = rect.width, h = rect.height, duration = clip.seconds * 1000, t = position();
  const current = chords.find(c => c.start_ms <= t && c.end_ms > t);
  const preview = hovered || selected || current || (!playing && t === 0 ? chords[0] : null);
  for (const chord of chords) {
    chord.button.classList.toggle("current", chord === current);
    chord.button.classList.toggle("selected", chord === selected);
    if (chord === current) chord.button.setAttribute("aria-current", "true");
    else chord.button.removeAttribute("aria-current");
  }
  showChord(preview);
  ctx.clearRect(0, 0, w, h);
  const notes = clip.cue.steps.flatMap((s) => s.notes), low = Math.min(...notes) - 2, high = Math.max(...notes) + 2;
  const y = (m) => h - 12 - (m - low) / (high - low) * (h - 24);
  if (preview) {
    ctx.fillStyle = "#b5ddcf12";
    ctx.fillRect(preview.start_ms / duration * w, 0, (preview.end_ms - preview.start_ms) / duration * w, h);
  }
  ctx.strokeStyle = "#ffffff0b"; ctx.lineWidth = 1;
  for (let m = Math.ceil(low / 12) * 12; m <= high; m += 12) {
    ctx.beginPath(); ctx.moveTo(0, y(m)); ctx.lineTo(w, y(m)); ctx.stroke();
  }
  for (const s of clip.cue.steps) {
    const active = playing && s.at_ms <= t && s.at_ms + s.hold_ms > t;
    for (const note of s.notes) {
      const highlighted = preview && preview.notes.includes(note) && s.at_ms < preview.end_ms && s.at_ms + s.hold_ms > preview.start_ms;
      ctx.fillStyle = active ? "#ffe2a6" : highlighted ? "#c9f3dd" : `rgba(166,216,203,${0.25 + 0.65 * s.velocity / 127})`;
      ctx.fillRect(s.at_ms / duration * w, y(note) - (highlighted ? 2 : 1.5), Math.max(2, s.hold_ms / duration * w), highlighted ? 4 : 3);
    }
  }
  ctx.strokeStyle = "#f4e8d9"; ctx.beginPath(); ctx.moveTo(t / duration * w, 0); ctx.lineTo(t / duration * w, h); ctx.stroke();
  $("position").textContent = clock(clip.start_ms + t);
  $("seek").value = t / 1000;
  $("seek").setAttribute("aria-valuetext", clock(clip.start_ms + t));
}

function tick() {
  frame = null;
  draw();
  if (!playing) return;
  if (position() >= clip.seconds * 1000) {
    const loop = $("loop").checked;
    pause(true);
    if (loop) void play();
    else $("status").textContent = "End of passage. Listen again whenever you like.";
    return;
  }
  frame = requestAnimationFrame(tick);
}

$("play").addEventListener("click", () => { $("status").classList.remove("error"); void play(); });
$("stop").addEventListener("click", () => { selected = null; pause(true); });
$("seek").addEventListener("input", () => {
  const next = Number($("seek").value) * 1000, resume = playing;
  pause(); selected = null; offset = next; draw(); if (resume) void play();
});
$("speed").addEventListener("change", () => {
  const resume = playing; pause(); speed = Number($("speed").value); if (resume) void play();
});
$("roll").addEventListener("pointermove", (event) => {
  if (!clip) return;
  const rect = $("roll").getBoundingClientRect();
  const t = (event.clientX - rect.left) / rect.width * clip.seconds * 1000;
  hovered = chords.find(c => c.start_ms <= t && c.end_ms > t) || null;
  draw();
});
$("roll").addEventListener("pointerleave", () => { hovered = null; draw(); });
$("roll").addEventListener("click", (event) => {
  if (!clip) return;
  const rect = $("roll").getBoundingClientRect();
  const t = (event.clientX - rect.left) / rect.width * clip.seconds * 1000;
  const chord = chords.find(c => c.start_ms <= t && c.end_ms > t);
  if (chord) void audition(chord);
});
window.addEventListener("resize", draw);
window.addEventListener("pagehide", () => { pause(); player?.dispose(); voice?.dispose(); });
document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); });
window.addEventListener("message", (event) => {
  if (event.source === parent && event.origin === location.origin && event.data?.type === "arsenal.replay.pause") pause();
});

async function load() {
  const params = new URLSearchParams(location.search);
  $("title").textContent = params.get("label") || "A moment from your playing";
  const responseId = params.get("response");
  if (!responseId && (!params.get("session") || !params.get("at"))) throw new Error("Open a passage link made with pianocue replay-link.");
  speed = Number(params.get("speed") || 1);
  if (!Number.isFinite(speed) || speed < 0.25 || speed > 2) throw new Error("Speed must be between 0.25 and 2.");
  if (![...$("speed").options].some((option) => Number(option.value) === speed)) {
    $("speed").add(new Option(`${speed}× speed`, String(speed)));
  }
  $("speed").value = String(speed);
  const query = new URLSearchParams({ session: params.get("session"), at: params.get("at"),
                                     seconds: params.get("seconds") || "8", speed: "1" });
  const resource = responseId ? `/api/conversation/replay/${encodeURIComponent(responseId)}` : `/api/piano/replay?${query}`;
  const response = await fetch(resource, { cache: "no-store", signal: AbortSignal.timeout(10000) });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Couldn't load this passage.");
  clip = data;
  renderChords();
  $("range").textContent = `${clock(clip.start_ms)}–${clock(clip.end_ms)} from your take · ${clip.seconds} seconds`;
  $("end").textContent = clock(clip.end_ms);
  $("seek").max = clip.seconds;
  controls.forEach((control) => { control.disabled = false; });
  $("status").textContent = "Ready. Press Play to hear this passage.";
  draw();
}

load().catch(fail);
