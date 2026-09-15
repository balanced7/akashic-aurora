"""J3, the store half: the deck on disk, the resolver (A4's transposition half), the run store and the alignment ladder.

Every card, session and run here is synthetic. The seed-like cards carry only the section 12 chord lines of the build
spec (public text), never practice data. Tests that voice chords need node (the voicing bridge)."""
import copy
import json
import re
import shutil
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import nashville  # noqa: E402
from arsenal.jam import align as A  # noqa: E402
from arsenal.jam import schemas as S  # noqa: E402
from arsenal.jam import tempomap as T  # noqa: E402
from arsenal.jam.cards import DeckError, DeckStore, merge_patch  # noqa: E402
from arsenal.jam.resolve import (STUB_WARNING, Resolver, ResolveError, chord_facts, degree_key,  # noqa: E402
                                 parse_line, parse_notes, run_bridge, shift_notes, shift_of, suffix_tones,
                                 transpose_key)
from arsenal.jam.runs import RunError, RunStore  # noqa: E402
from arsenal.performance import PerformanceStore  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "jam"
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="the voicing bridge needs node")
SESSION = "20300101-000012-5e55a0f1"
MAJOR_KEYS = [f"{n} major" for n in nashville.MAJOR_KEY_NAMES]
MINOR_KEYS = [f"{n} minor" for n in nashville.MINOR_KEY_NAMES]


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def card(cid, key, line=None, **kw):
    c = {"api": "arsenal.jam.card/v0", "id": cid, "title": cid.replace("-", " "), "meaning": "a synthetic card",
         "group": "moves", "kind": "loop", "key": key, "explanation": "x", "why": "x", "try": "x",
         "created_by": "claude"}
    if line is not None:
        c["chords"] = parse_line(line) if isinstance(line, str) else line
    c.update(kw)
    return c


def exact(line, notes_by_slot, **per_slot):
    """A chord line with exact notes on some slots (slots counted from 0 over chord items)."""
    items = parse_line(line)
    chords = [it for it in items if "key" not in it and "rest" not in it]
    for i, text in notes_by_slot.items():
        chords[i]["notes"] = parse_notes(text)
    for field, values in per_slot.items():
        for i, value in values.items():
            chords[i][field] = value
    return items


# ============================================================================================ the deck
@pytest.fixture()
def deck(tmp_path):
    return DeckStore(tmp_path / "jam")


def test_create_writes_the_server_fields_and_refuses_a_second_card_with_the_id(deck):
    c = load("card_lydian_four.json")
    c.update(rev=7, source={"kind": "seed", "seed_version": 1}, updated_by="daniel")
    out = deck.create(c, "claude")
    stored = deck.get("lydian-four")
    assert out["rev"] == 1 and stored["rev"] == 1 and stored["source"] == {"kind": "claude"}
    assert stored["updated_by"] == "claude" and S.validate_card(stored, stored=True)
    assert deck.deck() == {"api": "arsenal.jam.deck/v0", "rev": 1, "order": ["lydian-four"]}
    with pytest.raises(DeckError) as err:
        deck.create(c, "claude")
    assert err.value.status == 409 and err.value.extra == {"rev": 1}
    assert not list((deck.root / "deck").rglob("*.tmp"))


def test_a_malformed_card_is_refused_naming_the_field_and_nothing_is_written(deck):
    with pytest.raises(DeckError) as err:
        deck.create(card("bad-beats", "Eb major", [{"n": "1maj9", "beats": 3.3}]))
    assert err.value.status == 400 and err.value.field == "chords[0].beats"
    assert not deck.exists("bad-beats") and deck.deck()["rev"] == 0


def test_update_is_a_merge_patch_against_the_rev_it_was_made_on(deck):
    deck.create(card("vamp", "D minor", "1m11:4 | 4^13:4", tags=["dorian"], listen_for="B natural"))
    for patch, if_rev, status, field in (({"title": "x"}, None, 400, "if_rev"), ({"title": "x"}, 3, 409, None),
                                         ({"id": "other"}, 1, 400, "patch.id"),
                                         ({"source": {"kind": "seed"}}, 1, 400, "patch.source")):
        with pytest.raises(DeckError) as err:
            deck.update("vamp", patch, if_rev)
        assert (err.value.status, err.value.field) == (status, field)
    out = deck.update("vamp", {"title": "Two-chord vamp", "listen_for": None, "tempo": {"bpm": 88}}, 1, "daniel")
    stored = deck.get("vamp")
    assert out["rev"] == 2 and stored["title"] == "Two-chord vamp" and "listen_for" not in stored
    assert stored["tempo"] == {"bpm": 88} and stored["updated_by"] == "daniel" and deck.deck()["rev"] == 2
    assert merge_patch({"a": {"b": 1, "c": 2}}, {"a": {"b": None, "d": 3}}) == {"a": {"c": 2, "d": 3}}


def test_editing_a_seed_card_marks_it_edited(deck):
    deck.create(card("sus-five", "Eb major", "5^7sus4/1:16"), source={"kind": "seed", "seed_version": 1})
    deck.update("sus-five", {"title": "held"}, 1, "daniel")
    assert deck.get("sus-five")["source"] == {"kind": "edit", "from_seed_version": 1}


def test_delete_moves_to_the_trash_and_restore_brings_the_newest_back(deck):
    deck.create(card("a-card", "Eb major", "1maj9:4"))
    deck.create(card("b-card", "Eb major", "4maj9:4"))
    with pytest.raises(DeckError) as err:
        deck.delete("a-card", 2)
    assert err.value.status == 409 and err.value.extra["rev"] == 1
    out = deck.delete("a-card", 1)
    assert re.fullmatch(r"trash/a-card\.rev1\.\d{8}T\d{9}Z\.json", out["trashed"])
    assert not deck.exists("a-card") and deck.deck()["order"] == ["b-card"]
    assert [t["id"] for t in deck.trash()] == ["a-card"]
    with pytest.raises(DeckError) as err:
        deck.restore("nothing-here")
    assert err.value.status == 404
    back = deck.restore("a-card", "daniel")
    assert back["rev"] == 2 and deck.get("a-card")["rev"] == 2 and deck.trash() == []
    assert deck.deck()["order"] == ["b-card", "a-card"]
    deck.delete("a-card", 2)
    deck.create(card("a-card", "Eb major", "1maj9:4"))
    with pytest.raises(DeckError) as err:
        deck.restore("a-card")
    assert err.value.status == 409


def test_find_takes_an_id_or_a_unique_prefix(deck):
    for cid in ("lydian-four", "lament-bass", "lament-two"):
        deck.create(card(cid, "Eb major", "1maj9:4"))
    assert deck.find("lydian-four") == "lydian-four" and deck.find("lyd") == "lydian-four"
    for ref, status in (("lament", 400), ("zz", 404)):
        with pytest.raises(DeckError) as err:
            deck.find(ref)
        assert err.value.status == status


def test_order_puts_the_listed_cards_first_and_needs_the_deck_rev(deck):
    for cid in ("a-card", "b-card", "c-card"):
        deck.create(card(cid, "Eb major", "1maj9:4"))
    assert deck.order(["c-card"], 3)["order"] == ["c-card", "a-card", "b-card"]
    assert [c["id"] for c in deck.all()] == ["c-card", "a-card", "b-card"]
    with pytest.raises(DeckError) as err:
        deck.order(["a-card"], 3)
    assert err.value.status == 409 and err.value.extra == {"rev": 4}
    with pytest.raises(DeckError) as err:
        deck.order(["nope"], 4)
    assert (err.value.status, err.value.field) == (400, "order[0]")


def test_keep_copies_into_kept_and_moves_exact_notes_by_the_nearest_interval(deck):
    long_id = "one-note-apart-" + "x" * 33
    notes = [44, 51, 55, 60, 62, 65, 70]
    src = card(long_id, "Eb major", [{"n": "4maj13#11", "beats": 8, "notes": notes, "name": "Abmaj13#11"}],
               pair={"role": "question", "with": "some-answer"}, favorite=True)
    deck.create(src)
    kept = deck.keep(long_id, "daniel", key="A major")["card"]
    assert re.fullmatch(r"k-[a-z0-9-]+-[0-9a-f]{4}", kept["id"]) and len(kept["id"]) <= 48
    assert kept["group"] == "kept" and kept["key"] == "A major" and "pair" not in kept and "favorite" not in kept
    assert kept["source"] == {"kind": "kept", "from": {"id": long_id, "rev": 1}} and kept["updated_by"] == "daniel"
    assert shift_of("Eb major", "A major") == -6
    assert kept["chords"][0]["notes"] == [n - 6 for n in notes] and "name" not in kept["chords"][0]


def test_a_page_capture_becomes_a_kept_chord_card(deck):
    cap = {"notes": [42, 49, 54, 56, 58, 61, 65, 70, 75, 77, 80, 84], "name": "Gb Db Ab Bb F Eb C", "number": None,
           "key": "Db major", "key_conf": "sure", "locked": False, "title": None, "page_id": "p-0a1b",
           "perf_ms": 3753999.75, "log": {"local": "lg-0a1b", "session": SESSION, "t0_perf_ms": 3611999.75}}
    c = deck.template_from_capture(cap, "daniel")["card"]
    assert re.fullmatch(r"t-\d{8}-\d{6}-[0-9a-f]{4}", c["id"]) and c["group"] == "kept" and c["kind"] == "chord"
    assert c["created_by"] == "daniel" and c["key"] == "Db major"
    assert c["chords"] == [{"n": None, "beats": 4, "notes": cap["notes"]}]
    assert c["moments"] == [{"session": SESSION, "at": "2:22", "until": None, "label": "saved from the page"}]
    assert c["source"]["kind"] == "saved-live" and c["source"]["log_t_ms"] == 142000
    assert c["title"].startswith("Gb Db Ab Bb F Eb C, ") and S.validate_card(c, stored=True)
    rooted = deck.template_from_capture(dict(cap, key=None, name="Abmaj9", notes=[44, 55, 60, 63, 70], log=None),
                                        "daniel")["card"]
    assert rooted["key"] == "Ab major" and rooted["source"]["number_from"] == "root"
    assert rooted["chords"][0]["n"] == "1maj9" and "moments" not in rooted
    with pytest.raises(DeckError) as err:
        deck.template_from_capture(dict(cap, notes=list(range(40, 57))), "daniel")
    assert (err.value.status, err.value.field) == (400, "capture.notes")


def test_a_moment_from_the_log_becomes_a_card_saved_by_claude(deck):
    moment = {"session": SESSION, "at_ms": 160000, "until_ms": 169000, "notes": [39, 51, 63, 65, 68, 70],
              "name": "Bb7sus4/Eb", "number": "5^7sus4/1", "key": "Eb major"}
    c = deck.template_from_moment(moment, "claude")["card"]
    assert c["chords"] == [{"n": "5^7sus4/1", "beats": 4, "notes": [39, 51, 63, 65, 68, 70]}]
    assert c["moments"][0] == {"session": SESSION, "at": "2:40", "until": "2:49", "label": "saved from your practice log"}
    assert c["source"]["kind"] == "saved-from-moment" and c["source"]["saved_by"] == "claude"
    assert c["created_by"] == "daniel" and c["updated_by"] == "claude" and c["title"] == "Bb7sus4/Eb, from 2:40"


def _seed_doc():
    cards = []
    for name in ("card_pair_question.json", "card_pair_answer.json"):
        c = load(name)
        for key in ("rev", "page_reads", "created_at", "updated_at", "updated_by"):
            c.pop(key, None)
        c["source"] = {"kind": "seed", "seed_version": 1}
        cards.append(c)
    return {"api": "arsenal.jam.seed/v0", "seed_version": 1, "cards": cards}


def test_seed_installs_merges_moments_and_keeps_what_was_edited(deck):
    moments = deck.root / "seed" / "moments-v1.json"
    moments.parent.mkdir(parents=True)
    moments.write_text(json.dumps({"api": "arsenal.jam.seed.moments/v0", "cards": {"float-question": {
        "moments": [{"session": SESSION, "at": "0:12", "until": None, "label": "a synthetic moment"}]}}}),
        encoding="utf-8")
    doc = _seed_doc()
    dry = deck.seed(doc, dry_run=True)
    assert dry["installed"] == ["float-question", "float-answer"] and not deck.exists("float-question")
    out = deck.seed(doc)
    assert out["installed"] == ["float-question", "float-answer"] and out["moments"] == 1
    q = deck.get("float-question")
    assert q["source"] == {"kind": "seed", "seed_version": 1} and q["moments"][0]["at"] == "0:12" and q["rev"] == 1
    assert deck.seed(doc)["kept"] == ["float-question", "float-answer"]
    deck.update("float-answer", {"title": "The answer, my way"}, 1, "daniel")
    doc2 = copy.deepcopy(doc)
    doc2["cards"][0]["title"] = "The question, reworded"
    doc2["cards"][1]["title"] = "An answer nobody asked for"
    out = deck.seed(doc2, update=True)
    assert out["updated"] == ["float-question"] and out["kept"] == ["float-answer"]
    assert deck.get("float-question")["title"] == "The question, reworded" and deck.get("float-question")["rev"] == 1
    assert deck.get("float-answer")["title"] == "The answer, my way"
    leaky = copy.deepcopy(doc)
    leaky["cards"][0]["moments"] = [{"session": SESSION, "at": "0:12", "until": None, "label": "x"}]
    with pytest.raises(DeckError) as err:
        deck.seed(leaky)
    assert (err.value.status, err.value.field) == (400, "cards[0].moments")


# ============================================================================================ key maths
def test_key_items_are_degrees_of_the_card_key_spelled_by_the_degree():
    assert degree_key("Gb major", "6 major") == "Eb major"
    assert degree_key("Eb minor", "b3 major") == "Gb major"
    assert degree_key("Eb minor", "1 major") == "Eb major"
    assert degree_key("F major", "b7 major") == "Eb major"
    assert degree_key("F major", "b2 major") == "Gb major"
    assert degree_key("B major", "6 major") == "G# major"
    assert transpose_key("D minor", "E minor") == ("E minor", [])
    name, warnings = transpose_key("D minor", "Db major")
    assert name == "C# minor" and "minor" in warnings[0]
    with pytest.raises(ResolveError) as err:
        degree_key("Eb major", "9 major")
    assert err.value.field == "key"


def test_exact_notes_shift_by_the_nearest_interval_and_fold_on_the_keyboard():
    assert [shift_of("Eb major", k) for k in ("Eb major", "E major", "A major", "Bb major", "D major")] == \
        [0, 1, -6, -5, -1]
    assert shift_notes([44, 51, 55], -6) == ([38, 45, 49], None, [])
    assert shift_notes([29, 40], -3) == ([38, 49], "up", [])
    assert shift_notes([90, 105], 1) == ([79, 94], "down", [])


def test_the_chord_line_string_form_and_the_suffix_reader():
    assert parse_line("1maj9:4 | [6 major] | 1add9:4 | rest:2 | 5^7sus4/1") == [
        {"n": "1maj9", "beats": 4}, {"key": "6 major"}, {"n": "1add9", "beats": 4}, {"rest": 2}, {"n": "5^7sus4/1"}]
    assert parse_line("1 4 | 5:2.5") == [{"n": "1"}, {"n": "4"}, {"n": "5", "beats": 2.5}]
    with pytest.raises(ValueError):
        parse_line(" | ")
    assert suffix_tones("m11") == {"root": 0, "third": 3, "fifth": 7, "seventh": 10, "ninth": 2, "eleventh": 5}
    assert suffix_tones("maj7#11") == {"root": 0, "third": 4, "fifth": 7, "seventh": 11, "eleventh": 6}
    assert suffix_tones("7sus4") == {"root": 0, "sus": 5, "fifth": 7, "seventh": 10}
    assert suffix_tones("6/9") == {"root": 0, "third": 4, "fifth": 7, "sixth": 9, "ninth": 2}
    assert suffix_tones("m(add9)") == {"root": 0, "third": 3, "fifth": 7, "ninth": 2}
    assert chord_facts("Bbm11/Gb")["bass_pc"] == 6 and chord_facts("Bbm11/Gb")["root_pc"] == 10


# ============================================================================================ A4, transposition half
def seed_like():
    """The 17 section 12 lines as synthetic cards (their chord lines and exact notes only)."""
    n = parse_notes
    return [
        card("lydian-four", "Eb major", "1maj9:4 | 4maj7#11:4"),
        card("gospel-five-over-four", "Eb major", "4maj9:4 | 5^11/4:4 | 1/3:4 | 1maj9:4",
             variants=[{"id": "b", "chords": parse_line("4maj9:4 | 5^11/4:4 | 3m9:4 | 6m11:4")}]),
        card("one-note-apart", "Eb major", kind="concept", variants=[
            {"id": "a", "chords": [{"n": "4maj13#11", "beats": 8, "notes": n("Ab2 Eb3 G3 C4 D4 F4 Bb4"),
                                    "name": "Abmaj13#11"}]},
            {"id": "b", "chords": [{"n": "5^11/4", "beats": 8, "notes": n("Ab2 Eb3 C4 D4 F4 Bb4")}]},
            {"id": "c", "chords": exact("4maj13#11:4 | 5^11/4:4 | 1/3:8", {0: "Ab2 Eb3 G3 C4 D4 F4 Bb4",
                                                                           1: "Ab2 Eb3 C4 D4 F4 Bb4"})}]),
        card("blooming-chord", "Eb major", exact("4sus2:4 | 4add9:4 | 4maj9:4 | 4maj13#11:8", {
            0: "Ab2 Eb3 Bb3 Eb4", 1: "Ab2 Eb3 Bb3 C4 Eb4", 2: "Ab2 Eb3 G3 Bb3 C4 Eb4",
            3: "Ab2 Eb3 G3 Bb3 C4 Eb4 D5 F5"}, arp_ms={0: 45, 1: 45, 2: 45, 3: 45}), kind="progression"),
        card("half-step-slide", "Eb major", kind="concept", variants=[
            {"id": "a", "chords": exact("2^9/#4:4 | 2m9/4:4 | 4maj7#11:8", {0: "A2 F3 Eb4 G4 C5",
                                                                         1: "Ab2 F3 Eb4 G4 C5"})},
            {"id": "b", "key": "b7 major", "chords": exact("#4m7/6:4 | 4maj7/6:8", {0: "Bb2 F3 G3 Bb3 D4",
                                                                                   1: "Bb2 F3 Gb3 Bb3 Db4"})}]),
        card("lament-bass", "Db major", exact("6m11:4 | 6m11/5:4 | 6m11/4:4 | 6m11/3:4", {
            0: "Bb2 Bb3 Ab4 C5 Db5 Eb5 F5", 1: "Ab2 Bb3 Ab4 C5 Db5 Eb5 F5", 2: "Gb2 Bb3 Ab4 C5 Db5 Eb5 F5",
            3: "F2 Bb3 Ab4 C5 Db5 Eb5 F5"}, upper={1: "same", 2: "same", 3: "same"})),
        card("minor-third-drop", "F major", kind="concept", variants=[
            {"id": "a", "chords": parse_line("1add9:4 | 4maj13:4 | 5^6:4 | [6 major] | 1add9:4 | 4maj13:4 | 1maj9:8")},
            {"id": "b", "key": "b2 major", "chords": parse_line(
                "4maj9:4 | 1maj9:4 | 5sus4:4 | [b7 major] | b3add9/b7:2 | 1add9:6 | 4maj9:4 | 1maj9:8")}]),
        card("borrowed-four-minor", "Eb major", "1maj9:4 | 4add9:4 | 4m(add9):4 | 1maj9:4"),
        card("borrowed-b6-b7-home", "Eb major", "b6maj9:4 | b7maj9:4 | 1maj9:8"),
        card("float-or-pull", "Eb major", kind="concept", variants=[
            {"id": "a", "chords": exact("1maj9:4 | 5^7sus4/1:8 | 1maj9:4", {1: "Eb2 Eb3 Eb4 F4 Ab4 Bb4"})},
            {"id": "b", "chords": parse_line("1maj9:4 | 5^7:8 | 1maj9:4")},
            {"id": "c", "chords": exact("1maj9:4 | 5^7sus4:4 | 5^7:4 | 1maj9:8", {1: "Bb2 F3 Ab3 Eb4",
                                                                                2: "Bb2 F3 Ab3 D4"})}]),
        card("lush-two-five-one", "Eb major", exact("2m9:4 | 5^13:4 | 1maj9:8", {
            0: "F2 Eb3 Ab3 C4 G4", 1: "Bb2 D3 Ab3 C4 G4", 2: "Eb2 D3 G3 Bb3 F4"})),
        card("sunrise-ending", "Eb major",
             "1m11:4 | 1m11:4 | b6maj7#11:4 | 5^7sus4:2 | 5^7:2 | b3maj9:4 | b3maj9:4 | 4m6:4 | 1maj9:4",
             variants=[{"id": "b", "chords": parse_line(
                 "1m9:4 | 4m9:4 | b6maj9:4 | b7maj9:4 | [b3 major] | 4maj9:4 | 6m9:4 | 5sus4:4 | 1maj9:8 | "
                 "[1 major] | b3add9/b7:4 | 1add9:4 | 4maj9:4 | 1maj9:8")}]),
        card("db-opening", "Db major", exact("4maj9:2 | 4maj7#11:6 | 5^11/4:4 | 4maj7#11:4 | 6m9/1:8", {
            1: "Gb2 Db3 Gb3 Ab3 Bb3 Db4 F4 Bb4 Eb5 F5 Ab5 C6", 3: "Gb2 Db3 Gb3 Ab3 Bb3 Db4 F4 Bb4 Eb5 F5 Ab5 C6"},
            name={1: "Gbmaj13#11", 3: "Gbmaj13#11"})),
        card("held-sus-five", "Eb major", exact("5^7sus4/1:16", {0: "Eb2 Eb3 Eb4 F4 Ab4 Bb4"})),
        card("open-ending-b7", "Eb major", exact("b7maj9:16", {0: "Db3 Ab3 Eb4 F4 Ab4 C5 Db5 F5 Ab5"})),
        card("white-keys", "C major", "1maj9:4 | 6m11:4 | 4maj7#11:4 | 5^7sus4:2 | 5^13:2"),
        card("dorian-vamp", "D minor", "1m11:4 | 4^13:4"),
    ]


def _lines(c):
    return ([None] if c.get("chords") else []) + [v["id"] for v in c.get("variants") or []]


def _written(c, variant):
    items = c["chords"] if variant is None else next(v for v in c["variants"] if v["id"] == variant)["chords"]
    return [it for it in items if "key" not in it and "rest" not in it]


@needs_node
def test_a4_numbers_pitch_classes_sections_and_exact_notes_move_with_the_key():
    """A4: every slot's n is identical in all 12 keys; chord_pcs is the card-key set shifted by the interval; section
    keys move with the card; exact notes shift by s in -6..+5, stay inside E1..G7 and keep their interval pattern."""
    resolver = Resolver()
    cards = seed_like()
    for c in cards:
        S.validate_card(c)
    jobs = [(c, v, k) for c in cards for v in _lines(c)
            for k in (MINOR_KEYS if c["key"].endswith("minor") else MAJOR_KEYS)]
    with ThreadPoolExecutor(6) as pool:
        defs = list(pool.map(lambda job: resolver.resolve(job[0], key=job[2], variant=job[1]), jobs))
    base = {(c["id"], v): resolver.resolve(c, variant=v) for c in cards for v in _lines(c)}
    slots_checked = exact_checked = 0
    for (c, v, k), d in zip(jobs, defs):
        b = base[(c["id"], v)]
        s = shift_of(c["key"], k)
        assert -6 <= s <= 5
        assert [x["n"] for x in d["slots"]] == [x["n"] for x in b["slots"]], (c["id"], v, k)
        assert [nashville.parse_key(sec["key"])["tonic"] for sec in d["sections"]] == \
            [(nashville.parse_key(sec["key"])["tonic"] + s) % 12 for sec in b["sections"]]
        assert [sec["from_beat"] for sec in d["sections"]] == [sec["from_beat"] for sec in b["sections"]]
        written = _written(c, v)
        for x, y, item in zip(d["slots"], b["slots"], written):
            assert set(x["chord_pcs"]) == {(p + s) % 12 for p in y["chord_pcs"]}, (c["id"], v, k, x["i"])
            slots_checked += 1
            if item.get("notes"):
                play = x["voicings"]["play"]
                assert play == shift_notes(item["notes"], s)[0]
                assert play[0] >= 28 and play[-1] <= 103
                assert [p - play[0] for p in play] == [p - min(item["notes"]) for p in sorted(item["notes"])]
                exact_checked += 1
    assert slots_checked >= 17 * 12 * 3 and exact_checked >= 12 * 20


A4_NAMES = [("lydian-four", "Db major", ["Dbmaj9", "Gbmaj7#11"]), ("lydian-four", "F major", ["Fmaj9", "Bbmaj7#11"]),
            ("gospel-five-over-four", "D major", ["Gmaj9", "A11/G", "D/F#", "Dmaj9"]),
            ("lament-bass", "Eb major", ["Cm11", "Cm11/Bb", "Cm11/Ab", "Cm11/G"]),
            ("borrowed-b6-b7-home", "F major", ["Dbmaj9", "Ebmaj9", "Fmaj9"]),
            ("dorian-vamp", "E minor", ["Em11", "A13"]),
            ("sunrise-ending", "F major", ["Fm11", "Fm11", "Dbmaj7#11"])]


@needs_node
def test_a4_the_twenty_hand_written_names():
    by_id = {c["id"]: c for c in seed_like()}
    resolver = Resolver()
    got = []
    for cid, key, names in A4_NAMES:
        slots = resolver.resolve(by_id[cid], key=key)["slots"]
        got.append([s["name"] for s in slots[:len(names)]])
    assert got == [names for _, _, names in A4_NAMES]
    assert sum(len(names) for _, _, names in A4_NAMES) == 20


@needs_node
def test_a4_the_lament_keeps_its_upper_voices_and_its_f_in_every_key():
    lament = next(c for c in seed_like() if c["id"] == "lament-bass")
    resolver = Resolver()
    with ThreadPoolExecutor(6) as pool:
        defs = list(pool.map(lambda k: resolver.resolve(lament, key=k), MAJOR_KEYS))
    for d in defs:
        slots = d["slots"]
        fifth = slots[0]["tones_pc"]["fifth"]
        for key in ("full", "comp"):
            assert len({tuple(s["voicings"][key][1:]) for s in slots}) == 1, (d["key"], key)
        assert fifth in {n % 12 for n in slots[0]["voicings"]["full"][1:]}, d["key"]
        assert [s["upper_same"] for s in slots] == [False, True, True, True]
        assert [s["bass_pc"] for s in slots] == [s["voicings"]["full"][0] % 12 for s in slots]


@needs_node
def test_a4_resolving_is_deterministic_and_fast():
    line = parse_line("1m11:4 | 1m11:4 | b6maj7#11:4 | 5^7sus4:2 | 5^7:2 | b3maj9:4 | b3maj9:4 | 4m6:4 | 1maj9:4 | "
                      "2m9:4 | 5^13:4 | 1maj9:4 | 4maj9:4 | 5^11/4:4 | 1/3:4 | 6m11:4")
    sixteen = card("sixteen-slots", "Eb major", line)
    assert S.chord_count(line) == 16
    first = json.dumps(Resolver().resolve(sixteen, key="Gb major"), sort_keys=True)
    assert json.dumps(Resolver().resolve(sixteen, key="Gb major"), sort_keys=True) == first
    cold = []
    for _ in range(10):
        resolver = Resolver()
        t0 = time.perf_counter()
        resolver.resolve(sixteen)
        cold.append((time.perf_counter() - t0) * 1000)
    warm = []
    for _ in range(10):
        t0 = time.perf_counter()
        resolver.resolve(sixteen)
        warm.append((time.perf_counter() - t0) * 1000)
    assert statistics.median(cold) <= 150, cold
    assert statistics.median(warm) <= 2, warm
    assert resolver.stats["hits"] >= 10


@needs_node
def test_every_resolved_def_validates_and_its_band_keeps_the_registers():
    resolver = Resolver()
    for c in seed_like():
        for v in _lines(c):
            d = resolver.resolve(c, variant=v)
            S.validate_def(d)
            for s in d["slots"]:
                assert s["voicings"]["full"][-1] <= 69 and s["voicings"]["comp"][-1] <= 64
                assert 28 <= s["voicings"]["bass"][0] <= 50
                assert s["bass_pc"] in s["chord_pcs"]


@needs_node
def test_page_reads_name_what_the_page_calls_each_chord():
    by_id = {c["id"]: c for c in seed_like()}
    resolver = Resolver()
    lydian = resolver.page_reads(by_id["lydian-four"])
    assert [(p["slot"], p["name"], p["match"], p["voicing"]) for p in lydian] == [
        (0, "Ebmaj9", "exact", "spread"), (1, "Abmaj7#11", "exact", "spread")]
    apart = {p["variant"]: p for p in resolver.page_reads(by_id["one-note-apart"]) if p["slot"] == 0}
    assert apart["a"]["name"] == "Cm11/Ab" and apart["a"]["match"] == "equivalent" and apart["a"]["voicing"] == "notes"
    assert "your screen calls this Cm11/Ab" in apart["a"]["note"]
    assert apart["b"]["name"] == "Bb11/Ab" and apart["b"]["match"] == "exact"
    drop = resolver.resolve(by_id["minor-third-drop"], variant="b")
    assert [sec["key"] for sec in drop["sections"]] == ["Gb major", "Eb major"]
    d = resolver.resolve(by_id["float-or-pull"], variant="all")
    assert d["card"]["variant"] is None and len(d["slots"]) == 10


@needs_node
def test_the_bridge_band_style_is_used_when_the_bridge_has_it():
    requests = []

    def band_results(req, comp_top=55):
        named = run_bridge({"items": [it["text"] for it in req["items"]], "key": req["items"][0]["key"],
                            "voicing": "close"})
        out = []
        for r in named:
            b = 36 + chord_facts(r["name"])["bass_pc"]
            out.append({"band": {"full": {"notes": [b, 60], "roles": ["bass", "root"]},
                                 "comp": {"notes": [b, comp_top], "roles": ["bass", "fifth"]},
                                 "bass": {"notes": [b], "roles": ["bass"]}},
                        "reads_as": None, "warnings": ["a band note"]})
        return out

    def with_band(req):
        if req.get("voicing") != "band":
            return run_bridge(req)
        requests.append(req)
        return band_results(req)

    lament = next(c for c in seed_like() if c["id"] == "lament-bass")
    d = Resolver(bridge=with_band, band=True).resolve(lament)
    assert STUB_WARNING not in d["warnings"] and [s["voicings"]["full"][1:] for s in d["slots"]] == [[60]] * 4
    assert all("a band note" in s["warnings"] for s in d["slots"])
    assert requests[0]["line"] == "ring" and requests[0]["voicing"] == "band"
    assert requests[0]["items"] == [{"text": "6m11", "key": "Db major"},
                                    {"text": "6m11/5", "key": "Db major", "upper": "same"},
                                    {"text": "6m11/4", "key": "Db major", "upper": "same"},
                                    {"text": "6m11/3", "key": "Db major", "upper": "same"}]

    def off_contract(req):  # a comp above E4 breaks the frozen def: the stand-in takes over, and the def says why
        return band_results(req, comp_top=70) if req.get("voicing") == "band" else run_bridge(req)

    d = Resolver(bridge=off_contract, band=True).resolve(lament)
    assert STUB_WARNING in d["warnings"] and any("did not fit the def" in w for w in d["warnings"])
    assert all("a band note" not in s["warnings"] for s in d["slots"]) and d["slots"][0]["voicings"]["comp"][-1] <= 64

    def refusing_band(req):
        if req.get("voicing") == "band":
            raise ResolveError("", "voicing must be one of close, open, spread, drop2, shell")
        return run_bridge(req)

    d = Resolver(bridge=refusing_band, band=True).resolve(lament)
    assert STUB_WARNING in d["warnings"]


# ============================================================================================ runs (no node)
def _lydian():
    return load("def_lydian_four.json"), load("card_lydian_four.json")


def _spec(mode="loop", bpm=66, count_in=1, now=True, passes=0):
    return {"mode": mode, "bpm": bpm, "count_in": count_in, "now": now, "lead_ms": 800, "slot": None,
            "velocity": None, "settings0": {"from_bar": 0, "groove": "hold", "backing": "full", "level": 44,
                                            "humanize": 0, "seed": 7, "walk": 1, "try_backing": None,
                                            "passes": passes, "ending": "cut"}}


def test_a_whole_run_writes_a_valid_run_json_and_timeline(tmp_path):
    d, c = _lydian()
    t = 1893456000000.0
    store = RunStore(tmp_path / "jam")
    reply, frames = store.start(_spec(), d, c, "claude", t)
    rid = reply["run"]
    assert reply["state"] == "running" and reply["start_epoch_ms"] == t + 800
    assert frames[-1]["op"] == "start" and frames[-1]["def"] == d
    bar_ms = 4 * 60000 / 66
    assert reply["bar0_epoch_ms"] == pytest.approx(t + 800 + bar_ms, abs=1e-6)
    store.ack(rid, {"page_id": "p-1", "role": "owner", "version": 1, "bar": 0, "bar_epoch_ms": reply["bar0_epoch_ms"],
                    "perf_ms": 5000.0, "perf_offset_ms": t - 4000}, t + 900)
    change, _ = store.control(rid, "tempo", {"bpm": "+6"}, "claude", t + 5000)
    assert change["bpm"] == 72
    store.mark("a synthetic mark", rid, None, "claude", t + 6000)
    stop, frames = store.control(rid, "stop", {"at": "pass"}, "claude", t + 9000)
    assert frames[0]["op"] == "stop" and frames[0]["reason"] == "cli"
    run = json.loads((tmp_path / "jam" / "runs" / rid / "run.json").read_text(encoding="utf-8"))
    S.validate_run(run)
    lines = [json.loads(x) for x in (tmp_path / "jam" / "runs" / rid / "events.jsonl").read_text().splitlines()]
    for line in lines:
        S.validate_run_event(line)
    assert [x["kind"] for x in lines] == ["start", "ack", "change", "mark", "stop"]
    assert [x["seq"] for x in lines] == [0, 1, 2, 3, 4]
    assert run["stop_bar"] % 2 == 0 and run["last_version"] == 3
    with pytest.raises(RunError) as err:
        store.control(rid, "tempo", {"bpm": 70}, "claude", t + 9500)
    assert err.value.status == 409
    fresh = RunStore(tmp_path / "jam")
    assert fresh.get(rid)["run"] == run and len(fresh.get(rid)["events"]) == 5


def test_restart_close_is_explicit_and_approximate(tmp_path):
    d, c = _lydian()
    t = 1893456000000.0
    store = RunStore(tmp_path / "jam")
    running = store.start(_spec(), d, c, "claude", t)[0]["run"]
    pending = store.start(_spec(mode="play", count_in=0, now=False), d, c, "claude", t + 10)[0]["run"]
    fresh = RunStore(tmp_path / "jam")
    assert json.loads((tmp_path / "jam" / "runs" / running / "run.json").read_text())["closed"] is False
    assert sorted(fresh.close_unclosed(t + 60000)) == sorted([running, pending])
    for rid in (running, pending):
        got = fresh.get(rid)
        run, last = got["run"], got["events"][-1]
        S.validate_run(run)
        assert run["stop_reason"] == "server-restart" and run["approx"] is True and run["state"] == "stopped"
        assert last["kind"] == "stop" and last["by"] == "server" and last["approx"] is True
        assert run["stopped_epoch_ms"] == max(e["recorded_epoch_ms"] for e in got["events"][:-1])
    assert fresh.get(pending)["run"]["stop_bar"] is None
    assert fresh.close_unclosed(t + 70000) == []


# ============================================================================================ alignment
def _l1():
    folder = FIX / "run_loop_l1"
    run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    events = [json.loads(x) for x in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines() if x]
    return run, events, json.loads((folder / "expected.json").read_text(encoding="utf-8")), \
        PerformanceStore(folder / "session")


def test_the_alignment_ladder_on_the_synthetic_run():
    run, events, expected, store = _l1()
    got = A.align(run, events, store)
    assert len(got) == 1 and got[0]["session"] == expected["session"] and got[0]["method"] == "L1"
    assert got[0]["error_ms"] == 2 and got[0]["page_id"] == expected["alignment"]["page_id"]
    assert abs(got[0]["bar0_t_ms"] - expected["alignment"]["bar0_t_ms"]) <= 0.001
    for b in expected["bars"]:
        assert abs(A.bar_t_ms(got[0], run, b["bar"]) - b["t_ms"]) <= 0.001, b
    info = store.info(expected["session"])
    no_logs = [dict(e, log=None) if e["kind"] == "ack" else e for e in events]
    l2 = A.align_session(run, no_logs, info)
    assert l2["method"] == "L2" and abs(l2["bar0_t_ms"] - expected["alignment"]["bar0_t_ms"]) <= 0.001
    meta = dict(info["meta"])
    meta.pop("page_id")
    l3 = A.align_session(run, no_logs, dict(info, meta=meta))
    assert l3["method"] == "L3" and l3["error_ms"] == 50
    assert abs(l3["bar0_t_ms"] - expected["alignment"]["bar0_t_ms"]) <= 0.001
    meta.pop("opened_at_client")
    l4 = A.align_session(run, no_logs, dict(info, meta=meta))
    assert l4["method"] == "L4" and l4["approx"] is True and l4["error_ms"] == 150
    assert abs(l4["bar0_t_ms"] - expected["alignment"]["bar0_t_ms"]) <= 150
    refused = A.align_session(run, no_logs, dict(info, meta=dict(meta, buffered=True)))
    assert refused["refused"] is True and refused["method"] == "L4" and "opened_at_client" in refused["reason"]
    assert A.align(run, events, None)[0]["reason"] == "no log"
    assert A.align_session(dict(run, segments=[]), events, info)["refused"] is True
