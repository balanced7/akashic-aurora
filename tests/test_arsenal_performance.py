"""The practice log (PIANO-V2-SPEC section 4): the pure analyzer, the session store, every route, and the CLI."""
import copy
import json
import re
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import performance as perf  # noqa: E402
from arsenal.__main__ import main  # noqa: E402
from arsenal.serve import App, Server  # noqa: E402

C, G, AM, F = [48, 52, 55, 60], [43, 50, 55, 59], [45, 52, 57, 60], [41, 48, 53, 57]
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def spelled(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


def loop_session(loops=4, bar_ms=2000, pedal=True):
    """A C major I-V-vi-IV loop: each chord struck together, held most of the bar, pedal changed per chord."""
    events = []
    progression = [("C", C), ("G", G), ("Am", AM), ("F", F)]
    t = 0
    for _ in range(loops):
        for name, notes in progression:
            if pedal and t:
                events.append({"t_ms": t, "kind": "pedal", "down": False, "value": 0})
            for m in notes:
                events.append({"t_ms": t, "kind": "on", "note": m, "vel": 80})
            events.append({"t_ms": t, "kind": "chord", "chord": name, "notes": [spelled(m) for m in notes],
                           "key": "C major"})
            if pedal:
                events.append({"t_ms": t + 100, "kind": "pedal", "down": True, "value": 127})
            for m in notes:
                events.append({"t_ms": t + bar_ms - 200, "kind": "off", "note": m})
            t += bar_ms
    events.append({"t_ms": t, "kind": "pedal", "down": False, "value": 0})
    events.append({"t_ms": t, "kind": "chord", "chord": None, "notes": [], "key": None})
    return events


def question_lines(md):
    """The numbered lines under summary.md's questions heading (a glossary, when there is one, comes after them)."""
    return md.rstrip("\n").split("## Questions for Daniel\n", 1)[1].split("\n\n## Glossary\n", 1)[0].splitlines()


def glossary_terms(md):
    if "\n## Glossary\n" not in md:
        return []
    return [line[2:].split(": ", 1)[0] for line in md.rstrip("\n").split("\n## Glossary\n", 1)[1].splitlines()]


# ================================================================================================ analyzer
def test_i_v_vi_iv_loop_reads_as_c_major_with_its_chords_and_moves():
    events = loop_session()
    before = copy.deepcopy(events)
    s = perf.summarize(events)
    assert events == before, "summarize must not modify its input"
    assert perf.summarize(events) == s, "summarize must be deterministic"

    assert s["key"]["best"]["key"] == "C major"
    assert s["key"]["runner_up"]["key"] != "C major" and s["key"]["best"]["r"] > s["key"]["runner_up"]["r"]
    assert s["key"]["weights"] == "sounding seconds per pitch class"

    assert {c["chord"] for c in s["chords"]["top"]} == {"C", "G", "Am", "F"}
    assert all(c["seconds"] == 8.0 and c["segments"] == 4 for c in s["chords"]["top"])
    moves = {(p["from"], p["to"]): p["count"] for p in s["chords"]["progressions"]}
    assert moves == {("C", "G"): 4, ("G", "Am"): 4, ("Am", "F"): 4, ("F", "C"): 3}
    assert s["chords"]["changes"] == 15

    assert s["duration_s"] == 32.0 and s["note_count"] == 64 and s["notes_per_minute"] == 120.0
    assert s["range"]["lowest"] == {"midi": 41, "name": "F2"} and s["range"]["highest"] == {"midi": 60, "name": "C4"}
    # 16 named chord events (the closing null is not a chord); spreads C 12, G 16, Am 15, F 16.
    assert s["voicing"] == {"chord_events": 16, "mean_notes_per_chord": 4.0, "mean_spread_semitones": 14.75}
    tempo = s["timing"]["rough_tempo"]
    assert tempo is None, "one onset every 2 s is 30 BPM, outside the 60-200 range"
    assert s["timing"]["onsets"] == 16 and s["timing"]["ioi_histogram"]["at_or_over_max"] == 15

    assert 3 <= len(s["questions"]) <= 5
    # Each C -> G occurrence is 2 s of C plus 2 s of G: 16 s of a 32 s session. Ties go to the first move played.
    assert [(p["from"], p["to"], p["share_of_session"]) for p in s["chords"]["progressions"][:3]] == \
        [("C", "G", 0.5), ("G", "Am", 0.5), ("Am", "F", 0.5)]
    # The timestamped question leads; it already names the loop, so the plain move question is not asked as well.
    assert s["questions"][0] == ("At 0:00 you started looping 1 → 5 → 6m → 4 in C major (C G Am F), 4 times back "
                                 "to back. What draws you to that cycle?")
    assert not any(q.startswith("You spent") for q in s["questions"])
    nv = s["nashville"]
    assert nv["key"]["key"] == "C major" and nv["key"]["estimate"] == "C major" and nv["key"]["rule"] is None
    assert nv["loops"] == [{"numbers": ["1", "5", "6m", "4"], "length": 4, "count": 4, "first_at": "0:00",
                            "start_s": 0.0, "chords": ["C", "G", "Am", "F"], "key": "C major"}]
    assert [(a["at"], a["key"]["key"]) for a in nv["areas"]] == [("0:00", "C major")]
    assert nv["outside_key"]["count"] == 0 and nv["page"]["changes"] == []

    numbers = s["numbers"]
    assert numbers["source"] == {"piano": 0, "analyzer": 16, "reader": "arsenal.nashville"}
    assert numbers["keys"] == [{"key": "C major", "seconds": 32.0, "share_of_numbered_time": 1.0}]
    assert {(n["number"], n["seconds"], n["outside_key"]) for n in numbers["top"]} == \
        {("1", 8.0, False), ("5", 8.0, False), ("6m", 8.0, False), ("4", 8.0, False)}
    assert {(p["from"], p["to"]): p["count"] for p in numbers["progressions"]} == \
        {("1", "5"): 4, ("5", "6m"): 4, ("6m", "4"): 4, ("4", "1"): 3}
    assert numbers["outside_key"] == {"seconds": 0.0, "share_of_numbered_time": 0.0, "chords": []}
    assert s["chords"]["progressions"][0]["numbers"] == "1 → 5 in C major"


def test_timeline_merges_identical_chord_events_and_keeps_silence():
    events = [
        {"t_ms": 0, "kind": "on", "note": 60, "vel": 50},
        {"t_ms": 0, "kind": "chord", "chord": "C", "notes": ["C4", "E4", "G4"], "key": None},
        {"t_ms": 400, "kind": "chord", "chord": "C", "notes": ["C4", "E4", "G4"], "key": None},
        {"t_ms": 1000, "kind": "chord", "chord": None, "notes": [], "key": None},
        {"t_ms": 1500, "kind": "chord", "chord": "G", "notes": ["G3", "B3", "D4"], "key": None},
        {"t_ms": 1550, "kind": "chord", "chord": "G7", "notes": ["G3", "B3", "D4", "F4"], "key": None},  # 50 ms: passing
        {"t_ms": 1600, "kind": "chord", "chord": "G", "notes": ["G3", "B3", "D4"], "key": None},
        {"t_ms": 3000, "kind": "off", "note": 60},
    ]
    s = perf.summarize(events)
    assert s["chords"]["timeline"] == [
        {"chord": "C", "start_s": 0.0, "seconds": 1.0},
        {"chord": None, "start_s": 1.0, "seconds": 0.5},
        {"chord": "G", "start_s": 1.5, "seconds": 0.05},
        {"chord": "G7", "start_s": 1.55, "seconds": 0.05},
        {"chord": "G", "start_s": 1.6, "seconds": 1.4},
    ]
    top = {c["chord"]: c["seconds"] for c in s["chords"]["top"]}
    assert top == {"G": 1.45, "C": 1.0, "G7": 0.05}
    # Silence does not break a move; the 50 ms G7 and the short G are skipped, and the G pieces join.
    assert s["chords"]["progressions"] == [{"from": "C", "to": "G", "count": 1, "seconds": 2.4,
                                            "share_of_session": 0.8, "numbers": "1 → 5 in C major"}]
    # Five named chord events: 3+3+3+4+3 notes; spreads C4-G4 7, G3-D4 7 (three times), G3-F4 10.
    assert s["voicing"] == {"chord_events": 5, "mean_notes_per_chord": 3.2, "mean_spread_semitones": 7.6}


def test_pedal_and_dynamics_are_exact_on_hand_built_events():
    events = [{"t_ms": i * 1000, "kind": "on", "note": 60 + i, "vel": 10 * (i + 1)} for i in range(10)]
    events += [
        {"t_ms": 1000, "kind": "pedal", "down": True, "value": 100},
        {"t_ms": 2000, "kind": "pedal", "down": True, "value": 90},   # still down: not a new press
        {"t_ms": 3000, "kind": "pedal", "down": False, "value": 10},
        {"t_ms": 5000, "kind": "pedal", "down": True, "value": 127},
        {"t_ms": 6000, "kind": "pedal", "down": False, "value": 0},
        {"t_ms": 10000, "kind": "off", "note": 69},
    ]
    s = perf.summarize(events)
    assert s["duration_s"] == 10.0
    assert s["pedal"] == {"percent_down": 30.0, "presses": 2, "presses_per_minute": 12.0, "mean_down_s": 1.5}
    assert s["dynamics"] == {"notes": 10, "mean_velocity": 55.0, "p10": 19.0, "p90": 91.0, "min": 10, "max": 100}


def test_pedal_down_at_the_end_counts_until_the_last_event():
    events = [{"t_ms": 0, "kind": "on", "note": 60, "vel": 64},
              {"t_ms": 2000, "kind": "pedal", "down": True, "value": 127},
              {"t_ms": 4000, "kind": "off", "note": 60}]
    s = perf.summarize(events)
    assert s["pedal"] == {"percent_down": 50.0, "presses": 1, "presses_per_minute": 15.0, "mean_down_s": 2.0}


def test_sustain_extends_sounding_time_for_the_key_weights():
    events = [
        {"t_ms": 0, "kind": "pedal", "down": True, "value": 127},
        {"t_ms": 0, "kind": "on", "note": 60, "vel": 64},    # C, released at 500 but pedalled until 3000
        {"t_ms": 500, "kind": "off", "note": 60},
        {"t_ms": 1000, "kind": "on", "note": 62, "vel": 64},  # D, repeat-struck at 2000
        {"t_ms": 2000, "kind": "on", "note": 62, "vel": 64},
        {"t_ms": 2500, "kind": "off", "note": 62},
        {"t_ms": 3000, "kind": "pedal", "down": False, "value": 0},
        {"t_ms": 3000, "kind": "on", "note": 64, "vel": 64},  # E, held to the end
        {"t_ms": 4000, "kind": "off", "note": 64},
    ]
    s = perf.summarize(events)
    secs = {p["name"]: p["seconds"] for p in s["pitch_classes"] if p["seconds"]}
    assert secs == {"C": 3.0, "D": 2.0, "E": 1.0}
    counts = {p["name"]: p["count"] for p in s["pitch_classes"] if p["count"]}
    assert counts == {"C": 1, "D": 2, "E": 1}


def test_rough_tempo_uses_the_most_common_gap_cluster():
    # gaps: 500, 490, 510, 500, 250 (too fast for 200 BPM), 750, 500
    onsets = [0, 500, 990, 1500, 2000, 2250, 3000, 3500]
    events = []
    for t in onsets:
        events.append({"t_ms": t, "kind": "on", "note": 60, "vel": 70})
        events.append({"t_ms": t + 20, "kind": "on", "note": 64, "vel": 70})  # within 40 ms: the same onset
    s = perf.summarize(events)
    timing = s["timing"]
    assert timing["onsets"] == 8
    tempo = timing["rough_tempo"]
    assert tempo["label"] == "rough" and tempo["support"] == 5 and tempo["gaps_in_range"] == 6
    assert tempo["ioi_ms"] == 500.0 and tempo["bpm"] == 120.0
    bins = {b["lo_ms"]: b["count"] for b in timing["ioi_histogram"]["bins"]}
    assert bins == {250: 1, 450: 1, 500: 4, 750: 1}


def test_questions_are_built_from_the_numbers_and_the_markdown_ends_with_them():
    s = perf.summarize(loop_session())
    doc = {"session": "20260913-210000-deadbeef", "opened_at": "2026-09-13T21:00:00.000+00:00",
           "closed_at": "2026-09-13T21:01:00.000+00:00", **s}
    md = perf.render_markdown(doc)
    tail = question_lines(md)
    assert 3 <= len(tail) <= 5 and all(re.match(r"^\d\. ", line) for line in tail)
    assert "C major" in md and "C → G (1 → 5 in C major): 4 times, 50% of the session" in md
    assert "## Nashville numbers" in md and "- Loop from 0:00: 1 → 5 → 6m → 4 (C, G, Am, F), 4 times back to back." in md
    assert "- Move 1 → 5 (C → G): 4 times, first at 0:00." in md
    assert "- Every chord that lasted 120 ms or more belongs to C major." in md
    assert glossary_terms(md) == ["Nashville numbers", "m", "loop"]  # only the terms the section used
    assert "Down " in md and "Mean velocity 80.0" in md
    assert perf.summarize([])["questions"] == []


def test_a_single_note_still_gets_three_questions():
    s = perf.summarize([{"t_ms": 0, "kind": "on", "note": 60, "vel": 64}])
    assert 3 <= len(s["questions"]) <= 5


def _on(t, m, vel=64):
    return {"t_ms": t, "kind": "on", "note": m, "vel": vel}


def _off(t, m):
    return {"t_ms": t, "kind": "off", "note": m}


def _pedal(t, down):
    return {"t_ms": t, "kind": "pedal", "down": down, "value": 127 if down else 0}


DEGENERATE_SESSIONS = {
    # the pedal already down, one chord struck in the same millisecond, then stop() or pagehide
    "zero_ms_pedal_chord": [_pedal(0, True), _on(0, 60), _on(0, 64), _on(0, 67),
                            {"t_ms": 0, "kind": "chord", "chord": "C", "notes": ["C4", "E4", "G4"], "key": None}],
    "zero_ms_pedal_note": [_pedal(0, True), _on(0, 60, 80)],
    "zero_ms_pedal_up_and_down": [_pedal(0, True), _on(0, 60), _pedal(0, False), _pedal(0, True)],
    # twelve pitch classes with equal weight: no key can be estimated, and there are no chords, pedal or tempo
    "chromatic_cluster": [_on(0, m, 60) for m in range(60, 72)] + [_off(1000, m) for m in range(60, 72)],
    "chromatic_cluster_zero_ms": [_on(0, m, 60) for m in range(60, 72)],
    "one_repeated_note": [_on(0, 60), _off(5, 60), _on(3000, 60), _off(3005, 60)],
    "only_null_chords": [_on(0, 50), {"t_ms": 0, "kind": "chord", "chord": None, "notes": [], "key": None}],
    "off_before_on": [_off(0, 61), _on(5, 61, 30), _off(500, 61)],
}


@pytest.mark.parametrize("name", sorted(DEGENERATE_SESSIONS))
def test_degenerate_sessions_render_and_get_three_to_five_questions(name):
    s = perf.summarize(DEGENERATE_SESSIONS[name])
    assert 3 <= len(s["questions"]) <= 5, s["questions"]
    md = perf.render_markdown({"session": "20260913-210000-deadbeef", "opened_at": "2026-09-13T21:00:00.000+00:00",
                               "closed_at": "2026-09-13T21:00:01.000+00:00", **s})
    tail = question_lines(md)
    assert len(tail) == len(s["questions"])
    assert "None" not in md


def test_zero_length_session_with_the_pedal_says_so_instead_of_a_share():
    s = perf.summarize(DEGENERATE_SESSIONS["zero_ms_pedal_chord"])
    assert s["pedal"] == {"percent_down": None, "presses": 1, "presses_per_minute": None, "mean_down_s": 0.0}
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert "1 press, 0.00 s down per press on average. The session has no measurable length" in md


def test_equal_pitch_classes_get_a_question_from_the_table():
    s = perf.summarize(DEGENERATE_SESSIONS["chromatic_cluster"])
    assert s["key"] is None and s["chords"]["top"] == [] and s["pedal"]["presses"] == 0
    assert s["timing"]["rough_tempo"] is None
    assert "You used 12 of the 12 pitch classes, each with the same share of time sounding." in " ".join(s["questions"])


def test_validation_rejects_malformed_events():
    good = {"t_ms": 0, "kind": "on", "note": 60, "vel": 1}
    perf.validate_event(good)
    for bad in [None, {"kind": "on", "note": 60, "vel": 5}, dict(good, t_ms=-1), dict(good, t_ms=1.5),
                dict(good, t_ms=True), dict(good, kind="tap"), dict(good, note=128), dict(good, vel=0),
                {"t_ms": 0, "kind": "pedal", "down": 1, "value": 5}, {"t_ms": 0, "kind": "pedal", "down": True, "value": 200},
                {"t_ms": 0, "kind": "chord", "chord": "C", "notes": ["C4", 60], "key": None},
                {"t_ms": 0, "kind": "chord", "chord": "C", "notes": []}]:
        with pytest.raises(perf.BadEvent):
            perf.validate_event(bad)


def test_sound_end_and_the_extra_chord_fields_validate():
    chord = {"t_ms": 0, "kind": "chord", "chord": "F/A", "notes": ["A2", "C4", "F4"], "key": "F major"}
    perf.validate_event(chord)  # the section 4 shape still passes on its own
    full = dict(chord, bass="A", nns="1/3", nns_key="F major", key_conf="0.82", locked=True, harmony_notes=[1])
    perf.validate_event(full)   # fields the log does not know pass through untouched
    perf.validate_event(dict(full, bass=None, nns=None, nns_key=None, key_conf=None, locked=False))
    for field, value in [("bass", 9), ("nns", ["1"]), ("nns_key", False), ("key_conf", 0.82), ("locked", None),
                         ("locked", "yes")]:
        with pytest.raises(perf.BadEvent, match=field):
            perf.validate_event(dict(full, **{field: value}))

    for by in perf.SOUND_END_BY:
        perf.validate_event({"t_ms": 5, "kind": "sound_end", "note": 60, "by": by})
    for bad in [{"t_ms": 5, "kind": "sound_end", "note": 60}, {"t_ms": 5, "kind": "sound_end", "note": 60, "by": "lift"},
                {"t_ms": 5, "kind": "sound_end", "note": 128, "by": "pedal"}]:
        with pytest.raises(perf.BadEvent):
            perf.validate_event(bad)


def test_sound_ends_are_counted_and_described():
    events = [_pedal(0, True), _on(0, 60), _on(0, 64), _off(300, 60), _off(300, 64), _on(500, 67), _off(700, 67),
              _on(800, 67), {"t_ms": 800, "kind": "sound_end", "note": 67, "by": "repeat"}, _off(900, 67),
              _pedal(1000, False)]
    events += [{"t_ms": 1000, "kind": "sound_end", "note": n, "by": "pedal"} for n in (60, 64, 67)]
    events += [_on(1200, 72), _off(1400, 72), {"t_ms": 1400, "kind": "sound_end", "note": 72, "by": "release"}]
    s = perf.summarize(events)
    assert s["event_counts"]["sound_end"] == 5
    assert s["sound_ends"] == {"events": 5, "by": {"release": 1, "pedal": 3, "repeat": 1, "all-off": 0},
                               "share": {"release": 0.2, "pedal": 0.6, "repeat": 0.2, "all-off": 0.0}}
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert "The piano recorded how 5 sounds ended: 20% at the key release, 60% at a pedal lift, 20% re-struck" in md
    assert perf.summarize([_on(0, 60)])["sound_ends"] == {"events": 0, "by": dict.fromkeys(perf.SOUND_END_BY, 0),
                                                          "share": None}


def test_chord_numbers_come_from_the_shared_nashville_reader():
    from arsenal import nashville as nv  # the overlay's twin; its own fixture covers the theory
    triad = ["C4", "E4", "G4"]
    for chord, key in [("G7/B", "C major"), ("Bb", "C major"), ("Fm", "C major"), ("Dm7", "C major"),
                       ("Bbm7b5", "C major"), ("E7", "A minor"), ("D", "A minor"), ("Gsus4", "C major")]:
        want = nv.nashville_from_name(chord, key)
        assert perf.chord_number(chord, key, triad) == {"number": want["text"], "outside_key": not want["diatonic"]}
    assert perf.chord_number("G7/B", "C major", triad) == {"number": "5^7/7", "outside_key": False}
    assert perf.chord_number("Bb", "C major", triad) == {"number": "b7", "outside_key": True}
    assert perf.chord_number("C5", "C major", ["C3", "G3"]) == {"number": "1^5", "outside_key": False}
    # Not chords: a note (even one piano.js names like "C" in octaves), an interval, a cluster, no key.
    assert perf.chord_number("C", "C major", ["C3", "C4"]) is None
    assert perf.chord_number("C5", "C major", ["C5"]) is None
    assert perf.chord_number("C-E", "C major", ["C4", "E4"]) is None
    assert perf.chord_number("C Db D", "C major", ["C4", "Db4", "D4"]) is None
    assert perf.chord_number("C", None, triad) is None and perf.chord_number("C", "C dorian", triad) is None


def test_a_broken_numbers_reader_leaves_the_numbers_out_and_nothing_else(monkeypatch):
    monkeypatch.setattr(perf, "_numbers_reader", lambda: (None, "SyntaxError: half-written"))
    s = perf.summarize(loop_session(loops=1))
    assert s["numbers"]["source"] == {"piano": 0, "analyzer": 0, "reader": "unavailable (SyntaxError: half-written)"}
    assert s["numbers"]["top"] == [] and s["chords"]["top"] and s["key"]["best"]["key"] == "C major"
    assert s["nashville"]["key"]["key"] == "C major" and s["nashville"]["top"] == []  # the key needs no reader
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert "## Nashville" not in md and "## Glossary" not in md and "## Chords" in md


def test_numbers_prefer_the_pianos_own_reading_and_flag_time_outside_the_key():
    def chord(t, name, notes, **extra):
        return dict({"t_ms": t, "kind": "chord", "chord": name, "notes": notes, "key": "C major"}, **extra)

    events = [_on(0, 60), _on(0, 64), _on(0, 67),
              chord(0, "C", ["C4", "E4", "G4"], nns="I", nns_key="C major"),   # the piano's text wins for the label
              chord(1000, "Bb", ["Bb3", "D4", "F4"]),
              chord(2000, "Fm", ["F3", "Ab3", "C4"]),
              chord(3000, "C", ["C4", "E4", "G4"]),
              chord(4000, "Am", ["A3", "C4", "E4"], nns_key="A minor"),        # a key change: numbered in A minor
              _off(5000, 60)]
    s = perf.summarize(events)
    n = s["numbers"]
    assert n["source"] == {"piano": 1, "analyzer": 4, "reader": "arsenal.nashville"}
    assert [(t["key"], t["number"], t["seconds"], t["outside_key"]) for t in n["top"]] == [
        ("A minor", "1m", 1.0, False), ("C major", "1", 1.0, False), ("C major", "4m", 1.0, True),
        ("C major", "I", 1.0, False), ("C major", "b7", 1.0, True)]
    assert n["keys"] == [{"key": "C major", "seconds": 4.0, "share_of_numbered_time": 0.8},
                         {"key": "A minor", "seconds": 1.0, "share_of_numbered_time": 0.2}]
    assert n["outside_key"] == {"seconds": 2.0, "share_of_numbered_time": 0.4,
                                "chords": [{"chord": "Bb", "number": "b7", "key": "C major", "seconds": 1.0},
                                           {"chord": "Fm", "number": "4m", "key": "C major", "seconds": 1.0}]}
    # moves stay inside one key; the C major -> A minor change is not a number move
    assert [(p["from"], p["to"]) for p in n["progressions"]] == [("I", "b7"), ("b7", "4m"), ("4m", "1")]

    # the session-key view: one key for every chord, with the page's own key and numbers kept beside it
    nv = s["nashville"]
    assert nv["key"]["key"] == "C major"
    assert [row["number"] for row in nv["timeline"]] == ["1", "b7", "4m", "1", "6m"]  # Am is plain 6m in C major
    assert [(o["number"], o["chord"], o["kind"], o["borrowed_from"], o["times"])
            for o in nv["outside_key"]["by_number"]] == [("b7", "Bb", "borrowed", "C minor", ["0:01"]),
                                                          ("4m", "Fm", "borrowed", "C minor", ["0:02"])]
    assert nv["page"]["key_source"] == "nns_key"
    assert nv["page"]["changes"] == [{"at": "0:04", "t_s": 4.0, "from": "C major", "to": "A minor"}]
    assert nv["page"]["numbers"] == {"chords": 1, "in_session_key": 1, "agree": 0, "differ_count": 1, "unread": 0,
                                     "differ": [{"at": "0:00", "chord": "C", "page": "I", "session": "1"}],
                                     "other_keys": []}
    assert s["questions"][0] == ("At 0:01 you played a b7 (Bb) in C major, a borrowed chord (it belongs to C minor). "
                                 "What were you reaching for there?")
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert "- At 0:01: b7 (Bb), borrowed from C minor, 1.0 s in all." in md
    assert "- At 0:04 the piano page's key changed from C major to A minor." in md
    assert "- Counted in A minor instead, the page's key from 0:04: 1m for 1.0 s." in md
    assert "- At 0:00 the piano page wrote C as I; here it is 1." in md
    assert "| 0:01 | b7 * | Bb | 1.0 |" in md


def test_page_numbers_on_notes_and_intervals_are_compared_like_with_like():
    """The page numbers single notes and intervals too. Read the way the page read them (detect_kind, or one pitch
    class in notes), they agree with the summary; a name the summary cannot read is unread, never a difference."""
    events, t = [], 0
    for chord, notes in [("Eb", [39, 55, 58, 63]), ("Ab", [44, 56, 60, 63]), ("Bb", [46, 58, 62, 65]),
                         ("Eb", [39, 55, 58, 63])] * 2:
        events += bar(t, chord, notes, "Eb major", pedal=False)
        t += 3000

    def page(dt, name, notes, nns, **extra):
        return dict({"t_ms": t + dt, "kind": "chord", "chord": name, "notes": notes, "key": "Eb major", "nns": nns,
                     "nns_key": "Eb major"}, **extra)

    events += [_on(t, 41), page(0, "F2", ["F2"], "2", detect_kind="note"),
               page(500, "F-Ab", ["F3", "Ab3"], "2-4", detect_kind="interval"),
               page(1000, "G5", ["G5"], "3", detect_kind="note"),  # one note in octave 5, not a G power chord
               page(1500, "F", ["F3", "F4"], "2"),                  # octaves from a page without detect_kind
               page(2000, "H7", ["C4"], "7"),                       # a name the summary cannot read
               _off(t + 2500, 41)]
    s = perf.summarize(events)
    assert s["nashville"]["key"]["key"] == "Eb major"
    numbers = s["nashville"]["page"]["numbers"]
    assert {k: numbers[k] for k in ("chords", "in_session_key", "agree", "differ_count", "unread")} == {
        "chords": 5, "in_session_key": 5, "agree": 4, "differ_count": 0, "unread": 1}
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert ("- The piano page wrote its own number on 5 chords; 4 of the 4 it counted in Eb major match these. "
            "1 more is a name this summary cannot read.") in md.splitlines()
    assert perf.chord_number("G5", "Eb major", ["G5"], detect_kind="note") is None       # a note gets no chord number
    assert perf.chord_number("G5", "Eb major", ["G2", "D3"])["number"] == "3^5"          # a power chord does


def bar(t, chord, notes, key, bar_ms=3000, pedal=True, **extra):
    """One chord struck at t and held for the bar; with pedal, the pedal is changed right after the strike."""
    events = [_pedal(t, False)] if pedal and t else []
    events += [_on(t, m, 70) for m in notes]
    events.append(dict({"t_ms": t, "kind": "chord", "chord": chord, "notes": [spelled(m) for m in notes], "key": key},
                       **extra))
    if pedal:
        events.append(_pedal(t + 100, True))
    return events + [_off(t + bar_ms - 200, m) for m in notes]


F_LOOP = [("F/A", [45, 53, 57, 60, 65, 69]), ("C/G", [43, 52, 55, 60, 64, 67]), ("Dm", [38, 50, 53, 57, 62, 65]),
          ("Bbmaj7", [46, 50, 53, 57, 58, 62])]  # the voicings of the wash check at 80 bpm


def f_major_session():
    """Four passes of F/A C/G Dm Bbmaj7, 3 s a chord with the pedal changed per chord, then two separate Eb chords."""
    events, t = [], 0
    for _ in range(4):
        for chord, notes in F_LOOP:
            events += bar(t, chord, notes, "F major")
            t += 3000
    events.append(_pedal(t, False))
    for _ in range(2):
        events += bar(t, "Eb", [39, 55, 58, 63], "F major", pedal=False)
        events.append({"t_ms": t + 2800, "kind": "chord", "chord": None, "notes": [], "key": None})
        t += 4000
    return events


def test_the_leading_tone_rule_never_hands_a_minor_key_to_its_parallel_major():
    """Am Dm E Am with the E chord's G# struck lightly: the rule may sink A minor toward C major, its relative
    major, but never under A major. Without that floor these weights were numbered in A major (verifier, 2026-09-14)."""
    weights = [0.0] * 12
    for pc, w in {9: 10, 0: 4, 4: 8, 2: 4, 5: 2, 8: 1, 11: 2}.items():
        weights[pc] = w
    key = perf.estimate_key(weights)
    assert key["best"]["key"] == "A minor"
    nkey = perf.numbering_key(weights, key)
    assert nkey["key"] == "A minor" and nkey["rule"] is None


TRIAD = {"Am": (9, 3), "G": (7, 4), "F": (5, 4), "Em": (4, 3), "D": (2, 4), "C": (0, 4), "Dm": (2, 3), "Bb": (10, 4),
         "A": (9, 4), "Bm": (11, 3), "Eb": (3, 4), "Ab": (8, 4), "Cm": (0, 3), "Gm": (7, 3), "Db": (1, 4), "Gb": (6, 4)}


def triad_loop(chords, key, loops=10, bar_ms=2400):
    """Block triads over their roots, one chord a bar, the pedal changed per chord."""
    events, t = [], 0
    for _ in range(loops):
        for name in chords:
            root, third = TRIAD[name]
            events += bar(t, name, [36 + root, 60 + root, 60 + root + third, 60 + root + 7], key, bar_ms=bar_ms)
            t += bar_ms
    return events


@pytest.mark.parametrize("chords, estimate, want, minor_key, left_out", [
    (["Am", "G", "F", "G"], "G major", "C major", "A minor", "F"),
    (["Em", "D", "C", "D"], "D major", "G major", "E minor", "C"),
    (["Dm", "C", "Bb", "C"], "C major", "F major", "D minor", "Bb")])
def test_the_home_chord_rule_numbers_an_aeolian_loop_in_the_key_the_piano_shows(chords, estimate, want, minor_key, left_out):
    """i-bVII-bVI-bVII weighs like ii-I-bVII-I a step lower (Am G F G like G major), but its minor chord sounds as a
    chord with every note on its scale, while G major leaves out F, a quarter of the chords. The piano's key tracker
    shows C major there; the summary numbered the loop 2m 1 b7 1 in G major (verifier, 2026-09-14)."""
    s = perf.summarize(triad_loop(chords, want))
    nv = s["nashville"]
    rule = nv["key"]["rule"]
    assert s["key"]["best"]["key"] == estimate
    assert nv["key"]["key"] == want and rule["name"] == "home chord" and rule["demoted"] == estimate
    assert (rule["home_chord"], rule["minor_key"], rule["relative_major"], rule["left_out"]) == (chords[0], minor_key, want, left_out)
    assert rule["home_share"] >= 0.24 and rule["left_out_share"] >= perf.HOME_OUT
    assert [n["number"] for n in nv["top"]][:3] == ["5", "6m", "4"]

    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert (f"Your notes weigh most like {estimate} (r {rule['r']:.2f}), but {chords[0]} sounded for "
            f"{perf._pct(rule['home_share'])} of the chord time and nearly every note is on {minor_key}'s scale, while "
            f"{estimate} leaves out {left_out}") in md
    assert f"so the numbers count from {want} instead, the way the piano's key tracker decides." in md
    terms = glossary_terms(md)
    assert "home chord" in terms and "raised 7th" not in terms and terms.index("home chord") < terms.index("r")
    assert any(q.startswith(f"Your notes weigh most like {estimate}") and q.endswith(
        f"Did {chords[0]} feel like home ({minor_key}), or were you thinking in {want}?") for q in s["questions"])


def test_the_home_chord_rule_leaves_loops_without_that_evidence_alone():
    """D C G D weighs exactly like Am G F G a fifth up, but no Em sounds, so it stays D major; Am Dm G C sounds its Am,
    and C major, the key it is in, is the best of that minor chord's pair already."""
    for chords, want in ((["D", "C", "G", "D"], "D major"), (["Am", "Dm", "G", "C"], "C major")):
        nv = perf.summarize(triad_loop(chords, want))["nashville"]
        assert nv["key"]["key"] == want and nv["key"]["rule"] is None, chords


def test_home_chords_counts_a_minor_triad_over_the_bass_under_any_name():
    """With the pedal down, melody notes rename an Am bar (C6/9/A, a cluster); Am/C is minor by its name. An interval,
    a cluster with no minor triad over its bass, and silence are no chord time."""
    events = [{"t_ms": 0, "kind": "chord", "chord": "C6/9/A", "notes": ["A2", "C4", "E4", "G4", "D5"], "detect_kind": "chord"},
              {"t_ms": 1000, "kind": "chord", "chord": "A C E B F G", "notes": ["A2", "C4", "E4", "B4", "F5", "G5"],
               "detect_kind": "cluster"},
              {"t_ms": 2000, "kind": "chord", "chord": "Am/C", "notes": ["C3", "E4", "A4"]},
              {"t_ms": 3000, "kind": "chord", "chord": "G", "notes": ["G2", "B3", "D4"], "detect_kind": "chord"},
              {"t_ms": 4000, "kind": "chord", "chord": "C-E", "notes": ["C4", "E4"], "detect_kind": "interval"},
              {"t_ms": 4500, "kind": "chord", "chord": "C Db D", "notes": ["C4", "Db4", "D4"], "detect_kind": "cluster"},
              {"t_ms": 5000, "kind": "chord", "chord": None, "notes": []}]
    homes = perf.home_chords(events, 6000)
    assert homes["chord_ms"] == 4000 and homes["minor_ms"][9] == 3000 and sum(homes["minor_ms"]) == 3000


def test_an_f_major_session_numbers_its_loop_and_flags_the_borrowed_b7_with_its_times():
    s = perf.summarize(f_major_session())
    nv = s["nashville"]
    # The raw estimate hears D minor (F major's own notes, with Dm voiced low), but no C# ever sounds, so the key
    # tracker's leading-tone rule reads F major, and the numbers count from it.
    assert s["key"]["best"]["key"] == "D minor"
    assert nv["key"]["key"] == "F major" and nv["key"]["estimate"] == "D minor"
    assert nv["key"]["rule"] == {"name": "leading tone", "demoted": "D minor", "leading_tone": "C#",
                                 "leading_tone_share": 0.0, "relative_major": "F major"}
    assert nv["loops"] == [{"numbers": ["1/3", "5/2", "6m", "4maj7"], "length": 4, "count": 4, "first_at": "0:00",
                            "start_s": 0.0, "chords": ["F/A", "C/G", "Dm", "Bbmaj7"], "key": "F major"}]
    assert [row["number"] for row in nv["timeline"]] == ["1/3", "5/2", "6m", "4maj7"] * 4 + ["b7", None, "b7", None]
    assert [(n["number"], n["chord"], n["seconds"], n["outside_key"], n["first_at"]) for n in nv["top"]] == [
        ("1/3", "F/A", 12.0, False, "0:00"), ("5/2", "C/G", 12.0, False, "0:03"), ("6m", "Dm", 12.0, False, "0:06"),
        ("4maj7", "Bbmaj7", 12.0, False, "0:09"), ("b7", "Eb", 5.6, True, "0:48")]
    assert [(p["from"], p["to"], p["count"], p["first_at"]) for p in nv["progressions"][:4]] == [
        ("1/3", "5/2", 4, "0:00"), ("5/2", "6m", 4, "0:03"), ("6m", "4maj7", 4, "0:06"), ("4maj7", "1/3", 3, "0:09")]
    outside = nv["outside_key"]
    assert outside["count"] == 2 and outside["seconds"] == 5.6 and outside["share_of_numbered_time"] == 0.1045
    assert [(m["at"], m["number"], m["chord"], m["kind"], m["borrowed_from"], m["in_page_key"])
            for m in outside["moments"]] == [("0:48", "b7", "Eb", "borrowed", "F minor", False),
                                             ("0:52", "b7", "Eb", "borrowed", "F minor", False)]
    assert nv["page"]["key_source"] == "key" and [k["key"] for k in nv["page"]["keys"]] == ["F major"]

    assert s["questions"][0] == ("At 0:48 you played a b7 (Eb) in F major, a borrowed chord (it belongs to F minor). "
                                 "What were you reaching for there?")
    assert "Your notes weigh most like D minor (r 0.91), but its raised 7th, C#, never sounded, so the numbers read " \
           "F major. Were you thinking in F major or in D minor?" in s["questions"]

    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    lines = md.splitlines()
    for line in ["## Nashville numbers",
                 "Your notes weigh most like D minor (r 0.91), but its raised 7th, C#, never sounded, so the numbers "
                 "count from F major instead, the way the piano's key tracker decides.",
                 "- Loop from 0:00: 1/3 → 5/2 → 6m → 4maj7 (F/A, C/G, Dm, Bbmaj7), 4 times back to back.",
                 "- b7 (Eb, outside the key): 10% of the numbered time, 5.6 s, first at 0:48.",
                 "- At 0:48 and 0:52: b7 (Eb), borrowed from F minor, 5.6 s in all.",
                 "| 0:48 | b7 * | Eb | 2.8 |", "| 0:52 | b7 * | Eb | 2.8 |"]:
        assert line in lines, line
    assert glossary_terms(md) == ["Nashville numbers", "b and #", "m", "maj7", "/", "loop", "borrowed", "raised 7th",
                                  "r"]
    assert "In F major, b7 is Eb." in md and "(F minor for F major)" in md
    assert len(question_lines(md)) == len(s["questions"]) and "None" not in md


def test_an_a_minor_session_numbers_from_the_minor_tonic():
    events, t = [], 0
    for _ in range(4):
        for chord, notes in [("Am", [45, 57, 60, 64]), ("Dm", [38, 57, 62, 65]), ("E", [40, 56, 59, 64])]:
            events += bar(t, chord, notes, "A minor")
            t += 3000
    events += bar(t, "D", [38, 54, 57, 62], "A minor")
    s = perf.summarize(events)
    nv = s["nashville"]
    assert nv["key"]["key"] == "A minor" and nv["key"]["rule"] is None and nv["minor_numbering"] == "tonic"
    assert [(n["number"], n["chord"]) for n in nv["top"]] == [("1m", "Am"), ("4m", "Dm"), ("5", "E"), ("4", "D")]
    assert [(loop["numbers"], loop["count"]) for loop in nv["loops"]] == [(["1m", "4m", "5"], 4)]
    # E (with the raised 7th, G#) is the minor key's own 5; D major belongs to the parallel key, A major
    assert [(o["number"], o["chord"], o["kind"], o["borrowed_from"], o["times"])
            for o in nv["outside_key"]["by_number"]] == [("4", "D", "borrowed", "A major", ["0:36"])]
    assert s["questions"][0] == ("At 0:36 you played a 4 (D) in A minor, a borrowed chord (it belongs to A major). "
                                 "What were you reaching for there?")
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert "1 is the minor home chord itself, 1m" in md and "(A major for A minor)" in md


def test_a_key_change_on_the_page_is_reported_per_key_not_mixed_in():
    c_loop = [("C", [48, 52, 55, 60], "1"), ("G", [43, 50, 55, 59], "5"), ("Am", [45, 52, 57, 60], "6m"),
              ("F", [41, 48, 53, 57], "4")]
    d_loop = [("D", [50, 54, 57, 62], "1"), ("A", [45, 52, 57, 61], "5"), ("Bm", [47, 54, 59, 62], "6m"),
              ("G", [43, 50, 55, 59], "4")]
    events, t = [], 0
    for key, loops, chords in [("C major", 4, c_loop), ("D major", 1, d_loop)]:
        for _ in range(loops):
            for chord, notes, nns in chords:
                events += bar(t, chord, notes, key, bar_ms=2000, pedal=False, nns=nns, nns_key=key)
                t += 2000
    s = perf.summarize(events)
    nv = s["nashville"]
    assert nv["key"]["key"] == "C major"
    page = nv["page"]
    assert page["key_source"] == "nns_key" and [(k["key"], k["first_at"]) for k in page["keys"]] == \
        [("C major", "0:00"), ("D major", "0:32")]
    assert page["changes"] == [{"at": "0:32", "t_s": 32.0, "from": "C major", "to": "D major"}]
    assert page["numbers"] == {"chords": 20, "in_session_key": 16, "agree": 16, "differ_count": 0, "unread": 0, "differ": [],
                               "other_keys": [{"key": "D major", "chords": 4, "first_at": "0:32",
                                               "example": {"chord": "D", "page": "1", "session": "2"}}]}
    # In C major the D major chords are chromatic, and each one says the page had moved to a key it belongs to.
    assert [(m["at"], m["number"], m["chord"], m["kind"], m["page_key"], m["in_page_key"])
            for m in nv["outside_key"]["moments"]] == [("0:32", "2", "D", "chromatic", "D major", True),
                                                       ("0:34", "6", "A", "chromatic", "D major", True),
                                                       ("0:36", "7m", "Bm", "chromatic", "D major", True)]
    assert s["questions"][0] == ("At 0:32 the piano page's key moved from C major to D major. "
                                 "Did you mean to change key there, or did a chord pull it?")
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    lines = md.splitlines()
    for line in ["- At 0:32 the piano page's key changed from C major to D major.",
                 "- At 0:32: 2 (D), chromatic (in neither C major nor C minor), 2.0 s in all; the piano page showed "
                 "D major, where it belongs.",
                 "- From 0:32 the piano page numbered 4 chords in D major (first D: 1 there, 2 here)."]:
        assert line in lines, line
    assert "- Counted in D major instead, the page's key from 0:32: 1 for 2.0 s, 5 for 2.0 s, 6m for 2.0 s" in md
    assert "chromatic" in glossary_terms(md) and "borrowed" not in glossary_terms(md)


def test_a_session_that_moves_key_numbers_each_part_in_its_own_key():
    """F C Dm Bb, then D A Bm G: numbered in one session-wide key, both halves read in D minor, a key neither is in
    (verifier, 2026-09-14). Each part is numbered in the key that fits it, and every line says which key it counts in."""
    second = [dict(e, t_ms=e["t_ms"] + 96000) for e in triad_loop(["D", "A", "Bm", "G"], "D major")]
    s = perf.summarize(triad_loop(["F", "C", "Dm", "Bb"], "F major") + second)
    nv = s["nashville"]
    assert [a["key"]["key"] for a in nv["areas"]] == ["F major", "D major"]
    move = nv["areas"][1]
    assert abs(move["start_s"] - 96.0) <= perf.AREA_SNAP_MS / 1000
    assert {("1", "F major"), ("5", "F major"), ("1", "D major"), ("6m", "D major")} <= {(t["number"], t["key"]) for t in nv["top"]}
    assert nv["outside_key"]["count"] == 0
    assert {(("1", "5", "6m", "4"), "F major"), (("1", "5", "6m", "4"), "D major")} <= \
        {(tuple(loop["numbers"]), loop["key"]) for loop in nv["loops"]}
    assert s["questions"][0] == (f"At {move['at']} the music moved from F major to D major. "
                                 "Did you mean to change key there, or did a chord pull it?")
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert (f"The session changes key, so each part is numbered in the key that fits it: F major from 0:00, "
            f"D major from {move['at']}. Times are minutes:seconds from your first note.") in md
    assert "- Loop from 0:00 in F major: 1 → 5 → 6m → 4 (F, C, Dm, Bb)" in md
    assert "| at | key | number | chord | seconds |" in md and "| 0:00 | F major | 1 | F | 2.4 |" in md
    assert "the key that fits the whole session" not in md


def test_a_long_pause_into_another_key_starts_the_new_part_where_playing_resumes():
    """Daniel's sessions change key across pauses of minutes: the new part starts at the first note after the pause."""
    first = triad_loop(["F", "C", "Dm", "Bb"], "F major", loops=5) + [_pedal(48000, False)]
    second = [dict(e, t_ms=e["t_ms"] + 48000 + 218000) for e in triad_loop(["D", "A", "Bm", "G"], "D major", loops=5)]
    nv = perf.summarize(first + second)["nashville"]
    assert [(a["at"], a["key"]["key"]) for a in nv["areas"]] == [("0:00", "F major"), ("4:26", "D major")]


def test_one_key_with_its_relative_minor_chords_stays_one_part():
    """Am F C G and C G Am F loops, one after the other: the path may hear A minor steps, but both number in C major."""
    second = [dict(e, t_ms=e["t_ms"] + 96000) for e in triad_loop(["C", "G", "Am", "F"], "C major")]
    nv = perf.summarize(triad_loop(["Am", "F", "C", "G"], "C major") + second)["nashville"]
    assert [a["key"]["key"] for a in nv["areas"]] == ["C major"]


def shifted(events, ms):
    return [dict(e, t_ms=e["t_ms"] + ms) for e in events]


def test_chord_moves_are_numbered_in_their_key_area_not_in_the_key_the_page_showed():
    """The Chords section numbered each move in the key the page showed at its first occurrence, which lags a key change:
    F major then D major read D → A as 6 → 3 in F major beside the Nashville section's 1 → 5 in D major, and question 2
    taught those numbers (verifier, 2026-09-14). A move played in two key areas carries both readings."""
    s = perf.summarize(triad_loop(["F", "C", "Dm", "Bb"], "F major") + shifted(triad_loop(["D", "A", "Bm", "G"], "F major"), 96000))
    assert [a["key"]["key"] for a in s["nashville"]["areas"]] == ["F major", "D major"]
    rows = {(p["from"], p["to"]): p.get("numbers") for p in s["chords"]["progressions"]}
    assert (rows[("F", "C")], rows[("D", "A")], rows[("A", "Bm")]) == ("1 → 5 in F major", "1 → 5 in D major", "5 → 6m in D major")
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert "in F major): 10 times" in md and "6 → 3" not in md and "3 → #4m" not in md

    both = perf.summarize(triad_loop(["Bb", "F", "Gm", "Eb"], "Bb major") + shifted(triad_loop(["Eb", "Bb", "Cm", "Ab"], "Bb major"), 96000))
    rows = {(p["from"], p["to"]): p for p in both["chords"]["progressions"]}
    assert rows[("Eb", "Bb")]["numbers"] == "4 → 1 in Bb major; 1 → 5 in Eb major"
    assert any(q.startswith("You spent") and "(19 times, 4 → 1 in Bb major; 1 → 5 in Eb major)" in q for q in both["questions"])


def test_a_session_in_several_keys_asks_about_a_part_not_about_the_blend_of_its_parts():
    """F major then D major weighs most like D minor over the whole session, a key neither part is in, and summary.md asked
    whether Daniel was thinking in D minor (verifier, 2026-09-14). The Key section says the estimate is a blend; the
    question asks about the longest part (the first, on a tie), in that part's own estimate."""
    s = perf.summarize(triad_loop(["F", "C", "Dm", "Bb"], "F major") + shifted(triad_loop(["D", "A", "Bm", "G"], "D major"), 96000))
    blend = s["key"]["best"]["key"]
    assert blend not in ("F major", "D major")
    assert not any(f"thinking in {blend}" in q for q in s["questions"])
    main = s["nashville"]["areas"][0]["key"]
    assert (f"From 0:00 to 1:36 your notes fit F major best (r {main['r']:.2f}), ahead of {main['runner_up']} "
            f"(r {main['runner_up_r']:.2f}). Were you thinking in F major there, or did your hands find it?") in s["questions"]
    md = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **s})
    assert f"Krumhansl-Kessler estimate over sounding seconds per pitch class for the whole session: {blend}" in md
    assert ("The session changes key (F major from 0:00, D major from 1:36), so this estimate is a blend of its parts, "
            "not a key it stayed in; each part is numbered in its own key under Nashville numbers.") in md
    one = perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **perf.summarize(triad_loop(["C", "G", "Am", "F"], "C major"))})
    assert "for the whole session" not in one and "is a blend of its parts" not in one


def test_the_glossary_explains_the_lines_above_it_when_the_session_changes_key():
    """borrowed and chromatic took their example from the longest key area, and contradicted lines counted in another
    part (verifier, 2026-09-14): 'chromatic: neither D major nor D minor' under a line in C major."""
    terms = dict(perf._glossary({"key": "D major", "mode": "major"}, [], {"borrowed", "chromatic"},
                                {"borrowed": "F major", "chromatic": "A minor"}, {"major", "minor"}, True))
    assert terms["borrowed"].startswith("a chord from the parallel key of its part,") and "(F minor for F major)" in terms["borrowed"]
    assert terms["chromatic"] == ("a chord that belongs neither to the key of its part nor to that key's parallel key "
                                  "(in A minor, neither A minor nor A major).")
    assert "(in a minor key, the minor home chord itself, 1m)" in terms["Nashville numbers"]
    one = dict(perf._glossary({"key": "F major", "mode": "major"}, [], {"borrowed", "chromatic"}))
    assert one["chromatic"] == "a chord that belongs to neither F major nor F minor." and "(F minor for F major)" in one["borrowed"]


def test_a_rule_whose_own_key_did_not_win_is_never_named_as_the_cause():
    """F# minor's missing raised 7th counts it lower, and it points to A major, but D major fitted better than A major:
    summary.md said the missing E# made the numbers count from D major (verifier, 2026-09-14). That is a next best."""
    weights = [0, 9, 7, 0, 6, 0, 10, 5, 4, 6, 0, 7]  # C Db D Eb E F F# G Ab A Bb B: no E#, and G outweighs G#
    key = perf.estimate_key(weights)
    nkey = perf.numbering_key(weights, key)
    assert key["best"]["key"] == "F# minor" and nkey["key"] == "D major"
    assert nkey["rule"] == {"name": "next best", "because": "leading tone", "demoted": "F# minor", "leading_tone": "E#",
                            "leading_tone_share": 0.0, "relative_major": "A major"}
    nv = {"key": nkey, "areas": [{"at": "0:00", "start_s": 0.0, "end_s": 60.0, "key": nkey}], "loops": [], "progressions": [],
          "top": [{"number": "1", "chord": "D", "key": "D major", "outside_key": False, "share_of_numbered_time": 1.0,
                   "seconds": 60.0, "first_at": "0:00"}],
          "outside_key": {"by_number": []}, "min_move_ms": 120, "timeline": [], "page": {"changes": []}}
    lines: list = []
    perf._nashville_markdown({"nashville": nv, "key": key}, lines.append)
    assert (f"Your notes weigh most like F# minor (r {key['best']['r']:.2f}), but its raised 7th, E#, never sounded, so the "
            f"piano's key tracker counts F# minor lower; after that D major fits best (r {nkey['r']:.2f}), so the numbers "
            f"count from D major.") in lines
    doc = {"note_count": 10, "nashville": nv, "key": key, "chords": {"progressions": [], "top": [], "changes": 0},
           "pedal": {"presses": 0, "percent_down": None}, "dynamics": None, "timing": {"rough_tempo": None},
           "voicing": {"mean_spread_semitones": None}, "range": None, "notes_per_minute": None,
           "pitch_classes": [{"pc": pc, "name": "CDEFGAB"[0], "count": 1, "seconds": w} for pc, w in enumerate(weights)]}
    assert ("Your notes weigh most like F# minor, but its raised 7th, E#, never sounded, so the piano's key tracker counts "
            "it lower, and then D major fits best. Were you thinking in D major or in F# minor?") in perf.questions(doc)


SEVENTH = {"Cm7": (0, [3, 7, 10]), "F7": (5, [4, 7, 10]), "Bbmaj7": (10, [4, 7, 11]), "Fm7": (5, [3, 7, 10]),
           "Bb7": (10, [4, 7, 10]), "Ebmaj7": (3, [4, 7, 11])}


def seventh_loop(chords, key, loops=10, bar_ms=2400):
    events, t = [], 0
    for _ in range(loops):
        for name in chords:
            root, tones = SEVENTH[name]
            events += bar(t, name, [36 + root, 60 + root] + [60 + root + x for x in tones], key, bar_ms=bar_ms)
            t += bar_ms
    return events


def test_a_key_change_lands_on_the_first_chord_of_the_new_key():
    """Cm7 F7 Bbmaj7 Bbmaj7, then Fm7 Bb7 Ebmaj7 Ebmaj7: the Eb major area started at the Ebmaj7, so Fm7 (the new key's
    2m7) was flagged as a borrowed 5m7 in Bb major and led the questions (verifier, 2026-09-14)."""
    s = perf.summarize(seventh_loop(["Cm7", "F7", "Bbmaj7", "Bbmaj7"], "Bb major")
                       + shifted(seventh_loop(["Fm7", "Bb7", "Ebmaj7", "Ebmaj7"], "Bb major"), 96000))
    nv = s["nashville"]
    assert [(a["at"], a["key"]["key"]) for a in nv["areas"]] == [("0:00", "Bb major"), ("1:36", "Eb major")]
    assert nv["outside_key"]["count"] == 0
    assert s["questions"][0].startswith("At 1:36 the music moved from Bb major to Eb major.")


def test_what_is_played_after_a_long_silence_is_not_carried_into_the_key_before_it():
    """An Eb major session, 27 s of silence, then 12 s in Ab (with its Db): the Ab stretch was joined back over the silence
    and numbered with what came before it (verifier, 2026-09-14). A short part after a long silence keeps its own key when
    the key before the silence leaves out more of it; the same key's chords after the silence still join."""
    eb = triad_loop(["Eb", "Bb", "Cm", "Ab"], "Eb major", loops=13) + [_pedal(124800, False)]
    ab = shifted(triad_loop(["Ab", "Db", "Eb", "Ab"], "Eb major", loops=1, bar_ms=3000), 124800 + 27000)
    areas = perf.summarize(eb + ab)["nashville"]["areas"]
    assert [(a["at"], a["key"]["key"]) for a in areas] == [("0:00", "Eb major"), ("2:31", "Ab major")]
    same = shifted(triad_loop(["Cm", "Ab", "Eb", "Bb"], "Eb major", loops=1, bar_ms=3000), 124800 + 27000)
    assert [a["key"]["key"] for a in perf.summarize(eb + same)["nashville"]["areas"]] == ["Eb major"]

    # an opening phrase in Db, 13 s of silence, then D major: the phrase is not numbered in D major
    db = triad_loop(["Db", "Gb", "Ab", "Db"], "Db major", loops=1, bar_ms=2000) + [_pedal(8000, False)]
    d = shifted(triad_loop(["D", "A", "Bm", "G"], "D major"), 21000)
    areas = perf.summarize(db + d)["nashville"]["areas"]
    assert [(a["at"], a["key"]["key"]) for a in areas] == [("0:00", "Db major"), ("0:21", "D major")]
    # with no silence it still stands, since D major leaves out most of it (AREA_APART_FIT)
    db = triad_loop(["Db", "Gb", "Ab", "Db"], "Db major", loops=1, bar_ms=3000)
    areas = perf.summarize(db + shifted(triad_loop(["D", "A", "Bm", "G"], "D major"), 12000))["nashville"]["areas"]
    assert [a["key"]["key"] for a in areas] == ["Db major", "D major"] and abs(areas[1]["start_s"] - 12) <= 2


def test_a_pedal_held_through_a_long_pause_does_not_sound_the_last_chord_through_it():
    """With the pedal down through a 218 s pause, the last Bb counted as sounding for the whole pause: a Bb major area
    appeared in the silence and led the questions (verifier, 2026-09-14). A note released under the pedal counts for
    PEDAL_RING_MS at most."""
    first = triad_loop(["F", "C", "Dm", "Bb"], "F major", loops=5)  # the last Bb is released with the pedal still down
    s = perf.summarize(first + shifted(triad_loop(["D", "A", "Bm", "G"], "D major", loops=5), 48000 + 218000))
    assert [(a["at"], a["key"]["key"]) for a in s["nashville"]["areas"]] == [("0:00", "F major"), ("4:26", "D major")]
    bb = next(p for p in s["pitch_classes"] if p["pc"] == 10)  # two Bbs in each Bb chord: 4 bars, then the last one rings out
    assert bb["seconds"] == pytest.approx(2 * (4 * 2.4 + 2.2 + perf.PEDAL_RING_MS / 1000))


def test_the_pages_key_is_carried_through_a_short_silence_but_not_a_long_one():
    """The page's key was carried from its last chord event to the session's end: a session read D major for 58% of its
    length, most of it silence (verifier, 2026-09-14)."""
    loop = triad_loop(["F", "C", "Dm", "Bb"], "F major", loops=5, bar_ms=2000)
    rest = {"t_ms": 40000, "kind": "chord", "chord": None, "notes": [], "key": None}
    short = perf.summarize(loop + [rest] + shifted(loop, 45000))["nashville"]["page"]["keys"]
    assert [(k["key"], k["seconds"], k["segments"]) for k in short] == [("F major", 84.8, 1)]  # to the session's end
    notes = [_on(260000, 65), _off(262000, 65), _on(262000, 69), _off(270000, 69)]  # played later, with no chord events
    long = perf.summarize(loop + [rest] + notes)["nashville"]["page"]
    assert [(k["key"], k["seconds"]) for k in long["keys"]] == [("F major", 40.0)] and long["changes"] == []


def test_a_cluster_between_two_chords_does_not_break_the_move_in_either_section():
    """A pedalled cluster once between F6 and G7, straight F6 -> G7 twice: Chords counted that move 2 times and Nashville
    numbers 3 times, since a shape with no number never broke a move there. Both sections count 3 now."""
    shapes = [("F6", [41, 57, 60, 62, 65]), ("G7", [43, 53, 55, 59, 62]), ("C", [36, 55, 60, 64, 67])]
    events, t = [], 0
    for i in range(3):
        for chord, notes in shapes:
            events += bar(t, chord, notes, "C major", bar_ms=2400)
            if chord == "F6" and i == 1:
                events.append({"t_ms": t + 1200, "kind": "chord", "chord": "F A C D E", "detect_kind": "cluster",
                               "notes": ["F2", "A3", "C4", "D4", "E4"], "key": "C major"})
            t += 2400
    s = perf.summarize(sorted(events, key=lambda e: e["t_ms"]))
    chords = {(p["from"], p["to"]): p["count"] for p in s["chords"]["progressions"]}
    numbers = {(p["from"], p["to"]): p["count"] for p in s["nashville"]["progressions"]}
    assert chords[("F6", "G7")] == 3 and numbers[("4^6", "5^7")] == 3
    assert not any("F A C D E" in move for move in chords)


def test_counts_of_one_read_naturally_everywhere():
    one = [_pedal(0, True), _on(0, 60), {"t_ms": 0, "kind": "chord", "chord": "C4", "notes": ["C4"], "key": None},
           _pedal(100, False), _off(1000, 60), {"t_ms": 1000, "kind": "sound_end", "note": 60, "by": "release"}]
    gaps = [_on(0, 60), _off(200, 60), _on(500, 64), _off(700, 64), _on(3000, 67), _off(3200, 67)]
    mds = [perf.render_markdown({"session": "x", "opened_at": None, "closed_at": None, **perf.summarize(evs)})
           for evs in (one, gaps)]
    for phrase in ("1 note (", "1 press (", "1 onset (", "how 1 sound ended", "over 1 note)"):
        assert phrase in mds[0], phrase
    assert "Most common gaps between onsets: 500-550 ms (1); 1 gap of 2000 ms or more." in mds[1]
    for md in mds:
        for wrong in ("1 notes", "1 presses", "1 onsets", "1 gaps", "1 sounds", "1 semitones", "1 chord changes",
                      "1 chord events", "1 times"):
            assert wrong not in md, wrong


def _md_table(md, heading):
    """The table rows under a summary.md heading that starts with `heading`."""
    return md.split(heading, 1)[1].split("\n\n")[1].splitlines()[2:]


def test_markdown_tables_leave_passing_shapes_out_but_keep_their_counts():
    events = loop_session(loops=2)
    for t in (3900, 11900):  # a 100 ms G7 on the way from G to Am, each loop
        events.append({"t_ms": t, "kind": "chord", "chord": "G7", "notes": ["G2", "D3", "F3", "B3"], "key": "C major"})
    events.sort(key=lambda e: e["t_ms"])
    s = perf.summarize(events)
    md = perf.render_markdown(s)

    timeline = s["chords"]["timeline"]
    short = [seg for seg in timeline if seg["seconds"] < 0.3]
    assert [seg["chord"] for seg in short if seg["chord"]] == ["G7", "G7"]  # summary.json keeps every segment
    assert (f"Timeline (first {len(timeline) - len(short)} of {len(timeline)} segments; "
            f"the {len(short)} under 0.3 s are not listed):") in md
    rows = _md_table(md, "Timeline (")
    assert len(rows) == len(timeline) - len(short) and not any("G7" in r for r in rows)

    numbered = [seg for seg in s["nashville"]["timeline"] if seg["number"] is not None]
    assert [seg["number"] for seg in numbered if seg["seconds"] < 0.3] == ["5^7", "5^7"]
    assert (f"Numbers over time (first {len(numbered) - 2} of {len(numbered)} numbered stretches; "
            f"the 2 under 0.3 s are not listed):") in md
    rows = _md_table(md, "Numbers over time (")
    assert [r.split(" | ")[1] for r in rows] == ["1", "5", "6m", "4", "1", "5", "6m", "4"]

    blink = [{"t_ms": 0, "kind": "on", "note": 60, "vel": 60},
             {"t_ms": 0, "kind": "chord", "chord": "C", "notes": ["C4"], "key": None},
             {"t_ms": 100, "kind": "chord", "chord": "G", "notes": ["G4"], "key": None},
             {"t_ms": 200, "kind": "chord", "chord": None, "notes": [], "key": None},
             {"t_ms": 250, "kind": "off", "note": 60}]
    assert "Timeline: all 3 segments lasted under 0.3 s, so none are listed." in perf.render_markdown(perf.summarize(blink))


def test_a_count_of_one_reads_once():
    events = [e for e in loop_session(loops=1, pedal=False) if e["kind"] != "pedal"]
    events += [{"t_ms": 100, "kind": "pedal", "down": True, "value": 127},
               {"t_ms": 1000, "kind": "pedal", "down": False, "value": 0}]
    events.sort(key=lambda e: e["t_ms"])
    s = perf.summarize(events)
    md = perf.render_markdown(s)
    assert "- C → G (1 → 5 in C major): once, " in md
    assert "- Move 1 → 5 (C → G): once, first at 0:00." in md
    assert "You pressed the pedal once against 3 chord changes, holding it 0.9 s. How do you decide" in md
    assert "1 times" not in md


def test_the_glossary_gives_extended_shapes_their_own_meanings():
    nkey = {"key": "C major", "mode": "major"}
    fallback = perf._EXTENSIONS.get("no such shape", "extra stacked notes, named by their distance above the root.")
    shown = [("5^11", "G11"), ("2m11", "Dm11"), ("5add11", "Gadd11"), ("5^9sus4", "G9sus4"), ("1maj13", "Cmaj13"),
             ("4^6/9", "F6/9"), ("5^7#5", "G7#5"), ("1maj7#5", "Cmaj7#5"), ("5^7b5", "G7b5"), ("5^7b9", "G7b9"),
             ("5^7#9", "G7#9"), ("4maj7#11", "Fmaj7#11"), ("5^7#11", "G7#11"), ("5^13", "G13"), ("2m13", "Dm13")]
    terms = dict(perf._glossary(nkey, shown, set()))
    for term in ("11", "m11", "add11", "9sus4", "maj13", "6/9", "7#5", "maj7#5", "7b5", "7b9", "7#9", "maj7#11", "7#11",
                 "13", "m13"):
        assert term in terms and terms[term] != fallback, term
        assert terms[term].count(".") == 1 and len(terms[term]) < 120, "one line each"
    assert "m" in terms and "^" in terms
    assert "/" not in terms and "6" not in terms, "6/9 is one shape, not a 6 chord over the 9"
    over = dict(perf._glossary(nkey, [("4^6/9/5", "F6/9/C")], set()))
    assert "6/9" in over and "/" in over


def test_clock_and_loop_helpers():
    assert [perf._clock(ms) for ms in (0, 59_999, 192_000, 3_723_000)] == ["0:00", "0:59", "3:12", "1:02:03"]
    labels = "5 1 4 5 1 4 5 1 4 6m 2m 6m 2m".split()
    runs = [{"label": label, "first": {"t_ms": i * 1000, "chord": label}} for i, label in enumerate(labels)]
    # one cycle shown once, in the rotation played most; a two-chord vamp and non-repeating runs are not loops
    assert perf._loops(runs) == [{"numbers": ["5", "1", "4"], "length": 3, "count": 3, "first_at": "0:00",
                                  "start_s": 0.0, "chords": ["5", "1", "4"]}]


def test_rough_tempo_stays_fast_on_an_hour_of_onsets():
    events = [_on(i * 500 + (i % 3) * 7, 60 + i % 12) for i in range(7200)]  # an hour at 120 BPM, a little jitter
    s = perf.summarize(events)
    assert s["timing"]["rough_tempo"]["support"] == 7199 and round(s["timing"]["rough_tempo"]["bpm"]) == 120


# ================================================================================================== routes
@pytest.fixture()
def server(tmp_path):
    root = tmp_path / "performance"
    srv = Server(0, App([str(tmp_path)], takes_root=tmp_path / "takes", performance_root=root))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}", root
    srv.shutdown()
    srv.server_close()


def _request(method, url, body=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode("utf-8") if body is not None else None)
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read() or b"null")


def test_session_lifecycle_over_http(server):
    base, root = server
    status, opened = _request("POST", base + "/api/performance/open", {"meta": {"page": "test"}})
    assert status == 200 and re.fullmatch(r"\d{8}-\d{6}-[0-9a-f]{8}", opened["session"])
    session = opened["session"]
    folder = root / session
    info = json.loads((folder / "session.json").read_text(encoding="utf-8"))
    assert info["closed"] is False and info["event_count"] == 0 and info["meta"] == {"page": "test"}
    assert "opened_at" in info and (folder / "events.jsonl").read_text(encoding="utf-8") == ""

    assert _request("GET", f"{base}/api/performance/{session}") == (200, {"session": session, "summary": None})

    events = loop_session(loops=2)
    status, body = _request("POST", f"{base}/api/performance/{session}/events", {"events": events[:30]})
    assert status == 200 and body == {"accepted": 30}

    # A malformed event refuses the whole batch: nothing from it is written.
    written = (folder / "events.jsonl").read_text(encoding="utf-8")
    status, body = _request("POST", f"{base}/api/performance/{session}/events",
                            {"events": events[30:32] + [{"t_ms": 5, "kind": "on", "note": 60}]})
    assert status == 400 and "vel" in body["error"]
    assert (folder / "events.jsonl").read_text(encoding="utf-8") == written
    assert _request("POST", f"{base}/api/performance/{session}/events", {"nope": []})[0] == 400
    assert _request("POST", f"{base}/api/performance/{session}/events", raw=b"{not json")[0] == 400

    # close carries the final events too, the way the pagehide beacon sends them
    status, body = _request("POST", f"{base}/api/performance/{session}/close", {"events": events[30:]})
    assert status == 200
    summary = body["summary"]
    assert summary["session"] == session and summary["key"]["best"]["key"] == "C major"
    assert summary["duration_s"] == 16.0 and summary["opened_at"] == info["opened_at"]
    assert json.loads((folder / "summary.json").read_text(encoding="utf-8")) == summary
    md = (folder / "summary.md").read_text(encoding="utf-8")
    assert md.startswith(f"# Practice session {session}") and "## Questions for Daniel" in md

    listed = _request("GET", base + "/api/performance")[1]["sessions"]
    assert listed == [{"session": session, "opened_at": info["opened_at"], "closed": True,
                       "event_count": len(events), "duration_s": 16.0}]
    assert _request("GET", f"{base}/api/performance/{session}") == (200, {"session": session, "summary": summary})

    assert _request("POST", f"{base}/api/performance/{session}/events", {"events": events[:1]})[0] == 409
    assert _request("POST", f"{base}/api/performance/{session}/close", {})[0] == 409


def test_close_with_final_events_in_one_millisecond_under_the_pedal(server):
    base, root = server
    session = _request("POST", base + "/api/performance/open", {"meta": {}})[1]["session"]
    final = DEGENERATE_SESSIONS["zero_ms_pedal_chord"]
    status, body = _request("POST", f"{base}/api/performance/{session}/close", {"events": final})
    assert status == 200, body
    assert body["summary"]["pedal"]["presses"] == 1 and len(body["summary"]["questions"]) >= 3
    folder = root / session
    assert len((folder / "events.jsonl").read_text(encoding="utf-8").splitlines()) == len(final)
    info = json.loads((folder / "session.json").read_text(encoding="utf-8"))
    assert info["closed"] is True and info["event_count"] == len(final)
    assert (folder / "summary.md").is_file() and (folder / "summary.json").is_file()
    assert _request("POST", f"{base}/api/performance/{session}/close", {"events": final})[0] == 409
    assert len((folder / "events.jsonl").read_text(encoding="utf-8").splitlines()) == len(final)


def test_a_failed_close_writes_nothing_so_a_retry_stores_the_final_events_once(tmp_path, monkeypatch):
    store = perf.PerformanceStore(tmp_path)
    session = store.open()
    store.append(session, [_on(0, 60)])
    folder = tmp_path / session
    before = {name: (folder / name).read_bytes() for name in ("session.json", "events.jsonl")}

    def broken(doc):
        raise RuntimeError("render failed")
    monkeypatch.setattr(perf, "render_markdown", broken)
    with pytest.raises(RuntimeError):
        store.close(session, [_off(500, 60)])
    assert {name: (folder / name).read_bytes() for name in before} == before
    assert not (folder / "summary.json").exists() and not (folder / "summary.md").exists()

    monkeypatch.undo()
    doc = store.close(session, [_off(500, 60)])
    assert doc["event_counts"] == {"on": 1, "off": 1, "pedal": 0, "chord": 0, "sound_end": 0}
    assert len(store.events(session)) == 2 and store.info(session)["event_count"] == 2
    with pytest.raises(perf.BadEvent):  # a malformed final batch is refused before anything is written
        store.close(store.open(), [{"t_ms": 0, "kind": "on", "note": 60}])


def test_unknown_sessions_bad_bodies_and_ordering(server):
    base, root = server
    ghost = "20260101-000000-00000000"
    assert _request("POST", f"{base}/api/performance/{ghost}/events", {"events": []})[0] == 404
    assert _request("POST", f"{base}/api/performance/{ghost}/close", {})[0] == 404
    assert _request("GET", f"{base}/api/performance/{ghost}")[0] == 404
    assert _request("GET", f"{base}/api/performance/not-a-session")[0] == 404
    assert _request("POST", base + "/api/performance/open", {"meta": "nope"})[0] == 400
    assert _request("POST", base + "/api/performance/open", raw=b"[1,")[0] == 400
    assert _request("GET", base + "/api/performance") == (200, {"sessions": []})

    first = _request("POST", base + "/api/performance/open", {})[1]["session"]
    second = _request("POST", base + "/api/performance/open", {"meta": {}})[1]["session"]
    assert _request("POST", f"{base}/api/performance/{second}/events",
                    {"events": [{"t_ms": 2500, "kind": "on", "note": 60, "vel": 64}]}) == (200, {"accepted": 1})
    sessions = _request("GET", base + "/api/performance")[1]["sessions"]
    assert [s["session"] for s in sessions] == [second, first]
    assert sessions[0]["duration_s"] == 2.5 and sessions[0]["event_count"] == 1 and sessions[0]["closed"] is False


def test_uploads_are_idempotent_by_client_id_and_seq(server):
    """What the browser's offline buffer relies on: a reload that resends an open, a batch or a close stores nothing twice."""
    base, root = server
    status, first = _request("POST", base + "/api/performance/open",
                             {"meta": {"buffered": True, "opened_at_client": "2026-09-13T21:00:00.000Z"},
                              "client_id": "mf1x2y-0a1b2c3d"})
    assert status == 200 and first["resumed"] is False and first["closed"] is False and first["last_seq"] == -1
    session = first["session"]
    again = _request("POST", base + "/api/performance/open", {"meta": {}, "client_id": "mf1x2y-0a1b2c3d"})[1]
    assert again == {"session": session, "resumed": True, "closed": False, "last_seq": -1}
    assert len(_request("GET", base + "/api/performance")[1]["sessions"]) == 1
    assert _request("POST", base + "/api/performance/open", {"client_id": "not ok!"})[0] == 400

    events = loop_session(loops=1)
    url = f"{base}/api/performance/{session}/events"
    assert _request("POST", url, {"events": events[:10], "seq": 0}) == \
        (200, {"accepted": 10, "duplicate": False, "last_seq": 0})
    assert _request("POST", url, {"events": events[:10], "seq": 0}) == \
        (200, {"accepted": 0, "duplicate": True, "last_seq": 0})
    assert _request("POST", url, {"events": events[10:20], "seq": 1})[1]["accepted"] == 10
    assert _request("POST", url, {"events": events[20:], "seq": "2"})[0] == 400
    assert _request("POST", base + "/api/performance/open", {"client_id": "mf1x2y-0a1b2c3d"})[1]["last_seq"] == 1

    # the close carries the last batch under the next seq; resending it, or the batch, answers 409 with last_seq
    status, body = _request("POST", f"{base}/api/performance/{session}/close", {"events": events[20:], "seq": 2})
    assert status == 200 and body["summary"]["meta"]["buffered"] is True
    assert _request("POST", f"{base}/api/performance/{session}/close", {"events": events[20:], "seq": 2}) == \
        (409, {"error": f"session {session} is already closed", "last_seq": 2})
    assert _request("POST", url, {"events": events[20:], "seq": 2})[1]["last_seq"] == 2
    assert _request("POST", base + "/api/performance/open", {"client_id": "mf1x2y-0a1b2c3d"})[1] == \
        {"session": session, "resumed": True, "closed": True, "last_seq": 2}
    stored = (root / session / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(stored) == len(events) and json.loads((root / session / "session.json").read_text())["event_count"] == \
        len(events)
    md = (root / session / "summary.md").read_text(encoding="utf-8")
    assert "Played from 2026-09-13 21:00:00 UTC by the browser's clock" in md


def test_a_close_whose_final_batch_already_arrived_does_not_store_it_twice(tmp_path):
    store = perf.PerformanceStore(tmp_path)
    session = store.open(client_id="abc")
    assert store.append_batch(session, [_on(0, 60)], seq=0)["accepted"] == 1
    store.append_batch(session, [_off(400, 60)], seq=1)
    doc = store.close(session, [_off(400, 60)], seq=1)  # the beacon's batch had been uploaded already
    assert doc["event_counts"]["off"] == 1 and len(store.events(session)) == 2
    with pytest.raises(perf.SessionClosed) as err:
        store.append_batch(session, [_on(500, 60)], seq=2)
    assert err.value.extra == {"last_seq": 1}
    with pytest.raises(perf.BadEvent):
        store.append_batch(session, [], seq=-1)


def test_the_log_can_be_switched_off_to_answer_like_a_server_without_the_routes(tmp_path):
    srv = Server(0, App([str(tmp_path)], takes_root=tmp_path / "takes", performance_root=tmp_path / "performance",
                        performance_log=False))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        ghost = "20260101-000000-00000000"
        for method, path in [("POST", "/api/performance/open"), ("POST", f"/api/performance/{ghost}/events"),
                             ("POST", f"/api/performance/{ghost}/close"), ("GET", "/api/performance"),
                             ("GET", f"/api/performance/{ghost}")]:
            assert _request(method, base + path, {} if method == "POST" else None) == \
                (404, {"error": f"no route for {method} {path}"})
        assert _request("GET", base + "/api/health")[0] == 200
        assert not (tmp_path / "performance").exists()
    finally:
        srv.shutdown()
        srv.server_close()


# ===================================================================================================== CLI
def test_cli_lists_sessions_and_prints_summaries(tmp_path, capsys):
    store = perf.PerformanceStore(tmp_path)
    closed = store.open({"page": "cli"})
    store.append(closed, loop_session(loops=1))
    store.close(closed)
    live = store.open()
    store.append(live, [{"t_ms": 0, "kind": "on", "note": 64, "vel": 70}])

    assert main(["performance", "list", "--root", str(tmp_path)]) == 0
    listing = capsys.readouterr().out
    assert closed in listing and live in listing and "closed" in listing and "open" in listing

    assert main(["performance", "summary", closed, "--root", str(tmp_path)]) == 0
    printed = capsys.readouterr().out
    assert printed == (tmp_path / closed / "summary.md").read_text(encoding="utf-8")

    assert main(["performance", "summary", live, "--root", str(tmp_path)]) == 0
    assert "provisional" in capsys.readouterr().out
    assert not (tmp_path / live / "summary.md").exists()

    assert main(["performance", "summary", "20260101-000000-00000000", "--root", str(tmp_path)]) == 2

    assert main(["performance", "summary", "latest", "--root", str(tmp_path)]) == 0
    assert "provisional" in capsys.readouterr().out  # the newest session is the open one
    assert main(["performance", "summary", "latest", "--root", str(tmp_path / "empty")]) == 2
    assert "no practice sessions" in capsys.readouterr().err


def test_cli_prune_lists_first_and_deletes_only_with_yes(tmp_path, capsys):
    store = perf.PerformanceStore(tmp_path)
    old, recent = store.open({"page": "old"}), store.open({"page": "recent"})
    info = json.loads((tmp_path / old / "session.json").read_text(encoding="utf-8"))
    info["opened_ns"] -= 40 * 86400 * 10 ** 9  # opened 40 days ago
    (tmp_path / old / "session.json").write_text(json.dumps(info), encoding="utf-8")
    assert [r["session"] for r in store.older_than(30)] == [old] and store.older_than(50) == []

    assert main(["performance", "prune", "--older-than-days", "30", "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert old in out and recent not in out and "--yes" in out
    assert (tmp_path / old).is_dir()

    assert main(["performance", "prune", "--older-than-days", "30", "--yes", "--root", str(tmp_path)]) == 0
    assert "deleted 1" in capsys.readouterr().out
    assert not (tmp_path / old).exists() and (tmp_path / recent).is_dir()
    assert main(["performance", "prune", "--older-than-days", "30", "--root", str(tmp_path)]) == 0
    assert "nothing" in capsys.readouterr().out
    assert main(["performance", "prune", "--older-than-days", "-1", "--root", str(tmp_path)]) == 2


def test_cli_serve_flags_reach_serve(monkeypatch, tmp_path):
    import arsenal.serve as serve_module
    calls = []
    monkeypatch.setattr(serve_module, "serve", lambda **kwargs: calls.append(kwargs))
    assert main(["serve", "--port", "8899"]) == 0
    assert main(["serve", "--port", "8899", "--performance-root", str(tmp_path), "--no-performance-log"]) == 0
    assert calls == [{"port": 8899, "roots": None, "performance_root": None, "performance_log": True},
                     {"port": 8899, "roots": None, "performance_root": str(tmp_path), "performance_log": False}]
