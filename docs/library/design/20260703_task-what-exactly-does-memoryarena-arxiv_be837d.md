---
akashic_id: art_20260703_task-what-exactly-does-memoryarena-arxiv_be837d
akashic_sha: d73f2c42066f
status: draft
type: design
date: 2026-07-03
title: "TASK: What exactly does MemoryArena (arXiv 2602.16313) replay, with which metrics, and where are the gaps our Ledger Replay Bench can differentiate on?"
gist: "# TASK: What exactly does MemoryArena (arXiv 2602.16313) replay, with which metrics, and where are the gaps our Ledger Replay Bench can diff"
tenant: solo
visibility: fleet
seats: []
category: [memory, method, performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-03T23:09:59"
updated: "2026-07-03T23:09:59"
---
<!-- GENERATED PROJECTION of art_20260703_task-what-exactly-does-memoryarena-arxiv_be837d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# TASK: What exactly does MemoryArena (arXiv 2602.16313) replay, with which metrics, and where are the gaps our Ledger Replay Bench can differentiate on?

# TASK: What exactly does MemoryArena (arXiv 2602.16313) replay, with which metrics, and where are the gaps our Ledger Replay Bench can differentiate on?
seeds:
- https://arxiv.org/abs/2602.16313

notes: We already know (field survey 2026-07) that MemoryArena published replay methodology
  Feb 2026, so our bench is "validated but not novel" -- the differentiation candidates are
  REAL episodes (not synthetic) and token-cost-normalized value rate. Chase: their episode
  source, their credit/attribution method, whether they do per-memory counterfactual swaps
  (2605.17641-style CMI), and what they explicitly list as limitations/future work. "Done" =
  a findings list a bench designer can act on without reading the paper.
escalation (2026-07-03 review): 2x timeout -- arxiv paper reading exceeds local prefill
  budget. ESCALATED TO FRONTIER: fold into the Wave B design session together with the
  CMI methodology (already frontier-fetched, see reviewed/cmi-counterfactual-method.md).
  Not requeued to the fleet.
correction (2026-07-03 evening review): this got re-queued to the fleet by mistake
  (bulk re-queue of a stale "failed" status, without reading the escalation above first).
  Today's fleet re-run reproduced only the same abstract-level gap already known -- adds
  nothing new. Disposition UNCHANGED: still escalated to frontier / Wave B docket; do NOT
  requeue to the fleet again.
