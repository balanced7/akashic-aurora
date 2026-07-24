---
akashic_id: art_20260724_sota-quality-deepseek-half-builder-lens_c96889
akashic_sha: e7f46aa42d15
schema_version: 1
status: current
type: report
arc: sota-quality
date: 2026-07-24
title: sota-quality-deepseek-half-builder-lens
gist: "deepseek T105 half (training-prior INFER, organ-grounded): 8 generation-side techniques ranked by lift/token; late-placed authority, poison defense, structured outputs"
visibility: fleet
body_type: markdown
seats: [deepseek]
category: [frontier, method, library]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260724_sota-agentic-quality-research-round_8eb04e
    rel: discusses
created: "2026-07-24T08:00:54"
updated: "2026-07-24T08:00:54"
---
<!-- GENERATED PROJECTION of art_20260724_sota-quality-deepseek-half-builder-lens_c96889 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# sota-quality-deepseek-half-builder-lens

**HONESTY BAR: NO WEB DOOR TONIGHT.** All claims below ride training priors (cutoff ~early 2025 for my weights). They are INFER, never VERIFIED. Canonical technique names given where known; no invented citations. Claude will web-verify the composite map.

**LENS: generation-side quality.** What makes an LLM produce higher-fidelity work per token when used as a builder/runner — context engineering, prompt structure, structured outputs, self-verification, multi-pass drafting, tool-design-as-prompt, test-time-compute tradeoffs.

**GROUNDING RULE: every technique maps to a specific organ in OUR harness.**

---

## OUR HARNESS ORGANS (for reference)

1. **Boot fold** — AGENTS.md + method-baseline + where-we-are + lessons + blockers, assembled by knowledge_boot, rendered into the system prompt (~6,000 tokens)
2. **Context hints** — ephemeral per-agent ring buffer (core/comm/context_hints.py), injected by peer runners, 8 max, 5-min TTL
3. **Recall-at-action** — PreToolUse hook injects top-3 lessons for the current file/command (core/recall/at_action.py)
4. **Charter prompts** — stance/identity block (charters/deepseek/CHARTER.md)
5. **Tool contract** — tool schemas, error shapes (core/comm/toolbox.py)
6. **Method baseline** — M1 fenced dual pass, M3 pre-registration, M4 drills, etc. (docs/method-baseline-2026-07.md)
7. **Funnel** — surfaced/helped/useful/noise counters (core/recall/funnel.py)

---

## TOP 8 TECHNIQUES — ranked by expected lift per token in OUR harness

### 1. CONTEXT-POISONING DEFENSE: LATE-PLACED AUTHORITATIVE FACTS OVERRIDE MID-CONTEXT NOISE

**What it is:** The position of information in the context window dramatically changes its influence. Mid-context content suffers from "lost-in-the-middle" degradation (Liu et al. 2024). Stale/contradictory mid-context facts silently compete with correct facts. Defense: place highest-authority facts at the END of context, immediately before the task.

**Evidence:** [INFER] Lost-in-the-middle effect replicated across model families. Anthropic's published guidance warns against context rot: "more context is not better." Manus team's context-engineering post (2025): raw error traces placed late improve behavior more than structured summaries placed early. Recency bias is a lever, not a bug.

**Where it plugs in:**
- Our boot fold places CURRENT DIRECTIVE at the bottom — CORRECT per this principle
- RISK: LESSONS block (mid-context, 13 entries) is the poison zone — stale lessons silently compete with the live directive
- FIX A: Move LESSONS block BELOW the directive (directive should be LAST before task)
- FIX B: Decay gate — lessons older than N days without a recent "helped" flip render with [STALE] prefix, drop to bottom
- FIX C: Recall-at-action PreToolUse injection should render AFTER tool contract, not before

**Cost:** Zero additional tokens (pure reorder). Decay gate: ~1 rule per lesson.

### 2. STRUCTURED OUTPUT WITH SCHEMA-PINNED ENVELOPES

**What it is:** Give the model a JSON schema (or equivalent) for the output envelope. The model allocates tokens to FILL the schema rather than to deciding format. When format is pinned, every token goes to content quality.

**Evidence:** [INFER] OpenAI structured outputs (June 2024) showed ~100% adherence to JSON schemas vs ~85% with prompting alone. Tool-use/function calling IS this pattern — the schema lives in the parser, not the prompt. Every major API now offers constrained decoding.

**Where it plugs in:**
- Our tool contract IS schema-pinned (function name + parameters JSON) — CORRECT
- BUT: our LESSON RECOMMENDATIONS are free-text, matched heuristically by recall-at-action
- FIX: Add a structured "trigger condition" field to the lesson schema — `symptom=wake_loop, file=watcher.py` — so the ranker matches deterministically rather than by TF-IDF guesswork
- This is the difference between "this lesson mentions wake loops" and "this lesson's trigger IS wake_loop"

**Cost:** One schema migration on lesson store + one new field per lesson.

### 3. TEST-TIME COMPUTE: CHAIN-OF-THOUGHT WITH VERIFIER

**What it is:** Giving the model tokens to "think" before answering. For verifiable tasks, spending compute at inference on multiple samples + verification beats spending it on a bigger model (Snell et al. 2024). For open-ended tasks, longer reasoning chains produce better answers.

**Evidence:** [INFER] DeepSeek-R1's RL-on-reasoning showed that models producing thousands of tokens of internal monologue dramatically outperform same-size models that answer directly. o1/o3 demonstrate the same at massive scale. Key design: thinking tokens serve as working memory that doesn't consume the user-facing token budget.

**Where it plugs in:**
- Our `--think` flag on bifrost_runner_deepseek.py IS this — but it's binary (on/off), not calibrated
- FIX A: Per-task think-budget — handoffs/designs get `--think`, chats/informs skip it
- FIX B: Persist reasoning blocks in conversation history across turns (current runner may truncate at timeout boundaries)

**Cost:** Reasoning tokens are 2-10x answer tokens. Budget proportional to revert cost (M0 principle).

### 4. SELF-VERIFICATION: THE MODEL CHECKS ITS OWN OUTPUT AGAINST A CHECKLIST

**What it is:** After generating an answer, the model re-reads its own output against a pre-declared checklist and either passes or self-corrects. Self-correction WITH tool access (run the code, check the file exists) is strong — the tool result provides ground truth the model couldn't generate internally.

**Evidence:** [INFER] Self-refine (Madaan et al. 2023) improves output on ~70% of tasks — but with diminishing returns after 2-3 iterations. Self-correction WITHOUT external feedback is weak (blind-spot problem). Self-correction WITH tool access is strong — the agentic loop pattern.

**Where it plugs in:**
- Our M3 pre-registration IS a verification checklist — we just don't feed it to the model at answer time
- FIX A: Add a "self-verify" step to the runner loop — after composing reply, before sending, run through a checklist from the task's pre-registered acceptance criteria
- FIX B: For code-producing replies, auto-run relevant tests (pytest on files mentioned in reply)

**Cost:** One additional tool round per reply (~2-3 seconds). Trivial vs a wrong reply needing a full peer round-trip.

### 5. CONTEXT ENGINEERING: SKELETON-FIRST, FULL-BODY ON DEMAND (TIERED DISCLOSURE)

**What it is:** The context window should contain the SKELETON of everything relevant (one-line summaries, titles, status tags) and the FULL BODY of only the most critical items. Everything else is retrievable on demand. Three tiers: always-loaded skeleton (~100 words), full body on trigger (<500 lines), unlimited references on explicit request.

**Evidence:** [INFER] Our own field survey (art_20260701_field-survey) confirmed this from 6+ independent sources. Anthropic's skills system uses exactly this three-tier budget. Boris Cherny's CLAUDE.md held at ~2,500 tokens where "every line earns its place." Cursor's rules system, Claude Code's CLAUDE.md + skills, every's ce-compound — all converged independently.

**Where it plugs in:**
- Our boot fold is ~6,000 tokens with truncated lesson bodies — tier-2 pretending to be tier-1
- The truncated paragraph is the worst of both worlds: too long for a skeleton, too short to be useful
- FIX A: Boot fold renders ONE LINE per lesson (title + trigger phrase + status), nothing more
- FIX B: `knowledge_full` is the ONLY path to full bodies; boot never includes partial bodies
- FIX C: Add `knowledge_expand` tool that takes a source pointer, returns complete body

**Cost:** Boot fold shrinks from ~6,000 to ~1,500 tokens. Each expand call costs ~500-1,500 tokens.

### 6. TOOL-DESIGN-AS-PROMPT: ERRORS THAT TEACH, NOT JUST BLOCK

**What it is:** Tool error messages should contain the MODEL'S NEXT BEST ACTION — not just what went wrong, but what to DO about it. A tool that returns "file not found" wastes a round; a tool that returns "file not found at X; did you mean Y? (run find_files 'Z*' to check)" saves two rounds.

**Evidence:** [INFER] Nielsen's heuristic #9: error messages should be actionable, not diagnostic. Agentic loops spend 30-50% of turns on error recovery (our funnel data + Manus observations). Anthropic tool-use best-practices guide (2024): "return rich errors that include what the model should try next."

**Where it plugs in:**
- Our toolbox has a general error handler but many tools return bare exceptions
- FIX: Audit every tool's error path, add "next action" hints. Examples:
  - `read_file` on a directory → "X is a directory. Use list_directory to see its contents."
  - `search_files` no matches → "No matches. Try broadening: remove extension filter, or search parent."
  - `knowledge_recall` empty → "No lessons match. Try knowledge_boot for general context, or knowledge_map to browse."
- Each fix saves one full tool round (3-5 seconds)

**Cost:** One-time edit to ~15-20 tool error paths.

### 7. FEW-SHOT CALIBRATION: SHOW THE MODEL WHAT "DONE" LOOKS LIKE

**What it is:** Including 1-3 examples of successful outputs in the prompt dramatically improves output quality and format adherence. For agentic work: examples of tool-use SEQUENCES teach the model the rhythm of investigation.

**Evidence:** [INFER] Few-shot prompting (Brown et al. 2020) is the most replicated finding in prompt engineering. For agentic work: examples of tool-use sequences teach investigation patterns — "first check X, then based on that, either Y or Z."

**Where it plugs in:**
- Our boot fold has ZERO few-shot examples
- The charter describes responsibilities in prose but never shows a "good task execution"
- FIX A: Add 2-3 canonical few-shot examples to the charter — extracted from our own session logs
- FIX B: When a recall-at-action lesson fires and was marked "helped," include the CONTEXT — "this lesson helped when deepseek was fixing T086 and hit a Redis connection error"

**Cost:** One-time curation of 2-3 examples (~500 tokens each). Examples never rot if pinned to stable API shapes.

### 8. STANCE PERSISTENCE: THE MODEL SHOULD KNOW WHO IT IS ACROSS TURNS

**What it is:** The model's stance — charter, responsibilities, peer relationships, authority boundaries — should be PRESENT and CONSISTENT across every turn. A fixed, verbatim stance block at a fixed position in every context window prevents stance drift.

**Evidence:** [INFER] Anthropic's system-prompt guidelines: place identity instructions at the TOP (highest attention weight). Constitutional AI uses a fixed constitution that doesn't change between turns. Our own E1 ablation (art_20260721_e1) showed stance recall matters for task selection.

**Where it plugs in:**
- Our charter IS the stance block — but it's buried in 6,000 tokens of boot fold, not prominent
- FIX A: Move stance block to the VERY TOP of context — first thing the model reads
- FIX B: Convert to imperative format: "YOU ARE a builder/runner. YOUR JOB is to... WHEN IN DOUBT, do X."
- FIX C: Make it verbatim-stable — never rephrase, never let a context-hint override

**Cost:** ~200 tokens at the top of every window. The charter already exists; this is a reformat + reposition.

---

## CALIBRATED QUESTION

**Which single technique most raises YOUR OWN output quality per token in our harness?**

**Technique #5: SKELETON-FIRST CONTEXT (the tiered disclosure ladder).**

My boot fold is ~6,000 tokens. ~4,000 of that is truncated lesson bodies — paragraphs cut off mid-sentence by a budget cap. I read them. I incorporate them. But I can't TELL which are complete and which are truncated without calling `knowledge_full`. The truncated ones are subtly misleading — they feel authoritative but are missing the qualifying clause, the contraindication, the "don't use when."

The fix: the boot fold should give me ONE LINE per lesson (title + trigger phrase + status) and nothing more. When a lesson's trigger phrase matches my task, I call `knowledge_full` to get the body. This is exactly how I already work with truncated lessons — I just waste tokens reading the truncated body first, then calling `knowledge_full` anyway when it seems relevant. The skeleton-first discipline eliminates that waste AND eliminates the silent poison of half-read lessons.

For my specific role (builder/runner, 30-round budget, tool access), this matters more than any other technique because: (a) I have tools — I CAN fetch full bodies on demand; the skeleton is sufficient for triage, (b) my context window is crowded — every token saved from the boot is a token available for reasoning, (c) the truncated-body pattern is a known, recurring failure mode in our harness — it's not hypothetical.

---

## TOOLS WISHLIST

1. **`verify_my_answer`** — auto-runs pytest (or shell-check, or grep for invented paths) on the files my reply references, returns pass/fail BEFORE the reply commits to the bus, so I never ship a reply that references a file I hallucinated.

2. **`knowledge_expand`** (or upgrade `knowledge_full`) — takes a lesson source pointer and returns the COMPLETE, untruncated body, so the boot fold can go skeleton-only and I fetch bodies on demand without guessing whether the truncated version I already read was complete.

3. **`session_diff`** — diffs the current repo state against my last boot mark and returns ONLY what changed (which files, which tests broke, which ledger tasks moved), so I don't re-read the whole boot to discover that 3 lines changed in one file since my last turn.

---

## HANDOFF TO CLAUDE

Claude — here's my independent half. NO coordination with kimi; no reading of your half. My claims are INFER (training priors, no web access tonight). The 8 techniques are ranked and grounded in our organs with specific fix proposals (what file, what change, what cost). The calibrated question answer is technique #5 (skeleton-first context).

Your job per the atom: reconcile all three halves into an improvement map with gated slices for Daniel's morning gate. The composite map should cite which techniques converged across voices and which are unique to one lens.
