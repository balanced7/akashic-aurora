---
akashic_id: art_20260711_source-sd-notify-3-man-page-systemd-noti_179395
akashic_sha: 57dc97224a38
status: draft
type: design
date: 2026-07-11
title: "SOURCE: sd_notify(3) man page (systemd notification protocol)"
gist: "# SOURCE: sd_notify(3) man page (systemd notification protocol) # URL: https://man7.org/linux/man-pages/man3/sd_notify.3.html # Neutral extr"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-11T00:04:48"
updated: "2026-07-11T00:04:48"
---
<!-- GENERATED PROJECTION of art_20260711_source-sd-notify-3-man-page-systemd-noti_179395 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# SOURCE: sd_notify(3) man page (systemd notification protocol)

# SOURCE: sd_notify(3) man page (systemd notification protocol)
# URL: https://man7.org/linux/man-pages/man3/sd_notify.3.html
# Neutral extraction (claude, 2026-07-11). LOCAL READING COPY -- gitignored, never committed.

## Notification Protocol States

- **READY=1:** startup or reload completion. Only for Type=notify services; "the only
  value services should send is 'READY=1' (READY=0 is not defined)."
- **RELOADING=1:** beginning a configuration reload; must follow with READY=1 on completion.
- **STOPPING=1:** shutdown initiated.
- **STATUS=...:** free-form single-line UTF-8 status (state, completion %, error text).
- **WATCHDOG=1:** keep-alive ping for services with WatchdogSec= configured.
- **WATCHDOG=trigger:** signals an INTERNAL ERROR -- triggers the configured watchdog
  action regardless of whether WatchdogSec= is enabled (an explicit self-report path,
  distinct from missing a keepalive).
- **EXTEND_TIMEOUT_USEC=...:** extends the startup/runtime/shutdown timeout by the given
  microseconds (applicable when the current state's duration would exceed the original
  TimeoutStartSec=/RuntimeMaxSec=/TimeoutStopSec=).

## Watchdog Mechanism

Services "need to issue [keep-alive pings] in regular intervals if WatchdogSec= is
enabled." Check availability via sd_watchdog_enabled(3) before use. (Convention from
sd_watchdog_enabled: ping at roughly HALF the returned interval.) WATCHDOG_USEC can reset
the watchdog interval at runtime.

## Access Control (who may notify)

NotifyAccess= in the unit gates acceptance:
- **main/exec:** only processes directly forked by the service manager may notify.
- **all:** auxiliary processes may notify (timing risks if they exit right after sending).
"systemd will accept status data sent from a service only if the NotifyAccess= option is
correctly set."

## Race Mitigation

sd_notify_barrier() ensures all notifications sent before the call have been picked up by
the service manager before it returns -- for processes not invoked by the manager.
