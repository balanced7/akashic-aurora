"""
Coordinator Service: Background monitoring and decision synthesis
Week 1 Foundation - Coordinator Agent Layer

Semantic Relationship: CoordinatorService monitors AgentSignals, causing DecisionCaching and BriefingGeneration

This service runs continuously in the background (<200MB, <5% CPU) and:
1. Monitors agent signals from Redis streams
2. Synthesizes key decisions for reuse
3. Generates briefings for handoffs
4. Escalates blockers when needed
5. Maintains project state and manifests

The Coordinator is the key to achieving 95% token efficiency by preventing
agents from re-reasoning about already-made decisions.

Module Overview:
- DecisionCache: Caches decisions to prevent re-reasoning (saves 30-40% tokens)
- BlockerMonitor: Tracks and escalates critical blockers
- CoordinatorService: Main service that monitors signals and coordinates agents
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import os
from collections import defaultdict
import threading

# Persistence goes through the AgentSignalLedger + Store; this module never
# touches redis directly.
from core.foundation.redis_connection import DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT

# Import learning store for handling LEARNING signals
try:
    from core.learning.learning_store import get_learning_store
    LEARNING_STORE_AVAILABLE = True
except ImportError:
    LEARNING_STORE_AVAILABLE = False


class DecisionCache:
    """
    In-memory cache of decisions made by agents.

    Semantic Relationship: DecisionCache prevents_agents_from reusing decisions

    This is the core of the coordinator - it prevents agents from
    re-reasoning about already-made decisions, saving 30-40% of tokens.
    """

    def __init__(self, max_decisions: int = 1000):
        self.decisions: Dict[str, Dict[str, Any]] = {}
        self.max_decisions = max_decisions
        self.decision_timestamps: Dict[str, float] = {}

    def cache_decision_for_reuse(self, decision_name: str, outcome: str, reasoning: Optional[str], context: Optional[Dict] = None) -> None:
        """
        Cache a decision for future reference.

        Semantic Relationship: CachedDecision enables AgentReuse (prevents re-reasoning)

        Args:
            decision_name: What was decided
            outcome: The choice made
            reasoning: Why it was chosen
            context: Context that led to this decision
        """
        # Don't cache if already cached (trust most recent)
        if decision_name not in self.decisions:
            self.decisions[decision_name] = {
                "outcome": outcome,
                "reasoning": reasoning,
                "context": context or {},
                "first_seen": datetime.utcnow().isoformat(),
                "uses": 0
            }
            self.decision_timestamps[decision_name] = time.time()

    # Backward compatibility alias
    def add_decision(self, decision_name: str, outcome: str, reasoning: Optional[str], context: Optional[Dict] = None) -> None:
        """Deprecated: Use cache_decision_for_reuse() instead"""
        return self.cache_decision_for_reuse(decision_name, outcome, reasoning, context)

    def load_cached_decision_by_name(self, decision_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a cached decision.

        Semantic Relationship: LoadedDecision derived_from CachedStore

        Args:
            decision_name: What decision to look up

        Returns:
            Decision record if found, None otherwise
        """
        if decision_name in self.decisions:
            decision = self.decisions[decision_name]
            decision["uses"] += 1
            return decision
        return None

    # Backward compatibility alias
    def get_decision(self, decision_name: str) -> Optional[Dict[str, Any]]:
        """Deprecated: Use load_cached_decision_by_name() instead"""
        return self.load_cached_decision_by_name(decision_name)

    def load_all_cached_decisions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all cached decisions.

        Semantic Relationship: AllDecisions are_version_of CacheContents

        Returns:
            Copy of all cached decisions
        """
        return self.decisions.copy()

    # Backward compatibility alias
    def get_all_decisions(self) -> Dict[str, Dict[str, Any]]:
        """Deprecated: Use load_all_cached_decisions() instead"""
        return self.load_all_cached_decisions()

    def search_cached_decisions_by_query(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find decisions matching a query (keyword search in decision name/reasoning).

        Semantic Relationship: SearchResults derived_from CachedDecisions (filtered by query)

        Args:
            query: Keyword to search for
            limit: Max decisions to return

        Returns:
            List of matching decisions, most recent first
        """
        query_lower = query.lower()
        matches = []

        for name, decision in self.decisions.items():
            if (query_lower in name.lower() or
                query_lower in decision.get('reasoning', '').lower() or
                query_lower in decision.get('outcome', '').lower()):
                matches.append({**decision, 'name': name})

        # Sort by most recently used
        matches.sort(key=lambda d: d.get('uses', 0), reverse=True)
        return matches[:limit]

    # Backward compatibility alias
    def get_relevant_decisions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Deprecated: Use search_cached_decisions_by_query() instead"""
        return self.search_cached_decisions_by_query(query, limit)

    def remove_decisions_older_than_threshold(self, max_age_hours: int = 24) -> int:
        """
        Remove decisions older than max_age_hours.

        Semantic Relationship: RemovedDecisions causes_cleanup (freeing memory)

        Args:
            max_age_hours: How old a decision can be before removal

        Returns:
            Number of decisions pruned
        """
        cutoff = time.time() - (max_age_hours * 3600)
        to_remove = [
            name for name, ts in self.decision_timestamps.items()
            if ts < cutoff
        ]
        for name in to_remove:
            del self.decisions[name]
            del self.decision_timestamps[name]
        return len(to_remove)

    # Backward compatibility alias
    def prune_old_decisions(self, max_age_hours: int = 24) -> int:
        """Deprecated: Use remove_decisions_older_than_threshold() instead"""
        return self.remove_decisions_older_than_threshold(max_age_hours)


class BlockerMonitor:
    """
    Tracks blockers across all agents and escalates critical ones.

    Semantic Relationship: BlockerMonitor tracks_blockers, escalates_critical_ones

    Blockers that persist > 5 minutes or have severity=high are escalated.
    """

    def __init__(self):
        self.active_blockers: Dict[str, Dict[str, Any]] = {}
        self.blocker_timestamps: Dict[str, float] = {}

    def record_blocker_preventing_progress(self, agent_id: str, blocker_name: str, severity: str, description: Optional[str]) -> None:
        """
        Record a new blocker.

        Semantic Relationship: RecordedBlocker prevents_progress (tracked for escalation)

        Args:
            agent_id: Which agent reported it
            blocker_name: What's blocking
            severity: "low", "medium", or "high"
            description: Details about the blocker
        """
        key = f"{agent_id}:{blocker_name}"
        self.active_blockers[key] = {
            "agent_id": agent_id,
            "blocker_name": blocker_name,
            "severity": severity,
            "description": description,
            "first_seen": datetime.utcnow().isoformat()
        }
        self.blocker_timestamps[key] = time.time()

    # Backward compatibility alias
    def add_blocker(self, agent_id: str, blocker_name: str, severity: str, description: Optional[str]) -> None:
        """Deprecated: Use record_blocker_preventing_progress() instead"""
        return self.record_blocker_preventing_progress(agent_id, blocker_name, severity, description)

    def load_critical_blockers_requiring_escalation(self) -> List[Dict[str, Any]]:
        """
        Get blockers that need immediate attention.

        Semantic Relationship: CriticalBlockers require_escalation (high severity or persistent)

        Returns:
            List of blockers that are either:
            - severity="high" (any age)
            - Any severity that's persisted >5 minutes
        """
        critical = []
        now = time.time()
        five_minutes_ago = now - 300

        for key, blocker in self.active_blockers.items():
            timestamp = self.blocker_timestamps[key]
            is_old = timestamp < five_minutes_ago
            is_critical_severity = blocker["severity"] == "high"

            if is_critical_severity or is_old:
                critical.append({
                    **blocker,
                    "age_seconds": now - timestamp,
                    "escalation_reason": "high_severity" if is_critical_severity else "persistent"
                })

        return critical

    # Backward compatibility alias
    def get_critical_blockers(self) -> List[Dict[str, Any]]:
        """Deprecated: Use load_critical_blockers_requiring_escalation() instead"""
        return self.load_critical_blockers_requiring_escalation()

    def mark_blocker_as_resolved(self, agent_id: str, blocker_name: str) -> bool:
        """
        Mark a blocker as resolved.

        Semantic Relationship: ResolvedBlocker removes_from_active_list

        Args:
            agent_id: Agent that resolved it
            blocker_name: What was resolved

        Returns:
            True if blocker was found and removed
        """
        key = f"{agent_id}:{blocker_name}"
        if key in self.active_blockers:
            del self.active_blockers[key]
            del self.blocker_timestamps[key]
            return True
        return False

    # Backward compatibility alias
    def resolve_blocker(self, agent_id: str, blocker_name: str) -> bool:
        """Deprecated: Use mark_blocker_as_resolved() instead"""
        return self.mark_blocker_as_resolved(agent_id, blocker_name)

    def load_all_active_blockers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active blockers.

        Semantic Relationship: AllBlockers are_version_of MonitorState

        Returns:
            Copy of all active blockers
        """
        return self.active_blockers.copy()

    # Backward compatibility alias
    def get_all_blockers(self) -> Dict[str, Dict[str, Any]]:
        """Deprecated: Use load_all_active_blockers() instead"""
        return self.load_all_active_blockers()


class CoordinatorService:
    """
    Background service that monitors agents and provides coordination.

    This runs continuously as a separate thread/process and manages:
    - Decision caching for reuse
    - Blocker escalation
    - Briefing generation
    - Project state tracking
    """

    def __init__(self, redis_host: str = DEFAULT_REDIS_HOST, redis_port: int = DEFAULT_REDIS_PORT, poll_interval: float = 1.0):
        """
        Initialize the Coordinator Service.

        Args:
            redis_host: Redis server host
            redis_port: Redis server port
            poll_interval: How often to check for new signals (seconds)
        """
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.poll_interval = poll_interval
        self.is_running = False

        # Core components
        self.decision_cache = DecisionCache()
        self.blocker_monitor = BlockerMonitor()

        # State tracking
        self.agent_manifest: Dict[str, Dict[str, Any]] = {}  # Who's doing what
        self.processed_signals: Set[str] = set()  # Avoid reprocessing
        self.signal_log: List[Dict[str, Any]] = []  # Recent signals for context
        self.max_signal_history = 1000

        # Setup logging
        self.log_dir = Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "coordinator_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "coordinator.log"

        logging.basicConfig(
            level=logging.INFO,
            format='[COORDINATOR] [%(asctime)s] %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("coordinator")

        # Two persistence shapes (Pillar 0), both with graceful degradation:
        #  - AgentSignalLedger : signals are EVENTS the coordinator replays.
        #  - Store             : briefings, project state, and escalations are
        #                        STATE it reads back by key.
        # Both own Redis-vs-file selection, so this service consumes and persists
        # through one code path whether or not Redis is up.
        from core.signals.agent_signal_ledger import AgentSignalLedger
        from core.foundation.store import create_store
        self.signal_ledger = AgentSignalLedger(host=redis_host, port=redis_port)
        self.store = create_store(prefer_redis=True, host=redis_host, port=redis_port)

        if self.signal_ledger.redis_available:
            self.logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        else:
            self.logger.warning("Redis unavailable; using file fallback (ledger + Store)")

    def start_coordinator_service_background(self) -> None:
        """
        Start the Coordinator service in a background thread.

        Semantic Relationship: StartedService causes_event_loop_running

        Creates a daemon thread running the coordinator event loop.
        """
        if self.is_running:
            self.logger.warning("Coordinator already running")
            return

        self.is_running = True
        self.logger.info("Coordinator service starting")

        # Run in background thread
        thread = threading.Thread(target=self._run_coordinator_event_loop, daemon=True)
        thread.start()
        self.logger.info("Coordinator thread started")

    # Backward compatibility alias
    def start(self) -> None:
        """Deprecated: Use start_coordinator_service_background() instead"""
        return self.start_coordinator_service_background()

    def stop_coordinator_service(self) -> None:
        """
        Stop the Coordinator service.

        Semantic Relationship: StoppedService causes_event_loop_stopping
        """
        self.is_running = False
        self.logger.info("Coordinator service stopping")

    # Backward compatibility alias
    def stop(self) -> None:
        """Deprecated: Use stop_coordinator_service() instead"""
        return self.stop_coordinator_service()

    def _run_coordinator_event_loop(self) -> None:
        """
        Main service loop (runs in background thread).

        Semantic Relationship: EventLoop processes_signals_from Redis, causing coordination
        """
        last_stream_id = "0"
        stats_interval = 60  # Print stats every 60 seconds
        last_stats_time = time.time()

        while self.is_running:
            try:
                # Replay new signals from the ledger (works whether Redis is up
                # or down -- it reads its File backend when Redis is absent).
                last_stream_id = self._process_signals_from_ledger(last_stream_id)

                # Every interval, do housekeeping
                now = time.time()
                if now - last_stats_time > stats_interval:
                    self.log_coordinator_statistics_snapshot()
                    self.decision_cache.remove_decisions_older_than_threshold(max_age_hours=24)
                    last_stats_time = now

                # Check for critical blockers
                critical = self.blocker_monitor.load_critical_blockers_requiring_escalation()
                if critical:
                    self.escalate_critical_blockers_to_monitoring(critical)

                # Sleep briefly to avoid busy-waiting
                time.sleep(self.poll_interval)

            except Exception as e:
                self.logger.error(f"Error in coordinator loop: {e}", exc_info=True)
                time.sleep(5)  # Back off on error

    # Backward compatibility alias
    def _run_loop(self) -> None:
        """Deprecated: Use _run_coordinator_event_loop() instead"""
        return self._run_coordinator_event_loop()

    def _process_signals_from_ledger(self, from_id: str = "0") -> str:
        """
        Replay and process new signals from the AgentSignalLedger firehose.

        Semantic Relationship: ProcessedSignals derived_from AgentSignalLedger

        Args:
            from_id: Cursor id to resume after (newest processed id).

        Returns:
            The new cursor id (last processed), so the caller can resume there.
            Reprocessing is harmless: signals are deduped by agent:signal_number.
        """
        last_id = from_id
        try:
            # Replay the canonical firehose (blocks up to 1s for new signals).
            for message_id, signal in self.signal_ledger.replay_signals(
                after_id=from_id, count=100, block_ms=1000
            ):
                last_id = message_id
                try:
                    self._handle_signal_causing_coordination(signal)
                    signal_key = f"{signal.get('agent_id')}:{signal.get('signal_number')}"
                    self.processed_signals.add(signal_key)
                except Exception as e:
                    self.logger.error(f"Error processing message {message_id}: {e}")
        except Exception as e:
            self.logger.error(f"Error reading signals: {e}")
        return last_id

    # Backward compatibility aliases
    def _process_signals_from_redis_stream(self, from_id: str = "0") -> str:
        """Deprecated: Use _process_signals_from_ledger() instead"""
        return self._process_signals_from_ledger(from_id)

    def _process_signals(self, from_id: str = "0") -> str:
        """Deprecated: Use _process_signals_from_ledger() instead"""
        return self._process_signals_from_ledger(from_id)

    def _handle_signal_causing_coordination(self, signal: Dict[str, Any]) -> None:
        """
        Process a single signal from an agent.

        Semantic Relationship: HandledSignal causes_coordination (decision caching, blocker recording, etc)

        Args:
            signal: Signal object from agent
        """
        signal_type = signal.get("signal_type")
        agent_id = signal.get("agent_id")

        # Track signal in history
        self.signal_log.append(signal)
        if len(self.signal_log) > self.max_signal_history:
            self.signal_log.pop(0)

        # Update agent manifest
        if agent_id not in self.agent_manifest:
            self.agent_manifest[agent_id] = {
                "agent_id": agent_id,
                "first_seen": datetime.utcnow().isoformat(),
                "last_signal": None,
                "signal_count": 0
            }
        self.agent_manifest[agent_id]["last_signal"] = signal.get("timestamp")
        self.agent_manifest[agent_id]["signal_count"] += 1

        # Handle different signal types
        if signal_type == "action":
            action_name = signal.get("action_name")
            self.logger.info(f"[{agent_id}] Action: {action_name}")

        elif signal_type == "decision":
            decision_name = signal.get("decision_name")
            outcome = signal.get("outcome")
            reasoning = signal.get("reasoning")
            self.decision_cache.cache_decision_for_reuse(decision_name, outcome, reasoning, signal)
            self.logger.info(f"[{agent_id}] Decision cached: {decision_name} → {outcome}")

        elif signal_type == "blocker":
            blocker_name = signal.get("blocker_name")
            severity = signal.get("severity")
            description = signal.get("description")
            self.blocker_monitor.record_blocker_preventing_progress(agent_id, blocker_name, severity, description)
            self.logger.warning(f"[{agent_id}] Blocker: {blocker_name} ({severity})")

        elif signal_type == "handoff":
            target_agent = signal.get("target_agent")
            task = signal.get("task")
            self.logger.info(f"[{agent_id}] Handoff → {target_agent}: {task}")
            # Generate briefing for target agent (see _generate_briefing)

        elif signal_type == "learning":
            # Auto-index learning in learning store
            if LEARNING_STORE_AVAILABLE:
                try:
                    learning_store = get_learning_store()
                    # Add agent_id to signal for tracking
                    learning_signal = {**signal, "agent_id": agent_id}
                    learning_store.record_learning(learning_signal)
                    experiment_name = signal.get("experiment_name", "unknown")
                    success = signal.get("success", "unknown")
                    self.logger.info(f"[{agent_id}] Learning recorded: {experiment_name} ({success})")
                except Exception as e:
                    self.logger.error(f"Error recording learning: {e}")
            else:
                self.logger.warning("Learning store not available, skipping learning indexing")

        elif signal_type == "completion":
            success = signal.get("success")
            status = "SUCCESS" if success else "FAILED"
            self.logger.info(f"[{agent_id}] Task completion: {status}")

    # Backward compatibility alias
    def _handle_signal(self, signal: Dict[str, Any]) -> None:
        """Deprecated: Use _handle_signal_causing_coordination() instead"""
        return self._handle_signal_causing_coordination(signal)

    def generate_briefing_for_agent_handoff(self, target_agent: str, handoff_signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a briefing for an agent taking over a task.

        Semantic Relationship: GeneratedBriefing prevents_context_loss (during handoffs)

        This is the key function that prevents context loss during handoffs.
        Briefing includes relevant decisions, project state, and critical blockers.

        Args:
            target_agent: Who's receiving the handoff
            handoff_signal: The handoff signal from the previous agent

        Returns:
            Briefing containing everything the next agent needs to know
        """
        source_agent = handoff_signal.get("agent_id")
        task = handoff_signal.get("task")
        source_context = handoff_signal.get("context", {})
        source_blockers = handoff_signal.get("blockers", [])

        # Compile briefing
        briefing = {
            "timestamp": datetime.utcnow().isoformat(),
            "target_agent": target_agent,
            "source_agent": source_agent,
            "task": task,
            "context": source_context,
            "blockers": source_blockers,

            # Key addition: cached decisions relevant to this task
            "relevant_decisions": self.find_decisions_relevant_to_task(task),

            # And recent project state
            "project_state": self.load_project_state_for_briefing(),

            # And agent manifest
            "agent_manifest": self.agent_manifest.copy(),

            # Critical blockers
            "critical_blockers": self.blocker_monitor.load_critical_blockers_requiring_escalation()
        }

        # Add learnings if learning store is available
        if LEARNING_STORE_AVAILABLE:
            try:
                learning_store = get_learning_store()
                briefing["relevant_learnings"] = learning_store.get_learnings(task)
                briefing["recommendations"] = learning_store.get_recommendations(task)
                briefing["anti_patterns"] = learning_store.get_anti_patterns(task)
            except Exception as e:
                self.logger.error(f"Error adding learnings to briefing: {e}")

        # Store briefing as STATE for the target agent to retrieve (1h TTL).
        try:
            self.store.setex(f"briefing:{target_agent}:latest", 3600, json.dumps(briefing))
        except Exception as e:
            self.logger.error(f"Error storing briefing: {e}")

        return briefing

    # Backward compatibility alias
    def _generate_briefing(self, target_agent: str, handoff_signal: Dict[str, Any]) -> Dict[str, Any]:
        """Deprecated: Use generate_briefing_for_agent_handoff() instead"""
        return self.generate_briefing_for_agent_handoff(target_agent, handoff_signal)

    def find_decisions_relevant_to_task(self, task: str) -> List[Dict[str, Any]]:
        """
        Find cached decisions relevant to a task.

        Semantic Relationship: RelevantDecisions derived_from CachedDecisions (filtered by task)

        Simple heuristic: decisions that share keywords with the task.
        In production, this would use semantic similarity.

        Args:
            task: Task description

        Returns:
            List of relevant decisions
        """
        task_words = set(task.lower().split())
        relevant = []

        for decision_name, decision in self.decision_cache.load_all_cached_decisions().items():
            decision_words = set(decision_name.lower().split())
            if task_words & decision_words:  # Set intersection
                relevant.append({
                    "decision_name": decision_name,
                    "outcome": decision.get("outcome"),
                    "reasoning": decision.get("reasoning")
                })

        return relevant

    # Backward compatibility alias
    def _find_relevant_decisions(self, task: str) -> List[Dict[str, Any]]:
        """Deprecated: Use find_decisions_relevant_to_task() instead"""
        return self.find_decisions_relevant_to_task(task)

    def load_project_state_for_briefing(self) -> Dict[str, Any]:
        """
        Get current project state for briefings.

        Semantic Relationship: ProjectState derived_from Redis

        Returns:
            Project state dictionary, or empty dict if unavailable
        """
        try:
            state_json = self.store.get("project:state")
            if state_json:
                return json.loads(state_json)
        except Exception as e:
            self.logger.error(f"Error reading project state: {e}")

        return {}

    # Backward compatibility alias
    def _get_project_state(self) -> Dict[str, Any]:
        """Deprecated: Use load_project_state_for_briefing() instead"""
        return self.load_project_state_for_briefing()

    def escalate_critical_blockers_to_monitoring(self, critical_blockers: List[Dict[str, Any]]) -> None:
        """
        Escalate critical blockers (log them, store in Redis, etc).

        Semantic Relationship: EscalatedBlockers recorded_in_redis (for monitoring systems)

        Args:
            critical_blockers: List of blockers needing attention
        """
        for blocker in critical_blockers:
            reason = blocker.get("escalation_reason")
            agent_id = blocker.get("agent_id")
            blocker_name = blocker.get("blocker_name")
            age = blocker.get("age_seconds", 0)

            self.logger.critical(
                f"ESCALATED BLOCKER from {agent_id}: {blocker_name} "
                f"(reason: {reason}, age: {age:.0f}s)"
            )

            # Record escalation as STATE for monitoring (keep last 100).
            try:
                self.store.lpush("blockers:escalated", json.dumps(blocker))
                self.store.ltrim("blockers:escalated", 0, 99)
            except Exception as e:
                self.logger.error(f"Error storing escalation: {e}")

    # Backward compatibility alias
    def _escalate_blockers(self, critical_blockers: List[Dict[str, Any]]) -> None:
        """Deprecated: Use escalate_critical_blockers_to_monitoring() instead"""
        return self.escalate_critical_blockers_to_monitoring(critical_blockers)

    def log_coordinator_statistics_snapshot(self) -> None:
        """
        Log coordinator statistics.

        Semantic Relationship: LoggedStats documents_coordinator_state (snapshot of activity)
        """
        agents = len(self.agent_manifest)
        decisions = len(self.decision_cache.decisions)
        blockers = len(self.blocker_monitor.active_blockers)
        critical = len(self.blocker_monitor.load_critical_blockers_requiring_escalation())

        self.logger.info(
            f"STATS: {agents} agents, {decisions} decisions cached, "
            f"{blockers} active blockers ({critical} critical)"
        )

    # Backward compatibility alias
    def _log_stats(self) -> None:
        """Deprecated: Use log_coordinator_statistics_snapshot() instead"""
        return self.log_coordinator_statistics_snapshot()

    def get_coordinator_status_snapshot(self) -> Dict[str, Any]:
        """
        Get current status of coordinator.

        Semantic Relationship: StatusSnapshot documents_coordinator_state (current moment)

        Returns:
            Dictionary with coordinator status, agent count, decision cache size, etc.
        """
        return {
            "is_running": self.is_running,
            "agents_active": len(self.agent_manifest),
            "decisions_cached": len(self.decision_cache.decisions),
            "blockers_active": len(self.blocker_monitor.active_blockers),
            "critical_blockers": len(self.blocker_monitor.load_critical_blockers_requiring_escalation()),
            "signals_processed": len(self.processed_signals),
            "redis_connected": self.signal_ledger.redis_available
        }

    # Backward compatibility alias
    def get_status(self) -> Dict[str, Any]:
        """Deprecated: Use get_coordinator_status_snapshot() instead"""
        return self.get_coordinator_status_snapshot()

    def load_briefing_for_agent_from_cache(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest briefing for an agent (if any).

        Semantic Relationship: LoadedBriefing derived_from RedisCache (or files as fallback)

        Falls back to file-based briefings if Redis unavailable.

        Args:
            agent_id: Agent to get briefing for

        Returns:
            Briefing dict if available, None otherwise
        """
        briefing = None

        # Try the Store first (Redis when up, File otherwise).
        try:
            briefing_json = self.store.get(f"briefing:{agent_id}:latest")
            if briefing_json:
                self.logger.info(f"Briefing loaded from Store for {agent_id}")
                return json.loads(briefing_json)
        except Exception as e:
            self.logger.warning(f"Error retrieving briefing from Store: {e}")

        # Fallback to a standalone briefing file written elsewhere.
        briefing = self._load_briefing_for_agent_from_file(agent_id)
        if briefing:
            self.logger.info(f"Briefing loaded from file for {agent_id}")
            return briefing

        return None

    # Backward compatibility alias
    def get_briefing(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Deprecated: Use load_briefing_for_agent_from_cache() instead"""
        return self.load_briefing_for_agent_from_cache(agent_id)

    def _load_briefing_for_agent_from_file(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve briefing from file-based storage.

        Semantic Relationship: LoadedBriefing derived_from LocalFiles (fallback source)

        Args:
            agent_id: Agent to load briefing for

        Returns:
            Briefing dict if file exists and readable, None otherwise
        """
        try:
            briefing_file = Path(os.getenv("AI_SETUP", "E:\\AI-Setup")) / "session_logs" / f"briefing_{agent_id}.json"
            if briefing_file.exists():
                with open(briefing_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Could not load briefing from file: {e}")
        return None

    # Backward compatibility alias
    def _get_briefing_from_file(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Deprecated: Use _load_briefing_for_agent_from_file() instead"""
        return self._load_briefing_for_agent_from_file(agent_id)

    def load_decisions_matching_task_keyword(self, task_keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get cached decisions relevant to a task keyword.

        Semantic Relationship: MatchingDecisions derived_from CachedDecisions (filtered by keyword)

        Args:
            task_keyword: Keyword to search for
            limit: Max decisions to return

        Returns:
            List of relevant decisions
        """
        return self.decision_cache.search_cached_decisions_by_query(task_keyword, limit)

    # Backward compatibility alias
    def get_relevant_decisions(self, task_keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Deprecated: Use load_decisions_matching_task_keyword() instead"""
        return self.load_decisions_matching_task_keyword(task_keyword, limit)

    def load_recent_learnings_from_store(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent learnings from the learning store.

        Semantic Relationship: RecentLearnings derived_from LearningStore

        Args:
            limit: Max learnings to return

        Returns:
            List of recent learnings
        """
        if not LEARNING_STORE_AVAILABLE:
            return []

        try:
            learning_store = get_learning_store()
            # Get recent learnings (could improve this to be configurable)
            return self._load_recent_learnings_impl(learning_store, limit)
        except Exception as e:
            self.logger.warning(f"Could not get recent learnings: {e}")
            return []

    # Backward compatibility alias
    def get_recent_learnings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Deprecated: Use load_recent_learnings_from_store() instead"""
        return self.load_recent_learnings_from_store(limit)

    def _load_recent_learnings_impl(self, learning_store: Any, limit: int) -> List[Dict[str, Any]]:
        """
        Implementation of getting recent learnings.

        Semantic Relationship: LoadedLearnings derived_from StorageImplementation

        Args:
            learning_store: Learning store instance
            limit: Max learnings to return

        Returns:
            List of recent learnings from store
        """
        # Try to get stats to see what's available
        try:
            stats = learning_store.get_stats()
            if stats and 'total_learnings' in stats and stats['total_learnings'] > 0:
                # Get anti-patterns and recommendations as "recent learnings"
                recent = []
                anti_patterns = learning_store.get_anti_patterns()
                for ap in anti_patterns[:limit]:
                    recent.append({
                        "type": "anti_pattern",
                        "anti_pattern": ap,
                        "recommendation": "Avoid this pattern"
                    })
                return recent[:limit]
        except Exception as e:
            self.logger.debug(f"Could not get recent learnings from store: {e}")
        return []

    # Backward compatibility alias
    def _get_recent_learnings_impl(self, learning_store: Any, limit: int) -> List[Dict[str, Any]]:
        """Deprecated: Use _load_recent_learnings_impl() instead"""
        return self._load_recent_learnings_impl(learning_store, limit)


# Global coordinator instance
_coordinator: Optional[CoordinatorService] = None


def get_coordinator_service_instance() -> CoordinatorService:
    """
    Get or create the global coordinator instance.

    Semantic Relationship: CoordinatorInstance references_to Singleton

    Returns:
        The global CoordinatorService instance, creating it if needed
    """
    global _coordinator
    if _coordinator is None:
        _coordinator = CoordinatorService()
    return _coordinator


# Backward compatibility alias
def get_coordinator() -> CoordinatorService:
    """Deprecated: Use get_coordinator_service_instance() instead"""
    return get_coordinator_service_instance()


def start_coordinator_service(redis_host: str = DEFAULT_REDIS_HOST, redis_port: int = DEFAULT_REDIS_PORT) -> CoordinatorService:
    """
    Start the global coordinator service.

    Semantic Relationship: StartedCoordinator causes_background_monitoring

    Args:
        redis_host: Redis server host
        redis_port: Redis server port

    Returns:
        The started CoordinatorService instance
    """
    global _coordinator
    _coordinator = CoordinatorService(redis_host, redis_port)
    _coordinator.start_coordinator_service_background()
    return _coordinator


# Backward compatibility alias
def start_coordinator(redis_host: str = DEFAULT_REDIS_HOST, redis_port: int = DEFAULT_REDIS_PORT) -> CoordinatorService:
    """Deprecated: Use start_coordinator_service() instead"""
    return start_coordinator_service(redis_host, redis_port)
