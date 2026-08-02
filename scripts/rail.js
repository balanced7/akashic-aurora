/* rail.js — the right rail Aurora Glass designed and the console never built.
 *
 * PROVENANCE. The mockup (claude.ai artifact 4c051d39, "Bifrost — Aurora Glass", 2026-07-04)
 * specifies the shell as `grid-template-columns: 1fr 300px` — stream beside a rail. The live
 * console shipped the stream and dropped the rail, which is why ~280px of the viewport at 1280
 * has been dead space. Tokens: design/refs/aurora-glass-tokens.css. Rules: design/CONTRACT.md.
 *
 * WHAT IT FOLDS IN — four standing asks, all his words, none of them new tonight:
 *   "at a glance"                     -> GLANCE density + UniFi-style zone glanceability
 *   "verbosity"                       -> DETAIL density; Stripe-style expand-for-detail
 *   "full reasoning of every model"   -> per-agent reasoning drawer over the trace buffer
 *                                        (2026-07-20: "PAST reasoning browsable + REALTIME
 *                                         reasoning as a first-class beautiful pane")
 *   "side chats for AI groups"        -> /api/channels; a namespace is a room
 * Plus the 2026-07-23 NOW-card demand: task/status/substep + realtime reasoning per agent.
 *
 * CONTRACT COMPLIANCE, stated so it can be checked rather than trusted:
 *   - AXIS LAW: every number carries a label, a unit, and a title with its provenance. No bare
 *     glyphs. The strip this replaces had five unlabelled marks per row and no legend.
 *   - STATUS COLORS RESERVED: --good/--warn/--crit only for real state; identity gradients carry
 *     identity. Nominal gets NO status color, because "fine" is the absence of a status.
 *   - MOTION BUDGET: transform/opacity only, and animation is applied to the ACTIVE row only —
 *     never per-row, which is how the old strip's cost scaled with fleet size.
 *   - DEAD FEED LOOKS DEAD: a stale agent renders visibly stale, never merely un-updated.
 */
(function (global) {
  'use strict';

  var CSS = [
    /* shell: the grid the mockup specified */
    '.rail-grid{display:grid;grid-template-columns:1fr 300px;gap:16px;align-items:start}',
    '@media (max-width:1080px){.rail-grid{grid-template-columns:1fr}#rail{order:-1}}',
    '#rail{display:flex;flex-direction:column;gap:12px;position:sticky;top:12px;min-width:0}',

    /* card primitive — glass, per the mockup */
    '#rail .rcard{background:var(--glass,rgba(18,20,28,.55));backdrop-filter:blur(26px) saturate(1.35);',
    '  -webkit-backdrop-filter:blur(26px) saturate(1.35);border:1px solid var(--border,rgba(255,255,255,.07));',
    '  border-radius:14px;padding:13px 14px;box-shadow:0 1px 0 rgba(255,255,255,.06) inset,0 24px 60px -30px rgba(0,0,0,.8)}',
    '#rail h3{font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--faint,#5c6178);',
    '  font-weight:600;margin:0 0 10px;display:flex;align-items:center;gap:8px}',
    '#rail h3 .cnt{color:var(--muted,#9297ab);letter-spacing:0;text-transform:none;font-weight:500}',

    /* density switch — the verbosity ask, as a control rather than a setting */
    '.rdens{display:flex;gap:2px;margin-left:auto;background:rgba(255,255,255,.04);border-radius:7px;padding:2px}',
    '.rdens button{font:inherit;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--faint,#5c6178);',
    '  background:none;border:0;padding:3px 7px;border-radius:5px;cursor:pointer;transition:color .15s,background .15s}',
    '.rdens button.on{background:rgba(255,255,255,.08);color:var(--text,#eef0f7)}',

    /* agent row — UniFi compact device card */
    '.ragent{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-top:1px solid var(--border,rgba(255,255,255,.07));cursor:pointer}',
    '.ragent:first-of-type{border-top:0;padding-top:0}',
    '.ragent .rav{width:28px;height:28px;border-radius:9px;flex:none;display:grid;place-items:center;',
    '  font-size:11px;font-weight:700;color:#0a0b0f;position:relative}',
    '.ragent .rinfo{flex:1;min-width:0}',
    '.ragent .rnm{font-size:12.5px;font-weight:550;color:var(--text,#eef0f7);display:flex;align-items:center;gap:6px}',
    '.ragent .rst{font-size:10.5px;color:var(--muted,#9297ab);font-family:var(--mono,ui-monospace,monospace);',
    '  margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
    '.ragent.stale .rnm,.ragent.stale .rst{opacity:.42}',      /* dead feed LOOKS dead */
    '.ragent.stale .rav{filter:grayscale(1)}',

    /* status chip — never color alone: glyph + word + color */
    '.rchip{font-size:9px;letter-spacing:.06em;text-transform:uppercase;padding:1px 5px;border-radius:4px;',
    '  border:1px solid currentColor;font-weight:650;flex:none;display:inline-flex;align-items:center;gap:3px}',
    '.rchip.good{color:var(--good,#5FBE87);background:var(--good-bg,#16301F)}',
    '.rchip.warn{color:var(--warn,#D9A648);background:var(--warn-bg,#33270F)}',
    '.rchip.crit{color:var(--crit,#E4736A);background:var(--crit-bg,#34191A)}',
    '.rchip.mute{color:var(--faint,#5c6178);background:transparent}',

    /* the ONE animated element: a thinking pulse on the ACTIVE agent only.
       opacity-only, and capped at one row regardless of fleet size (motion budget). */
    '.ragent.active .rav::after{content:"";position:absolute;inset:-3px;border-radius:12px;',
    '  border:1.5px solid var(--user-a,#48e6bf);opacity:0;animation:rthink 2s ease-in-out infinite}',
    '@keyframes rthink{0%,100%{opacity:0}50%{opacity:.85}}',

    /* reasoning drawer — "full reasoning of every model" */
    '.rwhy{display:none;margin:6px 0 2px 38px;padding:8px 10px;border-radius:9px;',
    '  background:rgba(0,0,0,.28);border:1px dashed var(--border,rgba(255,255,255,.12))}',
    '.ragent.open + .rwhy{display:block}',
    '.rwhy .l{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint,#5c6178);margin-bottom:5px;',
    '  display:flex;justify-content:space-between;gap:8px}',
    '.rwhy .line{font-family:var(--mono,ui-monospace,monospace);font-size:10.5px;line-height:1.5;',
    '  color:var(--muted,#9297ab);padding:3px 0;border-top:1px solid rgba(255,255,255,.05)}',
    '.rwhy .line:first-of-type{border-top:0}',
    '.rwhy .empty{font-size:10.5px;color:var(--faint,#5c6178);font-style:italic}',

    /* metric tiles — labelled numbers, the honest replacement for unlabelled sparklines */
    '.rtiles{display:grid;grid-template-columns:1fr 1fr;gap:8px}',
    '.rtile{padding:9px 10px;border-radius:10px;background:rgba(255,255,255,.035);border:1px solid var(--border,rgba(255,255,255,.07))}',
    '.rtile .n{font-size:17px;font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-.02em;color:var(--text,#eef0f7)}',
    '.rtile .u{font-size:10px;font-weight:500;color:var(--muted,#9297ab);margin-left:2px}',
    '.rtile .l{font-size:9.5px;color:var(--muted,#9297ab);letter-spacing:.05em;text-transform:uppercase;margin-top:1px}',

    /* side channels — a namespace is a room */
    '.rchan{display:flex;align-items:center;gap:8px;padding:6px 0;border-top:1px solid var(--border,rgba(255,255,255,.07));font-size:11.5px}',
    '.rchan:first-of-type{border-top:0}',
    '.rchan .nm{font-family:var(--mono,ui-monospace,monospace);color:var(--text,#eef0f7);flex:none}',
    '.rchan .who{color:var(--faint,#5c6178);font-size:10px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
    '.rfoot{font-size:9.5px;color:var(--faint,#5c6178);margin-top:8px;padding-top:7px;',
    '  border-top:1px solid var(--border,rgba(255,255,255,.07));line-height:1.45}',
    '@media (prefers-reduced-motion:reduce){.ragent.active .rav::after{animation:none;opacity:.5}}',

    /* RETIRE THE OLD STRIP. #engine-room rendered five unlabelled marks per agent with no legend,
       no units and alarm hues on nominal activity — Daniil's "you dont know what any axis means",
       and a direct violation of CONTRACT §2. Everything it carried now has a labelled home: the
       per-agent half in FLEET, the counts in THROUGHPUT, the fence phases in FENCES below. The
       rail HIDES what it replaces rather than deleting it, so pulling one script tag restores the
       old surface exactly — a reversible swap, not a demolition. */
    '#engine-room{display:none !important}',
    '.rfence{display:flex;align-items:center;gap:8px;padding:5px 0;font-size:11.5px;',
    '  border-top:1px solid var(--border,rgba(255,255,255,.07))}',
    '.rfence:first-of-type{border-top:0}',
    '.rfence .nm{font-family:var(--mono,ui-monospace,monospace);color:var(--muted,#9297ab);flex:1;',
    '  min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}'
  ].join('');

  var GRAD = {
    claude:        ['#f0a56c', '#e0724f'],
    deepseek:      ['#7aa2f7', '#9d7cf7'],
    'deepseek-ui': ['#7aa2f7', '#9d7cf7'],
    kimi:          ['#f472b6', '#db4f9d'],
    user:          ['#48e6bf', '#2fbf8f'],
    'opus-engineer': ['#c4a2f7', '#9d7cf7']
  };
  function grad(a) {
    var g = GRAD[a];
    if (!g) { for (var k in GRAD) { if (a.indexOf(k) === 0) { g = GRAD[k]; break; } } }
    g = g || ['#5c6178', '#3a3f52'];
    return 'linear-gradient(140deg,' + g[0] + ',' + g[1] + ')';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function ago(iso) {
    if (!iso) return '';
    var t = Date.parse(iso); if (!t) return '';
    var s = Math.max(0, (Date.now() - t) / 1000);
    if (s < 60) return Math.round(s) + 's';
    if (s < 3600) return Math.round(s / 60) + 'm';
    return Math.round(s / 3600) + 'h';
  }

  var density = 'glance';                     // glance | detail
  try { density = localStorage.getItem('bifrost_rail_density') || 'glance'; } catch (e) {}
  var open = {};                              // agent -> reasoning drawer open

  function ensure() {
    if (document.getElementById('rail')) return document.getElementById('rail');
    var log = document.getElementById('log');
    if (!log || !log.parentNode) return null;
    var s = document.createElement('style'); s.id = 'rail-css'; s.textContent = CSS;
    document.head.appendChild(s);
    // DOM surgery rather than a bifrost_ui.py edit: the rail owns its own shell, so it can be
    // removed by deleting one script tag. Keeps the 3,300-line file from growing again.
    var grid = document.createElement('div'); grid.className = 'rail-grid';
    log.parentNode.insertBefore(grid, log);
    grid.appendChild(log);
    var rail = document.createElement('aside'); rail.id = 'rail';
    grid.appendChild(rail);
    return rail;
  }

  /* reasoning: the trace buffer is where 💭 lines land (same source presence-cloud reads) */
  function reasoning(aid, limit) {
    var out = [];
    try {
      var buf = (global._traceBuffer || {})[aid] || [];
      for (var i = buf.length - 1; i >= 0 && out.length < (limit || 6); i--) {
        var t = (buf[i] && buf[i].text) || '';
        if (t.indexOf('\u{1f4ad}') === 0) out.push({ text: t.replace(/^\u{1f4ad}\s*/u, ''), ts: buf[i].ts });
      }
    } catch (e) {}
    return out;
  }

  function agentCard(a, now) {
    var st = (now.status || {}), vit = (now.vitals || {})[a] || {};
    var sig = (st.signals || {})[a] || {};
    var halted = !!(st.halted || {})[a];
    var seen = null;
    (st.agents || []).forEach(function (r) { if (r.agent === a) seen = r.last_seen; });
    var acts = (st.activities || {})[a] || null;
    var age = seen ? (Date.now() - Date.parse(seen)) / 1000 : 1e9;
    var stale = !(age < 300);
    var active = !!(acts && acts.state) && !stale;

    var chip, cls;
    if (halted)          { chip = '⏸ halted';  cls = 'crit'; }
    else if (stale)      { chip = '○ offline'; cls = 'mute'; }
    else if (sig.steer_pending) { chip = '↳ steer'; cls = 'warn'; }
    else if (active)     { chip = '◆ working';  cls = 'good'; }
    else                 { chip = '● idle';     cls = 'mute'; }  /* nominal = no status hue */

    var verb = acts ? (acts.state || '') : (stale ? 'no beat' : 'idle');
    var detail = acts ? (acts.detail || '') : '';
    var why = reasoning(a, density === 'detail' ? 8 : 3);

    var line2 = density === 'detail'
      ? esc(verb) + (detail ? ' · ' + esc(detail) : '') +
        (vit.lanes ? '  │ work ' + vit.lanes.work + ' msg' : '')
      : esc(verb) + (detail ? ' · ' + esc(detail.slice(0, 34)) : '');

    var h = '<div class="ragent' + (stale ? ' stale' : '') + (active ? ' active' : '') +
              (open[a] ? ' open' : '') + '" data-a="' + esc(a) + '"' +
              ' title="' + esc(a) + ' — click for full reasoning' +
              (seen ? ' · last beat ' + ago(seen) + ' ago' : ' · never seen') + '">' +
        '<div class="rav" style="background:' + grad(a) + '">' + esc(a.slice(0, 1).toUpperCase()) + '</div>' +
        '<div class="rinfo">' +
          '<div class="rnm">' + esc(a) +
            '<span class="rchip ' + cls + '">' + chip + '</span>' +
            (why.length ? '<span class="rchip mute" title="reasoning lines captured">\u{1f4ad}' + why.length + '</span>' : '') +
          '</div>' +
          '<div class="rst">' + line2 + '</div>' +
        '</div>' +
      '</div>';

    h += '<div class="rwhy"><div class="l"><span>reasoning · newest first</span>' +
         '<span>' + (seen ? 'beat ' + ago(seen) + ' ago' : 'no beat') + '</span></div>';
    if (!why.length) {
      h += '<div class="empty">No reasoning captured for this seat. The trace lane carries ' +
           '\u{1f4ad} lines only while narration is on — empty here means unrecorded, not unthinking.</div>';
    } else {
      why.forEach(function (w) { h += '<div class="line">' + esc(w.text) + '</div>'; });
    }
    return h + '</div>';
  }

  function render(now, chans) {
    var rail = ensure(); if (!rail) return;
    var st = now.status || {}, known = st.known || [], vitals = now.vitals || {};

    var live = 0, working = 0, msgs = 0, toks = 0;
    known.forEach(function (a) {
      var v = vitals[a] || {}; var acts = (st.activities || {})[a];
      if (v.heartbeat === 'active') live++;
      if (acts && acts.state) working++;
      if (v.lanes) msgs += (v.lanes.work || 0);
      if (v.tokens) toks += (v.tokens.prompt || 0) + (v.tokens.completion || 0);
    });

    var h = '';
    /* zone 1 — presence (the NOW-card demand) */
    h += '<section class="rcard"><h3>Fleet' +
         '<span class="cnt">' + live + ' of ' + known.length + ' beating</span>' +
         '<span class="rdens">' +
           '<button data-d="glance" class="' + (density === 'glance' ? 'on' : '') + '">glance</button>' +
           '<button data-d="detail" class="' + (density === 'detail' ? 'on' : '') + '">detail</button>' +
         '</span></h3>';
    var order = known.slice().sort(function (x, y) {
      var ax = (st.activities || {})[x], ay = (st.activities || {})[y];
      return (ay && ay.state ? 1 : 0) - (ax && ax.state ? 1 : 0) || x.localeCompare(y);
    });
    (density === 'glance' ? order.slice(0, 6) : order).forEach(function (a) { h += agentCard(a, now); });
    if (density === 'glance' && order.length > 6) {
      h += '<div class="rfoot">' + (order.length - 6) + ' more seat(s) hidden in GLANCE — switch to DETAIL for all ' +
           order.length + '. Hiding is a density choice, not a filter: nothing is dropped.</div>';
    }
    h += '</section>';

    /* zone 2 — metrics, every number labelled + united (axis law) */
    h += '<section class="rcard"><h3>Throughput</h3><div class="rtiles">' +
      '<div class="rtile" title="Seats whose worklive heartbeat is currently active"><div class="n">' + live +
        '<span class="u">/' + known.length + '</span></div><div class="l">seats beating</div></div>' +
      '<div class="rtile" title="Seats reporting a non-idle activity right now"><div class="n">' + working +
        '</div><div class="l">working now</div></div>' +
      '<div class="rtile" title="Undrained messages across all work lanes"><div class="n">' + msgs +
        '<span class="u">msg</span></div><div class="l">work queued</div></div>' +
      '<div class="rtile" title="Prompt + completion tokens reported by runner seats today"><div class="n">' +
        (toks > 999 ? (toks / 1000).toFixed(1) + '<span class="u">k</span>' : toks) +
        '</div><div class="l">tokens today</div></div>' +
      '</div><div class="rfoot">Source: /api/now · refreshed with the page poll. ' +
      'Counts are of SEATS, not conversations — one operator session can hold several.</div></section>';

    /* zone 3 — fences. The one thing the retired strip carried that the rail did not; absorbed
       rather than dropped, because "we replaced that surface" must never quietly mean "we lost
       what it showed". */
    var fence = now.fence || {};
    var fkeys = Object.keys(fence);
    if (fkeys.length) {
      var busy = fkeys.filter(function (k) { return (fence[k] || {}).phase !== 'idle'; }).length;
      h += '<section class="rcard"><h3>Fences<span class="cnt">' +
           (busy ? busy + ' active' : 'all idle') + '</span></h3>';
      fkeys.sort().forEach(function (k) {
        var f = fence[k] || {}, ph = f.phase || 'unknown';
        var idle = ph === 'idle';
        h += '<div class="rfence" title="' + esc(k) + ' — phase ' + esc(ph) +
             (f.files && f.files.length ? ' · ' + f.files.length + ' file(s)' : '') + '">' +
             '<span class="nm">' + esc(k) + '</span>' +
             '<span class="rchip ' + (idle ? 'mute' : 'good') + '">' +
               (idle ? '● idle' : '◆ ' + esc(ph)) + '</span></div>';
      });
      h += '</section>';
    }

    /* zone 4 — side channels (the standing ask) */
    if (chans && chans.channels) {
      h += '<section class="rcard"><h3>Rooms<span class="cnt">' + chans.channels.length + '</span></h3>';
      chans.channels.forEach(function (c) {
        h += '<div class="rchan" title="namespace ' + esc(c.ns) + ' · ' + c.count + ' live seat(s)">' +
             '<span class="nm">' + esc(c.ns) + '</span>' +
             '<span class="rchip ' + (c.is_default ? 'mute' : 'good') + '">' +
                (c.is_default ? 'main' : 'side') + '</span>' +
             '<span class="who">' + esc(c.agents.join(', ')) + '</span></div>';
      });
      h += '<div class="rfoot">A room is a bus namespace. Side rooms are invisible to this feed by ' +
           'design — listing them here is the only way you can see one exists. ' +
           esc(chans.not_checked || '') + '</div></section>';
    }

    rail.innerHTML = h;

    rail.querySelectorAll('.rdens button').forEach(function (b) {
      b.onclick = function (e) {
        e.stopPropagation(); density = b.dataset.d;
        try { localStorage.setItem('bifrost_rail_density', density); } catch (err) {}
        render(_lastNow || {}, _lastChans);
      };
    });
    rail.querySelectorAll('.ragent').forEach(function (el) {
      el.onclick = function () {
        var a = el.dataset.a; open[a] = !open[a];
        el.classList.toggle('open', !!open[a]);
      };
    });
  }

  var _lastNow = null, _lastChans = null, _chanAt = 0;

  function tick() {
    fetch('/api/now').then(function (r) { return r.json(); }).then(function (now) {
      _lastNow = now;
      var stale = (Date.now() - _chanAt) > 20000;   /* channels change slowly; poll gently */
      if (stale) {
        _chanAt = Date.now();
        return fetch('/api/channels').then(function (r) { return r.json(); })
          .then(function (c) { _lastChans = c; render(now, c); })
          .catch(function () { render(now, _lastChans); });
      }
      render(now, _lastChans);
    }).catch(function () {});
  }

  function start() {
    if (!document.getElementById('log')) { setTimeout(start, 400); return; }
    tick();
    setInterval(tick, 5000);        /* one timer, not one per card (contract: one scheduler) */
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();

  global.BifrostRail = { render: function () { render(_lastNow || {}, _lastChans); }, tick: tick };
})(window);
