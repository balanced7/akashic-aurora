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
           tempo and phase. The tempo snaps to the database's when it is within 4 % (octave-folded), else to the
           tracker's (within 4 %, confidence 0.5 or more), else it is the tapped tempo rounded to a whole BPM (BEYOND's
           option; round_bpm=False keeps it exact)
           when the taps STOP (two tapping intervals without one) the lights keep the hand's beat: the tracker refines
           the tempo (and its small corrections) but the hand's phase holds, until the tracker agrees with it within
           1/8 of a beat for 8 beats running; then the phase goes back to the tracker. A run of 8 or more taps at a
           tempo the tracker disagrees with (over 4 %, octave-folded) asks for a re-seed, at most one per 15 s.
           A new track, or 3 s of silence (a pause, not a break), also hands the phase back

Every announced beat carries: src, ver (bumped on every hard re-anchor: the announced beat is off the last one's grid by
more than 1/8 of a beat, so a page re-anchors instead of slewing), and its place in the bar when it is known: with
tap_one (Daniel's call, off until he says he starts tapping on beat 1) the first tap of a run is the ONE; else bar 0.

All times are on ONE clock, the audio stream's (seconds of audio fed); the engine maps a tap's arrival onto it. Pure: no
threads, no I/O. The engine calls step() then announce() once per audio block, from the audio thread.
"""
from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional, Sequence, Tuple

from .beathand import LOCK_TAPS, RESEED_DIFF, RESEED_GAP_S, RESEED_TAPS, TapLog, folded_ratio

RUN_GAP_S = 2.0           # a tap with no tap in this long before it starts a new run (an isolated tap)
NOISE_BEATS = 0.06        # an isolated tap this close to a beat is tap noise: nothing changes
SLEW_BEATS = 0.125        # ... up to this far the beat moves half way to the tap; further, onto the tap
SNAP = 0.04               # a tapped tempo within 4 % (octave-folded) of the database's, else the tracker's, takes it
SNAP_CONF = 0.5           # ... the tracker's only at this confidence or more
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
    the tracker's range."""
    vals = [float(v) for v in raw if v and v > 0]
    if not fused or fused <= 0 or not vals:
        return fused
    target = statistics.median(math.log2(v) for v in vals)
    bpm = float(fused) * 2.0 ** round(target - math.log2(fused))
    while bpm >= hi:
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
        self.db_bpm: Optional[float] = None
        self.tr: Optional[Tuple[float, float, float]] = None     # the tracker's next beat, period, confidence
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
        else:
            self.tr = None
        for t in taps:
            self.tap(float(t))
        if self.locked and self.last_tap is not None and now - self.last_tap > 2.0 * self._p_tap:
            self.locked = False
            self._e0 = None
            self._note_tap(len(self.run.taps), "release", bpm=self.tap_bpm)
            self._status(f"taps stopped: the lights keep your beat at {self.tap_bpm:g} BPM until the tracker agrees")
            self._maybe_reseed(now)
        if self.owner == "hand" and silent_s >= SILENCE_RELEASE_S:
            self._give_back("silence")
        if self.owner == "hand" and not self.locked:
            self._hold()

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
            agrees = same_tempo and self._e0 is not None and abs(self._e0) < AGREE_BEATS
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
                "agree": self.agree, "hand_offset_beats": None if self._e0 is None else round(self._e0, 3)}

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

    def _snap(self, bpm: float) -> Tuple[float, str]:
        if self.db_bpm and folded_ratio(bpm, self.db_bpm) < SNAP:
            return self.db_bpm, "db"
        if self.tr is not None and self.tr[2] >= SNAP_CONF and folded_ratio(bpm, 60.0 / self.tr[1]) < SNAP:
            return 60.0 / self.tr[1], "track"
        return (float(round(bpm)) if self.round_bpm else bpm), "tap"

    def _lock(self, t: float) -> None:
        k = len(self.run.taps)
        g = self.run.tap_grid(t)
        if g is None:
            self._note_tap(k, "run")
            return
        p_tap = g[1]
        bpm, how = self._snap(60.0 / p_tap)
        period = 60.0 / bpm
        p_line = period * 2.0 ** round(math.log2(p_tap / period))   # the taps' own octave (half time is common)
        fit = self.run.tap_phase(p_line, self.run.taps[-12:])
        if fit is None or fit[1] > LOCK_RMS:
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

    def _hold(self) -> None:
        """The hand owns the phase and is not tapping: follow the tracker's tempo and its small corrections, keeping
        where the hand put the beat against it; a jump of the tracker (a re-lock, over 1/8 of a beat) is not
        followed."""
        if self.tr is None:
            return
        t_tr, p_tr, _conf = self.tr
        if abs(p_tr / self.period - 1.0) >= SNAP:
            return                                 # another tempo (an octave off): the hand's grid runs on its own
        e = wrap((t_tr - self.anchor) / self.period)
        if self._e0 is None or abs(wrap(e - self._e0)) > REANCHOR_BEATS:
            self._e0 = e
            return
        self.period = p_tr
        self.anchor = t_tr - self._e0 * p_tr

    def _maybe_reseed(self, now: float) -> None:
        if len(self.run.taps) < RESEED_TAPS or not self.tap_bpm or now - self.last_reseed < RESEED_GAP_S:
            return
        if self.tr is not None and folded_ratio(self.tap_bpm, 60.0 / self.tr[1]) <= RESEED_DIFF:
            return
        self.last_reseed = now
        self.notes.append({"t": "reseed", "bpm": self.tap_bpm})

    def _note_tap(self, count: int, mode: str, bpm: Optional[float] = None, shift: Optional[float] = None) -> None:
        self.notes.append({"t": "tap", "count": int(count), "mode": mode,
                           "bpm": None if bpm is None else round(float(bpm), 2), "shift": shift})

    def _status(self, msg: str) -> None:
        self.notes.append({"t": "status", "msg": msg})
