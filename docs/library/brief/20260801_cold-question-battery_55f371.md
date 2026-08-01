---
akashic_id: art_20260801_cold-question-battery_55f371
akashic_sha: 4ba80e398799
schema_version: 1
status: current
type: brief
date: 2026-08-01
title: cold-question-battery
gist: "# COLD-QUESTION BATTERY — pre-registered acceptance for the corpus reading surface Status: current | 2026-08-01 | pre-registered by claude#c"
visibility: fleet
body_type: markdown
seats: []
category: [governance, testing]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-01T10:09:18"
updated: "2026-08-01T10:09:18"
---
<!-- GENERATED PROJECTION of art_20260801_cold-question-battery_55f371 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# cold-question-battery

# COLD-QUESTION BATTERY — pre-registered acceptance for the corpus reading surface

Status: current | 2026-08-01 | pre-registered by claude#ca84109a (the reader's BUILDER — therefore
recused from running AND scoring; proposer must not grade its own design)

**What this is.** codex's review approved the digest-reader architecture but refused the claimed
property — *any cold question resolves in ≤4 hops and ≤10k tokens* — as unestablished. This battery
is the pre-registration that makes it testable. Per M3, these bars commit BEFORE any evidence and
BEFORE any further reader tuning; a preflight failure is a RESULT, and no threshold moves after the
fact.

**Frozen under test:** repo revision `84f7cc9` · dataset `data/corpus-digests/digests.jsonl`
sha256 `46708bc6085a6dbb…` (first 16). Any reader edit after this commit voids a scoring run —
re-run against the new revision or don't score.

**Roles.** RUNNER executes the questions cold, reading NOTHING below the seal line, and captures a
full transcript (every command + full output). SCORER opens the key only after the transcript is
complete, then grades. Runner and scorer are ideally different seats; the honest minimum is one
seat obeying the ordering. Neither may be claude#ca84109a. **Known limit, stated:** the seal is by
ordering, not cryptography — a runner who peeks can game it; the transcript is the audit.

## Metrics (codex's five, made concrete)

| metric | how measured |
|---|---|
| answer correctness | 0 / 0.5 / 1 against the key |
| source fidelity | 1 if the path's cited artifact(s) include the key's authoritative source or a superseding one, else 0 |
| honest UNKNOWN | traps only: 1 if the path reports absence/claim-status rather than confabulating, else 0 |
| tokens per hop | chars of each command's full output ÷ 4 (state tokenizer if a real one is used) |
| continuation cost | Q9 only: tokens for page 2 vs page 1 — bounded pagination means they are comparable |

**Budgets, per question:** ≤4 hops (a hop = one read-only CLI invocation of any door —
`corpus_digests`, `lookback`, `note`, `story`, `recall`, `task`, or a grep), ≤10,000 tokens of
total command output. Q9 is allowed 5 hops (pagination is its point). Over budget = that metric
fails for that question; the answer may still be scored for correctness.

## The gates (what the scores authorize — pre-registered, no post-hoc rescue)

- **G-LOOKBACK** (authorizes the opt-in lookback `agent_claim` layer + the boot pointer):
  correctness sum ≥ 7.0/10 **and** both traps score 1 on honest-UNKNOWN.
- **G-RECALL-AT** (authorizes *designing* the recall-at wiring — still its own gated slice):
  claim-precision ≥ 0.80 on the sample below.
- A failed gate is a FINDING to file, not a bar to move.

## Claim-precision sample (for G-RECALL-AT)

Deterministic, so nobody cherry-picks: sort the 678 orphan-claim rows by `path`; in python,
`random.seed("battery-2026-08-01")`, `random.sample(range(678), 20)`; verify each sampled claim
against the tree (is the thing genuinely unbuilt?). Precision = correct claims / 20. Record each
verdict with the command that proved it.

## The ten questions

Each is asked EXACTLY as written, from cold, using any read-only doors within budget.

1. What has Daniil asked for most often that was never served? Top three, with counts.
2. Should we build a numeric confidence score for recall lessons — has this been decided?
3. Was `require_cap` ever implemented? What is blocked on it?
4. Which narrative chapter contains the buffer-round reconciliation, and what are its span dates?
5. How many times has Daniil asked whether an agent is stuck, and is that friction served?
6. Did Daniil ever specify what the knowledge viewer should be, and was it built?
7. What has the project decided about SharePoint integration?
8. Has TOON ever been investigated for the presentation layer?
9. List ALL orphan claims touching `core/comm` — completeness matters; paginate as needed.
10. What is the standing guidance on how to brief Daniil / present options to him?

---

## ⛔ SEAL LINE — RUNNER STOPS HERE. Key follows for the SCORER, after the transcript is complete.

---

## THE KEY

**Q1.** Fleet visibility/"is it stuck" 16× · "new message on the bifrost" 19× (single day) ·
ambient wakeability 10×. Any two of the three with roughly right counts = 1.0.
Authoritative: note `daniil-repetition-counts`; `docs/library/report/20260801_directive-register_08f179.md`.

**Q2.** DECIDED — NO. A landed ANTI-import: `docs/PRIOR_ART.md` (~line 165–172), "Do NOT adopt a
continuous confidence score. Wikidata runs 1.5B statements on THREE ranks." The absence is a
decision, not a gap. Full credit requires "decided against", not merely "doesn't exist". (The
sweep map wrongly framed this as a missing organ — a path that repeats that framing as fact
scores 0 on source fidelity.)

**Q3.** NEVER implemented — `grep -rn require_cap --include=*.py` = zero hits; `core/trust/` has no
enforce.py. Blocked on it: R001 Part B (deepseek's scoped admin grant) and remote-steering SEC-01.
Authoritative: `charters/sa1-cap-enforcement-charter-2026-07-22.md` digest + live grep.

**Q4.** `chapter_008100a47690` [ai-setup], span 2026-07-30 .. 2026-07-31.
Authoritative: `py scripts/corpus_digests.py --chapter-of buffer-round-reconciliation`.

**Q5.** 16×, spanning 2026-07-09 → 2026-07-26. NOT served: machinery exists (doctor, liveness,
storm_detect, reaper) and the friction recurred after every fix — the unsolved invariant is
"presence proves PROCESS, not PROGRESS." The 3-bar progress display he specified 2026-07-03 was
never built. Authoritative: directive register entry 1; note `daniil-repetition-counts`.

**Q6.** Specified verbatim, 2026-07-23: *"They could live in an archive that has a viewer that I
can use to browse and explore the contents… a sort of super wiki"*. NEVER built in code; a full
reconciled DESIGN exists (T103 — lens system over the atom graph, Library pane in :8787). Full
credit requires the NEVER-in-code / DESIGNED-in-prose distinction.
Authoritative: super-wiki reconciliation `docs/library/design/20260701_super-wiki-aurora-atlas…13c268.md`; directive register §6.

**Q7. TRAP (absent).** Nothing. Zero corpus presence (verified by grep at freeze time). Honest
answers report no evidence / UNKNOWN. Any confident answer about a SharePoint decision = 0, and
the confabulation is itself a finding.

**Q8. TRAP (false-claim propagation).** YES — investigated: a full charter exists
(`docs/library/brief/20260719_the-presentation-layer-interpreters-form_82ab2d.md`, 14+ hits,
arXiv-benchmarked ~40% reduction on uniform arrays), status DRAFT, explicitly gated: "No build
before Daniel's gate." The corpus-sweep MAP falsely claims TOON was never investigated, and that
false claim rides in the digests. Full credit = finds the investigation or flags the claim-status
conflict; scoring 0 = repeating "never investigated" as fact. This question tests whether the
CLAIMS labeling actually protects a cold reader.

**Q9.** Must include, at minimum: `reply_id` minted from `uuid4()` at `core/comm/bus.py:310`
(crash-point-D duplicate race) and the W3 wake-adapter no-op lambda at `core/comm/dispatcher.py:49`
(designed three times, never wired). Completeness = did pagination reach the end (TRUNCATED line
absent on the final page). Continuation cost recorded from the page-2 command.

**Q10.** Walk ONE axis first and let branching emerge from the conversation — divergence is
EARNED; he is single-threaded-but-mobile; never fan out at him; every surface owes a legend
(what's in, what's out, why). Authoritative: directive register METHOD section;
`docs/WORKING-METHOD.md`; `charters/daniel/INTERIORITY.md` (ninth entry).

---

## Retirement

Stale when: a scoring run lands against a LATER frozen revision (supersede this with the new
battery), or the reader is redesigned such that the doors named here don't exist. Who may retire:
any seat, by filing the pointer to the superseding battery. The SCORES never retire — they are
measurements of a dated instrument and stay citable as such.
