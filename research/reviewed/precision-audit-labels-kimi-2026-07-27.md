# Precision audit -- kimi blind labels (VERBATIM)

Status: current | 2026-07-27

---

1:a on
2:a on
3:a off
3:b off
3:c skip
4:a off
4:b off
4:c off
5:a off
5:b skip
6:a on
7:a off
8:a on
8:b skip
8:c skip
9:a off
10:a off
10:b on
10:c on
11:a off
12:a off
12:b off
13:a on
13:b off
14:a off
14:b off
14:c on
15:a on
16:a off
16:b off
16:c off
17:a on
18:a on
19:a on
19:b on
19:c on
20:a off
20:b off
20:c skip
21:a on
22:a off
22:b off
22:c off
23:a on
23:b on
23:c on
24:a on
25:a off
25:b off
25:c off
26:a off
26:b on
26:c on
27:a off
27:b on
28:a on
28:b on
28:c on
29:a on
29:b on
29:c on
30:a on

MISS 4 knowledge_boot_stale_directive (boot-context action; the stale-directive lesson exists in corpus and is exactly about this situation, surfaced at case 25 instead)
MISS 14 runner_guarded_write_leaks_locks fired, but the general "runner --help is not the runner's live behaviour" lesson (if filed) should have; partial — naming the pattern in case no lesson covers it: `--help` output drift from live flags, cf. bifrost_send_supported_flags
MISS 21 semantic_documentation_update_strategy fired and WAS on-point, but note this is the receipt case from Daniel's original complaint (40-day-old doc lesson on wishlist.md) — under the repaired index it is arguably correct; flagging for the fence round, not as a miss
MISS 25 gate_exit_codes_never_piped SHOULD have been the top hit for a `--help | head -25` action on a gate-adjacent CLI verb and it did fire — recording as on-label confusion risk instead; no miss
MISS 27 bifrost_runner_backlog_skip fired; the kimi-runner-specific lesson (kimi_phase1_cannot_arm_wake_watcher) exists and did not fire on the kimi runner action — cross-seat matcher gap candidate

**PACK SHAPE NOTE (design feedback, one line): the instrument is sound, but the recall arm needs the labeler to have grep access to the corpus — my MISS labels above are from memory of lesson titles, which makes the recall arm measure my memory, not the index. Next pass: give labelers a read-only grep door to the lesson store during the MISS phase.**
