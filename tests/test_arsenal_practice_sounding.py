"""Practice verbs (arsenal/practice.py): a window's chord is every pitch that sounds across it, held by a finger or by
the pedal, on synthetic sessions built here.

Nothing here reads Daniel's practice data: every session is generated in this file and dated 2030. The fixtures under
tests/fixtures/practice_sounding/<name>/performance/<session>/ are written by build_fixture(), and a test checks that
the files on disk still match it. To regenerate them:

    py tests/test_arsenal_practice_sounding.py --write-fixtures

Each fixture pins one defect, red before the fix and green after it:
- rolled_dmaj7: a D-F#-A-C# unfolding under one held pedal is one Dmaj7 (not Dmaj7 without its 3rd, the F# heard
  late), borrowed in D minor (a Picardy third: the key stays D minor).
- late_arrivals: a Dm figure with a G joining 3 s in and an E 5 s in, and a D-A-C# figure with an F# joining 5 s into
  7 s: split where the new notes arrive, not named from the notes that came last or first.
- landings: 5 -> 1 and 4 -> 1 through a note-only window, 5 -> 1 onto a power chord through the bass octaves, and an
  unnamed set over the 5 in the bass (with the leading tone) landing on 1.
- late_pedal: chords struck, the pedal changed just after the strike over the last chord's figure, their notes arriving
  one by one: one chord each, not a broken chord holding the notes the pedal lift cleared.
- already_correct: windows the engine named correctly before the fix (block chords, a quick roll, a chord built note
  by note, a suspension, a pedalled arpeggio over a walking bass, a broken chord without pedal, an open 5th, a treble
  run, a melody over a held bass, a dominant onto a two-note shape, a figure with nothing joining it): expected.json
  pins them as the engine named them at git 7c2266a2, and they must not change. Rewrite it only after reading the
  diff: py tests/test_arsenal_practice_sounding.py --pin-already-correct
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import practice as pr  # noqa: E402
from arsenal.performance import PerformanceStore  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "practice_sounding"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is needed to run piano.js Theory.detect")

SESSIONS = {"rolled_dmaj7": "20300102-010000-5d0a0001", "late_arrivals": "20300102-011000-5d0a0002",
            "landings": "20300102-012000-5d0a0003", "late_pedal": "20300102-013000-5d0a0004",
            "already_correct": "20300102-014000-5d0a0005"}
OPENED_EPOCH = {name: 1893546000000.0 + k * 600000 for k, name in enumerate(SESSIONS)}  # from 2030-01-02T01:00Z

PRIORITY = {"off": 0, "up": 1, "down": 2, "on": 3}
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}

DM, GM, BB = ["D2", "F3", "A3", "D4"], ["G2", "Bb3", "D4", "G4"], ["Bb2", "D4", "F4", "Bb4"]
A7, A_MAJOR = ["A2", "C#4", "E4", "G4"], ["A2", "C#4", "E4", "A4"]
EB, AB, BB7 = ["Eb2", "G3", "Bb3", "Eb4"], ["Ab2", "C4", "Eb4", "Ab4"], ["Bb2", "D4", "F4", "Ab4"]
CM = ["C3", "Eb4", "G4", "C5"]


# ================================================================================================ building
def n(name: str) -> int:
    """'Eb3' -> 51 (C4 = 60)."""
    letters = name.rstrip("-0123456789")
    return (int(name[len(letters):]) + 1) * 12 + PC[letters]


def perform(actions):
    """[(t_ms, 'on'|'off'|'down'|'up', note, vel)] -> page-style events with sound_end, like log.js writes them."""
    events, held, ringing, pedal = [], set(), set(), False
    for t, kind, note, vel in sorted(actions, key=lambda a: (a[0], PRIORITY[a[1]], a[2])):
        if kind == "on":
            if note in ringing:
                events.append({"t_ms": t, "kind": "sound_end", "note": note, "by": "repeat"})
            events.append({"t_ms": t, "kind": "on", "note": note, "vel": vel})
            held.add(note)
            ringing.add(note)
        elif kind == "off" and note in held:
            held.discard(note)
            events.append({"t_ms": t, "kind": "off", "note": note})
            if not pedal:
                ringing.discard(note)
                events.append({"t_ms": t, "kind": "sound_end", "note": note, "by": "release"})
        elif kind == "down" and not pedal:
            pedal = True
            events.append({"t_ms": t, "kind": "pedal", "down": True, "value": 100})
        elif kind == "up" and pedal:
            pedal = False
            events.append({"t_ms": t, "kind": "pedal", "down": False, "value": 0})
            for m in sorted(ringing - held):
                ringing.discard(m)
                events.append({"t_ms": t, "kind": "sound_end", "note": m, "by": "pedal"})
    return events


def block(acts, t, notes, dur, vel=64):
    for m in notes:
        acts.append((t, "on", n(m), vel))
        acts.append((t + dur, "off", n(m), 0))


def pedalled(acts, t, chords, seconds=2.0):
    """Block chords, each held `seconds`, the pedal changed at every chord (lift at the attack, press 100 ms later).
    Returns the time after the last chord (the pedal is lifted there)."""
    step = int(seconds * 1000)
    for notes in chords:
        acts.append((t, "up", 0, 0))
        block(acts, t, notes, step - 100)
        acts.append((t + 100, "down", 0, 0))
        t += step
    acts.append((t, "up", 0, 0))
    return t


def figure(acts, t0, t1, notes, step=250, dur=150, vel=60):
    """Notes struck one at a time, cycling, every `step` ms from t0 until t1."""
    k, t = 0, t0
    while t < t1:
        block(acts, t, [notes[k % len(notes)]], dur, vel)
        k, t = k + 1, t + step


def d_minor_context(acts, t=0):
    return pedalled(acts, t, [DM, GM, BB, A7] * 2)


def rolled_dmaj7():
    """D minor; then Gm, A7 and a Dmaj7 unfolding under one pedal: D1 D2 held, D struck in octaves for 1.9 s, then C#
    and A, then F# 2.75 s in, down to C#4, the pedal lifted at 5.3 s."""
    acts = []
    t = pedalled(acts, d_minor_context(acts), [GM, A7])
    acts.append((t + 60, "down", 0, 0))
    block(acts, t, ["D1", "D2"], 4800, vel=78)
    for k, m in enumerate(["D4", "D5", "D5", "D5", "D6", "D6"]):
        block(acts, t + k * 300, [m], 120)
    for k, m in enumerate(["C#6", "A5", "D6", "C#6", "A5"]):
        block(acts, t + 1900 + k * 160, [m], 120)
    for k, m in enumerate(["F#5", "D5", "C#5", "A4", "F#4", "D4", "C#4"]):
        block(acts, t + 2750 + k * 300, [m], 120)
    acts.append((t + 5300, "up", 0, 0))
    return acts, {"roll_ms": t}


def late_arrivals():
    """D minor; then (a) a Dm figure under one pedal, G4 joining 3 s in and E4 5 s in, lifted at 7 s; Gm and A7; then
    (b) D2 held under a D-A-C# figure, F#4 joining 5 s in, lifted at 7 s."""
    acts = []
    a = pedalled(acts, d_minor_context(acts), [A7])
    acts.append((a + 60, "down", 0, 0))
    figure(acts, a, a + 7000, ["D2", "A2", "F3", "D3", "A3", "F4"])
    block(acts, a + 3000, ["G4"], 3900)
    block(acts, a + 5000, ["E4"], 1900)
    acts.append((a + 7000, "up", 0, 0))
    b = pedalled(acts, a + 7000, [GM, A7])
    acts.append((b + 60, "down", 0, 0))
    block(acts, b, ["D2"], 6900)
    figure(acts, b, b + 7000, ["A3", "C#4", "D4", "A4", "C#5"], step=300)
    block(acts, b + 5000, ["F#4"], 1900)
    acts.append((b + 7000, "up", 0, 0))
    return acts, {"a_ms": a, "b_ms": b}


def _then(acts, t, notes, dur):
    """One chord held dur ms, the pedal changed at its attack; returns its end."""
    acts.append((t, "up", 0, 0))
    block(acts, t, notes, dur - 100)
    acts.append((t + 100, "down", 0, 0))
    return t + dur


def landings():
    """D minor, then four landings on 1, each after a Bb chord: A7, C#4 alone, Dm (5 -> 1 through a note); Gm, Bb4
    alone, Dm (4m -> 1 through a note); A, D2-D3 in octaves, D5 (5 -> 1 onto a power chord through the bass octaves);
    A1 A2 Bb3 C#4 D4 (no chord name), Dm (the 5 by its bass and leading tone)."""
    acts = []
    t = d_minor_context(acts)
    times = {}
    for name, before, between, arrival in (("note_5_1", A7, ["C#4"], DM), ("note_4_1", GM, ["Bb4"], DM),
                                           ("octaves_5_power", A_MAJOR, ["D2", "D3"], ["D2", "A3", "D4"]),
                                           ("unnamed_5_1", None, None, DM)):
        t = _then(acts, t, BB, 2000)
        times[name] = t
        if before is not None:
            t = _then(acts, t, before, 2000)
            t = _then(acts, t, between, 600)
        else:
            t = _then(acts, t, ["A1", "A2", "Bb3", "C#4", "D4"], 2200)
        t = _then(acts, t, arrival, 2400)
    acts.append((t, "up", 0, 0))
    return acts, times


def late_pedal():
    """D minor; then Bbmaj7, Gm7, A7, Dm7, each struck as its bass octave and 3rd, the pedal lifted 50 ms after the
    strike and pressed again 120 ms later (clearing the last chord's figure, still ringing: its last notes struck under
    700 ms before), its 5th and 7th arriving 500 ms in, then its notes cycling."""
    acts = []
    t = d_minor_context(acts)
    starts = []
    chords = [(["Bb1", "Bb2", "D4", "D5"], ["F4", "A4"], ["Bb3", "D4", "F4", "A4"]),
              (["G1", "G2", "Bb3", "Bb4"], ["D5", "F5"], ["G4", "Bb4", "D5", "F5"]),
              (["A1", "A2", "C#4", "C#5"], ["E4", "G4"], ["A3", "C#4", "E4", "G4"]),
              (["D1", "D2", "F4", "F5"], ["A4", "C5"], ["D4", "F4", "A4", "C5"])]
    acts.append((t, "down", 0, 0))
    for strike, arrive, cycle in chords:
        starts.append(t)
        block(acts, t, strike, 400, vel=90)
        acts += [(t + 50, "up", 0, 0), (t + 170, "down", 0, 0)]
        block(acts, t + 500, arrive, 300, vel=70)
        figure(acts, t + 800, t + 2400, cycle, step=200, dur=120)
        t += 2500
    acts.append((t, "up", 0, 0))
    return acts, {"starts": starts}


def already_correct():
    """Eb major, already named right before the fix: block chords with 5 -> 1, 4 -> 1 and 5 -> 6m; a quick roll of
    Abmaj7 under one pedal; an F chord built note by note (F C, A, F, then Eb, G, Bb: one F11); Absus2 held, then its
    3rd; a pedalled Ebmaj9 arpeggio over a bass walking D3 Bb2 G2 Eb2; Eb G Bb one at a time without pedal; an open
    5th (Eb2 Bb3 D4); a pedalled treble run; a melody descending over a held Bb bass under one pedal; Bb7 onto Eb-G; an
    Ab figure under one pedal with nothing joining it."""
    acts = []
    t = pedalled(acts, 0, [EB, AB, EB, BB7, EB, ["Eb2", "Ab3", "C4", "Eb4"], EB, BB7, CM, AB, BB7, EB])
    acts.append((t + 60, "down", 0, 0))  # quick roll
    for k, m in enumerate(["Ab2", "Eb3", "C4", "G4", "C5"]):
        block(acts, t + k * 120, [m], 2600 - k * 120)
    acts.append((t + 3000, "up", 0, 0))
    t = pedalled(acts, t + 3000, [BB7, EB])
    for dt, m in [(0, "F2"), (0, "C3"), (400, "A4"), (800, "F3"), (2600, "Eb5"), (3300, "G5"), (3800, "Bb5")]:
        block(acts, t + dt, [m], 5800 - dt)  # built note by note
    acts += [(t + 150, "down", 0, 0), (t + 5900, "up", 0, 0)]
    t = pedalled(acts, t + 6000, [BB7, EB, ["Ab2", "Bb3", "Eb4", "Ab4"], AB, BB7, EB])  # Absus2, then its 3rd
    acts.append((t + 50, "down", 0, 0))  # pedalled arpeggio over a walking bass
    for k, bass in enumerate(["D3", "Bb2", "G2", "Eb2"]):
        block(acts, t + k * 1000, [bass], 300, vel=70)
    arp = ["Eb4", "G4", "Bb4", "D5", "F5", "Bb5", "G5", "D5"]
    for k in range(26):
        block(acts, t + 40 + k * 150, [arp[k % len(arp)]], 120, vel=50)
    acts.append((t + 4000, "up", 0, 0))
    t = pedalled(acts, t + 4000, [AB, BB7])
    for k, m in enumerate(["Eb3", "G3", "Bb3", "Eb4", "Bb3", "G3"]):  # without pedal
        block(acts, t + k * 300, [m], 150)
    t = pedalled(acts, t + 2000, [AB, ["Eb2", "Bb3", "D4"], AB, BB7, EB])  # an open 5th
    acts.append((t + 50, "down", 0, 0))  # a treble run
    for k, m in enumerate(["Eb5", "F5", "G5", "Ab5", "Bb5", "C6", "D6", "Eb6"]):
        block(acts, t + k * 180, [m], 140, vel=58)
    acts.append((t + 2000, "up", 0, 0))
    t = pedalled(acts, t + 2000, [AB, EB])
    acts.append((t + 60, "down", 0, 0))  # a melody over a held bass
    block(acts, t, ["Bb1"], 3400, vel=60)
    for dt, m in [(0, "D5"), (700, "Eb5"), (1300, "D5"), (1900, "C5"), (2500, "Ab4")]:
        block(acts, t + dt, [m], 250, vel=48)
    acts.append((t + 3500, "up", 0, 0))
    t = pedalled(acts, t + 3500, [EB, BB7, ["Eb3", "G3"], AB])  # a two-note shape never arrives
    acts.append((t + 60, "down", 0, 0))  # an Ab figure for 3.5 s, nothing new joining
    figure(acts, t, t + 3500, ["Ab2", "Eb3", "C4", "Eb4", "Ab4", "C4"])
    acts.append((t + 3500, "up", 0, 0))
    pedalled(acts, t + 3500, [BB7, EB])
    return acts, {}


BUILDERS = {"rolled_dmaj7": rolled_dmaj7, "late_arrivals": late_arrivals, "landings": landings,
            "late_pedal": late_pedal, "already_correct": already_correct}


def _iso(epoch_ms: float) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000, timezone.utc).isoformat(timespec="milliseconds")


def build_fixture(name: str, folder: Path) -> Path:
    """Write one fixture's session (session.json, events.jsonl) under folder/performance/<session>."""
    acts, _ = BUILDERS[name]()
    events = perform(acts)
    sid, opened = SESSIONS[name], OPENED_EPOCH[name]
    last = max(e["t_ms"] for e in events)
    info = {"api": "arsenal.performance/v0", "session": sid, "opened_at": _iso(opened + 41),
            "opened_ns": int(round(opened + 41)) * 1000000, "client_id": "lg-5d0a",
            "meta": {"page_id": "p-5d0a", "opened_at_client": _iso(opened), "buffered": False}, "closed": True,
            "event_count": len(events), "last_t_ms": last, "duration_s": round(last / 1000, 3)}
    d = folder / "performance" / sid
    d.mkdir(parents=True, exist_ok=True)
    (d / "session.json").write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (d / "events.jsonl").write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in events), encoding="utf-8",
                                    newline="\n")
    return folder


def window_view(doc: dict) -> list:
    """What 'a window did not change' means: its span, name, label, notes, class and key."""
    return [{"at": w["at"], "start_ms": w["start_ms"], "end_ms": w["end_ms"], "name": w["name"], "label": w["label"],
             "pcs": w["pcs"], "class": w["class"], "key": w["key"]} for w in doc["windows"]]


# ================================================================================================= helpers
_DOCS: dict = {}


def fixture_sess(name: str) -> dict:
    if name not in _DOCS:
        _DOCS[name] = pr.load_session(PerformanceStore(FIX / name / "performance"), SESSIONS[name])
    return _DOCS[name]


def fixture_doc(name: str) -> dict:
    return fixture_sess(name)["doc"]


def windows_from(doc: dict, t_ms: float) -> list:
    return [w for w in doc["windows"] if w["end_ms"] > t_ms]


def brief_text(name: str) -> str:
    sess = fixture_sess(name)
    return pr.render_brief(sess, pr.brief_data(sess))


# =================================================================================================== tests
@pytest.mark.parametrize("name", sorted(SESSIONS))
def test_fixture_files_match_their_builder(tmp_path, name):
    built = build_fixture(name, tmp_path / name) / "performance"
    on_disk = FIX / name / "performance"
    files = sorted(p.relative_to(built).as_posix() for p in built.rglob("*") if p.is_file())
    assert files == sorted(p.relative_to(on_disk).as_posix() for p in on_disk.rglob("*") if p.is_file())
    for rel in files:
        assert (built / rel).read_bytes() == (on_disk / rel).read_bytes(), f"{name}/{rel} is stale: --write-fixtures"


@pytest.mark.parametrize("name", sorted(SESSIONS))
def test_fixture_sessions_are_synthetic_and_dated_2030(name):
    d = FIX / name / "performance"
    assert [p.name for p in d.iterdir()] == [SESSIONS[name]]
    info = json.loads((d / SESSIONS[name] / "session.json").read_text(encoding="utf-8"))
    assert info["session"].startswith("2030") and info["opened_at"].startswith("2030-")


@needs_node
def test_a_dmaj7_unfolding_under_one_pedal_is_dmaj7_with_its_3rd():
    doc = fixture_doc("rolled_dmaj7")
    roll = rolled_dmaj7()[1]["roll_ms"]
    late = windows_from(doc, roll)
    assert len(late) == 1, [(w["at"], w["name"]) for w in late]
    w = late[0]
    assert (w["start_ms"], w["end_ms"]) == (roll, roll + 5300), w
    assert (w["name"], w["label"], w["marks"]) == ("Dmaj7", "Dmaj7", []), (w["name"], w["label"], w["marks"])
    assert sorted(w["pcs"]) == ["A", "C#", "D", "F#"]
    assert (w["key"], w["class"]) == ("D minor", "borrowed"), (w["key"], w["class"])
    # a minor piece closing on its major tonic is a Picardy third: the key stays D minor, no return to D major
    assert [a["key"] for a in doc["keys"]["areas"]] == ["D minor"], doc["keys"]["areas"]
    assert "Dmaj7(no3)" not in brief_text("rolled_dmaj7")


@needs_node
def test_notes_arriving_late_in_a_figure_split_the_window_where_they_arrive():
    doc = fixture_doc("late_arrivals")
    times = late_arrivals()[1]
    a, b = times["a_ms"], times["b_ms"]
    part_a = [(w["start_ms"] - a, w["end_ms"] - a, w["label"]) for w in doc["windows"] if a <= w["start_ms"] < a + 7000]
    assert part_a == [(0, 3000, "Dm"), (3000, 5000, "Dm(add11)"), (5000, 7000, "Dm(add9,11)")], part_a
    part_b = [(w["start_ms"] - b, w["end_ms"] - b, w["label"]) for w in doc["windows"] if b <= w["start_ms"] < b + 7000]
    assert [(s, lab) for s, _, lab in part_b] == [(0, "Dmaj7(no3)"), (5000, "Dmaj7")], part_b
    assert not [w for w in doc["windows"] if w["start_ms"] <= a and w["end_ms"] >= a + 7000]


@needs_node
def test_landings_on_1_pass_over_notes_octaves_and_find_an_unnamed_5():
    doc = fixture_doc("landings")
    times = landings()[1]
    found = {c["start_ms"]: (c["kind"], c["chords"][-1]) for c in doc["findings"]["cadences"]}
    want = {"note_5_1": ("5 -> 1 (authentic)", "Dm"), "note_4_1": ("4m -> 1 (minor plagal)", "Dm"),
            "octaves_5_power": ("5 -> 1 (authentic)", "D5"), "unnamed_5_1": ("5 -> 1 (authentic)", "Dm")}
    for name, (kind, arrival) in want.items():
        assert found.get(times[name]) == (kind, arrival), (name, times[name], found)
    unnamed = next(c for c in doc["findings"]["cadences"] if c["start_ms"] == times["unnamed_5_1"])
    assert unnamed["numbers"][0] == "5" and unnamed["bass"][0] == "A1", unnamed
    line = next(x for x in brief_text("landings").splitlines() if x.startswith("Cadences: "))
    assert line.startswith("Cadences: 5 -> 1 x4"), line  # the three here and the context's A7 -> Dm
    assert "none of them from the 5 chord" not in line


@needs_node
def test_a_pedal_change_just_after_the_strike_does_not_make_a_broken_chord_of_the_last_chord():
    doc = fixture_doc("late_pedal")
    starts = late_pedal()[1]["starts"]
    late = windows_from(doc, starts[0])
    assert not [w for w in late if w["kind"] == "broken chord"], [(w["at"], w["name"]) for w in late]
    got = [(w["start_ms"], w["label"]) for w in late]
    assert got == list(zip(starts, ["Bbmaj7", "Gm7", "A7", "Dm7"])), got


@needs_node
def test_windows_that_were_already_correct_do_not_change():
    expected = json.loads((FIX / "already_correct" / "expected.json").read_text(encoding="utf-8"))
    doc = fixture_doc("already_correct")
    assert window_view(doc) == expected["windows"]
    assert [(c["at"], c["kind"], c["chords"]) for c in doc["findings"]["cadences"]] == \
        [tuple(c) for c in expected["cadences"]]
    assert [a["key"] for a in doc["keys"]["areas"]] == expected["areas"]


def test_split_returns_keeps_a_picardy_ending_in_its_key():
    area = {"state": pr.KEYS.index((2, "minor")), "start_ms": 0, "end_ms": 34000, "section": 0}

    def w(a, b, pcs):
        return {"start_ms": a, "end_ms": b, "pcs": pcs}
    dm, d, gm, a7 = [2, 5, 9], [2, 6, 9], [7, 10, 2], [9, 1, 4, 7]
    ending = [w(0, 20000, dm), w(20000, 22000, d), w(22000, 25000, gm), w(25000, 28000, a7), w(28000, 34000, d)]
    assert len(pr.split_returns([area], ending)) == 1  # 2 s of D before the last chord: a Picardy third, not a return
    longer = [w(0, 20000, dm), w(20000, 25000, d), w(25000, 28000, a7), w(28000, 34000, d)]
    got = [(pr.KEYS[a["state"]], a["start_ms"], a["end_ms"], bool(a.get("return")))
           for a in pr.split_returns([area], longer)]
    assert got == [((2, "minor"), 0, 20000, False), ((2, "major"), 20000, 34000, True)], got


def _pin_already_correct() -> None:
    doc = pr.load_session(PerformanceStore(FIX / "already_correct" / "performance"), SESSIONS["already_correct"])["doc"]
    note = "Windows the engine named correctly before the sounding fix (git 7c2266a2); they must not change."
    pinned = {"note": note, "windows": window_view(doc),
              "cadences": [[c["at"], c["kind"], c["chords"]] for c in doc["findings"]["cadences"]],
              "areas": [a["key"] for a in doc["keys"]["areas"]]}
    (FIX / "already_correct" / "expected.json").write_text(json.dumps(pinned, indent=2) + "\n", encoding="utf-8",
                                                          newline="\n")


if __name__ == "__main__":
    if "--write-fixtures" in sys.argv:
        for fixture in SESSIONS:
            target = FIX / fixture / "performance"
            if target.exists():
                shutil.rmtree(target)
            build_fixture(fixture, FIX / fixture)
            print(f"wrote {target}")
    if "--pin-already-correct" in sys.argv:
        _pin_already_correct()
        print(f"pinned {FIX / 'already_correct' / 'expected.json'}")
