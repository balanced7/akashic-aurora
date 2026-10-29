// arsenal/web/lib/touchbar.js -- THE PHONE PAD BAR: a ghost row of pads along the bottom of a show page.
//
// WHY THIS EXISTS. Daniel opened the Stage on his S24 through the phone tunnel (2026-10-27) and asked, verbatim:
// "Can we make the diag readout hideable? ... Perhaps we can add a mini pad bar on the bottom that is 90% translucent".
// A phone has no keyboard and no Launchkey, so the show could be watched but not played.
//
// HOW. The bar does not own a single show action. Every pad presses the page's OWN key -- a KeyboardEvent with the same
// `code` the keyboard sends -- so whatever the page's key map says (V1 tonight, the V2 pad map once it lands) the bar
// plays, with no second table to drift. A pad holds its key for as long as the finger stays down (pad 2 on the Stage is
// hold = gate), several fingers play several pads, and a finger sliding off a pad still releases it. The HUD and
// fullscreen buttons press H and F, the keys both pages already give them, on the click (Android only grants fullscreen
// from a pointer-up). The bar asks for a screen wake lock on the first touch, so the phone does not sleep mid-show.
//
// THE KICK STRIPS (Daniel, same day: "lets make it a vertically longer button that presses and holds the light while the
// finger is on it and you can sweep up and down to adjust brightness! Lets have two kick buttons with vertical
// "velocity" one kick for white one kick for color, you can press both at same time and two rows can light up at
// once!"). Two tall ghost strips on the left and right edges, where the thumbs rest in landscape. The height of the
// finger is the velocity (the top is full); sliding while held rides the level live; release lets the row go. Keys
// carry no velocity, so the strips speak the page's PAD DOOR instead -- window CustomEvents "arsenal:pad" {pad, vel, on}
// and "arsenal:padlevel" {pad, vel} -- and only appear once the page has opened that door (window.__padDoor). On a
// page without the door nothing changes: no strips, and the bar keeps its own KICK pad.
//
// THE PALETTE PAD (2026-10-28, Daniel: "I want us to have 30 color palates ... what is used for driving the colors"). The
// Stage's PALETTE pad presses P (the next palette; it lands on the next 16-bar line). A page that knows its palette says so
// with the window event "arsenal:palette" {id, name, next, nextName, at, ladder, nextLadder} -- only when it changes, never
// per frame -- and keeps the latest in window.__palette. The pad's small line then shows the palette (or "-> the next one"
// while one is queued), and the colour kick strip carries a faint wash of the palette's two lift colours (what the colour
// kick paints). One text and one style change per palette event; nothing runs per frame.
//
// THE CAMERA DISTANCE SEGMENT (2026-10-29, Daniel: "can we think of a control scheme for camera distance so that i can
// trigger between closeup medium and far"). Three joined pads, CLOSE . MID . FAR, that press the page's Q, W and E (a
// tap starts the dolly, it lands on a beat; the lit one again hands distance back to the director). A page that knows its
// distance says so with the window event "arsenal:camdist" {mode, stop, ...} (only when it changes) and keeps the latest in
// window.__camdist; the segment lights the stop held by hand and none in auto. It sits in the bar, each pad 44 CSS px
// square. On a phone narrower than about 770 CSS px the bar wraps to a second row; the kick strips then stand above it
// (their bottom follows the bar's measured height, --tb-h), so no pad ever covers a strip, at any width.
//
// The bar shows itself on touch screens (pointer: coarse); ?pads=1 forces it on, ?pads=0 off. Its collapsed state is
// remembered per page (a convenience; the page works the same without storage).

const CSS = `
.tb { position: fixed; left: 0; right: 0; bottom: 0; z-index: 60; pointer-events: none;
      padding: 4px 4px calc(4px + env(safe-area-inset-bottom, 0px));
      display: flex; flex-wrap: wrap; gap: 4px; justify-content: flex-end;
      font: 600 10px/1 "JetBrains Mono", ui-monospace, monospace; letter-spacing: .06em; text-transform: uppercase;
      -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }
.tb button { pointer-events: auto; touch-action: none; flex: 1 1 44px; height: 44px; min-width: 0; margin: 0; padding: 0 2px;
      border-radius: 8px; border: 1px solid rgba(255, 255, 255, .14); background: rgba(255, 255, 255, .10);
      color: rgba(255, 255, 255, .42); font: inherit; letter-spacing: inherit; text-transform: inherit;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; transition: background .18s, color .18s; }
.tb button.long { font-size: 8.5px; letter-spacing: .02em; }
.tb button small { display: block; margin-top: 3px; font-size: 8px; opacity: .7; }
.tb button.on { background: rgba(255, 255, 255, .32); color: rgba(255, 255, 255, .9); transition: none; }
.tb button.util { flex: 0 0 44px; border-style: dashed; }
.tb.collapsed button:not(.grip) { display: none; }
.tb .seg { pointer-events: none; flex: 0 0 auto; display: flex; gap: 1px; }
.tb .seg button { flex: 0 0 44px; width: 44px; border-radius: 0; font-size: 8.5px; letter-spacing: .02em; }
.tb .seg button:first-child { border-radius: 8px 0 0 8px; }
.tb .seg button:last-child { border-radius: 0 8px 8px 0; }
.tb .seg button.lit { background: rgba(255, 255, 255, .26); color: rgba(255, 255, 255, .85); border-color: rgba(255, 255, 255, .34); }
.tb.strips button.stripped { display: none; }
.tbs { position: fixed; z-index: 61; top: 30vh; bottom: calc(var(--tb-h, calc(52px + env(safe-area-inset-bottom, 0px))) + 8px); width: 44px;
      pointer-events: auto; touch-action: none; border-radius: 12px; overflow: hidden;
      border: 1px solid rgba(255, 255, 255, .14); background: rgba(255, 255, 255, .08);
      font: 600 10px/1 "JetBrains Mono", ui-monospace, monospace; letter-spacing: .06em; text-transform: uppercase;
      color: rgba(255, 255, 255, .42); -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }
.tbs.left { left: calc(6px + env(safe-area-inset-left, 0px)); }
.tbs.right { right: calc(6px + env(safe-area-inset-right, 0px)); }
.tbs .lvl { position: absolute; left: 0; right: 0; bottom: 0; height: 0; background: rgba(255, 255, 255, .22); }
.tbs.on { border-color: rgba(255, 255, 255, .4); color: rgba(255, 255, 255, .9); }
.tbs .zone { position: absolute; left: 0; right: 0; top: 0; height: 5%; border-bottom: 1px dashed rgba(255, 255, 255, .25); }
.tbs .cap { position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%); text-align: center; pointer-events: none; }
.tbs .cap small { display: block; margin-top: 4px; font-size: 7px; opacity: .7; }
.tbs .cap { font-size: 9px; }
.tb.collapsed ~ .tbs { display: none; }
.tbs.tinted { background: linear-gradient(to top, var(--k0), var(--k1)); border-color: rgba(255, 255, 255, .22); }
`;

function store(key, value) {
  try {
    if (value === undefined) return localStorage.getItem(key);
    localStorage.setItem(key, value);
  } catch { /* private mode, blocked storage: the bar simply forgets */ }
  return null;
}

function sendKey(type, code, key) {
  // dispatched on <body> so it bubbles to the pages' window listeners and is never mistaken for typing in a field
  (document.body || document).dispatchEvent(new KeyboardEvent(type, { code, key, bubbles: true, cancelable: true }));
}

let wakeLock = null, wakeWanted = false;
async function keepAwake() {
  wakeWanted = true;
  if (wakeLock || !("wakeLock" in navigator) || document.visibilityState !== "visible") return;
  try {
    wakeLock = await navigator.wakeLock.request("screen");
    wakeLock.addEventListener("release", () => { wakeLock = null; });
  } catch { /* refused (battery saver, no secure context): the show still runs */ }
}
const padEvent = (type, detail) => window.dispatchEvent(new CustomEvent(type, { detail }));

// pads: [{ label, code, key, sub?, stripped? }] in order (stripped: hidden while the kick strips stand in for it).
// strips: [{ label, sub, pad, side: "left" | "right", floor? }]. id: a short name for the remembered collapsed state.
export function mountTouchBar({ id, pads, strips = [], segment = null }) {
  const qs = new URLSearchParams(location.search);
  const want = qs.get("pads");
  if (want === "0") return null;
  if (want !== "1" && !matchMedia("(pointer: coarse)").matches) return null;

  const style = document.createElement("style");
  style.textContent = CSS;
  document.head.appendChild(style);
  const bar = document.createElement("nav");
  bar.className = "tb";
  bar.setAttribute("aria-label", "Pads");

  const fingers = new Map();       // pointerId -> button
  const holds = new Map();         // button -> fingers on it
  const release = (pointerId) => {
    const b = fingers.get(pointerId);
    if (!b) return;
    fingers.delete(pointerId);
    const n = (holds.get(b) || 1) - 1;
    if (n > 0) { holds.set(b, n); return; }
    holds.delete(b);
    b.classList.remove("on");
    sendKey("keyup", b.dataset.code, b.dataset.key);
  };

  const padButton = (p, parent) => {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.code = p.code;
    b.dataset.key = p.key;
    b.textContent = p.label;
    if (p.label.length > 7) b.classList.add("long");
    if (p.stripped) b.classList.add("stripped");
    if (p.sub) { const s = document.createElement("small"); s.textContent = p.sub; b.appendChild(s); }
    if (p.palette) paletteLabel(b.querySelector("small"));
    b.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      keepAwake();
      if (fingers.has(e.pointerId)) return;
      try { b.setPointerCapture(e.pointerId); } catch { /* the pointer is already gone */ }
      fingers.set(e.pointerId, b);
      const n = (holds.get(b) || 0) + 1;
      holds.set(b, n);
      if (n === 1) { b.classList.add("on"); sendKey("keydown", p.code, p.key); }
    });
    for (const ev of ["pointerup", "pointercancel", "lostpointercapture"]) b.addEventListener(ev, (e) => release(e.pointerId));
    parent.appendChild(b);
    return b;
  };
  for (const p of pads) padButton(p, bar);
  if (segment) {
    const seg = document.createElement("div");
    seg.className = "seg";
    seg.setAttribute("role", "group");
    seg.setAttribute("aria-label", segment.label || "segment");
    const items = segment.items.map((it) => { const b = padButton(it, seg); b.dataset.stop = it.stop; b.title = it.title || it.label; return b; });
    // the lit item follows the page's own event (only when it changes; nothing per frame)
    const show = (d) => { for (const b of items) b.classList.toggle("lit", !!d && d.mode === "manual" && d.stop === b.dataset.stop); };
    if (segment.event) { window.addEventListener(segment.event, (e) => show(e.detail)); show(window[segment.state]); }
    bar.appendChild(seg);
  }

  const util = (label, title, onClick, cls = "") => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = `util ${cls}`.trim();
    b.textContent = label;
    b.title = title;
    b.setAttribute("aria-label", title);
    b.addEventListener("click", (e) => { e.preventDefault(); keepAwake(); onClick(b); });
    bar.appendChild(b);
    return b;
  };
  util("HUD", "Show or hide the readout", () => { sendKey("keydown", "KeyH", "h"); sendKey("keyup", "KeyH", "h"); });
  util("⛶", "Fullscreen", () => { sendKey("keydown", "KeyF", "f"); sendKey("keyup", "KeyF", "f"); });
  const KEY = `arsenal.touchbar.${id}.collapsed`;
  const setCollapsed = (on, b) => {
    bar.classList.toggle("collapsed", on);
    b.textContent = on ? "▴" : "▾";
    b.title = on ? "Show the pads" : "Hide the pads";
    b.setAttribute("aria-label", b.title);
    store(KEY, on ? "1" : "0");
  };
  const grip = util("▾", "Hide the pads", (b) => setCollapsed(!bar.classList.contains("collapsed"), b), "grip");
  if (store(KEY) === "1") setCollapsed(true, grip);

  bar.addEventListener("contextmenu", (e) => e.preventDefault());   // a long press is a held pad, not a menu
  window.addEventListener("blur", () => { for (const pid of [...fingers.keys()]) release(pid); });
  // the browser drops the wake lock whenever the tab is hidden; take it back on return once a touch has asked for it
  document.addEventListener("visibilitychange", () => { if (wakeWanted) keepAwake(); });
  document.body.appendChild(bar);
  // the strips stand above the bar whatever its height (one row, or two on a narrow phone): its measured height, live
  const barHeight = () => document.documentElement.style.setProperty("--tb-h", `${Math.ceil(bar.getBoundingClientRect().height)}px`);
  barHeight();
  if ("ResizeObserver" in window) new ResizeObserver(barHeight).observe(bar);
  else window.addEventListener("resize", barHeight);
  if (strips.length) {
    // the strips wait for the page's pad door (it opens once the show starts: a show page holds its start for the
    // viewer's flash protection choice, lib/flash-consent.js, for as long as the viewer reads the warning); a page
    // without a door keeps its keys. Looked for every 250 ms for 30 s, then every 2 s.
    const t0 = performance.now();
    const look = () => {
      if (window.__padDoor) { for (const st of strips) mountStrip(st); bar.classList.add("strips"); barHeight(); return; }
      setTimeout(look, performance.now() - t0 < 30000 ? 250 : 2000);
    };
    look();
  }
  return bar;
}

// the palette pad's small line: the palette showing, or the one queued to land (event-driven: arsenal:palette)
function paletteLabel(small) {
  if (!small) return;
  const show = (d) => { if (d && (d.name || d.nextName)) small.textContent = d.nextName ? `-> ${d.nextName}` : d.name; };
  window.addEventListener("arsenal:palette", (e) => show(e.detail));
  show(window.__palette);
}
const HEX6 = /^#[0-9a-f]{6}$/i;
// the colour strip's wash: the palette's two lift colours at a low alpha (event-driven: arsenal:palette)
function ladderTint(el) {
  const show = (d) => {
    const L = d && Array.isArray(d.ladder) && d.ladder.length === 2 && d.ladder.every((h) => HEX6.test(h)) ? d.ladder : null;
    if (!L) return;
    el.style.setProperty("--k0", `${L[0]}40`); el.style.setProperty("--k1", `${L[1]}1c`);
    el.classList.add("tinted");
  };
  window.addEventListener("arsenal:palette", (e) => show(e.detail));
  show(window.__palette);
}

// One tall strip: the finger's height is the velocity (floor at the bottom, 1 at the top), sliding rides it live.
function mountStrip({ label, sub, pad, side, floor = 0.15, tint = null }) {
  const el = document.createElement("div");
  el.className = `tbs ${side}`;
  el.setAttribute("role", "slider");
  el.setAttribute("aria-label", `${label} ${sub || ""}`.trim());
  for (const cls of ["zone", "lvl", "cap"]) { const d = document.createElement("div"); d.className = cls; el.appendChild(d); }
  const cap = el.querySelector(".cap");
  cap.textContent = label;
  if (sub) { const sm = document.createElement("small"); sm.textContent = sub; cap.appendChild(sm); }
  const lvl = el.querySelector(".lvl");
  let finger = null, vel = 0, sent = -1, raf = 0;
  const velAt = (y) => {
    const r = el.getBoundingClientRect();
    const u = Math.min(1, Math.max(0, 1 - (y - r.top) / Math.max(1, r.height)));
    return +(floor + (1 - floor) * u).toFixed(3);
  };
  const show = () => { lvl.style.height = `${Math.round(((vel - floor) / (1 - floor)) * 100)}%`; };
  const flush = () => { raf = 0; if (finger !== null && vel !== sent) { sent = vel; padEvent("arsenal:padlevel", { pad, vel }); } };
  el.addEventListener("pointerdown", (e) => {
    e.preventDefault();
    keepAwake();
    if (finger !== null) return;                       // one finger per strip; the other thumb has the other strip
    finger = e.pointerId;
    try { el.setPointerCapture(e.pointerId); } catch { /* the pointer is already gone */ }
    vel = sent = velAt(e.clientY);
    el.classList.add("on"); show();
    padEvent("arsenal:pad", { pad, vel, on: true });
  });
  el.addEventListener("pointermove", (e) => {
    if (e.pointerId !== finger) return;
    vel = velAt(e.clientY); show();
    if (!raf) raf = requestAnimationFrame(flush);      // at most one level update a frame
  });
  const up = (e) => {
    if (e.pointerId !== finger) return;
    finger = null;
    if (raf) { cancelAnimationFrame(raf); raf = 0; }
    el.classList.remove("on"); lvl.style.height = "0";
    padEvent("arsenal:pad", { pad, vel, on: false });
  };
  for (const ev of ["pointerup", "pointercancel", "lostpointercapture"]) el.addEventListener(ev, up);
  el.addEventListener("contextmenu", (e) => e.preventDefault());
  window.addEventListener("blur", () => { if (finger !== null) up({ pointerId: finger }); });
  if (tint === "ladder") ladderTint(el);
  document.body.appendChild(el);
  return el;
}

// The Stage's keys (stage/stage.js, the keyboard block; the set's pad map in sets/source-v1.json): kick white 1 and
// kick colour 5 (both step aside for the strips), lasers 2, phrase go 3 / next 4 / stop 7, fly-out 6, drop 0, the
// rings' MORPH 8 and HERO 9, C for the next camera shot, P for the next palette (it lands on the next 16-bar line), and O
// for the next colour setup (the next bar line).
export const STAGE_PADS = [
  { label: "kick", code: "Digit1", key: "1", sub: "white", stripped: true },
  { label: "kick", code: "Digit5", key: "5", sub: "colour", stripped: true },
  { label: "lasers", code: "Digit2", key: "2", sub: "hold" },
  { label: "go", code: "Digit3", key: "3", sub: "phrase" },
  { label: "next", code: "Digit4", key: "4", sub: "step" },
  { label: "stop", code: "Digit7", key: "7", sub: "phrase" },
  { label: "fly-out", code: "Digit6", key: "6" },
  { label: "drop", code: "Digit0", key: "0" },
  { label: "morph", code: "Digit8", key: "8", sub: "rings" },
  { label: "hero", code: "Digit9", key: "9", sub: "beam" },
  { label: "shot", code: "KeyC", key: "c", sub: "camera" },
  { label: "palette", code: "KeyP", key: "p", sub: "next", palette: true },
  // the next colour SETUP (setups.js; O; lands on the next bar line). Daniel, 2026-10-29, from his phone: "Latest version
  // seems to have only one color theme"
  { label: "setup", code: "KeyO", key: "o", sub: "next" },
];

// The Stage's camera distance segment (stage/distance.js): CLOSE, MID and FAR press Q, W and E.
export const STAGE_DISTANCE = {
  label: "Camera distance", event: "arsenal:camdist", state: "__camdist",
  items: [
    { label: "close", code: "KeyQ", key: "q", stop: "close", title: "Camera close (again: back to the director)" },
    { label: "mid", code: "KeyW", key: "w", stop: "medium", title: "Camera medium (again: back to the director)" },
    { label: "far", code: "KeyE", key: "e", stop: "far", title: "Camera far (again: back to the director)" },
  ],
};

// The Stage's two kick strips (KICK v2: pad 1 deals an area the palette's white, pad 5 an area lifted inside the palette;
// the colour strip wears a wash of the palette's two lift colours).
export const STAGE_STRIPS = [
  { label: "kick", sub: "white", pad: 1, side: "left" },
  { label: "kick", sub: "colour", pad: 5, side: "right", tint: "ladder" },
];

// The VJ page's twelve pads (vj.js KEY_PADS: 1-9, 0, minus, equals), labelled with the action each pad is mapped to
// (the short action name: the panel's full labels, "Kaleidoscope" and "Laser burst", do not fit a phone-width pad).
const VJ_CODES = [["Digit1", "1"], ["Digit2", "2"], ["Digit3", "3"], ["Digit4", "4"], ["Digit5", "5"], ["Digit6", "6"],
                  ["Digit7", "7"], ["Digit8", "8"], ["Digit9", "9"], ["Digit0", "0"], ["Minus", "-"], ["Equal", "="]];
export function vjPads(padMap) {
  return VJ_CODES.map(([code, key], i) => ({ label: String(padMap[i] || i + 1), code, key }));
}
