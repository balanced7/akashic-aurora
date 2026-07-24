---
akashic_id: art_20260710_p7-lookback-corpus-inventory-deepseek-ve_f5fc91
akashic_sha: cc754324da9f
status: draft
type: report
date: 2026-07-10
title: P7 lookback corpus inventory -- DeepSeek (verbatim)
gist: "# P7 lookback corpus inventory -- DeepSeek (verbatim) Delivered as the T026 ack-drill handoff answer (auto-ack proof) + P7 seat 1. --- Now I"
tenant: solo
visibility: fleet
seats: []
category: [bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_the-comprehensibility-immune-system-desi_339b01
    rel: cites
created: "2026-07-10T00:01:24"
updated: "2026-07-23T21:42:14"
---
<!-- GENERATED PROJECTION of art_20260710_p7-lookback-corpus-inventory-deepseek-ve_f5fc91 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# P7 lookback corpus inventory -- DeepSeek (verbatim)

# P7 lookback corpus inventory -- DeepSeek (verbatim)

Delivered as the T026 ack-drill handoff answer (auto-ack proof) + P7 seat 1.

---

Now I have all the pieces. Here's the compact reply:

---

## T026 Ack Drill / P7 Pre-read: Rationale Corpora Inventory

### (1) Rough Record Counts

| Corpus | Count | Storage |
|---|---|---|
| **docs/*.md** (~80 files) | ~75 dated designs + ~12 LIVING (`UPPERCASE.md`) | Git-tracked files |
| **research/reviewed/*.md** | 42 fenced review/redteam docs | Git-tracked files |
| **Note bodies** (Akashic Aurora `knowledge_note`) | 10–15 live (peak from onboarding: 8 shown, plus archived supersedes) | `knowledge_note` → Store (`narr:note:*` or similar) via `core/narrative/` |
| **Promoted bus messages** | ~hundreds (salient `handoff`/`decision`/`completion`/`blocker` kinds, plus console interjections/controls/drops) | Persisted as `bifrost_msg` events in the raw firehose (EventLog + EventIndex), queryable via `promoter.promoted()` |
| **Chapter summaries** (narrative spine) | ~26 `ai-setup` + ~4 `research` + ~1 `vision` = **~31 chapters** across 3 tracks per story.index.json | Store: `narr:chapter:<id>`; rendered to `chronicles/story.index.json` |
| **Git log bodies** | ~hundreds since 2026‑06 (the project's active window) | Git ODB (read via `git_log`/`git_show`) |

**Total estimable records searchable**: ~80 + 42 + ~15 + (hundreds) + ~31 + (hundreds) ≈ **roughly 400–800 searchable rationales**, depending on promoted-message and git-log density.

### (2) WHY Density — Which Corpus Answers Architectural-Why Best?

Three tiers:

1. **docs/*-design-*.md / *-research-*.md / *-plan-*.md** (~55 lowercase docs) — **THE highest WHY density.** These are the point-in-time design records. INDEX.md explicitly says: *"They explain why, not now."* Example: `docs/comprehensibility-immune-system-2026-07.md` is the full rationale for the comprehensibility pillar. Every architectural decision traces back to one of these.

2. **research/reviewed/*.md** — the **adversarial WHY**, second-highest. Each is an agent's fenced review/redteam of a pillar or plan (e.g. `deepseek-p0-design-review-2026-07-09.md`, `claude-comms-pillar-fenced-2026-07-09.md`). They capture REJECTED alternatives, counterfactuals, and edge-case reasoning that the design doc itself omits. The corpus answers "why was X chosen over Y?" better than any other.

3. **Chapter summaries + promoted messages** — the **temporal WHY**: what was decided when, in what order, by whom. Each chapter has a `summary` (the distillation) + beat entries with `source` pointers back to raw atoms. Promoted messages tag `handoff`/`decision`/`blocker` events with content and timestamps — "why did we pivot mid-sprint?" lives here.

Bottom tier: note bodies (too terse), git log bodies (too granular, one-line summaries).

### (3) Existing Search/Rank Machinery — Zero New Storage

Every single corpus can be indexed by machinery **already in core/**, with no new stores:

| Corpus | Existing indexer | How |
|---|---|---|
| **docs/*.md** | `Ranker` (+ `keyword_relevance`) — already does keyword-overlap relevance on `text` fields | Read file → dict `{"text": contents, "source": path, "timestamp": mtime}` → `Ranker.rank()` |
| **research/reviewed/*.md** | Same | Same |
| **Note bodies** | `Ranker` — notes are already loaded by recall boot as dicts with `text`/`recommendation`/`timestamp` | `at_action` already reads them; feed to `Ranker` |
| **Promoted bus messages** | `EventQuery.search()` — **already built**, filters by `kind=bifrost_msg`, ranks by `Ranker` (keyword + recency) | `promoter.promoted()` returns the list; `EventQuery.search("why did we...", kind="bifrost_msg")` already works |
| **Chapter summaries** | `Ranker` + `Distiller` — chapters are dicts with `summary`, `why`, `recorded_at`; `chronicler` already ranks beats → distills chapters | Load `narr:chapter:<id>` → dict with `{text: ch.summary, timestamp: ch.recorded_at, source: ch.id}` → `Ranker.rank()` |
| **Git log bodies** | `Ranker` (zero new code; git is filesystem) | `git_log` → parse each commit → dict `{"text": subject+body, "timestamp": authored_date, "source": sha}` → `Ranker.rank()` |
| **Event firehose (raw)** | `EventQuery.search()` + `EventIndex.window()` — **fully built**, total recall within retention | `events_in_window()` for timeline drill; `search()` for keyword over detail/summary/kind |

**The unifying seam**: every corpus projects to a `{"text": str, "source": str, "timestamp": str|float, "importance": int}` dict — which is exactly the `Ranker` item contract. The lookback verb is composition: fan-out the query to each corpus adapter, merge scored results, cap at a budget via `Distiller`.

**What's missing (P7 scope)**: not storage, not indexing — just the *fan-out orchestrator* that queries all 6 corpora simultaneously, merges `Scored` lists, and distills to a budget. That's ~50 lines of Python. The plumbing is all there: `EventQuery.search()`, `Ranker.rank()`, `Distiller.distill()`, `promoter.promoted()`, `chronicler` chapter loads, `knowledge_recall`, `git_log`. P7 is assembly, not new primitives.
