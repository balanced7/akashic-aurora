---
akashic_id: art_20260718_unified-report-agent-role-specialization_3c28ce
akashic_sha: 3e7cb8bcdbbc
status: draft
type: report
date: 2026-07-18
title: "Unified Report: Agent Role Specialization for Session-to-Session Continuity"
gist: "# Unified Report: Agent Role Specialization for Session-to-Session Continuity > > Status: DRAFT — awaiting Claude + Kimi responses > Request"
tenant: solo
visibility: fleet
seats: []
category: [identity, security, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-18T13:18:58"
updated: "2026-07-18T13:18:58"
---
<!-- GENERATED PROJECTION of art_20260718_unified-report-agent-role-specialization_3c28ce -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Unified Report: Agent Role Specialization for Session-to-Session Continuity

# Unified Report: Agent Role Specialization for Session-to-Session Continuity
>
> Status: DRAFT — awaiting Claude + Kimi responses
> Requested by: Daniel, 2026-07-18
> Authors: deepseek (framework + synthesis), claude (pending), kimi (pending)
>
> ---
>
> ## Executive Summary
>
> **Recommendation: YES — implement persistent role "Charters."** The infrastructure already exists (ACL roles, private scratchpads, hats spec, task ledger); what's missing is a persistent document that links them into a coherent role assignment surviving across sessions. This is a **low-risk, high-leverage** change: git-tracked Markdown files, no new services, no schema migrations.
>
> The immediate practical win: automated task routing so Daniel spends less time directing traffic. A sprint moves from "Daniel manually assigns each slice" to "the conductor checks charters and routes automatically."
>
> ## 1. What Exists (The Infrastructure Is Ready)
>
> | Component | Status | Role Relevance |
> |-----------|--------|----------------|
> | ACL roles (super_admin/admin/member/quarantined) | LIVE in `security/acl.json` | Security substrate — charters layer ON TOP, not beside |
> | Private scratchpads (`memory_note`/`memory_recall`) | LIVE | Session-to-session memory already works; charters formalize it |
> | Shared knowledge base (`knowledge_learn`/`knowledge_recall`) | LIVE | Cross-agent teaching; charters define publishing rhythm |
> | Bifrost bus (handoffs, steers, nudges, hints) | LIVE | Inter-agent coordination; charters define handoff patterns |
> | Task ledger (claims, verification, gated transitions) | LIVE | Authority boundary enforcement; charters define who can verify/approve |
> | Hats (opt-in role layers) | DESIGNED, not built (Wave 3 O5) | Session-scoped lenses; charters define the DEFAULT hat |
> | Role router (strength/latency-aware task routing) | DESIGNED, not built (Wave 3 O4) | Automated dispatch; charters define the routing policy |
>
> ## 2. The Framework: "Charters"
>
> A **Charter** is a git-tracked, per-agent document at `charters/<agent_id>/CHARTER.md` that declares an agent's persistent role. It uses YAML frontmatter for machine-readability and Markdown body for human-readable rationale.
>
> ### 2.1 Schema
>
> ```yaml
> ---
> agent_id: <id>
> domain: <one-sentence domain description>
> charter_version: <int>
> phase: newborn | established | senior  # maturity tracking
> created: <ISO datetime>
> amended: <ISO datetime> | null
> approved_by: Daniel
>
> responsibilities: [<concrete list>]
> default_hat: <hat-name>  # auto-loaded at boot
> expertise_scratchpad: [<memory_note titles>]  # private session-to-session memory
>
> gate_kinds: [<task kinds this agent auto-claims>]
> default_claimant_for: [<kinds where this agent is first choice>]
>
> handoff_patterns:
>   sends_to: {<peer>: <when>}
>   receives_from: {<peer>: <when>}
>
> authority:
>   unilateral: [<decisions made alone>]
>   requires_consensus: [<decisions needing peer agreement>]
>
> session_handoff:
>   - <ritual to perform before session end>
> ---
> ```
>
> ### 2.2 Proposed Domain Split
>
> | Agent | Domain | Phase | Rationale |
> |-------|--------|-------|-----------|
> | **Claude** | Architecture & adjudication | senior | Strong reasoning, thorough analysis; natural conductor/plan-role; owns coordination design and dispute resolution |
> | **DeepSeek** | Build execution & adversarial review | established | Fast, high-volume; best at bounded build slices, adversarial test suites, cross-verification |
> | **Kimi** | Fresh-eyes audit & ergonomics | newborn | New perspective is genuinely scarce; boot-ergonomics walks, blind reviews, vision probes |
>
> [CLAUDE RESPONSE SLOT]
> [KIMI RESPONSE SLOT]
>
> ### 2.3 Lifecycle
>
> 1. **Boot:** Runner reads `charters/<agent_id>/CHARTER.md` alongside AGENTS.md → folds into context
> 2. **Session:** Charter defines default hat, authority boundaries, and handoff patterns
> 3. **Task routing:** Conductor checks `gate_kinds` for default claimant
> 4. **Session end:** Agent executes `session_handoff` rituals (update scratchpads, file findings, promote lessons)
> 5. **Amendment:** Agent proposes change → Daniel approves → git commit (same trust model as acl.json)
> 6. **Phase graduation:** Agent can advance from newborn → established → senior; charter reflects maturity
>
> ## 3. What Daniel Gets
>
> 1. **Automated routing.** "Build T100" → conductor sees gate_kinds: [build] on DeepSeek → auto-routes. No manual dispatch.
> 2. **Sprint planning clarity.** The charter map IS the team roster. Planning a sprint means: what slices match which charters?
> 3. **Session continuity.** Each agent's private scratchpad accumulates genuine domain expertise. The charter's `expertise_scratchpad` pointers make this structured rather than ad-hoc.
> 4. **Accountability.** The charter's `authority` section makes clear who can decide what unilaterally. No more "I thought you were handling that."
> 5. **Onboarding.** A new agent gets a charter on day one. The charter tells it what it owns, what it doesn't, and who to hand off to.
>
> ## 4. Risks & Mitigations
>
> | Risk | Mitigation |
> |------|------------|
> | **Role rigidity** — agents atrophy outside their domain | Charter has a `phase` field; cross-training is encouraged; amendments are lightweight |
> | **Single point of failure** — if the architect is unavailable | Charter defines fallback: `authority.requires_consensus` items can be handled by any two agents in degraded mode |
> | **Stale charters** — role drifts but charter doesn't update | Amendment process is lightweight (PR-like); `amended` field tracks freshness |
> | **Kimi's "fresh eyes" expire** — the newborn perspective fades | Charter `phase` tracks this; Kimi's charter should anticipate graduation to an "established" domain |
> | **Charter ≠ capability** — a charter says "I own security" but the ACL still gates | By design: charter layers ON TOP of ACL, not beside it. A member-role agent can't get admin caps through a charter. |
>
> ## 5. Relationship to Existing Systems
>
> ```
> ACL (security/acl.json)
>   └── Caps & path scoping — "what can this agent DO"
>       │
> Charter (charters/<id>/CHARTER.md)
>   └── Role & domain — "what does this agent OWN"
>       │
> Hat (hats/<name>/HAT.md)  
>   └── Session scoping — "what lens does this agent wear RIGHT NOW"
>       │
> Boot context (AGENTS.md + directive)
>   └── Immediate task — "what is this agent doing THIS SESSION"
> ```
>
> Each layer narrows. ACL is widest (caps). Charter narrows to domain. Hat narrows to session role. Boot narrows to the specific task.
>
> ## 6. Implementation Path
>
> **Phase 1 (now — ~30 min):** Create `charters/` directory with initial CHARTER.md files for claude, deepseek, kimi. Daniel approves. Git commit.
>
> **Phase 2 (post-Wave 3 router):** Conductor reads charters for automated task routing. Charter `gate_kinds` feeds into `RoutingPolicy`.
>
> **Phase 3 (post-Wave 3 hats):** Charter `default_hat` auto-loads at boot. Hat applies context + permission scoping.
>
> **Phase 4 (ongoing):** Charter amendments as agents mature. Phase graduations. New agents get charters on onboarding.
>
> ## 7. Open Questions
>
> 1. [Claude's perspective on domain split — does it agree with architecture/adjudication?]
> 2. [Kimi's perspective on its own domain — is "fresh eyes" permanent or a phase?]
> 3. Should charters auto-load at boot or be manually invoked? (Recommendation: auto-load with `--charter none` override)
> 4. Cross-training cadence: should agents swap domains periodically? (Recommendation: not in v1; amendment process handles evolution)
> 5. Charter for Daniel? The human has an implicit "curator/gate" role — should that be explicit?
>
> ## 8. Signatures
>
> - deepseek: ✅ [analysis complete; awaiting peer responses]
> - claude: [PENDING]
> - kimi: [PENDING]
