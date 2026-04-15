"""
OpenCode Crash-Safe Launcher
=============================
Launches OpenCode with full context, OCR capabilities, and automatic logging.
All actions saved to Redis AND files for crash recovery.
Uses launch_verifier to confirm the app opened successfully.

CRITICAL: This launcher MUST pass session context to the OpenCode instance itself!
"""
import subprocess
import sys
import os
import time
import redis
import json
from datetime import datetime

LOG_DIR = r"E:\AI-Setup\session_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Import launch verifier
sys.path.insert(0, r"E:\AI-Setup")
from launch_verifier import verify_launch, LaunchConfig

def get_or_create_session():
    """Get existing active session OR create new one"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Check for existing active sessions
        sessions = r.hgetall("sessions:active")
        for sid, data in sessions.items():
            try:
                info = json.loads(data)
                if info.get("status") == "active":
                    return sid  # Use existing session
            except:
                pass
        
        # No active session - create new one
        return f"opencode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    except:
        return f"opencode_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Get session ID - prefer existing active session
SESSION_ID = get_or_create_session()

def log_action(action, data=None):
    """Log action to Redis AND file"""
    entry = {
        "session": SESSION_ID,
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "data": data or {}
    }
    
    # Save to file
    log_file = os.path.join(LOG_DIR, f"{SESSION_ID}.jsonl")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # Save to Redis
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.rpush(f"session:{SESSION_ID}:actions", json.dumps(entry))
        r.expire(f"session:{SESSION_ID}:actions", 86400 * 7)
        
        # Update active session info
        r.hset("sessions:active", SESSION_ID, json.dumps({
            "status": "active",
            "task": data.get("task", "continuing") if data else "continuing",
            "last_action": action,
            "started": datetime.now().isoformat()
        }))
    except:
        pass
    
    print(f"[LOG] {action}")

def get_crash_recovery_info():
    """Get info to help recover from crashes"""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Get recent sessions
        sessions = r.hgetall("sessions:active")
        recent = []
        for sid, data in sessions.items():
            try:
                recent.append(json.loads(data))
            except:
                pass
        
        # Get chat history
        chat = r.lrange("chat:history", -30, -1)  # Increased to 30
        chat_history = [json.loads(c) for c in chat] if chat else []
        
        # Get recent learnings
        learnings = {}
        for key in r.keys("kb:learning:*"):
            learnings[key] = r.get(key)
        
        # Get session actions for continuity
        session_actions = r.lrange(f"session:{SESSION_ID}:actions", -20, -1) if SESSION_ID else []
        
        return {
            "recent_sessions": recent,
            "chat_history": chat_history,
            "learnings": learnings,
            "session_actions": [json.loads(a) for a in session_actions] if session_actions else []
        }
    except Exception as e:
        return {"error": str(e)}

def print_primed_intro():
    """Print intro with full context"""
    print()
    print("=" * 70)
    print("  OPENCODE - CRASH-SAFE PRIMED LAUNCHER")
    print("=" * 70)
    print()
    print(f"Session ID: {SESSION_ID}")
    print(f"Log file: {LOG_DIR}\{SESSION_ID}.jsonl")
    print()
    
    # Get system status
    recovery = get_crash_recovery_info()
    
    print("=== CATCH-UP INFO (Read this to understand what was happening) ===")
    print("-" * 50)
    
    if "error" not in recovery:
        # Show previous session actions
        prev_actions = recovery.get("session_actions", [])
        if prev_actions:
            print(f"Previous session had {len(prev_actions)} actions:")
            for a in prev_actions[-5:]:
                ts = a.get("timestamp", "")[11:19] if a.get("timestamp") else ""
                print(f"  {ts} {a.get('action', '?')}: {a.get('data', {}).get('task', '')}")
        
        # Show recent chat for context
        chats = recovery.get("chat_history", [])
        if chats:
            print(f"\nRecent chat history ({len(chats)} messages):")
            for c in chats[-5:]:
                role = c.get("role", "?")[:8]
                msg = c.get("message", "")[:60].replace('\n', ' ')
                print(f"  [{role}] {msg}")
    
    print()
    print("=== YOUR CAPABILITIES ===")
    print("-" * 40)
    print("  [OCR] ai_helper.ocr() - Read text from screen")
    print("  [OCR] ai_helper.ui_scout('window') - Deep UI inspection")
    print("  [OCR] ai_helper.hybrid_inspect() - UI + OCR combined")
    print("  [OCR] ai_helper.ui_click(x, y) - Click UI elements")
    print("  [OCR] ai_helper.get_visual_context() - Full visual map")
    print()
    print("  [LOG] from session_logger import log, log_chat, log_error")
    print("  [LOG] log('action', 'description') - Log everything!")
    print()
    print("=== COLLABORATION RULES ===")
    print("-" * 40)
    print("  1. Log EVERY action with log() - CRASH-SAFE!")
    print("  2. Log errors with log_error()")
    print("  3. Use session_logger for crash protection")
    print("  4. Check Redis before major operations")
    print("  5. Save state after important tasks")
    print()
    print("=== KEY FILES ===")
    print("-" * 40)
    print("  - E:\\AI-Setup\\ai_helper.py - OCR, UI, helper functions")
    print("  - E:\\AI-Setup\\session_logger.py - Crash-safe logging")
    print("  - E:\\AI-Setup\\ui_scout.py - Naturo UI automation")
    print("  - E:\\AI-Setup\\screenshot_logger.py - Session screenshots")
    print("  - E:\\AI-Setup\\session_logs\\ - Session history")
    print("  - E:\\AI-Setup\\session_screenshots\\ - Screenshots")
    print()
    
    # Log this launch with CONTINUATION flag
    log_action("session_continued", {
        "session_id": SESSION_ID,
        "previous_actions": len(recovery.get("session_actions", [])),
        "continuing": True
    })
    
    print("=" * 70)
    print("  Session will be logged to Redis AND files!")
    print("  If you crash, run crash_recovery.recover() to catch up!")
    print("=" * 70)
    print()
    
    # Print explicit commands to run for full catch-up
    print("RUN THESE COMMANDS FOR FULL CATCH-UP:")
    print("-" * 40)
    print(f"python -c \"import sys; sys.path.insert(0, r'E:\\AI-Setup'); from session_logger import get_chat_history; chats = get_chat_history(20); [print(f'{c.get(\\\"role\\\")}: {c.get(\\\"message\\\", \\\"\")[:80]}') for c in chats]\"")
    print()
    print("OR run: python E:\\AI-Setup\\crash_recovery.py")
    print()

def launch_opencode():
    """Launch OpenCode or PowerShell with context"""
    log_action("attempting_launch", {"method": "opencode"})
    
    # Try OpenCode first
    opencode_paths = [
        "opencode",
        r"C:\Users\L5\AppData\Local\Programs\OpenCode\opencode.exe"
    ]
    
    for cmd in opencode_paths:
        try:
            subprocess.run([cmd, "--version"], capture_output=True, timeout=3)
            log_action("launched_opencode", {"cmd": cmd})
            
            # Launch and verify it opened
            process_name = "opencode.exe" if ".exe" in cmd.lower() else "opencode"
            subprocess.Popen([cmd])  # Use Popen to not block
            
            # Verify launch
            print("\nVerifying launch...")
            config = LaunchConfig(
                name="OpenCode",
                process_name=process_name,
                gui=True,
                screen_text="opencode",
                max_wait=15
            )
            result = verify_launch(config)
            
            log_action("launch_verified", result)
            
            if result["success"]:
                print(f"  [OK] Verified: {result['message']}")
            else:
                print(f"  [WARN] {result['message']}")
                print(f"         Checks performed: {len(result['checks'])}")
            
            return True
        except Exception as e:
            log_action("launch_error", {"cmd": cmd, "error": str(e)})
            continue
    
    # Fallback: PowerShell with primed session
    log_action("fallback_powershell", {})
    
    # Create PowerShell profile with imports
    ps_profile = r"""
# OpenCode Primed Profile
Write-Host ""
Write-Host "=== PRIMED POWERSHELL SESSION ===" -ForegroundColor Green
Write-Host "Session ID: {SESSION_ID}"
Write-Host ""
Write-Host "Available modules:" -ForegroundColor Yellow
Write-Host "  - ai_helper: ocr(), status(), learn(), ui_list(), ui_inspect(), diag()"
Write-Host "  - session_logger: SessionLogger for crash-safe logging"
Write-Host "  - knowledge_base: KB() for shared learnings"
Write-Host ""

# Import ai_helper
$env:PYTHONPATH = "E:\AI-Setup"
python -c "import sys; sys.path.insert(0, r'E:\AI-Setup'); from ai_helper import *; print('[OK] ai_helper imported')"

# Print catch-up
python E:\AI-Setup\catch_up.py
""".format(SESSION_ID=SESSION_ID)
    
    try:
        subprocess.Popen(["powershell.exe", "-NoExit", "-Command", ps_profile])
        log_action("launched_powershell", {"profile": "primed"})
        return True
    except Exception as e:
        log_action("launch_failed", {"error": str(e)})
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    print_primed_intro()
    time.sleep(1)
    launch_opencode()
    print("\n[Session logged. Check E:\\AI-Setup\\session_logs\\]")