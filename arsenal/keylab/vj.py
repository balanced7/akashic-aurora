"""arsenal.keylab.vj -- the VJ engine: the KeyLab, the music and the beat, served to a page as events.

Daniel (2026-10-23): "this makes me want to vj so bad with the pads triggering effects, I think that would be super
cool ^___^ can you build something to play with? what kind of vfx sets or laser shows can you think of with cool
elements for me to accent hits and chord changes with, perhaps faders for colors too, go wild" and "there could be a
pad to play an effect with velocity changing something about the element, then we could have sort of crash close
buttons to dampen or stop the effect".

This is the ENGINE (Python). The page draws; between them there is one contract, Server-Sent Events:

  GET  http://127.0.0.1:8794/api/events   one JSON object per 'data:' line, a ': hb' heartbeat every 15 s
  GET  http://127.0.0.1:8794/api/state    last chord, bpm, the key, connected inputs, audio health, LED state
  POST http://127.0.0.1:8794/api/pads     {"colors": ["#rrggbb", ... 12]} lights the DAW-bank pads: 202 taken,
                                          409 refused (--no-leds), 503 unavailable (no KeyLab DAW output found)
  Every route but the stream answers with Connection: close (no kept-alive connection outlives its response), and
  a stopping engine refuses new streams (503).

  hello  {"t":"hello","v":1,"src":"keylab-vj","beat_engine":"a","chords":"sense|basic","pads_mode":"daw|bank|both",
          "leds":true|false,"leds_reason":null|".."}   leds false: do not POST /api/pads, it would be refused
  beat   {"t":"beat","due_ms":..,"bpm":..,"conf":0..1,"n":..,"on_beat":0..1|null}  sent ~250 ms BEFORE the beat
  energy {"t":"energy","bass":..,"mid":..,"high":..,"level":..}                      40 Hz, each 0..1, auto-gained
  hit    {"t":"hit","strength":0..1,"band":"kick|snare|hat|full"}                   a heavy transient
  chord  {"t":"chord","src":"keys|audio","name":"Dbmaj7","root":0..11,"quality":"maj7","pcs":[..],"changed":true,
          "bass":0..11,"roman":"Imaj7"|null,"key":"Db major"|null,"conf":0..1}
          name 'N' (root, quality and bass null, pcs []) = the audio hears no chord (drums, noise, a lone line);
          roman is the chord in `key`, the key the page is told (below); --chords basic sends the first seven fields
  key    {"t":"key","name":"Db major","conf":0..1,"src":"keys|audio"}  the key, when it lands or moves (blend, sense)
  tension {"t":"tension","value":0..1,"pedal_pc":0..11|null,"src":"keys|audio"}  the harmony's tension: with every
          chord, pedal and resolution chordsense decides, from the ear that names the key (blend, sense)
  note   {"t":"note","key":0..127,"vel":0..1,"on":bool}        pedal {"t":"pedal","on":bool}
  pad    {"t":"pad","pad":1..12,"vel":0..1,"on":bool,"src":"daw|bank"}
  ctl    {"t":"ctl","id":"cc105","kind":"abs|rel","value":0..1,"delta":int}
  status {"t":"status","msg":".."}

What feeds it:
  KEYS    the 'KeyLab 88 mk3 MIDI' input: notes (any channel but 10) and the sustain pedal (CC 64) -> note, pedal,
          and a chord named from what is sounding (chordview.Voicing + theory.analyze), after a 30 ms settle so a
          rolled chord is one event, not three. Chord names use flats (Db, Eb, Ab, Bb, as the page's note names
          do); pitch class 6 is Gb when the key found from the recent notes (KeyFinder) has flats, else F#
  PADS    from EITHER mode: DAW mode arrives on the 'DAW' input, channel 10, notes 0..11 = pads 1..12 (inferred);
          the normal pad bank arrives on the MIDI input, channel 10, notes 36-47 (protocol.PAD_NOTE). While FL's
          Arturia script runs, DAW-mode pads 1-8 ALSO toggle FL's step-sequencer steps on release, so the normal
          bank is the safe choice with FL open; both are accepted (--pads picks), and a hit seen on both inputs
          within 40 ms counts once
  CONTROLS every CC on either input -> ctl. Faders (CC 105-113) are absolute; knobs (91, 92, 94-97, 102-104) and
          the dial (116) are relative around 64 -- all read from Arturia's script, NOT confirmed on the hardware, so
          every CC is learned on touch: an encoder repeats a value (an absolute control only sends on change) and
          stays near 64, a fader wanders far from it. A learned kind is announced as a status
  AUDIO   WASAPI loopback (whatever is playing), or --replay-audio FILE in real time (--loop repeats it), or
          --replay-audio demo (a made-up groove) -> the beat tracker (beat_<engine>.Tracker, predictions sent ahead, one per beat), the
          referee's on-beat score (beatref), energy bands, a heavy-hit detector, and chords from the AUDIO. --chords
          blend (the default): the older detector NAMES the audio chords (AudioChords: a 12-bin chroma from the
          spectrum's peaks, matched to major/minor/7th templates, sent only on a confident change), each decorated
          with its roman numeral and spelling in the key chordsense tells the page, while chordsense.ChordSense, fed
          every loopback block, sends the key and the tension (its own audio chords are not published). Measured
          2026-10-23 on a kick + sub bass + supersaw render: templates 59 % exact (root 59 %), chordsense 38 % (root
          61 %; the kick's sweep adds tones: F read Dm7, C read Cadd9); without drums chordsense led, 74 % to 68 %.
          --chords sense: chordsense names the audio chords too (chord with roman, key, bass and confidence; key;
          tension, through chordsense.to_vj_events). --chords basic: the templates only, no key or tension events
  HARMONY --chords blend and sense also run a second ChordSense on the KEYS (feed_notes, its clock stepped every 20 ms by the
          MIDI thread). The keys' chord NAME stays today's reading (Voicing + theory.analyze after the settle: exact
          on held piano chords and ~45 ms from the attack, where chordsense's notes path takes ~180 ms and reads
          85 % against 97 % on held block chords, measured 2026-10-23); when that reading cannot name what sounds (a
          held pedal note foreign to the chord, a sustain-pedal wash) the keys' chordsense chord is sent instead
          (78 % against 32 % with a re-struck pedal note). The key and the tension come from chordsense: from the keys
          while they have been played in the last 10 s, else from the audio; every chord's roman numeral is spelled
          in that key
  REPLAY  --replay-midi FILE plays a note list (JSON) or an FL project's pattern notes (.flp, read-only) as if
          played live, so the rig can be tried without the keyboard. A file that carries no tempo plays at 100 BPM
          and says so ('tempo unknown, assumed 100 BPM (--replay-bpm to set)'). replay_events() computes the same
          note and chord events offline, on a simulated clock

Threads: the audio loop never sleeps or waits on anything but its own source (the loopback's read is the clock);
publishing is a non-blocking put per client; HTTP, the MIDI dispatcher, the pad painter and the replay each run on
their own thread. The audio chordsense runs inline in the audio loop, a bounded step per block (any exception is
counted and said, never fatal to the beat, the energy or the hits); measured 2026-10-23 on a real-time synthesized
hardstyle replay at 48 kHz: 2400 of 2400 blocks read, capture timing gap +0.6 ms over 25.6 s, 0 late blocks, the
whole loop 0.87 ms a block (p99 2.8 ms) of which chordsense 0.28 ms (p99 0.88 ms), against a 10.7 ms block (the basic
chords: 0.67 ms, p99 2.4 ms). GET /api/state carries the same record live: audio.timing.capture (beatsync.capture_timing
of the blocks read) and audio.timing.proc_ms / sense_ms. LEDs: one LED-writing process only (do not run `beat`, `chordview` or `show` at the same time);
guest mode (no DAW connect) unless --connect and FL is not running; every packet passes the BurstGovernor.
The verb's stdout is line-buffered (core.foundation.streams), so a piped engine's console arrives as it happens.
"""
from __future__ import annotations

import importlib
import json
import math
import queue
import select
import socket
import struct
import subprocess
import sys
import threading
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

import numpy as np

from . import protocol as P
from .beatsync import IdleFill as _LoopbackIdleFill
from .chordview import Voicing
from .theory import analyze

HOST = "127.0.0.1"
DEFAULT_PORT = 8794
SRC = "keylab-vj"
CONTRACT_V = 1
HOP = 512                     # samples per audio block (the trackers' hop)
HEARTBEAT_S = 15.0
AHEAD_S = 0.25                # a beat is announced this long before it lands (the contract's 150-300 ms)
ENERGY_HZ = 40.0
CHORD_SETTLE_S = 0.03         # keys: a chord must hold this long before it is announced (a rolled chord = 1 event)
CHORD_SETTLE_MAX_S = 0.08     # ... but never wait longer than this from its first note
PAD_DEDUP_S = 0.04            # the same pad on both inputs within this long is one hit
SILENT_BEATS_S = 1.5          # no beats are announced after this long of silence
KEYS_WITNESS_S = 10.0         # the key: audio chords count as evidence only after the keys have been quiet this long
MAX_PADS_BODY = 4096
# --chords: blend (default) = the older audio templates NAME the audio chords (they hold up best under a hardstyle kick
# and sub bass, verified 2026-10-23) while chordsense on both ears gives the key, the roman numerals and the tension;
# sense = chordsense names the audio chords too; basic = the older templates only, no key or tension events.
CHORD_MODES = ("blend", "sense", "basic")
SENSE_TICK_S = 0.02           # the keys' chordsense clock is stepped at least this often (its frame is 20 ms)
TIMING_KEEP = 4096            # per-block processing times kept for the state route's percentiles

PC_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
_SHARP_TO_FLAT = {"C#": "Db", "D#": "Eb", "G#": "Ab", "A#": "Bb"}


def spell(name: str, flats: bool = False) -> str:
    """theory names chords with sharps ('C#maj7/G#'); the page shows the usual spelling ('Dbmaj7/Ab'). Pitch class 6
    stays F# unless the key has flats (flats=True): then it is Gb, the way the page's note names show it ('Gb/Db' in
    D-flat, not 'F#/Db')."""
    out = []
    for part in name.split("/"):
        head = part[:2]
        if head in _SHARP_TO_FLAT:
            part = _SHARP_TO_FLAT[head] + part[2:]
        elif head == "F#" and flats:
            part = "Gb" + part[2:]
        out.append(part)
    return "/".join(out)


def pc_name(pc: int, flats: bool = False) -> str:
    """One pitch class as the page spells it: flats, and Gb rather than F# when the key has flats."""
    return "Gb" if (pc % 12 == 6 and flats) else PC_NAMES[pc % 12]


# Krumhansl-Kessler key profiles, and each key's signature (+ sharps, - flats) by tonic pitch class. The two keys with
# six accidentals either way are taken on the flat side, Gb major and Eb minor, as the page spells every black key flat.
KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
MAJOR_SIG = (0, -5, 2, -3, 4, -1, -6, 1, -4, 3, -2, 5)     # C Db D Eb E F Gb G Ab A Bb B
MINOR_SIG = (-3, 4, -1, -6, 1, -4, 3, -2, 5, 0, -5, 2)     # Cm C#m Dm Ebm Em Fm F#m Gm G#m Am Bbm Bm


class KeyFinder:
    """The key of what has been played lately, for spelling chord names: note-ons (weighted by velocity) and
    confident audio chords go into a 12-bin pitch-class histogram that halves every half_life_s, correlated with the
    Krumhansl-Kessler major and minor profiles on all 12 tonics. key() is None until there is min_weight of evidence
    and the best correlation reaches min_r; flats() is True when that key's signature has flats. Thread-safe (the
    keys and the audio both feed it)."""

    def __init__(self, half_life_s: float = 20.0, min_weight: float = 4.0, min_r: float = 0.5):
        self.half_life_s, self.min_weight, self.min_r = half_life_s, min_weight, min_r
        self.h = np.zeros(12)
        self.t: Optional[float] = None
        self._lock = threading.Lock()
        prof = np.array([np.roll(KK_MAJOR, r) for r in range(12)] + [np.roll(KK_MINOR, r) for r in range(12)])
        prof = prof - prof.mean(axis=1, keepdims=True)
        self._prof = prof / np.linalg.norm(prof, axis=1, keepdims=True)

    def add(self, pcs, t: float, w: float = 1.0) -> None:
        with self._lock:
            if self.t is not None and t > self.t:
                self.h *= 0.5 ** ((t - self.t) / self.half_life_s)
            self.t = t if self.t is None else max(self.t, t)
            for pc in pcs:
                self.h[int(pc) % 12] += w

    def key(self) -> Optional[Tuple[int, str, int]]:
        """-> (tonic pitch class, 'major' or 'minor', its signature: + sharps, - flats), or None."""
        with self._lock:
            h = self.h.copy()
        if h.sum() < self.min_weight:
            return None
        hc = h - h.mean()
        n = float(np.linalg.norm(hc))
        if n <= 0:
            return None
        r = self._prof @ (hc / n)
        best = int(np.argmax(r))
        if r[best] < self.min_r:
            return None
        tonic, mode = best % 12, ("major" if best < 12 else "minor")
        return tonic, mode, (MAJOR_SIG if mode == "major" else MINOR_SIG)[tonic]

    def flats(self) -> bool:
        k = self.key()
        return k is not None and k[2] < 0

    def name(self) -> Optional[str]:
        k = self.key()
        return None if k is None else f"{pc_name(k[0], k[2] < 0)} {k[1]}"


def _quality(sym: Optional[str]) -> str:
    return "maj" if sym == "" else (sym or "")


# =====================================================================================================================
# the hub: fan-out to every page, never blocking the producer
# =====================================================================================================================
class Hub:
    """Each subscriber gets a bounded queue of ready-made SSE frames. A stalled page loses its OLDEST frames (counted),
    it never stalls the engine. taps are in-process listeners (tests, the console), called on the producer's thread."""

    def __init__(self, maxsize: int = 2048):
        self._lock = threading.Lock()
        self._clients: Dict[int, queue.Queue] = {}
        self._taps: List[Callable[[dict], None]] = []
        self._next = 0
        self.maxsize = maxsize
        self.counts: Dict[str, int] = {}
        self.dropped = 0
        self.closed = False

    @staticmethod
    def frame(evt: dict) -> bytes:
        return b"data: " + json.dumps(evt, separators=(",", ":")).encode("utf-8") + b"\n\n"

    def subscribe(self) -> Optional[Tuple[int, queue.Queue]]:
        """A new page's inbox, or None once the hub is closed: a stopped engine serves no new stream."""
        q: queue.Queue = queue.Queue(maxsize=self.maxsize)
        with self._lock:
            if self.closed:
                return None
            self._next += 1
            self._clients[self._next] = q
            return self._next, q

    def unsubscribe(self, token: int) -> None:
        with self._lock:
            self._clients.pop(token, None)

    def tap(self, fn: Callable[[dict], None]) -> None:
        with self._lock:
            self._taps.append(fn)

    @property
    def clients(self) -> int:
        with self._lock:
            return len(self._clients)

    def publish(self, evt: dict) -> None:
        data = self.frame(evt)
        with self._lock:
            self.counts[evt["t"]] = self.counts.get(evt["t"], 0) + 1
            clients = list(self._clients.values())
            taps = list(self._taps)
        for q in clients:
            self._put(q, data)
        for fn in taps:
            fn(evt)

    def _put(self, q: queue.Queue, data) -> None:
        try:
            q.put_nowait(data)
        except queue.Full:
            try:
                q.get_nowait()
            except queue.Empty:
                pass
            try:
                q.put_nowait(data)
            except queue.Full:
                pass
            self.dropped += 1

    def close(self) -> None:
        with self._lock:
            self.closed = True
            clients = list(self._clients.values())
        for q in clients:
            self._put(q, None)


# =====================================================================================================================
# controls: absolute or relative, learned on touch
# =====================================================================================================================
KNOB_CCS = (91, 92, 94, 95, 96, 97, 102, 103, 104)   # relative around 64 (Arturia's script; unconfirmed on hardware)
DIAL_CC, DIAL_CLICK_CC = 116, 117                     # dial: 65-72 clockwise, 55-63 counter-clockwise; click
FADER_CCS = tuple(range(105, 114))                    # faders 1-9, absolute
REL_STEP = 1.0 / 128                                  # one encoder tick moves a relative control's value this much
_PRIOR = 4                                            # how firmly the table's guess is held before touch evidence
_SCORE_CAP = 6


class CCDecoder:
    """Decodes every CC as absolute (value/127) or relative (offset around 64, accumulated into 0..1), and learns
    which on touch. Evidence, per message: a REPEATED value near 64 means a turning encoder (absolute controls send
    only on change: +2); a flip across 64 by 2 or more means an encoder turned back (+1); a value far from 64
    (outside 40..88) means an absolute control (-2). The score starts at the table's guess (+4 knob, -4 fader, 0
    unknown) and the kind is relative while it is above 0. Twos-complement encoders are not learned (Arturia's
    convention is offset-64)."""

    def __init__(self, known_rel=KNOB_CCS + (DIAL_CC,), known_abs=FADER_CCS + (DIAL_CLICK_CC,)):
        self.known_rel, self.known_abs = set(known_rel), set(known_abs)
        self._st: Dict[str, dict] = {}

    def kind_of(self, key: str) -> Optional[str]:
        st = self._st.get(key)
        return st["kind"] if st else None

    def feed(self, key: str, cc: int, value: int, t: float) -> Tuple[dict, Optional[str]]:
        """-> ({"kind","value","delta"}, a 'learned' note or None)."""
        st = self._st.get(key)
        if st is None:
            prior = _PRIOR if cc in self.known_rel else (-_PRIOR if cc in self.known_abs else 0)
            st = {"score": prior, "last": None, "t": -1e9, "pos": 0.5, "kind": None, "known": prior != 0}
            self._st[key] = st
        lv, far = st["last"], abs(value - 64)
        ev = 0
        if far > 24:
            ev -= 2
        if lv is not None and t - st["t"] < 1.0:
            if value == lv and 0 < far <= 16:
                ev += 2
            elif far <= 16 and abs(lv - 64) <= 16 and (value - 64) * (lv - 64) < 0 and abs(value - lv) >= 2:
                ev += 1
        st["score"] = max(-_SCORE_CAP, min(_SCORE_CAP, st["score"] + ev))
        kind = "rel" if st["score"] > 0 else "abs"
        if kind == "rel":
            delta = value - 64
            st["pos"] = min(1.0, max(0.0, st["pos"] + delta * REL_STEP))
            val = st["pos"]
        else:
            delta = 0 if lv is None else value - lv
            val = value / 127.0
            st["pos"] = val
        note = None
        if kind != st["kind"]:
            if st["kind"] is not None or not st["known"]:
                note = f"{key} learned as {'relative (around 64)' if kind == 'rel' else 'absolute'}"
            st["kind"] = kind
        st["last"], st["t"] = value, t
        return {"kind": kind, "value": round(float(val), 4), "delta": int(delta)}, note


# =====================================================================================================================
# audio: energy, hits, chords (the beat lives in BeatClock)
# =====================================================================================================================
ENERGY_BANDS = (("bass", 20.0, 150.0), ("mid", 150.0, 2000.0), ("high", 2000.0, 16000.0))
HIT_BANDS = ((30.0, 150.0), (150.0, 5000.0), (5000.0, 16000.0))      # kick, snare, hat
HIT_WEIGHTS = np.array([1.0, 0.8, 0.5])
GAIN_MIN_RANGE_DB = 12.0      # auto-gain: each band maps its recent floor..peak to 0..1, at least this many dB wide
GAIN_FLOOR_DB = -50.0         # a band whose recent peak is quieter than this (dB re full-scale sine) stays dim
GAIN_RELEASE_DB_S = 3.0       # how fast the remembered peak falls
GAIN_RISE_DB_S = 2.0          # how fast the remembered floor rises (it drops at once)
SILENCE_DB = -65.0            # block level below this is silence
ENERGY_RELEASE_S = 0.10       # attack is instant, release is this time constant
HIT_MIN_GAP_S = 0.10
HIT_SAFE_GAP_S = 0.34         # --rate-limit: at most 3 hits in any second (the flash-safety ceiling)
HIT_REL = 0.6                 # a hit must reach this share of the recent strongest onset ...
HIT_MAD = 3.0                 # ... and stand this many robust deviations above the recent median


def _db(p: float) -> float:
    return 10.0 * math.log10(p + 1e-12)


class Analyzer:
    """Per audio block: energy (40 Hz), heavy hits (immediately) and the audio chord (on a confident change).
    feed(block, audio_t) -> events. Pure numpy, causal, no wall clock (so it is pinned offline). chords=False leaves
    the chord to chordsense (Harmony, --chords sense): no AudioChords runs at all."""

    def __init__(self, rate: int, hop: int = HOP, rate_limit: bool = False, energy_hz: float = ENERGY_HZ,
                 chords: bool = True):
        self.rate, self.hop = int(rate), int(hop)
        self.n = 2048 if rate > 32000 else 1024
        self.win = np.hanning(self.n).astype(np.float32)
        self.ring = np.zeros(self.n, dtype=np.float32)
        f = np.fft.rfftfreq(self.n, 1.0 / rate)
        self.ebands = [(name, np.where((f >= lo) & (f < hi))[0]) for name, lo, hi in ENERGY_BANDS]
        self.hbands = [np.where((f >= lo) & (f < hi))[0] for lo, hi in HIT_BANDS]
        self.ref = self.n * float(np.sum(self.win.astype(np.float64) ** 2)) / 4.0   # full-scale sine -> 0 dB
        self.dt = hop / float(rate)
        self.peak = {k: GAIN_FLOOR_DB for k in ("bass", "mid", "high", "level")}
        self.floor = {k: GAIN_FLOOR_DB - GAIN_MIN_RANGE_DB for k in ("bass", "mid", "high", "level")}
        self.out = {k: 0.0 for k in ("bass", "mid", "high", "level")}
        self.rel = math.exp(-self.dt / ENERGY_RELEASE_S)
        self.energy_every = 1.0 / energy_hz
        self.next_energy = 0.0
        self.level_db = -120.0
        self.silent_since: Optional[float] = 0.0
        # hits
        self.prev_log = None
        self.hist: deque = deque(maxlen=max(20, int(1.5 * rate / hop)))
        self.cand: deque = deque(maxlen=3)
        self.band_cand: deque = deque(maxlen=3)
        self.hpk = 1e-6
        self.hpk_decay = math.exp(-self.dt / 3.0)
        self.last_hit = -1e9
        self.hit_gap = HIT_SAFE_GAP_S if rate_limit else HIT_MIN_GAP_S
        self.chords = AudioChords(rate, hop) if chords else None

    def silent_for(self, now: float) -> float:
        return 0.0 if self.silent_since is None else max(0.0, now - self.silent_since)

    def feed(self, block: np.ndarray, audio_t: float) -> List[dict]:
        x = np.asarray(block, dtype=np.float32).reshape(-1)
        self.ring = np.roll(self.ring, -len(x))
        self.ring[-len(x):] = x[-self.n:]
        mag = np.abs(np.fft.rfft(self.ring * self.win))
        rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) if len(x) else 0.0
        self.level_db = 20.0 * math.log10(rms + 1e-9) + 3.0103
        silent = self.level_db < SILENCE_DB
        if silent:
            if self.silent_since is None:
                self.silent_since = audio_t
        else:
            self.silent_since = None
        out: List[dict] = []
        e = self._energy(mag, silent, audio_t)
        if e:
            out.append(e)
        h = self._hit(mag, silent, audio_t)
        if h:
            out.append(h)
        if self.chords is not None:
            c = self.chords.feed(x, audio_t, silent=silent)
            if c:
                out.append(c)
        return out

    def _energy(self, mag, silent: bool, audio_t: float) -> Optional[dict]:
        pw = mag.astype(np.float64) ** 2
        raw = {name: _db(float(pw[idx].sum()) / self.ref) for name, idx in self.ebands}
        raw["level"] = self.level_db
        for k, db in raw.items():
            if not silent:
                self.peak[k] = max(db, self.peak[k] - GAIN_RELEASE_DB_S * self.dt, GAIN_FLOOR_DB)
                self.floor[k] = min(db, self.floor[k] + GAIN_RISE_DB_S * self.dt)
            span = max(self.peak[k] - self.floor[k], GAIN_MIN_RANGE_DB)
            v = 0.0 if silent else min(1.0, max(0.0, (db - (self.peak[k] - span)) / span))
            self.out[k] = v if v >= self.out[k] else v + (self.out[k] - v) * self.rel
            if self.out[k] < 0.004:
                self.out[k] = 0.0                     # a fade ends dark, not at 0.001 forever
        if audio_t + 1e-9 < self.next_energy:
            return None
        self.next_energy = max(self.next_energy + self.energy_every, audio_t)
        return {"t": "energy", **{k: round(float(self.out[k]), 3) for k in ("bass", "mid", "high", "level")}}

    def _hit(self, mag, silent: bool, audio_t: float) -> Optional[dict]:
        logm = np.log1p(100.0 * mag)
        if self.prev_log is None:
            self.prev_log = logm
            return None
        flux = np.maximum(logm - self.prev_log, 0.0)
        self.prev_log = logm
        fb = np.array([float(flux[b].mean()) if len(b) else 0.0 for b in self.hbands])
        contrib = HIT_WEIGHTS * fb
        total = float(contrib.sum())
        self.hist.append(total)
        self.hpk = max(total, self.hpk * self.hpk_decay, 1e-6)
        self.cand.append(total)
        self.band_cand.append(contrib)
        if silent or len(self.cand) < 3 or len(self.hist) < 20:
            return None
        a, b, c = self.cand
        if not (b > a and b >= c):
            return None
        h = np.asarray(self.hist, dtype=np.float64)
        med = float(np.median(h))
        mad = 1.4826 * float(np.median(np.abs(h - med))) + 1e-9
        if b < med + HIT_MAD * mad or b < HIT_REL * self.hpk:
            return None
        t_hit = audio_t - self.dt                      # the peak was one block ago
        if t_hit - self.last_hit < self.hit_gap:
            return None
        self.last_hit = t_hit
        share = self.band_cand[1] / (float(self.band_cand[1].sum()) + 1e-12)
        i = int(np.argmax(share))
        band = ("kick", "snare", "hat")[i] if share[i] >= 0.55 else "full"
        return {"t": "hit", "strength": round(min(1.0, b / self.hpk), 3), "band": band}


CHORD_QUALITIES = (("maj", (0, 4, 7)), ("m", (0, 3, 7)), ("7", (0, 4, 7, 10)), ("maj7", (0, 4, 7, 11)),
                   ("m7", (0, 3, 7, 10)))
SEVENTH_PENALTY = 0.03        # a 4-note template must beat its triad by this much (a passing note is not a 7th)
CHROMA_LO_HZ, CHROMA_HI_HZ = 80.0, 2500.0


class AudioChords:
    """Chords from the AUDIO: every ~50 ms, the spectrum's peaks (80-2500 Hz, parabolic-interpolated, tilted toward
    the fundamentals) are folded into 12 pitch classes; the chroma is smoothed (tau 0.2 s) and matched (cosine) to
    major, minor, dominant-7, maj7 and m7 templates on all 12 roots. A chord is announced only when the same
    template has been best for hold_s, scores at least min_score, beats its best RIVAL (a chord neither inside it
    nor containing it) by min_margin, the chroma is
    tonal (peaky, not flat like noise or drums), and it differs from the chord last announced (a 7th coming and
    going over the same root, Em <-> Em7, is colour, not a change, and is not announced). After release_s with
    no confident chord the memory clears, so the same chord coming back is a change again."""

    def __init__(self, rate: int, hop: int = HOP, every_s: float = 0.05, tau_s: float = 0.2, hold_s: float = 0.2,
                 min_score: float = 0.82, min_margin: float = 0.03, min_peakiness: float = 2.0,
                 release_s: float = 2.0):
        self.rate, self.hop = int(rate), int(hop)
        self.n = 8192 if rate > 32000 else 4096
        self.win = np.hanning(self.n).astype(np.float32)
        self.ring = np.zeros(self.n, dtype=np.float32)
        self.filled = 0
        self.every = max(1, int(round(every_s * rate / hop)))
        self.alpha = 1.0 - math.exp(-every_s / tau_s)
        self.hold_s, self.min_score, self.min_margin = hold_s, min_score, min_margin
        self.min_peakiness, self.release_s = min_peakiness, release_s
        f = np.fft.rfftfreq(self.n, 1.0 / rate)
        self.lo = max(2, int(np.searchsorted(f, CHROMA_LO_HZ)))
        self.hi = min(len(f) - 2, int(np.searchsorted(f, CHROMA_HI_HZ)))
        self.freqs = f
        rows, labels = [], []
        for q, ivs in CHORD_QUALITIES:
            for root in range(12):
                v = np.zeros(12)
                v[[(root + i) % 12 for i in ivs]] = 1.0
                rows.append(v / np.linalg.norm(v))
                labels.append((root, q, tuple(sorted((root + i) % 12 for i in ivs))))
        self.T = np.array(rows)
        self.penalty = np.array([SEVENTH_PENALTY if len(l[2]) == 4 else 0.0 for l in labels])
        self.labels = labels
        self.smooth = np.zeros(12)
        self.k = 0
        self.cand: Optional[int] = None
        self.cand_since = 0.0
        self.current: Optional[int] = None
        self.last_confident = -1e9
        self.last = None              # the last analysis, for the state route and tuning

    def chroma(self) -> np.ndarray:
        mag = np.abs(np.fft.rfft(self.ring * self.win))
        k = np.arange(self.lo, self.hi + 1)
        m0, m1, m2 = mag[k - 1], mag[k], mag[k + 1]
        top = float(m1.max()) if len(m1) else 0.0
        c = np.zeros(12)
        if top <= 0:
            return c
        pk = (m1 > m0) & (m1 >= m2) & (m1 > 0.02 * top)
        if not pk.any():
            return c
        k, a, b, cc = k[pk], np.log(m0[pk] + 1e-12), np.log(m1[pk] + 1e-12), np.log(m2[pk] + 1e-12)
        den = a - 2 * b + cc
        p = np.where(np.abs(den) > 1e-12, 0.5 * (a - cc) / np.where(np.abs(den) > 1e-12, den, 1.0), 0.0)
        p = np.clip(p, -0.5, 0.5)
        fr = (k + p) * self.rate / self.n
        midi = 69.0 + 12.0 * np.log2(fr / 440.0)
        r = np.round(midi)
        dev = midi - r
        w = m1[pk] * np.cos(np.pi * dev) ** 2 / (1.0 + (fr / 1200.0) ** 2)
        np.add.at(c, (r.astype(int) % 12), w)
        return c

    def feed(self, block: np.ndarray, audio_t: float, silent: bool = False) -> Optional[dict]:
        x = np.asarray(block, dtype=np.float32).reshape(-1)
        self.ring = np.roll(self.ring, -len(x))
        self.ring[-len(x):] = x[-self.n:]
        self.filled += len(x)
        self.k += 1
        if self.k % self.every:
            return None
        if self.current is not None and audio_t - self.last_confident > self.release_s:
            self.current = None
        if silent or self.filled < self.n // 2:
            self.smooth *= (1.0 - self.alpha)
            self.cand = None
            return None
        c = self.chroma()
        nrm = float(np.linalg.norm(c))
        if nrm <= 0:
            self.cand = None
            return None
        self.smooth = (1.0 - self.alpha) * self.smooth + self.alpha * (c / nrm)
        s = self.smooth
        sn = float(np.linalg.norm(s))
        if sn <= 0:
            return None
        scores = self.T @ (s / sn) - self.penalty
        order = np.argsort(scores)[::-1]
        best = int(order[0])
        bset = set(self.labels[best][2])
        # the runner-up that matters is a RIVAL: a chord that is neither inside the winner nor contains it (G vs G7
        # is settled by the 7th's penalty; G7 vs Em is a real ambiguity)
        rival = next((int(j) for j in order[1:] if not (set(self.labels[j][2]) <= bset or
                                                      bset <= set(self.labels[j][2]))), int(order[1]))
        score, margin = float(scores[best]), float(scores[best] - scores[rival])
        peaky = float(s.max() / (s.mean() + 1e-12))
        self.last = {"best": self.labels[best], "score": round(score, 3), "margin": round(margin, 3),
                     "peakiness": round(peaky, 2)}
        confident = score >= self.min_score and margin >= self.min_margin and peaky >= self.min_peakiness
        if not confident:
            self.cand = None
            return None
        if best != self.cand:
            self.cand, self.cand_since = best, audio_t
        self.last_confident = audio_t
        if audio_t - self.cand_since + 1e-9 < self.hold_s or best == self.current:
            return None
        if self.current is not None:
            cr, _q, cp = self.labels[self.current]
            if cr == self.labels[best][0] and (set(cp) <= bset or bset <= set(cp)):
                return None               # a 7th coming and going on the same root is colour, not a change
        self.current = best
        root, q, pcs = self.labels[best]
        return {"t": "chord", "src": "audio", "name": PC_NAMES[root] + ("" if q == "maj" else q), "root": root,
                "quality": q, "pcs": list(pcs), "changed": True, "conf": round(score, 3)}


# =====================================================================================================================
# harmony: chordsense on both ears (--chords sense)
# =====================================================================================================================
_KEY_PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
           "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
# a chord quality as the page spells it (theory's and chordsense's VJ spellings) -> the one chordsense's roman() reads;
# the chords chordsense has no template for read as the nearest it has (a 9 as its 7, a 6 or madd9 as its triad, a
# dim7 or a half-diminished 7th as diminished), so their numeral carries the degree and the family, not the extension
_ROMAN_QUALITY = {"maj": "maj", "m": "min", "min": "min", "7": "7", "maj7": "maj7", "m7": "m7", "sus2": "sus2",
                  "sus4": "sus4", "dim": "dim", "aug": "aug", "add9": "add9", "5": "5", "6": "maj", "m6": "min",
                  "madd9": "min", "dim7": "dim", "m7b5": "dim", "7sus4": "sus4", "9": "7", "maj9": "maj7", "m9": "m7"}


def parse_key(name) -> Optional[Tuple[int, str]]:
    """'Db major' / 'F# minor' (the key event's name) -> (tonic pitch class, 'major' | 'minor'), or None."""
    if not isinstance(name, str):
        return None
    parts = name.split()
    if len(parts) != 2 or parts[0] not in _KEY_PC or parts[1] not in ("major", "minor"):
        return None
    return _KEY_PC[parts[0]], parts[1]


def key_has_flats(name) -> Optional[bool]:
    """True when the key's signature has flats (Gb major and Eb minor count as flat keys), None for no key."""
    k = parse_key(name)
    if k is None:
        return None
    return (MAJOR_SIG if k[1] == "major" else MINOR_SIG)[k[0]] < 0


_PC_OF = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6,
          "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11, "Cb": 11, "B#": 0}


def _root_token(s: str) -> str:
    return s[:2] if len(s) > 1 and s[1] in "#b" else s[:1]


def spell_in_key(name, root, quality, key) -> Optional[str]:
    """A chord name re-spelled for a key by scale degree (chordsense.spell_root / spell_note): the root and any slash
    bass change letter, the suffix is kept as written. In E major the iii chord is G#m, not Abm; in C major the
    borrowed bVII is Bb, not A#. None with no key, no root, or a name whose root is not the event's root (then the
    caller keeps its own spelling)."""
    k = parse_key(key)
    if k is None or root is None or not isinstance(name, str) or not name or name == "N":
        return None
    try:
        from . import chordsense as CS
        head, _, slash = name.partition("/")
        r = _root_token(head)
        if _PC_OF.get(r) != int(root) % 12:
            return None
        out = CS.spell_root(int(root) % 12, _ROMAN_QUALITY.get(quality), k)[0] + head[len(r):]
        if slash:
            b = _root_token(slash)
            if b not in _PC_OF:
                return None
            out += "/" + CS.spell_note(_PC_OF[b], k) + slash[len(b):]
        return out
    except Exception:                                 # a chordsense that changed under us keeps the old spelling
        return None


def roman_in(root, quality, bass, key) -> Optional[str]:
    """The roman numeral of a chord in a key ('IV', 'V65', 'bVII', 'V7/V'), spelled by chordsense's own reading
    (chordsense.roman + full_roman), or None with no key or a chord it cannot place."""
    k = parse_key(key)
    q = _ROMAN_QUALITY.get(quality)
    if k is None or q is None or root is None:
        return None
    try:
        from . import chordsense as CS
        num, fig, _function = CS.roman(int(root) % 12, q, None if bass is None else int(bass) % 12, k[0], k[1])
        return CS.full_roman(num, fig)
    except Exception:                                 # a chordsense that changed under us names no numeral, never fails
        return None


class Harmony:
    """chordsense on both ears, merged into the page's events (--chords sense).

    audio: a ChordSense fed every block the audio loop reads (feed_audio, on the audio thread). keys: a second one fed
    the played notes and the sustain pedal (note, tick: on the MIDI thread; tick steps its clock while nothing is
    played). Each ear's events go through chordsense.to_vj_events. Then, under one lock:
      key      the page is told ONE key: the keys' while they have been played in the last witness_s seconds (what
               Daniel plays outranks what the speakers are estimated to play), else the audio's; either one when the
               other has none. A key event goes out when that key moves, also when it moves because the witness changed.
      tension  from the same ear (the keys while they are the witness, else the audio); a change of ear sends the new
               ear's latest value, so the page's tension is never a mix of two ears.
      chords   audio chords are published as they come (decorate: the name spelled for the page, the roman numeral
               in the key the page is told). Keys chords are RETURNED (t 'chord', src 'keys') for the engine, which
               publishes them only while its own keys reading cannot name what sounds (Engine._sense_keys).
    Every call is bounded: one block, or the 20 ms frames since the last tick."""

    def __init__(self, rate: Optional[int] = None, hop: int = HOP, witness_s: float = KEYS_WITNESS_S):
        from . import chordsense as CS
        self._CS = CS
        self.audio = CS.ChordSense(int(rate), int(hop)) if rate else None
        self.keys = CS.ChordSense()
        self.witness_s = witness_s
        self._lock = threading.Lock()
        self._key: Dict[str, Optional[Tuple[str, float]]] = {"audio": None, "keys": None}
        self._tension: Dict[str, Optional[dict]] = {"audio": None, "keys": None}
        self._struck = -math.inf          # when a key was last struck (the clock the notes come on)
        self._kt: Optional[float] = None  # the keys' chordsense clock: the latest time handed to it
        self.key_shown: Optional[dict] = None       # the key event the page was last told
        self.tension_shown: Optional[dict] = None   # ... and the tension event
        self._tension_src: Optional[str] = None
        self.counts = {"audio_blocks": 0, "keys_ticks": 0, "key_events": 0, "tension_events": 0}

    # ---- the ears
    def feed_audio(self, block, now: float) -> List[dict]:
        """One audio block (mono or (n, channels) float) -> the page events it decided (chord, key, tension)."""
        evs = self.audio.feed(block)
        self.counts["audio_blocks"] += 1
        return self._take("audio", evs, now) if evs else self.refresh(now)

    def note(self, ev: dict, t: float) -> List[dict]:
        """One played event for the keys ear: {"note", "vel"} (vel 0 = off) or {"sustain": 0..127}, at time t."""
        t = t if self._kt is None else max(t, self._kt)
        self._kt = t
        if ev.get("vel", 0) > 0 and "note" in ev:
            with self._lock:
                self._struck = t
        return self._take("keys", self.keys.feed_notes([{**ev, "t": t}]), t)

    def tick(self, now: float) -> List[dict]:
        """Let the keys' clock reach `now` (chords decided while notes ring, the key, the tension relaxing)."""
        now = now if self._kt is None else max(now, self._kt)
        self._kt = now
        self.counts["keys_ticks"] += 1
        return self._take("keys", self.keys.feed_notes([], now=now), now)

    # ---- merging
    def _keys_witness(self, now: float) -> bool:
        return now - self._struck <= self.witness_s

    def key_now(self, now: Optional[float] = None) -> Optional[Tuple[str, float, str]]:
        """(name, conf, ear) of the key the page should be told now, or None."""
        with self._lock:
            return self._key_now(self._kt if now is None else now)

    def _key_now(self, now) -> Optional[Tuple[str, float, str]]:
        order = ("keys", "audio") if (now is not None and self._keys_witness(now)) else ("audio", "keys")
        for ear in order:
            k = self._key[ear]
            if k is not None:
                return k[0], k[1], ear
        return None

    def _tension_ear(self, now) -> str:
        if self.audio is None:
            return "keys"
        return "keys" if (now is not None and self._keys_witness(now)) else "audio"

    def refresh(self, now: float) -> List[dict]:
        """The key / tension the page should have now, as events when they differ from what it was last told."""
        out: List[dict] = []
        with self._lock:
            k = self._key_now(now)
            if k is not None and (self.key_shown is None or self.key_shown["name"] != k[0]):
                self.key_shown = {"t": "key", "name": k[0], "conf": k[1], "src": k[2]}
                self.counts["key_events"] += 1
                out.append(dict(self.key_shown))
            ear = self._tension_ear(now)
            if ear != self._tension_src:
                self._tension_src = ear
                tv = self._tension[ear]
                if tv is not None and tv != self.tension_shown:
                    self.tension_shown = tv
                    self.counts["tension_events"] += 1
                    out.append(dict(tv))
        return out

    def _take(self, ear: str, events: List[dict], now: float) -> List[dict]:
        """One call's chordsense events -> page events. Keys are taken first and announced first (refresh), so a
        chord decided in the same frame as a modulation reaches the page after the key it is spelled in."""
        vj: List[dict] = []
        for e in events:
            vj += self._CS.to_vj_events(e, src=ear)
        with self._lock:
            for v in vj:
                if v.get("t") == "key" and v.get("name"):
                    self._key[ear] = (v["name"], float(v.get("conf") or 0.0))
        out = self.refresh(now)
        for v in vj:
            kind = v.get("t")
            if kind == "tension":
                tv = {"t": "tension", "value": round(min(1.0, max(0.0, float(v.get("value") or 0.0))), 3),
                      "pedal_pc": v.get("pedal_pc"), "src": ear}
                with self._lock:
                    self._tension[ear] = tv
                    if ear == self._tension_ear(now):
                        self._tension_src = ear
                        self.tension_shown = tv
                        self.counts["tension_events"] += 1
                        out.append(dict(tv))
            elif kind == "chord":
                out.append(v)                       # decorated by the engine, in the key refresh() just settled
        return out

    def decorate(self, chord: dict, now: Optional[float] = None, fallback_flats: bool = False) -> dict:
        """A chord event for the page: its roman numeral in the key the page is told (recomputed when the ear that
        named the chord heard another key), that key, and the name spelled by the key's scale degrees (spell_in_key:
        G#m in E major, Bb in C major), else the page's way (flats; pitch class 6 is Gb in a flat key). A chord with no
        root (N) carries no numeral."""
        k = self.key_now(now)
        key = k[0] if k else None
        out = dict(chord)
        if out.get("root") is None:
            out["roman"] = None
        elif key != chord.get("key") or "roman" not in chord:
            out["roman"] = roman_in(out["root"], out.get("quality"), out.get("bass"), key)
        out["key"] = key
        flats = key_has_flats(key)
        named = spell_in_key(out.get("name"), out.get("root"), out.get("quality"), key)
        if named:
            out["name"] = named
        elif out.get("name") and out["name"] != "N":
            out["name"] = spell(out["name"], fallback_flats if flats is None else flats)
        return out

    def snapshot(self) -> dict:
        """For the state route: each ear's key and tension, and what the page was last told."""
        with self._lock:
            return {"key": self.key_shown["name"] if self.key_shown else None,
                    "key_src": self.key_shown["src"] if self.key_shown else None,
                    "tension": self.tension_shown["value"] if self.tension_shown else None,
                    "tension_src": self._tension_src,
                    "ears": {ear: {"key": None if self._key[ear] is None else self._key[ear][0],
                                   "tension": None if self._tension[ear] is None else self._tension[ear]["value"]}
                             for ear in ("audio", "keys")},
                    **self.counts}


class BeatClock:
    """The beat tracker plus the referee, turned into one announcement per beat. feed(block) -> None, or a beat due
    now: {"lead_s", "bpm", "conf", "n", "on_beat"} where lead_s is how far ahead (audio time) the beat lands.
    A beat is announced the first time the next predicted beat is within ahead_s; a revised prediction of a beat
    already announced (closer than half a period to it) is never announced twice."""

    def __init__(self, rate: int, hop: int = HOP, engine: str = "a", seed_bpm: Optional[float] = None,
                 ahead_s: float = AHEAD_S, referee: bool = True):
        Tracker = importlib.import_module(f"{__package__}.beat_{engine}").Tracker
        self.tracker = Tracker(rate, hop, seed_bpm=seed_bpm)
        self.ref = None
        if referee:
            from .beatref import Referee
            self.ref = Referee(rate, hop)
        self.rate, self.hop, self.ahead_s = int(rate), int(hop), ahead_s
        self.audio_t = 0.0
        self.last_sent: Optional[float] = None
        self.n = 0
        self.on_beat: Optional[float] = None
        self.next_verdict = 2.0
        self.bpm: Optional[float] = None
        self.conf = 0.0

    def feed(self, block: np.ndarray) -> Optional[dict]:
        self.tracker.feed(block)
        self.audio_t += len(block) / self.rate
        ahead = self.tracker.predict(self.audio_t) or []
        if self.ref is not None:
            self.ref.predicted(ahead)
            self.ref.feed(block)
            if self.audio_t >= self.next_verdict:
                self.next_verdict = self.audio_t + 2.0
                v = self.ref.verdict()
                self.on_beat = (round(min(1.0, max(0.0, float(v["on_beat"]))), 3)
                                if v.get("state") == "ok" else None)
        if not ahead:
            return None
        nb = ahead[0]
        t_beat, bpm = float(nb["t_beat"]), float(nb["bpm"])
        self.bpm, self.conf = bpm, float(nb.get("confidence") or 0.0)
        period = 60.0 / bpm
        lead = t_beat - self.audio_t
        if lead > self.ahead_s or lead < -0.03:
            return None
        if self.last_sent is not None and t_beat - self.last_sent < 0.5 * period:
            return None
        self.last_sent = t_beat
        self.n += 1
        return {"lead_s": lead, "bpm": bpm, "conf": self.conf, "n": self.n, "on_beat": self.on_beat}


# =====================================================================================================================
# audio sources: read() -> one mono float32 block of HOP samples (None = ended); read() is the only wait
# =====================================================================================================================
class LoopbackSource:
    """What is playing out of the speakers (WASAPI loopback via pyaudiowpatch, as beatsync opens it)."""

    def __init__(self):
        import pyaudiowpatch as pa
        from .beatsync import _open_loopback
        self.inst, dev = _open_loopback(pa)
        self.rate = int(dev["defaultSampleRate"])
        self.ch = int(dev["maxInputChannels"]) or 2
        self.name = f"loopback: {dev['name']} @ {self.rate} Hz"
        self.stream = self.inst.open(format=pa.paFloat32, channels=self.ch, rate=self.rate, input=True,
                                     input_device_index=dev["index"], frames_per_buffer=HOP)

    def read(self) -> Optional[np.ndarray]:
        raw = self.stream.read(HOP, exception_on_overflow=False)
        x = np.frombuffer(raw, dtype=np.float32)
        if self.ch > 1:
            x = x.reshape(-1, self.ch).mean(axis=1)
        return np.ascontiguousarray(x, dtype=np.float32)

    def close(self) -> None:
        try:
            self.stream.stop_stream(); self.stream.close(); self.inst.terminate()
        except Exception:
            pass


class IdleFill(_LoopbackIdleFill):
    """Wraps a device whose read() BLOCKS while nothing plays (the WASAPI loopback delivers nothing in silence --
    measured 2026-10-23: a 3 s read on an idle Focusrite never returned): beatsync.IdleFill, the one reader every
    loopback user shares ('beat' and 'record' hung the same way). read() hands over the device's blocks, or silence in
    real time once the device has been quiet for grace_s, so the analysis clock keeps running through a pause (energy
    fades, beats stop, the chord memory releases); a backlog past max_backlog_s is dropped and counted (dropped_s)."""


class _Paced:
    """Real-time pacing for a source that is not a device: block k is handed over when it would have finished
    playing. The wait is the stand-in for a device's blocking read."""

    def _pace(self, k: int) -> None:
        if not self.realtime:
            return
        now = time.perf_counter()
        if self._t0 is None:
            self._t0 = now
        wait = self._t0 + k * HOP / self.rate - now
        if wait > 0:
            time.sleep(wait)


class FileSource(_Paced):
    """An audio file played in real time (soundfile: wav, flac, ogg, mp3), mixed to mono, read block by block."""

    def __init__(self, path, realtime: bool = True, loop: bool = False):
        import soundfile as sf
        self.f = sf.SoundFile(str(path))
        self.rate = int(self.f.samplerate)
        self.realtime, self.loop = realtime, loop
        self.name = f"file: {Path(path).name} @ {self.rate} Hz"
        self._t0 = None
        self.k = 0

    def read(self) -> Optional[np.ndarray]:
        data = self.f.read(HOP, dtype="float32", always_2d=True)
        if len(data) == 0 and self.loop:
            self.f.seek(0)
            data = self.f.read(HOP, dtype="float32", always_2d=True)
        if len(data) == 0:
            return None
        x = data.mean(axis=1)
        if len(x) < HOP:
            x = np.concatenate([x, np.zeros(HOP - len(x), dtype=np.float32)])
        self.k += 1
        self._pace(self.k)
        return np.ascontiguousarray(x, dtype=np.float32)

    def close(self) -> None:
        try:
            self.f.close()
        except Exception:
            pass


def _voicing(name: str) -> List[int]:
    pcs, root = P.chord_pitchclasses(name)
    return [48 + root] + sorted(60 + root + ((pc - root) % 12) for pc in pcs)


def _partials(midis, t, amp=0.08, partials=(1.0, 0.5, 0.3, 0.2)) -> np.ndarray:
    x = np.zeros_like(t)
    for m in midis:
        f0 = 440.0 * 2 ** ((m - 69) / 12.0)
        for h, a in enumerate(partials, start=1):
            x += amp * a * np.sin(2 * np.pi * f0 * h * t)
    return x


class SynthSource(_Paced):
    """A made-up groove for trying a page with no music playing (--replay-audio demo): a kick on every beat, a snare
    on 2 and 4, a hat on the off-beats, and a sustained chord that changes every bar. realtime=False runs flat out."""

    def __init__(self, rate: int = 48000, bpm: float = 120.0, chords=("C", "Am", "F", "G"), beats_per_chord: int = 4,
                 realtime: bool = True, seconds: Optional[float] = None, drums: bool = True, level: float = 0.6,
                 seed: int = 1):
        self.rate, self.bpm, self.realtime, self.seconds = int(rate), float(bpm), realtime, seconds
        self.period = 60.0 / self.bpm
        self.chords = [_voicing(c) for c in chords]
        self.chord_names = list(chords)
        self.bar = beats_per_chord * self.period
        self.drums, self.level = drums, level
        self.rng = np.random.default_rng(seed)
        self.name = f"demo groove: {self.bpm:g} BPM, {' '.join(chords)}"
        self._t0 = None
        self.k = 0

    def read(self) -> Optional[np.ndarray]:
        if self.seconds is not None and self.k * HOP / self.rate >= self.seconds:
            return None
        t = (self.k * HOP + np.arange(HOP)) / self.rate
        self.k += 1
        ci = np.floor(t / self.bar).astype(int)
        x = np.zeros(HOP)
        for c in np.unique(ci):
            sel = ci == c
            since = t[sel] - c * self.bar
            x[sel] = _partials(self.chords[c % len(self.chords)], t[sel]) * np.clip(since / 0.005, 0, 1)
        if self.drums:
            b = np.floor(t / self.period)
            dt = t - b * self.period
            x += 0.9 * np.sin(2 * np.pi * (45.0 * dt + 90.0 * 0.04 * (1 - np.exp(-dt / 0.04)))) * np.exp(-dt / 0.15)
            noise = self.rng.standard_normal(HOP)
            snare = (b.astype(int) % 2 == 1)
            x += snare * (0.3 * noise * np.exp(-dt / 0.08) + 0.2 * np.sin(2 * np.pi * 180 * dt) * np.exp(-dt / 0.05))
            dh = dt - self.period / 2
            hp = np.diff(noise, prepend=0.0)
            x += (dh >= 0) * 0.12 * hp * np.exp(-np.maximum(dh, 0) / 0.025)
        self._pace(self.k)
        return (self.level * x).astype(np.float32)

    def close(self) -> None:
        pass


# =====================================================================================================================
# MIDI replay: a note list or an FL project's pattern notes, played as if live
# =====================================================================================================================
DEFAULT_REPLAY_BPM = 100.0
STRETCH_GAP_BEATS = 8.0


def _varint(b: bytes, i: int) -> Tuple[int, int]:
    n = shift = 0
    while True:
        c = b[i]
        i += 1
        n |= (c & 0x7F) << shift
        shift += 7
        if not c & 0x80:
            return n, i


def read_flp(path) -> dict:
    """Read-only FL Studio project reader: pattern notes. Clean-room from the published event layout: an event id
    < 64 carries 1 byte, < 128 two, < 192 four, else a varint length and data; 65 = new pattern, 193 = pattern name
    (UTF-16), 156 = tempo x 1000, 224 = the pattern's notes as 24-byte records <IHHIHHBBBBBBBB (pos, flags, channel,
    length, key, group, fine pitch, -, release, MIDI channel, pan, velocity, mod x, mod y). PPQ from the FLhd
    header. Never writes. -> {"ppq", "tempo" (None if absent), "patterns": {id: {"name", "notes": [..]}}}"""
    b = Path(path).read_bytes()
    if b[:4] != b"FLhd" or len(b) < 22:
        raise ValueError(f"{path}: not an FL Studio project (no FLhd header)")
    hlen = struct.unpack_from("<I", b, 4)[0]
    _fmt, _nch, ppq = struct.unpack_from("<hHH", b, 8)
    i = 8 + hlen
    if b[i:i + 4] != b"FLdt":
        raise ValueError(f"{path}: no FLdt chunk after the header")
    dlen = struct.unpack_from("<I", b, i + 4)[0]
    i += 8
    end = min(len(b), i + dlen)
    patterns: Dict[int, dict] = {}
    cur, tempo = None, None
    try:
        while i < end:
            eid = b[i]
            i += 1
            if eid < 64:
                val = b[i]; i += 1
            elif eid < 128:
                val = struct.unpack_from("<H", b, i)[0]; i += 2
            elif eid < 192:
                val = struct.unpack_from("<I", b, i)[0]; i += 4
            else:
                n, i = _varint(b, i)
                val = b[i:i + n]; i += n
            if eid == 65:
                cur = int(val)
                patterns.setdefault(cur, {"name": None, "notes": []})
            elif eid == 193 and cur is not None:
                patterns[cur]["name"] = bytes(val).decode("utf-16-le", "replace").rstrip("\x00")
            elif eid == 156:
                tempo = int(val) / 1000.0
            elif eid == 224 and cur is not None:
                for k in range(0, len(val) - 23, 24):
                    pos, _fl, ch, ln, key, _g, _fine, _u, _rel, _mch, _pan, vel, _mx, _my = struct.unpack_from(
                        "<IHHIHHBBBBBBBB", val, k)
                    patterns[cur]["notes"].append({"pos": pos, "len": ln, "key": key, "vel": vel, "ch": ch})
    except (struct.error, IndexError):
        pass                                           # a truncated tail: keep what was read
    return {"ppq": int(ppq) or 96, "tempo": tempo, "patterns": patterns}


class Replay:
    """notes: [(on_s, off_s, key, vel 1..127)] from 0; label: what is being played, for the console and status."""

    def __init__(self, notes, label: str, bpm: Optional[float] = None, stretches: Optional[list] = None,
                 patterns: Optional[list] = None, tempo_known: bool = True):
        self.notes = sorted(notes)
        self.label = label
        self.bpm = bpm
        self.tempo_known = tempo_known       # False: tick-based notes played at an ASSUMED tempo (the label says so)
        self.stretches = stretches or []
        self.patterns = patterns or []       # .flp only: [(id, name, notes)] of every pattern with notes

    @property
    def seconds(self) -> float:
        return max((off for _on, off, _k, _v in self.notes), default=0.0)


def _fl_vel(v) -> int:
    return max(1, min(127, int(round(float(v) * 127 / 128))))


def load_replay(path, bpm: Optional[float] = None, stretch: Optional[int] = None,
                pattern: Optional[int] = None) -> Replay:
    """A note list to replay. Formats:
      [{"pos_s","key","vel","len_s"}, ...]                       seconds, velocity 0..127 (or 0..1)
      {"notes": [{"pos","len","key","vel"}], "ppq": 96, "bpm"?}  ticks (an FL score log), FL velocity 0..128
      *.flp                                                      an FL project: the NEWEST pattern with notes (the
                                                                 latest score-log dump) unless `pattern` picks one
    Tick-based notes are split into stretches of playing at gaps longer than 8 beats; the LARGEST is played unless
    `stretch` picks one (1-based; 0 = all). Tempo: bpm, else the file's, else 100 BPM -- and then the label says
    'tempo unknown, assumed 100 BPM (--replay-bpm to set)', so a replay at a guessed tempo never passes for the real one.
    On Worship Grandeur Piano.flp (2026-10-23) the defaults land on Joy to the World: pattern 7, stretch 2, 1378
    notes, Db4 repeating for tension at the end ("the big one with the repeating single note", Daniel)."""
    path = Path(path)
    name = path.name
    pat_info: list = []
    if path.suffix.lower() == ".flp":
        d = read_flp(path)
        pats = {pid: p for pid, p in d["patterns"].items() if p["notes"]}
        if not pats:
            raise ValueError(f"{name}: no pattern notes in this project")
        pat_info = [(pid, p["name"], len(p["notes"])) for pid, p in sorted(pats.items())]
        pid = pattern if pattern is not None else max(pats)    # the newest pattern: the latest score-log dump
        if pid not in pats:
            raise ValueError(f"{name}: no notes in pattern {pid} (patterns with notes: {sorted(pats)})")
        ticks, ppq, file_bpm = pats[pid]["notes"], d["ppq"], d["tempo"]
        pname = pats[pid]["name"]
        name = f"{name} pattern {pid}" + (f" '{pname}'" if pname else "")
    else:
        obj = json.loads(path.read_text(encoding="utf-8"))
        lst = obj if isinstance(obj, list) else obj.get("notes", [])
        if lst and "pos_s" in lst[0]:
            scale = 127.0 if all(float(n.get("vel", 100)) <= 1.0 for n in lst) else 1.0
            notes = [(float(n["pos_s"]), float(n["pos_s"]) + max(0.01, float(n.get("len_s", 0.25))), int(n["key"]),
                      max(1, min(127, int(round(float(n.get("vel", 100)) * scale))))) for n in lst]
            t0 = min((n[0] for n in notes), default=0.0)
            notes = [(a - t0, b - t0, k, v) for a, b, k, v in notes]
            return Replay(notes, f"{name} ({len(notes)} notes)", bpm=None)
        ticks = lst
        ppq = int(obj.get("ppq", 96)) if isinstance(obj, dict) else 96
        file_bpm = (obj.get("bpm") or obj.get("tempo")) if isinstance(obj, dict) else None
    if not ticks:
        raise ValueError(f"{name}: no notes")
    known = bool(bpm or file_bpm)
    use_bpm = float(bpm or file_bpm or DEFAULT_REPLAY_BPM)
    tempo = (f"at {use_bpm:g} BPM" if known else
             f"tempo unknown, assumed {use_bpm:g} BPM (--replay-bpm to set)")
    ticks = sorted(ticks, key=lambda n: n["pos"])
    gap = STRETCH_GAP_BEATS * ppq
    groups: List[list] = [[ticks[0]]]
    for a, b in zip(ticks, ticks[1:]):
        if b["pos"] - a["pos"] > gap:
            groups.append([])
        groups[-1].append(b)
    spt = 60.0 / (use_bpm * ppq)
    info = [{"n": k + 1, "notes": len(g), "start_beat": round(g[0]["pos"] / ppq, 1),
             "seconds": round((max(x["pos"] + x["len"] for x in g) - g[0]["pos"]) * spt, 1)}
            for k, g in enumerate(groups)]
    if stretch == 0:
        chosen, which = ticks, "all stretches"
    else:
        k = (stretch - 1) if stretch else max(range(len(groups)), key=lambda j: len(groups[j]))
        if not 0 <= k < len(groups):
            raise ValueError(f"{name}: stretch {stretch} does not exist (there are {len(groups)})")
        chosen, which = groups[k], f"stretch {k + 1}/{len(groups)}"
    p0 = chosen[0]["pos"]
    notes = [((n["pos"] - p0) * spt, (n["pos"] - p0 + max(1, n["len"])) * spt, int(n["key"]), _fl_vel(n["vel"]))
             for n in chosen]
    label = f"{name}: {which}, {len(notes)} notes{' ' if known else ', '}{tempo}"
    return Replay(notes, label, bpm=use_bpm, stretches=info, patterns=pat_info, tempo_known=known)


def note_schedule(notes) -> List[Tuple[float, int, int, int]]:
    """(on_s, off_s, key, vel) -> [(t, status, key, vel)], ch 1. A re-struck key's earlier note ends just before the
    new one starts, and at equal times note-offs go first, so a re-strike is heard as one."""
    by_key: Dict[int, list] = {}
    for on, off, key, vel in sorted(notes):
        by_key.setdefault(key, []).append([on, off, key, vel])
    ev = []
    for key, lst in by_key.items():
        for a, b in zip(lst, lst[1:]):
            if a[1] > b[0]:
                a[1] = max(a[0], b[0] - 1e-3)
        for on, off, k, vel in lst:
            ev.append((on, 1, k, vel))
            ev.append((off, 0, k, 0))
    ev.sort(key=lambda e: (e[0], e[1], e[2]))
    return [(t, 0x90 if kind else 0x80, k, v) for t, kind, k, v in ev]


def replay_events(replay: "Replay", chords: str = "blend", tail_s: float = 3.0) -> List[Tuple[float, dict]]:
    """The events a page receives from replaying `replay`, computed offline on a simulated clock: [(seconds, event)].
    The same path as a live replay (note_schedule -> Engine._handle: notes, the key, the keys' chord after its settle,
    and with --chords sense the keys' chordsense: key, tension, and its chord where the keys' reading has no name),
    with no threads and no waiting, so a whole take runs in a moment. The MIDI loop is simulated the way it runs: a
    pending chord is announced at its deadline unless a message arrives first, and the keys' chordsense clock steps
    every SENSE_TICK_S; the clock runs on tail_s past the last message. Used to give page logic a real take to be
    tested on (tests/fixtures/vj/)."""
    eng = Engine(http_port=None, chords=chords, say=lambda _m: None)
    clock = [0.0]
    tick = [0.0]
    out: List[Tuple[float, dict]] = []
    eng.hub.tap(lambda e: out.append((round(clock[0], 4), e)))

    def advance(t: float) -> None:
        """The MIDI loop's own work up to t: due settles and the harmony's clock steps, in time order."""
        while True:
            p = eng._chord_pending
            due = p[0] if p is not None else math.inf
            nxt = tick[0] + SENSE_TICK_S if eng.harmony is not None else math.inf
            if min(due, nxt) > t:
                return
            if due <= nxt:
                eng._chord_pending = None
                clock[0] = due
                eng._announce_keys_chord(p[1])
            else:
                tick[0] = clock[0] = nxt
                eng._sense_tick(nxt)

    last = 0.0
    for t, st, key, vel in note_schedule(replay.notes):
        advance(t)
        clock[0] = last = t
        eng._handle("midi", st, key & 0x7F, vel & 0x7F, t)
    advance(last + max(tail_s, CHORD_SETTLE_MAX_S))
    p = eng._chord_pending
    if p is not None:
        eng._chord_pending = None
        clock[0] = p[0]
        eng._announce_keys_chord(p[1])
    return out


# =====================================================================================================================
# hardware: the KeyLab inputs (pushed, not polled) and the pad painter
# =====================================================================================================================
def _live_input_class():
    from . import winmidi as W

    class LiveIn(W.MidiIn):
        """MidiIn that hands each short message straight to a callback instead of collecting it: a VJ session runs for
        hours (a collecting list would grow without bound) and polling adds latency. SysEx is not kept."""

        def __init__(self, port: str, kind: str, push):
            self._kind, self._push = kind, push
            super().__init__(port=port)

        def _cb(self, h, msg, inst, p1, p2):
            if msg == W.MIM_DATA and p1 is not None:
                v = int(p1)
                self._push(self._kind, v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF)

    return LiveIn


def open_keylab_inputs(push, say=print) -> Dict[str, object]:
    """Open BOTH KeyLab inputs ('...MIDI' = keys, pedal, bank pads, controls; '...DAW' = DAW-mode pads and controls).
    Shared with FL under the Windows MIDI Service; an input held exclusively elsewhere is reported and skipped."""
    from . import winmidi as W
    LiveIn = _live_input_class()
    opened: Dict[str, object] = {}
    try:
        names = W.inputs()
    except Exception as exc:
        say(f"MIDI inputs unavailable: {exc}")
        return opened
    for name in names:
        low = name.lower()
        if "keylab" not in low:
            continue
        kind = "daw" if "daw" in low else "midi"
        if kind in opened:
            continue
        try:
            m = LiveIn(port=name, kind=kind, push=push)
            m.start()
            opened[kind] = m
        except Exception as exc:
            say(f"could not listen on {name!r}: {exc}")
    return opened


def fl_running() -> Optional[bool]:
    """Is FL Studio open? (best effort; None = could not tell)"""
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return None
    low = out.lower()
    return any(f'"{exe}"' in low for exe in ("fl64.exe", "fl.exe", "fl studio.exe"))


class PadPainter:
    """Paints the page's pad colours on its OWN thread (never the audio loop): the newest frame wins (frames that
    arrive while one is painting are coalesced), at most one frame per MIN_GAP, only changed pads are sent
    (ledframe.PadRenderer) and every packet passes the output's BurstGovernor. reassert() repaints every pad a moment
    later -- used after a DAW-mode pad press, when FL's script may have repainted that pad itself."""

    MIN_GAP = 0.04

    def __init__(self, out, bank: str = "DAW"):
        from .ledframe import PadRenderer
        self.out = out
        self.render = PadRenderer(out, bank=bank, gap=0.003)
        self._lock = threading.Lock()
        self._frame = None
        self._current = None
        self._reassert_at: Optional[float] = None
        self._wake = threading.Event()
        self._stop = threading.Event()
        self.frames = self.coalesced = self.errors = 0
        self.last_error: Optional[str] = None
        self._t = threading.Thread(target=self._run, name="vj-pads", daemon=True)
        self._t.start()

    def submit(self, rgb) -> bool:
        with self._lock:
            coalesced = self._frame is not None
            self._frame = list(rgb)
            if coalesced:
                self.coalesced += 1
        self._wake.set()
        return coalesced

    def reassert(self, after: float = 0.25) -> None:
        with self._lock:
            if self._current is None:
                return
            self._reassert_at = time.perf_counter() + after
        self._wake.set()

    def _take(self):
        with self._lock:
            frame, self._frame = self._frame, None
            if self._reassert_at is not None and time.perf_counter() >= self._reassert_at:
                self._reassert_at = None
                self.render.resync()
                if frame is None:
                    frame = self._current
            return frame

    def _run(self) -> None:
        last = 0.0
        while not self._stop.is_set():
            with self._lock:
                ra = self._reassert_at
            timeout = 0.5 if ra is None else max(0.0, ra - time.perf_counter())
            self._wake.wait(timeout)
            self._wake.clear()
            if self._stop.is_set():
                break
            frame = self._take()
            if frame is None:
                continue
            gap = self.MIN_GAP - (time.perf_counter() - last)
            if gap > 0:
                time.sleep(gap)
                newer = self._take()
                frame = newer if newer is not None else frame
            try:
                self.render.set_frame(frame)
                self.frames += 1
                with self._lock:
                    self._current = frame
            except Exception as exc:
                self.errors += 1
                self.last_error = f"{type(exc).__name__}: {exc}"
            last = time.perf_counter()

    def stop(self, clear: bool = True) -> None:
        self._stop.set()
        self._wake.set()
        self._t.join(timeout=1.0)
        if clear:
            try:
                self.render.set_frame([(0, 0, 0)] * 12)
            except Exception:
                pass

    def stats(self) -> dict:
        return {"frames": self.frames, "coalesced": self.coalesced, "errors": self.errors,
                "last_error": self.last_error, **self.render.stats()}


# =====================================================================================================================
# HTTP: the contract's three routes (standard library only)
# =====================================================================================================================
class _Handler(BaseHTTPRequestHandler):
    server_version = f"{SRC}/{CONTRACT_V}"
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        try:                                       # small frames must not wait on Nagle + delayed ACK (a late beat)
            self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass

    @property
    def engine(self) -> "Engine":
        return self.server.engine

    def log_message(self, fmt, *args):
        if self.engine.verbose_http:
            sys.stderr.write(f"[vj] {fmt % args}\n")

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _close_after(self) -> None:
        """Every short answer closes its connection. A kept-alive connection would outlive the engine: after stop(),
        a browser's pooled connection (left over from POST /api/pads) could still ask for /api/events and be served
        a stream from a stopped engine -- found end to end, 2026-10-23."""
        self.send_header("Connection", "close")
        self.close_connection = True

    def _json(self, status: int, obj) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self._close_after()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self._close_after()
        self.end_headers()

    def do_GET(self):
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if self.engine.stopping:
            return self._json(503, {"error": "the engine is stopping"})
        if path == "/api/events":
            return self._events()
        if path == "/api/state":
            return self._json(200, self.engine.state())
        if path in ("/", "/api"):
            return self._json(200, {"src": SRC, "v": CONTRACT_V, "routes": {
                "GET /api/events": "Server-Sent Events: hello, beat, energy, hit, chord, key, tension, note, pedal, "
                                   "pad, ctl, status",
                "GET /api/state": "last chord, bpm, the key, connected inputs, audio health and timing, LED state",
                "POST /api/pads": '{"colors": ["#rrggbb", ... 12]} lights the DAW-bank pads'}})
        return self._json(404, {"error": f"no route {path}"})

    def do_POST(self):
        path = urlsplit(self.path).path.rstrip("/")
        if path != "/api/pads":
            return self._json(404, {"error": f"no route {path}"})
        if self.engine.stopping:
            return self._json(503, {"ok": False, "error": "the engine is stopping"})
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._json(400, {"ok": False, "error": "Content-Length is not a number"})
        if length <= 0 or length > MAX_PADS_BODY:
            return self._json(413 if length > 0 else 400, {"ok": False, "error": f"body must be 1..{MAX_PADS_BODY} bytes"})
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return self._json(400, {"ok": False, "error": "body is not JSON"})
        status, payload = self.engine.pads_request(body)
        return self._json(status, payload)

    def _events(self) -> None:
        hub = self.engine.hub
        sub = hub.subscribe()
        if sub is None:                           # the engine is stopping: no stream from a closed hub
            return self._json(503, {"error": "the engine is stopping"})
        token, inbox = sub
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self._cors()
            self._close_after()                   # no Content-Length: the stream ends when the connection does
            self.end_headers()
            self.wfile.write(b"retry: 1000\n\n" + b"".join(Hub.frame(e) for e in self.engine.greeting()))
            last = time.monotonic()
            while True:
                try:
                    frame = inbox.get(timeout=0.25)
                except queue.Empty:
                    frame = b""
                if frame is None:
                    return
                if frame:
                    chunks, done = [frame], False
                    while len(chunks) < 64:
                        try:
                            more = inbox.get_nowait()
                        except queue.Empty:
                            break
                        if more is None:
                            done = True
                            break
                        chunks.append(more)
                    self.wfile.write(b"".join(chunks))
                    last = time.monotonic()
                    if done:
                        return
                elif time.monotonic() - last >= self.engine.heartbeat_s:
                    self.wfile.write(b": hb\n\n")
                    last = time.monotonic()
                if self._peer_gone():
                    return
        except (OSError, ValueError):
            return
        finally:
            hub.unsubscribe(token)

    def _peer_gone(self) -> bool:
        """An EventSource never sends after its request, so a readable socket means the peer closed (or reset)."""
        try:
            readable, _, _ = select.select([self.connection], [], [], 0)
            if not readable:
                return False
            return self.connection.recv(1, socket.MSG_PEEK) == b""
        except (OSError, ValueError):
            return True


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False      # on Windows, reuse would let two servers share a port

    def __init__(self, port: int, engine: "Engine"):
        super().__init__((HOST, port), _Handler)
        self.engine = engine

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


# =====================================================================================================================
# the engine
# =====================================================================================================================
class Engine:
    """Owns the threads. Hardware is handed in (inputs via attach_inputs / feed_midi, an LED output, an audio
    source), so the same engine runs on fakes in the tests and on the KeyLab live."""

    def __init__(self, http_port: Optional[int] = DEFAULT_PORT, beat_engine: str = "a", source=None, led_out=None,
                 led_refusal: Optional[str] = "LEDs are off (--no-leds)", led_refusal_status: int = 409,
                 pads_mode: str = "both",
                 rate_limit: bool = False, ahead_ms: float = AHEAD_S * 1000, offset_ms: float = 0.0,
                 seed_bpm: Optional[float] = None, heartbeat_s: float = HEARTBEAT_S, replay: Optional[Replay] = None,
                 replay_delay: float = 1.5, verbose: bool = False, verbose_http: bool = False,
                 say: Callable[[str], None] = print, chords: str = "blend"):
        if pads_mode not in ("daw", "bank", "both"):
            raise ValueError("pads_mode must be daw, bank or both")
        if chords not in CHORD_MODES:
            raise ValueError(f"chords must be one of {', '.join(CHORD_MODES)}")
        self.http_port, self.beat_engine, self.source = http_port, beat_engine, source
        self.chords = chords
        # --chords sense / blend: chordsense on the audio (when there is a source) and on the keys
        self.harmony: Optional[Harmony] = (Harmony(rate=getattr(source, "rate", None))
                                           if chords in ("sense", "blend") else None)
        self._keys_lost = False                      # the keys' own reading cannot name what sounds now
        self.pads_mode, self.rate_limit = pads_mode, rate_limit
        self.ahead_s, self.offset_s, self.seed_bpm = ahead_ms / 1000.0, offset_ms / 1000.0, seed_bpm
        self.heartbeat_s, self.replay, self.replay_delay = heartbeat_s, replay, replay_delay
        self.verbose, self.verbose_http, self.say = verbose, verbose_http, say
        self.hub = Hub()
        self.led_out = led_out
        self.led_refusal = None if led_out is not None else led_refusal
        # why POST /api/pads is refused: 409 = the LEDs were turned off (--no-leds), 503 = no DAW output was found
        self.led_refusal_status = led_refusal_status
        self.led_info: dict = {}
        self.painter: Optional[PadPainter] = None
        self.inputs: Dict[str, object] = {}
        self._mq: "queue.SimpleQueue" = queue.SimpleQueue()
        self._stop = threading.Event()
        self._threads: List[threading.Thread] = []
        self._server: Optional[_Server] = None
        self._t0 = time.perf_counter()
        self.port: Optional[int] = None
        # keys / pads / controls
        self.voicing = Voicing()
        self.key = KeyFinder()                       # spelling: Gb or F#
        self._keys_t = -1e9                          # when a key was last struck (the audio's key evidence waits)
        self.cc = CCDecoder()
        self._pedal = False
        self._keys_shown: Optional[str] = None       # the chord the keys are showing now (None once all released)
        self._keys_last: Optional[str] = None        # the last chord the keys announced (for "changed")
        self._chord_pending: Optional[tuple] = None  # (deadline, event, first_t)
        self._pad_on: Dict[int, Tuple[float, str]] = {}
        self._pb_last: Dict[str, int] = {}
        # shared state for /api/state
        self.last = {"chord": None, "chord_keys": None, "chord_audio": None}
        self.beat = {"bpm": None, "conf": None, "n": 0, "on_beat": None}
        self.audio = {"source": getattr(source, "name", None), "rate": getattr(source, "rate", None),
                      "running": False, "blocks": 0, "behind_s": 0.0, "late_blocks": 0, "proc_ms_avg": 0.0,
                      "proc_ms_max": 0.0, "idle_s": 0.0, "silence_filled_s": 0.0, "dropped_s": 0.0,
                      "level_db": None, "chord_analysis": None, "chords": chords,
                      "sense_ms_avg": None, "sense_ms_max": None}
        # the capture timing record of the blocks the audio loop read: the first and the latest hand-over, and the
        # samples between (beatsync.capture_timing turns them into wall vs sample time); per-block processing times
        self._timing: Optional[dict] = None
        self._proc_ms: deque = deque(maxlen=TIMING_KEEP)
        self._sense_ms: deque = deque(maxlen=TIMING_KEEP)
        self._sense_errors = 0
        self.replay_state = None if replay is None else {"label": replay.label, "notes": len(replay.notes),
                                                         "seconds": round(replay.seconds, 1), "played": 0,
                                                         "done": False}

    # ----------------------------------------------------------------------------------------------- lifecycle
    def start(self) -> "Engine":
        self._t0 = time.perf_counter()
        if self.http_port is not None:                     # bind first: a taken port fails before any thread runs
            self._server = _Server(self.http_port, self)
            self.port = self._server.server_address[1]
            self._spawn(lambda: self._server.serve_forever(poll_interval=0.25), "vj-http")
        if self.led_out is not None:
            self.painter = PadPainter(self.led_out)
        self._spawn(self._midi_loop, "vj-midi")
        if self.source is not None:
            self._spawn(self._audio_loop, "vj-audio")
        if self.replay is not None:
            self._spawn(self._replay_loop, "vj-replay")
        self.status(self.summary())
        return self

    def _spawn(self, fn, name: str) -> None:
        t = threading.Thread(target=fn, name=name, daemon=True)
        t.start()
        self._threads.append(t)

    def attach_inputs(self, inputs: Dict[str, object]) -> None:
        self.inputs.update(inputs)

    @property
    def stopping(self) -> bool:
        return self._stop.is_set()

    def stop(self) -> None:
        """In this order: refuse new requests (stopping), stop accepting connections, end every open stream (the hub
        closes, and refuses any later subscribe), then the threads, the pads and the inputs. Every short route closes
        its connection, so no kept-alive connection is left to ask a stopped engine for a stream."""
        self._stop.set()
        if self._server is not None:
            self._server.shutdown()
        self.hub.close()
        self._mq.put(None)
        for t in self._threads:
            if t.name != "vj-http":
                t.join(timeout=1.5)
        audio_done = not any(t.name == "vj-audio" and t.is_alive() for t in self._threads)
        if self.painter is not None:
            self.painter.stop(clear=True)
        if self._server is not None:
            self._server.server_close()
        for m in self.inputs.values():
            try:
                m.stop(); m.close()
            except Exception:
                pass
        if self.source is not None and audio_done:       # a loopback blocked in read() is left to process exit
            try:
                self.source.close()
            except Exception:
                pass

    # ----------------------------------------------------------------------------------------------- publishing
    def publish(self, evt: dict) -> None:
        self.hub.publish(evt)

    def status(self, msg: str) -> None:
        if self.verbose or msg.startswith("!"):
            self.say(f"[vj] {msg.lstrip('!')}")
        self.publish({"t": "status", "msg": msg.lstrip("!")})

    def hello(self) -> dict:
        """leds tells the page whether POST /api/pads can light anything; when it cannot, leds_reason says why and
        the page does not post (a refused post every 100 ms would be spam)."""
        on = self.led_out is not None
        return {"t": "hello", "v": CONTRACT_V, "src": SRC, "beat_engine": self.beat_engine, "chords": self.chords,
                "pads_mode": self.pads_mode, "leds": on,
                "leds_reason": None if on else (self.led_refusal or "no LED output")}

    def greeting(self) -> List[dict]:
        """What a page gets the moment it connects: hello, where things stand, the key and tension the page would
        have been told, and the chord sounding now."""
        out = [self.hello(), {"t": "status", "msg": self.summary()}]
        if self.harmony is not None:
            snap_key, snap_t = self.harmony.key_shown, self.harmony.tension_shown
            if snap_key:
                out.append(dict(snap_key))
            if snap_t:
                out.append(dict(snap_t))
        if self.last["chord"]:
            out.append({**self.last["chord"], "changed": False})
        return out

    def summary(self) -> str:
        ins = ", ".join(getattr(m, "name", k) for k, m in self.inputs.items()) or "no KeyLab input"
        audio = self.audio["source"] or "no audio"
        leds = "LEDs on" if self.led_out is not None else (self.led_refusal or "LEDs off")
        rp = f" | replaying {self.replay.label}" if self.replay is not None else ""
        return (f"{SRC} v{CONTRACT_V}: {ins} | {audio} | beat_{self.beat_engine} | chords {self.chords} | "
                f"pads {self.pads_mode} | {leds}{rp}")

    def key_name(self) -> Optional[str]:
        """The key the page is told (chordsense, --chords sense), else the spelling helper's (KeyFinder) estimate."""
        if self.harmony is not None:
            k = self.harmony.key_now()
            if k is not None:
                return k[0]
        return self.key.name()

    def _flats(self) -> bool:
        """Spell pitch class 6 as Gb? By the key the page is told, else by KeyFinder's estimate."""
        if self.harmony is not None:
            k = self.harmony.key_now()
            f = key_has_flats(k[0]) if k else None
            if f is not None:
                return f
        return self.key.flats()

    def timing(self) -> dict:
        """The audio loop's timing receipt: the capture timing record of the blocks it read (beatsync.capture_timing:
        wall time from the first hand-over to the latest against the samples read; 'gap' True when they differ by more
        than 20 ms beyond the idle grace a paused loopback leaves), and the per-block processing cost, whole loop and
        chordsense's share, in ms (avg, p50, p99, max over the last TIMING_KEEP blocks)."""
        out: dict = {}
        tm = self._timing
        if tm is not None:
            from .beatsync import GAP_TOL_S, capture_timing
            rec = capture_timing(*tm)
            grace = float(getattr(self.source, "gap_s", 0.0) or 0.0)
            rec["idle_grace_s"] = round(grace, 3)
            rec["unexplained_gap_ms"] = round(rec["gap_ms"] - 1000.0 * grace, 1)
            rec["gap"] = abs(rec["unexplained_gap_ms"]) > 1000.0 * GAP_TOL_S
            out["capture"] = rec
        for name, buf in (("proc_ms", self._proc_ms), ("sense_ms", self._sense_ms)):
            vals = None
            for _attempt in range(3):                     # the audio thread appends while this reads
                try:
                    vals = np.array(tuple(buf), dtype=float) if buf else None
                    break
                except RuntimeError:
                    continue
            out[name] = None if vals is None or not len(vals) else {
                "blocks": int(len(vals)), "avg": round(float(vals.mean()), 3),
                "p50": round(float(np.percentile(vals, 50)), 3), "p99": round(float(np.percentile(vals, 99)), 3),
                "max": round(float(vals.max()), 3)}
        return out

    def state(self) -> dict:
        return {"v": CONTRACT_V, "src": SRC, "uptime_s": round(time.perf_counter() - self._t0, 1),
                "port": self.port, "beat_engine": self.beat_engine, "chords": self.chords,
                "pads_mode": self.pads_mode,
                "rate_limit": self.rate_limit, "bpm": self.beat["bpm"], "conf": self.beat["conf"],
                "beat_n": self.beat["n"], "on_beat": self.beat["on_beat"],
                "chord": self.last["chord"], "chord_keys": self.last["chord_keys"],
                "chord_audio": self.last["chord_audio"], "key": self.key_name(),
                "harmony": None if self.harmony is None else {**self.harmony.snapshot(),
                                                              "errors": self._sense_errors},
                "inputs": {k: getattr(self.inputs.get(k), "name", None) for k in ("midi", "daw")},
                "audio": {**self.audio, "timing": self.timing()},
                "leds": {"enabled": self.painter is not None, "refused": self.led_refusal,
                         "refusal_status": None if self.led_out is not None else self.led_refusal_status,
                         **self.led_info,
                         **(self.painter.stats() if self.painter is not None else {})},
                "replay": self.replay_state, "clients": self.hub.clients, "events": dict(self.hub.counts),
                "dropped": self.hub.dropped}

    # ----------------------------------------------------------------------------------------------- pads (LEDs)
    def pads_request(self, body) -> Tuple[int, dict]:
        colors = body.get("colors") if isinstance(body, dict) else None
        if not isinstance(colors, list) or len(colors) != 12:
            return 400, {"ok": False, "error": 'want {"colors": ["#rrggbb", ... 12]}'}
        try:
            rgb = []
            for c in colors:
                if not isinstance(c, str) or len(c) > 32:
                    raise ValueError(f"not a colour: {c!r}")
                rgb.append(P.parse_color(c))
        except ValueError as exc:
            return 400, {"ok": False, "error": str(exc)}
        if self.painter is None:                          # 409: turned off on purpose; 503: no device to light
            return self.led_refusal_status, {"ok": False, "refused": self.led_refusal or "no LED output"}
        coalesced = self.painter.submit(rgb)
        return 202, {"ok": True, "coalesced": coalesced}

    # ----------------------------------------------------------------------------------------------- MIDI
    def feed_midi(self, kind: str, status: int, d1: int, d2: int, t: Optional[float] = None) -> None:
        """Thread-safe: hand one short message from input `kind` ('midi' = the keys port, 'daw' = the DAW port)."""
        self._mq.put((kind, status & 0xFF, d1 & 0x7F, d2 & 0x7F, time.perf_counter() if t is None else t))

    def _midi_loop(self) -> None:
        next_tick = time.perf_counter()
        while not self._stop.is_set():
            p = self._chord_pending
            now = time.perf_counter()
            timeout = 0.25 if p is None else max(0.0, p[0] - now)
            if self.harmony is not None:                  # the keys' chordsense clock steps every SENSE_TICK_S
                timeout = min(timeout, max(0.0, next_tick - now))
            try:
                item = self._mq.get(timeout=timeout)
            except queue.Empty:
                item = None
            if item is not None:
                try:
                    self._handle(*item)
                except Exception as exc:                  # one odd message never takes the dispatcher down
                    self.status(f"!midi: {type(exc).__name__}: {exc}")
            p = self._chord_pending
            if p is not None and time.perf_counter() >= p[0]:
                self._chord_pending = None
                self._announce_keys_chord(p[1])
            if self.harmony is not None:
                now = time.perf_counter()
                if now >= next_tick:
                    next_tick = now + SENSE_TICK_S
                    self._sense_tick(now)

    def _sense_tick(self, now: float) -> None:
        try:
            self._sense_keys(self.harmony.tick(now), now)
        except Exception as exc:                          # the keys' harmony never takes the dispatcher down
            self._sense_failed("keys", exc)

    def _sense_note(self, ev: dict, t: float) -> None:
        try:
            self._sense_keys(self.harmony.note(ev, t), t)
        except Exception as exc:
            self._sense_failed("keys", exc)

    def _sense_failed(self, ear: str, exc: Exception) -> None:
        self._sense_errors += 1
        if self._sense_errors in (1, 10, 100, 1000):      # said, but never a flood
            self.status(f"!chordsense ({ear}): {type(exc).__name__}: {exc} ({self._sense_errors} so far)")

    def _sense_keys(self, events: List[dict], t: float) -> None:
        """The keys' chordsense events: key and tension go to the page; its CHORD only while today's reading
        (Voicing + theory.analyze) cannot name what sounds -- a held note foreign to the chord, a pedal wash."""
        for e in events:
            if e.get("t") != "chord":
                self.publish(e)
            elif self._keys_lost and e.get("root") is not None:
                evt = self.harmony.decorate(e, t, self.key.flats())
                if evt["name"] != self._keys_shown:
                    evt["changed"] = evt["name"] != self._keys_last
                    self._keys_shown = self._keys_last = evt["name"]
                    self.last["chord"] = self.last["chord_keys"] = evt
                    self.publish(evt)

    def _handle(self, kind: str, status: int, d1: int, d2: int, t: float) -> None:
        if status >= 0xF0:
            return                                        # clock / active sensing
        hi, ch = status & 0xF0, (status & 0x0F) + 1
        if hi in (0x80, 0x90):
            on = hi == 0x90 and d2 > 0
            if ch == 10:
                pad = None
                if kind == "daw" and 0 <= d1 <= 11:
                    pad, src = d1 + 1, "daw"
                elif kind == "midi" and d1 in P._NOTE_PAD:
                    pad, src = P._NOTE_PAD[d1], "bank"
                if pad is not None:
                    return self._pad(pad, src, d2, on, t)
                if kind == "daw":
                    return self._button(f"note{d1}", d2 if on else 0, kind, ch)
                return
            if kind == "midi":
                self.publish({"t": "note", "key": d1, "vel": round(d2 / 127.0, 3) if on else 0.0, "on": on})
                if on:
                    self.key.add((d1,), t, d2 / 127.0)
                    self._keys_t = t
                self.voicing.feed(status, d1, d2)
                self._keys_changed(t)
                if self.harmony is not None:
                    self._sense_note({"note": d1, "vel": d2 if on else 0}, t)
                return
            return self._button(f"note{d1}", d2 if on else 0, kind, ch)
        if hi == 0xB0:
            if d1 == 64:
                self.voicing.feed(status, d1, d2)
                on = d2 >= 64
                if on != self._pedal:
                    self._pedal = on
                    self.publish({"t": "pedal", "on": on})
                    if not on:
                        self._keys_changed(t)
                if self.harmony is not None and kind == "midi":
                    self._sense_note({"sustain": d2}, t)
                return
            dec, note = self.cc.feed(f"{kind}:{ch}:cc{d1}", d1, d2, t)
            if note:
                self.status(f"!{note} ({kind} input, channel {ch})")
            self.publish({"t": "ctl", "id": f"cc{d1}", **dec, "port": kind, "ch": ch})
            return
        if hi == 0xE0:
            v14 = (d2 << 7) | d1
            key = f"{kind}:{ch}"
            delta = v14 - self._pb_last.get(key, 8192)
            self._pb_last[key] = v14
            self.publish({"t": "ctl", "id": "pb", "kind": "abs", "value": round(v14 / 16383.0, 4), "delta": delta,
                          "port": kind, "ch": ch})
            return
        if hi == 0xD0:
            self.publish({"t": "ctl", "id": "at", "kind": "abs", "value": round(d1 / 127.0, 4), "delta": 0,
                          "port": kind, "ch": ch})
            return
        if hi == 0xA0 and ch == 10:                       # pad pressure (poly aftertouch)
            pad = (d1 + 1) if (kind == "daw" and 0 <= d1 <= 11) else P._NOTE_PAD.get(d1)
            if pad is not None:
                self.publish({"t": "ctl", "id": f"pad{pad}_at", "kind": "abs", "value": round(d2 / 127.0, 4),
                              "delta": 0, "port": kind, "ch": ch})

    def _button(self, ident: str, vel: int, kind: str, ch: int) -> None:
        self.publish({"t": "ctl", "id": ident, "kind": "abs", "value": round(vel / 127.0, 4), "delta": 0,
                      "port": kind, "ch": ch})

    def _pad(self, pad: int, src: str, vel: int, on: bool, t: float) -> None:
        if self.pads_mode != "both" and src != self.pads_mode:
            return
        prev = self._pad_on.get(pad)
        if on:
            if prev is not None and prev[1] != src and t - prev[0] < PAD_DEDUP_S:
                return                                    # the same hit, seen on the other input
            self._pad_on[pad] = (t, src)
        elif prev is not None and prev[1] != src:
            return                                        # the other input's release of a hit counted once already
        self.publish({"t": "pad", "pad": pad, "vel": round(vel / 127.0, 3) if on else 0.0, "on": on, "src": src})
        if src == "daw" and not on and self.painter is not None:
            self.painter.reassert(0.25)                   # FL's script may repaint a DAW-mode pad on release

    def _keys_changed(self, t: float) -> None:
        sounding = self.voicing.sounding
        if not sounding:
            self._keys_shown = None
            self._chord_pending = None
            self._keys_lost = False
            return
        name, root, qual = analyze(sorted(sounding))
        if root is None or qual == "note":
            self._chord_pending = None
            # a set of notes with no name (not a lone note): the keys' chordsense speaks for it (--chords sense)
            self._keys_lost = root is None
            return
        self._keys_lost = False
        name = spell(name, self._flats())
        if name == self._keys_shown:
            self._chord_pending = None
            return
        evt = {"t": "chord", "src": "keys", "name": name, "root": int(root), "quality": _quality(qual),
               "pcs": sorted({n % 12 for n in sounding})}
        if self.harmony is not None:
            evt["bass"] = min(sounding) % 12
        first = self._chord_pending[2] if self._chord_pending is not None else t
        self._chord_pending = (min(t + CHORD_SETTLE_S, first + CHORD_SETTLE_MAX_S), evt, first)

    def _announce_keys_chord(self, evt: dict) -> None:
        evt = {**evt, "changed": evt["name"] != self._keys_last}
        if self.harmony is not None:                      # the numeral in the key the page is told; exact: conf 1
            try:
                evt = self.harmony.decorate({**evt, "conf": 1.0}, None, self._flats())
            except Exception as exc:                      # then today's plain keys chord, never a lost dispatcher
                self._sense_failed("keys", exc)
        self._keys_shown = self._keys_last = evt["name"]
        self.last["chord"] = self.last["chord_keys"] = evt
        self.publish(evt)

    # ----------------------------------------------------------------------------------------------- audio
    def _audio_loop(self) -> None:
        src = self.source
        rate = int(src.rate)
        try:
            clock = BeatClock(rate, HOP, self.beat_engine, self.seed_bpm, self.ahead_s)
        except Exception as exc:
            self.status(f"!beat_{self.beat_engine} would not start: {type(exc).__name__}: {exc}")
            return
        harmony = self.harmony if (self.harmony is not None and self.harmony.audio is not None) else None
        blend = harmony is not None and self.chords == "blend"   # the templates name, chordsense keys and tensions
        ana = Analyzer(rate, HOP, rate_limit=self.rate_limit, chords=harmony is None or blend)
        a = self.audio
        a["running"] = True
        audio_t, wall0, idle, warned = 0.0, None, 0.0, 0.0
        proc_sum = sense_sum = 0.0
        sense_n = 0
        t_read = time.perf_counter()
        try:
            while not self._stop.is_set():
                block = src.read()
                t_got = time.perf_counter()
                if block is None:
                    self.status("audio source ended")
                    break
                n = len(block)
                # (first hand-over, its frames, latest hand-over, samples read, rate): one tuple, replaced whole, so
                # the state route never reads a half-updated record
                tm = self._timing
                self._timing = ((t_got, n, t_got, n, rate) if tm is None else (tm[0], tm[1], t_got, tm[3] + n, rate))
                dur = n / rate
                if wall0 is None:
                    wall0 = t_got - dur
                elif t_got - t_read > dur + 0.2:
                    idle += (t_got - t_read) - dur        # the source paused (nothing playing): not a loss
                audio_t += dur
                behind = (t_got - wall0) - idle - getattr(src, "gap_s", 0.0) - audio_t
                if behind - warned > 0.25:
                    warned = behind
                    lost = getattr(src, "dropped_s", None)
                    self.status(f"!audio: {behind:.2f} s behind the source so far"
                                + (f", {lost:.2f} s of it dropped" if lost else "")
                                + " (the analysis loop fell behind)")
                b = clock.feed(block)
                if b is not None and ana.silent_for(audio_t) < SILENT_BEATS_S:
                    due = (b["lead_s"] + self.offset_s - (time.perf_counter() - t_got)) * 1000.0
                    evt = {"t": "beat", "due_ms": round(max(0.0, due), 1), "bpm": round(b["bpm"], 2),
                           "conf": round(min(1.0, max(0.0, b["conf"])), 3), "n": b["n"], "on_beat": b["on_beat"]}
                    self.beat.update(bpm=evt["bpm"], conf=evt["conf"], n=evt["n"], on_beat=evt["on_beat"])
                    self.publish(evt)
                for evt in ana.feed(block, audio_t):
                    if evt["t"] == "chord":
                        self.audio_chord_seen(evt, t_got)
                        if blend:                     # its numeral and spelling in the key chordsense tells the page
                            try:
                                evt = harmony.decorate(evt, t_got, self.key.flats())
                            except Exception as exc:  # chordsense never stops the chords, beat, energy or hits
                                self._sense_failed("audio", exc)
                        self.last["chord"] = self.last["chord_audio"] = evt
                    self.publish(evt)
                if harmony is not None:
                    t_s = time.perf_counter()
                    try:
                        sensed = [self._audio_sense_chord(e, t_got) if e["t"] == "chord" else e
                                  for e in harmony.feed_audio(block, t_got) if not (blend and e["t"] == "chord")]
                    except Exception as exc:              # chordsense never stops the beat, the energy, the hits
                        self._sense_failed("audio", exc)
                        sensed = []
                    s_ms = (time.perf_counter() - t_s) * 1000.0
                    for evt in sensed:
                        self.publish(evt)
                    sense_sum += s_ms
                    sense_n += 1
                    self._sense_ms.append(s_ms)
                    a["sense_ms_avg"] = round(sense_sum / sense_n, 4)
                    a["sense_ms_max"] = round(max(a["sense_ms_max"] or 0.0, s_ms), 3)
                proc = time.perf_counter() - t_got
                self._proc_ms.append(proc * 1000.0)
                a["blocks"] += 1
                proc_sum += proc
                a["proc_ms_avg"] = round(1000.0 * proc_sum / a["blocks"], 3)
                a["proc_ms_max"] = round(max(a["proc_ms_max"], proc * 1000.0), 3)
                if proc > dur:
                    a["late_blocks"] += 1
                a["behind_s"], a["idle_s"] = round(max(0.0, behind), 3), round(idle, 2)
                a["silence_filled_s"] = round(getattr(src, "filled", 0) * dur, 2)
                a["dropped_s"] = round(getattr(src, "dropped_s", 0.0), 2)
                if a["blocks"] % 16 == 0:
                    a["level_db"] = round(ana.level_db, 1)
                    if harmony is None or blend:
                        a["chord_analysis"] = ana.chords.last
                    else:
                        snap = harmony.audio.snapshot()
                        a["chord_analysis"] = {"chord": snap["chord"]["name"], "key": snap["key"],
                                               "key_confidence": snap["key_confidence"], "tension": snap["tension"],
                                               "pedal": snap["pedal"], "tuning_cents": snap["tuning_cents"]}
                t_read = time.perf_counter()
        except Exception as exc:
            self.status(f"!audio loop stopped: {type(exc).__name__}: {exc}")
        finally:
            a["running"] = False

    def audio_chord_seen(self, evt: dict, t: float) -> dict:
        """An audio chord is spelled by the key (pitch class 6: Gb in a flat key, else F#), and is evidence for it while
        the keys are quiet: what Daniel plays is the better witness than everything coming out of the speakers (a demo
        groove in C under a replay in D-flat left the key undecided, and D-flat's Gb chords read F#)."""
        if t - self._keys_t > KEYS_WITNESS_S:
            self.key.add(evt["pcs"], t)
        if evt["root"] == 6:
            evt["name"] = pc_name(6, self.key.flats()) + evt["name"][2:]
        return evt

    def _audio_sense_chord(self, evt: dict, t: float) -> dict:
        """A chordsense audio chord for the page (--chords sense): decorated in the key the page is told, and evidence
        for the spelling helper's key while the keys are quiet, as audio_chord_seen does for the basic chords."""
        evt = self.harmony.decorate(evt, t, self.key.flats())
        if evt.get("root") is not None and t - self._keys_t > KEYS_WITNESS_S:
            self.key.add(evt["pcs"], t)
        self.last["chord"] = self.last["chord_audio"] = evt
        return evt

    # ----------------------------------------------------------------------------------------------- replay
    def _replay_loop(self) -> None:
        rp = self.replay
        sched = note_schedule(rp.notes)
        self.status(f"replay: {rp.label} ({rp.seconds:.0f} s)")
        t0 = time.perf_counter() + self.replay_delay
        for t, st, key, vel in sched:
            target = t0 + t
            while not self._stop.is_set():
                rem = target - time.perf_counter()
                if rem <= 0:
                    break
                time.sleep(min(rem, 0.05))
            if self._stop.is_set():
                return
            self.feed_midi("midi", st, key, vel)
            if st == 0x90:
                self.replay_state["played"] += 1
        self.replay_state["done"] = True
        self.status("replay done")


# =====================================================================================================================
# the verb
# =====================================================================================================================
def line_buffered_stdout() -> None:
    """A piped engine must speak as it goes: block-buffered stdout held the console (the URL, every warning) until
    the buffer filled or the process exited (found end to end, 2026-10-23). The house blessing does it -- utf-8,
    line-buffered, pipe-immune (core.foundation.streams) -- with a plain reconfigure when core is not importable."""
    try:
        from core.foundation.streams import self_bless_stdout
        self_bless_stdout()
        return
    except Exception:
        pass
    for name in ("stdout", "stderr"):
        try:
            getattr(sys, name).reconfigure(line_buffering=True)
        except Exception:
            pass


def run(port: int = DEFAULT_PORT, engine: str = "a", leds: bool = True, connect: bool = False,
        replay_midi: Optional[str] = None, replay_bpm: Optional[float] = None, replay_stretch: Optional[int] = None,
        replay_pattern: Optional[int] = None, replay_audio: Optional[str] = None, loop: bool = False,
        audio: bool = True, midi: bool = True, rate_limit: bool = False, pads: str = "both",
        ahead_ms: float = AHEAD_S * 1000, offset_ms: float = 0.0, seed_bpm: Optional[float] = None,
        secs: Optional[float] = None, quiet: bool = False, chords: str = "blend") -> int:
    line_buffered_stdout()
    say = print
    replay = None
    if replay_midi:
        replay = load_replay(replay_midi, bpm=replay_bpm, stretch=replay_stretch, pattern=replay_pattern)
        if len(replay.patterns) > 1:
            say("patterns with notes (pick with --replay-pattern N; default the newest):")
            for pid, pname, count in replay.patterns:
                say(f"  {pid}: {count} notes" + (f" '{pname}'" if pname else ""))
        if len(replay.stretches) > 1:
            say("replay stretches (pick with --replay-stretch N, 0 = all):")
            for s in replay.stretches:
                say(f"  {s['n']}: {s['notes']} notes from beat {s['start_beat']}, {s['seconds']} s")
        say(f"replay: {replay.label}")

    source = None
    if replay_audio:
        source = SynthSource() if replay_audio == "demo" else FileSource(replay_audio, loop=loop)
    elif audio:
        try:
            source = IdleFill(LoopbackSource())           # the loopback's read blocks while nothing plays
        except Exception as exc:
            say(f"no loopback audio ({type(exc).__name__}: {exc}); running on MIDI only")

    led_out, refusal, refusal_status, led_info = None, "LEDs are off (--no-leds)", 409, {}
    fl = fl_running()
    if leds:
        try:
            from . import winmidi as W
            led_out = W.MidiOut(prefer="daw")             # BurstGovernor on by default
            led_info = {"port": led_out.name, "guest": True, "fl_running": fl}
            if connect:
                if fl:
                    say("FL Studio is open: staying in guest mode (no DAW connect) -- FL keeps the connection")
                else:
                    led_out.send_sysex(P.daw_connect(True))
                    led_info["guest"] = False
            elif fl is False:
                say("FL Studio is not running: if the pads stay dark, rerun with --connect")
        except Exception as exc:
            led_out, refusal, refusal_status = None, f"no KeyLab DAW output ({exc})", 503

    eng = Engine(http_port=port, beat_engine=engine, source=source, led_out=led_out, led_refusal=refusal,
                 led_refusal_status=refusal_status, pads_mode=pads, rate_limit=rate_limit, ahead_ms=ahead_ms, offset_ms=offset_ms, seed_bpm=seed_bpm,
                 replay=replay, verbose=not quiet, say=say, chords=chords)
    eng.led_info = led_info
    if midi:
        eng.attach_inputs(open_keylab_inputs(eng.feed_midi, say=say))
    try:
        eng.start()
    except OSError as exc:
        say(f"cannot serve on {HOST}:{port}: {exc} (is another vj engine running?)")
        for m in eng.inputs.values():
            try:
                m.stop(); m.close()
            except Exception:
                pass
        if led_out is not None:
            led_out.close()
        if source is not None:
            source.close()
        return 1
    base = f"http://{HOST}:{eng.port}"
    say(f"VJ engine: {base}/api/events (SSE) | {base}/api/state | POST {base}/api/pads  -- Ctrl-C to stop")
    say("pads: DAW mode arrives on the DAW input; with FL's Arturia script running, DAW-mode pads 1-8 also toggle "
        "FL step-sequencer steps on release -- use the normal pad bank (notes 36-47) then; both are accepted")
    try:
        end = (time.perf_counter() + secs) if secs else None
        while end is None or time.perf_counter() < end:
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        eng.stop()
        if led_out is not None:
            try:
                if not led_info.get("guest", True):
                    led_out.send_sysex(P.daw_connect(False))
            except Exception:
                pass
            led_out.close()
        st = eng.state()
        tm = st["audio"]["timing"]
        cap, pm, sm = tm.get("capture"), tm.get("proc_ms"), tm.get("sense_ms")
        say(f"vj done -- events {st['events']} | audio blocks {st['audio']['blocks']}, late {st['audio']['late_blocks']}, "
            f"behind {st['audio']['behind_s']} s | dropped frames {st['dropped']}"
            + (f" | capture {cap['sample_secs']:.1f} s of samples over {cap['wall_secs']:.1f} s wall, "
               f"unexplained gap {cap['unexplained_gap_ms']:+.0f} ms{' GAP' if cap['gap'] else ''}" if cap else "")
            + (f" | per block {pm['avg']:.2f} ms avg, p99 {pm['p99']:.2f}, max {pm['max']:.2f}" if pm else "")
            + (f" (chordsense {sm['avg']:.2f} avg, p99 {sm['p99']:.2f})" if sm else ""))
    return 0
