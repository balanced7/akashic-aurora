"""One session identity, resolved one way, with its provenance attached.

WHY THIS MODULE EXISTS. Four places resolved "which session is this" and gave four answers:

    core/coord/session_focus.py   AKASHIC_SESSION_ID -> CLAUDE_CODE_SESSION_ID -> ""
    core/comm/runner_lock.py      CLAUDE_CODE_SESSION_ID -> CLAUDE_SESSION_ID -> "",
                                  returned as "session:<id>" or None
    core/comm/operator_reply.py   CLAUDE_CODE_SESSION_ID only, TRUNCATED TO 8 CHARS
    core/events/touch.py          payload -> env, returning (id, source)

Three env-var orders, three return shapes, two empty conventions. One meaning under four
implementations that diverge quietly, which is the genus this house keeps paying for. The
truncation is the sharpest edge: an id shortened for a display key can never join a
full-length one, which is the same shape measured on the target plane the same day -- two
sides minting two address classes, intersecting at zero.

The consequence, measured by `context --stats` over 24h on 2026-10-03: touch 796/796 and
phase 88/88 carry a session id, while boot 0/23, boot_unverified 0/22, fail 0/17 and
learning 0/4 carry none. A filed lesson could not be joined to the session that produced it.

THE CONTRACT IS TOUCH'S, NOT THE OTHER THREE'S, AND THAT CHOICE IS THE WHOLE DESIGN.
`touch._session_of` was the only one that got this right, so it is what gets lifted here
rather than the simpler string-returning shape:

  * THE PAYLOAD OUTRANKS THE ENVIRONMENT. The environment is ambient -- it inherits from
    parents and siblings -- so resolving from it first silently attributes one session's work
    to another. When a caller holds a payload, that payload is ground truth for who made the
    call.
  * THE SOURCE IS ALWAYS RETURNED. "payload", "env" or "unknown". An id that came from the
    ambient environment is a weaker fact than one the caller was handed, and a consumer that
    cannot tell them apart will eventually join on the weaker one. This is the house's
    zero-is-not-no law applied to attribution: absence is TYPED, never a bare empty string.
  * NOTHING IS TRUNCATED. Callers that need a short form (a roster key, a display label) cut
    it themselves, at the point of display, where the loss is visible.

Pure: environment reads only, no store, no imports beyond os. Safe on the hot capture path.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional, Tuple

#: Checked in order. AKASHIC_SESSION_ID is the harness override (a runner lane, a test) and
#: wins because it is set deliberately; CLAUDE_CODE_SESSION_ID is what Claude Code exports
#: into every tool process; CLAUDE_SESSION_ID is the legacy spelling runner_lock honoured.
ENV_VARS = ("AKASHIC_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")

PAYLOAD = "payload"
ENV = "env"
UNKNOWN = "unknown"


def ambient_session_id() -> Tuple[str, str]:
    """The session id visible in this process's environment, and where it came from.

    Returns ``(id, "env")`` or ``("", "unknown")``. Never truncates, never guesses, never
    invents a placeholder -- a fabricated id would join something, which is worse than
    joining nothing.
    """
    for var in ENV_VARS:
        try:
            v = str(os.environ.get(var) or "").strip()
        except Exception:                                                 # noqa: BLE001
            continue
        if v:
            return v, ENV
    return "", UNKNOWN


def session_of(payload: Optional[Mapping[str, Any]] = None) -> Tuple[str, str]:
    """Resolve a session for a call, payload first. Returns ``(id, source)``.

    Use this wherever a payload MIGHT be available (a hook). Use `ambient_session_id` where
    there is provably no payload to consult (a CLI process), so the call site states which
    situation it is in rather than passing an empty dict and hoping.
    """
    try:
        sid = str((payload or {}).get("session_id") or "").strip()
    except Exception:                                                     # noqa: BLE001
        sid = ""
    if sid:
        return sid, PAYLOAD
    return ambient_session_id()


def short(session_id: str, n: int = 8) -> str:
    """The display form, at the point of display. Kept here so the one place that used to
    truncate inside its resolver (operator_reply, to match roster's 8-char key shape) can
    say so explicitly instead of returning a shortened id that silently will not join."""
    return str(session_id or "").strip()[:n]
