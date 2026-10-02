# Suite verb family — build spec (draft, pre-fence)

**Status:** DRAFT for triangulation (deepseek/Heimdall, 2026-10-01). Not fenced, not approved.
Awaiting Daniil + Simon sign-off before any implementation lands on the tree.
**Origin:** Simon's question — "how much of the manual labor for diffing test suites and
interacting with the test pipeline can be verbified in a way that doesn't introduce
failure modes?" — plus the standing friction that a suite run is a black box that only
speaks at exit.

## Thesis

The suite's *post-hoc analysis* is already well-built (`suite_baseline.py` delta/verdicts,
`ship_gate.py` ratchet). What's missing is **delivery-timing**: the run won't speak while it's
running, failures surface only at the end, and the diff/triage/rerun labor is hand-rolled every
time. This slice verbifies the **reads** — projections over records that already exist — and
deliberately leaves every **write** (recording a baseline, tightening the ratchet) behind its
existing explicit flag. Reads cannot introduce new failure modes; writes are where the traps are.

This is one projection of the same defect the 2026-10-01 recall-experience round diagnosed:
*knowledge exists, it just doesn't reach the moment of need.* The suite's silence and the
"best knowledge doesn't reach us" round are the same wound wearing two clothes.

## Lineage

1. **`core/coord/suite_baseline.py`** — `delta()`, `verdicts()`, `classify()`, `record()`,
   `render_boot_line()`. Already tested (`tests/test_w34_suite_baseline.py`). This is the
   compute; we add doors, not logic.
2. **`scripts/ship_gate.py`** — the ratchet. `main()` runs pytest blocking
   (`capture_output=True`) and holds every byte until exit. One of the two silence points.
3. **`agent_cli.py` `cmd_suite_baseline` (:6719)** — already has `--whose` (run + attribute)
   but blocking (`timeout=3600`), no tail, no rerun lever.
4. **Corpus lessons that already name the traps** (this slice is shaped so none of them fire):
   `never_verify_a_write_door_by_invoking_it` (record-by-default), `attribution_organ_swallows_stdout_confident_zero`
   (empty stdout = confident zero), `background_receipt_runs_capture_full_output_not_tail`
   (redirect full output to a file, tail the file), `timeout_py_launcher_orphans_python_exe`
   (don't hold the process; the file is the record), `deploy_kit_public` (`py` vs `python3` —
   OS-agnostic interpreter selection). The whole spec is "what if those five already fired."

## Census: what already exists (verified against source, not memory)

| Piece | Where | State |
|---|---|---|
| node-id delta (new/fixed/inherited) | `suite_baseline.delta()` | live, tested |
| per-node verdict (YOURS/INHERITED/UNKNOWN + staleness) | `suite_baseline.verdicts()` | live, tested |
| lane classification (node → owning task) | `suite_baseline.classify()` | live |
| ratchet (block new / retire fixed / expire stale) | `ship_gate.evaluate()` | live |
| run + attribute in one command | `cmd_suite_baseline --whose` | live but **blocking**, no tail |
| re-run the failing subset | pytest `.pytest_cache/lastfailed` | exists, **not surfaced** |
| live progress (N of M, failures-as-they-happen) | — | **MISSING** (items 4–5, deferred) |
| a `suite` read-door (diff/triage/rerun/tail) | — | **MISSING** (this slice) |

## The verb family (all READ-ONLY)

Four verbs, all projections over existing records, none writes shared state:

| Verb | Does | Reuses | New failure mode? |
|---|---|---|---|
| `suite diff` | render delta/verdicts of a run's `FAILED` list vs baseline | `delta()` + `verdicts()` | none — pure read |
| `suite triage` | attribute a failure set to lanes + ledger | `classify()` | none — pure read |
| `suite rerun-failing` | emit the exact failing-node selector | pytest `lastfailed` | low — one subprocess, no mutation |
| `suite tail` | poll the progress/log file, render "N of M, last fail at T" | the log file | low — pure file read |

**Deliberately deferred (write-path, needs Daniil's sign-off on each):** `suite --record`
(snapshot a baseline), `suite --tighten` (retire fixed failures). These are the failure-mode
carriers (`record-by-default`, `absence = pass eats known failures`) and do NOT ride this slice.

## The one rule that makes it safe

> **Verbify the reads; keep every write behind an explicit flag re-using existing compute.**

- A `suite` verb **defaults to render/read**, never to record. This is the
  `never_verify_a_write_door_by_invoking_it` guarantee made structural.
- `suite rerun-failing` never runs the *whole* suite implicitly; it prints the selector and
  (optionally, flagged `--run`) executes `sys.executable -m pytest <selector>`.
- `suite tail` reads a FILE, never a pipe it owns. The file is the record of record; the verb
  is never the only holder of the process output (`orphan` + `confident-zero` traps closed).

## OS-agnosticism (Ubuntu / Simon)

- All subprocess invocations use `sys.executable -m pytest`, never a hardcoded `py`.
  (`cmd_suite_baseline:6740` already does this — it's the template, not the exception.)
- The log file path is derived from a module constant under `state/`, not the OS tempdir-shape,
  so `suite tail` resolves identically on Linux and Windows.
- No `cp1252`, no console-window, no `py` launcher, no CRLF assumptions anywhere in the slice.

## Pre-registered acceptance (RED-first)

1. `suite diff` returns nonzero iff a `YOURS` verdict exists, and never for `UNKNOWN`
   (UNKNOWN is "I cannot tell", never an accusation — inherited from `cmd_suite_baseline`).
2. `suite diff` on a stale baseline prints `[STALE]` and does NOT claim `INHERITED` (it says
   `LIKELY_INHERITED`/`UNKNOWN`), matching `verdicts()`.
3. `suite triage` output is deterministic: same failure set → same lane map, every run.
4. `suite rerun-failing --run` leaves `.pytest_cache/lastfailed` alone (no mutation) and exits
   with pytest's own exit code — **the gate is the pytest exit, never the pipe** (the
   `pipe_swallowed_pytest_exit_gates_nothing` class, closed by construction).
5. `suite tail` on a nonexistent log returns a named, non-zero "no run in progress", never a
   confident zero (the empty-and-error-share-a-type rule).
6. `suite diff`/`triage`/`tail` never write to `state/coord/suite_baseline.json` — pinned by
   asserting the file's mtime/bytes are unchanged across a run.

## Open questions for Daniil

1. Do items 4–5 (structured progress marker + live verdict surfacing) ride in **this** slice or
   in the 2026-10-01 recall/choice-time primitive arc? They are the same "honest progress" join;
   building them once, in that arc, is cheaper than a suite-only organ.
2. `suite` as a *family* (subcommands) vs four flat verbs (`suite-diff`, `suite-triage`, …)?
   The house already has both shapes (`suite-baseline` is flat; `bifrost-*` is a prefix family).
   Leaning family (`suite diff`) for discoverability; flagging so the door-parity check agrees.

## Cost

~1 slice, all additive, no new stores, no new authority. Items 1–3 land together; items 4–5 are
a separate gated slice. Predicted payback (deepseek's estimate, medium confidence): ~2–4 h/month
saved-and-reallocated on suite-active months.
