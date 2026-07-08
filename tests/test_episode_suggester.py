"""Bookends Slice S3 -- the episode auto-suggester (core/narrative/episode_suggester.py).

The slice's acceptance bar (design #4): fires on a REAL phase boundary, NOT on noise. Pinned here:
  * pure `evaluate()` -- the four triggers, their priorities, and the noise gates (young/thin spans,
    out-of-span task events, same-track, fresh activity);
  * stateful `suggest()` -- fingerprint fires-at-most-once, the standing suggestion is stable across
    polls, stronger-only replacement behind a cooldown, idle self-clears on activity, state resets on
    a new episode, and exactly ONE durable `episode_suggestion` event per NEW suggestion (the
    RENEW-shared bus, review Q5d);
  * the contract (#6): a suggestion is the draft shape + reason/confidence, fingerprint internal.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore
from core.narrative.beat_log import BeatLog
from core.narrative import episode as ep
from core.narrative import episode_suggester as sg


def _store():
    return FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))


def _emit(store, kind, summary, at, weight=None, track="ai-setup"):
    """Explicit track: routing is the TrackRouter's job, and letting it infer here would couple these
    tests to live router behavior (the exact drift the switch detector was hardened against)."""
    return BeatLog(store).emit(kind, summary, f"src:{summary}", at=at, weight=weight, themes=[],
                               track=track)


def _beats(store, track="ai-setup"):
    """Two quick beats right after open -- the minimum non-thin episode."""
    _emit(store, "decision", "fix the parser because QA found a crash", "2026-07-07T10:00:30",
          weight=4, track=track)
    _emit(store, "note", "edited parser.py", "2026-07-07T10:01:00", weight=5, track=track)


def _ledger(tmp_path, *history_specs):
    """A tmp tasks.json: history_specs = (task_id, to, at_iso). Timestamps use +00:00 like the real
    ledger (the tz-safe join against naive beat/span times is part of what's under test)."""
    tasks = {}
    for tid, to, at in history_specs:
        tasks.setdefault(tid, {"id": tid, "title": tid, "status": to, "history": []})
        tasks[tid]["history"].append({"to": to, "by": "t", "at": at})
    p = os.path.join(tmp_path, "tasks.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"seq": 1, "tasks": list(tasks.values())}, f)
    return p


def _empty_ledger(tmp_path):
    return _ledger(tmp_path)


def _spy_events(monkeypatch):
    import core.events.event_log as el
    events = []
    monkeypatch.setattr(el, "capture_event",
                        lambda kind, summary, **kw: events.append((kind, summary, kw)) or None)
    return events


class _B:
    def __init__(self, at, id="b1", track=None):
        self.at, self.id, self.track = at, id, track


def _switched():
    """Last 2 routed beats unanimously on another track -- a REAL subsystem switch."""
    return [_B("2026-07-07T10:05:00", "b1", "research"), _B("2026-07-07T10:05:30", "b2", "research")]


# --- evaluate(): triggers + noise gates --------------------------------------------------------------

def _ev(**kw):
    base = dict(chapter_track="ai-setup", span_start="2026-07-07T10:00:00",
                beats=[_B("2026-07-07T10:05:00", "b1", "ai-setup"),
                       _B("2026-07-07T10:05:30", "b2", "ai-setup")],
                task_events=[], now="2026-07-07T10:06:00")
    base.update(kw)
    return sg.evaluate(**base)


def test_evaluate_fires_on_real_subsystem_switch():
    got = _ev(beats=_switched())
    assert got == {"reason": "subsystem-switch", "confidence": 0.75,
                   "fingerprint": "subsystem-switch:research"}


def test_evaluate_same_track_is_silent():
    assert _ev() is None


def test_evaluate_single_stray_beat_is_silent():
    beats = [_B("2026-07-07T10:04:00", "b1", "ai-setup"), _B("2026-07-07T10:05:00", "b2", "ai-setup"),
             _B("2026-07-07T10:05:30", "b3", "research")]        # one stray, not unanimous
    assert _ev(beats=beats) is None


def test_evaluate_unrouted_beats_are_silent():
    assert _ev(beats=[_B("2026-07-07T10:05:00", "b1"), _B("2026-07-07T10:05:30", "b2")]) is None


def test_evaluate_young_episode_is_silent():
    assert _ev(beats=_switched(), now="2026-07-07T10:04:00") is None   # < MIN_SPAN_S


def test_evaluate_thin_episode_is_silent():
    assert _ev(beats=[_B("2026-07-07T10:05:00", "b1", "research")]) is None   # < MIN_BEATS


def test_evaluate_impl_complete_outranks_switch():
    got = _ev(beats=_switched(),
              task_events=[("impl-complete", "T042", sg._epoch("2026-07-07T10:05:00"))])
    assert got["reason"] == "impl-complete" and got["confidence"] == 0.88
    assert got["fingerprint"] == "impl-complete:T042"


def test_evaluate_task_event_outside_span_is_silent():
    assert _ev(task_events=[("impl-complete", "T042", sg._epoch("2026-07-07T09:59:00"))]) is None


def test_evaluate_new_objective_fires():
    got = _ev(task_events=[("new-objective", "T043", sg._epoch("2026-07-07T10:05:00"))])
    assert got["reason"] == "new-objective" and got["confidence"] == 0.70


def test_evaluate_idle_after_threshold_only():
    stale = [_B("2026-07-07T10:01:00", "b1"), _B("2026-07-07T10:02:00", "b2")]
    assert _ev(beats=stale, now="2026-07-07T10:16:00") is None            # 14 min: not yet
    got = _ev(beats=stale, now="2026-07-07T10:17:30")                     # 15.5 min idle
    assert got == {"reason": "idle", "confidence": 0.60, "fingerprint": "idle:b2"}


# --- suggest(): state machine + bus ------------------------------------------------------------------

def test_suggest_none_without_open_episode(tmp_path, monkeypatch):
    _spy_events(monkeypatch)
    assert sg.suggest(_store(), now="2026-07-07T10:06:00",
                      ledger_path=_empty_ledger(tmp_path)) is None


def test_suggest_switch_fires_once_stands_across_polls(tmp_path, monkeypatch):
    events = _spy_events(monkeypatch)
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00", track="ai-setup")
    _beats(s, track="research")                     # both routed beats left the episode's track
    led = _empty_ledger(tmp_path)
    got = sg.suggest(s, now="2026-07-07T10:06:00", ledger_path=led)
    assert got["reason"] == "subsystem-switch" and got["confidence"] == 0.75
    assert set(got) == {"title", "description", "why", "reason", "confidence"}   # contract, no internals
    assert "parser" in (got["title"] + got["description"]).lower()              # draft over real beats
    assert "because" in got["why"].lower()                                      # why from the decision beat
    again = sg.suggest(s, now="2026-07-07T10:07:00", ledger_path=led)
    assert again == got                                                         # standing view is stable
    assert len(events) == 1 and events[0][0] == "episode_suggestion"            # ONE bus event, not two
    assert events[0][2]["detail"]["reason"] == "subsystem-switch"


def test_suggest_idle_self_clears_when_activity_resumes(tmp_path, monkeypatch):
    events = _spy_events(monkeypatch)
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00", track="ai-setup")
    _beats(s)
    led = _empty_ledger(tmp_path)
    got = sg.suggest(s, now="2026-07-07T10:17:00", ledger_path=led)      # 16 min since last beat
    assert got["reason"] == "idle" and len(events) == 1
    _emit(s, "note", "back at it", "2026-07-07T10:18:00")               # activity resumes
    assert sg.suggest(s, now="2026-07-07T10:18:30", ledger_path=led) is None
    assert len(events) == 1                                              # clearing emits nothing


def test_suggest_stronger_replaces_only_after_cooldown(tmp_path, monkeypatch):
    events = _spy_events(monkeypatch)
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00", track="ai-setup")
    _beats(s)
    led_idle = _empty_ledger(tmp_path)
    got = sg.suggest(s, now="2026-07-07T10:17:00", ledger_path=led_idle)
    assert got["reason"] == "idle"
    led_done = _ledger(tmp_path, ("T042", "done", "2026-07-07T10:18:00+00:00"))
    within = sg.suggest(s, now="2026-07-07T10:19:00", ledger_path=led_done)     # 2 min after idle fired
    assert within["reason"] == "idle"                                           # cooldown holds the line
    later = sg.suggest(s, now="2026-07-07T10:28:00", ledger_path=led_done)      # past COOLDOWN_S
    assert later["reason"] == "impl-complete" and later["confidence"] == 0.88
    assert [e[2]["detail"]["reason"] for e in events] == ["idle", "impl-complete"]


def test_suggest_weaker_never_replaces_stronger(tmp_path, monkeypatch):
    events = _spy_events(monkeypatch)
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00", track="ai-setup")
    _beats(s)
    led = _ledger(tmp_path, ("T042", "done", "2026-07-07T10:05:00+00:00"))
    got = sg.suggest(s, now="2026-07-07T10:06:00", ledger_path=led)
    assert got["reason"] == "impl-complete"
    for i, at in enumerate(("2026-07-07T10:20:00", "2026-07-07T10:21:00", "2026-07-07T10:22:00")):
        _emit(s, "note", f"drifting {i}", at, track="research")          # a weaker trigger appears
    later = sg.suggest(s, now="2026-07-07T10:30:00", ledger_path=led)    # even past the cooldown
    assert later["reason"] == "impl-complete"                            # 0.75 never displaces 0.88
    assert len(events) == 1


def test_suggest_new_episode_resets_state(tmp_path, monkeypatch):
    events = _spy_events(monkeypatch)
    s = _store()
    ep.open_episode(s, now="2026-07-07T10:00:00", track="ai-setup")
    _beats(s, track="research")
    led = _empty_ledger(tmp_path)
    assert sg.suggest(s, now="2026-07-07T10:06:00", ledger_path=led)["reason"] == "subsystem-switch"
    ep.close_episode(s, now="2026-07-07T10:07:00")                       # close -> fresh episode opens
    _emit(s, "note", "new work a", "2026-07-07T10:07:30", track="research")
    _emit(s, "note", "new work b", "2026-07-07T10:08:00", track="research")
    got = sg.suggest(s, now="2026-07-07T10:13:00", ledger_path=led)      # same switch, NEW chapter
    assert got is not None and got["reason"] == "subsystem-switch"
    assert len(events) == 2                                              # fired once per episode
