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

  var log, rail, ticksEl, thumbEl, readEl, mounted = false;
  var model = [];             // [{y: 0..1, t: Date|null, el}]
  var raf = null;

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

    // viewport thumb: where you are, proportional to what you can see
    var H = log.scrollHeight || 1;
    var top = (log.scrollTop / H) * hPx;
    var h = Math.max(14, (log.clientHeight / H) * hPx);
    thumbEl.style.top = top.toFixed(1) + 'px';
    thumbEl.style.height = h.toFixed(1) + 'px';
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
    var frac = Math.min(1, Math.max(0, (ev.clientY - r.top) / r.height));
    var p = nearest(frac);
    // Same honesty rule as labels(): no exact stamps -> no time readout. The rail still
    // scrubs; it just does not claim to know when.
    if (!p || !p.t || !HAS_EXACT) { readEl.style.opacity = '0'; return; }
    readEl.textContent = fmtDay(p.t) + '  ' + fmtTime(p.t);
    readEl.style.top = (ev.clientY - r.top) + 'px';
    readEl.style.opacity = '1';
  }

  // ---------------------------------------------------------------- mount
  var CSS = ''
    + '#tl-rail{position:fixed;width:' + RAIL_W + 'px;z-index:40;pointer-events:auto;'
    + 'font:10px/1 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,system-ui,sans-serif;'
    + 'user-select:none;cursor:pointer}'
    + '#tl-rail:before{content:"";position:absolute;right:6px;top:0;bottom:0;width:1px;'
    + 'background:linear-gradient(180deg,transparent,var(--glass-line,rgba(255,255,255,.08)) 8%,'
    + 'var(--glass-line,rgba(255,255,255,.08)) 92%,transparent)}'
    + '#tl-ticks{position:absolute;inset:0}'
    + '.tl-t{position:absolute;right:6px;width:5px;height:1px;background:var(--faint,#727890);'
    + 'opacity:.5;transform:translateY(-.5px)}'
    + '.tl-t-x{width:3px;opacity:.25}'
    + '.tl-l{position:absolute;right:14px;transform:translateY(-50%);white-space:nowrap;'
    + 'color:var(--faint,#727890);font-weight:400;letter-spacing:.02em;opacity:.75}'
    + '.tl-l.tl-day{color:var(--accent2,#9d7cf7);font-weight:600;opacity:1;'
    + 'text-shadow:0 0 10px rgba(157,124,247,.35)}'
    + '#tl-thumb{position:absolute;right:3px;width:7px;border-radius:4px;'
    + 'background:linear-gradient(180deg,var(--accent,#7aa2f7),var(--accent2,#9d7cf7));'
    + 'opacity:.30;transition:opacity .15s;pointer-events:none}'
    + '#tl-rail:hover #tl-thumb{opacity:.55}'
    + '#tl-read{position:absolute;right:16px;transform:translateY(-50%);opacity:0;'
    + 'transition:opacity .12s;padding:3px 7px;border-radius:5px;white-space:nowrap;'
    + 'background:var(--glass,rgba(18,20,28,.55));border:1px solid var(--glass-line,rgba(255,255,255,.08));'
    + 'color:var(--text,#e7e9f0);backdrop-filter:blur(6px);box-shadow:var(--shadow,0 8px 30px rgba(0,0,0,.35));'
    + 'pointer-events:none;font-variant-numeric:tabular-nums}'
    + '@media (prefers-reduced-motion:reduce){#tl-thumb,#tl-read{transition:none}}';

  function mount() {
    log = document.getElementById(LOG_ID);
    if (!log || mounted) return;
    var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st);
    rail = document.createElement('div'); rail.id = 'tl-rail';
    rail.setAttribute('role', 'slider');
    rail.setAttribute('aria-label', 'Jump to a time in the conversation');
    ticksEl = document.createElement('div'); ticksEl.id = 'tl-ticks';
    thumbEl = document.createElement('div'); thumbEl.id = 'tl-thumb';
    readEl = document.createElement('div'); readEl.id = 'tl-read';
    rail.appendChild(ticksEl); rail.appendChild(thumbEl); rail.appendChild(readEl);
    document.body.appendChild(rail);
    mounted = true;

    var dragging = false;
    rail.addEventListener('mousedown', function (e) { dragging = true; jump(e); e.preventDefault(); });
    window.addEventListener('mousemove', function (e) { if (dragging) jump(e); });
    window.addEventListener('mouseup', function () { dragging = false; });
    rail.addEventListener('mousemove', hover);
    rail.addEventListener('mouseleave', function () { readEl.style.opacity = '0'; });

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
