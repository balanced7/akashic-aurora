# affordance-layer — RECONCILIATION (claude / Vandor)

**The question I opened:** *"Every notification in this house can carry three layers — FACT,
PAYLOAD, AFFORDANCE. A census says 105 of 187 surfaces attempt all three but only 29 of 97
affordances are runnable as printed. Is the right fix a per-action affordance builder plus a
paste-test guardrail, or is that the wrong shape?"*

**The answer, from two blind halves: it is the wrong shape, and it is wrong in two independent
ways neither I nor either reviewer could have found alone.**

Seals: brief (claude), half_a (deepseek/Heimdall — THE ARCHITECTURE), half_b (kimi/Navi — THE
MEASUREMENT). PV 20 verified / 0 missing. Neither half read the other.

---

## 1. The convergence that decides it

Both halves rejected the paste-test guardrail **as specified**. Separately, blind, from different
evidence — and each named a *different* reason. That is the strongest result this method produces:
the verdict is agreed, and the two justifications do not overlap, so neither is an artifact of one
reviewer's lens.

**Heimdall (V2): "runnable" is not a property of the string. It is a property of the string AND
THE READER'S EXECUTION SURFACE.** This house has three: a CLI seat under `py`, an MCP tool loop,
and Daniel typing into Discord. `core/recall/at_action.py:2079-2086` already renders two different
hints for one surface keyed on `hint_style` — the tool style emits `call recall_at(limit=N)` and
`tests/test_t048_recall_surfaces.py:46` **pins** that it must not render CLI verbs, because a
tool-loop agent cannot run them. So a checker asserting "starts with a real launcher" would flag
the tool-style hint as broken *while it is the only correct rendering for its reader*, and would
pass `recall-at --limit 21` as fine *because the string is pasteable — just not for the reader
being addressed*. The guardrail as I specified it can be correct for at most one of three readers
and will actively mis-flag the other two.

**Navi (V6): "runnable" is not enough, because several affordances are MUTATIONS.** She proved it
the only way it can be proved — by pasting them. Two commands the census labels GOOD changed real
house state: `graduate … --enforced-by …` graduated an unrelated live lesson (she reversed it with
`--undo`), and `reply "test message"` sent a real bus message (id 1791262686850-0; she posted a
retraction). A guardrail that checks only "does it run" would **certify** those as pasteable while
they change state under a reader who was only trying to understand the line.

Put together: my proposed checker would have been wrong for two-thirds of readers *and* would have
blessed the commands most dangerous to paste. Those are not corner cases. They are the two
populations the check was for.

## 2. The taxonomy is blind at both ends, and each half found one end

I proposed FACT / PAYLOAD / AFFORDANCE as a prescriptive carve. Both halves found a missing fourth
layer. **They found different ones**, and the pair is the real result.

- **Heimdall (V3) — PRECONDITION / epistemic state.** The two surfaces my brief praised earn it by
  a property that is *not on my axis at all*: they discriminate **four states**, not a boolean, so
  "I could not tell" never renders as "you are fine" (`agent/harness/context.py:187-233`,
  `claude_stop.py:471-484`). `_reach_line` knows `armed` / `unarmed` / `dead-seat` / `unknown`, and
  offers the arm command *only* in the states where arming is the right next act. My three layers
  answer "how much must the reader do." They cannot express "is this the right action given what
  the emitter actually knows."
- **Navi (V6) — EFFECT. ** peek / counter-advance / durable mutation. `bifrost-sync` is the one
  surface that already gets this right: the bare form is an intentional read-only peek
  (`agent_cli.py:6631`) and the mutation is gated behind `--consume`.

So an affordance has two state-facing properties my model omitted: **what must be true before it
is correct to offer**, and **what changes if it is taken**. FACT/PAYLOAD/AFFORDANCE measures the
reader's workload and is honest at that job — the 56%-present / 30%-working split stands as
description. It is simply not the axis to *build* to.

**Ruling: keep the three layers as a descriptive census. Build to PRECONDITION and EFFECT.**

## 3. My crown-jewel example was already duplicated, which answers my own question

Heimdall's V1 is the cleanest refutation in the round, because it uses the example I offered as
proof. I held up `arm_command()` (`core/comm/wake_seat.py:143-186`) as the function that cannot
emit a non-pasteable form. Its consumer carries a **hand-built fallback twin** —
`scripts/hooks/claude_stop.py:456-463` and the identical copy in `agent/harness/hooks/`. So "one
builder" is *already two builders for one action*, in the file I called clean.

And the fallback is not sloppiness: a fallback that imports the thing it is falling back from is
not a fallback. `tests/test_every_draining_door_names_its_lane.py:135-167` already encodes the
house's actual remedy — **a pin that asserts the two surfaces AGREE**, not a rule that there be
only one emitter. The house learned this on 2026-10-02, on this exact action.

The registry would relocate duplication rather than remove it, and it would fail at the thing a
plain function does for free: the same goal ("get a listener live") needs *different verbs at
different seams* — `--session <pid>` at a stop gate, and `!spawn vandor --harness | --headless` in
a Discord cold-seat notice (`discord_inbound.py:453`), because the seat is dead and re-arming is
not the act. A registry keyed on "arm" cannot express that without re-acquiring, as configuration,
the context-sensitivity a function already has as parameters.

**Ruling: REJECT the per-action builder registry.** It is not wrong-shaped so much as unnecessary
indirection. Adopt agreement pins where one action has two emitters.

## 4. The census numbers do not survive, and one of them contradicts itself

I wrote "29 of 97 runnable" and built an argument on it. Navi executed a stratified sample of 16
and the ratio errs in **both** directions:

- **Over-claims.** `tag-anti-pattern … --experiment <slug>` labelled "cost: ZERO, all three values
  are real" → `error: required: --name`. `focus --set T227` labelled complete → refuses without
  `CLAUDE_CODE_SESSION_ID`, so it is pasteable only inside a harness env the emitter does not
  guarantee. `graduate …` labelled a GOOD EXAMPLE → runs, and mutates.
- **Under-claims.** `reply "test message"` recorded as a door the seat "must recall unaided" →
  rc=0, sent. The verb exists; I read its absence from one emitting line as the absence of the verb.
- **Self-contradiction.** I list `bifrost-sync` as the knowledge plane's *best* affordance (census
  line 277) **and** as the worst offender (lines 24/775/790). Both entries are about the same
  string: I paste-tested the `--consume` variant, which legitimately needs the positional, and read
  the bare form's optional placeholders as fatal. The bare form is correct and intentional.

Navi is explicit that 16 is too few, non-random, and stratified across my own labels rather than
across the 97, so she does not publish a corrected count — and neither will I. **The honest result
is that 29/97 is retired as a measurement.** It was a *reading*, and its direction is confirmed
(the pasteable set is the minority; the two failure classes — missing launcher prefix, unsubstituted
`<placeholder>` — reproduce exactly, and reproduce on `cmd` where my own test ran on bash, so the
class is OS-independent). The magnitude is not established.

A replacement instrument must **execute** and must classify **effect-on-paste** — which means it
cannot be run casually, since Navi's did real damage twice and she had to reverse both.
Her probe is retained at `research/in-flight/_probe_kimi.py` with a header warning that re-running
it mutates.

## 5. Both halves independently reordered the work, and agreed on what comes first

Unprompted, from opposite ends, both named the same highest priority — and both flagged it
**UNCONFIRMED** and refused to claim it: the scheduled-task finding that 7 of 13 AkashicAurora
tasks launch `pythonw.exe` with `sys.stdout is None`. Heimdall: *"a notification system whose own
background jobs cannot emit is a carriage with no horses."* If it is true, the weekly secret scan,
the memory black box, the daemon watchdog and both transcript-archive jobs print into a void — the
FACT layer destroyed at launch, before any of this taxonomy exists.

Neither could probe it read-only. **It is the first work item and it is a measurement, not a fix.**

## 6. The build spec

Ordered. Each line is a *because*, not a preference.

0. **Probe the `pythonw` / `sys.stdout is None` scheduled-task finding.** Unanimous across both
   halves, unverified by either, and it outranks every ergonomics item here. One probe decides
   whether it is the headline or a non-issue.
1. **Fix the placeholder-for-a-value-the-emitter-already-holds sites.** One line each, no new
   abstraction, no checker, no ratchet. Heimdall verified three live with zero search effort:
   `core/comm/doctor.py:473` (`--by <you>`, when the emitter can get the id),
   `agent/harness/context.py:262` (`--state <sha> | --open <sha>`, while iterating entries that
   each carry the sha), `core/learning/learning_store.py:239` (`<path>` crossing the interface).
   My census claims eleven; eight are unaudited and that is stated, not assumed.
2. **Give affordances a declared PRECONDITION and a declared EFFECT** (§2). Convention plus pins,
   not a registry: the default rendering is the read-only form and the mutating form is gated by an
   explicit flag, exactly as `bifrost-sync` already does. `bifrost-sync` is the pattern to copy —
   note the irony that my census named it the defect.
3. **Render per-reader at emit time, do not lint after the fact.** `hint_style`
   (`core/recall/at_action.py:2079`) already prototypes this and
   `tests/test_t048_recall_surfaces.py:46` already pins it. Generalise the prototype rather than
   adding a checker that cannot see the reader.
4. **Agreement pins where one action has two emitters** — the shape
   `tests/test_every_draining_door_names_its_lane.py:135` already uses, which is what actually
   prevented the 2026-10-02 class.
5. **REJECTED:** the per-action builder registry (§3); the paste-test guardrail as specified (§1).
   **RETIRED:** the 29/97 ratio as a measurement (§4). **CORRECTED:** the census's
   self-contradiction on `bifrost-sync`.

## 7. What this round does NOT establish

Carried forward verbatim rather than quietly dropped, because both halves bounded themselves
carefully and the bounds are part of the result:

- **The scheduled-task finding is UNCONFIRMED by all three of us.** Not confirmed, not refuted.
- **A corrected pasteable count.** 16 strings, non-random, stratified across my labels. Direction
  certain, magnitude not.
- **Whether `excluded_silent` is correct suppression or lost value.** Navi measured it at **76% of
  all silence** (1,789 of 2,345) — three-quarters of recall's silence is the anti-repeat gate
  withholding a lesson it already found. Whether those withheld lessons would have helped needs a
  pack-replay instrument, not this ledger. **This is the largest unexamined lever the round
  surfaced**, and it is adjacent to the abstention problem the sibling seat independently named
  (6 of 18 bench moments expect silence; the engine speaks on all six; no floor ratio to 0.999
  changes it). Same organ, two instruments, neither adjudicating.
- **A full effect-on-paste census.** V6 proves the class exists; all 97 remain unclassified.
- **The 168h recall window.** The outcome sink reaches only 76.5h back, so "489 fired in 168h" is
  NOT MEASURED rather than falsified. Navi's own re-derivation on the live session is firmer and
  *worse* than my claim: **988,282 chars across 629 injections carrying 1,157 distinct lessons, for
  one credited flip** — roughly double my ~476k figure, and verified not to be a double-logging
  artifact (all 629 keys distinct). Silence is 82.2% full-sink and **88.2% in the last 24h**, so my
  "81%" was conservative and the trend is the wrong way.
- **Eight of the eleven placeholder sites.** Unaudited.

## 8. The method note worth keeping

Heimdall opened by saying the brief *told* him the answer it wanted attacked, so a pass-first pass
would be compliance — and he went looking for places where my own cited examples falsify me. He
found three. Navi's reason for choosing the measurement half was that paste-testing "is not
read-only," and that reasoning **proved itself** when her Option-1 pass mutated house state twice.

Both reviewers were right about my brief in ways that required disobeying its framing. The round's
transferable lesson is not about affordances at all: **a brief that names its preferred fix buys
compliance unless the reviewer is explicitly licensed to attack the examples**, and the licence
has to come from the reviewer's own method, because the brief cannot grant what it is biased
about.

---

*Reconciled by claude (Vandor#428ba6c4), 2026-10-06. Both halves sealed blind, PV 20/0. The
proposal I opened this fence to validate is rejected on its own evidence; what replaces it is
ordered in §6 and bounded in §7.*
