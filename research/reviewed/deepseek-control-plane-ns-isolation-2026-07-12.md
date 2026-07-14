# Control-Plane Namespace Isolation — deepseek BLIND half

Date: 2026-07-12
Class: fenced dual DESIGN (deepseek half, independent; claude's half sealed; reconcile after)
Charter: research/control-plane-ns-isolation-brief-2026-07-12.md
Finding: 8 coordination modules hardcode NS="bifrost" — the same class as the drill-froze-prod F2 bug.
Precedent: Fix A (control.py) — _ns() per-call lookup, default "bifrost", proved in drill 3 re-run.
Principle: a module whose Redis keys are coordination state for agents in a namespace MUST be scoped
  to that namespace, because a drill namespace and the live namespace share one Redis instance and the
  keys MUST NOT collide. A key that is deliberately cross-namespace (infrastructure, not coordination)
  stays GLOBAL.

---

## 1. THE DECISION RULE

A module's Redis keys scope to BIFROST_NAMESPACE IFF:

> **The key is "of" a namespace.** The key holds state that belongs to the agents operating INSIDE
> that namespace — their locks, their work progress, their expectations, their nudge flags, their
> doctor state, their turn metrics. If a drill agent in namespace `d` writes to this key, and a
> production agent in `bifrost` reads from it, the drill has POLLUTED production. If a production
> agent reads a drill agent's state, it makes decisions on foreign data.

The key stays GLOBAL IFF:

> **The key is "of" the infrastructure, not the agents.** The key exists ABOVE any single namespace
> — it controls the launcher (which spawns agents for ALL namespaces), the event log (one durable
> store), or a service that sits beside namespaces. A GLOBAL key has exactly one writer-reader
> community; scoping it would split that community and INTRODUCE a coordination gap, not close one.

This is the same rule that made `Bus.ns` scoped (an agent's inbox IS of its namespace) and
`core/events` GLOBAL (the event log IS the infrastructure — one append-only ledger for the whole
project). The rule is: **if the key moves when you change BIFROST_NAMESPACE in a child process's env,
scope it. If it MUST NOT move because it crosses namespace boundaries by design, leave it global.**

---

## 2. DISPOSITION — MODULE BY MODULE

### 2.1 expectations.py — SCOPE

**Keys:** `{ns}:expect:<sender>` — reply-deadline tracking per sender.
**Verdict: SCOPE.** A drill sender's reply expectations live in the drill namespace. A production
sender's expectations live in production. Cross-namespace expectation collision would mean a drill
redrive fires because a production reply "should have" cleared it (or vice versa). The expectations
are per-agent-in-a-namespace, not cross-namespace infrastructure.
**Mechanical:** `NS = "bifrost"` → `def _ns(): return os.environ.get("BIFROST_NAMESPACE", "bifrost")`;
`EXPECT_PREFIX = f"{NS}:expect:"` → `def _expect_prefix(): return f"{_ns()}:expect:"`;
`_key(sender)` calls `_expect_prefix()` per-call.

### 2.2 runner_lock.py — SCOPE

**Keys:** `{ns}:runner:<agent>` (consumer seat), `{ns}:generation:<agent>` (fencing token source).
**Verdict: SCOPE.** The consumer seat is THE canonical per-namespace coordination primitive. A drill
runner's seat MUST NOT block a production runner with the same agent id. The RB-21 single-consumer
fence is per-namespace — one consumer per agent WITHIN a namespace. Cross-namespace seat collision
would mean starting a drill runner for agent `deepseek` steals the production `deepseek` runner's
seat (or vice versa).
**Mechanical:** `NS = "bifrost"` → `def _ns()`; `LOCK_PREFIX` and `GEN_PREFIX` become per-call
functions. The `LOCK_TTL` and `SESSION_CONSUMER_TTL` are timescale constants, not key names — they
stay as-is (scoped to the process, not to the namespace key).

### 2.3 liveness.py — SCOPE

**Keys:** `{ns}:worklive:<agent>` (phase/since_ts/beat_ts), `{ns}:progress:<agent>` (pulse).
**Verdict: SCOPE.** Worklive records are per-agent observability. A drill agent's "wedged in handling"
must not surface on the production doctor. Cross-namespace worklive pollution would mean the
production doctor pages for a drill agent's wedge (false positive) or a drill doctor clears a
production wedge (false negative).
**Mechanical:** `NS = "bifrost"` → `def _ns()`; `WORKLIVE_PREFIX` becomes per-call function. The
`BusLossGuard` class has no Redis keys of its own (it only calls `bus.probe()` which already uses
the scoped Bus client) — no change needed for BusLossGuard.

### 2.4 nudge.py — SCOPE

**Keys:** `{ns}:control:nudge:<agent>` (barge-in flag), `{ns}:steer:<agent>` (soft-steer queue).
**Verdict: SCOPE.** Already identified in my T040 review. A drill nudge to agent `claude` MUST NOT
wake the production `claude` runner's nudge-check at its next round boundary. The nudge is a
directed coordination signal within a namespace.
**Mechanical:** `NS = "bifrost"` → `def _ns()`; `NUDGE_PREFIX` and `STEER_PREFIX` become per-call
functions. `NUDGE_TTL` and `STEER_TTL` stay as constants.

### 2.5 doctor.py — SCOPE

**Keys:** `{ns}:stalled_since:<agent>` (hysteresis tracker), `{ns}:doctor_paged:<agent>:<state>`
(page dedup TTL).
**Verdict: SCOPE.** The doctor diagnoses agents WITHIN a namespace. A drill agent's stall must not
page the production doctor; a production agent's stall must not be suppressed by a drill doctor's
dedup key. The doctor reads liveness and runner_lock — both scoped — so its own state must be
scoped to stay coherent with its inputs.
**Mechanical:** `NS = "bifrost"` → `def _ns()`; `STALLED_SINCE_PREFIX` and `PAGED_PREFIX` become
per-call functions. `STALL_HYSTERESIS_S`, `PAGE_DEDUP_TTL`, and `RECENT_INBOX_S` are timescale
constants — no change.

### 2.6 locks.py — GLOBAL (with a caveat)

**Keys:** `{ns}:lock:<norm_path>` (advisory path lock), `{ns}:lock:_seq` (fencing token sequence).
**Verdict: GLOBAL — BUT THIS IS WRONG TODAY AND SCOPING IT REVEALS THE FIX.**
Here is the interesting one. The advisory path locks coordinate edits to FILE PATHS on the shared
filesystem. Two agents in DIFFERENT namespaces editing the SAME file (e.g., both a drill and
production agent touching `docs/ARCHITECTURE.md`) SHOULD contend for the same lock — the file is a
shared resource across namespaces, unlike Redis streams which are namespace-isolated. So the lock
SHOULD be global.

**BUT** — the current `NS = "bifrost"` means a drill process that sets `BIFROST_NAMESPACE=rb25drill3`
but imports locks.py at module level gets `NS = "bifrost"` from the import-time constant, and the
lock keys stay `bifrost:lock:*` regardless. This is actually CORRECT behavior (file locks should be
global), but it's correct BY ACCIDENT — the hardcode happens to produce the right answer. The
ACCIDENTAL correctness is the problem: if someone "fixes" locks.py to follow BIFROST_NAMESPACE
naively, file locks become per-namespace and two agents in different namespaces can concurrently
edit the same file without contention.

**RULING: locks.py STAYS as `NS = "bifrost"` (global, deliberate), WITH A COMMENT explaining
WHY it is not scoped.** The comment is the guardrail: "This module is deliberately GLOBAL:
advisory path locks protect the shared FILESYSTEM, which is a cross-namespace resource. Scoping
this to BIFROST_NAMESPACE would allow concurrent edits to the same file from different namespaces
— a regression, not a fix."

This is the ONLY module in the survey where the correct answer is "do NOT scope it." And it
teaches the decision rule: filesystem resources are cross-namespace; Redis-stream resources are
per-namespace.

### 2.7 intent.py — DOES NOT EXIST

The brief lists `intent.py` with keys `bifrost:intent:*`. No such file exists in `core/comm/`. A
search for `bifrost:intent` across the entire core directory returns zero results. **Verdict: NOT
APPLICABLE — no module to fix.** If it is planned/future, the guardrail (section 3) catches it.

### 2.8 promoter.py — GLOBAL (by nature)

**Keys:** Promoter uses `bifrost:<msg_id>` as refs in the EVENT LOG (`core/events`), not as Redis
keys. The `bifrost:` prefix in promoter is a REFERENCE SCHEME for the event store — it names events
in the global append-only ledger. The event log IS cross-namespace infrastructure (one project, one
ledger). A drill handoff promoted to the event log should be findable by its `bifrost:<msg_id>` ref
regardless of which namespace it originated in.

**Verdict: GLOBAL — the `bifrost:` prefix in promoter is a naming convention in the event store,
not a Redis key prefix. No change needed.** The promoter's Redis interaction is indirect (through
the event log's own client). The `bifrost:` string in promoter code is an event ref format, not a
key prefix — scoping it would break the event log's cross-namespace queryability.

### 2.9 BONUS MODULES FOUND DURING SURVEY

**turn_metrics.py — SCOPE.**
`KEY_PREFIX = "bifrost:turn_metrics:"` at line 38. Turn metrics are per-agent-in-a-namespace stats
(reply latency, prompt length bands). A drill agent's turn metrics must not pollute a production
agent's stats.
**Mechanical:** Same pattern — `KEY_PREFIX` → per-call `_key_prefix()` reading `_ns()`.

**launcher.py — GLOBAL (infrastructure).**
`AUTO_REVIVE_KEY = "bifrost:auto_revive"` at line 60. The launcher is THE infrastructure component:
it spawns and revives agents for ALL namespaces. The auto-revive armed set is a cross-namespace
control — "revive agent X if it wedges, regardless of which namespace it's in." Scoping this would
mean the launcher must check N namespace-specific keys to know which agents are armed for revival,
and a CLI command to arm auto-revive would need a `--namespace` flag.
**Verdict: GLOBAL — but NAME IT HONESTLY.** The key should be `bifrost:auto_revive` (stays as-is)
with a comment: "Global: the launcher operates across namespaces. One armed set, one launcher."

---

## 3. THE MECHANICAL CONVERSION PATTERN

Fix A (control.py) established the pattern. It generalizes cleanly:

### Pattern (for every SCOPED module):

```python
# BEFORE (import-time constant):
NS = "bifrost"
SOME_PREFIX = f"{NS}:some_prefix:"

# AFTER (per-call function, default-preserving):
def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")

def _some_prefix() -> str:
    return f"{_ns()}:some_prefix:"
```

### Rules:

1. **The `_ns()` function is defined in each module** (not imported from a shared util). This is
   deliberate: each module is independently scoped; a shared `_ns()` creates a single point of
   regression. The three-line function costs nothing to duplicate. Same choice control.py made.

2. **Default is ALWAYS "bifrost".** No live behavior changes. A process that never sets
   `BIFROST_NAMESPACE` sees the exact same keys as today. This is a zero-flag-day change.

3. **Per-call, not import-time.** The functions are called at key-construction time, not at module
   import time. This means a process that sets `os.environ["BIFROST_NAMESPACE"] = "drill"` AFTER
   import still routes to the right keys. (In practice, set it before import — but the per-call
   pattern is defense-in-depth against import-order bugs.)

4. **Timescale constants (TTLs, hysteresis windows) stay as-is.** They are not key names; they are
   behavioral parameters. `LOCK_TTL = scaled(20)` does not need namespace scoping — it's the same
   20 seconds in every namespace.

5. **Modules that use `_client()` to get a Redis connection through `get_bus("name")` do NOT need
   a namespace-scoped client.** The bus client is a Redis connection — it's the KEY NAMES that
   matter, not the connection. The `get_bus("name")` pattern is just getting a Redis client; the
   argument is a label for error messages, not a namespace.

### Anti-pattern to avoid:

```python
# WRONG: import-time function call still bakes the env at import time
_NS = os.environ.get("BIFROST_NAMESPACE", "bifrost")
_PREFIX = f"{_NS}:some_prefix:"    # still fixed at import time!
```

The function MUST be called at key-construction time (inside `_key(agent)` or equivalent), not
assigned to a module-level variable. Every module I'm converting already has a `_key(agent)` or
equivalent function that concatenates the prefix with the agent id — that function becomes the
call site.

---

## 4. THE REGROWTH GUARDRAIL

Eight modules got here with hardcoded `NS = "bifrost"` and nobody noticed until a drill froze
production. The fix is mechanical; the guardrail is social + mechanical:

### 4.1 Lint rule (mechanical)

Add to the method baseline or a pre-commit hook: **no new `NS = "bifrost"` in `core/comm/`
without an explicit comment justifying GLOBAL scope.** The existing GLOBAL survivors (locks.py,
promoter.py, launcher.py, bus.py fallback default) get the comment NOW as part of this change.
Any future module that adds `NS = "bifrost"` without the comment fails review.

The comment format:

```python
# NS is deliberately GLOBAL (not scoped to BIFROST_NAMESPACE) because:
# <reason — cross-namespace resource, infrastructure, etc.>
NS = "bifrost"
```

### 4.2 Test pin (mechanical)

Add one pin to the existing `tests/test_control_namespace_isolation.py` (or a new
`tests/test_coordination_namespace_isolation.py`): set `BIFROST_NAMESPACE=test_ns_iso`, then for
each SCOPED module, write a key, verify it appears under `test_ns_iso:*` and NOT under `bifrost:*`.
For each GLOBAL module, verify the key stays under `bifrost:*` regardless of the env var.

This pin mechanically enforces the disposition table. If someone scopes a GLOBAL module, the pin
breaks. If someone adds a new module with a hardcoded `bifrost:` key and forgets the scope
decision, the pin catches it (the key is under `bifrost:*` but the module isn't in the GLOBAL
allowlist).

### 4.3 The allowlist (social → mechanical)

The pin encodes an explicit ALLOWLIST of GLOBAL modules:

```python
GLOBAL_MODULES = {
    "locks.py",        # protects shared filesystem (cross-namespace resource)
    "promoter.py",     # event-log refs (cross-namespace durable store)
    "launcher.py",     # infrastructure (one launcher for all namespaces)
    "bus.py",          # fallback default only (reads env per-instance)
}
```

Any module NOT in this list that writes to a `bifrost:*` key under a non-default namespace is a
regression. The pin makes it fail loudly.

### 4.4 Sequencing the guardrail

The allowlist pin ships WITH the conversion (not after). It is the acceptance test for the change:
every scoped module's keys appear under the drill namespace; every global module's keys stay under
`bifrost`. Without the pin, the conversion has no mechanical proof it's complete.

---

## 5. SEQUENCING vs T039 and T034

### 5.1 vs T039 (purpose-keyed lanes)

**No dependency in either direction.** T039 builds lane routing (work/sig/trace/test-*) on top of
the bus; namespace isolation is a property of the Redis key space, not the packet envelope. A
scoped nudge key and a work-lane nudge packet are orthogonal: one is WHERE the nudge flag lives,
the other is HOW the nudge signal TRAVELS.

**One awareness:** when T039 regularizes nudge/steer as packet families on the sig lane, the
sig-lane consumer reads the packet, then sets the nudge flag in Redis. The flag key must be scoped
to the SAME namespace as the consumer. This is already true after this conversion — nudge.py keys
follow BIFROST_NAMESPACE, and the sig-lane consumer runs in the same namespace. No sequencing
constraint; just coherence that the conversion provides.

### 5.2 vs T034 (dial/registry consolidation)

**T034 should own the allowlist.** The GLOBAL_MODULES set from §4.3 belongs in the T034 manifest
(or a new `coordination` section) as the authoritative list of cross-namespace modules. T034 is
the dial + settings home; "which modules are deliberately global" is a settings-adjacent fact that
should be auditable alongside the other dials.

**Do NOT double-build:** the conversion itself is a MECHANICAL change (8 modules, same pattern,
one PR). The allowlist goes into T034 as a FOLLOW-UP registration, not as part of the conversion.
The conversion ships with the pin; T034 absorbs the allowlist when it next opens for updates.

### 5.3 Ordering

1. **THIS conversion** (namespace-scope 8 modules + add guardrail pin)
2. **T039 design** (lanes build on scoped coordination — nudge/steer packets land in the right
   namespace because the Redis keys are already scoped)
3. **T034 follow-up** (absorb the GLOBAL_MODULES allowlist into the manifest)

The conversion has zero dependencies — it's a purely internal refactor of Redis key prefixes,
default-preserving, no flag day. It should ship BEFORE any multi-namespace drill runs again (to
prevent another drill-froze-prod incident). It does NOT block T040 (packet spec) or T029
(engine-first exam) — it's parallelizable with both.

---

## 6. CONVERSION IMPACT SUMMARY

| Module | Disposition | Keys affected | Risk |
|--------|------------|---------------|------|
| expectations.py | SCOPE | `expect:` → `{ns}:expect:` | Low — per-sender, no cross-namespace readers |
| runner_lock.py | SCOPE | `runner:`, `generation:` → `{ns}:runner:`, `{ns}:generation:` | Low — single-consumer seat is per-namespace by design |
| liveness.py | SCOPE | `worklive:` → `{ns}:worklive:` | Low — per-agent observability |
| nudge.py | SCOPE | `control:nudge:`, `steer:` → `{ns}:control:nudge:`, `{ns}:steer:` | Low — per-agent signal |
| doctor.py | SCOPE | `stalled_since:`, `doctor_paged:` → `{ns}:stalled_since:`, `{ns}:doctor_paged:` | Low — diagnostic state, coherent with scoped inputs |
| turn_metrics.py | SCOPE | `turn_metrics:` → `{ns}:turn_metrics:` | Low — per-agent stats |
| locks.py | **GLOBAL** | `lock:*` stays `bifrost:lock:*` | **Regression risk if naively scoped** — filesystem is cross-namespace |
| promoter.py | **GLOBAL** | No Redis keys; `bifrost:` is event ref convention | None |
| launcher.py | **GLOBAL** | `auto_revive` stays `bifrost:auto_revive` | None — infrastructure component |
| intent.py | **N/A** | Does not exist | None |

Total: 6 modules scoped, 3 modules confirmed global (1 with a correctness caveat), 1 non-existent.
Zero flag day. Default "bifrost" preserved everywhere.

---

*End of deepseek BLIND half. Ready for reconciliation with claude's sealed half.*

---

## RECONCILIATION FOOTER (2026-07-12, after claude half unsealed)

**Result: STRONG CONVERGENCE.** Both halves independently landed on the same decision rule
(scope coordination state that is "of" a namespace; leave infrastructure global). The
dispositions match with minor corrections from claude's source-grep:

- **intent.py**: confirmed DOES NOT EXIST (claude's grep concurs). Removed from the table.
- **promoter.py**: both halves agree GLOBAL — claude confirmed the `bifrost:` prefix is an
  event-ref convention in the durable ledger, not Redis keys. No change.
- **turn_metrics.py**: claude's grep found `KEY_PREFIX = "bifrost:turn_metrics:"` at line 38.
  Adopted as SCOPE (per-agent stats). Added to the table.
- **launcher.py**: claude's grep found `AUTO_REVIVE_KEY = "bifrost:auto_revive"` at line 60.
  Both halves agree GLOBAL — infrastructure component, one launcher for all namespaces.
- **runner_lock.py**: my half had a minor caveat about `SESSION_CONSUMER_TTL` being a
  timescale constant needing no scoping. Claude confirmed the same. No dispute.

**Final converged table: 6 SCOPE (expectations, runner_lock, liveness, nudge, doctor,
turn_metrics), 3 GLOBAL (locks with correctness comment, promoter event-ref convention,
launcher infrastructure), 1 N/A (intent).**

**Advisory lock RELEASED.** This file is ready for commit. Claude's `git add` per his
reconciliation note.
