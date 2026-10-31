/* app.js -- the phone panel's whole client. No framework, no build step, no inline script (the page's
 * CSP forbids inline, which is a feature: this file is the only code that runs).
 *
 * THREE RULES THE PAGE FOLLOWS, and each one exists because of what this screen is:
 *
 *   1. IT SHOWS WHAT IT MEASURED, AND SAYS WHEN IT MEASURED NOTHING. The status document is fetched
 *      with a timeout; when the fetch fails the page does NOT render the last known state as current.
 *      It shows the PC-unreachable banner and an amber dot everywhere, because a stale green is the
 *      most expensive lie a control panel can tell.
 *
 *   2. STOP AND RESTART ARE ALWAYS TWO TAPS. The first tap opens a dialog; confirming mints a confirm
 *      token with POST /api/confirm and then spends it in POST /api/action. The token is single-use and
 *      bound to that service and verb, so a mis-tap cannot become an outage -- and the client cannot
 *      skip the server-side gate even if this file were replaced.
 *
 *   3. THE LINK FIX IS NOT ON THIS PAGE. When the PC is unreachable, the next move is Termux:Widget on
 *      the phone (link-up). The banner names it. Nothing here pretends it can restore its own transport.
 */
"use strict";

var POLL_MS = 5000;
var FETCH_TIMEOUT_MS = 6000;
var state = { doc: null, busy: false, timer: null };

function $(id) { return document.getElementById(id); }

function el(tag, cls, text) {
  var node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function toast(message, kind) {
  var t = $("toast");
  t.textContent = message;
  t.className = "toast" + (kind ? " " + kind : "");
  t.hidden = false;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(function () { t.hidden = true; }, 5000);
}

/* ------------------------------------------------------------------ the transport */
function api(path, body) {
  var controller = new AbortController();
  var timer = setTimeout(function () { controller.abort(); }, FETCH_TIMEOUT_MS);
  var opts = { signal: controller.signal, cache: "no-store", headers: {} };
  if (body !== undefined) {
    opts.method = "POST";
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  return fetch(path, opts).then(function (res) {
    return res.json().catch(function () { return {}; }).then(function (json) {
      if (!res.ok) {
        var err = new Error(json.error || ("HTTP " + res.status));
        err.status = res.status;
        err.payload = json;
        throw err;
      }
      return json;
    });
  }).finally(function () { clearTimeout(timer); });
}

/* ------------------------------------------------------------------ rendering */
function dot(colour) { return el("span", "dot " + (colour || "amber")); }

function row(name, note, colour) {
  var li = el("li", "row");
  li.appendChild(dot(colour));
  var body = el("div");
  body.appendChild(el("div", "name", name));
  if (note) body.appendChild(el("div", "note", note));
  li.appendChild(body);
  li.appendChild(el("span", "note", colour || "amber"));
  return li;
}

function renderLink(doc) {
  var link = doc.link || {};
  var colours = link.colours || {};
  $("verdict").textContent = link.verdict || "(the reachability verb reported no verdict)";
  var ul = $("link-rows");
  ul.replaceChildren();
  var rows = [
    ["Tunnel", link.tunnel, "the ssh -R forward from the PhoneLink watcher"],
    ["Tailnet", link.tailnet, (link.tailnet && link.tailnet.address) || "the phone's own address"],
    ["Gateway", link.gateway, "the Discord gateway process"],
    ["Listener", link.listener, "this seat's wake listener"]
  ];
  rows.forEach(function (pair) {
    var label = pair[0];
    var item = pair[1] || {};
    var note = [item.why, pair[2]].filter(Boolean).join(" — ");
    var li = row(label, note, colours[label.toLowerCase()] || "amber");
    ul.appendChild(li);
  });
  if (link.stale) {
    ul.appendChild(row("Stale reading", link.why || "the reachability verb failed; the last good " +
                       "reading is shown and labelled", "amber"));
  }
}

function renderVideo(doc) {
  var video = doc.video || {};
  var apollo = video.apollo || {};
  var ul = $("video-rows");
  ul.replaceChildren();
  ul.appendChild(row("Apollo", [apollo.state, apollo.why].filter(Boolean).join(" — "),
                     apollo.colour || "amber"));
  var artemis = video.artemis || {};
  var btn = $("artemis");
  var why = $("artemis-why");
  if (artemis.configured) {
    btn.href = artemis.deep_link;
    btn.textContent = "Open " + (artemis.label || "Artemis");
    btn.hidden = false;
    why.textContent = "Hands the stream to the phone's own player; Apollo serves it.";
  } else {
    btn.hidden = true;
    why.textContent = artemis.why || "No Artemis deep link is configured for this PC.";
  }
}

function renderServices(doc) {
  var host = $("services");
  host.replaceChildren();
  var groups = doc.groups || [];
  var services = doc.services || [];
  groups.forEach(function (group) {
    var rows = services.filter(function (s) { return s.group === group; });
    if (!rows.length) return;
    var card = el("section", "card");
    card.appendChild(el("h2", null, group.charAt(0).toUpperCase() + group.slice(1)));
    rows.forEach(function (svc) { card.appendChild(serviceCard(svc)); });
    host.appendChild(card);
  });
}

function serviceCard(svc) {
  var wrap = el("div", "svc");
  var head = row(svc.label + " ", svc.why || svc.state, svc.colour);
  wrap.appendChild(head);
  if (svc.actions && svc.actions.length) {
    var actions = el("div", "actions");
    svc.actions.forEach(function (verb) {
      var destructive = (svc.confirm || []).indexOf(verb) >= 0;
      var btn = el("button", "btn" + (destructive ? " danger" : " go"), verb);
      btn.type = "button";
      btn.addEventListener("click", function () {
        if (destructive) ask(svc, verb); else run(svc, verb);
      });
      actions.appendChild(btn);
    });
    wrap.appendChild(actions);
  }
  if (svc.log_tail && svc.log_tail.length) {
    wrap.appendChild(el("pre", "log", svc.log_tail.join("\n")));
  }
  return wrap;
}

function renderWatched(doc) {
  var rows = doc.status_only || [];
  var card = $("status-only");
  card.hidden = rows.length === 0;
  var ul = $("watch-rows");
  ul.replaceChildren();
  rows.forEach(function (svc) {
    ul.appendChild(row(svc.label, svc.why_no_actions || svc.why, svc.colour));
  });
}

function renderAudit(doc) {
  var rows = (doc.audit_tail || []).slice().reverse();
  var ul = $("audit-rows");
  ul.replaceChildren();
  if (!rows.length) {
    ul.appendChild(el("li", "row muted", "no actions recorded yet"));
    return;
  }
  rows.forEach(function (rec) {
    var when = (rec.ts || "").replace("T", " ");
    var what = (rec.decision || "?") + " " + (rec.verb || "") + " " + (rec.service || "");
    var note = [when, rec.reason || rec.detail || ""].filter(Boolean).join(" — ");
    ul.appendChild(row(what.trim(), note, rec.ok ? "green" : "amber"));
  });
}

function render(doc) {
  state.doc = doc;
  $("offline").hidden = true;
  $("asof").textContent = "as of " + (doc.generated || "?") + " · panel " + (doc.panel && doc.panel.port);
  renderLink(doc);
  renderVideo(doc);
  renderServices(doc);
  renderWatched(doc);
  renderAudit(doc);
}

function renderOffline(reason) {
  state.doc = null;
  $("offline").hidden = false;
  $("asof").textContent = "no answer from the PC — " + reason;
  $("verdict").textContent = "not measured (the request never arrived)";
  var ul = $("link-rows");
  ul.replaceChildren();
  ["Tunnel", "Tailnet", "Gateway", "Listener"].forEach(function (name) {
    ul.appendChild(row(name, "not measured", "amber"));
  });
  /* The service cards stay on screen with every dot amber and every button disabled: the services are
   * still real, the reading is not. A removed card would look like a service that went away. */
  var services = $("services");
  services.querySelectorAll("button").forEach(function (b) { b.disabled = true; });
  if (!services.children.length) {
    var card = el("section", "card");
    card.appendChild(el("h2", null, "Services"));
    card.appendChild(el("p", "muted", "The service list is served by the PC, so it cannot be shown " +
                                     "while the PC is unreachable. Tap link-up in Termux:Widget, " +
                                     "then refresh."));
    services.appendChild(card);
  }
}

/* ------------------------------------------------------------------ actions */
function refresh() {
  if (state.busy) return;
  state.busy = true;
  return api("/api/status").then(function (doc) {
    render(doc);
  }).catch(function (err) {
    renderOffline(err.name === "AbortError" ? "timed out" : (err.message || "unreachable"));
  }).finally(function () {
    state.busy = false;
    schedule();
  });
}

function schedule() {
  clearTimeout(state.timer);
  state.timer = setTimeout(function () {
    if (document.visibilityState === "visible") refresh();
    else schedule();
  }, POLL_MS);
}

function ask(svc, verb) {
  var dialog = $("confirm");
  $("confirm-title").textContent = verb.charAt(0).toUpperCase() + verb.slice(1) + " " + svc.label + "?";
  $("confirm-body").textContent = svc.why || ("This " + verb + "s " + svc.id + " on the PC.");
  dialog.returnValue = "";
  dialog.showModal();
  dialog.addEventListener("close", function onClose() {
    dialog.removeEventListener("close", onClose);
    if (dialog.returnValue === "go") run(svc, verb, true);
  }, { once: true });
}

function run(svc, verb, confirmed) {
  var label = verb + " " + svc.label;
  toast(label + "…");
  var chain = Promise.resolve();
  if (confirmed) {
    chain = chain.then(function () {
      return api("/api/confirm", { service: svc.id, verb: verb }).then(function (minted) {
        return minted.token;
      });
    });
  }
  chain.then(function (token) {
    var body = { service: svc.id, verb: verb };
    if (token) body.token = token;
    return api("/api/action", body);
  }).then(function (res) {
    toast(label + ": " + (res.ok ? "done" : "did not verify") + " — " + (res.state || ""),
          res.ok ? "good" : "bad");
  }).catch(function (err) {
    toast(label + " failed: " + (err.message || err), "bad");
  }).finally(function () {
    setTimeout(refresh, 600);
  });
}

/* ------------------------------------------------------------------ boot */
$("refresh").addEventListener("click", function () { refresh(); });
document.addEventListener("visibilitychange", function () {
  if (document.visibilityState === "visible") refresh();
});

if ("serviceWorker" in navigator) {
  window.addEventListener("load", function () {
    navigator.serviceWorker.register("/sw.js").catch(function () { /* offline shell is a bonus */ });
  });
}

refresh();
