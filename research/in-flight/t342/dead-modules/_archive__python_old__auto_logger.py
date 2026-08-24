"""
Auto Logger - Automated Session Logging Without Agent Involvement
=================================================================

This module provides automatic logging by:
1. Parsing conversation history
2. Extracting file operations
3. Detecting decisions
4. Logging everything without requiring explicit agent calls

Usage (in bootstrap or auto-start):
    from auto_logger import AutoLogger
    auto = AutoLogger()
    auto.capture_session()  # Captures current session
    
Or run standalone:
    python auto_logger.py capture

"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter

BASE_DIR = Path(r"E:\AI-Setup")
SESSION_LOG_DIR = BASE_DIR / "session_logs"
LOG_FILE = SESSION_LOG_DIR / "session_all.jsonl"
BACKUP_LOG_FILE = SESSION_LOG_DIR / "backup_session_all.jsonl"

os.makedirs(SESSION_LOG_DIR, exist_ok=True)


class AutoLogger:
    """
    Automatically captures session actions from conversation context.
    No agent involvement required - parses and logs everything.
    """
    
    FILE_OPS = {
        'created': ['wrote', 'created', 'generated'],
        'edited': ['edited', 'modified', 'updated', 'changed'],
        'read': ['read', 'checked', 'examined', 'inspected'],
        'deleted': ['deleted', 'removed'],
        'executed': ['ran', 'executed', 'launched', 'started', 'stopped'],
    }
    
    TAG_PATTERNS = {
        "setup": ["bootstrap", "docker", "redis", "install", "launch", "start"],
        "automation": ["bat", "script", "batch", "automated", "auto"],
        "logging": ["log", "session", "monitor", "track"],
        "infrastructure": ["service", "container", "cluster", "ha"],
        "debugging": ["error", "fail", "fix", "issue", "problem"],
    }
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.entries: List[Dict] = []
        self.sequence = 0
        
    def _auto_tag(self, content: str) -> List[str]:
        """Auto-generate tags from content"""
        content_lower = content.lower()
        tags = []
        for tag, patterns in self.TAG_PATTERNS.items():
            if any(p in content_lower for p in patterns):
                tags.append(tag)
        return tags or ["general"]
    
    def _log(self, type_: str, content: str, tags: List[str] = None):
        """Internal log method"""
        self.sequence += 1
        auto_tags = self._auto_tag(content)
        if tags:
            auto_tags = list(set(auto_tags + tags))
        
        entry = {
            "type": type_,
            "timestamp": datetime.now().isoformat(),
            "sequence": self.sequence,
            "session": self.session_id,
            "content": content[:200],
            "tags": auto_tags,
            "data": {"auto": True}
        }
        
        self.entries.append(entry)
        
        # Dual-write to files
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except:
            pass
        
        try:
            with open(BACKUP_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except:
            pass
    
    def log_action(self, description: str, tags: List[str] = None):
        """Log an action"""
        self._log("action", description, tags)
    
    def log_decision(self, title: str, rationale: str = ""):
        """Log a decision"""
        content = f"Decision: {title}"
        if rationale:
            content += f" - {rationale}"
        self._log("decision", content, ["learning"])
    
    def parse_and_log_conversation(self, messages: List[Dict]) -> int:
        """
        Parse conversation messages and auto-log actions.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            
        Returns:
            Number of actions logged
        """
        actions_logged = 0
        
        for msg in messages:
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if not content:
                continue
            
            # Parse file operations
            if role == 'assistant':
                # Detect file creations
                if 'Wrote file' in content or 'Created' in content:
                    match = re.search(r'(?:Wrote file|Created)[^\n]*?\n*([^\n]+\.bat|\.py|\.md|\.json)', content)
                    if match:
                        self.log_action(f"Created {match.group(1).strip()}", ["automation"])
                        actions_logged += 1
                
                # Detect file edits
                if 'Edited' in content or 'Modified' in content:
                    self.log_action("Edited existing file", ["automation"])
                    actions_logged += 1
                
                # Detect service launches
                if 'Starting' in content or 'Started' in content or 'Launching' in content:
                    if any(s in content for s in ['Redis', 'Docker', 'sync', 'monitor']):
                        self.log_action(f"Started service: {content[:50]}", ["infrastructure"])
                        actions_logged += 1
                
                # Detect status checks
                if 'status' in content.lower() or 'Status' in content:
                    if 'Running' in content or 'OK' in content or 'Ready' in content:
                        self.log_action("Verified service status", ["infrastructure"])
                        actions_logged += 1
            
            # Parse user requests
            if role == 'user':
                # Detect task requests
                if 'check' in content.lower() or 'verify' in content.lower():
                    self.log_action(f"User request: {content[:60]}", ["general"])
                    actions_logged += 1
                
                # Detect setup requests
                if 'bootstrap' in content.lower() or 'initialize' in content.lower():
                    self.log_action("Bootstrap requested", ["setup"])
                    actions_logged += 1
        
        return actions_logged
    
    def capture_current_session(self) -> int:
        """
        Capture the current session by reading recent log entries
        and generating actions.
        
        Returns:
            Number of actions captured
        """
        captured = 0
        
        # Check for recent session log entries
        if LOG_FILE.exists():
            try:
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Get entries from last 30 minutes
                cutoff = datetime.now().timestamp() - 1800
                recent_sessions = set()
                
                for line in lines[-100:]:
                    try:
                        entry = json.loads(line)
                        ts = entry.get('timestamp', '')
                        if ts:
                            try:
                                entry_time = datetime.fromisoformat(ts).timestamp()
                                if entry_time > cutoff:
                                    recent_sessions.add(entry.get('session', ''))
                            except:
                                pass
                    except:
                        pass
                
                if recent_sessions:
                    self.log_action(f"Session captured {len(recent_sessions)} recent sessions", ["logging"])
                    captured += 1
                    
            except Exception as e:
                self.log_action(f"Auto-capture: {str(e)[:50]}", ["debugging"])
        
        return captured
    
    def log_bootstrap_complete(self, services: List[str] = None):
        """Log bootstrap completion"""
        services = services or ["Redis HA", "Sync Service"]
        for svc in services:
            self.log_action(f"Service running: {svc}", ["infrastructure"])
    
    def log_opencode_started(self, primed: bool = True):
        """Log OpenCode launch"""
        status = "fully primed" if primed else "standard"
        self.log_action(f"OpenCode started ({status})", ["setup"])
    
    def save(self) -> Dict:
        """Save session summary"""
        return {
            "session_id": self.session_id,
            "entries_captured": len(self.entries),
            "timestamp": datetime.now().isoformat()
        }


def quick_capture(session_id: str = None) -> int:
    """
    Quick one-liner to capture current session state.
    
    Usage:
        python auto_logger.py capture
        python auto_logger.py capture --session opencode_20260416_123456
    """
    auto = AutoLogger(session_id)
    
    # Log bootstrap state
    auto.log_action("Bootstrap check initiated", ["setup"])
    
    # Capture any recent activity
    captured = auto.capture_current_session()
    
    # Log summary
    summary = auto.save()
    print(f"Captured {len(auto.entries)} entries for session {summary['session_id']}")
    
    return len(auto.entries)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto Logger")
    parser.add_argument("cmd", nargs="?", choices=["capture", "status", "test"], default="capture")
    parser.add_argument("--session", help="Session ID to use")
    args = parser.parse_args()
    
    if args.cmd == "capture":
        count = quick_capture(args.session)
        print(f"Logged {count} entries")
    elif args.cmd == "status":
        auto = AutoLogger(args.session)
        print(f"Session: {auto.session_id}")
        print(f"Entries: {len(auto.entries)}")
    elif args.cmd == "test":
        auto = AutoLogger("test_session")
        auto.log_action("Test action 1")
        auto.log_action("Created test.bat", ["automation"])
        auto.log_decision("Test decision", "For testing")
        print(f"Test complete: {len(auto.entries)} entries logged")
