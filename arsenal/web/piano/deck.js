// Piano jam: the deck. A drawer of concept cards at the right of the piano stage, outside the recorded canvas
// (jam-spec 8.1-8.4, 8.7-8.9; UX 2.1, 3, 4, 5.2, 8).
//
// Cards come from the server (GET /api/piano/deck, .../cards/<id>, .../resolve); the deck never calls the voicing
// bridge. Chips show each chord of the card's resolved def in the key shown on that card: the name, the number (the
// def's own `n`, formatted through the page's nashville.js when the Minor setting numbers from the relative major), and
// its length. Hover a chip 250 ms: silent ghosts. Click: hear it (a one-slot Play). Shift-click: Show it (held ghosts).
// The five actions (Play, Show, Loop, Try, Hear me) go through the transport (8.2), which owns every run; Show and hover
// are local ghosts handed to the page through onGhosts. Nothing here reaches `sounding`, the log or the key tracker.
//
// Nothing moves under his mouse while he plays: deck frames that would add, remove or reorder cards wait for his next
// rest (isResting), and the "new cards" pill floats over the list instead of pushing it. The layout never reflows
// during REC: the dock width is frozen at REC start, and a deck opened during REC overlays with a peek rail.
//
// createDeck({ root, stage, api, transport, glass, cueClient, keyView, isRecording, onOpenChange, ...page hooks }) -> {
//   open(cardId?), close(), toggle(), select(delta), act(action, opts), applyDeckFrame(frame), refresh(),
//   layout() /* {mode: closed|overlay|dock, width, dockWidth, ...} */, stats(),
//   handleKey(event) /* the 8.7 keys, before the page's KEYMAP; true when the deck took it */,
//   showPosition(pos), showState(state), flashFound(), setKey(cardId, key), chips(cardId), settings(), dispose() }
//
// Page hooks (all optional): canvas, framing() -> {w, h} (the recorded canvas's backing size, for the overlay rule),
// pad() -> px, pageId, isResting() (8.9 rest), minor() -> "tonic"|"relative", onGhosts(ghosts|null), onLayout(layout),
// onSettings(settings, name), toast(text, isError), unlock(), stopDemo() -> bool, capture() -> DATA 2.10 capture,
// playReplay(cue, info), hush(), voiceReady() -> bool, storage {get, set}, query (URLSearchParams), now(), wallNow(),
// fetchImpl.

import { nashvilleFromName, parseKey } from "./nashville.js";

export const DECK_API = "arsenal.piano.deck/v0";
export const DECK_WIDTH = 380;
export const OVERLAY_MARGIN = 392;   // (stage width - canvas CSS width) / 2 at least this: the deck overlays
export const RAIL_WIDTH = 44;        // the peek rail during REC
export const PILL_HEIGHT = 44;
export const PILL_INSET = 14;
export const LETTERBOX_MIN = 56;     // a letterbox this tall below the canvas takes the pill
export const HOVER_MS = 250;
export const FOUND_MS = 600;
export const NOTE_MS = 6000;         // "Claude added a card" under the toast, deck closed
export const KNOCK_EXPIRE_MS = 60000;
export const TONIGHT_MS = 12 * 3600 * 1000;
export const SEEN_MAX = 500;
export const RESOLVE_CONCURRENCY = 3;
export const TEMPO = Object.freeze({ min: 30, max: 240, step: 2, key: 4, tapMin: 40, tapMax: 200, taps: 4,
                                     tapResetMs: 2000, holdDelayMs: 400, holdEveryMs: 110, sendAfterMs: 220 });
export const TABS = Object.freeze([["tonight", "Tonight"], ["moves", "Your moves"], ["try", "Try this"],
                                   ["kept", "Kept"], ["all", "All"]]);
export const STORE = Object.freeze({
  tab: "arsenal.piano.deck.tab", seen: "arsenal.piano.deck.seen", hint: "arsenal.piano.deck.hintNumbers",
  view: "arsenal.piano.jam.view", volume: "arsenal.piano.cueVolume", duck: "arsenal.piano.jam.duck",
  groove: "arsenal.piano.jam.groove", backing: "arsenal.piano.jam.backing", tryBacking: "arsenal.piano.jam.tryBacking",
  countIn: "arsenal.piano.jam.countIn", knock: "arsenal.piano.jam.knock",
});
// The 8.7 keys, by physical key (event.code). Space, the arrows left and right, H, F and the 33 KEYMAP keys stay the page's.
export const SHORTCUTS = Object.freeze([
  { code: "KeyA", action: "toggle" }, { code: "ArrowUp", action: "up" }, { code: "ArrowDown", action: "down" },
  { code: "Enter", shift: false, action: "enter" }, { code: "Enter", shift: true, action: "hear" },
  { code: "KeyK", action: "show" }, { code: "Backslash", action: "loop" }, { code: "Quote", action: "try" },
  { code: "Minus", action: "transpose-down" }, { code: "Equal", action: "transpose-up" },
  { code: "BracketLeft", action: "slower" }, { code: "BracketRight", action: "faster" },
  { code: "Escape", action: "stop" }, { code: "Backspace", action: "stop" },
]);
export const MAJOR_TONICS = Object.freeze(["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]);
export const MINOR_TONICS = Object.freeze(["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]);
export const HIS_KEYS = Object.freeze(["Eb", "F", "D", "Gb", "Db", "G"]);  // UX 4.3: the keys he plays in most (and G)
const GROOVES = ["hold", "ballad", "pulse"];
const BACKINGS = ["full", "comp", "bass"];
const TRY_BACKINGS = ["ghosts", "bass", "loop"];
const SETTING_DEFAULTS = Object.freeze({ view: "auto", volume: 0.7, duck: true, groove: "card", backing: "card",
                                         tryBacking: "bass", countIn: 1, knock: true });
const GROUP_TAG = { moves: "YOUR MOVE", try: "TRY THIS", kept: "KEPT" };
const KIND_WORD = { play: "PLAY", loop: "LOOP", try: "TRY" };
const MATCH_PLAIN = new Set(["exact", "enharmonic", "notes"]);

// ------------------------------------------------------------------------------------------------ text helpers --
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;",
  '"': "&quot;", "'": "&#39;" })[c]);
const ACC_GLYPH = { b: "♭", bb: "𝄫", "#": "♯", "##": "𝄪" };
const glyphSuffix = (s) => esc(s).replace(/b(?=\d)/g, "♭").replace(/#/g, "♯");
const mod = (a, n) => ((a % n) + n) % n;

// "Abmaj7#11" -> A♭maj7♯11; "Ab11/Gb" -> A♭11/G♭; a cluster "Gb Db Ab" keeps its letters with real flats.
export function nameText(name) {
  const s = String(name || "");
  if (/\s/.test(s.trim())) return s.trim().split(/\s+/).map((t) => t.replace(/^([A-G])(bb|##|b|#)?/, (m0, l, a) => l + (ACC_GLYPH[a] || ""))).join(" ");
  const m = /^([A-G])(bb|##|b|#)?(.*?)(?:\/([A-G])(bb|##|b|#)?)?$/.exec(s);
  if (!m) return s;
  return m[1] + (ACC_GLYPH[m[2]] || "") + m[3].replace(/b(?=\d)/g, "♭").replace(/#/g, "♯") +
    (m[4] ? "/" + m[4] + (ACC_GLYPH[m[5]] || "") : "");
}
export const nameHtml = (name) => esc(nameText(name));

// "5^7sus4/1" -> 5<sup>7sus4</sup>/1; "b7maj9" -> ♭7<sup>maj9</sup>; "2-^7" -> 2<sup>-7</sup>.
export function numberHtml(text) {
  const s = String(text || "");
  const m = /^(bb|##|b|#)?([1-7])(.*?)(?:\/(bb|##|b|#)?([1-7]))?$/.exec(s);
  if (!m) return esc(s);
  const sfx = m[3].replace(/^\^/, "").replace(/^-\^/, "-");
  return `${ACC_GLYPH[m[1]] || ""}${m[2]}${sfx ? `<sup>${glyphSuffix(sfx)}</sup>` : ""}` +
    (m[5] ? `/${ACC_GLYPH[m[4]] || ""}${m[5]}` : "");
}

// A tonic-numbered degree ("b3") counted from the relative major instead ("1"): letters move down 2, pitches down 3.
const MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11];
const ACC_OF = { bb: -2, b: -1, "": 0, "#": 1, "##": 2 };
const accText = (a) => (a < 0 ? "b".repeat(-a) : "#".repeat(a));
function relativeDegree(acc, d) {
  const pc = MAJOR_STEPS[d - 1] + ACC_OF[acc || ""];
  const nd = ((d - 1 + 5) % 7) + 1;
  return accText(mod(pc - 3 - MAJOR_STEPS[nd - 1] + 6, 12) - 6) + nd;
}
export function relativeNumber(n) {
  const m = /^(bb|##|b|#)?([1-7])(.*?)(?:\/(bb|##|b|#)?([1-7]))?$/.exec(String(n || ""));
  if (!m) return n;
  return relativeDegree(m[1], +m[2]) + m[3] + (m[5] ? "/" + relativeDegree(m[4], +m[5]) : "");
}

function pageNumber(name, key, minor) {
  try {
    const r = nashvilleFromName(name, key, { minor });
    return r && r.kind === "chord" ? r.text : null;
  } catch { return null; }
}

// The number a chip shows: the def's own `n` (the card's number, as the CLI prints it). With the Minor setting on
// "relative" in a minor section, the page's nashville.js numbers the chord from the relative major, so the chip, the
// Nashville row and the pill agree; an author label the page reads differently keeps the card's number, moved over.
export function chipNumber(slot, minor = "tonic") {
  if (!slot || !slot.n) return null;
  const k = parseKey(slot.key || "");
  if (!k || k.mode !== "minor" || minor !== "relative") return slot.n;
  if (pageNumber(slot.name, slot.key, "tonic") === slot.n) return pageNumber(slot.name, slot.key, "relative") || relativeNumber(slot.n);
  return relativeNumber(slot.n);
}

const SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const LETTER_PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const noteNamePc = (l, a) => mod(LETTER_PC[l] + (ACC_OF[a || ""] || 0), 12);
const sharpKey = (keyName) => {
  const k = parseKey(keyName || "");
  if (!k) return false;
  return k.mode === "major" ? [7, 2, 9, 4, 11, 6].includes(k.tonic) && !/b/.test(keyName)
    : [4, 11, 6, 1, 8].includes(k.tonic) && !/b/.test(keyName);
};
// Nearest shift (-6..+5 half steps) from one key to another: how the voicing moves (C6).
export function keyShift(fromKey, toKey) {
  const a = parseKey(fromKey || ""), b = parseKey(toKey || "");
  if (!a || !b) return 0;
  return mod(b.tonic - a.tonic + 6, 12) - 6;
}
// A chord name moved by a shift, spelled for the target key: the grey placeholder while resolve answers (8.3).
export function transposeName(name, semis, keyName) {
  const names = sharpKey(keyName) ? SHARP_NAMES : FLAT_NAMES;
  const mv = (l, a) => names[mod(noteNamePc(l, a) + semis, 12)];
  const s = String(name || "");
  if (/\s/.test(s.trim())) return s.trim().split(/\s+/).map((t) => t.replace(/^([A-G])(bb|##|b|#)?/, (m0, l, a) => mv(l, a))).join(" ");
  const m = /^([A-G])(bb|##|b|#)?(.*?)(?:\/([A-G])(bb|##|b|#)?)?$/.exec(s);
  if (!m) return s;
  return mv(m[1], m[2]) + m[3] + (m[4] ? "/" + mv(m[4], m[5]) : "");
}
const ROLE_WORDS = { "1": "root", b2: "♭2nd", 2: "2nd", b3: "♭3rd", 3: "3rd", 4: "4th", b5: "♭5th", 5: "5th", "#5": "♯5th",
                     6: "6th", b7: "♭7th", 7: "7th", b9: "♭9", 9: "9th", "#9": "♯9", 11: "11th", "#11": "♯11", b13: "♭13",
                     13: "13th" };
// Card prose with real accidentals on note names and colours ("Ab" -> A♭, "#11" -> ♯11), as the chips print them.
const pullText = (s) => String(s || "").replace(/\b([A-G])b\b/g, "$1♭").replace(/\b([A-G])#/g, "$1♯").replace(/(^|[\s(])#(\d)/g, "$1♯$2");
const keyWithGlyph = (k) => String(k || "").replace(/^([A-G])(b|#)/, (m0, l, a) => l + ACC_GLYPH[a]);
const shortKey = (k) => keyWithGlyph(String(k || "").replace(/ major$/, "").replace(/ minor$/, "m"));
// A transport state in one shape: J7's state() gives {state, run: <id>, mode, card, knock: {run, mode, card,
// at_epoch_ms}}; a run object ({run, mode, card, ...}) is taken as it is.
export function normState(st) {
  if (!st || typeof st !== "object") return null;
  if (st.run && typeof st.run === "object") return st;
  const run = st.run ? { run: st.run, mode: st.mode || null, card: st.card || null, state: st.state, key: st.key || null } : null;
  return { ...st, run };
}
const clockSeconds = (text) => {
  const m = /^(\d+):(\d{2})(?:\.(\d+))?$/.exec(String(text || ""));
  return m ? +m[1] * 60 + +m[2] + (m[3] ? +`0.${m[3]}` : 0) : null;
};

// ------------------------------------------------------------------------------------------------ the deck --
export function createDeck({
  root = null, stage, api = "", transport = null, glass = null, cueClient = null, keyView = null,
  isRecording = () => false, onOpenChange = () => {},
  canvas = null, framing = null, pad = null, pageId = null, isResting = () => true, minor = () => "tonic",
  onGhosts = () => {}, onLayout = () => {}, onSettings = () => {}, toast = null, unlock = () => {},
  stopDemo = () => false, capture = null, playReplay = null, hush = () => {}, voiceReady = null,
  storage = null, query = null, now = () => performance.now(), wallNow = () => Date.now(),
  fetchImpl = globalThis.fetch ? globalThis.fetch.bind(globalThis) : null, autoRefresh = true, tickMs = 250,
} = {}) {
  if (!stage) throw new Error("createDeck needs the stage element");
  const doc = stage.ownerDocument;
  const win = doc.defaultView;
  const canvasEl = canvas || stage.querySelector("canvas");
  const safe = (fn, fallback = null) => { try { return fn(); } catch (e) { warn("hook failed", e); return fallback; } };
  const warn = (what, e) => console.warn(`[deck] ${what}:`, e && (e.message || e));
  const store = storage || {
    get(k) { try { return win.localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { win.localStorage.setItem(k, v); } catch { /* storage blocked */ } },
  };
  const q = query || new URLSearchParams(win.location ? win.location.search : "");

  // ------------------------------------------------------------------------------------------ http --
  const base = typeof api === "string" ? api.replace(/\/+$/, "") : "";
  async function request(method, path, body) {
    if (!fetchImpl) throw new Error("no fetch in this page");
    const res = await fetchImpl(`${base}${path}`, {
      method, cache: "no-store", headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = null;
    try { data = await res.json(); } catch { /* no JSON body */ }
    if (!res.ok) {
      const err = new Error((data && data.error) || `${method} ${path} answered ${res.status}`);
      err.status = res.status;
      err.body = data;
      throw err;
    }
    return data;
  }
  const http = api && typeof api === "object" && typeof api.get === "function" ? api
    : { get: (p) => request("GET", p), post: (p, b) => request("POST", p, b) };

  // ------------------------------------------------------------------------------------------ state --
  const readSettings = () => {
    const out = { ...SETTING_DEFAULTS };
    const g = (k) => store.get(STORE[k]);
    if (["auto", "glass"].includes(g("view"))) out.view = g("view");
    const vol = parseFloat(g("volume"));
    if (Number.isFinite(vol) && vol >= 0 && vol <= 1) out.volume = vol;
    if (g("duck") === "off") out.duck = false;
    if ([...GROOVES, "card"].includes(g("groove"))) out.groove = g("groove");
    if ([...BACKINGS, "card"].includes(g("backing"))) out.backing = g("backing");
    if (TRY_BACKINGS.includes(g("tryBacking"))) out.tryBacking = g("tryBacking");
    if (["0", "1", "2"].includes(g("countIn"))) out.countIn = +g("countIn");
    if (g("knock") === "off") out.knock = false;
    const jv = q.get("jam");
    if (jv === "auto" || jv === "glass") out.view = jv;  // a receipt override, never stored
    return out;
  };
  const S = {
    doc: { rev: -1, order: [], cards: [] }, full: new Map(), view: new Map(), defs: new Map(), resolved: new Map(),
    tab: null, search: "", selected: null, expanded: null, open: false, peek: false,
    lastDock: 0, frozenDock: null, recording: false, layout: null,
    sessionIds: new Set(), pending: [], pendingOpen: null, badge: 0, noteTimer: 0,
    show: null, hover: null, hoverTimer: 0, position: null, tstate: null, runDef: null, runDefs: new Map(), knock: null,
    foundUntil: 0, settings: readSettings(), lastUsed: new Map(), greyed: new Map(), pairTimer: 0, moving: null, moveT: 0,
    seen: new Map(), seenLoaded: false, hint: store.get(STORE.hint) === "1", refreshing: null, disposed: false,
  };
  const counts = { refreshes: 0, frames: 0, deferred: 0, applied: 0, stale: 0, resolves: 0, errors: 0,
                   actions: {}, keys: {}, transport: {}, ghosts: 0, layouts: 0, renders: 0 };
  const bump = (bag, k) => { bag[k] = (bag[k] || 0) + 1; };
  const say = (text, isError = false) => { if (toast) safe(() => toast(text, isError)); else console.info(`[deck] ${text}`); };
  const minorNow = () => (safe(minor, "tonic") === "relative" ? "relative" : "tonic");
  const trackerKey = () => {
    const kv = typeof keyView === "function" ? safe(keyView) : keyView;
    const name = kv && (kv.name || (kv.key && kv.key.name));
    return typeof name === "string" && parseKey(name) ? parseKey(name).name : null;
  };

  (function loadSeen() {
    const raw = store.get(STORE.seen);
    if (raw == null) return;
    S.seenLoaded = true;
    try {
      for (const entry of JSON.parse(raw)) {
        const m = /^(.+):(\d+)$/.exec(String(entry));
        if (m) S.seen.set(m[1], Math.max(S.seen.get(m[1]) || 0, +m[2]));
      }
    } catch { /* a bad value is no memory */ }
  })();
  function saveSeen() {
    const entries = [...S.seen.entries()].slice(-SEEN_MAX).map(([id, rev]) => `${id}:${rev}`);
    store.set(STORE.seen, JSON.stringify(entries));
  }
  function markSeen(id) {
    const sum = summaryOf(id);
    if (!sum) return;
    if ((S.seen.get(id) || 0) >= sum.rev) return;
    S.seen.delete(id);
    S.seen.set(id, sum.rev);
    while (S.seen.size > SEEN_MAX) S.seen.delete(S.seen.keys().next().value);
    saveSeen();
    const el = cardEls.get(id);
    if (el) renderHead(el, sum);
  }
  const markOf = (sum) => {
    if (!S.seen.has(sum.id)) return sum.created_by === "claude" ? "new" : "";
    return S.seen.get(sum.id) < sum.rev ? "updated" : "";
  };

  const summaryOf = (id) => S.doc.cards.find((c) => c.id === id) || null;
  const isTonight = (sum) => {
    if (S.sessionIds.has(sum.id)) return true;
    const t = Date.parse(sum.updated_at || "");
    return Number.isFinite(t) && wallNow() - t < TONIGHT_MS;
  };
  const inTab = (sum, tab) => (tab === "all" ? true : tab === "tonight" ? isTonight(sum) : sum.group === tab);
  function sortedIds(tab) {
    const idx = new Map(S.doc.order.map((id, i) => [id, i]));
    const ord = (a, b) => (b.favorite - a.favorite) || ((idx.has(a.id) ? idx.get(a.id) : 1e9) -
      (idx.has(b.id) ? idx.get(b.id) : 1e9)) || a.id.localeCompare(b.id);
    const recent = (c) => Math.max(Date.parse(c.updated_at || "") || 0, S.lastUsed.get(c.id) || 0);
    const list = S.doc.cards.filter((c) => !c.archived && inTab(c, tab));
    // newest minute first, deck order inside a minute: a seed install writes 17 cards in one moment and they keep the
    // first-night order (section 12) instead of coming out last-installed first
    const minute = (c) => Math.floor(recent(c) / 60000);
    if (tab === "tonight" || tab === "kept") list.sort((a, b) => (minute(b) - minute(a)) || ord(a, b));
    else if (tab === "all") {
      const g = { moves: 0, try: 1, kept: 2 };
      list.sort((a, b) => ((g[a.group] ?? 3) - (g[b.group] ?? 3)) || ord(a, b));
    } else list.sort(ord);
    return list.map((c) => c.id);
  }

  // ------------------------------------------------------------------------------------------ DOM --
  const aside = root || doc.createElement("aside");
  aside.id = aside.id || "deck";
  aside.classList.add("deck");
  aside.setAttribute("aria-label", "Cards");
  aside.innerHTML = `
    <button type="button" class="deck-tab" aria-label="Open the cards (A)"><span class="deck-tab-text">CARDS</span><span class="deck-badge" hidden></span></button>
    <div class="deck-panel">
      <header class="deck-now" data-state="idle">
        <div class="now-idle">
          <div class="now-line"><span class="now-kicker">NOW</span><span class="now-status">Claude's hand: listening</span>
            <button type="button" class="deck-btn deck-more" data-act="settings" aria-label="Deck settings" title="Deck settings">&middot;&middot;&middot;</button></div>
          <div class="now-line"><span class="now-last"></span><button type="button" class="deck-btn" data-act="capture" title="Save the chord you are sounding as a Kept card">Keep what I just played</button></div>
        </div>
        <div class="now-run">
          <div class="now-line"><b class="now-kind"></b><span class="now-title"></span><span class="now-meta"></span>
            <button type="button" class="deck-btn now-stop" data-act="stop">Stop</button></div>
          <div class="now-line now-chords"><span class="now-label">NOW</span><span class="now-chord"></span><span class="now-num"></span>
            <span class="now-label now-next-label">NEXT</span><span class="now-next"></span><span class="now-next-num"></span></div>
          <div class="now-line"><span class="now-pips"></span><span class="now-bar"></span><span class="now-pass"></span>
            <span class="now-found" hidden>found</span><span class="now-count" hidden></span></div>
          <div class="now-progress"><span></span></div>
          <div class="now-line now-mix"><label class="now-field">Claude <input type="range" class="now-vol" min="0" max="1" step="0.01" aria-label="Claude's volume" /></label>
            <label class="now-field"><input type="checkbox" class="now-duck" /> duck</label>
            <button type="button" class="deck-btn deck-more" data-act="settings" aria-label="Deck settings">&middot;&middot;&middot;</button></div>
        </div>
        <div class="now-knock">
          <div class="now-line"><span class="knock-dot" aria-hidden="true"></span><span class="knock-text"></span></div>
          <div class="now-line"><span class="knock-wait"></span><button type="button" class="deck-btn knock-take" data-act="knock-take">Hear &#9166;</button>
            <button type="button" class="deck-btn" data-act="knock-decline">Not now</button></div>
        </div>
        <div class="now-show">
          <div class="now-line"><span class="now-kicker">SHOWING</span><span class="show-chord"></span><span class="show-num"></span>
            <button type="button" class="deck-btn" data-act="dismiss">Dismiss</button></div>
          <div class="now-line"><span class="now-status show-hint">K or Dismiss hides the ghosts</span></div>
        </div>
      </header>
      <div class="deck-search"><input type="search" class="deck-find" placeholder="Find a card: name, chord, number (4maj, sus, lament)" aria-label="Find a card" spellcheck="false" autocomplete="off" /></div>
      <nav class="deck-tabs" role="tablist"></nav>
      <div class="deck-listwrap">
        <button type="button" class="deck-newpill" hidden></button>
        <div class="deck-list" role="list"></div>
        <p class="deck-empty" hidden>No card matches. Ask Claude for one in chat.</p>
      </div>
      <div class="deck-settings" hidden role="dialog" aria-label="Deck settings"></div>
    </div>
    <button type="button" class="deck-peek" hidden aria-label="Peek the cards">&#8249;</button>`;
  if (!aside.parentNode) stage.appendChild(aside);
  const $ = (sel) => aside.querySelector(sel);
  const listEl = $(".deck-list"), listWrap = $(".deck-listwrap"), tabsEl = $(".deck-tabs"), findEl = $(".deck-find");
  const nowEl = $(".deck-now"), newPill = $(".deck-newpill"), emptyEl = $(".deck-empty"), settingsEl = $(".deck-settings");
  const tabBtn = $(".deck-tab"), badgeEl = $(".deck-badge"), peekBtn = $(".deck-peek");

  const pill = doc.getElementById("jam-pill") || doc.createElement("div");
  pill.id = "jam-pill";
  pill.classList.add("jam-pill");
  pill.hidden = true;
  if (!pill.parentNode) stage.appendChild(pill);
  const note = doc.createElement("div");
  note.className = "deck-note";
  note.hidden = true;
  note.setAttribute("role", "status");
  stage.appendChild(note);

  for (const [id, label] of TABS) {
    const b = doc.createElement("button");
    b.type = "button";
    b.className = "deck-tabbtn";
    b.dataset.tab = id;
    b.setAttribute("role", "tab");
    b.innerHTML = `<span class="tab-label">${esc(label)}</span><span class="tab-count"></span>`;
    tabsEl.appendChild(b);
  }
  const cardEls = new Map();

  // ------------------------------------------------------------------------------------------ data --
  let refreshSeq = 0;
  async function refresh() {
    const seq = ++refreshSeq;
    counts.refreshes++;
    let docOut;
    try {
      docOut = await http.get("/api/piano/deck");
    } catch (e) {
      counts.errors++;
      warn("deck read failed", e);
      return false;
    }
    if (seq !== refreshSeq || S.disposed) return false;
    const before = new Map(S.doc.cards.map((c) => [c.id, c.rev]));
    S.doc = { rev: docOut.rev, order: docOut.order || [], cards: docOut.cards || [] };
    for (const c of S.doc.cards) if (before.has(c.id) && before.get(c.id) !== c.rev) S.full.delete(c.id);
    if (!S.seenLoaded) {  // a first visit: what is here already is not news
      for (const c of S.doc.cards) S.seen.set(c.id, c.rev);
      S.seenLoaded = true;
      saveSeen();
    }
    if (!S.tab) {
      const stored = store.get(STORE.tab);
      S.tab = TABS.some(([t]) => t === stored) ? stored : S.doc.cards.some((c) => !c.archived && isTonight(c)) ? "tonight" : "moves";
    }
    renderAll();
    return true;
  }

  async function loadCard(id) {
    const sum = summaryOf(id);
    const have = S.full.get(id);
    if (have && (!sum || have.rev === sum.rev)) return have;
    const out = await http.get(`/api/piano/deck/cards/${encodeURIComponent(id)}`);
    S.full.set(id, out.card);
    return out.card;
  }

  const defaultVariant = (card) => (card && !(card.chords && card.chords.length) && card.variants && card.variants.length
    ? card.variants[0].id : null);
  function viewOf(id) {
    let v = S.view.get(id);
    if (!v) {
      const card = S.full.get(id) || summaryOf(id) || {};
      v = { choice: "written", key: card.key || null, variant: defaultVariant(card), bpm: null, groove: null,
            backing: null, def: null, taps: [], editing: false, token: 0 };
      S.view.set(id, v);
    }
    return v;
  }
  function shownKey(id) {
    const v = viewOf(id);
    const card = S.full.get(id) || summaryOf(id) || {};
    if (v.choice === "now") return trackerKey() || card.key;
    if (v.choice === "written") return card.key;
    return v.key || card.key;
  }
  const tempoOf = (id) => {
    const v = viewOf(id), card = S.full.get(id);
    return v.bpm || (card && card.tempo && card.tempo.bpm) || 66;
  };

  // resolve: one promise per (card, rev, key, variant); the collapsed lines go through a small queue
  function defFor(id, key, variant) {
    const card = S.full.get(id) || summaryOf(id);
    const rev = card ? card.rev : 0;
    const ck = `${id}|${rev}|${key || ""}|${variant || ""}`;
    if (!S.defs.has(ck)) {
      const qs = new URLSearchParams();
      if (key) qs.set("key", key);
      if (variant) qs.set("variant", variant);
      const p = http.get(`/api/piano/deck/cards/${encodeURIComponent(id)}/resolve?${qs}`).then((r) => {
        counts.resolves++;
        S.resolved.set(ck, r.def);
        return r.def;
      });
      p.catch(() => { S.defs.delete(ck); counts.errors++; });
      S.defs.set(ck, p);
    }
    return S.defs.get(ck);
  }
  const settledDef = (id, key, variant) => {
    const card = S.full.get(id) || summaryOf(id);
    return S.resolved.get(`${id}|${card ? card.rev : 0}|${key || ""}|${variant || ""}`) || null;
  };
  const lineQueue = [];
  let lineActive = 0;
  function queueLine(id) {
    if (lineQueue.includes(id)) return;
    lineQueue.push(id);
    pumpLines();
  }
  function pumpLines() {
    while (lineActive < RESOLVE_CONCURRENCY && lineQueue.length) {
      const id = lineQueue.shift();
      lineActive++;
      (async () => {
        try {
          await loadCard(id);
          const v = viewOf(id);
          await defFor(id, shownKey(id), v.variant);
          const el = cardEls.get(id), sum = summaryOf(id);
          if (el && sum) renderHead(el, sum);
        } catch (e) { warn(`resolve ${id}`, e); }
        lineActive--;
        pumpLines();
      })();
    }
  }

  // ------------------------------------------------------------------------------------------ rendering --
  function renderAll() {
    counts.renders++;
    renderTabs();
    renderList();
    renderNow();
    renderPill();
    relayout();
  }

  function renderTabs() {
    for (const b of tabsEl.children) {
      const t = b.dataset.tab;
      b.setAttribute("aria-selected", String(t === S.tab));
      const n = t === "all" ? "" : S.doc.cards.filter((c) => !c.archived && inTab(c, t)).length;
      b.querySelector(".tab-count").textContent = n === "" ? "" : String(n);
    }
  }

  const searchText = (id) => {
    const sum = summaryOf(id) || {};
    const card = S.full.get(id) || {};
    const def = settledDef(id, shownKey(id), viewOf(id).variant);
    const names = def ? def.slots.map((s) => `${s.name} ${s.n || ""} ${chipNumber(s, minorNow()) || ""}`).join(" ") : "";
    return [sum.title, sum.meaning, card.theory_name, (sum.tags || []).join(" "), sum.numbers, names,
            (card.variants || []).map((v) => v.label || "").join(" ")].join(" ").toLowerCase()
      .replace(/♭/g, "b").replace(/♯/g, "#");
  };
  const matches = (id) => {
    const qtext = S.search.trim().toLowerCase().replace(/♭/g, "b").replace(/♯/g, "#");
    if (!qtext) return true;
    const hay = searchText(id);
    return qtext.split(/\s+/).every((t) => hay.includes(t));
  };
  const visibleIds = () => sortedIds(S.tab || "moves").filter(matches);

  function renderList() {
    const ids = sortedIds(S.tab || "moves");
    const want = new Set(ids);
    for (const [id, el] of cardEls) if (!want.has(id)) { el.remove(); cardEls.delete(id); }
    let prev = null;
    for (const id of ids) {
      let el = cardEls.get(id);
      if (!el) { el = buildCard(id); cardEls.set(id, el); }
      const expectedNext = prev ? prev.nextSibling : listEl.firstChild;
      if (expectedNext !== el) listEl.insertBefore(el, expectedNext);
      renderHead(el, summaryOf(id));
      el.hidden = !matches(id);
      prev = el;
    }
    emptyEl.hidden = ids.some((id) => !cardEls.get(id).hidden);
    for (const id of ids) if (!cardEls.get(id).hidden && !settledDef(id, shownKey(id), viewOf(id).variant)) queueLine(id);
    if (S.expanded && !want.has(S.expanded)) S.expanded = null;
    syncSelection();
  }

  function buildCard(id) {
    const el = doc.createElement("article");
    el.className = "deck-card";
    el.dataset.id = id;
    el.setAttribute("role", "listitem");
    el.innerHTML = `
      <button type="button" class="deck-card-head" aria-expanded="false">
        <span class="card-row"><span class="card-title"></span><span class="card-tag"></span></span>
        <span class="card-meaning"></span>
        <span class="card-row card-row-line"><span class="card-line"></span><span class="card-keybpm"></span></span>
      </button>
      <div class="deck-card-body" hidden></div>`;
    el.querySelector(".deck-card-head").addEventListener("click", (e) => {
      e.currentTarget.blur();
      S.selected = id;
      toggleExpand(id);
    });
    return el;
  }

  function lineHtml(id, sum) {
    const def = settledDef(id, shownKey(id), viewOf(id).variant);
    if (!def) return `<span class="line-nums">${esc(sum.numbers || "")}</span>`;
    const mn = minorNow();
    const names = def.slots.map((s) => nameHtml(s.name)).join(" <span class=\"line-sep\">&rsaquo;</span> ");
    const nums = def.slots.map((s) => numberHtml(chipNumber(s, mn) || "")).join(" <span class=\"line-sep\">&rsaquo;</span> ");
    return `<span class="line-names">${names}</span><span class="line-nums">${nums}</span>`;
  }

  function renderHead(el, sum) {
    if (!sum) return;
    const mark = markOf(sum);
    el.dataset.mark = mark;
    el.dataset.group = sum.group || "";
    el.querySelector(".card-title").textContent = sum.title || sum.id;
    el.querySelector(".card-tag").textContent = mark === "new" ? "NEW" : mark === "updated" ? "updated" : (GROUP_TAG[sum.group] || "");
    el.querySelector(".card-meaning").textContent = sum.meaning || "";
    const line = lineHtml(sum.id, sum);
    const lineEl = el.querySelector(".card-line");
    if (lineEl.innerHTML !== line) lineEl.innerHTML = line;
    const key = shownKey(sum.id);
    el.querySelector(".card-keybpm").textContent = `${shortKey(key)}  ${tempoOf(sum.id)}`;
  }

  function syncSelection() {
    for (const [id, el] of cardEls) {
      el.classList.toggle("selected", id === S.selected);
      const exp = id === S.expanded;
      el.classList.toggle("expanded", exp);
      el.querySelector(".deck-card-head").setAttribute("aria-expanded", String(exp));
      const body = el.querySelector(".deck-card-body");
      if (!exp && !body.hidden) { body.hidden = true; body.innerHTML = ""; }
    }
  }

  async function toggleExpand(id, force = null) {
    const expand = force == null ? S.expanded !== id : force;
    S.expanded = expand ? id : null;
    syncSelection();
    if (expand) {
      markSeen(id);
      await renderBody(id);
    }
  }

  // The expanded card: chips, reads-as, key, tempo, actions, moments, about, footer.
  async function renderBody(id) {
    const el = cardEls.get(id);
    if (!el || S.expanded !== id) return;
    const body = el.querySelector(".deck-card-body");
    const v = viewOf(id);
    const token = ++v.token;
    let card;
    try { card = await loadCard(id); } catch (e) { body.hidden = false; body.textContent = `This card could not be read: ${e.message}`; return; }
    if (token !== v.token || S.expanded !== id) return;
    const key = shownKey(id);
    body.hidden = false;
    body.innerHTML = bodyHtml(card, v, key);
    wireBody(body, id);
    renderChips(id, body, null);
    paintPlaying(id);
    try {
      const def = await defFor(id, key, v.variant);
      if (token !== v.token || S.expanded !== id) return;
      v.def = def;
      renderChips(id, body, def);
      const sum = summaryOf(id);
      if (sum) renderHead(el, sum);
    } catch (e) {
      if (token !== v.token) return;
      const chipsEl = body.querySelector(".deck-chips");
      if (chipsEl) chipsEl.insertAdjacentHTML("beforeend", `<p class="deck-error">These chords could not be voiced: ${esc(e.message)}</p>`);
    }
  }

  function keyOptions(card, key, v) {
    const mode = (parseKey(card.key) || { mode: "major" }).mode;
    const tonics = mode === "minor" ? MINOR_TONICS : MAJOR_TONICS;
    const now = trackerKey();
    const his = [];
    for (const k of [...(card.also_in || []), ...HIS_KEYS.map((t) => `${t} ${mode}`)]) {
      const p = parseKey(k);
      if (p && !his.includes(p.name) && p.name !== parseKey(card.key).name) his.push(p.name);
    }
    const selected = (choice, name) => (v.choice === choice && (choice !== "key" || name === key) ? " selected" : "");
    let html = `<option value="written"${selected("written")}>as written &middot; ${esc(shortKey(card.key))}</option>`;
    html += `<option value="now"${selected("now")}${now ? "" : " disabled"}>my key now${now ? ` &middot; ${esc(shortKey(now))} (auto)` : ""}</option>`;
    html += `<optgroup label="your keys">${his.map((k) => `<option value="key:${esc(k)}"${selected("key", k)}>${esc(shortKey(k))}</option>`).join("")}</optgroup>`;
    html += `<optgroup label="all 12">${tonics.map((t) => { const k = `${t} ${mode}`; return `<option value="key:${esc(k)}"${selected("key", k)}>${esc(shortKey(k))}</option>`; }).join("")}</optgroup>`;
    return html;
  }

  function momentOf(card) {
    if (card.replay && card.replay.session) {
      return { session: card.replay.session, at: card.replay.at, seconds: card.replay.seconds || 8, speed: card.replay.speed || 1 };
    }
    const m = (card.moments || [])[0];
    if (!m || !m.session) return null;
    const a = clockSeconds(m.at), b = clockSeconds(m.until);
    const seconds = a != null && b != null && b > a ? Math.min(60, Math.max(1, b - a)) : 8;
    return { session: m.session, at: m.at, seconds, speed: 1, label: m.label || null };
  }

  function bodyHtml(card, v, key) {
    const groove = v.groove || card.groove || ((tempoOf(card.id) < 80) ? "ballad" : "pulse");
    const backing = v.backing || card.backing || "comp";
    const variants = card.variants || [];
    const moment = momentOf(card);
    const greyed = S.greyed.get(card.id);
    const beatsPerBar = (card.tempo && card.tempo.beats_per_bar) || 4;
    const partner = card.pair ? summaryOf(card.pair.with) : null;
    const parts = [];
    if (card.theory_name) parts.push(`<p class="deck-theory">${esc(card.theory_name)}</p>`);
    if (variants.length) {
      const opts = [];
      if (card.chords && card.chords.length) opts.push({ id: null, label: "main" });
      for (const x of variants) opts.push({ id: x.id, label: `${x.id}${x.label ? ` · ${x.label}` : ""}` });
      parts.push(`<div class="deck-variants" role="tablist">${opts.map((o) =>
        `<button type="button" class="deck-variant" data-variant="${esc(o.id || "")}" aria-selected="${String((o.id || null) === (v.variant || null))}">${esc(o.label)}</button>`).join("")}</div>`);
    }
    parts.push(`<div class="deck-chips" aria-label="Chords: hover to see, click to hear, shift-click to show"></div>`);
    parts.push(`<p class="deck-readsas" hidden></p>`);
    if (card.landing && card.landing.pull) parts.push(`<p class="deck-landing" hidden></p>`);  // filled with the chips (landingText)
    parts.push(`<p class="deck-hint" hidden>numbers stay the same in every key</p>`);
    parts.push(`<div class="deck-controls">
        <label class="deck-field">Key <select class="deck-key" aria-label="Key">${keyOptions(card, key, v)}</select></label>
        <span class="deck-field deck-tempo">Tempo <button type="button" class="deck-btn deck-step" data-step="-1" aria-label="Slower">&minus;</button><span class="deck-bpm">${tempoOf(card.id)}</span><button type="button" class="deck-btn deck-step" data-step="1" aria-label="Faster">+</button> bpm
          <button type="button" class="deck-btn" data-act="tap" title="Tap four times">tap</button></span>
        <span class="deck-field deck-meter">${card.bars ? `bars ${card.bars} &middot; ` : ""}${beatsPerBar}/4</span>
      </div>`);
    const needsClick = voiceReady && !safe(voiceReady, true) ? `<span class="deck-small deck-needs">needs a click</span>` : "";
    parts.push(`<div class="deck-actions">
        <button type="button" class="deck-btn deck-act" data-act="play">Play</button>${needsClick}
        <button type="button" class="deck-btn deck-act" data-act="show">Show</button>
        <button type="button" class="deck-btn deck-act" data-act="loop">Loop</button>
        <button type="button" class="deck-btn deck-act" data-act="try">Try</button>
        ${moment ? `<button type="button" class="deck-btn deck-act" data-act="hear"${greyed ? " disabled" : ""}>Hear me at ${esc(moment.at)}</button>` : ""}
      </div>`);
    parts.push(`<p class="deck-playing" hidden></p>`);  // "playing in E♭ · moves to G at the next pass" (paintPlaying)
    if (greyed) parts.push(`<p class="deck-small deck-greyed">${esc(greyed)}</p>`);
    if ((card.moments || []).length) {
      const ats = card.moments.map((m) => m.at).filter(Boolean);
      const list = ats.length > 1 ? `${ats.slice(0, -1).join(", ")} and ${ats[ats.length - 1]}` : ats[0];
      parts.push(`<p class="deck-moments">You played this at ${esc(list)}.</p>`);
    }
    if (card.pair && partner) {
      const words = card.pair.role === "question" ? "This one asks; the answer is" : "This one answers";
      parts.push(`<p class="deck-pair">${words} <button type="button" class="deck-link" data-act="open-pair">${esc(partner.title)}</button>
        <button type="button" class="deck-btn" data-act="pair">Play the pair</button></p>`);
    }
    const about = [["", card.explanation], ["Why it matters", card.why], ["Try", card.try], ["Listen for", card.listen_for]]
      .filter(([, t]) => t).map(([h, t]) => `<p>${h ? `<b>${esc(h)}</b> ` : ""}${esc(t)}</p>`).join("");
    if (about) parts.push(`<details class="deck-about"><summary>About this</summary>${about}</details>`);
    const opt = (list, cur) => list.map((x) => `<option value="${x}"${x === cur ? " selected" : ""}>${x}</option>`).join("");
    parts.push(`<div class="deck-foot">
        <button type="button" class="deck-btn" data-act="keep">Keep</button>
        <label class="deck-field">groove <select class="deck-groove" aria-label="Loop groove">${opt(GROOVES, groove)}</select></label>
        <label class="deck-field">backing <select class="deck-backing" aria-label="Loop backing">${opt(BACKINGS, backing)}</select></label>
        ${card.group === "kept" ? `<button type="button" class="deck-btn deck-more" data-act="edit" aria-label="Edit this card">&middot;&middot;&middot;</button>` : ""}
      </div>`);
    if (card.group === "kept") {
      parts.push(`<form class="deck-edit" hidden>
          <label class="deck-field">Title <input type="text" name="title" maxlength="80" value="${esc(card.title)}" /></label>
          <label class="deck-field">Meaning <input type="text" name="meaning" maxlength="120" value="${esc(card.meaning || "")}" /></label>
          <label class="deck-field">Tags <input type="text" name="tags" value="${esc((card.tags || []).join(", "))}" /></label>
          <div class="deck-actions"><button type="submit" class="deck-btn">Save</button><button type="button" class="deck-btn" data-act="edit-cancel">Cancel</button></div>
        </form>`);
    }
    return parts.join("");
  }

  function wireBody(body, id) {
    // The body element outlives its innerHTML (a variant switch, a key change or a deck frame renders it again), so its
    // click delegation is attached once: attaching it on every render made one click start N runs or keep N copies.
    if (!body.dataset.wired) body.addEventListener("click", (e) => {
      const b = e.target.closest("[data-act], [data-variant], [data-step]");
      if (!b || !body.contains(b)) return;
      if (b.tagName === "BUTTON") b.blur();
      if (b.dataset.variant !== undefined) {
        const v = viewOf(id);
        v.variant = b.dataset.variant || null;
        followRun(id);  // this card's Loop or Try moves to the variant at its next pass
        renderBody(id);
        return;
      }
      if (b.dataset.step !== undefined) return;  // pointerdown handles steps (hold to repeat)
      const a = b.dataset.act;
      if (a === "tap") return tap(id);
      if (a === "edit") { const f = body.querySelector(".deck-edit"); if (f) f.hidden = !f.hidden; return; }
      if (a === "edit-cancel") { const f = body.querySelector(".deck-edit"); if (f) f.hidden = true; return; }
      if (a === "open-pair") { const card = S.full.get(id); if (card && card.pair) open(card.pair.with); return; }
      act(a, { cardId: id });
    });
    body.dataset.wired = "1";
    for (const b of body.querySelectorAll("[data-step]")) {
      let holdT = 0, everyT = 0;
      const stop = () => { clearTimeout(holdT); clearInterval(everyT); };
      b.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        const d = +b.dataset.step * TEMPO.step;
        stepTempo(id, d);
        holdT = setTimeout(() => { everyT = setInterval(() => stepTempo(id, d), TEMPO.holdEveryMs); }, TEMPO.holdDelayMs);
      });
      for (const ev of ["pointerup", "pointerleave", "pointercancel"]) b.addEventListener(ev, stop);
    }
    const keySel = body.querySelector(".deck-key");
    if (keySel) keySel.addEventListener("change", () => {
      const val = keySel.value;
      keySel.blur();
      if (val === "written" || val === "now") setChoice(id, val, null);
      else if (val.startsWith("key:")) setChoice(id, "key", val.slice(4));
    });
    const g = body.querySelector(".deck-groove"), bk = body.querySelector(".deck-backing");
    if (g) g.addEventListener("change", () => { viewOf(id).groove = g.value; g.blur(); });
    if (bk) bk.addEventListener("change", () => { viewOf(id).backing = bk.value; bk.blur(); });
    const form = body.querySelector(".deck-edit");
    if (form) form.addEventListener("submit", (e) => { e.preventDefault(); saveEdit(id, form); });
  }

  // Chips for a def, or placeholders: before any answer, the card's numbers; while a new key is pending, the last
  // def's names moved by the nearest shift, in grey.
  function renderChips(id, body, def) {
    const chipsEl = body.querySelector(".deck-chips");
    if (!chipsEl) return;
    const v = viewOf(id);
    const key = shownKey(id);
    const mn = minorNow();
    let slots, sections, pending = false;
    if (def) {
      slots = def.slots;
      sections = def.sections || [];
    } else if (v.def && (v.def.card.variant || null) === (v.variant || null)) {
      const shift = keyShift(v.def.key, key);
      slots = v.def.slots.map((s) => ({ ...s, name: transposeName(s.name, shift, key), key: key }));
      sections = [];
      pending = true;
    } else {
      const card = S.full.get(id) || {};
      const variant = (card.variants || []).find((x) => x.id === v.variant);
      const items = variant ? variant.chords : card.chords || [];
      slots = items.filter((it) => it.n !== undefined || it.notes).map((it, i) => ({ i, n: it.n, name: it.name || "", beats: it.beats, key }));
      sections = [];
      pending = true;
    }
    const html = [];
    let lastSection = null, lastEnd = null;
    for (const s of slots) {
      if (sections.length > 1 && s.section !== lastSection) {
        html.push(`<span class="deck-divider">in ${esc(keyWithGlyph(s.key))}</span>`);
      }
      if (def && lastEnd != null && s.at_beat > lastEnd + 1e-6) {
        html.push(`<span class="deck-divider deck-rest">rest ${+(s.at_beat - lastEnd).toFixed(2)}</span>`);
      }
      lastSection = s.section;
      if (def) lastEnd = s.at_beat + s.beats;
      const number = chipNumber(s, mn);
      html.push(`<button type="button" class="deck-chip${pending ? " pending" : ""}" data-slot="${s.i}" data-name="${esc(s.name)}" data-number="${esc(number || "")}"` +
        ` title="hover: see it on the keys · click: hear it · shift-click: keep it shown">` +
        `<span class="chip-name">${s.name ? nameHtml(s.name) : "&hellip;"}</span>` +
        `<span class="chip-num">${number ? numberHtml(number) : "&nbsp;"}</span>` +
        `<span class="chip-beats">${s.beats === 1 ? "1 beat" : `${+s.beats} beats`}</span></button>`);
    }
    chipsEl.innerHTML = html.join("");
    chipsEl.dataset.pending = String(pending);
    chipsEl.dataset.key = key || "";
    for (const chip of chipsEl.querySelectorAll(".deck-chip")) wireChip(chip, id, pending);
    const readsAs = body.querySelector(".deck-readsas");
    if (readsAs) {
      const text = def ? readsAsText(def) : "";
      readsAs.hidden = !text;
      readsAs.textContent = text;
    }
    const landingEl = body.querySelector(".deck-landing");
    if (landingEl) {
      const text = landingText(id, def, key);
      landingEl.hidden = !text;
      landingEl.innerHTML = text ? `<span class="deck-small">lands on</span> ${esc(text)}` : "";
    }
    const hint = body.querySelector(".deck-hint");
    if (hint) hint.hidden = !(def && v.hintArmed && !S.hint);
    if (def && v.hintArmed && !S.hint) { S.hint = true; store.set(STORE.hint, "1"); v.hintArmed = false; }
  }

  // The card's landing line (house idea). Its pull text is written in the card's key, so it shows as written only in
  // that key; in any other key the line is built from the resolved def (the landing note as the server spells it from
  // the chord's own tones, def.landing.note, its role, the chord's name there), and while that def is pending it waits
  // rather than name the wrong notes. The deck never spells a note itself (jam-rulings: no second speller).
  function landingText(id, def, key) {
    const card = S.full.get(id);
    const l = card && card.landing;
    if (!l || !l.pull) return "";
    const v = viewOf(id);
    if (def && !def.landing) return "";
    if (!def && (l.variant || null) !== (v.variant || null)) return "";
    const a = parseKey(card.key || ""), b = parseKey(key || card.key || "");
    if (a && b && a.tonic === b.tonic && a.mode === b.mode) return pullText(l.pull);
    if (!def) return "";
    const dl = def.landing;
    const slot = def.slots.find((s) => s.i === dl.slot) || def.slots[dl.slot];
    if (!slot || !Number.isInteger(dl.pc)) return "";
    const chord = nameText(slot.name);
    const role = String(dl.role || "");
    const what = dl.relative_to === "bass"
      ? (role === "1" ? `the bass note of ${chord}` : `the ${ROLE_WORDS[role] || role} over the bass of ${chord}`)
      : `the ${ROLE_WORDS[role] || role} of ${chord}`;
    return typeof dl.note === "string" && dl.note ? `${nameText(dl.note)}, ${what}` : what;
  }

  // The reads-as line (8.3): what the screen will call a chord Play sounds, when that is not its name. The bridge's
  // "notes" match (an exact-note chord read back note for note) is plain, like exact and enharmonic.
  function readsAsText(def) {
    const odd = new Map();
    for (const s of def.slots) {
      const pr = s.page_reads;
      if (!pr || !pr.name || MATCH_PLAIN.has(pr.match) || pr.name === s.name) continue;
      if (!odd.has(pr.name)) odd.set(pr.name, { letters: !pr.number && /\s/.test(pr.name), slots: [] });
      odd.get(pr.name).slots.push(s.i + 1);
    }
    if (!odd.size) return "";
    const one = def.slots.length === 1;
    const which = (list) => (list.length === 1 ? `chord ${list[0]}` : `chords ${list.slice(0, -1).join(", ")} and ${list[list.length - 1]}`);
    const parts = [...odd.entries()].map(([name, o]) => (o.letters
      ? `shows ${one ? "this one" : which(o.slots)} as the letters ${nameText(name)}, with no chord name`
      : `calls ${one ? "this" : which(o.slots)} ${nameText(name)}`));
    return `your screen ${parts.join("; it ")}: the same notes`;
  }

  function wireChip(chip, id, pending) {
    const slot = +chip.dataset.slot;
    chip.addEventListener("pointerenter", () => {
      if (pending) return;
      clearTimeout(S.hoverTimer);
      S.hoverTimer = setTimeout(() => startHover(id, slot), HOVER_MS);
    });
    chip.addEventListener("pointerleave", () => {
      clearTimeout(S.hoverTimer);
      if (S.hover && S.hover.id === id && S.hover.slot === slot) { S.hover = null; emitGhosts(); }
    });
    chip.addEventListener("click", (e) => {
      chip.blur();
      if (pending) return;
      act(e.shiftKey ? "show" : "play", { cardId: id, slot });
    });
  }

  async function slotFor(id, slot) {
    await loadCard(id);
    const v = viewOf(id);
    const def = await defFor(id, shownKey(id), v.variant);
    return def.slots.find((s) => s.i === slot) || def.slots[0] || null;
  }
  const ghostOf = (s, id) => ({ card: id, slot: s.i, name: s.name, number: chipNumber(s, minorNow()),
                                 notes: ((s.voicings && s.voicings.play) || []).slice() });
  async function startHover(id, slot) {
    try {
      const s = await slotFor(id, slot);
      if (!s) return;
      S.hover = { id, ...ghostOf(s, id) };
      emitGhosts();
    } catch (e) { warn("hover", e); }
  }
  function emitGhosts() {
    const src = S.hover ? { ...S.hover, source: "hover" } : S.show ? { ...S.show, source: "show" } : null;
    counts.ghosts++;
    safe(() => onGhosts(src ? { target: src.notes, incoming: [], hold: [], found: null, source: src.source,
                                 card: src.card, slot: src.slot, name: src.name, number: src.number } : null));
    renderNow();
    renderPill();
  }

  // ------------------------------------------------------------------------------------------ key, tempo, edits --
  function setChoice(id, choice, key) {
    const v = viewOf(id);
    const before = shownKey(id);
    v.choice = choice;
    if (key) v.key = key;
    if (shownKey(id) !== before) v.hintArmed = true;
    const el = cardEls.get(id), sum = summaryOf(id);
    if (el && sum) renderHead(el, sum);
    followRun(id);  // a key picked while this card's Loop or Try plays: Claude moves there at the next pass (9.4)
    if (S.expanded === id) return renderBody(id);
    queueLine(id);
    return Promise.resolve();
  }
  // Receipts and the - = keys: show a card in a key ("Db major"), or back as written (null).
  function setKey(id, key) {
    if (!key) return setChoice(id, "written", null);
    const p = parseKey(key);
    if (!p) return Promise.reject(new Error(`not a key: ${key}`));
    const card = S.full.get(id) || summaryOf(id);
    if (card && parseKey(card.key) && parseKey(card.key).name === p.name) return setChoice(id, "written", null);
    return setChoice(id, "key", key.trim());
  }
  function transpose(id, semis) {
    const key = shownKey(id);
    const p = parseKey(key || "");
    if (!p) return Promise.resolve();
    const tonics = p.mode === "minor" ? MINOR_TONICS : MAJOR_TONICS;
    return setKey(id, `${tonics[mod(p.tonic + semis, 12)]} ${p.mode}`);
  }

  let tempoSendT = 0;
  function stepTempo(id, delta) {
    const v = viewOf(id);
    v.bpm = Math.max(TEMPO.min, Math.min(TEMPO.max, tempoOf(id) + delta));
    paintTempo(id);
    if (runOn(id)) {
      clearTimeout(tempoSendT);
      tempoSendT = setTimeout(() => callTransport("control", "tempo", { bpm: v.bpm }), TEMPO.sendAfterMs);
    }
  }
  function paintTempo(id) {
    const el = cardEls.get(id);
    if (!el) return;
    const bpmEl = el.querySelector(".deck-bpm");
    if (bpmEl) bpmEl.textContent = String(tempoOf(id));
    const sum = summaryOf(id);
    if (sum) renderHead(el, sum);
  }
  function tap(id) {
    const v = viewOf(id);
    const t = now();
    if (v.taps.length && t - v.taps[v.taps.length - 1] > TEMPO.tapResetMs) v.taps = [];
    v.taps.push(t);
    if (v.taps.length > TEMPO.taps) v.taps.shift();
    if (v.taps.length < TEMPO.taps) return;
    const gaps = v.taps.slice(1).map((x, i) => x - v.taps[i]).sort((a, b) => a - b);
    const median = gaps.length % 2 ? gaps[(gaps.length - 1) / 2] : (gaps[gaps.length / 2 - 1] + gaps[gaps.length / 2]) / 2;
    v.bpm = Math.max(TEMPO.tapMin, Math.min(TEMPO.tapMax, Math.round(60000 / median)));
    paintTempo(id);
    if (runOn(id)) callTransport("control", "tempo", { bpm: v.bpm });
  }

  async function saveEdit(id, form) {
    const card = S.full.get(id);
    if (!card) return;
    const data = new FormData(form);
    const tags = String(data.get("tags") || "").split(/[,\s]+/).map((t) => t.trim().toLowerCase()).filter(Boolean);
    const patch = { title: String(data.get("title") || "").trim() || card.title, meaning: String(data.get("meaning") || "").trim() || card.meaning, tags };
    try {
      const out = await http.post(`/api/piano/deck/cards/${encodeURIComponent(id)}/update`, { patch, if_rev: card.rev, by: "daniel" });
      upsertCard(out.card);
      say(`Saved: ${out.card.title}`);
    } catch (e) {
      if (e.status === 409) { S.full.delete(id); say("That card changed underneath; showing the new one."); await refresh(); if (S.expanded === id) renderBody(id); }
      else say(`Could not save the card: ${e.message}`, true);
    }
  }

  // ------------------------------------------------------------------------------------------ actions --
  const transportState = () => normState((transport && typeof transport.state === "function" ? safe(() => transport.state(), null) : null) || S.tstate);
  function runOn(id, mode = null) {
    const st = transportState();
    const r = st && st.run;
    if (!r || ["idle", "stopped", "pending"].includes(st.state) || r.state === "stopped") return false;
    return (!id || (r.card && r.card.id === id)) && (!mode || r.mode === mode);
  }

  // ------------------------------------------------------------------------------------------ the card that plays --
  // Round-2 verify: a key picked while a card's Loop played changed the chips but not the sound, and Loop then stopped
  // the run. Now picking a key or variant on the card that plays moves Claude there at the next pass (9.4's key rule),
  // the Loop and Try buttons show that their run is on (aria-pressed, "Stop"), and a note says what sounds meanwhile.
  const MOVE_AFTER_MS = 350;   // - = pressed in a row send one change
  const MOVE_WAIT_MS = 4000;   // how long a sent change counts as on its way before the position shows it
  const sameKey = (a, b) => { const x = parseKey(a || ""), y = parseKey(b || ""); return !!x && !!y && x.tonic === y.tonic; };
  const whereText = (key, variant) => `${variant ? `${variant} ` : ""}in ${shortKey(key)}`;      // "in E♭", "b in E♭"
  const targetText = (key, variant) => (variant ? `${variant} in ${shortKey(key)}` : shortKey(key)); // "G", "c in G"
  // This card's Loop or Try: {mode, key, variant} it sounds now and {goingKey, goingVariant} it will sound once a
  // change waiting for its line lands (the transport's position: the def in effect and the run's last def), or null.
  function playingOf(id) {
    if (!runOn(id, "loop") && !runOn(id, "try")) return null;
    const st = transportState();
    const pos = S.position && S.position.run === st.run.run ? S.position : null;
    const last = pos && pos.last_def;
    if (last && last.card_id && last.card_id !== id) return null;  // Claude moved the run on to another card
    const card = st.run.card || {};
    const key = (pos && pos.def_key) || st.run.key || null;
    const variant = pos && pos.def_key ? pos.def_variant ?? null : card.variant ?? null;
    return { mode: st.run.mode, key, variant, goingKey: last ? last.key : key, goingVariant: last ? last.variant ?? null : variant };
  }
  function goingOf(id, p) {
    const m = S.moving;
    if (m && m.id === id && now() - m.at < MOVE_WAIT_MS && !(sameKey(p.goingKey, m.key) && p.goingVariant === m.variant)) return m;
    return { key: p.goingKey, variant: p.goingVariant };
  }
  function moveWanted(id, p = playingOf(id)) {
    if (!p) return false;
    const g = goingOf(id, p);
    return !sameKey(g.key, shownKey(id)) || (g.variant || null) !== (viewOf(id).variant || null);
  }
  function moveRun(id) {
    clearTimeout(S.moveT);
    const p = playingOf(id);
    if (!moveWanted(id, p)) return Promise.resolve(null);
    const v = viewOf(id), key = shownKey(id);
    const args = (v.variant || null) === (goingOf(id, p).variant || null)
      ? { key, at: "pass" } : { card_id: id, key, ...(v.variant ? { variant: v.variant } : {}), at: "pass" };
    S.moving = { id, key, variant: v.variant || null, at: now() };
    paintPlaying(id);
    return callTransport("control", "next", args);
  }
  function followRun(id) {
    if (!playingOf(id)) return;
    clearTimeout(S.moveT);
    S.moveT = setTimeout(() => { moveRun(id); }, MOVE_AFTER_MS);
  }
  function paintPlaying(id = S.expanded) {
    if (!id || S.expanded !== id) return;
    const el = cardEls.get(id);
    const body = el && el.querySelector(".deck-card-body");
    if (!body || body.hidden) return;
    const p = playingOf(id);
    const v = viewOf(id), target = shownKey(id);
    const move = moveWanted(id, p);
    for (const mode of ["loop", "try"]) {
      const b = body.querySelector(`.deck-act[data-act="${mode}"]`);
      if (!b) continue;
      const on = !!p && p.mode === mode;
      const word = mode === "loop" ? "Loop" : "Try";
      const label = !on ? word : move ? `${word} ${whereText(target, v.variant)}` : "Stop";
      if (b.getAttribute("aria-pressed") !== String(on)) b.setAttribute("aria-pressed", String(on));
      if (b.textContent !== label) b.textContent = label;
      const title = !on ? "" : move ? `Move this ${word} to ${targetText(target, v.variant)} at the next pass` : `Stop this ${word}`;
      if (b.title !== title) b.title = title;
    }
    const note = body.querySelector(".deck-playing");
    if (!note) return;
    let text = "";
    if (p && (!sameKey(p.key, target) || (p.variant || null) !== (v.variant || null))) {
      const g = goingOf(id, p);
      const going = sameKey(g.key, target) && (g.variant || null) === (v.variant || null);
      text = `playing ${whereText(p.key, p.variant)} · ${going ? "moves" : `${p.mode === "try" ? "Try" : "Loop"} moves it`} to ${targetText(target, v.variant)} at the next pass`;
    }
    if (note.textContent !== text) note.textContent = text;
    note.hidden = !text;
  }
  function callTransport(method, ...args) {
    bump(counts.transport, method === "control" ? `control:${args[0]}` : method);
    if (!transport || typeof transport[method] !== "function") {
      say("Claude's hand is not ready yet: reload the piano page.", true);
      return Promise.resolve(null);
    }
    try {
      return Promise.resolve(transport[method](...args)).catch((e) => { counts.errors++; say(`Claude could not ${method}: ${e.message}`, true); return null; });
    } catch (e) {
      counts.errors++;
      say(`Claude could not ${method}: ${e.message}`, true);
      return Promise.resolve(null);
    }
  }
  function pickCard(opts) {
    if (opts && opts.cardId) return opts.cardId;
    if (S.selected && summaryOf(S.selected)) return S.selected;
    if (S.expanded) return S.expanded;
    const ids = visibleIds();
    if (ids.length) { S.selected = ids[0]; syncSelection(); }
    return ids[0] || null;
  }

  async function startRun(mode, id, opts = {}) {
    safe(unlock);
    if (safe(stopDemo, false)) say("Stopped the Demo so Claude can play.");
    try { await loadCard(id); } catch (e) { say(`This card could not be read: ${e.message}`, true); return null; }
    const card = S.full.get(id);
    const v = viewOf(id);
    const body = { mode, card_id: id, key: shownKey(id), bpm: tempoOf(id), by: "daniel" };
    if (v.variant) body.variant = v.variant;
    if (opts.slot != null) body.slot = opts.slot;
    if (pageId) body.page_id = pageId;
    if (mode === "loop" || mode === "try") body.count_in = S.settings.countIn;
    if (mode === "loop") {
      const groove = v.groove || (S.settings.groove !== "card" ? S.settings.groove : null);
      const backing = v.backing || (S.settings.backing !== "card" ? S.settings.backing : null);
      if (groove) body.groove = groove;
      if (backing) body.backing = backing;
    }
    if (mode === "try") body.try_backing = S.settings.tryBacking;
    markSeen(id);
    S.lastUsed.set(id, wallNow());
    if (card && card.group === "kept") renderTabs();
    return callTransport("start", body);
  }

  async function toggleShow(id, slot = null) {
    if (S.show && S.show.card === id && (slot == null || S.show.slot === slot)) return dismissShow();
    try {
      const s = await slotFor(id, slot == null ? (S.show && S.show.card === id ? S.show.slot : 0) : slot);
      if (!s) return null;
      S.show = { ...ghostOf(s, id) };
      markSeen(id);
      emitGhosts();
      return S.show;
    } catch (e) { say(`Could not show that chord: ${e.message}`, true); return null; }
  }
  function dismissShow() {
    if (!S.show && !S.hover) return null;
    S.show = null;
    S.hover = null;
    emitGhosts();
    return null;
  }

  async function hearMe(id) {
    let card;
    try { card = await loadCard(id); } catch (e) { say(`This card could not be read: ${e.message}`, true); return null; }
    const m = momentOf(card);
    if (!m) { say("This card has no moment of yours to play back."); return null; }
    safe(unlock);
    const qs = new URLSearchParams({ session: m.session, at: m.at, seconds: String(m.seconds), speed: String(m.speed || 1) });
    try {
      const out = await http.get(`/api/piano/replay?${qs}`);
      markSeen(id);
      if (playReplay) safe(() => playReplay(out.cue, { card: id, moment: m }));
      else say("Hear me needs the page's player.", true);
      return out.cue;
    } catch (e) {
      if (e.status === 404) {
        S.greyed.set(id, "that session is no longer in the log");
        if (S.expanded === id) renderBody(id);
      } else say(`Could not play that moment: ${e.message}`, true);
      return null;
    }
  }

  async function keepCard(id) {
    let card;
    try { card = await loadCard(id); } catch (e) { say(`This card could not be read: ${e.message}`, true); return null; }
    const key = shownKey(id);
    const body = { by: "daniel" };
    if (key && parseKey(key) && parseKey(card.key) && parseKey(key).name !== parseKey(card.key).name) body.key = key;
    try {
      const out = await http.post(`/api/piano/deck/cards/${encodeURIComponent(id)}/keep`, body);
      upsertCard(out.card);
      say(`Kept a copy in Kept: ${out.card.title}`);
      return out.card;
    } catch (e) { say(`Could not keep the card: ${e.message}`, true); return null; }
  }

  async function keepWhatIPlayed() {
    const cap = capture ? safe(capture) : null;
    if (!cap || !Array.isArray(cap.notes) || !cap.notes.length) {
      say("Nothing of yours is sounding to keep. Play the chord, then keep it.");
      return null;
    }
    try {
      const out = await http.post("/api/piano/deck/templates", { capture: cap, by: "daniel" });
      upsertCard(out.card);
      say(`Kept: ${out.card.title}`);
      return out.card;
    } catch (e) { say(`Could not keep that chord: ${e.message}`, true); return null; }
  }

  function stopClaude() {
    clearTimeout(S.pairTimer);
    const r = callTransport("stop", "now");
    S.show = null;
    S.hover = null;
    emitGhosts();
    safe(hush);
    return r;
  }

  // A question card and its answer, played one after the other (Heimdall: hearing the hinge is the lesson).
  async function playPair(id) {
    let card;
    try { card = await loadCard(id); } catch { return null; }
    if (!card.pair) return startRun("play", id);
    const first = card.pair.role === "question" ? id : card.pair.with;
    const second = first === id ? card.pair.with : id;
    try { await loadCard(first); await loadCard(second); } catch (e) { say(`Could not read the pair: ${e.message}`, true); return null; }
    await startRun("play", first);
    let ms = 4000;
    try {
      const def = await defFor(first, shownKey(first), viewOf(first).variant);
      ms = def.cycle_beats * 60000 / tempoOf(first) + 900;
    } catch { /* the default gap */ }
    clearTimeout(S.pairTimer);
    S.pairTimer = setTimeout(() => startRun("play", second), ms);
    return { first, second, gap_ms: Math.round(ms) };
  }

  function act(action, opts = {}) {
    bump(counts.actions, action);
    S.lastAction = { action, at: wallNow() };
    switch (action) {
      case "toggle": toggle(); return Promise.resolve(S.open);
      case "up": return Promise.resolve(select(-1));
      case "down": return Promise.resolve(select(1));
      case "stop": return stopClaude();
      case "dismiss": return Promise.resolve(dismissShow());
      case "settings": toggleSettings(); return Promise.resolve(!settingsEl.hidden);
      case "capture": return keepWhatIPlayed();
      case "knock-take": return callTransport("takeKnock");
      case "knock-decline": return callTransport("declineKnock");
      default: break;
    }
    const id = pickCard(opts);
    if (!id) { say("No card to use yet."); return Promise.resolve(null); }
    switch (action) {
      case "play": return startRun("play", id, opts);
      // on the card that plays: moves it to the key or variant shown (when they differ), else stops it
      case "loop": return runOn(id, "loop") ? (moveWanted(id) ? moveRun(id) : stopClaude()) : startRun("loop", id, opts);
      case "try": return runOn(id, "try") ? (moveWanted(id) ? moveRun(id) : stopClaude()) : startRun("try", id, opts);
      case "show": return toggleShow(id, opts.slot == null ? null : opts.slot);
      case "hear": return hearMe(id);
      case "keep": return keepCard(id);
      case "pair": return playPair(id);
      case "open": return Promise.resolve(open(id));
      case "transpose-up": return transpose(id, 1);
      case "transpose-down": return transpose(id, -1);
      case "faster": case "slower": {
        const d = action === "faster" ? TEMPO.key : -TEMPO.key;
        if (runOn(null)) {
          const v = viewOf(id);
          v.bpm = Math.max(TEMPO.min, Math.min(TEMPO.max, tempoOf(id) + d));
          paintTempo(id);
          return callTransport("control", "tempo", { bpm: d > 0 ? `+${d}` : String(d) });
        }
        stepTempo(id, d);
        return Promise.resolve(tempoOf(id));
      }
      default:
        bump(counts.actions, "unknown");
        return Promise.resolve(null);
    }
  }

  // ------------------------------------------------------------------------------------------ keys (8.7) --
  function shortcutFor(e) {
    for (const s of SHORTCUTS) {
      if (s.code !== e.code) continue;
      if (s.shift !== undefined && s.shift !== !!e.shiftKey) continue;
      return s.action;
    }
    return null;
  }
  function handleKey(e) {
    if (!e || S.disposed) return false;
    if (e.ctrlKey || e.metaKey || e.altKey) return false;
    const t = e.target;
    const tag = t && t.tagName;
    if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") {
      if (t === findEl && e.code === "Escape") {
        e.preventDefault();
        findEl.value = "";
        setSearch("");
        findEl.blur();
        return true;
      }
      return false;
    }
    const action = shortcutFor(e);
    if (!action) return false;
    e.preventDefault();
    if (e.repeat) return true;
    bump(counts.keys, action);
    if (action === "enter") {
      const st = transportState();
      if (S.knock || (st && st.knock)) act("knock-take");
      else act("play");
      return true;
    }
    act(action);
    return true;
  }

  // ------------------------------------------------------------------------------------------ frames --
  function upsertCard(card) {
    if (!card || !card.id) return;
    S.full.set(card.id, card);
    const sum = {
      id: card.id, rev: card.rev, title: card.title, meaning: card.meaning, group: card.group, kind: card.kind,
      key: card.key, numbers: (card.chords || []).map((it) => ("key" in it ? `[${it.key}]` : "rest" in it ? null : it.n || "notes")).filter(Boolean).join(" "),
      variants: (card.variants || []).map((x) => x.id), tags: card.tags || [], created_by: card.created_by,
      updated_at: card.updated_at, favorite: !!card.favorite, archived: !!card.archived, runs: 0,
    };
    applyNow({ op: "upsert", card_id: card.id, rev: card.rev, deck_rev: S.doc.rev, by: card.updated_by || "daniel", summary: sum }, true);
  }

  const canMove = () => !S.open || !!safe(isResting, true);
  function applyDeckFrame(frame) {
    const p = frame && frame.deck ? frame.deck : frame;
    if (!p || typeof p.op !== "string") return false;
    counts.frames++;
    if (p.by === "claude" && p.card_id && (p.op === "upsert" || p.op === "restore")) S.sessionIds.add(p.card_id);
    if (p.op === "open") {
      if (canMove() && safe(isResting, true)) open(p.card_id);
      else { S.pendingOpen = p.card_id; if (!S.open) setBadge(S.badge + 1); }
      return true;
    }
    if (p.op === "upsert" || p.op === "restore") {
      const have = summaryOf(p.card_id);
      if (have && Number.isInteger(p.rev) && have.rev >= p.rev) { counts.stale++; return false; }
    }
    if (!canMove()) {
      S.pending.push(p);
      counts.deferred++;
      renderNewPill();
      return true;
    }
    applyNow(p);
    return true;
  }

  function applyNow(p, local = false) {
    counts.applied++;
    if (Number.isInteger(p.deck_rev)) S.doc.rev = Math.max(S.doc.rev, p.deck_rev);
    if (p.op === "seed") { refresh(); return; }
    if (p.op === "order" && Array.isArray(p.order)) S.doc.order = p.order.slice();
    let fresh = null;
    if ((p.op === "upsert" || p.op === "restore") && p.summary) {
      const i = S.doc.cards.findIndex((c) => c.id === p.card_id);
      const isNew = i < 0;
      if (isNew) S.doc.cards.push(p.summary); else S.doc.cards[i] = p.summary;
      if (!local) S.full.delete(p.card_id);
      if (isNew && !S.doc.order.includes(p.card_id)) S.doc.order.push(p.card_id);
      if (isNew && p.by === "claude") fresh = p.summary;
      if (p.by === "claude" && !local) announce(p.summary, isNew);
    }
    if (p.op === "delete") {
      S.doc.cards = S.doc.cards.filter((c) => c.id !== p.card_id);
      S.full.delete(p.card_id);
      if (S.selected === p.card_id) S.selected = null;
      if (S.expanded === p.card_id) S.expanded = null;
    }
    renderTabs();
    renderList();
    if (fresh && S.open) {
      const el = cardEls.get(fresh.id);
      if (el && !el.hidden) {
        el.classList.add("arriving");
        setTimeout(() => el.classList.remove("arriving"), 400);
        S.selected = fresh.id;
        syncSelection();
        el.scrollIntoView({ block: "nearest" });
      } else {
        const tb = [...tabsEl.children].find((b) => b.dataset.tab === fresh.group);
        if (tb) { tb.classList.remove("pulse"); void tb.offsetWidth; tb.classList.add("pulse"); }
      }
    }
    if (S.expanded && S.expanded === p.card_id && (p.op === "upsert" || p.op === "restore")) renderBody(p.card_id);
  }

  function announce(sum, isNew) {
    if (S.open) return;
    if (isNew) setBadge(S.badge + 1);
    clearTimeout(S.noteTimer);
    note.innerHTML = `<span>Claude ${isNew ? "added" : "updated"} a card: ${esc(sum.title)}</span> <button type="button" class="deck-btn" data-open="${esc(sum.id)}">Open <kbd>A</kbd></button>`;
    note.hidden = false;
    S.noteTimer = setTimeout(() => { note.hidden = true; }, NOTE_MS);
  }
  note.addEventListener("click", (e) => {
    const b = e.target.closest("[data-open]");
    if (!b) return;
    b.blur();
    note.hidden = true;
    open(b.dataset.open);
  });

  function flushPending() {
    if (!S.pending.length && !S.pendingOpen) return;
    const frames = S.pending.splice(0);
    for (const p of frames) applyNow(p);
    renderNewPill();
    if (S.pendingOpen) { const id = S.pendingOpen; S.pendingOpen = null; open(id); }
  }
  function renderNewPill() {
    const n = S.pending.filter((p) => (p.op === "upsert" || p.op === "restore") && !summaryOf(p.card_id)).length;
    const other = S.pending.length - n;
    newPill.hidden = !S.pending.length;
    newPill.textContent = n ? `( ${n} new card${n === 1 ? "" : "s"} · show )` : other ? "( cards changed · show )" : "";
  }
  newPill.addEventListener("click", () => { newPill.blur(); flushPending(); });

  function setBadge(n) {
    S.badge = Math.max(0, n);
    badgeEl.hidden = !S.badge;
    badgeEl.textContent = S.badge ? String(S.badge) : "";
  }

  // ------------------------------------------------------------------------------------------ open, close, select --
  function open(cardId = null) {
    const was = S.open;
    S.open = true;
    S.peek = false;
    setBadge(0);
    note.hidden = true;
    relayout();
    if (cardId && summaryOf(cardId)) {
      const sum = summaryOf(cardId);
      if (!inTab(sum, S.tab)) { S.tab = sum.archived ? "all" : sum.group; renderTabs(); renderList(); }
      if (!matches(cardId)) { S.search = ""; findEl.value = ""; renderList(); }
      S.selected = cardId;
      toggleExpand(cardId, true).then(() => { const el = cardEls.get(cardId); if (el) el.scrollIntoView({ block: "nearest" }); });
    }
    if (!was) safe(() => onOpenChange({ open: true, layout: S.layout }));
    renderPill();
    return S.layout;
  }
  function close() {
    if (!S.open) return S.layout;
    S.open = false;
    S.peek = false;
    clearTimeout(S.hoverTimer);
    if (S.hover) { S.hover = null; emitGhosts(); }
    settingsEl.hidden = true;
    relayout();
    safe(() => onOpenChange({ open: false, layout: S.layout }));
    renderPill();
    return S.layout;
  }
  const toggle = () => (S.open ? close() : open());
  function select(delta) {
    const ids = visibleIds();
    if (!ids.length) return null;
    const i = ids.indexOf(S.selected);
    const next = i < 0 ? (delta > 0 ? 0 : ids.length - 1) : Math.max(0, Math.min(ids.length - 1, i + delta));
    S.selected = ids[next];
    syncSelection();
    const el = cardEls.get(S.selected);
    if (el && S.open) el.scrollIntoView({ block: "nearest" });
    return S.selected;
  }
  function setSearch(text) {
    S.search = text;
    renderList();
  }

  // ------------------------------------------------------------------------------------------ layout (8.1) --
  function undockedCanvasWidth(sr) {
    const f = typeof framing === "function" ? safe(framing) : framing;
    const w = f && f.w ? f.w : canvasEl ? canvasEl.width : 0;
    const h = f && f.h ? f.h : canvasEl ? canvasEl.height : 0;
    if (!w || !h) return sr.width;
    const p = pad ? safe(pad, 14) : doc.fullscreenElement ? 0 : 14;
    const scale = Math.max(0.05, Math.min((sr.width - 2 * p) / w, (sr.height - 2 * p) / h));
    return Math.floor(w * scale);
  }
  function computeLayout() {
    const rec = !!safe(isRecording, false);
    const sr = stage.getBoundingClientRect();
    const canvasW = undockedCanvasWidth(sr);
    const margin = (sr.width - canvasW) / 2;
    let dock;
    if (rec) {
      if (S.frozenDock == null) S.frozenDock = S.lastDock;
      dock = S.frozenDock;
    } else {
      S.frozenDock = null;
      dock = S.open && margin < OVERLAY_MARGIN ? DECK_WIDTH : 0;
      S.lastDock = dock;
    }
    const mode = !S.open ? "closed" : dock ? "dock" : "overlay";
    const peekable = rec && S.open && !dock && margin < OVERLAY_MARGIN;
    if (!peekable) S.peek = false;
    return { api: DECK_API, mode, open: S.open, width: DECK_WIDTH, dockWidth: dock, margin: +margin.toFixed(1),
             overlayMargin: OVERLAY_MARGIN, recording: rec, frozen: S.frozenDock != null, peekable, peek: S.peek,
             stage: { width: sr.width, height: sr.height } };
  }
  function relayout() {
    const L = computeLayout();
    const changed = !S.layout || S.layout.dockWidth !== L.dockWidth;
    S.layout = L;
    S.recording = L.recording;
    counts.layouts++;
    aside.dataset.open = String(L.open);
    aside.dataset.mode = L.mode;
    aside.dataset.peek = String(L.peek);
    peekBtn.hidden = !L.peekable;
    stage.classList.toggle("deck-dock", L.dockWidth > 0);
    stage.classList.toggle("deck-open", L.open);
    if (changed) safe(() => onLayout(L));
    placePill();
    return L;
  }
  const layout = () => relayout();
  peekBtn.addEventListener("click", () => { peekBtn.blur(); S.peek = !S.peek; relayout(); });
  tabBtn.addEventListener("click", () => { tabBtn.blur(); open(); });

  // ------------------------------------------------------------------------------------------ Now header, pill --
  const runOf = () => {
    const st = transportState();
    return st && st.run && !["idle", "stopped", "pending"].includes(st.state) ? st : null;
  };
  function slotName(ref, def) {
    if (ref == null) return null;
    if (typeof ref === "object") return ref;
    return def && def.slots ? def.slots.find((s) => s.i === ref) || null : null;
  }
  // The loop's length in beats for a running card, from a def the page was handed or one this deck resolved (a def's
  // cycle does not depend on its key); asked for once when neither is at hand.
  const cycleAsked = new Set();
  function cycleBeatsOf(card, def, runId = null) {
    if (def && def.cycle_beats) return def.cycle_beats;
    if (runId && S.runDefs.has(runId)) return S.runDefs.get(runId).cycle_beats || null;
    if (card && card.id) {
      const variant = card.variant || "";
      for (const [k, d] of S.resolved) {
        const parts = k.split("|");
        if (parts[0] === card.id && parts[3] === variant && d && d.cycle_beats) return d.cycle_beats;
      }
      if (summaryOf(card.id)) {
        if (!cycleAsked.has(card.id)) {
          cycleAsked.add(card.id);
          defFor(card.id, summaryOf(card.id).key, card.variant || null).then(() => { renderNow(); renderPill(); }).catch(() => {});
        }
        return null;
      }
    }
    // a card this deck has not loaded (one Claude added while Daniel played, still behind the new-cards pill) or bare
    // chords: the server's own def for the run, asked once
    if (runId && !cycleAsked.has(`run:${runId}`)) {
      cycleAsked.add(`run:${runId}`);
      http.get("/api/piano/jam").then((doc) => {
        if (doc && doc.run && doc.run.run === runId && doc.def && doc.def.cycle_beats) {
          S.runDefs.set(runId, doc.def);
          renderNow();
          renderPill();
        }
      }).catch(() => {});
    }
    return null;
  }
  // The Now header's view of the run, from either position shape: J7's onPosition ({run: id, mode, card, bar, beat,
  // beats_per_bar, pass, cycle_beat, slot index, chord {name, n, key}, next {slot, name, n, key}, rest, counting_in,
  // countdown, bpm, key}) or one carrying the def and the run object ({run: {...}, def, slot, next}).
  function positionView() {
    const st = runOf();
    const pos = S.position;
    if (!st && !pos) return null;
    const run = pos && pos.run && typeof pos.run === "object" ? pos.run
      : pos ? { run: pos.run, mode: pos.mode, card: pos.card, key: pos.key, beats_per_bar: pos.beats_per_bar } : (st && st.run) || {};
    const def = (pos && pos.def) || (st && st.def) || S.runDef || null;
    const bpb = (pos && pos.beats_per_bar) || run.beats_per_bar || (def && def.beats_per_bar) || 4;
    const bar = pos && Number.isFinite(pos.bar) ? pos.bar : null;
    const beat = pos && Number.isFinite(pos.beat) ? pos.beat : 0;
    const counting = pos && typeof pos.counting_in === "boolean" ? pos.counting_in : bar != null && bar < 0;
    const cycleBeats = cycleBeatsOf(run.card, def, typeof run.run === "string" ? run.run : null);
    const cycleBars = cycleBeats ? Math.max(1, Math.round(cycleBeats / bpb)) : null;
    let inCycle = null;  // beats into the loop
    if (pos && Number.isFinite(pos.cycle_beat)) inCycle = pos.cycle_beat;
    else if (bar != null && cycleBars) {
      const seg = run.segments ? [...run.segments].reverse().find((s) => s.from_bar <= bar) : null;
      const fromBar = seg && Number.isFinite(seg.def_from_bar) ? seg.def_from_bar : 0;
      inCycle = mod(bar - fromBar, cycleBars) * bpb + beat;
    }
    const mn = minorNow();
    const nowSlot = (pos && pos.chord) || slotName(pos && pos.slot, def);
    const nextSlot = slotName(pos && pos.next, def);
    return {
      mode: run.mode || "loop", title: (run.card && run.card.title) || (def && def.card && def.card.title) || "these chords",
      key: (nowSlot && nowSlot.key) || (pos && pos.key) || run.key || (def && def.key) || "", bpm: (pos && pos.bpm) || null,
      bpb, bar, beat, counting,
      countdown: counting ? (pos && Number.isFinite(pos.countdown) ? pos.countdown : Math.max(1, bpb - Math.floor(beat + 1e-6))) : null,
      barInCycle: !counting && inCycle != null ? Math.floor(inCycle / bpb + 1e-6) % (cycleBars || Infinity) + 1 : null,
      cycleBars,
      pass: pos && Number.isFinite(pos.pass) ? pos.pass + 1 : null,
      progress: !counting && inCycle != null && cycleBeats ? (inCycle % cycleBeats) / cycleBeats : 0,
      now: pos && pos.rest ? { name: "", number: null, rest: true }
        : nowSlot ? { name: nowSlot.name, number: chipNumber(nowSlot, mn), rest: !!nowSlot.rest } : null,
      next: nextSlot ? { name: nextSlot.name, number: chipNumber(nextSlot, mn) } : null,
    };
  }
  const pipsHtml = (n, beat, counting) => Array.from({ length: n }, (_, i) =>
    `<i class="pip${Math.floor(beat + 1e-6) === i ? " on" : ""}${counting ? " count" : ""}"></i>`).join("");

  function renderNow() {
    const knock = S.knock;
    const pv = positionView();
    const state = knock ? "knock" : pv ? "run" : S.show ? "show" : "idle";
    nowEl.dataset.state = state;
    aside.dataset.now = state;
    if (state === "knock") {
      const words = { play: "a chord", loop: "a Loop", try: "a Try" }[knock.mode] || "something";
      nowEl.querySelector(".knock-text").textContent = `Claude has ${words} for you${knock.title ? `: ${knock.title}` : ""}`;
      const waited = Math.max(0, Math.floor((now() - (knock.since || now())) / 1000));
      nowEl.querySelector(".knock-wait").textContent = `waiting ${Math.floor(waited / 60)}:${String(waited % 60).padStart(2, "0")}`;
    } else if (state === "run") {
      nowEl.querySelector(".now-kind").textContent = KIND_WORD[pv.mode] || pv.mode.toUpperCase();
      nowEl.querySelector(".now-title").textContent = pv.title;
      nowEl.querySelector(".now-meta").textContent = [shortKey(pv.key), pv.bpm ? `${Math.round(pv.bpm)} bpm` : ""].filter(Boolean).join(" · ");
      nowEl.querySelector(".now-chord").innerHTML = pv.now ? (pv.now.rest ? "rest" : nameHtml(pv.now.name)) : "";
      nowEl.querySelector(".now-num").innerHTML = pv.now && pv.now.number ? numberHtml(pv.now.number) : "";
      nowEl.querySelector(".now-next").innerHTML = pv.next ? nameHtml(pv.next.name) : "";
      nowEl.querySelector(".now-next-num").innerHTML = pv.next && pv.next.number ? numberHtml(pv.next.number) : "";
      nowEl.querySelector(".now-next-label").hidden = !pv.next;
      nowEl.querySelector(".now-pips").innerHTML = pipsHtml(pv.bpb, pv.beat, pv.counting);
      nowEl.querySelector(".now-bar").textContent = pv.barInCycle ? (pv.cycleBars ? `bar ${pv.barInCycle} of ${pv.cycleBars}` : `bar ${pv.barInCycle}`)
        : pv.counting ? "count-in" : "";
      nowEl.querySelector(".now-pass").textContent = pv.pass ? `pass ${pv.pass}` : "";
      const count = nowEl.querySelector(".now-count");
      count.hidden = !pv.counting;
      count.textContent = pv.counting ? String(pv.countdown) : "";
      nowEl.querySelector(".now-found").hidden = !(pv.mode === "try" && now() < S.foundUntil);
      nowEl.querySelector(".now-progress span").style.width = `${Math.round(Math.max(0, Math.min(1, pv.progress)) * 1000) / 10}%`;
      const vol = nowEl.querySelector(".now-vol"), duck = nowEl.querySelector(".now-duck");
      if (doc.activeElement !== vol) vol.value = String(S.settings.volume);
      duck.checked = !!S.settings.duck;
    } else if (state === "show") {
      nowEl.querySelector(".show-chord").innerHTML = nameHtml(S.show.name);
      nowEl.querySelector(".show-num").innerHTML = S.show.number ? numberHtml(S.show.number) : "";
    } else {
      const statusText = cueClient && typeof cueClient.status === "function" ? safe(() => cueClient.status(), null) : null;
      nowEl.querySelector(".now-status").textContent = `Claude's hand: ${typeof statusText === "string" ? statusText : "listening"}`;
    }
  }
  nowEl.addEventListener("click", (e) => {
    const b = e.target.closest("[data-act]");
    if (!b) return;
    b.blur();
    act(b.dataset.act);
  });
  nowEl.querySelector(".now-vol").addEventListener("input", (e) => setSetting("volume", +e.target.value));
  nowEl.querySelector(".now-vol").addEventListener("change", (e) => e.target.blur());
  nowEl.querySelector(".now-duck").addEventListener("change", (e) => { setSetting("duck", e.target.checked); e.target.blur(); });

  function renderPill() {
    const pv = positionView();
    const state = S.knock ? "knock" : pv ? "run" : S.show ? "show" : null;
    const show = !!state && !S.open;
    pill.dataset.state = state || "";
    if (!show) { pill.hidden = true; return; }
    const cards = `<button type="button" class="deck-btn" data-pill="cards">Cards${S.badge ? ` <b>${S.badge}</b>` : ""}</button>`;
    let html;
    if (state === "knock") {
      html = `<span class="knock-dot" aria-hidden="true"></span><span class="pill-text">Claude has ${esc({ play: "a chord", loop: "a Loop", try: "a Try" }[S.knock.mode] || "something")} for you</span>` +
        `<button type="button" class="deck-btn" data-pill="take">Hear <kbd>&#9166;</kbd></button><button type="button" class="deck-btn" data-pill="decline" aria-label="Not now">&times;</button>`;
    } else if (state === "run") {
      html = `<span class="now-pips">${pipsHtml(pv.bpb, pv.beat, pv.counting)}</span>` +
        `<span class="pill-now">${pv.counting ? String(pv.countdown) : pv.now ? (pv.now.rest ? "rest" : nameHtml(pv.now.name)) : ""}</span>` +
        (pv.next && !pv.counting ? `<span class="pill-sep">&rsaquo;</span><span class="pill-next">${nameHtml(pv.next.name)}</span>` : "") +
        `<span class="pill-bar">${pv.barInCycle ? (pv.cycleBars ? `bar ${pv.barInCycle}/${pv.cycleBars}` : `bar ${pv.barInCycle}`) : ""}</span>` +
        `<button type="button" class="deck-btn" data-pill="stop">Stop</button>${cards}`;
    } else {
      html = `<span class="now-kicker">SHOWING</span><span class="pill-now">${nameHtml(S.show.name)}</span>` +
        `<span class="pill-num">${S.show.number ? numberHtml(S.show.number) : ""}</span>` +
        `<button type="button" class="deck-btn" data-pill="dismiss">Dismiss</button>${cards}`;
    }
    if (pill.innerHTML !== html) pill.innerHTML = html;
    pill.hidden = false;
    placePill();
  }
  pill.addEventListener("click", (e) => {
    const b = e.target.closest("[data-pill]");
    if (!b) return;
    b.blur();
    const a = b.dataset.pill;
    if (a === "cards") open();
    else if (a === "stop") act("stop");
    else if (a === "dismiss") act("dismiss");
    else if (a === "take") act("knock-take");
    else if (a === "decline") act("knock-decline");
  });

  // The pill sits on the canvas box: 9:16 centred 14 px above its bottom; 16:9 at its bottom-right corner; in the
  // letterbox below the canvas when that is at least 56 px tall.
  function placePill() {
    if (pill.hidden || !canvasEl) return;
    const sr = stage.getBoundingClientRect(), cr = canvasEl.getBoundingClientRect();
    const left = cr.left - sr.left - stage.clientLeft, top = cr.top - sr.top - stage.clientTop;
    const below = sr.height - (top + cr.height);
    pill.style.maxWidth = `${Math.max(120, Math.min(560, cr.width - 24))}px`;
    const pw = pill.offsetWidth;
    const f = typeof framing === "function" ? safe(framing) : framing;
    const portrait = f && f.w ? f.w < f.h : cr.width < cr.height;
    let x, y;
    if (below >= LETTERBOX_MIN) {
      x = left + (cr.width - pw) / 2;
      y = top + cr.height + (below - PILL_HEIGHT) / 2;
    } else if (portrait) {
      x = left + (cr.width - pw) / 2;
      y = top + cr.height - PILL_INSET - PILL_HEIGHT;
    } else {
      x = left + cr.width - PILL_INSET - pw;
      y = top + cr.height - PILL_INSET - PILL_HEIGHT;
    }
    pill.style.left = `${Math.round(x)}px`;
    pill.style.top = `${Math.round(y)}px`;
  }

  function showPosition(pos) {
    S.position = pos ? { ...pos } : null;
    if (pos && pos.def) S.runDef = pos.def;
    renderNow();
    renderPill();
    paintPlaying();
  }
  function showState(raw) {
    const st = normState(raw);
    S.tstate = st;
    if (st && st.def) S.runDef = st.def;
    const k = st && st.knock;
    if (k) {
      // J7: {run, mode, card, at_epoch_ms}; the knock's clock is the wall clock it arrived on, so a page reopened
      // mid-knock still counts from then
      const since = Number.isFinite(k.since) ? k.since
        : Number.isFinite(k.at_epoch_ms) ? now() - Math.max(0, wallNow() - k.at_epoch_ms)
        : S.knock && S.knock.run === (k.run || null) ? S.knock.since : now();
      S.knock = { run: k.run || null, mode: k.mode || (st.run && st.run.mode) || "loop",
                  title: k.title || (k.card && k.card.title) || (st.run && st.run.card && st.run.card.title) || null, since };
    } else S.knock = null;
    if (!st || ["idle", "stopped"].includes(st.state)) S.position = null;
    renderNow();
    renderPill();
    paintPlaying();
  }
  function flashFound() {
    S.foundUntil = now() + FOUND_MS;
    renderNow();
  }

  // ------------------------------------------------------------------------------------------ settings (8.8) --
  function setSetting(name, value) {
    if (!(name in SETTING_DEFAULTS)) return;
    S.settings[name] = value;
    const stored = name === "duck" || name === "knock" ? (value ? "on" : "off") : String(value);
    if (!(name === "view" && q.get("jam"))) store.set(STORE[name], stored);
    safe(() => onSettings({ ...S.settings }, name));
  }
  function toggleSettings() {
    if (!settingsEl.hidden) { settingsEl.hidden = true; return; }
    const s = S.settings;
    const sel = (name, list) => `<select data-setting="${name}">${list.map(([v, l]) => `<option value="${v}"${String(s[name]) === String(v) ? " selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
    settingsEl.innerHTML = `
      <div class="set-head"><span class="now-kicker">DECK SETTINGS</span><button type="button" class="deck-btn" data-set-close>Done</button></div>
      <label class="set-row">Jam view ${sel("view", [["auto", "auto: on the keys, off them while REC runs"], ["glass", "glass: off the recorded canvas always"]])}</label>
      <label class="set-row">Claude volume <input type="range" min="0" max="1" step="0.01" data-setting="volume" value="${s.volume}" /></label>
      <p class="set-note">If Chrome plays through the interface whose Loopback you record, Claude's sound reaches that input whatever this page does.</p>
      <label class="set-row"><input type="checkbox" data-setting="duck"${s.duck ? " checked" : ""} /> Duck Claude when I play (Loop and Try)</label>
      <label class="set-row">Loop groove ${sel("groove", [["card", "the card's"], ...GROOVES.map((g) => [g, g])])}</label>
      <label class="set-row">Loop backing ${sel("backing", [["card", "the card's"], ...BACKINGS.map((b) => [b, b])])}</label>
      <label class="set-row">Try backing ${sel("tryBacking", [["ghosts", "ghosts only"], ["bass", "with bass"], ["loop", "with loop"]])}</label>
      <label class="set-row">Count-in ${sel("countIn", [["0", "none"], ["1", "1 bar"], ["2", "2 bars"]])}</label>
      <label class="set-row"><input type="checkbox" data-setting="knock"${s.knock ? " checked" : ""} /> Let Claude knock while I play</label>`;
    settingsEl.hidden = false;
  }
  settingsEl.addEventListener("change", (e) => {
    const t = e.target.closest("[data-setting]");
    if (!t) return;
    const name = t.dataset.setting;
    const value = t.type === "checkbox" ? t.checked : name === "volume" ? +t.value : name === "countIn" ? +t.value : t.value;
    setSetting(name, value);
    t.blur();
  });
  settingsEl.addEventListener("click", (e) => { if (e.target.closest("[data-set-close]")) { e.target.blur(); settingsEl.hidden = true; } });

  // ------------------------------------------------------------------------------------------ list events --
  tabsEl.addEventListener("click", (e) => {
    const b = e.target.closest("[data-tab]");
    if (!b) return;
    b.blur();
    S.tab = b.dataset.tab;
    store.set(STORE.tab, S.tab);
    renderTabs();
    renderList();
  });
  findEl.addEventListener("input", () => setSearch(findEl.value));

  // One ticker: waiting frames flush at his rest, REC changes the layout rule, the knock clock, "my key now".
  let lastTracker = trackerKey();
  const ticker = setInterval(() => {
    if (S.disposed) return;
    if ((S.pending.length || S.pendingOpen) && safe(isResting, true)) flushPending();
    const rec = !!safe(isRecording, false);
    if (rec !== S.recording) relayout();
    if (S.knock) renderNow();
    if (S.foundUntil && now() > S.foundUntil) { S.foundUntil = 0; renderNow(); }
    const tk = trackerKey();
    if (tk !== lastTracker) {
      lastTracker = tk;
      for (const [id, v] of S.view) if (v.choice === "now") { if (S.expanded === id) renderBody(id); else queueLine(id); }
    }
  }, tickMs);
  const ro = typeof win.ResizeObserver === "function" ? new win.ResizeObserver(() => relayout()) : null;
  if (ro) ro.observe(stage);
  const onFs = () => relayout();
  doc.addEventListener("fullscreenchange", onFs);

  // ------------------------------------------------------------------------------------------ boot --
  relayout();
  const ready = autoRefresh ? refresh().then(() => {
    const qc = q.get("card");
    if (q.get("deck") === "open" || qc) open(qc && summaryOf(qc) ? qc : null);
  }) : Promise.resolve();

  function chips(id) {
    const el = cardEls.get(id);
    const c = el && el.querySelector(".deck-chips");
    if (!c) return null;
    return { key: c.dataset.key, pending: c.dataset.pending === "true",
             chips: [...c.querySelectorAll(".deck-chip")].map((b) => ({ slot: +b.dataset.slot, name: b.dataset.name,
               number: b.dataset.number || null, text: b.querySelector(".chip-name").textContent,
               numberText: b.querySelector(".chip-num").textContent, beats: b.querySelector(".chip-beats").textContent })),
             readsAs: (el.querySelector(".deck-readsas:not([hidden])") || {}).textContent || null };
  }

  function stats() {
    const pv = positionView();
    return {
      api: DECK_API, open: S.open, layout: S.layout, tab: S.tab, search: S.search, deckRev: S.doc.rev,
      cards: S.doc.cards.length, visible: visibleIds().length, selected: S.selected, expanded: S.expanded,
      pendingFrames: S.pending.length, badge: S.badge, frames: counts.frames, deferred: counts.deferred,
      applied: counts.applied, stale: counts.stale, refreshes: counts.refreshes, resolves: counts.resolves,
      errors: counts.errors, actions: { ...counts.actions }, keys: { ...counts.keys }, transport: { ...counts.transport },
      ghosts: counts.ghosts, show: S.show ? { card: S.show.card, slot: S.show.slot, name: S.show.name, number: S.show.number } : null,
      hover: S.hover ? { card: S.hover.card, slot: S.hover.slot } : null, knock: S.knock ? { ...S.knock } : null,
      now: nowEl.dataset.state, pill: pill.hidden ? null : pill.dataset.state,
      position: pv ? { bar: pv.bar, barInCycle: pv.barInCycle, pass: pv.pass, now: pv.now, next: pv.next, countdown: pv.countdown } : null,
      settings: { ...S.settings }, glass: glass && typeof glass.stats === "function" ? safe(() => glass.stats()) : null,
    };
  }

  function dispose() {
    S.disposed = true;
    clearInterval(ticker);
    clearTimeout(S.hoverTimer);
    clearTimeout(S.noteTimer);
    clearTimeout(S.pairTimer);
    clearTimeout(S.moveT);
    clearTimeout(tempoSendT);
    if (ro) ro.disconnect();
    doc.removeEventListener("fullscreenchange", onFs);
    stage.classList.remove("deck-dock", "deck-open");
    pill.remove();
    note.remove();
    if (!root) aside.remove(); else aside.innerHTML = "";
  }

  return {
    open, close, toggle, select, act, applyDeckFrame, refresh, layout, stats, handleKey,
    showPosition, showState, flashFound, setKey, chips, ready,
    settings: () => ({ ...S.settings }), element: aside, pill,
    selected: () => S.selected, visible: visibleIds, dispose,
  };
}
