---
akashic_id: art_20260801_daniil-gate-surface_037701
akashic_sha: ce2d22788cd9
schema_version: 1
status: current
type: report
date: 2026-08-01
title: daniil-gate-surface
gist: "# ONE GATE — everything waiting on Daniil Status: current | 2026-08-01 ~01:00 local | assembled by claude#ca84109a Six decisions have been a"
visibility: fleet
body_type: markdown
seats: []
category: [memory, bus, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-01T00:19:15"
updated: "2026-08-01T00:19:15"
---
<!-- GENERATED PROJECTION of art_20260801_daniil-gate-surface_037701 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# daniil-gate-surface

# ONE GATE — everything waiting on Daniil

Status: current | 2026-08-01 ~01:00 local | assembled by claude#ca84109a

Six decisions have been arriving at Daniil one at a time, through notes, commit messages and bus
mail, over several days. That is the interruption pattern the buffer round exists to end. This is
the single surface. Nothing here is new work — every item is already designed, filed, and waiting.

**Reading order matters.** Item 1 subsumes parts of 3, 4 and 6. Decide it first.

---

## 1. RATIFY THE DEPARTMENT SYSTEM — `docs/ORG.md`

**This is the thing he asked for on 2026-08-01: "a department system for division of labor."**
It already exists. It was built 2026-07-31 from his own Siemens finding, carried verbatim:

> *"Processes that intersect between departments never seem to be treated as a consideration of
> the overall architecture … no one seems to care about the handoff ergonomics from department to
> department."*

The organising move, and the reason it is not an org chart: **posts own HANDOFFS, not domains.**
The intersections are what nobody owns. Thirteen posts, each owning one handoff — intent→lane,
operator→fleet, work→record, spec→running code, claim→proof, belief→truth, proposal→committed
reality. The no-ownership invariant is untouched: posts are gravity, not walls. Any seat may still
claim any task; no seat holds a file.

**What ratification decides, concretely:**

- **B1 — the empty-hands rule.** The conductor may not hold a build slice while conducting. Daniil
  enforced this by instinct tonight by spinning up `opus-engineer`. Ratifying makes it structural
  rather than a one-off.
- **B3 — no bus-factor-1.** Every mind-post names an understudy. Currently MISSING, and the
  evidence is 30 dead `claude` incarnations with claude holding conductor + chief-of-staff +
  sole-committer simultaneously. This is the difference between a *seat* dying and a *post* dying.
- **B2 — the Contrarian.** Not a seat: a slot filled by exclusion. The contrarian on any watch is
  whoever did not build the thing, mandatory and unsolicited, with NO authority — it produces the
  strongest objection and the builder decides. Currently PARTIAL.
- **C4 — the Siemens round.** His own ritual, never instituted here: every specialist is also a
  customer of the others and says so on a schedule. One line per seat at every gate: what would
  make my job easier if you did it differently. Currently MISSING.

**Open inside it, needs his word:** the Chief of Staff post is deliberately NOT decided in the
document — that round is live and four of five seats have now filed. Pre-empting it from the doc
would be the same act the round exists to fix.

**Also inside it:** Part 8, the standing pause rule, which claude ruled PROVISIONALLY under his
delegation ("right now you can choose, when I come back we can adjust this"). He is back. The rule:
corrections never trigger a pause, design pauses, never a build in flight, the pause is announced
with what stopped and what resuming costs, one word from him overrides. Its honest weakness is
recorded in the doc: it is wrong when the design lane matters and the build is trivial. That was
accepted because the failure it causes is cheap and LOUD while the failure it prevents is expensive
and SILENT — if he rejects that trade, the rule should change rather than be patched.

**Verdict needed:** ratify / amend / reject.

---

## 2. THE 20 STALE PROPOSALS — keep or kill, one sitting

Deliberately NOT swept. Stale means intent DRIFTED, not that intent DIED, and only he can tell
those apart. Abandoning proposals so a counter drops is precisely the metric corruption codex named
in the buffer round.

The pile includes **T020 visual layer** — his first recorded want, optics-first — plus T032
retrieval v2, T092 reasoning spine, T098 home-base program. Things he asked for, that drifted.

**Verdict needed:** per item, or a rule claude applies on his behalf.
Full list: `py agent_cli.py task list` → PROPOSED BUT STALE.

---

## 3. T118 — THE STORE CUTOVER FLIP

The only live task whose next action is his and nobody else's. Default flip is staged and waiting.
Held OUT of the park pass specifically so it would not go quiet.

**Verdict needed:** flip / hold / more evidence first.

---

## 4. THE L11 RETIREMENT RULE (ORG.md O4)

*"Unbounded accumulation is what makes a post feel unwinnable; elite units close things. A backlog
that only grows is a morale instrument pointed the wrong way."*

Tonight gave this a receipt: the ledger had **no honest way to release a claim** — `abandon` lied
(asserts intent died when it drifted), `approve` dropped the reason, and `park` was unreachable
from the state where work actually accumulates. Fixed 2026-08-01, RED-first. But the *policy*
question stands: what retires automatically, and what requires his word.

**Verdict needed:** adopt L11 as a standing rule / scope it / drop it.

---

## 5. WORKING-METHOD.md

The originating doctrine plane (CONDUCT leads, WORKING-METHOD originates, ORG shapes). Filed and
unratified.

**Verdict needed:** ratify / amend.

---

## 6. THE EYE

The falsifier for the buffer/intake organ: it must reconstruct every held item and every transition
**while disturbing no reader cursor**. Codex's framing is the load-bearing part — a buffer that also
authorizes becomes a hidden governor (agenda capture, self-sealing judgement, interruption-
minimising metric corruption, stale judgements laundered into facts across incarnations). The Eye is
what makes that falsifiable rather than trusted.

Now has a home: **T126**, minted 2026-08-01, the first ledger entry his stated #1 priority has ever
had. The Eye is its slice S5.

**Verdict needed:** is the Eye a gate condition for T126 shipping, or a follow-on slice.

---

## What claude is NOT asking him to decide

- **T125 grading** — dispatched to `opus-engineer`, which is clean by construction. Runs without him.
- **What parks** — done 2026-08-01 under his explicit delegation. 21 active → 5. Reversible; every
  parked task carries its debt in its reason line.
- **The mail root cause** — diagnosed, immediate fix shipped, structural fix (T108) is live and
  needs a fence with deepseek + kimi, both currently down. Blocked on seats, not on him.

---

## The theme claude would name, if he wants it named

Five defects found on 2026-07-31/08-01, and they are one defect:

| what it claimed | what was true |
|---|---|
| ledger: "release your claim with `approve`" | the reason was silently dropped |
| wake guard: "the watcher will now block correctly" | per-process seed; never survived to the next arm |
| boot: "research/** persists by doctrine" | rule-13 had REFUSED it since 2026-07-23 |
| lookback: searches the corpus | `charters/` — his own twenty entries — were not in it |
| the buffer | exists, and no newcomer can discover it |

Every one is **a system reporting a state it is not in.** Not five bugs — one theme, and it is
load-bearing, because the entire proposition of this project is that an agent can trust what the
system tells it. Each of these taught a seat to distrust an instrument, and the cost compounds: a
guard that cries wolf trains the behaviour it exists to prevent. Claude re-armed that watcher five
times tonight *because it said it had worked*.

**Proposed standing lens, not a task:** ask of every surface — *does this ever claim a state it is
not in?* It would have caught all five before they cost anything.
