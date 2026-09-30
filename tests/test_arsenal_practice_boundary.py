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


# ---- Heimdall's verification of the first cut (2026-09-29): the late merges leaked lift-spanning windows into the
# output Daniel reads, and short chords struck and released between two lifts were dropped as transients.

def lifts_of(events):
    return [p["up_ms"] for p in pr.sounding(events)["pedal"]]


def spanning(doc, lifts):
    return [(w["start_ms"], w["end_ms"], t) for w in doc["windows"] for t in lifts if w["start_ms"] < t < w["end_ms"]]


def build_session():
    """A chord built note by note across a quick pedal pump, keys held throughout: C3 and G3 held 0-3000; the pedal
    down at 0, UP at 350, down again at 360; E4 added at 400 and held to 3000; pedal up at 3000. In pedal mode the
    lift at 350 ends the first chord: an open fifth stands before it (350 ms, the whole of what was played between
    two lifts) and C major after it. In notes mode no window ends at 350."""
    acts = [(0, "down", 0, 0), (350, "up", 0, 0), (360, "down", 0, 0), (3000, "up", 0, 0)]
    for m in ("C3", "G3"):
        acts += [(0, "on", n(m), 80), (3000, "off", n(m), 0)]
    acts += [(400, "on", n("E4"), 80), (3000, "off", n("E4"), 0)]
    return perform(acts)


def twice_session():
    """The same C major twice, touching at a lift: struck at 0 and released at 1500 under the pedal (ringing); the
    pedal UP at 2000 and down at 2050; struck again at 2100 and held to 3900; pedal up at 3900."""
    acts = [(0, "down", 0, 0), (2000, "up", 0, 0), (2050, "down", 0, 0), (3900, "up", 0, 0)]
    for m in C_MAJOR:
        acts += [(0, "on", n(m), 80), (1500, "off", n(m), 0), (2100, "on", n(m), 80), (3900, "off", n(m), 0)]
    return perform(acts)


def staccato_session():
    """A chord struck and released between two lifts 350 ms apart (Heimdall's dropped chords): C major 0-900 under
    the pedal (ringing); lift at 2000; pedal down at 2050; F major keys 2050-2250 (ringing until the next lift);
    lift at 2350; pedal down at 2400; G major 2500-4000; lift at 4000."""
    acts = [(0, "down", 0, 0), (2000, "up", 0, 0), (2050, "down", 0, 0), (2350, "up", 0, 0), (2400, "down", 0, 0),
            (4000, "up", 0, 0)]
    for m in C_MAJOR:
        acts += [(0, "on", n(m), 80), (900, "off", n(m), 0)]
    for m in F_MAJOR:
        acts += [(2050, "on", n(m), 80), (2250, "off", n(m), 0)]
    for m in ("G3", "B4", "D5"):
        acts += [(2500, "on", n(m), 80), (4000, "off", n(m), 0)]
    return perform(acts)


def test_no_final_window_spans_a_lift():
    """The headline the mode stakes itself on, at the OUTPUT Daniel reads, not only at the segmenter."""
    for events in (legato_session(), build_session(), twice_session(), staccato_session()):
        doc = pr.analyze(events, boundary="pedal")
        assert spanning(doc, lifts_of(events)) == [], spanning(doc, lifts_of(events))


def test_the_late_merges_stop_at_a_lift():
    lifted = pr.analyze(twice_session(), boundary="pedal")["windows"]
    assert [(w["start_ms"], w["end_ms"], w["name"]) for w in lifted] == [(0, 2000, "C"), (2000, 3900, "C")], (
        "the same chord twice, touching at the lift: two chords (merge_same stops at the lift)")
    joined = pr.analyze(twice_session(), boundary="notes")["windows"]
    assert len(joined) == 1 and joined[0]["name"] == "C", "notes mode joins them as before"
    built = pr.analyze(build_session(), boundary="pedal")["windows"]
    assert [(w["start_ms"], w["end_ms"]) for w in built] == [(0, 350), (350, 3000)], (
        "a build across a quick lift-and-repress is two chords (merge_built stops at the lift)")
    assert set(built[0]["pcs"]) == {"C", "G"} and set(built[1]["pcs"]) == {"C", "E", "G"}
    assert 350 not in [w["end_ms"] for w in pr.analyze(build_session(), boundary="notes")["windows"]], (
        "notes mode: the pump is not a boundary")


def test_a_chord_struck_and_released_between_two_lifts_is_a_window_not_a_transient():
    events = staccato_session()
    doc = pr.analyze(events, boundary="pedal")
    assert doc["segmentation"]["transients_dropped"] == 0, doc["segmentation"]
    assert [(w["start_ms"], w["end_ms"], w["name"]) for w in doc["windows"]] == [(0, 2000, "C"), (2000, 2350, "F"),
                                                                                 (2350, 4000, "G")]
    snd = pr.sounding(events)
    pieces = [p for ph in pr._phrases(snd["notes"]) for p in pr._cut_at_lifts(ph, lifts_of(events))]
    assert [(p["start_ms"], p["end_ms"], p["attacked"]) for p in pieces] == [(0, 2000, True), (2000, 2350, True),
                                                                             (2350, 4000, True)]


def test_a_pump_over_ringing_notes_with_nothing_struck_stays_a_transient():
    """C3 rings under the pedal to the lift at 1000; the pedal pumps again at 1200 with nothing struck in between;
    E4 at 1300. The 200 ms piece between the two lifts has no attack of its own: residue, a transient as before."""
    events = perform([(0, "down", 0, 0), (0, "on", n("C3"), 80), (200, "off", n("C3"), 0), (1000, "up", 0, 0),
                      (1010, "down", 0, 0), (1200, "up", 0, 0), (1210, "down", 0, 0), (1300, "on", n("E4"), 80),
                      (3000, "off", n("E4"), 0), (3000, "up", 0, 0)])
    snd = pr.sounding(events)
    pieces = [p for ph in pr._phrases(snd["notes"]) for p in pr._cut_at_lifts(ph, lifts_of(events))]
    assert [(p["start_ms"], p["end_ms"], p["attacked"]) for p in pieces] == [(0, 1000, True), (1000, 1200, False),
                                                                             (1200, 3000, True)]
    seg = pr.harmonic_windows(snd, "pedal")
    assert seg["transients"] == {"count": 1, "ms": 200}
    assert [(w["start_ms"], w["end_ms"]) for w in seg["windows"]] == [(0, 1000), (1200, 3000)]
