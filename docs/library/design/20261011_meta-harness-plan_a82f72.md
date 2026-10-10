---
akashic_id: art_20261011_meta-harness-plan_a82f72
akashic_sha: 225d86f801ce
schema_version: 1
status: current
type: design
arc: meta-harness
date: 2026-10-11
title: meta-harness-plan
gist: "The meta-harness plan (tasks 01-11): what each built, where the code lives, the stacked PRs, and what still needs a person or a budget."
visibility: fleet
body_type: markdown
seats: [claude]
category: [testing, memory, performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-11T00:26:11"
updated: "2026-10-11T00:26:11"
---
<!-- GENERATED PROJECTION of art_20261011_meta-harness-plan_a82f72 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# meta-harness-plan

# The meta-harness: plan and build status

Written 2026-10-10 as a proposal; built 2026-10-10 and 2026-10-11 as tasks 01-11. This page is the
overview (plan file 00) brought up to date: what each task built, where the code lives, and what
still needs a person or a budget. The prior-art list (plan file 12) is its companion page,
`meta-harness-references`.

## The two questions that started it

**Does `learn` record the harness, model or thinking effort?** It did not. A lesson carried only
`agent_id`, and every Claude Code session shares `claude`. Task 01 fixed the record: each session
now has a durable provenance record, and lessons, flips, fails, repeats and session signals point
at it.

**Does recall at action fire only on failure?** No. When its hook is on, it fires before every
matching tool call, the first try included. The PostToolUse hook credits a flip (fail, then
success) to the lessons shown. In the aurora repo the PreToolUse recall hook is opt-in.

**Can lessons improve the harness before anything goes wrong?** That is the programme. Aurora was
interpretive: it retrieves lessons at the moment of action. The meta-harness adds a precompiled
path, a loop that proposes harness changes and replays our own tasks against them, and compression
that finds which pieces carry the weight.

## What was built

All code is in `core/metaharness/` plus small hooks into the learn, recall and boot paths. Every
piece has a CLI verb (CLI-only on the door-parity manifest). All state lives in gitignored
`<state>/metaharness/`.

| # | Task | Built | Verb | Upstream PR |
|---|---|---|---|---|
| 01 | Harness provenance | `core/fleet/provenance.py`; lessons, flips, fails, repeats and session signals carry `prov:session:<id>` | `provenance` | #77 |
| 02 | Lesson scope | `core/learning/scope.py`; recall-at and boot skip out-of-scope lessons; widening by evidence | `scope`, `learn --scope`, `recall --tree` | #78 |
| 03 | Task corpus | `transcripts.py` (redacted archive), `corpus.py` (miner, curation, validation, discrimination) | `corpus` | #79 |
| 04 | Replay runner | `replay.py`: sandbox clone with no remote, private state, closed proxy, headless Claude Code and Codex | `replay` | #80 |
| 05 | Graders and verdicts | `stats.py`, `graders.py`: code and model graders, two-order judge, calibration, paired verdicts | `grade` | #81 |
| 06 | Human review | `review.py`: queue, decisions as labels, accept-gated apply, exact rollback, provisional watch | `review` | #82 |
| 07 | Proposer loop | `archive.py`, `proposer.py`, `flags.py`, `loop.py`: contracts, bundle limit, GEPA parents, constrained BO, budget | `loop` | #83 |
| 08 | Memory replay | `memreplay.py`: snapshots, four arms, proven effect on the lesson and in the ranker | `memreplay` | #84 |
| 09 | Precompiler | `precompile.py`: routing, gates, emitters per harness, marked generated blocks, drift check | `precompile` | #86 |
| 10 | Execution modes | `modes.py`: `AKASHIC_MEMORY_MODE`, four-arm comparison, placement, staleness; docs page | `modes` | #87 |
| 11 | Compression | `compress.py`: piece registry, telemetry, Plackett-Burman with foldover, Lasso, noisy ddmin | `compress` | #89 |

The upstream PRs are stacked in that order, each on the one before, starting from #75.

## How it fits together

```text
real sessions --> provenance (01) --> scoped lessons (02)
      |                                     |
      +--> task corpus (03) --> replay runner (04) --> graders (05) --> human review (06)
                                     ^                      |
                 proposer loop (07) -+<---- traces, scores -+
                       |
          precompiler (09) --> harness candidates --> compression (11)
                       |
   memory replay (08) and modes (10) compare interpretive vs precompiled on the same corpus
```

## What still needs a person or a budget

The machinery is built and tested offline. These acceptance items cannot be met by code alone:

- **An accepted corpus.** `corpus mine` proposed 88 candidates on this repo, and 34 of the 41
  test-oracle ones validate. A person accepts scenarios (`corpus accept`); about 30 are needed.
- **Real loop runs.** `loop run`, `memreplay drain`, `modes compare` and `compress run` spend real
  money, so each requires an explicit budget or run cap. None has a default.
- **Sign-off.** Every harness change reaches the live config only through `review decide` and
  `review apply`, so the first accepted candidate is a person's call.
- **The SessionStart hook.** Provenance is written at session start once the hook is installed
  (`hooks install`); until then `learn` writes the record lazily.

## Principles that held throughout

- **Our tasks, not generic benchmarks.** The eval set grows from finished work on the task ledger.
- **Every diff is one point in a solution space.** The archive keeps every candidate with its
  scores, traces, contract and reviews.
- **Automatic first, human last.** Graders filter; a person accepts.
- **Graders out of reach.** The sandbox never holds the oracle; scenarios are sealed read-only
  before every run; grading happens on a copy.
- **Repo rules hold.** Tests and sandboxes use Redis db 15 or a private file store and their own
  `AI_SETUP`; a replay refuses db 0; only `uv` runs Python.
