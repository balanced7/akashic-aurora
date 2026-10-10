"""embedded_redis -- a Redis-compatible server in pure Python, persisted to SQLite.

WHY THIS EXISTS (2026-10-01). Memory (lessons, notes) always had a file fallback, but the
Bifrost bus -- mail, wake listeners, handoffs, presence -- speaks Redis streams directly, so a
machine without a Redis server had no bus at all: every listener exited "bus OFFLINE". Aurora
must run on Python and its pip dependencies alone, on Windows and Linux alike.

THE SHAPE. Not a second implementation of the bus. A stand-in SERVER: fakeredis (a faithful
pure-Python Redis, including streams, consumer groups, Lua via lupa and pub/sub) served over
TCP on the world's own Redis port. Every client in the house -- redis-py through
connect_to_redis_with_fail_fast, the scripts that dial redis.Redis(...) themselves, hooks in
short-lived processes -- keeps talking Redis protocol and cannot tell the difference. Blocking
reads block for real (no polling loop to tune), because the server is one process.

DURABILITY. fakeredis keeps data in memory, so the server persists every key a WRITE command
touched (Redis's own `write` flag, which covers XREADGROUP/XACK/XAUTOCLAIM consumer-group state,
and every redis.call inside a Lua script) to SQLite, flushed every FLUSH_INTERVAL. It stores
effects (pickled values), never commands: replaying `XADD *` would mint NEW stream ids and
orphan every bus cursor. A crash loses at most one flush interval, which is tighter than the
default RDB policy the Docker Redis ran with.

WHO STARTS IT. Nobody by hand: connect_to_redis_with_fail_fast() calls ensure_running() when a
WORLD port (config.PORT_REGISTRY) is unreachable and this checkout's backend is `embedded`. The
first caller spawns it detached (no console window on Windows); later callers just connect.

BACKEND CHOICE, AND WHY IT IS STICKY. `AKASHIC_REDIS_BACKEND=embedded|external` wins. Unset, the
first decision is recorded in state/redis-backend: a checkout whose Redis answered at that
moment is `external` for good, so a Windows box whose Docker Redis is briefly down behaves as it
always did (goes quiet) instead of starting a second server that would split its bus in two and
squat on the port Docker needs. A checkout with no Redis is `embedded`.

    py -m core.foundation.embedded_redis --port 16379        # run in the foreground
    py -m core.foundation.embedded_redis --status            # who is serving each world port
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import os
import pickle
import signal
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("embedded_redis")

#: How often dirty keys are written to SQLite (seconds) -- the bound on what a crash can lose.
FLUSH_INTERVAL = float(os.getenv("AKASHIC_EMBEDDED_REDIS_FLUSH_SEC", "0.2") or 0.2)

_BACKENDS = ("embedded", "external")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", ""}

# Commands that rewrite whole databases rather than named keys: resync everything after them.
_FULL_RESYNC = {"flushdb", "flushall", "swapdb", "move", "copy", "restore", "debug reload"}


# ------------------------------------------------------------------------------ locations


def _repo_root() -> Path:
    try:
        from core.paths import repo_root

        return repo_root()
    except Exception:  # pragma: no cover - import guard
        return Path(__file__).resolve().parents[2]


def _shared_root() -> Path:
    try:
        from core.paths import shared_state_root

        return shared_state_root()
    except Exception:  # pragma: no cover - import guard
        return _repo_root()


def data_dir() -> Path:
    """Where the embedded server keeps its files: the world's home (shared_state_root), else beside
    the CODE (repo_root) -- never data_root():
    one server serves a world port for every process, including test runs that point AI_SETUP
    at a throwaway tree -- they isolate on db 15, exactly as they did against Docker Redis."""
    override = (os.getenv("AKASHIC_EMBEDDED_REDIS_DIR") or "").strip()
    return Path(override) if override else _shared_root() / "state" / "redis-embedded"


def data_file(port: int) -> Path:
    return data_dir() / f"{int(port)}.sqlite3"


def _marker() -> Path:
    return _shared_root() / "state" / "redis-backend"


# ------------------------------------------------------------------------------ backend choice


def available() -> bool:
    """True when the pure-Python server can run here (fakeredis installed)."""
    try:
        import fakeredis  # noqa: F401  # availability probe

        return True
    except Exception:
        return False


def configured_backend() -> str | None:
    """The backend already decided for this checkout, or None if nothing decided yet."""
    env = (os.getenv("AKASHIC_REDIS_BACKEND") or "").strip().lower()
    if env in _BACKENDS:
        return env
    try:
        raw = _marker().read_text(encoding="utf-8").strip().lower()
    except OSError:
        return None
    return raw if raw in _BACKENDS else None


def record_backend(reachable: bool) -> str:
    """Decide once and remember: an answering Redis makes this checkout `external`, none makes
    it `embedded`. Returns the backend in force (an existing decision always wins)."""
    decided = configured_backend()
    if decided:
        return decided
    choice = "external" if (reachable or _has_redis_container()) else "embedded"
    try:
        _marker().parent.mkdir(parents=True, exist_ok=True)
        _marker().write_text(choice + "\n", encoding="utf-8")
    except OSError:  # read-only tree: decide per call
        pass
    return choice


def _has_redis_container() -> bool:
    """A Docker container for Aurora's Redis exists on this machine (running or not). Asked only
    on the very first decision: a checkout whose Docker Redis happens to be stopped at that
    moment is still an `external` checkout, and an embedded server squatting on its port would
    stop that container from ever starting again."""
    import shutil

    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        r = subprocess.run(
            [docker, "ps", "-a", "--filter", "name=akashic-redis", "-q"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


def is_world_port(port: int) -> bool:
    """A declared world port (config.PORT_REGISTRY). Test suites dial throwaway ports on
    purpose to exercise the Redis-down path; conjuring a server there would erase it."""
    try:
        from core.world import owner_of_port

        return owner_of_port(int(port)) is not None
    except Exception:
        return False


def is_own_world_port(port: int) -> bool:
    """THIS checkout's world port -- the only one it may start a server for. Another world's
    data lives in that world's checkout; a server started here for it would be an empty twin
    squatting on its port. An UNKNOWN checkout owns no port, so it never starts one."""
    try:
        from core.world import current

        return current().redis_port == int(port)
    except Exception:
        return False


# ------------------------------------------------------------------------------ persistence


class _Persistence:
    """Dirty-key tracking plus a flusher thread that mirrors those keys into SQLite."""

    def __init__(self, fake_server, path: Path):
        self.server = fake_server
        self.path = path
        self._dirty: set[tuple[int, bytes]] = set()  # (id(Database), key)
        self._full = False
        self._mu = threading.Lock()
        self._stop = threading.Event()
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS kv (db INTEGER, key BLOB, item BLOB, PRIMARY KEY (db, key))")

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.path), timeout=30)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        return c

    def load(self) -> int:
        now = time.time()
        n = 0
        with self._conn() as c:
            rows = c.execute("SELECT db, key, item FROM kv").fetchall()
        for db, key, blob in rows:
            try:
                item = pickle.loads(blob)
            except Exception as e:  # a corrupt row costs one key
                logger.warning("skipping unreadable key %r in db %s: %s", key, db, e)
                continue
            exp = getattr(item, "expireat", None)
            if exp is not None and exp <= now:
                continue
            self.server.dbs[int(db)][bytes(key)] = item
            n += 1
        return n

    def mark(self, db_obj, key: bytes) -> None:
        with self._mu:
            self._dirty.add((id(db_obj), bytes(key)))

    def mark_all(self) -> None:
        with self._mu:
            self._full = True

    def flush(self) -> None:
        with self._mu:
            dirty, self._dirty = self._dirty, set()
            full, self._full = self._full, False
        if not dirty and not full:
            return
        upserts, deletes = [], []
        with self.server.lock:  # a consistent cut: no command runs mid-snapshot
            by_id = {id(d): (n, d) for n, d in self.server.dbs.items()}
            if full:
                for n, d in by_id.values():
                    upserts.extend((n, key, pickle.dumps(d._dict[key], protocol=4)) for key in list(d._dict))
            else:
                for db_id, key in dirty:
                    if db_id not in by_id:
                        continue
                    n, d = by_id[db_id]
                    item = d._dict.get(key)
                    if item is None:
                        deletes.append((n, key))
                    else:
                        upserts.append((n, key, pickle.dumps(item, protocol=4)))
        with self._conn() as c:
            if full:
                c.execute("DELETE FROM kv")
            c.executemany("DELETE FROM kv WHERE db=? AND key=?", deletes)
            c.executemany("INSERT OR REPLACE INTO kv (db, key, item) VALUES (?,?,?)", upserts)

    def run(self) -> None:
        while not self._stop.wait(FLUSH_INTERVAL):
            try:
                self.flush()
            except Exception as e:  # never kill the flusher
                logger.error("flush failed: %s", e)

    def stop(self) -> None:
        self._stop.set()
        self.flush()


_PERSIST: _Persistence | None = None


def _install_hooks() -> None:
    """Teach fakeredis to report what each command touched, and add the commands it lacks."""
    import fakeredis._basefakesocket as bfs
    import fakeredis._commands as cmds
    from fakeredis._commands import command

    if getattr(bfs.BaseFakeSocket, "_aurora_hooked", False):
        return
    write_cmds = _write_commands()
    current = threading.local()

    orig_run = bfs.BaseFakeSocket._run_command

    def _run_command(self, func, sig, args, from_script):
        args = _complete_range_end(sig.name, args)
        prev = getattr(current, "write", False)
        current.write = sig.name in write_cmds
        try:
            return orig_run(self, func, sig, args, from_script)
        finally:
            current.write = prev
            if _PERSIST is not None and sig.name in _FULL_RESYNC:
                _PERSIST.mark_all()

    orig_writeback = cmds.CommandItem.writeback

    def writeback(self, remove_empty_val: bool = True):
        touched = self._modified or self._expireat_modified or getattr(current, "write", False)
        orig_writeback(self, remove_empty_val)
        if _PERSIST is not None and touched:
            _PERSIST.mark(self.db, self.key)

    bfs.BaseFakeSocket._run_command = _run_command
    cmds.CommandItem.writeback = writeback

    # -- commands the house uses that fakeredis does not implement --------------------
    class _AuroraExtras:
        # Mixed into BaseFakeSocket below; these are its attributes (annotation only).
        _server: Any
        _db: Any

        @command(name="info", fixed=(), repeat=(bytes,))
        def info(self, *sections):
            dbs = {n: len(d) for n, d in self._server.dbs.items() if len(d)}
            lines = [
                "# Server",
                "redis_version:7.4.0",
                "redis_mode:standalone",
                "aurora_backend:embedded",
                f"process_id:{os.getpid()}",
                "# Clients",
                "connected_clients:1",
                "# Memory",
                "used_memory:0",
                "used_memory_human:embedded",
                "# Keyspace",
            ]
            lines += [f"db{n}:keys={k},expires=0,avg_ttl=0" for n, k in sorted(dbs.items())]
            return ("\r\n".join(lines) + "\r\n").encode()

        @command(name="touch", fixed=(bytes,), repeat=(bytes,))
        def touch(self, *keys):
            return sum(1 for k in keys if k in self._db)

    for name in ("info", "touch"):
        setattr(bfs.BaseFakeSocket, name, getattr(_AuroraExtras, name))
    bfs.BaseFakeSocket._aurora_hooked = True  # pyright: ignore[reportAttributeAccessIssue]  # idempotence marker on a third-party class


_SEQ_MAX = b"18446744073709551615"


def _complete_range_end(name: str, args):
    """Complete an INCOMPLETE stream id (bare milliseconds) used as a range's UPPER bound the way
    Redis does: `<ms>` means `<ms>-<max seq>` there. fakeredis completes it as `<ms>-0`, so
    `XREVRANGE k 1000 1000` returned only 1000-0 and silently dropped 1000-1, 1000-2 -- every
    entry written in the same millisecond. The bus's lane-twin windows query exactly that way,
    and missed twins re-delivered packets as legacy stragglers. Lower bounds are already right.
    """
    pos = 2 if name == "xrange" else 1 if name == "xrevrange" else None
    if pos is None or len(args) <= pos:
        return args
    end = args[pos]
    raw = end.encode() if isinstance(end, str) else bytes(end)
    if raw.isdigit():
        args = list(args)
        args[pos] = raw + b"-" + _SEQ_MAX
    return args


def _write_commands() -> set[str]:
    """Every command Redis flags `write`, from fakeredis's own copy of the command table
    (names as fakeredis spells them: 'xgroup create' for subcommands)."""
    import json

    import fakeredis

    table = json.loads((Path(fakeredis.__file__).parent / "commands.json").read_text("utf-8"))
    out: set[str] = set()

    def walk(entry, parent=""):
        name, flags = entry[0], entry[2]
        full = f"{parent} {name.split('|')[-1]}".strip() if parent else name
        if "write" in flags:
            out.add(full.lower())
        for sub in (entry[9] if len(entry) > 9 else []) or []:
            walk(sub, full)

    for entry in table.values():
        walk(entry)
    return out


# ------------------------------------------------------------------------------ first boot


def _seed_from_file_tier(fake_server, port: int, path: Path) -> int:
    """On an EMPTY first boot, load what the file tier already holds.

    Before this server existed, a checkout without Redis kept its memory only in the file
    tier (session_logs/store_state.json). The Hybrid store reads Redis FIRST once Redis
    answers, so an empty server would hide every lesson recorded until now. Seed once, only
    for this checkout's own world port (the file tier belongs to that world), and leave a
    marker so a later deliberate FLUSHDB is never silently undone.
    """
    marker = path.with_suffix(".seeded")
    if marker.exists():
        return 0
    try:
        from core.world import current

        if current().redis_port != port:
            return 0
        import json

        import fakeredis

        from core.foundation.redis_connection import DEFAULT_REDIS_DB
        from core.paths import state_root

        state_file = state_root() / "session_logs" / "store_state.json"
        n = 0
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            r = fakeredis.FakeRedis(server=fake_server, db=int(DEFAULT_REDIS_DB))
            p = r.pipeline(transaction=False)
            for k, v in (data.get("kv") or {}).items():
                p.set(k, v)
                n += 1
            for k, v in (data.get("hash") or {}).items():
                if v:
                    p.hset(k, mapping=v)
                    n += 1
            for k, v in (data.get("list") or {}).items():
                if v:
                    p.rpush(k, *v)
                    n += 1
            for k, v in (data.get("set") or {}).items():
                if v:
                    p.sadd(k, *v)
                    n += 1
            for k, v in (data.get("zset") or {}).items():
                if v:
                    p.zadd(k, {m: float(s) for m, s in v.items()})
                    n += 1
            now = time.time()
            for k, ts in (data.get("__expiry__") or {}).items():
                ttl = float(ts) - now
                if ttl > 0:
                    p.expire(k, max(1, int(ttl)))
                else:
                    p.delete(k)
            p.execute()
        marker.write_text(f"{n}\n", encoding="utf-8")
        return n
    except Exception as e:  # a failed seed must never stop the server
        logger.warning("seeding from the file store failed: %s", e)
        return 0


# ------------------------------------------------------------------------------ the server


def _no_delay_handler(base: Any) -> Any:
    """fakeredis writes each reply of a pipeline as its own small send. With Nagle on, the
    second waits for the ACK of the first, which the client delays ~40ms because it is only
    reading -- so EVERY pipeline of two or more commands cost ~41ms flat (measured), against
    ~0.3ms for a single command. A real Redis sets TCP_NODELAY on client sockets; so do we."""

    class _NoDelay(base):
        def setup(self):
            with contextlib.suppress(OSError):
                self.request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            super().setup()

    return _NoDelay


def serve(port: int, host: str = "127.0.0.1", path: Path | None = None) -> int:
    """Run the server in this process until SIGTERM/SIGINT or SHUTDOWN. Returns an exit code."""
    global _PERSIST
    from fakeredis import TcpFakeServer

    _install_hooks()
    path = path or data_file(port)
    try:
        srv = TcpFakeServer((host, int(port)), server_type="redis")
    except OSError as e:
        # Someone else already serves this port: the job is done, and not by us.
        logger.info("port %s:%s already taken (%s) -- not starting", host, port, e)
        return 0
    srv.daemon_threads = True
    srv.RequestHandlerClass = _no_delay_handler(srv.RequestHandlerClass)
    _PERSIST = _Persistence(srv.fake_server, path)
    loaded = _PERSIST.load()
    if loaded == 0:
        seeded = _seed_from_file_tier(srv.fake_server, int(port), path)
        if seeded:
            logger.info("first boot: seeded %d key(s) from the file store", seeded)
    flusher = threading.Thread(target=_PERSIST.run, name="embedded-redis-flush", daemon=True)
    flusher.start()
    pidfile = path.with_suffix(".pid")
    with contextlib.suppress(OSError):
        pidfile.write_text(f"{os.getpid()}\n", encoding="utf-8")
    logger.info("embedded redis on %s:%s, %d key(s) loaded from %s", host, port, loaded, path)

    def _stop(*_):
        threading.Thread(target=srv.shutdown, daemon=True).start()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(ValueError, OSError):  # not the main thread
            signal.signal(sig, _stop)
    try:
        srv.serve_forever(poll_interval=0.2)
    finally:
        _PERSIST.stop()
        srv.server_close()
        with contextlib.suppress(OSError):
            pidfile.unlink()
    return 0


def _reachable(host: str, port: int, timeout: float = 0.3) -> bool:
    try:
        socket.create_connection((host or "127.0.0.1", int(port)), timeout=timeout).close()
        return True
    except OSError:
        return False


def _spawn(port: int) -> None:
    """Start the server detached from the caller: it must outlive a one-shot hook process,
    and on Windows it must never flash a console (DETACHED_PROCESS, as scripts/run_job.py)."""
    exe = sys.executable
    if sys.platform == "win32":
        w = Path(exe).with_name("pythonw.exe")
        exe = str(w) if w.exists() else exe
    log = data_dir() / f"{int(port)}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    root = str(_repo_root())
    env["PYTHONPATH"] = root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    kwargs = {
        "cwd": root,
        "stdin": subprocess.DEVNULL,
        "stdout": open(log, "ab"),  # noqa: SIM115  # handle outlives this block: inherited by the Popen child, parent copy closed on GC
        "stderr": subprocess.STDOUT,
        "close_fds": True,
        "env": env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([exe, "-m", "core.foundation.embedded_redis", "--port", str(int(port))], **kwargs)


def ensure_running(host: str, port: int, timeout: float = 10.0) -> bool:
    """Make sure SOMETHING answers Redis on host:port, starting the embedded server if this
    checkout's backend is `embedded`. True once the port answers. Never raises."""
    try:
        if _reachable(host, port):
            return True
        if (host or "").lower() not in _LOCAL_HOSTS:
            return False  # we only ever start a server on this machine
        if not is_own_world_port(port) or not available():
            return False
        if record_backend(reachable=False) != "embedded":
            return False
        _spawn(port)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if _reachable(host, port):
                return True
            time.sleep(0.05)
        logger.warning(
            "embedded redis did not come up on %s:%s within %.0fs (see %s)",
            host,
            port,
            timeout,
            data_dir() / f"{int(port)}.log",
        )
        return False
    except Exception as e:  # pragma: no cover
        logger.warning("ensure_running failed: %s", e)
        return False


def status() -> dict[int, str]:
    """Who answers each declared world port right now."""
    out = {}
    try:
        from core.world import WORLDS

        ports = [w.redis_port for w in WORLDS.values() if w.redis_port]
    except Exception:
        ports = [16379]
    for p in ports:
        if not _reachable("127.0.0.1", p):
            out[p] = "down"
            continue
        try:
            import redis

            info = redis.Redis(port=p, socket_timeout=2).info()
            out[p] = "embedded" if info.get("aurora_backend") == "embedded" else "redis"
        except Exception as e:
            out[p] = f"answering ({type(e).__name__})"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aurora's embedded, SQLite-persisted Redis server")
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--status", action="store_true", help="report who serves each world port")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if a.status:
        print(f"backend: {configured_backend() or 'undecided'}  data: {data_dir()}")
        for p, who in status().items():
            print(f"  {p}: {who}")
        return 0
    if a.port is None:
        try:
            from core.foundation.redis_connection import DEFAULT_REDIS_PORT

            a.port = DEFAULT_REDIS_PORT
        except Exception:
            a.port = 16379
    return serve(a.port, a.host)


if __name__ == "__main__":
    raise SystemExit(main())
