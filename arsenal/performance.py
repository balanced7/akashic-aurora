"""The practice log: piano sessions on disk, and a pure analyzer the agents can read (PIANO-V2-SPEC sections 4 and 6.5).

A session is a directory under state/arsenal/performance (git-ignored; Daniel's playing never leaves the
machine) holding session.json (opened_at, meta, closed, event_count) and events.jsonl, which is
append-only. Closing writes summary.json and summary.md.

Uploads are idempotent, so a browser that buffered a session offline can resend after a reload without
storing anything twice: open may carry a client_id (a second open with the same id returns the same
session), and events and close may carry seq, a per-session batch number (a batch at or below the last
stored seq is acknowledged and skipped).

summarize(events) is pure and deterministic. It reports numbers only; summary.md is a narrative built
from those numbers, ending with questions for Daniel that are generated from the same numbers.
"""
from __future__ import annotations

import json
import math
import re
import secrets
import shutil
import threading
import time
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional

API = "arsenal.performance/v0"
SUMMARY_API = "arsenal.performance.summary/v0"
DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "state" / "arsenal" / "performance"
SESSION_PATTERN = r"\d{8}-\d{6}-[0-9a-f]{8}"
_SESSION_RE = re.compile(rf"^{SESSION_PATTERN}$")
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,80}$")
KINDS = ("on", "off", "pedal", "chord", "sound_end")
SOUND_END_BY = ("release", "pedal", "repeat", "all-off")
CHORD_TEXT_FIELDS = ("bass", "nns", "nns_key", "key_conf", "detect_kind")  # optional on chord events: a string or null

# Analyzer constants. Each one is written into the summary, so every number can be reproduced by hand.
ONSET_MERGE_MS = 40      # note-ons within 40 ms of a group's first onset count as one onset (a chord, a roll)
IOI_BIN_MS = 50          # inter-onset-interval histogram bin width
IOI_MAX_MS = 2000        # gaps at or above this are counted as pauses, not binned
TEMPO_BPM = (60, 200)    # the rough tempo looks only at gaps in this range (1000 ms down to 300 ms)
TEMPO_WINDOW_MS = 25     # a gap's cluster is every in-range gap within 25 ms of it
MIN_MOVE_MS = 120        # chord segments shorter than this are passing shapes: kept in the timeline, not in moves
TOP_N = 10
MD_TIMELINE_ROWS = 24
MD_MIN_ROW_S = 0.3       # summary.md's timeline tables list stretches this long or longer; the heading counts the rest
LT_SHARE = 0.25          # the piano's key tracker (nashville.js rankKeys): a minor key whose raised 7th sounded for
LT_EDGE = 0.08           # under a quarter of its tonic's time ranks up to 0.08 under its relative major,
LT_FLOOR = 0.02          # but no lower than 0.02 above its parallel major once that major outscores the relative
LT_FLOOR_FADE = 0.16     # major (in full when by 0.16): the rule only chooses between a minor key and its relative major
HOME_SHARE = 0.15        # its home-chord rule: while a minor chord sounds for 15% of the chord time and its natural-minor
HOME_FIT = 0.03          # scale holds all but 3% of the sounding time, a key that leaves out 4% or more ranks LT_EDGE
HOME_OUT = 0.04          # under the better of that minor key and its relative major (Am G F G is never G major)
AREA_FRAME_MS = 1000     # key areas (each part of a session numbered in its own key): one step a second, scoring
AREA_CONTEXT_MS = 10000  # the sounding time in the 10 s around it (arsenal/practice.py's key path steps the same way)
AREA_SWITCH_PENALTY = 3.0  # the path pays this, in summed score, per key change
AREA_MIN_HEARD_MS = 1500   # a step hearing less than this, or fewer than 3 pitch classes, scores every key alike
AREA_FIT_WEIGHT = 1.0      # a step's score adds this times (the share of its sounding time inside the key's scale - 1)
AREA_SNAP_MS = 5000        # a key change moves to the nearest note-on this close (else to where playing resumes), then to
                           # the chord start this close that leaves the least chord time outside the keys on either side
AREA_MIN_MS = 30000        # a key area with less playing than this joins the neighbour whose key leaves out less of its sound,
AREA_GAP_MS = 10000        # but never across a silence this long into a key that leaves out more than AREA_GAP_FIT more
AREA_GAP_FIT = 0.03        # of it than its own key does (what was played after a long pause is not carried back into the
AREA_ALONE_MS = 5000       # key before it); a part with less playing than AREA_ALONE_MS always joins
AREA_APART_FIT = 0.20      # without a silence, a part still stands when a neighbour's key leaves out this much more of its
                           # sound than its own does (a Db phrase opening a D major session); a 19 s D major excursion inside
                           # C major (0.15 more) joins, as the 30 s minimum intends
PEDAL_RING_MS = 10000      # a note released under the pedal counts as sounding for this long at most: a pedal held through
                           # a pause counted the last chord for the whole pause, and the key areas heard a key in the silence
LOOP_LENGTHS = (3, 4)    # a loop is 3 or 4 different numbers played back to back, at least twice in a row
OUTSIDE_LISTED = 40      # outside-the-key moments kept in summary.json (all of them are counted)

# Krumhansl-Kessler probe-tone profiles, index 0 = tonic (the same numbers piano.js uses).
KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
MAJOR_KEY_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MINOR_KEY_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]
PC_NEUTRAL = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
PC_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PC_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_NOTE_RE = re.compile(r"^([A-G])(#{0,2}|b{0,2})(-?\d+)$")
_PC_NAME_RE = re.compile(r"^([A-G])(#{0,2}|b{0,2})(-?\d+)?$")
NUMBERS_READER = "arsenal.nashville"  # the Python twin of the overlay's nashville.js, so both number chords alike


# =============================================================================================== errors
class PerformanceError(Exception):
    status = 400

    def __init__(self, message: str = "", **extra):
        super().__init__(message)
        self.extra = extra  # merged into the JSON error body (a 409 carries last_seq)


class BadEvent(PerformanceError):
    status = 400


class UnknownSession(PerformanceError):
    status = 404


class SessionClosed(PerformanceError):
    status = 409


# =========================================================================================== validation
def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def validate_event(event, i: int = 0) -> None:
    """Raise BadEvent unless the event matches the section 4 / 6.5 shape. Fields not named here pass through."""
    where = f"event {i}"
    if not isinstance(event, dict):
        raise BadEvent(f"{where} is not an object")
    t = event.get("t_ms")
    if not _is_int(t) or t < 0:
        raise BadEvent(f"{where} needs t_ms, a non-negative integer (got {t!r})")
    kind = event.get("kind")
    if kind not in KINDS:
        raise BadEvent(f"{where} has kind {kind!r}; expected one of {', '.join(KINDS)}")
    if kind in ("on", "off", "sound_end"):
        note = event.get("note")
        if not _is_int(note) or not 0 <= note <= 127:
            raise BadEvent(f"{where} ({kind}) needs note, an integer 0..127 (got {note!r})")
        if kind == "on":
            vel = event.get("vel")
            if not _is_int(vel) or not 1 <= vel <= 127:
                raise BadEvent(f"{where} (on) needs vel, an integer 1..127 (got {vel!r})")
        if kind == "sound_end" and event.get("by") not in SOUND_END_BY:
            raise BadEvent(f"{where} (sound_end) needs by, one of {', '.join(SOUND_END_BY)} (got {event.get('by')!r})")
    elif kind == "pedal":
        if not isinstance(event.get("down"), bool):
            raise BadEvent(f"{where} (pedal) needs down, a boolean (got {event.get('down')!r})")
        value = event.get("value")
        if not _is_int(value) or not 0 <= value <= 127:
            raise BadEvent(f"{where} (pedal) needs value, an integer 0..127 (got {value!r})")
    else:
        for field in ("chord", "notes", "key"):
            if field not in event:
                raise BadEvent(f"{where} (chord) needs {field}")
        if event["chord"] is not None and not isinstance(event["chord"], str):
            raise BadEvent(f"{where} (chord) needs chord, a string or null")
        notes = event["notes"]
        if not isinstance(notes, list) or not all(isinstance(n, str) for n in notes):
            raise BadEvent(f"{where} (chord) needs notes, a list of strings")
        if event["key"] is not None and not isinstance(event["key"], str):
            raise BadEvent(f"{where} (chord) needs key, a string or null")
        for field in CHORD_TEXT_FIELDS:
            if event.get(field) is not None and not isinstance(event[field], str):
                raise BadEvent(f"{where} (chord) {field} must be a string or null (got {event[field]!r})")
        if "locked" in event and not isinstance(event["locked"], bool):
            raise BadEvent(f"{where} (chord) locked must be a boolean (got {event['locked']!r})")


def validate_events(events) -> None:
    if not isinstance(events, list):
        raise BadEvent("events must be a list")
    for i, event in enumerate(events):
        validate_event(event, i)


def _check_seq(seq) -> None:
    if seq is not None and (not _is_int(seq) or seq < 0):
        raise BadEvent(f"seq must be a non-negative integer (got {seq!r})")


def _last_seq(info: dict) -> int:
    value = info.get("last_seq")
    return value if _is_int(value) else -1


# ================================================================================================ store
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class PerformanceStore:
    def __init__(self, root=None):
        self.root = Path(root) if root else DEFAULT_ROOT
        self._lock = threading.Lock()

    # --------------------------------------------------------------------------------------- helpers
    def _dir(self, session) -> Path:
        if not isinstance(session, str) or not _SESSION_RE.match(session):
            raise UnknownSession(f"not a session id: {session!r}")
        path = self.root / session
        if not (path / "session.json").is_file():
            raise UnknownSession(f"no session {session}")
        return path

    def _read(self, session: str) -> dict:
        return json.loads((self._dir(session) / "session.json").read_text(encoding="utf-8"))

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8", newline="\n")  # the same bytes on every machine
        tmp.replace(path)

    def _write(self, session: str, info: dict) -> None:
        self._write_text(self._dir(session) / "session.json", json.dumps(info, indent=2, sort_keys=True, default=str))

    def _append_locked(self, session: str, info: dict, events: List[dict]) -> int:
        validate_events(events)  # the whole batch first: nothing from a refused batch is written
        if not events:
            return 0
        with open(self._dir(session) / "events.jsonl", "a", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(e, sort_keys=True) + "\n" for e in events))
        info["event_count"] = int(info.get("event_count", 0)) + len(events)
        info["last_t_ms"] = max([int(info.get("last_t_ms", 0))] + [e["t_ms"] for e in events])
        info["duration_s"] = round(info["last_t_ms"] / 1000, 3)
        return len(events)

    def _events_locked(self, session: str) -> List[dict]:
        raw = (self._dir(session) / "events.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in raw.splitlines() if line.strip()]

    def _infos(self) -> List[dict]:
        """Every readable session.json under the root (unordered)."""
        if not self.root.is_dir():
            return []
        out = []
        for path in self.root.iterdir():
            if not (path.is_dir() and _SESSION_RE.match(path.name)):
                continue
            try:
                info = json.loads((path / "session.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            info.setdefault("session", path.name)
            out.append(info)
        return out

    # ------------------------------------------------------------------------------------------- API
    def open(self, meta: Optional[dict] = None, client_id: Optional[str] = None) -> str:
        return self.open_session(meta, client_id)["session"]

    def open_session(self, meta: Optional[dict] = None, client_id: Optional[str] = None) -> dict:
        """Returns {session}; with a client_id also {resumed, closed, last_seq}, and an earlier session opened with
        that client_id is returned instead of a new one, so a client that lost the first answer cannot open twice."""
        if meta is None:
            meta = {}
        if not isinstance(meta, dict):
            raise BadEvent("meta must be an object")
        if client_id is not None and (not isinstance(client_id, str) or not _CLIENT_ID_RE.match(client_id)):
            raise BadEvent("client_id must be 1 to 80 letters, digits or _ . : -")
        with self._lock:
            if client_id is not None:
                for info in self._infos():
                    if info.get("client_id") == client_id:
                        return {"session": info["session"], "resumed": True, "closed": bool(info.get("closed")),
                                "last_seq": _last_seq(info)}
            self.root.mkdir(parents=True, exist_ok=True)
            while True:
                session = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4)
                path = self.root / session
                try:
                    path.mkdir()
                    break
                except FileExistsError:
                    continue
            (path / "events.jsonl").touch()
            info = {"api": API, "session": session, "opened_at": _now_iso(), "opened_ns": time.time_ns(), "meta": meta,
                    "closed": False, "event_count": 0, "last_t_ms": 0, "duration_s": 0.0}
            if client_id is not None:
                info["client_id"] = client_id
            self._write_text(path / "session.json", json.dumps(info, indent=2, sort_keys=True, default=str))
        out = {"session": session}
        if client_id is not None:
            out.update(resumed=False, closed=False, last_seq=-1)
        return out

    def append(self, session: str, events, seq: Optional[int] = None) -> int:
        return self.append_batch(session, events, seq)["accepted"]

    def append_batch(self, session: str, events, seq: Optional[int] = None) -> dict:
        """Returns {accepted}; with a seq also {duplicate, last_seq}. A seq at or below the last stored one is skipped."""
        _check_seq(seq)
        with self._lock:
            info = self._read(session)
            if info.get("closed"):
                raise SessionClosed(f"session {session} is closed", last_seq=_last_seq(info))
            if seq is not None and seq <= _last_seq(info):
                return {"accepted": 0, "duplicate": True, "last_seq": _last_seq(info)}
            accepted = self._append_locked(session, info, events)
            if seq is not None:
                info["last_seq"] = seq
            if accepted or seq is not None:
                self._write(session, info)
            out = {"accepted": accepted}
            if seq is not None:
                out.update(duplicate=False, last_seq=seq)
            return out

    def close(self, session: str, events=None, seq: Optional[int] = None) -> dict:
        """Append any final events (a pagehide beacon carries them), then write summary.json and summary.md.

        Everything that depends on the content (validation, the summary, both renders) runs before the first
        write. If any of it fails, nothing is written and the session stays open exactly as it was, so a client
        that retries the same close does not store its final events twice. A seq at or below the last stored
        one means the final events are already stored: they are skipped and the session just closes.
        """
        _check_seq(seq)
        with self._lock:
            info = self._read(session)
            if info.get("closed"):
                raise SessionClosed(f"session {session} is already closed", last_seq=_last_seq(info))
            final = [] if events is None else events
            if seq is not None and seq <= _last_seq(info):
                final = []
            validate_events(final)
            summary = summarize(self._events_locked(session) + list(final))
            closed_at = _now_iso()
            doc = {"session": session, "opened_at": info.get("opened_at"), "closed_at": closed_at,
                   "meta": info.get("meta") or {}, **summary}
            summary_json = json.dumps(doc, indent=2, ensure_ascii=False)
            summary_md = render_markdown(doc)
            # ---- writes from here on
            path = self._dir(session)
            if final:
                self._append_locked(session, info, final)
            if seq is not None and seq > _last_seq(info):
                info["last_seq"] = seq
            self._write_text(path / "summary.json", summary_json)
            self._write_text(path / "summary.md", summary_md)
            info.update(closed=True, closed_at=closed_at, duration_s=summary["duration_s"])
            self._write(session, info)
            return doc

    def get(self, session: str) -> dict:
        with self._lock:
            info = self._read(session)
            summary = None
            if info.get("closed"):
                summary = json.loads((self._dir(session) / "summary.json").read_text(encoding="utf-8"))
            return {"session": session, "summary": summary}

    def events(self, session: str) -> List[dict]:
        with self._lock:
            self._read(session)
            return self._events_locked(session)

    def info(self, session: str) -> dict:
        with self._lock:
            return self._read(session)

    def markdown(self, session: str) -> str:
        """summary.md for a closed session; a provisional render (nothing written) for an open one."""
        with self._lock:
            info = self._read(session)
            path = self._dir(session)
            if info.get("closed"):
                return (path / "summary.md").read_text(encoding="utf-8")
            doc = {"session": session, "opened_at": info.get("opened_at"), "closed_at": None,
                   "meta": info.get("meta") or {}, **summarize(self._events_locked(session))}
        return render_markdown(doc)

    def list(self) -> List[Dict]:
        rows = [(int(info.get("opened_ns", 0)), info["session"],
                 {"session": info["session"], "opened_at": info.get("opened_at"), "closed": bool(info.get("closed")),
                  "event_count": int(info.get("event_count", 0)), "duration_s": info.get("duration_s", 0.0)})
                for info in self._infos()]
        rows.sort(key=lambda row: (row[0], row[1]), reverse=True)  # the id starts with the local open time
        return [row[2] for row in rows]

    def latest(self) -> Optional[str]:
        """The newest session's id, or None when there are none."""
        rows = self.list()
        return rows[0]["session"] if rows else None

    def older_than(self, days: float, now_ns: Optional[int] = None) -> List[Dict]:
        """Sessions opened (by the server's clock) more than `days` ago, oldest first. Nothing is deleted here."""
        cutoff = (time.time_ns() if now_ns is None else now_ns) - int(days * 86400 * 1_000_000_000)
        rows = [info for info in self._infos() if int(info.get("opened_ns", 0)) < cutoff]
        rows.sort(key=lambda info: (int(info.get("opened_ns", 0)), info["session"]))
        return [{"session": info["session"], "opened_at": info.get("opened_at"), "closed": bool(info.get("closed")),
                 "event_count": int(info.get("event_count", 0)), "duration_s": info.get("duration_s", 0.0)}
                for info in rows]

    def delete(self, session: str) -> None:
        """Remove one session directory. Only the CLI's prune calls this, and only after --yes."""
        with self._lock:
            shutil.rmtree(self._dir(session))


# ============================================================================================= analyzer
def _r(x, places: int = 4):
    return None if x is None else round(float(x), places)


def _pearson(xs: List[float], ys: List[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else 0.0


def _key_name(tonic: int, mode: str) -> str:
    return (MAJOR_KEY_NAMES if mode == "major" else MINOR_KEY_NAMES)[tonic] + " " + mode


def estimate_key(weights: List[float]) -> Optional[dict]:
    """Krumhansl-Kessler: correlate the 12 pitch-class weights with all 24 rotated profiles."""
    if len(weights) != 12 or sum(weights) <= 0:
        return None
    candidates = []
    for tonic in range(12):
        rotated = [weights[(i + tonic) % 12] for i in range(12)]
        for mode, profile in (("major", KK_MAJOR), ("minor", KK_MINOR)):
            candidates.append((_pearson(rotated, profile), tonic, mode))
    if all(r == 0.0 for r, _, _ in candidates):
        return None  # every pitch class weighs the same: there is no key to read
    order = sorted(range(len(candidates)), key=lambda i: (-candidates[i][0], i))
    (r1, t1, m1), (r2, t2, m2) = candidates[order[0]], candidates[order[1]]
    return {"method": "Krumhansl-Kessler", "best": {"key": _key_name(t1, m1), "tonic": t1, "mode": m1, "r": _r(r1)},
            "runner_up": {"key": _key_name(t2, m2), "tonic": t2, "mode": m2, "r": _r(r2)},
            "margin": _r(r1 - r2)}


def _leading_tone(minor_key: str) -> str:
    """A minor key's raised 7th, spelled on the letter below its tonic: C# in D minor, F## in G# minor."""
    m = _PC_NAME_RE.match(minor_key.split(" ")[0])
    letters = "CDEFGAB"
    letter = letters[letters.index(m.group(1)) - 1]
    acc = (_LETTER_PC[m.group(1)] + _acc(m.group(2)) - 1 - _LETTER_PC[letter] + 6) % 12 - 6
    return letter + ("#" * acc if acc > 0 else "b" * -acc)


def _out_share(weights: List[float], tonic: int, mode: str) -> float:
    """Share of the weight outside a key's scale, a minor key's leading tone counted in (nashville.js outShare)."""
    scale = (0, 2, 4, 5, 7, 9, 11) if mode == "major" else (0, 2, 3, 5, 7, 8, 10, 11)
    total = sum(weights)
    return sum(w for pc, w in enumerate(weights) if (pc - tonic) % 12 not in scale) / total if total > 0 else 0.0


def home_chords(chord_events: List[dict], duration_ms: int, reader=None) -> dict:
    """How long each minor chord sounded, for the home-chord rule, as the piano key tracker counts it (nashville.js
    homeChordOf): chord_ms is the time any chord sounded, minor_ms[tonic] the time a minor chord on that tonic did. A
    minor triad over the bass counts under any name (with the pedal down, melody notes rename an Am bar C6/9/A, Cadd9/A
    or a cluster), and so does any minor-family chord (Am/C); any other cluster is no chord time. Each chord event
    lasts until the next one or the session's end."""
    if reader is None:
        reader = _numbers_reader()[0]
    out = {"chord_ms": 0, "minor_ms": [0] * 12}
    evs = sorted(chord_events, key=lambda e: e["t_ms"])
    for e, nxt in zip(evs, evs[1:] + [None]):
        name = e.get("chord")
        if name is None:
            continue
        span = max(0, (nxt["t_ms"] if nxt else duration_ms) - e["t_ms"])
        midis = [_parse_note(n) for n in (e.get("notes") or []) if isinstance(n, str)]
        midis = [m for m in midis if m is not None]
        kind = _read_as(e.get("notes"), e.get("detect_kind"))
        parsed = reader.parse_chord(name) if reader else None
        if kind is None:
            kind = parsed["kind"] if parsed else "cluster" if len(midis) >= 3 else None
        home = None
        if len({m % 12 for m in midis}) >= 3:
            bass, pcs = min(midis) % 12, {m % 12 for m in midis}
            if (bass + 3) % 12 in pcs and (bass + 7) % 12 in pcs:
                home = bass
        if home is None and kind == "chord" and parsed and parsed["kind"] == "chord" \
                and reader.FAMILY.get(parsed["suffix"]) == "min":
            home = (_LETTER_PC["CDEFGAB"[parsed["root"][0]]] + parsed["root"][1]) % 12
        if kind == "chord" or home is not None:
            out["chord_ms"] += span
            if home is not None:
                out["minor_ms"][home] += span
    return out


def _leading_tone_score(r: float, tonic_w: float, lt_w: float, r_rel: float, r_par: float) -> float:
    """A minor key's score under the leading-tone rule (numbering_key): r sinks toward its relative major's r_rel as its
    raised 7th (weight lt_w) is missing, but never under its parallel major's r_par once that outscores r_rel."""
    heard = min(1.0, lt_w / (LT_SHARE * tonic_w)) if tonic_w > 0 else 0.0
    score = r - (1 - heard) * max(0.0, r - r_rel + LT_EDGE)
    floor = min(r, r_par + LT_FLOOR)
    if floor > score:  # never under the parallel major once that major outscores the relative major
        score += min(1.0, max(0.0, (r_par - r_rel) / LT_FLOOR_FADE)) * (floor - score)
    return score


def numbering_key(weights: List[float], key: Optional[dict], homes: Optional[dict] = None) -> Optional[dict]:
    """The key the Nashville numbers count from: the Krumhansl-Kessler scores re-ranked by the piano key tracker's
    leading-tone and home-chord rules (nashville.js rankKeys at full maturity), so the summary settles where the HUD does.

    A minor key whose raised 7th sounded for less than LT_SHARE of its tonic's weight is demoted, in proportion to
    how little it sounded, to LT_EDGE under its relative major; major keys keep their score. A loop of F/A C/G Dm
    Bbmaj7 weighs most like D minor, but no C# ever sounds, so it is numbered in F major. The rule only decides
    between a minor key and its relative major, so the demotion stops LT_FLOOR above the parallel major: a
    harmonic-minor loop whose G# is light stays A minor instead of turning into A major.

    homes (home_chords) turns on the home-chord rule: while a minor chord sounded for HOME_SHARE of the chord time and
    its natural-minor scale holds all but HOME_FIT of the weight, a key that leaves out HOME_OUT or more ranks LT_EDGE
    under the better of that minor key and its relative major. Am G F G weighs like G major, but F sounds a quarter
    of the time and every note is on A minor's scale, so it is numbered in C major. rule is None when the estimate's
    best key stands, else it names the rule, the key it demoted and why.
    """
    if not key:
        return None
    r_of: Dict[tuple, float] = {}
    for tonic in range(12):
        rotated = [weights[(i + tonic) % 12] for i in range(12)]
        for mode, profile in (("major", KK_MAJOR), ("minor", KK_MINOR)):
            r_of[(tonic, mode)] = _pearson(rotated, profile)
    ranked = []
    for i, ((tonic, mode), r) in enumerate(r_of.items()):
        score = r
        if mode == "minor":
            score = _leading_tone_score(r, weights[tonic], weights[(tonic + 11) % 12],
                                        r_of[((tonic + 3) % 12, "major")], r_of[(tonic, "major")])
        ranked.append((score, i, tonic, mode, r))
    first = min(ranked, key=lambda x: (-x[0], x[1]))  # ties go to estimate_key's order
    chord_ms = homes["chord_ms"] if homes else 0
    home = None  # the minor chord whose rule demoted the leading-tone winner
    if chord_ms > 0:
        scores = {(t, m): s for s, _, t, m, _ in ranked}
        for tonic in range(12):  # in tonic order, each cap seeing the ones before it, as rankKeys does
            rel = (tonic + 3) % 12
            if homes["minor_ms"][tonic] < HOME_SHARE * chord_ms or _out_share(weights, rel, "major") > HOME_FIT:
                continue
            pair = ((rel, "major"), (tonic, "minor"))
            cap = max(scores[k] for k in pair) - LT_EDGE
            for k, s in scores.items():
                if k not in pair and s > cap and _out_share(weights, *k) >= HOME_OUT:
                    scores[k] = cap
                    home = tonic if k == (first[2], first[3]) else home
        ranked = [(scores[(t, m)], i, t, m, r) for _, i, t, m, r in ranked]
    score, _, tonic, mode, r = min(ranked, key=lambda x: (-x[0], x[1]))
    out = {"key": _key_name(tonic, mode), "tonic": tonic, "mode": mode, "r": _r(r), "score": _r(score),
           "estimate": key["best"]["key"], "runner_up": key["runner_up"]["key"], "runner_up_r": key["runner_up"]["r"],
           "rule": None}
    best = key["best"]
    if (tonic, mode) != (first[2], first[3]) and home is not None:
        dt, dm = first[2], first[3]
        scale = (0, 2, 4, 5, 7, 9, 11) if dm == "major" else (0, 2, 3, 5, 7, 8, 10, 11)
        names = _pc_names({"best": {"tonic": tonic, "mode": mode}})
        left = max((pc for pc in range(12) if (pc - dt) % 12 not in scale), key=lambda pc: (weights[pc], -pc))
        out["rule"] = {"name": "home chord", "demoted": _key_name(dt, dm), "r": _r(first[4]),
                       "home_chord": names[home] + "m", "home_share": _r(homes["minor_ms"][home] / chord_ms),
                       "left_out": names[left], "left_out_share": _r(_out_share(weights, dt, dm)),
                       "minor_key": _key_name(home, "minor"), "relative_major": _key_name((home + 3) % 12, "major")}
        points_to = (out["rule"]["minor_key"], out["rule"]["relative_major"])
    elif out["key"] != best["key"]:
        tonic_w = weights[best["tonic"]]
        out["rule"] = {"name": "leading tone", "demoted": best["key"], "leading_tone": _leading_tone(best["key"]),
                       "leading_tone_share": _r(weights[(best["tonic"] + 11) % 12] / tonic_w if tonic_w else 0.0),
                       "relative_major": _key_name((best["tonic"] + 3) % 12, "major")}
        points_to = (out["rule"]["relative_major"],)
    else:
        return out
    if out["key"] not in points_to:
        # The rule counted the key the notes weigh most like lower, but the key that won is not the one the rule points
        # to: F# minor's missing E# points to A major, and D major fitted better than A major (verifier, 2026-09-14: the
        # summary said the missing raised 7th made the numbers count from D major). Named "next best", with its cause.
        out["rule"] = dict(out["rule"], name="next best", because=out["rule"]["name"])
    return out


def _centred(profile: List[float]) -> List[float]:
    mean = sum(profile) / len(profile)
    norm = math.sqrt(sum((p - mean) ** 2 for p in profile))
    return [(p - mean) / norm for p in profile]


_KK_MAJOR_Z, _KK_MINOR_Z = _centred(KK_MAJOR), _centred(KK_MINOR)


def _pc_timelines(spans: List[tuple]) -> List[tuple]:
    """Per pitch class, the merged stretches it sounds in (spans are (start_ms, end_ms, pc)) and their running totals."""
    out = []
    for pc in range(12):
        merged: List[list] = []
        for a, b in sorted((a, b) for a, b, p in spans if p == pc and b > a):
            if merged and a <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], b)
            else:
                merged.append([a, b])
        totals = [0]
        for a, b in merged:
            totals.append(totals[-1] + b - a)
        out.append(([a for a, _ in merged], merged, totals))
    return out


def _sounded_before(timeline: tuple, t: float) -> float:
    starts, merged, totals = timeline
    i = bisect_right(starts, t)
    return totals[i - 1] + min(t, merged[i - 1][1]) - merged[i - 1][0] if i else 0.0


def _area_scores(hist: List[float]) -> List[float]:
    """The 24 keys' scores for one step of the key path (index tonic * 2, + 1 for minor): Krumhansl-Kessler r under the
    leading-tone rule, plus AREA_FIT_WEIGHT times (the share of the sounding time inside the key's scale - 1)."""
    mean = sum(hist) / 12
    spread = math.sqrt(sum((h - mean) ** 2 for h in hist))
    if spread == 0:
        return [0.0] * 24
    r = {}
    for t in range(12):
        rotated = hist[t:] + hist[:t]
        r[(t, "major")] = sum(h * z for h, z in zip(rotated, _KK_MAJOR_Z)) / spread
        r[(t, "minor")] = sum(h * z for h, z in zip(rotated, _KK_MINOR_Z)) / spread
    out = []
    for t in range(12):
        for mode in ("major", "minor"):
            score = r[(t, mode)]
            if mode == "minor":
                score = _leading_tone_score(score, hist[t], hist[(t + 11) % 12], r[((t + 3) % 12, "major")], r[(t, "major")])
            out.append(score - AREA_FIT_WEIGHT * _out_share(hist, t, mode))
    return out


def _area_path(rows: List[Optional[List[float]]]) -> List[int]:
    """Viterbi over the 24 keys: the most total score, less AREA_SWITCH_PENALTY per change. A row of None scores
    every key alike."""
    score: List[float] = [0.0] * 24
    back: List[List[int]] = []
    for row in rows:
        top = max(range(24), key=lambda k: score[k])
        back.append([k if score[k] >= score[top] - AREA_SWITCH_PENALTY else top for k in range(24)])
        score = [max(score[k], score[top] - AREA_SWITCH_PENALTY) + (row[k] if row else 0.0) for k in range(24)]
    state = max(range(24), key=lambda k: score[k])
    path = [state]
    for pointers in reversed(back[1:]):
        state = pointers[state]
        path.append(state)
    return path[::-1]


def key_areas(spans: List[tuple], chord_events: List[dict], duration_ms: int, nkey: Optional[dict],
              reader=None) -> List[dict]:
    """The session's key areas, [{start_ms, end_ms, key}] with key a numbering_key result. A session in one key is one
    area numbered in nkey, the session's own numbering key. A session that moves (F major, then D major) is numbered
    part by part, each in the key that fits it, instead of in one key that neither part is in.

    A Viterbi path over the 24 keys, one step every AREA_FRAME_MS scoring the sounding time around it (Krumhansl-
    Kessler r under the leading-tone rule, plus the share inside the key's scale), pays AREA_SWITCH_PENALTY per change;
    a change snaps to a nearby note-on. Parts are cut where playing resumes after a silence of AREA_GAP_MS. A part with
    less playing than AREA_MIN_MS joins the neighbour whose key leaves out less of it, but not across such a silence
    into a key that fits it worse (AREA_GAP_FIT), nor into one that leaves out AREA_APART_FIT more of it: an opening
    phrase in Db, 13 s of silence and a chromatic line, then D major, was numbered in D major, and 13 s in Ab after a 27 s
    pause was numbered with the Eb stretch before the pause as one Ab major area (verifier, 2026-09-14). Each part then
    gets its own numbering key (its own leading-tone and home-chord rules), and neighbours whose numbering keys agree join
    (A minor and C major steps of one Am F C G loop are one C major area). Last, each key change moves to the chord start
    within AREA_SNAP_MS that leaves the least chord time outside the key on either side: the path's 10 s context put the
    change a chord or two late, and the new key's first chords were flagged as outside the old key."""
    whole = [{"start_ms": 0, "end_ms": duration_ms, "key": nkey}]
    if not nkey or not spans or duration_ms < 2 * AREA_MIN_MS:
        return whole
    lines = _pc_timelines(spans)
    rows: List[Optional[List[float]]] = []
    for k in range(math.ceil(duration_ms / AREA_FRAME_MS)):
        centre = (k + 0.5) * AREA_FRAME_MS
        lo, hi = max(0.0, centre - AREA_CONTEXT_MS / 2), min(float(duration_ms), centre + AREA_CONTEXT_MS / 2)
        hist = [_sounded_before(line, hi) - _sounded_before(line, lo) for line in lines]
        heard = sum(hist) >= AREA_MIN_HEARD_MS and sum(1 for h in hist if h > 0) >= 3
        rows.append(_area_scores(hist) if heard else None)
    onsets = sorted({a for a, _, _ in spans})
    parts: List[dict] = []
    for k, state in enumerate(_area_path(rows)):
        if parts and parts[-1]["state"] == state:
            continue
        t = k * AREA_FRAME_MS
        if parts:
            near = onsets[bisect_left(onsets, t - AREA_SNAP_MS):bisect_right(onsets, t + AREA_SNAP_MS)]
            if near:
                t = min(near, key=lambda x: (abs(x - t), x))
            else:  # a change inside a pause: the new key starts where playing resumes
                i = bisect_right(onsets, t)
                t = onsets[i] if i < len(onsets) else t
            if t <= parts[-1]["start_ms"]:
                continue
            parts[-1]["end_ms"] = t
        parts.append({"state": state, "start_ms": t if parts else 0, "end_ms": duration_ms})

    # when anything sounds, and where playing resumes after a long silence
    cover: List[list] = []
    for a, b in sorted((a, b) for a, b, _ in spans if b > a):
        if cover and a <= cover[-1][1]:
            cover[-1][1] = max(cover[-1][1], b)
        else:
            cover.append([a, b])
    totals = [0]
    for a, b in cover:
        totals.append(totals[-1] + b - a)
    sounding = ([a for a, _ in cover], cover, totals)
    resumes = {b[0] for a, b in zip(cover, cover[1:]) if b[0] - a[1] >= AREA_GAP_MS}

    def played(part: dict) -> float:
        return _sounded_before(sounding, part["end_ms"]) - _sounded_before(sounding, part["start_ms"])

    cut: List[dict] = []
    for part in parts:
        edges = [part["start_ms"]] + sorted(t for t in resumes if part["start_ms"] < t < part["end_ms"]) + [part["end_ms"]]
        pieces = [{"state": part["state"], "start_ms": a, "end_ms": b} for a, b in zip(edges, edges[1:])]
        if len(pieces) > 1:  # each piece of a part cut by a long silence takes the key its own steps score best: the
            for piece in pieces:  # path's 10 s context carries a key a few steps past a silence
                steps = [row for row in rows[piece["start_ms"] // AREA_FRAME_MS:math.ceil(piece["end_ms"] / AREA_FRAME_MS)]
                         if row]
                if steps:
                    piece["state"] = max(range(24), key=lambda s: (sum(row[s] for row in steps), -s))
        cut += pieces
    parts = cut
    for part in parts:
        part["gap"] = part["start_ms"] in resumes  # a long silence ends where this part starts

    def weights_in(a: int, b: int) -> List[float]:
        w = [0.0] * 12
        for s0, s1, pc in spans:
            if s1 > a and s0 < b:
                w[pc] += min(s1, b) - max(s0, a)
        return w

    def left_out(w: List[float], state: int) -> float:
        return _out_share(w, state // 2, "minor" if state % 2 else "major")

    def join(i: int, j: int, state: int) -> None:
        lo, hi = min(i, j), max(i, j)
        parts[lo:hi + 1] = [{"state": state, "start_ms": parts[lo]["start_ms"], "end_ms": parts[hi]["end_ms"],
                             "gap": parts[lo]["gap"]}]

    def join_same() -> None:  # parts of one key join, except across a long silence (a short one may still join there)
        k = 0
        while k < len(parts) - 1:
            if parts[k]["state"] == parts[k + 1]["state"] and not parts[k + 1]["gap"]:
                join(k, k + 1, parts[k]["state"])
            else:
                k += 1

    join_same()
    while len(parts) > 1:
        short = [i for i, part in enumerate(parts) if played(part) < AREA_MIN_MS and not part.get("alone")]
        if not short:
            break
        i = min(short, key=lambda i: (played(parts[i]), i))
        w = weights_in(parts[i]["start_ms"], parts[i]["end_ms"])
        own = left_out(w, parts[i]["state"])
        options = [j for j in (i - 1, i + 1) if 0 <= j < len(parts)
                   and not (played(parts[i]) >= AREA_ALONE_MS and left_out(w, parts[j]["state"]) > own
                            + (AREA_GAP_FIT if (parts[i]["gap"] if j < i else parts[j]["gap"]) else AREA_APART_FIT))]
        if not options:  # every neighbour's key fits it worse: much worse, or worse across a long silence
            parts[i]["alone"] = True
            continue
        j = min(options, key=lambda j: left_out(w, parts[j]["state"]))
        join(i, j, parts[j]["state"])
        join_same()

    def keyed(part: dict) -> dict:
        w = weights_in(part["start_ms"], part["end_ms"])
        estimate = estimate_key(w)
        evs = [e for e in chord_events if part["start_ms"] <= e["t_ms"] < part["end_ms"]]
        part["key"] = numbering_key(w, estimate, home_chords(evs, part["end_ms"], reader)) if estimate else None
        return part

    parts = [keyed(part) for part in parts]
    k = 0
    while k < len(parts) - 1:
        a, b = parts[k], parts[k + 1]
        if a["key"] and b["key"] and a["key"]["key"] != b["key"]["key"]:
            k += 1
            continue
        parts[k:k + 2] = [keyed({"state": a["state"], "start_ms": a["start_ms"], "end_ms": b["end_ms"]})]
        k = max(0, k - 1)
    if len(parts) == 1:
        return whole
    if reader is not None:
        ordered = sorted(chord_events, key=lambda e: e["t_ms"])
        for k in range(len(parts) - 1):
            p, q = parts[k], parts[k + 1]
            if p["key"] and q["key"]:
                q["start_ms"] = p["end_ms"] = _key_change_at(ordered, p, q, duration_ms, reader)
    return [{"start_ms": part["start_ms"], "end_ms": part["end_ms"], "key": part["key"]} for part in parts]


def _key_change_at(ordered: List[dict], p: dict, q: dict, duration_ms: int, reader) -> int:
    """Where the key change between key areas p and q goes: the chord start within AREA_SNAP_MS of it (or the change itself)
    that leaves the least chord time outside p's key before it and q's key after it, the nearest one on a tie. Bb major's
    Cm7 F7 Bbmaj7, then Eb major's Fm7 Bb7 Ebmaj7: the path changed at the Ebmaj7, so Fm7 read as a borrowed 5m7 in Bb."""
    b = q["start_ms"]
    lo, hi = max(p["start_ms"] + 1, b - AREA_SNAP_MS), min(q["end_ms"] - 1, b + AREA_SNAP_MS)
    flags = []
    for i, e in enumerate(ordered):
        if not lo <= e["t_ms"] <= hi or e.get("chord") is None:
            continue
        ms = min(hi, ordered[i + 1]["t_ms"] if i + 1 < len(ordered) else duration_ms) - e["t_ms"]
        before, after = (chord_number(e["chord"], area["key"]["key"], e.get("notes"), reader, e.get("detect_kind"))
                         for area in (p, q))
        flags.append((e["t_ms"], ms, bool(before and before["outside_key"]), bool(after and after["outside_key"])))

    def outside_ms(c: int) -> int:
        return sum(ms for t, ms, out_before, out_after in flags if (out_before if t < c else out_after))

    return min({b} | {t for t, _, _, _ in flags}, key=lambda c: (outside_ms(c), abs(c - b), c))


def _pc_names(key: Optional[dict]) -> List[str]:
    if not key:
        return PC_NEUTRAL
    best = key["best"]
    rel_major = best["tonic"] if best["mode"] == "major" else (best["tonic"] + 3) % 12
    fifths = (rel_major * 7) % 12
    if fifths == 6:  # six accidentals go by the key's name, as Theory.estimateKey: F# major sharps, Eb minor flats
        return PC_SHARP if best["mode"] == "major" else PC_FLAT
    return PC_NEUTRAL if fifths == 0 else PC_SHARP if fifths < 6 else PC_FLAT


def _percentile(sorted_values: List[int], p: int) -> float:
    """Linear interpolation between closest ranks (numpy's default), computed exactly."""
    n = len(sorted_values)
    rank = Fraction(p * (n - 1), 100)
    lo = math.floor(rank)
    hi = min(lo + 1, n - 1)
    return float(sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (rank - lo))


def _acc(text: Optional[str]) -> int:
    return len(text) * (1 if text.startswith("#") else -1) if text else 0


def _parse_note(name: str) -> Optional[int]:
    m = _NOTE_RE.match(name)
    if not m:
        return None
    return (int(m.group(3)) + 1) * 12 + _LETTER_PC[m.group(1)] + _acc(m.group(2))


def _pitch_class(name: str) -> Optional[int]:
    m = _PC_NAME_RE.match(name) if isinstance(name, str) else None
    return None if not m else (_LETTER_PC[m.group(1)] + _acc(m.group(2))) % 12


def _mean(values) -> Optional[float]:
    values = list(values)
    return sum(values) / len(values) if values else None


def _numbers_reader():
    """(the arsenal.nashville module, None), or (None, why) when it cannot be imported. The numbers are an extra:
    a broken reader leaves them out of the summary and never takes the practice log down with it."""
    try:
        from . import nashville
        return nashville, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _read_as(notes, detect_kind) -> Optional[str]:
    """How to read a chord event's name: the page's own detect kind when it sent one, else "note" when `notes` hold
    a single pitch class (piano.js names a note repeated in octaves like a major chord, "C"), else by the name."""
    if detect_kind in ("chord", "interval", "note", "cluster"):
        return detect_kind
    if notes is not None and len({_pitch_class(n) for n in notes} - {None}) == 1:
        return "note"
    return None


def _shape_kind(event: dict, reader) -> Optional[str]:
    """How a chord event's shape reads: "chord", "note", "interval" or "cluster" (the page's detect_kind when it sent one,
    else by its notes and name), None for silence. Without a reader every name counts as a chord."""
    if event.get("chord") is None:
        return None
    kind = _read_as(event.get("notes"), event.get("detect_kind"))
    if kind or reader is None:
        return kind or "chord"
    parsed = reader.parse_chord(event["chord"])
    return parsed["kind"] if parsed else "cluster"


def shape_number(chord: Optional[str], key: Optional[str], notes=None, reader=None, detect_kind=None) -> Optional[dict]:
    """Any shape's number as the piano page writes it, single notes and intervals too: the reader's result dict,
    or None for silence, a cluster, an unreadable key, or no reader."""
    if reader is None:
        reader = _numbers_reader()[0]
    kind = _read_as(notes, detect_kind)
    if reader is None or not chord or not key or kind == "cluster":
        return None
    return reader.nashville_from_name(chord, key, kind=kind) or None


def chord_number(chord: Optional[str], key: Optional[str], notes=None, reader=None, detect_kind=None) -> Optional[dict]:
    """A chord event's Nashville number in a key, as arsenal.nashville writes it: {"number", "outside_key"}, or None
    for silence, a single note, an interval, a cluster, an unreadable key, or no reader.

    outside_key is nashville's diatonic flag inverted: borrowed and chromatic chords are flagged, never judged.
    detect_kind is the page's Theory.detect kind (sent with each chord event); without it a single pitch class in
    `notes` reads as a note, which gets no chord number.
    """
    got = shape_number(chord, key, notes, reader, detect_kind)
    if not got or got.get("kind") != "chord":
        return None
    return {"number": got["text"], "outside_key": not got["diatonic"]}


def _segments(marks: List[tuple], duration_ms: int) -> List[dict]:
    """marks are (t_ms, label, first) in time order. Consecutive identical labels merge (keeping the first
    mark's `first` dict); each segment lasts until the next label, and the last one until the session ends."""
    segments: List[dict] = []
    for t, label, first in marks:
        if segments and segments[-1]["label"] == label:
            continue
        if segments:
            segments[-1]["end_ms"] = t
        segments.append({"label": label, "start_ms": t, "end_ms": t, "first": first})
    if segments:
        segments[-1]["end_ms"] = max(duration_ms, segments[-1]["start_ms"])
    return segments


def _time_by_label(segments: List[dict]) -> Dict:
    by_label: Dict = {}
    for s in segments:
        if s["label"] is None:
            continue
        slot = by_label.setdefault(s["label"], {"ms": 0, "segments": 0, "first": s["first"]})
        slot["ms"] += s["end_ms"] - s["start_ms"]
        slot["segments"] += 1
    return by_label


def _moves(segments: List[dict]) -> tuple:
    """Runs are non-null segments of at least MIN_MOVE_MS with identical neighbours joined; moves are run bigrams,
    ordered by count, then time, then first occurrence. Returns (runs, [((from, to), slot), ...])."""
    runs: List[dict] = []
    for s in segments:
        ms = s["end_ms"] - s["start_ms"]
        if s["label"] is None or ms < MIN_MOVE_MS:
            continue
        if runs and runs[-1]["label"] == s["label"]:
            runs[-1]["ms"] += ms
        else:
            runs.append({"label": s["label"], "ms": ms, "first": s["first"]})
    moves: Dict[tuple, dict] = {}
    for i, (a, b) in enumerate(zip(runs, runs[1:])):
        slot = moves.setdefault((a["label"], b["label"]), {"count": 0, "ms": 0, "first": i,
                                                           "from_first": a["first"], "to_first": b["first"]})
        slot["count"] += 1
        slot["ms"] += a["ms"] + b["ms"]  # the time in both chords of each occurrence
    ordered = sorted(moves.items(), key=lambda kv: (-kv[1]["count"], -kv[1]["ms"], kv[1]["first"]))
    return runs, ordered


def _move_numbers(numbered: Dict[str, tuple]) -> Optional[str]:
    """A chord move's numbers in each key area it was played in ({key: (from, to)}, first played first): "1 → 5 in F major",
    or "4 → 1 in Bb major; 1 → 5 in Eb major" when the same two chords moved in two keys. None when never numbered."""
    return "; ".join(f"{a} → {b} in {k}" for k, (a, b) in numbered.items()) or None


def _clock(ms: int) -> str:
    """m:ss from the session's first note (h:mm:ss past an hour): a time Daniel can find in a recording."""
    s = int(ms) // 1000
    h, m, sec = s // 3600, s // 60 % 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{s // 60}:{sec:02d}"


def _parallel_key(key_name: str) -> str:
    """The same tonic in the other mode: F major -> F minor."""
    tonic, mode = key_name.rsplit(" ", 1)
    return f"{tonic} {'minor' if mode == 'major' else 'major'}"


def _same_key(a: Optional[str], b: Optional[str], reader) -> bool:
    if not a or not b:
        return False
    if reader is None:
        return a == b
    pa, pb = reader.parse_key(a), reader.parse_key(b)
    return bool(pa and pb and (pa["tonic"], pa["mode"]) == (pb["tonic"], pb["mode"]))


def _loops(runs: List[dict]) -> List[dict]:
    """3- and 4-number cycles: n different numbers whose run is repeated back to back (the next n runs, or the
    previous n, are the same). Rotations of one cycle count as one loop, shown in the rotation played most."""
    labels = [r["label"] for r in runs]
    found: Dict[tuple, dict] = {}
    for n in LOOP_LENGTHS:
        for i in range(len(labels) - n + 1):
            gram = tuple(labels[i:i + n])
            if len(set(gram)) < n:
                continue
            if tuple(labels[i + n:i + 2 * n]) != gram and (i < n or tuple(labels[i - n:i]) != gram):
                continue
            slot = found.setdefault(gram, {"count": 0, "first": i})
            slot["count"] += 1
    best: Dict[tuple, tuple] = {}
    for gram, slot in found.items():
        cycle = min(gram[k:] + gram[:k] for k in range(len(gram)))
        held = best.get(cycle)
        if held is None or (slot["count"], -slot["first"]) > (held[1]["count"], -held[1]["first"]):
            best[cycle] = (gram, slot)
    rows = sorted(best.values(), key=lambda gs: (-gs[1]["count"], -len(gs[0]), gs[1]["first"]))
    return [{"numbers": list(gram), "length": len(gram), "count": slot["count"],
             "first_at": _clock(runs[slot["first"]]["first"]["t_ms"]),
             "start_s": _r(runs[slot["first"]]["first"]["t_ms"] / 1000, 3),
             "chords": [runs[slot["first"] + k]["first"]["chord"] for k in range(len(gram))]}
            for gram, slot in rows[:TOP_N]]


def _nashville(chord_events: List[dict], areas: List[dict], reader, duration_ms: int) -> dict:
    """Every chord numbered in the key of its key area (key_areas: the session's numbering_key, unless the session moves
    to another key), beside what the piano page showed live: its key (nns_key, or key from a page that sent none) and
    its own numbers (nns). Where the page counted in another key, its numbers are reported per key and never mixed in.
    Numbers, loops and moves are kept per key: a 1 in F major and a 1 in D major are different chords."""
    starts = [a["start_ms"] for a in areas]
    names = [a["key"]["key"] if a["key"] else None for a in areas]

    def key_at(t_ms: int) -> Optional[str]:
        return names[max(0, bisect_right(starts, t_ms) - 1)]

    marks = []
    for e in chord_events:
        chord, kind, key_name = e.get("chord"), e.get("detect_kind"), key_at(e["t_ms"])
        got = chord_number(chord, key_name, e.get("notes"), reader, kind) if chord is not None and key_name and reader else None
        payload = {"t_ms": e["t_ms"], "chord": chord, "key": key_name, "outside_key": False, "borrowed_from": None,
                   "detect_kind": kind}
        if got:
            payload.update(got)
            if got["outside_key"]:  # borrowed: at home in the parallel key; chromatic: at home in neither
                parallel = _parallel_key(key_name)
                there = chord_number(chord, parallel, e.get("notes"), reader, kind)
                payload["borrowed_from"] = parallel if there and not there["outside_key"] else None
        marks.append((e["t_ms"], (key_name, got["number"]) if got else None, payload))
    segments = _segments(marks, duration_ms)

    def span(s: dict) -> int:
        return s["end_ms"] - s["start_ms"]

    timeline = [{"at": _clock(s["start_ms"]), "start_s": _r(s["start_ms"] / 1000, 3), "seconds": _r(span(s) / 1000, 3),
                 "number": s["label"][1] if s["label"] else None, "key": s["first"]["key"], "chord": s["first"]["chord"],
                 "outside_key": bool(s["first"]["outside_key"])}
                for s in segments]
    by_number = _time_by_label(segments)
    numbered_ms = sum(v["ms"] for v in by_number.values())
    share = (lambda ms: _r(ms / numbered_ms)) if numbered_ms else (lambda ms: 0.0)
    top = [{"number": n, "key": k, "chord": v["first"]["chord"], "seconds": _r(v["ms"] / 1000, 3),
            "segments": v["segments"], "share_of_numbered_time": share(v["ms"]),
            "outside_key": bool(v["first"]["outside_key"]), "first_at": _clock(v["first"]["t_ms"])}
           for (k, n), v in sorted(by_number.items(), key=lambda kv: (-kv[1]["ms"], kv[1]["first"]["t_ms"]))[:TOP_N]]
    runs, moves = _moves(segments)
    moves = [((a, b), v) for (a, b), v in moves if a[0] == b[0]]  # a move stays inside one key
    progressions = [{"from": a[1], "to": b[1], "key": a[0], "count": v["count"], "seconds": _r(v["ms"] / 1000, 3),
                     "share_of_session": _r(v["ms"] / duration_ms if duration_ms else 0.0),
                     "first_at": _clock(v["from_first"]["t_ms"]),
                     "chords": [v["from_first"]["chord"], v["to_first"]["chord"]]}
                    for (a, b), v in moves[:TOP_N]]
    loops = []
    for loop in _loops(runs):
        keys = {label[0] for label in loop["numbers"]}
        if len(keys) == 1:
            loops.append(dict(loop, numbers=[label[1] for label in loop["numbers"]], key=keys.pop()))

    # The key the page showed, carried through a short silence (which sends no key), but not through one of AREA_GAP_MS or
    # to the session's end: carried through minutes of silence, a session read D major for 58% of its length.
    source = next((field for field in ("nns_key", "key") if any(isinstance(e.get(field), str) for e in chord_events)),
                  None)
    key_marks = []
    next_keyed = duration_ms
    for e in reversed(chord_events):
        if source and isinstance(e.get(source), str):
            key_marks.append((e["t_ms"], e[source], {"t_ms": e["t_ms"]}))
            next_keyed = e["t_ms"]
        elif next_keyed - e["t_ms"] >= AREA_GAP_MS:
            key_marks.append((e["t_ms"], None, {"t_ms": e["t_ms"]}))
    key_marks.reverse()
    key_times = [t for t, _, _ in key_marks]

    def page_key_at(t_ms: int) -> Optional[str]:
        i = bisect_right(key_times, t_ms)
        return key_marks[i - 1][1] if i else None

    # outside the key: every stretch long enough to be a chord, not a passing shape, with its time. page_key names
    # the page's key there when it was another one, and in_page_key says the chord belongs to it (a key change).
    outside = [s for s in segments if s["label"] is not None and s["first"]["outside_key"] and span(s) >= MIN_MOVE_MS]
    # edge_key names the key of the neighbouring key area when the chord belongs there and sounds within AREA_SNAP_MS of
    # the change: a key change caught a chord late, not a colour to ask about.
    def edge_key(s: dict) -> Optional[str]:
        i = max(0, bisect_right(starts, s["start_ms"]) - 1)
        for j, near in ((i - 1, s["start_ms"] - areas[i]["start_ms"]), (i + 1, areas[i]["end_ms"] - s["start_ms"])):
            if 0 <= j < len(areas) and names[j] and near <= AREA_SNAP_MS:
                there = chord_number(s["first"]["chord"], names[j], None, reader, s["first"]["detect_kind"])
                if there and not there["outside_key"]:
                    return names[j]
        return None

    moments = []
    for s in outside:
        here = s["first"]["key"]
        shown = page_key_at(s["start_ms"])
        page_key = shown if shown and not _same_key(shown, here, reader) else None
        there = chord_number(s["first"]["chord"], page_key, None, reader) if page_key else None
        moments.append({"at": _clock(s["start_ms"]), "start_s": _r(s["start_ms"] / 1000, 3),
                        "seconds": _r(span(s) / 1000, 3), "number": s["label"][1], "key": here,
                        "chord": s["first"]["chord"], "kind": "borrowed" if s["first"]["borrowed_from"] else "chromatic",
                        "borrowed_from": s["first"]["borrowed_from"], "page_key": page_key,
                        "in_page_key": bool(there and not there["outside_key"]), "edge_key": edge_key(s)})
    grouped: Dict[tuple, dict] = {}
    for s, moment in zip(outside, moments):
        g = grouped.setdefault(s["label"], dict(moment, count=0, ms=0, start_ms=s["start_ms"], times=[]))
        g["count"] += 1
        g["ms"] += span(s)
        g["times"].append(moment["at"])
        if g["edge_key"] != moment["edge_key"]:  # the group is a key change only if every time it sounded was one
            g["edge_key"] = None
    by_outside = [{"number": g["number"], "key": g["key"], "chord": g["chord"], "kind": g["kind"],
                   "borrowed_from": g["borrowed_from"], "page_key": g["page_key"], "in_page_key": g["in_page_key"],
                   "edge_key": g["edge_key"],
                   "count": g["count"], "seconds": _r(g["ms"] / 1000, 3), "first_at": g["times"][0],
                   "times": g["times"][:8]}
                  for g in sorted(grouped.values(), key=lambda g: (-g["ms"], g["start_ms"]))]
    outside_ms = sum(span(s) for s in outside)

    # the page: how long each key held, and its own numbers
    key_segments = [s for s in _segments(key_marks, duration_ms) if s["label"] is not None]
    held_keys: Dict[str, dict] = {}
    for s in key_segments:
        slot = held_keys.setdefault(s["label"], {"ms": 0, "segments": 0, "start_ms": s["start_ms"]})
        slot["ms"] += span(s)
        slot["segments"] += 1
    page_keys = [{"key": k, "seconds": _r(v["ms"] / 1000, 3),
                  "share_of_session": _r(v["ms"] / duration_ms if duration_ms else 0.0), "segments": v["segments"],
                  "first_at": _clock(v["start_ms"])}
                 for k, v in sorted(held_keys.items(), key=lambda kv: (-kv[1]["ms"], kv[1]["start_ms"]))]
    changes = [{"at": _clock(b["start_ms"]), "t_s": _r(b["start_ms"] / 1000, 3), "from": a["label"], "to": b["label"]}
               for a, b in zip(key_segments, key_segments[1:]) if a["label"] != b["label"]]
    # The page numbers single notes and intervals as well as chords, so each of its numbers is compared with this
    # summary's number for the same shape, read the way the page read it (detect_kind), in the key this summary counts
    # that moment in. A name this summary cannot read at all is counted as unread, never as a disagreement.
    compared = in_key = agree = unread = 0
    differ: List[dict] = []
    other: Dict = {}
    for e in chord_events:
        if e.get("chord") is None or not isinstance(e.get("nns"), str) or not e["nns"]:
            continue
        compared += 1
        page_key, key_name = e.get("nns_key") or e.get("key"), key_at(e["t_ms"])
        got = shape_number(e["chord"], key_name, e.get("notes"), reader, e.get("detect_kind")) if key_name and reader else None
        here = got["text"] if got else None
        if key_name and _same_key(page_key, key_name, reader):
            in_key += 1
            if here is None:
                unread += 1
            elif e["nns"] == here:
                agree += 1
            else:
                differ.append({"at": _clock(e["t_ms"]), "chord": e["chord"], "page": e["nns"], "session": here})
        else:  # counted in another key: a key change, not a disagreement
            slot = other.setdefault(page_key, {"key": page_key, "chords": 0, "first_at": _clock(e["t_ms"]),
                                               "example": {"chord": e["chord"], "page": e["nns"], "session": here}})
            slot["chords"] += 1

    main = max(areas, key=lambda a: (a["end_ms"] - a["start_ms"], -a["start_ms"]))
    return {
        "key": main["key"],
        "areas": [{"at": _clock(a["start_ms"]), "start_s": _r(a["start_ms"] / 1000, 3), "end_s": _r(a["end_ms"] / 1000, 3),
                   "key": a["key"]} for a in areas],
        "minor_numbering": "tonic",
        "min_move_ms": MIN_MOVE_MS,
        "timeline": timeline,
        "top": top,
        "progressions": progressions,
        "loops": loops,
        "outside_key": {"seconds": _r(outside_ms / 1000, 3), "share_of_numbered_time": share(outside_ms),
                        "count": len(moments), "moments": moments[:OUTSIDE_LISTED], "by_number": by_outside},
        "page": {"key_source": source, "keys": page_keys, "changes": changes,
                 "numbers": {"chords": compared, "in_session_key": in_key, "agree": agree, "differ_count": len(differ),
                             "unread": unread, "differ": differ[:10],
                             "other_keys": sorted(other.values(), key=lambda o: -o["chords"])}},
    }


def summarize(events) -> dict:
    """Pure and deterministic: the same events give the same dict. The input is not modified."""
    evs = sorted(events, key=lambda e: e["t_ms"])  # stable: same-millisecond events keep their order
    duration_ms = max((e["t_ms"] for e in evs), default=0)
    minutes = duration_ms / 60000
    counts = {k: 0 for k in KINDS}

    sounding: Dict[int, dict] = {}   # note -> {"t0", "held"}
    pc_ms = [0] * 12
    pc_count = [0] * 12
    vels: List[int] = []
    onsets: List[int] = []
    lowest = highest = None
    pedal_down, pedal_since, pedal_spans = False, 0, []
    chord_events: List[dict] = []
    chord_sizes: List[int] = []
    spreads: List[int] = []
    endings = {by: 0 for by in SOUND_END_BY}
    spans: List[tuple] = []  # (start_ms, end_ms, pitch class) of every sound, for the key areas

    def end(note: int, t: int) -> None:
        start = sounding.pop(note)
        pc_ms[note % 12] += t - start["t0"]
        spans.append((start["t0"], t, note % 12))

    def ring_out(t: int) -> None:  # notes released under the pedal stop counting PEDAL_RING_MS after their release
        for note in sorted(n for n, s in sounding.items() if not s["held"] and s["released"] + PEDAL_RING_MS <= t):
            end(note, sounding[note]["released"] + PEDAL_RING_MS)

    for e in evs:
        t, kind = e["t_ms"], e["kind"]
        counts[kind] = counts.get(kind, 0) + 1
        if pedal_down:
            ring_out(t)
        if kind == "on":
            note = e["note"]
            if note in sounding:
                end(note, t)  # a repeat strike ends the previous sound
            sounding[note] = {"t0": t, "held": True}
            pc_count[note % 12] += 1
            vels.append(e["vel"])
            onsets.append(t)
            lowest = note if lowest is None else min(lowest, note)
            highest = note if highest is None else max(highest, note)
        elif kind == "off":
            note = e["note"]
            state = sounding.get(note)
            if state and state["held"]:
                state["held"], state["released"] = False, t
                if not pedal_down:
                    end(note, t)
        elif kind == "pedal":
            if e["down"] and not pedal_down:
                pedal_down, pedal_since = True, t
            elif not e["down"] and pedal_down:
                pedal_down = False
                pedal_spans.append(t - pedal_since)
                for note in sorted(n for n, s in sounding.items() if not s["held"]):
                    end(note, t)
        elif kind == "sound_end":
            endings[e["by"]] = endings.get(e["by"], 0) + 1  # the piano's own account; sounding time is inferred above
        elif kind == "chord":
            chord_events.append(e)
            if e.get("chord") is not None:
                names = e.get("notes") or []
                chord_sizes.append(len(names))
                parsed = [_parse_note(n) for n in names]
                midis = parsed if parsed and all(p is not None for p in parsed) else sorted(sounding)
                if midis:
                    spreads.append(max(midis) - min(midis))
    ring_out(duration_ms)
    for note in sorted(sounding):
        end(note, duration_ms)
    if pedal_down:
        pedal_spans.append(duration_ms - pedal_since)

    # ---- key and pitch
    total_pc_ms = sum(pc_ms)
    weights = pc_ms if total_pc_ms > 0 else pc_count
    key = estimate_key(weights)
    if key:
        key["weights"] = "sounding seconds per pitch class" if total_pc_ms > 0 else "note-ons per pitch class"
    nkey = numbering_key(weights, key, home_chords(chord_events, duration_ms))
    names = _pc_names(key)
    pitch_classes = [{"pc": pc, "name": names[pc], "count": pc_count[pc], "seconds": _r(pc_ms[pc] / 1000, 3),
                      "share": _r(pc_ms[pc] / total_pc_ms if total_pc_ms else 0.0)} for pc in range(12)]

    def note_name(m: int) -> str:
        return f"{names[m % 12]}{m // 12 - 1}"

    note_range = None
    if lowest is not None:
        note_range = {"lowest": {"midi": lowest, "name": note_name(lowest)},
                      "highest": {"midi": highest, "name": note_name(highest)},
                      "semitones": highest - lowest}

    # ---- numbers: the piano's own nns when it sent one, else read from the chord name in the event's key
    session_key = nkey["key"] if nkey else None
    reader, reader_error = _numbers_reader() if chord_events else (None, None)
    areas = key_areas(spans, chord_events, duration_ms, nkey, reader) if chord_events else \
        [{"start_ms": 0, "end_ms": duration_ms, "key": nkey}]
    area_starts = [a["start_ms"] for a in areas]
    number_of: List[Optional[dict]] = []
    area_numbers: List[Optional[dict]] = []  # each chord's number in its key area, as the Nashville section reads it
    from_piano = from_analyzer = 0
    for e in chord_events:
        chord, reading = e.get("chord"), None
        area_key = areas[max(0, bisect_right(area_starts, e["t_ms"]) - 1)]["key"]
        area_name = area_key["key"] if area_key else None
        in_area = chord_number(chord, area_name, e.get("notes"), reader, e.get("detect_kind")) \
            if chord is not None and area_name and reader else None
        area_numbers.append({"number": in_area["number"], "key": area_name} if in_area else None)
        event_key = e.get("nns_key") or e.get("key") or (area_key["key"] if area_key else session_key)
        computed = chord_number(chord, event_key, e.get("notes"), reader) if chord is not None and reader else None
        if chord is not None and e.get("nns") and event_key:
            reading = {"number": e["nns"], "key": event_key, "outside_key": bool(computed and computed["outside_key"])}
            from_piano += 1
        elif computed:
            reading = {"number": computed["number"], "key": event_key, "outside_key": computed["outside_key"]}
            from_analyzer += 1
        number_of.append(reading)

    # ---- chords: timeline, time by chord, moves
    chord_marks = [(e["t_ms"], e.get("chord"), dict(number_of[i] or {}, shape=_shape_kind(e, reader), area=area_numbers[i]))
                   for i, e in enumerate(chord_events)]
    segments = _segments(chord_marks, duration_ms)
    timeline = [{"chord": s["label"], "start_s": _r(s["start_ms"] / 1000, 3),
                 "seconds": _r((s["end_ms"] - s["start_ms"]) / 1000, 3)} for s in segments]
    by_chord = _time_by_label(segments)
    chord_ms = sum(v["ms"] for v in by_chord.values())
    top = sorted(by_chord.items(), key=lambda kv: (-kv[1]["ms"], kv[0]))[:TOP_N]
    top_chords = [{"chord": name, "seconds": _r(v["ms"] / 1000, 3), "segments": v["segments"],
                   "share_of_chord_time": _r(v["ms"] / chord_ms if chord_ms else 0.0),
                   "share_of_session": _r(v["ms"] / duration_ms if duration_ms else 0.0)} for name, v in top]
    # A move goes chord to chord: silence, a single note, an interval or a cluster between two chords does not break
    # it, just as a shape with no number does not break a move between numbers (so Chords and Nashville numbers count
    # the same moves: a cluster between Eb6 and F7 made them 2 times in one section and 3 in the other).
    runs, ordered_moves = _moves([s if s["first"].get("shape") == "chord" else dict(s, label=None) for s in segments])
    # A move's numbers are read in the key area it was played in, the keys the Nashville section numbers in. They used to
    # come from the key the page showed at the move's first occurrence, which lags a key change or is a passing key, so
    # the Chords section and question 2 taught numbers in a key the music had left (verifier, 2026-09-14).
    in_areas: Dict[tuple, Dict[str, tuple]] = {}
    for a, b in zip(runs, runs[1:]):
        na, nb = a["first"].get("area"), b["first"].get("area")
        if na and nb and na["key"] == nb["key"]:
            in_areas.setdefault((a["label"], b["label"]), {}).setdefault(na["key"], (na["number"], nb["number"]))
    progressions = []
    for (a, b), v in ordered_moves[:TOP_N]:
        row = {"from": a, "to": b, "count": v["count"], "seconds": _r(v["ms"] / 1000, 3),
               "share_of_session": _r(v["ms"] / duration_ms if duration_ms else 0.0)}
        numbers_text = _move_numbers(in_areas.get((a, b), {}))
        if numbers_text:
            row["numbers"] = numbers_text
        progressions.append(row)

    # ---- numbers: time by number within its key, number moves inside one key, time outside the key
    number_marks = [(e["t_ms"], (number_of[i]["key"], number_of[i]["number"]) if number_of[i] else None,
                     dict(number_of[i] or {}, chord=e.get("chord"))) for i, e in enumerate(chord_events)]
    number_segments = _segments(number_marks, duration_ms)
    by_number = _time_by_label(number_segments)
    numbered_ms = sum(v["ms"] for v in by_number.values())
    keys_ms: Dict[str, int] = {}
    outside_ms, outside_by_chord = 0, {}
    for s in number_segments:
        if s["label"] is None:
            continue
        ms = s["end_ms"] - s["start_ms"]
        keys_ms[s["label"][0]] = keys_ms.get(s["label"][0], 0) + ms
        if s["first"]["outside_key"]:
            outside_ms += ms
            slot = outside_by_chord.setdefault((s["first"]["chord"], s["label"][1], s["label"][0]), {"ms": 0})
            slot["ms"] += ms
    share = (lambda ms: _r(ms / numbered_ms)) if numbered_ms else (lambda ms: 0.0)
    number_moves = [((a, b), v) for (a, b), v in _moves(number_segments)[1] if a[0] == b[0]][:TOP_N]
    numbers = {
        "source": {"piano": from_piano, "analyzer": from_analyzer,
                   "reader": NUMBERS_READER if not reader_error else f"unavailable ({reader_error})"},
        "keys": [{"key": k, "seconds": _r(ms / 1000, 3), "share_of_numbered_time": share(ms)}
                 for k, ms in sorted(keys_ms.items(), key=lambda kv: (-kv[1], kv[0]))],
        "top": [{"key": k, "number": n, "seconds": _r(v["ms"] / 1000, 3), "segments": v["segments"],
                 "share_of_numbered_time": share(v["ms"]), "outside_key": bool(v["first"]["outside_key"])}
                for (k, n), v in sorted(by_number.items(), key=lambda kv: (-kv[1]["ms"], kv[0]))[:TOP_N]],
        "progressions": [{"key": a[0], "from": a[1], "to": b[1], "count": v["count"], "seconds": _r(v["ms"] / 1000, 3),
                          "share_of_session": _r(v["ms"] / duration_ms if duration_ms else 0.0)}
                         for (a, b), v in number_moves],
        "outside_key": {"seconds": _r(outside_ms / 1000, 3), "share_of_numbered_time": share(outside_ms),
                        "chords": [{"chord": c, "number": n, "key": k, "seconds": _r(v["ms"] / 1000, 3)}
                                   for (c, n, k), v in sorted(outside_by_chord.items(),
                                                              key=lambda kv: (-kv[1]["ms"], kv[0]))[:5]]},
    }

    # ---- dynamics
    dynamics = None
    if vels:
        ordered = sorted(vels)
        dynamics = {"notes": len(vels), "mean_velocity": _r(sum(vels) / len(vels)),
                    "p10": _r(_percentile(ordered, 10)), "p90": _r(_percentile(ordered, 90)),
                    "min": ordered[0], "max": ordered[-1]}

    # ---- pedal
    down_ms = sum(pedal_spans)
    pedal = {"percent_down": _r(100 * down_ms / duration_ms) if duration_ms else None,
             "presses": len(pedal_spans),
             "presses_per_minute": _r(len(pedal_spans) / minutes) if minutes else None,
             "mean_down_s": _r(down_ms / len(pedal_spans) / 1000) if pedal_spans else None}
    ended = sum(endings.values())
    sound_ends = {"events": ended, "by": endings,
                  "share": {by: _r(n / ended) for by, n in endings.items()} if ended else None}

    # ---- timing
    groups: List[int] = []
    for t in onsets:  # onsets are already in time order
        if not groups or t - groups[-1] > ONSET_MERGE_MS:
            groups.append(t)
    iois = [b - a for a, b in zip(groups, groups[1:])]
    bins: Dict[int, int] = {}
    for gap in iois:
        if gap < IOI_MAX_MS:
            lo = gap // IOI_BIN_MS * IOI_BIN_MS
            bins[lo] = bins.get(lo, 0) + 1
    histogram = {"bin_ms": IOI_BIN_MS, "max_ms": IOI_MAX_MS,
                 "bins": [{"lo_ms": lo, "hi_ms": lo + IOI_BIN_MS, "count": bins[lo]} for lo in sorted(bins)],
                 "at_or_over_max": sum(1 for gap in iois if gap >= IOI_MAX_MS)}
    fastest_ms, slowest_ms = 60000 / TEMPO_BPM[1], 60000 / TEMPO_BPM[0]
    in_range = sorted(g for g in iois if fastest_ms <= g <= slowest_ms)
    tempo = None
    if in_range:
        best_gap, best_support = None, -1
        for gap in in_range:  # sorted, so each cluster is a bisect away: an hour of playing stays fast
            support = bisect_right(in_range, gap + TEMPO_WINDOW_MS) - bisect_left(in_range, gap - TEMPO_WINDOW_MS)
            if support > best_support:
                best_gap, best_support = gap, support
        cluster = in_range[bisect_left(in_range, best_gap - TEMPO_WINDOW_MS):
                           bisect_right(in_range, best_gap + TEMPO_WINDOW_MS)]
        ioi_ms = sum(cluster) / len(cluster)
        tempo = {"label": "rough", "bpm": _r(60000 / ioi_ms, 1), "ioi_ms": _r(ioi_ms, 1),
                 "support": len(cluster), "gaps_in_range": len(in_range), "gaps": len(iois),
                 "bpm_range": list(TEMPO_BPM), "window_ms": TEMPO_WINDOW_MS}
    timing = {"onset_merge_ms": ONSET_MERGE_MS, "onsets": len(groups), "ioi_histogram": histogram,
              "rough_tempo": tempo}

    voicing = {"chord_events": len(chord_sizes), "mean_notes_per_chord": _r(_mean(chord_sizes)),
               "mean_spread_semitones": _r(_mean(spreads))}

    summary = {
        "api": SUMMARY_API,
        "duration_s": _r(duration_ms / 1000, 3),
        "note_count": len(vels),
        "notes_per_minute": _r(len(vels) / minutes, 2) if minutes else None,
        "event_counts": counts,
        "range": note_range,
        "pitch_classes": pitch_classes,
        "key": key,
        "chords": {"timeline": timeline, "top": top_chords, "progressions": progressions,
                   "changes": max(0, len(runs) - 1), "min_move_ms": MIN_MOVE_MS},
        "numbers": numbers,
        "nashville": _nashville(chord_events, areas, reader, duration_ms),
        "dynamics": dynamics,
        "pedal": pedal,
        "sound_ends": sound_ends,
        "timing": timing,
        "voicing": voicing,
    }
    summary["questions"] = questions(summary)
    return summary


# ============================================================================================ narrative
def _pct(share) -> str:
    return f"{round(100 * share)}%"


def _secs(seconds: float) -> str:
    seconds = float(seconds or 0)
    if seconds < 60:
        return f"{seconds:.1f} s"
    return f"{int(seconds // 60)} min {int(round(seconds % 60))} s"


def questions(s: dict) -> List[str]:
    """Three to five questions for Daniel, each built from one number in the summary (none for a silent session)."""
    if not s.get("note_count"):
        return []
    out: List[str] = []
    anchored = _nashville_question(s)
    if anchored:
        out.append(anchored[1])  # one question per session anchored to a time he can replay (spec 6.5)
    progressions = s["chords"]["progressions"]
    if progressions and progressions[0]["count"] >= 2 and not (anchored and anchored[0] in ("loop", "move")):
        p = progressions[0]
        numbers = f", {p['numbers']}" if p.get("numbers") else ""
        out.append(f"You spent {_pct(p['share_of_session'])} of the session moving {p['from']} → {p['to']} "
                   f"({_count(p['count'])}{numbers}). What pulls you to that move?")
    key = s.get("key")
    if key:
        best, runner = key["best"], key["runner_up"]
        nv = s.get("nashville") or {}
        nkey = nv.get("key") or {}
        rule = nkey.get("rule")
        areas = [a for a in (nv.get("areas") or []) if a.get("key")]
        main = max(areas, key=lambda a: (a["end_s"] - a["start_s"], -a["start_s"])) if len(areas) > 1 else None
        your = f"From {main['at']}, your" if main else "Your"  # the rule belongs to the longest key area
        heard = None
        if rule and "leading_tone_share" in rule:
            heard = "never sounded" if not rule["leading_tone_share"] else "barely sounded"
        if rule and rule["name"] == "home chord":
            out.append(f"{your} notes weigh most like {rule['demoted']} (r {rule['r']:.2f}), but {rule['home_chord']} sounded "
                       f"for {_pct(rule['home_share'])} of the chord time, nearly every note is on {rule['minor_key']}'s scale, "
                       f"and {rule['demoted']} leaves out {rule['left_out']}, so the numbers read {nkey['key']}. "
                       f"Did {rule['home_chord']} feel like home ({rule['minor_key']}), or were you thinking in {nkey['key']}?")
        elif rule and rule["name"] == "leading tone":
            fit = "" if main else f" (r {best['r']:.2f})"
            out.append(f"{your} notes weigh most like {rule['demoted']}{fit}, but its raised 7th, "
                       f"{rule['leading_tone']}, {heard}, so the numbers read {nkey['key']}. "
                       f"Were you thinking in {nkey['key']} or in {rule['demoted']}?")
        elif rule:  # next best: the rule counted the estimate lower, and another key than the one it points to won
            reason = f"its raised 7th, {rule['leading_tone']}, {heard}" if heard else \
                f"{rule['home_chord']} kept sounding and {rule['demoted']} leaves out {rule['left_out']}"
            out.append(f"{your} notes weigh most like {rule['demoted']}, but {reason}, so the piano's key tracker counts it "
                       f"lower, and then {nkey['key']} fits best. Were you thinking in {nkey['key']} or in {rule['demoted']}?")
        elif main and main["key"].get("runner_up"):
            # A session in several keys: the whole-session estimate blends its parts (F major then D major fit D minor
            # best, a key neither part is in), so the question asks about the longest part, in its own estimate.
            mk = main["key"]
            where = f"From {main['at']} to {_clock(main['end_s'] * 1000)}"
            if mk["r"] - mk["runner_up_r"] < 0.05:
                out.append(f"{where} your notes fit {mk['key']} (r {mk['r']:.2f}) and {mk['runner_up']} "
                           f"(r {mk['runner_up_r']:.2f}) almost equally. Which one felt like home there?")
            else:
                out.append(f"{where} your notes fit {mk['key']} best (r {mk['r']:.2f}), ahead of {mk['runner_up']} "
                           f"(r {mk['runner_up_r']:.2f}). Were you thinking in {mk['key']} there, or did your hands find it?")
        elif main:
            pass  # an area key without its estimate's runner-up (an older summary): no key question rather than a blend
        elif key["margin"] < 0.05:
            out.append(f"Your notes fit {best['key']} (r {best['r']:.2f}) and {runner['key']} (r {runner['r']:.2f}) "
                       f"almost equally. Which one felt like home?")
        else:
            out.append(f"Your notes fit {best['key']} best (r {best['r']:.2f}), ahead of {runner['key']} "
                       f"(r {runner['r']:.2f}). Were you thinking in {best['key']}, or did your hands find it?")
    pedal = s["pedal"]
    if pedal["presses"] and pedal["percent_down"] is not None:
        if pedal["percent_down"] >= 70:
            out.append(f"The pedal was down {round(pedal['percent_down'])}% of the session, "
                       f"{pedal['mean_down_s']:.1f} s per press on average. Is that blend the sound you're after?")
        else:
            each = " each time" if pedal["presses"] > 1 else ""
            out.append(f"You pressed the pedal {_count(pedal['presses'])} against {_n(s['chords']['changes'], 'chord change')}, "
                       f"holding it {pedal['mean_down_s']:.1f} s{each}. How do you decide when to change it?")
    top = s["chords"]["top"]
    if top and top[0]["seconds"]:
        c = top[0]
        out.append(f"{c['chord']} took the most chord time, {_pct(c['share_of_chord_time'])} of it. "
                   f"What makes it your home base?")
    d = s.get("dynamics")
    if d:
        spread = d["p90"] - d["p10"]
        tail = "Is that narrow band on purpose?" if spread < 25 else "Where did the loudest moments come from?"
        out.append(f"Most of your notes landed between velocity {d['p10']:.0f} and {d['p90']:.0f} "
                   f"(mean {d['mean_velocity']:.0f}). {tail}")
    tempo = s["timing"]["rough_tempo"]
    if tempo:
        out.append(f"The most common gap between onsets works out to a rough {tempo['bpm']:.0f} BPM. "
                   f"Were you feeling a pulse there, or playing freely?")
    v = s["voicing"]
    if v["mean_spread_semitones"] is not None:
        out.append(f"Your chords averaged {v['mean_notes_per_chord']:.1f} notes spread over "
                   f"{_n(round(v['mean_spread_semitones']), 'semitone')}. What decides how wide you voice them?")
    rng = s.get("range")
    if rng:
        out.append(f"You played from {rng['lowest']['name']} to {rng['highest']['name']}, {_n(rng['semitones'], 'semitone')} "
                   f"across {_n(s['note_count'], 'note')}. Which register do you reach for first?")
    # Fallbacks, used only when the questions above come to fewer than five. Dynamics and range always exist
    # once a note was played, and so does the pitch-class question, so a session with notes gets at least three.
    out.append(_pitch_class_question(s))
    if s.get("notes_per_minute") is not None:
        out.append(f"You played {_n(s['note_count'], 'note')} in {_secs(s['duration_s'])}, about {s['notes_per_minute']:.0f} "
                   f"a minute. Does that pace feel like where your playing is right now?")
    return out[:5]


def _nashville_question(s: dict) -> Optional[tuple]:
    """(kind, question) anchored to a time: a chord outside its key first, then a change of key (between this summary's
    key areas, else on the piano page), then the main loop, move or number. None when nothing with any length was
    numbered."""
    nv = s.get("nashville") or {}
    nkey = nv.get("key")
    if not nkey or not nv.get("top"):
        return None
    k = nkey["key"]
    colour = [o for o in nv["outside_key"]["by_number"] if not o.get("in_page_key") and not o.get("edge_key")]  # not a key change
    if colour:
        o = colour[0]
        ok = o.get("key") or k
        what = f"a borrowed chord (it belongs to {o['borrowed_from']})" if o["kind"] == "borrowed" else \
            f"a chromatic chord (it belongs to neither {ok} nor {_parallel_key(ok)})"
        return "outside", (f"At {o['first_at']} you played a {o['number']} ({o['chord']}) in {ok}, {what}. "
                           f"What were you reaching for there?")
    areas = [a for a in (nv.get("areas") or []) if a.get("key")]
    if len(areas) > 1:
        a, b = areas[0], areas[1]
        return "key change", (f"At {b['at']} the music moved from {a['key']['key']} to {b['key']['key']}. "
                              f"Did you mean to change key there, or did a chord pull it?")
    changes = nv["page"]["changes"]
    if changes:
        c = changes[0]
        return "key change", (f"At {c['at']} the piano page's key moved from {c['from']} to {c['to']}. "
                              f"Did you mean to change key there, or did a chord pull it?")
    if nv["loops"]:
        loop = nv["loops"][0]
        return "loop", (f"At {loop['first_at']} you started looping {' → '.join(loop['numbers'])} in "
                        f"{loop.get('key') or k} ({' '.join(loop['chords'])}), {_count(loop['count'])} back to back. "
                        f"What draws you to that cycle?")
    if nv["progressions"] and nv["progressions"][0]["count"] >= 2:
        p = nv["progressions"][0]
        return "move", (f"At {p['first_at']} you first moved {p['from']} → {p['to']} in {p.get('key') or k} "
                        f"({p['chords'][0]} → {p['chords'][1]}), and did it {_count(p['count'])} in all. "
                        f"What do you hear in that move?")
    t = nv["top"][0]
    if not t["seconds"]:
        return None
    return "number", f"At {t['first_at']} you settled on {t['number']} ({t['chord']}) in {t.get('key') or k}. What makes it home?"


def _pitch_class_question(s: dict) -> str:
    """Built from the pitch-class table: sounding seconds when any note had length, note-ons otherwise."""
    used = [p for p in s["pitch_classes"] if p["count"]]
    by_time = any(p["seconds"] for p in used)
    weight = (lambda p: p["seconds"]) if by_time else (lambda p: p["count"])
    measure = "time sounding" if by_time else "note-ons"
    if len({weight(p) for p in used}) == 1:
        if len(used) == 1:
            return (f"Everything you played was the pitch class {used[0]['name']}. "
                    f"What were you listening for in that one note?")
        tail = "Were you after that evenness, or exploring every note in the octave?" if len(used) == 12 else \
            "Was that balance on purpose?"
        return f"You used {len(used)} of the 12 pitch classes, each with the same share of {measure}. {tail}"
    total = sum(weight(p) for p in used)
    lead = sorted(used, key=lambda p: (-weight(p), p["pc"]))[0]
    return (f"{lead['name']} had the largest share of {measure}, {_pct(weight(lead) / total)}, across {len(used)} "
            f"of the 12 pitch classes. Is {lead['name']} a note you lean on?")


def render_markdown(doc: dict) -> str:
    """summary.md: a readable account built only from the summary's numbers."""
    lines: List[str] = []
    add = lines.append
    session = doc.get("session") or "(unsaved)"
    add(f"# Practice session {session}")
    add("")
    opened = (doc.get("opened_at") or "?")[:19].replace("T", " ")
    status = f"closed {doc['closed_at'][:19].replace('T', ' ')} UTC" if doc.get("closed_at") else \
        "still open, so this summary is provisional"
    npm = f" ({doc['notes_per_minute']:.1f} per minute)" if doc.get("notes_per_minute") is not None else ""
    add(f"Opened {opened} UTC, {status}. {_secs(doc['duration_s'])} long, {_n(doc['note_count'], 'note')}{npm}.")
    meta = doc.get("meta") or {}
    if meta.get("buffered") and isinstance(meta.get("opened_at_client"), str):
        add(f"Played from {meta['opened_at_client'][:19].replace('T', ' ')} UTC by the browser's clock; the browser "
            f"kept it while the server could not take it and uploaded it later.")
    add("")
    if not doc["note_count"]:
        add("No notes were logged in this session, so there is nothing to analyse.")
        return "\n".join(lines) + "\n"

    add("## Range and pitch")
    rng = doc["range"]
    add(f"Lowest {rng['lowest']['name']} (MIDI {rng['lowest']['midi']}), highest {rng['highest']['name']} "
        f"(MIDI {rng['highest']['midi']}): {_n(rng['semitones'], 'semitone')}.")
    ranked = sorted((p for p in doc["pitch_classes"] if p["seconds"]), key=lambda p: (-p["seconds"], p["pc"]))
    if ranked:
        add("Pitch classes by time sounding (pedal included): "
            + ", ".join(f"{p['name']} {_pct(p['share'])}" for p in ranked[:7]) + ".")
    add("")

    add("## Key")
    key = doc.get("key")
    parts = [a for a in ((doc.get("nashville") or {}).get("areas") or []) if a.get("key")]
    if key:
        whole = " for the whole session" if len(parts) > 1 else ""
        add(f"Krumhansl-Kessler estimate over {key['weights']}{whole}: {key['best']['key']} (r {key['best']['r']:.2f}), "
            f"runner-up {key['runner_up']['key']} (r {key['runner_up']['r']:.2f}), margin {key['margin']:.2f}.")
        if len(parts) > 1:
            listed = ", ".join(f"{a['key']['key']} from {a['at']}" for a in parts)
            add(f"The session changes key ({listed}), so this estimate is a blend of its parts, not a key it stayed in; "
                f"each part is numbered in its own key under Nashville numbers.")
    else:
        add("Not enough pitch variety to estimate a key.")
    add("")

    chords = doc["chords"]
    add("## Chords")
    if chords["top"]:
        add("Time by chord: " + ", ".join(f"{c['chord']} {_pct(c['share_of_chord_time'])} ({c['seconds']:.1f} s)"
                                          for c in chords["top"]) + ".")
    else:
        add("No chord names were logged.")
    if chords["progressions"]:
        add("")
        add(f"Most common moves ({_n(chords['changes'], 'chord change')}; shapes under {chords['min_move_ms']} ms are skipped):")
        for p in chords["progressions"][:5]:
            numbers = f" ({p['numbers']})" if p.get("numbers") else ""
            add(f"- {p['from']} → {p['to']}{numbers}: {_count(p['count'])}, {_pct(p['share_of_session'])} of the session")
    add("")
    if chords["timeline"]:
        segments = chords["timeline"]
        kept = [seg for seg in segments if seg["seconds"] >= MD_MIN_ROW_S]
        shown = kept[:MD_TIMELINE_ROWS]
        if shown:
            add(f"Timeline ({_listed(len(shown), len(segments), 'segment')}{_short_rows(len(segments) - len(kept))}):")
            add("")
            add("| start | chord | seconds |")
            add("| ---: | :--- | ---: |")
            for seg in shown:
                add(f"| {seg['start_s']:.2f} | {seg['chord'] if seg['chord'] is not None else '(none)'} | {seg['seconds']:.2f} |")
        else:
            add(f"Timeline: {_none_listed(len(segments), 'segment')}")
        add("")

    glossary = _nashville_markdown(doc, add)

    d = doc["dynamics"]
    add("## Dynamics")
    add(f"Mean velocity {d['mean_velocity']:.1f}, p10 {d['p10']:.1f}, p90 {d['p90']:.1f} "
        f"(min {d['min']}, max {d['max']}, over {_n(d['notes'], 'note')}).")
    add("")

    pedal = doc["pedal"]
    add("## Pedal")
    if pedal["presses"] and pedal["percent_down"] is not None and pedal["presses_per_minute"] is not None:
        add(f"Down {pedal['percent_down']:.1f}% of the session: {_n(pedal['presses'], 'press', 'presses')} "
            f"({pedal['presses_per_minute']:.1f} per minute), {pedal['mean_down_s']:.2f} s down per press on average.")
    elif pedal["presses"]:
        # every event shares one millisecond: there is no session length to take a share or a rate of
        add(f"{_n(pedal['presses'], 'press', 'presses')}, {pedal['mean_down_s'] or 0:.2f} s down per press on average. "
            f"The session has no measurable length, so there is no percent down or presses per minute.")
    else:
        add("The sustain pedal was not pressed.")
    ends = doc.get("sound_ends") or {}
    if ends.get("events"):
        share = ends["share"]
        add(f"The piano recorded how {_n(ends['events'], 'sound')} ended: {_pct(share['release'])} at the key release, "
            f"{_pct(share['pedal'])} at a pedal lift, {_pct(share['repeat'])} re-struck, "
            f"{_pct(share['all-off'])} by an all-notes-off.")
    add("")

    timing = doc["timing"]
    add("## Timing")
    hist = timing["ioi_histogram"]
    common = sorted(hist["bins"], key=lambda b: (-b["count"], b["lo_ms"]))[:3]
    add(f"{_n(timing['onsets'], 'onset')} (notes within {timing['onset_merge_ms']} ms count as one).")
    if common:
        add("Most common gaps between onsets: " + ", ".join(f"{b['lo_ms']}-{b['hi_ms']} ms ({b['count']})" for b in common)
            + f"; {_n(hist['at_or_over_max'], 'gap')} of {hist['max_ms']} ms or more.")
    tempo = timing["rough_tempo"]
    if tempo:
        add(f"Rough tempo: about {tempo['bpm']:.0f} BPM (rough: the most common gap between {tempo['bpm_range'][0]} "
            f"and {tempo['bpm_range'][1]} BPM, {tempo['support']} of {_n(tempo['gaps_in_range'], 'gap')} in that range).")
    else:
        add("Rough tempo: none (no gaps between 60 and 200 BPM).")
    add("")

    v = doc["voicing"]
    add("## Voicing")
    if v["chord_events"] and v["mean_spread_semitones"] is not None:
        add(f"{_n(v['chord_events'], 'chord event')} averaged {v['mean_notes_per_chord']:.1f} notes, spread "
            f"{v['mean_spread_semitones']:.1f} semitones from lowest to highest sounding note.")
    else:
        add("No chord events to measure.")
    add("")

    add("## Questions for Daniel")
    for i, q in enumerate(doc.get("questions") or [], 1):
        add(f"{i}. {q}")
    if glossary:
        add("")
        add("## Glossary")
        for term, text in glossary:
            add(f"- {term}: {text}")
    return "\n".join(lines) + "\n"


def _count(n: int) -> str:
    """'once', '2 times'."""
    return "once" if n == 1 else f"{n} times"


def _n(n: int, word: str, plural: Optional[str] = None) -> str:
    """'1 note', '2 notes': a count with its noun (plural: when it is not the noun plus s)."""
    return f"{n} {word if n == 1 else plural or word + 's'}"


def _listed(shown: int, total: int, word: str, plural: Optional[str] = None) -> str:
    """A table heading's count: 'first 24 of 581 segments', 'all 5 segments', 'the one segment'."""
    if total == 1:
        return f"the one {word}"
    return f"first {shown} of {_n(total, word, plural)}" if shown < total else f"all {_n(total, word, plural)}"


def _none_listed(total: int, word: str, plural: Optional[str] = None) -> str:
    """The line that replaces a table whose every row is a passing shape."""
    if total == 1:
        return f"the one {word} lasted under {MD_MIN_ROW_S:g} s, so it is not listed."
    return f"all {_n(total, word, plural)} lasted under {MD_MIN_ROW_S:g} s, so none are listed."


def _short_rows(n: int) -> str:
    """The note a table heading carries about the passing shapes it leaves out (their count stays in the heading)."""
    if not n:
        return ""
    return f"; {'the one' if n == 1 else f'the {n}'} under {MD_MIN_ROW_S:g} s {'is' if n == 1 else 'are'} not listed"


def _times(times: List[str], count: int) -> str:
    """'0:48', '0:48 and 0:52', '0:48, 0:52 and 1:10', with 'and N more' past the listed ones."""
    if count > len(times):
        return ", ".join(times) + f" and {count - len(times)} more"
    return times[0] if len(times) == 1 else ", ".join(times[:-1]) + " and " + times[-1]


def _nashville_markdown(doc: dict, add) -> List[tuple]:
    """The Nashville numbers section, one line per fact with the time to replay it. Returns the glossary entries
    for the terms the section used (none when there was nothing to number)."""
    nv = doc.get("nashville") or {}
    nkey = nv.get("key")
    if not nkey or not nv.get("top"):
        return []
    k = nkey["key"]
    areas = [a for a in (nv.get("areas") or []) if a.get("key")] or [{"at": "0:00", "key": nkey}]
    several = len(areas) > 1
    keys_here = {a["key"]["key"] for a in areas}

    def where(row: dict) -> str:  # the key a line is counted in, when the session has more than one
        return f" in {row['key']}" if several and row.get("key") else ""

    shown: List[tuple] = []  # (number, chord, key) the section wrote, for the glossary
    used = set()
    examples: Dict[str, str] = {}  # "borrowed" / "chromatic" -> the key of the first such line, for the glossary
    add("## Nashville numbers")
    if several:
        add("The session changes key, so each part is numbered in the key that fits it: "
            + ", ".join(f"{a['key']['key']} from {a['at']}" for a in areas)
            + ". Times are minutes:seconds from your first note.")
    else:
        add(f"Every chord here is numbered in {k}, the key that fits the whole session. "
            f"Times are minutes:seconds from your first note.")
    for area in areas:
        rule, ak = area["key"].get("rule"), area["key"]["key"]
        if not rule:
            continue
        your = f"From {area['at']}, your" if several else "Your"
        if rule.get("because", rule["name"]) == "home chord":
            used.add("home chord")
            why = (f"{your} notes weigh most like {rule['demoted']} (r {rule['r']:.2f}), but {rule['home_chord']} sounded for "
                   f"{_pct(rule['home_share'])} of the chord time and nearly every note is on {rule['minor_key']}'s scale, while "
                   f"{rule['demoted']} leaves out {rule['left_out']} ({_pct(rule['left_out_share'])} of the sounding time is "
                   f"outside it)")
        else:
            used.add("raised 7th")
            tonic = rule["demoted"].split(" ")[0]
            heard = "never sounded" if not rule["leading_tone_share"] else \
                f"sounded for only {_pct(rule['leading_tone_share'])} as long as {tonic}"
            best_r = ((doc.get("key") or {}).get("best") or {}).get("r")
            fit = f" (r {best_r:.2f})" if best_r is not None and not several else ""
            why = f"{your} notes weigh most like {rule['demoted']}{fit}, but its raised 7th, {rule['leading_tone']}, {heard}"
        if rule["name"] == "next best":  # the rule's own key did not win: never name it as the cause of the one that did
            add(f"{why}, so the piano's key tracker counts {rule['demoted']} lower; after that {ak} fits best "
                f"(r {area['key']['r']:.2f}), so the numbers count from {ak}.")
        else:
            add(f"{why}, so the numbers count from {ak} instead, the way the piano's key tracker decides.")
    add("")

    for loop in nv["loops"][:3]:
        used.add("loop")
        shown += [(n, c, loop.get("key") or k) for n, c in zip(loop["numbers"], loop["chords"])]
        add(f"- Loop from {loop['first_at']}{where(loop)}: {' → '.join(loop['numbers'])} ({', '.join(loop['chords'])}), "
            f"{_count(loop['count'])} back to back.")
    for t in nv["top"][:5]:
        shown.append((t["number"], t["chord"], t.get("key") or k))
        flag = ", outside the key" if t["outside_key"] else ""
        add(f"- {t['number']} ({t['chord']}{flag}){where(t)}: {_pct(t['share_of_numbered_time'])} of the numbered time, "
            f"{t['seconds']:.1f} s, first at {t['first_at']}.")
    for p in nv["progressions"][:3]:
        add(f"- Move {p['from']} → {p['to']}{where(p)} ({p['chords'][0]} → {p['chords'][1]}): {_count(p['count'])}, "
            f"first at {p['first_at']}.")
    outside = nv["outside_key"]
    for o in outside["by_number"][:5]:
        used.add(o["kind"])
        ok = o.get("key") or k
        examples.setdefault(o["kind"], ok)
        shown.append((o["number"], o["chord"], ok))
        what = f"borrowed from {o['borrowed_from']}" if o["kind"] == "borrowed" else \
            f"chromatic (in neither {ok} nor {_parallel_key(ok)})"
        page_note = f"; the piano page showed {o['page_key']}, where it belongs" if o.get("in_page_key") else \
            f"; it belongs to {o['edge_key']}, the key of the part next to it" if o.get("edge_key") else ""
        add(f"- At {_times(o['times'], o['count'])}: {o['number']} ({o['chord']}){where(o)}, {what}, "
            f"{o['seconds']:.1f} s in all{page_note}.")
    if not outside["by_number"]:
        add(f"- Every chord that lasted {nv['min_move_ms']} ms or more belongs to "
            f"{'the key of its part' if several else k}.")

    page = nv.get("page") or {}
    shows = "key guess" if page.get("key_source") == "key" else "key"
    for pk in page.get("keys", [])[:4]:
        add(f"- The piano page's {shows} read {pk['key']} for {_secs(pk['seconds'])} "
            f"({_pct(pk['share_of_session'])} of the session), first at {pk['first_at']}.")
    changes = page.get("changes", [])
    for c in changes[:6]:
        add(f"- At {c['at']} the piano page's {shows} changed from {c['from']} to {c['to']}.")
    if len(changes) > 6:
        add(f"- {_n(len(changes) - 6, 'more key change')} after that.")
    first_shown = {pk["key"]: pk["first_at"] for pk in page.get("keys", [])}
    elsewhere: Dict[str, List[dict]] = {}
    for n in (doc.get("numbers") or {}).get("top", []):
        if n["key"] not in keys_here:
            elsewhere.setdefault(n["key"], []).append(n)
    for other_key, rows in list(elsewhere.items())[:3]:
        since = f", the page's key from {first_shown[other_key]}" if other_key in first_shown else ""
        add(f"- Counted in {other_key} instead{since}: " + ", ".join(f"{n['number']} for {n['seconds']:.1f} s"
                                                                     for n in rows[:5]) + ".")
    pn = page.get("numbers") or {}
    if pn.get("chords"):
        counted = "the same key as here" if several else k
        read = pn["in_session_key"] - pn.get("unread", 0)
        if read:
            add(f"- The piano page wrote its own number on {_n(pn['chords'], 'chord')}; {pn['agree']} of the "
                f"{read} it counted in {counted} match these."
                + (f" {pn['unread']} more {'is a name' if pn['unread'] == 1 else 'are names'} this summary cannot read."
                   if pn.get("unread") else ""))
        elif pn["in_session_key"]:
            add(f"- The piano page wrote its own number on {_n(pn['chords'], 'chord')}; this summary cannot read the "
                f"{pn['in_session_key']} it counted in {counted}.")
        else:
            add(f"- The piano page wrote its own number on {_n(pn['chords'], 'chord')}, none of them counted in "
                f"{counted}.")
        for d in pn["differ"][:3]:
            add(f"- At {d['at']} the piano page wrote {d['chord']} as {d['page']}; here it is "
                f"{d['session'] or 'not numbered'}.")
        for o in pn["other_keys"][:3]:
            ex = o["example"]
            add(f"- From {o['first_at']} the piano page numbered {_n(o['chords'], 'chord')} in {o['key'] or 'no key'} "
                f"(first {ex['chord']}: {ex['page']} there, {ex['session'] or 'not numbered'} here).")

    rows = [s for s in nv["timeline"] if s["number"] is not None]
    kept = [s for s in rows if s["seconds"] >= MD_MIN_ROW_S]
    if kept:
        listed = kept[:MD_TIMELINE_ROWS]
        legend = "; * outside the key" if any(s["outside_key"] for s in listed) else ""
        add("")
        add(f"Numbers over time ({_listed(len(listed), len(rows), 'numbered stretch', 'numbered stretches')}"
            f"{_short_rows(len(rows) - len(kept))}{legend}):")
        add("")
        add("| at | key | number | chord | seconds |" if several else "| at | number | chord | seconds |")
        add("| ---: | :--- | :--- | :--- | ---: |" if several else "| ---: | :--- | :--- | ---: |")
        for s in listed:
            shown.append((s["number"], s["chord"], s.get("key") or k))
            cells = [s["at"]] + ([s.get("key") or ""] if several else []) + \
                [f"{s['number']}{' *' if s['outside_key'] else ''}", s["chord"], f"{s['seconds']:.1f}"]
            add("| " + " | ".join(cells) + " |")
    elif rows:
        add("")
        add(f"Numbers over time: {_none_listed(len(rows), 'numbered stretch', 'numbered stretches')}")
    add("")
    return _glossary(nkey, shown, used, examples, {a["key"]["mode"] for a in areas}, several)


_NUMBER_PARTS_RE = re.compile(r"^([b#]*)\d(.*?)(?:(/)([b#]*)\d)?$")
_CHORD_ROOT_RE = re.compile(r"^[A-G](#{1,2}|b{1,2})?")
_EXTENSIONS = {  # the chord-shape marks after a number, in plain words with a C chord as the example
    "7": "adds the note a whole step below the octave (C7 adds Bb): the bluesy, wants-to-move sound.",
    "maj7": "adds the note a half step below the octave (Cmaj7 adds B): softer and dreamier than 7.",
    "6": "adds the 6th above the root (C6 adds A).",
    "9": "a 7 chord with the 9th on top (the 2nd, an octave up).",
    "maj9": "a maj7 chord with the 9th on top.",
    "add9": "adds the 9th (the 2nd, an octave up) without a 7th.",
    "sus4": "the 3rd is swapped for the 4th, so the chord is neither major nor minor and wants to resolve.",
    "sus2": "the 3rd is swapped for the 2nd: open, neither major nor minor.",
    "5": "a power chord, only the root and the 5th.",
    "7sus4": "a sus4 chord with a 7 added.",
    "11": "a 9 chord with the 11th (the 4th, an octave up) on top as well (C11 adds Bb, D and F).",
    "m11": "a minor chord with the 7, 9 and 11 stacked on it (Cm11 adds Bb, D and F): soft, open and still minor.",
    "add11": "adds the 11th (the 4th, an octave up) without a 7th or 9th (Cadd11 adds F).",
    "9sus4": "a 9 chord with its 3rd swapped for the 4th (C9sus4 is C F G Bb D): open, a gentle pull toward home.",
    "maj13": "a maj7 chord with the 9th and the 13th (the 6th, an octave up) on top (Cmaj13 adds B, D and A): lush.",
    "6/9": "adds both the 6th and the 9th and no 7th (C6/9 adds A and D): warm and settled, a favourite last chord.",
    "7#5": "a 7 chord with its 5th raised a half step (C7#5 is C E G# Bb): tense, leaning hard into the next chord.",
    "maj7#5": "a maj7 chord with its 5th raised a half step (Cmaj7#5 is C E G# B): dreamy but unsettled.",
    "7b5": "a 7 chord with its 5th lowered a half step (C7b5 is C E Gb Bb): tense, with two tritones in it.",
    "7b9": "a 7 chord with a 9th a half step lower on top (C7b9 adds Bb and Db): dark, with a strong pull to resolve.",
    "7#9": "a 7 chord with a 9th a half step higher on top (C7#9 adds Bb and D#): gritty, the blues-rock sound.",
    "maj7#11": "a maj7 chord with a raised 11th on top (Cmaj7#11 adds B and F#): bright and floating.",
    "7#11": "a 7 chord with a raised 11th on top (C7#11 adds Bb and F#): bright but restless.",
    "13": "a 7 chord with the 9th and the 13th (the 6th, an octave up) on top (C13 adds Bb, D and A): full and jazzy.",
    "m13": "a minor chord with the 7, 9 and 13 stacked on it (Cm13 adds Bb, D and A): smooth and still minor.",
}


def _glossary(nkey: dict, shown: List[tuple], used: set, examples: Optional[dict] = None, modes: Optional[set] = None,
              several: bool = False) -> List[tuple]:
    """(term, plain words) for each term the Nashville section wrote, once each, in a fixed order. examples: the key of the
    first borrowed and chromatic line (so each entry explains a line above it, not the longest key area); modes: the modes
    of the session's key areas; several: the session has more than one key area."""
    k = nkey["key"]
    examples = examples or {}
    modes = modes or {nkey["mode"]}
    marks, extensions, accidental = set(), [], None
    for item in shown:
        number, chord = item[0], item[1]
        in_key = item[2] if len(item) > 2 and item[2] else k
        # 6/9 is a shape, not a slash: 4^6/9 is a 6/9 chord on 4 (and 4^6/9/5 one over 5)
        m = _NUMBER_PARTS_RE.match((number or "").replace("6/9", "6~9"))
        if not m:
            continue
        acc, middle, slash, bass_acc = m.groups()
        middle = middle.replace("6~9", "6/9")
        if acc and accidental is None and isinstance(chord, str) and _CHORD_ROOT_RE.match(chord):
            accidental = (number, _CHORD_ROOT_RE.match(chord).group(0), in_key)
        if acc or bass_acc:
            marks.add("b#")
        if slash:
            marks.add("/")
        if middle in ("°", "°7", "ø7", "+"):
            marks.add(middle)
            continue
        if middle.startswith("^"):
            marks.add("^")
            middle = middle[1:]
        if middle.startswith("m") and not middle.startswith("maj"):
            marks.add("m")
            if middle not in _EXTENSIONS:  # a minor shape with words of its own (m11) keeps them
                middle = middle[1:]
        ext = middle.strip("()")
        if ext and ext not in extensions:
            extensions.append(ext)
    home = "the minor home chord itself, 1m" if modes == {"minor"} else "the chord on the key's home note" \
        if modes == {"major"} else "the chord on the key's home note (in a minor key, the minor home chord itself, 1m)"
    out = [("Nashville numbers", f"chords named by where they sit in the key instead of by letter. 1 is {home}, "
                                 f"4 is the chord on the 4th note of the scale, and so on, so a progression reads the "
                                 f"same in every key.")]
    if "b#" in marks:
        example = f" In {accidental[2]}, {accidental[0]} is {accidental[1]}." if accidental else ""
        out.append(("b and #", "the chord's root (or bass) sits a half step below (b, flat) or above (#, sharp) that "
                               "step of the major scale built on the home note." + example))
    if "m" in marks:
        out.append(("m", "a minor chord, the darker sound (6m is the minor chord on 6)."))
    for mark, words in (("°", "diminished: a minor chord with its 5th lowered, tense and unstable."),
                        ("°7", "a diminished chord with one more minor third on top; every note is evenly spaced."),
                        ("ø7", "half-diminished: a diminished chord with a 7 (Bm7b5 is 7ø7 in C major)."),
                        ("+", "augmented: a major chord with its 5th raised.")):
        if mark in marks:
            out.append((mark, words))
    for ext in extensions:
        out.append((ext, _EXTENSIONS.get(ext, "extra stacked notes, named by their distance above the root.")))
    if "^" in marks:
        out.append(("^", "only a joiner, so a chord's shape does not run into its number: 5^7 is a 7 chord on 5."))
    if "/" in marks:
        out.append(("/", "the number after the slash is the lowest note: 1/3 is the 1 chord with the 3rd of the scale "
                         "in the bass."))
    if "loop" in used:
        out.append(("loop", "the same 3 or 4 chords played back to back, at least twice in a row."))
    if "borrowed" in used:
        ex, part = examples.get("borrowed") or k, " of its part" if several else ""
        out.append(("borrowed", f"a chord from the parallel key{part}, the one on the same home note in the other mode "
                                f"({_parallel_key(ex)} for {ex}). It is outside the key, and a common way to add colour."))
    if "chromatic" in used:
        ex = examples.get("chromatic") or k
        out.append(("chromatic", f"a chord that belongs neither to the key of its part nor to that key's parallel key (in "
                                 f"{ex}, neither {ex} nor {_parallel_key(ex)})." if several else
                                 f"a chord that belongs to neither {ex} nor {_parallel_key(ex)}."))
    if "raised 7th" in used:
        out.append(("raised 7th", "the note a half step below a minor key's home note (C# in D minor). Minor-key music "
                                  "usually plays it in the 5 chord; without it, a minor key has exactly the notes of "
                                  "its relative major (D minor and F major), so the numbers count from the major."))
    if "home chord" in used:
        out.append(("home chord", "a minor chord the music keeps sounding (Am in Am G F G). When nearly every note is on "
                                  "its scale, a key that leaves out a note you keep playing cannot be home, so the numbers "
                                  "count from that minor key or its relative major (A minor or C major for Am)."))
    if "raised 7th" in used or "home chord" in used:
        out.append(("r", "how closely your notes match a key's typical note weights, from 0 (no match) to 1."))
    return out
