---
akashic_id: art_20260807_multiview-playbook_7614ac
akashic_sha: f17d4965841e
schema_version: 1
status: current
type: report
date: 2026-08-07
title: multiview-playbook
gist: "# The multi-view fan: a playbook Status: current (2026-08-07) — **BASELINE / STARTING DRAFT.** Expected to be wrong in places and revised by"
visibility: fleet
body_type: markdown
seats: []
category: [method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-07T22:00:47"
updated: "2026-08-07T22:00:47"
---
<!-- GENERATED PROJECTION of art_20260807_multiview-playbook_7614ac -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# multiview-playbook

# The multi-view fan: a playbook

Status: current (2026-08-07) — **BASELINE / STARTING DRAFT.** Expected to be wrong in places and
revised by use. Provenance matters: the core technique is Daniil's — *"concurrently mine multiple
views and contexts… wait for the blind answer and then compare what they thought vs what we
made."* This document is that idea, run six times, measured, and written down.

Claims tagged **[M]** measured today with the receipt named, **[R]** reasoned, **[P]** proposed
and untested. `[M]` means *I have the receipt*, never *I remember it* — a rule this repo learned
by violating it four hours before this was written.

Raw prompts and full branch outputs: `research/in-flight/multiview-2026-08-07/` (saved raw, not
summarised — every claim below should be checkable against the actual branch text).

---

## 1. WHAT THIS IS, AND WHY IT BEATS A TRANSECT

**[M]** A five-lens transect (five different questions, all outputting "problems found") cost
$0.065 and changed nothing about the day. A three-view fan (evidence / analogy / intuition) cost
$0.0155 and found a live defect, validated a design, and imported a solved architecture.

**[R] The difference is the OUTPUT TYPE, not the question.** The transect's five branches all
returned the same *kind* of thing, so I had to assemble them — and assembly at the junction is
where fan cost actually lives, not in tokens. Views that return different kinds of thing need no
assembly:

| view | returns | what you do with it |
|---|---|---|
| EVIDENCE | facts to verify | check them |
| ANALOGY | a solved design | evaluate and mostly reject |
| INTUITION | a divergence from intent | read the gap |
| ADVERSARY | a claim killed or survived | change the design or don't |
| DECAY | expiry dates | schedule or guard |
| MISUSE | attack paths ranked by accident-likelihood | fix the accidental ones |
| ABSENCE | the case never handled | add it |

**THE RULE: vary the output type across branches, not just the question.**

## 2. THE METHOD

**2.1 BLIND is load-bearing. [M]** Strip your rationale before sending. My first instinct was to
send the function as written — but its docstring contains the entire design argument, so the
intuition view would have read my reasoning back and the diff would have measured nothing. With
the docstring stripped, the intuition view *derived* the philosophy from code alone (*"a silent,
non-blocking nudge… trust over gatekeeping"*), which is a real result. Unblinded, it is theatre.

**2.2 PREDICT PER VIEW, BEFORE READING. [M]** Write what you expect each view to say. Then the
finding is the **delta**, computed rather than felt. Today this converted two would-be
disappointments into results: predicting the intuition view would *fail* to derive the design made
its success a measurement of legibility; and predicting ABSENCE would be weakest made its finding
of the only crash path informative rather than incidental.

**2.3 THE FAN PROPOSES, YOU DISPOSE. [M]** The analogy view returned four "mature versions have
this" items. I took **one** and rejected three, each against a stated constraint: caching was
ungrounded in measured cost, configurable patterns is YAGNI at one pattern, and an enforcement
mode contradicts the design law that this must never block. **A plausible maturity checklist is
exactly the shape that gets imported wholesale.** Budget for rejecting most of it.

**2.4 CALIBRATE ON A KNOWN ANSWER FIRST. [M]** The pre-flight check was tested against a pack
whose answer I already knew (VOID, and it said VOID) *and* a known-good pack (ANSWERABLE). A
detector that only ever fires is not a detector. Two-point calibration is the minimum.

**2.5 YOUR OWN ERROR LOG IS THE TRAINING SET. [R]** Every mistake you have already paid to find is
a labelled example. Replaying a delegation shape against a known failure costs cents and gives
honest, immediate feedback. This is the cheapest deliberate practice available, and it is the same
move as 2.4.

## 3. THE VIEW CATALOGUE

### PROVEN — measured yield today

**EVIDENCE [M]** — *"State only what the evidence shows. Enumerate the exact conditions for each
outcome. Then name where it fails to fire when it should, or fires when it should not. Ground
every claim in a line."*
Yield: found the id regex expiring at T1000 (silent, with all eleven pins green), plus two
failure-to-fire cases I had not considered. **The workhorse.** Its power comes from the
*enumerate-then-invert* structure — asking for the negative space of its own enumeration.

**ANALOGY [M]** — *"What real-world engineering artifact is this most similar to? How did THEY
solve it, including what they learned the hard way? What does this lack that the mature version
has?"*
Yield: named the artifact class (commit-msg hooks validating ticket status), and one of its four
suggestions was a real gap already lesson-backed in our own corpus. **The only view that imports
knowledge from outside the problem** — evidence and intuition both work on what is in front of
them. Highest variance: mostly rejected, occasionally the best thing in the run.

**INTUITION [M]** — *"You have never seen this. What problem did someone have that made them write
it? What does its design tell you about what its author believes? Do not hedge."*
Yield: near-zero divergence from intent → the design is legible. **Agreement is only informative
when the reading was blind.** This is the one view whose *success* is the finding.

**ADVERSARY [M]** — *"Argue this should NOT be built. Do not hedge into agreement. If you cannot
make the case stand, name the specific point that defeats you."*
Yield: changed a design twice in one run — killed per-mode thresholds (uncalibrated) and forced a
derived rather than declared mode flag. Nearly free at the junction, because its answer either
changes the design or does not.

### TESTED TONIGHT — all three produced real findings

**DECAY [M]** — *"This is correct TODAY. Find what makes it stop being correct LATER. Not bugs —
EXPIRY. Name the event that ends each assumption, and say whether the failure is LOUD or SILENT.
Rank by silence."*
Yield: three silent-expiry classes — an id-convention change, a `file_path` key rename in the tool
API, and a `state_view()` refactor — **every one of which would make the feature vanish without a
trace**, because the catch-all swallows it. This is the strongest new view, and the T1000 bug was
this class found by accident. **The "rank by silence" instruction is doing the work**: a loud
expiry is a bug report, a silent one is a guard everyone still believes in.

**MISUSE [M]** — *"Make it LIE, or stay silent when it should speak. Then say which of your attacks
would happen by ACCIDENT in normal work, because those matter more than deliberate ones."*
Yield: five attack paths, including a file-already-exists blind spot and unrecognised terminal
statuses. **The accident-ranking clause is the valuable half** — this system has no adversary, so
deliberate attacks are noise and accidental ones are the whole point. Essential for anything that
emits a verdict an agent will trust.

**ABSENCE [M]** — *"Not what it does. What is conspicuously NOT here that its author has likely not
noticed is missing? For each, why is its absence easy to miss?"*
Yield: **the only crash path found all night** — `(data.get("tool_input") or {}).get(...)` assumes
a dict, and `or {}` guards `None` but not a truthy non-dict. I predicted this view would be the
weakest; it was wrong, and its "why is it easy to miss" clause explains its own edge: it hunts
what the author cannot see, which is the class I am structurally worst at.

### CANDIDATES — untested [P]

- **INHERITANCE** — *"You are the agent who inherits this in three months with no memory of today.
  What do you need that is not here?"* Especially apt here, where sessions do not persist.
- **SECOND-ORDER COST** — *"What does this make more expensive elsewhere?"* The injection-volume
  constraint is this class.
- **OPERATOR** — *"You are the human deciding whether to trust this. What would you need to see?"*
  Returns what the *decision* needs, which differs from what the code needs.

## 4. COMPOSITION

**[R]** Three to four views. The cap is not cost — it is that each view must return a different
KIND of thing, and beyond four they start overlapping and you are back to assembling.

Suggested sets, by what you are actually doing:
- **Reviewing something you built:** evidence + intuition + decay. (Intuition tests legibility,
  which only works on your own work, blind.)
- **Deciding whether to build:** adversary + analogy + evidence.
- **Hardening something that emits a verdict:** misuse + decay + absence.
- **Cold artifact you did not write:** evidence + analogy + absence. (Intuition is pointless — you
  have no intent to diff against.)

## 5. FAILURE MODES

**[M] The evidence pack is the whole game.** Three of four files were refused in the run that
started all this; two branches were structurally void and I paid for them. **Pre-flight the ask**
before spending a fan — one call, VERDICT/MISSING/WOULD-FIX, measured at 9× cheaper than the
mistake it prevents.

**[M] Shared evidence packs damage unrelated branches.** `ask_many` builds one context for all
branches, so one refused file voided a lens that never needed it (T235 fixes this).

**[R] Unblinded runs measure nothing.** If your rationale is in the payload, the intuition view is
a mirror.

**[R] Analogy imports cargo if you do not budget for rejection.** Take one in four and say why.

## 6. WHAT THIS DOES NOT KNOW

- Every yield above is **n=1 per view**, all on the same small artifact, all on one model.
- No false-positive rate for any view. Unmeasured: how often DECAY invents an expiry that never
  comes, or ABSENCE names a gap that is deliberate.
- Untested on anything large. All views ran on ~60 lines.
- Untested across learners — a different model may have different view strengths, which is T229's
  question and is unresolved.
