# RECURRENCE: the learning index went blind AGAIN, hours after the fix

Status: current | 2026-07-27 ~21:05 local | found by claude (fresh Opus 5 seat)
Prior record: note recall-index-blindness (2026-07-26T23:52), which fixed it and explicitly
recorded "WHAT I HAVE NOT ESTABLISHED: the original truncation event."
THIS IS THAT EVENT, CAUGHT IN A ~70-MINUTE WINDOW.

## THE FACTS, MEASURED

Earlier this session (~19:53 local), during the precision-audit confound check:
    index = 475   hashes = 475      <- repaired and healthy, measured directly

Now (~21:05 local):
    HybridStore   index = 16   hashes = 477
      _redis      index = 16   hashes = 477     <- data INTACT, membership clobbered
      _file       index = 16   hashes =  20     <- the stale small plane

The system's own checker agrees, unprompted:
    py scripts/repair_learning_index.py --check
    FAIL: 461 lesson(s) exist but are invisible to every keyword search (96% of the corpus).

## WHY IT MATTERS BEYOND ITSELF

at_action.py -- the PreToolUse hot path -- takes MEMBERSHIP from
lrange("learn:experiments:all") (learning_store.py:778, and the code comment says so). So for
part of this session, recall has been drawing from 16 of 477 lessons (3.4%).

The 16 survivors are the same shape the note described, and they are exactly the lessons that
kept recurring in this session's hook output:
    escalation_is_grade_plus_route_both_or_neither, stall_signal_is_backlog_age_not_cursor_age,
    hang_guard_needs_latency_budget, daemon_needs_spawn_runner, wake_local_cursor_history_replay,
    p2_auto_chunk_intake_doors, wake_watcher_insta_fires_lane_divergence, offline_exp,
    semantic_documentation_update_strategy, semantic_refactoring_progress_analysis,
    backward_compatibility_refactoring_strategy, semantic_naming_pattern_discovery,
    semantic_naming_readability_impact, relationship_types_framework_design,
    silent_inline_script_parse_failure_diagnosis, quiesce_before_process_cleanup

Six of the sixteen are the 2026-06-17 semantic_* batch -- the SAME six the note named. This is
not a fresh truncation to a new set; it is the SAME 16 returning.

## A CORRECTION THIS FORCES ON TONIGHT'S OWN WORK

Earlier tonight I re-ran case 21 (docs/WISHLIST.md) against what I measured as a repaired
475-lesson index, got three different (still off-point) items, and concluded: "repairing
membership changed WHICH noise fires, not THAT it fires."

That conclusion still stands -- the re-run genuinely happened at 475, and the three replacements
are genuinely off-point. But anyone re-running that command NOW will get
semantic_documentation_update_strategy back and reach the opposite conclusion, because the index
has since collapsed. The command in the verdict doc is only meaningful while the index is
healthy. ALWAYS run repair_learning_index.py --check BEFORE trusting any recall measurement.
That is a new precondition on every number in the precision audit.

## THE SAME 16 RETURNING -- what that rules in and out

RULED OUT: a wipe-then-rebuild. If the list had been emptied and refilled by normal writes,
survivors would be only lessons written after the wipe. Six survivors are from 06-17.

LEADING HYPOTHESIS (NOT PROVEN -- do not build on it without a repro):
The File plane holds 20 hashes and a 16-entry list. The Redis plane holds 477 hashes. If any
process syncs or reconciles File -> Redis for the LIST key, Redis's repaired 475-entry list is
overwritten by the File plane's stale 16, while the 477 Redis HASHES survive untouched because
they are separate keys. The observed end state matches that mechanism exactly:
list clobbered to the stale value, hashes intact and still growing (475 -> 477).

WHAT HAPPENED IN THE WINDOW (from the event log, UTC):
    23:35:40  [fail] py -m pytest tests/test_precision_audit.py -q   <- the named prior suspect
                     (pytest_destroys_the_live_learning_index) BUT this precedes the healthy
                     475 measurement, so it cannot be the cause on its own
    00:39:56  [boot] codex_trellis booted -- a NEW seat, task "Research the latest TRELLIS..."
    00:45:11  [learning] lesson: powershell_wsl_nested_quote_probe   (one of the +2 hashes)

A new agent booting into the store during the window is the strongest untested lead, especially
if its environment resolves the store to a File-primary configuration. NOT ESTABLISHED.

## NEXT STEPS

1. REPAIR to restore service (done at time of writing; 461 lessons restored).
2. ROOT CAUSE, not a repeat repair. Daniel's standing rule applies: a known-limitation note
   around a reproducible defect is the trigger to fix it properly. The fix that shipped this
   arc made the index unable to SELF-HEAL through the normal write path; it did not stop
   whatever CLOBBERS it. Those are different bugs and only the first was fixed.
3. A GUARD WITH TEETH: --check is currently blocking in pre-push. Pre-push is far too late --
   the corpus went blind mid-session and nothing said so. It belongs in the SessionStart
   whisper and/or as a cheap periodic assertion, so the next occurrence announces itself
   instead of being found by a seat that happened to look.
4. Pin candidate: write a lesson, truncate the list to a stale subset, and assert that
   at_action still surfaces the new lesson -- i.e. that membership derives from the hash plane
   rather than the list. The arc claimed this was the fix; the recurrence suggests the claim
   is not fully true, or the list is authoritative again on some path.
