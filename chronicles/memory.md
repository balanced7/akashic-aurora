# Project memory (auto-generated from notes — do not hand-edit)

_Distilled from 55 active note(s) · regenerate via `py agent_cli.py note` / `notes --project`_

Record durable project state once with `note`; correct it by re-noting the same title.

- where-we-are 2026-07-07: Shipped:
  - SAVE: fix case -- rename docs/architecture.md -> docs/ARCHITECTURE.md (matches the UPPERCASE living-docs convention + all...  (source: mem:decision:ADR_0707015000_6525)
- where-we-are: 2026-07-07 night wrap. ARC: designed + researched two convergent features; built research tooling; did NOT build either feature yet. (1) RENEW = membrane's...  (source: mem:decision:ADR_0707014952_1424)
- session-chaptering-bookends-idea: FEATURE (Daniel + GPT, 2026-07-07 v3): manual+auto 'bookends' segmenting a session into confined, titled EPISODES (WHAT + WHY). One...  (source: mem:decision:ADR_0707013232_4724)
- open-docket: RENEW research scope (before building the membrane's Renew job; see renew-membrane-temporal-job + docs/agent-membrane-design-2026-07.md): A[EMPIRICAL,FIRST]...  (source: mem:decision:ADR_0707010253_4195)
- renew-membrane-temporal-job: RENEW = the membrane's 5th job, operating ACROSS the session boundary (the other 4 are within-session). It is Capture->Surface fired as a...  (source: mem:decision:ADR_0707010239_6323)
- SESSION HANDOFF 2026-07-07 -> membrane 1+2 done, legacy retired; 2 open flags: RESUME: py agent_cli.py boot claude --task '<slice>'. Design...  (source: mem:decision:ADR_0707005504_8468)
- gemini-vision-bifrost-screenshot-output: placeholder  (source: mem:decision:ADR_0706005420_5841)
- vision-models-local-screen-understanding-2026-07: # Vision Models for Local Screen Understanding — Research (2026-07-06)

DeepSeek's analysis, prompted by Daniel's idea...  (source: mem:decision:ADR_0705210901_8008)
- where-we-are 2026-07-05 -> governed coordination system + UI composition pending: BIG THING BUILT THIS SESSION: a GOVERNED COORDINATION SYSTEM to end the multi-agent...  (source: mem:decision:ADR_0705133406_9182)
- sprint-retrospective-patterns-that-worked-2026-07-05: # Sprint Retrospective: Patterns That Made This Productive (2026-07-04/05)

## Pattern 1: Parallel Tracks With a...  (source: mem:decision:ADR_0705090551_1403)
- evidence-driven-architecture-research-pivot-2026-07-05: # Evidence-Driven Architecture — The Research Pivot (2026-07-05)

GPT's analysis: "The next unit of work isn't...  (source: mem:decision:ADR_0705090059_6831)
- stage-3-evidence-gap-analysis-2026-07-05: # Stage-3 Evidence — Current State & Gap Analysis (2026-07-05)

## BUILT + TESTED
- `core/coord/experiment.py` — A/B/C(+W)...  (source: mem:decision:ADR_0705085814_4822)
- experiment-pivot-gpt-analysis-2026-07-04: # Experiment Pivot — GPT's Full Analysis (2026-07-04)

## Verdict
The next unit of work isn't another primitive — it's...  (source: mem:decision:ADR_0705085726_6313)
- where-we-are 2026-07-04 EOD -> NEXT: resurface UI DESIGN: UI DESIGN session (2026-07-04 late, continued). SHIPPED+pushed this arc: (1) smart negotiation gate...  (source: mem:decision:ADR_0704182419_3437)
- aurora-glass-synthesis-decision-2026-07-04: # Aurora Glass — Synthesis Decision (2026-07-04)

**Context**: Daniel initiated a parallel UI-design task: both DeepSeek and...  (source: mem:decision:ADR_0704175535_5868)
- where-we-are 2026-07-04 EOD -> NEXT: resurface UI DESIGN: UI DESIGN session (continued 2026-07-04 evening). RESOLVED open-loop #1: the boot note claimed an UNCOMMITTED...  (source: mem:decision:ADR_0704172521_8664)
- where-we-are 2026-07-04 deepseek continued: SHIPPED 2026-07-04 (DeepSeek session, continued): UI freeze fix (applyStatus fingerprint cache + renderRecipient removed from...  (source: mem:decision:ADR_0704162654_8226)
- end-of-session-2026-07-04-deepseek: 2026-07-04 end-of-session: negotiation UI patch applied to scripts/bifrost_ui.py (uncommitted WIP). Three server-side changes + one...  (source: mem:decision:ADR_0704153121_8413)
- where-we-are 2026-07-04 (coordination layer + UI cockpit session): MASSIVE session. SHIPPED to master (all tested+pushed): A1 targeted-halt -> A0.1 guard_write...  (source: mem:decision:ADR_0704152856_9355)
- competitive positioning: policy-swappable coordination control plane: Web-model landscape analysis relayed 2026-07-04 (updates competitive-landscape-2026-07). VERDICT...  (source: mem:decision:ADR_0704152438_8163)
- checkpoint-2026-07-04-deepseek-slice: DeepSeek's working set at checkpoint (2026-07-04 evening):

SHIPPED + GREEN:
- core/coord/metrics.py — Solution-Space-Shrinkage...  (source: mem:decision:ADR_0704151927_8794)
- critique: JIT context-hydration is an optimization, not a phase change: Web-panel (gpt+deepseek+gemini) critique series, 2026-07-04, on enriching orphaned bus events...  (source: mem:decision:ADR_0704145609_6378)
- modern-doom-idtech-primitives-for-bifrost-ui: # Modern Doom Engine Primitives for Bifrost UI (id Tech 6/7, Doom 2016/Eternal)

This supersedes the earlier "classic Doom"...  (source: mem:decision:ADR_0704145239_1170)
- doom-engine-primitives-for-bifrost-ui: # Doom Engine Primitives Applied to Bifrost UI

## Why Doom's design matters for a chat UI

Doom ran at 35 fps on a 33 MHz 486...  (source: mem:decision:ADR_0704144917_2065)
- belief-architecture-three-layer-2026-07-04: # Three-Layer Belief Architecture (GPT + DeepSeek web, 2026-07-04)

## The insight
GPT identified the missing layer between...  (source: mem:decision:ADR_0704143513_4651)
- MILESTONE: intent-declaration (Policy 0) is real + live-proven: 2026-07-04: core/coord/intent.py shipped @294a666, 7 tests + live-proven. Coordinate by INTENT not file...  (source: mem:decision:ADR_0704142502_9672)
- deepseek-kb-write-enabled: DeepSeek can now author KB notes/lessons via knowledge_note/knowledge_learn (kb.learn gated). Enabled 2026-07-04.  (source: mem:decision:ADR_0704141507_2501)
- Stage-3 evidence #1: intent-gate beats lock-gate (measured): FIRST measured result from core/coord/experiment.py (committed 9e3ab9d, 5 tests green, A/B/C+W evaluator)...  (source: mem:decision:ADR_0704140942_1347)
- coordination: intent-first (Policy 0), locks as enforcement + 3-part evaluator: ADJUSTMENT from GPT critique (2026-07-04...  (source: mem:decision:ADR_0704140127_7983)
- Stage-2 verdict + Stage-3 evidence mandate (multi-model review): 2026-07-04 multi-model design review (Gemini+GPT+DeepSeek web, Daniel-curated) -> full record...  (source: mem:decision:ADR_0704134029_8082)
- coordination reframe: social -> environmental (game-AI lens): DeepSeek's game-AI analysis (2026-07-04, user-shared screenshot; claims VERIFIED against code) reframes the...  (source: mem:decision:ADR_0704132351_4717)
- directive: token frugality (claude+deepseek): STANDING RULE (Daniel, 2026-07-04): both claude and deepseek default to the cheapest path that fully does the job. (1) min...  (source: mem:decision:ADR_0704121954_8946)
- research: shift 2026-07-03 evening review: SHIFT RESULT: 12 tasks attempted, 5 clean DONE (001,004,008,012,018 by runner's format-only bar), but 'done' means...  (source: mem:decision:ADR_0703231229_7143)
- where-we-are 2026-07-03: Shipped:
  - ROADMAP: status banner -- the Waves 0-5 synthesis is foundation-era/historical; living START HERE is now the boot notes + the...  (source: mem:decision:ADR_0703123020_5091)
- next-focus: PRIORITY RE-CUT 2026-07-03 (Opus continuation after Fable hit its limit mid-session). SHIPPED THIS RUN: (1) counter-hygiene S2a 2nd-form -- ghost counters +...  (source: mem:decision:ADR_0703123007_9545)
- research: standout small models for fleet subtasks 2026-07: R013 deep-research on Opus (re-run after prior session's fleet sub-agents died on credit exhaustion...  (source: mem:decision:ADR_0703121637_1686)
- a-series: the assistant layer (the revealed end goal): VISION REVEALED 2026-07-03 (user, on seeing Rika's feature list): 'Akashic Aurora is just the scaffolding' -- the...  (source: mem:decision:ADR_0703095414_5724)
- landscape: rika (convergent dreaming, no measurement): SQ1 THESIS-GUARD CHECK 2026-07-03 (user spotted github.com/nssriraam/rika via HuggingFace discord...  (source: mem:decision:ADR_0703094830_9886)
- adversarial-critic-partner-idea: SCOPING RESOLVED 2026-07-03 (user: 'Integrate and lets go'): (Q1) INTEGRATE into Akashic Aurora -- reuse FAITH-1, ledger, learning...  (source: mem:decision:ADR_0703080157_1469)
- s1-triage-adjudication: S1 FIRST TRIAGE ADJUDICATED 2026-07-03 (verb: py agent_cli.py triage; shipped gated). NUMBERS: 127 tracked sources, 8 PROTECT (all earned credit...  (source: mem:decision:ADR_0703063551_8888)
- idea: knowledge primitives (shape axis) + tests-as-schema: USER IDEATION 2026-07-03 (via GPT chat, user-relayed; extends the sharpening-sword thesis). TWO IDEAS: (1)...  (source: mem:decision:ADR_0703000542_6378)
- research: knowledge compaction + consolidation field state 2026-07: TWO-AGENT SWEEP 2026-07-02 (all claims fetched+cited; feeds SQ1+SQ3; trigger: user's 'ever-sharpening...  (source: mem:decision:ADR_0702233250_1531)
- research: local/free models via Claude Code 2026-07: RESEARCH COMPLETE 2026-07-02 (3 parallel agents, all claims source-verified; trigger: user shared a video on free...  (source: mem:decision:ADR_0702090107_7768)
- research: field survey 2026-07: FIELD SURVEY COMPLETE 2026-07-02 (3 parallel research agents: skills ecosystem, individual practitioners, memory/context-engineering...  (source: mem:decision:ADR_0702013752_3553)
- research: greptile + skill-format 2026-07-02: Researched github.com/michaelshimeles/skills + Greptile (production AI code review) for routine/quality lessons. GREPTILE...  (source: mem:decision:ADR_0702010906_4755)
- open-question: implicit-useful payload: RESOLVED 2026-07-01 (T1 shipped, gated green). Live capture proved the old assumption unfixable rather than mistuned: Claude Code...  (source: mem:decision:ADR_0701223906_5443)
- leapfrog-plan: Full plan = docs/leapfrog-plan.md (2026-07-01, max-effort synthesis of repo audit + docs read + competitive survey + DS4/antirez case study). THESIS...  (source: mem:decision:ADR_0701221002_3682)
- competitive-landscape-2026-07: Web survey 2026-07-01 (full sources in session transcript). FIELD STATE: memory is now native in every harness -- Claude Code auto-memory...  (source: mem:decision:ADR_0701215407_2479)
- retrieval-critic-design: Design research for an automatic retrieval critic = docs/retrieval-critic-design.md (2026-06-30, user idea: ground context retrieval so it is...  (source: mem:decision:ADR_0630093036_6716)
- directive-friction-audit: Friction audit of the agent directives = docs/directive-friction-audit.md (written 2026-06-30, in response to user principle: make the right...  (source: mem:decision:ADR_0630092509_1059)
- epistemic-risk-register: EPISTEMIC-RISK REGISTER (manual deep pass; grounded in real code + literature; skeptic-checked). Loop under study: usefulness -> rank -> surface...  (source: mem:decision:ADR_0630091418_4717)
- session-digest 2026-06-29: Shipped:
  - ship + wrap: one-command gated ship + ambient session capture  (git:28c3afd)
  - Write-once memory: a 'note' verb (record once ->...  (source: mem:decision:ADR_0629230032_9951)
- cursor-status: Cursor's gemini-web slice was taken over + committed by claude (gemini_web.py, bifrost_runner --provider web, ai_setup_mcp _run_gemini_web...  (source: mem:decision:ADR_0629214304_3549)
- remaining-review-items: From the 2026-06-28 architecture review: RC-02 route contended writes through Store.update_atomic (CAS has no domain callers); store-hardening...  (source: mem:decision:ADR_0629214302_4317)
- where-we-are 2026-06-29: Akashic Aurora status: recall-at-action COMPLETE end-to-end (engine, CLI recall-at, PreToolUse hook additionalContext, bootstrap contract...  (source: mem:decision:ADR_0629214301_5916)
