"""
Core Multi-Agent Systems

Organized by semantic domain:
- foundation: Base primitives and vocabulary (relationship types, caching)
- signals: Agent communication (emit, receive, process signals)
- state: Agent state persistence (checkpoints, recovery)
- learning: Knowledge capture and retrieval

All systems use semantic naming: subject_relationship_object()
"""

__version__ = "1.0.0"
__all__ = ["foundation", "signals", "state", "learning"]


def _quiet_bootstrap() -> None:
    """Windows console-window suppression that survives a reinstall. Closes the durability gap
    opus-engineer flagged and scoped out of its own fix (bf1fb1c).

    THE GAP: scripts/quiet/sitecustomize.py silences the whole spawn tree, but Python only
    auto-imports sitecustomize when its directory is ALREADY on PYTHONPATH at interpreter start.
    That wiring lives in settings.json env blocks -- and the one covering HOME-ROOTED sessions is
    C:/Users/<user>/.claude/settings.json, which is OUTSIDE the repo and cannot be committed. On a
    reinstall, or for a fresh home-rooted seat, that single line is gone and the window-flashing
    returns with nothing in the tree to explain why.

    WHY HERE: opus-engineer's own diagnosis names this seam -- "the hooks call into core/, which
    shells out to git". Anything that can spawn a noisy child in this project imports core first,
    so bootstrapping here makes settings.json an OPTIMISATION (it catches the interpreter earlier)
    rather than a REQUIREMENT. A setup doc would have worked only for someone who read it.

    Two steps, because they fix different halves:
      1. sys.path + import -- makes the patch live in THIS process, which sitecustomize could not
         do for itself if PYTHONPATH was unset at startup. The module is module-level, guarded by
         its own _akashic_quiet marker, and therefore idempotent.
      2. os.environ -- propagates to DESCENDANTS, which is the half that actually stops the
         flashing, since the windows come from grandchildren shelling out to git.

    Honors the same AKASHIC_SHOW_CONSOLES / AKASHIC_TEST_SHOW_CONSOLES escape hatches, matched to
    sitecustomize:43-44 rather than reinvented. Never raises: a cosmetic fix must never be able to
    break an import.
    """
    import os
    import sys
    if sys.platform != "win32":
        return
    if os.environ.get("AKASHIC_SHOW_CONSOLES") or os.environ.get("AKASHIC_TEST_SHOW_CONSOLES"):
        return
    try:
        qdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "quiet")
        if not os.path.isdir(qdir):
            return
        if qdir not in sys.path:
            sys.path.insert(0, qdir)
        try:
            import sitecustomize  # noqa: F401  -- side-effecting, idempotent, self-marking
        except Exception:
            pass
        key = os.path.normcase(os.path.normpath(qdir))
        cur = [p for p in (os.environ.get("PYTHONPATH") or "").split(os.pathsep) if p.strip()]
        # normalised compare, same discipline as sitecustomize's _dedup: a raw string compare
        # would re-append a differently-spelled duplicate on every hop of a deep chain.
        if not any(os.path.normcase(os.path.normpath(p)) == key for p in cur):
            os.environ["PYTHONPATH"] = os.pathsep.join([qdir] + cur)
    except Exception:
        pass


_quiet_bootstrap()
