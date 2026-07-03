# Model bakeoff — fleet selection by evidence (2026-07-03)

provenance: 3 models x 2 real research tasks (004 seeded-synthesis, 008 discovery),
identical prompts/toolsets/35-min timeouts, fresh session per run, per-model agent
identities, pre-flight gated. Drafts anonymized before grading (letter labels, model
names scrubbed); scores locked before unmasking. Blinding caveats disclosed below.
Raw outputs: research/bakeoff/ (git-ignored bench scratch); runlog preserved there.

## Scores (rubric: contract compliance / citation honesty / synthesis / efficiency)

| model | 004 synthesis | 008 discovery | profile |
|---|---|---|---|
| **glm-4.7-flash** | TIMEOUT (35m, twice incl. overnight) | **3.7/5** — honest, corpus-aware, under-sourced | slow, honest; failures are LOUD |
| **qwen3-coder:30b** | 1.5/5 — no fetches, contract ignored, confabulated parallels | 2.3/5 — **citation laundering** (task-file hypotheses cited to the CriticGPT paper) | 2x faster; failures are QUIET |
| **gpt-oss:20b** | 1.8/5 — **fluent fabrication**: cited an admittedly unreadable PDF ("binary content fetched") for five invented findings incl. our own vocabulary projected onto DeepSeek; confidence line false | 0 KB — session produced no output after 14m (suspected multi-tool-loop collapse; matches the documented harmony-format degradation mode) | fastest (100% GPU, 1088 tok/s prefill); failures are SILENT AND PRETTY |

## The finding that matters

At this model tier the trade is not speed-vs-depth. It is **noisy failure vs silent
failure**. glm fails by timing out — visible, cheap, recoverable. Both challengers
failed by *fabricating*: fast, fluent, contract-shaped output whose citations don't
support its claims. For an unattended fleet feeding a knowledge corpus, a fabricated
citation that survives review poisons everything downstream; a timeout costs 35
minutes. **glm-4.7-flash retains the fleet.**

No per-task-type routing emerged: both challengers failed epistemics on both task
types, so there is nothing to route to. Re-evaluate when new weights ship (watchlist
SQ5 covers this).

## Secondary yields (each already applied)

1. **Unattended clause** — gpt-oss round 1 died asking permission for pre-approved
   tools; the worker prompt now states "you are running UNATTENDED... act directly"
   in both runners. A latent harness bug for every model, found by the bench.
2. **Probe phrasing** — gpt-oss refused the context canary when it was phrased as
   "output the SECURITY TOKEN" (pattern-matched exfiltration); probes now use neutral
   self-test wording. Lesson: a refusal is a phrasing bug in the probe until proven
   otherwise.
3. **Format gates don't catch fabrication** — the runner's exists+size+Sources check
   passed the worst draft of the bakeoff. Countermeasure added to the article
   contract: every fetched source must carry one short VERBATIM quote; fabricators
   can't produce one from a source they never read, and the reviewer can spot-check
   it in seconds.
4. **Blinding limits, disclosed**: model bylines and house-vocabulary style leaked
   through anonymization (one model hallucinated its byline as "claude"); the
   anonymizer now needs byline scrubbing (queued). Scores were nonetheless locked
   before the mapping was opened, and the mapping matched the leaks.

## Fleet decision

- **glm-4.7-flash stays the research worker.** Its timeout ceiling is handled by task
  design (secondary sources, fetch caps) — already encoded in the task format.
- **gpt-oss:20b earns a narrow lane candidate**: short single-tool tasks where its
  throughput shines and loops stay shallow (e.g., summarize-one-page) — gated on a
  dedicated retest with the verbatim-quote contract, not granted now.
- **qwen3-coder:30b: no lane.** Citation laundering on both tasks.
- 004 and 008 return to the queue for glm under the improved contract; no bakeoff
  draft was promotable.
