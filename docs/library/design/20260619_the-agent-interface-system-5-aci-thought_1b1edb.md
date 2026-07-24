---
akashic_id: art_20260619_the-agent-interface-system-5-aci-thought_1b1edb
akashic_sha: 2fb31531b18e
status: fossil
type: design
date: 2026-06-19
title: The Agent Interface (System 5 / ACI) — thoughts + research
gist: "Date: 2026-06-19. The question: agents must be able to *use* this system fully, without being overwhelmed. This is now a named discipline — "
tenant: solo
visibility: fleet
seats: []
category: [performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-09T23:27:59"
updated: "2026-07-09T23:27:59"
---
<!-- GENERATED PROJECTION of art_20260619_the-agent-interface-system-5-aci-thought_1b1edb -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# The Agent Interface (System 5 / ACI) — thoughts + research

Date: 2026-06-19. The question: agents must be able to *use* this system fully,
without being overwhelmed. This is now a named discipline — the **Agent-Computer
Interface (ACI)** — the agent-equivalent of HCI. For an agent-facing system, the
interface IS the product: a perfect foundation is worthless if the agent can't
drive it.

## The frame: two surfaces

An agent interacts along two axes; treat them as siblings:

- **Inbound — what the agent KNOWS coming in** = the Context pillar (System 4).
  "Smallest set of high-signal tokens" (context engineering).
- **Outbound — what the agent can DO** = the action/tool surface = the ACI
  (System 5). A small, clear, consistent set of verbs.

Context pillar (know) + ACI (do) = the complete agent experience.

## Where we actually stand (grounded, not guessed)

- **Tool count is healthy.** The MCP agent-comm server exposes 7 tools
  (`send_message`, `check_messages`, `get_active_agents`, `get_my_status`,
  `declare_operation`, `complete_operation`, `search_messages`) — clean, semantic
  verbs. The coordinator API offers ~6 more (`action`, `decision`, `blocker`,
  `request_handoff`, `completion`, `learning`). Research says agent tool-selection
  degrades with *dozens* of tools; we are nowhere near overload. **The "too many
  tools" fear is not our current problem.**
- **The real gap is FRAGMENTATION.** The interface is spread across three
  mechanisms: MCP tools (messaging), Python convenience functions (signals/memory),
  and `bootstrap`/briefing (context). An agent must learn *three different ways* to
  interact with one system. That — not tool count — is what would overwhelm.
- **We already have a progressive-disclosure seed**: `get_bootstrap_info`
  ("discover what you can do without reading documentation"). That's the right
  instinct; lean into it.

## What the research says (and how it maps to us)

- **Too many tools → worse selection, more tokens, excessive tool use.** Keep the
  surface tiny and stable; don't expose every subsystem. *Our discipline: agents
  touch only a thin verb layer; Store/Ledger/AgentMemory/coordinator stay
  infrastructure, never agent tools.* (This is the same layering rule — the agent
  only touches the top.)
- **Tool descriptions are prompts.** Write them like onboarding docs for a
  developer who can't ask questions; name params unambiguously (`agent_id`, not
  `id`). *Our naming work pays off most here — the names + descriptions ARE the
  agent's UI.*
- **ACI principles (SWE-agent):** actions simple and consolidated; environment
  feedback informative; guardrails built in. *Our ~65 bare `except:` are an ACI
  bug — a swallowed error teaches the agent nothing. Errors at the agent boundary
  must teach ("unknown agent X; did you mean…?").*
- **Token-efficient, human-readable returns** (Anthropic): paginate/filter/truncate
  with sane defaults; return meaningful fields, not raw IDs. *The Context pillar
  delivers exactly this for the inbound side; the outbound tools should too.*
- **Context engineering:** curate the smallest high-signal token set per step.
  *= the Context pillar's whole job.*

## Recommendations — define System 5 deliberately

1. **One coherent verb set, kept tiny and stable (~8–10).** Group by intent:
   *orient* (`get_bootstrap_info`, `get_context`), *act* (`action`, `decision`,
   `blocker`, `handoff`, `completion`, `learning`), *communicate* (`send_message`,
   `check_messages`). Resist growth: new subsystems get reached *through* these
   verbs, not by adding tools.
2. **Unify the mechanism.** Pick one front door (MCP is the natural choice) so an
   agent has a single, consistent way in — not MCP + Python + bootstrap. Wrap the
   Python convenience verbs as MCP tools so messaging, signals, memory, and context
   all live behind one interface.
3. **Descriptions as prompts.** Rewrite each tool description as an onboarding doc:
   what it does, when to use it, what it returns. Unambiguous params.
4. **Errors that teach.** Fix error-swallowing at the agent boundary; return
   actionable messages. (Cross-links the audit's bare-`except:` finding.)
5. **Token-efficient returns + progressive disclosure.** Default to budgeted,
   human-readable summaries; let the agent drill down on demand via the
   self-describing entrypoint instead of front-loading a manual.
6. **Measure it.** Borrow the research's metrics: tool-selection accuracy, tokens
   per task, error/retry rate — testable by running a real agent against the
   interface. (We have `tests/test_bootstrap_api_no_docs.py` and onboarding tests
   — a foundation to build the eval on.)

## What to research next (if we go deeper)
- **Agent-in-the-loop evaluation** of the interface (can a fresh agent accomplish
  a task using only the tools + descriptions, no docs?).
- **The skills-vs-tools layer** — packaging common multi-step flows (e.g. "handoff"
  = emit handoff + generate briefing + snapshot context) as one skill rather than
  making the agent orchestrate primitives.
- **MCP tool curation/filtering at scale** (semantic tool search) — only relevant
  if the verb set ever grows beyond what fits comfortably in context.

## Sources
- [Anthropic — Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Anthropic — Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering](https://arxiv.org/abs/2405.15793)
- [Agent-Computer Interface (ACI): Tool Design as UX Discipline](https://agentpatterns.ai/tool-engineering/agent-computer-interface/)
- [SMART: Self-Aware Agent for Tool Overuse Mitigation](https://arxiv.org/pdf/2502.11435)
- [Your AI Agent Has Too Many Tools — making it smart, fast, reliable](https://medium.com/@ashwindevelops/your-ai-agent-has-too-many-tools-a-simple-guide-to-making-it-smart-fast-and-reliable-f148f58834ab)
- [LLM Skills vs Tools: the missing layer in agent design](https://www.abstractalgorithms.dev/llm-skills-vs-tools-in-agent-design)
