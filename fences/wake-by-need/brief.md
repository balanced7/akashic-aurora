# FENCE BRIEF — wake-by-need (S3, T421): wake decides by need, not by kind

**Fence:** `wake-by-need` · **Tier:** lite · **Opened by:** claude (Vandor), 2026-10-01 · **Builder:** claude · **Blind half (half_a):** Heimdall (deepseek), his pick (a) at 13:42 · **Reconciler:** claude

## CHARTER

Daniel, 2026-10-01 13:37: "What would the ideal version of this look like and how do we get there?" and 13:40: "I really like this, think you can get it built with Heimdall?" The ladder note (ADR_1001133813_4f565322) property (2): "Wake decides by need, not by kind: operator always, directed asks, settlements of my own asks; everything else batched to the next boot. One wake per logical event, per-sender coalescing, so a chatty peer cannot burn plan."

## THE QUESTION

Does the harness listener now wake only for mail that needs this seat (operator, directed asks, answers to its own asks), hold ambient mail without consuming it and confess the count, coalesce a peer burst into one wake while never making the operator wait, and leave a receipt for every exit so wakes per day and turns-with-nothing-to-do become numbers?

## INPUTS

- Design: the ladder note; `core/comm/wake_tiers.py` (the ladder: 0 operator, 1 directed ask, 2 settlement, 3 ambient; `admits(tier, floor)`), already built 2026-09-23, opt-in per arm.
- Build (this fence): `agent_cli.py` `standby_min_tier()` / `standby_listener_argv()` / `--min-tier` (default 2 via `WAKE_FLOOR_DEFAULT`, env `BIFROST_WAKE_MIN_TIER`); `scripts/bifrost_wake.py` the settle window (`BIFROST_WAKE_SETTLE_S`, default 15 s; tier 0 exits at once) and the receipt at every exit; `core/comm/wake_seat.py` `append_wake_receipt` / `wake_receipts_summary` / `wake_receipts_path` (state/wake-receipts/<agent>.jsonl, git-ignored).
- Pins: `tests/test_wake_by_need.py` (RED first).
- Baseline, measured by hand from this session's task log 2026-10-01 09:00-13:45: 12 listener exits; 8 carried operator or peer mail that needed me; 2 were peer traces or a quiet cycle; 2 were Heimdall's directed chats (informational). Target after S3: zero exits with nothing to do; operator wake latency unchanged.

## RULES OF ENGAGEMENT

- Blind: run the drill before reading the diff; say which you read first.
- Never kill or displace Vandor's live listener (session bb86400e); use a throwaway agent id and the hermetic FakeApi in the pins, or a real listener on a test agent against the live bus.
- Zero is not no: a held message is reported as held, with its count.
- One document, written once, `fence write wake-by-need --slot half_a --file <path> --by deepseek`.
- ANSWERED IN ADVANCE (your question): the operator is tier 0 and is EXEMPT from the settle window and from any cap, by construction: a tier-0 message ends the block immediately. Only tiers >= 1 wait the settle window so a burst rides one wake.

## OUTPUT CONTRACT

half_a: sections E1-E6 below, each with OBSERVED (verbatim lines), VERDICT (HOLDS / FAILS / UNCHECKABLE), FALSE-IF; then VERDICT ON THE FRAMING and what you would not build. Cite file:line.

- E1 A peer's directed chat (kind=chat, to=<agent>) at floor 2 does NOT wake; the quiet line says "held below tier floor 2".
- E2 An operator chat directed to the agent wakes within one block (seconds), settle window or not.
- E3 A directed request/handoff from a peer wakes.
- E4 Three peer asks inside the settle window produce ONE listener exit carrying all three.
- E5 Every exit appends a receipt with outcome in {woke, quiet, cycled}, tiers, below_floor; the standby prints the 24 h counts on the next arm.
- E6 What this does not claim: name what still burns a turn (e.g. a peer re-asking every N minutes as distinct asks; redelivery twins are already deduped by S0-gamma).

## 5. Acceptance (pre-registered)

Pins GREEN after RED; E1-E5 observed by Heimdall; the live session's next 24 h of receipts show zero exits without mail (quiet cycles aside, which are planned); operator wake latency unchanged (one block).
