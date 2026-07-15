"""
Agent Memory: a multi-type memory for agents (decisions, experiences, reflections, approaches)

Semantic Relationship: AgentMemory persists_through Store

WHAT THIS IS
------------
A richer learning model than the experiment-signal `LearningStore`. It mirrors
the standard agent-memory taxonomy (CoALA):

- Decisions   (ADR-style)            -> semantic memory  ("we decided X because Y")
- Experiences (task/approach/result) -> episodic memory  ("what happened on an attempt")
- Reflections (what went wrong/help) -> the Reflexion loop (episodic -> semantic)
- Approaches  (per-component)        -> procedural memory ("what works for a component")

PHASE A (foundation fit)
------------------------
This persists through a `Store` (core.foundation.store) -- Redis when up, File
always -- so it survives Redis being down (the old learning/store.py was
Redis-only and returned empty on an outage). Behavior and shape are otherwise
unchanged from that original; richer retrieval, temporal supersession, and the
consolidation->chronicle loop are later phases (see docs/learning-memory-integration-plan.md).

It uses the `mem:` namespace, distinct from the `learn:` namespace of the
experiment-signal LearningStore, so the two never collide.

Usage:
    from core.learning.agent_memory import get_agent_memory

    mem = get_agent_memory()
    mem.decide(title="Use Sentinel", decision="Redis HA via Sentinel", rationale=["auto failover"])
    mem.record(task="install ComfyUI", success=True, learnings=["use custom nodes"])
    ctx = mem.get_context("what should I know before installing?")
"""

import json
import logging
import unicodedata
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

from core.foundation.store import CASConflict, Store, create_store

logger = logging.getLogger("agent_memory")

# RB-8 (Wave 3, docs/w3-build-spec-2026-07-11.md): the per-title head sentinel keyspace.
# Decisions-scoped on purpose -- experiences/reflections can grow their own heads later.
HEAD_KEY_PREFIX = "mem:decisions:head:"


class SupersedeRaceError(RuntimeError):
    """Lost the per-title head race (RB-8). The message names the winning head id so the
    caller can re-read and retry against it -- decide_with_retry() does exactly that."""


class SupersedeTargetError(SupersedeRaceError, ValueError):
    """RB-10: supersede target refused BEFORE any write. The message names the current
    head (for stale/superseded targets) or states the target doesn't exist. Raised
    pre-hset so the caller sees a teaching error with zero state mutation.

    is-a SupersedeRaceError: a stale target is the SAME race the CAS claim would lose
    post-write, detected early (so the RB-8 race contract holds and decide_with_retry
    auto-resolves it without the write+claim+cleanup cycle). is-a ValueError per the
    RB-10 frozen contract (tests/test_w3_rb9_rb10.py)."""


# RB-11 (Wave 3): the render-side chain-length warning threshold. Future T034 dial;
# until then a named constant the manifest will claim.
CHAIN_WARN_THRESHOLD = 50


def normalize_title(title: str) -> str:
    """RB-9: NFC + strip ONLY -- no case folding, no whitespace collapse. Case and
    spacing can carry meaning; precision first (reconciled Wave 3 spec; case-folding is
    the named escalation path if a real collision ever bites)."""
    return unicodedata.normalize("NFC", str(title or "")).strip()


@dataclass
class Decision:
    id: str
    title: str
    status: str
    context: str
    decision: str
    rationale: List[str]
    alternatives: List[Dict]
    consequences: Dict[str, List[str]]
    created_at: str
    session_id: str = ""
    supersedes: Optional[str] = None   # id of the decision this one replaces
    superseded: bool = False           # set True when a newer decision supersedes it


@dataclass
class Experience:
    id: str
    task: str
    approach: str
    result: str
    success: bool
    score: float
    learnings: List[str]
    timestamp: str
    session_id: str = ""
    supersedes: Optional[str] = None
    superseded: bool = False


@dataclass
class Reflection:
    id: str
    task: str
    attempt: int
    what_went_wrong: str
    why_it_failed: str
    what_would_help: str
    corrective_action: str
    confidence: float
    created_at: str


class AgentMemory:
    """
    Multi-type agent memory backed by a swappable Store.

    Semantic Relationship: AgentMemory indexes_memories_in Store

    Stores decisions, experiences, reflections, and per-component approaches,
    and assembles relevant context for a task.
    """

    PREFIX = "mem"
    KEY_DECISIONS = f"{PREFIX}:decisions"
    KEY_DECISION_INDEX = f"{PREFIX}:decisions:idx"
    KEY_EXPERIENCES = f"{PREFIX}:experiences"
    KEY_EXPERIENCES_SUCCESS = f"{PREFIX}:experiences:success"
    KEY_EXPERIENCES_FAILURE = f"{PREFIX}:experiences:failure"
    KEY_REFLECTIONS = f"{PREFIX}:reflections"
    KEY_REFLECTION_INDEX = f"{PREFIX}:reflections:idx"
    KEY_APPROACHES = f"{PREFIX}:approaches"
    KEY_APPROACH_BY_COMPONENT = f"{PREFIX}:approaches:by_component"

    MAX_REFLECTIONS = 50  # keep only the newest N reflections in the index

    def __init__(self, store: Optional[Store] = None):
        self.store = store if store is not None else create_store(prefer_redis=True)

    @property
    def redis_available(self) -> bool:
        return bool(getattr(self.store, "redis_available", False))

    def _gen_id(self, prefix: str) -> str:
        # RB-8 R-c: second-resolution timestamp + 4 random digits collided at ~1e-4 per
        # same-second pair, and hset silently overwrote the loser. uuid4 hex keeps ids
        # prefix-sortable and drops collision odds ~5 orders.
        return f"{prefix}_{datetime.now().strftime('%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # ----- decisions (semantic) -----
    def _retire_record(self, hash_key: str, record_id: str) -> None:
        """Mark a stored record superseded (inactive) so reads/ranking skip it."""
        from core.primitives import supersession
        data = self.store.hget(hash_key, record_id)
        if data:
            rec = supersession.retire(json.loads(data))
            self.store.hset(hash_key, field=record_id, value=json.dumps(rec))

    def decide(self, title: str, decision: str, context: str = "",
               rationale: List[str] = None, alternatives: List[Dict] = None,
               consequences: Dict[str, List[str]] = None, session_id: str = "",
               supersedes: Optional[str] = None) -> str:
        """Record an architectural decision. If `supersedes` is given, the named prior
        decision is retired (Supersession), so reads/ranking surface only this.

        RB-8 (Wave 3): SINGLE-ATTEMPT under the per-title head sentinel. The write order
        is record -> claim head via CAS -> retire old; only the claim WINNER retires.
        A lost race retires this call's own record and raises SupersedeRaceError naming
        the winner -- doors go through decide_with_retry(), which re-reads and retries.
        RB-9: the stored title is normalize_title()'d (NFC + strip)."""
        title = normalize_title(title)
        # RB-10: validate the supersede target BEFORE any write (existence, active, non-dangling).
        # A teaching error here saves the write+claim+cleanup cycle for invalid targets.
        if supersedes:
            err = self._validate_supersede_target(supersedes)
            if err:
                raise SupersedeTargetError(err)
        dec_id = self._gen_id("ADR")
        created = datetime.now().isoformat()
        dec = Decision(
            id=dec_id, title=title, status="accepted", context=context,
            decision=decision, rationale=rationale or [], alternatives=alternatives or [],
            consequences=consequences or {"positive": [], "negative": []},
            created_at=created, session_id=session_id, supersedes=supersedes,
        )
        try:
            self.store.hset(self.KEY_DECISIONS, field=dec_id, value=json.dumps(asdict(dec)))
            self.store.zadd(self.KEY_DECISION_INDEX, {dec_id: datetime.fromisoformat(created).timestamp()})
        except Exception as e:
            logger.error(f"Failed to record decision: {e}")
            return ""
        # Claim the title head. Claimable = fresh title, the id we expected to replace,
        # or a current head that no longer names an ACTIVE record (dangling after manual
        # deletion, or retired-in-place by retire_decision -- which never touches the
        # sentinel by design; reconciled Q4).
        head_key = HEAD_KEY_PREFIX + title

        def _claim(current: Optional[str]) -> Optional[str]:
            if current is None or current == supersedes or not self._is_active(current):
                return dec_id
            return None   # a foreign ACTIVE head owns this title -- lose cleanly

        try:
            result = self.store.update_atomic(head_key, _claim, retries=1)
        except CASConflict:
            result = self.store.get(head_key)   # the cycle itself raced; whoever's there won
        except Exception as e:
            logger.error(f"Head claim failed for '{title}': {e}")
            result = None
        if result != dec_id:
            # Lost: never leave our record active-but-unheaded (that IS the fork).
            self._retire_record(self.KEY_DECISIONS, dec_id)
            raise SupersedeRaceError(
                f"lost the title race for '{title}': current head is {result}; "
                f"re-read and retry against it (decide_with_retry does this)")
        if supersedes:
            self._retire_record(self.KEY_DECISIONS, supersedes)
        logger.info(f"Decision {dec_id}: {title}")
        return dec_id

    def _is_active(self, dec_id: str) -> bool:
        """Whether a decision id names an existing, non-superseded record. PURE read."""
        try:
            data = self.store.hget(self.KEY_DECISIONS, dec_id)
            return bool(data) and not json.loads(data).get("superseded")
        except Exception:
            return False

    def _resolve_head(self, title_n: str) -> Optional[str]:
        """Current ACTIVE head id for a normalized title. Reads the sentinel; when it is
        missing, dangling, or names a retired record, falls back to the newest ACTIVE
        record by scan (the RB-8 lazy bootstrap for pre-head corpora). None = fresh."""
        cur = self.store.get(HEAD_KEY_PREFIX + title_n)
        if cur and self._is_active(cur):
            return cur
        cands = [d for d in self.get_decisions(days=3650)
                 if normalize_title(d.title) == title_n]
        if not cands:
            return None
        cands.sort(key=lambda d: (d.created_at, d.id), reverse=True)
        return cands[0].id

    def decide_with_retry(self, title: str, decision: str, retries: int = 3, **kwargs) -> str:
        """The DOOR-level RB-8 helper: resolve the current head for `title`, decide once,
        and on a lost race re-read the head and retry with the corrected supersedes.
        Owns the supersedes pointer entirely (callers with an EXPLICIT target use
        decide() and handle SupersedeRaceError themselves). Cap `retries` attempts, then
        the last SupersedeRaceError propagates -- loud, never a silent fork. Retry lives
        HERE and not in decide() so a conflict never re-generates ids or rewrites bodies
        wastefully (reconciled Wave 3 spec)."""
        title_n = normalize_title(title)
        last: Optional[SupersedeRaceError] = None
        for _ in range(max(1, retries)):
            head = self._resolve_head(title_n)
            try:
                return self.decide(title_n, decision, supersedes=head, **kwargs)
            except SupersedeRaceError as e:
                last = e
        raise last

    # ----- RB-9: normalization collision scan -----
    def find_normalization_collisions(self) -> List[Dict]:
        """Scan active decisions for title pairs that normalize-equal but STORED different.
        RB-9 (W3): flags pre-existing near-duplicates for manual ruling; never auto-merges.
        FULL-corpus scan: legacy twins are old by nature (pre-RB-9 writes), so a lookback
        window would hide exactly the records this exists to find (pinned in
        tests/test_w3_rb9_rb10.py with 2026-01 forgeries). Doctor/boot frequency, never
        the default read path. Returns {title, stored_variants, ids, count} per collision."""
        decisions = self.get_decisions(days=3650)
        by_norm: Dict[str, List[Decision]] = {}
        for d in decisions:
            n = normalize_title(d.title)
            by_norm.setdefault(n, []).append(d)
        hits = []
        for norm, group in by_norm.items():
            distinct = sorted(set(d.title for d in group))
            if len(distinct) > 1:
                hits.append({"title": norm, "stored_variants": distinct,
                              "ids": [d.id for d in group], "count": len(group)})
        hits.sort(key=lambda h: h["title"])
        return hits

    # ----- RB-10: supersede-target validation -----
    def _validate_supersede_target(self, supersedes: str) -> str | None:
        """RB-10 pre-write validation. Returns a teaching-error string if the target is
        invalid, or None if it clears. Checks: existence, non-self (trivially: decide()
        hasn't minted the new id yet, so no self-check needed here), and ACTIVE status.
        An already-superseded target names the current head in the error."""
        data = self.store.hget(self.KEY_DECISIONS, supersedes)
        if not data:
            return f"supersede target '{supersedes}' does not exist; drop --supersedes for a fresh first note"
        rec = json.loads(data)
        if rec.get("superseded"):
            title_n = normalize_title(rec.get("title", ""))
            head = self.store.get(HEAD_KEY_PREFIX + title_n)
            if head and self._is_active(head):
                return (f"supersede target '{supersedes}' is already superseded "
                        f"(current head is '{head}'); drop --supersedes to auto-resolve, "
                        f"or name the current head explicitly")
            return (f"supersede target '{supersedes}' is already superseded "
                    f"and the sentinel for its title is missing/dangling; "
                    f"drop --supersedes to auto-resolve")
        return None

    def retire_decision(self, dec_id: str) -> bool:
        """Retire a decision with NO successor (supersede-into-nothing) -- the tombstone for
        one-shot notes (consumed handoffs, placeholders, done-arc status notes). Reversible at
        the store level (the record keeps its body; only the superseded flag flips). Returns
        True iff the record existed and is now retired (P1 / T021)."""
        try:
            if not self.store.hget(self.KEY_DECISIONS, dec_id):
                return False
            self._retire_record(self.KEY_DECISIONS, dec_id)
            data = self.store.hget(self.KEY_DECISIONS, dec_id)
            return bool(data and json.loads(data).get("superseded"))
        except Exception as e:
            logger.error(f"Failed to retire decision {dec_id}: {e}")
            return False

    # ----- RB-10: all-retired-title detector -----
    def get_retired_titles(self) -> List[Dict]:
        """Return titles whose every record is retired (vanished groups). Additive surface:
        default get_decisions() unchanged. Time-bounded to 90 days per the FM2 mitigation;
        older vanished groups surface only via --all. Each entry: {title, last_active_id,
        retired_count, last_retired_at}."""
        decisions = self.get_decisions(days=90, include_superseded=True)
        by_title: Dict[str, List[Decision]] = {}
        for d in decisions:
            n = normalize_title(d.title)
            by_title.setdefault(n, []).append(d)
        gone = []
        for title_n, group in by_title.items():
            if all(d.superseded for d in group):
                newest = max(group, key=lambda d: d.created_at)
                gone.append({"title": title_n, "last_active_id": newest.id,
                             "retired_count": len(group),
                             "last_retired_at": newest.created_at})
        gone.sort(key=lambda g: g["title"])
        return gone

    # ----- RB-11: migration idempotency -----
    def run_migration_once(self, name: str, fn) -> bool:
        """Run `fn()` exactly once, guarded by a per-name cas pin key `mem:migration:{name}`.
        Returns True if the migration ran; False if the pin was already present (no-op).
        The migration body must ALSO be inherently idempotent -- the pin is an optimization,
        not the sole safety mechanism (RB-11 FM1)."""
        key = f"mem:migration:{name}"
        claimed = self.store.cas(key, None, "done")
        if not claimed:
            return False
        try:
            fn()
        except Exception:
            self.store.delete(key)   # roll back the pin so a retry can re-attempt
            raise
        return True

    # ----- RB-11: chain-length warning -----
    def get_long_chains(self, threshold: int | None = None) -> List[Dict]:
        """Return titles whose superseded chain length exceeds the threshold (default
        CHAIN_WARN_THRESHOLD=50). Render-side only -- never on the default read path.
        FULL-corpus count: a chain that took months to grow is precisely the pathology
        this warns about, and a 90d window would undercount it (the pre-registered pin
        forges 2026-01 records; pin beats the spec's 90d line -- reconciled at wake-verify
        2026-07-11). Each entry: {title, count, oldest_id, newest_id}."""
        t = threshold if threshold is not None else CHAIN_WARN_THRESHOLD
        decisions = self.get_decisions(days=3650, include_superseded=True)
        by_title: Dict[str, List[Decision]] = {}
        for d in decisions:
            n = normalize_title(d.title)
            by_title.setdefault(n, []).append(d)
        long = []
        for title_n, group in by_title.items():
            if len(group) > t:
                newest = max(group, key=lambda d: d.created_at)
                oldest = min(group, key=lambda d: d.created_at)
                long.append({"title": title_n, "count": len(group),
                             "oldest_id": oldest.id, "newest_id": newest.id})
        long.sort(key=lambda c: -c["count"])
        return long

    def get_decisions(self, days: int = 30, include_superseded: bool = False) -> List[Decision]:
        """Get decisions from the last `days`, newest first. Active (not superseded) only by
        default; `include_superseded=True` is the archaeology path (notes --all)."""
        decisions = []
        cutoff = (datetime.now() - timedelta(days=days)).timestamp()
        try:
            for dec_id in self.store.zrangebyscore(self.KEY_DECISION_INDEX, cutoff, "+inf"):
                data = self.store.hget(self.KEY_DECISIONS, dec_id)
                if data:
                    d = json.loads(data)
                    if d.get("superseded") and not include_superseded:
                        continue  # retired by a newer decision
                    decisions.append(Decision(**d))
            # RB-12 (W3): (created_at, title, id) descending -- title as secondary tiebreak
            # before the opaque id. Deterministic across calls AND backends (zset ordering fixed
            # at the store level per the differential harness finding).
            decisions.sort(key=lambda x: (x.created_at, x.title, x.id), reverse=True)
        except Exception as e:
            logger.error(f"Failed to get decisions: {e}")
        return decisions

    # ----- experiences (episodic) -----
    def record(self, task: str, success: bool, approach: str = "", result: str = "",
               score: float = 0, learnings: List[str] = None, session_id: str = "",
               supersedes: Optional[str] = None) -> str:
        """Record an experience. If `supersedes` is given, the named prior
        experience is retired (Supersession)."""
        exp_id = self._gen_id("exp")
        created = datetime.now().isoformat()
        exp = Experience(
            id=exp_id, task=task[:200], approach=approach[:100] if approach else "",
            result=result[:200] if result else ("Success" if success else "Failed"),
            success=success, score=score, learnings=learnings or [],
            timestamp=created, session_id=session_id, supersedes=supersedes,
        )
        try:
            self.store.hset(self.KEY_EXPERIENCES, field=exp_id, value=json.dumps(asdict(exp)))
            key = self.KEY_EXPERIENCES_SUCCESS if success else self.KEY_EXPERIENCES_FAILURE
            self.store.zadd(key, {exp_id: datetime.fromisoformat(created).timestamp()})
            if supersedes:
                self._retire_record(self.KEY_EXPERIENCES, supersedes)
            logger.info(f"Experience {exp_id}: {task[:40]}")
            return exp_id
        except Exception as e:
            logger.error(f"Failed to record experience: {e}")
            return ""

    def get_similar(self, task: str, limit: int = 5) -> List[Experience]:
        """Find similar past experiences (keyword overlap; richer retrieval is Phase C)."""
        similar = []
        seen = set()
        try:
            for key in [self.KEY_EXPERIENCES_SUCCESS, self.KEY_EXPERIENCES_FAILURE]:
                for exp_id in self.store.zrange(key, 0, 50, desc=True):
                    if exp_id in seen:
                        continue
                    data = self.store.hget(self.KEY_EXPERIENCES, exp_id)
                    if data:
                        parsed = json.loads(data)
                        if parsed.get("superseded"):
                            continue  # retired by a newer experience
                        exp = Experience(**parsed)
                        if any(w in task.lower() for w in exp.task.lower().split() if len(w) > 3):
                            seen.add(exp_id)
                            similar.append(exp)
                            if len(similar) >= limit:
                                break
        except Exception as e:
            logger.error(f"Failed to get similar experiences: {e}")
        return similar

    def load_all_experiences(self) -> List[Experience]:
        """All active (not superseded) experiences, newest first across success+failure."""
        out, seen = [], set()
        try:
            for key in (self.KEY_EXPERIENCES_SUCCESS, self.KEY_EXPERIENCES_FAILURE):
                for exp_id in self.store.zrange(key, 0, -1, desc=True):
                    if exp_id in seen:
                        continue
                    data = self.store.hget(self.KEY_EXPERIENCES, exp_id)
                    if data:
                        parsed = json.loads(data)
                        if parsed.get("superseded"):
                            continue
                        seen.add(exp_id)
                        out.append(Experience(**parsed))
        except Exception as e:
            logger.error(f"Failed to load all experiences: {e}")
        return out

    # ----- reflections (Reflexion loop) -----
    def reflect(self, task: str, what_went_wrong: str, what_would_help: str,
                attempt: int = 1, confidence: float = 0.5) -> str:
        """Record a reflection on a failure."""
        refl_id = self._gen_id("refl")
        created = datetime.now().isoformat()
        refl = Reflection(
            id=refl_id, task=task[:100], attempt=attempt,
            what_went_wrong=what_went_wrong[:200], why_it_failed="",
            what_would_help=what_would_help[:200], corrective_action="",
            confidence=confidence, created_at=created,
        )
        try:
            self.store.hset(self.KEY_REFLECTIONS, field=refl_id, value=json.dumps(asdict(refl)))
            self.store.zadd(self.KEY_REFLECTION_INDEX, {refl_id: datetime.fromisoformat(created).timestamp()})
            # Keep only the newest MAX_REFLECTIONS by dropping the lowest-ranked.
            self.store.zremrangebyrank(self.KEY_REFLECTION_INDEX, 0, -(self.MAX_REFLECTIONS + 1))
            return refl_id
        except Exception as e:
            logger.error(f"Failed to reflect: {e}")
            return ""

    def get_insights(self, min_confidence: float = 0.6) -> List[Dict]:
        """Get actionable insights from recent reflections above a confidence floor."""
        insights = []
        try:
            for refl_id in self.store.zrange(self.KEY_REFLECTION_INDEX, 0, 50, desc=True):
                data = self.store.hget(self.KEY_REFLECTIONS, refl_id)
                if data:
                    r = json.loads(data)
                    if r.get("confidence", 0) >= min_confidence:
                        insights.append(r)
        except Exception as e:
            logger.error(f"Failed to get insights: {e}")
        return insights

    # ----- approaches (procedural) -----
    def register_approach(self, component: str, name: str, status: str,
                          learnings: List[str] = None, evidence: Dict = None) -> str:
        """Register an approach (working/failed/in_progress) for a component."""
        app_id = f"{component}_{name[:20].lower().replace(' ', '_')}_{datetime.now().strftime('%m%d%H%M')}"
        app = {
            "id": app_id, "component": component, "name": name, "status": status,
            "learnings": learnings or [], "evidence": evidence or {},
            "created_at": datetime.now().isoformat(),
        }
        try:
            self.store.hset(self.KEY_APPROACHES, field=app_id, value=json.dumps(app))
            existing = self.store.hget(self.KEY_APPROACH_BY_COMPONENT, component) or ""
            parts = [a for a in existing.split(",") if a] + [app_id]
            self.store.hset(self.KEY_APPROACH_BY_COMPONENT, field=component, value=",".join(parts))
            return app_id
        except Exception as e:
            logger.error(f"Failed to register approach: {e}")
            return ""

    def get_component_status(self, component: str) -> Dict[str, List[Dict]]:
        """Get all approaches for a component, grouped by status."""
        result = {"working": [], "failed": [], "in_progress": []}
        try:
            app_ids = self.store.hget(self.KEY_APPROACH_BY_COMPONENT, component) or ""
            for app_id in app_ids.split(","):
                if not app_id:
                    continue
                data = self.store.hget(self.KEY_APPROACHES, app_id)
                if data:
                    app = json.loads(data)
                    status = app.get("status", "failed")
                    if status in result:
                        result[status].append(app)
        except Exception as e:
            logger.error(f"Failed to get component status: {e}")
        return result

    # ----- retrieval + stats -----
    def get_context(self, query: str = "") -> Dict[str, Any]:
        """Assemble relevant memory for a task: decisions, experiences, insights, stats."""
        decisions = self.get_decisions(days=30)
        recent_experiences = []
        try:
            for exp_id in self.store.zrange(self.KEY_EXPERIENCES_SUCCESS, 0, 9, desc=True):
                data = self.store.hget(self.KEY_EXPERIENCES, exp_id)
                if data:
                    recent_experiences.append(Experience(**json.loads(data)))
        except Exception as e:
            logger.error(f"Failed to load recent experiences: {e}")

        return {
            "decisions": [asdict(d) for d in decisions[:5]],
            "recent_experiences": [asdict(e) for e in recent_experiences[:5]],
            "insights": self.get_insights()[:5],
            "stats": self.get_stats(),
        }

    def get_stats(self) -> Dict:
        """Overall memory statistics."""
        try:
            decisions = self.store.zcard(self.KEY_DECISION_INDEX)
            successes = self.store.zcard(self.KEY_EXPERIENCES_SUCCESS)
            failures = self.store.zcard(self.KEY_EXPERIENCES_FAILURE)
            reflections = self.store.zcard(self.KEY_REFLECTION_INDEX)
            total = successes + failures
            return {
                "decisions": decisions,
                "experiences": total,
                "success_rate": successes / total if total > 0 else 0,
                "reflections": reflections,
                "recent_successes": successes,
                "recent_failures": failures,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def log_failure(self, title: str, root_cause: str, fix_applied: str = "",
                    component: str = "system", learnings: List[str] = None,
                    session_id: str = "") -> str:
        """
        Log a failure: records it as an experience, a reflection, and indexed detail.

        Semantic Relationship: Failure recorded_as Experience AND Reflection
        """
        exp_id = self.record(
            task=title, success=False,
            approach=f"fix_attempt:{fix_applied[:50]}" if fix_applied else "",
            result=f"Failed: {root_cause[:100]}", score=0,
            learnings=learnings or [root_cause], session_id=session_id,
        )

        if component:
            try:
                self.store.zadd(f"{self.PREFIX}:experience:by_task:{component}",
                                {exp_id: datetime.now().timestamp()})
            except Exception as e:
                logger.error(f"Failed to index failure by component: {e}")

        refl_id = self.reflect(
            task=title[:100], what_went_wrong=title,
            what_would_help=(fix_applied or (learnings[0] if learnings else "Unknown")),
            attempt=1, confidence=0.8,
        )

        try:
            failure_data = {
                "id": exp_id, "title": title, "root_cause": root_cause,
                "fix_applied": fix_applied, "component": component,
                "learnings": learnings or [], "timestamp": datetime.now().isoformat(),
                "reflection_id": refl_id,
            }
            self.store.hset(f"{self.PREFIX}:failures:detailed", field=exp_id, value=json.dumps(failure_data))
            self.store.zadd(f"{self.PREFIX}:failures:index", {exp_id: datetime.now().timestamp()})
        except Exception as e:
            logger.error(f"Failed to store failure detail: {e}")

        logger.info(f"Failure logged: {title[:50]}")
        return exp_id


# Global instance
_agent_memory: Optional[AgentMemory] = None


def get_agent_memory(store: Optional[Store] = None) -> AgentMemory:
    """
    Get or create the global AgentMemory instance.

    T069 (reconciled spec: research/reviewed/t069-singleton-reconciliation-2026-07-15.md):
    the event_log three-branch shape. Explicit injection -> fresh; isolated mode
    (_AISETUP_TEST_ISOLATED) -> fresh per call, cache untouched (AgentMemory is a
    stateless wrapper over the Store, so fresh wrappers over the same isolated paths
    share state); canonical -> lazy singleton, unchanged.

    Semantic Relationship: AgentMemoryInstance references_to GlobalInstance
    """
    import os
    global _agent_memory
    if store is not None:
        return AgentMemory(store=store)
    if os.environ.get("_AISETUP_TEST_ISOLATED"):
        return AgentMemory()
    if _agent_memory is None:
        _agent_memory = AgentMemory()
    return _agent_memory


if __name__ == "__main__":
    mem = get_agent_memory()
    print("=" * 50)
    print("  AGENT MEMORY STATUS")
    print("=" * 50)
    for k, v in mem.get_stats().items():
        print(f"  {k}: {v}")
