"""The band voicer in arsenal/pianocue_voicing.mjs: jam-spec 10.1 and the voicing half of acceptance check A4.

Every seed line of jam-spec section 12 (main lines and variants, as the spec's text writes them) is voiced in all 12
keys. The checks: registers and low-interval limits, the round-trip gate with its exact exception list, the 20 names,
numbers and pitch classes that follow the key, the ring's wrap move, the lament's shared hands, determinism and speed.
Nothing here reads Daniel's practice log: the lines are the spec's own text.
"""
import json
import shutil
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BRIDGE = ROOT / "arsenal" / "pianocue_voicing.mjs"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="the voicing bridge needs node")

# ------------------------------------------------------------------------------------------------ the seed lines
# jam-spec section 12, as written: "|" between chords, "[6 major]" a key item (a degree of the card key), " same" an
# upper "same" slot. variant_keys: a variant's own key, as a degree of the card key.
SEED = [
    {"id": "lydian-four", "key": "Eb major", "kind": "loop", "lines": {"main": "1maj9 | 4maj7#11"}},
    {"id": "gospel-five-over-four", "key": "Eb major", "kind": "loop",
     "lines": {"main": "4maj9 | 5^11/4 | 1/3 | 1maj9", "b": "4maj9 | 5^11/4 | 3m9 | 6m11"}},
    {"id": "one-note-apart", "key": "Eb major", "kind": "concept",
     "lines": {"a": "4maj13#11", "b": "5^11/4", "c": "4maj13#11 | 5^11/4 | 1/3"}},
    {"id": "blooming-chord", "key": "Eb major", "kind": "progression",
     "lines": {"main": "4sus2 | 4add9 | 4maj9 | 4maj13#11"}},
    {"id": "half-step-slide", "key": "Eb major", "kind": "concept",
     "lines": {"a": "2^9/#4 | 2m9/4 | 4maj7#11", "b": "#4m7/6 | 4maj7/6"}, "variant_keys": {"b": "b7 major"}},
    {"id": "lament-bass", "key": "Db major", "kind": "loop",
     "lines": {"main": "6m11 | 6m11/5 same | 6m11/4 same | 6m11/3 same"}},
    {"id": "minor-third-drop", "key": "F major", "kind": "progression",
     "lines": {"a": "1add9 | 4maj13 | 5^6 | [6 major] | 1add9 | 4maj13 | 1maj9",
               "b": "4maj9 | 1maj9 | 5sus4 | [b7 major] | b3add9/b7 | 1add9 | 4maj9 | 1maj9"},
     "variant_keys": {"b": "b2 major"}},
    {"id": "borrowed-four-minor", "key": "Eb major", "kind": "loop", "lines": {"main": "1maj9 | 4add9 | 4m(add9) | 1maj9"}},
    {"id": "borrowed-b6-b7-home", "key": "Eb major", "kind": "loop", "lines": {"main": "b6maj9 | b7maj9 | 1maj9"}},
    {"id": "float-or-pull", "key": "Eb major", "kind": "concept",
     "lines": {"a": "1maj9 | 5^7sus4/1 | 1maj9", "b": "1maj9 | 5^7 | 1maj9", "c": "1maj9 | 5^7sus4 | 5^7 | 1maj9"}},
    {"id": "lush-two-five-one", "key": "Eb major", "kind": "loop", "lines": {"main": "2m9 | 5^13 | 1maj9"}},
    {"id": "sunrise-ending", "key": "Eb major", "kind": "loop",
     "lines": {"main": "1m11 | 1m11 | b6maj7#11 | 5^7sus4 | 5^7 | b3maj9 | b3maj9 | 4m6 | 1maj9",
               "b": "1m9 | 4m9 | b6maj9 | b7maj9 | [b3 major] | 4maj9 | 6m9 | 5sus4 | 1maj9 | [1 major] | b3add9/b7 | "
                    "1add9 | 4maj9 | 1maj9"}},
    {"id": "db-opening", "key": "Db major", "kind": "loop",
     "lines": {"main": "4maj9 | 4maj7#11 | 5^11/4 | 4maj7#11 | 6m9/1"}},
    {"id": "held-sus-five", "key": "Eb major", "kind": "moment", "lines": {"main": "5^7sus4/1"}},
    {"id": "open-ending-b7", "key": "Eb major", "kind": "moment", "lines": {"main": "b7maj9"}},
    {"id": "white-keys", "key": "C major", "kind": "loop", "lines": {"main": "1maj9 | 6m11 | 4maj7#11 | 5^7sus4 | 5^13"}},
    {"id": "dorian-vamp", "key": "D minor", "kind": "loop", "lines": {"main": "1m11 | 4^13"}},
]
assert len(SEED) == 17

# A4: the only full slots allowed to read as another chord (1-based slots), the chords whose cards show a reads-as line
READS_AS = {("one-note-apart", "a", 1), ("one-note-apart", "c", 1), ("blooming-chord", "main", 4)}

# A4: the 20 name expectations, (card, key) -> the main line's names (sunrise: its first three slots)
NAMES = {
    ("lydian-four", "Db major"): ["Dbmaj9", "Gbmaj7#11"],
    ("lydian-four", "F major"): ["Fmaj9", "Bbmaj7#11"],
    ("gospel-five-over-four", "D major"): ["Gmaj9", "A11/G", "D/F#", "Dmaj9"],
    ("lament-bass", "Eb major"): ["Cm11", "Cm11/Bb", "Cm11/Ab", "Cm11/G"],
    ("borrowed-b6-b7-home", "F major"): ["Dbmaj9", "Ebmaj9", "Fmaj9"],
    ("dorian-vamp", "E minor"): ["Em11", "A13"],
    ("sunrise-ending", "F major"): ["Fm11", "Fm11", "Dbmaj7#11"],
}
assert sum(len(v) for v in NAMES.values()) == 20

MAJOR_KEYS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
MINOR_KEYS = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]
DEGREE = {"1": 0, "b2": 1, "2": 2, "b3": 3, "3": 4, "4": 5, "#4": 6, "5": 7, "b6": 8, "6": 9, "b7": 10, "7": 11}
LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# design-music 4.4, as the bridge's BAND_LIL: the lowest allowed lower note of an adjacent pair, by interval
LIL = {1: 52, 2: 51, 3: 48, 4: 46, 5: 46, 6: 47, 7: 34, 8: 41, 9: 41, 10: 41, 11: 41, 13: 40, 14: 39}
ALTERED = {"fifth": {6, 8}, "ninth": {1, 3}, "eleventh": {6}, "thirteenth": {8}}  # semitones above the root


def key_pc(name):
    tonic, mode = name.split(" ")
    return (LETTER_PC[tonic[0]] + tonic.count("#") - tonic[1:].count("b")) % 12, mode


def key_name(pc, mode):
    return f"{(MAJOR_KEYS if mode == 'major' else MINOR_KEYS)[pc % 12]} {mode}"


def degree_key(card_pc, degree_item):
    degree, mode = degree_item.split(" ")
    return key_name(card_pc + DEGREE[degree], mode)


def items_for(card, variant, shift):
    """The band items of one line with the card moved up `shift` semitones (section keys move with it)."""
    card_pc, mode = key_pc(card["key"])
    card_pc = (card_pc + shift) % 12
    vkey = card.get("variant_keys", {}).get(variant)
    section = degree_key(card_pc, vkey) if vkey else key_name(card_pc, mode)
    items = []
    for token in (t.strip() for t in card["lines"][variant].split("|")):
        if token.startswith("["):
            section = degree_key(card_pc, token[1:-1])
            continue
        text, _, flag = token.partition(" ")
        item = {"text": text, "key": section}
        if flag == "same":
            item["upper"] = "same"
        items.append(item)
    return items


def bridge(request, raw=False):
    proc = subprocess.run([NODE, str(BRIDGE)], input=json.dumps(request), capture_output=True, text=True,
                          encoding="utf-8", timeout=300)
    assert proc.stdout.strip(), proc.stderr
    return proc.stdout if raw else json.loads(proc.stdout)


def band(items, **kw):
    reply = bridge({"items": items, "voicing": "band", **kw})
    assert reply["ok"], reply
    return reply["results"]


@pytest.fixture(scope="module")
def seed():
    """(card id, variant, shift) -> results, for every seed line in all 12 keys (one batched node call per card)."""
    def one(card):
        keys = [(v, s) for v in card["lines"] for s in range(12)]
        reply = bridge({"requests": [{"items": items_for(card, v, s), "voicing": "band"} for v, s in keys]})
        assert reply["ok"], reply
        out = {}
        for (v, s), r in zip(keys, reply["replies"]):
            assert r["ok"], (card["id"], v, s, r)
            out[(card["id"], v, s)] = r["results"]
        return out

    got = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for part in pool.map(one, SEED):
            got.update(part)
    return got


def cards_by_id():
    return {c["id"]: c for c in SEED}


# ---------------------------------------------------------------------------------------------------- A4 checks
def test_every_seed_line_voices_in_all_12_keys(seed):
    lines = sum(len(c["lines"]) for c in SEED)
    assert len(seed) == lines * 12
    for (cid, variant, shift), results in seed.items():
        card = cards_by_id()[cid]
        assert len(results) == len(items_for(card, variant, shift))
        for r in results:
            assert not r.get("error"), (cid, variant, shift, r)
            assert r["voicing"] == "band" and set(r["band"]) == {"full", "comp", "bass"}


def test_band_registers_spacing_and_the_bass(seed):
    checked = 0
    for (cid, variant, shift), results in seed.items():
        for i, r in enumerate(results):
            where = (cid, variant, shift, i + 1, r["name"])
            root = r["tones_pc"]["root"]
            for backing in ("full", "comp", "bass"):
                v = r["band"][backing]
                notes = v["notes"]
                assert notes == sorted(set(notes)), where
                assert 28 <= notes[0] <= 50 and notes[0] % 12 == r["bass_pc"], (where, backing, notes)
                assert len(v["roles"]) == len(notes) and v["roles"][0] == "bass", (where, backing, v)
                pairs = [(a, b) for a, b in zip(notes, notes[1:]) if b - a in LIL and a < LIL[b - a]]
                assert not pairs, (where, backing, notes, pairs)
            assert r["band"]["bass"]["notes"] == [r["band"]["full"]["notes"][0]], where
            full, comp = r["band"]["full"]["notes"], r["band"]["comp"]["notes"]
            assert full[-1] <= 69 and comp[-1] <= 64, (where, full, comp)
            assert 3 <= len(full) <= 7 and 2 <= len(comp) <= 7, (where, full, comp)
            # Loosening the seed deck may need where nothing else fits, always said in a warning: a minor 2nd on top, or
            # an inner comp voice over B3 (never a broken low-interval limit or a wider span)
            loose = [w for w in r["warnings"] if w.startswith("nothing else fits")]
            assert all("minor 2nd between its top two" in w or "inner voice over the top" in w for w in loose), (where, loose)
            group_loose = loose + [w for j in range(i, -1, -1) if results[j]["upper_same"] or j == i
                                   for w in results[j - 1 if results[j]["upper_same"] else j]["warnings"]
                                   if w.startswith("nothing else fits")]
            for backing, notes in (("full", full), ("comp", comp)):
                assert notes[1] - notes[0] >= 7 and notes[-1] - notes[1] <= 24, (where, notes)
                if notes[-1] - notes[-2] == 1:
                    assert any(f"the {backing} voicing" in w and "minor 2nd" in w for w in group_loose), (where, backing, notes)
            assert full[1] >= 50 and comp[1] >= 48, (where, full, comp)
            # comp's inner voices sit in C3-B3; only the top voice or an altered colour reaches up to E4
            for note, role in zip(comp[1:-1], r["band"]["comp"]["roles"][1:-1]):
                if note > 59 and not any("comp voicing" in w and "inner voice" in w for w in group_loose):
                    assert (note - root) % 12 in ALTERED.get(role, set()), (where, comp, role)
            # the bass pitch class is not doubled above it, except a root-position root filling a thin chord, or a
            # run of shared upper voices
            in_run = r["upper_same"] or (i + 1 < len(results) and results[i + 1]["upper_same"])
            doubled = [n for n in full[1:] if n % 12 == r["bass_pc"]]
            if doubled and not in_run:
                assert r["bass_pc"] == root and len(full) <= 4, (where, full)
            checked += 1
    assert checked == 12 * sum(len(items_for(c, v, 0)) for c in SEED for v in c["lines"])


def test_full_band_reads_back_as_itself_except_the_three_reads_as_chords(seed):
    misses = set()
    for (cid, variant, shift), results in seed.items():
        for i, r in enumerate(results):
            match = r["roundtrip"]["match"]
            if match in ("exact", "enharmonic"):
                assert r["reads_as"] is None, r
                continue
            misses.add((cid, variant, i + 1))
            assert r["reads_as"] and any("reads it as" in w or "reads this one as" in w for w in r["warnings"]), r
    assert misses == READS_AS


def test_the_twenty_names():
    got = 0
    by_id = cards_by_id()
    for (cid, key), names in NAMES.items():
        card = by_id[cid]
        shift = (key_pc(key)[0] - key_pc(card["key"])[0]) % 12
        items = items_for(card, "main", shift)[:len(names)]
        assert items[0]["key"] == key
        results = band(items)
        assert [r["name"] for r in results] == names, (cid, key, [r["name"] for r in results])
        got += len(names)
    assert got == 20


def test_numbers_stay_and_pitch_classes_move_with_the_key(seed):
    for card in SEED:
        for variant in card["lines"]:
            home = seed[(card["id"], variant, 0)]
            for shift in range(1, 12):
                moved = seed[(card["id"], variant, shift)]
                for a, b in zip(home, moved):
                    assert a["number"] == b["number"], (card["id"], variant, shift, a["number"], b["number"])
                    assert b["tones_pc"] == {role: (pc + shift) % 12 for role, pc in a["tones_pc"].items()}, (a, b)
                    assert b["bass_pc"] == (a["bass_pc"] + shift) % 12


def test_the_ring_wrap_move_costs_no_more_than_the_largest_other_move(seed):
    # The ring's moves are the moves between the line's chords, where a run of upper "same" slots is one chord (jam-spec
    # 10.1): the move into each run's first slot. Inside a run nothing is chosen (the written bass walks under the
    # shared hands), so the lament, one run, has no other move to compare its wrap with.
    loops = [c for c in SEED if c["kind"] == "loop"]
    assert len(loops) == 10
    compared = 0
    for card in loops:
        for shift in range(12):
            results = seed[(card["id"], "main", shift)]
            for backing in ("full", "comp"):
                assert None not in [r["band"][backing]["move_cost"] for r in results]
                moves = [r["band"][backing]["move_cost"] for r in results if not r["upper_same"]]
                if len(moves) > 1:
                    assert moves[0] <= max(moves[1:]) + 1e-9, (card["id"], shift, backing, moves)
                    compared += 1
    assert compared == 9 * 12 * 2


def test_the_lament_keeps_its_hands_and_its_F_over_the_walking_bass(seed):
    card = cards_by_id()["lament-bass"]
    for shift in range(12):
        results = seed[("lament-bass", "main", shift)]
        assert [r["upper_same"] for r in results] == [False, True, True, True]
        for backing in ("full", "comp"):
            uppers = {tuple(r["band"][backing]["notes"][1:]) for r in results}
            assert len(uppers) == 1, (shift, backing, [r["band"][backing]["notes"] for r in results])
        fifth = results[0]["tones_pc"]["fifth"]  # F over Bb in Db major
        assert fifth in {n % 12 for n in results[0]["band"]["full"]["notes"][1:]}, (shift, results[0]["band"])
        assert [r["band"]["full"]["notes"][0] % 12 for r in results] == [r["bass_pc"] for r in results]
        assert all(r["roundtrip"]["match"] in ("exact", "enharmonic") for r in results), (shift, card["key"])


def test_band_output_is_byte_identical_on_repeat_and_inside_a_batch():
    card = cards_by_id()["sunrise-ending"]
    request = {"items": items_for(card, "b", 5), "voicing": "band"}
    first, second = bridge(request, raw=True), bridge(request, raw=True)
    assert first == second
    batch = bridge({"requests": [request, {"items": items_for(card, "main", 0), "voicing": "band"}, request]})
    assert json.dumps(batch["replies"][0], separators=(",", ":")) == first.strip()
    assert batch["replies"][2] == batch["replies"][0]


def test_a_sixteen_slot_band_line_costs_little_over_a_plain_voicing():
    items = [{"text": t, "key": "Eb major"} for t in
             "1m11 1m11 b6maj7#11 5^7sus4 5^7 b3maj9 b3maj9 4m6 1maj9 4maj9 5^11/4 1/3 1maj9 2m9 5^13 1maj9".split()]
    assert len(items) == 16

    def median_ms(request):
        runs = []
        for _ in range(10):
            t0 = time.perf_counter()
            reply = bridge(request)
            runs.append((time.perf_counter() - t0) * 1000)
            assert reply["ok"]
        return statistics.median(runs)

    plain = median_ms({"items": items, "voicing": "spread"})
    banded = median_ms({"items": items, "voicing": "band"})
    print(f"\n16-slot cold median: spread {plain:.0f} ms, band {banded:.0f} ms (node start included)")
    assert banded - plain <= 40, (plain, banded)


# ----------------------------------------------------------------------------------------------- the contract
def test_upper_same_shares_the_shape_and_a_failed_gate_is_a_warning_not_a_refusal():
    # F/C cannot share C major's upper voices and still read as F/C: voiced anyway, with the warning
    results = band([{"text": "1", "key": "C major"}, {"text": "4/1", "key": "C major", "upper": "same"}])
    assert all(not r.get("error") for r in results)
    for backing in ("full", "comp"):
        assert results[0]["band"][backing]["notes"][1:] == results[1]["band"][backing]["notes"][1:]
    assert any("reads back as each chord" in w for w in results[0]["warnings"] + results[1]["warnings"]), results
    assert any(r["reads_as"] for r in results)


def test_upper_same_without_a_chord_before_it_is_voiced_on_its_own():
    results = band([{"text": "6m11/5", "key": "Db major", "upper": "same"}, "bogus chord!"], key="Db major")
    assert results[0]["upper_same"] is False and any("upper \"same\" needs a chord" in w for w in results[0]["warnings"])
    assert results[1].get("error")
    bad = band([{"text": "1", "upper": "held"}], key="C major")
    assert "upper must be" in bad[0]["error"]


def test_a_line_through_a_key_change_notes_items_and_a_chain():
    items = [{"text": "5^6", "key": "F major"}, {"text": "1add9", "key": "D major"}, "Ab2 Eb3 G3 C4 D4 F4 Bb4",
             {"text": "1maj9", "key": "D major"}]
    ring = band(items, key="Eb major")
    assert [r["name"] for r in ring[:2]] == ["C6", "Dadd9"] and ring[1]["key"] == "D major"
    assert ring[2]["kind"] == "notes" and ring[2]["name"] == "Cm11/Ab" and ring[2]["bass_pc"] == 8
    assert ring[0]["band"]["full"]["move_cost"] is not None
    chain = band(items, key="Eb major", line="chain")
    assert chain[0]["band"]["full"]["move_cost"] is None and chain[1]["band"]["full"]["move_cost"] is not None
    assert bridge({"items": ["1"], "key": "C major", "voicing": "band", "line": "loop"})["ok"] is False
    cluster = band(["C4 Db4 D4"])
    assert "the band voices chords" in cluster[0]["error"]


def test_tones_pc_and_bass_pc_on_every_style_and_on_notes():
    for style in ("close", "open", "spread", "drop2", "shell"):
        r = bridge({"items": ["Bbm11/Gb", "Ab2 C3 Eb3 G3"], "voicing": style, "key": "Db major"})["results"]
        assert r[0]["tones_pc"] == {"root": 10, "third": 1, "fifth": 5, "seventh": 8, "ninth": 0, "eleventh": 3}
        assert r[0]["bass_pc"] == 6
        assert r[1]["tones_pc"] == {"root": 8, "third": 0, "fifth": 3, "seventh": 7} and r[1]["bass_pc"] == 8
    cluster = bridge({"items": ["C4 Db4 D4"], "voicing": "close"})["results"][0]
    assert cluster["tones_pc"] is None and cluster["bass_pc"] == 0
    keyed = bridge({"items": [{"text": "1maj9", "key": "D major"}, "1maj9"], "key": "Eb major", "voicing": "close"})
    assert [r["name"] for r in keyed["results"]] == ["Dmaj9", "Ebmaj9"]
