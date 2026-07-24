# P7 lookback probe battery -- CLAUDE, PRE-REGISTERED (T027)

Committed BEFORE any lookback implementation exists (the F0 pre-registration fence; deepseek
registers its own battery in parallel, blind). Gate: for each question, the named expected
artifact appears in lookback's top-3 for its corpus layer. Six questions; corpus coverage:
docs x3, root contract x1, git history x1, promoted bus x1, with research/reviewed and
retired-notes as secondary expectations.

Q1. why is the bifrost bus ephemeral instead of durable
    EXPECT: docs/library/design/20260709_comms-messaging-pillar-dual-fenced-analy_051ff0.md  (accept: docs/library/design/20260710_multi-agent-coordination-layer-synthesis_283c99.md)

Q2. why is there no permanent per-agent file ownership
    EXPECT: AGENTS.md (the "no fixed split" contract section)
    (accept: docs/library/design/20260705_master-directive-list-akashic-aurora-202_964020.md as the historical record of the lane era)

Q3. why are project notes write-once and corrected by superseding instead of editing
    EXPECT: a git commit body -- T021 @d6153c2 (notes supersession)  (accept: chronicles/memory.md header)

Q4. why does the lesson forge gate edits behind a replay audit
    EXPECT: docs/library/design/20260701_lesson-forge-evidence-gated-content-opti_fd3204.md
    (accept: docs/library/report/20260709_forge-f0-data-sufficiency-audit-dual-pre_9749e0.md)

Q5. what happened to the GPT experiment-pivot analysis from early July
    EXPECT: a promoted handoff ref (deepseek-ui -> deepseek 2026-07-05, "SAVE THIS" chain)
    (accept: retired note "experiment-pivot-gpt-analysis-2026-07-04" via the --all archaeology path)

Q6. why does the wake listener detect messages without consuming them
    EXPECT: docs/library/design/20260709_p0-wake-listener-detect-don-t-consume-t0_864270.md
    (accept: docs/library/report/20260709_p0-wake-detect-design-deepseek-adversari_1faa7d.md; git T017 @d925d6b)
