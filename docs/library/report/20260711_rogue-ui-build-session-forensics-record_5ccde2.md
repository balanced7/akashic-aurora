---
akashic_id: art_20260711_rogue-ui-build-session-forensics-record_5ccde2
akashic_sha: 1a4c271ed65b
status: current
type: report
date: 2026-07-11
title: Rogue UI-build session -- forensics record (2026-07-11)
gist: "Class: evidence Scope: pure evidence + timeline. Diagnosis + fixes live in the fenced analysis (docs/boot-intent-gap-2026-07.md). Incident: "
tenant: solo
visibility: fleet
seats: []
category: [method, ergonomics, ui]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_comms-messaging-pillar-dual-fenced-analy_051ff0
    rel: cites
created: "2026-07-11T02:24:14"
updated: "2026-07-23T21:42:21"
---
<!-- GENERATED PROJECTION of art_20260711_rogue-ui-build-session-forensics-record_5ccde2 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Rogue UI-build session -- forensics record (2026-07-11)

Class: evidence
Scope: pure evidence + timeline. Diagnosis + fixes live in the fenced analysis
(docs/boot-intent-gap-2026-07.md). Incident: a fresh claude session, told to "pick up
where we left off", began building UI while the live session + Daniel intended
engine-hardening FIRST. No damage shipped (caught + stood down), but the boot surfaces
actively MISLED it.

## What the user saw
Daniel: "I launched a new session and it started building ui" -- after pausing UI
explicitly to "clean house first / verify the core before bodywork". That intent was
never in the new session's boot.

## Timeline (UTC; session 3b52 = the live/authoring session, 812c = the rogue one)
- 06:10:55  812c first user prompt: "initialize yourself with akashic aurora and pick
            up where we left off with the previous session". permissionMode
            bypassPermissions, entrypoint claude-desktop.
- 06:10-11  812c runs `py agent_cli.py boot claude` (transcript entries 2,3,11).
            Boot context (entry 17) showed it, VERBATIM:
              # Method: docs/method-baseline-2026-07.md (...)          <- CORRECT framing present
              # Governing arc: docs/comms-pillar-synthesis-2026-07.md  <- STALE: a DONE arc
                  (from note 'comms-pillar-status')
              # where-we-are: ...progress-bars data half shipped...    <- pre-dates the plan
              # Ledger: ... 5 next ...
                  next: T002 - UI: collapse agent reasoning + tool traces into ONE ...
                  next: T007 - Verify Void theme + aurora perf bench ...
- 06:11-17  812c reads the top of the NEXT list (T002, a UI task) and begins UI work.
- 06:17:25  812c last entry (7-minute session).
- 06:19ish  session 3b52 (live) writes the engine-first plan for the FIRST time:
            claude->claude handoff + next-focus note + live stop-order. The intent did
            not exist on any durable surface until AFTER 812c had already ended.

## The three misleading surfaces (verified STILL live at 06:1x via a fresh boot)
1. GOVERNING ARC = docs/comms-pillar-synthesis-2026-07.md -- whose OWN note body reads
   "ARC COMPLETE 2026-07-10. ALL SLICES SHIPPED". Boot pointed a fresh agent at a
   finished arc as if it governed. (The picker takes the newest <slug>-status note whose
   slug tokens hit an active ledger title; no active task carries a 'resilience'/
   'liveness' *-status note, so the done comms-pillar-status won by fallback.)
2. NEXT list, top entries = T002 "UI: collapse agent reasoning..." and T007 "Verify Void
   theme...". Both UI. They sit on top because they are the OLDEST approved tasks; NEXT
   carries no priority/sequence, so top-of-NEXT reads as "do this next".
3. where-we-are = "progress-bars data half shipped" -- true but silent on the
   engine-before-UI sequence, which had not been decided-durably yet.

## What was NOT the cause
- Not a boot failure: 812c booted correctly and the Method-baseline framing WAS present
  (Daniel's framing-check question: partial pass -- method yes, arc/sequence no).
- Not the running-session cursor gap (RB-21): 812c was a FRESH boot, not a stale
  long-runner. It was misled by durable content, not by missing a live update.
- Not disobedience: the session did exactly what boot told it -- picked the top NEXT
  task. The surfaces were wrong, not the reading.

## The core finding (one line)
Session-level PRIORITY/SEQUENCE intent ("engine before UI") had no durable boot home at
the moment it was decided; meanwhile the governing-arc pointer was stale and the NEXT
list was unordered -- so boot actively recommended the paused work.

## Cross-references
- The reactive fix (this session): engine-first claude->claude handoff + next-focus note
  + live stop-order, all pushed 06:19+.
- Related open work: RB-21 session-cursor discipline (running sessions don't re-read
  boot -- a DIFFERENT gap, not this one); the governing-arc picker
  (agent_cli.py _orientation_header, ~942) and its known keyword-projective bound.
