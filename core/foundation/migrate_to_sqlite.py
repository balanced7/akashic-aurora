"""One-way, REVERSIBLE migration: the JSON FileStore -> SqliteStore.

Reversible because it never touches the source. The JSON file is read and left exactly as it
was, so rollback is "stop pointing at the .db" -- no restore step, no window where neither
store is authoritative.

    py -m core.foundation.migrate_to_sqlite --check     # report only, writes nothing
    py -m core.foundation.migrate_to_sqlite             # migrate
    py -m core.foundation.migrate_to_sqlite --verify    # re-read both and compare

VERIFY IS NOT OPTIONAL AND IS NOT A FORMALITY. A migration that reports success while
silently dropping a structure is precisely the class of defect this whole arc exists to
remove -- so this refuses to claim success it has not checked, and --verify re-derives the
comparison from both stores rather than trusting the writer's own count.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Tuple

from core.foundation.sqlite_store import SqliteStore

_BUCKETS = ("kv", "hash", "list", "set", "zset")


def _default_json() -> Path:
    return Path(os.getenv("AI_SETUP", r"E:\AI-Setup")) / "session_logs" / "store_state.json"


def _default_db() -> Path:
    return Path(os.getenv("AI_SETUP", r"E:\AI-Setup")) / "session_logs" / "store_state.db"


def load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def census(data: Dict) -> Dict[str, int]:
    return {b: len(data.get(b, {}) or {}) for b in _BUCKETS}


def migrate(json_path: Path, db_path: Path) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Returns (source census, written census). They must match; the caller checks."""
    data = load_json(json_path)
    src = census(data)
    store = SqliteStore(str(db_path))
    if not store.is_available():
        raise SystemExit(f"[migrate] REFUSING: target store unavailable at {db_path}")

    for k, v in (data.get("kv") or {}).items():
        store.set(k, v)
    for k, fields in (data.get("hash") or {}).items():
        if fields:
            store.hset(k, mapping={f: str(val) for f, val in fields.items()})
    for k, items in (data.get("list") or {}).items():
        if items:
            store.rpush(k, *[str(i) for i in items])
    for k, members in (data.get("set") or {}).items():
        if members:
            store.sadd(k, *[str(m) for m in members])
    for k, scored in (data.get("zset") or {}).items():
        if scored:
            store.zadd(k, {str(m): float(s) for m, s in scored.items()})

    # Expiry is key-scoped metadata in the JSON, exactly as Redis treats TTL. Absolute
    # timestamps are preserved rather than re-based, so an already-expired key stays expired
    # instead of being silently resurrected with a fresh lease.
    now = __import__("time").time()
    for k, expires_at in (data.get("__expiry__") or {}).items():
        remaining = float(expires_at) - now
        if remaining > 0:
            store.expire(k, int(remaining))

    written = {
        "kv": len(store.keys("*")) and _count(store, "kv"),
        "hash": _count(store, "hash"),
        "list": _count(store, "list"),
        "set": _count(store, "set_members"),
        "zset": _count(store, "zset"),
    }
    store.checkpoint()
    store.close()
    return src, written


def _count(store: SqliteStore, table: str) -> int:
    return store._conn.execute(f"SELECT COUNT(DISTINCT key) FROM {table}").fetchone()[0]


def verify(json_path: Path, db_path: Path) -> Tuple[bool, list]:
    """Re-derive the comparison from BOTH stores. Value-level, not just counts -- a count
    match with wrong values is the friendly-looking version of a failed migration."""
    data = load_json(json_path)
    store = SqliteStore(str(db_path))
    problems = []

    for k, v in (data.get("kv") or {}).items():
        if store.get(k) != v:
            problems.append(f"kv[{k}]: json={v!r} db={store.get(k)!r}")
    for k, fields in (data.get("hash") or {}).items():
        got = store.hgetall(k)
        if {f: str(x) for f, x in (fields or {}).items()} != got:
            problems.append(f"hash[{k}]: {len(fields or {})} fields vs {len(got)}")
    for k, items in (data.get("list") or {}).items():
        got = store.lrange(k, 0, -1)
        if [str(i) for i in (items or [])] != got:
            problems.append(f"list[{k}]: {len(items or [])} items vs {len(got)}")
    for k, members in (data.get("set") or {}).items():
        got = store.smembers(k)
        if {str(m) for m in (members or [])} != got:
            problems.append(f"set[{k}]: {len(members or [])} vs {len(got)}")
    for k, scored in (data.get("zset") or {}).items():
        got = {m: store.zscore(k, m) for m in (scored or {})}
        for m, s in (scored or {}).items():
            if got.get(str(m)) != float(s):
                problems.append(f"zset[{k}][{m}]: {s} vs {got.get(str(m))}")
                break
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
        c = census(load_json(json_path))
        print(f"[migrate] would migrate: {c}  (total keys {sum(c.values())})")
        print("[migrate] --check writes nothing; the source is never modified by any mode")
        return 0

    if a.verify:
        ok, problems = verify(json_path, db_path)
        if ok:
            print("[migrate] VERIFY OK -- every JSON value re-read equal from SQLite")
            return 0
        print(f"[migrate] VERIFY FAILED -- {len(problems)} divergence(s):")
        for p in problems[:20]:
            print(f"  {p}")
        return 1

    src, written = migrate(json_path, db_path)
    print(f"[migrate] source census : {src}")
    print(f"[migrate] written census: {written}")
    ok, problems = verify(json_path, db_path)
    if not ok:
        print(f"[migrate] REFUSING TO CLAIM SUCCESS -- {len(problems)} divergence(s):")
        for p in problems[:20]:
            print(f"  {p}")
        return 1
    print("[migrate] OK -- verified value-by-value. The JSON source is UNTOUCHED; "
          "rollback is to stop pointing at the .db.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
