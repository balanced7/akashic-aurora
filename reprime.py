"""
Re-Prime Script - Force Session Re-priming
==========================================
Run this to force a re-prime sequence at any time.

Usage:
    python E:\AI-Setup\reprime.py              # Interactive re-prime
    python E:\AI-Setup\reprime.py --force      # Force without confirmation
    python E:\AI-Setup\reprime.py --check     # Just check session state
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, r'E:\AI-Setup')

SESSION_STATE_FILE = r"E:\AI-Setup\blackboard_data\session_state.json"
REPRIME_TRIGGER_FILE = r"E:\AI-Setup\blackboard_data\reprime_trigger.json"


def force_reprime():
    """Force a re-prime by clearing session state"""
    print("=" * 60)
    print("FORCE RE-PRIME")
    print("=" * 60)
    print()
    
    # 1. Archive current session
    if os.path.exists(SESSION_STATE_FILE):
        with open(SESSION_STATE_FILE, 'r') as f:
            old_state = json.load(f)
        
        # Save to history
        history_file = r"E:\AI-Setup\blackboard_data\session_history.json"
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r') as hf:
                history = json.load(hf)
        
        archived = {
            "session_id": old_state.get("session_id"),
            "unique_id": old_state.get("unique_id"),
            "started_at": old_state.get("started_at"),
            "ended_at": datetime.now().isoformat(),
            "reason": "force_reprime"
        }
        history.insert(0, archived)
        history = history[:20]  # Keep last 20
        
        with open(history_file, 'w') as hf:
            json.dump(history, hf, indent=2)
        
        print(f"Archived session: {old_state.get('session_id')}")
    
    # 2. Delete current session state (forces re-prime)
    if os.path.exists(SESSION_STATE_FILE):
        os.remove(SESSION_STATE_FILE)
        print("Cleared session state")
    
    # 3. Clear re-prime trigger if exists
    if os.path.exists(REPRIME_TRIGGER_FILE):
        os.remove(REPRIME_TRIGGER_FILE)
        print("Cleared re-prime trigger")
    
    # 4. Create re-prime trigger
    trigger_data = {
        "triggered_at": datetime.now().isoformat(),
        "reason": "force_reprime",
        "required_actions": [
            "Re-read STARTUP.md",
            "Re-initialize blackboard with init_blackboard(force=True)",
            "Run crash_recovery.get_summary()",
            "Verify logging with verify_logs()"
        ]
    }
    
    with open(REPRIME_TRIGGER_FILE, 'w') as f:
        json.dump(trigger_data, f, indent=2)
    
    print()
    print("Re-prime trigger created")
    print("Restart your session to trigger re-prime sequence")
    print()


def check_session_state():
    """Just check current session state without modifying"""
    print("=" * 60)
    print("SESSION STATE CHECK")
    print("=" * 60)
    print()
    
    if not os.path.exists(SESSION_STATE_FILE):
        print("No session state file found")
        print("This appears to be a fresh start")
        return
    
    with open(SESSION_STATE_FILE, 'r') as f:
        state = json.load(f)
    
    print(f"Session ID: {state.get('session_id', 'unknown')}")
    print(f"Unique ID: {state.get('unique_id', 'unknown')}")
    print(f"Started at: {state.get('started_at', 'unknown')}")
    print(f"Last check: {state.get('last_check', 'unknown')}")
    
    # Check history
    history_file = r"E:\AI-Setup\blackboard_data\session_history.json"
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            history = json.load(f)
        print(f"\nPrevious sessions in history: {len(history)}")
        if history:
            print(f"Last session: {history[0].get('session_id')}")
    
    # Check if re-prime trigger exists
    if os.path.exists(REPRIME_TRIGGER_FILE):
        print("\n[RE-PRIME TRIGGER EXISTS]")
        with open(REPRIME_TRIGGER_FILE, 'r') as f:
            trigger = json.load(f)
        print(f"  Triggered at: {trigger.get('triggered_at')}")
        print(f"  Reason: {trigger.get('reason')}")


def show_reprime_instructions():
    """Show what needs to be done for re-prime"""
    print("=" * 60)
    print("RE-PRIME INSTRUCTIONS")
    print("=" * 60)
    print()
    print("Run these commands in your session:")
    print()
    print("1. Force re-initialize blackboard:")
    print("   from blackboard import init_blackboard")
    print("   bb = init_blackboard(force=True)")
    print()
    print("2. Get summary from previous session:")
    print("   from crash_recovery import get_summary")
    print("   summary = get_summary()")
    print("   for s in summary.get('sessions', [])[:3]:")
    print("       print(f\"  [{s['session_id']}] {s.get('task')}\")")
    print()
    print("3. Verify logging integrity:")
    print("   from session_logger import verify_logs")
    print("   result = verify_logs(100)")
    print("   print(f\"Valid: {result['valid']}\")")
    print()
    print("4. Re-read key documentation:")
    print("   - E:\\AI-Setup\\STARTUP.md")
    print("   - E:\\AI-Setup\\ARCHITECTURE.md")
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-prime the session')
    parser.add_argument('--force', action='store_true', help='Force re-prime without confirmation')
    parser.add_argument('--check', action='store_true', help='Just check session state')
    parser.add_argument('--instructions', action='store_true', help='Show re-prime instructions')
    
    args = parser.parse_args()
    
    if args.check:
        check_session_state()
    elif args.instructions:
        show_reprime_instructions()
    elif args.force:
        force_reprime()
    else:
        print("Re-Prime Script")
        print("=" * 60)
        print()
        print("Options:")
        print("  --check        Show current session state")
        print("  --force        Force re-prime (archive current, clear state)")
        print("  --instructions Show what to do for re-prime")
        print()
        print("Examples:")
        print("  python reprime.py --check")
        print("  python reprime.py --force")
        print("  python reprime.py --instructions")
