"""Validators for the jam contracts: the card, the resolved def, the run, its event lines and the ack (jam-spec section 4).

Frozen in phase J0 (jam-spec 13.1 rule 3): later phases read these shapes and change them only through the conductor.

Every validator raises JamSchemaError, whose `field` is the path of the first field that is wrong ("chords[1].beats",
"segments[2].epoch_ms", "landing.pull") and whose message starts with that path, so a route answers 400 naming the
field. Unknown fields are refused wherever a shape is listed here, as pianocue.validate_cue does, so typos surface.
`source` (provenance) is the one open object: past its `kind` it carries whatever its writer recorded.

  validate_card(card, stored=False) -> dict   arsenal.jam.card/v0 (4.1, DATA 2.2-2.9). stored=True also requires the
                                              server's fields (rev, source, created_at, updated_at, updated_by).
                                              Defaults are not filled in: a stored card keeps what its author wrote;
                                              card_settings(card) gives the effective values.
  validate_def(d) -> dict                     arsenal.jam.def/v0 (4.2), computed by resolve, never stored in a card
  validate_run(run) -> dict                   arsenal.jam.run/v0 (4.3); segments are checked against the tempo map
  validate_run_event(line) -> dict            one line of runs/<run>/events.jsonl (start, launch, ack, change, mark, stop)
  validate_ack(ack) -> dict                   POST .../ack (4.3); returns the ack with its defaults filled in
  validate_seed(doc), validate_seed_moments(doc)   arsenal/jam/seed/deck-v1.json and its git-ignored moments file (12)

Two optional card fields beyond jam-spec 4.1 come from the house ideas (house-ideas/vandor-integration.md, Heimdall):

  landing  {variant?, slot?, role, relative_to?, pull}   the note a loop pass leaves unresolved on purpose, and one
           line naming its pull ("D, the #11, floats over Ab and leans up to Eb"). `role` and `relative_to` read as
           in checks, so the note moves with the key; `slot` defaults to the line's last chord. A resolved def may
           carry it as {slot, role, relative_to, pc, pull}.
  pair     {role: question|answer, with: <card id>}      question and answer cards: the question lands on a colour,
           the answer starts where it left off and goes home. Both cards name each other (pair_problems checks a
           set of cards).

Helpers other phases share: card_settings (4.1 defaults), line_beats and chord_count (a chord line's length and its
slot count), card_texts and wording_problems (the section 12 wording rule), pair_problems.
"""
from __future__ import annotations

import copy
import json
import math
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from arsenal import nashville
from arsenal.jam import CARD_API, DEF_API, RUN_API, SEED_API, SEED_MOMENTS_API, tempomap
from arsenal.performance import SESSION_PATTERN

# ================================================================================================= vocabulary
GROUPS = ("moves", "try", "kept")
KINDS = ("chord", "progression", "loop", "concept", "moment")
GROOVES_V1 = ("hold", "ballad", "pulse")
GROOVES = GROOVES_V1 + ("swell", "arp", "gospel")          # a v2 groove on a v1 page plays ballad (4.1)
BACKINGS_V1 = ("full", "comp", "bass")
BACKINGS = BACKINGS_V1 + ("pad",)                           # pad is v2
VOICING_STYLES = ("close", "open", "spread", "drop2", "shell")
FEELS = ("straight", "rubato", "half-time")                 # v1 always plays straight
HOLDS = ("legato", "detached")                              # or a number of beats
SOURCE_KINDS = ("seed", "claude", "saved-live", "saved-from-moment", "kept", "edit")
AUTHORS = ("claude", "daniel")
ROLES = ("1", "b3", "3", "4", "#4", "5", "b6", "6", "b7", "7", "b9", "9", "#9", "11", "#11", "b13", "13")
RELATIVE_TO = ("root", "bass")
WANTS = ("present", "landing", "absent")
VARIANT_IDS = ("a", "b", "c", "d", "e", "f")
PAIR_ROLES = ("question", "answer")
MATCHES = ("exact", "enharmonic", "equivalent", "unnamed",  # the voicing bridge's round trip for a chord
           "notes")                                          # ... and for exact notes: the page's own name, no chord to compare
TONE_ROLES = ("root", "third", "fifth", "sixth", "seventh", "ninth", "eleventh", "thirteenth", "sus")
VOICE_ROLES = ("bass",) + TONE_ROLES
SLOT_CLASSES = ("diatonic", "secondary dominant", "borrowed", "modal", "chromatic")  # practice.classify
MODES = ("play", "loop", "try")
ROUTES = ("page",)                                          # v2 adds FL as the clock
STATES = ("pending", "running", "stopped")
COURTESY_VIA = ("rest", "knock", "now", "timeout")
STOP_REASONS = ("page", "cli", "replaced", "count", "stream-lost", "server-restart", "device", "declined", "expired")
TRY_BACKINGS = ("ghosts", "bass", "loop")
ENDINGS = ("cut", "home")
AT_LINES = tempomap.AT_LINES
ACK_ROLES = ("owner", "viewer")
ACK_STOPPED = ("stream-lost", "device")
EVENT_KINDS = ("start", "launch", "ack", "change", "mark", "stop")
CHANGE_OPS = ("tempo", "next", "mute", "unmute", "set")    # a stop is its own line
EVENT_BY = ("claude", "daniel", "page", "server")

# ===================================================================================================== limits
MAX_CARD_BYTES = 64 * 1024
MAX_ITEMS = 64
MAX_VARIANTS = 6
MAX_ALSO_IN = 6
MAX_CHECKS = 8
MAX_TAGS = 12
MAX_MOMENTS = 12
MAX_RELATED = 8
MAX_BEATS = 64
MAX_EXACT_NOTES = 24
MAX_BAND_NOTES = 7              # a bass and up to 6 upper voices (MUSIC 3.2)
NOTE_MIN, NOTE_MAX = 21, 108
BPM_MIN, BPM_MAX = 30, 240
METER_MIN, METER_MAX = 2, 7
COUNT_IN_MAX = 2
VELOCITY_MIN, VELOCITY_MAX = 1, 127
ARP_MAX_MS = 2000
TEXT_LIMITS = {"title": 80, "meaning": 120, "theory_name": 40, "style": 80, "explanation": 400, "why": 300,
               "try": 300, "listen_for": 160}
SAY_MAX = 120
NAME_MAX = 24
NUMBER_MAX = 24
VARIANT_LABEL_MAX = 60
MOMENT_LABEL_MAX = 120
PULL_MAX = 120
MARK_TEXT_MAX = 200
ENGINE_MAX = 40
WARNING_MAX = 300
REPLAY_MAX_SECONDS = 600
REPLAY_MAX_SPEED = 4
BASS_RANGE = (28, 50)           # E1..D3 (10.1)
FULL_TOP_MAX = 69               # A4, hard
COMP_TOP_MAX = 64               # E4: only the defining altered colour reaches it
SEGMENT_TOLERANCE_MS = 0.1      # a stored segment epoch against the tempo map (DATA 6.3 keeps 0.1 ms)
CARD_DEFAULTS = {"tempo": {"bpm": 66, "beats_per_bar": 4, "feel": "straight"},
                 "voicing": {"style": "spread", "voice_lead": False, "octave": None},
                 "playback": {"velocity": 48, "arpeggio_ms": 0, "hold": "legato", "count": None},
                 "backing": "comp", "pulse_from_bpm": 80}
CARD_WORDING_FORBIDDEN = ("wrong", "mistake", "should")    # section 12 wording rule

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
TAG_RE = re.compile(r"^[a-z0-9-]{1,24}$")
NUMBER_RE = re.compile(r"^(#{1,2}|b{1,2})?[1-7]([^\s|:\[\]]*?)(/(#{1,2}|b{1,2})?[1-7])?$")
KEY_ITEM_RE = re.compile(r"^(#{1,2}|b{1,2})?[1-7] (major|minor)$")
CLOCK_RE = re.compile(r"^\d{1,3}:[0-5]\d(\.\d{1,3})?$")
ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(\+00:00|Z)$")
SESSION_RE = re.compile(rf"^{SESSION_PATTERN}$")
RUN_ID_RE = SESSION_RE          # runs are named like sessions: YYYYMMDD-HHMMSS-8 hex
PAGE_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")

CARD_KEYS = ("api", "id", "rev", "title", "meaning", "theory_name", "group", "kind", "key", "also_in", "chords",
             "variants", "voicing", "groove", "backing", "tempo", "bars", "playback", "style", "explanation", "why",
             "try", "listen_for", "checks", "tags", "moments", "replay", "related", "page_reads", "source",
             "created_by", "updated_by", "created_at", "updated_at", "favorite", "archived", "landing", "pair")
CARD_SERVER_FIELDS = ("rev", "source", "created_at", "updated_at", "updated_by")
CARD_UNPATCHABLE = ("api", "id", "rev", "created_by", "created_at", "page_reads", "source")  # 5.1 update
CHORD_ITEM_KEYS = ("n", "beats", "notes", "voicing", "vel", "arp_ms", "hold", "say", "upper", "name")
VARIANT_KEYS = ("id", "label", "key", "chords", "tempo", "say")
CHECK_KEYS = ("id", "variant", "slot", "role", "relative_to", "want", "say")
LANDING_KEYS = ("variant", "slot", "role", "relative_to", "pull")
PAIR_KEYS = ("role", "with")
MOMENT_KEYS = ("session", "at", "until", "label")
REPLAY_KEYS = ("session", "at", "seconds", "speed")
PAGE_READ_KEYS = ("variant", "slot", "key", "voicing", "notes", "name", "number", "match", "note")

DEF_KEYS = ("api", "card", "key", "beats_per_bar", "cycle_beats", "backing", "sections", "slots", "warnings", "landing")
DEF_CARD_KEYS = ("id", "rev", "title", "variant")
SECTION_KEYS = ("i", "key", "from_beat")
SLOT_KEYS = ("i", "section", "at_beat", "beats", "n", "name", "key", "tones_pc", "bass_pc", "chord_pcs", "scale",
             "scale_name", "class", "voicings", "roles", "exact", "upper_same", "vel", "arp_ms", "say", "page_reads",
             "warnings")
SLOT_OPTIONAL_KEYS = ("hold", "omits", "reads_as")
VOICING_KEYS = ("play", "full", "comp", "bass")
VOICING_OPTIONAL_KEYS = ("pad",)
DEF_LANDING_KEYS = ("slot", "role", "relative_to", "pc", "pull", "note")  # note: optional, spelled from the chord

RUN_KEYS = ("api", "run", "mode", "route", "engine", "state", "created_at", "created_by", "card", "card_snapshot", "key",
            "beats_per_bar", "count_in_bars", "start_epoch_ms", "bar0_epoch_ms", "segments", "settings",
            "last_version", "owner_page_id", "courtesy", "closed", "stopped_epoch_ms", "stop_bar", "stop_reason",
            "late_dropped")
RUN_OPTIONAL_KEYS = ("approx", "slot", "velocity")
SEGMENT_KEYS = ("from_bar", "bpm", "epoch_ms", "def_version", "def_from_bar")
SETTINGS_KEYS = ("from_bar", "groove", "backing", "level", "humanize", "seed", "walk", "try_backing", "passes", "ending")
SETTINGS_OPTIONAL_KEYS = ("muted", "dropout")  # dropout 0..1, absent means off (jam-rulings: a run setting)
COURTESY_KEYS = ("held_ms", "via")

ACK_KEYS = ("page_id", "role", "version", "bar", "bar_epoch_ms", "perf_ms", "perf_offset_ms")
ACK_DEFAULTS = {"output_latency_ms": None, "log": None, "stopped": None, "late_dropped": 0}
ACK_OPTIONAL_KEYS = ("late_frame_ms", "offset_step_ms", "stop_bar", "effective_bar")
ACK_LOG_KEYS = ("local", "session", "t0_perf_ms")

EVENT_COMMON_KEYS = ("seq", "kind", "recorded_epoch_ms", "by")
EVENT_REQUIRED = {"start": ("version", "effective_bar", "bpm", "def"),
                  "launch": ("version", "start_epoch_ms", "bar0_epoch_ms", "page_id"),
                  "ack": (),
                  "change": ("op", "version", "effective_bar", "epoch_ms"),
                  "mark": ("text",),
                  "stop": ("reason", "version", "epoch_ms")}
EVENT_OPTIONAL = {"start": ("epoch_ms", "state", "mode", "card", "key", "settings", "segments"),
                  "launch": ("epoch_ms", "held_ms", "via"),
                  "ack": (),
                  "change": ("at", "bpm", "def", "card", "key", "variant", "settings", "segments", "if_version"),
                  "mark": ("run", "epoch_ms", "version", "bar"),
                  "stop": ("effective_bar", "stop_bar", "at", "approx")}

SEED_KEYS = ("api", "seed_version", "cards")
SEED_MOMENTS_KEYS = ("api", "cards")
SEED_MOMENT_CARD_KEYS = ("moments", "replay")


class JamSchemaError(ValueError):
    """A malformed jam object. `field` is the path of the offending field; the message starts with it."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field} {message}" if field else message)


# ==================================================================================================== helpers
def _path(where: str, key) -> str:
    if isinstance(key, int):
        return f"{where}[{key}]"
    return f"{where}.{key}" if where else key


def _nested(prefix: str, exc: JamSchemaError) -> JamSchemaError:
    """The same complaint about an object held inside another, its field path prefixed ("card_snapshot.title")."""
    detail = str(exc)[len(exc.field):].lstrip() if exc.field else str(exc)
    return JamSchemaError(_path(prefix, exc.field) if exc.field else prefix, detail)


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _is_num(x) -> bool:
    return (isinstance(x, (int, float)) and not isinstance(x, bool)) and math.isfinite(x)


def _obj(value, field: str, what: str = "a JSON object") -> dict:
    if not isinstance(value, dict):
        raise JamSchemaError(field, f"must be {what} (got {value!r:.60})")
    return value


def _unknown(obj: dict, allowed: Iterable[str], where: str) -> None:
    extra = sorted(set(obj) - set(allowed))
    if extra:
        raise JamSchemaError(_path(where, extra[0]),
                             f"is not a known field; expected some of {', '.join(sorted(allowed))}")


def _need(obj: dict, key: str, where: str):
    if key not in obj:
        raise JamSchemaError(_path(where, key), "is required")
    return obj[key]


def _text(obj: dict, key: str, where: str, limit: int, required: bool = False, nullable: bool = True) -> Optional[str]:
    field = _path(where, key)
    if key not in obj or (obj[key] is None and nullable and not required):
        if required:
            raise JamSchemaError(field, "is required")
        return None
    value = obj[key]
    if not isinstance(value, str):
        raise JamSchemaError(field, f"must be a string (got {value!r:.60})")
    if required and not value.strip():
        raise JamSchemaError(field, "must not be empty")
    if len(value) > limit:
        raise JamSchemaError(field, f"is {len(value)} characters; at most {limit}")
    return value


def _enum(value, field: str, allowed: Sequence, nullable: bool = False):
    if value is None and nullable:
        return None
    if value not in allowed:
        raise JamSchemaError(field, f"must be one of {', '.join(map(str, allowed))} (got {value!r:.60})")
    return value


def _int(value, field: str, lo: Optional[int] = None, hi: Optional[int] = None, nullable: bool = False):
    if value is None and nullable:
        return None
    if not _is_int(value) or (lo is not None and value < lo) or (hi is not None and value > hi):
        raise JamSchemaError(field, f"must be an integer{_range(lo, hi)} (got {value!r:.60})")
    return value


def _num(value, field: str, lo: Optional[float] = None, hi: Optional[float] = None, nullable: bool = False,
         above: Optional[float] = None):
    if value is None and nullable:
        return None
    bad = not _is_num(value) or (lo is not None and value < lo) or (hi is not None and value > hi) or \
        (above is not None and value <= above)
    if bad:
        span = f" > {above}" if above is not None else _range(lo, hi)
        raise JamSchemaError(field, f"must be a number{span} (got {value!r:.60})")
    return value


def _range(lo, hi) -> str:
    if lo is not None and hi is not None:
        return f" {lo}..{hi}"
    if lo is not None:
        return f" >= {lo}"
    if hi is not None:
        return f" <= {hi}"
    return ""


def _bool(value, field: str, nullable: bool = False):
    if value is None and nullable:
        return None
    if not isinstance(value, bool):
        raise JamSchemaError(field, f"must be true or false (got {value!r:.60})")
    return value


def _list(value, field: str, lo: int = 0, hi: Optional[int] = None) -> list:
    if not isinstance(value, list):
        raise JamSchemaError(field, f"must be a list (got {value!r:.60})")
    if len(value) < lo:
        raise JamSchemaError(field, "must not be empty" if lo == 1 else f"needs at least {lo} entries")
    if hi is not None and len(value) > hi:
        raise JamSchemaError(field, f"has {len(value)} entries; at most {hi}")
    return value


def _key_name(value, field: str) -> str:
    if not isinstance(value, str) or nashville.parse_key(value) is None:
        raise JamSchemaError(field, f'must be a key name like "Eb major" or "D minor" (got {value!r:.60})')
    return value


def _iso(value, field: str, nullable: bool = False):
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not ISO_RE.match(value):
        raise JamSchemaError(field, f'must be an ISO 8601 UTC time like "2030-01-01T00:00:00.000+00:00" '
                                    f"(got {value!r:.60})")
    return value


def _card_id(value, field: str) -> str:
    if not isinstance(value, str) or not ID_RE.match(value):
        raise JamSchemaError(field, f"must be a card id: lowercase letters, digits and -, 1 to 48 long, starting "
                                    f"with a letter or digit (got {value!r:.60})")
    return value


def _beats(value, field: str, hi: float = MAX_BEATS) -> float:
    if not _is_num(value) or value <= 0 or value > hi or (value * 2) != int(value * 2):
        raise JamSchemaError(field, f"must be a number of beats > 0 in steps of 0.5, at most {hi} (got {value!r:.60})")
    return value


def _beat_position(value, field: str) -> float:
    if not _is_num(value) or value < 0 or (value * 2) != int(value * 2):
        raise JamSchemaError(field, f"must be a beat position >= 0 in steps of 0.5 (got {value!r:.60})")
    return value


def _midi_list(value, field: str, lo: int = 1, hi: int = MAX_EXACT_NOTES, ordered: bool = False) -> list:
    _list(value, field, lo, hi)
    for i, n in enumerate(value):
        if not _is_int(n) or not NOTE_MIN <= n <= NOTE_MAX:
            raise JamSchemaError(_path(field, i), f"must be a MIDI note {NOTE_MIN}..{NOTE_MAX} (got {n!r:.60})")
    if len(set(value)) != len(value):
        raise JamSchemaError(field, "has the same note twice")
    if ordered and list(value) != sorted(value):
        raise JamSchemaError(field, "must list its notes from the lowest up")
    return value


def _pc(value, field: str) -> int:
    return _int(value, field, 0, 11)


def _hold(value, field: str):
    if value in HOLDS:
        return value
    if _is_num(value) and 0 < value <= MAX_BEATS:
        return value
    raise JamSchemaError(field, f"must be legato, detached or a number of beats > 0 (got {value!r:.60})")


def _strings(value, field: str, limit: int = WARNING_MAX) -> list:
    _list(value, field)
    for i, s in enumerate(value):
        if not isinstance(s, str) or len(s) > limit:
            raise JamSchemaError(_path(field, i), f"must be a string of at most {limit} characters")
    return value


# ======================================================================================================= card
def chord_count(items: Sequence[dict]) -> int:
    """The number of slots a chord line makes: chord items only, key changes and rests not counted (DATA 2.8)."""
    return sum(1 for it in items if isinstance(it, dict) and "key" not in it and "rest" not in it)


def line_beats(items: Sequence[dict]) -> float:
    """The length of a chord line in beats: chords (default 4 beats) plus rests."""
    total = 0.0
    for it in items:
        if not isinstance(it, dict) or "key" in it:
            continue
        total += it["rest"] if "rest" in it else it.get("beats", 4)
    return total


def _chord_line(items, where: str) -> None:
    _list(items, where, 1, MAX_ITEMS)
    first_chord = True
    for i, item in enumerate(items):
        at = _path(where, i)
        _obj(item, at)
        if "key" in item:
            _unknown(item, ("key",), at)
            value = item["key"]
            if not isinstance(value, str) or not KEY_ITEM_RE.match(value):
                raise JamSchemaError(_path(at, "key"), f'must be a degree of the card key and a mode, like "6 major" '
                                                       f"or \"b3 minor\" (got {value!r:.60})")
            continue
        if "rest" in item:
            _unknown(item, ("rest",), at)
            _beats(item["rest"], _path(at, "rest"))
            continue
        _unknown(item, CHORD_ITEM_KEYS, at)
        n = item.get("n")
        if n is None:
            if "notes" not in item:
                raise JamSchemaError(_path(at, "n"), 'is required unless the chord has exact notes (a Nashville number '
                                                     'like "4maj7#11")')
        elif not isinstance(n, str) or len(n) > NUMBER_MAX or not NUMBER_RE.match(n):
            raise JamSchemaError(_path(at, "n"), f'must be a Nashville number like "1maj9", "5^7sus4/1" or "b6maj9" '
                                                 f"(got {n!r:.60})")
        if "beats" in item:
            _beats(item["beats"], _path(at, "beats"))
        if "notes" in item:
            _midi_list(item["notes"], _path(at, "notes"))
        if "voicing" in item:
            _enum(item["voicing"], _path(at, "voicing"), VOICING_STYLES)
        if "vel" in item:
            _int(item["vel"], _path(at, "vel"), VELOCITY_MIN, VELOCITY_MAX)
        if "arp_ms" in item:
            _int(item["arp_ms"], _path(at, "arp_ms"), 0, ARP_MAX_MS)
        if "hold" in item:
            _hold(item["hold"], _path(at, "hold"))
        _text(item, "say", at, SAY_MAX)
        _text(item, "name", at, NAME_MAX)
        if "upper" in item:
            if item["upper"] != "same":
                raise JamSchemaError(_path(at, "upper"), f'must be "same" (got {item["upper"]!r:.60})')
            if first_chord:
                raise JamSchemaError(_path(at, "upper"), "cannot be on a line's first chord: it keeps the previous "
                                                         "chord's upper voices")
        first_chord = False
    if chord_count(items) == 0:
        raise JamSchemaError(where, "needs at least one chord (not only rests and key changes)")


def _tempo(value, field: str, partial: bool = False) -> dict:
    _obj(value, field)
    _unknown(value, ("bpm", "beats_per_bar", "feel"), field)
    if "bpm" in value or not partial:
        _num(_need(value, "bpm", field) if not partial else value["bpm"], _path(field, "bpm"), BPM_MIN, BPM_MAX)
    if "beats_per_bar" in value:
        _int(value["beats_per_bar"], _path(field, "beats_per_bar"), METER_MIN, METER_MAX)
    if "feel" in value:
        _enum(value["feel"], _path(field, "feel"), FEELS)
    return value


def _line_for(card: dict, variant: Optional[str], field: str) -> list:
    if variant is None:
        return card.get("chords") or []
    for v in card.get("variants") or []:
        if v.get("id") == variant:
            return v["chords"]
    raise JamSchemaError(field, f"names variant {variant!r}, which the card does not have")


def _slot_in_line(card: dict, obj: dict, where: str, required: bool) -> None:
    variant = _enum(obj.get("variant"), _path(where, "variant"), VARIANT_IDS, nullable=True)
    line = _line_for(card, variant, _path(where, "variant"))
    if "slot" not in obj or obj["slot"] is None:
        if required:
            raise JamSchemaError(_path(where, "slot"), "is required")
        return
    count = chord_count(line)
    _int(obj["slot"], _path(where, "slot"), 0)
    if obj["slot"] >= count:
        raise JamSchemaError(_path(where, "slot"), f"is {obj['slot']}, but the line has {count} chord"
                                                   f"{'s' if count != 1 else ''} (slots count from 0)")


def _moment(value, field: str) -> None:
    _obj(value, field)
    _unknown(value, MOMENT_KEYS, field)
    session = _need(value, "session", field)
    if not isinstance(session, str) or not SESSION_RE.match(session):
        raise JamSchemaError(_path(field, "session"), f"must be a practice session id (got {session!r:.60})")
    at = _need(value, "at", field)
    if not isinstance(at, str) or not CLOCK_RE.match(at):
        raise JamSchemaError(_path(field, "at"), f'must be a time like "5:22" (got {at!r:.60})')
    until = value.get("until")
    if until is not None and (not isinstance(until, str) or not CLOCK_RE.match(until)):
        raise JamSchemaError(_path(field, "until"), f'must be a time like "5:30" or null (got {until!r:.60})')
    _text(value, "label", field, MOMENT_LABEL_MAX)


def _replay(value, field: str) -> None:
    _obj(value, field)
    _unknown(value, REPLAY_KEYS, field)
    session = _need(value, "session", field)
    if not isinstance(session, str) or not SESSION_RE.match(session):
        raise JamSchemaError(_path(field, "session"), f"must be a practice session id (got {session!r:.60})")
    at = _need(value, "at", field)
    if not isinstance(at, str) or not CLOCK_RE.match(at):
        raise JamSchemaError(_path(field, "at"), f'must be a time like "5:22" (got {at!r:.60})')
    _num(_need(value, "seconds", field), _path(field, "seconds"), hi=REPLAY_MAX_SECONDS, above=0)
    if "speed" in value:
        _num(value["speed"], _path(field, "speed"), hi=REPLAY_MAX_SPEED, above=0)


def _page_read(value, field: str) -> None:
    _obj(value, field)
    _unknown(value, PAGE_READ_KEYS, field)
    _enum(value.get("variant"), _path(field, "variant"), VARIANT_IDS, nullable=True)
    _int(_need(value, "slot", field), _path(field, "slot"), 0)
    if "key" in value:
        _key_name(value["key"], _path(field, "key"))
    _text(value, "voicing", field, 16)
    if "notes" in value:
        _midi_list(value["notes"], _path(field, "notes"))
    _text(value, "name", field, 60)
    _text(value, "number", field, 60)
    _enum(_need(value, "match", field), _path(field, "match"), MATCHES)
    _text(value, "note", field, 300)


def _source(value, field: str) -> None:
    _obj(value, field)
    kind = _enum(_need(value, "kind", field), _path(field, "kind"), SOURCE_KINDS)
    if kind == "seed":
        _int(_need(value, "seed_version", field), _path(field, "seed_version"), 1)
    if kind == "kept":
        origin = _obj(_need(value, "from", field), _path(field, "from"))
        _card_id(_need(origin, "id", _path(field, "from")), _path(field, "from.id"))
        _int(_need(origin, "rev", _path(field, "from")), _path(field, "from.rev"), 1)


def validate_card(card, stored: bool = False) -> dict:
    """Return a deep copy of the card, or raise JamSchemaError naming the first wrong field.

    Checks the shape and limits of jam-spec 4.1 and DATA 2.2-2.9, in the order the fields are listed there. A number's
    suffix is read by the voicing bridge on create and update (J3), not here. stored=True also requires the fields the
    server writes: rev, source, created_at, updated_at and updated_by.
    """
    if not isinstance(card, dict):
        raise JamSchemaError("card", "must be a JSON object")
    size = len(json.dumps(card, ensure_ascii=False, default=str).encode("utf-8"))
    if size > MAX_CARD_BYTES:
        raise JamSchemaError("card", f"is {size} bytes; at most {MAX_CARD_BYTES}")
    _unknown(card, CARD_KEYS, "")
    if _need(card, "api", "") != CARD_API:
        raise JamSchemaError("api", f"must be {CARD_API!r} (got {card['api']!r:.60})")
    _card_id(_need(card, "id", ""), "id")
    if stored:
        for key in CARD_SERVER_FIELDS:
            _need(card, key, "")
    if "rev" in card:
        _int(card["rev"], "rev", 1)
    for key in ("title", "meaning"):
        _text(card, key, "", TEXT_LIMITS[key], required=True)
    _text(card, "theory_name", "", TEXT_LIMITS["theory_name"])
    _enum(_need(card, "group", ""), "group", GROUPS)
    kind = _enum(_need(card, "kind", ""), "kind", KINDS)
    _key_name(_need(card, "key", ""), "key")
    if "also_in" in card:
        _list(card["also_in"], "also_in", 0, MAX_ALSO_IN)
        for i, k in enumerate(card["also_in"]):
            _key_name(k, _path("also_in", i))

    variants = card.get("variants") or []
    if "variants" in card:
        _list(card["variants"], "variants", 0, MAX_VARIANTS)
        seen = set()
        for i, v in enumerate(card["variants"]):
            at = _path("variants", i)
            _obj(v, at)
            _unknown(v, VARIANT_KEYS, at)
            vid = _enum(_need(v, "id", at), _path(at, "id"), VARIANT_IDS)
            if vid in seen:
                raise JamSchemaError(_path(at, "id"), f"repeats variant {vid!r}")
            seen.add(vid)
            _text(v, "label", at, VARIANT_LABEL_MAX)
            if "key" in v and v["key"] is not None:
                if not isinstance(v["key"], str) or not KEY_ITEM_RE.match(v["key"]):
                    raise JamSchemaError(_path(at, "key"), f'must be a degree of the card key and a mode, like '
                                                           f'"b7 major" (got {v["key"]!r:.60})')
            _chord_line(_need(v, "chords", at), _path(at, "chords"))
            if "tempo" in v:
                _tempo(v["tempo"], _path(at, "tempo"), partial=True)
            _text(v, "say", at, SAY_MAX)

    if kind == "concept" and variants and not card.get("chords"):
        if "chords" in card:
            _list(card["chords"], "chords", 0, 0)
    else:
        if "chords" not in card:
            raise JamSchemaError("chords", "is required (only a concept card with variants may leave it out)")
        _chord_line(card["chords"], "chords")

    if "voicing" in card:
        _obj(card["voicing"], "voicing")
        _unknown(card["voicing"], ("style", "voice_lead", "octave"), "voicing")
        if "style" in card["voicing"]:
            _enum(card["voicing"]["style"], "voicing.style", VOICING_STYLES)
        if "voice_lead" in card["voicing"]:
            _bool(card["voicing"]["voice_lead"], "voicing.voice_lead")
        if "octave" in card["voicing"]:
            _int(card["voicing"]["octave"], "voicing.octave", 0, 7, nullable=True)
    if "groove" in card:
        _enum(card["groove"], "groove", GROOVES)
    if "backing" in card:
        _enum(card["backing"], "backing", BACKINGS)
    if "tempo" in card:
        _tempo(card["tempo"], "tempo")
    if "bars" in card:
        _int(card["bars"], "bars", 1)
        meter = (card.get("tempo") or {}).get("beats_per_bar", CARD_DEFAULTS["tempo"]["beats_per_bar"])
        beats = line_beats(card.get("chords") or [])
        if card["bars"] * meter < beats:
            raise JamSchemaError("bars", f"is {card['bars']} bars of {meter} beats, but the chords last {beats:g} beats")
    if "playback" in card:
        pb = _obj(card["playback"], "playback")
        _unknown(pb, ("velocity", "arpeggio_ms", "hold", "count"), "playback")
        if "velocity" in pb:
            _int(pb["velocity"], "playback.velocity", VELOCITY_MIN, VELOCITY_MAX)
        if "arpeggio_ms" in pb:
            _int(pb["arpeggio_ms"], "playback.arpeggio_ms", 0, ARP_MAX_MS)
        if "hold" in pb:
            _hold(pb["hold"], "playback.hold")
        if "count" in pb:
            _int(pb["count"], "playback.count", 1, nullable=True)
    _text(card, "style", "", TEXT_LIMITS["style"])
    for key in ("explanation", "why", "try"):
        _text(card, key, "", TEXT_LIMITS[key], required=True)
    _text(card, "listen_for", "", TEXT_LIMITS["listen_for"])

    if "checks" in card:
        _list(card["checks"], "checks", 0, MAX_CHECKS)
        seen = set()
        for i, chk in enumerate(card["checks"]):
            at = _path("checks", i)
            _obj(chk, at)
            _unknown(chk, CHECK_KEYS, at)
            cid = _need(chk, "id", at)
            if not isinstance(cid, str) or not ID_RE.match(cid):
                raise JamSchemaError(_path(at, "id"), f"must be a slug like \"sharp-eleven\" (got {cid!r:.60})")
            if cid in seen:
                raise JamSchemaError(_path(at, "id"), f"repeats check {cid!r}")
            seen.add(cid)
            _slot_in_line(card, chk, at, required=True)
            _enum(_need(chk, "role", at), _path(at, "role"), ROLES)
            if "relative_to" in chk:
                _enum(chk["relative_to"], _path(at, "relative_to"), RELATIVE_TO)
            _enum(_need(chk, "want", at), _path(at, "want"), WANTS)
            _text(chk, "say", at, SAY_MAX, required=True)
    if "tags" in card:
        _list(card["tags"], "tags", 0, MAX_TAGS)
        for i, tag in enumerate(card["tags"]):
            if not isinstance(tag, str) or not TAG_RE.match(tag):
                raise JamSchemaError(_path("tags", i), f"must be a tag: lowercase letters, digits and -, 1 to 24 long "
                                                       f"(got {tag!r:.60})")
    if "moments" in card:
        _list(card["moments"], "moments", 0, MAX_MOMENTS)
        for i, m in enumerate(card["moments"]):
            _moment(m, _path("moments", i))
    if "replay" in card and card["replay"] is not None:
        _replay(card["replay"], "replay")
    if "related" in card:
        _list(card["related"], "related", 0, MAX_RELATED)
        for i, rid in enumerate(card["related"]):
            _card_id(rid, _path("related", i))
    if "page_reads" in card:
        _list(card["page_reads"], "page_reads")
        for i, pr in enumerate(card["page_reads"]):
            _page_read(pr, _path("page_reads", i))
    if "source" in card:
        _source(card["source"], "source")
    _enum(_need(card, "created_by", ""), "created_by", AUTHORS)
    if "updated_by" in card:
        _enum(card["updated_by"], "updated_by", AUTHORS)
    for key in ("created_at", "updated_at"):
        if key in card:
            _iso(card[key], key)
    for key in ("favorite", "archived"):
        if key in card:
            _bool(card[key], key)

    if "landing" in card and card["landing"] is not None:
        landing = _obj(card["landing"], "landing")
        _unknown(landing, LANDING_KEYS, "landing")
        _slot_in_line(card, landing, "landing", required=False)
        _enum(_need(landing, "role", "landing"), "landing.role", ROLES)
        if "relative_to" in landing:
            _enum(landing["relative_to"], "landing.relative_to", RELATIVE_TO)
        _text(landing, "pull", "landing", PULL_MAX, required=True)
    if "pair" in card and card["pair"] is not None:
        pair = _obj(card["pair"], "pair")
        _unknown(pair, PAIR_KEYS, "pair")
        _enum(_need(pair, "role", "pair"), "pair.role", PAIR_ROLES)
        other = _card_id(_need(pair, "with", "pair"), "pair.with")
        if other == card["id"]:
            raise JamSchemaError("pair.with", "names the card itself; a pair links two cards")
    return copy.deepcopy(card)


def card_settings(card: dict) -> dict:
    """The effective settings of a valid card, every 4.1 default filled in: {tempo, voicing, playback, groove,
    groove_v1, backing, backing_v1, bars, cycle_beats}. groove_v1 and backing_v1 are what a v1 page plays (a v2 groove
    plays ballad; the pad backing plays comp). bars and cycle_beats describe the main line (0 for a concept card
    without one)."""
    tempo = {**CARD_DEFAULTS["tempo"], **(card.get("tempo") or {})}
    voicing = {**CARD_DEFAULTS["voicing"], **(card.get("voicing") or {})}
    playback = {**CARD_DEFAULTS["playback"], **(card.get("playback") or {})}
    groove = card.get("groove") or ("ballad" if tempo["bpm"] < CARD_DEFAULTS["pulse_from_bpm"] else "pulse")
    backing = card.get("backing") or CARD_DEFAULTS["backing"]
    beats = line_beats(card.get("chords") or [])
    meter = tempo["beats_per_bar"]
    bars = card.get("bars") or (math.ceil(beats / meter) if beats else 0)
    return {"tempo": tempo, "voicing": voicing, "playback": playback, "groove": groove,
            "groove_v1": groove if groove in GROOVES_V1 else "ballad", "backing": backing,
            "backing_v1": backing if backing in BACKINGS_V1 else "comp", "bars": bars, "cycle_beats": bars * meter}


def card_texts(card: dict) -> List[Tuple[str, str]]:
    """Every text of a card Daniel reads, as (field path, text), for the wording guards (sections 11.4 and 12)."""
    out: List[Tuple[str, str]] = []

    def add(path, value):
        if isinstance(value, str) and value:
            out.append((path, value))

    for key in ("title", "meaning", "theory_name", "style", "explanation", "why", "try", "listen_for"):
        add(key, card.get(key))

    def line(items, where):
        for i, it in enumerate(items or []):
            if isinstance(it, dict):
                add(_path(_path(where, i), "say"), it.get("say"))

    line(card.get("chords"), "chords")
    for j, v in enumerate(card.get("variants") or []):
        at = _path("variants", j)
        add(_path(at, "label"), v.get("label"))
        add(_path(at, "say"), v.get("say"))
        line(v.get("chords"), _path(at, "chords"))
    for k, chk in enumerate(card.get("checks") or []):
        add(_path(_path("checks", k), "say"), chk.get("say"))
    for k, m in enumerate(card.get("moments") or []):
        add(_path(_path("moments", k), "label"), m.get("label"))
    if isinstance(card.get("landing"), dict):
        add("landing.pull", card["landing"].get("pull"))
    return out


def wording_problems(card: dict, forbidden: Sequence[str] = CARD_WORDING_FORBIDDEN) -> List[Tuple[str, str]]:
    """(field path, word) for every forbidden word (whole word, any case) in the card's texts."""
    out = []
    for path, text in card_texts(card):
        for word in forbidden:
            if re.search(rf"\b{re.escape(word)}\b", text, re.I):
                out.append((path, word))
    return out


def pair_problems(cards: Sequence[dict]) -> List[Tuple[str, str]]:
    """(card id, sentence) for every question and answer pair that does not close: the partner is missing from the
    cards, does not name this card back, or has the same role. The sentence reads after "<id>.pair "."""
    by_id = {c.get("id"): c for c in cards if isinstance(c, dict)}
    out = []
    for cid, card in by_id.items():
        pair = card.get("pair")
        if not isinstance(pair, dict):
            continue
        other = by_id.get(pair.get("with"))
        if other is None:
            out.append((cid, f"names {pair.get('with')!r}, which is not in the deck"))
            continue
        back = other.get("pair")
        if not isinstance(back, dict) or back.get("with") != cid:
            out.append((cid, f"names {other['id']!r}, whose pair does not name {cid!r} back"))
        elif back.get("role") == pair.get("role"):
            out.append((cid, f"and {other['id']}'s pair are both {pair.get('role')!r}; one asks, one answers"))
    return out


# ======================================================================================================== def
def _def_card(value, field: str) -> None:
    if value is None:
        return
    _obj(value, field)
    _unknown(value, DEF_CARD_KEYS, field)
    _card_id(_need(value, "id", field), _path(field, "id"))
    _int(_need(value, "rev", field), _path(field, "rev"), 1)
    _text(value, "title", field, TEXT_LIMITS["title"], required=True)
    _enum(value.get("variant"), _path(field, "variant"), VARIANT_IDS, nullable=True)


def _voicings(slot: dict, at: str) -> None:
    field = _path(at, "voicings")
    v = _obj(_need(slot, "voicings", at), field)
    _unknown(v, VOICING_KEYS + VOICING_OPTIONAL_KEYS, field)
    for key in VOICING_KEYS:
        _need(v, key, field)
    _midi_list(v["play"], _path(field, "play"), 1, MAX_EXACT_NOTES, ordered=True)
    _midi_list(v["bass"], _path(field, "bass"), 1, 1)
    for key in ("full", "comp", "pad"):
        if key in v:
            _midi_list(v[key], _path(field, key), 1, MAX_BAND_NOTES, ordered=True)
    lo, hi = BASS_RANGE
    for key in ("full", "comp", "bass"):
        low = v[key][0]
        if low % 12 != slot["bass_pc"]:
            raise JamSchemaError(_path(_path(field, key), 0), f"is MIDI {low}, not the bass pitch class "
                                                              f"{slot['bass_pc']}")
        if not lo <= low <= hi:
            raise JamSchemaError(_path(_path(field, key), 0), f"is MIDI {low}; the band bass sits in {lo}..{hi} "
                                                              f"(E1..D3)")
    if v["full"][-1] > FULL_TOP_MAX:
        raise JamSchemaError(_path(field, "full"), f"reaches MIDI {v['full'][-1]}; the full backing tops out at "
                                                   f"{FULL_TOP_MAX} (A4)")
    if v["comp"][-1] > COMP_TOP_MAX:
        raise JamSchemaError(_path(field, "comp"), f"reaches MIDI {v['comp'][-1]}; the comp backing tops out at "
                                                   f"{COMP_TOP_MAX} (E4)")
    rfield = _path(at, "roles")
    roles = _obj(_need(slot, "roles", at), rfield)
    _unknown(roles, VOICING_KEYS[1:] + VOICING_OPTIONAL_KEYS, rfield)
    for key in ("full", "comp", "bass", "pad"):
        if key not in v:
            continue
        names = _list(_need(roles, key, rfield), _path(rfield, key))
        if len(names) != len(v[key]):
            raise JamSchemaError(_path(rfield, key), f"has {len(names)} roles for {len(v[key])} notes")
        for i, name in enumerate(names):
            _enum(name, _path(_path(rfield, key), i), VOICE_ROLES)
        if names[0] != "bass":
            raise JamSchemaError(_path(_path(rfield, key), 0), f"must be bass, the lowest note (got {names[0]!r})")


def validate_def(d) -> dict:
    """Return a deep copy of a resolved def (arsenal.jam.def/v0), or raise JamSchemaError naming the first wrong field.

    Beyond the shape: slots are in time order without overlaps and inside one cycle; cycle_beats is whole bars; each
    slot's key is its section's; chord_pcs is exactly the named tones plus the bass pitch class; the band voicings keep
    their registers (bass E1..D3, full top A4, comp top E4) and stand on the bass; an upper_same slot keeps the previous
    slot's full and comp upper voices note for note.
    """
    field = "def"
    if not isinstance(d, dict):
        raise JamSchemaError(field, "must be a JSON object")
    _unknown(d, DEF_KEYS, "")
    if _need(d, "api", "") != DEF_API:
        raise JamSchemaError("api", f"must be {DEF_API!r} (got {d['api']!r:.60})")
    _def_card(_need(d, "card", ""), "card")
    _key_name(_need(d, "key", ""), "key")
    meter = _int(_need(d, "beats_per_bar", ""), "beats_per_bar", METER_MIN, METER_MAX)
    cycle = _need(d, "cycle_beats", "")
    if not _is_int(cycle) or cycle <= 0 or cycle % meter:
        raise JamSchemaError("cycle_beats", f"must be a whole number of bars of {meter} beats (got {cycle!r:.60})")
    _enum(_need(d, "backing", ""), "backing", BACKINGS)

    sections = _list(_need(d, "sections", ""), "sections", 1)
    last_from = -1.0
    for i, s in enumerate(sections):
        at = _path("sections", i)
        _obj(s, at)
        _unknown(s, SECTION_KEYS, at)
        for key in SECTION_KEYS:
            _need(s, key, at)
        if s["i"] != i:
            raise JamSchemaError(_path(at, "i"), f"must be {i}, its place in the list (got {s['i']!r:.60})")
        _key_name(s["key"], _path(at, "key"))
        _beat_position(s["from_beat"], _path(at, "from_beat"))
        if i == 0 and s["from_beat"] != 0:
            raise JamSchemaError(_path(at, "from_beat"), "must be 0 for the first section")
        if s["from_beat"] <= last_from or s["from_beat"] >= cycle:
            raise JamSchemaError(_path(at, "from_beat"), "must rise section by section and stay inside the cycle")
        last_from = s["from_beat"]

    slots = _list(_need(d, "slots", ""), "slots", 1, MAX_ITEMS)
    end = 0.0
    prev = None
    for i, slot in enumerate(slots):
        at = _path("slots", i)
        _obj(slot, at)
        _unknown(slot, SLOT_KEYS + SLOT_OPTIONAL_KEYS, at)
        for key in SLOT_KEYS:
            _need(slot, key, at)
        if slot["i"] != i:
            raise JamSchemaError(_path(at, "i"), f"must be {i}, its place in the list (got {slot['i']!r:.60})")
        sec = _int(slot["section"], _path(at, "section"), 0, len(sections) - 1)
        _beat_position(slot["at_beat"], _path(at, "at_beat"))
        _beats(slot["beats"], _path(at, "beats"), hi=cycle)
        if slot["at_beat"] < end:
            raise JamSchemaError(_path(at, "at_beat"), f"is {slot['at_beat']:g}, before the previous slot ends at "
                                                       f"beat {end:g}")
        if slot["at_beat"] < sections[sec]["from_beat"] or \
                (sec + 1 < len(sections) and slot["at_beat"] >= sections[sec + 1]["from_beat"]):
            raise JamSchemaError(_path(at, "section"), f"is {sec}, but beat {slot['at_beat']:g} is outside that section")
        end = slot["at_beat"] + slot["beats"]
        if end > cycle:
            raise JamSchemaError(_path(at, "beats"), f"runs to beat {end:g}, past the cycle's {cycle} beats")
        n = slot["n"]
        if n is not None and (not isinstance(n, str) or len(n) > NUMBER_MAX or not NUMBER_RE.match(n)):
            raise JamSchemaError(_path(at, "n"), f"must be a Nashville number or null (got {n!r:.60})")
        _text(slot, "name", at, 60)
        _key_name(slot["key"], _path(at, "key"))
        if slot["key"] != sections[sec]["key"]:
            raise JamSchemaError(_path(at, "key"), f"is {slot['key']!r}, but section {sec} is in "
                                                   f"{sections[sec]['key']!r}")
        tones = _obj(slot["tones_pc"], _path(at, "tones_pc"))
        for role, pc in tones.items():
            _enum(role, _path(_path(at, "tones_pc"), role), TONE_ROLES)
            _pc(pc, _path(_path(at, "tones_pc"), role))
        _pc(slot["bass_pc"], _path(at, "bass_pc"))
        pcs = _list(slot["chord_pcs"], _path(at, "chord_pcs"), 1, 12)
        for j, pc in enumerate(pcs):
            _pc(pc, _path(_path(at, "chord_pcs"), j))
        if len(set(pcs)) != len(pcs):
            raise JamSchemaError(_path(at, "chord_pcs"), "has the same pitch class twice")
        if slot["bass_pc"] not in pcs:
            raise JamSchemaError(_path(at, "chord_pcs"), f"must hold the bass pitch class {slot['bass_pc']}")
        if tones and set(pcs) != set(tones.values()) | {slot["bass_pc"]}:
            raise JamSchemaError(_path(at, "chord_pcs"), "must be the named chord's tones plus the bass pitch class")
        if slot["scale"] is not None:
            scale = _list(slot["scale"], _path(at, "scale"), 5, 12)
            for j, pc in enumerate(scale):
                _pc(pc, _path(_path(at, "scale"), j))
            if len(set(scale)) != len(scale):
                raise JamSchemaError(_path(at, "scale"), "has the same pitch class twice")
        _text(slot, "scale_name", at, 40)
        _enum(slot["class"], _path(at, "class"), SLOT_CLASSES, nullable=True)
        _voicings(slot, at)
        _bool(slot["exact"], _path(at, "exact"))
        _bool(slot["upper_same"], _path(at, "upper_same"))
        if slot["upper_same"]:
            if prev is None:
                raise JamSchemaError(_path(at, "upper_same"), "cannot be true on the first slot")
            for key in ("full", "comp"):
                if slot["voicings"][key][1:] != prev["voicings"][key][1:]:
                    raise JamSchemaError(_path(_path(at, "voicings"), key),
                                         "must keep the previous slot's upper voices (upper_same)")
        _int(slot["vel"], _path(at, "vel"), VELOCITY_MIN, VELOCITY_MAX)
        _int(slot["arp_ms"], _path(at, "arp_ms"), 0, ARP_MAX_MS)
        _text(slot, "say", at, SAY_MAX)
        if slot["page_reads"] is not None:
            pr = _obj(slot["page_reads"], _path(at, "page_reads"))
            _unknown(pr, ("name", "number", "match"), _path(at, "page_reads"))
            _text(pr, "name", _path(at, "page_reads"), 60)
            _text(pr, "number", _path(at, "page_reads"), 60)
            _enum(_need(pr, "match", _path(at, "page_reads")), _path(at, "page_reads.match"), MATCHES)
        _strings(slot["warnings"], _path(at, "warnings"))
        if "hold" in slot:
            _hold(slot["hold"], _path(at, "hold"))
        if "omits" in slot:
            for j, role in enumerate(_list(slot["omits"], _path(at, "omits"))):
                _enum(role, _path(_path(at, "omits"), j), TONE_ROLES)
        _text(slot, "reads_as", at, 60)
        prev = slot
    _strings(_need(d, "warnings", ""), "warnings")

    if "landing" in d and d["landing"] is not None:
        landing = _obj(d["landing"], "landing")
        _unknown(landing, DEF_LANDING_KEYS, "landing")
        _int(_need(landing, "slot", "landing"), "landing.slot", 0, len(slots) - 1)
        _enum(_need(landing, "role", "landing"), "landing.role", ROLES)
        if "relative_to" in landing:
            _enum(landing["relative_to"], "landing.relative_to", RELATIVE_TO)
        _pc(_need(landing, "pc", "landing"), "landing.pc")
        _text(landing, "pull", "landing", PULL_MAX, required=True)
        if "note" in landing and (not isinstance(landing["note"], str) or
                                  not re.fullmatch(r"[A-G](bb|##|b|#)?", landing["note"])):
            raise JamSchemaError("landing.note", f"must be a note name like Cb or F# (got {landing['note']!r:.60})")
    return copy.deepcopy(d)


# ======================================================================================================== run
def _segments(segments, meter: int, count_in: int, where: str = "segments") -> None:
    _list(segments, where)
    for i, seg in enumerate(segments):
        at = _path(where, i)
        _obj(seg, at)
        if "to_bpm" in seg or "to_bar" in seg:
            raise JamSchemaError(_path(at, "to_bpm" if "to_bpm" in seg else "to_bar"), "is a tempo ramp, which is v2")
        _unknown(seg, SEGMENT_KEYS, at)
        for key in SEGMENT_KEYS:
            _need(seg, key, at)
        _int(seg["from_bar"], _path(at, "from_bar"))
        _num(seg["bpm"], _path(at, "bpm"), BPM_MIN, BPM_MAX)
        _num(seg["epoch_ms"], _path(at, "epoch_ms"), above=0)
        _int(seg["def_version"], _path(at, "def_version"), 1)
        _int(seg["def_from_bar"], _path(at, "def_from_bar"))
        if i == 0:
            if seg["from_bar"] != -count_in:
                raise JamSchemaError(_path(at, "from_bar"), f"must be {-count_in}: the first segment starts the "
                                                            f"count-in of {count_in} bar{'s' if count_in != 1 else ''}")
            if seg["def_from_bar"] != 0:
                raise JamSchemaError(_path(at, "def_from_bar"), "must be 0: bar 0 is the first downbeat of the run")
            continue
        before = segments[i - 1]
        if seg["from_bar"] <= before["from_bar"]:
            raise JamSchemaError(_path(at, "from_bar"), f"must come after the previous segment's bar "
                                                        f"{before['from_bar']}")
        if seg["def_version"] < before["def_version"]:
            raise JamSchemaError(_path(at, "def_version"), "must not go back to an older def")
        if seg["def_from_bar"] > seg["from_bar"]:
            raise JamSchemaError(_path(at, "def_from_bar"), "cannot start the def's cycle after the segment starts")
        want = tempomap.t_epoch(segments[:i], meter, seg["from_bar"])
        if abs(seg["epoch_ms"] - want) > SEGMENT_TOLERANCE_MS:
            raise JamSchemaError(_path(at, "epoch_ms"), f"is {seg['epoch_ms']!r}, but the tempo map puts bar "
                                                        f"{seg['from_bar']} at {want!r}")


def _settings(settings, mode: str, where: str = "settings") -> None:
    _list(settings, where, 1)
    last = None
    for i, s in enumerate(settings):
        at = _path(where, i)
        _obj(s, at)
        _unknown(s, SETTINGS_KEYS + SETTINGS_OPTIONAL_KEYS, at)
        for key in SETTINGS_KEYS:
            _need(s, key, at)
        _int(s["from_bar"], _path(at, "from_bar"))
        if i == 0 and s["from_bar"] > 0:
            raise JamSchemaError(_path(at, "from_bar"), "must be 0 or less: the first settings cover bar 0")
        if last is not None and s["from_bar"] <= last:
            raise JamSchemaError(_path(at, "from_bar"), f"must come after the previous settings' bar {last}")
        last = s["from_bar"]
        _enum(s["groove"], _path(at, "groove"), GROOVES)
        _enum(s["backing"], _path(at, "backing"), BACKINGS)
        _int(s["level"], _path(at, "level"), VELOCITY_MIN, VELOCITY_MAX)
        _num(s["humanize"], _path(at, "humanize"), 0, 1)
        _int(s["seed"], _path(at, "seed"), 0, 2 ** 32 - 1)
        _int(s["walk"], _path(at, "walk"), 0, 1)
        if mode == "try":
            _enum(s["try_backing"], _path(at, "try_backing"), TRY_BACKINGS)
        elif s["try_backing"] is not None:
            raise JamSchemaError(_path(at, "try_backing"), f"must be null outside a try run (got {s['try_backing']!r})")
        _int(s["passes"], _path(at, "passes"), 0)
        _enum(s["ending"], _path(at, "ending"), ENDINGS)
        if "muted" in s:
            _bool(s["muted"], _path(at, "muted"))
        if "dropout" in s:
            _num(s["dropout"], _path(at, "dropout"), 0, 1)


def validate_run(run) -> dict:
    """Return a deep copy of run.json (arsenal.jam.run/v0), or raise JamSchemaError naming the first wrong field.

    Beyond the shape: a pending run has no epochs and no segments yet, anything launched has both; the first segment
    starts the count-in at bar -count_in_bars with the def's cycle at bar 0; later segments sit where the tempo map puts
    them (within 0.1 ms); bar0_epoch_ms is bar 0 under the map; a stopped run is closed with a reason, and only a
    stopped run. A swapped-in run numbers its own bars: its bar 0 is the old run's bar B (9.4).
    """
    if not isinstance(run, dict):
        raise JamSchemaError("run", "must be a JSON object")
    _unknown(run, RUN_KEYS + RUN_OPTIONAL_KEYS, "")
    for key in RUN_KEYS:
        _need(run, key, "")
    if run["api"] != RUN_API:
        raise JamSchemaError("api", f"must be {RUN_API!r} (got {run['api']!r:.60})")
    if not isinstance(run["run"], str) or not RUN_ID_RE.match(run["run"]):
        raise JamSchemaError("run", f"must be a run id like 20300101-000020-7a11c0de (got {run['run']!r:.60})")
    mode = _enum(run["mode"], "mode", MODES)
    _enum(run["route"], "route", ROUTES)
    _text(run, "engine", "", ENGINE_MAX, required=True)
    state = _enum(run["state"], "state", STATES)
    _iso(run["created_at"], "created_at")
    _enum(run["created_by"], "created_by", AUTHORS)
    _def_card(run["card"], "card")
    if run["card"] is None:
        if run["card_snapshot"] is not None:
            raise JamSchemaError("card_snapshot", "must be null when the run plays chords without a card")
    else:
        if run["card_snapshot"] is None:
            raise JamSchemaError("card_snapshot", "is required when the run plays a card")
        try:
            validate_card(run["card_snapshot"], stored=True)
        except JamSchemaError as exc:
            raise _nested("card_snapshot", exc) from None
        if run["card_snapshot"]["id"] != run["card"]["id"] or run["card_snapshot"]["rev"] != run["card"]["rev"]:
            raise JamSchemaError("card_snapshot.id", "must be the card the run names, at the same rev")
    _key_name(run["key"], "key")
    meter = _int(run["beats_per_bar"], "beats_per_bar", METER_MIN, METER_MAX)
    count_in = _int(run["count_in_bars"], "count_in_bars", 0, COUNT_IN_MAX)
    if mode == "play" and count_in:
        raise JamSchemaError("count_in_bars", "must be 0 for a play run")
    last_version = _int(run["last_version"], "last_version", 1)

    segments = _list(run["segments"], "segments")
    launched = bool(segments)
    for key in ("start_epoch_ms", "bar0_epoch_ms"):
        _num(run[key], key, above=0, nullable=True)
        if (run[key] is None) == launched:
            raise JamSchemaError(key, "is required once the run is launched (it has segments)" if launched else
                                 "must be null until the run is launched and has segments")
    if state == "running" and not launched:
        raise JamSchemaError("segments", "must not be empty for a running run")
    if state == "pending" and launched:
        raise JamSchemaError("segments", "must be empty while the run is pending")
    if launched:
        _segments(segments, meter, count_in)
        if abs(segments[0]["epoch_ms"] - run["start_epoch_ms"]) > tempomap.EPS_MS * 1000:
            raise JamSchemaError("segments[0].epoch_ms", "must equal start_epoch_ms")
        want = tempomap.t_epoch(segments, meter, 0)
        if abs(run["bar0_epoch_ms"] - want) > SEGMENT_TOLERANCE_MS:
            raise JamSchemaError("bar0_epoch_ms", f"is {run['bar0_epoch_ms']!r}, but the tempo map puts bar 0 at "
                                                  f"{want!r}")
        for i, seg in enumerate(segments):
            if seg["def_version"] > last_version:
                raise JamSchemaError(f"segments[{i}].def_version", f"is newer than last_version {last_version}")
    _settings(run["settings"], mode)

    if run["owner_page_id"] is not None and (not isinstance(run["owner_page_id"], str) or
                                             not PAGE_ID_RE.match(run["owner_page_id"])):
        raise JamSchemaError("owner_page_id", f"must be a page id or null (got {run['owner_page_id']!r:.60})")
    courtesy = _obj(run["courtesy"], "courtesy")
    _unknown(courtesy, COURTESY_KEYS, "courtesy")
    _num(_need(courtesy, "held_ms", "courtesy"), "courtesy.held_ms", 0)
    _enum(_need(courtesy, "via", "courtesy"), "courtesy.via", COURTESY_VIA, nullable=True)

    closed = _bool(run["closed"], "closed")
    _num(run["stopped_epoch_ms"], "stopped_epoch_ms", above=0, nullable=True)
    _int(run["stop_bar"], "stop_bar", nullable=True)
    reason = _enum(run["stop_reason"], "stop_reason", STOP_REASONS, nullable=True)
    stopped = state == "stopped"
    if closed != stopped:
        raise JamSchemaError("closed", f"must be {str(stopped).lower()} while the state is {state}")
    if (reason is None) == stopped:
        raise JamSchemaError("stop_reason", "is required once the run is stopped" if stopped else
                             "must be null until the run stops")
    if (run["stopped_epoch_ms"] is None) == stopped:
        raise JamSchemaError("stopped_epoch_ms", "is required once the run is stopped" if stopped else
                             "must be null until the run stops")
    _int(run["late_dropped"], "late_dropped", 0)
    if "approx" in run:
        _bool(run["approx"], "approx")
    if "slot" in run:
        _int(run["slot"], "slot", 0, nullable=True)
    if "velocity" in run:
        _int(run["velocity"], "velocity", VELOCITY_MIN, VELOCITY_MAX, nullable=True)
    return copy.deepcopy(run)


# ======================================================================================================== ack
def _ack_body(ack: dict, where: str, extra_allowed: Sequence[str] = ()) -> dict:
    _unknown(ack, ACK_KEYS + tuple(ACK_DEFAULTS) + ACK_OPTIONAL_KEYS + tuple(extra_allowed), where)
    for key in ACK_KEYS:
        _need(ack, key, where)
    page_id = ack["page_id"]
    if not isinstance(page_id, str) or not PAGE_ID_RE.match(page_id):
        raise JamSchemaError(_path(where, "page_id"), f"must be 1 to 80 letters, digits or _ . : - (got {page_id!r:.60})")
    _enum(ack["role"], _path(where, "role"), ACK_ROLES)
    _int(ack["version"], _path(where, "version"), 1)
    _int(ack["bar"], _path(where, "bar"), -COUNT_IN_MAX)
    _num(ack["bar_epoch_ms"], _path(where, "bar_epoch_ms"), above=0)
    _num(ack["perf_ms"], _path(where, "perf_ms"), 0)
    _num(ack["perf_offset_ms"], _path(where, "perf_offset_ms"))
    out = {**ACK_DEFAULTS, **ack}
    _num(out["output_latency_ms"], _path(where, "output_latency_ms"), 0, nullable=True)
    if out["log"] is not None:
        at = _path(where, "log")
        log = _obj(out["log"], at)
        _unknown(log, ACK_LOG_KEYS, at)
        local = _need(log, "local", at)
        if not isinstance(local, str) or not PAGE_ID_RE.match(local):
            raise JamSchemaError(_path(at, "local"), f"must be the log's local id (got {local!r:.60})")
        session = _need(log, "session", at)
        if session is not None and (not isinstance(session, str) or not SESSION_RE.match(session)):
            raise JamSchemaError(_path(at, "session"), f"must be a practice session id or null (got {session!r:.60})")
        _num(_need(log, "t0_perf_ms", at), _path(at, "t0_perf_ms"), 0)
    _enum(out["stopped"], _path(where, "stopped"), ACK_STOPPED, nullable=True)
    _int(out["late_dropped"], _path(where, "late_dropped"), 0)
    if "late_frame_ms" in out:
        _num(out["late_frame_ms"], _path(where, "late_frame_ms"), 0)
    if "offset_step_ms" in out:
        _num(out["offset_step_ms"], _path(where, "offset_step_ms"))
    if "stop_bar" in out:
        _int(out["stop_bar"], _path(where, "stop_bar"), nullable=True)
    if "effective_bar" in out:
        _int(out["effective_bar"], _path(where, "effective_bar"))
    return out


def validate_ack(ack) -> dict:
    """Return the ack with output_latency_ms, log, stopped and late_dropped filled in, or raise JamSchemaError.
    The input is not modified. Idempotence per (page_id, version, bar) is the run store's job."""
    if not isinstance(ack, dict):
        raise JamSchemaError("ack", "must be a JSON object")
    return copy.deepcopy(_ack_body(ack, ""))


# ================================================================================================ event lines
def validate_run_event(line) -> dict:
    """Return a deep copy of one events.jsonl line, or raise JamSchemaError. Every line carries seq, kind,
    recorded_epoch_ms and by; each kind adds its own fields (4.3, DATA 7.2). An ack line is an ack plus those four."""
    if not isinstance(line, dict):
        raise JamSchemaError("line", "must be a JSON object")
    _int(_need(line, "seq", ""), "seq", 0)
    kind = _enum(_need(line, "kind", ""), "kind", EVENT_KINDS)
    _num(_need(line, "recorded_epoch_ms", ""), "recorded_epoch_ms", above=0)
    _enum(_need(line, "by", ""), "by", EVENT_BY)
    if kind == "ack":
        _ack_body(line, "", EVENT_COMMON_KEYS)
        return copy.deepcopy(line)
    _unknown(line, EVENT_COMMON_KEYS + EVENT_REQUIRED[kind] + EVENT_OPTIONAL[kind], "")
    for key in EVENT_REQUIRED[kind]:
        _need(line, key, "")
    if "version" in line:
        _int(line["version"], "version", 1)
    if "epoch_ms" in line:
        _num(line["epoch_ms"], "epoch_ms", above=0, nullable=kind in ("start", "launch", "mark"))
    for key in ("effective_bar", "stop_bar", "bar"):     # null: a pending run has no bars yet
        if key in line:
            _int(line[key], key, nullable=True)
    if "bpm" in line:
        _num(line["bpm"], "bpm", BPM_MIN, BPM_MAX)
    if "def" in line:
        try:
            validate_def(line["def"])
        except JamSchemaError as exc:
            raise _nested("def", exc) from None
    if "card" in line:
        _def_card(line["card"], "card")
    if "key" in line:
        _key_name(line["key"], "key")
    if "variant" in line:
        _enum(line["variant"], "variant", VARIANT_IDS, nullable=True)
    if "at" in line:
        _enum(line["at"], "at", AT_LINES)
    if kind == "start":
        if line["version"] != 1:
            raise JamSchemaError("version", f"must be 1 on a start line (got {line['version']!r})")
        if "state" in line:
            _enum(line["state"], "state", STATES)
        if "mode" in line:
            _enum(line["mode"], "mode", MODES)
    elif kind == "launch":
        for key in ("start_epoch_ms", "bar0_epoch_ms"):
            _num(line[key], key, above=0)
        if not isinstance(line["page_id"], str) or not PAGE_ID_RE.match(line["page_id"]):
            raise JamSchemaError("page_id", f"must be a page id (got {line['page_id']!r:.60})")
        if "held_ms" in line:
            _num(line["held_ms"], "held_ms", 0)
        if "via" in line:
            _enum(line["via"], "via", COURTESY_VIA)
    elif kind == "change":
        op = _enum(line["op"], "op", CHANGE_OPS)
        if line["version"] < 2:
            raise JamSchemaError("version", "must be 2 or more on a change line: the start is version 1")
        if op == "tempo":
            _num(_need(line, "bpm", ""), "bpm", BPM_MIN, BPM_MAX)
        if op == "next":
            _need(line, "def", "")
        if op == "set":
            settings = _obj(_need(line, "settings", ""), "settings")
            _unknown(settings, SETTINGS_KEYS[1:] + SETTINGS_OPTIONAL_KEYS, "settings")
        if "if_version" in line:
            _int(line["if_version"], "if_version", 1)
    elif kind == "mark":
        _text(line, "text", "", MARK_TEXT_MAX, required=True)
        if "run" in line and line["run"] is not None and (not isinstance(line["run"], str) or
                                                          not RUN_ID_RE.match(line["run"])):
            raise JamSchemaError("run", f"must be a run id (got {line['run']!r:.60})")
    elif kind == "stop":
        _enum(line["reason"], "reason", STOP_REASONS)
        if "approx" in line:
            _bool(line["approx"], "approx")
    return copy.deepcopy(line)


# ======================================================================================================= seed
def validate_seed(doc) -> dict:
    """Return a deep copy of arsenal/jam/seed/deck-v1.json, or raise JamSchemaError. The file is tracked and the repo
    is public, so a seed card never carries moments or a replay (the privacy rule): those live in the git-ignored
    moments file. Card ids are unique, each card's source is this seed, and question/answer pairs close."""
    if not isinstance(doc, dict):
        raise JamSchemaError("seed", "must be a JSON object")
    _unknown(doc, SEED_KEYS, "")
    if _need(doc, "api", "") != SEED_API:
        raise JamSchemaError("api", f"must be {SEED_API!r} (got {doc['api']!r:.60})")
    version = _int(_need(doc, "seed_version", ""), "seed_version", 1)
    cards = _list(_need(doc, "cards", ""), "cards", 1)
    seen = set()
    for i, card in enumerate(cards):
        at = _path("cards", i)
        try:
            validate_card(card)
        except JamSchemaError as exc:
            raise _nested(at, exc) from None
        for key in ("moments", "replay"):
            if key in card:
                raise JamSchemaError(_path(at, key), "must stay out of the tracked seed: moment links live only in "
                                                     "state/arsenal/jam/seed/moments-v1.json")
        if card["id"] in seen:
            raise JamSchemaError(_path(at, "id"), f"repeats card {card['id']!r}")
        seen.add(card["id"])
        source = card.get("source")
        if source is not None and (source.get("kind") != "seed" or source.get("seed_version") != version):
            raise JamSchemaError(_path(at, "source"), f"must be {{kind: seed, seed_version: {version}}}")
    problems = pair_problems(cards)
    if problems:
        cid, sentence = problems[0]
        index = next(i for i, c in enumerate(cards) if c["id"] == cid)
        raise JamSchemaError(_path(_path("cards", index), "pair"), sentence)
    return copy.deepcopy(doc)


def validate_seed_moments(doc) -> dict:
    """Return a deep copy of state/arsenal/jam/seed/moments-v1.json ({api, cards: {id: {moments, replay}}}), or raise."""
    if not isinstance(doc, dict):
        raise JamSchemaError("moments", "must be a JSON object")
    _unknown(doc, SEED_MOMENTS_KEYS, "")
    if _need(doc, "api", "") != SEED_MOMENTS_API:
        raise JamSchemaError("api", f"must be {SEED_MOMENTS_API!r} (got {doc['api']!r:.60})")
    cards = _obj(_need(doc, "cards", ""), "cards")
    for cid, entry in cards.items():
        at = _path("cards", cid)
        _card_id(cid, at)
        _obj(entry, at)
        _unknown(entry, SEED_MOMENT_CARD_KEYS, at)
        if "moments" in entry:
            _list(entry["moments"], _path(at, "moments"), 0, MAX_MOMENTS)
            for i, m in enumerate(entry["moments"]):
                _moment(m, _path(_path(at, "moments"), i))
        if "replay" in entry and entry["replay"] is not None:
            _replay(entry["replay"], _path(at, "replay"))
    return copy.deepcopy(doc)
