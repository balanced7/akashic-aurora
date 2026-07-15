# DeepSeek T059 Fix Delta Cross-Check — 2026-07-14

Status: **GREEN — both defects confirmed fixed; no regressions found.**

Reviewer: deepseek (adversarial pass, fence-lite; author=cursor, reviewer=claude, cross-checker=deepseek).
Reference review: `research/reviewed/claude-t059-review-2026-07-14.md`.
Files under cross-check: `core/recall/knowledge_map.py`, `tests/test_knowledge_map.py`.

---

## Defect 1 — benched/graduated lessons leaked to surface → CONFIRMED FIXED [CERTAIN]

### The old broken code
Per claude's review: `str(rec.get("benched", "")).strip().lower() in ("1", "true", "yes")` — ISO timestamps like `"2026-07-08T05:38:53.822519"` never match those strings. Four live benched lessons leaked to the surface.

### The fix: `_lesson_status()` at knowledge_map.py:54-62
```python
def _lesson_status(rec: Dict[str, Any]) -> str:
    from core.learning.learning_store import is_benched, is_graduated
    if is_benched(rec):
        return "benched"
    if is_graduated(rec):
        return "graduated"
    return "current"
```

### Predicate chain verified
- `is_benched` at `learning_store.py:821`: `bool(str((rec or {}).get("benched") or "").strip())` — any non-empty string (including ISO timestamps) → True; empty string → False.
- `is_graduated` at `learning_store.py:813`: identical logic on the `graduated` field.
- `mark_benched` at `learning_store.py:274`: stamps `datetime.utcnow().isoformat()` when benching, `""` when undoing. Contract: non-empty = benched, empty = not benched.
- The predicates own the field contract; `_lesson_status` delegates to them. No re-derivation.

### ARCHIVE_STATUS at knowledge_map.py:45
```python
ARCHIVE_STATUS = {"retired", "superseded", "historical", "benched", "graduated"}
```
Both retirement flavors present. Architecture: `build_map` (line 149-155) routes any node whose `status` is in `ARCHIVE_STATUS` to the archive layer, never the surface.

### Test coverage
- `test_adapter_status_contract_timestamps_not_booleans` (line 93): timestamps → benched/graduated; empty → current; both ∈ ARCHIVE_STATUS.
- `test_benched_and_graduated_lessons_land_in_archive` (line 103): L3 routing confirmed, never L1.

### Verdict: FIXED. ✓

---

## Defect 2 — neighborhood nondeterministic → CONFIRMED FIXED [CERTAIN]

### The old broken code
Per claude's review: the walk iterated `set(surface_lesson_ids)` — Python string-hash order under `PYTHONHASHSEED` randomization — then truncated at `per_layer*2`. Identical inputs with seeds 1 vs 2 produced disjoint survivor sets.

### The fix at knowledge_map.py:156-195

**Surface lesson order** (line 159-161):
```python
surface_lesson_order = [n["id"] for n in surface if n["kind"] == "lesson"]
surface_lesson_ids = set(surface_lesson_order)
surface_rank = {sid: i for i, sid in enumerate(surface_lesson_order)}
```
List, never a set. Rank order = surface list order = ranker output order.

**Forward walk** (line 179-182):
```python
for sid in surface_lesson_order:  # rank-stable list, never a set
    for e in (lesson_by_id.get(sid, {}).get("edges") or []):
```
Iterates rank order. No hash randomization surface.

**Reverse walk** (line 183-194):
```python
rev = []
for rec in lessons:
    ...
    if e.get("to") in surface_lesson_ids:
        rev.append((surface_rank[e.get("to")], str(aid), rec, e))
        break
for _, _, rec, e in sorted(rev, key=lambda t: (t[0], t[1])):
    _add(rec, e.get("to"), e, "in")
```
Candidates collected with surface-rank priority + id tiebreaker, then sorted deterministically. Input list order never decides who survives.

**Cap** (line 195):
```python
neighborhood = neighborhood[:per_layer * 2]
```
Truncates AFTER deterministic ordering.

### Test coverage
- `test_walk_is_input_order_invariant` (line 121): forward and reversed input lists → identical neighborhood survivors. 3 hubs × 8 leaves = 24 candidates capped at 12; survivors identical in both orientations.

### Verdict: FIXED. ✓

---

## Remaining Code Paths — Clean [CERTAIN]

| Surface | Check | Result |
|---------|-------|--------|
| `_lesson_items()` (line 65-91) | Loads via `get_learning_store().load_all_learnings_from_store()`, projects edges from `related_to` JSON | No boolean-string compare; delegates status to `_lesson_status()` |
| `_node()` (line 95-107) | Status passthrough, not derived | No re-derivation |
| `build_map()` surface/archive split (line 149-155) | `if node["status"] in ARCHIVE_STATUS` → archive; else → surface | Correct gate; `ARCHIVE_STATUS` includes both retirement flavors |
| `knowledge_map()` loader (line 213-224) | Delegates to `build_map` with live corpora, fail-soft per corpus | Clean |

---

## Full Verdict

**Both defects are correctly fixed with proper test coverage.** The fix delta at `core/recall/knowledge_map.py:54-62` (Defect 1) and lines 156-195 (Defect 2) is faithful to claude's review at every point. The three new test pins (`test_adapter_status_contract_timestamps_not_booleans`, `test_benched_and_graduated_lessons_land_in_archive`, `test_walk_is_input_order_invariant`) correctly pre-register RED → GREEN for the failure modes. No regression risk: `_lesson_status` is the sole status derivation point, predicates are the store's canonical ones, and the walk order is purely rank+id based.

**T059 fix delta: GREEN. Gates the commit.**
