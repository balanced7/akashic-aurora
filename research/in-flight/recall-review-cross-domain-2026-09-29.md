# Recall, reviewed with Daniel: cross-domain routing, accessibility, and what the manuals shelf taught us

**Filed** 2026-09-29 by Vandor (claude), as an opening position for a fence with Heimdall. Daniel's ask,
verbatim: "I want to run through our recall system with you. How are we doing on cross domain knowledge
routing and accessibility? What are the barriers to us accessing our best knowledge and how do we apply
our learnings from the PDF parser injest system to our broader knowledgebase?"

Every number below was measured today on this machine; the receipts are named. Where the PDF ingest
system is cited it means `core/manuals/` (the manuals shelf: `convert.py` + `shelf.py`, hybrid mode,
blind-evaluated 2026-09-24).

## 1. The measured state

**The corpus.** 1,526 lessons (`py agent_cli.py list --json`). 64% carry an explicit "Use when" trigger.
Categories: 822 (54%) `uncategorized`; the rest is free text (correction 110, architecture 73,
reliability 51, tooling 44, ...). The `domain` field has three values in the whole corpus: `system`
(758), empty (695), `vfx` (73). Success is self-reported `yes` on 91%.

**Cross-domain routing, mechanically.** `core/recall/at_action.py` D5: a lesson credited useful in >= 2
distinct domains becomes "general" and surfaces everywhere. Today the number of lessons that have
earned that status is in the reply below (measured through the module's own loader). With one real
domain label in the data, the ladder has no rungs: cross-domain promotion is designed and cannot fire.

**How recall-at chooses.** `_damped_overlap`: IDF-weighted keyword overlap between the action text and
each lesson's text, with a min-hits dampener, a trigger-aware pass, and a usefulness factor. Lexical
only. There is no embedding anywhere under `core/recall/` or `core/eye/`; the house's cached MiniLM
embedder (`core/primitives/embedder.py`) is used by exactly one consumer: the manuals shelf.

**What one session receives.** This session (2026-09-28/29): 913 recall-at firings; 2,184 lesson
entries, 492 verb blurbs (`find` 51x, `ask` 39x, `sha` 36x, `discord` 33x), 972 "age" lines, 669
"legend" lines. The most-surfaced "lesson" was a pseudo-source named `research` (78x) -- a naming
bug in source canonicalization. Votes cast by the reader in those 913 firings: zero.

**The feedback loop, this week.** `recall:outcome`: 7,219 rows in 7 days, every one with
`outcome: None` -- the ring records surfacings and auto-credits, no judgments. `recall:surface`: 1,313
rows, no source field. Useful/noise votes in the last 7 days: 0 / 0. Lifetime: 493 / 39, judged
532 of 23,123 surfacings (2.3%). The counters' own hygiene report: 18 zero-credit ghosts and 11
credited ghosts -- lessons whose sources no longer exist.

**The strong barrier.** `gate_rules.py` refuses at the door by a hand-written table of shapes
(`_mutates`, `_features_count`, `_features_door`, `_whole_command_readonly`, `table_hash`). No lesson
has ever been promoted into it (`state/recall/` is empty). The 2026-09-05 redesign said it plainly:
recall injection is a symbolic barrier, Hollnagel's second-weakest class, and the three slices that
would change that (S1 promotion ladder, S2 Eye-wired AAR + precision retirement, S3 expectancy priming)
exist as one proposed task, T392, and no code.

**Ground truth.** Recall has one measured-misses dossier (2026-08-08: 4 misses, funnel value 5.2%)
and one precision sample about orphan claims (20/20, a different question). It has no blind
evaluation set: no list of moments with a known right lesson, so `recall@5` cannot be computed and
every change to the trigger is argued rather than measured.

## 2. The barriers, ranked by how silently they fail

1. **Feedback starvation.** Retirement-by-precision, the usefulness factor and D5 all consume
   judgments; the reader gives none (0 in 913 firings tonight; 2.3% lifetime). A learning loop with
   no observations does not learn; it only grows. Silent, because the counters still print numbers.
2. **No domain axis in the data.** Three labels across 1,526 lessons. Nothing that keys on `domain`
   can route across domains. Silent, because the mechanism is present and green.
3. **Lexical-only matching.** The manuals shelf's first real miss was "tappable button" vs "hit
   target": a wording gap keywords cannot cross. Recall-at has the same gap and no meaning channel.
   The 08-08 misses (M1-M3) are wording-gap misses; M4 was the other shape: right topic, wrong moment.
4. **The query is the command, not the intent.** The shelf searches a question. Recall-at searches
   the Bash line. A moment is an intent plus an action; keying on the action alone is why verbs and
   filenames dominate what surfaces.
5. **No evaluation set.** The shelf shipped with 40 blind questions and a number (39/40 right page in
   the top 5). Recall shipped with a funnel. You cannot tune what you cannot score.
6. **Volume without cap.** ~3,600 injected items in one session, a third of them chrome ("age",
   "legend") and a seventh verb blurbs. The shelf caps answers by characters and names its
   denominator on a zero; recall-at does neither.
7. **Structure absent at write time.** A lesson is a flat record (what_tried / expected / actual /
   recommendation); a shelf chunk carries a title and its full heading path, weighted above the body.
   The lesson has no path (organ / subsystem / door), so nothing can route it by where it lives.
8. **Source hygiene.** A pseudo-source named `research` outranked every real lesson tonight; 29 ghost
   sources sit in the counters. Small, but it is noise at the top of the list.
9. **Worktree invisibility** (a lesson of its own: work done in a worktree is invisible to recall):
   the index follows the checkout, not the repository.

## 3. What the PDF ingest system did right, and how each carries over

| the shelf did | how it carries to the knowledge base |
|---|---|
| chunk by STRUCTURE: a Section is one heading's text plus its full heading path (PDF pages labelled by the outline) | give every lesson a PATH at write time -- organ / subsystem / door -- derived, not asked: from `--files-affected`, the seat's `focus` task, the cwd. The path becomes the `domain` axis D5 needs. |
| FTS5 with weighted columns (title, heading path above body) | one SQLite index over lessons (title + trigger + path weighted above the body) replacing the JSON cache in `%TEMP%` with a 120 s TTL |
| a question reduced to content words, quoted and OR-ed (syntax-proof) | the recall query becomes the INTENT: the seat's current task + the last operator sentence + the action, not the Bash line alone |
| HYBRID: BM25 + MiniLM fused by reciprocal rank fusion, with a similarity floor for meaning-only hits | the same fusion for recall-at, with the embedder that is already cached; the floor keeps the honest zero |
| embed once at ingest, store beside the text; PIPELINE_VERSION; incremental ingest | embed at `learn` time; re-embed on pipeline version change; no per-firing model load |
| answers capped by characters; a zero names what was searched | per-firing cap (3-4 items, chrome once per session); a silent firing says what it searched |
| 40 blind questions -> "right page in the top 5 for 39/40" | 40 blind MOMENTS with a known right lesson (the 08-08 misses, the flips, tonight's lessons) -> recall@5 and precision@3 printed on every change; retire triggers that never hit |
| a shelf is a named collection; search can be scoped to one | verbs are their own shelf, searched only when the seat types a verb it has not used this session; lessons are the other |

And the one the shelf did NOT need but recall does: **objective outcomes instead of votes.** The shelf's
score is "right page in the top 5" -- ground truth without asking the reader. Recall's analog is the
redesign's S2: did the seat's next action follow the recommendation (the recommended command ran
within N minutes; the file the lesson names was touched; the pin it cites was run)? That is readable
from the ledger, and it is the only feedback source that does not depend on a reader who casts zero
votes in 913 firings.

## 4. The build order this position proposes (each slice claude+Heimdall fenced, with a receipt)

1. **The eval set** (small, first, because everything after it needs a number): 40 moments with a
   known right lesson; a bench verb prints recall@5 / precision@3 / chrome share for the current
   trigger. Receipt: the baseline number.
2. **Paths at write time** (small): `learn` derives organ / subsystem / door; a backfill pass over
   the 1,526 from `files_affected` and the ledger; `domain` stops being three labels.
3. **The index** (medium): lessons into the shelf's engine (SQLite FTS5 + stored embeddings, hybrid
   with RRF and a floor); recall-at reads it; the `%TEMP%` cache goes. Receipt: the eval number moves.
4. **Intent queries and caps** (small): query = task + last operator sentence + action; 3-4 items
   per firing; chrome once; verbs as their own shelf.
5. **Objective outcomes** (medium, the redesign's S2): the Eye-wired AAR credits a lesson when the
   next actions follow it; precision retirement runs on that record; the 29 ghosts go.
6. **Promotion to gates** (the redesign's S1): a lesson with a `refusal_shape` that keeps earning
   objective credit becomes a door rule. The symbolic barrier becomes a functional one.
