"""arsenal.keylab.beatgrid -- one beat clock for the VJ engine: the beat tracker, the song database and the hand.

Daniel (2026-10-24, verbatim): "for the lasers perhaps we can do a triple strobe, or a one two flicker, it could be
timed to the bpm of the track once its established from a database, I can also tap the tempo button or the tap button
to the right of record on the keylab."

The build spec: research/reviewed/keylab-liberation-2026-10-22/vj-lasers-v2-and-colour-themes-2026-10-24.md, section 3
(slice S1). Three sources feed the clock, in rising authority:

  db     the song database's tempo for the track playing (tempo.lookup, fused, its octave restored: database_tempo).
         Tempo only. The engine re-seeds the tracker with it on a track change, and a beat whose tempo agrees with it
         (within 4 %) says src "db"
  track  the beat tracker's predictions (beat_a by default): where the beats fall, and the tempo refined. src "track"
  tap    the hand, on the KeyLab's Tap button (CC 23 on the DAW port, to the right of Record). src "tap":
           ONE isolated tap (no tap in the 2 s before it) re-phases the beat, as BEYOND's Backspace and a ChamSys tap
           do: where it falls against the beat being shown, wrapped to half a beat either side, is the error. Under
           0.06 of a beat (about 25 ms at 150 BPM) it is tap noise and changes nothing; up to 1/8 of a beat the beat
           moves half way to the tap; further, the tap IS the beat (a hard re-anchor). One tap on a kick therefore
           fixes a tracker locked on the off-beat (hardstyle's reverse bass sits there)
           FOUR or more taps put the lights on the taps (tap-lock): a least-squares line through the run's taps gives
           tempo and phase. A tap that misses the run (a sloppy first tap, say) is dropped before the line is drawn:
           against the database's or the tracker's tempo, a tap more than 1/8 of a beat off the others and off the
           line through them (unless the database and the tracker agree with each other, when the first is
           enough); with no tempo to check against, a tap whose miss stands out from what the other taps predict (the
           lane's first build kept such a tap, so one first tap 60 ms off locked a 150 groove at 157 and the lights
           drifted for good). The references are the database's tempo and a confident tracker's (confidence 0.5 or
           more, its tempo read off the lines through its own beats and averaged, not its momentary bpm field). The
           database's is a candidate when the line through the taps kept is within 4 % of it (octave-folded): the
           spec's window. It is wider, what 25 ms of human jitter can put on the slope of the taps LEFT (2.5 sigma: 11 % for
           three, 7 % for four), only when a real outlier was dropped (it misses the line through the other taps by
           over 1/8 of a beat: against a grid a few per cent off, the end taps of a steady run drift off it as well,
           but they sit on the others' line), or when the tracker agrees with the database (then the two set the
           tempo and the taps the phase). Round 2 widened it for every short run, so four perfect taps at 142
           snapped to a database's 150 and drifted. The tracker's always has the wider window: its tempo is measured
           off the music playing, the database's is metadata. Database and tracker agreeing: the database's (the cleaner
           number). Disagreeing: the one the taps' own slope misses least, so a steady tracker that agrees with the
           taps outvotes a database a few per cent off the music (a pitched re-upload, a DJ-pitched live version, a
           title matched to the wrong song). No candidate: the tapped tempo rounded to a whole BPM (BEYOND's
           option; round_bpm=False keeps it exact). A
           snap keeps the faster of the two octaves, at any tempo (uptempo runs past the tracker's 200): taps at 150 on
           a database or tracker at 75 (half time: the fusion folds hardstyle to half, and beat_a reads 180 as 90)
           give 150, taps at 205 on beat_a's 102.3 give 205, and half-time taps (every other kick) on a database at 150
           still give 150
           when the taps STOP (two tapping intervals without one) the lights keep the hand's beat: the tracker refines
           the tempo (and its small corrections) but the hand's phase holds, until the tracker's own beats land within
           1/8 of a beat of the hand's for 8 beats running; then the phase goes back to the tracker. Where the
           tracker sat against the taps is measured at the release, tap by tap. While the hand holds it follows the
           tracker's beats with that offset, at the tempo of its LINE (see below) and only while the line is steady,
           in the hand's octave (a half-time tracker is followed at the hand's tempo, and never takes the beat back),
           within 4 %, or further when it is confident (0.5 or more) and the database does not side with the hand
           (the database sides with the hand when it agrees with the taps' OWN slope, never the snapped tempo, and
           not with the tracker): 8 %, 15 % after a run of fewer than 8 taps, any distance when the database sides
           with the tracker. Taps a
           few per cent off then stop drifting the moment the hand lets go; between follows the hand runs at its
           tempo averaged. A run of 8 or more taps at a tempo the tracker disagrees with (over 4 %, octave-folded)
           asks for a re-seed, at most one per 15 s. A new track, or 3 s of silence (a pause, not a break) with no
           tap in it, also hands the phase back

The tracker's LINE: beat_a on real music puts its beats 12-18 ms RMS around the track's straight tempo line while its
bpm field swings 147-156 at 154 BPM (measured on loopback recordings of released hardstyle). So its tempo and its
steadiness are read off where its beats LAND (its last prediction of each beat before it passes), not off the bpm
field: a least-squares line through its landed beats of the last 4 s (10 beats at least), its worst misses left off (at
most a quarter of them). Steady = at least 5 beats on it within 6 % of a beat RMS, and its newest 3 beats within 1/10
of a beat of where the beats before them said they would land (beat_a pulling its phase in moves it 0.1-0.12 of a beat
a beat). Round 1 asked for a bpm field within 0.5 % over 1.5 s instead, which real music almost never gives (open in
1-6 % of a kick section), so the hand never gave the beat back: perfect taps left the lights 25-50 ms off for good.

Every announced beat carries: src, ver (bumped on every hard re-anchor: the announced beat is off the last one's grid by
more than 1/8 of a beat, so a page re-anchors instead of slewing), and its place in the bar when it is known: with
tap_one (Daniel's call, off until he says he starts tapping on beat 1) the first tap of a run is the ONE; else bar 0.

All times are on ONE clock, the audio stream's (seconds of audio fed); the engine maps a tap's arrival onto it. Pure: no
threads, no I/O. The engine calls step() then announce() once per audio block, from the audio thread.
"""
from __future__ import annotations

import math
import statistics
from collections import deque
from typing import Deque, Dict, List, NamedTuple, Optional, Sequence, Tuple

import numpy as np

from .beathand import LOCK_TAPS, RESEED_DIFF, RESEED_GAP_S, RESEED_TAPS, TapLog, folded_ratio

RUN_GAP_S = 2.0           # a tap with no tap in this long before it starts a new run (an isolated tap)
NOISE_BEATS = 0.06        # an isolated tap this close to a beat is tap noise: nothing changes
SLEW_BEATS = 0.125        # ... up to this far the beat moves half way to the tap; further, onto the tap
SNAP = 0.04               # a tapped tempo within 4 % (octave-folded) of the database's, else the tracker's, takes it
SNAP_CONF = 0.5           # ... the tracker's only at this confidence or more
TAP_JITTER_S = 0.025      # ... or within SNAP_SIGMAS of the slope error this much human jitter gives so few taps
SNAP_SIGMAS = 2.5
SNAP_OCT = math.log2(1.0 + SNAP)          # 4 % in octaves, the unit folded_ratio answers in (0.04 octaves is 2.8 %)
RESEED_OCT = math.log2(1.0 + RESEED_DIFF)
HOLD_WIDE = 0.08          # once the taps stop, a confident tracker this close (in the hand's octave) sets the tempo
HOLD_FAR = 0.15           # ... this close after a run too short to ask for a re-seed (fewer than RESEED_TAPS taps)
HOLD_EMA = 0.1            # ... and between follows the hand runs at its tempo averaged this much per landed beat
FRESH_BEATS = 16          # the taps' own offset against the tracker sets the first follow this long after them ...
FRESH_MOVE = 0.25         # ... unless the tracker moved this much (beats) against the taps since
LINE_S = 4.0              # the tracker's LINE: drawn through its beats that landed in the last LINE_S ...
LINE_BEATS = 10           # ... or its last LINE_BEATS beats, whichever reaches further back (a half-time tracker)
LINE_MIN = 5              # ... at least this many of them on it
LINE_DROP = 0.25          # ... its worst misses left off, at most this share of the beats (a re-lock's old phase)
LINE_FLOOR = 0.03         # ... and only a miss over this much of a beat (or 3 sigma of the rest's spread)
LINE_RMS = 0.06           # steady: the beats on it sit this close to it, RMS, in beats of the lights' period ...
LINE_NEW = 3              # ... and its newest LINE_NEW beats each land within LINE_PRED of a beat of the line
LINE_PRED = 0.10          #     through the beats before them (a tracker moving its phase is not steady)
TEMPO_EMA = 0.1           # the tracker's tempo for a snap: its steady lines' tempi averaged, this much per beat
OUTLIER_BEATS = 0.125     # a tap this far off the rest of its run (in beats; see _inliers) is left out of the lock
FREE_DROP_RMS = 0.25      # ... with no tempo to check against, only if the line then misses by a quarter as much
LOCK_RMS = 0.15           # taps the fitted line misses by more than this (RMS, in beats) are not steady: no lock yet
AGREE_BEATS = 0.125       # the tracker agrees with the hand's beat within 1/8 of a beat ...
AGREE_RUN = 8             # ... for this many beats running: the phase goes back to the tracker
REANCHOR_BEATS = 0.125    # an announced beat this far off the last one's grid is a hard re-anchor (ver + 1)
SILENCE_RELEASE_S = 3.0   # this long of silence hands the phase back to the tracker
BPM_LO, BPM_HI = 60.0, 200.0   # the house tracker's range: only the tempo that SEEDS it is folded into it


def wrap(x: float) -> float:
    """A phase in beats, wrapped to [-0.5, 0.5)."""
    return (x + 0.5) % 1.0 - 0.5


def restore_octave(fused: float, raw: Sequence[float], lo: float = BPM_LO, hi: Optional[float] = BPM_HI) -> float:
    """tempo.fuse_bpm folds every database answer into 70-140 BPM to cluster them, so a 150 BPM hardstyle track comes
    back as 75 (and the `beat` command seeded beat_a at half time with it). The databases' own numbers carry the
    octave: the octave multiple of the fused tempo nearest (in octaves) to the median of the raw answers, kept inside
    lo..hi (by default the tracker's range, 60-200 BPM, both ends included: beat_a's tempo grid runs from 60 to 200).
    hi=None keeps the octave the databases said however fast (an uptempo track at 205 stays 205: database_tempo)."""
    vals = [float(v) for v in raw if v and v > 0]
    if not fused or fused <= 0 or not vals:
        return fused
    target = statistics.median(math.log2(v) for v in vals)
    bpm = float(fused) * 2.0 ** round(target - math.log2(fused))
    while hi is not None and bpm > hi:
        bpm /= 2.0
    while bpm < lo:
        bpm *= 2.0
    return bpm


def tracker_seed(bpm: Optional[float], lo: float = BPM_LO, hi: float = BPM_HI) -> Optional[float]:
    """The tempo to seed the beat tracker with: bpm folded into its range (60-200). The only tempo that is capped at
    200: a 205 BPM uptempo track seeds beat_a at 102.5 (it cannot run faster), while the database's tempo for the beat
    grid, the hand's tempo and the snap's octave stay at 205."""
    if not bpm or bpm <= 0:
        return bpm
    bpm = float(bpm)
    while bpm > hi:
        bpm /= 2.0
    while bpm < lo:
        bpm *= 2.0
    return bpm


def database_tempo(artist: str, title: str, offline: bool = False) -> Optional[Dict]:
    """The song's tempo from the database chain in tempo.py (GetSongBPM / MusicBrainz -> AcousticBrainz / Deezer),
    fused and its octave restored, past 200 too (an uptempo or frenchcore track at 205 is 205): {"bpm", "confidence",
    "sources"}; None when nothing answers or nothing agrees. Seed a tracker with tracker_seed(bpm), never bpm itself.
    Network calls: run it off the audio thread (the VJ engine's track thread does)."""
    from . import tempo as T
    found = T.lookup(artist or "", title or "", offline=offline)
    if not found:
        return None
    fused = T.fuse_bpm(found)
    if not fused.bpm or fused.confidence <= 0:
        return None
    bpm = restore_octave(float(fused.bpm), [s.bpm for s in found], hi=None)
    return {"bpm": round(bpm, 2), "confidence": round(float(fused.confidence), 2),
            "sources": [s.name for s in found]}


class TrackerLine(NamedTuple):
    """A least-squares line through the beat tracker's landed beats (tracker_line)."""
    period: float     # seconds per beat: the tracker's tempo, smoothed over the window
    t_last: float     # the line's beat at the newest landed beat: the tracker's phase, smoothed
    t_first: float    # the oldest beat it was drawn through
    rms: float        # how far the beats kept on it sit from it, RMS, in seconds
    n: int            # how many beats are on it
    new_miss: float   # how far the newest LINE_NEW beats land from the line through the beats before them (worst, s)

    def steady(self, period: Optional[float] = None) -> bool:
        """At least LINE_MIN beats on it, within LINE_RMS of a beat RMS, and its newest beats where the older ones
        said they would land (within LINE_PRED of a beat); beats of period (the lights' beat) when given, else its
        own."""
        p = period or self.period
        return self.n >= LINE_MIN and self.rms <= LINE_RMS * p and self.new_miss <= LINE_PRED * p


def _fit_line(k: np.ndarray, x: np.ndarray, keep: np.ndarray) -> Tuple[float, float]:
    A = np.vstack([k[keep], np.ones(int(keep.sum()))]).T
    (a, b), *_ = np.linalg.lstsq(A, x[keep], rcond=None)
    return float(a), float(b)


def _robust_line(k: np.ndarray, x: np.ndarray, p0: float) -> Tuple[float, float, np.ndarray, np.ndarray]:
    """(slope, intercept, each beat's miss, which beats are kept) of the least-squares line x = slope * k + b. The
    beat it misses most is left off while, against the line drawn WITHOUT it, it misses by more than LINE_FLOOR of a
    beat and more than 3 sigma of the others' spread (1.4826 x their median miss), at most LINE_DROP of the beats. (The
    line drawn with it leans toward it: one stray beat at the end of a window pulled the line enough to hide.)"""
    keep = np.ones(len(x), dtype=bool)
    left = int(LINE_DROP * len(x))
    a, b = _fit_line(k, x, keep)
    while left > 0:
        miss = np.abs(x - (a * k + b))
        j = int(np.argmax(np.where(keep, miss, -1.0)))
        rest = keep.copy()
        rest[j] = False
        a2, b2 = _fit_line(k, x, rest)
        miss2 = np.abs(x - (a2 * k + b2))
        spread = 1.4826 * float(np.median(miss2[rest]))
        if miss2[j] <= max(LINE_FLOOR * p0, 3.0 * spread):
            break
        keep, a, b = rest, a2, b2
        left -= 1
    return a, b, np.abs(x - (a * k + b)), keep


def tracker_line(beats: Sequence[float]) -> Optional[TrackerLine]:
    """The line through the tracker's landed beats (oldest first), or None with fewer than LINE_MIN. Beats are
    numbered interval by interval on the median interval (a skipped prediction counts two), the line drawn robustly
    (_robust_line: a re-lock's old phase drops out once it is a quarter of the window, and one stray beat never bends
    it), and the newest LINE_NEW beats are checked against the line through the beats before them: beat_a pulling its
    phase in moves it 0.1-0.12 of a beat a beat (seen on a released hardstyle track and on a 180 groove read at half
    time), and a line drawn through such a move is bent but can still look tidy."""
    x = np.asarray(beats, dtype=float)
    if len(x) < LINE_MIN:
        return None
    iv = np.diff(x)
    p0 = float(np.median(iv))
    if not p0 > 0:
        return None
    k = np.concatenate([[0.0], np.cumsum(np.maximum(1.0, np.round(iv / p0)))])
    a, b, miss, keep = _robust_line(k, x, p0)
    rms = float(np.sqrt(np.mean(miss[keep] ** 2)))
    new_miss = math.inf
    if len(x) >= LINE_NEW + 4:
        a2, b2, _m, _k = _robust_line(k[:-LINE_NEW], x[:-LINE_NEW], p0)
        new_miss = float(np.max(np.abs(x[-LINE_NEW:] - (a2 * k[-LINE_NEW:] + b2))))
    return TrackerLine(a, a * float(k[-1]) + b, float(x[0]), rms, int(keep.sum()), new_miss)


class BeatGrid:
    """The clock's state machine (see the module docstring). step(now, ahead, taps, silent_s) takes the tracker's
    predictions for this block (t_beat on the stream's clock), the taps since the last block and how long it has been
    silent; announce(now) gives the beat to announce now, or None; view(now) is the beats the lights will show (what the
    referee should judge). notes collects what to tell the page: tap events, status lines, and re-seed requests
    ({"t": "reseed", "bpm": x}, for the tracker's owner)."""

    def __init__(self, ahead_s: float = 0.25, tap_one: bool = False, round_bpm: bool = True):
        self.ahead_s, self.tap_one, self.round_bpm = float(ahead_s), bool(tap_one), bool(round_bpm)
        self.run = TapLog(window_s=3600.0)        # the current run of taps (cleared when a new run starts)
        self.last_tap: Optional[float] = None
        self.owner = "track"                      # who owns the beat's phase: "track" (the tracker) or "hand"
        self.locked = False                       # the hand is tapping (tap-lock): the lights follow the taps
        self.anchor: Optional[float] = None       # the hand's grid: a beat time ...
        self.period: Optional[float] = None       # ... and seconds per beat
        self.tap_bpm: Optional[float] = None      # the tempo the taps set (snapped or rounded)
        self.tap_how: Optional[str] = None        # what it snapped to: "db", "track" or "tap" (the taps' own)
        self._p_tap = 0.5                         # the interval the hand taps at (the taps stop after two of them)
        self._e0: Optional[float] = None          # holding: where the tracker's beat sits against the hand's (beats)
        self._e0_taps: Optional[float] = None     # ... as measured against the taps at the release (_first_offset)
        self._following = False                   # holding: this block the hand's grid followed the tracker
        self._p_hold: Optional[float] = None      # holding: the tempo the hand runs at between follows (seconds)
        self._keep: List[float] = []              # the taps the last lock kept
        self._own: Optional[float] = None         # ... their own slope (seconds per beat), not the snapped period
        self._hold_line: Optional["TrackerLine"] = None          # the line last folded into _p_hold
        self.db_bpm: Optional[float] = None
        self.tr: Optional[Tuple[float, float, float]] = None     # the tracker's next beat, period, confidence
        self._tr_next: Optional[float] = None     # the tracker's latest prediction of the beat coming up
        self._landed: Deque[float] = deque()      # its beats as they landed (its last word on each): the line's window
        self.line: Optional[TrackerLine] = None   # the line through them (tracker_line)
        self._tr_bpm: Optional[float] = None      # the tracker's tempo, its steady lines averaged (TEMPO_EMA) ...
        self._tr_bpm_n = 0                        # ... over this many of them
        self._now = 0.0
        self._ahead: List[dict] = []
        self.ver = 0
        self.n = 0
        self.last_sent: Optional[float] = None
        self.src: Optional[str] = None            # the source of the last announced beat
        self.bar_ref: Optional[Tuple[float, int]] = None          # a beat whose place in the bar is known (tap_one)
        self.agree = 0
        self.last_reseed = -1e9
        self.notes: List[dict] = []

    # ------------------------------------------------------------------------------------------------------ inputs
    def set_db(self, bpm: Optional[float]) -> None:
        """The song database's tempo for the track playing (None: none known)."""
        self.db_bpm = float(bpm) if bpm and bpm > 0 else None

    def new_track(self) -> None:
        """A new track: its database tempo is not known yet, and the taps and the bar belong to the old one."""
        self.db_bpm = None
        self.run.clear()
        self.last_tap = None
        self.bar_ref = None
        self.tap_bpm = self.tap_how = None
        self._give_back("track")

    def tap(self, t: float) -> None:
        """One tap of the hand, at time t on the stream's clock."""
        isolated = self.last_tap is None or t - self.last_tap > RUN_GAP_S
        self.last_tap = t
        if isolated:
            self.run.clear()
            self._keep = []                        # the last lock's taps: a re-phase must not be undone by them
        self.run.add(t)
        k = len(self.run.taps)
        if isolated:
            self._resync(t)
        elif k < LOCK_TAPS:
            self._note_tap(k, "run")
        else:
            self._lock(t)

    def step(self, now: float, ahead: Sequence[dict], taps: Sequence[float] = (), silent_s: float = 0.0) -> None:
        """Once per audio block, before announce(): the tracker's predictions, the taps since the last block (stream
        clock), how long it has been silent."""
        self._now = now
        self._ahead = list(ahead or [])
        if self._ahead:
            b = self._ahead[0]
            self.tr = (float(b["t_beat"]), 60.0 / float(b["bpm"]), float(b.get("confidence") or 0.0))
            self._land(now, self.tr[0], self.tr[1])
        else:
            self.tr = None
            self._tr_next, self.line = None, None
            self._landed.clear()
        for t in taps:
            self.tap(float(t))
        if self.locked and self.last_tap is not None and now - self.last_tap > 2.0 * self._p_tap:
            self.locked = False
            self._e0 = None                        # measured at the first follow (_hold, _first_offset)
            self._e0_taps = self._taps_vs_tracker()
            self._note_tap(len(self.run.taps), "release", bpm=self.tap_bpm)
            self._status(f"taps stopped: the lights keep your beat at {self.tap_bpm:g} BPM until the tracker agrees")
            self._maybe_reseed(now)
        # silence hands the beat back, but not while the hand is tapping into it (taps in a pause used to lock and be
        # handed straight back on every tap): only once it has been silent for 3 s since the last tap
        if silent_s >= SILENCE_RELEASE_S and (self.last_tap is None or now - self.last_tap >= SILENCE_RELEASE_S):
            self.bar_ref = None                    # the music may come back on another phase: the tapped ONE is stale
            if self.owner == "hand":
                self._give_back("silence")
        self._following = False
        if self.owner == "hand" and not self.locked:
            self._hold(now)

    # ------------------------------------------------------------------------------------------------------ output
    def announce(self, now: float) -> Optional[dict]:
        """The beat to announce now ({"lead_s", "bpm", "conf", "n", "src", "ver", "bar", "bar_src"}), or None. A beat is
        announced the first time it is within ahead_s; a beat closer than half a period to the last one announced is
        the same beat said again, and is not."""
        nxt = self._next(now)
        if nxt is None:
            return None
        t_next, period, conf, src = nxt
        lead = t_next - now
        if lead > self.ahead_s or lead < -0.03:
            return None
        if self.last_sent is not None:
            gap = t_next - self.last_sent
            if gap < 0.5 * period:
                return None
            if gap < 4.0 * period and abs(wrap(gap / period)) > REANCHOR_BEATS:
                self.ver += 1                      # off the last beat's grid: a hard re-anchor
        if self.owner == "hand" and not self.locked:
            self.agree = self.agree + 1 if self._agrees(t_next, period) else 0
            if self.agree >= AGREE_RUN:
                self._give_back("agree")           # this beat is still the hand's; the next is the tracker's
        bar, bar_src = 0, None
        if self.tap_one and self.bar_ref is not None:
            t_ref, b_ref = self.bar_ref
            bar = (b_ref - 1 + int(round((t_next - t_ref) / period))) % 4 + 1
            self.bar_ref = (t_next, bar)
            bar_src = "tap"
        self.last_sent = t_next
        self.n += 1
        self.src = src
        return {"lead_s": lead, "bpm": 60.0 / period, "conf": conf, "n": self.n, "src": src, "ver": self.ver,
                "bar": bar, "bar_src": bar_src}

    def view(self, now: float, count: int = 4) -> List[dict]:
        """The next beats the lights will show, in the tracker's prediction format (for the referee)."""
        if self.owner != "hand":
            return list(self._ahead)
        t = self._hand_next(now)
        return [{"t_beat": t + k * self.period, "bpm": 60.0 / self.period, "phase": 0.0, "confidence": 1.0}
                for k in range(count)]

    def snapshot(self) -> dict:
        return {"owner": self.owner, "locked": self.locked, "src": self.src, "ver": self.ver,
                "db_bpm": self.db_bpm, "tap_bpm": self.tap_bpm, "tap_snapped_to": self.tap_how,
                "taps": len(self.run.taps), "tap_one": self.tap_one, "round_bpm": self.round_bpm,
                "agree": self.agree, "hand_offset_beats": None if self._e0 is None else round(self._e0, 3),
                "following": self._following,
                "line_bpm": None if self.line is None else round(60.0 / self.line.period, 2),
                "line_steady": bool(self.line is not None and self.line.steady())}

    # ------------------------------------------------------------------------------------------------------ inside
    def _next(self, now: float) -> Optional[Tuple[float, float, float, str]]:
        if self.owner == "hand":
            return self._hand_next(now), self.period, 1.0, "tap"
        if self.tr is None:
            return None
        t, period, conf = self.tr
        bpm = 60.0 / period
        src = "db" if self.db_bpm and abs(bpm / self.db_bpm - 1.0) < SNAP else "track"
        return t, period, conf, src

    def _hand_next(self, now: float) -> float:
        """The hand's first beat after now."""
        return self.anchor + (math.floor((now - self.anchor) / self.period) + 1) * self.period

    def _grid(self) -> Optional[Tuple[float, float]]:
        """A beat time and the period of the beat being shown: the hand's, else the tracker's (its tempo off its line
        when that is steady: a tap that takes the beat then holds it at the tracker's smoothed tempo, not at whatever
        its bpm field reads that block)."""
        if self.owner == "hand":
            return self.anchor, self.period
        if self.tr is not None:
            return self.tr[0], self._tracker_period()
        return None

    # --- the tracker's line ---------------------------------------------------------------------------------------
    def _land(self, now: float, t_next: float, period: float) -> None:
        """The tracker's prediction of the beat coming up, this block. When it moves on to the next beat, the beat it
        replaces has landed: its last prediction goes into the window, and the line is drawn again (a few times a
        second, not every block)."""
        prev, self._tr_next = self._tr_next, t_next
        if prev is None or t_next - prev <= 0.5 * period or prev > now:
            return                                 # the same beat, refined (or moved before it landed)
        self._landed.append(prev)
        span = max(LINE_S, LINE_BEATS * period)
        while prev - self._landed[0] > span:
            self._landed.popleft()
        self.line = ln = tracker_line(self._landed)
        if ln is not None and ln.steady():
            bpm = 60.0 / ln.period
            if self._tr_bpm is None or abs(bpm / self._tr_bpm - 1.0) >= SNAP:
                self._tr_bpm, self._tr_bpm_n = bpm, 1          # a tempo of its own (a new track, an octave slip)
            else:
                self._tr_bpm_n += 1
                self._tr_bpm += max(TEMPO_EMA, 1.0 / self._tr_bpm_n) * (bpm - self._tr_bpm)

    def _steady_line(self, period: Optional[float] = None) -> Optional[TrackerLine]:
        """The tracker's line when it is steady (against the lights' beat, period, when given) and still current."""
        ln = self.line
        if ln is None or self._now - ln.t_last > 3.0 * ln.period or not ln.steady(period):
            return None
        return ln

    def _tracker_period(self) -> float:
        """The tracker's tempo, seconds per beat: off its line when that is steady, else its bpm field."""
        ln = self._steady_line()
        return ln.period if ln is not None else self.tr[1]

    def _agrees(self, t_beat: float, period: float) -> bool:
        """The tracker's own beat lands on this beat of the hand's: at the hand's tempo (within 4 %, NOT octave-folded:
        a half-time tracker never takes the beat back) and its beat nearest within 1/8 of a beat. Measured on the
        tracker's predictions themselves, whether or not the hand is following the tracker (round 1 counted only
        while it followed, and on real music it almost never did, so the beat never went back)."""
        if not self._ahead or self.tr is None or abs(self._tracker_period() / period - 1.0) >= SNAP:
            return False
        near = min((float(b["t_beat"]) for b in self._ahead), key=lambda t: abs(t - t_beat))
        return abs(wrap((near - t_beat) / period)) < AGREE_BEATS

    def _take(self, anchor: float, period: float, own: Optional[float] = None) -> None:
        """The hand takes the beat: its grid at anchor + k * period; own is the taps' own slope (seconds per beat of
        the line through the taps a lock kept), what the database is asked to agree with (_db_sides_with_hand)."""
        self.owner = "hand"
        self.anchor, self.period = float(anchor), float(period)
        self._own = None if own is None else float(own)
        self._p_hold, self._hold_line = float(period), None
        self._e0, self._e0_taps = None, None
        self.agree = 0

    def _set_period(self, now: float, period: float) -> None:
        """The hand's grid at a new tempo from the beat it shows now on (the anchor may be many beats back)."""
        beat = self._hand_next(now) - self.period
        self.anchor, self.period = beat, float(period)

    def _give_back(self, why: str) -> None:
        was = self.owner == "hand"
        self.owner = "track"
        self.locked = False
        self.anchor = self.period = None
        self._own = None
        self._e0, self._e0_taps = None, None
        self.agree = 0
        if was:
            self._note_tap(0, "return")
            self._status({"agree": "the tracker agrees with your beat: back to the tracker",
                          "silence": "silence: the beat goes back to the tracker",
                          "track": "a new track: the beat goes back to the tracker"}[why])

    def _resync(self, t: float) -> None:
        grid = self._grid()
        if grid is None:                           # nothing shown yet to re-phase; the tap may still mark the ONE
            if self.tap_one:
                self.bar_ref = (t, 1)
            self._note_tap(1, "resync")
            return
        b0, period = grid
        own = self._own if self.owner == "hand" else None        # a re-phase keeps the tapped run's own slope
        d = wrap((t - b0) / period)                # where the tap fell against the beat shown, in beats
        if abs(d) < NOISE_BEATS:
            shift, beat = 0.0, t - d * period
        elif abs(d) <= SLEW_BEATS:
            shift = d / 2.0
            beat = t - (d - shift) * period
            self._take(beat, period, own=own)
        else:
            shift, beat = d, t
            self._take(t, period, own=own)
            self._status(f"tap: the beat moved {d:+.2f} of a beat onto your tap")
        if self.tap_one:
            self.bar_ref = (beat, 1)
        self._note_tap(1, "resync", shift=round(shift, 3))

    def _references(self, p_taps: Optional[float] = None) -> List[Tuple[float, str]]:
        """The tempi a tap run may snap to, in order: the database's (unfolded: 205 for an uptempo track), then a
        confident tracker's while its line is steady against the taps' beat p_taps: its tempo smoothed, the steady
        lines' tempi averaged (_tr_bpm). On real music its bpm field swings a few per cent from block to block, and a
        snap to one block's 153.41 or 152.63 on a 154.14 track left the hand running free half a per cent off; one 4 s
        line still reads a per cent either way (156.2 on a 154.76 track)."""
        refs = []
        if self.db_bpm:
            refs.append((self.db_bpm, "db"))
        ln = self._steady_line(p_taps)
        if self.tr is not None and self.tr[2] >= SNAP_CONF and ln is not None:
            avg = self._tr_bpm
            refs.append((avg if avg and abs(avg * ln.period / 60.0 - 1.0) < SNAP else 60.0 / ln.period, "track"))
        return refs

    @staticmethod
    def _octave(ref: float, tapped: float) -> float:
        """ref in the faster of its octave and the tapped one, at any tempo. Half time is the common octave slip on
        both sides: the database fusion folds a 150 BPM track to 75, beat_a reads a 180 groove as 90 (and a 205
        uptempo groove as 102.3: its range ends at 200), while a hand often taps every other kick. So taps at double
        the reference keep their tempo, and half-time taps keep the reference's. Round 1 capped this at 200, so taps
        at 205 snapped to the half-time tracker's 102.3 and it took the beat back; only the tracker's seed is capped
        now (tracker_seed)."""
        m = max(0, round(math.log2(tapped / ref)))
        return ref * 2.0 ** m

    @staticmethod
    def _line(taps: Sequence[float], period: float) -> Tuple[np.ndarray, np.ndarray]:
        """Each tap's beat number on a grid of this period and the tap times. Numbered interval by interval (each gap
        is a whole number of beats, at least one), not from the first tap: with 30 ms of jitter the median interval
        can be 10 % off, and counting the whole run with it put the 8th tap on beat 6 (a 124 BPM lock from taps at
        150, seen while checking round 1)."""
        x = np.asarray(taps, dtype=float)
        steps = np.maximum(1.0, np.round(np.diff(x) / period))
        return np.concatenate([[0.0], np.cumsum(steps)]), x

    @classmethod
    def _phase(cls, taps: Sequence[float], period: float) -> Tuple[float, float]:
        """With the period fixed: the beat time that best fits the taps (least squares) and the RMS miss in periods
        (TapLog.tap_phase, with the taps numbered interval by interval)."""
        k, x = cls._line(taps, period)
        anchor = float(np.mean(x - k * period))
        return anchor, float(np.sqrt(np.mean(((x - (anchor + k * period)) / period) ** 2)))

    @classmethod
    def _free_period(cls, taps: Sequence[float]) -> float:
        """Seconds per beat of the run's own least-squares line. A hand taps every beat (or every other one) and
        seldom skips one, so the run is first read as one beat per gap: on the mean interval (the run's span over its
        gaps), when that numbers every gap as one beat and the line through it is steady (LOCK_RMS). Otherwise the
        beats are numbered on the median interval (a skipped beat counts two). With 30 ms of jitter four taps can
        have one gap half again as long as the median, which the median numbering alone counted as two beats (a 201
        BPM lock from taps at 150, seen while checking round 1)."""
        x = np.asarray(taps, dtype=float)
        iv = np.diff(x)
        p_mean = float(x[-1] - x[0]) / max(1, len(iv))
        if p_mean > 0:
            k, xx = cls._line(taps, p_mean)
            if np.all(np.diff(k) == 1):
                coef, r, _h = cls._lsq(k, xx)
                if math.sqrt(float(np.mean(r ** 2))) / abs(float(coef[0])) <= LOCK_RMS:
                    return float(coef[0])
        good = iv[(iv > 0.2) & (iv < 2.0)]
        return cls._slope(taps, float(np.median(good)) if len(good) else 0.5)

    @classmethod
    def _inliers(cls, taps: Sequence[float], period: float, fixed: bool) -> List[float]:
        """The taps that belong to the run, the worst miss dropped first while it is over OUTLIER_BEATS, at most a
        quarter of the run and never below 3 taps.

        fixed=True (a tempo to check against, the database's or the tracker's, in the taps' octave): the miss is
        each tap's distance from the grid of that period through the median tap, so one sloppy tap stands out at
        its full size whatever the others do.
        fixed=False (the taps alone): the miss is the tap's residual from the least-squares line through all of them,
        scaled by how much that line leans on it (r / sqrt(1 - leverage), the studentized residual's numerator: an
        end tap pulls the line toward itself, so its raw residual understates it), and the tap goes only if the line
        through the others then misses by a quarter as much (FREE_DROP_RMS) or less. Ordinary human jitter (20-30 ms)
        is then not mistaken for a sloppy tap: dropping its worst tap barely helps the fit, and dropping it anyway
        made the tempo worse (p95 tempo error 6.8 against 5.3 BPM for 6 taps of 30 ms jitter). Measured on the
        verifier's hand-alone jitter grid (128/150/180 BPM, 20 and 30 ms, 4/6/8 taps, 150 seeds), the mean p95 phase
        error is 97.0 ms against the first build's 96.8; a stricter 0.4 gave 99.2. The cost: four taps can only catch
        a tap well off (about 1/4 of a beat at the end of the run)."""
        keep = list(taps)
        cap = len(keep) // 4
        while cap > 0 and len(keep) > 3:
            k, x = cls._line(keep, period)
            if fixed:
                off = x - k * period
                miss = np.abs(off - float(np.median(off))) / period
            else:
                coef, r, h = cls._lsq(k, x)
                miss = np.abs(r) / np.sqrt(np.clip(1.0 - h, 1e-9, None)) / abs(float(coef[0]) or period)
            j = int(np.argmax(miss))
            if miss[j] <= OUTLIER_BEATS:
                break
            rest = keep[:j] + keep[j + 1:]
            if not fixed:
                k2, x2 = cls._line(rest, period)
                _c2, r2, _h2 = cls._lsq(k2, x2)
                rms = math.sqrt(float(np.sum(r ** 2)) / (len(r) - 2))
                rms2 = math.sqrt(float(np.sum(r2 ** 2)) / max(1, len(r2) - 2))
                if rms2 > FREE_DROP_RMS * rms:
                    break
            keep = rest
            cap -= 1
        return keep

    @staticmethod
    def _lsq(k: np.ndarray, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """The least-squares line x = slope * k + t0: (slope, t0), the residuals and the hat matrix's diagonal."""
        A = np.vstack([k, np.ones_like(k)]).T
        coef, *_ = np.linalg.lstsq(A, x, rcond=None)
        h = np.einsum("ij,ji->i", A, np.linalg.pinv(A.T @ A) @ A.T)
        return coef, x - A @ coef, h

    @classmethod
    def _slope(cls, taps: Sequence[float], period: float) -> float:
        """Seconds per beat of the least-squares line through the taps, beat numbers counted on a grid of period."""
        coef, _r, _h = cls._lsq(*cls._line(taps, period))
        return float(coef[0])

    @staticmethod
    def _snap_window(k: np.ndarray, period: float) -> float:
        """How far (a ratio) the slope of a line through taps numbered k (beats of period) may miss a reference's
        tempo and still be it, once a real outlier has been dropped (_stands_out; else the window is the spec's 4 %):
        4 %, or SNAP_SIGMAS times the slope error TAP_JITTER_S of human jitter gives the taps LEFT (sigma / (period *
        sqrt(sum (k - mean k)^2))), whichever is wider. Three taps left after an outlier carry about 3.5 % of slope
        noise at 20 ms (the window is 11 % at 150 BPM), four 2.2 % (7 %), six 1.2 % (4 %). With a flat 4 %, the three
        good taps of [+82, -7, +3, -40] ms at 150 sloped 4.3 % off the database's 150: the run then fell back to its own
        line, outlier and all, and locked at 165 for good (round 1's verifier: 8 of 80 such runs at 174 BPM, 7 at 150,
        every one 8-14 % off). Round 2 widened it for EVERY short run, outlier or not, so four perfect taps at 142
        snapped to a database's 150 (7 % for four taps) and drifted."""
        s = float(np.sum((k - k.mean()) ** 2))
        if s <= 0:
            return SNAP
        return max(SNAP, SNAP_SIGMAS * TAP_JITTER_S / (period * math.sqrt(s)))

    @classmethod
    def _stands_out(cls, taps: Sequence[float], keep: Sequence[float], period: float) -> bool:
        """Whether the taps _inliers dropped against a reference's grid were real outliers: each misses the line
        through the taps KEPT (their own slope, numbered on that grid) by more than OUTLIER_BEATS. Against a grid a
        few per cent off the taps, the end taps of a perfectly steady run drift off it and get dropped too, but they
        sit on the other taps' own line (round 2 dropped the first of six perfect taps at 180 against a database's 170,
        which widened the window to 5.6 % and snapped to 170: 5.56 % off). h8's sloppy first tap, [+82, -7, +3, -40]
        ms, misses the line through the other three by 0.16 of a beat at 150 (0.19 at 174): an outlier."""
        if len(keep) >= len(taps):
            return False
        k, x = cls._line(taps, period)
        kept = np.isin(x, np.asarray(keep, dtype=float))
        coef, _r, _h = cls._lsq(k[kept], x[kept])
        miss = np.abs(x[~kept] - (float(coef[0]) * k[~kept] + float(coef[1]))) / period
        return bool(np.all(miss > OUTLIER_BEATS))

    def _fit(self, taps: Sequence[float]) -> Tuple[float, str, float, List[float], float]:
        """(bpm, what it snapped to, the period of the taps' own octave, the taps kept, the taps' own slope: seconds
        per beat of the line through the taps kept) for a tap run. Each reference: drop the taps that miss its grid,
        and it is a candidate when the line through the rest is within the snap window of it.

        The database's: the spec's 4 %, wider (_snap_window, what human jitter puts on the slope of the taps left)
        only when what was dropped was a real outlier (_stands_out), or when a confident, steady tracker agrees with
        the database (within 4 %): then two sources set the tempo and the taps only the phase. Otherwise a dropped tap
        is put back: dropping the tap furthest from a reference's grid leans what is left toward that reference (six
        taps with 15 ms of jitter at 180, one dropped against a database's 170, sloped 3.1 % off it where all six
        slope 4.8 %). The database is metadata, and a few per cent off the music is ordinary (a pitched re-upload, a
        DJ-pitched live version, a title matched to the wrong song); round 2 gave it the wide window for every short
        run, so four perfect taps at 142 snapped to a database's 150.

        The tracker's (confident, its line steady): the wide window, as round 2 had it. Its tempo is measured off the
        music playing, so sloppy taps on it lean the right way (narrowed to 4 % like the database's, four taps
        [+81, +12, +16, -52] ms on a wobbly tracker at 174 fell back to their own 196 and held 137 ms off).

        The candidates are chosen by AGREEMENT (_agreeing), not database first. None: drop the taps that miss the
        run's own line, and keep its tempo."""
        p_free = self._free_period(taps)
        tapped = 60.0 / p_free
        refs = self._references(p_free)
        both = len(refs) == 2 and folded_ratio(refs[0][0], refs[1][0]) < SNAP_OCT
        found = []
        for ref, how in refs:
            bpm = self._octave(ref, tapped)
            period = 60.0 / bpm
            p_line = period * 2.0 ** round(math.log2(p_free / period))    # the taps' own octave (half time is common)
            keep = self._inliers(taps, p_line, fixed=True)
            trusted = both or how == "track" or self._stands_out(taps, keep, p_line)
            if not trusted:
                keep = list(taps)          # a drop that does not stand out may be the grid's own doing: all count
            k, x = self._line(keep, p_line)
            slope = float(self._lsq(k, x)[0][0])
            miss = abs(slope / p_line - 1.0)
            if miss < (self._snap_window(k, p_line) if trusted else SNAP):
                found.append((miss, bpm, how, p_line, keep, slope))
        pick = self._agreeing(found)
        if pick is not None:
            _miss, bpm, how, p_line, keep, slope = pick
            return bpm, how, p_line, keep, slope
        keep = self._inliers(taps, p_free, fixed=False)
        p_in = self._slope(keep, p_free)
        bpm = float(round(60.0 / p_in)) if self.round_bpm else 60.0 / p_in
        return bpm, "tap", 60.0 / bpm, keep, p_in

    @staticmethod
    def _agreeing(found: Sequence[tuple]) -> Optional[tuple]:
        """Which candidate reference a tap run snaps to ((miss, bpm, how, ...) in reference order: the database's,
        then the tracker's). While the two agree with each other (within 4 %, octave-folded), the database's (the
        spec's order: it is the cleaner number). When they DISAGREE, the one the taps' own slope misses least: a
        confident, steady tracker that agrees with the taps outvotes a database a few per cent off the music (a
        pitched re-upload, a DJ-pitched live version, a title that matched the wrong song). Round 2 tried the
        database first, so four perfect taps at 142 snapped to a database's 150 with beat_a reading 142.1 at
        confidence 1.0."""
        if not found:
            return None
        db = next((c for c in found if c[2] == "db"), None)
        tr = next((c for c in found if c[2] == "track"), None)
        if db is not None and tr is not None and folded_ratio(db[1], tr[1]) >= SNAP_OCT:
            return min((db, tr), key=lambda c: c[0])
        return found[0]

    def _lock(self, t: float) -> None:
        k = len(self.run.taps)
        g = self.run.tap_grid(t)
        if g is None:
            self._note_tap(k, "run")
            return
        bpm, how, p_line, keep, own = self._fit(self.run.taps[-12:])
        period = 60.0 / bpm
        fit = self._phase(keep, p_line)
        if fit[1] > LOCK_RMS:
            self._note_tap(k, "run")
            return
        anchor = fit[0]
        anchor += round((self.run.taps[-1] - anchor) / period) * period          # a beat at the latest tap
        first = not self.locked
        self._take(anchor, period, own=own)
        self.locked = True
        self._keep = list(keep)
        self._p_tap = p_line
        self.tap_bpm, self.tap_how = round(bpm, 2), how
        if self.tap_one:
            f = self.run.taps[0]
            self.bar_ref = (anchor + round((f - anchor) / period) * period, 1)
        if first:
            whose = {"db": " (the song database's tempo)", "track": " (the tracker's tempo)", "tap": ""}[how]
            self._status(f"tap-lock: the lights follow your taps at {self.tap_bpm:g} BPM{whose}")
        self._note_tap(k, "lock", bpm=self.tap_bpm)

    def _hold(self, now: float) -> None:
        """The hand owns the phase and is not tapping: follow the tracker's beat (its own prediction of the next one)
        at the tempo of its LINE, keeping where the hand put the beat against it (_e0); a jump (a re-lock, over 1/8 of
        a beat) is not followed. Only while the line is steady (against the lights' beat) and its tempo, in the
        hand's octave (a half-time tracker sets the tempo at the hand's), is within 4 % of the hand's, or further when
        _hold_wide allows; otherwise the hand's grid runs on at _p_hold (the hand meant another tempo; 8 taps re-seed).

        Why the tracker's own prediction and not the line's: on real music beat_a's beats wander 20-40 ms over a few
        seconds, which a 4 s line reads as a tempo a per cent or two off (156.7 on a 154.14 track); extrapolated, that
        put the lights 35-90 ms early. Its prediction carries the wander but does not amplify it (the lane's first
        build followed it, and gave the beat back on real music in 13 of 14 runs).

        Why only while the line is steady: a tracker pulling its phase in moves it 0.1-0.12 of a beat a beat (beat_a
        reading a 180 groove at half time sat on the off-beat, then re-locked onto the kicks just after the taps), and
        a hand following that moved with it, off the taps for good (round 1's finding). Its line's newest beats then
        miss where the older ones said they would land (TrackerLine.steady). Round 1 asked for a steady bpm field
        instead, which real music almost never gives.

        _e0 is set at the first follow (_first_offset): from the taps themselves when that follow comes soon after
        them, else against the beat the lights show then; afterwards a move of the tracker over 1/8 of a beat sets
        it again (the lights keep their beat). Round 1 measured it at the tracker's momentary period from the last
        tapped beat however long ago that was: 1 % of period error over 18 beats is 70 ms.

        Between follows the hand runs at _p_hold: the tapped tempo, moved a tenth of the way to the line's tempo at
        each beat that lands while it follows, so one line read a per cent off does not set the free run."""
        if self.tr is None:
            return
        t_tr = self.tr[0]
        ln = self._steady_line(self.period)
        p_f = None
        if ln is not None:
            p_f = ln.period / 2.0 ** round(math.log2(ln.period / self.period))      # in the hand's octave
            off = abs(p_f / self.period - 1.0)
            if off >= SNAP and not self._hold_wide(p_f, off):
                p_f = None
        if p_f is None:
            if self._p_hold and self.period != self._p_hold:
                self._set_period(now, self._p_hold)
            return
        if self._e0 is None:
            self._e0 = self._first_offset(t_tr, p_f)
        else:
            e = wrap((t_tr - self.anchor) / self.period)
            if abs(wrap(e - self._e0)) > REANCHOR_BEATS:
                self._e0 = e                       # a re-lock (or the lights drifted while it was not steady)
                return
        self._following = True
        if ln is not self._hold_line:
            self._hold_line = ln
            self._p_hold += HOLD_EMA * (p_f - self._p_hold)
        self.period = p_f
        self.anchor = t_tr - self._e0 * p_f

    def _first_offset(self, t_tr: float, p_f: float) -> float:
        """Where the tracker's beat (t_tr) sits against the hand's at the first follow, in beats. Within FRESH_BEATS
        of the last tap and with the taps measured against the tracker at the release (_taps_vs_tracker): that measure,
        unless the tracker has moved more than 1/4 of a beat against the taps since (their own phase, the kept taps
        refitted at the tracker's tempo p_f), and then that phase. Either way the lights go back onto the taps' beat
        whatever the hand's tempo did since: taps locked at 116 on a 128 groove had drifted 0.4 of a beat by the
        release, and sloppy taps at a section start (the tracker not steady for a few beats yet) 0.1-0.3 in the beats
        before the first follow; measured against the lights, that drift was kept for good. With no tracker during
        the taps, their own phase. Later than FRESH_BEATS, or after a single tap: against the beat the lights show
        now."""
        pairs, self._e0_taps = self._e0_taps, None
        if len(self._keep) < 2 or self.last_tap is None or self._now - self.last_tap > FRESH_BEATS * p_f:
            return wrap((t_tr - self.anchor) / self.period)
        k, x = self._line(self._keep, p_f)
        beat = float(np.mean(x - k * p_f)) + float(k[-1]) * p_f        # the kept taps' beat at the last of them
        e_taps = wrap((t_tr - beat) / p_f)
        return pairs if pairs is not None and abs(wrap(e_taps - pairs)) <= FRESH_MOVE else e_taps

    def _taps_vs_tracker(self) -> Optional[float]:
        """Where the tracker's beats sat against the taps while the hand tapped, in beats of the hand's period: the
        circular mean, over the taps kept by the lock, of each tap's nearest tracker beat (landed, or coming up) within
        half of the TRACKER's beat, wrapped to the hand's beat. Both at the same moment, so no tempo carries it across
        beats; and every tap counts against a half-time tracker too (paired only within half the hand's beat, the taps
        between its beats were left out, and the hand sat on the mean of the others, the sloppy first tap among
        them). None with fewer than two pairs."""
        beats = list(self._landed) + ([self._tr_next] if self._tr_next is not None else [])
        if not beats or not self._keep or not self.period or self.tr is None:
            return None
        tb = np.asarray(beats)
        reach = 0.5 * max(self.period, self._tracker_period())
        z = []
        for t in self._keep:
            j = int(np.argmin(np.abs(tb - t)))
            if abs(tb[j] - t) <= reach:
                z.append(np.exp(2j * math.pi * (tb[j] - t) / self.period))
        if len(z) < 2:
            return None
        return wrap(float(np.angle(np.mean(z))) / (2.0 * math.pi))

    def _hold_wide(self, p_tracker: float, off: float) -> bool:
        """A confident tracker more than 4 % off the hand (in the hand's octave) still sets the tempo once the taps
        stop, unless the database sides with the hand: at any distance when the database sides with the tracker (two
        sources against a few taps), within HOLD_FAR after a run too short to ask for a re-seed (under RESEED_TAPS:
        four or five sloppy taps can slope 10-14 % off), else within HOLD_WIDE. Round 1's verifier saw runs lock
        8-14 % off and drift for good, outside HOLD_WIDE, with a confident, right tracker."""
        if self.tr is None or self.tr[2] < SNAP_CONF or self._db_sides_with_hand(p_tracker):
            return False
        if self._db_agrees(p_tracker):
            return True
        return off < (HOLD_WIDE if len(self.run.taps) >= RESEED_TAPS else HOLD_FAR)

    def _db_agrees(self, period: float) -> bool:
        """The database's tempo is this one's, within 4 % octave-folded."""
        return bool(self.db_bpm) and folded_ratio(60.0 / period, self.db_bpm) < SNAP_OCT

    def _db_sides_with_hand(self, p_tracker: float) -> bool:
        """The database agrees with the taps' OWN slope (within 4 %, octave-folded: the line through the taps the lock
        kept, _own) and not with the tracker's tempo. Never the hand's period: after a snap to the database that is
        the database's own tempo, so it agreed with itself and kept a right tracker out for good (round 2: a database
        at 150 on a 142 groove held the lights at 150 for 40 s, 107 ms median off). With no tapped run behind the
        hand's beat (one isolated tap took it from the tracker) the database has no taps to side with.

        Asking more of the taps (the tracker further from their slope than human jitter can put it) was tried: it
        sent four jittered taps sloping toward a database 5 % off back to a right tracker more often (89 of 1080
        drifting runs at 20 ms of jitter down to 10), but let a wrong tracker 5-8 % off pull taps on a right database
        far more often (four taps: 46 of 240 up to 142), so the plain 4 % stays."""
        return self._own is not None and self._db_agrees(self._own) and not self._db_agrees(p_tracker)

    def _maybe_reseed(self, now: float) -> None:
        if len(self.run.taps) < RESEED_TAPS or not self.tap_bpm or now - self.last_reseed < RESEED_GAP_S:
            return
        if self.tr is not None and folded_ratio(self.tap_bpm, 60.0 / self._tracker_period()) <= RESEED_OCT:
            return
        self.last_reseed = now
        self.notes.append({"t": "reseed", "bpm": self.tap_bpm})

    def _note_tap(self, count: int, mode: str, bpm: Optional[float] = None, shift: Optional[float] = None) -> None:
        self.notes.append({"t": "tap", "count": int(count), "mode": mode,
                           "bpm": None if bpm is None else round(float(bpm), 2), "shift": shift})

    def _status(self, msg: str) -> None:
        self.notes.append({"t": "status", "msg": msg})
