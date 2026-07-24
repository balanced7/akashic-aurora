"""
harmonize_knowledge.py — one-time knowledge-store harmonization (2026-06-20)

See docs/library/design/20260709_knowledge-store-harmonization-plan-2026_9e9656.md. Backup-first; nothing is deleted before a
full snapshot exists. Operates DIRECTLY on both backends (the FileStore JSON and
Redis 16379) so they end byte-for-byte consistent by construction.

Decisions (approved 2026-06-20):
  * canonical Redis = 16379
  * test data -> quarantined to a jsonl, then removed from the live store
  * keep all static chronicles

Phases (run explicitly):
  py scripts/harmonize_knowledge.py backup    # Phase 0: snapshot + quarantine jsonl
  py scripts/harmonize_knowledge.py rebuild    # Phases 3-5: clear junk, re-import 6 lessons richly, reconcile
  py scripts/harmonize_knowledge.py verify     # show final state of BOTH backends + assert equality
"""
import json
import os
import shutil
import sys
import time
from pathlib import Path

BASE = Path(os.getenv("AI_SETUP", "E:\\AI-Setup"))
STORE_FILE = BASE / "session_logs" / "store_state.json"
JSONL = BASE / "session_logs" / "learnings.jsonl"
CHRONICLES = BASE / "chronicles"
BACKUP_DIR = BASE / "backups" / "knowledge_2026-06-20"
QUARANTINE = BASE / "session_logs" / "quarantine_test_data.jsonl"
REDIS_PORT = 16379

# The 6 real lessons (the only knowledge kept live), in jsonl order.
REAL = [
    "relationship_types_framework_design",
    "semantic_naming_readability_impact",
    "semantic_naming_pattern_discovery",
    "backward_compatibility_refactoring_strategy",
    "semantic_refactoring_progress_analysis",
    "semantic_documentation_update_strategy",
]
REAL_AGENT = "semantic_refactor_research"
CATEGORY = {
    "relationship_types_framework_design": "knowledge_representation",
    "semantic_naming_readability_impact": "code_readability",
    "semantic_naming_pattern_discovery": "code_patterns",
    "backward_compatibility_refactoring_strategy": "refactoring_methodology",
    "semantic_refactoring_progress_analysis": "project_management",
    "semantic_documentation_update_strategy": "documentation",
}
TEST_EXPERIMENTS = {"test_learning_1", "test_sync_learning_v1", "verify_exp", "recon_facade_exp"}
TEST_AGENTS = {"test_agent_2", "test_agent_6", "verify_agent2", "recon_test_agent"}
TEST_CATEGORIES = {"test", "testing", "verification"}
TEST_STREAMS = ["agent:events", "agent:recon_test_agent:events"]


def _redis():
    import redis
    return redis.Redis(port=REDIS_PORT, decode_responses=True)


def _load_jsonl():
    """experiment_name -> (lineno, full rich record) from the raw archival jsonl."""
    out = {}
    for i, line in enumerate(JSONL.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        out[rec["experiment_name"]] = (i, rec)
    return out


# ----------------------------------------------------------------------------- backup
def phase_backup():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    # 1. file store
    shutil.copy2(STORE_FILE, BACKUP_DIR / "store_state.json")
    shutil.copy2(JSONL, BACKUP_DIR / "learnings.jsonl")
    # 2. chronicles
    shutil.copytree(CHRONICLES, BACKUP_DIR / "chronicles", dirs_exist_ok=True)
    # 3. full Redis dump (type-aware, lossless)
    r = _redis()
    dump = {}
    for k in r.keys("*"):
        t = r.type(k)
        if t == "string":
            dump[k] = {"type": t, "v": r.get(k)}
        elif t == "hash":
            dump[k] = {"type": t, "v": r.hgetall(k)}
        elif t == "list":
            dump[k] = {"type": t, "v": r.lrange(k, 0, -1)}
        elif t == "set":
            dump[k] = {"type": t, "v": sorted(r.smembers(k))}
        elif t == "zset":
            dump[k] = {"type": t, "v": r.zrange(k, 0, -1, withscores=True)}
        elif t == "stream":
            dump[k] = {"type": t, "v": r.xrange(k)}
    (BACKUP_DIR / "redis_16379_dump.json").write_text(
        json.dumps(dump, indent=1, ensure_ascii=False), encoding="utf-8")
    # 4. quarantine the test records verbatim (from file store + redis), before any removal
    d = json.loads(STORE_FILE.read_text(encoding="utf-8"))
    q = []
    for name in TEST_EXPERIMENTS:
        h = d.get("hash", {}).get(f"learn:experiment:{name}")
        if h:
            q.append({"kind": "test_learning", "source": "store_state.json", "record": h})
        rh = r.hgetall(f"learn:experiment:{name}")
        if rh and rh != h:
            q.append({"kind": "test_learning", "source": "redis:16379", "record": rh})
    for b in d.get("list", {}).get("blockers:escalated", []):
        q.append({"kind": "test_blocker", "source": "store_state.json", "record": b})
    for s in TEST_STREAMS:
        ent = r.xrange(s)
        if ent:
            q.append({"kind": "test_stream", "source": f"redis:{s}", "record": ent})
    with QUARANTINE.open("w", encoding="utf-8") as fh:
        for item in q:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"[backup] -> {BACKUP_DIR}")
    print(f"[backup] redis keys dumped: {len(dump)}")
    print(f"[backup] quarantined {len(q)} test records -> {QUARANTINE.name}")


# ----------------------------------------------------------------------- canonical records
def _canonical_records():
    """Build the 6 rich canonical hashes: flat summary + source pointer + full detail_json."""
    jl = _load_jsonl()
    recs = {}
    for name in REAL:
        lineno, rich = jl[name]
        recs[name] = {
            "experiment_name": name,
            "agent_id": REAL_AGENT,
            "category": CATEGORY[name],
            "what_tried": rich.get("what_tried", ""),
            "expected": rich.get("expected_outcome", rich.get("expected", "")),
            "actual": rich.get("actual_outcome", rich.get("actual", "")),
            "metrics": json.dumps(rich.get("metrics", {}), ensure_ascii=False),
            "success": "yes",
            "confidence": rich.get("confidence", "medium"),
            "recommendation": rich.get("recommendation", ""),
            "anti_pattern": "",
            "root_cause": "",
            "timestamp": rich.get("timestamp", ""),
            # lossy summary above + lossless pointer + full detail (lose nothing, even in-store).
            # Path is repo-root-relative so an agent can actually open it (the pointer
            # must be FOLLOWABLE -- an unresolvable pointer isn't lossless).
            "source": f"session_logs/learnings.jsonl:L{lineno}",
            "detail_json": json.dumps(rich, ensure_ascii=False),
        }
    return recs


# ----------------------------------------------------------------------------- rebuild
def phase_rebuild():
    if not (BACKUP_DIR / "redis_16379_dump.json").exists():
        sys.exit("REFUSING: run `backup` first (no snapshot found).")
    recs = _canonical_records()
    r = _redis()

    # The complete canonical key set (learn:* only — nothing else is canonical).
    canonical_keys = (
        {f"learn:experiment:{n}" for n in REAL}
        | {f"learn:category:{CATEGORY[n]}" for n in REAL}
        | {"learn:experiments:all", "learn:experiments:success", f"learn:agent:{REAL_AGENT}"}
    )

    # ---- Redis: delete EVERYTHING that isn't canonical, then (re)write canonical.
    # Deterministic: produces exactly the canonical state regardless of prior pollution.
    removed = 0
    for k in r.keys("*"):
        if k not in canonical_keys:
            r.delete(k); removed += 1
    for name in REAL:
        r.delete(f"learn:experiment:{name}")
        r.hset(f"learn:experiment:{name}", mapping=recs[name])
    r.delete("learn:experiments:all"); r.rpush("learn:experiments:all", *REAL)
    r.delete("learn:experiments:success"); r.zadd("learn:experiments:success", {n: 100.0 for n in REAL})
    r.delete(f"learn:agent:{REAL_AGENT}"); r.rpush(f"learn:agent:{REAL_AGENT}", *REAL)
    for name in REAL:
        r.delete(f"learn:category:{CATEGORY[name]}"); r.sadd(f"learn:category:{CATEGORY[name]}", name)

    # ---- File store: write a FRESH skeleton holding ONLY the canonical learn:*.
    d = {"kv": {}, "hash": {}, "list": {}, "set": {}, "zset": {}, "__expiry__": {}}
    for name in REAL:
        d["hash"][f"learn:experiment:{name}"] = recs[name]
    d["list"]["learn:experiments:all"] = list(REAL)
    d["list"][f"learn:agent:{REAL_AGENT}"] = list(REAL)
    for name in REAL:
        d["set"][f"learn:category:{CATEGORY[name]}"] = [name]
    d["zset"]["learn:experiments:success"] = {n: 100.0 for n in REAL}
    STORE_FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[rebuild] wrote {len(REAL)} canonical lessons to BOTH backends; "
          f"removed {removed} non-canonical Redis key(s); file reset to clean skeleton.")


# ----------------------------------------------------------------------------- verify
def phase_verify():
    r = _redis()
    d = json.loads(STORE_FILE.read_text(encoding="utf-8"))
    print("=== REDIS 16379 learn:* ===")
    rk = sorted(r.keys("learn:*"))
    for k in rk:
        print(f"  {r.type(k):6} {k}")
    print(f"  streams present: {[s for s in TEST_STREAMS if r.exists(s)]}")
    print("=== FILE store learn:* ===")
    fk = sorted(k for sect in ("hash", "list", "set", "zset") for k in d.get(sect, {}) if k.startswith("learn:"))
    for k in fk:
        print(f"  {k}")
    # equality checks
    exp_redis = sorted(k.split("learn:experiment:")[1] for k in rk if k.startswith("learn:experiment:"))
    exp_file = sorted(k.split("learn:experiment:")[1] for k in fk if k.startswith("learn:experiment:"))
    assert exp_redis == sorted(REAL), f"redis experiments mismatch: {exp_redis}"
    assert exp_file == sorted(REAL), f"file experiments mismatch: {exp_file}"
    assert r.llen("learn:experiments:all") == len(REAL), "redis all-index wrong length"
    assert d["list"]["learn:experiments:all"] == REAL, "file all-index wrong"
    assert not [s for s in TEST_STREAMS if r.exists(s)], "test streams still present"
    assert "blockers:escalated" not in d.get("list", {}), "blockers still present"
    # detail preserved?
    for name in REAL:
        h = r.hgetall(f"learn:experiment:{name}")
        assert h.get("source", "").startswith("learnings.jsonl:L"), f"{name} missing source pointer"
        assert h.get("detail_json"), f"{name} missing detail_json"
    print("\nOK: both backends consistent; 6 lessons live with source pointers + full detail; junk gone.")


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "verify"
    {"backup": phase_backup, "rebuild": phase_rebuild, "verify": phase_verify}[phase]()
