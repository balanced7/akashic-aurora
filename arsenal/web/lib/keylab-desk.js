// The KeyLab's face on a page: arsenal/web/lib/keylab-desk.js (an ES module, DOM only, no dependency but the client).
//
// mountKeyLabHud() draws, for any page a binder drives (the Shader Desk, the VFX Bench mount, Play in a frame):
//   - where the KeyLab is coming from (the VJ engine, Web MIDI, or nothing yet, with a button to allow Web MIDI);
//   - the readout: the control you just moved or touched, what it drives, the value as text and as a bar, and while a
//     fader has not caught its value yet, a ghost mark where the value is and which way to move ("move up to 42%");
//   - the chord, with the colour its root puts on a hue parameter;
//   - the 12 pads as they sit on the unit, 4 across x 3 down (1 2 3 4 / 5 6 7 8 / 9 10 11 12, PAD_GRID): scenes on
//     1-8 (the top two rows), snapshots A-D on 9-12 (the bottom row, nearest the player) (click = the pad; shift-click
//     or right-click a snapshot pad = store);
//   - optionally the map (every parameter, the controls that drive it, a learn chip) and the options.
// An `overlay` element (the stage) gets a large readout that fades a moment after the last move, for performing.
//
// Pad lights: wirePadLights() asks the VJ engine to colour the pads on a scene change or a snapshot store, and only
// then (never on a timer), and only while the "Light the pads" option is on. Off by default: another page (the VJ
// page) may be painting them.
import { PAD_GRID, controlLabel, controlShort, fifthsTurn } from "./keylab-client.js";

// The panel lives in a shadow root: a host page's own CSS (the VFX Bench styles every button full width) cannot reach
// it. Colours are custom properties with defaults on :host, so a page restyles it by setting --klh-* on the element it
// passes as `parent` (an outer page's declaration on the host element wins over :host).
const CSS = `
:host{--klh-bg:rgba(16,18,22,.86);--klh-panel:rgba(255,255,255,.04);--klh-ink:#e6e8eb;--klh-ink2:#a3acb7;--klh-ink3:#7f8994;
  --klh-rule:rgba(255,255,255,.09);--klh-accent:#e47fa7;--klh-ok:#4cc2ba;--klh-warn:#f0a443;display:block}
.klh,.klh-overlay{font:12px/1.35 "JetBrains Mono","Cascadia Mono",Consolas,monospace;color:var(--klh-ink);box-sizing:border-box;text-align:left}
.klh *,.klh-overlay *{box-sizing:border-box}
button,select,input{margin:0;width:auto;flex:none;text-transform:none;letter-spacing:normal;box-shadow:none}
.klh.klh-floating{position:fixed;right:14px;bottom:14px;width:300px;max-height:calc(100vh - 28px);overflow:auto;z-index:2147483000;
  background:var(--klh-bg);backdrop-filter:blur(10px);border:1px solid var(--klh-rule);border-radius:8px;padding:10px;
  box-shadow:0 12px 40px rgba(0,0,0,.45)}
.klh-head{display:flex;align-items:center;gap:8px}
.klh-title{font-weight:600;letter-spacing:.06em;text-transform:uppercase;font-size:11px;color:var(--klh-ink2);flex:1;min-width:0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.klh-dot{width:8px;height:8px;border-radius:50%;background:var(--klh-ink3);flex:none}
.klh-dot.up{background:var(--klh-ok);box-shadow:0 0 8px var(--klh-ok)}.klh-dot.midi{background:var(--klh-warn);box-shadow:0 0 8px var(--klh-warn)}
.klh-src{color:var(--klh-ink2);font-size:11px;margin:4px 0 0}
.klh-btn{font:inherit;font-size:11px;color:var(--klh-ink);background:transparent;border:1px solid var(--klh-rule);border-radius:4px;
  padding:3px 8px;cursor:pointer}
.klh-btn:hover{border-color:var(--klh-accent)}.klh-btn[aria-pressed=true]{border-color:var(--klh-accent);color:var(--klh-accent)}
.klh-sec{margin-top:10px;padding-top:8px;border-top:1px solid var(--klh-rule)}
.klh-sec-t{font-size:10px;letter-spacing:.08em;text-transform:uppercase;color:var(--klh-ink3);margin:0 0 6px}
.klh-read{min-height:46px}
.klh-read-top{display:flex;justify-content:space-between;gap:8px;color:var(--klh-ink2);font-size:11px}
.klh-read-val{font-size:20px;font-weight:600;letter-spacing:.01em;margin:2px 0 4px;font-variant-numeric:tabular-nums}
.klh-bar{position:relative;height:6px;border-radius:3px;background:var(--klh-panel);overflow:visible}
.klh-bar-fill{position:absolute;left:0;top:0;bottom:0;border-radius:3px;background:var(--klh-accent);transition:width .06s linear}
.klh-bar-ghost{position:absolute;top:-4px;bottom:-4px;width:2px;margin-left:-1px;background:var(--klh-ink);opacity:0;border-radius:1px}
.klh-bar.pending .klh-bar-fill{background:var(--klh-ink3)}.klh-bar.pending .klh-bar-ghost{opacity:.9}
.klh-hint{color:var(--klh-warn);font-size:11px;min-height:15px;margin-top:4px}
.klh-chord{display:flex;align-items:center;gap:8px;min-height:20px}
.klh-swatch{width:14px;height:14px;border-radius:3px;border:1px solid var(--klh-rule);flex:none;visibility:hidden}
.klh-swatch.on{visibility:visible}
.klh-chord-name{font-size:15px;font-weight:600}
.klh-pads{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px}
.klh-pad{font:inherit;font-size:10px;line-height:1.2;text-align:left;height:44px;padding:3px 5px;border-radius:5px;border:1px solid var(--klh-rule);
  background:var(--klh-panel);color:var(--klh-ink2);cursor:pointer;overflow:hidden;position:relative;display:block;width:100%}
.klh-pad b{display:block;font-size:9px;color:var(--klh-ink3);font-weight:400;margin-bottom:1px}
.klh-pad span{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.klh-pad.snap:not(.full) span{color:var(--klh-ink3)}
.klh-pad.scene{border-left:3px solid var(--pad-c,#555)}
.klh-pad.on{color:var(--klh-ink);background:color-mix(in srgb,var(--pad-c,#e47fa7) 26%,transparent);border-color:var(--pad-c,#e47fa7)}
.klh-pad.snap.full{color:var(--klh-ink);border-color:#3a5bd0}
.klh-pad.hit{outline:2px solid var(--klh-ink);outline-offset:-2px}
.klh-map{display:flex;flex-direction:column;gap:3px}
.klh-row{display:grid;grid-template-columns:1fr auto auto;gap:6px;align-items:center}
.klh-row-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.klh-row-name small{color:var(--klh-ink3);margin-left:4px}
.klh-badges{display:flex;gap:3px}
.klh-badge{font-size:9.5px;padding:1px 4px;border-radius:3px;border:1px solid var(--klh-rule);color:var(--klh-ink2)}
.klh-badge.learned{border-color:var(--klh-accent);color:var(--klh-accent)}.klh-badge.picked{background:rgba(76,194,186,.16)}
.klh-chip{font:inherit;font-size:10px;padding:1px 6px;border-radius:9px;border:1px solid var(--klh-rule);background:transparent;
  color:var(--klh-ink2);cursor:pointer}
.klh-chip.armed{border-color:var(--klh-accent);color:var(--klh-ink);background:rgba(228,127,167,.2);animation:klh-pulse 1s infinite}
@keyframes klh-pulse{50%{background:rgba(228,127,167,.05)}}
.klh-opts{display:flex;flex-direction:column;gap:5px}
.klh-opts label{display:flex;align-items:center;gap:6px;color:var(--klh-ink2)}
.klh-opts select{font:inherit;font-size:11px;background:transparent;color:var(--klh-ink);border:1px solid var(--klh-rule);border-radius:4px}
.klh-collapsed .klh-body{display:none}
.klh-overlay{position:absolute;left:50%;bottom:9%;transform:translateX(-50%);min-width:280px;max-width:70%;padding:12px 18px 14px;
  border-radius:10px;background:rgba(10,11,14,.62);backdrop-filter:blur(8px);border:1px solid rgba(255,255,255,.1);
  color:#eef0f3;font:13px/1.3 "JetBrains Mono",Consolas,monospace;opacity:0;transition:opacity .35s ease;pointer-events:none;z-index:5}
.klh-overlay.show{opacity:1;transition:opacity .08s ease}
.klh-overlay .klh-read-val{font-size:30px}
.klh-overlay .klh-bar{height:8px}
@media (prefers-reduced-motion:reduce){.klh-chip.armed{animation:none}.klh-overlay,.klh-bar-fill{transition:none}}
`;

function el(doc, tag, cls, text) {
  const e = doc.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
// A host element with its own shadow root and the panel's CSS inside; returns [host, shadowRoot].
function isolated(doc, hostStyle) {
  const host = el(doc, "div", "klh-host");
  if (hostStyle) host.setAttribute("style", hostStyle);
  const shadow = host.attachShadow({ mode: "open" });
  const style = el(doc, "style");
  style.textContent = CSS;
  shadow.append(style);
  return [host, shadow];
}
const hueCss = (turn) => `hsl(${Math.round(turn * 360)} 70% 58%)`;

function sourceText(st) {
  if (st.source === "engine") return { dot: "up", text: "KeyLab via the VJ engine", button: false };
  if (st.source === "webmidi") return { dot: "midi", text: `KeyLab via Web MIDI (${st.inputs.length} input${st.inputs.length === 1 ? "" : "s"})`, button: false };
  if (st.engine === "connecting") return { dot: "", text: "Looking for the VJ engine...", button: false };
  if (st.midi === "needs-permission") return { dot: "", text: "No VJ engine. Allow Web MIDI to read the KeyLab directly.", button: true };
  if (st.midi === "denied") return { dot: "", text: "No VJ engine, and Web MIDI is blocked for this page (site settings).", button: false };
  if (st.midi === "unavailable") return { dot: "", text: "No VJ engine, and this browser has no Web MIDI.", button: false };
  if (st.midi === "no-inputs") return { dot: "", text: "Web MIDI is open but sees no KeyLab input.", button: false };
  return { dot: "", text: "KeyLab not connected yet.", button: st.midi !== "open" };
}

// Build the readout block (used in the panel and, larger, on the stage).
function readoutBlock(doc) {
  const root = el(doc, "div", "klh-read");
  const top = el(doc, "div", "klh-read-top");
  const ctl = el(doc, "span", "", "Move a fader or a knob");
  const how = el(doc, "span", "", "");
  top.append(ctl, how);
  const val = el(doc, "div", "klh-read-val", "");
  const bar = el(doc, "div", "klh-bar");
  const fill = el(doc, "div", "klh-bar-fill");
  const ghost = el(doc, "div", "klh-bar-ghost");
  bar.append(fill, ghost);
  const hint = el(doc, "div", "klh-hint", "");
  root.append(top, val, bar, hint);
  function paint(r) {
    if (!r) return;
    ctl.textContent = r.controlLabel ? `${r.controlLabel}${r.param ? " → " + r.label : ""}` : r.label || "";
    how.textContent = r.how === "learned" ? "learned" : r.how === "desk" ? (r.fine ? "desk · fine" : "desk") : r.how === "chord" ? "chord" : r.source === "peek" ? "touch" : "";
    val.textContent = r.param ? r.text : (r.text ? `${r.label} ${r.text}` : r.label || "");
    const pos = typeof r.pos === "number" ? r.pos : null;
    bar.style.visibility = pos === null && !r.pending ? "hidden" : "visible";
    bar.classList.toggle("pending", !!r.pending);
    if (r.pending) {
      fill.style.width = `${Math.round(r.pending.at * 1000) / 10}%`;
      ghost.style.left = `${Math.round(r.pending.want * 1000) / 10}%`;
      hint.textContent = `Move ${r.pending.dir} to ${r.text} to catch it`;
    } else {
      if (pos !== null) fill.style.width = `${Math.round(pos * 1000) / 10}%`;
      hint.textContent = r.source === "control" && !r.param ? "Not bound: press learn on a parameter, then move this control" : "";
    }
  }
  return { root, paint };
}

// opts: doc, client, binder, parent (default body), floating (default true when parent is body), overlay (an element
// to show the big readout in), title, map (true), pads (true), options (true), collapsed (false), onPadClick.
export function mountKeyLabHud(opts) {
  const doc = opts.doc || document;
  const { client, binder } = opts;
  const parent = opts.parent || doc.body;
  const floating = opts.floating ?? (parent === doc.body);
  const root = el(doc, "section", "klh" + (floating ? " klh-floating" : ""));
  root.setAttribute("aria-label", "KeyLab");
  const head = el(doc, "div", "klh-head");
  const dot = el(doc, "span", "klh-dot");
  const title = el(doc, "span", "klh-title", opts.title || "KeyLab");
  const allow = el(doc, "button", "klh-btn", "Use Web MIDI");
  allow.type = "button";
  allow.hidden = true;
  const fold = el(doc, "button", "klh-btn", "–");
  fold.type = "button";
  fold.title = "Fold the KeyLab panel";
  head.append(dot, title, allow, fold);
  const src = el(doc, "p", "klh-src", "");
  const body = el(doc, "div", "klh-body");
  root.append(head, src);   // the readout section goes between these and the body: it stays visible when folded

  const readSec = el(doc, "div", "klh-sec");
  const panelRead = readoutBlock(doc);
  readSec.append(panelRead.root);
  const chord = el(doc, "div", "klh-chord");
  const sw = el(doc, "span", "klh-swatch");
  const chordName = el(doc, "span", "klh-chord-name", "");
  const chordNote = el(doc, "span", "klh-src", "play a chord: its root turns the hue");
  chord.append(sw, chordName, chordNote);
  readSec.append(chord);
  root.append(readSec, body);

  let padsEls = null;
  if (opts.pads !== false) {
    const sec = el(doc, "div", "klh-sec");
    sec.append(el(doc, "p", "klh-sec-t", "Pads: 1-8 scenes, 9-12 snapshots (hold to store)"));
    const grid = el(doc, "div", "klh-pads");
    // the column count comes from the grid itself, so the panel cannot draw a different shape from PAD_GRID's rows
    grid.style.gridTemplateColumns = `repeat(${PAD_GRID[0].length}, minmax(0, 1fr))`;
    padsEls = new Map();
    for (const row of PAD_GRID) for (const pad of row) {
      const b = el(doc, "button", "klh-pad");
      b.type = "button";
      b.dataset.pad = String(pad);
      grid.append(b);
      padsEls.set(pad, b);
      b.addEventListener("click", (ev) => padClick(pad, ev.shiftKey));
      b.addEventListener("contextmenu", (ev) => { ev.preventDefault(); padClick(pad, true); });
    }
    sec.append(grid);
    body.append(sec);
  }

  let mapEl = null;
  if (opts.map !== false) {
    const sec = el(doc, "div", "klh-sec");
    sec.append(el(doc, "p", "klh-sec-t", "Map: learn, then move or touch a control"));
    mapEl = el(doc, "div", "klh-map");
    sec.append(mapEl);
    const clear = el(doc, "button", "klh-btn", "Forget learned controls");
    clear.type = "button";
    clear.style.marginTop = "6px";
    clear.addEventListener("click", () => binder.clearLearned());
    sec.append(clear);
    body.append(sec);
  }

  let optEls = null;
  if (opts.options !== false) {
    const sec = el(doc, "div", "klh-sec klh-opts");
    sec.append(el(doc, "p", "klh-sec-t", "Options"));
    const box = (key, text) => {
      const l = el(doc, "label");
      const c = el(doc, "input");
      c.type = "checkbox";
      c.addEventListener("change", () => binder.setOption(key, key === "layout" ? (c.checked ? "desk" : "none") : c.checked));
      l.append(c, doc.createTextNode(text));
      sec.append(l);
      return c;
    };
    const layout = box("layout", "Desk layout: fader n = parameter n, knob n trims it");
    const chordHue = box("chordHue", "Chord root turns the hue");
    const lights = box("lightPads", "Light the pads (through the VJ engine)");
    const screen = box("screen", "Show values on the KeyLab's screen (needs the engine's /api/screen)");
    const l = el(doc, "label");
    const smooth = el(doc, "select");
    for (const [v, t] of [[0, "instant"], [40, "snappy (40 ms)"], [80, "smooth (80 ms)"], [200, "glide (200 ms)"]]) {
      const o = el(doc, "option", "", t); o.value = String(v); smooth.append(o);
    }
    smooth.addEventListener("change", () => binder.setOption("smoothMs", Number(smooth.value)));
    l.append(doc.createTextNode("Smoothing "), smooth);
    sec.append(l);
    body.append(sec);
    optEls = { layout, chordHue, lights, screen, smooth };
  }
  const [hostEl, shadow] = isolated(doc);
  shadow.append(root);
  parent.append(hostEl);

  // ---- the stage overlay (its own shadow root, laid over the stage)
  let overlay = null, overlayTimer = null, overlayHost = null;
  if (opts.overlay) {
    overlay = readoutBlock(doc);
    overlay.root.className = "klh-overlay";
    let oshadow;
    [overlayHost, oshadow] = isolated(doc, "position:absolute;inset:0;pointer-events:none;z-index:5");
    oshadow.append(overlay.root);
    opts.overlay.append(overlayHost);
  }

  // ---- painting
  function paintStatus() {
    const st = client.status();
    const s = sourceText(st);
    dot.className = "klh-dot" + (s.dot ? " " + s.dot : "");
    src.textContent = s.text;
    allow.hidden = !s.button;
    if (optEls) {
      optEls.lights.disabled = st.source !== "engine";
      optEls.screen.disabled = st.source !== "engine";
      optEls.screen.parentElement.title = st.screen === "unsupported" ? "This VJ engine has no /api/screen yet: nothing is drawn" : "";
    }
  }
  function paintOptions() {
    if (!optEls) return;
    const o = binder.options;
    optEls.layout.checked = o.layout === "desk";
    optEls.chordHue.checked = !!o.chordHue;
    optEls.lights.checked = !!o.lightPads;
    optEls.screen.checked = !!o.screen;
    optEls.smooth.value = String([0, 40, 80, 200].includes(o.smoothMs) ? o.smoothMs : 80);
  }
  function paintMap() {
    if (!mapEl) return;
    const d = binder.describe();
    mapEl.textContent = "";
    for (const p of d.params) {
      const row = el(doc, "div", "klh-row");
      const name = el(doc, "span", "klh-row-name", p.label);
      name.append(el(doc, "small", "", p.text));
      const badges = el(doc, "span", "klh-badges");
      for (const c of p.controls) {
        const b = el(doc, "span", "klh-badge" + (c.how === "learned" ? " learned" : "") + (c.picked ? " picked" : ""), controlShort(c.control) + (c.fine ? "·" : ""));
        b.title = `${controlLabel(c.control)} (${c.how}${c.fine ? ", fine" : ""}${c.picked ? ", caught" : ""})`;
        badges.append(b);
      }
      const chip = el(doc, "button", "klh-chip" + (d.learning === p.id ? " armed" : ""), d.learning === p.id ? "touch a control" : "learn");
      chip.type = "button";
      chip.title = "Learn: click, then move or touch a fader or knob. Right-click forgets the learned ones.";
      chip.addEventListener("click", () => { binder.learn(p.id); paintMap(); });
      chip.addEventListener("contextmenu", (ev) => { ev.preventDefault(); binder.unbindParam(p.id); paintMap(); });
      row.append(name, badges, chip);
      mapEl.append(row);
    }
  }
  function paintPads(hitPad) {
    if (!padsEls) return;
    const scenes = scenesOf(), cur = sceneOf();
    for (const [pad, b] of padsEls) {
      b.className = "klh-pad";
      b.textContent = "";
      if (pad <= 8) {
        const sc = scenes[pad - 1];
        b.classList.add("scene");
        if (sc) {
          b.style.setProperty("--pad-c", sc.colour || "#e47fa7");
          if (sc.id === cur) b.classList.add("on");
        }
        b.append(el(doc, "b", "", `pad ${pad}`), el(doc, "span", "", sc ? sc.label : "\u2014"));
        b.title = sc ? `Pad ${pad}: ${sc.label}` : `Pad ${pad}: no scene`;
      } else {
        const slot = pad - 8;
        const full = binder.hasSnapshot(slot);
        b.classList.add("snap");
        if (full) b.classList.add("full");
        b.append(el(doc, "b", "", `pad ${pad}`), el(doc, "span", "", `Snap ${"ABCD"[slot - 1]}${full ? "" : " \u00b7 empty"}`));
        b.title = `Pad ${pad}: tap recalls snapshot ${"ABCD"[slot - 1]}, hold (or shift-click) stores it`;
      }
      if (pad === hitPad) b.classList.add("hit");
    }
  }
  const scenesOf = () => { try { return opts.scenes ? opts.scenes() : []; } catch { return []; } };
  const sceneOf = () => { try { return opts.scene ? opts.scene() : null; } catch { return null; } };
  function padClick(pad, store) {
    if (pad <= 8) {
      const sc = scenesOf()[pad - 1];
      if (sc) binder.selectScene(sc.id, `pad${pad}`);
    } else if (store) binder.storeSnapshot(pad - 8);
    else binder.recallSnapshot(pad - 8);
    paintPads(pad);
  }
  function showReadout(r) {
    panelRead.paint(r);
    if (overlay) {
      overlay.paint(r);
      overlay.root.classList.add("show");
      clearTimeout(overlayTimer);
      overlayTimer = setTimeout(() => overlay.root.classList.remove("show"), r.pending ? 2600 : 1500);
    }
    if (r.source === "learn" || r.source === "scene" || r.source === "snapshot") { paintMap(); paintPads(); }
  }

  const offs = [
    client.on("status", paintStatus),
    client.on("chord", (c) => {
      chordName.textContent = c.name || "";
      chordNote.textContent = typeof c.root === "number" && binder.options.chordHue ? "root → hue" : "";
      if (typeof c.root === "number") { sw.style.background = hueCss(fifthsTurn(c.root)); sw.classList.add("on"); }
    }),
    client.on("pad", (e) => { if (e.on) paintPads(e.pad); }),
    binder.on("readout", showReadout),
    binder.on("learn", paintMap),
    binder.on("bindings", () => { paintMap(); paintPads(); }),
    binder.on("options", () => { paintOptions(); paintStatus(); }),
    binder.on("snapshot", () => paintPads()),
    binder.on("scene", () => paintPads()),
  ];
  allow.addEventListener("click", () => client.connectMidi());
  fold.addEventListener("click", () => {
    root.classList.toggle("klh-collapsed");
    fold.textContent = root.classList.contains("klh-collapsed") ? "+" : "–";
  });
  if (opts.collapsed ?? floating) fold.click();   // on another page, start small: header, source and readout
  // the map's values change while you play: repaint it a few times a second, never per event
  const mapTimer = mapEl ? setInterval(() => { if (!root.classList.contains("klh-collapsed")) paintMap(); }, 400) : null;

  paintStatus(); paintOptions(); paintMap(); paintPads();
  return {
    root,
    refresh() { paintStatus(); paintOptions(); paintMap(); paintPads(); },
    destroy() { for (const off of offs) off(); clearInterval(mapTimer); clearTimeout(overlayTimer); hostEl.remove(); overlayHost?.remove(); },
  };
}

// Mirror the readout on the KeyLab's own screen through the engine (client.postScreen), while the option is on: a
// fader or knob you move or touch shows its parameter, its value and a bar. The client keeps the rate legal.
export function wireScreen(client, binder) {
  return binder.on("readout", (r) => {
    if (!binder.options.screen || client.source !== "engine" || !r.param || r.source === "scene") return;
    const knob = /^knob/.test(r.control || "");
    client.postScreen({ screen: knob ? "knob" : "fader", name: r.label, value: r.pending ? `-> ${r.text}` : r.text,
      level: Math.round((r.pending ? r.pending.at : (r.pos ?? 0)) * 127) });
  });
}

// Colour the pads through the VJ engine when something worth showing changes. Never on a timer: a scene change, a
// snapshot store, the option being switched on, or the engine coming up. The engine's governor keeps the rate legal.
export function wirePadLights(client, binder) {
  let last = "";
  const push = () => {
    if (!binder.options.lightPads || client.source !== "engine") return;
    const colors = binder.padColors();
    const key = colors.join(",");
    if (key === last) return;
    last = key;
    client.postPads(colors);
  };
  const offs = [binder.on("scene", push), binder.on("snapshot", push), binder.on("options", (o) => { if (o.lightPads) { last = ""; push(); } }),
    client.on("source", (e) => { if (e.source === "engine") { last = ""; push(); } })];
  return () => offs.forEach((f) => f());
}
