---
akashic_id: art_20260714_verify-brief-t045-storm-rerun-cfdcb65f-f_dc68fc
akashic_sha: e53025941918
status: current
type: design
date: 2026-07-14
title: "Verify brief — T045 storm rerun cfdcb65f (fence-lite, M1-BRIEF format)"
gist: "Tier: FENCE-LITE per M1-LITE (single-blind adversarial review; evidence-grading of an isolated drill — no blind half needed; the executing a"
tenant: solo
visibility: fleet
seats: []
category: [bus, security, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_t045-stage-2-runner-consume-cutover-scop_b9c06c
    rel: cites
  - target: art_20260714_deepseek-t045-storm-rerun-verify-cfdcb65_888077
    rel: cites
created: "2026-07-14T09:36:46"
updated: "2026-07-23T21:42:12"
---
<!-- GENERATED PROJECTION of art_20260714_verify-brief-t045-storm-rerun-cfdcb65f-f_dc68fc -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Verify brief — T045 storm rerun cfdcb65f (fence-lite, M1-BRIEF format)

Tier: FENCE-LITE per M1-LITE (single-blind adversarial review; evidence-grading of an
isolated drill — no blind half needed; the executing agent authored, the verifier grades).

## (1) CHARTER
REVIEW fence-lite: independent verify of the T045 stage-2 completion bar — the RB-25
storm rerun (storm cfdcb65f) executed with every consumer on the work lane — plus the
one post-storm fix it surfaced (newborn shadow/bc seeding, pin R11).

## (2) INPUTS
- research/reviewed/rb25-drill3-evidence-cfdcb65f.json (the bundle; incl. s6, session_leg, t045 blocks)
- research/reviewed/rb25-drill3-ledger-cfdcb65f.json (pre-seeded send ledger)
- research/reviewed/rb25-drill3-logs-cfdcb65f/ (all child logs)
- tests/rb25_drill3_orchestrate.py (the --t045 harness additions; frozen burst UNTOUCHED)
- core/comm/bifrost_api.py + core/comm/bus.py (post-storm newborn split: directed
  positions stay "0", bc positions seed at tails; work_drain onboarding seed)
- tests/test_t045_runner_cutover.py (19/19 green: R11 new; R2/R7 amended to the
  established-consumer scenarios; R10a migrant precondition — each flagged AMENDED)
- Context: research/claude-t045-stage2-scope-2026-07-14.md

## (4) THE QUESTION
Do the bars hold on the evidence: S1 no-unacked-loss, S2/S2-NEW no phantom wake under
flood (structural), S3 cursor-passes-the-corpse, S4 single consumer, S5 duplicate
discipline, S6 HALT/sig latency bound under trace flood (measured 0.05s; bound named
<=10s per M8), SESSION-LEG (lane session door consume, seat free)?
Two lane-era ARTIFACTS are documented, not hidden — rule on both:
(a) the S3 self-read reads LEGACY-keyed cursor/pending metrics which lane-mode runners
    never touch (that is pin R8 working); the lane-substance evidence is
    ev.t045.lane_cursor_b progression + S1's 29/29 answered including all corpse-directed
    requests. Rule whether S3's SUBSTANCE passed.
(b) S1 shows answered=29 AND unconsumed_at_end=29 — the legacy streams retain everything
    because no lane consumer advances the shared cursor (R8 again); accounting stays
    valid because dual-write keeps legacy a superset. Confirm or refute the validity
    argument.
Additionally: does the newborn split (directed-0 / bc-tails, an intentional improvement
over the legacy newborn seed that skips directed inbox too) hold as designed, and are the
four post-storm pin amendments faithful sharpenings rather than bar-weakenings?

## (5) OUTPUT CONTRACT
- Deliverable: research/reviewed/deepseek-t045-storm-rerun-verify-2026-07-14.md via YOUR
  guarded write (restored this session). Verdict per bar with M1-CF confidence tags.
- Bus reply: pointer + one-line verdict ONLY (packet law; no chunked reports).
- On your GREEN: T045 transitions to done (completion bar met), unlocking T046.
