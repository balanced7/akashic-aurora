"""
snapshot_knowledge.py -- backup & restore the live knowledge layer.

Git protects the CODE/architecture. This protects the DATA: the canonical Store
(Redis db 0 + session_logs/store_state.json), the raw learnings.jsonl, and the
curated chronicles/. So if an agent deletes or corrupts knowledge, you can roll back.

    py scripts/snapshot_knowledge.py snapshot ["note"]   # take a timestamped snapshot
    py scripts/snapshot_knowledge.py list                # list snapshots (newest first)
    py scripts/snapshot_knowledge.py restore <name>      # restore (auto-snapshots current first)
    py scripts/snapshot_knowledge.py verify              # show current canonical key count

Snapshots live in backups/snapshots/<timestamp>/ and are self-contained:
  redis_db0.json (type-aware dump) + store_state.json + learnings.jsonl + chronicles/.
The last KEEP_LAST are retained; older ones are pruned.
"""
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = Path(os.getenv("AI_SETUP", "E:\\AI-Setup"))
SNAP_DIR = BASE / "backups" / "snapshots"
STORE_FILE = BASE / "session_logs" / "store_state.json"
JSONL = BASE / "session_logs" / "learnings.jsonl"
CHRONICLES = BASE / "chronicles"
KEEP_LAST = 20

try:
    from config import REDIS_HOST, REDIS_PORT
except Exception:
    REDIS_HOST, REDIS_PORT = "localhost", 16379


def _redis():
    try:
        import redis
        c = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0,
                        decode_responses=True, socket_connect_timeout=1.0)
        c.ping()
        return c
    except Exception:
        return None   # Redis down -> snapshot the file side only


def _dump_redis(r):
    dump = {}
    for k in r.keys("*"):
        t = r.type(k)
        if t == "string":
            dump[k] = {"t": t, "v": r.get(k)}
        elif t == "hash":
            dump[k] = {"t": t, "v": r.hgetall(k)}
        elif t == "list":
            dump[k] = {"t": t, "v": r.lrange(k, 0, -1)}
        elif t == "set":
            dump[k] = {"t": t, "v": sorted(r.smembers(k))}
        elif t == "zset":
            dump[k] = {"t": t, "v": r.zrange(k, 0, -1, withscores=True)}
        elif t == "stream":
            dump[k] = {"t": t, "v": r.xrange(k)}
    return dump


def _restore_redis(r, dump):
    for k in list(r.keys("*")):
        r.delete(k)
    for k, rec in dump.items():
        t, v = rec["t"], rec["v"]
        if t == "string":
            r.set(k, v)
        elif t == "hash":
            if v:
                r.hset(k, mapping=v)
        elif t == "list":
            if v:
                r.rpush(k, *v)
        elif t == "set":
            if v:
                r.sadd(k, *v)
        elif t == "zset":
            if v:
                r.zadd(k, {m: s for m, s in v})
        elif t == "stream":
            for eid, fields in v:
                r.xadd(k, fields)


def snapshot(note=""):
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = SNAP_DIR / stamp
    dest.mkdir()
    r = _redis()
    redis_keys = 0
    if r is not None:
        dump = _dump_redis(r)
        redis_keys = len(dump)
        (dest / "redis_db0.json").write_text(json.dumps(dump, indent=1, ensure_ascii=False), encoding="utf-8")
    if STORE_FILE.exists():
        shutil.copy2(STORE_FILE, dest / "store_state.json")
    if JSONL.exists():
        shutil.copy2(JSONL, dest / "learnings.jsonl")
    if CHRONICLES.exists():
        shutil.copytree(CHRONICLES, dest / "chronicles", dirs_exist_ok=True)
    (dest / "manifest.json").write_text(json.dumps({
        "timestamp": stamp, "note": note, "redis_up": r is not None,
        "redis_keys": redis_keys, "created": datetime.now().isoformat(),
    }, indent=1), encoding="utf-8")
    print(f"[snapshot] {dest.name}  (redis_keys={redis_keys}, redis_up={r is not None})"
          + (f"  note: {note}" if note else ""))
    _prune()
    return dest


def _prune():
    snaps = sorted([p for p in SNAP_DIR.iterdir() if p.is_dir()], reverse=True)
    for old in snaps[KEEP_LAST:]:
        shutil.rmtree(old, ignore_errors=True)
        print(f"[prune] removed old snapshot {old.name}")


def list_snaps():
    if not SNAP_DIR.exists() or not any(SNAP_DIR.iterdir()):
        print("(no snapshots yet -- run: py scripts/snapshot_knowledge.py snapshot)")
        return
    for p in sorted([p for p in SNAP_DIR.iterdir() if p.is_dir()], reverse=True):
        m = {}
        mf = p / "manifest.json"
        if mf.exists():
            m = json.loads(mf.read_text(encoding="utf-8"))
        print(f"  {p.name}  redis_keys={m.get('redis_keys', '?')}"
              + (f"  note: {m['note']}" if m.get("note") else ""))


def restore(name):
    src = SNAP_DIR / name
    if not src.is_dir():
        sys.exit(f"no such snapshot: {name} (run `list`)")
    print(f"[restore] from {name} -- snapshotting CURRENT state first (safety)...")
    snapshot(note=f"auto-before-restore-of-{name}")
    r = _redis()
    rfile = src / "redis_db0.json"
    if r is not None and rfile.exists():
        _restore_redis(r, json.loads(rfile.read_text(encoding="utf-8")))
        print(f"[restore] Redis db0 restored ({len(r.keys('*'))} keys)")
    elif r is None:
        print("[restore] Redis down -- restored files only (Redis will re-hydrate from File on next use)")
    for fname, dst in [("store_state.json", STORE_FILE), ("learnings.jsonl", JSONL)]:
        if (src / fname).exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / fname, dst)
    if (src / "chronicles").exists():
        shutil.copytree(src / "chronicles", CHRONICLES, dirs_exist_ok=True)
    print(f"[restore] DONE -- knowledge rolled back to {name}")


def verify():
    r = _redis()
    if r is None:
        print("Redis down; canonical lives in session_logs/store_state.json")
        return
    learn = len(r.keys("learn:experiment:*"))
    print(f"canonical: {len(r.keys('*'))} keys ({learn} experiments) on {REDIS_HOST}:{REDIS_PORT} db0")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "snapshot":
        snapshot(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "list":
        list_snaps()
    elif cmd == "restore":
        if len(sys.argv) < 3:
            sys.exit("usage: restore <snapshot_name> (run `list` to see names)")
        restore(sys.argv[2])
    elif cmd == "verify":
        verify()
    else:
        sys.exit(f"unknown command: {cmd} (snapshot|list|restore|verify)")
