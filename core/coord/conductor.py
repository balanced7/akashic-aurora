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


def _emit_resolved(tid: str, title: str, commit: str) -> None:
    """Announce a closure on the bus so waking agents see it in-stream too. Best-effort; the ledger
    is the real authority, so a bus failure never blocks the close."""
    try:
        from core.comm.bus import Bus
        Bus("conductor").broadcast(
            "resolved", f"RESOLVED {tid}: {title} @ {commit} -- CLOSED, do not redo.",
            meta={"via": "conductor", "hops": 0, "task": tid, "commit": commit, "display_only": True})
    except Exception:
        pass


# --- the propose/approve/claim/... verbs (each stamps time; done emits the marker) -------------
# path/client default to production (the real git ledger + live Redis); tests pass a tmp path + None.
def propose(title, *, owner="", deps=None, files=None, acceptance="", by="claude", client="auto", path=None):
    return _ledger(client, path).propose(title, owner=owner, deps=deps, files=files,
                                         acceptance=acceptance, by=by, at=_now())


def approve(tid, *, by="user", client="auto", path=None):
    return TL.approve(_ledger(client, path), tid, by=by, at=_now())


def claim(tid, by, *, client="auto", path=None):
    return TL.claim(_ledger(client, path), tid, by, by=by, at=_now())


def start(tid, *, by="", client="auto", path=None):
    return TL.start(_ledger(client, path), tid, by=by, at=_now())


def verify(tid, *, by="", client="auto", path=None):
    return TL.verifying(_ledger(client, path), tid, by=by, at=_now())


def done(tid, commit, verified_by, *, by="", client="auto", path=None):
    t = TL.done(_ledger(client, path), tid, commit=commit, verified_by=verified_by, by=by, at=_now())
    _emit_resolved(tid, t["title"], commit)
    return t


def block(tid, reason, *, by="", client="auto", path=None):
    return TL.block(_ledger(client, path), tid, reason, by=by, at=_now())


def next_task(client="auto", path=None):
    """The single task that may start now: none if something is already IN_PROGRESS (Phase 1's
    one-at-a-time gate), else the first APPROVED task whose deps are all DONE. Returns a dict or None."""
    v = TL.state_view(path or TL.LEDGER_PATH, client)
    if any(t["status"] == TL.IN_PROGRESS for t in v["in_progress"]):
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
    q = sub.add_parser("block"); q.add_argument("tid"); q.add_argument("--reason", required=True); q.add_argument("--by", default="")
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
            t = done(a.tid, a.commit, a.verified_by, by=a.by)
            print(f"DONE {t['id']} @ {a.commit} -- RESOLVED marker emitted")
        elif a.cmd == "block":
            print(f"blocked {block(a.tid, a.reason, by=a.by)['id']}: {a.reason}")
        elif a.cmd == "list":
            print(TL.format_state())
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
