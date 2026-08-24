"""
Project Context Manager: Store-backed multi-agent context

Semantic Relationship: ProjectContext persists_through Store (Redis when up, File always)

Provides architectural, big-picture, mid-picture, and recent context for new agents.
All data persists through a Store (Redis when up, File always) with relationships:

Context Layers:
- ARCHITECTURAL: System design, components, relationships
- BIG PICTURE: Project goals, milestones, roadmap
- MID PICTURE: Current work streams, tasks, blockers
- RECENT: Current session, latest actions, immediate context

Usage:
    from project_context import get_project_context_manager_instance

    # Get full context for re-priming
    ctx = get_project_context_manager_instance().derive_full_context_for_agent_repriming()

    # Update current work
    get_project_context_manager_instance().set_current_task_with_details("Deploying Redis HA")

    # Add blocker preventing task
    get_project_context_manager_instance().record_blocker_preventing_task("Waiting for GPU allocation")

    # Complete milestone
    get_project_context_manager_instance().mark_milestone_as_completed("Redis HA Deployed")
"""

import os
import sys
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for standalone runs


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

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_store()
        return cls._instance

    def _init_store(self):
        """Initialize persistence through a Store (Redis when up, File always).

        Semantic Relationship: ProjectContext persists_through Store

        Replaces the old raw-Redis connect that HARD-FAILED when Redis was down;
        the Store always works (file fallback), so context is always available.
        """
        from core.foundation.store import create_store
        self.store = create_store(prefer_redis=True)

    def _key(self, name: str) -> str:
        """Get the prefixed Store key for a project-context value."""
        return f"context:{name}"

    def _gen_id(self, prefix: str) -> str:
        """Collision-resistant id: prefix + timestamp + random suffix."""
        return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}"
    
    # ============ ARCHITECTURAL CONTEXT ============

    def establish_architecture_with_relationships(self, architecture: Dict) -> bool:
        """
        Establish architecture documentation with component relationships.

        Semantic Relationship: Architecture documents SystemDesign

        Args:
            architecture: Complete architecture specification

        Returns:
            True if successfully established
        """
        self.store.set(self._key("architecture"), json.dumps(architecture))
        return True

    # Backward compatibility alias
    def set_architecture(self, architecture: Dict) -> bool:
        """Deprecated: Use establish_architecture_with_relationships() instead"""
        return self.establish_architecture_with_relationships(architecture)

    def load_architecture_documentation(self) -> Optional[Dict]:
        """
        Load architectural documentation.

        Semantic Relationship: Architecture located_in Store

        Returns:
            Architecture specification or None if not found
        """
        data = self.store.get(self._key("architecture"))
        return json.loads(data) if data else None

    # Backward compatibility alias
    def get_architecture(self) -> Optional[Dict]:
        """Deprecated: Use load_architecture_documentation() instead"""
        return self.load_architecture_documentation()

    def update_architecture_component_details(self, component: str, details: Dict) -> None:
        """
        Update a specific component in architecture.

        Semantic Relationship: ComponentDetails updated_at Timestamp

        Args:
            component: Component name to update
            details: New component details
        """
        arch = self.load_architecture_documentation() or {"components": {}, "relationships": [], "updated_at": ""}
        arch["components"][component] = details
        arch["updated_at"] = datetime.now().isoformat()
        self.establish_architecture_with_relationships(arch)

    # Backward compatibility alias
    def update_architecture_component(self, component: str, details: Dict) -> None:
        """Deprecated: Use update_architecture_component_details() instead"""
        return self.update_architecture_component_details(component, details)
    
    # ============ BIG PICTURE (Milestones) ============

    def record_milestone_marking_progress(self, name: str, description: str, priority: int = 0) -> str:
        """
        Record a milestone marking project progress.

        Semantic Relationship: Milestone marks Progress

        Args:
            name: Milestone name
            description: Milestone description
            priority: Priority level (higher = more important)

        Returns:
            Milestone ID
        """

        milestone_id = self._gen_id("ms")
        milestone = Milestone(
            id=milestone_id,
            name=name,
            description=description,
            status="pending",
            created_at=datetime.now().isoformat(),
            priority=priority
        )

        self.store.hset(
            self._key("milestones"),
            milestone_id,
            json.dumps(asdict(milestone))
        )

        return milestone_id

    # Backward compatibility alias
    def add_milestone(self, name: str, description: str, priority: int = 0) -> str:
        """Deprecated: Use record_milestone_marking_progress() instead"""
        return self.record_milestone_marking_progress(name, description, priority)

    def load_milestones_filtered_by_status(self, status: Optional[str] = None) -> List[Milestone]:
        """
        Load milestones optionally filtered by status.

        Semantic Relationship: Milestone filtered_by Status

        Args:
            status: Optional status filter (pending, in_progress, completed, blocked)

        Returns:
            List of milestones sorted by priority and creation time
        """

        milestones = []
        data = self.store.hgetall(self._key("milestones"))

        for m_id, m_json in data.items():
            m = Milestone(**json.loads(m_json))
            if status is None or m.status == status:
                milestones.append(m)

        return sorted(milestones, key=lambda x: (-x.priority, x.created_at))

    # Backward compatibility alias
    def get_milestones(self, status: Optional[str] = None) -> List[Milestone]:
        """Deprecated: Use load_milestones_filtered_by_status() instead"""
        return self.load_milestones_filtered_by_status(status)

    def update_milestone_status_to(self, milestone_id: str, new_status: str) -> None:
        """
        Update milestone status.

        Semantic Relationship: MilestoneStatus updated_to NewStatus

        Args:
            milestone_id: ID of milestone to update
            new_status: New status (pending, in_progress, completed, blocked)
        """

        data = self.store.hget(self._key("milestones"), milestone_id)
        if data:
            m = Milestone(**json.loads(data))
            m.status = new_status
            if new_status == "completed":
                m.completed_at = datetime.now().isoformat()
            self.store.hset(self._key("milestones"), milestone_id, json.dumps(asdict(m)))

    # Backward compatibility alias
    def update_milestone_status(self, milestone_id: str, status: str) -> None:
        """Deprecated: Use update_milestone_status_to() instead"""
        return self.update_milestone_status_to(milestone_id, status)

    def mark_milestone_as_completed(self, milestone_id: str) -> None:
        """
        Mark milestone as completed.

        Semantic Relationship: Milestone marked_as Completed

        Args:
            milestone_id: ID of milestone to mark complete
        """
        self.update_milestone_status_to(milestone_id, "completed")

    # Backward compatibility alias
    def complete_milestone(self, milestone_id: str) -> None:
        """Deprecated: Use mark_milestone_as_completed() instead"""
        return self.mark_milestone_as_completed(milestone_id)
    
    # ============ MID PICTURE (Tasks) ============

    def register_task_derived_from_milestone(self, title: str, description: str, milestone_id: Optional[str] = None,
                 assignee: Optional[str] = None) -> str:
        """
        Register a task derived from a milestone.

        Semantic Relationship: Task derived_from Milestone

        Args:
            title: Task title
            description: Task description
            milestone_id: Parent milestone ID
            assignee: Agent assigned to task

        Returns:
            Task ID
        """

        task_id = self._gen_id("task")
        task = Task(
            id=task_id,
            title=title,
            description=description,
            status="todo",
            milestone_id=milestone_id,
            assignee=assignee,
            created_at=datetime.now().isoformat()
        )

        self.store.hset(self._key("tasks"), task_id, json.dumps(asdict(task)))
        return task_id

    # Backward compatibility alias
    def add_task(self, title: str, description: str, milestone_id: Optional[str] = None,
                 assignee: Optional[str] = None) -> str:
        """Deprecated: Use register_task_derived_from_milestone() instead"""
        return self.register_task_derived_from_milestone(title, description, milestone_id, assignee)

    def load_tasks_filtered_by_status(self, status: Optional[str] = None, milestone_id: Optional[str] = None) -> List[Task]:
        """
        Load tasks optionally filtered by status and milestone.

        Semantic Relationship: Task filtered_by Status OR Milestone

        Args:
            status: Optional status filter (todo, in_progress, done, blocked)
            milestone_id: Optional milestone filter

        Returns:
            List of tasks sorted by creation time
        """

        tasks = []
        data = self.store.hgetall(self._key("tasks"))

        for t_id, t_json in data.items():
            t = Task(**json.loads(t_json))
            if status and t.status != status:
                continue
            if milestone_id and t.milestone_id != milestone_id:
                continue
            tasks.append(t)

        return sorted(tasks, key=lambda x: x.created_at, reverse=True)

    # Backward compatibility alias
    def get_tasks(self, status: Optional[str] = None, milestone_id: Optional[str] = None) -> List[Task]:
        """Deprecated: Use load_tasks_filtered_by_status() instead"""
        return self.load_tasks_filtered_by_status(status, milestone_id)

    def update_task_status_to(self, task_id: str, new_status: str) -> None:
        """
        Update task status.

        Semantic Relationship: TaskStatus updated_to NewStatus

        Args:
            task_id: ID of task to update
            new_status: New status (todo, in_progress, done, blocked)
        """

        data = self.store.hget(self._key("tasks"), task_id)
        if data:
            t = Task(**json.loads(data))
            t.status = new_status
            t.updated_at = datetime.now().isoformat()
            if new_status == "done":
                t.completed_at = datetime.now().isoformat()
            self.store.hset(self._key("tasks"), task_id, json.dumps(asdict(t)))

    # Backward compatibility alias
    def update_task_status(self, task_id: str, status: str) -> None:
        """Deprecated: Use update_task_status_to() instead"""
        return self.update_task_status_to(task_id, status)
    
    # ============ BLOCKERS ============

    def record_blocker_preventing_task(self, description: str, severity: str = "medium", task_id: Optional[str] = None) -> str:
        """
        Record a blocker preventing task progress.

        Semantic Relationship: Blocker prevents Progress

        Args:
            description: Blocker description
            severity: Severity level (low, medium, high, critical)
            task_id: Task ID if blocker is task-specific

        Returns:
            Blocker ID
        """

        blocker_id = self._gen_id("blk")
        blocker = Blocker(
            id=blocker_id,
            description=description,
            severity=severity,
            status="active",
            created_at=datetime.now().isoformat(),
            task_id=task_id
        )

        self.store.hset(self._key("blockers"), blocker_id, json.dumps(asdict(blocker)))
        return blocker_id

    # Backward compatibility alias
    def add_blocker(self, description: str, severity: str = "medium", task_id: Optional[str] = None) -> str:
        """Deprecated: Use record_blocker_preventing_task() instead"""
        return self.record_blocker_preventing_task(description, severity, task_id)

    def load_blockers_filtered_by_status(self, status: Optional[str] = None) -> List[Blocker]:
        """
        Load blockers optionally filtered by status.

        Semantic Relationship: Blocker filtered_by Status

        Args:
            status: Optional status filter (active, resolved)

        Returns:
            List of blockers sorted by creation time
        """

        blockers = []
        data = self.store.hgetall(self._key("blockers"))

        for b_id, b_json in data.items():
            b = Blocker(**json.loads(b_json))
            if status is None or b.status == status:
                blockers.append(b)

        return sorted(blockers, key=lambda x: x.created_at, reverse=True)

    # Backward compatibility alias
    def get_blockers(self, status: Optional[str] = None) -> List[Blocker]:
        """Deprecated: Use load_blockers_filtered_by_status() instead"""
        return self.load_blockers_filtered_by_status(status)

    def mark_blocker_as_resolved(self, blocker_id: str) -> None:
        """
        Mark blocker as resolved.

        Semantic Relationship: Blocker resolved_at Timestamp

        Args:
            blocker_id: ID of blocker to resolve
        """

        data = self.store.hget(self._key("blockers"), blocker_id)
        if data:
            b = Blocker(**json.loads(data))
            b.status = "resolved"
            b.resolved_at = datetime.now().isoformat()
            self.store.hset(self._key("blockers"), blocker_id, json.dumps(asdict(b)))

    # Backward compatibility alias
    def resolve_blocker(self, blocker_id: str) -> None:
        """Deprecated: Use mark_blocker_as_resolved() instead"""
        return self.mark_blocker_as_resolved(blocker_id)
    
    # ============ CURRENT WORK ============

    def set_current_task_with_details(self, task: str, details: str = "") -> None:
        """
        Set current task with optional details.

        Semantic Relationship: CurrentTask recorded_at Timestamp

        Args:
            task: Current task name
            details: Optional task details
        """

        data = {
            "task": task,
            "details": details,
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.store.set(self._key("current_task"), json.dumps(data))

    # Backward compatibility alias
    def set_current_task(self, task: str, details: str = "") -> None:
        """Deprecated: Use set_current_task_with_details() instead"""
        return self.set_current_task_with_details(task, details)

    def load_current_task_in_progress(self) -> Optional[Dict]:
        """
        Load current task in progress.

        Semantic Relationship: CurrentTask located_in Store

        Returns:
            Current task dictionary or None if not set
        """

        data = self.store.get(self._key("current_task"))
        return json.loads(data) if data else None

    # Backward compatibility alias
    def get_current_task(self) -> Optional[Dict]:
        """Deprecated: Use load_current_task_in_progress() instead"""
        return self.load_current_task_in_progress()

    def append_entry_to_work_log(self, entry: str) -> None:
        """
        Append entry to work log.

        Semantic Relationship: WorkLogEntry created_at Timestamp

        Args:
            entry: Work log entry text
        """

        work_log = self.store.lrange(self._key("work_log"), 0, 49)

        entry_data = {
            "entry": entry,
            "timestamp": datetime.now().isoformat()
        }
        self.store.lpush(self._key("work_log"), json.dumps(entry_data))
        self.store.ltrim(self._key("work_log"), 0, 99)  # Keep last 100

    # Backward compatibility alias
    def add_to_work_log(self, entry: str) -> None:
        """Deprecated: Use append_entry_to_work_log() instead"""
        return self.append_entry_to_work_log(entry)
    
    # ============ COMPREHENSIVE CONTEXT ============

    def derive_full_context_for_agent_repriming(self) -> Dict:
        """
        Derive full context for agent re-priming.

        Semantic Relationship: FullContext derived_from AllLayers (architectural, big-picture, mid-picture, recent)

        Returns:
            Complete context dictionary for new agents
        """

        # Get all data
        architecture = self.load_architecture_documentation()
        milestones = self.load_milestones_filtered_by_status()
        active_milestones = self.load_milestones_filtered_by_status(status="in_progress")
        completed_milestones = self.load_milestones_filtered_by_status(status="completed")

        tasks = self.load_tasks_filtered_by_status()
        active_tasks = self.load_tasks_filtered_by_status(status="in_progress")
        todo_tasks = self.load_tasks_filtered_by_status(status="todo")
        done_tasks = self.load_tasks_filtered_by_status(status="done")

        blockers = self.load_blockers_filtered_by_status(status="active")

        current_task = self.load_current_task_in_progress()
        work_log = [json.loads(w) for w in self.store.lrange(self._key("work_log"), 0, 19)]

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
                "last_20_actions": self._load_recent_actions_from_sessions()
            }
        }

    # Backward compatibility alias
    def get_full_context(self) -> Dict:
        """Deprecated: Use derive_full_context_for_agent_repriming() instead"""
        return self.derive_full_context_for_agent_repriming()

    def _load_recent_actions_from_sessions(self) -> List[Dict]:
        """
        Load recent actions from all sessions.

        Semantic Relationship: RecentActions derived_from SessionKeys

        Returns:
            List of recent actions
        """

        recent = []
        session_keys = self.store.keys("session:*:actions")

        for sk in sorted(session_keys, reverse=True)[:3]:
            actions = self.store.lrange(sk, -5, -1)
            session_id = sk.split(":")[1]
            for a in reversed(actions):
                try:
                    data = json.loads(a)
                    data["session"] = session_id
                    recent.append(data)
                except:
                    pass

        return recent[:20]

    # Backward compatibility alias
    def _get_recent_actions(self) -> List[Dict]:
        """Deprecated internal: Use _load_recent_actions_from_sessions() instead"""
        return self._load_recent_actions_from_sessions()
    
    def print_full_context_for_repriming(self) -> None:
        """
        Print human-readable full context for agent re-priming.

        Semantic Relationship: ReportOutput derived_from FullContext

        Displays architectural, big-picture, mid-picture, and recent context.
        """
        ctx = self.derive_full_context_for_agent_repriming()
        
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

    # Backward compatibility alias
    def print_full_context(self) -> None:
        """Deprecated: Use print_full_context_for_repriming() instead"""
        return self.print_full_context_for_repriming()

    def initialize_with_akashic_aurora_defaults(self) -> None:
        """
        Initialize project context with Akashic Aurora defaults.

        Semantic Relationship: ProjectContext initialized_with StandardDefaults

        Sets up default architecture, milestones, and system configuration.
        """

        # Set default architecture
        if not self.load_architecture_documentation():
            arch = {
                "name": "Akashic Aurora",
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
            self.establish_architecture_with_relationships(arch)

        # Add initial milestones if none exist
        if not self.load_milestones_filtered_by_status():
            self.record_milestone_marking_progress("Redis HA Cluster", "Deploy Redis with triple redundancy and Sentinel failover", priority=10)
            self.record_milestone_marking_progress("MCP Server", "Create MCP server for context exposure to AI clients", priority=9)
            self.record_milestone_marking_progress("Redis Sync Service", "Background service to sync logs to Redis", priority=8)
            self.record_milestone_marking_progress("Session Context System", "Track session state and enable agent catch-up", priority=7)
            self.record_milestone_marking_progress("Bootstrap Automation", "Foolproof bootstrap for new OpenCode instances", priority=6)
            self.record_milestone_marking_progress("Project Context Tracking", "Milestones, tasks, blockers for project management", priority=5)

        print("[ProjectContext] Initialized with Akashic Aurora defaults")

    # Backward compatibility alias
    def initialize_defaults(self) -> None:
        """Deprecated: Use initialize_with_akashic_aurora_defaults() instead"""
        return self.initialize_with_akashic_aurora_defaults()


# Singleton instance
_manager = None

def get_project_context_manager_instance() -> ProjectContextManager:
    """
    Get the project context manager singleton instance.

    Semantic Relationship: ManagerInstance references_to GlobalSingleton

    Returns:
        The global ProjectContextManager instance
    """
    global _manager
    if _manager is None:
        _manager = ProjectContextManager()
    return _manager


# Backward compatibility alias
def get_context_manager() -> ProjectContextManager:
    """Deprecated: Use get_project_context_manager_instance() instead"""
    return get_project_context_manager_instance()


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

    mgr = get_project_context_manager_instance()

    if args.init:
        mgr.initialize_with_akashic_aurora_defaults()
        print("Initialized with defaults")

    if args.context:
        mgr.print_full_context_for_repriming()

    if args.milestone:
        mgr.record_milestone_marking_progress(args.milestone, "")
        print(f"Added milestone: {args.milestone}")

    if args.task:
        mgr.register_task_derived_from_milestone(args.task, "")
        print(f"Added task: {args.task}")

    if args.blocker:
        mgr.record_blocker_preventing_task(args.blocker)
        print(f"Added blocker: {args.blocker}")

    if args.current:
        mgr.set_current_task_with_details(args.current)
        print(f"Current task: {args.current}")

    if args.complete_milestone:
        milestones = mgr.load_milestones_filtered_by_status(status="in_progress")
        for m in milestones:
            if args.complete_milestone.lower() in m.name.lower():
                mgr.mark_milestone_as_completed(m.id)
                print(f"Completed milestone: {m.name}")
                break

    if args.resolve_blocker:
        mgr.mark_blocker_as_resolved(args.resolve_blocker)
        print(f"Resolved blocker: {args.resolve_blocker}")
