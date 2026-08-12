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
from typing import Any, Dict, List, Optional, Tuple

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
    # 2026-08-11: PARKED reachable from PROPOSED -- "still valid, just not now". The only exits
    # were ABANDONED (asserts the intent DIED when it merely DRIFTED) and the three-event detour
    # APPROVED -> CLAIMED -> PARKED, which manufactures a file claim to record one decision. Same
    # defect as the T139 and T083-C5-1 notes below, one status earlier in the lifecycle. Receipt:
    # 68 proposals standing, 32 rendered stale, every one facing those two bad doors. The mandatory
    # --reason gate is unchanged and pinned from this new origin, so the shorter route is a route
    # and not a hole.
    PROPOSED:    {APPROVED, ABANDONED, PARKED},
    APPROVED:    {CLAIMED, ABANDONED},
    CLAIMED:     {IN_PROGRESS, VERIFYING, APPROVED, ABANDONED, PARKED},
    #            ^ release: APPROVED drops it silently, PARKED shelves it WITH a reason.
    #
    # T139 (2026-08-03): VERIFYING is reachable from CLAIMED so a COMPLETION RECORD can be closed
    # without pretending to build it. Four entries were proposals whose own titles read "T110 DONE
    # (0a2e6a4+8fc841b)", "T113 DONE (67f9e1a)" and so on -- finished slices someone filed as new
    # entries instead of closing the originals. Reaching DONE required IN_PROGRESS, IN_PROGRESS is
    # serialized one-at-a-time, so recording four week-old deliveries meant faking four IN_PROGRESS
    # events; the only reachable terminal was ABANDONED, which asserts the intent DIED when it was
    # DELIVERED and drops the receipts out of the record.
    #
    # This is the SAME defect the PARKED note below records ("16 FALSE in_progress events ... purely
    # to reach a legal state"), at a different terminal, and it takes the same shape of fix.
    # VERIFICATION IS LITERALLY THE WORK: checking a claimed sha against the commit. The evidence bar
    # does not move -- the done gate still refuses without a commit AND a verification record, which
    # is what makes a shorter route safe rather than a hole -- and the serialize gate is untouched,
    # since it tests `to == IN_PROGRESS` specifically. A fresh proposal still walks the whole
    # lifecycle: APPROVED -> VERIFYING is not legal, only CLAIMED -> VERIFYING.
    IN_PROGRESS: {VERIFYING, BLOCKED, ABANDONED, PARKED},
    VERIFYING:   {DONE, IN_PROGRESS, BLOCKED, PARKED},  # verification can bounce it back, or shelve
    BLOCKED:     {APPROVED, IN_PROGRESS, ABANDONED},
    DONE:        set(),
    ABANDONED:   set(),
    # T083-C5-1: PARKED = deliberately shelved mid-flight (reason mandatory). Unlike BLOCKED
    # (waiting on something external, still "the" current work), a parked wave FREES the Phase-1
    # sequential slot (the gate checks status==IN_PROGRESS specifically) while KEEPING its owner +
    # file claims -- resuming re-enters through the same one-in-progress gate. Live receipt
    # 2026-07-16: T075 (explicitly 'PARKED behind T047' in its own text) held the slot for a day
    # and blocked T081's done transition. Prior art: issue-tracker on-hold states.
    #
    # 2026-07-31: PARKED also reachable from CLAIMED and VERIFYING. It was written for work shelved
    # MID-FLIGHT, so IN_PROGRESS was its only door -- but CLAIMED-and-never-started is the state that
    # ACCUMULATES, because claiming is free and releasing is not. Its only exits were ABANDONED
    # (destructive: asserts the intent DIED when it merely DRIFTED) and APPROVED (no --reason, so the
    # rationale is lost). Receipt: 21 ACTIVE / 16 CLAIMED-not-started, unparkable without routing each
    # through the one serialized IN_PROGRESS slot -- 16 FALSE in_progress events in an audited ledger
    # purely to reach a legal state. A ledger you cannot cut honestly is a ledger that grows.
    PARKED:      {IN_PROGRESS, ABANDONED},
}
ACTIVE = {CLAIMED, IN_PROGRESS, VERIFYING}   # occupies the sequential slot / working set
FILE_HOLDING = ACTIVE | {PARKED}             # parked work still owns its files (no mid-park grabs)

#: T248 -- WHERE AN INDEPENDENT REVIEWER IS REQUIRED BEFORE A TASK MAY CLOSE.
#:
#: A prefix match against the task's `files`. Deliberately ONE named constant rather than a
#: predicate buried in the gate: whoever is subject to a threshold should be able to read it
#: without reading the code that enforces it.
#:
#: DANIIL SETS THIS. Measured 2026-08-08: I closed four consecutive slices across core/comm/
#: writing "SELF-VERIFIED by claude" into the verification field, and one fence afterwards
#: found three real defects for $0.09. I am the party being gated, so choosing my own
#: threshold is the T227 defect -- ratifying my own drafts -- one level up.
#:
#: WIDER IS NOT SAFER. Every path added here costs a review on work that may not need one, and
#: a gate that fires on everything is the 5.2%-value recall funnel again: it trains the reader
#: to route around it. Docs and tests are deliberately absent.
LOAD_BEARING = (
    "core/",          # the substrate every seat runs on
    "agent_cli.py",   # the door every agent enters through
    "scripts/hooks/", # fires unbidden in every session; a defect here is silent and global
)


def is_load_bearing(files) -> bool:
    """True when any of `files` sits under a LOAD_BEARING prefix.

    THE LIMIT, STATED HERE BECAUSE IT IS THE ONE THAT MATTERS: this reads the task's DECLARED
    files. It never sees the diff. A task declaring `files=["README.md"]` while editing
    `core/` is not gated, and nothing here can notice. That makes the gate a SPEED BUMP, not a
    wall -- it catches the honest omission, not the determined one, and it is worth having for
    exactly that. A guard believed to be a wall is more dangerous than one known to be a bump.

    The same threat model covers a second bypass a reviewer found and I am not fixing: a
    homoglyph path (`сore/x.py` with a Cyrillic U+0441) fails segment equality and slips
    through. Defeating that means confusable-detection, and NFKC does not even solve it -- a
    large mechanism against an attacker this gate has already conceded, while the honest
    omission it exists to catch is caught. Both limits are here so the next reader inherits the
    threat model rather than rediscovering it.

    Path spelling is normalised because it varied in practice (T250): backslashes, a leading
    './', absolute paths, and non-leading '../' segments all reached this function and three of
    the four escaped a naive prefix test. Matching is done on PATH SEGMENTS, so `core/` matches
    `core/comm/ask.py` and `/srv/repo/core/x.py` but never `core.py`, `mycore/x.py` or
    `score/x.py` -- those non-matches are correct and are pinned so a later widening cannot
    start catching documentation.
    """
    import posixpath

    for f in (files or []):
        p = str(f).replace("\\", "/")
        p = posixpath.normpath(p).lstrip("/")     # resolves ../, strips a leading / or ./
        segs = p.split("/")
        for prefix in LOAD_BEARING:
            pre = prefix.rstrip("/").split("/")
            if prefix.endswith("/"):
                # a directory prefix matches at ANY depth, so an absolute path still counts
                if any(segs[i:i + len(pre)] == pre for i in range(len(segs))):
                    return True
            elif segs and segs[-1] == prefix:     # a bare filename, e.g. agent_cli.py
                return True
    return False


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
            # T248: reviewed_by is WHO (and whether they are the author); verified_by is the
            # EVIDENCE. Collapsed into one field, a sentence describing evidence satisfied a
            # gate about independence -- four times in one day.
            "status": PROPOSED, "commit": None, "verified_by": None,
            "reviewed_by": None, "self_verified": None,
            "created": at, "updated": at,
            "history": [{"to": PROPOSED, "by": by, "at": at}],
        }
        self.tasks[tid] = task
        self.save()
        return task

    def transition(self, tid: str, to: str, *, by: str = "", at: str = "", commit: str = "",
                   verified_by: str = "", owner: str = "", reason: str = "",
                   reviewed_by: str = "", self_verified: str = "") -> Dict[str, Any]:
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

            # T248: verification and INDEPENDENCE are two claims, and one field could only
            # carry one. Measured on the author of this gate: four consecutive load-bearing
            # slices closed with "SELF-VERIFIED by claude" written into `verified_by`, which
            # satisfied the check above because the check only asks whether the field is
            # non-empty. One fence afterwards found three real defects for $0.09.
            #
            # The override exists on purpose. A gate with no exit gets routed around by not
            # using the ledger at all, and an unused ledger is worse than a permissive one --
            # so `self_verified` closes the task and RECORDS why. The count of overrides is
            # the actual instrument; refusing without one is just what keeps that count honest.
            r = (reviewed_by or t.get("reviewed_by") or "").strip()
            sv = (self_verified or "").strip()
            # T250: compare NORMALISED, or " claude" and "Claude" review claude's own work.
            closer = (by or t.get("owner") or "").strip()
            same = bool(r) and bool(closer) and r.casefold() == closer.casefold()
            if is_load_bearing(t.get("files")):
                # A gate about IDENTITY must not run when it cannot establish who is acting.
                # Before T250 an empty closer compared against "", so any reviewer name passed
                # -- a check that reported success without having checked.
                if not closer and not sv:
                    raise LedgerError(
                        f"done blocked: {tid} touches load-bearing paths and the CLOSER is "
                        f"unknown (no --by, no owner), so independence cannot be established. "
                        f"Pass --by <you>, or --self-verified '<why not>'.")
            if is_load_bearing(t.get("files")) and (not r or same):
                if not sv:
                    who = f" (reviewed_by={r!r} is the closer)" if r else ""
                    raise LedgerError(
                        f"done blocked: {tid} touches load-bearing paths "
                        f"{[f for f in (t.get('files') or []) if is_load_bearing([f])]} and has "
                        f"no independent review{who}. Either pass --reviewed-by <someone else>, "
                        f"or --self-verified '<why not>' to close it anyway and be counted. "
                        f"Threshold: task_ledger.LOAD_BEARING.")
                t["self_verified"] = sv
            t["commit"], t["verified_by"] = c, v
            if r:
                t["reviewed_by"] = r
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


TASK_SETTLED_STATUSES = frozenset({"done", "parked", "abandoned"})


def settled_tasks(text: str) -> Tuple[List[str], List[str]]:
    """(settled, live): T-numbers named in `text` whose ledger status contradicts acting
    on them (done/parked/abandoned, rendered 'T075 PARKED') vs those still open. Unknown
    ids read LIVE (fail toward answering/acting). Fail-open ([], []) when the ledger is
    unreachable. Shared by the boot directive cross-check (W04) and the runner's
    premise-gate -- this module's own WHY paragraph, made a callable."""
    import re
    ids = sorted(set(re.findall(r"\bT\d{3}\b", str(text or ""))))
    if not ids:
        return [], []
    try:
        status: Dict[str, str] = {}
        for v in state_view().values():
            if isinstance(v, list):
                for t in v:
                    if isinstance(t, dict) and t.get("id"):
                        status[str(t["id"])] = str(t.get("status", ""))
        settled = [f"{i} {status[i].upper()}" for i in ids
                   if status.get(i, "").lower() in TASK_SETTLED_STATUSES]
        live = [i for i in ids if status.get(i, "").lower() not in TASK_SETTLED_STATUSES]
        return settled, live
    except Exception:
        return [], []


def premise_settled(kind: str, age_ms: Optional[int], text: str, *,
                    min_age_ms: Optional[int] = None) -> List[str]:
    """The premise-gate's pure verdict: the settled list when a short-circuit should
    fire, else []. Fires ONLY when: the kind is an ask, the message is OLDER than the
    age floor (a fresh ask about closed work is deliberate; an old one is a backlog
    echo), it names >=1 T-number, and ALL named tasks are settled. Unknowable age reads
    FRESH; min_age_ms<=0 disables (the P2-style kill switch); ledger errors fail open
    to answering. Env dial: BIFROST_PREMISE_GATE_MIN_AGE_MS (default 2h)."""
    from core.comm import packet_spec
    if min_age_ms is None:
        try:
            min_age_ms = int(os.environ.get("BIFROST_PREMISE_GATE_MIN_AGE_MS",
                                            2 * 3600 * 1000))
        except (TypeError, ValueError):
            min_age_ms = 2 * 3600 * 1000
    if min_age_ms <= 0 or not packet_spec.is_ask_kind(kind):
        return []
    if age_ms is None or age_ms < min_age_ms:
        return []
    settled, live = settled_tasks(text)
    return settled if settled and not live else []


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
        # T248: how many closed WITHOUT independent review. In the view rather than scraped by
        # one renderer, so every surface reads the same number -- two renderers computing the
        # same count is how they come to disagree.
        "self_verified": sum(1 for t in tasks if t.get("self_verified")),
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
        # W15: this header must speak the same one-at-a-time gate as `task next`
        # (conductor.next_task refuses while ANY task is ACTIVE) -- "claimable now"
        # over an occupied slot made the two surfaces contradict each other.
        if v["in_progress"]:
            out.append(f"NEXT (slot occupied by {len(v['in_progress'])} active -- "
                       "claimable when one closes/parks):")
        else:
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
    # T248: the override COUNT is the instrument -- the refusal only keeps it honest. Rendered
    # here rather than behind a flag, because a number you have to go and ask for is a number
    # nobody asks for. Absent at zero: a counter that is always on screen stops being read,
    # which is the same rule the evidence notice follows one subsystem over.
    sv = v.get("self_verified", 0)
    sv_bar = f" | SELF-VERIFIED {sv}" if sv else ""
    out.append(f"(done {c[DONE]} | active {c[CLAIMED] + c[IN_PROGRESS] + c[VERIFYING]} | "
               f"next {len(v['next'])} | {prop} | blocked {c[BLOCKED]}{parked_bar}{sv_bar})")
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
