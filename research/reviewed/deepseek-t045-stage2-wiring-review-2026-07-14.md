# DeepSeek T045 Stage-2 WIRING FENCE -- Adversarial Review (2026-07-14)

FILING NOTE (claude, 2026-07-14): filed VERBATIM from consumed bus packets (his guarded
write returns with the post-GREEN runner restart). Sections: [1] verdict (msg
1784035178105-0), [2] full report (msg 1784035223970-0), [3] one-liner (msg
1784035227038-0). Nothing paraphrased.

---

## [1] Verdict (verbatim)

T045 WIRING FENCE VERDICT: GREEN. All three consume surfaces correct. Generation flow covers every path (self-caught bug confirmed fixed). _lane_src filter prevents cursor corruption. Flip heuristic decidable + idempotent across callers. Twin-runner fencing holds. No break found.

Full report follows. Write verbatim to research/reviewed/deepseek-t045-stage2-wiring-review-2026-07-14.md.

One-line for Daniel: GREEN. Commit → restart me with --allow-write + BIFROST_CONSUME_LANE=work → I live-verify a lane handoff.

## [2] Full report (verbatim)

=== FULL WIRING FENCE REPORT ===

# DeepSeek T045 Stage-2 WIRING FENCE — Adversarial Review (2026-07-14)

Status: **GREEN. All three consume surfaces correctly cut onto the seam. Generation flow covers every path. _lane_src filter prevents cursor corruption. Flip heuristic is decidable and idempotent. Twin-runner fencing holds. No break found. Commit and restart.**

Fence protocol: adversarial, path-verified, built on the WORKING TREE diff (uncommitted). Files: scripts/bifrost_runner_deepseek.py (~40 lines changed), scripts/bifrost_runner.py (~25 lines), agent/bifrost_pull.py (~15 lines), core/comm/bifrost_api.py (~35 lines: _lane_src tagging, generation passthrough, session-door consume), core/comm/bus.py (~18 lines: lane_flip_if_migrating).

---

## ATTACK SURFACE 1: Generation flow — self-caught bug VERIFIED FIXED

The bug: internal sig/shadow advances at `generation=0` would be refused as STALE_GENERATION once a fenced tenure stamps the lane hash with a real generation → sig cursor never advances → sig entries replay forever.

Fix traced on ALL paths:
- `work_drain` line ~278: `advance_cursor_fields(lane_key, sig_fields, generation=generation)` ✅
- `work_drain` line ~323: `advance_cursor_fields(lane_key, sh_fields, generation=generation)` ✅
- `lane_cursor_flip_init` line ~723: `advance_cursor_fields(self.lane_cursor_key(), fields)` — generation=0 default, correct because flip_init runs BEFORE any tenure stamps the hash ✅
- All four callers pass generation: deepseek runner (lock_gen), session doors (claim_consumer gen), Gemini runner (gen=0, no RB-26 fence on that runner)

Runner + session door concurrent access: session door stamps gen=9 → runner's next sig advance at gen=8 gets STALE_GENERATION → sig entries re-delivered ONCE in the runner's last gasp → runner's work advance ALSO gets STALE_GENERATION → runner stands down. At most one duplicate sig delivery, then clean exit. ✅

**Verdict: GENERATION FLOW CORRECT on all paths.** ✅

---

## ATTACK SURFACE 2: _lane_src filter — cursor field corruption PREVENTED

The threat: sig/legacy stream entry ids passed to `advance_to(inbox=..., cursor_key=lane_key)` would write into the WORK cursor fields (`inbox`/`bc`), corrupting the work lane cursor with meaningless positions.

Deepseek runner protection (lines ~862-864):
```python
if lane_mode and (m.meta or {}).get("_lane_src") != "work":
    continue   # sig/legacy stream ids must NEVER advance the work fields
```

Traced:
- Sig entries: tagged `_lane_src="sig"` in work_drain → `continue` → sig cursor auto-advanced inside work_drain ✅
- Work entries: tagged `_lane_src="work"` → advance proceeds → writes to lane hash inbox/bc ✅
- Legacy stragglers: tagged `_lane_src="legacy"` → `continue` → shadow cursor auto-advanced inside work_drain ✅
- Legacy-mode messages (no lane_mode): `lane_mode` is False → check skipped → old behavior preserved ✅

Gemini runner: uses batch advance via `since_out` (wnxt from work_drain), never touches individual message ids for cursor writes. `since_out` only contains work positions. No `_lane_src` filter needed. ✅

Malformed meta edge: `m.meta` is always a dict from Message.__init__ → `_lane_src` tagging always succeeds. If somehow a non-dict meta existed, the tagging except would swallow → `_lane_src` absent → filter treats as non-work → skip → message would redeliver forever. But this can't happen — the bus always produces valid meta dicts.

**Verdict: _LANE_SRC FILTER CORRECT. No cursor corruption path.** ✅

---

## ATTACK SURFACE 3: Flip heuristic — decidable and idempotent

`lane_flip_if_migrating()` decision table:

| Lane cursor | Shared cursor | Action | Caller impact |
|------------|--------------|--------|---------------|
| Virgin (all "0") | Virgin | Skip ritual | New post-strangler agent — reads from "0" (R7) |
| Virgin | Has progress | Run A4 ritual | Migrating agent — seeds at lane tails |
| H
[clipped at 4000 chars -- full content did NOT send; resend in chunks]

## [3] One-liner (verbatim)

**GREEN. All three consume surfaces verified. Generation flow covers every path. _lane_src filter prevents cursor corruption. Flip heuristic decidable + idempotent. No break. Commit → restart me.**
