# T040 spec review — claude cross-check of deepseek's Q1 findings, 2026-07-12

Completes the fenced T040 review. Deepseek's Q1: research/reviewed/deepseek-t040-review-2026-07-12.md
(he holds the advisory lock pending THIS). Spec under review: docs/packet-spec-v1-2026-07.md.
Verdict per finding + the finalized amendment set for Daniel's approval (the T040 gate).

## Cross-check verdicts

**1.1 ADD `pri` (drop-precedence 0-3 within work lane) — AFFIRM, with a sequencing note.**
Sound (DiffServ AFxy; it's an intra-class precedence, strictly smaller than the "priority tier LANE"
the cut list already refused). One optional int, default 2, inert unless a consumer sheds load. BUT:
v1 (N<10 agents, one machine) has no load-shedding consumer yet, so it must ride R3's exact pattern —
**spec the field NOW, enforce when a shedding consumer exists** (same as `seq`: "spec-now,
enforce-at-lanes"). Add the field; do NOT build drop logic in v1. Net envelope: +1 optional int.

**1.2 MODIFY per-lane `overflow` column (work/sig REFUSE-WRITE+backpressure, trace XTRIM) — STRONG
AFFIRM.** This is the most important finding. The spec claims work=QoS1/AF but line 107 only says
`maxlen 10000` with no overflow rule — so today a full work stream silently XTRIMs the oldest, which
can drop a latch-satisfying packet. That is a silent QoS1 violation. Making overflow explicit
(work/sig refuse-write-LOUD at the send door when at capacity; trace trims oldest) makes the QoS
contract honest and extends the existing MTU refuse-loud pattern to stream-full. It also pairs with
1.3: refuse-write IS the backpressure event. Spec-text (contract table) + a `BUS_MAX_STREAM_LEN`
send-door check. Adopt.

**1.3 ADD `ecn` bool (congested consumer → sender feedback) — STRONG AFFIRM.** This is the spec side
of the F3 fix. It's the minimum viable feedback wire (one optional bool, absent=0), set by a congested
consumer on its reply, read by the sender's rate controller — which in the reconciled endpoint set is
my **backpressure controller** (the F3 endpoint). Together: `ecn` marks congestion in the envelope +
the controller slows the hot flow, INSTEAD of the RateLimiter's global pause that froze the fleet in
drill 3. The bug and its principled fix now close in the spec. Net envelope: +1 optional bool.

**1.4 CUT `ttl` — AFFIRM THE DIRECTION, REFINE THE EXECUTION (this supersedes R1's keep-ttl).**
Deepseek is right that `ttl` (seconds-from-send) and `deadline_ts` (absolute) both express staleness,
and on ONE machine (one clock, no skew) the absolute form is strictly cleaner (gRPC precedent). BUT
the current spec gives them DIFFERENT violation semantics that serve different roles:
- `ttl` expired → **DROP + event** (fire-and-forget content freshness; no one waiting; e.g. a status
  broadcast that's useless after N seconds).
- `deadline_ts` past → **skip + DEADLINE_EXCEEDED reply** (reply-SLA; a sender is waiting).
A naive cut loses the fire-and-forget/broadcast content-freshness case (a DEADLINE_EXCEEDED reply to a
broadcast is meaningless). **Refined cut:** fold `ttl` into `deadline_ts` (send door offers the
`deadline_ts = ts + ttl_s` convenience so senders keep the ergonomic relative form), AND make the
DEADLINE_EXCEEDED reply **conditional on an armed expectation** — a past-deadline packet with NO armed
expectation just skips + emits a `stale` event (the old ttl-drop behavior), with a reply ONLY when the
sender is actually waiting. This gets deepseek's one-staleness-field simplification without losing
either behavior. Net envelope: **−1 field**. (Fallback if Daniel prefers minimal change: keep both but
make them mutually exclusive — a packet carrying both is REFUSED at the door.)

**1.6a Family cap 12 — AFFIRM** (matches R2; my endpoints half adds ZERO new families, so the cap is
untouched by the whole T041 set — independent confirmation the cap holds).

**1.6b Trace integrity default OFF + periodic spot-check — AFFIRM.** Good refinement of R5: keep the
hash off the QoS0 firehose (correct — no decision depends on a trace packet), but stamp len+sha on
every Nth (N=1000, dial) so the implicit-ECN telemetry-join wire can detect a corrupt trace stream at
~0.1% cost; consume-door logs mismatch at WARNING, never DROP. One sentence. Adopt.

**1.6c R8 seq enforcement — AFFIRM, and RECONCILE WITH 1.4.** Naming the gap-detection window is right,
but the spec (line 90) currently bounds it "by ttl" — and 1.4 CUTS ttl. So the bound must move: **hold
seq N+1 awaiting N for `min(remaining-time-to deadline_ts, GAP_WINDOW default 30s)`, then LOUD gap
event + proceed.** Use `deadline_ts` (the surviving staleness field) + a named `GAP_WINDOW` dial. This
catch is exactly why the cross-check matters — 1.4 and 1.6c both touch `ttl` and must move together.

## Convergence with my sealed endpoints half (the cross-cutting coherence)
- `ecn` (1.3) + my **backpressure controller** = the complete F3 answer.
- `overflow` refuse-write (1.2) = the backpressure TRIGGER (a full work lane backpressures the sender).
- ZERO new families across both the spec amendments AND all T041 endpoints — the cap (12) is safe.

## FINALIZED amendment set (for Daniel's T040 approval)
| # | Change | Envelope delta | Status |
|---|--------|----------------|--------|
| A | ADD `pri` int 0-3 (spec-now, enforce-when-shedding, like seq) | +1 int | affirmed |
| B | MODIFY per-lane `overflow` (work/sig refuse-write-loud, trace XTRIM) | spec text | affirmed (important) |
| C | ADD `ecn` bool (consumer→sender congestion, F3 wire) | +1 bool | affirmed |
| D | CUT `ttl`; fold into `deadline_ts` + conditional DEADLINE_EXCEEDED reply | −1 field | affirmed-refined (supersedes R1) |
| E | Trace integrity: default OFF + every-1000th len+sha spot-check | 1 sentence | affirmed |
| F | seq gap window: bound by deadline_ts + named GAP_WINDOW (30s), not ttl | 1 sentence | affirmed (reconciles B/D↔R3) |
| — | Family cap 12 | — | affirmed |

Net envelope: **+1 field** (`pri` + `ecn` added, `ttl` cut). All additions absent-in-common-case.
No new families. Both halves fenced-converged.

## DANIEL DECISION
Approve docs/packet-spec-v1-2026-07.md WITH amendments A–F? On approval the spec becomes LAW and the
**send-door hardening** (the riding build — now also framed as deepseek's Send-Door Gate endpoint,
which houses these overflow/MTU/len+sha/ecn checks) registers its M3 pins and BUILDS (engine-first is
satisfied — T029 is certified). The one genuinely load-bearing call is **D (cut ttl)** — my refined
version preserves both behaviors; your call whether to take the cut or the mutual-exclusivity fallback.
