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
// The bar shows itself on touch screens (pointer: coarse); ?pads=1 forces it on, ?pads=0 off. Its collapsed state is
// remembered per page (a convenience; the page works the same without storage).

const CSS = `
.tb { position: fixed; left: 0; right: 0; bottom: 0; z-index: 60; pointer-events: none;
      padding: 4px 4px calc(4px + env(safe-area-inset-bottom, 0px));
      display: flex; flex-wrap: wrap; gap: 4px; justify-content: flex-end;
      font: 600 10px/1 "JetBrains Mono", ui-monospace, monospace; letter-spacing: .06em; text-transform: uppercase;
      -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; }
.tb button { pointer-events: auto; touch-action: none; flex: 1 1 48px; height: 44px; min-width: 0; margin: 0; padding: 0 2px;
      border-radius: 8px; border: 1px solid rgba(255, 255, 255, .14); background: rgba(255, 255, 255, .10);
      color: rgba(255, 255, 255, .42); font: inherit; letter-spacing: inherit; text-transform: inherit;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; transition: background .18s, color .18s; }
.tb button.long { font-size: 8.5px; letter-spacing: .02em; }
.tb button small { display: block; margin-top: 3px; font-size: 8px; opacity: .7; }
.tb button.on { background: rgba(255, 255, 255, .32); color: rgba(255, 255, 255, .9); transition: none; }
.tb button.util { flex: 0 0 38px; border-style: dashed; }
.tb.collapsed button:not(.grip) { display: none; }
.tb.strips button.stripped { display: none; }
.tbs { position: fixed; z-index: 61; top: 12vh; bottom: calc(60px + env(safe-area-inset-bottom, 0px)); width: 64px;
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
.tbs .cap small { display: block; margin-top: 4px; font-size: 8px; opacity: .7; }
.tb.collapsed ~ .tbs { display: none; }
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
export function mountTouchBar({ id, pads, strips = [] }) {
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

  for (const p of pads) {
    const b = document.createElement("button");
    b.type = "button";
    b.dataset.code = p.code;
    b.dataset.key = p.key;
    b.textContent = p.label;
    if (p.label.length > 7) b.classList.add("long");
    if (p.stripped) b.classList.add("stripped");
    if (p.sub) { const s = document.createElement("small"); s.textContent = p.sub; b.appendChild(s); }
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
    bar.appendChild(b);
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
  if (strips.length) {
    // the strips wait for the page's pad door (it opens once the page has booted); a page without one keeps its keys
    const t0 = performance.now();
    const look = () => {
      if (window.__padDoor) { for (const st of strips) mountStrip(st); bar.classList.add("strips"); return; }
      if (performance.now() - t0 < 30000) setTimeout(look, 250);
    };
    look();
  }
  return bar;
}

// One tall strip: the finger's height is the velocity (floor at the bottom, 1 at the top), sliding rides it live.
function mountStrip({ label, sub, pad, side, floor = 0.15 }) {
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
  document.body.appendChild(el);
  return el;
}

// The Stage's keys (stage/stage.js, the keyboard block; the set's pad map in sets/source-v1.json): kick white 1 and
// kick colour 5 (both step aside for the strips), lasers 2, phrase go 3 / next 4 / stop 7, fly-out 6, drop 0, the
// rings' MORPH 8 and HERO 9, and C for the next camera shot.
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
];

// The Stage's two kick strips (KICK v2: pad 1 deals a row toward white, pad 5 a row in the theme's colour).
export const STAGE_STRIPS = [
  { label: "kick", sub: "white", pad: 1, side: "left" },
  { label: "kick", sub: "colour", pad: 5, side: "right" },
];

// The VJ page's twelve pads (vj.js KEY_PADS: 1-9, 0, minus, equals), labelled with the action each pad is mapped to
// (the short action name: the panel's full labels, "Kaleidoscope" and "Laser burst", do not fit a phone-width pad).
const VJ_CODES = [["Digit1", "1"], ["Digit2", "2"], ["Digit3", "3"], ["Digit4", "4"], ["Digit5", "5"], ["Digit6", "6"],
                  ["Digit7", "7"], ["Digit8", "8"], ["Digit9", "9"], ["Digit0", "0"], ["Minus", "-"], ["Equal", "="]];
export function vjPads(padMap) {
  return VJ_CODES.map(([code, key], i) => ({ label: String(padMap[i] || i + 1), code, key }));
}
