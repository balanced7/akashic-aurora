"""PRE-REGISTERED ACCEPTANCE (T179) -- capture must not report a lost event it actually stored.

THE DEFECT, found by reading the function for the T170 migration. `self.index.add(out)` and the
per-agent stream emit both sat INSIDE the outer try, so a failure in either -- documented one line
above as "best-effort; the Ledger write above is the record" -- was caught by the outer handler,
logged as "capture failed (ignored)" and returned as None. The event was on the canonical
firehose the whole time.

That is a boundary lying in the OPPOSITE direction from T149. T149 claimed success for a send
that never happened; this claimed failure for a write that did. Both are the same disease: a
verdict that does not match the world. And it poisons any drop count built on it, which is
precisely what the Season 1 coverage manifest needs to be trustworthy.

WHY THE LIE HAD NOWHERE ELSE TO GO. The old return was dict-or-None -- two states for three
situations. "Record written, index behind" is neither a clean success nor a loss, so it had to be
squeezed into one of them, and the code chose the wrong one. This is T170's thesis in miniature:
the missing state is what forces the lie.

  K1  a clean capture returns a truthy BoundaryOutcome carrying the event's followable ref
  K2  canonical write OK + index THROWS  -> PARTIALLY, never failed          (the lie, pinned)
  K3  canonical write OK + per-agent stream THROWS -> PARTIALLY, never failed
  K4  the canonical emit failing IS a failure, and it names the cause
  K5  capture never raises -- the auto-logger must never cost the host command
  K6  capture_event (the hot-path wrapper) returns an outcome too, never a bare None

Run: py -m pytest tests/test_t179_capture_cannot_lie.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.events import event_log as EL  # noqa: E402


class _Ledger:
    """Emits fine unless a stream is named in `boom`."""

    def __init__(self, boom=()):
        self.boom, self.emitted = set(boom), []

    def emit(self, stream, event, maxlen=None):
        if stream in self.boom:
            raise RuntimeError(f"stream {stream} is down")
        self.emitted.append(stream)
        return f"id-{len(self.emitted)}"


class _Index:
    def __init__(self, boom=False):
        self.boom, self.added = boom, []

    def add(self, event):
        if self.boom:
            raise RuntimeError("index is corrupt")
        self.added.append(event)


def _log(ledger=None, index=None):
    log = EL.EventLog.__new__(EL.EventLog)      # bypass __init__'s store wiring
    log.ledger = ledger or _Ledger()
    log.index = index
    return log


def test_k1_a_clean_capture_is_truthy_and_carries_its_ref():
    log = _log(index=_Index())
    o = log.capture("note", "hello")
    assert bool(o) is True, "a fully successful capture must be truthy"
    assert o.ref and "event:" in o.ref, "the followable ref is the handle callers act on"
    assert o.detail.get("summary") == "hello"


def test_k2_an_index_failure_is_PARTIAL_not_a_lost_event():
    """THE DEFECT. The canonical write succeeded; the old code returned None and logged
    'capture failed'. The event was never lost -- only the convenience index was behind."""
    ledger = _Ledger()
    o = _log(ledger=ledger, index=_Index(boom=True)).capture("note", "hello")
    assert o.ok is True, "the record IS on the firehose -- this is not a failure"
    assert o.partial is True, "nor is it a clean success: an index is behind"
    assert bool(o) is False, "a partial is falsy, so a caller cannot mistake it for done"
    assert "index" in o.why.lower() and o.why, "it must name which index is behind"
    assert EL.RAW_STREAM in ledger.emitted, "the canonical write really did happen"


def test_k3_a_per_agent_stream_failure_is_also_PARTIAL():
    ledger = _Ledger(boom={EL.per_agent_stream("claude")})
    o = _log(ledger=ledger, index=_Index()).capture("note", "hi", agent_id="claude")
    assert o.ok is True and o.partial is True
    assert "per-agent" in o.why.lower()
    assert EL.RAW_STREAM in ledger.emitted


def test_k4_a_canonical_emit_failure_is_a_named_failure():
    o = _log(ledger=_Ledger(boom={EL.RAW_STREAM})).capture("note", "hi")
    assert o.ok is False, "no canonical write means the event really is lost"
    assert "RuntimeError" in o.why and "down" in o.why, "a failure must name its cause"


class _Weird(Exception):
    """Something no caller could have foreseen -- the case the prime directive is about."""


def test_k5_capture_swallows_errors_but_not_the_operator():
    """The auto-logger's prime directive: capturing the story must never cost you the thing you
    were doing. But "never raises" has a boundary -- the FIRST draft of this pin asserted that
    even KeyboardInterrupt was swallowed, which would mean Ctrl-C could not stop a hung capture.
    Swallowing the operator is worse than the bug being fixed. The real contract is: every
    Exception is absorbed and reported; BaseException (Ctrl-C, SystemExit) passes through."""
    class _Hostile:
        def emit(self, *a, **k):
            raise _Weird("unforeseeable")

    o = _log(ledger=_Hostile()).capture("note", "hi")     # must not raise
    assert o.ok is False and "_Weird" in o.why

    class _Interrupted:
        def emit(self, *a, **k):
            raise KeyboardInterrupt()

    try:
        _log(ledger=_Interrupted()).capture("note", "hi")
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("KeyboardInterrupt must PASS THROUGH -- a telemetry write that eats "
                             "Ctrl-C makes a hung capture unkillable")


def test_k6_the_hot_path_wrapper_returns_an_outcome_not_none(monkeypatch):
    monkeypatch.setattr(EL, "get_event_log", lambda: (_ for _ in ()).throw(RuntimeError("no store")))
    o = EL.capture_event("note", "hi")
    assert hasattr(o, "ok") and o.ok is False, (
        "capture_event returned a bare None on failure -- the same unrepresentable silence one "
        "layer out from the function it wraps")
    assert o.why, "and it must say why"
