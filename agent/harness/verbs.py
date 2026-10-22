"""The verb pushes every harness shares: the session map, the plan-time suggestion, the
action-time substitution hint, and the reminder signal (core/coord/verb_guide.py says why).

Adapters call these and translate the text into their runtime's envelope; nothing here knows
a harness name (the agent/harness rule). All three injections carry verb_guide.MARK so the
transcripts show what was suggested, and every one is fail-open and silent when nothing fits.

Volume discipline, because the house already spends ~42k injected tokens a day and trust
falls with volume:
  * the map rides the SessionStart whisper once per session (and again after compaction,
    when the harness re-fires SessionStart) and is budgeted under the 10,000-character
    hook-context cap;
  * at most ONE verb per prompt and ONE per shell command, each verb at most once per
    session (the shared per-session seen set, keys "verb:<name>");
  * a verb the operator typed is never echoed back -- it is counted instead.

Kill switches: AKASHIC_VERB_MAP=0 (the session map), AKASHIC_VERB_NUDGE=0 (both nudges).
The reminder count is a measurement, not an injection, so it has no switch.
"""

from __future__ import annotations

import os

#: Claude Code caps each hook-context string at 10,000 characters and replaces anything longer
#: with a file path and a 2,000-character preview -- the map would silently become a pointer.
HOOK_CONTEXT_CAP = 10_000
_MARGIN = 300


def _cli() -> str:
    try:
        from agent.harness.context import _cli as ctx_cli

        return ctx_cli()
    except Exception:
        return "aurora"


def build_verb_map(already: int = 0) -> str:
    """The situation map, sized to fit beside `already` characters of other whisper text."""
    if os.getenv("AKASHIC_VERB_MAP", "1") == "0":
        return ""
    try:
        from core.coord.verb_guide import render_map

        return render_map(_cli(), max_chars=max(0, HOOK_CONTEXT_CAP - _MARGIN - already))
    except Exception:
        return ""


def _seen_verbs(seen_key: str) -> set[str]:
    from agent.harness.seen import load_seen

    return {s[5:] for s in load_seen(seen_key) if s.startswith("verb:")}


def _mark(seen_key: str, verbs) -> None:
    from agent.harness.seen import mark_seen

    mark_seen(seen_key, [f"verb:{v}" for v in verbs])


def record_reminders(prompt: str, agent_id: str = "", session_id: str = "") -> list[str]:
    """Count the verbs the operator had to type (the miss), one event per prompt."""
    try:
        from core.coord.verb_guide import load, mentioned_verbs

        named = mentioned_verbs(prompt or "", load().keys())
        if named:
            from core.events.event_log import capture_event

            capture_event(
                "verb_reminder",
                "operator named " + ", ".join(named),
                detail={"verbs": named},
                agent_id=agent_id or None,
                session_id=session_id or "",
            )
        return named
    except Exception:
        return []


def verb_plan_line(prompt: str, seen_key: str, agent_id: str = "", session_id: str = "") -> str:
    """At most one verb for this request, or "". Also records the reminder signal."""
    record_reminders(prompt, agent_id, session_id or seen_key)
    if os.getenv("AKASHIC_VERB_NUDGE", "1") == "0":
        return ""
    try:
        from core.coord.verb_guide import match_prompt, render_suggestions

        hits = match_prompt(prompt, k=1, exclude=_seen_verbs(seen_key))
        if not hits:
            return ""
        verbs = [v for v, _ in hits]
        _mark(seen_key, verbs)
        _log("plan", verbs, agent_id, session_id or seen_key)
        return render_suggestions(verbs, _cli(), header="a house verb fits this request:")
    except Exception:
        return ""


def verb_action_line(command: str, seen_key: str, agent_id: str = "", session_id: str = "") -> str:
    """One substitution hint when a shell command hand-rolls what a verb does, or ""."""
    if os.getenv("AKASHIC_VERB_NUDGE", "1") == "0" or not command:
        return ""
    try:
        from core.coord.verb_guide import hand_rolled, render_suggestions

        hits = hand_rolled(command, exclude=_seen_verbs(seen_key))[:1]
        if not hits:
            return ""
        verbs = [v for v, _ in hits]
        _mark(seen_key, verbs)
        _log("action", verbs, agent_id, session_id or seen_key)
        return render_suggestions(
            verbs, _cli(), header="this command hand-rolls a house verb; prefer it:", why=dict(hits)
        )
    except Exception:
        return ""


def _log(altitude: str, verbs: list[str], agent_id: str, session_id: str) -> None:
    try:
        from core.events.event_log import capture_event

        capture_event(
            "verb_nudge",
            f"{altitude}: " + ", ".join(verbs),
            detail={"altitude": altitude, "verbs": verbs},
            agent_id=agent_id or None,
            session_id=session_id or "",
        )
    except Exception:
        pass
