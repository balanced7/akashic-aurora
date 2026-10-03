# The 133: sorting the suite into "red on purpose" and "someone should look"

2026-10-03, claude/Vandor. Turns a standing unknown into a number.

## Why this exists

The suite has been failing in bulk and nobody could say how much of that is intentional.
The recorded baseline (`suite-baseline --show`) is **24 days old** and its own banner says the
classification has rotted. So "is the house healthy" cost a full diagnosis every time it was
asked, and last night it cost two complete suite runs plus a false alarm that nearly reached
Daniel.

Re-recording the baseline would make the question go away without answering it — that is the
hygiene-over-a-live-wound anti-pattern (`env_self_splits_hygiene_vs_exposes`: it "converts a
real bug's loudest witness into a green test over a live wound"). So: sort, don't launder.

## The measurement

Two full runs, same command, same isolation:

| | failing nodes |
|---|---|
| 2026-10-01 23:58 (yesterday's HEAD, with current untracked files) | **213** |
| 2026-10-02 after 48 commits | **133** |

96 fixed during the day, 16 newly red, net 80 better. Three of the 16 were mine and are
fixed (`43509a77`, `48292a94`), leaving **130** for this triage.

A first attempt at the baseline reported **zero** failures. It had died at collection with
exit 2 and run no tests, because the worktree had no untracked files. "133 broken today"
would have been entirely false. The lesson is in the method below: a run that did not run is
not a green run.

## The discriminator, and why it is mechanical

M3 pre-registration says a RED pin is committed **alone**, before any implementation exists.
So a pin failing by design leaves a trace in git. Per test file:

- **A** — newest commit subject announces a pre-registration (`RED` / `pre-registered` / `prereg`)
- **B** — `_red` filename, this house's convention for pre-registered pin files
- **C** — **untracked**: not in git at all, so it is in-flight work and its failure says nothing
  about the committed tree
- **D** — docstring calls itself RED *(annotates only, never classifies)*

D never classifies alone on purpose. A false "by design" **hides a real break**, which is the
expensive direction.

## The answer

**130 failing nodes across 51 files.**

| class | nodes | files | |
|---|---|---|---|
| BY-DESIGN | 31 | 10 | committed pre-registered pins awaiting implementation |
| UNTRACKED | 39 | 7 | in-flight; 32 of these are also `_red` pins, so doubly intentional |
| **NEEDS-LOOK** | **60** | **34** | no pre-registration trace |

**63 of 130 (48%) are provably intentional.** Of the 60 that need a look, only **11 are new
since yesterday**; the other 49 predate this session entirely.

### Newly red and unexplained — the short list worth starting from

| file | nodes | last commit |
|---|---|---|
| `test_t169_budget_exhaustion_still_answers.py` | 4 new | *test(deepseek): bound forced-answer fixt…* |
| `test_t093_durable_job.py` | 1 of 4 new | *P3: THE SPRAWL DIES* |
| `test_runner_gemini_pins.py` | 1 of 3 new | *PRESERVATION COMMIT* |
| `test_alias_composition_is_honest.py` | 1 | *GREEN x2 of 3: the composition plane* |
| `test_report_kit.py` | 1 | *T275: `report`* |
| `test_t156_wire_verification.py` | 1 | *T157 GREEN: the wire journal* |

The deepseek budget-exhaustion four are the densest single new cluster and are not mine.

### The known-red that are correctly red

Heimdall's wire call-site seam (P2/P2b/P2c) classifies BY-DESIGN off its own commit —
*"pre-registered acceptance for the wire call-site seam, written by the reviewer"*. It is
working exactly as intended and should stay red until the seam lands.

## The failing set is not stable between runs — measured, after this was first written

A third full run of the same tree was used to check the number above, and it disagreed:
**131 nodes against the 130 predicted**, with five nodes churning in both directions.

| churned | direction |
|---|---|
| `test_t093_durable_job::test_atomic_receipt_never_tears_during_heartbeats` | was red, now green |
| `test_t156_wire_verification::test_a3_every_filesystem_function_completes_under_deadline` | was red, now green |
| `test_t093_durable_job::test_exit_zero_after_deadline_intent_remains_success` | was green, now red |
| `test_atoms_v11::test_lineage_resolve_current_and_lineage_backlinks` | was green, now red |
| `test_t114_running_code_version::test_p4_a_seat_at_head_is_not_accused` | was green, now red |

Three of the five name a **deadline**, a **heartbeat**, or **HEAD**. Those are wall-clock and
git-state dependent, and the tree was being committed to throughout — so at least some of this
churn is the measurement reacting to the measurer rather than to the code.

**So every count in this document carries about ±5 nodes of noise**, and FLAKY is a fourth
class this triage does not have. That matters more than the imprecision: a flaky node is
neither "red on purpose" nor "a real break", and sorting it into either is wrong. Any future
baseline must record a node's *stability across runs*, not just its last verdict — otherwise
the churn silently re-opens the same question this document was written to close.

The 48% intentional / 60 needs-look split survives the correction; the individual node counts
should be read as approximate.

## The honest limits of this triage

0. **The failing set churns by about five nodes per run** (measured above). Treat every count
   here as ±5, and treat the three deadline/heartbeat/HEAD names as flaky until pinned
   otherwise.
1. **Eleven NEEDS-LOOK files call themselves RED in their docstring but carry no commit
   trace.** They may be older pre-registrations whose history was squashed or renamed, or they
   may be genuine breaks. The classifier refuses to guess, by design. They are annotated in
   `triage.json` and are the cheapest next thing to resolve by hand.
2. **UNTRACKED is a finding, not just a category.** Seven files are doing real work in this
   tree while being invisible to anyone who clones the repo. That connects to a separate
   defect found the same night: `tests/test_codex_hook_contract.py` is *tracked* but imports
   three *untracked* `agent/harness/hooks/codex_*.py` modules, and pytest aborts the whole run
   on one collection error — so **a fresh clone of `balanced7/akashic-aurora` cannot run a
   single test**. Three named files, Asta's lane, awaiting Daniel's call.
3. This is a file-level classification. A file can hold both a deliberate RED pin and a real
   break; nothing here separates them within a file.
4. The baseline is still 24 days old and is **deliberately not re-recorded**. Re-recording it
   against 130 failures would convert every one of them into "known" with a single command.

## What would stop this recurring

The question "is the suite healthy" should not cost two full runs. The cheap fix is a baseline
that is re-recorded **only** when the failing set is explained — i.e. recording the
classification, not the count. That is a slice, not a note, and it is not started.
