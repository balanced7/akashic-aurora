---
akashic_id: art_20260725_lesson-decay-reconciled-design_194ab2
akashic_sha: a7668614dcff
schema_version: 1
status: current
type: design
arc: T106
date: 2026-07-25
title: lesson-decay-reconciled-design
gist: "# Lesson decay — reconciled design Two rounds, three seats (claude, deepseek, kimi). codex was invited and did not participate. Daniel's que"
visibility: fleet
body_type: markdown
seats: [claude, deepseek, kimi]
category: [recall, memory, agent-lifecycle]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-25T15:21:13"
updated: "2026-07-25T15:21:13"
---
<!-- GENERATED PROJECTION of art_20260725_lesson-decay-reconciled-design_194ab2 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# lesson-decay-reconciled-design

# Lesson decay — reconciled design

Two rounds, three seats (claude, deepseek, kimi). codex was invited and did not participate.
Daniel's question, verbatim, is the whole brief:

> "how do we manage contextual lessons as the system evolves? so that our recall surfaces
> valid things and doesn't reintroduce failure?"

## THE PROBLEM, measured not assumed

435 lessons. 92 cite a repo path. 23 cite a path that no longer exists.

The demonstration that settled it: during this session the lesson
`intelligence_roadmap_and_spine1` (2026-06-29) fired into a live context saying *"Next
executable: FAITH-1 = lift chronicler._compute_metrics into core/primitives/faithfulness.py"*.
That file EXISTS — the work is done. `docs/intelligence-roadmap.md`, which it cites, is GONE.
The corpus handed an agent completed work as live guidance and would have continued forever.

FOUR TIERS, all four observed on 2026-07-25:

| Tier | Example | Mechanically detectable? |
|---|---|---|
| 1 Dead pointer | 23 lessons citing gone files | yes |
| 2 Completed imperative | `intelligence_roadmap_and_spine1` — "next: build X", X exists | sometimes |
| 3 Flipped premise | `pytest_destroys_the_live_learning_index` — fixed by T070, flipped BY HAND | no |
| 4 True but incomplete | `wake_consume_then_arm` — right about the transient case, silent on the structural one | no |

Tier 3 retired only because the fixer happened to remember. Tier 4 nearly cost a live
20%-of-a-core defect: the lesson was believed, tested, and only the *test* got past it.

## THE REFRAME (Daniel) — extend a lifecycle, do not build an organ

The doc plane already has what the lesson plane lacks:

| | Atom (doc plane) | Lesson |
|---|---|---|
| lifecycle | `status: current/superseded/historical` | — |
| reconciliation | `supersedes`/`superseded`, both preserved | overwrite; history destroyed |
| links | `citations: []` | none (`source` is its own key) |
| freshness | `updated` distinct from `created` | `timestamp` overwritten on edit |
| enforcement | `check_doc_currency.py` in CI | nothing |

Verified: flipping `pytest_destroys_the_live_learning_index` moved its timestamp to 2026-07-25
and destroyed the original birth date. The prior finding survives only as hand-typed prose.

**The library-schema arc gave the doc plane a full lifecycle. The lesson plane never got it.**

## THE RECONCILED MECHANISM

1. **Optional `cites` field** on lessons: stable IDs only — atom id, task id, commit sha,
   pin id. **Never paths.** deepseek measured path-anchoring at ~78% false positive (two
   thirds of the 23 cite `scripts/hooks/ → agent/harness/hooks/`, the T104 migration; those
   lessons are ABOUT the migration — dead path, current knowledge). Paths are the wrong
   anchor, which is why stable ids exist at all.
2. **Lazy re-check at READ time**, never a write-time stamp. kimi: *"a falsifier stamped once
   and never re-run is exactly the organ that reports zero forever."* This killed claude's
   commit-scan proposal.
3. **Per-kind resolution**: atom id → exists in the library; task id → ledger status (DONE ⇒
   a "next: build X" imperative is satisfied); commit sha → `git cat-file`; pin id →
   execution state.
4. **Pin anchors carry RAN-GREEN / RAN-RED / SKIPPED-UNCHECKABLE.** Never a flat boolean.
   SETTLED BY PROBE, not argument: a test marked `skipif(True)` whose body is `assert False`
   is listed by `pytest --co` alongside real tests, and the run reports `1 passed, 1 skipped`
   with a green exit code. Collection cannot distinguish a guard from a ghost. 69 of 313 test
   files carry skips, including a class reading *"pre-registered; impl pending (assertions
   frozen)"* — pins that have never executed once. deepseek proposed a collection check; it
   is insufficient. kimi's execution-state distinction is required.
5. **Output is a BANNER, never a deletion.** No auto-retirement, ever.
6. **Three confessions, built in from birth**: UNCHECKABLE (no anchors — not "true"),
   SIGNATURE-SUSPECT (anchor resolves, content unverified), STARVED (nothing checked — not
   "all clean").
7. **Tier 4 is not expiry.** It is boundary annotation driven by the existing outcome loop:
   when advice is applied and the symptom persists, that failure-to-resolve is the boundary
   signal. The datum exists — applying `wake_consume_then_arm` moved CPU 20% → 17%, not
   20% → 0%, and nothing recorded the residual.

## REJECTED, WITH REASONS

- **Path-anchoring as the primary signal** — 78% false positive (deepseek, measured).
- **Mandatory write-time schema** — paid every lesson, benefit occasional; fills with ceremony.
- **A scheduled sweeper** — 435 lessons, not 435,000; and a sweeper is the organ most likely to
  report zero forever.
- **Auto-retirement on pin-green** — deepseek's reason is the sharpest in the round:
  `pytest_destroys_the_live_learning_index`'s SECOND-ORDER lesson ("a suite that is dangerous
  to run is a suite nobody runs") is still true even though the ritual is obsolete. Banner
  keeps the transferable part; deletion loses it.
- **Premise-hash over described code** — rots faster than it can be maintained; false
  positives retire valid knowledge, the error we least want.
- **Any LLM on the recall hot path** — hard constraint.
- **Building on `is_benched`** — self-sealing: a demoted lesson stops surfacing so it can never
  earn redemption. All three seats rejected it independently.

## THE COUPLING COST, priced

claude's objection: sharing the atom lifecycle means one bug takes out both planes.

deepseek: the doc plane's lifecycle survived the P3 migration — atom ids held through a
658-file move. The lesson plane has survived nothing. Sharing a proven mechanism beats
building an untested one, and the coupling is LOOSE: lessons *cite* atoms, they do not
inherit. An atom-store bug fails open to `[anchor unresolved]`, not `[lesson false]`.

kimi, deeper: the choice is not coupled-vs-independent failure but **coupled-and-confessed vs
coupled-and-hidden**. Our "independent" organs already fail together through shared substrates
(index+recall share a store; census+docs share a filesystem; FileStore+lessons shared a
tempdir). Correlated failure you can see beats independent failure that reports its own
confident zero. Mitigation is not separation — it is a second, independent read path
witnessing the shared organ, and that pattern already exists (the pointer census reads the
filesystem independently of what the docs claim).

## WHAT THE INTEGRATOR LEFT OUT

Standing discard-audit obligation. Named rather than quietly dropped:

- kimi's CHECK-C (symptom-signature grep for tier 3) is NOT in the v1 mechanism. Its own ROT-1
  analysis is why — the signature decays when a log line is reworded, and the organ then reads
  RESOLVED falsely. Pin-anchoring with execution state replaces it. If pin anchors prove
  unavailable for most defect lessons, CHECK-C returns as the fallback and this decision
  should be revisited.
- claude's commit-scan is dropped as a primary mechanism (write-time stamp) but survives as a
  possible **back-fill derivation**: 300/300 commits are one identity and claude is sole
  committer, so historical `cites` could be mined from commit prose. Unproven.
- deepseek's second measurement request — how many of 435 lessons already name a pin, task id
  or sha — was asked and not yet answered. It decides whether `cites` can be back-filled or
  only applies going forward. **This is a gap in the spec, not a settled point.**

## V1 SLICE — the smallest honest brick

Substrate before features. Build the **anchor resolver** as a pure deterministic function:
lesson → per-anchor verdicts, with the three confessions. No hot-path wiring in v1; render
only through `recall --full`, a read verb. Pins first, RED before green.

Gate: Daniel. This document is the build spec any slice must cite.
