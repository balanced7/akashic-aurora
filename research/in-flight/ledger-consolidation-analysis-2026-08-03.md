# Ledger consolidation — analysis of all 84 open entries, 2026-08-03

Daniil: "How do we make sure we aren't losing anything with the entries. I am sure there are
entries that overlap. I think we should probably analyze all of them and consolidate."

**Nothing in this document has been applied.** It is a proposal for his ruling. The ledger is
untouched.

## How loss is prevented — the four guarantees

1. **Nothing is deleted, ever.** Consolidation means the ABSORBING entry names the absorbed
   T-numbers in its own text, and the absorbed entry is `abandon`ed with a reason pointing at the
   absorber. Both remain readable in the ledger forever; `abandon` is a tombstone, not an erase.
2. **Most merges are not my judgment — they are already written in the entries.** T072 says
   "Supersedes/absorbs proposed T036+T037". T088 says "Absorbs T072 + T036 scope". T098 says
   "absorbs/aligns T033 UI re-grounding + T060-M7 glass cockpit + T079 engine room". Those
   absorptions were declared by their authors and never executed. Applying them loses nothing that
   the ledger did not already say was subsumed.
3. **This document is committed BEFORE any mutation**, so the full pre-state is recoverable from
   git independently of the ledger file.
4. **`state/coord/tasks.json` is version-controlled.** Any consolidation is one `git revert` away.

## What the census actually found

84 open of 133 total (63%). Four categories, and only ONE of them is genuinely "unfinished work".

---

### A. COMPLETION RECORDS MISFILED AS PROPOSALS — 4 entries, 0 risk

The clearest defect in the ledger, and it explains part of the 63%. Someone recorded a completion by
PROPOSING A NEW ENTRY describing it, instead of closing the original. The numbering then drifted:

| entry | status | its own title says |
|---|---|---|
| T110 | proposed | "**T110 DONE** (08f6016+c2244b6): cost meter honesty…" |
| T111 | proposed | "**T108 slice 2 DONE** (31e6737): per-incarnation lane cursor…" |
| T112 | proposed | "**T113 DONE** (c94e1f4): the tool send door spills oversize payloads…" |
| T113 | proposed | "**T115 DONE** (2cc5dc6): check_advertised_verbs…" |

Note T112's title names "T113" and T113's names "T115", while the real T115 is an unrelated
faithfulness diagnosis. The IDs and the contents disagree.

**Proposed:** mark all four `done` (each cites its own commit sha as the receipt), and re-file their
three explicit OPEN FOLLOW-UPs as small entries so they are not lost with the closure:
- kimi-k3 + sol model rates missing from PRICES (cost-aware routing cannot price those lanes)
- T111's open question to deepseek on read-only cursor inheritance windows
- the MCP twin for `bifrost_fetch` (declared tracked debt; 5 known CLI↔MCP gaps)

**Risk: none.** The work is on disk with commit shas.

---

### B. DECLARED-BUT-UNEXECUTED SUPERSESSION — 3 chains, 11 entries

#### B1. Multi-seat identity / cursor sharing / mis-wake — 5 entries → 1
`T035(abandoned) → T036 → T037 → T072 → T088 → T108`

Each names its predecessor. T072: "Supersedes/absorbs proposed T036+T037". T088: "Absorbs T072 +
T036 scope; folds T080 frm-spoofing caveat". T108 (`claimed`) is the architectural answer to all of
it — Daniil's own words in it: *"why can't we have two seats or as many as we need so we stop
getting all this mail mis routing, mis waking, mis consuming, mis everything mess."*

**Proposed:** T108 absorbs T036, T037, T072. T088's *naming/display-name* half is genuinely distinct
(a UI-legibility concern, not a coordination one) and survives on its own, scoped down.

#### B2. UI / cockpit / home-base — 5 entries → 1 program + kept slices
`T007 → T033 → T060-M7 → T079 → T098`

T033: "incl. the parked T002/T007". T098: "absorbs/aligns T033 UI re-grounding + T060-M7 glass
cockpit + T079 engine room (their designs become this program's views)".

**Proposed:** T098 is the program; T033/T079/T060-M7 become its views as their own text already
says. T003 and T005 are small shipped-UI fixes that should NOT be swallowed by a program — keep
them standalone and small.

#### B3. Store cutover — already handled correctly
T117 `abandoned`, T118 `claimed` re-files it. **No action.** Included to show the pattern works when
someone executes it.

---

### C. OVERTAKEN BY EVENTS — 3 entries, needs a receipt check before closing

- **T076** (parked) "redelivery-storm hygiene": item (1) *sanctioned skip-to-now* now EXISTS as
  `bifrost-skip-to-now` and was used today under audit. Items (2) storm detector and (3) root
  spigot remain. **Proposed:** close item 1 in the text, keep the entry for 2+3.
- **T031** (parked) "method-baseline enforcement": its (2) pre-registration checker and (4)
  verbatim-record linter exist as `check_preregistration.py` and `check_verbatim_citation.py`.
  **Proposed:** verify each against the entry's wording, then reduce the entry to what is left.
- **T133** (approved) is now substantially delivered (M1–M6 landed 2026-08-02/03 across six
  commits). **Proposed:** mark done, re-file the two named residuals (harness-seat receipts
  unproven end-to-end; M3 needs the scheduled sweep it now has).

**Risk: real but bounded.** Each needs its receipt verified before closing — that check is the work,
and it is cheap.

---

### D. GENUINELY DISTINCT AND LIVE — keep untouched

T125 (architecture datasheet — *"THIS is the heart of what I am trying to fix"*), T126
(chief-of-staff intake — *"my priority"*, stated twice), T127–T132 (pod + rooms), T047 (retire the
legacy stream — the ROOT CAUSE of the dual-lane drift that cost this week two debugging passes),
T123 (boundary debt), T107, T109/T114 (the R-track), T115, T116.

**T047 deserves promotion, not consolidation.** Everything in the lane/cursor/mis-delivery family
exists because dual-write is still live. Retiring the legacy stream removes the *class*.

---

## What this would change

- 84 open → roughly **68**, without a single line of work being dropped.
- 4 entries move to `done` with commit receipts.
- 7 are absorbed by entries that already claim them.
- 3 shrink to their genuine remainder.
- 3 new small entries are MINTED so that explicit open follow-ups survive their parents' closure.

The last point is the one that matters for "not losing anything": closing a parent without
re-filing its named follow-ups is exactly how work disappears, and three of these parents have them.

## What needs Daniil's ruling, not mine

1. **T088's naming/display-name half** — keep as its own entry or fold into T108? It is the one
   merge in B1 I am not confident about.
2. **T003 / T005** — small UI fixes owned by `deepseek-plumbing`, approved 6 weeks ago, untouched.
   Still wanted, or abandon with a reason?
3. **T020, T028, T032, T041, T051, T085, T090, T092, T098, T103, T105** — eleven design/program
   entries, none started, several superseded in spirit by later arcs. These need a *decision*, not
   an analysis: the corpus's own ruling is that "a stale ledger is a curation act, and it delivers
   more relief per hour than any sprint."

## Method note

Every proposed absorption above quotes the absorbing entry's OWN text declaring it. Where no such
declaration exists, the entry is left alone or routed to Daniil. That is deliberate: an automated
broom must not outrank an author who actually wrote down what they meant.
