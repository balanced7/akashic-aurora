// The Rescan hint's decision model: given what the page, the browser and Windows can each see, which gentle hint (if
// any) answers this moment. Pure -- no DOM, timers or fetch. The host (midi-hint.js) gathers the facts and renders.
//
// The principle (docs/library/design/20261007_second-press-gentle-hints_db25d1.md): the first press of Rescan is a
// command, the second is a question. Answer on strong signals only, name the layer where the signal stops, offer one
// action, never pop up unprompted, defer during REC, and leave on success.
// Acceptance: docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md (H1). Tests:
// tests/piano_midi_hint.test.mjs.
//
// Facts, gathered by the host:
//   now, trigger ("press" | "tick" | "change"), presses (Rescan press times),
//   permission ("granted" | "denied" | "prompt" | "unknown"), access (a MIDIAccess was granted),
//   inputs ([{ name, state }] the browser lists, Claude's MIDI out already removed),
//   bound (names the page listens to), remembered (the stored input choice),
//   events / eventsAtPress (midi.events now and at the last press), rec (the recorder's state),
//   windows (null, or GET /api/midi/ports: { ok, inputs, service: { state } }),
//   browser ({ name, restartUrl }), shown ({ cause: highest level shown }), open (the cause on screen, or null),
//   heard (null, or { notes: [spelled names], chord } of what is sounding now), heardShown (the narration's title),
//   banter (how many presses in a row came after a success; 0 for none), lastHeard (the last note it named).

export const SECOND_PRESS_WINDOW_MS = 90_000;
export const SOUND_CHECK_AFTER_MS = 2_000;      // bound, Rescanned, and silent this long: the sound check begins to
                                                // condense out of a mist (Daniel, 2026-10-08: "a 2 second slow delay
                                                // that fades in or becomes revealed out of a mist"; midi-hint.css)
export const STILL_SILENT_AFTER_MS = 26_000;    // ...and this long: say so once more
export const SOUND_CHECK_GIVE_UP_MS = 120_000;  // a check nobody answered closes by itself
export const SUCCESS_LINGER_MS = 3_500;
export const NARRATE_MS = 8_000;                // "Heard you" narrates new notes this long, then lets itself fade

const ALL_INPUTS = "__all__";  // piano.js's "all inputs" choice, never a device name
const PROBLEMS = new Set(["permission-denied", "no-access", "stale-browser-list", "windows-sees-none",
  "service-stopped", "browser-sees-none", "not-selected"]);
const WEAK = new Set(["not-selected"]);  // waits for the second press; the rest are answered on the first

const isDaw = (name) => /daw/i.test(name || "");  // the same rule as piano.js midiRank: DAW control ports are not keys
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
export const displayName = (name) => String(name || "").replace(/\s+MIDI$/i, "").trim();
const sameDevice = (a, b) => {  // WinMM caps names at 31 characters, and option labels carry suffixes
  const x = String(a || "").toLowerCase().trim(), y = String(b || "").toLowerCase().trim();
  return !!x && !!y && (x.startsWith(y) || y.startsWith(x));
};
const browserKeys = (f) => (f.inputs || []).filter((i) => !isDaw(i.name) && i.state !== "disconnected");
const windowsKeys = (f) => (f.windows && f.windows.ok ? (f.windows.inputs || []).filter((n) => !isDaw(n)) : []);

export function decideMidiHint(f) {
  const now = f.now;
  const presses = (f.presses || []).filter((t) => t <= now);
  const lastPress = presses.length ? presses[presses.length - 1] : null;
  const recent = presses.filter((t) => now - t <= SECOND_PRESS_WINDOW_MS).length;
  const bound = f.bound || [];
  const recording = !!f.rec && f.rec !== "idle";

  // 1. Success closes whatever was open. Never during REC.
  if (bound.length && f.open && PROBLEMS.has(f.open)) {
    return recording ? null : success("found", "There it is", `Listening to ${displayName(bound[0])}.`);
  }
  if (bound.length && f.open === "sound-check" && f.events > f.eventsAtPress) {
    return recording ? null : success("heard", heardTitle(f.heard), `${displayName(bound[0])} is coming through.`);
  }
  // While "Heard you" lingers it narrates: each new note or chord renames the card ("that's a C... that's an E...",
  // Daniel's own sample, 2026-10-08). Nothing new, or a take starting: the card is left to its own timer.
  if (bound.length && f.open === "heard") {
    const title = heardTitle(f.heard);
    if (recording || !f.heard || title === f.heardShown) return null;
    return success("heard", title, `${displayName(bound[0])} is coming through.`);
  }

  // 2. Something is bound: the only question left is whether notes arrive.
  if (bound.length) {
    // ...unless Rescan already said yes. Pressed again after a success, it answers in the deadpan register, one rung
    // per press, and then goes quiet -- the second-press principle, played as comedy (Daniel, 2026-10-08).
    if (f.trigger === "press" && f.banter > 0) {
      const line = BANTER[f.banter - 1];
      return recording || !line ? null
        : { cause: "banter", level: f.banter, tone: "wry", title: line.title, body: line.body(f.lastHeard) };
    }
    if (lastPress == null || f.events > f.eventsAtPress) return null;
    const silent = now - lastPress;
    if (silent < SOUND_CHECK_AFTER_MS || silent >= SOUND_CHECK_GIVE_UP_MS) return null;
    const name = displayName(bound[0]);
    const v = silent >= STILL_SILENT_AFTER_MS
      ? { cause: "sound-check", level: 2, tone: "check", title: `Still nothing from ${name}`,
          body: "If its keys don't light up the piano, choose another input in Studio → Input." }
      : { cause: "sound-check", level: 1, tone: "check", title: `Listening to ${name}`,
          body: "Play any key — I'll tell you the moment I hear it." };
    return recording ? { cause: v.cause, defer: true } : v;
  }

  // 3. Nothing is bound: find the layer where the signal stops.
  const cause = problemCause(f);
  if (!cause) return null;
  const isOpen = f.open === cause;
  // A problem hint never pops up on its own: it answers a press, or a press that REC deferred ("resume", when
  // recording ends -- that question is still pending however long the take ran, so the window does not apply).
  const asked = f.trigger === "press" || f.trigger === "resume";
  if (!asked && !isOpen) return null;
  const pressed = f.trigger === "resume" ? Math.max(recent, 1) : recent;
  if (!isOpen && pressed < (WEAK.has(cause) ? 2 : 1)) return null;
  if (recording) return { cause, defer: true };
  const shown = (f.shown || {})[cause] || 0;
  const level = pressed >= 3 || (shown >= 1 && pressed >= 2) ? 2 : 1;
  const v = { cause, level, tone: "hint", ...WORDS[cause](f, keyboardName(f)) };
  if (level === 2) v.chain = chain(f);
  return v;
}

function problemCause(f) {
  if (f.permission === "denied") return "permission-denied";
  if (!f.access) return "no-access";
  if (browserKeys(f).length) return "not-selected";
  const w = f.windows;
  if (!w || !w.ok) return "browser-sees-none";
  if (windowsKeys(f).length) return "stale-browser-list";
  if (w.service && w.service.state === "stopped") return "service-stopped";
  return "windows-sees-none";
}

function keyboardName(f) {
  const rem = f.remembered && f.remembered !== ALL_INPUTS ? f.remembered : null;
  const win = windowsKeys(f);
  const pick = (rem && win.find((n) => sameDevice(n, rem))) || rem || win[0] || null;
  return pick ? displayName(pick) : null;
}

const restartAction = (f) => (f.browser.restartUrl
  ? { action: { label: `Copy ${f.browser.restartUrl}`, copy: f.browser.restartUrl, note: "then paste it into the address bar" } }
  : {});

const WORDS = {
  "permission-denied": (f) => ({
    title: "MIDI is blocked for this page",
    body: `${cap(f.browser.name)} isn't letting this page use MIDI devices. Allow MIDI for this site in the site settings left of the address bar, then press Rescan.`,
  }),
  "no-access": (f) => (f.permission === "prompt"
    ? { title: "MIDI is waiting for your OK", body: `Allow MIDI when ${f.browser.name} asks, then press Rescan.` }
    : { title: "This browser can't reach MIDI", body: "Web MIDI isn't available here. Brave, Chrome and Edge can all play the piano from a MIDI keyboard." }),
  "stale-browser-list": (f, kb) => ({
    title: `Your ${kb || "keyboard"} is plugged in, but ${f.browser.name} can't see it`,
    body: `Windows sees it, so the keyboard and cable are fine. ${cap(f.browser.name)}'s list of MIDI devices is out of date: it missed the keyboard when it connected. Restart ${f.browser.name} and your tabs come back.`,
    ...restartAction(f),
  }),
  "windows-sees-none": () => ({
    title: "Windows doesn't see a MIDI keyboard",
    body: "Check that it's switched on and the USB cable is seated. It shows up a few seconds after it connects; then press Rescan.",
  }),
  "service-stopped": () => ({
    title: "Windows' MIDI service is stopped",
    body: "Restarting the computer brings it back. An administrator can also start “midisrv” from Services.",
  }),
  "browser-sees-none": (f) => ({
    title: "No MIDI keyboard in sight",
    body: `If it's plugged in and switched on, ${f.browser.name} may have missed it when it connected. Restarting ${f.browser.name} usually brings it back.`,
    ...restartAction(f),
  }),
  "not-selected": (f) => ({
    title: `${displayName(browserKeys(f)[0].name)} is here, but not selected`,
    body: "Choose it in Studio → Input, and the piano starts listening.",
  }),
};

function chain(f) {
  const w = f.windows;
  const win = windowsKeys(f);
  const windows = !w || !w.ok ? "unknown" : win.length ? "ok"
    : (w.service && w.service.state === "stopped" ? "stopped" : "missing");
  const browser = f.permission === "denied" ? "blocked" : browserKeys(f).length ? "ok" : (win.length ? "stale" : "missing");
  return [
    { id: "windows", label: "Windows", status: windows },
    { id: "browser", label: cap(f.browser.name), status: browser },
    { id: "page", label: "This page", status: (f.bound || []).length ? "ok" : "idle" },
  ];
}

const success = (cause, title, body) => ({ cause, level: 1, tone: "success", title, body });

// What the sound check heard, as a title. The notes arrive already spelled by the page's own speller (one speller for
// the reader and the page), so this only chooses the sentence -- and the article: "an" before A, E and F, which are
// said with a vowel sound ("an E", "an F♯"), "a" before the rest ("a C", "a B♭").
const article = (name) => (/^[AEF]/.test(name) ? "an" : "a");
export function heardTitle(heard) {
  const notes = (heard && heard.notes) || [];
  if (!notes.length) return "Heard you";
  if (notes.length === 1) return `That's ${article(notes[0])} ${notes[0]}`;
  if (notes.length === 2) return `That's ${article(notes[0])} ${notes[0]} and ${article(notes[1])} ${notes[1]}`;
  return heard.chord ? `${heard.chord}, loud and clear` : "That's a chord, loud and clear";
}

// The deadpan ladder: Rescan pressed again while everything already works. Clarke & Dawe by way of Bagley.
export const BANTER = [
  { title: "…yes?",
    body: (heard) => (heard ? `Still here. Still working. That was ${article(heard)} ${heard} a moment ago.` : "Still here. Still working.") },
  { title: "It's working.",
    body: () => "I've had it checked. It's connected, the notes are arriving, and frankly I'm running out of ways to say so." },
  { title: "Look, I'll be straight with you.",
    body: () => "There's nothing wrong with it. That's the hardest thing in the world to diagnose." },
  { title: "I'm going to have a little lie down.",
    body: () => "Play something and I'll know you're alright." },
];

// Musical easter eggs, heard only while the hint is listening (after a Rescan press, never during a take), so a
// D-minor improvisation is never ambushed mid-performance. pcs are pitch classes in order, any octave.
export const EGGS = [
  {
    // Periphery lore, from Daniel: Misha Mansoor explained his guitar tuning in a YouTube video, deadpan, string by
    // string, until it hits you -- and he actually played in it.
    id: "fagdad",
    pcs: [5, 9, 7, 2, 9, 2],
    title: "F. A. G. D. A. D.",
    // The first sentence is Daniel's own line; the last two are his verdict ("he played the right notes in the wrong
    // tuning, it was glorious"), both 2026-10-08.
    body: "Ah yes, one of Misha Mansoor's legendary guitar tunings. In his Scarlet lesson he plays the first riff, then names the tuning, string by string, with a perfectly straight face. The right notes, in the wrong tuning. Glorious.",
    // Verified 2026-10-08 against the original's captions (py agent_cli.py captions): "Scarlet Guitar Lesson with
    // Misha". He plays the first riff at 0:14-0:25, then at ~0:27 calls it "a different tuning" and spells it out --
    // which YouTube's own auto-captions render as "f-a-a ... a detuning" and then censor. Sourcing rules: atom 84c3e2.
    // The thumbnail is the platform's own image, linked, never copied.
    source: {
      url: "https://www.youtube.com/watch?v=z7K8Vjm8jLU",
      label: "Watch the Scarlet lesson ↗",
      thumb: "https://i.ytimg.com/vi/z7K8Vjm8jLU/hqdefault.jpg",
    },
  },
];

export function matchEgg(noteOns) {  // the egg whose sequence the most recent note-ons end with, or null
  const pcs = (noteOns || []).map((m) => ((m % 12) + 12) % 12);
  for (const egg of EGGS) {
    const n = egg.pcs.length;
    if (pcs.length >= n && egg.pcs.every((pc, i) => pcs[pcs.length - n + i] === pc)) return egg;
  }
  return null;
}

// The Studio footer's input line. It used to say "Computer keyboard ready" whenever no MIDI input was bound -- true,
// and exactly how a missing KeyLab hid on 2026-10-07. null means "keep the selected input's own label".
export function footerStatus({ boundName, remembered, visible = [] }) {
  if (boundName) return null;
  const rem = remembered && remembered !== ALL_INPUTS ? remembered : null;
  if (!rem) return "Computer keyboard ready";
  const here = visible.some((v) => sameDevice(v, rem));
  return `${displayName(rem)} ${here ? "not selected" : "not found"} · computer keyboard ready`;
}
