# RESULT: point the fan at its own door -- ask-verb ergonomics

Status: current (2026-08-07)
Pre-registration: research/in-flight/prereg-ask-ergonomics-fan-2026-08-07.md (committed 86e4851,
before the fan ran). Slices: T225, T226.

## Headline

The fan's most valuable output was not an answer. It was the $0.065 receipt for a run whose
evidence pack was 25% delivered, in total silence. Three of four `--with` files were REFUSED
(outside the repo root), the caller was told nothing, and Lens 1 -- whose only file was one of
the three -- was billed for a question it was structurally unable to answer.

That defect was found by RUNNING the instrument, not by reading its output, which is the thing
the pre-registration said to expect and the reason it was written first.

## Predictions, scored

| | prediction | outcome |
|---|---|---|
| P1 | false-positive rate >= 50% | **REFUTED** -- ~0 of 4 claims were confabulated |
| P2 | diversity reads `distinct` | **REFUTED** -- read `unknown` (lexical 0.0606) |
| P3 | >= 1 reproducible accepted-but-inert defect | **CONFIRMED** -- and it opened a family of four |
| P4 | `--help` claims modal, worst reproduce-rate | **REFUTED** -- Lens 1 produced no claims at all |

**P1 is the interesting miss.** I predicted the helpers would hallucinate behaviour from a
783-line module. Instead, the two branches whose evidence was refused ABSTAINED and named the
file they lacked; Lens 5 said plainly "the evidence runs out before we can see how those doors
translate flags"; Lens 2 returned a clean negative trace and marked its own uncertainty.

The reason is mechanical, and it is the same mechanism T225 is about. `build_context` writes, in
band, `--- COULD NOT READ <path> (...) -- do not assume its contents ---`, and the helpers obeyed
it exactly. **The in-band refusal notice is an anti-confabulation device, and it is why the fan's
precision beat my prediction.** The defect was never that the door lies to the model. It is that
the same fact never reaches the human.

**P2 is a note, not an action.** Five genuinely different lenses scored 0.0606, between the
calibrated bands (DISTINCT_AT 0.05, COLLAPSE_AT 0.85), so the instrument returned `unknown`.
Reading them, they are distinct. The band may be tight for prose that shares domain vocabulary
("ask", "flag", "caller", "code path"). **The band was NOT retuned.** Retuning a threshold so
that my own fan scores better is the exact move the pre-registration's kill condition forbids,
and `attack_your_own_scoring_rule_before_the_players_do` says the same thing from the other side.
Recorded as one calibration control (5 lenses / 1 artifact / 0.0606) for whoever has enough
controls to move the band honestly.

## Every claim, dispositioned (A2)

| lens | claim | verdict |
|---|---|---|
| 1 cold-encounter | (none -- abstained, evidence refused) | correct abstention |
| 2 inertness | `ask_many` takes no `continue_on_cut`/`max_continuations`; "a parser exposing them would TypeError, not silently ignore" | **REPRODUCED as to the gap, REFUTED as to the conclusion** -- the CLI never passes them at all, so it is silent. Its reasoning was right; it lacked the CLI file, which I refused into the fan |
| 2 inertness | no other flag is accepted-then-unread in `ask.py` | **CONFIRMED** by inspection |
| 3 unactionable | `how_to_check` points at a CLI command a non-shell caller cannot run | **PLAUSIBLE, NOT FIXED** -- real for runners; T200 shipped MCP twins, so the pointer is reachable but still names one door. Filed, not closed |
| 3 unactionable | `CLOSED.DEAD` explains but prescribes no next move | **REPRODUCED** (reading) -- every other terminal state prescribes one. Low severity, filed |
| 4 cost | `continue_on_cut=False` is a stingy default that costs a whole retry | **REFUTED as a defect** -- see below. True of the library door, and deliberately so |
| 5 reach | cannot prove any CLI-only capability from the file given | correct abstention |

## The claim I got wrong, and how far it got

Lens 4 called the `False` library default a cost defect. The CLI defaults the same flag `True`.
Read together they looked like unreconciled drift across two doors of one verb, and I flipped the
library default to match.

**T204 had already ruled on it.** `test_t204_untruncate.test_continuation_is_opt_in`, one line of
docstring: *"Spending extra calls must be asked for."* A programmatic caller has no human watching
the spend line, so an automatic extra completion is money nobody agreed to. The two doors differ
on purpose: a door may choose a policy for its user, and the CLI does, with its argument written
in its own help.

The full suite caught it by name. Nothing shipped. But it is worth being exact about the failure
mode, because it is the one this whole exercise is supposed to guard against: **I ratified a
tool-less helper's hypothesis against a pinned decision I had not read.** The pre-registration
says the fan proposes and I ratify by execution -- I executed the code and not the record.

What landed instead is the invariant the drift-hunt was actually reaching for: the library never
continues unasked, the CLI passes its own choice EXPLICITLY to both paths it owns, and the reason
they differ now lives in the docstring where its absence caused two readers to call it a bug in
one day.

## What shipped

**T225** -- `unusable_evidence_notice` replaces `clipped_evidence_notice` at both CLI render
sites. Four classes, four next moves: CLIPPED (narrow the question), REFUSED (path is outside the
repo -- move it in), MISSING (fix the typo), SKIPPED (budget spent by earlier files -- reorder or
split). Paths are printed AS TYPED, not basenamed: caught by this slice's own pin, since
`no/such/file/t225.py` rendering as `t225.py` hides exactly the typo the caller must see.

**T226** -- `--bg` stopped assembling its child argv from four remembered flags. Measured before
the fix: `ask --bg --fan 5` ran ONE ask, silently, while `--bg`'s own help advertises "fan out
without drowning". `--system` and `--continuations` were dropped the same way. The hand list is
replaced by two total tables (`_BG_FORWARD` / `_BG_NOT_FORWARDED`, the latter carrying a reason
per exclusion) that a pin walks the parser against, so the next flag must be classified rather
than forgotten.

Fixing the forwarding exposed two more layers underneath it, both worse than what they hid:

  * the fan path returned WITHOUT writing the background record, so a completed, paid-for
    3-branch fan rendered as `ORPHANED -- "never wrote a result -- re-ask; nothing will arrive"`.
    A tool that tells you to buy again what you already own.
  * `summarize()` read `result["answer"]`, which only a single ask has, so a retrieved fan
    rendered DONE with an empty body -- three answers on disk, none shown.

Both closed in the same slice, because each was created by fixing the one above it.

## Method notes worth keeping

  * **Two of my own pins were defective, and both were caught by running them.** One located the
    `--no-continue` default by string index and matched `child.append("--no-continue")` 3400
    lines from the argparse site -- it PASSED, green, over a real difference. The other basenamed
    a path. A pin that can silently address the wrong site is not evidence.
  * **A replace-all edit matched 1 of 2 call sites** (four spaces of indentation apart) and the
    live re-run printed nothing, which read as "the fix does not work" rather than "the fix
    reached one door". Now pinned by count.
  * **Cost of the whole exercise: $0.069.** The fan was $0.065 of it, and its single most
    valuable product was its own receipt.

## Acceptance

  A1 >= 2 defects reproducing from a pasteable command, fixed RED-pin-first -- **met** (5 fixed
     across T225/T226; RED pins committed before implementation).
  A2 every claim dispositioned in writing, refutations kept -- **met** (table above).
  A3 per-branch yield reported including zeros -- **met** (Lenses 1 and 5 yielded no claims, and
     Lens 1's silence was the finding).

## Still open, filed not closed

  * `CLOSED.DEAD` prescribes no next move where every sibling state does (Lens 3).
  * `how_to_check` names one door (Lens 3); the MCP twin exists, the pointer does not say so.
  * The `distinct` band may be tight for prose. One control recorded; do not move it on one.
