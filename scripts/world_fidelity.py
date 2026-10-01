"""What this checkout can and cannot do, before you find out by failing.

    py scripts/world_fidelity.py

Run it from the checkout you are about to work in. Every probe is scoped to where you are
standing -- the W156h incident was a tool whose two planes disagreed about that, so this one
takes no world argument at all.

Written after losing time twice in one day to a twin being silently INCAPABLE rather than
wrong: once to suite failures caused by files the source carries uncommitted, once to a
five-branch model fanout that died at the door because `.secrets/` is gitignored and a clone
carries none. Neither was a bug. Both were discoverable in one command, if the command had
existed.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.coord import world_fidelity as F  # noqa: E402
from core.paths import repo_root  # noqa: E402
from core.world import checkout_of, current  # noqa: E402

ROOT = repo_root()
#: Where each world's checkout lives, so the CODE plane can compare against its source.
#: Both twins are seeded from prod, whose checkout is derived rather than pinned to a drive.
SOURCES = {"beta": str(checkout_of("prod")), "alpha": str(checkout_of("prod"))}


def _count(path: Path):
    """0 when the directory is ABSENT, None only when it exists and cannot be read.

    Collapsing those two into None reported `.secrets/` as "unknown -- could not read" in a
    twin where it definitively does not exist. Understating a known absence is the opposite
    of this tool's job: unknown is for what could not be established, never for what was.
    """
    if not path.exists():
        return 0
    try:
        return len(list(path.iterdir()))
    except OSError:
        return None


def _git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
        if r.returncode != 0:
            return None
        return r.stdout.decode("utf-8", "replace").strip()
    except OSError:
        return None


def main() -> int:
    w = current()
    source = SOURCES.get(w.name)

    head = _git(ROOT, "rev-parse", "--short", "HEAD")
    dirty = None
    if source and Path(source).exists():
        # The SOURCE's uncommitted count, not this checkout's: a twin cannot contain what
        # the source never committed, so the source's dirt is a property of THIS twin's
        # fidelity. Measuring the wrong tree here would invert the finding.
        st = _git(source, "status", "--porcelain")
        if st is not None:
            dirty = len([l for l in st.splitlines() if l and not l.lstrip().startswith("??")])
    elif w.name == "prod":
        dirty = 0  # prod IS the source; nothing lags it

    seeded_from = None
    try:
        import redis

        from core.foundation.redis_connection import probe_redis_reachable
        from core.world_seed import read_manifest

        # Same 48s trap as agent_cli._boot_world_line(). A connect timeout does NOT fix it --
        # measured 2026-09-27: socket_connect_timeout=2 still cost 47.95s and =1 cost 26.13s,
        # because redis-py retries per resolved address. Only the probe bounds it, at 1.02s.
        if not probe_redis_reachable("localhost", w.redis_port):
            raise ConnectionError(f"world {w.name!r} store at {w.redis_port} is not reachable")
        m = read_manifest(
            redis.Redis(host="localhost", port=w.redis_port, db=w.redis_db, socket_timeout=2, socket_connect_timeout=2)
        )
        seeded_from = (m or {}).get("source_world")
    except Exception:
        seeded_from = None

    tracked_ok = None
    tracked = _git(ROOT, "ls-files", "state/")
    if tracked is not None:
        wanted = [l for l in tracked.splitlines() if l.strip()]
        tracked_ok = bool(wanted) and all((ROOT / w).exists() for w in wanted)

    rows = F.assess(
        root=str(ROOT),
        secrets_count=_count(ROOT / ".secrets"),
        state_count=_count(ROOT / "state"),
        head_sha=head,
        source_dirty=dirty,
        seeded_from=seeded_from,
        is_source=(w.name == "prod"),
        tracked_state_present=tracked_ok,
    )
    print(F.render(rows, world=w.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
