"""The jam contracts (phase J0): the card, def, run, event-line and ack validators, and the tempo map's two twins.

Every fixture under tests/fixtures/jam is accepted; malformed objects are refused with the offending field named; the
Python tempo map agrees with tests/fixtures/jam/tempomap_cases.json to 0.001 ms, and so does its JS twin
(tests/jam_tempomap.test.mjs, run here when node is present). All data is synthetic: nothing reads Daniel's practice log.
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal.jam import API, schemas, tempomap  # noqa: E402
from arsenal.jam.schemas import (JamSchemaError, card_settings, chord_count, line_beats, pair_problems,  # noqa: E402
                                 validate_ack, validate_card, validate_def, validate_run, validate_run_event,
                                 validate_seed, validate_seed_moments, wording_problems)
from arsenal.performance import PerformanceStore, validate_events  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "jam"
RUN_DIR = FIX / "run_loop_l1"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is needed to run tempomap.js")


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def run_lines():
    raw = (RUN_DIR / "events.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


CARD_FILES = sorted(p.name for p in FIX.glob("card_*.json"))
DEF_FILES = sorted(p.name for p in FIX.glob("def_*.json"))


# ================================================================================================ fixtures accepted
def test_fixture_set_is_there():
    assert len(CARD_FILES) >= 5 and len(DEF_FILES) >= 5
    assert (RUN_DIR / "run.json").is_file() and (RUN_DIR / "expected.json").is_file()
    assert API["card"] == schemas.CARD_API == "arsenal.jam.card/v0"


@pytest.mark.parametrize("name", CARD_FILES)
def test_card_fixtures_validate(name):
    card = load(name)
    before = copy.deepcopy(card)
    assert validate_card(card, stored=True) == card
    assert validate_card(card) == card
    assert card == before
    assert wording_problems(card) == []


def test_card_fixtures_cover_the_shapes_later_phases_need():
    cards = {name: load(name) for name in CARD_FILES}
    everything = list(cards.values())
    assert any(c.get("landing") for c in everything)
    assert any(c.get("pair") for c in everything)
    assert any(c["kind"] == "concept" and "chords" not in c and c["variants"] for c in everything)
    assert any(ch.get("n") is None and ch.get("notes") for c in everything for ch in c.get("chords", []))
    assert {c["source"]["kind"] for c in everything} >= {"seed", "kept", "saved-live", "claude", "edit"}
    assert pair_problems(everything) == []


@pytest.mark.parametrize("name", DEF_FILES)
def test_def_fixtures_validate(name):
    d = load(name)
    assert validate_def(d) == d
    for slot in d["slots"]:
        # every sounding note of every voicing is a chord tone or the bass (the fixture's own consistency)
        for notes in slot["voicings"].values():
            assert {n % 12 for n in notes} <= set(slot["chord_pcs"]), (name, slot["i"])


def test_def_fixtures_cover_sections_rests_exact_notes_and_no_card():
    defs = [load(name) for name in DEF_FILES]
    assert any(len(d["sections"]) > 1 for d in defs)
    assert any(d["card"] is None for d in defs)
    assert any(any(s["upper_same"] for s in d["slots"]) for d in defs)
    assert any(d["beats_per_bar"] == 3 for d in defs)
    assert any(d.get("landing") for d in defs)
    rests = [d for d in defs if any(a["at_beat"] + a["beats"] < b["at_beat"] for a, b in zip(d["slots"], d["slots"][1:]))]
    assert rests


def test_lament_def_keeps_its_upper_voices_with_f():
    d = load("def_lament_bass.json")
    uppers = {tuple(s["voicings"]["full"][1:]) for s in d["slots"]}
    assert len(uppers) == 1 and 65 in next(iter(uppers))          # F4 stays in the shared shape
    assert [s["voicings"]["bass"][0] for s in d["slots"]] == [46, 44, 42, 41]


def test_run_fixture_validates():
    run = load("run_loop_l1/run.json")
    assert validate_run(run) == run
    assert run["card_snapshot"] == load("card_lydian_four.json")


def test_run_events_validate_and_agree_with_run_json():
    run = load("run_loop_l1/run.json")
    lines = run_lines()
    for line in lines:
        assert validate_run_event(line) == line
    assert [line["seq"] for line in lines] == list(range(len(lines)))
    assert lines[0]["kind"] == "start" and lines[0]["def"] == load("def_lydian_four.json")
    changes = [line for line in lines if line["kind"] == "change"]
    assert changes[-1]["segments"] == run["segments"]
    stop = next(line for line in lines if line["kind"] == "stop")
    assert (stop["reason"], stop["effective_bar"], stop["version"]) == (run["stop_reason"], run["stop_bar"],
                                                                        run["last_version"])
    assert stop["epoch_ms"] == run["stopped_epoch_ms"]
    common = set(schemas.EVENT_COMMON_KEYS)
    for line in lines:
        if line["kind"] == "ack":
            ack = {k: v for k, v in line.items() if k not in common}
            assert validate_ack(ack) == ack


def test_run_session_fixture_is_a_performance_store_session():
    expected = load("run_loop_l1/expected.json")
    store = PerformanceStore(RUN_DIR / expected["session_root"])
    info = store.info(expected["session"])
    events = store.events(expected["session"])
    validate_events(events)
    assert info["event_count"] == len(events)
    ack = next(line for line in run_lines() if line["kind"] == "ack")
    assert info["meta"]["page_id"] == ack["page_id"]
    assert info["meta"]["t0_perf_ms"] == ack["log"]["t0_perf_ms"]
    assert ack["log"]["session"] == expected["session"]


def test_run_expected_numbers_follow_the_tempo_map():
    run = load("run_loop_l1/run.json")
    expected = load("run_loop_l1/expected.json")
    d = load("def_lydian_four.json")
    segs, m = run["segments"], run["beats_per_bar"]
    ack = next(line for line in run_lines() if line["kind"] == "ack" and line["bar"] == 0)
    anchor = {"bar_epoch_ms": ack["bar_epoch_ms"], "perf_ms": ack["perf_ms"], "t0_perf_ms": ack["log"]["t0_perf_ms"]}
    assert tempomap.session_t_ms(segs, m, 0, 0, anchor) == pytest.approx(expected["alignment"]["bar0_t_ms"], abs=1e-3)
    for row in expected["bars"]:
        assert tempomap.t_epoch(segs, m, row["bar"]) == pytest.approx(row["epoch_ms"], abs=1e-3)
        assert tempomap.session_t_ms(segs, m, row["bar"], 0, anchor) == pytest.approx(row["t_ms"], abs=1e-3)
        assert tempomap.pass_of(segs, m, row["bar"], d) == row["pass"]
    open_epoch = expected["clock"]["open_client_epoch_ms"]
    for note in expected["notes"]:
        pos = tempomap.position(segs, m, open_epoch + note["t_ms"], d)
        assert (pos["bar"], pos["pass"], pos["slot"]) == (note["bar"], note["pass"], note["slot"])
        assert pos["beat"] == pytest.approx(note["beat"], abs=1e-6)
    for which in ("tempo", "stop"):
        land = expected["landing"][which]
        lines = segs if which == "stop" else segs[:1]
        got = tempomap.next_line(lines, m, land["received_epoch_ms"], land["at"], d)
        assert got["bar"] == land["bar"]


def test_data_73_worked_example_and_a1_tempo_change_by_hand():
    # DATA 7.3: bar 0 at 8123456.2 - 8101234.0 = 22222.2 ms; bar 8 at 66 bpm is 22222.2 + 8 * 4 * 60000 / 66
    seg = tempomap.first_segment(1789365129812.0, 66, count_in=0)
    anchor = {"bar_epoch_ms": seg["epoch_ms"], "perf_ms": 8123456.2, "t0_perf_ms": 8101234.0}
    assert tempomap.session_t_ms([seg], 4, 0, 0, anchor) == pytest.approx(22222.2, abs=1e-6)
    assert tempomap.session_t_ms([seg], 4, 8, 0, anchor) == pytest.approx(51313.1, abs=0.05)
    # A1(e): 72 bpm with a one-bar count-in, 80 bpm from bar 40: the bar-40 downbeat is 41 bars of 72 after the start
    segs = tempomap.add_segment([tempomap.first_segment(0.0, 72, count_in=1)], 4, 40, bpm=80)
    assert segs[1]["epoch_ms"] == pytest.approx(41 * 4 * 60000 / 72, abs=1e-9)
    assert tempomap.t_epoch(segs, 4, 41) - tempomap.t_epoch(segs, 4, 40) == pytest.approx(3000.0, abs=1e-9)


# ============================================================================================ tempo map (A2, Python)
TEMPO = load("tempomap_cases.json")
INT_KEYS = {"bar", "pass", "slot", "def_version", "from_bar", "def_from_bar"}
BEAT_KEYS = {"beat", "cycle_beat", "at_beat"}


def _differ(got, want, key, op, path=""):
    where = path or "(value)"
    if want is None or isinstance(want, (bool, str)):
        return None if got == want and type(got) is type(want) else f"{where}: got {got!r} want {want!r}"
    if isinstance(want, (int, float)):
        if isinstance(got, bool) or not isinstance(got, (int, float)):
            return f"{where}: got {got!r} want {want!r}"
        if key in INT_KEYS or (key is None and op in ("pass_of", "slot_at")):
            return None if got == want else f"{where}: got {got!r} want {want!r}"
        tol = TEMPO["tolerance_beats"] if key in BEAT_KEYS or (key is None and op == "cycle_beat") else TEMPO["tolerance_ms"]
        return None if abs(got - want) <= tol else f"{where}: got {got!r} want {want!r} (|d| {abs(got - want)})"
    if isinstance(want, list):
        if not isinstance(got, list) or len(got) != len(want):
            return f"{where}: got {got!r} want {want!r}"
        for i, (g, w) in enumerate(zip(got, want)):
            d = _differ(g, w, key, op, f"{path}[{i}]")
            if d:
                return d
        return None
    if not isinstance(got, dict) or sorted(got) != sorted(want):
        return f"{where}: got {got!r} want {want!r}"
    for k in want:
        d = _differ(got[k], want[k], k, op, f"{path}.{k}" if path else k)
        if d:
            return d
    return None


def _defs_for(case):
    args = case.get("args", {})
    if "defs" in args and args["defs"] is None:
        return None
    mp = TEMPO["maps"].get(case.get("map"))
    if mp is None:
        return None
    if isinstance(mp["defs"], str):
        return TEMPO["defs"][mp["defs"]]
    return {int(v): TEMPO["defs"][name] for v, name in mp["defs"].items()}


def _run_case(case):
    a = case.get("args", {})
    mp = TEMPO["maps"].get(case.get("map")) or {}
    segs, m = mp.get("segments"), mp.get("beats_per_bar")
    defs = _defs_for(case)
    op = case["op"]
    if op == "t_epoch":
        return tempomap.t_epoch(segs, m, a["bar"], a.get("beat", 0))
    if op == "bar_at":
        return tempomap.bar_at(segs, m, a["epoch_ms"])
    if op == "pass_of":
        return tempomap.pass_of(segs, m, a["bar"], defs)
    if op == "cycle_beat":
        return tempomap.cycle_beat(segs, m, a["bar"], a.get("beat", 0), defs)
    if op == "slot_at":
        return tempomap.slot_at(TEMPO["defs"][a["def"]]["slots"], a["cycle_beat"])
    if op == "position":
        return tempomap.position(segs, m, a["epoch_ms"], defs)
    if op == "first_segment":
        return tempomap.first_segment(a["start_epoch_ms"], a["bpm"], a["count_in"], a["def_version"])
    if op == "add_segment":
        out = segs
        for ch in a["changes"]:
            out = tempomap.add_segment(out, m, ch["bar"], ch.get("bpm"), ch.get("def_version"), ch.get("def_from_bar"))
        return out
    if op == "next_line":
        return tempomap.next_line(segs, m, a["received_epoch_ms"], a["at"], defs, a.get("lead_ms", tempomap.CHANGE_LEAD_MS))
    if op == "handoff_epoch":
        return tempomap.handoff_epoch(segs, m, a["bar"], a.get("margin_ms", tempomap.HANDOFF_MARGIN_MS))
    if op == "session_t_ms":
        return tempomap.session_t_ms(segs, m, a["bar"], a.get("beat", 0), a["anchor"])
    if op == "median_offset":
        return tempomap.median_offset(a["pairs"])
    if op == "beat_ms":
        return tempomap.beat_ms(a["bpm"])
    if op == "bar_ms":
        return tempomap.bar_ms(a["bpm"], a["beats_per_bar"])
    raise AssertionError(f"unknown op {op}")


def test_tempomap_fixture_size_ops_and_constants():
    cases = TEMPO["cases"]
    assert TEMPO["api"] == API["tempomap_cases"]
    assert len(cases) >= 40
    assert len({c["id"] for c in cases}) == len(cases)
    assert {c["op"] for c in cases} >= {"t_epoch", "bar_at", "pass_of", "cycle_beat", "slot_at", "position",
                                        "add_segment", "next_line", "handoff_epoch", "session_t_ms"}
    assert len(TEMPO["maps"]["many"]["segments"]) >= 6
    for name, value in TEMPO["constants"].items():
        assert getattr(tempomap, name) == value, name


@pytest.mark.parametrize("case", TEMPO["cases"], ids=lambda c: c["id"])
def test_tempomap_python_agrees_with_fixture(case):
    if case.get("raises"):
        with pytest.raises(tempomap.TempoMapError):
            _run_case(case)
        return
    diff = _differ(_run_case(case), case["expect"], None, case["op"])
    assert diff is None, diff


def test_add_segment_leaves_its_input_alone():
    segs = TEMPO["maps"]["steady66"]["segments"]
    before = copy.deepcopy(segs)
    tempomap.add_segment(segs, 4, 8, bpm=72)
    assert segs == before


@needs_node
def test_tempomap_js_twin_agrees_with_fixture():
    res = subprocess.run([NODE, str(ROOT / "tests" / "jam_tempomap.test.mjs")], capture_output=True, text=True,
                         cwd=str(ROOT), timeout=60)
    assert res.returncode == 0, res.stdout + res.stderr
    assert " 0 failed" in res.stdout


# ============================================================================================== malformed, refused
def _lydian():
    return load("card_lydian_four.json")


def _one():
    return load("card_one_note_apart.json")


def _lament():
    return load("def_lament_bass.json")


def _run():
    return load("run_loop_l1/run.json")


def _ack():
    return {"page_id": "p-0a1b", "role": "owner", "version": 1, "bar": 0, "bar_epoch_ms": 1893456023636.36,
            "perf_ms": 3623636.11, "perf_offset_ms": 1893452400000.25,
            "log": {"local": "lg-0a1b", "session": "20300101-000012-5e55a0f1", "t0_perf_ms": 3611999.75}}


def _line(kind):
    return next(line for line in run_lines() if line["kind"] == kind)


def _set(obj, path, value):
    *head, last = path
    for p in head:
        obj = obj[p]
    obj[last] = value


def _del(obj, path):
    *head, last = path
    for p in head:
        obj = obj[p]
    del obj[last]


def _seed(cards):
    out = []
    for c in cards:
        c = copy.deepcopy(c)
        for key in ("rev", "page_reads", "created_at", "updated_at", "updated_by", "moments"):
            c.pop(key, None)
        c["source"] = {"kind": "seed", "seed_version": 1}
        out.append(c)
    return {"api": "arsenal.jam.seed/v0", "seed_version": 1, "cards": out}


def _stored_card(card):
    return validate_card(card, stored=True)


# (id, validator, make the base object, mutate it, the field the refusal must name)
MALFORMED = [
    ("card-missing-title", _stored_card, _lydian, lambda c: _del(c, ["title"]), "title"),
    ("card-long-meaning", _stored_card, _lydian, lambda c: _set(c, ["meaning"], "x" * 121), "meaning"),
    ("card-bad-id", _stored_card, _lydian, lambda c: _set(c, ["id"], "Lydian_Four"), "id"),
    ("card-bad-group", _stored_card, _lydian, lambda c: _set(c, ["group"], "tonight"), "group"),
    ("card-bad-key", _stored_card, _lydian, lambda c: _set(c, ["key"], "H major"), "key"),
    ("card-beats-off-grid", _stored_card, _lydian, lambda c: _set(c, ["chords", 1, "beats"], 3.3), "chords[1].beats"),
    ("card-bad-number", _stored_card, _lydian, lambda c: _set(c, ["chords", 0, "n"], "8maj7"), "chords[0].n"),
    ("card-upper-same-first", _stored_card, _lydian, lambda c: _set(c, ["chords", 0, "upper"], "same"),
     "chords[0].upper"),
    ("card-bad-key-item", _stored_card, _lydian, lambda c: c["chords"].append({"key": "6 Major"}), "chords[2].key"),
    ("card-bpm-too-fast", _stored_card, _lydian, lambda c: _set(c, ["tempo", "bpm"], 300), "tempo.bpm"),
    ("card-meter-9", _stored_card, _lydian, lambda c: _set(c, ["tempo", "beats_per_bar"], 9), "tempo.beats_per_bar"),
    ("card-bars-too-few", _stored_card, _lydian, lambda c: _set(c, ["bars"], 1), "bars"),
    ("card-check-slot-past-line", _stored_card, _lydian, lambda c: _set(c, ["checks", 0, "slot"], 2), "checks[0].slot"),
    ("card-check-bad-role", _stored_card, _lydian, lambda c: _set(c, ["checks", 0, "role"], "#12"), "checks[0].role"),
    ("card-unknown-field", _stored_card, _lydian, lambda c: _set(c, ["display"], {"in_recording": True}), "display"),
    ("card-landing-without-pull", _stored_card, _lydian, lambda c: _del(c, ["landing", "pull"]), "landing.pull"),
    ("card-landing-slot-past-line", _stored_card, _lydian, lambda c: _set(c, ["landing", "slot"], 5), "landing.slot"),
    ("card-pair-with-itself", _stored_card, _lydian, lambda c: _set(c, ["pair"], {"role": "question",
                                                                                  "with": "lydian-four"}), "pair.with"),
    ("card-pair-bad-role", _stored_card, _lydian, lambda c: _set(c, ["pair"], {"role": "call", "with": "x"}),
     "pair.role"),
    ("card-moment-bad-session", _stored_card, _lydian,
     lambda c: _set(c, ["moments"], [{"session": "S4", "at": "0:00", "until": None, "label": "x"}]),
     "moments[0].session"),
    ("card-stored-without-rev", _stored_card, _lydian, lambda c: _del(c, ["rev"]), "rev"),
    ("card-note-off-keyboard", _stored_card, _lydian, lambda c: _set(c, ["chords", 0, "notes"], [20, 60]),
     "chords[0].notes[0]"),
    ("card-bad-groove", _stored_card, _lydian, lambda c: _set(c, ["groove"], "swing"), "groove"),
    ("card-bad-author", _stored_card, _lydian, lambda c: _set(c, ["created_by"], "vandor"), "created_by"),
    ("card-too-big", _stored_card, _lydian, lambda c: _set(c, ["style"], "x" * 70000), "card"),
    ("card-variant-id-g", _stored_card, _one, lambda c: _set(c, ["variants", 0, "id"], "g"), "variants[0].id"),
    ("card-concept-check-unknown-variant", _stored_card, _one,
     lambda c: _set(c, ["checks"], [{"id": "x", "variant": "e", "slot": 0, "role": "7", "want": "present",
                                     "say": "you played G"}]), "checks[0].variant"),
    ("card-page-read-bad-match", _stored_card, _lydian, lambda c: _set(c, ["page_reads", 0, "match"], "close"),
     "page_reads[0].match"),
    ("def-overlapping-slots", validate_def, _lament, lambda d: _set(d, ["slots", 1, "at_beat"], 2), "slots[1].at_beat"),
    ("def-cycle-not-whole-bars", validate_def, _lament, lambda d: _set(d, ["cycle_beats"], 18), "cycle_beats"),
    ("def-full-above-a4", validate_def, _lament, lambda d: d["slots"][0]["voicings"]["full"].append(70),
     "slots[0].voicings.full"),
    ("def-chord-pcs-without-bass", validate_def, _lament, lambda d: d["slots"][2]["chord_pcs"].remove(6),
     "slots[2].chord_pcs"),
    ("def-upper-same-moved", validate_def, _lament, lambda d: _set(d, ["slots", 1, "voicings", "full", 1], 57),
     "slots[1].voicings.full"),
    ("def-first-role-not-bass", validate_def, _lament, lambda d: _set(d, ["slots", 0, "roles", "full", 0], "root"),
     "slots[0].roles.full[0]"),
    ("def-slot-key-not-section", validate_def, _lament, lambda d: _set(d, ["slots", 3, "key"], "Eb major"),
     "slots[3].key"),
    ("def-bass-pc-not-in-chord", validate_def, _lament, lambda d: _set(d, ["slots", 0, "bass_pc"], 9),
     "slots[0].chord_pcs"),
    ("def-bass-below-e1", validate_def, _lament, lambda d: _set(d, ["slots", 0, "voicings", "bass"], [22]),
     "slots[0].voicings.bass[0]"),
    ("def-bad-tone-role", validate_def, _lament, lambda d: _set(d, ["slots", 0, "tones_pc", "fourth"], 3),
     "slots[0].tones_pc.fourth"),
    ("run-segment-off-the-map", validate_run, _run, lambda r: _set(r, ["segments", 1, "epoch_ms"],
                                                                   r["segments"][1]["epoch_ms"] + 5),
     "segments[1].epoch_ms"),
    ("run-first-segment-not-count-in", validate_run, _run, lambda r: _set(r, ["segments", 0, "from_bar"], 0),
     "segments[0].from_bar"),
    ("run-bad-stop-reason", validate_run, _run, lambda r: _set(r, ["stop_reason"], "bored"), "stop_reason"),
    ("run-running-but-closed", validate_run, _run, lambda r: _set(r, ["state"], "running"), "closed"),
    ("run-try-backing-on-loop", validate_run, _run, lambda r: _set(r, ["settings", 0, "try_backing"], "bass"),
     "settings[0].try_backing"),
    ("run-snapshot-without-title", validate_run, _run, lambda r: _del(r, ["card_snapshot", "title"]),
     "card_snapshot.title"),
    ("run-bar0-off-the-map", validate_run, _run, lambda r: _set(r, ["bar0_epoch_ms"], r["bar0_epoch_ms"] + 1),
     "bar0_epoch_ms"),
    ("run-ramp-is-v2", validate_run, _run, lambda r: _set(r, ["segments", 1, "to_bpm"], 90), "segments[1].to_bpm"),
    ("ack-bad-role", validate_ack, _ack, lambda a: _set(a, ["role"], "listener"), "role"),
    ("ack-bad-log-session", validate_ack, _ack, lambda a: _set(a, ["log", "session"], "S1"), "log.session"),
    ("ack-missing-perf-ms", validate_ack, _ack, lambda a: _del(a, ["perf_ms"]), "perf_ms"),
    ("ack-bad-stopped", validate_ack, _ack, lambda a: _set(a, ["stopped"], "tired"), "stopped"),
    ("event-change-version-1", validate_run_event, lambda: _line("change"), lambda e: _set(e, ["version"], 1),
     "version"),
    ("event-start-def-velocity-0", validate_run_event, lambda: _line("start"),
     lambda e: _set(e, ["def", "slots", 0, "vel"], 0), "def.slots[0].vel"),
    ("event-unknown-kind", validate_run_event, lambda: _line("mark"), lambda e: _set(e, ["kind"], "pause"), "kind"),
    ("seed-card-with-moments", validate_seed, lambda: _seed([_lydian()]),
     lambda s: _set(s, ["cards", 0, "moments"], [{"session": "20300101-000012-5e55a0f1", "at": "0:10", "until": None,
                                                  "label": "x"}]), "cards[0].moments"),
    ("seed-pair-missing-partner", validate_seed,
     lambda: _seed([_lydian(), load("card_pair_question.json"), load("card_pair_answer.json")]),
     lambda s: s["cards"].pop(2), "cards[1].pair"),
]


def test_at_least_24_malformed_cases():
    assert len(MALFORMED) >= 24
    assert len({m[0] for m in MALFORMED}) == len(MALFORMED)


@pytest.mark.parametrize("case", MALFORMED, ids=lambda m: m[0])
def test_malformed_is_refused_with_the_field_named(case):
    _, validator, make, mutate, field = case
    base = make()
    validator(copy.deepcopy(base))          # the base itself is accepted
    mutate(base)
    with pytest.raises(JamSchemaError) as info:
        validator(base)
    assert info.value.field == field, str(info.value)
    assert str(info.value).startswith(field), str(info.value)


# ================================================================================================= helpers and edges
def test_ack_defaults_are_filled_and_input_untouched():
    ack = _ack()
    ack.pop("log")
    before = copy.deepcopy(ack)
    out = validate_ack(ack)
    assert ack == before
    assert (out["output_latency_ms"], out["log"], out["stopped"], out["late_dropped"]) == (None, None, None, 0)


def test_pending_run_has_no_epochs_and_a_play_run_no_count_in():
    run = _run()
    run.update(state="pending", closed=False, stop_reason=None, stopped_epoch_ms=None, stop_bar=None,
               start_epoch_ms=None, bar0_epoch_ms=None, segments=[], last_version=1)
    run["courtesy"] = {"held_ms": 0, "via": None}
    assert validate_run(run) == run
    run["mode"] = "play"
    with pytest.raises(JamSchemaError) as info:
        validate_run(run)
    assert info.value.field == "count_in_bars"
    run["count_in_bars"] = 0
    validate_run(run)


def test_chord_run_without_card_and_try_run_settings():
    run = _run()
    run.update(card=None, card_snapshot=None, mode="try")
    with pytest.raises(JamSchemaError) as info:
        validate_run(run)
    assert info.value.field == "settings[0].try_backing"
    run["settings"][0]["try_backing"] = "bass"
    assert validate_run(run) == run


def test_card_settings_defaults():
    card = _lydian()
    for key in ("groove", "backing", "tempo", "voicing", "playback", "bars"):
        card.pop(key)
    s = card_settings(card)
    assert s["tempo"] == {"bpm": 66, "beats_per_bar": 4, "feel": "straight"}
    assert (s["groove"], s["backing"], s["bars"], s["cycle_beats"]) == ("ballad", "comp", 2, 8)
    assert s["voicing"] == {"style": "spread", "voice_lead": False, "octave": None}
    assert s["playback"] == {"velocity": 48, "arpeggio_ms": 0, "hold": "legato", "count": None}
    card["tempo"] = {"bpm": 88}
    assert card_settings(card)["groove"] == "pulse"
    card.update(groove="gospel", backing="pad")
    s = card_settings(card)
    assert (s["groove"], s["groove_v1"], s["backing"], s["backing_v1"]) == ("gospel", "ballad", "pad", "comp")


def test_line_helpers_count_slots_and_beats():
    line = [{"n": "1add9", "beats": 4}, {"key": "6 major"}, {"rest": 2}, {"n": "4maj13"}, {"n": "5^6", "beats": 1.5}]
    assert chord_count(line) == 3
    assert line_beats(line) == 11.5


def test_wording_and_pair_helpers():
    card = _lydian()
    card["try"] = "You should keep D on top."
    card["landing"]["pull"] = "D is WRONG here"
    assert wording_problems(card) == [("try", "should"), ("landing.pull", "wrong")]
    q, a = load("card_pair_question.json"), load("card_pair_answer.json")
    assert pair_problems([q, a]) == []
    a["pair"]["role"] = "question"
    assert pair_problems([q, a])[0][0] == "float-question"
    assert pair_problems([q])[0] == ("float-question", "names 'float-answer', which is not in the deck")


def test_seed_validates_and_keeps_moments_out():
    doc = _seed([_lydian(), load("card_pair_question.json"), load("card_pair_answer.json")])
    assert validate_seed(doc) == doc
    moments = {"api": "arsenal.jam.seed.moments/v0",
               "cards": {"lydian-four": {"moments": [{"session": "20300101-000012-5e55a0f1", "at": "0:00",
                                                      "until": "0:22", "label": "synthetic"}],
                                         "replay": {"session": "20300101-000012-5e55a0f1", "at": "0:02",
                                                    "seconds": 18, "speed": 1}}}}
    assert validate_seed_moments(moments) == moments
    moments["cards"]["lydian-four"]["replay"]["seconds"] = 0
    with pytest.raises(JamSchemaError) as info:
        validate_seed_moments(moments)
    assert info.value.field == "cards.lydian-four.replay.seconds"


def test_concept_card_may_leave_chords_out_but_a_loop_may_not():
    one = _one()
    assert "chords" not in one and validate_card(one, stored=True)
    loop = _lydian()
    loop.pop("chords")
    loop.pop("bars")
    loop.pop("checks")
    loop.pop("landing")
    with pytest.raises(JamSchemaError) as info:
        validate_card(loop)
    assert info.value.field == "chords"
