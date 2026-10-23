"""Bright-bass probe (2026-10-22, run after scoring; not a registered row of the pre-registration).

The beat_w auditor's finding, applied to every contestant: the drift suite's sub-bass is a pure sine, while real
half-time bass music (TYNAN) has harmonic-rich bass. This rebuilds the drift cases with a sawtooth bass (same pitch
drop, same envelope, same syncopated 16ths), and with that saw low-passed at ~400 Hz, and scores all trackers.
Run from the repo root: py research/reviewed/keylab-liberation-2026-10-22/bright-bass-probe-2026-10-22.py"""
import sys, importlib
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, "E:/AI-Setup")
sys.stdout.reconfigure(encoding="utf-8")
from arsenal.keylab import beatbench as BB

RATE = 44100
TRACKERS = ["a", "g", "h", "w"]


def saw_bass(rate, lowpass_hz=None):
    n = int(0.22 * rate)
    t = np.arange(n) / rate
    freq = 55 + 15 * np.exp(-t * 40)
    ph = np.cumsum(freq) / rate
    x = 2.0 * (ph % 1.0) - 1.0
    if lowpass_hz:
        a = np.exp(-2 * np.pi * lowpass_hz / rate)          # one-pole low-pass, twice
        for _ in range(2):
            y = np.zeros_like(x)
            acc = 0.0
            for i, v in enumerate(x):
                acc = (1 - a) * v + a * acc
                y[i] = acc
            x = y / (np.max(np.abs(y)) + 1e-9)
    return (x * BB._env(n, rate, 0.15)).astype(np.float32)


def cases(kind):
    orig = BB._bass
    if kind == "saw":
        BB._bass = lambda rate: saw_bass(rate)
    elif kind == "saw_lp400":
        BB._bass = lambda rate: saw_bass(rate, 400.0)
    try:
        return [BB.synth_case(f"ht_{kind}_{b}", b, 40.0, RATE, style="halftime_bass") for b in (128, 140, 150)]
    finally:
        BB._bass = orig


def run(job):
    kind, name, i = job
    c = cases(kind)[i]
    m = importlib.import_module(f"arsenal.keylab.beat_{name}")
    s = BB.score(c, BB.run_tracker(m.Tracker, c))
    return kind, name, c.name, s


if __name__ == "__main__":
    jobs = [(k, n, i) for k in ("sine", "saw", "saw_lp400") for n in TRACKERS for i in range(3)]
    with Pool(8) as p:
        rows = p.map(run, jobs)
    agg = {}
    for kind, name, cname, s in rows:
        agg.setdefault((kind, name), []).append(s)
    print(f"{'bass':10} {'tracker':7} {'F':>6} {'CMLt':>6} {'AMLt':>6} {'est bpm (128/140/150)':>24}")
    for kind in ("sine", "saw", "saw_lp400"):
        for name in TRACKERS:
            rs = agg[(kind, name)]
            f = np.mean([r.get("F", 0) for r in rs]); c = np.mean([r.get("CMLt", 0) for r in rs])
            am = np.mean([r.get("AMLt", 0) for r in rs])
            est = "/".join(f"{r['est_bpm']:.0f}" for r in rs)
            print(f"{kind:10} {name:7} {f:6.3f} {c:6.3f} {am:6.3f} {est:>24}")
