"""arsenal.keylab.beatref -- the referee: how ON BEAT is a tracker right now, with no answer key.

Daniel (2026-10-23): "hitting the same bpm twice should re-enforce something, do we have any way to get a good
guesser of how on beat we are?"

The referee watches the audio and a tracker's PREDICTIONS (what predict() said before the moment came). Each time a
kick-band onset arrives, it measures where that onset fell relative to the nearest beat the tracker had predicted
for it, as a phase in [-0.5, 0.5) of a beat. Over the last few beats (strength-weighted, circular statistics):

    consistency  0..1   do the kicks keep landing at the SAME place relative to our beats? (resultant length)
    offset_ms    signed  where that place is: + = the kicks land AFTER our beats (we are early)
    on_beat     -1..1   consistency x cos(offset): 1 = kicks right on our beats, 0 = lost, < 0 = on the off-beat
    agree               the tempo the kicks themselves repeat at (their own period), and whether the tracker's
                        BPM matches it; matching again and again REINFORCES (Daniel's "same bpm twice"): the
                        streak of agreeing checks is reported, a disagreement resets it

It assumes the kick marks the beat, which holds for most electronic dance music (hardstyle, house, techno, DnB) and
much pop; on music without a kick it says "no kick" rather than guessing. Pure numpy, causal, cheap.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Deque, Dict, List, Optional

import numpy as np

KICK_HZ = 150.0          # the kick band's upper edge
WINDOW_BEATS = 8         # judge over about this many beats
MIN_KICKS = 4            # fewer onsets than this in the window: no verdict
AGREE_TOL = 0.02         # tempo agreement within 2 %, octave-folded


class Referee:
    def __init__(self, rate: int, hop: int = 512):
        self.rate, self.hop = rate, hop
        self.n_fft = 2048 if rate > 32000 else 1024
        self.win = np.hanning(self.n_fft).astype(np.float32)
        self.ring = np.zeros(self.n_fft, dtype=np.float32)
        freqs = np.fft.rfftfreq(self.n_fft, 1.0 / rate)
        self.low = np.where((freqs > 30.0) & (freqs < KICK_HZ))[0]
        self.prev = None
        self.frames = 0
        self.flux: Deque[float] = deque(maxlen=int(3.0 * rate / hop))
        self.cand: Deque[float] = deque(maxlen=3)          # last flux values, for a 1-frame-late peak pick
        self.kicks: Deque[tuple] = deque(maxlen=64)         # (time, strength, phase vs predicted beat)
        self.pred: Deque[float] = deque(maxlen=64)          # predicted beat times, as announced BEFORE they came
        self.period = None
        self.streak = 0
        self.last_agree_check = 0.0

    @property
    def now(self) -> float:
        return self.frames * self.hop / self.rate

    def predicted(self, beats: List[dict]) -> None:
        """Hand the referee what the tracker predicts (call with predict()'s output, before the audio arrives)."""
        for b in beats or []:
            t = float(b["t_beat"])
            if t <= self.now:
                continue
            if not self.pred or abs(t - self.pred[-1]) > 0.05:
                if self.pred and t < self.pred[-1]:
                    # a revised prediction replaces the later ones it overrides
                    while self.pred and self.pred[-1] > t + 0.05:
                        self.pred.pop()
                self.pred.append(t)
            if b.get("bpm"):
                self.period = 60.0 / float(b["bpm"])

    def feed(self, block: np.ndarray) -> None:
        x = np.asarray(block, dtype=np.float32).reshape(-1)
        self.ring = np.roll(self.ring, -len(x))
        self.ring[-len(x):] = x[-self.n_fft:] if len(x) > self.n_fft else x
        mag = np.log1p(100.0 * np.abs(np.fft.rfft(self.ring * self.win)))
        f = 0.0 if self.prev is None else float(np.maximum(mag[self.low] - self.prev[self.low], 0.0).mean())
        self.prev = mag
        self.frames += 1
        self.flux.append(f)
        self.cand.append(f)
        if len(self.cand) == 3 and len(self.flux) > 20:
            a, b, c = self.cand
            thr = float(np.median(self.flux)) + 1.5 * float(np.std(self.flux))
            if b > a and b >= c and b > thr:
                t = self.now - 1.5 * self.hop / self.rate - self.n_fft / 2 / self.rate
                self._kick(t, b)

    def _kick(self, t: float, strength: float) -> None:
        if not self.pred or self.period is None:
            return
        # the nearest PREDICTED beat (predictions are kept only as announced in advance)
        p = min(self.pred, key=lambda x: abs(x - t))
        ph = ((t - p) / self.period + 0.5) % 1.0 - 0.5
        if abs(t - p) > self.period:          # no prediction near this kick (gap, track change)
            return
        self.kicks.append((t, strength, ph))

    def verdict(self) -> Dict:
        if self.period is None:
            return {"state": "no prediction yet"}
        horizon = self.now - WINDOW_BEATS * self.period
        recent = [(t, s, ph) for t, s, ph in self.kicks if t >= horizon]
        if len(recent) < MIN_KICKS:
            return {"state": "no kick", "kicks": len(recent)}
        w = np.array([s for _, s, _ in recent])
        ph = np.array([p for _, _, p in recent])
        z = (w * np.exp(2j * math.pi * ph)).sum() / w.sum()
        consistency = float(abs(z))
        offset = float(np.angle(z) / (2 * math.pi))           # beats
        on_beat = consistency * math.cos(2 * math.pi * offset)
        out = {"state": "ok", "kicks": len(recent), "consistency": round(consistency, 3),
               "offset_ms": round(offset * self.period * 1000, 1), "on_beat": round(on_beat, 3),
               "tracker_bpm": round(60.0 / self.period, 2)}
        kp = self._kick_period(recent)
        if kp:
            r = (60.0 / kp) / (60.0 / self.period)
            fold = abs(math.log2(r) - round(math.log2(r)))
            agree = fold < math.log2(1 + AGREE_TOL)
            if self.now - self.last_agree_check >= self.period:
                self.streak = self.streak + 1 if agree else 0
                self.last_agree_check = self.now
            out.update({"kick_bpm": round(60.0 / kp, 2), "agree": agree, "agree_streak": self.streak})
        return out

    def _kick_period(self, recent) -> Optional[float]:
        """The kick band's OWN repetition period, independent of the tracker -- the second witness. The kick-band
        flux of the last few seconds is compared with itself shifted by every lag near the tracker's beat (and
        its half and double): the lag where it matches itself best is how often the kicks repeat. (Counting
        gaps between onsets fails on a hardstyle kick, which fires several onsets per hit.)"""
        if self.period is None or len(self.flux) < int(2.0 * self.rate / self.hop):
            return None
        env = np.array(self.flux, dtype=float)
        env = env - env.mean()
        fps = self.rate / self.hop
        best = None
        for mult in (0.5, 1.0, 2.0):
            base = self.period * mult * fps
            lo, hi = int(base * 0.8), int(math.ceil(base * 1.2))
            if hi >= len(env) // 2 or lo < 2:
                continue
            lags = np.arange(lo, hi + 1)
            ac = np.array([float(env[:-L] @ env[L:]) / (len(env) - L) for L in lags])
            i = int(np.argmax(ac))
            if 0 < i < len(ac) - 1:
                y0, y1, y2 = ac[i - 1], ac[i], ac[i + 1]
                den = y0 - 2 * y1 + y2
                shift = 0.5 * (y0 - y2) / den if den < 0 else 0.0
            else:
                shift = 0.0
            lag_s = (lags[i] + shift) / fps / mult          # folded back to the tracker's beat octave
            score = ac[i] / (float(env @ env) / len(env) + 1e-12)
            if best is None or score > best[0]:
                best = (score, lag_s)
        if best is None or best[0] < 0.1:
            return None
        return float(best[1])
