"""Claude's hand on the piano page: a cue channel and the verbs that send into it.

The server side (arsenal/serve.py routes these):
  POST /api/piano/cue           {"cue": CUE} -> 200 {"id", "listeners"}; 400 for a malformed cue; 403 cross-site
  GET  /api/piano/cues          text/event-stream: opens with "retry: 1000 / id: <cursor>", then each cue as
                                "id: N / event: cue / data: {id, cue, sent_at}", ": hb" every 15 s. Last-Event-ID (or
                                ?lastEventId= when the header is absent) replays newer cues from the last 50 that are
                                younger than 10 s. Ids count up from the server's boot time in epoch ms.
  GET  /api/piano/cues/status   {"listeners", "last_id"}

CUE = {"type": "play" | "hover" | "sequence" | "clear", "notes": [21..108], "velocity": 1..127 (80),
       "hold_ms": >= 0 (2500; 0 = until clear), "arpeggio_ms": >= 0 (0), "sound": bool (play true, hover false),
       "label": str|null, "detail": str|null, "steps": [{"at_ms", "type", "notes", "velocity", "hold_ms",
       "arpeggio_ms", "label", "detail"}], "source": "claude" | "replay"}
validate_cue fills the defaults in, so every listener receives explicit values.

The verbs (py -m arsenal.pianocue <verb> --help):
  play, hover, progression, replay, clear, voicing (prints only), status.
Chord names, Nashville numbers and voicings come from arsenal/pianocue_voicing.mjs, which runs the THEORY block
of arsenal/web/piano.js and arsenal/web/piano/nashville.js, so the names and numbers match the page's. --minor relative
follows a page whose minor-key numbering (arsenal.piano.minor) is set to relative.
"""
from __future__ import annotations

import argparse
import json
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PACKAGE = Path(__file__).resolve().parent
BRIDGE = PACKAGE / "pianocue_voicing.mjs"
DEFAULT_PORT = 8793

TYPES = ("play", "hover", "sequence", "clear")
STEP_TYPES = ("play", "hover")
SOURCES = ("claude", "replay")
NOTE_MIN, NOTE_MAX = 21, 108
MAX_NOTES = 88
MAX_STEPS = 4000
MAX_MS = 30 * 60 * 1000        # no hold, stagger or step lands more than 30 minutes out
MAX_TEXT = 500
DEFAULTS = {"velocity": 80, "hold_ms": 2500, "arpeggio_ms": 0}
CUE_KEYS = {"type", "notes", "velocity", "hold_ms", "arpeggio_ms", "sound", "label", "detail", "steps", "source"}
STEP_KEYS = {"at_ms", "type", "notes", "velocity", "hold_ms", "arpeggio_ms", "label", "detail"}
RING = 50
REPLAY_MAX_AGE_S = 10.0
HEARTBEAT_S = 15.0
MAX_CUE_BODY = 2 * 1024 * 1024

NO_LISTENER = "no piano page is listening - open http://127.0.0.1:{port}/piano"


# ================================================================================================ validation
class CueError(ValueError):
    """A malformed cue: the message says which field and what was expected."""


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _int_field(obj: dict, field: str, where: str, lo: int, hi: int, default: int) -> int:
    if field not in obj or obj[field] is None:
        return default
    value = obj[field]
    if not _is_int(value) or not lo <= value <= hi:
        raise CueError(f"{where}{field} must be an integer {lo}..{hi} (got {value!r})")
    return value


def _text_field(obj: dict, field: str, where: str) -> Optional[str]:
    value = obj.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise CueError(f"{where}{field} must be a string or null (got {value!r})")
    if len(value) > MAX_TEXT:
        raise CueError(f"{where}{field} is longer than {MAX_TEXT} characters")
    return value


def _notes_field(obj: dict, where: str) -> List[int]:
    notes = obj.get("notes")
    if not isinstance(notes, list) or not notes:
        raise CueError(f"{where}notes must be a non-empty list of MIDI note numbers {NOTE_MIN}..{NOTE_MAX}")
    if len(notes) > MAX_NOTES:
        raise CueError(f"{where}notes has {len(notes)} notes; at most {MAX_NOTES}")
    for n in notes:
        if not _is_int(n) or not NOTE_MIN <= n <= NOTE_MAX:
            raise CueError(f"{where}notes must be MIDI note numbers {NOTE_MIN}..{NOTE_MAX} (got {n!r})")
    return sorted(set(notes))


def _unknown(obj: dict, allowed: set, where: str) -> None:
    extra = sorted(set(obj) - allowed)
    if extra:
        raise CueError(f"{where}unknown field{'s' if len(extra) > 1 else ''} {', '.join(map(repr, extra))}; "
                       f"expected some of {', '.join(sorted(allowed))}")


def validate_cue(cue) -> dict:
    """Return the cue with every default filled in, or raise CueError. The input is not modified.

    play and hover: notes are sorted bottom-up and de-duplicated. A hover never sounds. sequence: steps are sorted
    by at_ms (stable), each with its own velocity, hold_ms and arpeggio_ms (the cue's own values are the defaults).
    clear: only type, source, label and detail.
    """
    if not isinstance(cue, dict):
        raise CueError('the cue must be a JSON object, e.g. {"type": "play", "notes": [60, 64, 67]}')
    kind = cue.get("type")
    if kind not in TYPES:
        raise CueError(f"type must be one of {', '.join(TYPES)} (got {kind!r})")
    _unknown(cue, CUE_KEYS, "")
    source = cue.get("source", "claude")
    if source is None:
        source = "claude"
    if source not in SOURCES:
        raise CueError(f"source must be one of {', '.join(SOURCES)} (got {source!r})")
    out = {"type": kind, "label": _text_field(cue, "label", ""), "detail": _text_field(cue, "detail", ""),
           "source": source}
    if kind == "clear":
        _unknown(cue, {"type", "source", "label", "detail"}, "a clear cue has ")
        return out

    velocity = _int_field(cue, "velocity", "", 1, 127, DEFAULTS["velocity"])
    hold_ms = _int_field(cue, "hold_ms", "", 0, MAX_MS, DEFAULTS["hold_ms"])
    arpeggio_ms = _int_field(cue, "arpeggio_ms", "", 0, MAX_MS, DEFAULTS["arpeggio_ms"])
    sound = cue.get("sound")
    if sound is not None and not isinstance(sound, bool):
        raise CueError(f"sound must be true or false (got {sound!r})")

    if kind in ("play", "hover"):
        if "steps" in cue:
            raise CueError(f"a {kind} cue has no steps; send type sequence for timed steps")
        if kind == "hover" and sound:
            raise CueError("a hover never sounds; send type play (with sound true) to hear it")
        out.update(notes=_notes_field(cue, ""), velocity=velocity, hold_ms=hold_ms, arpeggio_ms=arpeggio_ms,
                   sound=kind == "play" and sound is not False)
        return out

    # sequence
    if "notes" in cue:
        raise CueError("a sequence cue has no notes of its own; put them in steps")
    steps = cue.get("steps")
    if not isinstance(steps, list) or not steps:
        raise CueError("a sequence needs steps, a non-empty list of {at_ms, type, notes, ...}")
    if len(steps) > MAX_STEPS:
        raise CueError(f"a sequence has at most {MAX_STEPS} steps (got {len(steps)})")
    clean = []
    for i, step in enumerate(steps):
        where = f"steps[{i}]."
        if not isinstance(step, dict):
            raise CueError(f"steps[{i}] must be an object")
        _unknown(step, STEP_KEYS, where)
        step_type = step.get("type")
        if step_type not in STEP_TYPES:
            raise CueError(f"{where}type must be play or hover (got {step_type!r})")
        at_ms = step.get("at_ms")
        if not _is_int(at_ms) or not 0 <= at_ms <= MAX_MS:
            raise CueError(f"{where}at_ms must be an integer 0..{MAX_MS} (got {at_ms!r})")
        clean.append({"at_ms": at_ms, "type": step_type, "notes": _notes_field(step, where),
                      "velocity": _int_field(step, "velocity", where, 1, 127, velocity),
                      "hold_ms": _int_field(step, "hold_ms", where, 0, MAX_MS, hold_ms),
                      "arpeggio_ms": _int_field(step, "arpeggio_ms", where, 0, MAX_MS, arpeggio_ms),
                      "label": _text_field(step, "label", where), "detail": _text_field(step, "detail", where)})
    clean.sort(key=lambda s: s["at_ms"])
    out.update(steps=clean, velocity=velocity, hold_ms=hold_ms, arpeggio_ms=arpeggio_ms,
               sound=sound is not False)
    return out


# ======================================================================================================= hub
class CueHub:
    """Fan-out of cues to every connected event stream, with a small replay buffer for reconnects.

    publish() numbers a cue and hands the encoded frame to every listener's queue under one lock, so a listener that
    subscribes with a Last-Event-ID gets each cue exactly once: from the ring buffer or live, never both.

    Ids stay unique across server restarts: they count up from id_base, which defaults to the boot time in epoch
    milliseconds (still plain integers). A page that reconnects to a restarted server therefore never sends an id the
    new server has issued too, and a Last-Event-ID below id_base is known to come from an earlier server.
    """

    def __init__(self, ring: int = RING, replay_max_age_s: float = REPLAY_MAX_AGE_S,
                 heartbeat_s: float = HEARTBEAT_S, clock=time.monotonic, id_base: Optional[int] = None):
        self.replay_max_age_s = replay_max_age_s
        self.heartbeat_s = heartbeat_s
        self._clock = clock
        self._lock = threading.Lock()
        self._ring: deque = deque(maxlen=ring)  # (id, monotonic time, frame bytes)
        self._listeners: Dict[int, "queue.SimpleQueue"] = {}
        self._next_token = 0
        self.id_base = int(time.time() * 1000) if id_base is None else int(id_base)
        self._last_id = self.id_base
        self._closed = False

    @staticmethod
    def frame(cue_id: int, cue: dict, sent_at: int) -> bytes:
        data = json.dumps({"id": cue_id, "cue": cue, "sent_at": sent_at}, separators=(",", ":"))
        return f"id: {cue_id}\nevent: cue\ndata: {data}\n\n".encode("utf-8")

    def publish(self, cue: dict) -> dict:
        with self._lock:
            self._last_id += 1
            cue_id = self._last_id
            frame = self.frame(cue_id, cue, int(time.time() * 1000))
            self._ring.append((cue_id, self._clock(), frame))
            for q in self._listeners.values():
                q.put(frame)
            return {"id": cue_id, "listeners": len(self._listeners)}

    def subscribe(self, last_event_id: Optional[int] = None) -> Tuple[int, "queue.SimpleQueue", List[bytes]]:
        """Register a listener. Returns (token, queue, backlog): the backlog holds the replayed frames.

        Nothing is replayed without a Last-Event-ID (a freshly opened page must not play old cues). An id below this
        hub's id_base or above the last id it issued comes from another (earlier) server, so every young cue is newer.
        """
        token, q, backlog, _ = self._subscribe(last_event_id)
        return token, q, backlog

    def open_stream(self, last_event_id: Optional[int] = None) -> Tuple[int, "queue.SimpleQueue", bytes]:
        """subscribe() for an event stream: returns (token, queue, preamble), the bytes to write before live frames.

        The preamble is "retry: 1000" with an "id:" line, then the replayed frames. The id is the cursor just before
        the first replayed cue, or the last id issued, so the page's EventSource has a Last-Event-ID to send back on a
        reconnect even before it has received a cue.
        """
        token, q, backlog, cursor = self._subscribe(last_event_id)
        return token, q, f"retry: 1000\nid: {cursor}\n\n".encode("ascii") + b"".join(backlog)

    def _subscribe(self, last_event_id: Optional[int]):
        with self._lock:
            token = self._next_token
            self._next_token += 1
            q: "queue.SimpleQueue" = queue.SimpleQueue()
            if self._closed:
                q.put(None)
            self._listeners[token] = q
            entries = []
            if last_event_id is not None:
                now = self._clock()
                foreign = last_event_id < self.id_base or last_event_id > self._last_id
                entries = [(cue_id, frame) for cue_id, t, frame in self._ring
                           if (foreign or cue_id > last_event_id) and now - t < self.replay_max_age_s]
            cursor = entries[0][0] - 1 if entries else self._last_id
            return token, q, [frame for _, frame in entries], cursor

    def unsubscribe(self, token: int) -> None:
        with self._lock:
            self._listeners.pop(token, None)

    def status(self) -> dict:
        with self._lock:
            return {"listeners": len(self._listeners), "last_id": self._last_id}

    def close(self) -> None:
        """Wake every stream so its thread ends (server shutdown, tests)."""
        with self._lock:
            self._closed = True
            for q in self._listeners.values():
                q.put(None)


# ====================================================================================================== replay
def parse_clock(text: str) -> int:
    """"5:22" -> 322000 ms; also "1:02:03", "5:22.5" and plain seconds ("322")."""
    t = str(text).strip()
    m = re.fullmatch(r"(?:(\d+):)?(\d+):(\d{1,2}(?:\.\d+)?)", t)
    if m:
        hours = int(m.group(1) or 0)
        return int(round((hours * 3600 + int(m.group(2)) * 60 + float(m.group(3))) * 1000))
    if re.fullmatch(r"\d+(?:\.\d+)?", t):
        return int(round(float(t) * 1000))
    raise ValueError(f"not a time: {text!r} (use m:ss, like 5:22)")


def clock_text(ms: int) -> str:
    s = max(0, int(ms)) // 1000
    return f"{s // 60}:{s % 60:02d}" if s < 3600 else f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}"


def _note_spans(events: List[dict]) -> List[dict]:
    """Every note-on with the time its sound ended: the piano's own sound_end when it logged one, else the next
    strike of that note, else inferred from off and the sustain pedal (as performance.summarize does)."""
    evs = sorted(events, key=lambda e: e["t_ms"])
    end_ms = max((e["t_ms"] for e in evs), default=0)
    spans: List[dict] = []
    open_by_note: Dict[int, dict] = {}     # note -> the span still waiting for its end
    held: Dict[int, bool] = {}              # note -> key still down (for sessions without sound_end)
    pedal_down = False
    has_sound_end = any(e["kind"] == "sound_end" for e in evs)

    def finish(note: int, t: int) -> None:
        span = open_by_note.pop(note, None)
        if span is not None and span["end_ms"] is None:
            span["end_ms"] = max(t, span["t_ms"])
        held.pop(note, None)

    for e in evs:
        kind, t = e["kind"], e["t_ms"]
        if kind == "on":
            note = e["note"]
            if note in open_by_note:
                finish(note, t)  # a repeat strike ends the previous sound
            span = {"note": note, "t_ms": t, "vel": e.get("vel", 80), "end_ms": None}
            spans.append(span)
            open_by_note[note] = span
            held[note] = True
        elif kind == "sound_end":
            finish(e["note"], t)
        elif has_sound_end:
            continue  # the piano said when each sound ended; off and pedal add nothing
        elif kind == "off":
            note = e["note"]
            if note in open_by_note:
                held[note] = False
                if not pedal_down:
                    finish(note, t)
        elif kind == "pedal":
            if e.get("down"):
                pedal_down = True
            elif pedal_down:
                pedal_down = False
                for note in [n for n, down in held.items() if not down]:
                    finish(note, t)
    for note in list(open_by_note):
        finish(note, end_ms)
    return spans


def _chord_marks(events: List[dict]) -> List[dict]:
    return sorted((e for e in events if e["kind"] == "chord" and e.get("chord") and e.get("detect_kind") == "chord"),
                  key=lambda e: e["t_ms"])


def build_replay_cue(events: List[dict], start_ms: int, seconds: float = 8.0, speed: float = 1.0,
                     at_text: Optional[str] = None, session: Optional[str] = None) -> dict:
    """A sequence cue rebuilt from logged note events: one play step per strike inside the window, each held until
    its sound ended (pedal-held notes too), clipped to the window's end. Notes still sounding at the window's start
    open the sequence at 0 ms. Steps carry the chord the page named at that moment, when it named one."""
    if seconds <= 0:
        raise ValueError("--seconds must be positive")
    if speed <= 0:
        raise ValueError("--speed must be positive")
    end_ms = start_ms + int(round(seconds * 1000))
    marks = _chord_marks(events)
    mark_times = [m["t_ms"] for m in marks]

    def chord_at(t: int) -> Optional[dict]:
        from bisect import bisect_right
        i = bisect_right(mark_times, t + 25) - 1  # the page logs the chord a few ms after the strike
        return marks[i] if i >= 0 and t - marks[i]["t_ms"] < 4000 else None

    steps = []
    carried = []
    for span in _note_spans(events):
        if span["t_ms"] < start_ms < span["end_ms"]:
            carried.append(span)
        elif start_ms <= span["t_ms"] < end_ms:
            at = int(round((span["t_ms"] - start_ms) / speed))
            hold = int(round((min(span["end_ms"], end_ms) - span["t_ms"]) / speed))
            mark = chord_at(span["t_ms"])
            steps.append({"at_ms": at, "type": "play", "notes": [span["note"]], "velocity": max(1, min(127, span["vel"])),
                          "hold_ms": max(1, hold), "arpeggio_ms": 0,
                          "label": mark["chord"] if mark else None,
                          "detail": (f"{mark['nns']} in {mark['nns_key']}" if mark and mark.get("nns") and mark.get("nns_key")
                                     else None)})
    at_text = at_text or clock_text(start_ms)
    if carried:
        by_end: Dict[int, List[dict]] = {}
        for span in carried:
            by_end.setdefault(min(span["end_ms"], end_ms), []).append(span)
        mark = chord_at(start_ms)
        for end, group in sorted(by_end.items()):
            steps.append({"at_ms": 0, "type": "play", "notes": sorted({s["note"] for s in group}),
                          "velocity": max(1, min(127, round(sum(s["vel"] for s in group) / len(group)))),
                          "hold_ms": max(1, int(round((end - start_ms) / speed))), "arpeggio_ms": 0,
                          "label": mark["chord"] if mark else None,
                          "detail": f"already sounding at {at_text}"})
    if not steps:
        raise ValueError(f"nothing sounds between {clock_text(start_ms)} and {clock_text(end_ms)}")
    steps.sort(key=lambda s: s["at_ms"])
    detail = f"{seconds:g} s from {session}" if session else f"{seconds:g} s"
    if speed != 1:
        detail += f" at {speed:g}x"
    return {"type": "sequence", "steps": steps, "label": f"you, at {at_text}", "detail": detail, "source": "replay"}


# ====================================================================================================== bridge
class VoicingError(RuntimeError):
    pass


def voice(items: List[str], key: Optional[str] = None, voicing: str = "close", octave: Optional[int] = None,
          voice_lead: bool = False, minor: str = "tonic") -> List[dict]:
    """Run arsenal/pianocue_voicing.mjs on a batch. Each result has input, name, number, notes (MIDI), names,
    roundtrip {detected, match, page_name, page_number}, warnings; or error. minor: "tonic" (the page's default) or
    "relative" (minor keys numbered from their relative major, as the page's arsenal.piano.minor pref can be)."""
    node = shutil.which("node")
    if not node:
        raise VoicingError("node is not on PATH; the voicing bridge runs arsenal/pianocue_voicing.mjs with it")
    request = {"items": items, "key": key, "voicing": voicing, "octave": octave, "voice_lead": voice_lead,
               "minor": minor}
    proc = subprocess.run([node, str(BRIDGE)], input=json.dumps(request), capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    if proc.returncode != 0 and not proc.stdout.strip():
        raise VoicingError(f"the voicing bridge failed: {proc.stderr.strip() or proc.returncode}")
    try:
        reply = json.loads(proc.stdout)
    except ValueError:
        raise VoicingError(f"the voicing bridge answered something that is not JSON: {proc.stdout[:300]!r}")
    if not reply.get("ok"):
        raise VoicingError(reply.get("error") or "the voicing bridge refused the request")
    return reply["results"]


# A token only notes can be: a note with its octave ("Ab2", "C#4") or a number no Nashville degree is (8 and up, so MIDI
# notes like 57). "Ab7" is also a chord; a segment holding one stays whole, as before.
_NOTE_TOKEN = re.compile(r"[A-Ga-g](?:#{1,2}|b{1,2})?-?\d{1,2}|\d{2,3}|[089]")


def split_progression(text: str) -> List[str]:
    """Chords or numbers separated by "|" or spaces. Without a "|", every whitespace-separated token is an item. With
    one, a segment that could be notes is one item, so explicit notes can be grouped ("Ab2 Eb3 G3 | Bb2 F3 Ab3"); a
    segment of chord names or numbers with spaces in it gives each its own item ("Abmaj9#11 Bb7sus4/Eb | Ebmaj9" is three
    chords, "1 4 | 5" three numbers). A segment is notes when any token is a note with an octave or a number above 7,
    beats (":2") aside."""
    if "|" not in text:
        return text.split()
    items: List[str] = []
    for seg in text.split("|"):
        toks = seg.split()
        if not toks:
            continue
        if len(toks) > 1 and not any(_NOTE_TOKEN.fullmatch(re.sub(r":\d+(?:\.\d+)?$", "", t)) for t in toks):
            items.extend(toks)
        else:
            items.append(" ".join(toks))
    return items


# ====================================================================================================== client
class ServerError(RuntimeError):
    pass


def _request(port: int, method: str, path: str, body: Optional[dict] = None, timeout: float = 10.0):
    url = f"http://127.0.0.1:{port}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data is not None else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            payload = json.loads(raw or b"null")
        except ValueError:
            payload = {"error": raw.decode("utf-8", "replace")[:300]}
        if err.code == 404 and "no route" in str((payload or {}).get("error", "")):
            raise ServerError(f"the server on 127.0.0.1:{port} has no piano cue channel; it predates it - restart "
                              f"py -m arsenal serve --port {port}")
        return err.code, payload
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as err:
        raise ServerError(f"no arsenal server answers on 127.0.0.1:{port} ({getattr(err, 'reason', err)}) - start it "
                          f"with py -m arsenal serve --port {port}")


def send_cue(port: int, cue: dict) -> dict:
    status, reply = _request(port, "POST", "/api/piano/cue", {"cue": cue})
    if status != 200:
        raise ServerError(f"the server refused the cue ({status}): {(reply or {}).get('error', reply)}")
    return reply


def cue_status(port: int) -> dict:
    status, reply = _request(port, "GET", "/api/piano/cues/status")
    if status != 200:
        raise ServerError(f"status answered {status}: {reply}")
    return reply


# ========================================================================================================= CLI
def _format_result(r: dict, key: Optional[str]) -> List[str]:
    if r.get("error"):
        return [f"  {r['input']}: {r['error']}"]
    head = r["name"] or r["input"]
    if r.get("number"):
        head += f"   {r['number']} in {r.get('key') or key}"
    lines = [f"  {head}   ({r.get('voicing')} voicing)",
             f"    notes  {' '.join(r['names'])}",
             f"    midi   {' '.join(str(n) for n in r['notes'])}"]
    rt = r.get("roundtrip") or {}
    if rt:
        page = rt.get("page_name") or rt.get("detected")
        extra = f", number {rt['page_number']}" if rt.get("page_number") else ""
        lines.append(f"    page   reads {page} ({rt.get('match')}{extra})")
        if rt.get("omits"):
            lines.append(f"    omits  {', '.join(rt['omits'])}")
    for w in r.get("warnings") or []:
        lines.append(f"    note   {w}")
    return lines


def _chord_detail(r: dict, key: Optional[str], custom_label: bool = False) -> Optional[str]:
    """The line under the label. A typed Nashville number is shown as typed ("#4 in Eb major"), even when the page
    numbers the chord another way (the CLI prints that as a note). Explicit notes under Claude's own --label also say
    what the page reads them as ("Cm9/Ab · 4maj9#11 in Eb major")."""
    where = r.get("key") or key
    number = r.get("number_typed") or r.get("number")
    parts = []
    if r.get("kind") == "notes" and custom_label and r.get("name"):
        parts.append(r["name"])
    if number and where:
        parts.append(f"{number} in {where}")
    return " · ".join(parts) or None


def _finish(sent: dict, port: int, out) -> int:
    print(f"sent cue #{sent['id']} to {sent['listeners']} listener{'s' if sent['listeners'] != 1 else ''}", file=out)
    if sent["listeners"] == 0:
        print(NO_LISTENER.format(port=port), file=sys.stderr)
        return 3
    return 0


def _voiced(args, items: List[str], voice_lead: bool = False) -> Optional[List[dict]]:
    try:
        results = voice(items, key=args.key, voicing=args.voicing, octave=args.octave, voice_lead=voice_lead,
                        minor=args.minor)
    except VoicingError as exc:
        print(f"voicing failed: {exc}", file=sys.stderr)
        return None
    bad = [r for r in results if r.get("error")]
    if bad:
        for r in bad:
            print(f"cannot voice {r['input']!r}: {r['error']}", file=sys.stderr)
        return None
    return results


def _cmd_play(args, hover: bool, out) -> int:
    text = " ".join(args.chord)
    results = _voiced(args, [text])
    if results is None:
        return 2
    r = results[0]
    cue = {"type": "hover" if hover else "play", "notes": r["notes"],
           "label": args.label if args.label is not None else r["name"],
           "detail": args.detail if args.detail is not None else _chord_detail(r, args.key, args.label is not None),
           "source": "claude"}
    if args.vel is not None:
        cue["velocity"] = args.vel
    if args.hold is not None:
        cue["hold_ms"] = int(round(args.hold * 1000))
    if args.arp is not None:
        cue["arpeggio_ms"] = args.arp
    if not hover:
        cue["sound"] = not args.silent
    cue = validate_cue(cue)
    sent = send_cue(args.port, cue)
    print(f"{cue['type']}{'' if cue.get('sound', True) or hover else ' (silent)'}: label {cue['label']!r}"
          f"{', detail ' + repr(cue['detail']) if cue['detail'] else ''}", file=out)
    for line in _format_result(r, args.key):
        print(line, file=out)
    return _finish(sent, args.port, out)


def _cmd_progression(args, out) -> int:
    raw = split_progression(args.chords)
    if not raw:
        print("the progression is empty", file=sys.stderr)
        return 2
    items, beats = [], []
    for item in raw:
        m = re.fullmatch(r"(.+?):(\d+(?:\.\d+)?)", item)
        items.append(m.group(1) if m else item)
        beats.append(float(m.group(2)) if m else float(args.beats))
    results = _voiced(args, items, voice_lead=args.voice_lead)
    if results is None:
        return 2
    beat_ms = 60000.0 / args.bpm
    starts, at = [], 0.0
    for b in beats:
        starts.append(int(round(at)))
        at += b * beat_ms
    starts.append(int(round(at)))
    steps = []
    for i, r in enumerate(results):
        length = starts[i + 1] - starts[i]
        if args.hold is not None:
            hold = int(round(args.hold * 1000))
        elif args.hover:
            hold = max(1, length)  # a hover lasts until the next begins, so the ghost keys never blink between chords
        else:
            hold = max(1, length - 40)  # a breath before the next strike
        step = {"at_ms": starts[i], "type": "hover" if args.hover else "play", "notes": r["notes"],
                "hold_ms": hold, "label": r["name"], "detail": _chord_detail(r, args.key)}
        if args.vel is not None:
            step["velocity"] = args.vel
        if args.arp is not None:
            step["arpeggio_ms"] = args.arp
        steps.append(step)
    cue = validate_cue({"type": "sequence", "steps": steps, "source": "claude",
                        "label": args.label if args.label is not None else " | ".join(r["name"] for r in results),
                        "detail": args.detail if args.detail is not None else
                        (f"in {args.key}, {args.bpm:g} bpm" if args.key else f"{args.bpm:g} bpm")})
    sent = send_cue(args.port, cue)
    print(f"sequence of {len(steps)} {'hovers' if args.hover else 'chords'} at {args.bpm:g} bpm "
          f"({'voice-led ' if args.voice_lead else ''}{args.voicing}), {at / 1000:.2f} s:", file=out)
    for step, r in zip(cue["steps"], results):
        print(f"  @{step['at_ms']:>6} ms  hold {step['hold_ms']:>5}", file=out)
        for line in _format_result(r, args.key):
            print("  " + line, file=out)
    if args.voice_lead and len(results) > 1:
        moves = [r.get("movement") for r in results[1:] if r.get("movement") is not None]
        if moves:
            print(f"  voice-leading movement per change (semitones): {moves}", file=out)
    return _finish(sent, args.port, out)


def _cmd_replay(args, out) -> int:
    from .performance import PerformanceError, PerformanceStore
    store = PerformanceStore(args.root)
    session = store.latest() if args.session == "latest" else args.session
    if not session:
        print(f"no practice sessions under {store.root}", file=sys.stderr)
        return 2
    try:
        events = store.events(session)  # read only
        start_ms = parse_clock(args.at)
        cue = validate_cue(build_replay_cue(events, start_ms, args.seconds, args.speed, at_text=args.at,
                                            session=session))
    except (PerformanceError, ValueError) as exc:
        print(f"cannot replay: {exc}", file=sys.stderr)
        return 2
    sent = send_cue(args.port, cue)
    print(f"replay {session} at {args.at} for {args.seconds:g} s (speed {args.speed:g}): {len(cue['steps'])} steps, "
          f"label {cue['label']!r}", file=out)
    names = "C Db D Eb E F F# G Ab A Bb B".split()
    for step in cue["steps"]:
        notes = " ".join(f"{names[n % 12]}{n // 12 - 1}" for n in step["notes"])
        tag = f"  {step['label']}" if step["label"] else ""
        tag += f"  ({step['detail']})" if step["detail"] else ""
        print(f"  @{step['at_ms']:>6} ms  {notes:<16} vel {step['velocity']:>3}  hold {step['hold_ms']:>5}{tag}", file=out)
    return _finish(sent, args.port, out)


def _cmd_voicing(args, out) -> int:
    text = " ".join(args.chord)
    items = split_progression(text) if "|" in text else [text]
    try:
        results = voice(items, key=args.key, voicing=args.voicing, octave=args.octave, minor=args.minor)
    except VoicingError as exc:
        print(f"voicing failed: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(results, indent=2), file=out)
    else:
        for r in results:
            for line in _format_result(r, args.key):
                print(line, file=out)
    return 2 if any(r.get("error") for r in results) else 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="py -m arsenal.pianocue",
                                 description="Claude's hand on the piano page: play, hover, replay and clear chords")
    sub = ap.add_subparsers(dest="verb", required=True)

    def port(p):
        p.add_argument("--port", type=int, default=DEFAULT_PORT, help="the arsenal server's port (default 8793)")

    def chord_opts(p, voicing_default="spread"):
        p.add_argument("--key", help='a key for numbers and spelling, e.g. "Eb major", "C# minor"')
        p.add_argument("--voicing", choices=("close", "open", "spread", "drop2", "shell"), default=voicing_default)
        p.add_argument("--octave", type=int,
                       help="the octave of the chord's root (spread: of the bass); a slash bass goes below it, and "
                            "drop2's dropped voice and bass land an octave lower (drop2 C --octave 3: C2 G2 C3 E3 C4; "
                            "C/G: G2 C3 E3 C4, the dropped G is the bass); default by style")
        p.add_argument("--minor", choices=("tonic", "relative"), default="tonic",
                       help="how a minor key is numbered, as the page's minor setting: tonic (Am in A minor is 1m, the "
                            "page's default) or relative (from the relative major: Am is 6m)")

    for verb, hover in (("play", False), ("hover", True)):
        p = sub.add_parser(verb, help=("sound and show" if not hover else "show without sound") +
                           ' a chord name, a Nashville number with --key, or notes ("Ab3 Eb4 G4" or MIDI numbers)')
        p.add_argument("chord", nargs="+")
        chord_opts(p)
        p.add_argument("--arp", type=int, help="stagger bottom-up, ms between notes")
        p.add_argument("--hold", type=float, help="seconds to hold (0 = until clear; default 2.5)")
        p.add_argument("--vel", type=int, help="velocity 1..127 (default 80)")
        p.add_argument("--label", help="the label shown (default: the chord name)")
        p.add_argument("--detail", help="the detail line (default: the number in the key)")
        if not hover:
            p.add_argument("--silent", action="store_true", help="show the keys pressed, without sound")
        port(p)

    pg = sub.add_parser("progression", help='a timed sequence: "Abmaj9#11 | Bb7sus4/Eb | Ebmaj9" (item:beats allowed)',
                        description='A timed sequence of chords, one per --beats: "Abmaj9#11 | Bb7sus4/Eb | Ebmaj9", or '
                                    'with --key "4maj9#11 | 5^7sus4/1:2 | 1" (item:beats sets one chord\'s length). '
                                    'Chords may also be separated by spaces, inside a bar too ("1 4 | 5 1"). Notes '
                                    'grouped between bars are one chord each ("Ab2 Eb3 G3 | Bb2 F3 Ab3").')
    pg.add_argument("chords")
    chord_opts(pg)
    pg.add_argument("--bpm", type=float, default=72.0)
    pg.add_argument("--beats", type=float, default=4.0, help="beats per chord (default 4)")
    pg.add_argument("--hover", action="store_true", help="show the chords without sound")
    pg.add_argument("--voice-lead", action="store_true",
                    help="voice each chord with the least movement from the previous one, keeping the bass")
    pg.add_argument("--arp", type=int)
    pg.add_argument("--hold", type=float,
                    help="seconds each chord holds (default: its length minus 40 ms; a hover its full length)")
    pg.add_argument("--vel", type=int)
    pg.add_argument("--label")
    pg.add_argument("--detail")
    port(pg)

    rp = sub.add_parser("replay", help="replay a moment from the practice log (read only)")
    rp.add_argument("session", help="a session id, or latest")
    rp.add_argument("at", help="m:ss into the session")
    rp.add_argument("--seconds", type=float, default=8.0)
    rp.add_argument("--speed", type=float, default=1.0)
    rp.add_argument("--root", help="the sessions directory (default: state/arsenal/performance)")
    port(rp)

    cl = sub.add_parser("clear", help="cancel pending cues and release every cue note and hover")
    port(cl)

    vc = sub.add_parser("voicing", help="print a voicing without sending anything")
    vc.add_argument("chord", nargs="+")
    chord_opts(vc)
    vc.add_argument("--json", action="store_true", help="print the bridge's full result")

    st = sub.add_parser("status", help="listeners and the last cue id")
    port(st)
    return ap


def _utf8_streams() -> None:
    """Claude runs these verbs through a pipe, where Windows gives Python cp1252: a label like "D♭maj9 · the ♭7"
    would raise UnicodeEncodeError after the cue was already sent. Write UTF-8 (replacing anything unencodable)."""
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if encoding != "utf8" and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main(argv=None, out=None) -> int:
    _utf8_streams()
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        if args.verb in ("play", "hover"):
            return _cmd_play(args, args.verb == "hover", out)
        if args.verb == "progression":
            return _cmd_progression(args, out)
        if args.verb == "replay":
            return _cmd_replay(args, out)
        if args.verb == "voicing":
            return _cmd_voicing(args, out)
        if args.verb == "clear":
            sent = send_cue(args.port, validate_cue({"type": "clear", "source": "claude"}))
            return _finish(sent, args.port, out)
        if args.verb == "status":
            st = cue_status(args.port)
            print(f"listeners {st['listeners']}, last cue id {st['last_id']}", file=out)
            if st["listeners"] == 0:
                print(NO_LISTENER.format(port=args.port), file=sys.stderr)
            return 0
    except CueError as exc:
        print(f"the cue is malformed: {exc}", file=sys.stderr)
        return 2
    except ServerError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    return 2


if __name__ == "__main__":
    sys.exit(main())
