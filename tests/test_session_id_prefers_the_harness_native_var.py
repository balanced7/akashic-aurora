"""RED pins: a DSH seat resolves to the session it INHERITED, not the one it IS.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

RILL'S REPORT, 2026-10-06, verbatim from the bus (1790912239616-0) and the reason he has
missed two fences running:

    "the door resolves my seat via CLAUDE_CODE_SESSION_ID, which is INHERITED from the Claude
    Code shell that launched me, not my real DSH session. Env: DSH_SESSION_ID=session-45421d78
    (LIVE in roster as dsh_agent#45421d78) but CLAUDE_CODE_SESSION_ID=bb86400e-a609
    (inherited; DEAD/tombstoned T086 S1). So consume pins me to the tombstoned
    dsh_agent#bb86400e row and refuses; my lane cursor stays stuck at ~Aug 26 and the wake
    loops."

He is LIVE in the roster and CANNOT READ HIS MAIL. Two fences in a row have gone to him and
neither could land: the filing-schema round recorded "Contract B is UNTESTED, and that is a
result", and the affordance-layer round got no cold-read. Both times I reasoned about why a
seat had not delivered. Both times the seat could not receive.

WHY THIS PIN IS MINE AND NOT HIS. `core/coord/session_id.py` is the ONE resolver I built on
2026-10-05 and migrated sixteen call sites onto, precisely so that "which session is this" had
a single answer. Its env list is:

    ENV_VARS = ("AKASHIC_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")

`DSH_SESSION_ID` is absent. So the unification did not create this bug -- it MADE IT UNIFORM.
Before, sixteen sites were wrong in sixteen ways; now they are wrong in one way, everywhere, for
every DSH seat. That is still an improvement (one place to fix) and it is also exactly the
failure mode a single resolver is supposed to prevent, so it belongs in the file's own pins.

THE DISCRIMINATOR ALREADY EXISTS IN THIS REPO, which is what makes this cheap:
`seat_topology.py:160` already decides `in_dsh = bool(os.getenv("DSH_SESSION_ID"))`. A process
carrying DSH_SESSION_ID *is* a DSH seat, and any Claude session id it also carries is the shell
it was launched from -- inherited noise, not identity.

DEFENSE IN DEPTH, NOT A DUPLICATE FIX. `scripts/local/launch_rill.ps1` (0bc82be2, Daniel,
2026-10-01) already clears the Claude session variables at ingress, with the commit message
"a seat launched from another seat's shell inherited its session id". That is the right fix at
the right place and it only protects sessions launched AFTER it. Rill's current session
predates it and has been unreachable since. A launcher cleans the environment; a resolver must
not be fooled when the environment was not cleaned.

Run::

    py -m pytest tests/test_session_id_prefers_the_harness_native_var.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.coord import session_id as S  # noqa: E402

#: Rill's real environment, as he reported it from his own process.
RILL_REAL = "session-45421d78"
RILL_INHERITED = "bb86400e-a609"

_ALL = ("AKASHIC_SESSION_ID", "DSH_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for v in _ALL:
        monkeypatch.delenv(v, raising=False)


def test_a_dsh_seat_resolves_to_its_own_session_not_the_shell_it_inherited(monkeypatch):
    """THE PIN. Rill's exact environment: both vars set, and the Claude one is a dead shell."""
    monkeypatch.setenv("DSH_SESSION_ID", RILL_REAL)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", RILL_INHERITED)

    sid, src = S.ambient_session_id()
    assert sid == RILL_REAL, (
        "a DSH seat resolved to %r -- the session id it INHERITED from the Claude Code shell "
        "that launched it -- instead of %r, the session it actually is. That pins consume to a "
        "tombstoned roster row and the seat cannot read its mail. DSH_SESSION_ID is absent from "
        "ENV_VARS." % (sid, RILL_REAL))
    assert src and src != S.UNKNOWN


def test_a_claude_seat_is_completely_unchanged(monkeypatch):
    """RATCHET. The fix must not move the answer for the seats that work today."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "428ba6c4-2217-4008-a2be-ecd9901cc3b2")
    sid, src = S.ambient_session_id()
    assert sid == "428ba6c4-2217-4008-a2be-ecd9901cc3b2"
    assert src == S.ENV_SOURCE if hasattr(S, "ENV_SOURCE") else src


def test_the_explicit_override_still_outranks_every_harness(monkeypatch):
    """AKASHIC_SESSION_ID is the deliberate override and must stay first -- a drill or a
    cross-harness probe sets it precisely to say 'I know better than the environment'."""
    monkeypatch.setenv("AKASHIC_SESSION_ID", "deliberate-override")
    monkeypatch.setenv("DSH_SESSION_ID", RILL_REAL)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", RILL_INHERITED)
    assert S.ambient_session_id()[0] == "deliberate-override"


def test_the_source_names_WHICH_VAR_won(monkeypatch):
    """EPISTEMIC STATE, which is the layer Heimdall's half_a named as missing from my own
    affordance model an hour ago: "env" says a variable answered, never WHICH. For a seat that
    carries two session ids and must trust one, the distinction is the whole bug -- a reader
    cannot tell a correctly-resolved DSH seat from a mis-resolved one without it.
    """
    monkeypatch.setenv("DSH_SESSION_ID", RILL_REAL)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", RILL_INHERITED)
    _, src = S.ambient_session_id()
    assert "DSH_SESSION_ID" in src, (
        "the source is %r -- it says a variable answered but not which one, so a seat carrying "
        "an inherited id alongside its own cannot tell a correct resolution from the bug this "
        "file exists for" % (src,))


def test_dsh_is_declared_in_the_resolver_not_patched_at_a_call_site():
    """THE CLASS, not the instance. If a caller special-cases DSH itself, the next harness
    repeats this and the one-resolver property is lost -- which is the whole reason this module
    exists (sixteen sites were migrated onto it on 2026-10-05)."""
    assert "DSH_SESSION_ID" in S.ENV_VARS, (
        "DSH_SESSION_ID is not in core.coord.session_id.ENV_VARS, so any seat that resolves it "
        "correctly is doing so by special-casing at its own call site")
    assert S.ENV_VARS.index("DSH_SESSION_ID") < S.ENV_VARS.index("CLAUDE_CODE_SESSION_ID"), (
        "DSH_SESSION_ID must outrank CLAUDE_CODE_SESSION_ID: a process carrying BOTH is a DSH "
        "seat whose Claude id is the shell it was launched from. Order is the fix.")
    assert S.ENV_VARS.index("AKASHIC_SESSION_ID") == 0, "the explicit override stays first"
