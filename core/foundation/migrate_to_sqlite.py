"""JSON FileStore -> SqliteStore migration: shadow-build, census law, honest verify.

REWRITTEN 2026-07-28 (T118, fleet-poll winner) after the first form shipped three
reproduced defects (codex_explain's fence, note codex-b-defect-map-2026-07-28):
upsert-into-existing-target kept ghost keys under "VERIFY OK" (D1), verify() walked
only the source so it could not say no (D2), and already-expired keys were written
then never expired -- resurrection with a straight face (D3).

THE THREE LAWS THIS FORM ENFORCES
  SHADOW, NEVER MERGE   the target is built FRESH at <db>.shadow and atomically
                        swapped in only after verify passes. An existing .db is
                        displaced to <db>.pre.<stamp>, never upserted into. There is
                        no code path that merges into a store already holding data.
  CENSUS IS TERMINAL    per-bucket, written + skipped_expired must equal source, and
                        a bidirectional verify must pass, or the shadow is deleted
                        and the exit is nonzero. No half-artifact survives failure.
  EXPIRED MEANS ABSENT  a source key whose __expiry__ is in the past is not data; it
                        is a tombstone. It is skipped at build (counted, reported)
                        and verify treats its presence in the target as a defect.

ROLLBACK, STATED HONESTLY: the JSON source is never touched here, so rolling back at
the cutover instant is selecting the file backend again. Post-flip writes are covered
by the sqlite-era close() echo (SqliteStore.echo_json_path, T118 D4) plus the
dual-authority checker watching the twins' freshness -- NOT by pretending an untouched
snapshot stays current forever, which is what the previous docstring claimed.

    py -m core.foundation.migrate_to_sqlite --check     # report only, writes nothing
    py -m core.foundation.migrate_to_sqlite             # shadow-build + swap + verify
    py -m core.foundation.migrate_to_sqlite --verify    # re-compare both stores
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

from core.foundation.sqlite_store import SqliteStore

def _repo_root_str() -> str:
    """AI_SETUP override, else the root DERIVED from this file (core/paths).

    Was os.getenv("AI_SETUP", <hardcoded absolute path>). The default was a
    specific machine's path, and AI_SETUP was never actually set anywhere -- so
    every call here silently used that literal and the repo only ran from one
    directory on one disk.
    """
    from core.paths import root_str
    import os as _os
    return (_os.getenv("AI_SETUP") or "").strip() or root_str()


_BUCKETS = ("kv", "hash", "list", "set", "zset")


def _default_json() -> Path:
    return Path(_repo_root_str()) / "session_logs" / "store_state.json"


def _default_db() -> Path:
    return Path(_repo_root_str()) / "session_logs" / "store_state.db"


def load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def census(data: Dict) -> Dict[str, int]:
    return {b: len(data.get(b, {}) or {}) for b in _BUCKETS}


def _expired_keys(data: Dict, now: float) -> set:
    """Keys whose __expiry__ lies in the past: tombstones, not data."""
    return {k for k, ts in (data.get("__expiry__") or {}).items() if float(ts) <= now}


def _drop_sidecars(db_path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()


def migrate(json_path: Path, db_path: Path) -> Tuple[Dict[str, int], Dict[str, int], Dict[str, int]]:
    """Shadow-build the target and swap it in. Returns (live source census,
    written census, skipped-expired census); the caller enforces the census law.

    Raises SystemExit on any violated invariant, after deleting the shadow --
    failure leaves the previous target exactly as it was.
    """
    json_path, db_path = Path(json_path), Path(db_path)
    now = time.time()
    data = load_json(json_path)
    dead = _expired_keys(data, now)

    live: Dict = {b: {k: v for k, v in (data.get(b) or {}).items() if k not in dead}
                  for b in _BUCKETS}
    src = census(live)
    skipped = {b: len((data.get(b) or {})) - len(live[b]) for b in _BUCKETS}

    shadow_path = Path(str(db_path) + ".shadow")
    if shadow_path.exists():
        shadow_path.unlink()
    _drop_sidecars(shadow_path)

    store = SqliteStore(str(shadow_path))
    if not store.is_available():
        raise SystemExit(f"[migrate] REFUSING: shadow store unavailable at {shadow_path}")

    try:
        for k, v in live["kv"].items():
            store.set(k, v)
        for k, fields in live["hash"].items():
            if fields:
                store.hset(k, mapping={f: str(val) for f, val in fields.items()})
        for k, items in live["list"].items():
            if items:
                store.rpush(k, *[str(i) for i in items])
        for k, members in live["set"].items():
            if members:
                store.sadd(k, *[str(m) for m in members])
        for k, scored in live["zset"].items():
            if scored:
                store.zadd(k, {str(m): float(s) for m, s in scored.items()})

        # Absolute timestamps preserved; only future expiries are written at all --
        # past ones were dropped from `live` above, so nothing exists to resurrect.
        for k, expires_at in (data.get("__expiry__") or {}).items():
            if k in dead:
                continue
            remaining = float(expires_at) - now
            if remaining > 0 and store.exists(k):
                store.expire(k, max(1, int(remaining)))

        written = {b: _count(store, t) for b, t in
                   zip(_BUCKETS, ("kv", "hash", "list", "set_members", "zset"))}

        if written != src:
            raise SystemExit(f"[migrate] CENSUS VIOLATION -- source(live) {src} != "
                             f"written {written}; shadow deleted, target untouched")

        # Quiesce assert (codex: counts moved during the live census probe): if the
        # source advanced while the shadow was building, the shadow is already stale.
        recheck = load_json(json_path)
        if recheck != data:
            raise SystemExit("[migrate] SOURCE MOVED during shadow build -- quiesce "
                             "writers first; shadow deleted, target untouched")
    except BaseException:
        store.close()
        if shadow_path.exists():
            shadow_path.unlink()
        _drop_sidecars(shadow_path)
        raise

    store.close()  # checkpoints; shadow is a complete, self-contained .db
    _drop_sidecars(shadow_path)

    if db_path.exists():
        displaced = Path(f"{db_path}.pre.{int(now)}")
        os.replace(db_path, displaced)
        # The displaced db's sidecars must not survive under the target name -- a new
        # .db next to an old -wal is exactly the corrupt-restore shape backup_to warns
        # about, one directory over.
        _drop_sidecars(db_path)
    os.replace(shadow_path, db_path)
    return src, written, skipped


def _count(store: SqliteStore, table: str) -> int:
    return store._conn.execute(f"SELECT COUNT(DISTINCT key) FROM {table}").fetchone()[0]


def verify(json_path: Path, db_path: Path) -> Tuple[bool, list]:
    """BIDIRECTIONAL, value-level comparison. Forward: every live source value equal
    in the target (a logically expired source key must instead be ABSENT). Backward:
    every target key, member, and expiry row must be claimed by the live source --
    target-only data is named per structure, never sailed past (T118 D2: a verifier
    that only walks the source cannot say no)."""
    json_path, db_path = Path(json_path), Path(db_path)
    now = time.time()
    data = load_json(json_path)
    dead = _expired_keys(data, now)
    store = SqliteStore(str(db_path))
    problems: List[str] = []

    try:
        # ---- forward: live source values present and equal; expired absent ----
        for k, v in (data.get("kv") or {}).items():
            if k in dead:
                if store.get(k) is not None:
                    problems.append(f"kv[{k}]: expired in source but PRESENT in db")
                continue
            if store.get(k) != v:
                problems.append(f"kv[{k}]: json={v!r} db={store.get(k)!r}")
        for k, fields in (data.get("hash") or {}).items():
            if k in dead:
                if store.hgetall(k):
                    problems.append(f"hash[{k}]: expired in source but PRESENT in db")
                continue
            got = store.hgetall(k)
            if {f: str(x) for f, x in (fields or {}).items()} != got:
                problems.append(f"hash[{k}]: {len(fields or {})} fields vs {len(got)}")
        for k, items in (data.get("list") or {}).items():
            if k in dead:
                continue
            got = store.lrange(k, 0, -1)
            if [str(i) for i in (items or [])] != got:
                problems.append(f"list[{k}]: {len(items or [])} items vs {len(got)}")
        for k, members in (data.get("set") or {}).items():
            if k in dead:
                continue
            got = store.smembers(k)
            if {str(m) for m in (members or [])} != got:
                problems.append(f"set[{k}]: {len(members or [])} vs {len(got)}")
        for k, scored in (data.get("zset") or {}).items():
            if k in dead:
                continue
            for m, s in (scored or {}).items():
                if store.zscore(k, m) != float(s):
                    problems.append(f"zset[{k}][{m}]: {s} vs {store.zscore(k, m)}")
                    break

        # ---- backward: nothing in the target the live source does not claim ----
        snap = store.snapshot()
        for bucket in _BUCKETS:
            src_keys = {k for k in (data.get(bucket) or {}) if k not in dead}
            for k in snap[bucket]:
                if k not in src_keys:
                    problems.append(f"{bucket}[{k}]: target-only (source does not hold it)")
        live_expiry = {k for k, ts in (data.get("__expiry__") or {}).items()
                       if k not in dead and float(ts) > now}
        for k in snap["expiry"]:
            if k not in live_expiry:
                problems.append(f"expiry[{k}]: target-only expiry row")
    finally:
        store.close()
    return (not problems), problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", default=None, help="source JSON store")
    ap.add_argument("--db", default=None, help="target SQLite store")
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    ap.add_argument("--verify", action="store_true", help="compare an existing migration")
    a = ap.parse_args(argv)

    json_path = Path(a.json) if a.json else _default_json()
    db_path = Path(a.db) if a.db else _default_db()

    print(f"[migrate] source : {json_path}")
    print(f"[migrate] target : {db_path}")

    if not json_path.exists():
        print("[migrate] source does not exist -- nothing to migrate")
        return 0

    if a.check:
        data = load_json(json_path)
        c = census(data)
        dead = len(_expired_keys(data, time.time()))
        print(f"[migrate] would shadow-build: {c}  (total keys {sum(c.values())}, "
              f"of which {dead} expired tombstone(s) will be dropped)")
        print("[migrate] --check writes nothing; the source is never modified by any mode")
        return 0

    if a.verify:
        ok, problems = verify(json_path, db_path)
        if ok:
            print("[migrate] VERIFY OK -- bidirectional: every live JSON value present in "
                  "SQLite, nothing in SQLite the JSON does not claim")
            return 0
        print(f"[migrate] VERIFY FAILED -- {len(problems)} divergence(s):")
        for p in problems[:20]:
            print(f"  {p}")
        return 1

    src, written, skipped = migrate(json_path, db_path)
    print(f"[migrate] live source census : {src}")
    print(f"[migrate] written census     : {written}")
    if any(skipped.values()):
        print(f"[migrate] expired tombstones dropped: {skipped}")
    ok, problems = verify(json_path, db_path)
    if not ok:
        print(f"[migrate] REFUSING TO CLAIM SUCCESS -- {len(problems)} divergence(s):")
        for p in problems[:20]:
            print(f"  {p}")
        return 1
    print("[migrate] OK -- shadow-built, swapped, verified bidirectionally. The JSON "
          "source is untouched; the sqlite era echoes state back to it on close, and "
          "check_dual_authority watches the twins.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
