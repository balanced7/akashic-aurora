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

# --- lifecycle ---------------------------------------------------------------------------------
PROPOSED, APPROVED, CLAIMED, IN_PROGRESS, VERIFYING, DONE, BLOCKED, ABANDONED = (
    "proposed", "approved", "claimed", "in_progress", "verifying", "done", "blocked", "abandoned")

STATUSES = (PROPOSED, APPROVED, CLAIMED, IN_PROGRESS, VERIFYING, DONE, BLOCKED, ABANDONED)

# who may move where. DONE/ABANDONED are terminal (empty set).
TRANSITIONS: Dict[str, set] = {
    PROPOSED:    {APPROVED, ABANDONED},
    APPROVED:    {CLAIMED, ABANDONED},
    CLAIMED:     {IN_PROGRESS, APPROVED, ABANDONED},   # release back to APPROVED if you can't do it
    IN_PROGRESS: {VERIFYING, BLOCKED, ABANDONED},
    VERIFYING:   {DONE, IN_PROGRESS, BLOCKED},         # verification can bounce it back
    BLOCKED:     {APPROVED, IN_PROGRESS, ABANDONED},
    DONE:        set(),
    ABANDONED:   set(),
}
ACTIVE = {CLAIMED, IN_PROGRESS, VERIFYING}   # holds files / occupies the sequential slot


class LedgerError(Exception):
    """A rejected transition. The message names the gate that blocked it (teaches the fix)."""


class TaskLedger:
    def __init__(self, path: str = LEDGER_PATH):
        self.path = path
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._seq = 0
        self.load()

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
        """path -> task_id for every file an ACTIVE task holds (exclude one task if given)."""
        held: Dict[str, str] = {}
        for t in self.tasks.values():
            if t["id"] == exclude or t["status"] not in ACTIVE:
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
