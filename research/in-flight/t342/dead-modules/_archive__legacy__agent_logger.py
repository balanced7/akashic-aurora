"""
Agent Logger - Unified Logging for AI Agents
==========================================

Single entry point for all agent logging activities.
Inspired by Amazon/Google logging best practices.

Redis Key Structure:
    agent:work         - Current work context
    agent:actions      - All actions logged
    agent:history      - Completed work sessions
    agent:work:by_system:{s}  - Work by system
    agent:work:by_result:{r}   - Work by result
    agent:patches      - Patch log entries

Usage:
    from agent_logger import log, work, result
    
    # Start work
    work(system="logging", component="patch_log.py", 
         why="Need querying", plan="1) Add 2) Test")
    
    # Log actions
    log("Added Redis storage")
    log("Created query methods")
    
    # Complete
    result("SUCCESS", "All methods working")

Quick Log:
    log(system="logging", action="Did something", result="SUCCESS")
"""

import json
import redis
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field

try:
    import redis as redis_lib
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

REDIS_HOST = "localhost"
REDIS_PORT = 6379

# Redis keys
KEY_WORK = "agent:work"
KEY_ACTIONS = "agent:actions"
KEY_HISTORY = "agent:history"
KEY_PATCHES = "agent:patches"
KEY_VERSION = "agent:version"


@dataclass
class WorkContext:
    system: str = ""
    component: str = ""
    issue: str = ""
    plan: str = ""
    actions: List[str] = field(default_factory=list)
    started_at: str = ""
    session_id: str = ""


@dataclass
class PatchEntry:
    id: str
    timestamp: str
    system: str
    change_type: str
    title: str
    goal: str
    result: str
    version_from: str = ""
    version_to: str = ""


class AgentLogger:
    """
    Unified logging for AI agents.
    
    Single entry point for:
    - Work context tracking
    - Action logging
    - Learning/feedback
    - Patch-style changelog
    """
    
    _instance = None
    _redis = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self._connect_redis()
        self.work = WorkContext(
            session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            started_at=datetime.now().isoformat()
        )
    
    def _connect_redis(self):
        if not REDIS_AVAILABLE:
            return
        try:
            from core.foundation.redis_connection import connect_to_redis_with_fail_fast
            self._redis = connect_to_redis_with_fail_fast(
                host=REDIS_HOST,
                port=REDIS_PORT,
                timeout_seconds=3,
                decode_responses=True,
            )
        except:
            self._redis = None
    
    def _ensure_redis(self) -> bool:
        return self._redis is not None
    
    # ============ WORK CONTEXT ============
    
    def set_work(self, system: str, component: str, issue: str = "", cause: str = "", fix: str = ""):
        """
        Set current work context.
        
        Prints natural engineer comment style.
        """
        self.work = WorkContext(
            system=system,
            component=component,
            issue=issue,
            plan=fix,
            session_id=self.work.session_id,
            started_at=datetime.now().isoformat()
        )
        
        print()
        print(f"# ISSUE: {issue}")
        if cause:
            print(f"# CAUSE: {cause}")
        print(f"# COMPONENT: {component}")
        print(f"# FIX: {fix}")
        print()
        
        # Store in Redis
        if self._ensure_redis():
            try:
                self._redis.hset(KEY_WORK, mapping={
                    'system': system,
                    'component': component,
                    'issue': issue,
                    'plan': plan,
                    'session_id': self.work.session_id,
                    'started_at': self.work.started_at
                })
            except:
                pass
    
    def log_action(self, action: str, result: str = "PENDING"):
        """
        Log an action taken.
        """
        timestamp = datetime.now().isoformat()
        self.work.actions.append(action)
        
        print(f"# {action}")
        
        # Store in Redis
        if self._ensure_redis():
            try:
                action_data = {
                    'system': self.work.system,
                    'component': self.work.component,
                    'action': action,
                    'result': result,
                    'timestamp': timestamp,
                    'session_id': self.work.session_id
                }
                self._redis.zadd(KEY_ACTIONS, {
                    json.dumps(action_data): datetime.fromisoformat(timestamp).timestamp()
                })
            except:
                pass
    
    def set_result(self, fix: str = "", test: str = ""):
        """
        Set final result.
        """
        print()
        print(f"# FIX: {fix}")
        print(f"# TEST: {test}")
        print()
        
        # Store in Redis
        if self._ensure_redis():
            try:
                # Index by system and result
                self._redis.zadd(f"agent:work:by_system:{self.work.system}", {
                    self.work.session_id: datetime.now().timestamp()
                })
                self._redis.zadd(f"agent:work:by_result:{result.upper()}", {
                    self.work.session_id: datetime.now().timestamp()
                })
                
                # Save to history
                history_entry = {
                    'system': self.work.system,
                    'component': self.work.component,
                    'why': self.work.why,
                    'summary': summary,
                    'result': result,
                    'actions': len(self.work.actions),
                    'session_id': self.work.session_id,
                    'started_at': self.work.started_at,
                    'completed_at': datetime.now().isoformat()
                }
                self._redis.lpush(KEY_HISTORY, json.dumps(history_entry))
                self._redis.ltrim(KEY_HISTORY, 0, 99)
            except:
                pass
        
        # Clear work context
        self.work = WorkContext(
            session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            started_at=datetime.now().isoformat()
        )
    
    # ============ PATCH LOGGING ============
    
    def _gen_patch_id(self) -> str:
        return f"PK_{datetime.now().strftime('%m%d%H%M%S')}"
    
    def _load_version(self) -> tuple:
        if self._ensure_redis():
            try:
                ver = self._redis.get(KEY_VERSION) or "v0.0.0"
                parts = ver.lstrip('v').split('.')
                return int(parts[0]), int(parts[1]), int(parts[2])
            except:
                pass
        return 0, 0, 0
    
    def _save_version(self, major: int, minor: int, patch: int):
        if self._ensure_redis():
            try:
                self._redis.set(KEY_VERSION, f"v{major}.{minor}.{patch}")
            except:
                pass
    
    def patch(self, system: str, change_type: str, title: str, 
              goal: str = "", result: str = "PENDING") -> str:
        """
        Log a patch-style entry (like git commit).
        
        Bumps version based on change type.
        """
        patch_id = self._gen_patch_id()
        major, minor, patch = self._load_version()
        
        # Version bump based on type
        if change_type == "feat":
            minor += 1
            patch = 0
        elif change_type in ["fix", "perf"]:
            patch += 1
        version_from = f"v{major}.{minor - (1 if change_type == 'feat' else 0)}.{patch - (1 if change_type in ['feat', 'fix', 'perf'] else 0)}"
        version_to = f"v{major}.{minor}.{patch}"
        
        if change_type == "feat":
            version_from = f"v{major}.{minor - 1}.{patch}"
        elif change_type in ["fix", "perf"]:
            version_from = f"v{major}.{minor}.{patch - 1}" if patch > 0 else f"v{major}.{minor}.0"
        
        entry = PatchEntry(
            id=patch_id,
            timestamp=datetime.now().isoformat(),
            system=system,
            change_type=change_type,
            title=title[:100],
            goal=goal[:200],
            result=result,
            version_from=version_from,
            version_to=version_to
        )
        
        # Print patch
        print(f"\n[{system}:{change_type}] {title}")
        print(f"  Goal: {goal or 'N/A'}")
        print(f"  Result: {result}")
        print(f"  Version: {version_from} -> {version_to}")
        
        # Store in Redis
        if self._ensure_redis():
            try:
                self._redis.hset(KEY_PATCHES, patch_id, json.dumps(asdict(entry)))
                self._redis.zadd(f"agent:patches:index", {patch_id: datetime.now().timestamp()})
                self._redis.zadd(f"agent:patches:by_system:{system}", {patch_id: datetime.now().timestamp()})
                self._redis.zadd(f"agent:patches:by_type:{change_type}", {patch_id: datetime.now().timestamp()})
                self._save_version(major, minor, patch)
            except:
                pass
        
        return patch_id
    
    # ============ QUERY METHODS ============
    
    def get_recent_actions(self, limit: int = 10) -> List[Dict]:
        """Get recent actions from Redis."""
        if not self._ensure_redis():
            return []
        
        try:
            ids = self._redis.zrevrange(KEY_ACTIONS, 0, limit - 1)
            actions = []
            for idata in ids:
                actions.append(json.loads(idata))
            return actions
        except:
            return []
    
    def get_work_history(self, limit: int = 10) -> List[Dict]:
        """Get completed work sessions."""
        if not self._ensure_redis():
            return []
        
        try:
            entries = self._redis.lrange(KEY_HISTORY, 0, limit - 1)
            return [json.loads(e) for e in entries]
        except:
            return []
    
    def get_patches(self, system: str = None, limit: int = 20) -> List[PatchEntry]:
        """Get patch entries."""
        if not self._ensure_redis():
            return []
        
        try:
            key = f"agent:patches:by_system:{system}" if system else "agent:patches:index"
            ids = self._redis.zrevrange(key, 0, limit - 1)
            patches = []
            for pid in ids:
                data = self._redis.hget(KEY_PATCHES, pid)
                if data:
                    patches.append(PatchEntry(**json.loads(data)))
            return patches
        except:
            return []


# Singleton instance
_logger: Optional[AgentLogger] = None


def get_logger() -> AgentLogger:
    global _logger
    if _logger is None:
        _logger = AgentLogger()
    return _logger


# ============ CONVENIENCE FUNCTIONS ============

def work(system: str, component: str, issue: str = "", cause: str = "", fix: str = ""):
    """Set work context and print header."""
    get_logger().set_work(system, component, issue, cause, fix)


def log(action: str, result: str = "PENDING"):
    """Log an action."""
    get_logger().log_action(action, result)


def result(what_changed: str, why_it_matters: str = ""):
    """Set final result - explain what changed and why it matters."""
    get_logger().set_result(what_changed, why_it_matters)


def patch(system: str, change_type: str, title: str, 
          goal: str = "", result: str = "PENDING") -> str:
    """Log a patch-style entry."""
    return get_logger().patch(system, change_type, title, goal, result)


def feat(system: str, title: str, goal: str = "", result: str = "SUCCESS"):
    """Log a feature (patch)."""
    return patch(system, "feat", title, goal, result)


def fix(system: str, title: str, goal: str = "", result: str = "SUCCESS"):
    """Log a fix (patch)."""
    return patch(system, "fix", title, goal, result)


# ============ CLI ============

if __name__ == "__main__":
    logger = get_logger()
    
    logger.set_work(
        system="logging",
        component="E:\\AI-Setup\\agent_logger.py (logging system)",
        issue="agent_logger.py demo was too structured/template-like",
        cause="set_work() printed ISSUE/CAUSE/COMPONENT/FIX with bullets, log_action() printed [SYSTEM] prefix",
        fix="Changed to natural engineer comment style: # ISSUE: ..., # FIX: ..., # action"
    )
    
    logger.log_action("E:\\AI-Setup\\agent_logger.py line 127-175 - set_work() prints # ISSUE:, # CAUSE:, # COMPONENT:, # FIX:")
    logger.log_action("E:\\AI-Setup\\agent_logger.py line 178 - log_action() prints # {action} instead of structured output")
    logger.log_action("E:\\AI-Setup\\agent_logger.py line 197-207 - set_result() prints # FIX:, # TEST:")
    logger.log_action("E:\\AI-Setup\\bootstrap.py lines 188-215 - protocol reminder updated with natural style")
    logger.log_action("E:\\AI-Setup\\primer.py - rewritten with simple ISSUE/CAUSE/FIX format")
    
    logger.set_result(
        "E:\\AI-Setup\\agent_logger.py - unified logging module",
        "python E:\\AI-Setup\\agent_logger.py - shows natural comment-style output"
    )
