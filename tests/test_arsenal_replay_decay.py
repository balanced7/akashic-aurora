"""The replay audition plays a chord as it sounded when the chord began (arsenal/replay_harmony.py decay).

Daniel, 2026-09-29: "when I hit the chord it sounds with the notes that I was actually sustaining in that time. past
notes that have decayed and are barely silent should either register and play as such or be silent." A struck string
decays whatever the pedal does, so each note is auditioned at the share of its strike velocity it had left when the
chord began (a velocity half-life, long in the bass, short in the treble); under FADE_FLOOR it is silent and listed
as faded. Notes carried into an excerpt from before its start bring their real age (replay.carried_at), which the
cue format cannot carry. Synthetic events only.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from arsenal import pianocue, replay  # noqa: E402
from arsenal.replay_harmony import DECAY_HALF_MS, FADE_FLOOR, half_life_ms, harmony, level_at  # noqa: E402
from test_arsenal_replay import take  # noqa: E402,F401  (the fixture: a synthetic store)

BASS, TREBLE = 36, 86            # C2 and D6, struck at 0 under the pedal and left to ring. D6, because the namer
                                 # represents each pitch class once: a G5 would fold into the chord's own G4
CHORD = (64, 67, 71)             # E4 G4 B4, struck at 8 s over them, under the same pedal


def events():
    ev = [{"kind": "pedal", "t_ms": 0, "down": True, "value": 100}]
    for note in (BASS, TREBLE):
        ev += [{"kind": "on", "t_ms": 0, "note": note, "vel": 80}, {"kind": "off", "t_ms": 200, "note": note}]
    for note in CHORD:
        ev += [{"kind": "on", "t_ms": 8000, "note": note, "vel": 80}, {"kind": "off", "t_ms": 14000, "note": note},
               {"kind": "sound_end", "t_ms": 14000, "note": note, "by": "release"}]
    for note in (BASS, TREBLE):
        ev.append({"kind": "sound_end", "t_ms": 14000, "note": note, "by": "pedal"})
    ev.append({"kind": "pedal", "t_ms": 14000, "down": False, "value": 0})
    return ev


def window_from(windows, start_ms):
    ws = [w for w in windows if w["start_ms"] >= start_ms]
    assert ws, f"no window starts at or after {start_ms}: {[w['start_ms'] for w in windows]}"
    return ws[0]


def test_the_model_is_long_in_the_bass_short_in_the_treble_and_fresh_at_the_strike():
    lo, hi = DECAY_HALF_MS
    assert half_life_ms(36) == lo and half_life_ms(96) == hi and lo > hi
    assert half_life_ms(0) == lo and half_life_ms(127) == hi, "clamped outside the anchors"
    assert hi < half_life_ms(66) < lo
    assert level_at(0, 60) == 1.0 and level_at(half_life_ms(60), 60) == 0.5
    assert 0 < FADE_FLOOR < 0.5


def test_a_chord_over_ringing_notes_plays_them_as_quiet_as_they_had_become():
    cue = pianocue.build_replay_cue(events(), 0, 14)
    windows = harmony(cue)
    first, later = window_from(windows, 0), window_from(windows, 8000)
    assert first["velocities"][BASS] == 80 and TREBLE in first["notes"], "at the strike everything is fresh"
    assert later["velocities"][BASS] == round(80 * level_at(8000, BASS)), "the bass has half-decayed: quiet, not silent"
    assert all(later["velocities"][n] == 80 for n in CHORD), "the chord just struck is fresh"
    assert TREBLE in later["faded"] and TREBLE not in later["notes"], "a treble note 8 s old is barely silent: silent"
    assert later["levels"][TREBLE] < FADE_FLOOR <= later["levels"][BASS]


def test_notes_carried_into_an_excerpt_bring_their_real_age():
    ev = events()
    carried = replay.carried_at(ev, 5000)
    assert carried == {BASS: {"age_ms": 5000, "vel": 80}, TREBLE: {"age_ms": 5000, "vel": 80}}
    cue = pianocue.build_replay_cue(ev, 5000, 9)
    without = window_from(harmony(cue), 3000)
    with_age = window_from(harmony(cue, 1, None, "notes", carried), 3000)
    assert without["velocities"][BASS] == round(80 * level_at(3000, BASS)), "the cue alone thinks the bass is 3 s old"
    assert with_age["velocities"][BASS] == round(80 * level_at(8000, BASS)), "with its real age it is 8 s old"
    assert TREBLE in with_age["faded"] and TREBLE in without["notes"]


def test_excerpt_reports_what_was_carried_in(take):
    store, session = take
    data = replay.excerpt(store, session, "0:01", seconds=2)
    assert data["carried"] == {48: {"age_ms": 1000, "vel": 55}}, "struck at 0, pedal-held to 3 s: 1 s old at 0:01"
    assert data["lifts_ms"] == [2000], "the lift at 3 s, 2 s into the excerpt"
