"""arsenal.keylab.beat_w -- contestant W: a discrete bar-pointer forward filter (A16 T4, the grid tracker).

Built from the papers (Whiteley, Cemgil & Godsill 2006, "Bayesian modelling of temporal structure in musical
audio"; Krebs, Boeck & Widmer 2015, "An efficient state-space model for joint tempo and meter tracking"), not from
any implementation: no madmom code and none of its non-commercial models. Imports: stdlib and numpy only.
Forward filtering only: causal and real-time (the filter runs two frames behind the audio, for the onset peak
picker's one-frame look-ahead).

THE STATE: (tempo, position in a 4/4 bar). The tempo bank is evenly log-spaced (1.5 % steps, 55-215 BPM) with REAL
beat periods P_i in frames. Tempo i has floor(P_i) pointer positions per beat and advances on a global schedule that
depends on the frame index only (one position per frame, none on the few frames its running count does not move),
so every period is exact and the bank is equally fine at every octave. A position k in the bar IS (tatum, sub-tatum
phase): the 16th grid line just passed and the fraction of the way to the next one.

THE TRANSITION: the pointer advances; the tempo may change only at a beat line, with
    P(j | i) = (1 - rho) exp(-lam_lo s_i |P_i/P_j - 1|) / Z  +  rho exp(-lam_hi s_i |P_i/P_j - 1|) / Z',
lam_lo the stiffness, lam_hi a broad kernel, and s_i ~ 1/sqrt(period) so the tempo random walk has the same variance
per second at every tempo (a per-beat kernel alone taxes the faster octave of every octave tie).

LOW AND HIGH VOLATILITY, SMARTLY JOINED (Daniel's two settings). Two forward filters run on the same state space and
the same evidence: the STABLE model (rho ~ 0, long memory) holds the grid through syncopation; the VOLATILE model
(half broad kernel, short memory) follows. Every frame the volatile model takes a small share of the stable belief,
the IMM mixing step ("the volatile one gets guesses from the lower volatility one"). Their per-frame predictive
likelihoods give a running log Bayes factor (1.5 s memory); when the volatile model has out-predicted the stable one
by ALARM_H nats the change ALARM fires: the stable model takes the volatile posterior in (a re-induction from the
onsets of the last couple of seconds, which is all the volatile model remembers) and its tempo kernel is widened
(rho raised) for two beats.

THE OBSERVATION ("on what grid would all of these notes fit?"). Every detected onset is scored against the grid lines
of every state at once. A line of metrical level l (bar, half bar, beat, 8th, 16th, off-beat triplet 8th) carries an
onset with probability h_l, with Gaussian timing jitter; anything else is a Poisson background. So an onset on a
coarse line earns the most, on a 16th line less, off the grid only the background (a BOUNDED off-grid cost), and
every line passed empty pays log(1 - h_l): the PARSIMONY term, since a finer or faster grid has more lines to leave
empty. That cost is tempered by how busy the music is (a lone kick per bar leaves every grid empty). Onsets are
strength-weighted (a weighted log-likelihood). The grid stops at 16ths (plus triplets), so notes that need 32nds of
a slower beat are off its grid: that is what holds half-time bass music at the fast level.
ACCENT: an onset whose energy rises in the lower AND the upper half of the spectrum at once (kick with its click,
snare, kick with hat) is accented; beat-level lines expect accent, 8ths and 16ths do not. One band alone (a sub-bass
note, a hat) is never the beat cue.
PRIORS: a tempo lean toward ~120 BPM (log-normal, applied per second so it settles octave ties without overriding
evidence); a seed BPM is an octave-agnostic prior that DECAYS, never a lock; and music starts on a beat: the first
strong note after silence (stream start, or a gap between tracks, which also resets the filter) counts as an accented,
double-weight onset.

OUTPUT: the posterior is read as ONE master grid: the dominant tempo neighbourhood (a rival family, e.g. the other
octave, takes over only after leading for a whole beat or by 3 to 1), its beat phase, period and bar position. A
beat is emitted as the master grid crosses a beat line (is_downbeat from the bar position), corrected within four
frames if an onset sharpens it (the bench keeps the last word). BPM is a least-squares fit over the recent emitted
beats; predict() extrapolates the master grid with that period.
"""
from __future__ import annotations

import math
from collections import deque
from typing import List, Optional

import numpy as np


# --- the onset front end -------------------------------------------------------------------------------------

class _OnsetFrontEnd:
    """Causal multi-band log spectral flux with a one-frame look-ahead peak picker.

    One FFT per hop (window = 2 hops, Hann; frame f is centred on sample f*hop). Positive log-magnitude flux is
    averaged inside four bands (sub/low, low-mid, mid, high). Each band has its own noise floor (a slow running
    mean) and its own decaying running peak, so a band's salience s_g = (flux - floor) / (peak - floor) reads about
    1 for that band's typical onset whatever its loudness: a hat counts as much as a kick ("all onsets").
      detection function  sum of the band saliences;
      strength w          the onset's salience in its strongest band (0..1);
      accent              min(strongest low band, strongest high band): high only when the energy rises in the
                          lower AND the upper half of the spectrum together (kick with click, snare, kick with
                          hat). A sub-bass note alone or a hat alone is never accented."""

    EDGES_HZ = (25.0, 120.0, 500.0, 2500.0, 16000.0)

    def __init__(self, rate: int, hop: int):
        self.rate, self.hop = rate, hop
        self.n = 2 * hop
        self.win = np.hanning(self.n + 1)[:-1]
        self.buf = np.zeros(self.n)
        freqs = np.fft.rfftfreq(self.n, 1.0 / rate)
        hi_edge = min(self.EDGES_HZ[-1], 0.45 * rate)
        edges = list(self.EDGES_HZ[:-1]) + [hi_edge]
        mats = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = ((freqs >= lo) & (freqs < hi)).astype(float)
            if m.sum() == 0:                                   # degenerate rates: nearest bin
                m[int(np.argmin(np.abs(freqs - 0.5 * (lo + hi))))] = 1.0
            mats.append(m / m.sum())
        self.band_mat = np.array(mats).T                       # (bins, 4): band means
        self.prev_log: Optional[np.ndarray] = None
        fps = rate / hop
        self.peak_decay = math.exp(-math.log(2.0) / (3.0 * fps))    # running-peak half-life 3 s
        self.floor_a = 1.0 - math.exp(-1.0 / (1.0 * fps))           # noise-floor EMA, 1 s
        self.peak = np.full(4, 1e-2)
        self.floor = np.zeros(4)
        self.dev = np.zeros(4)
        self.odf_peak = 1e-2
        self.odf_hist: deque = deque(maxlen=12)
        self.frame = -1
        self._last = None                                      # (frame, odf, saliences) one frame back
        self._last2 = None
        self.last_onset = -10 ** 9
        self.silent_run = 0

    def step(self, block: np.ndarray) -> Optional[tuple]:
        """Push one hop of audio; returns an onset (frame, delta, w, accent) for the PREVIOUS frame, or None."""
        self.frame += 1
        self.buf[:-self.hop] = self.buf[self.hop:]
        self.buf[-self.hop:] = block
        quiet = float(np.dot(block, block)) < len(block) * 1e-8          # below -80 dBFS: digital silence
        self.silent_run = self.silent_run + 1 if quiet else 0
        L = np.log1p(np.abs(np.fft.rfft(self.buf * self.win)))
        if self.prev_log is None:
            self.prev_log = L
        bands = np.maximum(L - self.prev_log, 0.0) @ self.band_mat     # (4,)
        self.prev_log = L
        thr = self.floor + 2.0 * self.dev                      # a band's noise: running mean + 2 deviations
        sal = np.maximum(bands - thr, 0.0) / np.maximum(self.peak - thr, 1e-3)
        sal = np.minimum(sal, 1.5)
        top = float(self.peak.max())
        sal[self.peak < 0.05 * top] *= 0.25                     # a near-silent band cannot dominate
        clipped = np.minimum(bands, self.peak)
        self.dev += self.floor_a * (np.abs(clipped - self.floor) - self.dev)
        self.floor += self.floor_a * (clipped - self.floor)
        self.peak = np.maximum(self.peak * self.peak_decay, bands)
        odf = float(sal.sum())
        self.odf_peak = max(self.odf_peak * self.peak_decay, odf, 1e-3)

        cur = (self.frame, odf, sal)
        out = None
        if self._last is not None and self._last2 is not None:
            f, v, s = self._last
            vp, vn = self._last2[1], odf
            past = list(self.odf_hist)[:-1]                   # values before frame f
            local_max = (v >= vp) and (v > vn) and (not past[-3:] or v >= max(past[-3:]))
            mean = (sum(past[-10:]) / len(past[-10:])) if past else 0.0
            if local_max and v > mean + 0.15 and f - self.last_onset >= 2:
                den = vp - 2.0 * v + vn
                delta = 0.5 * (vp - vn) / den if den < 0 else 0.0
                delta = min(0.5, max(-0.5, delta))
                smax = np.maximum(np.maximum(self._last2[2], s), sal)    # the onset frame and its neighbours
                w = min(1.0, float(smax.max()))
                acc = min(1.0, float(min(max(smax[0], smax[1]), max(smax[2], smax[3]))))
                out = (f, delta, w, acc)
                self.last_onset = f
        self._last2 = self._last
        self._last = cur
        self.odf_hist.append(odf)
        return out


# --- the tracker ---------------------------------------------------------------------------------------------

class Tracker:
    # tempo bank: evenly log-spaced, real beat periods
    BPM_LO, BPM_HI, BANK_STEP = 55.0, 215.0, 0.015
    # metrical levels: 0 bar, 1 half bar, 2 beat, 3 eighth, 4 sixteenth, 5 off-beat triplet eighth
    H_LINE = np.array([0.90, 0.60, 0.50, 0.20, 0.10, 0.03])   # P(onset on a line of this level)
    Q_ACC = np.array([0.70, 0.70, 0.65, 0.25, 0.15, 0.15])    # P(accented | onset on this level)
    Q_BG = 0.20                                               # P(accented | background onset)
    BG_RATE = 2.0                                              # background (off-grid) onsets per second
    SIGMA = 1.1                                                # line timing jitter, frames
    LAM_LO, LAM_HI = 50.0, 6.0                                 # stiff / broad tempo-change kernels (at 120 BPM)
    PERIOD_REF_S = 0.5                                         # the beat period where lambda is quoted
    RHO_IDLE, RHO_ALARM = 1e-4, 0.35                           # broad-kernel share: stable model, after an alarm
    FLOOR = 1e-7                                               # per-frame mix toward the prior (bounded memory)
    RHO_V, FLOOR_V, MIX_V = 0.5, 1e-3, 0.005                   # volatile model: broad share, short memory, coupling
    PRIOR_BPM, PRIOR_OCT, PRIOR_RATE = 120.0, 0.9, 1.0          # tempo lean: centre, width (octaves), nats/s scale
    SEED_OCT, SEED_RATE, SEED_TAU = 0.12, 1.5, 12.0            # seed lean: width, initial rate, decay (s)
    ALARM_H, ALARM_TAU, ALARM_REFRACT, ALARM_MIX = 1.0, 1.5, 1.5, 0.5   # Bayes-factor alarm (nats, s, s, share)
    ANCHOR_W, RESET_SILENCE_S = 2.0, 4.0                       # first note after silence; silence that resets
    WARMUP_S = 4.0                                             # no master hysteresis before this
    DENS_REF, DENS_TAU = 2.5, 3.0                              # emptiness tempering: onsets/s, EMA time constant

    def __init__(self, rate: int, hop: int, seed_bpm: Optional[float] = None):
        self.rate, self.hop = int(rate), int(hop)
        self.fps = self.rate / self.hop
        self.dt = 1.0 / self.fps
        self.seed = float(seed_bpm) if seed_bpm else None
        self.fe = _OnsetFrontEnd(self.rate, self.hop)
        self._pending = np.zeros(0, dtype=np.float64)
        self.kappa = self.kappa_used = 1.0
        self.density = self.DENS_REF                           # onsets per second (strength-weighted), EMA
        self.dens_decay = math.exp(-self.dt / self.DENS_TAU)
        self._build_states()
        self._build_observation_tables()
        self._build_transitions()
        self.p = self.p0.copy()                                # the stable (low-volatility) model
        self.pv = self.p0.copy()                               # the volatile (high-volatility) model
        self.f = -1                                            # last filtered frame
        self.rho_until = -1
        self.D, self.last_alarm_f = 0.0, -10 ** 9
        self.anchor_ready, self.anchor_age = True, 0
        self.d_decay = math.exp(-self.dt / self.ALARM_TAU)
        self.beat_frames: List[float] = []                     # emitted beat lines (fractional frames)
        self.last_emit_f = -10 ** 9
        self.conf = 0.0
        self.g_tempo_i = int(np.argmax(np.add.reduceat(self.p0, self.off)))
        self.g_period = float(self.Pf[self.g_tempo_i])
        self.g_beat_f = 0.0
        self.g_beat_idx = 0
        self._rival_frames = 0

    # --- construction -------------------------------------------------------------------------------------

    def _build_states(self) -> None:
        """The tempo bank is evenly log-spaced in BPM, with REAL beat periods P_i (frames). Tempo i has
        Q_i = floor(P_i) pointer positions per beat and advances on a global schedule: one position on most frames,
        none on the few frames where its running count floor(f * Q_i / P_i) does not move. The schedule depends on
        the frame index only, never on the path, so every state of a tempo moves together and the period is exact.
        (An integer-frames-per-beat bank is 4x coarser at 200 BPM than at 50 BPM, and that taxes the faster octave
        of every octave tie.)"""
        fps = self.fps
        n = int(math.ceil(math.log(self.BPM_HI / self.BPM_LO) / math.log(1.0 + self.BANK_STEP))) + 1
        bpm = np.geomspace(self.BPM_LO, self.BPM_HI, n)[::-1]          # slow to fast
        self.Pf = 60.0 * fps / bpm                                      # beat period, frames (real)
        self.Q = np.floor(self.Pf).astype(int)
        self.adv_rate = self.Q / self.Pf                                # positions per frame, <= 1
        self.nT = len(self.Q)
        N = 4 * self.Q
        self.N = N
        self.off = np.concatenate([[0], np.cumsum(N)[:-1]]).astype(int)
        S = int(N.sum())
        self.S = S
        self.tempo_of = np.repeat(np.arange(self.nT), N)
        self.pos = np.concatenate([np.arange(x) for x in N])
        Qs = self.Q[self.tempo_of]
        self.Qs = Qs
        self.kb = self.pos % Qs                                         # positions since the beat line
        self.beat_of = self.pos // Qs                                   # beat index in the bar (0 = downbeat)
        self.prev = np.arange(S) - 1
        self.start_idx = (self.off[:, None] + np.arange(4)[None, :] * self.Q[:, None]).astype(int)
        self.end_idx = self.start_idx + self.Q[:, None] - 1
        self.bpm_of = 60.0 * fps / self.Pf
        self.phase_bin = np.minimum((self.kb / Qs * self.PHASE_BINS).astype(int), self.PHASE_BINS - 1)
        self._rot_m = (np.arange(self.PHASE_BINS) - 1) % self.PHASE_BINS
        self._rot_p = (np.arange(self.PHASE_BINS) + 1) % self.PHASE_BINS
        self._next_beat = np.array([3, 0, 1, 2])                       # start of beat b <- end of beat b-1
        # tempo prior (log-normal in tempo around PRIOR_BPM)
        oct_ = np.log2(self.bpm_of / self.PRIOR_BPM)
        self.logprior_t = -0.5 * (oct_ / self.PRIOR_OCT) ** 2
        p0t = np.exp(self.logprior_t + self._seed_logprior(1.0))
        p0t /= p0t.sum()
        self.p0 = (p0t / N)[self.tempo_of]                     # uniform position within each tempo
        self.p0 /= self.p0.sum()

    def _schedule(self, frame: int):
        """Which tempi advance at this frame, and each tempo's fractional progress toward its next position."""
        c1 = (frame + 1) * self.adv_rate
        adv = np.floor(c1) - np.floor(frame * self.adv_rate) > 0
        eps_frames = (c1 - np.floor(c1)) / self.adv_rate               # sub-position progress, in frames
        return adv, eps_frames

    def _seed_logprior(self, strength: float) -> np.ndarray:
        if not self.seed or strength <= 0:
            return np.zeros(self.nT)
        o = np.log2(self.bpm_of / self.seed)
        fam = np.abs(o - np.round(o))                           # octave-agnostic distance to the seed family
        exact = np.abs(o)
        return strength * (-0.5 * (fam / self.SEED_OCT) ** 2 - 0.25 * np.minimum(exact, 1.0))

    def _build_observation_tables(self) -> None:
        Qs = self.Qs.astype(float)
        a = self.adv_rate[self.tempo_of]
        k = self.pos.astype(float)
        # nearest straight-16th line: signed offset in frames, and its metrical level
        m = np.round(k * 4.0 / Qs).astype(int)
        self.off16 = (k - m * Qs / 4.0) / a
        mm = m % 16
        lev = np.full(self.S, 4)
        lev[mm % 2 == 0] = 3
        lev[mm % 4 == 0] = 2
        lev[mm == 8] = 1
        lev[mm == 0] = 0
        self.lev16 = lev
        # nearest triplet-eighth line (only the off-beat ones; the on-beat one is the straight beat line)
        mt = np.round(k * 3.0 / Qs).astype(int)
        self.offT = (k - mt * Qs / 3.0) / a
        self.trip_ok = (mt % 3 != 0)
        # emptiness: a line at position L is paid by the state the pointer ARRIVES at first, ceil(L)
        log_empty = np.zeros(self.S)
        logh0 = np.log1p(-self.H_LINE)
        for i in range(self.nT):
            q = int(self.Q[i])
            Ni, base = 4 * q, self.off[i]
            for j in range(16):
                lv = 0 if j == 0 else 1 if j == 8 else 2 if j % 4 == 0 else 3 if j % 2 == 0 else 4
                log_empty[base + int(math.ceil(j * q / 4.0 - 1e-9)) % Ni] += logh0[lv]
            for b in range(4):
                for t3 in (1, 2):
                    log_empty[base + int(math.ceil(b * q + t3 * q / 3.0 - 1e-9)) % Ni] += logh0[5]
        self.log_empty = log_empty
        self._refresh_base(0)

    def _build_transitions(self) -> None:
        r = np.abs(self.Pf[:, None] / self.Pf[None, :] - 1.0)   # |P_i / P_j - 1|, i = from, j = to
        # stiffness per beat grows with tempo (lambda ~ 1/sqrt(period)), so the tempo random walk has the same
        # variance per SECOND at every tempo: a per-beat kernel alone taxes the faster octave of every tie, since
        # it has more beats per second in which to pay
        scale = np.sqrt(self.PERIOD_REF_S * self.fps / self.Pf)[:, None]
        lo = np.exp(-self.LAM_LO * scale * r)
        hi = np.exp(-self.LAM_HI * scale * r)
        self.A_lo = lo / lo.sum(axis=1, keepdims=True)
        self.A_hi = hi / hi.sum(axis=1, keepdims=True)
        self._A_cache = {}

    def _A(self, rho: float) -> np.ndarray:
        key = round(rho, 6)
        A = self._A_cache.get(key)
        if A is None:
            A = ((1.0 - rho) * self.A_lo + rho * self.A_hi).T.copy()   # transposed: new = A @ ends
            self._A_cache[key] = A
        return A

    def _refresh_base(self, frame: int) -> None:
        """Per-frame multiplicative factor: line emptiness (tempered by how busy the music is) and the tempo/seed
        lean. An empty line is evidence only in proportion to how full lines usually are: in a sparse passage
        (a lone kick per bar) every grid is mostly empty, and a full-strength emptiness cost would just push the
        tempo down an octave, so it is scaled by kappa = recent onset density / DENS_REF, clipped to [0.25, 1]."""
        t = frame * self.dt
        lean = self.PRIOR_RATE * self.logprior_t
        if self.seed:
            lean = lean + self.SEED_RATE * math.exp(-t / self.SEED_TAU) * self._seed_logprior(1.0)
        self.kappa_used = self.kappa
        self.base = np.exp(self.kappa * self.log_empty + self.dt * lean[self.tempo_of])
        self.unempty = np.exp(-self.kappa * self.log_empty)

    # --- the filter -------------------------------------------------------------------------------------------

    def _predict_step(self, p: np.ndarray, rho: float, adv: np.ndarray) -> np.ndarray:
        stalled = np.flatnonzero(~adv)
        new = p[self.prev]                                      # one position per frame
        ends = p[self.end_idx]                                  # (nT, 4): mass about to cross a beat line
        if len(stalled):
            ends[stalled] = 0.0
        starts = (self._A(rho) @ ends)[:, self._next_beat]      # the tempo may change only here
        new[self.start_idx] = starts
        for i in stalled:                                       # tempi that do not move this frame
            a, b = self.off[i], self.off[i] + self.N[i]
            new[a:b] = p[a:b]
            new[self.start_idx[i]] += starts[i]
        return new

    def _onset_loglik(self, delta: float, w: float, acc: float, eps_frames: np.ndarray) -> np.ndarray:
        s2 = 2.0 * self.SIGMA ** 2
        norm = 1.0 / (math.sqrt(2.0 * math.pi) * self.SIGMA)
        h = self.H_LINE
        accf = acc * self.Q_ACC + (1.0 - acc) * (1.0 - self.Q_ACC)
        c = h * (1.0 - h) ** (-self.kappa_used) * accf * norm    # undoes the (tempered) emptiness already paid
        bg = self.BG_RATE * self.dt * (acc * self.Q_BG + (1.0 - acc) * (1.0 - self.Q_BG))
        shift = eps_frames[self.tempo_of] + delta
        d16 = self.off16 + shift
        dT = self.offT + shift
        r = c[self.lev16] * np.exp(-d16 * d16 / s2)
        r += np.where(self.trip_ok, c[5] * np.exp(-dT * dT / s2), 0.0)
        return w * np.log1p(r / bg)

    def _frame_factors(self, frame: int, onset):
        """What both volatility models share at this frame: the pointer schedule and the onset's grid score."""
        adv, eps = self._schedule(frame)
        g = None
        if onset is not None:
            ll = self._onset_loglik(onset[1], onset[2], onset[3], eps)
            g = np.exp(ll - ll.max())
        return adv, g

    def _filter_frame(self, p: np.ndarray, adv: np.ndarray, g, rho: float, floor: float):
        """One forward step. Returns the new posterior and log Z, this frame's predictive likelihood (the same
        scale for both models, so their difference is a per-frame Bayes factor)."""
        p = self._predict_step(p, rho, adv)
        p *= self.base
        for i in np.flatnonzero(~adv):                          # a stalled pointer passes no line this frame
            a, b = self.off[i], self.off[i] + self.N[i]
            p[a:b] *= self.unempty[a:b]
        if g is not None:
            p *= g
        tot = float(p.sum())
        if not np.isfinite(tot) or tot <= 0:
            return self.p0.copy(), -50.0
        p /= tot
        p *= (1.0 - floor)
        p += floor * self.p0
        return p, math.log(tot)

    # --- the two volatility models, smartly joined (the high-volatility path) --------------------------------

    def _join(self, frame: int, zs: float, zv: float) -> None:
        """The volatile model takes a small share of the stable belief every frame (it "gets guesses from the
        lower volatility one", the IMM mixing step). Their running log Bayes factor D (forgetting ~1.5 s) is the
        change detector: when the volatile model has out-predicted the stable one by ALARM_H nats, the ALARM
        fires: the stable model takes the volatile posterior in (re-induction from the recent onsets, since the
        volatile model's memory is short) and its tempo kernel is widened for two beats."""
        self.pv *= (1.0 - self.MIX_V)
        self.pv += self.MIX_V * self.p
        self.D = self.D * self.d_decay + (zv - zs)
        if (self.D > self.ALARM_H and frame * self.dt > self.WARMUP_S
                and frame - self.last_alarm_f > self.ALARM_REFRACT * self.fps):
            self.last_alarm_f = frame
            self.D = 0.0
            self.p = (1.0 - self.ALARM_MIX) * self.p + self.ALARM_MIX * self.pv
            self.rho_until = frame + int(2 * self.g_period)

    # --- the contract ---------------------------------------------------------------------------------------

    def feed(self, block: np.ndarray) -> List[dict]:
        x = np.asarray(block, dtype=np.float64).ravel()
        if len(x) == self.hop and not len(self._pending):
            chunks = [x]
        else:
            self._pending = np.concatenate([self._pending, x])
            chunks = []
            while len(self._pending) >= self.hop:
                chunks.append(self._pending[:self.hop])
                self._pending = self._pending[self.hop:]
        events: List[dict] = []
        for c in chunks:
            onset = self.fe.step(c)
            frame = self.fe.frame - 1                          # the frame the peak picker just decided on
            if frame < 0:
                continue
            if self.fe.silent_run * self.dt >= self.RESET_SILENCE_S:
                self._restart()                                # a gap between tracks: the next song owes us nothing
            elif self.fe.silent_run == 0 and self.anchor_ready:
                self.anchor_age += 1
                if onset is not None and onset[2] >= 0.5:
                    # music starts on a beat: the first strong note after silence is scored as an accented,
                    # double-weight onset (a prior that decays into the evidence, never a lock)
                    onset = (onset[0], onset[1], self.ANCHOR_W, 1.0)
                    self.anchor_ready = False
                elif self.anchor_age * self.dt > 1.5:
                    self.anchor_ready = False
            events.extend(self._advance(frame, onset))
        return events

    def _restart(self) -> None:
        if self.anchor_ready and self.anchor_age == 0:
            return
        self.p = self.p0.copy()
        self.pv = self.p0.copy()
        self.D = 0.0
        self.density = self.DENS_REF
        self.beat_frames = []
        self.anchor_ready, self.anchor_age = True, 0

    def _advance(self, frame: int, onset) -> List[dict]:
        self.f = frame
        self.density *= self.dens_decay
        if onset is not None:
            self.density += onset[2] / self.DENS_TAU
        self.kappa = min(1.0, max(0.25, self.density / self.DENS_REF))
        if (frame % 32 == 0 and self.seed) or abs(self.kappa - self.kappa_used) > 0.05:
            self._refresh_base(frame)
        if self.anchor_ready and self.anchor_age == 0 and self.fe.silent_run > 0:
            return []                                          # silence before the music (re)starts: wait
        rho = self.RHO_ALARM if frame <= self.rho_until else self.RHO_IDLE
        adv, g = self._frame_factors(frame, onset)
        self.p, zs = self._filter_frame(self.p, adv, g, rho, self.FLOOR)
        self.pv, zv = self._filter_frame(self.pv, adv, g, self.RHO_V, self.FLOOR_V)
        self._join(frame, zs, zv)
        return self._emit(frame)

    # --- reading the posterior: the master grid ----------------------------------------------------------------

    PHASE_BINS = 72

    def _read_grid(self, frame: int) -> None:
        """Collapse the posterior onto ONE grid: the dominant tempo neighbourhood (5 bank tempi around the peak of
        the tempo marginal), its beat phase (a weighted circular histogram over those states), its expected period
        and its bar position. Aggregating neighbours is what keeps the read-out steady when the MAP state wanders
        between adjacent tempi (sparse music, gaps)."""
        pt = np.add.reduceat(self.p, self.off)
        sm = pt.copy()
        sm[1:] += pt[:-1]
        sm[:-1] += pt[1:]
        i = int(np.argmax(sm))
        # hysteresis on the master: a rival family (more than 3 bank steps away, e.g. the other octave) takes over
        # only after leading by 30 % for a whole beat, or at once when it leads 3 to 1 (a real tempo change)
        c = self.g_tempo_i
        settled = frame * self.dt > self.WARMUP_S and frame > self.rho_until
        if settled and abs(i - c) > 3:
            ratio = sm[i] / max(sm[c], 1e-300)
            self._rival_frames = self._rival_frames + 1 if ratio > 1.3 else 0
            if ratio < 3.0 and self._rival_frames < self.Pf[i]:
                i = c
        else:
            self._rival_frames = 0
        lo, hi = max(0, i - 2), min(self.nT - 1, i + 2)
        a, b = int(self.off[lo]), int(self.off[hi] + self.N[hi])
        ps = self.p[a:b]
        wt = pt[lo:hi + 1]
        Mbar = float((wt * self.Pf[lo:hi + 1]).sum() / max(wt.sum(), 1e-300))
        hist = np.bincount(self.phase_bin[a:b], weights=ps, minlength=self.PHASE_BINS)
        hs = hist + 0.5 * (hist[self._rot_m] + hist[self._rot_p])
        k = int(np.argmax(hs))
        # sub-bin refinement: circular mean of the three bins around the peak
        idx = np.array([k - 1, k, k + 1])
        wv = hist[idx % self.PHASE_BINS]
        ph = (k + float((wv * (idx - k)).sum() / max(wv.sum(), 1e-300)) + 0.5) / self.PHASE_BINS
        self.g_period = Mbar
        self.g_beat_f = frame - ph * Mbar                       # the most recent beat line, fractional frame
        near = np.abs(((self.phase_bin[a:b] - k + self.PHASE_BINS // 2) % self.PHASE_BINS) - self.PHASE_BINS // 2) <= 2
        self.conf = float(min(1.0, ps[near].sum()))
        # bar position: the beat index carried by the states that agree on this phase
        bb = np.bincount(self.beat_of[a:b][near], weights=ps[near], minlength=4)
        beat_now = int(np.argmax(bb))
        self.g_beat_idx = beat_now
        self.g_tempo_i = i

    def _period_frames(self) -> float:
        """Reported period: least squares over the recent emitted beats whose intervals agree with each other (so the
        BPM shown is the BPM of the beats actually emitted); the master grid's period until there are three."""
        bf = self.beat_frames[-9:]
        if len(bf) >= 3:
            iv = np.diff(bf)
            ref = float(np.median(iv[-3:]))
            k = len(bf) - 1
            while k > 0 and abs((bf[k] - bf[k - 1]) / ref - 1.0) < 0.12:
                k -= 1
            tail = bf[k:]
            if len(tail) >= 3:
                n = np.arange(len(tail), dtype=float)
                return float(np.polyfit(n, np.array(tail), 1)[0])
        return float(self.g_period)

    def _emit(self, frame: int) -> List[dict]:
        self._read_grid(frame)
        M = self.g_period
        beat_f = self.g_beat_f
        since = frame - beat_f                                  # frames since that beat line
        gap = beat_f - self.last_emit_f
        out: List[dict] = []
        if gap >= 0.6 * M and since <= 0.25 * M:
            self.beat_frames.append(beat_f)                     # a new beat, announced as the pointer crosses it
        elif abs(gap) <= 3.0 and frame - self.last_emit_f <= 4 and abs(gap) >= 0.5 and self.beat_frames:
            self.beat_frames[-1] = beat_f                       # sharpened by the onset just seen: last word
        else:
            return out
        self.last_emit_f = beat_f
        if len(self.beat_frames) > 64:
            del self.beat_frames[:-32]
        P = self._period_frames()
        bi = self.g_beat_idx
        out.append({"t_beat": beat_f * self.dt, "bpm": 60.0 / (P * self.dt), "phase": bi / 4.0,
                    "confidence": self.conf, "is_downbeat": bool(bi == 0)})
        return out

    def predict(self, now: float) -> List[dict]:
        if self.f < 0:
            return []
        P = self._period_frames()
        base = self.g_beat_f
        bi = self.g_beat_idx
        out = []
        k = 1
        while len(out) < 4 and k < 32:
            t = (base + k * P) * self.dt
            if t > now:
                out.append({"t_beat": t, "bpm": 60.0 / (P * self.dt), "phase": float((bi + k) % 4) / 4.0,
                            "confidence": self.conf, "is_downbeat": (bi + k) % 4 == 0})
            k += 1
        return out
