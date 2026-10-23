"""arsenal.keylab.beat_g -- the grid tracker: hold the grid ALL the notes fit, follow real tempo changes.

Daniel's design (2026-10-22, live, after beat_a drifted on a half-time bass track), in his words:
  "detect the grid not just the spaced out notes and ... correct itself based on the grid keeping track of beats"
  "on what grid would all of these notes fit? ... multiple grid permutations simultaniously with a confidence
   score, then you can adjust so they all connect to the master and they all agree"
  "a higher and lower volitility setting that are smartly joined ... the volatile one could get guesses from the
   lower volitility one ... have shifting bpm"
Mechanical at runtime: numpy only, no model in the loop. Contract and scoring: arsenal/keylab/beatbench.py.
Research behind each choice: research/reviewed/keylab-liberation-2026-10-22/grid-research-*.md.

Layers:
  onsets     band-averaged log-magnitude flux in four bands, peak-picked with sub-frame (parabolic) timing. Each
             onset keeps its strength in every band and an ACCENT (strength times how many bands rose together).
  grid       question 1, "on what grid do all these notes fit": the lattice whose lines ALL recent onsets sit
             nearest, scored as a log-likelihood ratio against "anywhere at random" (strengths compressed, so a
             quiet hat counts and one freak onset cannot decide alone). A finer grid earns less per note (the
             random alternative gets likelier as lines crowd), so parsimony is the maths; it is subdivided by 2, 3
             or 4 while that pays, and a fit that needs a non-musical split (11 ways) falls back to its repeat.
  master     question 2, "which multiple of that grid is the beat, and which line is beat one": every (multiple,
             slot) reading of the one lattice is scored, so octave relatives agree on the grid and argue only
             about the level. The SLOT comes from the clearest band (hats mark the beat under loud off-beat bass,
             the kick's band marks it under off-beat hats) plus pulse continuity (a beat line always holds a
             note); the LEVEL from the combined accent, a log-normal tempo prior around 120, a cost for beats of
             1 or 8 tatums, and the seed (its family, and its own octave by a bounded amount). Triplet readings
             exist only when the accent pattern repeats in threes. A first reading must win several inductions
             running before it is protected; after that a rival must win repeatedly (longer for an octave).
  IMM        Interacting Multiple Model filter over [last beat time, period] with steady, ramp and step models
             (the low and high volatility settings). Each beat it is fed a robust (weighted-median) timing error
             of ALL onsets snapped to the master tatum grid -- never the nearest single note.
  alarm      CUSUM on the innovations of a separate, UNMIXED steady predictor. An alarm cuts the evidence window
             to the last few seconds and re-runs the grid search, then re-seeds the IMM: how a real tempo step
             relocks in about 4 s (7 s without it, measured).

Measured 2026-10-22 against the pre-registered acceptance: passes drift, shift and synthetic; trails beat_a on
real BPM-labelled loops (hip-hop octave, humanised and swung drums), so it is NOT shipped. Opt-in live trial:
`py -m arsenal.keylab beat --engine g`. Record: research/reviewed/keylab-liberation-2026-10-22/
grid-tracker-scoring-2026-10-22.md.
"""
from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

BPM_LO, BPM_HI = 60.0, 200.0
EDGES_HZ = (0.0, 150.0, 400.0, 2500.0)     # sub/kick, snare body, mids, hats
HIST_S = 6.0                # onset evidence window for the grid search
MAX_HIST_S = 10.0           # ... stretched up to this for sparse music, so it holds at least MIN_NOTES notes
MIN_NOTES = 16
ALARM_WINDOW_S = 2.5        # window right after a change alarm
INDUCE_EVERY_S = 0.5        # how often the grid search re-runs
MIN_EVIDENCE_S = 3.0        # before the first lock
SIGMA_T = 0.012             # onset timing tolerance on a grid line (s)
OFF_GRID_EPS = 0.08         # share of onsets allowed to be off-grid: small, so the grid must fit (nearly) ALL notes
PRIOR_CENTER, PRIOR_OCT = 120.0, 0.9        # log-normal tempo prior (octaves)
SEED_OCT = 0.08             # how close (octaves, folded) a tempo must be to count as the seed's family
SEED_FIT_SLACK = 0.3        # the seed's grid may fit the notes this much worse (mean LLR) and still compete
SEED_FAMILY_W = 1.0         # prior bonus for the seed's tempo family (any octave)
SEED_OCTAVE_W = 0.4         # ... and for the seed's own octave
SEED_OCTAVE_OCT = 0.12
SEED_HALF_LIFE_S = 600.0    # the seed fades slowly: a database tempo stays good for the whole track
LEVEL_SWITCH_AFTER = 3      # consecutive inductions a rival master must win before it takes over
OCTAVE_SWITCH_AFTER = 8     # ... and for an octave relative (same grid, other level: 70 <-> 140), about 4 s
PRIOR_W = 1.0               # weight of the (log) priors against accent contrast when choosing the beat level
COARSE_COST = 0.5           # per level of beat beyond 4 tatums (16ths read as half-time 8ths of 32nds)
SUBDIV_COST = 0.3           # per level of beat subdivision the notes do not show (see _level_table)
TERNARY_MARGIN = 0.05       # the accent pattern must repeat in threes by this much more than in twos
DESCEND_MIN = 0.10          # a subdivided lattice must explain the notes this much better (mean log-likelihood ratio)
ESTABLISH_AFTER = 3         # a first reading must win this many inductions running before hysteresis protects it
LEVEL_BY_ACCENT = True      # tempo level judged on the combined accent, beat slot on the clearest band
COVER_W = 0.8               # weight of pulse continuity (share of beat lines holding a note) in the level choice
CONFIRM_S = 0.09            # an expected beat is confirmed this long after it is due
CUSUM_K, CUSUM_H = 0.5, 6.0 # alarm drift and threshold, in units of normalized innovation
SILENCE_S = 2.5             # no onsets this long = coast, then re-acquire without hysteresis
BAND_FLOOR = 0.02           # minimum band scale (log-flux units), so a near-silent band cannot blow up
RISE_Z = 0.35               # a band "rises" at an onset when its flux reaches 35 % of its typical peak

# IMM: steady / ramp / step. Process noise on the period (s per beat); Markov switching per beat.
Q_PERIOD = (0.00015, 0.0012, 0.030)
Q_PHASE = (0.0008, 0.002, 0.010)
PI = np.array([[0.990, 0.008, 0.002],
               [0.040, 0.950, 0.010],
               [0.100, 0.100, 0.800]])


class Tracker:
    def __init__(self, rate: int, hop: int, seed_bpm: Optional[float] = None):
        self.rate, self.hop = int(rate), int(hop)
        self.n_fft = 1024 if rate <= 48000 else 2048
        self.win = np.hanning(self.n_fft).astype(np.float32)
        self.ring = np.zeros(self.n_fft, dtype=np.float32)
        self.pending = np.zeros(0, dtype=np.float32)
        freqs = np.fft.rfftfreq(self.n_fft, 1.0 / self.rate)
        edges = list(EDGES_HZ) + [self.rate / 2 + 1]
        self.bands = [np.where((freqs >= lo) & (freqs < hi))[0] for lo, hi in zip(edges[:-1], edges[1:])]
        self.prev = None
        self.frames = 0
        self.fr = self.rate / self.hop
        # rolling band flux, for onset picking and per-band normalisation
        n = int(4.0 * self.fr)
        self.flux = np.zeros((n, 4), dtype=np.float64)
        # onsets: time, strength, accent (bands rising together)
        self.on_t: List[float] = []
        self.on_w: List[float] = []
        self.on_a: List[float] = []
        self.on_z: List[np.ndarray] = []      # per-band strength of each onset (in units of the band's typical peak)
        self.last_onset_t = -1e9
        # grid / master
        self.seed = float(seed_bpm) if seed_bpm else None
        # lattice periods to scan: a 16th at 200 BPM up to a whole 4-beat bar at 60 BPM (a kick only on each bar)
        self.tau_grid = np.geomspace(60.0 / (BPM_HI * 4), 4 * 60.0 / BPM_LO, 900)
        self.tau_min = 60.0 / (BPM_HI * 4)
        self.master: Optional[dict] = None
        self._rival, self._rival_wins = None, 0
        self.master_age = 0
        self.next_induce = MIN_EVIDENCE_S
        self.window_s = HIST_S
        self.alarm_until = -1.0
        # IMM state
        self.x = None                      # per-model [last beat time, period]
        self.P = None                      # per-model 2x2 covariance
        self.mu = np.array([0.94, 0.05, 0.01])
        self.ref_x, self.ref_P = None, None   # the unmixed steady reference predictor
        self.cusum_pos = self.cusum_neg = 0.0
        self.next_beat: Optional[float] = None
        self.beat_index = 0
        self.slot_accent = np.zeros(4)
        self.conf = 0.0

    # --- clock ----------------------------------------------------------------------------------------------
    @property
    def now(self) -> float:
        return self.frames * self.hop / self.rate

    def _frame_time(self, idx: float) -> float:
        """Onset time of frame `idx` (0-based): the centre of its analysis window."""
        return ((idx + 1) * self.hop - self.n_fft / 2) / self.rate

    # --- the stream -----------------------------------------------------------------------------------------
    def feed(self, block) -> List[dict]:
        x = np.asarray(block, dtype=np.float32).reshape(-1)
        self.pending = np.concatenate([self.pending, x]) if len(self.pending) else x
        out: List[dict] = []
        while len(self.pending) >= self.hop:
            frame, self.pending = self.pending[: self.hop], self.pending[self.hop:]
            out.extend(self._frame(frame))
        return out

    def predict(self, now: Optional[float] = None) -> List[dict]:
        if self.next_beat is None or self.x is None:
            return []
        now = self.now if now is None else now
        period = self._period()
        t = self.next_beat
        while t <= now:
            t += period
        return [{"t_beat": float(t + k * period), "bpm": 60.0 / period, "phase": 0.0,
                 "confidence": round(self.conf, 3)} for k in range(4)]

    # --- per frame -----------------------------------------------------------------------------------------
    def _frame(self, samples: np.ndarray) -> List[dict]:
        self.ring = np.roll(self.ring, -len(samples))
        self.ring[-len(samples):] = samples
        mag = np.log1p(100.0 * np.abs(np.fft.rfft(self.ring * self.win)))
        flux = np.zeros_like(mag) if self.prev is None else np.maximum(mag - self.prev, 0.0)
        self.prev = mag
        bands = np.array([flux[b].mean() if len(b) else 0.0 for b in self.bands])
        self.flux = np.roll(self.flux, -1, axis=0)
        self.flux[-1] = bands
        self.frames += 1
        self._pick_onset()
        out: List[dict] = []
        if self.now >= self.next_induce:
            self._induce()
            self.next_induce = self.now + INDUCE_EVERY_S
        if self.next_beat is not None and self.now >= self.next_beat + CONFIRM_S:
            ev = self._confirm()
            if ev:
                out.append(ev)
        return out

    def _pick_onset(self) -> None:
        """Peak-pick the frame two hops back (so its neighbours on both sides are known): local maximum of the
        band-normalised onset function above an adaptive threshold, timed below the frame by a parabola."""
        f = self.flux
        n = min(self.frames, len(f))
        if n < 12:
            return
        hist = f[-n:]
        # Each band in units of its own typical PEAK (95th percentile), floored. A median scale explodes in a band
        # that is silent most of the time (median ~0), and one band then outvotes the rest by numerical accident.
        scale = np.maximum(np.percentile(hist, 95, axis=0), BAND_FLOOR)
        z = hist / scale
        odf = z.sum(axis=1)
        c = len(odf) - 3                                     # the candidate frame
        if not (odf[c] >= odf[c - 1] and odf[c] > odf[c + 1] and odf[c] >= odf[c - 2] and odf[c] >= odf[c + 2]):
            return
        local = odf[max(0, c - int(0.8 * self.fr)):c + 1]
        thr = np.median(local) + 1.5 * (np.percentile(local, 75) - np.percentile(local, 25)) + 0.15
        if odf[c] < thr:
            return
        y0, y1, y2 = odf[c - 1], odf[c], odf[c + 1]
        den = y0 - 2 * y1 + y2
        delta = 0.5 * (y0 - y2) / den if den < 0 else 0.0
        idx = (self.frames - n) + c + float(np.clip(delta, -0.5, 0.5))
        t = self._frame_time(idx)
        if t - self.last_onset_t < 0.03:                    # one onset per 30 ms
            return
        rising = z[c] > RISE_Z
        accent = float(odf[c]) * (0.5 + 0.5 * max(0, int(rising.sum()) - 1))
        self.on_t.append(t)
        self.on_w.append(float(odf[c]))
        self.on_a.append(accent)
        self.on_z.append(z[c].copy())
        self.last_onset_t = t
        horizon = self.now - MAX_HIST_S - 1.0
        while self.on_t and self.on_t[0] < horizon:
            self.on_t.pop(0); self.on_w.pop(0); self.on_a.pop(0); self.on_z.pop(0)

    # --- the grid search ------------------------------------------------------------------------------------
    def _evidence(self, window_s: float, stretch: bool = True):
        t = np.array(self.on_t)
        if not len(t):
            return None
        if stretch and len(t) >= MIN_NOTES:
            # sparse music (a kick on each bar) needs a longer look to see the pattern repeat twice
            window_s = min(MAX_HIST_S, max(window_s, self.now - float(t[-MIN_NOTES])))
        keep = t >= self.now - window_s
        if keep.sum() < 6:
            return None
        return t[keep], np.array(self.on_w)[keep], np.array(self.on_a)[keep], np.array(self.on_z)[keep]

    @staticmethod
    def _llr_scan(t, w, taus):
        """Mean log-likelihood ratio of the onsets (t, weights w) sitting near the lines of each lattice in taus
        versus anywhere at random, with each lattice at its best anchor (closed form: the circular mean)."""
        wn = w / (w.sum() + 1e-9)
        ph = np.exp(2j * np.pi * t[None, :] / taus[:, None])
        res = (ph * wn[None, :]).sum(axis=1)
        anchor = (np.angle(res) / (2 * np.pi)) % 1.0 * taus
        r_s = (((t[None, :] - anchor[:, None]) / taus[:, None] + 0.5) % 1.0 - 0.5) * taus[:, None]
        on_grid = np.exp(-0.5 * (r_s / SIGMA_T) ** 2) / (math.sqrt(2 * math.pi) * SIGMA_T)
        llr = np.log((1 - OFF_GRID_EPS) * on_grid * taus[:, None] + OFF_GRID_EPS)
        return (llr * wn[None, :]).sum(axis=1), anchor

    def _refine(self, t, w, tau, span):
        """Best (period, anchor) near tau. The circular-mean anchor is pulled between grid notes and off-grid
        ones, so the phases of the strongest notes are tried as anchors too."""
        taus = tau * np.linspace(1 - span, 1 + span, 41)
        s, a = self._llr_scan(t, w, taus)
        j = int(np.argmax(s))
        best = (float(s[j]), float(taus[j]), float(a[j]))
        wn = w / (w.sum() + 1e-9)
        for i in np.argsort(-w)[:6]:
            anc = t[i] % taus
            r_s = (((t[None, :] - anc[:, None]) / taus[:, None] + 0.5) % 1.0 - 0.5) * taus[:, None]
            on_grid = np.exp(-0.5 * (r_s / SIGMA_T) ** 2) / (math.sqrt(2 * math.pi) * SIGMA_T)
            sc = (np.log((1 - OFF_GRID_EPS) * on_grid * taus[:, None] + OFF_GRID_EPS) * wn[None, :]).sum(axis=1)
            k = int(np.argmax(sc))
            if sc[k] > best[0]:
                best = (float(sc[k]), float(taus[k]), float(anc[k]))
        return best[1], best[2], best[0]

    def _lattice(self, t, w):
        """Question 1 -- on what grid do ALL these notes fit? The best lattice at any period, then subdivided by
        2, 3 or 4 for as long as the finer grid explains the notes better than it costs. A finer lattice earns
        less per note (the random alternative gets likelier as lines crowd), so parsimony is the maths; and a fit
        that needs a non-musical split falls back to the repeat (see below)."""
        score, _ = self._llr_scan(t, w, self.tau_grid)
        i = int(np.argmax(score))
        tau, anchor, base = self._refine(t, w, float(self.tau_grid[i]), 0.01)
        while True:
            best = None
            for k in (2, 3, 4):
                if tau / k < self.tau_min * 0.98:
                    continue
                s = self._llr_at(t, w, tau / k)
                if best is None or s > best[0]:
                    best = (s, k)
            if best is None or best[0] <= base + DESCEND_MIN:
                break
            tau, anchor, base = self._refine(t, w, tau / best[1], 0.004)
        # A grid can fit every note in a musically impossible way: a kick on each bar plus the click of its own
        # tail 1/11 of a bar later fits an 11-way split exactly. Music divides in twos and threes, so when the notes
        # sit sparsely on the lattice and repeat every P lines with P not of the form 2^a 3^b, the real grid is
        # the repeat itself, and the in-between notes are ornaments.
        P = self._odd_repeat(t, tau, anchor)
        if P:
            tau, anchor, base = self._refine(t, w, tau * P, 0.004)
        return tau, anchor, base

    @staticmethod
    def _smooth(n: int) -> bool:
        while n % 2 == 0:
            n //= 2
        while n % 3 == 0:
            n //= 3
        return n == 1

    def _odd_repeat(self, t, tau, anchor) -> int:
        pos = np.round((t - anchor) / tau).astype(int)
        near = np.abs((t - anchor) / tau - pos) < 0.3
        if near.sum() < 4:
            return 0
        p = pos[near] - pos[near].min()
        occ = np.zeros(p.max() + 1)
        occ[p] = 1.0
        K = len(occ)
        if occ.mean() >= 0.5:
            return 0
        best_odd, best_smooth = (0.0, 0), 0.0
        for L in range(2, K // 2 + 1):
            if K - L < 8:
                break
            x, y = occ[:K - L], occ[L:]
            den = math.sqrt(float(x @ x) * float(y @ y))
            r = float(x @ y) / den if den > 0 else 0.0
            if self._smooth(L):
                best_smooth = max(best_smooth, r)
            elif r > best_odd[0]:
                best_odd = (r, L)
        if best_odd[1] and best_odd[0] > best_smooth + 0.2 and tau * best_odd[1] <= self.tau_grid[-1]:
            return best_odd[1]
        return 0

    def _llr_at(self, t, w, tau: float) -> float:
        """How well ALL onsets fit one lattice of spacing tau (best anchor, closed form): mean log-likelihood ratio."""
        wn = w / (w.sum() + 1e-9)
        res = (np.exp(2j * np.pi * t / tau) * wn).sum()
        anchor = (np.angle(res) / (2 * np.pi)) % 1.0 * tau
        r_s = (((t - anchor) / tau + 0.5) % 1.0 - 0.5) * tau
        on_grid = np.exp(-0.5 * (r_s / SIGMA_T) ** 2) / (math.sqrt(2 * math.pi) * SIGMA_T)
        return float((np.log((1 - OFF_GRID_EPS) * on_grid * tau + OFF_GRID_EPS) * wn).sum())

    def _periodicity(self, t, a, tau, anchor):
        """How the accent pattern repeats, in tatums: the best normalised autocorrelation of the per-tatum accent
        sequence at a binary lag (2, 4, 8, 16) and at a lag that is a multiple of three (3, 6, 12). Straight
        music repeats every 4 / 8 / 16 tatums; swing, triplet feel and 3/4 or 6/8 bars repeat every 3 / 6 / 12. A
        syncopated bass in groups of three sixteenths (3-3-2) does NOT repeat at 3 over a whole bar, which is
        what separates it from a real triplet feel."""
        pos = np.round((t - anchor) / tau).astype(int)
        near = np.abs((t - anchor) / tau - pos) < 0.3
        if near.sum() < 4:
            return 0.0, 0.0
        p = pos[near] - pos[near].min()
        s = np.bincount(p, weights=a[near])
        K = len(s)

        def r(L):
            if K - L < max(8, L // 2):
                return None
            x, y = s[:K - L], s[L:]
            den = math.sqrt(float(x @ x) * float(y @ y))
            return float(x @ y) / den if den > 0 else 0.0

        binary = [v for v in (r(2), r(4), r(8), r(16)) if v is not None]
        ternary = [v for v in (r(3), r(6), r(12)) if v is not None]
        return (max(binary) if binary else 0.0), (max(ternary) if ternary else 0.0)

    def _level_table(self, t, a, w, tau, anchor, window_s, ternary: Optional[bool] = None, Z=None):
        """Every (multiple, slot) reading of one lattice, scored. Rows: (score, bpm, m, slot, contrast, prior,
        cost). Multiples below 1 are beats the lattice only implies (a kick on every bar implies four beats in it)."""
        if ternary is None:
            rb, rt = self._periodicity(t, a, tau, anchor)
            ternary_ok = rt > rb + TERNARY_MARGIN
        else:
            ternary_ok = ternary
        pos = np.round((t - anchor) / tau).astype(int)
        near = np.abs((t - anchor) / tau - pos) < 0.3
        occupied = np.unique(pos[near])
        if len(occupied):
            all_lines = np.arange(occupied.min(), occupied.max() + 1)
        else:
            all_lines = np.zeros(0, dtype=int)
        lattice_cover = len(occupied) / max(1, len(all_lines))
        # per (multiple, slot): accent contrast of its lines against the other tatum lines, and pulse continuity
        # (the share of its lines holding a note: a beat is felt on EVERY beat line, so loud syncopated bass that
        # fills some off-beat lines but leaves gaps loses to quiet hats on every beat). Computed for every whole
        # multiple.
        n_lat = max(1.0, window_s / tau)
        feats = [a]
        if Z is not None and len(Z):
            for b in range(Z.shape[1]):
                zb = Z[:, b]
                feats.append(np.minimum(zb, 4.0 * float(np.median(zb)) + 1e-9))
        stats = {}
        for mi in (2, 3, 4, 6, 8):
            if mi in (3, 6) and not ternary_ok:
                continue
            n_beat_lines = max(1.0, n_lat / mi)
            n_off_lines = max(1.0, n_lat - n_beat_lines)
            per = []
            for slot in range(mi):
                on = near & (pos % mi == slot)
                off = near & (pos % mi != slot)
                # the clearest instrument decides: contrast in each band on its own (the hats' band marks the
                # beat in half-time bass music, the kick's band marks it under off-beat hats) and in the combined
                # accent; a slot is as good as the band that marks it most clearly
                cs = []
                for v in feats:
                    mean_on = v[on].sum() / n_beat_lines
                    mean_off = v[off].sum() / n_off_lines
                    cs.append((mean_on - mean_off) / (mean_on + mean_off + 1e-9))
                lines = all_lines[all_lines % mi == slot]
                cover = (np.isin(lines, occupied).sum() / len(lines)) if len(lines) else 0.0
                per.append((float(max(cs)), float(cs[0]), float(cover)))
            stats[mi] = per
        rows = []
        for m in (0.125, 0.25, 1 / 3, 0.5, 1, 2, 3, 4, 6, 8):
            bpm = 60.0 / (m * tau)
            if not (BPM_LO <= bpm <= BPM_HI):
                continue
            if self._is_ternary(m) and not ternary_ok:
                continue
            # a beat split into 2, 3 or 4 tatums (8ths, triplets, 16ths) is the usual case; the beat being the finest
            # grid itself (m = 1) costs a little, each level of subdivision the notes do not show costs more, and
            # so does a beat of 6 or 8 tatums (a 16th lattice read as half-time 8ths of 32nds)
            lm = math.log2(m)
            cost = SUBDIV_COST * max(0.0, 1.0 - lm) + COARSE_COST * max(0.0, lm - 2.0)
            prior = self._prior(bpm)
            if m < 2:
                # pulse continuity for a beat at or below the lattice: the share of its lines holding a note
                cover = min(1.0, m) * lattice_cover
                rows.append((float(PRIOR_W * prior - cost + COVER_W * cover), float(bpm), m, 0, 0.0, float(prior),
                             float(cost), float(cover)))
                continue
            mi = int(round(m))
            for slot in range(mi):
                c_max, c_acc, cover = stats[mi][slot]
                # WHICH slot is the beat: the clearest band; HOW FAST the beat is: the combined accent (hats on
                # every 8th are the clearest band in a boom-bap loop, yet they mark its subdivision, not its beat)
                phase = c_max + COVER_W * cover
                level = (c_acc if LEVEL_BY_ACCENT else c_max) + COVER_W * cover + PRIOR_W * prior - cost
                rows.append((float(level), float(bpm), mi, slot, float(c_max), float(prior), float(cost),
                             float(cover), float(phase)))
        if LEVEL_BY_ACCENT:
            # one row per level: its best slot by phase evidence, scored by level evidence
            keep = {}
            for r in rows:
                k = round(r[1], 3)
                if k not in keep or (len(r) > 8 and r[8] > keep[k][8]):
                    keep[k] = r
            rows = list(keep.values())
        rows.sort(key=lambda r: -r[0])
        return rows

    def _levels(self, t, a, w, tau, anchor, window_s, ternary: Optional[bool] = None, Z=None):
        """Question 2 -- which multiple of the lattice is the BEAT, and which tatum is beat one? Every
        (multiple, slot) is a permutation of the same grid; they are scored by accent CONTRAST (beat lines vs
        the other tatum lines, accent = bands rising together), the tempo prior and the seed, and a cost for
        beats whose subdivisions the notes do not show. The ternary readings exist only when the accent pattern
        repeats in threes. Octave relatives therefore agree on one lattice and only argue about the level."""
        rows = self._level_table(t, a, w, tau, anchor, window_s, ternary, Z)
        if not rows:
            return None
        total, bpm, m, slot, contrast = rows[0][:5]
        h = {"total": total, "bpm": bpm, "div": m, "slot": slot, "tat": tau, "anchor": anchor,
             "contrast": contrast}
        h["seed_family"] = any(self._in_seed_family(r[1]) for r in rows)
        return h

    def _in_seed_family(self, bpm: float) -> bool:
        if not self.seed:
            return False
        d = math.log2(bpm / self.seed)
        return abs(d - round(d)) < 0.05

    def _prior(self, bpm: float) -> float:
        lp = -0.5 * (math.log2(bpm / PRIOR_CENTER) / PRIOR_OCT) ** 2
        if self.seed:
            fade = 0.5 ** (self.now / SEED_HALF_LIFE_S)
            # the seed favours its FAMILY (any octave), and its own octave by a bounded amount: a database tempo
            # is usually right, but strong evidence for the other octave (a seed off by an octave) must still win
            d = math.log2(bpm / self.seed)
            fam_d = d - round(d)
            lp += fade * (SEED_FAMILY_W * math.exp(-0.5 * (fam_d / SEED_OCT) ** 2)
                          + SEED_OCTAVE_W * math.exp(-0.5 * (d / SEED_OCTAVE_OCT) ** 2))
        return lp

    def _induce(self) -> None:
        alarmed = self.now < self.alarm_until
        window = ALARM_WINDOW_S if alarmed else self.window_s
        ev = self._evidence(window, stretch=not alarmed)
        if ev is None:
            if self.now - self.last_onset_t > 2 * SILENCE_S:
                self.master = None
            return
        t, w, a, Z = ev
        # compress and cap the note strengths: the grid is about WHERE notes sit, and one freak onset (the first
        # kick after silence normalises to hundreds of times a hat) must not decide it alone
        w = np.sqrt(w)
        w = np.minimum(w, 3.0 * float(np.median(w)))
        a = np.minimum(a, 4.0 * float(np.median(a)))
        tau, anchor, fit = self._lattice(t, w)
        # a tempo change keeps the meter: after an alarm, the short window may not overturn the master's family
        ternary = None
        if alarmed and self.master is not None:
            ternary = self._is_ternary(self.master["div"])
        best = self._levels(t, a, w, tau, anchor, window, ternary, Z)
        if self.seed and best is not None and not best["seed_family"]:
            # the free search settled on a lattice whose levels never include the seed's tempo (swung 16ths read as
            # a 7-way split), so no prior could pick it: let the seed's own 8th / 16th grid compete, if it explains
            # the notes nearly as well (after a real tempo change it will not, and the free reading stands)
            for k in (2, 4):
                st, sa, sf = self._refine(t, w, 60.0 / self.seed / k, 0.015)
                if sf < fit - SEED_FIT_SLACK:
                    continue
                cand = self._levels(t, a, w, st, sa, window, ternary, Z)
                if cand is not None and cand["total"] > best["total"]:
                    best, fit = cand, sf
        if best is None:
            return
        best["fit"] = fit
        self.conf = float(np.clip(fit / 1.5, 0.0, 1.0))
        if self.master is None or alarmed or self.master_age < ESTABLISH_AFTER:
            # nothing established yet: the best reading leads until one has won ESTABLISH_AFTER inductions running
            if self.master is not None and not alarmed and self._same(best, self.master):
                self.master_age += 1
                return
            self._adopt(best)
            self.master_age = 1
            return
        if self._same(best, self.master):
            self.master_age += 1
            self._rival, self._rival_wins = None, 0
            return
        if self._rival is not None and self._same(best, self._rival):
            self._rival_wins += 1
        else:
            self._rival, self._rival_wins = best, 1
        rel = best["bpm"] / self._bpm()
        need = OCTAVE_SWITCH_AFTER if abs(abs(math.log2(rel)) - 1.0) < 0.05 else LEVEL_SWITCH_AFTER
        if self._rival_wins >= need:
            self._adopt(best)
            self.master_age = 1
            self._rival, self._rival_wins = None, 0

    @staticmethod
    def _is_ternary(div) -> bool:
        return any(abs(div - d) < 1e-6 for d in (3, 6, 1 / 3))

    def _beat_line(self, h: dict) -> float:
        return h["anchor"] + (h["slot"] * h["tat"] if h["div"] >= 1 else 0.0)

    def _same(self, h: dict, ref: dict) -> bool:
        """Same reading: tempo within 3 % AND beat lines within 15 % of a beat of each other (a same-tempo
        reading on the off-beat is a rival, not a confirmation)."""
        if abs(math.log2(h["bpm"] / ref["bpm"])) >= 0.03:
            return False
        period = 60.0 / ref["bpm"]
        if ref is self.master and self.next_beat is not None:
            line = self.next_beat
        else:
            line = self._beat_line(ref)
        off = ((self._beat_line(h) - line) / period + 0.5) % 1.0 - 0.5
        return abs(off) < 0.15

    def _adopt(self, h: dict) -> None:
        """Make hypothesis h the master and (re)seed the IMM from it."""
        self.master = h
        period = 60.0 / h["bpm"]
        # the most recent beat line at or before now: anchor on the tatum lattice + the beat slot
        first = h["anchor"] + h["slot"] * h["tat"]
        k = math.floor((self.now - first) / period)
        last_beat = first + k * period
        x0 = np.array([last_beat, period])
        P0 = np.diag([0.01 ** 2, (0.01 * period) ** 2])
        self.x = np.array([x0.copy() for _ in range(3)])
        self.P = np.array([P0.copy() for _ in range(3)])
        self.mu = np.array([0.94, 0.05, 0.01])
        self.ref_x, self.ref_P = x0.copy(), P0.copy()
        self.cusum_pos = self.cusum_neg = 0.0
        nb = last_beat + period
        while nb <= self.now - CONFIRM_S:
            nb += period
        self.next_beat = nb

    # --- the IMM ---------------------------------------------------------------------------------------------
    def _period(self) -> float:
        return float(self.mu @ self.x[:, 1]) if self.x is not None else 0.5

    def _bpm(self) -> float:
        return 60.0 / self._period()

    def _measure(self, expected: float, period: float):
        """Robust timing error of ALL recent onsets snapped to the master tatum grid around the expected beat."""
        if not self.on_t:
            return None, None
        t = np.array(self.on_t); w = np.array(self.on_w)
        sel = (t >= expected - period * 1.5) & (t <= expected + period * 0.6)
        if sel.sum() < 2:
            return None, None
        div = self.master["div"] if self.master else 4
        tat = period / max(1, div)        # a beat the lattice only implies (div < 1) snaps to the beat itself
        r = ((t[sel] - expected) / tat + 0.5) % 1.0 - 0.5
        r_s = r * tat
        ws = w[sel]
        order = np.argsort(r_s)
        cw = np.cumsum(ws[order])
        med = float(r_s[order][np.searchsorted(cw, cw[-1] / 2)])
        spread = float(np.sqrt(np.average((r_s - med) ** 2, weights=ws)))
        n_eff = ws.sum() ** 2 / (np.sum(ws ** 2) + 1e-9)
        R = max(0.003, min(0.03, spread)) ** 2 / max(1.0, n_eff)
        return expected + med, R

    def _imm_step(self, z: Optional[float], R: Optional[float]) -> None:
        F = np.array([[1.0, 1.0], [0.0, 1.0]])
        H = np.array([[1.0, 0.0]])
        cbar = PI.T @ self.mu
        mix = (PI * self.mu[:, None]) / (cbar[None, :] + 1e-12)            # mix[i, j] = P(i | j)
        x0 = np.einsum("ij,ik->jk", mix, self.x)
        P0 = np.zeros_like(self.P)
        for j in range(3):
            for i in range(3):
                d = (self.x[i] - x0[j])[:, None]
                P0[j] += mix[i, j] * (self.P[i] + d @ d.T)
        like = np.ones(3)
        for j in range(3):
            Q = np.diag([Q_PHASE[j] ** 2, Q_PERIOD[j] ** 2])
            xp = F @ x0[j]
            Pp = F @ P0[j] @ F.T + Q
            if z is None:
                self.x[j], self.P[j] = xp, Pp
                continue
            S = float((H @ Pp @ H.T)[0, 0]) + R
            K = (Pp @ H.T) / S
            nu = z - float((H @ xp)[0])
            self.x[j] = xp + (K * nu).ravel()
            self.P[j] = (np.eye(2) - K @ H) @ Pp
            like[j] = math.exp(-0.5 * nu * nu / S) / math.sqrt(2 * math.pi * S)
        if z is not None:
            self.mu = cbar * like
            self.mu = self.mu / (self.mu.sum() + 1e-300)
        else:
            self.mu = cbar
        # the unmixed steady reference and its CUSUM alarm
        Qs = np.diag([Q_PHASE[0] ** 2, Q_PERIOD[0] ** 2])
        rx = F @ self.ref_x
        rP = F @ self.ref_P @ F.T + Qs
        if z is not None:
            S = float((H @ rP @ H.T)[0, 0]) + R
            K = (rP @ H.T) / S
            nu = z - float((H @ rx)[0])
            self.ref_x, self.ref_P = rx + (K * nu).ravel(), (np.eye(2) - K @ H) @ rP
            u = nu / math.sqrt(S)
            self.cusum_pos = max(0.0, self.cusum_pos + u - CUSUM_K)
            self.cusum_neg = max(0.0, self.cusum_neg - u - CUSUM_K)
            if self.cusum_pos > CUSUM_H or self.cusum_neg > CUSUM_H:
                self._alarm()
        else:
            self.ref_x, self.ref_P = rx, rP

    def _alarm(self) -> None:
        """A real tempo change: cut the evidence to the last few seconds and re-search at any ratio."""
        self.alarm_until = self.now + 3.0
        self.cusum_pos = self.cusum_neg = 0.0
        self.next_induce = self.now           # re-search on the very next frame

    def _confirm(self) -> Optional[dict]:
        expected = self.next_beat
        period = self._period()
        z, R = self._measure(expected, period)
        self._imm_step(z, R)
        if self.x is None:
            return None
        beat_t = float(self.mu @ self.x[:, 0])
        period = self._period()
        if not (60.0 / BPM_HI * 0.9 <= period <= 60.0 / BPM_LO * 1.1):
            self.master = None
            self.next_beat = None
            return None
        self.next_beat = beat_t + period
        self.beat_index += 1
        # bar position: which of 4 beat slots carries the most accent (the kick / downbeat)
        acc = self._accent_near(beat_t, period * 0.15)
        self.slot_accent *= 0.97
        self.slot_accent[self.beat_index % 4] += acc
        down = None
        if self.slot_accent.sum() > 0 and self.beat_index >= 8:
            down = bool(self.beat_index % 4 == int(np.argmax(self.slot_accent)))
        steady = float(self.mu[0])
        conf = float(np.clip(0.6 * self.conf + 0.4 * steady, 0.0, 1.0))
        return {"t_beat": beat_t, "bpm": 60.0 / period, "phase": 0.0, "confidence": round(conf, 3),
                "is_downbeat": down}

    def _accent_near(self, t0: float, tol: float) -> float:
        if not self.on_t:
            return 0.0
        t = np.array(self.on_t); a = np.array(self.on_a)
        sel = np.abs(t - t0) <= tol
        return float(a[sel].sum())
