"""
Briefing loader: the most recent handoff briefing addressed to an agent.

Semantic Relationship: Briefing derived_from PreviousHandoff (AgentSignalLedger)

Part of the Context pillar (System 4). Unlike the other loaders this returns a
single most-recent item, not a ranked list: a briefing is "what the last agent
handed to me." It replays the signal ledger for HANDOFF signals targeting this
agent and returns the latest one's payload (task, context, blockers).
"""

from typing import Any, Dict, Optional


def _consumed(handoff: Dict[str, Any], agent: str, learning_store: Any = None) -> bool:
    """True once the target agent has recorded a LESSON after this handoff was written.

    A briefing's job is delivery: the target's next boot surfaces it, the target works. The
    first lesson the target records after the handoff is proof the baton changed hands -- from
    then on the briefing is history, not context. (Without this, a consumed handoff tops every
    boot indefinitely: the 2026-06-29 cursor handoff was still the lead LESSONS line on
    2026-07-02.) Both timestamps are datetime.utcnow().isoformat(), so a lexical compare is a
    time compare. FAIL-OPEN on a missing timestamp or store error: re-surfacing a stale
    briefing is cheap, losing a live one is not. The full history stays one hop away:
    `py agent_cli.py handoff <me> --list`.
    """
    ts = str(handoff.get("timestamp") or "")
    if not ts:
        return False
    try:
        if learning_store is None:
            from core.learning.learning_store import get_learning_store
            learning_store = get_learning_store()
        for rec in learning_store.load_learnings_contributed_by_agent(agent):
            if str(rec.get("timestamp") or "") > ts:
                return True
    except Exception:
        return False
    return False


def load_briefing_from_previous_handoff(
    agent: str,
    *,
    signal_ledger: Any = None,
    learning_store: Any = None,
    scan: int = 10000,
) -> Optional[Dict[str, Any]]:
    """
    Return the most recent handoff briefing addressed to `agent`, or None.

    Semantic Relationship: Briefing derived_from LatestHandoff (to this agent)

    Replays the canonical signal stream (oldest-first), keeping the last HANDOFF
    whose `target_agent` is this agent. No handoff -> None (graceful). A handoff the
    agent has already acted on (see _consumed) is retired -> None as well.
    """
    if signal_ledger is None:
        from core.signals.agent_signal_ledger import AgentSignalLedger
        signal_ledger = AgentSignalLedger()

    latest = None
    for _cursor_id, signal in signal_ledger.replay_signals(after_id="0", count=scan):
        if signal.get("signal_type") == "handoff" and signal.get("target_agent") == agent:
            latest = signal  # oldest-first replay -> last match is the most recent

    if latest is None or _consumed(latest, agent, learning_store):
        return None
    return {
        "from_agent": latest.get("agent_id"),
        "task": latest.get("task"),
        "context": latest.get("context", {}),
        "blockers": latest.get("blockers", []),
        "source": latest.get("signal_id") or f"{latest.get('agent_id')}:{latest.get('signal_number')}",
    }
