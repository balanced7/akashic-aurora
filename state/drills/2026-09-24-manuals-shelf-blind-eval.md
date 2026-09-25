# EVAL RECEIPT — the manuals shelf on Apple's HIG and Samsung's One UI (blind questions)

**Date:** 2026-09-24, about 23:00 EDT
**Organ:** `core/manuals` + `manual search|ingest|list` (CLI and MCP), built tonight on Daniil's
"find the apple ui design documentation and the oneui documentation and use that to test and build these features"
**Corpora (local only, git-ignored, copyrighted):**

| Shelf | Documents | Passages |
|---|---|---|
| apple-hig | 172 DocC pages | 1,752 |
| one-ui (live site) | 37 pages | 129 |
| one-ui-2019-pdf (legacy guide plus its landing page) | 2 | 111 |

All 1,992 passages were embedded with the house's cached all-MiniLM-L6-v2. Nothing was downloaded to do it.

## Method

A separate agent wrote **40 questions**: 26 answered by Apple across 22 pages, and 14 answered by One UI across
12 pages. It read the raw source documents and never touched the search, the index or `core/manuals`. It wrote
each question in its own words, avoiding the section's heading and distinctive phrases, and recorded the answering
page and section. The file stays in the session scratchpad because it names vendor headings.

The scoring script counts four things:

- **page hit@k:** a top-k passage comes from the answering page;
- **section hit@k:** a top-k passage is the answering section;
- **MRR:** the average of 1/rank;
- **context:** the characters an agent reads.

## Results (limit 5, default 6,000-char cap)

| setting | mode | page @1 | page @5 | section @1 | section @5 | MRR page |
|---|---|---|---|---|---|---|
| all shelves at once | keyword | 72% | 85% | 57% | 78% | 0.79 |
| all shelves at once | hybrid | 78% | 92% | 60% | 82% | 0.84 |
| scoped to the right manual | keyword | 88% | 95% | 70% | 80% | 0.90 |
| **scoped to the right manual** | **hybrid** | **92%** | **98% (39/40)** | **72%** | **88%** | **0.94** |

Scoped hybrid broken down by shelf: Apple reaches 100% page @5 (96% @1). One UI reaches 93% page @5 (86% @1).

**Context.** An agent reads a median of about 1,360-1,440 tokens of passages per question. The answering page alone
is about 2,480 tokens. The whole Apple guide is about 432,000 tokens (1.73M chars) and One UI about 16,000.

**Latency.**

| Mode | Time per question |
|---|---|
| keyword | about 5 ms |
| hybrid, warm | about 25 ms |
| hybrid, first call in a process | about 5 s, one time, to load the model |

The MCP door loads the model once per server process.

## What the eval caught (each fixed with a red pin first)

1. **Every Apple passage linked to raw JSON.** The crawler's manifest records data urls, and the shelf preferred
   them over the page identifier. The first run scored Apple 0 of 26 for that reason. Pin 40bb4d65, fix 81931a22.
2. **My own harness bug.** The scorer built the shelf without a model, so "hybrid" silently ran as keywords. The
   note that said so was in the result, but I was not printing it. The shelf's fallback note did its job; the
   harness ignored it.
3. **Integration faults found while shelving, before the eval ran:**
   - Several One UI pages named `intro.html` got another page's url; now fixed with mirror urls.
   - The `_root.html` landing page was skipped.
   - A tight cap dropped the second passage instead of trimming it.
   - The landing page repeated the overview, so the same passage came back twice.

   Pins ce13e474 and 53d6898a, fixes ec7058d8 and b8eea84b.

## Fence (DeepSeek, verbatim)

`py agent_cli.py ask`, deepseek-v4-pro, 8796+11140 tok, 183 s, on `core/manuals/shelf.py` and `chunk.py` at
603b351a:

> 1. BLOCKER — Hybrid search materializes every vector row and builds a full dense matrix per query: `rows = c.execute(...).fetchall()` then `mat = np.frombuffer(b"".join(...)).reshape(len(rows), -1)` (shelf.py:394-401). This is unbounded memory/time on a large shelf.
> 2. BLOCKER — `_embed_missing` fetches all missing chunk texts into memory before batching: `todo = c.execute(...).fetchall()` (shelf.py:230-232). First/upgrade ingest on a large shelf is unbounded memory.
> 3. BLOCKER — A single over-long paragraph is split by repeatedly copying the whole remaining suffix: `while len(s) > max_chars: ... s = s[max_chars:]` (chunk.py:42-45). Worst-case quadratic time on a huge run-on paragraph.
> 4. OK — No query-string SQL/FTS5 injection: `terms_of` extracts only `\w+` and caps at 24, and `_bm25` quotes each term, strips embedded quotes, and binds MATCH as a parameter (shelf.py:173-181, 384-388); FTS errors are caught in `search` (shelf.py:427-430).
> 5. OK — Per-document replacement is atomic: `_drop_doc`, new doc/chunk/FTS inserts, and `c.commit()` happen before moving to the next file (shelf.py:324-340); failure rolls back one doc, not a half-replaced doc.
> 6. OK — `_drop_doc` deletes FTS rows, vectors, chunks, and the doc in one transaction (shelf.py:370-376), so deleted chunks do not leave stale FTS/vector rows.
> 7. OK — RRF and budget/dedupe are correct: standard `1/(RRF_K + rank)` fusion (shelf.py:437-440), rank order preserved after DB lookup (shelf.py:445-449), and the budget loop trims to remaining room and never exceeds `max_chars` (shelf.py:450-473).
> 8. OK — Concurrency is WAL-based; connections set `journal_mode=WAL`, and ingest commits only whole docs/batches (shelf.py:241-245, 233-238, 340). No other blockers found.

**Disposition (claude): all three blockers ACCEPTED and fixed.** At today's size they are harmless: the vectors
total about 3 MB. They grow with the shelf, though, and this is the night the machine died of memory.

- Vectors are scored in batches of `VECTOR_BATCH` (4096) with a running top-N heap.
- Embedding keeps only the ids in memory and fetches and encodes texts `EMBED_BATCH` (256) at a time.
- A run-on paragraph is cut by index in one pass.

Pins fffb8656, then the fix. 22 of 22 tests pass, and the blind eval is unchanged (scoped hybrid: 39 of 40 in the
top 5).

## NOT proven — read before trusting

1. **Retrieval, not answers.** This measures whether the right passage comes back. It does not measure whether an
   agent then answers correctly from it. That A/B (answer from the passages vs from the whole page vs from no
   manual) is the next test.
2. **Small, single-author sample.** 40 questions from one writer agent. One UI has only 14, so its percentages move
   about 7 points per question.
3. **Known weak phrasing.** "Minimum size of a tappable button" ranks Apple Pay's button-size rules first, because
   they share the literal words. The general 44-point guidance comes third. A wording closer to the manual
   ("touch targets") puts it first.
4. **Not evaluated:** the 2019 PDF shelf and cross-vendor questions.
5. **Runner seats have no door yet.** Navi and Heimdall cannot use the shelf until the ToolBox coverage slice lands
   (door-parity exemption recorded).
