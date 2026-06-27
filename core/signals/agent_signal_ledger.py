"""
Agent Signal Ledger: the ordered record of every signal agents emit

Semantic Relationship: AgentSignalLedger records_signals_for Coordination

WHAT THIS IS
------------
A `Ledger` is the generic primitive: an append-only, ordered, replayable record
of any events (see core.foundation.ledger). The AgentSignalLedger is THE specific
ledger this system runs on -- the one that holds agent signals (action, decision,
blocker, handoff, completion, learning).

It owns the signal-specific layout so nothing else has to know it:
- a canonical "agent:events" stream every signal lands on (the firehose the
  coordinator replays), and
- a per-agent stream for each agent's own history,
- plus how many signals each stream retains.

Agents append signals here; the coordinator replays the canonical stream and
reacts. There can be other ledgers for other event kinds -- this is the one for
agent signals.

Usage:
    from core.signals.agent_signal_ledger import AgentSignalLedger

    signal_ledger = AgentSignalLedger()
    signal_ledger.append_signal({"agent_id": "a1", "signal_type": "decision", ...})
    for cursor_id, signal in signal_ledger.replay_signals(after_id="0"):
        ...
"""

from typing import Any, Dict, List, Optional, Tuple

from core.foundation.ledger import Ledger, create_ledger
from core.foundation.redis_connection import DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT

Signal = Tuple[str, Dict[str, Any]]  # (cursor_id, signal)


class AgentSignalLedger:
    """
    The agent-signal ledger: where every emitted signal is recorded, in order.

    Semantic Relationship: AgentSignalLedger built_on Ledger

    Wraps a generic Ledger and centralizes the signal layout (stream names +
    retention). Backed by Redis when up, File always; degrades gracefully.
    """

    CANONICAL_STREAM = "agent:events"   # the firehose: every agent's signals
    PER_AGENT_MAXLEN = 10_000           # signals retained per agent stream
    CANONICAL_MAXLEN = 100_000          # signals retained on the canonical stream

    def __init__(self, ledger: Optional[Ledger] = None,
                 host: str = DEFAULT_REDIS_HOST, port: int = DEFAULT_REDIS_PORT):
        self.ledger = ledger if ledger is not None else \
            create_ledger(prefer_redis=True, host=host, port=port)

    @property
    def redis_available(self) -> bool:
        return getattr(self.ledger, "redis_available", False)

    def stream_for_agent(self, agent_id: str) -> str:
        """The per-agent stream name for one agent's own signal history."""
        return f"agent:{agent_id}:events"

    def append_signal(self, signal: Dict[str, Any]) -> None:
        """
        Record a signal: onto the agent's own stream AND the canonical firehose.

        Semantic Relationship: Signal appended_to AgentSignalLedger
        """
        agent_id = signal.get("agent_id", "unknown")
        self.ledger.emit(self.stream_for_agent(agent_id), signal, maxlen=self.PER_AGENT_MAXLEN)
        self.ledger.emit(self.CANONICAL_STREAM, signal, maxlen=self.CANONICAL_MAXLEN)

    def replay_signals(self, after_id: str = "0", count: int = 100,
                       block_ms: int = 0) -> List[Signal]:
        """
        Replay signals from the canonical firehose, oldest first, after a cursor.

        Semantic Relationship: Signals replayed_from AgentSignalLedger
        """
        return self.ledger.consume(self.CANONICAL_STREAM, after_id=after_id,
                                   count=count, block_ms=block_ms)
