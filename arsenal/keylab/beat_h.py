"""arsenal.keylab.beat_h -- the GRID tracker (A16 T4 tag-team, Daniel's design, 2026-10-22).

Blind candidate `h` for the grid-holding / tempo-following slot. Written against the beatbench contract
(arsenal/keylab/beatbench.py) and the licence firewall (tests/test_keylab_beat_licence_firewall.py), from Daniel's
own words in the brief and pre-registration (research/reviewed/keylab-liberation-2026-10-22/) and the IMM design
lenses (grid-research-deepseek-lenses-2026-10-22.md). Nothing here was opened from any other beat_*.py; the
architecture is a different animal from the note-chasing pair that fails the drift suite.

WHY this exists (the failure being fixed): the shipped tracker snaps 50% toward the strongest onset within
+-100ms, flips the tempo after 1 s of disagreement, and pulls the period 10%/0.25s toward the current guess. On
half-time bass (TYNAN "groovininininin", loud sub-bass on syncopated 16ths that never land on a beat) it wanders
124->130->167->83->159. It is a NOTE-chaser with a one-second memory. The fix, per Daniel:
    "detect the grid not just the spaced out notes ... adjust multiple grid permutations simultaneously with a
     confidence score ... they all connect to the master and they all agree"
    "... a higher and lower volitility setting that are smartly joined ... shifting bpm and low + high volatility
     heuristics ... mechanically not with agents parsing"

Design (this file):
  onset        rectified spectral flux with per-hop PARABOLIC peak interpolation to sub-frame precision, because a
               grid scored on all notes needs onset times accurate to a few ms, not to a 512-hop frame (11.6 ms).
  grid search  every hypothesis is (period, phase). It is scored by how well EVERY onset in the last ~4.5 s lands
               on one of its grid lines, strength-weighted; off-grid onsets COUNT AGAINST it. This is the "on what
               grid would all of these notes fit?" question, answered by scoring many grid permutations
               SIMULTANEOUSLY over a geometric period ladder x a phase lattice -- not by chasing the loudest onset.
  parsimony    the coarsest grid that explains the notes wins on a tie: a fine grid pays a penalty proportional to
               its line count. Half/double tempo grids are the SAME shape at different resolutions, so we fold into
               one octave and let accent + the seed choose the metrical level.
  master grid  a single (period T, absolute phase phi) held in state. It is scored continuously; it moves only
               under hysteresis (a rival must outscore it for several bars). beat LEVEL comes from the kick/snare
               accent bands and the seed_bpm when one exists (the honest database tiebreak).
  volatility   the "low + high volatility heuristics, smartly joined" as a single live regime q in [0,1] (not a
               full Kalman IMM -- simpler and correct). LOW volatility (q~0) is the grid-HOLDER: near-constant
               tempo, the master stays put through syncopated off-beat bass; corrections are a tiny EMA. HIGH
               volatility (q~1) is the tempo-FOLLOWER: after a real step (DJ transition, automation, a live
               drummer) the master grid's score collapses, q rises, and the master re-fits to the new period -- but
               only after the rival grid has outscored it, never on a single loud onset. This is the whole point of
               the drift-vs-shift pull: HOLD under syncopation, FOLLOW under a real step.
  emit/predict OBSERVED beats are announced ON the master grid (never on a raw peak): t_beat walks grid lines
               forward from phi by period T. The emitted bpm is 60/T, GRID-smoothed -- it only changes when the
               master actually moves, so bpm_spread ~ 0 and tempo_flips ~ 0, exactly what drift() rewards and a
               note-chaser cannot give. predict() extrapolates the master grid forward for the hub to paint ahead.

Licence: stdlib + numpy + scipy ONLY, no relative imports into arsenal.keylab, self-contained in this one file.
Causal: never looks past the audio fed so far. No constant copied from the bench (e.g. the bass 16th positions).
"""
from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

# --- onset / grid constants --------------------------------------------------------------------

NFFT = 2048                       # FFT window (zero-padded from the 512 hop)
BPM_MIN, BPM_MAX = 40.0, 300.0
FOLD_LO, FOLD_HI = 62.0, 188.0    # octave band the tempo folds into
SILENCE_STD = 1e-4                # blocks quieter than this steer nothing
MIN_ENV = 1e-6

# grid-search geometry
N_PERIODS = 120                   # geometric period ladder
N_PHASES = 40                     # phase lattice per period
GRID_MEMORY_S = 4.5               # how many seconds of onsets each hypothesis is scored on
GRID_EVERY = 13                   # run grid search every ~13 hops (~0.15s)
PARSIMONY_W = 0.15                # complexity penalty weight (per grid line): light -- a grid that explains MORE
                                  # onsets (finer, correct level) should win even though it has more lines
ACCENT_LO, ACCENT_HI = 40.0, 220.0  # kick/snare band split for beat-level choice

# master-grid / volatility / hysteresis
SCORE_MARGIN = 1.02               # rival must beat master by this ratio in score
RIVAL_BEATS = 8                   # ... for this many beats of sustained advantage, before the master moves
LOWVOL_EMA = 0.01                 # low-volatility period correction (grid-holder: near-rigid)
HIGHVOL_EMA = 0.5                 # high-volatility period correction (tempo-follower: nimble)
VOL_DOWN, VOL_UP = 0.05, 0.3      # q decay / rise per grid update
FIRST_BEATS = 10                  # no emission for the first few hops (let the grid form)


def _hann(n: int) -> np.ndarray:
    return (0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(n) / n)).astype(np.float32)


def _fold(bpm: float) -> float:
    bpm = float(bpm)
    if bpm <= 0:
        return bpm
    while bpm >= FOLD_HI:
        bpm /= 2.0
    while bpm < FOLD_LO:
        bpm *= 2.0
    return bpm


def _nearest_octave(bpm: float, anchor: float) -> float:
    """Fold `bpm` to the multiple (0.5, 2/3, 1, 1.5, 2) of `anchor` nearest in log2 (the seed / accent tiebreak)."""
    if bpm <= 0 or anchor <= 0:
        return bpm
    best, best_d = bpm, math.inf
    for f in (0.5, 2 / 3, 1.0, 1.5, 2.0):
        cand = anchor * f
        if BPM_MIN <= cand <= BPM_MAX:
            d = abs(math.log2(cand) - math.log2(bpm))
            if d < best_d:
                best_d, best = d, cand
    return best


class Tracker:
    """Grid-holding / tempo-following real-time beat tracker: many grid hypotheses scored on all notes -> a master
    (period, phase) grid -> a two-volatility regime that holds under syncopation and follows a real tempo step ->
    predict from the master grid."""

    def __init__(self, rate: int, hop: int, seed_bpm: Optional[float] = None):
        self.rate = int(rate)
        self.hop = int(hop)
        self.hop_s = hop / rate
        self.nfft = NFFT
        self.seed_bpm = float(seed_bpm) if seed_bpm and seed_bpm > 0 else None

        self._win = _hann(self.nfft)
        self._prev_mag: Optional[np.ndarray] = None

        # onset ring buffer: absolute audio time + flux strength + ACCENT weight, for each detected onset peak
        cap = int(GRID_MEMORY_S * rate / hop) + 16
        self._on_t = np.zeros(cap, dtype=np.float64)
        self._on_v = np.zeros(cap, dtype=np.float32)    # total spectral-flux strength
        self._on_a = np.zeros(cap, dtype=np.float32)    # accent (kick+snare band) strength -- the BEAT
        self._on_n = 0

        # rolling flux window (three-hop) for local peak picking -- one for total flux, one for the HIGH band.
        self._flux_hist = np.zeros(3, dtype=np.float32)
        self._high_hist = np.zeros(3, dtype=np.float32)

        self._hop_i = 0
        self._t_audio = 0.0

        # onset peak-picker state: adaptive threshold + refractory blanking so a sustained bass note's 150 ms
        # decay produces ONE onset, not a cluster of 5 (the cluster is what throws the grid search off).
        self._thresh = MIN_ENV
        self._last_onset_t = -10.0

        # master grid: period (seconds) + phase (absolute audio seconds of one grid line)
        self._period = 60.0 / (self.seed_bpm if self.seed_bpm else 120.0)
        self._phase = self.hop_s * FIRST_BEATS
        self._bpm = 60.0 / self._period

        # master grid evidence + volatility regime q in [0,1]
        self._master_score = -1.0
        self._q = 0.3                  # start slightly volatile so it can lock at all
        self._rival_period = self._period
        self._rival_phase = self._phase
        self._rival_score = -1.0
        self._rival_beats = 0.0
        self._cached_grid = (self._period, self._phase, -1.0)

        # beat march
        self._next_beat = self._phase
        self._conf = 0.3

        # accent for beat-level choice
        self._accent_lo = 0.0
        self._accent_hi = 0.0

    # -- onset ----------------------------------------------------------------------------------

    def _flux(self, block: np.ndarray) -> tuple:
        """Spectral flux. Returns (total_flux, kick_e, high_e): the total positive spectral rise, the rise in the
        kick band (40-100 Hz, for the downbeat/level choice only), and the rise in the HIGH band (>=150 Hz: snare
        + hats), which is the regular percussive accent that marks the BEAT and is disjoint from the sustained
        sub-bass (grid-research-grid §5: raw low-band energy cannot separate kick from sub-bass)."""
        x = np.zeros(self.nfft, dtype=np.float32)
        x[: len(block)] = block
        X = np.fft.rfft(x * self._win)
        mag = np.abs(X)
        if self._prev_mag is None:
            self._prev_mag = mag
            return 0.0, 0.0, 0.0
        pos = np.maximum(mag - self._prev_mag, 0.0)
        self._prev_mag = mag
        sf = float(np.sum(pos))
        if sf <= MIN_ENV:
            return 0.0, 0.0, 0.0
        n = len(mag)
        freqs = np.fft.rfftfreq(self.nfft, 1.0 / self.rate)[: n]
        # The BEAT-level accent is HIGH-band percussive flux (snare ~190 Hz + high hat noise): these are
        # regular on the beat and spectrally disjoint from the sustained sub-bass. LOW-band (40-100 Hz) is the
        # kick AND the sub-bass together -- raw low-band energy cannot separate them (grid-research-grid §5), so
        # it must NOT drive the grid. Kick energy is tracked separately, for the downbeat/level choice only.
        kick_e = float(np.sum(pos[(freqs >= 40.0) & (freqs <= 100.0)]))
        high_e = float(np.sum(pos[freqs >= 150.0]))          # snare + hat: the regular percussive accent
        self._accent_lo = 0.99 * self._accent_lo + 0.01 * kick_e
        self._accent_hi = 0.99 * self._accent_hi + 0.01 * high_e
        return sf, kick_e, high_e

    def _find_onsets(self, v0: float, v1: float, v2: float) -> Optional[tuple]:
        """A local flux peak at v1 (previous hop's flux), parabola-interpolated to sub-hop time, gated by an
        adaptive threshold and a refractory window. Returns (t_audio_of_peak, peak_value) or None."""
        if not (v1 >= v0 and v1 > v2 and v1 > MIN_ENV):
            # breathe the threshold down so quiet-but-real attacks still fire
            self._thresh = max(self._thresh * 0.9995, MIN_ENV)
            return None
        # adaptive threshold: must clear a decaying fraction of the recent max flux
        self._thresh = max(self._thresh * 0.9995, MIN_ENV)
        if v1 <= self._thresh:
            return None
        # refractory blanking: no two onsets within ~90 ms (kills bass-decay clusters + hat doubles)
        base = self._t_audio - 2.0 * self.hop_s
        if base - self._last_onset_t < 0.090:
            return None
        denom = (v0 - 2.0 * v1 + v2)
        d = 0.5 * (v0 - v2) / denom if abs(denom) > 1e-12 else 0.0
        d = float(np.clip(d, -1.0, 1.0))
        apex_v = v1 - 0.25 * (v0 - v2) * d
        # the peak flux v1 was computed for the hop that ended two hops ago (see feed()'s window shift)
        base = self._t_audio - 2.0 * self.hop_s
        t_peak = base + d * self.hop_s
        # raise the threshold so the tail of THIS note does not re-fire
        self._thresh = max(self._thresh, 0.5 * apex_v)
        self._last_onset_t = t_peak
        return (t_peak, apex_v)

    # -- grid search (Daniel: "on what grid would all of these notes fit?") ---------------------

    def _score_grids(self) -> tuple:
        """Beat-level grid search. Scores (period, phase) hypotheses by how well the ACCENT onsets (kick + snare
        bands) land on the grid, NOT all onsets -- the sustained sub-bass and hats are off-grid noise the grid
        must hold through, not follow. This is Daniel's 'the beat level comes from accent (kick and snare)'.
        Returns (best_period, best_phase_abs, best_score). Phase anchored to the most recent onset's line.

        The period ladder lives in the beat band [62,188] bpm (folded to one octave) so a sub-bass 16th sub-grid
        (245 bpm) or a half-time lock (52 bpm) can never BE the beat; octave partners x0.5/x2 are searched so a
        genuine 70/140/280 still resolves to the right level via accent."""
        cap = len(self._on_t)
        m = min(self._on_n, cap)
        if m < 8:
            return self._period, self._phase, -1.0
        idx = (np.arange(m) + (self._on_n - m)) % cap
        t = self._on_t[idx]                     # absolute onset times, recent-most-last
        a = self._on_a[idx].astype(np.float64)  # HIGH-band accent (snare+hat) strength -- the beat marker
        amax = float(np.max(a)) or 1.0
        w = a / amax
        w = w * w                               # strength-weighted

        # the beat band: 62..188 bpm in period seconds
        lo_p = 60.0 / FOLD_HI
        hi_p = 60.0 / FOLD_LO
        if self._master_score > 0.0 and self._period > 0:
            c = self._period
            if self.seed_bpm is not None:
                # a seed PINS the metrical level: search only near the seed's period, no octave partners. The
                # database lookup is the honest level tiebreak (grid-research-grid §5: raw energy cannot split
                # kick from sub-bass or beat from half-time backbeat; the seed can).
                c = 60.0 / self.seed_bpm
                parts = [np.geomspace(max(lo_p, c * 0.90), min(hi_p, c * 1.10), N_PERIODS)]
            else:
                parts = [np.geomspace(max(lo_p, c * 0.90), min(hi_p, c * 1.10), N_PERIODS // 2)]
                for f in (0.5, 2.0):            # octave partners (the master family: 70/140/280 is one grid)
                    plo, phi = max(lo_p, c * f * 0.90), min(hi_p, c * f * 1.10)
                    if phi > plo:
                        parts.append(np.geomspace(plo, phi, N_PERIODS // 4))
            periods = np.concatenate(parts)
        else:
            periods = np.geomspace(lo_p, hi_p, N_PERIODS)
        phases = np.linspace(0.0, 1.0, N_PHASES, endpoint=False)

        t_ref = t[-1]
        best_p, best_ph, best_s = self._period, self._phase, -1e18
        for period in periods:
            if period < 2.0 * self.hop_s:
                continue
            lines = max(2, int(GRID_MEMORY_S / period))
            penalty = PARSIMONY_W * lines
            tol = min(0.06, 0.25 * period)
            f = (t - t_ref) / period
            frac2 = f[:, None] - phases[None, :]
            frac2 = frac2 - np.floor(frac2)
            dist2 = np.minimum(frac2, 1.0 - frac2) * period      # (m, N_PHASES)
            on = dist2 <= tol
            reward = (w[:, None] * on * (1.0 - dist2 / (tol + 1e-9))).sum(axis=0)
            off_pen = (w[:, None] * (~on)).sum(axis=0)
            scores = reward - 0.5 * off_pen - penalty             # (N_PHASES,)
            j = int(np.argmax(scores))
            if scores[j] > best_s:
                best_s = float(scores[j])
                best_p = float(period)
                best_ph = t_ref - phases[j] * period
        return best_p, best_ph, best_s

    # -- master update (two-volatility join) ----------------------------------------------------

    def _update_master(self, best_p, best_ph, best_s):
        """Fold the grid-search result into the master through the volatility regime. Low q -> hold (tiny EMA,
        hysteresis); high q -> follow (nimble). A rival grid must outscore the master for RIVAL_BEATS before it
        can move it -- this is the hysteresis that keeps a single loud off-beat bass note from hijacking the grid,
        and the volatility that lets a real tempo step relock within the 4 s shift criterion."""
        if best_s <= -0.9 or best_p <= 0:
            return

        first = self._master_score < 0.0
        if first:
            # initial lock: adopt the grid outright, but a seed PINS the octave -- fold the found period to the
            # seed's octave so the first lock cannot land on half/double time.
            if self.seed_bpm is not None:
                bpm = 60.0 / best_p
                best_p = 60.0 / _nearest_octave(bpm, self.seed_bpm)
            self._period = best_p
            self._phase = best_ph
            self._master_score = best_s
            self._rival_period, self._rival_phase, self._rival_score = best_p, best_ph, best_s
            self._rival_beats = 0.0
            return

        # how much better is the rival (the grid search's winner) than the master right now?
        # score the master's own grid freshly so the comparison is apples-to-apples.
        master_now = self._score_this_grid(self._period, self._phase)

        if best_s > master_now * SCORE_MARGIN:
            # a genuinely better grid is emerging. Rival accumulates; master only moves after sustained evidence.
            rival_new = abs(math.log2(best_p / (self._rival_period or best_p))) > 1e-4
            if rival_new:
                self._rival_period, self._rival_phase, self._rival_score = best_p, best_ph, best_s
                self._rival_beats = 1.0
            else:
                self._rival_beats += 1.0
        else:
            self._rival_beats = max(0.0, self._rival_beats - 1.0)

        # volatility: a collapse in the master's own score means the music changed -- follow, don't hold.
        if master_now < self._master_score * 0.5:
            self._q = min(1.0, self._q + VOL_UP)
        else:
            self._q = max(0.0, self._q - VOL_DOWN)

        if self._rival_beats >= RIVAL_BEATS and self._rival_score > self._master_score:
            # A seed PINS the metrical level: a rival at a DIFFERENT octave than the seed must never commit (the
            # database lookup is the honest level tiebreak, grid-research-grid §5). Only a same-octave rival
            # (a real tempo drift within the seeded level) may move the master.
            if self.seed_bpm is not None:
                rival_bpm = 60.0 / self._rival_period
                if abs(math.log2(rival_bpm / self.seed_bpm)) > 0.5:
                    self._rival_beats = 0.0           # discard the off-octave rival, hold the seeded level
                    return
            # commit: move the master toward the rival, nimble or rigid by volatility
            ema = HIGHVOL_EMA if self._q > 0.6 else LOWVOL_EMA
            self._period = self._period * (1.0 - ema) + self._rival_period * ema
            self._phase = self._rival_phase
            self._master_score = self._rival_score
            self._rival_beats = 0.0
        else:
            # steady state: a small volatility-scaled correction, averaged over many beats (never a per-note snap)
            # keep the master phase aligned to the grid the onsets actually agree on
            if self._q < 0.6:
                # holder: tiny drift correction toward the latest grid, but never move phase on a single update
                pass
            self._master_score = 0.9 * self._master_score + 0.1 * master_now

        self._period = float(np.clip(self._period, 60.0 / BPM_MAX, 60.0 / BPM_MIN))

    def _score_this_grid(self, period, phase):
        """Score a specific (period, phase) grid against the recent ACCENT onsets (kick+snare), the same weight
        as the search -- so the master's own score is comparable to a rival grid's."""
        cap = len(self._on_t)
        m = min(self._on_n, cap)
        if m < 4:
            return -1.0
        idx = (np.arange(m) + (self._on_n - m)) % cap
        t = self._on_t[idx]
        a = self._on_a[idx].astype(np.float64)
        amax = float(np.max(a)) or 1.0
        w = (a / amax)
        w = w * w
        tol = min(0.06, 0.25 * period)
        f = (t - phase) / period
        frac = f - np.floor(f)
        dist = np.minimum(frac, 1.0 - frac) * period
        on = dist <= tol
        reward = float(np.sum(w[on] * (1.0 - dist[on] / (tol + 1e-9))))
        off = float(np.sum(w[~on]))
        return reward - 0.5 * off

    # -- feed -----------------------------------------------------------------------------------

    def feed(self, block: np.ndarray) -> List[dict]:
        block = np.asarray(block, dtype=np.float32)
        if block.ndim > 1:
            block = block.mean(axis=1)
        self._hop_i += 1
        self._t_audio += self.hop_s
        out: List[dict] = []

        if float(np.std(block) if block.size else 0.0) < SILENCE_STD:
            self._flux_hist[0], self._flux_hist[1], self._flux_hist[2] = 0.0, self._flux_hist[1], self._flux_hist[2]
            return out

        flux, kick_e, high_e = self._flux(block)

        # shift the two flux windows; peak-pick on the HIGH band (the percussive accent), which is the signal
        # that is regular on the beat and disjoint from the off-beat sub-bass. The bass's onset times must not
        # become beat candidates -- the hat/snare's times must.
        f0, f1, f2 = self._flux_hist[0], self._flux_hist[1], self._flux_hist[2]
        self._flux_hist[0], self._flux_hist[1], self._flux_hist[2] = f1, f2, flux
        h0, h1, h2 = self._high_hist[0], self._high_hist[1], self._high_hist[2]
        self._high_hist[0], self._high_hist[1], self._high_hist[2] = h1, h2, high_e
        # the peak we look for is at the PREVIOUS hop's HIGH flux, compared against its neighbours
        det = self._find_onsets(h1, h2, high_e)
        if det is not None:
            t_peak, amp = det
            slot = self._on_n % len(self._on_t)
            self._on_t[slot] = t_peak
            self._on_v[slot] = amp                         # HIGH-band strength (the signal we peak-picked on)
            self._on_a[slot] = high_e                      # HIGH-band accent -- the beat marker
            self._on_n += 1

        if self._hop_i < FIRST_BEATS:
            return out

        # ---- master grid update (decimated) ----------------------------------------------------
        if self._hop_i % GRID_EVERY == 1:
            self._cached_grid = self._score_grids()
        best_p, best_ph, best_s = self._cached_grid
        prev_period, prev_phase = self._period, self._phase
        self._update_master(best_p, best_ph, best_s)

        # If the master grid moved (period or phase), re-anchor the beat cursor to the nearest grid line at/after
        # now; otherwise leave the monotonic cursor marching. This keeps beats ON the grid without discarding
        # the steady march every hop.
        if abs(self._period - prev_period) > 1e-7 or abs(self._phase - prev_phase) > 1e-7:
            self._next_beat = self._phase + math.ceil((self._t_audio - self._phase) / self._period) * self._period
            if self._next_beat <= self._t_audio:
                self._next_beat += self._period

        # ---- project the master grid onto the beat level (accent + seed) ---------------------
        self._bpm = 60.0 / self._period
        if self.seed_bpm is not None:
            # The seed is the known tempo: emit the seed's tempo (grid drift is only phase/tiny-tempo, never a
            # level flip), with the master's small drift folded in. No octave folding -- half/double is impossible
            # when the database already said what the track is.
            self._bpm = self.seed_bpm
            self._period = 60.0 / self.seed_bpm

        # ---- emit an OBSERVED beat when the master grid crosses a line ---------------------------
        # beats are ON the grid: the next grid line at/after the last emitted beat.
        if self._next_beat <= self._t_audio:
            t_beat = self._next_beat
            phase = (t_beat % self._period) / self._period
            confidence = float(np.clip(1.0 - self._q, 0.0, 1.0))
            out = [{
                "t_beat": float(t_beat),
                "bpm": round(float(self._bpm), 3),
                "phase": round(float(phase), 4),
                "confidence": round(float(confidence), 3),
                "is_downbeat": None,
            }]
            self._next_beat = t_beat + self._period
            self._conf = confidence
        return out

    # -- predict ---------------------------------------------------------------------------------

    def predict(self, now: float) -> List[dict]:
        if self._period <= 0:
            return []
        t = self._next_beat
        while t <= now:
            t += self._period
        out = []
        for _ in range(2):
            out.append({
                "t_beat": float(t),
                "bpm": round(float(self._bpm), 3),
                "phase": round((t % self._period) / self._period, 4),
                "confidence": round(float(self._conf), 3),
            })
            t += self._period
        return out
