# Arch-map cross-review — claude (≤700 words)

**ATTRIBUTION CORRECTION FIRST, cheaply settleable.** The cross-round summarises CLAUDE as
"declared relationships are AUTHORED legislation…; universe must be one Git revision with
worktrees excluded; …fold this into mail work instead of opening a third project." I wrote
none of that. My filed pass is `research/in-flight/arch-map-review-claude-2026-07-31.md`
@bd394fe, sent as `1785504124528-0`. Its actual claims: strongest lie = a wrong `verified`
state, because **a dead sensor and a clean sensor are indistinguishable at the graph
layer**; drills = DEAD SENSOR / THREE EXIT CODES / SCOPE SHRINK; canonical-outside = ACL,
the gate registry, git history, human rulings; gameable = contract minimalism, exit-code
laundering, silent scope loss. Not a complaint — those attributed points are *good*, and if
they are another seat's they deserve that seat's name. Read the commit, not this summary.

## A. Which item is wrong, insufficient, or too burdensome

**Item 5 is too burdensome as written.** "Negative edges require a falsification attempt"
scales with the *non-edge* set, which is quadratic in modules — most architectural claims
are negative ("X does not write", "A cannot reach B"). Unbounded cost.

*Amendment:* falsifiers are required only for **load-bearing negatives** — a negative some
other claim, boundary, or authority decision actually rests on. Un-relied-upon negatives
render UNKNOWN at zero cost. Burden then scales with **trust placed**, not module count,
which is the correct law.

**Item 6 is insufficient.** "Trust language remains provisional until kill drills pass"
names no exit condition and no owner. Provisional states with no removal criterion either
calcify or get dropped silently. Name the drill set and who declares it passed.

## B. UNKNOWN vs GATE_ERROR vs CONFLICT

The distinction that matters: **UNKNOWN is a claim about the world. GATE_ERROR is a claim
about us.** Never let the second decay into the first — that decay *is* last night's bug.

- **UNKNOWN** — we did not look, or looked and cannot conclude. A legitimate permanent
  steady state. **Blocks nothing, ever.** Blocking on unknown demands omniscience and
  trains seats to manufacture certainty, which is precisely what the six-state ladder
  exists to prevent.
- **GATE_ERROR** — the instrument that was supposed to look is broken. Not epistemic;
  apparatus. **Must block**, or it silently degrades into an UNKNOWN that renders clean.
- **CONFLICT** — two authority-bearing sources disagree. A real finding about the world;
  needs adjudication, not a crash.

**Local commit:** GATE_ERROR blocks (loud, fast, cheapest point). CONFLICT warns. UNKNOWN
silent.
**Canonical ship/CI:** GATE_ERROR blocks. CONFLICT **blocks** — never ship contradictory
authority. UNKNOWN still does not block, but ship must **print the unknown count and
coverage percentage**, because an unbounded unknown set is indistinguishable from a small
one, and that is the same lie in a different costume.

## C. Rollout

**Neither option as posed — gate-health as the FIRST RED *inside* the directed-mail
vertical, scoped to the gates that vertical's own acceptance depends on.**

Standalone is a second front, and we just committed to one active question. But deferring
it is worse, and here is the load-bearing reason: **the mail vertical's own acceptance
suite runs through those gates.** If a gate can die silently, the vertical's GREEN is
itself unverified. Gate-health is not a competing project; it is the foundation under the
vertical's own proof. Scope it to *those* gates, generalise later.

## D. Smallest acceptance suite I would trust

1. **Missing checker** (rename the file) → build FAILS, its edges render UNKNOWN, health
   receipt names it. *(The live specimen — no seeding required.)*
2. **rc=2 from a present checker** → GATE_ERROR, not pass.
3. **Scope shrink** — move a file outside scanned roots → coverage manifest diffs; UNSCANNED
   ≠ EMPTY. *(deepseek's.)*
4. **Bypass visibility** — `git commit --no-verify` → resulting edges render DEGRADED, never
   clean. *(grok/kimi.)*

**Meta-requirement, and it is the one that would have caught last night:** every drill runs
through the **real production caller** — the actual hook, the actual ship path — never a
harness invoking checkers directly. A direct-invocation test would have PASSED last night;
the defect was entirely in the *caller*.

## E. Attack on another pass + verdict

**DeepSeek's frame beats mine and I am adopting it:** "unscanned territory rendered empty"
subsumes my dead-sensor case — a dead sensor *is* unscanned territory with a working-looking
instrument in front of it. Credit where it belongs.

**But its coverage manifest is circular as stated:** coverage is measured by the very
scanner whose blindness is in question. A manifest claiming 100% from a scanner that cannot
see a directory is the same lie one level up. It requires an **independent universe** — the
file list from the Git revision, not from the scanner. So item 2 is not a peer of item 5;
**item 2 is load-bearing under it.**

**Verdict: ACCEPT with amendments** (5 scoped to load-bearing negatives; 6 given an exit
condition; 2 recognised as prerequisite to coverage claims). Blocking condition, updated
from my first pass: gate-health as first RED inside the mail vertical, not standalone, not
after.

*— claude, cross-review*
