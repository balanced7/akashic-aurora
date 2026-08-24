"""Recall-at-action (`core/recall`) — read the right knowledge AT THE MOMENT of action.

Semantic Relationship: Recall surfaces ActiveKnowledge for a PointOfAction (path | command)

The pain this closes: storage is passive — lessons are written far more than they are read when
they matter. Given the file path or shell command an agent is about to act on, return the FEW
highest-signal ACTIVE items (relevant lessons + a lock/peer-activity warning) with `source`
pointers. The one reusable engine consumed by BOTH the `recall-at` CLI verb AND the PreToolUse
hook's `additionalContext` (so it is wired by construction, never built-but-not-wired).

Design — deterministic, no-LLM, fail-soft (SOTA-informed; see docs/library/design/20260709_agent-experience-plan-akashic-aurora_405872.md):
- **keyword/path-first relevance** via the shared Ranker (no embedding on the hot path).
- **SHOW NOTHING unless it clears a relevance floor** — a weak, off-topic hint at action-time is
  worse than silence (context-rot). We gate on the Ranker's RELEVANCE component specifically, not
  the blended score, so a merely-important-but-irrelevant lesson never fires.
- **cap at a few entries** (default 3) — skeleton-first, lossy summary + lossless `source` pointer.
- **FAITH-1 gate** — recalled text runs through `faithfulness_report`; nothing unfaithful (a
  fabricated/unresolvable pointer) ever reaches the agent.
- **provenance-labelled** — each item is prefixed with outcome-status + author + claim-kind
  (worked / partial / unverified / anti-pattern; `advice` marks a forward-looking recommendation),
  so a self-authored, unverified hypothesis never returns framed as an external verified fact
  (Factor 1: opinion-laundering). Status reflects the AUTHOR'S OWN report (`worked` = self-reported
  success, not an independent check). The store already holds this; projection carries it to the surface.
- **fully degrades to empty** on any error — a recall path must never brick the action.

LATENCY: lesson items are served from a TTL disk cache (a fresh hook process can't hold an in-memory
one), so after warm-up a call is a ~1ms file read + rank, not a store round-trip. On a cold/down store
the cache returns last-known-good (stale fallback) instead of empty — this kills the cold-start empty.
The PreToolUse hook is also non-blocking + fail-open, so even a cold first call delays a hint, never the
action. Anti-repeat (don't re-surface a lesson already shown this session) is handled by the hook via
`exclude_sources`. Tunables: AKASHIC_RECALL_CACHE_TTL (sec), AKASHIC_RECALL_AT_ACTION=0 (off).
"""
from __future__ import annotations

import json

# T120 F2 (G11b): the ONE title-shaped-query heuristic. The CLI (cmd_recall), the
# ToolBox (knowledge_recall), and the pin (test_t120_surface_honesty_bounds) all import
# THIS — a second copy is the defect (same law as G5's one-derivation-function).
# Shape: source-prefixed slug with content after the prefix, OR a 3+-token slug.
TITLE_SHAPED_RE = r'^(?:(?:learn:experiment:|research:web:)\S+|\w{4,}(?:[\s_-]\w+){2,})$'
import os
import re
import tempfile
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
# generic tokens that carry no recall signal (tooling/noise) — never used as query terms.
_STOP = {"core", "self", "true", "false", "none", "null", "test", "tests", "json",
         "http", "https", "www", "com", "the", "and", "for", "with", "this", "that",
         "py", "python", "git", "main", "init", "args", "data", "path", "file",
         # conversational filler (plan-altitude queries are PROSE): in a 60-doc corpus these look
         # "rare" to IDF yet carry zero domain signal — the 'lets continue working' failure mode.
         "lets", "want", "need", "going", "gonna", "please", "continue", "keep", "just",
         "really", "think", "thing", "things", "make", "made", "work", "working", "would",
         "could", "should", "about", "some", "more", "next", "also", "into", "over",
         # domain-generic in THIS corpus (everything is an agent/system) + comparative filler —
         # same class as the existing file/path/test entries above.
         "system", "systems", "agent", "agents", "better", "good", "nice", "right", "well",
         "sure", "okay", "help", "using", "used", "does", "doesnt", "dont", "cant", "when"}

# --- warm disk cache: a fresh hook process can't keep an in-memory cache, so cache the projected
# lesson items to a small JSON file (read ~1ms) instead of cold-connecting the store every call.
# Fresh (within TTL) -> read it; expired -> refresh from the store; store fails (cold/down) -> fall
# back to the STALE cache (last-known-good) -- this is what kills the cold-start empty. Env-tunable.
# AKASHIC_RECALL_STATE_DIR overrides the state root (tests/conftest.py sets it suite-wide so
# no test can ever clobber the production cache -- the 2026-07-02 hermeticity leak).
_CACHE_DIR = os.getenv("AKASHIC_RECALL_STATE_DIR") or os.path.join(tempfile.gettempdir(), "akashic_recall")
_CACHE_FILE = os.path.join(_CACHE_DIR, "lesson_items.json")
_CACHE_TTL = float(os.getenv("AKASHIC_RECALL_CACHE_TTL", "120"))

# Age past which a surfaced lesson earns the one-line staleness cue in render() (first-party
# fold-in 2026-07-08: recalled memories "reflect what was true when written"). Env-tunable;
# 0 disables the cue entirely.
_STALE_CUE_DAYS = float(os.getenv("AKASHIC_STALE_CUE_DAYS", "30"))

# F0b (Forge): durable mirror of the injection ledger. The tempdir ledger above is 7-day
# observability; the Forge gate's axis-B validation set needs RETENTION (dual blind audit
# 2026-07-09: retention, not resolvability, was the gap). Own bounded stream so the raw
# event firehose stays clean (~44 entries/day -> maxlen 6000 = ~4.5 months).
# R2 slice 0 (2026-07-28): the OUTCOME sink -- every recall_at call, fired OR silent.
# recall:surface records only firings, so the census's 27%-silent target was unverifiable:
# a floor-silent call, an empty-query call and a crash-empty all left NO record. The
# denominator lives here, built BEFORE the correlation gate so the gate's effect lands on
# a baseline. JSONL in the state dir (same lifecycle as the injection ledger); reasons:
#   fired | floor_silent | empty_query | error_empty | disabled | gate_silent (slice 1, reserved)
_OUTCOME_DIR = os.getenv("AKASHIC_RECALL_STATE_DIR") or _CACHE_DIR
_OUTCOME_FILE = "recall_outcomes.jsonl"
_OUTCOME_MAX_BYTES = 4_000_000          # ~4MB ring; oldest half dropped on overflow


#: T251. The two rules that produce `excluded_silent`, kept as named constants because the
#: whole point of the slice is that they must never be collapsed again.
EXCL_ANTIREPEAT = "antirepeat"     # already shown this SESSION (exclude_sources)
EXCL_SELF_ECHO = "self_echo"       # the caller authored it within the self-echo window


def _note_exclusion(stats: Optional[Dict[str, int]], kinds) -> None:
    """Count one excluded ITEM, under EVERY rule that excluded it (T251).

    Both call sites used to bump one `excluded` counter, so the measurement that showed
    exclusion dominates silence 4:1 could not say WHICH rule dominated -- and the two have
    opposite fixes.

    `kinds` is a LIST, and that is the correction Gemini 3.1 Pro found in the first version:
    the anti-repeat branch `continue`d before `_self_echo` was ever evaluated, so an item
    breaking BOTH rules was recorded as anti-repeat only. The instrument's implicit promise --
    that loosening the rule it names will un-silence the call -- was false for exactly those
    items, which is the worst possible defect in an instrument built to choose between two
    rules.

    The TOTAL counts ITEMS, not rule-hits. It gates the outcome label through
    `excluded >= above_floor`, so double-counting an item that broke two rules would
    manufacture `excluded_silent` calls that never happened.
    """
    if stats is None or not kinds:
        return
    # A bare string is ONE kind. Left as-is it is iterable, and `for kind in kinds` would walk
    # it character by character -- producing excluded_a, excluded_n, excluded_t... This is the
    # exact defect Gemini 3.1 Pro reported in ask_many's `files` an hour ago, which I then
    # reproduced here inside the fix for it. Third instance of this class today.
    if isinstance(kinds, str):
        kinds = [kinds]
    stats["excluded"] = stats.get("excluded", 0) + 1
    for kind in kinds:
        key = f"excluded_{kind}"
        stats[key] = stats.get(key, 0) + 1


def _excl_kind(stats: Optional[Dict[str, int]]) -> str:
    """Which rule withheld this call: antirepeat | self_echo | mixed | "" when neither."""
    if not stats:
        return ""
    a = stats.get(f"excluded_{EXCL_ANTIREPEAT}", 0)
    s = stats.get(f"excluded_{EXCL_SELF_ECHO}", 0)
    if a and s:
        return "mixed"
    if a:
        return EXCL_ANTIREPEAT
    if s:
        return EXCL_SELF_ECHO
    return ""


def _record_outcome(outcome: str, reason: str = "", *, query: str = "",
                    n_items: int = 0, agent_id: str = "",
                    query_shape: str = "", excl_kind: str = "",
                    excl_counts: Optional[Dict[str, int]] = None) -> None:
    """One row per recall_at call. Best-effort by contract (P6): an exception here must
    never cost the caller its items -- observability must not wedge the path it observes."""
    try:
        os.makedirs(_OUTCOME_DIR, exist_ok=True)
        fp = os.path.join(_OUTCOME_DIR, _OUTCOME_FILE)
        try:                                    # bounded: drop the oldest half on overflow
            if os.path.getsize(fp) > _OUTCOME_MAX_BYTES:
                with open(fp, encoding="utf-8") as f:
                    keep = f.readlines()[-2000:]
                with open(fp, "w", encoding="utf-8") as f:
                    f.writelines(keep)
        except OSError:
            pass
        with open(fp, "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": time.time(), "outcome": outcome, "reason": reason,
                                "q": str(query)[:160], "n_items": int(n_items),
                                "agent": str(agent_id or ""),
                                # deepseek's R2 review: the census's NONE-NEEDED reasons are
                                # SHAPE reasons; a silent row must say what shape went silent
                                # or it cannot be audited against the pack that justified it.
                                "query_shape": str(query_shape or ""),
                                # T251: WHICH suppression rule withheld the call. Absent on
                                # every row written before 2026-08-08; those read as "unknown"
                                # in the breakdown rather than vanishing, because the old rows
                                # ARE the baseline that made this worth splitting.
                                "excl_kind": str(excl_kind or ""),
                                # T251b (Gemini 3.1 Pro): 'mixed' is a CALL-level label, so a
                                # call with 99 anti-repeat items and 1 self-echo item reads
                                # identically to a 1-and-1 call. The per-ITEM counts are the
                                # only thing that can say which rule dominates, which is the
                                # single question this instrument exists to answer.
                                "excl_counts": dict(excl_counts or {})}) + "\n")
    except Exception:
        pass


def silence_rate(window_s: float = 86400.0) -> Dict[str, Any]:
    """The number the census bar needs: over the window, {calls, fired, silent, by_reason}.
    Reads the outcome sink; zeros when absent (a missing file is 'no calls recorded', and
    the caller can tell that apart from '0% silent' by calls==0)."""
    out: Dict[str, Any] = {"calls": 0, "fired": 0, "silent": 0, "by_reason": {},
                           # T251: excluded_silent dominates silence 4:1 over floor_silent, and
                           # it merged two rules with opposite fixes. Broken out here so the
                           # tuning decision has a number behind it instead of a guess.
                           "excluded_by_kind": {}}
    try:
        cutoff = time.time() - float(window_s)
        with open(os.path.join(_OUTCOME_DIR, _OUTCOME_FILE), encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if float(row.get("at", 0)) < cutoff:
                    continue
                out["calls"] += 1
                if row.get("outcome") == "fired":
                    out["fired"] += 1
                else:
                    out["silent"] += 1
                    r = str(row.get("reason") or "unknown")
                    out["by_reason"][r] = out["by_reason"].get(r, 0) + 1
                    if r == "excluded_silent":
                        # "unknown", never dropped: every row written before T251 lacks the
                        # field, and those rows ARE the baseline that justified the split. A
                        # silent omission inside the instrument that measures silent omissions
                        # would be its own punchline.
                        # T251b (Gemini 3.1 Pro): `.get(k) or "unknown"` folded an EMPTY kind
                        # into the historical bucket. A pre-T251 row has NO key; a future row
                        # written with an empty kind -- a third exclusion rule bumping the
                        # total without setting either flag -- HAS the key. Merging them would
                        # hide a new rule inside the baseline, which is the exact merge this
                        # task exists to undo. Missing -> unknown; present-but-empty ->
                        # unclassified.
                        if "excl_kind" not in row:
                            k = "unknown"
                        else:
                            k = str(row.get("excl_kind") or "").strip() or "unclassified"
                        out["excluded_by_kind"][k] = out["excluded_by_kind"].get(k, 0) + 1
    except OSError:
        pass
    except Exception:
        pass
    return out


SURFACE_STREAM = "recall:surface"
SURFACE_MAXLEN = 6000

# Durable mirror of the OUTCOME stage (2026-07-25). Same reasoning as F0b one line up, and
# the same gap it was built to close: the tempdir ledger is ~7-day observability, but a
# PREVENTION rate is a TREND -- it needs weeks before it says anything, and a 7-day prune
# would destroy the series before it was long enough to read. That is the starved-index
# genus (a signal that exists, is individually retrievable, and is silently unavailable in
# aggregate), and it cost 382 lessons earlier tonight. Outcomes fire far more often than
# injections (per tool resolution, not per surfacing), so the bound is larger: at a few
# hundred/day, 20000 is roughly two months of series.
OUTCOME_STREAM = "recall:outcome"
OUTCOME_MAXLEN = 20000


def _parse_trigger(text: str) -> str:
    """The lesson convention encodes its own firing condition: 'Use when <symptom>, before
    <action>: <advice>'. Return that leading trigger clause ('' when absent) so matching can
    weight the DESIGNED trigger over incidental prose -- the vNext precision fix for lessons
    firing on generic tokens like 'continue working' (docs/library/design/20260701_recall-vnext-closing-the-four-loops-2026_b93539.md loop 2)."""
    m = re.match(r"\s*use\s+when\s+(.{3,240}?)(?::|\.\s|$)", str(text or ""), re.IGNORECASE)
    return m.group(1).strip() if m else ""


_BENCH_PROBE_DAYS = float(os.getenv("AKASHIC_BENCH_PROBE_DAYS", "14") or 14)
# How many benched lessons may probe in ONE pass. Unbounded probing was the defect
# deepseek found: past the age threshold EVERY benched lesson surfaced at once, so the
# cure reintroduced the slot-starvation it was meant to treat.
_BENCH_PROBE_MAX = int(os.getenv("AKASHIC_BENCH_PROBE_MAX", "3") or 3)


def _bench_probe_due(rec: Dict[str, Any]) -> bool:
    """Has this benched lesson been sidelined long enough to deserve one more look?

    Breaks the self-seal without abandoning slot economy. Deterministic on purpose: the
    caller feeds a TTL disk cache, so a random probe would make the cache irreproducible and
    two seats reading one corpus would disagree about what exists.

    `benched` holds the ISO timestamp of the bench (the flag IS the time -- see
    LearningStore.mark_benched). Unparseable or missing means we cannot tell how long it has
    been sidelined, and we probe: failing OPEN keeps a lesson reachable, and the cost of an
    unnecessary probe is one slot while the cost of never probing is a permanently lost
    lesson. AKASHIC_BENCH_PROBE_DAYS=0 disables probing entirely.
    """
    if _BENCH_PROBE_DAYS <= 0:
        return False
    stamp = str((rec or {}).get("benched") or "").strip()
    if not stamp:
        return True
    try:
        when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if when.tzinfo is not None:
            when = when.replace(tzinfo=None)
    except Exception:
        return True
    return (datetime.utcnow() - when).total_seconds() >= _BENCH_PROBE_DAYS * 86400


def _bench_probe_set(recs: List[Dict[str, Any]], is_benched) -> set:
    """WHICH benched lessons probe this pass -- at most _BENCH_PROBE_MAX, oldest bench first.

    Added after deepseek's review found the first version UNBOUNDED: every benched lesson past
    the age threshold probed on every cache refresh, so fifty benched lessons meant fifty
    probes competing with the active corpus. That destroys the slot economy the probe was
    written to preserve -- a cure that reintroduces the disease it treats.

    Oldest-first is a queue, not a preference: the most overdue lesson gets the slot, and when
    the curator re-benches a probe that earned nothing it stamps a FRESH timestamp, sending it
    to the back. Rotation therefore DEPENDS ON THE CURATOR RUNNING. If it stops, the same few
    lessons probe forever and the rest never get a turn -- a real coupling, recorded here
    rather than discovered later.
    """
    due = []
    for rec in recs:
        if not is_benched(rec):
            continue
        if _bench_probe_due(rec):
            due.append((str(rec.get("benched") or ""), _rec_name(rec)))
    due.sort()                       # ISO timestamps sort chronologically; "" (unknown) first
    return {name for _, name in due[:_BENCH_PROBE_MAX]}


def _rec_name(rec: Dict[str, Any]) -> str:
    return str(rec.get("experiment_name") or rec.get("experiment") or rec.get("name") or "")


def _project_items(recs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        from core.learning.learning_store import is_graduated, is_benched
    except Exception:
        def is_graduated(_):
            return False   # predicate unavailable -> fail OPEN (surface rather than lose)
        def is_benched(_):
            return False
    _probe_set = _bench_probe_set(recs, is_benched)
    items: List[Dict[str, Any]] = []
    for rec in recs:
        # A GRADUATED lesson (rule now enforced by automation -- LearningStore.mark_graduated)
        # never enters the recall cache: the hook/guardrail does its job, so the surface slot
        # goes to knowledge that still needs remembering. Full record stays one hop away.
        # A BENCHED lesson (curator: surfaced-often-never-credited) is out for the same
        # slot-economy reason -- and unlike graduation it is auto-reversed on new credit.
        if is_graduated(rec):
            continue
        # BENCHED: excluded from slots, but NOT excluded from existence -- and that
        # distinction is the whole fix.
        #
        # The slot-economy argument above is correct and is kept. What was wrong is that
        # `continue` also removed benched lessons from the only surface that AWARDS credit,
        # while the curator's documented rule is "UNBENCH on any new credit". The mechanism
        # was sound and its input was cut off: demoted -> never surfaces -> never credited ->
        # never redeemed. at_action's own docstring names this self-sealing loop.
        #
        # This is the exploration/exploitation shape: an arm that is never pulled can never
        # have its value re-estimated, so a wrongly-benched lesson is lost permanently.
        # The fix is a PROBE -- a benched lesson gets an occasional chance to prove itself.
        #
        # The probe is DETERMINISTIC (age-based), never random. `_project_items` feeds a TTL
        # disk cache, so a random probe would make the cache non-reproducible and two seats
        # reading the same corpus would disagree. Age is stable, cheap, and says the right
        # thing: a lesson benched long ago has earned one more look, and one benched moments
        # ago has not.
        probe = False
        if is_benched(rec):
            probe = _rec_name(rec) in _probe_set
            if not probe:
                continue
        # Track WHICH field the surfaced text came from: `recommendation` is forward-looking advice
        # (a claim), `actual` is an observed outcome (evidence), `what_tried` is the action. The
        # reader must be able to tell a claim from evidence, so carry the field through (-> _provenance_tag).
        summary, field = "", ""
        for f in ("recommendation", "actual", "what_tried"):
            if rec.get(f):
                summary, field = rec[f], f
                break
        if not summary:
            continue
        success = str(rec.get("success", "")).lower()
        items.append({
            "text": summary,
            "trigger": _parse_trigger(rec.get("recommendation") or ""),
            "source": f"learn:experiment:{rec.get('experiment_name')}",
            "importance": 4 if success in ("yes", "true") else 3,
            "timestamp": rec.get("timestamp"), "kind": "lesson",
            # Provenance carried to the surface so a self-authored, unverified hypothesis can never
            # return wearing the costume of an external verified fact (Factor 1: opinion-laundering).
            # The store already holds all of this; the old projection discarded it at this seam.
            "success": success,
            "agent_id": rec.get("agent_id", ""),
            "confidence": rec.get("confidence", ""),
            "anti_pattern": rec.get("anti_pattern", ""),
            # Carried for the same reason the provenance fields above are: the store holds it and
            # the projection was dropping it, so nothing downstream could scope on it. A lesson
            # written before domains existed has no field and means DEFAULT_DOMAIN by construction.
            "domain": rec.get("domain", ""),
            "field": field,
            # Carried so the renderer can say so. A probed lesson was benched for failing to
            # earn credit and is being re-tested -- presenting it as an ordinary lesson would
            # overclaim its standing, which is the failure genus this whole arc is about.
            "bench_probe": probe,
        })
    return items


def _cached_items(learning_store: Optional[Any]) -> List[Dict[str, Any]]:
    """Projected lesson items via a TTL disk cache with stale-fallback. An INJECTED store (tests)
    bypasses the cache for determinism; only the production singleton path is cached."""
    if learning_store is not None:
        return _project_items(learning_store.load_all_learnings_from_store())
    try:
        if (time.time() - os.stat(_CACHE_FILE).st_mtime) < _CACHE_TTL:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)          # fresh cache hit (~1ms, no store round-trip)
    except Exception:
        pass
    try:
        from core.learning.learning_store import get_learning_store
        items = _with_usefulness(_with_mined_triggers(
            _project_items(get_learning_store().load_all_learnings_from_store())))
        if items:
            try:
                os.makedirs(_CACHE_DIR, exist_ok=True)
                with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(items, f)
            except Exception:
                pass
        return items
    except Exception:
        try:                                  # store cold/down -> last-known-good (kills cold empties)
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []


# Per-session anti-repeat files live here (the hook writes them; this module prunes them). Keep this
# path in sync with claude_pretooluse.py:_SEEN_DIR.
_SEEN_DIR = os.path.join(_CACHE_DIR, "seen")
# Hook-owned per-session state this module only PRUNES: transcript-failure watermarks (see
# claude_posttooluse.py:_TXW_DIR), captured payload samples (claude_posttooluse.py:_CAP_DIR), and
# the learn-nudge rate-limit state (claude_posttooluse.py:_NUDGE_DIR).
_TXW_DIR = os.path.join(_CACHE_DIR, "txw")
_PAYLOAD_DIR = os.path.join(_CACHE_DIR, "payloads")
_NUDGE_DIR = os.path.join(_CACHE_DIR, "nudge")
# Owned by THIS module: the per-session FAIL->SUCCESS flip log (written by resolve_action_outcome,
# read by the JIT learn nudge and the wrap-time candidate-lesson drafts).
_FLIP_DIR = os.path.join(_CACHE_DIR, "flips")
# The INJECTION LEDGER: every piece of context recall PUSHES at an agent, logged per session
# (altitude action|plan, target, sources, chars). Injected context must be inspectable --
# "harnesses inject context behind your back" is the canonical objection (field-survey C4) --
# and its token cost measurable (the Ronacher dissent: dynamic injection has real cache/token
# cost, so put it in the funnel). Written by the hooks via log_injection, read by the
# `injections` verb + stats.
_INJ_DIR = os.path.join(_CACHE_DIR, "inj")


def warm_cache(learning_store: Optional[Any] = None) -> int:
    """Force-refresh the lesson-item disk cache from the store (ignores TTL). Best-effort; returns the
    item count (0 on failure). Call at session start (SessionStart hook / boot) so the FIRST recall is
    already warm -- the last cold-start corner."""
    try:
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        items = _with_usefulness(_project_items(learning_store.load_all_learnings_from_store()))
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(items, f)
        return len(items)
    except Exception:
        return 0


def prune_state(max_age_days: float = 7.0) -> int:
    """Best-effort sweep of stale per-session state files (anti-repeat seen-sets, open impressions, and
    last-outcomes). Returns the count removed. The cache itself is a single self-refreshing file."""
    removed = 0
    cutoff = time.time() - max_age_days * 86400.0
    for d in (_SEEN_DIR, _IMP_DIR, _OUTCOME_DIR, _TXW_DIR, _PAYLOAD_DIR, _NUDGE_DIR, _FLIP_DIR,
              _INJ_DIR):
        try:
            for name in os.listdir(d):
                p = os.path.join(d, name)
                try:
                    if os.path.isfile(p) and os.stat(p).st_mtime < cutoff:
                        os.remove(p)
                        removed += 1
                except Exception:
                    pass
        except Exception:
            pass
    return removed


# --- usefulness feedback loop: recall learns what's LOAD-BEARING. Each lesson accrues counters in the
# Store (recall:use:<source>): `surfaced` (auto, each time it's shown) + explicit `useful`/`noise` votes
# (via `agent_cli.py recall-feedback`). A smoothed factor then boosts proven-useful lessons and decays
# ones surfaced often yet never useful -- self-improving relevance, deterministic, no LLM. Counters are
# baked into the warm cache at build time, so the hot path stays a pure file read.
_USE_PREFIX = "recall:use:"


def _store():
    from core.foundation.store import create_store
    return create_store()


def _load_use(store, source: str) -> Dict[str, int]:
    try:
        raw = store.get(_USE_PREFIX + str(source))
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


# ---- D5: cross-domain promotion, earned rather than declared ------------------------------------
# A lesson credited useful in >= 2 DOMAINS is domain-general and surfaces everywhere. This is not
# new machinery: it is the funnel that already counts surfaced/useful/noise, read across a boundary.
#
# Promotion has to be EARNED because the first case is the one that motivated it. "An instrument
# that cannot see its subject returns a confident answer, not silence" was found three times in one
# day -- in a PNG decoder, in a metric suite, and in recall itself. Hand-labelling that lesson
# general would ship the mechanism untested on the single example it exists for.
_GENERAL_AT = 2


def credit_useful(source: str, domain: str, store: Optional[Any] = None) -> Dict[str, Any]:
    """Record a useful vote AND the domain it was useful in. Additive: the ordinary `useful` counter
    keeps counting, because the funnel's value gauge reads the same record and a promotion that
    reset it would corrupt the measurement it depends on."""
    st = store if store is not None else _store()
    use = _load_use(st, source)
    use["useful"] = int(use.get("useful", 0) or 0) + 1
    doms = list(use.get("useful_domains") or [])
    d = str(domain or "").strip()
    if d and d not in doms:
        doms.append(d)
    use["useful_domains"] = doms
    try:
        st.set(_USE_PREFIX + str(source), json.dumps(use))
    except Exception:
        pass
    return use


def is_general(source: str, store: Optional[Any] = None,
               use: Optional[Dict[str, Any]] = None) -> bool:
    """True once a lesson has earned credit in >= 2 distinct domains. Twice in one domain is a
    popular lesson; that is not the same claim and must not be promoted to one."""
    rec = use if use is not None else _load_use(store if store is not None else _store(), source)
    return len(set(rec.get("useful_domains") or [])) >= _GENERAL_AT


def _with_usefulness(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach each lesson's usefulness counters (read once at cache-build time -> off the hot path)."""
    try:
        store = _store()
        for it in items:
            it["_use"] = _load_use(store, it.get("source"))
    except Exception:
        pass
    return items


def _with_mined_triggers(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Self-tuning matcher (vNext loop 2): append each lesson's historically-CREDITED flip targets
    to its trigger vocabulary. The durable `flip` events carry (target, credited sources), so every
    FAIL->SUCCESS a lesson helped with teaches the matcher where that lesson actually fires --
    outcome history narrows the trigger, deterministically. Cache-build time only (off the hot
    path); fail-soft to items unchanged."""
    try:
        from core.events.event_log import get_event_log
        mined: Dict[str, set] = {}
        for ev in get_event_log().recent(limit=2000):
            if ev.get("kind") != "flip":
                continue
            detail = ev.get("detail") or {}
            srcs = detail.get("sources") or []
            if not srcs or not int(detail.get("credited", 0) or 0):
                continue   # only CREDITED flips teach (an uncredited flip names a corpus gap instead)
            terms = {t.lower() for t in _TOKEN_RE.findall(str(detail.get("target") or ""))
                     if len(t) > 3 and t.lower() not in _STOP}
            for s in srcs:
                mined.setdefault(str(s), set()).update(terms)
        for it in items:
            extra = mined.get(str(it.get("source")))
            if extra:
                it["trigger_terms"] = sorted(extra)
    except Exception:
        pass
    return items


def _item_tokens(it: Dict[str, Any]) -> set:
    blob = " ".join(filter(None, [str(it.get("text") or ""), str(it.get("trigger") or ""),
                                  " ".join(it.get("trigger_terms") or [])]))
    return {w.lower() for w in _TOKEN_RE.findall(blob) if len(w) > 3}


def _idf_weights(items: List[Dict[str, Any]]) -> Dict[str, float]:
    """Per-term discriminative weight, computed FROM THE CORPUS (document frequency -> normalized
    IDF in [0,1]). Corpus-common tokens ('system', 'working' -- present in half the lessons) weigh
    ~0; rare tokens weigh ~1. This is the data-driven answer to generic-prompt noise: no hand-tuned
    stoplist, and the weights move with the corpus. Deterministic; ~60 small token-set ops."""
    import math
    n = len(items)
    if n < 2:
        return {}
    df: Dict[str, int] = {}
    for it in items:
        for t in _item_tokens(it):
            df[t] = df.get(t, 0) + 1
    # Add-one smoothing: df==n must not weigh EXACTLY 0 (a 2-item corpus would zero out any shared
    # term and silence legitimate queries); at n=60 an everywhere-term still weighs ~0.004.
    log_n1 = math.log(n + 1)
    return {t: (math.log((n + 1) / d) / log_n1) for t, d in df.items()}


def _damped_overlap(text: str, query: str, weights: Optional[Dict[str, float]] = None) -> float:
    """Weighted keyword overlap with two noise defenses (same 0..1 contract as keyword_relevance):
    (1) IDF weighting -- hits and query mass are weighted by corpus rarity, so matching only
    corpus-common tokens scores ~0, and a query with NO discriminative tokens returns 0 outright
    (the show-nothing principle, made information-theoretic); (2) a MIN-HITS dampener -- a
    3+-token query matching exactly ONE term is halved (single incidental tokens are how June's
    dead arc fired on 'continue working'). Unknown terms (not in the corpus) weigh 1.0 -- a rare
    query term that DOES hit is maximally informative."""
    qwords = {w for w in _TOKEN_RE.findall(query.lower()) if len(w) > 3}
    if not qwords:
        return 0.0
    twords = {w.lower() for w in _TOKEN_RE.findall(text.lower())}
    w = weights or {}
    q_mass = sum(w.get(t, 1.0) for t in qwords)
    hits = qwords & twords
    # Denominator floored at ONE fully-rare term's mass: a plain ratio is scale-invariant, so a
    # query reduced to a single corpus-common token would score 1.0 on half the corpus (the bug
    # this line fixes). You cannot score high without matching real information mass.
    frac = sum(w.get(t, 1.0) for t in hits) / max(q_mass, 1.0)
    if len(hits) == 1 and w.get(next(iter(hits)), 1.0) < 0.5:
        frac *= 0.5   # a lone CORPUS-COMMON hit is noise; a lone rare hit ('consolidator') is
        # exactly the designed path->lesson match and must NOT be damped (found by the
        # characterization suite when a token-count heuristic bit the legit case)
    return frac


def _trigger_aware_relevance(by_text: Dict[str, Dict[str, Any]]):
    """Relevance fn for the shared Ranker (its `relevance_fn` seam -- same 0..1 contract as
    keyword_relevance). When a lesson carries a trigger (its own 'Use when' clause + any mined
    credited-target terms), the DESIGNED trigger dominates: 0.6 x trigger overlap + 0.4 x prose
    overlap. Without a trigger, plain overlap. Both components ride the IDF weighting + min-hits
    dampener above. `by_text` closes over the ranked items because the Ranker hands its
    relevance_fn only (text, query)."""
    weights = _idf_weights(list(by_text.values()))

    def fn(text: str, query: str) -> float:
        it = by_text.get(text)
        prose = _damped_overlap(text, query, weights)
        if not it:
            return prose
        trig = " ".join(filter(None, [it.get("trigger") or "",
                                      " ".join(it.get("trigger_terms") or [])]))
        if not trig.strip():
            return prose
        return 0.6 * _damped_overlap(trig, query, weights) + 0.4 * prose
    return fn


def usefulness_factor(use: Optional[Dict[str, int]]) -> float:
    """Smoothed ranking multiplier in [0.5, 1.5]. Neutral (1.0) for unseen; ->1.5 for proven-useful;
    ->0.5 for noise-voted or surfaced-often-yet-never-useful (the automatic noise decay)."""
    use = use or {}
    useful = int(use.get("useful", 0))
    noise = int(use.get("noise", 0))
    helped = int(use.get("helped", 0))            # automatic contrastive positive (FAIL->SUCCESS flip)
    surfaced = int(use.get("surfaced", 0))
    eff = useful - noise + min(helped, surfaced)  # cap helped at impressions (defends join drift)
    denom = max(surfaced, useful + noise + helped) + 2.0   # rate, not raw count -> anti-runaway
    rate = max(0.0, min(1.0, (eff + 1.0) / denom))   # ~0.5 neutral; ->1 proven; ->0 stale/noise
    return 0.5 + rate


def canonicalize_source(source: str, *, learning_store: Optional[Any] = None) -> str:
    """One counter key per lesson (sharpening S2a). A bare slug that names a known lesson
    becomes its full pointer (learn:experiment:<slug>); anything namespaced (contains ':')
    or unknown passes through unchanged -- note ids and other source types are not lessons.
    Without this, a vote cast as 'session_hooks_need_matcher' opens a parallel counter
    that never joins the lesson's surfaced counts (found by the first triage run)."""
    s = str(source or "").strip()
    if not s or ":" in s:
        return s
    try:
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        names = {r.get("experiment_name") for r in learning_store.load_all_learnings_from_store()}
        if s in names:
            return f"learn:experiment:{s}"
    except Exception:
        pass
    return s


def merge_use_counters(*, store=None, learning_store: Optional[Any] = None) -> int:
    """One-time S2a migration: fold bare-slug counters into their canonical keys (counters
    are mutable Store STATE, not Ledger history -- correcting state is legitimate). Returns
    the number of keys merged. Safe to re-run: no bare keys, no work."""
    merged = 0
    try:
        store = store or _store()
        for k in list(store.keys(_USE_PREFIX + "*")):
            src = k[len(_USE_PREFIX):]
            canon = canonicalize_source(src, learning_store=learning_store)
            if canon == src:
                continue
            bare = _load_use(store, src)
            full = _load_use(store, canon)
            for f in ("surfaced", "useful", "noise", "helped"):
                if int(bare.get(f, 0)):
                    full[f] = int(full.get(f, 0)) + int(bare.get(f, 0))
            store.set(_USE_PREFIX + canon, json.dumps(full))
            store.delete(k)
            merged += 1
    except Exception:
        pass
    return merged


def prune_ghost_counters(*, store=None, learning_store: Optional[Any] = None) -> Dict[str, Any]:
    """Fold counter debt left by retired lessons (sharpening S2a, second key form): a GHOST is a
    learn:experiment:* counter whose lesson no longer exists in the corpus. Zero-credit ghosts
    (impressions only) are bookkeeping rows pointing at nothing -- deleted (counters are mutable
    Store STATE, not Ledger history). A ghost WITH credit (useful/helped/noise) is earned history
    outliving its lesson -- that is an adjudication case for S2 supersession (fold the credit into
    the superseding lesson), so it is KEPT and reported, never auto-dropped. Recurs by design:
    every consolidation pass that retires lessons mints new ghosts. Safe to re-run."""
    pruned: List[str] = []
    kept: List[str] = []
    lesson_prefix = "learn:experiment:"
    try:
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        names = {r.get("experiment_name") for r in learning_store.load_all_learnings_from_store()}
        if not names:            # empty/broken corpus read must not classify everything as ghost
            return {"pruned": pruned, "kept_credited": kept}
        store = store or _store()
        for k in list(store.keys(_USE_PREFIX + lesson_prefix + "*")):
            src = k[len(_USE_PREFIX):]
            if src[len(lesson_prefix):] in names:
                continue
            use = _load_use(store, src)
            if any(int(use.get(f, 0)) for f in ("useful", "noise", "helped")):
                kept.append(src)
                continue
            store.delete(k)
            pruned.append(src)
    except Exception:
        pass
    return {"pruned": pruned, "kept_credited": kept}


def record_feedback(source: str, kind: str = "useful", *, store=None,
                    domain: Optional[str] = None) -> bool:
    """Record a usefulness signal for a recalled lesson. kind: 'useful'/'noise' (explicit votes),
    'helped' (the automatic contrastive positive -- a FAIL->SUCCESS flip), or 'engaged' (the agent
    pulled the FULL record -- strong interest, weaker than helped; counted + shown in triage and
    protective against benching, but deliberately NOT a ranking boost until it earns one).
    Best-effort, repeatable. Sources are canonicalized (S2a) so votes land on one counter."""
    if not source or kind not in ("useful", "noise", "helped", "engaged"):
        return False
    try:
        source = canonicalize_source(source)
        store = store or _store()
        if kind == "useful":
            # ONE write path for useful, so `useful` and `useful_domains` can never disagree about
            # the same vote -- which is what would let a lesson be promoted by credit it never got.
            credit_useful(source, domain, store=store)
            return True
        use = _load_use(store, source)
        use[kind] = int(use.get(kind, 0)) + 1
        store.set(_USE_PREFIX + str(source), json.dumps(use))
        return True
    except Exception:
        return False


def full_record(source: str, *, learning_store: Optional[Any] = None) -> Dict[str, Any]:
    """The one-hop pull from a recalled lesson's lossy summary to its WHOLE record (what_tried,
    expected, actual, root_cause, metrics, ...) -- the escape hatch `render()` points to when more
    exists than the capped surface shows. `source` is the pointer already carried on every recalled
    item, e.g. `learn:experiment:NAME`. Fail-soft: {} on any error, bad pointer, or unknown source
    (a failed pull must never brick the caller, same discipline as recall_at)."""
    prefix = "learn:experiment:"
    try:
        if not source or not str(source).startswith(prefix):
            return {}
        exp_id = str(source)[len(prefix):]
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        rec = learning_store._load_experiment(exp_id) or {}
        if rec:
            # The one-hop full pull is a strong implicit interest signal (vNext loop 3): count it.
            # Both doors (CLI `recall --full`, MCP twin) route through here, so neither is blind.
            record_feedback(source, "engaged")
        return rec
    except Exception:
        return {}


def bump_surfaced(sources, *, store=None) -> None:
    """Increment the `surfaced` (impression) counter for shown lessons -- best-effort, fire-and-forget."""
    try:
        store = store or _store()
        for s in sources:
            use = _load_use(store, s)
            use["surfaced"] = int(use.get("surfaced", 0)) + 1
            store.set(_USE_PREFIX + str(s), json.dumps(use))
    except Exception:
        pass


# --- implicit-useful: the contrastive FAIL->SUCCESS flip (automatic positive, no agent vote needed).
# At surface time PreToolUse records an "open impression" {target -> sources}; a PostToolUse hook calls
# resolve_outcome() when the action completes. If a target that JUST FAILED now SUCCEEDS, the lessons
# surfaced for it are credited 'helped' (consume-on-credit). Contrastive by construction: a first-try
# success credits nothing. All best-effort + fail-soft (a PostToolUse hook must never affect the action).
_IMP_DIR = os.path.join(_CACHE_DIR, "imp")
_OUTCOME_DIR = os.path.join(_CACHE_DIR, "outcome")
# Stage-separation ledger (2026-07-25 debate): EVERY resolved outcome, flipped or not.
# The flip log answers "was a failure rescued"; this answers "what happened, and had a
# lesson surfaced" -- which is the only way to see PREVENTION.
_STAGE_DIR = os.path.join(_CACHE_DIR, "stage")


def _safe_id(session_id: str) -> str:
    return "".join(c for c in str(session_id) if c.isalnum() or c in "-_")[:128] or "nosession"


def normalize_target(path: Optional[str] = None, command: Optional[str] = None) -> str:
    """Stable key for a point of action -- MUST be identical at surface (PreToolUse) and resolve
    (PostToolUse) time or the join silently evaporates. Paths -> normcased absolute; commands ->
    lowercased + whitespace-collapsed."""
    if path:
        try:
            return "p:" + os.path.normcase(os.path.abspath(path))
        except Exception:
            return "p:" + str(path)
    if command:
        return "c:" + " ".join(str(command).lower().split())
    return ""


def mark_impression(session_id: str, target: str, sources) -> None:
    """Record that `sources` were surfaced for `target` this session (the outcome-join key)."""
    srcs = [s for s in (sources or []) if s]
    if not session_id or not target or not srcs:
        return
    try:
        os.makedirs(_IMP_DIR, exist_ok=True)
        with open(os.path.join(_IMP_DIR, _safe_id(session_id) + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": target, "s": srcs}) + "\n")
    except Exception:
        pass


def _impressions_for(session_id: str, target: str) -> list:
    out = []
    try:
        with open(os.path.join(_IMP_DIR, _safe_id(session_id) + ".jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if rec.get("t") == target:
                        out += rec.get("s", [])
                except Exception:
                    pass
    except Exception:
        pass
    return list(dict.fromkeys(out))   # dedup, order-stable


def _clear_impressions(session_id: str, target: str) -> None:
    try:
        p = os.path.join(_IMP_DIR, _safe_id(session_id) + ".jsonl")
        kept = []
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    if json.loads(line).get("t") != target:
                        kept.append(line)
                except Exception:
                    pass
        with open(p, "w", encoding="utf-8") as f:
            f.writelines(kept)
    except Exception:
        pass


def _outcome_file(session_id: str) -> str:
    return os.path.join(_OUTCOME_DIR, _safe_id(session_id) + ".json")


def _get_outcome(session_id: str, target: str):
    try:
        with open(_outcome_file(session_id), encoding="utf-8") as f:
            return json.load(f).get(target)
    except Exception:
        return None


def _set_outcome(session_id: str, target: str, status: str) -> None:
    try:
        os.makedirs(_OUTCOME_DIR, exist_ok=True)
        p = _outcome_file(session_id)
        d = {}
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {}
        d[target] = status
        with open(p, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass


def resolve_action_outcome(session_id: str, target: str, success: bool, *, store=None,
                           agent_id: Optional[str] = None) -> Dict[str, Any]:
    """PostToolUse resolver, full report. If `target` SUCCEEDS now after having JUST FAILED:
    (1) credit the lessons surfaced for it with 'helped' (consume-on-credit, so one flip can't be
    farmed), and (2) append the flip to the per-session FLIP LOG -- a flip is the moment a lesson
    was just earned, so it is the raw material for the JIT learn nudge and the wrap-time candidate
    lessons (friction audit D5). Returns {"flipped", "credited", "sources"}; best-effort + fail-soft
    -- a first-try success credits and logs nothing (the contrastive gate)."""
    out: Dict[str, Any] = {"flipped": False, "credited": 0, "sources": []}
    if not session_id or not target:
        return out
    try:
        # Read impressions ONCE, before any clear -- the outcome stage needs to know a
        # lesson was surfaced even when nothing flipped (that is the prevention case).
        srcs_now = _impressions_for(session_id, target)
        if success and _get_outcome(session_id, target) == "FAIL":
            out["flipped"] = True
            out["sources"] = srcs_now
            for src in out["sources"]:
                if record_feedback(src, "helped", store=store):
                    out["credited"] += 1
            _clear_impressions(session_id, target)
            _log_flip(session_id, target, out["credited"], out["sources"])
        # Stage separation: record EVERY resolution, flipped or not. Purely additive --
        # the flip path above is byte-for-byte unchanged, and nothing here steers ranking.
        _log_outcome_stage(session_id, target, success, surfaced_sources=srcs_now,
                           flipped=out["flipped"], credited=out["credited"],
                           agent_id=agent_id)
        _set_outcome(session_id, target, "SUCCESS" if success else "FAIL")
    except Exception:
        pass
    return out


def resolve_outcome(session_id: str, target: str, success: bool, *, store=None) -> int:
    """Compat shim: the original int contract (number credited). See resolve_action_outcome."""
    return resolve_action_outcome(session_id, target, success, store=store)["credited"]


def _log_flip(session_id: str, target: str, credited: int, sources) -> None:
    try:
        os.makedirs(_FLIP_DIR, exist_ok=True)
        rec = {"t": target, "credited": credited, "s": list(sources or []), "at": time.time()}
        with open(os.path.join(_FLIP_DIR, _safe_id(session_id) + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def _log_outcome_stage(session_id: str, target: str, success: bool, *,
                       surfaced_sources, flipped: bool, credited: int,
                       agent_id: Optional[str] = None) -> None:
    """Record the OUTCOME stage for EVERY resolution -- not only for flips.

    STAGE SEPARATION (the 2026-07-25 four-seat debate's unanimous result). "surfaced",
    "applied", "outcome" and "attributed" must be DISTINCT events, because an aggregate
    cannot name which funnel stage is failing. codex decomposed it: C/N = (R/N)(S/R)(A/S)
    (F/A)(C/F) -- four credited flips proves the PRODUCT is tiny and cannot say WHICH
    factor is. Before this function, outcome and attribution were FUSED into the flip
    record, and the record was written ONLY when a flip occurred.

    That is the expensive blindness. kimi, verified in this file: the credited-flip
    numerator counts RESCUE, never PREVENTION -- "a first-try success credits and logs
    nothing" was the contrastive gate, by design -- so the single most valuable thing a
    lesson can do (stop the failure from happening at all) was invisible to the only value
    metric the system had. Daniel's bar is that agents PREFER the store, and you prefer
    what stops you failing, not what rescues you.

    This event makes the prevention numerator computable for the first time:
        success AND surfaced AND NOT flipped  -> a PREVENTION candidate
        success AND NOT surfaced              -> its CONTROL arm
    The contrastive first-try-success rate falls straight out of that pair.

    OBSERVATION ONLY -- nothing here feeds ranking. The debate showed BOTH feedback loops
    are confounded (the positive by self-inflation; the negative by exposure-bias, and
    is_benched makes it self-sealing: a demoted lesson stops surfacing, so it can never
    earn the credit that would redeem it). No automatic steer may ride this signal until
    the stages are separately observed. Carries agent_id so cross-seat questions become
    answerable. Fail-soft by contract: a PostToolUse hook must never affect the action.
    """
    # Build the record ONCE, outside both writers: the tempdir write and the durable
    # mirror must carry identical shapes, and neither may depend on the other having run.
    srcs = [s for s in (surfaced_sources or []) if s]
    rec = {"at": time.time(), "t": str(target or ""), "ok": bool(success),
           "surfaced": bool(srcs), "s": srcs,
           "flipped": bool(flipped), "credited": int(credited or 0),
           # t383 identity thread: the explicit param beats env — a harness seat that
           # INHERITS a foreign AKASHIC_AGENT_ID (the DSH-under-Claude-Code case) must
           # not stamp its outcome rows with the parent's identity.
           "agent": str(agent_id or os.getenv("AKASHIC_AGENT_ID") or "")}
    try:
        os.makedirs(_STAGE_DIR, exist_ok=True)
        with open(os.path.join(_STAGE_DIR, _safe_id(session_id) + ".jsonl"),
                  "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass
    # Durable mirror -- a prevention RATE is a trend, and the tempdir is per-boot only.
    # ISOLATION GUARD, and it is not theoretical: the first version of this mirror wrote
    # test fixtures straight into the canonical stream. 36 of the first 51 records were
    # my own pins. tests/conftest.py redirects AKASHIC_RECALL_STATE_DIR (the tempdir side)
    # but NOTHING redirects the event log, so the two writers had different isolation and
    # only one of them was honest about it. That is the same genus as the pytest suite
    # replacing the live learning index (lesson: pytest_destroys_the_live_learning_index)
    # and W66 -- committed here by the seat that filed both, hours later.
    # RULE: if the state root is redirected, this is not production. One isolation signal,
    # both writers, no divergence.
    if os.environ.get("AKASHIC_RECALL_STATE_DIR") or os.environ.get("_AISETUP_TEST_ISOLATED"):
        return
    try:
        from core.events.event_log import get_event_log
        get_event_log().ledger.emit(OUTCOME_STREAM,
                                    dict(rec, sid=_safe_id(session_id)),
                                    maxlen=OUTCOME_MAXLEN)
    except Exception:
        pass


def session_outcomes(session_id: str) -> List[Dict[str, Any]]:
    """Every resolved outcome this session (oldest first), flipped or not. Fail-soft."""
    out: List[Dict[str, Any]] = []
    try:
        with open(os.path.join(_STAGE_DIR, _safe_id(session_id) + ".jsonl"),
                  encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def prevention_rate(session_id: str) -> Dict[str, Any]:
    """The CONTRASTIVE first-try-success rate -- the metric the rescue-only funnel cannot see.

    Compares first-try success WHERE A LESSON SURFACED against first-try success where none
    did. `lift` is the difference; a positive lift is the first evidence the store PREVENTS
    failure rather than merely rescuing it.

    HONEST BOUND, and it must travel with the number: this is a CONTRAST, not a
    counterfactual. The two arms are not randomised -- lessons surface where they match, so
    the surfaced arm is a biased sample of targets. It cannot prove causation; it can only
    show whether the association exists at all, which is strictly more than the rescue
    metric could show. A real counterfactual needs the control arm run in the sandbox.
    Also unmeasured here: the APPLIED stage. Whether a seat changed course BECAUSE of a
    lesson leaves no trace unless the seat declares it (kimi), so `lift` bounds the
    prevention effect from above and attributes nothing.
    """
    return _contrast(session_outcomes(session_id))


def _contrast(recs) -> Dict[str, Any]:
    """The contrast math, shared by the session and durable readers so they cannot drift.

    Counts the FIRST resolution per (session, target). First-try is the whole point: a
    target that fails and is later rescued is a RESCUE, not a prevention, and counting the
    eventual success would inflate the rate with exactly the cases the old metric already
    saw."""
    seen = set()
    with_l = {"n": 0, "ok": 0}
    without = {"n": 0, "ok": 0}
    for r in recs or []:
        t = str(r.get("t") or "")
        if not t:
            continue
        key = (str(r.get("sid") or ""), t)
        if key in seen:
            continue
        seen.add(key)
        bucket = with_l if r.get("surfaced") else without
        bucket["n"] += 1
        if r.get("ok"):
            bucket["ok"] += 1
    rate_w = (with_l["ok"] / with_l["n"]) if with_l["n"] else None
    rate_o = (without["ok"] / without["n"]) if without["n"] else None
    return {"with_lesson": with_l, "without_lesson": without,
            "rate_with": rate_w, "rate_without": rate_o,
            "lift": (round(rate_w - rate_o, 4)
                     if (rate_w is not None and rate_o is not None) else None)}


def durable_outcomes(days: float = 30.0) -> List[Dict[str, Any]]:
    """The durable OUTCOME stream over a window, oldest-first. [] when the store is down."""
    out: List[Dict[str, Any]] = []
    cutoff = time.time() - (float(days) * 86400.0)
    try:
        from core.events.event_log import get_event_log
        ledger = get_event_log().ledger
        after = "0"
        while True:
            batch = ledger.consume(OUTCOME_STREAM, after_id=after, count=500)
            if not batch:
                break
            for eid, ev in batch:
                if isinstance(ev, dict) and float(ev.get("at") or 0) >= cutoff:
                    out.append(ev)
                after = str(eid)
            if len(batch) < 500:
                break
    except Exception:
        return out
    return out


def prevention_rate_durable(days: float = 30.0) -> Dict[str, Any]:
    """The FLEET-WIDE prevention contrast over a window -- the trend version.

    prevention_rate() answers "this session"; a prevention rate only means something as a
    TREND, so this is the one that will eventually answer whether the store prevents
    failure. Same honest bounds as prevention_rate: a contrast, not a counterfactual, with
    the APPLIED stage still unobserved. Carries the same warning -- it bounds the effect
    from above and attributes nothing."""
    return _contrast(durable_outcomes(days))


def session_flips(session_id: str) -> List[Dict[str, Any]]:
    """FAIL->SUCCESS flips recorded for one session (oldest first). Fail-soft: [] on any error."""
    out: List[Dict[str, Any]] = []
    try:
        with open(os.path.join(_FLIP_DIR, _safe_id(session_id) + ".jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def log_injection(session_id: str, altitude: str, target: str, sources, chars: int) -> None:
    """Append one entry to the injection ledger (see _INJ_DIR note). Best-effort, fail-soft --
    the ledger observes the push, it must never block it."""
    srcs = [s for s in (sources or []) if s]
    if not session_id or not srcs:
        return
    try:
        os.makedirs(_INJ_DIR, exist_ok=True)
        with open(os.path.join(_INJ_DIR, _safe_id(session_id) + ".jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"at": time.time(), "alt": str(altitude or "action"),
                                "t": str(target or ""), "s": srcs, "chars": int(chars or 0)}) + "\n")
    except Exception:
        pass
    try:   # F0b durable mirror (same capture chokepoint -- renew_signal_label_symmetry);
        # rides the event-log singleton's Ledger, own stream, fail-soft, ~1 write.
        from core.events.event_log import get_event_log
        get_event_log().ledger.emit(SURFACE_STREAM, {
            "at": time.time(), "sid": _safe_id(session_id), "alt": str(altitude or "action"),
            "t": str(target or ""), "s": srcs, "chars": int(chars or 0)}, maxlen=SURFACE_MAXLEN)
    except Exception:
        pass


def session_recall_summary(session_id: str) -> Dict[str, int]:
    """This session's recall economy in four ints (vNext loop 3): injections pushed, distinct
    lessons, chars of context spent, and flips that credited a lesson. Read from the session's own
    injection + flip files; zeros when absent. Feeds the durable `session_signals` event so recall
    efficacy lands in the SAME dataset the Renew correlation reads -- one dataset, two pillars."""
    out = {"injections": 0, "distinct_sources": 0, "chars": 0, "helped_flips": 0}
    try:
        srcs = set()
        with open(os.path.join(_INJ_DIR, _safe_id(session_id) + ".jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                out["injections"] += 1
                out["chars"] += int(rec.get("chars", 0) or 0)
                srcs.update(rec.get("s", []))
        out["distinct_sources"] = len(srcs)
    except Exception:
        pass
    try:
        with open(os.path.join(_FLIP_DIR, _safe_id(session_id) + ".jsonl"), encoding="utf-8") as f:
            for line in f:
                try:
                    if int((json.loads(line) or {}).get("credited", 0) or 0) > 0:
                        out["helped_flips"] += 1
                except Exception:
                    pass
    except Exception:
        pass
    return out


def recent_injections(hours: float = 24.0) -> List[Dict[str, Any]]:
    """Injections across ALL sessions in the last `hours`, oldest first (same shape of reader
    as recent_flips; tempdir-lifetime -- a cost/observability view, not a durable record)."""
    cutoff = time.time() - hours * 3600.0
    out: List[Dict[str, Any]] = []
    try:
        for name in os.listdir(_INJ_DIR):
            p = os.path.join(_INJ_DIR, name)
            try:
                if not (os.path.isfile(p) and os.stat(p).st_mtime >= cutoff):
                    continue
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        try:
                            rec = json.loads(line)
                            if float(rec.get("at", 0)) >= cutoff:
                                out.append(rec)
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass
    out.sort(key=lambda r: r.get("at", 0))
    return out


def injections_by_family(hours: float = 24.0, injections=None) -> Dict[str, Any]:
    """W54 (kimi F3, the activation gauge): group the injection ledger by lesson FAMILY -- the
    experiment name's first token (conductor_brief_intent_law -> 'conductor') -- so a claim about
    an organ's firing rate reads the instrument instead of an anecdote. Numerator = injections
    that carried >=1 lesson of the family; denominator = ALL injections in the window. 'conductor'
    is always present (0/N included): the stance family is the reason this gauge exists. Pass
    `injections` to stay pure (no IO) -- the wrap draft does; omit it to read the live ledger."""
    inj = recent_injections(hours) if injections is None else list(injections)
    fams: Dict[str, int] = {}
    for rec in inj:
        seen = set()
        for s in rec.get("s", []) or []:
            name = str(s).replace("learn:experiment:", "").strip()
            fam = name.split("_", 1)[0].split("-", 1)[0] if name else ""
            if fam:
                seen.add(fam)
        for f in seen:
            fams[f] = fams.get(f, 0) + 1
    fams.setdefault("conductor", 0)
    return {"window_hours": float(hours), "total": len(inj), "families": fams}


def recent_flips(hours: float = 12.0) -> List[Dict[str, Any]]:
    """Flips across ALL sessions in the last `hours` (oldest first). The wrap draft reads this --
    the CLI has no hook session_id, and 'this working session' is a time window anyway."""
    cutoff = time.time() - hours * 3600.0
    out: List[Dict[str, Any]] = []
    try:
        for name in os.listdir(_FLIP_DIR):
            p = os.path.join(_FLIP_DIR, name)
            try:
                if not (os.path.isfile(p) and os.stat(p).st_mtime >= cutoff):
                    continue
                with open(p, encoding="utf-8") as f:
                    for line in f:
                        try:
                            rec = json.loads(line)
                            if float(rec.get("at", 0)) >= cutoff:
                                out.append(rec)
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass
    out.sort(key=lambda r: r.get("at", 0))
    return out


def _slug_from_target(target: str) -> str:
    """A pre-filled --experiment name candidate from the target's meaningful tokens (defaults do
    the work -- the agent edits a suggestion instead of authoring a name from scratch)."""
    toks = [t.lower() for t in _TOKEN_RE.findall(str(target)) if len(t) > 3 and t.lower() not in _STOP]
    return "fix_" + "_".join(toks[:3]) if toks else "fix_this"


def learn_command_for(target: str, agent_id: Optional[str] = None) -> str:
    """The pre-filled `learn` command skeleton for a flip target -- defaults do the work (friction
    audit fix #3): the agent edits two placeholders instead of authoring a command from scratch."""
    agent = agent_id or os.getenv("AKASHIC_AGENT_ID") or "<agent>"
    # Trigger-phrased recommendation placeholder (field-survey C5): "Use when <symptom>..."
    # descriptions are what make a lesson FIRE at the right moment -- the template models it
    # so the phrasing costs one edit instead of authorship.
    return (f'py agent_cli.py learn {agent} --experiment {_slug_from_target(target)} '
            f'--tried "<what failed>" --result "<what fixed it>" '
            f'--recommend "Use when <symptom>, before <action>: <advice>"')


def build_learn_nudge(target: str, credited: int, sources, agent_id: Optional[str] = None,
                      probe=None) -> str:
    """The JIT 'learn it?' prompt for a FAIL->SUCCESS flip (friction audit D5: a cue at the moment
    of insight converts lesson capture from memory to a signal prompt). Silent-when-irrelevant is
    the CALLER's job (only call on a real flip); this stays small-when-not: three short lines with
    a pre-filled command skeleton, so capture costs one edit, not authorship."""
    short = target if len(target) <= 90 else target[:90] + "..."
    lines = [f"[flip] FAIL->SUCCESS on: {short}"]
    if credited:
        lines.append(f"{credited} stored lesson(s) just earned 'helped' credit here.")
    else:
        # NEVER claim a corpus gap without probing for one. `credited == 0` is true in three
        # disjoint cases -- (a) nothing relevant exists, (b) something relevant exists but did
        # not SURFACE for this target, (c) something surfaced and was not credited -- and only
        # (a) is a gap. The old text asserted (a) unconditionally.
        #
        # 2026-07-25: it told me "this is a corpus gap worth filling" after a Write flip. I
        # filled it. One call later recall surfaced `write_tool_needs_read_tool`, which
        # already said the same thing -- the lesson existed, it just could not rank for a
        # path-keyed target. The instrument degraded the corpus it was measuring.
        candidates = []
        probed = False
        if probe is not None:
            try:
                candidates = [c for c in (probe(target) or [])][:3]
                probed = True
            except Exception:
                probed = False        # a probe fault must never license a gap claim
        if probed and candidates:
            lines.append("No stored lesson was CREDITED here, but the corpus already holds "
                         f"possibly-relevant lesson(s): {', '.join(str(c) for c in candidates)}. "
                         "Check before writing -- a near-match means a duplicate, not a gap.")
        elif probed:
            lines.append("No stored lesson helped here and a corpus probe found no near-match "
                         "-- if the fix generalizes, this is a corpus gap worth filling.")
        else:
            # Unprobed: say what is true (nothing was credited) and nothing about gaps.
            lines.append("No stored lesson was credited here.")
    lines.append("If there's a transferable lesson, record it now (one line): "
                 + learn_command_for(target, agent_id))
    return "\n".join(lines)


def _query_from(path: Optional[str], command: Optional[str],
                subject: Optional[str] = None, gesture: Optional[str] = None) -> str:
    """Build a keyword query from a path (dir/stem tokens), a command, and/or a composition
    GESTURE and SUBJECT. Keeps tokens len>3 (the Ranker's keyword_relevance ignores shorter ones)
    minus generic noise; order-stable, deduped.

    subject/gesture exist because path and command are both SYSTEM-shaped triggers: they assume the
    point of action is a file or a shell line. "About to add tanh-tonemap after superlinear-
    highlight" is neither, so the moment when the chunk-ordering rule is worth knowing was a moment
    recall could not be asked about. Extending this one function rather than adding a second door is
    deliberate -- the hooks already call recall_at and nothing else, so the mediation layer exists.
    """
    parts: List[str] = []
    if path:
        parts += _TOKEN_RE.findall(path.replace("\\", "/"))
    if command:
        parts += _TOKEN_RE.findall(command)[:16]
    # The gesture leads: it names what is ABOUT to happen, which is what the lesson must match. The
    # subject is context and follows.
    if gesture:
        parts = _TOKEN_RE.findall(gesture)[:16] + parts
    if subject:
        parts += _TOKEN_RE.findall(subject)[:8]
    out: List[str] = []
    for t in parts:
        t = t.lower()
        if len(t) > 3 and t not in _STOP and t not in out:
            out.append(t)
    return " ".join(out)


def _domain_from_trigger(path: Optional[str], command: Optional[str],
                         subject: Optional[str], gesture: Optional[str]) -> Optional[str]:
    """Which domain is this point of action in? None when there is nothing to go on.

    Returning None rather than the default matters: an unscoped call must keep searching everything,
    exactly as it did before domains existed. Guessing "system" from an empty trigger would silently
    hide every vfx lesson from callers that simply did not say.
    """
    if gesture or subject:
        return "vfx"          # a composition gesture only exists inside the bench
    blob = " ".join(str(x or "") for x in (path, command))
    if not blob.strip():
        return None
    from core.learning.domains import infer_domain
    return infer_domain({"what_tried": blob, "recommendation": ""})


def _self_echo(item: Dict[str, Any], agent_id: Optional[str], now: Optional[float]) -> bool:
    """True when this lesson was authored by the CALLING agent within the echo window -- its author
    just lived it, so resurfacing it to them is pure noise (it still surfaces to everyone else,
    and to the author again once the window passes). AKASHIC_RECALL_SELF_ECHO_H tunes; 0 disables."""
    if not agent_id or str(item.get("agent_id") or "") != str(agent_id):
        return False
    try:
        hours = float(os.getenv("AKASHIC_RECALL_SELF_ECHO_H", "2"))
        if hours <= 0:
            return False
        # timeutil.to_epoch, NOT fromisoformat().timestamp(): records carry utcnow()-naive stamps,
        # which .timestamp() reads as LOCAL -- fresh lessons then sit "in the future" and the
        # window never matches (caught live by the vNext flight test, 2026-07-08).
        from core.foundation.timeutil import to_epoch
        age_s = (now if now is not None else time.time()) - to_epoch(item.get("timestamp") or "")
        return 0 <= age_s < hours * 3600.0
    except Exception:
        return False


def _lessons(query: str, now: Optional[float], limit: int, min_relevance: float,
             learning_store: Optional[Any] = None,
             exclude_sources: Optional[set] = None,
             agent_id: Optional[str] = None,
             stats_out: Optional[Dict[str, int]] = None,
             domain: Optional[str] = None) -> "tuple[List[Dict[str, Any]], int]":
    """Rank ACTIVE lessons by TRIGGER-AWARE relevance; keep those above the show-nothing floor,
    minus any already surfaced this session (`exclude_sources` -> anti-repeat), the caller's own
    fresh lessons (self-echo window), and intra-call source dups. Returns (items capped at `limit`,
    TOTAL that cleared the floor) -- the total powers the N-of-M escape line in render()."""
    from core.primitives.ranker import Ranker
    items = _cached_items(learning_store)
    if domain:
        # SCOPE, with two deliberate escapes. A lesson written before domains existed carries no
        # field and means DEFAULT_DOMAIN by construction, so it stays visible to system actions
        # rather than vanishing during the backfill gap. And a lesson credited useful in two
        # domains has EARNED its way across the boundary -- that is D5, and this is the one line
        # where cross-domain learning actually pays out.
        from core.learning.domains import DEFAULT_DOMAIN
        items = [it for it in items
                 if (it.get("domain") or DEFAULT_DOMAIN) == domain
                 or is_general(it.get("source"), use=it.get("_use"))]
    excl = exclude_sources or set()
    by_text = {str(it.get("text") or ""): it for it in items}
    cands: List = []
    seen = set()
    ranker = Ranker(relevance_fn=_trigger_aware_relevance(by_text))
    for s in ranker.rank(items, query=query, now=now):   # Ranker excludes superseded (is_active)
        if s.components.get("relevance", 0.0) <= min_relevance:
            continue   # SHOW-NOTHING floor (T_min): must actually match this path/command; never pad to `limit`
        # R2 s0 P8 (sol's fence): count the stages so the outcome row can tell
        # "nothing cleared the floor" apart from "cleared, then withheld". A mixed
        # floor_silent bucket poisons any read of the floor's own behaviour.
        if stats_out is not None:
            stats_out["above_floor"] = stats_out.get("above_floor", 0) + 1
        src = s.item.get("source")
        # T251, corrected by Gemini 3.1 Pro's review: evaluate BOTH rules before deciding, or
        # the first one shadows the second and the instrument names a rule whose loosening
        # would not actually un-silence the call. Intra-call dedup (src in seen) is deliberately
        # NOT a suppression -- the item was already accepted this very call.
        _hit = []
        if src in excl:
            _hit.append(EXCL_ANTIREPEAT)
        if _self_echo(s.item, agent_id, now):
            _hit.append(EXCL_SELF_ECHO)
        if src in seen or _hit:
            _note_exclusion(stats_out, _hit)      # no-op when only intra-call dedup fired
            continue
        seen.add(src)
        # usefulness re-rank: proven-useful lessons rise; surfaced-often-yet-never-useful decay
        cands.append((s.score * usefulness_factor(s.item.get("_use")), s.item))
    cands.sort(key=lambda t: t[0], reverse=True)
    return [it for _, it in cands[:limit]], len(cands)


def _locks(path: Optional[str], agent_id: Optional[str]) -> List[Dict[str, Any]]:
    """A peer holding an advisory lock on this exact path = the single most actionable hint."""
    if not path:
        return []
    try:
        from core.comm.locks import path_conflict
        c = path_conflict(path, agent_id or "(unidentified)")
    except Exception:
        return []
    if c.get("conflict"):
        return [{"held_by": c.get("held_by"), "reason": c.get("reason", "")}]
    return []


# SHOW-NOTHING floor default (vNext loop 2). Calibrated 2026-07-08 by replaying every historically
# CREDITED (lesson,target) pair + the 24h injection ledger through the trigger-aware relevance fn
# (scratchpad recall_floor_calibration.py; result recorded in docs/library/design/20260701_recall-vnext-closing-the-four-loops-2026_b93539.md): the
# chosen default keeps >=95% of historical helps while cutting the never-credited tail. 0 restores
# the old any-overlap behavior. Env-tunable without a deploy.
def _floor_default() -> float:
    try:
        return float(os.getenv("AKASHIC_RECALL_FLOOR", "0.20"))
    except Exception:
        return 0.20


# --- T311 capability-recall: the verb channel -------------------------------------------------
# This surface already pushes lessons and locks at the moment of action. It did not push VERBS,
# and the door has 85 of them. Measured 2026-08-15: a seat met a YouTube URL, reached for a web
# fetch, then grepped the repo for a script, while `captions` sat on the door with tests behind
# it. Daniel: "We forget it every time Q__Q".
#
# `discover` is the near miss, not the answer: it lists every verb, but it is SELF-SERVE -- an
# agent must already suspect the capability exists to ask. This channel is the push side.
#
# The index is parsed from the PARSER (T115 check_advertised_verbs precedent), never from a
# snapshot file, so it cannot drift from the door. It reads add_argument help too, which closes
# the structural blind spot in `discover`: a capability shipped as a FLAG is invisible to a
# verb-table read (lesson discover_reads_verbs_not_flags).

_VERB_CACHE: Dict[str, Any] = {"mtime": None, "index": None, "df": None}


def _agent_cli_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "agent_cli.py")


def verb_index(source_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every door verb, its purpose, and its flags -- read from agent_cli's AST.

    Returns [{verb, purpose, flags:[...]}]. Cached on the source file's mtime because this runs
    before every edit and command; a cold parse of a 7k-line module is not hot-path work.

    Adjacent string literals in a help= are concatenated by the Python parser itself, so a
    multi-line help arrives here as one Constant and needs no reassembly. Flags are attached to
    the most recent preceding add_parser assignment for that variable, which is source order and
    therefore exactly how argparse itself binds them.

    Fail-soft by contract: any parse problem returns [] so the verb channel goes quiet rather
    than taking the whole recall surface down with it."""
    path = source_path or _agent_cli_path()
    try:
        mtime = os.path.getmtime(path)
        if _VERB_CACHE["mtime"] == mtime and _VERB_CACHE["index"] is not None:
            return _VERB_CACHE["index"]
        import ast
        with open(path, "r", encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        parsers: List[Any] = []        # (lineno, var_name, entry)
        args: List[Any] = []           # (lineno, var_name, flag_names, help_text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                fn = node.value.func
                if isinstance(fn, ast.Attribute) and fn.attr == "add_parser" and node.value.args:
                    first = node.value.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        helptext = ""
                        for kw in node.value.keywords:
                            if kw.arg in ("help", "description") and \
                                    isinstance(kw.value, ast.Constant) and \
                                    isinstance(kw.value.value, str):
                                helptext = kw.value.value
                        tgt = node.targets[0]
                        var = tgt.id if isinstance(tgt, ast.Name) else ""
                        parsers.append((node.lineno, var,
                                        {"verb": first.value, "purpose": helptext, "flags": []}))
            elif isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Attribute) and fn.attr == "add_argument" and \
                        isinstance(fn.value, ast.Name) and node.args:
                    names = [a.value for a in node.args
                             if isinstance(a, ast.Constant) and isinstance(a.value, str)]
                    helptext = ""
                    for kw in node.keywords:
                        if kw.arg == "help" and isinstance(kw.value, ast.Constant) and \
                                isinstance(kw.value.value, str):
                            helptext = kw.value.value
                    args.append((node.lineno, fn.value.id, names, helptext))
        parsers.sort(key=lambda t: t[0])
        for lineno, var, names, helptext in sorted(args, key=lambda t: t[0]):
            owner = None
            for p_line, p_var, entry in parsers:
                if p_var == var and p_line < lineno:
                    owner = entry
                elif p_line > lineno:
                    break
            if owner is not None:
                owner["flags"].extend(n.lstrip("-") for n in names)
                if helptext:
                    owner["flags"].append(helptext)
        index = [e for _, _, e in parsers]
        _VERB_CACHE.update({"mtime": mtime, "index": index, "df": None})
        return index
    except Exception:
        return []


def _verb_tokens(entry: Dict[str, Any]) -> set:
    text = " ".join([entry.get("verb", "").replace("-", " "), entry.get("purpose", "")]
                    + [str(f) for f in entry.get("flags", [])])
    return {t.lower() for t in _TOKEN_RE.findall(text)
            if len(t) > 3 and t.lower() not in _STOP}


_EXTERNAL_TOOLS = {"git", "npm", "docker", "pip", "node", "cargo", "yarn", "pytest", "poetry"}
_VERB_NOISE = {"claude", "deepseek", "kimi", "agent", "python"}


def _verb_exclusions(command: Optional[str]) -> set:
    """Tokens that must NOT be allowed to summon a verb, and why each class is here.

    Measured before this existed: 67% false-positive rate over a sample of sixteen real triggers
    from one session (12 of which should have stayed silent; 8 fired). Every class below is one
    of those failures, not a hypothetical.

      PATH TOKENS -- `py tests/test_t311_capability_recall.py` summoned `recall` and `recall-at`
      off the FILENAME. A path says where you are working; a verb answers what you want to do.
      Lessons legitimately match on filenames, which is why this filter lives here and not in
      _query_from: the two channels want different things from the same trigger.

      ANOTHER TOOL'S SUBCOMMAND -- `git status` summoned our `status`; `npm install` summoned
      `kit`. The token after a known external executable belongs to that executable.

      THE VERB ALREADY BEING RUN -- `py agent_cli.py boot claude` summoned `boot`. Telling an
      agent about the verb it is at that moment invoking is pure noise, and worse, it is the
      kind of noise that teaches a reader to skip the whole surface.

      FLEET NOISE -- agent ids appear in a large share of commands and carry no intent."""
    excl = set(_VERB_NOISE)
    if not command:
        return excl
    toks = command.split()
    for i, seg in enumerate(toks):
        low = seg.lower()
        # A URL is NOT a path. It is the SUBJECT of the action, and it carries the strongest
        # signal this channel has -- a youtube URL is the whole reason `captions` should speak.
        # Caught by the pins immediately after the path rule silenced the motivating case.
        is_url = "://" in low or low.startswith("www.")
        if not is_url and ("/" in seg or "\\" in seg or seg.endswith(".py")):
            excl |= {t.lower() for t in _TOKEN_RE.findall(seg)}
        if i > 0 and toks[i - 1].lower() in _EXTERNAL_TOOLS:
            excl |= {t.lower() for t in _TOKEN_RE.findall(seg)}
    if "agent_cli" in command:
        # the door is being driven directly: every bare token is a candidate verb being invoked
        excl |= {t.lower() for t in _TOKEN_RE.findall(command)}
    return excl


def _verbs(query: str, command: Optional[str] = None, limit: int = 2) -> List[Dict[str, Any]]:
    """Rank verbs against the SAME query the lessons ranked against, and stay quiet by default.

    Scoring is inverse-document-frequency over the verb corpus: a token appearing in one verb's
    help is worth 1.0, a token appearing in twenty is worth 0.05. The floor is therefore "at
    least one token that is nearly unique to this verb" -- 'youtube' names captions and nothing
    else; 'file' names half the door and must never fire.

    This floor is deliberately strict. Calibrated silence is a stated property of this surface,
    and a chatty verb channel would train the reader to skip the whole render, costing more than
    it pays. Pin: test_noise_floor_unrelated_trigger_surfaces_no_verbs."""
    try:
        index = verb_index()
        if not index or not query:
            return []
        df = _VERB_CACHE.get("df")
        if not df:
            df = {}
            for e in index:
                for t in _verb_tokens(e):
                    df[t] = df.get(t, 0) + 1
            _VERB_CACHE["df"] = df
        q = {t for t in query.split() if t and t not in _verb_exclusions(command)}
        scored: List[Any] = []
        for e in index:
            toks = _verb_tokens(e)
            hits = q & toks
            if not hits:
                continue
            score = sum(1.0 / df.get(t, 1) for t in hits)
            # A token that IS the verb's own name is the strongest signal available, and plain
            # IDF punishes it: 'friction' appears in two verbs' help, so the verb literally NAMED
            # friction scored 0.5 and was filtered. Naming the organ is not a coincidence, so a
            # name hit always clears the floor. (Found by the friction pin, 2026-08-15.)
            name_toks = {t.lower() for t in _TOKEN_RE.findall(e.get("verb", "").replace("-", " "))
                         if len(t) > 3}
            if q & name_toks:
                score = max(score, _VERB_FLOOR)
            elif len(hits) < 2:
                # ONE generic help-text token is not evidence of intent. This single rule killed
                # four of the eight measured false positives: 'directory' summoned `tally`,
                # 'install' summoned `kit`, 'item' summoned `defer`, 'remove' summoned `grant`.
                # IDF over 108 verbs cannot see that a token is common ENGLISH, only that it is
                # rare in this corpus -- so corroboration does the job frequency cannot.
                continue
            if score >= _VERB_FLOOR:
                scored.append((score, sorted(hits), e))
        scored.sort(key=lambda t: (-t[0], t[2].get("verb", "")))
        out = []
        for score, hits, e in scored[:max(0, limit)]:
            out.append({"verb": e["verb"], "purpose": e.get("purpose", ""),
                        "score": round(score, 3), "matched": hits})
        return out
    except Exception:
        return []


_VERB_FLOOR = float(os.environ.get("AKASHIC_VERB_FLOOR", "0.9"))


def recall_at(*, path: Optional[str] = None, command: Optional[str] = None,
              subject: Optional[str] = None, gesture: Optional[str] = None,
              domain: Optional[str] = None,
              agent_id: Optional[str] = None, limit: int = 3,
              min_relevance: Optional[float] = None, now: Optional[float] = None,
              learning_store: Optional[Any] = None,
              exclude_sources: Optional[set] = None,
              count_surface: bool = False) -> Dict[str, Any]:
    """Given a point of action (path and/or command), return the few highest-signal active items.
    `exclude_sources` (lesson sources already shown this session) enables hook anti-repeat.
    `min_relevance=None` -> the calibrated show-nothing floor (AKASHIC_RECALL_FLOOR); pass an
    explicit float (tests, callers with their own floor) to override.
    Deterministic, no-LLM, FAITH-gated, fail-soft (returns an empty result on any error)."""
    try:
        floor = _floor_default() if min_relevance is None else float(min_relevance)
        query = _query_from(path, command, subject, gesture)
        # An explicit domain wins; otherwise the trigger decides; otherwise nothing is scoped and
        # the whole corpus is searched, exactly as before domains existed.
        scope = domain or _domain_from_trigger(path, command, subject, gesture)
        lstats: Dict[str, int] = {}
        lessons, total = _lessons(query, now, limit, floor, learning_store, exclude_sources,
                                  agent_id=agent_id, stats_out=lstats, domain=scope) \
            if query else ([], 0)
        locks = _locks(path, agent_id)
        counter = None
        faithful, conf = True, 1.0
        if lessons:
            # Dissent (Tier 1): the strongest genuine counter to the TOP lesson, or None (silent).
            # Searched across the whole corpus (not just the surfaced few), so a disagreement that
            # doesn't itself match the action can still surface. Precision-first, deterministic, fail-soft.
            try:
                from core.recall.dissent import find_counter
                counter = find_counter(lessons[0], _cached_items(learning_store))
            except Exception:
                counter = None
            from core.primitives.faithfulness import faithfulness_report
            # R2 P10 (found by the pack replay's FIRST run): the FAITH check is PER ITEM.
            # It used to run once over the whole render and zero EVERYTHING on any
            # failure -- census case 4's confirmed HIT (faithful, conf 1.00) was silenced
            # because two higher-ranked NEIGHBOURS failed. Silence-beats-fabrication is
            # the right law per item: drop the unfaithful, keep the innocent. A silenced
            # HIT is invisible forever; that harm outranks the cost of N small checks.
            kept: List[Dict[str, Any]] = []
            confs: List[float] = []
            for it in lessons:
                rep = faithfulness_report([it], f"- {it['text']}  (source: {it['source']})")
                if rep["faithful"]:
                    kept.append(it)
                    confs.append(float(rep["confidence"]))
                else:
                    lstats["faith_dropped"] = lstats.get("faith_dropped", 0) + 1
            if counter is not None:
                c_item = {"text": counter["text"], "source": counter["source"]}
                rep = faithfulness_report([c_item],
                                          f"- {c_item['text']}  (source: {c_item['source']})")
                if not rep["faithful"]:
                    counter = None            # a fabricated dissent is still fabricated
                else:
                    confs.append(float(rep["confidence"]))
            faithful = bool(kept)
            conf = min(confs) if confs else 0.0
            if not kept:
                # P9 (sol's fence): remember WHO silenced. This assignment used to destroy
                # the fact, and the exit then blamed the floor for the FAITH gate's verdict.
                lstats["faith_rejected"] = 1
                lessons, total, counter = [], 0, None   # nothing faithful survived
            else:
                total -= lstats.get("faith_dropped", 0)
                lessons = kept
        if count_surface and lessons:
            bump_surfaced([l.get("source") for l in lessons])   # impression count (best-effort, feeds noise-decay)
        # R2 s0: EVERY exit records an outcome. empty_query ("nothing was even rankable")
        # is a different fact from floor_silent ("ranked; nothing cleared the floor") --
        # conflating them hides query-construction bugs behind an honest-looking silence.
        # Guarded AT THE CALL SITE, not only inside the callee (P6): _record_outcome is
        # fail-safe internally, but a replaced/broken sink raising HERE would fall into the
        # outer except and convert a SUCCESSFUL recall into an error-empty -- the caller
        # would lose its items to an observability write. Same belt-and-suspenders as
        # liveness._safe_code_sha, same reason.
        try:
            shape = ("command" if command else "path" if path else "")
            if lessons:
                _record_outcome("fired", query=query, n_items=len(lessons),
                                agent_id=agent_id or "", query_shape=shape)
            elif not query:
                _record_outcome("silent", "empty_query", agent_id=agent_id or "",
                                query_shape=shape)
            elif lstats.get("faith_rejected"):
                # cleared the floor; the FAITH gate rejected the render (sol P9)
                _record_outcome("silent", "unfaithful_silent", query=query,
                                agent_id=agent_id or "", query_shape=shape)
            elif lstats.get("above_floor", 0) > 0 and \
                    lstats.get("excluded", 0) >= lstats.get("above_floor", 0):
                # everything that cleared the floor was withheld (anti-repeat /
                # self-echo) -- 'already shown' is not 'nothing relevant' (sol P8)
                _record_outcome("silent", "excluded_silent", query=query,
                                agent_id=agent_id or "", query_shape=shape,
                                excl_kind=_excl_kind(lstats),
                                excl_counts={k: lstats[f"excluded_{k}"]
                                             for k in (EXCL_ANTIREPEAT, EXCL_SELF_ECHO)
                                             if lstats.get(f"excluded_{k}")})
            else:
                _record_outcome("silent", "floor_silent", query=query,
                                agent_id=agent_id or "", query_shape=shape)
        except Exception:
            pass
        # T311: verbs ride the same query the lessons ranked against. Computed independently of
        # `lessons` on purpose -- the motivating case (a YouTube URL, and `captions` on the door)
        # had NO matching lesson, so gating verbs on a lesson hit would have stayed silent in the
        # exact situation that prompted this channel.
        verbs = _verbs(query, command=command) if query else []
        return {"path": path, "command": command, "query": query, "lessons": lessons,
                "locks": locks, "counter": counter, "verbs": verbs,
                "shown": len(lessons) + len(locks),
                "total": total, "faithful": faithful, "confidence": conf}
    except Exception as e:
        # faithful/confidence describe a check that RAN. This one raised, so they are
        # UNAVAILABLE -- not True, not 1.0.
        #
        # Found by codex 2026-07-25: this handler returned faithful=True, confidence=1.0,
        # which renders as "I looked thoroughly and there is genuinely nothing relevant."
        # The `error` key was set here and read NOWHERE, so a store failure in the hot path
        # was indistinguishable from an honest empty. Silence meaning "nothing relevant" and
        # silence meaning "I could not look" are different facts and must not share a
        # rendering. Sixth instance of this genus today and the worst-placed -- recall-at
        # fires before every edit and command.
        # R2 s0: the crash-empty is RECORDED as its own reason. An empty-from-crash that
        # renders identically to an empty-from-judgment is the confident-zero disease at
        # the meta level (recall_at_error_masks_as_confident_empty, landed as pin P4).
        try:
            _record_outcome("silent", "error_empty", agent_id=agent_id or "")
        except Exception:
            pass                              # the fail-soft contract outranks the record
        return {"path": path, "command": command, "query": "", "lessons": [], "locks": [],
                "counter": None, "verbs": [], "shown": 0, "total": 0,
                "faithful": None, "confidence": None,
                "error": type(e).__name__, "error_detail": str(e)[:200]}


def _provenance_tag(item: Dict[str, Any]) -> str:
    """A terse, honest status prefix for a recalled lesson — the antidote to opinion-laundering
    (Factor 1). Encodes outcome-status + author + claim-kind from provenance the store already
    holds, so a self-authored, unverified hypothesis can't come back framed as an external verified
    fact. Status is the AUTHOR'S OWN report ('worked' = self-reported success, not an independent
    check). Kept ASCII + short to stay off the context-rot / meta-noise line (Factors 6, 9).

    NB: the store normalizes a MISSING success to 'no', so the non-success bucket is labelled
    'unverified' ('not a confirmed success' — failed OR never checked), never the over-claim 'failed'.
    A populated `anti_pattern` is the one case we *can* call out as actively known-bad."""
    success = str(item.get("success", "")).lower()
    author = str(item.get("agent_id") or "").strip()
    field = item.get("field") or ""
    parts: List[str] = []
    if item.get("bench_probe"):
        # FIRST, because it qualifies everything after it. This lesson was BENCHED for
        # surfacing repeatedly without ever earning credit, and is here only because it is
        # being re-tested. Rendering it identically to a lesson that earned its slot is the
        # exact over-claim this function exists to prevent -- and it is what shipped for a
        # few hours: the field was written at projection time and no renderer read it, so
        # the commit message's claim that probes are marked was false until now.
        # (deepseek's review, finding (b).)
        parts.append("probation")
    if item.get("anti_pattern"):
        parts.append("anti-pattern")          # documented known-bad: doing this IS the mistake
    elif success in ("yes", "true"):
        # 'worked', NOT 'verified': success=yes is the AUTHOR'S OWN report, not an independent check.
        # Calling it 'verified' would re-launder a self-claim as external fact (the exact Factor-1 trap).
        # Independent corroboration (a cross-agent `helped`) could later earn a stronger 'confirmed' tag.
        parts.append("worked")
    elif success == "partial":
        parts.append("partial")
    else:
        parts.append("unverified")
    if author and author.lower() != "unknown":
        parts.append(author)
    if field == "recommendation" and success not in ("yes", "true"):
        parts.append("advice")                # forward-looking suggestion, not an observation
    # Track record (the confidence-score analog Greptile v4 validated as triage UI): EARNED
    # credit only -- 'helped' (automatic FAIL->SUCCESS) and 'useful' (explicit votes). Silent at
    # zero; counts ride the cached _use counters (<= cache-TTL stale, same as ranking already is).
    use = item.get("_use") or {}
    for kind in ("helped", "useful"):
        try:
            n = int(use.get(kind, 0) or 0)
        except Exception:
            n = 0
        if n > 0:
            parts.append(f"{kind} {n}x")
    return "[" + " ".join(parts) + "]"


def render(result: Dict[str, Any], *, max_chars: int = 110,
           header: str = "Recall-at-action (Akashic) - facts relevant to what you're about to do:",
           hint_style: str = "cli") -> str:
    """Compact, agent-readable rendering for the hook's additionalContext. Each lesson is prefixed
    with a provenance tag (verification-status + author + claim-kind) so the agent reads it with the
    right epistemic weight rather than as a settled fact. Empty result -> ''.

    When more lessons cleared the relevance floor than `limit` surfaced, appends a single N-of-M
    escape line — the cheap one-hop pull to the rest, instead of silently truncating (the "recommend
    less, retrieve more" pull-side: a capped surface should say so, not pretend it's complete)."""
    # A FAILED recall is not an empty one. Say so instead of rendering ordinary silence --
    # otherwise a store outage looks exactly like "nothing relevant here" and the agent acts
    # on a confidence nobody computed. Loud on purpose: this fires before every edit.
    if result.get("error"):
        return ("Recall-at-action (Akashic) - UNAVAILABLE: retrieval failed "
                f"({result.get('error')}). This is NOT 'no relevant lessons' -- the check did "
                "not run, so treat this action as unadvised and re-run recall if it matters.")
    lines: List[str] = []
    for lk in result.get("locks", []):
        lines.append(f"[lock] {lk.get('held_by')} holds an advisory lock on this path — coordinate before editing")
    for l in result.get("lessons", []):
        s = l.get("text", "")
        if len(s) > max_chars:
            s = s[:max_chars].rsplit(" ", 1)[0] + "..."
        lines.append(f"{_provenance_tag(l)} {s} (source: {l.get('source')})")
    # Dissent line: the strongest genuine counter to the TOP lesson (Tier 1). Silent when none — a
    # manufactured counter would be a hallucinated disagreement, the exact failure we're avoiding.
    counter = result.get("counter")
    if counter and counter.get("text"):
        shown_src = {l.get("source") for l in result.get("lessons", [])}
        if counter.get("source") in shown_src:
            # the counter is one of the lessons already shown -> flag the disagreement, don't repeat text
            lines.append(f"[counter] the top lesson is disputed above by {counter.get('source')}")
        else:
            cs = counter["text"]
            if len(cs) > max_chars:
                cs = cs[:max_chars].rsplit(" ", 1)[0] + "..."
            lines.append(f"[counter] {cs} (source: {counter.get('source')})")
    # T311 verb channel: the door already has a verb for this. Rendered AFTER the lessons because
    # lessons are the proven cargo and verbs ride along; rendered BEFORE the empty-check so a
    # trigger that matches a verb but no lesson still speaks -- that was the motivating case.
    # hint_style is honoured for the same reason T048 gave it: naming `py agent_cli.py <verb>` to
    # a tool-loop reader that cannot run CLI verbs is a dead end in its surface.
    for v in result.get("verbs", []):
        p = v.get("purpose", "")
        if len(p) > max_chars:
            p = p[:max_chars].rsplit(" ", 1)[0] + "..."
        if hint_style == "tool":
            lines.append(f"[verb] the door already has a `{v.get('verb')}` verb — {p}")
        else:
            lines.append(f"[verb] `py agent_cli.py {v.get('verb')}` — {p}")
    if not lines:
        return ""
    shown, total = len(result.get("lessons", [])), result.get("total", 0)
    if total > shown:
        # T048 item 1 (deepseek interview): the escape hint must name a surface the READER can
        # actually use -- a tool-loop agent cannot run CLI verbs, so hint_style="tool" names its
        # registered tools instead (the CLI-shaped hint was a dead end in its tool surface).
        if hint_style == "tool":
            lines.append(f"... {shown} of {total} relevant lesson(s) shown — call recall_at(limit={total}) "
                          f"for the rest, or knowledge_full(source=\"<source>\") for any one's whole record")
        else:
            lines.append(f"... {shown} of {total} relevant lesson(s) shown — `recall-at --limit {total}` for the rest, "
                          f"or `recall --full <source>` for any one's whole record")
    # Staleness cue (first-party fold-in 2026-07-08): a lesson describes the repo AS OF WRITING —
    # the older it is, the likelier its named files/flags/verbs have moved. One line, and only
    # when an old lesson is actually on this surface (silent otherwise — surface discipline).
    try:
        if _STALE_CUE_DAYS > 0 and result.get("lessons"):
            from core.foundation.timeutil import to_epoch
            ages = [(time.time() - to_epoch(l.get("timestamp"))) / 86400.0
                    for l in result["lessons"] if to_epoch(l.get("timestamp") or 0) > 0]
            oldest = max(ages) if ages else 0.0
            if oldest >= _STALE_CUE_DAYS:
                lines.append(f"[age] oldest lesson shown is ~{int(oldest)}d old — it reflects the repo as of "
                             "writing; verify named files/flags still exist before leaning on it")
    except Exception:
        pass   # the cue is a bonus; its failure must never cost the surface
    # Legend (T048 item 4, deepseek design): define the provenance terms IN BAND, but only when a
    # surfaced lesson actually carries credibility markers. Reference material -> renders LAST, so
    # it is the first thing the 900-char cap truncates.
    try:
        def _has_marker(l):
            use = l.get("_use") or {}
            return (use.get("helped") or use.get("useful")
                    or str(l.get("success", "yes")).lower() not in ("", "yes", "true"))
        if any(_has_marker(l) for l in result.get("lessons", [])):
            lines.append("[legend] worked=self-reported | helped=auto credit | useful=vote | "
                         "unverified=unconfirmed | anti-pattern=known-bad | advice=forward-looking")
    except Exception:
        pass
    # Factual framing (not imperative — imperative trips prompt-injection defenses). Hard total cap
    # well under Claude Code's 10k-char additionalContext limit.
    body = header + "\n" + "\n".join(lines)
    return body[:900]
