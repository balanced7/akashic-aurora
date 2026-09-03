"""Discord outbound rate-limit retry pins (2026-09-03 reachability incident).

Root cause: four independent daemons (claude, deepseek, kimi, sol) each pump the SAME
global webhook every ~10s with zero cross-process coordination. Under fleet chatter this
blew through Discord's per-webhook rate bucket (live 429s: kimi/sol/deepseek, 2026-09-01
through 2026-09-02, event:events:discord:raw:1788398239408-0 et al). Every `_default_post`
in this house raised on the first 429 and the caller (discord_feed.pump) treats a failed
post as skip-never-retry -- the cursor still advances, so the reply was gone forever. This
is the mechanism behind "I messaged multiple agents and none responded" with a healthy
gateway, a healthy daemon, and a bus reply that really was sent.

Run:  py -m pytest tests/test_discord_rate_limit_retry.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm.discord_bridge import post_with_rate_limit_retry  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code, retry_after=None):
        self.status_code = status_code
        self.headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
        self._retry_after = retry_after

    def json(self):
        if self.status_code == 429:
            return {"retry_after": self._retry_after}
        return {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_retries_on_429_then_succeeds():
    responses = [_FakeResponse(429, retry_after=0.2), _FakeResponse(200)]
    calls = {"n": 0}
    slept = []

    def post_fn():
        r = responses[calls["n"]]
        calls["n"] += 1
        return r

    out = post_with_rate_limit_retry(post_fn, sleep=slept.append)
    assert out.status_code == 200, "must return the eventual success, not the first 429"
    assert calls["n"] == 2, "exactly one retry for one 429"
    assert slept == [pytest.approx(0.25)], (
        "must sleep Discord's OWN reported retry_after (+ small pad), not a guess")


def test_gives_up_after_max_retries_and_still_returns_the_429():
    calls = {"n": 0}

    def post_fn():
        calls["n"] += 1
        return _FakeResponse(429, retry_after=0.01)

    out = post_with_rate_limit_retry(post_fn, sleep=lambda _s: None)
    assert out.status_code == 429, (
        "sustained rate-limiting must still surface as a real failure -- bounded "
        "retry absorbs a collision, it must never mask an actual outage")
    assert calls["n"] == 4, "1 initial attempt + 3 retries, then stop"


def test_non_429_failure_is_not_retried():
    calls = {"n": 0}

    def post_fn():
        calls["n"] += 1
        return _FakeResponse(500)

    out = post_with_rate_limit_retry(post_fn, sleep=lambda _s: None)
    assert out.status_code == 500 and calls["n"] == 1, (
        "a real server error is not a coordination collision -- retrying it here "
        "would just turn a fast failure into a slow one")


def test_success_on_first_try_never_sleeps():
    slept = []
    out = post_with_rate_limit_retry(lambda: _FakeResponse(200), sleep=slept.append)
    assert out.status_code == 200 and not slept
