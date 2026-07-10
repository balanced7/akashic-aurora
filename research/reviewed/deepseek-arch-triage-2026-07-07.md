## Independent Triage — Architect’s Assessment

Your prior slices are **not** clean. The coverage matrix and the recent commit history tell a blunt story: you shipped fast, but you shipped **with the test debt accumulating**. Several production‑critical modules are running right now with zero direct tests, and the “frozen” built‑ahead backlog is already 15 files deep. This is technical debt that will bite you during the next coordination or narrative slice. Below is my prioritized plan.

### (1) Prior Shipped Slices That Need Immediate Attention
I identified them by cross‑referencing the “reachable but untested” modules with the commit that shipped them. The evidence from the matrix is that these modules are **running in production** but have **no direct tests**.

- **L1 liveness** (commit `4a7200a`): `core/comm/liveness.py` (162 LOC, reachable, untested). The heartbeat that underpins wedge detection. A regression here would silently break auto‑revive.
- **L3b/L5 supervisor** (commits `04fffea`, `cbaa98e`): `core/comm/launcher.py` (716 LOC, reachable, untested). The process‑lifecycle manager; a bug can starve or double‑spawn agents without notice.
- **L3b auto‑revive** (commit `04fffea`): `core/comm/runner_lock.py` (147 LOC, reachable, untested). The singleton lock guarding exactly‑one‑runner; another silent failure point.
- **Session state / snapshot** (shipped earlier, surfaced in recent bookend slice): `core/state/session_state.py` (433 LOC) and `core/comm/session_state.py` (222 LOC). Both reachable, untested. Session recovery is a “resume from nothing” path that is exercised every boot.
- **Narrative spine / knowledge graph** (ship dates unclear but live): `core/signals/coordinator_api.py` (990 LOC) and `core/foundation/relationship_types.py` (750 LOC) — massive, load‑bearing modules that are reachable and untested.

**Conclusion:** Liveness, launcher, session state, and the two huge foundation modules are **genuine risks** that escaped the QA net when their slices shipped. They must be addressed.

### (2) Genuine Risk Among the 13 Reachable‑but‑Untested Modules
“No test imports it” does not guarantee zero indirect coverage, but for these I judge the risk by **LoC + load‑bearing role**:

| Module | LoC | Role | Risk |
|--------|-----|------|------|
| `coordinator_api.py` | 990 | Agent‑signal coordinator API (still referenced by the signals layer) | **HIGH** — huge surface, unclear test penetration |
| `relationship_types.py` | 750 | Graph edge vocabulary used by learning/recall/primitives | **HIGH** — foundation, faulty edges corrupt recall |
| `launcher.py` | 716 | Process lifecycle, revive, storm guard | **HIGH** — direct crash impact |
| `session_state.py` (state) | 433 | Crash‑resume checkpoint | **MEDIUM‑HIGH** — every boot path |
| `session_state.py` (comm) | 222 | Live‑session snapshot for resume | **MEDIUM** — less critical if crash‑resume works |
| `liveness.py` | 162 | Heartbeat, wedge detection | **MEDIUM** (likely covered indirectly via runner tests that import runner, which imports liveness — but the **wedge‑logic** itself may lack unit tests) |
| `cognitive_metrics.py` | 275 | Experimental metrics engine | **LOW** — stage‑3 evidence, not load‑bearing yet |
| `negotiation.py` | 60 | Lightweight plan‑declaration window | **LOW** — small surface, likely exercised by integration |
| `trust/registry.py` | 160 | ACL reader | **LOW** — thin wrapper over a JSON file |
| `trust/capabilities.py` | 83 | Role vocabulary | **LOW** |
| `comm/context_hints.py` | 124 | Per‑agent context forwarding | **LOW** — simple data forwarding |
| `comm/nudge.py` | 152 | Targeted barge‑in | **MEDIUM** — could cause message injection bugs |
| `comm/runner_lock.py` | 147 | Singleton lock | **MEDIUM‑HIGH** — deadlock risk, but small LoC |

**Top‑5 to add direct tests for:**
1. `coordinator_api.py` (990 LOC — sheer volume and unclear coverage).
2. `relationship_types.py` (750 LOC — foundation, whole knowledge stack corruptible).
3. `launcher.py` (716 LOC — process management, if it breaks we lose agents).
4. `core/state/session_state.py` (433 LOC — crash‑resume is a bare‑metal path).
5. `core/comm/session_state.py` (222 LOC — snapshot for resume, closely coupled to the above).

### (3) Built‑Not‑Wired Backlog (15 items) — Verdicts
For each frozen module, I assign one of **WIRE‑NOW** (integrate urgently), **KEEP‑FROZEN** (future slice), or **DELETE** (removes dead weight).

#### Unwired WITH tests (12 modules)
| Module | Verdict | Reasoning |
|--------|---------|-----------|
| `coord/conductor.py` (149 LOC) | **WIRE‑NOW** | The orchestration shell needed by the mediation membrane. It’s tested, small, and the membrane wiring is the next major slice. |
| `comm/dispatcher.py` (105 LOC) | **WIRE‑NOW** | Doorbell→wake is a missing link in the wake infrastructure; without it `bifrost_wake` is a single‑point handshake. Tested already. |
| `learning/consolidation.py` (120 LOC) | **KEEP‑FROZEN** | Consolidation is a mid‑term priority for memory‑to‑chronicle. |
| `narrative/drift.py` (104 LOC) | **KEEP‑FROZEN** | Drift detector is a prototype; useful when narrative health matures. |
| `narrative/tag_audit.py` (98 LOC) | **KEEP‑FROZEN** | Tag governance is still gated by the wider tagging rewrite. |
| `narrative/tag_governance.py` (118 LOC) | **KEEP‑FROZEN** | Same as above — wire when governed re‑tag is enabled. |
| `perspectives/reinforce.py` (110 LOC) | **KEEP‑FROZEN** | Perspectives are a swappable projection; not yet a required layer. |
| `perspectives/schema.py` (101 LOC) | **KEEP‑FROZEN** | Same. |
| `coord/experiment.py` (132 LOC) | **KEEP‑FROZEN** | Stage‑3 evidence engine is not load‑bearing yet; keep for when we measure coordination. |
| `coord/metrics.py` (250 LOC) | **KEEP‑FROZEN** | Same. |
| `codex/lifecycle.py` (83 LOC) | **DELETE** | The codex layer was planned as a regenerable projection; it has been superseded by the learning/primitives stack. Its test‑only existence is dead weight. |
| `codex/schema.py` (91 LOC) | **DELETE** | Same. |

#### Unwired AND untested (3 modules)
| Module | Verdict | Reasoning |
|--------|---------|-----------|
| `comm/interject.py` (121 LOC) | **KEEP‑FROZEN** | Human‑interjection is a planned feature; no tests yet, but do not delete a forward‑looking module. Mark as “needs tests before wiring”. |
| `foundation/fast_cache.py` (623 LOC) | **DELETE** | 623 LOC of untested, unwired caching layer. The Store + Redis already provide fast reads; this is premature optimisation that will rot. The effort to test + wire is higher than value. |
| `state/session_recovery.py` (322 LOC) | **DELETE** | Diagnostic snapshot recovery (distinct from the two session‑state modules). Untested, unwired, and we already have two session‑state modules that cover checkpoint/resume. Redundant. |

*Rationale for deletions:* They are large, untested, and duplicate or pre‑empt existing functionality. Deleting them immediately reduces the maintenance surface without impacting any active code path.

### (4) Name Collision: `session_state.py`
Two modules in different packages both named `session_state.py`:
- `core/state/session_state.py` (433 LOC) — checkpoint & recovery system.
- `core/comm/session_state.py` (222 LOC) — snapshot live Bifrost session for later resume.

**Resolution:** Rename for clarity and to eliminate import confusion.
- `core/state/session_state.py` → **`core/state/session_checkpoint.py`** (or `checkpoint.py`)
- `core/comm/session_state.py` → **`core/comm/session_snapshot.py`** (or `session_resume.py`)

Then update all imports and the ARCHITECTURE doc. This costs a few minutes of find‑and‑replace but prevents silent shadowing when a module does `from core.state import session_state`.

### (5) Structural / Entry‑Point Risks
- **Unwired super‑critical modules threaten the membrane coherence.** The conductor and dispatcher are the missing arms of the mediation membrane; keeping them frozen means the membrane’s “unify” job remains half‑built, and the doorbell wake is fragile (only `bifrost_wake.py` does it directly).
- **The 13 reachable‑but‑untested modules are a ticking time‑bomb for any refactor.** A rename or change in `relationship_types` or `coordinator_api` will be impossible to verify without a test suite, and those modules are ingested by almost every knowledge‑related path.
- **Two session‑state modules with the same name creates a latent import hazard.** If someone writes `from core import session_state` (without package), Python will pick one arbitrarily depending on `__init__.py` exports. This has already been a source of bugs in large codebases.
- **The frozen backlog’s size (15 files) risks “built‑not‑wired” rot.** If not pruned (deleting dead code), future wiring efforts will need to re‑audit every frozen module for compatibility.

---

## Prioritized Triage Plan (P0 → P2)

### P0 — Stop the regression bleed (now)
**Finding:** Seven production‑critical modules shipped without direct tests, including the three heaviest (`coordinator_api`, `relationship_types`, `launcher`).  
**Action:** Write direct unit tests for:
1. `core/signals/coordinator_api.py` (990 LOC)  
2. `core/foundation/relationship_types.py` (750 LOC)  
3. `core/comm/launcher.py` (716 LOC)  
4. `core/state/session_state.py` (433 LOC) — to be renamed  
5. `core/comm/session_state.py` (222 LOC) — to be renamed  
**Effort:** L (1–3 days per module, 2–5 days total heavily loaded).

### P1 — Wire the missing arms of the membrane + name fix (now, alongside P0)
**Finding:** The conductor and dispatcher are tested but disconnected; the session‑state collision will cause confusion.  
**Action:**
- Wire `coord/conductor.py` and `comm/dispatcher.py` into production entry points (doorbell/wake and coordination shell).
- Rename the two `session_state.py` modules as above, update imports, and add a regression guard in `check_comprehensibility.py` to prohibit future name collisions.
**Effort:** M (1–2 days for wiring + rename).

### P2 — Clean the frozen backlog (this sprint)
**Finding:** 3 modules (`codex/lifecycle`, `codex/schema`, `fast_cache`, `session_recovery`) are dead weight.  
**Action:**
- DELETE `core/codex/lifecycle.py`, `core/codex/schema.py`, `core/foundation/fast_cache.py`, `core/state/session_recovery.py`.
- Mark `interject.py` as frozen‑but‑must‑be‑tested before wiring.
- Update the wiring gate to ratchet deletion (so that an unwired module that is not on a “kept” list fails ship).
**Effort:** S (a few hours + guard update).

---

## Single Most Important Thing to Do First
**Write direct tests for `coordinator_api.py`, `relationship_types.py`, and `launcher.py`.**  
These three are the largest untested production modules, collectively ~2460 LOC, and they form the backbone of signal logging, knowledge structure, and agent supervision. If any of them has a latent defect, the regression will impact *every* future slice. Add tests now, before you wire anything else.
