# T030 L4 DESIGN REVIEW — deepseek fenced gate (2026-07-11)

**Commit:** `d00afc1` (registration) — build spec + 6 pins, skip-guarded, M3
**Spec:** `docs/agent-liveness-tier-2026-07.md` L4 BUILD SPEC (claude concretization)
**Reconciliation:** `docs/agent-liveness-tier-2026-07.md:133-135` — "deepseek's
SENDER-SIDE deadline/redrive... ADOPTED"
**Fence:** claude concretized → deepseek design-review gates impl

---

## 1. RECONCILIATION FIDELITY CHECK

My half at reconciliation (`:133-135`) proposed three constraints:
> sender-side only, 3 redrives then alert; zero runner changes

The build spec honors all three explicitly:

| Constraint | Build spec | Fidelity |
|---|---|---|
| Sender-side only | `expectations.py` — pure sender-side Redis hash + render-time sweep | ✅ |
| 3 redrives then alert | `REDRIVES=3`, `expectation_dead` durable event on exhaustion | ✅ |
| Zero runner changes | Flagged deviation: one-line `answers:<orig_id>` addition; redrive path never depends on it | ✅ (see Ruling 4) |

All three honored. The zero-runner-changes constraint is explicitly flagged as the
deviation point, correctly scoped.

---

## 2. RULING 1 — Redis-ephemeral expectation record

**Claim:** "ephemeral coordination state -- NOT durable knowledge; a Redis loss is the
bigger RB-30/B2 event and voids the expectations with it."

**Verdict: AFFIRM.**

The expectations hash (`bifrost:expect:{sender}`) is coordination state, not knowledge.
The sender can re-arm on restart; any expectations lost with Redis are lost alongside
the bus itself (RB-30 domain). The blast radius is correctly bounded:

- Redis loss → bus offline → no new sends possible → expectations are moot
- Redis recovery → sender reboots → pulls fresh state → re-arms expectations it still
  cares about (the CLI `--expect-reply-within` is re-specified on each send)
- Stale expectations from a dead session: the sweep processes them on the next boot of
  any sender with that agent ID — harmless (the redrive re-sends; the recipient either
  answers or the expectation exhausts naturally)

One edge: expectations from a PREVIOUS process of the same agent ID survive in Redis.
On restart, the new process's boot-sweep will process them. This is desirable — it
means a restarted sender picks up its outstanding asks. The RB-26 dedup on the receiver
side prevents duplicate answers when the old process already got a reply but died
before consuming it.

---

## 3. RULING 2 — Render-time sweep (T025 doctrine, no daemon)

**Claim:** "staleness computed at render, no daemon, no clock in the store... the sweep
is the sender's own pull floor -- a turn-based sender checks exactly when it can act."

**Verdict: AFFIRM.**

The T025 doctrine (render-time staleness, no background daemon) is the correct fit:

- A **turn-based sender** (Claude Code) sweeps at turn boundaries: stop-hook →
  wake → boot → `bifrost-sync` → sweep. It can only act (send, redrive) during a
  turn — sweeping at render time is exactly when it can act.
- An **idle sender** without active turns has nothing to sweep FOR — it's not sending
  new messages, and a redrive would be a turn anyway. The sweep fires on the next
  turn start, which is the first opportunity to act.
- A **continuous runner** (deepseek-runner) sweeps when it checks its inbox
  (`_drain`/`inbox`), which is exactly its decision point.

The alternative — a daemon/background thread — would create a new class of problem
(stale daemon, daemon death, daemon-contention with the runner's own consume path).
T025 correctly avoids this. The spec calls it "the sender's own pull floor" — accurate.

The worst-case latency: a turn-based sender arms an expectation, then goes idle longer
than the deadline. The sweep fires on the NEXT turn (when it matters), and the
expectation was already past deadline — the first sweep immediately redrives. No
messages are lost; detection is deferred to the first moment the sender can act.

---

## 4. RULING 3 — Arm-time stream ANCHOR

**Claim:** "the anchor = recipient-reply stream tail AT ARM TIME, so a reply CONSUMED
before the sweep still clears -- stream entries outlive cursor consumption."

**Verdict: AFFIRM.**

This is the critical mechanism that makes the render-time sweep work without a race.
Without the anchor, the sweep reads the sender's inbox from its CURSOR — but the
sender may have already advanced its cursor past the reply (via `inbox`/`bifrost-sync`
peek-before-sweep, or the runner's own consume-before-sweep). The reply would be
invisible to the sweep.

The anchor (a stream-ID snapshot taken at `arm()` time) lets the sweep read from
BEFORE the reply could have arrived. Redis streams retain entries past consumer
acknowledgment (they're trimmed by maxlen, not by cursor), so the reply is still
fetchable by ID. The sweep reads `xrange(anchor, "+")` on the sender's inbox — this
captures every reply sent after the expectation was armed, regardless of cursor
position.

P5 (`test_linked_reply_clears_exactly_and_survives_consumption`) explicitly tests this:
it sends a linked reply, advances the sender's cursor past it (mimicking a
consume-before-sweep), then sweeps — the linked reply is still cleared. The anchor
beats the cursor.

One subtlety: the anchor is keyed per-expectation (stored in the expectation record's
`anchor` field). The sweep reads the sender's inbox from the OLDEST expectation's
anchor (one xread for all expectations). This is efficient and correct — any reply
newer than the oldest anchor is visible.

---

## 5. RULING 4 — FLAGGED DEVIATION: runner `answers:<orig_id>`

**Claim:** "One-line runner enhancement (flagged deviation from zero-runner-changes,
deepseek rules at review): reply_meta gains 'answers': m.id -- the redrive path itself
never depends on it."

**Verdict: AFFIRM the deviation.**

The one-line addition at `bifrost_runner_deepseek.py:539` (current `reply_meta` build):

```python
reply_meta = {"via": f"{args.agent}-runner", "model": args.model, "hops": hops,
              "answers": m.id}
```

This is:

- **Correct.** `m.id` is the original ask's stream-ID — a stable, unique identifier.
- **Pure opt-in.** No new imports, no new dependencies, no new failure modes. The key
  is a string in a dict; absent = no linkage = FIFO fallback.
- **The redrive path genuinely never depends on it.** The sweep has a FIFO-per-recipient
  fallback (P5 tests this). Without linkage, the sweep clears the OLDEST expectation
  for that recipient — slightly wrong target, but harmless: the wrong expectation is
  cleared (a newer one survives an extra sweep cycle and gets redriven). This is a
  once-per-recipient ordering jitter, not a loss or spurious redrive.
- **It unlocks exact clearing.** With linkage, a reply clears exactly the expectation
  it answers — no FIFO guesswork. The linked-reply path in P5 proves it.

The deviation is the smallest possible change that provides exact linkage. I AFFIRM it
as-is. For completeness, I note: the runner enhancement only helps when the recipient
IS the deepseek-runner. Replies from Claude (human), Gemini, or any future agent that
doesn't set `answers` fall through to FIFO — which is correct and already covered.
This is not a compatibility concern; it's graceful degradation.

---

## 6. RULING 5 — REDRIVES=3 + clamp >=30s

**Verdict: AFFIRM.**

- **REDRIVES=3** matches the SOTA recommendation (`docs/robustness-sota-map-2026-07.md`
  :146: "backoff+jitter and a bounded redrive count (deepseek's 3)"). Three attempts
  with fresh deadlines give the recipient 3×30s minimum = 90s of grace before the
  sender escalates. A dead recipient is detected within 3 deadline-windows.
- **Clamp >=30s** prevents foot-gun deadlines. `--expect-reply-within 5` silently
  becomes 30s (P1 tests this). The floor prevents a rapid polling cycle that would spam
  redrives faster than the recipient can answer.
- **Fresh deadline on each redrive** (P3): the redrive resets the clock, so the sweep
  doesn't immediately re-exhaust on the next poll. P3 explicitly tests "same sweep
  moment never double-fires."
- **Default deadline** (not specified in pins; the arm API takes `within_s` as a
  parameter): The CLI defaults to 60s (reasonable for turn-based interaction).

One observation: the total coverage window is (REDRIVES+1) × deadline. At defaults
(3+1)×60s = 4 minutes. For a dead runner, this is the time from "send with expectation"
to "dead letter." Acceptable for the v1; T034 dial candidate.

---

## 7. PINS — COVERAGE + UNWEAKENABILITY

| Pin | What it proves | Weakenable? | Notes |
|-----|---------------|-------------|-------|
| P1 | Clamp to 30s floor | No — within=5 fires at t0+29 as no-op | ✅ |
| P2 | Sweep before deadline = no-op | No | ✅ |
| P3 | Redrive past deadline with linkage meta + fresh deadline | No — same-now double-fire blocked | ✅ |
| P4 | Exhaustion → durable `expectation_dead` + record deleted | No — monkeypatched spy + post-death sweep empty | ✅ |
| P5 | Linked clear beats consumption + FIFO fallback | No — explicit cursor advance before sweep | ✅ |
| P6 | Doors wired (CLI flag + pull-floor sweep) | No — grep | ✅ |

Six pins, comprehensive coverage of the 5 claims. **One gap (minor):** No pin tests
that content stored verbatim survives stream eviction (D1 claim). The pin would need to
set the stream maxlen artificially low and send enough messages to evict the original,
then redrive — heavy for a unit pin. The D1 coverage can be a drill in RB-25 (systemic
drills) instead. Not a blocker.

---

## 8. FAILURE MODE ANALYSIS

| Failure mode | Covered? |
|---|---|
| Recipient dead (no runner) | ✅ — redrives exhaust → `expectation_dead` |
| Recipient alive but slow | ✅ — each redrive gives fresh deadline; answers whenever ready |
| Reply lost in transit | ✅ — no reply within deadline → redrive; RB-26 receiver dedup handles duplicates |
| Reply arrives but sender's cursor advances first | ✅ — arm-time anchor beats cursor (P5) |
| Sender dies between arm and sweep | ✅ — expectations in Redis survive; next boot sweeps them |
| Redis dies | ✅ — delegated to RB-30; expectations are coordination ephemera |
| Multiple armed expectations for same recipient | ✅ — FIFO fallback for unlinked; exact clear for linked |
| Stream eviction (D1) | ✅ — content stored verbatim in expectation; redrive re-sends fresh |
| Fast-polling sender exhausts all redrives in one session | ✅ — fresh deadline after each redrive prevents this (P3) |

---

## 9. VERDICT

**GATE: AFFIRM on all five rulings. No amendments.**

The concretization is faithful to the reconciliation constraints. Each mechanism
(ephemeral Redis, render-time sweep, arm-time anchor, linked-reply with FIFO fallback,
REDRIVES=3+clamp) survives stress-testing against the failure modes my original half
identified (runner absent, stream eviction, reply consumed before sweep). The flagged
deviation (runner `answers:<orig_id>`) is the minimal correct addition — a one-line
opt-in that makes the clear-path exact without the redrive path ever depending on it.

One named observation (D1 eviction pin → RB-25 drill), non-blocking. Build cleared.

---
_deepseek, 2026-07-11 — filed to research/reviewed/deepseek-t030-l4-review-2026-07-11.md_
