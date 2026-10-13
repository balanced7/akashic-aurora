"""Pins for the light family of the house GLSL library (shader school batch B, atlas family F): the CPU twins against
the physics they claim, and the GLSL modules against their twins on SwiftShader.

WHAT IS PINNED, AND AGAINST WHAT. Each claim in a module's contract is checked by an independent route where one
exists, not by re-typing the module's own formula:
  * Diffuse (light/diffuse.glsl): energy-normalised wrap keeps exactly Lambert's pi of energy for every wrap (a
    numerical integral over the sphere); the hemisphere term equals the irradiance of an unoccluded uniform dome
    (another integral).
  * Specular (light/specular.glsl): normalised Blinn-Phong's directional albedo stays within a few per cent of 1 as
    the exponent climbs (numerical integral against the closed form s(s+8)/((s+2)(s+4))).
  * Fresnel (light/fresnel.glsl): Schlick's end points, F0 of water, glass and diamond, and Schlick against the exact
    dielectric Fresnel equations away from grazing.
  * Lights, glass and glow: the window reaches zero at the radius; Snell's law for refraction and the mirror on total
    internal reflection; Beer-Lambert round trips; glow emission independent of step count; the house's own two-
    Gaussian constants reproduced; hot cores whiten while keeping the hottest channel.
  * Environment and rig (light/env.glsl, light/rigs.glsl): the key panel's centre radiance, its brighter rim, edges
    that widen with roughness at near-constant energy, no ground edge at the horizon; the rig's emissive bypass and the
    law that ambient occlusion never touches the key.
  * Visibility (light/visibility.glsl): the soft shadow and the ambient occlusion on a sphere-over-floor scene: full
    shadow in the umbra, fully lit in the open (including a floor lit from straight above, the case where the
    triangulated penumbra estimate divides zero by zero, and an open floor under a light 10 to 25 degrees up, where
    the batch-B review found it black), a monotone penumbra that widens with the light's size.

SLOW TESTS. The GPU half renders one probe card on SwiftShader under the house GPU lock (render.py's driver, one
burst), exactly as tests/test_glsl_twins_colour.py does: every result's float32 bits are written into pixels and
compared with the twin. Deselect with  py -m pytest -m "not slow".
"""
from __future__ import annotations

import json
import math
import shutil
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from arsenal.shaders.twins import light as L

REPO = Path(__file__).resolve().parents[1]
GLSL = REPO / "arsenal" / "web" / "glsl"

MODULES = {   # module name -> file, as the atlas manifest places them
    "light-diffuse": "light/diffuse.glsl",
    "light-specular": "light/specular.glsl",
    "light-fresnel": "light/fresnel.glsl",
    "light-lights": "light/lights.glsl",
    "light-visibility": "light/visibility.glsl",
    "light-env": "light/env.glsl",
    "light-glass": "light/glass.glsl",
    "light-glow": "light/glow.glsl",
    "light-rigs": "light/rigs.glsl",
}
CATEGORY = {"light-diffuse": "F1", "light-specular": "F2", "light-fresnel": "F3", "light-lights": "F4",
            "light-visibility": "F5", "light-env": "F6", "light-glass": "F7", "light-glow": "F9", "light-rigs": "F10"}
PROVIDES = {   # the P0 functions and structs atlas.json's batch-B manifest places in each file
    "light-diffuse": {"litLambert", "litHalfLambert", "litWrapDiffuse", "litHemisphere"},
    "light-specular": {"litBlinnPhong"},
    "light-fresnel": {"litFresnelSchlick", "litF0FromIor", "litRim"},
    "light-lights": {"litInverseSquare"},
    "light-visibility": {"visSoftShadow", "visAO"},
    "light-env": {"StudioParams", "litStudioEnv", "litFloorPool"},
    "light-glass": {"litRefractTIR", "litSigmaFromColour"},
    "light-glow": {"glowAccum", "glowEmitStep", "glowExp", "glowLorentz", "glowTwoGauss", "glowHotCore",
                   "glowStepCount"},
    "light-rigs": {"LitSurface", "rigStudio"},
}


def close(a, b, tol):
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return a.shape == b.shape and bool(np.all(np.abs(a - b) <= tol))


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def sphere_points(n=400_000):
    """A Fibonacci lattice: n nearly uniform unit directions; each stands for 4 pi / n steradians."""
    i = np.arange(n) + 0.5
    z = 1.0 - 2.0 * i / n
    r = np.sqrt(1.0 - z * z)
    phi = math.pi * (3.0 - math.sqrt(5.0)) * i
    return np.stack([r * np.cos(phi), z, r * np.sin(phi)], axis=-1)     # y is up, like the house frame


DIRS = sphere_points()
SOLID = 4.0 * math.pi / len(DIRS)


def rng():
    return np.random.default_rng(20261013)


# --------------------------------------------------------------------------------------------------------- diffuse F1
def test_lambert_is_the_clamped_cosine():
    n = np.array([0.0, 1.0, 0.0])
    for ang in (0.0, 0.3, 1.0, math.pi / 2, 2.0, math.pi):
        l = np.array([math.sin(ang), math.cos(ang), 0.0])
        assert abs(L.litLambert(n, l) - max(math.cos(ang), 0.0)) < 1e-12


def test_half_lambert_keeps_the_back_shaped():
    n = np.array([0.0, 0.0, 1.0])
    assert abs(L.litHalfLambert(n, n) - 1.0) < 1e-12
    assert abs(L.litHalfLambert(n, np.array([1.0, 0.0, 0.0])) - 0.25) < 1e-12      # the terminator sits at a quarter
    assert abs(L.litHalfLambert(n, -n)) < 1e-12                                     # black only straight behind
    assert L.litHalfLambert(n, unit([0.0, 1.0, -1.0])) > 0.0                        # past the terminator, still shaped


@pytest.mark.parametrize("w", [0.0, 0.25, 0.5, 1.0])
def test_wrap_diffuse_keeps_lamberts_energy_for_every_wrap(w):
    n = np.array([0.0, 1.0, 0.0])
    energy = float(np.sum(L.litWrapDiffuse(n, DIRS, w)) * SOLID)
    assert abs(energy - math.pi) < 2e-3 * math.pi, energy          # McAuley and Hill: (NoL + w) / (1 + w)^2
    assert abs(L.litWrapDiffuse(n, n, w) - 1.0 / (1.0 + w)) < 1e-12   # the peak drops so the wrapped light pays for it
    edge = np.array([math.sqrt(1.0 - w * w), -w, 0.0])               # NoL = -w: where the wrapped light ends
    assert abs(L.litWrapDiffuse(n, edge, w)) < 1e-12


def test_wrap_zero_is_lambert():
    l = unit(rng().normal(size=(200, 3)))
    n = unit(rng().normal(size=(200, 3)))
    assert close(L.litWrapDiffuse(n, l, 0.0), L.litLambert(n, l), 1e-12)


@pytest.mark.parametrize("tilt", [0.0, 0.4, 1.0, math.pi / 2, 2.2, math.pi])
def test_hemisphere_is_the_irradiance_of_an_unoccluded_uniform_dome(tilt):
    n = np.array([math.sin(tilt), math.cos(tilt), 0.0])
    sky = DIRS[DIRS[:, 1] > 0.0]
    irradiance = float(np.sum(np.maximum(sky @ n, 0.0)) * SOLID) / math.pi     # a unit-radiance upper dome, pi folded
    got = L.litHemisphere(n, [1.0, 1.0, 1.0], [0.0, 0.0, 0.0])
    assert close(got, [irradiance] * 3, 3e-3), (got, irradiance)
    assert close(L.litHemisphere(n, [0.2, 0.4, 0.8], [0.3, 0.2, 0.1]),
                 np.array([0.3, 0.2, 0.1]) + (np.array([0.2, 0.4, 0.8]) - [0.3, 0.2, 0.1]) * (0.5 + 0.5 * n[1]),
                 1e-12)


# -------------------------------------------------------------------------------------------------------- specular F2
@pytest.mark.parametrize("s", [16.0, 64.0, 256.0, 1024.0])
def test_normalised_blinn_phong_keeps_its_energy_as_the_highlight_sharpens(s):
    # Seen head-on (v = n) the lobe is symmetric about n, so the directional albedo is a 1D integral over the light's
    # polar angle: the twin is sampled along one meridian, then integrated with the ring weight 2 pi sin(theta).
    n = np.array([0.0, 1.0, 0.0])
    theta = (np.arange(200_000) + 0.5) * (math.pi / 2.0) / 200_000
    l = np.stack([np.sin(theta), np.cos(theta), np.zeros_like(theta)], axis=-1)
    h = unit(l + n)
    ring = 2.0 * math.pi * np.sin(theta) * (math.pi / 2.0) / 200_000
    albedo = float(np.sum(L.litBlinnPhong(n, h, s) * np.cos(theta) * ring))
    closed = s * (s + 8.0) / ((s + 2.0) * (s + 4.0))          # the integral done by hand (u = cos(theta / 2))
    assert abs(albedo - closed) < 2e-3 * closed, (albedo, closed)
    assert 0.99 < closed < 1.08                                # constant to a few per cent: the dot only concentrates
    plain = float(np.sum(np.maximum(h @ n, 0.0) ** s * np.cos(theta) * ring))
    assert plain < 26.0 / s                                    # unnormalised, the total light falls as 1/s: plastic


def test_blinn_phong_peak_rises_with_the_exponent():
    n = np.array([0.0, 1.0, 0.0])
    peaks = [L.litBlinnPhong(n, n, s) for s in (8.0, 64.0, 512.0)]
    assert close(peaks, [(s + 8.0) / (8.0 * math.pi) for s in (8.0, 64.0, 512.0)], 1e-12)
    assert peaks[0] < peaks[1] < peaks[2]
    assert L.litBlinnPhong(n, np.array([1.0, 0.0, 0.0]), 32.0) == 0.0


# --------------------------------------------------------------------------------------------------------- fresnel F3
def exact_dielectric_fresnel(cos_i, eta):
    """Unpolarised Fresnel reflectance, eta = n_t / n_i (Lagarde's memo form); 1 under total internal reflection."""
    g2 = eta * eta - 1.0 + cos_i * cos_i
    if g2 < 0.0:
        return 1.0
    g = math.sqrt(g2)
    a = (g - cos_i) / (g + cos_i)
    b = (cos_i * (g + cos_i) - 1.0) / (cos_i * (g - cos_i) + 1.0)
    return 0.5 * a * a * (1.0 + b * b)


def test_schlick_end_points_and_both_forms():
    for f0 in (0.02, 0.04, 0.5, 1.0):
        assert abs(L.litFresnelSchlick(1.0, f0) - f0) < 1e-12
        assert abs(L.litFresnelSchlick(0.0, f0) - 1.0) < 1e-12
    gold = np.array([1.0, 0.71, 0.29])
    for c in (0.0, 0.3, 0.77, 1.0):
        assert close(L.litFresnelSchlick3(gold, c), [L.litFresnelSchlick(c, g) for g in gold], 1e-12)
    cs = np.linspace(0.0, 1.0, 101)
    assert np.all(np.diff(L.litFresnelSchlick(cs, 0.04)) <= 0.0)       # brighter toward grazing, never the reverse


def test_schlick_tracks_the_exact_dielectric_fresnel_away_from_grazing():
    f0 = L.litF0FromIor(1.5)
    for deg in range(0, 80, 5):
        c = math.cos(math.radians(deg))
        assert abs(L.litFresnelSchlick(c, f0) - exact_dielectric_fresnel(c, 1.5)) < 0.02, deg   # measured max 0.0196


def test_f0_from_ior():
    assert abs(L.litF0FromIor(1.0)) < 1e-15
    assert abs(L.litF0FromIor(1.33) - (0.33 / 2.33) ** 2) < 1e-15 and abs(L.litF0FromIor(1.33) - 0.0200593) < 1e-6
    assert abs(L.litF0FromIor(1.5) - 0.04) < 1e-15
    assert abs(L.litF0FromIor(2.42) - 0.1723949) < 1e-6           # diamond: (1.42 / 3.42)^2
    for n in (1.2, 1.5, 2.4):
        assert abs(L.litF0FromIor(1.0 / n) - L.litF0FromIor(n)) < 1e-15        # the same from either side
        assert abs(L.litF0FromIor(n) - exact_dielectric_fresnel(1.0, n)) < 1e-12


def test_rim_is_an_art_term_with_a_power():
    assert abs(L.litRim(0.5, 1.0) - 0.5) < 1e-12
    assert abs(L.litRim(0.5, 0.2) - 0.5 ** 0.2) < 1e-12       # a small power flattens a sphere into a glowing disc
    assert abs(L.litRim(0.0, 3.0) - 1.0) < 1e-12 and abs(L.litRim(-0.4, 3.0) - 1.0) < 1e-12
    assert L.litRim(1.0, 2.0) < 1e-20 and math.isfinite(L.litRim(1.0, 0.0))


# ---------------------------------------------------------------------------------------------------------- lights F4
def test_inverse_square_window():
    r = 4.0
    assert L.litInverseSquare(r, r) == 0.0 and L.litInverseSquare(9.0, r) == 0.0
    for d in (0.1, 0.5, 1.0):                      # far inside the radius: plain 1/d^2 within 1 per cent
        assert abs(L.litInverseSquare(d, r) * d * d - 1.0) < 0.01
    d = np.linspace(0.0, 5.0, 501)
    f = L.litInverseSquare(d, r)
    assert np.all(np.isfinite(f)) and abs(f[0] - 1.0e4) < 1e-6      # a 1 cm floor: finite at the light itself
    assert np.all(np.diff(f) <= 0.0)
    assert abs(L.litInverseSquare(2.0, r) - (1.0 - 0.5 ** 4) ** 2 / 4.0) < 1e-12


# ----------------------------------------------------------------------------------------------------------- glass F7
@pytest.mark.parametrize("eta", [1.0 / 1.5, 1.0 / 1.33, 1.5, 1.04])
def test_refraction_obeys_snell_and_reflects_under_total_internal_reflection(eta):
    n = np.array([0.0, 1.0, 0.0])
    for deg in range(0, 90, 3):
        th = math.radians(deg)
        i = np.array([math.sin(th), -math.cos(th), 0.0])      # arriving from above, against the normal
        for normal in (n, -n):                                 # the caller may pass the normal on either side
            ok, t = L.litRefractTIR(i, normal, eta)
            assert abs(np.linalg.norm(t) - 1.0) < 1e-12
            if eta * math.sin(th) < 1.0:
                assert ok
                assert abs(t[0] - eta * math.sin(th)) < 1e-12 and t[1] < 0.0 and abs(t[2]) < 1e-12   # Snell
            else:
                assert not ok
                assert close(t, [i[0], -i[1], i[2]], 1e-12)                                         # the mirror


def test_sigma_from_colour_is_beer_lambert_backwards():
    c = np.array([0.8, 0.35, 0.1])
    for dist in (0.5, 2.0):
        sigma = L.litSigmaFromColour(c, dist)
        assert close(np.exp(-sigma * dist), c, 1e-12)
        assert close(np.exp(-sigma * 2.0 * dist), c * c, 1e-12)        # twice as thick: the colour squared
    assert close(L.litSigmaFromColour([1.0, 1.0, 1.0], 1.0), [0.0, 0.0, 0.0], 0.0)
    assert np.all(np.isfinite(L.litSigmaFromColour([0.0, 0.0, 0.0], 0.0)))


# ------------------------------------------------------------------------------------------------------------ glow F9
def test_glow_accum_is_one_over_distance_with_a_floor():
    acc = L.glowAccum([0.1, 0.0, 0.0], [1.0, 0.5, 0.25], 0.5, 0.01)
    assert close(acc, [2.1, 1.0, 0.5], 1e-12)
    assert close(L.glowAccum([0.0] * 3, [1.0, 1.0, 1.0], 0.0, 0.02), [50.0] * 3, 1e-9)
    assert close(L.glowAccum([0.0] * 3, [1.0, 1.0, 1.0], -3.0, 0.02), [50.0] * 3, 1e-9)    # inside: the floor


def test_glow_emit_step_is_independent_of_the_step_count():
    def march(steps):
        dt = 4.0 / steps
        ts = (np.arange(steps) + 0.5) * dt
        return sum(L.glowEmitStep(math.exp(-t), dt, 2.0) for t in ts)
    coarse, fine = march(16), march(256)
    assert abs(coarse - fine) < 0.01 * fine and abs(fine - 2.0 * (1.0 - math.exp(-4.0))) < 1e-4
    counted = [sum(math.exp(-t) for t in (np.arange(s) + 0.5) * 4.0 / s) for s in (16, 256)]
    assert counted[1] > 10.0 * counted[0]            # counting per step instead grows with the steps: the bug it fixes


def test_glow_exp_and_lorentz():
    assert abs(L.glowExp(0.0, 3.0) - 1.0) < 1e-15 and abs(L.glowExp(1.0 / 3.0, 3.0) - math.exp(-1.0)) < 1e-12
    assert abs(L.glowExp(-1.0, 3.0) - 1.0) < 1e-15
    k = 0.01
    assert abs(L.glowLorentz(0.0, k) - 1.0) < 1e-15 and abs(L.glowLorentz(math.sqrt(k), k) - 0.5) < 1e-12
    assert abs(L.glowLorentz(10.0, k) * 100.0 / k - 1.0) < 1e-3       # tails fall as k / d^2
    assert abs(L.glowLorentz(-0.3, k) - L.glowLorentz(0.3, k)) < 1e-15


def test_two_gauss_reproduces_the_house_light_lines():
    s = np.linspace(-1.0, 1.0, 81)
    flight = np.exp(-s * s * 24.0) + 0.18 * np.exp(-s * s * 3.0)            # gyre-flight.js:24
    rays = np.exp(-s * s * 38.0) * 0.78 + np.exp(-s * s * 5.0) * 0.12       # gyre-light-rays.mjs:14
    assert close(L.glowTwoGauss(s, [24.0, 1.0, 3.0, 0.18]), flight, 1e-12)
    assert close(L.glowTwoGauss(s, [38.0, 0.78, 5.0, 0.12]), rays, 1e-12)


def test_hot_core_whitens_while_the_hottest_channel_leads():
    tint = np.array([1.0, 0.3, 0.05])
    assert close(L.glowHotCore(tint, 0.0), [0.0, 0.0, 0.0], 0.0)
    dim = L.glowHotCore(tint, 0.05)
    assert close(dim / dim[0], tint, 0.01)                                   # faint: the tint itself
    prev = np.zeros(3)
    for i in (0.1, 0.5, 1.0, 2.0, 4.0, 8.0):
        hot = L.glowHotCore(tint, i)
        assert abs(hot[0] - i) < 1e-12                                       # the hottest channel is never touched
        assert np.all(hot >= prev - 1e-12)
        prev = hot
    assert np.min(prev) > 0.98 * prev[0]                                     # by 8: white
    assert np.all(np.isfinite(L.glowHotCore(tint, 1e18)))


def test_step_count_glow():
    assert L.glowStepCount(0.0, 64.0, 2.0) == 0.0 and L.glowStepCount(64.0, 64.0, 2.0) == 1.0
    assert L.glowStepCount(200.0, 64.0, 2.0) == 1.0
    for s in (8.0, 16.0, 40.0):
        x = s / 64.0
        assert abs(L.glowStepCount(s, 64.0, 1.0) - x) < 1e-12
        assert abs(L.glowStepCount(s, 64.0, 2.0) - (1.0 - (1.0 - x) ** 2)) < 1e-12
    assert math.isfinite(L.glowStepCount(64.0, 64.0, 0.0))


# ------------------------------------------------------------------------------------------------------ environment F6
def test_floor_pool_is_a_gaussian_disc():
    col = np.array([0.6, 0.5, 0.4])
    c = np.array([0.5, -1.0, 0.25])
    assert close(L.litFloorPool(c + [0.0, 3.0, 0.0], c, 0.8, col), col, 1e-12)             # height never counts
    assert close(L.litFloorPool(c + [0.8, 0.0, 0.0], c, 0.8, col), col * math.exp(-1.0), 1e-12)
    assert np.all(L.litFloorPool(c + [0.0, 0.0, 1.6], c, 0.8, col) < 0.02 * col)


def studio(**kw):
    return replace(L.studio_default(), **kw)


def test_studio_env_is_finite_and_non_negative_everywhere():
    for rough in (0.0, 0.5, 1.0):
        env = L.litStudioEnv(DIRS[::7], rough, L.studio_default())
        assert np.all(np.isfinite(env)) and np.all(env >= 0.0)


def test_the_key_panel_shows_its_centre_radiance_and_a_brighter_rim():
    s = L.studio_default()
    dark = studio(keyCol=np.zeros(3))
    key = L.litStudioEnv(s.keyDir, 0.0, s) - L.litStudioEnv(s.keyDir, 0.0, dark)
    assert close(key, s.keyCol, 1e-9)
    across, along = L.panel_frame(s.keyDir)
    near_rim = unit(s.keyDir + 0.9 * s.boxSize[0] * across)
    rim = L.litStudioEnv(near_rim, 0.0, s) - L.litStudioEnv(near_rim, 0.0, dark)
    assert np.all(rim > 1.3 * key)                                      # a real diffuser panel: a hot frame


def test_roughness_widens_the_panel_edge_at_nearly_constant_energy():
    s = studio(rimBright=0.0)
    dark = studio(rimBright=0.0, keyCol=np.zeros(3))
    across, _ = L.panel_frame(s.keyDir)
    outside = unit(s.keyDir + 1.25 * s.boxSize[0] * across)
    lum = lambda env: float(env @ [0.2126, 0.7152, 0.0722])            # noqa: E731
    assert lum(L.litStudioEnv(outside, 0.0, s) - L.litStudioEnv(outside, 0.0, dark)) < 1e-9
    assert lum(L.litStudioEnv(outside, 1.0, s) - L.litStudioEnv(outside, 1.0, dark)) > 0.05
    energy = []
    for rough in (0.0, 0.5, 1.0):
        e = (L.litStudioEnv(DIRS, rough, s) - L.litStudioEnv(DIRS, rough, dark)) @ [0.2126, 0.7152, 0.0722]
        energy.append(float(np.sum(e) * SOLID))
    assert max(energy) < 1.06 * min(energy), energy


@pytest.mark.parametrize("rim", [0.0, 0.8, 1.5])
def test_the_key_panel_keeps_its_energy_as_roughness_rises_with_a_bright_rim(rim):
    # Batch-B review, defect 4: the contract and the card promise a rough ball is "not brighter or darker than a
    # polished one, only softer", but the rim brightening (1 + rimBright (1 - roughness) edge^2, which averages
    # 1 + rimBright / 2 over a panel) faded with roughness and took its light with it: with the default rimBright 0.8
    # the key panel's energy over the sphere was 1.40, 1.31, 1.22, 1.12, 1.00 at roughness 0 .. 1. The pin above holds
    # rimBright 0 only; this one holds the default and a hotter frame.
    s = studio(rimBright=rim)
    dark = studio(rimBright=rim, keyCol=np.zeros(3))
    energy = []
    for rough in (0.0, 0.25, 0.5, 0.75, 1.0):
        e = (L.litStudioEnv(DIRS, rough, s) - L.litStudioEnv(DIRS, rough, dark)) @ [0.2126, 0.7152, 0.0722]
        energy.append(float(np.sum(e) * SOLID))
    assert max(energy) < 1.06 * min(energy), energy
    centre = L.litStudioEnv(s.keyDir, 0.0, s) - L.litStudioEnv(s.keyDir, 0.0, dark)
    assert close(centre, s.keyCol, 1e-9)                              # sharp: the panel's own colour at its centre


def test_no_soft_box_shows_a_speck_exactly_opposite_itself():
    # Batch-B review, defect 7: straight away from a box, its equal-area coordinates are 0 / 0 (the projection's
    # antipode), the floor on 0.5 + 0.5 dot made them 0, and the box shone at full brightness in that one direction
    # (3.78 against 0.17 just 3 mrad away). A direction that far from the box is never on it.
    s = L.studio_default()
    for box, col in ((s.keyDir, "keyCol"), (s.fillDir, "fillCol")):
        dark = studio(**{col: np.zeros(3)})
        for rough in (0.0, 0.5, 1.0):
            for off in (0.0, 1e-4, 3e-3):
                across, _ = L.panel_frame(box)
                d = unit(-box + off * across)
                extra = L.litStudioEnv(d, rough, s) - L.litStudioEnv(d, rough, dark)
                assert np.all(np.abs(extra) < 1e-6), (col, rough, off, extra)


def test_the_floor_dissolves_into_the_horizon_with_no_edge():
    s = L.studio_default()
    down = L.litStudioEnv(np.array([0.0, -1.0, 0.0]), 0.0, s)
    assert close(down, s.floorCol, 1e-9)                               # straight down: the pool's centre
    for az in np.linspace(0.0, 2.0 * math.pi, 13):
        flat = np.array([math.cos(az), 0.0, math.sin(az)])
        above = L.litStudioEnv(unit(flat + [0.0, 0.002, 0.0]), 0.0, s)
        below = L.litStudioEnv(unit(flat - [0.0, 0.002, 0.0]), 0.0, s)
        assert close(above, below, 0.03 * float(np.max(above)) + 1e-6), (az, above, below)


# ------------------------------------------------------------------------------------------------------------ rigs F10
def test_rig_emissive_bypasses_every_light():
    s = L.studio_default()
    glow = np.array([2.0, 0.4, 0.1])
    surf = L.LitSurface(diffuseColor=np.zeros(3), F0=np.zeros(3), alpha=0.3, emissive=glow)
    for ao in (0.0, 0.5, 1.0):
        n = unit(rng().normal(size=3))
        assert close(L.rigStudio(surf, n, unit([0.1, 0.2, 1.0]), ao, s), glow, 1e-12)


def test_rig_never_puts_ambient_occlusion_on_the_key():
    s = studio(skyCol=np.zeros(3), horizonCol=np.zeros(3), floorCol=np.zeros(3), fillCol=np.zeros(3))
    surf = L.LitSurface(diffuseColor=np.array([0.5, 0.4, 0.3]), F0=np.zeros(3), alpha=0.25, emissive=np.zeros(3))
    n, v = unit([0.2, 0.9, 0.3]), unit([0.0, 0.3, 1.0])
    lit = L.rigStudio(surf, n, v, 1.0, s)
    assert np.all(lit > 0.0) and close(L.rigStudio(surf, n, v, 0.0, s), lit, 1e-12)
    double = L.rigStudio(surf, n, v, 1.0, studio(skyCol=np.zeros(3), horizonCol=np.zeros(3), floorCol=np.zeros(3),
                                                 fillCol=np.zeros(3), keyCol=2.0 * s.keyCol))
    assert close(double, 2.0 * lit, 1e-12)                              # linear in the key


def test_rig_metal_is_its_environment():
    s = L.studio_default()
    metal = L.LitSurface(diffuseColor=np.zeros(3), F0=np.ones(3), alpha=0.09, emissive=np.zeros(3))
    n, v = unit([0.3, 0.8, 0.5]), unit([0.0, 0.0, 1.0])
    r = 2.0 * float(n @ v) * n - v
    assert close(L.rigStudio(metal, n, v, 0.6, s), 0.6 * L.litStudioEnv(r, 0.3, s), 1e-9)


# ------------------------------------------------------------------------------------------------------ visibility F5
SPHERE_C, SPHERE_R = np.array([0.0, 0.6, 0.0]), 0.5


def scene(p):
    """The probe's scene, as the GPU probe defines mapScene: a ball of radius 0.5 floating above the floor y = 0."""
    p = np.asarray(p, dtype=float)
    return min(float(np.linalg.norm(p - SPHERE_C)) - SPHERE_R, float(p[1]))


UP = np.array([0.0, 1.0, 0.0])


def shade_floor(x, angle, steps=48):
    return L.visSoftShadow(scene, np.array([x, 0.0, 0.0]), UP, (0.02, 6.0), angle, steps)


def test_soft_shadow_umbra_open_floor_and_the_lit_top():
    assert shade_floor(0.0, 0.05) < 0.01                         # straight under the ball
    assert shade_floor(1.6, 0.05) > 0.99                         # out in the open
    for x in (2.0, 3.0):                                         # the floor lit from straight above: no false shadow
        assert shade_floor(x, 0.2) > 0.99
    top = SPHERE_C + UP * SPHERE_R
    assert L.visSoftShadow(scene, top, UP, (0.02, 6.0), 0.1, 48) > 0.99
    side = SPHERE_C + unit([1.0, 1.0, 0.0]) * SPHERE_R           # leaving a curved surface at 45 degrees
    assert L.visSoftShadow(scene, side, unit([1.0, 2.0, 0.3]), (0.02, 6.0), 0.1, 48) > 0.99


def floor_only(p):
    """An open floor y = 0 and nothing else: every light above the horizon is visible from it."""
    return float(np.asarray(p, dtype=float)[1])


def toward_elevation(degrees):
    e = math.radians(degrees)
    return np.array([math.cos(e), math.sin(e), 0.0])


@pytest.mark.parametrize("degrees", [10, 15, 20, 25])
def test_soft_shadow_leaves_an_open_floor_lit_under_a_low_light(degrees):
    # Batch-B review, defect 1: with the light-visibility card's own settings (the start 0.002 off the floor, tRange
    # 0.01..8, 48 steps) an unoccluded floor went fully BLACK under a light 20 degrees up or lower (0.653 for the soft
    # light at 25). The shortest step (span / 8n) carried the ray past the last empty ball, so the two balls never met
    # (or barely touched), and the triangulation put the near miss at 0. The twin and the GLSL now triangulate only
    # where the step stayed inside the last ball and the balls meet; elsewhere the classic h / t.
    start = np.array([0.0, 0.002, 0.0])
    sharp = L.visSoftShadow(floor_only, start, toward_elevation(degrees), (0.01, 8.0), 0.02, 48)
    assert sharp > 0.99, sharp
    soft = L.visSoftShadow(floor_only, start, toward_elevation(degrees), (0.01, 8.0), 0.2, 48)
    # a light of radius 0.2 rad (11.5 degrees) whose centre stands 10 degrees up straddles the horizon (about 97 per
    # cent of its disk is above the floor, and h / t alone reads 0.95 there), so the estimate may dip at 10; from 15
    # degrees the whole disk clears the horizon
    assert soft > (0.85 if math.radians(degrees) < 0.2 else 0.99), soft
    # the probe's own scene and settings, on the floor well clear of the ball, the light low and facing away from it
    away = L.visSoftShadow(scene, np.array([2.5, 0.0, 0.0]), toward_elevation(degrees), (0.02, 6.0), 0.02, 48)
    assert away > 0.99, away


def test_soft_shadow_still_darkens_a_floor_behind_the_ball_under_a_low_light():
    # the guard must not open the shadow itself: a low light straight behind the ball still leaves an umbra on the floor
    behind = toward_elevation(15) * np.array([-1.0, 1.0, 1.0])               # light low in the -x direction
    floor_behind = np.array([0.0, 0.6, 0.0]) - behind * (0.6 / behind[1])     # where the ray to the light meets the ball's
    assert L.visSoftShadow(scene, floor_behind, behind, (0.02, 6.0), 0.02, 48) < 0.01      # centre, back on the floor


def test_soft_shadow_penumbra_is_monotone_and_widens_with_the_light():
    xs = np.linspace(0.0, 1.4, 57)
    widths = []
    for angle in (0.05, 0.25):
        s = np.array([shade_floor(x, angle) for x in xs])
        assert np.all(np.diff(s) >= -0.02), s                    # out of the shadow, never back in
        inside = xs[np.argmax(s > 0.1)]
        outside = xs[np.argmax(s > 0.9)]
        widths.append(outside - inside)
        half = xs[np.argmax(s > 0.5)]
        assert 0.3 < half < 0.8, half                            # the geometric edge of a ball 0.5 wide sits at 0.5-0.6
    assert widths[1] > 2.0 * widths[0], widths


def test_soft_shadow_step_budget_is_capped_at_the_constant_ceiling():
    assert L.VIS_MAX_SHADOW_STEPS == 64
    a = L.visSoftShadow(scene, np.array([0.7, 0.0, 0.0]), UP, (0.02, 6.0), 0.1, 64)
    b = L.visSoftShadow(scene, np.array([0.7, 0.0, 0.0]), UP, (0.02, 6.0), 0.1, 10_000)
    assert a == b


def test_ambient_occlusion_open_floor_contact_and_monotone():
    assert L.visAO(scene, np.array([3.0, 0.0, 0.0]), UP, 0.4, 0.8) == 1.0
    near = [L.visAO(scene, np.array([x, 0.0, 0.0]), UP, 0.4, 0.8) for x in (0.02, 0.1, 0.2, 0.3, 0.45, 0.7)]
    assert near[0] < 0.6
    assert all(b >= a - 1e-12 for a, b in zip(near, near[1:])), near
    under = SPHERE_C - UP * SPHERE_R                             # the ball's underside faces the floor 0.1 away
    assert L.visAO(scene, under, -UP, 0.4, 0.8) < 0.7


# ------------------------------------------------------------------------------------------- module files and cards
def _header(path):
    head = " ".join(line[3:] for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("//!"))
    return json.loads(head)


@pytest.mark.parametrize("name", sorted(MODULES))
def test_each_module_exists_with_its_header_and_its_card(name):
    path = GLSL / MODULES[name]
    assert path.is_file(), path
    header = _header(path)
    assert header["name"] == name and header["family"] == "F" and header["license"] == "Apache-2.0"
    assert header["cat"] == CATEGORY[name]
    for field in ("kind", "version", "credits", "cost", "contract", "note", "targets", "card", "twin", "status",
                  "exemplars", "learn"):
        assert field in header, (name, field)
    assert (GLSL / "cards" / header["card"]).is_file(), header["card"]
    assert b"\r" not in path.read_bytes()
    # every credit says where to read it: a link, or (for the house's own earlier work) a path in this repo (batch-B
    # review, defect 12: two credits named a book and a law with no link)
    assert all("http" in c or "arsenal/" in c for c in header["credits"]), [c[:60] for c in header["credits"]
                                                                            if "http" not in c and "arsenal/" not in c]


def test_the_library_provides_every_planned_part_and_lints_clean():
    from arsenal.shaders import modules as M
    lib = M.load_library()
    for name, wanted in PROVIDES.items():
        assert wanted <= set(lib.modules[name].provides), (name, wanted - set(lib.modules[name].provides))
        assert M.lint(lib.modules[name], library=lib) == [], name
    assert lib.modules["light-visibility"].hook_names == ("mapScene",)
    text = lib.compose(sorted(MODULES))
    assert text.count("float mapScene(vec3 p);") == 1


def test_the_light_modules_expose_only_names_the_atlas_plans():
    # The atlas owns every public name (tests/test_glsl_atlas.py says so for the whole library); this is the light
    # family's own copy of that pin, so a helper or a preset added here is caught here first.
    from arsenal.shaders import modules as M
    atlas = json.loads((REPO / "arsenal" / "shaders" / "atlas.json").read_text(encoding="utf-8"))
    planned = {fn for p in atlas["parts"] for fn in p["functions"]}
    lib = M.load_library()
    exposed = {n for name in MODULES for n in lib.modules[name].provides}
    assert sorted(exposed - planned) == []


# ======================================================================================== the GPU half (slow, locked)
V3_N = [tuple(unit(v)) for v in [(0.0, 1.0, 0.0), (0.3, 0.8, 0.2), (-0.6, 0.2, 0.7), (0.1, -0.9, 0.3), (1, 0, 0)]]
V3_L = [tuple(unit(v)) for v in [(0.2, 1.0, 0.4), (-0.5, 0.6, 0.6), (0.8, 0.1, -0.2), (0.0, 1.0, 0.0), (-1, 0.2, 0)]]
F_COS = [1.0, 0.8, 0.5, 0.2, 0.0]
SCENE_GLSL = """
float mapScene(vec3 p) {
    float ball = length(p - vec3(0.0, 0.6, 0.0)) - 0.5;
    return min(ball, p.y);
}

vec3 probeRefractDir(vec3 i, vec3 n, float eta) {
    vec3 bent;
    bool through = litRefractTIR(i, n, eta, bent);
    return bent;
}

float probeRefractOk(vec3 i, vec3 n, float eta) {
    vec3 bent;
    return litRefractTIR(i, n, eta, bent) ? 1.0 : 0.0;
}
"""


def _lin(v):
    return np.asarray(v, dtype=float)


def _groups():
    """(label, glsl expression over the named args, {arg: (type, values)}, twin(**args) -> 3 floats)."""
    v3 = lambda vals: ("vec3", vals)                       # noqa: E731
    f1 = lambda vals: ("float", vals)                      # noqa: E731
    sd = L.studio_default()
    incid = [tuple(unit(v)) for v in [(0.3, -1.0, 0.0), (0.9, -0.3, 0.1), (0.5, 0.8, 0.0), (0.0, -1.0, 0.0)]]
    surf = lambda a, b, t: L.LitSurface(diffuseColor=a, F0=b, alpha=t, emissive=_lin([0.03, 0.01, 0.0]))  # noqa
    view = unit([0.2, 0.3, 1.0])
    ao_points = [(3.0, 0.0, 0.0), (0.15, 0.0, 0.0), (0.4, 0.0, 0.3), (0.0, 0.1, 0.0)]
    groups = [
        ("litLambert", "vec3(litLambert(a, b), 0.0, 0.0)", {"a": v3(V3_N), "b": v3(V3_L)},
         lambda a, b: [L.litLambert(a, b), 0.0, 0.0]),
        ("litHalfLambert", "vec3(litHalfLambert(a, b), 0.0, 0.0)", {"a": v3(V3_N), "b": v3(V3_L)},
         lambda a, b: [L.litHalfLambert(a, b), 0.0, 0.0]),
        ("litWrapDiffuse", "vec3(litWrapDiffuse(a, b, t), 0.0, 0.0)",
         {"a": v3(V3_N), "b": v3(V3_L), "t": f1([0.0, 0.3, 0.5, 1.0, 0.7])},
         lambda a, b, t: [L.litWrapDiffuse(a, b, t), 0.0, 0.0]),
        ("litHemisphere", "litHemisphere(a, vec3(0.3, 0.5, 0.9), vec3(0.4, 0.25, 0.1))", {"a": v3(V3_N)},
         lambda a: L.litHemisphere(a, [0.3, 0.5, 0.9], [0.4, 0.25, 0.1])),
        ("litBlinnPhong", "vec3(litBlinnPhong(a, normalize(a + b), t), 0.0, 0.0)",
         {"a": v3(V3_N), "b": v3(V3_L), "t": f1([8.0, 32.0, 128.0, 0.0, 512.0])},
         lambda a, b, t: [L.litBlinnPhong(a, unit(a + b), t), 0.0, 0.0]),
        ("litFresnelSchlick float", "vec3(litFresnelSchlick(t, u), 0.0, 0.0)",
         {"t": f1(F_COS), "u": f1([0.04, 0.02, 0.5, 0.17, 0.04])},
         lambda t, u: [L.litFresnelSchlick(t, u), 0.0, 0.0]),
        ("litFresnelSchlick vec3", "litFresnelSchlick(a, t)",
         {"a": v3([(1.0, 0.71, 0.29), (0.95, 0.64, 0.54), (0.04, 0.04, 0.04), (0.56, 0.57, 0.58), (1, 1, 1)]),
          "t": f1(F_COS)}, lambda a, t: L.litFresnelSchlick3(a, t)),
        ("litF0FromIor", "vec3(litF0FromIor(t), 0.0, 0.0)", {"t": f1([1.0, 1.33, 1.5, 2.42, 0.6667])},
         lambda t: [L.litF0FromIor(t), 0.0, 0.0]),
        ("litRim", "vec3(litRim(t, u), 0.0, 0.0)", {"t": f1([0.5, 0.5, 0.0, 1.0, -0.3]), "u": f1([1.0, 0.2, 3.0, 2.0, 4.0])},
         lambda t, u: [L.litRim(t, u), 0.0, 0.0]),
        ("litInverseSquare", "vec3(litInverseSquare(t, u), 0.0, 0.0)",
         {"t": f1([0.0, 0.5, 2.0, 3.9, 6.0]), "u": f1([4.0] * 5)},
         lambda t, u: [L.litInverseSquare(t, u), 0.0, 0.0]),
        ("litRefractTIR dir", "probeRefractDir(a, b, t)",
         {"a": v3(incid), "b": v3([(0.0, 1.0, 0.0)] * 4), "t": f1([1.0 / 1.5, 1.5, 1.5, 1.33])},
         lambda a, b, t: L.litRefractTIR(a, b, t)[1]),
        ("litRefractTIR ok", "vec3(probeRefractOk(a, b, t), 0.0, 0.0)",
         {"a": v3(incid), "b": v3([(0.0, 1.0, 0.0)] * 4), "t": f1([1.0 / 1.5, 1.5, 1.5, 1.33])},
         lambda a, b, t: [1.0 if L.litRefractTIR(a, b, t)[0] else 0.0, 0.0, 0.0]),
        ("litSigmaFromColour", "litSigmaFromColour(a, t)",
         {"a": v3([(0.8, 0.35, 0.1), (1.0, 1.0, 1.0), (0.5, 0.25, 0.125)]), "t": f1([0.5, 1.0, 2.0])},
         lambda a, t: L.litSigmaFromColour(a, t)),
        ("glowAccum", "glowAccum(a, b, t, u)",
         {"a": v3([(0.1, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 2.0, 3.0)]), "b": v3([(1.0, 0.5, 0.25)] * 3),
          "t": f1([0.5, 0.0, -1.0]), "u": f1([0.01, 0.02, 0.05])}, lambda a, b, t, u: L.glowAccum(a, b, t, u)),
        ("glowEmitStep", "vec3(glowEmitStep(t, u, 2.5), 0.0, 0.0)", {"t": f1([0.3, 1.0, 0.0]), "u": f1([0.1, 0.02, 1.0])},
         lambda t, u: [L.glowEmitStep(t, u, 2.5), 0.0, 0.0]),
        ("glowExp", "vec3(glowExp(t, u), 0.0, 0.0)", {"t": f1([0.0, 0.1, 1.0, -0.5]), "u": f1([3.0, 8.0, 2.0, 1.0])},
         lambda t, u: [L.glowExp(t, u), 0.0, 0.0]),
        ("glowLorentz", "vec3(glowLorentz(t, u), 0.0, 0.0)", {"t": f1([0.0, 0.1, 1.0, -0.05]), "u": f1([0.01] * 4)},
         lambda t, u: [L.glowLorentz(t, u), 0.0, 0.0]),
        ("glowTwoGauss", "vec3(glowTwoGauss(t, vec4(24.0, 1.0, 3.0, 0.18)), glowTwoGauss(t, vec4(38.0, 0.78, 5.0, "
         "0.12)), 0.0)", {"t": f1([0.0, 0.1, 0.3, -0.6])},
         lambda t: [L.glowTwoGauss(t, [24.0, 1.0, 3.0, 0.18]), L.glowTwoGauss(t, [38.0, 0.78, 5.0, 0.12]), 0.0]),
        ("glowHotCore", "glowHotCore(a, t)", {"a": v3([(1.0, 0.3, 0.05), (0.1, 0.4, 1.0), (0.2, 1.0, 0.1)]),
                                               "t": f1([0.2, 1.0, 4.0])}, lambda a, t: L.glowHotCore(a, t)),
        ("glowStepCount", "vec3(glowStepCount(t, 64.0, u), 0.0, 0.0)",
         {"t": f1([0.0, 16.0, 40.0, 80.0]), "u": f1([2.0, 1.0, 3.0, 2.0])},
         lambda t, u: [L.glowStepCount(t, 64.0, u), 0.0, 0.0]),
        ("litFloorPool", "litFloorPool(a, vec3(0.2, -1.0, -0.1), t, vec3(0.6, 0.5, 0.4))",
         {"a": v3([(0.2, -1.0, -0.1), (1.0, -1.0, 0.5), (-0.5, 2.0, 0.0)]), "t": f1([0.8, 1.2, 0.5])},
         lambda a, t: L.litFloorPool(a, [0.2, -1.0, -0.1], t, [0.6, 0.5, 0.4])),
        ("litStudioEnv", "litStudioEnv(a, t, probeStudio())",
         {"a": v3([tuple(sd.keyDir), tuple(sd.fillDir), (0.0, -1.0, 0.0), tuple(unit([0.3, 0.05, 1.0])),
                   tuple(unit([0.0, 1.0, 0.1])), tuple(unit([-0.7, 0.6, 0.3])), tuple(-sd.keyDir),
                   tuple(-sd.fillDir), tuple(sd.keyDir)]),
          "t": f1([0.0, 0.3, 0.0, 0.6, 1.0, 0.15, 0.0, 0.5, 0.7])},     # opposite each box: no speck
         lambda a, t: L.litStudioEnv(a, t, sd)),
        ("rigStudio", "rigStudio(LitSurface(a, b, t, vec3(0.03, 0.01, 0.0)), c, normalize(vec3(0.2, 0.3, 1.0)), u, "
         "probeStudio())",
         {"a": v3([(0.5, 0.4, 0.3), (0.0, 0.0, 0.0), (0.03, 0.03, 0.03), (0.18, 0.18, 0.18)]),
          "b": v3([(0.04, 0.04, 0.04), (1.0, 0.71, 0.29), (0.04, 0.04, 0.04), (0.0, 0.0, 0.0)]),
          "c": v3([tuple(unit(v)) for v in [(0.2, 0.9, 0.3), (0.5, 0.2, 0.8), (-0.4, 0.6, 0.7), (0.0, -1.0, 0.1)]]),
          "t": f1([0.25, 0.04, 0.01, 0.6]), "u": f1([1.0, 0.7, 0.4, 0.9])},
         lambda a, b, c, t, u: L.rigStudio(surf(a, b, t), c, view, u, sd)),
        ("visSoftShadow", "vec3(visSoftShadow(a, b, vec2(0.02, 6.0), t, 48), 0.0, 0.0)",
         {"a": v3([(0.0, 0.0, 0.0), (0.45, 0.0, 0.1), (2.5, 0.0, 0.0), (0.0, 1.1, 0.0), (0.8, 0.0, -0.2),
                   (2.5, 0.0, 0.0), (2.5, 0.0, 0.0), (2.5, 0.0, 0.0)]),
          "b": v3([tuple(UP), tuple(UP), tuple(UP), tuple(UP), tuple(unit([-0.6, 1.0, 0.2])),
                   tuple(toward_elevation(10)), tuple(toward_elevation(15)), tuple(toward_elevation(20))]),
          "t": f1([0.05, 0.2, 0.2, 0.1, 0.15, 0.02, 0.2, 0.02])},       # the last three: an open floor, a low light
         lambda a, b, t: [L.visSoftShadow(scene, a, b, (0.02, 6.0), t, 48), 0.0, 0.0]),
        ("visAO", "vec3(visAO(a, b, t, 0.8), 0.0, 0.0)",
         {"a": v3(ao_points), "b": v3([tuple(UP), tuple(UP), tuple(UP), (0.0, -1.0, 0.0)]), "t": f1([0.4] * 4)},
         lambda a, b, t: [L.visAO(scene, a, b, t, 0.8), 0.0, 0.0]),
    ]
    return groups


DEFAULT_TOL = 1e-4          # float32 on SwiftShader against float64, relative to max(1, |value|)
TOLERANCE = {"litStudioEnv": 1e-3, "rigStudio": 1e-3, "visSoftShadow": 3e-3, "visAO": 1e-3, "litBlinnPhong": 3e-4,
             "glowHotCore": 2e-4}
PROBE_COLS = 8              # cases per row; each case is 6 pixels (3 channels x 2 halves of 32 bits)


def _glsl_float(x: float) -> str:
    return repr(float(x)) if math.isfinite(x) else "0.0"


def _glsl_value(kind: str, v) -> str:
    if kind == "float":
        return _glsl_float(v)
    return "vec3(" + ", ".join(_glsl_float(c) for c in v) + ")"


def _studio_glsl(s) -> str:
    """The twin's studio as a GLSL function, written from the twin's own values (one source for the probe)."""
    v3 = lambda v: "vec3(" + ", ".join(_glsl_float(c) for c in v) + ")"      # noqa: E731
    parts = [v3(s.keyDir), v3(s.keyCol), v3(s.fillDir), v3(s.fillCol),
             "vec2(" + ", ".join(_glsl_float(c) for c in s.boxSize) + ")", _glsl_float(s.rimBright),
             v3(s.skyCol), v3(s.horizonCol), v3(s.floorCol), _glsl_float(s.floorDrop), _glsl_float(s.poolRadius),
             _glsl_float(s.keyWrap)]
    return "StudioParams probeStudio() {\n    return StudioParams(" + ", ".join(parts) + ");\n}\n"


def _probe_card(groups):
    decls, branches, n = [], [], 0
    for gi, (label, expr, args, _) in enumerate(groups):
        count = max(len(v) for _, v in args.values())
        local = []
        for arg, (kind, vals) in args.items():
            vals = list(vals) + [vals[-1]] * (count - len(vals))
            decls.append(f"const {kind} PROBE_G{gi}_{arg.upper()}[{count}] = {kind}[{count}]("
                         + ", ".join(_glsl_value(kind, v) for v in vals) + ");")
            local.append(f"{kind} {arg} = PROBE_G{gi}_{arg.upper()}[i];")
        branches.append(f"    if (i < {count}) {{ {' '.join(local)} return {expr}; }}  // {label}\n    i -= {count};")
        n += count
    rows = (n + PROBE_COLS - 1) // PROBE_COLS
    header = {"card": "light-twin-probe", "uses": sorted(MODULES), "t": [0], "size": [PROBE_COLS * 6, rows],
              "note": "TEST PROBE (tests/test_glsl_twins_light.py): float32 bits of every case, 16 bits per pixel."}
    body = "\n".join(decls) + "\n" + SCENE_GLSL + "\n" + _studio_glsl(L.studio_default()) + \
        "\nvec3 probeCase(int i) {\n" + "\n".join(branches) + \
        "\n    return vec3(-7.0);   // padding past the last case: never decoded\n}\n\n" + """
void mainImage(out vec4 probeOut, in vec2 probeAt) {
    ivec2 cell = ivec2(probeAt);
    int caseIndex = cell.y * """ + str(PROBE_COLS) + """ + cell.x / 6;
    int slot = cell.x - (cell.x / 6) * 6;
    vec3 v = probeCase(caseIndex);
    float f = slot < 2 ? v.x : (slot < 4 ? v.y : v.z);
    uint bits = floatBitsToUint(f);
    uint half16 = (slot - (slot / 2) * 2 == 0) ? (bits >> 16u) : (bits & 65535u);
    probeOut = vec4(float(half16 >> 8u) / 255.0, float(half16 & 255u) / 255.0, 0.0, 1.0);
}
"""
    return "//! " + json.dumps(header) + "\n// Apache-2.0, Akashic Aurora. Generated by the test; never tracked.\n" + body, n


def _decode(png: Path, n: int) -> np.ndarray:
    from PIL import Image
    with Image.open(png) as im:
        px = np.asarray(im.convert("RGB"), dtype=np.uint32)
    px = px[::-1]                                       # PNG row 0 is the top; fragment row 0 is the bottom
    out = np.zeros((n, 3), dtype=np.float32)
    for i in range(n):
        y, x0 = divmod(i, PROBE_COLS)
        for ch in range(3):
            hi = px[y, x0 * 6 + 2 * ch]
            lo = px[y, x0 * 6 + 2 * ch + 1]
            bits = (((hi[0] << 8) | hi[1]) << 16) | ((lo[0] << 8) | lo[1])
            out[i, ch] = np.array([bits], dtype=np.uint32).view(np.float32)[0]
    return out


@pytest.fixture(scope="module")
def gpu(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node is not on PATH (the headless driver)")
    from arsenal.shaders import cards as K
    groups = _groups()
    text, n = _probe_card(groups)
    cards_dir = tmp_path_factory.mktemp("probe_cards")
    (cards_dir / "light-twin-probe.card").write_text(text, encoding="utf-8", newline="\n")
    out = tmp_path_factory.mktemp("probe_out")
    report = K.render_cards(["light-twin-probe"], cards_dir=cards_dir, out_root=out, allow_tracked=True,
                            lock_wait_min=5, quiet=True)
    driver = report["driver"]
    if driver.get("error") and "lock" in str(driver["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {driver['error']}")
    assert not driver.get("refused"), driver["refused"]
    row = report["cards"][0]
    assert row.get("compile_ok") is True, row
    receipt = json.loads(Path(row["receipt"]).read_text(encoding="utf-8"))
    png = Path(receipt["card"]["frames"][0]["png"])
    return groups, _decode(png, n)


@pytest.mark.slow
def test_glsl_light_modules_agree_with_their_twins_on_swiftshader(gpu):
    groups, got = gpu
    i, bad = 0, []
    for label, _expr, args, twin in groups:
        count = max(len(v) for _, v in args.values())
        for k in range(count):
            pick = {arg: vals[min(k, len(vals) - 1)] for arg, (kind, vals) in args.items()}
            call = {arg: (_lin(v) if args[arg][0] == "vec3" else float(v)) for arg, v in pick.items()}
            want = np.asarray(twin(**call), dtype=float).reshape(3)
            tol = TOLERANCE.get(label, DEFAULT_TOL) * np.maximum(1.0, np.abs(want))
            if not (np.all(np.isfinite(got[i])) and np.all(np.abs(got[i] - want) <= tol)):
                bad.append(f"{label}[{k}] {pick}: glsl {got[i].tolist()} twin {want.tolist()}")
            i += 1
    assert not bad, "\n".join(bad)
