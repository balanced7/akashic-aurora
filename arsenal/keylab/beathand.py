"""arsenal.keylab.beathand -- a hand on the beat: pad taps and a fader, read alongside FL.

Daniel (2026-10-23), while the lights ran on a hardstyle track: "I can also slide a fader to correct!" and "or i can
just tap the pad at the bpm".

  TAPS   any pad hit is "the beat is HERE". Steady taps give a tempo (median interval) and a phase; compared with
         the tracker's predicted beats they say how far the lights are off, measured by ear. Enough steady taps at
         a tempo the tracker disagrees with (octave-folded, > 4 %) ask for a RE-SEED from the hand.
  FADER  the first control change that moves is grabbed as a nudge: centre (64) = none, 4 ms a step (about
         +-250 ms over the throw), up = lights LATER.

Everything the hand does is logged with times, so a correction made by ear is also a MEASUREMENT of where the beat
really is (the answer key the referee and the bench can be checked against). Listens on every KeyLab input
(the MIDI and the DAW ports), shared with FL under the Windows MIDI Service.
"""
from __future__ import annotations

import math
import time
from typing import List, Optional, Tuple

import numpy as np

STEP_MS = 4.0
TAP_WINDOW_S = 8.0       # taps older than this are forgotten
MIN_TAPS = 5             # this many steady taps make a tempo
LOCK_TAPS = 4            # this many recent taps put the lights on the TAPS (the hand is the metronome)
RESEED_TAPS = 8          # a re-seed needs this many steady taps ...
RESEED_GAP_S = 15.0      # ... and at most one re-seed in this long (a handful of taps wobbles about 3 %, and
                         # re-seeding on every wobble restarted the tracker ~40 times in a minute, 2026-10-23)
STEADY = 0.06            # intervals within 6 % of their median count as steady
RESEED_DIFF = 0.04       # a tap tempo this far (octave-folded) from the tracker's asks for a re-seed


class Hand:
    def __init__(self, verbose: bool = True):
        from . import protocol as P
        from . import winmidi as W
        self._pad_notes = set(P._NOTE_PAD)
        self.verbose = verbose
        self.ins = []
        for name in W.inputs():
            if "keylab" in name.lower():
                try:
                    m = W.MidiIn(port=name)
                    m.start()
                    self.ins.append(m)
                except Exception as exc:                       # an input held exclusively elsewhere
                    print(f"hand: could not listen on {name!r}: {exc}")
        self.seen = [0] * len(self.ins)
        self.cc: Optional[Tuple[int, int]] = None
        self.nudge_ms = 0.0
        self.taps: List[float] = []                            # perf_counter times of pad hits
        self.log: List[tuple] = []                             # (perf_counter, kind, value)
        print(f"hand: listening on {[m.name for m in self.ins] or 'nothing'} -- tap any pad on the beat; "
              f"move a fader to grab it as a nudge (centre = none, up = lights later)")

    def poll(self) -> None:
        for i, m in enumerate(self.ins):
            ev = m.events
            while self.seen[i] < len(ev):
                t_rel, data, kind = ev[self.seen[i]]
                self.seen[i] += 1
                if kind != "short":
                    continue
                t = m._t0 + t_rel                              # back to perf_counter time
                status, d1, d2 = data[0] & 0xF0, data[1], data[2]
                # in FL's DAW mode a pad arrives on the DAW port as a note of its own (pad hit = note 11 on
                # channel 10, seen live 2026-10-23), so ANY note there is a tap; on the MIDI port only pad notes
                # count, so playing the keys never reads as tapping
                is_daw = "daw" in m.name.lower()
                if status == 0x90 and d2 > 0 and (is_daw or d1 in self._pad_notes):
                    self.taps.append(t)
                    self.log.append((t, "tap", d1))
                elif status == 0xB0:
                    if self.cc is None:
                        self.cc = (i, d1)
                        if self.verbose:
                            print(f"hand: grabbed CC {d1} on {m.name!r} as the nudge fader")
                    if self.cc == (i, d1):
                        self.nudge_ms = (d2 - 64) * STEP_MS
                        self.log.append((t, "nudge", self.nudge_ms))
        horizon = time.perf_counter() - TAP_WINDOW_S
        self.taps = [t for t in self.taps if t >= horizon]

    def tap_tempo(self, need: int = MIN_TAPS) -> Optional[float]:
        """Seconds per beat from the recent steady taps, or None."""
        if len(self.taps) < need:
            return None
        iv = np.diff(self.taps)
        iv = iv[(iv > 0.2) & (iv < 2.0)]
        if len(iv) < need - 1:
            return None
        med = float(np.median(iv))
        steady = iv[np.abs(iv / med - 1) < STEADY]
        return float(np.mean(steady)) if len(steady) >= need - 1 else None

    def tap_grid(self, now: float) -> Optional[Tuple[float, float]]:
        """While the hand is tapping, the beat IS the taps: a straight line through the recent taps (least
        squares on beat number), giving the next beat time (perf_counter) and the period. None once tapping
        has stopped for two beats."""
        taps = self.taps[-12:]
        if len(taps) < LOCK_TAPS:
            return None
        iv = np.diff(taps)
        iv = iv[(iv > 0.2) & (iv < 2.0)]
        if not len(iv):
            return None
        p0 = float(np.median(iv))
        if now - taps[-1] > 2.0 * p0:
            return None
        k = np.round((np.array(taps) - taps[0]) / p0)
        A = np.vstack([k, np.ones_like(k)]).T
        (period, t0), *_ = np.linalg.lstsq(A, np.array(taps), rcond=None)
        if not (0.2 < period < 2.0):
            return None
        n = math.floor((now - t0) / period) + 1
        return float(t0 + n * period), float(period)

    def versus(self, predicted_wall: List[float], period: float) -> Optional[dict]:
        """Where the taps fall against the beats the lights were showing (wall-clock times): circular mean.
        offset_ms > 0 = you tap AFTER the lights (the lights are early)."""
        if len(self.taps) < 3 or not predicted_wall or period <= 0:
            return None
        pw = np.array(predicted_wall)
        ph = []
        for t in self.taps:
            k = int(np.argmin(np.abs(pw - t)))
            if abs(pw[k] - t) <= period:
                ph.append(((t - pw[k]) / period + 0.5) % 1.0 - 0.5)
        if len(ph) < 3:
            return None
        z = np.exp(2j * math.pi * np.array(ph)).mean()
        return {"taps": len(ph), "offset_ms": round(float(np.angle(z) / (2 * math.pi) * period * 1000), 1),
                "steady": round(float(abs(z)), 2)}

    def close(self) -> None:
        for m in self.ins:
            try:
                m.stop(); m.close()
            except Exception:
                pass


def folded_ratio(a: float, b: float) -> float:
    """How far apart two tempi are, octave-folded (0 = same family)."""
    r = math.log2(a / b)
    return abs(r - round(r))
