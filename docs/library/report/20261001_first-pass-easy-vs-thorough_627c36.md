---
akashic_id: art_20261001_first-pass-easy-vs-thorough_627c36
akashic_sha: d2b097a33930
schema_version: 1
status: current
type: report
date: 2026-10-01
title: first-pass-easy-vs-thorough
gist: "# First pass: easy search vs thorough census (Daniel's loop), 2026-10-01 Daniel, from work, verbatim: \"we could try using our easy tools for"
visibility: fleet
body_type: markdown
seats: []
category: [migration, agent-lifecycle, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-01T09:37:03"
updated: "2026-10-01T09:37:03"
---
<!-- GENERATED PROJECTION of art_20261001_first-pass-easy-vs-thorough_627c36 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# first-pass-easy-vs-thorough

# First pass: easy search vs thorough census (Daniel's loop), 2026-10-01

Daniel, from work, verbatim: "we could try using our easy tools for a concept or term and see what
surfaces, then we could run a thorough verification pass to see what percentage surfaced and what it
missed and why, implement fixes and improvements and then rerun until our easy search and what is
actually there match"

Run by Vandor (claude) the same morning, on the three concepts the seats had just reported as missed
in the recall-experience round (Heimdall, Sunshine, Navi).

## Method

Easy side, as a seat would type it: `py agent_cli.py recall "<concept>"`, `py agent_cli.py eye find
"<concept>"`, `py agent_cli.py knowledge-map "<concept>"`.

Thorough side (the oracle): a regex census over the full lesson dump (`list --json`, 1,529 records)
and every .md/.py/.json/.txt file under docs/library, docs (other), research, fences, core, scripts,
agent. Patterns:

- fence-slot overwrite: `write_slot|fence write ... overwrit|overwrit ... slot|slot ... overwrit`
- the captions verb: `\bcaptions\b`
- session_id forwarding: `session_id ... (forward|capture_event|never passed|0.0%)|capture_event ... session_id|session id (fill|forwarding)`

Relevance of the easy side's lesson hits was judged by name against the census set (a surfaced lesson
counts as relevant only if the census pattern matches it).

## Results

| concept | relevant lessons (census) | easy surfaced | relevant among surfaced | relevant missed | other-plane records | of those surfaced |
|---|---|---|---|---|---|---|
| fence-slot overwrite | 1 | 4 | 1 | 0 | 12 (3 atoms, 6 research, 1 fence, 1 code, 1 wishlist) | 0 |
| the captions verb | 9 | 6 | 6 | 3 | 43 (12 atoms, 24 research, 1 fence, 3 code, 3 docs) | 0 |
| session_id forwarding | 0 | 6 | 0 | 0 | 7 (fences: context-system, cross-plane-join) | 0 |

Totals: lesson-plane recall at census 7/10; precision 7/16; other-plane reach 0/62. `eye find` returned
0 hits on all three (the phrasings are not verbatim in any transcript).

Missed captions lessons: a_diff_based_sweep_cannot_see_untracked_load_bearing_files,
exact_name_before_latest_bus_inference, exceptions_that_prove_self_sealing_rules (the verb is mentioned
in passing inside another subject: the wording-gap class).

## What it means

1. The lesson plane is reachable and mostly right. Ranking work there is second-order.
2. The load-bearing fact of the context-system round (the hook holds session_id and forwards it
   nowhere; 0.0% fill) exists in no lesson. It lives only in sealed fences. The easy tools returned six
   unrelated lessons instead of an honest zero. This is the dark-plane barrier with a receipt.
3. The fix this pass points at: one retrieval engine over every plane (the manuals shelf's, extended
   to atoms, research, fences, notes), and a zero that names what was searched.

## Rerun

Same three patterns after each fix. The loop closes when the easy side and the census match. Add a
concept to this file each time a seat reports a miss; the set builds itself.
