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

import contextlib
import sys
import time
from datetime import UTC, datetime
from typing import cast

from core.coord import task_ledger as TL  # import as a module (py -m core.coord.conductor) -- no sys.path hack


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _ledger(client="auto", path=None) -> TL.TaskLedger:
    # T352: pass None THROUGH -- TaskLedger's own default chain is path -> AKASHIC_TASKS_PATH
    # (the test-isolation redirect) -> LEDGER_PATH. Forcing the constant here re-imposed the
    # production path over isolated drills and was the last leak in the 32-phantom-row class.
    return TL.TaskLedger(path, client=client)


#: 77e485bb23: how many times a verb loads the ledger fresh and re-applies after save() refuses
#: because a PEER wrote between our load and our save (TL.LedgerConflict). Every attempt re-runs
#: every gate against the file as it now stands, so a retry can only land a move that is legal
#: on the truth -- or turn into a gate refusal, which is an answer and is never retried.
#: Bounded on purpose: a ledger too hot to land on surfaces as the last refusal, not a spin.
LOST_UPDATE_ATTEMPTS = 4


def _apply(op, client="auto", path=None):
    """Run `op(ledger)` against a FRESHLY loaded ledger; on a lost-update refusal, re-read and
    re-apply. This is the door's half of the ledger's CAS (task_ledger.save refuses to clobber
    a peer's write and re-reads the truth; the door re-decides on top of it). Split on purpose:
    the ledger stays pure (no sleeping, no policy) and the policy every `task` verb shares
    lives once, here -- T271's 'detected and retried', at the one door the verbs enter by."""
    last = None
    for attempt in range(LOST_UPDATE_ATTEMPTS):
        try:
            return op(_ledger(client, path))
        except TL.LedgerConflict as e:
            last = e
            time.sleep(0.02 * (attempt + 1))  # let the peer's mirror/announce land first
    raise cast("TL.LedgerConflict", last)  # ty: ignore[redundant-cast]  # LOST_UPDATE_ATTEMPTS >= 1, so a conflict set it


def _broadcast(kind: str, text: str, meta: dict) -> None:
    """One patchable bus-exit for conductor announcements. Best-effort; the ledger is the
    real authority, so a bus failure never blocks a transition (tests monkeypatch THIS)."""
    from core.comm.bus import Bus

    Bus("conductor").broadcast(kind, text, meta=meta)


def _emit_resolved(tid: str, title: str, commit: str) -> None:
    """Announce a closure on the bus so waking agents see it in-stream too. Best-effort; the ledger
    is the real authority, so a bus failure never blocks the close."""
    with contextlib.suppress(Exception):
        _broadcast(
            "resolved",
            f"RESOLVED {tid}: {title} @ {commit} -- CLOSED, do not redo.",
            meta={"via": "conductor", "hops": 0, "task": tid, "commit": commit, "display_only": True},
        )


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
            meta={"via": "conductor", "hops": 0, "task": tid, "frm_status": frm, "to": to_status, "display_only": True},
        )
    except Exception:
        pass


# --- the propose/approve/claim/... verbs (each stamps time; done emits the marker) -------------
# path/client default to production (the real git ledger + live Redis); tests pass a tmp path + None.
def propose(title, *, owner="", deps=None, files=None, acceptance="", by="claude", client="auto", path=None):
    t = _apply(
        lambda led: led.propose(title, owner=owner, deps=deps, files=files, acceptance=acceptance, by=by, at=_now()),
        client,
        path,
    )
    _emit_ledger_update(t, "proposed", by)
    return t


def approve(tid, *, by="user", client="auto", path=None):
    t = _apply(lambda led: TL.approve(led, tid, by=by, at=_now()), client, path)
    _emit_ledger_update(t, "approved", by)
    return t


def claim(tid, by, *, client="auto", path=None):
    t = _apply(lambda led: TL.claim(led, tid, by, by=by, at=_now()), client, path)
    _emit_ledger_update(t, "claimed", by)
    return t


def start(tid, *, by="", client="auto", path=None, pauses="", operator_ruling=""):
    # Ruling 369243: a THIRD watch opens only with pauses=<what stops> or the operator's
    # recorded word. Threaded through rather than defaulted here -- agent_cli surfaces THIS
    # parser (same law as done()'s reviewed_by threading).
    t = _apply(
        lambda led: TL.start(led, tid, by=by, at=_now(), pauses=pauses, operator_ruling=operator_ruling), client, path
    )
    _emit_ledger_update(t, "in_progress", by)
    return t


def verify(tid, *, by="", client="auto", path=None):
    t = _apply(lambda led: TL.verifying(led, tid, by=by, at=_now()), client, path)
    _emit_ledger_update(t, "verifying", by)
    return t


def done(tid, commit, verified_by, *, by="", client="auto", path=None, reviewed_by="", self_verified=""):
    # T248: reviewed_by is WHO, verified_by is the EVIDENCE, self_verified is a recorded
    # override. Threaded through rather than defaulted here -- agent_cli surfaces THIS parser,
    # so a default set at one door would be the only door that had it.
    t = _apply(
        lambda led: TL.done(
            led,
            tid,
            commit=commit,
            verified_by=verified_by,
            by=by,
            at=_now(),
            reviewed_by=reviewed_by,
            self_verified=self_verified,
        ),
        client,
        path,
    )
    _emit_resolved(tid, t["title"], commit)
    _emit_ledger_update(t, "done", by)
    return t


def block(tid, reason, *, by="", client="auto", path=None):
    t = _apply(lambda led: TL.block(led, tid, reason, by=by, at=_now()), client, path)
    _emit_ledger_update(t, "blocked", by)
    return t


def abandon(tid, reason, *, by="", client="auto", path=None, operator_ruling=""):
    """P5 (T025): the explicit verdict for parked intent -- terminal, with a recorded reason
    (a proposal that decays without one is exactly the ambiguity the decay flag exists to end).
    T352: abandoning a DONE row additionally requires operator_ruling (recorded in history)."""
    t = _apply(
        lambda led: TL.abandon(led, tid, reason, by=by, at=_now(), operator_ruling=operator_ruling), client, path
    )
    _emit_ledger_update(t, "abandoned", by)
    return t


def park(tid, reason, *, by="", client="auto", path=None):
    """T083-C5-1: shelve an IN_PROGRESS wave deliberately -- keeps owner + file claims, FREES the
    Phase-1 sequential slot (a parked wave must not block unrelated work from finishing)."""
    t = _apply(lambda led: TL.park(led, tid, reason, by=by, at=_now()), client, path)
    _emit_ledger_update(t, "parked", by)
    return t


def unpark(tid, *, by="", client="auto", path=None, pauses="", operator_ruling=""):
    """T083-C5-1: resume a parked wave -- re-enters through the same two-watch gate."""
    t = _apply(
        lambda led: TL.unpark(led, tid, by=by, at=_now(), pauses=pauses, operator_ruling=operator_ruling), client, path
    )
    _emit_ledger_update(t, "in_progress", by)
    return t


def next_task(client="auto", path=None):
    """The single task that may start now: none while anything is ACTIVE (claimed/in_progress/
    verifying all occupy the sequential slot -- TL.ACTIVE law, W15 header contract), else the
    first APPROVED task whose deps are all DONE. Returns a dict or None."""
    v = TL.state_view(path or TL.LEDGER_PATH, client)
    if v["in_progress"]:  # state_view buckets every ACTIVE status here, not just IN_PROGRESS
        return None
    return v["next"][0] if v["next"] else None


# --- CLI ---------------------------------------------------------------------------------------
def _csv(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def main(argv=None) -> int:
    from core.axi.cli import AxiArgumentParser

    # The AXI parser: a usage error is reported on stdout with this subcommand's flags, which is
    # where an agent reads. `agent_cli.py task` names it as the door agents call it by.
    ap = AxiArgumentParser(prog="agent_cli.py task", description="Conductor for the governed task ledger.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("propose")
    p.add_argument("title")
    p.add_argument("--owner", default="")
    p.add_argument("--deps", default="")
    p.add_argument("--files", default="")
    p.add_argument("--acc", default="")
    p.add_argument("--by", default="claude")
    for name in ("approve", "verify"):
        q = sub.add_parser(name)
        q.add_argument("tid")
        q.add_argument("--by", default="")
    q = sub.add_parser("start")
    q.add_argument("tid")
    q.add_argument("--by", default="")
    q.add_argument("--pauses", default="", help="ruling 369243: a THIRD open watch requires naming what stops")
    q.add_argument(
        "--operator-ruling",
        default="",
        dest="operator_ruling",
        help="the operator's recorded word -- the cap never refuses him",
    )
    q = sub.add_parser("claim")
    q.add_argument("tid")
    q.add_argument("--by", required=True)
    q = sub.add_parser("done")
    q.add_argument("tid")
    q.add_argument("--commit", required=True)
    q.add_argument("--verified-by", required=True, dest="verified_by")
    q.add_argument("--by", default="")
    # T248. --verified-by is the EVIDENCE; --reviewed-by is WHO, and must not be the closer.
    q.add_argument(
        "--reviewed-by",
        default="",
        dest="reviewed_by",
        help="who INDEPENDENTLY reviewed this (not you). Required for paths in "
        "task_ledger.LOAD_BEARING unless --self-verified is given.",
    )
    q.add_argument(
        "--self-verified",
        default="",
        dest="self_verified",
        help="close a load-bearing task WITHOUT independent review, recording why. "
        "Counted, not hidden -- the total shows in the `task list` summary.",
    )
    q = sub.add_parser("block")
    q.add_argument("tid")
    q.add_argument("--reason", required=True)
    q.add_argument("--by", default="")
    q = sub.add_parser("abandon")
    q.add_argument("tid")
    q.add_argument("--reason", required=True)
    q.add_argument("--by", default="")
    q.add_argument(
        "--operator-ruling",
        default="",
        dest="operator_ruling",
        help="T352: required to abandon a DONE row -- the operator's words, recorded in history",
    )
    q = sub.add_parser("park")
    q.add_argument("tid")
    q.add_argument("--reason", required=True)
    q.add_argument("--by", default="")
    q = sub.add_parser("unpark")
    q.add_argument("tid")
    q.add_argument("--by", default="")
    q.add_argument("--pauses", default="", help="ruling 369243: resuming as a THIRD watch requires naming what stops")
    q.add_argument(
        "--operator-ruling",
        default="",
        dest="operator_ruling",
        help="the operator's recorded word -- the cap never refuses him",
    )
    q = sub.add_parser("list")
    q.add_argument("--limit", type=int, default=10, help="how many of the most recent DONE tasks to list (default 10)")
    sub.add_parser("next")
    from core.axi import out
    from core.axi.cli import cli_name, parse

    a = parse(
        ap, sys.argv[1:] if argv is None else list(argv)
    )  # an unknown flag is reported by the subcommand it was given to
    task = f"{cli_name()} task"
    # The read side honours the same isolation door the writes do (T352). TaskLedger resolves
    # AKASHIC_TASKS_PATH, but state_view and next_task default to LEDGER_PATH, so with the Redis
    # mirror empty an isolated `list` read the checkout's ledger file while its writes went to
    # the sandbox. Unset, this is LEDGER_PATH exactly as before.
    import os

    read_path = os.environ.get("AKASHIC_TASKS_PATH") or TL.LEDGER_PATH
    try:
        if a.cmd == "list":
            return _emit_list(task, limit=a.limit, path=read_path)
        if a.cmd == "next":
            n = next_task(path=read_path)
            if not n:
                return out.emit(
                    {"next": "none", "why": "a task is already active, or no approved task has its deps done"},
                    hints=[f"{task} list"],
                    title="Next task",
                )
            return out.emit(
                {"next": n["id"], "title": n["title"]},
                hints=[f"{task} claim {n['id']} --by <agent_id>"],
                title="Next task",
            )
        # One row per mutation: the task, the status it moved to, and what the move recorded.
        # The next-step hint is the lifecycle's next verb on the same task.
        if a.cmd == "propose":
            t = propose(a.title, owner=a.owner, deps=_csv(a.deps), files=_csv(a.files), acceptance=a.acc, by=a.by)
            extra, nxt = {}, f"{task} approve {t['id']}"
        elif a.cmd == "approve":
            t = approve(a.tid, by=a.by or "user")
            extra, nxt = {}, f"{task} claim {t['id']} --by <agent_id>"
        elif a.cmd == "claim":
            t = claim(a.tid, a.by)
            extra, nxt = {"owner": a.by}, f"{task} start {t['id']} --by {a.by}"
        elif a.cmd == "start":
            t = start(a.tid, by=a.by, pauses=a.pauses, operator_ruling=a.operator_ruling)
            extra, nxt = ({"pauses": a.pauses} if a.pauses else {}), f"{task} verify {t['id']}"
        elif a.cmd == "verify":
            t = verify(a.tid, by=a.by)
            extra, nxt = {}, f'{task} done {t["id"]} --commit <sha> --verified-by "<evidence>"'
        elif a.cmd == "done":
            t = done(a.tid, a.commit, a.verified_by, by=a.by, reviewed_by=a.reviewed_by, self_verified=a.self_verified)
            extra, nxt = {"commit": a.commit, "resolved_marker": "emitted"}, f"{task} next"
        elif a.cmd == "block":
            t = block(a.tid, a.reason, by=a.by)
            extra, nxt = {"reason": a.reason}, f"{task} list"
        elif a.cmd == "abandon":
            t = abandon(a.tid, a.reason, by=a.by, operator_ruling=a.operator_ruling)
            extra, nxt = {"reason": a.reason}, f"{task} list"
        elif a.cmd == "park":
            t = park(a.tid, a.reason, by=a.by)
            extra, nxt = {"reason": a.reason, "slot": "freed"}, f"{task} unpark {t['id']}"
        else:  # unpark
            t = unpark(a.tid, by=a.by, pauses=a.pauses, operator_ruling=a.operator_ruling)
            extra, nxt = {}, f"{task} verify {t['id']}"
        doc = {"task": t["id"], "status": t.get("status"), "title": out.truncate(t.get("title"), 200)[0], **extra}
        return out.emit(doc, hints=[nxt], title=f"Task {t['id']} · {t.get('status')}")
    except TL.LedgerError as e:
        # The ledger's refusal is the answer (a gate said no); exit 1 as before. Agent mode puts
        # it on stdout, where an agent reads; a person still gets it on stderr.
        return out.fail(str(e), code="REFUSED", hints=[f"{task} list"])


def _emit_list(task: str, *, limit: int = 10, path: str = TL.LEDGER_PATH) -> int:
    """`task list` as data: counts first, then the rows an agent acts on (active, next, parked,
    stale proposals) and the most recent DONE rows -- the full DONE history is hundreds of rows
    nobody acts on, so it is cut to `limit` with the total said. The text block boot prints
    (task_ledger.format_state) is untouched; this is the door's own rendering of the same view."""
    import os

    from core.axi import out

    stale_days = TL.STALE_PROPOSED_DAYS
    with contextlib.suppress(ValueError, TypeError):
        stale_days = int(os.environ.get("AKASHIC_PROPOSED_STALE_DAYS", stale_days))
    v = TL.state_view(path, now=time.time(), stale_days=stale_days)
    c = v["counts"]
    total = sum(c.values())
    if not total:
        return out.emit(
            {"total": 0, "tasks": "no governed tasks yet; nothing to redo or claim"},
            hints=[f'{task} propose "<title>" --by <agent_id>'],
            title="Task ledger",
        )
    stale = [t for t in v["proposed"] if t.get("stale")]
    doc: dict = {
        "total": total,
        "done": c[TL.DONE],
        "active": len(v["in_progress"]),
        "next": len(v["next"]),
        "proposed": c[TL.PROPOSED],
        "blocked": c[TL.BLOCKED],
    }
    if c.get(TL.PARKED):
        doc["parked"] = c[TL.PARKED]
    if stale:
        doc["stale_proposed"] = len(stale)
    if v.get("self_verified"):
        doc["self_verified"] = v["self_verified"]  # T248: absent at zero, like the old bar

    def row(t, *keys):
        return {"id": t["id"], "title": out.truncate(t["title"], 90)[0], **{k: t.get(k) or None for k in keys}}

    if v["in_progress"]:
        doc["active_tasks"] = [row(t, "status", "owner") for t in v["in_progress"]]
    if v["next"]:
        # W15: while any task is active the slot is occupied and `task next` says none; the rows
        # say so too instead of reading as claimable now.
        doc["next_claimable"] = "when the active task closes or parks" if v["in_progress"] else "now"
        doc["next_tasks"] = [row(t, "owner") for t in v["next"]]
    if v.get("parked"):
        doc["parked_tasks"] = [{**row(t), "reason": out.truncate(t.get("reason"), 80)[0] or None} for t in v["parked"]]
    if stale:
        doc["stale_proposals"] = [
            {**row(t), "age_days": round(t.get("age_days") or 0)} for t in stale
        ]  # re-approve or abandon: parked intent, not live
    if v["done"]:
        recent = v["done"][-max(0, limit) :] if limit else []
        doc["done_recent"] = [{**row(t), "commit": (t.get("commit") or "")[:8] or None} for t in reversed(recent)]
    doc["rule"] = "DONE is closed: never redo it; work only your assigned or NEXT task"
    hints = []
    if v["next"] and not v["in_progress"]:
        hints.append(f"{task} claim {v['next'][0]['id']} --by <agent_id>")
    if c[TL.DONE] > limit:
        hints.append(f"{task} list --limit {c[TL.DONE]}")
    return out.emit(doc, hints=hints, human=_human_list, title="Task ledger")


def _human_list(console, doc) -> None:
    """Human view of `task list`: the counts on one line, then one table per bucket an agent or
    person acts on, the DONE rule last."""
    from core.axi import out

    counts = ("done", "active", "next", "proposed", "blocked", "parked", "stale_proposed", "self_verified")
    bar = " · ".join(f"[bold]{doc[k]}[/] {k.replace('_', ' ')}" for k in counts if k in doc)
    console.print(f"{doc['total']} task{'s' if doc['total'] != 1 else ''} · {bar}")
    for key, label in (
        ("active_tasks", "Active"),
        ("next_tasks", f"Next (claimable {doc.get('next_claimable', 'now')})"),
        ("parked_tasks", "Parked"),
        ("stale_proposals", "Stale proposals (re-approve or abandon)"),
        ("done_recent", "Recently done"),
    ):
        if doc.get(key):
            console.print(out.table(doc[key], title=label))
    console.print(f"[dim]{out._esc(doc['rule'])}[/]")


if __name__ == "__main__":
    sys.exit(main())
