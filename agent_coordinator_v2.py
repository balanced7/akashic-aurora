"""
Agent Coordination System - Intelligent Multi-Agent Orchestration
============================================================
Enables agents to declare their intent, scope, and status for intelligent coordination.

AGENT MANIFEST FIELDS:
- intent: What the agent plans to do
- scope: Files/modules being worked on
- status: idle/busy/paused/completed
- eta_minutes: Estimated time to completion
- priority: low/normal/high/critical
- dependencies: What this agent needs from others
- blocked_by: What's preventing progress

COORDINATION FEATURES:
- Agent manifest broadcasts
- Resource locking (file/area locks)
- Task registry
- Conflict detection
- Dependency resolution

Author: Senior Systems Architect
Version: 1.0 Coordination
"""

import os
import sys
import json
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field

sys.path.insert(0, r'E:\AI-Setup')

# ============================================================================
# CONFIGURATION
# ============================================================================

COORD_DIR = r"E:\AI-Setup\blackboard_data\agent_coordination"
MANIFEST_DIR = os.path.join(COORD_DIR, "manifests")
LOCK_DIR = os.path.join(COORD_DIR, "locks")
TASK_DIR = os.path.join(COORD_DIR, "tasks")

os.makedirs(MANIFEST_DIR, exist_ok=True)
os.makedirs(LOCK_DIR, exist_ok=True)
os.makedirs(TASK_DIR, exist_ok=True)

MANIFEST_TTL = 300  # 5 minutes - manifest expires if not refreshed


class AgentStatus(Enum):
    IDLE = "idle"
    BUSY = "busy"
    PAUSED = "paused"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    WAITING = "waiting"


class Priority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentManifest:
    """
    Agent's declaration of intent and scope.
    
    This is broadcast periodically so other agents know what this agent is doing.
    """
    agent_id: str
    role: str
    
    # Intent
    intent: str = ""  # "Refactoring authentication module"
    intent_detail: str = ""  # More detailed description
    
    # Scope - what files/areas being worked on
    scope: List[str] = field(default_factory=list)  # ["auth.py", "models/user.py"]
    areas: List[str] = field(default_factory=list)  # ["authentication", "security"]
    
    # Status
    status: AgentStatus = AgentStatus.IDLE
    priority: Priority = Priority.NORMAL
    
    # ETA
    eta_minutes: int = 0
    started_at: str = ""
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # Agent IDs we need help from
    blocked_by: List[str] = field(default_factory=list)  # What's blocking us
    waiting_for: List[str] = field(default_factory=list)  # Tasks we're waiting on
    
    # Current work
    current_task: str = ""
    current_task_id: str = ""
    progress_percent: float = 0.0
    
    # Metadata
    last_updated: str = ""
    session_id: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "intent": self.intent,
            "intent_detail": self.intent_detail,
            "scope": self.scope,
            "areas": self.areas,
            "status": self.status.value,
            "priority": self.priority.value,
            "eta_minutes": self.eta_minutes,
            "started_at": self.started_at,
            "dependencies": self.dependencies,
            "blocked_by": self.blocked_by,
            "waiting_for": self.waiting_for,
            "current_task": self.current_task,
            "current_task_id": self.current_task_id,
            "progress_percent": self.progress_percent,
            "last_updated": self.last_updated,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'AgentManifest':
        return cls(
            agent_id=d["agent_id"],
            role=d.get("role", "unknown"),
            intent=d.get("intent", ""),
            intent_detail=d.get("intent_detail", ""),
            scope=d.get("scope", []),
            areas=d.get("areas", []),
            status=AgentStatus(d.get("status", "idle")),
            priority=Priority(d.get("priority", "normal")),
            eta_minutes=d.get("eta_minutes", 0),
            started_at=d.get("started_at", ""),
            dependencies=d.get("dependencies", []),
            blocked_by=d.get("blocked_by", []),
            waiting_for=d.get("waiting_for", []),
            current_task=d.get("current_task", ""),
            current_task_id=d.get("current_task_id", ""),
            progress_percent=d.get("progress_percent", 0.0),
            last_updated=d.get("last_updated", ""),
            session_id=d.get("session_id", "")
        )


@dataclass  
class ResourceLock:
    """Lock on a file, directory, or area"""
    lock_id: str
    resource: str  # File path or area name
    lock_type: str  # "exclusive" or "shared"
    agent_id: str
    purpose: str
    created_at: str
    expires_at: str
    priority: Priority = Priority.NORMAL


class AgentCoordinator:
    """
    Coordinates multiple agents by tracking manifests, locks, and tasks.
    """
    
    _instance = None
    
    def __init__(self):
        self.agent_id = self._get_my_agent_id()
        self._manifest: Optional[AgentManifest] = None
        self._init_manifest()
    
    def _get_my_agent_id(self) -> str:
        """Get this agent's ID"""
        identity_file = os.path.join(COORD_DIR, "state", "identity.json")
        if os.path.exists(identity_file):
            try:
                with open(identity_file, 'r') as f:
                    data = json.load(f)
                return data.get("agent_id", f"agent_{uuid.uuid4().hex[:8]}")
            except:
                pass
        return f"agent_{uuid.uuid4().hex[:8]}"
    
    def _init_manifest(self):
        """Initialize this agent's manifest"""
        self._manifest = AgentManifest(
            agent_id=self.agent_id,
            role=os.environ.get("OPENCODE_AGENT_ROLE", "generator"),
            status=AgentStatus.IDLE,
            last_updated=datetime.now().isoformat()
        )
    
    # =========================================================================
    # MANIFEST MANAGEMENT
    # =========================================================================
    
    def update_manifest(
        self,
        intent: str = None,
        scope: List[str] = None,
        areas: List[str] = None,
        status: AgentStatus = None,
        priority: Priority = None,
        eta_minutes: int = None,
        current_task: str = None,
        progress_percent: float = None,
        blocked_by: List[str] = None,
        waiting_for: List[str] = None
    ) -> AgentManifest:
        """
        Update this agent's manifest and broadcast to others.
        """
        manifest = self._manifest
        
        if intent is not None:
            manifest.intent = intent
        if scope is not None:
            manifest.scope = scope
        if areas is not None:
            manifest.areas = areas
        if status is not None:
            if isinstance(status, AgentStatus):
                manifest.status = status
            elif isinstance(status, str):
                try:
                    manifest.status = AgentStatus(status.lower())
                except:
                    manifest.status = AgentStatus.IDLE
            else:
                manifest.status = AgentStatus.IDLE
        if priority is not None:
            if isinstance(priority, Priority):
                manifest.priority = priority
            elif isinstance(priority, str):
                try:
                    manifest.priority = Priority(priority.lower())
                except:
                    manifest.priority = Priority.NORMAL
            else:
                manifest.priority = Priority.NORMAL
        if eta_minutes is not None:
            manifest.eta_minutes = eta_minutes
        if current_task is not None:
            manifest.current_task = current_task
        if progress_percent is not None:
            manifest.progress_percent = progress_percent
        if blocked_by is not None:
            manifest.blocked_by = blocked_by
        if waiting_for is not None:
            manifest.waiting_for = waiting_for
        
        manifest.last_updated = datetime.now().isoformat()
        
        # Save to file
        self._save_manifest(manifest)
        
        # Also broadcast via fast_agent_comm
        self._broadcast_manifest(manifest)
        
        return manifest
    
    def _save_manifest(self, manifest: AgentManifest):
        """Save manifest to file"""
        manifest_file = os.path.join(MANIFEST_DIR, f"{manifest.agent_id}.json")
        with open(manifest_file, 'w') as f:
            json.dump(manifest.to_dict(), f, indent=2)
    
    def _broadcast_manifest(self, manifest: AgentManifest):
        """Broadcast manifest to other agents"""
        try:
            from fast_agent_comm import get_fast_comm
            comm = get_fast_comm()
            if comm.is_available:
                comm.set_agent_id(self.agent_id)
                comm.send_broadcast(
                    msg_type="manifest_update",
                    content=manifest.to_dict()
                )
        except:
            pass
    
    def get_manifest(self) -> AgentManifest:
        """Get this agent's manifest"""
        return self._manifest
    
    def get_all_manifests(self, include_self: bool = True) -> List[AgentManifest]:
        """
        Get all active agents' manifests.
        """
        manifests = []
        cutoff = time.time() - MANIFEST_TTL
        
        for fname in os.listdir(MANIFEST_DIR):
            if not fname.endswith('.json'):
                continue
            
            fpath = os.path.join(MANIFEST_DIR, fname)
            
            # Check if recent enough
            if os.path.getmtime(fpath) < cutoff:
                continue
            
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                
                manifest = AgentManifest.from_dict(data)
                
                if not include_self and manifest.agent_id == self.agent_id:
                    continue
                
                manifests.append(manifest)
            except:
                pass
        
        return manifests
    
    def get_manifest_by_agent(self, agent_id: str) -> Optional[AgentManifest]:
        """Get a specific agent's manifest"""
        manifest_file = os.path.join(MANIFEST_DIR, f"{agent_id}.json")
        
        if not os.path.exists(manifest_file):
            return None
        
        try:
            with open(manifest_file, 'r') as f:
                data = json.load(f)
            return AgentManifest.from_dict(data)
        except:
            return None
    
    # =========================================================================
    # RESOURCE LOCKING
    # =========================================================================
    
    def lock_resource(
        self,
        resource: str,
        lock_type: str = "exclusive",
        purpose: str = "",
        ttl_seconds: int = 300,
        priority: Priority = Priority.NORMAL
    ) -> Optional[ResourceLock]:
        """
        Lock a file or area for exclusive or shared access.
        
        Args:
            resource: File path or area name
            lock_type: "exclusive" (one agent) or "shared" (multiple OK)
            purpose: Why we're locking it
            ttl_seconds: How long until lock expires
            priority: Lock priority
            
        Returns:
            ResourceLock if successful, None if conflict
        """
        lock_id = str(uuid.uuid4())[:8]
        now = datetime.now()
        expires_at = datetime.fromtimestamp(now.timestamp() + ttl_seconds).isoformat()
        
        lock = ResourceLock(
            lock_id=lock_id,
            resource=resource,
            lock_type=lock_type,
            agent_id=self.agent_id,
            purpose=purpose,
            created_at=now.isoformat(),
            expires_at=expires_at,
            priority=priority
        )
        
        lock_file = os.path.join(LOCK_DIR, f"{hash(resource) % 10000:04d}_{lock_id}.json")
        
        # Check for conflicts
        existing = self._get_resource_lock(resource)
        if existing and existing.lock_type == "exclusive" and existing.agent_id != self.agent_id:
            # Check if expired
            if datetime.fromisoformat(existing.expires_at) > now:
                return None  # Can't lock - someone else has it
        
        with open(lock_file, 'w') as f:
            json.dump({
                **lock.__dict__,
                "priority": lock.priority.value
            }, f, indent=2)
        
        # Broadcast lock
        self._broadcast_lock(lock, "acquired")
        
        return lock
    
    def unlock_resource(self, resource: str) -> bool:
        """Release a lock on a resource"""
        for fname in os.listdir(LOCK_DIR):
            if not fname.endswith('.json'):
                continue
            
            fpath = os.path.join(LOCK_DIR, fname)
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                
                if data.get("resource") == resource and data.get("agent_id") == self.agent_id:
                    os.remove(fpath)
                    
                    # Broadcast unlock
                    self._broadcast_lock(data, "released")
                    return True
            except:
                pass
        
        return False
    
    def _get_resource_lock(self, resource: str) -> Optional[ResourceLock]:
        """Get existing lock on a resource"""
        for fname in os.listdir(LOCK_DIR):
            if not fname.endswith('.json'):
                continue
            
            fpath = os.path.join(LOCK_DIR, fname)
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                
                if data.get("resource") == resource:
                    # Check if expired
                    if datetime.fromisoformat(data["expires_at"]) < datetime.now():
                        os.remove(fpath)  # Remove expired
                        continue
                    
                    data["priority"] = Priority(data.get("priority", "normal"))
                    return ResourceLock(**data)
            except:
                pass
        
        return None
    
    def get_all_locks(self) -> List[ResourceLock]:
        """Get all active locks"""
        locks = []
        now = datetime.now()
        
        for fname in os.listdir(LOCK_DIR):
            if not fname.endswith('.json'):
                continue
            
            fpath = os.path.join(LOCK_DIR, fname)
            try:
                with open(fpath, 'r') as f:
                    data = json.load(f)
                
                if datetime.fromisoformat(data["expires_at"]) < now:
                    os.remove(fpath)
                    continue
                
                locks.append(ResourceLock(**data))
            except:
                pass
        
        return locks
    
    def is_resource_locked(self, resource: str, by_self: bool = False) -> bool:
        """Check if resource is locked"""
        lock = self._get_resource_lock(resource)
        if not lock:
            return False
        if by_self and lock.agent_id != self.agent_id:
            return False
        return True
    
    def _broadcast_lock(self, lock_data: Dict, action: str):
        """Broadcast lock change"""
        try:
            from fast_agent_comm import get_fast_comm
            comm = get_fast_comm()
            if comm.is_available:
                comm.set_agent_id(self.agent_id)
                comm.send_broadcast(
                    msg_type="lock_update",
                    content={
                        "action": action,
                        "lock": lock_data
                    }
                )
        except:
            pass
    
    # =========================================================================
    # CONFLICT DETECTION
    # =========================================================================
    
    def check_scoped_conflicts(
        self,
        scope: List[str],
        areas: List[str]
    ) -> List[Dict]:
        """
        Check if proposed scope conflicts with other agents' work.
        
        Returns list of conflicts with details.
        """
        conflicts = []
        
        for manifest in self.get_all_manifests(include_self=False):
            if manifest.status == AgentStatus.COMPLETED:
                continue
            
            # Check file scope overlap
            for file in scope:
                if file in manifest.scope:
                    conflicts.append({
                        "type": "file_conflict",
                        "agent_id": manifest.agent_id,
                        "file": file,
                        "their_intent": manifest.intent,
                        "their_status": manifest.status.value
                    })
            
            # Check area overlap
            for area in areas:
                if area in manifest.areas:
                    conflicts.append({
                        "type": "area_conflict", 
                        "agent_id": manifest.agent_id,
                        "area": area,
                        "their_intent": manifest.intent,
                        "their_status": manifest.status.value
                    })
        
        return conflicts
    
    def find_available_agents(
        self,
        role: str = None,
        status: AgentStatus = None,
        not_busy: bool = True
    ) -> List[AgentManifest]:
        """Find agents that match criteria"""
        matching = []
        
        for manifest in self.get_all_manifests(include_self=False):
            if role and manifest.role != role:
                continue
            if status and manifest.status != status:
                continue
            if not_busy and manifest.status == AgentStatus.BUSY:
                continue
            
            matching.append(manifest)
        
        return matching
    
    # =========================================================================
    # HELP REQUESTS
    # =========================================================================
    
    def request_help(
        self,
        help_type: str,
        description: str,
        scope: List[str] = None,
        priority: Priority = Priority.NORMAL
    ) -> Optional[str]:
        """
        Request help from another agent.
        
        Returns request ID if broadcast successfully.
        """
        try:
            from fast_agent_comm import get_fast_comm
            comm = get_fast_comm()
            if comm.is_available:
                comm.set_agent_id(self.agent_id)
                
                # Update our manifest to show we're blocked
                self.update_manifest(
                    status=AgentStatus.BLOCKED,
                    waiting_for=[help_type]
                )
                
                msg_id = comm.send_broadcast(
                    msg_type="help_request",
                    content={
                        "requesting_agent": self.agent_id,
                        "help_type": help_type,
                        "description": description,
                        "scope": scope or [],
                        "priority": priority.value,
                        "manifest": self._manifest.to_dict()
                    }
                )
                return msg_id
        except:
            pass
        
        return None
    
    def offer_help(
        self,
        to_agent: str,
        help_type: str,
        description: str
    ) -> Optional[str]:
        """Offer help to a specific agent"""
        try:
            from fast_agent_comm import get_fast_comm
            comm = get_fast_comm()
            if comm.is_available:
                comm.set_agent_id(self.agent_id)
                return comm.send_direct(
                    to_agent=to_agent,
                    msg_type="help_offer",
                    content={
                        "offering_agent": self.agent_id,
                        "help_type": help_type,
                        "description": description
                    }
                )
        except:
            pass
        
        return None
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    def get_system_status(self) -> Dict:
        """Get full coordination system status"""
        manifests = self.get_all_manifests()
        locks = self.get_all_locks()
        
        busy_agents = [m for m in manifests if m.status == AgentStatus.BUSY]
        idle_agents = [m for m in manifests if m.status == AgentStatus.IDLE]
        blocked_agents = [m for m in manifests if m.status == AgentStatus.BLOCKED]
        
        return {
            "my_agent_id": self.agent_id,
            "my_manifest": self._manifest.to_dict(),
            "total_agents": len(manifests),
            "busy_agents": len(busy_agents),
            "idle_agents": len(idle_agents),
            "blocked_agents": len(blocked_agents),
            "active_locks": len(locks),
            "conflicts_detected": len(self.check_scoped_conflicts(
                self._manifest.scope,
                self._manifest.areas
            )),
            "agents": [m.to_dict() for m in manifests],
            "locks": [l.__dict__ for l in locks]
        }
    
    def print_status(self):
        """Print human-readable coordination status"""
        status = self.get_system_status()
        
        print("\n" + "=" * 60)
        print("AGENT COORDINATION STATUS")
        print("=" * 60)
        
        print(f"\nMy Agent: {status['my_agent_id']}")
        print(f"My Intent: {status['my_manifest']['intent'] or 'None'}")
        print(f"My Status: {status['my_manifest']['status']}")
        print(f"My Scope: {', '.join(status['my_manifest']['scope']) or 'None'}")
        
        print(f"\nSystem:")
        print(f"  Total Agents: {status['total_agents']}")
        print(f"  Busy: {status['busy_agents']}")
        print(f"  Idle: {status['idle_agents']}")
        print(f"  Blocked: {status['blocked_agents']}")
        print(f"  Active Locks: {status['active_locks']}")
        print(f"  Conflicts: {status['conflicts_detected']}")
        
        if status['agents']:
            print("\nOther Agents:")
            for a in status['agents']:
                if a['agent_id'] == status['my_agent_id']:
                    continue
                print(f"  [{a['status']}] {a['agent_id'][:12]}...")
                print(f"    Intent: {a['intent'] or 'None'}")
                print(f"    Scope: {', '.join(a['scope']) or 'None'}")
        
        if status['locks']:
            print("\nActive Locks:")
            for l in status['locks']:
                print(f"  {l['resource']} - {l['lock_type']} by {l['agent_id'][:12]}")
        
        print("=" * 60 + "\n")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_coordinator() -> AgentCoordinator:
    """Get coordinator singleton"""
    return AgentCoordinator()


def declare_intent(intent: str, scope: List[str] = None, areas: List[str] = None):
    """Quick function to declare intent"""
    coord = get_coordinator()
    coord.update_manifest(
        intent=intent,
        scope=scope or [],
        areas=areas or [],
        status=AgentStatus.BUSY
    )


def lock_file(file_path: str, purpose: str = "") -> bool:
    """Quick function to lock a file"""
    coord = get_coordinator()
    lock = coord.lock_resource(file_path, purpose=purpose)
    return lock is not None


def check_conflicts(scope: List[str], areas: List[str]) -> List[Dict]:
    """Quick function to check conflicts"""
    coord = get_coordinator()
    return coord.check_scoped_conflicts(scope, areas)


def declare_operation(
    intent: str,
    scope: List[str] = None,
    areas: List[str] = None,
    alert_type: str = "intent_declared",
    eta_minutes: int = 0,
    risk_level: str = "low",
    operations: List[str] = None
) -> Optional[Dict]:
    """
    Declare an operation that updates both manifest AND creates an operational alert.
    
    This is the unified way to tell other agents what you're doing.
    
    Args:
        intent: What you plan to do
        scope: Files/resources affected
        areas: Areas being worked on
        alert_type: Type of operational alert (from AlertType enum values)
        eta_minutes: Estimated completion time
        risk_level: low/medium/high/critical
        operations: What operations being performed
    
    Returns:
        Dict with manifest and alert info, or None if failed
    """
    try:
        from operational_alerts import AlertManager, AlertType
        
        coord = get_coordinator()
        
        alert_mgr = AlertManager()
        
        alert_type_enum = AlertType.INTENT_DECLARED
        for at in AlertType:
            if at.value == alert_type:
                alert_type_enum = at
                break
        
        manifest = coord.update_manifest(
            intent=intent,
            scope=scope or [],
            areas=areas or [],
            status=AgentStatus.BUSY,
            eta_minutes=eta_minutes
        )
        
        alert = alert_mgr.start_operation(
            alert_type=alert_type_enum,
            description=intent,
            scope=scope or [],
            operations=operations or ["working"],
            eta_minutes=eta_minutes,
            risk_level=risk_level
        )
        
        return {
            "manifest": manifest.to_dict(),
            "alert": alert.to_dict()
        }
    except Exception as e:
        print(f"declare_operation error: {e}")
        return None


def complete_operation(alert_id: str = None, scope: List[str] = None):
    """
    Complete an operation - marks alert done and updates manifest to idle.
    
    Args:
        alert_id: Specific alert to complete
        scope: If alert_id not provided, find alert by scope
    """
    try:
        from operational_alerts import AlertManager
        
        coord = get_coordinator()
        alert_mgr = AlertManager()
        
        if alert_id:
            alert_mgr.complete_operation(alert_id)
        elif scope:
            alerts = alert_mgr.get_alerts_by_scope(scope, active_only=True)
            for alert in alerts:
                if alert.agent_id == coord.agent_id:
                    alert_mgr.complete_operation(alert.alert_id)
                    break
        
        coord.update_manifest(
            intent="",
            scope=[],
            areas=[],
            status=AgentStatus.IDLE,
            progress_percent=100.0
        )
    except Exception as e:
        print(f"complete_operation error: {e}")


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("Agent Coordination System")
    print("=" * 50)
    
    coord = get_coordinator()
    
    # Declare some intent
    print("\nDeclaring intent...")
    coord.update_manifest(
        intent="Testing coordination system",
        scope=["test_file.py"],
        areas=["testing"],
        status=AgentStatus.BUSY,
        eta_minutes=5
    )
    
    # Check status
    coord.print_status()
    
    # Try to lock a resource
    print("\nLocking test resource...")
    lock = coord.lock_resource("test_resource", purpose="testing")
    print(f"Lock result: {'Success' if lock else 'Failed'}")
    
    # List locks
    print("\nActive locks:")
    for l in coord.get_all_locks():
        print(f"  {l.resource} by {l.agent_id}")
