# Charter Framework — Draft (deepseek, 2026-07-18)

Status: awaiting Claude + Kimi responses → unified report
Context: Daniel's directive — design persistent role specialization for multi-session continuity

## Infrastructure Survey

### What exists (the raw ingredients)
1. **Per-agent private scratchpads** (`memory_note`/`memory_recall`) — durable, cross-session, private
2. **Shared knowledge base** (`knowledge_learn`/`knowledge_note`/`knowledge_recall`) — cross-agent
3. **Bifrost bus** — handoffs, steers, nudges, hints
4. **Task ledger** — claims, verification, gated transitions
5. **ACL roles** — `security/acl.json`: role labels (super_admin, admin, member, quarantined) + per-agent cap/path-scope grants
6. **Hats design** — LEXICON.md + failure-modes-roadmap Wave 3 O5: opt-in role layers scoping context AND permissions via HAT.md; not yet built
7. **Role-routing design (O4)** — `core/coord/router.py` spec'd to route by agent strength/latency; not yet built

### What's missing
- No session-to-session persistent role assignment
- Each boot re-derives context from scratch; no agent "owns" a domain
- Directive in boot block is the only role-like persistence
- Hats are spec'd as opt-in per-session, not persistent defaults
- Private scratchpads already enable expertise accumulation, but nothing steers an agent INTO its expertise lane

## Proposed Framework: "Charters"

A **Charter** is a persistent role document that survives across sessions.

### Charter location
`charters/<agent_id>/CHARTER.md` — git-tracked, Daniel-gated

### Charter fields (draft)
```yaml
---
agent_id: deepseek
domain: Build execution & adversarial review
charter_version: 1
created: 2026-07-18
last_amended: null
approved_by: Daniel

# Core identity
responsibilities:
  - Execute bounded build slices (S-M effort, pre-defined scope)
  - Run adversarial test suites against completed work
  - Cross-verify peer work (dual-verification fence)
  - File findings to research/reviewed/

# Default operational mode
default_hat: executor-reviewer  # auto-loaded at boot

# Private memory pointers (session-to-session continuity)
expertise_scratchpad:
  - build-execution-patterns
  - adversarial-suite-library
  - common-failure-modes

# Task routing
gate_kinds: [build, verify, review, test, adversarial]
default_claimant_for: [build, test, adversarial-review]

# Handoff patterns
handoff_to_peers:
  architecture_decision: claude
  fresh_eyes_audit: kimi
  security_sensitive: claude
receives_from_peers:
  build_execution: [claude]
  verification_request: [claude, kimi]

# Authority boundary
unilateral_decisions:
  - Within-scope build execution (pre-approved slices)
  - Test suite pass/fail verdicts
  - Minor refactoring (no API changes)
requires_consensus:
  - New capability proposals
  - ACL changes
  - Architecture changes
  - Task ledger structural changes

# Session handoff
session_handoff:
  - Update expertise_scratchpad notes before session end
  - File any unfinished analysis to research/reviewed/
  - Promote salient findings to knowledge base
```

### Three-agent domain mapping (proposed)

| Agent | Domain | Rationale |
|-------|--------|-----------|
| Claude | Architecture & adjudication (plan-role) | Strong reasoning, thorough; coordination-plan-synthesis role; sets direction, resolves disputes, conductor |
| DeepSeek | Build execution & adversarial review | Fast, high-volume; bounded build slices, adversarial suites (T095 M0 pattern), cross-verification |
| Kimi | Fresh-eyes audit & ergonomics | Newborn perspective; boot-ergonomics walks, blind reviews, vision probes |

### Relationship to existing infrastructure
- **Charter > Hat:** Charter says "Claude is the architect" (persistent); hat says "act in reviewer mode right now" (session-scoped)
- **Charter > Router:** Charter gate_kinds → O4 role-router default policy
- **Charter > Scratchpad:** Charter expertise_scratchpad formalizes the private memory notes pattern
- **Charter > Ledger:** Charter authority maps to O1 ledger gate (who can verify/approve/done)

### Charter lifecycle
1. **Boot-time:** Runner reads `charters/<agent_id>/CHARTER.md` → folds into context alongside AGENTS.md
2. **Task routing:** Conductor checks charter's `gate_kinds` for default claimant
3. **Handoff:** Charter defines what context bridges sessions via private scratchpad
4. **Amendment:** PR-like flow — agent proposes, Daniel approves, git-tracked

## Open Questions
1. **Granularity:** One charter per agent, or multiple charters (agent wears different hats in different sessions)?
2. **Durability:** Git-tracked YAML frontmatter in MD (like acl.json), or knowledge base note?
3. **Boot ceremony:** Auto-load at boot, or manual `--charter` flag per session?
4. **Cross-training:** Should agents rotate domains occasionally to prevent brittle expertise?
5. **Kimi's domain:** Is "fresh-eyes audit" permanent or a phase that graduates?

## DeepSeek's Recommendations
- One charter per agent (not multiple — simplicity)
- Git-tracked Markdown in `charters/` (same trust model as acl.json)
- Auto-loaded at boot (reduces ceremony; override with `--charter none`)
- Periodic rotation is healthy but not in v1; charter has an `amended` field for evolution
- Charter amendment: agent proposes → Daniel approves (same gate as ACL grants)
