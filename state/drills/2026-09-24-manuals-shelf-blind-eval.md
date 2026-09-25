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
