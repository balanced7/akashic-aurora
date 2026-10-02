# half_a — wake-by-need (S3, T421) — Heimdall (deepseek), blind

**Read order (blind declaration):** I read the RED commit `45532d3a` (the pin file's docstrings
and test bodies — they state the intended behaviour but not the implementation) and the brief
FIRST. Then the GREEN commit `70264777`'s message. Then the implementation. I did **not** read
the GREEN diff before forming E1-E5 verdicts; verdicts below are from source line-reading, not
from the diff narrative. Everything cited is the current working tree at `scripts/bifrost_wake.py`
(~L354-658), `core/comm/wake_seat.py`, `core/comm/wake_tiers.py`, `agent_cli.py` (~L6459-6530).

---

## E1 — a peer's directed chat at floor 2 does NOT wake; quiet line says "held below tier floor 2"

**OBSERVED.** `WAKE_WORTHY_KINDS` (`bifrost_wake.py:56`) is `{request, handoff, reply, blocker,
question, completion, nudge}` — `chat` is **not** on it. So a peer's directed chat (`kind=chat,
to=<agent>`) is dropped at the *gate* (`wake_worthy` returns False, `bifrost_wake.py:157-159`),
never even reaching the tier floor. The pin `test_floor_two_holds_ambient_peer_broadcast_and_confesses`
does **not** use `chat` for exactly this reason — it uses `completion` with `to="*"` (a broadcast),
which passes the allowlist and ranks `AMBIENT` in `wake_tiers.wake_tier` (`wake_tiers.py:88-91`:
"Broadcasts are visibility … can never be tier 1 or 2"), then is held by `not admits(3, 2)`
(`bifrost_wake.py:456-459`), incrementing `below_floor`. The quiet line prints
`below_floor held below tier floor 2` (`bifrost_wake.py:644-645` + the shared `held` string).

**VERDICT: HOLDS**, with a naming caveat.

**FALSE-IF:** a peer `kind=chat` directed to the agent would be described as "held" — it is not;
it is *rejected at the allowlist gate before tiering exists*. Both outcomes are "does not wake",
but they are different instruments: chat is invisible (the echo default, intentional), while an
ambient broadcast is present-and-confessed. The brief's E1 wording ("a peer's directed chat …
the quiet line says 'held below tier floor 2'") conflates the two. The implementation is *more*
correct than the brief: a held count is only claimed for mail that passed the gate and was held
back by the floor (`below_floor` is incremented only after `wake_worthy` returns True and
`admits` returns False). An ambient broadcast IS confessed; a peer chat is silently skipped as
non-wake-worthy. If the brief means "a peer's directed chat" literally, the quiet line will show
**nothing** about it (it appears only in the `saw:` render as `frm:kind`, `bifrost_wake.py:432`),
not "held below tier floor 2". This is worth reconciling the *wording* of, not the behavior.

---

## E2 — an operator chat directed to the agent wakes within one block; settle window never delays it

**OBSERVED.** `_operator_ids()` defaults to `user,daniel,daniil` (`bifrost_wake.py:71`). In
`wake_worthy` the operator override fires **before** the kind allowlist and returns True for a
directed chat (the carve-out only suppresses `to="*"` broadcasts) (`bifrost_wake.py:147-151`).
In `wake_tiers.wake_tier` the same operator branch returns `OPERATOR` (tier 0) for a directed
chat (`wake_tiers.py:70-78`). `admits(0, 2)` is True, `woke_tiers=[0]`, and `out` fills in the
first `wake_block` that returns the message. The settle window guard is
`min(woke_tiers) > 0` (`bifrost_wake.py:605`): with `min==0`, the window is **skipped entirely**.
The pin `test_operator_mail_never_waits_for_the_settle_window` sets `BIFROST_WAKE_SETTLE_S=30`
and asserts `clock.now - t0 <= 10 + 1e-6` — the operator message at +10 ends the run with zero
settle wait.

**VERDICT: HOLDS** — operator is tier 0 and structurally exempt from the settle window (both the
`if … min(woke_tiers) > 0` gate at `bifrost_wake.py:605` and the guard's `min>0` condition at
`:607`). One block wake latency, unchanged from pre-S3.

**FALSE-IF:** an operator *broadcast* `to="*" kind=chat` were treated as tier 0 — it is not; it is
the lounge carve-out (tier AMBIENT, held at floor 2). That is by Daniil's 2026-08-31 ruling and
correct, but note it is the one place "operator" does not mean wake.

---

## E3 — a directed request/handoff from a peer wakes

**OBSERVED.** `request` and `handoff` are both in `WAKE_WORTHY_KINDS` (`bifrost_wake.py:56`).
`wake_worthy` admits them (kind is allowlisted, `frm != agent`, not a broadcast-reply).
`wake_tiers.wake_tier` maps `request`/`handoff` (both in `ASK_KINDS`, `wake_tiers.py:38`) to
`DIRECTED_ASK` (tier 1) when `directed_to_me` (`wake_tiers.py:85-87`). `admits(1, 2)` is True.
The pin `test_floor_two_wakes_on_operator_and_on_directed_ask` asserts a `handoff` from `kimi`
wakes and its receipt shows `tiers == [1]`.

**VERDICT: HOLDS.**

**FALSE-IF:** a peer's `question` or `blocker` failed to wake — they are also `ASK_KINDS`
(`wake_tiers.py:38`) and on the allowlist, so they wake too. Good coverage; no gap.

---

## E4 — three peer asks inside the settle window produce ONE listener exit carrying all three

**OBSERVED.** The settle window (`bifrost_wake.py:590-608`): when `out` is non-empty and the
minimum `woke_tiers` is > 0, it loops `_admit(api.wake_block(...))` for `settle_s` seconds,
reusing the **same** `_admit` closure so later batches ride the identical gate→floor→dedup chain.
`_admit` appends to the **shared** `out` and `delivered` lists (they are nonlocal and closed over).
So three peer `handoff`s arriving at +10/+18/+26 within a 30s window all append to one `out`, one
`delivered`, one exit. The pin asserts `r["mail"] == 3` and `out.count('"frm"') == 3`. The receipt
`mail=len(out)` counts them.

**VERDICT: HOLDS.**

**FALSE-IF** (design boundary worth naming, not a defect): the settle loop's exit condition is
`while time.time() < settle_until and (not woke_tiers or min(woke_tiers) > 0)`. If an **operator**
message (tier 0) arrives *during* the settle window, the loop breaks immediately — correct
(operator never waits). But an **operator message arriving *after* the settle window has lapsed**
on a peer burst is a *next* exit: the burst already rode one wake; the operator gets its own
instant wake. No lost mail, no operator delay; just two exits where a pedant might want one. Not
a defect, matches the "operator never waits" contract precisely.

---

## E5 — every exit writes a receipt (outcome ∈ woke/quiet/cycled, tiers, below_floor); standby prints 24h counts

**OBSERVED.** At the tail of `watch()` before `return 0`, a receipt is appended unconditionally on
every non-early-return path that reaches it (`bifrost_wake.py:650-656`) with `outcome` =
`"woke" if out else ("cycled" if cycled else "quiet")`, plus `mail`, `tiers`, `below_floor`,
`twins`, `floor`, `elapsed_s`, `session`, `origin`. `append_wake_receipt` (`wake_seat.py:~290-308`
block) appends one JSON line to `state/wake-receipts/<agent>.jsonl` (git-ignored), best-effort,
never raises. `wake_receipts_summary` (`wake_seat.py:311-343`) counts `wakes / with_mail / quiet
/ cycled / held_below_floor` over `since_s`. The standby arm prints both the floor and the 24h
summary on every arm (`agent_cli.py:6521-6526`).

**VERDICT: HOLDS**, with two durable-receipt caveats that are worth stating out loud (they are
`UNCHECKABLE` rather than failing):

1. **Early naked `return 0/2` paths write no receipt.** `stand-down` (seat displaced `:517`,
   lost `:526`), `tombstoned` (`:508-511`), and `bus OFFLINE` (`:566`) all `return` *before* the
   receipt block. These are genuinely "not a wake" exits — a displaced seat is a stand-down, not
   a listener outcome — so omitting them may be intended ("one line *per exit*" vs "per
   outcome-in-{woke,quiet,cycled}"). But the brief says "a receipt for **every exit**" and "the
   summary counts *wakes* = listener exits". A displaced/tombstoned/offline exit is an exit with
   no receipt, so `wakes` undercounts actual process exits. This does not break the *meter* (the
   thing you actually want: turns spent vs. turns with nothing to do), but the brief's word
   "every exit" is not literally true. Worth a one-line reconciliation: either extend the receipt
   to these paths with `outcome="standdown"`/`"offline"`, or narrow the brief's claim to "every
   *waking/quiet/cycled* exit".

2. **`outcome` for the `cycled` deadline line is correct** (`bifrost_wake.py:653`) but the
   deadline-cycle **confession** of held count (`held_c`, `:633-634`) was added and is present —
   confirming the brief's "deadline-cycle line confesses the held count" note.

**FALSE-IF:** the receipt were written *after* `say_seen_at_fire` could throw — it is not; the
receipt block is guarded by its own `try/except` and sits after the prints but the `say_seen`
call is separately fail-open (`:647-649` guarded). Receipt cannot cost the wake. Clean.

---

## E6 — what this does NOT claim (still burns a turn)

Written blind, then checked against source:

1. **A peer re-asking every N minutes as distinct asks** rides `logical_key = frm|ts|kind`
   (`bifrost_wake.py:352-356`). A genuinely *new* ask from the same peer with a new `ts` is a new
   key → new wake. "Per-sender coalescing" (the ladder note's property) is only within a settle
   *window*, not across time. A chatty peer that spaces its asks beyond `BIFROST_WAKE_SETTLE_S`
   still burns one plan per ask. This is the **biggest remaining turn-burner** and is *out of
   scope by design* (the ladder note says "batched to the next boot", and batching-until-boot
   would need a consume-and-re-emit budget, which S3 deliberately does not do).

2. **Redelivery twins are S0-gamma, not S3.** `_declared_intent_for` + `_reply_is_settled` +
   the `seen_set`/`seen_keys` sidecar (`bifrost_wake.py:468-482`) already dedupe dual-write twins
   and RB-26 redelivery. S3 inherits this; it is not S3's claim.

3. **The floor does *not* consume the backlog.** `below_floor` mail is counted but never drained
   (`bifrost_wake.py:456-459`). It re-appears on the next arm via `wake_block`'s SEED rule and is
   re-held (and re-confessed) forever until someone *reads* it. The 24h `held_below_floor` is a
   running *total* of holds, not distinct messages — a single held broadcast re-counts every arm.
   That is correct as an alert ("there is ambient mail you keep not reading") but it is **not** a
   deduplicated "N distinct messages held".

4. **Kind ≠ operator broadcast of a non-chat kind** (`frm=operator, kind=blocker` broadcast) —
   operator outranks kind, so a non-chat broadcast from the operator *does* wake (tier 0). Only
   `to="*" kind=chat` is the lounge. This is arguably a gap: an operator `blocker` broadcast wakes
   every seat, though it may be intended ("operator always wakes" is the ladder's tier 0).

---

## VERDICT LINES (M1-CF)

V1. [CERTAIN] E1 HOLDS — a peer's ambient mail (broadcast completion, `to="*"`) passes `wake_worthy`
and ranks AMBIENT, is held at floor 2, and the quiet line confesses `held below tier floor 2`;
but a peer's *directed chat* (`kind=chat`) is gate-rejected by the allowlist (`WAKE_WORTHY_KINDS`
omits `chat`) before tiering exists, so it is silently skipped, never "held". The E1 wording
conflates gate-rejection with floor-holding.

V2. [CERTAIN] E2 HOLDS — the operator is tier 0, exempt from the settle window by construction
(the `min(woke_tiers) > 0` guard is structurally skipped), wakes within one block.

V3. [CERTAIN] E3 HOLDS — directed `request`/`handoff`/`question`/`blocker` rank DIRECTED_ASK
(tier 1), admit at floor 2, wake.

V4. [CERTAIN] E4 HOLDS — the settle window reuses the single `_admit` closure into one shared
`out`/`delivered`, so a peer burst inside the window is one exit carrying all three.

V5. [DESIGN] E5 HOLDS with a scope caveat — the receipt writes on woke/quiet/cycled but the naked
early-return paths (displaced seat, tombstoned, bus offline) return before the receipt block, so
the brief's "every exit" is not literal; "wakes" counts plan-spending exits, not process exits.

V6. [INFERRED] E6 — largest remaining turn-burner is a peer re-asking beyond the settle window
(per-sender coalescing is window-scoped, not time-scoped); `held_below_floor` is a running re-count
of holds, not a distinct-message inventory.

## VERDICT ON THE FRAMING

The framing — "wake decides by need, not by kind" — is **the right axis**, and the implementation
correctly keeps `wake_worthy` as the *sole gate* and adds the tier floor as a *second, independent
question asked only of admitted mail* (`bifrost_wake.py:440-452`, `wake_tiers.py` docstring). The
single most load-bearing decision is the **one `_admit` closure** that both the main loop and the
settle window call: there is no second implementation to drift. That is the kind of structural
choice that keeps a "one meaning under two implementations" defect out of this house for exactly
the class of bug it keeps re-paying for. The fail-open directions (mailbox outage → still wake;
receipt → never cost the wake; operator → never subject to a cap) are all pointed the right way.
The operator's tier-0 exemption *by construction* (it never enters the settle gate, `:605`) is
the best single property here: it is not a tested-for side effect, it is structurally impossible
to violate, which is what "never makes the operator wait" ought to mean.

### What I would not build (the dissenting edge)

1. **I would not widen the receipt to the naked `return` paths silently.** Right now `wakes`
   undercounts *process exits* (displaced/tombstoned/offline) but correctly counts *plan-spending
   exits*. If the meter's purpose is "how many turns did this seat spend, and how many had
   nothing to do", the current definition is the one that matters; widening it to count
   stand-downs would pollute the number the operator actually wants (turns-with-nothing-to-do)
   with administrative churn. I would **narrow the brief's word "every exit"** rather than widen
   the receipt. (See E5 caveat 1.)

2. **I would not add cross-window sender coalescing now.** "A peer re-asking every N minutes"
   (E6.1) is real, but the fix — a consume-and-re-emit batching budget — drags in the
   detect-without-consume doctrine and a semaphore that is a different surgery than this fence's
   "hold vs. admit" question. Ship the window; measure whether peer-re-ask churn shows up in the
   receipts *first* (that is exactly what the receipt was built to prove). Don't pre-build the
   cure for a burn you haven't yet metered.

3. **I would not treat `held_below_floor` as a distinct-message count** in any downstream surface
   (E6.3). It is a per-arm running re-count of holds, not a deduped inventory. Any renderer that
   reads it as "N messages the floor held back" overstates. If doctor or the standby line ever
   pivots off it, it needs a distinct-key set first.

4. **I would not extend the operator override to `to="*" kind=chat`** (E6.4). The lounge carve-out
   is Daniil's explicit ruling and it is load-bearing. Leaving it is correct even though a
   literal reading of "operator always wakes" is violated by that one shape.

---

## BLOCKING / reconciliation asks to claude

- **E1 wording:** "a peer's directed chat … held below tier floor 2" is not literal — chat is
  gate-rejected (allowlist), not floor-held; only an ambient **broadcast** (completion/ask to
  `*`) is floor-held-and-confessed. Confirm the brief means "a peer's *ambient* mail", or update
  the observable to name the broadcast shape the pin actually exercises.
- **E5 "every exit":** confirm whether displaced/tombstoned/offline exits are in-scope for a
  receipt, or narrow the claim to `{woke, quiet, cycled}`. I recommend narrowing.
