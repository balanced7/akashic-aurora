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

import uuid
import json
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
import os
from core.paths import repo_root

from core.foundation.store import Store, create_store
from core.learning.domains import DEFAULT_DOMAIN, infer_domain

# ---- RETRIEVAL VOCABULARY ----------------------------------------------------------------------
# The flood, measured 2026-08-02: asking the corpus a shader question returned 77, 707 and 675 rows,
# every one of them about bus lanes and ACLs, and it never said "I have nothing". The cause was two
# lines below the surface -- `hits = sum(1 for t in terms if t in haystack)` then `if hits:`. That
# is a SUBSTRING test with no floor, so "the" matched almost every record and "state" matched
# "statement". A ten-word question therefore reached most of the corpus and came back RANKED, which
# reads as confidence.
#
# The same defect turned up twice more the same day in unrelated instruments (a PNG decoder that
# returned ten identical confident errors; a metric suite that scored three visibly different images
# as identical). AN INSTRUMENT THAT CANNOT SEE ITS SUBJECT RETURNS A CONFIDENT ANSWER, NOT SILENCE.
# Recall is allowed to answer "nothing" -- and must, or every other honesty guarantee is decoration.
_STOPWORDS = frozenset("""
a an and are as at be been being both but by can could did do does for from had has have how i if
in into is it its may might most must no not of on once one only or other our over own same should
so some such than that the their them then there these they this those through to too two under
until up very was we were what when where which while who why will with would you your about after
again all also any because before between during each few more much never new now off out same
""".split())

# UNDERSCORE IS PART OF A TOKEN; HYPHEN IS A SEPARATOR. That asymmetry is deliberate and was caught
# by an existing pin: splitting on '_' made the query `gamma_lesson` match the record `alpha_lesson`
# through the shared fragment "lesson", which is exactly the false confidence this work exists to
# remove. snake_case names are single symbols and must match whole; kebab-case labels like
# `channel-rotate` are multi-word and must stay reachable by either half.
_TOKEN = re.compile(r"[a-z0-9_]+")


# LIGHT SUFFIX FOLDING, and it was forced by evidence rather than chosen. Exact-token matching
# fixed the flood and immediately broke an older bar (test_recall_match): the query "salience
# promotion consolidation track" stopped finding lessons about "salient", "promote" and "tracks".
# That older pin was labelled OR-matching, but what it was really defending was MORPHOLOGY -- the
# old substring test caught "track" inside "tracks" by accident. Folding a few suffixes serves both
# bars honestly instead of weakening either: word forms match, fragments still do not.
# Longest suffix first; the stem must stay >=4 characters so short words are left alone.
_SUFFIXES = ("ations", "ation", "ions", "ion", "ences", "ence", "ances", "ance",
             "ents", "ent", "ings", "ing", "ed", "es", "s", "e")


def _stem(tok: str) -> str:
    for suf in _SUFFIXES:
        if tok.endswith(suf) and len(tok) - len(suf) >= 4:
            return tok[:-len(suf)]
    return tok


def _content_terms(query: str) -> List[str]:
    """Query words that carry meaning, folded to stems. Single characters go too: they cannot
    discriminate and they were half the flood."""
    return [_stem(t) for t in _TOKEN.findall(str(query or "").lower())
            if t not in _STOPWORDS and len(t) > 1]


def _tokens_of(text: str) -> set:
    """WORD stems, not substrings -- so 'track' still matches 'tracks' while 'state' no longer
    matches 'statement'."""
    return {_stem(t) for t in _TOKEN.findall(str(text or "").lower())}


def _min_hits(n_terms: int) -> int:
    """How many content terms must actually land before a record counts as an answer.

    One term matching out of ten is not a match, it is a coincidence -- and returning it ranked is
    what made the corpus look like it knew things it did not. Short queries keep a floor of one
    because there is nothing to be relative to.
    """
    if n_terms <= 2:
        return 1
    return max(2, -(-n_terms // 4))         # ceil(n/4), never below 2

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
        log_dir = repo_root() / "coordinator_logs"
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
            legacy_file = repo_root() / "session_logs" / "learnings.jsonl"
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

    # ----- repeats (T253) -------------------------------------------------------------------
    #: A REPEAT is evidence ABOUT a lesson: the lesson existed, and the mistake happened anyway.
    #:
    #: Nothing here measured that before. `value rate` divided by every surfacing while 95.2% of
    #: its denominator had never been voted on -- a feedback-COVERAGE number under a QUALITY
    #: label. `related_to` measures corpus REDUNDANCY (180 of 831 lessons resemble another, but
    #: zero reach the strong threshold and only 9 match problem+solution, so the corpus is
    #: clean). Neither can see a mistake recurring, because the pattern is: write ONE lesson,
    #: then repeat the mistake without writing more.
    #:
    #: THE COUNT IS A FLOOR, NEVER A RATE. It counts only repeats someone NOTICED, so its true
    #: denominator is unknowable. Rendering it as a percentage would recreate exactly the defect
    #: it replaces. `repeat_report()` refuses to emit one and says so in its own payload.
    REPEAT_INDEX = "learn:repeats"

    def record_repeat(self, of: str, agent_id: str = "", what: str = "",
                      recall_outcome: str = "") -> Dict[str, Any]:
        """Record that a lesson which ALREADY EXISTED was violated anyway.

        `recall_outcome` is the field that earns its place: a repeat where recall FIRED is a
        READING failure, and one where it was SUPPRESSED is a TARGETING failure. Those need
        opposite fixes and one field separates them, which no other instrument records.

        Raises on an unknown lesson rather than filing an unresolvable pointer -- that is how a
        ledger fills with claims nobody can check.
        """
        key = f"learn:experiment:{of}"
        if not of or not self.store.exists(key):
            raise ValueError(
                f"cannot record a repeat of {of!r}: no such lesson. A repeat is a pointer AT a "
                f"lesson; without a resolvable target it is just an unverifiable claim.")

        original = self._load_experiment(of) or {}
        now = datetime.utcnow()
        elapsed = 0.0
        try:
            ts = original.get("timestamp")
            if ts:
                elapsed = max(0.0, (now - datetime.fromisoformat(str(ts))).total_seconds())
        except Exception:
            elapsed = 0.0                       # unparseable original timestamp -> 0, not a guess

        # A timestamp alone is NOT unique here. Windows clock granularity let two repeats
        # recorded in the same tick produce the same id, and `sadd` then silently deduped them
        # -- three became two. Caught by this slice's own pin. In a counter whose only claim is
        # to be an honest FLOOR, silently merging two real events is the one unacceptable bug.
        rid = f"{of}:{now.strftime('%Y%m%dT%H%M%S%f')}:{uuid.uuid4().hex[:8]}"
        rec = {"id": rid, "of": of, "agent_id": str(agent_id or ""), "what": str(what or ""),
               "recall_outcome": str(recall_outcome or ""), "at": now.isoformat(),
               "elapsed_s": round(elapsed, 3)}
        try:
            self.store.hset(f"learn:repeat:{rid}", mapping={k: str(v) for k, v in rec.items()})
            self.store.sadd(self.REPEAT_INDEX, rid)
        except Exception as e:
            self.logger.warning(f"repeat not persisted: {e}")
        return rec

    # NOTE: there is deliberately no `repeat_count()`. The first draft had one, check_wiring
    # flagged it as a public function with no production caller, and it was right --
    # `repeat_report()["count"]` already answers it. A second way to ask the same question is
    # a second thing to keep in agreement.

    def repeat_report(self) -> Dict[str, Any]:
        """The multifaceted record, deliberately not a score.

        Returns a count, the lessons ranked by how often they were violated, and the split by
        what recall did at the moment. NO percentage appears anywhere and no key is named a
        rate -- pinned, because this counts only what was noticed and a rate would imply a
        denominator nobody has.

        The `most_violated` list is the useful artifact: a lesson that exists, is good, and gets
        violated anyway is a targeting failure WITH A KNOWN RIGHT ANSWER, which is the rarest
        thing in the corpus and exactly the training set the recall trigger problem needs.
        """
        entries: List[Dict[str, Any]] = []
        try:
            for rid in (self.store.smembers(self.REPEAT_INDEX) or []):
                rec = self.store.hgetall(f"learn:repeat:{rid}") or {}
                if rec:
                    entries.append(rec)
        except Exception:
            pass

        by_lesson: Dict[str, int] = {}
        by_outcome: Dict[str, int] = {}
        for e in entries:
            by_lesson[e.get("of", "?")] = by_lesson.get(e.get("of", "?"), 0) + 1
            o = e.get("recall_outcome") or "unrecorded"
            by_outcome[o] = by_outcome.get(o, 0) + 1

        return {
            "count": len(entries),
            # Declared in the payload, not just the docstring: a consumer that renders this
            # cannot claim it did not know.
            "floor_not_rate": True,
            "caveat": "counts only repeats that were NOTICED; the true denominator is unknown",
            "most_violated": sorted(by_lesson.items(), key=lambda kv: -kv[1]),
            "by_recall_outcome": by_outcome,
            "entries": sorted(entries, key=lambda e: str(e.get("at", ""))),
        }

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

    def _rebuild_index(self) -> None:
        """Rebuild `learn:experiments:all` as a DERIVED projection over the hash plane.

        Membership = every discoverable record, UNION whatever the index already holds.
        Union-only is load-bearing and inherited from repair_learning_index.py: a record this
        rebuild cannot see is KEPT rather than silently dropped, because a repair that can lose
        data is worse than the defect it fixes.

        Order = newest-first by the record's own timestamp, the list's documented semantic
        (see the module header). Membership is integrity and derives here; QUALITY filtering
        belongs to the recall surface, not to this list -- the claude/deepseek fence settled
        that split on 2026-07-27 (gating membership on an anchor predicate would strand
        unanchored lessons where no outcome loop could ever redeem them: is_benched's
        self-seal, moved one layer down).

        ONE bulk read, no per-record round trips. Scale caveat, named honestly: this is O(n)
        per new lesson. At 464 that is one hgetall_prefix. At Daniel's millions target the
        derivation must move to a periodic batch with an atomic swap (Postgres REFRESH
        MATERIALIZED VIEW CONCURRENTLY: build under a temp key, RENAME over). The Store ABC
        has no rename today, so that is a named follow-up rather than a silent omission.
        """
        prefix = "learn:experiment:"
        rows: Dict[str, str] = {}
        for key, val in (self.store.hgetall_prefix(prefix) or {}).items():
            if prefix not in key:
                continue
            name = key.split(prefix, 1)[1]
            if name:
                rows[name] = str((val or {}).get("timestamp") or "")
        for name in self.store.lrange("learn:experiments:all", 0, -1):
            rows.setdefault(name, "")          # union-only: never drop what we cannot resolve
        if not rows:
            return
        ordered = [n for n, _ in sorted(rows.items(), key=lambda kv: (kv[1], kv[0]),
                                        reverse=True)]
        self.store.delete("learn:experiments:all")
        self.store.rpush("learn:experiments:all", *ordered)

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
            # JSON like metrics, not a bare string: base_score ITERATES this, so a plain
            # "a.py,b.py" would iterate per-CHARACTER and become dozens of one-letter "paths"
            # that match nothing -- a silent ranking corruption rather than an error. Decoded
            # back to a list at both read sites, exactly as metrics is.
            "files_affected": json.dumps(learning_signal.get("files_affected") or []),
            "confidence": _s(learning_signal.get("confidence"), "medium"),
            "category": _s(learning_signal.get("category"), "uncategorized"),
            # THE DOMAIN AXIS. Declared if the writer knows, inferred otherwise -- because a field
            # nothing fills stays empty (that is why --category has been offered for months and
            # essentially every lesson still reads 'uncategorized'). Inference is biased hard toward
            # the default: ~840 lessons predate domains and all of them MEAN system by construction,
            # so only a clear signal moves one.
            "domain": _s(learning_signal.get("domain")) or infer_domain(learning_signal),
            "agent_id": agent_id,
            # lossy summary + lossless pointer: the store record IS the raw for an
            # agent-authored learning, so it points at itself -> Distiller can keep it.
            "source": _s(learning_signal.get("source"), f"learn:experiment:{experiment_id}"),
        }

        self.store.hset(f"learn:experiment:{experiment_id}", mapping=experiment_data)

        # MEMBERSHIP DERIVES FROM THE HASH PLANE -- it never accumulates.
        #
        # This gate used to read `is_new = not exists(learn:experiment:<id>)`, keyed on HASH
        # existence rather than INDEX membership. The consequence, measured live 2026-07-27:
        # 464 records, 16 indexed, 446 lessons invisible to every recall read path. Once an id
        # left the index while its hash survived, every later write saw is_new=False and skipped
        # the lpush, so the index could never rebuild itself through its own write path. It had
        # already been repaired once (24/406 on 2026-07-25) and recurred inside two days.
        #
        # Strategy from deepseek's prior-art half (materialized-view maintenance): FULL REBUILD
        # beats incremental repair when the mutation log is unreliable -- and this one is
        # provably unreliable. The list is a cached projection; the hashes are the truth.
        # Cost is bounded: the common path (re-recording an already-indexed lesson) is ONE
        # lrange. The rebuild fires only when this id is absent, which is exactly the new-lesson
        # and self-heal cases, and costs one bulk hgetall_prefix -- no per-record round trips.
        try:
            if experiment_id not in set(self.store.lrange("learn:experiments:all", 0, -1)):
                self._rebuild_index()
        except Exception as e:                    # never let indexing lose the record itself
            self.logger.warning(f"index rebuild skipped for {experiment_id}: {e}")
        if experiment_id not in set(self.store.lrange(f"learn:agent:{agent_id}", 0, -1)):
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
        for field in ("metrics", "files_affected"):
            if data and field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return data

    # ----- read: search -----
    def search_learnings_by_keyword(self, keyword: str,
                                    domain: Optional[str] = None,
                                    agent: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search learnings by keyword, optionally scoped to one domain and/or one agent.

        Semantic Relationship: SearchResults derived_from Learnings (by keyword)

        The original here OR-matched substrings with no floor, which meant a long question reached
        most of the corpus and returned it ranked. See the module header for the measurement. Now:
        stopwords dropped, WORD tokens rather than substrings, and a minimum number of content terms
        that must actually land. `domain` scopes the answer so shader work stops competing with
        bus-lane work -- pass None to search everything, which keeps every existing caller working.

        T260: `agent` scopes to one author's archive -- "what has Navi learned about X", the
        per-resident read the residents directive makes load-bearing. The filter sits ABOVE the
        weak-match fallback on purpose: a confession about one agent's archive may only confess
        that agent's lessons, because the degraded answer must be a SUBSET of the normal one
        (the audited fallback class). Matching strips and lowercases both sides -- the store
        persists agent ids verbatim, trailing whitespace included (probed live for T258b).
        """
        try:
            terms = _content_terms(keyword)
            if not terms:
                return []
            want_agent = str(agent).strip().lower() if agent else None
            need = _min_hits(len(terms))
            scored, weak, seen = [], [], set()
            for exp_id in self.store.lrange("learn:experiments:all", 0, -1):
                if exp_id in seen:
                    continue
                seen.add(exp_id)
                data = self._load_experiment(exp_id)
                if not data:
                    continue
                # A record written before domains existed has no field; it means system, which is
                # what DEFAULT_DOMAIN says, so the filter stays correct across the backfill gap.
                if domain and (data.get("domain") or DEFAULT_DOMAIN) != domain:
                    continue
                # T260 agent scope. A record with NO author cannot prove it is the wanted
                # agent's, so it is excluded from a scoped read -- absence is not membership.
                if want_agent is not None:
                    author = str(data.get("agent_id") or data.get("agent") or "").strip().lower()
                    if author != want_agent:
                        continue
                hay = _tokens_of(exp_id) | _tokens_of(" ".join(str(v) for v in data.values()))
                hits = sum(1 for t in terms if t in hay)
                if hits >= need:
                    scored.append((hits, {"id": exp_id, **data}))
                elif hits:
                    weak.append((hits, {"id": exp_id, **data}))
            scored.sort(key=lambda x: -x[0])   # most terms matched first
            if scored:
                return [d for _, d in scored]
            # NOTHING CLEARED THE FLOOR, BUT SOMETHING TOUCHED. Returning silence here would be the
            # mirror of the defect this work removes: a nine-word grab-bag ("shader glow tile gap
            # vignette tonemap hue palette wireframe") spreads one hit across many real shader
            # lessons and clears no floor, so a strict cut answers "I know nothing" about a corpus
            # that demonstrably knows. So: hand back the best few, FLAGGED, and let the caller
            # decide. Capped hard, because the flag is a confession and confessions do not scale.
            weak.sort(key=lambda x: -x[0])
            return [dict(d, weak_match=True) for _, d in weak[:5]]
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
                for field in ("metrics", "files_affected"):
                    if field in data and isinstance(data[field], str):
                        try:
                            data[field] = json.loads(data[field])
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
