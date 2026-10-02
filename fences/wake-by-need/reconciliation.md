# Reconciliation -- wake-by-need (lite, S3 / T421)

**By:** claude (Vandor), builder and reconciler, 2026-10-01 20:40 local. **Half_a:** Heimdall (deepseek), blind, sealed through the door. **Build:** 45532d3a (RED), 70264777 (GREEN), 76cdf4e6 (receipts stay out of the machine ledger under pytest). **Daniel's words:** the ladder's property (2), "wake decides by need, not by kind."

V1. [CERTAIN] E1 holds -- and Heimdall's wording ask is ACCEPTED: the observable is "a peer's AMBIENT mail (a broadcast completion or ask to *)", not "a peer's directed chat"; chat is rejected by the kind allowlist before the floor is ever asked. The pin already exercises the broadcast shape; the brief's E1 sentence is amended to match.
V2. [CERTAIN] E2 holds -- the operator is tier 0 and exempt from the settle window by construction (it never enters the gate), which is the property this slice exists for.
V3. [CERTAIN] E3 holds -- directed request/handoff/question/blocker rank as directed asks and wake at floor 2.
V4. [CERTAIN] E4 holds -- the settle window reuses the one `_admit` closure; three peer asks inside the window are one exit carrying all three.
V5. [DESIGN] E5 holds with Heimdall's scope caveat ACCEPTED in the direction he recommends: the receipt covers {woke, quiet, cycled}; displaced, tombstoned and bus-offline exits are stand-downs, not plan-spending exits, and widening the meter to them would pollute the number the operator wants (turns spent vs turns with nothing to do). The brief's "every exit" is narrowed to "every waking, quiet or cycled exit".
V6. [CERTAIN] E6, what still burns a turn, adopted verbatim: a peer re-asking beyond the settle window is a new wake per ask (out of scope by design; measure it in the receipts before building a cure); redelivery twins are S0-gamma's; the floor holds but never drains, so `held_below_floor` is a running re-count of holds and never a distinct-message inventory (no downstream surface may read it as one); an operator broadcast of a non-chat kind wakes every seat by the ladder's tier 0, and the lounge carve-out (to=* chat) stands by Daniel's ruling.
V7. [CERTAIN] Live, the same evening: floor-2 listeners on the claude seat woke on tier 0 and tier 2 mail only, with zero held-below-floor and zero quiet exits across the afternoon; the first receipt landed 13:50.
V8. [CERTAIN] Method -- RED pins committed before the fix; 7 pins, then 8 with the ledger-isolation pin; neighbouring wake, tier, standby, seat and stop-hook pins green; the driller read the brief and the pins first and said so.

## What this closes and what it does not

Closes: the arm's budget lever. A seat wakes for the operator, for directed asks and for answers to its own asks; everything else waits for boot and is confessed by count; every plan-spending exit leaves a receipt the next arm prints. Does not close: cross-window per-sender coalescing (V6, measure first), a distinct-message inventory of held mail, and the naked stand-down exits, all named and deliberately left.
