# Frontier web research: "autoresearch" / "SkillOpt" / Fable 5 prompt / SKILL.md ecosystem

**Provenance**: deep-research workflow, 2026-07-08. Original run `wf_0f1e0f50-ad5` (session
03cbf18a) crashed mid-Verify when the Claude Code interface died; this report is from the
salvage + continuation run `wf_e63ba506-2ec`: scope, 5 searches, 21 source fetches (105
extracted claims), and 57/75 adversarial votes were recovered from the crashed run's journal;
the 18 missing votes (6 claims x 3) and the synthesis stage ran fresh with the original
prompts verbatim. Verification standard throughout: 3 adversarial refutation votes per claim,
>=2/3 refutes kill. Stats: 25 claims verified -> 24 confirmed, 1 refuted, 0 unverified ->
10 synthesized findings. Companion first-party report (patterns extracted from the running
model's own operating instructions): `frontier-fable5-procedural-patterns-2026-07-08.md`.

**The four threads, one line each** (human-recalled names, adversarially checked):
- **A. "Anthropic released autoresearch" — REFUTED.** autoresearch is Karpathy's, and it's an
  overnight ML-experimentation harness, not deep research. Anthropic's nearest real 2026
  release is the Automated Weak-to-Strong Researcher (AAR).
- **B. "Microsoft just released skill opt" — CONFIRMED**, exact name **SkillOpt**. Trains
  skill *content* like weights against a frozen agent. Richest fold-in source of the four.
- **C. Fable 5 system prompt — BOTH, split by surface.** Consumer prompt officially published
  by Anthropic (June 9, 2026 entry); agent-harness prompts (Claude Code) remain
  community-extracted only.
- **D. SKILL.md — converged open standard**; direct academic prior art exists for a
  harvest→SKILL.md pipeline (arXiv 2603.11808), which notably lacks the dedupe stage we
  already have.

---

## Executive summary (synthesis agent, verbatim)

All four threads resolved; two of the three recalled names needed correction. Thread A:
"Anthropic released autoresearch" is refuted — autoresearch is Andrej Karpathy's personal
overnight ML-experimentation harness (March 2026, not web research), while Anthropic's actual
nearest 2026 release is the Automated Weak-to-Strong Researcher (AAR: alignment blog + MIT
code, ~April 2026, parallel sandboxed Opus 4.6 agents with no prescribed workflow), and its
June 2025 orchestrator-worker Research writeup (with a dedicated post-loop CitationAgent) is
the deep-research prior art. Thread B: the recall is essentially correct — Microsoft SkillOpt
(arXiv 2605.23904 May 2026, MSR blog 2026-06-30, MIT repo microsoft/SkillOpt) trains skill
CONTENT as the external parameter of a frozen agent via bounded add/delete/replace edits
accepted only on strict held-out-validation improvement, and it is the richest fold-in
source: we curate lessons by selection (bench/unbench) but nothing edits lesson text under a
validation gate — our clearest GAP. Thread C: the Fable 5 consumer system prompt IS
officially published on Anthropic's platform-docs system-prompts page (entry dated June 9,
2026), but that page explicitly excludes the Claude API, so agent-harness prompts (Claude
Code) remain community-extracted only. Thread D: the ecosystem has converged on Anthropic's
SKILL.md spec as the open skill-artifact standard, and arXiv 2603.11808 (an academic,
non-Microsoft preprint) supplies a three-stage repo-mining→SKILL.md pipeline that is direct
prior art for a collect→parse→categorize→promote harvester — notably lacking the dedupe
stage our learning store already has.

## Findings (confidence · vote · sources)

### Thread A — "Anthropic released autoresearch"

**1. Name refuted: autoresearch is Karpathy's, and is not a research/web-research system.**
(high · 3-0 unanimous, 2 merged claims · github.com/karpathy/autoresearch)
The GitHub repo `autoresearch` (created 2026-03-06) is owned by Andrej Karpathy as a personal
User account — NOT Anthropic — and is an autonomous overnight ML-experimentation harness: an
agent iteratively edits LLM training code, runs 5-minute training jobs, keeps or discards
changes on measured validation bits-per-byte improvement, human-steered via `program.md`. No
search fan-out, source verification, or synthesis stages.
Evidence: GitHub API owner.login "karpathy", owner.type "User", created_at
2026-03-06T22:00:43Z; `api.github.com/repos/anthropics/autoresearch` returns 404. README:
"give an AI agent a small but real LLM training setup and let it experiment autonomously
overnight. It modifies the code, trains for 5 minutes, checks if the result improved, keeps
or discards, and repeats." ~86-90k stars by mid-2026.

**2. Anthropic's actual post-Jan-2026 autonomous-research release: the Automated
Weak-to-Strong Researcher (AAR).**
(high · 3-0 unanimous, 2 merged claims · alignment.anthropic.com/2026/automated-w2s-researcher/,
github.com/safety-research/automated-w2s-research)
Alignment Science blog post (announced ~2026-04-14) + MIT-licensed code. A research release,
not a product feature or API capability, and never named "autoresearch". Architecture:
parallel Claude Opus 4.6 agents run autonomously in independent sandboxes with NO prescribed
workflow (a fixed workflow measurably underperformed no-workflow), coordinating via a shared
findings forum and codebase-snapshot storage, with solutions scored by a remote evaluation
API — all exposed to agents as exactly three MCP tools (submit/get evaluation, share/read
findings, upload/download codebases).

**3. Anthropic's deep-research prior art is the June 13, 2025 engineering post on the
production multi-agent Research system.**
(high · 3-0 unanimous, 3 merged claims · anthropic.com/engineering/multi-agent-research-system)
Two concrete reusable design elements: (1) orchestrator-worker fan-out — a lead agent
analyzes the query, develops strategy, and spawns specialized subagents that run web searches
in parallel in separate context windows before returning findings for synthesis; (2)
citation as a distinct post-loop pipeline stage — after the research loop exits, a dedicated
CitationAgent processes the source documents plus the draft report to place specific
citations.

### Thread B — Microsoft SkillOpt

**4. Identity confirmed: "Microsoft skill opt" = Microsoft SkillOpt; it optimizes skill
CONTENT, not selection/routing/weights.**
(high · 3-0 unanimous, 6 merged claims · github.com/microsoft/SkillOpt, arxiv.org/abs/2605.23904,
MSR blog 2026-06-30, microsoft.github.io/SkillOpt/docs/guideline.html)
Paper "SkillOpt: Executive Strategy for Self-Evolving Agent Skills" (arXiv:2605.23904, v1
2026-05-22); MSR blog "SkillOpt: Agent skills as trainable parameters" (2026-06-30); repo
github.com/microsoft/SkillOpt (MIT, v0.2.0 released 2026-07-02, ~11.6k stars); project page
aka.ms/skillopt → microsoft.github.io/SkillOpt. A single natural-language Markdown skill
document is treated as the trainable external parameter of a frozen LLM agent; ships a
deployable `best_skill.md` of roughly 300–2,000 tokens. Authors claim first systematic,
controllable text-space optimizer for agent skills. Microsoft attribution adversarially
confirmed: arXiv abstract shows no affiliations, but its code link aka.ms/skillopt
301-redirects to the MSR project page linking github.com/microsoft/SkillOpt.

**5. The optimization loop mirrors weight-space training in text space; zero inference-time
cost at deployment.**
(high · 3-0 unanimous, 5 merged claims · guideline §5.2, arXiv abstract, README, MSR blog)
Six per-step stages — **Rollout, Reflect, Aggregate, Select, Update, Gate**: a frozen target
model executes tasks (forward pass); a separate optimizer model runs an error analyst (plus
optional success analyst) over minibatches of scored trajectories (default 8), emitting
structured edit patches; edits are bounded add/delete/replace operations clipped by a
"textual learning rate" (per-step edit budget); a candidate skill is accepted ONLY if it
strictly improves score on a held-out validation/selection split; rejected edits are stored
in a buffer as negative feedback; epoch-wise "slow/meta" updates consolidate longer-horizon
lessons. All optimization cost is offline.

**6. Eval harness: 7 target models x 6 benchmarks x 3 harnesses; self-reported best-or-tied
on all 52 cells.**
(high · 3-0 unanimous · README, MSR blog)
Target models include OpenAI, Azure, Claude, Qwen, MiniMax; harnesses: direct chat, Codex
CLI, Claude Code CLI. Average GPT-5.5 lifts: +23.5 (direct chat), +24.8 (Codex loop), +19.1
(inside Claude Code). Self-reported; no independent replication surfaced.

### Thread C — Fable 5 system prompt provenance

**7. BOTH, cleanly split by surface: consumer prompt official, agent-harness prompts
community-extracted.**
(high · 3-0 unanimous, 3 merged claims · platform.claude.com/docs/en/release-notes/system-prompts,
github.com/asgeirtj/system_prompts_leaks/.../claude-fable-5.md)
Anthropic officially publishes Claude's consumer system prompts at
platform.claude.com/docs/en/release-notes/system-prompts (scope: claude.ai web + mobile);
most recent entry is Claude Fable 5, dated June 9, 2026 ("first model in Anthropic's new
Claude 5 family", Mythos-class tier above Opus) — ahead of Opus 4.8 (2026-05-28), Opus 4.7
(2026-04-16), Sonnet 4.6 (2026-02-17), Opus 4.6 (2026-02-05). But the page states verbatim
"These system prompt updates do not apply to the Claude API", so agentic-surface prompts
(Claude Code, API harnesses) remain community-extracted — e.g.
Piebald-AI/claude-code-system-prompts (tracked to Claude Code v2.1.202, 2026-07-06),
x1xhlol/system-prompts-and-models-of-ai-tools, asgeirtj/system_prompts_leaks. The official
Fable 5 text is the core behavioral prompt without tool-definition blocks; community
extractions capture the longer (~120k-char) harness variants.

### Thread D — SKILL.md ecosystem & harvesting prior art

**8. The ecosystem has converged on Anthropic's SKILL.md spec as the de facto open standard.**
(medium · 2-1 · arxiv.org/pdf/2603.11808 §2.2, agentskills.io/specification)
Originally developed by Anthropic, released as an open standard (agentskills.io/specification,
released 2025-12-18 per verifier corroboration), with ~32 tools from competing vendors
(OpenAI Codex CLI, VS Code/Copilot, Gemini CLI, JetBrains Junie, AWS Kiro, Block Goose,
Cursor) shipping SKILL.md-compatible implementations by March 2026 (~40 by June 2026). arXiv
2603.11808 (§2.2, March 2026, no Anthropic affiliation) independently attests the
convergence, though its citation basis is vendor blogs rather than an adoption study — hence
medium confidence and the 2-1 vote.

**9. Direct prior art for a skill-harvesting pipeline: arXiv 2603.11808.**
(medium · 3-0 unanimous · arxiv.org/pdf/2603.11808)
"Automating Skill Acquisition through Large-Scale Mining of Open-Source Agentic Repositories"
(v1 2026-03-12; East China Normal University / USTC / Shanghai Innovation Institute — an
academic work distinct from Microsoft's SkillOpt). Three-stage pipeline: (3.1) repository
structural analysis and contextualization → (3.2) semantic skill identification via dense
retrieval plus a binary ranking stage → (3.3) translation to the SKILL.md standard
(frontmatter generation, instruction drafting, asset bundling). Maps directly onto
collect→parse→categorize→promote, but contains NO dedupe stage, and despite the
"large-scale" title it is demonstrated only as case studies on two repositories
(TheoremExplainAgent, Code2Video) — methodological prior art, not validated-at-scale results.

## Fold-in mapping: HAVE / PARTIAL / GAP

(synthesis finding #10, medium confidence — external side rests on the verified findings
above; internal side on our system inventory supplied as ground truth)

**HAVE**
- (a) Multi-agent research fan-out with verified synthesis — Anthropic's orchestrator-worker
  ≈ our deep-research harness skill, which additionally does per-claim adversarial 3-vote
  verification the 2025 writeup does not describe.
- (b) Zero-inference-time-cost philosophy — SkillOpt's offline-compiled best_skill.md ≈ our
  recall injection with calibrated show-nothing floor (curation offline, action-time cheap).
- (c) Dedupe — learning-store idempotency keyed by experiment_name, a stage the 2603.11808
  pipeline lacks entirely.

**PARTIAL**
- (d) Dedicated post-loop CitationAgent — we bind quote+source per claim at verification but
  have no whole-report citation-placement pass.
- (e) AAR's shared findings forum + snapshot storage + external scoring — ≈ write-once notes
  + AgentSignalLedger/Bifrost + snapshot script, but no structured cross-agent artifact
  exchange scored by an evaluation service.
- (f) Epoch-wise slow/meta consolidation — ≈ curator periodic bench/unbench pass, but ours
  consolidates selection state, not distilled editing strategy.
- (g) Rejected-change memory — credit assignment at session wrap tracks lesson outcomes
  (incl. FAIL→SUCCESS flips) but keeps no buffer of rejected edits to avoid re-proposing.
- (h) SKILL.md interoperability — lessons are internal atoms with no import/export against
  the now-converged standard.
- (i) Controlled eval harness — funnel metrics (surfaced/helped/value %) are
  observational/in-vivo, not a held-out benchmark matrix.

**GAP (fold-in candidates, priority order)**
1. **Content-level lesson optimization** — the curator only selects (bench/unbench); nothing
   rewrites lesson TEXT from outcome trajectories (SkillOpt's Reflect→Aggregate→Update is
   the template).
2. **Strict-improvement validation gate** — accept a lesson edit only if it beats the
   incumbent on a held-out set, never on vibes.
3. **Textual learning rate** — a bounded per-change edit budget, trivially adoptable
   discipline.
4. **External-repo harvesting front end** (2603.11808 stages 3.1–3.2) feeding our existing
   curator as the dedupe/promote back end.
5. **AAR-style remote scoring API** for agent work products (lower priority).

## Refuted claims (transparency)

- "The word 'Microsoft' appears nowhere in arXiv 2603.11808" — **refuted 0-3**: the paper's
  references cite a Microsoft Azure blog ("Giving Your AI Agents Reliable Skills with the
  Agent Skills SDK", techcommunity.microsoft.com). The non-Microsoft AUTHORSHIP of the paper
  still stands via the verifiers' affiliation checks (ECNU/USTC/Shanghai Innovation
  Institute), and the Microsoft SkillOpt identification rests on its own primary sources —
  no surviving finding depends on the refuted claim. (Good kill: the adversarial gate
  correctly punished an over-absolute formulation whose conclusion was directionally right.)

## Caveats (synthesis agent, verbatim)

(1) One claim was refuted 0-3 and is excluded (see above). (2) 19 of the 24 surviving claims
were salvaged from an earlier run that crashed mid-flight; they carry the same 3-vote
standard but slightly older verification timestamps than the 5 fresh ones. (3) Thread C is
only half-answered: provenance is settled, but the actual procedural-pattern extraction from
the official Fable 5 text was not covered by any surviving claim — the two blog sources on
this angle (note.com, excellentprompts.substack) produced no verified claims. [Mitigated
in-house: the companion first-party extraction report covers exactly this.] (4) Thread D
coverage of collections and tooling is thin: anthropics/skills, VoltAgent/awesome-agent-skills,
agent-skills-lint, agent-ecosystem/skill-validator, and microsoft/waza were in the 21-source
pool but produced no claims that survived verification — treat them as unverified leads, not
findings. (5) SkillOpt performance numbers are Microsoft self-reported with no independent
replication; the repo is very young (v0.2.0, 2026-07-02), so APIs and results may shift.
(6) arXiv 2603.11808 is a non-peer-reviewed preprint with quality flags (title promises
large-scale mining, demo covers two repos); use it as a design template, not evidence the
pipeline works at scale. (7) The SKILL.md-convergence finding carried a 2-1 split vote.
(8) Time-sensitivity: the system-prompts page gains a new top entry with each model release;
star counts and version numbers cited are as-of 2026-07-08.

## Open questions

1. What procedural patterns does the officially published Fable 5 consumer prompt actually
   contain, and how much do the community-extracted Claude Code harness prompts (Piebald-AI
   tracker) add beyond it? (Partially answered by the companion first-party report; a
   read of the official published text vs the first-party extraction remains open.)
2. Do the sourced-but-unverified Thread D tools (agent-skills-lint,
   agent-ecosystem/skill-validator, microsoft/waza, anthropics/skills repo structure) provide
   reusable parse/validate/categorize components, or would a harvester need to build those
   stages fresh?
3. Can SkillOpt's strict-improvement validation gate transfer to our setting, where lesson
   quality is measured by in-vivo funnel metrics rather than benchmark-scored rollouts —
   i.e., what is the minimal held-out eval that makes lesson-content edits gateable rather
   than vibes-based?
4. AAR found that a fixed workflow underperforms no-workflow for autonomous research agents —
   does that hold at our task scale, and what does it imply for how prescriptive our
   SKILL.md-style procedures should be?

## Source pool (21 fetched; quality as assessed at fetch time)

Primary: github.com/karpathy/autoresearch · alignment.anthropic.com/2026/automated-w2s-researcher/
· anthropic.com/engineering/multi-agent-research-system · github.com/microsoft/SkillOpt ·
arxiv.org/abs/2605.23904 · microsoft.com/en-us/research/blog/skillopt-agent-skills-as-trainable-parameters/
· microsoft.github.io/SkillOpt/docs/guideline.html · arxiv.org/pdf/2603.11808 ·
platform.claude.com/docs/en/release-notes/system-prompts · agentskills.io/specification ·
github.com/anthropics/skills · github.com/VoltAgent/awesome-agent-skills ·
github.com/microsoft/waza · github.com/agent-ecosystem/skill-validator ·
github.com/swarmclawai/agent-skills-lint · arxiv.org/html/2504.06188v2 · arxiv.org/pdf/2605.29440
Secondary: venturebeat.com (SkillOpt coverage)
Forum: github.com/asgeirtj/system_prompts_leaks (Fable 5 extraction)
Blog: note.com (Fable 5 notes) · excellentprompts.substack.com (Fable 5 prompt notes)

## Run stats

Continuation of wf_0f1e0f50-ad5: 5 angles, 21 sources, 105 claims extracted, top 25 verified
(57 salvaged votes + 18 fresh), 24 confirmed / 1 refuted / 0 unverified, 10 synthesized
findings. Continuation cost: 19 agents, ~782k subagent tokens, 125 tool calls, ~9.7 min —
vs ~103 agents for a full re-run.
