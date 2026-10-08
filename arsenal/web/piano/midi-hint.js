// The Rescan hint on /piano: gathers the facts, asks the model (midi-hint-model.mjs) which gentle hint answers this
// moment, and renders a small card anchored beside Rescan.
//
// It is the first brick of the house's gentle-hint primitive (roadmap P1,
// docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md):
//   - beside the control, never over the stage;
//   - DOM only, so never in a take (REC records the canvas);
//   - never popping up on its own;
//   - gone on success.
// The facts it adds to the page's own: what Windows sees (GET /api/midi/ports, asked only when nothing is bound), the
// MIDI permission state, and which browser this is (for its restart door).
import { decideMidiHint, matchEgg, NARRATE_MS, SUCCESS_LINGER_MS, SOUND_CHECK_GIVE_UP_MS } from "./midi-hint-model.mjs";

const FAIL = new Set(["missing", "stale", "stopped", "blocked", "idle"]);
const LINGERING = new Set(["heard", "egg", "banter"]);  // cards that leave by their own fade, never on a null verdict
const PORTS_TIMEOUT_MS = 1500;
const EGG_LINGER_MS = 7_000;          // long enough to read the punchline
const WRY_LINGER_MS = 4_500;
const BANTER_WINDOW_MS = 5 * 60_000;  // presses within this long of a success climb the deadpan ladder
const NOTE_BUFFER = 12;               // note-ons the eggs remember
const TICK_MS = 250;  // fine enough to catch a held note for the narration; it only runs for two minutes after a press

export function browserIdentity(nav = globalThis.navigator || {}) {
  if (nav.brave) return { name: "Brave", restartUrl: "brave://restart" };
  const ua = nav.userAgent || "";
  if (/\bEdg\//.test(ua)) return { name: "Edge", restartUrl: "edge://restart" };
  if (/\bFirefox\//.test(ua)) return { name: "Firefox", restartUrl: null };
  if (/\bChrome\//.test(ua)) return { name: "Chrome", restartUrl: "chrome://restart" };
  return { name: "your browser", restartUrl: null };
}

async function fetchPorts(endpoint) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), PORTS_TIMEOUT_MS);
  try {
    const r = await fetch(endpoint, { cache: "no-store", signal: ctl.signal });
    return r.ok ? await r.json() : null;  // a server without the route answers 404: then no claim about Windows
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function midiPermission() {
  try { return (await navigator.permissions.query({ name: "midi" })).state; } catch { return "unknown"; }
}

const make = (tag, className, text) => {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text != null) el.textContent = text;
  return el;
};

// queryPermission and fetchWindows are seams for tests and demos; the page uses the defaults.
export function createMidiHint({ anchor, readFacts, endpoint = "/api/midi/ports",
                                 queryPermission = midiPermission, fetchWindows = fetchPorts }) {
  const presses = [];
  const shown = {};
  const browser = browserIdentity();
  let eventsAtPress = 0, windows = null, permission = "unknown";
  let open = null, deferred = false, quietAfter = -1, ticker = 0, lingerTimer = 0;
  let heardShown = null, narrateUntil = 0;  // the "Heard you" narration: its current title, and when it stops renaming
  let banter = 0, successAt = 0, lastHeard = null;  // the deadpan ladder: its rung, the last success, the last note named
  const noteBuf = [];                               // recent note-ons, for the eggs

  const el = make("div", "midi-hint");
  el.setAttribute("role", "status");
  el.setAttribute("aria-live", "polite");
  el.setAttribute("aria-hidden", "true");
  const close = make("button", "midi-hint-close", "×");
  close.type = "button";
  close.setAttribute("aria-label", "Dismiss");
  const title = make("p", "midi-hint-title");
  const body = make("p", "midi-hint-body");
  const chainEl = make("ol", "midi-hint-chain");
  const actionEl = make("div", "midi-hint-action");
  el.append(close, title, body, chainEl, actionEl);
  document.body.append(el);

  close.addEventListener("click", () => { close.blur(); dismiss(); });  // blur: Space must stay the piano's
  const onKey = (e) => { if (e.key === "Escape" && open) dismiss(); };
  const onResize = () => { if (el.classList.contains("is-on")) place(); };
  addEventListener("keydown", onKey);
  addEventListener("resize", onResize);

  function place() {
    const a = anchor && anchor();
    const r = a && a.getBoundingClientRect ? a.getBoundingClientRect() : null;
    if (r && r.width) {
      el.style.top = `${Math.round(r.bottom + 10)}px`;
      el.style.right = `${Math.max(12, Math.round(innerWidth - r.right))}px`;
    } else {  // Rescan hidden (a compact or focus layout): the top-right corner
      el.style.top = "72px";
      el.style.right = "12px";
    }
  }

  function render(v) {
    clearTimeout(lingerTimer);
    el.dataset.tone = v.tone;
    el.dataset.level = String(v.level);
    title.textContent = v.title;
    body.textContent = v.body;
    chainEl.replaceChildren();
    if (v.chain) {  // lit up to the step where the signal stops; the steps after it never saw it
      let broken = false;
      for (const node of v.chain) {
        const li = make("li");
        li.dataset.status = node.status;
        if (!broken && FAIL.has(node.status)) { li.classList.add("is-break"); broken = true; }
        li.append(make("i"), node.label);
        li.title = `${node.label}: ${node.status}`;
        chainEl.append(li);
      }
    }
    chainEl.hidden = !v.chain;
    actionEl.replaceChildren();
    if (v.action) {
      const btn = make("button", null, v.action.label);
      btn.type = "button";
      btn.addEventListener("click", async () => {
        btn.blur();
        try { await navigator.clipboard.writeText(v.action.copy); btn.textContent = "Copied"; }
        catch { btn.textContent = v.action.copy; }  // no clipboard: show the text to type instead
      });
      actionEl.append(btn);
      if (v.action.note) actionEl.append(make("span", "midi-hint-note", v.action.note));
    }
    const src = v.source && v.source.url ? v.source : null;
    if (src) {  // an egg's original: a link (and the platform's own thumbnail), never a copy
      const a = make("a", "midi-hint-source", src.label || "Watch it ↗");
      a.href = src.url;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      if (src.thumb) {
        const img = make("img");
        img.src = src.thumb;
        img.alt = "";
        img.loading = "lazy";
        a.prepend(img);
      }
      actionEl.append(a);
    }
    actionEl.hidden = !v.action && !src;
    place();
    el.setAttribute("aria-hidden", "false");
    el.classList.add("is-on");
    if (v.tone === "success") {
      successAt = Date.now();
      if (v.cause === "heard") {  // stays open while it lingers, so new notes can rename it
        if (open !== "heard") narrateUntil = Date.now() + NARRATE_MS;
        open = "heard";
        heardShown = v.title;
      } else {
        open = null;
        if (v.cause === "found") quietAfter = presses.length;  // no sound check straight after "There it is"
      }
      lingerTimer = setTimeout(hide, SUCCESS_LINGER_MS);  // each rename restarts the fade
    } else if (v.tone === "wry" || v.tone === "egg") {  // the comedy department: one card, its own fade
      open = v.cause;
      quietAfter = presses.length;  // the joke answers this press; no sound check after it
      if (v.tone === "egg") successAt = Date.now();
      lingerTimer = setTimeout(hide, v.tone === "egg" ? EGG_LINGER_MS : WRY_LINGER_MS);
    } else {
      open = v.cause;
      shown[v.cause] = Math.max(shown[v.cause] || 0, v.level);
      if (v.tone === "hint") { banter = 0; successAt = 0; }  // a real problem ends the joke
    }
  }

  function hide() {
    clearTimeout(lingerTimer);
    el.classList.remove("is-on");
    el.setAttribute("aria-hidden", "true");
    open = null;
    heardShown = null;
  }

  function dismiss() {
    quietAfter = presses.length;  // dismissed: nothing time-driven comes back until the next press
    hide();
  }

  function evaluate(trigger) {
    const facts = readFacts();
    let v = decideMidiHint({
      ...facts, now: Date.now(), trigger, presses: [...presses], eventsAtPress, windows, permission,
      browser, shown: { ...shown }, open, heardShown, banter, lastHeard,
    });
    if (v && v.cause === "heard" && facts.heard && facts.heard.notes.length === 1) lastHeard = facts.heard.notes[0];
    if (v && v.defer) {  // REC is running: keep the question, show nothing, re-offer when the take ends
      deferred = true;
      if (open) hide();
      return;
    }
    deferred = false;
    if (open === "heard" && facts.rec && facts.rec !== "idle") { hide(); return; }  // a take starts: step aside
    if (v && v.cause === "heard" && open === "heard" && Date.now() > narrateUntil) v = null;  // narration is capped
    if (v && v.cause === "sound-check" && quietAfter === presses.length) v = null;
    if (v) render(v);
    else if (open && !LINGERING.has(open)) hide();  // a lingering card leaves by its own timer
  }

  function arm() {
    if (ticker) return;
    ticker = setInterval(() => {
      const last = presses.length ? presses[presses.length - 1] : 0;
      if (!open && !deferred && Date.now() - last >= SOUND_CHECK_GIVE_UP_MS) {
        clearInterval(ticker);
        ticker = 0;
        return;
      }
      evaluate(deferred && readFacts().rec === "idle" ? "resume" : "tick");
    }, TICK_MS);
  }

  async function pressed() {
    const facts = readFacts();
    const now = Date.now();
    banter = facts.bound.length && successAt && now - successAt < BANTER_WINDOW_MS ? banter + 1 : 0;
    presses.push(now);
    eventsAtPress = facts.events;
    noteBuf.length = 0;  // a fresh listening window for the eggs
    [windows, permission] = await Promise.all([
      facts.bound.length ? Promise.resolve(windows) : fetchWindows(endpoint), queryPermission(),
    ]);
    evaluate("press");
    arm();
  }

  // Every note-on from the page. The eggs listen only while the hint does -- within two minutes of a Rescan press, never
  // during a take -- so an improvisation is never ambushed.
  function noteOn(m) {
    const last = presses.length ? presses[presses.length - 1] : 0;
    if (!last || Date.now() - last >= SOUND_CHECK_GIVE_UP_MS) return;
    const rec = readFacts().rec;
    if (rec && rec !== "idle") return;
    noteBuf.push(m);
    if (noteBuf.length > NOTE_BUFFER) noteBuf.shift();
    const egg = matchEgg(noteBuf);
    if (!egg) return;
    noteBuf.length = 0;
    render({ cause: "egg", level: 1, tone: "egg", title: egg.title, body: egg.body, source: egg.source });
  }

  function changed() {  // bindings changed: only an open hint (or a deferred one) can have news
    if (open || deferred) evaluate("change");
  }

  function dispose() {
    clearInterval(ticker);
    clearTimeout(lingerTimer);
    removeEventListener("keydown", onKey);
    removeEventListener("resize", onResize);
    el.remove();
  }

  return { pressed, changed, noteOn, dispose, get open() { return open; } };
}
