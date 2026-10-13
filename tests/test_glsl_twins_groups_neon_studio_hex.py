"""Pins for three of the six P0 group recipes of the house GLSL library (shader school batch B, 2026-10-13), and for
the parity compositor one of them reaches for.

WHAT THESE ARE. A group is a recipe module: a function that wires library parts into something that works, with the
knobs a person turns declared in its header (each knob names its uniform, so the Shader Lab's Inspector generates the
control through arsenal/web/lib/params-ui.js and the Workbench binds it into the card).

    groups/neon-line.glsl      a thin line of light: a hot core of constant pixel width, a halo whose falloff is a
                               choice, a defocus that spreads light without adding any, crossings by max or add
    groups/hex-neon.glsl       a hexagonal tiling whose per-cell id drives size, spin, colour and the wave's arrival,
                               outlined in antialiased neon, each cell seen by its six neighbours so nothing clips
    groups/studio-object.glsl  a raymarched hero object under the product-shot rig: the host's mapScene and
                               materialAt hooks, a soft shadow, occlusion, a floor pool, silhouettes from the cone
    composite/parity.glsl      cmpXor, the even-odd combination behind hex-neon's graphic (XOR) mood

WHY THESE PINS. A group is where a surface meets the library, so a recipe whose line thickens on a big canvas, whose
halo is cut off at a cell border, or whose floor shows a seam at the horizon would show up on every piano floor and
hero render at once. Each recipe has a CPU twin built from the twins of the parts it calls (arsenal/shaders/twins/
neon_line.py, hex_neon.py, studio_object.py, parity.py); the twins are held to independent references (the ink of a
line integrated across it, a Monte Carlo XOR, a brute-force polyline distance, the harmonic table's intervals, the
studio's own environment), and the slow test at the bottom renders a parity card on SwiftShader and holds the GLSL to
the twins pixel by pixel. The headers are held to the atlas (arsenal/shaders/atlas.json): its exemplars, required
parts, hooks and debug views, and every knob is checked through the param schema's own descriptor check.

Like a calibration bench: the twin is the golden model, the integral and the brute force are the reference standard,
and the SwiftShader render is the device under test.

Apache-2.0, Akashic Aurora. Written fresh for the house; no corpus code.
"""
from __future__ import annotations

import importlib
import json
import math
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from arsenal import params as P
from arsenal.shaders import cards as K
from arsenal.shaders import modules as M

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "arsenal" / "web" / "glsl"
ATLAS = REPO / "arsenal" / "shaders" / "atlas.json"
F32 = np.float32
RNG = np.random.default_rng(20261013)

# file (under arsenal/web/glsl/) -> module name, for the three recipes and the one helper this slice builds
RECIPES = {
    "groups/neon-line.glsl": "neon-line",
    "groups/hex-neon.glsl": "hex-neon",
    "groups/studio-object.glsl": "studio-object",
}
GROUP_OF = {"neon-line": "neon-line", "hex-neon": "hex-neon", "studio-object": "studio-object"}
HELPERS = {"composite/parity.glsl": "composite-parity"}


def twin(area: str):
    """The twin module, imported inside each test so a missing twin fails that test by name (not the whole file)."""
    return importlib.import_module(f"arsenal.shaders.twins.{area}")


def close(a, b, tol=1e-6):
    return np.allclose(np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64), rtol=tol, atol=tol)


# ================================================================================================ composite/parity.glsl
def test_xor_is_the_truth_table_on_binary_coverage():
    x = twin("parity")
    for a in (0.0, 1.0):
        for b in (0.0, 1.0):
            assert x.cmpXor(a, b) == float(int(a) ^ int(b))


def test_xor_is_the_signed_product_so_any_grouping_and_order_agree():
    x = twin("parity")
    a, b, c = RNG.uniform(0, 1, (3, 2000))
    assert close(1.0 - 2.0 * x.cmpXor(a, b), (1.0 - 2.0 * a) * (1.0 - 2.0 * b), 1e-12)
    assert close(x.cmpXor(x.cmpXor(a, b), c), x.cmpXor(a, x.cmpXor(b, c)), 1e-12)
    assert close(x.cmpXor(a, b), x.cmpXor(b, a), 1e-12)
    assert close(x.cmpXor(a, 0.0), a) and close(x.cmpXor(a, 1.0), 1.0 - a)


def test_xor_of_two_coverages_is_the_chance_exactly_one_is_set():
    """A coverage is the fraction of a pixel a shape covers; for shapes placed independently, the fraction of the pixel
    covered by exactly one of them is what cmpXor returns, so antialiased edges XOR without a jaggy seam."""
    x = twin("parity")
    samples = RNG.uniform(0, 1, (2, 400000))
    for pa, pb in ((0.3, 0.6), (0.5, 0.5), (0.9, 0.15)):
        one = np.mean((samples[0] < pa) ^ (samples[1] < pb))
        assert abs(one - x.cmpXor(pa, pb)) < 0.004


def test_xor_holds_its_inputs_to_zero_one():
    x = twin("parity")
    assert x.cmpXor(-0.5, 0.25) == x.cmpXor(0.0, 0.25)
    assert x.cmpXor(1.7, 0.25) == x.cmpXor(1.0, 0.25)
    v = x.cmpXor(RNG.uniform(-3, 3, 1000), RNG.uniform(-3, 3, 1000))
    assert v.min() >= 0.0 and v.max() <= 1.0


# ==================================================================================================== groups/neon-line
NEON_DEFAULTS = dict(widthPx=1.6, haloPx=14.0, profile=0, coreHeat=1.6, combine=0, defocus=0.35, view=0)


def _neon(t, d, px, tint=(0.2, 0.55, 1.0), energy=1.0, depth=0.0, acc=None, **over):
    kw = dict(NEON_DEFAULTS)
    kw.update(over)
    d = np.asarray(d, dtype=np.float64)
    acc = np.zeros(d.shape + (3,)) if acc is None else acc
    return t.neonLine(acc, d, px, np.array(tint), energy, depth, kw["widthPx"], kw["haloPx"], kw["profile"],
                      kw["coreHeat"], kw["combine"], kw["defocus"], kw["view"])


def test_profile_is_one_at_the_line_and_falls_away_monotonically():
    n = twin("neon_line")
    d = np.linspace(0, 80, 4001)
    for profile in (0, 1, 2):
        f = n.neonProfile(d, 14.0, profile)
        assert close(f[0], 1.0, 1e-6), profile
        assert np.all(np.diff(f) <= 1e-12), profile
        assert f[-1] < 0.02, profile


def test_profiles_are_the_atlas_line_shapes_measured_in_halo_widths():
    """Two Gaussians: the house light-line profile (24, 1, 3, 0.18), normalised to 1. Lorentzian: k / (k + x^2) with
    half height at a quarter of the halo. Inverse power: (0.35 / (x + 0.35))^2. Wire only: no halo at all."""
    n = twin("neon_line")
    halo = 12.0
    d = RNG.uniform(0, 40, 500)
    x = d / halo
    assert close(n.neonProfile(d, halo, 0), (np.exp(-24 * x * x) + 0.18 * np.exp(-3 * x * x)) / 1.18, 1e-6)
    assert close(n.neonProfile(d, halo, 1), (1 / 16) / (1 / 16 + x * x), 1e-6)
    assert close(n.neonProfile(0.25 * halo, halo, 1), 0.5, 1e-6)
    assert close(n.neonProfile(d, halo, 2), (0.35 / (x + 0.35)) ** 2, 1e-5)
    assert np.all(n.neonProfile(d, halo, 3) == 0.0)
    assert np.all(n.neonProfile(d, 0.0, 0) == 0.0)                   # no halo width: no halo, never a division by 0


def test_path_step_keeps_the_nearest_segment_and_its_curve_parameter():
    n = twin("neon_line")
    xs = np.linspace(-1, 1, 9)
    ys = 0.3 * np.sin(2.5 * xs)
    pts = RNG.uniform(-1.2, 1.2, (300, 2))
    for p in pts:
        best = np.array([1e9, 0.0])
        for k in range(8):
            best = n.neonPathStep(p, (xs[k], ys[k]), (xs[k + 1], ys[k + 1]), (k / 8, (k + 1) / 8), best)
        # brute force: dense points along the polyline, each with its parameter
        dense_s = np.linspace(0, 1, 8 * 400 + 1)
        seg = np.minimum((dense_s * 8).astype(int), 7)
        f = dense_s * 8 - seg
        dense = np.stack([xs[seg] + f * (xs[seg + 1] - xs[seg]), ys[seg] + f * (ys[seg + 1] - ys[seg])], -1)
        dist = np.hypot(*(dense - p).T)
        assert abs(best[0] - dist.min()) < 2e-3
        assert abs(best[1] - dense_s[np.argmin(dist)]) < 0.02 or abs(dist.min() - np.sort(dist)[50]) < 1e-3


def _ink(n, px, **over):
    """The peak channel of a line's light integrated across it, in pixels: what an eye sees as how much line there is."""
    d = np.linspace(-1500 * px, 1500 * px, 60001)                      # wide: the Lorentzian's tails are long
    light = _neon(n, d, px, tint=(0.2, 0.55, 1.0), **over)
    return np.trapezoid(light[:, 2], d) / px


def test_the_twin_whitens_exactly_as_the_hot_core_part_does():
    n, lt = twin("neon_line"), twin("light")
    tint = np.array([0.2, 0.55, 1.0])
    for energy in (0.1, 0.5, 1.0, 2.5):
        for heat in (0.3, 1.6, 4.0):
            got = _neon(n, [0.0], 0.01, tint=tint, energy=energy, coreHeat=heat, haloPx=0.0)[0]
            h = heat * energy
            assert close(got, energy * lt.glowHotCore(tint, h) / h, 1e-12)


def test_the_core_is_its_width_in_pixels_at_any_scale():
    """Constant pixel width (atlas craft secret 21): the core's ink is widthPx pixels whatever the units of d are."""
    n = twin("neon_line")
    for px in (0.002, 0.01, 0.5):
        for width in (1.0, 2.5, 6.0):
            ink = _ink(n, px, widthPx=width, haloPx=0.0, defocus=0.0)
            assert abs(ink - width) < 0.01 * width, (px, width, ink)
    thin = _ink(n, 0.01, widthPx=0.5, haloPx=0.0, defocus=0.0)
    assert abs(thin - 0.5) < 0.01                                        # a half-pixel line dims, never breaks
    core = _neon(n, np.linspace(-1, 1, 41) * 0.01, 0.01, widthPx=0.5, haloPx=0.0, defocus=0.0)
    assert core[:, 2].max() < 0.55                                      # ... drawn one pixel wide at half strength


def test_defocus_spreads_the_light_and_never_adds_any():
    n = twin("neon_line")
    for profile in (0, 1, 2, 3):
        sharp = _ink(n, 0.01, profile=profile, defocus=1.0)                  # depth 0: no blur at all
        soft = _ink(n, 0.01, profile=profile, defocus=1.0, depth=1.0)
        assert abs(soft - sharp) < 0.02 * sharp, (profile, sharp, soft)
        peak_sharp = _neon(n, [0.0], 0.01, defocus=1.0, profile=profile)[0, 2]
        peak_soft = _neon(n, [0.0], 0.01, defocus=1.0, depth=1.0, profile=profile)[0, 2]
        assert peak_soft < 0.5 * peak_sharp                                  # four times wider, a quarter as high


def test_the_core_whitens_with_heat_while_the_halo_keeps_its_hue():
    n = twin("neon_line")
    tint = np.array([0.2, 0.55, 1.0])
    cool = _neon(n, [0.0], 0.01, tint=tint, coreHeat=0.0, haloPx=0.0)[0]
    hot = _neon(n, [0.0], 0.01, tint=tint, coreHeat=4.0, haloPx=0.0)[0]
    assert close(cool / cool[2], tint, 1e-9)                             # no heat: the core is the tint itself
    assert close(hot[2], cool[2], 1e-9)                                  # the peak channel is the energy, always
    assert hot[0] / hot[2] > 0.9 and hot[1] / hot[2] > 0.9               # heat carries the others up toward white
    halo = _neon(n, [0.2], 0.01, tint=tint, coreHeat=4.0)[0]             # 20 pixels out: halo only
    assert halo[2] > 0 and close(halo / halo[2], tint, 1e-9)
    softer = _neon(n, [0.0], 0.01, tint=tint, energy=0.25, haloPx=0.0)[0]
    louder = _neon(n, [0.0], 0.01, tint=tint, energy=1.0, haloPx=0.0)[0]
    assert softer[0] / softer[2] < louder[0] / louder[2]                 # a soft note keeps its colour, a hard one whitens


def test_max_keeps_crossings_crisp_and_add_sums_light():
    n = twin("neon_line")
    d = np.array([0.0, 0.03, 0.2])
    one = _neon(n, d, 0.01, combine=0)
    crossed = _neon(n, d, 0.01, combine=0, acc=one)
    assert close(crossed, one, 1e-12)                                    # max: a crossing is as bright as one line
    summed = _neon(n, d, 0.01, combine=1, acc=one)
    assert close(summed, 2 * one, 1e-12)


def test_debug_views_show_the_core_alone_and_the_halo_alone():
    n = twin("neon_line")
    d = np.linspace(-0.3, 0.3, 601)
    full = _neon(n, d, 0.01)
    core = _neon(n, d, 0.01, view=1)
    halo = _neon(n, d, 0.01, view=2)
    assert close(core[:, 0], core[:, 1]) and core.max() <= 1.0 + 1e-9 and core[300, 0] > 0.99   # white coverage
    assert np.all(halo <= full + 1e-12) and halo[300, 2] > 0 and halo[:, 2].max() < full[:, 2].max()


def test_no_light_from_no_energy_and_nothing_non_finite_at_the_edges():
    n = twin("neon_line")
    assert np.all(_neon(n, [0.0, 0.1], 0.01, energy=0.0) == 0.0)
    for px in (1e-9, 0.0, 1.0):
        for over in (dict(haloPx=0.0, widthPx=0.0), dict(defocus=1.0), dict(profile=2, haloPx=64.0)):
            v = _neon(n, [0.0, 1e-7, 3.0], px, depth=1.0, **over)
            assert np.all(np.isfinite(v)) and v.min() >= 0.0


# ===================================================================================================== groups/hex-neon
HEX_DEFAULTS = dict(cellSize=0.22, lineWidth=1.5, haloPx=7.0, waveSpeed=0.6, sizeAmp=0.55, spin=0.35, palette=0,
                    accent=0.1, combine=0, view=0)


def _hex(h, p, px, t, origin=(0.0, 0.0), **over):
    kw = dict(HEX_DEFAULTS)
    kw.update(over)
    return h.hexNeon(np.asarray(p, dtype=np.float64), px, t, np.asarray(origin, dtype=np.float64), kw["cellSize"],
                     kw["lineWidth"], kw["haloPx"], kw["waveSpeed"], kw["sizeAmp"], kw["spin"], kw["palette"],
                     kw["accent"], kw["combine"], kw["view"])


def test_the_six_steps_reach_the_six_neighbouring_centres():
    h, lat = twin("hex_neon"), twin("draw2")
    steps = np.array([h.hexNeonStep(k) for k in range(6)])
    assert close(np.hypot(*steps.T), 1.0, 1e-6)
    axial = lat.latHexAxial(steps.astype(F32))
    assert {tuple(a) for a in axial.tolist()} == {(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)}
    assert all(lat.latHexSteps([0.0, 0.0], a) == 1 for a in axial)


def test_a_cell_is_posed_by_its_centre_alone_and_the_wave_arrives_cell_by_cell():
    """The pose reads only the cell's centre (so every point of a cell shares one size and one turn): its swell is the
    swell curve at the cell's own clock, t minus the centre's distance over the speed, detuned by the cell's die. A
    ring of whole cells, never a smooth front."""
    h, lat, hs = twin("hex_neon"), twin("draw2"), twin("hash")
    origin = np.array([0.5, -0.25])
    for centre in ([0.0, 0.0], [2.0, 0.0], [1.5, 2.598076211353316], [-3.0, 1.7320508075688772]):
        c = np.array(centre)
        dist = math.hypot(*(c - origin))
        dice = float(hs.hash21(lat.latHexAxial(c.astype(F32))))
        pose = h.hexNeonPose(c, 9.0, origin, 0.6, 0.55, 0.35)
        assert close(pose[2], h.hexNeonSwell(9.0 - dist / 0.6, dice), 1e-6)
    a = h.hexNeonPose(np.array([1.0, 0.0]), 5.0, np.zeros(2), 0.6, 0.55, 0.35)
    b = h.hexNeonPose(np.array([1.0, 0.0]), 5.0 + 1.0 / 0.6, np.array([-1.0, 0.0]), 0.6, 0.55, 0.35)
    assert close(a, b, 1e-5)                                             # twice as far, as much later: the same pose
    rest = h.hexNeonPose(np.array([2.0, 0.0]), 3.0, np.zeros(2), 0.6, 0.0, 0.35)
    assert close(rest[:2], [0.36, 0.0], 1e-6)                            # no swing: the rest size, no turn


def test_size_swing_stays_inside_its_band_and_the_turn_follows_the_size():
    h = twin("hex_neon")
    ts = np.linspace(0, 120, 3001)
    for amp in (0.3, 0.55, 1.0):
        poses = np.array([h.hexNeonPose(np.array([1.0, 0.0]), t, np.zeros(2), 0.6, amp, 0.35) for t in ts])
        r, angle, swell = poses[:, 0], poses[:, 1], poses[:, 2]
        assert r.min() >= 0.36 * (1 - 0.65 * amp) - 1e-9 and r.max() <= 0.36 * (1 + 0.65 * amp) + 1e-9
        assert np.ptp(r) > 0.36 * 0.65 * amp                             # it really breathes
        assert close(angle, 2 * math.pi * 0.35 * (r / 0.36 - 1.0), 1e-9)  # spin coupled to size (Hexagone's iris)
        assert swell.min() >= 0.0 and swell.max() <= 1.0


def test_lines_keep_their_pixel_width_whatever_the_cell_size():
    """Walk out from a cell's centre along +x through its outline: the line's ink is lineWidth pixels for any cell size
    and canvas, because every width is measured in pixels of the unwarped coordinate."""
    h = twin("hex_neon")
    for cell, px in ((0.22, 2 / 270), (0.6, 2 / 1080), (0.08, 2 / 540)):
        r = 0.36 * cell                                                  # sizeAmp 0: the outline sits at the rest size
        reach = min(25 * px, 0.14 * cell)                                # half way to the neighbour's outline
        xs = np.linspace(r - reach, r + reach, 6001)
        pts = np.stack([xs, np.zeros_like(xs)], -1)
        bare = _hex(h, pts, px, 1.0, cellSize=cell, sizeAmp=0.0, haloPx=0.0, accent=0.0)
        peak = bare.max(axis=0).argmax()
        ink = np.trapezoid(bare[:, peak], xs) / px / bare[:, peak].max()
        assert abs(ink - 1.5) < 0.15, (cell, px, ink)


def test_no_seams_where_cells_meet_because_each_cell_is_seen_by_its_neighbours():
    """A halo or an oversized hexagon reaches into the next cell; with the six neighbours evaluated as well, the picture
    is continuous across every cell border (a halo clipped at a border would jump there)."""
    h = twin("hex_neon")
    px = 2 / 270
    for over in (dict(), dict(sizeAmp=1.0, haloPx=14.0), dict(combine=1, spin=1.0)):
        xs = np.linspace(-0.9, 0.9, 30001)                               # sub-pixel steps, crossing many borders
        pts = np.stack([xs, 0.11 + 0.37 * xs], -1)
        v = _hex(h, pts, px, 2.3, **over).max(axis=-1)
        step = np.abs(np.diff(v))
        # the steepest honest change is a one-pixel antialiased edge: about the peak per pixel, here per 1/16 pixel
        assert step.max() < 0.12 * max(v.max(), 1e-6), (over, step.max(), v.max())


def test_pitch_palette_lays_the_harmonic_table_on_the_lattice():
    """palette 1: one step right is a fifth (+7 semitones), one step up and right a major third (+4), and every cell's
    colour is the house note colour of its pitch class (palPitchFifths), so C is the same colour on every surface."""
    h, pal = twin("hex_neon"), twin("palette")
    for q, r in ((0, 0), (1, 0), (0, 1), (-1, 1), (3, -2)):
        pc = (7 * q + 4 * r) % 12
        got = h.hexNeonColour(np.array([q, r], dtype=float), 0.5, 1, 0.1)
        assert close(got, pal.palPitchFifths(float(pc), 4.0, pal.palPitchPiano()), 1e-9), (q, r)


def test_cosine_palette_is_analogous_cool_with_a_coral_accent():
    """The house rule: analogous, never a rainbow; two cool families and one warm accent, and coral is the accent."""
    h, col = twin("hex_neon"), twin("colour")
    dice = RNG.uniform(0, 1, 4000)
    rgb = np.array([h.hexNeonColour(np.zeros(2), u, 0, 0.1) for u in dice])
    hue = col.oklchFromOklab(col.oklabFromLinear(rgb))[:, 2] % 1.0
    warm = (hue > 0.0) & (hue < 0.15)                                    # coral sits near 0.1 turns in OKLCH
    assert abs(np.mean(warm) - 0.1) < 0.02                               # one cell in ten, as asked
    cool = hue[~warm]
    assert np.all((cool > 0.5) & (cool < 0.88)) and np.ptp(cool) < 0.35  # cyan through blue to violet, nothing else
    none = np.array([h.hexNeonColour(np.zeros(2), u, 0, 0.0) for u in dice[:500]])
    hue0 = col.oklchFromOklab(col.oklabFromLinear(none))[:, 2] % 1.0
    assert not np.any((hue0 > 0.0) & (hue0 < 0.15))                      # no accent asked, no coral


def test_combine_add_max_and_xor():
    """Add is light (overlaps brighten), max keeps crossings at one line's brightness, and XOR is the graphic mood:
    filled hexagons whose overlaps cancel (the even-odd rule of cmpXor)."""
    h, lat = twin("hex_neon"), twin("draw2")
    px, cell = 2 / 270, 0.22
    pts = np.random.default_rng(4).uniform(-0.8, 0.8, (8000, 2))      # its own dice: the result never hangs on order
    add = _hex(h, pts, px, 1.3, sizeAmp=1.0, combine=0)
    mx = _hex(h, pts, px, 1.3, sizeAmp=1.0, combine=1)
    assert np.all(mx <= add + 1e-9) and np.mean(add > mx + 1e-6) > 0.01  # overlaps: add is brighter, max never is
    xor = _hex(h, pts, px, 4.0, sizeAmp=1.0, combine=2)
    assert np.all(np.isfinite(xor)) and xor.min() >= 0.0
    home = lat.latHex((pts / cell).astype(F32)).astype(np.float64)
    fills = []
    for k in range(7):
        step = np.zeros(2) if k == 0 else np.asarray(h.hexNeonStep(k - 1))
        _, fill = h.hexNeonCell(home[:, :2] - step, home[:, 2:] + step, px / cell, 4.0, np.zeros(2), 1.5, 7.0, 0.6,
                                1.0, 0.35, 0, 0.1, 2)
        fills.append(fill)
    fills = np.stack(fills, -1)
    full, touched = (fills >= 1.0).sum(axis=1), (fills > 0.0).sum(axis=1)
    two = (full == 2) & (touched == 2)
    one = (full == 1) & (touched == 1)
    assert two.mean() > 0.005 and one.mean() > 0.2
    assert np.all(xor[two].max(axis=1) < 1e-6)                          # two fills overlap: the ink cancels
    assert np.all(xor[one].max(axis=1) > 1e-3)                          # one fill alone: it shows


def test_cells_view_numbers_the_cells():
    h = twin("hex_neon")
    px = 2 / 270
    pts = RNG.uniform(-0.8, 0.8, (2000, 2))
    v = _hex(h, pts, px, 0.0, view=1)
    assert np.all(np.isfinite(v)) and v.min() >= 0.0 and v.max() <= 1.0 + 1e-9
    assert len({tuple(np.round(c, 3)) for c in v}) > 50                  # cells differ, and so does the place in them


# ================================================================================================ groups/studio-object
STUDIO_DEFAULTS = dict(lens=3.2, keyTurn=0.85, keyElevation=48.0, boxSize=0.42, backdrop=0.3, fresnelFloor=0.04, metal=0.0,
                       roughness=0.25, shadowAngle=6.0, aoReach=0.35, poolRadius=1.1, floorDrop=0.62, bound=0.75,
                       steps=96.0, omega=1.0, view=0)
EYE = np.array([0.0, 0.55, 4.2])
TARGET = np.zeros(3)


def ball(p):
    return float(np.linalg.norm(np.asarray(p, dtype=np.float64)) - 0.45)


def grey(p, n, ident):
    return np.array([0.18, 0.18, 0.18]) if ident > 0.5 else np.array([0.5, 0.08, 0.04])


def _studio(s, pixel, res=(160, 90), eye=EYE, scene=ball, material=grey, **over):
    kw = dict(STUDIO_DEFAULTS)
    kw.update(over)
    return s.studioObject(eye, TARGET, np.asarray(pixel, dtype=np.float64), np.asarray(res, dtype=np.float64),
                          kw["lens"], kw["keyTurn"], kw["keyElevation"], kw["boxSize"], kw["backdrop"], kw["fresnelFloor"],
                          kw["metal"],
                          kw["roughness"], kw["shadowAngle"], kw["aoReach"], kw["poolRadius"], kw["floorDrop"],
                          kw["bound"], kw["steps"], kw["omega"], kw["view"], scene, material)


def _pixel_of(s, point, res=(160, 90), eye=EYE, lens=3.2):
    """The pixel a world point projects to through the recipe's camera (camLookAt at the target, focal = lens)."""
    ray = twin("ray")
    basis = ray.camLookAt(eye, TARGET, 0.0).astype(np.float64)
    local = basis.T @ (np.asarray(point) - eye)
    uv = -lens * local[:2] / local[2]
    return uv * res[1] / 2 + np.array(res) / 2


def test_the_rig_is_the_neutral_studio_at_the_default_knobs():
    s, light = twin("studio_object"), twin("light")
    rig = s.studioObjectRig(0.85, 48.0, 0.42, 1.1, 0.62)
    ref = light.studio_default()
    assert float(np.dot(rig.keyDir, ref.keyDir)) > 0.999                  # the key: high on the upper left, in front
    assert float(np.dot(rig.fillDir, ref.fillDir)) > 0.99                 # the fill: behind, on the right
    assert close(rig.keyCol, ref.keyCol) and close(rig.fillCol, ref.fillCol) and close(rig.floorCol, ref.floorCol)
    assert rig.floorDrop == 0.62 and rig.poolRadius == 1.1 and close(rig.boxSize, [0.42, 0.42 * 0.66])


def test_a_miss_shows_the_bare_studio_and_a_hit_is_lit_by_the_rig():
    s, light = twin("studio_object"), twin("light")
    sky = _studio(s, (80.5, 88.5))                                       # top centre: above the horizon, past the ball
    rig = s.studioObjectRig(0.85, 48.0, 0.42, 1.1, 0.62)
    bare = s.studioObjectBare(rig)
    ray = twin("ray")
    rd = ray.camRay(np.array([80.5, 88.5]), np.array([160.0, 90.0]), ray.camLookAt(EYE, TARGET, 0.0), 3.2)
    assert close(sky, 0.3 * light.litStudioEnv(rd, 0.0, bare), 1e-5)               # the backdrop knob's black flag
    centre = _studio(s, _pixel_of(s, [0.0, 0.0, 0.45]))
    assert centre.sum() > sky.sum() and np.all(np.isfinite(centre))


def test_a_black_dielectric_with_no_fresnel_floor_is_black_and_a_mirror_shows_its_studio():
    s, light = twin("studio_object"), twin("light")
    at = _pixel_of(s, [-0.15, 0.2, 0.45])
    black = _studio(s, at, material=lambda p, n, i: np.zeros(3) if i < 0.5 else np.full(3, 0.18), fresnelFloor=0.0)
    assert np.all(black < 1e-6)
    rig = s.studioObjectRig(0.85, 48.0, 0.42, 1.1, 0.62)
    n = np.array([0.3, 0.5, 0.8]) / np.linalg.norm([0.3, 0.5, 0.8])
    v = np.array([0.1, 0.2, 1.0]) / np.linalg.norm([0.1, 0.2, 1.0])
    mirror = s.studioObjectSurface(np.zeros(3), n, v, rig, 0.04, 1.0, 0.0, 0.5, 0.8, lambda p, nn, i: np.ones(3))
    want = light.litStudioEnv(2 * np.dot(n, v) * n - v, 0.0, rig) * 0.8   # a white metal: the studio, times the AO
    assert close(mirror, want, 1e-6)


def _no_object(p):
    return 10.0


def test_the_floor_carries_a_shadow_and_a_contact_darkening_under_the_object():
    """Compare the floor with and without the ball: where the key's ray to the ball's centre lands, the floor is in
    the umbra; right beside the ball's foot the occlusion darkens it; far away the ball changes nothing."""
    s = twin("studio_object")
    rig = s.studioObjectRig(0.85, 48.0, 0.42, 1.1, 0.62)
    spot = -rig.keyDir / rig.keyDir[1] * 0.62                            # the ball's centre projected along the key
    for where, most in ((spot, 0.5), ([0.0, -0.62, 0.0], 0.5)):
        at = _pixel_of(s, where)
        with_ball, without = _studio(s, at), _studio(s, at, scene=_no_object)
        assert with_ball.sum() < most * without.sum(), (where, with_ball, without)
    far = _pixel_of(s, [-1.6, -0.62, 1.2])
    assert close(_studio(s, far), _studio(s, far, scene=_no_object), 1e-9)


def test_the_floor_dissolves_into_the_horizon_with_no_edge():
    """Near the horizon the floor and the backdrop above it agree, so there is no ground line (Cube Lines' trick)."""
    s = twin("studio_object")
    res = (160, 90)
    eye = np.array([0.0, 0.3, 4.2])
    rows = [_studio(s, (20.5, y + 0.5), res=res, eye=eye, lens=1.2) for y in range(0, 90)]
    lum = np.array([r @ [0.2126, 0.7152, 0.0722] for r in rows])
    assert np.max(np.abs(np.diff(lum))) < 0.02


def test_silhouettes_are_covered_by_the_cone_not_cut():
    s = twin("studio_object")
    res = (160, 90)
    edge = _pixel_of(s, [0.45, 0.0, 0.0], res)
    row = [_studio(s, (edge[0] + dx, edge[1]), res) for dx in np.linspace(-3, 3, 25)]
    lum = np.array([r @ [0.2126, 0.7152, 0.0722] for r in row])
    assert np.max(np.abs(np.diff(lum))) < 0.6 * np.ptp(lum)              # at least two steps across the edge


def test_debug_views_are_finite_and_the_step_heat_rises_toward_the_silhouette():
    s = twin("studio_object")
    for view in range(1, 6):
        v = _studio(s, (80.5, 45.5), view=view)
        assert np.all(np.isfinite(v)) and v.min() >= 0.0, view
    centre = _studio(s, _pixel_of(s, [0.0, 0.0, 0.45]), view=1)
    rim = _studio(s, _pixel_of(s, [0.445, 0.0, 0.05]), view=1)
    assert rim.sum() > centre.sum()


# ======================================================================================================= the modules
def _atlas():
    return json.loads(ATLAS.read_text(encoding="utf-8"))


def _group(name):
    return next(g for g in _atlas()["groups"] if g["name"] == name)


@pytest.fixture(scope="module")
def library():
    return M.load_library(strict=False)


def _module(lib, file, table=None):
    table = table or {**RECIPES, **HELPERS}
    name = table[file]
    assert name in lib.modules, f"no module named {name} (expected in arsenal/web/glsl/{file}); " \
                                f"quarantined: {[p for p in lib.problems if file in p['path'].replace(chr(92), '/')]}"
    m = lib.modules[name]
    assert Path(m.path).resolve() == (LIB / file).resolve(), f"{name} lives in {m.path}, not {file}"
    return m


def _entry_args(m):
    """[(type, name), ...] of the header's entry, which must be a function the module defines with that signature."""
    entry = m.header["entry"]
    mm = re.fullmatch(r"\s*(\w+)\s+(\w+)\s*\(([^()]*)\)\s*", entry)
    assert mm, entry
    assert mm.group(2) in m.functions
    args = []
    for raw in mm.group(3).split(","):
        words = raw.split()
        args.append((words[-2], words[-1]))
    defined = [d for d in M.DEFINITION_RE.finditer(M.strip_comments(m.body)) if d.group(2) == mm.group(2)]
    assert len(defined) == 1
    got = [tuple(w.split()[-2:]) for w in defined[0].group(3).split(",")]
    assert got == args, f"the entry in the header and the code disagree: {args} != {got}"
    return args


@pytest.mark.parametrize("file", sorted(RECIPES))
def test_recipe_headers_carry_every_library_field(library, file):
    m = _module(library, file)
    h = m.header
    g = _group(GROUP_OF[m.name])
    cats = {c["id"]: c for c in _atlas()["categories"]}
    assert h["name"] == RECIPES[file] and h["kind"] == "recipe"
    assert h["cat"] in cats and h["family"] == cats[h["cat"]]["family"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", h["version"]) and 50 <= h["order"] <= 90
    assert h["license"] == "Apache-2.0"
    assert isinstance(h["credits"], list) and h["credits"] and all("http" in c for c in h["credits"])
    assert h["cost"]["class"] == g["cost"] and h["cost"]["tex"] == 0 and h["cost"].get("loop")
    for key in ("contract", "note"):
        assert isinstance(h[key], str) and len(h[key]) > 120, key
    assert h["status"] == "P0" and h["targets"]["glsl"] == "300es"
    assert set(h["targets"]["needs"]) <= set(M.KNOWN_NEEDS)
    assert h["card"] == f"{m.name}.card" and (LIB / "cards" / h["card"]).is_file()
    assert sorted(h["exemplars"]) == sorted(g["exemplars"])
    assert h["learn"] and all(isinstance(x, str) for x in h["learn"])
    for path in h["twin"].split(";"):
        assert (REPO / path.strip().split(":")[0]).is_file()
    assert sorted(h.get("hooks") or []) == sorted(g["hook_signatures"].values())
    assert isinstance(h.get("debug"), list) and h["debug"]


@pytest.mark.parametrize("file", sorted(RECIPES))
def test_every_knob_is_a_valid_descriptor_with_a_uniform_and_an_entry_argument(library, file):
    m = _module(library, file)
    params = m.header["params"]
    names = [p["name"] for p in params]
    head, *rest = m.name.split("-")
    camel = head + "".join(w[:1].upper() + w[1:] for w in rest)
    for p in params:
        assert {"name", "label", "default", "group", "uniform", "help"} <= set(p), p
        # Vandor's ruling (b), 2026-10-13: u_<recipeCamel>_<param>, one rule across every group recipe
        assert p["uniform"] == f"u_{camel}_{p['name']}", p["uniform"]
        if "choices" not in p:
            assert {"unit", "range", "step"} <= set(p) and p["unit"] in P.NUMERIC_UNITS, p
        else:
            assert [c["value"] for c in p["choices"]] == list(range(len(p["choices"]))), \
                "choices are numbered 0, 1, 2, ... so a card's const int holds the same number the Workbench writes"
    assert len({p["uniform"] for p in params}) == len(params)
    descriptors = P.params_from_module(m.header)
    assert P.check_descriptors(descriptors) == [], P.check_descriptors(descriptors)
    args = _entry_args(m)
    assert [a[1] for a in args[-len(params):]] == names, "the knobs are the entry's last arguments, in header order"
    for (typ, _), p in zip(args[-len(params):], params):
        assert typ == ("int" if "choices" in p else "float"), (p["name"], typ)


@pytest.mark.parametrize("file", sorted(RECIPES))
def test_the_recipe_reaches_every_required_part_and_one_of_each_alternative(library, file):
    """The atlas's chain, part by part: called by the recipe or by a part it calls, or (for the frame the host sets
    up, such as uvCentered) by the recipe's own card, the reference host."""
    m = _module(library, file)
    g = _group(GROUP_OF[m.name])
    graph = {}                                                           # function -> the functions its body calls
    for name in library.resolve([m.name]):
        code = M.strip_comments(library.modules[name].body)
        for d in M.DEFINITION_RE.finditer(code):
            start = code.index("{", d.end() - 1)
            depth, end = 0, start
            for end in range(start, len(code)):
                depth += {"{": 1, "}": -1}.get(code[end], 0)
                if depth == 0:
                    break
            graph.setdefault(d.group(2), set()).update(M.CALL_RE.findall(code[start:end]))
    frontier = set(m.functions) | set(M.CALL_RE.findall(M.strip_comments(K.load_card(m.name).body)))
    reachable = set()
    while frontier:
        fn = frontier.pop()
        if fn not in reachable:
            reachable.add(fn)
            frontier |= graph.get(fn, set())
    for tier in g["tiers"]:
        for part in tier["required"]:
            assert part in reachable, f"{m.name} never calls the required part {part}"
        for choice in tier["alternatives"]:
            assert any(all(f in reachable for f in alt) for alt in choice), (m.name, choice)


@pytest.mark.parametrize("file", sorted(RECIPES) + sorted(HELPERS))
def test_each_module_composes_and_lints_clean(library, file):
    m = _module(library, file)
    for target in ("toy", "webgl2"):
        text = library.compose([m.name], target=target)
        assert m.name in text.splitlines()[0]
    assert M.lint(m, library_module=True, library=library) == []


@pytest.mark.parametrize("file", sorted(RECIPES) + sorted(HELPERS))
def test_each_module_has_a_card_that_builds_and_binds_its_knobs_at_their_defaults(library, file):
    m = _module(library, file)
    card = K.load_card(m.name)
    assert m.name in card.uses and card.note
    built = K.build_card(card, library=library)
    assert m.name in built["card"]["modules"]
    if m.kind != "recipe":
        return
    assert list(card.times) == [0.0, 2.0, 4.0] and card.size == (480, 270)
    body = M.strip_comments(card.body)
    for p in m.header["params"]:
        want = p["default"]
        if "choices" in p:
            want = [c["value"] for c in p["choices"]].index(want)
        mm = re.search(rf"^\s*const\s+(float|int)\s+{p['uniform']}\s*=\s*([-0-9.eE]+)\s*;", body, re.M)
        assert mm, f"{card.name} does not hold {p['uniform']} as a const (the Workbench binds a knob there)"
        assert float(mm.group(2)) == float(want), (p["uniform"], mm.group(2), want)
        assert re.search(rf"\b{p['uniform']}\b", body[mm.end():]), f"{p['uniform']} is declared and never used"


def test_parity_helper_header_follows_the_atlas(library):
    m = _module(library, "composite/parity.glsl")
    h = m.header
    part = next(p for p in _atlas()["parts"] if "cmpXor" in p["functions"])
    assert h["kind"] == "helper" and h["cat"] == part["category"] == "K3" and h["family"] == "K"
    assert set(m.functions) == {"cmpXor"} and h["license"] == "Apache-2.0"
    assert all("http" in c for c in h["credits"]) and 10 <= h["order"] <= 30
    assert sorted(h["exemplars"]) == sorted(part["exemplars"]) and h["status"] == "P1"
    assert (REPO / h["twin"].split(":")[0]).is_file()
    defs = [d for d in M.DEFINITION_RE.finditer(M.strip_comments(m.body))]
    assert [(d.group(1), d.group(2)) for d in defs] == [("float", "cmpXor")]


def test_no_module_redeclares_a_batch_a_name_or_reaches_for_the_sine_hash(library):
    for file in {**RECIPES, **HELPERS}:
        m = _module(library, file)
        code = M.strip_comments(m.body)
        assert "hashSine" not in code and not re.search(r"\bsin\s*\(\s*dot", code)
        assert not re.search(r"\bconst\s+float\s+(PI|TAU|PHI|SQRT3)\b", code)
        assert not re.search(r"\buniform\b", code), "recipes take knobs as arguments; the host declares the uniforms"
    assert "composite-parity" in library.resolve(["hex-neon"])


# ====================================================================================== the GPU against the twins
PARITY_CARD = """\
//! {"card": "parity-groups-g2", "uses": ["neon-line", "hex-neon", "studio-object", "composite-parity",
//!  "draw2-aa", "draw2-sdf2", "sdf-shapes"], "t": [0], "size": [512, 64],
//!  "note": "Not a house card: three group recipes and cmpXor, compared pixel by pixel with their CPU twins."}
// Apache-2.0, Akashic Aurora. Written fresh for the parity test.
float mapScene(vec3 p) {
    float ball = length(p - vec3(-0.2, 0.0, 0.0)) - 0.4;
    return min(ball, sdBox(p - vec3(0.35, -0.2, 0.1), vec3(0.22)));
}
vec3 materialAt(vec3 p, vec3 n, float id) {
    return id > 0.5 ? vec3(0.18) : (p.x < 0.1 ? vec3(0.6, 0.1, 0.05) : vec3(0.05, 0.2, 0.6));
}
void mainImage(out vec4 color, in vec2 pixel) {
    vec2 at = floor(pixel);
    int panel = int(at.x) / 64;
    vec2 local = pixel - vec2(64.0 * float(panel), 0.0);
    vec2 p = local / 32.0 - 1.0;
    float px = 1.0 / 32.0;
    vec3 v = vec3(0.0);
    if (panel == 0) {
        vec2 best = vec2(1e9, 0.0);
        best = neonPathStep(p, vec2(-0.9, -0.6), vec2(0.1, 0.5), vec2(0.0, 0.5), best);
        best = neonPathStep(p, vec2(0.1, 0.5), vec2(0.8, -0.2), vec2(0.5, 1.0), best);
        v = neonLine(vec3(0.0), best.x, px, vec3(0.2, 0.55, 1.0), 1.0 - 0.5 * best.y, 0.0, 1.6, 14.0, 0, 1.6, 0, 0.35, 0);
        v = neonLine(v, sd2Segment(p, vec2(-0.8, 0.6), vec2(0.9, -0.7)).x, px, vec3(1.0, 0.35, 0.2), 0.8, 0.0,
                     1.6, 14.0, 0, 1.6, 0, 0.35, 0);
        v *= 0.5;
    } else if (panel == 1) {
        float depth = local.x / 64.0;
        v = neonLine(vec3(0.0), abs(p.y - 0.3 * p.x), px, vec3(0.6, 0.3, 1.0), 1.0, depth, 2.5, 10.0, 1, 3.0, 1, 1.0, 0);
        v = neonLine(v, abs(p.y + 0.5), px, vec3(0.1, 0.9, 0.7), 0.7, 0.0, 0.7, 20.0, 2, 0.5, 1, 0.0, 0);
        v *= 0.5;
    } else if (panel == 2) {
        float d = local.x * 0.5;
        float halo = 4.0 + local.y * 0.25;
        v = vec3(neonProfile(d, halo, 0), neonProfile(d, halo, 1), neonProfile(d, halo, 2));
    } else if (panel == 3) {
        v = 0.5 * hexNeon(p * 0.6, px * 0.6, 1.7, vec2(0.0), 0.22, 1.5, 7.0, 0.6, 0.55, 0.35, 0, 0.1, 0, 0);
    } else if (panel == 4) {
        v = 0.5 * hexNeon(p * 0.6, px * 0.6, 4.1, vec2(0.2, -0.1), 0.25, 2.0, 5.0, 0.9, 1.0, 0.8, 1, 0.1, 1, 0);
    } else if (panel == 5) {
        v = hexNeon(p * 0.6, px * 0.6, 2.9, vec2(0.0), 0.3, 1.5, 7.0, 0.6, 1.0, 0.35, 0, 0.2, 2, 0);
    } else if (panel == 6) {
        float a = aaFill(sd2Circle(p - vec2(-0.25, 0.1), 0.5), px);
        float b = aaFill(sd2Circle(p - vec2(0.25, 0.1), 0.5), px);
        float c = aaFill(sd2Circle(p - vec2(0.0, -0.35), 0.5), px);
        v = vec3(cmpXor(a, b), cmpXor(b, c), cmpXor(cmpXor(a, b), c));
    } else {
        v = 0.6 * studioObject(vec3(0.6, 0.8, 3.9), vec3(0.0), local, vec2(64.0), 3.2, 0.85, 48.0, 0.42, 0.5, 0.04, 0.0,
                               0.25, 6.0, 0.35, 1.1, 0.62, 0.75, 96.0, 1.0, 0);
    }
    color = vec4(clamp(v, 0.0, 1.0), 1.0);
}
"""


def _parity_scene(p):
    p = np.asarray(p, dtype=np.float64)
    ball_ = np.linalg.norm(p - [-0.2, 0.0, 0.0]) - 0.4
    block = float(twin("sdf").sdBox((p - [0.35, -0.2, 0.1]).astype(F32), np.full(3, 0.22, F32)))
    return float(min(ball_, block))


def _parity_material(p, n, ident):
    if ident > 0.5:
        return np.full(3, 0.18)
    return np.array([0.6, 0.1, 0.05]) if p[0] < 0.1 else np.array([0.05, 0.2, 0.6])


def _twin_parity_image(studio_every=2):
    n, h, s, x, d2 = twin("neon_line"), twin("hex_neon"), twin("studio_object"), twin("parity"), twin("draw2")
    ys, xs = np.mgrid[0:64, 0:64]
    local = np.stack([xs + 0.5, ys + 0.5], -1).astype(np.float64)
    p = local / 32.0 - 1.0
    px = 1.0 / 32.0
    out = np.full((64, 512, 3), np.nan)
    z = np.zeros((64, 64, 3))
    best = np.stack([np.full((64, 64), 1e9), np.zeros((64, 64))], -1)
    best = n.neonPathStep(p, (-0.9, -0.6), (0.1, 0.5), (0.0, 0.5), best)
    best = n.neonPathStep(p, (0.1, 0.5), (0.8, -0.2), (0.5, 1.0), best)
    v = n.neonLine(z, best[..., 0], px, np.array([0.2, 0.55, 1.0]), 1.0 - 0.5 * best[..., 1], 0.0, 1.6, 14.0, 0, 1.6,
                   0, 0.35, 0)
    seg = d2.sd2Segment(p.astype(F32), np.array([-0.8, 0.6], F32), np.array([0.9, -0.7], F32))[..., 0]
    v = n.neonLine(v, seg, px, np.array([1.0, 0.35, 0.2]), 0.8, 0.0, 1.6, 14.0, 0, 1.6, 0, 0.35, 0)
    out[:, 0:64] = 0.5 * v
    depth = local[..., 0] / 64.0
    v = n.neonLine(z, np.abs(p[..., 1] - 0.3 * p[..., 0]), px, np.array([0.6, 0.3, 1.0]), 1.0, depth, 2.5, 10.0, 1,
                   3.0, 1, 1.0, 0)
    v = n.neonLine(v, np.abs(p[..., 1] + 0.5), px, np.array([0.1, 0.9, 0.7]), 0.7, 0.0, 0.7, 20.0, 2, 0.5, 1, 0.0, 0)
    out[:, 64:128] = 0.5 * v
    dd, halo = local[..., 0] * 0.5, 4.0 + local[..., 1] * 0.25
    out[:, 128:192] = np.stack([n.neonProfile(dd, halo, k) for k in range(3)], -1)
    out[:, 192:256] = 0.5 * h.hexNeon(p * 0.6, px * 0.6, 1.7, np.zeros(2), 0.22, 1.5, 7.0, 0.6, 0.55, 0.35, 0, 0.1, 0, 0)
    out[:, 256:320] = 0.5 * h.hexNeon(p * 0.6, px * 0.6, 4.1, np.array([0.2, -0.1]), 0.25, 2.0, 5.0, 0.9, 1.0, 0.8, 1,
                                      0.1, 1, 0)
    out[:, 320:384] = h.hexNeon(p * 0.6, px * 0.6, 2.9, np.zeros(2), 0.3, 1.5, 7.0, 0.6, 1.0, 0.35, 0, 0.2, 2, 0)
    fill = lambda c: d2.aaFill(d2.sd2Circle((p - c).astype(F32), F32(0.5)), F32(px)).astype(np.float64)
    a, b, c = fill([-0.25, 0.1]), fill([0.25, 0.1]), fill([0.0, -0.35])
    out[:, 384:448] = np.stack([x.cmpXor(a, b), x.cmpXor(b, c), x.cmpXor(x.cmpXor(a, b), c)], -1)
    for j in range(0, 64, studio_every):
        for i in range(0, 64, studio_every):
            out[j, 448 + i] = 0.6 * s.studioObject(np.array([0.6, 0.8, 3.9]), np.zeros(3), local[j, i],
                                                   np.array([64.0, 64.0]), 3.2, 0.85, 48.0, 0.42, 0.5, 0.04, 0.0, 0.25, 6.0,
                                                   0.35, 1.1, 0.62, 0.75, 96.0, 1.0, 0, _parity_scene, _parity_material)
    return (np.round(np.clip(out, 0, 1) * 255.0))[::-1]                  # PNG rows run top down


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH (the headless driver)")
def test_the_glsl_matches_its_twins_on_swiftshader(tmp_path):
    from PIL import Image
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "parity-groups-g2.card").write_text(PARITY_CARD, encoding="utf-8", newline="\n")
    report = K.render_cards(["parity-groups-g2"], cards_dir=cards_dir, out_root=tmp_path / "out",
                            allow_tracked=True, lock_wait_min=5, quiet=True)
    if report["driver"].get("error") and "lock" in str(report["driver"]["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {report['driver']['error']}")
    row = report["cards"][0]
    assert row["compile_ok"] is True and row["nan_pixels"] == 0, row
    png = sorted((tmp_path / "out" / "parity-groups-g2").glob("t0*.png"))[0]
    gpu = np.asarray(Image.open(png).convert("RGB")).astype(np.float64)
    cpu = _twin_parity_image()
    miss = np.abs(gpu - cpu)
    smooth = miss[:, 0:192]                                       # lines and profiles: continuous everywhere
    assert smooth.max() <= 3 and np.mean(smooth > 1) < 0.003, f"neon drift: max {smooth.max()}"
    tiles = miss[:, 192:448]                                      # lattices and coverage: a tie may land in the next cell
    assert np.mean(tiles > 2) < 0.01, f"hex/parity drift: {np.mean(tiles > 2):.4f} of pixels"
    studio = miss[:, 448:512][np.isfinite(cpu[:, 448:512])]       # a march: silhouettes may step differently
    assert np.mean(studio > 3) < 0.03 and np.mean(studio) < 1.0, \
        f"studio drift: {np.mean(studio > 3):.4f} of pixels over 3, mean {np.mean(studio):.3f}"
