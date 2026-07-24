---
akashic_id: art_20260714_claude-t059-review-r8-knowledge-map-2026_43eade
akashic_sha: 645971776ec5
status: draft
type: report
date: 2026-07-14
title: Claude T059 Review — R8 knowledge_map (2026-07-14)
gist: "Reviewer: claude (adversarial pass per cursor's ask: \"break it, do not bless it\", M1-LITE — author≠reviewer). Build under review: cursor's, "
tenant: solo
visibility: fleet
seats: []
category: [recall, security, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-14T22:05:01"
updated: "2026-07-14T22:05:01"
---
<!-- GENERATED PROJECTION of art_20260714_claude-t059-review-r8-knowledge-map-2026_43eade -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Claude T059 Review — R8 knowledge_map (2026-07-14)

Reviewer: claude (adversarial pass per cursor's ask: "break it, do not bless it", M1-LITE — author≠reviewer).
Build under review: cursor's, 2026-07-14 23:44→23:53 (ledger T059 claimed→in_progress→verifying, clean gated flow).
Files: `core/recall/knowledge_map.py`, `cmd_knowledge_map` + subparser in `agent_cli.py`, MCP twin in `ai_setup_mcp.py`, MANIFEST entry in `scripts/check_door_parity.py`, `tests/test_knowledge_map.py`, `docs/MODULE_INDEX.md`.

---

## Defect 1 — benched/graduated lessons leaked to the surface (CONFIRMED, fixed)

The adapter read the `benched` field as a boolean string:

```python
benched = str(rec.get("benched", "")).strip().lower() in ("1", "true", "yes")
```

But the store stamps **ISO timestamps** (`mark_benched`, learning_store.py:274: `"benched": datetime.utcnow().isoformat()`), so every benched lesson read as `current`. Live evidence: **4 of 4 benched lessons in the real store leaked as current**; `semantic_documentation_update_strategy` would have been the TOP surface hit for its topics at rel 1.0. This is exactly the failure the archive layer exists to prevent (dead law reading as live), and exactly cursor's own attack-surface item (2).

`graduated` was not read at all — graduation's contract (learning_store.py:813-818: "graduated lessons stay OUT of recall SURFACES") was violated by a brand-new surface.

**Fix:** new `_lesson_status(rec)` reads through the store's canonical predicates `is_benched`/`is_graduated` (they own the field contract); `ARCHIVE_STATUS += {"graduated"}`. Both flavors now route to L3.

Root cause worth keeping: the canonical predicates existed and were not used. Adapter code must never re-derive another module's field semantics.

## Defect 2 — neighborhood nondeterministic across processes (CONFIRMED, fixed)

The walk iterated `set(surface_lesson_ids)` (Python string-hash order = per-process under PYTHONHASHSEED randomization) and then truncated at `per_layer*2`. Repro: identical inputs, seeds 1 vs 2 → **disjoint survivor sets** (seed1 kept `leaf_0_*`, seed2 kept `leaf_2_*`). Contradicts the module's own "Deterministic" claim; for the UI face it means the map flaps between renders.

**Fix:** forward walk iterates surface lessons in **rank order** (`surface_lesson_order` list); reverse arrivals are collected then applied sorted by `(surface target's rank, lesson id)`. Survivors are now a function of the graph, not of hashing or input list order. Repro re-run across seeds: identical output. Residual (accepted): equal-relevance ranker ties still break by corpus load order — that is Ranker's existing stable-sort contract, out of T059 scope.

## Blessed (attack surface items that hold)

- **IDF relevance reused from lookback for the SURFACE only** — correct: surface selection needs a relevance floor; neighborhood nodes deliberately carry `score=None` (the whole point is that edges reach what relevance cannot). Design is right.
- **Reverse-edge scan O(lessons·edges) per call** — 91 lessons today; trivial. Revisit if the corpus reaches ~10k (then: maintain a reverse index at capture time).
- **Doc/note statuses** — clean. `_doc_status` normalizes free text to a closed set ({superseded, historical, current, unstamped}); notes map superseded→"retired". No leak on those corpora.
- **Door wiring** — CLI render honest, MCP twin matches, MANIFEST honest (pre-existing `delta` verb reclassified as tracked gap instead of silently passing).
- **Private-import coupling** (`lookback._note_items` etc.) — fails LOUD at import if lookback refactors (acceptable today); follow-up: promote the five shared names to public.

## Pins added (pre-registered RED → GREEN)

- `test_adapter_status_contract_timestamps_not_booleans` — timestamps route to benched/graduated; both ∈ ARCHIVE_STATUS.
- `test_benched_and_graduated_lessons_land_in_archive` — L3, never L1.
- `test_walk_is_input_order_invariant` — cap survivors invariant to input order (hub relevances strictly distinct so ranker tie-break is not what's tested).

## Gates at close

13/13 tests (knowledge_map 7 + fence_workspace 6), door parity PASS (1 tracked gap), boundaries PASS, recall-seam subset 90/90, live probe: benched lesson renders `[lesson:benched]` in L3 on a topic where it scores rel 1.0.

## Ergonomics paper cuts noticed in passing (separate proposals, not T059)

1. Boot's truncated delta prints "full: `py agent_cli.py delta claude`" — but boot already advanced the mark, so the pointer returns "no changes". The drill-down instruction eats its own payload.
2. Unhandled-message warning prints ids as `bifrost:<id>` but `bifrost-ack` refuses that form (double-prefixes it) — the printed command doesn't round-trip. Accept both forms.
3. Handoff notes clip at 1000 chars with "remainder NOT stored" — cursor's T059 brief lost its tail silently at write time; the writer gets no warning.
