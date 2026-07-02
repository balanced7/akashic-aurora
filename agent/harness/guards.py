"""Action-veto policy shared by every harness adapter (Integration Tiers H1).

Two vetoes protect the shared tree, and their RULES -- including the teaching messages
and the RC-01 fail-closed-when-unidentified rule -- must be identical no matter which
harness the action came through. Adapters translate their payload in and their runtime's
deny shape out; the verdict text comes from here.

Both guards fail OPEN when their policy layer is unavailable (advisory by design), but
the lock guard fails CLOSED on an un-verifiable lock: a silently-unset agent id must
not disable peer protection.
"""


def git_veto(command: str) -> str:
    """The deny reason if `command` blanket-stages git (agent/policy/git_guard.py),
    else "" (allow)."""
    if not command:
        return ""
    try:
        from agent.policy.git_guard import check_git_command
        allowed, reason = check_git_command(command)
    except Exception:
        return ""   # policy unavailable -> allow
    return "" if allowed else (reason or "")


def lock_veto(path: str, agent_id: str, id_hint: str) -> str:
    """The deny reason if a PEER holds an advisory lock on `path` (core/comm/locks.py),
    else "". With `agent_id` set we know who we are and only a PEER's lock blocks. With
    it UNSET we can't verify ownership, so we fail CLOSED on any locked path, teaching
    the fix -- `id_hint` says where THIS harness sets its env (the message must name a
    place the reader can actually reach)."""
    if not path:
        return ""
    try:
        from core.comm.locks import path_conflict
        c = path_conflict(path, agent_id or "(unidentified)")
    except Exception:
        return ""   # lock layer unavailable -> allow (advisory)
    if not c.get("conflict"):
        return ""
    if not agent_id:
        return (f"AKASHIC_AGENT_ID is not set, so lock ownership can't be verified and this path is "
                f"locked by {c.get('held_by')}. Set AKASHIC_AGENT_ID=<your agent id> "
                f"({id_hint}) so the peer-lock guard can tell your edits from a peer's.")
    return c.get("reason", "")
