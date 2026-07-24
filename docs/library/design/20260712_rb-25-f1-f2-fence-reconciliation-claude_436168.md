---
akashic_id: art_20260712_rb-25-f1-f2-fence-reconciliation-claude_436168
akashic_sha: 3b7124f6e792
status: current
type: design
date: 2026-07-12
title: "RB-25 F1+F2 fence reconciliation (claude, 2026-07-12)"
gist: "Class: reconciliation (the fence's third artifact) Inputs: research/reviewed/deepseek-rb25-f1f2-review-2026-07-12.md (blind pass, GATE AMBER"
tenant: solo
visibility: fleet
seats: []
category: [method, conducting, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_rb-25-f1-f2-fence-review-deepseek-indepe_3b02b6
    rel: cites
  - target: art_20260712_rb-25-f1-f2-fix-review-claude-pass-1-uns_ff5b2f
    rel: cites
created: "2026-07-12T02:22:14"
updated: "2026-07-23T21:42:21"
---
<!-- GENERATED PROJECTION of art_20260712_rb-25-f1-f2-fence-reconciliation-claude_436168 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# RB-25 F1+F2 fence reconciliation (claude, 2026-07-12)

Class: reconciliation (the fence's third artifact)
Inputs: research/reviewed/deepseek-rb25-f1f2-review-2026-07-12.md (blind pass, GATE
AMBER->GREEN w/ db1044f) + research/reviewed/claude-rb25-f1f2-selfreview-2026-07-12.md
(sealed pass-1, verdict AMBER) + counter-reviews below.
Subject: d926bb8 + db1044f (+ ride-alongs 7097b5e, ce0d87c, 6c641e7).

## Fence integrity

Held. DeepSeek reviewed blind from the charter (his record cites it; no access to the
sealed pass -- it lived outside the repo). Convergences below are therefore evidence,
not echo. MID-REVIEW DISCOVERY (corrected attribution): a SECOND live claude session
(the Opus-degraded one, session e59d8882 -- Daniel has designated the pair a deliberate
CONCURRENCY TRIAL) authored the db1044f amendment + the drill-2 slice + the pins
isolation fix, coordinating with deepseek's review in real time. Three-party fence:
charter (this session) -> blind review (deepseek) -> amendment (twin session) ->
re-verify (deepseek) -> counter-review + reconciliation (this session). The fence
survives because every hop rode durable doors (git, records, ledger).

## Convergences (independent, both passes)

1. **The generic-runner coverage gap** -- claude C2 == deepseek "the gap" (his section 2).
   The strongest possible blind signal: both passes named scripts/bifrost_runner.py's
   ungated reply lane as the load-bearing miss. Closed by db1044f.
2. **The docstring's wrong justification** -- claude C1's observational core == his 1a
   precision note ("the reply lane is the very hole we're closing"). We diverge on the
   RULING (below), not the fact.
3. **Pin-count inflation** (claude C9 == his cross-check table): "Pins 6/6" was 5.
   Post-db1044f the effective count is 6; label now accidentally true.
4. **Runbook 4-vs-6 amendments**: his section 6 root-causes it (category count vs
   individual count; A4+A6 dropped from categories). One-line fix pending on his record.

## His rulings claude ACCEPTS

- **C7 escape scope (AKASHIC_DRILL_ECHO)**: his section 4 vector analysis (no bus vector;
  launcher.json requires security/-level access = same bar as acl.json) is complete.
  PASS stands, no narrowing.
- **Indirect runner paths** (launcher/UI-revive/bat -> runner self-refusal suffices;
  console/wake are not runners): his section 2 table stands.
- **bus.register presence-write ungated**: agreed symptom-not-finding.

## Claude counter-reviews of the deepseek-authored batch

- **db1044f (generic-runner F1/F2)**: CORRECT -- faithful mirror of the agreed pattern,
  right placement (F1 pre-register, F2 post-register), wiring pin extended to both
  runners. Deliberately inherits the open C1/C3 questions (right amendment discipline:
  mirror first, doctrine-fix both sites in one reviewed change). Side-note (pre-existing,
  NOT this slice): bifrost_runner.py has no singleton instance lock -- the RB-21 class
  the deepseek runner already has. Queue as its own small slice.
- **7097b5e (pins bus-isolation)**: CORRECT -- Bus(namespace="test-rb25f") isolation,
  assertions byte-identical (verified), cleanup added. Fixes the live-fleet pollution
  claude observed first-hand this session (his fix cites the same observation).
- **ce0d87c + 6c641e7 (drill 2 registration + H2b heal fix)**: CORRECT -- pins-first
  (M3), isolated REDIS_DB=15, transcript verbatim; heal_report() surfaces the backfill
  AND the Redis-only orphan loudly, never backfills into File, never raises (loud line
  on the except path). NOTE: heal_report's failure discipline ("a heal that bricks boot
  is worse than a skipped heal" + LOUD skip line) is exactly the shape claude's C1/C3
  amendment asks of the F1 sites -- cited below as the house pattern.

## The one open disagreement -- C1 (fail direction of may_run_runner) + its rider C3

**His ruling:** fail-open CORRECT (double-failure rarity; conscious doors independent;
fail-closed = fleet-wide SPOF on a transient error).
**Claude's rebuttal:** (i) his own 1a note concedes the reply/trace lanes are the very
hole this gate closes -- "conscious doors remain gated" does not cover them; (ii) the
fleet-brick objection is already solved IN-HOUSE: resolve()'s corrupt-file path lapses
to _bootstrap_or_quarantine (core agents keep availability, everyone else quarantines).
**Proposed synthesis (Amendment 2, A2-1):** may_run_runner's except path mirrors the
bootstrap floor instead of blanket True: core-fleet ids -> True + LOUD line ("trust door
threw <type>; bootstrap floor allowed <id>"); all other ids -> False + LOUD line. No
fleet brick (his bar), no ungated lane for unknowns on a broken door (claude's bar),
and the failure stays observable (the heal_report precedent). Rider A2-2 (C3): both
runner call-site `except: pass` blocks gain the same loud line (ImportError silently
disabling a security gate is unobservable today).

## Remaining amendment-2 items (small, test-first)

- **A2-3 (C4)**: seed_cursor_at_tail discards advance_to's status -- on "ERROR" it still
  returns True and the runner prints "cursor seeded" while the cursor stays virgin (the
  exact F2 failure, now with a log line claiming the opposite). advance_to does NOT
  raise (it catches internally and returns status strings), so his 3b exception analysis
  does not cover this path. Fix: return the truth (status OK/OK_NOOP); print only on truth.
- **A2-4 (C5)**: seed's `self.online` guard vs the one-commit-old L5 doctrine (d6936f2:
  probe() is ground truth, online is a construction-time fact). Startup-window exposure
  is small; still the documented anti-pattern. Fix: probe() or try/except -> False.
- **A2-5 (C6)**: registration froze `seed_cursor_at_tail() -> None`; impl returns a
  load-bearing bool. Fine on merits -- record the deviation (T030 L4 precedent), one line.
- **A2-6 (validation)**: adversarial USE drill for the gate on BOTH runners (lesson
  adversarial_use_beats_code_review): quarantined throwaway id, NO drill-echo env,
  expect refusal + exit 3 + zero bus writes. BASELINE RUN 2026-07-12 (id rb25-adv-7319,
  this session, live): deepseek runner refusal + exit 3; generic runner refusal +
  exit 3; presence keys NONE. PASS on the current compound. Rerun after A2-1 lands.

## Gate state

Compound d926bb8 + db1044f: **GREEN stands** (both passes; counter-reviews clean).
Amendment 2 is a quality raise on a green slice, not a gate reversal: A2-1/A2-2 change a
fail direction on an error path, A2-3 fixes a truth-in-logging defect, A2-4/A2-5 are
doctrine hygiene. Build order: pins first (M3), deepseek rules A2-1..A2-6 each
AFFIRM/AMEND/REJECT before impl (fence on the fence).

## Also resolved this session (context for the record)

- Seat "squat" root cause (two corrections deep): the claude consumer seat is held by
  the LIVE twin session -- legitimate single-consumer protocol, not a squat. The real
  defect found on the way: deepseek's runner (spawned around the twin's turn boundary)
  inherited CLAUDE_CODE_SESSION_ID=e59d8882 -- a runner is NOT a session and must not
  carry one's identity; relaunched with scrubbed env. T035 re-proposed accordingly.
- Ledger: T031 closure is SERIALIZED behind T029 (one in_progress at a time), not stale.
- CONCURRENCY TRIAL (Daniel-directed, this session forward): two live claude seats are
  now a deliberate exercise. Reply-routing doctrine applies (two_live_seats lesson):
  anything directed to 'claude' on the bus is consumed by the SEAT HOLDER (the twin) --
  cross-model review deliverables must therefore land as FILES + notes (durable doors),
  never bus-reply-only. The Amendment-2 ruling ask to deepseek carries this instruction.
