"""
Learning Store: Persists and retrieves experiment outcomes via the Store.

Semantic Relationship: Learnings persist_to Store (Redis when up, Files always)

Captures and organizes experiment outcomes to prevent rework and enable
collective learning. Learnings derive from experiments and are indexed for
discovery by other agents.

PERSISTENCE MODEL (Pillar 0)
----------------------------
This module talks ONLY to a `Store` (core.foundation.store). The Store handles
Redis-vs-file selection and graceful degradation, so this module no longer
branches on "if redis else file" -- there is exactly one code path per
operation. Swapping persistence = swapping the injected Store.

Learnings are indexed with the same structure regardless of backend:
- learn:experiment:{id}      (hash)  full experiment record
- learn:experiments:all      (list)  experiment ids, newest first
- learn:experiments:success  (zset)  id -> success score (0/50/100)
- learn:category:{category}  (set)   experiment ids in a category
- learn:agent:{agent_id}     (list)  experiment ids from an agent
- learn:anti_patterns        (set)   known anti-pattern names
- learn:anti_pattern:{name}  (hash)  anti-pattern detail

Usage:
    from core.learning.learning_store import persist_learning_to_store, load_recommendations_from_store

    persist_learning_to_store({
        "experiment_name": "exp_1", "what_tried": "approach_x",
        "expected_outcome": "result_y", "actual_outcome": "result_z",
        "category": "optimization", "success": "yes", "recommendation": "...",
    })

    recommendations = load_recommendations_from_store("code_optimization")
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import os

from core.foundation.store import Store, create_store

# Generic verbs/nouns that describe *that* something failed rather than *what* the known-bad is;
# stripped so an auto-drafted slug names the pattern, not the failure event.
_DRAFT_STOP = {"the", "and", "for", "with", "this", "that", "use", "used", "using", "via", "from",
               "into", "was", "were", "then", "when", "because", "cause", "only", "gave", "made",
               "make", "does", "did", "not", "but", "our", "its", "have", "has", "had", "will",
               "would", "could", "should", "must", "tried", "trying", "failed", "fails", "fail",
               "error", "errors", "issue", "problem", "result", "results", "instead", "again"}


def draft_anti_pattern_slug(what_tried: str = "", root_cause: str = "", recommendation: str = "",
                            max_words: int = 4) -> str:
    """Auto-draft a candidate anti-pattern slug from a failure lesson's own words -- removes the
    'what do I even name it' cost of capturing a known-bad (Slice 2). Prefers root_cause (it names
    WHY it failed), then what_tried, then recommendation. Returns a snake_case slug of the most
    salient content tokens, or '' when there is nothing meaningful to name (stay silent)."""
    source = (root_cause or "").strip() or (what_tried or "").strip() or (recommendation or "").strip()
    if not source:
        return ""
    words: List[str] = []
    for w in re.findall(r"[A-Za-z0-9]+", source.lower()):
        if len(w) > 3 and w not in _DRAFT_STOP and w not in words:
            words.append(w)
        if len(words) >= max_words:
            break
    return "_".join(words)


class LearningStore:
    """
    Unified interface to learning data, backed by a swappable Store.

    Semantic Relationship: LearningStore indexes_experiments_in Store

    Stores structured learning signals with automatic indexing and
    categorization, enabling agents to learn from past experiments and outcomes.
    """

    # Canonical success vocabulary. Every stored learning uses exactly one of
    # these three values so reads, scoring, and ranking are unambiguous.
    SUCCESS_SCORES = {"yes": 100, "partial": 50, "no": 0}

    # Maps the messy real-world representations that have shown up in signals
    # (booleans, prose, pass/fail) onto the canonical vocabulary above.
    _SUCCESS_SYNONYMS = {
        "yes": "yes", "true": "yes", "success": "yes", "succeeded": "yes",
        "pass": "yes", "passed": "yes", "ok": "yes",
        "partial": "partial", "partially": "partial", "mixed": "partial",
        "no": "no", "false": "no", "failure": "no", "failed": "no",
        "fail": "no", "error": "no",
    }

    @classmethod
    def normalize_success_to_vocabulary(cls, raw: Any) -> str:
        """
        Normalize any success value onto the canonical {yes, partial, no}.

        Semantic Relationship: RawSuccess normalized_to CanonicalVocabulary

        Accepts booleans, casing variants, and common synonyms ("True",
        "passed", "failed", ...). Anything unrecognized becomes "no" so an
        ambiguous outcome is never optimistically scored as a success.
        """
        if isinstance(raw, bool):
            return "yes" if raw else "no"
        if raw is None:
            return "no"
        return cls._SUCCESS_SYNONYMS.get(str(raw).strip().lower(), "no")

    def __init__(self, store: Optional[Store] = None, redis_client: Optional[Any] = None):
        """
        Initialize the Learning Store.

        Args:
            store: A Store instance to persist through. If None, a default
                   HybridStore (Redis when up, File always) is created.
            redis_client: Deprecated/back-compat. If provided, it is wrapped in a
                   RedisStore+HybridStore so existing callers keep working.
        """
        log_dir = Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "coordinator_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(level=logging.INFO, format='[LEARNING_STORE] [%(asctime)s] %(message)s')
        self.logger = logging.getLogger("learning_store")

        if store is not None:
            self.store = store
        elif redis_client is not None:
            # Back-compat: wrap a passed-in client, keep file durability.
            from core.foundation.store import RedisStore, FileStore, HybridStore
            self.store = HybridStore(RedisStore(redis_client), FileStore())
        else:
            self.store = create_store(prefer_redis=True)

        # One-time, idempotent import of the legacy flat learnings.jsonl so the
        # existing on-disk learnings become first-class Store entries.
        self._import_legacy_jsonl_if_needed()

    # ----- legacy migration -----
    def _import_legacy_jsonl_if_needed(self) -> None:
        """
        Import learnings from the legacy session_logs/learnings.jsonl, once.

        Semantic Relationship: LegacyLearnings migrated_into Store

        Idempotent: an experiment already indexed in the Store is skipped, so
        repeated startups never duplicate entries.
        """
        try:
            legacy_file = Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "session_logs" / "learnings.jsonl"
            if not legacy_file.exists():
                return
            imported = 0
            with open(legacy_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        signal = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    exp_id = signal.get("experiment_name")
                    if not exp_id:
                        continue
                    if self.store.exists(f"learn:experiment:{exp_id}"):
                        continue
                    self._index_learning(signal)
                    imported += 1
            if imported:
                self.logger.info(f"Imported {imported} legacy learning(s) from learnings.jsonl into Store")
        except Exception as e:
            self.logger.warning(f"Legacy learning import skipped: {e}")

    # ----- write -----
    def persist_learning_derived_from_experiment(self, learning_signal: Dict[str, Any]) -> bool:
        """
        Persist learning derived from experiment to the Store.

        Semantic Relationship: Learning derives_from Experiment

        Args:
            learning_signal: Learning signal containing experiment data

        Returns:
            True if the learning was successfully recorded.
        """
        try:
            self._index_learning(learning_signal)
            exp = learning_signal.get("experiment_name", "unknown")
            self.logger.info(f"Learning recorded: {exp} ({learning_signal.get('success')})")
            return True
        except Exception as e:
            self.logger.error(f"Error recording learning: {e}")
            return False

    # Backward compatibility alias
    def record_learning(self, learning_signal: Dict[str, Any]) -> bool:
        """Deprecated: Use persist_learning_derived_from_experiment() instead"""
        return self.persist_learning_derived_from_experiment(learning_signal)

    def tag_anti_pattern(self, experiment_id: str, name: str, reason: str = "") -> bool:
        """Attach an anti_pattern NAME to an EXISTING lesson WITHOUT clobbering its other fields.

        Re-recording a lesson rewrites the whole hash (every field, blanks included), so it can't be
        used to add one field. This does a targeted merge-hset of just `anti_pattern`, then indexes
        the anti-pattern (so recall's dissent-finder can surface it). Returns False if the lesson is
        unknown. This is the safe write path behind Slice 2's capture nudge: record the failure first,
        then tag it as a reusable known-bad in one cheap follow-up -- growing the disconfirmers the
        dissent-finder needs, without the confirmation-biased corpus ever losing data."""
        key = f"learn:experiment:{experiment_id}"
        if not name or not self.store.exists(key):
            return False
        try:
            self.store.hset(key, mapping={"anti_pattern": str(name)})   # merge: only this field
            self.store.sadd("learn:anti_patterns", str(name))
            existing = self._load_experiment(experiment_id)
            self.store.hset(f"learn:anti_pattern:{name}", mapping={
                "experiments": experiment_id,
                "reason": str(reason or existing.get("root_cause") or existing.get("recommendation") or ""),
                "severity": "medium",
                "first_seen": datetime.utcnow().isoformat(),
            })
            return True
        except Exception as e:
            self.logger.error(f"tag_anti_pattern failed for {experiment_id}: {e}")
            return False

    def mark_graduated(self, experiment_id: str, enforced_by: str = "", *, undo: bool = False) -> bool:
        """GRADUATE a lesson: its rule is now ENFORCED by automation (a hook / guardrail / CI
        check), so it stops competing for recall surface slots while keeping its full history
        and full-corpus visibility (append-only ethos: graduation is state on the record, never
        a delete). This is Greptile's "disable what a deterministic tool already covers" mapped
        onto the friction-audit spectrum: once a lesson becomes a forcing function, re-surfacing
        the reminder is pure noise. PARTIAL hash update on purpose -- a re-record via
        record_learning would blank unset fields, and hset merges so a later re-record can't
        blank THIS. `undo=True` clears it (a mistaken graduation must be reversible).

        Semantic Relationship: Lesson superseded_by Automation (enforced_by)
        """
        key = f"learn:experiment:{experiment_id}"
        try:
            if not self.store.exists(key):
                return False
            self.store.hset(key, mapping={
                "graduated": "" if undo else datetime.utcnow().isoformat(),
                "enforced_by": "" if undo else str(enforced_by or ""),
            })
            return True
        except Exception as e:
            self.logger.error(f"mark_graduated failed for {experiment_id}: {e}")
            return False

    def mark_benched(self, experiment_id: str, reason: str = "", *, undo: bool = False) -> bool:
        """BENCH a lesson: it has surfaced repeatedly without ever earning credit, so it stops
        competing for recall surface slots (cache/boot) while keeping full history + full-corpus
        visibility -- graduation's exact mechanics with the opposite cause (graduated = the rule
        WON and became automation; benched = the lesson never demonstrated value at the surface).
        Reversible by design: the curator UNBENCHES on any new credit (helped/useful/engaged), so
        a quiet guardian that finally fires earns its slot back. Same partial-hset rationale as
        mark_graduated. See core/recall/curator.py for the rules that drive this.

        Semantic Relationship: Lesson benched_by Curator (cost_no_return)
        """
        key = f"learn:experiment:{experiment_id}"
        try:
            if not self.store.exists(key):
                return False
            self.store.hset(key, mapping={
                "benched": "" if undo else datetime.utcnow().isoformat(),
                "bench_reason": "" if undo else str(reason or ""),
            })
            return True
        except Exception as e:
            self.logger.error(f"mark_benched failed for {experiment_id}: {e}")
            return False

    def mark_related(self, experiment_id: str, related: List[Dict[str, Any]]) -> bool:
        """Persist the near-duplicate edges `find_related` computed at capture time. The write door
        has ALWAYS warned on overlap (advisory print) -- but the edge itself evaporated with the
        console line, so the consolidation/merge pass it points at had nothing durable to act on.
        Stored one-directional on the NEW record as JSON [{'experiment_name','dims','matched'}...];
        a merge pass can invert. Same partial-hset rationale as mark_benched/mark_graduated.
        Capped at 5 edges by design: >5 near-duplicates of one lesson is itself the signal
        (a consolidation emergency), and the strongest 5 (find_related sorts by dims) are
        plenty to route the merge pass there.

        Semantic Relationship: Lesson related_to Lesson (near_duplicate_edge)
        """
        key = f"learn:experiment:{experiment_id}"
        try:
            if not related or not self.store.exists(key):
                return False
            self.store.hset(key, mapping={
                "related_to": json.dumps([{"experiment_name": r.get("experiment_name"),
                                           "dims": r.get("dims"),
                                           "matched": r.get("matched")} for r in related[:5]]),
                "related_stamped": datetime.utcnow().isoformat(),
            })
            return True
        except Exception as e:
            self.logger.error(f"mark_related failed for {experiment_id}: {e}")
            return False

    def mark_forge_rejected(self, experiment_id: str, draft: str, reasons: List[str]) -> bool:
        """Append a rejected Forge edit to the record's durable negative-feedback buffer
        (design decision 6, locked KEEP as a plain field). The optimizer prompt includes
        this buffer so a failed edit is never re-proposed; capped to the last 8 rejections
        (enough to steer, bounded on the record). Same partial-hset idiom as the mark_* family."""
        key = f"learn:experiment:{experiment_id}"
        try:
            rec = self._load_experiment(experiment_id)
            if not rec:
                return False
            try:
                buf = json.loads(str(rec.get("forge_rejected") or "[]"))
            except Exception:
                buf = []
            buf.append({"at": datetime.utcnow().isoformat(),
                        "draft": str(draft or "")[:400],
                        "reasons": [str(r)[:200] for r in (reasons or [])][:5]})
            self.store.hset(key, mapping={"forge_rejected": json.dumps(buf[-8:])})
            return True
        except Exception as e:
            self.logger.error(f"mark_forge_rejected failed for {experiment_id}: {e}")
            return False

    def stamp_forge_proposal(self, experiment_id: str, draft: str, verdict: str, *,
                             by: str = "", rationale: str = "") -> bool:
        """Queue an optimizer proposal for HUMAN review (F2): one pending proposal per
        lesson, overwritten by a newer one, swept by the curator after PROPOSAL_TTL_DAYS.
        Holds the draft + the gate's verdict (PASS or UNMEASURABLE) -- FAILs never queue."""
        key = f"learn:experiment:{experiment_id}"
        try:
            if not self.store.exists(key) or not str(draft or "").strip():
                return False
            self.store.hset(key, mapping={"forge_proposal": json.dumps({
                "draft": str(draft), "verdict": str(verdict or ""),
                "at": datetime.utcnow().isoformat(), "by": str(by or ""),
                "rationale": str(rationale or "")[:200]})})
            return True
        except Exception as e:
            self.logger.error(f"stamp_forge_proposal failed for {experiment_id}: {e}")
            return False

    def clear_forge_proposal(self, experiment_id: str) -> bool:
        """Remove a pending proposal (applied, declined, or curator-expired)."""
        key = f"learn:experiment:{experiment_id}"
        try:
            if not self.store.exists(key):
                return False
            self.store.hset(key, mapping={"forge_proposal": ""})
            return True
        except Exception as e:
            self.logger.error(f"clear_forge_proposal failed for {experiment_id}: {e}")
            return False

    def apply_forge_edit(self, experiment_id: str, new_recommendation: str,
                         gate_summary: Dict[str, Any],
                         baseline: Optional[Dict[str, Any]] = None) -> bool:
        """Apply a gate-PASSED, human-approved Forge edit: swap the recommendation text,
        retaining the incumbent for rollback (reversible by construction -- the same bet
        bench/unbench makes) and stamping provenance + the provisional watch marker the
        curator's Tier-1 pass (F4) will read. Counters are untouched: an edit is a new
        coat, not a new identity."""
        key = f"learn:experiment:{experiment_id}"
        try:
            rec = self._load_experiment(experiment_id)
            if not rec or not str(new_recommendation or "").strip():
                return False
            self.store.hset(key, mapping={
                "recommendation": str(new_recommendation),
                "forge_previous_text": str(rec.get("recommendation") or ""),
                "forged_at": datetime.utcnow().isoformat(),
                "forge_provisional": datetime.utcnow().isoformat(),
                "forge_gate": json.dumps(gate_summary or {}, default=str),
                # counters snapshot at apply time -- the Tier-1 watch (F4) computes its
                # rollback/confirm deltas against exactly this
                "forge_baseline": json.dumps(baseline or {}, default=str),
                "forge_proposal": "",   # an applied proposal is no longer pending
            })
            return True
        except Exception as e:
            self.logger.error(f"apply_forge_edit failed for {experiment_id}: {e}")
            return False

    def rollback_forge_edit(self, experiment_id: str) -> bool:
        """Restore the pre-Forge text (Tier-1 rollback path; also the operator's undo).
        Clears the provisional marker; the rejected buffer keeps the failed variant."""
        key = f"learn:experiment:{experiment_id}"
        try:
            rec = self._load_experiment(experiment_id)
            prev = str((rec or {}).get("forge_previous_text") or "")
            if not rec or not prev:
                return False
            self.store.hset(key, mapping={"recommendation": prev, "forge_previous_text": "",
                                          "forge_provisional": "", "forge_rolled_back":
                                          datetime.utcnow().isoformat()})
            return True
        except Exception as e:
            self.logger.error(f"rollback_forge_edit failed for {experiment_id}: {e}")
            return False

    def _index_learning(self, learning_signal: Dict[str, Any]) -> None:
        """
        Index a learning signal into all Store structures (single code path).

        Semantic Relationship: Learning indexed_in Store
        """
        experiment_id = learning_signal.get(
            "experiment_name", f"exp_{datetime.utcnow().isoformat()}"
        )

        # Normalize success once, here, so the stored field and the success
        # score are derived from the same canonical value -- they can never
        # disagree, and every learning reads back with consistent vocabulary.
        success = self.normalize_success_to_vocabulary(learning_signal.get("success"))

        agent_id = learning_signal.get("agent_id") or "unknown"

        # Coerce every field to a non-None string: Redis hset rejects None, and an
        # agent (e.g. OpenCode) will pass partial/None fields. Sanitize at the seam.
        def _s(v, default=""):
            return default if v is None else str(v)

        experiment_data = {
            "experiment_name": experiment_id,
            "what_tried": _s(learning_signal.get("what_tried")),
            "expected": _s(learning_signal.get("expected_outcome")),
            "actual": _s(learning_signal.get("actual_outcome")),
            "metrics": json.dumps(learning_signal.get("metrics") or {}),
            "success": success,
            "timestamp": _s(learning_signal.get("timestamp"), datetime.utcnow().isoformat()),
            "recommendation": _s(learning_signal.get("recommendation")),
            "anti_pattern": _s(learning_signal.get("anti_pattern")),
            "root_cause": _s(learning_signal.get("root_cause")),
            "confidence": _s(learning_signal.get("confidence"), "medium"),
            "category": _s(learning_signal.get("category"), "uncategorized"),
            "agent_id": agent_id,
            # lossy summary + lossless pointer: the store record IS the raw for an
            # agent-authored learning, so it points at itself -> Distiller can keep it.
            "source": _s(learning_signal.get("source"), f"learn:experiment:{experiment_id}"),
        }

        is_new = not self.store.exists(f"learn:experiment:{experiment_id}")
        self.store.hset(f"learn:experiment:{experiment_id}", mapping=experiment_data)
        # Indexes are SETS-of-names in spirit: only add a name once. Re-recording the
        # same experiment updates the hash but must NOT duplicate index entries
        # (this is the bug that accumulated verify_exp x4 in the original data).
        if is_new:
            self.store.lpush("learn:experiments:all", experiment_id)
            self.store.lpush(f"learn:agent:{agent_id}", experiment_id)

        score = self.SUCCESS_SCORES[success]
        self.store.zadd("learn:experiments:success", {experiment_id: score})

        category = experiment_data["category"]
        self.store.sadd(f"learn:category:{category}", experiment_id)

        anti_pattern = learning_signal.get("anti_pattern")
        if anti_pattern:
            self.store.sadd("learn:anti_patterns", str(anti_pattern))
            self.store.hset(f"learn:anti_pattern:{anti_pattern}", mapping={
                "experiments": experiment_id,
                "reason": _s(learning_signal.get("root_cause")),
                "severity": _s(learning_signal.get("severity"), "medium"),
                "first_seen": datetime.utcnow().isoformat(),
            })

    # ----- read helpers -----
    def _load_experiment(self, exp_id: str) -> Dict[str, Any]:
        """Load one experiment hash and parse its metrics JSON."""
        data = self.store.hgetall(f"learn:experiment:{exp_id}")
        if data and "metrics" in data:
            try:
                data["metrics"] = json.loads(data["metrics"])
            except (json.JSONDecodeError, TypeError):
                pass
        return data

    # ----- read: search -----
    def search_learnings_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Search learnings by keyword (matches experiment id or any field).

        Semantic Relationship: SearchResults derived_from Learnings (by keyword)
        """
        try:
            # Tokenize + OR-match: a multi-word query matches any learning containing
            # ANY of its terms, ranked by how many terms hit (so the closest matches
            # surface first). A single substring match made multi-word queries return
            # nothing -- the worst failure mode for a memory system (Cursor caught this).
            terms = [t for t in (keyword or "").lower().split() if t]
            if not terms:
                return []
            scored, seen = [], set()
            for exp_id in self.store.lrange("learn:experiments:all", 0, -1):
                if exp_id in seen:
                    continue
                seen.add(exp_id)
                data = self._load_experiment(exp_id)
                if not data:
                    continue
                haystack = exp_id.lower() + " " + " ".join(str(v).lower() for v in data.values())
                hits = sum(1 for t in terms if t in haystack)
                if hits:
                    scored.append((hits, {"id": exp_id, **data}))
            scored.sort(key=lambda x: -x[0])   # most terms matched first
            return [d for _, d in scored]
        except Exception as e:
            self.logger.error(f"Error searching learnings: {e}")
            return []

    # Backward compatibility alias
    def get_learnings(self, query: str) -> List[Dict[str, Any]]:
        """Deprecated: Use search_learnings_by_keyword() instead"""
        return self.search_learnings_by_keyword(query)

    # search_learnings_by_keywords is kept as a distinct public name (same logic)
    def search_learnings_by_keywords(self, keywords: str) -> List[Dict[str, Any]]:
        """
        Search learnings by keywords.

        Semantic Relationship: SearchResults derived_from Learnings (by keywords)
        """
        return self.search_learnings_by_keyword(keywords)

    # Backward compatibility alias
    def search_learnings(self, keywords: str) -> List[Dict[str, Any]]:
        """Deprecated: Use search_learnings_by_keywords() instead"""
        return self.search_learnings_by_keywords(keywords)

    # ----- read: category analysis -----
    def analyze_learning_patterns_in_category(self, category: str) -> Dict[str, Any]:
        """
        Analyze what consistently works vs doesn't in a category.

        Semantic Relationship: Patterns derived_from LearningsInCategory
        """
        try:
            experiments = self.store.smembers(f"learn:category:{category}")
            success_count = {"yes": 0, "partial": 0, "no": 0}
            results = []
            for exp_id in experiments:
                data = self._load_experiment(exp_id)
                if not data:
                    continue
                success = data.get("success", "unknown")
                if success in success_count:
                    success_count[success] += 1
                results.append(data)

            total = sum(success_count.values())
            success_rate = success_count["yes"] / total if total > 0 else 0
            return {
                "category": category,
                "total_experiments": len(experiments),
                "success_breakdown": success_count,
                "success_rate": success_rate,
                "experiments": results,
            }
        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {e}")
            return {}

    # Backward compatibility alias
    def get_patterns(self, category: str) -> Dict[str, Any]:
        """Deprecated: Use analyze_learning_patterns_in_category() instead"""
        return self.analyze_learning_patterns_in_category(category)

    # ----- read: anti-patterns -----
    def load_documented_anti_patterns(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load documented anti-patterns (things that don't work), by severity.

        Semantic Relationship: AntiPattern referenced_by LearningStore
        """
        try:
            all_patterns = self.store.smembers("learn:anti_patterns")
            if topic:
                topic_lower = topic.lower()
                matching = [p for p in all_patterns if topic_lower in p.lower()]
            else:
                matching = list(all_patterns)

            results = []
            for pattern in matching:
                data = self.store.hgetall(f"learn:anti_pattern:{pattern}")
                if data:
                    results.append({
                        "pattern": pattern,
                        "severity": data.get("severity", "medium"),
                        "reason": data.get("reason", ""),
                        "experiments": data.get("experiments", ""),
                        "first_seen": data.get("first_seen", ""),
                    })

            severity_order = {"high": 3, "medium": 2, "low": 1}
            results.sort(key=lambda x: severity_order.get(x["severity"], 0), reverse=True)
            return results
        except Exception as e:
            self.logger.error(f"Error getting anti-patterns: {e}")
            return []

    # Backward compatibility alias
    def get_anti_patterns(self, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Deprecated: Use load_documented_anti_patterns() instead"""
        return self.load_documented_anti_patterns(topic)

    # ----- read: recommendations -----
    def load_recommendations_for_task(self, task: str) -> List[Dict[str, Any]]:
        """
        Load recommendations for a task from past learnings, by success.

        Semantic Relationship: Recommendation derived_from SuccessfulExperiments
        """
        try:
            task_lower = task.lower()
            recommendations = []
            for exp_id in self.store.lrange("learn:experiments:all", 0, -1):
                if task and task_lower not in exp_id.lower():
                    data = self._load_experiment(exp_id)
                    # also match against content, not just id
                    if not data or task_lower not in " ".join(
                        str(v).lower() for v in data.values()
                    ):
                        continue
                else:
                    data = self._load_experiment(exp_id)
                if data and data.get("recommendation"):
                    recommendations.append({
                        "experiment": exp_id,
                        "recommendation": data.get("recommendation", ""),
                        "success": data.get("success", ""),
                        "what_tried": data.get("what_tried", ""),
                        "metrics": data.get("metrics", {}),
                        "category": data.get("category", ""),
                    })

            success_scores = {"yes": 3, "partial": 2, "no": 1}
            recommendations.sort(
                key=lambda x: success_scores.get(x["success"], 0), reverse=True
            )
            return recommendations
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            return []

    # Backward compatibility alias
    def get_recommendations(self, task: str) -> List[Dict[str, Any]]:
        """Deprecated: Use load_recommendations_for_task() instead"""
        return self.load_recommendations_for_task(task)

    # ----- read: category summary -----
    def summarize_learnings_by_category(self) -> Dict[str, Dict[str, Any]]:
        """
        Summarize learnings grouped by category.

        Semantic Relationship: CategorySummary derived_from LearningsGroupedByCategory
        """
        try:
            categories = {}
            for key in self.store.keys("learn:category:*"):
                category = key.replace("learn:category:", "")
                categories[category] = self.analyze_learning_patterns_in_category(category)
            return categories
        except Exception as e:
            self.logger.error(f"Error getting category summary: {e}")
            return {}

    # Backward compatibility alias
    def get_category_summary(self) -> Dict[str, Dict[str, Any]]:
        """Deprecated: Use summarize_learnings_by_category() instead"""
        return self.summarize_learnings_by_category()

    # ----- read: by agent -----
    def load_learnings_contributed_by_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Load all learnings contributed by a specific agent.

        Semantic Relationship: Learnings contributed_by Agent
        """
        try:
            results = []
            for exp_id in self.store.lrange(f"learn:agent:{agent_id}", 0, -1):
                data = self._load_experiment(exp_id)
                if data:
                    results.append({"id": exp_id, **data})
            return results
        except Exception as e:
            self.logger.error(f"Error getting agent learnings: {e}")
            return []

    # Backward compatibility alias
    def get_agent_learnings(self, agent_id: str) -> List[Dict[str, Any]]:
        """Deprecated: Use load_learnings_contributed_by_agent() instead"""
        return self.load_learnings_contributed_by_agent(agent_id)

    # ----- read: all -----
    def load_all_learnings_from_store(self) -> List[Dict[str, Any]]:
        """
        Load all learnings from the Store (newest first).

        Semantic Relationship: AllLearnings derived_from LearningStore
        """
        try:
            # ONE bulk read instead of one round-trip per lesson.
            #
            # This used to list the index and then call _load_experiment for every id.
            # Measured 2026-07-26 at 455 lessons: 220ms per query, 0.483ms per lesson, and it
            # sits on the PreToolUse path -- so it ran on EVERY tool call, extrapolating to
            # 483 seconds per query at a million lessons. The cost was round-trips, not
            # ranking, so the fix is to stop making N of them.
            #
            # The index still decides ORDER (newest first) and membership; the bulk read only
            # supplies the payloads. That keeps the ordering contract exactly as it was --
            # a set-based read would have silently changed result order.
            by_key = self.store.hgetall_prefix("learn:experiment:")
            results = []
            for exp_id in self.store.lrange("learn:experiments:all", 0, -1):
                data = by_key.get(f"learn:experiment:{exp_id}")
                if not data:
                    continue
                data = dict(data)
                if "metrics" in data:
                    try:
                        data["metrics"] = json.loads(data["metrics"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                results.append(data)
            return results
        except Exception as e:
            self.logger.error(f"Error getting all learnings: {e}")
            return []

    # Backward compatibility alias
    def get_all_learnings(self) -> List[Dict[str, Any]]:
        """Deprecated: Use load_all_learnings_from_store() instead"""
        return self.load_all_learnings_from_store()

    # ----- stats -----
    def get_learning_store_stats(self) -> Dict[str, Any]:
        """
        Statistics about the learning store.

        Semantic Relationship: StoreStats derived_from AllLearnings
        """
        try:
            all_learnings = self.load_all_learnings_from_store()
            redis_up = False
            # HybridStore exposes redis_available; other stores may not.
            redis_up = bool(getattr(self.store, "redis_available", False))
            return {
                "total_experiments": len(all_learnings),
                "successful": len([l for l in all_learnings if l.get("success") == "yes"]),
                "failed": len([l for l in all_learnings if l.get("success") == "no"]),
                "partial": len([l for l in all_learnings if l.get("success") == "partial"]),
                "redis_connected": redis_up,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # Backward compatibility alias
    def get_stats(self) -> Dict[str, Any]:
        """Deprecated: Use get_learning_store_stats() instead"""
        return self.get_learning_store_stats()


_DIM_TOKEN_RE = re.compile(r"[A-Za-z0-9_./\\-]+")


def _dim_tokens(s: Any) -> set:
    return {t.lower() for t in _DIM_TOKEN_RE.findall(str(s or "")) if len(t) > 3}


def _dims_of(rec: Dict[str, Any]) -> Dict[str, set]:
    """The five comparison dimensions for near-duplicate detection, adapted from Every's
    ce-compound overlap rule (docs/library/design/20260701_field-survey-what-the-best-practitioners_3c9d20.md C5): problem / root cause /
    solution / referenced paths / kind. Purely lexical on purpose -- deterministic, no
    embeddings, no LLM judge."""
    problem = _dim_tokens(rec.get("what_tried")) | _dim_tokens(rec.get("expected"))
    solution = _dim_tokens(rec.get("recommendation")) | _dim_tokens(rec.get("actual"))
    return {
        "problem": problem,
        "root_cause": _dim_tokens(rec.get("root_cause")),
        "solution": solution,
        "refs": {t for t in (problem | solution) if "/" in t or "\\" in t or "." in t},
        "kind": _dim_tokens(rec.get("category")) | _dim_tokens(rec.get("anti_pattern")),
    }


def _overlap(a: set, b: set) -> float:
    """Overlap coefficient |A∩B| / min(|A|,|B|) -- forgiving of length asymmetry (a terse
    lesson vs a verbose one about the same thing should still match)."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def find_related(signal: Dict[str, Any], existing: List[Dict[str, Any]], *,
                 threshold: float = 0.5, min_dims: int = 2,
                 exclude_name: str = "") -> List[Dict[str, Any]]:
    """Deterministic near-duplicate scan for a lesson about to be recorded. Returns
    [{'experiment_name', 'dims', 'matched'}] sorted by dims desc, for records matching the
    candidate on >= min_dims of the five dimensions. The write door uses it as an ADVISORY
    (4-5 dims: 'update the existing one instead'; 2-3: 'flag for consolidation') -- it never
    blocks a write (append-only ethos; the consolidation pass merges later)."""
    cand = _dims_of({"what_tried": signal.get("what_tried"),
                     "expected": signal.get("expected_outcome"),
                     "recommendation": signal.get("recommendation"),
                     "actual": signal.get("actual_outcome"),
                     "root_cause": signal.get("root_cause"),
                     "category": signal.get("category"),
                     "anti_pattern": signal.get("anti_pattern")})
    out: List[Dict[str, Any]] = []
    for rec in existing or []:
        name = str(rec.get("experiment_name") or "")
        if not name or name == exclude_name:
            continue
        theirs = _dims_of(rec)
        matched = [d for d in cand if _overlap(cand[d], theirs[d]) >= threshold]
        if len(matched) >= min_dims:
            out.append({"experiment_name": name, "dims": len(matched), "matched": matched})
    out.sort(key=lambda r: r["dims"], reverse=True)
    return out


def is_graduated(rec: Dict[str, Any]) -> bool:
    """True when a lesson's rule is enforced by automation (see mark_graduated). The contract:
    graduated lessons stay OUT of recall SURFACES (recall-at cache, boot ranking) but stay IN
    full-corpus queries (list / recall / --full) wearing a [graduated] tag -- history preserved,
    hot path decluttered."""
    return bool(str((rec or {}).get("graduated") or "").strip())


def is_benched(rec: Dict[str, Any]) -> bool:
    """True when the curator has benched this lesson (surfaced-often-never-credited; see
    mark_benched). Same surface contract as graduation: out of recall surfaces, in full-corpus
    queries with a [benched] tag. Reversed automatically on new credit."""
    return bool(str((rec or {}).get("benched") or "").strip())


# Global instance
_learning_store: Optional[LearningStore] = None


def get_learning_store_instance(redis_client: Optional[Any] = None,
                                store: Optional[Store] = None) -> LearningStore:
    """
    Get or create the global learning store instance.

    T069 (reconciled spec: docs/library/report/20260715_t069-singleton-isolation-reconciliation_1a7cdb.md):
    explicit injection -> fresh; _AISETUP_TEST_ISOLATED -> fresh per call, cache
    untouched (stateless wrapper over the Store); canonical -> lazy singleton.

    Semantic Relationship: LearningStoreInstance references_to GlobalInstance
    """
    import os
    global _learning_store
    if store is not None or redis_client is not None:
        return LearningStore(store=store, redis_client=redis_client)
    if os.environ.get("_AISETUP_TEST_ISOLATED"):
        return LearningStore()
    if _learning_store is None:
        _learning_store = LearningStore()
    return _learning_store


# Backward compatibility alias
def get_learning_store(redis_client: Optional[Any] = None) -> LearningStore:
    """Deprecated: Use get_learning_store_instance() instead"""
    return get_learning_store_instance(redis_client=redis_client)


def persist_learning_to_store(learning_signal: Dict[str, Any]) -> bool:
    """
    Persist a learning signal to the global learning store.

    Semantic Relationship: Learning persist_to LearningStore
    """
    return get_learning_store_instance().persist_learning_derived_from_experiment(learning_signal)


# Backward compatibility alias
def record_learning(learning_signal: Dict[str, Any]) -> bool:
    """Deprecated: Use persist_learning_to_store() instead"""
    return persist_learning_to_store(learning_signal)


def search_learnings_in_store(keyword: str) -> List[Dict[str, Any]]:
    """
    Search learnings in the global store by keyword.

    Semantic Relationship: SearchResults derived_from LearningStore
    """
    return get_learning_store_instance().search_learnings_by_keyword(keyword)


# Backward compatibility alias
def get_learnings(query: str) -> List[Dict[str, Any]]:
    """Deprecated: Use search_learnings_in_store() instead"""
    return search_learnings_in_store(query)


def load_recommendations_from_store(task: str) -> List[Dict[str, Any]]:
    """
    Load recommendations from the global store for a task.

    Semantic Relationship: Recommendation derived_from LearningStore
    """
    return get_learning_store_instance().load_recommendations_for_task(task)


# Backward compatibility alias
def get_recommendations(task: str) -> List[Dict[str, Any]]:
    """Deprecated: Use load_recommendations_from_store() instead"""
    return load_recommendations_from_store(task)


def load_anti_patterns_from_store(topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load anti-patterns from the global store.

    Semantic Relationship: AntiPattern referenced_by LearningStore
    """
    return get_learning_store_instance().load_documented_anti_patterns(topic)


# Backward compatibility alias
def get_anti_patterns(topic: Optional[str] = None) -> List[Dict[str, Any]]:
    """Deprecated: Use load_anti_patterns_from_store() instead"""
    return load_anti_patterns_from_store(topic)
