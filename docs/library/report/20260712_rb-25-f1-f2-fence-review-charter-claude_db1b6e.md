---
akashic_id: art_20260712_rb-25-f1-f2-fence-review-charter-claude_db1b6e
akashic_sha: 9db0db5bae5e
status: draft
type: report
date: 2026-07-12
title: "RB-25 F1+F2 fence review — charter (claude → deepseek, 2026-07-12)"
gist: "Class: review charter (fenced — deepseek reviews BLIND; claude's pass-1 is sealed outside the repo and will be reconciled only AFTER deepsee"
tenant: solo
visibility: fleet
seats: []
category: [security, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_newborn-gauntlet-pre-registered-rubric-t_16fdb3
    rel: cites
  - target: art_20260712_rb-25-drill-1-newborn-gauntlet-re-run-ve_419213
    rel: cites
  - target: art_20260709_agent-security-schema-design-proposal_cdccf1
    rel: cites
  - target: art_20260712_rb-25-f1-f2-fence-review-deepseek-indepe_3b02b6
    rel: cites
  - target: art_20260711_rb-25-engine-exam-runbook-review-deepsee_3bfc0b
    rel: cites
created: "2026-07-12T01:45:34"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260712_rb-25-f1-f2-fence-review-charter-claude_db1b6e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# RB-25 F1+F2 fence review — charter (claude → deepseek, 2026-07-12)

Class: review charter (fenced — deepseek reviews BLIND; claude's pass-1 is sealed
       outside the repo and will be reconciled only AFTER deepseek's record lands)

## Why this review

Commit d926bb8 ("RB-25 findings F1+F2 FIXED") shipped 2026-07-12 ~00:37, inside a
window where the authoring harness was DEGRADED (model fell back to Opus mid-session;
Daniel flagged it). It touches kill-critical trust code — the ACL bypass class the
newborn gauntlet proved live, and cursor onboarding discipline. Daniel's directive:
this is the core of the system and must be the best it can possibly be. Per the
method baseline (docs/method-baseline-2026-07.md), a fenced cross-model review gates
ratification of this slice; RB-25 drills 2-4 stay parked until the gate is decided.

## Artifacts (raw — form your own view before reading anything by claude about this slice)

- The diff: `git show d926bb8` — core/trust/registry.py (may_run_runner),
  core/comm/bus.py (seed_cursor_at_tail), scripts/bifrost_runner_deepseek.py
  (startup wiring for both), tests/test_rb25_newborn_findings.py (escape pin).
- The frozen contract: tests/test_rb25_newborn_findings.py module docstring
  (registration commit 67adeb0, M3).
- The findings' source: docs/newborn-gauntlet-rubric-2026-07.md +
  research/reviewed/newborn-gauntlet-transcript-2026-07-12.md (F1: 3 reply + 47 trace
  broadcasts from a quarantined id landed on the bus; F2: virgin cursor drained
  months-old backlog as current).
- Threat model: core/trust/registry.py resolve() docstring, security/acl.json,
  docs/security-schema-proposal.md / -implementation.md.
- SCOPE IS THE FINDING CLASS, NOT THE DIFF: audit EVERY path that starts a runner or
  reaches the bus reply/trace lanes (the whole scripts/ runner family and any other
  bus-reaching infrastructure lane), not only the files d926bb8 touched.

## Deliverables

1. Verdict per change — F1 helper, F1 runner wiring, F2 helper, F2 runner wiring,
   pins: CORRECT / AMEND (state the amendment) / REJECT (state why).
2. Coverage gaps: anything the diff MISSED for the F1/F2 finding classes.
3. Failure-direction analysis: for each new guard, what happens when its own
   machinery fails (exception, import failure, dead Redis, corrupt ACL) — and is
   that the direction our threat model wants?
4. Escape-hatch ruling: AKASHIC_DRILL_ECHO gates both fixes off — right scope, or
   narrow further?
5. Overall GATE for ratifying d926bb8: GREEN / AMBER (pass after amendments — list
   them) / RED (revert-and-rebuild).
6. Write the FULL report verbatim to
   research/reviewed/deepseek-rb25-f1f2-review-2026-07-12.md (guarded write is
   enabled on your runner), then reply on the bus with the one-line GATE + the
   record path.

## Side reconcile-ask (small, do last)

research/reviewed/deepseek-rb25-runbook-review-2026-07-11.md is now landed verbatim
from disk — but its summary says "4 AMENDMENTS" while your bus line and c1bb1f6 both
say 6 (your runner hop was killed mid-reshape that night). Confirm whether the landed
copy is your final; if your final counted 6, reply with the delta so the record chain
is whole.

## Method notes

- Think mode is on; take the depth this deserves — deny-by-default doctrine review,
  not a style pass.
- Do not soften: a clean pass teaches nothing (the exam doctrine). If it should be
  RED, say RED.
