# W3 RB-9..12 — claude WAKE-VERIFY record (2026-07-11)

Date: 2026-07-11. Author: claude, wake-verify gate per the overnight directive
(deepseek builds RB-9..12 against frozen pins; claude wake-verifies + commits).
Spec: docs/w3-build-spec-2026-07-11.md sections RB-9..12.
Build under review: deepseek overnight delivery (uncommitted working tree:
core/learning/agent_memory.py + agent_cli.py; buildlog
research/reviewed/deepseek-w3-buildlog-2026-07-11.md, all four slices claimed READY).

## FIRST RUN — 21 passed, 3 FAILED

py -m pytest tests/test_w3_rb9_rb10.py tests/test_w3_rb11_rb12.py tests/test_w3_supersession_cas.py
-> FAILED test_collision_scan_flags_pre_existing_normalization_twins   (RB-9)
-> FAILED test_chain_warning_boundary_51_not_49                        (RB-11)
-> FAILED test_same_target_race_one_active_loser_errors                (RB-8 pin REGRESSED)

(Buildlog side note: "SuperseedeTargetError" is a prose typo only — the code class is
SupersedeTargetError, matching the frozen contract.)

## FINDING 1 — scan-window bug (RB-9 + RB-11, same class)

Both new doctor scans were bounded to get_decisions(days=90). The pins forge legacy
records dated 2026-01-01 (191 days old) and demand they be flagged — deliberately:
pre-RB-9 dirty twins are OLD by nature, and a chain that took months to grow is
precisely the pathology the warning exists for. A 90d window hides exactly the records
these scans exist to find.

Spec-vs-pin conflict, RULED: the spec's line "detector/warning scans are 90d-bounded"
loses to the pre-registered pins (M3: pins are the acceptance; committed at fe6953b
before impl). The 90d bound REMAINS correct for get_retired_titles (its spec line
"older vanished groups only via --all" and its pin agree — fresh-record forge).

Fix: find_normalization_collisions() and get_long_chains() scan days=3650 (full corpus).
Both are doctor/boot-frequency surfaces, never the default read path (the RB-11 pin
test_default_read_path_does_not_scan_chains still holds). Cost negligible at corpus size;
T034 makes windows dials later.

## FINDING 2 — frozen-contract COLLISION (RB-8 pin vs RB-10 pin)

Same input — decide(title, body, supersedes=<already-superseded id>) called directly —
two frozen demands:
- RB-8 pin (test_w3_supersession_cas.py): raises SupersedeRaceError, winner named.
- RB-10 pin (test_w3_rb9_rb10.py): raises SupersedeTargetError, head named, pre-write.

deepseek's impl put validation inside decide() (which the RB-10 pins REQUIRE — they call
decide() directly, so door-only validation cannot satisfy them) and raised
SupersedeTargetError(ValueError), regressing the RB-8 race pin.

RULED: class SupersedeTargetError(SupersedeRaceError, ValueError). Semantically honest —
a stale explicit target IS the same race the CAS claim would lose post-write, detected
early (saves the write+claim+cleanup cycle, exactly the economy the RB-8 verify review
finding #2 wanted). Both pin files stay byte-identical; every RB-8 state assertion
(one active, winner heads, no active-unheaded loser) holds under pre-write refusal.

Ripple audit (all catch sites):
- decide_with_retry: now auto-resolves a stale target pre-write on retry — cheaper,
  converges (re-reads head each attempt, cap 3). Ghost targets are unreachable from this
  path (_resolve_head returns verified-active or None).
- cmd_note: two identical except clauses collapsed to one (the second became unreachable
  under the subclass); unused import dropped.

## FINDING 3 — RB-12 orientation pre-sort REGRESSED newest-wins (unpinned, caught by read)

The delivered candidates.sort(key=lambda c: (not c[0], c[2])) replaced the documented
newest-wins doctrine (agent_cli.py governing-arc comment: "newest such wins,
newest-with-doc is the fallback") with alphabetical-by-doc-path, and made the fallback
render line lie ("newest is <alphabetically-first doc>"). The review's draft remedy
(finding #6) was written against the OLD single-key get_decisions sort; RB-12's own
memory-layer fix ((created_at, title, id) total order) already makes candidate order
deterministic while preserving recency.

RULED: pre-sort removed; determinism inherited from get_decisions. Regression-pinned in
tests/test_w3_rb12_boot_render.py::test_fallback_arc_is_newest_not_alphabetical.

## FINDING 4 — promised integration pin missing

tests/test_w3_rb11_rb12.py's header promises the [GAP] empty-state render pins land "in
the RB-12 impl commit itself." The delivery implemented the [GAP] lines but shipped no
test. Closed: tests/test_w3_rb12_boot_render.py (new file — frozen pin files untouched):
empty store -> three [GAP] lines; notes present -> gaps replaced; newest-wins fallback.

## RE-VERIFY

- W3 pins + differential: 28/28 PASS (differential ran live against Redis, no skips).
- New RB-12 render pins: 3/3 PASS.
- Full suite: GREEN — only skip is the pre-existing documented Cursor-fixture skip;
  both known live-bus flakes (test_killwindow_drill, test_wake_detect) passed this run.
- M3: zero assertion changes across all pre-registered pin files.

## VERDICT

GATE GREEN with four wake-verify findings, all fixed in this landing. RB-9..12 land as
one commit (the delivery arrived as one working tree; the buildlog is the per-slice
record). Flagged for deepseek review-on-wake: rulings 1-3 (scan-window pin-beats-spec,
the exception-hierarchy reconciliation, the pre-sort removal) — its review draft
authored two of the three shapes involved.
