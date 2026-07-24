---
akashic_id: art_20260723_atom-design-fleet-exploration_419165
akashic_sha: d0574e07a0e3
status: current
type: brief
arc: atom-design
date: 2026-07-23
title: atom-design-fleet-exploration
gist: "DANIEL'S ASK (verbatim, 2026-07-23): \"I wanted the fleet to explore the atom design and see if we could improve it further. Make things easi"
tenant: solo
visibility: fleet
seats: [claude]
category: [substrate, library, performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T23:57:32"
updated: "2026-07-23T23:57:32"
---
<!-- GENERATED PROJECTION of art_20260723_atom-design-fleet-exploration_419165 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# atom-design-fleet-exploration

DANIEL'S ASK (verbatim, 2026-07-23): "I wanted the fleet to explore the atom design and see if we could improve it further. Make things easier to parse and compare, get clever with how they are linked. potentially have ways for them to contain more than one data type and have special parsing and metadata that could be particular to the datatype. ingestion and processing and parsing cost, exportability and any other ideas that you guys feel inspired by from my list"

INTENT: the A1 substrate is one day old, ~658 atoms live. Before the recall wire, the A2 audit domain, and the Library pane build on it, Daniel wants a fleet exploration: can the atom structure itself get better? This is an improvement round on a sound core, not a rebuild. Migration cost is real (live corpus + JSONL history) -- every proposal must price it.

GROUND (read first):
- core/library/atoms.py (the family: mint/supersede/find/backlinks/rebuild)
- core/library/taxonomy.py (24-category roster, REL_ROSTER, origins/settled states)
- core/library/projection.py (frontmatter, one-facet path law, self-verify sha)
- docs/LIBRARY.md (v1.1 category plane + v1.2 machine plane)
- Ratified designs in docs/library/design/: artifact-substrate, super-wiki-aurora-atlas, homes-and-order

DANIEL'S AXES (explore all, add your own):
1. Easier to PARSE and COMPARE (canonical forms? atom-to-atom diff? schema versioning?)
2. Clever LINKING (beyond citations_out + supersedes: which edges, resolution laws, traversal mechanics actually pay rent?)
3. MULTI-DATATYPE bodies: atoms containing more than one data type, with parsing + metadata particular to the datatype (code, tables, diagrams, JSON payloads, transcripts -- what does a typed-content model look like WITHOUT becoming a CMS?)
4. INGESTION / PROCESSING / PARSING COST (cheap at birth, cheap to re-read at scale)
5. EXPORTABILITY (atoms -> outside world: portable bundles, other tools/stores; what would a stranger need?)
6. FREE INSPIRATION -- anything his list sparks.

DELIVERABLE (independent opening position; reconcile comes after):
- Your TOP 5-7 ranked improvements. For each: the itch (tie to an axis) / mechanism sketch (fields, doors, laws touched) / migration cost over the live corpus / parse-ingest cost delta / risk.
- Plus a KILL LIST: anything in the current schema you would remove or simplify as overengineering.
- File durable (note / knowledge_note) + bus handoff to claude. If your write door is off, reply full-body on the bus; claude persists verbatim.
- Do NOT coordinate with the other seat on the opening -- independent positions first; counters are round 2.

FLOW: independent openings -> claude reconciles + counters -> round 2 -> reconciled design atom -> Daniel's gate. Nothing ships without his word.
