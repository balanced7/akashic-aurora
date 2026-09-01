"""RED: the failsafe watcher -- an out-of-band deadman that survives the bus it watches.

Daniil, 2026-08-20: "I am also wondering if we should have an always on failsafe watcher that
isn't tied to the bifrost as a recovery mechanism for if you forgot to set a watcher."

WHY OUT-OF-BAND IS THE WHOLE POINT, and the house already learned it the expensive way --
control_channel.py: "control.is_halted is checked inside the message-handling path, which only
runs AFTER a message arrives, which is exactly what a blocked read prevents." kimi was once up,
heartbeating and uncommandable for twelve hours. A watcher living on Bifrost goes blind in exactly
the failures worth watching for. This one touches no redis, no bus, no lane: a file on disk, a
clock, and a write-only webhook.

WHY AN EXPECTATION FILE AND NOT JUST A TIMER, which is the hard half: silence is USUALLY correct.
At 3am with no run active, quiet is the right state, and a watcher that alarms on quiet gets muted
-- and then we are blind for a worse reason than before. Last night's lesson said it plainly: a
heartbeat proves PRESENCE and cannot prove ABSENCE; absence needs a DURABLE EXPECTATION to be
measured against. So the alarm fires only where an expectation is live AND its checkpoint has gone
stale. No expectation, no alarm, ever.

V1 IS NOTIFY-ONLY, deliberately. It can tell him; it cannot act. Auto-recovery (spawning a fresh
seat) is real now that his token works and T366/T367 make a stillborn spawn visible -- but this
house has scars from thundering-herd spawns, so that half stays behind his ruling. A watcher with
zero blast radius that reliably speaks is most of the value.

Run:  py -m pytest tests/test_failsafe_watcher.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts" / "ops"))

import failsafe_watcher as W  # noqa: E402
from core.comm import failsafe as F  # noqa: E402

NOW = 1_787_240_000.0
LIVE = {"active": True, "declared_by": "claude#06528775", "what": "door arc pass 2",
        "checkpoint_at": NOW - 60, "grace_s": 1800}


# ------------------------------------------------------------------ silence is the default
def test_no_expectation_means_no_alarm_ever():
    """The floor. Nothing declared -> quiet is correct and must stay quiet."""
    assert F.verdict(None, now=NOW) is None


def test_a_stood_down_expectation_is_silent():
    assert F.verdict({**LIVE, "active": False, "checkpoint_at": NOW - 99999}, now=NOW) is None


def test_a_fresh_checkpoint_is_silent():
    assert F.verdict(LIVE, now=NOW) is None


def test_malformed_expectation_is_silent_not_alarming():
    """Fail-open toward SILENCE. A watcher that alarms on its own parse errors trains the reader
    to ignore it, which costs more than the blind spot it was built to close."""
    for junk in ({}, {"active": True}, {"active": True, "checkpoint_at": "soon"}, "not-a-dict"):
        assert F.verdict(junk, now=NOW) is None, junk


# ------------------------------------------------------------------ the one case that fires
def test_a_live_expectation_with_a_stale_checkpoint_alarms():
    stale = {**LIVE, "checkpoint_at": NOW - 3600}
    alarm = F.verdict(stale, now=NOW)
    assert alarm, "a declared-active run silent for an hour past its grace must alarm"


def test_the_alarm_names_what_who_and_how_long():
    """He reads this on a phone. 'Something is wrong' is the same silence with punctuation."""
    alarm = F.verdict({**LIVE, "checkpoint_at": NOW - 3600}, now=NOW)
    assert "door arc pass 2" in alarm, alarm
    assert "claude#06528775" in alarm, alarm
    assert "60" in alarm or "min" in alarm.lower(), alarm
    assert "\n" not in alarm.strip(), "one line, for a phone"


def test_the_boundary_is_the_grace_not_the_cadence():
    """One minute under grace is silent; one minute over alarms. The boundary IS the mechanism."""
    assert F.verdict({**LIVE, "checkpoint_at": NOW - 1799}, now=NOW) is None
    assert F.verdict({**LIVE, "checkpoint_at": NOW - 1801}, now=NOW) is not None


# ------------------------------------------------------------------ it must not become noise
def test_cooldown_stops_a_repeating_alarm_from_becoming_wallpaper():
    """Scheduled every few minutes, an un-cooled alarm would fire forever and get muted."""
    stale = {**LIVE, "checkpoint_at": NOW - 3600, "last_alarm_at": NOW - 30, "cooldown_s": 1800}
    assert F.verdict(stale, now=NOW) is None, "re-alarmed inside its own cooldown"
    aged = {**stale, "last_alarm_at": NOW - 3600}
    assert F.verdict(aged, now=NOW) is not None, "cooldown expired but stayed silent"


# ------------------------------------------------------------------ the wire half
def test_the_post_wears_a_name_cloudflare_will_admit(monkeypatch):
    """2026-09-01: the scheduled task sat at 0x1 for days -- an alarm was due and every POST
    bounced. Discord webhooks sit behind Cloudflare, which 403s (error code 1010) the default
    Python-urllib browser signature outright. A/B receipt on the live URL: no User-Agent -> 403,
    named User-Agent -> 200. The deadman's one job is to speak; it must not dress as a banned bot."""
    seen = {}

    class _Resp:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def fake_urlopen(req, timeout=None):
        seen["ua"] = req.get_header("User-agent") or ""
        return _Resp()

    monkeypatch.setattr(W, "_webhook", lambda: "https://discord.com/api/webhooks/1/x")
    monkeypatch.setattr(W.urllib.request, "urlopen", fake_urlopen)
    assert W._post("drill line") is True
    assert seen["ua"], "no User-Agent set -- urllib's default signature is Cloudflare-banned"
    assert "python-urllib" not in seen["ua"].lower(), seen["ua"]


def test_declaring_and_standing_down_round_trips(tmp_path):
    """The expectation is a FILE, so a crashed session leaves it behind and the watcher still
    fires -- which is the entire point of putting it outside the process that declares it."""
    p = tmp_path / "run-active.json"
    F.declare(p, who="claude#abc", what="a slice", grace_s=900, now=NOW)
    assert F.load(p)["active"] is True
    F.checkpoint(p, now=NOW + 100)
    assert F.load(p)["checkpoint_at"] == NOW + 100
    F.stand_down(p, now=NOW + 200)
    assert F.load(p)["active"] is False
    assert F.verdict(F.load(p), now=NOW + 99999) is None
