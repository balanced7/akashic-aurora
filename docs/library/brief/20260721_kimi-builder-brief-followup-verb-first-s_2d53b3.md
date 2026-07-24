---
akashic_id: art_20260721_kimi-builder-brief-followup-verb-first-s_2d53b3
akashic_sha: 5f8618f3c9ac
status: current
type: brief
date: 2026-07-21
title: "Kimi builder brief — followup verb (first self-serve build round, 2026-07-21)"
gist: "Class: brief (launcher extracts the blockquote body; run via launch_kimi_builder.ps1) > FIRST BUILDER ROUND — Daniel's morning ruling (verba"
tenant: solo
visibility: fleet
seats: []
category: [identity, security, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260721_tools-hunt-tonight-s-edition-kimi-2026-0_974493
    rel: cites
created: "2026-07-21T09:01:07"
updated: "2026-07-23T21:42:08"
---
<!-- GENERATED PROJECTION of art_20260721_kimi-builder-brief-followup-verb-first-s_2d53b3 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Kimi builder brief — followup verb (first self-serve build round, 2026-07-21)

Class: brief (launcher extracts the blockquote body; run via launch_kimi_builder.ps1)

> FIRST BUILDER ROUND — Daniel's morning ruling (verbatim, in security/acl.json under your
> record's _tool_author_activation): "I want us to fix permissions so that deepseek and kimi
> can actually add tools and verbs for the roster without having to ask you to do it for
> them." Your allowlist now covers the tool/verb surfaces end-to-end: core/toolbelt/**,
> tests/**, data/play/kimi/**, data/toolbelt/**, docs/WISHLIST.md, research/**, scratch/**,
> plus pytest and the mirror door. You build, you pin, you flip, you COMMIT. No claude hands.
>
> THE BUILD: your own W46 — the `followup` verb (you designed it in last night's tools hunt,
> research/reviewed/kimi-tools-hunt-tonight-2026-07-21.md #2). Scope as you filed it:
> `followup <me> --on <verdict-file> --ask "..."` appends a q-id'd question to the file's
> `## Open Questions` block AND files a defer-queue item naming the responsible seat
> (core/coord/defer_queue.py is live; `defer <seat> --list` shows the shape; your
> receipt-on-done amendment is in it). The discharge receipt points at the answered block.
>
> METHOD (the house contract, docs/method-baseline-2026-07.md):
> 1. Ground: py agent_cli.py boot kimi --task "builder round: followup verb" then
>    note kimi --get where-we-are. Read core/coord/defer_queue.py + how cmd_defer/cmd_toast
>    wire into agent_cli (build_parser + the T099 door neighborhood) BEFORE designing.
> 2. Pins RED-FIRST: tests/test_w46_followup_kimi.py (note the _kimi suffix -- per-lane
>    test namespacing, C2-1). Pin at least: question lands in the verdict file's Open
>    Questions block with a q-id; the defer item carries the pointer; a missing verdict
>    file refuses loudly; the block is created if absent.
> 3. Build minimal: a helper module (core/toolbelt/followup.py or core/coord/ -- your
>    altitude call, justify in the docstring) + the agent_cli verb + parser entry.
>    CAUTION: agent_cli.py is shared and >120KB -- make your edits SURGICAL (one cmd
>    function + one parser block next to the defer verb); if your read-tool clips the
>    file, use Grep for the anchor lines, never guess offsets.
> 4. GREEN: py -m pytest tests/test_w46_followup_kimi.py -q, then the neighbors:
>    tests/test_w33_defer_queue.py tests/test_t099_doors_wireup.py.
> 5. Flip W46 in docs/WISHLIST.md ([x] FOLDED, your receipts inline -- the door is open
>    to you now).
> 6. COMMIT through the audited mirror family with EXPLICIT paths:
>    py scripts/mirror.py "W46 followup: charter question-back channel (kimi's first
>    self-serve build)" core/toolbelt/followup.py agent_cli.py
>    tests/test_w46_followup_kimi.py docs/WISHLIST.md
>    (never a sweep; never security/ or .claude/; the B5 partition line teaches the law.)
> 7. Handoff to claude: kind=handoff, the receipts + anything you want fence-checked.
>    Post-hoc fence is claude's job (T049 lite) -- your commit does NOT wait for it.
>
> HONESTY: label anything you could not run. If a step refuses (allowlist gap, door
> refusal), file it as a wish (the wish verb WORKS from this launcher -- W49's gap is
> closed for you) and hand off what you have. Budget ~60 turns.
