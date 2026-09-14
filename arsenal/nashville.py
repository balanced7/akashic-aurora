"""Nashville numbers from chord names: the Python twin of arsenal/web/piano/nashville.js.

Both modules run every case in tests/fixtures/nashville_cases.json, so the practice-log analyzer and the
piano overlay number a chord the same way.

Conventions (the same words head nashville.js):
- Degree = letter distance from the key tonic's letter + 1. Accidental = semitone difference from that
  degree of the tonic's MAJOR scale (b, #, bb rarely). In C major: Eb -> b3, F# -> #4, Bb -> b7.
- Spelling follows the key, not the chord name: a spelling that fits the key worse than its enharmonic twin
  is respelled first (D#m in Eb minor reads 1m, not #7m). A pitch between two scale notes reads the way charts
  write it, whatever its given spelling (CHART below): major keys b2 b3 #4 b6 b7, minor keys (tonic numbering)
  b2 3 #4 6 7, minor keys numbered from the relative major use that major key's table. Diminished chords lead
  up (#1°, #2°, #5° in major, #1° in minor) and a major or dominant chord on the tritone is b5.
- Minor keys, minor="tonic" (default) numbers from the minor tonic with major-scale accidentals
  (A minor: Am=1m, C=b3, Dm=4m, E=5, Em=5m, F=b6, G=b7). minor="relative" numbers from the relative
  major (A minor: Am=6m, C=1, F=4, G=5, E=3).
- Suffixes: "m" -> minor_mark ("m" by default, or "-"; it also replaces the leading m of m7, m9, m(add9)...),
  "dim" -> "°", "dim7" -> "°7", "m7b5" -> "ø7", "aug" -> "+"; every other Theory.TEMPLATES suffix unchanged.
- The text form is never ambiguous: a suffix digit that would touch the degree (or a "-" minor mark) is
  joined with "^" ("5^7", "1^6", "1^5", "2-^7"). The structured fields let the overlay draw a superscript.
- Slash chords add "/" + the bass degree ("1/3", "5/2", "4/b7"). The bass, and an interval's top note, are read
  from the root, not on their own: a chromatic chord tone keeps its letter (E/G# in C major is 3/#5, A/C# is 6/#1,
  E-G# is 3-#5), unless its own reading is on the scale and the root-relative one is not (C#-E in C major: b2-3).
- kind "note": the note's degree ("3"). kind "interval": "lo-hi" degrees ("1-3"). A cluster, or no key: None.
- diatonic: the root degree and the triad family (major, minor, diminished, augmented; sus, power and
  other) fit the key. Major key: 1 maj, 2 min, 3 min, 4 maj, 5 maj, 6 min, 7 dim. Minor key (tonic
  numbering): 1 min, 2 dim, b3 maj, 4 min, 5 min or maj, b6 maj, b7 maj, 7 dim. Sus, power and other
  chords are diatonic when the root degree is in the scale. Notes and intervals: every note in the scale.
  Non-diatonic means borrowed or chromatic: flagged, never judged. The flag is decided the same way
  under both minor numberings.

The result dict has the same keys and values as the JS result: text, degree, acc, root, suffix,
bass ({degree, acc, text} or None), upper (the interval's top note, same shape, or None), diatonic, kind.
"""
from __future__ import annotations

import re
from typing import Dict, Optional

LETTERS = "CDEFGAB"
LETTER_PC = (0, 2, 4, 5, 7, 9, 11)  # also the major scale, degree 1..7
MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)
MAJOR_KEY_NAMES = ("C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
MINOR_KEY_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B")

FAMILY = {
    "": "maj", "m": "min", "dim": "dim", "aug": "aug", "sus4": "sus", "sus2": "sus", "5": "power",
    "7": "maj", "maj7": "maj", "m7": "min", "m7b5": "dim", "dim7": "dim", "6": "maj", "m6": "min", "add9": "maj",
    "m(add9)": "min", "m(maj7)": "min", "7sus4": "sus", "add11": "maj", "7#5": "aug", "maj7#5": "aug", "7b5": "other",
    "6/9": "maj", "m6/9": "min", "9": "maj", "maj9": "maj", "m9": "min", "9sus4": "sus", "7b9": "maj", "7#9": "maj",
    "maj7#11": "maj", "7#11": "maj", "13": "maj", "maj13": "maj", "m11": "min", "m13": "min", "11": "maj",
}
FITS = {  # tonic-numbered degree text -> triad families that fit
    "major": {"1": ("maj",), "2": ("min",), "3": ("min",), "4": ("maj",), "5": ("maj",), "6": ("min",), "7": ("dim",)},
    "minor": {"1": ("min",), "2": ("dim",), "b3": ("maj",), "4": ("min",), "5": ("min", "maj"), "b6": ("maj",),
              "b7": ("maj",), "7": ("dim",)},
}
# Letter steps of each chord tone above the root, by semitones above it: Theory.detect's TEMPLATES in piano.js (the
# tests check both twins against them), except dim7's 7th, a diminished 7th here (G#dim7/F in A major is 7°7/b6).
# detect spells it as a 6th but always names a dim7 from its bass, so only a written name reaches that entry. A bass
# that is no chord tone is spelled as detect spells a foreign bass.
IV_STEPS = (0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6)
TONE_STEPS = {suffix: {int(s): int(n) for s, n in (x.split(":") for x in tones.split())} for suffix, tones in {
    "": "0:0 4:2 7:4", "m": "0:0 3:2 7:4", "dim": "0:0 3:2 6:4", "aug": "0:0 4:2 8:4", "sus4": "0:0 5:3 7:4",
    "sus2": "0:0 2:1 7:4", "5": "0:0 7:4", "7": "0:0 4:2 7:4 10:6", "maj7": "0:0 4:2 7:4 11:6", "m7": "0:0 3:2 7:4 10:6",
    "m7b5": "0:0 3:2 6:4 10:6", "dim7": "0:0 3:2 6:4 9:6", "6": "0:0 4:2 7:4 9:5", "m6": "0:0 3:2 7:4 9:5",
    "add9": "0:0 2:1 4:2 7:4", "m(add9)": "0:0 2:1 3:2 7:4", "m(maj7)": "0:0 3:2 7:4 11:6", "7sus4": "0:0 5:3 7:4 10:6",
    "add11": "0:0 4:2 5:3 7:4", "7#5": "0:0 4:2 8:4 10:6", "maj7#5": "0:0 4:2 8:4 11:6", "7b5": "0:0 4:2 6:4 10:6",
    "6/9": "0:0 2:1 4:2 7:4 9:5", "m6/9": "0:0 2:1 3:2 7:4 9:5", "9": "0:0 2:1 4:2 7:4 10:6",
    "maj9": "0:0 2:1 4:2 7:4 11:6", "m9": "0:0 2:1 3:2 7:4 10:6", "9sus4": "0:0 2:1 5:3 7:4 10:6",
    "7b9": "0:0 1:1 4:2 7:4 10:6", "7#9": "0:0 3:1 4:2 7:4 10:6", "maj7#11": "0:0 4:2 6:3 7:4 11:6",
    "7#11": "0:0 4:2 6:3 7:4 10:6", "13": "0:0 2:1 4:2 7:4 9:5 10:6", "maj13": "0:0 2:1 4:2 7:4 9:5 11:6",
    "m11": "0:0 2:1 3:2 5:3 7:4 10:6", "m13": "0:0 2:1 3:2 7:4 9:5 10:6", "11": "0:0 2:1 4:2 5:3 7:4 10:6",
}.items()}
EXACT = {"dim": "°", "dim7": "°7", "m7b5": "ø7", "aug": "+"}
# chart degrees for the pitches between two scale notes, by semitones above the tonic numbered from
CHART = {"major": {1: "b2", 3: "b3", 6: "#4", 8: "b6", 10: "b7"}, "minor": {1: "b2", 4: "3", 6: "#4", 9: "6"}}
CHART_DIM = {"major": {1: "#1", 3: "#2", 8: "#5"}, "minor": {1: "#1"}}  # passing diminished chords lead up

_NOTE_RE = re.compile(r"^([A-Ga-g])(#{1,2}|b{1,2})?")
_INTERVAL_RE = re.compile(r"^-([A-Ga-g](?:#{1,2}|b{1,2})?)$")
_OCTAVE_RE = re.compile(r"^-?\d+$")


def _signed(x: int) -> int:
    return (x + 6) % 12 - 6


def _pc(sp) -> int:
    return (LETTER_PC[sp[0]] + sp[1]) % 12


def _acc_text(acc: int) -> str:
    return "#" * acc if acc > 0 else "b" * -acc


def _name(sp) -> str:
    return LETTERS[sp[0]] + _acc_text(sp[1])


def _clean(text) -> str:
    return str(text).strip().replace("♭", "b").replace("♯", "#")


def _parse_note(text: str):
    """(spelling, rest) where a spelling is (letter 0..6, acc), or None."""
    m = _NOTE_RE.match(text)
    if not m:
        return None
    acc_s = m.group(2) or ""
    acc = len(acc_s) if acc_s.startswith("#") else -len(acc_s)
    return (LETTERS.index(m.group(1).upper()), acc), text[m.end():]


def bias_of(tonic: int, mode: str, sp=None) -> int:
    """Spelling bias exactly as Theory.estimateKey: +1 sharp keys, -1 flat keys, 0 for C major / A minor.

    Six accidentals go by the name: F# major sharps, Eb minor flats. A spelled tonic (letter, acc) decides for
    itself: Gb major flats, D# minor sharps."""
    if sp and sp[1]:
        return 1 if sp[1] > 0 else -1
    rel_major = tonic if mode == "major" else (tonic + 3) % 12
    fifths = rel_major * 7 % 12
    if fifths == 6:
        return 1 if mode == "major" else -1
    return 0 if fifths == 0 else 1 if fifths < 6 else -1


def key_name_of(tonic: int, mode: str) -> str:
    return (MAJOR_KEY_NAMES if mode == "major" else MINOR_KEY_NAMES)[tonic % 12] + " " + mode


def parse_key(key_name) -> Optional[Dict]:
    """'F major', 'C# minor', 'Bbm', 'A' (major) -> {tonic, mode, name, bias}, or None when unreadable."""
    if key_name is None:
        return None
    parsed = _parse_note(_clean(key_name))
    if not parsed:
        return None
    sp, rest = parsed
    rest = rest.strip()
    if re.fullmatch(r"(major|maj)?", rest, re.I):
        mode = "major"
    elif re.fullmatch(r"minor|min|m", rest, re.I):
        mode = "minor"
    else:
        return None
    tonic = _pc(sp)
    return {"tonic": tonic, "mode": mode, "name": f"{_name(sp)} {mode}", "bias": bias_of(tonic, mode, sp)}


def _key_context(key) -> Optional[Dict]:
    if isinstance(key, dict):
        if isinstance(key.get("name"), str):
            k = parse_key(key["name"])
        elif isinstance(key.get("tonic"), int) and key.get("mode") in ("major", "minor"):
            k = parse_key(key_name_of(key["tonic"], key["mode"]))
        else:
            k = None
    else:
        k = parse_key(key)
    if not k:
        return None
    return {**k, "sp": _parse_note(k["name"])[0]}


def parse_chord(name, kind: Optional[str] = None) -> Optional[Dict]:
    """A chord name as Theory.detect writes one -> {kind, root, suffix, bass, upper}, spellings as (letter, acc).

    'Fmaj7/A', 'Bbm7b5', 'C6/9/E', 'C5' (power chord), 'C-E' (interval), 'E4' (a note with its octave).
    A bare letter reads as a major chord and 'G5'/'C6'/'C7' read as chords, as on a lead sheet; pass
    kind='note' to read them as notes. A cluster ('C D E') or an unreadable name gives None.
    """
    head = _parse_note(_clean("" if name is None else name))
    if not head:
        return None
    root, rest = head
    if kind == "note":
        return {"kind": "note", "root": root, "suffix": "", "bass": None, "upper": None} if re.fullmatch(r"(-?\d+)?", rest) else None
    iv = _INTERVAL_RE.match(rest)
    if iv:
        return {"kind": "interval", "root": root, "suffix": "", "bass": None, "upper": _parse_note(iv.group(1))[0]}
    if _OCTAVE_RE.match(rest) and rest not in FAMILY:
        return {"kind": "note", "root": root, "suffix": "", "bass": None, "upper": None}
    suffix, bass = rest, None
    slash = suffix.rfind("/")
    if slash >= 0:
        b = _parse_note(suffix[slash + 1:])
        if b and b[1] == "":
            bass, suffix = b[0], suffix[:slash]
    if re.search(r"\s", suffix):
        return None
    return {"kind": "chord", "root": root, "suffix": suffix, "bass": bass, "upper": None}


# ------------------------------------------------------------------ numbering --
def _scale_offset(sp, ctx) -> int:
    """Signed distance of a spelling from the key's own scale at its letter (minor keys also accept the leading tone)."""
    d = (sp[0] - ctx["sp"][0]) % 7
    scale = LETTER_PC if ctx["mode"] == "major" else MINOR_SCALE
    offs = [_signed(_pc(sp) - (ctx["tonic"] + scale[d]))]
    if ctx["mode"] == "minor" and d == 6:
        offs.append(_signed(_pc(sp) - (ctx["tonic"] + 11)))
    best = offs[0]
    for o in offs[1:]:
        if abs(o) < abs(best):
            best = o
    return best


def _degree_from(sp, tonic_sp) -> Dict:
    d = (sp[0] - tonic_sp[0]) % 7
    acc = _signed(_pc(sp) - (_pc(tonic_sp) + LETTER_PC[d]))
    return {"degree": d + 1, "acc": acc, "text": _acc_text(acc) + str(d + 1)}


def _relative_major(ctx):
    letter = (ctx["sp"][0] + 2) % 7
    return letter, _signed(ctx["tonic"] + 3 - LETTER_PC[letter])


def _respell(sp, ctx, minor: str = "tonic", family: Optional[str] = None):
    """The spelling numbers are read from: the one closest to the key's scale (double sharps and flats too: G dim
    in G# minor is F## dim, 7°). Enharmonic ties go to the chart degree, then to the fewer accidentals in the
    degree, then to the spelling given. family: FAMILY of a chord root's suffix, or None for a note, bass or interval."""
    pc = _pc(sp)
    ties, least = [], None
    for letter in range(7):
        acc = _signed(pc - LETTER_PC[letter])
        if abs(acc) > 2:
            continue
        c = abs(_scale_offset((letter, acc), ctx))
        if least is None or c < least:
            least, ties = c, []
        if c == least:
            ties.append((letter, acc))
    if len(ties) < 2:
        return ties[0] if ties else sp
    relative = ctx["mode"] == "minor" and minor == "relative"
    home = _relative_major(ctx) if relative else ctx["sp"]
    table = "major" if relative else ctx["mode"]
    above = (pc - _pc(home)) % 12
    want = (CHART_DIM[table].get(above) if family == "dim" else None) or (
        "b5" if family == "maj" and above == 6 else CHART[table].get(above))

    def rank(s):
        d = _degree_from(s, home)
        return (0 if d["text"] == want else 1, abs(d["acc"]), 0 if s[0] == sp[0] else 1)

    return min(ties, key=rank)  # min keeps the first of equals, as the JS stable sort does


def spell_in_key(sp, key, minor: str = "tonic", suffix: Optional[str] = None) -> Optional[Dict]:
    """A spelling (letter, acc) as it reads in a key: {letter, acc, in_scale}, or None without a readable key.
    The twin of nashville.js spellInKey (which piano.js uses to spell chord names in the shown key)."""
    ctx = _key_context(key)
    if not ctx or not sp:
        return None
    family = None if suffix is None else FAMILY.get(suffix, "other")
    s = _respell(tuple(sp), ctx, "relative" if minor == "relative" else "tonic", family)
    return {"letter": s[0], "acc": s[1], "in_scale": _scale_offset(s, ctx) == 0}


def _number_spelled(s, ctx, minor: str) -> Dict:
    """{degree, acc, text} of a spelling already read in the key, plus tonic-numbered tdeg/tacc for the diatonic test."""
    t = _degree_from(s, ctx["sp"])
    out = _degree_from(s, _relative_major(ctx)) if ctx["mode"] == "minor" and minor == "relative" else t
    return {**out, "tdeg": t["degree"], "tacc": t["acc"]}


def _number(sp, ctx, minor: str, family: Optional[str] = None) -> Dict:
    return _number_spelled(_respell(sp, ctx, minor, family), ctx, minor)


def _bass_steps(bass, root_sp, suffix: str) -> int:
    """Letters from the root up to a slash chord's bass, read from the chord and not from the name's letters (piano.js
    spellForKey may write a bass that would need a double accidental as its plain twin, D#/G for D#/F##): a chord tone
    as its template spells it, any other bass as Theory.detect spells a foreign bass. The twin of nashville.js bassSteps."""
    semis = (_pc(bass) - _pc(root_sp)) % 12
    return TONE_STEPS.get(suffix, {}).get(semis, IV_STEPS[semis])


def _spell_from(sp, steps: int, root_sp, ctx, minor: str):
    """A slash chord's bass or an interval's top note, read from the root: the note sits `steps` letters above the
    root's respelling, so a chromatic chord tone keeps its function (E/G# in C major is 3/#5, not 3/b6). The note's
    own reading stands when it is on the key's scale and the moved spelling is not (C#-E in C major reads b2-3, not
    b2-b4), or when the moved spelling would need more than one accidental in a degree. The twin of nashville.js spellFrom."""
    own = _respell(sp, ctx, minor)
    letter = (root_sp[0] + steps) % 7
    moved = (letter, _signed(_pc(sp) - LETTER_PC[letter]))
    if abs(moved[1]) > 2 or abs(_degree_from(moved, ctx["sp"])["acc"]) > 1:
        return own
    if ctx["mode"] == "minor" and abs(_degree_from(moved, _relative_major(ctx))["acc"]) > 1:
        return own
    return own if _scale_offset(moved, ctx) != 0 and _scale_offset(own, ctx) == 0 else moved


def _pub(n) -> Optional[Dict]:
    return {"degree": n["degree"], "acc": n["acc"], "text": n["text"]} if n else None


def _in_scale(n, ctx) -> bool:
    return _acc_text(n["tacc"]) + str(n["tdeg"]) in FITS[ctx["mode"]]


def _chord_fits(n, suffix: str, ctx) -> bool:
    fits = FITS[ctx["mode"]].get(_acc_text(n["tacc"]) + str(n["tdeg"]))
    if not fits:
        return False
    family = FAMILY.get(suffix, "other")
    return family in ("sus", "power", "other") or family in fits


def _suffix_text(suffix: str, minor_mark: str) -> str:
    if suffix in EXACT:
        return EXACT[suffix]
    if suffix.startswith("m") and not suffix.startswith("maj"):
        return minor_mark + suffix[1:]
    return suffix


def _join_suffix(base: str, suffix: str) -> str:
    if not suffix:
        return base
    if suffix[0].isdigit():
        return base + "^" + suffix
    m = re.match(r"^-(\d.*)$", suffix)
    return base + "-^" + m.group(1) if m else base + suffix


def _build(chord: Dict, ctx: Dict, minor: str, minor_mark: str) -> Dict:
    minor = "relative" if minor == "relative" else "tonic"
    minor_mark = "m" if minor_mark is None else str(minor_mark)
    kind = chord["kind"]
    root_sp = _respell(chord["root"], ctx, minor, FAMILY.get(chord["suffix"], "other") if kind == "chord" else None)
    r = _number_spelled(root_sp, ctx, minor)
    if kind == "note":
        return {"text": r["text"], "degree": r["degree"], "acc": r["acc"], "root": r["text"], "suffix": "",
                "bass": None, "upper": None, "diatonic": _in_scale(r, ctx), "kind": kind}
    if kind == "interval":
        steps = (chord["upper"][0] - chord["root"][0]) % 7  # an interval keeps the letters it is written with
        u = _number_spelled(_spell_from(chord["upper"], steps, root_sp, ctx, minor), ctx, minor)
        return {"text": f"{r['text']}-{u['text']}", "degree": r["degree"], "acc": r["acc"], "root": r["text"],
                "suffix": "", "bass": None, "upper": _pub(u), "diatonic": _in_scale(r, ctx) and _in_scale(u, ctx),
                "kind": kind}
    sfx = _suffix_text(chord["suffix"], minor_mark)
    b = _number_spelled(_spell_from(chord["bass"], _bass_steps(chord["bass"], root_sp, chord["suffix"]), root_sp, ctx, minor),
                        ctx, minor) if chord["bass"] else None
    return {"text": _join_suffix(r["text"], sfx) + ("/" + b["text"] if b else ""), "degree": r["degree"],
            "acc": r["acc"], "root": r["text"], "suffix": sfx, "bass": _pub(b), "upper": None,
            "diatonic": _chord_fits(r, chord["suffix"], ctx), "kind": "chord"}


def nashville_from_name(chord_name, key_name, minor: str = "tonic", minor_mark: str = "m",
                        kind: Optional[str] = None) -> Optional[Dict]:
    """Number a chord name ('Fmaj7/A') in a key ('F major', or a {tonic, mode, name} dict). None for a cluster or no key."""
    ctx = _key_context(key_name)
    chord = parse_chord(chord_name, kind)
    if not ctx or not chord:
        return None
    return _build(chord, ctx, minor, minor_mark)
