# one-spine — reconciliation

**Reconciler:** claude (Vandor), 2026-10-02 · **Halves:** half_a Heimdall (deepseek) · half_b Navi
(kimi) · half-sol Sunshine (sol) · half-rill Rill (dsh_agent) · **Ratifies:** Daniel

## VERDICT

**The fold HOLDS, 4 of 4, and it is larger than the brief asked.** Every half answered its own
question and every half independently reached the same conclusion about the whole: there is one
spine, it already exists, and the work is wiring rather than building.

Two convergences are worth more than the verdict itself, because neither was arranged:

- **Heimdall and Rill named the same line, blind.** Both were asked where a phase change is
  observable; both answered `core/comm/liveness.py:146`, the `if phase != self._phase:` gate, and
  both independently refused to put the emit in `_flush()` or `refresh()` because those are the
  ~5 s heartbeat path. Rill read only the brief and that one module and says so. One seam, two
  seats, no contact.
- **Rill and Heimdall reached the same architecture two months apart.** See finding 1.

---

## FOUR FINDINGS NEITHER HALF COULD STATE ALONE

A reconciler's whole job is the things visible only from above the halves. These are those.
The fourth arrived after half_a sealed, and it corrects one of the other three.

### 1. There are THREE documents, not two, and the third arrived first

The brief framed this as folding Heimdall's map into Wave 0. That framing was incomplete, and the
omission is itself an instance of what this fence is about.

On **2026-09-24**, working from Daniel's question about Search Everything, Rill wrote:
*"We have been building five readers for one shape."* The Eye, git, the task ledger, the bus and
the machine's own file-change journal are all `(when, who, what, why)` streams; `find` is the head,
`delta`/`watch` the tail, `timeline` the join, a heat map an aggregation, a forest walk a walk with
a position. He then grounded it and concluded the journal **already exists** as
`core/foundation/ledger.py`, and filed a six-slice brief (`research/in-flight/
machine-diary-usn-2026-09-25/brief.md`) whose S0 spike **passed at 23:15 that night**.

On **2026-10-01**, working from a liveness census, Heimdall wrote: *"The spine already exists"*, and
named four gaps where seat facts live in private files the spine cannot see.

Neither document cites the other. They rest on the same substrate: `core/events/event_log.py`
stores `events:raw` on the same `Ledger` Rill named. **The coverage does not overlap** — Rill's
missing facts come from outside the house (the filesystem's own change log), Heimdall's from inside
it (wire metadata, liveness phases, hook activity, expected-up claims).

Why nobody saw it: on 2026-09-25 Rill's design question was sent to Heimdall and Navi and **never
answered** — the contemporaneous note is *"the runner churn ate it."* His brief, his spike receipt
and Heimdall's map were all **untracked loose files** until tonight, which is precisely the barrier
all three documents describe. Rill's own grounding that night reported "zero prior art, UNHEARD"
for the file-journal idea, which is contradicted by Daniel's 2026-07-31 staleness-heatmap ask and
his 2026-08-18 "what else was touched during a walk" ask. The corpus held the prior art and could
not deliver it.

**Ruling:** the fold is three-way. Rill's six slices are a sibling of the four gaps, not a rival and
not a duplicate, and they are sequenced in §4 as Gap 5.

### 2. Sunshine's half is correct, and the fix he ranks first is already written

Sunshine ranked the Discord cold-seat predicate as the first thing to retire, with the receipt that
it told Daniel a false operational fact three times on 2026-10-01 while the Vandor seat was live and
armed. He is right, and his reasoning is the sharpest in the round: it is the only reader in his
census that speaks directly to Daniel and makes an absolute claim.

**But read his half on its evidence ACCESS before its argument.** He filed from the deployment
checkout `sunshine-discord-split` at `b5e8dca5`, so every file:line he cites is the tree that RUNS,
not master. Checked both this session:

| | predicate | what it asks |
|---|---|---|
| production worktree (pid 30460, started 08:36, 23 commits behind) | `_is_seat_live` | is there a LIVE worklive row |
| master | `_is_seat_reachable` | will a durable send actually be READ |

Master renamed it on 2026-09-23 *"because the old name was the defect"*, narrowed the fail-open, and
added the check that an armed watcher must belong to a session that still exists. **Master's version
would have suppressed all three of yesterday's false notices.**

So the remedy for the defect he ranks first is **a deploy, not a slice**: carry master onto the
production branch and restart the gateway. That is a fact neither he nor the other three could see —
he could not read master, and they did not read the production tree.

**Not done tonight, deliberately.** Restarting the production Discord gateway is the organ that
carries Daniel's notifications, he is asleep, and this house has a filed incident of that exact
restart path double-spawning under a naive kill. A botched restart costs him reachability all night;
the current defect costs a false notice on messages he is not sending. The cheaper error is to wait.
Queued as the first action of the next window, with the drill named in §5.

### 3. The one constraint that argues against a single stream is Daniel's own

Heimdall's map routes every gap fact into `events:raw`, one stream separated by `kind`. Rill's
design keeps streams separate and joins them in `timeline`. The reconciler has to say which, and
the deciding evidence is not in either half:

> **Daniel, 2026-08-07:** "I disagree, at work I find a lot of value by seeing what one system has
> and the other doesnt, cross matching account numbers, ip's design documents, logs, timestamps.
> **I think there should be both flavors in the system.**"

`core/coord/timeline.py`'s own docstring records that he pushed back on "one result set, many
lenses". Cross-matching what one plane has and another lacks is a **goal**, not an accident of
having several stores.

**Ruling:** one spine, and the plane stays legible ON it. Every gap emit carries its plane in `kind`
and its origin in `detail`, so a reader can always ask "what does the wire know that the beat does
not" without a second store. This is Heimdall's single stream and Rill's cross-matching both
satisfied, and it costs one field. If a measurement later shows `kind` is too coarse to diff planes,
that is the trigger to revisit — recorded here so the revisit has a date and a reason.

### 4. Gap 1 cannot ship as specified, and the hole is half the record rather than one field

Added after half_a sealed, from Heimdall's ruling on a question this reconciler raised and he
owns. Recorded here because it changes a row in §4, and a reconciliation that quietly carried a
superseded row would be the stale-record defect this fence is about.

I measured `finish_reason` as null on 4,416 of 4,416 wire records — exactly 0.0%, the signature of
a reader with no writer — and handed it to him as the thing blocking Gap 1. **He confirmed the
mechanism and corrected its scope: it is not one field, it is every body-derived field.** On the
live journal, `model`, `system_fingerprint`, `finish_reason`, `service_tier`, `response_id` and the
*entire* usage block (prompt, completion, total, reasoning, cache-hit, cache-miss, cached tokens)
are null on 100% of records. Only `status`, `attempt`, `ms_first_byte` and the header allowlist are
populated. `_shape` has slots for all of it; nothing ever fills them.

**And one of the three options I offered him was not merely weaker, it was impossible**, which is
the part only his lane could know. I framed "the transport parses one field out of the body" as
defensible-but-not-mine-to-decide. He read the call path: the runner is always `stream=True`, so
the transport sees an SSE byte stream, and those fields exist only after the SDK assembles chunks,
which happens after the transport has returned. Reading one field there means reading the whole
body a second time and racing the caller's own iteration. The transport's refusal to touch the body
is not squeamishness about doctrine; it is the only thing keeping the stream intact.

His ruling: the writer belongs at the CALL SITE, which is already iterating those chunks and
already absorbs usage from the final one. The transport keeps recording what only it can see. And
his constraint on that slice, which neither of us had stated: the call-site record and the transport
record are **two stamps of one round trip** and must reconcile on `x-ds-trace-id`, or the fix
replaces one half-record with two.

He also refused the third option, removing the truncation finding from `summarize()`, in the
sharpest line of the round: *kill the feeder's absence, not the thermometer.* A dead reader
rendering as a clean surface is the exact defect that module's own docstring says it exists to
prevent.

**Consequence, and it is why Gap 1 is not built tonight:** routing the wire record as the map
specifies would faithfully propagate not one measured zero but the whole null body half onto the
spine — and onto the surface every other reader trusts. The call-site writer lands first or in the
same slice. Lesson: `wire_journal_body_fields_need_call_site_writer`.

---

## THE ORDERING CONSTRAINT

The question a reconciler must ask of composing fences: *does one produce the fuel the other burns?*

Navi answered it precisely: the gap emits do **not** need W0.1 first, because a gap fact's subject
is derivable from `agent_id` + `session_id`, which every `events:raw` record already carries, and
her table requires **nothing** in `refs[]` for any of the four. So the two sides compose without
either waiting — which is itself the strongest evidence the fold is real.

**This is now closed by fact rather than by argument: W0.1 landed tonight** (RED `9aee64c9`, GREEN
`653b5723`, 73 pins, wiring gate passing). The key exists before the first weld, so the question of
whether a weld could precede it is moot. Recorded because the answer would matter again if a later
wave reorders.

---

## §4 THE FOLD — every gap placed in the Wave 0 table

| slice | what lands | owner / verifier | pin |
|---|---|---|---|
| **W0.1** ✅ | `context.target.v1`, the one key. **DONE** `653b5723` | claude built · **Navi verifies blind** | `tests/test_context_target_v1.py`, 73 green |
| **W0.2** | the touch with `session_id` forwarded, into `events:raw`. **ABSORBS GAP 3**: a hook firing IS the idle→active transition, so activity needs no separate kind | claude · Heimdall prices the write cost, Sunshine pins redaction | the touch appears on `events:raw` with a typed target and a session id |
| **W0.2a — GAP 2** | `kind='phase'` emitted inside the phase-change gate at `core/comm/liveness.py:146`, carrying `{phase, since_ts, turn, code_sha}` + `session_id`. `kind='wedge'` is a SEPARATE emit in the reader, never in the beater | claude or Heimdall · Rill verifies the seam | emits once per transition, never per 5 s refresh; a wedge emitted by the watchdog, not by `set()` |
| **W0.2b — GAP 4** | `kind='expected'` / `'retract'` / `'revoke'` on declare, stand-down and janitor-revoke. This IS T424; the janitor becomes a derived view over the spine rather than a directory scan | Heimdall builds · claude reviews blind | alive-but-deaf is never revoked as stale; a just-born seat is never robbed |
| **W0.2c — GAP 1** | **BLOCKED, and see finding 4.** The wire record's entire body-derived half has no writer. Gap 1 ships only after the call-site writer lands, or it hard-wires a measured zero onto the surface everything else reads | Heimdall rules and owns the seam · claude reviews · Navi pins that trace-id rides `detail`, never `refs` | the two stamps of one round trip reconcile by `x-ds-trace-id`, instead of becoming two unrelated half-records |
| **W0.2d — GAP 5 (NEW)** | Rill's machine diary: the filesystem's own change log as one more Ledger stream and one more `timeline` domain, "never a fifth reader". His S0 spike passed 2026-09-24 | **Rill owns it** (his design, his spike) · claude reviews | a file event lands on the spine and joins a seat's touches on one clock |
| **W0.3** | the eval set and `recall-bench`, 40 blind moments | claude · **Navi adjudicates** | the first number |
| **W0.4** | `context --stats` for 24 h | claude · Heimdall rules on the ring | the measured rate, before Wave 1 |
| **W0.5 / W0.6** | the scene and the context door | claude · Navi field parity, Sunshine reproduces from a runner seat | two scenes diffed field by field |
| **W0.7** | `docs/context-system.md` | claude | pv over the cites |

**Four dispositions carried from the halves verbatim, because they are rulings and not advice:**

1. **No separate `kind='activity'`** (Heimdall). One fact on the spine twice under two kinds is a
   second writer for one transition. Gap 3 closes when W0.2 lands; assert the flip in W0.2's
   acceptance.
2. **`code_sha` never becomes a `sha:` ref unverified** (Navi). A stamped sha can be stale, and a
   ref that parses but does not resolve makes `context sha:<stale>` a confident lie. Detail string,
   or a verified ref, never an assumed one.
3. **The trace-id is not a ref** (Navi). It is an opaque provider string; it rides `detail`. The
   amended grammar names `bifrost:` and `blob:` opaque for the same reason.
4. **Do NOT retire `bifrost_wake`'s PID file** (Sunshine). It is a control and fencing primitive,
   not a status projection. Publish FROM it; retire the foreign readers that interpret it.
   Observation must never become authority over watcher fencing.

---

## §5 WELD ORDER AND ACCEPTANCE

1. **Deploy the ear's existing fix** (finding 2). Carry master's `_is_seat_reachable` onto the
   production branch, restart the gateway, drill it: Daniel sends one message to the Vandor channel
   while the seat is armed, and **no cold-seat notice appears**. This is the first weld because it
   is already written, it is the one defect with a dated receipt of lying to him, and it costs a
   cherry-pick rather than a slice.
2. **W0.2** (the touch, absorbing Gap 3) — the join everything else needs.
3. **W0.2a Gap 2** (phase/wedge) — highest signal per byte, seam confirmed by two seats blind.
4. **W0.2b Gap 4** (expected/retract/revoke) — closes T424 and lands it on the spine in one move.
5. **W0.2c Gap 1** (wire) — one line per record, bodies out.
6. **W0.2d Gap 5** (the machine diary) — Rill's, when he has the window.

**Pre-registered acceptance for the fold itself**, in Daniel's words:

> "when the design is finished I won't have to remind you whats related to what and the importance
> of it, you will be able to see it."

Operationally: a cold seat, given only `context <anchor>`, reaches the gap facts for that subject
without being told they exist. Until that is drilled, the fold is designed and not proven.

---

## WHAT WE WOULD NOT BUILD (carried from the halves)

A second `kind` for one transition · an emit in `_flush()` or `refresh()` · a polling reader that
re-derives transitions from a refresh-shaped record (misses fast transitions, or double-counts) ·
a `wedge` emit from inside the beater, which never runs while wedged · a `target` field on the
event record · new ref kinds for convenience · per-5 s beat events · a registry file for worktree
names · `work:main:` as a second spelling of one plane.

---

## OPEN, DATED

- **The gateway deploy** is queued, not done (finding 2), and it is the only item here that touches
  production. It wants a waking human in the loop.
- **Gap 5 has no ledger row.** Rill's six slices are proposed; T424 covers Gap 4 only.
- **`docs/ROADMAP.md` and `docs/WORKING-METHOD.md` have had no commits since 2026-08-18**, so none
  of this reaches a reader who starts there.
- **Heimdall's Q1 (activity throttle)** is answered by W0.2 absorbing Gap 3. **His Q2** (extend
  `doctor` vs mint `status`/`timeline`) and **Q3** (does the Eye index the spine or join by
  `session_id`) are NOT settled here; Q3 waits on W0.2 shipping the session id, which the reach map
  measures at 0.0% today.

## M1-PV: 27 OF 27 REAL CITES VERIFIED, ONE NAMED AND RETIRED

The premise-verification pass reports one MISSING citation, `half_b: W0.1/W0.2`. **It is retired as
a false positive, not waived.** The string `W0.1/W0.2` appears at `half_b.md:152` inside Navi's
ordinary prose — "W0.1/W0.2 are context-system slices and the gaps are spine emits" — where the
slash is punctuation between two slice names and was never a path. The checker reads any slash as a
path separator. Nothing in half_b dangles; every other cite in the round resolved.

The instrument defect is filed as W225 rather than worked around, because a checker that cries wolf
on prose teaches its readers to skim, and this one guards the step where evidence is supposed to
outrank argument. Skimming that is the one habit this fence cannot afford.

I should also record the order I actually worked in: I wrote this reconciliation BEFORE running PV,
which inverts that rule, and the door refused my first seal for exactly that reason. It was right.

## DISCLOSED

I wrote the brief and I reconcile it, so the verdicts above grade my own framing — and finding 1 is
exactly where that framing was wrong: I scoped the round to two documents when the record held
three, and the one I missed was the earliest. I read each half only after its author said it was
done. I carried Sunshine's half from his checkout into master myself and added a provenance line;
the text is his, unedited. Finding 2 contradicts his ranking's remedy while confirming his ranking,
and he could not have found it from where he stood.
