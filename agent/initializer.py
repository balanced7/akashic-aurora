"""
Agent Initialization Module: Derive context from startup sources

Semantic Relationship: AgentInitializer derives_from StartupSources

One-stop initialization for any agent to load full startup context.

Usage:
    from agent.initializer import derive_agent_context_from_startup_sources

    result = derive_agent_context_from_startup_sources(
        agent_id="my_agent",
        task_keyword="implementation"
    )

    api = result["api"]
    context = result["context"]
    state = result["state"]

This module handles:
- SignalEmitter initialization (derives from coordinator_api)
- Startup context loading (briefing, decisions, learnings from cache)
- Session state recovery (from checkpoint if available)
- Startup diagnostics (verification and health check)
- Graceful error handling and degradation
"""

import sys
import time
import logging
from typing import Dict, Any, Optional

from core.foundation.redis_connection import DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[AGENT_INIT] %(asctime)s - %(message)s'
)
logger = logging.getLogger("agent_init")


def derive_agent_context_from_startup_sources(
    agent_id: str,
    task_keyword: Optional[str] = None,
    redis_host: str = DEFAULT_REDIS_HOST,
    redis_port: int = DEFAULT_REDIS_PORT,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Derive agent context from startup sources (Redis primary, Files fallback).

    Semantic Relationship: Context derives_from StartupSources → enables AgentWork

    This is the PRIMARY initialization path for all agents in the system.
    Handles everything needed to prepare an agent with full startup context.

    Context derives from:
    - Briefing: Instructions from previous agent (if handed off)
    - Decisions: Cached choices for reuse (avoid rethinking)
    - Learnings: Lessons learned by prior agents (apply insights)
    - Checkpoint: Resume point if agent crashed (recovery)

    Args:
        agent_id: Unique identifier for this agent
        task_keyword: Optional keyword to filter relevant decisions/learnings
        redis_host: Redis server host (default: localhost)
        redis_port: Redis server port (default: 6379)
        verbose: Whether to print diagnostic report (default: True)

    Returns:
        Dictionary containing:
        {
            "api": SignalEmitter instance (emits signals causing effects)
            "state": SessionState instance (tracks and recovers from checkpoints)
            "context": Full startup context (briefing, decisions, learnings)
            "diagnostics": StartupDiagnostics report (health check)
            "status": "success" or "partial" or "failed"
            "message": Status message
        }

    Example:
        result = derive_agent_context_from_startup_sources("my_agent", "implementation")

        if result["status"] == "success":
            api = result["api"]
            api.emit_decision_referenced_by_agents("choice", outcome="yes", reason="...")
            api.derive_learning_from_experiment("exp", "tried x", "expected y", "got z", ...)
        else:
            print(f"Initialization warning: {result['message']}")
    """

    if verbose:
        print(f"\n{'='*70}")
        print(f"AGENT INITIALIZATION: {agent_id}")
        print(f"{'='*70}\n")

    start_time = time.time()
    status = "success"
    message = "Initialization complete"

    try:
        # Import required modules. agent/ is the top (application) layer, so it may
        # import the Context pillar (System 4) — lower layers never import upward.
        from core.signals.coordinator_api import initialize
        from core.state.session_checkpoint import SessionState
        from infrastructure.health_check import create_startup_diagnostics
        from context.aggregator import assemble_context

        logger.info(f"Initializing agent: {agent_id}")

        # Create diagnostics tracker
        diag = create_startup_diagnostics(agent_id)

        # SignalEmitter for EMITTING signals. Context now comes from the Context
        # pillar (below), so we skip coordinator_api's old load path -> no duplication.
        api = initialize(agent_id, redis_host=redis_host, redis_port=redis_port,
                         load_context=False)

        # Session state for crash recovery
        logger.info("Checking for checkpoint...")
        state = SessionState(agent_id)
        checkpoint_exists = state.has_checkpoint()

        # THE WIRING: assemble the agent's starting context through the Context
        # pillar (System 4) — ranked, budget-fitted, every entry traceable to source.
        logger.info("Assembling startup context (Context pillar)...")
        context = assemble_context(task_keyword or "", agent=agent_id)

        # Expose it on the api too, so the back-compat getters return the new context.
        sections = context.get("sections", {})
        api.startup_context = context
        api.startup_briefing = sections.get("briefing")
        api.startup_decisions = sections.get("decisions", [])
        api.startup_learnings = sections.get("learnings", [])

        if verbose:
            print("STARTUP CONTEXT ASSEMBLED (Context pillar / System 4):")
            print(f"  coverage: {context.get('coverage')}")
            print(f"  ~tokens: {context.get('approx_tokens')}/{context.get('token_budget')} "
                  f"(within budget: {context.get('within_budget')})")
            print(f"  decisions: {len(sections.get('decisions', []))}  "
                  f"learnings: {len(sections.get('learnings', []))}  "
                  f"blockers: {len(sections.get('blockers', []))}  "
                  f"briefing: {sections.get('briefing') is not None}")
            print(f"  checkpoint available: {checkpoint_exists}")

            if checkpoint_exists:
                checkpoint = state.load_checkpoint()
                print(f"\n  RECOVERY INFO:")
                print(f"    Task: {checkpoint.get('task')}")
                print(f"    Progress: {checkpoint.get('progress')}%")
                print(f"    Blockers: {checkpoint.get('blockers', [])}")

            print()
            diag.print_report()

        elapsed = (time.time() - start_time) * 1000
        logger.info(f"Initialization complete in {elapsed:.1f}ms")

        return {
            "api": api,
            "state": state,
            "context": context,
            "diagnostics": diag,
            "status": status,
            "message": message,
            "initialization_time_ms": elapsed,
        }

    except ImportError as e:
        status = "failed"
        message = f"Import error: {e}"
        logger.error(message)

        return {
            "api": None,
            "state": None,
            "context": None,
            "diagnostics": None,
            "status": status,
            "message": message,
        }

    except Exception as e:
        status = "partial"
        message = f"Initialization error: {e}"
        logger.error(message)

        return {
            "api": None,
            "state": None,
            "context": None,
            "diagnostics": None,
            "status": status,
            "message": message,
        }


def initialize_agent_with_minimal_output(agent_id: str, task_keyword: str = None):
    """
    Initialize agent quickly without verbose output.

    Semantic Relationship: Initialize with_minimal_output

    Returns: tuple of (api, state, context) for quick setup
    """
    result = derive_agent_context_from_startup_sources(
        agent_id,
        task_keyword=task_keyword,
        verbose=False
    )

    if result["status"] == "success":
        return result["api"], result["state"], result["context"]
    else:
        raise RuntimeError(f"Initialization failed: {result['message']}")


def initialize_agent_with_full_diagnostics(agent_id: str, task_keyword: str = None):
    """
    Initialize agent with full error handling, logging, and diagnostics.

    Semantic Relationship: Initialize with_full_diagnostics → enables Debugging

    Returns: result dict with complete status information and diagnostics
    """
    return derive_agent_context_from_startup_sources(
        agent_id,
        task_keyword=task_keyword,
        verbose=True
    )


# ===== BACKWARD COMPATIBILITY ALIASES =====
# These are deprecated. Use semantic names instead.

def initialize_and_load_context(
    agent_id: str,
    task_keyword: Optional[str] = None,
    redis_host: str = DEFAULT_REDIS_HOST,
    redis_port: int = DEFAULT_REDIS_PORT,
    verbose: bool = True
) -> Dict[str, Any]:
    """Deprecated: Use derive_agent_context_from_startup_sources() instead"""
    return derive_agent_context_from_startup_sources(
        agent_id, task_keyword, redis_host, redis_port, verbose
    )


def quick_initialize(agent_id: str, task_keyword: str = None):
    """Deprecated: Use initialize_agent_with_minimal_output() instead"""
    return initialize_agent_with_minimal_output(agent_id, task_keyword)


def robust_initialize(agent_id: str, task_keyword: str = None):
    """Deprecated: Use initialize_agent_with_full_diagnostics() instead"""
    return initialize_agent_with_full_diagnostics(agent_id, task_keyword)


# CLI support - allows direct invocation
if __name__ == "__main__":
    """
    Command-line usage:
        python agent_init.py <agent_id> [task_keyword]

    Example:
        python agent_init.py my_agent implementation
    """

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python agent_init.py <agent_id> [task_keyword]")
        print("\nExample:")
        print("  python agent_init.py opencode_instance code_analysis")
        sys.exit(1)

    agent_id = sys.argv[1]
    task_keyword = sys.argv[2] if len(sys.argv) > 2 else None

    # Initialize with semantic function
    result = derive_agent_context_from_startup_sources(agent_id, task_keyword, verbose=True)

    # Report status
    if result["status"] == "success":
        print(f"\n[SUCCESS] Agent '{agent_id}' initialized")
        print(f"Startup time: {result['initialization_time_ms']:.1f}ms")
        sys.exit(0)
    else:
        print(f"\n[{result['status'].upper()}] {result['message']}")
        sys.exit(1)
