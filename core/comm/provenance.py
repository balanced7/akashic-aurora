"""provenance -- WHERE a message came from, stamped by the door that creates it.

THE WISH (docs/WISHLIST.md, 2026-10-30, phase 3 of the modular-core detangle):

    "Bus messages carry provenance (discord / runner / cli / mcp), so 'did this come from
     Discord?' needs no gateway-log archaeology."

That sentence is precise about the mechanism and it is the mechanism that matters: the answer is
STAMPED AT CREATION, not deduced later. Today it took archaeology -- reading the gateway's log in
another worktree, matching message ids and timestamps -- because the packet itself did not say.
An inferred answer ("the sender is named user, and user usually types in Discord") is exactly the
kind of confident guess that this house has paid for repeatedly: it is right until it is wrong,
and it is never checkable.

THE LAW, in three clauses:

  1. DECLARED BEATS INFERRED. A door that KNOWS what it is says so: `meta["origin"]` passed by
     the caller, else `AKASHIC_DOOR` in the environment (the MCP server and the runners set it
     at import). Inference is only the fallback for doors that do not declare.
  2. INFERENCE READS THE PROCESS, NOT THE SENDER. The fallback asks "what am I?" -- script name,
     module shape -- and never "who does this look like". A name is not a mechanism.
  3. UNKNOWN IS A REAL ANSWER. A message with no origin (every message sent before this landed,
     and any door that declares nothing and is unrecognisable) reads `unknown`. It never reads
     `cli` by default, because "the door I know best" is not evidence.

WHAT THIS IS NOT: not authentication. A stamp records which door WROTE the packet, and any caller
holding the bus could write a different one. It answers "did this arrive through Discord?", not
"was the Discord user who they claimed?" -- the latter needs the identity gate that does not exist
yet, and conflating the two would be the expensive mistake.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

#: The vocabulary. Declared here once: a surface that invents a sixth spelling would make
#: "did this come from Discord?" a question with two answers.
ORIGINS = ("discord", "runner", "cli", "mcp")

#: The key the stamp lands on, inside a message's meta.
KEY = "origin"

#: No door declared one and the process is unrecognisable.
UNKNOWN = "unknown"

#: Environment variables a door may use to declare itself, in precedence order. AKASHIC_DOOR is
#: the one this house sets; the others are accepted because an out-of-tree launcher (the DSH
#: plugin, a codex wake seat) may already be exporting one of them.
_ENV_VARS = ("AKASHIC_DOOR", "AKASHIC_ORIGIN", "BIFROST_DOOR")

#: Script-name fragments -> the door they belong to. Matched on the BASENAME of argv[0], because a
#: path is not a mechanism either (".../scripts/bifrost_runner_kimi.py" is a runner wherever it
#: lives). ORDER MATTERS: the more specific fragment first, so the Discord runner reads as the
#: Discord ear and not as a generic runner.
_SCRIPT_HINTS = (
    ("bifrost_runner_discord", "discord"),
    ("discord_gateway", "discord"),
    ("bifrost_runner", "runner"),
    ("run_aurora_service", "runner"),
    ("bifrost_daemon", "runner"),
    ("bifrost_wake", "runner"),
    ("ai_setup_mcp", "mcp"),
    ("agent_cli", "cli"),
)


def _normalise(value: Any) -> Optional[str]:
    """A recognised origin, or None. An unrecognised declaration is NOT silently accepted: it
    would put a seventh spelling into the field and make the field unqueryable."""
    if not isinstance(value, str):
        return None
    v = value.strip().lower()
    return v if v in ORIGINS else None


def _from_env() -> Optional[str]:
    for name in _ENV_VARS:
        got = _normalise(os.environ.get(name))
        if got:
            return got
    return None


def _from_process() -> Optional[str]:
    """What IS this process? Read from the module shape first (an MCP server imported its own
    module), then from the script basename."""
    if "ai_setup_mcp" in sys.modules:
        return "mcp"
    try:
        argv0 = os.path.basename(str(sys.argv[0] or ""))
    except Exception:
        argv0 = ""
    low = argv0.lower()
    for fragment, door in _SCRIPT_HINTS:
        if fragment in low:
            return door
    return None


def detect() -> str:
    """The door THIS process speaks for: declared, else inferred, else 'unknown'."""
    return _from_env() or _from_process() or UNKNOWN


def of(meta: Any) -> str:
    """The origin recorded in a message's meta -- 'unknown' when there is none, never a guess."""
    if isinstance(meta, dict):
        got = _normalise(meta.get(KEY))
        if got:
            return got
        # A declaration made by another door may also have been recorded verbatim under a
        # differently-cased key; accepting it is cheap and keeps one spelling on the surface.
        for k, v in meta.items():
            if str(k).lower() == KEY:
                got = _normalise(v)
                if got:
                    return got
    return UNKNOWN


def stamps(meta: Optional[Dict[str, Any]] = None, *, origin: Optional[str] = None) -> Dict[str, Any]:
    """`meta` with the origin set. Idempotent: an EXISTING origin is never overwritten.

    Never overwriting is the whole discipline in one line. The caller who passed an explicit
    origin knows more than this module can see (discord_inbound knows it is the Discord ear even
    if it is running inside a process whose script name says something else), and a later stamp
    that "corrected" it would make the field a function of the last writer.
    """
    out: Dict[str, Any] = dict(meta or {})
    if of(out) != UNKNOWN:
        return out
    declared = _normalise(origin) or detect()
    out[KEY] = declared
    return out
