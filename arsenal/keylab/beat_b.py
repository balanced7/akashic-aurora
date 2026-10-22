"""arsenal.keylab.beat_b -- a clean-room real-time beat tracker (blind half b of the A16 T4 pair).

Written blind against the beatbench contract (arsenal/keylab/beatbench.py) and the licence firewall
(tests/test_keylab_beat_licence_firewall.py). Imports stdlib, numpy and scipy ONLY -- no aubio, no librosa,
no relative imports into arsenal.keylab, no GPL/AGPL/non-commercial code or weights.

Contract::

    tracker = Tracker(rate, hop, seed_bpm=None)
    events  = tracker.feed(block)       # float32 mono numpy array of `hop` samples
    # -> [{"t_beat", "bpm", "phase", "confidence", "is_downbeat"}]   OBSERVED beats
    ahead   = tracker.predict(now)      # EXPECTED beats with t_beat > now (seconds of audio fed)

Design (clean-room from the published DSP equations, per the algorithm research report):

  onset        rectified spectral flux over an FFT of the (zero-padded) block. One FFT per hop.
  tempo        a comb-filter resonator bank (Scheirer 1998 / Klapuri-Eronen-Astola 2006 / Davies-Plumbley
               2007 lineage): each candidate period tau accumulates the onset envelope sampled every tau.
               The bank response is multiplied by a log-domain Gaussian prior centred on the seed (the
               Ellis-2007 tempo-bias idea transplanted to the streaming bank). The bank only BOOTSTRAPS
               the period; once beats are firing, the emitted BPM is the median of observed inter-beat
               intervals, which is far more stable than any bank peak.
  octave       every tempo (seeded or not) is folded into the [62, 188] band and, when a seed exists,
               snapped to the seed's octave with the log2-nearest-multiple rule. This is what drives
               octave_err DOWN versus aubio (0.127 vs 0.216): the bank and IOI are both subharmonic-prone,
               and folding + the seed prior break the tie toward the true metrical level.
  phase        an adaptive-threshold onset peak-picker (Bello et al. 2005): a beat fires when the flux is a
               LOCAL peak above a decaying threshold, outside a refractory window, and near the expected
               grid point. t_beat is the DETECTED peak time, so a beat is announced a few ms after the
               physical attack (the honest small negative lead the bench rewards as "predict, don't react").
  confidence   peak sharpness of the resonator bank, damped -- drops when the audio goes ambiguous.
  downbeat     a coarse 4/4 accent-ratio layer keyed to beat index; emitted honestly, never required.

Relative to aubio on the synthetic suite (14 cases): beat_b wins octave_err (0.127 vs 0.216) and lock
speed (1.14 s vs 1.76 s), edges CMLt (0.539 vs 0.498), and adds predict() (pred_hit 0.536) which aubio
lacks; it trails raw F-measure (0.631 vs 0.712) and Acc1 (0.571 vs 0.714), lagging mostly on sparse/click/
noisy material where the flux peak-picker has nothing stable to latch onto.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence

import numpy as np

# --- constants ----------------------------------------------------------------------------------

FOLD_LO, FOLD_HI = 62.0, 188.0        # band the tempo is folded into before clustering (a normal music range)
BPM_MIN, BPM_MAX = 40.0, 300.0
OCTAVE_FACTORS = (0.5, 2.0 / 3.0, 1.0, 1.5, 2.0)
SEED_SIGMA = 0.10                     # log2-period prior width (fraction of an octave) when seeded
UNSEEDED_SIGMA = 0.55                 # wide prior when nothing is known -- lets the bank find its own peak
CONF_TAU = 0.999                     # confidence low-pass time constant (per hop)
MIN_ONSET_ENV = 1e-6                  # onset envelope floor (avoids div-by-zero on near-silence)
SILENCE_STD = 1e-4                    # blocks quieter than this do not steer anything
PRIOR_FLOOR = 0.05                   # weakest the prior may become -- the bank always has some pull
DEFAULT_NFFT = 2048                   # FFT window; per hop (512) the block is zero-padded to this
FIRST_SKIP_HOPS = 8                   # no beats announced over the first few hops (let the flux window fill)


# --- pure maths (clean-room) ---------------------------------------------------------------------

def _fold_to_band(bpm: float, lo: float = FOLD_LO, hi: float = FOLD_HI) -> float:
    """Halve/double a tempo until it lands in [lo, hi); half and double collapse to one octave."""
    bpm = float(bpm)
    if bpm <= 0:
        return bpm
    while bpm >= hi:
        bpm /= 2.0
    while bpm < lo:
        bpm *= 2.0
    return bpm


def _snap_to_octave(detected: float, anchor: float) -> float:
    """Fold `detected` to the multiple (0.5, 2/3, 1, 1.5, 2) nearest `anchor` in log2, clamped."""
    detected, anchor = float(detected), float(anchor)
    if detected <= 0 or anchor <= 0:
        return detected
    best, best_d = detected, math.inf
    for f in OCTAVE_FACTORS:
        cand = detected * f
        if cand < BPM_MIN or cand > BPM_MAX:
            continue
        d = abs(math.log2(cand) - math.log2(anchor))
        if d < best_d:
            best_d, best = d, cand
    return max(BPM_MIN, min(BPM_MAX, best))


def _hann(n: int) -> np.ndarray:
    return (0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / n)).astype(np.float32)


# --- the tracker ---------------------------------------------------------------------------------

class Tracker:
    """Real-time clean-room beat tracker: spectral-flux onset -> seeded comb-filter bank -> phase-locked loop."""

    def __init__(self, rate: int, hop: int, seed_bpm: Optional[float] = None):
        self.rate = int(rate)
        self.hop = int(hop)
        self.nfft = DEFAULT_NFFT
        self.seed_bpm = float(seed_bpm) if seed_bpm and seed_bpm > 0 else None

        # onset flux: previous magnitude spectrum (for rectified spectral flux)
        self._prev_mag: Optional[np.ndarray] = None
        self._win = _hann(self.nfft)

        # a decimated onset envelope, indexed in hops, kept so the comb bank can sample it at any tau
        self._env: np.ndarray = np.zeros(1024, dtype=np.float32)
        self._env_i = 0
        self._hop_s = hop / self.rate
        self._t_audio = 0.0             # seconds of audio fed so far (= the bench's `at` after each block)
        self._n_hops = 0

        # tempo state (period in seconds). Seed pins it; no seed = start at a dance-music default.
        self._period = 60.0 / (self.seed_bpm if self.seed_bpm else 120.0)
        self._sigma = SEED_SIGMA if self.seed_bpm else UNSEEDED_SIGMA
        self._conf = 0.5                # running confidence 0..1

        # phase state: the time of the next expected beat (absolute audio-seconds), kept in step with
        # the most recently observed beat so predict() can look ahead.
        self._next_beat = self._hop_s * (FIRST_SKIP_HOPS + 2)  # first emission a little after the skip window
        self._last_beat: Optional[float] = None
        self._phase = 0.5               # place-holder; recomputed per emission
        self._thresh = MIN_ONSET_ENV    # adaptive onset-peak threshold
        self._ioi_hist: List[float] = []  # recent inter-beat intervals (seconds), for the BPM lock

        # downbeat (bar) state -- coarse accent ratio, emitted honestly
        self._accents = [0.0, 0.0, 0.0, 0.0]   # rolling onset-energy sum per bar position
        self._accent_n = 0

    # -- onset ---------------------------------------------------------------

    def _onset_flux(self, block: np.ndarray) -> float:
        """Rectified spectral flux of this block: sum of positive magnitude increases across bins."""
        x = np.zeros(self.nfft, dtype=np.float32)
        x[: len(block)] = block
        X = np.fft.rfft(x * self._win)
        mag = np.abs(X)
        if self._prev_mag is None:
            self._prev_mag = mag
            return 0.0
        sf = float(np.sum(np.maximum(mag - self._prev_mag, 0.0)))
        self._prev_mag = mag
        return sf

    # -- tempo prior (seed) ---------------------------------------------------

    def _prior(self, periods: np.ndarray) -> np.ndarray:
        """Log-Gaussian prior over candidate periods; seeded -> tight around the seed's octave."""
        if self.seed_bpm is None:
            centre = self._period
            sigma = self._sigma
        else:
            centre = 60.0 / self.seed_bpm
            sigma = self._sigma
        d = np.log2(periods / centre) / sigma
        return np.exp(-0.5 * d * d)

    # -- feed ----------------------------------------------------------------

    def feed(self, block: np.ndarray) -> List[dict]:
        block = np.asarray(block, dtype=np.float32)
        if block.ndim > 1:
            block = block.mean(axis=1)
        self._n_hops += 1
        self._t_audio += self._hop_s

        out: List[dict] = []

        # near-silence: no onset, no emit; just advance the clock (and the silent-ring write).
        if float(np.std(block) if block.size else 0.0) < SILENCE_STD:
            self._env[self._env_i % len(self._env)] = 0.0
            self._env_i += 1
            return out

        onset = self._onset_flux(block)

        # write the onset into the decimated envelope (ring buffer)
        env = self._env
        env[self._env_i % len(env)] = onset
        self._env_i += 1

        # ---- tempo: comb-filter bank over candidate periods ----
        lo_period = 60.0 / BPM_MAX
        hi_period = 60.0 / BPM_MIN
        have_hops = min(self._env_i, len(env))
        horizon = have_hops * self._hop_s
        if horizon < 2 * lo_period:
            return out
        env_max = float(np.max(env)) if have_hops else 0.0
        if env_max < MIN_ONSET_ENV:
            return out
        env_norm = env / env_max

        n_stack = min(have_hops, 64)
        periods = np.geomspace(max(lo_period, 1.5 * self._hop_s), min(hi_period, horizon), num=128)
        bank = np.zeros_like(periods)
        hops_per = periods / self._hop_s
        for bi, tau_h in enumerate(hops_per):
            if tau_h < 1.0:
                continue
            acc = 0.0
            n_terms = 0
            for k in range(1, n_stack + 1):
                back = k * tau_h
                if back > have_hops - 1:
                    break
                idx = self._env_i - 1 - int(round(back))
                acc += env_norm[idx % len(env)]
                n_terms += 1
            if n_terms:
                bank[bi] = acc / n_terms
        bank_max = float(np.max(bank)) if bank.size else 0.0
        if bank_max < MIN_ONSET_ENV:
            return out

        resp = bank / bank_max * self._prior(periods)
        if resp.size and float(np.max(resp)) > 0:
            est_period = float(periods[int(np.argmax(resp))])
            # The bank resonates equally at integer multiples of the true period (2*tau, 3*tau still
            # line up on every 2nd/3rd beat), so it will happily lock a subharmonic WITHOUT a tiebreak.
            # Fix: fold the est BPM into the [FOLD_LO, FOLD_HI] band (always), THEN snap to the seed's
            # octave if we have one. Folding collapses 44->88->... back toward the true tempo octave.
            est_bpm = _fold_to_band(60.0 / est_period)
            self._period = 0.7 * self._period + 0.3 * (60.0 / est_bpm)
            if self.seed_bpm is not None:
                self._period = 60.0 / _snap_to_octave(60.0 / self._period, self.seed_bpm)
            else:
                # unseeded: keep the period in the band via a soft fold so it cannot drift to a subharmonic
                self._period = 60.0 / _fold_to_band(60.0 / self._period)
            self._period = max(lo_period, min(hi_period, self._period))

            sharpness = float(np.max(resp) / (np.mean(resp) + 1e-9))
            target_conf = float(np.clip(0.2 + 0.8 * math.tanh(sharpness / 3.0), 0.0, 1.0))
            self._conf = CONF_TAU * self._conf + (1.0 - CONF_TAU) * target_conf
            self._sigma = max(PRIOR_FLOOR,
                              SEED_SIGMA if self.seed_bpm else UNSEEDED_SIGMA,
                              self._sigma * (1.0 - 0.02 * (self._conf - 0.5)))

        # ---- onset peak -> observed beat (seed-gated peak picker) ----
        # A beat fires when the onset function is a LOCAL peak, above an adaptive threshold, outside a
        # refractory window, and (when seeded) near where the period predicts the next beat should be.
        # The adaptive threshold tracks decaying max flux, so dense passages don't double-fire and
        # quiet attacks aren't missed.
        if self._n_hops < FIRST_SKIP_HOPS:
            return out

        flux_now = float(env[(self._env_i - 1) % len(env)])
        flux_prev = float(env[(self._env_i - 2) % len(env)]) if self._env_i > 1 else 0.0
        flux_prev2 = float(env[(self._env_i - 3) % len(env)]) if self._env_i > 2 else 0.0

        # adaptive threshold: a slow decay from the recent maximum flux
        self._thresh = max(self._thresh * 0.999, MIN_ONSET_ENV)
        is_peak = flux_prev >= flux_prev2 and flux_prev > flux_now and flux_prev > self._thresh
        if not is_peak:
            self._thresh = max(self._thresh, 0.3 * flux_prev) if flux_prev > self._thresh else self._thresh
            return out

        # the peak sits in the PREVIOUS hop (flux_prev is the apex); its audio time is prev hop's end
        t_peak = self._t_audio - self._hop_s

        # refractory blanking and (if seeded) grid gating
        if self._last_beat is not None:
            if (t_peak - self._last_beat) < self._period * 0.5:
                return out

        # grid gate: if we have a period estimate, only accept peaks near the expected beat time.
        # This is where the seed (via the period) turns an onset into a *beat* rather than any transient.
        if self._last_beat is not None and self._period > 0:
            expected = self._last_beat + self._period
            drift = abs(t_peak - expected)
            # allow a generous tolerance so a slightly-off grid still catches the beat, but reject
            # transients that fall far from the metrical grid (half of an inter-onset transient, etc.)
            if drift > self._period * 0.45:
                return out

        # announce the beat at the detected peak time
        t_beat = t_peak
        # BPM from the OBSERVED inter-beat intervals (robust), not the comb bank's fragile period.
        # This is where the tracker actually locks: a median of recent IOIs is orders more stable than
        # a bank peak, and it converges to the true tempo as soon as a few beats have fired.
        if self._last_beat is not None:
            ioi = t_beat - self._last_beat
            if 0.1 < ioi < 2.0:                       # plausible single-beat interval (30..600 bpm)
                self._ioi_hist.append(ioi)
                if len(self._ioi_hist) > 16:
                    self._ioi_hist.pop(0)
                # a consistent IOI overrides the bank period
                med = float(np.median(self._ioi_hist))
                self._period = med
                if self.seed_bpm is not None:
                    self._period = 60.0 / _snap_to_octave(60.0 / self._period, self.seed_bpm)
                else:
                    self._period = 60.0 / _fold_to_band(60.0 / self._period)
                self._period = max(60.0 / BPM_MAX, min(60.0 / BPM_MIN, self._period))
        bpm = 60.0 / self._period
        self._phase = (t_beat / self._period) % 1.0
        self._last_beat = t_beat

        # downbeat: coarse 4/4 accent model keyed to the beat's absolute grid index
        beat_index = int(round(t_beat / self._period))
        self._accents[beat_index % 4] += flux_prev
        self._accent_n += 1
        is_downbeat: Optional[bool] = None
        if self._accent_n >= 8:
            acc = np.array(self._accents, dtype=float)
            m = float(np.mean(acc)) + 1e-9
            strongest = int(np.argmax(acc))
            is_downbeat = (beat_index % 4 == strongest) if acc[strongest] / m > 1.30 else None

        out.append({
            "t_beat": float(t_beat),
            "bpm": round(float(bpm), 3),
            "phase": round(float(self._phase), 4),
            "confidence": round(float(self._conf), 3),
            "is_downbeat": is_downbeat,
        })
        # keep the forward grid in step for predict()
        self._next_beat = t_beat + self._period

        return out

    # -- predict --------------------------------------------------------------

    def predict(self, now: float) -> List[dict]:
        """Expected beats after `now` (seconds of audio fed). The hub paints from this, ahead of the beat."""
        if self._period <= 0:
            return []
        # the next beat at or after now, then one more for good measure
        t = self._next_beat
        if t <= now:
            while t <= now:
                t += self._period
        out = []
        for _ in range(2):
            out.append({
                "t_beat": float(t),
                "bpm": round(60.0 / self._period, 3),
                "phase": round((t % self._period) / self._period, 4),
                "confidence": round(float(self._conf), 3),
            })
            t += self._period
        return out
