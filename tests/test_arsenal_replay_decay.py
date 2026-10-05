"""The replay audition plays a chord as it sounded at the instant it was whole (arsenal/replay_harmony.py decay).

Daniel, 2026-09-29: "when I hit the chord it sounds with the notes that I was actually sustaining in that time. past
notes that have decayed and are barely silent should either register and play as such or be silent."
Heimdall's measured verdict on the first model (2026-09-29) set these numbers: the keys voice maps velocity to
loudness as peak = 0.2 * (0.06 + 0.94 * v ** 1.6) (cues.js:1455), so decay is computed in AMPLITUDE and turned
back into a velocity by inverting that curve; the decay rate is a T60 (20 s at C2, 3 s at C7); the voice has no
gate (its quietest strike peaks at 0.012), so a note quieter than that plays at velocity 1 and only a note more
than 40 dB below its strike is silent and faded; ages are taken at the densest instant of the window, so an
arpeggio's later notes are not "fresh" by construction. Notes carried into an excerpt bring their real age
(replay.carried_at). Synthetic events only.
"""

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from arsenal import pianocue, replay  # noqa: E402
from arsenal.replay_harmony import (
    DECAY_T60_S,
    SILENT_DB,
    VOICE_FLOOR,
    VOICE_LEVEL,
    amplitude_at,  # noqa: E402
    densest_instant,
    harmony,
    peak_of,
    t60_s,
    velocity_for_peak,
)
from test_arsenal_replay import take  # noqa: E402,F401  (the fixture: a synthetic store)

BASS, TREBLE = 36, 86  # C2 and D6, struck at 0 under the pedal and left to ring. D6, because the namer
# represents each pitch class once: a G5 would fold into the chord's own G4
CHORD = (64, 67, 71)  # E4 G4 B4, struck at 8 s over them, under the same pedal


def events():
    ev = [{"kind": "pedal", "t_ms": 0, "down": True, "value": 100}]
    for note in (BASS, TREBLE):
        ev += [{"kind": "on", "t_ms": 0, "note": note, "vel": 80}, {"kind": "off", "t_ms": 200, "note": note}]
    for note in CHORD:
        ev += [
            {"kind": "on", "t_ms": 8000, "note": note, "vel": 80},
            {"kind": "off", "t_ms": 14000, "note": note},
            {"kind": "sound_end", "t_ms": 14000, "note": note, "by": "release"},
        ]
    for note in (BASS, TREBLE):
        ev.append({"kind": "sound_end", "t_ms": 14000, "note": note, "by": "pedal"})
    ev.append({"kind": "pedal", "t_ms": 14000, "down": False, "value": 0})
    return ev


def window_from(windows, start_ms):
    ws = [w for w in windows if w["start_ms"] >= start_ms]
    assert ws, f"no window starts at or after {start_ms}: {[w['start_ms'] for w in windows]}"
    return ws[0]


def db_of(ratio):
    return 20.0 * math.log10(ratio)


def test_the_model_is_amplitude_through_the_voice_curve_with_t60_anchors():
    lo, hi = DECAY_T60_S
    assert (lo, hi) == (20.0, 3.0), "the calibration the first model stated and missed"
    assert t60_s(36) == lo and t60_s(96) == hi and t60_s(0) == lo and t60_s(127) == hi
    assert amplitude_at(0, 60) == 1.0
    assert abs(db_of(amplitude_at(20000, 36)) - (-60.0)) < 1e-6, "-60 dB at T60"
    assert abs(db_of(amplitude_at(1000, 96)) - (-20.0)) < 1e-6, "a C7 is -20 dB after one second"
    # the voice's own curve, and its inverse: round trips through the audible range
    assert abs(peak_of(80) - 0.1017) < 1e-3, "Heimdall's measurement of vel 80"
    assert abs(peak_of(0) - VOICE_LEVEL * VOICE_FLOOR) < 1e-12, "the voice never gates: its floor is 0.012"
    for v in (1, 20, 40, 80, 127):
        assert velocity_for_peak(peak_of(v)) == v
    assert velocity_for_peak(0.0) == 1 and velocity_for_peak(10.0) == 127
    assert SILENT_DB == -40.0


def test_a_chord_over_ringing_notes_plays_them_as_they_sounded_when_it_was_whole():
    cue = pianocue.build_replay_cue(events(), 0, 14)
    windows = harmony(cue)
    first, later = window_from(windows, 0), window_from(windows, 8000)
    assert first["velocities"][BASS] == 80 and TREBLE in first["notes"], "at the strike everything is fresh"
    assert later["at_ms"] == 8000, "the chord is whole the instant its three notes land"
    assert all(later["velocities"][n] == 80 for n in CHORD), "the chord just struck is fresh"
    # the bass, 8 s old: 10^(-3*8/20) = -24 dB -- audible, but quieter than the voice can play: velocity 1
    assert abs(later["db"][BASS] - (-24.0)) < 0.05
    assert later["velocities"][BASS] == 1, "as quiet as the voice can say it (peak 0.0064 < the voice floor 0.012)"
    assert BASS in later["notes"]
    # the treble D6, 8 s old: T60 ~ 4.1 s -> ~ -116 dB: silent, listed as faded
    assert later["db"][TREBLE] < SILENT_DB and TREBLE in later["faded"] and TREBLE not in later["notes"]


def test_an_unfolding_arpeggio_is_aged_from_the_instant_it_is_whole_not_the_window_start():
    ev = [{"kind": "pedal", "t_ms": 0, "down": True, "value": 100}]
    for at, note in [(0, 48), (400, 64), (800, 67)]:
        ev += [{"kind": "on", "t_ms": at, "note": note, "vel": 80}, {"kind": "off", "t_ms": at + 180, "note": note}]
    for note in (48, 64, 67):
        ev.append({"kind": "sound_end", "t_ms": 2600, "note": note, "by": "pedal"})
    ev.append({"kind": "pedal", "t_ms": 2600, "down": False, "value": 0})
    w = harmony(pianocue.build_replay_cue(ev, 0, 2.6))[0]
    assert w["at_ms"] == 800, "whole when the third note lands, not at the window start"
    assert w["db"][48] < 0 and w["db"][64] < 0 and w["db"][67] == 0.0, "the earlier notes have aged, the last is fresh"
    # through the voice curve, -3.5 dB of amplitude (C3 at 0.8 s) is velocity 60 of 80; E4 at 0.4 s is 63
    assert w["velocities"][67] == 80 > w["velocities"][64] > w["velocities"][48] > 50, w["velocities"]


def test_notes_carried_into_an_excerpt_bring_their_real_age():
    ev = events()
    carried = replay.carried_at(ev, 5000)
    assert carried == {BASS: {"age_ms": 5000, "vel": 80}, TREBLE: {"age_ms": 5000, "vel": 80}}
    cue = pianocue.build_replay_cue(ev, 5000, 9)
    without = window_from(harmony(cue), 3000)
    with_age = window_from(harmony(cue, 1, None, "notes", carried), 3000)
    assert abs(without["db"][BASS] - db_of(amplitude_at(3000, BASS))) < 0.05, "the cue alone thinks the bass is 3 s old"
    assert abs(with_age["db"][BASS] - db_of(amplitude_at(8000, BASS))) < 0.05, "with its real age it is 8 s old"
    assert without["velocities"][BASS] > 20 and with_age["velocities"][BASS] == 1, (
        "3 s old plays; 8 s old is at the floor"
    )
    assert TREBLE in with_age["faded"]


def test_densest_instant_prefers_the_first_moment_of_maximum_sound():
    sounding = [
        {"on_ms": 0, "end_ms": 3000},
        {"on_ms": 400, "end_ms": 3000},
        {"on_ms": 800, "end_ms": 1000},
        {"on_ms": 2000, "end_ms": 3000},
    ]
    assert densest_instant(sounding, 0, 3000) == 800, "three sound at 800; only two again at 2000"


def test_excerpt_reports_what_was_carried_in(take):
    store, session = take
    data = replay.excerpt(store, session, "0:01", seconds=2)
    assert data["carried"] == {48: {"age_ms": 1000, "vel": 55}}, "struck at 0, pedal-held to 3 s: 1 s old at 0:01"
    assert data["lifts_ms"] == [2000], "the lift at 3 s, 2 s into the excerpt"
