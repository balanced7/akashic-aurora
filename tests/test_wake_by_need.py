"""S3 wake-by-need pins (T421, 2026-10-01). Daniel: "wake decides by need, not by kind."

Every wake is a full model turn. Before S3 the harness listener admitted everything
(floor AMBIENT), so quiet cycles and peers' chatter each cost one. These pins hold:
  - the standby's floor resolves flag > env > 2 and REACHES the listener's argv;
  - at floor 2 an ambient directed chat from a peer is held (and confessed), while an
    operator message and a directed ask still wake;
  - the operator is never subject to the settle window; a peer burst within the window
    is one wake carrying all of it;
  - every listener exit writes a receipt (woke / quiet / cycled) that the summary counts.
Hermetic: the fake bus from test_t073_wake_longlived.py, receipts in tmp_path.
"""
import json
import os
import sys
import time as real_time
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli
from core.comm import wake_seat as ws
from scripts import bifrost_wake as bw


class FakeClock:
    def __init__(self, start=1_000_000.0):
        self.now = start

    def time(self):
        return self.now


class FakeApi:
    """wake_block advances the fake clock one chunk and serves scripted mail by time."""
    online_now = True

    def __init__(self, clock, chunk_s, schedule=None):
        self.clock, self.chunk_s = clock, chunk_s
        self.schedule = sorted(schedule or [], key=lambda x: x[0])   # [(at, [msgs])]

    def online(self):
        pass

    def wake_block(self, timeout_ms=0):
        step = min(self.chunk_s, max(0.001, timeout_ms / 1000.0)) if timeout_ms else self.chunk_s
        self.clock.now += step
        due = [m for at, ms in self.schedule if at <= self.clock.now for m in ms]
        self.schedule = [(at, ms) for at, ms in self.schedule if at > self.clock.now]
        return due


def _msg(kind="chat", frm="kimi", to="claude", text="hi"):
    return SimpleNamespace(kind=kind, frm=frm, to=to, content=text, meta={})


@pytest.fixture()
def seat(tmp_path, monkeypatch):
    monkeypatch.setattr(bw.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setenv("AKASHIC_WAKE_RECEIPTS_DIR", str(tmp_path / "receipts"))
    monkeypatch.setenv("AKASHIC_OPERATOR_IDS", "daniil")
    monkeypatch.delenv("BIFROST_WAKE_SETTLE_S", raising=False)
    p = os.path.join(str(tmp_path), "bifrost_wake_claude_s1.pid")
    with open(p, "w") as f:
        f.write("4242")
    return p


def _run(seat, clock, api, min_tier, deadline=600, monkeypatch=None):
    monkeypatch.setattr(bw.time, "time", clock.time)
    monkeypatch.setattr(bw, "say_seen_at_fire", lambda *a, **k: 0, raising=False)
    return bw.watch("claude", deadline, 10_000, api=api, hb_path=seat, my_pid=4242,
                    session_id="s1", min_tier=min_tier)


def _receipts(tmp_path):
    p = ws.wake_receipts_path("claude", str(tmp_path / "receipts"))
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []


# ---------------------------------------------------------------- the floor reaches the child
def test_standby_floor_resolves_flag_env_default(monkeypatch):
    monkeypatch.delenv("BIFROST_WAKE_MIN_TIER", raising=False)
    assert agent_cli.standby_min_tier() == 2
    monkeypatch.setenv("BIFROST_WAKE_MIN_TIER", "3")
    assert agent_cli.standby_min_tier() == 3
    assert agent_cli.standby_min_tier(0) == 0                 # flag beats env
    monkeypatch.setenv("BIFROST_WAKE_MIN_TIER", "garbage")
    assert agent_cli.standby_min_tier() == 2                 # unreadable -> default, never 3
    assert agent_cli.standby_min_tier(9) == 3                # clamped to the ladder


def test_standby_listener_argv_carries_the_floor_and_session():
    argv = agent_cli.standby_listener_argv("claude", "sid-1", 2)
    assert argv[1].endswith("bifrost_wake.py")
    assert "--min-tier" in argv and argv[argv.index("--min-tier") + 1] == "2"
    assert "--session" in argv and argv[argv.index("--session") + 1] == "sid-1"


# ---------------------------------------------------------------- floor 2 semantics
def test_floor_two_holds_ambient_peer_broadcast_and_confesses(seat, tmp_path, monkeypatch, capsys):
    clock = FakeClock()
    # a peer BROADCAST completion passes wake_worthy (kind allowlist) and ranks AMBIENT (to != me);
    # a peer chat never reaches the floor: chat is not in WAKE_WORTHY_KINDS at all
    api = FakeApi(clock, 10, schedule=[(clock.now + 20, [_msg("completion", "kimi", "*")])])
    rc = _run(seat, clock, api, min_tier=2, deadline=120, monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert rc == 0 and "BIFROST WAKE -- messages" not in out
    assert "held below tier floor 2" in out
    r = _receipts(tmp_path)
    assert r and r[-1]["outcome"] in ("quiet", "cycled") and r[-1]["below_floor"] == 1


def test_floor_two_wakes_on_operator_and_on_directed_ask(seat, tmp_path, monkeypatch, capsys):
    clock = FakeClock()
    api = FakeApi(clock, 10, schedule=[(clock.now + 20, [_msg("chat", "daniil", "claude")])])
    assert _run(seat, clock, api, min_tier=2, deadline=600, monkeypatch=monkeypatch) == 0
    assert "BIFROST WAKE -- messages" in capsys.readouterr().out
    clock2 = FakeClock(2_000_000.0)
    api2 = FakeApi(clock2, 10, schedule=[(clock2.now + 20, [_msg("handoff", "kimi", "claude")])])
    assert _run(seat, clock2, api2, min_tier=2, deadline=600, monkeypatch=monkeypatch) == 0
    assert "BIFROST WAKE -- messages" in capsys.readouterr().out
    r = _receipts(tmp_path)
    assert [x["outcome"] for x in r[-2:]] == ["woke", "woke"]
    assert r[-2]["tiers"] == [0] and r[-1]["tiers"] == [1]


# ---------------------------------------------------------------- settle window
def test_operator_mail_never_waits_for_the_settle_window(seat, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BIFROST_WAKE_SETTLE_S", "30")
    clock = FakeClock()
    api = FakeApi(clock, 10, schedule=[(clock.now + 10, [_msg("chat", "daniil", "claude")]),
                                       (clock.now + 25, [_msg("handoff", "kimi", "claude")])])
    t0 = clock.now
    _run(seat, clock, api, min_tier=2, deadline=600, monkeypatch=monkeypatch)
    assert clock.now - t0 <= 10 + 1e-6            # exited on the operator, no settle
    assert _receipts(tmp_path)[-1]["mail"] == 1


def test_peer_burst_within_settle_window_is_one_wake(seat, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("BIFROST_WAKE_SETTLE_S", "30")
    clock = FakeClock()
    api = FakeApi(clock, 10, schedule=[(clock.now + 10, [_msg("handoff", "kimi", "claude", "a")]),
                                       (clock.now + 18, [_msg("handoff", "sol", "claude", "b")]),
                                       (clock.now + 26, [_msg("request", "deepseek", "claude", "c")])])
    _run(seat, clock, api, min_tier=2, deadline=600, monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    r = _receipts(tmp_path)[-1]
    assert r["outcome"] == "woke" and r["mail"] == 3, r
    assert out.count('"frm"') == 3


# ---------------------------------------------------------------- receipts + summary
def test_receipt_summary_counts_window(tmp_path):
    base = str(tmp_path / "r")
    now = real_time.time()
    ws.append_wake_receipt("claude", {"ts": now - 10, "outcome": "woke", "below_floor": 0}, base)
    ws.append_wake_receipt("claude", {"ts": now - 20, "outcome": "quiet", "below_floor": 4}, base)
    ws.append_wake_receipt("claude", {"ts": now - 30, "outcome": "cycled", "below_floor": 0}, base)
    ws.append_wake_receipt("claude", {"ts": now - 90_000, "outcome": "woke", "below_floor": 0}, base)
    s = ws.wake_receipts_summary("claude", since_s=3600, now=now, base=base)
    assert s == {"wakes": 3, "with_mail": 1, "quiet": 1, "cycled": 1, "held_below_floor": 4}
    assert ws.wake_receipts_summary("nobody", base=base)["wakes"] == 0


def test_receipts_never_touch_the_machine_ledger_under_pytest(tmp_path, monkeypatch):
    """The listener pins run watch() on a fake clock; without a named directory the receipt
    must be refused, not written to state/wake-receipts/ with a 1970 timestamp."""
    monkeypatch.delenv("AKASHIC_WAKE_RECEIPTS_DIR", raising=False)
    assert os.environ.get("PYTEST_CURRENT_TEST")
    assert ws.append_wake_receipt("tnobody", {"outcome": "woke"}) is False
    assert ws.append_wake_receipt("tnobody", {"outcome": "woke"}, base=str(tmp_path)) is True
