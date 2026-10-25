// VJ stage: arsenal/web/vj-stage.js (ES module, DOM + WebGL through vj-fx.js). The page (vj.js) hands it a small context
// of accessors once; everything here hangs off that context, so vj.js only carries a few one-line hooks.
//
//   - beat-synced transitions: plan() tells nextSet when a switch starts (the next beat, or the next bar when the beat
//     source numbers its bars) and in which style; mix() renders the non-crossfade styles through vj-fx.js
//   - the look: a post pass over the composite (bloom, vignette, grain, aberration on hits) with a master amount on a
//     fader (learned on touch) and an off switch; the mapping panel gets a "Transitions and look" section
//   - the showcase (?showcase=1, or S): an automatic tour of every set, ~20 s each, driven by the engine when it plays
//     beats and by the demo otherwise, with tasteful transitions, gentle accents and a name card for each set
//   - window.__vjx: the receipt's hook (arsenal/lanes/vj2_verify.mjs)
// Keys: T next transition style, L look on/off, S showcase on/off.
import {
  TRANSITIONS, TRANSITION_IDS, STYLE_CHOICES, QUANTIZE_CHOICES, pickStyle, planTransition, transitionProgress,
  normalizeLook, lookParams, blurbFor, ShowcaseTour, cardOpacity, styleLabel, quantizeLabel, NEVER_IN_TOUR,
} from "./vj-show.js";
import { createVjFx } from "./vj-fx.js";

const STORE_LOOK = "arsenal.vj.look";

function safeGet(key) { try { return localStorage.getItem(key); } catch { return null; } }
function safeSet(key, value) { try { localStorage.setItem(key, value); } catch { /* private window or blocked storage */ } }

export function createStage(ctx) {
  const QS = new URLSearchParams(location.search);
  let look = normalizeLook(null);
  try { look = normalizeLook(JSON.parse(safeGet(STORE_LOOK) || "null")); } catch { /* defaults */ }
  if (QS.get("look") === "0") look.on = false;
  if (QS.get("look") === "1") look.on = true;
  const save = () => safeSet(STORE_LOOK, JSON.stringify(look));
  let fx = null, fxError = "";
  let serial = 0;                 // transitions planned (the cycle's counter)
  let learnLook = false;
  const log = [];                 // transitions, for the receipt: { style, on, from, to, asked, start, ms, end }
  let current = null;             // the transition in flight (a log entry)
  let lastPlan = null;
  let slow = 1;                   // receipts only (window.__vjx.setSlow): stretch transitions to photograph them mid-way

  // ------------------------------------------------------------------------------------------------ GL --
  function initGL(gl, fmt) {
    if (fx) { try { fx.dispose(); } catch { /* a lost context took it */ } }
    fx = null;
    try {
      fx = createVjFx(gl, fmt);
      fxError = "";
    } catch (err) {
      fxError = String(err.message || err);
      ctx.recordError("compile", "vj-fx", fxError);
    }
  }
  // the framebuffer the composite should draw into (the look's input), or null to draw to the screen. Since 2026-10-24
  // the page composites into its own pair and hands the texture to post(); this stays for a page that does not.
  function compositeTarget(w, h) { return fx && look.on && look.amount > 0.001 ? fx.target(w, h) : null; }
  // The look, from `src` (the page's composite texture; the module's own target when omitted) to the screen, or into
  // `dst` (a framebuffer: since 2026-10-24 the flash limiter's input, vj-limiter.js). False when the look is off: the
  // page then hands its composite on itself.
  function post(w, h, src = null, dst = null) {
    if (!fx || !look.on || look.amount <= 0.001) return false;
    fx.post(w, h, lookParams(look.amount), ctx.hit(), src, dst);
    return true;
  }

  // ------------------------------------------------------------------------------------- transitions --
  // When and how the next switch plays. styleOverride: the showcase's choice.
  function plan(nowMs, from, to, styleOverride = null) {
    const style = styleOverride && TRANSITIONS[styleOverride] ? styleOverride : pickStyle(look.style, serial);
    serial++;
    const p = planTransition(nowMs, ctx.beat(), { style, quantize: look.quantize, bars: ctx.barsKnown() });
    p.seed = Math.random() * 100;
    p.ms *= slow;
    lastPlan = { ...p, asked: nowMs };
    current = { style: p.style, on: p.on, from: ctx.setId(from), to: ctx.setId(to), asked: Math.round(nowMs),
                start: Math.round(p.startMs), ms: Math.round(p.ms), end: null, beatAtStart: null, beatN: null };
    log.push(current);
    if (log.length > 40) log.shift();
    return p;
  }
  // Called when a fade finishes (the deck's new live set is `to`).
  function landed(nowMs) {
    if (current && current.end === null) current.end = Math.round(nowMs);
    current = null;
  }
  // The picture of a non-crossfade transition in flight, or null for the page's own crossfade.
  function mix(deck, texA, texB, w, h, nowMs, nowS) {
    if (!deck.running) return null;
    const p = transitionProgress(nowMs, deck.start, deck.ms);
    if (p <= 0) return null;
    // for the receipt: the fired beat nearest the start, watched over the transition's first 200 ms
    if (current && current.end === null && (current.beatAtStart === null || nowMs - deck.start < 200)) {
      const b = ctx.beat();
      if (current.beatAtStart === null || Math.abs(b.lastBeat - current.start) < Math.abs(current.beatAtStart - current.start)) {
        current.beatAtStart = Math.round(b.lastBeat);
        current.beatN = b.n;
      }
    }
    if (!fx || !deck.code) return null;                // the crossfade is the composite's own
    const from = deck.from || 0;
    const pal = ctx.palette();
    return fx.transition(w, h, texA, texB, { code: deck.code, progress: from + (1 - from) * p, seed: deck.seed || 0, t: nowS,
                                             edge: [pal[0] * 1.2, pal[1] * 1.2, pal[2] * 1.2] });
  }

  // ------------------------------------------------------------------------------------------- the look --
  function setLook(patch) {
    if (typeof patch.on === "boolean") look.on = patch.on;
    if (typeof patch.amount === "number" && Number.isFinite(patch.amount)) look.amount = Math.min(1, Math.max(0, patch.amount));
    if (STYLE_CHOICES.includes(patch.style)) look.style = patch.style;
    if (QUANTIZE_CHOICES.includes(patch.quantize)) look.quantize = patch.quantize;
    save();
    refreshPanel();
  }
  // A control event, before the page's own mapping: true when the look took it.
  function onCtl(ev) {
    if (ctx.learning()) {                       // the page is learning another target: let go of this control
      if (look.ctl === ev.id) { look.ctl = null; save(); refreshPanel(); }
      return false;
    }
    if (learnLook) {
      learnLook = false;
      look.ctl = ev.id;
      ctx.unbindCtl(ev.id);                     // one control, one target
      look.amount = ev.kind === "rel" ? look.amount : ev.value;
      save();
      refreshPanel();
      return true;
    }
    if (look.ctl && ev.id === look.ctl) {
      look.amount = ev.kind === "rel" ? Math.min(1, Math.max(0, look.amount + ev.delta / 64)) : ev.value;
      save();
      refreshPanel();
      return true;
    }
    return false;
  }

  // ------------------------------------------------------------------------------------------ the panel --
  let panelEls = null;
  function buildPanel() {
    const panel = document.getElementById("panel");
    if (!panel || panelEls) return;
    const sec = document.createElement("section");
    sec.className = "panel-sec stage-sec";
    sec.setAttribute("aria-label", "Transitions and look");
    const h3 = document.createElement("h3");
    h3.textContent = "Transitions and look";
    const row = (labelText, control) => {
      const r = document.createElement("div");
      r.className = "stage-row";
      const l = document.createElement("label");
      l.textContent = labelText;
      r.append(l, control);
      return r;
    };
    const style = document.createElement("select");
    style.setAttribute("aria-label", "Transition style");
    for (const s of STYLE_CHOICES) {
      const o = document.createElement("option");
      o.value = s;
      o.textContent = styleLabel(s);
      style.appendChild(o);
    }
    style.addEventListener("change", () => { setLook({ style: style.value }); style.blur(); });
    const quant = document.createElement("select");
    quant.setAttribute("aria-label", "Transition timing");
    for (const q of QUANTIZE_CHOICES) {
      const o = document.createElement("option");
      o.value = q;
      o.textContent = quantizeLabel(q);
      quant.appendChild(o);
    }
    quant.addEventListener("change", () => { setLook({ quantize: quant.value }); quant.blur(); });
    const on = document.createElement("input");
    on.type = "checkbox";
    on.addEventListener("change", () => setLook({ on: on.checked }));
    const onLabel = document.createElement("label");
    onLabel.className = "check";
    onLabel.append(on, document.createTextNode(" Look on (bloom, vignette, grain, colour split on hits)"));
    const amt = document.createElement("input");
    amt.type = "range"; amt.min = "0"; amt.max = "1"; amt.step = "0.01";
    amt.setAttribute("aria-label", "Look amount");
    amt.addEventListener("input", () => setLook({ amount: +amt.value }));
    const amtVal = document.createElement("span");
    amtVal.className = "val";
    const bind = document.createElement("span");
    bind.className = "bind";
    const learn = document.createElement("button");
    learn.type = "button";
    learn.className = "btn";
    learn.addEventListener("click", () => { learnLook = !learnLook; refreshPanel(); });
    const lookRow = document.createElement("div");
    lookRow.className = "target";
    const lookLabel = document.createElement("label");
    lookLabel.textContent = "Look amount";
    lookLabel.title = "the master amount of the post look; learn a fader for it";
    lookRow.append(lookLabel, amt, bind, learn);
    const tour = document.createElement("button");
    tour.type = "button";
    tour.className = "btn";
    tour.addEventListener("click", () => toggleShowcase());
    const tourRow = document.createElement("div");
    tourRow.className = "row";
    tourRow.append(tour);
    const note = document.createElement("p");
    note.className = "note";
    note.textContent = "A switch (R, pad 12, a click on a set) lands on the next bar when the beat source counts bars " +
      "(the demo does), else on the next beat, and plays two beats (the glitch cut one). Keys: T next style, L look on/off, " +
      "S showcase. The look never adds a flash: its glow's share of the frame is measured and capped every frame.";
    sec.append(h3, row("Style", style), row("Timing", quant), onLabel, lookRow, tourRow, note);
    // after the Sets section
    const setsSec = panel.querySelector('section[aria-label="Sets"]');
    if (setsSec && setsSec.nextSibling) panel.insertBefore(sec, setsSec.nextSibling); else panel.appendChild(sec);
    panelEls = { style, quant, on, amt, amtVal, bind, learn, tour };
    refreshPanel();
  }
  function refreshPanel() {
    if (!panelEls) return;
    const e = panelEls;
    if (document.activeElement !== e.style) e.style.value = look.style;
    if (document.activeElement !== e.quant) e.quant.value = look.quantize;
    e.on.checked = look.on;
    if (document.activeElement !== e.amt) e.amt.value = String(look.amount);
    e.bind.textContent = learnLook ? "move a control…" : (look.ctl || "unbound");
    e.learn.textContent = learnLook ? "Move…" : "Learn";
    e.learn.classList.toggle("armed", learnLook);
    e.tour.textContent = tour ? "Stop the showcase" : "Start the showcase tour";
  }

  // ----------------------------------------------------------------------------------- the name card --
  let card = null, cardAt = -1e9, cardHold = 3200, cardFor = -1, cardsOff = false, booted = false;
  function buildCard() {
    if (card) return;
    card = document.createElement("div");
    card.className = "namecard";
    card.setAttribute("role", "status");
    card.setAttribute("aria-live", "polite");
    const kicker = document.createElement("div");
    kicker.className = "nc-kicker";
    const name = document.createElement("div");
    name.className = "nc-name";
    const blurb = document.createElement("div");
    blurb.className = "nc-blurb";
    card.append(kicker, name, blurb);
    ctx.stage.appendChild(card);
  }
  function showCard(index, nowMs) {
    buildCard();
    const sets = ctx.sets();
    const s = sets[index];
    if (!s) return;
    const valid = sets.filter((x) => x.status !== "broken");
    const n = tour ? ((tour.visits - 1) % valid.length) + 1 : valid.indexOf(s) + 1;
    card.children[0].textContent = `${tour ? "Showcase" : "Now playing"} · ${n} / ${valid.length}`;
    card.children[1].textContent = s.name;
    card.children[2].textContent = blurbFor(s.id);
    cardAt = nowMs;
    cardFor = index;
  }
  function updateCard(nowMs) {
    if (!card) return;
    const o = cardOpacity(nowMs - cardAt, cardHold);
    card.style.opacity = o.toFixed(3);
    card.style.transform = `translate(-50%, ${((1 - Math.min(1, (nowMs - cardAt) / 600)) * 10).toFixed(1)}px)`;
    card.classList.toggle("shown", o > 0.01);
  }

  // ------------------------------------------------------------------------------------- the showcase --
  let tour = null;
  const show = { mode: "off", probeUntil: 0, reprobeAt: 0, lastBeatCount: -1, accents: [], dwellMs: 20000, startedAt: 0,
                 cards: [], visits: 0 };
  const accentTimers = new Set();
  function startShowcase(nowMs = performance.now()) {
    const dwell = Number(QS.get("dwell"));
    show.dwellMs = Number.isFinite(dwell) && dwell >= 2 ? dwell * 1000 : 20000;
    tour = new ShowcaseTour({ dwellMs: show.dwellMs });
    show.startedAt = nowMs;
    show.lastBeatCount = ctx.beat().count;
    show.cards = [];
    // listen for an engine that plays beats; otherwise the demo drives the tour
    if (ctx.engineUrl() && !ctx.demoOn()) { show.mode = "probe"; show.probeUntil = nowMs + 2500; }
    else { show.mode = "demo"; if (!ctx.demoOn()) ctx.setDemo(true); }
    ctx.stage.classList.add("showcase");
    refreshPanel();
  }
  function stopShowcase() {
    tour = null;
    show.mode = "off";
    for (const t of accentTimers) clearTimeout(t);
    accentTimers.clear();
    ctx.stage.classList.remove("showcase");
    refreshPanel();
  }
  function toggleShowcase() { if (tour) stopShowcase(); else startShowcase(); }
  function engineDriving(nowMs) { return ctx.engineOpen() && !ctx.demoOn() && ctx.beat().alive(nowMs); }
  function padFor(effect) {
    const map = ctx.padMap();
    const i = map.indexOf(effect);
    return i >= 0 ? i + 1 : 0;
  }
  function tick(nowMs) {
    // outside the tour the card follows the live set, however it changed (a transition, a click, a cut)
    if (!tour && booted && !cardsOff && ctx.deck().a !== cardFor && !ctx.deck().running) showCard(ctx.deck().a, nowMs);
    updateCard(nowMs);
    if (!tour) return;
    // who drives: the engine when it plays beats, else the demo
    if (show.mode === "probe" && nowMs >= show.probeUntil) {
      if (engineDriving(nowMs)) show.mode = "engine";
      else { show.mode = "demo"; show.reprobeAt = nowMs + 60000; if (!ctx.demoOn()) ctx.setDemo(true); }
    } else if (show.mode === "demo" && nowMs >= show.reprobeAt && ctx.engineOpen() && nowMs - ctx.engineLastMsg() < 1500) {
      ctx.setDemo(false);
      show.mode = "probe";
      show.probeUntil = nowMs + 3000;
    } else if (show.mode === "engine" && !ctx.beat().alive(nowMs)) {
      show.mode = "demo"; show.reprobeAt = nowMs + 60000;
      if (!ctx.demoOn()) ctx.setDemo(true);
    }
    const b = ctx.beat();
    let downbeat = false;
    if (b.count !== show.lastBeatCount) {
      show.lastBeatCount = b.count;
      downbeat = ctx.barsKnown() ? b.n >= 0 && b.n % 4 === 0 : b.count % 4 === 0;
    }
    const deck = ctx.deck();
    const actions = tour.tick(nowMs, { active: deck.a, fading: deck.running, downbeat });
    for (const a of actions) {
      if (a.do === "card") { showCard(a.index, nowMs); show.cards.push({ t: Math.round(nowMs), id: ctx.setId(a.index) }); }
      else if (a.do === "next") ctx.nextSet(a.style);
      else if (a.do === "accent" && !NEVER_IN_TOUR.includes(a.effect)) {
        const pad = padFor(a.effect);
        if (pad < 1) continue;
        ctx.press(pad, a.vel);
        show.accents.push({ t: Math.round(nowMs), effect: a.effect, pad });
        if (show.accents.length > 60) show.accents.shift();
        const timer = setTimeout(() => { accentTimers.delete(timer); ctx.release(pad); }, a.holdMs);
        accentTimers.add(timer);
      }
    }
  }

  // ------------------------------------------------------------------------------------------- keys --
  function wireKeys() {
    const typing = (el) => el && (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA") && el.type !== "range";
    window.addEventListener("keydown", (e) => {
      if (typing(e.target) || e.ctrlKey || e.metaKey || e.altKey || e.repeat) return;
      if (e.code === "KeyT") {
        const i = STYLE_CHOICES.indexOf(look.style);
        setLook({ style: STYLE_CHOICES[(i + 1) % STYLE_CHOICES.length] });
        ctx.toast(`transition: ${styleLabel(look.style)}`);
      } else if (e.code === "KeyL") {
        setLook({ on: !look.on });
        ctx.toast(look.on ? `look on (${Math.round(look.amount * 100)}%)` : "look off");
      } else if (e.code === "KeyS") {
        toggleShowcase();
        ctx.toast(tour ? "showcase tour" : "showcase off");
      } else return;
      e.preventDefault();
    });
  }

  function boot(nowMs = performance.now()) {
    buildPanel();
    buildCard();
    wireKeys();
    booted = true;
    if (QS.get("showcase") === "1") startShowcase(nowMs);
    else showCard(ctx.deck().a, nowMs);
  }

  // the receipt's hook
  window.__vjx = {
    api: "arsenal.vj-stage/v1",
    look: () => ({ ...look, params: lookParams(look.amount), fx: !!fx, fxError, sizes: fx ? fx.sizes() : null }),
    setLook: (patch) => { setLook(patch || {}); return { ...look }; },
    transitions: () => log.map((x) => ({ ...x })),
    lastPlan: () => (lastPlan ? { ...lastPlan } : null),
    styles: () => TRANSITION_IDS.slice(),
    showcase: () => ({ on: !!tour, mode: show.mode, dwellMs: show.dwellMs, cards: show.cards.slice(), accents: show.accents.slice(),
                       visits: tour ? tour.visits : 0,
                       card: card ? { text: card.textContent, opacity: +card.style.opacity || 0 } : null }),
    cardOff: () => { cardAt = -1e9; cardsOff = true; return true; },   // receipts: clean frames, no name cards outside the tour
    setSlow: (k) => { slow = Math.min(8, Math.max(1, Number(k) || 1)); return slow; },
    startShowcase: () => { startShowcase(); return true; },
    stopShowcase: () => { stopShowcase(); return true; },
  };

  return { initGL, compositeTarget, post, plan, landed, mix, onCtl, tick, boot, look: () => look, showCard };
}
