"""serve -- `aurora link serve`: run the fleet-link daemon under supervision and pump its mail.

The daemon (aurora-linkd) runs as a ManagedChild with backoff and a circuit breaker, speaking
JSON-RPC on its stdin/stdout to this process and on its socket to the CLI. This loop does the
Python half, and only that:

- the quarantine pump: admitted records -> `bifrost:remote:<link>` (quarantine.py);
- local promotion rules, when a link's promote.toml opts into any (promote.py).

The daemon aborts on a panic and is restarted; a deliberate stop (exit 0) stays stopped. Its
stderr tail goes to `state/logs/linkd.log` on every exit, next to the old bridge listener's log.
"""

from __future__ import annotations

import contextlib
import io
import signal
import sys
import time
from typing import TYPE_CHECKING, Any

from core.link import promote, quarantine
from core.link.client import MISSING, Client, LinkRpcError, find_linkd, spawn_args
from core.paths import data_root

if TYPE_CHECKING:
    from pathlib import Path


def log_path(home: Path | None = None) -> Path:
    return (home or data_root()) / "state" / "logs" / "linkd.log"


def daemon_flags(
    *,
    mailbox: bool = False,
    relays: list[str] | None = None,
    no_relay: bool = False,
    no_n0: bool = False,
    no_mdns: bool = False,
    bind: str | None = None,
    trace_rpc: bool = False,
) -> list[str]:
    """The daemon's serve flags from `aurora link serve` options."""
    flags: list[str] = []
    if mailbox:
        flags.append("--mailbox")
    for r in relays or []:
        flags += ["--relay", r]
    if no_relay:
        flags.append("--no-relay")
    if no_n0:
        flags.append("--no-n0")
    if no_mdns:
        flags.append("--no-mdns")
    if bind:
        flags += ["--bind", bind]
    if trace_rpc:
        flags.append("--trace-rpc")
    return flags


def run(*, flags: list[str] | None = None, mailbox: bool = False, once: bool = False, out: Any = None) -> int:
    """Supervise the daemon and pump until interrupted. Returns the process exit code."""
    out = out or sys.stdout
    binary = find_linkd()
    if not binary:
        print(f"[link serve] {MISSING}", file=out)
        return 2
    from scripts.bifrost_child import ManagedChild

    home = data_root()
    child = ManagedChild(spawn_args(binary, home, stdio=True, socket_=True, offline=False, extra=flags), stdio_rpc=True)

    def _on_exit(code: int, tail: str | None) -> None:
        path = log_path(home)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"--- aurora-linkd exited {code} at {time.strftime('%Y-%m-%dT%H:%M:%S')}\n{tail or ''}\n")
        print(f"[link serve] aurora-linkd exited {code}; tail in {path}", file=out, flush=True)

    child.on_exit = _on_exit
    stopping = False

    def _stop(*_: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    child.spawn()
    print(f"[link serve] aurora-linkd pid {child.pid} ({binary})", file=out, flush=True)
    client: Client | None = None
    client_pid: int | None = None
    try:
        while not stopping:
            child.poll()
            pipes = child.rpc_pipes
            if pipes is None:
                client = None
                time.sleep(0.5)
                continue
            if client is None or client_pid != child.pid:
                reader, writer = pipes
                client = Client(io.BufferedReader(reader), writer, desc=f"stdio pid {child.pid}")
                client_pid = child.pid
            if mailbox:
                time.sleep(1.0)  # a mailbox opens nothing: no quarantine, no promotion
                continue
            try:
                events = quarantine.pump_once(client, timeout_ms=2000)
                if events:
                    print(f"[link serve] {len(events)} record(s) quarantined", file=out, flush=True)
                    for done in promote.apply_rules(client, events):
                        print(
                            f"[link serve] rule promoted {done['record_id'][:12]} -> {done.get('seat')}",
                            file=out,
                            flush=True,
                        )
                elif quarantine.redis_client() is None:
                    time.sleep(2.0)  # bus offline: everything stays in the store until it is back
            except (LinkRpcError, OSError, ValueError) as e:
                print(
                    f"[link serve] channel error ({type(e).__name__}: {e}); waiting for the daemon",
                    file=out,
                    flush=True,
                )
                client = None
                time.sleep(1.0)
            if once:
                break
    finally:
        if client is not None:
            with contextlib.suppress(LinkRpcError, OSError, ValueError):
                client.call("daemon.shutdown")
        child.terminate()
    return 0
