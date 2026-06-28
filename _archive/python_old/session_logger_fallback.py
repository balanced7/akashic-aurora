#!/usr/bin/env python3
"""
Akashic Aurora - File-Based Session Logger (Fallback)
=========================================================

Works when Redis is unavailable. Provides same interface as redis-based logger.
Logs to JSONL with automatic dual-write for redundancy.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from threading import Lock

BASE_DIR = Path(r"E:\AI-Setup")
SESSION_LOGS_DIR = BASE_DIR / "session_logs"
SESSION_LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = SESSION_LOGS_DIR / "session_all.jsonl"
BACKUP_LOG_FILE = SESSION_LOGS_DIR / "backup_session_all.jsonl"
CANONICAL_EVENTS_FILE = SESSION_LOGS_DIR / "session_events_canonical.jsonl"

class FileBasedSessionLogger:
    """File-based fallback logger with dual-write redundancy"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        """Initialize logger"""
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.started_at = datetime.now().isoformat()
        self.sequence = 0
        self.entries = []

    def _write_entry(self, entry: Dict) -> None:
        """Write entry to both log files (dual-write)"""
        entry['sequence'] = self.sequence
        entry_json = json.dumps(entry)

        try:
            # Write to main log
            with open(LOG_FILE, 'a') as f:
                f.write(entry_json + '\n')
        except IOError as e:
            print(f"[WARNING] Could not write to main log: {e}")

        try:
            # Write to backup log (redundancy)
            with open(BACKUP_LOG_FILE, 'a') as f:
                f.write(entry_json + '\n')
        except IOError as e:
            print(f"[WARNING] Could not write to backup log: {e}")

        # If it's an event, also write to canonical events
        if entry.get('type') in ['chat', 'action', 'error']:
            try:
                with open(CANONICAL_EVENTS_FILE, 'a') as f:
                    f.write(entry_json + '\n')
            except IOError as e:
                print(f"[WARNING] Could not write to events log: {e}")

    def log_chat(self, role: str, message: str, timestamp: Optional[str] = None) -> None:
        """Log chat message"""
        self.sequence += 1
        entry = {
            'type': 'chat',
            'timestamp': timestamp or datetime.now().isoformat(),
            'session': self.session_id,
            'role': role,
            'message': message,
            'message_length': len(message),
        }
        self.entries.append(entry)
        self._write_entry(entry)

    def log_action(self, action: str, description: str, data: Dict = None) -> None:
        """Log action"""
        self.sequence += 1
        entry = {
            'type': 'action',
            'timestamp': datetime.now().isoformat(),
            'session': self.session_id,
            'action': action,
            'description': description,
            'data': data or {},
        }
        self.entries.append(entry)
        self._write_entry(entry)

    def log_error(self, error_type: str, details: str, traceback: str = "") -> None:
        """Log error"""
        self.sequence += 1
        entry = {
            'type': 'error',
            'timestamp': datetime.now().isoformat(),
            'session': self.session_id,
            'error_type': error_type,
            'details': details,
            'traceback': traceback,
        }
        self.entries.append(entry)
        self._write_entry(entry)

    def log_decision(self, decision: str, rationale: List[str] = None) -> None:
        """Log decision"""
        self.sequence += 1
        entry = {
            'type': 'decision',
            'timestamp': datetime.now().isoformat(),
            'session': self.session_id,
            'decision': decision,
            'rationale': rationale or [],
        }
        self.entries.append(entry)
        self._write_entry(entry)

    def log_startup(self, redis_available: bool = False) -> None:
        """Log session startup"""
        entry = {
            'type': 'logger_startup',
            'session': self.session_id,
            'unique_id': f"{self.session_id}_{datetime.now().strftime('%H%M%S')}",
            'redis': redis_available,
            'timestamp': datetime.now().isoformat(),
        }
        self._write_entry(entry)

    def log_shutdown(self, total_messages: int = 0) -> None:
        """Log session shutdown"""
        entry = {
            'type': 'logger_shutdown',
            'session': self.session_id,
            'total_messages': total_messages,
            'duration_seconds': (datetime.now() - datetime.fromisoformat(self.started_at)).total_seconds(),
            'timestamp': datetime.now().isoformat(),
        }
        self._write_entry(entry)

    def get_session_info(self) -> Dict:
        """Get current session info"""
        return {
            'session_id': self.session_id,
            'started_at': self.started_at,
            'entries_logged': len(self.entries),
            'log_files': {
                'main': str(LOG_FILE),
                'backup': str(BACKUP_LOG_FILE),
                'events': str(CANONICAL_EVENTS_FILE),
            }
        }

# Convenience functions
def log_chat(role: str, message: str) -> None:
    """Log a chat message"""
    logger = FileBasedSessionLogger()
    logger.log_chat(role, message)

def log_action(action: str, description: str, data: Dict = None) -> None:
    """Log an action"""
    logger = FileBasedSessionLogger()
    logger.log_action(action, description, data)

def log_error(error_type: str, details: str, traceback: str = "") -> None:
    """Log an error"""
    logger = FileBasedSessionLogger()
    logger.log_error(error_type, details, traceback)

def log_decision(decision: str, rationale: List[str] = None) -> None:
    """Log a decision"""
    logger = FileBasedSessionLogger()
    logger.log_decision(decision, rationale)

def get_session_id() -> str:
    """Get current session ID"""
    logger = FileBasedSessionLogger()
    return logger.session_id

if __name__ == '__main__':
    # Test the logger
    logger = FileBasedSessionLogger()
    logger.log_startup(redis_available=False)
    logger.log_action("test_init", "Testing file-based logger")
    logger.log_chat("user", "This is a test message")
    logger.log_chat("assistant", "This is a test response")
    logger.log_shutdown(total_messages=2)

    print(f"Session logged to:")
    info = logger.get_session_info()
    for key, value in info['log_files'].items():
        print(f"  {key}: {value}")
