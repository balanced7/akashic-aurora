# Landscape watchlist — what we watch and WHY

Every entry names the standing question it feeds; an entry that produces nothing for two
consecutive sweeps gets pruned (a watchlist rots exactly like any hand-written map).
Sweeps ask for the DELTA since `last-swept`, never a re-survey. The maturity stages —
paper → reference-impl → framework → commodity — exist for ADOPTION TIMING: build now
what nobody has; deliberately wait where the field is about to commoditize (Ollama's
Anthropic API turned "local agents" from a project into a config file — that's the
pattern to catch early).

## Standing questions (tasks must name one in `feeds:`)

| id | question | current decision it feeds |
|----|----------|---------------------------|
| SQ1 | Is anyone shipping CAUSAL memory-utility measurement (did memory change the action + outcome)? | Ledger Replay Bench design + thesis early-warning — our differentiator |
| SQ2 | How are critics trained/deployed that catch a generator's real mistakes? | adversarial-critic-partner design |
| SQ3 | What memory/context-engineering practice is winning (injection altitude, consolidation, cost discipline)? | recall pipeline evolution |
| SQ4 | What can each harness actually deliver (hooks, events, models-behind-APIs)? | integration tiers matrix |
| SQ5 | What's the local-model frontier (models, tool-calling quality, tuning, serving)? | fleet composition + critic trainability |

## Sources

| source | feeds | watching for | last-swept |
|--------|-------|--------------|------------|
| arXiv follow-ups: 2602.16313 (MemoryArena), 2605.17641 (CMI), 2407.00215 (CriticGPT), 2407.13692 (prover-verifier) | SQ1, SQ2 | new versions, citing papers | 2026-07-02 (tasks 001/002) |
| Letta / Mem0 / Zep blogs + releases | SQ1, SQ3 | anyone adding outcome-credit or replay evals | 2026-07-01 (competitive survey) |
| Anthropic engineering blog + Claude Code changelog | SQ3, SQ4 | hook/event surface changes, memory features, multi-agent patterns | 2026-07-02 (tiers arc) |
| Cursor changelog + hooks docs | SQ4 | hook capabilities (esp. inject-on-allow, beforeSubmitPrompt) | 2026-07-02 (pinned) |
| Ollama blog + releases | SQ4, SQ5 | API compat, tool-call parsing fixes, scheduler/VRAM changes | 2026-07-02 (L0 research) |
| Nous Research / Hermes Agent repo + HermesBench | SQ2, SQ3, SQ5 | MoA mechanics, aggregator prompts, bench methodology | 2026-07-02 (task 005) |
| DeepSeek org (papers + repos) | SQ3, SQ5 | V4 architecture, training-pipeline gating, sparse attention | 2026-07-02 (task 004) |
| Qwen / Z.ai-GLM / Moonshot-Kimi release channels | SQ5 | coder-model releases, tool-format changes, local weights | 2026-07-02 (local-models research) |
| Terminal-Bench leaderboard (tbench.ai) | SQ5 | open-vs-frontier gap trend on shell loops (fleet ceiling) | 2026-07-02 |
| SWE-bench Pro (Scale scaffold) + tau-bench (benchlm) | SQ5 | standardized-scaffold rows only (vendor scaffolds lie) | 2026-07-02 |
| BFCL / Gorilla leaderboard | SQ5 | tool-calling scores for fleet candidates | 2026-07-02 (stale mirror noted) |
| simonwillison.net | SQ3, SQ4, SQ5 | field-wide signal amplifier; cheap delta | 2026-07-01 |
| Hamel Husain / eval-practice circle | SQ1, SQ3 | eval methodology that could sharpen the bench | 2026-07-01 |
| Manus + Dex/HumanLayer + Ronacher posts | SQ3 | context-engineering practice (C2-C4 sources) | 2026-07-02 (field survey) |
| HN + r/LocalLLaMA (via websearch queries, not feeds) | SQ5 | field reports: what actually works in harnesses | 2026-07-02 |
| unsloth / axolotl / llama-factory releases | SQ2, SQ5 | AMD/consumer-GPU training support (critic trainability) | 2026-07-02 (task 003) |

## Cadence

- **Weekly**: one fleet sweep day — delta tasks generated from this table (template:
  `queue/_sweep-template.md`), max ~5 sweep tasks, grouped by standing question.
- **Evening reviews**: adjudicate — every finding becomes a hypothesis task, a roadmap
  note, or an explicit discard. Update `last-swept` here.
- **Monthly**: frontier synthesis pass (stage moves, adoption-timing calls).
- **Quarterly**: re-rank this table; prune two-sweep-silent entries.
