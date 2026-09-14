"""Nashville numbers (arsenal/nashville.py): every shared fixture case, the result shape, key and chord parsing.

The JS twin (arsenal/web/piano/nashville.js) runs the same fixture in tests/nashville_js.test.mjs.
"""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal import nashville as nv  # noqa: E402

FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "nashville_cases.json").read_text(encoding="utf-8"))
CASES = FIXTURE["cases"]


def number(case):
    opts = case["opts"]
    return nv.nashville_from_name(case["chord"], case["key"], minor=opts.get("minor", "tonic"),
                                  minor_mark=opts.get("minorMark", "m"), kind=opts.get("kind"))


def test_fixture_is_broad():
    assert len(CASES) >= 100
    keys = {c["key"] for c in CASES if c["key"]}
    assert {nv.key_name_of(t, m) for t in range(12) for m in ("major", "minor")} <= keys  # all 24 estimateKey names
    assert {"relative"} == {c["opts"]["minor"] for c in CASES if "minor" in c["opts"]}
    assert any(c["opts"].get("minorMark") == "-" for c in CASES)


@pytest.mark.parametrize("case", CASES, ids=[f"{i}:{c['chord']}@{c['key']}{json.dumps(c['opts'])}" for i, c in enumerate(CASES)])
def test_fixture_case(case):
    got = number(case)
    assert (got and {"text": got["text"], "diatonic": got["diatonic"]}) == case["expected"]


def test_result_shape():
    assert nv.nashville_from_name("G7/B", "C major") == {
        "text": "5^7/7", "degree": 5, "acc": 0, "root": "5", "suffix": "7",
        "bass": {"degree": 7, "acc": 0, "text": "7"}, "upper": None, "diatonic": True, "kind": "chord"}
    assert nv.nashville_from_name("Bbm7b5", "C major") == {
        "text": "b7ø7", "degree": 7, "acc": -1, "root": "b7", "suffix": "ø7",
        "bass": None, "upper": None, "diatonic": False, "kind": "chord"}
    assert nv.nashville_from_name("F#-A", "C major") == {
        "text": "#4-6", "degree": 4, "acc": 1, "root": "#4", "suffix": "", "bass": None,
        "upper": {"degree": 6, "acc": 0, "text": "6"}, "diatonic": False, "kind": "interval"}
    assert nv.nashville_from_name("Eb4", "C major")["kind"] == "note"


def test_key_dict_and_unreadable_inputs():
    assert nv.nashville_from_name("C7", {"tonic": 5, "mode": "major", "name": "F major", "bias": -1})["text"] == "5^7"
    assert nv.nashville_from_name("C7", {"tonic": 5, "mode": "major"})["text"] == "5^7"
    assert nv.nashville_from_name("C", "H major") is None
    assert nv.nashville_from_name("C", "C lydian") is None
    assert nv.nashville_from_name("", "C major") is None
    assert nv.nashville_from_name(None, "C major") is None


def test_parse_key():
    assert nv.parse_key("C# minor") == {"tonic": 1, "mode": "minor", "name": "C# minor", "bias": 1}
    assert nv.parse_key("Eb minor") == {"tonic": 3, "mode": "minor", "name": "Eb minor", "bias": -1}  # as estimateKey
    assert [nv.parse_key(k)["bias"] for k in ("D# minor", "Gb major", "F# major")] == [1, -1, 1]  # spelled names decide
    assert nv.parse_key("db MAJOR") == {"tonic": 1, "mode": "major", "name": "Db major", "bias": -1}
    assert nv.parse_key("Bbm")["mode"] == "minor"
    assert nv.parse_key("A")["name"] == "A major"
    assert nv.parse_key("A minor")["bias"] == 0 and nv.parse_key("C major")["bias"] == 0
    sharp = {"G", "D", "A", "E", "B", "F#"}
    for tonic in range(12):
        name = nv.MAJOR_KEY_NAMES[tonic]
        assert nv.parse_key(name + " major")["bias"] == (0 if name == "C" else 1 if name in sharp else -1)


def test_spell_in_key_twins_the_js():
    """spell_in_key reads a spelling the way the numbers do (nashville.js spellInKey, which piano.js uses to spell
    chord names in the shown key, returns the same values under the key inScale)."""
    assert nv.spell_in_key((5, -1), "C# minor") == {"letter": 4, "acc": 1, "in_scale": True}                # Ab -> G#
    assert nv.spell_in_key((0, 0), "C# minor", suffix="dim7") == {"letter": 6, "acc": 1, "in_scale": True}  # C -> B#
    assert nv.spell_in_key((3, 1), "C major", suffix="") == {"letter": 4, "acc": -1, "in_scale": False}     # F# chord -> Gb
    assert nv.spell_in_key((3, 1), "C major") == {"letter": 3, "acc": 1, "in_scale": False}                 # the note F#
    assert nv.spell_in_key((0, 0), None) is None


def test_parse_chord():
    assert nv.parse_chord("C6/9/E") == {"kind": "chord", "root": (0, 0), "suffix": "6/9", "bass": (2, 0), "upper": None}
    assert nv.parse_chord("Bbm7b5") == {"kind": "chord", "root": (6, -1), "suffix": "m7b5", "bass": None, "upper": None}
    assert nv.parse_chord("C D E") is None
    assert nv.parse_chord("G5")["kind"] == "chord"  # a power chord, as on a lead sheet ...
    assert nv.parse_chord("G5", kind="note")["kind"] == "note"  # ... or the note G5 when the caller knows
    assert nv.parse_chord("E4")["kind"] == "note"
    assert nv.parse_chord("Bb-Db")["upper"] == (1, -1)
    assert nv.parse_chord("C♯m")["root"] == (0, 1)


def test_every_template_suffix_has_a_family():
    """FAMILY covers exactly the suffixes piano.js's Theory.detect can produce (TEMPLATES plus the power chord)."""
    src = (ROOT / "arsenal" / "web" / "piano.js").read_text(encoding="utf-8")
    block = src[src.index("const TEMPLATES = ["):src.index("];", src.index("const TEMPLATES = ["))]
    suffixes = set(re.findall(r'T\("([^"]*)"', block)) | {"5"}
    assert set(nv.FAMILY) == suffixes
    for suffix in suffixes:  # on the tonic of a major key only minor, diminished and augmented families are flagged
        minorish = suffix.startswith("m") and not suffix.startswith("maj")
        flagged = minorish or suffix in ("dim", "dim7", "aug", "7#5", "maj7#5")
        assert nv.nashville_from_name("C" + suffix, "C major")["diatonic"] is (not flagged), suffix


def test_tone_steps_are_the_templates_letter_steps():
    """A slash chord's bass is read from the chord's own tones: TONE_STEPS is piano.js Theory.detect's TEMPLATES
    (semitones above the root -> letter steps), except a dim7's 7th, a diminished 7th rather than detect's 6th."""
    src = (ROOT / "arsenal" / "web" / "piano.js").read_text(encoding="utf-8")
    block = src[src.index("const TEMPLATES = ["):src.index("];", src.index("const TEMPLATES = ["))]
    want = {"5": {0: 0, 7: 4}}
    for suffix, tones in re.findall(r'T\("([^"]*)",\s*\[\[(.*?)\]\]', block):
        for semis, steps in re.findall(r"(\d+),\s*(\d+)", tones):
            want.setdefault(suffix, {})[int(semis)] = 6 if (suffix, semis) == ("dim7", "9") else int(steps)
    assert nv.TONE_STEPS == want


def test_a_slash_chords_bass_is_read_from_its_chord_not_its_letters():
    """piano.js spellForKey writes a bass that would need a double accidental as its plain twin: D#/G for D#/F## in
    C# minor. G is the chord's 3rd, so it reads #4 (as F##), not b5 (verifier, 2026-09-14)."""
    assert nv.nashville_from_name("D#/G", "C# minor")["text"] == nv.nashville_from_name("D#/F##", "C# minor")["text"] == "2/#4"
    assert nv.nashville_from_name("Gbm/A", "Db major")["text"] == nv.nashville_from_name("Gbm/Bbb", "Db major")["text"] == "4m/b6"
    assert nv.nashville_from_name("C/D", "C major")["text"] == "1/2"  # no chord tone: spelled as detect spells a foreign bass


def test_minor_numberings_flag_the_same_chords():
    minor_cases = [c for c in CASES if c["key"] and c["key"].endswith("minor") and c["expected"]]
    assert len(minor_cases) > 40
    for c in minor_cases:
        kind = c["opts"].get("kind")
        tonic = nv.nashville_from_name(c["chord"], c["key"], minor="tonic", kind=kind)
        relative = nv.nashville_from_name(c["chord"], c["key"], minor="relative", kind=kind)
        assert tonic["diatonic"] == relative["diatonic"], c


def test_relative_numbering_is_the_relative_major_key():
    """minor="relative" numbers like the relative major key, except at the minor key's leading tone (a scale
    member in minor, so C in C# minor is respelled B#, #5 from E, where E major itself keeps C as b6)."""
    compared = 0
    for tonic in range(12):
        minor = nv.key_name_of(tonic, "minor")
        ctx = nv._key_context(minor)
        rel_major = nv._name(nv._relative_major(ctx)) + " major"  # spelled: Eb minor -> Gb major, not F# major
        leading_tone = (ctx["tonic"] + 11) % 12
        for chord in ("C", "Dm", "E7", "F#dim", "Bbmaj7/D", "Ab", "G#m", "Db7"):
            parsed = nv.parse_chord(chord)
            if leading_tone in {nv._pc(parsed["root"])} | ({nv._pc(parsed["bass"])} if parsed["bass"] else set()):
                continue
            got = nv.nashville_from_name(chord, minor, minor="relative")["text"]
            assert got == nv.nashville_from_name(chord, rel_major)["text"], (chord, minor, rel_major)
            compared += 1
    assert compared > 70
