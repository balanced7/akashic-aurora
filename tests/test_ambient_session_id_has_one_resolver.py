"""RED pins: three session-id resolvers, three answers, and the kinds that matter carry none.

THE MEASUREMENT. `py agent_cli.py context --stats` over a 24h window, 2026-10-03:

    touch              796/796   100%
    phase               88/88    100%
    boot                 0/23      0%
    boot_unverified      0/22      0%
    fail                 0/17      0%
    learning              0/4      0%

Touch and phase are at 100% because the harness hands them a session id in the hook payload.
Every CLI-side kind is at ZERO -- so a filed lesson cannot be joined to the session that
produced it, and neither can a failure or a boot. That is the join Wave 0 is for, missing on
exactly the planes worth joining.

IT IS NOT FOR WANT OF A RESOLVER. There are THREE, and they disagree:

    core/coord/session_focus.py   AKASHIC_SESSION_ID -> CLAUDE_CODE_SESSION_ID -> ""
    core/comm/runner_lock.py      CLAUDE_CODE_SESSION_ID -> CLAUDE_SESSION_ID -> "",
                                  returned as "session:<sid>" or None
    core/comm/operator_reply.py   CLAUDE_CODE_SESSION_ID only, TRUNCATED TO 8 CHARS

Three env-var orders, three return shapes, two empty conventions -- one meaning under three
implementations that diverge quietly, which is the genus this house keeps paying for. The
8-char truncation is the sharpest: an id resolved there can never join one resolved anywhere
else, which is the same defect just measured on the target plane (0 of 365, because two sides
minted two address classes).

WHAT THESE PINS DELIBERATELY DO NOT ASK FOR, and checking saved me from shipping it. The
obvious fix is to default `session_id` inside `EventLog.capture` so every kind gets one for
free. That is WRONG and two existing tests say so: `tests/test_touch_v1.py:104` asserts a
touch built from a payload with no session reports `session_id == ""`, and
`tests/test_phase_emit_v1.py:151` asserts the same plus `session_source == "unknown"`.
`core/events/touch.py:120` states the reason -- the payload's session_id is GROUND TRUTH, and
backfilling from the ambient environment "silently attributes one session's work to another".

So "no session in this payload" and "no session anywhere" are different facts, and the
difference is this house's own zero-is-not-no law applied to attribution. A door-level default
would erase it. The resolver is therefore AMBIENT-CONTEXT ONLY: a CLI process with no payload
may ask the environment; a builder holding a payload may not be overridden by it.

Run::

    py -m pytest tests/test_ambient_session_id_has_one_resolver.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FULL = "428ba6c4-2217-4008-a2be-ecd9901cc3b2"


# --------------------------------------------------------------- the resolver
def test_there_is_one_ambient_resolver():
    from core.coord.session_id import ambient_session_id, session_of   # noqa: F401


def test_it_reads_the_three_env_vars_in_precedence_order(monkeypatch):
    """AKASHIC_SESSION_ID is the harness override (a runner lane, a test);
    CLAUDE_CODE_SESSION_ID is what Claude Code exports; CLAUDE_SESSION_ID is the legacy
    spelling runner_lock still honours. All three must be in ONE place."""
    from core.coord.session_id import ambient_session_id
    for v in ("AKASHIC_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
        monkeypatch.delenv(v, raising=False)

    monkeypatch.setenv("CLAUDE_SESSION_ID", "legacy")
    assert ambient_session_id()[0] == "legacy"
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "claude-code")
    assert ambient_session_id()[0] == "claude-code", "CLAUDE_CODE_SESSION_ID must outrank the legacy spelling"
    monkeypatch.setenv("AKASHIC_SESSION_ID", "override")
    assert ambient_session_id()[0] == "override", "the harness override must win"


def test_it_returns_the_full_id_never_truncated(monkeypatch):
    """THE JOIN-KILLING PIN. operator_reply truncates to 8 chars for a DISPLAY key shape. A
    resolver that truncates mints an id that can never join a full-length one -- the exact
    shape measured on the target plane, where two address classes intersected at zero."""
    from core.coord.session_id import ambient_session_id
    monkeypatch.delenv("AKASHIC_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", FULL)
    got, _src = ambient_session_id()
    assert got == FULL, "the resolver truncated or rewrote the id: %r" % got
    assert len(got) == len(FULL) == 36


def test_absent_is_empty_AND_SAYS_SO(monkeypatch):
    """Zero is not no, and the house already solved this correctly in exactly one place.
    `core/events/touch.py:_session_of` returns (id, SOURCE) -- "payload", "env" or "unknown" --
    so an unattributable touch is emitted and is not indistinguishable from an attributed one.
    The other three resolvers return a bare string and throw that away. Lifting the pair is the
    unification; returning a bare id would unify them on the WORSE of the two contracts."""
    from core.coord.session_id import ambient_session_id
    for v in ("AKASHIC_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
        monkeypatch.delenv(v, raising=False)
    sid, src = ambient_session_id()
    assert sid == ""
    assert src == "unknown", "absence must be TYPED, not just empty: got source %r" % src


# --------------------------------------------------- the ratchet that matters most
def test_the_payload_outranks_the_environment_and_the_source_is_recorded(monkeypatch):
    """THE PROPERTY THAT MUST SURVIVE THE UNIFICATION, and my first draft of this pin had it
    backwards. I assumed touch REFUSED the ambient fallback; it does not -- it takes it and
    RECORDS that it did. touch.py:120: "The environment is ambient: it inherits from parents
    and siblings, so resolving a seat from it first silently attributes one session's work to
    another. The payload's session_id is ground truth for who made this call."

    So the rule is not "never read the env". It is "payload wins, and the loser is named".
    A shared resolver that drops the source would quietly destroy that."""
    from core.coord.session_id import session_of
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "ambient-env-sid")

    sid, src = session_of({"session_id": "from-the-payload"})
    assert (sid, src) == ("from-the-payload", "payload"), (
        "the ambient environment outranked the payload -- that attributes one session's "
        "work to another")

    sid, src = session_of({})
    assert (sid, src) == ("ambient-env-sid", "env"), (
        "the env fallback must still work, and must be LABELLED env: got %r" % (src,))


def test_touch_delegates_rather_than_keeping_its_own_copy():
    """touch.py is where the good contract lives; after the unification it should be the
    shared one, not a fourth implementation that happens to agree today."""
    import inspect
    from core.events import touch as T
    src = inspect.getsource(T)
    assert "session_id" in src and "core.coord.session_id" in src, (
        "touch.py still carries its own session resolution instead of delegating to the "
        "shared module -- four implementations, one meaning")


# --------------------------------------------------------------- the call sites
def test_the_cli_capture_sites_resolve_a_session():
    """learning / fail / boot are CLI-or-hook processes with no payload to consult, so the
    ambient environment IS their ground truth -- and all three currently pass nothing."""
    import re
    src = (ROOT / "agent_cli.py").read_text(encoding="utf-8")
    start = src.index('capture_event("learning"')
    block = src[start:start + 600]
    assert re.search(r"session_id\s*=", block), (
        "cmd_learn's capture_event passes no session_id, so a filed lesson cannot be joined "
        "to the session that produced it (measured 0 of 4 over 24h)")


def test_the_old_resolvers_agree_with_the_shared_one(monkeypatch):
    """Names the unification, so a future edit that re-forks the answer fails here rather
    than as a quietly dead join months later."""
    monkeypatch.delenv("AKASHIC_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", FULL)
    from core.coord.session_id import ambient_session_id
    from core.coord import session_focus
    assert session_focus.this_session() == ambient_session_id()[0], (
        "session_focus.this_session resolves a different id than the shared resolver")
