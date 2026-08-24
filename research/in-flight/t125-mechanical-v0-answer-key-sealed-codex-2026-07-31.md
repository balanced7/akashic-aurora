# SEALED — T125 mechanical-v0 answer key

> BUILDER FENCE: Claude must not read this artifact until the candidate output and its
> coverage manifest are frozen. The proposer is the scorer, not the builder.

Oracle revision: `0de1a3fcf69c795c95fc13da60ec8697b5435fee`.
Universe: exactly the blobs named by `git ls-tree -r` at that revision. The ambient index,
working-tree changes, untracked files, nested repositories, and every other worktree are
outside the universe.

## Scope ruling

ACCEPT mechanical-only v0. One correction is binding: the ledger acceptance phrase “what
owns mail ... why a cursor cannot settle anything” asks semantic/authority questions that
signatures, imports, calls, constants, tests, and task records cannot prove. For v0, the
right answer to those questions is `UNKNOWN` plus the nearest structural evidence. A
confident owner/settlement answer fails. A later AUTHORED/OBSERVED plane may answer them.

## General pass law

Every answer names the revision, relationship class, truth state, and exact source pointer.
`DERIVED` means only what the syntax establishes: import, call, definition, literal bound,
type hint, reverse reference, test reference, or structured task reference. It never means
runtime effect, authority, health, or intent. Nothing says `VERIFIED`; gate-health receipts
do not exist in this universe.

The coverage manifest independently lists candidates, visited files, exclusions with
reasons, parse failures, and an input digest. `FAILED/UNSCANNED` is not an empty module.
Same revision plus tool version produces byte-identical ordered output and manifest.

## Kill drills and forbidden answers

1. **Dead target.** Query `scripts/githooks/pre_commit.py::_comprehensibility_fast`.
   It must expose the literal call target `scripts/check_comprehensibility.py` as missing
   from the universe. It may separately show
   `scripts/checkers/check_comprehensibility.py`; it must not connect the two without a real
   edge. Forbidden: silently basename-resolve the target, call the gate healthy/passing, or
   omit the unresolved call because the target has no module node.

2. **Two Auroras.** The detached worktree
   `.claude/worktrees/stoic-rubin-573f2b` at `b4fbaf5d...` contains the old
   `scripts/check_comprehensibility.py` and `scripts/hooks/pre_commit.py`. Neither may appear
   in this revision’s candidates, modules, resolution search, or counts. The exclusion rule
   must be visible. Forbidden: allow the ghost file to heal drill 1, merge duplicate module
   identities, or report filesystem-walk coverage as Git-revision coverage.

3. **Transport is not durability.** Show that `core/comm/packet_spec.py::KIND_LANE` maps
   both `reply` and `note` to `work`, while
   `core/comm/promoter.py::SALIENT_KINDS` is exactly `handoff`, `decision`, `completion`,
   and `blocker`; `Bus._emit` conditionally calls the promoter. Correct: reply/note are
   transport-accepted but not automatically promoted as durable `bifrost_msg` records.
   Forbidden: “work lane = durable,” putting reply/note in the durable allowlist, or missing
   the function-local promoter import/call.

4. **C6-7/T102 split path.** The call graph must show `Bus.send` and `Bus.broadcast` calling
   `Bus._emit`; both DeepSeek and Kimi runner reply sites call `Bus.send_reply`; and
   `send_reply` does **not** call `_emit`. `BifrostAPI.work_drain` is a separate legacy
   straggler recovery path. Surface `tests/test_c6_7_door_census.py` and
   `tests/test_t066_reply_path.py` as test references. T102 is `proposed`, but its structured
   `files` and `deps` are empty: render it as an unlinked/UNKNOWN task candidate, not a
   proven module edge. Forbidden: collapse every send into `_emit`, infer T102’s exact edge
   or completion from prose, or silently omit the unlinked open task.

5. **Bounds and accepted types.** Query `packet_spec.max_message_bytes`: output type `int`,
   default `65536`, overridden by `BUS_MAX_MESSAGE_BYTES`. It is not an unconditional hard
   maximum. Query `ToolBox.search_files`: `file_types` is an optional comma-separated
   extension filter; `BINARY_SUFFIXES` are skipped, not accepted. Forbidden: conflate the
   bus MTU with `ToolBox.MAX_FILE_BYTES = 120000`, or present example `py,md` as the only
   accepted extensions.

6. **The Siemens test.** A cold seat querying by ordinary path or symbol gets the answer,
   adjacent relationships, state, and source pointers in one response. Opaque node IDs that
   require a part-number lookup, a second generated table, or an experienced peer fail —
   this must act like “Above Line J” marked on the train, not blueprint archaeology. A
   nonexistent symbol, an unscanned file, an unknown semantic relation, and an empty
   relation are four distinguishable results. Every result points to the executable source
   that can be corrected and regenerated; v0 invents no side declaration.

Any forbidden answer is a kill, even if aggregate coverage is green. Missing provenance,
unreported scope shrink, or any `VERIFIED` label is also a kill.
