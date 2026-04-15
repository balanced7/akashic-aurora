"""
Crash Recovery - Catch up after crash
======================================
Run this to recover context from a crashed session.

Usage:
    from crash_recovery import recover, get_summary
    summary = get_summary()
    recover()
"""
import os
import json
import redis
from datetime import datetime, timedelta

LOG_DIR = r"E:\AI-Setup\session_logs"

# Connection pool - reuse connections
_redis_pool = None

def _get_redis_pool():
    """Get or create Redis connection pool"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True, max_connections=10)
    return _redis_pool

def _get_redis_client():
    """Get Redis client from pool"""
    try:
        r = redis.Redis(connection_pool=_get_redis_pool())
        r.ping()
        return r, True
    except:
        return None, False

def get_summary():
    """Get summary of recent sessions and what happened"""
    summary = {
        "sessions": [],
        "chat_history": [],
        "learnings": {},
        "last_task": None,
        "last_error": None
    }
    
    r, redis_available = _get_redis_client()
    
    if not redis_available:
        summary["error"] = "Redis not available"
        return summary
    
    try:
        # Get active sessions
        sessions = r.hgetall("sessions:active")
        for sid, data in sessions.items():
            try:
                info = json.loads(data)
                summary["sessions"].append({
                    "session_id": sid,
                    "task": info.get("task", "unknown"),
                    "status": info.get("status", "unknown"),
                    "last_action": info.get("last_action", "none")
                })
            except:
                pass
        
        # Get last error
        error_keys = r.keys("session:*:errors")
        if error_keys:
            last_error = r.lrange(error_keys[0], -1, -1)
            if last_error:
                try:
                    summary["last_error"] = json.loads(last_error[0])
                except:
                    pass
        
        # Get recent learnings using pipeline
        pipe = r.pipeline()
        for key in r.keys("kb:learning:*"):
            pipe.get(key)
        learnings = pipe.execute()
        for i, key in enumerate(r.keys("kb:learning:*")):
            summary["learnings"][key] = learnings[i]
        
        # Get chat history
        chat = r.lrange("chat:history", -30, -1)
        summary["chat_history"] = [json.loads(c) for c in chat] if chat else []
        
    except Exception as e:
        summary["error"] = str(e)
    
    return summary

def get_session_log(session_id):
    """
    Get full log for a session from the unified session_all.jsonl file.
    FIXED: Now reads from session_all.jsonl and filters by session_id embedded in entries.
    """
    log_file = os.path.join(LOG_DIR, "session_all.jsonl")
    
    if not os.path.exists(log_file):
        return []
    
    log = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                # Filter entries belonging to this session
                if entry.get("session") == session_id:
                    log.append(entry)
            except:
                pass
    
    return log

def find_last_session():
    """Find the most recent session that was active"""
    r, redis_available = _get_redis_client()
    
    if redis_available:
        try:
            sessions = r.hgetall("sessions:active")
            
            # Find most recent active session
            active = []
            for sid, data in sessions.items():
                try:
                    info = json.loads(data)
                    if info.get("status") == "active":
                        active.append((sid, info))
                except:
                    pass
            
            if active:
                # Sort by updated time
                active.sort(key=lambda x: x[1].get("updated", ""), reverse=True)
                return active[0][0]
            
        except:
            pass
    
    # Fallback: find latest log entry in session_all.jsonl
    log_file = os.path.join(LOG_DIR, "session_all.jsonl")
    if os.path.exists(log_file):
        last_session = None
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    last_session = entry.get("session")
                except:
                    pass
        if last_session:
            return last_session
    
    return None

def recover():
    """Main recovery - print what happened"""
    print("=" * 70)
    print("  CRASH RECOVERY")
    print("=" * 70)
    print()
    
    summary = get_summary()
    
    if "error" in summary:
        print(f"Redis error: {summary['error']}")
        return
    
    # Print recent sessions
    print("RECENT SESSIONS:")
    print("-" * 40)
    if summary["sessions"]:
        for s in summary["sessions"][:5]:
            print(f"  [{s['session_id']}]")
            print(f"    Task: {s.get('task', 'unknown')}")
            print(f"    Last action: {s.get('last_action', 'none')}")
            print(f"    Status: {s.get('status', 'unknown')}")
            print()
    else:
        print("  No recent sessions")
        print()
    
    # Print last error
    if summary["last_error"]:
        print("LAST ERROR:")
        print("-" * 40)
        err = summary["last_error"]
        print(f"  Type: {err.get('error_type', 'unknown')}")
        print(f"  Details: {err.get('details', 'N/A')}")
        if err.get("traceback"):
            print(f"  Traceback: {err['traceback'][:200]}...")
        print()
    
    # Print recent learnings
    print("RECENT LEARNINGS:")
    print("-" * 40)
    learnings = list(summary["learnings"].items())[:5]
    if learnings:
        for key, value in learnings:
            try:
                data = json.loads(value)
                print(f"  [{key}] {data.get('category', 'general')}: {data.get('key', key)}")
            except:
                print(f"  [{key}] {value[:50]}...")
    else:
        print("  No learnings stored")
    print()
    
    # Print recent chat
    print("RECENT CHAT:")
    print("-" * 40)
    if summary["chat_history"]:
        for chat in summary["chat_history"][-5:]:
            role = chat.get("role", "unknown")
            msg = chat.get("message", "")[:80]
            print(f"  {role}: {msg}")
    else:
        print("  No chat history")
    print()
    
    # Find and print last session log
    last_session = find_last_session()
    if last_session:
        print(f"LAST SESSION LOG ({last_session}):")
        print("-" * 40)
        log = get_session_log(last_session)
        
        if log:
            for entry in log[-10:]:
                ts = entry.get("timestamp", "")[11:19] if entry.get("timestamp") else ""
                action = entry.get("action", "unknown")
                desc = entry.get("description", entry.get("data", ""))
                print(f"  {ts} {action}: {str(desc)[:60]}")
        else:
            print("  (log file empty or missing)")
    print()
    
    print("=" * 70)
    print("  Use session_logger.SessionLogger() to auto-log everything")
    print("=" * 70)

def auto_recover_on_startup():
    """Call this at start of any session to auto-recover"""
    summary = get_summary()
    
    # Check if there was a crash
    if summary.get("last_error"):
        print("\n[RECOVER] Previous session had an error:")
        err = summary["last_error"]
        print(f"  {err.get('error_type')}: {err.get('details')}")
        print()
        
        # Find what task was being worked on
        for s in summary.get("sessions", []):
            if s.get("status") == "active":
                print(f"  Task: {s.get('task', 'unknown')}")
                print(f"  Last action: {s.get('last_action', 'none')}")
                break
        
        print()
        print("Run 'recover()' for full details")
        return summary
    
    return None


if __name__ == "__main__":
    recover()