"""
RB-7 (T029 Wave 2) -- durable-pointer honesty when the firehose evicts a referenced payload.

Bar (docs/library/design/20260701_resilience-battery-sliced-execution-plan_8d660c.md): a promoted/drill pointer whose payload
has been evicted by the stream bound renders "payload aged out", never a blank or
confidently-wrong "no event" (R14, payload-drop half). The check leans on a designed
property: FileLedger ids are monotonic per-stream ints "so they stay comparable even
after maxlen trimming" (core/foundation/ledger.py); Redis stream ids (<ms>-<seq>) order
the same way. An id we cannot order is never claimed as aged -- honesty both directions.

Run: py -m pytest tests/test_evicted_payload_honesty.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.events import event_log as EL
from core.events.event_query import EventQuery
from core.foundation.ledger import FileLedger

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tiny_log(tmp_path, monkeypatch, maxlen=5):
    """An isolated EventLog whose canonical firehose holds only `maxlen` events."""
    monkeypatch.setattr(EL, "CANONICAL_MAXLEN", maxlen)
    monkeypatch.setattr(EL, "PER_AGENT_MAXLEN", maxlen)
    return EL.EventLog(FileLedger(str(tmp_path)))


def test_evicted_pointer_confesses_aging(tmp_path, monkeypatch):
    log = _tiny_log(tmp_path, monkeypatch)
    # capture() returns a BoundaryOutcome since T179 (64066a3f); .ref IS the _ref pointer.
    refs = [log.capture("note", f"event {i}").ref for i in range(8)]
    ev, why = log.resolve(refs[0])          # ids 1..3 evicted by the bound of 5
    assert ev is None
    assert "aged out" in why, f"an evicted payload must say so, got: {why!r}"
    assert "if it ever existed" in why, \
        "the claim stays within its evidence: sparse (Redis) ids below the oldest " \
        "survivor may never have been minted -- eviction is asserted conditionally " \
        "(live find 2026-07-10: a nonsense id far below the ms-epoch range was " \
        "rendered as unconditionally evicted)"


def test_present_pointer_resolves_clean(tmp_path, monkeypatch):
    log = _tiny_log(tmp_path, monkeypatch)
    refs = [log.capture("note", f"event {i}").ref for i in range(8)]
    ev, why = log.resolve(refs[-1])
    assert why is None and ev is not None and ev["summary"] == "event 7"


def test_never_existed_says_so_without_false_aging(tmp_path, monkeypatch):
    log = _tiny_log(tmp_path, monkeypatch)
    for i in range(8):
        log.capture("note", f"event {i}")
    ev, why = log.resolve(f"event:{EL.RAW_STREAM}:99999")   # beyond the newest id
    assert ev is None
    assert "aged out" not in why, "an id newer than every survivor was never evicted"


def test_malformed_pointer_is_named(tmp_path, monkeypatch):
    log = _tiny_log(tmp_path, monkeypatch)
    ev, why = log.resolve("bogus-not-a-ref")
    assert ev is None and "followable" in why


def test_get_still_returns_bare_event(tmp_path, monkeypatch):
    """get() keeps its contract (event-or-None) and shares resolve()'s scan."""
    log = _tiny_log(tmp_path, monkeypatch)
    refs = [log.capture("note", f"event {i}").ref for i in range(3)]
    assert log.get(refs[0])["summary"] == "event 0"
    assert log.get(f"event:{EL.RAW_STREAM}:777") is None


def test_query_layer_shares_the_honest_door(tmp_path, monkeypatch):
    log = _tiny_log(tmp_path, monkeypatch)
    refs = [log.capture("note", f"event {i}").ref for i in range(8)]
    eq = EventQuery(log)
    ev, why = eq.resolve(refs[0])
    assert ev is None and "aged out" in why


def test_cli_drill_door_resolves_honestly():
    """Structural guard: the `events --get` drill door goes through resolve() so a miss
    prints the confession, never a bare 'no event' that reads as never-existed."""
    src = open(os.path.join(REPO, "agent_cli.py"), encoding="utf-8").read()
    assert ".resolve(args.get)" in src, \
        "cmd_events --get must resolve through the honest door (RB-7)"
