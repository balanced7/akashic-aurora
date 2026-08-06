"""PRE-REGISTERED ACCEPTANCE (T171) -- ask answers, or says why. It never becomes a seat.

Daniil, 2026-08-04: "what if you could quickly invoke with a verb a deepseek instance to help you
with something... this might help reduce your cognitive load if you could quickly ask for help
yourself."

WHY: across two multi-seat rounds that night, NINE seat-tasks produced TWO findings that reached the
conductor. The rest died to cursor tail-seeding, dedup collapse, budget exhaustion returning "", and
wedges. Asking had become more expensive than doing it myself.

The expensive part was never the model call -- it is the SEAT (identity, lock, cursors, mailbox,
heartbeat, roster row, wake listener, reaper protection), all of which exists so a peer can be
addressed ASYNCHRONOUSLY and survive without the caller. A synchronous ask needs none of it.

  K1  a good answer returns a truthy BoundaryOutcome carrying the text
  K2  a LENGTH-truncated answer returns PARTIALLY, never a silent complete   (the T169 lesson)
  K3  an empty answer is a FAILURE with a reason, never an empty success
  K4  a raising client is caught and named, never propagated                 (ask must not crash a turn)
  K5  no key is a configuration failure that says so
  K6  ask touches NO seat machinery -- no lock, no cursor, no roster, no mailbox
  K7  spend is reported, and an unpriced model reports None rather than a guess

Run: py -m pytest tests/test_t171_ask_is_not_a_seat.py -q
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import ask as A  # noqa: E402


class _Resp:
    def __init__(self, text, finish="stop", pt=100, ct=50):
        self.choices = [type("C", (), {
            "message": type("M", (), {"content": text})(),
            "finish_reason": finish})()]
        self.usage = type("U", (), {"prompt_tokens": pt, "completion_tokens": ct})()


class _Client:
    """Minimal OpenAI-compatible stand-in."""
    def __init__(self, resp=None, exc=None):
        self._resp, self._exc = resp, exc
        outer = self

        class _Completions:
            def create(self, **kw):
                outer.seen = kw
                if outer._exc:
                    raise outer._exc
                return outer._resp

        self.chat = type("Chat", (), {"completions": _Completions()})()


def test_k1_a_good_answer_is_a_truthy_outcome():
    o = A.ask("what is 2+2?", client=_Client(_Resp("4")))
    assert bool(o) is True
    assert o.detail["answer"] == "4"
    assert o.detail["prompt_tokens"] == 100


def test_k2_a_truncated_answer_is_partial_not_complete():
    """The T169 lesson generalized: out of room hands back what it has, MARKED."""
    o = A.ask("write an essay", client=_Client(_Resp("half an ans", finish="length")))
    assert o.partial is True
    assert bool(o) is False, "a partial must be falsy so a caller cannot read it as done"
    assert o.detail["answer"] == "half an ans", "the partial work must survive"
    assert "length" in o.why or "cut" in o.why


def test_k3_an_empty_answer_is_a_named_failure():
    o = A.ask("hello", client=_Client(_Resp("   ")))
    assert o.ok is False and o.why
    assert "empty" in o.why.lower()


def test_k4_a_raising_client_is_caught_and_named():
    o = A.ask("hello", client=_Client(exc=RuntimeError("connection reset")))
    assert o.ok is False
    assert "RuntimeError" in o.why and "connection reset" in o.why


def test_k5_no_key_is_a_configuration_failure_that_says_so(monkeypatch):
    # The seam MOVED: ask no longer reaches into scripts/ for a credential (that import
    # needed a sys.path.insert, which was a real boundary violation). Key resolution is now
    # core-local, so _load_key is what a keyless door patches. K5's claim is unchanged.
    monkeypatch.setattr(A, "_load_key", lambda: None)
    o = A.ask("hello")            # no client -> takes the real construction path
    assert o.ok is False
    assert "key" in o.why.lower()


# The durable transport, excluded from the STATELESS law and governed by its own (T197).
# Named explicitly rather than pattern-matched: a new durable verb must be added here
# DELIBERATELY, which is the point -- silent growth of this set is the drift the law guards.
_DURABLE_FUNCS = {"ask_peer"}


def _stateless_only(tree):
    """The module with its durable-transport functions removed, so the stateless law reads
    only the stateless code. Module-level statements are KEPT: a top-level seat import would
    still be a violation no matter which function it was for."""
    return ast.Module(
        body=[n for n in tree.body
              if not (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                      and n.name in _DURABLE_FUNCS)],
        type_ignores=[])


def test_k6_ask_touches_no_seat_machinery():
    """THE DESIGN CLAIM, enforced SEMANTICALLY: the moment ask acquires a lock or a cursor it has
    become a seat, and inherits every failure mode that made the last two rounds expensive.

    AST, not grep. A raw-source search makes this module's own prose part of the pin's input, so
    DOCUMENTING the design falsifies it: the first cut of K6 went red on the word "mailbox"
    appearing in the ask.py docstring that explains ask deliberately does NOT have one. Reading
    names instead of text dissolves that reflexivity rather than patching one instance of it --
    stripping docstrings would still leave the next explanatory comment to trip it.

    STATED LIMIT, not papered over: this reads static imports, attribute access, bare names and
    call targets. Dynamic access -- getattr(o, "mail" + "box") -- would evade it. That blind spot
    is accepted: this pin guards against DRIFT, not sabotage.

    SCOPED TO THE STATELESS PATH (amended 2026-08-06, T197). T196c added `ask_peer` to this
    module -- a DURABLE ask to a real seat, whose entire purpose is to ride the expectation
    machinery. It made this whole-file scan red on a reference the design requires, and the pin
    then sat red rather than saying anything true. The law was written when `ask` meant only the
    stateless helper; the module has since grown a second, deliberately-durable transport.

    So the law now says what it always MEANT: the STATELESS path touches no seat machinery. Every
    original forbidden name is still enforced, with no exemptions, on `ask`/`ask_many` and every
    helper they reach. `ask_peer` gets its own narrower law in test_t197_peer_presence.py --
    expectations ONLY, and still no lock, cursor, roster or heartbeat. Teeth kept, scope corrected;
    an amended law beats a red one nobody can act on (docs/CONDUCT.md's anti-fossil clause).
    """
    tree = ast.parse(open(os.path.join(ROOT, "core", "comm", "ask.py"), encoding="utf-8").read())
    tree = _stateless_only(tree)

    forbidden = {"runner_lock", "seed_cursor", "roster", "mailbox", "worklive",
                 "acquire", "bifrost_send", "heartbeat", "role_queue", "expectations"}

    referenced = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                referenced.update(alias.name.split("."))
        elif isinstance(node, ast.ImportFrom):
            referenced.update((node.module or "").split("."))
            for alias in node.names:
                referenced.add(alias.name)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
        elif isinstance(node, ast.Name):
            referenced.add(node.id)

    hits = sorted(forbidden & referenced)
    assert not hits, (
        f"ask.py references seat machinery {hits} as CODE -- it is becoming a seat, which is the "
        f"one thing this design exists to avoid")


def test_k7_spend_is_reported_and_an_unpriced_model_says_none():
    o = A.ask("hi", client=_Client(_Resp("yo")))
    assert o.detail["usd"] is not None and o.detail["usd"] > 0, "a priced model must report cost"
    u = A.ask("hi", model="model-that-has-no-rate", client=_Client(_Resp("yo")))
    assert u.detail["usd"] is None, (
        "an unpriced model must report None, never borrow another vendor's rate -- the designed "
        "state runner_token_journal's own comment insists on")
