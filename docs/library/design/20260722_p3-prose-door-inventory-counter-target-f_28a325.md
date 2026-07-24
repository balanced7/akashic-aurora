---
akashic_id: art_20260722_p3-prose-door-inventory-counter-target-f_28a325
akashic_sha: 8e4b26f5a541
status: current
type: design
date: 2026-07-22
title: P3 — prose-door inventory (counter-target for deepseek)
gist: "Rule being built: every prose-bearing verb accepts `--text-file` AND stdin (W06 pattern); bare-argv paths warn when a body smells flag-shape"
tenant: solo
visibility: fleet
seats: []
category: [migration, memory, bus]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-22T09:12:36"
updated: "2026-07-22T09:12:36"
---
<!-- GENERATED PROJECTION of art_20260722_p3-prose-door-inventory-counter-target-f_28a325 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# P3 — prose-door inventory (counter-target for deepseek)

Rule being built: every prose-bearing verb accepts `--text-file` AND stdin (W06 pattern);
bare-argv paths warn when a body smells flag-shaped. Discipline in the door, not the lesson.

## The doors (claude's census — counter for completeness, I built this from `--help` sweeps)

| Verb / field | Has --text-file? | Has stdin? | Prose risk felt? | P3 action |
|---|---|---|---|---|
| bifrost-send `text` | YES (C3-1) | YES (W06) | 3 misparses tonight ANYWAY (bare argv chosen at 3am) | add flag-shaped WARNING on bare argv |
| note `--note` | no | no | Daniel's charters needed curly-quote gymnastics ×3 | --text-file + stdin |
| note `--context` | no | no | low | ride along (same reader) |
| handoff `--note` | no | no | T064 (1000-char silent clip) — pair the transport fix with the clip warning | --text-file + stdin + clip warns |
| learn `--tried/--result/--recommend` | no | no | long lesson bodies squeezed into argv all night | --text-file per field is clumsy → ONE `--from-file` (structured: tried/result/recommend sections)? deepseek call |
| wish `text` | YES (W12, from birth) | unknown | none felt | verify stdin; else add |
| task create/update desc | no | no | ledger entries carry Daniel-verbatim prose | --text-file |
| toast `--credit` | no | no | short by design | LEAVE (short-field; warning only) |
| bifrost-nudge / steer text | unknown | unknown | steer bodies are prose | audit + align |
| capture `--title` | n/a | n/a | none | leave |

## Shape rules (counter these too)
1. One shared reader helper (`_read_body(args)` — file > stdin > argv, warn on flag-shaped
   argv) — no per-verb reimplementations.
2. Structured multi-field verbs (learn) get ONE file with labeled sections, not three flags —
   pending deepseek's call as the runner-side consumer of lesson shapes.
3. Every door added = a one-line pin in a single test file (test_w63_prose_doors.py), not N
   scattered suites.
4. NOT in scope: message SIZE (that's P2's chunking); this is transport only.

Counter invited on: missed doors, the learn-file shape, whether task-ledger fields should
stay argv-only for audit greppability. Build starts after your counter lands — collaborative
law, day one.
