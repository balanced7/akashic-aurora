"""Practice verbs (arsenal/practice.py): the offline harmony engine, on synthetic sessions built here.

Every session below is generated in the test (no real practice data). The events follow the piano page's log: on/off,
pedal, and a sound_end for every note (release, pedal lift, re-strike). Tests that name chords run the page's own
Theory.detect through node and are skipped when node is missing.
"""
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import practice as pr  # noqa: E402

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is needed to run piano.js Theory.detect")

PRIORITY = {"off": 0, "up": 1, "down": 2, "on": 3}
PC = {"C": 0, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10,
      "B": 11, "Cb": 11, "C#": 1}


def n(name: str) -> int:
    """'Eb3' -> 51 (C4 = 60)."""
    letters = name.rstrip("-0123456789")
    return (int(name[len(letters):]) + 1) * 12 + PC[letters]


def perform(actions):
    """[(t_ms, 'on'|'off'|'down'|'up', note, vel)] -> page-style events with sound_end, like log.js writes them."""
    events, held, ringing, pedal = [], set(), set(), False
    for t, kind, note, vel in sorted(actions, key=lambda a: (a[0], PRIORITY[a[1]])):
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
        acts.append((t, "on", n(m) if isinstance(m, str) else m, vel))
        acts.append((t + dur, "off", n(m) if isinstance(m, str) else m, 0))


def pedalled_progression(chords, seconds=2.0, repeats=1, start=0):
    """Block chords, each held `seconds`, the pedal changed at every chord (lift at the attack, press 100 ms later)."""
    acts, t = [], start
    step = int(seconds * 1000)
    for _ in range(repeats):
        for notes in chords:
            acts.append((t, "up", 0, 0))
            block(acts, t, notes, step - 100)
            acts.append((t + 100, "down", 0, 0))
            t += step
    acts.append((t, "up", 0, 0))
    return acts, t


EB = ["Eb2", "G3", "Bb3", "Eb4"]
AB = ["Ab2", "C4", "Eb4", "Ab4"]
BB7 = ["Bb2", "D4", "F4", "Ab4"]
CM7 = ["C3", "Eb4", "G4", "Bb4"]


# ================================================================================ sounding reconstruction
def test_pedal_held_notes_sound_until_their_sound_end():
    acts = [(0, "down", 0, 0)]
    block(acts, 0, ["C4"], 200)
    block(acts, 1000, ["E4"], 200)
    acts.append((3000, "up", 0, 0))
    block(acts, 3500, ["G4"], 400)
    snd = pr.sounding(perform(acts))
    ends = {(x["note"], x["on_ms"]): (x["end_ms"], x["by"]) for x in snd["notes"]}
    assert ends[(60, 0)] == (3000, "pedal")
    assert ends[(64, 1000)] == (3000, "pedal")
    assert ends[(67, 3500)] == (3900, "release")
    assert snd["pedal"] == [{"down_ms": 0, "up_ms": 3000, "value": 100}]
    assert snd["explicit_ends"] is True


def test_sounding_without_sound_end_events_is_inferred_the_same_way():
    acts = [(0, "down", 0, 0)]
    block(acts, 0, ["C4", "E4"], 200)
    block(acts, 500, ["C4"], 100)  # a re-strike under the pedal
    acts.append((2000, "up", 0, 0))
    block(acts, 2500, ["G4"], 300)
    events = perform(acts)
    with_ends = pr.sounding(events)
    without = pr.sounding([e for e in events if e["kind"] != "sound_end"])
    assert without["explicit_ends"] is False
    strip = lambda s: [(x["note"], x["on_ms"], x["end_ms"], x["by"]) for x in s["notes"]]  # noqa: E731
    assert strip(with_ends) == strip(without)
    assert (60, 0, 500, "repeat") in strip(without)


# ================================================================================== windows and naming
@needs_node
def test_arpeggiated_pedalled_dmaj9_with_moving_bass_is_one_window():
    """A Dmaj9 rolled over a bass walking C#3 A2 F#2 D2 under one pedal, twice: one harmony, not a four-chord loop."""
    acts, t = [], 0
    for _ in range(2):
        acts.append((t, "up", 0, 0))
        acts.append((t + 50, "down", 0, 0))
        for k, bass in enumerate(["C#3", "A2", "F#2", "D2"]):
            block(acts, t + k * 1000, [bass], 300, vel=70)
        arp = ["D4", "F#4", "A4", "C#5", "E5", "A5", "F#5", "C#5"]
        for k in range(26):
            block(acts, t + 40 + k * 150, [arp[k % len(arp)]], 120, vel=50)
        t += 4000
    acts.append((t, "up", 0, 0))
    doc = pr.analyze(perform(acts))
    assert len(doc["windows"]) == 1, [(w["at"], w["name"]) for w in doc["windows"]]
    w = doc["windows"][0]
    assert w["name"] == "Dmaj9"
    assert w["bass"]["motion"] == "moving"
    figure = [f[0] for f in w["bass"]["figure"]]
    assert figure[:4] == ["C#3", "A2", "F#2", "D2"]
    assert sorted(w["pcs"]) == sorted(["D", "F#", "A", "C#", "E"])
    assert doc["segmentation"]["transients_dropped"] == 0


@needs_node
def test_passing_tone_stays_inside_and_isolated_blip_is_a_transient():
    acts = []
    block(acts, 0, ["C3", "E4", "G4", "C5"], 3900)  # held by the fingers, no pedal
    block(acts, 1500, ["D5"], 150)  # a quick passing D over it (under the pedal it would ring on: part of the harmony)
    block(acts, 9000, ["A4"], 100)  # an isolated 100 ms blip long after
    doc = pr.analyze(perform(acts))
    assert [w["name"] for w in doc["windows"]] == ["C"]
    assert [p[0] for p in doc["windows"][0]["passing"]] == ["D"]
    assert doc["segmentation"]["transients_dropped"] == 1


# ============================================================================================ key areas
@needs_node
def test_bb_major_modulating_to_eb_major_is_found_within_a_few_seconds():
    bb = [["Bb2", "D4", "F4", "A4"], ["G2", "Bb3", "D4", "F4"], ["C3", "Eb4", "G4", "Bb4"], ["F2", "A3", "C4", "Eb4"]]
    eb = [["Eb2", "G3", "Bb3", "D4"], CM7, ["F2", "Ab3", "C4", "Eb4"], BB7]
    acts, t = pedalled_progression(bb, seconds=2.0, repeats=8)                # 0:00 - 1:04
    more, end = pedalled_progression(eb, seconds=2.0, repeats=10, start=t)   # 1:04 - 2:24
    doc = pr.analyze(perform(acts + more))
    keys = [(a["key"], a["start_ms"]) for a in doc["keys"]["areas"]]
    assert [k for k, _ in keys] == ["Bb major", "Eb major"], keys
    assert abs(keys[1][1] - t) <= 3000, (keys, t)
    assert doc["home_key"] == "Eb major"
    assert doc["keys"]["areas"][0]["relation"] == "5 of Eb major"
    assert doc["findings"]["modulations"][0]["from"] == "Bb major"
    # the A-natural Bbmaj7 is diatonic in its own key area, and numbered there
    first = doc["windows"][0]
    assert (first["name"], first["number"], first["class"]) == ("Bbmaj7", "1maj7", "diatonic")
    assert first["in_home_key"]["class"] != "diatonic"


# ======================================================================================= classification
@needs_node
def test_abmaj9_sharp11_in_eb_major_reads_as_the_lydian_4():
    lyd = ["Ab2", "C3", "G3", "Bb3", "D4", "Eb4"]
    acts, _ = pedalled_progression([EB, lyd, BB7, CM7], seconds=3.0, repeats=4)
    doc = pr.analyze(perform(acts))
    assert doc["home_key"] == "Eb major"
    lyd_windows = [w for w in doc["windows"] if w["root"] == "Ab"]
    assert lyd_windows, [(w["at"], w["name"]) for w in doc["windows"]]
    for w in lyd_windows:
        assert w["analysed_as"] == "Abmaj9#11"
        assert w["analysed_from"] == "reading"
        assert w["reading"]["text"] == "Abmaj9#11 (reading)"
        assert w["number"] == "4maj9#11"
        assert w["class"] == "diatonic"
    assert len(doc["findings"]["lydian_4"]) == len(lyd_windows)
    assert all(m["number"] == "4maj9#11" for m in doc["findings"]["lydian_4"])


@pytest.fixture(scope="module")
def eb_progression_doc():
    """Eb major: Eb | Absus2 | Abadd9 | Bb7sus4 | Eb | Abm | Eb | Bbsus4 | Bb7 | Eb, three times, pedal over an Eb
    bass held through the first two bars as well."""
    chords = [EB, ["Ab2", "Bb3", "Eb4", "Ab4"], ["Ab2", "Bb3", "C4", "Eb4"], ["Bb2", "Eb4", "F4", "Ab4"], EB,
              ["Ab2", "Eb3", "Ab3", "Cb4"], EB, ["Bb2", "Eb4", "F4", "Bb4"], BB7, EB]
    acts, _ = pedalled_progression(chords, seconds=2.0, repeats=3)
    return pr.analyze(perform(acts)) if NODE else None


@needs_node
def test_abm_in_eb_major_is_spelled_abm_and_borrowed_from_eb_minor(eb_progression_doc):
    doc = eb_progression_doc
    assert [a["key"] for a in doc["keys"]["areas"]] == ["Eb major"]
    abm = [w for w in doc["windows"] if w["suffix"] == "m" and w["root"] == "Ab"]
    assert len(abm) == 3, [(w["at"], w["name"]) for w in doc["windows"]]
    for w in abm:
        assert w["name"] == "Abm"
        assert w["detect"]["name"] == "G#m"  # the page's detect alone spells it with sharps
        assert w["number"] == "4m"
        assert (w["class"], w["class_detail"]) == ("borrowed", "borrowed from Eb minor")
    outside = doc["findings"]["outside_key"]
    assert any(o["chord"] == "Abm" and o["class"] == "borrowed" for o in outside)


@needs_node
def test_suspensions_cadences_and_dominants(eb_progression_doc):
    f = eb_progression_doc["findings"]
    sus = {(s["from"], s["to"]) for s in f["suspensions"]}
    assert ("Absus2", "Abadd9") in sus
    assert ("Bbsus4", "Bb7") in sus
    kinds = {(c["kind"], tuple(c["chords"])) for c in f["cadences"]}
    assert ("5sus -> 1 (suspended dominant)", ("Bb7sus4", "Eb")) in kinds
    assert ("4m -> 1 (minor plagal)", ("Abm", "Eb")) in kinds
    assert ("5 -> 1 (authentic)", ("Bb7", "Eb")) in kinds
    summary = f["dominants"]["summary"]
    assert summary["suspended"]["windows"] == 6  # Bb7sus4 and Bbsus4, three times
    assert summary["with its major 3rd"]["windows"] == 3


@needs_node
def test_pedal_point_under_changing_chords():
    """Eb2 held by the finger under Eb | Ab/Eb | Fm/Eb | Eb. (Bb D F over Eb would read as Ebmaj9 without its 3rd: a
    reading rooted on the held bass, so it is not used here as a chord rooted off the bass.)"""
    acts = [(0, "down", 0, 0)]
    block(acts, 0, ["Eb2"], 11900, vel=60)  # the bass key held down throughout
    for k, upper in enumerate([["G3", "Bb3", "Eb4"], ["Ab3", "C4", "Eb4"], ["F3", "Ab3", "C4"], ["G3", "Bb3", "Eb4"]]):
        acts.append((k * 3000, "up", 0, 0))
        block(acts, k * 3000, upper, 2900)
        acts.append((k * 3000 + 100, "down", 0, 0))
    acts.append((12000, "up", 0, 0))
    doc = pr.analyze(perform(acts))
    points = doc["findings"]["pedal_points"]
    assert len(points) == 1, points
    assert points[0]["bass"] == "Eb2"
    assert points[0]["over"][:2] == ["Eb", "Ab/Eb"] and points[0]["over"][2].startswith("Fm")
    assert points[0]["seconds"] >= 11


@needs_node
def test_voicing_and_touch_stats():
    acts = [(0, "down", 0, 0)]
    for m, vel in (("C3", 40), ("G3", 60), ("E4", 80), ("C5", 100)):
        acts.append((0, "on", n(m), vel))
        acts.append((1900, "off", n(m), 0))
    acts.append((2000, "up", 0, 0))
    doc = pr.analyze(perform(acts))
    (w,) = doc["windows"]
    v = w["voicing"]
    assert (v["distinct_notes"], v["spread"], v["onsets"], v["vel_mean"], v["vel_max"]) == (4, 24, 4, 70.0, 100)
    assert (v["lowest"], v["highest"], v["max_polyphony"]) == ("C3", "C5", 4)
    assert v["pedal_share"] == 1.0
    assert doc["pedal"]["presses"] == 1


# ======================================================================================== pure helpers
def test_reading_suffixes():
    cases = {("maj7", (2, 6)): "maj9#11", ("m7", (9,)): "m7(13)", ("m7", (2, 5)): "m11", ("7", (1, 6)): "7b9#11",
             ("", (2, 6)): "add9(#11)", ("m", (5,)): "m(add11)", ("sus2", (6, 9)): "sus2(#11,13)",
             ("7", (9,)): "13", ("6", (2,)): "6/9", ("m(maj7)", (2, 5)): "m(maj9,11)"}
    for (base, ext), want in cases.items():
        assert pr._reading_suffix(base, set(ext)) == want, (base, ext)


@needs_node
def test_extended_readings_are_backed_by_every_note():
    answer, err = pr.run_theory([])
    assert err is None
    templates = answer["templates"]
    ab, bb, c, d, eb, f, g, a = 8, 10, 0, 2, 3, 5, 7, 9
    best = pr.extended_readings([ab, bb, c, d, eb, g], ab, templates)[0]
    assert (best["root_pc"], best["suffix"], best["no3"]) == (ab, "maj9#11", False)
    no3 = pr.extended_readings([eb, f, a, bb, d], eb, templates, roots=[eb])[0]
    assert (no3["suffix"], no3["no3"]) == ("maj9#11", True)
    assert pr.extended_readings([d, g, ab], ab, templates) == []  # too thin to name
    assert all(not r["no3"] for r in pr.extended_readings([c, g, d, f], c, templates) if r["base"].startswith("m"))


def test_classify_borrowed_modal_and_secondary_dominants():
    eb_major = {"key": "Eb major", "tonic": 3, "mode": "major"}
    eb_minor = {"key": "Eb minor", "tonic": 3, "mode": "minor"}
    dbmaj9 = [1, 5, 8, 0, 3]
    got = pr.classify(dbmaj9, 1, eb_major)
    assert got["class"] == "modal" and got["mode"] == "Mixolydian" and "borrowed from Eb minor" in got["detail"]
    assert pr.classify([0, 4, 7, 10], 0, eb_major)["detail"].startswith("5 of 2m")  # C7: its b7 makes it a dominant
    assert pr.classify([7, 11, 2], 7, eb_major, next_root_pc=0)["detail"] == "5 of 6m, and it lands there"
    assert pr.classify([7, 11, 2], 7, eb_major, next_root_pc=5)["class"] == "chromatic"  # G major going nowhere
    assert pr.classify([3, 7, 10], 3, eb_minor)["detail"] == "borrowed from Eb major"  # a major tonic, not V of 4m
    assert pr.classify([8, 11, 3], 8, eb_major)["detail"] == "borrowed from Eb minor"


def test_key_names_follow_the_home_key_spelling():
    flat = pr.key_namer(pr.KEYS.index((3, "major")))
    sharp = pr.key_namer(pr.KEYS.index((4, "major")))
    g_sharp_minor = pr.KEYS.index((8, "minor"))
    assert (flat(g_sharp_minor), sharp(g_sharp_minor)) == ("Ab minor", "G# minor")
    assert pr.parallel_key("Ab major") == "Ab minor"


# ================================================================================================= CLI
def _store_session(root: Path, events) -> str:
    sid = "20260101-120000-0badcafe"
    d = root / sid
    d.mkdir(parents=True)
    (d / "session.json").write_text(json.dumps({"session": sid, "opened_ns": 1, "closed": False,
                                                "event_count": len(events), "duration_s": 1.0}), encoding="utf-8")
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return sid


@needs_node
def test_cli_verbs_on_a_temporary_store(tmp_path, capsys):
    acts, _ = pedalled_progression([EB, AB, BB7, EB], seconds=2.0, repeats=3)
    sid = _store_session(tmp_path / "perf", perform(acts))
    root = str(tmp_path / "perf")
    assert pr.main(["list", "--root", root]) == 0
    assert sid in capsys.readouterr().out
    assert pr.main(["windows", "latest", "--root", root, "--from", "0:04", "--to", "0:08"]) == 0
    out = capsys.readouterr().out
    assert "| 0:04 | 2.0 | Bb7 | 5^7 | Eb major |" in out
    assert "| 0:00 |" not in out
    assert pr.main(["keys", sid, "--root", root]) == 0
    assert "Home key: Eb major" in capsys.readouterr().out
    assert pr.main(["harmony", sid, "--root", root]) == 0
    assert "5 -> 1 (authentic): Bb7 -> Eb" in capsys.readouterr().out
    out_file = tmp_path / "receipts" / "a.json"
    assert pr.main(["analyze", sid, "--root", root, "--out", str(out_file)]) == 0
    doc = json.loads(out_file.read_text(encoding="utf-8"))
    assert doc["session"] == sid and doc["api"] == pr.API
    assert pr.main(["windows", "20260101-000000-deadbeef", "--root", root]) == 2


def test_without_node_the_windows_and_keys_still_come(tmp_path):
    acts, _ = pedalled_progression([EB, AB, BB7, EB], seconds=2.0, repeats=3)
    doc = pr.analyze(perform(acts), node=str(tmp_path / "no-such-node"))
    assert doc["naming"]["source"].startswith("unavailable")
    assert len(doc["windows"]) == 10  # twelve chords, but Eb -> Eb across each repeat is one harmony
    assert all(w["name"] is None for w in doc["windows"])
    assert doc["home_key"] == "Eb major"


# ================================================================================================ verbs
LYD = ["Ab2", "C3", "G3", "Bb3", "D4", "Eb4"]
BB7SUS = ["Bb2", "Eb4", "F4", "Ab4"]
ABM = ["Ab2", "Eb3", "Ab3", "Cb4"]
ABSUS2 = ["Ab2", "Bb3", "Eb4", "Ab4"]
ABADD9 = ["Ab2", "Bb3", "C4", "Eb4"]
DBMAJ9 = ["Db3", "F3", "Ab3", "C4", "Eb4"]
RICH = [EB, LYD, BB7SUS, EB, ABM, EB, ABSUS2, ABADD9, BB7, EB, DBMAJ9, EB]  # Eb major with its colours
LOOP = [EB, CM7, AB, BB7]  # 1 -> 6m -> 4 -> 5, back to back


def _store(root: Path, sid: str, events, opened_at: datetime, closed: bool = True, meta=None) -> str:
    d = root / sid
    d.mkdir(parents=True)
    info = {"session": sid, "opened_at": opened_at.isoformat(), "opened_ns": int(opened_at.timestamp() * 1e9),
            "closed": closed, "event_count": len(events), "meta": meta or {"page": "piano"},
            "duration_s": max((e["t_ms"] for e in events), default=0) / 1000}
    (d / "session.json").write_text(json.dumps(info), encoding="utf-8")
    (d / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return sid


def _run(capsys, *argv):
    code = pr.main([str(a) for a in argv])
    got = capsys.readouterr()
    return code, got.out, got.err


def _words(text: str):
    """The terms of the glossary at the end of an output."""
    if "\nWords:\n" not in text:
        return []
    return [line[2:].split(":")[0] for line in text.split("\nWords:\n", 1)[1].splitlines() if line.startswith("- ")]


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    """A temporary store: a rich Eb major session, a loop session, a modulation, an open empty session and a
    session of single notes. Sids sort by time; the rich session is the latest."""
    root = tmp_path_factory.mktemp("perf")
    now = datetime.now().astimezone()
    ids = {}
    acts, _ = pedalled_progression(LOOP, seconds=2.0, repeats=4)
    ids["loop"] = _store(root, "20260101-100000-00000001", perform(acts), now - timedelta(days=40))
    bb = [["Bb2", "D4", "F4", "A4"], ["G2", "Bb3", "D4", "F4"], ["C3", "Eb4", "G4", "Bb4"], ["F2", "A3", "C4", "Eb4"]]
    acts, t = pedalled_progression(bb, seconds=2.0, repeats=8)
    more, _ = pedalled_progression([["Eb2", "G3", "Bb3", "D4"], CM7, ["F2", "Ab3", "C4", "Eb4"], BB7], seconds=2.0,
                                   repeats=10, start=t)
    ids["modulation"] = _store(root, "20260101-110000-00000002", perform(acts + more), now - timedelta(seconds=40))
    ids["empty"] = _store(root, "20260101-120000-00000003", [], now - timedelta(seconds=30), closed=False)
    single = []
    for k, m in enumerate(["C4", "D4", "E4", "F4", "G4", "E4", "C4"]):
        block(single, k * 800, [m], 600, vel=40 + 5 * k)
    ids["single"] = _store(root, "20260101-130000-00000004", perform(single), now - timedelta(seconds=20))
    acts, _ = pedalled_progression(RICH, seconds=2.5, repeats=3)
    ids["rich"] = _store(root, "20260101-140000-00000005", perform(acts), now - timedelta(seconds=10))
    return root, ids


def test_session_start_prefers_the_page_clock_and_today_uses_it(tmp_path):
    now = datetime.now().astimezone()
    root = tmp_path / "perf"
    buffered = _store(root, "20260101-090000-0000000a", [], now - timedelta(seconds=1),
                      meta={"page": "piano", "buffered": True,
                            "opened_at_client": (now - timedelta(days=3)).astimezone(timezone.utc).isoformat()
                            .replace("+00:00", "Z")})
    fresh = _store(root, "20260101-090001-0000000b", [], now)
    store_ = pr.PerformanceStore(root)
    start = pr.session_start(store_.info(buffered))
    assert abs((start - (now - timedelta(days=3))).total_seconds()) < 1
    assert pr.resolve_sessions(store_, "today") == [fresh]
    assert pr.resolve_sessions(store_, None) == [fresh]  # latest by open time
    with pytest.raises(pr.PerformanceError):
        pr.resolve_sessions(store_, "today", today=(now - timedelta(days=10)).date())


@needs_node
def test_sessions_verb_lists_start_length_notes_home_key_and_areas(store, capsys):
    root, ids = store
    code, out, _ = _run(capsys, "sessions", "--root", root)
    assert code == 0
    lines = {line.split()[-1]: line for line in out.splitlines() if line.strip().startswith("20")}
    rich = next(line for line in out.splitlines() if ids["rich"] in line)
    assert "Eb major" in rich and "1:30" in rich
    assert "(still open)" in next(line for line in out.splitlines() if ids["empty"] in line)
    assert len([line for line in out.splitlines() if "20260101-" in line]) == 5, lines
    code, out, _ = _run(capsys, "sessions", "today", "--root", root, "--json")
    rows = json.loads(out)
    assert ids["loop"] not in [r["session"] for r in rows]  # opened 40 days ago
    by_id = {r["session"]: r for r in rows}
    assert by_id[ids["modulation"]]["key_areas"] == 2 and by_id[ids["modulation"]]["home_key"] == "Eb major"
    assert by_id[ids["empty"]]["home_key"] is None and by_id[ids["empty"]]["notes"] == 0


@needs_node
def test_brief_is_compact_and_covers_what_claude_needs(store, capsys):
    root, ids = store
    code, out, _ = _run(capsys, "brief", "--root", root)  # latest = the rich session
    assert code == 0
    lines = out.rstrip("\n").splitlines()
    assert len(lines) <= 80, len(lines)
    assert lines[0].startswith(f"Brief: Session {ids['rich']} (played ")
    for part in ("Home key: Eb major", "Held harmony", "Most time:", "Moves (quality only", "Colour (share of chord",
                 "Lydian 4:", "Dominants on 5 (", "Outside the key:", "Cadences:", "Touch:", "Ask Daniel about:",
                 "Data caveats:", "Words:"):
        assert part in out, part
    assert "Abmaj9#11~ 4maj9#11" in out  # the timeline shows letters, numbers and readings
    asks = [line for line in lines if re.match(r"^\d\. \d+:\d\d \(replay \d+:\d\d-\d+:\d\d\)", line)]
    assert len(asks) == 3, asks
    assert sum(1 for line in lines if line.startswith("   In plain words: ")) == 3
    words = _words(out)
    assert len(words) == len(set(words)) and {"Lydian", "borrowed", "sus", "numbers"} <= set(words)
    data = json.loads(_run(capsys, "brief", ids["rich"], "--root", root, "--json")[1])
    categories = [m["category"] for m in data["ask"]]
    assert len(set(categories)) == 3
    assert all(abs(a["start_ms"] - b["start_ms"]) >= pr.ASK_SEPARATION_MS for a in data["ask"] for b in data["ask"]
               if a is not b)
    assert data["touch"]["pedal"]["presses"] > 0 and data["colours"]["lydian_4"]


@needs_node
def test_brief_asks_about_a_key_change_with_the_notes_that_changed(store, capsys):
    root, ids = store
    data = json.loads(_run(capsys, "brief", ids["modulation"], "--root", root, "--json")[1])
    change = next(m for m in data["ask"] if m["category"] == "key change")
    assert "Bb major becomes Eb major" in change["what"]
    assert "A in Bb major, Ab in Eb major" in change["plain"]


@needs_node
def test_chords_vocabulary_by_time_with_numbers_and_classes(store, capsys):
    root, ids = store
    data = json.loads(_run(capsys, "chords", ids["rich"], "--root", root, "--json")[1])
    top = data["chords"][0]
    assert top["chord"] == "Eb" and top["in"][0]["number"] == "1" and top["in"][0]["class"] == "diatonic"
    names = {c["chord"]: c for c in data["chords"]}
    assert names["Abm"]["in"][0]["class"] == "borrowed" and names["Abm"]["times"] == 3
    assert abs(sum(c["share"] for c in data["chords"]) - 1) < 0.02
    assert "4maj9#11" in {n["number"] for n in data["numbers"]}
    short = json.loads(_run(capsys, "chords", ids["rich"], "--root", root, "--json", "--min-seconds", 4)[1])
    assert all(c["seconds"] >= 4 for c in short["chords"]) and len(short["chords"]) < len(data["chords"])
    code, out, _ = _run(capsys, "chords", ids["rich"], "--root", root)
    assert code == 0 and "Chord time by class:" in out and "By number" in out


@needs_node
def test_progressions_find_the_loop_and_moves_with_first_times(store, capsys):
    root, ids = store
    data = json.loads(_run(capsys, "progressions", ids["loop"], "--root", root, "--json")[1])
    moves2 = {tuple(g["numbers"]): g for g in data["moves"]["2"]}
    assert moves2[("1", "6m")]["count"] == 4 and moves2[("1", "6m")]["first_at"] == "0:00"
    assert moves2[("5", "1")]["count"] == 3
    loop = data["loops"][0]
    assert loop["numbers"] == ["1", "6m", "4", "5"] and loop["best_reps"] == 4
    exact = json.loads(_run(capsys, "progressions", ids["loop"], "--root", root, "--json", "--exact", "--n", "4",
                            "--min-count", 3)[1])
    assert list(exact["moves"]) == ["4"]
    assert [g["numbers"] for g in exact["moves"]["4"]][0] == ["1", "6m7", "4", "5^7"]
    code, out, _ = _run(capsys, "progressions", ids["loop"], "--root", root)
    assert code == 0 and "1 -> 6m -> 4 -> 5 (and round again): up to 4 times" in out
    assert _run(capsys, "progressions", ids["loop"], "--root", root, "--n", "7")[0] == 2


@needs_node
def test_keys_evidence_names_the_notes_that_changed(store, capsys):
    root, ids = store
    data = json.loads(_run(capsys, "keys", ids["modulation"], "--root", root, "--json")[1])
    (change,) = data["evidence"]["changes"]
    notes = {s["note"]: s for s in change["swapped"]}
    assert set(notes) == {"A", "Ab"} and change["agreeing"] == 2
    assert notes["A"]["before"] > 0.06 and notes["A"]["after"] < notes["A"]["before"] / 3  # the last A still rings
    assert notes["Ab"]["after"] > 0.06 and notes["Ab"]["before"] < 0.01
    assert change["first_chord_after"]["key"] == "Eb major"
    code, out, _ = _run(capsys, "keys", ids["modulation"], "--root", root)
    assert "Home key: Eb major" in out and "key change: Bb major -> Eb major" in out
    assert "A (Bb major)" in out and "Ab (Eb major)" in out


@needs_node
def test_borrowed_lists_source_outside_notes_and_times(store, capsys):
    root, ids = store
    data = json.loads(_run(capsys, "borrowed", ids["rich"], "--root", root, "--json")[1])
    groups = {g["chord"]: g for g in data["groups"]}
    abm = groups["Abm"]
    assert (abm["number"], abm["class"], abm["source"]) == ("4m", "borrowed", "borrowed from Eb minor")
    assert abm["outside_notes"] == [{"note": "Cb", "degree": "b6"}] and len(abm["times"]) == 3
    mixo = [g for g in data["groups"] if g["class"] == "modal" and "Mixolydian" in g["source"]]
    assert mixo and {"note": "Db", "degree": "b7"} in mixo[0]["outside_notes"]
    code, out, _ = _run(capsys, "borrowed", ids["rich"], "--root", root)
    assert "Borrowed from the parallel key" in out and "outside notes Cb (b6)" in out
    assert "borrowed" in _words(out)


@needs_node
def test_colors_count_extensions_lydian_4_suspended_dominants(store, capsys):
    root, ids = store
    data = json.loads(_run(capsys, "colors", ids["rich"], "--root", root, "--json")[1])
    colours = {c["colour"]: c for c in data["colours"]}
    assert {"sus2", "sus4", "#11", "maj7", "add9", "plain triad"} <= set(colours)
    assert all(0 < c["share"] <= 1 for c in data["colours"])
    assert len(data["lydian_4"]) == 3
    assert data["dominants"]["summary"]["suspended"]["windows"] == 3
    code, out, _ = _run(capsys, "colors", ids["rich"], "--root", root)
    assert "Lydian 4 (the 4 chord with its #11): 3 times" in out and "Suspensions (" in out


def test_colour_tags_measure_from_the_analysed_root():
    def w(name, pcs, bass):
        return {"analysed_as": name, "pcs": pcs, "bass": {"note": bass}}
    assert pr.colour_tags(w("Abmaj9#11", ["Ab", "C", "Eb", "G", "Bb", "D"], "Ab2")) == ["maj7", "9", "#11"]
    assert pr.colour_tags(w("Abadd9", ["Ab", "Bb", "C", "Eb"], "Ab2")) == ["add9"]
    assert pr.colour_tags(w("Bb7sus4", ["Bb", "Eb", "F", "Ab"], "Bb2")) == ["sus4", "b7 (plain 7th)"]
    assert pr.colour_tags(w("Eb/G", ["Eb", "G", "Bb"], "G2")) == ["plain triad",
                                                                "inversion (3rd, 5th or 7th in the bass)"]
    assert pr.colour_tags(w("Cm7b5", ["C", "Eb", "Gb", "Bb"], "C3")) == ["b7 (plain 7th)", "b5 (diminished)"]


@needs_node
def test_moment_shows_notes_with_octaves_windows_and_key(store, capsys):
    root, ids = store
    data = json.loads(_run(capsys, "moment", ids["loop"], "0:03", "--window", 1, "--root", root, "--json")[1])
    assert data["key_area"]["key"] == "Eb major"
    assert data["onsets"][0]["at"] == "0:02.0" and data["onsets"][0]["notes"] == ["C3", "Eb4", "G4", "Bb4"]
    assert "Cm7" in [w["chord"] for w in data["windows"]]
    assert data["sounding_at"] == ["C3", "Eb4", "G4", "Bb4"] and data["pedal_down_at"] is True
    code, out, _ = _run(capsys, "moment", "0:03", "--root", root)  # the time alone: the latest session
    assert code == 0 and out.startswith(f"Session {ids['rich']}")
    assert _run(capsys, "moment", ids["loop"], "soon", "--root", root)[0] == 2


def test_parse_voicing_names_midi_and_stacked_notes():
    assert pr.parse_voicing(["Ab3 Eb4 G4", "Bb4,C5", "D5"]) == ([56, 63, 67, 70, 72, 74], -1)
    assert pr.parse_voicing(["56", "63"]) == ([56, 63], 0)
    assert pr.parse_voicing(["Ab", "C", "Eb", "G"]) == ([56, 60, 63, 67], -1)  # stacked upward from octave 3
    assert pr.parse_voicing(["Cb4", "B#3"])[0] == [59, 60]
    with pytest.raises(ValueError):
        pr.parse_voicing(["H3"])


@needs_node
def test_name_gives_every_reading_numbered_in_the_key(capsys):
    code, out, _ = _run(capsys, "name", "Ab3", "Eb4", "G4", "Bb4", "C5", "D5", "--key", "Eb")
    assert code == 0
    assert "The piano page's namer says: Cm9/Ab = 6m9/4" in out
    assert "Analysed as: Abmaj9#11 (reading) = 4maj9#11; diatonic; the Lydian 4" in out
    assert "From the root: Ab3 root, Eb4 5th, G4 maj7, Bb4 9, C5 3rd, D5 #11" in out
    assert "Lydian" in _words(out)
    data = json.loads(_run(capsys, "name", "56 63 67 70 72 74", "--json")[1])
    assert data["analysed"]["name"] == "Abmaj9#11" and data["key"] is None
    assert data["fits_keys"] == ["C minor", "Eb major"]
    assert [r["name"] for r in data["readings"]][0] == "Abmaj9#11"
    assert _run(capsys, "name", "H3")[0] == 2
    assert _run(capsys, "name", "C4", "--key", "Q lydian")[0] == 2
    single = json.loads(_run(capsys, "name", "E4", "--key", "C major", "--json")[1])
    assert single["readings"] == [] and single["detect"]["kind"] == "note"


@needs_node
def test_compare_shows_keys_overlap_and_habits(store, capsys):
    root, ids = store
    data = json.loads(_run(capsys, "compare", ids["loop"], ids["rich"], "--root", root, "--json")[1])
    assert data["a"]["home_key"] == data["b"]["home_key"] == "Eb major"
    shared = [t for t, _, _ in data["numbers"]["shared"]]
    assert "1" in shared and "4" in shared and 0 < data["numbers"]["overlap"] < 1
    assert data["a"]["lydian_4"] == 0 and data["b"]["lydian_4"] == 3
    code, out, _ = _run(capsys, "compare", ids["loop"], "latest", "--root", root)
    assert code == 0 and "Overlap" in out and "Lydian 4 (times)" in out
    assert _run(capsys, "compare", "today", ids["rich"], "--root", root)[0] == 2


@needs_node
def test_history_first_seen_qualities_and_growth(store, capsys):
    root, ids = store
    data = pr.history_data(pr.PerformanceStore(root), days=60)
    assert [g["session"] for g in data["growth"]] == [ids[k] for k in ("loop", "modulation", "empty", "single", "rich")]
    firsts = {q["quality"]: q for q in data["qualities"]}
    assert firsts["m7"]["session"] == ids["loop"]  # Cm7 in the first session
    assert firsts["maj9#11"]["session"] == ids["rich"] and firsts["maj9#11"]["chord"] == "Abmaj9#11"
    rich = data["growth"][-1]
    assert "maj9#11" in rich["new_qualities"] and "m7" not in rich["new_qualities"]
    assert data["growth"][0]["new_qualities"] == []  # nothing is new in the first session looked at
    top = {n["number"]: n for n in data["numbers"]}
    assert top["1"]["sessions"] == 2  # Eb in the loop and the rich session (the modulation plays only 7th chords)
    recent = pr.history_data(pr.PerformanceStore(root), days=30)
    assert ids["loop"] not in [g["session"] for g in recent["growth"]]
    code, out, _ = _run(capsys, "history", "--days", 60, "--root", root)
    assert code == 0 and "Chord qualities, by when each was first played:" in out and "maj9#11" in out
    code, out, _ = _run(capsys, "history", "--days", 60, "--root", root / "nothing-here")
    assert code == 0 and "No sessions in that time." in out


@needs_node
@pytest.mark.parametrize("verb", ["brief", "chords", "progressions", "keys", "borrowed", "colors", "windows",
                                  "harmony"])
def test_every_session_verb_handles_an_open_empty_session_and_single_notes(store, capsys, verb):
    root, ids = store
    code, out, _ = _run(capsys, verb, ids["empty"], "--root", root)
    assert code == 0 and "No notes logged yet." in out and "still open" in out
    code, out, _ = _run(capsys, verb, ids["single"], "--root", root)
    assert code == 0 and ids["single"] in out
    assert json.loads(_run(capsys, verb, ids["single"], "--root", root, "--json")[1])
    code, out, _ = _run(capsys, verb, "today", "--root", root, "--json")
    assert code == 0 and isinstance(json.loads(out), list) and len(json.loads(out)) == 4


@needs_node
def test_single_note_session_says_so_instead_of_inventing_chords(store, capsys):
    root, ids = store
    out = _run(capsys, "brief", ids["single"], "--root", root)[1]
    assert "none: no chords held that long" in out and "hardly any chords were held" in out
    assert "Mostly single notes; most heard:" in out
    assert "No chords held." in _run(capsys, "chords", ids["single"], "--root", root)[1]
    prog = json.loads(_run(capsys, "progressions", ids["single"], "--root", root, "--json")[1])
    assert prog["chords"] == 0 and prog["loops"] == [] and all(v == [] for v in prog["moves"].values())
    assert _run(capsys, "moment", ids["empty"], "0:01", "--root", root)[0] == 0
    moment = json.loads(_run(capsys, "moment", ids["single"], "0:00.8", "--window", 0.1, "--root", root,
                             "--json")[1])
    assert [g["notes"] for g in moment["onsets"]] == [["D4"]] and moment["windows"]


def test_glossary_lists_each_used_term_once_and_ignores_times():
    words = [line for line in pr.glossary("Lydian 4 at 2:13, borrowed Abm, Lydian again, pedal point") if
             line.startswith("- ")]
    assert [w.split(":")[0] for w in words] == ["- borrowed", "- Lydian", "- pedal point"]
    assert pr.glossary("played 22:13 at 1:11, 0:09") == []
    assert "- extensions" in "".join(pr.glossary("Ebmaj9 and Bb11/Ab"))


def test_small_helpers():
    assert pr.clock_tenths(75049) == "1:15.0" and pr.clock_tenths(599960) == "10:00.0"
    assert pr._parse_ns("2..4") == (2, 3, 4) and pr._parse_ns("3") == (3,) and pr._parse_ns("2,4") == (2, 4)
    assert pr.quality("m7b5") == "diminished" and pr.quality("7sus4") == "suspended" and pr.quality("maj9#11") == "major"
    assert pr._degree(6, "Bb major", "F#") == "#5" and pr._degree(11, "Eb major", "Cb") == "b6"


# ================================================================================== verifier must-fix items
def _analyze(acts, **kw):
    return pr.analyze(perform(acts), **kw)


def _sess(events, doc):
    return {"session": "x", "start": None, "closed": True, "events": events, "snd": pr.sounding(events), "doc": doc,
            "problems": []}


@needs_node
def test_readings_take_the_chord_rooted_on_the_bass_and_keep_real_inversions():
    cases = {  # (voicing, key): (analysed name, no 3rd, number); generic shapes, transposed to F
        ("Bb2 F3 Bb3 D4 F5 C6 E6", "F major"): ("Bbadd9(#11)", False, "4add9(#11)"),  # detect: C11/Bb
        ("F2 C3 F3 G5 C6 E6", "F major"): ("Fmaj9", True, "1maj9"),  # detect: Cadd11/F
        ("Bb1 Bb2 A4 C5 F5", "F major"): ("Bbmaj9", True, "4maj9"),  # detect: F/Bb
        ("A2 C5 C#5 Eb5 F5", "F minor"): ("F7b13/A", False, None),  # detect: Dbmaj9/A with no Ab sounding
        ("Eb4 F4 Ab4 Bb4", "Eb major"): ("Ebsus4(9)", False, "1sus4(9)"),  # detect: Bb7sus4/Eb
        ("E3 A3 D4 G4 B4", "C major"): ("Em7(11)", False, None),  # So What: detect A9sus4/E
    }
    for (notes, key), (name, no3, number) in cases.items():
        a = pr.name_data(notes.split(), key)["analysed"]
        assert (a["name"], a["from"], bool(a.get("no3"))) == (name, "reading", no3), (notes, a)
        if number:
            assert a["number"] == number, (notes, a)
    assert "Lydian 4" in pr.name_data("Bb2 F3 Bb3 D4 F5 C6 E6".split(), "F major")["analysed"]["note"]
    out = pr.render_name(pr.name_data("F2 C3 F3 G5 C6 E6".split(), "F major"))
    assert "Analysed as: Fmaj9 (reading, no 3rd) = 1maj9" in out
    for notes, key in (("D3 Bb3 F4 A4 C5", "Bb major"), ("E3 C4 G4 Bb4 D5 A5", "F major"),
                       ("Bb2 Eb4 G4 D5 F5", "Eb major"), ("F2 Bb3 D4 C5", "Eb major"), ("C3 Eb4 G4 Bb4", "Eb major")):
        data = pr.name_data(notes.split(), key)  # an inversion of a chord with its 3rd keeps detect's name
        assert data["analysed"]["from"] == "detect" and data["analysed"]["name"] == data["detect"]["name"], (notes, data)


@needs_node
def test_a_shape_over_the_4_bass_is_the_4_chord_not_a_dominant():
    bb11_over_ab = ["Ab2", "Eb3", "C4", "Ab4", "Bb4", "D5", "Eb5"]
    doc = _analyze(pedalled_progression([EB, bb11_over_ab, BB7, EB, CM7, bb11_over_ab, BB7, EB], seconds=2.5,
                                        repeats=2)[0])
    f = doc["findings"]
    assert [w["analysed_as"] for w in doc["windows"] if w["root"] == "Ab"] == ["Abadd9(#11)"] * 4
    assert {d["analysed_as"] for d in f["dominants"]["windows"]} == {"Bb7"}
    assert f["dominants"]["by_key"]["Eb major"]["with its major 3rd"]["over_root_s"] == 10.0
    assert len(f["lydian_4"]) == 4
    assert not any(c["kind"].startswith("5") and c["chords"][0].startswith("Ab") for c in f["cadences"])


@needs_node
def test_a_one_voice_line_is_not_named_as_chords():
    line = ["D4", "E4", "F#4", "E4", "D4", "C4", "D4", "E4", "F#4", "A4", "B4", "C5", "B4", "A4", "F#4", "E4"]
    acts = []
    for rep in range(4):
        for k, m in enumerate(line):
            block(acts, rep * 4000 + k * 240, [m], 200, vel=50)
    doc = _analyze(acts)
    assert "line" in {w["kind"] for w in doc["windows"]}
    assert not any(pr.is_chord(w) for w in doc["windows"]), [(w["at"], w["name"]) for w in doc["windows"]]
    assert pr.borrowed_data(doc)["groups"] == [] and doc["findings"]["outside_key"] == []
    assert pr.progression_data(doc)["chords"] == 0


@needs_node
def test_a_treble_arpeggio_has_no_bass():
    arp = ["D7", "C#7", "A6", "F#6", "E6", "D6", "C#6", "A5", "F#5", "E5", "D5"]
    acts, t = [], 0
    for _ in range(2):
        acts.append((t, "up", 0, 0))
        acts.append((t + 20, "down", 0, 0))
        for k, m in enumerate(arp):
            block(acts, t + 40 + k * 350, [m], 150, vel=50)
        t += 4000
    acts.append((t, "up", 0, 0))
    events = perform(acts)
    doc = pr.analyze(events)
    chords = [w for w in doc["windows"] if pr.is_chord(w)]
    assert chords and all(w["bass"]["motion"] == "figure" and w["bass"]["low"] is False for w in chords), \
        [(w["at"], w["name"], w["bass"]) for w in doc["windows"]]
    assert doc["findings"]["pedal_points"] == []
    sess = _sess(events, doc)
    text = pr.render_moment(sess, pr.moment_data(sess, chords[0]["start_ms"] + 1000, 1000))
    assert "no low bass" in text and "bass moving" not in text


@needs_node
def test_a_pedal_point_is_measured_on_the_bass_notes_own_sound():
    """Eb1 sounds 2.2 s, then only an Eb4 F4 Ab4 Bb4 cluster pulses above middle C: no long pedal point, and the
    cluster (detect: Bb7sus4/Eb) is heard from its lowest note as Ebsus4(9), not as a suspended dominant."""
    acts = [(0, "down", 0, 0)]
    block(acts, 0, ["Eb1", "Eb2"], 2200, vel=60)
    block(acts, 100, ["F4", "Ab4", "Bb4"], 400)
    acts += [(3000, "up", 0, 0), (3100, "down", 0, 0)]
    block(acts, 3200, ["F4", "Ab4", "Bb4"], 300)
    for k in range(48):
        block(acts, 3200 + k * 250, ["Eb4"], 120, vel=45)
    acts.append((15500, "up", 0, 0))
    doc = _analyze(acts)
    assert doc["findings"]["pedal_points"] == []
    assert not [d for d in doc["findings"]["dominants"]["windows"] if d["form"] == "suspended"]
    long = max(doc["windows"], key=lambda w: w["seconds"])
    assert long["analysed_as"] == "Ebsus4(9)" and long["bass"]["low"] is False, long


@needs_node
def test_cadences_follow_the_bass():
    ab_over_eb = ["Eb2", "Ab3", "C4", "Eb4"]
    cm = ["C3", "Eb4", "G4", "C5"]
    dyad = ["Eb3", "G3"]
    chords = [EB, AB, EB, BB7, EB, ab_over_eb, EB, BB7, cm, AB, BB7, dyad]
    doc = _analyze(pedalled_progression(chords, seconds=2.0, repeats=3)[0])
    kinds = [(c["kind"], tuple(c["chords"]), tuple(c["bass"])) for c in doc["findings"]["cadences"]]
    assert ("4 -> 1 (plagal)", ("Ab", "Eb"), ("Ab2", "Eb2")) in kinds, kinds
    assert ("5 -> 1 (authentic)", ("Bb7", "Eb"), ("Bb2", "Eb2")) in kinds, kinds
    assert ("5 -> 6m (deceptive)", ("Bb7", "Cm"), ("Bb2", "C3")) in kinds, kinds
    assert not any(k[1][0] == "Ab/Eb" for k in kinds)  # the same Eb bass under both chords: no plagal cadence
    assert not any(k[1][-1] == "Eb-G" for k in kinds)  # a two-note shape never arrives


@needs_node
def test_a_suspension_is_a_held_sus_chord_not_a_roll():
    held = [EB, ["Ab2", "Bb3", "Eb4", "Ab4"], ["Ab2", "C4", "Eb4", "Ab4"], BB7, EB]  # Absus2 held, then its 3rd
    doc = _analyze(pedalled_progression(held, seconds=2.0, repeats=3)[0])
    sus = [(s["from"], s["to"], s["resolves"]) for s in doc["findings"]["suspensions"]]
    assert ("Absus2", "Ab", True) in sus, sus
    acts, t = [], 0
    for _ in range(3):  # Eb, then an Abadd9 rolled upward after the pedal lift, its 3rd last
        acts.append((t, "up", 0, 0))
        block(acts, t, EB, 1900)
        acts.append((t + 100, "down", 0, 0))
        acts.append((t + 2000, "up", 0, 0))
        for k, m in enumerate(["Ab2", "Eb3", "Bb3", "C4"]):
            block(acts, t + 2000 + k * 200, [m], 1700 - k * 200)
        acts.append((t + 2050, "down", 0, 0))
        t += 4000
    acts.append((t, "up", 0, 0))
    rolled = _analyze(acts)
    assert rolled["findings"]["suspensions"] == [], rolled["findings"]["suspensions"]


@needs_node
def test_a_long_pause_starts_a_new_section_and_a_short_passage_takes_its_own_centre():
    bb = [["Bb2", "D4", "F4", "A4"], ["G2", "Bb3", "D4", "F4"], ["C3", "Eb4", "G4", "Bb4"], ["F2", "A3", "C4", "Eb4"]]
    eb = [["Eb2", "G3", "Bb3", "D4"], CM7, ["F2", "Ab3", "C4", "Eb4"], BB7]
    acts, t = pedalled_progression(bb, seconds=2.0, repeats=4)
    more, t2 = pedalled_progression(eb, seconds=2.0, repeats=4, start=t + 20000)
    tail, _ = pedalled_progression([["Gb2", "Db3", "Gb3"], ["Db3", "Ab3", "Eb4", "F4", "C5"]], seconds=4.0,
                                   start=t2 + 25000)
    events = perform(acts + more + tail)
    doc = pr.analyze(events)
    areas = doc["keys"]["areas"]
    assert [a["key"] for a in areas] == ["Bb major", "Eb major", "Db major"], areas
    assert areas[1]["after_pause_s"] >= 19 and areas[2]["after_pause_s"] >= 24
    assert [s["at"] for s in doc["sections"]] == [a["at"] for a in areas]
    assert not any(a["into"] == "Eb major" and a["start_ms"] >= areas[2]["start_ms"] for a in doc["keys"]["absorbed"])
    db = [w for w in doc["windows"] if w["root"] == "Db"]
    assert db and db[-1]["number"] == "1maj9" and db[-1]["class"] == "diatonic"
    sess = _sess(events, doc)
    brief = pr.brief_data(sess)
    assert all(m["category"] != "key change" for m in brief["ask"])
    assert brief["changes"] and all(c["pause_s"] for c in brief["changes"])
    assert "new section after a" in pr.render_brief(sess, brief)


@needs_node
def test_a_minor_turn_keeps_its_raised_7th_in_the_plain_words():
    ebm = [["Eb2", "Gb3", "Bb3", "Eb4"], ["Ab2", "Cb4", "Eb4", "Ab4"], BB7, ["Eb2", "Gb3", "Bb3", "Eb4"]]
    acts, t = pedalled_progression([EB, AB, BB7, EB], seconds=2.0, repeats=5)
    more, _ = pedalled_progression(ebm, seconds=2.0, repeats=5, start=t)
    events = perform(acts + more)
    doc = pr.analyze(events)
    assert [a["key"] for a in doc["keys"]["areas"]] == ["Eb major", "Eb minor"]
    sess = _sess(events, doc)
    change = pr.key_evidence(doc, sess["snd"])["changes"][0]
    assert "D" in change["stayed"] and "D" not in change["gone"] and "G" in change["gone"], change
    ask = next(m for m in pr.brief_data(sess)["ask"] if m["category"] == "key change")
    assert "D still sounds" in ask["plain"] and "raised 7th" in ask["plain"], ask["plain"]


def test_recoloured_harmony_is_one_step_in_the_moves():
    def row(name, pcs, bass, seconds=2.0):
        return {"analysed_as": name, "pcs": pcs, "bass": {"note": bass}, "seconds": seconds}
    fm_add9 = row("Fm(add9)", ["F", "G", "Ab", "C"], "F2")
    abmaj13_over_f = row("Abmaj13/F", ["Ab", "Bb", "C", "F", "G"], "F2")
    fm9_over_ab = row("Fm9/Ab", ["F", "G", "Ab", "C", "Eb"], "Ab2")
    assert pr.same_harmony(fm_add9, abmaj13_over_f)  # the same bass: recoloured
    assert pr.same_harmony(abmaj13_over_f, fm9_over_ab, roots={5})  # the step's root F, now over its 3rd
    assert pr.same_harmony(row("Fm7/Ab", ["F", "Ab", "C", "Eb"], "Ab2"), row("Ab6", ["Ab", "C", "Eb", "F"], "Ab2"))
    assert not pr.same_harmony(row("Eb", ["Eb", "G", "Bb"], "Eb2"), row("Cm7", ["C", "Eb", "G", "Bb"], "C3"))  # 1 -> 6m
    assert not pr.same_harmony(row("Abmaj9#11", ["Ab", "C", "Eb", "G", "Bb", "D"], "Ab2"),
                               row("Bb7sus4", ["Bb", "Eb", "F", "Ab"], "Bb2"))
    assert pr.same_harmony(row("Bb", ["Bb", "D", "F"], "Bb2"), row("Bb/D", ["Bb", "D", "F"], "D3"))  # an inversion


def test_a_bass_moving_to_a_new_chords_root_is_a_change():
    """Cm over C, Ebmaj7 over Eb, Gm over G, F over F (2m 4 6m 5, twice) and Eb Bb Eb over their roots (4 1 4 in Bb
    major) stay separate steps; a 7-note wash over a bass does not swallow the next chord over its own root."""
    def row(name, pcs, bass, at, seconds=1.7, key="Bb major", low=True):
        return {"analysed_as": name, "label": name, "pcs": pcs, "bass": {"note": bass, "low": low}, "seconds": seconds,
                "at": at, "start_ms": int(at * 1000), "end_ms": int((at + seconds) * 1000), "key": key,
                "kind": "chord", "analysed_from": "detect", "number": None}
    cycle = [("Cm", ["C", "Eb", "G"], "C3"), ("Ebmaj7", ["Eb", "G", "Bb", "D"], "Eb3"), ("Gm", ["G", "Bb", "D"], "G3"),
             ("F", ["F", "A", "C"], "F3")]
    windows = [row(name, pcs, bass, 1.7 * k) for k, (name, pcs, bass) in enumerate(cycle * 2)]
    steps = pr.chord_sequences({"windows": windows})[0]
    assert [s["token"] for s in steps] == ["2m", "4", "6m", "5"] * 2, [(s["token"], s["merged"]) for s in steps]
    loop = pr.find_loops([steps])[0]
    assert loop["numbers"] == ["2m", "4", "6m", "5"] and loop["runs"][0]["start_ms"] == 0
    four_one = [row("Eb", ["Eb", "G", "Bb"], "Eb3", 0, 2.0), row("Bb", ["Bb", "D", "F"], "Bb2", 2.0, 2.0),
                row("Eb", ["Eb", "G", "Bb"], "Eb3", 4.0, 2.0)]
    assert [s["token"] for s in pr.chord_sequences({"windows": four_one})[0]] == ["4", "1", "4"]
    wash = [row("Bbadd11", ["Bb", "D", "Eb", "F"], "Bb2", 0, 2.0, key="Eb major"),
            row("Cm11b13/Bb", ["C", "D", "Eb", "F", "G", "Ab", "Bb"], "Bb2", 2.0, 1.5, key="Eb major"),
            row("Cm7", ["C", "Eb", "G", "Bb"], "C2", 3.5, 2.5, key="Eb major")]
    assert [s["token"] for s in pr.chord_sequences({"windows": wash})[0]] == ["5", "6m"]
    melody = [row("Ebm(add9,11)", ["Eb", "F", "Gb", "Ab", "Bb"], "Eb5", 0, 1.5, key="Eb minor", low=False),
              row("Gbmaj9/F", ["Gb", "Ab", "Bb", "F"], "F5", 1.5, 1.5, key="Eb minor", low=False)] * 2
    for k, w in enumerate(melody):
        melody[k] = {**w, "at": 1.5 * k, "start_ms": 1500 * k, "end_ms": 1500 * (k + 1)}
    assert pr.chord_sequences({"windows": melody}) == []  # a right-hand melody alone makes no progression


@needs_node
def test_moves_do_not_count_a_minor_chord_renamed_over_its_bass():
    fm_add9, abmaj13_f = ["F2", "G3", "Ab3", "C4"], ["F2", "Ab3", "Bb3", "C4", "G4"]
    fm9_ab = ["Ab2", "F3", "G3", "C4", "Eb4"]
    doc = _analyze(pedalled_progression([EB, fm_add9, abmaj13_f, fm9_ab, BB7], seconds=2.0, repeats=4)[0])
    moves = {tuple(g["numbers"]) for g in pr.progression_data(doc, (2,), 1)["moves"]["2"]}
    assert ("2m", "4") not in moves and ("4", "2m") not in moves, moves


@needs_node
def test_labels_keep_a_missing_3rd():
    acts, _ = pedalled_progression([EB, ["Eb2", "Bb3", "D4"], AB, BB7], seconds=3.0, repeats=3)
    events = perform(acts)
    doc = pr.analyze(events)
    open5 = [w for w in doc["windows"] if sorted(w["pcs"]) == ["Bb", "D", "Eb"]]
    assert open5 and all(w["label"] == "Ebmaj7(no3)" for w in open5), [(w["at"], w["label"]) for w in doc["windows"]]
    assert all(w["label"] == w["analysed_as"] for w in doc["windows"] if w["analysed_as"] in ("Eb", "Ab", "Bb7"))
    sess = _sess(events, doc)
    assert "Ebmaj7(no3)~" in pr.render_brief(sess, pr.brief_data(sess))


def _write_raw(root: Path, sid: str, info: dict, lines):
    d = root / sid
    d.mkdir(parents=True)
    (d / "session.json").write_text(json.dumps({"session": sid, **info}), encoding="utf-8")
    if lines is not None:
        (d / "events.jsonl").write_text(lines, encoding="utf-8")


@needs_node
def test_a_broken_log_is_read_as_far_as_it_goes(tmp_path, capsys):
    root = tmp_path / "perf"
    now = datetime.now().astimezone()
    good = perform(pedalled_progression([EB, AB, BB7, EB], seconds=2.0, repeats=2)[0])
    text = "".join(json.dumps(e) + "\n" for e in good)
    info = {"opened_at": (now - timedelta(minutes=5)).isoformat(), "opened_ns": 1, "closed": True, "duration_s": 16}
    _write_raw(root, "20260102-100000-0000000a", info, text + '{"kind": "on", "note": 60, "t_')  # cut mid-write
    _write_raw(root, "20260102-100100-0000000b", {**info, "opened_ns": 2}, None)  # no events.jsonl at all
    _write_raw(root, "20260102-100200-0000000c", {**info, "opened_ns": 3},
               text + json.dumps({"kind": "off", "note": 60}) + "\n")  # an event without t_ms
    code, out, err = _run(capsys, "brief", "20260102-100000-0000000a", "--root", root)
    assert code == 0 and "1 unreadable log line skipped" in out and "Home key: Eb major" in out, err
    code, out, err = _run(capsys, "brief", "20260102-100100-0000000b", "--root", root)
    assert code == 0 and "No notes logged yet." in out and "events.jsonl could not be read" in out, err
    code, out, err = _run(capsys, "chords", "20260102-100200-0000000c", "--root", root)
    assert code == 0 and "Chords by time" in out, err
    for verb in ("sessions", "history"):
        code, out, err = _run(capsys, verb, "--root", root)
        assert code == 0 and "Traceback" not in err, (verb, err)
    bad = root / "20260102-100300-0000000d"
    bad.mkdir()
    (bad / "session.json").write_text("{not json", encoding="utf-8")
    code, out, err = _run(capsys, "brief", "20260102-100300-0000000d", "--root", root)
    assert code == 2 and "20260102-100300-0000000d" in err, err


@needs_node
def test_notes_still_held_when_the_log_ends(tmp_path, capsys):
    root = tmp_path / "perf"
    now = datetime.now().astimezone()
    events = [{"t_ms": t, "kind": "on", "note": m, "vel": 60} for t, m in ((0, 60), (5, 64), (9, 67))]
    _store(root, "20260103-100000-0000000a", events, now - timedelta(hours=1), closed=True)
    code, out, _ = _run(capsys, "brief", "20260103-100000-0000000a", "--root", root)
    assert code == 0 and "Home key: none yet" in out and "3 notes were still sounding when the log ends" in out, out
    assert "Key areas: none yet" in out and "0:00-0:00" not in out  # no key area named for a session without chords
    assert "notes a minute" not in out  # nor a rate for a session of a few milliseconds
    _store(root, "20260103-100100-0000000b", events, now - timedelta(seconds=6), closed=False)
    code, out, _ = _run(capsys, "brief", "20260103-100100-0000000b", "--root", root)
    assert code == 0 and "Home key: C major" in out and "counted up to now" in out, out


@needs_node
def test_cli_refuses_times_and_numbers_that_make_no_sense(store, capsys):
    root, ids = store
    bad = [("moment", ids["rich"], "1:75"), ("moment", ids["rich"], "99:00"),
           ("moment", ids["rich"], "0:10", "--window", "-5"), ("moment", ids["rich"], "0:10", "--window", "0"),
           ("windows", ids["rich"], "--from", "1:00", "--to", "0:30"),
           ("progressions", ids["rich"], "--min-count", "0"), ("history", "--days", "-1"),
           ("compare", ids["rich"], ids["rich"]), ("chords", ids["rich"], "--min-seconds", "-1")]
    for argv in bad:
        code, _, err = _run(capsys, *argv, "--root", root)
        assert code == 2 and err.strip(), argv
    assert _run(capsys, "moment", ids["rich"], "1:29", "--root", root)[0] == 0


@needs_node
def test_piped_output_is_utf8():
    import os
    import subprocess
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    proc = subprocess.run([sys.executable, "-m", "arsenal.practice", "name", "C3", "Eb3", "Gb3", "A3", "--key",
                           "Bb major"], cwd=ROOT, env=env, capture_output=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    text = proc.stdout.decode("utf-8")  # raises if the console code page leaked through
    assert "°" in text


def _triad(root: str, quality: str):
    names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    r = names.index(root)
    steps = {"": (4, 7, 12), "m": (3, 7, 12), "7": (4, 7, 10)}[quality]
    return [f"{names[(r + s) % 12]}{4 if r + s < 12 else 5}" for s in steps]


@needs_node
def test_brief_fits_in_80_lines_with_many_key_areas():
    keys = [("C", "A", "F", "G"), ("A", "F#", "D", "E"), ("F", "D", "Bb", "C"), ("D", "B", "G", "A"),
            ("Bb", "G", "Eb", "F"), ("G", "E", "C", "D"), ("Eb", "C", "Ab", "Bb")]
    acts, t = [], 0
    for one, six, four, five in keys:
        chords = [[f"{one}2"] + _triad(one, ""), [f"{six}2"] + _triad(six, "m"), [f"{four}2"] + _triad(four, ""),
                  [f"{five}2"] + _triad(five, "7")]
        more, t = pedalled_progression(chords, seconds=2.0, repeats=4, start=t)
        acts += more
    events = perform(acts)
    doc = pr.analyze(events)
    assert len(doc["keys"]["areas"]) >= 6, [a["key"] for a in doc["keys"]["areas"]]
    sess = _sess(events, doc)
    text = pr.render_brief(sess, pr.brief_data(sess))
    assert "\nWords:\n" in text  # the brief carries its own words, fitted to its cap
    total = len(text.rstrip("\n").splitlines())
    assert total <= pr.BRIEF_MAX_LINES, total
    counts, area = {}, None  # every key area of 20 s or more keeps at least three chords in the timeline
    for line in text.split("Held harmony", 1)[1].split("\n\n", 1)[0].splitlines()[1:]:
        m = re.match(r"\s+\[([^\],]+)[^\]]*\] (.*)", line)
        if m:
            area, line = m.group(1), m.group(2)
            counts.setdefault(area, 0)
        counts[area] += len(re.findall(r"(?:^|\| )\d+:\d\d ", line.strip()))
    long_areas = {a["key"] for a in doc["keys"]["areas"] if a["seconds"] >= pr.ASK_MIN_AREA_S}
    assert long_areas and all(counts.get(k, 0) >= 3 for k in long_areas), counts


# ================================================================================ round-2 verifier must-fix items
@needs_node
def test_one_chord_built_under_one_pedal_is_not_a_key_change():
    """Eb major, then an F chord built note by note under one pedal (F C, A, F, then Eb, G, Bb) and Cm11: one Eb major
    area, the F chord one window numbered 2 (the 5 of 5, with nothing to land on), and no Lydian 4 from it."""
    acts, t = pedalled_progression([EB, AB, BB7, EB, CM7, AB, BB7, EB], seconds=2.5, repeats=2)
    for dt, m in [(0, "F2"), (0, "C3"), (400, "A4"), (800, "F3"), (2600, "Eb5"), (3300, "G5"), (3800, "Bb5")]:
        block(acts, t + dt, [m], 5800 - dt)
    acts += [(t + 150, "down", 0, 0), (t + 5900, "up", 0, 0)]
    block(acts, t + 6000, ["C3", "G3", "D4", "Eb4", "F4", "G4", "Bb4"], 4800)
    acts += [(t + 6100, "down", 0, 0), (t + 11000, "up", 0, 0)]
    doc = _analyze(acts)
    assert [a["key"] for a in doc["keys"]["areas"]] == ["Eb major"], doc["keys"]
    late = [w for w in doc["windows"] if w["start_ms"] >= t - 100]
    f_windows = [w for w in late if w["root"] == "F"]
    assert len(f_windows) == 1, [(w["at"], w["name"], w["pcs"]) for w in late]
    w = f_windows[0]
    assert w["number"].startswith("2") and w["class"] == "secondary dominant", w
    assert w["class_detail"] == "5 of 5, not followed by its target", w["class_detail"]
    assert not [m for m in doc["findings"]["lydian_4"] if m["start_ms"] >= t - 100]


@needs_node
def test_grace_notes_crushes_and_notes_that_stopped_are_not_chord_tones():
    """A 40 ms grace note and a soft crush a half step under a loud note never become chord tones (no secondary dominant
    from a grace note's b7); a note released just before a short window is not in its chord."""
    ebm = ["Eb2", "Gb3", "Bb3", "Eb4"]
    acts, t = pedalled_progression([ebm, ["Ab2", "B3", "Eb4", "Ab4"], BB7, ebm], seconds=2.5, repeats=3)
    block(acts, t, ["Ab2", "Ab3", "B4"], 1250)
    acts += [(t + 100, "down", 0, 0), (t + 1300, "up", 0, 0)]
    block(acts, t + 1300, ["G2", "G3", "Eb5"], 1300)
    block(acts, t + 1340, ["Db5"], 40, vel=30)  # a grace note
    block(acts, t + 1350, ["B4"], 1250, vel=20)  # a soft crush into...
    block(acts, t + 1380, ["Bb4"], 1220, vel=75)  # ...the loud Bb4
    acts += [(t + 1450, "down", 0, 0), (t + 2650, "up", 0, 0)]
    block(acts, t + 2650, ["Eb2", "G4", "Bb4"], 2800)
    acts += [(t + 2750, "down", 0, 0), (t + 5500, "up", 0, 0)]
    doc = _analyze(acts)
    late = [w for w in doc["windows"] if w["start_ms"] >= t + 1200]
    assert late and not any({"Db", "C#"} & set(w["pcs"]) for w in late), [(w["at"], w["name"], w["pcs"]) for w in late]
    struck = next(w for w in late if w["start_ms"] <= t + 1500 < w["end_ms"])  # G2 G3 Eb5 Bb4 with the grace and crush
    assert not {"Cb", "B", "Db", "C#"} & set(struck["pcs"]) and struck["root"] == "Eb", (struck["name"], struck["pcs"])
    assert not [w for w in doc["windows"] if w["class"] == "secondary dominant"]
    acts = []
    block(acts, 0, ["C3", "E4", "G4"], 2000)
    block(acts, 2000, ["C4", "E4", "G4"], 250)  # re-struck short and released, no pedal
    block(acts, 2260, ["Bb2", "D4", "F4"], 650)
    block(acts, 2910, ["Eb3", "G3", "Bb3"], 2000)
    doc = _analyze(acts)
    short = next(w for w in doc["windows"] if abs(w["start_ms"] - 2260) <= 60)
    assert set(short["pcs"]) == {"Bb", "D", "F"}, (short["name"], short["pcs"])


@needs_node
def test_a_pedalled_treble_run_is_a_line_not_a_progression():
    run = ["Eb5", "F5", "Gb5", "Ab5", "Bb5", "B5", "Db6", "Eb6", "Db6", "B5", "Bb5", "Ab5", "Gb5", "F5"]
    acts, t = [], 0
    for _ in range(3):
        acts += [(t, "up", 0, 0), (t + 30, "down", 0, 0)]
        for k, m in enumerate(run):
            block(acts, t + 60 + k * 260, [m], 200, vel=55)
        t += 60 + len(run) * 260 + 200
    acts.append((t, "up", 0, 0))
    doc = _analyze(acts)
    shown = [(w["at"], w["name"], w["kind"]) for w in doc["windows"]]
    assert pr.progression_data(doc)["chords"] == 0 and pr.progression_data(doc)["loops"] == [], shown
    assert any(w["kind"] == "line" and " run " in w["name"] for w in doc["windows"]), shown
    assert doc["findings"]["outside_key"] == [] and doc["findings"]["pedal_points"] == []


@needs_node
def test_a_bass_walking_under_a_repeated_dyad_is_a_bass_line_not_a_chord():
    ebm = ["Eb2", "Gb3", "Bb3", "Eb4"]
    acts, t = pedalled_progression([ebm, ["Ab2", "B3", "Eb4", "Ab4"], BB7, ebm], seconds=2.0, repeats=3)
    for k, bass in enumerate(["Eb1", "Bb0", "Ab1", "B0"]):
        acts += [(t + k * 600, "up", 0, 0), (t + k * 600 + 60, "down", 0, 0)]
        block(acts, t + k * 600, [bass], 560, vel=65)
    for k in range(8):
        block(acts, t + k * 300, ["Bb4", "Eb5"], 280, vel=45)
    acts.append((t + 2400, "up", 0, 0))
    block(acts, t + 2500, ebm, 2000)
    doc = _analyze(acts)
    span = [w for w in doc["windows"] if t - 100 <= w["start_ms"] < t + 2300]
    assert any(w["kind"] == "bass line" and w["name"].startswith("bass line ") and " under " in w["name"]
               for w in span), [(w["at"], w["name"], w["kind"], w["bass"]) for w in span]
    assert not [w for w in span if pr.is_chord(w) and w["seconds"] >= 1.5], [(w["at"], w["name"]) for w in span]
    assert "## Bass lines" in pr.render_harmony(doc)


@needs_node
def test_one_harmony_with_a_tune_over_its_root_is_not_a_pedal_point():
    acts, t = pedalled_progression([EB, AB, BB7, EB], seconds=2.0, repeats=2)
    acts.append((t, "down", 0, 0))
    block(acts, t, ["Ab1", "Ab2"], 6000, vel=50)  # held by the fingers under a tune: F5 G5 Eb5 G5
    for k, m in enumerate(["F5", "G5", "Eb5", "G5"]):
        block(acts, t + 100 + k * 1450, [m], 1400, vel=60)
    acts.append((t + 6000, "up", 0, 0))
    block(acts, t + 6100, EB, 2000)
    doc = _analyze(acts)
    assert not [p for p in doc["findings"]["pedal_points"] if p["start_ms"] >= t - 100], doc["findings"]["pedal_points"]


@needs_node
def test_lydian_4_counts_moments_and_the_5_chord_over_the_4_bass_is_a_dominant():
    lyd_a, lyd_b = ["Ab2", "C4", "Eb4", "D5"], ["Ab2", "Eb3", "G3", "C4", "Bb4", "D5"]
    over4 = ["Ab1", "Ab2", "Bb3", "D4", "Eb4", "F4"]  # the 5 chord's notes (and Eb) over the 4 bass, no C
    over3, over1 = ["G1", "G2", "Bb3", "D4", "F4"], ["Eb1", "Eb2", "Bb3", "D4", "F4"]
    home = ["Eb2", "Eb3", "G3", "Bb3", "Eb4"]
    chords = [EB, lyd_a, lyd_b, EB, BB7, EB, over4, over3, over1, home, AB, BB7, EB]
    seconds = [2.0, 1.5, 1.5, 2.0, 2.0, 2.0, 2.2, 0.9, 1.6, 2.5, 2.0, 2.0, 2.0]
    acts, t = [], 0
    for notes, s in zip(chords, seconds):
        acts += [(t, "up", 0, 0), (t + 100, "down", 0, 0)]
        block(acts, t, notes, int(s * 1000) - 100)
        t += int(s * 1000)
    acts.append((t, "up", 0, 0))
    doc = _analyze(acts)
    f = doc["findings"]
    lyd = f["lydian_4"]
    assert len(lyd) == 1 and lyd[0]["seconds"] >= 2.9, [(m["at"], m["label"], m["seconds"]) for m in lyd]
    heard = [d for d in f["dominants"]["windows"] if d["over"] == "4"]
    assert heard and heard[0]["label"] == "Bb7/Ab" and heard[0]["number"] == "5^7/4", f["dominants"]["windows"]
    kinds = [(c["kind"], c["chords"][0]) for c in f["cadences"]]
    assert any(k == "5 over a 1 pedal -> 1" and first.startswith("Bb") for k, first in kinds), kinds


def test_split_returns_cuts_a_minor_area_around_its_major_return():
    area = {"state": pr.KEYS.index((3, "minor")), "start_ms": 0, "end_ms": 60000, "section": 0}

    def w(a, b, pcs):
        return {"start_ms": a, "end_ms": b, "pcs": pcs}
    ebm, eb, eb_g, abm, dyad = [3, 6, 10], [3, 7, 10], [7, 3, 10], [8, 11, 3], [3, 5]
    windows = [w(0, 10000, ebm), w(10000, 20000, ebm), w(20000, 22000, dyad), w(22000, 26000, eb), w(26000, 28000, abm),
               w(28000, 33000, eb_g), w(33000, 40000, ebm), w(40000, 60000, ebm)]
    got = [(pr.KEYS[a["state"]], a["start_ms"], a["end_ms"], bool(a.get("return"))) for a in pr.split_returns([area], windows)]
    assert got == [((3, "minor"), 0, 20000, False), ((3, "major"), 20000, 33000, True), ((3, "minor"), 33000, 60000, False)]
    brief = [w(0, 20000, ebm), w(20000, 23000, eb), w(23000, 60000, ebm)]  # three seconds of Eb: colour, not a return
    assert len(pr.split_returns([area], brief)) == 1


@needs_node
def test_asks_never_treat_the_home_tonic_as_outside_or_repeat_a_return():
    ebm, abm = ["Eb2", "Gb3", "Bb3", "Eb4"], ["Ab2", "B3", "Eb4", "Ab4"]
    acts, t = pedalled_progression([EB, AB, BB7, EB], seconds=2.5, repeats=4)
    more, t2 = pedalled_progression([ebm, abm, BB7, ebm], seconds=2.5, repeats=4, start=t)
    back, t3 = pedalled_progression([EB, ["G2", "Eb4", "G4", "Bb4"], abm, EB, EB], seconds=2.6, start=t2)
    rest, _ = pedalled_progression([ebm, abm, BB7, ebm], seconds=2.5, repeats=3, start=t3)
    events = perform(acts + more + back + rest)
    doc = pr.analyze(events)
    assert [a["key"] for a in doc["keys"]["areas"]] == ["Eb major", "Eb minor", "Eb major", "Eb minor"], doc["keys"]
    sess = _sess(events, doc)
    asks = pr.brief_data(sess)["ask"]
    tonic = [m for m in asks if m["category"] == "outside the key" and re.match(r"Eb(/G)? =", m["what"])]
    assert not tonic, asks
    spans = sorted((pr.parse_clock(m["replay"][0]), pr.parse_clock(m["replay"][1])) for m in asks)
    assert len({m["category"] for m in asks}) == len(asks) and all(b[0] >= a[0] for a, b in zip(spans, spans[1:]))


@needs_node
def test_an_impossible_event_time_is_dropped_not_allocated(tmp_path, capsys):
    import time
    root = tmp_path / "perf"
    now = datetime.now().astimezone()
    good = perform(pedalled_progression([EB, AB, BB7, EB], seconds=2.0, repeats=2)[0])
    bad = good + [{"t_ms": 1.76e12, "kind": "off", "note": 60}]  # an epoch time logged by mistake
    sid = _store(root, "20260104-100000-0000000a", bad, now - timedelta(minutes=5))
    started = time.monotonic()
    code, out, err = _run(capsys, "sessions", "--root", root)
    assert code == 0 and "impossible time" in out and sid in out, (out, err)
    code, out, _ = _run(capsys, "brief", sid, "--root", root)
    assert code == 0 and "Home key: Eb major" in out and "impossible time" in out, out
    assert _run(capsys, "history", "--days", 30, "--root", root)[0] == 0
    assert time.monotonic() - started < 30
    doc = pr.analyze(bad)
    assert doc["impossible_events"] == 1 and doc["duration_s"] < 60


@needs_node
def test_a_short_phrase_after_a_long_pause_stays_its_own_section():
    c_major = [["C3", "E4", "G4", "C5"], ["A2", "C4", "E4", "A4"], ["F2", "A3", "C4", "F4"], ["G2", "B3", "D4", "G4"]]
    acts, t = pedalled_progression(c_major, seconds=2.0, repeats=3)
    more, _ = pedalled_progression([["D3", "F4", "A4", "C5"]], seconds=3.0, start=t + 600000)
    events = perform(acts + more)
    doc = pr.analyze(events)
    assert len(doc["sections"]) == 2 and doc["sections"][1]["pause_before_s"] >= 590, doc["sections"]
    assert doc["keys"]["areas"][-1]["after_pause_s"] >= 590
    sess = _sess(events, doc)
    text = pr.render_brief(sess, pr.brief_data(sess))
    timeline = text.split("Held harmony", 1)[1].split("\n\n", 1)[0]
    areas_line = re.split(r"\n\S|\n  \d", text.split("Key areas", 1)[1], maxsplit=1)[0]  # with its wrapped lines
    assert "after a 600 s pause" in timeline and "after a 600 s pause" in areas_line, text


@needs_node
def test_a_chromatic_note_inside_a_pedalled_scale_run_is_not_outside_the_key():
    acts, t = pedalled_progression([EB, AB, BB7, EB], seconds=2.0, repeats=3)
    acts += [(t, "up", 0, 0), (t + 50, "down", 0, 0)]
    block(acts, t, ["Ab2", "Eb3"], 4200, vel=45)
    for k, m in enumerate(["Ab4", "Bb4", "C5", "Db5", "D5", "Eb5", "F5", "G5"]):
        block(acts, t + 200 + k * 480, [m], 420, vel=60)
    acts.append((t + 4200, "up", 0, 0))
    block(acts, t + 4300, EB, 2000)
    doc = _analyze(acts)
    late = [o for o in doc["findings"]["outside_key"] if any(pr.parse_clock(x) * 1000 >= t - 1000 for x in o["times"])]
    assert not late, late


def test_cli_session_paths_and_bad_options(store, capsys, tmp_path):
    if NODE is None:
        pytest.skip("node is needed to run piano.js Theory.detect")
    root, ids = store
    assert _run(capsys, "keys", ids["rich"] + "/", "--root", root)[0] == 0  # tab completion's trailing slash
    assert _run(capsys, "keys", str(Path(root) / ids["rich"]), "--root", root)[0] == 0  # a session directory
    code, _, err = _run(capsys, "brief", ids["rich"], "--root", root, "--out", tmp_path)
    assert code == 2 and "directory" in err
    for argv in (("windows", ids["rich"], "--limit", "0"), ("windows", ids["rich"], "--from", "9:00"),
                 ("history", "--days", "0.01"), ("moment", ids["rich"], "0:30", "--window", "inf"),
                 ("history", "--days", "inf"), ("chords", ids["rich"], "--min-seconds", "nan"),
                 ("moment", ids["rich"], "0:30", "--window", "nan")):
        code, _, err = _run(capsys, *argv, "--root", root)
        assert code == 2 and "Traceback" not in err, argv


def test_glossary_examples_follow_the_home_key():
    text = "\n".join(pr.glossary("the Lydian 4, borrowed, extensions", "Db major"))
    assert "C over Gb in Db major" in text and "(Db minor for Db major)" in text
    assert "D over Ab in Eb major" in "\n".join(pr.glossary("the Lydian 4"))  # Eb major without a home key
    folded = pr.glossary("numbers, Lydian, velocity, semitone, runner-up, new section after a pause", "C major", 6)
    assert "- Lydian: " in "\n".join(folded) and any(line.startswith("- also: ") for line in folded), folded


@needs_node
def test_a_deceptive_cadence_through_a_sus_on_6_but_not_a_neighbour_motion():
    csus4, cm = ["C3", "F4", "G4", "C5"], ["C3", "Eb4", "G4", "C5"]
    doc = _analyze(pedalled_progression([EB, AB, BB7, csus4, cm, AB, BB7, EB], seconds=2.0, repeats=3)[0])
    kinds = [(c["kind"], tuple(c["chords"])) for c in doc["findings"]["cadences"]]
    assert ("5 -> 6m (deceptive)", ("Bb7", "Csus4", "Cm")) in kinds, kinds
    doc = _analyze(pedalled_progression([EB, AB, cm, BB7, cm, AB, BB7, EB], seconds=2.0, repeats=3)[0])
    assert not [c for c in doc["findings"]["cadences"] if "deceptive" in c["kind"]], doc["findings"]["cadences"]


@needs_node
def test_a_chromatic_bass_line_under_held_notes_is_one_finding():
    bb = [["Bb2", "D4", "F4", "A4"], ["Eb2", "G3", "Bb3", "D4"], ["F2", "A3", "C4", "Eb4"], ["Bb2", "D4", "F4", "Bb4"]]
    acts, t = pedalled_progression(bb, seconds=2.0, repeats=3)
    block(acts, t, ["Bb4", "D5", "C6"], 9000, vel=40)  # held by the fingers over the walking bass
    for k, bass in enumerate(["G3", "F#3", "F3", "E3", "Eb3"]):
        acts += [(t + k * 1800, "up", 0, 0), (t + k * 1800 + 80, "down", 0, 0)]
        block(acts, t + k * 1800, [bass], 1750, vel=55)
    acts.append((t + 9000, "up", 0, 0))
    more, _ = pedalled_progression([["F2", "A3", "C4", "F4"], ["G2", "Bb3", "D4", "G4"], bb[0]], seconds=2.0,
                                   start=t + 9000)
    doc = _analyze(acts + more)
    lines = doc["findings"]["bass_lines"]
    walk = [b for b in lines if b["start_ms"] >= t - 100]
    assert walk and walk[0]["direction"] == "falling" and walk[0]["chromatic"], lines
    assert [pr._sp_pc(pr._parse_name(re.sub(r"-?\d+$", "", x))) for x in walk[0]["notes"]][:5] == [7, 6, 5, 4, 3]


def test_glossary_explains_carets_and_two_note_shapes():
    assert "- ^ in numbers" in "\n".join(pr.glossary("Bb7sus4/Eb = 5^7sus4/1"))
    assert "- two-note shape" in "\n".join(pr.glossary("arrives on 1-3 (Bb-D)"))
    assert "two-note shape" not in "\n".join(pr.glossary("0:27-1:27 D major; 1^5 power"))
    assert pr.parse_clock("1:15") == 75000 and pr.parse_clock("75") == 75000
    with pytest.raises(ValueError):
        pr.parse_clock("1:75")


# ================================================================================ round-3 verifier must-fix items
F_MAJOR = [["F2", "A3", "C4", "F4"], ["Bb2", "D4", "F4", "Bb4"], ["C3", "E4", "G4", "Bb4"], ["F2", "A3", "C4", "F4"]]


@needs_node
def test_a_chord_unfolding_or_gaining_a_note_over_its_bass_is_not_a_pedal_point():
    """C2 held under an F arpeggio that starts on G A (a moment of Csus4, then Fadd9/C), and A2 held under Gm9 that
    gains its 11th (Gm9/A, then Gm11/A): one harmony each, so no pedal point; generic shapes, in F major."""
    acts, t = pedalled_progression(F_MAJOR, seconds=2.0, repeats=2)
    acts += [(t, "up", 0, 0), (t + 200, "down", 0, 0)]
    block(acts, t, ["C2", "C3"], 5900, vel=40)
    for k, m in enumerate(["G5", "A5", "F5", "G5", "A5", "F5", "C5"]):
        block(acts, t + 150 + k * 400, [m], 350, vel=50)
    acts.append((t + 6000, "up", 0, 0))
    more, t2 = pedalled_progression(F_MAJOR, seconds=2.0, start=t + 6000)
    acts += more + [(t2, "up", 0, 0), (t2 + 100, "down", 0, 0)]
    block(acts, t2, ["A2"], 4900, vel=45)
    block(acts, t2 + 50, ["F4", "Bb4", "G5"], 4800, vel=50)
    block(acts, t2 + 1300, ["C5"], 3550, vel=50)
    acts.append((t2 + 5000, "up", 0, 0))
    acts += pedalled_progression([["Bb2", "D4", "F4", "A4"], ["C3", "E4", "G4", "Bb4"], ["F2", "A3", "C4", "F4"]],
                                 seconds=2.0, start=t2 + 5000)[0]
    doc = _analyze(acts)
    late = [p for p in doc["findings"]["pedal_points"] if p["start_ms"] >= t - 100]
    assert not late, late
    x = {"_pcs": [0, 5, 7], "_root_pc": 5, "third": None}  # Csus4's notes, then Fadd9's: a subset, the same harmony
    y = {"_pcs": [5, 7, 9, 0], "_root_pc": 5, "third": "major"}
    assert not pr._different_harmonies(x, y)
    assert pr._different_harmonies({"_pcs": [0, 4, 7], "_root_pc": 0, "third": "major"},
                                   {"_pcs": [5, 9, 0], "_root_pc": 5, "third": "major"})


@needs_node
def test_a_brush_a_neighbour_note_and_an_approach_bass_are_not_outside_the_key():
    """In F major: B4 v33 brushed 40 ms after C5 v79 and released at once under the pedal; B5 as an upper neighbour
    between two A5s over a D bass; B1 (octaves, struck once) stepping from F2 down to A1. None is a chord outside the key."""
    acts, t = pedalled_progression(F_MAJOR, seconds=2.0, repeats=2)
    acts += [(t, "up", 0, 0), (t + 100, "down", 0, 0)]
    block(acts, t, ["A2", "F3", "E4"], 3100, vel=70)  # Fmaj7/A...
    block(acts, t + 360, ["C5"], 570, vel=79)
    block(acts, t + 400, ["B4"], 50, vel=33)  # ...and the brush
    block(acts, t + 860, ["A4"], 880, vel=71)
    acts.append((t + 3150, "up", 0, 0))
    t += 3200
    acts += [(t, "up", 0, 0), (t + 100, "down", 0, 0)]
    block(acts, t, ["D3"], 600, vel=46)
    block(acts, t + 200, ["A5", "A6"], 380, vel=60)
    block(acts, t + 650, ["A3"], 540, vel=42)
    block(acts, t + 720, ["B5", "B6"], 270, vel=55)  # the neighbour
    acts += [(t + 1690, "up", 0, 0), (t + 1840, "down", 0, 0)]
    block(acts, t + 1680, ["D3"], 400, vel=53)
    block(acts, t + 1740, ["A5", "A6"], 230, vel=56)
    block(acts, t + 2200, ["Bb5", "Bb6"], 200, vel=50)
    block(acts, t + 2200, ["A3", "D4"], 1600, vel=45)
    acts.append((t + 3900, "up", 0, 0))
    t += 4000
    for bass, dur, top in ((["F2", "F3"], 800, ["C6", "E6"]), (["B1", "B2"], 700, ["C6"]), (["A1", "A2"], 550, ["C6"]),
                           (["Bb1", "Bb2"], 2000, ["D5", "F5", "A5"])):
        acts += [(t, "up", 0, 0), (t + 120, "down", 0, 0)]
        block(acts, t, bass, dur - 40, vel=50)
        block(acts, t, top, dur - 40, vel=55)
        t += dur
    acts.append((t, "up", 0, 0))
    acts += pedalled_progression(F_MAJOR[2:], seconds=2.0, start=t)[0]
    doc = _analyze(acts)
    outside = [(o["chord"], o["times"]) for o in doc["findings"]["outside_key"]]
    assert not outside, outside
    assert not [w for w in doc["windows"] if "B" in w["pcs"] and w["class"] not in pr.NON_CHORD_CLASSES]
    assert not [m for m in pr.borrowed_data(doc)["moments"] if any(n["note"] == "B" for n in m["outside_notes"])]
    n1 = {"note": 71, "vel": 33, "on_ms": 40, "off_ms": 90, "end_ms": 3000}  # the brush on its own
    c5 = {"note": 72, "vel": 79, "on_ms": 0, "off_ms": 570, "end_ms": 3000}
    assert pr._ornament(n1, [c5, n1]) and not pr._ornament({**n1, "off_ms": 600, "vel": 70}, [c5, n1])


@needs_node
def test_a_minor_chord_over_its_3rd_is_heard_from_its_held_bass_unless_its_root_is_there():
    """Bbmaj7 -> F C D E A over F (detect: Dm9/F) is 4 -> 1, a plagal cadence; Gm(add9) then Gm9/Bb keeps its Gm name; a
    shell Gm7 is labelled without its 5th; a dominant with both 3rds carries its 11th (in F major)."""
    fmaj = ["F2", "C3", "D4", "E4", "A4"]
    chords = [["F2", "A3", "C4", "F4"], ["Bb2", "D4", "F4", "A4"], fmaj, ["C3", "E4", "G4", "Bb4"]]
    doc = _analyze(pedalled_progression(chords, seconds=3.0, repeats=3)[0])
    home = [w for w in doc["windows"] if w["bass"]["note"] == "F2" and "D" in w["pcs"] and "E" in w["pcs"]]
    assert home and all(w["analysed_as"] == "Fmaj7(13)" and w["number"] == "1maj7(13)" for w in home), \
        [(w["at"], w["name"], w["analysed_as"]) for w in home]
    kinds = [(c["kind"], c["chords"][-1]) for c in doc["findings"]["cadences"]]
    assert ("4 -> 1 (plagal)", "Fmaj7(13)") in kinds, kinds
    gm_add9, gm9_bb = ["G2", "A3", "Bb3", "D4"], ["Bb2", "G3", "A3", "D4", "F4"]
    doc = _analyze(pedalled_progression([chords[0], gm_add9, gm9_bb, chords[3]], seconds=2.0, repeats=3)[0])
    over3 = [w for w in doc["windows"] if w["bass"]["note"] == "Bb2"]
    assert over3 and all(w["analysed_as"] == "Gm9/Bb" for w in over3), [(w["at"], w["analysed_as"]) for w in over3]
    assert pr.name_data("Bb2 G3 A3 D4 F4".split(), "F major")["analysed"]["name"] == "Bbmaj7(13)"  # alone: from its bass
    doc = _analyze(pedalled_progression([chords[0], ["G2", "Bb3", "F4"], chords[3], chords[0]], seconds=2.0,
                                        repeats=2)[0])
    shells = [w for w in doc["windows"] if w["analysed_as"] == "Gm7"]
    assert shells and all(w["label"] == "Gm7(no5)" for w in shells), [(w["at"], w["label"]) for w in doc["windows"]]
    a = pr.name_data("C3 G3 Eb4 E4 F5 A5 Bb5".split(), "F major")["analysed"]
    assert (a["name"], a["from"], a["number"]) == ("C13#9(11)", "reading", "5^13#9(11)"), a


def test_labels_keep_a_6_9_whole_when_marking_a_missing_5th():
    w = {"info": None, "pcs": [6, 8, 10, 3], "root_pc": 6, "suffix": "6/9", "texture": "chord", "reading": None,
         "from": "detect", "no5": True, "bass": 34, "touch": {}, "sound_ms": [1000] * 12}
    info = {"kind": "chord", "name": "Gb6/9/Bb", "root": {"letter": 4, "acc": -1}, "suffix": "6/9",
            "bass": {"letter": 6, "acc": -1}, "upper": None, "pcNames": [], "cost": 3.0}
    w["info"] = info
    w.update({"heard_ms": 800, "merged": 1, "start_ms": 0, "end_ms": 800, "share": [0.0] * 12, "bass_share": 1.0,
              "figure": [[34, 800]], "detect_notes": [], "live": {"events": 0, "names": []},
              "line": {"notes": []}, "implied_root": None})
    w["touch"] = {"distinct_notes": 4, "max_polyphony": 4, "lowest": 34, "highest": 70, "spread": 36, "register": 50,
                  "onsets": 4, "vel_mean": 50, "vel_min": 50, "vel_max": 50, "pedal_share": 1.0}
    area = {"key": "Eb major", "tonic": 3, "mode": "major"}
    row = pr._row(0, w, area, area, None)
    assert row["label"] == "Gb6/9(no5)/Bb", row["label"]


@needs_node
def test_days_of_held_sound_cost_what_the_playing_costs(tmp_path, capsys):
    """A chord held 6.9 days, and a pedal left down for 6.9 days with one note an hour: every overview verb stays fast,
    and the brief says nothing was struck while notes kept sounding."""
    import time
    root = tmp_path / "perf"
    now = datetime.now().astimezone()
    held = [{"t_ms": 0, "kind": "on", "note": m, "vel": 60} for m in (48, 60, 64, 67)]
    held += [e for m in (48, 60, 64, 67) for e in ({"t_ms": 596_000_000, "kind": "off", "note": m},
                                                    {"t_ms": 596_000_000, "kind": "sound_end", "note": m, "by": "release"})]
    a = _store(root, "20260105-100000-0000000a", held, now - timedelta(days=7))
    pedal = [{"t_ms": 0, "kind": "pedal", "down": True, "value": 127}]
    for h in range(165):
        pedal += [{"t_ms": h * 3_600_000, "kind": "on", "note": 60 + h % 5, "vel": 50},
                  {"t_ms": h * 3_600_000 + 100, "kind": "off", "note": 60 + h % 5}]
    end = 165 * 3_600_000
    pedal += [{"t_ms": end, "kind": "pedal", "down": False, "value": 0}]
    pedal += [{"t_ms": end, "kind": "sound_end", "note": 60 + k, "by": "pedal"} for k in range(5)]
    b = _store(root, "20260106-100000-0000000b", pedal, now - timedelta(days=6))
    started = time.monotonic()
    assert _run(capsys, "sessions", "--root", root)[0] == 0
    assert _run(capsys, "history", "--days", 30, "--root", root)[0] == 0
    code, out, _ = _run(capsys, "brief", b, "--root", root)
    assert code == 0 and "nothing was struck for" in out and "while notes kept sounding" in out, out
    code, out, _ = _run(capsys, "brief", a, "--root", root)
    assert code == 0 and "Home key: C major" in out and "while notes kept sounding" in out, out
    assert time.monotonic() - started < 30
    doc = pr.analyze(pedal)
    assert len(doc["sections"]) == 165 and all(s["end_ms"] - s["start_ms"] <= pr.SECTION_IDLE_MS for s in doc["sections"])


def test_outside_groups_leave_out_only_the_times_that_ride_a_bass_line():
    def row(at, line):
        return {"analysed_as": "Bm7", "label": "Bm7(no5)", "kind": "chord", "analysed_from": "detect", "pcs": ["B", "D", "A"],
                "class": "modal", "class_detail": "F Lydian colour (#4)", "key": "F major", "number": "#4m7",
                "at": at, "start_ms": pr.parse_clock(at), "seconds": 1.0, "on_bass_line": line, "root": "B",
                "bass": {"note": "B2"}, "light_notes": []}
    doc = {"notes": 10, "home_key": "F major", "windows": [row("0:50", None), row("1:19", "1:15"), row("2:40", None)]}
    groups = pr.borrowed_data(doc)["groups"]
    by = {bool(g["on_bass_line"]): g for g in groups}
    assert len(groups) == 2 and by[False]["times"] == ["0:50", "2:40"] and by[False]["seconds"] == 2.0, groups
    assert by[True]["times"] == ["1:19"] and by[True]["on_bass_line"] == "1:15"
