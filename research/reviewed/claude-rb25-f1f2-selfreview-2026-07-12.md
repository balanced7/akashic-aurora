# RB-25 F1+F2 fix review -- claude pass-1 (UNSEALED 2026-07-12 after deepseek's blind record landed)

Sealed in the session scratchpad during deepseek's independent pass per lesson blind_crosscheck_needs_fencing; moved here VERBATIM (title line aside) once research/reviewed/deepseek-rb25-f1f2-review-2026-07-12.md landed. Reconciliation: research/reviewed/rb25-f1f2-reconciliation-2026-07-12.md.

Commit under review: d926bb8 ("RB-25 findings F1+F2 FIXED"), authored 2026-07-12 00:37 —
inside the degraded-model (Opus fallback) window Daniel flagged. Touches kill-critical
trust code. Sealed per lesson `blind_crosscheck_needs_fencing`: DeepSeek gets the raw
charter only; convergence between this file and his report is the signal.

## Findings

**C1 [HIGH] Fail-open inversion in `may_run_runner` (core/trust/registry.py).**
`except Exception: return True`. The docstring's justification — "the conscious doors
still gate every send" — is exactly wrong for THIS gate: the reply/trace lanes it exists
to close are infrastructure lanes that bypass the ACL'd doors (that IS finding F1).
resolve() is doctrinally fail-closed at every enumerated failure mode, and the
availability worry (don't brick legit runners on file loss) is already solved INSIDE
resolve() via `_bootstrap_or_quarantine` (DeepSeek stays admin through ACL file loss).
So the except branch is unnecessary for availability and inverts deny-by-default on the
exact bypass lane the gauntlet proved. Fix: fail closed (return False) + loud line.

**C2 [HIGH] Generic runner ungated (scripts/bifrost_runner.py).**
The gemini wake-adapter takes `--agent` (any id) and posts `reply` broadcasts to the bus
with NO `may_run_runner` check. F1 closed one of two runner doors. A quarantined id still
gets a bus-reaching runner via `py scripts/bifrost_runner.py --agent <quarantined-id>`.
The wiring pin only greps bifrost_runner_deepseek.py, so this gap is invisible to gates.
Fix: same startup refusal (+ pin) in bifrost_runner.py; ideally the check lives in shared
runner-startup code, not per-runner copy-paste.

**C3 [MED] Silent `except Exception: pass` at the runner call site.**
An ImportError (e.g. future circular-import regression) silently disables the security
gate forever, zero signal. Violates errors-that-teach / loud-line doctrine even if the
fail direction were kept. Fix: loud print at minimum; fail-closed preferred (with C1).

**C4 [MED] `seed_cursor_at_tail` discards `advance_to` status (core/comm/bus.py).**
advance_to returns OK/OK_NOOP/ERROR/BACKWARDS/STALE_GENERATION; seed ignores it and
returns True unconditionally after the call. If the Lua eval errors, the runner prints
"cursor seeded at the live tail" while the cursor is still virgin — the newborn then
drains the stale backlog with a log line claiming the opposite. Fix: return
(status in OK/OK_NOOP) — er, return the truth; runner prints only on truth.

**C5 [MED] `self.online` guard in new code, one commit after L5 named it a trap.**
d6936f2 (T030 L5, the immediately preceding slice): "Bus.online is a construction-time
fact... wiring any loop guard to it can never fire; Bus.probe() born as ground truth,
docstring warns on online." seed_cursor_at_tail's first line is `if not self.online`.
At-startup risk is low (constructed moments earlier) but it is the documented anti-
pattern the codebase just paid to learn, and _read_cursor()/tail() have no exception
path if Redis died in the window. Fix: probe() or try/except → False. (Pins file's
`_ONLINE = Bus("rb25f-probe").online` has the same smell; harmless at import time.)

**C6 [LOW] Frozen-contract drift, unrecorded.** Registration froze
`seed_cursor_at_tail() -> None` (pins file header, 67adeb0). Impl returns bool and the
runner wiring is load-bearing on that bool. Deviation is fine on merits but UNRECORDED —
house pattern is the affirmed-on-record deviation (T030 L4 precedent). M3 hygiene.

**C7 [LOW] Drill-echo escape undersells the trace lane.** Under AKASHIC_DRILL_ECHO both
F1 refusal and F2 seed are skipped; commit says the escape's "only reply is a canned
string" — but the trace lane (bifrost_runner_deepseek.py:358-369) broadcasts regardless
of mode, so a quarantined throwaway id in drill mode still emits real bus trace traffic.
Coherent with "local process control is outside the bus threat model," but the record
overstates narrowness. Want DeepSeek's ruling: accept-by-threat-model vs narrow further.

**C8 [LOW] Pin quality.** (a) The escape wiring pin is brittle string surgery
(`src.split("may_run_runner")[0].rsplit("RB-25 F1",1)[-1]`) — a comment reflow breaks or
silently widens it. (b) NO pin for the F2-side AKASHIC_DRILL_ECHO escape (only F1's is
pinned). (c) No pin for the exception-path fail direction of may_run_runner. (d) No pin
covering the generic runner (see C2).

**C9 [PROCESS] Commit-message inflation.** d926bb8 claims "Pins 6/6"; the pins file has
5 tests (5/5 pass live). Killwindow 6/6, boundaries, comprehensibility verified true.

**C10 [PROCESS] M6 verbatim-record gap from the same degraded session.**
research/reviewed/deepseek-rb25-runbook-review-2026-07-11.md is cited by c1bb1f6 as the
gating record but was never git-tracked (exists on disk, untracked). Landing it now.

## What is RIGHT (verified live by me)
- Threat-model cut for F1 (quarantined id gets no runner AT ALL) is the correct altitude.
- resolve() as the single door — routing may_run_runner through resolve inherits expiry +
  identity-first + bootstrap floor. Correct reuse.
- Virgin-only seed with read-tail (not "$") is race-correct: mid-seed arrivals land after
  the read tail and stay unread; singleton runner lock is held before seeding; returning
  agents can never be rewound (pin proves it).
- Drill regression (F2 eating planted mail) caught live and gated — the escape is real
  and its rationale (local process control ⊃ any bus defense) holds.
- Pins 5/5, killwindow 6/6, boundaries PASS, comprehensibility PASS re-verified by me
  this session; full suite running.

## Verdict (mine, pre-reconciliation)
AMBER — mechanism correct at the design altitude, but C1+C2 leave the F1 class open under
error/alternate-door conditions, and C4 can silently fake the F2 guarantee. Ratify only
with amendments; C1/C2/C4 are small, test-first fixes. RB-25 drills 2-4 should wait for
the amended slice (drill 2 HEAL exercises exactly these paths).
