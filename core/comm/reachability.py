"""reachability -- one screen answering "is this seat reachable, and by which path?" (READ-ONLY).

Filed from the 2026-10-30 wish in docs/WISHLIST.md (phase 3 of the modular-core detangle):
answering this question took about ten commands across two worktrees. The two worktrees are the
point: the production Discord gateway does NOT run from the checkout a seat is standing in, so
"where is its log" is a different question from "is its service row up", and a seat that assumes
the main checkout reads a stale file and concludes the wrong thing.

WHAT IT ANSWERS, in the order a stranded seat needs them:

  1. THE GATEWAY -- the process row (pid, start time, age) AND the path of its REAL log, taken
     from the process's own working directory rather than from this checkout. A gateway that is
     up while its log sits in another worktree is exactly the case that wastes an hour.
  2. THIS SEAT'S WAKE LISTENER -- every armed seat file for the agent id, with pid, age, launch
     origin (harness / daemon / unknown), and whether that pid is still alive.
  3. THE CONSUMER SEAT -- who holds it for this agent id (RB-21). One session consumes per
     agent id; if a twin holds it, this seat's reads degrade to peek and the screen says so.
  4. OPERATOR MAIL -- the last inbound message from the operator and the last outbound reply TO
     the operator, each with its bus id and timestamp. This is the question "did the operator's
     message actually reach me, and did my answer actually leave" answered from the streams
     rather than from a transcript.
  5. THE PHONE TUNNEL -- the PhoneLink watcher's `ssh -R` forward (if any) and whether the
     phone answers on the tailnet. A tunnel that was never opened and a tunnel whose far end is
     asleep look identical from inside a seat, so both halves are measured.

WHERE THE INSTANCE VALUES COME FROM, and why they are not constants here: which scripts are
gateway markers, where the gateway's log lands relative to its worktree, and the phone's tailnet
address and ports are the LOCAL layer's facts (`local/reachability.json`, read through
`core.local`). Naming them in Core is what the purity ratchet refuses, and rightly -- a fork must
be able to take this module without being told who we are. Missing Local data is reported as
UNKNOWN per rung, never collapsed into a default.

HARD RULES, because this is a diagnostic a stranded seat runs:

  * Nothing here consumes a cursor, sends mail, arms a listener or starts a process. Every read
    is XREVRANGE / a filesystem stat / a short TCP connect. Running `reachability` twice must
    never change what the second run sees (pin: tests/test_reachability.py).
  * Every rung reports UP / DOWN / UNKNOWN. UNKNOWN is the honest answer when the probe itself
    could not run (psutil missing, Redis unreachable, Local data absent, a file unreadable) and
    it is never collapsed into DOWN -- a diagnostic that answers "no tunnel" when it simply
    could not look is worse than no diagnostic, because it sends the reader hunting a fault that
    may not exist.
  * Fail-soft throughout: this verb's whole job is to run when things are broken, so it must
    not raise when the bus, Redis, psutil or the filesystem are the broken thing.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import time
from typing import Any, Dict, List, Optional

UP = "UP"
DOWN = "DOWN"
UNKNOWN = "UNKNOWN"

#: The Local data file this module asks for its instance values. See local/reachability.json.
LOCAL_FILE = "reachability"

#: How far back to scan a stream looking for the operator's last message. Generous because a
#: quiet hour of agent-to-agent traffic can bury it; bounded because this is a screen, not a log.
SCAN_LIMIT = 300

#: Never spend more than this on the phone probe: the verb has to be usable while a seat is
#: stranded, and a black-holed tailnet route is a 20-second SYN timeout by default.
PHONE_CONNECT_TIMEOUT_S = 1.5


# ------------------------------------------------------------------------- the Local layer
def local_data() -> Dict[str, Any]:
    """`local/reachability.json`, or {} with no exception. A MISSING file is not a value: every
    rung that needs it reports UNKNOWN and says the file is missing (see rung_missing_local)."""
    try:
        from core import local
        return local.optional(LOCAL_FILE) or {}
    except Exception:
        return {}


def _local_section(name: str) -> Dict[str, Any]:
    sect = local_data().get(name)
    return sect if isinstance(sect, dict) else {}


def _local_missing(what: str, name: str) -> str:
    return (f"the Local layer carries no {what} to measure (local/{name}.json is absent or has "
            f"no {what!r} section) -- UNKNOWN, not 'down'")


def operator_ids() -> frozenset:
    raw = os.environ.get("AKASHIC_OPERATOR_IDS")
    if raw is None:
        raw = ",".join(_local_section("operator_ids").get("values") or [])
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


def _age(ts: float, now: Optional[float] = None) -> float:
    return max(0.0, (now if now is not None else time.time()) - ts)


def fmt_age(seconds: Optional[float]) -> str:
    if seconds is None:
        return "age unknown"
    s = int(seconds)
    if s < 90:
        return f"{s}s"
    if s < 5400:
        return f"{s // 60}m"
    if s < 172800:
        return f"{s // 3600}h{(s % 3600) // 60:02d}m"
    return f"{s // 86400}d{(s % 86400) // 3600:02d}h"


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))


def _preview(value: Any, limit: int = 160) -> str:
    if isinstance(value, (dict, list)):
        try:
            value = json.dumps(value, ensure_ascii=False)
        except Exception:
            value = repr(value)
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _psutil():
    """psutil, or None. The one import this module cannot do without for the process rungs --
    and it must degrade to UNKNOWN, never to "no process"."""
    try:
        import psutil  # noqa: F401
        return psutil
    except Exception:
        return None


def _argv(proc) -> List[str]:
    try:
        return list(proc.info.get("cmdline") or [])
    except Exception:
        return []


def _script_arg(argv: List[str], markers: tuple) -> str:
    """The .py script argument matching one of `markers`, or "".

    MATCH THE ARGUMENT, NOT THE WHOLE COMMAND LINE. A bare substring test over the joined
    cmdline is how the first draft of this module reported a gateway that did not exist: a seat
    whose task text contained the words "discord gateway" belongs to no gateway. A process IS a
    gateway when one of its ARGUMENTS is the gateway script; prose inside an argument is not."""
    for arg in argv:
        low = str(arg).lower().replace("\\", "/")
        base = low.rsplit("/", 1)[-1]
        if not base.endswith(".py"):
            continue
        if any(marker in base for marker in markers):
            return str(arg)
    return ""


def _is_ssh_client(argv: List[str]) -> bool:
    """True for an ssh CLIENT process (by executable, not by anything it says)."""
    if not argv:
        return False
    exe = str(argv[0]).lower().replace("\\", "/").rsplit("/", 1)[-1]
    return exe in ("ssh", "ssh.exe")


# --------------------------------------------------------------------------- 1. the gateway
def gateway_markers() -> tuple:
    return tuple(_local_section("gateway").get("script_markers") or ())


def gateway_log_relpath() -> str:
    return str(_local_section("gateway").get("log_relpath") or "")


def _gateway_processes() -> Dict[str, Any]:
    """[{pid, started, age_s, worktree, cmd}] for every live gateway process, or a reason."""
    markers = gateway_markers()
    if not markers:
        return {"state": UNKNOWN, "why": _local_missing("gateway", LOCAL_FILE)}
    ps = _psutil()
    if ps is None:
        return {"state": UNKNOWN, "why": "psutil is not importable, so no process could be "
                                         "inspected (this is NOT a claim that the gateway is down)"}
    found: List[Dict[str, Any]] = []
    try:
        for proc in ps.process_iter(["pid", "cmdline", "create_time"]):
            argv = _argv(proc)
            script = _script_arg(argv, markers)
            if not script:
                continue
            try:
                cwd = proc.cwd()
            except Exception:
                cwd = ""
            found.append({"pid": proc.info.get("pid"),
                          "started": _iso(proc.info.get("create_time") or time.time()),
                          "age_s": _age(proc.info.get("create_time") or time.time()),
                          "worktree": cwd,
                          "script": script,
                          "cmd": " ".join(argv)[:300]})
    except Exception as exc:                                  # pragma: no cover - env dependent
        return {"state": UNKNOWN, "why": f"the process walk failed: {type(exc).__name__}: {exc}"}
    return {"state": UP if found else DOWN, "processes": found}


def _gateway_log(worktree: str) -> Dict[str, Any]:
    """The REAL log: resolved from the gateway's own working directory."""
    if not worktree:
        return {"state": UNKNOWN, "why": "the gateway process did not report a working "
                                         "directory, so its log path cannot be resolved "
                                         "(guessing this checkout's path would be a lie)"}
    rel = gateway_log_relpath()
    if not rel:
        return {"state": UNKNOWN, "why": _local_missing("gateway.log_relpath", LOCAL_FILE)}
    path = os.path.normpath(os.path.join(worktree, rel))
    try:
        st = os.stat(path)
    except Exception:
        return {"state": UNKNOWN, "path": path,
                "why": "no log at that path (the process runs from a worktree whose "
                       "state/logs does not carry one)"}
    tail = ""
    try:
        with open(path, "rb") as fh:
            fh.seek(max(0, st.st_size - 4096))
            chunk = fh.read().decode("utf-8", "replace")
        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        tail = lines[-1][:200] if lines else ""
    except Exception:
        tail = "(unreadable)"
    return {"state": UP, "path": path, "size": st.st_size,
            "mtime": _iso(st.st_mtime), "age_s": _age(st.st_mtime), "tail": tail}


def gateway() -> Dict[str, Any]:
    """The gateway rung: the process row, the worktree it runs from, and its real log."""
    procs = _gateway_processes()
    out: Dict[str, Any] = {"state": procs["state"]}
    if procs["state"] == UNKNOWN:
        out["why"] = procs.get("why", "")
        return out
    rows = procs.get("processes") or []
    if not rows:
        out["why"] = ("no live process runs a gateway marker; the service row is down (a "
                      "gateway started from a launcher this screen cannot see would also "
                      "read DOWN -- the log line below is the cross-check)")
        # Still name where the log WOULD be, resolved from this checkout, marked as such.
        rel = gateway_log_relpath()
        guess = os.path.join(os.getcwd(), rel) if rel else ""
        out["log"] = {"state": UNKNOWN, "path": guess,
                      "why": "no gateway process to resolve the real path from; this is THIS "
                             "checkout's path, not the production one"}
        return out
    rows.sort(key=lambda r: r.get("age_s") or 0)
    first = rows[0]
    out["processes"] = rows
    out["pid"] = first["pid"]
    out["started"] = first["started"]
    out["age_s"] = first["age_s"]
    out["worktree"] = first["worktree"]
    out["log"] = _gateway_log(first.get("worktree") or "")
    return out


# ------------------------------------------------------------------- 2. this seat's listener
def wake_seats(agent: str, session: str = "", tmp: Optional[str] = None) -> Dict[str, Any]:
    """Every armed wake seat for `agent` -- per-session (Wave 2) and the legacy name-keyed one.

    A pid is reported with its liveness; the ORIGIN sidecar decides whether that listener's
    exit can actually start a turn (an `unknown` origin is a watcher nobody hears)."""
    from core.comm import wake_seat
    base = tmp or tempfile.gettempdir()
    ps = _psutil()
    prefix = f"bifrost_wake_{agent}"
    try:
        names = sorted(os.listdir(base))
    except Exception as exc:
        return {"state": UNKNOWN, "why": f"cannot list {base}: {type(exc).__name__}: {exc}"}
    seats: List[Dict[str, Any]] = []
    for name in names:
        if not name.startswith(prefix):
            continue
        if name.endswith(".alive") or name.endswith(".arming") or name.endswith(".reap.log"):
            continue
        if not name.endswith(".pid"):
            continue
        path = os.path.join(base, name)
        pid = None
        try:
            pid = int(open(path).read().strip())
        except Exception:
            pid = None
        sid = ""
        stem = name[len(prefix):-len(".pid")]
        if stem.startswith("_"):
            sid = stem[1:]
        alive: Optional[bool] = None
        if pid is not None and ps is not None:
            try:
                alive = bool(ps.pid_exists(pid))
            except Exception:
                alive = None
        origin = ""
        try:
            origin = str(wake_seat.read_origin(agent, sid or None) or "")
        except Exception:
            origin = ""
        seats.append({"path": path, "session": sid, "pid": pid, "alive": alive,
                      "origin": origin,
                      "age_s": _age(os.path.getmtime(path))})
    if not seats:
        return {"state": DOWN, "seats": [],
                "why": "no wake seat file for this agent -- nothing is listening, so mail "
                       "queues until the next boot or a manual bifrost-sync"}
    mine = [s for s in seats if session and s["session"] == session]
    return {"state": UP, "seats": seats, "this_session": mine[0] if mine else None,
            "listed_for": session or "(any)"}


# ---------------------------------------------------------------------- 3. the consumer seat
def consumer_seat(agent: str) -> Dict[str, Any]:
    """Who holds the RB-21 consumer seat for this agent id -- peek only, never a claim."""
    try:
        from core.comm import runner_lock
    except Exception as exc:
        return {"state": UNKNOWN, "why": f"runner_lock not importable: {exc}"}
    try:
        info = runner_lock.holder(agent)
    except Exception as exc:
        return {"state": UNKNOWN, "why": f"the seat read failed: {type(exc).__name__}: {exc}"}
    if not info:
        return {"state": DOWN, "holder": None,
                "why": "no holder: the seat is free, and the next consumer takes it"}
    return {"state": UP, "holder": info.get("token"), "since": info.get("ts"),
            "ttl_s": getattr(runner_lock, "SESSION_CONSUMER_TTL", None)}


def live_runner(agent: str) -> Dict[str, Any]:
    """Is a live RUNNER (rather than a session) bound to this agent id?

    THE QUESTION A HANDOFF ACTUALLY NEEDS ANSWERED (2026-10-30 wish): a handoff briefing is read
    by the target's next `boot`, and a RUNNER does not reboot -- it holds the runner lock and
    works the lane until it is drained or displaced. So a handoff addressed to a seat whose work
    is done by a runner can sit unread for hours while the sender believes it landed. This
    function is the fact that makes that visible, and it is the ONE definition both `reachability`
    and the handoff warning read (two implementations would disagree at the worst moment).

    Three rungs, in the order that makes an answer honest:
      * the runner LOCK (`runner_lock.holder`) -- the authoritative "a runner is bound here";
      * the daemon's published runtimes card (`incarnation.daemon_runtimes`) -- a second,
        independent witness, because a lock can outlive a wedged runner by its TTL;
      * neither -> DOWN (no runner), which is a different claim from UNKNOWN (could not look).
    """
    out: Dict[str, Any] = {"state": UNKNOWN, "holder": None, "runtimes": {}}
    why = []
    try:
        from core.comm import runner_lock
        out["holder"] = runner_lock.holder(agent)
        out["state"] = UP if out["holder"] else DOWN
    except Exception as exc:
        why.append(f"runner lock unreadable: {type(exc).__name__}: {exc}")
    try:
        from core.comm import incarnation
        out["runtimes"] = incarnation.daemon_runtimes(agent) or {}
        if out["runtimes"]:
            out["state"] = UP
    except Exception as exc:
        why.append(f"daemon runtimes unreadable: {type(exc).__name__}: {exc}")
    if why and out["state"] == UNKNOWN:
        out["why"] = "; ".join(why)
    elif why:
        out["partial"] = "; ".join(why)      # one rung answered, one did not -- say both
    return out


# ------------------------------------------------------------------------ 4. operator mail
def _stream_keys(agent: str) -> List[str]:
    """Every stream addressed TO `agent`, deduped, work lane first (T045: that is the lane the
    prescribed commands consume)."""
    from core.comm import packet_spec
    ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
    keys = [packet_spec.lane_stream_key(ns, "work", to=agent),
            f"{ns}:inbox:{agent}"]
    out: List[str] = []
    for k in keys:
        if k not in out:
            out.append(k)
    return out


def _client():
    try:
        from core.comm.bus import get_bus
        b = get_bus("control")
        return (b._client if b is not None and b.online else None), b
    except Exception:
        return None, None


def _last_match(streams: List[str], predicate, limit: int = SCAN_LIMIT):
    """The newest entry in any of `streams` matching `predicate(fields)`.

    XREVRANGE only: read-only by construction, so no cursor can move no matter who calls this."""
    cli, _bus = _client()
    if cli is None:
        return None, "the bus is offline (Redis unreachable), so the streams cannot be read"
    best = None
    for key in streams:
        try:
            rows = cli.xrevrange(key, count=limit)
        except Exception:
            continue
        for sid, fields in rows or []:
            try:
                pairs = fields.items() if hasattr(fields, "items") else fields
                f = {(_k.decode() if isinstance(_k, bytes) else _k):
                     (_v.decode() if isinstance(_v, bytes) else _v) for _k, _v in pairs}
            except Exception:
                continue
            if not predicate(f):
                continue
            rec = {"id": sid, "ts": f.get("ts", ""), "frm": f.get("frm", ""),
                   "to": f.get("to", ""), "kind": f.get("kind", ""),
                   "content": _preview(f.get("content"))}
            try:
                rec["provenance"] = json.loads(f.get("meta") or "{}").get("origin", "unknown")
            except Exception:
                rec["provenance"] = "unknown"
            if best is None or _stream_order(sid) > _stream_order(best["id"]):
                best = rec
        if best is not None:
            break                      # the first stream with a hit is the freshest lane
    return best, ""


def _stream_order(sid: str) -> tuple:
    try:
        ms, seq = str(sid).split("-", 1)
        return (int(ms), int(seq))
    except Exception:
        return (0, 0)


def operator_mail(agent: str) -> Dict[str, Any]:
    """The last inbound operator message and the last outbound reply TO the operator."""
    ops = operator_ids()
    inbound, why_in = _last_match(_stream_keys(agent),
                                  lambda f: str(f.get("frm", "")) in ops)
    out: Dict[str, Any] = {"operator_ids": sorted(ops), "inbound": inbound,
                           "inbound_why": why_in}
    # Outbound: a reply to the operator lands on the operator's own inbox (operator_reply.py
    # sends to operator_id()), so that stream is the one to read -- for every operator id.
    streams: List[str] = []
    for who in sorted(ops):
        for k in _stream_keys(who):
            if k not in streams:
                streams.append(k)
    outbound, why_out = _last_match(streams, lambda f: str(f.get("frm", "")) == agent)
    out["outbound"] = outbound
    out["outbound_why"] = why_out
    if inbound is None and outbound is None:
        if why_in or why_out:
            # The streams could not be read at all -- that is UNKNOWN, not "nobody has written".
            out["state"] = UNKNOWN
            out["why"] = why_in or why_out
        else:
            # Readable and empty: the honest reading is DOWN (no exchange found), never UP --
            # an [UP] mark beside "none found" is how a screen teaches its reader the wrong thing.
            out["state"] = DOWN
            out["why"] = (f"no operator traffic in the last {SCAN_LIMIT} entries on this seat's "
                          f"streams or the operator's")
    else:
        out["state"] = UP
    return out


# -------------------------------------------------------------------------- 5. phone tunnel
def phone_tunnel(tailnet: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    """The PhoneLink forward (`ssh -R`) and whether the phone answers on the tailnet."""
    phone = _local_section("phone")
    host = (tailnet or os.environ.get("AKASHIC_PHONE_TAILNET")
            or str(phone.get("tailnet_host") or ""))
    raw_port = port or os.environ.get("AKASHIC_PHONE_PORT") or phone.get("ssh_port")
    try:
        prt = int(raw_port) if raw_port else 0
    except (TypeError, ValueError):
        prt = 0
    forwarded = [str(p) for p in (phone.get("forwarded_ports") or [])]
    if not host or not prt:
        # THREE ways to get here, and the message distinguishes them, because they have three
        # different fixes: no `phone` section at all, a section whose address is `null` by design
        # (the public file refuses to commit a routable address), or no sshd port anywhere.
        if not phone:
            why = _local_missing("phone", LOCAL_FILE)
        elif not host:
            why = (f"local/{LOCAL_FILE}.json carries phone.tailnet_host: null and the private "
                   f"profile (akashic-local/profile/{LOCAL_FILE}.json) supplied no value -- set "
                   f"AKASHIC_PHONE_TAILNET or add the overlay key. UNKNOWN, not 'down'")
        else:
            why = (f"no sshd port to connect to: local/{LOCAL_FILE}.json has phone.ssh_port "
                   f"{phone.get('ssh_port')!r} and AKASHIC_PHONE_PORT is unset")
        return {"state": UNKNOWN, "forwards": [],
                "why": why,
                "tailnet_host": host or "?", "tailnet_port": prt or "?",
                "phone_answers": None, "phone_state": UNKNOWN}
    ps = _psutil()
    forwards: List[Dict[str, Any]] = []
    tunnel_state = UNKNOWN
    tunnel_why = ""
    if ps is None:
        tunnel_why = "psutil is not importable, so the forward process could not be inspected"
    else:
        try:
            for proc in ps.process_iter(["pid", "cmdline", "create_time"]):
                argv = _argv(proc)
                if not _is_ssh_client(argv):
                    continue
                # the forward itself: a remote-forward argument -- either the bare flag followed
                # by its spec, or the flag glued to the spec. Shape only; the ports are the Local
                # layer's values (local/reachability.json: phone.forwarded_ports).
                if not any(str(a) == "-R" or str(a).startswith("-R") for a in argv):
                    continue
                forwards.append({"pid": proc.info.get("pid"),
                                 "started": _iso(proc.info.get("create_time") or time.time()),
                                 "age_s": _age(proc.info.get("create_time") or time.time()),
                                 "cmd": " ".join(argv)[:200]})
            tunnel_state = UP if forwards else DOWN
            if not forwards:
                ports_txt = f" ({', '.join(forwarded)})" if forwarded else ""
                tunnel_why = ("no ssh -R forward is running; the phone's loopback ports"
                              f"{ports_txt} are not reachable through this PC right now")
        except Exception as exc:                              # pragma: no cover - env dependent
            tunnel_why = f"the process walk failed: {type(exc).__name__}: {exc}"
    answers: Optional[bool] = None
    try:
        with socket.create_connection((host, prt), timeout=PHONE_CONNECT_TIMEOUT_S):
            answers = True
    except Exception:
        answers = False
    reach_state = DOWN if answers is False else UP
    return {"state": tunnel_state,
            "forwards": forwards, "why": tunnel_why,
            "tailnet_host": host, "tailnet_port": prt,
            "phone_answers": answers, "phone_state": reach_state}


# ------------------------------------------------------------------------------- the screen
def report(agent: str, session: str = "", *, phone: bool = True) -> Dict[str, Any]:
    """Every rung, gathered. Never raises: a rung that dies reads UNKNOWN with its reason."""
    rungs: Dict[str, Any] = {}
    for name, fn in (("gateway", gateway),
                     ("wake_listener", lambda: wake_seats(agent, session)),
                     ("consumer_seat", lambda: consumer_seat(agent)),
                     ("runner", lambda: live_runner(agent)),
                     ("operator_mail", lambda: operator_mail(agent))):
        try:
            rungs[name] = fn()
        except Exception as exc:                              # pragma: no cover - belt and braces
            rungs[name] = {"state": UNKNOWN,
                           "why": f"{type(exc).__name__}: {exc}"}
    if phone:
        try:
            rungs["phone_tunnel"] = phone_tunnel()
        except Exception as exc:                              # pragma: no cover
            rungs["phone_tunnel"] = {"state": UNKNOWN, "why": f"{type(exc).__name__}: {exc}"}
    verdict = agree(rungs)
    return {"agent": agent, "session": session, "generated": _iso(time.time()),
            "rungs": rungs, "verdict": verdict}


def agree(rungs: Dict[str, Any]) -> Dict[str, Any]:
    """The one-line verdict, and it names its own gaps rather than averaging them away."""
    reachable = []
    blocked = []
    if rungs.get("gateway", {}).get("state") == UP:
        reachable.append("gateway")
    else:
        blocked.append("gateway")
    if rungs.get("wake_listener", {}).get("state") == UP:
        reachable.append("wake listener")
    else:
        blocked.append("wake listener")
    if rungs.get("phone_tunnel", {}).get("phone_answers"):
        reachable.append("phone (tailnet)")
    unknown = [k for k, v in rungs.items() if isinstance(v, dict) and v.get("state") == UNKNOWN]
    if reachable:
        line = ("reachable by: " + ", ".join(reachable)
                + (("; NOT by: " + ", ".join(blocked)) if blocked else ""))
    else:
        line = "reachable by NO measured path" + (
            "; unmeasured: " + ", ".join(unknown) if unknown else "")
    return {"line": line, "reachable": reachable, "blocked": blocked, "unmeasured": unknown}


_MARK = {UP: "UP  ", DOWN: "DOWN", UNKNOWN: "????"}


def render(rep: Dict[str, Any]) -> str:
    """The one screen. Fixed order, one rung per block, gaps named."""
    r = rep.get("rungs") or {}
    lines: List[str] = []
    lines.append(f"reachability -- {rep.get('agent')}"
                 + (f" session {rep.get('session')}" if rep.get("session") else "")
                 + f"  ({rep.get('generated')})")
    lines.append(f"verdict: {(rep.get('verdict') or {}).get('line', '')}")

    g = r.get("gateway") or {}
    lines.append("")
    lines.append(f"[{_MARK.get(g.get('state'), '????')}] discord gateway")
    if g.get("state") == UP:
        lines.append(f"       pid {g.get('pid')} started {g.get('started')} "
                     f"({fmt_age(g.get('age_s'))} ago)")
        lines.append(f"       runs from {g.get('worktree') or '(cwd unknown)'}")
        log = g.get("log") or {}
        if log.get("state") == UP:
            lines.append(f"       REAL log {log.get('path')} "
                         f"({fmt_age(log.get('age_s'))} old, {log.get('size')} bytes)")
            if log.get("tail"):
                lines.append(f"       last line: {log.get('tail')}")
        else:
            lines.append(f"       REAL log UNKNOWN -- {log.get('why', '')}"
                         + (f" (would be {log.get('path')})" if log.get("path") else ""))
    else:
        lines.append(f"       {g.get('why', '')}")

    w = r.get("wake_listener") or {}
    lines.append("")
    lines.append(f"[{_MARK.get(w.get('state'), '????')}] wake listener (this seat)")
    for s in w.get("seats") or []:
        who = s.get("session") or "(name-keyed, legacy)"
        lines.append(f"       {who}: pid {s.get('pid')} alive={s.get('alive')} "
                     f"armed {fmt_age(s.get('age_s'))} ago origin={s.get('origin') or '?'}")
    if w.get("state") != UP:
        lines.append(f"       {w.get('why', '')}")

    c = r.get("consumer_seat") or {}
    lines.append("")
    lines.append(f"[{_MARK.get(c.get('state'), '????')}] consumer seat (RB-21, this agent id)")
    if c.get("state") == UP:
        lines.append(f"       HELD by {c.get('holder')} since {c.get('since')} "
                     f"(ttl {c.get('ttl_s')}s) -- this session consumes only if that is you")
    else:
        lines.append(f"       {c.get('why', '')}")

    rn = r.get("runner") or {}
    if rn:
        lines.append("")
        lines.append(f"[{_MARK.get(rn.get('state'), '????')}] runner (a handoff surfaces at its "
                     f"NEXT boot)")
        if rn.get("holder"):
            lines.append(f"       runner lock held by {rn['holder'].get('token', '?')} "
                         f"since {rn['holder'].get('ts', '?')}")
        if rn.get("runtimes"):
            try:
                lines.append(f"       runtimes: {json.dumps(rn['runtimes'])[:300]}")
            except Exception:
                lines.append("       runtimes present")
        if rn.get("state") != UP:
            lines.append(f"       {rn.get('why') or 'no live runner reported'}")
        if rn.get("partial"):
            lines.append(f"       (partial read: {rn['partial']})")

    om = r.get("operator_mail") or {}
    lines.append("")
    lines.append(f"[{_MARK.get(om.get('state'), '????')}] operator mail "
                 f"(ids: {', '.join(om.get('operator_ids') or [])})")
    for label, rec, why in (("inbound ", om.get("inbound"), om.get("inbound_why")),
                            ("outbound", om.get("outbound"), om.get("outbound_why"))):
        if rec:
            lines.append(f"       {label} {rec.get('ts')}  id {rec.get('id')}  "
                         f"{rec.get('frm')} -> {rec.get('to')}  [{rec.get('kind')}]  "
                         f"via {rec.get('provenance')}")
            lines.append(f"                {rec.get('content')}")
        else:
            lines.append(f"       {label} none found{(' -- ' + why) if why else ''}")

    p = r.get("phone_tunnel") or {}
    if p:
        lines.append("")
        lines.append(f"[{_MARK.get(p.get('state'), '????')}] phone tunnel")
        for f in p.get("forwards") or []:
            lines.append(f"       ssh -R pid {f.get('pid')} ({fmt_age(f.get('age_s'))} old): "
                         f"{f.get('cmd')}")
        if p.get("state") != UP:
            lines.append(f"       {p.get('why', '')}")
        answers = p.get("phone_answers")
        tail = (f"phone answers on {p.get('tailnet_host')}:{p.get('tailnet_port')}"
                if answers else
                f"phone did NOT answer on {p.get('tailnet_host')}:{p.get('tailnet_port')} "
                f"within {PHONE_CONNECT_TIMEOUT_S}s"
                if answers is False else "phone reachability unmeasured")
        lines.append(f"       {tail}")

    lines.append("")
    lines.append("(read-only: no cursor advanced, nothing sent, nothing armed)")
    return "\n".join(lines)
