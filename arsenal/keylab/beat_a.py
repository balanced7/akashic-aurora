"""arsenal.keylab.beat_a -- Vandor's clean real-time beat tracker (one half of the blind pair; beat_b.py is
Heimdall's). Contract and scoring: arsenal/keylab/beatbench.py. Licence firewall: stdlib + numpy only
(tests/test_keylab_beat_licence_firewall.py). Built from published methods, not from anyone's code:

  onsets   log-magnitude spectral flux (Bello et al. 2005), two weightings: full band for tempo, and a
           low-band-heavy one for phase, because kick and snare carry the beat and hats carry the off-beat
  tempo    autocorrelation of the onset curve with harmonic summation (Scheirer 1998 / Klapuri 2006 lineage),
           times a log-Gaussian prior: tight around the database seed when there is one (Ellis 2007's tempo bias
           idea), loose around 120 BPM when there is not; switched only after it wins repeatedly (hysteresis)
  phase    a comb search over the recent onset curve to lock, then a phase-locked loop: each expected beat is
           confirmed against the nearest strong onset after a short wait, nudging phase and period
           (Davies & Plumbley 2007 two-state idea; Stark et al. 2009 predict-ahead idea)

feed(block) returns OBSERVED beats (confirmed shortly after they happen, accurate); predict(now) returns the
EXPECTED next beats (ahead of time, what lights are painted from). Downbeats are not claimed (is_downbeat None).
"""
from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

HIST_S = 8.0            # onset history kept for tempo
PHASE_S = 4.0           # onset history used for the phase comb
TEMPO_EVERY_S = 0.25    # how often tempo and the phase comb are re-estimated
MIN_HIST_S = 2.0        # history needed before the first lock
BPM_LO, BPM_HI = 60.0, 200.0
SEED_SIGMA = 0.12       # octaves: a seed holds the octave and allows about +-9 %
FREE_SIGMA = 0.6        # octaves around 120 BPM when there is no seed
SWITCH_AFTER = 4        # consecutive disagreeing estimates before the tempo jumps
CONFIRM_S = 0.09        # how long after an expected beat we wait to confirm it
PLL_PHASE = 0.5         # share of the timing error taken into the beat time
PLL_PERIOD = 0.08       # share of the timing error taken into the period
ONSET_LAG_S = 0.0       # systematic detector delay (calibrated on the synthetic suite)
KICK_GATE = 0.70        # accent rule may halve tempo only when kick_likeness() >= this (see _metrical_level)


def kick_likeness(band_hist: np.ndarray) -> float:
    """0..1: how 'kick-like' the recent per-band onset flux is, by RELATIVE transient sharpness (low bands vs the
    hats band). A pure function over `band_hist` -- the most recent rows of the per-band onset-flux ring, one
    four-band vector per frame (bands: [sub/kick, snare body, mids, hats]). Module-level so it is swappable and
    testable in isolation; stdlib + numpy only (licence firewall).

    A kick/snare loop has a spiky low-band (kick body) flux -- one pulse per beat, high peak/mean -- and a
    relatively steady hats band; a hats-only (tops) loop is the opposite (spiky high band, flat low band); a
    melodic loop is sustained (low spikiness in both, but with real low-band magnitude). So the sign of
    (low-band sharpness - hats-band sharpness), folded with the low-band magnitude share, separates a body pulse
    from the rest. This is NOT the earlier failed gate (band energy share + periodicity, which gated nothing,
    medians .276 vs .275): it measures the sharpness of the ATTACK, on the onset bands.

    PARTIAL IMPROVEMENT, not a full kick detector (2026-10-22, pre-registered test, fresh seed 101, 88 loops):
    gating the unseeded accent-rule halving at threshold 0.70 lifts melodic CMLt +.071 with kick +.021 and tops
    +.001 (all non-regressive). It does NOT reach the stronger aubio parity on hats/melodic that a per-onset
    sub-150 Hz attack/decay detector would; it is labelled as a partial improvement over shipped beat_a.
    """
    h = np.asarray(band_hist, dtype=np.float64)
    if h.shape[0] < 8 or h.shape[1] < 4:
        return 0.0
    low = h[:, 0] * 2.0 + h[:, 1] * 1.5       # kick + snare body (0-400 Hz), accent-weighted
    hat = h[:, 3]                             # hats band (2500 Hz+)

    def sharp(x):
        return float(x.max() / (x.mean() + 1e-9))

    s_low, s_hat = sharp(low), sharp(hat)
    mag_ratio = float(low.max()) / (float(low.max()) + float(hat.max()) + 1e-9)
    rel = (s_low - s_hat) / (s_low + s_hat + 1e-9)   # -1..+1: positive = low band spikier than hats (kick-like)
    like = 0.55 * np.clip((rel + 1.0) / 2.0, 0.0, 1.0) + 0.45 * mag_ratio
    return float(np.clip(like, 0.0, 1.0))


class Tracker:
    def __init__(self, rate: int, hop: int, seed_bpm: Optional[float] = None):
        self.rate, self.hop = int(rate), int(hop)
        self.n_fft = 1024 if rate <= 48000 else 2048
        self.win = np.hanning(self.n_fft).astype(np.float32)
        self.ring = np.zeros(self.n_fft, dtype=np.float32)
        self.pending = np.zeros(0, dtype=np.float32)
        freqs = np.fft.rfftfreq(self.n_fft, 1.0 / self.rate)
        # Bands are AVERAGED, then weighted: summing bins let broadband hi-hat noise (hundreds of bins) outvote the
        # kick (a handful of bins) whatever the weight. Kick and snare body carry the beat; hats carry the off-beat.
        edges = [0.0, 150.0, 400.0, 2500.0, self.rate / 2 + 1]
        self.bands = [np.where((freqs >= lo) & (freqs < hi))[0] for lo, hi in zip(edges[:-1], edges[1:])]
        self.w_accent = np.array([2.0, 1.5, 1.0, 0.3])     # phase: sub/kick, snare body, mids, hats
        self.w_even = np.array([1.0, 1.0, 1.0, 0.6])       # tempo: closer to even
        self.prev = None
        self.fr = self.rate / self.hop
        n_hist = int(HIST_S * self.fr)
        self.oss_t = np.zeros(n_hist, dtype=np.float32)      # full-band onset strength (tempo)
        self.oss_p = np.zeros(n_hist, dtype=np.float32)      # low-weighted onset strength (phase)
        # Per-band onset-flux ring for the kick gate; each row is the four-band flux vector at one frame.
        self.band_hist = np.zeros((n_hist, 4), dtype=np.float32)
        self.frames = 0
        self.every = max(1, int(round(TEMPO_EVERY_S * self.fr)))
        self.seed = float(seed_bpm) if seed_bpm else None
        self.grid = np.geomspace(BPM_LO, BPM_HI, 241)
        center, sigma = (self.seed, SEED_SIGMA) if self.seed else (120.0, FREE_SIGMA)
        self.prior = np.exp(-0.5 * (np.log2(self.grid / center) / sigma) ** 2)
        self.bpm: Optional[float] = None
        self._challenger, self._challenges = None, 0
        self.period: Optional[float] = None                   # seconds
        self.next_beat: Optional[float] = None
        self.last_beat: Optional[float] = None
        self.conf = 0.0
        self._tempo_conf = 0.0
        self._miss = 0

    # --- time bookkeeping: frame n's onset lands near the centre of its analysis window -------------------------
    def _t(self, frame_index: float) -> float:
        return ((frame_index + 1) * self.hop - self.n_fft / 2) / self.rate - ONSET_LAG_S

    @property
    def now(self) -> float:
        return self.frames * self.hop / self.rate

    # --- the stream ---------------------------------------------------------------------------------------------
    def feed(self, block) -> List[dict]:
        x = np.asarray(block, dtype=np.float32).reshape(-1)
        self.pending = np.concatenate([self.pending, x]) if len(self.pending) else x
        out: List[dict] = []
        while len(self.pending) >= self.hop:
            frame, self.pending = self.pending[: self.hop], self.pending[self.hop:]
            out.extend(self._frame(frame))
        return out

    def predict(self, now: Optional[float] = None) -> List[dict]:
        if self.next_beat is None or self.period is None:
            return []
        now = self.now if now is None else now
        t = self.next_beat
        while t <= now:
            t += self.period
        return [{"t_beat": t + k * self.period, "bpm": 60.0 / self.period, "phase": 0.0,
                 "confidence": round(self.conf, 3)} for k in range(4)]

    # --- per frame --------------------------------------------------------------------------------------------
    def _frame(self, samples: np.ndarray) -> List[dict]:
        self.ring = np.roll(self.ring, -len(samples))
        self.ring[-len(samples):] = samples
        mag = np.log1p(100.0 * np.abs(np.fft.rfft(self.ring * self.win)))
        if self.prev is None:
            flux = np.zeros_like(mag)
        else:
            flux = np.maximum(mag - self.prev, 0.0)
        self.prev = mag
        self.oss_t = np.roll(self.oss_t, -1)
        self.oss_p = np.roll(self.oss_p, -1)
        self.band_hist = np.roll(self.band_hist, -1, axis=0)
        bands = np.array([flux[b].mean() if len(b) else 0.0 for b in self.bands])
        self.oss_t[-1] = float(bands @ self.w_even)
        self.oss_p[-1] = float(bands @ self.w_accent)
        self.band_hist[-1] = bands
        self.frames += 1
        out: List[dict] = []
        have = min(self.frames, len(self.oss_t)) / self.fr
        if self.frames % self.every == 0 and have >= MIN_HIST_S:
            self._update_tempo()
            if self.bpm is not None:
                self._check_phase()
        if self.next_beat is not None and self.now >= self.next_beat + CONFIRM_S:
            out.append(self._confirm())
        return out

    # --- tempo --------------------------------------------------------------------------------------------------
    def _salience(self) -> np.ndarray:
        n = min(self.frames, len(self.oss_t))
        x = self.oss_t[-n:].astype(np.float64)
        k = max(3, int(0.4 * self.fr))
        x = x - np.convolve(x, np.ones(k) / k, mode="same")   # remove the slow loudness drift
        x = np.maximum(x, 0.0)
        if not x.any():
            return np.zeros_like(self.grid)
        spec = np.fft.rfft(x, 2 * n)
        acf = np.fft.irfft(spec * np.conj(spec))[:n]
        acf = acf / (acf[0] + 1e-9)
        lags = 60.0 / self.grid * self.fr
        sal = np.zeros_like(self.grid)
        for h, w in ((1, 1.0), (2, 0.5), (3, 0.33), (4, 0.25)):
            L = lags * h
            ok = L < n - 1
            sal[ok] += w * np.interp(L[ok], np.arange(n), acf)
        return np.maximum(sal, 0.0)

    def _update_tempo(self) -> None:
        sal = self._salience() * self.prior
        if not sal.any():
            return
        i = int(np.argmax(sal))
        cand = float(self.grid[i])
        if self.seed is None:
            cand = self._metrical_level(cand)
        self._tempo_conf = float(min(1.0, (sal[i] - np.median(sal)) / (sal[i] + 1e-9) * 1.4))
        if self.bpm is None:
            self.bpm = cand
            return
        if abs(math.log2(cand / self.bpm)) < 0.04:
            self.bpm = 2 ** (0.85 * math.log2(self.bpm) + 0.15 * math.log2(cand))
            self._challenger, self._challenges = None, 0
            return
        if self._challenger is not None and abs(math.log2(cand / self._challenger)) < 0.04:
            self._challenges += 1
        else:
            self._challenger, self._challenges = cand, 1
        if self._challenges >= SWITCH_AFTER:
            self.bpm, self._challenger, self._challenges = cand, None, 0
            self.period = 60.0 / self.bpm

    def _metrical_level(self, bpm: float) -> float:
        """No seed: pick the beat level by ACCENT, not by a tempo prior. At half the candidate tempo, if the
        positions halfway between the slow beats carry much less accent than the beats themselves (hats between
        kick and snare), the slower level is the beat. Kick-and-snare on every beat keeps the faster one.

        Measured trade-off (2026-10-22, 89 stratified loops from Daniel's packs, unseeded): with this rule, kick
        loops F .73 / CMLt .60 (aubio .65 / .51); without it .62 / .50. But hats-only and melodic loops get worse
        (CMLt .29 / .28 vs .34 / .45 without). Kept because the lights mostly follow full mixes with drums; seeded
        tracking, the main path, does not use it.

        KICK GATE (2026-10-22): halving is only the right reading when the material has a body transient, so it is
        gated on kick_likeness() (relative transient sharpness of the low bands vs the hats band) at KICK_GATE.
        Below the threshold the material is hats-only or sustained, and bpm is returned unchanged. This is a
        LABELLED PARTIAL IMPROVEMENT, not a full kick detector: pre-registered on fresh seed 101 it lifts melodic
        CMLt +.071 with kick +.021 and tops +.001 (all non-regressive); it was confirmed on unseen data after being
        fitted on seed 7 (a post-hoc pick that could not confirm itself, now did)."""
        slow = bpm / 2.0
        if slow < BPM_LO:
            return bpm
        if kick_likeness(self.band_hist) < KICK_GATE:
            return bpm
        on, off, strength = self._comb_scores(60.0 / slow)
        if strength > 1.0 and on > 0 and off < 0.6 * on:
            return slow
        return bpm

    def _comb_scores(self, period_s: float, series=None):
        """(score at the best phase, score half a period away, contrast) for a comb of this period."""
        n = min(self.frames, int(PHASE_S * self.fr))
        y = (self.oss_p if series is None else series)[-n:].astype(np.float64)
        y = np.maximum(y - np.median(y), 0.0)
        if not y.any():
            return 0.0, 0.0, 0.0
        y = np.convolve(y, np.array([0.25, 0.5, 1.0, 0.5, 0.25]), mode="same")
        P = period_s * self.fr
        teeth = int(n // P)
        if teeth < 2:
            return 0.0, 0.0, 0.0
        idx = np.arange(n)
        offs = np.arange(0.0, P, 0.5)
        sc = []
        for off in offs:
            pos = (n - 1 - off) - P * np.arange(teeth)
            pos = pos[pos >= 0]
            sc.append(float(np.interp(pos, idx, y).mean()))
        sc = np.array(sc)
        j = int(np.argmax(sc))
        k = int(round((offs[j] + P / 2) % P / 0.5)) % len(sc)
        return float(sc[j]), float(sc[k]), float((sc[j] - sc.mean()) / (sc.std() + 1e-9))

    # --- phase --------------------------------------------------------------------------------------------------
    def _comb_phase(self, period_s: float):
        """Most recent beat time that best explains the recent low-weighted onsets, and how strongly."""
        n = min(self.frames, int(PHASE_S * self.fr))
        y = self.oss_p[-n:].astype(np.float64)
        y = y - np.median(y)
        y = np.maximum(y, 0.0)
        if not y.any():
            return None, 0.0
        y = np.convolve(y, np.array([0.25, 0.5, 1.0, 0.5, 0.25]), mode="same")
        P = period_s * self.fr
        teeth = int(n // P)
        if teeth < 2:
            return None, 0.0
        offsets = np.arange(0.0, P, 0.5)
        idx = np.arange(n)
        best, best_off, scores = -1.0, 0.0, []
        for off in offsets:
            pos = (n - 1 - off) - P * np.arange(teeth)
            pos = pos[pos >= 0]
            w = 0.85 ** np.arange(len(pos))
            s = float(np.dot(w, np.interp(pos, idx, y)))
            scores.append(s)
            if s > best:
                best, best_off = s, off
        scores = np.array(scores)
        strength = float((best - scores.mean()) / (scores.std() + 1e-9))
        frame_of_beat = (self.frames - 1) - best_off
        return self._t(frame_of_beat), strength

    def _check_phase(self) -> None:
        period = 60.0 / self.bpm
        t_beat, strength = self._comb_phase(period)
        if t_beat is None:
            return
        if self.next_beat is None or self.period is None:
            if strength < 1.5:
                return
            self.period = period
            self.last_beat = t_beat
            nb = t_beat + period
            while nb <= self.now - CONFIRM_S:
                nb += period
            self.next_beat = nb
            self.conf = 0.5 * self._tempo_conf + 0.5 * min(1.0, strength / 4)
            return
        # Locked: pull the period toward the tempo estimate, and re-lock if the comb strongly disagrees for long.
        self.period = 0.9 * self.period + 0.1 * period
        expected_prev = self.next_beat - self.period
        err = ((t_beat - expected_prev + self.period / 2) % self.period) - self.period / 2
        # Re-lock needs strong, PERSISTENT disagreement (about 1.5 s): ambiguous material (hats with no kick) must
        # not flip the lights between beat and off-beat.
        if strength > 3.0 and abs(err) > 0.3 * self.period:
            self._miss += 1
            if self._miss >= 6:
                self.next_beat = t_beat + self.period
                while self.next_beat <= self.now - CONFIRM_S:
                    self.next_beat += self.period
                self._miss = 0
        else:
            self._miss = max(0, self._miss - 1)

    def _confirm(self) -> dict:
        """The expected beat is CONFIRM_S in the past: look for the strongest onset near it and correct."""
        exp = self.next_beat
        P = self.period
        w = min(0.1, 0.15 * P)
        n = min(self.frames, len(self.oss_p))
        times = np.array([self._t(self.frames - n + i) for i in range(n)])
        sel = (times >= exp - w) & (times <= exp + w)
        err = 0.0
        if sel.any():
            seg = self.oss_p[-n:][sel]
            local = self.oss_p[-n:][max(0, n - int(2 * P * self.fr)):]
            j = int(np.argmax(seg))
            if seg[j] > np.median(local) + 1.5 * (np.std(local) + 1e-9) * 0.5:
                err = float(times[sel][j] - exp)
        t_beat = exp + PLL_PHASE * err
        self.period = min(60.0 / BPM_LO, max(60.0 / BPM_HI, P + PLL_PERIOD * err))
        self.last_beat = t_beat
        self.next_beat = t_beat + self.period
        hit = 1.0 if err != 0.0 else 0.0
        self.conf = 0.9 * self.conf + 0.1 * (0.5 * self._tempo_conf + 0.5 * hit)
        return {"t_beat": float(t_beat), "bpm": 60.0 / self.period, "phase": 0.0,
                "confidence": round(float(min(1.0, max(0.0, self.conf))), 3), "is_downbeat": None}
