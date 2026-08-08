"""Conductor — the impure orchestration shell over the pure task ledger (Slice D).

The ledger (task_ledger.py) is pure + deterministic: no clock, injectable Redis client, gates that
reject illegal moves. The conductor adds the real-world I/O the ledger deliberately avoids:
  - stamps real timestamps on every transition (the ledger takes `at` so it stays clock-free/testable),
  - uses the LIVE Redis mirror (client="auto"),
  - emits a RESOLVED marker on the bus when a task closes, so a waking agent sees the closure in the
    message stream too — belt-and-suspenders with read-state-first.

Phase 1 is sequential + human-approved: claude PROPOSES tasks; Daniel APPROVES; the ledger's
one-in-progress gate keeps exactly one task running. `next_task()` names the single claimable task.
Phase 2 (later) relaxes one-in-progress to "any provably-disjoint set" — same gates, no rewrite here.

CLI:
  py core/coord/conductor.py propose "title" [--owner O] [--deps T001,T002] [--files a.py,b.py] [--acc "..."]
  py core/coord/conductor.py approve  T001                     # Daniel's gate
  py core/coord/conductor.py claim    T001 --by claude
  py core/coord/conductor.py start    T001
  py core/coord/conductor.py verify   T001
  py core/coord/conductor.py done     T001 --commit abc123 --verified-by pytest   # emits RESOLVED
  py core/coord/conductor.py block    T001 --reason "..."
  py core/coord/conductor.py list                             # the read-state-first view
  py core/coord/conductor.py next                             # the single claimable task, or none
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone

from core.coord import task_ledger as TL   # import as a module (py -m core.coord.conductor) -- no sys.path hack


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ledger(client="auto", path=None) -> TL.TaskLedger:
    return TL.TaskLedger(path or TL.LEDGER_PATH, client=client)


def _broadcast(kind: str, text: str, meta: dict) -> None:
    """One patchable bus-exit for conductor announcements. Best-effort; the ledger is the
    real authority, so a bus failure never blocks a transition (tests monkeypatch THIS)."""
    from core.comm.bus import Bus
    Bus("conductor").broadcast(kind, text, meta=meta)


def _emit_resolved(tid: str, title: str, commit: str) -> None:
    """Announce a closure on the bus so waking agents see it in-stream too. Best-effort; the ledger
    is the real authority, so a bus failure never blocks the close."""
    try:
        _broadcast(
            "resolved", f"RESOLVED {tid}: {title} @ {commit} -- CLOSED, do not redo.",
            meta={"via": "conductor", "hops": 0, "task": tid, "commit": commit, "display_only": True})
    except Exception:
        pass


def _emit_ledger_update(task: dict, to_status: str, by: str = "") -> None:
    """P3 (T023): EVERY transition rings the doorbell -- kind=ledger_update, folded hint-style
    by runners (never answered, never a wake) so a live agent's ledger view stops being frozen
    at its onboarding. The bus stays ephemeral; the ledger file remains the only truth. The
    conductor's own resolved marker stays for done (existing consumers), this adds the rest.
    Hint shape per the fold spec (deepseek-p3-fold-spec): TASK from->to: title (owner) -- the
    from-state is load-bearing (a claim, a gate pass and a completion demand different
    reactions); it comes free from the transition history the ledger already stamped."""
    try:
        tid, title = task["id"], task.get("title", "")
        hist = task.get("history") or []
        frm = hist[-2]["to"] if len(hist) >= 2 else "new"
        _broadcast(
            "ledger_update",
            f"LEDGER {tid} {frm}->{to_status}: {title[:120]}" + (f"  ({by})" if by else ""),
            meta={"via": "conductor", "hops": 0, "task": tid, "frm_status": frm,
                  "to": to_status, "display_only": True})
    except Exception:
        pass


# --- the propose/approve/claim/... verbs (each stamps time; done emits the marker) -------------
# path/client default to production (the real git ledger + live Redis); tests pass a tmp path + None.
def propose(title, *, owner="", deps=None, files=None, acceptance="", by="claude", client="auto", path=None):
    t = _ledger(client, path).propose(title, owner=owner, deps=deps, files=files,
                                      acceptance=acceptance, by=by, at=_now())
    _emit_ledger_update(t, "proposed", by)
    return t


def approve(tid, *, by="user", client="auto", path=None):
    t = TL.approve(_ledger(client, path), tid, by=by, at=_now())
    _emit_ledger_update(t, "approved", by)
    return t


def claim(tid, by, *, client="auto", path=None):
    t = TL.claim(_ledger(client, path), tid, by, by=by, at=_now())
    _emit_ledger_update(t, "claimed", by)
    return t


def start(tid, *, by="", client="auto", path=None):
    t = TL.start(_ledger(client, path), tid, by=by, at=_now())
    _emit_ledger_update(t, "in_progress", by)
    return t


def verify(tid, *, by="", client="auto", path=None):
    t = TL.verifying(_ledger(client, path), tid, by=by, at=_now())
    _emit_ledger_update(t, "verifying", by)
    return t


def done(tid, commit, verified_by, *, by="", client="auto", path=None,
         reviewed_by="", self_verified=""):
    # T248: reviewed_by is WHO, verified_by is the EVIDENCE, self_verified is a recorded
    # override. Threaded through rather than defaulted here -- agent_cli surfaces THIS parser,
    # so a default set at one door would be the only door that had it.
    t = TL.done(_ledger(client, path), tid, commit=commit, verified_by=verified_by, by=by,
                at=_now(), reviewed_by=reviewed_by, self_verified=self_verified)
    _emit_resolved(tid, t["title"], commit)
    _emit_ledger_update(t, "done", by)
    return t


def block(tid, reason, *, by="", client="auto", path=None):
    t = TL.block(_ledger(client, path), tid, reason, by=by, at=_now())
    _emit_ledger_update(t, "blocked", by)
    return t


def abandon(tid, reason, *, by="", client="auto", path=None):
    """P5 (T025): the explicit verdict for parked intent -- terminal, with a recorded reason
    (a proposal that decays without one is exactly the ambiguity the decay flag exists to end)."""
    t = TL.abandon(_ledger(client, path), tid, reason, by=by, at=_now())
    _emit_ledger_update(t, "abandoned", by)
    return t


def park(tid, reason, *, by="", client="auto", path=None):
    """T083-C5-1: shelve an IN_PROGRESS wave deliberately -- keeps owner + file claims, FREES the
    Phase-1 sequential slot (a parked wave must not block unrelated work from finishing)."""
    t = TL.park(_ledger(client, path), tid, reason, by=by, at=_now())
    _emit_ledger_update(t, "parked", by)
    return t


def unpark(tid, *, by="", client="auto", path=None):
    """T083-C5-1: resume a parked wave -- re-enters through the same one-in-progress gate."""
    t = TL.unpark(_ledger(client, path), tid, by=by, at=_now())
    _emit_ledger_update(t, "in_progress", by)
    return t


def next_task(client="auto", path=None):
    """The single task that may start now: none while anything is ACTIVE (claimed/in_progress/
    verifying all occupy the sequential slot -- TL.ACTIVE law, W15 header contract), else the
    first APPROVED task whose deps are all DONE. Returns a dict or None."""
    v = TL.state_view(path or TL.LEDGER_PATH, client)
    if v["in_progress"]:   # state_view buckets every ACTIVE status here, not just IN_PROGRESS
        return None
    return v["next"][0] if v["next"] else None


# --- CLI ---------------------------------------------------------------------------------------
def _csv(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Conductor for the governed task ledger.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("propose"); p.add_argument("title"); p.add_argument("--owner", default="")
    p.add_argument("--deps", default=""); p.add_argument("--files", default=""); p.add_argument("--acc", default="")
    p.add_argument("--by", default="claude")
    for name in ("approve", "start", "verify"):
        q = sub.add_parser(name); q.add_argument("tid"); q.add_argument("--by", default="")
    q = sub.add_parser("claim"); q.add_argument("tid"); q.add_argument("--by", required=True)
    q = sub.add_parser("done"); q.add_argument("tid"); q.add_argument("--commit", required=True)
    q.add_argument("--verified-by", required=True, dest="verified_by"); q.add_argument("--by", default="")
    # T248. --verified-by is the EVIDENCE; --reviewed-by is WHO, and must not be the closer.
    q.add_argument("--reviewed-by", default="", dest="reviewed_by",
                   help="who INDEPENDENTLY reviewed this (not you). Required for paths in "
                        "task_ledger.LOAD_BEARING unless --self-verified is given.")
    q.add_argument("--self-verified", default="", dest="self_verified",
                   help="close a load-bearing task WITHOUT independent review, recording why. "
                        "Counted, not hidden -- the total shows in the `task list` summary.")
    q = sub.add_parser("block"); q.add_argument("tid"); q.add_argument("--reason", required=True); q.add_argument("--by", default="")
    q = sub.add_parser("abandon"); q.add_argument("tid"); q.add_argument("--reason", required=True); q.add_argument("--by", default="")
    q = sub.add_parser("park"); q.add_argument("tid"); q.add_argument("--reason", required=True); q.add_argument("--by", default="")
    q = sub.add_parser("unpark"); q.add_argument("tid"); q.add_argument("--by", default="")
    sub.add_parser("list"); sub.add_parser("next")
    a = ap.parse_args(argv)

    try:
        if a.cmd == "propose":
            t = propose(a.title, owner=a.owner, deps=_csv(a.deps), files=_csv(a.files),
                        acceptance=a.acc, by=a.by)
            print(f"proposed {t['id']}: {t['title']}")
        elif a.cmd == "approve":
            print(f"approved {approve(a.tid, by=a.by or 'user')['id']}")
        elif a.cmd == "claim":
            print(f"claimed {claim(a.tid, a.by)['id']} by {a.by}")
        elif a.cmd == "start":
            print(f"started {start(a.tid, by=a.by)['id']} (now IN_PROGRESS)")
        elif a.cmd == "verify":
            print(f"verifying {verify(a.tid, by=a.by)['id']}")
        elif a.cmd == "done":
            t = done(a.tid, a.commit, a.verified_by, by=a.by,
                     reviewed_by=a.reviewed_by, self_verified=a.self_verified)
            print(f"DONE {t['id']} @ {a.commit} -- RESOLVED marker emitted")
        elif a.cmd == "block":
            print(f"blocked {block(a.tid, a.reason, by=a.by)['id']}: {a.reason}")
        elif a.cmd == "abandon":
            print(f"ABANDONED {abandon(a.tid, a.reason, by=a.by)['id']}: {a.reason}")
        elif a.cmd == "park":
            print(f"PARKED {park(a.tid, a.reason, by=a.by)['id']} (slot freed; unpark to resume): {a.reason}")
        elif a.cmd == "unpark":
            print(f"UNPARKED {unpark(a.tid, by=a.by)['id']} (now IN_PROGRESS)")
        elif a.cmd == "list":
            import time
            print(TL.format_state(now=time.time()))
        elif a.cmd == "next":
            n = next_task()
            print(f"NEXT: {n['id']} - {n['title']}" if n else
                  "NEXT: none (a task is already in progress, or nothing is claimable)")
    except TL.LedgerError as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
