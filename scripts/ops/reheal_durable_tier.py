"""Backfill the durable file tier FROM Redis. The direction the built-in heal refuses.

WHY THIS EXISTS -- the incoherence, stated plainly
--------------------------------------------------
HybridStore's contract (its own docstring): "Writes always land in File (the durable record)
and best-effort in Redis. Reads prefer Redis when available, else fall back to File."

So File should hold a SUPERSET of Redis. Measured 2026-07-26:

    Redis : 455 learn:experiment keys
    File  :  17

Three point seven percent. File writes have been lost at scale -- the FileStore whole-file
flush drops concurrent writers (measured: 450 writes, 155 survived), and at least one
truncation event today took store_state.json from ~109KB to 164 bytes when a failed _load()
left an empty dict that the next flush wrote over everything.

Nobody noticed because READS PREFER REDIS. The cache has been carrying the system while the
durable tier quietly emptied. That is the whole failure in one sentence.

WHY THE BUILT-IN HEAL CANNOT FIX IT
------------------------------------
HybridStore.heal_report/reconcile are UNIDIRECTIONAL by design -- File is declared source of
truth, so a Redis-only key is called an orphan the heal "cannot and must not backfill into
File". That is correct when File is genuinely authoritative. It is exactly wrong today,
because the authoritative copy is the one that got emptied, and the only surviving copy lives
in the tier we call disposable.

This script does NOT change that design. It is a one-way repair for a corpus that is
currently held by its cache, run deliberately by an operator who knows the direction is
inverted -- not a new heal path, and not something to wire into boot.

SAFETY
------
- ADDITIVE ONLY. Never deletes, never overwrites a differing File value unless --overwrite.
- Snapshot first (scripts/ops/snapshot_knowledge.py snapshot "pre-reheal").
- --check reports what WOULD move and writes nothing.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.foundation.store import RedisStore, FileStore  # noqa: E402


def _target(backend: str):
    if backend == "sqlite":
        from core.foundation.sqlite_store import SqliteStore
        return SqliteStore()
    return FileStore()


def reheal(pattern: str, backend: str, dry_run: bool, overwrite: bool) -> int:
    r = RedisStore.connect()
    if r is None or not r.is_available():
        print("[reheal] REFUSING: Redis is down. It currently holds the only copy of the "
              "missing records -- without it there is nothing to heal FROM.")
        return 2

    dst = _target(backend)
    if not dst.is_available():
        print(f"[reheal] REFUSING: target {backend} store unavailable")
        return 2

    keys = r.keys(pattern)
    print(f"[reheal] redis keys matching {pattern!r}: {len(keys)}")

    moved = Counter()
    skipped = Counter()
    failed = []

    for k in keys:
        try:
            # Structure is discovered from Redis, since only Redis knows what each key IS.
            kind = r._client.type(k)
            kind = kind.decode() if isinstance(kind, bytes) else str(kind)

            if kind == "string":
                val = r.get(k)
                if val is None:
                    continue
                cur = dst.get(k)
                if cur is not None and not overwrite:
                    skipped["present"] += 1
                    continue
                if not dry_run:
                    dst.set(k, val)
                moved["string"] += 1
            elif kind == "hash":
                m = r.hgetall(k)
                if m:
                    if dst.hgetall(k) and not overwrite:
                        skipped["present"] += 1
                        continue
                    if not dry_run:
                        dst.hset(k, mapping=m)
                    moved["hash"] += 1
            elif kind == "list":
                items = r.lrange(k, 0, -1)
                if items:
                    if dst.llen(k) and not overwrite:
                        skipped["present"] += 1
                        continue
                    if not dry_run:
                        dst.rpush(k, *items)
                    moved["list"] += 1
            elif kind == "set":
                members = r.smembers(k)
                if members:
                    if dst.smembers(k) and not overwrite:
                        skipped["present"] += 1
                        continue
                    if not dry_run:
                        dst.sadd(k, *members)
                    moved["set"] += 1
            elif kind == "zset":
                pairs = r.zrange(k, 0, -1, withscores=True)
                if pairs:
                    if dst.zcard(k) and not overwrite:
                        skipped["present"] += 1
                        continue
                    if not dry_run:
                        dst.zadd(k, {m: s for m, s in pairs})
                    moved["zset"] += 1
            else:
                skipped[f"type:{kind}"] += 1
        except Exception as e:
            failed.append((k, f"{type(e).__name__}: {e}"))

    print(f"[reheal] {'WOULD MOVE' if dry_run else 'MOVED'}: {dict(moved)}  "
          f"(total {sum(moved.values())})")
    if skipped:
        print(f"[reheal] skipped: {dict(skipped)}  (already present; --overwrite to replace)")
    if failed:
        print(f"[reheal] FAILED on {len(failed)} key(s) -- reported, not swallowed:")
        for k, e in failed[:10]:
            print(f"    {k}: {e}")

    if not dry_run:
        try:
            dst.checkpoint()
        except AttributeError:
            pass
        after = len(dst.keys(pattern))
        print(f"[reheal] target now holds {after} key(s) matching {pattern!r} "
              f"(redis has {len(keys)})")
        if after < len(keys):
            print(f"[reheal] STILL SHORT by {len(keys) - after} -- not claiming success")
            return 1
    return 0 if not failed else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pattern", default="*", help="key pattern to heal (default: everything)")
    ap.add_argument("--backend", default="sqlite", choices=["sqlite", "file"])
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace values that already differ in the target")
    a = ap.parse_args(argv)
    return reheal(a.pattern, a.backend, a.check, a.overwrite)


if __name__ == "__main__":
    sys.exit(main())
