"""The pedal-boundary mode of the practice segmenter (arsenal/practice.py, boundary="pedal").

Daniel, 2026-09-29: "adjust the chord detection logic to have a mode that utilizes when I let go of the sustain pedal
to signify a note change. the current iteration still captures prior notes." One synthetic session, built here like
the others (nothing reads his practice data): a C major chord under the pedal with a melody note over it, then the
next chord's keys pressed a beat BEFORE the pedal comes up (legato pedalling), then the lift.

- notes mode (the default, unchanged): a window may run across the lift, and a note's 700 ms heard-extension may too.
- pedal mode: every window ends at a lift, the heard-extension stops at the first lift after the onset, and the window
  after the lift holds none of the pitch classes the lift cleared.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from arsenal import practice as pr  # noqa: E402
from test_arsenal_practice import n, perform  # noqa: E402  (the synthetic-session helpers)

C_MAJOR = ["C3", "E4", "G4"]
F_MAJOR = ["F3", "A4", "C5"]
PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9}


def legato_session():
    """t=0 pedal down; C major struck at 0, keys up at 900 (ringing under the pedal); a D5 melody note 1500-1600
    (rings); F major keys down at 1900; pedal UP at 1950 (the C major and the D stop); pedal down at 2050; F held
    to 3400; pedal up at 3400."""
    acts = [(0, "down", 0, 0)]
    for m in C_MAJOR:
        acts += [(0, "on", n(m), 80), (900, "off", n(m), 0)]
    acts += [(1500, "on", n("D5"), 60), (1600, "off", n("D5"), 0)]
    for m in F_MAJOR:
        acts += [(1900, "on", n(m), 80), (3400, "off", n(m), 0)]
    acts += [(1950, "up", 0, 0), (2050, "down", 0, 0), (3400, "up", 0, 0)]
    return perform(acts)


def windows_for(events, boundary):
    snd = pr.sounding(events)
    ctx = pr._context(snd, events, boundary)
    windows = pr.harmonic_windows(snd, boundary)["windows"]
    for w in windows:
        pr._facts(w, ctx)
    return pr.merge_growth(windows, ctx), snd


def test_pedal_mode_cuts_every_window_at_the_lift():
    events = legato_session()
    windows, snd = windows_for(events, "pedal")
    assert [p["up_ms"] for p in snd["pedal"]] == [1950, 3400]
    ends = [w["end_ms"] for w in windows]
    assert 1950 in ends, f"a window ends exactly at the lift; windows end at {ends}"
    after = [w for w in windows if w["start_ms"] >= 1950]
    assert after, "the F major has its own window after the lift"
    cleared = {PC["E"], PC["G"], PC["D"]}
    for w in after:
        assert not (set(w["pcs"]) & cleared), f"prior notes captured after the lift: {sorted(w['pcs'])}"
        assert PC["F"] in w["pcs"] and PC["A"] in w["pcs"]
    before = [w for w in windows if w["end_ms"] <= 1950]
    assert any({PC["C"], PC["E"], PC["G"]} <= set(w["pcs"]) for w in before), "the C major is named before the lift"


def test_pedal_mode_stops_the_heard_extension_at_the_first_lift_after_the_onset():
    events = legato_session()
    snd = pr.sounding(events)
    lifts = [p["up_ms"] for p in snd["pedal"]]
    heard_notes, _ = pr._heard(snd["notes"])
    heard_pedal, _ = pr._heard(snd["notes"], lifts)
    d = PC["D"]
    assert heard_notes[d][-1][1] > 1950, "notes mode: the D (struck 1500) is heard past the lift by its extension"
    assert heard_pedal[d][-1][1] == 1950, "pedal mode: the lift ends what the pedal was holding"
    f = PC["F"]
    assert heard_pedal[f][-1][1] >= 3400, "a key held across the lift keeps sounding into the next window"


def test_notes_mode_is_unchanged_by_the_flag_defaults():
    events = legato_session()
    snd = pr.sounding(events)
    assert pr.harmonic_windows(snd) == pr.harmonic_windows(snd, "notes")
    assert pr._context(snd, events)["boundary"] == "notes"
    doc = pr.analyze(events)
    assert doc["boundary"] == "notes"


def test_analyze_reports_the_boundary_it_used():
    doc = pr.analyze(legato_session(), boundary="pedal")
    assert doc["boundary"] == "pedal"
