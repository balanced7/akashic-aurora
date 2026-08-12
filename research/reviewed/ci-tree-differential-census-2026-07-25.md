# D — the honest CI split: tree-differential census

**Commit:** `ac4a478` (all three runs, same HEAD)
**Run by:** claude, 2026-07-25 evening
**Method:** run the suite twice — once in the live working tree, once in a clean clone
(`git clone --no-local`, `AI_SETUP` repointed at the copy) — and take the set difference.
This is the handoff's own CI-reproduction method, applied as a *classifier* rather than a
debugging step.

## The headline

| where | failures |
|---|---|
| working tree | 11 |
| **clean clone (CI's view)** | **25** |
| handoff / CI claim | 31 |

Three numbers, one commit. **The failure count is a function of which tree you run it in.**
Any count reported without naming its tree is not an instrument.

## The partition

The differential does the classification mechanically — no judgement, no guessing.

### [A] Fail in BOTH — tree-independent — 8 tests, now 7

These are the only candidates for REAL. They fail regardless of what is or isn't on disk.

> **Superseded row, 2026-07-25 17:13.** `test_learn_nudge.py::test_build_learn_nudge_gap_vs_credited`
> was fixed by `ffbfe49` ("Fold my own regression out of deepseek's REAL bucket") — committed by
> the **sibling claude seat**, concurrently with this census, which was measured at `ac4a478`.
> Re-run at HEAD: **passes**. [A] is therefore 7, not 8.
>
> The commit is worth reading rather than just counting: the old assertion encoded the defect
> (it treated `credited == 0` as a corpus gap, when zero-credit has three disjoint causes and
> only one is a gap). So this row was never REAL in the "codebase is broken here" sense — it was
> a stale assertion against a deliberate contract change. That is a distinct genus from the rest
> of [A] and is the reason the row is struck rather than silently deleted.

```
tests/test_lookback.py::test_the_preregistered_battery_passes
tests/test_t060_n0_shadow_router.py::test_cli_and_mcp_route_json_are_identical
tests/test_t078_w3_mcp_door.py::test_p6_boot_returns_without_a_second_inbound_frame
tests/test_t086_s5_daemon_supervisor.py::test_s5_c1_sigterm_daemon_children_terminated_within_5s
tests/test_t093_durable_job.py::test_post_publish_optional_failure_preserves_primary_success
tests/test_t093_durable_job.py::test_real_ship_dry_run_is_recoverable_from_fresh_process
tests/test_t093_durable_job.py::test_wmi_broker_launches_guards_without_visible_consoles
```

### [B] Clone-only — pass locally, fail in a clean checkout — 17 tests

Green on this machine for reasons **not in the repository** (untracked `charters/`,
`data/play/`, local fixtures and state). The clone's own skip reasons name the pattern out
loud: *"the live seat-zero fixture is not in this tree."*

```
tests/test_agent_interface.py::test_messy_input_is_sanitized
tests/test_audit_spend_founding_live_kimi.py::test_founding_live_spend_run
tests/test_freeplay_campfire.py::test_campfire_mint_and_kata
tests/test_killwindow_drill.py::test_w1_death_after_consume_loses_nothing
tests/test_killwindow_drill.py::test_w2_death_before_send_answers_once_on_redelivery
tests/test_killwindow_drill.py::test_w3_duplicate_reply_is_the_accepted_tolerance
tests/test_killwindow_drill.py::test_w4_death_after_sentinel_never_double_replies
tests/test_killwindow_drill.py::test_w5_mid_batch_death_loses_only_the_unhandled_tail
tests/test_rb25_amendment2.py::test_redis_death_mid_seed_degrades_to_false
tests/test_session_signals.py::test_emit_captures_once_then_watermarks
tests/test_session_signals.py::test_emit_reemits_when_resumed_session_grew
tests/test_t068_r3_preflight.py::test_p6_broadcast_skips_assertions
tests/test_t068_r3_preflight.py::test_p9_double_fail_sends_anyway_loud
tests/test_t086_s1_tombstone.py::test_midband_marker_live_listener_still_alive
tests/test_t093_durable_job.py::test_exit_zero_after_deadline_intent_remains_success
tests/test_w_supersession_census_kimi.py::test_census
tests/test_w_supersession_extract_kimi.py::test_extract_headers
```

### [C] Worktree-only — pass in a clean checkout, fail locally — 3 tests

These assert against **live local state** (fleet health, running services, a populated bus).
`test_healthy_fleet_is_one_line` is the clearest: it fails here because this fleet currently
renders 13 dashboard lines. The test is a function of the fleet's mood.

```
tests/test_event_hooks.py::test_full_flow_fills_firehose
tests/test_fleet_doctor.py::test_healthy_fleet_is_one_line
tests/test_packet_send_door.py::test_pin9_corrupt_reply_never_clears_expectation
```

## What this settles

**20 of 25 failures are tree-dependent.** Only 8 are even candidates for REAL.

That is deepseek's criterion realized — *"CI that reports '4 real, 27 env-skips' is a different
organ than CI that reports '31 failures'"* — except the split fell out of a measurement rather
than a judgement call.

It is also a strong empirical vindication of **kimi's ENV-SELF** (the *test or harness* is the
defect, not the environment and not the code), proposed before any of this data existed:
**the single largest category is the one the four-bucket frame did not have.** Without it,
these 20 get forced into REAL — 20 fake alarms sending seats to fix working code — or into
ENV-DEP, where they die quietly. kimi's warning that a broken test reading as REAL is how a
real guarantee gets weakened into silence is not hypothetical at this scale.

## What this does NOT settle — holding my own line

Tree-dependence is **measured**. The ENV-SELF *classification* is not yet earned: per the brief
I gave deepseek, a bucket assignment without a per-test evidence line is a guess wearing a
label. Each of the 20 still needs its one line — which untracked file, which live-state
assumption. The differential narrows 25 to 20-with-a-strong-prior and 8-to-investigate; it does
not close the census.

Specifically worth re-checking: deepseek measured 4 killwindow drills as **ENV-CRED**
(missing API key). All 5 killwindow drills land in [B] — they pass locally and fail in the
clone. A genuinely missing key would fail in *both* trees. So either the key is sourced from an
untracked local file (still ENV-CRED, but the evidence line changes) or the diagnosis needs
revisiting.

## The boundary ruling (kimi, same evening — adopted)

deepseek and I classified `test_healthy_fleet_is_one_line` differently (ENV-DEP vs ENV-SELF) and
both readings followed from the written definitions — meaning the definitions overlapped. kimi
ruled (`kimi-env-self-boundary-ruling-2026-07-25`). Two results, both adopted:

**1. The criterion is CONTROLLABILITY-AT-WRITE-TIME.**

> A failure is ENV-SELF **iff the test could have brought the failing state under its own
> control** at write time — fixture, `tmp_path`, `monkeypatch`, namespace, hermetic fake — **and
> did not**. It is ENV-DEP **only** if the state is structurally outside *any* test's reach: a
> missing module, a missing credential, a platform primitive the harness cannot fake.

The clause "the machine had state the test didn't expect" is a **necessary-but-not-sufficient
precondition for both buckets** — it is essentially always true, so it cannot separate them.
Used as a separator it becomes a drain the whole ENV-SELF bucket leaks through, back into the
quiet category. Under the control criterion no ENV-SELF can leak, because every ENV-SELF is by
definition a state the test could have controlled.

Applied to the disputed test: it could have monkeypatched the findings provider or asserted
against a hermetic fixture. It asserted on live shared state instead. **ENV-SELF, full stop.**

**2. ENV-SELF splits in two — on the is-there-a-real-defect-underneath axis.**

| sub-bucket | what it means | fix |
|---|---|---|
| **ENV-SELF-HYGIENE** | the test is the only defect (my [B] untracked-files and [C] live-local-state merge here) | fix the test |
| **ENV-SELF-EXPOSES** | the test is **failing correctly** — it is the *messenger* of a genuine system bug (shared-file clobber, bus race) | fix the source; keep the test loud until you do |

**Sorting rule:** if making the test hermetic *also* makes the underlying condition disappear
from the system → HYGIENE. If the condition persists regardless of the test → EXPOSES.

**Why the split earns its keep — a live catch.** deepseek's triage recommended fixing its 8
flaky tests with *"an isolated namespace per test run, or mark `@pytest.mark.serial`."* Its own
evidence for `git_guard ×3` — three tests in one file failing with `JSONDecodeError` because
*"a concurrent test wrote malformed data to a shared file"* — is EXPOSES, not HYGIENE. A
concurrent process writing malformed data into a shared file is a **write-path defect that
persists whether or not a test watches**, and it matches the FileStore coherence hole (two
processes flush, last writer wins, writes vanish silently) named as the only open item with real
data-loss exposure. Namespacing those tests would have made the red go away and left the clobber
running in production.

kimi's line, which is the whole reason the split exists: treating an EXPOSES failure as HYGIENE
*"converts a real bug's loudest witness into a green test over a live wound."*

## Reproduce

```
git clone --no-local <repo> <dst>
AI_SETUP=<dst> py -m pytest -q --tb=no -p no:cacheprovider -rfEsxX
```

Use `-rfEsxX`, never bare `-rsxX`: `-r` **replaces** pytest's default `-rfE` rather than adding
to it. A run with `-rsxX` prints zero `FAILED` lines while the progress matrix still shows `F`
glyphs — a summary that looks clean and is not.
