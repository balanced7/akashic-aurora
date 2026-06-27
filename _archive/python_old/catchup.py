#!/usr/bin/env python3
"""
BreakThrough Stack - Session Catchup
===================================

Shows context for resuming work across all systems:
- Recent sessions with action types and efficacy
- Recent chronicles (milestones, decisions, failures)
- Redis-backed: decisions, experiences, insights, context, session summaries
- Free-text query against session_text_idx
- Recent canonical session stream (``session:events`` on WSL master)
- Learned tags
- Action type patterns

Usage:
    python catchup.py                  # Full briefing
    python catchup.py --brief          # Quick status
    python catchup.py --sessions       # Recent sessions only
    python catchup.py --chronicles     # Chronicles only
    python catchup.py --learn          # Decisions/experiences/insights from learning store
    python catchup.py --context        # Free-form context:* keys
    python catchup.py --query "redis"  # FT.SEARCH session summaries by text
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import redis

sys.path.insert(0, r"E:\AI-Setup")

try:
    from config import SESSION_EVENTS_STREAM, get_redis_config
except Exception:
    SESSION_EVENTS_STREAM = "session:events"

    def get_redis_config():
        return {"host": "localhost", "port": 6380, "db": 0,
                "decode_responses": True, "socket_connect_timeout": 3}

BASE_DIR = Path(r"E:\AI-Setup")
ARCHIVE_DIR = BASE_DIR / "sessions"
CHRONICLE_DIR = BASE_DIR / "chronicles"
INDEX_FILE = ARCHIVE_DIR / "index.json"


def print_header():
    print()
    print("=" * 70)
    print("  BREAKTHROUGH STACK - SESSION CATCHUP")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


_redis_cache = {}


def _get_redis(name="wsl"):
    """Get cached Redis connection. name='wsl' (master 6380) or 'docker' (16379)."""
    if name in _redis_cache:
        return _redis_cache[name]
    try:
        if name == "docker":
            r = redis.Redis(host="localhost", port=16379, db=0,
                            decode_responses=True, socket_connect_timeout=3)
        else:
            r = redis.Redis(**get_redis_config())
        r.ping()
        _redis_cache[name] = r
        return r
    except Exception:
        _redis_cache[name] = None
        return None


def print_system():
    print()
    print("[1] SYSTEM STATUS")
    print("-" * 40)

    r = _get_redis("wsl")
    if r:
        try:
            print(f"  [OK] WSL Redis (6380): {r.info().get('used_memory_human', 'N/A')} used")
        except Exception:
            print("  [OK] WSL Redis (6380): connected")
    else:
        print("  [XX] WSL Redis (6380): not connected")

    rd = _get_redis("docker")
    if rd:
        try:
            print(f"  [OK] Docker Redis (16379): {rd.info().get('used_memory_human', 'N/A')} used")
        except Exception:
            print("  [OK] Docker Redis (16379): connected")
    else:
        print("  [..] Docker Redis (16379): not connected (optional)")


def print_canonical_stream(limit=12):
    """Newest MCP canonical events from Redis Stream session:events."""
    print()
    print("[+] MCP SESSION EVENT STREAM (canonical, recent)")
    print("-" * 40)
    r = _get_redis("wsl")
    if not r:
        print("  Redis unavailable.")
        return
    try:
        rows = r.xrevrange(SESSION_EVENTS_STREAM, max="+", min="-", count=max(1, min(int(limit), 80)))
        if not rows:
            print(f"  No entries in `{SESSION_EVENTS_STREAM}` yet.")
            return
        for mid, fields in rows:
            sid = fields.get("session_id", "?")
            ag = fields.get("agent", "?")
            et = fields.get("event_type", "?")
            pl = fields.get("payload", "")[:220].replace("\n", " ")
            print(f"  {mid}")
            print(f"    {ag}/{et} · {sid}")
            if pl:
                print(f"    {pl}...")
        print(f"  (stream `{SESSION_EVENTS_STREAM}` on WSL master)")
    except Exception as e:
        print(f"  Error reading stream: {e}")


def print_sessions():
    print()
    print("[2] RECENT SESSIONS")
    print("-" * 40)
    
    if not INDEX_FILE.exists():
        print("  No sessions archived yet.")
        return
    
    with open(INDEX_FILE) as f:
        sessions = json.load(f)
    
    if not sessions:
        print("  No sessions yet.")
        return
    
    for s in sessions[:8]:
        sid = s.get('session_id', 'unknown')
        date = s.get('date', '')
        tags = s.get('tags', [])
        summary = s.get('summary', 'N/A')
        action_types = s.get('action_types', {})
        efficacy = s.get('efficacy', {})
        
        print(f"  [{date}] {sid}")
        
        if tags:
            print(f"       Tags: {', '.join(tags[:3])}")
        
        # Show efficacy
        if efficacy:
            parts = []
            for status, count in efficacy.items():
                parts.append(f"{status}:{count}")
            print(f"       Result: {', '.join(parts)}")
        
        # Show action types
        if action_types:
            types = [f"{k}:{v}" for k, v in sorted(action_types.items(), key=lambda x: -x[1])[:3]]
            print(f"       Activity: {', '.join(types)}")
        
        print(f"       {summary[:60]}")
        print()


def print_chronicles():
    print()
    print("[3] RECENT CHRONICLES")
    print("-" * 40)
    
    # Milestones
    ms_file = CHRONICLE_DIR / "milestones.json"
    if ms_file.exists():
        with open(ms_file) as f:
            milestones = json.load(f)
        print(f"  Milestones ({len(milestones)}):")
        for m in milestones[:3]:
            status = m.get('status', 'unknown')
            status_marker = {'claimed': '[?]', 'prototype': '[P]', 'alpha': '[A]', 'beta': '[B]', 'verified': '[V]'}
            marker = status_marker.get(status, '[ ]')
            title = m.get('title', 'N/A')[:50]
            print(f"    {marker} {title}")
    
    # Decisions
    adr_file = CHRONICLE_DIR / "adrs.json"
    if adr_file.exists():
        with open(adr_file) as f:
            decisions = json.load(f)
        print(f"  Decisions ({len(decisions)}):")
        for d in decisions[:3]:
            title = d.get('title', 'N/A')[:50]
            print(f"    [ADR] {title}")
    
    # Failures
    fl_file = CHRONICLE_DIR / "failures.json"
    if fl_file.exists():
        with open(fl_file) as f:
            failures = json.load(f)
        print(f"  Failures ({len(failures)}):")
        for f in failures[:3]:
            status = f.get('status', 'unknown')
            marker = '[!]' if status == 'open' else '[R]'
            title = f.get('title', 'N/A')[:50]
            print(f"    {marker} {title}")


def print_tags():
    print()
    print("[4] LEARNED VOCABULARY")
    print("-" * 40)
    
    vocab_file = CHRONICLE_DIR / "tag_vocabulary.json"
    if vocab_file.exists():
        with open(vocab_file) as f:
            vocab = json.load(f)
        
        sorted_tags = sorted(vocab.items(), key=lambda x: -x[1])[:15]
        print(f"  {', '.join(t for t, _ in sorted_tags)}")
    else:
        print("  No vocabulary learned yet.")


def print_action_patterns():
    print()
    print("[5] ACTION TYPE PATTERNS")
    print("-" * 40)
    print("  Detected automatically from work:")
    print("  - analyzing, planning, researching")
    print("  - coding, testing, debugging")
    print("  - deploying, documenting")
    print("  - configuring, learning, communicating")
    print()
    print("  Efficacy tracked:")
    print("  - success: Goal achieved")
    print("  - failure: Goal not achieved")
    print("  - partial: Some progress made")
    print("  - unknown: Not yet determined")


def print_changelog():
    print()
    print("[6] CHANGELOG (Recent)")
    print("-" * 40)
    
    try:
        from patch_log import get_patch_log
        pl = get_patch_log()
        
        print(f"  Version: {pl.version}")
        print()
        
        entries = pl.get_changelog(limit=5)
        if entries:
            for entry in entries:
                result_marker = {
                    "SUCCESS": "[+]", "FAILURE": "[-]",
                    "PARTIAL": "[~]", "PENDING": "[ ]"
                }.get(entry.result, "[ ]")
                print(f"    {result_marker} {entry.system}:{entry.change_type} {entry.title[:40]}")
                if entry.goal:
                    print(f"         Goal: {entry.goal[:40]}...")
        else:
            print("  No patches yet.")
    except Exception as e:
        print(f"  Could not load changelog: {e}")


def print_learn(limit=5):
    """Surface decisions/experiences/insights from the learning store."""
    print()
    print("[7] LEARNING STORE")
    print("-" * 40)
    r = _get_redis("wsl")
    if not r:
        print("  Redis unavailable.")
        return

    try:
        # Recent decisions
        ids = r.zrevrange("learn:decisions:idx", 0, limit - 1)
        if ids:
            print(f"  Decisions ({r.zcard('learn:decisions:idx')} total, showing {len(ids)}):")
            for did in ids:
                raw = r.hget("learn:decisions", did)
                if raw:
                    d = json.loads(raw)
                    print(f"    [ADR] {d.get('title', '')[:60]}")
                    dec_text = d.get('decision', '')
                    if dec_text:
                        print(f"           -> {dec_text[:80]}")
        else:
            print("  Decisions: none recorded yet.")

        # Recent successful experiences
        succ_ids = r.zrevrange("learn:experiences:success", 0, limit - 1)
        fail_ids = r.zrevrange("learn:experiences:failure", 0, limit - 1)
        total = r.zcard("learn:experiences:success") + r.zcard("learn:experiences:failure")
        if succ_ids or fail_ids:
            print(f"  Experiences ({total} total):")
            for eid in succ_ids:
                raw = r.hget("learn:experiences", eid)
                if raw:
                    e = json.loads(raw)
                    print(f"    [OK] {e.get('task', '')[:60]}")
            for eid in fail_ids:
                raw = r.hget("learn:experiences", eid)
                if raw:
                    e = json.loads(raw)
                    print(f"    [XX] {e.get('task', '')[:60]}")
        else:
            print("  Experiences: none recorded yet.")

        # Insights from reflections
        refl_ids = r.zrevrange("learn:reflections:idx", 0, limit - 1)
        if refl_ids:
            print(f"  Reflections (showing {len(refl_ids)}):")
            for rid in refl_ids:
                raw = r.hget("learn:reflections", rid)
                if raw:
                    rf = json.loads(raw)
                    if rf.get("confidence", 0) >= 0.5:
                        print(f"    [REFL] {rf.get('task', '')[:55]}")
                        if rf.get('what_would_help'):
                            print(f"           helpful: {rf['what_would_help'][:70]}")
        else:
            print("  Reflections: none recorded yet.")
    except Exception as e:
        print(f"  Error reading learning store: {e}")


def print_context(limit=10):
    """Surface free-form context:* keys (the prior AI's working memory)."""
    print()
    print("[8] CONTEXT MEMORY (context:*)")
    print("-" * 40)
    r = _get_redis("wsl")
    if not r:
        print("  Redis unavailable.")
        return

    try:
        keys = sorted(r.scan_iter(match="context:*", count=200))
        if not keys:
            print("  No context entries.")
            return
        print(f"  {len(keys)} entries:")
        for k in keys[:limit]:
            try:
                t = r.type(k)
                if t == "string":
                    val = r.get(k) or ""
                    preview = val.replace("\n", " ")[:80]
                    print(f"    {k}: {preview}")
                elif t == "hash":
                    fields = r.hkeys(k)
                    print(f"    {k}: <hash, {len(fields)} fields>")
                else:
                    print(f"    {k}: <{t}>")
            except Exception:
                print(f"    {k}: <unreadable>")
        if len(keys) > limit:
            print(f"    ... and {len(keys) - limit} more")
    except Exception as e:
        print(f"  Error: {e}")


def print_summaries(limit=5):
    """Recent session summaries from the compressor."""
    print()
    print("[9] RECENT SESSION SUMMARIES")
    print("-" * 40)
    r = _get_redis("wsl")
    if not r:
        print("  Redis unavailable.")
        return

    try:
        keys = list(r.scan_iter(match="session:summary:*", count=200))
        if not keys:
            print("  No summaries yet (compressor will populate as sessions log).")
            return

        items = []
        for k in keys:
            try:
                h = r.hgetall(k)
                ts = int(h.get("timestamp", "0") or "0")
                items.append((ts, h))
            except Exception:
                pass
        items.sort(key=lambda x: x[0], reverse=True)

        print(f"  {len(items)} summaries (showing {min(limit, len(items))}):")
        for ts, h in items[:limit]:
            sid = h.get("session_id", "?")
            when = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "?"
            summ = (h.get("summary", "") or "").replace("\n", " ")[:90]
            print(f"    [{when}] {sid}")
            print(f"           {summ}")
    except Exception as e:
        print(f"  Error: {e}")


def query_summaries(text, limit=5):
    """FT.SEARCH the session_text_idx for relevant past sessions."""
    print()
    print(f"[QUERY] '{text}'")
    print("-" * 40)
    r = _get_redis("wsl")
    if not r:
        print("  Redis unavailable.")
        return

    try:
        res = r.execute_command(
            "FT.SEARCH", "session_text_idx", f"@summary:{text}",
            "LIMIT", "0", str(limit),
            "RETURN", "3", "session_id", "summary", "timestamp"
        )
        if not res or len(res) < 2:
            print("  No matches.")
            return
        total = res[0]
        print(f"  {total} match(es):")
        for i in range(1, len(res), 2):
            if i + 1 >= len(res):
                break
            doc = res[i + 1]
            d = dict(zip(doc[::2], doc[1::2]))
            ts = int(d.get("timestamp", "0") or "0")
            when = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "?"
            print(f"    [{when}] {d.get('session_id', '?')}")
            print(f"           {(d.get('summary', '') or '')[:120]}")
    except Exception as e:
        print(f"  Error: {e}")


def print_brief():
    """Quick overview for fast context"""
    print_sessions()
    print_canonical_stream(limit=8)
    print_chronicles()
    print_learn(limit=3)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--brief', action='store_true', help='Quick summary')
    parser.add_argument('--sessions', action='store_true', help='Sessions only')
    parser.add_argument('--chronicles', action='store_true', help='Chronicles only')
    parser.add_argument('--changelog', action='store_true', help='Changelog only')
    parser.add_argument('--learn', action='store_true', help='Learning store only')
    parser.add_argument('--context', action='store_true', help='Free-form context:* keys')
    parser.add_argument('--summaries', action='store_true', help='Recent session summaries')
    parser.add_argument('--stream', action='store_true', help='Canonical MCP session stream tail')
    parser.add_argument('--query', metavar='TEXT', help='FT.SEARCH session summaries by text')
    args = parser.parse_args()

    print_header()
    print_system()

    if args.query:
        query_summaries(args.query)
    elif args.changelog:
        print_changelog()
    elif args.chronicles:
        print_chronicles()
        print_tags()
    elif args.sessions:
        print_sessions()
    elif args.learn:
        print_learn()
    elif args.context:
        print_context()
    elif args.summaries:
        print_summaries()
    elif args.stream:
        print_canonical_stream()
    elif args.brief:
        print_brief()
    else:
        print_sessions()
        print_canonical_stream(limit=14)
        print_chronicles()
        print_changelog()
        print_learn()
        print_summaries()
        print_context(limit=8)
        print_tags()
        print_action_patterns()

    print()
    print("=" * 70)
    print("  Run 'python catchup.py --brief' for quick summary")
    print("  Run 'python catchup.py --query \"text\"' to search past summaries")
    print("  Run 'python catchup.py --learn' for decisions/experiences/insights")
    print("  Run 'python catchup.py --stream' for canonical MCP session:event tail")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
