"""
State Management System

Semantic Relationship: State enables crash recovery for agents

Includes:
- session_state.py: Agent session and checkpoint management
  - Functions: save_checkpoint_for_recovery()
  - Functions: load_checkpoint_from_storage()

- session_recovery.py: session-HISTORY diagnostic (read past logs when Redis is down)

Note: Redis<->File divergence healing now lives on HybridStore (check_drift/reconcile) and is wired
into cold-start boot (agent_cli cmd_boot); the old StoreReconciler wrapper + RedisSyncCoordinator
facade were retired 2026-07-07.

Purpose: Agent state survives crashes through persistent checkpoints.
"""

from .session_state import SessionState
from .session_recovery import SessionRecovery

__all__ = [
    "SessionState",
    "SessionRecovery",
]
