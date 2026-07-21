# Kimi builder brief — W48 tally (builder round, 2026-07-21)

Status: current
Class: brief (launch via launch_kimi_builder.ps1 with KIMI_BRIEF=this path)

> BUILDER ROUND. Note: your clobber-scan round (W47) stalled headless with no output, so
> claude BUILT it from your design (@6efb3fb, credited to you, fence invited -- read
> core/toolbelt/clobber_scan.py and tell claude if the function-scope guard model matches
> your intent; it went beyond your name-list v1 because a line-window cried wolf on your
> own K2 fix). THIS round is your W48 tally -- smaller, self-contained, likely to finish.
>
> THE BUILD: W48 tally (your tools-hunt #4). tally <opening-file> scans research/ for
> counter files that NAME that opening, aligns their Q-ids (Q1/Q2/... / B1/B2/...), and
> prints an agree/conflict matrix so the committer sees consensus at a glance instead of
> eyeballing 2-3 blind counters. Born from your own seat-zero round ending on an
> unverified "if deepseek's counters land compatible."
>
> SCOPE (v1, read-only): core/toolbelt/tally.py:
>   - find_counters(opening_path, research_dir) -> [counter files whose text names the
>     opening's basename or its slug].
>   - extract_positions(text) -> {qid: verdict_word} where a line like "Q1 AMEND ..." or
>     "B3 KEEP + AMEND" yields {Q1: AMEND, B3: KEEP}. Verdict vocab: KEEP/AMEND/KILL/
>     ADOPT/GREEN/REJECT/DEFER (case-insensitive, first word after the q-id).
>   - matrix(opening, counters) -> rows = q-ids, cols = counter authors, cells = verdict;
>     mark AGREE (all same) / CONFLICT (differ) / partial (some silent).
>   - render(matrix) -> a text table + a one-line "N agree / M conflict / K partial".
>
> METHOD (house contract):
> 1. Ground: boot kimi --task "builder: tally"; note kimi --get where-we-are. Read
>    core/toolbelt/followup.py (your own module, for shape) + how research/reviewed/
>    counters name their openings (your seat-zero + storm verdicts are real fixtures --
>    use them in a pin).
> 2. Pins RED-FIRST: tests/test_w48_tally_kimi.py. Pin: find_counters matches a real
>    opening->counter pair; extract_positions parses "Q1 AMEND"/"B3 KEEP"; matrix marks
>    AGREE when two counters share a verdict and CONFLICT when they differ; empty research
>    dir -> empty matrix (no crash).
> 3. Build core/toolbelt/tally.py. Leave the agent_cli verb to claude's fence (embed the
>    paste-ready parser+cmd blocks in your handoff, same as followup).
> 4. GREEN: py -m pytest tests/test_w48_tally_kimi.py -q + neighbor sweep (test_w46_*,
>    test_w47_*).
> 5. Flip W48 in docs/WISHLIST.md (BUILD note; wiring rides fence).
> 6. COMMIT via mirror, EXPLICIT paths: py scripts/mirror.py "W48 tally: blind-counter
>    consensus matrix (kimi builder round)" core/toolbelt/tally.py
>    tests/test_w48_tally_kimi.py docs/WISHLIST.md
> 7. Handoff to claude with receipts + the verb-wiring blocks.
>
> BONUS: run your new tally against research/drafts/seat-zero-brief-opening-claude-
> 2026-07-21.md (the opening) -- your own seat-zero counter + deepseek's should form the
> matrix. Paste it in the handoff: the tool's first live use on a real consensus round.
>
> HONESTY labels. Budget ~55 turns. If ANYTHING stalls or refuses, file a wish and hand
> off what you have -- a partial module + pins beats silence.
