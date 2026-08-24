"""
Robust Catch-Up from Redis
===========================
Run this in any new session to get FULL context from Redis.

This is what a NEW OpenCode session should run first thing!
"""
import sys
sys.path.insert(0, r"E:\AI-Setup")

def full_catchup():
    """Get complete session context from Redis"""
    import redis
    import json
    
    print("\n" + "="*70)
    print("  FULL CATCH-UP FROM REDIS")
    print("="*70)
    
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("[OK] Connected to Redis\n")
    except Exception as e:
        print(f"[ERROR] Cannot connect to Redis: {e}")
        return
    
    # 1. Get active sessions
    print("-" * 50)
    print("ACTIVE SESSIONS:")
    print("-" * 50)
    sessions = r.hgetall("sessions:active")
    for sid, data in sessions.items():
        try:
            info = json.loads(data)
            print(f"  [{sid}]")
            print(f"      Status: {info.get('status', 'unknown')}")
            print(f"      Task: {info.get('task', 'unknown')}")
            print(f"      Last action: {info.get('last_action', 'none')}")
            print(f"      Started: {info.get('started', 'unknown')}")
        except:
            print(f"  [{sid}] (parse error)")
    print()
    
    # 2. Get chat history
    print("-" * 50)
    print("CHAT HISTORY (last 20):")
    print("-" * 50)
    chat = r.lrange("chat:history", -20, -1)
    print(f"  Total messages: {len(chat)}")
    for c in chat[-10:]:
        try:
            msg = json.loads(c)
            role = msg.get("role", "?")[:8]
            text = msg.get("message", "")[:60].replace('\n', ' ')
            ts = msg.get("timestamp", "")[:16]
            print(f"  [{ts}] {role}: {text}")
        except:
            pass
    print()
    
    # 3. Get key learnings
    print("-" * 50)
    print("KEY LEARNINGS:")
    print("-" * 50)
    keys = ["crash_safe_logging", "launcher_fix", "launch_verifier", "system_onboarding"]
    for key in keys:
        val = r.hget("knowledge:facts", key)
        if val:
            print(f"  [{key}]")
            # Print first 100 chars
            print(f"      {val[:100]}...")
    print()
    
    # 4. Get recent errors
    print("-" * 50)
    print("RECENT ERRORS:")
    print("-" * 50)
    error_keys = []
    for key in r.keys("session:*:errors"):
        error_keys.append(key)
    if error_keys:
        for key in error_keys[:3]:
            errors = r.lrange(key, -5, -1)
            for e in errors:
                try:
                    err = json.loads(e)
                    print(f"  {err.get('error_type', 'error')}: {err.get('details', '')[:60]}")
                except:
                    pass
    else:
        print("  No errors logged")
    print()
    
    # 5. Instructions for next steps
    print("="*70)
    print("  NEXT STEPS:")
    print("="*70)
    print("""
  To continue this session:
  
  1. Import session logger:
     from session_logger import log, log_chat
     
  2. Log your actions:
     log('action_name', 'what you did')
     log_chat('assistant', 'your response')
     
  3. Check for errors in previous session:
     - See 'RECENT ERRORS' above
  
  4. Check session files:
     - E:\\AI-Setup\\session_logs\\*.jsonl
     - E:\\AI-Setup\\session_screenshots\\
  
  5. Run quick catch-up:
     from ai_helper import quick_catchup
     quick_catchup()
""")
    print("="*70 + "\n")

if __name__ == "__main__":
    full_catchup()