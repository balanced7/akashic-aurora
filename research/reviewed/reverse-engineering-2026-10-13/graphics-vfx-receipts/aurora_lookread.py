"""Worked example A: read the LOOK of a house-owned frame from pixels alone, then grade the reading against the source.

Target: state/arsenal/shaders/cards/atmos-aurora/t0.00.png and t2.00.png (house card, Apache-2.0, source known:
arsenal/web/glsl/cards/atmos-aurora.card). CPU only. Reads the house CPU twins (does not edit them).

Receipt for research/reviewed/reverse-engineering-2026-10-13/graphics-vfx.md, worked example W2. Run: `py aurora_lookread.py`
from this folder; it prints and writes aurora_lookread.json beside itself. First run 2026-10-13 (Vandor seat, Opus).
Apache-2.0, Akashic Aurora.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import cv2
import numpy as np
from sklearn.cluster import KMeans

sys.path.insert(0, r"E:\AI-Setup")
from arsenal.shaders.twins import atmos as A  # noqa: E402
from arsenal.shaders.twins import tone as T  # noqa: E402

CARD = r"E:\AI-Setup\state\arsenal\shaders\cards\atmos-aurora"
W, H, X0 = 480, 270, 154
OUT = {}


def load(t):
    img = cv2.imread(fr"{CARD}\t{t:.2f}.png", cv2.IMREAD_COLOR)[:, :, ::-1].astype(np.float64)  # RGB codes 0..255
    return img


def twin_panel(t):
    """The card's right panel at time t, recomputed on the CPU from the source formulas (GL pixel centres)."""
    xs = np.arange(X0, W) + 0.5
    ys = (H - 1 - np.arange(H)) + 0.5                       # PNG row r -> GL pixel.y (origin bottom-left)
    px, py = np.meshgrid(xs, ys)
    alt = 80.0 + py / 270.0 * 260.0
    along = (px - 154.0) / 326.0 * 8.0
    hem = 100.0 + 6.0 * np.sin(0.9 * along + 0.35 * t) + 2.5 * np.sin(2.3 * along - 0.6 * t)
    bright = A.auroraProfile(alt, hem, 55.0)
    rays = A.auroraRays(1.5 * along, t, 7)
    emitted = 0.8 * A.auroraLineColor(alt, 0.35) * (bright * (0.3 + 0.7 * rays))[..., None]
    sky = np.array([0.002, 0.004, 0.012])
    paint = np.clip(T.displayHueSafeGamma(sky + emitted, 2.2), 0.0, 1.0)
    return paint * 255.0, alt, hem


def srgb_decode(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def oklab(rgb_codes):
    lin = srgb_decode(rgb_codes)
    m1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929],
                   [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
    m2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])
    return np.cbrt(lin @ m1.T) @ m2.T


# ---- 0. parity: is the twin a faithful stand-in for the GPU frame? (it lets us make frames we did not render)
for t in (0.0, 2.0):
    png = load(t)[:, X0:]
    tw, _, _ = twin_panel(t)
    d = np.abs(png - np.round(tw))
    OUT[f"parity_t{t:g}"] = {"mean_abs_code": round(float(d.mean()), 3), "p99_code": float(np.percentile(d, 99)),
                             "max_code": float(d.max())}

png2 = load(2.0)[:, X0:]

# ---- 1. palette: k-means in OKLab over the panel, area-weighted
lab = oklab(png2.reshape(-1, 3))
km = KMeans(n_clusters=5, n_init=4, random_state=0).fit(lab)
pal = []
for k in range(5):
    member = km.labels_ == k
    mean_code = png2.reshape(-1, 3)[member].mean(0)
    pal.append({"share": round(float(member.mean()), 3),
                "hex": "#%02x%02x%02x" % tuple(int(round(v)) for v in mean_code),
                "L": round(float(km.cluster_centers_[k][0]), 3)})
OUT["palette_oklab_k5"] = sorted(pal, key=lambda p: -p["share"])

# ---- 2. a constant from pixels: the green line's R/G ratio (source: 0.222, and hue-safe gamma keeps the ratio)
px = png2.reshape(-1, 3)
green_bright = px[(px[:, 1] > 200) & (px[:, 2] < 40)]
OUT["green_R_over_G"] = {"n_pixels": int(len(green_bright)),
                         "median": round(float(np.median(green_bright[:, 0] / green_bright[:, 1])), 4),
                         "source_constant": 0.222}

# ---- 3. a falloff from pixels: the scale height above the green body, under three decode assumptions
_, alt, hem = twin_panel(2.0)
alt_col = alt[:, 0]
mag = np.linalg.norm(png2, axis=-1) / 255.0                   # displayed magnitude per pixel
fits = {}
DECODES = {"none (codes treated as linear)": lambda m: m,
           "sRGB curve": lambda m: srgb_decode(m * 255.0),
           "magnitude gamma 2.2 (the true display transform)": lambda m: m ** 2.2}
for lo_km, hi_km in ((118, 158), (128, 160)):
    band = (alt_col > lo_km) & (alt_col < hi_km)              # pure green zone: |lineColor| constant here
    for name, decode in DECODES.items():
        hs = []
        for c in range(mag.shape[1]):
            m = mag[band, c]
            ok = m > 8 / 255.0
            if ok.sum() < 10:
                continue
            y = np.log(np.maximum(decode(m[ok]), 1e-9))
            slope = np.polyfit(alt_col[band][ok], y, 1)[0]
            if slope < 0:
                hs.append(-1.0 / slope)
        fits[f"{lo_km}-{hi_km} km | {name}"] = {"median_scale_height_km": round(float(np.median(hs)), 1),
                                                "columns": len(hs)}
fits["source_value_km"] = 55.0
OUT["scale_height_fit"] = fits

# ---- 4. an edge from pixels: the hem, as the half-maximum on the rising side, per column.
# NOTE: the half-maximum's offset above the hem is taken from the source profile shape (an inference a blind reader
# would have to fit); the truth curve `hem` is the grading key only, never an input to the measurement.
z = np.linspace(0, 40, 4001)
prof = A.auroraProfile(100.0 + z, 100.0, 55.0)
half_offset = float(z[np.argmax(prof >= 0.5)])                 # half of the LINEAR peak, above the hem
lum_lin = mag ** 2.2
hem_est = []
for c in range(lum_lin.shape[1]):
    colv = lum_lin[::-1, c]                                   # bottom -> top
    altv = alt_col[::-1]
    peak = colv.max()
    i = int(np.argmax(colv >= 0.5 * peak))
    hem_est.append(altv[i] - half_offset)
hem_est = np.array(hem_est)
hem_true = hem[0, :]
OUT["hem_from_pixels"] = {"half_max_offset_km_from_source_profile": round(half_offset, 2),
                          "rms_error_km": round(float(np.sqrt(np.mean((hem_est - hem_true) ** 2))), 2),
                          "km_per_pixel_row": round(260 / 270, 3),
                          "corr_with_true_hem": round(float(np.corrcoef(hem_est, hem_true)[0, 1]), 3)}

# ---- 5. motion from pixels: two drifting ray layers (the dual-scroll trick)
PX_PER_ALONG = 326.0 / 8.0
truth = {"coarse_px_per_s": round(0.21 / 1.5 * PX_PER_ALONG, 3), "fine_px_per_s": round(-0.53 / 4.65 * PX_PER_ALONG, 3)}


def ray_signal(panel, alt_col):
    rows = (alt_col > 125) & (alt_col < 150)
    return np.linalg.norm(panel[rows], axis=-1).mean(0)


def best_shift(a, b, maxs):
    a = (a - a.mean()) / (a.std() + 1e-9)
    b = (b - b.mean()) / (b.std() + 1e-9)
    best, arg = -9, 0
    scores = {}
    for s in range(-maxs, maxs + 1):
        if s >= 0:
            v = float(np.mean(a[: len(a) - s] * b[s:]))
        else:
            v = float(np.mean(a[-s:] * b[: len(b) + s]))
        scores[s] = v
        if v > best:
            best, arg = v, s
    return arg, best, scores


def bands(sig):
    lo = cv2.GaussianBlur(sig.reshape(1, -1).astype(np.float64), (0, 0), sigmaX=6).ravel()
    return lo, sig - lo


s0 = ray_signal(load(0.0)[:, X0:], alt_col)
s2 = ray_signal(png2, alt_col)
lo0, hi0 = bands(s0)
lo2, hi2 = bands(s2)
sh_lo, sc_lo, _ = best_shift(lo0, lo2, 25)
sh_hi, sc_hi, scores_hi = best_shift(hi0, hi2, 25)
top_hi = sorted(scores_hi.items(), key=lambda kv: -kv[1])[:3]
OUT["motion_two_frames_2s_apart"] = {"truth": truth,
                                     "lowpass_shift_px": sh_lo, "lowpass_px_per_s": sh_lo / 2.0,
                                     "highpass_shift_px": sh_hi, "highpass_px_per_s": sh_hi / 2.0,
                                     "highpass_top3_(shift,score)": [(k, round(v, 3)) for k, v in top_hi]}

# dense study from the twin: the column PEAK (hem-independent), log, band-pass per layer, several spacings
from arsenal.shaders.twins import noise as N  # noqa: E402
U = 8
crop = slice(40 * U, -40 * U)
up = lambda v: cv2.resize(np.asarray(v, float).reshape(1, -1), (len(v) * U, 1), interpolation=cv2.INTER_CUBIC).ravel()
blur = lambda u, sg: cv2.GaussianBlur(u.reshape(1, -1), (0, 0), sigmaX=sg * U).ravel()


def peak_sig(t):
    p = np.round(twin_panel(t)[0])
    return np.log(((np.linalg.norm(p, axis=-1) / 255.0) ** 2.2).max(0) + 1e-6)


along_px = (np.arange(X0, W) + 0.5 - 154.0) / 326.0 * 8.0
coarse_alone = lambda t: 0.5 + 0.5 * N.noiseValue2(np.stack([1.5 * along_px - 0.21 * t, np.zeros_like(along_px)], -1), 7)
cal = up(coarse_alone(0.0))
calib = {dt: round(best_shift(cal[crop], up(coarse_alone(dt))[crop], 8 * U)[0] / U / dt, 2) for dt in (0.25, 1.0)}
u0 = up(peak_sig(0.0))
study = {}
for dt in (1 / 30, 0.25, 0.5, 1.0):
    u1 = up(peak_sig(dt))
    row = {}
    fine0, fine1 = u0 - blur(u0, 2.0), u1 - blur(u1, 2.0)
    row["fine (residual under 2 px)"] = round(best_shift(fine0[crop], fine1[crop], int(U * 14 * dt + 3 * U))[0] / U / dt, 2)
    for lo_s, hi_s in ((4, 20), (8, 40)):
        c0, c1 = blur(u0, lo_s) - blur(u0, hi_s), blur(u1, lo_s) - blur(u1, hi_s)
        row[f"coarse band {lo_s}-{hi_s} px"] = round(best_shift(c0[crop], c1[crop], 8 * U)[0] / U / dt, 2)
    study[f"dt={dt:.3f}s"] = row
OUT["motion_dense_twin_study"] = {"truth": truth, "ruler_check_coarse_layer_alone_px_per_s": calib, "readings_px_per_s": study}

print(json.dumps(OUT, indent=1))
with open(Path(__file__).with_suffix(".json"), "w", newline="\n") as f:
    json.dump(OUT, f, indent=1)
