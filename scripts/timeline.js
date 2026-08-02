/* timeline.js -- the date spine: jump large spans, land on a specific minute.
 *
 * Daniil's ask, verbatim: "make a smooth date based scroll function on the left where you
 * can click on a time and skip there. make it a cool design that allows to jump large spans
 * of time but also be accurate to select specific timeframes."
 *
 * THE TENSION, and the whole design is an answer to it: a linear time axis wastes the rail
 * on idle gaps (six sleeping hours get the same pixels as six working minutes), while a
 * pure scroll-position axis has no relationship to time at all. So the SPINE IS POSITIONAL
 * -- it maps 1:1 to feed scroll, which is what dragging already feels like -- and the
 * LABELS are temporal, thinned adaptively so density follows how much actually happened.
 * Big drags therefore cover big spans, and the hover readout gives the minute. Both asks,
 * one control, no mode switch.
 *
 * Standalone by construction (the _static module pattern: presence-rail.js, rail.js,
 * theme-void.js). It reads the DOM, owns one absolutely-positioned element, and touches
 * no console internals.
 *
 * TIMESTAMPS: prefers .msg[data-ts] (ISO, exact, survives midnight). Falls back to parsing
 * the rendered .time text, which is same-day only -- a fallback that DEGRADES rather than
 * lying: without data-ts the day markers are suppressed instead of guessed.
 *
 * SCROLLING IS INSTANT, DELIBERATELY. #log has scroll-behavior: smooth, so assigning
 * scrollTop starts an animation that the feed's own autoscroll/trim cancels mid-flight
 * (measured live 2026-08-02: assignment read back 0, still 0 after 700ms; scrollTo with
 * behavior:'instant' landed immediately). A scrubber that animates would be cancelled by
 * the next arriving message, which is the click-many-times bug wearing a new hat.
 */
(function () {
  'use strict';

  var LOG_ID = 'log';
  var RAIL_W = 44;            // px; the gutter left of the feed
  var MIN_LABEL_GAP = 34;     // px; below this two labels collide, so one is dropped
  var TICK_MIN_GAP = 7;       // px; below this ticks read as a smear

  var log, rail, ticksEl, thumbEl, readEl, glowEl, mounted = false;
  var model = [];             // [{y: 0..1, t: Date|null, el}]
  var raf = null;

  /* FISHEYE. The rail is dense by design -- 58 ticks in ~500px on a busy feed -- which is
   * right for seeing shape and wrong for picking a moment. So the cursor carries a lens:
   * ticks within FISH_R px stretch and brighten on a smooth falloff, giving local precision
   * without a mode, a zoom control, or a second scale. It is the same answer as the label
   * thinning one layer down -- density where it helps, detail where you are looking.
   *
   * Everything here animates via transform/opacity ONLY, so it rides the compositor and
   * never triggers layout. That distinction is the whole reason this can be smooth while
   * the SCROLL stays instant: visual feedback is cheap and continuous, content movement is
   * discrete and must not be animated (a smooth scroll here would be cancelled by the next
   * arriving message -- the bug this module was built beside). */
  var FISH_R = 68;            // px; lens radius
  var FISH_MAX = 3.2;         // px; extra tick length at the centre of the lens
  var cursorY = null;         // px within the rail, or null when the pointer is away
  var tickEls = [];           // cached so the hover pass never re-queries the DOM
  var reduceMotion = false;

  // ---------------------------------------------------------------- timestamps
  function parseTs(el) {
    var iso = el.getAttribute && el.getAttribute('data-ts');
    if (iso) { var d = new Date(iso); if (!isNaN(d)) return d; }
    // Fallback: rendered clock text ("08:49 AM"). Same-day only -- see header.
    var t = el.querySelector && el.querySelector('.time');
    if (!t) return null;
    var m = /(\d{1,2}):(\d{2})\s*(AM|PM)?/i.exec(t.textContent || '');
    if (!m) return null;
    var h = parseInt(m[1], 10), min = parseInt(m[2], 10), ap = (m[3] || '').toUpperCase();
    if (ap === 'PM' && h < 12) h += 12;
    if (ap === 'AM' && h === 12) h = 0;
    var now = new Date(), d2 = new Date(now);
    d2.setHours(h, min, 0, 0);
    return d2;
  }

  var HAS_EXACT = false;      // true when at least one node carried data-ts

  function build() {
    if (!log) return;
    var kids = log.querySelectorAll('.msg');
    var H = log.scrollHeight || 1;
    model = [];
    HAS_EXACT = false;
    for (var i = 0; i < kids.length; i++) {
      var el = kids[i];
      if (el.getAttribute('data-ts')) HAS_EXACT = true;
      model.push({ y: Math.min(1, Math.max(0, el.offsetTop / H)), t: parseTs(el), el: el });
    }
  }

  // ---------------------------------------------------------------- label thinning
  function fmtTime(d) {
    var h = d.getHours(), m = d.getMinutes(), ap = h >= 12 ? 'p' : 'a';
    h = h % 12; if (h === 0) h = 12;
    return h + ':' + (m < 10 ? '0' : '') + m + ap;
  }
  function fmtDay(d) {
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  /* Keep a label only when it clears the previous kept one by MIN_LABEL_GAP px. Day
   * boundaries outrank clock labels: a new date always earns its slot and evicts a
   * neighbouring time. That is what makes a long scrollback legible -- you see the DAYS
   * first, and the minutes only where there is room for them.
   *
   * WITHOUT data-ts THE RAIL SHOWS NO TIMES AT ALL, and that is the honest behaviour.
   * Measured live 2026-08-02 before this guard existed: parsing the rendered .time text
   * stamps every message with TODAY, so a multi-day scrollback rendered
   * 8:53 -> 21:04 -> 19:49 -> 10:08 -> 1:19 descending the rail -- non-monotonic and
   * confidently wrong. A scrubber whose labels lie is worse than one with none, so the
   * fallback degrades to a positional spine (ticks + thumb, still fully clickable) and
   * says so. Ship data-ts and the times appear. */
  function labels(hPx) {
    if (!HAS_EXACT) return [];
    var out = [], lastY = -1e9, prevDay = null;
    for (var i = 0; i < model.length; i++) {
      var p = model[i];
      if (!p.t) continue;
      var yPx = p.y * hPx;
      var dayKey = HAS_EXACT ? p.t.toDateString() : null;
      var isDayBreak = HAS_EXACT && prevDay !== null && dayKey !== prevDay;
      if (isDayBreak) {
        while (out.length && yPx - out[out.length - 1].yPx < MIN_LABEL_GAP) out.pop();
        out.push({ yPx: yPx, text: fmtDay(p.t), day: true, y: p.y });
        lastY = yPx; prevDay = dayKey; continue;
      }
      if (prevDay === null) prevDay = dayKey;
      if (yPx - lastY >= MIN_LABEL_GAP) {
        out.push({ yPx: yPx, text: fmtTime(p.t), day: false, y: p.y });
        lastY = yPx;
      }
    }
    return out;
  }

  function tickRows(hPx) {
    var out = [], lastY = -1e9;
    for (var i = 0; i < model.length; i++) {
      var yPx = model[i].y * hPx;
      if (yPx - lastY >= TICK_MIN_GAP) { out.push({ yPx: yPx, has: !!model[i].t }); lastY = yPx; }
    }
    return out;
  }

  // ---------------------------------------------------------------- render
  function render() {
    raf = null;
    if (!mounted || !log) return;
    var r = log.getBoundingClientRect();
    rail.style.top = r.top + 'px';
    rail.style.left = Math.max(2, r.left - RAIL_W) + 'px';
    rail.style.height = r.height + 'px';
    var hPx = r.height;

    var t = '';
    tickRows(hPx).forEach(function (k) {
      t += '<i class="tl-t' + (k.has ? '' : ' tl-t-x') + '" style="top:' + k.yPx.toFixed(1) + 'px"></i>';
    });
    labels(hPx).forEach(function (L) {
      t += '<b class="tl-l' + (L.day ? ' tl-day' : '') + '" style="top:' + L.yPx.toFixed(1) + 'px">'
        + L.text + '</b>';
    });
    ticksEl.innerHTML = t;
    tickEls = [].slice.call(ticksEl.querySelectorAll('.tl-t'));
    for (var i = 0; i < tickEls.length; i++) tickEls[i]._y = parseFloat(tickEls[i].style.top);

    // viewport thumb: where you are, proportional to what you can see
    var H = log.scrollHeight || 1;
    var top = (log.scrollTop / H) * hPx;
    var h = Math.max(14, (log.clientHeight / H) * hPx);
    thumbEl.style.transform = 'translateY(' + top.toFixed(1) + 'px)';
    thumbEl.style.height = h.toFixed(1) + 'px';
    lens();
  }

  /* The hover pass. Runs on the same rAF as everything else and touches only transform and
   * opacity, so a dense rail stays at 60fps while the pointer moves. */
  function lens() {
    if (reduceMotion) return;
    for (var i = 0; i < tickEls.length; i++) {
      var el = tickEls[i], f = 0;
      if (cursorY !== null) {
        var d = Math.abs(el._y - cursorY);
        if (d < FISH_R) { var n = 1 - d / FISH_R; f = n * n * (3 - 2 * n); }   // smoothstep
      }
      el.style.transform = f ? 'translateX(' + (-FISH_MAX * f).toFixed(2) + 'px) scaleX('
        + (1 + f * 1.9).toFixed(3) + ')' : '';
      el.style.opacity = f ? (0.5 + f * 0.5).toFixed(3) : '';
    }
    if (glowEl) {
      glowEl.style.opacity = cursorY === null ? '0' : '1';
      if (cursorY !== null) glowEl.style.transform = 'translateY(' + cursorY.toFixed(1) + 'px)';
    }
  }

  function schedule() { if (!raf) raf = requestAnimationFrame(render); }

  // ---------------------------------------------------------------- interaction
  function nearest(frac) {
    if (!model.length) return null;
    var best = model[0], bd = 1e9;
    for (var i = 0; i < model.length; i++) {
      var d = Math.abs(model[i].y - frac);
      if (d < bd) { bd = d; best = model[i]; }
    }
    return best;
  }

  function jump(ev) {
    var r = rail.getBoundingClientRect();
    var frac = Math.min(1, Math.max(0, (ev.clientY - r.top) / r.height));
    var H = log.scrollHeight, target = frac * H - log.clientHeight / 2;
    // INSTANT on purpose -- see the header note on smooth-scroll cancellation.
    log.scrollTo({ top: Math.max(0, Math.min(H, target)), behavior: 'instant' });
    schedule();
  }

  function hover(ev) {
    var r = rail.getBoundingClientRect();
    cursorY = ev.clientY - r.top;                 // drives the lens + the glow
    schedule();
    var frac = Math.min(1, Math.max(0, cursorY / r.height));
    var p = nearest(frac);
    // Same honesty rule as labels(): no exact stamps -> no time readout. The rail still
    // scrubs and still lenses; it just does not claim to know when.
    if (!p || !p.t || !HAS_EXACT) { readEl.style.opacity = '0'; return; }
    // Two lines: the minute is the answer, the day is the context. Rebuild only when the
    // target message actually changes -- a mousemove that lands on the same message must
    // not touch innerHTML, or the panel restyles 60 times a second for no reason.
    if (readEl._for !== p.el) {
      readEl._for = p.el;
      readEl.innerHTML = '<b class="tl-hh"></b><b class="tl-dd"></b>';
      readEl.firstChild.textContent = fmtTime(p.t);
      readEl.lastChild.textContent = fmtDay(p.t);
    }
    readEl.style.transform = 'translateY(' + cursorY.toFixed(1) + 'px) translateY(-50%)';
    readEl.style.opacity = '1';
  }

  function leave() { cursorY = null; readEl.style.opacity = '0'; schedule(); }

  // ---------------------------------------------------------------- mount
  /* THE RAIL HAS ITS OWN PALETTE, deliberately. It previously borrowed --accent/--accent2,
   * which are the deepseek and claude identity colours -- so navigation chrome was wearing
   * an agent's clothes. A timeline is not a participant. These four tokens are scoped to
   * the rail and are the ONLY place its colour is decided: retune here and everything --
   * ticks, lens, thumb, glow, day markers, the glass edge -- moves together.
   * Cyan->mint reads as instrument rather than actor, and stays clear of every seat colour
   * in the console (blue #7aa2f7, violet #9d7cf7, coral #e0915c, pink #f472b6, green #5fd39b). */
  var CSS = ''
    + '#tl-rail{--tl-1:#38d9e0;--tl-2:#5fe3bf;--tl-dim:#5a6b78;--tl-hot:#7ef0ff;'
    + 'position:fixed;width:' + RAIL_W + 'px;z-index:40;pointer-events:auto;'
    + 'font:10px/1 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,system-ui,sans-serif;'
    + 'user-select:none;cursor:pointer}'
    + '#tl-rail:before{content:"";position:absolute;right:6px;top:0;bottom:0;width:1px;'
    + 'background:linear-gradient(180deg,transparent,var(--glass-line,rgba(255,255,255,.08)) 8%,'
    + 'var(--glass-line,rgba(255,255,255,.08)) 92%,transparent)}'
    + '#tl-ticks{position:absolute;inset:0}'
    // transform-origin right: a lens stretch grows LEFTWARD off the spine, so the rail's
    // edge stays a clean line while the ticks reach toward the cursor.
    + '.tl-t{position:absolute;right:6px;width:5px;height:1px;background:var(--tl-dim);'
    + 'opacity:.55;transform-origin:100% 50%;will-change:transform,opacity;'
    + 'transition:transform .12s cubic-bezier(.22,1,.36,1),opacity .12s ease,background .2s}'
    + '.tl-t-x{width:3px;opacity:.28}'
    + '#tl-rail:hover .tl-t{background:var(--tl-1)}'
    // the cursor glow: a soft bloom tracking the pointer, purely decorative and cheap
    + '#tl-glow{position:absolute;right:0;width:30px;height:76px;margin-top:-38px;opacity:0;'
    + 'pointer-events:none;will-change:transform,opacity;transition:opacity .18s ease;'
    + 'background:radial-gradient(ellipse at 80% 50%,rgba(56,217,224,.34),'
    + 'rgba(95,227,191,.15) 46%,transparent 72%)}'
    + '.tl-l{position:absolute;right:14px;transform:translateY(-50%);white-space:nowrap;'
    + 'color:var(--tl-dim);font-weight:400;letter-spacing:.02em;opacity:.8}'
    + '.tl-l.tl-day{color:var(--tl-2);font-weight:600;opacity:1;'
    + 'text-shadow:0 0 10px rgba(95,227,191,.4)}'
    // The thumb EASES to its new position while the feed jumps instantly. The content must
    // not animate (see header); the indicator may, and that easing is what makes a jump
    // read as travel instead of a teleport.
    + '#tl-thumb{position:absolute;top:0;right:3px;width:7px;border-radius:4px;'
    + 'background:linear-gradient(180deg,var(--tl-1),var(--tl-2));'
    + 'opacity:.32;pointer-events:none;will-change:transform;'
    + 'transition:transform .22s cubic-bezier(.22,1,.36,1),opacity .15s,box-shadow .2s}'
    + '#tl-rail:hover #tl-thumb{opacity:.8;box-shadow:0 0 14px rgba(56,217,224,.5)}'
    + '#tl-rail:active #tl-thumb{opacity:1;transition:transform .06s linear}'

    /* THE GLASS PANEL. Real glass is three things stacked, not one translucent fill:
     * a BLURRED backdrop (so the feed behind it smears rather than disappears), a
     * SATURATION lift (blur alone reads muddy and grey), and a bright TOP EDGE where
     * light would catch a physical pane. The ::before sheen is that edge; the shadow
     * beneath gives it height off the page. It tracks the cursor on the same eased
     * transform as everything else, so it glides rather than teleports. */
    + '#tl-read{position:absolute;top:0;right:18px;opacity:0;'
    + 'transition:opacity .16s ease,transform .19s cubic-bezier(.22,1,.36,1);'
    + 'padding:9px 13px 8px;border-radius:13px;white-space:nowrap;overflow:hidden;'
    + 'background:linear-gradient(150deg,rgba(38,52,58,.62),rgba(20,26,32,.52));'
    + 'border:1px solid rgba(255,255,255,.14);border-top-color:rgba(255,255,255,.26);'
    + 'color:var(--text,#e7e9f0);pointer-events:none;'
    + '-webkit-backdrop-filter:blur(18px) saturate(180%);backdrop-filter:blur(18px) saturate(180%);'
    + 'box-shadow:0 10px 34px rgba(0,0,0,.5),0 0 0 1px rgba(56,217,224,.10),'
    + 'inset 0 1px 0 rgba(255,255,255,.13);will-change:transform,opacity}'
    // the sheen: a soft diagonal highlight across the top third, the tell of a glass surface
    + '#tl-read:before{content:"";position:absolute;left:0;right:0;top:0;height:56%;'
    + 'background:linear-gradient(160deg,rgba(255,255,255,.16),rgba(255,255,255,.03) 55%,transparent);'
    + 'pointer-events:none}'
    + '#tl-read .tl-hh{display:block;position:relative;font-size:14px;font-weight:600;'
    + 'letter-spacing:-.01em;line-height:1.15;font-variant-numeric:tabular-nums;'
    + 'color:#fff;text-shadow:0 1px 6px rgba(0,0,0,.45)}'
    + '#tl-read .tl-dd{display:block;position:relative;margin-top:2px;font-size:10px;'
    + 'font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:var(--tl-1);'
    + 'opacity:.95}'
    // The spine brightens and the gutter breathes on hover -- the rail says "I am grabbable"
    // before you click it.
    + '#tl-rail:before{transition:background .25s ease,width .25s ease}'
    + '#tl-rail:hover:before{width:2px;background:linear-gradient(180deg,transparent,'
    + 'var(--tl-1) 10%,var(--tl-2) 90%,transparent);opacity:.6}'
    + '@media (prefers-reduced-motion:reduce){'
    + '#tl-thumb,#tl-read,.tl-t,#tl-glow,#tl-rail:before{transition:none}'
    + '.tl-t{transform:none!important}}';

  function mount() {
    log = document.getElementById(LOG_ID);
    if (!log || mounted) return;
    var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    rail = document.createElement('div'); rail.id = 'tl-rail';
    rail.setAttribute('role', 'slider');
    rail.setAttribute('aria-label', 'Jump to a time in the conversation');
    ticksEl = document.createElement('div'); ticksEl.id = 'tl-ticks';
    glowEl = document.createElement('div'); glowEl.id = 'tl-glow';
    thumbEl = document.createElement('div'); thumbEl.id = 'tl-thumb';
    readEl = document.createElement('div'); readEl.id = 'tl-read';
    rail.appendChild(glowEl); rail.appendChild(ticksEl);
    rail.appendChild(thumbEl); rail.appendChild(readEl);
    document.body.appendChild(rail);
    try { reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}
    mounted = true;

    var dragging = false;
    rail.addEventListener('mousedown', function (e) {
      dragging = true; rail.classList.add('tl-drag'); jump(e); hover(e); e.preventDefault();
    });
    window.addEventListener('mousemove', function (e) { if (dragging) { jump(e); hover(e); } });
    window.addEventListener('mouseup', function () { dragging = false; rail.classList.remove('tl-drag'); });
    rail.addEventListener('mousemove', hover);
    rail.addEventListener('mouseleave', function () { if (!dragging) leave(); });

    log.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', function () { build(); schedule(); });

    // New messages change both the model and the geometry; debounce so a burst costs one pass.
    var deb = null;
    new MutationObserver(function () {
      clearTimeout(deb);
      deb = setTimeout(function () { build(); schedule(); }, 120);
    }).observe(log, { childList: true });

    build(); schedule();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();

  window.timelineRebuild = function () { build(); schedule(); };
})();
