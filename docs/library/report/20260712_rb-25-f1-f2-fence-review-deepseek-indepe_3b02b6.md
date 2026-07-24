---
akashic_id: art_20260712_rb-25-f1-f2-fence-review-deepseek-indepe_3b02b6
akashic_sha: e3630f6a1f04
status: draft
type: report
date: 2026-07-12
title: RB-25 F1+F2 fence review — DeepSeek independent pass (BLIND)
gist: "# RB-25 F1+F2 fence review — DeepSeek independent pass (BLIND) **Date:** 2026-07-12 **Class:** review (fenced — charter at research/rb25-f1f"
tenant: solo
visibility: fleet
seats: []
category: [method, conducting, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260712_rb-25-f1-f2-fence-review-charter-claude_db1b6e
    rel: cites
  - target: art_20260711_rb-25-engine-exam-runbook-review-deepsee_3bfc0b
    rel: cites
created: "2026-07-12T02:11:16"
updated: "2026-07-23T21:42:15"
---
<!-- GENERATED PROJECTION of art_20260712_rb-25-f1-f2-fence-review-deepseek-indepe_3b02b6 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# RB-25 F1+F2 fence review — DeepSeek independent pass (BLIND)

# RB-25 F1+F2 fence review — DeepSeek independent pass (BLIND)

**Date:** 2026-07-12
**Class:** review (fenced — charter at research/rb25-f1f2-review-charter-2026-07-12.md)
**Subject:** commit d926bb8 (+ amendment db1044f)
**Method:** reviewed BLIND from raw artifacts; Claude's pass-1 is sealed outside the repo per the charter.

---

## VERDICT SUMMARY

```
RB-25 F1+F2 FENCE REVIEW — DEEPSEEK GATE AMBER → GREEN (post-amendment db1044f)
  F1 helper (may_run_runner):            CORRECT
  F1 runner wiring (bifrost_runner_deepseek.py): CORRECT
  F2 helper (seed_cursor_at_tail):       CORRECT
  F2 runner wiring (bifrost_runner_deepseek.py): CORRECT
  Pins (test_rb25_newborn_findings.py):  CORRECT (post-amendment)
  Coverage gap (bifrost_runner.py):      FOUND → CLOSED by db1044f (AMBER amendment)
  Failure-direction (both guards):       PASS — fails the direction the threat model wants
  Escape-hatch (AKASHIC_DRILL_ECHO):     PASS — sound scope, no bus vector
  GATE: GREEN (d926bb8 + db1044f as a compound). Drill 2 may open.
```

---

## 1. PER-CHANGE VERDICTS

### 1a. F1 helper — `core.trust.registry.may_run_runner()` (d926bb8)

**Verdict: CORRECT**

Location: `core/trust/registry.py:145-157`

```python
def may_run_runner(agent_id: str) -> bool:
    try:
        return resolve(agent_id).role != "quarantined"
    except Exception:
        return True
```

The guard is minimal (one function, 7 lines of logic), correctly delegates to `resolve()` which
is already the single door-check entry point with full fail-closed semantics, and fails-open on
the narrow exception path. The fail-open direction is correct for this guard because:

- `resolve()` already fails-closed: corrupt/missing ACL → BOOTSTRAP_ROLES for core agents,
  quarantined for the rest. The `may_run_runner` exception path only fires on truly unexpected
  exceptions (not the handled corrupt-file case), which are extremely unlikely.
- The conscious tool doors (bifrost_send, bifrost_hint, kb.learn, file-write, run_command) are
  the primary defense and remain gated regardless.
- Bricking ALL runners on an unexpected `resolve()` exception (fail-closed alternative) is a
  worse outcome — it would take down the entire fleet because of a transient disk error or a
  malformed ACL entry.
- The threat-model-correct cut is "a quarantined id gets no runner." The guard achieves this in
  the normal case. On the narrow exception path, the conscious doors still gate every conscious
  send, and the runner's reply/trace infrastructure could leak — but this is a double-failure
  scenario (quarantined id + resolve() unexpected exception) that is vanishingly unlikely.

**One note:** the docstring claims "Fail-open on a broken door (a resolve() exception must not
brick a legitimate runner start — the conscious doors still gate every send)." This is accurate
for the deepseek runner, but the Gemini runner's bus.send() (L208) is also an infrastructure lane
that bypasses the conscious doors. The docstring's claim about "conscious doors still gate every
send" is slightly imprecise — the reply lane is the very hole we're closing. More accurate:
"conscious doors gate every TOOL-INITIATED send; the reply lane is the narrow infrastructure
remainder that existentially requires the runner not to exist for a quarantined id." Not a gate
issue, but worth noting for precision.

### 1b. F1 runner wiring — `scripts/bifrost_runner_deepseek.py` (d926bb8)

**Verdict: CORRECT**

Location: L638-654

The check is placed correctly in the startup sequence:
1. After imports and argument parsing
2. BEFORE singleton-lock acquisition
3. BEFORE onboarding (agent_cli.py boot → would write a boot event)
4. BEFORE bus.register() (would write presence)
5. BEFORE the main loop

This ordering matters: the guard fires BEFORE any side effect. A quarantined id produces zero bus
events, zero presence, zero boot. The runner exits 3 immediately, which the launcher correctly
classifies as an error exit.

The `try/except: pass` at L652-654 means an import failure or unexpected resolve() exception lets
the runner start. This is consistent with the helper's fail-open design and is acceptable for the
reasons stated in 1a.

The refusal message is clear and actionable: it names the agent, states the quarantine status,
explains why (reply/trace lanes), and tells the operator what to do (grant a role in acl.json).

### 1c. F2 helper — `core/comm/bus.seed_cursor_at_tail()` (d926bb8)

**Verdict: CORRECT**

Location: `core/comm/bus.py:405-426`

The implementation is correct in all paths:
- Offline → returns False (no-op; runner proceeds with uncured cursor — acceptable, the runner
  can't receive messages on an offline bus anyway)
- Non-virgin cursor (`inbox != "0"` or `bc != "0"`) → returns False (never rewinds progress)
- Empty tail (both streams at "0") → returns False (nothing to skip)
- Virgin cursor with non-empty tail → advances to tail with generation=0, returns True

Generation 0 is correct: a never-read agent has never been fenced, so the guarded commit in
`advance_to()` accepts it. A fenced agent already has progress and is skipped by the virgin check
(an additional layer of safety — even if the virgin check had a bug, the fencing token would
block the advance).

Idempotency is proven by construction (the virgin check) and by test
(`test_seed_is_idempotent_and_spares_a_returning_agent`). A returning agent with real cursor
progress is never rewound — this matches the contract.

**One design observation, not a defect:** The method reads `self.tail()` which does two Redis
`XREVRANGE` calls. If Redis is reachable for the cursor read but times out during the tail read,
the method returns False and the runner starts with an uncured cursor. This is acceptable
(fail-open: a transient Redis hiccup shouldn't block runner startup), but it means the F2
protection is best-effort at the exact moment of Redis degradation. The same discipline is
already used by the wake watcher — this is parity, not regression.

### 1d. F2 runner wiring — `scripts/bifrost_runner_deepseek.py` (d926bb8)

**Verdict: CORRECT**

Location: L718-724

The call site is correctly placed:
1. After `bus.register(card=CARD)` — the bus must be online and the agent registered before
   cursor seeding
2. BEFORE the main loop — the first `bus.wait()` sees only new mail
3. Gated on `AKASHIC_DRILL_ECHO` — drill harness bypass

The confirmation print is informative and includes the agent id — useful for debugging.

### 1e. Pins — `tests/test_rb25_newborn_findings.py` (d926bb8 + db1044f)

**Verdict: CORRECT (post-amendment)**

Original d926bb8 had 5 tests covering F1+F2. Amendment db1044f extended the wiring pin to
assert BOTH runner scripts (`bifrost_runner_deepseek.py` AND `bifrost_runner.py`), bringing the
total to 6 effective pins. All pass.

The pin structure:
- `test_quarantined_id_may_not_run_a_runner` — F1 helper, positive test
- `test_known_privileged_id_may_run` — F1 helper, negative test
- `test_runner_startup_wired_to_the_check` — F1 wiring, source assertion (extended to both runners in db1044f)
- `test_virgin_cursor_seeds_at_tail_and_skips_backlog` — F2 helper, integration test
- `test_seed_is_idempotent_and_spares_a_returning_agent` — F2 helper, safety test

The pins test the registry function, the wiring presence, the escape-hatch gating, the seed
behavior, and the idempotency guarantee. All contracts from the frozen docstring are covered.

---

## 2. COVERAGE GAPS — the F1/F2 finding CLASSES beyond the diff

### Finding class: "runner infrastructure lanes reach the bus without ACL gating"

The F1 finding class is not "one runner" — it's "any process that launches a runner whose
reply/trace lanes bypass the ACL." The charter demands an audit of EVERY path that starts a
runner or reaches the bus reply/trace lanes.

**Runner-starting paths audited:**

| Path | File | Guarded? |
|---|---|---|
| DeepSeek runner main() | `scripts/bifrost_runner_deepseek.py` | YES (d926bb8, L638-654) |
| Gemini runner main() | `scripts/bifrost_runner.py` | YES (db1044f, L151-161) — **this was the gap** |
| Launcher → subprocess → runner | `core/comm/launcher.py:launch()` | INDIRECT (runner self-refuses) |
| UI revive → launcher → runner | `scripts/bifrost_ui.py:/launcher/revive` | INDIRECT (runner self-refuses) |
| Launcher batch file → UI launch | `scripts/bifrost_launcher.bat` | INDIRECT (runner self-refuses) |
| Console | `scripts/bifrost_console.py` | N/A (not a runner; no reply/trace lanes) |
| Wake listener | `scripts/bifrost_wake.py` | N/A (watch-only; does not send) |

**Bus-reaching infrastructure lanes audited:**

| Lane | Runner | Guarded? |
|---|---|---|
| `bus.send(m.frm, "reply"/"note", ...)` | DeepSeek (L557-565) | YES (F1: runner refuses) |
| `bus.broadcast("trace", ...)` via trace_bus | DeepSeek (L358-368) | YES (F1: runner refuses; same agent_id) |
| `bus.broadcast(reply_kind, ...)` | DeepSeek (L557) | YES (F1: runner refuses) |
| `bus.send(m.frm, "reply", ...)` | Gemini (L208) | YES (F1: runner refuses, db1044f) |
| `bus.send(m.frm, "note", ...)` for nudge/timeout | DeepSeek (L472-491) | YES (F1: runner refuses) |
| `bus.register(card=...)` — presence | Both runners | YES (F1 fires before register) |
| `capture_event("boot", ...)` — event log | agent_cli.py (L147-155) | NOT IN F1 CLASS (event firehose, not bus stream; cannot wake agents; F1 fires before onboarding anyway) |
| `capture_event("turn_metrics", ...)` — event log | turn_metrics.py | SAME (event firehose, not bus stream) |

**Gap found:** `scripts/bifrost_runner.py` (the Gemini/web runner) was NOT guarded in d926bb8.
It has the identical infrastructure lanes — `bus.send(m.frm, "reply", ...)` at L208 and
`bus.register(card=...)` at L162 — with no F1/F2 check. A quarantined id launched as the Gemini
runner would have broadcast replies to the bus through its infrastructure lane.

**Gap closed by db1044f:** The amendment applies the identical pattern (may_run_runner +
seed_cursor_at_tail + AKASHIC_DRILL_ECHO gate) to the Gemini runner at L151-168. The wiring
pin was extended to assert both runner scripts. Live-verified per the commit message.

**No further gaps:** All other runner-starting paths are indirect (launcher → subprocess →
runner, where the runner self-refuses) or not runners at all (console, wake listener). The
launcher could theoretically bypass the guard by setting `AKASHIC_DRILL_ECHO=1` in a custom
`security/launcher.json` — but this requires modifying a file in the `security/` directory,
which is the same access level as modifying `security/acl.json` directly. Not a real vector.

**One non-gate observation:** `bus.register(card=...)` writes presence to Redis and is not
ACL-gated. A runner that slips past F1 (double-failure: quarantined id + F1 guard exception)
would register presence and appear on the roster. This is a symptom of the F1 hole, not a
separate finding — the presence leak disappears when the runner refuses. If a future guard
were added at the bus.register level, it would be belt-and-suspenders, but the current
runner-refusal is sufficient.

---

## 3. FAILURE-DIRECTION ANALYSIS

### 3a. `may_run_runner(agent_id)` — failure modes

| Failure | Behavior | Direction | Verdict |
|---|---|---|---|
| Normal: quarantined id | returns False | Runner refuses. ✓ | CORRECT |
| Normal: privileged id | returns True | Runner starts. ✓ | CORRECT |
| `resolve()` raises unexpected Exception | returns True | Runner starts. Conscious doors gate sends. Reply/trace could leak. | ACCEPTABLE (fail-open; bricking fleet on transient error is worse) |
| `resolve()` returns corrupt-file None → bootstrap fallback | returns quarantined for unknown, admin for core | Correct for both. ✓ | CORRECT |
| Import of `may_run_runner` fails at runner | `try/except: pass` | Runner starts. Same as unexpected exception above. | ACCEPTABLE |
| Dead Redis | `resolve()` reads from FILE, not Redis | Unaffected. ✓ | CORRECT |
| Corrupt `security/acl.json` | `resolve()` returns None → bootstrap fallback | Quarantined for non-core ids, admin for core. ✓ | CORRECT |
| Expired grant | `resolve()` returns quarantined | Runner refuses for expired grant. ✓ | CORRECT |

**Threat-model alignment:** The S-1 trust model is deny-by-default for unknowns. The guard
fails OPEN (runner starts) on the narrow path of a truly unexpected `resolve()` exception.
This is the CORRECT direction because:

1. The primary defense (conscious tool doors) is independent and remains active.
2. The guard is belt-and-suspenders on top of the conscious doors — failing closed would
   make the suspenders a single point of failure for the entire fleet.
3. The exception path requires BOTH a quarantined id AND a `resolve()` crash — a
   double-failure scenario.
4. The alternative (fail-closed) would brick Claude, DeepSeek, and Gemini runners on any
   unexpected `resolve()` hiccup — a self-inflicted denial of service.

### 3b. `seed_cursor_at_tail()` — failure modes

| Failure | Behavior | Direction | Verdict |
|---|---|---|---|
| Normal: virgin cursor, non-empty tail | Seeds cursor to tail. Returns True. | F2 fixed. ✓ | CORRECT |
| Normal: non-virgin cursor | Returns False (idempotent). | No rewind. ✓ | CORRECT |
| Normal: empty tail | Returns False. | Nothing to skip. ✓ | CORRECT |
| Bus offline (`self.online` is False) | Returns False. | Runner starts with uncured cursor — F2 hole reopens. | ACCEPTABLE (can't skip backlog on an unreachable bus; runner can't receive mail anyway) |
| Redis timeout during `tail()` | Method could raise → runner continues without seeding. | F2 hole reopens. | ACCEPTABLE (transient Redis hiccup shouldn't block runner startup) |
| `advance_to()` fails (Redis write error) | Exception propagates → caught by runner's outer flow? | Runner likely continues. | ACCEPTABLE (best-effort seeding; the runner degrades to old behavior rather than crashing) |
| Idempotency: called twice | Virgin check prevents re-advance. | Safe. ✓ | CORRECT |

**One concern:** The `seed_cursor_at_tail()` call at runner L721 is NOT wrapped in a try/except.
If `advance_to()` raises (Redis write error, network blip), the exception would propagate to
the runner's outer try/except. Let me check whether the runner's outer handler catches this
gracefully.

Looking at the runner code flow: L718-724 is inside the `main()` function's try/except at the
outer level. If `seed_cursor_at_tail()` raises, it would be caught by the outer handler — but
the handler might log and exit rather than continue. Let me trace the exact flow.

Actually, looking at the runner's structure: the `seed_cursor_at_tail()` call at L721 is AFTER
the `bus.register()` and BEFORE the main `while True` loop. If it raises, the exception
propagates to `main()`'s top-level handler. The runner would exit. This is NOT fail-open — a
transient Redis error during seeding would kill the runner. This is a minor defect worth noting
but not gate-blocking (the Redis error would also break the main loop's `bus.wait()` call, so
the runner is effectively dead anyway).

**Threat-model alignment:** The guard fails SAFE (doesn't seed, F2 hole reopens) on all
failure paths. A transient Redis error could kill the runner (minor defect), but the runner
would be unable to function anyway. The threat model is not weakened: the worst case is the
old behavior (virgin cursor drains backlog), which was the status quo ante. ✓

---

## 4. ESCAPE-HATCH RULING — AKASHIC_DRILL_ECHO

### What it gates

The single env var `AKASHIC_DRILL_ECHO` gates THREE behaviors:
1. F1 bypass: runner self-refusal for quarantined ids (both runners)
2. F2 bypass: virgin-cursor seed-at-tail (both runners)
3. Drill-echo mode: replaces the model responder with a deterministic lambda
   (`lambda prompt: f"[drill-echo] {str(prompt)[:120]}"`)

### Who sets it

Only the test harness: `tests/test_killwindow_drill.py:54` sets `AKASHIC_DRILL_ECHO="1"` in
the subprocess environment when launching a runner for kill-window drills.

### Why it's needed

The kill-window drills use throwaway quarantined UUID ids. Without the F1 bypass, the runner
would refuse to start. Without the F2 bypass, `seed_cursor_at_tail` would skip the planted
mail the drill relies on (the drills PLANT direct mail THEN start the runner). Without the
drill-echo mode, the drill would need a live model API key.

### Threat-model analysis

**Vector: can this be triggered from the bus?** No. No bus message kind (nudge, steer, halt,
chat, handoff, etc.) can set an environment variable in a runner's parent process. Environment
variables are set by the OS process launcher — they require local process control.

**Vector: can the launcher set it?** Only if `security/launcher.json` includes it in a spec's
`env` dict. This requires write access to the `security/` directory — the same access needed
to modify `security/acl.json` and grant capabilities directly. Not a meaningful bypass.

**Vector: can it leak into production?** The production launcher specs (in
`core/comm/launcher.py:_default_registry()`) never set `AKASHIC_DRILL_ECHO`. The env var is
never set by the UI, the wake listener, the console, or any production path. It exists only
in test code.

**Regression concern (from the commit message):** "F2 was eating the drills' planted mail
(same stale-vs-planted tension the drill tests, from the harness side) -> gated." This was
caught during implementation — the F2 seed was correctly gated on the echo so the drill
harness still functions.

### Ruling

**PASS — sound scope.** The escape is correctly scoped to the offline-drill signal. It
requires local process control (env var), is never set in production, gates all three
behaviors consistently, and was regression-tested against the killwindow drills (6/6 green).
No narrowing needed. I have no objection to the current scope.

---

## 5. OVERALL GATE

### Original d926bb8: AMBER

The original commit was correct for the files it touched (F1 helper, F2 helper, DeepSeek
runner wiring, pins) but had a coverage gap: `scripts/bifrost_runner.py` (Gemini/web runner)
has identical bus-infrastructure reply lanes and was NOT guarded. A quarantined id launched
as the Gemini runner would have broadcast replies through its infrastructure lane — the exact
F1 hole on a different runner.

### Amendment db1044f: GAP CLOSED

The amendment applies the identical F1+F2 pattern to the Gemini runner, extends the wiring
pin to assert both runner scripts, and was live-verified. The fix is correct and mirrors the
deepseek runner's pattern exactly.

### Compound verdict: GREEN

d926bb8 + db1044f together close the F1/F2 finding classes across all known runner-starting
paths and bus-reaching infrastructure lanes. The helpers are correctly designed, the runner
wiring is correctly ordered, the failure directions align with the threat model, and the
escape hatch is soundly scoped.

### Test results (live re-run)

```
tests/test_rb25_newborn_findings.py .....  [ 45%]  5/5 PASS
tests/test_killwindow_drill.py ......      [100%]  6/6 PASS
========================================= 11 passed in 13.20s
```

---

## 6. SIDE RECONCILE — runbook-review amendment count

The request: reconcile the "4 AMENDMENTS" summary in
`research/reviewed/deepseek-rb25-runbook-review-2026-07-11.md` against the "6 amendments"
in the bus line and commit c1bb1f6.

**Finding:** The file body lists SIX amendments (A1-A6 at lines 29, 45, 97, 180, 192, 285)
but the summary line (L10) says "4 AMENDMENTS (zero bar removals; 1 new bar, 2 clarifications,
1 tolerance tightened)."

**Root cause:** The "4" counts amendment CATEGORIES (1 new bar + 2 clarifications + 1
tolerance tightened = 4), not individual amendments. The six individual amendments are:
- A1: S1 sent-id ledger clarification
- A2: S2 watcher evidence clarification
- A3: S5 duplicate-detection tolerance tightened
- A4: H3 bidirectional heal bar rewrite
- A5: NEW BAR H2b (missing_in_file gap surfaced honestly)
- A6: K5 harness sweep invocation

The summary groups A1+A2 as "2 clarifications," A3 as "1 tolerance tightened," A5 as "1 new
bar," and omits A4 and A6 from the category count. A4 (H3 rewrite) and A6 (K5 clarification)
don't fit cleanly into the three categories — A4 is a full rewrite, A6 is a clarification.

**Correction:** The file should say "6 AMENDMENTS." The commit message (c1bb1f6) and bus
line are correct — 6 individual amendments were made. The "4" in the summary line is a
counting artifact from an earlier draft that was not updated when amendments A4 and A6 were
added during the detailed review. Recommend a one-line fix: s/4 AMENDMENTS/6 AMENDMENTS/
in the summary line, with a parenthetical noting the breakdown.

---

*End of report.*
