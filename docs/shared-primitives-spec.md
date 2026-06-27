# Shared primitives — interface spec

Date: 2026-06-19. The three cross-cutting primitives that both the Context pillar
(System 4) and AgentMemory (Systems 1–3) need. Specified once here so they are
built once. These are **interfaces** (contracts); implementation happens during
Waves 2–3. Proposed home: a new `core/primitives/` package (foundation =
persistence; primitives = shared algorithms over stored records).

Build order is fixed by dependency: **Supersession → Ranker → Distiller.**

---

## 1. Supersession  (build first — others depend on it)

"A newer fact retires an older one." Temporal correctness so stale facts stop
surfacing. Embodies: Zep's bi-temporal idea, lightweight. Vocabulary: the
`supersedes` relationship type (from the 66-type vocab).

**Data convention** — records that can be superseded carry:
- `id: str`
- `supersedes: Optional[str]` — id of the record this one replaces (set on write)
- `superseded: bool` — flipped True on the old record when a newer one supersedes it

**Interface**
```python
class Supersession:
    @staticmethod
    def mark(new_record: dict, supersedes_id: Optional[str]) -> dict:
        """Stamp new_record.supersedes; caller flips the old record's superseded=True."""

    @staticmethod
    def is_active(record: dict) -> bool:
        """True if this record has not been superseded."""

    @staticmethod
    def active_only(records: Iterable[dict]) -> list[dict]:
        """Drop superseded records (the default read filter)."""
```
**Lands in:** AgentMemory (decisions/approaches gain supersedes; reads call
`active_only`); the Ranker (never scores a superseded record).

---

## 2. Ranker  (build second — filters superseded via #1)

"Given a pile of items and a query, which matter most right now?" Embodies:
Generative Agents retrieval (relevance × importance × recency), plus
relationship-type weighting (our differentiator).

**Interface**
```python
@dataclass
class Scored:
    item: dict
    score: float
    components: dict   # {"relevance":.., "importance":.., "recency":.., "relationship":..}

class Ranker:
    def __init__(self, *, relevance_fn=None, weights=None, half_life_days=14.0): ...

    def rank(self, items: list[dict], query: str, *, now: float,
             top_k: Optional[int] = None) -> list[Scored]:
        """Score active items and return them ordered best-first.
        relevance : query match (keyword now; embeddings seam via relevance_fn)
        importance: item['importance'] in 1..5 (vital never decays)
        recency   : exp(-age / half_life)
        relationship: weight by item['relationship_type'] vs the query intent
        Superseded items (Supersession.is_active == False) are excluded.
        """
```
**Inputs each item provides:** `text`, `importance` (1–5), `timestamp`, optional
`relationship_type`. **Lands in:** AgentMemory `get_similar` (replaces keyword
scan); Context `learning_loader` / `decision_loader`.

---

## 3. Distiller  (build third)

"Compress many items into a token budget, with a critic so nothing is lost or
hallucinated." Embodies: Mem0 consolidation with a writer→critic gate.

**Interface**
```python
@dataclass
class Distillation:
    text: str
    included_ids: list[str]
    dropped_ids: list[str]
    approx_tokens: int
    critic_ok: bool

class Distiller:
    def __init__(self, *, writer=None, critic=None): ...

    def distill(self, items: list[dict], *, token_budget: int,
                instruction: str) -> Distillation:
        """writer: produce a summary within token_budget.
        critic: check for data loss / hallucination / conflict; if invalid, redo
        (bounded retries). writer/critic default to heuristics (rank+truncate,
        coverage check) with an LLM seam for later."""
```
**Lands in:** Context `summarizer` (fit the 8–10k budget); AgentMemory Phase D
(consolidate raw experiences → durable lessons → `chronicles/`).

**Compaction rules (from `docs/context-compaction-skeleton-research.md`):** the
Distiller is *hierarchical* (raw → per-topic → top skeleton) and produces a
**Markdown+YAML skeleton** (`Domain > Topic > Entry`, edges = relationship_types).
Crucially — **lossy summary + lossless pointer**: never delete the raw (the Ledger
stays append-only); every distilled entry keeps a `source` pointer (Ledger cursor
id / experiment id) so detail can be reconstructed. So `Distillation` entries carry
`source` alongside `included_ids`/`dropped_ids`.

---

## How they compose (the payoff)

```
records ── Supersession.active_only ──> Ranker.rank ──(top items)──> Distiller.distill ──> budgeted context
```
Build them once here; the Context pillar and AgentMemory both consume the same
three. Improving any one improves both features at once.

## When each lands (ties to the roadmap)
- **Supersession** with AgentMemory Phase B (temporal fields).
- **Ranker** with Context pillar Wave 2 (and AgentMemory Phase C retrieval).
- **Distiller** with Context pillar Wave 2 summarizer (and AgentMemory Phase D).

`IndexedRecords` (the existing LearningStore/AgentMemory storage shape) is a
separate extraction, done in Context Wave 1 when it gains its third user — see
`docs/shared-primitives-and-coherence.md`.
