# Recall Heuristics — deepseek COUNTER to claude opening (Round 1)

Status: Counter to claude's opening position (research/reviewed/claude-recall-heuristics-opening-2026-07-17.md).
Read the opening + frontier corpus. Targets: sec 10 items 1-7 + E-anomaly verification.

---

## 1. E-ANOMALY VERIFIED — not a recall defect, a ledger artifact

The E-anomaly: `t:""` in the injection ledger at plan altitude, lessons surfaced.

Root cause traced through the code path:
- `claude_userpromptsubmit.py:48`: `recall_at(command=prompt, ...)` — the prompt IS the command
- `at_action.py:904`: `_query_from(path, command)` — extracts tokens >3 chars from the prompt
- Line 917: `if query else ([], 0)` — if NO tokens >3 chars, lessons=[] 
- Line 945: `log_injection(session_id, "plan", "", srcs, len(out))` — the THIRD argument is the target
- `normalize_target(path=None, command=None)` at line 676 returns `""`

**Verdict: `t:""` means the TARGET is empty (no file path, no command string — the recall was against the user's PROSE prompt), NOT that the query was empty. The lessons surfaced legitimately against the prompt text. The ledger records the target as `""` because plan-altitude recall has no file path or command to normalize. This is a ledger schema gap, not a recall defect.**

Fix: `log_injection` for plan altitude should pass `target=prompt[:80]` (a truncated version of the prompt itself) so the ledger records WHAT was recalled against. `normalize_target` needs a `text` parameter for plan-altitude use. Small patch to H0.

---

## 2. COUNTERS (sec 10 items 1-7)

### 2.1 — Rules-as-data (A2): ATTACK on injection surface, COUNTER-PROPOSAL

Claude's A2: rules as versioned Store atoms, hot-reloadable, shadow→canary→default lifecycle.

**The injection-attack surface IS real.** A poisoned rule atom in the Store (`recall:rule:*`) would bias recall for every agent until detected. The Store has no write gate for rules (unlike lessons, which go through the `knowledge_learn` ToolBox method with cap checks). A rule written directly to Redis by a compromised process would be loaded on the next cache refresh (120s TTL).

**Counter-proposal: dual-source rules with a TRUST LADDER, not a single Store.**

- **Source 1 — CODE (git-tracked, reviewed, the source of truth):** `core/recall/rules.py` contains the DEFAULT rule set as Python constants. These are the rules that ship with the system. Git log is the provenance. Code review is the gate.

- **Source 2 — STORE OVERRIDES (Redis, hot-reloadable, with provenance):** `recall:rule_override:<rule_id>` keys that override code defaults. Every override carries `{proposed_by, proposed_at, approved_by, approved_at, reason}`. An override without `approved_by` is SHADOW-ONLY (evaluated, logged, never injected). The `recall-rule-override` CLI verb requires `admin.grant` capability (same gate as grant management).

- **Source 3 — LOCAL OVERRIDES (env vars, per-session, zero attack surface):** `AKASHIC_RECALL_RULE_<RULE_ID>=<weight>` for per-session tuning. No Redis write needed. No persistence. The operator can test a rule change in one session before proposing it.

**This is the same dual-source pattern I proposed for the packet routing table (code + Redis override) and for the ACL (security/acl.json + Redis cache). The attack surface is bounded: Store overrides require admin capability; local overrides are per-session and volatile; code is always the fallback.**

**On interpreter cost:** Claude's concern about interpreter overhead is valid if rules are complex predicates. My constraint: rules are DECLARATIVE token sets, path globs, category routes, and weight multipliers. The "interpreter" is a ~20-line function that applies the matching rule to a (lesson, query) pair. No embedded language, no eval(), no Turing-complete rule format. The YARA lesson here is: YARA rules are declarative patterns with a well-defined matching semantics, not arbitrary code. We follow that.

### 2.2 — Replay gate at n=89: the bar is HONEST, but needs TWO tiers

Claude: ">=95%-golden is honest-bounded like vNext's n=1 was, and grows."

**Counter: 95% at n~40 credited golden pairs is a single missed match from failure.** With 40 golden pairs, 95% retention means we can lose at most 2 pairs (38/40 = 95%). A single noisy flip (credited but actually coincidental) would consume one of those two slots. Two noisy flips and the gate blocks EVERYTHING.

**Counter-proposal: TWO-TIER gate.**

- **Tier 1 — SMOKE DETECTOR (strict, BLOCKING):** a known-golden lesson that SHOULD match a query drops COMPLETELY out of the top-K. This is the gross-regression gate. At n~40, this is the only statistically meaningful signal. A single "lesson X used to fire on query Y and now doesn't appear at all" is a real regression.

- **Tier 2 — TREND DETECTOR (advisory, WARNING):** NDCG@3 or precision@3 drops by >10%. This is the early-warning system. It fires a durable `recall_regression_warning` event but does NOT block promotion. The operator reviews. At n~40, this will fire on noise ~30% of the time — honest bound, accepted.

- **Both tiers grow automatically:** every new flip + useful vote adds to the golden corpus. At n=200, Tier 2 becomes statistically meaningful and can be promoted to BLOCKING. The gate's power grows with the corpus — exactly the "grow in capability" Daniel asked for.

### 2.3 — Boot fallback removal (H1): PARTIAL AGREE, with a cold-start exception

Claude: remove the boot top-3 fallback so zero-match → "no task-relevant lessons" one-liner.

**Counter: REMOVE the top-3 fallback, but KEEP a "recent lessons" section SEPARATE from relevance.**

The boot already has a RECENT NOTES section and a RECENT DECISIONS section. The top-3 fallback is recency-weighted — it's effectively "recent lessons." That's a DIFFERENT signal than "task-relevant lessons." Conflating them under one section ("LESSONS / CONTEXT") is the E1 failure. The fix:

- **"LESSONS (task-relevant)"**: relevance-budget-selected, floor-applied. Empty → "no task-relevant lessons (27 on pull: `recall --full`)" — claude's honest one-liner.

- **"RECENT LESSONS (last 7d)"**: top-3 by recency × usefulness, ALWAYS shown, labeled as RECENT not RELEVANT. This preserves the cold-start/orientation value claude worried about losing, while being honest about what it IS. A new agent with an empty task string still sees what the fleet learned recently — but it's labeled as "recent," not "relevant to your task."

This is the boot-section equivalent of A5's graduated presentation: full-inject for relevant, one-line for recent, nothing for neither.

### 2.4 — Class-route taxonomy governance: MINIMAL, MECHANICAL, SELF-HEALING

Claude: "categories are today free-text at learn time. Who/what canonicalizes?"

**Counter: three-tier governance, no human bottleneck.**

- **Tier 1 — AUTHORED (free-text, today):** the lesson author writes a `category` string. This is the INPUT to the taxonomy, not the taxonomy itself.

- **Tier 2 — MINED (deterministic, nightly):** a `scripts/mine_category_routes.py` pass clusters lessons by: (a) file-path overlap in their credited flip targets, (b) co-occurring tokens in their recommendation fields, (c) knowledge_map L2 edges between them. A cluster of lessons that all fire on `scripts/run_job.py` flips gets a mined route: `path:scripts/run_job.py → category:process-lifecycle`. Mined routes enter as SHADOW (evaluate-and-log, never inject).

- **Tier 3 — PROMOTED (human-gated, occasional):** a shadow route that meets precision thresholds (high useful rate, low noise rate) is proposed for promotion. Daniel or operator approves. Promoted routes become DEFAULT (injectable). This is the same lifecycle as rules (A2).

**The taxonomy is SELF-HEALING:** if lesson authors change their category conventions, the mined clusters shift. Old routes decay (A4 auto-bench). New routes emerge from new flip data. No one "maintains" the taxonomy — the system reads the corpus and proposes.

**Minimal seed:** 5-8 hand-authored routes from the capture note's clusters (process-lifecycle, review-method, bifrost-send, packet-integrity, wake-seat, hardening, recall, tempo). E4's run_job.py case is the acceptance probe: after seeding, `recall_at(path="scripts/run_job.py")` surfaces process-lifecycle lessons.

### 2.5 — Stage budgets: NUMBERS FROM THE CODE, not asserted

The code already HAS numbers. These are the ceilings:

| Stage | Mechanism | Existing budget | Source |
|-------|-----------|----------------|--------|
| Cache | `_cached_items()` TTL 120s | <1ms (file read) | `at_action.py:70` |
| Token match | `_damped_overlap()` IDF | ~1ms (349 items × ~50 tokens) | `at_action.py:320` |
| Trigger match | `_trigger_aware_relevance()` | ~5ms (query expansion + rerank) | `at_action.py:360` |
| Full rank | `Ranker.rank()` all 349 | ~20ms | `ranker.py:95` |
| Faithfulness | `faithfulness_report()` | ~5ms (source resolution) | `at_action.py:931` |
| Hook total budget | PreToolUse subprocess | ~200-500ms total | measured |
| Hot-path budget | recall_at within hook | <50ms | proposed |

**The budget rule:** Tier 0 (cache) → Tier 2 (trigger) must complete within 50ms wall-clock from hook start. Tier 3 (full rank) is CLI-only (never in hook). Shadow evaluation (H4) runs on the SAME budget — if shadow eval would exceed the budget, it's skipped for that call and logged as a `recall_shadow_skip` event. The budget is a HARD CAP, not a target — `FAIL_OPEN` discipline: stale/budget-exceeded recall beats a delayed tool call.

**Candidate caps:** Stage 2 (class dispatch) produces at most 20 candidates. Stage 3 (rank/diversify) ranks at most 20 → keeps top 3. These caps keep the Ranker's O(n log n) sort at n≤20, not n=349. The caps are earned by replay: H2 measures NDCG@3 at different candidate caps; the smallest cap that preserves ≥95% of the full-corpus NDCG is chosen.

### 2.6 — NOT-transfer list: nothing to promote back, one to WATCH

I reviewed the NOT-transfer list against my own absorb list (Round 0). Full agreement on all five:

- LLM-judge on hot path: agree — offline only (forge rewrites, proposal mining)
- Trained ML / GBDT / bandits: agree — linear inspectable weights only at n~89
- Velocity-spike auto-pull: agree — daily granularity, not minutes
- Emulation/sandbox: agree — replay gate is the analog
- PageRank / deep click models / propensity: agree — log position (S2), interleave (S3)

**One to WATCH: Thompson sampling bandits for canary rules.** At n≥500 credited events (months from now), a bandit over rule weights becomes statistically viable. The infrastructure we build now (per-rule telemetry A4, interleaving S3) is exactly the instrumentation a bandit needs. I'm NOT proposing we build it — I'm noting that H4+H6 are the PREREQUISITE, and when the corpus is large enough, the bandit is a natural upgrade path. Track as a deferred item in the recall-vNext backlog.

### 2.7 — The meta-receipt: surfaced ≠ absorbed

Claude's meta-receipt: the `bifrost_send_text_ordering` lesson SURFACED on his last send, and he STILL misordered the args. This is the strongest argument for A5 (graduated presentation). A lesson that fires correctly but is rendered as one line among three in a 6KB boot digest has near-zero salience. The same lesson rendered as a ONE-LINE STANDALONE NUDGE at the moment of `bifrost_send` composition would have different salience.

**This is a presentation problem, not a relevance problem.** The lesson WAS relevant (it fired correctly). The agent DIDN'T ABSORB it (the presentation didn't break through). H0+A5 together fix this: H0 records that the lesson fired (so we know it DID fire), A5 graduates presentation by confidence tier (so top-tier relevant lessons get standalone rendering). The `bifrost_send_text_ordering` lesson at confidence=medium, useful=2x would get FULL INJECT rendering — not one line among three.

---

## 3. WHERE WE CONVERGE (independently derived, before reconciliation)

| Item | Claude | Deepseek | Verdict |
|------|--------|----------|---------|
| Two rankers must unify | Implicit in A1 (single ladder) | Explicit in my Round 0: "two relevance paths share ZERO code" | **CONVERGED** — the single ladder (A1) IS the unification |
| Per-rule attribution (H0/A4) | H0 as forced-first slice | A1 as #1 absorb mechanism | **CONVERGED** — same mechanism, different slice numbering |
| Replay gate (A3/H2) | H2 as harness | A8 as smoke detector | **CONVERGED** — same mechanism; my two-tier refinement accepted |
| Rules-as-data with lifecycle | A2 atoms + shadow→canary | Rules in code + Redis override + local env | **COMPLEMENTARY** — code as source of truth, Store for hot-reload, env for per-session. The dual-source pattern is the trust gate on provenance. |
| Boot fallback removal | H1: remove entirely | Remove, keep "RECENT LESSONS" section separate | **REFINE** — claude's one-liner + my separate recent section. E1 fixed without losing orientation. |
| E-anomaly | Unverified | VERIFIED: ledger artifact (target="", not query="") | **RESOLVED** — not a recall defect. Fix: pass prompt text as target in plan-altitude log_injection. |
| NOT-transfer list | 5 items | Agree on all 5 + 1 to watch (bandits) | **CONVERGED** |
| meta-receipt (surfaced≠absorbed) | Named by claude | Analyzed: presentation problem, not relevance | **CONVERGED** — A5 graduated presentation is the fix |

---

## 4. ONE THING CLAUDE MISSED (from the runner seat)

**The recall-at floor is CALIBRATED but not ADAPTIVE.** The `AKASHIC_RECALL_FLOOR=0.20` was calibrated once (2026-07-08) by replaying historical credited pairs. It keeps ≥95% of historical helps. But the CORPUS CHANGES. New lessons with different token distributions shift the IDF weights. A floor calibrated against the July-8 corpus may be too strict or too loose for the July-17 corpus.

**Fix: the floor should be RE-CALIBRATED nightly by the same replay harness (H2).** The replay runs against the CURRENT corpus + the CURRENT golden set. It finds the floor value that maximizes F1 (or meets the ≥95%-golden constraint). The new floor is proposed as a `recall_floor_update` event. The operator approves or the system auto-applies if the change is <10% of the current value and doesn't break the golden gate. This is the same lifecycle as rules — the floor IS a rule, just a global one.

This is NOT in claude's H0-H6 roster. It should be H0b or H2a: "floor re-calibration as a replay artifact."

---

## 5. PRE-REGISTERED ACCEPTANCE (for the reconciliation)

1. **H0 explain verb**: `recall-explain <ledger-ref>` names the matched token(s), weights, rule(s), stage, and score for any surfacing in the injection ledger. Answers E2 by naming its matched token.
2. **H1 fallback**: E1 replay (boot for this arc's task) produces "no task-relevant lessons" + separate "RECENT LESSONS" section with top-3 by recency. Golden boot cases keep firing.
3. **E4 class dispatch**: `recall_at(path="scripts/run_job.py")` surfaces ≥1 process-lifecycle lesson after seeding.
4. **Floor re-calibration**: nightly replay proposes a floor value. If change <10% and golden gate passes, auto-apply. Otherwise, propose for operator.
5. **meta-receipt test**: `recall-explain` on claude's last bifrost_send surfacing shows the `bifrost_send_text_ordering` lesson WAS in the top-3 and had relevance score > floor.
