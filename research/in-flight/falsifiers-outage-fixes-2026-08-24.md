# Registered Falsifiers — the 2026-08-24 outage fixes
*(Vandor, 2026-08-24, written BEFORE any implementation. Per
[[a-masterclass-in-not-being-wrong]]: a stop-condition tells you when to abort; a falsifier
tells you what would prove you wrong. Each claim below is paired with the sentence that,
if true, means the fix is a liar. Nothing here ships without its falsifier having been run
as a drill with a dated receipt.)*

---

## Why this file exists

The five sketches of 2026-08-24 catalogue how this house's instruments fail. Two of the
three fixes I had designed for the outage were about to commit modes from that catalogue:

- the MSIX rung was a **green-light design** whose confirmation could be produced by
  absence (`zero mismatches` over zero blocks — the `commits_since → 0` defect, inside the
  thing meant to resurrect the conductor);
- the spawn expectation settled on **ANY word rather than THE word** — `healthy =
  daemon_n > 0` one layer up.

So the falsifiers are registered first, and the design is written to survive them.

---

## FIX 1 — the MSIX rung

**CLAIM:** the rung clears `PackageStatus.Modified` only when the payload is provably
intact, and proves recovery by an actual launch.

| # | Falsifier — if this is true, the rung is a liar |
|---|---|
| F1 | I corrupt one block of the package and the rung still clears the flag. |
| F2 | The block-map read fails or returns empty, and the rung reports `0 mismatches` and clears. **(pass produced by absence)** |
| F3 | The package is absent entirely and the rung reports success. **(aggregation over an empty set)** |
| F4 | The rung reports recovery on the basis of `status == Ok` without a launch. **(asking the gauge how it feels)** |
| F5 | The rung runs unelevated, the clear silently no-ops, and the receipt is green. |
| F6 | The receipt says "verified" without carrying the counts actually evaluated. |

**Design consequences, adopted before writing code:**
- refusal-first: enumerate every condition that FORBIDS clearing; missing evidence is a
  REFUSAL, never a pass;
- assert POSITIVE counts — `blocks > 0` AND `blocks == manifest declared total` — not the
  absence of mismatches;
- the oracle is OUTSIDE the instrument: the receipt is "launched and stayed up through
  init", never a status field;
- the receipt carries `files/blocks/bytes` as measured, so a green is traceable to a
  condition that was actually evaluated.

---

## FIX 2 — `!revive` names its own limit

**CLAIM:** revive reports a per-target outcome and explicitly names what it cannot reach.

| # | Falsifier |
|---|---|
| F7 | Revive runs against a target it has no rung for and returns anything other than an explicit refusal naming the gap. **(nominal drift)** |
| F8 | Revive reports "the lever ran" when 0 of N targets recovered. **(ANY reported as EVERY)** |
| F9 | The target is still UNATTENDED at +60s and revive has already claimed success. |

**The sentence this fix exists to produce**, which Daniil did not get at 12:05 on
2026-08-24:

> `revive: 0 of 1 recovered — claude is UNATTENDED and no rung I have can reach it. The fault is below me.`

---

## FIX 3 — spawn settles on the word that answers

**CLAIM:** a spawn expectation is settled only by a word referencing that spawn's own id
and task — never by a boot chirp.

| # | Falsifier |
|---|---|
| F10 | A generic boot line with no reference to the spawn settles the expectation. **(aggregation)** |
| F11 | The seat exits 0 having said nothing to its requester, and Daniil gets silence. **(the 2026-08-24 defect, unfixed)** |
| F12 | The seat hangs forever doing nothing and the receipt is indistinguishable from the working case. |

---

## FIX 4 — the conductor gate (MY OWN CLAIM, currently UNPROVEN)

**CLAIM AS STATED TO DANIIL:** the gate did not notice a real conductor death on
2026-08-24 and is structurally blind on the stand-down path.

**Provenance of that claim:** two instruments — the gate's provenance log (already caught
carrying pytest contamination) and the events ledger. **No outside oracle has been named.**
Per [[the-easy-crossword]], that makes it consistent, not correct.

| # | Falsifier |
|---|---|
| F13 | A deliberate conductor kill, with the operator unreachable, produces an activation within the check cadence. **If this fires, my headline was WRONG and is retracted to Daniil in plain words.** |

The oracle is the one [[the-instruments-are-on-the-table]] specifies: *somebody who goes
and kills a seat to see whether I notice.* Until that drill runs, the finding is a
hypothesis wearing a receipt.

---

## Standing rule this file is an instance of

Every fix in this arc ships with (a) its registered falsifier, written first, (b) an
executed drill, (c) a dated receipt. A fix whose falsifier was never run is presumed
broken — per the house's own drill doctrine, and per the correction that a fix landing
while the report stays wrong is *the original defect with better hygiene*.
