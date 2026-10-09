"""The floor's first real sensor: undeliverable directed mail (spec d622ac s4, entry 1; Daniel 2026-10-09: "keep
building out the one world ui").

Navi's entry, verbatim in the spec: undeliverable directed mail -- mail to an absent seat is MORE urgent, never ghost
mail. The sensor crosses the roster (who has a live or stale incarnation) with the shadow mailbox (core.comm.mailbox:
what is addressed to each agent, and whether it was handled). It is THREE-state like every floor sensor:
fired (an absent seat holds unhandled directed obligations), clear (both reads worked and nothing qualifies), and
unavailable (a read failed -- named, never reported as clear). Its CLEAR detail states its own bound: an agent the
roster has never seen is not scanned.

Every source is injected here, so none of these touch a live Redis.
"""
from __future__ import annotations

import pytest

floor = pytest.importorskip("core.oneworld.floor")
sensors = pytest.importorskip("core.oneworld.sensors")

NOW = 1_800_000_000.0  # a fixed "now" in epoch seconds


def _iso(ago_s):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(NOW - ago_s, tz=timezone.utc).isoformat()


def _roster(*rows):
    return lambda: [{"agent": a, "state": s} for a, s in rows]


def _mail(by_agent):
    def query(ns, agent):
        return {"available": True, "entries": by_agent.get(agent, [])}
    return query


def _entry(kind, tier, ago_s=3600.0, frm="deepseek"):
    return {"kind": kind, "tier": tier, "ts": _iso(ago_s), "frm": frm}


def sense(roster, mail):
    return sensors.undeliverable_mail(roster_rows=roster, mailbox_query=mail, now_s=NOW)


def test_an_absent_seat_holding_an_unhandled_request_fires_and_says_who_what_and_how_old():
    sig = sense(_roster(("sol", "DEAD"), ("kimi", "LIVE")),
                _mail({"sol": [_entry("request", "unhandled", ago_s=2 * 3600), _entry("handoff", "unhandled", 600)]}))
    assert sig.status == floor.FIRED
    assert "sol" in sig.detail and "2 unhandled" in sig.detail and "request" in sig.detail and "handoff" in sig.detail
    assert "2.0h" in sig.detail, "the oldest obligation's age is stated"


def test_handled_mail_to_an_absent_seat_is_clear_and_the_clear_states_its_bound():
    sig = sense(_roster(("sol", "DEAD")), _mail({"sol": [_entry("request", "replied"), _entry("handoff", "consumed")]}))
    assert sig.status == floor.CLEAR
    assert "sol" in sig.detail and "never seen on the roster" in sig.detail


def test_a_live_or_stale_seat_is_not_an_absent_seat():
    sig = sense(_roster(("kimi", "LIVE"), ("claude", "STALE")),
                _mail({"kimi": [_entry("request", "unhandled")], "claude": [_entry("handoff", "unhandled")]}))
    assert sig.status == floor.CLEAR, "mail waiting for a seat that is alive is a backlog, not undeliverable"


def test_chat_to_an_absent_seat_is_not_a_directed_obligation():
    sig = sense(_roster(("sol", "DEAD")), _mail({"sol": [_entry("chat", "unhandled"), _entry("note", "unhandled")]}))
    assert sig.status == floor.CLEAR


def test_an_unreadable_roster_is_unavailable_not_clear():
    def broken():
        raise ConnectionError("redis down")
    sig = sense(broken, _mail({}))
    assert sig.status == floor.UNAVAILABLE and "roster" in sig.detail and "redis down" in sig.detail


def test_an_unreadable_mailbox_for_an_absent_seat_is_unavailable_and_names_the_seat():
    def query(ns, agent):
        return {"available": False, "reason": "index unavailable", "entries": []}
    sig = sense(_roster(("sol", "DEAD")), query)
    assert sig.status == floor.UNAVAILABLE and "sol" in sig.detail


def test_a_fire_still_names_the_seats_it_could_not_read():
    def query(ns, agent):
        if agent == "neo":
            return {"available": False, "reason": "index unavailable", "entries": []}
        return {"available": True, "entries": [_entry("request", "unhandled")]}
    sig = sense(_roster(("sol", "DEAD"), ("neo", "OFFLINE")), query)
    assert sig.status == floor.FIRED and "could not read" in sig.detail and "neo" in sig.detail


def test_the_default_manifest_uses_the_real_sensor_and_its_falsifier_runs_the_real_logic(monkeypatch):
    calls = []
    real = sensors.undeliverable_mail

    def spy(*a, **k):
        calls.append(k)
        return real(*a, **k)

    monkeypatch.setattr(sensors, "undeliverable_mail", spy)
    entry = {e.key: e for e in floor.default_manifest()}["undeliverable_mail"]
    assert floor.self_check([entry]) == {"undeliverable_mail": True}
    assert calls and calls[-1].get("roster_rows") is not None, "the falsifier drives the real sensor, not a constant"
