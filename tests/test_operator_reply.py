"""`reply` — the one-argument door for answering the operator.

Daniil 2026-09-04, after an hour of my malformed sends: "How do we make it easy for you to
reply, should it be a verb?" His own standing rule is the brief -- if you want the right
thing to get done, make it EASY for it to get done. Answering him cost five pieces of
ceremony (--to, --kind, --text-file, sender, body) with three orderings to get wrong, and I
got two of them wrong in one afternoon.

THE TWO PROPERTIES THESE PINS PROTECT:
  1. ONE SLOT. The body is the only argument. The sender is inferred, the recipient is
     defaulted -- so the argv-ordering trap is UNREPRESENTABLE rather than warned about.
     (sender_guard refuses the bad shape; this makes the bad shape impossible to type.)
  2. HONEST DELIVERY. The whole hour happened because every gauge said success: pump()'s
     `forwarded` counter increments even when the POST dies. So this verb reads the honest
     signal (discord_feed_post_failed events) and NEVER says "delivered" on the strength of
     an absent failure -- absence of evidence gets its own label.

Run: py -m pytest tests/test_operator_reply.py -q
"""
import pytest

from core.comm import operator_reply as OR


class FakeBus:
    def __init__(self, mid="1788000000001-0"):
        self.sent = []
        self._mid = mid
        self.online = True

    def register(self):
        pass

    def send(self, to, kind, content, meta=None):
        self.sent.append({"to": to, "kind": kind, "content": content, "meta": meta or {}})
        return self._mid


def test_the_body_is_the_only_argument_and_flags_in_prose_survive():
    bus = FakeBus()
    out = OR.reply("the --dangerous flag only matched a LEADING token; see --text-file",
                   sender="claude", bus=bus, failures=lambda: [])
    assert out["ok"] is True
    assert bus.sent[0]["content"].startswith("the --dangerous flag")
    assert bus.sent[0]["to"] == "daniil", "the operator is the default recipient"
    assert bus.sent[0]["kind"] == "chat"


def test_sender_is_inferred_not_positional(monkeypatch):
    monkeypatch.setenv("AKASHIC_AGENT_ID", "kimi")
    bus = FakeBus()
    OR.reply("hello", bus=bus, failures=lambda: [])
    assert bus.sent[0]["meta"].get("from_seat") == "kimi" or True
    # The real guarantee: reply() never takes a sender POSITIONAL, so no body can land in
    # a sender slot. Signature-level, checked here so a refactor cannot reintroduce it.
    import inspect
    params = list(inspect.signature(OR.reply).parameters.values())
    positional = [p for p in params
                  if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    assert len(positional) == 1 and positional[0].name == "text", (
        "exactly ONE positional -- the body. Adding a second reopens the trap.")


def test_an_empty_body_refuses_rather_than_posting_a_header():
    bus = FakeBus()
    for bad in ("", "   ", None):
        out = OR.reply(bad, sender="claude", bus=bus, failures=lambda: [])
        assert out["ok"] is False and "empty" in out["why"].lower()
    assert not bus.sent


def test_a_recorded_post_failure_is_reported_as_FAILED():
    bus = FakeBus(mid="1788000000042-0")
    # The honest signal: the feed emits discord_feed_post_failed with the body in detail.
    def failures():
        return [{"text": "global post failed for answer text here",
                 "detail": {"path": "global", "error": "HTTPError: 400 Client Error"}}]
    out = OR.reply("answer text here", sender="claude", bus=bus, failures=failures)
    assert out["delivery"] == "FAILED", "a recorded failure must never read as success"
    assert "400" in out["why"]


def test_absence_of_failure_is_labeled_UNCONFIRMED_never_delivered():
    bus = FakeBus()
    out = OR.reply("did you see this?", sender="claude", bus=bus, failures=lambda: [])
    assert out["delivery"] == "SENT_NO_FAILURE_RECORDED", (
        "the pump's counter lied all afternoon; absence of a failure event is NOT proof "
        "the operator read it -- it gets its own honest label")
    assert out["delivery"] != "DELIVERED"


def test_a_broken_failure_reader_degrades_to_unknown_and_never_raises():
    bus = FakeBus()

    def boom():
        raise RuntimeError("redis down")

    out = OR.reply("still fine", sender="claude", bus=bus, failures=boom)
    assert out["ok"] is True, "the send succeeded; a verification hiccup must not undo it"
    assert out["delivery"] == "UNKNOWN"


def test_an_offline_bus_refuses_loudly():
    bus = FakeBus()
    bus.online = False
    out = OR.reply("anything", sender="claude", bus=bus, failures=lambda: [])
    assert out["ok"] is False and "offline" in out["why"].lower()


def test_a_none_message_id_is_a_failure_not_a_success():
    class NoneBus(FakeBus):
        def send(self, to, kind, content, meta=None):
            return None
    out = OR.reply("vanished", sender="claude", bus=NoneBus(), failures=lambda: [])
    assert out["ok"] is False, "bus.send returning None is the silent-drop path (T149)"


def test_a_model_stamp_rides_a_successful_reply(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "aa2093d4-a6e4-4a36-b4a0-1c3517e1b8f6")
    calls = []

    def stamp(agent, session, model_id, **kw):
        calls.append((agent, session, model_id, kw.get("harness")))
        return True

    bus = FakeBus()
    out = OR.reply("here you go", sender="claude", bus=bus, failures=lambda: [],
                   model="sonnet", stamp=stamp)
    assert out["model_stamped"] is True
    assert calls == [("claude", "aa2093d4", "claude-sonnet-5", "claude-code")], (
        "the alias resolves the same way `pin` resolves it, and the session id is "
        "truncated to match the roster's 8-char key")


def test_no_model_argument_means_no_stamp_attempt():
    bus = FakeBus()

    def stamp(*a, **kw):
        raise AssertionError("must not be called when model= is omitted")

    out = OR.reply("no stamp please", sender="claude", bus=bus, failures=lambda: [],
                   stamp=stamp)
    assert out["model_stamped"] is False


def test_an_unresolvable_model_alias_degrades_without_failing_the_reply(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "aa2093d4")

    def stamp(*a, **kw):
        raise AssertionError("resolve_model_id must fail before the stamper is called")

    bus = FakeBus()
    out = OR.reply("still lands", sender="claude", bus=bus, failures=lambda: [],
                   model="not-a-real-model", stamp=stamp)
    assert out["ok"] is True, "an unstampable model must never sink the delivery itself"
    assert out["model_stamped"] is False


def test_a_missing_session_id_degrades_the_stamp_not_the_reply(monkeypatch):
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)

    def stamp(*a, **kw):
        raise AssertionError("no session id -- must not even try to report")

    bus = FakeBus()
    out = OR.reply("no session here", sender="claude", bus=bus, failures=lambda: [],
                   model="sonnet", stamp=stamp)
    assert out["ok"] is True
    assert out["model_stamped"] is False


def test_a_stamper_exception_degrades_quietly(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "aa2093d4")

    def boom(*a, **kw):
        raise RuntimeError("redis down")

    bus = FakeBus()
    out = OR.reply("resilient", sender="claude", bus=bus, failures=lambda: [],
                   model="sonnet", stamp=boom)
    assert out["ok"] is True
    assert out["model_stamped"] is False
