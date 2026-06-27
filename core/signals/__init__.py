"""
Signals & Events System

Semantic Relationship: Signals enable communication between agents

Includes:
- coordinator_api.py: Main API - emit signals, load context
  - Functions: emit_signal_causing_state_change()
  - Functions: derive_context_from_startup_sources()

- coordinator_service.py: Process signals and route actions
  - Functions: process_signal_causing_effect()

Signal Types:
- DECISION: Agent made a choice (cacheable for reuse)
- BLOCKER: Agent hit obstacle
- LEARNING: Agent discovered insight
- HANDOFF: Agent → next agent briefing
- COMPLETION: Agent finished task
"""

from .agent_signal_ledger import AgentSignalLedger
from .coordinator_api import initialize, SignalEmitter
from .coordinator_service import CoordinatorService

__all__ = ["AgentSignalLedger", "initialize", "SignalEmitter", "CoordinatorService"]
