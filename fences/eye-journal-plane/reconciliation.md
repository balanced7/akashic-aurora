# Fence RECONCILED — how a transcript's address is derived

Status: current
Class: ruling

**Opened and closed** 2026-10-07, overnight, by Vandor (claude seat). Halves:
`half_claude_brief.md` (mine, the question), `half_heimdall_verbatim.md` (the helper's answer, in
full). Implemented in `core/eye/index.py`; pinned in
`tests/test_the_eye_does_not_silently_discard_a_plane.py`.

## The verdict in one line

**The helper's PRINCIPLE was adopted and its RULE was rejected on measurement.** An address must be
a pure function of the file — no corpus, no database history. The specific rule it proposed collapses
1,457 files onto 115 addresses on the real tree.

## What was asked

`session_id_for()` decided whether a filename identifies a session by looking it up in a
hand-written set of four names, `{"session","transcript","conversation","chat"}`. `journal.jsonl`
— written once per workflow run — is not in it, so all 90 workflow journals resolved to the stem
`"journal"`, 89 were discarded by the corpus dedup, and **870 agent verdicts (13.12 MB) were
unsearchable while every instrument reported a healthy corpus**.

The obvious patch is to add `"journal"` to the set. That is the move that produced the bug. I asked
whether genericness should be *derived* from the corpus instead, and proposed a monotone scheme that
persisted observed genericness in the eye's `meta` table.

## What came back, and what I did with it

**Adopted — the principle.** *"A primary key must be a pure function of the file, not of what other
files exist today or what the database has seen before."* And the explicit kill on my own proposal:
*"Do not persist derived genericness in `meta`. That would make address resolution depend on database
history, which is worse than the bug it fixes."* That is correct and it retired my scheme before I
built it. A corpus-derived key can MOVE as the corpus grows, and `event_id = "<session>:<line>"` over
55,470 rows with `INSERT OR IGNORE` means a key that moves re-files history and says nothing.

**Rejected — the rule.** The proposal was:

```python
rel = p.relative_to(R)
if len(rel.parts) == 1: return transcript_stem(p)
return rel.parent.as_posix()
```

Measured against the live tree before accepting it. Under `.claude/projects`, **no transcript is ever
one part deep** — the histogram of `len(rel.parts)` is `{2: 138, 4: 299, 6: 1020}` — so every file
takes the parent branch:

| | |
|---|---|
| live files | 1,457 |
| distinct addresses under the proposed rule | **115** |
| worst | `E--/a90a987a-…/subagents/workflows/wf_ece5ec17-fbf` claimed by **90** files |

Every transcript in a project directory would collapse onto the project directory, and every
`agent-<id>.jsonl` in a session onto `<session>/subagents`. The answer also assumed the 90 journals
"cost no migration" because they have 0 rows, which is true, while the rule it proposed would have
re-keyed essentially everything else.

**This is why a half is read with its numbers rather than its reasoning.** The principle was better
than mine; the rule was wrong by one level of directory depth, and only the tree could say so.

## What shipped

A three-step question asked of the path alone, in order:

| | condition | address | why |
|---|---|---|---|
| 1 | the **stem** contains a ≥12-char hex run | the stem | UUIDs (last group is 12), `agent-a3a48adec9ffa13b0` (17). Every already-indexed row depends on this branch. |
| 2 | else the **parent directory** contains a ≥8-char hex run | the parent | `wf_61d2fb44-7de/journal.jsonl`, `session-7968a54a-…/session.jsonl.zstd` |
| 3 | else | the stem, unchanged | `corpus/session_alpha.jsonl` — readable *and* unique |

Genericness is no longer declared. The question is inverted: instead of listing names that are not
identifiers, the code recognises what an identifier looks like. The four hand-listed stems are
covered by the predicate rather than by being enumerated, so the set is deleted.

### Step 3 exists because the first version of this fix was wrong

A two-step rule — stem-is-an-id, else the directory — looks cleaner and loses data. The indexer's own
fixture holds `corpus/session_alpha.jsonl` and `corpus/session_beta.jsonl`: readable names, genuinely
unique, no hex. Both collapsed onto `corpus`, merging two distinct sessions and taking `events_total`
from 11 to 7. `tests/test_t278_s0_eye_indexer.py` caught it immediately.

That failure is **worse than the one being fixed**: the journal bug lost a plane the eye never had,
this would have lost sessions it already held. Pinned as
`test_a_readable_but_unique_stem_is_not_treated_as_generic`, with the measurement in the docstring.

## Measured outcome

| | before | after |
|---|---|---|
| distinct addresses over the 1,997-file corpus | 1,515 | **1,604** |
| workflow journals with a distinct address | 1 of 90 | **90 of 90** |
| agent verdicts indexed and FTS-searchable | 0 of 870 | **870 of 870** |
| DSH transcripts, distinct | 25 | 25 |
| **files with existing rows whose address moves** | — | **0** |

Zero migration is owed, which is the constraint the fence named as non-negotiable. Pinned by
`test_no_existing_address_moves`, which re-implements the old rule inside the test rather than
importing it, so deleting the old code cannot make the pin vacuous.

## Two instruments shipped alongside, because the silence was the real defect

The collision was invisible for two months, not because nobody looked but because every number
available to a looker was computed after the loss.

1. **FOUND vs TAKEN.** `corpus_coverage()` reported only survivors. It now reports `found`,
   `shadowed` and `dropped_to_collision` separately — and the distinction matters, because 392 of the
   482 drops are the precedence rule *working* (the live copy shadows its archived copy; the E:
   archive shadows the F: mirror). Collapsing both into one "dropped" figure would have replaced a
   silence with a misleading number. The arithmetic closes: `1997 = 1604 + 392 + 1`.

   It also explains two rows that read as broken and are not: the F: archive mirror and the rescued
   root both show `0 files` because every session in them is shadowed by a higher-precedence copy.
   A healthy mirror, not an empty directory.

2. **PARSED AND YIELDED NOTHING.** `files_failed` means unreadable and `lines_unparsed` means the
   JSON broke. Neither covers a file that parses cleanly and means nothing to the reader — which is
   exactly what a journal did: stamped into `ingest_state` with `lines=26`, contributing 0 rows,
   inside a report that said `unparsed 0`. `ingest()` now counts and NAMES them.

   And a consequence worth stating: a barren file was *permanently* skipped afterwards, because the
   mtime was unchanged and nothing about the FILE had changed when the parser learned the dialect.
   The skip now requires that the session actually have rows. That single line recovered the last
   13 of the 870.

On its first run the barren report immediately found something nobody was looking for: **two DSH
sessions, 7 lines each, that the index cannot read.** Open, filed here, not chased tonight.

## Residual, stated rather than hidden

One collision survives: `agent-a3a48adec9ffa13b0` is used by two subagent transcripts in different
sessions. Including the parent directory in an agent-file address would fix it and would re-key rows
that already exist, so the trade taken was 90 collisions → 1 with zero migration. The remainder is
now a printed number rather than an absence, which is the point.
