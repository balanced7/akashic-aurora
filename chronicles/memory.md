# Project memory (auto-generated from notes — do not hand-edit)

_Distilled from 14 active note(s) · regenerate via `py agent_cli.py note` / `notes --project`_

Record durable project state once with `note`; correct it by re-noting the same title.

- where-we-are: T1 SHIPPED (implicit FAIL->SUCCESS credit real + proven live, first helped credit in system history) AND presentation pass SHIPPED (2026-07-01): tracked...  (source: mem:decision:ADR_0701225643_5172)
- next-focus: NEXT per docs/leapfrog-plan.md triage (loop fires -> corpus grows -> numbers exist): T2 = write-side friction fixes (JIT learn-it? prompt at the...  (source: mem:decision:ADR_0701223907_7327)
- open-question: implicit-useful payload: RESOLVED 2026-07-01 (T1 shipped, gated green). Live capture proved the old assumption unfixable rather than mistuned: Claude Code...  (source: mem:decision:ADR_0701223906_5443)
- leapfrog-plan: Full plan = docs/leapfrog-plan.md (2026-07-01, max-effort synthesis of repo audit + docs read + competitive survey + DS4/antirez case study). THESIS...  (source: mem:decision:ADR_0701221002_3682)
- competitive-landscape-2026-07: Web survey 2026-07-01 (full sources in session transcript). FIELD STATE: memory is now native in every harness -- Claude Code auto-memory...  (source: mem:decision:ADR_0701215407_2479)
- adversarial-critic-partner-idea: User idea (2026-07-01): design an adversarial partner/critic for Claude that TRAINS INDEPENDENTLY (not just prompted-in-context) and...  (source: mem:decision:ADR_0701010114_6136)
- retrieval-critic-design: Design research for an automatic retrieval critic = docs/retrieval-critic-design.md (2026-06-30, user idea: ground context retrieval so it is...  (source: mem:decision:ADR_0630093036_6716)
- directive-friction-audit: Friction audit of the agent directives = docs/directive-friction-audit.md (written 2026-06-30, in response to user principle: make the right...  (source: mem:decision:ADR_0630092509_1059)
- epistemic-risk-register: EPISTEMIC-RISK REGISTER (manual deep pass; grounded in real code + literature; skeptic-checked). Loop under study: usefulness -> rank -> surface...  (source: mem:decision:ADR_0630091418_4717)
- session-digest 2026-06-29: Shipped:
  - ship + wrap: one-command gated ship + ambient session capture  (git:28c3afd)
  - Write-once memory: a 'note' verb (record once ->...  (source: mem:decision:ADR_0629230032_9951)
- cursor-status: Cursor's gemini-web slice was taken over + committed by claude (gemini_web.py, bifrost_runner --provider web, ai_setup_mcp _run_gemini_web...  (source: mem:decision:ADR_0629214304_3549)
- open-docket: Explored-not-built: mutual agent invocation (claude -p / cursor-agent headless + generalized bifrost_runner + optional ask_agent RPC; blocked on CLIs not...  (source: mem:decision:ADR_0629214303_8701)
- remaining-review-items: From the 2026-06-28 architecture review: RC-02 route contended writes through Store.update_atomic (CAS has no domain callers); store-hardening...  (source: mem:decision:ADR_0629214302_4317)
- where-we-are 2026-06-29: Akashic Aurora status: recall-at-action COMPLETE end-to-end (engine, CLI recall-at, PreToolUse hook additionalContext, bootstrap contract...  (source: mem:decision:ADR_0629214301_5916)
