"""
Session Context Manager - Redis-backed Context Awareness
======================================================
Provides persistent context awareness across the session.
Remembers everything done, current task, decisions, and state.

Usage:
    from session_context import get_context, update_context, get_recent_work
    
    # Get current context
    ctx = get_context()
    
    # Update what we're working on
    update_context(current_task="Deploying Redis HA")
    
    # Get recent work summary
    recent = get_recent_work(limit=10)
"""

import os
import sys
import json
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

REDIS_HOST = "localhost"
REDIS_PORT = 6379
SESSION_LOG_DIR = r"E:\AI-Setup\session_logs"

CONTEXT_KEY = "context:current"
TASK_STACK_KEY = "context:task_stack"
DECISION_LOG_KEY = "context:decisions"
WORK_SUMMARY_KEY = "context:work_summary"
CURRENT_TASK_KEY = "context:current_task"


@dataclass
class SessionContext:
    session_id: str
    current_task: str
    current_phase: str
    started_at: str
    last_activity: str
    task_history: List[Dict]
    decisions_made: List[Dict]
    files_modified: List[str]
    discoveries: List[str]
    blockers: List[str]
    next_steps: List[str]


class SessionContextManager:
    _instance = None
    _redis = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connect()
        return cls._instance
    
    def _connect(self):
        """Connect to Redis"""
        try:
            self._redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self._redis.ping()
        except Exception as e:
            print(f"[Context] Redis unavailable: {e}")
            self._redis = None
    
    def _key(self, key: str) -> str:
        """Get full Redis key"""
        return f"session:{self._session_id}:{key}" if hasattr(self, '_session_id') else key
    
    def initialize(self, session_id: str):
        """Initialize context for session"""
        self._session_id = session_id
        
        if self._redis is None:
            self._connect()
        
        ctx = self.get_context()
        if ctx is None:
            ctx = SessionContext(
                session_id=session_id,
                current_task="Starting session",
                current_phase="IDLE",
                started_at=datetime.now().isoformat(),
                last_activity=datetime.now().isoformat(),
                task_history=[],
                decisions_made=[],
                files_modified=[],
                discoveries=[],
                blockers=[],
                next_steps=[]
            )
            self._save_context(ctx)
    
    def _save_context(self, ctx: SessionContext):
        """Save context to Redis"""
        if self._redis is None:
            return
        
        try:
            data = asdict(ctx)
            self._redis.set(CONTEXT_KEY, json.dumps(data))
        except Exception as e:
            print(f"[Context] Failed to save: {e}")
    
    def get_context(self) -> Optional[SessionContext]:
        """Get current session context"""
        if self._redis is None:
            return None
        
        try:
            data = self._redis.get(CONTEXT_KEY)
            if data:
                ctx_data = json.loads(data)
                return SessionContext(**ctx_data)
        except Exception as e:
            print(f"[Context] Failed to load: {e}")
        return None
    
    def update_current_task(self, task: str):
        """Update what we're currently working on"""
        ctx = self.get_context()
        if ctx is None:
            return
        
        if ctx.current_task != task:
            ctx.task_history.append({
                "task": ctx.current_task,
                "ended_at": datetime.now().isoformat()
            })
            ctx.current_task = task
        
        ctx.last_activity = datetime.now().isoformat()
        self._save_context(ctx)
    
    def update_phase(self, phase: str):
        """Update current workflow phase"""
        ctx = self.get_context()
        if ctx is None:
            return
        
        ctx.current_phase = phase
        ctx.last_activity = datetime.now().isoformat()
        self._save_context(ctx)
    
    def record_decision(self, decision: str, rationale: str = "", outcome: str = ""):
        """Record a significant decision"""
        ctx = self.get_context()
        if ctx is None:
            return
        
        ctx.decisions_made.append({
            "decision": decision,
            "rationale": rationale,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat()
        })
        ctx.last_activity = datetime.now().isoformat()
        self._save_context(ctx)
    
    def record_file_modified(self, filepath: str):
        """Record a file that was modified"""
        ctx = self.get_context()
        if ctx is None:
            return
        
        if filepath not in ctx.files_modified:
            ctx.files_modified.append(filepath)
        ctx.last_activity = datetime.now().isoformat()
        self._save_context(ctx)
    
    def record_discovery(self, discovery: str):
        """Record something important we discovered"""
        ctx = self.get_context()
        if ctx is None:
            return
        
        ctx.discoveries.append({
            "discovery": discovery,
            "timestamp": datetime.now().isoformat()
        })
        ctx.last_activity = datetime.now().isoformat()
        self._save_context(ctx)
    
    def add_blocker(self, blocker: str):
        """Add a blocker"""
        ctx = self.get_context()
        if ctx is None:
            return
        
        if blocker not in ctx.blockers:
            ctx.blockers.append(blocker)
        ctx.last_activity = datetime.now().isoformat()
        self._save_context(ctx)
    
    def remove_blocker(self, blocker: str):
        """Remove a blocker when resolved"""
        ctx = self.get_context()
        if ctx is None:
            return
        
        if blocker in ctx.blockers:
            ctx.blockers.remove(blocker)
        ctx.last_activity = datetime.now().isoformat()
        self._save_context(ctx)
    
    def add_next_step(self, step: str):
        """Add a next step"""
        ctx = self.get_context()
        if ctx is None:
            return
        
        if step not in ctx.next_steps:
            ctx.next_steps.append(step)
        ctx.last_activity = datetime.now().isoformat()
        self._save_context(ctx)
    
    def complete_next_step(self, step: str):
        """Mark a next step as completed"""
        ctx = self.get_context()
        if ctx is None:
            return
        
        if step in ctx.next_steps:
            ctx.next_steps.remove(step)
        ctx.last_activity = datetime.now().isoformat()
        self._save_context(ctx)
    
    def get_work_summary(self) -> Dict:
        """Get summary of work done in session"""
        ctx = self.get_context()
        if ctx is None:
            return {"error": "No context available"}
        
        return {
            "session_id": ctx.session_id,
            "started_at": ctx.started_at,
            "current_task": ctx.current_task,
            "current_phase": ctx.current_phase,
            "tasks_completed": len(ctx.task_history),
            "decisions_made": len(ctx.decisions_made),
            "files_modified_count": len(ctx.files_modified),
            "discoveries_count": len(ctx.discoveries),
            "active_blockers": len(ctx.blockers),
            "next_steps_count": len(ctx.next_steps),
            "last_activity": ctx.last_activity
        }
    
    def get_recent_work(self, limit: int = 10) -> List[Dict]:
        """Get recent work from session logs"""
        if self._redis is None:
            return []
        
        summary = []
        
        try:
            actions_key = f"session:{self._session_id}:actions"
            actions = self._redis.lrange(actions_key, -limit, -1)
            
            for action in reversed(actions):
                try:
                    data = json.loads(action)
                    summary.append({
                        "type": data.get("type", "unknown"),
                        "description": data.get("description", ""),
                        "timestamp": data.get("timestamp", "")
                    })
                except:
                    continue
        except Exception as e:
            print(f"[Context] Failed to get recent work: {e}")
        
        return summary
    
    def print_context_summary(self):
        """Print a human-readable context summary"""
        ctx = self.get_context()
        if ctx is None:
            print("No context available (Redis unavailable)")
            return
        
        print("\n" + "=" * 60)
        print("  SESSION CONTEXT SUMMARY")
        print("=" * 60)
        print(f"  Session:     {ctx.session_id}")
        print(f"  Current:     {ctx.current_task}")
        print(f"  Phase:      {ctx.current_phase}")
        print(f"  Started:    {ctx.started_at}")
        print(f"  Last Active: {ctx.last_activity}")
        print("-" * 60)
        
        if ctx.files_modified:
            print(f"  Files Modified ({len(ctx.files_modified)}):")
            for f in ctx.files_modified[-5:]:
                print(f"    - {f}")
            if len(ctx.files_modified) > 5:
                print(f"    ... and {len(ctx.files_modified) - 5} more")
        
        if ctx.discoveries:
            print(f"\n  Discoveries ({len(ctx.discoveries)}):")
            for d in ctx.discoveries[-3:]:
                print(f"    - {d.get('discovery', '')[:50]}")
        
        if ctx.blockers:
            print(f"\n  Blockers ({len(ctx.blockers)}):")
            for b in ctx.blockers:
                print(f"    - {b}")
        
        if ctx.next_steps:
            print(f"\n  Next Steps ({len(ctx.next_steps)}):")
            for s in ctx.next_steps[:5]:
                print(f"    - {s}")
        
        if ctx.decisions_made:
            print(f"\n  Decisions ({len(ctx.decisions_made)}):")
            for d in ctx.decisions_made[-3:]:
                print(f"    - {d.get('decision', '')[:50]}")
        
        print("=" * 60 + "\n")


_global_context = None


def get_context() -> Optional[SessionContext]:
    """Get the global context instance"""
    global _global_context
    if _global_context is None:
        _global_context = SessionContextManager()
    return _global_context.get_context()


def get_context_manager() -> SessionContextManager:
    """Get the context manager instance"""
    global _global_context
    if _global_context is None:
        _global_context = SessionContextManager()
    return _global_context


def update_context(**kwargs):
    """Convenience function to update context"""
    mgr = get_context_manager()
    for key, value in kwargs.items():
        if key == "current_task":
            mgr.update_current_task(value)
        elif key == "phase":
            mgr.update_phase(value)


def initialize_context(session_id: str):
    """Initialize context for a session"""
    mgr = get_context_manager()
    mgr.initialize(session_id)


def get_recent_work(limit: int = 10) -> List[Dict]:
    """Get recent work from session"""
    mgr = get_context_manager()
    return mgr.get_recent_work(limit)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Session Context Manager")
    parser.add_argument("--summary", action="store_true", help="Print context summary")
    parser.add_argument("--init", type=str, help="Initialize with session ID")
    parser.add_argument("--task", type=str, help="Set current task")
    parser.add_argument("--decision", type=str, help="Record a decision")
    parser.add_argument("--files", action="store_true", help="Show modified files")
    parser.add_argument("--recent", type=int, default=10, help="Show recent work")
    
    args = parser.parse_args()
    
    mgr = get_context_manager()
    
    if args.init:
        mgr.initialize(args.init)
        print(f"Context initialized for {args.init}")
    
    if args.task:
        mgr.update_current_task(args.task)
        print(f"Task updated: {args.task}")
    
    if args.decision:
        mgr.record_decision(args.decision)
        print(f"Decision recorded: {args.decision}")
    
    if args.summary:
        mgr.print_context_summary()
    
    if args.files:
        ctx = mgr.get_context()
        if ctx:
            for f in ctx.files_modified:
                print(f"  {f}")
    
    if args.recent:
        recent = mgr.get_recent_work(args.recent)
        print(f"\nRecent {len(recent)} actions:")
        for r in recent:
            print(f"  [{r.get('type', '')}] {r.get('description', '')[:50]}")
