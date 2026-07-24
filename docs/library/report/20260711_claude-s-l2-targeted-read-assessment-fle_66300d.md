---
akashic_id: art_20260711_claude-s-l2-targeted-read-assessment-fle_66300d
akashic_sha: 31c5e2480a72
status: draft
type: report
date: 2026-07-11
title: "Claude's L2 targeted-read assessment -- fleet-doctor noise discipline + pulse protocol"
gist: "on his reply). Sources: research/sources-cache/sre-monitoring-alerting.md + research/sources-cache/systemd-sd-notify-watchdog.md. ## 1. Nois"
tenant: solo
visibility: fleet
seats: []
category: [memory, agent-lifecycle, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_source-google-sre-book-ch-6-monitoring-d_6b0396
    rel: cites
  - target: art_20260711_source-sd-notify-3-man-page-systemd-noti_179395
    rel: cites
created: "2026-07-11T00:11:27"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260711_claude-s-l2-targeted-read-assessment-fle_66300d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Claude's L2 targeted-read assessment -- fleet-doctor noise discipline + pulse protocol

on his reply). Sources: research/sources-cache/sre-monitoring-alerting.md +
research/sources-cache/systemd-sd-notify-watchdog.md.

## 1. Noise discipline for the fleet doctor (RB-27b)

The SRE chapter's law, applied: PAGE on symptoms, DASHBOARD the causes, and every page
must pass the five questions (undetected + urgent + actionable + user-visible; never
safely-ignorable; requires intelligence). Our "page" = a bus interruption/note that
demands Daniel's or an agent's attention; our "dashboard" = the fleet-doctor verb + boot
lines + UI panel. Funnel doctrine says the same thing in-house: noise is a tax.

Per-state ruling:
  SUSPECTED MAIL LOSS  -> PAGE-GRADE (bus note to the ASKER). The symptom: a directed
                          ask consumed with no outcome past deadline. Urgent, actionable
                          (redrive), user-visible (someone is waiting). The only always-
                          page state.
  FLEET FROZEN         -> PAGE-GRADE at boot + UI banner (leftover pause with provenance:
                          actionable -- resume or confirm). Not a bus interruption to
                          agents (they are frozen; the human acts).
  WEDGED               -> DASHBOARD + boot line only. It is a CAUSE-level signal (worklive
                          stale in a phase); long legitimate work trips it (F2), so it
                          fails "never safely ignorable". L0 timeouts usually self-heal it
                          -- page only if a future soak shows wedges that L0 missed AND
                          acting on them is automatable (then it becomes the launcher's
                          auto-revive input, not a page at all -- SRE: rote response =
                          automate, don't page).
  STALLED CONSUMER     -> DASHBOARD + boot line; escalate to ONE bus note only after
                          persisting N consecutive doctor ticks (hysteresis against poll
                          jitter).
  UNHANDLED (P6)       -> unchanged (already boot/promoted-surfaced; it IS the mail-loss
                          symptom at the hours scale; the doctor's mail-loss check is the
                          same symptom at the seconds scale -- one symptom, two horizons).

Also adopted from the chapter: no auto-threshold magic (fixed, named thresholds with env
overrides); doctor output stays SHORT (a full-fleet-healthy run prints one line); every
state line carries its drill-down command (dashboards paired with logs).

## 2. Pulse protocol (RB-27a) vs sd_notify

  ADOPT  pulse-at-half-TTL: progress key TTL 5s, worker pulses ~2s (systemd convention:
         ping at half the watchdog window). Missed-pulse = the detector's signal.
  ADOPT  WATCHDOG=trigger equivalent: the worker may WRITE AN EXPLICIT ERROR VALUE into
         the progress key ("trigger:<reason>") on a caught-fatal -- self-reported failure
         is distinguishable from silent hang, and the doctor renders them differently
         (SELF-REPORTED beats INFERRED in diagnosability).
  ADAPT  NotifyAccess: the pulse writer is gated by construction-bound agent id (the
         ToolBox _bus_send_ok pattern); a full authenticated gate waits for signed
         identity (same honest bound as RB-1/RB-2 -- named, not smuggled).
  REJECT READY/RELOADING/STOPPING mirroring: worklive's phase vocabulary
         (online/handling/idle/...) already carries the lifecycle and predates this;
         renaming to systemd's lexicon adds translation cost, no signal.
  REJECT EXTEND_TIMEOUT_USEC equivalent (a worker extending its own deadline): it
         inverts the trust -- the thing being watched shouldn't move its own goalposts;
         our per-phase grace map (from the earlier phi-accrual deferral) covers the
         long-legit-work case from the DETECTOR side.

## 3. Build-spec consequence for L2

RB-27a: worker-thread pulse (bifrost:progress:<agent>, TTL 5s, ~2s cadence, trigger
value on caught-fatal). RB-27b: doctor verb evaluating {mail-loss, frozen, wedged,
stalled, unhandled} with the paging table above, hysteresis on STALLED, one-line-healthy
output, drill-down per state; wired into boot + bifrost-sync; bus notes ONLY for the two
page-grade states.
