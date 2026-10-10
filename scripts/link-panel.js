/* link-panel.js -- the console's fleet-link panel (RFC #70): members, devices, delivery, the
 * quarantine queue and alarms, with promote / accept / decline behind an explicit confirm.
 *
 * Everything another fleet wrote is UNTRUSTED TEXT: it is only ever set with textContent, never
 * parsed as HTML. Polls /api/link every 10 s while the panel is open, and not at all while closed
 * (one scheduler, as rail.js). Colours come from the page's CSS variables.
 */
(function (global) {
  'use strict';

  var open = false, timer = null, root = null, body = null;

  function el(tag, text, style) {
    var e = document.createElement(tag);
    if (text !== undefined && text !== null) e.textContent = String(text);
    if (style) e.setAttribute('style', style);
    return e;
  }

  function when(ts) {
    if (!ts) return 'never';
    var d = new Date(ts * 1000);
    return d.toLocaleString();
  }

  function act(action, payload, question) {
    if (!global.confirm(question)) return;
    payload.action = action;
    payload.confirm = true;
    fetch('/api/link/act', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (r) { return r.json(); }).then(function (out) {
      if (!out.ok) global.alert('Not done: ' + (out.why || 'refused'));
      tick();
    });
  }

  function button(label, onclick) {
    var b = el('button', label, 'margin-left:6px;background:var(--panel2);color:var(--text);' +
      'border:1px solid var(--border);border-radius:4px;padding:1px 6px;cursor:pointer;font:inherit');
    b.addEventListener('click', onclick);
    return b;
  }

  function renderLink(L) {
    var s = L.status, box = el('div', null, 'border-top:1px solid var(--border);padding:8px 0');
    box.appendChild(el('div', s.name + '  (epoch ' + s.epoch + ', our role ' + s.my_role + ')',
      'font-weight:600;color:var(--text)'));
    (s.alarms || []).forEach(function (a) {
      box.appendChild(el('div', 'ALARM ' + a.kind + ' from ' + a.author.slice(0, 16) + ': ' + a.detail,
        'color:var(--danger)'));
    });
    if (s.rotation_due) box.appendChild(el('div', 'Key rotation due', 'color:var(--amber)'));
    (s.members || []).forEach(function (m) {
      var line = el('div', null, 'color:var(--muted);margin-top:4px');
      var state = m.removed ? 'removed' : m.pending ? 'pending' : m.role;
      line.appendChild(el('span', m.label + (m.us ? ' (us)' : '') + ': ' + state, 'color:var(--text)'));
      if (!m.us && !m.removed) {
        if (m.verified) line.appendChild(el('span', '  verified', 'color:var(--accent)'));
        else line.appendChild(button('mark verified', function () {
          act('verify', { link: s.link, member: m.root },
            'Did you compare this safety number with ' + m.label + ' over a channel you trust?\n\n' + m.safety_number);
        }));
      }
      box.appendChild(line);
      (m.devices || []).forEach(function (d) {
        var extra = d.removed ? '  removed' : d.frozen ? '  FROZEN' : d.cert_expired ? '  cert expired' : '';
        box.appendChild(el('div', '   ' + d.label + ' ' + d.device.slice(0, 12) + '  head ' + d.head +
          '  last contact ' + when(d.last_contact) + extra, 'color:var(--faint);font-size:90%'));
      });
    });
    (s.pending_joins || []).forEach(function (p) {
      var line = el('div', 'Join waiting: ' + (p.label || p.root.slice(0, 16)), 'color:var(--amber);margin-top:4px');
      if (p.needs_approval) {
        line.appendChild(button('accept', function () {
          act('accept', { link: s.link, join: p.join }, 'Admit ' + p.label + ' and give them the read key?');
        }));
        line.appendChild(button('decline', function () {
          act('decline', { link: s.link, join: p.join }, 'Refuse ' + p.label + '?');
        }));
      }
      box.appendChild(line);
    });
    (s.sent || []).slice(0, 5).forEach(function (r) {
      box.appendChild(el('div', 'sent #' + r.seq + ' ' + (r.kind || '') + ': ' + (r.receipts || 'not yet delivered'),
        'color:var(--faint);font-size:90%'));
    });
    box.appendChild(el('div', 'Quarantine (' + s.quarantine_unpromoted + ' not promoted)', 'margin-top:6px;color:var(--text)'));
    (L.inbox || []).forEach(function (q) {
      var line = el('div', null, 'margin:3px 0;color:var(--muted)');
      line.appendChild(el('span', '[' + q.kind + '] ' + q.fleet + '/' + q.seat_claim + ' -> ' + (q.to || 'link') + ': '));
      line.appendChild(el('span', q.content.slice(0, 280), 'color:var(--text)'));
      line.appendChild(button('promote', function () {
        act('promote', { link: s.link, record: q.record_id },
          'Put this message from ' + q.fleet + ' on our bus? It arrives as data with no authority.\n\n' +
          q.content.slice(0, 400));
      }));
      box.appendChild(line);
    });
    return box;
  }

  function render(snap) {
    if (!body) return;
    body.textContent = '';
    var h = snap.health || {};
    (h.problems || []).forEach(function (p) { body.appendChild(el('div', p, 'color:var(--amber)')); });
    if (!h.in_use) {
      body.appendChild(el('div', 'No fleet links here. `aurora link create <name>` starts one.', 'color:var(--muted)'));
      return;
    }
    body.appendChild(el('div', 'daemon ' + (h.running ? 'running' : 'not running'), 'color:var(--faint)'));
    (snap.links || []).forEach(function (L) { body.appendChild(renderLink(L)); });
  }

  function tick() {
    if (!open) return;
    fetch('/api/link').then(function (r) { return r.json(); }).then(render).catch(function () {});
  }

  function toggle() {
    open = !open;
    root.style.display = open ? 'block' : 'none';
    if (open) { tick(); timer = setInterval(tick, 10000); }
    else if (timer) { clearInterval(timer); timer = null; }
  }

  function start() {
    if (!document.body) { setTimeout(start, 400); return; }
    var tab = el('button', 'Links', 'position:fixed;right:14px;bottom:14px;z-index:60;background:var(--panel);' +
      'color:var(--text);border:1px solid var(--border);border-radius:6px;padding:4px 10px;cursor:pointer');
    tab.setAttribute('title', 'Fleet links: members, delivery, quarantine');
    tab.addEventListener('click', toggle);
    root = el('div', null, 'display:none;position:fixed;right:14px;bottom:52px;z-index:60;width:min(560px,92vw);' +
      'max-height:70vh;overflow:auto;background:var(--panel);color:var(--text);border:1px solid var(--border);' +
      'border-radius:8px;padding:10px 12px;box-shadow:0 8px 24px var(--shadow);font-size:13px');
    root.appendChild(el('div', 'Fleet links', 'font-weight:700;margin-bottom:6px'));
    body = el('div');
    root.appendChild(body);
    document.body.appendChild(tab);
    document.body.appendChild(root);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();

  global.BifrostLinks = { tick: tick, toggle: toggle };
})(window);
