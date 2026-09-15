"""The seed deck (phase J6): arsenal/jam/seed/deck-v1.json, jam-spec section 12.

- **Validation.** The 17 cards validate as a seed file and one by one, the second time as the store holds them after
  `deck seed`.
- **Privacy.** The tracked file carries no moment links, session ids or clock times.
- **Wording.** Every text a card shows passes the wording guard.
- **Verbatim.** The text is section 12's word for word, except for the errata below. The table's group, kind, key,
  tempo, bars, groove, backing and chord lines match, and so does every exact-note chord.
- **Checks and landings.** Each names the note its role points at.
- **Pairs.** Question and answer pairs close.
- **Bridge.** Through the voicing bridge, every chord reads in its section key the way section 12 says the page reads
  it, and the Play voicing holds every check's and landing's note. A4's 20 names come out exactly, and every number
  resolves in all 12 keys.

Merging moments uses synthetic sessions dated 2030. Nothing here reads Daniel's practice log or the git-ignored moments
file (state/arsenal/jam/seed/moments-v1.json).
"""
import copy
import functools
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from arsenal.jam import SEED_API, SEED_MOMENTS_API  # noqa: E402
from arsenal.jam.schemas import (BACKINGS_V1, CARD_WORDING_FORBIDDEN, GROOVES_V1, JamSchemaError,  # noqa: E402
                                 card_settings, card_texts, chord_count, line_beats, pair_problems, validate_card,
                                 validate_seed, validate_seed_moments, wording_problems)

SEED = ROOT / "arsenal" / "jam" / "seed" / "deck-v1.json"
SPEC = ROOT / "research" / "in-flight" / "piano-jam-2026-09-14" / "jam-spec.md"
BRIDGE = ROOT / "arsenal" / "pianocue_voicing.mjs"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is needed to run the voicing bridge")
needs_spec = pytest.mark.skipif(not SPEC.is_file(), reason="jam-spec.md is not on disk (the research folder moved)")

DOC = json.loads(SEED.read_text(encoding="utf-8"))
CARDS = {card["id"]: card for card in DOC["cards"]}
IDS = ["lydian-four", "gospel-five-over-four", "one-note-apart", "blooming-chord", "half-step-slide", "lament-bass",
       "minor-third-drop", "borrowed-four-minor", "borrowed-b6-b7-home", "float-or-pull", "lush-two-five-one",
       "sunrise-ending", "db-opening", "held-sus-five", "open-ending-b7", "white-keys", "dorian-vamp"]
MOMENT_COUNTS = {"lydian-four": 3, "gospel-five-over-four": 4, "one-note-apart": 2, "blooming-chord": 3,
                 "half-step-slide": 2, "lament-bass": 2, "minor-third-drop": 2, "borrowed-four-minor": 2,
                 "borrowed-b6-b7-home": 3, "float-or-pull": 2, "lush-two-five-one": 1, "sunrise-ending": 2,
                 "db-opening": 1, "held-sus-five": 1, "open-ending-b7": 1, "white-keys": 0, "dorian-vamp": 0}
PAIRS = {("held-sus-five", "float-or-pull"), ("open-ending-b7", "borrowed-b6-b7-home")}   # (question, answer)

# Where the deck departs from section 12's words, and why. Each fix applies only while the spec still has the old text.
ERRATA = [
    # 12.17: B is the 3rd of G13; its 13th is E. The check's role is 3 for the same reason.
    ("dorian-vamp", "explanation", "the 13 of G and the 6 of D", "the 3rd of G and the 6 of D"),
    ("dorian-vamp", "checks", "you played B, the 13 of G", "you played B, the 3rd of G"),
    # 12.10's "why" is 301 characters; 4.1 (frozen in J0) allows 300.
    ("float-or-pull", "why", "found in your sessions uses a plain", "found in your sessions use a plain"),
]

# ============================================================================================================ music
LETTERS = "CDEFGAB"
LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
MAJOR_STEPS = (0, 2, 4, 5, 7, 9, 11)
ROLE_SEMIS = {"1": 0, "b3": 3, "3": 4, "4": 5, "#4": 6, "5": 7, "b6": 8, "6": 9, "b7": 10, "7": 11, "b9": 1, "9": 2,
              "#9": 3, "11": 5, "#11": 6, "b13": 8, "13": 9}
KEY_RE = re.compile(r"^([A-G])(#{1,2}|b{1,2})? (major|minor)$")
DEGREE_RE = re.compile(r"^(#{1,2}|b{1,2})?([1-7]) (major|minor)$")
NUMBER_RE = re.compile(r"^(#{1,2}|b{1,2})?([1-7])(.*?)(?:/(#{1,2}|b{1,2})?([1-7]))?$")
NOTE_RE = re.compile(r"^([A-G])(#|b)?(\d)$")
MAJOR_TONICS = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
MINOR_TONICS = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B")


def _acc(text) -> int:
    return (len(text) if text.startswith("#") else -len(text)) if text else 0


def name_pc(name: str) -> int:
    return (LETTER_PC[name[0]] + _acc(name[1:])) % 12


def midi(names: str) -> list:
    out = []
    for token in names.split():
        letter, acc, octave = NOTE_RE.match(token).groups()
        out.append(12 * (int(octave) + 1) + LETTER_PC[letter] + _acc(acc))
    return out


def tonic_pc(key: str) -> int:
    letter, acc, _mode = KEY_RE.match(key).groups()
    return name_pc(letter + (acc or ""))


def degree_key(key: str, item: str) -> str:
    """A key item or variant key ("6 major"), a degree of the card key, spelled from the degree (6 of Gb is Eb)."""
    letter, acc, _mode = KEY_RE.match(key).groups()
    sign, degree, mode = DEGREE_RE.match(item).groups()
    degree = int(degree)
    new_letter = LETTERS[(LETTERS.index(letter) + degree - 1) % 7]
    pc = (tonic_pc(key) + MAJOR_STEPS[degree - 1] + _acc(sign)) % 12
    shift = (pc - LETTER_PC[new_letter] + 6) % 12 - 6
    return f"{new_letter}{'#' * shift if shift > 0 else 'b' * -shift} {mode}"


def plain_key(key: str) -> str:
    """The same key respelled by pitch class when its tonic takes a double accidental or is Cb, Fb, E# or B#."""
    letter, acc, mode = KEY_RE.match(key).groups()
    if (acc and len(acc) == 2) or letter + (acc or "") in ("Cb", "Fb", "E#", "B#"):
        return f"{(MAJOR_TONICS if mode == 'major' else MINOR_TONICS)[tonic_pc(key)]} {mode}"
    return key


def number_pcs(n: str, key: str):
    """(root pc, bass pc) of a Nashville number in a key: tonic numbering with major-scale accidentals (DATA 2.6)."""
    acc, degree, _suffix, bass_acc, bass_degree = NUMBER_RE.match(n).groups()
    root = (tonic_pc(key) + MAJOR_STEPS[int(degree) - 1] + _acc(acc)) % 12
    bass = root if bass_degree is None else (tonic_pc(key) + MAJOR_STEPS[int(bass_degree) - 1] + _acc(bass_acc)) % 12
    return root, bass


def line_of(card: dict, variant=None) -> list:
    if variant is None:
        return card.get("chords") or []
    return next(v["chords"] for v in card["variants"] if v["id"] == variant)


def slots(card: dict, variant=None, key=None) -> list:
    """[(slot, section key, chord item)] of a line with the card played in `key` (default: the card key)."""
    key = key or card["key"]
    section = key
    if variant is not None:
        vkey = next(v for v in card["variants"] if v["id"] == variant).get("key")
        section = degree_key(key, vkey) if vkey else key
    out = []
    for item in line_of(card, variant):
        if "key" in item:
            section = degree_key(key, item["key"])
        elif "rest" not in item:
            out.append((len(out), section, item))
    return out


def lines(card: dict):
    """(variant, slots) for the main line and every variant."""
    out = [(None, slots(card))] if card.get("chords") else []
    return out + [(v["id"], slots(card, v["id"])) for v in card.get("variants", [])]


def line_text(items) -> str:
    """A chord line in the CLI string form (4.1): "1maj9:4 | [6 major] | rest:2"."""
    parts = []
    for it in items:
        if "key" in it:
            parts.append(f"[{it['key']}]")
        elif "rest" in it:
            parts.append(f"rest:{it['rest']:g}")
        else:
            parts.append(f"{it['n']}:{it['beats']:g}")
    return " | ".join(parts)


def strings(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from strings(v, f"{path}[{i}]")


# ============================================================================================================= spec
TEXT_BULLETS = {"Meaning": "meaning", "Theory name": "theory_name", "Explanation": "explanation",
                "Why it matters": "why", "Try this": "try", "Listen for": "listen_for"}


@functools.lru_cache(maxsize=1)
def spec_section() -> str:
    text = SPEC.read_text(encoding="utf-8")
    return text[text.index("## 12. The seed deck"):text.index("## 13. Build plan")]


@functools.lru_cache(maxsize=1)
def spec_rows() -> dict:
    rows = {}
    for raw in spec_section().splitlines():
        if not re.match(r"^\| \d+ \|", raw):
            continue
        cells = [c.strip().replace("\x00", "|") for c in raw.replace("\\|", "\x00").strip().strip("|").split("|")]
        _num, cid, group, kind, key, bpm, bars, groove_backing, line = cells
        groove, backing = [x.strip() for x in groove_backing.split("/")]
        main = re.match(r"^`([^`]+)`", line)
        rows[cid.strip("`")] = {"group": group, "kind": kind, "key": key, "bpm": int(bpm),
                                "bars": None if bars == "var." else int(bars), "groove": groove, "backing": backing,
                                "line": main.group(1) if main else None}
    return rows


@functools.lru_cache(maxsize=1)
def spec_cards() -> dict:
    sec = spec_section()
    heads = list(re.finditer(r"^### 12\.\d+ (.+?) \(`([a-z0-9-]+)`\)\s*$", sec, re.M))
    cards = {}
    for i, head in enumerate(heads):
        body = sec[head.end():heads[i + 1].start() if i + 1 < len(heads) else len(sec)]
        bullets, says, variants = {}, [], {}
        for raw in body.splitlines():
            top = re.match(r"^- \*\*(.+?):\*\* (.*)$", raw)
            if top:
                bullets[top.group(1)] = top.group(2)
                if top.group(1) in ("Check", "Checks"):
                    says = re.findall(r'(?:present|`): "([^"]+)"', top.group(2))
            var = re.match(r'^\s*- \*\*(?:Variant )?([a-f])\*\* "([^"]+)"(.*)$', raw)
            if var:
                ticks = [t for t in re.findall(r"`([^`]+)`", var.group(3)) if re.search(r":\d", t)]
                vkey = re.search(r"variant key `([^`]+)`", var.group(3))
                variants[var.group(1)] = {"label": var.group(2), "line": ticks[0] if ticks else None,
                                          "key": vkey.group(1) if vkey else None}
        tail = re.search(r"\*\*Tags:\*\* (.+?)\. \*\*Related:\*\* (.+?)\. \*\*Moments:\*\* (\d+)\.", body)
        cards[head.group(2)] = {"title": head.group(1), "body": body, "bullets": bullets, "says": says,
                                "variants": variants, "tags": [t.strip() for t in tail.group(1).split(",")],
                                "related": [t.strip() for t in tail.group(2).split(",")],
                                "moments": int(tail.group(3))}
    return cards


def expected(cid: str, field: str, text: str) -> str:
    for eid, efield, old, new in ERRATA:
        if eid == cid and efield == field and old in text:
            text = text.replace(old, new)
    return text


# ========================================================================================================= the file
def test_seed_file_is_the_seventeen_cards():
    assert validate_seed(DOC) == DOC
    assert DOC["api"] == SEED_API and DOC["seed_version"] == 1
    assert [card["id"] for card in DOC["cards"]] == IDS
    for card in DOC["cards"]:
        assert card["source"] == {"kind": "seed", "seed_version": 1}
        assert card["created_by"] == "claude"
        assert card["playback"] == {"velocity": 48} and card["voicing"] == {"style": "spread"}


@pytest.mark.parametrize("cid", IDS)
def test_card_validates_as_the_store_holds_it(cid):
    card = CARDS[cid]
    assert validate_card(card) == card
    stored = {**copy.deepcopy(card), "rev": 1, "created_at": "2030-01-01T00:00:00.000+00:00",
              "updated_at": "2030-01-01T00:00:00.000+00:00", "updated_by": "claude"}
    assert validate_card(stored, stored=True) == stored
    settings = card_settings(card)
    assert settings["groove"] in GROOVES_V1 and settings["backing"] in BACKINGS_V1
    if "bars" in card:
        assert line_beats(card["chords"]) == card["bars"] * card["tempo"]["beats_per_bar"]
    for other in card["related"]:
        assert other in CARDS and other != cid


def test_tracked_seed_carries_no_moment_links():
    raw = SEED.read_text(encoding="utf-8")
    assert not re.search(r"\d{8}-\d{6}-[0-9a-f]{8}", raw), "a session id in the tracked seed"
    assert not re.search(r"\bS[1-4]\b", raw), "a session label in the tracked seed"
    for card in DOC["cards"]:
        assert "moments" not in card and "replay" not in card
    for path, text in strings(DOC):
        assert not re.search(r"\b\d{1,3}:[0-5]\d\b", text), f"{path} holds a clock time: {text!r}"


@pytest.mark.parametrize("cid", IDS)
def test_wording_guard_over_every_text(cid):
    card = CARDS[cid]
    assert wording_problems(card) == []
    shown = dict(card_texts(card))
    for key in ("title", "meaning", "theory_name", "explanation", "why", "try", "listen_for"):
        assert shown.get(key), key
    for path, text in strings(card):
        for word in CARD_WORDING_FORBIDDEN:
            assert not re.search(rf"\b{word}\b", text, re.I), f"{path} says {word!r}"
    # theory names follow plain words: the one-line meaning never opens on the theory name
    assert not card["meaning"].lower().startswith(card["theory_name"].lower())


# ======================================================================================================= section 12
@needs_spec
def test_spec_lists_the_same_cards():
    assert list(spec_rows()) == IDS
    assert list(spec_cards()) == IDS
    assert {cid: spec["moments"] for cid, spec in spec_cards().items()} == MOMENT_COUNTS


@needs_spec
@pytest.mark.parametrize("cid", IDS)
def test_text_and_table_are_section_12(cid):
    card, spec, row = CARDS[cid], spec_cards()[cid], spec_rows()[cid]
    assert card["title"] == spec["title"]
    for label, field in TEXT_BULLETS.items():
        assert card[field] == expected(cid, field, spec["bullets"][label]), field
    assert card["tags"] == spec["tags"]
    assert card["related"] == spec["related"]
    assert [c["say"] for c in card.get("checks", [])] == [expected(cid, "checks", s) for s in spec["says"]]

    for field in ("group", "kind", "key", "groove", "backing"):
        assert card[field] == row[field], field
    assert card["tempo"] == {"bpm": row["bpm"], "beats_per_bar": 4}
    assert card.get("bars") == row["bars"]
    if row["line"]:
        assert line_text(card["chords"]) == row["line"]

    deck_variants = {v["id"]: v for v in card.get("variants", [])}
    assert sorted(deck_variants) == sorted(spec["variants"])
    for vid, sv in spec["variants"].items():
        assert deck_variants[vid]["label"] == sv["label"]
        assert line_text(deck_variants[vid]["chords"]) == sv["line"]
        assert deck_variants[vid].get("key") == sv["key"]


@needs_spec
def test_notes_in_the_spec_prose_are_kept():
    gospel = CARDS["gospel-five-over-four"]
    assert gospel["chords"][2]["say"] == spec_cards()["gospel-five-over-four"]["bullets"]["Note on bar 3"]
    # a progression needs a main line (DATA 2.2): minor-third-drop's is variant a, so Play and Loop start on F to D
    drop = CARDS["minor-third-drop"]
    assert drop["chords"] == line_of(drop, "a")
    assert spec_cards()["lament-bass"]["body"].count("(upper same)") == 3


# ====================================================================================================== exact notes
A_NOTES = "Ab2 Eb3 G3 C4 D4 F4 Bb4"
B_NOTES = "Ab2 Eb3 C4 D4 F4 Bb4"
HANDS = "Bb3 Ab4 C5 Db5 Eb5 F5"
CLOUD = "Gb2 Db3 Gb3 Ab3 Bb3 Db4 F4 Bb4 Eb5 F5 Ab5 C6"
EXACT = {  # (card, variant, slot from 1): notes, as section 12 writes them
    ("one-note-apart", "a", 1): A_NOTES, ("one-note-apart", "b", 1): B_NOTES,
    ("one-note-apart", "c", 1): A_NOTES, ("one-note-apart", "c", 2): B_NOTES,
    ("blooming-chord", None, 1): "Ab2 Eb3 Bb3 Eb4", ("blooming-chord", None, 2): "Ab2 Eb3 Bb3 C4 Eb4",
    ("blooming-chord", None, 3): "Ab2 Eb3 G3 Bb3 C4 Eb4", ("blooming-chord", None, 4): "Ab2 Eb3 G3 Bb3 C4 Eb4 D5 F5",
    ("half-step-slide", "a", 1): "A2 F3 Eb4 G4 C5", ("half-step-slide", "a", 2): "Ab2 F3 Eb4 G4 C5",
    ("half-step-slide", "b", 1): "Bb2 F3 G3 Bb3 D4", ("half-step-slide", "b", 2): "Bb2 F3 Gb3 Bb3 Db4",
    ("lament-bass", None, 1): "Bb2 " + HANDS, ("lament-bass", None, 2): "Ab2 " + HANDS,
    ("lament-bass", None, 3): "Gb2 " + HANDS, ("lament-bass", None, 4): "F2 " + HANDS,
    ("float-or-pull", "a", 2): "Eb2 Eb3 Eb4 F4 Ab4 Bb4",
    ("float-or-pull", "c", 2): "Bb2 F3 Ab3 Eb4", ("float-or-pull", "c", 3): "Bb2 F3 Ab3 D4",
    ("lush-two-five-one", None, 1): "F2 Eb3 Ab3 C4 G4", ("lush-two-five-one", None, 2): "Bb2 D3 Ab3 C4 G4",
    ("lush-two-five-one", None, 3): "Eb2 D3 G3 Bb3 F4",
    ("db-opening", None, 2): CLOUD, ("db-opening", None, 4): CLOUD,
    ("held-sus-five", None, 1): "Eb2 Eb3 Eb4 F4 Ab4 Bb4",
    ("open-ending-b7", None, 1): "Db3 Ab3 Eb4 F4 Ab4 C5 Db5 F5 Ab5",
}
NAMES = {("one-note-apart", "a", 1): "Abmaj13#11", ("one-note-apart", "c", 1): "Abmaj13#11",
         ("blooming-chord", None, 4): "Abmaj13#11", ("db-opening", None, 2): "Gbmaj13#11",
         ("db-opening", None, 4): "Gbmaj13#11"}


def chord_fields():
    """{(card, variant, slot from 1): chord item} over every line of every card."""
    out = {}
    for cid in IDS:
        for vid, line in lines(CARDS[cid]):
            for slot, _key, item in line:
                out[(cid, vid, slot + 1)] = item
    return out


def test_exact_notes_are_the_spec_notes():
    items = chord_fields()
    with_notes = {where for where, item in items.items() if "notes" in item}
    assert with_notes == set(EXACT)
    for where, names in EXACT.items():
        assert items[where]["notes"] == midi(names), where
    assert {where: item["name"] for where, item in items.items() if "name" in item} == NAMES
    arps = {where for where, item in items.items() if "arp_ms" in item}
    assert arps == {("blooming-chord", None, s) for s in (1, 2, 3, 4)}
    assert all(items[where]["arp_ms"] == 45 for where in arps)
    upper = {where for where, item in items.items() if item.get("upper") == "same"}
    assert upper == {("lament-bass", None, s) for s in (2, 3, 4)}


@needs_spec
def test_exact_notes_appear_in_section_12():
    cards = spec_cards()
    for (cid, _vid, _slot), names in EXACT.items():
        text = HANDS if cid == "lament-bass" else names
        assert text in cards[cid]["body"], (cid, text)
    assert "bass Bb2, Ab2, Gb2, F2" in cards["lament-bass"]["body"]
    for (cid, _vid, _slot), name in NAMES.items():
        assert f"name {name}" in cards[cid]["body"], (cid, name)


# =========================================================================================== checks, landings, pairs
SAY_NOTE = re.compile(r"^you (?:touched|played|found|landed on) ([A-G][b#]?|home)\b")
PULL_NOTE = re.compile(r"^([A-G][b#]?)\b")


def role_pc(card, variant, slot, role, relative_to):
    _slot, key, item = slots(card, variant)[slot]
    root, bass = number_pcs(item["n"], key)
    return ((bass if relative_to == "bass" else root) + ROLE_SEMIS[role]) % 12, key


def pointers():
    """(card id, what, variant, slot, role, relative_to, text naming the note) for every check and landing."""
    out = []
    for cid in IDS:
        card = CARDS[cid]
        for chk in card.get("checks", []):
            out.append((cid, f"check {chk['id']}", chk.get("variant"), chk["slot"], chk["role"],
                        chk.get("relative_to", "root"), chk["say"]))
        landing = card.get("landing")
        if landing:
            variant = landing.get("variant")
            slot = landing.get("slot", chord_count(line_of(card, variant)) - 1)
            out.append((cid, "landing", variant, slot, landing["role"], landing.get("relative_to", "root"),
                        landing["pull"]))
    return out


def test_every_check_and_landing_names_the_note_its_role_points_at():
    found = pointers()
    assert len(found) == 19      # 11 checks, 8 landings
    for cid, what, variant, slot, role, relative_to, text in found:
        pc, key = role_pc(CARDS[cid], variant, slot, role, relative_to)
        m = (SAY_NOTE if what.startswith("check") else PULL_NOTE).match(text)
        assert m, (cid, what, text)
        named = tonic_pc(key) if m.group(1) == "home" else name_pc(m.group(1))
        assert named == pc, f"{cid} {what}: role {role} over the {relative_to} is pc {pc}, the text names {m.group(1)}"


def test_landings_are_on_the_cards_that_leave_a_note_hanging():
    landed = {cid for cid in IDS if CARDS[cid].get("landing")}
    assert landed == {"lydian-four", "gospel-five-over-four", "borrowed-four-minor", "borrowed-b6-b7-home",
                      "float-or-pull", "held-sus-five", "open-ending-b7", "white-keys"}


def test_question_and_answer_pairs_close():
    cards = list(CARDS.values())
    assert pair_problems(cards) == []
    pairs = {(c["id"], c["pair"]["with"]) for c in cards if c.get("pair", {}).get("role") == "question"}
    assert pairs == PAIRS
    for question, answer in PAIRS:
        assert CARDS[answer]["pair"] == {"role": "answer", "with": question}
        assert answer in CARDS[question]["related"] and question in CARDS[answer]["related"]
        assert CARDS[question].get("landing"), f"{question} asks, so it leaves a note hanging"
    broken = copy.deepcopy(DOC)
    next(c for c in broken["cards"] if c["id"] == "float-or-pull").pop("pair")
    with pytest.raises(JamSchemaError) as exc:
        validate_seed(broken)
    assert exc.value.field.endswith(".pair")


# ========================================================================================================== moments
def synthetic_moments() -> dict:
    cards = {}
    for i, cid in enumerate(IDS):
        entry = {}
        if MOMENT_COUNTS[cid]:
            entry["moments"] = [{"session": f"20300101-0000{i:02d}-0000000{k}", "at": f"{k}:00", "until": f"{k}:30",
                                 "label": f"synthetic moment {k + 1}"} for k in range(MOMENT_COUNTS[cid])]
        if CARDS[cid]["kind"] == "moment":
            entry["replay"] = {"session": entry["moments"][0]["session"], "at": "0:00", "seconds": 12, "speed": 1}
        if entry:
            cards[cid] = entry
    return {"api": SEED_MOMENTS_API, "cards": cards}


def test_moments_merge_by_card_id():
    moments = synthetic_moments()
    assert validate_seed_moments(moments) == moments
    assert set(moments["cards"]) <= set(CARDS)
    for cid in IDS:
        entry = moments["cards"].get(cid, {})
        merged = {**copy.deepcopy(CARDS[cid]), **entry, "rev": 1, "created_at": "2030-01-01T00:00:00.000+00:00",
                  "updated_at": "2030-01-01T00:00:00.000+00:00", "updated_by": "claude"}
        assert validate_card(merged, stored=True) == merged
        assert wording_problems(merged) == []
        assert len(merged.get("moments", [])) == MOMENT_COUNTS[cid]
        if merged["kind"] == "moment":
            assert merged["replay"]["seconds"] > 0
    leaked = copy.deepcopy(DOC)
    leaked["cards"][0]["moments"] = moments["cards"]["lydian-four"]["moments"]
    with pytest.raises(JamSchemaError) as exc:
        validate_seed(leaked)
    assert exc.value.field == "cards[0].moments"


# =========================================================================================================== bridge
CLOUD_LETTERS = "Gb Db Ab Bb F Eb C"     # the Db pedal cloud has no chord name on the page, only its letters
READS = {  # (card, variant, slot from 0): the page's name for the exact notes, as section 12 says
    ("one-note-apart", "a", 0): "Cm11/Ab", ("one-note-apart", "b", 0): "Bb11/Ab",
    ("one-note-apart", "c", 0): "Cm11/Ab", ("one-note-apart", "c", 1): "Bb11/Ab",
    ("blooming-chord", None, 0): "Absus2", ("blooming-chord", None, 1): "Abadd9",
    ("blooming-chord", None, 2): "Abmaj9", ("blooming-chord", None, 3): "Cm11/Ab",
    ("half-step-slide", "a", 0): "F9/A", ("half-step-slide", "a", 1): "Fm9/Ab",
    ("half-step-slide", "b", 0): "Bb6", ("half-step-slide", "b", 1): "Gbmaj7/Bb",
    ("lament-bass", None, 0): "Bbm11", ("lament-bass", None, 1): "Bbm11/Ab",
    ("lament-bass", None, 2): "Bbm11/Gb", ("lament-bass", None, 3): "Bbm11/F",
    ("float-or-pull", "a", 1): "Bb7sus4/Eb", ("float-or-pull", "c", 1): "Bb7sus4", ("float-or-pull", "c", 2): "Bb7",
    ("lush-two-five-one", None, 0): "Fm9", ("lush-two-five-one", None, 1): "Bb13",
    ("lush-two-five-one", None, 2): "Ebmaj9",
    ("db-opening", None, 1): CLOUD_LETTERS, ("db-opening", None, 3): CLOUD_LETTERS,
    ("held-sus-five", None, 0): "Bb7sus4/Eb", ("open-ending-b7", None, 0): "Dbmaj9",
}
SPELLED = {  # numbers whose page spelling section 12 names
    ("borrowed-b6-b7-home", None, 0): "Bmaj9", ("sunrise-ending", None, 2): "Bmaj7#11",
    ("minor-third-drop", "b", 0): "Cbmaj9", ("borrowed-four-minor", None, 2): "Abm(add9)",
}
EXTRA_KEYS = {"lydian-four": ["Gb major"]}     # 12.1 also names Gb (enharmonic)
A4_NAMES = [("lydian-four", "Db major", ["Dbmaj9", "Gbmaj7#11"]), ("lydian-four", "F major", ["Fmaj9", "Bbmaj7#11"]),
            ("gospel-five-over-four", "D major", ["Gmaj9", "A11/G", "D/F#", "Dmaj9"]),
            ("lament-bass", "Eb major", ["Cm11", "Cm11/Bb", "Cm11/Ab", "Cm11/G"]),
            ("borrowed-b6-b7-home", "F major", ["Dbmaj9", "Ebmaj9", "Fmaj9"]),
            ("dorian-vamp", "E minor", ["Em11", "A13"]),
            ("sunrise-ending", "F major", ["Fm11", "Fm11", "Dbmaj7#11"])]


def notes_text(notes) -> str:
    return " ".join(str(n) for n in notes)


def bridge(key: str, style: str, items) -> dict:
    request = json.dumps({"items": list(items), "key": key, "voicing": style, "voice_lead": False})
    res = subprocess.run([NODE, str(BRIDGE)], input=request, capture_output=True, text=True, encoding="utf-8",
                         cwd=str(ROOT), timeout=120)
    doc = json.loads(res.stdout)
    assert doc.get("ok"), doc
    return dict(zip(items, doc["results"]))


def read_all(groups: dict) -> dict:
    """{(key, style): {item: result}}, one bridge process per key and style, run side by side."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {group: pool.submit(bridge, group[0], group[1], sorted(items)) for group, items in groups.items()}
        return {group: future.result() for group, future in futures.items()}


def reads_back(result: dict) -> bool:
    return not result.get("error") and not any("reads back as" in w for w in result.get("warnings", []))


@functools.lru_cache(maxsize=1)
def default_reads():
    """Every chord of every line in its section key (and the card's other named keys), numbers and exact notes."""
    groups, plan = {}, []
    for cid in IDS:
        card = CARDS[cid]
        style = card["voicing"]["style"]
        for key in [card["key"]] + card.get("also_in", []) + EXTRA_KEYS.get(cid, []):
            for vid, _line in lines(card):
                for slot, section, item in slots(card, vid, key):
                    section = plain_key(section)
                    group = groups.setdefault((section, style), set())
                    group.add(item["n"])
                    if "notes" in item and key == card["key"]:
                        group.add(notes_text(item["notes"]))
                    plan.append((cid, vid, slot, key, section, style, item))
    return plan, read_all(groups)


@needs_node
def test_every_chord_reads_the_way_section_12_says():
    plan, results = default_reads()
    seen_reads, seen_spelled = set(), set()
    for cid, vid, slot, key, section, style, item in plan:
        where = (cid, vid, slot)
        number = results[(section, style)][item["n"]]
        assert reads_back(number), (where, key, number)
        if "notes" not in item:     # Play voices the number, so the page names it as itself
            assert number["roundtrip"]["match"] in ("exact", "enharmonic"), (where, key, number["roundtrip"])
        if key != CARDS[cid]["key"]:
            continue
        if where in SPELLED:
            assert number["roundtrip"]["page_name"] == SPELLED[where], where
            seen_spelled.add(where)
        if "notes" in item:
            read = results[(section, style)][notes_text(item["notes"])]
            assert not read.get("error") and read["notes"] == item["notes"], where
            assert read["name"] == READS[where], (where, read["name"])
            if READS[where] == CLOUD_LETTERS:
                assert read["number"] is None
            seen_reads.add(where)
    assert seen_reads == set(READS) and seen_spelled == set(SPELLED)


@needs_node
def test_play_voicing_holds_every_check_and_landing_note():
    plan, results = default_reads()
    play = {}
    for cid, vid, slot, key, section, style, item in plan:
        if key == CARDS[cid]["key"]:
            notes = item.get("notes") or results[(section, style)][item["n"]]["notes"]
            play[(cid, vid, slot)] = {n % 12 for n in notes}
    for cid, what, variant, slot, role, relative_to, _text in pointers():
        pc, _key = role_pc(CARDS[cid], variant, slot, role, relative_to)
        assert pc in play[(cid, variant, slot)], f"{cid} {what}: pc {pc} is not in the Play voicing"


@needs_node
def test_a4_names_twenty_of_twenty():
    hits = 0
    for cid, key, names in A4_NAMES:
        line = slots(CARDS[cid], None, key)[:len(names)]
        got = bridge(plain_key(line[0][1]), "spread", [item["n"] for _slot, _section, item in line])
        assert [got[item["n"]]["name"] for _s, _k, item in line] == names, (cid, key)
        hits += len(names)
    assert hits == 20


@needs_node
def test_every_number_resolves_in_all_twelve_keys():
    groups, plan = {}, []
    for cid in IDS:
        card = CARDS[cid]
        _letter, _acc_text, mode = KEY_RE.match(card["key"]).groups()
        for tonic in (MAJOR_TONICS if mode == "major" else MINOR_TONICS):
            key = f"{tonic} {mode}"
            for vid, _line in lines(card):
                for slot, section, item in slots(card, vid, key):
                    section = plain_key(section)
                    groups.setdefault((section, "spread"), set()).add(item["n"])
                    plan.append((cid, key, vid, slot, section, item["n"]))
    results = read_all(groups)
    problems = [(cid, key, vid, slot, n, results[(section, "spread")][n].get("error"))
                for cid, key, vid, slot, section, n in plan if not reads_back(results[(section, "spread")][n])]
    assert len(plan) == 1224
    assert problems == []
