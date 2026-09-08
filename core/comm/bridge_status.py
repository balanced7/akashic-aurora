"""Remote-bridge status and remediation — the model the Bifrost UI renders.

Daniil, 2026-08-25: "make the bifrost ui be remote aware and to allow for remediation."

Kept OUT of scripts/bifrost_ui.py deliberately. The UI is a hot shared file; this is logic
that wants pins, and pins want a module that imports without a socket. The panel should be a
few lines of paint over a dict computed here.

TWO HALVES, AND THEY OBEY DIFFERENT RULES.

STATUS IS A READ, AND MUST NOT LIE BY OMISSION. The temptation in a dashboard is to render
what the config says and call it state. That is how a peer shows green because a row exists —
the same green-receipt-over-a-broken-path shape that cost this fleet 2h44m, wearing better
typography. So: unprobed reachability is reported as ABSENT (None), never as a verdict; an
unkeyed peer reads INERT rather than broken, because configuration is a state and not a
failure; and every render carries `measured_at`, because a number with no age is a claim
about now that may be about an hour old.

REMEDIATION IS AN ACT, AND MUST NEVER BE A SIDE EFFECT OF LOOKING. Anything that changes the
world requires `confirm=True`, so rendering a page cannot perform work and a stray GET cannot
restart a listener. Actions report what they ACTUALLY did rather than what they attempted.

The sharp one is drain_parked. It moves another fleet's words onto our live bus, which spends
the parked-not-bussed defence the inbound gate exists to hold — so what lands carries the
Discord guest-tier posture (R2/R3): attributed in the body, `authority: none` in the meta,
provenance from the verified route, and no control kinds. Reach, never authority. It moves
mail; it never obeys it.

The other sharp one is restart_listener, because it stops PROCESSES, and a process is found by
its command line. It stops an interpreter whose PROGRAM is the listener script -- never a
command line that merely mentions the name -- and it refuses its own lineage and anything
running pytest, by pid, in the report. [5d2f0963e1] is what the looser predicate did: with the
listener's TEST file on a pytest command line, `-like '*remote_bridge_listener*'` selected
pytest itself, the py launcher and the host shell, and the panel's restart took the whole shell
down with zero output.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.outcome import BoundaryOutcome
from core.comm import remote_relay as RR


def _reachable(url: str, timeout: float = 4.0) -> Optional[bool]:
    """TCP-connect a peer's endpoint. None when there is nothing to probe.

    Deliberately a connect and not a signed POST: "is the door there" and "does the door admit
    me" are different questions, and conflating them makes a key problem look like an outage.
    """
    if not url:
        return None
    import socket
    try:
        host = url.split("//", 1)[-1].split("/", 1)[0]
        h, _, p = host.partition(":")
        socket.create_connection((h, int(p or 80)), timeout=timeout).close()
        return True
    except Exception:                                             # noqa: BLE001
        return False


def status(*, probe: bool = True) -> Dict[str, Any]:
    """The whole remote plane as one dict. NEVER RAISES.

    `probe=False` is the cheap render and reports reachability as None rather than guessing —
    the panel must not imply a measurement it did not take.
    """
    out: Dict[str, Any] = {"measured_at": int(time.time()), "probed": bool(probe),
                           "peers": [], "outbox_pending": 0, "parked": 0,
                           "listener": {"bound": None, "reachable": None}}
    try:
        RR._reset_cache()
        pending = RR.pending()
        out["outbox_pending"] = len(pending)
        parked = [r for r in RR._read_jsonl(RR.inbox_path())
                  if str(r.get("frm", "")).startswith("remote:")]
        out["parked"] = len(parked)
        if parked:
            newest = max(int(r.get("admitted_at") or 0) for r in parked)
            out["newest_inbound"] = newest
            out["newest_inbound_age_s"] = max(0, int(time.time()) - newest)

        for row in RR.peers():
            name = str(row.get("name") or "")
            url = str(row.get("url") or "")
            keyed = bool(RR._secret(str(row.get("inbound_secret_file")
                                        or RR.INBOUND_KEY_FILE)))
            queued = sum(1 for r in pending
                         if str(r.get("peer") or "") in (name, str(row.get("as") or "")))
            last = [r for r in parked if r.get("frm") == f"remote:{name}"]
            # STATE IS A JUDGEMENT AND SAYS SO. "inert" is not a failure -- a peer with no key
            # or no route is configured-and-waiting, and painting that red teaches the reader
            # to ignore red.
            if not keyed or not url:
                state = "inert"
            else:
                state = "ready"
            out["peers"].append({
                "name": name,
                "as": str(row.get("as") or ""),
                "url": url,
                "keyed": keyed,
                "state": state,
                "queued_for_peer": queued,
                "received": len(last),
                "last_inbound": max((int(r.get("admitted_at") or 0) for r in last), default=0),
                "reachable": _reachable(url) if probe else None,
            })
    except Exception as e:                                        # noqa: BLE001
        # A dashboard that crashes on a malformed world takes the operator's eyes out at
        # exactly the moment something is wrong. Degrade, and say why in the payload.
        out["error"] = f"{type(e).__name__}: {e}"
    return out


#: What a UI may offer. `danger` drives confirmation and colour; `what` is shown to the human
#: BEFORE they press it, because a button whose consequence is only in the source is a trap.
_ACTIONS: List[Dict[str, str]] = [
    {"id": "tick_outbox", "label": "Retry queued mail", "danger": "low",
     "what": "Attempt delivery of everything in the outbox. Failures stay queued; nothing is "
             "lost either way. Safe to press repeatedly."},
    {"id": "drain_parked", "label": "Drain parked peer mail to the bus", "danger": "high",
     "what": "Puts another fleet's messages on YOUR live bus, attributed and authority:none. "
             "This spends the parked-not-bussed defence on purpose — an agent will read them."},
    {"id": "restart_listener", "label": "Restart the inbound listener", "danger": "medium",
     "what": "Bounces the local listener process. Mail sent during the gap is RETAINED by the "
             "sender's outbox and replays; nothing is lost, but the door is shut briefly."},
]


def actions() -> List[Dict[str, str]]:
    return [dict(a) for a in _ACTIONS]


def act(action_id: Any, *, confirm: bool = False,
        bus_send: Optional[Callable[..., Any]] = None,
        process_table: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        kill: Optional[Callable[[int], bool]] = None) -> BoundaryOutcome:
    """Perform one remediation. NEVER RAISES.

    `confirm` is not ceremony: rendering a page must never perform work, and a GET that
    restarts a listener is a defect wearing a button.

    `bus_send`, `process_table` and `kill` are seams -- the world-touching halves of drain and
    restart, injectable so a test can pin the ACT without the side effect. [5d2f0963e1] is what
    a test without the seam did to its host.
    """
    try:
        aid = str(action_id or "")
        spec = next((a for a in _ACTIONS if a["id"] == aid), None)
        if spec is None:
            return BoundaryOutcome.failed(
                f"unknown action {aid!r} — offered actions are "
                f"{[a['id'] for a in _ACTIONS]}. Refusing rather than guessing.")
        if spec["danger"] in ("medium", "high") and not confirm:
            return BoundaryOutcome.failed(
                f"{aid} is rated {spec['danger']} and needs confirm=true. {spec['what']}")

        if aid == "tick_outbox":
            out = RR.tick()
            return out

        if aid == "drain_parked":
            return _drain(bus_send)

        if aid == "restart_listener":
            return _restart_listener(process_table=process_table, kill=kill)

        return BoundaryOutcome.failed(f"action {aid!r} is offered but not implemented")
    except Exception as e:                                        # noqa: BLE001
        return BoundaryOutcome.caught(e, where="bridge_status.act")


def _drain(bus_send: Optional[Callable[..., Any]]) -> BoundaryOutcome:
    """Put parked peer mail on the local bus with the guest-tier posture.

    Attributed in the body, authority:none in the meta, provenance from the VERIFIED ROUTE
    with the sender's own claim kept inert beside it. Reach, never authority — the same
    settlement the Discord guest tier reached for human visitors, applied to a fleet.
    """
    RR._reset_cache()
    rows = [r for r in RR._read_jsonl(RR.inbox_path())
            if str(r.get("frm", "")).startswith("remote:")]
    if not rows:
        return BoundaryOutcome.done(ref="drain", chars=0)

    send = bus_send
    if send is None:
        from core.comm.bus import Bus
        bus = Bus("bridge-drain")

        def send(**kw):
            return bus.broadcast(kw.get("kind", "chat"), kw.get("content"),
                                 meta=kw.get("meta"))

    n = 0
    for r in rows:
        send(kind="chat",
             content=f"[remote {r.get('frm')}] {r.get('content')}",
             meta={"source": "remote-bridge", "remote": True, "authority": "none",
                   "route": r.get("frm"), "claimed_frm": r.get("claimed_frm"),
                   "bridge_id": r.get("id"),
                   "idempotency_key": f"bridge:{r.get('id')}"})
        n += 1
    return BoundaryOutcome.done(ref="drain", chars=n)


#: The listener's program file. Discovery keys on this being the interpreter's PROGRAM (its
#: first positional argument) -- never on the name appearing somewhere in a command line.
LISTENER_SCRIPT = "remote_bridge_listener.py"

_INTERPRETER_NAME = re.compile(r"^(?:py|pyw|python|pythonw)[\d.]*(?:\.exe)?$", re.I)
_PATH_PREFIX = r'(?:"(?:[^"]*[\\/])?|(?:[^"\s]*[\\/])?)'       # an optional directory, quoted or bare
_LISTENER_PROGRAM = re.compile(
    r"^\s*" + _PATH_PREFIX + r'(?:py|pyw|python|pythonw)[\d.]*(?:\.exe)?"?'   # the interpreter
    r"(?:\s+-[\w.]+)*"                     # single-token interpreter flags (-u, -3.11, -Wignore);
                                           # `-m x` / `-c x` never match: x would have to BE the script
    r"\s+" + _PATH_PREFIX + re.escape(LISTENER_SCRIPT) + r'"?(?=\s|$)',        # the PROGRAM
    re.I)


def _process_table() -> List[Dict[str, Any]]:
    """The host's process table as {pid, ppid, name, cmdline} rows. RAW on purpose: the
    selection lives in select_listener_pids, one pure Python function a pin can feed a fake
    table, rather than a predicate string handed to PowerShell where nothing can test it.
    Windows/CIM; elsewhere the FileNotFoundError reaches the caller's outcome, which is honest
    -- this action stops processes with taskkill."""
    import json
    import subprocess
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
         "Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId, Name, "
         "CommandLine | ConvertTo-Json -Compress"],
        capture_output=True, encoding="utf-8", errors="replace", timeout=25)
    raw = json.loads(r.stdout) if (r.stdout or "").strip() else []
    if isinstance(raw, dict):                                     # ConvertTo-Json unwraps a 1-row table
        raw = [raw]
    rows: List[Dict[str, Any]] = []
    for p in raw:
        try:
            rows.append({"pid": int(p.get("ProcessId")),
                         "ppid": int(p.get("ParentProcessId") or 0),
                         "name": str(p.get("Name") or ""),
                         "cmdline": str(p.get("CommandLine") or "")})
        except (TypeError, ValueError, AttributeError):
            continue
    return rows


def select_listener_pids(rows: List[Dict[str, Any]], *, self_pid: Optional[int] = None,
                         self_ppid: Optional[int] = None
                         ) -> Tuple[List[int], List[Tuple[int, str]]]:
    """(targets, refused) from a process table. PURE -- no host access -- so the predicate and
    the self-protection are pinnable against a fake table.

    SELECTED: an interpreter whose PROGRAM is the listener script. Not "a command line that
    contains the name": `py -m pytest tests/test_remote_bridge_listener_pins.py` contains it,
    and so do the shell carrying that command, an editor with the file open and a grep.
    [5d2f0963e1] is the day `-like '*remote_bridge_listener*'` selected the host.

    REFUSED, independently of the predicate and reported by pid: the caller itself, its
    ancestor chain (walked by ppid and bounded, because pid reuse can make a chain loop) and
    anything running pytest. If the predicate ever regresses, this is what keeps a restart
    button from being a suicide button; while it never fires, it costs one set lookup.
    """
    me = int(os.getpid() if self_pid is None else self_pid)
    parent = int(os.getppid() if self_ppid is None else self_ppid)
    ppid_of: Dict[int, int] = {}
    for r in rows:
        try:
            ppid_of[int(r["pid"])] = int(r.get("ppid") or 0)
        except (TypeError, ValueError, KeyError):
            continue
    lineage = {me}
    cur = me
    for _ in range(64):
        nxt = ppid_of.get(cur, 0)
        if nxt <= 0 or nxt in lineage:
            break
        lineage.add(nxt)
        cur = nxt
    lineage.add(parent)                       # even when the table lacks the caller's own row

    targets: List[int] = []
    refused: List[Tuple[int, str]] = []
    for r in rows:
        try:
            pid = int(r["pid"])
        except (TypeError, ValueError, KeyError):
            continue
        name = str(r.get("name") or "")
        cmd = str(r.get("cmdline") or "")
        if name and not _INTERPRETER_NAME.match(name):
            continue
        if not _LISTENER_PROGRAM.match(cmd):
            continue
        if pid in lineage:
            refused.append((pid, "self or an ancestor of the caller"))
        elif "pytest" in cmd.lower():
            refused.append((pid, "running under pytest"))
        else:
            targets.append(pid)
    return targets, refused


def _taskkill(pid: int) -> bool:
    """Stop one process. True only when taskkill itself reported success."""
    import subprocess
    r = subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True,
                       timeout=15)
    return r.returncode == 0


def _restart_listener(*, process_table: Optional[Callable[[], List[Dict[str, Any]]]] = None,
                      kill: Optional[Callable[[int], bool]] = None) -> BoundaryOutcome:
    """Stop the local listener. Reports what it actually observed, not what it attempted.

    [5d2f0963e1] This used to select `CommandLine -like '*remote_bridge_listener*'` and
    taskkill /F every match. A command line that MENTIONS the listener is not the listener:
    with the listener's TEST file on the pytest command line, the matches were pytest's own
    python.exe, the py launcher and the host shell -- and test_act_never_raises, pressing this
    button, took the whole shell down with zero output. Now discovery is a raw table
    (`process_table`), selection is select_listener_pids (program == the listener script; the
    caller's lineage and anything under pytest refused and NAMED), and the stop is `kill`.
    Both seams default to the host and exist so a test never has to touch it.
    """
    find = process_table or _process_table
    stop = kill or _taskkill
    try:
        targets, refused = select_listener_pids(find())
        stopped = [pid for pid in targets if stop(pid)]
        failed = [pid for pid in targets if pid not in stopped]
        refused_txt = ", ".join(f"{pid} ({why})" for pid, why in refused) or "-"
        return BoundaryOutcome.partially(
            f"matched {len(targets) + len(refused)} listener process(es); refused "
            f"{len(refused)} as self/test [{refused_txt}]; stopped {stopped}; failed to stop "
            f"{failed}. RELAUNCH IS NOT AUTOMATED here on purpose: the bind address and --peer "
            f"are operator decisions, and a panel that guesses them would quietly rebind the "
            f"door somewhere nobody chose.",
            ref="restart", chars=len(stopped), stopped=stopped, failed=failed,
            refused=[pid for pid, _ in refused])
    except Exception as e:                                        # noqa: BLE001
        return BoundaryOutcome.caught(e, where="bridge_status._restart_listener")
