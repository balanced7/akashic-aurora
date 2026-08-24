"""
Auto-Catchup Module
===================
Run this immediately at startup to get up to speed.

Usage:
    from auto_catchup import run
    run()  # Shows recent sessions and chat
    
Or just:
    python E:\AI-Setup\auto_catchup.py
"""
import sys
sys.path.insert(0, r"E:\AI-Setup")

def run():
    """Run full catch-up"""
    from session_logger import get_chat_history, get_recent_sessions
    from screenshot_logger import get_recent_screenshots
    
    print()
    print("=" * 70)
    print("  AUTO-CATCHUP - Session Continuity")
    print("=" * 70)
    print()
    
    # Recent sessions
    sessions = get_recent_sessions(5)
    print(f"RECENT SESSIONS: {len(sessions)}")
    for s in sessions:
        sid = s.get("session_id", "?")[-15:]
        task = s.get("task", "unknown")
        status = s.get("status", "?")
        print(f"  [{sid}] {task[:30]} - {status}")
    
    # Recent chats
    print()
    chats = get_chat_history(20)
    print(f"RECENT CHAT HISTORY: {len(chats)} messages")
    for c in chats[-10:]:
        role = c.get("role", "?")[:8]
        msg = c.get("message", "")[:70].replace('\n', ' ')
        print(f"  {role:8} {msg}")
    
    # Recent screenshots
    print()
    screenshots = get_recent_screenshots(5)
    print(f"RECENT SCREENSHOTS: {len(screenshots)}")
    for s in screenshots[:5]:
        print(f"  {s[:60]}...")
    
    print()
    print("=" * 70)
    print("  Use log() to log every action!")
    print("  Use log_chat('assistant', 'response') to save your answers!")
    print("=" * 70)
    print()

if __name__ == "__main__":
    run()