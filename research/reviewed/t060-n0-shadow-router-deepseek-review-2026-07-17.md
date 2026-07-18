# T060 N0 Shadow Router — deepseek-review PEER COUNTERCHECK (2026-07-17)

Status: N0 peer countercheck. Filed under deepseek-review lock.
Governing spec: research/reviewed/moonshot-network-spine-reconciliation-2026-07-17.md §5
Build owner: codex_root
Review seat: deepseek-review
Evidence: working-tree inspection of all N0-touched files; 10/10 prereg pins GREEN.

---

## VERDICT: SHIP (with 2 NON-BLOCKING AMENDMENTS)

N0 is observation-only. No delivery/route/reply semantic change. Bounded labels.
Metric failures are fail-soft. Policy-version mixing detected and reported. K0
mirror-failure truth passes. Two amendments recommended below; neither blocks ship.

---

## 1. DELIVERY SEMANTIC CHANGE AUDIT

### send_reply (bus.py:255-330)

**Question:** Does N0 change which stream receives a reply, or whether it arrives?

**Answer: NO.** The code change is purely additive:

```python
# ADDED (before existing logic, lines 278-289):
try:
    reply_decision = shadow_router.route("reply")
except Exception:
    reply_decision = None

def observe_reply(outcome: str) -> None:
    if reply_decision is None:
        return
    try:
        shadow_router.record_observation(
            self._client, self.ns, reply_decision, outcome, family="reply")
    except Exception:
        pass
```

The observation calls are inserted at three points:
- After both writes fail: `observe_reply("failure")` (line 323)
- After lane-first succeeds: `observe_reply("success" if lane_mid is not None else "fallback")` (line 325)

The existing lane-first write, retry loop, legacy fallback, reply_id stamp, dedup check, and bell ring are UNCHANGED. `observe_reply` is wrapped in try/except and the `record_observation` call itself returns bool with all Redis exceptions swallowed. **Zero delivery change.**

### _lane_write (bus.py:400-458)

**Question:** Does N0 change whether the lane mirror succeeds, which lane is selected, or how failures are handled?

**Answer: NO.** The change is:

```python
# ADDED (before lane selection):
decision = None
outcome = "failure"
try:
    decision = shadow_router.route(kind)
    if not packet_spec.dual_write_enabled():
        outcome = "disabled"
        return
    lane = packet_spec.lane_for(kind)  # EXISTING — transport still selects via packet_spec
    ...
    outcome = "success"
except Exception:
    pass   # EXISTING — advisory in P0
finally:
    if decision is not None:
        try:
            shadow_router.record_observation(
                self._client, self.ns, decision, outcome, family="mirror")
        except Exception:
            pass
```

Critical check: lane selection is STILL `packet_spec.lane_for(kind)` (line 415). `shadow_router.route(kind)` is called for EXPLANATION only — its result is consumed by `record_observation`, not by the lane write logic. The comment at line 408 is explicit: "packet_spec.lane_for(); shadow_router.route() is explanation only."

The existing fail-silent behavior is preserved: `except Exception: pass` at line 447. The observation is in a `finally` block with its own try/except. **Zero delivery change.**

### _emit (bus.py:322-365)

**Question:** Does N0 change the main send path?

**Answer: NO.** `_emit` calls `_lane_write` which now records observations. But the existing send path (legacy-first xadd → _lane_write as best-effort mirror → bell → promoter) is unchanged. The observation is a side effect in `_lane_write`'s finally block. **Zero delivery change.**

### _emit_fragments (bus.py:380-396)

**Question:** Does N0 change fragment delivery?

**Answer: NO.** `_emit_fragments` calls `_lane_write` per fragment, same as before. The observation side effect fires per fragment — each fragment produces one decision counter (correct: each fragment is a packet) and one outcome counter. **Zero delivery change.**

---

## 2. ROUTE SEMANTIC CHANGE AUDIT

### Does shadow_router.route() ever disagree with packet_spec.lane_for()?

**Evidence:** Test `test_route_matches_lane_for_every_live_kind` iterates ALL 23 `KIND_LANE` entries and asserts `decision.lane == lane` for every one. This test passed (10/10 suite).

The code-level audit confirms: `route()` calls `packet_spec.lane_for(normalized)` directly (line 72 of router.py). The `known` flag and `rule_id` are derived from `normalized in packet_spec.KIND_LANE` — the same table. There is no second truth source. **The shadow router cannot disagree with the live router because they share the same `lane_for()` call.**

### What about the "UNKNOWN_KIND" case?

`route("brand-new-kind")` returns `lane=None, known=False, rule_id="kind:_unknown"`. This matches the live behavior: `lane_for("brand-new-kind")` returns `None`, and the `_lane_write` path sets `outcome="unmapped"` and returns without writing. The existing loud-diagnostic path (`_unmapped_loud_seen`) is unchanged. **Zero route change for unknown kinds.**

---

## 3. REPLY SEMANTIC CHANGE AUDIT

### Does N0 change reply_id generation, dedup, lane-first ordering, or expectation settlement?

**Answer: NO.** The reply code at lines 255-330 is unchanged EXCEPT for the three `observe_reply()` calls inserted at outcome points. The reply_id is generated by `uuid4().hex` (line 273) before the observation section. The lane-first write loop (lines 295-311) is unchanged. The legacy fallback (lines 312-317) is unchanged. The dedup check `is_duplicate_reply()` is unchanged. **Zero reply semantic change.**

Test `test_reply_lane_first_dedup_and_expectation_semantics_unchanged` confirms:
- Lane key appears BEFORE legacy key in xadd_keys (lane-first ordering preserved)
- reply_id in lane meta == reply_id in legacy meta (same id on both copies)
- `answers` field preserved in both meta dicts
- `is_duplicate_reply()` returns False on first sight, True on second (dedup works)
- Decision counter shows `decision:reply == 1`
- Reply outcome counter shows `reply:reply:success == 1`

**AMENDMENT 1 (non-blocking):** The `observe_reply("success" if lane_mid is not None else "fallback")` at line 325 calls `observe_reply` unconditionally — but the check `if lane_mid is None and legacy_mid is None` at line 322 already short-circuits with `observe_reply("failure")` and `return None`. So by line 325, at least one of `lane_mid`/`legacy_mid` is not None. The logic is correct. However, if `lane_mid is None` but `legacy_mid is not None`, the outcome is "fallback" — which means the lane write failed twice but legacy succeeded. This is the correct outcome string. No bug.

---

## 4. UNBOUNDED REDIS LABELS AUDIT

### Can an attacker inject unbounded Redis hash field names?

**Answer: NO.** The defense has three layers:

1. **`_observation_fields()` (router.py lines 109-118):** Only creates fields whose components are in the closed rosters: `MIRROR_OUTCOMES`, `REPLY_OUTCOMES`, and `_labels()` (which is `sorted(KIND_LANE.keys()) + ("_unknown",)`). Any `family` not "mirror" or "reply" → returns `None`. Any `outcome` not in the respective roster → returns `None`. Any `label` not matching a `KIND_LANE` key → collapsed to `_unknown`.

2. **`_METRIC_FIELD_SCHEMA` (router.py lines 85-92):** A frozen set of ALL legal field names, computed from `metric_field_schema()`. Every field name is pre-computed from the Cartesian product of static labels × static outcomes.

3. **`_observation_fields` final gate (line 118):** `if decision_field not in _METRIC_FIELD_SCHEMA or outcome_field not in _METRIC_FIELD_SCHEMA: return None`. Even if the label/outcome check passes, the resulting field name must be in the frozen schema.

Test `test_route_and_outcome_cardinality_is_static` sends 1,000 unique `"untrusted-kind-{N}"` strings and asserts only two counters exist: `decision:_unknown:1000` and `mirror:_unknown:unmapped:1000`. All 1,000 unique kind strings collapse to `_unknown`. The total field count is ≤ the schema size. **Cardinality is provably bounded.**

### Can a policy version change create new field names?

**Answer: NO.** The field names are derived from `packet_spec.KIND_LANE` at import time. If `KIND_LANE` changes (a code change), the field schema changes — but that's a code deploy, not an attacker-controlled input. And the new schema is still bounded to 24 labels × (4 mirror outcomes + 1 decision) + 1 reply kind × 4 = 124 fields. The `POLICY_VERSION` hash changes when `KIND_LANE` changes, and `route_stats()` reports `policy_matches` as False if the stored version differs.

**AMENDMENT 2 (non-blocking):** The `POLICY_VERSION` hash is computed ONCE at module import time (line 29). If `KIND_LANE` is modified at runtime (admittedly unlikely since it's a module-level dict), the hash goes stale and `policy_matches` would be False permanently. This is a theoretical concern — in practice `KIND_LANE` is static config — but the `route_stats()` report correctly detects the mismatch and reports `policy_matches: False`. No data corruption; just a stale hash. Not blocking.

---

## 5. METRIC FAILURE PROPAGATION AUDIT

### Can a Redis failure during record_observation fail a send?

**Answer: NO.** The entire observation path is fail-soft:

1. `shadow_router.route(kind)` in `_lane_write` is wrapped in try/except (line 411).
2. `shadow_router.record_observation()` in `_lane_write` is wrapped in try/except inside `finally` (lines 450-455).
3. `shadow_router.route("reply")` in `send_reply` is wrapped in try/except (lines 278-280).
4. The `observe_reply()` closure checks `if reply_decision is None: return` before calling `record_observation` (line 283).
5. `record_observation()` itself returns `False` on any Redis error (lines 133-135, 146, 153).
6. The non-pipeline fallback path (lines 157-167) also swallows all exceptions.

There is NO code path where a metric write failure propagates to the caller. The send succeeds or fails independently of observation.

Test `test_shadow_metrics_failure_never_fails_send` confirms: with `fail_metrics=True` on the fake Redis (hincrby raises RuntimeError), `bus.send()` still returns a valid mid, and both legacy and lane streams have the message. **Metric failure is fully isolated.**

### Can a route() failure (exception in packet_spec) fail a send?

**Answer: NO.** `route()` is a pure function: `str(kind)`, `packet_spec.lane_for(normalized)`, and `normalized in packet_spec.KIND_LANE`. The only possible exceptions are `TypeError` if `kind` is not stringable (caught by `str()` which works on everything) or a bug in `packet_spec`. The caller wraps `route()` in try/except. **Route failure is fully isolated.**

---

## 6. POLICY-VERSION MIXING AUDIT

### Can two processes running different code produce conflicting counters in the same Redis hash?

**Answer: YES — detected, not prevented.** The `POLICY_VERSION` hash (line 29) is computed at module import from the sorted `KIND_LANE` items. If process A has `KIND_LANE = {"handoff": "work", ...}` and process B has `KIND_LANE = {"handoff": "sig", ...}`, they produce different `POLICY_VERSION` hashes.

- Each process writes `_meta:policy_version` via `hsetnx` (set-if-not-exists). The FIRST process to write sets the version. The second process's `hsetnx` is a no-op (key already exists).
- Both processes `hincrby` their counters. The counters from process B use different field names if `KIND_LANE` differs (because `_labels()` and `metric_field_schema()` differ).
- `route_stats()` reports `stored_policy_version` (what's in Redis) vs `POLICY_VERSION` (local), and sets `policy_matches` accordingly.

**This is correct behavior for N0.** N0 is observational — it detects version mixing and reports it. It does not prevent mixed writes (prevention would require a CAS check before every hincrby, adding latency to the hot path). For a shadow observation phase, detection is sufficient.

### Is the `hsetnx` race-free?

Two processes starting simultaneously could both read `hgetall`, see no `_meta:policy_version`, and both try `hsetnx`. Redis `HSETNX` is atomic — exactly one succeeds. The other silently fails. The field names from the "loser" process may differ, but they're still within its own schema. `route_stats()` on the loser process will see `policy_matches: False` (stored version ≠ local version). This is fine — it tells the operator "two different KIND_LANE tables have written to this hash."

**No data corruption. Detection is correct.**

---

## 7. K0 MIRROR-FAILURE TRUTH AUDIT

### Does the kill drill assertion hold?

K0 spec: "Inject an xadd failure only on the lane mirror while legacy remains live. The recipient must receive exactly one logical message via current semantics; route explanation must remain unchanged; failure diagnostics/counter must identify the static rule; no wake, cursor, priority, deadline, or ownership state may change."

Test `test_lane_failure_preserves_legacy_delivery_and_counts_failure`:
- `fail_lane_writes=True` on FakeRedis → lane xadd raises RuntimeError
- Bus.send("fable", "handoff", ...) → `_emit` → legacy xadd succeeds → mid returned
- `_lane_write` → `shadow_router.route("handoff")` → decision recorded
- `packet_spec.lane_for("handoff")` returns "work" → lane xadd raises → `outcome = "failure"` (set in the except block, then `finally` records observation)
- Assertions: mid is not None; legacy inbox stream has 1 message; work lane stream is ABSENT (lane write failed); `decision:handoff == 1`; `mirror:handoff:failure == 1`

**K0 passes.** The recipient received the message via legacy. The lane mirror failure is counted. No lane was written to. The route explanation is correct.

---

## 8. DOOR-PARITY AUDIT

### Are packet_trace/packet_stats declared in the MANIFEST and present on both CLI and MCP?

**Evidence:** Test `test_door_guard_understands_intentional_cli_mcp_route_aliases`:
- `parity.CLI_MCP_ALIASES["packet_trace"] == "packet_route"` ✓
- `parity.CLI_MCP_ALIASES["packet_stats"] == "packet_route_stats"` ✓
- `parity.check()` returns zero failures for `packet_*` entries ✓

The MANIFEST declares them as `"shared"`. The MCP tools exist at `ai_setup_mcp.py:295-303`. The CLI commands exist at `agent_cli.py:2983,2999`. Both are exempt from ToolBox coverage with rationale "operator/MCP route explanation; transport continues to use packet_spec directly" — correct, this is an operator/agent diagnostic, not an in-task mutation tool.

Test `test_fresh_stdio_mcp_registers_route_tools_and_returns_single_frame` confirms a fresh MCP server has `packet_route` and `packet_route_stats` in its tool list, and `packet_route("handoff")` returns in <5s.

**Doors are in parity.**

---

## 9. PERFORMANCE AUDIT

### Does N0 add measurable latency to the send path?

Test `test_shadow_observation_adds_under_5ms_p50_on_local_redis`:
- 50 samples of `record_observation()` against real local Redis
- Median latency < 5.0ms

`route()` is a pure function: one dictionary lookup, one string format. ~hundreds of nanoseconds.

`record_observation()` does 1 pipeline with 2× HSETNX + 2× HINCRBY → 1 Redis round-trip. On local Redis, ~1-2ms. The test confirms p50 < 5ms.

For the `send_reply` path, the observation is in the reply code which already does 1-2 Redis round-trips (lane xadd, retry, legacy xadd). Adding one more pipelined observation call is ~1-2ms additional — within the existing reply latency budget.

**Performance is acceptable.** The 5ms bound is well within the N0 spec.

---

## 10. EXCLUSIONS COMPLIANCE

### Does N0 contain any of the §5 explicit exclusions?

| Exclusion | Present? | Evidence |
|-----------|----------|----------|
| Intent send wrappers | **NO** | No `api.ask/tell/hand/review/stream/signal` methods exist. `router.py` only has `route()` and `record_observation()`. |
| meta.wake honoring | **NO** | No code reads `meta.wake`. No wake-policy change. |
| Lane selection by new router | **NO** | `route()` is called for explanation; `packet_spec.lane_for()` is the transport selector. |
| Priority/deadline/ECN/AIMD | **NO** | No priority field reads, no deadline_ts stamping, no ECN bit, no rate control. |
| Target/model/cost selection | **NO** | No `target_hint`, no model routing, no cost data. |
| Refusal/reordering | **NO** | No send refusal based on route decision. No consumer-side reordering. |
| Raw-send deprecation | **NO** | `bus.send()` unchanged. No deprecation warning. |
| Legacy read/write removal | **NO** | Legacy streams untouched. Dual-write still ON. |
| Cursor migration | **NO** | No cursor changes. |
| Interactive lane peek | **NO** | No new read paths. |
| Trace repartition | **NO** | Trace lane still shared. |
| Latch/daemon/UI code | **NO** | None present. |
| Content-based routing | **NO** | `route()` reads only `kind`. |
| Model on hot path | **NO** | `route()` is pure dictionary lookup. |
| Unbounded labels | **NO** | Proven in §4. |

**All exclusions complied with.**

---

## 11. SUMMARY

| Threat vector | Verdict | Evidence |
|---------------|---------|----------|
| Delivery semantic change | **PASS** | `_emit`, `_lane_write`, `send_reply`, `_emit_fragments` unchanged except additive observation |
| Route semantic change | **PASS** | `route()` calls `packet_spec.lane_for()` — same truth source; test confirms 23/23 match |
| Reply semantic change | **PASS** | reply_id, dedup, lane-first ordering, expectation settlement all unchanged |
| Unbounded Redis labels | **PASS** | Three-layer defense: closed rosters → Cartesian schema → frozen set gate; test confirms 1000 unique kinds → 2 counters |
| Metric failure propagation | **PASS** | All observation paths have try/except; test confirms metric failure never fails send |
| Policy-version mixing | **PASS (detected)** | HSETNX sets version; route_stats reports policy_matches; different schemas produce different field names, detected |
| K0 mirror-failure truth | **PASS** | Lane write failure → legacy delivery intact → failure counter correct → no wake/cursor change |
| Door parity | **PASS** | Both CLI and MCP tools exist; manifest declares shared; parity check passes |
| Performance | **PASS** | p50 < 5ms on local Redis |
| Exclusion compliance | **PASS** | Zero exclusions violated |

### Amendments

| # | Severity | Description | Recommendation |
|---|----------|-------------|----------------|
| A1 | NON-BLOCKING | `observe_reply("success" if lane_mid is not None else "fallback")` at bus.py:325 — the conditional is correct but the expression is fragile; if someone adds code between the guard at line 322 and this line, `lane_mid` could be None here with `legacy_mid` also None (double-failure was already handled). | Extract to `outcome = "success" if lane_mid else "fallback"` on a separate line for clarity. |
| A2 | NON-BLOCKING | `POLICY_VERSION` is computed once at import. If `KIND_LANE` were modified at runtime (unlikely but possible in tests), the hash goes stale. | Add a `_policy_version()` function that recomputes on each call, or document that POLICY_VERSION is static. Not blocking — `route_stats()` already detects the mismatch. |

---

## FINAL: SHIP

N0 is observation-only, bounded, fail-soft, and compliant with all §5 exclusions. All 10 preregistered pins are GREEN. No delivery, route, or reply semantic change detected. Two non-blocking amendments filed. N0 may begin the 48-hour observation window.

*Filed under deepseek-review lock. This countercheck cites the exact working-tree paths and line numbers inspected. The reconciliation at research/reviewed/moonshot-network-spine-reconciliation-2026-07-17.md §5 governs.*
