"""
Coordinator API: Minimal signal-based logging for agents
Week 1 Foundation - Signal Logging Layer

Semantic Architecture: Signals cause effects in the system.
This module provides agents with a lightweight API for emitting signals.
Every signal causes state changes and is located_in both Redis (primary) and Files (fallback).
Every log call has <1ms overhead and contributes to 95% token efficiency.

Signal Types:
  - DECISION: Choice made (derives_from reasoning) → cached for future reference
  - LEARNING: Experiment outcome (derives_from experiment) → shared across agents
  - ACTION: Work in progress (creates event) → tracks activity
  - BLOCKER: Obstacle encountered (prevents progress) → alerts system
  - HANDOFF: Passing work (creates context transfer) → between agents
  - COMPLETION: Task finished (concludes work) → marks outcome
"""

import logging

# Persistence goes through the AgentSignalLedger (Redis Streams when up, File
# always); this module never touches redis directly.
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from core.foundation.redis_connection import DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT
from core.paths import state_root


class SignalType(Enum):
    """Types of signals agents can emit"""

    ACTION = "action"  # Task started
    DECISION = "decision"  # Key choice made
    BLOCKER = "blocker"  # Obstacle encountered
    HANDOFF = "handoff"  # Passing to another agent
    COMPLETION = "completion"  # Task finished
    LEARNING = "learning"  # Experiment outcome (new)
    INSIGHT = "insight"  # Learning extracted
    CONTEXT = "context"  # State snapshot


class SignalEmitter:
    """
    Emits signals that cause effects in the system.

    Relationship: SignalEmitter causes StateChanges

    Minimal API for agents to emit signals about their work efficiently.
    Every signal:
    - causes: system state changes and reactions
    - located_in: Redis (primary, fast) and Files (fallback, reliable)
    - created_by: the agent emitting it
    - enables: future agents to reference this work

    Signals derive_from:
    - DECISION: choice made (reasoning process)
    - LEARNING: experiment outcome (investigation)
    - ACTION: work in progress (activity)
    - BLOCKER: obstacle encountered (failure point)
    - HANDOFF: work transfer (context passing)
    - COMPLETION: task finished (conclusion)

    Usage:
        from core.signals.coordinator_api import SignalEmitter

        emitter = SignalEmitter("agent_id")
        emitter.emit_action_triggering_work("code_review", details={"file": "main.py"})
        emitter.emit_decision_referenced_by_agents("use_llama", outcome="yes", reason="verified")
        emitter.emit_blocker_preventing_progress("redis_timeout", severity="high")
        emitter.emit_handoff_to_target_agent("opencode", "implementation")
    """

    def __init__(self, agent_id: str, redis_host: str = DEFAULT_REDIS_HOST, redis_port: int = DEFAULT_REDIS_PORT):
        """
        Initialize coordinator API for an agent.

        Args:
            agent_id: Unique identifier for this agent
            redis_host: Redis server host
            redis_port: Redis server port
        """
        self.agent_id = agent_id
        self.session_id = str(uuid.uuid4())[:8]
        self.start_time = time.time()
        self.signal_count = 0

        # Signals are EVENTS, so they go in the AgentSignalLedger (Redis Streams
        # when up, File always). The ledger owns dual-write, graceful degradation,
        # AND the signal layout (stream names + retention) -- so this module just
        # appends and never branches on "if redis else file".
        from core.signals.agent_signal_ledger import AgentSignalLedger

        self.signal_ledger = AgentSignalLedger(host=redis_host, port=redis_port)
        self.agent_stream = self.signal_ledger.stream_for_agent(self.agent_id)

        # Retained for other file artifacts (briefings, etc.); the durable
        # signal record now lives in the ledger's File backend.
        self.log_dir = state_root() / "session_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s")
        self.logger = logging.getLogger(f"coordinator_api.{self.agent_id}")

        # Startup context (loaded by initialize())
        self.startup_context = None
        self.startup_briefing = None
        self.startup_decisions = []
        self.startup_learnings = []

    def _emit_signal_causing_state_change(self, signal_type: SignalType, data: dict[str, Any]) -> bool:
        """
        Internal method: emit signal that causes state changes.

        Relationship: _emit_signal_causing_state_change causes StateChange

        This signal:
        - causes: Agent reactions, context updates, dependent operations
        - derives_from: Agent action or system event
        - located_in: Redis (primary, fast), Files (fallback, reliable)
        - creates: Event in system

        Args:
            signal_type: Type of signal (DECISION, BLOCKER, etc.)
            data: Signal payload with semantic meaning

        Returns:
            bool: True if signal was successfully persisted to both backends
        """
        signal = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "signal_type": signal_type.value,
            "signal_number": self.signal_count,
            **data,
        }

        self.signal_count += 1

        # Record the signal. The ledger writes File (durable) always and Redis
        # (fast) best-effort, onto both the agent's stream and the canonical
        # firehose -- one append path regardless of Redis availability.
        try:
            self.signal_ledger.append_signal(signal)
            return True
        except Exception as e:
            logging.error("Failed to emit signal: %s", e)  # noqa: LOG015  # root-logger routing kept as-is
            return False

    def emit_action_triggering_work(self, action_name: str, details: dict[str, Any] | None = None) -> None:
        """
        Emit action signal triggering work in progress.

        Relationship: ActionSignal causes WorkProgress

        Call this when starting a task or significant work unit.

        Signal causes:
        - Progress tracking
        - Activity logging
        - Dependent operations to be triggered

        Args:
            action_name: Name of the action (e.g., "code_review", "analysis")
            details: Optional task details (file, parameters, etc.)
        """
        data = {"action_name": action_name, "details": details or {}}
        self._emit_signal_causing_state_change(SignalType.ACTION, data)

    def emit_decision_referenced_by_agents(
        self, decision_name: str, outcome: str, reason: str | None = None, reasoning: str | None = None
    ) -> None:
        """
        Emit decision signal that future agents can reference.

        Relationship: DecisionSignal derived_from Reasoning → referenced_by FutureAgents

        Key decisions are cached by the Coordinator so future agents don't re-reason.
        This saves tokens and prevents rework.

        Signal causes:
        - Decision caching
        - Future agent optimization
        - Reduced cognitive load for next team member

        Args:
            decision_name: What was decided (e.g., "use_async", "refactor_auth")
            outcome: The choice made (e.g., "yes", "no", "partial")
            reason: Brief human-readable reason
            reasoning: Detailed reasoning for Coordinator synthesis
        """
        data = {"decision_name": decision_name, "outcome": outcome, "reason": reason, "reasoning": reasoning}
        self._emit_signal_causing_state_change(SignalType.DECISION, data)

    def emit_blocker_preventing_progress(
        self,
        blocker_name: str,
        severity: str = "medium",
        description: str | None = None,
        impact: str | None = None,
    ) -> None:
        """
        Emit blocker signal indicating obstacle preventing progress.

        Relationship: BlockerSignal prevents ProgressContinuation

        Alerts the Coordinator to obstacles. Critical blockers escalate.

        Signal causes:
        - System alerts
        - Escalation if severity=high
        - Next agent awareness

        Args:
            blocker_name: What's blocking (e.g., "redis_timeout", "dependency_missing")
            severity: Importance ("high" escalates, "medium" noted, "low" informational)
            description: What happened
            impact: How it affects progress
        """
        data = {"blocker_name": blocker_name, "severity": severity, "description": description, "impact": impact}
        self._emit_signal_causing_state_change(SignalType.BLOCKER, data)

    def emit_handoff_to_target_agent(
        self,
        target_agent: str,
        task: str,
        context: dict[str, Any] | None = None,
        blockers: list[str] | None = None,
    ) -> None:
        """
        Emit handoff signal transferring work to another agent.

        Relationship: HandoffSignal creates ContextTransfer to TargetAgent

        Coordinator generates briefing for target agent, ensures context continuity.

        Signal causes:
        - Context preservation
        - Briefing generation
        - Work continuity between agents

        Args:
            target_agent: Agent taking over (e.g., "implementation_agent")
            task: What they should do (e.g., "build_auth_system")
            context: Any context they need
            blockers: Blockers the next agent should know about
        """
        data = {"target_agent": target_agent, "task": task, "context": context or {}, "blockers": blockers or []}
        self._emit_signal_causing_state_change(SignalType.HANDOFF, data)

    def emit_completion_signal_concluding_work(
        self, success: bool, output: dict[str, Any] | None = None, learned: str | None = None
    ) -> None:
        """
        Emit completion signal concluding work.

        Relationship: CompletionSignal marks WorkConclusion → enables NextPhase

        Args:
            success: Whether the task succeeded
            output: What was produced
            learned: Lessons learned for future agents
        """
        data = {
            "success": success,
            "output": output or {},
            "learned": learned,
            "total_signals": self.signal_count,
            "duration_seconds": time.time() - self.start_time,
        }
        self._emit_signal_causing_state_change(SignalType.COMPLETION, data)

    def derive_learning_from_experiment(
        self,
        experiment_name: str,
        what_tried: str,
        expected_outcome: str,
        actual_outcome: str,
        category: str,
        success: str,
        metrics: dict[str, Any] | None = None,
        root_cause: str | None = None,
        recommendation: str | None = None,
        anti_pattern: str | None = None,
        confidence: str = "medium",
    ) -> None:
        """
        Derive learning from experiment and emit for future agents.

        Relationship: Learning derives_from Experiment → referenced_by FutureAgents

        Captures structured learnings enabling collective learning and preventing rework.

        This learning:
        - derives_from: experimental investigation
        - supports: future agent decision-making
        - prevents: rework by sharing "we tried X, got Y"

        Args:
            experiment_name: Name of the experiment
            what_tried: Specific description of what was attempted
            expected_outcome: What was predicted to happen
            actual_outcome: What actually happened
            category: Category (performance|cost|quality|architecture|reliability)
            success: Outcome (yes|partial|no)
            metrics: Quantified results (optional)
            root_cause: Why it succeeded or failed (optional)
            recommendation: What to do next time (optional)
            anti_pattern: What NOT to do (optional)
            confidence: Confidence in this learning (high|medium|low)
        """
        data = {
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
        }
        self._emit_signal_causing_state_change(SignalType.LEARNING, data)

        # Directly record to learning store (don't wait for coordinator service)
        try:
            from core.learning.learning_store import get_learning_store

            store = get_learning_store()
            learning_signal = {**data, "agent_id": self.agent_id, "timestamp": datetime.utcnow().isoformat()}
            store.record_learning(learning_signal)
            self.logger.info("Learning indexed: %s (%s)", experiment_name, success)
        except Exception as e:
            self.logger.warning("Could not index learning directly: %s", e)

    def load_context_derived_from_startup_sources(self) -> dict[str, Any] | None:
        """
        Load context derived from startup sources.

        Relationship: Context derives_from StartupSources

        Returns context containing:
        - briefing: Instructions from previous handoff
        - decisions: Cached decisions to reference and reuse
        - learnings: Lessons learned to apply

        Returns:
            Dict with briefing, decisions, and learnings, or None if not loaded

        Usage:
            api = initialize("my_agent")
            context = api.load_context_derived_from_startup_sources()
            if context["briefing"]:
                print("I was handed off a task")
        """
        return self.startup_context

    def load_briefing_from_previous_handoff(self) -> dict[str, Any] | None:
        """
        Load briefing from previous handoff.

        Relationship: Briefing created_by PreviousAgent → documents NextTask

        Returns: Instructions/context from previous agent, or None if fresh start
        """
        return self.startup_briefing

    def load_decisions_referenced_in_cache(self) -> list[dict[str, Any]]:
        """
        Load decisions cached for reference.

        Relationship: Decisions referenced_by CurrentAgent → created_by PreviousAgents

        Returns: List of relevant cached decisions (empty if first run)
        """
        return self.startup_decisions or []

    def load_learnings_applicable_to_task(self) -> list[dict[str, Any]]:
        """
        Load learnings applicable to current task.

        Relationship: Learnings referenced_by CurrentAgent → derived_from PriorExperiments

        Returns: Recent learnings to apply to this task (empty if first run)
        """
        return self.startup_learnings or []

    def get_stats(self) -> dict[str, Any]:
        """Get current session statistics"""
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "signals_emitted": self.signal_count,
            "duration_seconds": time.time() - self.start_time,
            "redis_available": self.signal_ledger.redis_available,
            "agent_stream": self.agent_stream,
        }

    # ===== BOOTSTRAP API: Self-Describing System =====
    # These methods make the system discoverable without documentation

    def get_bootstrap_info(self) -> dict[str, Any]:
        """
        Returns complete self-describing system information.
        Agents use this to discover what they can do, without reading documentation.
        """
        return {
            "system": {
                "name": "Agent Coordination Framework",
                "phase": "1.5",
                "status": "Production Ready",
                "purpose": "Multi-agent learning system with cross-agent decision/learning sharing",
            },
            "signals": self._describe_signals(),
            "context": self._describe_context(),
            "methods": self._describe_methods(),
            "capabilities": self._describe_capabilities(),
            "examples": {
                "quick_start": self._get_quick_start_example(),
                "all_methods": {
                    method: self.get_method_example(method)
                    for method in ["action", "decision", "blocker", "learning", "completion", "handoff"]
                },
            },
        }

    def get_context_summary(self) -> dict[str, Any]:
        """
        Returns what context is available to this agent.
        Shows briefing, decisions, learnings, checkpoints without reading any files.
        """
        return {
            "briefing": {
                "available": self.startup_briefing is not None,
                "content": self.startup_briefing if self.startup_briefing else "None (first run or no handoff)",
                "purpose": "Instructions from previous agent",
            },
            "decisions": {
                "count": len(self.startup_decisions or []),
                "items": self.startup_decisions or [],
                "purpose": "Cached decisions to reuse (saves tokens)",
            },
            "learnings": {
                "count": len(self.startup_learnings or []),
                "items": self.startup_learnings or [],
                "purpose": "Lessons learned to apply (avoid rework)",
            },
            "checkpoint": {
                "available": getattr(self, "checkpoint", None) is not None,  # == hasattr and not None
                "purpose": "Resume point if crashed",
            },
            "summary": {
                "total_context_items": len(self.startup_decisions or []) + len(self.startup_learnings or []),
                "is_cold_start": self.startup_briefing is None and len(self.startup_decisions or []) == 0,
                "recommendation": self._get_context_recommendation(),
            },
        }

    def get_method_example(self, method_name: str) -> dict[str, Any]:
        """Returns copy-paste code example for any method"""
        examples = {
            "action": {
                "method": "action",
                "description": "Log an action you're taking",
                "code": """api.action(
    action_name="code_review",
    details={"files": 5, "issues_found": 2}
)""",
                "parameters": {
                    "action_name": "str - Name of the action",
                    "details": "dict - Additional details (optional)",
                },
            },
            "decision": {
                "method": "decision",
                "description": "Log a decision (cached for next agent to reuse)",
                "code": """api.decision(
    name="use_async",
    outcome="yes",
    reason="Performance test showed 35% improvement"
)""",
                "parameters": {
                    "name": "str - Decision identifier",
                    "outcome": "str - yes|no|partial",
                    "reason": "str - Why this choice",
                },
            },
            "learning": {
                "method": "learning",
                "description": "Log a learning from an experiment (for next agent)",
                "code": """api.learning(
    experiment_name="async_performance",
    what_tried="Async processing",
    expected_outcome="30% faster",
    actual_outcome="35% faster",
    category="performance",
    success="yes",
    recommendation="Use async for I/O operations"
)""",
                "parameters": {
                    "experiment_name": "str - Name of experiment",
                    "what_tried": "str - The approach tested",
                    "expected_outcome": "str - Prediction",
                    "actual_outcome": "str - Result",
                    "category": "str - performance|quality|cost|reliability",
                    "success": "str - yes|partial|no",
                    "recommendation": "str - What next agent should do",
                },
            },
            "blocker": {
                "method": "blocker",
                "description": "Log an obstacle you hit",
                "code": """api.blocker(
    blocker_name="redis_timeout",
    severity="high",
    description="Redis not responding",
    impact="Cannot persist decisions"
)""",
                "parameters": {
                    "blocker_name": "str - Name of blocker",
                    "severity": "str - high|medium|low",
                    "description": "str - What's blocked",
                    "impact": "str - How it affects work",
                },
            },
            "completion": {
                "method": "completion",
                "description": "Log task completion",
                "code": """api.completion(
    success=True,
    output={"files_analyzed": 42, "issues_found": 3},
    learned="Async patterns improve performance"
)""",
                "parameters": {
                    "success": "bool - Did task succeed",
                    "output": "dict - Results",
                    "learned": "str - Key learning from this work",
                },
            },
            "handoff": {
                "method": "request_handoff",
                "description": "Pass work to another agent",
                "code": """api.request_handoff(
    target_agent="implementation_agent",
    task="Implement async file processor",
    context={"decisions": [...], "design": "..."},
    blockers=[]
)""",
                "parameters": {
                    "target_agent": "str - Agent to take over",
                    "task": "str - What they should do",
                    "context": "dict - Context for next agent",
                    "blockers": "list - Any blockers to know about",
                },
            },
        }
        return examples.get(method_name, {"error": f"Unknown method: {method_name}"})

    def get_next_action_suggestion(self) -> dict[str, Any]:
        """Suggests what agent should do next based on context"""
        context_size = len(self.startup_decisions or []) + len(self.startup_learnings or [])

        if self.startup_briefing:
            return {
                "situation": "You were handed off a task",
                "suggestion": "1. Read your briefing 2. Check cached decisions 3. Apply learnings 4. Start work",
                "code": "briefing = api.get_startup_briefing()",
            }
        if context_size > 0:
            return {
                "situation": f"You have {context_size} relevant decisions/learnings loaded",
                "suggestion": "1. Review decisions to reuse (save tokens) 2. Apply learnings 3. Start work",
                "code": "decisions = api.get_startup_decisions(); learnings = api.get_startup_learnings()",
            }
        return {
            "situation": "Cold start (no prior context)",
            "suggestion": "1. Do your work 2. Record decisions 3. Record learnings 4. System learns for next agent",
            "code": "api.decision(...); api.learning(...)",
        }

    # ===== Helper methods for Bootstrap API =====

    def _describe_signals(self) -> dict[str, dict[str, Any]]:
        """Describe all available signal types"""
        return {
            "DECISION": {
                "description": "Key choice made during work",
                "purpose": "Cached for next agent to reuse (saves tokens)",
                "example": "api.decision('use_async', outcome='yes', reason='...')",
            },
            "LEARNING": {
                "description": "Experiment outcome or lesson learned",
                "purpose": "Shared with next agent to improve decisions",
                "example": "api.learning(experiment_name='...' what_tried='...', actual_outcome='...')",
            },
            "ACTION": {
                "description": "Work being performed",
                "purpose": "Track progress and activity",
                "example": "api.action('code_review', details={...})",
            },
            "BLOCKER": {
                "description": "Obstacle encountered",
                "purpose": "Alert next agent to problems",
                "example": "api.blocker('redis_timeout', severity='high')",
            },
            "HANDOFF": {
                "description": "Passing work to another agent",
                "purpose": "Context transfer between agents",
                "example": "api.request_handoff('agent_name', 'task', ...)",
            },
            "COMPLETION": {
                "description": "Task finished",
                "purpose": "Mark success/failure and document outcome",
                "example": "api.completion(success=True, output={...})",
            },
        }

    def _describe_context(self) -> dict[str, dict[str, Any]]:
        """Describe what context is available"""
        return {
            "briefing": {
                "description": "Instructions from previous agent",
                "retrieval": "api.get_startup_briefing()",
                "always_available": False,
            },
            "decisions": {
                "description": "Cached decisions relevant to your task",
                "retrieval": "api.get_startup_decisions()",
                "always_available": True,
                "note": "Empty list if first run or no prior decisions",
            },
            "learnings": {
                "description": "Lessons learned by previous agents",
                "retrieval": "api.get_startup_learnings()",
                "always_available": True,
                "note": "Empty list if first run or no prior learnings",
            },
            "checkpoint": {
                "description": "Resume point if you crashed before",
                "retrieval": "state.load_checkpoint()",
                "always_available": False,
            },
        }

    def _describe_methods(self) -> dict[str, str]:
        """Describe all available API methods"""
        return {
            "action": "Log an action you're performing",
            "decision": "Log a decision (cached for next agent)",
            "learning": "Log a learning from an experiment",
            "blocker": "Log an obstacle you hit",
            "completion": "Log task completion",
            "request_handoff": "Pass work to another agent",
            "get_startup_context": "Retrieve all loaded context",
            "get_startup_briefing": "Get instructions from previous agent",
            "get_startup_decisions": "Get cached decisions to reuse",
            "get_startup_learnings": "Get lessons learned",
            "get_stats": "Get session statistics",
            "get_bootstrap_info": "Get this self-describing info",
            "get_context_summary": "See what context you have",
            "get_method_example": "Get code example for any method",
        }

    def _describe_capabilities(self) -> dict[str, str]:
        """Describe system capabilities"""
        return {
            "cross_agent_learning": "Decisions and learnings shared between agents",
            "crash_recovery": "Save/resume checkpoints to survive crashes",
            "context_persistence": "Briefing, decisions, learnings persist across agents",
            "signal_logging": "All signals logged to file and optionally Redis",
            "zero_documentation_bootstrap": "Get all info via APIs, no docs needed",
            "graceful_degradation": "Works with Redis (fast) or fallback to files",
        }

    def _get_quick_start_example(self) -> str:
        """Quick start code example"""
        return """# Initialize yourself
from agent.initializer import derive_agent_context_from_startup_sources

result = derive_agent_context_from_startup_sources("agent_id", "task")
api = result["api"]

# Check what context you have
context = api.get_context_summary()
print(f"Decisions: {context['decisions']['count']}")
print(f"Learnings: {context['learnings']['count']}")

# Get examples of any method
example = api.get_method_example("decision")
print(example["code"])

# Do your work
api.action("starting_work")
api.decision("choice_1", outcome="yes", reason="...")
api.learning(experiment_name="test", what_tried="x", actual_outcome="y", category="perf", success="yes")

# Finish
api.completion(success=True, output={...})"""

    def _get_context_recommendation(self) -> str:
        """Suggest what agent should do based on loaded context"""
        if self.startup_briefing:
            return "You have a briefing: READ IT FIRST"
        if len(self.startup_decisions or []) > 0:
            return "You have cached decisions: REVIEW AND REUSE THEM"
        if len(self.startup_learnings or []) > 0:
            return "You have learnings: APPLY THEM"
        return "Cold start: Do your work, record decisions/learnings for next agent"

    # ===== BACKWARD COMPATIBILITY: Deprecated names with wrappers =====
    # These methods are deprecated. Use semantic names instead.
    # Kept for backward compatibility with existing code.

    def action(self, action_name: str, details: dict[str, Any] | None = None) -> None:
        """Deprecated: Use emit_action_triggering_work() instead"""
        self.emit_action_triggering_work(action_name, details)

    def decision(
        self, decision_name: str, outcome: str, reason: str | None = None, reasoning: str | None = None
    ) -> None:
        """Deprecated: Use emit_decision_referenced_by_agents() instead"""
        self.emit_decision_referenced_by_agents(decision_name, outcome, reason, reasoning)

    def blocker(
        self,
        blocker_name: str,
        severity: str = "medium",
        description: str | None = None,
        impact: str | None = None,
    ) -> None:
        """Deprecated: Use emit_blocker_preventing_progress() instead"""
        self.emit_blocker_preventing_progress(blocker_name, severity, description, impact)

    def request_handoff(
        self,
        target_agent: str,
        task: str,
        context: dict[str, Any] | None = None,
        blockers: list[str] | None = None,
    ) -> None:
        """Deprecated: Use emit_handoff_to_target_agent() instead"""
        self.emit_handoff_to_target_agent(target_agent, task, context, blockers)

    def completion(self, success: bool, output: dict[str, Any] | None = None, learned: str | None = None) -> None:
        """Deprecated: Use emit_completion_signal_concluding_work() instead"""
        self.emit_completion_signal_concluding_work(success, output, learned)

    def learning(
        self,
        experiment_name: str,
        what_tried: str,
        expected_outcome: str,
        actual_outcome: str,
        category: str,
        success: str,
        metrics: dict[str, Any] | None = None,
        root_cause: str | None = None,
        recommendation: str | None = None,
        anti_pattern: str | None = None,
        confidence: str = "medium",
    ) -> None:
        """Deprecated: Use derive_learning_from_experiment() instead"""
        self.derive_learning_from_experiment(
            experiment_name,
            what_tried,
            expected_outcome,
            actual_outcome,
            category,
            success,
            metrics,
            root_cause,
            recommendation,
            anti_pattern,
            confidence,
        )

    def get_startup_context(self) -> dict[str, Any] | None:
        """Deprecated: Use load_context_derived_from_startup_sources() instead"""
        return self.load_context_derived_from_startup_sources()

    def get_startup_briefing(self) -> dict[str, Any] | None:
        """Deprecated: Use load_briefing_from_previous_handoff() instead"""
        return self.load_briefing_from_previous_handoff()

    def get_startup_decisions(self) -> list[dict[str, Any]]:
        """Deprecated: Use load_decisions_referenced_in_cache() instead"""
        return self.load_decisions_referenced_in_cache()

    def get_startup_learnings(self) -> list[dict[str, Any]]:
        """Deprecated: Use load_learnings_applicable_to_task() instead"""
        return self.load_learnings_applicable_to_task()


# Backward compatibility alias
CoordinatorAPI = SignalEmitter

# Global instance for easy access
_global_api: SignalEmitter | None = None


def initialize(
    agent_id: str,
    redis_host: str = DEFAULT_REDIS_HOST,
    redis_port: int = DEFAULT_REDIS_PORT,
    task_keyword: str | None = None,
    load_context: bool = True,
) -> SignalEmitter:
    """
    Initialize the global SignalEmitter instance.

    Semantic Relationship: SignalEmitter derived_from InitializationSources

    Automatically loads startup context (briefing, decisions, learnings) from cached sources.
    This should be called once at agent startup.

    Returns a SignalEmitter that:
    - emits signals that cause state changes
    - derives context from Redis (primary) or Files (fallback)
    - enables next agent to reference your decisions and learnings

    Args:
        agent_id: Unique identifier for this agent
        redis_host: Redis server host
        redis_port: Redis server port
        task_keyword: Optional keyword to filter relevant decisions/learnings
        load_context: Whether to auto-load briefing and learnings (default True)

    Returns:
        Initialized SignalEmitter instance with loaded context
    """
    import os as _os

    global _global_api
    api = CoordinatorAPI(agent_id, redis_host, redis_port)
    # T069 (reconciled spec): under _AISETUP_TEST_ISOLATED the fresh emitter is returned
    # WITHOUT writing the module global -- an isolated test's initialize() must never
    # become another test's get_api(). get_api()'s raise is then the correct isolation
    # semantics: no canonical emitter exists unless canonical code initialized one.
    if not _os.environ.get("_AISETUP_TEST_ISOLATED"):
        _global_api = api

    # Context loading moved to the Context pillar (System 4). coordinator_api is
    # System 1-3 and must NOT depend upward on System 4, so it no longer loads
    # context. `load_context` and `task_keyword` are kept for back-compat but are a
    # deprecated no-op: agents get context via context.aggregator.assemble_context
    # (wired through agent.initializer).
    if load_context:
        api.logger.debug(
            "initialize(load_context=True) is deprecated and a no-op; context now "
            "comes from the Context pillar (context.aggregator.assemble_context)."
        )

    return api


def get_api() -> SignalEmitter:
    """
    Get the global SignalEmitter instance.

    Relationship: get_api() locates_in GlobalScope

    Returns the initialized SignalEmitter for this session.

    Raises:
        RuntimeError: If initialize() hasn't been called yet

    Returns:
        The global SignalEmitter instance
    """
    global _global_api
    if _global_api is None:
        raise RuntimeError("SignalEmitter not initialized. Call initialize() first.")
    return _global_api


# ===== SEMANTIC CONVENIENCE FUNCTIONS (Module-level API) =====
# These use the global SignalEmitter instance for easy access


def emit_action_triggering_work(action_name: str, details: dict[str, Any] | None = None) -> None:
    """Emit action signal (convenience function using global API)"""
    get_api().emit_action_triggering_work(action_name, details)


def emit_decision_referenced_by_agents(
    decision_name: str, outcome: str, reason: str | None = None, reasoning: str | None = None
) -> None:
    """Emit decision signal (convenience function using global API)"""
    get_api().emit_decision_referenced_by_agents(decision_name, outcome, reason, reasoning)


def emit_blocker_preventing_progress(
    blocker_name: str, severity: str = "medium", description: str | None = None, impact: str | None = None
) -> None:
    """Emit blocker signal (convenience function using global API)"""
    get_api().emit_blocker_preventing_progress(blocker_name, severity, description, impact)


def emit_handoff_to_target_agent(
    target_agent: str, task: str, context: dict[str, Any] | None = None, blockers: list[str] | None = None
) -> None:
    """Emit handoff signal (convenience function using global API)"""
    get_api().emit_handoff_to_target_agent(target_agent, task, context, blockers)


def emit_completion_signal_concluding_work(
    success: bool, output: dict[str, Any] | None = None, learned: str | None = None
) -> None:
    """Emit completion signal (convenience function using global API)"""
    get_api().emit_completion_signal_concluding_work(success, output, learned)


def derive_learning_from_experiment(
    experiment_name: str,
    what_tried: str,
    expected_outcome: str,
    actual_outcome: str,
    category: str,
    success: str,
    metrics: dict[str, Any] | None = None,
    root_cause: str | None = None,
    recommendation: str | None = None,
    anti_pattern: str | None = None,
    confidence: str = "medium",
) -> None:
    """Derive and emit learning signal (convenience function using global API)"""
    get_api().derive_learning_from_experiment(
        experiment_name,
        what_tried,
        expected_outcome,
        actual_outcome,
        category,
        success,
        metrics,
        root_cause,
        recommendation,
        anti_pattern,
        confidence,
    )


# ===== BACKWARD COMPATIBILITY CONVENIENCE FUNCTIONS =====
# These are deprecated. Use semantic versions above instead.


def action(action_name: str, details: dict[str, Any] | None = None) -> None:
    """Deprecated: Use emit_action_triggering_work() instead"""
    get_api().action(action_name, details)


def decision(decision_name: str, outcome: str, reason: str | None = None, reasoning: str | None = None) -> None:
    """Deprecated: Use emit_decision_referenced_by_agents() instead"""
    get_api().decision(decision_name, outcome, reason, reasoning)


def blocker(
    blocker_name: str, severity: str = "medium", description: str | None = None, impact: str | None = None
) -> None:
    """Deprecated: Use emit_blocker_preventing_progress() instead"""
    get_api().blocker(blocker_name, severity, description, impact)


def request_handoff(
    target_agent: str, task: str, context: dict[str, Any] | None = None, blockers: list[str] | None = None
) -> None:
    """Deprecated: Use emit_handoff_to_target_agent() instead"""
    get_api().request_handoff(target_agent, task, context, blockers)


def completion(success: bool, output: dict[str, Any] | None = None, learned: str | None = None) -> None:
    """Deprecated: Use emit_completion_signal_concluding_work() instead"""
    get_api().completion(success, output, learned)


def learning(
    experiment_name: str,
    what_tried: str,
    expected_outcome: str,
    actual_outcome: str,
    category: str,
    success: str,
    metrics: dict[str, Any] | None = None,
    root_cause: str | None = None,
    recommendation: str | None = None,
    anti_pattern: str | None = None,
    confidence: str = "medium",
) -> None:
    """Deprecated: Use derive_learning_from_experiment() instead"""
    get_api().learning(
        experiment_name,
        what_tried,
        expected_outcome,
        actual_outcome,
        category,
        success,
        metrics,
        root_cause,
        recommendation,
        anti_pattern,
        confidence,
    )
