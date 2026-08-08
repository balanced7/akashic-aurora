# PRE-REGISTRATION: the recall-trigger fan, 2026-08-08

Status: current | Type: pre-registration | Author: claude#f9d12d26

Committed BEFORE the fan runs and before any answer is read. Method baseline M3: pins and
predictions land first, or git holds no evidence the acceptance came before the result. My
scorecard is at 50% clean on this, which is why it is being written rather than remembered.

Daniil, 2026-08-08, on the frame: *"I don't know if I'm making sense... I don't know what the
right shape but I believe iteration will help us get there."* This run is iteration 1. It is
scoped to UNDERSTAND, not to fix, and nothing here proposes a build.

## The fan

Five branches, five DIFFERENT OUTPUT TYPES, because a transect whose branches all return
"problems found" costs money and changes nothing -- the reader has to assemble it, and assembly
at the junction is where fan cost actually lives.

| branch | returns | evidence |
|---|---|---|
| MECHANISM | a decision path, enumerated | at_action.py + the hook |
| AUTOPSY | candidate trigger SIGNALS, ranked by cases caught | the miss dossier only |
| ANALOGY | deployed designs + their documented failures | **none, deliberately** |
| ADVERSARY | a claim killed or surviving | the miss dossier only |
| CONTROL | an inventory of knobs, tunable vs hardcoded | at_action.py |

ANALOGY and ADVERSARY get NO source on purpose. A branch that can read the implementation stops
answering from outside it, and outside is the whole value of those two positions. This is the
first run where that is enforceable rather than merely requested (T244/T246).

## Predictions

**P1.** MECHANISM will confirm that path and command are the ONLY signals reaching the ranking
-- no tool name, no history, no session state. Stated as a prediction rather than a fact because
I read the call site, not the whole 1665-line module.

**P2.** AUTOPSY will find that at least one of the four misses is UNREACHABLE from any
observable signal available at that moment. I expect it to be M2 (the RED pin that failed for
the wrong reason), because the distinguishing fact was the CONTENT of a file being written, and
nothing in a path or command carries it.

**P3.** ANALOGY will return alert fatigue from clinical decision support with real numbers, and
that will turn out to be the closest analogue -- a high-value channel destroyed by low-precision
firing, which is the exact failure mode of a 5.2% funnel. **I expect this to be the most useful
branch**, which is unusual: analogy is normally the highest-variance and most-rejected view.

**P4.** CONTROL will find that thresholds exist and are tunable, but that "let a lesson declare
the situations it applies to" is UNEXPRESSIBLE -- there is a trigger-clause parser
(`_parse_trigger`), so the data may be half-present while the matching is not.

**P5 -- THE ONE I EXPECT TO DIE.** I predict ADVERSARY fails to land a serious blow, and that
its best objection is the after-the-fact selection of the misses. I am recording this precisely
because three of four headline predictions died on 2026-08-07 and each corpse was worth more
than the prediction. If ADVERSARY lands something real -- most likely that a smarter trigger
gets trusted more and therefore fails harder -- that changes what is worth building, and I
should not be able to quietly discover I meant that all along.

## Stated blindness, before any result

- The miss dossier is **n=4, one seat, one day**, and every case was chosen by me AFTER I knew
  the answer. That is the weakest possible sampling and the ADVERSARY branch is explicitly
  pointed at it.
- The misses I did not notice are invisible by construction and are probably the larger set.
- `helped 61` says the system does work sometimes. Nothing here measures the successes, so any
  conclusion drawn from this fan is about the misses only.
- One counter-example is already on record: while preparing this fan the hook surfaced
  `preflight_the_ask_before_you_spend_the_fan` at exactly the right moment. **The trigger is not
  uniformly broken**, and a fix built as though it were would be built on a false premise.
