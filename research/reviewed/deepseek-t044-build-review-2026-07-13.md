# DeepSeek T044 (T039a) BUILD REVIEW — adversarial fence, gates claude's commit

Status: current (2026-07-13)
Class: build-review fence (deepseek, full-capability lane). Adversarially gates the T039a lane-router
build before claude commits.
Build under review: UNCOMMITTED working-tree implementation — core/comm/packet_spec.py (lanes section),
core/comm/bus.py (_lane_write + dual-write in _emit/_emit_fragments), tests/test_t039a_lane_router.py
(pre-registered RED at 793d70e, now GREEN). Governing docs: docs/t039-lanes-latches-design-2026-07.md
(Daniel gate) + docs/packet-spec-v1-2026-07.md (LAW).

## VERDICT: AMBER — PASS AFTER ONE CENSUS FIX. The architecture is correct and the two deviations are
sound; one live production kind is missing from the router table. Fix it and this is GREEN.

---

## DOCUMENTS EXAMINED (every file:line is from one of these)
- core/comm/packet_spec.py (lines 178–245 — the new lanes section)
- core/comm/bus.py (lines 250–350 — _emit, _emit_fragments, _lane_write)
- tests/test_t039a_lane_router.py (full file, 158 lines)
- docs/t039-lanes-latches-design-2026-07.md (governing design)
- docs/packet-spec-v1-2026-07.md (LAW)
- scripts/bifrost_ui.py (lines 350–410 — the `inform` kind source)
- scripts/bifrost_runner_deepseek.py (lines 275–290, 540–570)
- Git: 793d70e (HEAD, pre-registration), working tree diff

---

## CORE REVIEW

### 1. Deviation: unknown kind → legacy-only + loud once-per-kind — SOUND

**What the spec says** (packet-spec-v1, R6/lane contract):
> "unknown kind = REFUSED loud"

**What the implementation does** (bus.py:317–325):
```python
if lane is None:
    if kind not in Bus._unmapped_loud_seen:
        Bus._unmapped_loud_seen.add(kind)
        _loud(f"[lane-router] kind '{kind}' has NO lane mapping -- riding legacy "
              f"only. Add it to packet_spec.KIND_LANE before the T039b cutover.")
    return
```

The implementation returns early — no lane write, but the legacy write (already completed at line 275)
succeeds. The spec's REFUSED is deferred to the T039b/d cutover.

**Soundness analysis:**
- The strangler fig pattern REQUIRES P0 to be non-breaking: unknown kinds must not REFUSE during the
  soak window or the system breaks before any consumer benefits from lanes.
- The once-per-kind throttle prevents log spam while ensuring operators see every missing kind.
- The straddling comment explicitly names the end-state contract: "Full refusal is the spec's end
  state and activates at cutover, once the soak proves the table complete."
- The reader census bar (A3, governing doc §"Folded amendments") forces a comprehensive kind audit
  before T039b, catching any missing entries before the spec's REFUSED activates.
- No consumer reads lane streams during P0 (A4 tail-at-flip), so the missing lane write causes zero
  data loss — the legacy stream IS the delivery path.

**Risk:** An unmapped kind goes unnoticed for the entire P0 soak window, then suddenly REFUSED at
T039b cutover. Mitigations: (a) the loud warning fires on first occurrence, (b) the reader census
bar forces a grep audit, (c) the governing doc names every live kind. However, if operators ignore
stderr, a real problem could survive undetected. This is inherent to the strangler pattern, not a
flaw in the implementation.

**Verdict: SOUND.** The deferral is correctly motivated and bounded. The loud path is sufficient
for P0 because the warning + census bar form a two-stage catch.

---

### 2. Deviation: P0 lane retention = approximate-trim everywhere — SOUND

**What the spec says** (PER-LANE CONTRACT):
- work: overflow REFUSE-WRITE loud
- sig: overflow REFUSE-WRITE loud
- trace: XTRIM oldest

**What the implementation does** (bus.py:343–344):
```python
self._client.xadd(key, fields, maxlen=packet_spec.lane_maxlen(lane),
                  approximate=True)
```

All lanes use `approximate=True` maxlen trimming, NOT the spec's REFUSE-WRITE for work/sig.

**Soundness analysis:**
- During P0, NO consumer reads lane streams (A4: lane cursors initialize tail-at-flip at T039b
  cutover). The lane history is a write-only soak log.
- `approximate=True` is standard Redis behavior — it trims to approximately maxlen entries using
  a probabilistic algorithm that is more efficient than exact trimming. The exact count may vary
  by a few entries.
- The spec's REFUSE-WRITE contract activates at T039b: "P0 retention = approximate-trim everywhere;
  REFUSE-WRITE overflow contract activates at the T039b cutover when a lane becomes load-bearing."
  (packet_spec.py lines 210–212, docstring).
- The governing design doc's §"Folded amendments" M2 addresses this: "dual-write retention guard —
  cutover order bounded by lane retention windows." The approximate trim during P0 is irrelevant
  since nothing reads lanes.
- The trace lane uses maxlen ~5000 with approximate trim, not explicit XTRIM. During P0 this is
  equivalent — both are approximate retention policies on a firehose nobody reads. The explicit
  XTRIM contract activates at T039b when trace consumers exist.

**Question: "Does anything read the lane streams during P0 that I missed?"**
- Reader census (governing doc A3): runner via bifrost_api, wake listener, core/comm/doctor.py,
  scripts/bifrost_ui.py, scripts/bifrost_console.py, agent_cli.py bifrost-sync →
  agent/bifrost_pull.py. ALL of these read the LEGACY stream during P0 (the cutover hasn't
  happened). None reads lane streams.
- The trace firehose could attract ad-hoc inspection (e.g., a developer running `XREAD` on
  `bifrost:trace`), but that's seatless QoS0 — approximate retention is correct for that use.
- **Confirmed: nothing reads lane streams in P0.**

**Verdict: SOUND.** The approximate-trim is correct for a write-only soak. The spec's contracts
are correctly deferred to T039b.

---

### 3. KIND_LANE census completeness — ONE MISS

I verified every production bus kind against the KIND_LANE table (packet_spec.py:187–200) by
grepping live `bus.send()`/`bus.broadcast()` call sites:

| Kind | Source | In KIND_LANE? |
|------|--------|---------------|
| handoff, reply, request, chat, note, answer, dispatch, status | bus.send/broadcast + runner | ✓ work |
| question, query | agent_cli.py --kind help + deepseek_chat | ✓ work |
| halt, interrupt, pause, nudge, steer | bus.send + bifrost_api + deepseek_chat | ✓ sig |
| resume | agent_cli --kind | ✓ sig |
| trace, thinking, tool, narration | runner trace feed + bus | ✓ trace |
| ledger_update, resolved, hint | promoter + context_hints + deepseek_chat | ✓ trace |
| **inform** | **scripts/bifrost_ui.py:404** | **✗ MISSING** |

**The miss:** `scripts/bifrost_ui.py:404`:
```python
kind = "inform" if fidelity == "inform" else "chat"
mid = BUS.broadcast(kind, text, meta=meta) if broadcast else BUS.send(to, kind, text, meta=meta)
```

`inform` is the DEFAULT fidelity in the Bifrost UI (see `scripts/bifrost_ui.py:1470`:
`setFidelity('inform')`). Every user message sent from the Bifrost console with the default
fidelity uses `kind="inform"`. It is functionally identical to `kind="chat"` — both are plain
user-to-agent messages. It belongs in the work lane.

**Impact during P0:** Every user message from the Bifrost UI (default fidelity) will NOT be
dual-written to the work lane. The first such message per process emits:
`[lane-router] kind 'inform' has NO lane mapping -- riding legacy only.`
This is not a correctness bug (the message IS delivered via legacy, which is the only path
consumers read in P0), but it means the lane soak is incomplete — the most common user message
kind is missing from the dual-write, so the soak won't exercise the work lane for user messages.

**Fix:** Add `"inform": "work"` to KIND_LANE in packet_spec.py. One line. The kind is
functionally identical to `"chat"` — both are directed/broadcast user-to-agent text.

**Note on `content_floor_failed` and `content_floor_exhausted`** (scripts/bifrost_runner_deepseek.py:286):
These are NOT bus kinds. They are passed to `pulse(agent_id, ...)` (a liveness heartbeat), not to
`bus.send()`/`bus.broadcast()`. Correctly absent from KIND_LANE.

**Verdict: ONE CENSUS MISS.** `inform` must be added to KIND_LANE as `"inform": "work"`.
Everything else is covered.

---

### 4. Trace spot INCR cost on the hot path — ACCEPTABLE

**What the code does** (bus.py:330–333):
```python
tick = 0
try:
    tick = int(self._client.incr(f"{self.ns}:trace:spotcount"))
except Exception:
    pass
```

The Redis INCR is ONLY on the trace lane path. Work and sig lane writes pay zero overhead (they
never enter the `if lane == "trace"` block). For trace packets, the cost is one additional Redis
round-trip on the send hot path.

**Assessment:** Trace is QoS0 firehose — no expectation, no wake, no seat depends on it. An extra
INCR on a firehose is acceptable. The INCR is also inside a try/except, so a Redis failure during
the counter increment silently degrades (tick stays 0, the lane_wants_integrity check returns False
for tick=0, trace stays unstamped). This is exactly D-3's global spot counter design, correctly
implemented.

**Verdict: ACCEPTABLE.** QoS0 firehose, try/except guarded, correct per D-3.

---

### 5. Field identity of lane copies — CORRECT

**Non-trace** (bus.py:329): `fields = env` — direct reference to the same dict that was
legacy-written. Since `xadd` serializes the dict, both writes produce identical field values.
This is correct and intentional — the test `test_dual_write_work_lane_and_legacy_identical`
verifies field-by-field equality.

**Trace** (bus.py:330): `fields = dict(env)` — shallow copy, then len/sha are conditionally
removed. This is correct because the trace copy must be unstamped (or spot-stamped) while the
legacy copy stays always stamped.

**Risk:** `fields = env` means the lane write and legacy write share the same dict object. If
future code inserts a mutation between the legacy xadd and the lane xadd (e.g., adding a lane-
specific field), both streams would be affected. Currently, `_lane_write` is called immediately
after the legacy xadd (line 276 right after line 275), and no mutation occurs between them.
Documented risk, not a bug.

**Verdict: CORRECT.** Intentional reference-sharing for field identity; trace copy correctly
branches for exemption.

---

### 6. Bell-rings-once — CORRECT

**Test** (test_t039a_lane_router.py:109–115): monkeypatches `_ring_bell` to record calls, then
asserts exactly one ring after `bus.send("agent-d", "handoff", "bell probe")`.

**Implementation:** `_lane_write` (bus.py:304–350) does NOT call `_ring_bell` at all. The bell
is rung only in `_emit` (line 278, after `_lane_write` returns) and in `_emit_fragments` (line
302, after the fragment loop). Lane bells activate at T039b (when wake-listeners subscribe to
the work-lane bell). This is correct per the design.

**Verdict: CORRECT.** Exactly one bell per send, verified by test.

---

### 7. Pre-registration RED→GREEN claim — VERIFIED

**RED commit** (793d70e, HEAD): `tests/test_t039a_lane_router.py` committed with B1-B6 bars but
NO implementation in bus.py or packet_spec.py. The test would fail because `packet_spec.lane_for()`
did not exist and `bus._lane_write()` was not called.

**GREEN working tree:** Implementation added to packet_spec.py (lanes section, 68 lines) and
bus.py (_lane_write, 47 lines; dual-write calls at 2 sites). Tests adjusted for API compatibility
(Bus constructor now takes client + agent_id, `frm` kwarg removed from send).

**Verdict: HONEST.** The pre-registration discipline was followed. Tests were committed RED,
implementation came after, tests now pass GREEN.

---

### 8. Known limitation: already-running processes — ACCEPTABLE

Processes that were running before the implementation lands will call the old `_emit` without
`_lane_write`. They must be restarted for dual-write to take effect. During the restart window,
some sends are legacy-only. This is documented as acceptable — the lane soak is best-effort, and
no consumer reads lanes during P0. The runner restart is planned post-GREEN.

**Verdict: ACCEPTABLE.** Standard deployment limitation; zero data impact since lanes are
write-only in P0.

---

### 9. `_unmapped_loud_seen` class-level set — CORRECT

`_unmapped_loud_seen: set = set()` (bus.py:307) is a class-level attribute on `Bus`. This means
the once-per-kind throttle is process-wide across all Bus instances. Correct per the docstring
("once-per-kind-per-process throttle"). The set grows by one entry per unique unmapped kind
ever seen; in practice this is 0-5 entries, so unbounded growth is not a concern for P0.
If it became one, a TTL or size cap would be warranted.

**Verdict: CORRECT.** Process-wide throttle, bounded by the small universe of unmapped kinds.

---

## BARS B1-B6: ALL PASS (with the census fix for B6)

| Bar | Description | Status |
|-----|-------------|--------|
| B1 | Per-kind router pins: control→sig NEVER trace; unknown→NO lane | **PASS** |
| B2 | Dual-write: legacy+lane field-identical; bell rings once | **PASS** |
| B3 | Kill-switch BIFROST_LANES_DUAL_WRITE=0: lanes untouched, legacy unchanged | **PASS** |
| B4 | Trace exemption: unstamped by default, Nth spot-checked; legacy always stamped | **PASS** |
| B5 | Key shapes: lane dimension before topology suffix | **PASS** |
| B6 | Reader census documented in governing doc | **PASS*** |

*B6 passes the test as written (the doc names the readers), but the census is incomplete because
`inform` is not in KIND_LANE. The fix closes this.

---

## SUMMARY

| Item | Verdict |
|------|---------|
| Deviation 1 (unknown→legacy+loud) | SOUND — strangler-required; sufficient for P0 |
| Deviation 2 (approximate-trim) | SOUND — write-only soak; contracts activate at T039b |
| KIND_LANE census | ONE MISS — `inform` from bifrost_ui.py:404 not in table |
| Trace INCR cost | ACCEPTABLE — QoS0 firehose, try/except guarded |
| Field identity (lane copies) | CORRECT — reference for non-trace, copy for trace |
| Bell rings once | CORRECT — verified by test |
| Pre-registration RED→GREEN | HONEST — 793d70e RED, working tree GREEN |
| Known limitation (restart) | ACCEPTABLE — write-only soak, planned restart |
| `_unmapped_loud_seen` | CORRECT — process-wide throttle |
| B1-B6 bars | ALL PASS (B6 requires `inform` fix for full coverage) |

## REQUIRED FIX (one line)

In `core/comm/packet_spec.py`, in the `KIND_LANE` dict, in the work section (between `"chat"` and
`"note"` or adjacent), add:

```python
"inform": "work",
```

This maps `scripts/bifrost_ui.py:404`'s default user-message kind to the work lane, where it
belongs alongside `"chat"`. Without this, every user message sent from the Bifrost UI at default
fidelity rides legacy-only during P0 and triggers a loud warning.

## OPTIONAL (not blocking)

Consider adding a dedicated test pin: `test_inform_kind_routes_work` in the B1 parametrized group.
Low priority — the existing `test_unknown_kind_has_no_lane_strangler_phase` would catch it if
`inform` were ever removed from the table after being added.

---

## CLOSING

The implementation is tight, correctly scoped to P0, honest about its deviations, and the two
deliberate deviations are soundly reasoned. The `inform` census miss is the only gap — a live
production kind that the router doesn't know about. Fix it and this is GREEN. Nothing else
blocks the commit.
