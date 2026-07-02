"""
Session Logger - Unified Logging with Compact Format
=================================================

New logging system with:
- Compact JSONL (no noise)
- Auto-tagging
- Session digests
- Archive to sessions/ directory

Usage:
    from session_logger import log_action, log_decision, log_error
    from session_logger import get_session_id, save_session
    
    log_action("Created file", tags=["architecture"])
    log_decision("Use Redis", rationale=["Fast"])
    
    # End of session:
    save_session()
"""

import os
import sys
import json
import redis
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from collections import Counter

BASE_DIR = Path(r"E:\AI-Setup")
ARCHIVE_DIR = BASE_DIR / "sessions"
INDEX_FILE = ARCHIVE_DIR / "index.json"
LOG_DIR = BASE_DIR / "session_logs"

LOG_FILE = LOG_DIR / "session_all.jsonl"
BACKUP_LOG_FILE = LOG_DIR / "backup_session_all.jsonl"

os.makedirs(ARCHIVE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

sys.path.insert(0, str(BASE_DIR))
from config import get_redis_config

TAG_PATTERNS = {
    "vision": ["vision", "comfyui", "florence", "ocr", "image"],
    "infrastructure": ["redis", "backup", "ha", "sentinel", "docker", "container"],
    "multi-agent": ["mcp", "agent", "comm", "message", "coordinate", "broadcast", "alert"],
    "learning": ["learning", "decision", "experience", "reflection", "reflexion", "context"],
    "architecture": ["consolidat", "refactor", "architecture", "design", "merge", "file", "folder"],
    "setup": ["install", "setup", "configur", "deploy", "build", "bootstrap"],
    "debugging": ["bug", "fix", "error", "crash", "debug", "issue", "problem"],
    "automation": ["automation", "pyautogui", "selenium", "ui", "window"],
}


class SessionLogger:
    """Compact session logger with auto-tagging and digest generation"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.entries: List[Dict] = []
        self.sequence = 0
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.started_at = datetime.now().isoformat()
        self._pending_tags: List[str] = []
        
        try:
            from core.foundation.redis_connection import connect_to_redis_with_fail_fast
            cfg = get_redis_config()
            self._redis = connect_to_redis_with_fail_fast(
                host=cfg["host"],
                port=cfg["port"],
                timeout_seconds=cfg.get("socket_connect_timeout", 5),
                decode_responses=cfg.get("decode_responses", True),
            )
            self._redis_available = self._redis is not None
        except Exception:
            self._redis = None
            self._redis_available = False
    
    def _auto_tag(self, content: str, tags: List[str] = None) -> List[str]:
        """Auto-generate tags from content"""
        result = list(tags) if tags else []
        content_lower = content.lower()
        
        for tag, patterns in TAG_PATTERNS.items():
            if any(p in content_lower for p in patterns):
                if tag not in result:
                    result.append(tag)
        
        return result or ["general"]
    
    def _log(self, type_: str, content: str, tags: List[str] = None, data: Dict = None):
        """Internal log method with DUAL-WRITE fault tolerance"""
        self.sequence += 1
        auto_tags = self._auto_tag(content, tags)
        
        entry = {
            "type": type_,
            "timestamp": datetime.now().isoformat(),
            "sequence": self.sequence,
            "session": self.session_id,
            "content": content[:200],
            "tags": auto_tags,
            "data": data or {}
        }
        
        self.entries.append(entry)
        
        # DUAL-WRITE: Write to Redis AND both files
        # This ensures continuity even if one write fails or agent forgets
        
        # 1. Redis (if available)
        if self._redis_available:
            try:
                self._redis.rpush(f"session:{self.session_id}:log", json.dumps(entry))
            except:
                pass
        
        # 2. Primary JSONL file
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            # Fall through to backup
            pass
        
        # 3. BACKUP JSONL file (failsafe - ALWAYS write this)
        try:
            with open(BACKUP_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            # Last resort: log to console if file write fails
            print(f"[LOG FAILSAFE] {entry.get('type')}: {content[:80]}", file=sys.stderr)
    
    def action(self, description: str, tags: List[str] = None):
        """Log an action"""
        self._log("action", description, tags)
    
    def decision(self, title: str, rationale: List[str] = None, tags: List[str] = None):
        """Log a decision"""
        content = f"Decision: {title}"
        if rationale:
            content += f" - Rationale: {', '.join(rationale[:2])}"
        self._log("decision", content, tags or ["learning"], {"rationale": rationale or []})
    
    def error(self, details: str, tags: List[str] = None):
        """Log an error"""
        self._log("error", details, tags or ["debugging"])
    
    def learning(self, content: str, tags: List[str] = None):
        """Log a learning"""
        self._log("learning", content, tags or ["learning"])
    
    def system(self, content: str):
        """Log system message"""
        self._log("system", content)
    
    def save(self) -> Dict:
        """Save session digest and update index"""
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        duration = max(1, int((now - datetime.fromisoformat(self.started_at)).total_seconds() / 60))
        
        tags = self._get_tags()
        summary = self._generate_summary()
        
        actions = [e["content"] for e in self.entries if e["type"] == "action" and "continu" not in e["content"].lower()][:10]
        learnings = [e["content"] for e in self.entries if e["type"] == "learning"][:5]
        decisions = [e["content"] for e in self.entries if e["type"] == "decision"][:5]
        error_count = sum(1 for e in self.entries if e["type"] == "error")
        
        digest_lines = [
            f"# Session {self.session_id}",
            "",
            f"**Date**: {date_str}",
            f"**Duration**: ~{duration} min",
            f"**Tags**: [{'] ['.join(tags)}]",
            "",
            "## Summary",
            summary,
            "",
        ]
        
        if actions:
            digest_lines.extend(["## Key Actions"] + [f"- {a}" for a in actions] + [""])
        
        if learnings:
            digest_lines.extend(["## Learnings"] + [f"- {l}" for l in learnings] + [""])
        
        if decisions:
            digest_lines.extend(["## Decisions"] + [f"- {d}" for d in decisions] + [""])
        
        digest_lines.extend(["---", f"*Logged: {now.isoformat()}*"])
        
        date_dir = ARCHIVE_DIR / date_str
        date_dir.mkdir(parents=True, exist_ok=True)
        
        digest_path = date_dir / f"{self.session_id}_digest.md"
        raw_path = date_dir / f"{self.session_id}_raw.jsonl"
        
        digest_path.write_text("\n".join(digest_lines), encoding='utf-8')
        with open(raw_path, 'w', encoding='utf-8') as f:
            for e in self.entries:
                f.write(json.dumps(e) + '\n')
        
        digest = {
            "session_id": self.session_id,
            "date": date_str,
            "started_at": self.started_at,
            "ended_at": now.isoformat(),
            "duration_minutes": duration,
            "tags": tags,
            "summary": summary,
            "key_actions": actions,
            "learnings": learnings,
            "decisions": decisions,
            "message_count": len(self.entries),
            "error_count": error_count,
            "digest_file": str(digest_path),
            "raw_file": str(raw_path)
        }
        
        self._update_index(digest)
        
        return digest
    
    def _update_index(self, digest: Dict):
        """Update master index"""
        sessions = []
        if INDEX_FILE.exists():
            try:
                with open(INDEX_FILE, 'r') as f:
                    sessions = json.load(f)
            except:
                sessions = []
        
        sessions.insert(0, digest)
        
        with open(INDEX_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
    
    def _get_tags(self) -> List[str]:
        """Get top tags from session"""
        counter = Counter()
        for e in self.entries:
            for t in e.get("tags", []):
                counter[t] += 1
        return [t for t, _ in counter.most_common(5)]
    
    def _generate_summary(self) -> str:
        """Generate session summary"""
        actions = [e["content"] for e in self.entries if e["type"] == "action" and len(e["content"]) > 20][:3]
        if actions:
            return f"Actions: {', '.join(actions)}"
        return f"Session: {len(self.entries)} entries"


_logger: Optional[SessionLogger] = None

def get_logger() -> SessionLogger:
    global _logger
    if _logger is None:
        _logger = SessionLogger()
    return _logger

def log_action(description: str, tags: List[str] = None):
    get_logger().action(description, tags)

def log_decision(title: str, rationale: List[str] = None, tags: List[str] = None):
    get_logger().decision(title, rationale, tags)

def log_error(details: str, tags: List[str] = None):
    get_logger().error(details, tags)

def log_learning(content: str, tags: List[str] = None):
    get_logger().learning(content, tags)

def log_system(content: str):
    get_logger().system(content)

def save_session():
    return get_logger().save()

def get_session_id() -> str:
    return get_logger().session_id

SESSION_ID = get_session_id()


# Legacy compatibility
def log(type_: str, description: str, data: Dict = None):
    """Legacy log function - routes to appropriate method"""
    if type_ == "action":
        log_action(description, data.get("tags") if data else None)
    elif type_ == "decision":
        log_decision(description, data.get("rationale") if data else None)
    elif type_ == "error":
        log_error(description)
    else:
        log_system(f"{type_}: {description}")


# Legacy functions for compatibility
def get_chat_history(limit: int = 50):
    """Get recent chat messages from current session log file"""
    chats = []
    try:
        if LOG_FILE.exists():
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-limit:]:
                    try:
                        entry = json.loads(line)
                        if entry.get("type") == "chat" or entry.get("role"):
                            chats.append(entry)
                    except:
                        pass
    except Exception as e:
        print(f"[session_logger] get_chat_history error: {e}")
    return chats


def get_recent_sessions(limit: int = 5):
    """Get recent sessions from index"""
    sessions = []
    try:
        if INDEX_FILE.exists():
            with open(INDEX_FILE, 'r') as f:
                all_sessions = json.load(f)
                for s in all_sessions[:limit]:
                    sessions.append({
                        "session_id": s.get("session_id"),
                        "date": s.get("date"),
                        "summary": s.get("summary", "")[:100],
                        "tags": s.get("tags", []),
                        "duration": s.get("duration_minutes", 0)
                    })
    except Exception as e:
        print(f"[session_logger] get_recent_sessions error: {e}")
    return sessions


def verify_logs():
    """Verify log file integrity"""
    results = {"log_file": str(LOG_FILE), "exists": False, "entries": 0, "valid": True, "errors": []}
    
    try:
        results["exists"] = LOG_FILE.exists()
        results["size_kb"] = LOG_FILE.stat().st_size / 1024 if results["exists"] else 0
        
        if results["exists"]:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    try:
                        json.loads(line)
                        results["entries"] += 1
                    except json.JSONDecodeError as e:
                        results["valid"] = False
                        results["errors"].append(f"Line {i+1}: {str(e)}")
                        if len(results["errors"]) >= 5:
                            break
    except Exception as e:
        results["valid"] = False
        results["errors"].append(str(e))
    
    return results


def log_chat(role: str, message: str):
    """Log a chat message"""
    _logger = get_logger()
    _logger.entries.append({
        "type": "chat",
        "role": role,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "sequence": _logger.sequence + 1,
        "session": _logger.session_id
    })
    _logger.sequence += 1
    if _logger._redis_available:
        try:
            _logger._redis.rpush(f"session:{_logger.session_id}:chats", json.dumps({"role": role, "message": message}))
        except:
            pass


# ============ FAILSAFE LOGGING ============
# Manual failsafe for when agents forget to log or harness misses non-compliance

def failsafe(type_: str, content: str, data: Dict = None):
    """
    MANUAL FAILSAFE logging - Use this when agent forgets to log.
    Writes to ALL destinations: Redis + Primary + Backup files.
    
    This is the last line of defense for continuity.
    """
    entry = {
        "type": type_,
        "timestamp": datetime.now().isoformat(),
        "sequence": 0,
        "session": SESSION_ID,
        "content": content[:200],
        "tags": ["failsafe"],
        "data": data or {}
    }
    entry_json = json.dumps(entry)
    
    destinations_ok = 0
    
    # 1. Redis
    try:
        from core.foundation.redis_connection import connect_to_redis_with_fail_fast
        cfg = get_redis_config()
        r = connect_to_redis_with_fail_fast(
            host=cfg["host"],
            port=cfg["port"],
            timeout_seconds=cfg.get("socket_connect_timeout", 5),
            decode_responses=cfg.get("decode_responses", True),
        )
        if r is not None:
            r.rpush(f"session:{SESSION_ID}:log", entry_json)
            destinations_ok += 1
    except:
        pass
    
    # 2. Primary file
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(entry_json + '\n')
        destinations_ok += 1
    except:
        pass
    
    # 3. Backup file (MOST IMPORTANT - always should work)
    try:
        with open(BACKUP_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(entry_json + '\n')
        destinations_ok += 1
    except Exception as e:
        # LAST RESORT: Print to console
        print(f"[FAILSAFE CRITICAL] Could not write to backup: {e}", file=sys.stderr)
        print(f"[FAILSAFE] {type_}: {content}", file=sys.stderr)
    
    if destinations_ok < 3:
        print(f"[FAILSAFE WARNING] Only {destinations_ok}/3 destinations written", file=sys.stderr)
    
    return destinations_ok


def manual_log(description: str, type_: str = "action", tags: List[str] = None):
    """
    MANUAL LOG - Call this when agent realizes they forgot to log something.
    This ensures the action is captured regardless of previous misses.
    """
    return failsafe(type_, description, {"tags": tags or [], "manual": True, "note": "Agent manually logged this"})


# Export SessionLogger alias for legacy code
SessionLogger = SessionLogger


if __name__ == "__main__":
    logger = get_logger()
    print(f"Session ID: {logger.session_id}")
    print(f"Redis: {'Connected' if logger._redis_available else 'Not available'}")
    print()
    
    logger.action("Testing new session logger", tags=["setup"])
    logger.decision("Use compact format", rationale=["Cleaner", "Faster"])
    
    digest = logger.save()
    print(f"\nSaved: {digest['session_id']}")
    print(f"Tags: {digest['tags']}")
    print(f"Digest: {digest['digest_file']}")
