"""
Work Context - Standardized Agent Action Logging
==============================================

Every agent response should include context about what they're working on.

Format:
    ┌─────────────────────────────────────────────────────────┐
    │ WORKING ON: [system]                                    │
    │ GOAL: [why we're doing this]                           │
    │ ────────────────────────────────────────────────────── │
    │ ACTIONS:                                                │
    │   [1] [timestamp] [description] → [result]             │
    │   [2] [timestamp] [description] → [result]           │
    │ ────────────────────────────────────────────────────── │
    │ STATUS: [pending|in-progress|success|partial|failure]   │
    └─────────────────────────────────────────────────────────┘

Usage:
    from work_context import WorkContext, work
    
    # Set context
    work.system("logging")
    work.goal("Fix session logging to use Redis")
    
    # Log action
    work.action("Added Redis primary storage to patch_log")
    
    # Set result
    work.result("SUCCESS")
    
    # Print for visibility
    print(work)  # Shows formatted context

Redis Keys:
    work:current     - Hash of current work state
    work:history     - List of past work sessions
    work:actions     - Sorted set of actions by timestamp
"""

import json
import redis
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field
from collections import defaultdict

try:
    import redis as redis_lib
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


REDIS_HOST = "localhost"
REDIS_PORT = 6379


@dataclass
class Action:
    timestamp: str
    description: str
    result: str  # PENDING, SUCCESS, FAILURE, PARTIAL
    verified: bool = False
    evidence: List[str] = field(default_factory=list)


@dataclass
class WorkState:
    session_id: str
    system: str = ""
    goal: str = ""
    status: str = "pending"  # pending, in-progress, success, partial, failure
    actions: List[Dict] = field(default_factory=list)
    started_at: str = ""
    updated_at: str = ""
    confidence: float = 0.5  # How confident we are in this work


SYSTEMS = [
    "vision", "redis", "logging", "learning", "mcp",
    "bootstrap", "infrastructure", "architecture", "automation", "multi-agent"
]


class WorkContext:
    """
    Tracks current work context for the agent.
    
    Every response should print this context so the human (and logs) know:
    - WHAT system we're working on
    - WHY we're doing it
    - WHAT actions we've taken
    - IF those actions succeeded
    """
    
    _instance = None
    _redis = None
    
    KEY_CURRENT = "work:current"
    KEY_HISTORY = "work:history"
    KEY_ACTIONS = "work:actions"
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self.state = WorkState(
            session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            started_at=datetime.now().isoformat()
        )
        self._connect_redis()
        self._load_current()
    
    def _connect_redis(self):
        if not REDIS_AVAILABLE:
            return
        try:
            self._redis = redis_lib.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                decode_responses=True
            )
            self._redis.ping()
        except:
            self._redis = None
    
    def _load_current(self):
        """Load current work state from Redis"""
        if not self._redis:
            return
        
        try:
            data = self._redis.hgetall(self.KEY_CURRENT)
            if data and data.get('system'):
                self.state = WorkState(
                    session_id=data.get('session_id', self.state.session_id),
                    system=data.get('system', ''),
                    goal=data.get('goal', ''),
                    status=data.get('status', 'pending'),
                    actions=json.loads(data.get('actions', '[]')),
                    started_at=data.get('started_at', ''),
                    updated_at=data.get('updated_at', ''),
                    confidence=float(data.get('confidence', 0.5))
                )
        except Exception as e:
            print(f"[WorkContext] Load error: {e}")
    
    def _save_current(self):
        """Save current work state to Redis"""
        if not self._redis:
            return
        
        self.state.updated_at = datetime.now().isoformat()
        
        data = {
            'session_id': self.state.session_id,
            'system': self.state.system,
            'goal': self.state.goal,
            'status': self.state.status,
            'actions': json.dumps(self.state.actions),
            'started_at': self.state.started_at,
            'updated_at': self.state.updated_at,
            'confidence': str(self.state.confidence)
        }
        
        try:
            self._redis.hset(self.KEY_CURRENT, mapping=data)
            self._redis.expire(self.KEY_CURRENT, 86400 * 7)  # 7 day TTL
        except Exception as e:
            print(f"[WorkContext] Save error: {e}")
    
    def system(self, name: str) -> 'WorkContext':
        """Set current system"""
        self.state.system = name
        self._save_current()
        return self
    
    def goal(self, description: str) -> 'WorkContext':
        """Set current goal"""
        self.state.goal = description
        self._save_current()
        return self
    
    def action(self, description: str, result: str = "PENDING", 
               verified: bool = False) -> 'WorkContext':
        """Log an action taken"""
        action = Action(
            timestamp=datetime.now().isoformat(),
            description=description,
            result=result,
            verified=verified
        )
        
        self.state.actions.append(asdict(action))
        
        # Also store in Redis for searching
        if self._redis:
            try:
                action_data = {
                    'system': self.state.system,
                    'goal': self.state.goal,
                    'description': description,
                    'result': result,
                    'verified': verified,
                    'timestamp': action.timestamp,
                    'session_id': self.state.session_id
                }
                self._redis.zadd(self.KEY_ACTIONS, {
                    json.dumps(action_data): datetime.fromisoformat(action.timestamp).timestamp()
                })
            except:
                pass
        
        self._save_current()
        return self
    
    def result(self, status: str, confidence: float = None) -> 'WorkContext':
        """Set final result status"""
        self.state.status = status
        if confidence is not None:
            self.state.confidence = confidence
        self._save_current()
        
        # Save to history
        self._save_to_history()
        return self
    
    def _save_to_history(self):
        """Save completed work to history"""
        if not self._redis:
            return
        
        try:
            history_entry = {
                'system': self.state.system,
                'goal': self.state.goal,
                'status': self.state.status,
                'actions': len(self.state.actions),
                'confidence': self.state.confidence,
                'session_id': self.state.session_id,
                'started_at': self.state.started_at,
                'completed_at': datetime.now().isoformat()
            }
            self._redis.lpush(self.KEY_HISTORY, json.dumps(history_entry))
            self._redis.ltrim(self.KEY_HISTORY, 0, 99)  # Keep last 100
        except:
            pass
    
    def clear(self):
        """Clear current work context"""
        self.state = WorkState(
            session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            started_at=datetime.now().isoformat()
        )
        self._save_current()
    
    def reset(self, system: str = "", goal: str = ""):
        """Reset with new context"""
        self.clear()
        if system:
            self.system(system)
        if goal:
            self.goal(goal)
    
    def get_status_line(self) -> str:
        """Get one-line status summary"""
        action_count = len(self.state.actions)
        action_results = [a.get('result', 'PENDING') for a in self.state.actions]
        
        if not self.state.system:
            return "[no context set]"
        
        parts = [
            f"[{self.state.system.upper()}]",
        ]
        
        if self.state.goal:
            parts.append(f"GOAL: {self.state.goal[:50]}")
        
        if action_count > 0:
            parts.append(f"ACTIONS: {action_count}")
            success_count = action_results.count('SUCCESS')
            fail_count = action_results.count('FAILURE')
            if success_count:
                parts.append(f"+{success_count}")
            if fail_count:
                parts.append(f"-{fail_count}")
        
        parts.append(f"STATUS: {self.state.status.upper()}")
        
        return " | ".join(parts)
    
    def __str__(self) -> str:
        """Formatted output for printing"""
        if not self.state.system:
            return ""
        
        lines = []
        lines.append("+" + "-" * 60 + "+")
        lines.append(f"| WORKING ON: [{self.state.system.upper()}]")
        
        if self.state.goal:
            lines.append(f"| GOAL: {self.state.goal}")
        
        lines.append("|" + "-" * 60)
        
        if self.state.actions:
            lines.append("| ACTIONS:")
            for i, action in enumerate(self.state.actions[-5:], 1):  # Last 5
                result_icon = {
                    'SUCCESS': '[+]',
                    'FAILURE': '[-]',
                    'PARTIAL': '[~]',
                    'PENDING': '[ ]'
                }.get(action.get('result', 'PENDING'), '[ ]')
                
                ts = action.get('timestamp', '')[:8]
                desc = action.get('description', '')[:40]
                lines.append(f"|   [{i}] {ts} {desc} {result_icon}")
        else:
            lines.append("| ACTIONS: (none yet)")
        
        lines.append("|" + "-" * 60)
        
        status_marker = {
            'success': '[+]',
            'failure': '[-]',
            'partial': '[~]',
            'in-progress': '[>]',
            'pending': '[ ]'
        }.get(self.state.status, '[ ]')
        
        lines.append(f"| STATUS: {status_marker} {self.state.status.upper()}")
        lines.append("+" + "-" * 60 + "+")
        
        return "\n".join(lines)
    
    def as_dict(self) -> Dict[str, Any]:
        """Get state as dict for JSON serialization"""
        return asdict(self.state)


def work() -> WorkContext:
    """Get singleton WorkContext instance"""
    return WorkContext()


# Convenience functions
def set_system(name: str):
    work().system(name)

def set_goal(description: str):
    work().goal(description)

def log_action(description: str, result: str = "PENDING"):
    work().action(description, result)

def set_result(status: str):
    work().result(status)

def status():
    print(work())

def quick_action(system: str, component: str, action: str, result: str = ""):
    """
    Quick log: [SYSTEM] component: action -> result
    
    Usage:
        from work_context import quick_action
        quick_action("logging", "patch_log.py", "Added Redis storage", "SUCCESS")
        # Output: [LOGGING] patch_log.py: Added Redis storage -> SUCCESS
    """
    base = f"[{system.upper()}] {component}: {action}"
    if result:
        base += f" -> {result.upper()}"
    print(base)


def work_header(system: str, component: str, why: str = "", plan: str = ""):
    """Print work context header"""
    print("-" * 60)
    print(f"SYSTEM: {system}")
    print(f"COMPONENT: {component}")
    if why:
        print(f"WHY: {why}")
    if plan:
        print(f"PLAN: {plan}")
    print("-" * 60)


def work_result(system: str, component: str, summary: str, result: str):
    """Print work result"""
    print("-" * 60)
    print(f"SYSTEM: {system}")
    print(f"COMPONENT: {component}")
    print(f"SUMMARY: {summary}")
    print(f"RESULT: {result.upper()}")
    print("-" * 60)


if __name__ == "__main__":
    print("=== WORK CONTEXT DEMO ===")
    print()
    
    # Show new format
    work_header("logging", "patch_log.py", 
                "Patches should live in Redis",
                "1) Add Redis storage 2) Add query methods")
    
    quick_action("logging", "patch_log.py", "Adding Redis storage", "")
    quick_action("logging", "patch_log.py", "Adding query methods", "")
    quick_action("logging", "patch_log.py", "Testing queries", "")
    
    print()
    work_result("logging", "patch_log.py", 
                "Redis storage added, 3 query methods created, all tested",
                "SUCCESS")
