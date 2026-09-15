"""Card -> resolved def: the notes, names and chord facts the page plays from (jam-spec 4.2, DATA 2.6, MUSIC 3.1, 9.5).

The page never calls the voicing bridge: the server resolves a card (or a bare chord line) in a key into an
arsenal.jam.def/v0 and sends the page finished notes.

  Resolver().resolve(card, key=None, variant=None, backing=None, voicing=None, slot=None) -> def
  Resolver().resolve_chords(items, key, meter=4, backing="comp", voicing="spread", slot=None) -> def (def.card null)
  Resolver().page_reads(card) -> [PageRead]   what the page names each chord in the card key (DATA 2.7)

How a line becomes slots (DATA 2.6, C6, C7):
- Key items start sections. A key item is a degree of the card key ("6 major"), moved with the card to the shown key,
  so its spelling follows the degree: 6 major of Gb major is Eb major. A rest is a gap in at_beat.
- Numbers are voiced by arsenal/pianocue_voicing.mjs in their section's key (one bridge call per section and style,
  calls in parallel). That call gives the name, the play notes and what the page reads.
- Exact notes (his voicings) shift by the nearest interval s = mod(K - card tonic + 6, 12) - 6 (-6..+5), then fold an
  octave to stay inside E1..G7; notes still off the keyboard are dropped with a warning. A second bridge call in notes
  mode records what the page reads them as.
- tones_pc, bass_pc and the band voicings (full, comp, bass) come from the bridge's `band` style (J1, jam-spec 10.1).
  Until the bridge has that style, a stand-in voicer here keeps the registers and the upper_same rule, and the def
  carries a warning saying so. tones_pc falls back to reading the chord name's suffix (suffix_tones).
- chord_pcs is the named chord's tones plus the bass pitch class; scale, scale_name and class follow MUSIC 9.5.

Cache (4.2): keyed (id, rev, key, variant, backing, play voicing, slot) plus whether the bridge has the band style, so
a bridge that gains it re-voices. A warm resolve is a JSON decode of the cached answer.
"""
from __future__ import annotations

import json
import math
import re
import shutil
import subprocess
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from arsenal import nashville
from arsenal.jam import DEF_API
from arsenal.jam import schemas as S

BRIDGE = Path(__file__).resolve().parents[1] / "pianocue_voicing.mjs"
BRIDGE_TIMEOUT_S = 60
CACHE_SIZE = 512
MAJOR_STEPS = (0, 2, 4, 5, 7, 9, 11)
PC_FLAT = ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B")
PC_SHARP = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
EXACT_LOW, EXACT_HIGH = 28, 103          # E1..G7 after the octave folds (DATA 2.6)
STUB_WARNING = "the band voicings come from a stand-in voicer until the bridge's band style lands"
ROLE_SEMIS = {"1": 0, "b3": 3, "3": 4, "4": 5, "#4": 6, "5": 7, "b6": 8, "6": 9, "b7": 10, "7": 11, "b9": 1, "9": 2,
              "#9": 3, "11": 5, "#11": 6, "b13": 8, "13": 9}
ROLE_STEPS = {"1": 0, "b3": 2, "3": 2, "4": 3, "#4": 3, "5": 4, "b6": 5, "6": 5, "b7": 6, "7": 6, "b9": 1, "9": 1,
              "#9": 1, "11": 3, "#11": 3, "b13": 5, "13": 5}  # letters above the root (or bass) a role sits

# Section scales on the tonic, in MUSIC 9.5's order, and every scale a slot can be named by (semitones above its root).
SECTION_SCALES = (("major", (0, 2, 4, 5, 7, 9, 11)), ("natural minor", (0, 2, 3, 5, 7, 8, 10)),
                  ("harmonic minor", (0, 2, 3, 5, 7, 8, 11)), ("melodic minor", (0, 2, 3, 5, 7, 9, 11)),
                  ("Dorian", (0, 2, 3, 5, 7, 9, 10)), ("Mixolydian", (0, 2, 4, 5, 7, 9, 10)),
                  ("Lydian", (0, 2, 4, 6, 7, 9, 11)), ("Phrygian", (0, 1, 3, 5, 7, 8, 10)))
SCALE_OF = dict(SECTION_SCALES)
PHRYGIAN_DOMINANT = (0, 1, 4, 5, 7, 8, 10)
LYDIAN_DOMINANT = (0, 2, 4, 6, 7, 9, 10)
LOCRIAN_NAT9 = (0, 2, 3, 5, 6, 8, 10)
WHOLE_HALF = (0, 2, 3, 5, 6, 8, 9, 11)
WHOLE_TONE = (0, 2, 4, 6, 8, 10)


def _rotations(steps, names):
    out = {}
    for i, name in enumerate(names):
        if name:
            out[frozenset((s - steps[i]) % 12 for s in steps)] = name
    return out


SCALE_NAMES: Dict[frozenset, str] = {}
SCALE_NAMES.update(_rotations(SCALE_OF["major"], ("major", "Dorian", "Phrygian", "Lydian", "Mixolydian", "Aeolian",
                                                  "Locrian")))
SCALE_NAMES.update(_rotations(SCALE_OF["harmonic minor"], ("harmonic minor", None, None, None, "Phrygian dominant",
                                                           None, None)))
SCALE_NAMES.update(_rotations(SCALE_OF["melodic minor"], ("melodic minor", None, None, "Lydian dominant", None,
                                                          "Locrian natural 9", "altered")))
SCALE_NAMES[frozenset(WHOLE_HALF)] = "whole-half diminished"
SCALE_NAMES[frozenset(WHOLE_TONE)] = "whole tone"


class ResolveError(ValueError):
    """A card or line that cannot be resolved; `field` names where (the route answers 400 with it)."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field} {message}" if field else message)


class BridgeUnavailable(RuntimeError):
    """node is not on PATH, or the bridge process failed: routes that must voice answer 503."""


# ============================================================================================== the bridge
def run_bridge(request: dict) -> List[dict]:
    node = shutil.which("node")
    if not node:
        raise BridgeUnavailable("the voicing bridge is unavailable (node not on PATH)")
    try:
        proc = subprocess.run([node, str(BRIDGE)], input=json.dumps(request), capture_output=True, text=True,
                              encoding="utf-8", timeout=BRIDGE_TIMEOUT_S)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BridgeUnavailable(f"the voicing bridge did not answer ({type(exc).__name__}: {exc})")
    try:
        reply = json.loads(proc.stdout)
    except ValueError:
        raise BridgeUnavailable(f"the voicing bridge failed: {(proc.stderr or proc.stdout).strip()[:300]}")
    if not reply.get("ok"):
        raise ResolveError("", reply.get("error") or "the voicing bridge refused the request")
    return reply["results"]


_BAND_PROBE = {"mtime": None, "has": False}
_BAND_LOCK = threading.Lock()


def bridge_has_band() -> bool:
    """Whether pianocue_voicing.mjs has the band voicer (J1: its runBand). Re-read when the file changes."""
    try:
        mtime = BRIDGE.stat().st_mtime_ns
    except OSError:
        return False
    with _BAND_LOCK:
        if _BAND_PROBE["mtime"] != mtime:
            text = BRIDGE.read_text(encoding="utf-8", errors="replace")
            _BAND_PROBE.update(mtime=mtime, has=bool(re.search(r"\bfunction runBand\s*\(", text)))
        return _BAND_PROBE["has"]


_POOL: Optional[ThreadPoolExecutor] = None


def _pool() -> ThreadPoolExecutor:
    global _POOL
    if _POOL is None:
        _POOL = ThreadPoolExecutor(max_workers=6, thread_name_prefix="jam-bridge")
    return _POOL


# ================================================================================================= keys
def _num(x):
    return int(x) if isinstance(x, float) and x.is_integer() else x


def key_of(name: str, field: str = "key") -> dict:
    k = nashville.parse_key(name) if isinstance(name, str) else None
    if not k:
        raise ResolveError(field, f'must be a key name like "Eb major" or "D minor" (got {name!r:.60})')
    return k


def _spelled(letter: int, pc: int, mode: str) -> str:
    natural = nashville.LETTER_PC[letter]
    acc = (pc - natural + 6) % 12 - 6
    text = nashville.LETTERS[letter] + ("#" * acc if acc > 0 else "b" * -acc)
    if abs(acc) > 1 or text in ("Fb", "E#", "B#"):
        text = (nashville.MAJOR_KEY_NAMES if mode == "major" else nashville.MINOR_KEY_NAMES)[pc]
    return f"{text} {mode}"


def tone_name(slot: dict, role: str, relative_to: str = "root") -> Optional[str]:
    """A landing or check note spelled from the chord's own tones (jam-rulings: "Bb, the b3rd of Gm(add9)"; Cb, not B,
    over Abm(add9); Ebb over Cbm(add9)): the role's letter counted up from the root (or bass) the slot's name spells,
    through nashville's shared speller (_spell_from), never a key-wide sharp or flat table. None when the name does not
    spell that root or bass (a caller may then name the pitch class some other way)."""
    if role not in ROLE_SEMIS or not isinstance(slot, dict):
        return None
    tones = slot.get("tones_pc") or {}
    base_pc = slot.get("bass_pc") if relative_to == "bass" else tones.get("root", slot.get("bass_pc"))
    chord = nashville.parse_chord(slot.get("name"))
    if not isinstance(base_pc, int) or not chord or chord["kind"] != "chord":
        return None
    base = chord["bass"] if relative_to == "bass" and chord["bass"] else chord["root"]
    if nashville._pc(base) != base_pc % 12:
        return None
    pc = (base_pc + ROLE_SEMIS[role]) % 12
    letter = (base[0] + ROLE_STEPS[role]) % 7
    ctx = nashville._key_context(slot.get("key"))
    sp = (letter, nashville._signed(pc - nashville.LETTER_PC[letter]))
    if ctx:
        sp = nashville._spell_from(sp, ROLE_STEPS[role], base, ctx, "tonic")
    return nashville._name(sp) if abs(sp[1]) <= 2 else None


def transpose_key(card_key: str, target: Optional[str]) -> Tuple[str, List[str]]:
    """The card key moved to the target's tonic, keeping the card's mode (a transposition plays the same music)."""
    card = key_of(card_key, "key")
    if target is None or target == card["name"] or target == card_key:
        return card["name"], []
    want = key_of(target, "key")
    if want["mode"] == card["mode"]:
        return want["name"], []
    # another mode on that tonic: named as the page's key tracker names it (C# minor, not Db minor)
    name = nashville.key_name_of(want["tonic"], card["mode"])
    return name, [f"the card is in {card['mode']}, so it plays in {name} (asked for {want['name']})"]


def degree_key(base_key: str, item: str, field: str = "key") -> str:
    """A key item ("6 major", "b3 major") as a degree of base_key, spelled by the degree (DATA 2.3)."""
    m = S.KEY_ITEM_RE.match(item or "")
    if not m:
        raise ResolveError(field, f'must be a degree and a mode, like "6 major" (got {item!r:.60})')
    base = key_of(base_key, field)
    acc_text = m.group(1) or ""
    acc = len(acc_text) if acc_text.startswith("#") else -len(acc_text)
    degree = int(item.strip()[len(acc_text)])
    mode = m.group(2)
    base_sp = nashville._parse_note(base["name"])[0]
    letter = (base_sp[0] + degree - 1) % 7
    pc = (base["tonic"] + MAJOR_STEPS[degree - 1] + acc) % 12
    return _spelled(letter, pc, mode)


def shift_of(card_key: str, key: str) -> int:
    return (key_of(key)["tonic"] - key_of(card_key)["tonic"] + 6) % 12 - 6


def shift_notes(notes: Sequence[int], s: int) -> Tuple[List[int], Optional[str], List[int]]:
    """(notes, fold, dropped): exact notes moved by s semitones, folded an octave to stay inside E1..G7 (DATA 2.6)."""
    out = sorted(n + s for n in notes)
    fold = None
    if out and out[0] < EXACT_LOW:
        out = [n + 12 for n in out]
        fold = "up"
    elif out and out[-1] > EXACT_HIGH:
        out = [n - 12 for n in out]
        fold = "down"
    kept = [n for n in out if S.NOTE_MIN <= n <= S.NOTE_MAX]
    dropped = [n for n in out if n not in kept]
    return sorted(set(kept)), fold, dropped


# ============================================================================================ lines and notes
_NOTE_NAME_RE = re.compile(r"^([A-Ga-g])(#{1,2}|b{1,2})?(-?\d)$")


def note_midi(token: str) -> int:
    t = str(token).strip()
    if re.fullmatch(r"\d{1,3}", t):
        n = int(t)
    else:
        m = _NOTE_NAME_RE.match(t.replace("♭", "b").replace("♯", "#"))
        if not m:
            raise ValueError(f"not a note: {token!r} (use names with octaves like Ab2, or MIDI numbers)")
        acc = m.group(2) or ""
        n = (int(m.group(3)) + 1) * 12 + nashville.LETTER_PC[nashville.LETTERS.index(m.group(1).upper())] + \
            (len(acc) if acc.startswith("#") else -len(acc))
    if not S.NOTE_MIN <= n <= S.NOTE_MAX:
        raise ValueError(f"{token} is off the keyboard (MIDI {S.NOTE_MIN}..{S.NOTE_MAX})")
    return n


def parse_notes(text: str) -> List[int]:
    notes = [note_midi(t) for t in re.split(r"[\s,]+", str(text).strip()) if t]
    if not notes:
        raise ValueError("no notes given")
    return sorted(set(notes))


def midi_name(n: int, flats: bool = True) -> str:
    return f"{(PC_FLAT if flats else PC_SHARP)[n % 12]}{n // 12 - 1}"


def parse_line(text: str) -> List[dict]:
    """The CLI string form (4.1): "1maj9:4 | [6 major] | 1add9:4 | rest:2". Items are separated by "|" (or spaces
    inside a segment); item:beats sets a chord's length (default 4); [degree mode] is a key item; rest:N a rest."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("the chord line is empty")
    items: List[dict] = []
    for seg in text.split("|"):
        seg = seg.strip()
        if not seg:
            continue
        m = re.fullmatch(r"\[\s*(.+?)\s*\]", seg)
        if m:
            items.append({"key": re.sub(r"\s+", " ", m.group(1))})
            continue
        for tok in seg.split():
            mm = re.fullmatch(r"(.+?)(?::(\d+(?:\.\d+)?))?", tok)
            head, beats = mm.group(1), mm.group(2)
            value = _num(float(beats)) if beats is not None else None
            if head == "rest":
                items.append({"rest": value if value is not None else 4})
            else:
                item = {"n": head}
                if value is not None:
                    item["beats"] = value
                items.append(item)
    if not items:
        raise ValueError("the chord line is empty")
    return items


def line_text(items: Sequence[dict]) -> str:
    out = []
    for it in items:
        if "key" in it:
            out.append(f"[{it['key']}]")
        elif "rest" in it:
            out.append(f"rest:{_num(it['rest'])}")
        else:
            label = it.get("n") or "notes"
            out.append(f"{label}:{_num(it.get('beats', 4))}")
    return " | ".join(out)


# ============================================================================================ chord tones
_SUFFIX_ALIASES = (("Δ", "maj"), ("M7", "maj7"), ("min", "m"), ("°7", "dim7"), ("°", "dim"), ("ø7", "m7b5"),
                   ("ø", "m7b5"), ("^", ""), ("(", ""), (")", ""), (",", ""))


def suffix_tones(suffix: str) -> Dict[str, int]:
    """{role: semitones above the root} for a chord suffix ("m11", "maj7#11", "7sus4", "6/9"), or ValueError."""
    s = suffix or ""
    for a, b in _SUFFIX_ALIASES:
        s = s.replace(a, b)
    if s.startswith("-"):
        s = "m" + s[1:]
    third, fifth, sus = 4, 7, None
    seventh = sixth = ninth = eleventh = thirteenth = None
    dim = major7 = power = False
    if s.startswith("m") and not s.startswith("maj"):
        third, s = 3, s[1:]
    elif s.startswith("dim"):
        third, fifth, dim, s = 3, 6, True, s[3:]
    elif s.startswith("aug") or s.startswith("+"):
        fifth, s = 8, s[3:] if s.startswith("aug") else s[1:]
    if s.startswith("maj"):
        major7, s = True, s[3:]
    m = re.match(r"6/9|69|13|11|9|7|6|5", s)
    ext = m.group(0) if m else ""
    s = s[len(ext):]
    seven = 11 if major7 else (9 if dim else 10)
    if ext in ("6/9", "69"):
        sixth, ninth = 9, 2
    elif ext == "6":
        sixth = 9
    elif ext == "7":
        seventh = seven
    elif ext == "9":
        seventh, ninth = seven, 2
    elif ext == "11":
        seventh, ninth, eleventh = seven, 2, 5
    elif ext == "13":
        seventh, ninth, thirteenth = seven, 2, 9
    elif ext == "5":
        power, third = True, None
    elif major7:
        seventh = 11
    while s:
        mm = re.match(r"sus4|sus2|sus|add9|add11|add13|add2|add4|add6|b5|#5|b9|#9|#11|b13|13|11|9|alt|no3|no5|omit3|"
                      r"omit5", s)
        if not mm:
            raise ValueError(f"cannot read the chord suffix {suffix!r}")
        tok, s = mm.group(0), s[len(mm.group(0)):]
        if tok in ("sus4", "sus", "add4"):
            if tok == "add4":
                eleventh = 5
            else:
                third, sus = None, 5
        elif tok == "sus2":
            third, sus = None, 2
        elif tok in ("add9", "add2", "9"):
            ninth = 2
        elif tok in ("add11", "11"):
            eleventh = 5
        elif tok in ("add13", "13"):
            thirteenth = 9
        elif tok == "add6":
            sixth = 9
        elif tok == "b5":
            fifth = 6
        elif tok == "#5":
            fifth = 8
        elif tok == "b9":
            ninth = 1
        elif tok == "#9":
            ninth = 3
        elif tok == "#11":
            eleventh = 6
        elif tok == "b13":
            thirteenth = 8
        elif tok == "alt":
            ninth, thirteenth, fifth = 1, 8, None
        elif tok in ("no3", "omit3"):
            third = None
        elif tok in ("no5", "omit5"):
            fifth = None
    out: Dict[str, int] = {"root": 0}
    if third is not None:
        out["third"] = third
    if sus is not None:
        out["sus"] = sus
    if fifth is not None:
        out["fifth"] = fifth
    if sixth is not None:
        out["sixth"] = sixth
    if seventh is not None:
        out["seventh"] = seventh
    if ninth is not None:
        out["ninth"] = ninth
    if eleventh is not None:
        out["eleventh"] = eleventh
    if thirteenth is not None:
        out["thirteenth"] = thirteenth
    del power
    return out


def chord_facts(name: Optional[str]) -> Optional[dict]:
    """{root_pc, bass_pc, semis, tones_pc, suffix} for a chord name, or None when it is not a readable chord."""
    parsed = nashville.parse_chord(name) if name else None
    if not parsed or parsed["kind"] != "chord":
        return None
    try:
        semis = suffix_tones(parsed["suffix"])
    except ValueError:
        return None
    root = nashville._pc(parsed["root"])
    bass = nashville._pc(parsed["bass"]) if parsed["bass"] else root
    return {"root_pc": root, "bass_pc": bass, "semis": semis, "suffix": parsed["suffix"],
            "tones_pc": {role: (root + v) % 12 for role, v in semis.items()}}


def _interval_role(iv: int) -> str:
    return {0: "root", 1: "ninth", 2: "ninth", 3: "third", 4: "third", 5: "eleventh", 6: "eleventh", 7: "fifth",
            8: "thirteenth", 9: "thirteenth", 10: "seventh", 11: "seventh"}[iv % 12]


# ================================================================================================ scales
def _rel(pcs, root) -> frozenset:
    return frozenset((p - root) % 12 for p in pcs)


def _is_dominant(semis: Dict[str, int]) -> bool:
    return semis.get("third") == 4 and semis.get("seventh") == 10


def slot_scale(slot_pcs: Sequence[int], root: int, semis: Dict[str, int], section: dict, section_scale: str,
               next_root: Optional[int]) -> Tuple[List[int], str]:
    """(scale pcs as a set-like list, class) for one slot in its section (MUSIC 9.5)."""
    from arsenal.practice import classify  # the practice verbs' own rules; imported late (it is a large module)
    tonic, mode = section["tonic"], section["mode"]
    own = "major" if mode == "major" else "natural minor"
    rel = _rel(slot_pcs, tonic)
    cls = classify(list(slot_pcs), root, {"key": section["name"], "tonic": tonic, "mode": mode}, next_root)
    klass = cls["class"]  # the chord's relation to its key, whichever scale it is heard in
    if rel <= set(SCALE_OF[section_scale]):
        return [(tonic + i) % 12 for i in SCALE_OF[section_scale]], klass
    fits = cls.get("fits") or []
    steps: Sequence[int]
    base = tonic
    if klass == "diatonic":
        home = ("major",) if mode == "major" else ("natural minor", "harmonic minor", "melodic minor")
        steps = SCALE_OF[next((s for s in home if s in fits), own)]
    elif klass == "borrowed":
        parallel = ("natural minor", "harmonic minor") if mode == "major" else ("major",)
        steps = SCALE_OF[next((s for s in parallel if s in fits), parallel[0])]
    elif klass == "modal":
        steps = SCALE_OF.get(cls.get("mode") or "", SCALE_OF[own])
    elif klass == "secondary dominant":
        if str(cls.get("target", "")).endswith("m"):
            steps, base = PHRYGIAN_DOMINANT, root
        else:
            own_pcs = {(tonic + i) % 12 for i in SCALE_OF[own]}
            own_pcs.discard((root + 3) % 12)
            own_pcs.add((root + 4) % 12)
            return sorted(own_pcs), klass
    else:
        base = root
        if semis.get("sus") is not None:
            steps = SCALE_OF["Mixolydian"]
        elif semis.get("third") == 3 and semis.get("fifth") == 6 and semis.get("seventh") == 9:
            steps = WHOLE_HALF
        elif semis.get("third") == 3 and semis.get("fifth") == 6:
            steps = LOCRIAN_NAT9
        elif semis.get("third") == 3 and semis.get("sixth") is not None and semis.get("seventh") is None:
            steps = SCALE_OF["melodic minor"]
        elif semis.get("third") == 3:
            steps = SCALE_OF["Dorian"]
        elif semis.get("fifth") == 8:
            steps = WHOLE_TONE
        elif _is_dominant(semis):
            steps = LYDIAN_DOMINANT
        else:
            steps = SCALE_OF["Lydian"]
    return [(base + i) % 12 for i in steps], klass


def _complete_scale(scale: Sequence[int], chord_pcs: Sequence[int], root: int, semis: Dict[str, int]) -> List[int]:
    """Any chord tone missing from the scale replaces the scale note beside it with the same letter (MUSIC 9.5)."""
    out = set(scale)
    natural = {"third": 4, "fifth": 7, "sixth": 9, "seventh": 10, "ninth": 2, "eleventh": 5, "thirteenth": 9}
    by_pc = {(root + v) % 12: (role, v) for role, v in semis.items()}
    for pc in chord_pcs:
        if pc in out:
            continue
        role, v = by_pc.get(pc, (None, None))
        order = (-1, 1)
        if role in natural and v is not None and v < natural[role]:
            order = (1, -1)
        for d in order:
            nb = (pc + d) % 12
            if nb in out and nb not in chord_pcs:
                out.discard(nb)
                break
        out.add(pc)
    return sorted(out)


def scale_name(scale: Sequence[int], root: int, root_text: str, section: dict) -> str:
    name = SCALE_NAMES.get(_rel(scale, root))
    if name is None:
        return f"{root_text} {len(scale)}-note scale"
    if name == "Aeolian" and root == section["tonic"] and section["mode"] == "minor":
        return f"{root_text} minor"
    return f"{root_text} {name}"


# ======================================================================================= the stand-in band
def _upper_order(semis: Dict[str, int], slash: bool) -> Tuple[List[str], List[str]]:
    """(full roles, comp roles) in the order MUSIC 4.2 requires them."""
    third = "third" if "third" in semis else ("sus" if "sus" in semis else None)
    seventh = "seventh" if "seventh" in semis else ("sixth" if "sixth" in semis else None)
    altered = [r for r in ("ninth", "eleventh", "thirteenth", "fifth")
               if r in semis and ((r == "ninth" and semis[r] in (1, 3)) or (r == "eleventh" and semis[r] == 6) or
                                  (r == "thirteenth" and semis[r] == 8) or (r == "fifth" and semis[r] in (6, 8)))]
    named = [r for r in ("ninth", "eleventh", "thirteenth") if r in semis and r not in altered]
    full = [r for r in [third, seventh] + altered + named if r]
    comp = [r for r in [third, seventh] + altered[:1] if r]
    if slash:
        full.append("root")
        comp.append("root")
    return full, comp


def _place(pcs_roles: List[Tuple[int, str]], low: int) -> Tuple[List[int], List[str]]:
    placed = sorted((low + (pc - low) % 12, role) for pc, role in pcs_roles)
    if len(placed) >= 3 and placed[-1][0] - placed[-2][0] == 1:  # never a minor 2nd between the top two voices
        top = placed.pop()
        placed = sorted(placed + [(top[0] - 12, top[1])])
    return [n for n, _ in placed], [r for _, r in placed]


def stub_band(facts: Sequence[dict]) -> List[dict]:
    """A stand-in for the bridge's band style: {full, comp, bass: notes; roles: {full, comp, bass}} per slot. The bass
    sits on the bass pitch class in C2..B2; full's upper voices in F3..E4, comp's in E3..Eb4 (inside the 10.1 limits,
    above every low-interval limit); an upper_same slot keeps the previous upper voices and moves only the bass."""
    out: List[dict] = []
    prev = None
    for i, f in enumerate(facts):
        bass_pc = f["bass_pc"]
        # a shape the next slots keep over a moving bass holds its 5th, so it still names the chord over each bass
        # (MUSIC 1.3: without F, Bbm11/Gb reads Ab11/Gb)
        held = i + 1 < len(facts) and bool(facts[i + 1].get("upper_same"))
        if f.get("upper_same") and prev is not None:
            ceiling = min([prev["full"][1] if len(prev["full"]) > 1 else 51,
                           prev["comp"][1] if len(prev["comp"]) > 1 else 51, 51])
            options = [p for p in range(S.BASS_RANGE[0], S.BASS_RANGE[1] + 1) if p % 12 == bass_pc and p < ceiling]
            bass = min(options, key=lambda p: (abs(p - prev["bass"]), p)) if options else 36 + bass_pc
            v = {"bass": bass, "full": [bass] + prev["full"][1:], "comp": [bass] + prev["comp"][1:],
                 "roles": {"full": ["bass"] + prev["roles"]["full"][1:], "comp": ["bass"] + prev["roles"]["comp"][1:],
                           "bass": ["bass"]}}
            out.append(v)
            prev = v
            continue
        bass = 36 + bass_pc
        semis, tones = f.get("semis") or {}, f.get("tones_pc") or {}
        if semis:
            full_roles, comp_roles = _upper_order(semis, f["root_pc"] != bass_pc)

            def pick(roles, fill):
                chosen, seen = [], set()
                for role in roles + fill:
                    pc = tones.get(role)
                    if pc is None or pc in seen:
                        continue
                    if pc == bass_pc and not (role == "root" and len(chosen) < 2):
                        continue
                    chosen.append((pc, role))
                    seen.add(pc)
                return chosen

            full = pick(full_roles, ["fifth"] if held else [])
            if len(full) < 4:
                full = pick(full_roles, ["fifth", "root"])
            full = full[:6]
            comp = pick(comp_roles, [])
            if len(comp) < 2:
                comp = pick(comp_roles, ["fifth", "root"])
            comp = comp[:4]
        else:
            pcs = [pc for pc in (f.get("note_pcs") or []) if pc != bass_pc]
            full = [(pc, _interval_role(pc - bass_pc)) for pc in dict.fromkeys(pcs)][:5]
            comp = full[:3]
        fn, fr = _place(full, 53)
        cn, cr = _place(comp, 52)
        v = {"bass": bass, "full": [bass] + fn, "comp": [bass] + cn,
             "roles": {"full": ["bass"] + fr, "comp": ["bass"] + cr, "bass": ["bass"]}}
        out.append(v)
        prev = v
    return out


# ============================================================================================== resolver
class Resolver:
    def __init__(self, bridge: Callable[[dict], List[dict]] = run_bridge, band: Optional[bool] = None,
                 cache_size: int = CACHE_SIZE):
        """bridge: a callable taking a bridge request and returning its results (tests pass a fake). band: True or
        False forces the bridge's band style on or off; None asks the bridge file (bridge_has_band)."""
        self._bridge = bridge
        self._band = band
        self._cache: "OrderedDict[tuple, str]" = OrderedDict()
        self._cache_size = cache_size
        self._lock = threading.Lock()
        self.stats = {"hits": 0, "misses": 0}

    # ------------------------------------------------------------------------------------------ public
    def resolve(self, card: dict, key: Optional[str] = None, variant: Optional[str] = None,
                backing: Optional[str] = None, voicing: Optional[str] = None, slot: Optional[int] = None) -> dict:
        band = self._band_on()
        ck = ("card", card.get("id"), card.get("rev"), card.get("updated_at"), key, variant, backing, voicing, slot,
              band, json.dumps(card, sort_keys=True) if card.get("rev") is None else None)
        return self._cached(ck, lambda: self._build(card, key, variant, backing, voicing, slot, band, True))

    def resolve_chords(self, items: List[dict], key: str, meter: int = 4, backing: str = "comp",
                       voicing: str = "spread", slot: Optional[int] = None, title: Optional[str] = None) -> dict:
        try:
            S._chord_line(items, "chords")
        except S.JamSchemaError as exc:
            raise ResolveError(exc.field, str(exc)[len(exc.field):].strip())
        if backing not in S.BACKINGS:
            raise ResolveError("backing", f"must be one of {', '.join(S.BACKINGS)} (got {backing!r})")
        pseudo = {"key": key_of(key)["name"], "chords": items, "tempo": {"bpm": 66, "beats_per_bar": meter},
                  "voicing": {"style": voicing}, "backing": backing}
        band = self._band_on()
        ck = ("chords", json.dumps(items, sort_keys=True), key, meter, backing, voicing, slot, band)
        return self._cached(ck, lambda: self._build(pseudo, None, None, backing, voicing, slot, band, False))

    def page_reads(self, card: dict) -> List[dict]:
        """What the page names each chord of every line, in the card key and voicing (DATA 2.7)."""
        out = []
        lines = ([None] if card.get("chords") else []) + [v["id"] for v in card.get("variants") or []]
        style = S.card_settings(card)["voicing"]["style"]
        for variant in lines:
            d = self.resolve(dict(card, rev=None, page_reads=[]), variant=variant)
            items = _line_items(card, variant)
            chords = [it for it in items if "key" not in it and "rest" not in it]
            for sl, it in zip(d["slots"], chords):
                entry = {"variant": variant, "slot": sl["i"], "key": sl["key"],
                         "voicing": "notes" if sl["exact"] else (it.get("voicing") or style),
                         "notes": sl["voicings"]["play"], "name": sl["page_reads"]["name"],
                         "number": sl["page_reads"]["number"], "match": sl["page_reads"]["match"]}
                if sl["page_reads"]["match"] not in ("exact", "enharmonic", "notes") and sl["page_reads"]["name"]:
                    entry["note"] = f"your screen calls this {sl['page_reads']['name']}: the same notes"
                out.append(entry)
        return out

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    # ------------------------------------------------------------------------------------------ helpers
    def _band_on(self) -> bool:
        return bridge_has_band() if self._band is None else bool(self._band)

    def _cached(self, ck, build) -> dict:
        with self._lock:
            hit = self._cache.get(ck)
            if hit is not None:
                self._cache.move_to_end(ck)
                self.stats["hits"] += 1
                return json.loads(hit)
        d = build()
        text = json.dumps(d, separators=(",", ":"))
        with self._lock:
            self.stats["misses"] += 1
            self._cache[ck] = text
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return json.loads(text)

    def _call(self, request: dict, field: str) -> List[dict]:
        try:
            return self._bridge(request)
        except ResolveError as exc:
            raise ResolveError(field, str(exc)) from None

    # ------------------------------------------------------------------------------------------ build
    def _build(self, card: dict, key: Optional[str], variant: Optional[str], backing: Optional[str],
               voicing: Optional[str], slot: Optional[int], band: bool, is_card: bool) -> dict:
        settings = S.card_settings(card)
        k_name, warnings = transpose_key(card["key"], key)
        card_key = key_of(card["key"])["name"]
        style = voicing or settings["voicing"]["style"]
        if style not in S.VOICING_STYLES:
            raise ResolveError("voicing", f"must be one of {', '.join(S.VOICING_STYLES)} (got {style!r})")
        backing = backing or settings["backing"]
        if backing not in S.BACKINGS:
            raise ResolveError("backing", f"must be one of {', '.join(S.BACKINGS)} (got {backing!r})")
        items, meter, where, used_variant = _pick_line(card, variant, settings)
        s = shift_of(card_key, k_name)

        # sections and slots
        sections = [{"i": 0, "key": k_name, "from_beat": 0}]
        raw: List[dict] = []
        beat = 0.0
        for idx, it in enumerate(items):
            at = f"{where[idx]}"
            if "key" in it:
                nk = degree_key(k_name, it["key"], f"{at}.key")
                if beat == sections[-1]["from_beat"] and not any(r["section"] == len(sections) - 1 for r in raw):
                    sections[-1]["key"] = nk
                else:
                    sections.append({"i": len(sections), "key": nk, "from_beat": _num(beat)})
            elif "rest" in it:
                beat += it["rest"]
            else:
                raw.append({"item": it, "at": at, "at_beat": beat, "beats": it.get("beats", 4),
                            "section": len(sections) - 1})
                beat += it.get("beats", 4)
        total = beat
        if slot is not None:
            if not isinstance(slot, int) or isinstance(slot, bool) or not 0 <= slot < len(raw):
                raise ResolveError("slot", f"must be a chord slot 0..{len(raw) - 1} (got {slot!r})")
            one = raw[slot]
            sections = [{"i": 0, "key": sections[one["section"]]["key"], "from_beat": 0}]
            raw = [dict(one, at_beat=0.0, section=0)]
            total = one["beats"]
        bars = card.get("bars") if (is_card and used_variant is None and slot is None and card.get("bars")) else None
        bars = bars or max(1, math.ceil(total / meter))
        cycle = int(bars * meter)
        sections = [sec for sec in sections if sec["from_beat"] < cycle and
                    any(r["section"] == sec["i"] for r in raw)]
        renumber = {sec["i"]: i for i, sec in enumerate(sections)}
        for i, sec in enumerate(sections):
            sec["i"] = i
        for r in raw:
            r["section"] = renumber[r["section"]]
        sections[0]["from_beat"] = 0

        # bridge calls: numbers per (section, style), exact notes per section, all in parallel
        jobs = {}
        for i, r in enumerate(raw):
            it = r["item"]
            sec_key = sections[r["section"]]["key"]
            if it.get("n"):
                st = it.get("voicing") or style
                jobs.setdefault(("n", r["section"], st), []).append(i)
            if it.get("notes"):
                notes, fold, dropped = shift_notes(it["notes"], s)
                if not notes:
                    raise ResolveError(f"{r['at']}.notes", f"has no note left on the keyboard in {k_name}")
                r.update(exact_notes=notes, fold=fold, dropped=dropped)
                jobs.setdefault(("notes", r["section"], None), []).append(i)
            del sec_key
        voice_lead = bool(settings["voicing"].get("voice_lead"))
        octave = settings["voicing"].get("octave")
        futures = {}
        for (kind, sec, st), idxs in jobs.items():
            if kind == "n":
                req = {"items": [raw[i]["item"]["n"] for i in idxs], "key": sections[sec]["key"], "voicing": st,
                       "octave": octave, "voice_lead": voice_lead, "minor": "tonic"}
            else:
                req = {"items": [" ".join(str(n) for n in raw[i]["exact_notes"]) for i in idxs],
                       "key": sections[sec]["key"], "voicing": "close", "octave": None, "voice_lead": False,
                       "minor": "tonic"}
            futures[(kind, sec, st)] = _pool().submit(self._call, req, raw[idxs[0]]["at"])
        # the band request needs only numbers, keys and exact notes, so it runs beside the calls above
        band_future = _pool().submit(self._bridge, self._band_request(raw, sections)) if band else None
        for jk, fut in futures.items():
            results = fut.result()
            for i, res in zip(jobs[jk], results):
                if res.get("error"):
                    field = f"{raw[i]['at']}.{'n' if jk[0] == 'n' else 'notes'}"
                    raise ResolveError(field, f"cannot be voiced: {res['error']}")
                raw[i]["num" if jk[0] == "n" else "read"] = res

        # per-slot facts
        for r in raw:
            it = r["item"]
            num, read = r.get("num"), r.get("read")
            name = (num or read)["name"]
            if it.get("name") and k_name == card_key and it.get("notes"):
                name = it["name"]
            facts = None
            if num and isinstance(num.get("tones_pc"), dict) and isinstance(num.get("bass_pc"), int):
                facts = chord_facts(num["name"]) or {"root_pc": num["bass_pc"], "semis": {}}
                facts = dict(facts, tones_pc=num["tones_pc"], bass_pc=num["bass_pc"],
                             root_pc=num["tones_pc"].get("root", facts["root_pc"]))
            elif num:
                facts = chord_facts(num["name"])
            play = r.get("exact_notes") or (num or {}).get("notes")
            if facts is None:
                pcs = list(dict.fromkeys(n % 12 for n in sorted(play)))
                facts = {"root_pc": pcs[0], "bass_pc": pcs[0], "semis": {}, "tones_pc": {}}
                r["note_pcs"] = pcs
            r["facts"] = facts
            r["name"] = name
            r["play"] = sorted(play)

        # band voicings
        facts_list = [{"bass_pc": r["facts"]["bass_pc"], "root_pc": r["facts"]["root_pc"],
                       "semis": r["facts"].get("semis") or {}, "tones_pc": r["facts"].get("tones_pc") or {},
                       "upper_same": r["item"].get("upper") == "same" and i > 0, "note_pcs": r.get("note_pcs")}
                      for i, r in enumerate(raw)]
        voiced = self._band_parse(band_future, facts_list) if band_future is not None else None
        from_bridge = voiced is not None
        if voiced is None:
            voiced = stub_band(facts_list)
            warnings.append(STUB_WARNING)

        # scales per section
        slots: List[dict] = []
        sec_scale = {}
        for sec in sections:
            k = key_of(sec["key"])
            sec["_k"] = {"name": k["name"], "tonic": k["tonic"], "mode": k["mode"]}
            members = [r for r in raw if r["section"] == sec["i"]]
            own = "major" if k["mode"] == "major" else "natural minor"
            counts = {nm: sum(1 for r in members if _rel(_chord_pcs(r), k["tonic"]) <= set(steps))
                      for nm, steps in SECTION_SCALES}
            best = max(counts.values())
            sec_scale[sec["i"]] = own if counts[own] == best else next(nm for nm, _ in SECTION_SCALES
                                                                      if counts[nm] == best)

        pb = settings["playback"]
        for i, r in enumerate(raw):
            it, facts, v = r["item"], r["facts"], voiced[i]
            sec = sections[r["section"]]
            chord_pcs = _chord_pcs(r)
            nxt = raw[i + 1] if i + 1 < len(raw) and raw[i + 1]["section"] == r["section"] else None
            scale, klass = slot_scale(chord_pcs, facts["root_pc"], facts.get("semis") or {}, sec["_k"],
                                      sec_scale[sec["i"]], nxt["facts"]["root_pc"] if nxt else None)
            scale = _complete_scale(scale, chord_pcs, facts["root_pc"], facts.get("semis") or {})
            scale = sorted(scale, key=lambda p: (p - facts["root_pc"]) % 12)
            root_text = _root_text(r["name"], facts["root_pc"], sec["_k"])
            # an exact chord plays its own notes, so the styled voicing's warnings do not apply to it
            slot_warnings = [] if it.get("notes") else list((r.get("num") or {}).get("warnings") or [])
            if r.get("fold"):
                slot_warnings.append(f"the exact notes moved an octave {r['fold']} to stay on the keyboard in {k_name}")
            if r.get("dropped"):
                slot_warnings.append(f"{len(r['dropped'])} exact note(s) fell off the keyboard in {k_name}")
            if it.get("upper") == "same" and i == 0 and slot is not None:
                slot_warnings.append("upper same needs the chord before it; played as written here")
            exact = bool(it.get("notes"))
            if exact:
                pr = _exact_reads(r)
                omits = [role for role, pc in (facts.get("tones_pc") or {}).items()
                         if pc not in {n % 12 for n in r["play"]}]
            else:
                rt = r["num"].get("roundtrip") or {}
                pr = {"name": rt.get("page_name") or rt.get("detected"), "number": rt.get("page_number"),
                      "match": rt.get("match") or "unnamed"}
                omits = list(rt.get("omits") or [])
            entry = {"i": i, "section": r["section"], "at_beat": _num(float(r["at_beat"])),
                     "beats": _num(float(r["beats"])), "n": it.get("n"), "name": (r["name"] or "")[:60] or None,
                     "key": sec["key"], "tones_pc": facts.get("tones_pc") or {}, "bass_pc": facts["bass_pc"],
                     "chord_pcs": chord_pcs, "scale": scale,
                     "scale_name": scale_name(scale, facts["root_pc"], root_text, sec["_k"])[:40], "class": klass,
                     "voicings": {"play": r["play"], "full": v["full"], "comp": v["comp"], "bass": [v["bass"]]},
                     "roles": v["roles"], "exact": exact, "upper_same": facts_list[i]["upper_same"],
                     "vel": it.get("vel", pb["velocity"]), "arp_ms": it.get("arp_ms", pb["arpeggio_ms"]),
                     "say": it.get("say"), "page_reads": pr, "warnings": slot_warnings,
                     "hold": it.get("hold", pb["hold"]), "omits": [o for o in omits if o in S.TONE_ROLES]}
            if v.get("reads_as"):
                entry["reads_as"] = str(v["reads_as"])[:60]
            band_warnings = [w for w in v.get("warnings") or [] if w not in entry["warnings"]]
            entry["warnings"] = entry["warnings"] + band_warnings
            r["band_warnings"] = band_warnings
            slots.append(entry)
        for sec in sections:
            sec.pop("_k", None)

        d = {"api": DEF_API,
             "card": ({"id": card["id"], "rev": card["rev"] if card.get("rev") else 1, "title": card["title"],
                       "variant": used_variant} if is_card else None),
             "key": k_name, "beats_per_bar": meter, "cycle_beats": cycle, "backing": backing,
             "sections": sections, "slots": slots, "warnings": list(dict.fromkeys(warnings))}
        landing = card.get("landing") if is_card else None
        if landing and landing.get("variant") == used_variant and slot is None:
            li = landing.get("slot", len(slots) - 1)
            if 0 <= li < len(slots):
                sl = slots[li]
                base = sl["bass_pc"] if landing.get("relative_to") == "bass" else \
                    sl["tones_pc"].get("root", sl["bass_pc"])
                d["landing"] = {"slot": li, "role": landing["role"], "relative_to": landing.get("relative_to", "root"),
                                "pc": (base + ROLE_SEMIS[landing["role"]]) % 12, "pull": landing["pull"]}
                note = tone_name(sl, landing["role"], d["landing"]["relative_to"])
                if note:
                    d["landing"]["note"] = note  # spelled from the chord's own tones: the deck and the riff name it so
        try:
            S.validate_def(d)
        except S.JamSchemaError as exc:
            if not from_bridge:
                raise ResolveError("def", f"came out malformed ({exc}); this is a resolver bug") from None
            # the bridge's band voicings broke the frozen def contract (registers, upper same): the stand-in voices
            # the line instead, and the def says why, so a bridge change never takes Loop and Try down
            for sl, r, v in zip(d["slots"], raw, stub_band(facts_list)):
                sl["voicings"].update(full=v["full"], comp=v["comp"], bass=[v["bass"]])
                sl["roles"] = v["roles"]
                sl.pop("reads_as", None)
                sl["warnings"] = [w for w in sl["warnings"] if w not in r.get("band_warnings", [])]
            d["warnings"] += [f"the bridge's band voicings did not fit the def ({exc})", STUB_WARNING]
            try:
                S.validate_def(d)
            except S.JamSchemaError as exc2:
                raise ResolveError("def", f"came out malformed ({exc2}); this is a resolver bug") from None
        return d

    @staticmethod
    def _band_request(raw: List[dict], sections: List[dict]) -> dict:
        """The bridge's band voicer over the whole line as a ring (J1, jam-spec 10.1). Request: {items: [{text, key,
        upper?}], key: null, voicing: "band", line: "ring"}, one item per slot: its number in its section's key, or
        its exact notes when it has no number, with upper "same" where the card says so (never on the line's first
        slot). Each result carries band.{full, comp, bass}.{notes, roles}, reads_as and warnings."""
        items = []
        for i, r in enumerate(raw):
            text = r["item"]["n"] if r["item"].get("n") else " ".join(str(n) for n in r["exact_notes"])
            item = {"text": text, "key": sections[r["section"]]["key"]}
            if r["item"].get("upper") == "same" and i > 0:
                item["upper"] = "same"
            items.append(item)
        return {"items": items, "key": None, "voicing": "band", "octave": None, "voice_lead": False,
                "minor": "tonic", "line": "ring"}

    @staticmethod
    def _band_parse(future, facts: List[dict]) -> Optional[List[dict]]:
        """The band results read into voicings. An item error (a cluster the band cannot voice), a missing field or an
        older bridge returns None, and the stand-in voices the line."""
        try:
            results = future.result()
            out = []
            for f, res in zip(facts, results):
                if res.get("error"):
                    return None
                b = res["band"]
                full, comp, bass = b["full"], b["comp"], b["bass"]
                v = {"bass": bass["notes"][0], "full": sorted(full["notes"]), "comp": sorted(comp["notes"]),
                     "roles": {"full": list(full["roles"]), "comp": list(comp["roles"]), "bass": ["bass"]},
                     "reads_as": res.get("reads_as"), "warnings": list(res.get("warnings") or [])}
                if v["full"][0] % 12 != f["bass_pc"] or len(v["roles"]["full"]) != len(v["full"]):
                    return None
                out.append(v)
            return out if len(out) == len(facts) else None
        except (BridgeUnavailable, ResolveError, KeyError, TypeError, IndexError, ValueError):
            return None


def _chord_pcs(r: dict) -> List[int]:
    facts = r["facts"]
    tones = facts.get("tones_pc") or {}
    if tones:
        pcs = list(dict.fromkeys(tones.values()))
        if facts["bass_pc"] not in pcs:
            pcs.append(facts["bass_pc"])
        return pcs
    return list(r.get("note_pcs") or [facts["bass_pc"]])


def _root_text(name: Optional[str], root_pc: int, k: dict) -> str:
    parsed = nashville.parse_chord(name) if name else None
    if parsed and parsed.get("root") and nashville._pc(parsed["root"]) == root_pc:
        return nashville._name(parsed["root"])
    flats = nashville.bias_of(k["tonic"], k["mode"]) <= 0
    return (PC_FLAT if flats else PC_SHARP)[root_pc]


def _exact_reads(r: dict) -> dict:
    read = r["read"]
    rt = read.get("roundtrip") or {}
    page_name, page_number = rt.get("page_name") or read.get("name"), rt.get("page_number") or read.get("number")
    chord = r.get("num")
    if not chord:
        return {"name": page_name, "number": page_number, "match": "notes" if page_name else "unnamed"}
    if not page_name:
        return {"name": None, "number": None, "match": "unnamed"}
    if page_name == chord["name"]:
        match = "exact"
    else:
        a, b = chord_facts(page_name), chord_facts(chord["name"])
        same = a and b and a["root_pc"] == b["root_pc"] and a["bass_pc"] == b["bass_pc"] and \
            set(a["tones_pc"].values()) == set(b["tones_pc"].values())
        match = "enharmonic" if same else "equivalent"
    return {"name": page_name, "number": page_number, "match": match}


def _line_items(card: dict, variant: Optional[str]) -> List[dict]:
    if variant is None:
        return list(card.get("chords") or [])
    for v in card.get("variants") or []:
        if v["id"] == variant:
            return ([{"key": v["key"]}] if v.get("key") else []) + list(v["chords"])
    return []


def _pick_line(card: dict, variant: Optional[str], settings: dict):
    """(items, meter, field path per item, variant id or None) for the line to resolve."""
    meter = settings["tempo"]["beats_per_bar"]
    variants = card.get("variants") or []
    if variant is None and not card.get("chords") and variants:
        variant = variants[0]["id"]
    if variant is None:
        items = list(card.get("chords") or [])
        if not items:
            raise ResolveError("chords", "is empty: the card has no line to play")
        return items, meter, [f"chords[{i}]" for i in range(len(items))], None
    if variant == "all":
        if not variants:
            return _pick_line(card, None, settings)
        items, where = [], []
        keyed = False
        for vi, v in enumerate(variants):
            if vi:
                items.append({"rest": meter})
                where.append(f"variants[{vi}]")
            if v.get("key") or keyed:
                items.append({"key": v.get("key") or f"1 {key_of(card['key'])['mode']}"})
                where.append(f"variants[{vi}].key")
                keyed = bool(v.get("key"))
            for ci, it in enumerate(v["chords"]):
                items.append(it)
                where.append(f"variants[{vi}].chords[{ci}]")
        return items, meter, where, None
    for vi, v in enumerate(variants):
        if v["id"] == variant:
            vmeter = (v.get("tempo") or {}).get("beats_per_bar", meter)
            items = ([{"key": v["key"]}] if v.get("key") else []) + list(v["chords"])
            where = ([f"variants[{vi}].key"] if v.get("key") else []) + \
                [f"variants[{vi}].chords[{ci}]" for ci in range(len(v["chords"]))]
            return items, vmeter, where, variant
    raise ResolveError("variant", f"names variant {variant!r}, which the card does not have")
