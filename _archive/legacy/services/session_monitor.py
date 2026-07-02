"""
Session Monitor - Track OpenCode Sessions and Logging Status
============================================================

**Prefer ``ai_watchdog.py`` / MCP ``ai_watchdog_report`` for unified ports + canonical ``session:events`` checks.
This module focuses on OpenCode-specific legacy LIST logs and file merging.

Monitors OpenCode sessions to detect:
- Which sessions ARE logging (have entries in Redis/file)
- Which sessions are SILENT (OpenCode but no logging)

Provides mechanisms to:
- Nudge silent sessions to start logging
- Re-prime sessions with patch-note thinking instructions
- Track session health over time

Usage:
    python session_monitor.py status    # Show session status
    python session_monitor.py nudge    # Nudge silent sessions
    python session_monitor.py --daemon # Run as background service

Redis Keys:
    sessions:active          - Hash of active sessions
    session:*:log           - Lists of session entries
    session:*:actions       - Action entries per session
    opencode:*              - OpenCode-specific sessions
"""

import os
import sys
import json
import time
import signal
import threading
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from collections import defaultdict

sys.path.insert(0, r"E:\AI-Setup")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from config import get_redis_config
SESSION_LOG_DIR = r"E:\AI-Setup\session_logs"
STATE_FILE = r"E:\AI-Setup\blackboard_data\session_monitor_state.json"
POLL_INTERVAL = 30  # seconds between checks
SILENCE_THRESHOLD_MINUTES = 5  # Consider silent if no log entries in this time


@dataclass
class SessionInfo:
    """Information about a session"""
    session_id: str
    is_opencode: bool
    has_redis_log: bool
    has_file_log: bool
    redis_entry_count: int = 0
    file_entry_count: int = 0
    last_activity: str = ""
    first_seen: str = ""
    is_logging: bool = False
    is_silent: bool = False
    nudged: int = 0
    last_nudge: str = ""


@dataclass
class MonitorState:
    """State for the session monitor"""
    last_check: str = ""
    sessions_tracked: Dict[str, dict] = field(default_factory=dict)
    silent_sessions: List[str] = field(default_factory=list)
    nudged_this_session: int = 0


PRIMER_MESSAGE = """
[SYSTEM] Session Logging Reminder
===================================
You're in an OpenCode session that hasn't been logging to Redis.

To ensure session continuity and learning:
1. Import the logger: from session_logger import log_action
2. Log your current task: log_action("Starting work on: <your task>")
3. Continue logging significant actions with: log_action("did X", tags=["tag"])

For patch-note style logging:
    from patch_log import feat, fix
    feat("system", "description", goal="why", result="SUCCESS")

Current session ID: {session_id}
Time: {timestamp}

This reminder is automated by the Session Monitor.
"""


class SessionMonitor:
    """Monitor OpenCode sessions and their logging status"""
    
    def __init__(self):
        self.state = MonitorState()
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self._lock = threading.Lock()
        self._load_state()
    
    def _load_state(self):
        """Load state from file"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.state = MonitorState(**data)
            except Exception as e:
                print(f"[Monitor] Failed to load state: {e}")
    
    def _save_state(self):
        """Save state to file"""
        try:
            os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
            with open(STATE_FILE, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
        except Exception as e:
            print(f"[Monitor] Failed to save state: {e}")
    
    def _connect_redis(self) -> bool:
        """Connect to Redis"""
        if not REDIS_AVAILABLE:
            return False
        
        try:
            if self.redis_client is None:
                from core.foundation.redis_connection import connect_to_redis_with_fail_fast
                cfg = get_redis_config()
                self.redis_client = connect_to_redis_with_fail_fast(
                    host=cfg["host"],
                    port=cfg["port"],
                    timeout_seconds=cfg.get("socket_connect_timeout", 5),
                    decode_responses=cfg.get("decode_responses", True),
                )
            if self.redis_client is None:
                raise ConnectionError("Redis not reachable")
            self.redis_client.ping()
            return True
        except:
            self.redis_client = None
            return False
    
    def _get_opencode_sessions_from_redis(self) -> Dict[str, SessionInfo]:
        """Get OpenCode sessions from Redis"""
        sessions = {}
        
        if not self._connect_redis():
            return sessions
        
        try:
            # Get all session keys
            keys = self.redis_client.keys('session:*')
            
            for key in keys:
                try:
                    # Parse session ID from key
                    # Key format: session:session_YYYYMMDD_HHMMSS:log or session:opencode_YYYYMMDD_HHMMSS:log
                    parts = key.split(':')
                    if len(parts) >= 2:
                        full_session = parts[1]
                        
                        # Extract just the session ID part
                        if ':' in full_session:
                            session_id = full_session
                        else:
                            session_id = full_session
                        
                        # Determine if OpenCode
                        is_opencode = 'opencode' in session_id.lower()
                        
                        # Get entry count from Redis
                        entry_count = 0
                        if key.endswith(':log'):
                            entry_count = self.redis_client.llen(key)
                        elif key.endswith(':actions'):
                            entry_count = self.redis_client.llen(key)
                        
                        sessions[session_id] = SessionInfo(
                            session_id=session_id,
                            is_opencode=is_opencode,
                            has_redis_log=True,
                            has_file_log=False,
                            redis_entry_count=entry_count,
                            last_activity=datetime.now().isoformat(),
                            first_seen=self.state.sessions_tracked.get(session_id, {}).get('first_seen', datetime.now().isoformat())
                        )
                except Exception as e:
                    continue
        except Exception as e:
            print(f"[Monitor] Error getting sessions: {e}")
        
        return sessions
    
    def _get_sessions_from_files(self) -> Dict[str, SessionInfo]:
        """Get sessions from log files"""
        sessions = {}
        
        log_file = os.path.join(SESSION_LOG_DIR, "session_all.jsonl")
        if not os.path.exists(log_file):
            return sessions
        
        try:
            session_counts = defaultdict(int)
            session_last_activity = {}
            
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        session = entry.get("session", "")
                        if session:
                            session_counts[session] += 1
                            ts = entry.get("timestamp", "")
                            if ts:
                                session_last_activity[session] = ts
                    except:
                        continue
            
            for session_id, count in session_counts.items():
                is_opencode = 'opencode' in session_id.lower()
                
                # Check if we already have this session from Redis
                if session_id in sessions:
                    sessions[session_id].has_file_log = True
                    sessions[session_id].file_entry_count = count
                else:
                    sessions[session_id] = SessionInfo(
                        session_id=session_id,
                        is_opencode=is_opencode,
                        has_redis_log=False,
                        has_file_log=True,
                        redis_entry_count=0,
                        file_entry_count=count,
                        last_activity=session_last_activity.get(session_id, ""),
                        first_seen=self.state.sessions_tracked.get(session_id, {}).get('first_seen', "")
                    )
        except Exception as e:
            print(f"[Monitor] Error reading files: {e}")
        
        return sessions
    
    def _update_session_status(self, sessions: Dict[str, SessionInfo]):
        """Update session logging status"""
        now = datetime.now()
        silence_threshold = now - timedelta(minutes=SILENCE_THRESHOLD_MINUTES)
        
        for session_id, info in sessions.items():
            # Determine if session is actively logging
            has_activity = False
            
            if info.has_redis_log and info.redis_entry_count > 0:
                has_activity = True
            
            if info.has_file_log and info.file_entry_count > 0:
                has_activity = True
            
            info.is_logging = has_activity
            
            # Determine if silent OpenCode session
            if info.is_opencode and not info.is_logging:
                info.is_silent = True
            
            # Update from saved state
            if session_id in self.state.sessions_tracked:
                saved = self.state.sessions_tracked[session_id]
                info.nudged = saved.get('nudged', 0)
                info.last_nudge = saved.get('last_nudge', '')
            
            # Update tracked state
            self.state.sessions_tracked[session_id] = {
                'first_seen': info.first_seen,
                'nudged': info.nudged,
                'last_nudge': info.last_nudge,
                'last_activity': info.last_activity,
                'is_logging': info.is_logging
            }
    
    def poll(self) -> Dict:
        """Poll and update session status"""
        stats = {
            "total_sessions": 0,
            "opencode_sessions": 0,
            "logging": 0,
            "silent": 0,
            "nudged": 0
        }
        
        with self._lock:
            self.state.last_check = datetime.now().isoformat()
            
            # Get sessions from both sources
            redis_sessions = self._get_opencode_sessions_from_redis()
            file_sessions = self._get_sessions_from_files()
            
            # Merge sessions
            all_sessions = {**file_sessions}
            for session_id, info in redis_sessions.items():
                if session_id in all_sessions:
                    all_sessions[session_id].has_redis_log = True
                    all_sessions[session_id].redis_entry_count = info.redis_entry_count
                else:
                    all_sessions[session_id] = info
            
            # Update status
            self._update_session_status(all_sessions)
            
            # Track silent OpenCode sessions
            self.state.silent_sessions = [
                sid for sid, info in all_sessions.items()
                if info.is_silent
            ]
            
            # Update stats
            stats["total_sessions"] = len(all_sessions)
            stats["opencode_sessions"] = sum(1 for s in all_sessions.values() if s.is_opencode)
            stats["logging"] = sum(1 for s in all_sessions.values() if s.is_logging)
            stats["silent"] = len(self.state.silent_sessions)
            
            self._save_state()
        
        return stats
    
    def nudge_silent_sessions(self) -> List[str]:
        """Nudge silent OpenCode sessions to start logging"""
        nudged = []
        
        if not self._connect_redis():
            return nudged
        
        for session_id in self.state.silent_sessions:
            try:
                # Create a nudge message in Redis
                nudge_key = f"nudge:{session_id}"
                nudge_data = {
                    "type": "logging_reminder",
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "message": PRIMER_MESSAGE.format(
                        session_id=session_id,
                        timestamp=datetime.now().isoformat()
                    ),
                    "action_required": "import logging and start recording actions"
                }
                
                self.redis_client.setex(
                    nudge_key,
                    300,  # Expire in 5 minutes
                    json.dumps(nudge_data)
                )
                
                # Also publish to agent_comm stream
                self.redis_client.publish(
                    "agent_comm:stream",
                    json.dumps({
                        "type": "system_reminder",
                        "session": session_id,
                        "message": "Your session hasn't been logging. Please import session_logger and start logging actions."
                    })
                )
                
                # Update state
                if session_id in self.state.sessions_tracked:
                    self.state.sessions_tracked[session_id]['nudged'] += 1
                    self.state.sessions_tracked[session_id]['last_nudge'] = datetime.now().isoformat()
                
                self.state.nudged_this_session += 1
                nudged.append(session_id)
                
            except Exception as e:
                print(f"[Monitor] Failed to nudge {session_id}: {e}")
        
        self._save_state()
        return nudged
    
    def get_primer_text(self) -> str:
        """Get primer text for non-logging sessions"""
        return PRIMER_MESSAGE
    
    def get_status(self) -> Dict:
        """Get current status"""
        return {
            "last_check": self.state.last_check,
            "sessions_tracked": len(self.state.sessions_tracked),
            "silent_sessions": self.state.silent_sessions,
            "nudged_total": self.state.nudged_this_session
        }
    
    def print_report(self):
        """Print a detailed session report"""
        print()
        print("=" * 60)
        print("  SESSION MONITOR REPORT")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Get fresh data
        stats = self.poll()
        
        print(f"\n  Summary:")
        print(f"    Total sessions tracked:   {stats['total_sessions']}")
        print(f"    OpenCode sessions:        {stats['opencode_sessions']}")
        print(f"    Sessions logging:         {stats['logging']}")
        print(f"    Silent (not logging):     {stats['silent']}")
        print(f"    Nudged this run:          {stats['nudged']}")
        
        if self.state.silent_sessions:
            print(f"\n  Silent OpenCode Sessions (NOT logging):")
            for sid in self.state.silent_sessions:
                saved = self.state.sessions_tracked.get(sid, {})
                nudge_count = saved.get('nudged', 0)
                last_nudge = saved.get('last_nudge', 'Never')
                print(f"    - {sid}")
                print(f"      Nudged: {nudge_count}x, Last: {last_nudge[:19] if last_nudge else 'Never'}")
        
        print()
        print("=" * 60)
        
        return stats


class MonitorRunner:
    """Runs the session monitor as a service"""
    
    def __init__(self):
        self.monitor = SessionMonitor()
        self._shutdown_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._nudge_counter = 0
    
    def _run_loop(self):
        """Main monitoring loop"""
        print(f"[SessionMonitor] Started - checking every {POLL_INTERVAL}s")
        
        while not self._shutdown_event.is_set():
            try:
                stats = self.monitor.poll()
                
                if stats['silent'] > 0:
                    self._nudge_counter += 1
                    if self._nudge_counter >= 2:  # Nudge every 2 poll cycles
                        nudged = self.monitor.nudge_silent_sessions()
                        if nudged:
                            print(f"[SessionMonitor] Nudged {len(nudged)} silent sessions")
                        self._nudge_counter = 0
                
                if stats['silent'] > 0 or stats['opencode_sessions'] > 0:
                    print(f"[SessionMonitor] {stats['opencode_sessions']} opencode, "
                          f"{stats['logging']} logging, {stats['silent']} silent")
                
            except Exception as e:
                print(f"[SessionMonitor] Error: {e}")
            
            self._shutdown_event.wait(POLL_INTERVAL)
        
        print("[SessionMonitor] Stopped")
    
    def start(self):
        """Start the monitor service"""
        if self._thread is not None and self._thread.is_alive():
            print("[SessionMonitor] Already running")
            return
        
        self._shutdown_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.monitor.running = True
    
    def stop(self):
        """Stop the monitor service"""
        self._shutdown_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        self.monitor.running = False
    
    def status(self):
        """Print current status"""
        self.monitor.print_report()


# Global runner
_runner: Optional[MonitorRunner] = None


def _signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n[SessionMonitor] Shutdown signal")
    if _runner:
        _runner.stop()
    sys.exit(0)


def get_runner() -> MonitorRunner:
    """Get or create the global runner"""
    global _runner
    if _runner is None:
        _runner = MonitorRunner()
    return _runner


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Session Monitor")
    parser.add_argument("cmd", nargs="?", choices=["status", "nudge", "daemon"], default="status")
    parser.add_argument("--daemon", action="store_true", help="Run as background service")
    args = parser.parse_args()
    
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    
    runner = get_runner()
    
    if args.cmd == "status" and not args.daemon:
        runner.status()
    elif args.cmd == "nudge":
        runner.monitor.poll()
        nudged = runner.monitor.nudge_silent_sessions()
        if nudged:
            print(f"Nudged {len(nudged)} sessions: {nudged}")
        else:
            print("No silent sessions to nudge")
    elif args.daemon or args.cmd == "daemon":
        runner.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            runner.stop()
