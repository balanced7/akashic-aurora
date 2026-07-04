// presence-rail.js — vertical rich-presence panel (claude's lane, Aurora Glass)
//
// Replaces the horizontal top-bar agent pills with a VERTICAL presence panel per Daniel's mockup
// (OneUI/Apple/Ubiquity/Razer synthesis): each agent = gradient avatar square + name + state badge
// + live status line + an activity meter. Registers as a standalone 'tile' variant (the theme-void.js
// pattern) so it drops in with no surgery on bifrost_ui.py's structure.
//
// Data seam (kept minimal): bifrost_ui.py's applyStatus() caches window._glassCardData + window._lastActs
// and calls window.renderPresence(data, activities) when this tile is active. We read the global
// avatarInfo()/setTarget() helpers. Everything else lives here so the design is iterable in this file.

(function (global) {
  'use strict';

  var CSS =
    '#tiles.presence-rail{display:flex;flex-direction:column;gap:0;padding:4px 4px}' +
    '.prow{display:flex;gap:11px;align-items:center;padding:9px 8px;border-top:1px solid var(--glass-line,rgba(255,255,255,.07));cursor:pointer;border-radius:11px;transition:background .15s}' +
    '.prow:first-child{border-top:0}' +
    '.prow:hover{background:rgba(255,255,255,.045)}' +
    '.pav{width:34px;height:34px;border-radius:11px;flex:none;display:grid;place-items:center;font-size:12.5px;font-weight:700;color:#0a0b0f;letter-spacing:.02em;box-shadow:0 2px 8px -2px rgba(0,0,0,.6)}' +
    '.pav.off{filter:grayscale(.75) brightness(.55)}' +
    '.pinfo{flex:1;min-width:0}' +
    '.pname{font-size:13px;font-weight:600;display:flex;align-items:center;gap:7px;color:var(--text)}' +
    '.pbadge{font-size:8.5px;letter-spacing:.06em;text-transform:uppercase;padding:2px 6px;border-radius:5px;color:var(--muted);border:1px solid var(--glass-line,rgba(255,255,255,.14));font-weight:700;white-space:nowrap}' +
    '.pbadge.on{color:var(--user,#5fd39b);border-color:rgba(95,211,155,.38);background:rgba(95,211,155,.10)}' +
    '.pbadge.halt{color:var(--danger,#f0666e);border-color:rgba(240,102,110,.4);background:rgba(240,102,110,.10)}' +
    '.pbadge.run{color:var(--deepseek,#7aa2f7);border-color:rgba(122,162,247,.4);background:rgba(122,162,247,.10)}' +
    '.pstatus{font-size:11px;color:var(--muted);font-family:var(--mono,ui-monospace,monospace);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.pstatus.think{color:var(--deepseek,#7aa2f7)}' +
    '.pmeter{height:3px;border-radius:3px;background:rgba(255,255,255,.07);margin-top:6px;overflow:hidden}' +
    '.pmeter i{display:block;height:100%;border-radius:3px;background:linear-gradient(90deg,var(--deepseek,#7aa2f7),var(--user,#5fd39b));animation:pmeter 1.7s ease-in-out infinite}' +
    '@keyframes pmeter{0%,100%{width:28%;margin-left:0}50%{width:70%;margin-left:15%}}' +
    '@media (prefers-reduced-motion:reduce){.pmeter i{animation:none;width:55%}}';

  function injectCss() {
    if (document.getElementById('presence-rail-css')) return;
    var s = document.createElement('style');
    s.id = 'presence-rail-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function esc(x) { return String(x == null ? '' : x).replace(/[&<>"]/g, function (c) {
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // ACTIVE verbs → the meter animates + status is "thinking"-coloured
  var ACTIVE = { thinking: 1, reading: 1, writing: 1, searching: 1, running: 1, recalling: 1, working: 1 };

  // window.renderPresence(data, activities) — called by applyStatus each poll (and on mount).
  global.renderPresence = function (d, acts) {
    var host = document.getElementById('tiles');
    if (!host || !host.classList.contains('presence-rail')) return;
    d = d || {}; acts = acts || {};
    var online = new Set(d.agents || []);
    var roster = d.roster || [].concat(d.known || [], d.agents || [], ['user']);
    var uniq = []; var seen = {};
    roster.forEach(function (a) { if (a && !seen[a]) { seen[a] = 1; uniq.push(a); } });
    var sig = d.signals || {};

    var html = uniq.map(function (aid) {
      var isUser = aid === 'user';
      var on = isUser || online.has(aid);
      var info = (typeof global.avatarInfo === 'function') ? global.avatarInfo(aid)
                 : { a: '#7aa2f7', b: '#5fd39b', l: (aid[0] || '?').toUpperCase() };
      var g = sig[aid] || {};
      var act = acts[aid] || null;
      var active = act && ACTIVE[act.state];
      // badge: halted > running > online > offline
      var badge, bcls;
      if (g.halted) { badge = 'halted'; bcls = 'halt'; }
      else if (g.runner || active) { badge = active ? act.state : 'active'; bcls = 'run'; }
      else if (on) { badge = 'online'; bcls = 'on'; }
      else { badge = 'offline'; bcls = ''; }
      // status line
      var status;
      if (act && act.state) status = act.state + (act.detail ? ' · ' + act.detail : '');
      else if (g.runner) status = 'runner · listening';
      else if (isUser) status = 'steering';
      else status = on ? 'idle' : 'offline';
      var grad = 'background:linear-gradient(140deg,' + info.a + ',' + info.b + ')';
      return '' +
        '<div class="prow" data-aid="' + esc(aid) + '" title="message ' + esc(aid) + '">' +
          '<div class="pav ' + (on ? '' : 'off') + '" style="' + grad + '">' + esc(info.l) + '</div>' +
          '<div class="pinfo">' +
            '<div class="pname">' + esc(aid) + '<span class="pbadge ' + bcls + '">' + esc(badge) + '</span></div>' +
            '<div class="pstatus ' + (active ? 'think' : '') + '">' + esc(status) + '</div>' +
            (active ? '<div class="pmeter"><i></i></div>' : '') +
          '</div>' +
        '</div>';
    }).join('');

    host.innerHTML = html;
    // click a row → target that agent (reuse the global helper)
    [].forEach.call(host.querySelectorAll('.prow'), function (el) {
      el.addEventListener('click', function () {
        var aid = el.getAttribute('data-aid');
        if (aid && aid !== 'user' && typeof global.setTarget === 'function') global.setTarget(aid);
      });
    });
  };

  function ready() {
    return typeof global.registerVariant === 'function' && document.getElementById('tiles');
  }

  function install() {
    if (!ready()) return false;
    injectCss();
    global.registerVariant(
      'tile', 'presence', 'Presence Rail', 'vertical avatars + role/state + live status',
      function mountPresence() {
        var pills = document.getElementById('pills'); if (pills) pills.style.display = 'none';
        var t = document.getElementById('tiles'); t.classList.add('show', 'presence-rail');
        global.renderPresence(global._glassCardData, global._lastActs);   // immediate paint from cache
      },
      function unmountPresence() {
        var pills = document.getElementById('pills'); if (pills) pills.style.display = '';
        var t = document.getElementById('tiles'); t.classList.remove('show', 'presence-rail');
      }
    );
    // Auto-activate for anyone who hasn't explicitly chosen a tile — so the panel shows by default
    // (respects an explicit user choice, which localStorage records).
    try {
      if (!localStorage.getItem('bifrost_pref_tile') && typeof global.setPref === 'function') {
        global.setPref('tile', 'presence');
      }
    } catch (e) {}
    return true;
  }

  if (!install()) {
    var n = 0, iv = global.setInterval(function () { if (install() || ++n > 30) global.clearInterval(iv); }, 50);
  }
})(typeof window !== 'undefined' ? window : globalThis);
