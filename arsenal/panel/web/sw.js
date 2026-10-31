/* sw.js -- the offline shell.
 *
 * ITS ONLY JOB IS TO MAKE THE PAGE OPEN WHEN THE PC IS GONE. The panel's most important message is
 * "PC unreachable, tap link-up in Termux:Widget", and that message must render from the phone's own
 * cache -- a page that needs the unreachable PC in order to say the PC is unreachable is useless at
 * exactly the moment it matters.
 *
 * SO: the SHELL (html/css/js/manifest/icon) is cache-first. THE API IS NEVER CACHED -- /api/* is
 * network-only and fails loudly, because a cached status document would be a stale green dot, which is
 * the one lie this page exists not to tell.
 *
 * The version string is bumped by hand when a shell file changes; there is no build step. An old cache
 * is deleted on activate, so a shell change is one reload away rather than a mystery. */
"use strict";

var CACHE = "phone-panel-v1";
var SHELL = ["/", "/app.css", "/app.js", "/manifest.webmanifest", "/icon.svg"];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE).then(function (cache) {
      return cache.addAll(SHELL);
    }).then(function () { return self.skipWaiting(); })
  );
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) { return k !== CACHE; })
        .map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  var url = new URL(event.request.url);
  if (event.request.method !== "GET") return;
  if (url.pathname.indexOf("/api/") === 0) return;        /* never cached, never served offline */
  event.respondWith(
    caches.match(event.request).then(function (hit) {
      if (hit) return hit;
      return fetch(event.request).then(function (res) {
        if (res && res.ok && url.origin === self.location.origin) {
          var copy = res.clone();
          caches.open(CACHE).then(function (cache) { cache.put(event.request, copy); });
        }
        return res;
      }).catch(function () {
        return caches.match("/");
      });
    })
  );
});
