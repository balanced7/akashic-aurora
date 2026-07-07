# RENEW — prior-art grounding (research item B) · 2026-07-07

Full-fidelity grounding for the membrane's **Renew** job (context-lifecycle management), per the research
scope in `docs/agent-membrane-design-2026-07.md`. Method: web search + primary-source verification, the
same discipline that caught the hallucinated *"Synthetic Membrane"* paper in the membrane note. Sources
are **graded**; unverifiable/future-dated results were excluded (see bottom).

## The one-line finding
GPT's "context lifecycle management" is a **named, active research area** with a canonical vocabulary
(MemGPT/Letta tiered memory), an empirical justification (Chroma "context rot"), a consolidation
paradigm (sleep-time compute), and a stated industry practice we must differentiate from (harness
LLM-compaction at a token threshold). Renew is adoption of a validated paradigm — not speculation.

## 1. The four-tier model is MemGPT/Letta virtual context management [SOLID]
**MemGPT: Towards LLMs as Operating Systems** — Packer, Wooders, Lin, Fang, Patil, Gonzalez —
**arXiv 2310.08560** (2023); now the **Letta** framework. OS-paging metaphor: "the illusion of an
extended virtual memory via paging between physical memory and disk." Two tiers:
- **Main context (in-context):** core memories + system instructions + conversation history (FIFO queue).
- **External context (out-of-context):** recall storage (full history) + archival storage (read-write datastore).

→ **Maps 1:1 onto GPT's four tiers AND onto Aurora's existing layer stack.** MemGPT's Main-context/FIFO =
our *Working* tier (live hook context); recall storage = our *Session/Historical* (notes, Ledger,
chronicles); archival = our *Project* codex (lessons, ARCHITECTURE, LEXICON). **We already have the
tiers physically** (the membrane note's claim, now externally corroborated). The gap MemGPT names and we
lack: the **explicit paging function** — the rules that move a fact Working→Session→Project and evict it
from Working. That paging function *is* Renew.

## 2. "Don't trigger on raw token count" is empirically backed — context rot [SOLID]
**Chroma's 2025 "context rot" study (18 frontier models):** measurable degradation at *every* increment
of context growth, *regardless of relevance*; "lost-in-the-middle" causes 30%+ accuracy drops for
mid-context info. The widely-reported convergent conclusion (Anthropic, JetBrains, SWE-agent):
**"raw context size matters less than context quality."**

→ Directly validates our anti-pattern #1 (**never raw token count as the trigger**) and GPT's own
"health, not usage" framing. A 48%-full context thick with superseded plans is genuinely unhealthier
than a coherent 72%-full one — context rot says the *contents*, not the fill level, predict degradation.
It also empirically motivates the **context-health estimator** (research item A): if quality ≠ size,
the trigger *must* read quality signals.

## 3. The "save at the boundary" idea is the sleep-time-compute paradigm [CONCEPT SOLID; exact IDs unverified]
**Sleep-time compute:** agents consolidate/pre-compute memory during idle periods ("sleep"), decoupling
consolidation from online inference. Reported effect: ~5× less test-time compute for equal accuracy;
~2.5× lower average cost amortized across related queries. Origin: Letta/associated 2025 work; multiple
follow-on memory-consolidation systems (LightMem, TiMem, "Learning to Forget: Sleep-Inspired Memory
Consolidation") extend it.

→ Grounds Renew's **Capture half** ("save = extract durable knowledge, not a transcript") as a known,
measured paradigm — and the ~2.5–5× compute reduction echoes our **token-frugality directive** and the
membrane note's LbMAS ~3× finding. Consolidating at the *session boundary* (not mid-inference) is
exactly the decoupling sleep-time compute advocates. **Caveat (citation honesty):** I did not
independently verify the exact arXiv IDs of the sleep-time-compute origin paper or the follow-ons in this
pass; treat the *concept* as grounded and confirm specific IDs before quoting them in a public artifact.

## 4. The differentiator — how Renew differs from harness auto-compaction [SOLID, load-bearing]
**Anthropic, "Effective context engineering for AI agents"** (anthropic.com) + the convergent industry
picture: **"all agent harnesses run LLM-powered compaction triggered by a token threshold."** Their
taxonomy: **compaction** (summarize near the limit — loses factual/temporal detail), **clearing**
(drop re-fetchable tool output — lossless), **sub-agents** (offload bounded work, return compact
summaries). A key nuance: **summary-only compaction loses detail; event-based/structured logs preserve
structure at 3–40× compression.**

→ This is the sharpest research payoff. The harness *already* compacts — so Renew must not re-implement
it. The **four-axis differentiator**, each axis backed above:
| Axis | Harness compaction (today) | Renew |
|---|---|---|
| **Trigger** | raw token threshold | deterministic **health + lifecycle events** (§2) |
| **Extraction** | LLM summary (lossy, §4) | **NO-LLM distiller** over **event-based** durable records (Ledger/notes/lessons) — the 3–40× structured-compression path, not a blob |
| **Scope** | ephemeral, in-session | **durable + cross-session** (survives relaunch; MemGPT external context, §1) |
| **Warrant** | assumed helpful | **evidence-gated** by a benchmark (item D) |

Corollary: Aurora's **Ledger already IS the "event-based log" Anthropic recommends over summary blobs.**
We built the recommended substrate a year ago; Renew is the paging function over it.

## 5. What this changes in the design
- Item A (health estimator) is **necessary, not optional** — §2 proves size≠quality, so a quality signal
  is the only correct trigger. Promote it to the first build slice, as planned.
- Adopt MemGPT's **"paging function"** as the LEXICON term for Renew's mechanism (page-in on relevance,
  page-out/evict on staleness) — established vocabulary beats a coined one.
- Frame the public/portfolio story as **"a deterministic, cross-session, evidence-gated alternative to
  token-threshold LLM compaction"** — a precise, demonstrable delta, not a vague "memory layer."

## Sources (graded)
- **[SOLID, verified]** MemGPT: Towards LLMs as Operating Systems — arXiv **2310.08560** (Packer et al., 2023) · Letta framework docs.
- **[SOLID]** Chroma, "Context Rot" (2025, 18-model study) — via morphllm.com/context-rot, producttalk.org/context-rot, redis.io/blog/context-rot.
- **[SOLID]** Anthropic, "Effective context engineering for AI agents" (anthropic.com/engineering) + Claude Cookbook context-engineering page.
- **[CONCEPT SOLID, IDs unverified]** Sleep-time compute + memory-consolidation follow-ons (LightMem, TiMem, "Learning to Forget"). Verify exact arXiv IDs before public citation.
- **[EXCLUDED for provenance]** Numerous search hits with future-dated arXiv IDs (2604.x / 2605.x / 2606.x) and odd names (MatClaw, SemaClaw, MAPLE, MEMTIER, Entity-Collision). Not verified; not cited — same discipline that dropped the fake "Synthetic Membrane" paper.
