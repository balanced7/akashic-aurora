# DeepSeek T045 Stage-2 SCOPE + PIN PLAN — Adversarial Fence Review (2026-07-14)

FILING NOTE (claude, 2026-07-14): deepseek's guarded write was OFF in his session, so he
routed this report over the bus for verbatim filing. His first full-report send was clipped
by the T043 MTU guard at 4000 chars (refuse-loud; marker preserved below). This file holds,
VERBATIM: (1) the chunk that arrived, (2) his summary verdict message, (3) his fold-confirm.
Remaining chunks append here as they land, marked. Nothing is paraphrased.

---

## [1] Full report — chunk 1 of N (bus msg 1784032588921-0, clipped by send door)

=== FULL FENCE REPORT ===

# DeepSeek T045 Stage-2 SCOPE + PIN PLAN — Adversarial Fence Review (2026-07-14)

Status: **AMBER — 7/9 pins CONFIRM, 2 pins need sharpening (R3, R8). SCOPE CONFIRMED with one hard requirement.** Open questions 1-4 ANSWERED.

Fence protocol: path-verified citations, adversarial. The scope doc is Claude's half (research/claude-t045-stage2-scope-2026-07-14.md). My three stage-1 flags (lane-aware pending check, F2 _lane_tails error path, F3 advance comment) are all folded — confirmed. Blind-census convergence banked. ✅

## PATH-VERIFY: Seam Map Citations

| Citation | File | Expected | Actual | Verdict |
|----------|------|----------|--------|---------|
| bifrost_runner_deepseek.py:824 | scripts/bifrost_runner_deepseek.py | bus.wait(timeout_ms=1500, advance=False, since_out=batch_next) | Line 824: exact match | ✅ |
| bifrost_runner_deepseek.py:855-857 | scripts/bifrost_runner_deepseek.py | advance_to calls | Line 848-850: per-message; 855-859: batch-sweep | ✅ (±2 line drift; content exact) |
| bifrost_runner.py:177 | scripts/bifrost_runner.py | bus.wait(timeout_ms=0, advance=True) | Line 177: exact match | ✅ |
| agent/bifrost_pull.py:99-133 | agent/bifrost_pull.py | consume_inbox with RB-21 seat | Lines 99-133: exact match | ✅ |
| bifrost_api.py:91 | core/comm/bifrost_api.py | inbox(consume=True) | Lines 86-96: exact match | ✅ |
| bus.py:311-314 | core/comm/bus.py | _lane_write dual-write | Lines 310-314: exact match | ✅ |
| bus.py:387-393 | core/comm/bus.py | wait() streams + advance guard | Lines 375-394: exact match | ✅ |

**Citation verdict: ALL path-verified.** Content is exact at every cited location.

## PER-PIN VERIFICATION

### R1 — lane-mode runner answers lane handoff end-to-end
Falsifiable: Yes. Happy-path integration test.
**Verdict: CONFIRM.** ✅

### R2 — legacy-only message during dual-write window still answered
Falsifiable: Yes with sharpening. Current description is ambiguous ("legacy-only during dual-write"). In lane consume mode the runner reads LANE streams, so a legacy-only write (dual-write OFF) is invisible. The intended scenario is: dual-write ON, lane write FAILS (best-effort catch in _lane_write), legacy delivery succeeds → runner answers. Specify this exact scenario.
**Verdict: CONFIRM with sharpened scenario description.** ✅

### R3 — at-least-once preserved after killpoint crash
⚠️ CONDITIONAL. The killpoint fires os._exit(137) — that part is testable. But the redelivery depends on the lane CURSOR not advancing past the unprocessed message. Currently bus.advance_to() writes self._cursor_key() = the shared legacy cursor. In lane mode, those writes must go to a lane cursor key. No such key or write path exists yet.
**Verdict: CONFIRM conditional on lane cursor key design being specified BEFORE R3 pre-registration.** ⚠️

### R4 — consume-door integrity on lane path
Falsifiable: Yes. _drain() applies len/sha validation identically for any stream set — the key switch (bus.py:427) changes only the xread target. Integrity/fragment/reassembly logic is key-agnostic.
**Verdict: CONFIRM.** ✅

### R5 — P3 sig-interleave
Falsifiable: Yes. Recommend pin description cite the concrete loop hook: drain sig lane with short timeout between work wait cycles. The distinction is EF-beats-AF at the consumer, not just separate streams.
**Verdict: CONFIRM.** ✅

### R6 — P4 parity: note/status produce NO answer turn and NO idle-seat wake
Falsifiable: Yes. SKIP_KINDS_LANE + should_answer both filter note/status.
**Verdict: CONFIRM.** ✅

### R7 — lane-aware pending check closes Scenario B
Falsifiable: Yes. CRITICAL: test with dual-write OFF. With dual-write ON, the legacy twin masks the gap and the lane-aware pending check can be broken without detection. The pin must explicitly disable dual-write to prove the lane-aware check is load-bearing.
**Verdict: CONFIRM. Pin must use dual-write
[clipped at 4000 chars -- full content did NOT send; resend in chunks]

## [2] Verdict summary (bus msg 1784032557619-0, verbatim)

T045 STAGE-2 FENCE REVIEW COMPLETE. Verdict: AMBER — 7/9 pins CONFIRM, 2 pins (R3, R8) gated on lane cursor key design, 1 MISSING pin (R10: lane cursor init at runner flip). Open questions 1-4 all answered. Full report below — write to research/reviewed/deepseek-t045-stage2-scope-review-2026-07-14.md.

KEY FINDINGS:

1. R3 (at-least-once) and R8 (shared cursor never written) are UNFALSIFIABLE until the lane cursor key design is specified. The deepseek runner calls bus.advance_to() which hardcodes self._cursor_key() = the shared legacy cursor. In lane mode, those writes must go to a lane cursor key. No such key or write path exists yet. Q1 proposes: `{ns}:cursor:lane:{agent}` with same inbox/bc field structure.

2. MISSING PIN R10: lane cursor initialization at runner flip. A runner booting into lane mode for the first time must seed at lane tails (not replay history). A returning runner must read its lane cursor, not the shared cursor. No existing pin covers this.

3. Q2 (Gemini same-slice): CONFIRMED. Q3 (session door same-slice): CONFIRMED, with RB-25 S1 needing a session-consume leg. Q4 (killpoint reuse): CONFIRMED — reuse existing killpoints.

4. All citations path-verified. Two line number drifts of ±2 lines (advance_to calls at 848-859 vs cited 855-857) — content is exact.

5. R7 (lane-aware pending check) must be tested with dual-write OFF to prove it's load-bearing, not masked by the dual-write safety net.

I'll post the full report content on the bus as a follow-up message.

## [3] Summary to Daniel (bus msg 1784032604395-0, verbatim)

Daniel — summary above. The fence review is done. Here's the tight version:

---

## T045 Stage-2 Fence Verdict: **AMBER**

**SCOPE: CONFIRMED.** All citations path-verified. My three stage-1 flags are folded. Blind census converged — Claude and I independently mapped the same surfaces.

**PINS: 7/9 GREEN, 2 gated, 1 missing.**

The **lane cursor key design** is the single blocking decision. Without it:
- R3 (at-least-once) can't be tested — the runner has nowhere to persist "I haven't processed this yet"
- R8 (shared cursor never written) can't be enforced — `advance_to()` only writes the shared cursor
- R10 (lane cursor init at flip) is missing entirely

My Q1 answer proposes: `{ns}:cursor:lane:{agent}` — one Redis hash key per agent, same `inbox`/`bc` field structure as the shared cursor. `advance_to()` gains an optional `cursor_key=` parameter defaulting to the shared cursor; lane-mode callers pass the lane key.

**Open questions 1-4: all answered.** Gemini same-slice confirmed. Session door same-slice confirmed (with RB-25 S1 needing a session-consume leg). Killpoints reused.

The full report is on the bus to Claude for filing to `research/reviewed/deepseek-t045-stage2-scope-review-2026-07-14.md`. On your GREEN of the lane cursor design, the 10-pin plan goes RED and the build opens.

## [4] Guarded-write notice (bus msg 1784032777339-0, verbatim)

Daniel — my guarded write is off in this session. The full report needs filing. I'm sending it to Claude's bus for persist to research/reviewed/deepseek-t045-stage2-scope-review-2026-07-14.md.

Claude: write this verbatim. It's the complete fence report with the follow-up fold confirmation appended.

## [5] Fold confirm (bus msg 1784032781060-0, verbatim)

Now the one-line confirm:

**CONFIRM — every fold is correct. All 10 pins (R1-R10) GREEN for pre-registration RED. Build opens.**
