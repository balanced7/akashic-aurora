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
2. **Built≠Wired gate** (`check_wiring.py`) — the maintainability guard: fail if a capability exists +
   passes tests but isn't on a production call path. Directly serves the adherence↔maintainability balance.
3. **Surface → orientation** — inject the relevant ARCHITECTURE/LEXICON slice at the tool boundary, so an
   agent touching `core/comm` gets the Bifrost map, not just lessons. (Instant skeleton retrieval.)
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
