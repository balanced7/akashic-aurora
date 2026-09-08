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

IT KEEPS THE EVIDENCE. The listener's stdout/stderr is ManagedChild's pipe, drained into a
200-line ring that ManagedChild hands to on_exit — and to nobody else. On 2026-08-26 the
listener died three times in fifty seconds, the breaker tripped correctly, and the cause could
not be found: on_exit was never wired, so the ring died with each child, and the breaker line
sent the operator to state/logs/remote-bridge-listener.log, which only peer_connect.py writes
(it hands that file to the listener as stdout when IT launches one) — an empty file, pointed
at with confidence [e935125f0e]. Now every exit prints the tail here AND appends it to
--child-log (default: that same file, so its name is true under supervision too), and the
breaker verdict re-prints the last tail beside itself, naming the sink that actually got it.

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

from scripts.bifrost_child import ManagedChild, _RING_LINES  # noqa: E402


def _stamp() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _datestamp() -> str:
    """Full date for the append-only file: it spans days; the console does not."""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def door_open(host: str, port: int, timeout: float = 3.0) -> bool:
    """Is the door actually answering? NEVER RAISES.

    Deliberately probed at the SOCKET rather than inferred from the child being alive: the
    failure this file exists for was a process that stopped serving. `alive` is a claim about
    a pid; this is a claim about the door.

    OBSERVATION ONLY. This result drives nothing — it is printed on transitions and then
    forgotten. Respawn, backoff and the breaker are decided inside child.poll() from the
    child's EXIT CODE alone. A DOOR SHUT line is a symptom report, not a cause and not a
    trigger; reading it as either is the misreading that cost the 2026-08-26 root-cause.
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
    ap.add_argument("--child-log", default=None,
                    help="file the listener's output tail is APPENDED to on every exit "
                         "(default: state/logs/remote-bridge-listener.log under the repo — "
                         "the file peer_connect gives the listener as stdout, so the name "
                         "stays true whichever way the listener was launched)")
    a = ap.parse_args(argv)
    child_log = Path(a.child_log) if a.child_log else (
        REPO / "state" / "logs" / "remote-bridge-listener.log")

    args = [sys.executable, str(REPO / "scripts" / "remote_bridge_listener.py"),
            "--host", a.host, "--port", str(a.port)]
    if a.peer:
        args += ["--peer", a.peer]

    child = ManagedChild(args, cwd=str(REPO))

    # Evidence of the most recent exit, kept so the breaker verdict can re-print it BESIDE
    # itself instead of pages up the scrollback. `tee` is the path the tail actually reached,
    # or None when it reached no file — the verdict names only sinks that received it.
    last = {"code": None, "tail": "", "tee": None, "tee_err": ""}

    def _on_child_exit(code: int, tail) -> None:
        """ManagedChild calls this ONCE per exit with the ring tail, before it decides
        restart/backoff/breaker. Everything the child said on its way out passes through
        here exactly once — printed and appended now, or gone with the deque."""
        tail = (tail or "").rstrip()
        lines = tail.splitlines()
        last["code"], last["tail"] = code, tail
        pid = f" (pid {child.pid})" if child.pid else ""
        verdict = ("DELIBERATE stop, exit 0 — NOT respawned (N1)" if code == 0
                   else "crash — ManagedChild schedules the respawn/backoff/breaker")
        print(f"[{_stamp()}] LISTENER EXITED code={code}{pid}: {verdict}", flush=True)
        if lines:
            full = (f" — the ring holds {_RING_LINES}, so OLDER LINES WERE DROPPED"
                    if len(lines) >= _RING_LINES else "")
            print(f"  last {len(lines)} line(s) of its output{full}:", flush=True)
            for ln in lines:
                print(f"  | {ln}", flush=True)
        else:
            print("  (no output captured — it died before printing anything)", flush=True)
        try:
            child_log.parent.mkdir(parents=True, exist_ok=True)
            with open(child_log, "a", encoding="utf-8") as f:
                f.write(f"==== {_datestamp()} supervised listener exited code={code}{pid}; "
                        f"{len(lines)} line(s) of its output follow ====\n")
                f.write((tail + "\n") if tail else "(no output captured)\n")
            last["tee"], last["tee_err"] = str(child_log), ""
            print(f"  (appended to {child_log})", flush=True)
        except Exception as e:                                    # noqa: BLE001
            last["tee"], last["tee_err"] = None, f"{type(e).__name__}: {e}"
            print(f"  WARNING: could not append to {child_log} ({last['tee_err']}) — the copy "
                  f"printed above is the ONLY record of this exit", flush=True)

    child.on_exit = _on_child_exit

    print(f"[{_stamp()}] supervising the bridge door on {a.host}:{a.port}", flush=True)
    print(f"  backoff + circuit breaker via ManagedChild; exit 0 is a DELIBERATE stop and is "
          f"NOT respawned", flush=True)
    print(f"  the listener's output tail is printed here on every exit and appended to "
          f"{child_log}", flush=True)

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
                # The breaker is the honest end of the line: say so loudly, stop pretending
                # supervision is happening, and put the evidence BESIDE the verdict — naming
                # only a sink that actually received it.
                print(f"[{_stamp()}] BREAKER TRIPPED — the listener failed repeatedly and is "
                      f"NOT being respawned. This is a real fault, not a flap.", flush=True)
                if last["tee"]:
                    where = f"appended to {last['tee']}, and printed here"
                elif last["tee_err"]:
                    where = f"printed here ONLY — appending to {child_log} failed: {last['tee_err']}"
                else:
                    where = f"printed here ONLY — no exit ever reported a tail to {child_log}"
                print(f"  last output of the listener before its final death ({where}):",
                      flush=True)
                for ln in (last["tail"].splitlines()
                           or ["(no output captured — it died before printing anything)"]):
                    print(f"  | {ln}", flush=True)
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
