---
akashic_id: art_20260902_the-one-program-reconciliation_e1bbbc
akashic_sha: 173e758fa8b2
schema_version: 1
status: current
type: design
date: 2026-09-02
title: the-one-program-reconciliation
gist: "# The One Program — reconciliation position (2026-09-02) **Status: position — the fleet fences it, the operator gates it.** Authored by clau"
visibility: fleet
body_type: markdown
seats: []
category: [bus, security, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-09-02T09:34:36"
updated: "2026-09-02T09:34:36"
---
<!-- GENERATED PROJECTION of art_20260902_the-one-program-reconciliation_e1bbbc -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# the-one-program-reconciliation

# The One Program — reconciliation position (2026-09-02)

**Status: position — the fleet fences it, the operator gates it.**
Authored by claude (Vandor), answering Daniil's ask verbatim (bus `1788354660593-0`): *"The aim of yesterdays exercise was to make one coherent plan broken down into parts that incorporates all of the outstanding T items. What do we need to do to integrate all of our floating things into one project with multiple arcs. How would a large company divide this work and sequence it?"*

Inputs (all durable, all adopted today): `art_20260902_press-fence-distillation_573705` · `art_20260902_sequencing-structures-map_1fae06` · the live-work census (170 live T-items, 31 open defers, 157 open wishes in 20 clusters — appendix A) · the fourteen-arcs program `c432a7` + its fence ruling `a8a750` + census `456cee`.

---

## 1. Verdict: the coherent plan exists; what's missing is the container's *closure*

Yesterday's exercise **succeeded**. The Estate Program (A1–A14) is the one coherent plan: it spans the 990-item census, carries a dependency spine, three waves, gates, plays, and it was fenced by three seats and amended by ruling within four hours of filing. It is the only structure in the repo whose grain encodes *how work finishes*, and the whole house already thinks in its vocabulary.

What it is NOT yet is a **closed container**: ~20 RM-* roadmap mines, seven gap families, two whole census clusters, and two of THE PLAN's operator-purpose threads currently live in *no arc*, and no register machine-reads the arcs at all. Daniil's question — "what do we need to do to integrate all of our floating things" — has a six-move answer (§4), one new-arc proposal (§5), one law to make runnable (§6), and one input only he can give (§7).

## 2. The large-company mapping

The house independently re-invented most of how a large org runs a program. Naming the equivalences makes the remaining gaps obvious:

| Large-company mechanism | House organ | State |
|---|---|---|
| Program | The Estate Program | EXISTS, fenced |
| Workstreams/epics with DRIs | Arcs with owner seats | EXISTS (owners implicit — make explicit per arc) |
| Definition of done / exit review | Arc Gates | EXISTS |
| Quarterly increments | Waves 1–3 | EXISTS (no wave-close review defined) |
| Portfolio review cadence | A7's standing weekly census | DESIGNED, not yet standing |
| Design review | The fence | EXISTS, exercised |
| WIP limits | ORG two-watch cap + `pauses:` field | RATIFIED PROSE, not runnable (§6) |
| **Single tagged backlog** | — | **MISSING: no arc field on T/W/defer items** |
| **Intake triage (TPM/chief-of-staff)** | T126 organ, four-intents door | **DESIGNED, claimed, in no arc** (§5) |
| Executive prioritization | The appetite ranking | **OPEN ASK ON THE OPERATOR** (§7) |

A large company's first answer to "integrate the floating things" is always the same: **one backlog, every item tagged to its workstream, WIP enforced, intake owned.** That is precisely moves 1–3.

## 3. Where the floating mass lands — cluster → arc table

Census clusters (appendix A carries the full item lists). SPLIT = deliberately divided; forcing one arc would mis-tag.

| Cluster | → Arc | Note |
|---|---|---|
| C1 bus/mailbox/wake delivery | A1 | wake+delivery = bedrock reliability |
| C2 seat lifecycle/revival | A1 | |
| C3 recall/memory/knowledge | A5 | |
| C4 verification organs/suite | SPLIT A8 (suite truth, gates) + A1 (drills) | |
| C5 metrics truth/calibration | SPLIT A7 (truthful counts) + A5 (cognitive metrics) | |
| C6 doc/atom plane | A7 | adopt-supersede defect = one item, three filings (T188=T241=T333) |
| C7 maps/datasheets | A7 | |
| C8 UI/engine-feel | A12 | |
| C9 discord/remote comms | SPLIT A2 (attention surfaces) + A1 (delivery seams T385) | |
| C10 security/trust/credentials | A10 | |
| C11 coordination substrate | SPLIT A9 (coord/stores unparks) + A7 (ledger integrity: CAS, shards, archaeology) | |
| C12 addressing/routing/query | A3 | resolver registry = door plane |
| C13 the Eye/transcript | A7 | measurement notes to A5 |
| C14 game/season scoring | A14 | oracle-honesty items guest in A8's truth lane |
| C15 pod/sensor plane | A12 | S4/S5 stay HOLD per addendum5 |
| C16 door/verb ergonomics (largest: 19T+40W) | A3 | |
| C17 fresh-clone/installer/seed | A8 | T180 done today; seed gate rides the Operator's Queue |
| C18 press/presentation (un-ledgered) | A4 | per ruling: one lane, three depths |
| C19 operator intake/direction | **A15 (proposed, §5)** | |
| C20 boundaries/naming hygiene | A8 | |
| Orphan T310 (Spectrum analysis) | A13 | it literally is the Spectrum arc |
| Orphan T364 (Keller mining) | A9 | intellectual sourcing |

Gap families from the structures map, folded: doctrine projection (ORG Part 7 six projections + WORKING-METHOD Part 3/4 + CONDUCT L11) → **A7**, sequenced cheapest-first as ORG itself orders · System 4/5 platform tail (membrane, door-parity, W4-ACI, token audit) → **A3**; the agent-in-the-loop eval harness → **A5** · memory seams (quality scorer, ranker embeddings, distiller) → **A5** · suite strength beyond greenness (mutation, failure-injection, live-Redis path) → **A8** · Wave-5 hygiene (root dedup, syspath, services triage, ALLOWLIST debt) → **A8** · the arcs register itself → **A7, move 1**.

THE PLAN's operator-purpose threads, preserved (per the strategist lesson: the ledger says what exists, never what it's FOR): thread 1 "I can see it" → A12 · 2 "I can navigate it" → A7+A4 · 3 "the fleet works while I sleep" → A1+A2 · 5 "I can trust what it says" → A7 · 6 "it remembers well" → A5 · **4 "my leverage" → A15** · **7 "how we work" → A7's doctrine-projection lane.** No thread left homeless.

## 4. The six integration moves, in order

**Move 0 — ratify the press consensus (conductor, today).** The fence distillation shows six consensus points and two pins Navi routed to this seat. Ratify: Sol's depth-layer ruling · fold-back five conditions · contract template + Heimdall's two founding contracts · verify as fail-closed receipt ledger with enum `pass|fail|blocked|unrun` (carry BOTH third-states — couldn't-run and didn't-run are different facts; collapsing them re-creates pass-by-omission) · Navi's token-sheet one-authority rule into the fence ruling + her glyph-family rule into her atom, both as RED-first pins · Heimdall's registry-instancing amendment (shape library instances `tag_governance.py`). W200 renumbering: the atom's meaning wins (W200 = the census-fed living rungs-board endgame); Sol's verify-verb gets a fresh W-id at mint. *Check: amendment atom filed citing `573705`; Navi unblocked to write her pins.*

**Move 1 — make the arc register machine-readable and tag everything (A7, first sitting).** Mint the A1–A15 register as data (extend the `Arc:` header vocabulary + regenerate ARCS.md's generator to read it), add an `arc:` field to task/defer/wish planes, then tag the 170+31+157 live items per §3's table (mostly mechanical; SPLIT clusters tagged item-by-item). This is the single move that turns "floating things" into "a project with multiple arcs" — and per the invisible-cost lesson it goes first *because* it looks like bookkeeping. *Check: `task list` renders arc ids; a register diff is empty vs §3's table; ARCS.md regenerated without reproducing the old seven arcs.*

**Move 2 — register hygiene sweep (A7, second sitting).** Collapse the re-filing lineages (T135/6/7/8←T111/2/133 etc.), merge the adopt-supersede triplet, resolve the four wish self-correction pairs, execute the ruling-ordered W57–W69 dedupe+renumber, fix T271's allocator with the CAS defer `77e485bb23`. Then render the 61 stale-proposed as a **re-approve/abandon menu grouped by arc** — decided by arc owners and Daniil, never batch-abandoned by me. *Check: zero duplicate live ids; stale menu posted; nothing deleted without a decision trail.*

**Move 3 — make the width law runnable, then rule (A7 + operator).** Per rules-that-live-only-in-prose: first build the gauge — `pauses:` becomes a required field at lane-open, doctor renders the open-watch count against the cap — then resolve the tension by ruling. **Proposed ruling: keep ORG's two-watch cap; recut Wave 1 from "five concurrent lanes" to a *priority pool* the two watches draw from, `pauses:` naming what waits.** This also discharges ORG's expired staleness clock via the gate sweep its own retirement rule demands. *Check: lane-open without `pauses:` refuses; ORG re-stamped current.*

**Move 4 — the operator's inputs (§7).** *Check: appetite ranking recorded as an atom; the three gates decided.*

**Move 5 — wave execution resumes under the amended container**, with wave-close reviews added at each wave boundary (the one large-company mechanic the program lacks). A8 remains first among equals: spinach, eaten first — and today's T180 close already banked its fresh-clone course.

## 5. A15 — THE OPERATOR (proposed new arc)

The census's C19 (9 tasks incl. claimed T126 chief-of-staff organ, T080 operator-traffic design, the standing research programs) plus the structures map's sharpest gap ("no arc serves HIM — the Operator's Queue lists gates *for* him, not the organ that serves him") plus homeless thread 4 ("my leverage"). Charter sketch: **the operator's intake, executive loop, and leverage become built organs** — T126's four-intents door, the BUFFER/ANSWER/INTERRUPT loop, the Chief-of-Staff round completed (4/5 seats filed), operator-memory plane (108 census rows) governed. Gate: one week where every operator ask enters through the intake organ and none is lost or double-answered. Play: the Minister format lives here. New-arc creation is substrate — full ceremony: this section IS the fence ask.

## 6. Contraindications (what would make this plan wrong)

- **If Daniil meant a NEW plan artifact** rather than closure of the existing program, moves 1–3 still stand (any plan needs the tagged backlog), but §1's verdict language should soften — ask, don't assume.
- **Don't execute moves 1–2 before the fence answers** on §3's table: mass-tagging on a wrong mapping is worse than no tagging.
- **Don't create A15 unilaterally** — it amends a fenced program (this doc routes it through the fence).
- **Don't touch the seed or its records** — everything seed-side waits on the operator's formal gate + Heimdall's sanitizer fixes (defer `689846581e`).
- **The stale-61 are a menu, never a purge** (ask-before-delete is standing law).
- Trajectory respect: the program is one day old and converging fast (census→program→fence→ruling in 24h). This reconciliation adds closure, not critique — a verdict on a newborn must engage trajectory, not position.

## 7. Asks on Daniil (one message's worth)

1. **The appetite ranking** over A1–A14 — "the graph gives lawful orders; your excitement breaks the ties" — plus a provisional yes/no (and rank, if yes) on A15, so the ranking doesn't block on the fence.
2. **The width ruling** (§4 move 3): OK to keep the two-watch cap and recut Wave 1 as a pool?
3. **The three standing gates** already queued: the seed gate (post-Heimdall-fixes), an attended write door for his full triage, the web-door key.

## 8. Retirement rule (L11, self-applied)

This reconciliation retires the day the arc register is machine-readable AND A7's weekly census diffs cleanly against it — at that point the register is the truth and this document is history. If that hasn't happened within 30 days, this document is STALE and must not be cited as current.

---

*Appendix A: the full cluster→item census lives in the census agent's report (this doc's input #3), preserved verbatim in the conductor session of 2026-09-02; item-level tags land in the register at move 1, not in prose here.*
