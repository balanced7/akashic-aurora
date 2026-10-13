"""Worked examples B, C, D: calibrate each measuring tool on a look we built ourselves (known truth) before trusting it
on anything else. CPU only, numpy + OpenCV. House images are read, never written.

B. Hald CLUT capture of a per-pixel grade, and the two tests that say when a LUT CANNOT capture a look.
C. Bloom ruler: threshold, tail shape, and the code-value trap, on a frame with a known mip-chain bloom.
D. Particle counting, hit-stop and screen-shake detection on a synthetic clip with known counts and offsets.

Receipt for research/reviewed/reverse-engineering-2026-10-13/graphics-vfx.md, worked examples W3 (B), W4 (C), W5 (D).
Run: `py synthetic_rulers.py` from this folder; it prints and writes synthetic_rulers.json beside itself. First run
2026-10-13 (Vandor seat, Opus). Apache-2.0, Akashic Aurora.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

RNG = np.random.default_rng(7)
OUT = {}
HOUSE_IMAGES = [r"E:\AI-Setup\state\arsenal\shaders\cards\atmos-aurora\t2.00.png",
                r"E:\AI-Setup\design\vfx-snaps\avatar-geodesic-onblack.png"]


def srgb_decode(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb_encode(l):
    l = np.clip(l, 0.0, 1.0)
    return np.where(l <= 0.0031308, l * 12.92, 1.055 * l ** (1 / 2.4) - 0.055)


def q8(x):
    return np.round(np.clip(x, 0, 1) * 255.0).astype(np.uint8)


# ===================================================================================== B. Hald CLUT
def mystery_grade(rgb01):
    """Stand-in for 'a look we are permitted to run': white balance, exposure, filmic shoulder, split tone, saturation,
    S-curve. Pure per-pixel colour function."""
    lin = srgb_decode(rgb01) * np.array([1.06, 1.0, 0.90]) * 2 ** 0.3
    lin = np.tanh(lin * 1.1)                                          # shoulder
    c = srgb_encode(lin)
    luma = c @ np.array([0.2126, 0.7152, 0.0722])
    shadow = (1 - luma)[..., None] ** 2
    hi = luma[..., None] ** 2
    c = c + shadow * np.array([-0.02, 0.015, 0.04]) + hi * np.array([0.04, 0.01, -0.03])   # teal shadows, warm highs
    luma = c @ np.array([0.2126, 0.7152, 0.0722])
    c = luma[..., None] + 1.18 * (c - luma[..., None])                                       # saturation
    c = np.clip(c, 0, 1)
    return c + 0.12 * np.sin(2 * np.pi * c) / (2 * np.pi) * -1.0                            # gentle S-curve


def hald_identity(level):
    n = level * level
    side = level ** 3
    i = np.arange(side * side)
    r, g, b = i % n, (i // n) % n, i // (n * n)
    return (np.stack([r, g, b], -1).reshape(side, side, 3) / (n - 1)).astype(np.float64)


def lut_from_hald(img01, level):
    n = level * level
    return img01.reshape(-1, 3).reshape(n, n, n, 3)                   # [b, g, r] order


def apply_lut(lut, rgb01):
    n = lut.shape[0]
    p = np.clip(rgb01, 0, 1) * (n - 1)
    i0 = np.floor(p).astype(int)
    i0 = np.minimum(i0, n - 2)
    f = p - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    out = 0
    for db in (0, 1):
        for dg in (0, 1):
            for dr in (0, 1):
                w = (fr if dr else 1 - fr) * (fg if dg else 1 - fg) * (fb if db else 1 - fb)
                out = out + w * lut[b0 + db, g0 + dg, r0 + dr]
    return out


tests = [cv2.imread(p)[:, :, ::-1].astype(np.float64) / 255.0 for p in HOUSE_IMAGES]
ramp = hald_identity(8)                                               # plus every colour the 64^3 cube names
res = {}
for level in (4, 6, 8):
    hald = hald_identity(level)
    graded = q8(mystery_grade(hald)).astype(np.float64) / 255.0      # what we would read back from the tool's output
    lut = lut_from_hald(graded, level)
    errs = []
    for img in tests + [ramp]:
        truth = q8(mystery_grade(img)).astype(np.float64)
        got = q8(apply_lut(lut, img)).astype(np.float64)
        errs.append(np.abs(truth - got))
    e = np.concatenate([x.ravel() for x in errs])
    res[f"level {level} ({level*level}^3 = {level**6} colours, {level**3}x{level**3} image)"] = {
        "mean_abs_code": round(float(e.mean()), 3), "p99_code": float(np.percentile(e, 99)), "max_code": float(e.max())}
OUT["B_hald_capture_error_vs_truth"] = res


def vignette_pipeline(frame01):
    hgt, wid = frame01.shape[:2]
    yy, xx = np.mgrid[0:hgt, 0:wid]
    r2 = ((xx - wid / 2) / (wid / 2)) ** 2 + ((yy - hgt / 2) / (hgt / 2)) ** 2
    return mystery_grade(frame01) * (1 - 0.35 * r2 / 2)[..., None]


def blur_pipeline(frame01):
    return cv2.GaussianBlur(mystery_grade(frame01), (0, 0), 1.0)


def capture(pipeline, hald, at, block):
    canvas = np.full((1080, 1920, 3), 0.5)
    h = np.repeat(np.repeat(hald, block, 0), block, 1)
    y, x = at
    canvas[y:y + h.shape[0], x:x + h.shape[1]] = h
    out = q8(pipeline(canvas)).astype(np.float64) / 255.0
    o = out[y:y + h.shape[0], x:x + h.shape[1]]
    return o[block // 2::block, block // 2::block]                     # sample each block's centre


hald6 = hald_identity(6)                                              # 216x216, small enough to place anywhere
tests_spatial = {}
for name, pipe in (("pure grade", mystery_grade), ("grade + vignette", vignette_pipeline),
                   ("grade + 1 px blur", blur_pipeline)):
    centre = capture(pipe, hald6, (432, 852), 1)
    corner = capture(pipe, hald6, (0, 0), 1)
    big = capture(pipe, hald6, (108, 108), 4)
    small = capture(pipe, hald6, (108, 108), 1)
    tests_spatial[name] = {"position_test_max_code_diff(centre vs corner)": float(np.abs(centre - corner).max() * 255),
                           "neighbour_test_max_code_diff(1px vs 4px cells)": float(np.abs(big - small).max() * 255)}
OUT["B_when_a_LUT_cannot_capture_it"] = tests_spatial

# ===================================================================================== C. Bloom ruler
Hh, Ww = 540, 960
THRESH, STRENGTH, SIGMAS = 1.0, 0.04, [1.5 * 2 ** k for k in range(6)]
sources = [0.6, 1.5, 4.0, 16.0, 64.0]
xs = [120, 300, 480, 660, 840]
scene = np.full((Hh, Ww), 0.002)
yy, xx = np.mgrid[0:Hh, 0:Ww]
for I, x in zip(sources, xs):
    scene[(yy - 270) ** 2 + (xx - x) ** 2 <= 2.25] = I                 # tiny disc, radius 1.5 px
bright = np.maximum(scene - THRESH, 0.0)
bloom = sum(cv2.GaussianBlur(bright, (0, 0), s) for s in SIGMAS) / len(SIGMAS)
hdr = scene + STRENGTH * bloom
codes = q8(srgb_encode(hdr)).astype(np.float64)                       # an LDR game look: clamp, then sRGB


def radial(img, cx, cy, rmax=80):
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    prof = np.array([img[(r >= k - 0.5) & (r < k + 0.5)].mean() for k in range(rmax)])
    return prof


bloom_res = {"truth": {"threshold": THRESH, "chain_sigmas_px": SIGMAS, "strength": STRENGTH},
             "core_codes": [float(codes[270, x]) for x in xs]}
lin = srgb_decode(codes / 255.0)


def halos(img):
    out = []
    for I, x in zip(sources, xs):
        p = radial(img, x, 270)
        base = float(np.median(img[20:60, 20:60]))                    # empty sky, same frame
        out.append(float((p[6:60] - base).sum()))
    return out


halo_shot = halos(lin)
halo_float = halos(hdr)                                               # the HDR target a frame debugger would show
bloom_res["halo_energy_r6_60"] = {"screenshot (8-bit, decoded)": dict(zip(map(str, sources), [round(h, 5) for h in halo_shot])),
                                  "float render target (pre-clamp)": dict(zip(map(str, sources), [round(h, 5) for h in halo_float]))}
k, c0 = np.polyfit(sources[2:], halo_shot[2:], 1)
k2, c2 = np.polyfit(sources[1:], halo_float[1:], 1)
bloom_res["threshold_fit"] = {"from screenshot, sources 4..64 (the tempting fit)": round(float(-c0 / k), 3),
                              "from float target, sources 1.5..64": round(float(-c2 / k2), 3)}


def tail_ratio(p, r0=4):
    v = (p - p[-1]) / (p[r0] - p[-1])
    r50 = r0 + int(np.argmax(v[r0:] < 0.5))
    r10 = r0 + int(np.argmax(v[r0:] < 0.1))
    return r50, r10, round(r10 / r50, 2)


p_lin = radial(lin, 840, 270, 160)
p_code = radial(codes, 840, 270, 160)
g = cv2.GaussianBlur(np.where(scene >= 64, 1.0, 0.0), (0, 0), 6.0)
p_gauss = radial(g, 840, 270, 160)
bloom_res["tail_ratio_r10_over_r50"] = {"mip-chain bloom, display-linear": tail_ratio(p_lin),
                                        "same bloom, raw 8-bit codes (the trap)": tail_ratio(p_code),
                                        "single Gaussian reference": tail_ratio(p_gauss)}
OUT["C_bloom_ruler"] = bloom_res

# ===================================================================================== D. Particles, hit-stop, shake
W2, H2 = 320, 180
bg = cv2.GaussianBlur(RNG.random((H2 + 40, W2 + 40)), (0, 0), 2.0)
bg = (bg - bg.min()) / (bg.max() - bg.min()) * 0.35 + 0.05            # static world texture, 0.05..0.40


def particles_frame(pos, offset=(0.0, 0.0)):
    M = np.float32([[1, 0, offset[0] - 20], [0, 1, offset[1] - 20]])
    img = cv2.warpAffine(bg.astype(np.float32), M, (W2, H2), flags=cv2.INTER_LINEAR).astype(np.float64)
    acc = np.zeros((H2, W2))
    for x, y in pos:
        xi, yi = int(round(x)), int(round(y))
        if 3 <= xi < W2 - 3 and 3 <= yi < H2 - 3:
            acc[yi, xi] += 1.0
    acc = cv2.GaussianBlur(acc, (0, 0), 1.2) * (2 * np.pi * 1.2 ** 2) * 0.8   # additive soft dots, peak ~0.8
    return np.clip(img + acc, 0, 1)


def count(frame):
    m = (frame > 0.45).astype(np.uint8)
    n_cc = cv2.connectedComponents(m, connectivity=8)[0] - 1
    f32 = frame.astype(np.float32)
    dil = cv2.dilate(f32, np.ones((3, 3), np.uint8))
    peaks = int(((f32 >= dil) & (f32 > 0.45)).sum())
    return n_cc, peaks


cnt = {}
for N_true in (25, 100, 400):
    pos = RNG.random((N_true, 2)) * [W2, H2]
    n_cc, n_pk = count(particles_frame(pos))
    cnt[str(N_true)] = {"connected_components": n_cc, "local_maxima": n_pk}
OUT["D_particle_count_true_vs_counted"] = cnt

# a 60-frame clip: particles drift; frames 30-33 repeat frame 29 (hit-stop); frames 34-41 shake (decaying offsets)
pos = RNG.random((100, 2)) * [W2, H2]
vel = RNG.normal(0, 1.5, (100, 2))
frames, truth_shake = [], []
held = None
for f in range(60):
    off = (0.0, 0.0)
    if 34 <= f <= 41:
        a = 4.0 * 0.7 ** (f - 34)
        off = (a * (1 if f % 2 else -1), a * 0.5 * (1 if f % 3 else -1))
    truth_shake.append(off)
    if 30 <= f <= 33:
        frames.append(held.copy())
        continue
    pos = pos + vel
    fr = particles_frame(pos, off)
    frames.append(fr)
    held = fr


GRAIN = [RNG.normal(0, 2.0 / 255, (H2, W2)) for _ in range(60)]        # film grain that keeps animating in a hit-stop


def jpeg(fr, q=50):
    ok, buf = cv2.imencode(".jpg", q8(fr), [cv2.IMWRITE_JPEG_QUALITY, q])
    return cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE).astype(np.float64) / 255.0


hit = {}
for name, seq in (("lossless, no grain", [q8(f).astype(np.float64) / 255 for f in frames]),
                  ("animated grain + jpeg q50", [jpeg(np.clip(f + GRAIN[i], 0, 1)) for i, f in enumerate(frames)])):
    mean_diff = [float(np.abs(seq[i] - seq[i - 1]).mean() * 255) for i in range(1, len(seq))]
    # a structure-aware measure: blur away the grain, then count pixels that changed by more than 8 codes
    blurred = [cv2.GaussianBlur(x, (0, 0), 1.5) for x in seq]
    changed = [float((np.abs(blurred[i] - blurred[i - 1]) * 255 > 8).mean() * 100) for i in range(1, len(seq))]
    hit[name] = {"frames_with_zero_mean_diff": [i for i, d in enumerate(mean_diff, 1) if d == 0.0],
                 "mean_diff_codes_frozen_30_33": [round(mean_diff[i - 1], 2) for i in range(30, 34)],
                 "mean_diff_codes_median_elsewhere": round(float(np.median([d for i, d in enumerate(mean_diff, 1) if not 30 <= i <= 33])), 2),
                 "pct_pixels_changed_gt8_frozen_30_33": [round(changed[i - 1], 2) for i in range(30, 34)],
                 "pct_pixels_changed_gt8_median_elsewhere": round(float(np.median([d for i, d in enumerate(changed, 1) if not 30 <= i <= 33])), 2)}
OUT["D_hit_stop"] = hit

# shake: global translation between each frame and a reference frame, from the static world texture
def world_only(fr):
    """Remove the small moving foreground (particles) with a grey-level opening before estimating the camera."""
    return cv2.morphologyEx(fr.astype(np.float32), cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))


win = cv2.createHanningWindow((W2, H2), cv2.CV_32F)
naive, cleaned = [], []
ref_raw, ref_clean = frames[28].astype(np.float32), world_only(frames[28])
for f in range(34, 44):
    (dx, dy), _ = cv2.phaseCorrelate(ref_raw, frames[f].astype(np.float32), win)
    naive.append((round(dx, 2), round(dy, 2)))
    (dx, dy), _ = cv2.phaseCorrelate(ref_clean, world_only(frames[f]), win)
    cleaned.append((round(dx, 2), round(dy, 2)))
tru = [truth_shake[f] for f in range(34, 44)]
rms = lambda e: round(float(np.sqrt(np.mean([(a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 for a, b in zip(e, tru)]))), 2)
OUT["D_screen_shake"] = {"true_offsets_px(frames 34-43)": [tuple(round(v, 2) for v in t) for t in tru],
                         "phase_correlation_raw_frames": naive, "rms_error_raw_px": rms(naive),
                         "phase_correlation_after_removing_particles": cleaned, "rms_error_cleaned_px": rms(cleaned)}

print(json.dumps(OUT, indent=1))
with open(Path(__file__).with_suffix(".json"), "w", newline="\n") as fh:
    json.dump(OUT, fh, indent=1)
