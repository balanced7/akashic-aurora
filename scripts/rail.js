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
    /* CRITICAL: the grid must INHERIT the flex role it displaced, or it eats the composer.
       .app is `display:flex; flex-direction:column; height:100vh` and #log was `flex:1;
       overflow-y:auto` -- the child that absorbed leftover height and scrolled INTERNALLY.
       Wrapping #log in a plain div made THAT div the flex child, with no flex:1 and no
       min-height:0, so it sized to the whole feed (thousands of px), overflowed .app, and
       pushed the composer below the viewport. Daniil, live: "message box is gone, zooming to
       bottom is hard." Both are the same defect -- the page began scrolling instead of the feed.
       min-height:0 is the load-bearing half: without it a flex child REFUSES to shrink below its
       content, so flex:1 alone would not have been enough. */
    /* ADAPTIVE, not breakpoint-driven. The 2026 intrinsic-design toolbox: the rail's WIDTH is a
       clamp of the available space rather than a fixed 300px, so it shrinks continuously on a
       laptop and grows on an ultrawide with no jump. minmax(0,...) is what lets the feed column
       actually shrink -- a grid track's default min is auto, the same trap as flex min-width. */
    '.rail-grid{display:grid;',
    '  grid-template-columns:minmax(0,1fr) clamp(240px, 24%, 360px);',
    '  gap:clamp(10px,1.4vw,18px);align-items:stretch;flex:1;min-height:0}',
    '.rail-grid > #log{height:100%;min-height:0;overflow-y:auto}',
    /* READABILITY IS MEASURED IN CHARACTERS, NOT PIXELS. A line longer than ~75ch is hard to
       track back to the next line, and that is true at every resolution -- which is exactly the
       property a px width cannot express. */
    '.rail-grid > #log .msg{max-width:min(100%, 78ch)}',
    /* Long unbroken tokens (paths, kind=... strings, ids) are the thing that actually breaks a
       narrow column -- seen at 390px: "handoff/decision/completion/bloc·ker" split mid-word.
       break-word keeps normal prose wrapping at spaces and only breaks a token that genuinely
       cannot fit, which is the behaviour you want for a console full of file paths. */
    '.rail-grid > #log .msg,.rail-grid > #log .bubble{overflow-wrap:break-word;word-break:normal}',
    '.rail-grid > #log code,.rail-grid > #log pre{overflow-wrap:anywhere}',

    /* Below ~900px the two-column shape stops working, so the rail moves ABOVE the feed as a
       horizontal band rather than disappearing. Hiding it was the lazy answer and it loses
       information on precisely the device that has least room to spare. */
    '@media (max-width:900px){',
    '  .rail-grid{grid-template-columns:minmax(0,1fr);grid-template-rows:auto minmax(0,1fr)}',
    '  #rail{order:-1;flex-direction:row;overflow-x:auto;overflow-y:hidden;',
    '        max-height:clamp(120px,22vh,190px);padding-bottom:4px}',
    '  #rail .rcard{flex:none;width:min(78vw,300px)}',
    '}',

    /* CONTAINER QUERIES: the cards respond to the RAIL, not the viewport. That is the whole point
       -- the rail can be narrow on a wide screen (ultrawide with a big feed) or wide on a small
       one, and a viewport media query cannot tell those apart. */
    '#rail{display:flex;flex-direction:column;gap:12px;min-width:0;',
    '  height:100%;min-height:0;overflow-y:auto;padding-right:2px;',
    '  container-type:inline-size;container-name:rail}',
    '@container rail (max-width: 260px){',
    '  .rtiles{grid-template-columns:1fr}',            /* one tile per row before numbers wrap */
    '  .ragent .rst{display:none}',                    /* drop the second line, keep identity */
    '  #rail h3 .cnt{display:none}',
    '}',
    '@container rail (min-width: 340px){',
    '  .rtiles{grid-template-columns:repeat(auto-fit,minmax(120px,1fr))}',
    '}',

    /* card primitive — glass, per the mockup */
    '#rail .rcard{background:var(--glass,rgba(18,20,28,.55));backdrop-filter:blur(26px) saturate(1.35);',
    '  -webkit-backdrop-filter:blur(26px) saturate(1.35);border:1px solid var(--border,rgba(255,255,255,.07));',
    '  border-radius:14px;padding:13px 14px;box-shadow:0 1px 0 rgba(255,255,255,.06) inset,0 24px 60px -30px rgba(0,0,0,.8)}',
    /* FLUID TYPE. clamp(min, preferred, max) scales continuously with the viewport and stops at
       both ends -- never smaller than legible, never absurd on an ultrawide. The rem term is what
       keeps it accessible: a pure vw formula IGNORES the user's browser font-size setting, so
       text stops responding to zoom, which is the accessibility bug most fluid-type snippets
       quietly ship. Pairing rem with vw keeps both working, and satisfies One UI's 200%
       text-scalability rule that design/CONTRACT.md §1 adopted. */
    '#rail{font-size:clamp(11.5px, 0.62rem + 0.22vw, 14px)}',
    '#rail h3{font-size:clamp(9.5px,0.5rem + 0.14vw,11.5px);letter-spacing:.13em;',
    '  text-transform:uppercase;color:var(--faint,#5c6178);',
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

    /* SUPERSEDE THE OLD PRESENCE RAIL. presence-rail.js registers a tile variant ("Presence Rail")
       whose mount does two things: sets #pills to display:none, and puts `presence-rail` on #tiles
       which makes it flex-direction:column. #tiles lives in the HEADER flex row, so a vertical
       stack of eleven agent rows turns the header into a ~1000px column. THAT is the "ai list at
       the top taking half the screen" from Daniil's very first message.
       It went unfound for four rounds because the variant is persisted PER BROWSER: his had it,
       my headless Chromium did not. Every screenshot I took was of a console where this feature
       was off, so I kept fixing .pills -- an element that is display:none in his configuration.
       Its own description is "vertical avatars + role/state + live status", which is exactly what
       #rail now provides, in a column that was designed to hold it. Same reversible-swap rule as
       #engine-room: hidden, never deleted. */
    '#tiles.presence-rail{display:none !important}',
    '.rfence{display:flex;align-items:center;gap:8px;padding:5px 0;font-size:11.5px;',
    '  border-top:1px solid var(--border,rgba(255,255,255,.07))}',
    '.rfence:first-of-type{border-top:0}',
    '.rfence .nm{font-family:var(--mono,ui-monospace,monospace);color:var(--muted,#9297ab);flex:1;',
    '  min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',

    /* SCROLLBAR — Daniil: "we could use a nice looking ui scroll". Styled, not hidden: a
       scrollbar is the only affordance telling you how much feed exists and where you are in it.
       Hiding it is the common mistake and it costs orientation. */
    '.rail-grid > #log::-webkit-scrollbar,#rail::-webkit-scrollbar{width:10px}',
    '.rail-grid > #log::-webkit-scrollbar-track,#rail::-webkit-scrollbar-track{background:transparent}',
    '.rail-grid > #log::-webkit-scrollbar-thumb,#rail::-webkit-scrollbar-thumb{',
    '  background:linear-gradient(180deg,rgba(122,162,247,.30),rgba(157,124,247,.22));',
    '  border-radius:99px;border:2px solid transparent;background-clip:padding-box}',
    '.rail-grid > #log:hover::-webkit-scrollbar-thumb,#rail:hover::-webkit-scrollbar-thumb{',
    '  background:linear-gradient(180deg,rgba(122,162,247,.55),rgba(157,124,247,.42));background-clip:padding-box}',
    '.rail-grid > #log,#rail{scrollbar-width:thin;scrollbar-color:rgba(122,162,247,.35) transparent}',

    /* JUMP TO LATEST — "zooming to bottom is hard". Appears only when you are actually away
       from the bottom, so it never covers the feed while you are reading live. */
    /* anchored to the GRID, not .app: anchoring to .app put it on top of the composer hint row,
       because bottom:18px there is inside the composer's own 134px band. The feed is what you are
       returning to, so the button belongs at the foot of the feed. */
    '.rail-grid{position:relative}',
    '#rjump{position:absolute;right:322px;bottom:14px;z-index:14;display:none;align-items:center;gap:6px;',
    '  padding:7px 12px;border-radius:99px;cursor:pointer;font:inherit;font-size:11.5px;font-weight:550;',
    '  color:var(--text,#eef0f7);border:1px solid var(--border,rgba(255,255,255,.12));',
    '  background:rgba(18,20,28,.82);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);',
    '  box-shadow:0 10px 30px -12px rgba(0,0,0,.9);transition:transform .16s,opacity .16s}',
    '#rjump.show{display:flex}',
    '#rjump:hover{transform:translateY(-1px)}',
    '#rjump .n{color:var(--user-a,#48e6bf);font-variant-numeric:tabular-nums}',
    '@media (max-width:1080px){#rjump{right:18px}}',

    /* CHAPTERS — "no clickable chapters on the left to quickly orient yourself".
       Derived from the feed itself (speaker changes + time gaps), never hand-maintained. */
    '.rchap{display:flex;gap:8px;align-items:baseline;padding:5px 0;cursor:pointer;',
    '  border-top:1px solid var(--border,rgba(255,255,255,.07));font-size:11.5px}',
    '.rchap:first-of-type{border-top:0}',
    '.rchap:hover .t{color:var(--text,#eef0f7)}',
    '.rchap.here .t{color:var(--user-a,#48e6bf)}',
    '.rchap .ts{font-family:var(--mono,ui-monospace,monospace);font-size:9.5px;',
    '  color:var(--faint,#5c6178);flex:none;width:52px}',
    '.rchap .t{color:var(--muted,#9297ab);flex:1;min-width:0;overflow:hidden;',
    '  text-overflow:ellipsis;white-space:nowrap;transition:color .15s}'
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

  /* Undo the old Presence Rail variant if it is mounted. A CSS hide is not enough: its
     mountPresence() sets `pills.style.display='none'` INLINE, and an inline style outlives any
     stylesheet rule. Re-asserted on every render because the variant can be remounted at runtime
     from the settings panel -- a swap that only holds until the next click is not a swap. */
  function supersedeOldRail() {
    try {
      var t = document.getElementById('tiles');
      if (t && t.classList.contains('presence-rail')) {
        t.classList.remove('show', 'presence-rail');
        t.innerHTML = '';
      }
      var p = document.getElementById('pills');
      if (p && p.style.display === 'none') p.style.display = '';

      /* IDENTIFY BY BEHAVIOUR, NOT BY NAME. The tile layer is a registry of swappable variants
         persisted per browser, so the component stacking agents into the header is one I have
         never had mounted and cannot select for. Four attempts to name it (.pills, the roster
         popover, #tiles.presence-rail) each fixed a real but innocent element.
         What every offender HAS in common is observable: it is a direct header child whose
         natural height far exceeds the band and which holds several stacked rows. The band
         already stops it breaking the page; this stops it rendering as a clipped sliver.
         Guarded tightly so it can never eat a legitimate control: direct children only, must
         want >2x the band AND contain 4+ element children. The brand, the chips and the button
         cluster all fail both tests. */
      var hdr = document.querySelector('header');
      if (hdr) {
        var band = hdr.clientHeight || 72;
        [].forEach.call(hdr.children, function (el) {
          if (el.id === 'pills' || el.dataset.railKept) return;
          var wants = el.scrollHeight;
          if (wants > band * 2 && el.childElementCount >= 4) {
            if (el.dataset.railHid !== '1') {
              el.dataset.railHid = '1';
              el.style.display = 'none';
              try {
                console.info('[rail] hid a header child that wanted ' + wants + 'px in a ' + band +
                  'px band (' + el.childElementCount + ' rows) — the rail owns per-agent presence now. ' +
                  'id=' + (el.id || '(none)') + ' class=' + (el.className || '(none)'));
              } catch (e2) {}
            }
          }
        });
      }
    } catch (e) {}
  }

  function ensure() {
    supersedeOldRail();
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
    mountJump(log);
    return rail;
  }

  /* ---- jump-to-latest ------------------------------------------------------------------
     "zooming to bottom is hard". A feed that auto-scrolls while you read is worse than one
     that does not, so the honest answer is not more auto-scroll -- it is a visible way BACK,
     that appears only once you have actually left the bottom, and that tells you how much you
     missed while you were away. */
  function mountJump(log) {
    if (document.getElementById('rjump')) return;
    var btn = document.createElement('button');
    btn.id = 'rjump';
    btn.title = 'Scroll to the newest message';
    btn.innerHTML = '<span>↓ Latest</span><span class="n"></span>';
    (log.parentNode || document.body).appendChild(btn);   // the grid; see #rjump CSS note
    var seenAtBottom = log.children.length;
    function atBottom() { return (log.scrollHeight - log.scrollTop - log.clientHeight) < 80; }
    function sync() {
      if (atBottom()) { seenAtBottom = log.children.length; btn.classList.remove('show'); return; }
      var behind = Math.max(0, log.children.length - seenAtBottom);
      btn.querySelector('.n').textContent = behind ? '+' + behind : '';
      btn.classList.add('show');
    }
    log.addEventListener('scroll', sync, { passive: true });
    btn.onclick = function () {
      // ONE CLICK MUST ARRIVE. Daniil: "it takes multiple clicks to get to the bottom."
      // A smooth scroll toward scrollHeight is a moving target here -- the feed re-renders on a
      // 5s poll, images/markdown settle after layout, and content-visibility:auto means
      // off-screen rows have an ESTIMATED height that is replaced by the real one as they come
      // into view. Each of those changes scrollHeight mid-animation, so the smooth scroll lands
      // where the bottom USED to be. Jump instantly, then re-assert on the next few frames until
      // the target stops moving. Instant is also the honest interaction: the button says take me
      // to the bottom, not take me toward it.
      var tries = 0;
      (function land() {
        log.scrollTop = log.scrollHeight;
        if (++tries < 8 && (log.scrollHeight - log.scrollTop - log.clientHeight) > 2) {
          requestAnimationFrame(land);
        } else { sync(); }
      })();
    };
    setInterval(sync, 1500);   // catches new messages arriving while scrolled away
    sync();
  }

  /* ---- chapters ------------------------------------------------------------------------
     DERIVED from the feed, never authored: a new chapter starts on a speaker change or a gap
     of >8 minutes. That keeps it honest (it cannot claim structure the transcript does not
     have) and self-maintaining (nothing to update when the feed grows). */
  function chapters(log) {
    var out = [], lastWho = null, lastT = 0;
    [].forEach.call(log.children, function (el) {
      if (!el.classList || !el.classList.contains('msg')) return;
      var who = (el.querySelector('.who b, .who, .nm') || {}).textContent || '';
      who = who.trim().split(/\s+/)[0] || '?';
      var tEl = el.querySelector('.t, .time, .who i, .who span');
      var label = (tEl && tEl.textContent || '').trim();
      var t = Date.parse(el.dataset.ts || '') || 0;
      var gap = lastT && t && (t - lastT) > 8 * 60000;
      if (who !== lastWho || gap) {
        var first = (el.textContent || '').replace(/\s+/g, ' ').trim();
        first = first.replace(/^\S+\s*\d{1,2}:\d{2}\s*(AM|PM)?\s*\??\s*/i, '').slice(0, 46);
        out.push({ el: el, who: who, ts: label, text: first || who });
        lastWho = who;
      }
      if (t) lastT = t;
    });
    return out.slice(-14);          // bounded: a nav that grows without limit is a second feed
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

    /* zone 4 — chapters, so the feed is navigable rather than only scrollable */
    var log = document.getElementById('log');
    var chaps = log ? chapters(log) : [];
    if (chaps.length > 1) {
      h += '<section class="rcard"><h3>Chapters<span class="cnt">' + chaps.length + '</span></h3>';
      chaps.forEach(function (c, i) {
        h += '<div class="rchap" data-i="' + i + '" title="' + esc(c.who) + ' — jump here">' +
             '<span class="ts">' + esc(c.ts || c.who) + '</span>' +
             '<span class="t">' + esc(c.text) + '</span></div>';
      });
      h += '<div class="rfoot">Derived from the feed — a chapter starts on a speaker change or an ' +
           '8-minute gap. Newest ' + chaps.length + ' shown; nothing is authored, so nothing rots.</div></section>';
    }

    /* zone 5 — side channels (the standing ask) */
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
    supersedeOldRail();     // the variant can be remounted at runtime; keep the swap asserted

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
    rail.querySelectorAll('.rchap').forEach(function (el) {
      el.onclick = function () {
        var c = chaps[parseInt(el.dataset.i, 10)];
        if (!c || !c.el) return;
        c.el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        rail.querySelectorAll('.rchap.here').forEach(function (o) { o.classList.remove('here'); });
        el.classList.add('here');
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
