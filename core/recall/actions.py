"""The importable recall-at-action contract for EXTERNAL consumers (deepseek harness posttool /
cordis plugin, and any other out-of-tree runtime that wants a stable point-of-action recall call
without shelling out to `py agent_cli.py recall-at --json`).

WHY THIS EXISTS as a separate module rather than "just import recall_at": an external plugin
lives on the OTHER side of a process boundary and iterates on a SLOWER clock than this repo. It
needs a function whose signature and failure semantics are a CONTRACT, not an implementation
detail. The engine (`core/recall/at_action.py::recall_at`) is heavily parameterized (subject,
gesture, domain, min_relevance, exclude_sources, count_surface, learning_store injection ...) and
its docstring is an internal design record; a plugin author should not be asked to hold all of
that in their head. This module gives them:

  recall_context(session_key, path, command) -> dict

... one function, three arguments, one return shape, one named failure rule. Everything else is
the engine's job. If the engine's surface changes, the plugin pins THIS import and keeps working.

THE FAIL-OPEN / KILL-SWITCH CONTRACT (mirror these in your plugin verbatim):

  KILL SWITCH   env AKASHIC_RECALL_AT_ACTION=0 disables recall entirely; recall_context returns
                the EMPTY result shape (shown=0, no error) -> render to nothing, inject nothing.
                Default "1" = enabled. This is the SAME switch every harness hook and the CLI
                verb honor -- there is exactly one off-switch for the whole recall channel, so a
                seat that turns recall off never has one surface still injecting.

  FAIL-OPEN     on ANY exception -- store down, missing env, a broken sink -- recall_context
                returns the empty result shape with error=<ExceptionName> and error_detail set,
                it NEVER raises. The caller (your plugin) must therefore NEVER block the agent's
                action on this call: it is advisory cargo (additionalContext-equivalent), not a
                gate. A failed recall is NOT "no relevant lessons"; distinguish by reading the
                `error` key and say 'unavailable' rather than 'nothing relevant' when it is set.

  SESSION KEY   session_key is a REQUIRED plain agent id (e.g. "deepseek"); it maps 1:1 to the
                engine's agent_id and feeds (a) advisory-lock ownership and (b) observation/
                fairness attribution. It is NOT a store key namespace -- pass the id, not a
                path. REQUIRED (no env fallback): an external harness may inherit a wrong
                AKASHIC_AGENT_ID (the DSH seat inherits Claude Code's env), so recall_context
                demands the id explicitly and returns error=MissingSessionKey rather than
                silently mis-attributing to the inherited env.

  DETERMINISM + STALENESS   recall is deterministic (no LLM on the hot path), FAITH-gated (a
                fabricated pointer never surfaces), and each lesson is provenance-labelled with
                the AUTHOR'S OWN status (worked/unverified/...), never laundered as external fact.

Return-shape contract (subset of recall_at's dict the plugin may rely on):
  {
    "path": str|None, "command": str|None, "query": str,
    "lessons": [ { "text": str, "source": str, ... } ],   # highest-signal, faith-gated
    "locks":   [ { "held_by": str, "reason": str, ... } ], # advisory lock always surfaces
    "counter": dict|None,   # strongest genuine dissent to the top lesson
    "verbs":   [ { "verb": str, "purpose": str, ... } ],  # door verbs that match the trigger
    "shown": int, "total": int,
    "faithful": bool, "confidence": float,
    # present ONLY on failure (fail-open): "error": str, "error_detail": str
  }
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

# The ONE kill switch for the whole recall channel. Mirrored (not imported, because the CLINICAL
# contract is that an external plugin re-states it) across every harness hook and the CLI verb.
_KILL_SWITCH = "AKASHIC_RECALL_AT_ACTION"

# The empty result on kill-switch-off. Deliberately NOT an `error` result: recall being turned off
# is a normal, chosen state, not a malfunction -- rendering it as "UNAVAILABLE" would lecture a
# seat that just asked for silence. It is the exact same 'shown 0, no error' shape recall_at
# returns for an honest empty result, so the plugin's renderer needs no special case.
_EMPTY = {
    "path": None, "command": None, "query": "", "lessons": [], "locks": [],
    "counter": None, "verbs": [], "shown": 0, "total": 0,
    "faithful": True, "confidence": 1.0,
}

# The engine seam. Module-level (not a function-local import) because an EXTERNAL consumer pins
# THIS module as its contract, and a contract needs a stable, swappable seam: tests monkeypatch
# `_engine` to a fake (or to None to prove the engine is never reached), and the caller-side
# plugin mirrors this indirection when it wants to detach recall from the real store. Keeping it
# module-level also means the kill-switch test's `_engine = None` genuinely short-circuits the
# hot path rather than leaving a function-local import alive.
#
# Still lazy: the attribute starts as the UNRESOLVED sentinel and resolves to the real engine on
# first use, preserving the cheap-import discipline (the heavy at_action module + its store/cache
# stay out of the import path until a recall is actually requested -- same as core/recall/surface.py).
# `None` is NOT the sentinel: it means "explicitly detached" (never resolve), which is what a test
# sets when it wants to prove the kill switch / guard fires BEFORE the engine is even loaded.
_UNRESOLVED = object()
_engine = _UNRESOLVED


def _resolve_engine():
    """Lazy one-shot resolver: real engine on first use, so the module import stays cheap.
    An `_engine = None` (a test proving the engine must not be reached) stays None."""
    global _engine
    if _engine is _UNRESOLVED:
        from core.recall.at_action import recall_at
        _engine = recall_at
    return _engine


def recall_context(session_key: Optional[str], path: Optional[str] = None,
                   command: Optional[str] = None, *, limit: int = 3,
                   exclude_sources: Optional[set] = None) -> Dict[str, Any]:
    """Recall-at-action for an external runtime: the few highest-signal lessons (+ locks + verbs)
    for a point of action, under a stable, plugin-facing contract.

    FAIL-OPEN / KILL-SWITCH: see the module docstring. Returns the empty shape (never raises) on
    AKASHIC_RECALL_AT_ACTION=0 and on any engine exception (then with error=<Name>, error_detail).
    """
    # Kill switch FIRST -- it is the cheapest check and the one guarantee the operator gets about
    # 'off', so it must be honored before any store/engine work happens.
    if os.getenv(_KILL_SWITCH, "1") == "0":
        return dict(_EMPTY, path=path, command=command)

    # CORRECTNESS GUARD (DSH identity finding, 2026-08-23): session_key is REQUIRED. The
    # engine's own hooks fall back to AKASHIC_AGENT_ID because they run INSIDE a harness that
    # sets it correctly. An EXTERNAL plugin does not: the DSH seat inherits Claude Code's env
    # (AKASHIC_AGENT_ID=claude), so a fallback here would silently attribute every recall to
    # claude -- the same cross-agent attribution leak that motivated T108. Fail LOUD (error
    # shape, not a silent wrong agent) rather than attach to the inherited env.
    if not session_key:
        out = dict(_EMPTY, path=path, command=command)
        out.update(error="MissingSessionKey",
                   error_detail="recall_context requires session_key (a plain agent id); the "
                                "harness env may be inherited and mis-attributed -- pass it "
                                "explicitly, never fall back to AKASHIC_AGENT_ID.")
        return out
    try:
        res = _resolve_engine()(path=path or None, command=command or None,
                                agent_id=session_key,
                                limit=limit, exclude_sources=exclude_sources)
        return {
            "path": res.get("path"), "command": res.get("command"),
            "query": res.get("query"), "lessons": res.get("lessons"),
            "locks": res.get("locks"), "counter": res.get("counter"),
            "verbs": res.get("verbs"), "shown": res.get("shown"),
            "total": res.get("total"), "faithful": res.get("faithful"),
            "confidence": res.get("confidence"),
        }
    except Exception as e:
        # fail-open: a recall path must never brick the caller. `error` distinguishes 'unavailable'
        # from 'nothing relevant' -- the exact confident-zero disease the engine's own handler
        # documents (recall_at_error_masks_as_confident_empty, pin P4).
        out = dict(_EMPTY, path=path, command=command)
        out.update(error=type(e).__name__, error_detail=str(e)[:200])
        return out
