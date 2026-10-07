# Contract B's acceptance test, RUN — and it fails

Status: current
Class: report
Arc: filing-schema

**Run** 2026-10-07 overnight by Vandor (claude seat), against Daniel's standing instruction:

> "See if you can't continue working on making our best knowledge reach us when we need it or at
> least be easy to find."

## Why this test existed and had never been run

`fences/filing-schema/reconciliation.md` §6 says, in full:

> **Contract B is UNTESTED, and that is a result.** Rill's outside-reader file never landed. He was
> live and idle throughout and was asked twice. His piece was not decoration: **it *was* Contract B's
> acceptance test** — can a seat that has never seen this tree retrieve the Wave-0 build spec by what
> it is about, in one command? Nobody answered that, so B carries no evidence either way and must not
> be built on the strength of the census alone.

So the verdict "unproven, do not build" was never a measurement. It was an absence. The test is cheap
and nobody had run it.

**I cannot be the reader.** I know where the file is, so any attempt of mine measures my memory and
not the retrieval system. The test needs a cold seat, and to make a single cold seat's luck
non-decisive it was run **twice, independently, with different phrasings**, neither reader knowing of
the other, neither told it was a test of anything, neither given the filename, the folder, the word
"fence", or the word "reconciliation" — only what the document is *about*, which is the test's own
wording.

**The target:** `fences/context-system/reconciliation.md`, whose H1 is
*"Reconciliation -- context-system (the Wave 0 build spec)"*.

## The result

**Contract B FAILS.** Both readers found it. Neither found it in one command, and — the part that
matters — **neither found it by searching for it.**

| | Reader A | Reader B |
|---|---|---|
| `agent_cli` invocations to a printed path | **15** (6 of them `--help`) | **11** |
| first *named* at | invocation 5 | invocation 6 |
| how it was first named | a **note body quoting the path** | a **decision note quoting the path** |
| the document as a result ROW | **never** | **never** |
| same near-miss briefly believed | `docs/context-system.md` | `docs/context-system.md` |

Both reached the authoritative document only because unrelated prose happened to cite it. That is not
retrieval; it is a citation surviving in a neighbouring corpus.

## The root cause, found independently by both readers

> **The `fences/` plane is in no searchable corpus.**

- `lookback --layers` offers `docs,research,notes,promoted,chapters,git`. There is no `fences` layer.
- `knowledge-map` walks lessons, notes and docs. There is no `fences` corpus.

These are the two doors that look purpose-built for "find the document that decided X", and **the
house's 21 sealed reconciliations are structurally unreachable as result rows from either.** A
reconciliation is the most authoritative artifact this house produces — it is where a contested
question is *settled* — and it is the one class of document no retrieval verb indexes.

That is the answer to the question Daniel has been asking since 2026-10-01. Our best knowledge does
not reach us because our best knowledge lives in `fences/`, and nothing looks there.

**It was already measured once.** Reader A noticed a row surfaced by its own `knowledge-map` call —
`docs/library/report/20261001_first-pass-easy-vs-thorough` — independently reporting *"other-plane
reach 0/62"* and *"`eye find` returned 0 hits"*. So the gap had been quantified before, recorded, and
nothing followed. The finding reaching the corpus is not the same as the finding reaching a fix.

## Five further defects, each found by both readers or cited with evidence

1. **`fence status` and `fence list` know the document and will not say where it is.** Both readers
   got `reconciliation SEALED by claude`, `closed: True`, and the round's question — and no path. The
   fence door holds the authority and withholds the address, so both had to cross to a different verb
   to turn a confirmed document into a file they could open.

2. **`find`'s ranking is still biting after tonight's fix.** Reader A ran
   `find reconciliation --path --limit 25` and got **25 rows with ZERO from the live repo** — every
   hit a stale Everything-index copy under `C:\Users\L5\.codex\worktrees\...` or `X:\wt-baseline-...`,
   which look exactly like the repo at a glance. It cites W255 (the `--sort` defect fixed earlier
   tonight) by name: the re-sort is gone, but **name-sort plus `--limit` still truncates the live
   repo out of the result set before relevance is ever consulted.** Reader B saw the same shape:
   rank 8 of 186. The fix closed the inert-sort half and not this half.

3. **`recall` is the most search-sounding verb in the house and is lesson-only.** Reader A's query
   returned **512 loosely-matched lessons** and tens of thousands of tokens of unrelated prose, plus a
   `[title-miss]` nudge toward `knowledge_full(source=...)` — which presupposes you already hold the
   pointer you are searching for.

4. **`eye find` reads as full-text over everything and indexes only session JSONL.** On the obvious
   query it billed **~98k tokens** and found nothing on topic. Reader A names the noise as
   "workflow-result" rows — **which is the plane I added to the eye three hours earlier tonight.** An
   honest cost of that work: 870 verdicts made the transcript plane richer and `eye find` noisier, and
   nothing yet lets a caller scope a query away from them.

5. **`notes --all | Select-String` returns nothing and exits 255.** Reader B took the silence for "the
   note does not exist", then re-ran and found 1,889 notes: the listing is truncated line-by-line and
   the shell pipe kills the process early (AGENTS.md RB-28). A grep over this verb's stdout is
   unreliable, and its failure mode is a confident empty result.

Minor, noted not chased: `fence pv context-system` reports "3 MISSING" while that reconciliation's own
§5 is headed "the four MISSING citations".

## The decoy is worth its own paragraph

Both readers briefly settled on `docs/context-system.md`, and it is instructive that they did. It is
`Status: current`, typed `contract`, carries arc `context-system`, names all four remembered items, and
is reinforced from three directions (a `knowledge-map` doc row, `lookback`'s top git row, and a library
atom). It reads exactly like the answer.

It is not. It is the W0.7 *contract* — the after-the-fact status table — which the reconciliation
itself ordered built, and its own second paragraph points at the real document: *"Build spec:
`fences/context-system/reconciliation.md` section 4."*

So the filing schema's own machinery (status, type, arc) ranked the derived document above its source,
and the only thing that corrected both readers was the derived document being honest enough to cite
upward. That is a property of how that file happened to be written, not of the retrieval system.

## Verbatim reports

Both readers' reports are reproduced below in full, unedited, per the full-fidelity preservation rule.
The synthesis above is disposable; these are the evidence.

---

### Reader A — verbatim

#### 1. Commands run, verbatim, in order

```
py agent_cli.py --help
py agent_cli.py discover
py agent_cli.py knowledge-map --help
py agent_cli.py lookback --help
py agent_cli.py knowledge-map context system
py agent_cli.py lookback "what did we agree to build first for the context system"
py agent_cli.py context --help
py agent_cli.py eye --help
py agent_cli.py eye find "Wave 0"
py agent_cli.py fence --help
py agent_cli.py find --help
py agent_cli.py fence status context-system
py agent_cli.py fence pv context-system
py agent_cli.py find reconciliation --path --limit 25
py agent_cli.py find "context-system" --path --limit 40
wc -c fences/context-system/reconciliation.md docs/context-system.md
grep -n "^#" fences/context-system/reconciliation.md
grep -n "^#" docs/context-system.md
sed -n '1,30p;76,135p' fences/context-system/reconciliation.md
sed -n '1,20p;110,140p' docs/context-system.md
py agent_cli.py recall "context system build first wave 0"
head -12 fences/context-system/addendum-2026-10-02-the-fold.md
```

(The `--help` and the `wc`/`grep`/`sed` reads were issued paired inside single shell calls; listed
separately for the record. No raw filesystem *search* was used at all — `grep`/`sed`/`wc` only ran
against two files the repo's own doors had already named.)

#### 2. Did the target appear, and where

| Command | Target in output? |
|---|---|
| `--help`, `discover` | N/A — verb inventory only |
| `knowledge-map context system` | **Indirectly, position 8 of 18** in the L1 surface list. The target itself is NOT a result row; row 8 is the note `current-directive`, whose body quotes `fences/context-system/reconciliation.md` section 4 with the slice list "W0.1 target schema, W0.2 touch, W0.3 eval set, W0.4 stats, W0.5 scene, W0.6 door" — an exact match for the four things remembered. The decoy `docs/context-system.md` appeared as a real row at position 16 of 18. |
| `lookback "what did we agree to build first..."` | **NOT FOUND.** No layer returned it. Its `git` layer row 1 (`b4015aa4`) pointed at `docs/context-system.md` instead. |
| `eye find "Wave 0"` | **NOT FOUND.** 20 of 53 transcript hits, ~98k tokens priced, nothing on topic. |
| `fence status context-system` | **Partially — confirmed, no path.** Printed the round's question plus `reconciliation SEALED by claude`, `closed: True`. Established the document exists and is authoritative, but printed no filename. |
| `fence pv context-system` | NOT FOUND (citation audit only: 20 verified, 3 MISSING). |
| `find reconciliation --path --limit 25` | **NOT FOUND.** 25 rows, not one from `E:\AI-Setup`. |
| `find "context-system" --path --limit 40` | **FOUND, position 16 of 40**: `E:\AI-Setup\fences\context-system\reconciliation.md`. |
| `recall "context system build first wave 0"` | **NOT FOUND.** 512 fuzzy lesson matches, zero documents. |

#### 3. The answer

**`fences/context-system/reconciliation.md`**

Its H1 is literally "Reconciliation -- context-system (the Wave 0 build spec)"; section 2 is titled
"Build first, and what is refused" and section 4 is the Wave 0 build-spec table whose rows are W0.1
`context.target.v1` (the canonical spelling of a code location — EBNF, `file:<path>:<line>`, `dir/`,
refs), W0.2 the touch (`capture(kind="touch", ..., session_id=)` from the Claude hook), W0.3 the eval
set (40 blind moments + `recall-bench`), W0.4 the instrument (`context --stats`). The confirming
cross-check is that the decoy, `docs/context-system.md`, points *at* it: "Build spec:
`fences/context-system/reconciliation.md` section 4, as folded by `fences/one-spine/reconciliation.md`."

Two related-but-not-the-answer documents: `docs/context-system.md` (the W0.7 contract written after
the build, with a done/blocked status table) and `fences/context-system/addendum-2026-10-02-the-fold.md`
(dated addendum folding the `one-spine` round in, since sealed text is never edited).

#### 4. Command count

**15 `agent_cli` invocations** to the printed path, of which 6 were `--help`. First *named* at
invocation 5 (`knowledge-map`, inside a note body); path printed at invocation 15 (`find
"context-system" --path`). By substantive query: 2nd query named it, 8th query printed its path.

#### 5. What actively misled me

- **The fence plane is in no searchable corpus.** `lookback --layers` offers
  `docs,research,notes,promoted,chapters,git`; `knowledge-map` walks lessons/notes/docs. There is no
  `fences` layer in either, so the house's 21 sealed reconciliations — including this one — are
  structurally unreachable as result rows from the two doors that look purpose-built for "find the
  document that decided X". Both only reached it through prose *quoting* the path inside a note. (A
  `docs/library/report/20261001_first-pass-easy-vs-thorough` row surfaced by the same `knowledge-map`
  call independently reports "other-plane reach 0/62" and "`eye find` returned 0 hits", so this is a
  known, measured gap.)
- **`recall` is the most search-sounding verb and is lesson-only.** It returned 512 loosely-matched
  lessons and tens of thousands of tokens of unrelated prose, plus a `[title-miss]` nudge toward
  `knowledge_full(source=...)` that presupposes you already hold the pointer you are searching for.
- **`eye find` reads as full-text search over everything** ("the transcript plane as terrain") but
  indexes only session JSONL. On the obvious query it billed ~98k tokens of workflow-result noise and
  found nothing.
- **`find reconciliation --path --limit 25` returned 25 paths with zero from the live repo** — every
  hit was a stale Everything-index copy under `C:\Users\L5\.codex\worktrees\e5d8\AI-Setup\fences\...`
  or `X:\wt-baseline-682c5cf8\...`, which look exactly like the repo at a glance and would have had me
  reading a worktree. Cause is name-sort plus `--limit`, not relevance; the unlimited query on a
  narrower term put the real file at row 16. A lesson already in the store (`find --sort and every
  --preset are silently inert, because _rank_exact_first re-sorts results after es.exe returns them`,
  W255) describes this ranking defect.
- **The near-miss decoy was `docs/context-system.md`**, reinforced from three directions: a
  `knowledge-map` doc row, `lookback`'s top git row (commit `b4015aa4`, "W0.7: the context system
  contract"), and a library atom `docs/library/contract/20261002_context-system_de056e.md`. It names
  all four remembered items, so it reads as the answer — but it is the after-the-fact reader's
  contract (status table of what is done), not the agreement on what to build first.
- Minor inconsistency, not a mislead: `fence pv` reports "3 MISSING" while the reconciliation's own
  section 5 is headed "the four MISSING citations". Nothing was changed, written, or committed.

---

### Reader B — verbatim

#### Answer

**`fences/context-system/reconciliation.md`** (absolute:
`E:\AI-Setup\fences\context-system\reconciliation.md`)

Line 1 reads "Reconciliation -- context-system (the Wave 0 build spec)"; it was written by claude
(Vandor) on 2026-09-30 after three independently fenced halves were sealed (Heimdall `half_a`, Navi
`half_b`, Sunshine `half-sol`, plus the brief and Daniel's addendum), and its 45 verdict lines each
assign a slice to Wave 0 / Wave 1 / Wave 2 / Wave 3 with four "BUILD FIRST" items — i.e. exactly
"which pieces get built in the first round versus later rounds" for how an agent's working context is
assembled.

#### 1 & 2. Commands in order, and whether the target was in the output

| # | Command (verbatim) | Target in output? |
|---|---|---|
| 1 | `py E:\AI-Setup\agent_cli.py --help` | NOT FOUND (verb list only) |
| 2 | `py E:\AI-Setup\agent_cli.py discover` | NOT FOUND (112 verbs + purposes only) |
| 3 | `py E:\AI-Setup\agent_cli.py knowledge-map -h` | n/a (usage text) |
| 4 | `py E:\AI-Setup\agent_cli.py lookback -h` | n/a (usage text) |
| 5 | `py E:\AI-Setup\agent_cli.py knowledge-map how an agent working context is assembled` | NOT FOUND. 18 surface + 14 archive hits, none the target. Nearest: `docs/ARCHITECTURE.md` (doc rank 4 of 6) whose snippet says "core/context/ boot context assembly"; archived note `where-we-are-2026-10-02` (archive rank 7) mentioning "W0.1 context.target.v1" |
| 6 | `py E:\AI-Setup\agent_cli.py lookback why did we decide what goes into wave 0 of the context system and what waits for later` | **FOUND, as a citation, not as a row.** The notes layer's **rank 2** hit (`mem:decision:ADR_1001232645_0350fb9e`) names `fences/context-system/reconciliation.md` section 4 verbatim. The file itself was never a listed hit. `docs/context-system.md` appeared at docs **rank 3**, and it in turn points at the reconciliation |
| 7 | `py E:\AI-Setup\agent_cli.py fence -h` | n/a (usage; revealed that `reconciliation` is one of four fence slots) |
| 8 | `py E:\AI-Setup\agent_cli.py notes --all 2>&1 \| Select-String -Pattern "ADR_1001232645_0350fb9e" -Context 0,40` | NOT FOUND — returned no output at all |
| 9 | `py E:\AI-Setup\agent_cli.py fence list` | Partially: `[CLOSED] context-system (full) ... sealed: brief,half_a,half_b,reconciliation` at **rank 3 of 24** (alphabetical). Confirms the round and its sealed write-up, prints no path |
| 10 | `py E:\AI-Setup\agent_cli.py fence status context-system` | Confirms `reconciliation SEALED by claude`, plus the round's question. Still **no filesystem path** |
| 11 | `py E:\AI-Setup\agent_cli.py find reconciliation.md` | **FOUND at rank 8 of 186**: `E:\AI-Setup\fences\context-system\reconciliation.md` |
| 12 | Read `E:\AI-Setup\fences\context-system\reconciliation.md` (lines 1-80) | Confirmed the answer |
| 13 | Read `E:\AI-Setup\docs\context-system.md` (lines 1-60) | Confirmed it is the downstream contract, not the write-up |
| 14 | `py E:\AI-Setup\agent_cli.py notes --all 2>&1 \| Select-Object -First 15` | Diagnostic for #8 — the verb does print 1889 notes, so #8's silence was a real non-match / truncated stream, not an empty store |

No ordinary grep/find was needed. Command 11 used the repo's own `find` verb (Everything index), not a
filesystem sweep.

#### 3. Conclusion and confidence

`fences/context-system/reconciliation.md` — it is the sealed reconciliation slot of the CLOSED
`context-system` fence (a four-slot brief/half_a/half_b/reconciliation debate structure), its own title
calls it the Wave 0 build spec, and the contract doc `docs/context-system.md` cites it as the authority
for the build order.

#### 4. Command count

**11 repo-verb commands** got me from nothing to the path (the path first surfaced at command 6, was
confirmed on disk at command 11). Plus 2 file reads to verify and 1 diagnostic re-run = 14 steps total.

#### 5. What misled me

- **`knowledge-map` was the obvious-looking verb and returned nothing useful.** It walks
  lessons/notes/docs and gave 32 hits across three layers without the target, even though the target
  sits in `fences/` — the fence corpus appears not to be in its index. Rephrasing would not have
  helped; it does not look where the answer lives.
- **`lookback` found it only by accident of citation.** The hit was a decision note that happened to
  quote the path. `lookback`'s own layer list (`docs,research,notes,promoted,chapters,git`) has no
  `fences` layer, so the authoritative document is unreachable as a row in the one verb built for "the
  strategic WHY".
- **Near-miss I briefly believed: `docs/context-system.md`.** It is current, typed `contract`, arc
  `context-system`, and names the wave assignments and seats — it reads like the answer. It is not: it
  is the Wave 3 contract stub that the reconciliation itself orders built (verdict V32), and its own
  second paragraph says "Build spec: `fences/context-system/reconciliation.md` section 4".
- **`fence status` / `fence list` name the slot but never print its path.** I had to cross to the
  `find` verb to get a filesystem location for a document the fence door fully knows about.
- **`notes --all | Select-String <id>` returned absolutely nothing** for an id `lookback` had just
  printed, which read as "the note does not exist". Re-running with a different pipe showed 1889 notes
  and exit code 255 — the listing is truncated line-by-line and the shell pipe terminates the process
  early (the repo's AGENTS.md warns about truncating pipes, RB-28). A grep over this verb's stdout is
  unreliable.
- `find reconciliation.md` returned 186 matches because worktrees, `X:\` scratch, `E:\AI-Setup-publish`
  and temp fence dirs all carry same-named files; the canonical one is 8th and only recognizable by
  its parent directory.

Nothing was modified, no files written, no commits.
