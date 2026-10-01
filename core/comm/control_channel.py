"""Out-of-band control: a loopback listener that survives a dead bus.

WHY THIS EXISTS -- measured, 2026-07-26
---------------------------------------
kimi wedged for 12+ hours and was UNCOMMANDABLE. Not crashed -- up, heartbeating, and
unreachable. `control.is_halted` is checked inside the message-handling path, which only runs
AFTER a message arrives, which is exactly what a blocked read prevents. So the only way to
speak to an agent ran through the path that had failed.

The bus could not carry a stand-down. Redis had no record of the connections (zero of kimi's
12 sockets appeared in CLIENT LIST -- they terminated at `wslrelay`, which stays alive and
keeps ACKing after the container side dies). The heartbeat kept reporting a live agent. The
only instrument that reported truth was py-spy -- an out-of-band channel. This module makes
that capability ours instead of borrowed.

Daniel's framing, which is what named the gap: our lanes (work/trace/sig) are LOGICAL
separation over ONE transport. A management VLAN's value is not the tag, it is that it
survives the failure of the primary. We had the labelling and were calling it isolation.

WHY A SOCKET AND NOT A FILE (deepseek's correction to my first design)
----------------------------------------------------------------------
A control FILE shares the disk with the sqlite store, the boot scripts and agent_cli. If the
disk stalls, the control thread blocks in open() and the wedge MOVES rather than escapes -- one
shared failure domain swapped for another. A loopback socket shares nothing with the bus: no
Redis, no wslrelay, no Docker NAT, no disk. And accept() is interrupt-driven, so there is no
polling thread to burn a core -- our corpus already records a poller doing exactly that.

WHY THE PORT IS DERIVED AND NOT REGISTERED
-------------------------------------------
A registry is state, and stale state is this system's worst failure class -- a 44h-old suite
baseline, a 45h cursor, derived docs stale on three consecutive commits. So the port is a pure
function of the agent name: no table to write, nothing to go stale, and any process can compute
where an agent listens without asking anything.

WHAT THIS CANNOT DO, stated because overselling it would be worse than not building it
--------------------------------------------------------------------------------------
It CANNOT unblock a thread already stuck in recv(). A Python thread blocked in a C-level read
cannot be interrupted by another Python thread, and signals are not reliable here (Python
retries after EINTR). So the ceiling is: detect -> exit cleanly -> the daemon relaunches ->
messages redeliver (the cursor was never advanced, so RB-26 redelivery applies).

That is fast RESTART, not live recovery of the running loop. deepseek's framing: the difference
between a human noticing at hour 45 and the system noticing at hour 6. Both lose the process;
one loses 39 fewer hours of silence. True live recovery via ctypes shutdown(fd) is possible and
was judged too fragile for v1.
"""

from __future__ import annotations

import os
import socket
import threading
import time
import zlib
from typing import Dict, Optional
from collections.abc import Callable

# Loopback only, always. This is a control plane: it must never be reachable off-box.
_HOST = "127.0.0.1"
_PORT_SPAN = 100
_WINDOWS_BASE = 47100
#: Off-Windows fallback base: below Linux's ephemeral floor (32768), so no outgoing connection
#: can ever be handed one of these ports. Registered beside 47100 in config.PORT_REGISTRY.
_LOW_BASE = 27100


def _ephemeral_range():
    """This OS's range for OUTGOING connections' local ports (Linux reads it from /proc;
    Windows and macOS both default to the IANA range 49152-65535)."""
    try:
        with open("/proc/sys/net/ipv4/ip_local_port_range") as fh:
            lo, hi = (int(x) for x in fh.read().split()[:2])
            return lo, hi
    except (OSError, ValueError):
        return 49152, 65535


def _default_base() -> int:
    """47100 wherever that is outside the ephemeral range (Windows, macOS -- unchanged). On Linux
    47100-48099 sits INSIDE 32768-60999, so any Redis/HTTP client connection could be given a
    control port as its local port -- measured: the test channel's port held in TIME_WAIT by a
    connection to 16379, refusing the bind. There the base moves below the range."""
    lo, hi = _ephemeral_range()
    top = _WINDOWS_BASE + 10 * _PORT_SPAN  # tests use base+900.., leave headroom
    return _LOW_BASE if (_WINDOWS_BASE <= hi and top >= lo) else _WINDOWS_BASE


CONTROL_PORT_BASE = int(os.getenv("AKASHIC_CONTROL_PORT_BASE", "") or _default_base())


def port_for(agent: str) -> int:
    """The control port for an agent -- a pure function of the name.

    Deterministic on purpose: no registry, no lookup, nothing to go stale. crc32 rather than
    hash() because Python's hash() is randomised per process (PYTHONHASHSEED), so two
    processes would disagree about where the same agent listens -- which is precisely the
    stale-mapping failure this design exists to avoid.
    """
    return CONTROL_PORT_BASE + (zlib.crc32(str(agent).encode("utf-8")) % _PORT_SPAN)


class ControlChannel:
    """A tiny line-oriented control server on loopback, one per agent.

    Protocol is deliberately trivial -- one line in, one line out -- so it can be driven by
    anything, including a shell one-liner, when nothing else about the process is working.
    """

    def __init__(self, agent: str, *, port: int | None = None):
        self.agent = str(agent)
        self.port = int(port or port_for(self.agent))
        self._handlers: dict[str, Callable[[str], str]] = {}
        self._sock: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.started_at: float | None = None
        self.last_command: str | None = None
        self.last_command_at: float | None = None
        self._register_builtins()

    # ---------------------------------------------------------------- handlers
    def register(self, verb: str, fn: Callable[[str], str]) -> None:
        self._handlers[verb.strip().lower()] = fn

    def _register_builtins(self) -> None:
        def _ping(_arg: str) -> str:
            # The point of ping is that it proves THIS thread is alive even when the main loop
            # is not -- the exact discrimination nobody could make during the kimi wedge.
            up = int(time.time() - (self.started_at or time.time()))
            return f"pong agent={self.agent} pid={os.getpid()} control_uptime_s={up}"

        def _help(_arg: str) -> str:
            return "verbs: " + " ".join(sorted(self._handlers))

        self.register("ping", _ping)
        self.register("help", _help)

    # ---------------------------------------------------------------- lifecycle
    def start(self) -> bool:
        """Bind and serve. Returns False if the port is taken -- LOUDLY, never silently.

        A bind failure usually means another instance of this agent is already running, which
        is exactly the condition a caller wants to know about rather than have papered over.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Do NOT mask a conflict -- which needs opposite settings per OS. On Windows
            # SO_REUSEADDR lets a second socket steal a port that is LIVE, so it stays off. On
            # POSIX it only permits reusing a port in TIME_WAIT (a live listener still refuses
            # the bind), and leaving it off made a restarted runner's control port unbindable
            # for ~60s after the previous one closed.
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0 if os.name == "nt" else 1)
            s.bind((_HOST, self.port))
            s.listen(4)
            s.settimeout(1.0)  # so stop() is responsive; accept still blocks, briefly
            self._sock = s
        except OSError as e:
            print(
                f"[control] {self.agent}: cannot bind {_HOST}:{self.port} -- {e}. Another instance may already hold it."
            )
            return False

        self.started_at = time.time()
        self._thread = threading.Thread(target=self._serve, name=f"control-{self.agent}", daemon=True)
        self._thread.start()
        print(
            f"[control] {self.agent}: out-of-band control on {_HOST}:{self.port} "
            f"(verbs: {' '.join(sorted(self._handlers))})"
        )
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._sock is not None:
            # shutdown() first: on Linux, close() from this thread does NOT wake the serve
            # thread blocked in accept(), so the socket kept LISTENING until the accept
            # timeout and a quick restart could not bind. shutdown() wakes it (Windows aborts
            # the accept on close alone, so this is a no-op difference there).
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2.0)

    # ---------------------------------------------------------------- serving
    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _addr = self._sock.accept()
            except TimeoutError:
                continue
            except OSError:
                break  # socket closed under us -> done
            try:
                conn.settimeout(5.0)
                raw = conn.recv(4096).decode("utf-8", "replace").strip()
                reply = self._dispatch(raw)
                conn.sendall((reply + "\n").encode("utf-8"))
            except Exception as e:
                try:
                    conn.sendall(f"ERR {type(e).__name__}: {e}\n".encode())
                except Exception:
                    pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    def _dispatch(self, line: str) -> str:
        if not line:
            return "ERR empty"
        verb, _, arg = line.partition(" ")
        fn = self._handlers.get(verb.strip().lower())
        self.last_command, self.last_command_at = line, time.time()
        if fn is None:
            return f"ERR unknown verb {verb!r}; try 'help'"
        try:
            return str(fn(arg.strip()))
        except Exception as e:
            return f"ERR {type(e).__name__}: {e}"


# -------------------------------------------------------------------- client
def send(agent: str, command: str, *, timeout: float = 3.0, port: int | None = None) -> str | None:
    """Speak to an agent's control channel. None when nobody is listening.

    None is the honest answer for 'no control channel' and is NOT the same as an error reply --
    a caller must be able to tell 'the agent has no listener' from 'the agent refused'. That
    distinction is the empty-versus-error collapse this codebase has been removing all week.
    """
    p = int(port or port_for(agent))
    try:
        with socket.create_connection((_HOST, p), timeout=timeout) as s:
            s.sendall((command.strip() + "\n").encode("utf-8"))
            s.settimeout(timeout)
            return s.recv(8192).decode("utf-8", "replace").strip()
    except OSError:
        return None
