"""The auto-boot whisper shared by every harness adapter (Integration Tiers H0).

Friction audit D2 / fix #2: session start used to only warm the cache -- context still
required remembering to run `boot` (diligence decays; the cue must come TO the agent).
`build_autoboot_context` is that cue, tiered by where the session started, because
context rot is real and unrelated projects deserve silence:

  cwd in the repo, or cwd == the user home dir (the read-bootstrap flow's launch point):
      a compact whisper -- newest note titles, the funnel pulse, unread bus mail, a
      fresh last-session-draft pointer, and the one-hop full-boot command. <= ~10 lines.
  anywhere else:
      SILENT unless something is genuinely NEW (unread mail / fresh draft) -- then one
      line pointing home. Never a standing banner in unrelated projects.

Full boot stays one hop away and remains the ritual (this whisper never replaces it --
it makes forgetting it cheap instead of costly). Kill switch: AKASHIC_AUTOBOOT=0.
Every data pull is independently fail-soft; adapters deliver the returned text in
their runtime's session-start channel and add nothing to it.
"""
import os
import time

from agent.harness.scope import repo_root, session_in_scope

_DRAFT_FRESH_SECS = 2 * 86400


def _notes_line(limit: int = 3) -> str:
    from core.learning.agent_memory import get_agent_memory
    notes = get_agent_memory().get_decisions(days=60)[:limit]
    if not notes:
        return ""
    return "notes: " + "; ".join(f"{d.title} [{str(d.created_at)[5:10]}]" for d in notes)


def _funnel_line() -> str:
    from core.recall.funnel import snapshot, summary_line
    return "funnel: " + summary_line(snapshot(hours=7 * 24))


def _unread_count(agent_id: str) -> int:
    from agent.bifrost_pull import collect_boot_bifrost
    return int((collect_boot_bifrost(agent_id, limit=8) or {}).get("pending", 0) or 0)


def _draft_fresh() -> bool:
    p = os.path.join(repo_root(), "chronicles", "last-session-draft.md")
    try:
        return os.path.isfile(p) and (time.time() - os.path.getmtime(p)) < _DRAFT_FRESH_SECS
    except Exception:
        return False


def build_autoboot_context(cwd: str, agent_id: str) -> str:
    """The whisper text for this session's start point, or "" for silence. Each data pull
    is independently fail-soft: a broken piece drops out, it never blanks the rest."""
    if os.getenv("AKASHIC_AUTOBOOT", "1") == "0":
        return ""
    home_or_repo = session_in_scope(cwd)

    unread = 0
    try:
        unread = _unread_count(agent_id)
    except Exception:
        pass
    fresh_draft = _draft_fresh()

    if not home_or_repo:
        if not unread and not fresh_draft:
            return ""   # unrelated project, nothing new -> full silence
        bits = []
        if unread:
            bits.append(f"{unread} unread bus msg(s)")
        if fresh_draft:
            bits.append("a fresh last-session draft")
        return (f"[akashic] {' and '.join(bits)} waiting -- "
                f"py agent_cli.py boot {agent_id} --task \"...\"  (repo: {repo_root()})")

    lines = [f"[akashic] Akashic Aurora memory (light auto-boot; full context: "
             f"py agent_cli.py boot {agent_id} --task \"<this slice>\")"]
    for build in (_notes_line, _funnel_line):
        try:
            piece = build()
            if piece:
                lines.append("  " + piece)
        except Exception:
            pass
    if unread:
        lines.append(f"  mail: {unread} unread -> py agent_cli.py bifrost-sync {agent_id}")
    if fresh_draft:
        lines.append("  draft: chronicles/last-session-draft.md -> review; promote with "
                     "`py agent_cli.py wrap --commit`")
    if len(lines) == 1:
        return ""   # nothing behind the header -> stay silent rather than print a banner
    return "\n".join(lines)
