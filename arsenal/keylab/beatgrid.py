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
           against the database's or the tracker's tempo, a tap more than 1/8 of a beat off the others; with no
           tempo to check against, a tap whose miss stands out from what the other taps predict (the lane's first
           build kept such a tap, so one first tap 60 ms off locked a 150 groove at 157 and the lights drifted for
           good). The tempo snaps to the database's when it is within 4 % (octave-folded), else to the tracker's
           (within 4 %, confidence 0.5 or more), else it is the tapped tempo rounded to a whole BPM (BEYOND's option;
           round_bpm=False keeps it exact). A snap keeps the faster of the two octaves: taps at 150 on a database or
           tracker at 75 (half time: the fusion folds hardstyle to half, and beat_a reads 180 as 90) give 150, and
           half-time taps (every other kick) on a database at 150 still give 150
           when the taps STOP (two tapping intervals without one) the lights keep the hand's beat: the tracker refines
           the tempo (and its small corrections) but the hand's phase holds, until the tracker agrees with it within
           1/8 of a beat for 8 beats running; then the phase goes back to the tracker. The tracker's tempo is taken in
           the hand's octave (a half-time tracker is followed at the hand's tempo, and never takes the beat back),
           within 4 %, or within 8 % when it is confident (0.5 or more) and the database does not side with the hand:
           taps a few per cent off then stop drifting the moment the hand lets go. A run of 8 or more taps at a
           tempo the tracker disagrees with (over 4 %, octave-folded) asks for a re-seed, at most one per 15 s.
           A new track, or 3 s of silence (a pause, not a break) with no tap in it, also hands the phase back

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
from typing import Deque, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .beathand import LOCK_TAPS, RESEED_DIFF, RESEED_GAP_S, RESEED_TAPS, TapLog, folded_ratio

RUN_GAP_S = 2.0           # a tap with no tap in this long before it starts a new run (an isolated tap)
NOISE_BEATS = 0.06        # an isolated tap this close to a beat is tap noise: nothing changes
SLEW_BEATS = 0.125        # ... up to this far the beat moves half way to the tap; further, onto the tap
SNAP = 0.04               # a tapped tempo within 4 % (octave-folded) of the database's, else the tracker's, takes it
SNAP_CONF = 0.5           # ... the tracker's only at this confidence or more
SNAP_OCT = math.log2(1.0 + SNAP)          # 4 % in octaves, the unit folded_ratio answers in (0.04 octaves is 2.8 %)
RESEED_OCT = math.log2(1.0 + RESEED_DIFF)
HOLD_WIDE = 0.08          # once the taps stop, a confident tracker this close (in the hand's octave) sets the tempo
STEADY_S = 1.5            # ... and only a STEADY tracker: its period has stayed within STEADY_TOL over this long
STEADY_TOL = 0.005        # (a tracker still pulling its phase in runs a per cent or two fast or slow while it does)
OUTLIER_BEATS = 0.125     # a tap this far off the rest of its run (in beats; see _inliers) is left out of the lock
FREE_DROP_RMS = 0.25      # ... with no tempo to check against, only if the line then misses by a quarter as much
LOCK_RMS = 0.15           # taps the fitted line misses by more than this (RMS, in beats) are not steady: no lock yet
AGREE_BEATS = 0.125       # the tracker agrees with the hand's beat within 1/8 of a beat ...
AGREE_RUN = 8             # ... for this many beats running: the phase goes back to the tracker
REANCHOR_BEATS = 0.125    # an announced beat this far off the last one's grid is a hard re-anchor (ver + 1)
SILENCE_RELEASE_S = 3.0   # this long of silence hands the phase back to the tracker
BPM_LO, BPM_HI = 60.0, 200.0   # the house tracker's range: a database tempo is folded into it


def wrap(x: float) -> float:
    """A phase in beats, wrapped to [-0.5, 0.5)."""
    return (x + 0.5) % 1.0 - 0.5


def restore_octave(fused: float, raw: Sequence[float], lo: float = BPM_LO, hi: float = BPM_HI) -> float:
    """tempo.fuse_bpm folds every database answer into 70-140 BPM to cluster them, so a 150 BPM hardstyle track comes
    back as 75 (and the `beat` command seeded beat_a at half time with it). The databases' own numbers carry the
    octave: the octave multiple of the fused tempo nearest (in octaves) to the median of the raw answers, kept inside
    the tracker's range (60-200 BPM, both ends included: beat_a's tempo grid runs from 60 to 200)."""
    vals = [float(v) for v in raw if v and v > 0]
    if not fused or fused <= 0 or not vals:
        return fused
    target = statistics.median(math.log2(v) for v in vals)
    bpm = float(fused) * 2.0 ** round(target - math.log2(fused))
    while bpm > hi:
        bpm /= 2.0
    while bpm < lo:
        bpm *= 2.0
    return bpm


def database_tempo(artist: str, title: str, offline: bool = False) -> Optional[Dict]:
    """The song's tempo from the database chain in tempo.py (GetSongBPM / MusicBrainz -> AcousticBrainz / Deezer),
    fused and its octave restored: {"bpm", "confidence", "sources"}; None when nothing answers or nothing agrees.
    Network calls: run it off the audio thread (the VJ engine's track thread does)."""
    from . import tempo as T
    found = T.lookup(artist or "", title or "", offline=offline)
    if not found:
        return None
    fused = T.fuse_bpm(found)
    if not fused.bpm or fused.confidence <= 0:
        return None
    bpm = restore_octave(float(fused.bpm), [s.bpm for s in found])
    return {"bpm": round(bpm, 2), "confidence": round(float(fused.confidence), 2),
            "sources": [s.name for s in found]}


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
        self._following = False                   # holding: this block the hand's grid followed the tracker
        self.db_bpm: Optional[float] = None
        self.tr: Optional[Tuple[float, float, float]] = None     # the tracker's next beat, period, confidence
        self._tr_hist: Deque[Tuple[float, float]] = deque()     # (time, the tracker's period) over the last STEADY_S
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
        self._ahead = list(ahead or [])
        if self._ahead:
            b = self._ahead[0]
            self.tr = (float(b["t_beat"]), 60.0 / float(b["bpm"]), float(b.get("confidence") or 0.0))
            self._tr_hist.append((now, self.tr[1]))
            while now - self._tr_hist[0][0] > STEADY_S:
                self._tr_hist.popleft()
        else:
            self.tr = None
            self._tr_hist.clear()
        for t in taps:
            self.tap(float(t))
        if self.locked and self.last_tap is not None and now - self.last_tap > 2.0 * self._p_tap:
            self.locked = False
            self._e0 = None
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
            same_tempo = self.tr is not None and abs(self.tr[1] / period - 1.0) < SNAP
            agrees = same_tempo and self._following and self._e0 is not None and abs(self._e0) < AGREE_BEATS
            self.agree = self.agree + 1 if agrees else 0
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
                "following": self._following}

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
        """A beat time and the period of the beat being shown: the hand's, else the tracker's."""
        if self.owner == "hand":
            return self.anchor, self.period
        if self.tr is not None:
            return self.tr[0], self.tr[1]
        return None

    def _take(self, anchor: float, period: float) -> None:
        self.owner = "hand"
        self.anchor, self.period = float(anchor), float(period)
        self._e0 = None
        self.agree = 0

    def _give_back(self, why: str) -> None:
        was = self.owner == "hand"
        self.owner = "track"
        self.locked = False
        self.anchor = self.period = None
        self._e0 = None
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
        d = wrap((t - b0) / period)                # where the tap fell against the beat shown, in beats
        if abs(d) < NOISE_BEATS:
            shift, beat = 0.0, t - d * period
        elif abs(d) <= SLEW_BEATS:
            shift = d / 2.0
            beat = t - (d - shift) * period
            self._take(beat, period)
        else:
            shift, beat = d, t
            self._take(t, period)
            self._status(f"tap: the beat moved {d:+.2f} of a beat onto your tap")
        if self.tap_one:
            self.bar_ref = (beat, 1)
        self._note_tap(1, "resync", shift=round(shift, 3))

    def _references(self) -> List[Tuple[float, str]]:
        """The tempi a tap run may snap to, in order: the database's, then a confident tracker's."""
        refs = []
        if self.db_bpm:
            refs.append((self.db_bpm, "db"))
        if self.tr is not None and self.tr[2] >= SNAP_CONF:
            refs.append((60.0 / self.tr[1], "track"))
        return refs

    @staticmethod
    def _octave(ref: float, tapped: float) -> float:
        """ref in the faster of its octave and the tapped one (never past the tracker's 200 BPM). Half time is the
        common octave slip on both sides: the database fusion folds a 150 BPM track to 75 and beat_a reads a 180
        groove as 90, while a hand often taps every other kick. So taps at double the reference keep their tempo, and
        half-time taps keep the reference's."""
        m = max(0, round(math.log2(tapped / ref)))
        while m > 0 and ref * 2.0 ** m > BPM_HI:
            m -= 1
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

    def _fit(self, taps: Sequence[float]) -> Tuple[float, str, float, List[float]]:
        """(bpm, what it snapped to, the period of the taps' own octave, the taps kept) for a tap run. Each reference
        in turn: drop the taps that miss its grid, and snap when a line through the rest is within 4 % of it. None
        agrees: drop the taps that miss the run's own line, and keep its tempo."""
        p_free = self._free_period(taps)
        tapped = 60.0 / p_free
        for ref, how in self._references():
            bpm = self._octave(ref, tapped)
            period = 60.0 / bpm
            p_line = period * 2.0 ** round(math.log2(p_free / period))    # the taps' own octave (half time is common)
            keep = self._inliers(taps, p_line, fixed=True)
            if folded_ratio(60.0 / self._slope(keep, p_line), bpm) < SNAP_OCT:
                return bpm, how, p_line, keep
        keep = self._inliers(taps, p_free, fixed=False)
        p_in = self._slope(keep, p_free)
        bpm = float(round(60.0 / p_in)) if self.round_bpm else 60.0 / p_in
        return bpm, "tap", 60.0 / bpm, keep

    def _lock(self, t: float) -> None:
        k = len(self.run.taps)
        g = self.run.tap_grid(t)
        if g is None:
            self._note_tap(k, "run")
            return
        bpm, how, p_line, keep = self._fit(self.run.taps[-12:])
        period = 60.0 / bpm
        fit = self._phase(keep, p_line)
        if fit[1] > LOCK_RMS:
            self._note_tap(k, "run")
            return
        anchor = fit[0]
        anchor += round((self.run.taps[-1] - anchor) / period) * period          # a beat at the latest tap
        first = not self.locked
        self._take(anchor, period)
        self.locked = True
        self._p_tap = p_line
        self.tap_bpm, self.tap_how = round(bpm, 2), how
        if self.tap_one:
            f = self.run.taps[0]
            self.bar_ref = (anchor + round((f - anchor) / period) * period, 1)
        if first:
            whose = {"db": " (the song database's tempo)", "track": " (the tracker's tempo)", "tap": ""}[how]
            self._status(f"tap-lock: the lights follow your taps at {self.tap_bpm:g} BPM{whose}")
        self._note_tap(k, "lock", bpm=self.tap_bpm)

    def _steady(self, now: float) -> bool:
        """The tracker's period has stayed within STEADY_TOL for the last STEADY_S."""
        h = self._tr_hist
        if not h or now - h[0][0] < 0.9 * STEADY_S:
            return False
        ps = [p for _t, p in h]
        return max(ps) / min(ps) - 1.0 < STEADY_TOL

    def _hold(self, now: float) -> None:
        """The hand owns the phase and is not tapping: follow the tracker's tempo and its small corrections, keeping
        where the hand put the beat against it; a jump of the tracker (a re-lock, over 1/8 of a beat) is not
        followed. The tracker's period is taken in the hand's octave (a half-time tracker sets the tempo at the
        hand's), within 4 %, or within HOLD_WIDE when the tracker is confident and the database does not side with
        the hand. Further off, the hand's grid runs on its own (the hand meant another tempo; 8 taps re-seed).

        Only a STEADY tracker is followed (_steady). A tracker still pulling its phase in does it by running fast or
        slow for a few seconds (beat_a reading a 180 groove at half time moved its beat 140 ms that way just after the
        taps), and a hand following it moved with it, off the taps for good. Until it steadies the hand's grid runs
        on at the tapped tempo, which the snap has usually made right.

        The first time it follows, where the tracker's beat sits against the hand's is measured from the hand's last
        tapped beat at the TRACKER's tempo, not at the hand's: a hand a few per cent off has drifted a good part of a
        beat by the time the taps are known to have stopped (the lane's first build ran free at that tempo)."""
        if self.tr is None or not self._steady(now):
            return
        t_tr, p_tr, conf = self.tr
        p_f = p_tr / 2.0 ** round(math.log2(p_tr / self.period))     # the tracker's period in the hand's octave
        off = abs(p_f / self.period - 1.0)
        if off >= SNAP and not (off < HOLD_WIDE and conf >= SNAP_CONF and not self._db_sides_with_hand(p_f)):
            return
        self._following = True
        if self._e0 is None:
            self._e0 = wrap((t_tr - self.anchor) / p_f)
        else:
            e = wrap((t_tr - self.anchor) / self.period)
            if abs(wrap(e - self._e0)) > REANCHOR_BEATS:
                self._e0 = e
                return
        self.period = p_f
        self.anchor = t_tr - self._e0 * p_f

    def _db_sides_with_hand(self, p_tracker: float) -> bool:
        """The database agrees with the hand's tempo (within 4 %, octave-folded) and not with the tracker's."""
        if not self.db_bpm:
            return False
        return (folded_ratio(60.0 / self.period, self.db_bpm) < SNAP_OCT
                and folded_ratio(60.0 / p_tracker, self.db_bpm) >= SNAP_OCT)

    def _maybe_reseed(self, now: float) -> None:
        if len(self.run.taps) < RESEED_TAPS or not self.tap_bpm or now - self.last_reseed < RESEED_GAP_S:
            return
        if self.tr is not None and folded_ratio(self.tap_bpm, 60.0 / self.tr[1]) <= RESEED_OCT:
            return
        self.last_reseed = now
        self.notes.append({"t": "reseed", "bpm": self.tap_bpm})

    def _note_tap(self, count: int, mode: str, bpm: Optional[float] = None, shift: Optional[float] = None) -> None:
        self.notes.append({"t": "tap", "count": int(count), "mode": mode,
                           "bpm": None if bpm is None else round(float(bpm), 2), "shift": shift})

    def _status(self, msg: str) -> None:
        self.notes.append({"t": "status", "msg": msg})
