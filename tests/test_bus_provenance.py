"""Provenance pins: a message says which door made it, or says it does not know.

THE WISH (docs/WISHLIST.md, 2026-10-30, phase 3):
    "Bus messages carry provenance (discord / runner / cli / mcp), set at the door that creates
     them, and shown by `bus read` and bifrost-sync --json. Old messages without the field read
     unknown, never a guess."

Four clauses, and every one of them is a promise that can be kept or broken silently, so each has
a pin:

  1. STAMPED AT CREATION -- `Bus._emit` (the funnel every send path already passes through) fills
     meta.origin, so a door cannot forget and a later reader cannot have to infer.
  2. DECLARED BEATS INFERRED -- an explicit meta["origin"] and a declared AKASHIC_DOOR both win
     over the process-shape fallback, because the door that knows is the door that should say.
  3. AN EXISTING ORIGIN IS NEVER OVERWRITTEN -- otherwise the field becomes a function of the last
     writer, which is the same as having no field.
  4. UNKNOWN IS AN ANSWER, NOT A DEFAULT -- no declaration + no recognisable process reads
     `unknown`; it never reads `cli` because that is "the door I know best".

The fourth clause is the one with the scar tissue: this house has repeatedly paid for confident
answers produced by a default (`did this come from Discord?` answered by inference is precisely
the archaeology the wish asks to end).

Run: py tests/test_bus_provenance.py   (or via pytest)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import provenance as P                                       # noqa: E402


def _clean_env(monkeypatch):
    for name in P._ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _no_process_rung(monkeypatch):
    """Isolate the PROCESS rung, which is process-global by design: `ai_setup_mcp` in
    sys.modules and the real argv belong to whatever ran this suite. Without this, a test that
    asks "is nothing-declared UNKNOWN?" would be answering a question about the test runner --
    the first version of this file passed alone and failed inside the whole suite for exactly
    that reason."""
    monkeypatch.setattr(P, "_from_process", lambda: None)


# ------------------------------------------------------------------ 4. unknown is an answer
def test_nothing_declared_and_nothing_recognisable_reads_unknown(monkeypatch):
    _clean_env(monkeypatch)
    _no_process_rung(monkeypatch)
    assert P.detect() == P.UNKNOWN
    assert P.of({}) == P.UNKNOWN
    assert P.of({"source": "discord"}) == P.UNKNOWN, \
        "a `source` key is not the origin field -- inferring one from the other is a guess"


def test_an_unrecognised_declaration_is_not_silently_accepted(monkeypatch):
    """A seventh spelling would make 'did this come from Discord?' a question with two answers."""
    _clean_env(monkeypatch)
    _no_process_rung(monkeypatch)
    monkeypatch.setenv("AKASHIC_DOOR", "carrier-pigeon")
    assert P.detect() == P.UNKNOWN
    assert P.stamps({})[P.KEY] == P.UNKNOWN


# ------------------------------------------------------------------ 2. declared beats inferred
def test_a_declared_door_wins_over_the_process_shape(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(P, "_from_process", lambda: "runner")   # e.g. bifrost_runner_kimi.py
    assert P.detect() == "runner"
    monkeypatch.setenv("AKASHIC_DOOR", "mcp")
    assert P.detect() == "mcp", "the door that declares itself beats the script it happens to be in"


def test_the_process_rung_reads_a_script_basename(monkeypatch):
    """The fallback exists for doors that declare nothing; it reads the BASENAME, not the path.

    `ai_setup_mcp` is temporarily removed from sys.modules for this one: the module-shape rung
    answers first by design, and in a suite that imported the MCP server it would answer for
    everything -- which is correct in production and useless as a test of the other rung."""
    _clean_env(monkeypatch)
    monkeypatch.delitem(sys.modules, "ai_setup_mcp", raising=False)
    for argv0, expect in (("/x/scripts/bifrost_runner_kimi.py", "runner"),
                          ("C:/w/scripts/bifrost_runner_discord.py", "discord"),
                          ("/x/scripts/discord_gateway.py", "discord"),
                          ("/x/agent_cli.py", "cli"),
                          ("/x/something_else.py", None)):
        monkeypatch.setattr(sys, "argv", [argv0])
        assert P._from_process() == expect, (argv0, P._from_process())


def test_an_explicit_meta_origin_wins_over_everything(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AKASHIC_DOOR", "mcp")
    got = P.stamps({"origin": "discord", "lane": "seat-channel"})
    assert got["origin"] == "discord"
    assert got["lane"] == "seat-channel", "stamping may not disturb any other meta field"


# ------------------------------------------------------------------ 3. never overwritten
def test_an_existing_origin_is_never_overwritten(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AKASHIC_DOOR", "cli")
    assert P.stamps({"origin": "runner"})["origin"] == "runner"
    # case-insensitive read, canonical spelling preserved
    assert P.of({"Origin": "DISCORD"}) == "discord"


def test_stamping_is_idempotent(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AKASHIC_DOOR", "runner")
    once = P.stamps({})
    twice = P.stamps(once)
    assert once == twice


# ------------------------------------------------------------------ 1. the bus actually stamps
def test_the_send_funnel_stamps_every_packet(monkeypatch):
    """`Bus._emit` is the ONE funnel send/send_reply/broadcast all pass through -- pinning it
    there is what makes 'a door cannot forget' true rather than aspirational."""
    from core.comm import bus as bus_mod
    _clean_env(monkeypatch)
    monkeypatch.setenv("AKASHIC_DOOR", "runner")

    captured = {}

    class _FakeClient:
        def xadd(self, key, fields, **kw):
            captured.setdefault("packs", []).append((key, fields))
            return f"17000000{len(captured['packs']):05d}-0"

        def set(self, *a, **kw):
            return True

        def hset(self, *a, **kw):
            return 1

        def expire(self, *a, **kw):
            return 1

        def exists(self, *a, **kw):
            return 0

    b = bus_mod.Bus("pin_sender", client=_FakeClient())
    mid = b.send("pin_target", "chat", "hello", meta={"note": "kept"})
    assert mid, "the send must actually go out"
    metas = []
    for _key, fields in captured.get("packs") or []:
        raw = fields.get("meta")
        if raw:
            import json
            metas.append(json.loads(raw))
    assert metas, captured
    assert any(m.get("origin") == "runner" for m in metas), metas
    assert any(m.get("note") == "kept" for m in metas), "existing meta must survive the stamp"


def main() -> int:
    import pytest
    return pytest.main([os.path.abspath(__file__), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
