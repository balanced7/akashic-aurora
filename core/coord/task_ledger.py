"""Governed task ledger — the deterministic coordination substrate (Phase 1: sequential-correct).

WHY: the fleet reworks + confuses itself because agents read an append-only MESSAGE stream and infer
intent — a three-hour-old "apply the perf fix" reads as a live directive even though it's long done.
The fix: make TASKS (not messages) the unit of coordination, with a validated lifecycle. Agents read
the LEDGER (curated current truth), never the raw backlog. Anything DONE is closed.

GOVERN BY THE ENVIRONMENT, DETERMINISTICALLY: invalid transitions are REJECTED here in code — no model
in the loop deciding what's allowed. A misbehaving agent physically cannot rework, clobber, or close
work without proof, because these gates block it.

Slice A (this file): the pure state machine + validated transitions + git-durable JSON persistence.
Slice B adds the Redis mirror for fast reads; C wires boot/wake to read-state-first; D the conductor.

Gates enforced here:
- transition validity  — only lifecycle-legal moves (TRANSITIONS).
- claim gate           — an APPROVED task, all deps DONE, its files held by no other active task, not
                         already done.
- one-in-progress gate — Phase 1: at most ONE task IN_PROGRESS globally (sequential-correct).
- done gate            — cannot close without a commit SHA + a verification record. No proof, no close.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

# repo root is two dirs up from core/coord/
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER_PATH = os.path.join(_ROOT, "state", "coord", "tasks.json")

# --- Redis mirror (Slice B) --------------------------------------------------------------------
# The git file above is ALWAYS the source of truth. Redis is a fast, FAIL-OPEN read cache: every
# write goes through to it, but any Redis error is a no-op and readers fall back to the git file.
# ns-isolation GLOBAL (2026-07-12, deliberate -- deepseek-reviewed): the task ledger is PROJECT
# INFRASTRUCTURE -- one git-durable source of truth for the governed task roster across ALL
# namespaces. Scoping would fork the ledger per-namespace. In the GLOBAL_MODULES allowlist
# (see tests/test_coordination_namespace_isolation.py).
REDIS_LEDGER_KEY = "bifrost:coord:ledger"
REDIS_VER_KEY = "bifrost:coord:ledger:v"


def _bus_client():
    """The shared bus Redis client, or None if unreachable. Same connector control.py uses."""
    try:
        from core.comm.bus import get_bus
        return get_bus("coord")._client
    except Exception:
        return None


def _decode(v):
    return v.decode() if isinstance(v, (bytes, bytearray)) else v

# --- lifecycle ---------------------------------------------------------------------------------
PROPOSED, APPROVED, CLAIMED, IN_PROGRESS, VERIFYING, DONE, BLOCKED, ABANDONED, PARKED = (
    "proposed", "approved", "claimed", "in_progress", "verifying", "done", "blocked", "abandoned",
    "parked")

STATUSES = (PROPOSED, APPROVED, CLAIMED, IN_PROGRESS, VERIFYING, DONE, BLOCKED, ABANDONED, PARKED)

# who may move where. DONE/ABANDONED are terminal (empty set).
TRANSITIONS: Dict[str, set] = {
    PROPOSED:    {APPROVED, ABANDONED},
    APPROVED:    {CLAIMED, ABANDONED},
    CLAIMED:     {IN_PROGRESS, APPROVED, ABANDONED},   # release back to APPROVED if you can't do it
    IN_PROGRESS: {VERIFYING, BLOCKED, ABANDONED, PARKED},
    VERIFYING:   {DONE, IN_PROGRESS, BLOCKED},         # verification can bounce it back
    BLOCKED:     {APPROVED, IN_PROGRESS, ABANDONED},
    DONE:        set(),
    ABANDONED:   set(),
    # T083-C5-1: PARKED = deliberately shelved mid-flight (reason mandatory). Unlike BLOCKED
    # (waiting on something external, still "the" current work), a parked wave FREES the Phase-1
    # sequential slot (the gate checks status==IN_PROGRESS specifically) while KEEPING its owner +
    # file claims -- resuming re-enters through the same one-in-progress gate. Live receipt
    # 2026-07-16: T075 (explicitly 'PARKED behind T047' in its own text) held the slot for a day
    # and blocked T081's done transition. Prior art: issue-tracker on-hold states.
    PARKED:      {IN_PROGRESS, ABANDONED},
}
ACTIVE = {CLAIMED, IN_PROGRESS, VERIFYING}   # occupies the sequential slot / working set
FILE_HOLDING = ACTIVE | {PARKED}             # parked work still owns its files (no mid-park grabs)


class LedgerError(Exception):
    """A rejected transition. The message names the gate that blocked it (teaches the fix)."""


class TaskLedger:
    def __init__(self, path: str = LEDGER_PATH, client: Any = "auto"):
        self.path = path
        # client: "auto" resolves the bus Redis client lazily; None disables the mirror (git-only,
        # used by tests); or pass an object with get/set for an injected/fake client.
        self._client = client
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._seq = 0
        self.load()

    def _mirror_client(self):
        if self._client == "auto":
            self._client = _bus_client()   # resolve once
        return self._client

    def _mirror(self) -> None:
        """Write-through the whole ledger to Redis (fast reads). Best-effort; git file is the truth."""
        c = self._mirror_client()
        if c is None:
            return
        try:
            c.set(REDIS_LEDGER_KEY, json.dumps({"seq": self._seq, "tasks": list(self.tasks.values())}))
            c.set(REDIS_VER_KEY, str(self._seq))
        except Exception:
            pass   # fail-open

    # --- persistence (git-durable source of truth) ---------------------------------------------
    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.tasks = {t["id"]: t for t in data.get("tasks", [])}
            self._seq = int(data.get("seq", len(self.tasks)))
        except Exception as e:
            raise LedgerError(f"ledger unreadable at {self.path}: {e}")

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        payload = {"seq": self._seq, "tasks": list(self.tasks.values())}
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp, self.path)   # atomic write — never a half-written ledger
        self._mirror()               # write-through to the Redis read cache (best-effort)

    # --- reads (what agents obey instead of the backlog) ---------------------------------------
    def get(self, tid: str) -> Optional[Dict[str, Any]]:
        return self.tasks.get(tid)

    def by_status(self, status: str) -> List[Dict[str, Any]]:
        return [t for t in self.tasks.values() if t["status"] == status]

    def in_progress(self) -> List[Dict[str, Any]]:
        return [t for t in self.tasks.values() if t["status"] in ACTIVE]

    def is_done(self, tid: str) -> bool:
        t = self.tasks.get(tid)
        return bool(t) and t["status"] == DONE

    def files_held(self, exclude: Optional[str] = None) -> Dict[str, str]:
        """path -> task_id for every file a FILE_HOLDING task holds (exclude one task if given).
        T083-C5-1: parked tasks keep their claims -- shelved work must not lose its files."""
        held: Dict[str, str] = {}
        for t in self.tasks.values():
            if t["id"] == exclude or t["status"] not in FILE_HOLDING:
                continue
            for f in t.get("files", []):
                held[f] = t["id"]
        return held

    # --- writes (all validated) ----------------------------------------------------------------
    def propose(self, title: str, *, desc: str = "", owner: str = "", deps: Optional[List[str]] = None,
                files: Optional[List[str]] = None, acceptance: str = "", by: str = "claude",
                at: str = "") -> Dict[str, Any]:
        """Add a task in PROPOSED. `at` is an ISO timestamp passed in (this module never reads the clock,
        so it stays pure + testable). Unknown deps are allowed at propose time; the CLAIM gate enforces
        that deps are DONE, so a not-yet-created dep just keeps the task un-claimable until it exists+done."""
        self._seq += 1
        tid = f"T{self._seq:03d}"
        task = {
            "id": tid, "title": title, "desc": desc, "owner": owner,
            "deps": list(deps or []), "files": list(files or []), "acceptance": acceptance,
            "status": PROPOSED, "commit": None, "verified_by": None,
            "created": at, "updated": at,
            "history": [{"to": PROPOSED, "by": by, "at": at}],
        }
        self.tasks[tid] = task
        self.save()
        return task

    def transition(self, tid: str, to: str, *, by: str = "", at: str = "", commit: str = "",
                   verified_by: str = "", owner: str = "", reason: str = "") -> Dict[str, Any]:
        """The one guarded mutation. Validates the move against every gate, then applies + persists.
        Raises LedgerError (naming the gate) on any violation — nothing partial is written."""
        t = self.tasks.get(tid)
        if not t:
            raise LedgerError(f"no such task {tid}")
        frm = t["status"]
        if to not in STATUSES:
            raise LedgerError(f"unknown status {to!r}")
        if to not in TRANSITIONS.get(frm, set()):
            raise LedgerError(f"illegal transition {frm} -> {to} for {tid} "
                              f"(allowed: {sorted(TRANSITIONS.get(frm, set())) or 'none — terminal'})")

        # --- claim gate ---
        if to == CLAIMED:
            unmet = [d for d in t["deps"] if not self.is_done(d)]
            if unmet:
                raise LedgerError(f"claim blocked: deps not DONE {unmet}")
            held = self.files_held(exclude=tid)
            clash = {f: held[f] for f in t["files"] if f in held}
            if clash:
                raise LedgerError(f"claim blocked: files held by another active task {clash}")

        # --- park gate (T083-C5-1): shelving without a why is exactly the ambiguity P5 ended ---
        if to == PARKED and not reason:
            raise LedgerError("park blocked: needs a --reason (why is this wave shelved, and "
                              "what unparks it)")

        # --- one-in-progress gate (Phase 1: sequential-correct) ---
        if to == IN_PROGRESS:
            others = [o["id"] for o in self.in_progress() if o["id"] != tid and o["status"] == IN_PROGRESS]
            if others:
                raise LedgerError(f"serialize: another task is IN_PROGRESS {others} "
                                  f"(Phase 1 runs one at a time)")

        # --- done gate ---
        if to == DONE:
            c = commit or t.get("commit")
            v = verified_by or t.get("verified_by")
            if not c or not v:
                raise LedgerError("done blocked: needs a commit SHA AND a verification record "
                                  "(no proof, no close)")
            t["commit"], t["verified_by"] = c, v
            try:                              # T056: finalize the cost accumulator (fail-open;
                from core.coord.task_costs import finalize   # absent accumulator stamps nothing)
                finalize(tid, t)
            except Exception:
                pass

        # apply
        if owner:
            t["owner"] = owner
        if commit:
            t["commit"] = commit
        if verified_by:
            t["verified_by"] = verified_by
        t["status"] = to
        t["updated"] = at
        entry = {"to": to, "by": by, "at": at}
        if reason:
            entry["reason"] = reason
        t["history"].append(entry)
        self.save()
        return t


# convenience wrappers (each is just a named transition — readable call sites)
def _t(ledger: TaskLedger, tid: str, to: str, **kw): return ledger.transition(tid, to, **kw)
def approve(ledger, tid, **kw):  return _t(ledger, tid, APPROVED, **kw)
def claim(ledger, tid, owner, **kw):  return _t(ledger, tid, CLAIMED, owner=owner, **kw)
def start(ledger, tid, **kw):    return _t(ledger, tid, IN_PROGRESS, **kw)
def verifying(ledger, tid, **kw):return _t(ledger, tid, VERIFYING, **kw)
def done(ledger, tid, commit, verified_by, **kw): return _t(ledger, tid, DONE, commit=commit, verified_by=verified_by, **kw)
def block(ledger, tid, reason, **kw): return _t(ledger, tid, BLOCKED, reason=reason, **kw)
def abandon(ledger, tid, reason, **kw): return _t(ledger, tid, ABANDONED, reason=reason, **kw)   # P5: terminal, reasoned
def park(ledger, tid, reason, **kw): return _t(ledger, tid, PARKED, reason=reason, **kw)         # C5-1: shelved, reasoned, slot freed
def unpark(ledger, tid, **kw): return _t(ledger, tid, IN_PROGRESS, **kw)                         # C5-1: resumes through the one-in-progress gate


# --- fast reads (Slice B): what agents obey instead of the message backlog ---------------------
def read_ledger(path: str = LEDGER_PATH, client: Any = "auto") -> Dict[str, Any]:
    """Read the current ledger FAST. Prefers the Redis mirror (one GET); falls back to the git file
    (the source of truth) if Redis is empty or unreachable. Returns {"seq", "tasks": [...]}"."""
    c = _bus_client() if client == "auto" else client
    if c is not None:
        try:
            raw = c.get(REDIS_LEDGER_KEY)
            if raw:
                return json.loads(_decode(raw))
        except Exception:
            pass
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            pass
    return {"seq": 0, "tasks": []}


STALE_PROPOSED_DAYS = 7   # default; render callers may override via env AKASHIC_PROPOSED_STALE_DAYS


def _age_days(t: Dict[str, Any], now_ts: float) -> Any:
    """Days since the task was last TOUCHED (updated stamp; created as fallback). None if unparseable."""
    from datetime import datetime
    raw = t.get("updated") or t.get("created") or ""
    try:
        return max(0.0, (now_ts - datetime.fromisoformat(raw).timestamp()) / 86400)
    except (ValueError, TypeError):
        return None


def state_view(path: str = LEDGER_PATH, client: Any = "auto", *,
               now: Any = None, stale_days: int = STALE_PROPOSED_DAYS) -> Dict[str, Any]:
    """The read-state-first view (used by boot/wake in Slice C). 'next' = APPROVED tasks whose deps
    are all DONE (claimable now). This is the curated current truth agents read, not the backlog.

    P5 (T025): pass `now` (epoch seconds -- the CALLER owns the clock; this module stays pure)
    and proposed entries gain stale/age_days: a proposal untouched past `stale_days` is parked
    intent that must be re-approved or abandoned, not silently counted as live."""
    led = read_ledger(path, client)
    tasks = led.get("tasks", [])
    done_ids = {t["id"] for t in tasks if t["status"] == DONE}

    def summ(t):
        s = {"id": t["id"], "title": t["title"], "owner": t.get("owner", ""),
             "status": t["status"], "commit": t.get("commit"), "files": t.get("files", [])}
        for ck in ("cost_turns", "cost_duration_s", "cost_tool_calls", "cost_tokens"):
            if ck in t:                       # T056: cost stamps ride the summary (done-only render)
                s[ck] = t[ck]
        if now is not None and t["status"] == PROPOSED:
            age = _age_days(t, float(now))
            s["age_days"] = age
            s["stale"] = bool(age is not None and stale_days and age > stale_days)
        return s

    def _park_reason(t):
        for h in reversed(t.get("history") or []):
            if h.get("to") == PARKED:
                return h.get("reason", "")
        return ""

    return {
        "done": [summ(t) for t in tasks if t["status"] == DONE],
        "in_progress": [summ(t) for t in tasks if t["status"] in ACTIVE],
        "next": [summ(t) for t in tasks if t["status"] == APPROVED
                 and all(d in done_ids for d in t.get("deps", []))],
        "proposed": [summ(t) for t in tasks if t["status"] == PROPOSED],
        "blocked": [summ(t) for t in tasks if t["status"] == BLOCKED],
        "parked": [{**summ(t), "reason": _park_reason(t)}
                   for t in tasks if t["status"] == PARKED],   # C5-1: shelved, reasoned, visible
        "counts": {s: sum(1 for t in tasks if t["status"] == s) for s in STATUSES},
    }


def format_state(agent: str = "", path: str = LEDGER_PATH, client: Any = "auto",
                 now: Any = None) -> str:
    """The READ-STATE-FIRST block shown at boot + wake (Slice C). Agents obey THIS, not the message
    backlog — an old 'apply the fix' message can't cause rework because the ledger says it's DONE.
    An empty ledger prints a clear 'no governed tasks yet' line so it never reads as a bug.
    With `now` (P5), stale proposals are counted and listed for a verdict instead of passing
    as live intent."""
    stale_days = STALE_PROPOSED_DAYS
    try:
        stale_days = int(os.environ.get("AKASHIC_PROPOSED_STALE_DAYS", stale_days))
    except (ValueError, TypeError):
        pass
    v = state_view(path, client, now=now, stale_days=stale_days)
    c = v["counts"]
    if sum(c.values()) == 0:
        return ("## TASK LEDGER (governed coordination)\n"
                "  (empty -- no governed tasks yet; nothing to redo or claim)\n")

    def sha(t):
        return (t.get("commit") or "")[:8]

    out = ["## TASK LEDGER -- obey THIS, not old messages"]
    if v["done"]:
        out.append("DONE (closed -- do NOT redo):")
        def _cost(t):
            try:                              # T056: retro-only cost line (fail-soft)
                from core.coord.task_costs import cost_line
                cl = cost_line(t)
                return f"  [{cl}]" if cl else ""
            except Exception:
                return ""
        out += [f"  {t['id']} - {t['title']}" + (f"  @{sha(t)}" if sha(t) else "") + _cost(t)
                for t in v["done"]]
    if v["in_progress"]:
        out.append("IN PROGRESS:")
        out += [f"  {t['id']} - {t['title']}  ({t['status']}"
                + (f", {t['owner']}" if t['owner'] else "") + ")" for t in v["in_progress"]]
    if v.get("parked"):
        out.append("PARKED (shelved with a reason -- slot freed; unpark to resume):")
        out += [f"  {t['id']} - {t['title'][:90]}  ({t.get('reason', '')[:80]})"
                for t in v["parked"]]
    if v["next"]:
        out.append("NEXT (claimable now):")
        out += [f"  {t['id']} - {t['title']}"
                + ("  <- you" if agent and t['owner'] == agent else "") for t in v["next"]]
    stale = [t for t in v["proposed"] if t.get("stale")]
    if stale:
        out.append("PROPOSED BUT STALE (parked intent -- re-approve or abandon, do not treat as live):")
        out += [f"  {t['id']} - {t['title'][:90]}  (untouched {t.get('age_days', 0):.0f}d)"
                for t in stale]
    prop = f"proposed {c[PROPOSED]}" + (f" ({len(stale)} stale)" if stale else "")
    parked_bar = f" | parked {c[PARKED]}" if c.get(PARKED) else ""
    out.append(f"(done {c[DONE]} | active {c[CLAIMED] + c[IN_PROGRESS] + c[VERIFYING]} | "
               f"next {len(v['next'])} | {prop} | blocked {c[BLOCKED]}{parked_bar})")
    out.append("RULE: anything in DONE is closed. Work only your assigned/NEXT task. "
               "Ignore backlog messages that contradict the ledger.")
    return "\n".join(out) + "\n"


def sync_redis_from_git(path: str = LEDGER_PATH, client: Any = "auto") -> bool:
    """Rehydrate the Redis mirror from the git file (the truth). Call on boot / after a Redis flush,
    so the fast cache can never be authoritatively wrong. Returns True iff it wrote."""
    c = _bus_client() if client == "auto" else client
    if c is None or not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as fh:
            data = fh.read()
        c.set(REDIS_LEDGER_KEY, data)
        c.set(REDIS_VER_KEY, str(json.loads(data).get("seq", 0)))
        return True
    except Exception:
        return False
