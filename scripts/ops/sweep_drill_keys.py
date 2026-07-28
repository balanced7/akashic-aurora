"""Audited sweep of drill/test key crumbs from the live keyspace (T118 ratified).

The census found ~180 singleton families (t-*, t056_*, census_test) -- leftovers
from old drill runs that pollute every keyspace census and would halt the durable
reconcile forever. The ratified roster rules them "one audited TTL-sweep": delete,
but leave a receipt that could restore every byte.

CONTRACT (pinned in tests/test_sweep_drill_keys.py):
- dry-run by default; --apply to delete.
- the audit file is written BEFORE any deletion and holds each doomed key's full
  typed value -- the sweep is reversible from its own receipt.
- only pattern-matched keys are touched, ever.

Root-cause sibling (not this script's job): drill namespaces should TTL at mint so
this class stops accumulating -- tracked as a T118 follow-up.

    py scripts/ops/sweep_drill_keys.py            # dry-run: list the doomed
    py scripts/ops/sweep_drill_keys.py --apply    # audit, then delete
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

SWEEP_PATTERNS = ("t-*", "t056_*", "t117dbg:*", "census_test")


def _doomed(store) -> List[str]:
    out = []
    for key in store.keys("*"):
        if any(fnmatch.fnmatch(str(key), p) for p in SWEEP_PATTERNS):
            out.append(str(key))
    return sorted(out)


def _quiet(fn, default):
    """Real Redis RAISES (WRONGTYPE) on a type-mismatched read where FileStore
    returns empty -- the first live --apply died on exactly this. Tolerate per verb."""
    try:
        return fn()
    except Exception:
        return default


def _typed_value(store, key):
    h = _quiet(lambda: store.hgetall(key), {})
    if h:
        return {"type": "hash", "value": h}
    v = _quiet(lambda: store.get(key), None)
    if v is not None:
        return {"type": "kv", "value": v}
    lst = _quiet(lambda: store.lrange(key, 0, -1), [])
    if lst:
        return {"type": "list", "value": list(lst)}
    s = _quiet(lambda: store.smembers(key), set())
    if s:
        return {"type": "set", "value": sorted(s)}
    z = _quiet(lambda: store.zrange(key, 0, -1, withscores=True), [])
    if z:
        return {"type": "zset", "value": {m: sc for m, sc in z}}
    return {"type": "empty", "value": None}


def sweep(store, audit_path, apply: bool = False) -> List[str]:
    """Returns the doomed key list. apply=False (default) touches nothing."""
    doomed = _doomed(store)
    if not apply or not doomed:
        return doomed
    audit_path = Path(audit_path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    record: Dict[str, Dict] = {k: _typed_value(store, k) for k in doomed}
    tmp = Path(f"{audit_path}.tmp.{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=1)
    os.replace(tmp, audit_path)
    for k in doomed:
        store.delete(k)
    return doomed


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="audit, then delete")
    a = ap.parse_args(argv)

    from core.foundation.store import RedisStore
    r = RedisStore.connect()
    if not r.is_available():
        print("[sweep] Redis down -- nothing to sweep")
        return 1

    stamp = int(time.time())
    audit = Path(os.getenv("AI_SETUP", r"E:\AI-Setup")) / "session_logs" / \
        f"sweep-drill-{stamp}.json"
    doomed = sweep(r, audit_path=audit, apply=a.apply)
    mode = "SWEPT" if a.apply else "DRY-RUN (would sweep)"
    print(f"[sweep] {mode}: {len(doomed)} key(s)")
    for k in doomed[:15]:
        print(f"  {k}")
    if len(doomed) > 15:
        print(f"  ... +{len(doomed) - 15} more")
    if a.apply and doomed:
        print(f"[sweep] audit (full typed values, restorable): {audit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
