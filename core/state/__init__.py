"""
State Management System

Semantic Relationship: State enables crash recovery for agents

Includes:
- session_state.py: Agent session and checkpoint management
  - Functions: save_checkpoint_for_recovery()
  - Functions: load_checkpoint_from_storage()

- session_recovery.py: Resume from crash
  - Functions: resume_from_checkpoint_preventing_loss()

- sync_reconciler.py: Keep Redis and file in sync (heal divergence)
  - Functions: sync_state_reconciling_divergence()
  - Class: StoreReconciler (operates on a HybridStore)

- redis_sync_coordinator.py: DEPRECATED facade over AgentSignalLedger/LearningStore/Store
  - Retained for back-compat; new code should use the primitives directly.

Purpose: Agent state survives crashes through persistent checkpoints.
"""

from .session_state import SessionState
from .session_recovery import SessionRecovery
from .sync_reconciler import (
    StoreReconciler,
    create_store_reconciler,
    sync_state_reconciling_divergence,
)
from .redis_sync_coordinator import RedisSyncCoordinator

__all__ = [
    "SessionState",
    "SessionRecovery",
    "StoreReconciler",
    "create_store_reconciler",
    "sync_state_reconciling_divergence",
    "RedisSyncCoordinator",
]
