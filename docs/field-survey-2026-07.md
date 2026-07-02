# Field survey: what the best practitioners can teach this system (2026-07-02)

> Three parallel research passes over (1) the Claude Code skills ecosystem, (2) prominent
> individual practitioners, (3) the agent-memory / context-engineering canon. All sources
> fetched and verified 2026-07-02. Companion to `docs/leapfrog-plan.md` and the Greptile
> research note (ADR_0702010906_4755). Raw per-source detail lives in the session that
> produced this; everything load-bearing is condensed here.

## How to read this

Findings are graded: **ADOPT** (concrete mechanism, sliceable), **HAVE** (we already do it
-- listed because independent validation matters), **DISSENT** (a credible practitioner
position that challenges our design; kept visible on purpose).

---

## 1. The strongest convergences (multiple independent sources, same mechanism)

### C1. The promotion ladder is real, and graduation is one rung of it
- Anthropic best practices: *"If Claude already does something correctly without the
  instruction, delete it or convert it to a hook."*
- Geoffrey Huntley's "signs": when the loop fails the same way twice, add a guardrail line
  to the always-loaded prompt ("tuning Ralph like a guitar") -- https://ghuntley.com/ralph/
- Boris Cherny: CLAUDE.md held at ~2,500 tokens where *"every line earns its place."*
- Us: `graduate` (2026-07-02) covers the top rung (lesson -> hook-enforced).

**ADOPT:** mechanize the full ladder, driven by funnel data:
`JIT lesson (recall-at) -> standing sign (AGENTS.md line) -> forcing function (hook/guard)`.
Credit data decides promotion: repeatedly-`helped` lesson => wrap-time candidate for a
standing sign; a sign whose rule gets automated => `graduate`. Demotion mirrors it (noise
votes -> decay -> supersede). This turns "forcing-function > JIT > docs > memory" from
philosophy into a mechanism with a data-driven actuator.

### C2. The credit loop has a confound, and the bench must control for it
- Manus (Yichao Ji): keep failures in context -- raw error traces alone improve behavior
  (https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus).
  => a FAIL->SUCCESS flip may be caused by the in-context error trace, NOT the surfaced
  lesson. **Our value rate can silently over-credit.**
- CAUSAL-LoCoMo / CMI (arXiv 2605.17641): counterfactual add/remove of INDIVIDUAL memories;
  metrics: useful-memory F1, bad-memory rejection, poisoned-memory adoption.
- MemoryArena (arXiv 2602.16313): interdependent agentic tasks; memory ablation drops
  completion ~80%->~45%; LoCoMo-perfect agents do poorly. Published replay-bench methodology.
- superpowers `verification-before-completion`: *"NO COMPLETION CLAIMS WITHOUT FRESH
  VERIFICATION EVIDENCE."*

**ADOPT (bench design requirements, Wave B):** (a) the recall-off replay arm MUST keep raw
error traces (it does if we replay real episodes -- now written down); (b) upgrade
on/off replay to per-lesson counterfactual swaps; (c) report useful-lesson F1 +
poisoned-adoption, token-cost-normalized (Mem0's critique: a 92-score system at 70k
tokens/query is not the same product as one at 7k). Differentiation vs MemoryArena/CMI:
REAL production episodes, not synthetic tasks. The bench is validated by the field now,
no longer novel -- move accordingly.

### C3. Injection altitude: action-time is the lowest-leverage tier
- Dex Horthy (12-factor-agents; ACE-FCA): review leverage is research > plan > code --
  *"a bad line of a plan could lead to hundreds of bad lines of code."* PreToolUse lessons
  arrive after the plan is committed.
- Every/Kieran Klaassen: *"Plan and review steps should comprise 80 percent"* of time.
- HAVE: SessionStart whisper (2026-07-02) is session-altitude; PreToolUse is code-altitude.

**ADOPT:** plan-time recall -- surface lessons relevant to the USER'S PROMPT (UserPromptSubmit
hook or boot --task ranking already does this for session start), rate-limited,
silent-when-empty. Keep PreToolUse for gotchas (its precision is the differentiator: even
243k-star superpowers only surfaces at SessionStart).

### C4. Injections must be cache-stable and observable
- Manus: KV-cache hit rate is THE production metric; one-token prefix churn = 10x cost.
  Per-action varying top-3 injection is cache-hostile.
- Armin Ronacher: pins fixed cache points; dynamic injection invalidates the cache tail
  (https://lucumr.pocoo.org/2025/11/21/agents-are-hard/).
- Mario Zechner: *"I want to inspect every aspect of my interactions with the model"* --
  harnesses that inject behind your back are the enemy
  (https://mariozechner.at/posts/2025-11-30-pi-coding-agent/).

**ADOPT:** (a) skip injection when the top-3 set is unchanged since last injection
(anti-repeat already covers the common case -- extend to full-set identity); (b) byte-stable
lesson formatting, never reorder; (c) an inspectable injection log via a door verb (we
already write impressions; expose them). Answers the "hidden state" objection and is
required for honest crediting anyway.

### C5. Lesson anatomy: the ecosystem converged on a schema
- superpowers skill anatomy: trigger-phrased descriptions (*"Use when encountering any bug,
  test failure, or unexpected behavior, BEFORE proposing fixes"*), Iron Laws,
  rationalization tables (excuse -> reality), red-flag phrases, escalation rules
  ("3+ failed fixes -> question the architecture").
- Every ce-compound: schema'd frontmatter (`symptoms`, `root_cause`, `applies_when`,
  `problem_type`), a **"What Didn't Work"** section, and a DETERMINISTIC 5-dimension
  overlap score (problem/root-cause/solution/files/prevention) deciding
  update-vs-create-vs-flag-for-consolidation.
- anthropics/skills skill-creator: 3-tier disclosure budgets -- ~100 words always-loaded,
  <500-line body on trigger, unlimited references on demand. Descriptions should be
  "a little bit pushy."
- contains-studio: 3-4 concrete usage examples in the description measurably improve
  triggering.
- LongMemEval-V2 taxonomy: workflow knowledge / environment gotchas / dynamic state /
  premise awareness. Lance Martin: episodic / procedural / semantic typing.

**ADOPT:** (a) trigger-phrase the `learn` template ("Use when <symptom>, before <action>";
"Don't use when <contraindication>") -- same as the SKILL.md finding from the Greptile
detour, now triple-confirmed; (b) lift ce-compound's 5-dim overlap as a write-time dedup
check (deterministic, pure Python) -- on high overlap suggest re-recording the existing
experiment name instead of minting a near-dupe; (c) our provenance/track-record tags are
the ~100-word tier; `recall --full` is tier 2 -- the 3-tier budget already fits.

### C6. Consolidation ("dreaming") is the missing hygiene loop
- Letta Context Repositories (Feb 2026): sleep-time reflection + defragmentation toward
  "15-25 focused files" (https://www.letta.com/blog/context-repositories/).
- Boris Cherny (mid-2026): leans on native auto-memory + /dream consolidation.
- Jesse Vincent: mined 2,249 files of past-session corrections into candidate skills.
- ce-compound: 2-3 dimension overlap => flag for consolidation.

**ADOPT:** an offline `consolidate` pass over the corpus: cluster near-dupes (5-dim
overlap), propose supersessions + graduation candidates, human-gated. This is the
leapfrog plan's D4 "dreaming slice," now with a concrete deterministic algorithm.
Note: Letta ships this with ZERO quantitative evaluation -- our funnel measures what
their flagship can't. That gap is the portfolio story.

---

## 2. Singular finds worth keeping

- **Correction->lesson reflex (Boris Cherny):** *"Every time Claude makes a mistake, I
  don't tell it to do it differently. I tell it to write it to the CLAUDE.md."* His team
  tags `@.claude` on PRs so review comments become memory. The creator of Claude Code runs
  our core loop MANUALLY -- strongest possible validation, and the marketing line. ADOPT:
  a correction-intake ritual (wrap-time "corrections this session" candidates; standing
  AGENTS.md line).
- **Anthropic memory tool is PULL, not push** (+39% on agentic search with memory+context
  editing): we have `recall`/`recall --full` as the pull path -- expose it prominently in
  boot output so mid-task pulls are one hop. (HAVE, mostly.)
- **Cognition (Don't Build Multi-Agents):** a lesson is aggressive compression -- it strips
  the implicit decisions of its source episode; cross-agent lessons are the
  conflicting-assumptions hazard. ADOPT: auto-attach source-episode refs (ledger pointers)
  to lessons at learn time so the receiving agent can expand the original trace.
- **Metrics as artifact (Willison SQLite / Zechner JSON / disler dashboard):** export the
  surfaced->used->credited event stream as JSONL; a tiny live dashboard on our own hook
  events is cheap and is the demo. (disler's multi-agent-observability repo is the pattern.)
- **Steinberger's deterministic refactor kit:** jscpd (duplication), knip (dead code),
  AST-grep rules as a scheduled quality routine -- deterministic-first, bundleable as a
  door command.
- **CLI-over-MCP, empirically (Zechner):** MCP servers burn 13-18k tokens/session standing;
  models learn CLIs from --help at near-zero cost. Validates agent_cli as the door; keep
  the MCP layer thin parity.

## 3. Standing dissent (kept visible on purpose)

1. **Ronacher:** hook guidance under-delivers ("only way to guide is denies"); dynamic
   injection has real cache cost. => measure injection token cost in the funnel.
2. **Steinberger:** subagents/elaborate scaffolds are "charade." => the funnel must prove
   value or the feature dies; value rate is the rebuttal, not argument.
3. **Cherny mid-2026:** model-native auto-memory + /dream may eat hand-built memory layers.
   => reinforces leapfrog Wave E: package as the intelligence loop ON TOP of native memory,
   not a parallel store.
4. **Zechner:** no hidden state, files only, no hooks. => answered by observable injections
   (C4c); partially conceded by keeping everything cat-readable (Miessler agrees).
5. **Manus:** our value rate may over-credit (C2) -- do not headline it externally until the
   counterfactual bench exists.

## 4. Ranked adoption plan (impact x ease, convergence-weighted)

| # | Slice | Size | Sources |
|---|-------|------|---------|
| 1 | Cache-stable + observable injection (skip-if-unchanged, byte-stable, injection-log verb) | S | Manus, Ronacher, Zechner |
| 2 | Plan-time recall (prompt-relevant lessons at UserPromptSubmit; silent-when-empty) | S-M | Dex, Every |
| 3 | Trigger-phrased learn template + 5-dim overlap dedup at write time | S-M | superpowers, ce-compound, skill-creator |
| 4 | Promotion-ladder mechanization (helped>=N -> wrap-time "sign" candidate; sign automated -> graduate) | M | Huntley, Cherny, Anthropic |
| 5 | Consolidate verb (offline near-dupe clustering -> supersession/graduation proposals, human-gated) | M | Letta, ce-compound, Vincent |
| 6 | Correction->lesson intake (wrap section + standing line) | S | Cherny |
| 7 | Funnel JSONL export + live hook-event dashboard | M | disler, Zechner, Willison |
| 8 | Bench upgrade: per-lesson counterfactual, error-trace-preserving off-arm, F1/poisoned metrics, token-normalized | L (Wave B) | CMI, MemoryArena, Manus |
| 9 | Door as SKILL.md folder (cross-harness distribution; Wave E) | M | Willison, Vincent, anthropics |
| 10 | Source-episode refs on lessons (expandable provenance) | M | Cognition |

## 5. Primary sources index

Skills ecosystem: https://github.com/anthropics/skills · https://github.com/obra/superpowers ·
https://github.com/EveryInc/compound-engineering-plugin · https://github.com/wshobson/agents ·
https://github.com/contains-studio/agents · https://github.com/hesreallyhim/awesome-claude-code ·
https://github.com/nizos/tdd-guard · https://github.com/disler/claude-code-hooks-mastery ·
https://github.com/disler/claude-code-hooks-multi-agent-observability

Practitioners: https://simonwillison.net/2025/Oct/16/claude-skills/ ·
https://lucumr.pocoo.org/2025/11/21/agents-are-hard/ · https://lucumr.pocoo.org/2026/6/23/the-coming-loop/ ·
https://mariozechner.at/posts/2025-11-30-pi-coding-agent/ · https://mariozechner.at/posts/2025-08-15-mcp-vs-cli/ ·
https://steipete.me/posts/just-talk-to-it · https://ampcode.com/notes/how-to-build-an-agent ·
https://ghuntley.com/ralph/ · https://github.com/danielmiessler/fabric ·
https://howborisusesclaudecode.com/ · https://blog.fsck.com/2025/10/09/superpowers/

Canon: https://github.com/humanlayer/12-factor-agents ·
https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md ·
https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents ·
https://www.anthropic.com/engineering/writing-tools-for-agents · https://claude.com/blog/context-management ·
https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus ·
https://rlancemartin.github.io/2025/06/23/context_engineering/ ·
https://www.letta.com/blog/context-repositories/ · https://cognition.com/blog/dont-build-multi-agents ·
https://arxiv.org/abs/2602.16313 (MemoryArena) · https://arxiv.org/abs/2605.17641 (CMI) ·
https://arxiv.org/abs/2605.12493 (LongMemEval-V2) · https://mem0.ai/blog/ai-memory-benchmarks-in-2026
