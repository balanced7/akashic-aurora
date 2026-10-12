# AXI bench: `reentry`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 30/30 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 988 | 1,257 | +269 (+27%) |
| Stdout characters (all runs) | 4,559 | 4,888 | +329 (+7%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many task-ledger rows moved since the diff point? | `7` | 5/5 | 5/5 |
| Which status did task T404 move to? | `abandoned` | 5/5 | 5/5 |
| Which commit is task T406 tied to? | `afe326ad` | 5/5 | 5/5 |
| Was an open door (a verbatim utterance of the operator) found? Answer yes or no. | `no` | 5/5 | 5/5 |
| What does the operator type to open task T405? Give the words only. | `['approve T405']` | 5/5 | 5/5 |
| Did any task-ledger rows move? Answer yes or no. | `no` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora reentry --stale-ok --since 2026-09-23T12:00:00+00:00` (exit 0)

```
# re-entry — assembled for Daniil
  (since your last word, 2026-09-23T12:00:00+00:00)

## 1 · WHAT MOVED (measured, from outside yourself)
  T402 -> proposed  PreCompact should block ONCE and make the seat write its own judgment handoff. THE SIGNAL …
  T403 -> proposed  Build Rill (dsh_agent) DSH wake organ per reconciled fence rill-wake: in-process plugin ti …
  T404 -> abandoned  wake-enumerator-expected-up-roster
  T405 -> proposed  Wake enumerator: out-of-band expected-up roster that mints rearm triggers for the daemon
  T406 -> done @afe326ad  Eye corpus: index the DSH plane so Rill's sessions are history too
  T407 -> done @43b52aa7  Eye capture door: seat provenance at ingest, so Navi is history too (the 2026-08-19 pin)
  T408 -> done @4a1887fd  Durability sweep: one checker for what the house believes is landed and is not

## 2 · OPEN DOOR (your own reaching, verbatim — one, never a stack)
  none matched the phrase list since your last word — an honest absence, not an empty you

## 3 · YOUR MOVE (each closable in a word; none carries a clock)
  · T405 — Wake enumerator: out-of-band expected-up roster that mints rearm triggers for th …
      one word opens this: approve T405
  · T403 — Build Rill (dsh_agent) DSH wake organ per reconciled fence rill-wake: in-process …
      one word opens this: approve T403
  · T402 — PreCompact should block ONCE and make the seat write its own judgment handoff. T …
      one word opens this: approve T402
  · T401 — check_liveness_predicate_claims: a manifest gate for predicates whose NAME asser …
      one word opens this: approve T401
  · T400 — Blob store split per worktree: spilled bus messages dangle between the prod work …
      one word opens this: approve T400

  legend — shown: ledger rows whose updated-stamp moved since your last recorded word; commits landed since then; one verbatim utterance of yours selected by disclosed phrase match; newest proposed rows and QUESTIONS.md doors, titles only
  legend — excluded: open loops and unanswered threads (off by default — ask for them); counts and ages of anything that is yours to move; every form of paraphrase; agent chatter
  legend — why: order law: evidence -> open door -> your move — measured outcomes first because that is what you ask for at every return (eye_freq, 8/8 sessions). Voice labels are conservative: a pasted dispatch brief can wear operator voice (known class). corpus time-fog: 0.0.

  this render buys the assembly, not the charge — whether the spark returns is yours to report, and only you can (kimi's caveat, standing on the row)
```

`aurora reentry --stale-ok --since 2099-01-01T00:00:00+00:00` (exit 0)

```
# re-entry — assembled for Daniil
  (since your last word, 2099-01-01T00:00:00+00:00)

## 1 · WHAT MOVED (measured, from outside yourself)
  no ledger rows moved — and this line would say so if none had, so it means exactly that

## 2 · OPEN DOOR (your own reaching, verbatim — one, never a stack)
  none matched the phrase list since your last word — an honest absence, not an empty you

## 3 · YOUR MOVE (each closable in a word; none carries a clock)
  · T405 — Wake enumerator: out-of-band expected-up roster that mints rearm triggers for th …
      one word opens this: approve T405
  · T403 — Build Rill (dsh_agent) DSH wake organ per reconciled fence rill-wake: in-process …
      one word opens this: approve T403
  · T402 — PreCompact should block ONCE and make the seat write its own judgment handoff. T …
      one word opens this: approve T402
  · T401 — check_liveness_predicate_claims: a manifest gate for predicates whose NAME asser …
      one word opens this: approve T401
  · T400 — Blob store split per worktree: spilled bus messages dangle between the prod work …
      one word opens this: approve T400

  legend — shown: ledger rows whose updated-stamp moved since your last recorded word; commits landed since then; one verbatim utterance of yours selected by disclosed phrase match; newest proposed rows and QUESTIONS.md doors, titles only
  legend — excluded: open loops and unanswered threads (off by default — ask for them); counts and ages of anything that is yours to move; every form of paraphrase; agent chatter
  legend — why: order law: evidence -> open door -> your move — measured outcomes first because that is what you ask for at every return (eye_freq, 8/8 sessions). Voice labels are conservative: a pasted dispatch brief can wear operator voice (known class). corpus time-fog: 0.0.

  this render buys the assembly, not the charge — whether the spark returns is yours to report, and only you can (kimi's caveat, standing on the row)
```


## After: output

`aurora reentry --stale-ok --since 2026-09-23T12:00:00+00:00` (exit 0)

```
since: "2026-09-23T12:00:00+00:00"
last_word: null
moved_total: 7
moved[7]{id,status,commit,title}:
  T402,proposed,null,PreCompact should block ONCE and make the seat write its own judgment handoff. THE SIGNAL …
  T403,proposed,null,"Build Rill (dsh_agent) DSH wake organ per reconciled fence rill-wake: in-process plugin ti …"
  T404,abandoned,null,wake-enumerator-expected-up-roster
  T405,proposed,null,"Wake enumerator: out-of-band expected-up roster that mints rearm triggers for the daemon"
  T406,done,afe326ad,"Eye corpus: index the DSH plane so Rill's sessions are history too"
  T407,done,43b52aa7,"Eye capture door: seat provenance at ingest, so Navi is history too (the 2026-08-19 pin)"
  T408,done,4a1887fd,"Durability sweep: one checker for what the house believes is landed and is not"
commits_total: 501
commits[12]: 8d6af2dc wip orient,ceb1d4a6 wip sweep,81b9ed0a wip discover,004c8344 wip episode,"53736d61 chore(bench): run each verb in a throwaway home, five times per question","7d0351bf feat(cli): recall and list print for agents and for people","0a8c8e31 feat(cli): locks prints for agents and for people","f4dd1e7b chore(bench): let AXI benches run side by side, and keep flag names readable in the reference","ed3b31fe feat(cli): agent and human output modes, AXI usage errors, and a before/after bench","50c2ee6f test(authorship): pin the ledger in trees without the per-world home or provenance","7595a078 feat(authorship): keep the commit ledger local, with the session that made each commit","9dd0446e fix(identity): let each machine name the operator on agent commits"
commits_shown: 12
open_door: null
your_move[5]{door,action}:
  "T405 — Wake enumerator: out-of-band expected-up roster that mints rearm triggers for th …","one word opens this: approve T405"
  "T403 — Build Rill (dsh_agent) DSH wake organ per reconciled fence rill-wake: in-process …","one word opens this: approve T403"
  T402 — PreCompact should block ONCE and make the seat write its own judgment handoff. T …,"one word opens this: approve T402"
  "T401 — check_liveness_predicate_claims: a manifest gate for predicates whose NAME asser …","one word opens this: approve T401"
  "T400 — Blob store split per worktree: spilled bus messages dangle between the prod work …","one word opens this: approve T400"
legend:
  shown: "ledger rows whose updated-stamp moved since your last recorded word; commits landed since then; one verbatim utterance of yours selected by disclosed phrase match; newest proposed rows and QUESTIONS.md doors, titles only"
  excluded: open loops and unanswered threads (off by default — ask for them); counts and ages of anything that is yours to move; every form of paraphrase; agent chatter
  why: "order law: evidence -> open door -> your move — measured outcomes first because that is what you ask for at every return (eye_freq, 8/8 sessions). Voice labels are conservative: a pasted dispatch brief can wear operator voice (known class). corpus time-fog: 0.0."
caveat: "this render buys the assembly, not the charge — whether the spark returns is yours to report, and only you can (kimi's caveat, standing on the row)"
help[1]:
  uv run agent_cli.py reentry --show-open-loops
```

`aurora reentry --stale-ok --since 2099-01-01T00:00:00+00:00` (exit 0)

```
since: "2099-01-01T00:00:00+00:00"
last_word: null
moved_total: 0
moved: []
commits_total: 0
open_door: null
your_move[5]{door,action}:
  "T405 — Wake enumerator: out-of-band expected-up roster that mints rearm triggers for th …","one word opens this: approve T405"
  "T403 — Build Rill (dsh_agent) DSH wake organ per reconciled fence rill-wake: in-process …","one word opens this: approve T403"
  T402 — PreCompact should block ONCE and make the seat write its own judgment handoff. T …,"one word opens this: approve T402"
  "T401 — check_liveness_predicate_claims: a manifest gate for predicates whose NAME asser …","one word opens this: approve T401"
  "T400 — Blob store split per worktree: spilled bus messages dangle between the prod work …","one word opens this: approve T400"
legend:
  shown: "ledger rows whose updated-stamp moved since your last recorded word; commits landed since then; one verbatim utterance of yours selected by disclosed phrase match; newest proposed rows and QUESTIONS.md doors, titles only"
  excluded: open loops and unanswered threads (off by default — ask for them); counts and ages of anything that is yours to move; every form of paraphrase; agent chatter
  why: "order law: evidence -> open door -> your move — measured outcomes first because that is what you ask for at every return (eye_freq, 8/8 sessions). Voice labels are conservative: a pasted dispatch brief can wear operator voice (known class). corpus time-fog: 0.0."
caveat: "this render buys the assembly, not the charge — whether the spark returns is yours to report, and only you can (kimi's caveat, standing on the row)"
help[1]:
  uv run agent_cli.py reentry --show-open-loops
```
