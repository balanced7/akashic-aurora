"""
Operational Alert System - Tiered Multi-Agent Coordination
========================================================
A tiered alert system for coordinating operations between agents.

TIER LEVELS:
- CRITICAL (1): Deployments, restarts, destructive operations
- HIGH (2): File writes, builds, test runs
- NORMAL (3): Status changes, coordination
- LOW (4): Informational, intent declarations

ALERT TYPES:
- FILE_WRITE_IN_PROGRESS: "I'm modifying auth.py"
- FILE_WRITE_COMPLETED: "Finished modifying auth.py"
- DEPLOY_IN_PROGRESS: "Deploying to production"
- DEPLOY_COMPLETED: "Deployment finished"
- TEST_RUNNING: "Running tests on module X"
- BUILD_IN_PROGRESS: "Building project"
- INTENT_DECLARED: "Planning to refactor auth"
- SCOPE_CLAIMED: "Claiming src/ as my work area"
- CONFLICT_DETECTED: "Another agent is working on auth.py!"
- ERROR_OCCURRED: "Error in module X"

Author: Senior Systems Architect
Version: 1.0 Operational Alerts
"""

import os
import sys
import json
import time
import uuid
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field

sys.path.insert(0, r'E:\AI-Setup')

# ============================================================================
# CONFIGURATION
# ============================================================================

COORD_DIR = r"E:\AI-Setup\blackboard_data\agent_coordination"
ALERTS_DIR = os.path.join(COORD_DIR, "alerts")
ACTIVE_ALERTS_FILE = os.path.join(ALERTS_DIR, "active_alerts.json")
ALERT_HISTORY_FILE = os.path.join(ALERTS_DIR, "alert_history.json")

os.makedirs(ALERTS_DIR, exist_ok=True)


class AlertTier(Enum):
    """Alert severity tiers - higher number = more urgent"""
    LOW = 4      # Informational
    NORMAL = 3   # Coordination
    HIGH = 2     # Ongoing operations
    CRITICAL = 1  # Destructive/urgent


class AlertType(Enum):
    """Types of operational alerts"""
    # File operations
    FILE_WRITE_IN_PROGRESS = "file_write_in_progress"
    FILE_WRITE_COMPLETED = "file_write_completed"
    FILE_READ_IN_PROGRESS = "file_read_in_progress"
    
    # Build/Deploy operations
    DEPLOY_IN_PROGRESS = "deploy_in_progress"
    DEPLOY_COMPLETED = "deploy_completed"
    DEPLOY_FAILED = "deploy_failed"
    BUILD_IN_PROGRESS = "build_in_progress"
    BUILD_COMPLETED = "build_completed"
    
    # Testing operations
    TEST_RUNNING = "test_running"
    TEST_COMPLETED = "test_completed"
    
    # Agent coordination
    AGENT_STARTING = "agent_starting"
    AGENT_COMPLETING = "agent_completing"
    AGENT_BLOCKED = "agent_blocked"
    AGENT_STOPPING = "agent_stopping"
    
    # Intent/Scope
    INTENT_DECLARED = "intent_declared"
    SCOPE_CLAIMED = "scope_claimed"
    SCOPE_RELEASED = "scope_released"
    RESOURCE_LOCKED = "resource_locked"
    RESOURCE_UNLOCKED = "resource_unlocked"
    
    # Warnings/Errors
    CONFLICT_DETECTED = "conflict_detected"
    ERROR_OCCURRED = "error_occurred"
    WARNING = "warning"
    DEPENDENCY_MISSING = "dependency_missing"
    
    # System
    REDIS_CONNECTED = "redis_connected"
    REDIS_DISCONNECTED = "redis_disconnected"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


# Map alert types to their default tiers
ALERT_TIER_MAP = {
    AlertType.FILE_WRITE_IN_PROGRESS: AlertTier.HIGH,
    AlertType.FILE_WRITE_COMPLETED: AlertTier.NORMAL,
    AlertType.FILE_READ_IN_PROGRESS: AlertTier.LOW,
    AlertType.DEPLOY_IN_PROGRESS: AlertTier.CRITICAL,
    AlertType.DEPLOY_COMPLETED: AlertTier.NORMAL,
    AlertType.DEPLOY_FAILED: AlertTier.CRITICAL,
    AlertType.BUILD_IN_PROGRESS: AlertTier.HIGH,
    AlertType.BUILD_COMPLETED: AlertTier.NORMAL,
    AlertType.TEST_RUNNING: AlertTier.HIGH,
    AlertType.TEST_COMPLETED: AlertTier.NORMAL,
    AlertType.AGENT_STARTING: AlertTier.NORMAL,
    AlertType.AGENT_COMPLETING: AlertTier.NORMAL,
    AlertType.AGENT_BLOCKED: AlertTier.HIGH,
    AlertType.AGENT_STOPPING: AlertTier.NORMAL,
    AlertType.INTENT_DECLARED: AlertTier.LOW,
    AlertType.SCOPE_CLAIMED: AlertTier.NORMAL,
    AlertType.SCOPE_RELEASED: AlertTier.LOW,
    AlertType.RESOURCE_LOCKED: AlertTier.HIGH,
    AlertType.RESOURCE_UNLOCKED: AlertTier.NORMAL,
    AlertType.CONFLICT_DETECTED: AlertTier.HIGH,
    AlertType.ERROR_OCCURRED: AlertTier.CRITICAL,
    AlertType.WARNING: AlertTier.NORMAL,
    AlertType.DEPENDENCY_MISSING: AlertTier.HIGH,
    AlertType.REDIS_CONNECTED: AlertTier.LOW,
    AlertType.REDIS_DISCONNECTED: AlertTier.HIGH,
    AlertType.SESSION_STARTED: AlertTier.LOW,
    AlertType.SESSION_ENDED: AlertTier.NORMAL,
}


@dataclass
class OperationalAlert:
    """
    An operational alert broadcast to all agents.
    
    This is the core unit of coordination - when an agent starts an operation,
    it broadcasts an alert so others know what's happening.
    """
    alert_id: str
    alert_type: AlertType
    tier: AlertTier
    
    agent_id: str
    description: str
    
    # Operational context
    scope: List[str] = field(default_factory=list)  # Files/resources affected
    operations: List[str] = field(default_factory=list)  # What we're doing
    
    # Timing
    started_at: str = ""
    eta_minutes: int = 0
    completed_at: Optional[str] = None
    
    # Risk factors
    risk_level: str = "low"  # low/medium/high/critical
    can_interrupt: bool = True
    rollback_available: bool = True
    
    # Metadata
    related_alert_id: Optional[str] = None  # For linked alerts (e.g. completed vs in_progress)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "tier": self.tier.value,
            "agent_id": self.agent_id,
            "description": self.description,
            "scope": self.scope,
            "operations": self.operations,
            "started_at": self.started_at,
            "eta_minutes": self.eta_minutes,
            "completed_at": self.completed_at,
            "risk_level": self.risk_level,
            "can_interrupt": self.can_interrupt,
            "rollback_available": self.rollback_available,
            "related_alert_id": self.related_alert_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'OperationalAlert':
        return cls(
            alert_id=d["alert_id"],
            alert_type=AlertType(d.get("alert_type", "intent_declared")),
            tier=AlertTier(d.get("tier", 3)),
            agent_id=d["agent_id"],
            description=d.get("description", ""),
            scope=d.get("scope", []),
            operations=d.get("operations", []),
            started_at=d.get("started_at", ""),
            eta_minutes=d.get("eta_minutes", 0),
            completed_at=d.get("completed_at"),
            risk_level=d.get("risk_level", "low"),
            can_interrupt=d.get("can_interrupt", True),
            rollback_available=d.get("rollback_available", True),
            related_alert_id=d.get("related_alert_id"),
            metadata=d.get("metadata", {})
        )
    
    def complete(self):
        """Mark alert as completed"""
        self.completed_at = datetime.now().isoformat()
    
    def is_active(self) -> bool:
        """Check if alert is still active"""
        return self.completed_at is None


class AlertManager:
    """
    Manages operational alerts for an agent.
    
    Usage:
        alerts = AlertManager()
        
        # Start an operation
        alert = alerts.start_operation(
            alert_type=AlertType.FILE_WRITE_IN_PROGRESS,
            description="Modifying auth.py",
            scope=["auth.py"],
            operations=["edit", "validate"],
            risk_level="medium"
        )
        
        # Complete it
        alerts.complete_operation(alert.alert_id)
        
        # Check for conflicts
        conflicts = alerts.check_scope_conflicts(["auth.py"])
    """
    
    _instance = None
    
    def __init__(self):
        self.agent_id = self._get_my_agent_id()
        self.active_alerts: Dict[str, OperationalAlert] = {}
        self._lock = threading.Lock()
        self._load_active_alerts()
    
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
    
    def _load_active_alerts(self):
        """Load active alerts from disk"""
        if os.path.exists(ACTIVE_ALERTS_FILE):
            try:
                with open(ACTIVE_ALERTS_FILE, 'r') as f:
                    data = json.load(f)
                
                with self._lock:
                    for alert_data in data.values():
                        alert = OperationalAlert.from_dict(alert_data)
                        if alert.is_active():
                            self.active_alerts[alert.alert_id] = alert
            except:
                pass
    
    def _save_active_alerts(self):
        """Save active alerts to disk"""
        with self._lock:
            data = {
                alert_id: alert.to_dict() 
                for alert_id, alert in self.active_alerts.items()
            }
        
        with open(ACTIVE_ALERTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _broadcast_alert(self, alert: OperationalAlert, action: str = "created"):
        """Broadcast alert via fast_agent_comm"""
        try:
            from fast_agent_comm import get_fast_comm
            comm = get_fast_comm()
            if comm.is_available:
                comm.set_agent_id(self.agent_id)
                comm.send_broadcast(
                    msg_type="operational_alert",
                    content={
                        "action": action,  # created, completed, cancelled
                        "alert": alert.to_dict()
                    }
                )
        except:
            pass
    
    # =========================================================================
    # ALERT CREATION
    # =========================================================================
    
    def start_operation(
        self,
        alert_type: AlertType,
        description: str,
        scope: List[str] = None,
        operations: List[str] = None,
        eta_minutes: int = 0,
        risk_level: str = "low",
        can_interrupt: bool = True,
        rollback_available: bool = True,
        metadata: Dict = None
    ) -> OperationalAlert:
        """
        Start a new operational alert.
        
        This broadcasts to all agents that an operation is in progress.
        """
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        
        alert = OperationalAlert(
            alert_id=alert_id,
            alert_type=alert_type,
            tier=ALERT_TIER_MAP.get(alert_type, AlertTier.NORMAL),
            agent_id=self.agent_id,
            description=description,
            scope=scope or [],
            operations=operations or [],
            started_at=datetime.now().isoformat(),
            eta_minutes=eta_minutes,
            risk_level=risk_level,
            can_interrupt=can_interrupt,
            rollback_available=rollback_available,
            metadata=metadata or {}
        )
        
        with self._lock:
            self.active_alerts[alert_id] = alert
        
        self._save_active_alerts()
        self._broadcast_alert(alert, "created")
        
        return alert
    
    def complete_operation(self, alert_id: str) -> bool:
        """Complete an active alert"""
        with self._lock:
            if alert_id not in self.active_alerts:
                return False
            
            alert = self.active_alerts[alert_id]
            alert.complete()
            
            # Move to history
            self._add_to_history(alert)
            
            # Remove from active
            del self.active_alerts[alert_id]
        
        self._save_active_alerts()
        self._broadcast_alert(alert, "completed")
        
        return True
    
    def cancel_operation(self, alert_id: str) -> bool:
        """Cancel an active alert without completing"""
        with self._lock:
            if alert_id not in self.active_alerts:
                return False
            
            alert = self.active_alerts[alert_id]
            alert.completed_at = datetime.now().isoformat()
            
            # Move to history
            self._add_to_history(alert)
            
            # Remove from active
            del self.active_alerts[alert_id]
        
        self._save_active_alerts()
        self._broadcast_alert(alert, "cancelled")
        
        return True
    
    # =========================================================================
    # QUICK ALERT METHODS
    # =========================================================================
    
    def file_write_start(self, file_path: str, description: str = "") -> OperationalAlert:
        """Quick alert: starting file write"""
        return self.start_operation(
            alert_type=AlertType.FILE_WRITE_IN_PROGRESS,
            description=description or f"Writing to {file_path}",
            scope=[file_path],
            operations=["write"],
            risk_level="medium"
        )
    
    def file_write_complete(self, file_path: str):
        """Complete file write alert"""
        alerts = self.get_alerts_by_scope([file_path], active_only=True)
        for alert in alerts:
            if alert.alert_type == AlertType.FILE_WRITE_IN_PROGRESS:
                self.complete_operation(alert.alert_id)
                return True
        return False
    
    def deploy_start(self, target: str, description: str = "") -> OperationalAlert:
        """Quick alert: starting deployment"""
        return self.start_operation(
            alert_type=AlertType.DEPLOY_IN_PROGRESS,
            description=description or f"Deploying to {target}",
            scope=[target],
            operations=["deploy"],
            risk_level="critical",
            can_interrupt=False,
            rollback_available=True
        )
    
    def deploy_complete(self, target: str):
        """Complete deploy alert"""
        alerts = self.get_alerts_by_scope([target], active_only=True)
        for alert in alerts:
            if alert.alert_type == AlertType.DEPLOY_IN_PROGRESS:
                self.complete_operation(alert.alert_id)
                return True
        return False
    
    def test_start(self, test_path: str, description: str = "") -> OperationalAlert:
        """Quick alert: starting tests"""
        return self.start_operation(
            alert_type=AlertType.TEST_RUNNING,
            description=description or f"Running tests: {test_path}",
            scope=[test_path],
            operations=["test"],
            risk_level="low",
            can_interrupt=True
        )
    
    def test_complete(self, test_path: str):
        """Complete test alert"""
        alerts = self.get_alerts_by_scope([test_path], active_only=True)
        for alert in alerts:
            if alert.alert_type == AlertType.TEST_RUNNING:
                self.complete_operation(alert.alert_id)
                return True
        return False
    
    def intent_declare(self, intent: str, scope: List[str] = None) -> OperationalAlert:
        """Quick alert: declaring intent"""
        return self.start_operation(
            alert_type=AlertType.INTENT_DECLARED,
            description=intent,
            scope=scope or [],
            operations=["planning"],
            risk_level="low",
            can_interrupt=True
        )
    
    def conflict_detected(self, scope: List[str], description: str) -> OperationalAlert:
        """Quick alert: conflict detected"""
        return self.start_operation(
            alert_type=AlertType.CONFLICT_DETECTED,
            description=description,
            scope=scope,
            operations=["conflict"],
            risk_level="high",
            can_interrupt=False
        )
    
    # =========================================================================
    # ALERT QUERIES
    # =========================================================================
    
    def get_active_alerts(self) -> List[OperationalAlert]:
        """Get all active alerts for this agent"""
        return list(self.active_alerts.values())
    
    def get_all_active_alerts(self) -> List[OperationalAlert]:
        """Get ALL active alerts from ALL agents (from disk)"""
        alerts = list(self.active_alerts.values())
        
        # Load from disk (other agents' alerts)
        if os.path.exists(ACTIVE_ALERTS_FILE):
            try:
                with open(ACTIVE_ALERTS_FILE, 'r') as f:
                    data = json.load(f)
                
                for alert_id, alert_data in data.items():
                    if alert_id not in self.active_alerts:
                        alert = OperationalAlert.from_dict(alert_data)
                        if alert.is_active() and alert.agent_id != self.agent_id:
                            alerts.append(alert)
            except:
                pass
        
        return sorted(alerts, key=lambda a: a.tier.value)
    
    def get_alerts_by_scope(self, scope: List[str], active_only: bool = False) -> List[OperationalAlert]:
        """Find alerts that overlap with given scope"""
        matching = []
        alerts = self.get_active_alerts() if active_only else self.get_all_active_alerts()
        
        for alert in alerts:
            for resource in scope:
                if resource in alert.scope:
                    matching.append(alert)
                    break
        
        return matching
    
    def get_alerts_by_tier(self, tier: AlertTier, active_only: bool = True) -> List[OperationalAlert]:
        """Get alerts by tier level"""
        alerts = self.get_active_alerts() if active_only else self.get_all_active_alerts()
        return [a for a in alerts if a.tier == tier]
    
    def get_critical_alerts(self, active_only: bool = True) -> List[OperationalAlert]:
        """Get CRITICAL tier alerts"""
        return self.get_alerts_by_tier(AlertTier.CRITICAL, active_only)
    
    def get_high_alerts(self, active_only: bool = True) -> List[OperationalAlert]:
        """Get HIGH tier alerts"""
        return self.get_alerts_by_tier(AlertTier.HIGH, active_only)
    
    def check_scope_conflicts(self, scope: List[str]) -> List[OperationalAlert]:
        """
        Check if any other agent has alerts for the given scope.
        
        Returns list of conflicting alerts.
        """
        conflicts = []
        all_alerts = self.get_all_active_alerts()
        
        for alert in all_alerts:
            if alert.agent_id == self.agent_id:
                continue  # Skip our own alerts
            
            # Check for scope overlap
            for resource in scope:
                if resource in alert.scope:
                    conflicts.append(alert)
                    break
        
        return conflicts
    
    def is_scope_busy(self, scope: List[str]) -> bool:
        """Check if any other agent is working on given scope"""
        return len(self.check_scope_conflicts(scope)) > 0
    
    def get_scope_occupants(self, scope: List[str]) -> List[Dict]:
        """Get info about agents working on given scope"""
        occupants = []
        for alert in self.check_scope_conflicts(scope):
            occupants.append({
                "agent_id": alert.agent_id,
                "alert_type": alert.alert_type.value,
                "description": alert.description,
                "risk_level": alert.risk_level,
                "can_interrupt": alert.can_interrupt,
                "started_at": alert.started_at
            })
        return occupants
    
    # =========================================================================
    # HISTORY
    # =========================================================================
    
    def _add_to_history(self, alert: OperationalAlert):
        """Add completed alert to history"""
        history = []
        if os.path.exists(ALERT_HISTORY_FILE):
            try:
                with open(ALERT_HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append(alert.to_dict())
        
        # Keep last 100 entries
        history = history[-100:]
        
        with open(ALERT_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
    
    def get_alert_history(self, limit: int = 20) -> List[OperationalAlert]:
        """Get recent alert history"""
        if not os.path.exists(ALERT_HISTORY_FILE):
            return []
        
        try:
            with open(ALERT_HISTORY_FILE, 'r') as f:
                history = json.load(f)
            
            return [OperationalAlert.from_dict(h) for h in history[-limit:]]
        except:
            return []
    
    # =========================================================================
    # STATUS
    # =========================================================================
    
    def get_system_status(self) -> Dict:
        """Get full alert system status"""
        all_alerts = self.get_all_active_alerts()
        
        by_tier = {
            "critical": len([a for a in all_alerts if a.tier == AlertTier.CRITICAL]),
            "high": len([a for a in all_alerts if a.tier == AlertTier.HIGH]),
            "normal": len([a for a in all_alerts if a.tier == AlertTier.NORMAL]),
            "low": len([a for a in all_alerts if a.tier == AlertTier.LOW]),
        }
        
        by_type = {}
        for alert in all_alerts:
            by_type[alert.alert_type.value] = by_type.get(alert.alert_type.value, 0) + 1
        
        my_alerts = [a for a in all_alerts if a.agent_id == self.agent_id]
        other_alerts = [a for a in all_alerts if a.agent_id != self.agent_id]
        
        return {
            "total_active": len(all_alerts),
            "my_active": len(my_alerts),
            "other_active": len(other_alerts),
            "by_tier": by_tier,
            "by_type": by_type,
            "critical_count": by_tier["critical"],
            "high_count": by_tier["high"],
            "has_critical": by_tier["critical"] > 0,
            "has_high": by_tier["high"] > 0
        }
    
    def print_status(self):
        """Print human-readable status"""
        status = self.get_system_status()
        
        print("\n" + "=" * 60)
        print("OPERATIONAL ALERTS STATUS")
        print("=" * 60)
        
        print(f"\nActive Alerts: {status['total_active']}")
        print(f"  Mine: {status['my_active']}")
        print(f"  Other agents: {status['other_active']}")
        
        print(f"\nBy Tier:")
        print(f"  CRITICAL: {status['by_tier']['critical']}")
        print(f"  HIGH: {status['by_tier']['high']}")
        print(f"  NORMAL: {status['by_tier']['normal']}")
        print(f"  LOW: {status['by_tier']['low']}")
        
        all_alerts = self.get_all_active_alerts()
        
        if all_alerts:
            print(f"\nActive Operations:")
            for alert in all_alerts:
                me = "(YOU)" if alert.agent_id == self.agent_id else ""
                print(f"  [{alert.tier.name}] {alert.alert_type.value} {me}")
                print(f"    {alert.description}")
                print(f"    Scope: {', '.join(alert.scope) or 'none'}")
                if alert.eta_minutes > 0:
                    print(f"    ETA: {alert.eta_minutes} min")
        
        print("=" * 60 + "\n")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_alert_manager() -> AlertManager:
    """Get AlertManager singleton"""
    return AlertManager()


def alert_file_write(file_path: str, description: str = ""):
    """Quick alert: file write in progress"""
    return get_alert_manager().file_write_start(file_path, description)


def alert_deploy(target: str, description: str = ""):
    """Quick alert: deploy in progress"""
    return get_alert_manager().deploy_start(target, description)


def alert_test(test_path: str, description: str = ""):
    """Quick alert: test running"""
    return get_alert_manager().test_start(test_path, description)


def check_file_conflict(file_path: str) -> List[Dict]:
    """Check if any other agent is working on a file"""
    return get_alert_manager().get_scope_occupants([file_path])


def is_file_busy(file_path: str) -> bool:
    """Check if any other agent is working on a file"""
    return get_alert_manager().is_scope_busy([file_path])


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("Operational Alert System Test")
    print("=" * 50)
    
    alerts = AlertManager()
    
    print("\nStarting operations...")
    
    # Start a file write
    alert1 = alerts.file_write_start("auth.py", "Refactoring authentication")
    print(f"Started: {alert1.alert_id}")
    
    # Start a deploy
    alert2 = alerts.deploy_start("production", "Deploying v2.0")
    print(f"Started: {alert2.alert_id}")
    
    # Check status
    alerts.print_status()
    
    # Check conflicts
    print("\nChecking conflicts for auth.py...")
    conflicts = alerts.check_scope_conflicts(["auth.py"])
    print(f"Conflicts: {len(conflicts)}")
    for c in conflicts:
        print(f"  {c.agent_id}: {c.description}")
    
    # Complete file write
    print("\nCompleting file write...")
    alerts.complete_operation(alert1.alert_id)
    
    alerts.print_status()
