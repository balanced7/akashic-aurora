# RESULTS: kill-drill at n=5 (T274). Pre-registered at 8d4a3e1.

Run 2026-08-10, $0.3328, 15 calls, one file per call (no evidence clipped anywhere).

## Raw

| target | A blind | B resident | C foreign |
|---|---|---|---|
| expectations | 1 | 0 | 3 |
| reaper | 2 | 1 | 2 |
| scoring | 4 | 3 | 2 |
| friction | 2 | 1 | 1 |
| task_ledger | 2 | 2 | 1 |
| **TOTAL** | **11** | **7** | **9** |

Attribution, arm B, COMPUTED against the pack actually sent:
GROUNDED 1 · FABRICATED 0 · NONE 6

## The bars

**BAR 1 CLEARED, once.** On task_ledger the resident cited
`uuid4_reply_id_crash_race_duplicate_delivery` and that lesson WAS in its pack. Its own
words: "the pattern of assuming a local increment gives global uniqueness is the same hazard
as fresh-uuid-per-attempt in at-least-once delivery." That is a TRANSFER, not a restatement --
a lesson about message delivery applied to id allocation.

**BAR 2 CLEARED, once.** The finding is REAL (verified against source: `self._seq += 1` then
`tid = f"T{self._seq:03d}"`, read-modify-write with no lock) and the blind arm did NOT
produce it. So on one target, a recalled lesson produced a real finding a blind seat missed.
H2 holds -- at the confidence its own pre-registration gave it: LOW-MODERATE, one instance.

**H5 FAILED, and that is good news.** Zero fabricated citations. I predicted the model would
invent lesson ids once asked for them; it did not. Six findings said NONE honestly. The
citation channel is trustworthy enough to score, which the n=1 run could not establish.

**H3, kimi's null, SURVIVES ON VOLUME.** Blind produced 11 findings to the resident's 7. No
claim that residents find MORE is supported. If anything the archive made the resident
TERSER.

## The finding neither arm could have made alone

Blind found `\bT\d{3}\b` (task_ledger.py:431) -- the id regex breaks at four digits.
Resident found `f"T{self._seq:03d}"` -- the allocator that will PRODUCE T1000.
Same defect, opposite ends, and only together do they describe it: at T1000 the ledger mints
an id its own cross-check regex silently stops matching. We are at T274.

That is an argument for BOTH arms rather than for either.

## Triage depth, stated

task_ledger's four findings were verified line-by-line against source. Blind #2 (PARKED in
TASK_SETTLED_STATUSES) is a FALSE POSITIVE -- the docstring three lines above the constant
says done/parked/abandoned is intentional; the reviewer read the constant without its
contract. The remaining 23 findings across four targets are NOT individually triaged, so the
REAL-defect ratio per arm is unknown and no claim depends on it. Raw counts are raw counts.

## What this licenses

Persistence is now isolated as the cause of ONE real finding, with a checkable receipt. That
is strictly more than the n=1 run produced and strictly less than a general claim. kimi's
objection is NARROWED, not answered: the resident premium exists and is small, and on volume
the blind arm still wins.

The honest posture for T108 and everything downstream: residents are worth having for
LEGIBILITY (measured) and for occasional cross-domain transfer (now measured once). They are
NOT a replacement for blind review, and the drill's own best finding required both arms.
