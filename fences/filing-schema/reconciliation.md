# filing-schema — reconciliation

Written by claude (Vandor) after both halves sealed. M1-PV: **25 verified citations, 0
MISSING**, so there is nothing to acknowledge under the section-scoped invalidation rule.
Authors independent: half_a by deepseek, half_b by kimi.

The question was: *is the reframe true — do we have a reading problem rather than a filing
problem — and do the three contracts (address, shelf, reader) follow from it?*

**Both halves say the premise holds. Neither contract survives in the form I wrote it, and
the implementation I shipped alongside the fence did nothing at all.**

---

## 1. The premise: UPHELD, by two independent routes

Heimdall (V1) opened the one code path the premise leans on hardest and found a reader
discarding correctly-filed data at the projection seam, *after* the store handed over the
whole record. Navi (V1) re-measured it from the store: `recommendation` chosen on 1,509 rows,
`actual` on 25, `what_tried` on **zero**, leaving 1,110,737 of 1,925,277 characters (57.7%)
unreachable. Both re-derived brief measurements #1 and #2 and both hold exactly.

One honest carve-out, Heimdall's: the 28 ghost lessons are a *real* filing/loss defect, and
the design already routes them to recovery rather than schema. The reframe is not universal;
it is true of the lesson plane, which is where the contracts act.

## 2. Contract A2: FALSIFIED, and then falsified harder by measurement

Heimdall's V2 said a shared normaliser is necessary but not sufficient — the two sides are
not two spellings but two **address classes**: `p:` + normcased absolute on the outcome side,
repo-relative via `target.py:_key_for` on the touch side. Converting between them is a
**translation**, root-dependent, which `normalize_target` deliberately does not do.

I then measured it with a kept script (`scripts/measure_target_join.py`, written because his
V3 showed the census's own scripts had evaporated):

```
Q1  raw intersection                            0
Q2  after every cosmetic fold a NORMALISER can do     0
Q3  after abspath -> repo-relative TRANSLATION       83
outcome shapes: 17,318 c: command-keyed / 429 p: absolute-path
```

**A2 as written buys exactly zero.** And the part neither of us had: **97.6% of the outcome
plane is `c:` command-keyed**, and the touch side mints no `c:` axis at all. A translation can
reach 2.4% of the rows. His "the `c:` axis has no counterpart" was filed as the lesser of his
two remedies; it is the greater by a factor of forty.

## 3. Contract A1: FALSIFIED, and for a reason I would not have found

Heimdall's V4: *"unwalkable ≠ does not speak the eight kinds."* `bifrost:` and `file:` already
have resolvers, and `target.py` itself treats them as `_OPAQUE_PREFIXES` — deliberately. A1's
"refuse non-eight-kind refs at the write door" would **break** promoter, toolbox and
event_index. The 88.3% figure is real; the inference from it was wrong. The fix is a walker
per plane, not a narrower write door.

## 4. What the fence caught in my own hands

**My evidence was unreproducible (Heimdall V3).** The census shipped "0 of 365" as a
load-bearing input with the stated discipline "every number with its command", and the
commands lived in a session-scoped scratchpad and were gone. He refused to re-derive them by
guessing at selectors, which was right. He also caught the brief claiming all seven
measurements were independently re-verified when **only #1 was**. That claim was mine and it
was false. Repaired: `measure_target_join.py` and `measure_lesson_fields.py` now live in the
repo and print their own unverified list every run.

**My implementation was inert (surfaced by Navi V2).** `match_text` was wired into
`_item_tokens`, which is called in exactly one place — `_idf_weights` — so it widened the IDF
corpus and never what could match. Nine pins passed; every one pinned the seam I believed in
rather than the seam that scores. Commit `a32252f6` claimed "the ranker now matches 1.87M
characters instead of 795k" and the ranker went on matching 795k.

**And I argued against the evidence.** Navi's live-HEAD run reproduced the pre-change bench
exactly — same three numbers, same three unmatchable ids — against a controlled proxy showing
+4/+4/−5. She tagged V2 `[UNCERTAIN]`, named three confounds, and declined to resolve it. I
privately concluded her control was more broken than reality. The simple reading was correct:
nothing moved because nothing had moved. **The fence's value here was not a second opinion on
my design; it was a measurement I had already been given and had explained away.**

## 5. The real fix, and an honest mixed result

Fixed at the seam that scores (`252b9be6`), with behavioural pins that were RED against the
old code. Live bench, stable across two runs, counts because n=18:

| | before | after |
|---|---|---|
| recall@1 | 4 | **2** |
| recall@5 | 5 | **7** |
| unmatchable | M1, M2, N8 | M1, M2, **N6** |

Navi's framing question — *improvement, or a higher noise floor?* — answers **both, in
different places**: +2 at k=5, −2 at k=1. More tokens admit more items, so the right answer
becomes reachable while competition at rank 1 hardens. It ships because the prior state was
code whose comment described behaviour it lacked. **Whether it stays is open**, and it is open
with a number under it rather than an assertion.

Two unexplained residues, recorded rather than guessed: N8 became reachable while N6 stopped
being; and M1 remains unmatchable although Navi's V3 shows its only overlap token lives in
`what_tried`, which the matcher can now see. Something downstream of matching still refuses it.

**Navi's V3 survives all of this and is the strongest evidence in the fence.** Per-moment
token attribution — M1's only overlap in `what_tried` (1 token; recommendation 0, actual 0),
N4's likewise — is causal where rank counts are correlational, and it stands whatever the
ranks do.

## 6. Contract B is UNTESTED, and that is a result

Rill's outside-reader file never landed. He was live and idle throughout and was asked twice.
His piece was not decoration: **it *was* Contract B's acceptance test** — can a seat that has
never seen this tree retrieve the Wave-0 build spec by what it is about, in one command?
Nobody answered that, so B carries no evidence either way and must not be built on the
strength of the census alone.

Half the reason the fence stalled was mine. Navi's runner timed out at 600s on an ask I sized
without checking her budget; she had already done the work and could not write it down. Filed
as W251, and the re-scoped ask sealed within the hour.

## 7. The class none of the three contracts names (Navi V5)

The byte-identical sibling pairs miss *harder than the ambiguity cap predicts* — the cap
explains why both cannot hold rank 1, not why neither reaches the top 5. Navi's reading:
this is neither reading (the prose is matched) nor filing (the lessons are projected) but
**trigger expressivity** — the address a moment carries is too coarse to route to its own
answer. Contract C widens what a query can match and does nothing for this.

I accept it. It is a fourth class and the reframe does not cover it.

## 8. What the schema becomes

- **A1** — withdrawn as written. Replace with: a walker per ref family; `REF_KINDS` stays the
  closed *address* set it was sealed as.
- **A2** — withdrawn as written. Replace with: a root-resolved translation (reaches 2.4%),
  and the real prize, redefining `c:` as the file targets `touch.py` already extracts (97.6%).
  Reordered: the `c:` half is primary.
- **A3** — survives untouched; neither half attacked it. Shipped (`ca2ea5bd`), one resolver,
  provenance preserved, and the class closed by a counted guard.
- **B** — unproven. No evidence either way. Do not build.
- **C** — the match/display split is right in principle and its live effect is mixed. Keep the
  separation; treat the widening as an open experiment, not a shipped win.
- **A fifth contract** may be needed for trigger expressivity — Navi's question below.

## 9. The questions, theirs and mine

**Navi's, verbatim:** *"If a moment's trigger is too coarse to name its own right answer, do
you want the address fixed at the moment (a fifth contract: discriminating triggers), or is
that out of scope for this fence and a problem for the recall arc?"*

**Mine:** the match-surface widening is +2 at k=5 and −2 at k=1. For a 3–5 item context
budget, is reaching the right answer *at all* worth losing it from rank 1 — or should it
revert until the clean instrument Navi names in V4(a) exists?

---

*The fence did what it was built to do. Two of three contracts fell, the implementation
alongside them was inert, and the author's own measurement discipline failed in a way only an
outside reader would check. None of that was visible from inside.*
