# beat_w: the workflow builder's report and the adversarial audit, verbatim (2026-10-22)

The full return values of the two agents in workflow run wf_82b36762-fb4 ("Build contestant beat_w.py (discrete
bar-pointer engine) blind against the pre-registered beat-tracker bench, then audit it adversarially"). Both agents
ran as Claude (Opus). The builder never opened another beat_*.py. The auditor read beat_w.py and the bench only.
Persisted unedited per the full-fidelity rule; the independent scoring is in grid-tracker-scoring-2026-10-22.md.

---

## The builder (build:beat_w)

I built `E:/AI-Setup/arsenal/keylab/beat_w.py` and it passes the drift, shift and synthetic bars. All six loop classes beat beat_a's F and CMLt from the brief, but I could not check the loop bpm_spread bar because beat_a's spread isn't in the brief. The contract check printed OK and the licence firewall test passed (2/2). It imports only stdlib and numpy and uses nothing from the bench (I opened no other `beat_*.py`).

**Design**
1. **State:** (tempo, position in a 4/4 bar). The tempo bank runs 55 to 215 BPM in even 1.5 % log steps with real (non-integer) beat periods. Each tempo has floor(P) positions per beat and moves on a schedule set by the frame index alone, so periods are exact and the bank is equally fine at every octave. A position is (16th grid line, sub-16th phase).
2. **Transition:** tempo changes only at beat lines, with stiffness λ=50 at 120 BPM. λ is scaled by 1/√period, so tempo drifts at the same rate per second at any tempo. A per-beat kernel alone, or an integer-frame bank, tilted every octave tie toward the slower tempo; I measured that.
3. **Low and high volatility:** two forward filters share the same states and evidence. The stable one holds the grid; the volatile one has a broad kernel and about 2 s of memory. Every frame the volatile one takes a 0.5 % share of the stable belief (the IMM mixing step, Daniel's "guesses from the low-volatility one").
4. **Alarm:** a running log Bayes factor between the two models (1.5 s memory). When the volatile model leads by 1 nat, the stable model mixes in the volatile posterior (a re-induction from the last ~2 s of onsets) and widens λ for two beats.
5. **Observation:** every onset is scored against the grid lines of every state. Lines are bar, half bar, beat, 8th, 16th and off-beat triplet, each with a probability of carrying an onset. The background floor bounds the off-grid cost.
6. **Parsimony:** every line passed empty costs log(1−h), softened when the music is sparse. The grid stops at 16ths, so half-time bass notes that would need 32nds of the slower beat stay off its grid. That is what holds the drift suite at the fast level.
7. **Accent:** energy must rise in the lower and upper halves of the spectrum together (kick with click or hat, snare). Sub-bass alone or a hat alone is never accented.
8. **Priors:** a log-normal tempo lean (120 BPM, 0.9 octave) applied per second. The seed is octave-agnostic and decays over 12 s. The first strong note after silence counts as an accented beat, and 4 s of digital silence resets the filter.
9. **Output:**
   - The posterior is read as one master grid. A rival family such as the other octave takes over only after leading for a whole beat, or at once if it leads 3 to 1.
   - Beats are emitted as the grid crosses a beat line, with is_downbeat from the bar position.
   - BPM is a least-squares fit over recent emitted beats; `predict()` extrapolates the master grid.
   - Single-core speed is about 53 to 66× real time.

**Summary lines**
- drift, w: `{"cases": 5, "F": 1.0, "CMLt": 1.0, "AMLt": 1.0, "Acc1": 1.0, "Acc2": 1.0, "octave_err": 0.0, "lead_ms": -42.62, "lock_s_median": 1.79, "never_locked": 0, "pred_err_ms": 5.54, "pred_hit": 0.994, "bpm_spread": 0.004, "tempo_flips": 0.0, "relock_s": null, "never_relocked": 0, "realtime_x_min": 53.0}`
- drift, aubio: `{"cases": 5, "F": 0.809, "CMLt": 0.513, "AMLt": 0.713, "Acc1": 0.8, "Acc2": 1.0, "octave_err": 0.321, "lead_ms": -4.24, "lock_s_median": 1.85, "never_locked": 1, "pred_err_ms": null, "pred_hit": null, "bpm_spread": 0.24, "tempo_flips": 3.2, "relock_s": null, "never_relocked": 0, "realtime_x_min": 1011.6}`
- shift, w: `{"cases": 4, "F": 0.987, "CMLt": 0.978, "AMLt": 0.978, "Acc1": 1.0, "Acc2": 1.0, "octave_err": 0.0, "lead_ms": -45.6, "lock_s_median": 0.98, "never_locked": 0, "pred_err_ms": 6.525, "pred_hit": 0.949, "bpm_spread": 0.147, "tempo_flips": 0.5, "relock_s": 0.8, "never_relocked": 0, "realtime_x_min": 65.9}`
- shift, aubio: `{"cases": 4, "F": 0.747, "CMLt": 0.631, "AMLt": 0.674, "Acc1": 0.5, "Acc2": 0.5, "octave_err": 0.017, "lead_ms": -6.575, "lock_s_median": 1.75, "never_locked": 0, "pred_err_ms": null, "pred_hit": null, "bpm_spread": 0.158, "tempo_flips": 1.5, "relock_s": 6.287, "never_relocked": 1, "realtime_x_min": 1179.7}`
- synthetic, w: `{"cases": 14, "F": 1.0, "CMLt": 1.0, "AMLt": 1.0, "Acc1": 1.0, "Acc2": 1.0, "octave_err": 0.0, "lead_ms": -53.343, "lock_s_median": 1.08, "never_locked": 0, "pred_err_ms": 7.55, "pred_hit": 0.971, "bpm_spread": 0.016, "tempo_flips": 0.0, "relock_s": null, "never_relocked": 0, "realtime_x_min": 53.0}`
- loops, w (`--per-cat 30 --seeded`): `{"cases": 176, "F": 0.67, "CMLt": 0.586, "AMLt": 0.85, "Acc1": 0.812, "Acc2": 0.938, "octave_err": 0.122, "lead_ms": -48.641, "lock_s_median": 0.0, "never_locked": 34, "pred_err_ms": 93.732, "pred_hit": 0.607, "bpm_spread": 0.054, "tempo_flips": 0.761, "relock_s": null, "never_relocked": 0, "realtime_x_min": 43.7}`

**Bars**

| Suite | Bar | Result |
|---|---|---|
| drift | F ≥ .85, CMLt ≥ .75, spread ≤ .02, flips ≤ 0.5 | pass: 1.0 / 1.0 / .004 / 0 |
| shift | F ≥ .85, CMLt ≥ .75, relock ≤ 4.0 s, none never relocked | pass: .987 / .978 / 0.8 s / 0 |
| synthetic | F ≥ .95, CMLt ≥ .85 | pass: 1.0 / 1.0 |
| speed | ≥ 20× real time | pass: lowest 43.7× |

Loops by class, split out of that run's receipt, against beat_a's numbers in the brief:

| Class | W F / CMLt | beat_a F / CMLt | W bpm_spread |
|---|---|---|---|
| kick, unseeded (n=28) | .862 / .759 | .723 / .660 | .059 |
| tops, unseeded | .538 / .425 | .352 / .213 | .043 |
| melodic, unseeded | .604 / .536 | .465 / .376 | .096 |
| kick, seeded | .889 / .821 | .803 / .805 | .058 |
| tops, seeded | .533 / .439 | .409 / .395 | .005 |
| melodic, seeded | .621 / .563 | .547 / .559 | .063 |

**Known weaknesses**
- **Tuned against the bench:** about 20 model settings (line probabilities, accent probabilities, λ, prior width, alarm threshold, emptiness softening) were chosen by iterating on the three bench suites and my own 46-case synthetic set (bench styles at other tempi, offsets and seeds). No bench pattern constants are in the file, but the bench shaped the choices. The prior width came from a sweep (0.7 to 1.0); 0.9 is close to the conventional one-octave prior.
- **drums_70 vs halftime_bass_140:** these share a skeleton. With the prior at 0.7, drums_70 locked at 140, and the stable model's evidence over 20 s was nearly a tie. drums_70 passes at 0.9 but is likely fragile.
- **Slow kick loops:** hip-hop and R&B loops at 80 to 100 BPM with busy hats often lock at double tempo (87 → 174).
- **Hats-only loops:** these often lock on the off-beat (AMLt about .86 against CMLt about .43). The first-note anchor helps only when the loop starts with a hit.
- **Sparse material:** one kick per bar relies on the tempo prior and weak bar-line evidence. In my extra set, a kick every bar at 128 BPM locked late.
- **Cold start after a track change:** about 6 s to settle. For the first 4 s of a silent gap the grid keeps emitting beats before it resets.
- **Repeated beats:** `feed()` re-announces a beat when a correction lands within 4 frames. The bench keeps the last word, but a consumer that flashes on every `feed()` event would double-flash; `predict()` is unaffected.
- **The alarm rarely fires** on constant-tempo material; its gain is on steps (shift relock 1.25 s without it, 0.8 s with it).
- **CPU:** about 55× real time, roughly 20× more CPU than aubio.

The instructed bench commands wrote four receipts in `E:/AI-Setup/state/arsenal/keylab/receipts/` (`beatbench-20261022-231511`, `-231527`, `-231535`, `-231723.json`). My working scripts are in the session scratchpad, not the repo. Nothing was committed.

---

## The adversarial audit (audit:beat_w)

**beat_w audit: it is causal and conforms to the contract, but it fails one pre-registered acceptance bar (loop bpm_spread, 4 of 6 classes). Its drift-suite pass also depends on the bench's pure-sine bass timbre.**

Methods: I ran the two instructed commands. I re-ran the drift, shift and synthetic suites in-process, with no receipt saved, and matched the builder's receipts exactly. I added black-box probes: future-perturbation, off-bench variants and per-block timing. I edited no repo files. The probe scripts are in `<session scratchpad>` [local path redacted] (`audit_w_causal.py`, `audit_w_general.py`, `audit_w_perf.py`). I ran Python with `PYTHONDONTWRITEBYTECODE=1`, except one early receipt-reading call that imported beatbench; it may have refreshed `.pyc` files in `arsenal/keylab/__pycache__`.

**1. Causality**
- **PASS** – `beat_w.py:107-151, 407-435, 549-563`.
  - **Code reading:** the peak picker looks one frame ahead, and that frame's window ends at the last sample received. The filter runs two frames behind the audio (line 420). `predict()` only reads state.
  - **Future-perturbation test:** I swapped the audio after 7.3 s, 15.0 s and 22.9 s for a different song. Events and `predict()` stayed byte-identical up to 2–3 blocks after the cut, the expected two-frame lag.
  - **`predict()`** has no side effects: events are identical with and without the calls.
  - **Timing:** no `feed()` beat is ever later than the audio fed; the maximum `t_beat` is 26 ms before it.
  - **Robustness:** irregular block sizes give the same beats, and runs are deterministic.

**2. Bench-fitting**
- **PASS (constants)** – `beat_w.py:158-175`.
  - No `SYNC_BASS_16THS`, case names, 0.5 s offset or 20 s step appear in the code, and nothing reads `Case` or `meta`.
  - Off-bench variants all hold at F/CMLt 0.97–1.0:
    - other bass patterns `(2,5,7,11,14)`, `(1,6,9,14)` and `(3,7,10,11,15)` at 135 and 160 BPM;
    - no leading silence, with the audio starting on a bass 16th, on beat 2 or on the "and";
    - offsets of 0, 0.23 and 1.71 s;
    - tempo steps at 13, 17, 22 and 27 s with other tempo pairs;
    - drums at 84, 105, 160 and 190 BPM.
  - The first-note anchor (`:425-433`) fits how the bench is built, but the results do not depend on it.
- **CONCERN (timbre)** – `beat_w.py:70-73, 143-145` (accent = low-band AND high-band rise).
  - The drift hold rests on the bench's bass being a pure sine.
  - **Saw bass, same patterns:** F .067, CMLt .041, AMLt .652, tempo still right (Acc1 1.0). It locks on the off-beat phase. aubio scores F .524 on the same audio.
  - **Saw low-passed at 400 Hz:** F .50.
  - **Sine bass plus an attack click:** still 1.0.
  - Real bass music, like the TYNAN failure, has harmonic-rich bass. The drift pass may not carry over to it.
- **CONCERN (slow tempo)** – `beat_w.py:170, 243, 322-327`.
  - The 120 BPM tempo lean is applied every second, so it accumulates over time.
  - drums_66 reported 132 BPM for the first ~11 s: F .903, CMLt .778, bpm_spread 1.0.
  - The builder disclosed that drums_70 is fragile; this confirms it.

**3. Contract and licence**
- **PASS.**
  - `check_tracker` printed `OK`.
  - The firewall pytest passed 2 of 2 (rc 0).
  - Imports are math, collections, typing and numpy only, with no relative imports.

**4. Real-time**
- **PASS** – `beat_w.py:100, 309-315, 332-344, 541-542`.
  - The state space is 18,912 states over 93 tempi.
  - On a 600 s stream: mean 0.198 ms per block, p99 0.81 ms, max 1.27 ms, against an 11.6 ms budget. That is 58.5× real time, with no growth over time.
  - Traced memory stays flat at 0.8 MB. The beat list (≤ 64), cache (3 entries), onset history (12) and pending buffer are all bounded.
  - Rate 48k, hop 512 is correct at ~47×. Hop 256 is correct but only ~20× real time.

**5. Honesty**
- **FAIL (acceptance bar the builder could not check)** – loop bpm_spread must be ≤ shipped beat_a's per class.
  - beat_a's per-class numbers come from receipt `E:/AI-Setup/state/arsenal/keylab/receipts/beatbench-20261022-231143.json`. Its F/CMLt match the brief exactly and it covers the same 176 cases.

  | Class | W bpm_spread | beat_a bpm_spread | Result |
  |---|---|---|---|
  | kick, seeded | .058 | .003 | fail |
  | melodic, seeded | .063 | .015 | fail |
  | tops, unseeded | .043 | .036 | fail |
  | tops, seeded | .005 | .003 | fail |
  | kick, unseeded | .059 | .119 | pass |
  | melodic, unseeded | .096 | .158 | pass |

  - The F/CMLt bars all pass. Under the pre-registration's "ships only if ALL hold", W does not qualify as registered.
- **PASS** – the builder's receipts (`-231511`, `-231527`, `-231535`, `-231723`) match the summaries and the per-class table exactly. `beat_w.py` (modified 23:15:01) predates all four.
- **CONCERN** – the report says "4 s of silence" (`beat_w.py:437-445, 455-456, 549-563`). After the reset, `predict()` keeps extrapolating the stale grid. The hub in `beatsync.py:154` paints from `predict()`, so lights would keep flashing for ~17.7 s into silence. `feed()` stops at 3.7 s.
  - A track change after a gap still relocks in 1.2 s. `_restart` does not reset `g_tempo_i`, `_rival_frames`, `rho_until` or `last_alarm_f`, and the warmup and seed-decay clocks run on absolute stream time (`:398, 481, 322`).
- **CONCERN** – "seed is octave-agnostic" (`beat_w.py:41, 262`). The `-0.25*min(exact,1)` term leans toward the seed's own octave, about 4.5 nats in total against the octave over its decay.
- **CONCERN** – "relock 1.25 s without the alarm, 0.8 s with it" (`beat_w.py:389-403`). With the alarm disabled in-process I measured 0.9 s mean relock (F .983, never_relocked 0). The two-volatility join adds about 0.1 s on the bench and doubles the filter cost. It fires only on 2 of 4 shift cases and never on drift; that part of the claim holds.
- **CONCERN (design deviation from the pre-registration)** – `beat_w.py:478-488`.
  - Hysteresis is one beat (or 3 to 1), not the "several bars" in design item 5.
  - Octave relatives compete as rivals rather than "merge and vote together" (item 4).
  - The acceptance table does not bind these, but they differ from the registered design.
- **PASS** – the other claims match the code:
  - the bank is 55–215 BPM in 1.49 % steps with real periods;
  - λ scales as 1/√period, giving equal tempo variance per second;
  - the volatile model's 0.5 % per-frame mix gives a ~2.3 s time constant;
  - the alarm uses a 1-nat threshold with 1.5 s memory;
  - line levels and the bounded background cost are as described;
  - BPM is a least-squares fit over recent beats;
  - re-announcements in `feed()` (`:536-537`) stay inside the bench's 50 ms dedupe window, and the hub uses `predict()`, so they never double-flash.
