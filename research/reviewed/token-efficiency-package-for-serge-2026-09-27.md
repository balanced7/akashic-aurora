# Token-efficiency / context-leverage research — package for Serge

**Assembled** 2026-09-27 for outside reading. Both documents below are reproduced
**verbatim** from the house record; nothing has been re-summarised for this bundle.

## What this is

Two companion documents from the night of 2026-08-11, filed within hours of each other:

1. **The doctrine** — `research/in-flight/context-leverage-doctrine-2026-08-11.md`
   (atom `context-leverage-doctrine_c8408f`). What actually made one long, multi-mind
   night cheap, written from a *measured* observation rather than a claim: a session that
   processed megabytes of evidence across three independent readers ended at 427k context.
   Four named mechanisms, each with the number that supports it.

2. **The prior-art sweep** — `research/reviewed/context-leverage-prior-art-2026-08-11.md`.
   Who else in the field is doing this, what they call it, what they learned the hard way,
   and an explicit *have / steal / skip* mapping. Total research spend: ~$0.02.

They are best read in that order: the first says what we observed, the second says who
else has observed it and what they named it.

## The honest caveats, up front

- **427k is an anecdote, not a benchmark.** The doctrine says so itself, and the sweep's
  steal #4 is precisely "make the context budget an organ, not an anecdote." We have no
  controlled A/B against a naive-retrieval baseline for that night. Treat the number as a
  *direction of effect*, not a measured speedup.
- **The counter-evidence is included deliberately.** Section 1 of the sweep cites the
  finding that a fixed-budget *single* agent wins on sequential reasoning. Fanning out buys
  parallel **reading**, not deeper **thinking**. Anyone adopting this should adopt that
  boundary with it.
- **One research arm was starved** (2,200 tokens) and one was skipped on an expired login.
  The sweep names both rather than presenting four-of-four coverage.

## Vocabulary, for an outside reader

| Ours | Means |
|---|---|
| store / ledger | durable state plane / append-only event plane |
| atom | an adopted document, content-addressed and citable |
| the Eye | full-text index over past session transcripts |
| fence | a brief plus two independently-written halves, reconciled afterwards |
| fan / fan-out | dispatch the same evidence to several independent readers |
| organ | a standing capability, as opposed to a one-off manual act |
| funnel | behavioural credit scoring on retrieval lanes (helped / useful votes) |
| T-number | an internal task id |

---
---

# DOCUMENT 1 — The doctrine (verbatim)

> Source: `research/in-flight/context-leverage-doctrine-2026-08-11.md`

# Context leverage — the 427k night, measured (2026-08-11)

**Trigger:** Daniil, after the priorish audit + sweep + fence + connectome + persistence +
Codex-correction cycle all ran in one session: "I am also amazed by the contextual efficiency
of it all! you are at only 427k context after all of that! Reading all of those files
manually or grepping would not have produced this kind of result."

## The measured shape

One seat at ~427k context conducted, in one night: a live external-API audit (~25 calls over
a 121k-document corpus), full ToS review, an 83-transcript sweep (233 candidates), 12 fan
branches (~$0.35 deepseek total), a design fence, a 2.3MB transcript redaction with
per-substitution audit, and a three-way audit-correction cycle — while the underlying
material was on the order of tens of MB. Almost none of it entered context. Only verdicts
came home.

## The four mechanisms (name them, they are the doctrine)

1. **Scripts do the mechanical reading.** The extractor swept 83 transcripts; context
   received one line (`candidates=233`). The redactor processed 2.3MB; context received a
   20-sample audit. The union assertion checked 119 records; context received `PASSED`.
   Deterministic work belongs in deterministic substrate.
2. **The fan does the semantic reading.** ~160k chars of operator utterances went through
   cheap branches; what returned was findings. The pack pipeline is a CONTEXT FIREWALL:
   megabytes → bounded pack → few-k verdict. (Corollary from the same night's failure: the
   firewall must pass the WHOLE verdict contract — BLIND/CHECK included — and coverage must
   be asserted at the source manifest, or the firewall becomes a launderer.)
3. **The store carries the state.** where-we-are superseded three times in one night — each
   supersede EXPORTS the arc from context to substrate; context holds the live edge, not the
   history. A fresh seat re-enters for thousands of tokens, not 427k.
4. **Verification samples with receipts.** 13 quotes checked, 3 of an auditor's quotes
   re-checked at source — sampling against named planes, never exhaustive re-reads.

## Why grep could not have produced this

The value was not retrieval; it was THREE MINDS CATCHING THREE DIFFERENT FAILURE CLASSES
over the same evidence (author's laundering ← Codex; auditor's observed=existed error ←
Daniil's testimony; corrected reading ← confirmed by an independent completion fan). Each
pass was cheap because each reader read only what its role needed. Selection beats
filtering; the loop beats the read.

## The frame

This is `harness_tier_over_model_tier`, measured live, and the unit economics of the
compounding: the organs that made it cheap (report verb, resident asks, clip warnings,
branch evidence packs, recall-at, the funnel) are weeks old, half of them days old. Same
model, different harness tier → a different class of night.

**Standing question opened by Daniil the same hour:** who else is applying this kind of
leverage, and what can we learn from them? → external sweep filed separately
(context-leverage prior-art), the first live run of the T276 research-cadence shape.

---
---

# DOCUMENT 2 — The prior-art sweep (verbatim)

> Source: `research/reviewed/context-leverage-prior-art-2026-08-11.md`

# Who else applies context leverage — prior-art sweep, 2026-08-11 (~02:45)

**Trigger:** Daniil, right after the 427k observation: "Who else is applying this kind of
leverage and how can we learn from them. I know this can be even more powerful and
transformational." First live run of the T276 research-cadence shape. Companion doctrine:
atom `context-leverage-doctrine_c8408f`.

**Arms:** 2× WebSearch (landed), deepseek prior-art lens (landed), deepseek analogs lens
(STARVED at 2,200 tokens but fully recoverable from the preserved reasoning field — the
door's honesty organ made the spend recoverable), Gemini-web (login expired; skipped).
Spend: ~$0.02.

---

## 1 · The 2026 landscape has NAMED our doctrine

- **The four context verbs — write / select / compress / isolate** — are now the standard
  taxonomy (LangChain-popularized; mem0/appscale guides). Our organs map exactly: store=write,
  recall/packs=select, fan-verdicts=compress, branch-isolation=isolate.
- **"Harness engineering" is an arxiv term now** (SemaClaw 2604.11548; survey 2606.20683
  "Agent System and Harness Design") — our harness_tier_over_model_tier lesson, as a field.
- **Anthropic's multi-agent research**: 90.2% gain over single-agent Opus via Sonnet
  subagents with isolated context windows — the canonical published number for the pattern.
- **The honest counterpoint exists and is measured**: Tran & Kiela 2026 / OneFlow 2026 —
  fixed-budget SINGLE-agent wins on sequential reasoning. Multi-agent buys parallel READING,
  not deeper THINKING. (Matches our selection_beats_filtering lesson.)
- Notable arxiv 2026: **"Long Live the Librarian!"** (persistent search sub-agent),
  **SearchSwarm** (delegation intelligence for long-horizon research), **"LLM Agents Are
  Latent Context Managers"** (proprioceptive context dashboard — the agent sees its own
  budget), **HarnessBridge** (learnable harness controller), **Provence** (95% document
  pruning), and the offload pattern: tool outputs >2k tokens written to disk, replaced by
  path + 10-line preview + re-read verb (our harness's persisted-output, generalized).

## 2 · Framework/product prior art (deepseek lens, training knowledge)

MemGPT/Letta context paging (risk: paging discards critical state) · Chain-of-Agents
sequential chunk-summaries (risk: cumulative drift) · LLM MapReduce (risk: reducer loses
cross-chunk interactions) · OpenAI Deep Research (risk: citation hallucination) · Devin's
single-context stance (buys replayable trace; risk: loses raw texture — the OPPOSITE bet
from ours, both defensible) · LangGraph supervisor patterns (risk: ambiguous verdicts
bottleneck the supervisor) · RAG (risk: no global view).

## 3 · The organizational analogs and their guards (recovered from the starved lens)

| Institution | Verdict format | Failure they learned | Guard |
|---|---|---|---|
| Military staff | BLUF + commander's intent | intent misunderstood downstream | **backbrief** — restate in own words before acting |
| Copy desk | headline/lede/nut-graf | slanted compression | multiple editors + fact-check against raw |
| Peer review | structured review + recommendation | reviewer bias/groupthink | N independent reviewers + editorial override |
| MapReduce/Unix | typed partials | faulty mapper propagates | redundancy, checksums, stage sanity checks |
| Crew Resource Mgmt | standardized callouts | **authority gradient silences dissent** | two-challenge rule, assertiveness norms |
| Intel (ACH/Team B) | key judgments + confidence + alternatives | confirmation bias | devil's advocacy, key-assumptions check |

**Three guards that transfer best** (deepseek's ranking, endorsed): (1) redundant
independent verdicts with cross-check; (2) mandatory structured-uncertainty verdict format —
confidence, assumptions, counter-evidence in EVERY summary; (3) **blind backbrief
validation** — after the conductor decides, a raw-access worker re-checks the decision
against source. *Tonight's Codex cycle WAS guard 3, performed by hand. The finding is to
make it an organ.*

## 4 · The mapping — have / steal / skip

**Already ours (sometimes ahead):** the four verbs as organs; structured-uncertainty verdicts
(the findings preset's FINDINGS/REASONING/CHECK/BLIND *is* guard 2 — 2026 guides recommend
what our ask door already enforces); adversarial review culture (fence, kill-drills); the
behavioral-credit funnel (NO surveyed system scores its own retrieval lanes by helped-votes);
bitemporal attribution (our connectome stance goes past anything in the sweep).

**Steal, ranked:**
1. **Backbrief-as-organ** (military + tonight's Codex cycle): a standing post-synthesis verb —
   one raw-access branch re-checks any corpus-level claim before it lands in a report. Cheap,
   would have caught the coverage laundering same-hour.
2. **Offload-with-preview at the ask door** (arxiv + our own harness): packs and big tool
   outputs ride as path + preview + re-read verb instead of inline bytes — composes with T273
   (clip chokepoint, already approved).
3. **Sequential-vs-parallel routing rule** (Tran & Kiela / OneFlow): codify WHEN to fan —
   wide independent reading → fan; deep sequential reasoning → one seat, spend the savings on
   context quality. A one-paragraph addition to the fan doctrine.
4. **Proprioceptive context dashboard** (arxiv 2606.30005): surface the seat's own context
   budget as a queryable gauge (flightdeck integration) — the 427k number should be an organ,
   not an anecdote.
5. **Conductor digest discipline** (LangChain deep-agents): compress older turns into a
   structured digest at a sliding window — our wrap/boot already approximates this at session
   boundaries; the steal is doing it MID-session at defined waypoints.

**Skip for now:** learned compression (HarnessBridge-class) — premature at our scale;
persistent librarian subagent — THE EYE *is* our librarian, build T278 first; Provence-class
pruning — revisit when packs regularly exceed budgets.

## 5 · Both-direction deltas (for the Max weekly doc)

They have, we lack: learned harness controllers; context self-management dashboards;
published benchmarks of the leverage (90.2%). We have, none surveyed do: funnel-scored
retrieval lanes; bitemporal idea-lineage attribution; resident fence culture with named
minds; wisdom-layer edges. **Question candidates for the weekly doc:** how do production
fleets measure summary-fidelity loss at the compression boundary? Who has shipped
backbrief-style post-decision validation as automation, and what did it cost/catch?

**Sources:** [FlowHunt multi-agent 2026](https://www.flowhunt.io/blog/multi-agent-ai-system/) ·
[Subagent architecture](https://clouatre.ca/posts/orchestrating-ai-agents-subagent-architecture/) ·
[5 orchestration patterns](https://www.digitalapplied.com/blog/multi-agent-orchestration-5-patterns-that-work) ·
[Librarian sub-agent](https://arxiv.org/pdf/2605.27787) · [SemaClaw harness engineering](https://arxiv.org/pdf/2604.11548) ·
[Harness design survey](https://arxiv.org/pdf/2606.20683) · [SearchSwarm](https://arxiv.org/pdf/2606.09730) ·
[Proprioceptive dashboard](https://arxiv.org/pdf/2606.30005) · [HarnessBridge](https://arxiv.org/pdf/2606.12882) ·
[LogRocket context problem](https://blog.logrocket.com/llm-context-problem-strategies-2026/) ·
[mem0 context engineering](https://mem0.ai/blog/context-engineering-ai-agents-guide) ·
[LangChain deep-agents context](https://www.langchain.com/blog/context-management-for-deepagents) ·
[appscale production guide](https://appscale.blog/en/blog/context-engineering-production-llm-agents-token-budget-compaction-2026) ·
[Code agent orchestra](https://addyosmani.com/blog/code-agent-orchestra/)
