"""
Project Context Manager - Redis-backed Multi-Agent Context
========================================================
Provides architectural, big-picture, mid-picture, and recent context for new agents.
All data stored in Redis for fast multi-agent access.

Context Layers:
- ARCHITECTURAL: System design, components, relationships
- BIG PICTURE: Project goals, milestones, roadmap
- MID PICTURE: Current work streams, tasks, blockers
- RECENT: Current session, latest actions, immediate context

Usage:
    from project_context import get_context_manager, update_context
    
    # Get full context for re-priming
    ctx = get_context_manager().get_full_context()
    
    # Update current work
    get_context_manager().update_current_task("Deploying Redis HA")
    
    # Add blocker
    get_context_manager().add_blocker("Waiting for GPU allocation")
    
    # Complete milestone
    get_context_manager().complete_milestone("Redis HA Deployed")
"""

import os
import json
import redis
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

REDIS_HOST = "localhost"
REDIS_PORT = 6379


@dataclass
class Milestone:
    id: str
    name: str
    description: str
    status: str  # pending|in_progress|completed|blocked
    created_at: str
    priority: int = 0
    completed_at: Optional[str] = None


@dataclass
class Task:
    id: str
    title: str
    description: str
    status: str  # todo|in_progress|done|blocked
    created_at: str
    assignee: Optional[str] = None
    milestone_id: Optional[str] = None
    updated_at: str = ""
    completed_at: Optional[str] = None


@dataclass
class Blocker:
    id: str
    description: str
    severity: str  # low|medium|high|critical
    status: str  # active|resolved
    created_at: str
    resolved_at: Optional[str] = None
    task_id: Optional[str] = None


class ProjectContextManager:
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
    
    def _key(self, name: str) -> str:
        """Get prefixed Redis key"""
        return f"context:{name}"
    
    # ============ ARCHITECTURAL CONTEXT ============
    
    def set_architecture(self, architecture: Dict):
        """Set architectural documentation"""
        if self._redis is None:
            return False
        self._redis.set(self._key("architecture"), json.dumps(architecture))
        return True
    
    def get_architecture(self) -> Optional[Dict]:
        """Get architectural documentation"""
        if self._redis is None:
            return None
        data = self._redis.get(self._key("architecture"))
        return json.loads(data) if data else None
    
    def update_architecture_component(self, component: str, details: Dict):
        """Update a specific component in architecture"""
        arch = self.get_architecture() or {"components": {}, "relationships": [], "updated_at": ""}
        arch["components"][component] = details
        arch["updated_at"] = datetime.now().isoformat()
        self.set_architecture(arch)
    
    # ============ BIG PICTURE (Milestones) ============
    
    def add_milestone(self, name: str, description: str, priority: int = 0) -> str:
        """Add a milestone"""
        if self._redis is None:
            return ""
        
        milestone_id = f"ms_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        milestone = Milestone(
            id=milestone_id,
            name=name,
            description=description,
            status="pending",
            created_at=datetime.now().isoformat(),
            priority=priority
        )
        
        self._redis.hset(
            self._key("milestones"),
            milestone_id,
            json.dumps(asdict(milestone))
        )
        
        return milestone_id
    
    def get_milestones(self, status: Optional[str] = None) -> List[Milestone]:
        """Get all milestones, optionally filtered by status"""
        if self._redis is None:
            return []
        
        milestones = []
        data = self._redis.hgetall(self._key("milestones"))
        
        for m_id, m_json in data.items():
            m = Milestone(**json.loads(m_json))
            if status is None or m.status == status:
                milestones.append(m)
        
        return sorted(milestones, key=lambda x: (-x.priority, x.created_at))
    
    def update_milestone_status(self, milestone_id: str, status: str):
        """Update milestone status"""
        if self._redis is None:
            return
        
        data = self._redis.hget(self._key("milestones"), milestone_id)
        if data:
            m = Milestone(**json.loads(data))
            m.status = status
            if status == "completed":
                m.completed_at = datetime.now().isoformat()
            self._redis.hset(self._key("milestones"), milestone_id, json.dumps(asdict(m)))
    
    def complete_milestone(self, milestone_id: str):
        """Mark milestone as completed"""
        self.update_milestone_status(milestone_id, "completed")
    
    # ============ MID PICTURE (Tasks) ============
    
    def add_task(self, title: str, description: str, milestone_id: Optional[str] = None, 
                 assignee: Optional[str] = None) -> str:
        """Add a task"""
        if self._redis is None:
            return ""
        
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task = Task(
            id=task_id,
            title=title,
            description=description,
            status="todo",
            milestone_id=milestone_id,
            assignee=assignee,
            created_at=datetime.now().isoformat()
        )
        
        self._redis.hset(self._key("tasks"), task_id, json.dumps(asdict(task)))
        return task_id
    
    def get_tasks(self, status: Optional[str] = None, milestone_id: Optional[str] = None) -> List[Task]:
        """Get tasks, optionally filtered"""
        if self._redis is None:
            return []
        
        tasks = []
        data = self._redis.hgetall(self._key("tasks"))
        
        for t_id, t_json in data.items():
            t = Task(**json.loads(t_json))
            if status and t.status != status:
                continue
            if milestone_id and t.milestone_id != milestone_id:
                continue
            tasks.append(t)
        
        return sorted(tasks, key=lambda x: x.created_at, reverse=True)
    
    def update_task_status(self, task_id: str, status: str):
        """Update task status"""
        if self._redis is None:
            return
        
        data = self._redis.hget(self._key("tasks"), task_id)
        if data:
            t = Task(**json.loads(data))
            t.status = status
            t.updated_at = datetime.now().isoformat()
            if status == "done":
                t.completed_at = datetime.now().isoformat()
            self._redis.hset(self._key("tasks"), task_id, json.dumps(asdict(t)))
    
    # ============ BLOCKERS ============
    
    def add_blocker(self, description: str, severity: str = "medium", task_id: Optional[str] = None) -> str:
        """Add a blocker"""
        if self._redis is None:
            return ""
        
        blocker_id = f"blk_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        blocker = Blocker(
            id=blocker_id,
            description=description,
            severity=severity,
            status="active",
            created_at=datetime.now().isoformat(),
            task_id=task_id
        )
        
        self._redis.hset(self._key("blockers"), blocker_id, json.dumps(asdict(blocker)))
        return blocker_id
    
    def get_blockers(self, status: Optional[str] = None) -> List[Blocker]:
        """Get blockers, optionally filtered"""
        if self._redis is None:
            return []
        
        blockers = []
        data = self._redis.hgetall(self._key("blockers"))
        
        for b_id, b_json in data.items():
            b = Blocker(**json.loads(b_json))
            if status is None or b.status == status:
                blockers.append(b)
        
        return sorted(blockers, key=lambda x: x.created_at, reverse=True)
    
    def resolve_blocker(self, blocker_id: str):
        """Mark blocker as resolved"""
        if self._redis is None:
            return
        
        data = self._redis.hget(self._key("blockers"), blocker_id)
        if data:
            b = Blocker(**json.loads(data))
            b.status = "resolved"
            b.resolved_at = datetime.now().isoformat()
            self._redis.hset(self._key("blockers"), blocker_id, json.dumps(asdict(b)))
    
    # ============ CURRENT WORK ============
    
    def set_current_task(self, task: str, details: str = ""):
        """Set what we're currently working on"""
        if self._redis is None:
            return
        
        data = {
            "task": task,
            "details": details,
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._redis.set(self._key("current_task"), json.dumps(data))
    
    def get_current_task(self) -> Optional[Dict]:
        """Get current task"""
        if self._redis is None:
            return None
        
        data = self._redis.get(self._key("current_task"))
        return json.loads(data) if data else None
    
    def add_to_work_log(self, entry: str):
        """Add an entry to the work log"""
        if self._redis is None:
            return
        
        work_log = self._redis.lrange(self._key("work_log"), 0, 49)
        
        entry_data = {
            "entry": entry,
            "timestamp": datetime.now().isoformat()
        }
        self._redis.lpush(self._key("work_log"), json.dumps(entry_data))
        self._redis.ltrim(self._key("work_log"), 0, 99)  # Keep last 100
    
    # ============ COMPREHENSIVE CONTEXT ============
    
    def get_full_context(self) -> Dict:
        """Get complete context for agent re-priming"""
        if self._redis is None:
            return {"error": "Redis unavailable"}
        
        # Get all data
        architecture = self.get_architecture()
        milestones = self.get_milestones()
        active_milestones = self.get_milestones(status="in_progress")
        completed_milestones = self.get_milestones(status="completed")
        
        tasks = self.get_tasks()
        active_tasks = self.get_tasks(status="in_progress")
        todo_tasks = self.get_tasks(status="todo")
        done_tasks = self.get_tasks(status="done")
        
        blockers = self.get_blockers(status="active")
        
        current_task = self.get_current_task()
        work_log = [json.loads(w) for w in self._redis.lrange(self._key("work_log"), 0, 19)]
        
        # Calculate progress
        total_milestones = len(milestones)
        completed_milestone_count = len(completed_milestones)
        total_tasks = len(tasks)
        done_task_count = len(done_tasks)
        
        progress_pct = 0
        if total_milestones > 0:
            progress_pct = int(100 * completed_milestone_count / total_milestones)
        
        return {
            "generated_at": datetime.now().isoformat(),
            "architecture": architecture,
            "big_picture": {
                "milestones": {
                    "total": total_milestones,
                    "completed": completed_milestone_count,
                    "in_progress": len(active_milestones),
                    "pending": len([m for m in milestones if m.status == "pending"]),
                    "completed_list": [asdict(m) for m in completed_milestones[-5:]],
                    "in_progress_list": [asdict(m) for m in active_milestones]
                },
                "progress_percentage": progress_pct
            },
            "mid_picture": {
                "tasks": {
                    "total": total_tasks,
                    "todo": len(todo_tasks),
                    "in_progress": len(active_tasks),
                    "done": done_task_count,
                    "active_list": [asdict(t) for t in active_tasks]
                },
                "blockers": {
                    "active": len(blockers),
                    "list": [asdict(b) for b in blockers]
                },
                "current_work": current_task
            },
            "recent_context": {
                "work_log": work_log,
                "last_20_actions": self._get_recent_actions()
            }
        }
    
    def _get_recent_actions(self) -> List[Dict]:
        """Get recent actions from all sessions"""
        if self._redis is None:
            return []
        
        recent = []
        session_keys = self._redis.keys("session:*:actions")
        
        for sk in sorted(session_keys, reverse=True)[:3]:
            actions = self._redis.lrange(sk, -5, -1)
            session_id = sk.split(":")[1]
            for a in reversed(actions):
                try:
                    data = json.loads(a)
                    data["session"] = session_id
                    recent.append(data)
                except:
                    pass
        
        return recent[:20]
    
    def print_full_context(self):
        """Print human-readable full context"""
        ctx = self.get_full_context()
        
        print("\n" + "=" * 70)
        print("  PROJECT CONTEXT - FOR AGENT RE-PRIMING")
        print("=" * 70)
        
        if "error" in ctx:
            print(f"  Error: {ctx['error']}")
            print("=" * 70 + "\n")
            return
        
        # Big Picture
        print("\n[ARCHITECTURE]")
        arch = ctx.get("architecture", {})
        if arch:
            print(f"  System: {arch.get('name', 'Unknown')}")
            components = arch.get("components", {})
            if components:
                print(f"  Components: {', '.join(components.keys())}")
        else:
            print("  Not yet documented - see ARCHITECTURE.md")
        
        # Milestones
        print("\n[BIG PICTURE - MILESTONES]")
        bp = ctx.get("big_picture", {})
        print(f"  Progress: {bp.get('progress_percentage', 0)}%")
        
        completed = bp.get("milestones", {}).get("completed_list", [])
        if completed:
            print(f"  Completed ({len(completed)}):")
            for m in completed:
                print(f"    - {m['name']}")
        
        in_progress = bp.get("milestones", {}).get("in_progress_list", [])
        if in_progress:
            print(f"  In Progress ({len(in_progress)}):")
            for m in in_progress:
                print(f"    - {m['name']}")
        
        # Mid Picture
        print("\n[MID PICTURE - TASKS]")
        mp = ctx.get("mid_picture", {})
        tasks_data = mp.get("tasks", {})
        print(f"  Tasks: {tasks_data.get('todo', 0)} todo, {tasks_data.get('in_progress', 0)} active, {tasks_data.get('done', 0)} done")
        
        active_tasks = tasks_data.get("active_list", [])
        if active_tasks:
            print(f"  Active:")
            for t in active_tasks[:5]:
                print(f"    - {t['title']}")
        
        blockers = mp.get("blockers", {}).get("list", [])
        if blockers:
            print(f"\n  BLOCKERS ({len(blockers)}):")
            for b in blockers:
                print(f"    - [{b['severity'].upper()}] {b['description']}")
        
        # Current Work
        current = mp.get("current_work")
        if current:
            print(f"\n  CURRENT: {current.get('task', 'Unknown')}")
            if current.get('details'):
                print(f"  Details: {current.get('details')}")
        
        # Recent Context
        print("\n[RECENT CONTEXT - LAST 20 ACTIONS]")
        recent = ctx.get("recent_context", {}).get("work_log", [])
        if recent:
            for r in recent[:10]:
                ts = r.get("timestamp", "")[:19]
                entry = r.get("entry", "")[:60]
                print(f"  [{ts}] {entry}")
        
        print("\n" + "=" * 70 + "\n")
    
    def initialize_defaults(self):
        """Initialize with BreakThrough Stack defaults"""
        if self._redis is None:
            return
        
        # Set default architecture
        if not self.get_architecture():
            arch = {
                "name": "BreakThrough Stack",
                "type": "Multi-Agent AI Harness",
                "version": "6.0",
                "purpose": "Agentic AI harness with multi-agent coordination, Redis HA, vector storage",
                "components": {
                    "redis_ha": {"type": "database", "status": "running", "description": "Redis HA cluster with Sentinel failover"},
                    "mcp_server": {"type": "protocol", "status": "ready", "description": "Model Context Protocol server"},
                    "session_logger": {"type": "logging", "status": "active", "description": "Session and action logging"},
                    "sync_service": {"type": "sync", "status": "active", "description": "Redis sync background service"},
                    "vector_store": {"type": "storage", "status": "active", "description": "Vector embeddings for fast search"}
                },
                "relationships": [
                    "redis_ha -> session_logger (stores session data)",
                    "redis_ha -> mcp_server (exposes data)",
                    "redis_ha -> sync_service (syncs logs)",
                    "mcp_server -> all_components (provides context)"
                ],
                "updated_at": datetime.now().isoformat()
            }
            self.set_architecture(arch)
        
        # Add initial milestones if none exist
        if not self.get_milestones():
            self.add_milestone("Redis HA Cluster", "Deploy Redis with triple redundancy and Sentinel failover", priority=10)
            self.add_milestone("MCP Server", "Create MCP server for context exposure to AI clients", priority=9)
            self.add_milestone("Redis Sync Service", "Background service to sync logs to Redis", priority=8)
            self.add_milestone("Session Context System", "Track session state and enable agent catch-up", priority=7)
            self.add_milestone("Bootstrap Automation", "Foolproof bootstrap for new OpenCode instances", priority=6)
            self.add_milestone("Project Context Tracking", "Milestones, tasks, blockers for project management", priority=5)
        
        print("[ProjectContext] Initialized with BreakThrough Stack defaults")


# Singleton instance
_manager = None

def get_context_manager() -> ProjectContextManager:
    """Get the context manager singleton"""
    global _manager
    if _manager is None:
        _manager = ProjectContextManager()
    return _manager


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Project Context Manager")
    parser.add_argument("--init", action="store_true", help="Initialize defaults")
    parser.add_argument("--context", action="store_true", help="Print full context")
    parser.add_argument("--milestone", type=str, help="Add milestone")
    parser.add_argument("--task", type=str, help="Add task")
    parser.add_argument("--blocker", type=str, help="Add blocker")
    parser.add_argument("--current", type=str, help="Set current task")
    parser.add_argument("--complete-milestone", type=str, help="Complete a milestone by name")
    parser.add_argument("--resolve-blocker", type=str, help="Resolve a blocker by ID")
    
    args = parser.parse_args()
    
    mgr = get_context_manager()
    
    if args.init:
        mgr.initialize_defaults()
        print("Initialized with defaults")
    
    if args.context:
        mgr.print_full_context()
    
    if args.milestone:
        mgr.add_milestone(args.milestone)
        print(f"Added milestone: {args.milestone}")
    
    if args.task:
        mgr.add_task(args.task, "")
        print(f"Added task: {args.task}")
    
    if args.blocker:
        mgr.add_blocker(args.blocker)
        print(f"Added blocker: {args.blocker}")
    
    if args.current:
        mgr.set_current_task(args.current)
        print(f"Current task: {args.current}")
    
    if args.complete_milestone:
        milestones = mgr.get_milestones(status="in_progress")
        for m in milestones:
            if args.complete_milestone.lower() in m.name.lower():
                mgr.complete_milestone(m.id)
                print(f"Completed milestone: {m.name}")
                break
    
    if args.resolve_blocker:
        mgr.resolve_blocker(args.resolve_blocker)
        print(f"Resolved blocker: {args.resolve_blocker}")
