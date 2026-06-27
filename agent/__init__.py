"""
Agent Orchestration System (SYSTEM 5)

Semantic Relationship: Agent orchestration enables multi-agent coordination

Purpose: One-call bootstrap for any agent type.

Components:
- initializer.py: derive_agent_context_from_startup_sources()
  - Main entry point for any agent to load full startup context
  - Returns: dict with api, state, context, diagnostics, status

- detector.py: detect_agent_type() [not built yet]
- supervisor.py: manage_agent_lifecycle() [not built yet]
- briefing_generator.py: generate_briefing_for_agent() [not built yet]

All functions use semantic naming with relationship types.
"""

from .initializer import (
    derive_agent_context_from_startup_sources,
    initialize_agent_with_minimal_output,
    initialize_agent_with_full_diagnostics,
    initialize_and_load_context,  # Backward-compat alias
)

__all__ = [
    "derive_agent_context_from_startup_sources",
    "initialize_agent_with_minimal_output",
    "initialize_agent_with_full_diagnostics",
    "initialize_and_load_context",
]
