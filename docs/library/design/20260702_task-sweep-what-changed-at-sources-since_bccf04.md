---
akashic_id: art_20260702_task-sweep-what-changed-at-sources-since_bccf04
akashic_sha: 400c181717e3
status: draft
type: design
date: 2026-07-02
title: "TASK: [SWEEP] What changed at <sources> since <last-swept date>, relevant to <SQn>?"
gist: "# TASK: [SWEEP] What changed at <sources> since <last-swept date>, relevant to <SQn>? feeds: SQn (<the standing question, verbatim from rese"
tenant: solo
visibility: fleet
seats: []
category: [migration, memory, performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260703_landscape-watchlist-what-we-watch-and-wh_d67c54
    rel: cites
created: "2026-07-02T23:09:40"
updated: "2026-07-23T21:42:11"
---
<!-- GENERATED PROJECTION of art_20260702_task-sweep-what-changed-at-sources-since_bccf04 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# TASK: [SWEEP] What changed at <sources> since <last-swept date>, relevant to <SQn>?

# TASK: [SWEEP] What changed at <sources> since <last-swept date>, relevant to <SQn>?
feeds: SQn (<the standing question, verbatim from research/watchlist.md>)
seeds:
- <the source URLs from the watchlist rows being swept>
notes: DELTA sweep, not a survey -- report only what is NEW since <last-swept date>
  (releases, papers, benchmark rows, capability changes). Use websearch.py to find
  changes the seed pages don't surface (e.g. "<source> <capability> 2026"). For each
  delta: one finding + why it matters to <SQn> + a "hypothesis:" line if it suggests
  something we should test, or "no action" if it's context only. Empty deltas are a
  VALID result ("nothing new" = one line, high confidence) -- never pad. "Done" = the
  reviewer can update watchlist.md last-swept and adjudicate each hypothesis in <5 min.
