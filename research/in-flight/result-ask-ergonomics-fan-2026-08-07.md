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
it exactly. ~~**The in-band refusal notice is an anti-confabulation device, and it is why the
fan's precision beat my prediction.**~~ The defect was never that the door lies to the model. It
is that the same fact never reaches the human.

> **CORRECTION, same day, struck above.** That sentence was a causal claim from two observations
> about a mechanism I had just shipped, filed in the document where I was scoring my own honesty.
> Four screens away the friction reader says `presence_effect is a CORRELATION and licenses no
> causal claim`. I had the disease I was diagnosing. Ablation below; it cost $0.03 and refutes me.

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

## ABLATION: what actually makes the helpers abstain? (added same day)

Written because the struck sentence above was unearned, and because noticing WHY it was unearned
found a confound: `DEFAULT_SYSTEM` already ends *"If you cannot answer from what you were given,
say exactly what is missing -- a stated gap is worth more than a confident guess."* Two abstention
instructions were in play and I credited the one whose slice I was writing.

Target: `QUORUM_FLOOR` in `core/comm/quorum_gate.py`. Neither exists, so any specific value is
invented by construction -- no lucky guesses to argue about.

| condition | n | confabulated |
|---|---|---|
| 2x2: notice x gap-instruction, BLATANT absence (wrong file entirely) | 16 | **0** |
| notice x gap-instruction, TEMPTING (file present, on-topic, truncated before the answer) | 8 | **0** |
| BARE: no header, no notice, no gap instruction, plain assistant persona | 5 | **1** |
| HEADER ONLY: exactly one factor added back to BARE | 5 | **0** |

**The refusal notice is not what produced the abstentions.** Removing it AND the system prompt's
gap sentence changed nothing across 24 branches at two difficulty levels. The struck claim is
refuted, not merely unsupported.

**The load-bearing nudge is the one nobody was talking about**: `build_context`'s header --
*"CITE `filename:line` for any claim about this code; if you are inferring rather than reading,
say so explicitly."* It is the only factor whose removal produced the class
(`"The default value of QUORUM_FLOOR is 3"`, flat and unhedged), and adding it back as a
single-factor change restored 5/5 abstention -- with every answer now citing `quorum_gate.py:4-6`,
which is the behaviour the header asks for. That is a mechanism, not just a correlation: the
header makes the answer's FORM require a line reference, and you cannot cite a line for a constant
that is not there.

**What this does NOT establish.** 1 event in 5 is not a rate; the effect is qualitative (the class
appears / does not appear), and the size is unmeasured. The BARE arm also changed the system
persona, which is why the HEADER-ONLY arm exists -- but one single-factor arm at n=5 is suggestive,
not settled. Replication belongs to whoever needs to depend on it.

**Why the original P1 refutation actually happened**, most likely: I forecast >=50% confabulation
from a general prior about hallucination, and that prior does not transfer to *"is symbol X in the
text I was handed?"* -- a locally checkable question about evidence the helper can see. Cheaper and
less flattering than "my notice saved it."

**T225 is unaffected and still right.** The notice's job was never to make the helper abstain --
the helper had other reasons. Its job is to tell the CALLER, and that half was genuinely broken,
measured at 0 bytes of stderr and $0.065. What changed is my story about the helper half, which I
had no business asserting.

## Still open, filed not closed

  * `CLOSED.DEAD` prescribes no next move where every sibling state does (Lens 3).
  * `how_to_check` names one door (Lens 3); the MCP twin exists, the pointer does not say so.
  * The `distinct` band may be tight for prose. One control recorded; do not move it on one.
