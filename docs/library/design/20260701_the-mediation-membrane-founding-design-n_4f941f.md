---
akashic_id: art_20260701_the-mediation-membrane-founding-design-n_4f941f
akashic_sha: 86864d0d666a
status: current
type: design
date: 2026-07-01
title: The Mediation Membrane — founding design note (2026-07-06)
gist: "Daniel's intuition: *\"Akashic is only useful if it's used by the right things at the right time. There needs to be a substrate that mediates"
tenant: solo
visibility: fleet
seats: []
category: [substrate, recall, memory]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260707_renew-strand-a-cheap-deterministic-conte_6eba11
    rel: cites
  - target: art_20260707_renew-prior-art-grounding-research-item_4548c5
    rel: cites
created: "2026-07-09T23:27:59"
updated: "2026-07-23T21:42:04"
---
<!-- GENERATED PROJECTION of art_20260701_the-mediation-membrane-founding-design-n_4f941f -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# The Mediation Membrane — founding design note (2026-07-06)

Daniel's intuition: *"Akashic is only useful if it's used by the right things at the right time. There
needs to be a substrate that mediates between the agents and Akashic to reduce the cognitive load of
being in this space — and we must balance adherence + auto-logging against maintainability and instant
skeleton retrieval."* This note grounds that intuition in what already exists and names the thing.

## The reveal: the membrane already exists as the HOOK LAYER (half-built)

The need was diagnosed a year ago (`agent-interface-aci.md`, `agent-experience-plan.md`,
`directive-friction-audit.md`, `integration-tiers.md`) and **half-built**. The membrane is the set of
runtime hooks that, for Claude Code, already fire ambiently: PreToolUse (recall-at-action, FAITH-gated),
PostToolUse (FAIL→SUCCESS outcome credit), UserPromptSubmit (bus-sync + top lessons), SessionStart
(light boot). The agent doesn't invoke these — they mediate *around* it. **We are further along than it
feels; the job is to NAME the membrane, finish the deferred half, and unify the door.**

## The membrane's four jobs (and the ground truth of each)

| Job | Wired today | Gap |
|-----|-------------|-----|
| **Surface** — the right context at the moment of action | recall-at-action via PreToolUse (Claude Code); FAITH-1 gate | Cursor is one-beat-late; bare CLI manual. Surfaces lessons, **not the skeleton/map** (orientation). |
| **Capture** — auto-log what's salient | session lifecycle + outcome credit auto-emit | **lessons/notes still 100% manual**; auto-draft from FAIL→SUCCESS deferred. Must gate on SALIENCE, not frequency. |
| **Enforce** — auto-adherence to what matters | boundary + doc-freshness guards (CI) | comprehensibility guard not in CI; **`check_wiring.py` (Built≠Wired gate) does not exist** — latent capability accumulates silently. |
| **Unify** — one coherent door | agent_cli (33), MCP (22), bus API (18) all exist | **THE biggest load: 3 unsynchronized doors, no parity test.** 11 CLI verbs have no MCP twin; bus verbs exposed nowhere but a direct import. |

Quantified load today: ~4 entry surfaces, ~33 verbs, ~5 workflows, ~8 conventions ≈ **~50 things an
agent must internalize**. The door fragmentation is the heaviest chunk.

## The three tensions → the membrane's design axes
- **auto-logging ↔ maintainability** → Capture at **salience** (weight-gated), funnel prunes. *Principle 7.*
- **adherence ↔ maintainability** → **guard what matters, nudge the rest.** The missing `check_wiring.py`
  is itself the maintainability guard (catches built-but-unwired). *Principle 4.*
- **skeleton instant retrieval** → extend **Surface** from lessons to **orientation** (inject the
  ARCHITECTURE/LEXICON slice for the subsystem an agent touches).

Two prior decisions snap in: **hats** = the ultimate load-reducer (see only your slice); the membrane is
**stigmergic** (hooks shape an ambient environment the agent reads, not a system it must query — Principle 8).

## What's real / deferred (verified against code, not docs)
- ✅ Wired: recall-at-action (Claude Code), session auto-capture, outcome credit, FAITH-1 gate, boundary
  guards (CI), identity fail-closed, integration-tier honesty.
- ⏸️ Deferred: door unification + `test_door_parity.py`; write-once projector (MEMORY.md auto-rerender);
  **`check_wiring.py`**; auto-drafted lessons; membrane parity for Cursor/bare-CLI; comprehensibility guard in CI.

## Proposed sequence (finish the membrane, heaviest-load first)
1. **Unify the door** — the biggest load. A single verb registry both CLI and MCP project from + a
   `test_door_parity.py` gate so they can't drift. (Bus verbs surfaced too, or explicitly scoped.)
   - **1a ✅ SHIPPED 2026-07-06 — door-parity guard.** `scripts/check_door_parity.py` makes the surface
     EXPLICIT (CLI 33 / MCP 22 / bus 18) and RATCHETS it: every verb classified (16 shared / 17 cli-only /
     6 mcp-only), fails on a new unclassified verb or a shared regression; wired into `ship.py`. Bus is a
     separate programmatic door (reported, not parity-enforced in v1). Stops new drift; freezes today's debt.
   - **1b ✅ COMPLETE 2026-07-06 — CLI↔MCP door debt paid down 12 → 0.** MCP twins added for
     `note, notes, lock, unlock, locks` (a shell-less/MCP-only agent can now record write-once decisions +
     claim advisory locks) and `tag_anti_pattern, bifrost_nudge`. The rest rationalized honestly:
     `list`/`fleet` = cli_only (CLI alias for `recall ""` / operator-oriented dispatch); `bifrost_broadcast`/
     `bifrost_inbox`/`bifrost_presence` = mcp_only (CLI covers via `bifrost-send --broadcast` / `bifrost-sync`).
     Every verb is now shared or intentionally single-door **with a documented reason**; guard verifies 0 gaps.
   - **1c (optional endgame) — one registry both doors project from,** so twins auto-generate and parity is
     structural, not a hand-written pair + a test. Bigger lift; deferrable — the ratchet already holds the line.
2. **Built≠Wired gate** (`check_wiring.py`) — ✅ **SHIPPED 2026-07-07.** Import-graph reachability from the
   production entry points (doors/runners/hooks/boot); flags `core/` modules that exist but run nowhere.
   Wired into `ship.py`; ratchets (fails on a NEW unwired module). **Surfaced 18 latent modules** frozen as
   a documented backlog: 14 **built-ahead** (codex, perspectives, the **conductor**+coord layer, narrative
   slices, fast_cache — wire when their consumer lands) + 4 **legacy** (`coordinator_service`,
   `redis_sync_coordinator`, `sync_reconciler`, `session_recovery` — deletion candidates for a boy-scout slice).
3. **Surface → orientation** — ✅ **SHIPPED 2026-07-07 (via Renew Strand E gap #2):** boot now carries an
   ARCH SLICE section (`context/arch_loader.py`, deterministic show-nothing-floored projection over
   ARCHITECTURE.md), inherited by both CLI+MCP doors. The original tool-boundary variant stays a
   possible refinement.
4. **Capture at salience** — auto-draft a lesson/note candidate from a FAIL→SUCCESS flip, weight-gated,
   human/agent confirms. Closes the manual-capture gap without corpus bloat.
5. **Hats** (Wave 3) — per-role context+permission scoping; the deepest load reducer.

None of this is greenfield — it's completing a diagnosed, half-built layer and giving it a name.

---

## Verified prior art (2026-07-06 — grounded via web search, not a hallucinated citation)

DeepSeek's prior-art streams are real (ambient-intelligence middleware; ACI + cognitive-load theory;
stigmergy; transactive memory) — but its cited paper *"The Synthetic Membrane: A Shared Permeable
Boundary"* **does not exist** (it conflated a GitHub tool named `membrane` + real "governed shared
memory" papers). Dropped. The strongest REAL prior art, classical and in active 2025 LLM revival:

- **Blackboard systems** (Hearsay-II) — the canonical shared-medium coordination pattern. 2025 LLM
  revival: *Terrarium* (arxiv 2510.14312), *LbMAS* (2507.01701), bMAS, "LLM Multi-Agent Blackboard"
  (2510.01285). The field independently states our stigmergy principle: *"all agent interaction is
  exclusively blackboard-mediated; agents neither message directly nor keep private histories."*
- **Tuple spaces / Linda** — generative communication, the archetypal shared medium between agents.
- **Transactive memory** (who-knows-what) · **ambient-intelligence middleware** · **ACI + cognitive-load
  theory** · **capability-based security** (the permeability gate).

**Our LEXICON already calls the Akasha Ledger a "blackboard."** We named the substrate correctly a year
ago; this is adoption of a validated paradigm, not a pivot.

### Concrete patterns extracted (from Terrarium + LbMAS) → design decisions

1. **Permeability is STRUCTURAL, never prompt-based.** Terrarium: prompt-instructed non-disclosure leaked
   at **100%**; the boundary must be enforced at the blackboard/factor-graph layer. → **A hat gates what
   an agent sees/writes at the ACL/door, never by instruction.** (= Principle 4, empirically confirmed.)
2. **A bounded, salience-gated medium is a SAFETY property.** Context saturation is a **100%-success
   availability attack**. → Retention limits + compression + salience-capture (Distiller, funnel) are
   *security*, not just the maintainability tension. Bounding the medium is non-negotiable.
3. **Coordination via a control-unit/Conductor improves quality AND cuts tokens ~3×** (LbMAS: +5% vs
   static MAS, 4.7M vs 13–17M tokens via selective agent activation). → Validates the Conductor +
   strength/latency-aware routing (G1); aligns with the token-frugality directive.
4. **The blackboard replaces agents' private memory** — pull context from shared state, don't carry it.
   → The membrane thesis (cognitive-load reduction), proven. **Public medium (Ledger) + private scratch
   (AgentMemory `mem:`)** — both already exist.
5. **Write-integrity: poisoning 1–3 messages caused misalignment.** → Provenance + fencing token + FAITH
   gate at the *write*, not trust. (Already designed.)

### The three-layer framing, now grounded
- **Medium** = Akasha Ledger/Store (the blackboard) — bounded + salience-gated (safety, per #2).
- **Permeability** = hats + capability ACL — enforced structurally at the door (per #1).
- **Mediation/Governance** = the hook layer + Conductor + guards — selective, cheap, audited (per #3).

Sources: arxiv 2510.14312 (Terrarium), 2507.01701 (LbMAS blackboard), 2510.01285, 2606.24535
(Governed Shared Memory).

---

## Renew — the membrane's temporal job (proposed 2026-07-07, from GPT dialogue)

The four jobs above all operate *within* a live session. There is a fifth that operates *across the
session boundary* — the compress-and-reload seam GPT named "context lifecycle management." It is **not a
new mechanism**: it is **Capture → Surface fired as a loop**.

> **Renew** — keep working context healthy over long-running work: detect cognitive debt → extract
> durable knowledge (*Capture*) → reload a curated working set (*Surface*).

This is the membrane closing its own loop. It does not reorder the sequence — it gives the two deferred
steps a shared telos (#3 Surface→orientation and #4 Capture-at-salience are the two halves Renew
stitches together) and adds one step (#6) + one new primitive.

### Already ~60% built (same story as the membrane itself)
| GPT's piece | Exists today as |
|---|---|
| "Save = extract durable knowledge, not a transcript" | `scripts/snapshot.py` + `wrap --commit` + `core/learning/consolidation.py` + narrative `beat_log→chronicler` + last-session-draft |
| "Relaunch with a curated working set" (Mission/Objective/Arch-slice/Modules/Lessons/Branch/TODOs/Decisions) | `agent_cli boot` (Context pillar) via `primitives/ranker.py` + `distiller.py` — the boot payload already *is* this, **minus the arch slice (= deferred step #3)** |
| Refresh triggers (task-transition / branch-switch / arch-change / policy-change) | Already substrate *events*: `coord/task_ledger.py` (task close) · git (branch) · `primitives/supersession.py` (arch change) · `security/acl.json` (policy) |
| "Forced save + relaunch" enforcement | `comm/launcher.py` + `runner_lock.py` + `liveness.py` — supervision can already stop/revive; today fires only on crash/wedge, not on cognitive debt |

GPT's **four context tiers already physically exist as our layer stack**: Working = live hook context ·
Session = notes/last-session-draft/narrative session · Project = ARCHITECTURE/LEXICON/lessons/ACL ·
Historical = Ledger/chronicles/benchmarks. The gap is not the tiers — it is *promotion/demotion rules
between them* (the distiller/supersession pipeline pointed at the refresh boundary).

### The three genuinely-new pieces
1. **A context-health estimator** — the one real new primitive. The funnel scores whether *surfaced
   corpus* helps; `cognitive_metrics.py` scores whether *coordination* helps; nothing scores a single
   agent's *live working-context quality*.
2. **A refresh policy** fusing health + the lifecycle events above into a recommend/enforce decision.
3. **Enforcement matched to agent type** (see fidelity, below).

### Two framings adopted
- **Cognitive debt = self-inflicted availability degradation → a *safety* property, not just
  productivity.** This is the agent-side analog of Verified-prior-art point #2 ("context saturation is a
  100%-success availability attack; bounding the medium is non-negotiable"). Renew inherits that already-
  grounded justification.
- **Refresh fidelity = reuse the Bifrost fidelity ladder.** Interactive Claude Code is never force-
  relaunched (human-in-loop) — it gets an INFORM/STEER *recommendation* through the membrane. Stateless
  runner agents (deepseek runner owns its loop) *are* enforced — a HALT + respawn. The ladder already
  exists; Renew rides it.

### Design discipline (anti-patterns, baked in)
- **Never raw token count as the trigger** (GPT's own warning). Health ≠ usage — a 48%-full context
  thick with superseded plans is unhealthier than a 72%-full coherent one.
- **No LLM judge for health** — violates the NO-LLM faithfulness principle *and* token-frugality. Start
  deterministic.
- **Evidence-gate it** — no policy ships without a benchmark that it improves outcomes (Principle: each
  slice gated by a benchmark). Otherwise it is ceremony.
- **Metric before dashboard** — GPT's cognition dashboard is the payoff, but observing a metric that
  does not yet exist is theater.

### Research scope before building (tagged by kind) → tracked in `open-docket`
- **A. [EMPIRICAL — core] Cheap deterministic health signals that predict degraded output.** Candidate
  proxies, mostly already logged: **file-reread rate** (GPT's "they start rereading files" tell — *in the
  PostToolUse stream, free*), tool-call repetition/backtrack rate, turns-since-boot, task-ledger churn,
  superseded-record density (diff live context vs `supersession.py` edges), stale-lock count. Method:
  instrument + correlate against an outcome signal we already have (FAIL→SUCCESS flips, funnel helped-
  rate, task completion). **This slice comes first.**
  ✅ RESEARCHED 2026-07-07 (`research/reviewed/renew-stranda-health-signals-2026-07-07.md`) — verdict
  inverted the method: label first (flips measure recall-utility, not health; raw reread rate demoted).
  **A′ SHIPPED 2026-07-07:** durable `fail` label events. **A″ SHIPPED 2026-07-08:** durable
  `session_signals` events — the SessionEnd hook folds the session transcript through
  `core/renew/session_signals.py` (churn-over-progress family), so the signal×label correlation
  dataset now accrues passively (the manual bus recorder had silently stopped 2026-07-07).
  Remaining: the correlation itself, data-gated on ~10–20 labeled sessions.
- **B. [PRIOR-ART] ✅ GROUNDED 2026-07-07 → `research/reviewed/renew-priorart-2026-07-07.md`.** Anchor
  confirmed: **MemGPT** (arXiv **2310.08560**, Packer et al.) / **Letta** virtual context management —
  OS-paging over Main(in-context)/External(recall+archival) tiers = GPT's four tiers = our layer stack;
  the gap is the **paging function** (adopt that as the LEXICON term for Renew). Trigger-on-quality is
  empirically forced by **Chroma "context rot"** (18 models: size≠quality; 30%+ lost-in-the-middle) →
  item A is necessary, not optional. Save-at-boundary = **sleep-time compute** (~2.5–5× compute cut,
  echoes token-frugality). **Differentiator sharpened & load-bearing:** Anthropic's own guidance states
  harnesses already run **LLM compaction at a token threshold**; Renew's delta on four axes — trigger
  (deterministic health/lifecycle vs tokens), extraction (NO-LLM distiller over **event-based** records
  vs lossy summary — and *our Ledger already IS the event log Anthropic recommends over summary blobs*),
  scope (durable/cross-session vs ephemeral), warrant (benchmark-gated vs assumed). Excluded future-dated
  2026 arXiv hits for provenance, per the "Synthetic Membrane" discipline.
- **C. [DESIGN] Refresh-decision policy** — map actions onto the fidelity ladder (recommend-for-
  interactive / enforce-for-runner per hat); triggers as substrate events; human-in-loop boundaries.
- **D. [EMPIRICAL — the gate] Does refresh actually help?** A/B via `coord/experiment.py` +
  `cognitive_metrics.py`: refresh-on-debt vs run-long; metric = rework rate / output quality / tokens.
- **E. [EMPIRICAL] Cold-resume fidelity** — is the existing curated save (boot payload) *sufficient* to
  resume as well as full context? Test directly. If yes, Renew is mostly wiring; if no, the distiller
  needs work before any of this matters.

Net: like the membrane, not a new subsystem — a **control loop over snapshot + boot + funnel + launcher +
supersession**, plus one new primitive (health estimator) and one benchmark to earn it.
