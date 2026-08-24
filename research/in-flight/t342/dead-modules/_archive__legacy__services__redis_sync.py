"""
Redis Sync Poller - Persistent Low-Resource Background Sync
==========================================================
Continuously polls session logs and syncs new entries to Redis.
Runs as a background service with minimal resource usage.

Features:
- Low CPU usage polling (5 second intervals)
- Tracks last synced position per file
- Only syncs NEW entries since last sync
- Automatic reconnection on Redis failure
- Graceful shutdown on SIGTERM/SIGINT
- Progress checkpointing to avoid re-syncing

Usage:
    python redis_sync.py              # Start sync service
    python redis_sync.py --status   # Check sync status
    python redis_sync.py --reset    # Reset sync positions
"""

import os
import sys
import json
import time
import signal
import threading
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

sys.path.insert(0, r"E:\AI-Setup")

REDIS_HOST = "localhost"
REDIS_PORT = 6379
SESSION_LOG_DIR = r"E:\AI-Setup\session_logs"
SYNC_STATE_FILE = r"E:\AI-Setup\blackboard_data\redis_sync_state.json"
POLL_INTERVAL = 5  # seconds between checks


@dataclass
class SyncState:
    """Tracks sync progress for each log file"""
    session_all_position: int = 0
    session_all_lines: int = 0
    backup_session_position: int = 0
    errors_position: int = 0
    last_sync: str = ""
    last_redis_check: str = ""
    redis_available: bool = False


class RedisSyncPoller:
    def __init__(self):
        self.state = SyncState()
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self._lock = threading.Lock()
        self._load_state()
        
    def _load_state(self):
        """Load sync state from file"""
        if os.path.exists(SYNC_STATE_FILE):
            try:
                with open(SYNC_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.state = SyncState(**data)
                print(f"[RedisSync] Loaded state: last sync={self.state.last_sync}")
            except Exception as e:
                print(f"[RedisSync] Failed to load state: {e}")
    
    def _save_state(self):
        """Save sync state to file"""
        try:
            with open(SYNC_STATE_FILE, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
        except Exception as e:
            print(f"[RedisSync] Failed to save state: {e}")
    
    def _connect_redis(self) -> bool:
        """Connect to Redis with retry logic"""
        if not REDIS_AVAILABLE:
            return False
            
        try:
            if self.redis_client is None:
                from core.foundation.redis_connection import connect_to_redis_with_fail_fast
                self.redis_client = connect_to_redis_with_fail_fast(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    timeout_seconds=5,
                    decode_responses=True,
                )
            if self.redis_client is None:
                raise ConnectionError(f"Redis not reachable at {REDIS_HOST}:{REDIS_PORT}")
            self.redis_client.ping()
            if not self.state.redis_available:
                print("[RedisSync] Redis connected")
            self.state.redis_available = True
            return True
        except Exception as e:
            if self.state.redis_available:
                print(f"[RedisSync] Redis unavailable: {e}")
            self.state.redis_available = False
            self.redis_client = None
            return False
    
    def _read_log_file(self, filepath: str, start_line: int = 0) -> tuple:
        """Read new entries from a log file starting at given line"""
        if not os.path.exists(filepath):
            return [], 0
        
        entries = []
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_lines = len(lines)
        new_entries = []
        
        for i in range(start_line, len(lines)):
            try:
                entry = json.loads(lines[i].strip())
                new_entries.append(entry)
            except json.JSONDecodeError:
                continue
        
        return new_entries, current_lines
    
    def _entry_key(self, entry: Dict) -> str:
        """Generate a unique key for an entry to avoid duplicates"""
        parts = [
            entry.get("type", ""),
            entry.get("session", ""),
            entry.get("timestamp", ""),
            entry.get("action", ""),
            entry.get("message", ""),
            entry.get("error_type", "")
        ]
        return hashlib.md5("|".join(parts).encode()).hexdigest()[:12]
    
    def _sync_entry_to_redis(self, entry: Dict) -> bool:
        """Sync a single entry to Redis"""
        if not self.state.redis_available or self.redis_client is None:
            return False
        
        try:
            entry_type = entry.get("type", "")
            session = entry.get("session", "unknown")
            
            if entry_type == "action":
                key = f"session:{session}:actions"
                action_data = {
                    "type": entry.get("action", ""),
                    "description": entry.get("description", ""),
                    "timestamp": entry.get("timestamp", ""),
                    "sequence": entry.get("sequence", 0),
                    "entry_key": self._entry_key(entry)
                }
                self.redis_client.rpush(key, json.dumps(action_data))
                
            elif entry_type == "chat":
                key = "chat:history"
                chat_data = {
                    "role": entry.get("role", ""),
                    "message": entry.get("message", ""),
                    "timestamp": entry.get("timestamp", ""),
                    "session": session,
                    "entry_key": self._entry_key(entry)
                }
                self.redis_client.rpush(key, json.dumps(chat_data))
                
            elif entry_type == "error":
                key = "errors:faults"
                error_data = {
                    "error_type": entry.get("error_type", ""),
                    "details": entry.get("details", ""),
                    "timestamp": entry.get("timestamp", ""),
                    "session": session,
                    "traceback": entry.get("traceback", ""),
                    "entry_key": self._entry_key(entry)
                }
                self.redis_client.rpush(key, json.dumps(error_data))
            
            return True
        except Exception as e:
            print(f"[RedisSync] Failed to sync entry: {e}")
            return False
    
    def _sync_active_sessions(self):
        """Sync active sessions from session logs"""
        if not self.state.redis_available:
            return
        
        sessions: Set[str] = set()
        log_file = os.path.join(SESSION_LOG_DIR, "session_all.jsonl")
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        session = entry.get("session", "")
                        if session:
                            sessions.add(session)
                    except:
                        continue
        
        if sessions:
            try:
                key = "sessions:active"
                pipe = self.redis_client.pipeline()
                for session in sessions:
                    session_data = {
                        "session_id": session,
                        "status": "active",
                        "last_seen": datetime.now().isoformat()
                    }
                    pipe.hset(key, session, json.dumps(session_data))
                pipe.execute()
            except Exception as e:
                print(f"[RedisSync] Failed to sync sessions: {e}")
    
    def poll(self) -> Dict:
        """Poll session logs for new entries and sync to Redis"""
        stats = {
            "actions": 0,
            "chats": 0,
            "errors": 0,
            "sessions_synced": False
        }
        
        with self._lock:
            # Check Redis connection
            self._connect_redis()
            self.state.last_redis_check = datetime.now().isoformat()
            
            if not self.state.redis_available:
                self._save_state()
                return stats
            
            # Sync session_all.jsonl
            log_file = os.path.join(SESSION_LOG_DIR, "session_all.jsonl")
            if os.path.exists(log_file):
                entries, total_lines = self._read_log_file(log_file, self.state.session_all_position)
                
                if total_lines > self.state.session_all_lines:
                    self.state.session_all_lines = total_lines
                
                for entry in entries:
                    entry_type = entry.get("type", "")
                    if entry_type == "action":
                        if self._sync_entry_to_redis(entry):
                            stats["actions"] += 1
                            self.state.session_all_position += 1
                    elif entry_type == "chat":
                        if self._sync_entry_to_redis(entry):
                            stats["chats"] += 1
                            self.state.session_all_position += 1
                    elif entry_type == "error":
                        if self._sync_entry_to_redis(entry):
                            stats["errors"] += 1
                            self.state.session_all_position += 1
                    else:
                        self.state.session_all_position += 1
            
            # Sync backup_session_all.jsonl
            backup_file = os.path.join(SESSION_LOG_DIR, "backup_session_all.jsonl")
            if os.path.exists(backup_file):
                entries, _ = self._read_log_file(backup_file, self.state.backup_session_position)
                for entry in entries:
                    entry_type = entry.get("type", "")
                    if entry_type in ("action", "chat", "error"):
                        if self._sync_entry_to_redis(entry):
                            if entry_type == "action":
                                stats["actions"] += 1
                            elif entry_type == "chat":
                                stats["chats"] += 1
                            else:
                                stats["errors"] += 1
                    self.state.backup_session_position += 1
            
            # Sync errors_and_faults.jsonl
            errors_file = os.path.join(SESSION_LOG_DIR, "errors_and_faults.jsonl")
            if os.path.exists(errors_file):
                entries, _ = self._read_log_file(errors_file, self.state.errors_position)
                for entry in entries:
                    if self._sync_entry_to_redis(entry):
                        stats["errors"] += 1
                    self.state.errors_position += 1
            
            # Sync active sessions periodically (every ~1 minute)
            if not hasattr(self, '_session_sync_counter'):
                self._session_sync_counter = 0
            self._session_sync_counter += 1
            if self._session_sync_counter >= 12:  # ~1 minute at 5s intervals
                self._sync_active_sessions()
                stats["sessions_synced"] = True
                self._session_sync_counter = 0
            
            self.state.last_sync = datetime.now().isoformat()
            self._save_state()
        
        return stats
    
    def get_status(self) -> Dict:
        """Get current sync status"""
        return {
            "running": self.running,
            "redis_available": self.state.redis_available,
            "last_sync": self.state.last_sync,
            "last_redis_check": self.state.last_redis_check,
            "session_all_position": self.state.session_all_position,
            "session_all_lines": self.state.session_all_lines,
            "backup_session_position": self.state.backup_session_position,
            "errors_position": self.state.errors_position,
            "poll_interval": POLL_INTERVAL
        }
    
    def reset_positions(self):
        """Reset sync positions to re-sync all entries"""
        with self._lock:
            self.state.session_all_position = 0
            self.state.session_all_lines = 0
            self.state.backup_session_position = 0
            self.state.errors_position = 0
            self.state.last_sync = ""
            self._save_state()
            print("[RedisSync] Positions reset - will re-sync all entries")


class SyncRunner:
    """Runs the sync poller as a background service"""
    
    def __init__(self):
        self.poller = RedisSyncPoller()
        self._shutdown_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
    
    def _run_loop(self):
        """Main polling loop"""
        print(f"[RedisSync] Started - polling every {POLL_INTERVAL}s")
        
        while not self._shutdown_event.is_set():
            try:
                stats = self.poller.poll()
                
                if stats["actions"] > 0 or stats["chats"] > 0 or stats["errors"] > 0:
                    total = stats["actions"] + stats["chats"] + stats["errors"]
                    print(f"[RedisSync] Synced {total} entries "
                          f"(actions={stats['actions']}, "
                          f"chats={stats['chats']}, "
                          f"errors={stats['errors']})")
                
            except Exception as e:
                print(f"[RedisSync] Poll error: {e}")
            
            self._shutdown_event.wait(POLL_INTERVAL)
        
        print("[RedisSync] Stopped")
    
    def start(self):
        """Start the sync service"""
        if self._thread is not None and self._thread.is_alive():
            print("[RedisSync] Already running")
            return
        
        self._shutdown_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.poller.running = True
    
    def stop(self):
        """Stop the sync service"""
        self._shutdown_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        self.poller.running = False
    
    def status(self):
        """Print current status"""
        status = self.poller.get_status()
        print("\n" + "=" * 50)
        print("  REDIS SYNC POLLER STATUS")
        print("=" * 50)
        print(f"  Running:         {status['running']}")
        print(f"  Redis Available: {status['redis_available']}")
        print(f"  Poll Interval:   {status['poll_interval']}s")
        print(f"  Last Sync:       {status['last_sync'] or 'Never'}")
        print(f"  Last Redis Chk:  {status['last_redis_check'] or 'Never'}")
        print("=" * 50)
        print("  Sync Progress:")
        print(f"    session_all.jsonl:     {status['session_all_position']}/{status['session_all_lines']} lines")
        print(f"    backup_session_all.jsonl: {status['backup_session_position']} lines")
        print(f"    errors_and_faults.jsonl: {status['errors_position']} lines")
        print("=" * 50 + "\n")


# Global runner instance
_runner: Optional[SyncRunner] = None


def _signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n[RedisSync] Received shutdown signal")
    if _runner:
        _runner.stop()
    sys.exit(0)


def get_runner() -> SyncRunner:
    """Get or create the global sync runner"""
    global _runner
    if _runner is None:
        _runner = SyncRunner()
    return _runner


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis Sync Poller")
    parser.add_argument("--status", action="store_true", help="Show sync status")
    parser.add_argument("--reset", action="store_true", help="Reset sync positions")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    
    args = parser.parse_args()
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    
    runner = get_runner()
    
    if args.status:
        runner.status()
    elif args.reset:
        runner.poller.reset_positions()
    elif args.daemon or True:  # Default to daemon mode
        runner.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            runner.stop()
