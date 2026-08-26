"""Keep the bridge door open — supervise the inbound listener so staging cannot be missed.

    py scripts/remote_bridge_supervise.py --host 100.86.106.36 --peer serge-dsh

THE STAGING MAILBOX ALREADY EXISTS AND ALREADY AUTO-CAPTURES. accept() parks every admitted
message in state/coord/remote_bridge_inbox.jsonl — durable on disk, deduped by stable id
(RB-26), no drain required for the capture to happen. That half has worked all along.

WHAT FAILED ON 2026-08-25 WAS THE DOOR, NOT THE MAILBOX. The listener served a request at
20:46:35 and was simply absent afterwards — no crash line, no error, just gone — and for
nineteen minutes every message sent to us was refused before it could ever be staged. A
mailbox behind a closed door captures nothing, however durable it is.

So this is the missing sibling: something whose only job is that the door stays open.

IT SUPERVISES RATHER THAN RESTARTS, and the difference matters. A bare restart loop turns a
listener that crashes on startup into an infinite spawn storm. core/comm's ManagedChild already
solves this properly — non-blocking backoff, a circuit breaker (3 failures in 300s trips it),
and N1: EXIT CODE 0 IS A DELIBERATE HANDOVER AND IS NOT RESPAWNED, so an operator who stops the
listener on purpose does not fight a supervisor to keep it stopped. Inherited, not reinvented;
it is the same machinery bifrost_daemon uses for runners.

WHAT IT WILL NOT DO: it will not choose your bind address or your peer name. Those are operator
decisions, and a supervisor that guesses them would rebind the door somewhere nobody chose —
the same reason bridge_status.restart_listener stops rather than relaunches. Pass them.
"""
from __future__ import annotations

import argparse
import datetime
import socket
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.bifrost_child import ManagedChild  # noqa: E402


def _stamp() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def door_open(host: str, port: int, timeout: float = 3.0) -> bool:
    """Is the door actually answering? NEVER RAISES.

    Deliberately probed at the SOCKET rather than inferred from the child being alive: the
    failure this file exists for was a process that stopped serving. `alive` is a claim about
    a pid; this is a claim about the door.
    """
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except Exception:                                             # noqa: BLE001
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Supervise the remote-bridge inbound listener")
    ap.add_argument("--host", required=True, help="bind address (operator decision, not guessed)")
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--peer", default="", help="route name for provenance")
    ap.add_argument("--poll-sec", type=float, default=5.0)
    a = ap.parse_args(argv)

    args = [sys.executable, str(REPO / "scripts" / "remote_bridge_listener.py"),
            "--host", a.host, "--port", str(a.port)]
    if a.peer:
        args += ["--peer", a.peer]

    child = ManagedChild(args, cwd=str(REPO))
    print(f"[{_stamp()}] supervising the bridge door on {a.host}:{a.port}", flush=True)
    print(f"  backoff + circuit breaker via ManagedChild; exit 0 is a DELIBERATE stop and is "
          f"NOT respawned", flush=True)

    child.spawn()
    was_open = None
    while True:
        time.sleep(a.poll_sec)
        try:
            child.poll()                       # drives restart/backoff/breaker internally

            # TRANSITIONS ONLY. A supervisor that narrates every quiet tick gets muted, and a
            # muted supervisor is the same silence by a longer road.
            now_open = door_open(a.host, a.port)
            if now_open != was_open:
                if now_open:
                    print(f"[{_stamp()}] DOOR OPEN — {a.host}:{a.port} answering"
                          f"{f' (pid {child.pid})' if child.pid else ''}", flush=True)
                else:
                    print(f"[{_stamp()}] DOOR SHUT — {a.host}:{a.port} not answering. Peers are "
                          f"being REFUSED right now; their outboxes retain and replay, so "
                          f"nothing is lost, but nothing is staged either.", flush=True)
                was_open = now_open

            if child.tripped:
                # The breaker is the honest end of the line: say so loudly and stop pretending
                # supervision is happening.
                print(f"[{_stamp()}] BREAKER TRIPPED — the listener failed repeatedly and is "
                      f"NOT being respawned. Read state/logs/remote-bridge-listener.log; this "
                      f"is a real fault, not a flap.", flush=True)
                return 1
        except KeyboardInterrupt:
            print(f"\n[{_stamp()}] stopping supervisor (listener left as-is)", flush=True)
            return 0
        except Exception as e:                                    # noqa: BLE001
            print(f"[{_stamp()}] supervisor tick error ({type(e).__name__}: {e}) — continuing",
                  flush=True)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
