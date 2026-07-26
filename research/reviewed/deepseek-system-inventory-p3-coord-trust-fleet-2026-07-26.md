# System Inventory + Prior-Art Register — Part 3: Coordination, Trust, Fleet, Harness, Hooks
## DeepSeek, 2026-07-26 — overnight program

---

## core/coord (11 modules)

### 18. Task Ledger (task_ledger.py)

**WHAT IT DOES:** Governed task tracking. Tasks have states (PROPOSED → APPROVED → IN_PROGRESS → VERIFYING → DONE), agents, claims, and transitions. Every transition is gated and attributed. `format_state()` renders the task list (the roadmap the agents obey). The README's "44 shipped of 100 registered" comes from here.

**CONNECTED TO:**
- Writes to: Store (task hashes), event log (transition events)
- Reads from: Store
- Used by: `agent_cli.py task`, `wrap` verb, `conductor.py`, boot greeting, the task list rendered in agent context blocks
- Related: `conductor.py` (orchestration), `suite_baseline.py` (CI baseline recording)

**COMPARABLE SYSTEMS:**
1. **JIRA / Linear** — issue tracking with workflows, assignments, and states. Our task ledger is a minimal, git-durable version. JIRA has custom workflows, our states are fixed.
2. **Temporal** — durable execution with workflows and activities. Our task ledger tracks WHAT to do; Temporal executes it with retries and timeouts. Temporal would replace the manual task→build→verify loop with a durable workflow.
3. **Kubernetes Custom Resources** — declarative desired state with controllers reconciling. A task would be a CR; a controller would transition it through states.

**THE DELTA:**
- Temporal: durable execution. A task defined in Temporal runs its workflow to completion with automatic retries, timeouts, and compensation. Our tasks are manually advanced — an agent claims, builds, and transitions the state by hand.
- JIRA: rich metadata, comments, attachments, sprints. Our tasks have ~6 fields (id, title, state, agent, created, updated). Spartan but sufficient.

**THE IMPORT:** UNVERIFIED. The task ledger's value is in the gated transitions, not the execution model. Making tasks auto-advance (e.g., on CI green, auto-transition from VERIFYING to DONE) would reduce manual toil. But this requires CI→task ledger integration, which is a D-lane dependency (CI must be honest first).

**THE ANTI-IMPORT:** **Temporal workers.** Adding a workflow engine for 100 tasks is overkill. The manual advance model works at our scale. Revisit at 1,000+ active tasks.

**STATUS:** LIVE. 24KB. 44 DONE, 17 active, 18 next, 20 proposed. States are manually advanced by agents or Daniel.

---

### 19. Conductor (conductor.py)

**WHAT IT DOES:** Orchestration layer for the fleet. Routes tasks to agents, tracks which agent is working on what, enforces the "one agent per task" rule. The conductor is the human-in-the-loop coordinator — it suggests, the human gates.

**CONNECTED TO:**
- Reads from: `task_ledger.py` (task state), `liveness.py` (agent presence), `runner_lock.py` (seat ownership)
- Writes to: `task_ledger.py` (assignments)
- Used by: `agent_cli.py` (task claim), `wrap` verb (status summary)

**COMPARABLE SYSTEMS:**
1. **Kubernetes scheduler** — assigns pods to nodes based on resources, affinity, and constraints. Our conductor assigns tasks to agents based on claim and availability. K8s has resource-aware scheduling; ours is manual claim-based.
2. **Apache Mesos** — two-level scheduler: allocates resources to frameworks, which schedule tasks within their allocation. Our conductor is single-level.
3. **Load balancer (HAProxy, NGINX)** — distributes work across workers. Our conductor doesn't distribute — agents pull work by claiming tasks.

**THE DELTA:**
- Kubernetes: resource-aware scheduling (CPU, memory, GPU). Our conductor has no resource model — an agent claims a task and hopes it fits.

**THE IMPORT:** **Agent capacity model.** Each agent declares its capabilities and current load. The conductor refuses assignments that exceed capacity. This is a ~20-line addition: `agent_capacity = {max_tasks, supported_kinds}`, checked on claim. Right now any agent can claim any task, which is how codex got handed a build it couldn't execute.

**THE ANTI-IMPORT:** **Kubernetes scheduler complexity.** Pod scheduling with constraints, taints, tolerations, and priorities is over-engineered for a 4-agent fleet.

**STATUS:** LIVE. 11KB. Manual claim-based task assignment. No capacity model.

---

### 20. Suite Baseline (suite_baseline.py)

**WHAT IT DOES:** Records CI test results as a node-id baseline for diffing. `record(label, sha, failures)` stores a baseline; `diff(current_failures)` reports new/fixed/inherited failures. Found tonight: it was 44.7 HOURS STALE at bb0beac with 13 known failures while HEAD has 25.

**CONNECTED TO:**
- Writes to: Store (baseline hashes)
- Reads from: Store
- Used by: `agent_cli.py suite-baseline`, CI (theoretically — hasn't been refreshed)
- Pins: `test_w34_suite_baseline.py`

**COMPARABLE SYSTEMS:**
1. **pytest --junitxml + diff** — the standard CI pattern: generate JUnit XML, compare to previous run. Our baseline is a custom format but conceptually identical.
2. **Develocity (Gradle) / BuildPulse** — test flakiness detection, historical trends, blame attribution. Our baseline has no history — just one recorded state.
3. **pytest-xdist** — parallel test execution with failure tracking. Our baseline doesn't track per-worker failures, just the aggregate.

**THE DELTA:**
- Develocity: flakiness detection (which tests pass/fail intermittently), historical trends, blame. Our baseline has one snapshot — can't answer "was this test also flaky last week?"

**THE IMPORT:** **Record from CI, not from a working tree.** The baseline at bb0beac was recorded from a working tree — the same tree that has 11 failures vs the clean clone's 25. The baseline must be recorded from a clean clone (matching CI's view) or it's measuring the wrong thing. This is the D-lane fix.

**THE ANTI-IMPORT:** UNVERIFIED. A flakiness database is useful but premature — we need ONE honest baseline before we can track drift.

**STATUS:** LIVE but STALE. 6KB. 44.7 hours old. Needs refresh from a clean clone.

---

## core/trust (2 modules)

### 21. Capabilities (capabilities.py)

**WHAT IT DOES:** Capability-based access control. `Capability(action, resource, constraints)` — an unforgeable token granting specific access. `verify(cap, action, resource)` checks the capability is valid and sufficient.

**CONNECTED TO:**
- Used by: `guards.py` (pre-action authorization), `toolbox.py` (ToolBox verb gating), UNVERIFIED — grep for other consumers

**COMPARABLE SYSTEMS:**
1. **macaroons** — bearer tokens with caveats (contextual constraints). Our capabilities have constraints; macaroons would add attenuation (deriving weaker caps from stronger ones) and third-party caveats.
2. **OAuth 2.0 scopes** — "this token can read:lessons write:lessons". Our capabilities are OAuth scopes with resource-level granularity.
3. **AWS IAM policies** — JSON policy documents with Effect, Action, Resource, Condition. Our capabilities mirror this shape.

**THE DELTA:**
- Macaroons: attenuation (derive a weaker capability from a stronger one), third-party caveats (e.g., "valid only if user is in group X"). Our capabilities are static — you can't derive a read-only version of a read-write capability.
- OAuth: token refresh, revocation, introspection endpoints. Our capabilities are stored in the Store — no refresh/revoke lifecycle.

**THE IMPORT:** **Capability attenuation.** If an agent holds "write:*", it should be able to derive "write:scratch/*" for a sub-agent. This is macaroon attenuation — append a caveat, get a weaker token. Prevents privilege escalation by construction.

**THE ANTI-IMPORT:** **Full OAuth 2.0 / OIDC.** Token endpoints, refresh tokens, client registration — server-grade auth for a local fleet. Our capability model is sufficient.

**STATUS:** UNVERIFIED — I haven't traced the full usage. `capabilities.py` exists (4KB). Needs audit.

---

### 22. Registry (registry.py)

**WHAT IT DOES:** Agent capability registry. Maps agent_id → allowed capabilities. `can(agent_id, action, resource)` checks the registry.

**CONNECTED TO:**
- Reads from: Store (agent capability records), `capabilities.py`
- Used by: `guards.py`, UNVERIFIED — other consumers

**COMPARABLE SYSTEMS:**
1. **Kubernetes RBAC** — Role → RoleBinding → Subject. Our registry is agent→capability; K8s has an intermediate Role abstraction.
2. **LDAP / Active Directory** — group-based access. Agents are "users," groups are "roles."
3. **OPA / Rego** — policy-as-code. `allow { input.agent == "claude"; input.action == "write" }`. Our registry is data; OPA is logic.

**THE DELTA:**
- OPA: policy as code, decoupled from the registry. You write Rego rules; OPA evaluates them. Our registry is agent-capability pairs — no policy logic.

**THE IMPORT:** **Policy-as-code for the fence.** The guarded write door already has assertion logic. OPA/Rego would externalize that: "allowed if agent owns the lock AND the path is in the allowlist AND the file is git-tracked." This makes the fence auditable without reading Python.

**THE ANTI-IMPORT:** **Full OPA deployment.** Running an OPA sidecar for a local fleet adds a service dependency. Policy-as-code in Python (our assertion runner) is sufficient.

**STATUS:** UNVERIFIED — partial audit. `registry.py` exists (9KB). Need to trace consumers.

---

## agent/harness (9 modules) + scripts/hooks (7 modules)

### 23. Hook System (scripts/hooks/)

**WHAT IT DOES:** Claude Code hook integration. Seven hooks: `claude_pretooluse.py` (recall injection before every tool call), `claude_posttooluse.py` (outcome capture, flip detection, learn nudge), `claude_sessionstart.py` (cache warm), `claude_sessionend.py` (wrap summary), `claude_userpromptsubmit.py` (plan-time recall), `claude_stop.py` (wake enforcer), `claude_trace.py` (tool-call → bus trace). Also `scripts/checkers/` — 12 CI guard scripts (boundaries, doc freshness, comprehensibility, door parity, pointer promises, wiring, etc.).

**CONNECTED TO:**
- Integrated with: Claude Code (via USER settings ~/.claude/settings.json with absolute paths)
- Reads from: `core/recall/at_action.py` (recall engine), `core/comm/bus.py` (trace emission), Store
- Writes to: bus (traces), event log (flips, injections), Store (counters)
- Guarded by: `scripts/checkers/*` — CI gates that fail the build

**COMPARABLE SYSTEMS:**
1. **git hooks** — pre-commit, post-commit, pre-push. Our checkers are pre-commit hooks (run on git operations). The pattern is identical: a script is registered, git calls it, exit 0 = pass.
2. **pre-commit framework** — managed git hook runner with plugin ecosystem. Our checkers are custom scripts; pre-commit would manage them with caching, parallel execution, and auto-update.
3. **oxlint** — JavaScript linter with category tiers (correctness, suspicious, pedantic, style). Our checkers have no severity tiers — they pass or fail. oxlint's tiered model would let us gate on correctness while allowing style warnings.
4. **OPA admission control** — policy evaluation before an operation. Our hooks are admission control: PreToolUse evaluates "should I inject recall for this action?" PostToolUse evaluates "should I capture an outcome?"

**THE DELTA:**
- pre-commit: managed hooks with caching. Our hooks run raw Python; pre-commit would cache environments and run in parallel. The 12 checkers run sequentially; pre-commit would parallelize them.
- oxlint: tiered severity. Our checkers are binary — they gate the build or they don't. A correctness-tier failure should block; a style-tier failure should warn. This is the confidence-tiered gating Daniel wants.
- OPA: decoupled policy from enforcement. Our hooks have policy IN the Python code. OPA would externalize it — the hook asks OPA "should I inject?" and OPA evaluates rules.

**THE IMPORT:** **pre-commit framework for checkers.** Our 12 checker scripts are custom Python. Registering them as pre-commit hooks would give us: caching (don't re-run on unchanged files), parallel execution, auto-update (pre-commit autoupdate), and a standard interface. This is a YAML file + `pip install pre-commit`, not a rewrite.

**THE ANTI-IMPORT:** **OPA.** External policy engine for hooks that fire on every tool call. The latency of calling an external service on every Claude Code action would be noticeable. Python-in-process policy is faster and sufficient.

**STATUS:** LIVE. 7 hooks in `scripts/hooks/`, 12 checkers in `scripts/checkers/`. Hooks fire on Claude Code actions. Checkers run in CI (currently red — 31 failures with ~4 REAL). PreToolUse recall injection is on by default.

---

### 24. Autopilot (autopilot_a1.py, fleet/)

**WHAT IT DOES:** Presence autopilot that supervises the fleet. Crash backoff, circuit breaker, presence held through Redis outages. Refuses to steal a running session's seat. First live launch proved the safety property by REFUSING to steal a running session's seat, twice, with legible reasons.

**CONNECTED TO:**
- Reads from: `liveness.py` (agent presence), `runner_lock.py` (seat ownership)
- Writes to: `launcher.py` (restart decisions)
- Pins: `test_autopilot_a1.py`

**COMPARABLE SYSTEMS:**
1. **Kubernetes controllers** — reconcile loop: observe desired state, observe actual state, take action to converge. Our autopilot IS a basic controller.
2. **systemd restart policies** — Restart=on-failure, RestartSec, StartLimitBurst. Our autopilot has backoff; systemd has more configurable policies.
3. **Erlang supervisors** — restart strategies (one-for-one, one-for-all, rest-for-one). Our autopilot restarts one agent at a time.

**THE DELTA:**
- Kubernetes: declarative desired state. Our autopilot observes and reacts but has no "desired state" manifest — it infers desired from what was running.

**THE IMPORT:** **Declarative fleet manifest.** A YAML file: `fleet: { agents: { deepseek: { runner: ..., desired: running }, kimi: { ... } } }`. The autopilot reads it and converges. This makes "bring the fleet up" a single command that works idempotently. Currently, each runner is launched manually.

**THE ANTI-IMPORT:** **systemd unit files for every agent.** OS-level service management for a development fleet. Keep the Python autopilot; add systemd as optional production config.

**STATUS:** LIVE. `core/fleet/` directory. Crash backoff, circuit breaker, no seat stealing. No declarative manifest.

---

### 25. Guards (guards.py)

**WHAT IT DOES:** Write-time guards. `guard_write(path, content)` enforces: path is in the allowlist, file is git-tracked, agent owns the lock, content passes integrity checks. The guarded execution door in `toolbox.py` calls these.

**CONNECTED TO:**
- Used by: `toolbox.py` (edit_file, write_file verbs), UNVERIFIED — mirror.py pre-commit path
- Reads from: `locks.py` (lock ownership), `capabilities.py` (agent permissions), git (tracked status)
- Configured by: builder allowlist (`research/**, scratch/**, tests/**, ...`)

**COMPARABLE SYSTEMS:**
1. **OPA admission control** — policy evaluation before mutation. Our guards ARE admission control. OPA would externalize the rules.
2. **GitLab/GitHub protected branches** — require approvals, CI passing, specific reviewers. Our guards are file-level; protected branches are branch-level.
3. **AWS IAM condition keys** — `s3:PutObject` allowed only if `s3:x-amz-acl` is `bucket-owner-full-control`. Our guards check multiple conditions (locked? tracked? allowed?).

**THE DELTA:**
- Protected branches: branch-level policy. Our guards are file-level; we have no branch-level protection (anyone can push to main if they have commit access).

**THE IMPORT:** **Already well-designed.** The guard system is layered (lock→tracked→allowlist→integrity) with fail-closed defaults. The builder allowlist is explicitly scoped. No major gaps found.

**THE ANTI-IMPORT:** **OPA for guards.** Same as hooks — external policy evaluation on every write would add latency. In-process guards are correct.

**STATUS:** LIVE. `agent/harness/guards.py` (2KB file, imports larger modules). The guarded write door is the primary consumer.

---

## FLEET SUMMARY (what exists, quick audit)

- **Runners:** `bifrost_runner_deepseek.py`, `bifrost_runner_kimi.py`, `bifrost_runner_sol.py` — each is a Python loop that polls the bus, processes messages, and replies. DeepSeek runner is the most mature (34-verb ToolBox, guarded execution, fence).
- **Wake watcher:** `bifrost_wake.py` — blocks on the bus until mail arrives, then exits for the runner to consume. Fixed tonight (hot-spin → 0% CPU).
- **UI:** `bifrost_ui.py` — Flask-based fleet dashboard with console, lane depths, presence. Port 8787.
- **Autopilot:** `autopilot_a1.py` — supervision with crash backoff and circuit breaker.
- **Daemon supervisor:** `test_t086_s5_daemon_supervisor.py` — process supervision drills. The daemon itself may be in `launcher.py`.

### COMPARABLE: Erlang/OTP Supervision Trees

**THE DELTA:** Erlang supervisors have restart strategies (one-for-one, one-for-all) and escalation (if a supervisor can't recover, its parent tries). Our supervision is ad-hoc — the autopilot restarts agents but has no strategy hierarchy or escalation.

**THE IMPORT:** UNVERIFIED. Our fleet is small (4 agents). Erlang-style supervision trees solve problems at 100+ processes that we don't have. Revisit when the fleet grows.

**THE ANTI-IMPORT:** **Rewriting in Erlang/Elixir.** A platform migration for supervision benefits that a 4-process fleet doesn't need.

### COMPARABLE: Kubernetes Controllers and the Reconcile Loop

**THE DELTA:** K8s controllers continuously reconcile: observe → diff → act. Our autopilot observes and reacts but has no continuous reconciliation — if the autopilot itself crashes, no one restarts the restarters.

**THE IMPORT:** **Reconcile loop in the autopilot.** A single `while True: observe(); diff(); act(); sleep(5)` loop would make the autopilot a proper controller. It already has the pieces; they just need to be wired into a loop.

**THE ANTI-IMPORT:** **Kubernetes.** Cluster management for a single-machine fleet.

---

## REMAINING AREAS (inventory only for now)

- **core/recall/** (at_action, ranker, funnel, curator, forge, knowledge_map, lookback, anchors, replay) — the recall system. Census filed in `scratch/recall-census-2026-07-26.md`.
- **core/learning/** (learning_store, agent_memory, consolidation, loader) — the lesson CRUD and dedup.
- **core/narrative/** (beat_log, chronicler, schema, tag_governance, tag_audit, episode, session) — the narrative spine.
- **core/library/** (atoms, projection, taxonomy) — the artifact-atom family.
- **core/primitives/** (ranker, faithfulness, clusterer, embedder, distiller, consolidator, supersession, etc.) — the shared algorithmic primitives.
- **core/renew/** (session_signals) — session lifecycle signals.
- **core/signals/** (coordinator_api) — coordinator signal interface.
- **core/perspectives/** (reinforce) — perspective tracking.
