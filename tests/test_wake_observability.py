"""S5 wake-observability pins (T423, 2026-10-01). Daniel's ladder property (5): doctor shows
per seat who launched the listener, since when, and what wakes cost; and PAGES when a session
that is demonstrably alive has had no listener that can start a turn.

Hermetic: seats, origin sidecars and activity markers in tmp_path; receipts under tmp_path;
pid liveness injected. The grading is PURE (wake_findings) so these pins run without Redis.
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import wake_seat as ws

AGENT = "tobs"
NOW = 1_700_000_000.0


def _seat(tmp, sid, pid=4242, origin=None, age_s=600):
    p = ws.seat_path(AGENT, sid, str(tmp))
    with open(p, "w") as f:
        f.write(str(pid))
    os.utime(p, (NOW - age_s, NOW - age_s))
    if origin:
        ws.write_origin(AGENT, sid, origin, pid, str(tmp))


def _alive(tmp, sid, age_min):
    p = ws.activity_marker_path(AGENT, sid, str(tmp))
    with open(p, "w") as f:
        f.write(str(NOW - age_min * 60))          # the marker's CONTENT is the timestamp


def _find(tmp, **kw):
    return ws.wake_findings([AGENT], tmp=str(tmp), now=NOW, receipts_base=str(tmp / "r"),
                            pid_probe=lambda p: True, **kw)


def _states(fs):
    return [(f["state"], f["grade"]) for f in fs]


def test_reachable_seat_is_a_dashboard_line_with_origin_and_since(tmp_path):
    _seat(tmp_path, "s1", origin=ws.ORIGIN_HARNESS)
    _alive(tmp_path, "s1", 20)
    fs = _find(tmp_path)
    assert ("wake_reachable", "dashboard") in _states(fs)
    line = next(f["line"] for f in fs if f["state"] == "wake_reachable")
    assert "armed-harness since" in line and "alive 20m ago" in line
    assert not any(f["grade"] == "page" for f in fs)


def test_alive_session_with_daemon_only_seat_pages_after_grace(tmp_path):
    _seat(tmp_path, "s2", origin=ws.ORIGIN_DAEMON)
    _alive(tmp_path, "s2", 25)
    fs = _find(tmp_path, arm_hint=lambda a, s: f"ARM {a} {s}")
    page = [f for f in fs if f["grade"] == "page"]
    assert len(page) == 1 and page[0]["state"] == "wake_deaf"
    assert "armed-daemon" in page[0]["line"] and "DEAF" in page[0]["line"]
    assert page[0]["drill"] == "ARM tobs s2"


def test_alive_session_with_no_seat_at_all_pages(tmp_path):
    _alive(tmp_path, "s3", 30)                      # marker only, no seat file
    fs = _find(tmp_path)
    assert [f["state"] for f in fs if f["grade"] == "page"] == ["wake_deaf"]
    assert "unarmed" in next(f["line"] for f in fs if f["state"] == "wake_deaf")


def test_unarmed_inside_grace_is_dashboard_not_page(tmp_path):
    _alive(tmp_path, "s4", 3)
    fs = _find(tmp_path)
    assert ("wake_unarmed_grace", "dashboard") in _states(fs)
    assert not any(f["grade"] == "page" for f in fs)


def test_stale_session_is_the_janitors_not_a_page(tmp_path):
    _seat(tmp_path, "s5", origin=ws.ORIGIN_DAEMON)
    _alive(tmp_path, "s5", 180)
    fs = _find(tmp_path)
    assert ("wake_seat_stale", "dashboard") in _states(fs)
    assert not any(f["grade"] == "page" for f in fs)


def test_seat_without_any_activity_marker_is_not_a_finding(tmp_path):
    _seat(tmp_path, "s6", origin=ws.ORIGIN_DAEMON)   # no .alive ever: no evidence of a session
    fs = _find(tmp_path)
    assert not any(f["state"] in ("wake_deaf", "wake_unarmed_grace") for f in fs)


def test_cost_line_reads_the_receipts(tmp_path):
    base = str(tmp_path / "r")
    ws.append_wake_receipt(AGENT, {"ts": NOW - 100, "outcome": "woke", "below_floor": 2}, base)
    ws.append_wake_receipt(AGENT, {"ts": NOW - 200, "outcome": "quiet", "below_floor": 0}, base)
    fs = _find(tmp_path)
    cost = next(f["line"] for f in fs if f["state"] == "wake_cost")
    assert "wakes 24h 2 (1 with mail, 1 quiet" in cost and "2 held below floor" in cost


def test_agents_with_seats_and_wake_tag(tmp_path):
    _seat(tmp_path, "s7", pid=os.getpid(), origin=ws.ORIGIN_HARNESS)   # a pid that is alive
    assert ws.agents_with_seats(str(tmp_path)) == [AGENT]
    assert ws.wake_tag(AGENT, "s7", str(tmp_path)) == "armed-harness"
    assert ws.wake_tag(AGENT, "nope", str(tmp_path)) == "unarmed"
