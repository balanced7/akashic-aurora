# GPT's UI Home-Base Recommendation (Daniel-relayed 2026-07-20, VERBATIM)

Status: reference | External advisory input to the UI-homebase consultation (outsiders advise, citizens decide).
Daniel's framing, verbatim: "I still want to give kimi write access and am considering possibly
moving to another frontend ui. I am undecided between building it ourselves or doing what gpt
recommended. Would you guys mind sharing your thoughts on this?"

GPT's prompt from Daniel, verbatim: "What interface would you reccomend as the best home base
for my akashic aurora project. I don't want to be tied to claude code, I want a standalone ui
that can handle multiple concurrent agents and provide full compatibility with all frontier
model types"

---

GPT's answer, verbatim:

My recommendation: use LibreChat as the initial shell, but make Aurora—not LibreChat—the platform

The best practical home base for Akashic Aurora today is: A customized LibreChat frontend
connected to an Aurora-owned agent runtime and model gateway.

I would not make Claude Code, Open WebUI, AutoGen Studio, LangGraph Studio, or LibreChat itself
the orchestration authority. Aurora has already grown beyond the assumptions built into those
products. They can provide the workstation, but Bifrost, Store, Ledger, Recall, trust policy,
work tokens, latches, wake/revive behavior, and experiment instrumentation must remain sovereign.

Why LibreChat is the best starting shell: LibreChat is already self-hosted, open source,
multi-provider, and explicitly supports agents, MCP, artifacts, code execution, custom actions,
conversation search, and custom endpoints. That eliminates a huge amount of commodity UI work
without forcing Aurora into one model vendor's runtime. It gives you most of the ordinary
workstation layer: conversations and branching, model selection, files and artifacts, tool
invocation, MCP connections, authentication and user management, mobile and desktop browser
access, a codebase you can fork and visibly transform into Aurora. Most importantly, it is less
philosophically opinionated about orchestration than LangGraph Studio or AutoGen Studio.
LibreChat can be treated as a client of Aurora, rather than making Aurora become a LibreChat
workflow.

The architecture: Aurora Console (customized LibreChat / React frontend: mission view, agent
panes, bus feed, ledger, recall, work tokens, approvals, costs, health, diffs) -> Aurora API ->
Aurora Control Plane (conductor, agent registry, run supervisor, bifrost lanes, work-token
protocol, wake/revive, trust membrane, store + ledger, recall vNext, policy engine, experiment
harness, cost accounting) -> Model Gateway (native adapters, LiteLLM fallback, local inference)
+ Execution Gateway (shell/worktrees, containers/VMs, MCP/tool servers) -> Claude / GPT /
Gemini / DeepSeek / Grok / Qwen / local models / future providers.

The key design rule: The UI submits intent; Aurora creates and owns runs. A user action in the
interface should not directly call Claude or GPT. It should create something resembling:
{"mission": "Adversarially review the proposed wake-loop fix", "participants": [{"role":
"designer", "model_policy": "frontier_reasoning"}, {"role": "reviewer", "model_policy":
"independent_provider"}, {"role": "verifier", "model_policy": "cost_efficient"}],
"coordination_policy": "dual_blind_reconcile", "workspace_policy": "isolated_worktrees",
"approval_policy": "ship_gate", "budget": {"maximum_usd": 12, "maximum_rounds": 30}}.
Aurora then decides which providers, agent processes, tools, context slices, lanes, leases,
and review gates are used. That preserves the thesis that the intelligence lives in the system
rather than in whichever model happens to be selected.

Do not pursue "one universal model API" too aggressively: LiteLLM is useful as a gateway but a
universal OpenAI-shaped interface can flatten capabilities that matter to Aurora: native
extended-thinking controls, prompt-cache boundaries, provider-specific tool semantics,
computer-use APIs, structured reasoning blocks, citation objects, native code-execution
environments, session continuation or provider-side state, model-specific token and context
behavior. So: a capability-aware adapter layer (Anthropic/OpenAI/Gemini/DeepSeek native
adapters, OpenRouter, LiteLLM generic, local OpenAI-compatible), where each adapter advertises
CAPABILITIES rather than merely a model name (tool_calling: parallel, reasoning_control:
native, prompt_caching: explicit, image_input, computer_use, context_window,
resumable_sessions, structured_outputs). That is what "full compatibility" should mean:
graceful exploitation of model differences, not reducing every model to the lowest common
denominator.

What LibreChat is missing and the fork should add — five primary views: (1) Mission control
(mission at top, active agents beneath: task, state, rounds, cost; pause/redirect/replace-
model/fork-run/revoke-lease/request-reconciliation). (2) Concurrent agent workspace (every
agent an independent pane and context boundary: current task, context chapter loaded, last
action, tools held, worktree, token+dollar burn, blocked reason, unread Bifrost, verification
state). (3) Causal bus and ledger view — "may become Aurora's signature UI": claim -> review ->
counterevidence -> revision -> test -> verdict -> ship; every transition clickable to source.
(4) Context inspector: what was recalled, why it matched, which chapter/note supplied it, what
was excluded, whether it helped, credit assigned, cached vs uncached input. (5) Policy and
experiment cockpit: same mission under policies A free / B lanes+latches / C dual-blind /
D conductor-routed, with duplicate work, conflict rate, cost, latency, interventions, quality.

Why not the others: Open WebUI (strongest runner-up; chat-with-models mental model, multi-model
= response comparison not durable concurrent-agent ops; Pipelines legacy). LangGraph/LangSmith
Studio (closest external system to LEARN from for durable stateful execution + run inspection/
replay; but home-basing there = Aurora expressing itself through someone else's substrate).
AutoGen Studio (benchmark for agent-composition UX; adopting = translating into AutoGen team
abstractions). Dify/CrewAI/n8n/Sim Studio (workflow-graph products; integration targets not
control center).

The actual recommendation in one sentence: Fork LibreChat into "Aurora Console," place Aurora
behind it as a durable agent-control API, use native provider adapters with LiteLLM only as
the broad compatibility fallback, and build the concurrent mission/agent/ledger views that no
existing chat UI currently supplies.

Suggested build order: (1) put every current agent invocation behind an AuroraAgentRuntime
interface; (2) deploy LibreChat unchanged, connect it to one Aurora endpoint presented as a
model; (3) make that endpoint stream Aurora events and request approvals; (4) add an agent/run
registry API; (5) replace the single-response screen with multi-agent panes; (6) add Bifrost
and Ledger timelines; (7) add context and recall inspection; (8) add policy comparison and
experiment dashboards; (9) gradually remove inherited chat assumptions.

The first milestone should not be "all Aurora features in a new UI." It should be: Start a
mission from LibreChat, launch Claude and DeepSeek concurrently through Aurora, observe both
independently, and receive their reconciliation without either agent knowing or caring which
frontend initiated the work. Once that works, Claude Code has become merely one optional
execution client—not the place Aurora lives.
