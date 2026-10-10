"""client -- the JSON-RPC client for aurora-linkd, Aurora's fleet-link daemon.

Python never re-implements any part of the link protocol (RFC #70's addendum, premise P2): identity,
the ACL log, records, keys and the network all live in the Rust daemon. This module only finds the
daemon and talks to it, one JSON request per line:

- while `aurora link serve` runs, over its socket (`state/link/linkd.addr` names it: a Unix socket
  path, or a named pipe on Windows);
- otherwise by spawning a one-shot `aurora-linkd serve --stdio --no-socket [--offline]` for the call,
  which exits when we close its stdin.

Every call is checked against the generated contract (rpc_types.METHODS) before it leaves, so a
renamed parameter fails here, at the call site, not as a remote error.

Without the akashic-aurora-linkd wheel (or a dev build in aurora-rs/target), links are unavailable
and nothing else in Aurora is affected: `find_linkd()` returns None and `connect()` raises
LinkdMissing with the one-line remedy.
"""

from __future__ import annotations

import contextlib
import itertools
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from core.link.rpc_types import METHODS, NETWORK
from core.paths import data_root, repo_root

MISSING = (
    "links need the akashic-aurora-linkd package: `uv pip install akashic-aurora-linkd`, "
    "or build it with `cargo build -p aurora-linkd` in aurora-rs/"
)

_ids = itertools.count(1)


class LinkdMissing(RuntimeError):
    """The aurora-linkd binary is not installed."""


class LinkRpcError(RuntimeError):
    """The daemon refused or failed a call. `code` follows aurora-linkd's table:
    -32001 refused, -32002 unavailable, -32003 internal, -326xx JSON-RPC errors."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def state_dir(home: Path | None = None) -> Path:
    """`state/link/` under the Aurora data root: per-link stores, blobs, the socket address."""
    return (home or data_root()) / "state" / "link"


def secrets_root() -> Path:
    """The secrets folder the daemon keeps its `link/` keys in (same rule as secret_intake)."""
    from core.comm.secret_intake import secrets_dir

    return secrets_dir()


def find_linkd() -> str | None:
    """The aurora-linkd binary: $AURORA_LINKD, then PATH, then beside this Python (where the wheel
    installs it), then a dev build in aurora-rs/target (the newer of release and debug)."""
    exe = "aurora-linkd.exe" if os.name == "nt" else "aurora-linkd"
    override = (os.getenv("AURORA_LINKD") or "").strip()
    if override:
        return override if Path(override).is_file() else None
    found = shutil.which(exe)
    if found:
        return found
    beside = Path(sys.executable).parent / exe
    if beside.is_file():
        return str(beside)
    builds = [
        p
        for p in (repo_root() / "aurora-rs" / "target" / k / exe for k in ("release", "linkd", "debug"))
        if p.is_file()
    ]
    return str(max(builds, key=lambda p: p.stat().st_mtime)) if builds else None


def check_params(method: str, params: dict[str, Any]) -> None:
    """Refuse a call the contract does not allow, before it is sent."""
    if method not in METHODS:
        raise LinkRpcError(-32601, f"aurora-linkd has no method {method}")
    required, optional = METHODS[method]
    missing = [p for p in required if params.get(p) is None]
    unknown = [p for p in params if p not in required and p not in optional]
    if missing or unknown:
        raise LinkRpcError(-32602, f"{method}: missing {missing or '-'}, unknown {unknown or '-'}")


class Client:
    """One channel to a daemon. Calls are serialised: one request, then its response."""

    def __init__(self, reader: Any, writer: Any, *, close_hook=None, desc: str = ""):
        self._r = reader
        self._w = writer
        self._close_hook = close_hook
        self._lock = threading.Lock()
        self.desc = desc

    def call(self, method: str, **params: Any) -> Any:
        params = {k: v for k, v in params.items() if v is not None}
        check_params(method, params)
        req = {"jsonrpc": "2.0", "id": next(_ids), "method": method, "params": params}
        with self._lock:
            self._w.write((json.dumps(req) + "\n").encode("utf-8"))
            self._w.flush()
            line = self._r.readline()
        if not line:
            raise LinkRpcError(-32003, f"aurora-linkd closed the channel during {method}")
        resp = json.loads(line)
        if "error" in resp:
            err = resp["error"]
            raise LinkRpcError(int(err.get("code", -32003)), str(err.get("message", "")))
        return resp.get("result")

    def close(self) -> None:
        for f in (self._w, self._r):
            with contextlib.suppress(Exception):
                f.close()
        if self._close_hook:
            self._close_hook()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


#: Windows: the pipe is "busy" (ERROR_PIPE_BUSY) between one client's connect and the server
#: creating its next instance. That is a daemon at work, not a missing one.
_PIPE_BUSY = 231


def _socket_client(addr: str) -> Client | None:
    """Connect to a running daemon's socket or pipe; None when nothing answers there."""
    try:
        if os.name == "nt":
            for _ in range(100):
                try:
                    pipe = open(addr, "r+b", buffering=0)  # noqa: SIM115  # closed by Client.close
                    return Client(pipe, pipe, desc=f"pipe {addr}")
                except OSError as e:
                    if getattr(e, "winerror", None) != _PIPE_BUSY:
                        raise
                    time.sleep(0.02)
            return None
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)  # POSIX-only branch
        s.connect(addr)
        f = s.makefile("rwb", buffering=0)
        return Client(f, f, close_hook=s.close, desc=f"socket {addr}")
    except OSError:
        return None


def running_addr(home: Path | None = None) -> str | None:
    """The address of a running daemon for this data root, if one answers."""
    try:
        addr = (state_dir(home) / "linkd.addr").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    c = _socket_client(addr) if addr else None
    if c is None:
        return None
    c.close()
    return addr


def spawn_args(
    binary: str,
    home: Path,
    *,
    stdio: bool,
    socket_: bool,
    offline: bool,
    extra: list[str] | None = None,
    secrets: Path | None = None,
) -> list[str]:
    """The daemon's command line for this data root."""
    args = [binary, "--home", str(home), "--secrets", str(secrets or secrets_root()), "serve"]
    if stdio:
        args.append("--stdio")
    if not socket_:
        args.append("--no-socket")
    if offline:
        args.append("--offline")
    return args + list(extra or [])


def connect(*, network: bool = False, home: Path | None = None, secrets: Path | None = None) -> Client:
    """A channel to the daemon for this data root: the running one if there is one, else a one-shot
    child (offline unless `network`). Raises LinkdMissing when the binary is absent."""
    home = home or data_root()
    try:
        addr = (state_dir(home) / "linkd.addr").read_text(encoding="utf-8").strip()
    except OSError:
        addr = ""
    if addr:
        c = _socket_client(addr)  # one connection, not a probe and then another
        if c is not None:
            return c
    binary = find_linkd()
    if not binary:
        raise LinkdMissing(MISSING)
    proc = subprocess.Popen(
        spawn_args(binary, home, stdio=True, socket_=False, offline=not network, secrets=secrets),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    def _reap() -> None:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    if proc.stdout is None or proc.stdin is None:  # pipes were requested above; never true
        raise LinkRpcError(-32003, "aurora-linkd started without its pipes")
    return Client(proc.stdout, proc.stdin, close_hook=_reap, desc=f"one-shot pid {proc.pid}")


def call(method: str, *, home: Path | None = None, **params: Any) -> Any:
    """One call on a fresh channel. Network methods need `aurora link serve` running."""
    with connect(network=method in NETWORK or (method == "link.join" and "acl" not in params), home=home) as c:
        return c.call(method, **params)
