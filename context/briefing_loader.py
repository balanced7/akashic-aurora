"""
Briefing loader: the most recent handoff briefing addressed to an agent.

Semantic Relationship: Briefing derived_from PreviousHandoff (AgentSignalLedger)

Part of the Context pillar (System 4). Unlike the other loaders this returns a
single most-recent item, not a ranked list: a briefing is "what the last agent
handed to me." It replays the signal ledger for HANDOFF signals targeting this
agent and returns the latest one's payload (task, context, blockers).
"""

from typing import Any, Dict, Optional


def load_briefing_from_previous_handoff(
    agent: str,
    *,
    signal_ledger: Any = None,
    scan: int = 10000,
) -> Optional[Dict[str, Any]]:
    """
    Return the most recent handoff briefing addressed to `agent`, or None.

    Semantic Relationship: Briefing derived_from LatestHandoff (to this agent)

    Replays the canonical signal stream (oldest-first), keeping the last HANDOFF
    whose `target_agent` is this agent. No handoff -> None (graceful).
    """
    if signal_ledger is None:
        from core.signals.agent_signal_ledger import AgentSignalLedger
        signal_ledger = AgentSignalLedger()

    latest = None
    for _cursor_id, signal in signal_ledger.replay_signals(after_id="0", count=scan):
        if signal.get("signal_type") == "handoff" and signal.get("target_agent") == agent:
            latest = signal  # oldest-first replay -> last match is the most recent

    if latest is None:
        return None
    return {
        "from_agent": latest.get("agent_id"),
        "task": latest.get("task"),
        "context": latest.get("context", {}),
        "blockers": latest.get("blockers", []),
        "source": latest.get("signal_id") or f"{latest.get('agent_id')}:{latest.get('signal_number')}",
    }
