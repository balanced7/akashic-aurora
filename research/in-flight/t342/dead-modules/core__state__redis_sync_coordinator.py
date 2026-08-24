"""
Redis Sync Coordinator: DEPRECATED facade over the Pillar 0 primitives

Semantic Relationship: RedisSyncCoordinator delegates_to AgentSignalLedger, LearningStore, Store

WHAT HAPPENED TO THE 900 LINES
------------------------------
This module used to hand-roll dual-write, hash verification, learning indexing,
and instance heartbeats -- all of which now live in dedicated, tested places:

- signals (events)      -> core.signals.agent_signal_ledger (AgentSignalLedger)
- learnings (state)     -> core.learning.learning_store (LearningStore on a Store)
- status/instances      -> core.foundation.store   (HybridStore dual-writes)
- Redis<->File healing  -> core.state.sync_reconciler (StoreReconciler)

So this class collapsed into a thin delegating facade. It exists only so
existing imports keep working; new code should use the primitives directly.
The genuine surviving responsibility -- reconciling Redis with File -- is now
`StoreReconciler` / `sync_state_reconciling_divergence()`.

Usage (preferred):
    from core.state.sync_reconciler import sync_state_reconciling_divergence
    report = sync_state_reconciling_divergence()
"""

import json
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import os

from core.signals.agent_signal_ledger import AgentSignalLedger
from core.signals.coordinator_api import SignalType  # single source of truth; re-exported for back-compat
from core.foundation.store import create_store
from core.foundation.redis_connection import DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT
from core.learning.learning_store import get_learning_store_instance
from core.state.sync_reconciler import StoreReconciler

logger = logging.getLogger("redis_sync_coordinator")


class SyncStatus(Enum):
    """Sync status for signals and learnings (retained for back-compat)."""
    SYNCED = "synced"
    OUT_OF_SYNC = "out_of_sync"
    REDIS_ONLY = "redis_only"
    FILE_ONLY = "file_only"
    NOT_FOUND = "not_found"


class RedisSyncCoordinator:
    """
    DEPRECATED facade. Delegates to AgentSignalLedger + LearningStore + Store + StoreReconciler.

    Semantic Relationship: RedisSyncCoordinator delegates_to Pillar0Primitives

    Kept so `from core.state import RedisSyncCoordinator` and existing method
    calls keep working. Prefer the underlying primitives in new code.
    """

    def __init__(self, agent_id: str, fallback_dir: str = "E:\\AI-Setup\\session_logs",
                 redis_host: str = DEFAULT_REDIS_HOST, redis_port: int = DEFAULT_REDIS_PORT):
        self.agent_id = agent_id
        self.instance_id = f"instance-{agent_id}-{int(time.time() * 1000)}"
        self.session_id = str(uuid.uuid4())[:8]
        self.signal_count = 0

        # The primitives this facade delegates to (all dual-write + degrade).
        self.signal_ledger = AgentSignalLedger(host=redis_host, port=redis_port)
        self.store = create_store(prefer_redis=True, host=redis_host, port=redis_port)
        self.learning = get_learning_store_instance(store=self.store)
        self.reconciler = StoreReconciler(self.store)

        # Retained attributes some callers/tests still reference.
        base = Path(fallback_dir)
        self.signal_log = base / "ledger" / "agent_events.jsonl"  # durable signal record
        self.learning_log = base / "learnings.jsonl"              # legacy learnings file

    @property
    def redis_available(self) -> bool:
        return getattr(self.store, "redis_available", False)

    # ----- signals (-> AgentSignalLedger) -----
    def emit_signal_located_in_redis_and_files(self, signal_type: SignalType,
                                               data: Dict[str, Any],
                                               session_id: Optional[str] = None) -> bool:
        """Record a signal in the AgentSignalLedger (Redis Streams + File)."""
        self.signal_count += 1
        signal = {
            "signal_id": f"signal-{self.agent_id}-{self.signal_count}",
            "signal_type": signal_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": self.agent_id,
            "instance_id": self.instance_id,
            "session_id": session_id or self.session_id,
            "signal_number": self.signal_count,
            **data,
        }
        try:
            self.signal_ledger.append_signal(signal)
            return True
        except Exception as e:
            logger.error(f"Signal emit failed: {e}")
            return False

    def emit_signal(self, signal_type: SignalType, data: Dict[str, Any],
                    session_id: Optional[str] = None) -> bool:
        """Deprecated: Use emit_signal_located_in_redis_and_files() instead"""
        return self.emit_signal_located_in_redis_and_files(signal_type, data, session_id)

    # ----- learnings (-> LearningStore) -----
    def derive_and_record_learning(self, experiment_name: str, what_tried: str,
                                   expected_outcome: str, actual_outcome: str,
                                   category: str, success: str,
                                   metrics: Optional[Dict[str, Any]] = None,
                                   root_cause: Optional[str] = None,
                                   recommendation: Optional[str] = None,
                                   anti_pattern: Optional[str] = None,
                                   confidence: str = "medium") -> bool:
        """Record a learning through the LearningStore (single indexing path)."""
        return self.learning.persist_learning_derived_from_experiment({
            "experiment_name": experiment_name,
            "what_tried": what_tried,
            "expected_outcome": expected_outcome,
            "actual_outcome": actual_outcome,
            "category": category,
            "success": success,
            "metrics": metrics or {},
            "root_cause": root_cause,
            "recommendation": recommendation,
            "anti_pattern": anti_pattern,
            "confidence": confidence,
            "agent_id": self.agent_id,
        })

    def record_learning(self, experiment_name: str, what_tried: str, expected_outcome: str,
                        actual_outcome: str, category: str, success: str,
                        metrics: Optional[Dict[str, Any]] = None, root_cause: Optional[str] = None,
                        recommendation: Optional[str] = None, anti_pattern: Optional[str] = None,
                        confidence: str = "medium") -> bool:
        """Deprecated: Use derive_and_record_learning() instead"""
        return self.derive_and_record_learning(
            experiment_name, what_tried, expected_outcome, actual_outcome,
            category, success, metrics, root_cause, recommendation, anti_pattern, confidence)

    # ----- instance status (-> Store) -----
    def publish_instance_status_for_heartbeat(self, status: Dict[str, Any]) -> bool:
        """Publish a heartbeat status as expiring state in the Store (5 min TTL)."""
        instance_status = {
            "instance_id": self.instance_id,
            "agent_id": self.agent_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "session_id": self.session_id,
        }
        try:
            self.store.setex(f"instance:status:{self.instance_id}", 300, json.dumps(instance_status))
            self.store.sadd("active_instances", self.instance_id)
            self.store.expire("active_instances", 300)
            return True
        except Exception as e:
            logger.error(f"Status publish failed: {e}")
            return False

    def publish_status(self, status: Dict[str, Any]) -> bool:
        """Deprecated: Use publish_instance_status_for_heartbeat() instead"""
        return self.publish_instance_status_for_heartbeat(status)

    def load_active_instances_from_registry(self) -> Dict[str, Any]:
        """Load currently active instances from the Store registry."""
        try:
            instances = {}
            for inst_id in self.store.smembers("active_instances"):
                data = self.store.get(f"instance:status:{inst_id}")
                if data:
                    instances[inst_id] = json.loads(data)
            return instances
        except Exception as e:
            logger.warning(f"Could not fetch active instances: {e}")
            return {}

    def get_active_instances(self) -> Dict[str, Any]:
        """Deprecated: Use load_active_instances_from_registry() instead"""
        return self.load_active_instances_from_registry()

    # ----- reconciliation (-> StoreReconciler) -----
    def verify_all_signals_and_learnings_synced(self) -> Dict[str, Any]:
        """Report Redis<->File divergence via the reconciler."""
        drift = self.reconciler.check_divergence()
        if not drift.get("applicable") or not drift.get("redis_available"):
            return {"timestamp": datetime.utcnow().isoformat(), "health": "unknown",
                    "in_sync": False, "detail": drift}
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "health": "green" if drift["in_sync"] else "yellow",
            "in_sync": drift["in_sync"],
            "missing_in_redis": len(drift["missing_in_redis"]),
            "missing_in_file": len(drift["missing_in_file"]),
        }

    def verify_all_synced(self) -> Dict[str, Any]:
        """Deprecated: Use verify_all_signals_and_learnings_synced() instead"""
        return self.verify_all_signals_and_learnings_synced()

    def resync_all_out_of_sync_items(self) -> Dict[str, Any]:
        """Heal divergence by backfilling Redis from File."""
        return self.reconciler.reconcile_divergence()

    def resync_all(self) -> Dict[str, Any]:
        """Deprecated: Use resync_all_out_of_sync_items() instead"""
        return self.resync_all_out_of_sync_items()

    # ----- health & stats -----
    def check_system_health_and_readiness(self) -> Dict[str, Any]:
        """Report availability + sync status across the delegated primitives."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "instance_id": self.instance_id,
            "redis_available": self.redis_available,
            "learnings_in_store": len(self.learning.load_all_learnings_from_store()),
            "sync_status": self.verify_all_signals_and_learnings_synced(),
        }

    def health_check(self) -> Dict[str, Any]:
        """Deprecated: Use check_system_health_and_readiness() instead"""
        return self.check_system_health_and_readiness()

    def get_coordinator_stats(self) -> Dict[str, Any]:
        """Operational stats for this facade instance."""
        return {
            "instance_id": self.instance_id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "signals_emitted": self.signal_count,
            "redis_available": self.redis_available,
            "signal_log": str(self.signal_log),
            "learning_log": str(self.learning_log),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Deprecated: Use get_coordinator_stats() instead"""
        return self.get_coordinator_stats()


# Global instance
_global_coordinator: Optional[RedisSyncCoordinator] = None


def initialize_redis_sync_coordinator(agent_id: str,
                                      fallback_dir: str = "E:\\AI-Setup\\session_logs") -> RedisSyncCoordinator:
    """
    Initialize the global Redis sync coordinator facade.

    Semantic Relationship: Coordinator created_by Initialization
    """
    global _global_coordinator
    _global_coordinator = RedisSyncCoordinator(agent_id, fallback_dir)
    return _global_coordinator


def initialize(agent_id: str, fallback_dir: str = "E:\\AI-Setup\\session_logs") -> RedisSyncCoordinator:
    """Deprecated: Use initialize_redis_sync_coordinator() instead"""
    return initialize_redis_sync_coordinator(agent_id, fallback_dir)


def get_redis_sync_coordinator() -> RedisSyncCoordinator:
    """
    Get the global Redis sync coordinator facade.

    Semantic Relationship: CoordinatorReference references_to GlobalCoordinator
    """
    global _global_coordinator
    if _global_coordinator is None:
        raise RuntimeError("Coordinator not initialized. Call initialize_redis_sync_coordinator() first.")
    return _global_coordinator


def get_coordinator() -> RedisSyncCoordinator:
    """Deprecated: Use get_redis_sync_coordinator() instead"""
    return get_redis_sync_coordinator()
