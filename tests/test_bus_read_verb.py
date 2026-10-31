"""`bus read <id>` and the full-wake path: pointers must be followable, previews must be escapable.

THE WISH (docs/WISHLIST.md, 2026-10-30, phase 3):
    "Full waking message on wake (WOKE BY previews are clipped; every wake needed a hand-written
     json one-liner), plus `bus read <id>`."

Two halves of one problem. The preview is clipped ON PURPOSE -- it is rendered onto a status line,
and a 20k body there would be worse than useless -- but a clipped preview is only acceptable if
the id it names can be followed. So:

  * `bus read <id>` prints the WHOLE packet (every wire field, plus where it came from), searching
    every stream that can carry a message, because a stream id is unique only WITHIN its stream.
    When an id is held by several streams it SAYS SO rather than picking one.
  * `--wake-full` prints the whole waking message at fire time, so the turn that must act on it
    never reconstructs it from a preview.

The pins below are about the honest failure modes, not the happy path:
  1. NOT FOUND is a real answer with a reason -- and it names how many streams were searched, so
     "I looked in six" can never be mistaken for "I looked everywhere".
  2. an id held by TWO streams is reported as ambiguous, never silently resolved;
  3. reading is read-only: the fake client REFUSES anything but xrange/scan_iter;
  4. provenance prints `unknown` (never a guess) for a message that carries no origin, and the
     actual origin when the door stamped one.

Run: py tests/test_bus_read_verb.py   (or via pytest)
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import bus_read as BR                                         # noqa: E402


def _fields(**kw):
    return [(k.encode(), str(v).encode()) for k, v in kw.items()]


class _Client:
    """xrange/scan_iter only; every other method raises -- the read-only pin's mechanism."""

    def __init__(self, streams):
        self.streams = streams
        self.calls = []

    def xrange(self, key, min=None, max=None, count=None, **_kw):
        self.calls.append(("xrange", key, min, max))
        rows = []
        for sid, fields in self.streams.get(key, []):
            if min is not None and sid != min:
                continue
            rows.append((sid, fields))
        return rows

    def scan_iter(self, match=None, count=None, **_kw):
        self.calls.append(("scan_iter", match))
        return iter([k.encode() for k in self.streams])

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        def _refuse(*_a, **_kw):
            raise AssertionError(f"bus read called {name!r} -- this door is READ-ONLY (no cursor "
                                 f"to advance, nothing to consume)")
        return _refuse


def _wire(monkeypatch, streams):
    client = _Client(streams)
    monkeypatch.setattr(BR, "_client", lambda: client)
    return client


MESSAGE = [("1793405184749-0", _fields(frm="user", to="pin_seat", kind="chat",
                                       ts="2026-10-30T10:00:00", sha="ab12",
                                       content=json.dumps("the whole body, not a preview"),
                                       meta=json.dumps({"origin": "cli", "source": "reply-verb"})))]


def test_a_message_is_found_in_full_with_its_stream_and_provenance(monkeypatch):
    client = _wire(monkeypatch, {"bifrost:inbox:pin_seat": MESSAGE})
    found = BR.find_message("1793405184749-0")
    assert found["found"], found
    rec = found["record"]
    assert rec["frm"] == "user" and rec["to"] == "pin_seat" and rec["kind"] == "chat"
    assert rec["content"] == "the whole body, not a preview", "the body must NOT be clipped here"
    assert rec["origin"] == "cli", "provenance comes from meta.origin"
    assert rec["stream"] == "bifrost:inbox:pin_seat"
    text = BR.render(found)
    assert "1793405184749-0" in text and "the whole body, not a preview" in text
    assert "provenance: cli" in text
    assert {c[0] for c in client.calls} <= {"xrange", "scan_iter"}, client.calls


def test_an_id_held_by_two_streams_is_reported_not_resolved(monkeypatch):
    """An id is unique only WITHIN a stream. Picking one silently would be a wrong answer that
    looks right -- dual-write puts the same logical packet on the work lane and the legacy inbox."""
    _wire(monkeypatch, {"bifrost:inbox:pin_seat": MESSAGE,
                        "bifrost:work:inbox:pin_seat": MESSAGE})
    found = BR.find_message("1793405184749-0")
    assert found["found"]
    assert len(found["streams"]) == 2, found["streams"]
    text = BR.render(found)
    assert "ALSO held by 1 other stream" in text, text


def test_a_missing_id_says_what_was_searched(monkeypatch):
    client = _wire(monkeypatch, {"bifrost:inbox:pin_seat": MESSAGE})
    found = BR.find_message("1700000000000-0")
    assert not found["found"]
    assert found["searched"] >= 1, "an honest NOT FOUND counts its own coverage"
    text = BR.render(found)
    assert "NOT FOUND" in text
    assert "no stream under" in text and "events --get" in text
    assert client.calls, "it must have actually looked"


def test_missing_provenance_reads_unknown_never_a_guess(monkeypatch):
    older = [("1700000000001-0", _fields(frm="discord-bot", to="pin_seat", kind="chat",
                                         content=json.dumps("no origin here")))]
    _wire(monkeypatch, {"bifrost:inbox:pin_seat": older})
    found = BR.find_message("1700000000001-0")
    assert found["record"]["origin"] == "unknown"
    assert "unknown" in BR.render(found)
    assert "(this message predates provenance stamping" in BR.render(found)


def test_an_offline_bus_is_not_an_empty_bus(monkeypatch):
    monkeypatch.setattr(BR, "_client", lambda: None)
    found = BR.find_message("1793405184749-0")
    assert not found["found"]
    assert "offline" in found["why"], found


def test_narrowing_to_one_agent_keeps_the_search_bounded(monkeypatch):
    _wire(monkeypatch, {"bifrost:inbox:pin_seat": MESSAGE})
    keys = BR.candidate_streams("pin_seat")
    assert "bifrost:inbox:pin_seat" in keys
    assert all("pin_seat" in k or "broadcast" in k for k in keys), keys


# ------------------------------------------------------------- the other half: --wake-full
def _wake_module():
    import importlib.util
    path = os.path.join(ROOT, "scripts", "bifrost_wake.py")
    spec = importlib.util.spec_from_file_location("bifrost_wake_full_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LONG_BODY = "line one of a briefing\n" + ("x" * 5000) + "\nline last of a briefing"


def test_default_wake_note_stays_a_preview(tmp_path):
    W = _wake_module()
    W.write_wake_note("pin_seat", "sess-1", [{"frm": "user", "kind": "chat", "text": LONG_BODY}],
                      tmp=str(tmp_path))
    doc = json.load(open(W.wake_note_path("pin_seat", "sess-1", str(tmp_path)), encoding="utf-8"))
    assert doc["full"] is False
    assert len(doc["msgs"][0]["snippet"]) == W.WAKE_SNIPPET
    assert "\n" not in doc["msgs"][0]["snippet"], "the preview is a single line on purpose"


def test_wake_full_keeps_the_whole_body_and_renders_every_field(tmp_path):
    """The wish's exact complaint: the preview is clipped, so the seat rebuilds the message by
    hand. With --wake-full the note carries the body and a render puts it in front of the seat."""
    W = _wake_module()
    W.write_wake_note("pin_seat", "sess-1", [{"frm": "user", "kind": "chat", "id": "17-0",
                                              "text": LONG_BODY}],
                      tmp=str(tmp_path), full=True)
    doc = json.load(open(W.wake_note_path("pin_seat", "sess-1", str(tmp_path)), encoding="utf-8"))
    assert doc["full"] is True
    assert doc["msgs"][0]["snippet"] == LONG_BODY, "the whole body, newlines and all"
    text = W.render_wake_full(doc)
    assert "WOKE BY (FULL" in text
    assert "id:    17-0" in text and "from:  user" in text and "kind: chat" in text
    assert "line last of a briefing" in text, "the END of the body must be printed, not just its head"
    assert "nothing here consumed mail" in text


def test_wake_full_still_caps_at_a_number_and_says_how_many_are_hidden(tmp_path):
    W = _wake_module()
    many = [{"frm": "peer", "kind": "chat", "text": f"m{i}"} for i in range(W.WAKE_FULL_MESSAGES + 3)]
    W.write_wake_note("pin_seat", "s", many, tmp=str(tmp_path), full=True)
    doc = json.load(open(W.wake_note_path("pin_seat", "s", str(tmp_path)), encoding="utf-8"))
    assert len(doc["msgs"]) == W.WAKE_FULL_MESSAGES
    text = W.render_wake_full(doc)
    assert "and 3 more message(s) not shown" in text


def main() -> int:
    import pytest
    return pytest.main([os.path.abspath(__file__), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
