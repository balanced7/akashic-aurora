---
akashic_id: art_20260716_multi-agent-failure-mode-foresight-n-3-1_0b38cd
akashic_sha: e05c3c01881d
status: draft
type: report
date: 2026-07-16
title: "Multi-Agent Failure-Mode Foresight — N=3..10, blind half"
gist: "# Multi-Agent Failure-Mode Foresight — N=3..10, blind half **Author:** deepseek-review (the fleet's newborn review seat, acl member grant) *"
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, identity, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-16T20:51:03"
updated: "2026-07-16T20:51:03"
---
<!-- GENERATED PROJECTION of art_20260716_multi-agent-failure-mode-foresight-n-3-1_0b38cd -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Multi-Agent Failure-Mode Foresight — N=3..10, blind half

# Multi-Agent Failure-Mode Foresight — N=3..10, blind half

**Author:** deepseek-review (the fleet's newborn review seat, acl member grant)
**Date:** 2026-07-16 evening
**Status:** FOR DANIEL'S MORNING GATE — my independent (blind) half of the dual-blind foresight exercise
**Directive:** Daniel verbatim in `multiagent-foresight-directive`: forecast failure modes for multi-agent runs BEFORE they bite, and identify the infrastructure gaps to close before scaling

---

## 0. The evidence base — what 2 agents already broke

The failure ledger (`docs/failure-ledger-2026-07.md`) is a catalog of what broke with TWO agents. Extrapolate to N:

| Category | 2-agent receipts (sampled) | N-agent multiplier |
|----------|--------------------------|---------------------|
| **C1 Seat & lease lifecycle** | Ghost wake seat (C1-5, ~30 min unwakeable); dead-holder rescue (C1-1); wake-arm insta-loop (C1-2); redelivery storms (C1-4); runner context loss on interrupt (C1-3) | **Quadratic**: each new agent adds new lease pairs, new ghost paths, new redrive sources |
| **C2 Concurrent-write collisions** | Test-file clobber (C2-1, silent); exec-family denial blocking commits (C2-2); big-write truncation (C2-3) | **Combinatorial**: N writers, M hot files → N×M collision surface; advisory-lock `list_locks()` scans O(keyspace) at `SCAN` cost |
| **C3 CLI ergonomics** | Text-before-flags footgun (C3-1); PowerShell cwd resets (C3-2) | Linear in seats — every new agent hits the same footguns once |
| **C4 Process/launcher state** | UI launcher lost track of a live runner after UI restart (C4-1) | **Quadratic**: launcher tracks N children; UI restart orphans N mappings |
| **C5 Ledger state machine** | PARKED task blocked a done-transition (C5-1, now fixed) | Linear — one ledger, one state machine; the fixed PARKED status handles the general case |
| **C6 Message/lane integrity** | Unread-count drift (C6-1, closed); runner reply landed legacy-only (C6-2, fixed); piped gate exits swallow failures (C6-3, closed) | **Quadratic** on dual-write: N agents × 2 streams per message = 2N writes per message; the echo amplification is N×(N-1)×2 |
| **C8 Cross-surface rendering** | PreToolUse hook double-fires inflating the funnel gauge (C8-3); boot trim names CLI commands a runner can't use (C8-1) | Linear in surfaces — each agent door type adds a rendering fork |

The core finding: **our liveness is forensic, not maintained** (T086 reconciliation thesis). At N=2, the TTL/grace ladder takes minutes; at N=10, every seat-claim attempt races every other seat's expiration, and the retry thundering herd compounds. This is the scaling ceiling.

---

## 1. Envisioned failure modes for N-agent runs

For each: trigger condition, blast radius, earliest detectable signal, and whether TODAY's machinery contains it.

### FM-1: Seat-claim thundering herd (C1 × combinatorics)

**Trigger:** N agents all restart simultaneously (daemon restart, host reboot, overnight window). Every consumer seat is TTL-expired; every agent's `claim_consumer()` races the same Redis NX key. One wins per agent-id; the other N−1 degrade to peek and retry. With grace=300s, a losing agent retries in a loop — and at N=10, 10 agents × 10 retry loops = 100 concurrent Redis probes per cycle, every 20s (standby retry interval).

**Blast radius:** Redis CPU saturates on NX contention; bus latency climbs; wake listeners false-trigger on the latency jitter; the fleet enters a slow-motion livelock where everyone peeks, no one consumes, and the retry drain prevents any agent from settling into productive work. At enough contention, the leader-fencing `generation` INCR itself becomes the bottleneck — every claim attempt mints a generation, and the losing ones are wasted.

**Earliest signal:** `doctor` shows all seats in "peek (seat held by X)" with holder TTLs counting down; consume latency spikes across the board before the TTL expires. The `_next_token()` INCR rate climbs from ~1/min to ~N/sec.

**Today's machinery:** `runner_lock.free_if_dead` with the T086-S2a renewal-staleness fast-path mitigates the *recovery* side (stale holders free in seconds, not 30 min), but the *thundering herd at claim time* is unmitigated. REDIS NX is atomic but the retry shape is a tight poll. **Missing: randomized exponential backoff on claim failure + a "standby queue" where one agent arms per agent-id and the others sleep longer.**

### FM-2: Echo amplification — dual-write × N agents (C6 × combinatorics)

**Trigger:** Any broadcast message. Today: one `send(to='*')` writes 1 legacy + 1 lane copy per recipient lane — but the lane broadcast key (`bifrost:work`) is shared, and the work lane `MAXLEN` (10000) is per-stream. At N=10, a single broadcast generates 1 broadcast lane entry × 1 read by N agents = N deliveries. That's fine. The problem is the **reply amplification**: a broadcast that triggers a reply from each agent generates N directed replies × 2 writes each (legacy + lane) = 2N writes. The lane inbox keys are per-agent (1 each), so storage is linear — but the *total Redis write throughput* is 2N² for a broadcast→all-reply cascade.

**Blast radius:** At N=10 with moderate chat volume (~5 broadcasts/min, each getting ~5 replies), the sustained Redis write rate hits ~250 writes/min from traffic alone — before any telemetry (trace lane). The trace lane is shared (one ring), so N agents generating thinking/tool traces compete for one `MAXLEN=5000` ring; at N=10 the ring turns over rapidly, and useful traces evaporate before any human reads them. The dual-write soak (T039a/T044) multiplies every packet — the lanes PREDATE the N-agent design and assume 2–3 writers. **The dual-write retirement (T047) becomes URGENT at N≥5 — it's no longer a soak, it's a capacity drain.**

**Earliest signal:** `BIFROST_CONSUME_LANE=work` agents report "LEGACY STRAGGLER(S)" on stderr at rising frequency — the dual-write window races widen under Redis load. Trace lane MAXLEN evictions visible in `XLEN bifrost:trace` declining even as agent count rises (the ring is full, older traces are trimmed).

**Today's machinery:** Lane isolation (T039a) works correctly per-agent but the dual-write × N combination is untested. The trace lane shared ring was designed for 1–2 agents. **Missing: per-agent trace lanes or a MUCH larger trace ring; T047 legacy retirement; broadcast reply storm detection (rate-limit broadcast replies from the sender door).**

### FM-3: Advisory-lock scaling collapse (C2 × combinatorics)

**Trigger:** N agents all editing files concurrently. `LockManager.list_locks()` scans `bifrost:lock:*` with `SCAN` — O(keyspace), not O(locks). At N=10 with 3–5 locks each, the keyspace has 30–50 lock keys. `SCAN` is cursor-based and Redis-side but each `list_locks()` call does N round-trips for ~1/N of the keyspace. The `guard_write()` pattern (proactive lock claim before every edit) is called on EVERY write — at high writer counts, the lock claim itself becomes a Redis round-trip per edit.

**Blast radius:** Write latency rises linearly with lock count as `SCAN` throughput competes with `acquire()` NX sets. Worse: the fencing-token `_next_token()` (global INCR on `bifrost:lock:_seq`) becomes a contended key — every `acquire()` on a NEW path hits that INCR. At N=10 with 5 new-file writes per minute, that's 50 INCRs/min on one key — hot, but not catastrophic. The real failure is the **discoverability gap**: at N=10, `list_locks()` returns 30 entries — no agent reads them all (the boot context is already budget-constrained at 6000 chars). An agent editing a file that's *about to be locked by a peer* has no pre-claim signal stronger than "call `list_locks()` and scan visually." The model won't.

**Earliest signal:** `list_locks()` latency climbs past 50ms; boot's lock list is truncated by the relevance budget; a C2-1-style clobber happens again but at N≥5 the collision is between TWO agents who each held the lock at different times within the same 60s window (lock TTL outlives the edit).

**Today's machinery:** `path_conflict()` is a point-check before one write; `guard_write()` claims proactively. The `list_locks()` SCAN is unbounded. **Missing: lock-count gauge + SCAN-to-KEYS migration threshold; a bus-level lock-change event so agents learn about new locks without polling; per-agent lock budget (an agent holding >5 locks is a signal).**

### FM-4: Operator-visibility collapse (cross-cutting)

**Trigger:** Daniel runs 3+ agents and asks "what is everyone doing?" Today: `py agent_cli.py doctor` shows presence + vitals; the UI dashboard shows lane depths. At N=3, the doctor output shows 3 agents with seat status, lease age, and pending counts — readable. At N=10, the doctor output is 10 sections × ~8 lines each = 80 lines. The dashboard's `bifrost_dashboard` text summary grows linearly. The task ledger has 10 agents claiming/filing — the "who owns what" question requires cross-referencing the ledger with the incarnation cards.

**Blast radius:** An operator cannot answer "is the fleet healthy or stuck?" in under 30 seconds at N≥7. The W4 trace-collapse rendering collapses per-agent traces — but the fleet-level summary has no equivalent. A stuck agent (C1-3: runner lost context) is one line in an 80-line doctor output; it's invisible. The operator loses the ability to detect anomalies at a glance.

**Earliest signal:** Daniel asks "what is everyone doing?" and the answer is a wall of text. Doctor output crosses 60 lines.

**Today's machinery:** Doctor exists (T081-W7 `bifrost_dashboard`), incarnation cards exist (T074-P3), the UI has agent cards. **Missing: a fleet-level HEALTH SUMMARY that answers "are all agents progressing?" in one line — reachable/progressing/stuck counts, oldest worklive age, any seat in peek mode. A "fleet is GREEN / YELLOW / RED" top-line verdict derived from those gauges.**

### FM-5: Cross-agent trust-boundary erosion (ACL × N)

**Trigger:** The fleet grows from 3 agents (claude super-admin, deepseek admin, deepseek-review member) to N where N−3 are NEW agent identities provisioned by non-super-admin agents, or by a script that reuses templates. The ACL (`security/acl.json`) has 6 grants today; at N=10 it will have 10+ grants, each with `caps`, `path_scope`, `bus_send_kinds`, and `reason`. A copy-paste error — granting `admin.approve` to a member, or omitting `path_scope` restriction on a build agent — is a one-character diff in a JSON file with no schema enforcement beyond the human reviewer.

**Blast radius:** A build agent with accidental `admin.grant` can escalate its own role; an agent with `path_scope: ["*"]` when it should have `["research/*"]` can write to `security/acl.json` itself — the crown-jewel self-escalation. Worse: at N=10, the grant `reason` strings become the ONLY documentation of WHY an agent has its caps — and they're free-text, not validated. A grant with reason "temp escalation for T099 build" that isn't revoked becomes a permanent backdoor.

**Earliest signal:** `security/acl.json` diff shows an unexpected `admin.*` cap on a non-admin agent. The `_comment` header says "source of truth" but there's no CI check that validates the file against a schema. A `git diff security/acl.json` in the morning gate catches it — but only if Daniel reads it.

**Today's machinery:** `core/trust/registry.py` reads the ACL; `core/trust/capabilities.py` enforces at the door. The enforcement WORKS — an agent without `admin.grant` cannot grant. But the *provisioning* (who grants what to whom) has no guardrail beyond the super-admin's judgment. **Missing: ACL schema validation (CI gate that refuses invalid caps, missing path_scope, or a grant that escalates beyond the grantor's own caps); a "least-privilege" default (new agents start with NO caps unless explicitly granted); grant expiry (all non-super-admin grants require an `expires_at` or auto-revoke).**

### FM-6: Cost runaway — N concurrent API agents (economic)

**Trigger:** N agents, each with its own API key/seat, all running concurrently. Today: deepseek has a `MAX_TOKENS` setting but no per-task or per-session dollar cap. Claude's session has no cost gauge. At N=10, if 3 agents enter a wake-loop (C1-2 shape: arm→wake→empty→re-arm), each burns tokens on an empty turn every ~20s. That's 3 × 3 × 60 = 540 empty turns per hour, each costing a model round-trip.

**Blast radius:** A single stuck agent can burn $5–20/hr on empty turns. A redelivery storm (C1-4) where an agent re-processes 500 stale handoffs burns ~500 turns × (context + reasoning) tokens. At N=10, if 2 agents simultaneously hit redelivery storms, the combined token burn is $20–50 in a single hour, silently. The operator has no cost gauge — the first signal is the API bill.

**Earliest signal:** `worklive` phase shows "idle" but the agent keeps consuming (empty turns). A `doctor` or dashboard gauge that reports "tokens this session" would catch it; today nothing reports token consumption at the fleet level.

**Today's machinery:** `MAX_CMD_TIMEOUT` and hop budget limit tool-call waste, but the model's own token consumption (the LLM turn itself) is unmeasured. **Missing: a per-session token counter (the runner/harness tracks input+output tokens per turn, aggregated to session and fleet); an empty-turn detector (N consecutive turns with zero tool calls → alarm); a per-agent daily cost soft-cap with a bus warning when approaching it.**

### FM-7: UI legibility collapse — the human surface at N agents

**Trigger:** The Bifrost UI (`scripts/bifrost_ui.py`) renders agent cards, message streams, and trace decks. At N=2 (claude + deepseek), the UI has ~4 agent cards (including standby/wake processes). At N=10, there are 10+ agent cards, each with live trace streams, thinking blocks, and tool traces. The SSE stream pushes N× the event volume. The browser's DOM has 10× the nodes.

**Blast radius:** The UI becomes unresponsive (SSE saturation), agent cards stack below the fold (scrolling to find one agent), the trace-collapse feature (T002) collapses per-agent but the *interleaved multi-agent trace stream* is a visual spaghetti. An operator trying to follow ONE agent's work scrolls past 9 other agents' trace cards.

**Earliest signal:** Browser tab memory climbs past 500MB; SSE event rate exceeds 10/sec; "scroll to find agent X" takes >3 seconds.

**Today's machinery:** W4 trace collapse (consecutive same-agent dedup), T002 UI collapse (in progress, deepseek-claimed). The shared `render_collapsed` works. **Missing: agent-filter toggle (show/hide per-agent traces in the UI); fleet-summary bar (green/orange/red); per-agent trace ring buffer in the UI so old traces don't accumulate in DOM.**

### FM-8: Identity/naming collision at scale

**Trigger:** Two agents register with the same or confusingly similar `agent_id`. Today: the ACL is the source of truth for agent identities. `runner_lock.acquire()` keys on `agent` string — two processes claiming `deepseek` race the NX lock. But what about a NEW agent id that collides with a bus stream key? The stream keys are `bifrost:work:inbox:<agent>` — if agent_id contains `:` or `*`, it creates ambiguous keys.

**Blast radius:** An agent_id of `deepseek-build` and another of `deepseek` share no prefix collision in the current key scheme, but an id like `deepseek:worker` would collide with the `:`-delimited lane key structure — `bifrost:work:inbox:deepseek:worker` is ambiguous (is `worker` a sub-agent or a lane dimension?). Worse: the incarnation card keys (`bifrost:incarnation:<agent>:<sid>`) embed the agent_id verbatim. A `:` in the agent_id breaks the key parser.

**Earliest signal:** A new agent provisioned with `:` or `*` in its id fails to consume (stream key doesn't match what the sender wrote) or its incarnation card key collides with another agent's.

**Today's machinery:** No agent_id character validation exists. The ACL accepts any string. `runner_lock._key()` sanitizes nothing. **Missing: agent_id naming rules (RFC: alphanumeric + hyphen only, max 32 chars, enforced at ACL provisioning and at runner start); a name-collision check at `acquire()` time.**

---

## 2. Top 8 ranked by (likelihood × cost)

| # | Failure mode | Likelihood | Cost | Existing containment | Missing slice |
|---|-------------|-----------|------|---------------------|---------------|
| **1** | **FM-2: Echo amplification** (dual-write × N, trace ring saturation) | HIGH — dual-write is ON, trace ring is 5k, T047 not yet shipped | MEDIUM — Redis saturation degrades the whole bus; trace loss hides real issues | Lane isolation (T039a), MAXLEN caps, T047 planned | **T047 LEGACY RETIREMENT as a gated slice BEFORE N≥5; per-agent trace lanes or ring scaling; broadcast-reply rate limiter** |
| **2** | **FM-1: Seat-claim thundering herd** | HIGH — every fleet restart hits it; grace=300s makes the window long | HIGH — fleet-wide unavailability for minutes after restart | T086-S2a fast-free, generation fencing | **Exponential-backoff on claim retry; standby queue (one contender per agent-id, others sleep); claim-attempt gauge** |
| **3** | **FM-4: Operator-visibility collapse** | HIGH — linear in N, no fleet summary exists | HIGH — operator cannot answer "is the fleet healthy?" in under 30s | Doctor, dashboard, incarnation cards | **Fleet health summary: one-line GREEN/YELLOW/RED verdict; reachable/progressing/stuck counts; oldest worklive age** |
| **4** | **FM-5: Trust-boundary erosion** | MEDIUM — requires a provisioning mistake, but at N=10 the review surface is 10 grants | CRITICAL — self-escalation to super-admin is a one-line diff | `core/trust/` enforcement works; ACL is git-tracked | **ACL schema CI gate; least-privilege default for new agents; mandatory grant expiry; grantor-cap check (can't grant what you don't have)** |
| **5** | **FM-3: Advisory-lock scaling** | MEDIUM — requires concurrent writers on hot files, but N≥5 makes this routine | MEDIUM — write latency climbs, lock discoverability drops | `guard_write()`, `path_conflict()`, fencing tokens | **Lock-change bus events (pub/sub on lock acquire/release); per-agent lock budget; SCAN-to-KEYS migration** |
| **6** | **FM-6: Cost runaway** | MEDIUM — wake-loops and redelivery storms are documented failure classes at N=2, N≥5 amplifies | HIGH — silent API spend with no gauge until the bill arrives | Hop budget, MAX_CMD_TIMEOUT; no token counter | **Per-session token counter; empty-turn detector; fleet cost gauge; per-agent daily soft-cap with bus alert** |
| **7** | **FM-7: UI legibility collapse** | MEDIUM — SSE event volume scales linearly; browser DOM accumulates | MEDIUM — operator tool becomes unusable, forcing CLI-only monitoring | W4 trace collapse, T002 in progress | **Agent-filter toggle in UI; fleet-summary top bar; per-agent DOM ring buffer** |
| **8** | **FM-8: Identity/naming collisions** | LOW — requires a deliberate bad name, but the damage is silent and hard to debug | HIGH — key-space collision breaks consume paths silently | None | **agent_id naming rules (alphanumeric + hyphen, max 32); validation at ACL provision + runner start** |

---

## 3. Immediate do-now items (the three that gate N≥3)

1. **T047 legacy retirement.** The dual-write IS the N-agent scaling tax. Every message pays 2× Redis writes; at N≥5 the tax is >50% of Redis throughput. Retire legacy (T047) and the tax vanishes. This gates ALL other scaling work — fixing echo amplification while dual-write persists is treating a symptom.

2. **Fleet health summary.** Before Daniel launches a 5-agent run, `py agent_cli.py doctor` needs a one-line verdict: "FLEET: GREEN — 5/5 progressing, oldest stall 12s." This is ~50 lines of Python (aggregate worklive ages, count stuck, derive color). Without it, Daniel flies blind at N≥3.

3. **ACL schema CI gate + least-privilege.** Add a `check_acl_schema.py` that runs at pre-commit: every grant has valid caps, path_scope covers the caps (write→non-empty path_scope), no agent grants caps beyond its own, expires_at is set for non-super-admin grants. Fail-closed. This is ~100 lines and prevents the one-class self-escalation.

---

## 4. The "ready for N=3 today" assessment

With the T086 seat-lifecycle fixes (S1 tombstone + S2a renewal-staleness fast-free), the fleet CAN run N=3 right now. The C1-5 ghost-seat class is structurally closed; a dead holder frees in seconds. The lane consume path (T045 stage 2) handles per-agent inboxes correctly. The advisory locks (C2) work at N=3. What WILL happen:

- **At restart:** A brief (5–15s) seat-claim contention window as agents race the NX lock. Tolerable at N=3; unacceptable at N=5.
- **Under load:** Dual-write legacy stragglers (already seen at N=2) will rise. The `work_drain` prints them to stderr — loud but not blocking.
- **Operator view:** Doctor + dashboard will be readable at N=3. The first sign of FM-4 (visibility collapse) appears at N=5.

**Gate recommendation:** N=3 is safe tonight for the foresight exercise itself (claude + deepseek + deepseek-review). N≥5 needs items 1–3 above shipped first.

---

## Appendix A: Newborn onboarding friction (deepseek-review boot observations)

*Per the directive: "your boot/onboarding friction observations are THEMSELVES valuable."*

### A1 — Boot trim block is 6000 chars, but the dropped content matters

My onboarding trim block says `[onboarding TRIMMED at its 6000-char budget. DROPPED: RECENT DECISIONS...]`. The dropped sections include: RECENT DECISIONS (durable salient bus), DOCTOR (fleet liveness), TO CONTRIBUTE A LESSON. As a newborn review seat whose FIRST task is fleet foresight, the `DOCTOR` drop is material — it contains the fleet liveness instructions that would help me assess the current fleet. The trim confesses what it dropped (`[onboarding TRIMMED... DROPPED: ...]`) which is better than silence, but the dropped section names are a tease.

**Observation:** The boot's relevance budget (T071-R1) correctly prioritizes task-relevant lessons, but the trim block's hard 6000-char cap drops structural orientation (DOCTOR, BIFROST) that every agent needs regardless of task. A split: structural boot (always included, ~1500 chars) + task-scoped boot (budgeted, remaining ~4500 chars).

### A2 — `delta` returns "no mark yet (newborn)" — correct but sparse

My first `delta` call returned "no mark yet (newborn) -- the mark writes at your next boot; until then the full boot is the orientation." This is correct behavior (I have no prior mark), but it means my ONLY source of "what changed since I was last here" is the full boot — which is truncated. A newborn agent should get a one-time "here's the last 24h of commits + ledger transitions" as a substitute delta.

### A3 — The `knowledge_recall` surface works well; the truncation confesses

My recalls returned truncated bodies (e.g., the messy 256-char `actual` field for `dup_exp`), but the source pointer (`learn:experiment:NAME`) is always present so I can `knowledge_full()` to get the real body. The system prompt's instruction `knowledge_full()` is the one-hop escape, and it works. Good design.

### A4 — C8-1 is still live: the trim block tells me to run `py agent_cli.py doctor`

My boot says: "DOCTOR (fleet liveness -- full: py agent_cli.py doctor)." I am a ToolBox-door agent. I cannot run `py agent_cli.py doctor` without going through the exec-family gate (which allows agent_cli READ verbs, so it WOULD work). But the ToolBox-native tool for this is `bifrost_dashboard` — and the trim block doesn't tell me that. C8-1, still open, confirmed from a newborn seat.

### A5 — Exec-family gate: my `run_command` works for pytest and agent_cli reads

The ACL grants me `exec` capability; the `_exec_family` gate allows pytest + agent_cli READ verbs + IR-4 mirror. My `write_file` above (this report) succeeded — I have `write` cap scoped to `research/*`. The path-scope enforcement is ADVISORY per my ACL grant reason ("path_scope ADVISORY until S-2 enforcement") — but it's still the runtime that enforces it. I trust it.

### A6 — No private notes survived (newborn) — but I should leave one

I'm the first agent besides claude and deepseek. I'm filing a `memory_note` with my working observations so my next boot has continuity.

---

## Appendix B: The ACL review (Daniel's gate item)

Per the directive: "review deepseek's exec grant (security/acl.json)."

### deepseek's grant assessment

- **agent_id:** `deepseek`, role: `admin`
- **caps:** `read write exec bus.send bus.nudge bus.steer kb.recall kb.learn net git.read bifrost.inbox`
- **Withheld:** `admin.grant`, `admin.approve` — correctly, so deepseek cannot escalate others
- **path_scope:** `["*"]` — full filesystem write; this is correct for an `admin` build agent that needs to write to `core/`, `scripts/`, `tests/`, etc.
- **exec justification:** The `reason` field documents the entire chain: T067-2 guarded exec (families-only, shell=False, metachar refusal) → IR-4 audited mirror (canonical script path, explicit paths, no flags, security/ + .claude/ excluded). The exec family list (`scripts/deepseek_chat.py:_exec_family`) is the actual enforce point.
- **bus_send_kinds:** `["chat", "note", "request", "reply", "nudge", "steer", "inform", "hint", "handoff", "completion", "decision", "blocker"]` — comprehensive, includes `nudge` and `steer` (needed for peer coordination) and `blocker` (needed to raise issues).

**Verdict: APPROPRIATE for an admin build agent.** The exec grant is safe-by-construction (families-only), the mirror family is audited (paths visible, one-command revert), and the withheld `admin.grant` prevents escalation. No changes recommended.

### deepseek-review's own grant assessment (self-review for completeness)

- **agent_id:** `deepseek-review`, role: `member`
- **caps:** `read write exec bus.send kb.recall kb.learn git.read bifrost.inbox`
- **Withheld:** `bus.nudge`, `bus.steer`, `net`, `admin.*` — correctly for a review seat
- **path_scope:** `["research/*", "scratch/*", "docs/*"]` — scoped; this report lands in `research/reviewed/` which is within scope
- **exec:** Same families gate as deepseek; allows pytest for pin verification
- **bus_send_kinds:** `["chat", "note", "request", "reply", "handoff", "completion", "inform"]` — no `nudge`/`steer` (review seat doesn't interrupt builders), no `blocker` (escalates via handoff to claude)

**Verdict: CORRECT for a review seat.** The path_scope restriction is appropriate; exec through families gate only; no control-plane bus verbs.

### ACL-wide observation

The `deepseek-ui` grant has `path_scope: []` — an empty list. This means "no filesystem write paths" which is correct for a UI design consultant. But the schema doesn't distinguish between `[]` (intentional no-write) and `null`/absent (forgot to set). A schema that normalizes `path_scope` would help.

---

*End of report. Filed blind; claude's half was not consulted. Bus-replying claude with the top-3 summary now.*
