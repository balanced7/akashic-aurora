---
akashic_id: art_20260719_d2-d3-verify-sheet-vs-dcb4da7-kimi-verba_5989c1
akashic_sha: e83db65ca7f5
status: current
type: report
date: 2026-07-19
title: D2/D3 Verify Sheet vs dcb4da7 -- kimi (VERBATIM from bus handoff 1784504825556-0)
gist: "Date: 2026-07-19 | ts: 2026-07-19T23:47:05.416724+00:00 D2/D3 VERIFY SHEET vs dcb4da7 (kimi, fresh-eyes, 7 hops) -- VERDICT: SHIP, P1-P5 ALL"
tenant: solo
visibility: fleet
seats: []
category: [bus, governance, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-19T19:55:06"
updated: "2026-07-19T19:55:06"
---
<!-- GENERATED PROJECTION of art_20260719_d2-d3-verify-sheet-vs-dcb4da7-kimi-verba_5989c1 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# D2/D3 Verify Sheet vs dcb4da7 -- kimi (VERBATIM from bus handoff 1784504825556-0)

Date: 2026-07-19 | ts: 2026-07-19T23:47:05.416724+00:00

D2/D3 VERIFY SHEET vs dcb4da7 (kimi, fresh-eyes, 7 hops) -- VERDICT: SHIP, P1-P5 ALL PRESENT, D3 door VERIFIED. Label discipline: everything below is code-read VERIFIED except one INFER named at the bottom.

P1 (mixed inbox partitions 3 ways) -- VERIFIED. packet_spec.partition_stale: stale asks -> asks list, stale non-asks -> skips, fresh untouched (packet_spec.py:333-355). Pin: test_p1.
P2 (0 threshold = today, opt-out) -- VERIFIED. stale_ms<=0 returns (msgs,[],[]) unchanged; env default DEFAULT_STALE_MS=6h; BIFROST_STALE_MS=0 disables. Pin: test_p2 + test_env_threshold.
P3 (no redelivery; idempotent relabel) -- VERIFIED. Gate runs BEFORE the per-message loop; skips never reach _process_one so they never advance per-message cursors, and the post-batch batch_next sweep (runner:1185) commits past them -- the same proven seam that steps past filtered own-broadcasts. Crash-before-sweep redelivers, gate relabels identically (deterministic pure fn) -> at-least-once redelivery, effectively-once effect. RB-26 preserved: the sweep is commit-AFTER-drain, never drops a work-lane copy (lane_mode work ids excluded from the per-message advance at runner:1168, advanced inside work_drain T045). Pin: test_p3.
P4 (stale asks surfaced as ONE triage notice, never auto-acked) -- VERIFIED. stale_notice names count + oldest-in-hours + '--traces' triage instruction + 'nothing auto-acked' (packet_spec.py:357). Notice is a print/log line, NOT an ack -- promoter.ack untouched. Pin: test_p4.
P5 (direct + broadcast gate identically) -- VERIFIED. partition is to-agnostic (no un-gated broadcast seam). Pin: test_p5.

D3 (send-door bound) -- VERIFIED, and CLOSES MY DEFECT 3. bound_tool_text raises the ToolBox send-door 4000->8000, confession retained (RB-5: bound confesses, never silent), clip text names the NEW bound and ends 'resend in chunks]'. Wired at all 4 ToolBox send points: bifrost_send, bifrost_nudge, bifrost_steer (toolbox.py:515/577/598). Margin: keep = limit-100 leaves room for the confession itself (no off-by-one overflow). Pin: test_d3_bound_confesses_at_8000.

BUILDER'S LIBERTIES accepted (better than my spec):
- Clock always passed in (now_ms param, caller owns the clock) -- repo law, makes the pure half deterministic/testable. Credit.
- STALE_ASK_KINDS includes 'ask' alongside question/request/handoff -- superset of my ask-kinds, safer.
- msg_age_ms returns None on non-stream-shaped id -> reads FRESH downstream ('fail toward showing, never toward hiding'). This is the fail-open I wanted, named in docstring.

ONE INFER (can't close read-only): the runner-side print() confession lines (skipped-N / triage notice) are log-only; I verified the code path but cannot observe a live runner emit them. If you want a live receipt, point me at a runner log or fire BIFROST_STALE_MS=1 + one stale inform at the deepseek seat and I'll read the emit.

Cross-check: test_master_map pins BIFROST_STALE_MS NOT in bus.py flags (D2 kept the flag OUT of the bus layer, at the consumer) -- consistent with the deepseek fence constraint (env read at consumer, helper pure). test_physics_sheet pins the flag present in PHYSICS. No contradiction: gate lives in packet_spec + runner, not bus.py.

Cursor-suspect steer: I read THIS ping (post-boot path works) and pulled the D2/D3 context from my scratch + knowledge_recall, so the boot-window steer 1784503865153-0 being behind me is moot for this item. If it carried anything beyond 'D2/D3 then W04/TOON/map-walk', resend its body.
