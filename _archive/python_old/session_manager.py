"""
Session Manager - Session Tracking and Re-prime Detection
======================================================
Detects session changes and triggers re-priming to keep agents grounded.

How it works:
1. On startup, current SESSION_ID is compared against stored session
2. If different → User/AI restarted = Re-prime triggered
3. If same → Continuing session = Normal operation

Usage:
    from session_manager import get_session_manager, SessionState
    
    sm = get_session_manager()
    
    if sm.is_new_session():
        print("RE-PRIME REQUIRED")
        sm.trigger_reprime()
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Paths
SESSION_STATE_FILE = r"E:\AI-Setup\blackboard_data\session_state.json"
SESSION_HISTORY_FILE = r"E:\AI-Setup\blackboard_data\session_history.json"


class SessionState:
    """Holds current session information"""
    def __init__(self):
        self.session_id: str = ""
        self.unique_id: str = ""
        self.started_at: str = ""
        self.is_new: bool = False
        self.is_continuation: bool = False


class SessionManager:
    """
    Manages session lifecycle and detects when re-priming is needed.
    
    Session changes that trigger re-prime:
    - New SESSION_ID (AI or user restarted)
    - Session ID format: opencode_YYYYMMDD_HHMMSS
    """
    
    _instance: Optional['SessionManager'] = None
    
    def __init__(self):
        self._state: Optional[SessionState] = None
        self._previous_session: Optional[Dict] = None
        self._ensure_dirs()
    
    @classmethod
    def get_instance(cls) -> 'SessionManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _ensure_dirs(self):
        """Ensure directories exist"""
        os.makedirs(os.path.dirname(SESSION_STATE_FILE), exist_ok=True)
    
    def _load_state(self) -> Dict:
        """Load stored session state"""
        if os.path.exists(SESSION_STATE_FILE):
            try:
                with open(SESSION_STATE_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_state(self, state: Dict):
        """Save session state"""
        with open(SESSION_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _load_history(self) -> list:
        """Load session history"""
        if os.path.exists(SESSION_HISTORY_FILE):
            try:
                with open(SESSION_HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def _save_history(self, history: list):
        """Save session history"""
        with open(SESSION_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    
    def check_session(self, current_session_id: str, current_unique_id: str) -> SessionState:
        """
        Check if session has changed and return state.
        Call this on startup with the current SESSION_ID from session_logger.
        """
        state = self._load_state()
        stored_session_id = state.get("session_id", "")
        
        result = SessionState()
        result.session_id = current_session_id
        result.unique_id = current_unique_id
        result.started_at = datetime.now().isoformat()
        
        if stored_session_id != current_session_id:
            # Session changed - new startup
            result.is_new = True
            result.is_continuation = False
            
            # Archive previous session to history
            if stored_session_id:
                self._archive_session(state)
        else:
            # Same session - continuing
            result.is_new = False
            result.is_continuation = True
        
        self._previous_session = state if stored_session_id else None
        self._state = result
        
        # Update stored state
        self._save_state({
            "session_id": current_session_id,
            "unique_id": current_unique_id,
            "started_at": result.started_at,
            "last_check": datetime.now().isoformat()
        })
        
        return result
    
    def _archive_session(self, old_state: Dict):
        """Archive completed session to history"""
        history = self._load_history()
        
        archived = {
            "session_id": old_state.get("session_id"),
            "unique_id": old_state.get("unique_id"),
            "started_at": old_state.get("started_at"),
            "ended_at": datetime.now().isoformat(),
            "reason": "session_change"
        }
        
        history.insert(0, archived)  # Most recent first
        
        # Keep last 20 sessions
        history = history[:20]
        
        self._save_history(history)
    
    def is_new_session(self) -> bool:
        """Returns True if this is a new session requiring re-prime"""
        if self._state is None:
            return True
        return self._state.is_new
    
    def is_continuation(self) -> bool:
        """Returns True if continuing same session"""
        if self._state is None:
            return False
        return self._state.is_continuation
    
    def get_previous_session(self) -> Optional[Dict]:
        """Get info about the previous session if there was one"""
        return self._previous_session
    
    def get_current_state(self) -> Optional[SessionState]:
        """Get current session state"""
        return self._state
    
    def trigger_reprime(self) -> Dict:
        """
        Trigger re-prime sequence.
        Returns instructions for what needs to be re-read.
        """
        reprime_data = {
            "triggered_at": datetime.now().isoformat(),
            "previous_session": self._previous_session,
            "current_session": self._state.session_id if self._state else None,
            "required_actions": [
                {
                    "action": "read",
                    "file": "E:\\AI-Setup\\STARTUP.md",
                    "purpose": "Re-read startup sequence"
                },
                {
                    "action": "read",
                    "file": "E:\\AI-Setup\\blackboard_data\\session_state.json",
                    "purpose": "Understand current session context"
                },
                {
                    "action": "call",
                    "function": "crash_recovery.get_summary",
                    "purpose": "Get context from previous session"
                },
                {
                    "action": "call",
                    "function": "blackboard.init_blackboard",
                    "purpose": "Re-initialize state machine"
                }
            ]
        }
        
        # Save reprime trigger
        reprime_file = r"E:\AI-Setup\blackboard_data\reprime_trigger.json"
        with open(reprime_file, 'w') as f:
            json.dump(reprime_data, f, indent=2)
        
        return reprime_data
    
    def get_reprime_instructions(self) -> str:
        """Get human-readable re-prime instructions"""
        if self.is_continuation():
            return "Continuing session - no re-prime needed."
        
        instructions = []
        instructions.append("=" * 60)
        instructions.append("RE-PRIME REQUIRED - NEW SESSION DETECTED")
        instructions.append("=" * 60)
        instructions.append("")
        instructions.append("Run these commands in order:")
        instructions.append("")
        instructions.append("1. Re-initialize blackboard:")
        instructions.append("   from blackboard import init_blackboard")
        instructions.append("   bb = init_blackboard()")
        instructions.append("")
        instructions.append("2. Get catch-up from previous session:")
        instructions.append("   from crash_recovery import get_summary")
        instructions.append("   get_summary()")
        instructions.append("")
        instructions.append("3. Verify logging:")
        instructions.append("   from session_logger import verify_logs")
        instructions.append("   verify_logs(100)")
        instructions.append("")
        instructions.append("4. Read STARTUP.md for reference:")
        instructions.append("   ( Already reading it )")
        instructions.append("")
        instructions.append("=" * 60)
        
        return "\n".join(instructions)


def get_session_manager() -> SessionManager:
    """Convenience function to get SessionManager instance"""
    return SessionManager.get_instance()


def check_and_reprime(current_session_id: str, current_unique_id: str) -> SessionState:
    """
    One-shot session check and reprime trigger.
    Call this at the START of every session.
    
    Returns SessionState with is_new flag.
    If is_new=True, call trigger_reprime() and show instructions.
    """
    sm = get_session_manager()
    state = sm.check_session(current_session_id, current_unique_id)
    
    if state.is_new:
        sm.trigger_reprime()
    
    return state
