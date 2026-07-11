# DeepSeek L2 verify -- GATE GREEN + 3 drifts (verbatim, committed by claude)

Provenance: bus msg 1783747879793-0, 2026-07-11 ~01:31; blind, code+tests vs the L2 BUILD SPEC.

I've read all four files and the spec. Here's the blind verify.

---

## T030 L2 BLIND VERIFY — GATE: **GREEN** ✅

### (1) Pulse placement — RIGHT points, dead-pulse unreachable during legit work

**Wired at three progress surfaces:**
- `on_trace` (bifrost_runner_deepseek.py:270): every tool call + thinking chunk fires `liveness.pulse()` — the REAL progress points. The spec says "~2s"; the implementation pulses per-event (finer granularity, strictly better).
- `on_activity` (runner:261): state transitions (thinking/reading/searching) all pulse.
- Turn edges: `"starting"` phase pulsed at boot (runner:383); `pulse_error` on caught fatal (runner:438).

**Dead-pulse unreachable during legit work?** YES. The hard_wedge gate requires BOTH `stuck >= 300s` AND dead pulse. Legit work pulses on every tool call / thinking chunk — a 300s silent window would mean the model produced zero tokens and zero tool calls for 5 minutes, which is itself a wedge. The TTL window is `PROGRESS_TTL * 2 = 10s` for "dead" classification; even the longest single tool call (30s) is far below the 300s stuck threshold. No false page path. ✓

### (2) Paging table vs reconciled spec — three minor drifts, none gate-blocking

| State | Spec Grade | Impl Grade | Match? |
|---|---|---|---|
| hard_wedge | page | page | ✓ |
| stalled_consumer | page | page | ✓ |
| frozen | banner | banner | ✓ |
| working (F2) | dashboard | dashboard | ✓ |
| self_reported_error | dashboard | dashboard | ✓ |
| **SUSPECTED MAIL LOSS** | dashboard | **not implemented** | drift |
| UNHANDLED | dashboard | deferred (boot/promoted) | per-spec |

**Drift 1 — SUSPECTED MAIL LOSS absent:** The spec explicitly says it's "auto-healed by RB-26" and "paging would duplicate the automation." Adding it as a dashboard line is low-risk future work; its absence doesn't change any page/banner behavior. **Minor.**

**Drift 2 — "draining" phase not in worklive vocabulary:** The spec names `starting / draining / error:<reason>` as extended phases. `starting` ✓ and `error:<reason>` ✓ (doctor reads `phase.startswith("error:")` at line 94). `draining` is not set; the runner's shutdown is a fast finally-block cleanup, so a hung-drain wedge is structurally near-impossible. **Minor.**

**Drift 3 — generation not checked in `pulse_fresh`:** The pulse carries `generation` (spec: "self-identifying stale tenure"), but the doctor's `pulse_fresh` (doctor.py:91-92) only checks `age_s <= PROGRESS_TTL * 2` + non-trigger, never reads `prog["generation"]`. A dead tenure's pulse could mask a hard wedge for up to 10s (the `PROGRESS_TTL * 2` expiry window). But 10s << 300s wedge threshold, so the mask evaporates before a page would fire. **Minor, zero practical impact.**

### (3) Hysteresis first-seen key lifecycle + page dedup — CORRECT

**Stalled-since key** (`bifrost:stalled_since:<agent>`, doctor.py:59-71):
- `SET NX` on first observation → first-seen timestamp preserved across checks ✓
- `DELETE` when stall clears (`present=False`) → clock resets ✓
- TTL = `STALL_HYSTERESIS_S * 20` = 3600s → prevents orphaned keys; 20x the hysteresis threshold so the key never expires before paging ✓

**Page dedup** (`bifrost:doctor_paged:<agent>:<state>`, doctor.py:145-152):
- `SET NX EX 3600` → one bus note per (agent, state) per hour ✓
- Returns False (skip) on both "already exists" and Redis error → fail-safe (silence over spam) ✓

### (4) Fail-open posture — no broken probe can ever page falsely

Traced every probe failure:

| Probe fails | Returns | Effect on hard_wedge | Effect on stalled_consumer |
|---|---|---|---|
| worklive `read()` | `None` → `{}` | `phase=""` → `non_idle=False` → no wedge | `idleish=True` but `backlog=0` → no stall |
| progress `progress_read()` | `None` | `pulse_fresh=False` → would page IF wedged (correct) | irrelevant |
| backlog `_probe_backlog()` | `0` | irrelevant | `backlog=0` → no stall |
| stalled_since `_probe_stalled_since()` | `time.time()` | irrelevant | `age=0 < hysteresis` → dashboard, never page |
| halted `_probe_halted()` | `None` | irrelevant | irrelevant |
| **Redis entirely down** | all `_client()` return `None` | `wl={}` → no wedge | `backlog=0` → no stall |

**Zero false-page paths.** A broken probe produces silence, never a spurious page. The doctor renders "healthy fleet" when it can't see anything — exactly the fail-open contract. ✓

### One-liners

- **Pulse points:** `on_trace` (tool/think chunks) + `on_activity` (state edges) + `starting`/`pulse_error` at lifecycle boundaries — the right set; dead-pulse-during-work requires 300s of zero progress, which IS a wedge.
- **Table drift:** Three minor (SUSPECTED_MAIL_LOSS not wired, draining phase absent, generation unchecked in pulse_fresh); all within spec tolerance; zero impact on the two page-grade states.
- **Hysteresis:** SET NX + DELETE on clear + 20x-threshold TTL = correct lifecycle; page dedup = SET NX EX 3600 per (agent, state), fail-silent.
- **Fail-open:** No broken probe → false page; every path returns safe defaults; Redis-down → "healthy fleet."

**GATE GREEN.** Ship it.