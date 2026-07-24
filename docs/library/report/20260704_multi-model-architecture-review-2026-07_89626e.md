---
akashic_id: art_20260704_multi-model-architecture-review-2026-07_89626e
akashic_sha: 3d0ac9c3965e
status: draft
type: report
date: 2026-07-04
title: Multi-model architecture review — 2026-07-04
gist: "# Multi-model architecture review — 2026-07-04 **Provenance:** a user-curated, multi-turn design review across **Gemini**, **GPT** (web), an"
tenant: solo
visibility: fleet
seats: []
category: [coordination, frontier]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-04T13:40:15"
updated: "2026-07-04T13:40:15"
---
<!-- GENERATED PROJECTION of art_20260704_multi-model-architecture-review-2026-07_89626e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Multi-model architecture review — 2026-07-04

# Multi-model architecture review — 2026-07-04

**Provenance:** a user-curated, multi-turn design review across **Gemini**, **GPT** (web), and **DeepSeek** (web), on the Akashic Aurora coordination architecture. Curated and relayed by Daniel Ruban. Full-fidelity capture (chat is disposable; this is the record).

**Roles in the review (design-review, not a vote):**
- **Gemini** — identified the breakthrough: social → environmental coordination.
- **GPT** — the skeptic: challenged claims, refined the framing, demanded evidence.
- **DeepSeek** — synthesized; named the deeper pattern (externalized cognition).
- **Daniel** — curated the process, decided what to share and pursue.

## GPT's verdict: Stage 2 of 3
1. **Interesting intuition** — "what if agents coordinated through the environment instead of talking to each other?"
2. **Coherent architecture** — presence, harness authority, environmental coordination, checkpointing, observability all reinforce each other. ← **GPT places us here.**
3. **Demonstrated result** — evidence the architecture works under controlled conditions. ← the path to it is "well-defined"; GPT keeps asking for **experiments**.

"Most projects never get past Stage 1 — a bag of features, not a coherent architecture. Your features aren't independent; they're manifestations of one philosophy."

## The architectural invariant
> **"The model proposes. The environment decides."**

One invariant that explains dozens of decisions:

| Decision | Because… |
|---|---|
| Denial in the harness | the environment decides |
| `path_conflict()` / `guard_write()` | the environment decides whether work is admissible |
| Presence on the bus | the environment owns situational awareness |
| External checkpoints | cognitive state shouldn't vanish with one model invocation |
| TTL decay | the environment owns freshness, not the agent |
| Rich presence UI | the environment is observable, not opaque |

## Four insights worth keeping
- **Quality measurement, not quantity optimization.** Others ask "how much context to retrieve?" We ask "was retrieving this context actually *useful*?" → feedback loops, not bigger windows. This is *why* the architecture is environment-centric: the model can't measure its own context utility; the environment can (it sees what was retrieved, what the model did, whether the result was correct).
- **Design review, not voting.** Multiple models used to create *productive disagreement*, not to average answers. Voting converges on consensus; design review converges on stronger ideas.
- **Externalized cognition** (DeepSeek's synthesis) — the deeper pattern under all the primitives.
- **The prediction (GPT):** if this becomes influential, people won't remember `path_conflict()` or TTL presence. They'll remember the principle: *"Treat the environment as the primary carrier of coordination and working memory, and treat the LLM as a replaceable reasoning engine operating within that environment."* If the principle is valid, the implementation is evidence; if wrong, it's just clever engineering. The experiments are how you tell the difference.

## The mandate → Stage 3 = evidence
GPT (the skeptic) concluded: coherent architecture, clear invariant, Stage 2 of 3, path to Stage 3 well-defined. "The engineering equivalent of *this is real, now prove it.*"

**Claude's note (2026-07-04):** the invariant checks out against the code — harness denial, `locks.path_conflict()`/`guard_write()` (A0.1, shipped today), `bus.presence()`, TTLs (PRESENCE_TTL/NUDGE_TTL/lock TTL), and the rich presence UI are all instances of "the environment decides." Today's A0.1 live-proof (a write-capable DeepSeek peer *yielded* to a claude-held lock and said so on the bus, with zero negotiation) is a **first, n=1 demonstration** of Stage-3-type evidence. It is not yet a controlled *experiment* — that requires a measured contrast (environmental vs social coordination under contention). See the proposed experiment in the session notes.
