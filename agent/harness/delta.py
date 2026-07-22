"""The delta door (T052 / wishlist R1) -- "what changed since I was last here."

ONE mechanism serving every agent's continuity: a per-agent SEEN MARK (four positions:
git_commit / ledger_seq / notes_head / promoted_id) + a budgeted render of what moved.
Build spec: research/reviewed/r1-delta-door-reconciliation-2026-07-14.md (full-fence
reconciliation, deepseek-confirmed). Pins: tests/test_t052_delta_door.py (P1-P8).

MARK-LAG CONTRACT (D1 ruling, deepseek's corrected form): building a delta block NEVER
writes the mark. `delta_boot_block` returns (text, commit_fn); the CALLER invokes
commit_fn only after the context containing the block has been DELIVERED. A crash
before commit leaves the old mark -- the whole gap redelivers next boot (RB-26
geometry anchored at delivery). Consequence, accepted knowingly: an agent's next delta
includes its OWN prior-session outputs -- correct under context-death reality; the git
render groups by author so self-echo skims fast.

Positions are each INDEPENDENTLY fail-soft ("?" on error; "?" never counts as moved --
unknown is not movement). The mark is a Redis-cache, not a durability requirement:
loss degrades to today's full boot (C6). Raw bus positions are deliberately ABSENT
(D2 ruling): live mail belongs to the UNREAD/wake surfaces; the delta tracks only the
durable-salient promoted stream.
"""
import os
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIELDS = ("git_commit", "ledger_seq", "notes_head", "promoted_id")
BUDGET_DEFAULT = 1200
RENDER_TTL_S = 30          # X1: turn_metrics EST_CACHE_TTL pattern
GIT_CAP = 10               # commits listed before the pull pointer takes over


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _redis():
    try:
        from core.foundation.redis_connection import (
            connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
        return connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST,
                                               port=DEFAULT_REDIS_PORT,
                                               timeout_seconds=3, decode_responses=True)
    except Exception:
        return None


# ---------------------------------------------------------------- position sources
def _git(*args: str) -> Optional[str]:
    try:
        # The MCP server owns stdin as its JSON-RPC transport.  If Git inherits that
        # handle on Windows, a completed boot response can remain pending until the
        # client sends another frame (C7-4).  Delta runs during every full boot, so
        # explicitly detach the child from the transport.
        r = subprocess.run(["git", "-C", REPO] + list(args),
                           stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=10, close_fds=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _git_head() -> str:
    return _git("rev-parse", "HEAD") or "?"


def _git_log_range(frm: str, to: str) -> Optional[List[str]]:
    """Oneline subjects with author initials, oldest range capped upstream. None on any
    git failure (unknown sha, backwards range) -- the caller classifies."""
    out = _git("log", f"{frm}..{to}", "--pretty=format:%h %an: %s", f"--max-count={200}")
    if out is None:
        return None
    return [ln for ln in out.splitlines() if ln.strip()]


def _git_is_forward(mark_sha: str, head_sha: str) -> Optional[bool]:
    """True = mark is an ancestor of HEAD (normal forward motion); False = backwards or
    diverged or unknown sha (all deserve the loud path); None never returned -- errors
    classify as False because 'cannot prove forward' and 'moved backwards' get the same
    honest render (P4)."""
    try:
        r = subprocess.run(["git", "-C", REPO, "merge-base", "--is-ancestor",
                            mark_sha, head_sha], capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


def _ledger_seq() -> str:
    c = _redis()
    if c is not None:
        try:
            v = c.get("bifrost:coord:ledger:v")     # GLOBAL by design (task_ledger.py)
            if v is not None:
                return str(v)
        except Exception:
            pass
    try:
        from core.coord.task_ledger import TaskLedger
        return str(TaskLedger()._seq)
    except Exception:
        return "?"


def _notes_head() -> str:
    """Fingerprint of note freshness across BOTH stores (D4): the max created_at."""
    try:
        from core.learning.agent_memory import get_agent_memory
        mem = get_agent_memory()
        stamps: List[str] = []
        for pull in (lambda: mem.get_decisions(days=90),
                     lambda: mem.get_experiences(days=90)):
            try:
                stamps += [str(x.created_at) for x in (pull() or [])]
            except Exception:
                pass
        return max(stamps) if stamps else "0"
    except Exception:
        return "?"


def _promoted_id() -> str:
    """Newest durable-salient position (bifrost_msg projection via promoter.promoted_page
    -- the same seam the boot's RECENT DECISIONS section reads)."""
    try:
        from core.comm.promoter import promoted_page
        evs, _more = promoted_page(limit=1, now=time.time())
        if not evs:
            return "0"
        e0 = evs[0]
        get = e0.get if isinstance(e0, dict) else lambda k, d=None: getattr(e0, k, d)
        return str(get("id") or get("at") or get("ts") or "0")
    except Exception:
        return "?"


def current_positions(agent: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for field, fn in (("git_commit", _git_head), ("ledger_seq", _ledger_seq),
                      ("notes_head", _notes_head), ("promoted_id", _promoted_id)):
        try:
            out[field] = str(fn())
        except Exception:
            out[field] = "?"
    return out


# ---------------------------------------------------------------- the mark
class DeltaMark:
    """The per-agent seen mark: {ns}:delta:mark:{agent}, one field per source.
    Plain HSET (X5): boot-owned, twin overwrite = harmless over-delivery (D5c)."""

    def __init__(self, agent: str):
        self.agent = str(agent)

    def key(self) -> str:
        return f"{_ns()}:delta:mark:{self.agent}"

    def read(self) -> Optional[Dict[str, str]]:
        c = _redis()
        if c is None:
            return None
        try:
            h = c.hgetall(self.key()) or {}
        except Exception:
            return None
        return {f: str(h.get(f, "?")) for f in FIELDS} if h else None

    def write(self, positions: Dict[str, str]) -> bool:
        c = _redis()
        if c is None:
            return False
        try:
            c.hset(self.key(), mapping={f: str(positions.get(f, "?")) for f in FIELDS})
            return True
        except Exception:
            return False


# ---------------------------------------------------------------- render
def _moved(mark_v: str, cur_v: str) -> bool:
    """Unknown is not movement: '?' on either side never counts (P5)."""
    return mark_v != cur_v and "?" not in (mark_v, cur_v)


def _sections(agent: str, mark: Dict[str, str], cur: Dict[str, str]) -> List[str]:
    parts: List[str] = []
    # git -- range attempt first (P3's monkeypatch seam), classify on failure (P4)
    if _moved(mark["git_commit"], cur["git_commit"]):
        lines = _git_log_range(mark["git_commit"], cur["git_commit"])
        if lines:
            shown = lines[:GIT_CAP]
            more = len(lines) - len(shown)
            body = "\n".join(f"    {ln}" for ln in shown)
            tail = (f"\n    [+{more} more -- git log "
                    f"{mark['git_commit'][:7]}..{cur['git_commit'][:7]}]") if more else ""
            parts.append(f"  git: {len(lines)} commit(s)\n{body}{tail}")
        elif lines is None and not _git_is_forward(mark["git_commit"], cur["git_commit"]):
            parts.append(
                f"  git: HEAD moved BACKWARDS or diverged "
                f"({mark['git_commit'][:7]} -> {cur['git_commit'][:7]}); history changed "
                f"under you -- inspect: git log {cur['git_commit'][:7]}..{mark['git_commit'][:7]}")
        # lines == [] (empty forward range): same tree, nothing to say
    elif cur["git_commit"] == "?":
        parts.append("  git: (unavailable -- repository not readable)")
    if _moved(mark["ledger_seq"], cur["ledger_seq"]):
        parts.append(f"  ledger: moved {mark['ledger_seq']} -> {cur['ledger_seq']} -- "
                     f"transitions: py agent_cli.py task list")
    elif cur["ledger_seq"] == "?":
        parts.append("  ledger: (unavailable)")
    if _moved(mark["notes_head"], cur["notes_head"]):
        parts.append(f"  notes: updated since your mark -- py agent_cli.py notes")
    elif cur["notes_head"] == "?":
        parts.append("  notes: (unavailable)")
    if _moved(mark["promoted_id"], cur["promoted_id"]):
        parts.append(f"  bus: new promoted salient(s) -- py agent_cli.py promoted")
    elif cur["promoted_id"] == "?":
        parts.append("  bus: (unavailable)")
    return parts


def delta_boot_block(agent: str, budget: int = BUDGET_DEFAULT) -> Tuple[str, Callable[[], bool]]:
    """(text, commit_fn). Text is "" for newborns (no mark -> full boot unchanged, C3)
    and for an unmoved world (P6 zero-cost silence). commit_fn stamps the mark at
    CURRENT positions -- call it only after delivery (mark-lag)."""
    agent = str(agent)

    def commit() -> bool:
        return DeltaMark(agent).write(current_positions(agent))

    mark = DeltaMark(agent).read()
    if mark is None:
        return "", commit
    cur = current_positions(agent)
    parts = _sections(agent, mark, cur)
    if not any(_moved(mark[f], cur[f]) for f in FIELDS):
        return "", commit                      # P6: silence is free
    head = (f"[delta {agent}] since your last boot "
            f"({mark['git_commit'][:7]} -> {cur['git_commit'][:7]}):")
    text = "\n".join([head] + parts)
    if len(text) > budget:
        counts = f"[delta truncated: {len(parts)} section(s), {len(text)} chars -- " \
                 f"full: py agent_cli.py delta {agent}]"
        keep: List[str] = [head]
        for p in parts:
            if len("\n".join(keep + [p, counts])) > budget:
                break
            keep.append(p)
        text = "\n".join(keep + [counts])
        if len(text) > budget:                 # even one section overflows: counts only
            text = "\n".join([head, counts])[:budget]
    return text, commit


def render_full(agent: str) -> str:
    """The `delta` verb: full render, cached RENDER_TTL_S (X1). Never raises."""
    agent = str(agent)
    ckey = f"{_ns()}:delta:render:{agent}"
    c = _redis()
    if c is not None:
        try:
            hit = c.get(ckey)
            if hit:
                return str(hit)
        except Exception:
            pass
    mark = DeltaMark(agent).read()
    if mark is None:
        # Reviewer nit (t052 build review): do NOT cache the newborn message -- the first
        # boot stamps a mark within the TTL and a cached "no mark yet" would mask it.
        return (f"[delta {agent}] no mark yet (newborn) -- the mark writes at your next "
                f"boot; until then the full boot is the orientation")
    else:
        cur = current_positions(agent)
        parts = _sections(agent, mark, cur)
        head = (f"[delta {agent}] since your last boot "
                f"({mark['git_commit'][:7]} -> {cur['git_commit'][:7]}):")
        text = "\n".join([head] + parts) if parts else f"[delta {agent}] no changes since your last boot"
    if c is not None:
        try:
            c.set(ckey, text, ex=RENDER_TTL_S)
        except Exception:
            pass
    return text
