// Piano: the Studio drawer (studio.js + studio.css). One right-edge drawer inside #stage, outside the recorded canvas, with two
// tabs:
//   Practice  the exercise library (practice/library.js) as a family -> group -> exercise tree, played by practice/player.js
//             through the page's own cue player and Claude's voice as LOCAL cues. The drawer only calls the player, so
//             nothing reaches the practice log, the key tracker, the chord reader, the Nashville row, the staff or REC audio.
//   Looks     saved looks (looks/store.js: four built-in starters, then his own, favourites first) and the live visual
//             settings (looks/registry.js), always applied through the registry (its verified order, its REC refusal).
//
// Layout follows the deck (deck.js computeLayout and relayout, deck.js:1507-1552): 380 px wide (the deck's width, so swapping
// drawers never moves the canvas); it docks (.studio-dock on the stage, onLayout so the page refits the canvas) when the
// canvas's side margin is under 392 px and overlays that margin otherwise; the dock width is frozen while REC runs, and a
// Studio opened during REC overlays with a 44 px peek rail. The Studio and the deck share the right edge: opening one
// closes the other (the Studio watches #deck's data-open, as conversation-dock.js:20-22 does).
//
// House rule: every clickable blurs itself after a pointer click, so letter keys go back to the note keyboard. A click made
// from the keyboard (Enter or Space: event.detail is 0) keeps its focus, so Tab still walks the drawer.
//
// Keys (every letter is taken): ` toggles the Studio; Page Up / Page Down previous / next exercise; Home play or pause; End
// stop; Insert / Delete previous / next saved look. Ignored in form fields and with Ctrl, Meta or Alt held.
//
//   const studio = mountStudio({ stage, page: window.__piano, practice: { library, createPlayer }, looks: { registry, store },
//                                onLayout: () => fitCanvas() });
//   -> { open(tab), close(), toggle(), isOpen(), dockWidth(), frozen(v), destroy() }  plus handleKey(e), layout(), stats(),
//      ready (a promise: the saved looks loaded), element, player()
//
// practice.library: { FAMILIES, EXERCISES }. practice.createPlayer(opts): practice/player.js createExercisePlayer or a factory
// bound around it; it is called once with { cues, voice, now, onState, library, beforeStart } (page.cues, page.voice or
// page.cues.voice, page.beforeExerciseStart). The drawer uses load, play, pause, resume, stop, next, prev, playChord,
// showChord, setTranspose, setBpm, setLoops, setAutoAdvance, view and state.
// looks.registry: the registry module (LOOK_SETTINGS, snapshot, diff, applyLook, applySetting, recording).
// looks.store: createLooksStore() (load, list, status, save, rename, duplicate, setFavourite, delete).
//
// Page hooks, all optional (`page` is also the object the registry reads and sets): isRecording() (else the registry's
// recording(page), else stats().rec !== "idle"); framing() -> { w, h } or "9:16" (else stats().framing); canvas; pad();
// toast(text, isError); cues; voice or cues.voice ({ enabled, unlock() }); voiceEnabled(); unlock(); turnVoiceOn() (else a
// click on the top bar's #btn-cue-voice, the same toggle); minor() -> "tonic"|"relative"; jam.deck (else
// window.__piano.jam.deck); now(); beforeExerciseStart().

import { nashvilleFromName, parseKey, formatNumber } from "../nashville.js";
import { keyContext } from "../spell.js";

export const STUDIO_API = "arsenal.piano.studio/v1";
export const STUDIO_WIDTH = 380;     // the deck's width too (deck.js:30)
export const OVERLAY_MARGIN = 392;   // (stage width - canvas CSS width) / 2 at least this: the Studio overlays
export const RAIL_WIDTH = 44;        // the peek rail during REC
export const UI_KEY = "arsenal.piano.studio";
export const TABS = Object.freeze([["practice", "Practice"], ["looks", "Looks"]]);
export const SHORTCUTS = Object.freeze([
  { code: "Backquote", action: "toggle" },
  { code: "PageUp", action: "prev" }, { code: "PageDown", action: "next" },
  { code: "Home", action: "play-pause" }, { code: "End", action: "stop" },
  { code: "Insert", action: "look-prev" }, { code: "Delete", action: "look-next" },
]);
export const TEMPO = Object.freeze({ min: 30, max: 240, step: 2, big: 10 });
export const LOOPS = Object.freeze([1, 2, 4, Infinity]);
export const KEY_SHIFTS = Object.freeze([6, 5, 4, 3, 2, 1, 0, -1, -2, -3, -4, -5]);  // the player's 12 keys (transposeChoices), high to low
export const LEVELS = Object.freeze({
  foundation: { label: "Foundation", hint: "a first step: one idea, slow and clear" },
  build: { label: "Build", hint: "builds on the foundation: more chords or a new colour" },
  stretch: { label: "Stretch", hint: "longer, richer or less expected" },
});
export const NAME_MAX = 60;
// The Looks tab's groups and their order (the registry's LOOK_GROUPS ids; a setting keeps the registry's group).
export const LOOK_GROUPS = Object.freeze([
  { id: "scene", title: "Scene", ids: ["scheme", "instrument"] },
  { id: "atmosphere", title: "Atmosphere", ids: ["enabled", "theme", "weather", "harmonyMode", "intensity", "motion", "journey",
                                                 "harmony", "waveform", "autoWorld", "labels"] },
  { id: "colour", title: "Colour & numbers", ids: ["colour", "nns"] },
  { id: "frame", title: "Frame", ids: ["framing", "quality"] },
]);
// A short line under a setting that needs one. The label itself is the registry's (the Atmosphere panel's own words).
const SETTING_HINTS = {
  enabled: "The world around the keys",
  autoWorld: "The world changes by itself as the music moves",
  waveform: "Shows only when an audio input is connected",
  quality: "Sharper, and heavier on the graphics card",
};
const FRAMING_SIZE = { "9:16": { w: 1080, h: 1920 }, "16:9": { w: 1920, h: 1080 } };

// ------------------------------------------------------------------------------------------------ text helpers --
// (nameText and pullText as deck.js:82-89 and :165 print them, copied so the two drawers never share a lifecycle)
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;",
  '"': "&quot;", "'": "&#39;" })[c]);
const ACC_GLYPH = { b: "♭", bb: "𝄫", "#": "♯", "##": "𝄪" };
const mod = (a, n) => ((a % n) + n) % n;
const clampInt = (x, lo, hi) => Math.min(hi, Math.max(lo, Math.round(Number(x) || 0)));
export function nameText(name) {
  const s = String(name || "");
  const m = /^([A-G])(bb|##|b|#)?(.*?)(?:\/([A-G])(bb|##|b|#)?)?$/.exec(s);
  if (!m) return s;
  return m[1] + (ACC_GLYPH[m[2]] || "") + m[3].replace(/b(?=\d)/g, "♭").replace(/#/g, "♯") +
    (m[4] ? "/" + m[4] + (ACC_GLYPH[m[5]] || "") : "");
}
// A number drawn from nashville.js formatNumber's parts (the page's one formatter): quality and extensions raised, the
// bass degree a size smaller, never the text form's "^".
export function numberHtml(text) {
  const f = text ? formatNumber(String(text)) : null;
  if (!f) return esc(text || "");
  const glyph = (acc) => (acc > 0 ? "♯".repeat(acc) : "♭".repeat(-acc));
  return f.parts.map((p) => {
    if (p.role === "degree") return `${glyph(p.acc)}${esc(p.num)}`;
    if (p.role === "sup") return `<sup>${esc(p.text).replace(/b(?=\d)/g, "♭").replace(/#/g, "♯")}</sup>`;
    if (p.role === "slash") return "/";
    if (p.role === "dash") return "–";
    if (p.role === "bass") return `<span class="num-bass">${glyph(p.acc)}${esc(p.num)}</span>`;
    return esc(p.text);
  }).join("");
}
const pullText = (s) => String(s || "").replace(/\b([A-G])b\b/g, "$1♭").replace(/\b([A-G])#/g, "$1♯").replace(/(^|[\s(])#(\d)/g, "$1♯$2");
const keyText = (k) => String(k || "").replace(/^([A-G])(b|#)/, (m0, l, a) => l + ACC_GLYPH[a]);
const shortKey = (k) => keyText(String(k || "").replace(/ major$/, "").replace(/ minor$/, "m"));
const fold = (s) => String(s || "").toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "");
const tokens = (q) => fold(q).split(/\s+/).filter(Boolean);
const ICON = {
  prev: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="2" y="3" width="2" height="10"/><path d="M14 3v10L5 8z"/></svg>',
  next: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="12" y="3" width="2" height="10"/><path d="M2 3v10l9-5z"/></svg>',
  play: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11L13.5 8z"/></svg>',
  pause: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3.5" y="2.5" width="3" height="11"/><rect x="9.5" y="2.5" width="3" height="11"/></svg>',
  stop: '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="3" width="10" height="10"/></svg>',
};

// ------------------------------------------------------------------------------------------------ the drawer --
export function mountStudio({
  stage, page = {}, practice = {}, looks = {}, onLayout = () => {},
  deck = null, storage = null, now = null, keys = true, tickMs = 250, root = null,
} = {}) {
  if (!stage) throw new Error("mountStudio needs the stage element");
  page = page || {};
  const doc = stage.ownerDocument;
  const win = doc.defaultView;
  const warn = (what, e) => console.warn(`[studio] ${what}:`, e && (e.message || e));
  const safe = (fn, fallback = null) => { try { return fn(); } catch (e) { warn("hook failed", e); return fallback; } };
  const hook = (name) => (typeof page[name] === "function" ? page[name].bind(page) : null);
  const clock = typeof now === "function" ? now : hook("now") || (() => win.performance.now());
  const store = storage || {
    get(k) { try { return win.localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { win.localStorage.setItem(k, v); } catch { /* storage blocked */ } },
  };
  const blurAfter = (e, el) => { if (el && (!e || e.detail !== 0)) el.blur(); };
  const settled = (p) => { if (p && typeof p.then === "function") p.then(null, (e) => warn("player", e)); return p; };

  // ------------------------------------------------------------------------------------------ remembered UI --
  const ui = (() => { try { return JSON.parse(store.get(UI_KEY) || "{}") || {}; } catch { return {}; } })();
  let saveT = 0;
  function saveUi() {
    clearTimeout(saveT);
    saveT = setTimeout(() => {
      store.set(UI_KEY, JSON.stringify({
        tab: S.tab, exercise: P.exerciseId, libraryOpen: P.libraryOpen, openFamilies: [...P.openFamilies],
        closedGroups: [...P.closedGroups], transpose: P.transpose, loops: P.loops === Infinity ? "forever" : P.loops,
        autoAdvance: P.autoAdvance, look: L.active,
      }));
    }, 120);
  }

  // ------------------------------------------------------------------------------------------ page hooks --
  const registry = looks.registry || null;
  const lstore = looks.store || null;
  function isRecording() {
    const h = hook("isRecording");
    if (h) return !!safe(h, false);
    if (registry && typeof registry.recording === "function") return !!safe(() => registry.recording(page), false);
    const st = typeof page.stats === "function" ? safe(() => page.stats()) : null;
    return !!(st && st.rec && st.rec !== "idle");
  }
  const voiceObj = () => page.voice || (page.cues && page.cues.voice) || null;
  function voiceEnabled() {
    const h = hook("voiceEnabled");
    if (h) return !!safe(h, true);
    const v = voiceObj();
    return !v || v.enabled !== false;
  }
  // Called first thing in a click handler (before any await), so the browser still counts the click as the gesture.
  async function unlockVoice() {
    const h = hook("unlock");
    const v = voiceObj();
    const fn = h || (v && typeof v.unlock === "function" ? () => v.unlock() : null);
    if (!fn) return;
    try {
      await Promise.race([Promise.resolve(fn()), new Promise((r) => setTimeout(r, 1500))]);
    } catch (e) { warn("voice unlock", e); }
  }
  async function turnVoiceOn() {
    const h = hook("turnVoiceOn");
    if (h) { await safe(h); return; }
    const btn = doc.getElementById("btn-cue-voice");  // the top bar's own toggle (piano.js wireCueUi)
    if (btn) { btn.click(); return; }
    const v = voiceObj();
    if (v && typeof v.setEnabled === "function") { v.setEnabled(true); await unlockVoice(); }
  }
  const say = (text, isError = false) => { const t = hook("toast"); if (t) safe(() => t(text, isError)); };
  const deckApi = () => deck || (page.jam && page.jam.deck) || (win.__piano && win.__piano.jam && win.__piano.jam.deck) || null;
  // the page's Minor setting: the hook, else the top bar's own menu (piano.html #minor-select), read cheaply at 4 Hz
  const minorNow = () => {
    const h = hook("minor");
    const v = h ? safe(h) : doc.getElementById("minor-select") ? doc.getElementById("minor-select").value : "tonic";
    return v === "relative" ? "relative" : "tonic";
  };

  // ------------------------------------------------------------------------------------------ state --
  const S = { tab: TABS.some(([id]) => id === ui.tab) ? ui.tab : "practice", open: false, peek: false,
              lastDock: 0, frozenDock: null, forced: false, recording: false, layout: null, destroyed: false };
  const lib = practice.library || {};
  const FAMILIES = Array.isArray(lib.FAMILIES) ? lib.FAMILIES : [];
  const EXERCISES = Array.isArray(lib.EXERCISES) ? lib.EXERCISES : [];
  const byId = new Map(EXERCISES.map((e) => [e.id, e]));
  const placeOf = new Map();  // exercise id -> { family, group }
  for (const f of FAMILIES) for (const g of f.groups || []) {
    for (const id of g.exercises || []) if (!placeOf.has(id)) placeOf.set(id, { family: f, group: g });
  }
  const ORDER = FAMILIES.flatMap((f) => (f.groups || []).flatMap((g) => g.exercises || [])).filter((id) => byId.has(id));
  const neighbour = (id, dir) => {
    const i = ORDER.indexOf(id);
    const j = i + (dir < 0 ? -1 : 1);
    return i >= 0 && j >= 0 && j < ORDER.length ? byId.get(ORDER[j]) : null;
  };
  const P = {
    exerciseId: byId.has(ui.exercise) ? ui.exercise : null, loaded: null, state: null, search: "", shown: null,
    libraryOpen: ui.libraryOpen !== false, openFamilies: new Set(Array.isArray(ui.openFamilies) ? ui.openFamilies : []),
    closedGroups: new Set(Array.isArray(ui.closedGroups) ? ui.closedGroups : []),
    transpose: KEY_SHIFTS.includes(ui.transpose) ? ui.transpose : 0,
    loops: ui.loops === "forever" ? Infinity : [1, 2, 4].includes(ui.loops) ? ui.loops : 1, autoAdvance: !!ui.autoAdvance,
    bpm: null, nowIndex: null, notice: "", noticeT: 0,
  };
  const L = { list: [], status: null, active: typeof ui.look === "string" ? ui.look : null, snap: null, changed: [],
              busy: false, form: null, applying: null };

  // ------------------------------------------------------------------------------------------ DOM --
  const aside = root || doc.createElement("aside");
  aside.id = aside.id || "studio";
  aside.classList.add("studio");
  aside.setAttribute("aria-label", "Studio");
  aside.innerHTML = `
    <button type="button" class="studio-tab" aria-label="Open the Studio: practice and looks (\` key)" title="Studio: practice and looks (\` key)"><span class="studio-tab-text">STUDIO</span><span class="studio-tab-dot" hidden></span></button>
    <div class="studio-panel">
      <header class="studio-head">
        <div class="studio-tabs" role="tablist" aria-label="Studio">
          ${TABS.map(([id, label]) => `<button type="button" role="tab" class="studio-tabbtn" data-tab="${id}" id="studio-tab-${id}" aria-controls="studio-pane-${id}">${label}</button>`).join("")}
        </div>
        <button type="button" class="studio-x" data-act="close" aria-label="Close the Studio" title="Close the Studio (\` key)">&times;</button>
      </header>

      <section class="studio-pane sp" id="studio-pane-practice" role="tabpanel" aria-labelledby="studio-tab-practice" data-pane="practice">
        <div class="studio-notice sp-voice" hidden role="status">
          <span class="studio-notice-text">Claude's voice is off, so you will see the chords but not hear them.</span>
          <button type="button" class="studio-btn studio-strong" data-act="voice-on">Turn sound on</button>
        </div>
        <div class="studio-notice sp-noplayer" hidden role="status"><span class="studio-notice-text">Playback isn't available on this page yet. You can still read the exercises.</span></div>
        <div class="sp-library" data-open="true">
          <button type="button" class="sp-libhead" data-act="library" aria-expanded="true">
            <span class="studio-caret" aria-hidden="true"></span><span class="studio-kicker">Exercises</span>
            <span class="sp-libwhere"></span><span class="sp-libcount"></span>
          </button>
          <div class="sp-libbody">
            <input type="search" class="studio-find sp-find" placeholder="Find by name, key, chord or idea" aria-label="Find an exercise" spellcheck="false" autocomplete="off" />
            <div class="sp-tree"></div>
            <p class="studio-empty sp-empty" hidden>Nothing matches. Try a key (G major), a chord (maj7) or an idea (pedal).</p>
          </div>
        </div>
        <div class="sp-exercise">
          <div class="sp-none">
            <p class="sp-none-title">Pick an exercise above.</p>
            <p>Click a chord to hear it, or press Play to hear the whole progression. Exercises play through Claude's voice and are never written to your practice log.</p>
          </div>
          <div class="sp-body" hidden>
            <p class="sp-where"></p>
            <div class="sp-titlerow"><h2 class="sp-title"></h2><span class="sp-levelbox"></span></div>
            <div class="sp-controls">
              <span class="studio-label" id="studio-key-label">Key</span>
              <select class="studio-select sp-key" aria-labelledby="studio-key-label"></select>
              <span class="studio-label" id="studio-tempo-label">Tempo</span>
              <span class="sp-tempo" role="group" aria-labelledby="studio-tempo-label">
                <button type="button" class="studio-btn sp-step" data-act="slower" aria-label="Slower" title="Slower (shift-click: 10 slower)">&minus;</button>
                <span class="sp-bpm"><b class="sp-bpmnum"></b> bpm</span>
                <button type="button" class="studio-btn sp-step" data-act="faster" aria-label="Faster" title="Faster (shift-click: 10 faster)">+</button>
                <button type="button" class="studio-link sp-bpmreset" data-act="tempo-reset" title="Back to the tempo the exercise is written at" hidden></button>
              </span>
              <span class="studio-label" id="studio-repeat-label">Repeat</span>
              <span class="studio-seg sp-loops" role="group" aria-labelledby="studio-repeat-label">${LOOPS.map((n) => `<button type="button" class="studio-segbtn" data-act="loops" data-loops="${n === Infinity ? "forever" : n}" aria-pressed="false" title="${n === Infinity ? "Repeat until you stop" : n === 1 ? "Play once" : `Play ${n} times`}">${n === Infinity ? "∞" : `${n}×`}</button>`).join("")}</span>
              <span aria-hidden="true"></span>
              <button type="button" class="studio-switch sp-auto" role="switch" aria-checked="false" data-act="auto" title="When this exercise ends, go straight on to the next one">
                <span class="studio-knob" aria-hidden="true"></span><span>Then play the next exercise</span>
              </button>
            </div>
            <div class="sp-chips" role="group" aria-label="Chords"></div>
            <p class="sp-chiphint">Click a chord to hear it. Shift-click shows it on the keys without sound.</p>
            <dl class="sp-notes"></dl>
            <p class="sp-tags"></p>
          </div>
        </div>
        <footer class="sp-transport">
          <div class="sp-buttons">
            <button type="button" class="studio-btn sp-tbtn" data-act="prev" aria-label="Previous exercise (Page Up)" title="Previous exercise (Page Up)">${ICON.prev}</button>
            <button type="button" class="studio-btn sp-tbtn sp-play" data-act="play-pause" title="Play (Home)"><span class="sp-playicon">${ICON.play}</span><span class="sp-playtext">Play</span></button>
            <button type="button" class="studio-btn sp-tbtn" data-act="next" aria-label="Next exercise (Page Down)" title="Next exercise (Page Down)">${ICON.next}</button>
            <button type="button" class="studio-btn sp-tbtn sp-stop" data-act="stop" title="Stop (End)">${ICON.stop}<span>Stop</span></button>
          </div>
          <p class="sp-status" role="status" aria-live="polite"></p>
        </footer>
      </section>

      <section class="studio-pane sl" id="studio-pane-looks" role="tabpanel" aria-labelledby="studio-tab-looks" data-pane="looks">
        <div class="studio-notice sl-rec" hidden role="status"><span class="sl-recdot" aria-hidden="true"></span>
          <span class="studio-notice-text">Recording. Saved looks, and the settings marked locked, wait until you stop.</span></div>
        <div class="studio-notice sl-unavailable" hidden role="status"><span class="studio-notice-text"></span></div>
        <section class="sl-presets" aria-label="Saved looks">
          <div class="sl-headrow"><span class="studio-kicker">Favourites</span><span class="sl-source" role="status"></span></div>
          <div class="sl-chips sl-favs" role="group" aria-label="Favourite looks: click one to use it"></div>
          <div class="sl-otherwrap" hidden>
            <div class="sl-headrow"><span class="studio-kicker">Your other looks</span></div>
            <div class="sl-chips sl-others" role="group" aria-label="Your other looks: click one to use it"></div>
          </div>
          <div class="sl-using" hidden>
            <span class="sl-dot" aria-hidden="true"></span><span class="sl-usingtext"></span>
            <span class="sl-usingacts">
              <button type="button" class="studio-btn" data-act="look-update">Save changes</button>
              <button type="button" class="studio-btn" data-act="look-revert">Undo changes</button>
            </span>
          </div>
          <div class="sl-actions">
            <button type="button" class="studio-btn studio-strong" data-act="look-save-as">Save current as&hellip;</button>
            <button type="button" class="studio-btn sl-fav" data-act="look-favourite" aria-pressed="false"><span class="sl-star" aria-hidden="true">&#9734;</span>Favourite</button>
            <button type="button" class="studio-btn" data-act="look-rename">Rename</button>
            <button type="button" class="studio-btn" data-act="look-duplicate">Duplicate</button>
            <button type="button" class="studio-btn" data-act="look-delete">Delete</button>
          </div>
          <form class="sl-form" hidden autocomplete="off">
            <label class="sl-formlabel"><span class="studio-label sl-formtitle">Name</span>
              <input type="text" class="studio-input sl-name" maxlength="${NAME_MAX}" spellcheck="false" /></label>
            <span class="sl-formacts"><button type="submit" class="studio-btn studio-strong sl-formok">Save</button>
              <button type="button" class="studio-btn" data-act="form-cancel">Cancel</button></span>
          </form>
          <div class="sl-confirm" hidden role="alertdialog" aria-label="Delete this look?">
            <span class="sl-confirmtext"></span>
            <span class="sl-formacts"><button type="button" class="studio-btn studio-danger" data-act="look-delete-yes">Delete</button>
              <button type="button" class="studio-btn" data-act="look-delete-no">Keep it</button></span>
          </div>
          <p class="sl-msg" hidden role="status"></p>
        </section>
        <div class="sl-controls"></div>
      </section>
    </div>
    <button type="button" class="studio-peek" hidden aria-label="Peek the Studio">&#8249;</button>`;
  if (!aside.parentNode) stage.appendChild(aside);
  const $ = (sel) => aside.querySelector(sel);
  const tabBtn = $(".studio-tab"), tabDot = $(".studio-tab-dot"), peekBtn = $(".studio-peek"), tabsEl = $(".studio-tabs");
  // practice
  const voiceNote = $(".sp-voice"), noPlayerNote = $(".sp-noplayer"), libEl = $(".sp-library"), libHead = $(".sp-libhead");
  const libWhere = $(".sp-libwhere"), libCount = $(".sp-libcount"), findEl = $(".sp-find"), treeEl = $(".sp-tree");
  const emptyEl = $(".sp-empty"), noneEl = $(".sp-none"), bodyEl = $(".sp-body"), whereEl = $(".sp-where");
  const titleEl = $(".sp-title"), levelBox = $(".sp-levelbox"), keySel = $(".sp-key"), bpmNum = $(".sp-bpmnum");
  const bpmReset = $(".sp-bpmreset"), loopsEl = $(".sp-loops"), autoEl = $(".sp-auto"), chipsEl = $(".sp-chips");
  const notesEl = $(".sp-notes"), tagsEl = $(".sp-tags"), transportEl = $(".sp-transport"), playBtn = $(".sp-play");
  const statusEl = $(".sp-status");
  // looks
  const recNote = $(".sl-rec"), unavailNote = $(".sl-unavailable"), presetsEl = $(".sl-presets"), sourceEl = $(".sl-source");
  const favChips = $(".sl-favs"), otherWrap = $(".sl-otherwrap"), otherChips = $(".sl-others"), usingEl = $(".sl-using");
  const usingText = $(".sl-usingtext"), usingDot = $(".sl-using .sl-dot"), actionsEl = $(".sl-actions");
  const formEl = $(".sl-form"), formTitle = $(".sl-formtitle"), nameEl = $(".sl-name"), formOk = $(".sl-formok");
  const confirmEl = $(".sl-confirm"), confirmText = $(".sl-confirmtext"), msgEl = $(".sl-msg"), controlsEl = $(".sl-controls");

  // ------------------------------------------------------------------------------------------ the player --
  let player = null;
  const status = () => (P.state && P.state.status) || "idle";
  function pull() {
    if (!player) return P.state;
    const s = typeof player.state === "function" ? safe(() => player.state()) : null;
    if (s && typeof s === "object") P.state = { ...(P.state || {}), ...s };
    return P.state;
  }
  function onPlayerState(s) {
    if (!s || typeof s !== "object" || S.destroyed) return;
    P.state = { ...s };
    if (s.exerciseId && byId.has(s.exerciseId) && s.exerciseId !== P.loaded) {
      // the player moved on by itself (auto-advance) or through next / prev
      P.loaded = s.exerciseId;
      if (P.exerciseId !== s.exerciseId) {
        P.exerciseId = s.exerciseId;
        P.bpm = null;
        P.shown = null;
        revealExercise(s.exerciseId);
        saveUi();
      }
      renderTree();
      renderExercise();
      scrollTreeTo(s.exerciseId);
      return;
    }
    paintPractice();
  }
  if (typeof practice.createPlayer === "function") {
    try {
      player = practice.createPlayer({ cues: page.cues || null, voice: voiceObj(), now: clock, onState: onPlayerState,
                                       library: lib, beforeStart: hook("beforeExerciseStart") });
    } catch (e) { warn("the exercise player could not start", e); player = null; }
  }
  const call = (name, ...args) => (player && typeof player[name] === "function" ? settled(safe(() => player[name](...args))) : undefined);
  // The chords as they will sound (transposed and respelled by the player), or the written ones when nothing is loaded.
  function viewNow(ex) {
    if (player && ex && P.loaded === ex.id) {
      const v = typeof player.view === "function" ? safe(() => player.view()) : player.view;
      if (v && Array.isArray(v.chords) && v.id === ex.id) return v;
    }
    return { id: ex.id, key: keyAt(ex.key, P.transpose), bpm: P.bpm || ex.bpm, chords: ex.chords, written: true };
  }
  function loadIntoPlayer(thenPlay = false) {
    const ex = byId.get(P.exerciseId);
    if (!player || !ex) return;
    P.loaded = ex.id;
    call("load", ex, { transpose: P.transpose, bpm: P.bpm, loops: P.loops, autoAdvance: P.autoAdvance });
    pull();
    if (thenPlay) call("play");
  }
  function ensureLoaded() {
    if (!P.exerciseId && ORDER.length) { P.exerciseId = ORDER[0]; revealExercise(P.exerciseId); renderTree(); renderExercise(); }
    if (P.exerciseId && P.loaded !== P.exerciseId) loadIntoPlayer(false);
  }
  // A live change (key, tempo, repeat, auto-advance): the player's setter re-times what has not sounded yet.
  function retune(setter, value) {
    if (!player || P.loaded !== P.exerciseId) return;
    if (typeof player[setter] === "function") { call(setter, value); pull(); return; }
    loadIntoPlayer(status() === "playing");
  }

  // ------------------------------------------------------------------------------------------ keys and names --
  function keyAt(keyName, semis) {
    if (!semis) return keyName;
    const k = keyContext(keyName);
    return k ? keyContext({ tonic: mod(k.tonic + semis, 12), mode: k.mode }).name : keyName;
  }
  function keyOptions(ex) {
    if (!parseKey(ex.key || "")) return [{ semis: 0, label: ex.key || "as written" }];
    return KEY_SHIFTS.map((s) => ({
      semis: s,
      label: s === 0 ? `${keyText(ex.key)} · as written` : `${keyText(keyAt(ex.key, s))} · ${s > 0 ? "up" : "down"} ${Math.abs(s)}`,
    }));
  }
  function chordNumber(c, v) {
    const k = parseKey(v.key || "");
    if (k && k.mode === "minor" && minorNow() === "relative") {
      try {
        const r = nashvilleFromName(c.name, v.key, { minor: "relative" });
        if (r && r.kind === "chord" && r.text) return r.text;
      } catch { /* the written number */ }
    }
    return c.number;
  }

  // ------------------------------------------------------------------------------------------ the tree --
  function matches(ex, q) {
    if (!q.length) return true;
    const place = placeOf.get(ex.id);
    const hay = fold([ex.title, ex.key, shortKey(ex.key), ex.level, ...(ex.tags || []), place && place.family.title,
      place && place.group.title, ...(ex.chords || []).flatMap((c) => [c.name, c.number])].join(" "));
    return q.every((t) => hay.includes(t));
  }
  function levelHtml(level, withWord = false) {
    const lv = LEVELS[level];
    if (!lv) return "";
    return `<span class="studio-level" data-level="${esc(level)}" title="${esc(`${lv.label}: ${lv.hint}`)}">` +
      `<span class="studio-bars" aria-hidden="true"><i></i><i></i><i></i></span>` +
      `<span class="${withWord ? "studio-levelword" : "studio-sr"}">${esc(lv.label)}</span></span>`;
  }
  function renderTree() {
    const q = tokens(P.search);
    let shown = 0;
    const st = status();
    const sounding = st === "playing" || st === "paused" ? P.loaded : null;
    treeEl.innerHTML = FAMILIES.map((f) => {
      let count = 0;
      const groups = (f.groups || []).map((g) => {
        const exs = (g.exercises || []).map((id) => byId.get(id)).filter((ex) => ex && matches(ex, q));
        if (!exs.length && q.length) return "";
        count += exs.length;
        const gkey = `${f.id}/${g.id}`;
        const gOpen = q.length > 0 || !P.closedGroups.has(gkey);
        return `<div class="sp-grp">
          <button type="button" class="sp-grphead" data-act="group" data-group="${esc(gkey)}" aria-expanded="${gOpen}" title="${esc(g.blurb || "")}">
            <span class="studio-caret" aria-hidden="true"></span><span class="sp-grptitle">${esc(g.title)}</span><span class="sp-count">${exs.length}</span></button>
          ${gOpen ? `<ul class="sp-exlist">${exs.map((ex) => `<li><button type="button" class="sp-ex" data-act="exercise" data-id="${esc(ex.id)}"
              aria-current="${ex.id === P.exerciseId}" data-playing="${ex.id === sounding}">
              ${levelHtml(ex.level)}<span class="sp-extitle">${esc(pullText(ex.title))}</span>
              <span class="sp-exmeta">${esc(shortKey(ex.key))}</span><span class="sp-exnow" aria-hidden="true"></span></button></li>`).join("")}</ul>` : ""}
        </div>`;
      }).join("");
      if (q.length && !count) return "";
      shown += count;
      const fOpen = q.length > 0 || P.openFamilies.has(f.id);
      return `<div class="sp-fam">
        <button type="button" class="sp-famhead" data-act="family" data-family="${esc(f.id)}" aria-expanded="${fOpen}">
          <span class="studio-caret" aria-hidden="true"></span><span class="sp-famtitle">${esc(f.title)}</span><span class="sp-count">${count}</span></button>
        ${fOpen ? `${f.blurb && !q.length ? `<p class="sp-blurb">${esc(pullText(f.blurb))}</p>` : ""}<div class="sp-groups">${groups}</div>` : ""}
      </div>`;
    }).join("");
    emptyEl.hidden = !(q.length && !shown);
    const ex = byId.get(P.exerciseId);
    libWhere.textContent = !P.libraryOpen && ex ? pullText(ex.title) : "";
    libCount.textContent = P.libraryOpen ? String(ORDER.length) : "";
    libEl.dataset.open = String(P.libraryOpen);
    libHead.setAttribute("aria-expanded", String(P.libraryOpen));
  }
  function revealExercise(id) {
    const place = placeOf.get(id);
    if (!place) return;
    P.openFamilies.add(place.family.id);
    P.closedGroups.delete(`${place.family.id}/${place.group.id}`);
  }
  function scrollTreeTo(id) {
    const b = [...treeEl.querySelectorAll(".sp-ex")].find((el) => el.dataset.id === id);
    if (b && P.libraryOpen && S.open) b.scrollIntoView({ block: "nearest" });
  }

  // ------------------------------------------------------------------------------------------ the exercise --
  function renderExercise() {
    const ex = byId.get(P.exerciseId);
    noneEl.hidden = !!ex;
    bodyEl.hidden = !ex;
    if (!ex) { chipsEl.innerHTML = ""; chipsEl.dataset.exercise = ""; paintPractice(); return; }
    const place = placeOf.get(ex.id);
    whereEl.textContent = place ? `${place.family.title} › ${place.group.title}` : "";
    titleEl.textContent = pullText(ex.title);
    levelBox.innerHTML = levelHtml(ex.level, true);
    keySel.innerHTML = keyOptions(ex).map((o) => `<option value="${o.semis}">${esc(o.label)}</option>`).join("");
    keySel.value = String(P.transpose);
    const notes = [["The idea", ex.concept], ["Listen for", ex.listenFor], ["Left hand", ex.leftHand], ["Try next", ex.variation]]
      .filter(([, t]) => t);
    notesEl.innerHTML = notes.map(([h, t]) => `<div class="sp-note"><dt>${h}</dt><dd>${esc(pullText(t))}</dd></div>`).join("");
    tagsEl.innerHTML = (ex.tags || []).map((t) => `<span class="studio-tag">${esc(pullText(t))}</span>`).join("");
    tagsEl.hidden = !(ex.tags || []).length;
    renderChips();
    paintPractice();
  }
  function renderChips() {
    const ex = byId.get(P.exerciseId);
    if (!ex) return;
    const v = viewNow(ex);
    const beatMs = 60000 / (v.bpm || ex.bpm || 60);
    Object.assign(chipsEl.dataset, { key: v.key || "", bpm: String(v.bpm || ""), exercise: ex.id, source: v.written ? "written" : "player",
                                     minor: minorNow() });
    chipsEl.innerHTML = (v.chords || []).map((c, i) => {
      const n = chordNumber(c, v);
      const dur = Number.isFinite(c.durMs) ? c.durMs : c.beats * beatMs;
      const beats = `${c.beats} beat${c.beats === 1 ? "" : "s"}`;
      return `<button type="button" class="sp-chip" data-i="${i}" style="--chord-ms:${Math.round(dur)}ms"
          aria-label="${esc(`${nameText(c.name)}, ${formatNumber(n) ? formatNumber(n).display : n || ""}, ${beats}${c.pedal === "hold" ? ", hold the pedal" : ""}`)}">
        <span class="sp-chipname">${esc(nameText(c.name))}</span>
        <span class="sp-chipnum">${numberHtml(n)}</span>
        <span class="sp-chipbeats">${beats}${c.pedal === "hold" ? " · hold" : ""}</span>
        <span class="sp-chipbar" aria-hidden="true"></span></button>`;
    }).join("");
    P.nowIndex = null;
  }
  function paintPractice() {
    const ex = byId.get(P.exerciseId);
    const s = P.state || {};
    const st = status();
    const same = !!ex && P.loaded === ex.id && (!s.exerciseId || s.exerciseId === ex.id);
    // chips follow the player: a new key respells them, a new tempo re-times their bars, the Minor setting renumbers them
    if (ex && (chipsEl.dataset.exercise !== ex.id || chipsEl.dataset.minor !== minorNow() ||
        (same && (chipsEl.dataset.source === "written" || (s.key && s.key !== chipsEl.dataset.key) ||
                  (s.bpm && String(s.bpm) !== chipsEl.dataset.bpm))))) renderChips();
    const idx = same && Number.isInteger(s.index) ? s.index : null;
    const nowIdx = st === "playing" ? idx : null;
    [...chipsEl.children].forEach((b, i) => {
      b.dataset.now = String(nowIdx === i);
      b.dataset.held = String(st === "paused" && idx === i);
      b.dataset.shown = String(P.shown === i);
    });
    if (nowIdx !== P.nowIndex) {
      P.nowIndex = nowIdx;
      const b = nowIdx != null ? chipsEl.children[nowIdx] : null;
      if (b) { b.classList.remove("run"); void b.offsetWidth; b.classList.add("run"); }
    }
    // transport
    const playing = st === "playing", paused = st === "paused";
    playBtn.querySelector(".sp-playicon").innerHTML = playing ? ICON.pause : ICON.play;
    playBtn.querySelector(".sp-playtext").textContent = playing ? "Pause" : paused ? "Resume" : "Play";
    playBtn.title = `${playing ? "Pause" : paused ? "Resume" : "Play"} (Home)`;
    playBtn.dataset.state = st;
    playBtn.disabled = !player || !ORDER.length;
    transportEl.querySelector('[data-act="stop"]').disabled = !player || !(playing || paused);
    const at = ex ? ORDER.indexOf(ex.id) : -1;
    transportEl.querySelector('[data-act="prev"]').disabled = !ORDER.length || at === 0;
    transportEl.querySelector('[data-act="next"]').disabled = !ORDER.length || (at >= 0 && at === ORDER.length - 1);
    // header controls
    if (ex) {
      const bpm = P.bpm || (same && s.bpm) || ex.bpm;
      bpmNum.textContent = String(Math.round(bpm));
      bpmReset.hidden = !(P.bpm && P.bpm !== ex.bpm);
      bpmReset.textContent = `back to ${ex.bpm}`;
      if (doc.activeElement !== keySel) keySel.value = String(P.transpose);
      const loopsText = P.loops === Infinity ? "forever" : String(P.loops);
      for (const b of loopsEl.children) b.setAttribute("aria-pressed", String(b.dataset.loops === loopsText));
      autoEl.setAttribute("aria-checked", String(P.autoAdvance));
    }
    statusEl.textContent = statusText(ex, s, st, same);
    statusEl.dataset.state = st;
    for (const b of treeEl.querySelectorAll(".sp-ex")) b.dataset.playing = String((playing || paused) && b.dataset.id === P.loaded);
    tabDot.hidden = !(playing && !S.open);
    paintVoice();
  }
  function statusText(ex, s, st, same) {
    if (P.notice) return P.notice;
    if (!ex) return ORDER.length ? "Pick an exercise, or press Play to start with the first one." : "No exercises are installed.";
    const v = viewNow(ex);
    const total = (v.chords || []).length;
    const at = same && Number.isInteger(s.index) ? s.index + 1 : 1;
    const pass = same && Number.isInteger(s.pass) ? s.pass + 1 : 1;
    const passText = P.loops === Infinity ? ` · time ${pass}, repeating` : P.loops > 1 ? ` · time ${pass} of ${P.loops}` : "";
    if (st === "playing") return `Playing chord ${at} of ${total}${passText}`;
    if (st === "paused") return `Paused on chord ${at} of ${total}. Play carries on from here.`;
    if (st === "stopped") {
      if (s.reason === "cleared") return "Stopped: the sound was hushed.";
      if (s.reason === "ended") return "Finished. Press Play to hear it again.";
      return "Stopped.";
    }
    return `${total} chord${total === 1 ? "" : "s"} in ${keyText(v.key || ex.key)} at ${Math.round(P.bpm || v.bpm || ex.bpm)} bpm.`;
  }
  function flashNotice(text, ms = 3200) {
    P.notice = text;
    clearTimeout(P.noticeT);
    P.noticeT = setTimeout(() => { P.notice = ""; paintPractice(); }, ms);
    paintPractice();
  }
  function paintVoice() {
    voiceNote.hidden = !player || voiceEnabled();
    noPlayerNote.hidden = !!player;
  }

  // ------------------------------------------------------------------------------------------ practice actions --
  async function selectExercise(id) {
    if (!byId.has(id)) return;
    const playing = status() === "playing";
    const unlocking = playing ? unlockVoice() : null;
    P.exerciseId = id;
    P.bpm = null;
    P.shown = null;
    revealExercise(id);
    renderTree();
    scrollTreeTo(id);
    if (unlocking) await unlocking;
    if (player) loadIntoPlayer(playing && P.exerciseId === id);
    renderExercise();
    scrollTreeTo(id);
    saveUi();
  }
  async function playPause() {
    const st = status();
    if (st === "playing") { call("pause"); pull(); paintPractice(); return; }
    await unlockVoice();
    if (!player) return;
    ensureLoaded();
    P.shown = null;
    if (status() === "paused") await call("resume"); else await call("play");
    pull();
    paintPractice();
  }
  function stop() {
    if (!player) return;
    call("stop");
    P.shown = null;
    pull();
    paintPractice();
  }
  async function step(dir) {
    const unlocking = unlockVoice();
    if (!P.exerciseId) {
      await unlocking;
      if (ORDER.length) await selectExercise(dir > 0 ? ORDER[0] : ORDER[ORDER.length - 1]);
      return;
    }
    const target = neighbour(P.exerciseId, dir);
    if (!target) { flashNotice(dir > 0 ? "That was the last exercise." : "This is the first exercise."); return; }
    await unlocking;
    if (player && P.loaded === P.exerciseId) {
      const ok = await call(dir > 0 ? "next" : "prev");  // keeps playing when it was, keeps the key and repeat
      if (ok === false) return;                         // a later click took over
      pull();
      if (P.state && P.state.exerciseId !== P.loaded) onPlayerState(P.state);
      return;
    }
    await selectExercise(target.id);
    scrollTreeTo(target.id);
  }
  async function chipClick(i, show) {
    const unlocking = unlockVoice();
    if (!player) return;
    ensureLoaded();
    await unlocking;
    if (show) { P.shown = i; call("showChord", i); }
    else { P.shown = null; await call("playChord", i); }
    pull();
    paintPractice();
  }
  function setTranspose(semis) {
    P.transpose = KEY_SHIFTS.includes(semis) ? semis : 0;
    retune("setTranspose", P.transpose);
    renderChips();
    paintPractice();
    saveUi();
  }
  function setBpm(bpm) {
    const ex = byId.get(P.exerciseId);
    if (!ex) return;
    const v = bpm == null ? ex.bpm : clampInt(bpm, TEMPO.min, TEMPO.max);
    P.bpm = v === ex.bpm ? null : v;
    retune("setBpm", P.bpm);
    renderChips();
    paintPractice();
  }
  function setLoops(n) {
    P.loops = LOOPS.includes(n) ? n : 1;
    retune("setLoops", P.loops);
    paintPractice();
    saveUi();
  }
  function setAutoAdvance(on) {
    P.autoAdvance = !!on;
    retune("setAutoAdvance", P.autoAdvance);
    paintPractice();
    saveUi();
  }

  // ------------------------------------------------------------------------------------------ practice events --
  treeEl.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-act]");
    if (!b) return;
    blurAfter(e, b);
    const act = b.dataset.act;
    const attr = act === "exercise" ? "id" : act;
    const value = b.dataset[attr];
    if (act === "family") {
      if (P.openFamilies.has(value)) P.openFamilies.delete(value); else P.openFamilies.add(value);
      renderTree();
      saveUi();
    } else if (act === "group") {
      if (P.closedGroups.has(value)) P.closedGroups.delete(value); else P.closedGroups.add(value);
      renderTree();
      saveUi();
    } else if (act === "exercise") {
      selectExercise(value);
    }
    if (e.detail === 0) {  // a keyboard click re-rendered the tree: the focus stays on the same row
      const again = treeEl.querySelector(`button[data-act="${act}"][data-${attr}="${win.CSS.escape(value)}"]`);
      if (again) again.focus();
    }
  });
  libHead.addEventListener("click", (e) => {
    blurAfter(e, libHead);
    P.libraryOpen = !P.libraryOpen;
    renderTree();
    saveUi();
  });
  findEl.addEventListener("input", () => { P.search = findEl.value; renderTree(); });
  findEl.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    const first = treeEl.querySelector(".sp-ex");
    if (first) selectExercise(first.dataset.id);
    findEl.blur();
  });
  chipsEl.addEventListener("click", (e) => {
    const b = e.target.closest(".sp-chip");
    if (!b) return;
    blurAfter(e, b);
    chipClick(+b.dataset.i, !!e.shiftKey);
  });
  keySel.addEventListener("change", () => { setTranspose(+keySel.value); keySel.blur(); });
  bodyEl.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-act]");
    if (!b || b.closest(".sp-chips")) return;
    blurAfter(e, b);
    const ex = byId.get(P.exerciseId);
    const act = b.dataset.act;
    const cur = () => P.bpm || (P.state && P.state.exerciseId === P.exerciseId && P.state.bpm) || (ex && ex.bpm) || 72;
    if (act === "slower") setBpm(cur() - (e.shiftKey ? TEMPO.big : TEMPO.step));
    else if (act === "faster") setBpm(cur() + (e.shiftKey ? TEMPO.big : TEMPO.step));
    else if (act === "tempo-reset") setBpm(null);
    else if (act === "loops") setLoops(b.dataset.loops === "forever" ? Infinity : +b.dataset.loops);
    else if (act === "auto") setAutoAdvance(!P.autoAdvance);
  });
  transportEl.addEventListener("click", (e) => {
    const b = e.target.closest("button[data-act]");
    if (!b) return;
    blurAfter(e, b);
    const act = b.dataset.act;
    if (act === "play-pause") playPause();
    else if (act === "stop") stop();
    else if (act === "prev") step(-1);
    else if (act === "next") step(+1);
  });
  voiceNote.addEventListener("click", async (e) => {
    const b = e.target.closest('[data-act="voice-on"]');
    if (!b) return;
    blurAfter(e, b);
    await turnVoiceOn();
    setTimeout(paintVoice, 0);
  });

  // ------------------------------------------------------------------------------------------ looks: saved looks --
  const lookOf = (p) => (p && p.settings) || {};
  const isBuiltIn = (p) => !!(p && p.builtIn);
  const favourites = () => L.list.filter((p) => isBuiltIn(p) || p.favourite);
  const others = () => L.list.filter((p) => !isBuiltIn(p) && !p.favourite);
  const ordered = () => [...favourites(), ...others()];  // the order Insert and Delete step through
  const presetById = (id) => L.list.find((p) => p.id === id) || null;
  function readStore() {
    if (!lstore) return;
    L.list = (safe(() => lstore.list(), []) || []).filter((p) => p && p.id && p.name);
    L.status = typeof lstore.status === "function" ? safe(() => lstore.status()) : null;
    if (L.active && !presetById(L.active)) { L.active = null; saveUi(); }
  }
  async function loadPresets() {
    if (!lstore) { paintPresets(); return; }
    try { await lstore.load(); } catch (e) { warn("saved looks", e); }
    readStore();
    paintPresets();
  }
  // One change through the store; its own words on a refusal (a starter look, a full list, a name too long).
  async function storeOp(run, okText) {
    if (!lstore) { lookMsg("Saving looks isn't available on this page.", true); return null; }
    L.busy = true;
    paintPresets();
    try {
      const out = await run();
      readStore();
      if (okText) lookMsg(typeof okText === "function" ? okText(out) : okText);
      return out ?? true;
    } catch (e) {
      readStore();
      lookMsg((e && e.message) || String(e), true);
      return null;
    } finally {
      L.busy = false;
      paintPresets();
    }
  }
  let msgT = 0;
  function lookMsg(text, isError = false) {
    msgEl.textContent = text || "";
    msgEl.dataset.error = String(isError);
    msgEl.hidden = !text;
    clearTimeout(msgT);
    if (text) msgT = setTimeout(() => { msgEl.hidden = true; }, isError ? 9000 : 4000);
  }
  // A choice's name as the Looks controls list it (the registry's own labels: "Afterglow Roll", "Moonlit lake"), never its id.
  function choiceLabel(id, value, fallback) {
    const d = !registry ? null : typeof registry.setting === "function" ? registry.setting(id)
      : (Array.isArray(registry.LOOK_SETTINGS) ? registry.LOOK_SETTINGS : []).find((x) => x.id === id);
    const o = d ? optionsOf(d).find((x) => x.value === String(value)) : null;
    return o ? o.label : fallback;
  }
  function presetMeta(p) {
    const s = lookOf(p);
    const bits = [];
    if (s.framing) bits.push(s.framing);
    if (s.enabled === true) bits.push(choiceLabel("theme", s.theme, "atmosphere"));
    else if (s.scheme) bits.push(choiceLabel("scheme", s.scheme, "custom scheme"));
    return bits.join(" · ");
  }
  function chipHtml(p) {
    const active = p.id === L.active;
    const rec = S.recording;
    const changed = active && L.changed.length > 0;
    const meta = isBuiltIn(p) ? ["built in", lookOf(p).framing].filter(Boolean).join(" · ") : presetMeta(p);
    return `<button type="button" class="sl-chip" data-id="${esc(p.id)}" aria-pressed="${active}" data-applying="${L.applying === p.id}"
        ${rec || !registry || L.applying ? "disabled" : ""} title="${esc(rec ? "Stop recording to change the look" : `Use “${p.name}”`)}">
      <span class="sl-chipname">${esc(p.name)}</span><span class="sl-chipmeta">${esc(meta)}</span>
      <span class="sl-chipdot" ${changed ? "" : "hidden"}></span><span class="studio-sr">${changed ? ", changed since you picked it" : ""}</span></button>`;
  }
  function paintPresets() {
    const rec = S.recording;
    const favs = favourites(), rest = others();
    favChips.innerHTML = favs.map(chipHtml).join("") || `<p class="studio-empty">No looks yet.</p>`;
    otherChips.innerHTML = rest.map(chipHtml).join("");
    otherWrap.hidden = !rest.length;
    const active = presetById(L.active);
    const changed = !!active && L.changed.length > 0;
    usingEl.hidden = !active;
    usingEl.dataset.changed = String(changed);
    if (active) {
      const names = L.changed.map((d) => d.label).filter(Boolean);
      usingText.textContent = changed
        ? `Changed since “${active.name}”: ${names.slice(0, 3).join(", ").toLowerCase()}${names.length > 3 ? ` and ${names.length - 3} more` : ""}`
        : `Showing “${active.name}”`;
      usingText.title = changed ? names.join(", ") : "";
      usingDot.hidden = !changed;
      const upd = usingEl.querySelector('[data-act="look-update"]'), undo = usingEl.querySelector('[data-act="look-revert"]');
      upd.hidden = !changed || isBuiltIn(active);
      undo.hidden = !changed;
      upd.disabled = L.busy;
      undo.disabled = rec || L.busy || !!L.applying;
    }
    const full = !!(L.status && L.status.count >= (L.status.max || 100));
    const can = {
      "look-save-as": !!registry && !!lstore && !L.busy && !full,
      "look-favourite": !!lstore && !L.busy && !!active && !isBuiltIn(active),
      "look-rename": !!lstore && !L.busy && !!active && !isBuiltIn(active),
      "look-duplicate": !!lstore && !L.busy && !!active && !full,
      "look-delete": !!lstore && !L.busy && !!active && !isBuiltIn(active),
    };
    for (const b of actionsEl.querySelectorAll("button[data-act]")) {
      b.disabled = !can[b.dataset.act];
      const needsOwn = ["look-favourite", "look-rename", "look-delete"].includes(b.dataset.act);
      b.title = !active && b.dataset.act !== "look-save-as" ? "Pick a look first"
        : needsOwn && isBuiltIn(active) ? "Built-in looks stay as they are. Duplicate one to make it your own."
        : b.dataset.act === "look-save-as" && full ? "You have 100 looks. Delete one to make room." : "";
    }
    const fav = actionsEl.querySelector('[data-act="look-favourite"]');
    const isFav = !!(active && (active.favourite || isBuiltIn(active)));
    fav.setAttribute("aria-pressed", String(isFav));
    fav.querySelector(".sl-star").innerHTML = isFav ? "&#9733;" : "&#9734;";
    const st = L.status;
    sourceEl.textContent = !lstore ? "" : st && st.offline
      ? `saved in this browser${st.pending ? ` · ${st.pending} change${st.pending === 1 ? "" : "s"} waiting for the server` : " only"}`
      : st && st.lastError ? st.lastError : "";
    sourceEl.dataset.state = st && (st.offline || st.lastError) ? "warn" : "";
    recNote.hidden = !rec;
    unavailNote.hidden = !!registry;
    if (!registry) unavailNote.querySelector(".studio-notice-text").textContent = "Looks aren't available on this page yet.";
  }
  async function applyPreset(id) {
    const p = presetById(id);
    if (!p || !registry || typeof registry.applyLook !== "function" || L.applying) return;
    if (S.recording) { lookMsg("Stop recording to change the look.", true); return; }
    L.applying = id;
    paintPresets();
    let r;
    try { r = await registry.applyLook(page, lookOf(p)); } catch (e) { r = { ok: false, refused: "error", reason: (e && e.message) || String(e) }; }
    L.applying = null;
    if (r && r.refused) {
      lookMsg(r.reason || "The page didn't take that look.", true);
    } else {
      L.active = id;
      saveUi();
      if (r && r.ok === false) lookMsg(r.reason || "Some of this look didn't apply.", true); else lookMsg("");
    }
    if (r && r.state) L.snap = r.state;
    await refreshLooks();
  }
  function stepLook(dir) {
    const list = ordered();
    if (!list.length || !registry) return;
    if (S.recording) { say("Stop recording to change the look", true); return; }
    const i = list.findIndex((p) => p.id === L.active);
    const next = list[i < 0 ? (dir > 0 ? 0 : list.length - 1) : mod(i + dir, list.length)];
    say(`Look: ${next.name}`);
    applyPreset(next.id);
  }
  function snapshotNow() {
    if (!registry || typeof registry.snapshot !== "function") return null;
    try { return registry.snapshot(page); } catch (e) { warn("snapshot", e); return null; }
  }
  function openForm(mode, name, e) {
    L.form = mode;
    confirmEl.hidden = true;
    formEl.hidden = false;
    formTitle.textContent = mode === "rename" ? "New name" : "Name this look";
    formOk.textContent = mode === "rename" ? "Rename" : "Save";
    nameEl.value = name;
    nameEl.focus();
    nameEl.select();
  }
  function closeForm() {
    L.form = null;
    formEl.hidden = true;
    if (doc.activeElement === nameEl) nameEl.blur();
  }
  function uniqueName(base) {
    const names = new Set(L.list.map((p) => p.name));
    if (!names.has(base)) return base;
    for (let n = 2; ; n++) if (!names.has(`${base} ${n}`)) return `${base} ${n}`;
  }
  async function submitForm() {
    const name = nameEl.value.trim().replace(/\s+/g, " ");
    if (L.form === "save-as") {
      const settings = snapshotNow();
      if (!settings) { lookMsg("Couldn't read the look on the page.", true); return; }
      const saved = await storeOp(() => lstore.save(name, settings), (p) => `Saved “${p ? p.name : name}”.`);
      if (saved) { if (saved.id) L.active = saved.id; saveUi(); closeForm(); }
    } else if (L.form === "rename") {
      const active = presetById(L.active);
      if (!active || isBuiltIn(active)) { closeForm(); return; }
      if (await storeOp(() => lstore.rename(active.id, name), (p) => `Renamed to “${p ? p.name : name}”.`)) closeForm();
    }
    await refreshLooks();
  }
  async function lookAction(act, e) {
    const active = presetById(L.active);
    if (act === "look-save-as") openForm("save-as", uniqueName("My look"), e);
    else if (act === "look-favourite" && active && !isBuiltIn(active)) {
      await storeOp(() => lstore.setFavourite(active.id, !active.favourite),
        active.favourite ? `“${active.name}” is no longer a favourite.` : `“${active.name}” is a favourite now.`);
    } else if (act === "look-rename" && active && !isBuiltIn(active)) openForm("rename", active.name, e);
    else if (act === "look-duplicate" && active) {
      const copy = await storeOp(() => lstore.duplicate(active.id, uniqueName(`${active.name} copy`).slice(0, NAME_MAX)),
        "Made a copy. Give it a name of its own:");
      if (copy && copy.id) {
        L.active = copy.id;
        saveUi();
        await refreshLooks();
        openForm("rename", copy.name, e);
      }
    } else if (act === "look-delete" && active && !isBuiltIn(active)) {
      closeForm();
      confirmText.textContent = `Delete “${active.name}”? This can't be undone.`;
      confirmEl.hidden = false;
      if (e && e.detail === 0) confirmEl.querySelector('[data-act="look-delete-no"]').focus();
    } else if (act === "look-delete-yes" && active) {
      confirmEl.hidden = true;
      if (await storeOp(() => lstore.delete(active.id), `Deleted “${active.name}”.`)) { L.active = null; saveUi(); }
      await refreshLooks();
    } else if (act === "look-delete-no") {
      confirmEl.hidden = true;
    } else if (act === "form-cancel") {
      closeForm();
    } else if (act === "look-update" && active && !isBuiltIn(active)) {
      const settings = snapshotNow();
      if (settings && await storeOp(() => lstore.save(active.name, settings, { id: active.id }), `Saved the changes to “${active.name}”.`)) {
        await refreshLooks();
      }
    } else if (act === "look-revert" && active) {
      applyPreset(active.id);
    }
  }
  presetsEl.addEventListener("click", (e) => {
    const chip = e.target.closest(".sl-chip");
    if (chip) { blurAfter(e, chip); applyPreset(chip.dataset.id); return; }
    const b = e.target.closest("button[data-act]");
    if (!b) return;
    blurAfter(e, b);
    lookAction(b.dataset.act, e);
  });
  formEl.addEventListener("submit", (e) => { e.preventDefault(); submitForm(); });
  nameEl.addEventListener("keydown", (e) => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closeForm(); } });

  // ------------------------------------------------------------------------------------------ looks: live controls --
  const descriptors = () => (registry && Array.isArray(registry.LOOK_SETTINGS) ? registry.LOOK_SETTINGS : [])
    .slice().sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  function kindOf(d) {
    const t = String(d.type || "").toLowerCase();
    if (["toggle", "boolean", "bool", "switch"].includes(t)) return "toggle";
    if (["range", "number", "slider"].includes(t)) return "range";
    return "choice";
  }
  const rangeOf = (d) => ({ min: d.range?.min ?? 0, max: d.range?.max ?? 1, step: d.range?.step ?? 0.05 });
  function optionsOf(d) {
    let v = null;
    try { v = typeof d.options === "function" ? d.options(page) : d.values; } catch (e) { warn(`choices for ${d.id}`, e); }
    if (!Array.isArray(v) || !v.length) v = Array.isArray(d.values) ? d.values : [];
    return v.map((o) => (o && typeof o === "object" ? { value: String(o.value ?? o.id), label: o.label || o.name || String(o.value ?? o.id) }
      : { value: String(o), label: String(o) }));
  }
  const rows = new Map();  // setting id -> { d, row, input, kind, out }
  function buildControls() {
    rows.clear();
    controlsEl.innerHTML = "";
    const list = descriptors();
    if (!list.length) return;
    const groups = LOOK_GROUPS.map((g) => ({ ...g, items: [] }));
    const more = { id: "more", title: "More", ids: [], items: [] };
    for (const d of list) (groups.find((g) => g.ids.includes(d.id)) || groups.find((g) => g.id === d.group) || more).items.push(d);
    for (const g of groups) g.items.sort((a, b) => g.ids.indexOf(a.id) - g.ids.indexOf(b.id));
    for (const g of [...groups, more]) {
      if (!g.items.length) continue;
      const sec = doc.createElement("section");
      sec.className = "sl-group";
      sec.dataset.group = g.id;
      sec.innerHTML = `<h3 class="studio-kicker sl-grouptitle">${esc(g.title)}</h3>`;
      for (const d of g.items) {
        const kind = kindOf(d);
        const label = d.label || d.id;
        const inputId = `studio-look-${d.id}`;
        const row = doc.createElement("div");
        row.className = "sl-row";
        row.dataset.setting = d.id;
        row.dataset.kind = kind;
        let ctl;
        if (kind === "toggle") {
          ctl = `<button type="button" class="studio-switch sl-switch" role="switch" aria-checked="false" id="${inputId}"><span class="studio-knob" aria-hidden="true"></span><span class="sl-switchtext">Off</span></button>`;
        } else if (kind === "range") {
          const r = rangeOf(d);
          ctl = `<input type="range" class="studio-range" id="${inputId}" min="${r.min}" max="${r.max}" step="${r.step}" /><output class="sl-out" for="${inputId}"></output>`;
        } else {
          ctl = `<select class="studio-select sl-select" id="${inputId}"></select>`;
        }
        row.innerHTML = `<label class="sl-label" for="${inputId}" id="${inputId}-label"><span class="sl-labeltext">${esc(label)}</span>${SETTING_HINTS[d.id] ? `<span class="sl-hint">${esc(SETTING_HINTS[d.id])}</span>` : ""}<span class="sl-lock" hidden>Locked while recording</span></label>
          <span class="sl-ctl">${ctl}</span>`;
        sec.appendChild(row);
        const input = row.querySelector(".sl-ctl > select, .sl-ctl > input, .sl-ctl > button");
        input.setAttribute("aria-labelledby", `${inputId}-label`);
        if (kind === "choice") input.innerHTML = optionsOf(d).map((o) => `<option value="${esc(o.value)}">${esc(o.label)}</option>`).join("");
        rows.set(d.id, { d, row, input, kind, out: row.querySelector("output") });
      }
      controlsEl.appendChild(sec);
    }
  }
  function valueOf(x) {
    if (L.snap && typeof L.snap === "object" && x.d.id in L.snap) return L.snap[x.d.id];
    return undefined;
  }
  const shownRange = (d, v) => (rangeOf(d).max <= 1.5 ? `${Math.round(v * 100)}%` : String(v));
  function paintControls() {
    const rec = S.recording;
    const travelling = L.snap && L.snap.autoWorld === true;
    for (const x of rows.values()) {
      const v = valueOf(x);
      const locked = !!(x.d.recBlocked && rec);
      const busy = x.row.dataset.busy === "true";
      x.row.dataset.missing = String(v === undefined);
      if (x.kind === "toggle") {
        x.input.setAttribute("aria-checked", String(v === true));
        x.input.querySelector(".sl-switchtext").textContent = v === true ? "On" : "Off";
      } else if (x.kind === "range") {
        if (doc.activeElement !== x.input && Number.isFinite(v)) x.input.value = String(v);
        if (x.out) x.out.textContent = shownRange(x.d, +x.input.value);
      } else if (doc.activeElement !== x.input && v != null) {
        const sv = String(v);
        if (![...x.input.options].some((o) => o.value === sv)) {
          if (x.d.id === "scheme" || x.d.id === "instrument") {  // a module listed since the controls were built
            const opts = optionsOf(x.d);
            x.input.innerHTML = opts.map((o) => `<option value="${esc(o.value)}">${esc(o.label)}</option>`).join("");
          }
          if (![...x.input.options].some((o) => o.value === sv)) {
            const o = doc.createElement("option");
            o.value = sv;
            o.textContent = sv;
            x.input.appendChild(o);
          }
        }
        x.input.value = sv;
      }
      x.input.disabled = locked || busy || !registry || v === undefined;
      x.row.dataset.locked = String(locked);
      x.row.querySelector(".sl-lock").hidden = !locked;
      if (x.d.id === "theme") x.row.dataset.travelling = String(!!travelling);
    }
  }
  let refreshing = null, refreshAgain = false;
  function refreshLooks() {
    if (!registry) { paintPresets(); return Promise.resolve(); }
    if (refreshing) { refreshAgain = true; return refreshing; }
    refreshing = (async () => {
      do {
        refreshAgain = false;
        await Promise.resolve();  // after a microtask: the page repaints an instrument's black keys after configure()
        const snap = snapshotNow();
        if (snap) L.snap = snap;
        const active = presetById(L.active);
        let changed = [];
        if (active && L.snap && typeof registry.diff === "function") {
          try { changed = registry.diff(lookOf(active), L.snap) || []; } catch (e) { warn("diff", e); }
        }
        L.changed = Array.isArray(changed) ? changed : [];
        paintControls();
        paintPresets();
      } while (refreshAgain);
    })().finally(() => { refreshing = null; });
    return refreshing;
  }
  async function applyControl(x, value) {
    if (x.d.recBlocked && S.recording) { lookMsg("Stop recording to change this.", true); paintControls(); return; }
    x.row.dataset.busy = x.kind === "range" ? "false" : "true";  // a slider stays in his hand while it applies
    if (x.kind === "choice") x.input.dataset.loading = "true";
    let r;
    try {
      r = typeof registry.applySetting === "function" ? await registry.applySetting(page, x.d.id, value)
        : { ok: (await x.d.apply(page, value)) !== false };
    } catch (e) { r = { ok: false, reason: (e && e.message) || String(e) }; }
    x.row.dataset.busy = "false";
    delete x.input.dataset.loading;
    if (r && r.ok === false) lookMsg(r.reason || "The page kept that setting as it was.", true);
    await refreshLooks();
  }
  let rangeFrame = 0;
  const pendingRange = new Map();
  function flushRanges() {
    if (rangeFrame) { win.cancelAnimationFrame(rangeFrame); rangeFrame = 0; }
    for (const [id, v] of pendingRange) { const x = rows.get(id); if (x) applyControl(x, v); }
    pendingRange.clear();
  }
  controlsEl.addEventListener("click", (e) => {
    const b = e.target.closest(".sl-switch");
    if (!b) return;
    blurAfter(e, b);
    const x = rows.get(b.closest(".sl-row").dataset.setting);
    if (x && !b.disabled) applyControl(x, b.getAttribute("aria-checked") !== "true");
  });
  controlsEl.addEventListener("change", (e) => {
    const rowEl = e.target.closest(".sl-row");
    const x = rowEl && rows.get(rowEl.dataset.setting);
    if (!x) return;
    e.target.blur();
    if (x.kind === "choice") applyControl(x, e.target.value);
    else if (x.kind === "range") { pendingRange.set(x.d.id, +e.target.value); flushRanges(); }
  });
  controlsEl.addEventListener("input", (e) => {
    const rowEl = e.target.closest(".sl-row");
    const x = rowEl && rows.get(rowEl.dataset.setting);
    if (!x || x.kind !== "range") return;
    if (x.out) x.out.textContent = shownRange(x.d, +e.target.value);
    pendingRange.set(x.d.id, +e.target.value);
    if (!rangeFrame) rangeFrame = win.requestAnimationFrame(flushRanges);
  });

  // ------------------------------------------------------------------------------------------ tabs --
  function paintTabs() {
    for (const b of tabsEl.children) {
      const on = b.dataset.tab === S.tab;
      b.setAttribute("aria-selected", String(on));
      b.tabIndex = on ? 0 : -1;
    }
    for (const pane of aside.querySelectorAll(".studio-pane")) pane.hidden = pane.dataset.pane !== S.tab;
    aside.dataset.tab = S.tab;
  }
  function setTab(tab) {
    if (!TABS.some(([id]) => id === tab)) return;
    S.tab = tab;
    paintTabs();
    saveUi();
    if (tab === "looks") refreshLooks(); else paintPractice();
  }
  tabsEl.addEventListener("click", (e) => {
    const b = e.target.closest("[data-tab]");
    if (!b) return;
    blurAfter(e, b);
    setTab(b.dataset.tab);
  });
  tabsEl.addEventListener("keydown", (e) => {  // the tab list's own arrows while a tab has the focus
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    e.stopPropagation();
    const i = TABS.findIndex(([id]) => id === S.tab);
    const next = TABS[mod(i + (e.key === "ArrowRight" ? 1 : -1), TABS.length)][0];
    setTab(next);
    tabsEl.querySelector(`[data-tab="${next}"]`).focus();
  });
  $(".studio-x").addEventListener("click", (e) => { blurAfter(e, e.currentTarget); close(); });

  // ------------------------------------------------------------------------------------------ layout --
  function framingSize() {
    const h = hook("framing");
    const f = h ? safe(h) : null;
    if (f && f.w && f.h) return f;
    if (typeof f === "string" && FRAMING_SIZE[f]) return FRAMING_SIZE[f];
    const st = !h && typeof page.stats === "function" ? safe(() => page.stats()) : null;
    return st && FRAMING_SIZE[st.framing] ? FRAMING_SIZE[st.framing] : null;
  }
  function undockedCanvasWidth(sr) {
    const canvasEl = page.canvas || stage.querySelector("#piano-canvas") || stage.querySelector("canvas");
    const f = framingSize();
    const w = f ? f.w : canvasEl ? canvasEl.width : 0;
    const h = f ? f.h : canvasEl ? canvasEl.height : 0;
    if (!w || !h) return sr.width;
    const ph = hook("pad");
    const p = ph ? safe(ph, 14) : doc.fullscreenElement ? 0 : 14;
    const scale = Math.max(0.05, Math.min((sr.width - 2 * p) / w, (sr.height - 2 * p) / h));
    return Math.floor(w * scale);
  }
  function computeLayout() {
    const rec = isRecording() || S.forced;
    const sr = stage.getBoundingClientRect();
    const margin = (sr.width - undockedCanvasWidth(sr)) / 2;
    let dock;
    if (rec) {
      if (S.frozenDock == null) S.frozenDock = S.lastDock;
      dock = S.frozenDock;
    } else {
      S.frozenDock = null;
      dock = S.open && margin < OVERLAY_MARGIN ? STUDIO_WIDTH : 0;
      S.lastDock = dock;
    }
    const mode = !S.open ? "closed" : dock ? "dock" : "overlay";
    const peekable = rec && S.open && !dock && margin < OVERLAY_MARGIN;
    if (!peekable) S.peek = false;
    return { api: STUDIO_API, mode, open: S.open, tab: S.tab, width: STUDIO_WIDTH, dockWidth: dock, margin: +margin.toFixed(1),
             overlayMargin: OVERLAY_MARGIN, recording: rec, frozen: S.frozenDock != null, peekable, peek: S.peek,
             stage: { width: sr.width, height: sr.height } };
  }
  function relayout() {
    if (S.destroyed) return S.layout;  // a page refit after destroy() must not put the stage classes back
    const Lt = computeLayout();
    const prev = S.layout;
    const changed = !prev || prev.dockWidth !== Lt.dockWidth || prev.open !== Lt.open || prev.mode !== Lt.mode;
    const recChanged = !prev || prev.recording !== Lt.recording;
    S.layout = Lt;
    S.recording = Lt.recording;
    aside.dataset.open = String(Lt.open);
    aside.dataset.mode = Lt.mode;
    aside.dataset.peek = String(Lt.peek);
    peekBtn.hidden = !Lt.peekable;
    stage.classList.toggle("studio-dock", Lt.dockWidth > 0);
    stage.classList.toggle("studio-open", Lt.open);
    if (changed) safe(() => onLayout(Lt));
    if (recChanged) { paintControls(); paintPresets(); }
    return Lt;
  }
  peekBtn.addEventListener("click", (e) => { blurAfter(e, peekBtn); S.peek = !S.peek; relayout(); });
  tabBtn.addEventListener("click", (e) => { blurAfter(e, tabBtn); open(); });

  function open(tab = null) {
    if (S.destroyed) return S.layout;
    if (typeof tab === "string") setTab(tab);
    const was = S.open;
    S.open = true;
    S.peek = false;
    if (!was) {
      const d = deckApi();
      if (d && typeof d.close === "function") safe(() => d.close());
      // the Conversation dock (conversation-dock.js) covers the same edge from above the stage: its own button closes it
      // (the button toggles on the dock's hidden flag, so it is clicked only while the dock shows)
      const convBtn = doc.getElementById("btn-conversation"), convDock = doc.getElementById("conversation-dock");
      if (convBtn && convDock && !convDock.hidden) safe(() => convBtn.click());
    }
    const Lt = relayout();
    if (!was) {
      renderTree();
      paintPractice();
      if (S.tab === "looks") refreshLooks();
      const cur = P.exerciseId && [...treeEl.querySelectorAll(".sp-ex")].find((el) => el.dataset.id === P.exerciseId);
      if (cur && P.libraryOpen) cur.scrollIntoView({ block: "nearest" });
    }
    return Lt;
  }
  function close() {
    if (!S.open) return S.layout;
    S.open = false;
    S.peek = false;
    closeForm();
    confirmEl.hidden = true;
    if (aside.contains(doc.activeElement)) doc.activeElement.blur();
    const Lt = relayout();
    paintPractice();
    return Lt;
  }
  const toggle = () => (S.open ? close() : open());
  const isOpen = () => S.open;
  const dockWidth = () => relayout().dockWidth;
  // frozen(true) holds the dock width as it is now (the page's REC start), frozen(false) lets it follow again; frozen() tells.
  // REC freezes it by itself too, through isRecording, as the deck does.
  function frozen(v) {
    if (typeof v === "boolean") { S.forced = v; relayout(); }
    return S.frozenDock != null;
  }

  // ------------------------------------------------------------------------------------------ keys --
  function handleKey(e) {
    if (!e || S.destroyed || e.defaultPrevented) return false;
    if (e.ctrlKey || e.metaKey || e.altKey) return false;
    const t = e.target;
    const tag = t && t.tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA" || (t && t.isContentEditable)) {
      if (t === findEl && e.code === "Escape") {
        e.preventDefault();
        findEl.value = "";
        P.search = "";
        renderTree();
        findEl.blur();
        return true;
      }
      return false;
    }
    const s = SHORTCUTS.find((x) => x.code === e.code);
    if (!s) return false;
    e.preventDefault();
    if (e.repeat) return true;
    const a = s.action;
    if (a === "toggle") toggle();
    else if (a === "prev") step(-1);
    else if (a === "next") step(+1);
    else if (a === "play-pause") playPause();
    else if (a === "stop") stop();
    else if (a === "look-prev") stepLook(-1);
    else if (a === "look-next") stepLook(+1);
    return true;
  }
  const onKey = (e) => handleKey(e);
  if (keys) win.addEventListener("keydown", onKey);

  // ------------------------------------------------------------------------------------------ the deck shares the edge --
  let deckObs = null, mountObs = null;
  function watchDeck() {
    const el = stage.querySelector("#deck") || doc.getElementById("deck");
    if (!el || typeof win.MutationObserver !== "function") return false;
    deckObs = new win.MutationObserver(() => { if (el.dataset.open === "true" && S.open) close(); });
    deckObs.observe(el, { attributes: true, attributeFilter: ["data-open"] });
    return true;
  }
  if (!watchDeck() && typeof win.MutationObserver === "function") {
    mountObs = new win.MutationObserver(() => { if (watchDeck()) { mountObs.disconnect(); mountObs = null; } });
    mountObs.observe(stage, { childList: true });
  }

  // ------------------------------------------------------------------------------------------ ticker --
  let lastVoice = null, lookTick = 0, lastMinor = minorNow();
  const ticker = setInterval(() => {
    if (S.destroyed) return;
    const rec = isRecording() || S.forced;
    if (rec !== S.recording) relayout();
    const ve = voiceEnabled();
    if (ve !== lastVoice) { lastVoice = ve; paintVoice(); }
    const mn = minorNow();
    if (mn !== lastMinor) { lastMinor = mn; paintPractice(); }
    // the top bar and the Atmosphere panel change looks too: keep the controls and the changed dot honest
    if (S.open && S.tab === "looks" && ++lookTick % 4 === 0 && !pendingRange.size && !L.applying) refreshLooks();
  }, tickMs);
  const ro = typeof win.ResizeObserver === "function" ? new win.ResizeObserver(() => relayout()) : null;
  if (ro) ro.observe(stage);
  const onFs = () => relayout();
  doc.addEventListener("fullscreenchange", onFs);

  // ------------------------------------------------------------------------------------------ boot --
  if (P.exerciseId) revealExercise(P.exerciseId);
  paintTabs();
  renderTree();
  renderExercise();
  if (player && P.exerciseId) loadIntoPlayer(false);
  buildControls();
  readStore();
  const ready = loadPresets().then(() => refreshLooks());
  relayout();

  function stats() {
    return {
      api: STUDIO_API, open: S.open, tab: S.tab, layout: S.layout, recording: S.recording,
      practice: { exerciseId: P.exerciseId, loaded: P.loaded, state: P.state ? { ...P.state, handed: undefined, counts: undefined } : null,
                  transpose: P.transpose, bpm: P.bpm, loops: P.loops === Infinity ? "forever" : P.loops, autoAdvance: P.autoAdvance,
                  shown: P.shown, search: P.search, player: !!player, voice: voiceEnabled(),
                  chips: [...chipsEl.children].map((b) => ({ name: b.querySelector(".sp-chipname").textContent,
                    number: b.querySelector(".sp-chipnum").textContent, now: b.dataset.now === "true" })) },
      looks: { active: L.active, changed: L.changed.map((d) => d.id), favourites: favourites().map((p) => p.id),
               others: others().map((p) => p.id), status: L.status, busy: L.busy, controls: rows.size,
               locked: [...rows.values()].filter((x) => x.row.dataset.locked === "true").map((x) => x.d.id) },
    };
  }
  function destroy() {
    if (S.destroyed) return;
    S.destroyed = true;
    clearInterval(ticker);
    clearTimeout(saveT);
    clearTimeout(msgT);
    clearTimeout(P.noticeT);
    if (rangeFrame) win.cancelAnimationFrame(rangeFrame);
    if (keys) win.removeEventListener("keydown", onKey);
    if (ro) ro.disconnect();
    if (deckObs) deckObs.disconnect();
    if (mountObs) mountObs.disconnect();
    doc.removeEventListener("fullscreenchange", onFs);
    if (player) { safe(() => player.stop()); safe(() => player.dispose && player.dispose()); }
    S.open = false;
    S.layout = { api: STUDIO_API, mode: "closed", open: false, tab: S.tab, width: STUDIO_WIDTH, dockWidth: 0, recording: false,
                 frozen: false, peekable: false, peek: false, destroyed: true };
    stage.classList.remove("studio-dock", "studio-open");
    if (!root) aside.remove(); else aside.innerHTML = "";
    safe(() => onLayout(S.layout));
  }

  return { open, close, toggle, isOpen, dockWidth, frozen, destroy, handleKey, layout: relayout, stats, ready, element: aside,
           player: () => player };
}
