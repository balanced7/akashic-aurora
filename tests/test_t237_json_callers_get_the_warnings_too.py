"""T237 RED: `ask --json` returns before the evidence notice, so machine callers are blind.

FOUND BY BEING THE MACHINE CALLER. A blind-draft experiment tonight was silently compromised
by a clipped file (`bus.py` at 40000 of 80052 chars, hiding `cursor:lane:` at line 1201), and
I scored the resulting miss as a reasoning failure until I checked. The notice built to
prevent exactly that never reached me.

TWO SEPARATE GAPS, and I only knew about the first:

  1. the notice goes to STDERR, and my probe captured stdout only;
  2. AND THE `--json` BRANCH RETURNS BEFORE THE NOTICE IS EMITTED AT ALL -- so it fires on
     NEITHER channel for a programmatic caller.

Verified: `ask --with core/comm/bus.py --json` produced `context.truncated == True` in the
payload and `'CLIPPED' in stderr == False`.

That is my own T218 reaching some call sites and not all -- the same shape as T219 (a fix
wired into one of two harnesses) and T220 (a pointer fixed at one of two clip sites), both of
which I found in other people's code today.

THE FIX FOR A MACHINE READER IS NOT A STDERR LINE. A JSON consumer does not read prose; it
reads keys. The signal already exists at `context.truncated`, but a caller has to KNOW that
nested key to find it, and none of my four probes tonight did. A top-level `warnings` array
is discoverable by anyone who prints the payload once.

Same law as the lesson this run produced: a warning is loud only on a channel the reader is
actually listening to -- and for a machine, the channel is a field.

REWRITTEN IN-PROCESS (suite:test_t237_json_callers_get_the_warnings_too). The first cut
shelled out to `py agent_cli.py ask ...` three times, which reaches the REAL deepseek door:
in a keyless checkout every node died at its precondition with
`no DEEPSEEK_API_KEY and no .secrets/deepseek.key` -- ask() returns that failure BEFORE
attach_evidence runs, so `context` and `warnings` never existed to be asserted on -- and in
a keyed checkout the same three nodes spent three live model calls to test a RENDER. A pin
whose colour depends on a credential and a network is a live-state leak, and it was red for
the wrong reason. Now the door is driven in-process through the same parser and the same
cmd_ask the shell reaches, with exactly one thing faked: the wire. Vendor resolution, key
loading, the client-construction seam, build_context, attach_evidence, _ask_payload and
both render paths all run for real (the T242 pattern, one layer up).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import agent_cli                                    # noqa: E402  (the door under test)
from core.comm import ask as ask_mod                # noqa: E402
from core.comm import runner_lib as _runner_lib     # noqa: E402

# ABSOLUTE on purpose: build_context resolves a relative path against the process cwd, and an
# in-process pin must not care where pytest was launched from. Both stay inside the repo root,
# which the CLI door (no context_root parameter) requires.
BUS = str(REPO / "core" / "comm" / "bus.py")        # ~83k chars: clips at the 40k budget
CLEAN = str(REPO / "core" / "outcome.py")           # ~6k chars: fits with room to spare


# --------------------------------------------------------------------------- fakes
class _Msg:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Msg(content)
        self.finish_reason = "stop"


class _Usage:
    prompt_tokens = 10
    completion_tokens = 5


class _Resp:
    def __init__(self, content):
        self.choices = [_Choice(content)]
        self.usage = _Usage()


class _Completions:
    def create(self, **kwargs):
        return _Resp("ANSWER")


class _Chat:
    completions = _Completions()


class FakeClient:
    """Enough of the OpenAI-compatible surface for ask(), and no network (as in T242's pin).

    Deliberately NOT a mock of build_context or of ask() itself: the whole point is that the
    real evidence path runs and the door renders what the real boundary hands it.
    """
    chat = _Chat()


class _Wire:
    """What the fake factory saw. `calls` proves the REAL construction path was traversed
    (vendor -> key -> factory) rather than bypassed by handing ask() a client directly."""
    def __init__(self):
        self.calls = 0


@pytest.fixture
def wire(monkeypatch):
    """Fake ONLY the network.

    _load_key is what a keyless door patches (T171's K5 pin states that contract, and
    _load_key_for delegates to it for the deepseek vendor so the patch cannot be routed
    around). The value is a placeholder, not a credential. The client factory is the G4/L0
    seam every real call passes through, so replacing it there leaves nothing between this
    test and the wire that is not the wire.

    The budget is pinned to the documented default so the two preconditions below depend on
    two repo files and this number -- never on an AKASHIC_ASK_CONTEXT_CHARS in the caller's
    environment.
    """
    w = _Wire()

    def _factory(*_a, **_k):
        w.calls += 1
        return FakeClient()

    monkeypatch.setattr(ask_mod, "_load_key", lambda: "not-a-real-key-t237")
    monkeypatch.setattr(_runner_lib, "make_openai_compat_client", _factory)
    monkeypatch.setattr(ask_mod, "DEFAULT_CONTEXT_CHARS", 40000, raising=False)
    return w


# --------------------------------------------------------------------------- the door
def _run_cli(capsys, *argv):
    """The same parser and the same cmd_ask the shell reaches -- in this process."""
    ns = agent_cli.build_parser().parse_args(["ask", *argv])
    rc = agent_cli.cmd_ask(ns)
    out, err = capsys.readouterr()
    return rc, out, err


def _ask_json(capsys, *extra):
    rc, out, err = _run_cli(capsys, "--json", *extra, "reply with just: OK")
    i = out.find("{")
    return (json.loads(out[i:]) if i >= 0 else {}), rc, err


# --------------------------------------------------------------------------- the pins
def test_a_json_caller_gets_a_discoverable_warning_when_evidence_was_clipped(capsys, wire):
    """THE PIN. bus.py is ~80k chars against a 40k budget, so this always clips."""
    d, rc, _ = _ask_json(capsys, "--with", BUS)
    assert rc == 0 and wire.calls == 1, "precondition: the fake wire answered through the real door"
    assert (d.get("context") or {}).get("truncated") is True, "precondition: it clipped"
    warnings = d.get("warnings")
    assert warnings, (
        "the payload carries context.truncated but no top-level `warnings` -- a machine "
        "caller must know a nested key to learn its evidence was incomplete, and four "
        "probes tonight did not")
    joined = " ".join(str(w) for w in warnings).lower()
    assert "clip" in joined or "partial" in joined
    assert "bus.py" in joined, "a warning that does not name the file is unactionable"


def test_a_clean_run_carries_no_warnings(capsys, wire):
    """Noise on clean runs gets filtered out mentally, and that is how the real one is missed.
    An empty or absent list on a clean call, never a placeholder."""
    d, rc, _ = _ask_json(capsys, "--with", CLEAN)
    assert rc == 0 and wire.calls == 1, "precondition: the fake wire answered through the real door"
    assert (d.get("context") or {}).get("truncated") is False, "precondition: fits the budget"
    assert not d.get("warnings")


def test_the_human_path_still_prints_to_stderr(capsys, wire):
    """REGRESSION. The machine channel is ADDITIVE -- T218's stderr notice is what a person
    reads, and gaining a field must not cost the line."""
    rc, out, err = _run_cli(capsys, "--with", BUS, "reply with just: OK")
    assert rc == 0 and "ANSWER" in out, "precondition: the fake wire answered through the real door"
    assert "CLIPPED" in (err or ""), "the human notice regressed"
