"""Discord multi-pipe pool + single-pump-owner election pins (2026-09-03).

Daniil, verbatim: "How do we set up multiple pipes for communication with discord as one
unit so its invisible to the agents but has effectively an unlimited rate limit?"

Root cause this answers (the same incident test_discord_rate_limit_retry.py pins): four
independent seat daemons each pumped the SAME global webhook every ~10s with zero
cross-process coordination, so the SAME new message could be posted up to four times and
the aggregate call rate was ~4x actual traffic -- that is what exhausted Discord's
per-webhook rate bucket, not the fleet's real chat volume. Bounded retry (70aa9314)
absorbs the resulting 429s; it does not stop them from happening.

Two independent mechanisms, both pinned here:

  ELECTION (discord_feed.pump_if_owner) -- a short-lived TTL lock makes N daemons behave
  as ONE logical pump per beat: exactly one of them does the real xrange/post/advance-
  cursor work, the rest are no-ops. This is what "invisible to the agents, as one unit"
  actually means at the coordination layer.

  POOL (discord_bridge.webhook_urls / post_via_pool) -- multiple independent webhooks
  pointed at the SAME channel are separate rate-limit buckets; pooling N of them multiplies
  the sustained ceiling by N, and a pipe that is still 429 after its own retry budget hands
  off to the NEXT pipe instead of waiting out the same bucket -- this is the "effectively
  unlimited" half.

Run:  py -m pytest tests/test_discord_webhook_pool.py -v
"""

from __future__ import annotations

import os
import sys

import pytest
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import discord_bridge as DB  # noqa: E402
from core.comm import discord_feed as F  # noqa: E402


# ============================================================================ webhook_urls()

def test_single_pipe_is_unchanged_when_only_one_is_configured(monkeypatch):
    """Calibration: the common case (one webhook) must behave exactly as before."""
    monkeypatch.delenv("AKASHIC_DISCORD_WEBHOOKS", raising=False)
    monkeypatch.setenv("AKASHIC_DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1/g")
    assert DB.webhook_urls() == ["https://discord.com/api/webhooks/1/g"]


def test_env_list_overrides_with_multiple_pipes(monkeypatch):
    monkeypatch.setenv("AKASHIC_DISCORD_WEBHOOKS",
                       "https://discord.com/api/webhooks/1/a,"
                       "https://discord.com/api/webhooks/2/b\n"
                       "https://discord.com/api/webhooks/3/c")
    urls = DB.webhook_urls()
    assert urls == ["https://discord.com/api/webhooks/1/a",
                    "https://discord.com/api/webhooks/2/b",
                    "https://discord.com/api/webhooks/3/c"], (
        "comma AND newline separated, blanks dropped, order preserved")


def test_no_pipes_configured_is_an_empty_list_not_an_error(monkeypatch, tmp_path):
    monkeypatch.delenv("AKASHIC_DISCORD_WEBHOOKS", raising=False)
    monkeypatch.delenv("AKASHIC_DISCORD_WEBHOOK", raising=False)
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(tmp_path))
    assert DB.webhook_urls() == []


def test_vault_pool_slots_are_read_in_order(monkeypatch, tmp_path):
    monkeypatch.delenv("AKASHIC_DISCORD_WEBHOOKS", raising=False)
    monkeypatch.delenv("AKASHIC_DISCORD_WEBHOOK", raising=False)
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(tmp_path))
    (tmp_path / "discord_webhook.url").write_text(
        "https://discord.com/api/webhooks/1/g", encoding="utf-8")
    (tmp_path / "discord_webhook_3.url").write_text(
        "https://discord.com/api/webhooks/3/c", encoding="utf-8")
    # slot 2 deliberately absent -- a gap must not break the pool, just shrink it
    assert DB.webhook_urls() == ["https://discord.com/api/webhooks/1/g",
                                 "https://discord.com/api/webhooks/3/c"]


# ============================================================================ post_via_pool()

class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code


def _http_429():
    e = requests.HTTPError("429")
    e.response = _Resp(429)
    return e


def test_first_healthy_pipe_wins_immediately():
    calls = []

    def poster(url, content):
        calls.append(url)
        return "ok"

    out = DB.post_via_pool(["p1", "p2"], "hi", poster)
    assert out == "ok"
    assert calls == ["p1"], "no need to touch p2 when p1 succeeds"


def test_a_429_exhausted_pipe_hands_off_to_the_next_one():
    calls = []

    def poster(url, content):
        calls.append(url)
        if url == "p1":
            raise _http_429()
        return "ok-from-p2"

    out = DB.post_via_pool(["p1", "p2"], "hi", poster)
    assert out == "ok-from-p2"
    assert calls == ["p1", "p2"], (
        "a pipe still 429 after its own retry budget must hand off, not block the beat")


def test_all_pipes_429_raises_the_last_429_not_a_generic_error():
    def poster(url, content):
        raise _http_429()

    with pytest.raises(requests.HTTPError):
        DB.post_via_pool(["p1", "p2"], "hi", poster)


def test_a_non_429_failure_is_never_hopped_it_is_a_real_outage():
    calls = []

    def poster(url, content):
        calls.append(url)
        raise RuntimeError("dns died")

    with pytest.raises(RuntimeError):
        DB.post_via_pool(["p1", "p2"], "hi", poster)
    assert calls == ["p1"], (
        "hopping past a non-429 failure would mask a real outage as a rate-limit hiccup")


def test_empty_pool_refuses_loudly():
    with pytest.raises(RuntimeError):
        DB.post_via_pool([], "hi", lambda u, c: "unreached")


# ============================================================================ pump_if_owner()

class _FakeClient:
    def __init__(self):
        self.streams = {"bifrost:broadcast": [], "bifrost:inbox:claude": []}
        self.hash: dict = {}

    def hgetall(self, key):
        return dict(self.hash)

    def hset(self, key, field, value):
        self.hash[field] = value

    def xrevrange(self, key, count=1):
        return list(reversed(self.streams.get(key, [])))[:count]

    def xrange(self, key, min="-", count=100):
        s = self.streams.get(key, [])
        if min.startswith("("):
            floor = min[1:]
            return [e for e in s if e[0] > floor][:count]
        return s[:count]


class _FakeBus:
    ns = "bifrost"

    def __init__(self, client):
        self._client = client

    def known_agents(self):
        return ["claude"]

    def _inbox_key(self, agent):
        return f"bifrost:inbox:{agent}"


@pytest.fixture()
def wired(monkeypatch):
    monkeypatch.setenv("AKASHIC_DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1/g")
    monkeypatch.setenv("AKASHIC_DISCORD_FORUM_WEBHOOK", "https://discord.com/api/webhooks/2/f")
    return _FakeBus(_FakeClient())


def test_the_election_loser_never_calls_pump(wired, monkeypatch):
    """This is the whole mechanism: a daemon that loses the beat must not touch the
    cursor or the webhook at all -- not 'pump but skip', genuinely never called."""
    from core.comm import runner_lock
    monkeypatch.setattr(runner_lock, "acquire", lambda *a, **k: False)
    called = {"n": 0}
    monkeypatch.setattr(F, "pump", lambda *a, **k: called.__setitem__("n", called["n"] + 1))

    out = F.pump_if_owner(wired)

    assert called["n"] == 0, "a losing daemon must never invoke the real pump"
    assert out.ok, "losing the election is a normal beat, not a failure"


def test_the_election_winner_pumps_and_releases(wired, monkeypatch):
    from core.comm import runner_lock
    monkeypatch.setattr(runner_lock, "acquire", lambda *a, **k: True)
    released = []
    monkeypatch.setattr(runner_lock, "release", lambda key, token: released.append(key))

    out = F.pump_if_owner(wired)

    assert out.ok
    assert released == ["discord-pump"], (
        "the winner must release the lock so the NEXT beat (any daemon) can compete "
        "again, rather than squatting the lock for its full TTL")


def test_the_winner_releases_even_if_pump_itself_raises(wired, monkeypatch):
    from core.comm import runner_lock
    monkeypatch.setattr(runner_lock, "acquire", lambda *a, **k: True)
    released = []
    monkeypatch.setattr(runner_lock, "release", lambda key, token: released.append(key))

    def _boom(*a, **k):
        raise RuntimeError("mid-pump explosion")

    monkeypatch.setattr(F, "pump", _boom)

    with pytest.raises(RuntimeError):
        F.pump_if_owner(wired)
    assert released == ["discord-pump"], (
        "a crash mid-pump must not leave the lock held for the daemon's own process "
        "lifetime -- release belongs in a finally, not after a successful return")
