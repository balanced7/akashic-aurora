"""The embedded bus server must not be a code-execution door (core/foundation/embedded_redis.py).

WHY THIS EXISTS (2026-10-20). fakeredis builds its Lua runtime with lupa's defaults -- the
`python` bridge left on (`python.eval`) and Lua's own `os`/`io`/`require`/`loadstring` libraries
open -- so an unguarded embedded server lets any client run `EVAL "return python.eval(...)" 0`
and execute arbitrary Python inside the bus-owner's process. Every local process, and every
Docker Desktop container (whose host traffic arrives from 127.0.0.1), could reach it. fakeredis
also `pickle.loads` the bytes a client hands to RESTORE, a second arbitrary-code path.

WHAT IS PINNED. On a throwaway embedded server (never the live 16379):
  * the dangerous Lua globals -- python, os, io, require, loadstring, load, dofile, loadfile,
    package -- are all `nil`, so a script cannot reach Python or the host;
  * the house's own Lua scripts (CAS, cursor advance, settle, role-commit) and the Lua a script
    legitimately needs (redis.call, tonumber, string/table) still run;
  * RESTORE round-trips a value the house itself DUMPed (what core/world_seed.copy_prefix does),
    but refuses a pickle that reaches outside fakeredis's own value types.

These are RED before the embedded_redis hardening and GREEN after; nothing here touches the
live server on 16379 or any ~/.aurora state (own throwaway port > 16400 + own data dir).
"""

from __future__ import annotations

import hashlib
import os
import pickle
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("fakeredis")
redis = pytest.importorskip("redis")


def _free_port_above(floor: int = 16400) -> int:
    """A free TCP port strictly above `floor`, so a scratch server can never land on the world
    port 16379 even by coincidence."""
    for _ in range(50):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        if port > floor:
            return port
    pytest.skip("could not find a free port above the floor")


def _up(port: int, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), 0.2).close()
            return True
        except OSError:
            time.sleep(0.05)
    return False


@pytest.fixture
def client(tmp_path):
    """A real embedded server subprocess on a throwaway port + data dir, and a redis-py client
    to it. Exercises the deployed serve() path, so the hardening is pinned where it ships."""
    port = _free_port_above()
    assert port != 16379, "scratch server must never use the live world port"
    env = dict(os.environ, AKASHIC_EMBEDDED_REDIS_DIR=str(tmp_path), PYTHONPATH=str(ROOT))
    proc = subprocess.Popen(
        [sys.executable, "-m", "core.foundation.embedded_redis", "--port", str(port)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not _up(port):
            raise RuntimeError("embedded server did not come up")
        yield redis.Redis(port=port, socket_timeout=10)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# -- the Lua sandbox: the escape hatches are gone -------------------------------------------

# Every global that reaches Python (lupa's bridge) or the host/filesystem (Lua's own libraries)
# or dynamic code loading. `type(x)` is "nil" exactly when the name is unbound.
_FORBIDDEN_GLOBALS = [
    "python",  # lupa bridge: python.eval / python.builtins -> arbitrary Python
    "os",  # os.execute / os.getenv -> shell + environment
    "io",  # io.open / io.popen -> filesystem + subprocess
    "require",  # module loader -> can pull a Python module back in
    "loadstring",  # compile a string into a callable (Lua 5.1)
    "load",  # the 5.2+ sibling of loadstring
    "dofile",  # run a file
    "loadfile",  # compile a file
    "package",  # package.loadlib -> load an arbitrary C library
]


@pytest.mark.parametrize("name", _FORBIDDEN_GLOBALS)
def test_dangerous_lua_global_is_nil(client, name):
    """Each escape-hatch global is unbound in the embedded server's Lua runtime."""
    assert client.eval(f"return type({name})", 0) == b"nil"


def test_indexing_the_python_bridge_fails(client):
    """Beyond `type` being nil: actually reaching for the bridge raises, so a script cannot get
    at Python (not merely find the name rebindable). `python` is nil, so indexing it is a Lua
    error -- which fakeredis's TcpFakeServer reports, for ANY nil-value index, by dropping the
    connection rather than with a -ERR reply. Either way no Python runs, and the server lives on
    to serve the next client."""
    with pytest.raises((redis.exceptions.ResponseError, redis.exceptions.ConnectionError)):
        client.eval("return python.eval", 0)
    # The escape failed WITHOUT taking the bus down: the pool reconnects and the server answers.
    assert client.eval("return type(python)", 0) == b"nil"


# -- legitimate Lua still works -------------------------------------------------------------


def test_redis_call_and_tonumber_still_work(client):
    """The Lua a real script actually uses -- redis.call, tonumber, string -- is untouched."""
    assert client.eval("redis.call('SET', KEYS[1], ARGV[1]) return redis.call('GET', KEYS[1])", 1, "k", "v") == b"v"
    assert client.eval("return tonumber(ARGV[1]) + 1", 0, "41") == 42
    assert client.eval("return string.upper(ARGV[1])", 0, "hi") == b"HI"


def test_the_houses_own_lua_scripts_run(client):
    """The five Lua scripts the house ships still behave on the hardened runtime."""
    from core.comm.expectations import _SETTLE_LUA
    from core.comm.role_queue import _COMMIT_LUA
    from core.foundation.store import RedisStore

    # store CAS: swaps the value only when the witness matches.
    client.set("cas", "old")
    assert client.eval(RedisStore._CAS_LUA, 1, "cas", "old", "new") == 1
    assert client.get("cas") == b"new"
    assert client.eval(RedisStore._CAS_LUA, 1, "cas", "old", "nope") == 0

    # role-queue commit fence: deletes the fence only when the token matches.
    client.set("fence", "tok")
    assert client.eval(_COMMIT_LUA, 1, "fence", "tok") == 1
    assert client.exists("fence") == 0

    # expectations settle: writes the settled marker (NX) and clears the pending field.
    client.hset("pending", "oid", "1")
    assert client.eval(_SETTLE_LUA, 2, "settled", "pending", "oid", "30") == 1
    assert client.get("settled") == b"1"
    assert client.hexists("pending", "oid") == 0


def test_bus_advance_lua_runs(client):
    """The bus cursor-advance guard (generation-fenced HSET) still commits on the server."""
    from core.comm.bus import Bus

    key = "cursor:test"
    res = client.eval(Bus._ADVANCE_LUA, 1, key, 0, "shared", "100")
    assert res is not None
    assert client.hget(key, "shared") == b"100"


# -- RESTORE is not a pickle door -----------------------------------------------------------


def test_restore_round_trips_a_house_dump(client):
    """What core/world_seed.copy_prefix does -- DUMP a key, RESTORE it elsewhere -- must keep
    working for every type the knowledge plane holds."""
    client.set("s", "value")
    client.rpush("l", "a", "b")
    client.hset("h", mapping={"f": "v"})
    client.zadd("z", {"m": 1.5})
    for src, check in [
        ("s", lambda d: client.get(d) == b"value"),
        ("l", lambda d: client.lrange(d, 0, -1) == [b"a", b"b"]),
        ("h", lambda d: client.hget(d, "f") == b"v"),
        ("z", lambda d: client.zscore(d, "m") == 1.5),
    ]:
        payload = client.dump(src)
        assert payload is not None
        client.restore(src + "_copy", 0, payload, replace=True)
        assert check(src + "_copy")


def test_restore_refuses_a_pickle_outside_fakeredis_value_types(client):
    """A crafted RESTORE payload whose pickle reaches outside fakeredis's own value classes is
    refused. The payload here is a benign reference to the builtin `print` (never called) -- it
    only proves the server will not resolve a global from an arbitrary module, which is the
    gate that stops a reduce-based payload from running code."""
    evil = pickle.dumps(print)  # a GLOBAL ref to builtins.print: outside the value-type safelist
    framed = hashlib.sha1(evil).digest() + evil  # fakeredis's DUMP framing: sha1 then the pickle
    with pytest.raises(redis.exceptions.ResponseError):
        client.restore("danger", 0, framed, replace=True)
