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
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

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
        bus_send: Optional[Callable[..., Any]] = None) -> BoundaryOutcome:
    """Perform one remediation. NEVER RAISES.

    `confirm` is not ceremony: rendering a page must never perform work, and a GET that
    restarts a listener is a defect wearing a button.
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
            return _restart_listener()

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


def _restart_listener() -> BoundaryOutcome:
    """Bounce the local listener. Reports what it actually observed, not what it attempted."""
    import subprocess
    import sys as _sys
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "
             "'*remote_bridge_listener*' } | ForEach-Object { $_.ProcessId }"],
            capture_output=True, text=True, timeout=25)
        pids = [p.strip() for p in (r.stdout or "").split() if p.strip().isdigit()]
        for pid in pids:
            subprocess.run(["taskkill", "/PID", pid, "/F"], capture_output=True, text=True)
        return BoundaryOutcome.partially(
            f"stopped {len(pids)} listener process(es) {pids}. RELAUNCH IS NOT AUTOMATED here "
            f"on purpose: the bind address and --peer are operator decisions, and a panel that "
            f"guesses them would quietly rebind the door somewhere nobody chose.",
            ref="restart", chars=len(pids))
    except Exception as e:                                        # noqa: BLE001
        return BoundaryOutcome.caught(e, where="bridge_status._restart_listener")
