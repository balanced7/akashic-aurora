"""Pins for the volume-atmos family of the house GLSL library (shader school batch B, 2026-10-13), written before the
modules: volume/integrate.glsl, volume/phase.glsl, volume/density.glsl, volume/march.glsl, atmos/fog.glsl,
atmos/aurora.glsl and atmos/sky.glsl, with their CPU twins (arsenal/shaders/twins/volume.py and atmos.py) and their
cards (arsenal/web/glsl/cards/<module>.card). envBreath, which the aurora band also needs, was built in batch A
(motion/envelope.glsl); it is checked here only for being where the atlas puts it.

WHAT THIS FAMILY IS. Light passing THROUGH stuff: fog, cloud, aurora, the sky. One law sits under all of it,
Beer-Lambert (the fraction of light that survives a distance d through a medium of extinction sigma is exp(-sigma d)),
and one accounting rule makes a march honest: integrate each step's light exactly across the step, so the picture does
not depend on how many steps were taken (Hillaire 2015; research/reviewed/shader-school-2026-10-13/volumes-atmosphere.md
section 1.4). Hardware picture: a chain of neutral-density filters, each with a faint lamp inside; optical depth adds
along the chain like decibels through a signal chain, while the gains multiply.

WHY THESE PINS. Two kinds, as in batch A:
  - MODULE pins: every planned function is in its planned file with the atlas's signature (one addition, reported: a
    vec3 overload of volOpacityFactor, used by the per-channel steps), the header carries the house fields, lint is
    clean, every module composes, each card builds, and the family REUSES the house instead of re-declaring it (PI from
    core-const, the Beer law from volTransmittance, the 1D noise from noise-value);
  - TWIN pins: the promises in each contract measured on the CPU against the mathematics: step-count independence to
    twelve digits, a phase function that integrates to one with mean cosine g, an aurora profile that peaks at exactly
    one and decays by e per scale height, emission-line colours that follow the CIE 1931 observer, a sky that is exactly
    the zenith colour overhead. The slow test at the bottom renders a parity card on SwiftShader and compares the GLSL
    with the twin pixel for pixel.

Apache-2.0, Akashic Aurora. Written fresh for the house; no corpus code.
"""
from __future__ import annotations

import json
import math
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

from arsenal.shaders import cards as K
from arsenal.shaders import modules as M

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "arsenal" / "web" / "glsl"
ATLAS = REPO / "arsenal" / "shaders" / "atlas.json"

# file (under arsenal/web/glsl/) -> (module name, atlas category, twin file). The atlas plans files and functions.
FAMILY = {
    "volume/integrate.glsl": ("volume-integrate", "G1", "arsenal/shaders/twins/volume.py"),
    "volume/phase.glsl": ("volume-phase", "G2", "arsenal/shaders/twins/volume.py"),
    "volume/density.glsl": ("volume-density", "G4", "arsenal/shaders/twins/volume.py"),
    "volume/march.glsl": ("volume-march", "G5", "arsenal/shaders/twins/volume.py"),
    "atmos/fog.glsl": ("atmos-fog", "G7", "arsenal/shaders/twins/atmos.py"),
    "atmos/aurora.glsl": ("atmos-aurora", "G8", "arsenal/shaders/twins/atmos.py"),
    "atmos/sky.glsl": ("atmos-sky", "G6", "arsenal/shaders/twins/atmos.py"),
}
NAMES = [v[0] for v in FAMILY.values()]

# Every planned P0 function's return type and parameter types, from the atlas signatures (atlas.json parts G1-G8).
# One addition: vec3 volOpacityFactor(vec3 x), the per-channel form the steps use (like u01's overloads in hash-pcg).
SIGNATURES = {
    "volTransmittance": [("float", ["float", "float"])],
    "volTransmittance3": [("vec3", ["vec3", "float"])],
    "volOpacityFactor": [("float", ["float"]), ("vec3", ["vec3"])],
    "volAccumInit": [("VolAccum", [])],
    "volStepScatter": [("void", ["inout VolAccum", "vec3", "vec3", "vec3", "float"])],
    "volStepEmit": [("void", ["inout VolAccum", "vec3", "vec3", "float"])],
    "volSaturated": [("bool", ["VolAccum", "float"])],
    "volResolve": [("vec3", ["VolAccum", "vec3"])],
    "phaseIso": [("float", [])],
    "phaseHG": [("float", ["float", "float"])],
    "densFromSDF": [("float", ["float", "float"])],
    "marchStepPoly": [("float", ["int", "float", "float", "float"])],
    "volLightOneTap": [("float", ["vec3", "vec3", "float", "float"])],
    "fogExp": [("vec3", ["vec3", "vec3", "float", "float"])],
    "auroraProfile": [("float", ["float", "float", "float"])],
    "auroraLineColor": [("vec3", ["float", "float"])],
    "auroraRays": [("float", ["float", "float", "uint"])],
    "skyGradient": [("vec3", ["vec3", "vec3", "vec3", "vec3", "vec3"])],
}

# The house parts each module must reuse rather than re-declare (module -> modules it must depend on).
REUSES = {
    "volume-phase": {"core-const"},                     # PI
    "volume-march": {"volume-integrate"},              # the Beer law, volTransmittance
    "atmos-fog": {"volume-integrate"},                 # the same law: fog is transmittance toward a colour
    "atmos-aurora": {"noise-value", "hash-pcg"},       # rays are 1D value noise
}


# --------------------------------------------------------------------------------------------- the modules themselves
def _atlas():
    return json.loads(ATLAS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def library():
    return M.load_library(strict=False)


def _module(lib, file):
    name = FAMILY[file][0]
    assert name in lib.modules, f"no module named {name} (expected in arsenal/web/glsl/{file}); " \
                                f"quarantined: {[p for p in lib.problems if file in p['path'].replace(chr(92), '/')]}"
    m = lib.modules[name]
    assert Path(m.path).resolve() == (LIB / file).resolve(), f"{name} lives in {m.path}, not {file}"
    return m


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_every_planned_batch_b_part_is_in_its_planned_file(library, file):
    planned = [row for row in _atlas()["manifest"] if row["file"] == file and row["batch"] == "B"]
    assert planned, f"the atlas plans no batch-B parts in {file}"
    m = _module(library, file)
    missing = sorted(set(planned[0]["functions"]) - set(m.provides))
    assert not missing, f"{file} lacks the planned {missing}"


def test_envbreath_is_where_the_atlas_puts_it(library):
    """The aurora band needs envBreath (ruling b-promote-envBreath); batch A built it in motion/envelope.glsl."""
    row = next(r for r in _atlas()["manifest"] if "envBreath" in r["functions"])
    assert row["file"] == "motion/envelope.glsl"
    m = library.modules["motion-envelope"]
    assert "envBreath" in m.functions and Path(m.path).resolve() == (LIB / row["file"]).resolve()


def _definitions(m):
    out = {}
    for d in M.DEFINITION_RE.finditer(M.strip_comments(m.body)):
        params = []
        for raw in d.group(3).split(","):
            words = [w for w in raw.split() if w not in ("in", "const", "highp")]
            if words:
                params.append(" ".join(words[:-1]))      # drop the parameter's name, keep out/inout and the type
        out.setdefault(d.group(2), []).append((d.group(1), params))
    return out


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_signatures_are_exactly_the_atlas_signatures(library, file):
    m = _module(library, file)
    defs = _definitions(m)
    for fn in m.functions:
        assert fn in SIGNATURES, f"{file} defines {fn}(), which the atlas does not plan (a private helper could " \
                                 "clash with a later family's name; keep the module to its planned parts)"
        assert sorted(defs[fn]) == sorted(SIGNATURES[fn]), f"{fn}: {defs[fn]} != planned {SIGNATURES[fn]}"


def test_the_accumulator_is_a_struct_of_light_and_transmittance(library):
    m = _module(library, "volume/integrate.glsl")
    assert m.structs == ("VolAccum",)
    body = M.strip_comments(m.body)
    fields = re.search(r"struct\s+VolAccum\s*\{([^}]*)\}", body).group(1)
    assert re.sub(r"\s+", " ", fields).strip() == "vec3 L; vec3 T;"


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_headers_carry_every_library_field(library, file):
    m = _module(library, file)
    h = m.header
    name, cat, twin = FAMILY[file]
    parts = [p for p in _atlas()["parts"] if p.get("module") == file]
    assert h["cat"] == cat and h["family"] == "G"
    assert h["kind"] == "helper" and re.fullmatch(r"\d+\.\d+\.\d+", h["version"])
    assert h["license"] == "Apache-2.0"
    assert isinstance(h["credits"], list) and h["credits"] and all("http" in c for c in h["credits"]), \
        "credits name who taught the technique, each with a link"
    assert h["cost"]["class"] in ("C0", "C1", "C2", "C3", "C4") and h["cost"]["tex"] == 0 and h["cost"]["loop"]
    assert h["contract"] and h["note"] and h["status"] == "P0"
    assert h["targets"]["glsl"] == "300es"
    assert (LIB / "cards" / h["card"]).is_file() and h["card"] == f"{m.name}.card"
    assert h["twin"].split(":")[0] == twin and (REPO / twin).is_file(), f"the twin {twin} does not exist"
    p0 = [p for p in parts if p["status"] == "P0"]
    assert sorted(h["exemplars"]) == sorted({e for p in p0 for e in p["exemplars"]})
    assert h["learn"] and set(h["learn"]) <= {x for p in parts for x in p["learn"]}
    assert 10 <= h["order"] <= 30


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_each_module_composes_and_lints_clean(library, file):
    m = _module(library, file)
    for target in ("toy", "webgl2", "three-r186"):
        text = library.compose([m.name], target=target)
        assert m.name in text.splitlines()[0]
    assert M.lint(m, library_module=True, library=library) == []
    assert ("uint" in m.target_needs) == (m.name == "atmos-aurora"), "only the aurora takes a uint seed"


def test_the_family_reuses_the_house_instead_of_redeclaring_it(library):
    for name, needed in REUSES.items():
        deps = set(library.resolve([name]))
        assert needed <= deps, f"{name} should reuse {sorted(needed - deps)}"
    for file in FAMILY:
        m = _module(library, file)
        assert not ({"PI", "TAU", "PHI"} & set(m.consts)), f"{file} re-declares a core constant"
    code = M.strip_comments(_module(library, "atmos/fog.glsl").body)
    assert "volTransmittance" in code and "exp(" not in code, "fog is Beer's law: call it, do not write it again"


def test_the_one_tap_light_declares_its_density_hook(library):
    m = _module(library, "volume/march.glsl")
    assert m.hooks == ("float densityAt(vec3 p)",)
    assert m.header["cost"].get("hooks") == 1
    text = library.compose([m.name], target="toy")
    assert text.count("float densityAt(vec3 p);") == 1
    assert text.index("float densityAt(vec3 p);") < text.index("float volLightOneTap(")


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_each_module_has_a_card_that_builds(library, file):
    m = _module(library, file)
    card = K.load_card(m.name)
    assert m.name in card.uses and card.note
    built = K.build_card(card, library=library)
    assert m.name in built["card"]["modules"]


# --------------------------------------------------------------------------------------------------------- the twins
# Imported inside each test, so a missing twin fails its own pins and the module pins above still report.
def _volume():
    from arsenal.shaders.twins import volume
    return volume


def _atmos():
    from arsenal.shaders.twins import atmos
    return atmos


# ---- integration (volume/integrate.glsl)
def test_beer_lambert_transmittances_multiply_and_one_mean_free_path_passes_one_over_e():
    v = _volume()
    assert v.volTransmittance(0.0, 5.0) == 1.0
    assert abs(v.volTransmittance(2.0, 0.5) - math.exp(-1.0)) < 1e-15
    for a, b in ((0.3, 1.7), (2.0, 0.01), (0.0, 4.0)):
        assert abs(v.volTransmittance(1.3, a + b) - v.volTransmittance(1.3, a) * v.volTransmittance(1.3, b)) < 1e-15
    t3 = v.volTransmittance3(np.array([0.5, 1.0, 2.0]), 2.0)
    assert np.allclose(t3, np.exp(-np.array([1.0, 2.0, 4.0])), rtol=0, atol=1e-15)


def test_the_opacity_factor_is_stable_through_zero_and_matches_expm1():
    v = _volume()
    xs = np.concatenate([np.linspace(0.0, 0.05, 2001), np.geomspace(1e-12, 60.0, 4001)])
    ref = np.array([1.0 if x == 0 else -math.expm1(-x) / x for x in xs])
    got = v.volOpacityFactor(xs)
    assert np.max(np.abs(got - ref) / ref) < 1e-9
    assert v.volOpacityFactor(0.0) == 1.0 and np.all(np.diff(v.volOpacityFactor(np.sort(xs))) <= 0)
    vec = v.volOpacityFactor(np.array([0.0, 0.5, 3.0]))
    assert vec.shape == (3,) and abs(vec[1] - (1 - math.exp(-0.5)) / 0.5) < 1e-15


def test_the_opacity_factor_series_is_what_keeps_float32_honest():
    """Why the series: in 32-bit floats (1 - e^-x)/x cancels catastrophically for small x (at x = 1e-6 it is off by
    several per cent; at 1e-8 it is 0), while the module's branch keeps every x to a few millionths."""
    v = _volume()
    xs = np.geomspace(1e-9, 30.0, 3000).astype(np.float32)
    ref = -np.expm1(-xs.astype(np.float64)) / xs.astype(np.float64)
    naive = ((np.float32(1.0) - np.exp(-xs)) / xs).astype(np.float64)
    house = v.volOpacityFactor32(xs).astype(np.float64)
    assert np.max(np.abs(naive - ref) / ref) > 0.05
    assert np.max(np.abs(house - ref) / ref) < 2e-5


def _slab(v, steps, depth_total, albedo, lin, length=1.0):
    a = v.volAccumInit()
    sigma_t = np.array(depth_total, dtype=np.float64) / length
    dt = length / steps
    for _ in range(steps):
        v.volStepScatter(a, albedo * sigma_t, sigma_t, lin, dt)
    return a


def test_a_slab_is_equally_bright_at_any_step_count_and_equals_the_exact_integral():
    """The contract's heart: a quality tier changes cost, not exposure. With constant coefficients the exact segment
    integral telescopes, so one step and a thousand give the same light to twelve digits: rho Lin (1 - e^-tau)."""
    v = _volume()
    depth = np.array([0.2, 1.0, 3.0])
    albedo, lin = np.array([0.9, 0.8, 0.7]), np.array([1.0, 0.9, 0.6])
    exact = albedo * lin * (1.0 - np.exp(-depth))
    for steps in (1, 2, 7, 64, 1000):
        a = _slab(v, steps, depth, albedo, lin)
        assert np.allclose(a.L, exact, rtol=0, atol=1e-12), steps
        assert np.allclose(a.T, np.exp(-depth), rtol=0, atol=1e-12), steps


def test_the_naive_order_brightens_with_fewer_steps_by_the_reports_numbers():
    """Light first, then transmittance (what most shaders and the house light bed do) overshoots by
    x / (1 - e^-x) per step: 5 % at x = 0.1, 27 % at 0.5, 35 % at 0.64 (the light bed's dense slice), 131 % at 2."""
    for x, too_bright in ((0.1, 0.05), (0.5, 0.27), (0.64, 0.35), (2.0, 1.31)):
        assert abs(x / -math.expm1(-x) - 1.0 - too_bright) < 0.006


def test_scattering_never_creates_energy_in_any_medium():
    """For albedo <= 1 and unit light, the gathered light never exceeds what the medium removed, 1 - T, whatever the
    density does from step to step and however coarse the steps are."""
    v = _volume()
    rng = np.random.default_rng(13)
    for _ in range(200):
        steps = int(rng.integers(1, 40))
        a = v.volAccumInit()
        albedo = rng.uniform(0.0, 1.0, 3)
        for _ in range(steps):
            sigma_t = rng.exponential(2.0, 3) * rng.choice([0.0, 1.0, 30.0])
            v.volStepScatter(a, albedo * sigma_t, sigma_t, np.ones(3), float(rng.uniform(0.0, 0.5)))
        assert np.all(a.L <= (1.0 - a.T) * albedo.max() + 1e-12) and np.all((a.T >= 0) & (a.T <= 1))


def test_a_smooth_medium_converges_as_the_steps_shrink():
    v = _volume()

    def run(steps):
        a = v.volAccumInit()
        dt = 2.0 / steps
        for i in range(steps):
            s = 1.5 * (1.0 + math.sin(3.0 * (i + 0.5) * dt))          # density sampled mid-step
            v.volStepScatter(a, np.full(3, 0.8 * s), np.full(3, s), np.ones(3), dt)
        return a.L[0]
    coarse, fine, finer = run(8), run(256), run(4096)
    assert abs(fine - finer) < 1e-4 and abs(coarse - finer) < 0.03


def test_emission_sums_plainly_when_thin_and_saturates_when_thick():
    v = _volume()
    eps = np.array([0.3, 0.6, 0.1])
    for steps in (1, 5, 50):
        a = v.volAccumInit()
        for _ in range(steps):
            v.volStepEmit(a, eps, np.zeros(3), 2.0 / steps)          # an aurora: no absorption at all
        assert np.allclose(a.L, 2.0 * eps, atol=1e-14) and np.all(a.T == 1.0)
        b = v.volAccumInit()
        sigma = np.array([0.5, 1.0, 4.0])
        for _ in range(steps):
            v.volStepEmit(b, eps, sigma, 2.0 / steps)
        assert np.allclose(b.L, eps * (1 - np.exp(-2.0 * sigma)) / sigma, atol=1e-12)


def test_saturation_resolve_and_the_starting_state():
    v = _volume()
    a = v.volAccumInit()
    assert np.all(a.L == 0.0) and np.all(a.T == 1.0) and not v.volSaturated(a, 0.01)
    a.T = np.array([0.005, 0.009, 0.02])
    assert not v.volSaturated(a, 0.01) and v.volSaturated(a, 0.03)
    a.L = np.array([0.1, 0.2, 0.3])
    assert np.allclose(v.volResolve(a, np.array([1.0, 2.0, 3.0])), [0.105, 0.218, 0.36])


# ---- phase functions (volume/phase.glsl)
def _sphere_mean(f):
    """(integral of f over the sphere, its mean cosine) for a function of mu: 2 pi times a fine Simpson integral."""
    mu = np.linspace(-1.0, 1.0, 400001)
    w = np.ones_like(mu)
    w[1:-1:2], w[2:-1:2] = 4.0, 2.0
    h = (mu[1] - mu[0]) / 3.0
    p = f(mu)
    return 2 * math.pi * h * np.sum(w * p), 2 * math.pi * h * np.sum(w * p * mu)


def test_the_isotropic_phase_is_one_over_four_pi():
    v = _volume()
    assert abs(v.phaseIso() - 1.0 / (4.0 * math.pi)) < 1e-15


@pytest.mark.parametrize("g", [-0.9, -0.5, 0.0, 0.3, 0.76, 0.9])
def test_henyey_greenstein_integrates_to_one_with_mean_cosine_g(g):
    v = _volume()
    total, mean = _sphere_mean(lambda mu: v.phaseHG(mu, g))
    assert abs(total - 1.0) < 1e-6 and abs(mean - g) < 1e-6


def test_henyey_greenstein_peaks_toward_the_light_by_the_textbook_values():
    """House sign: mu = dot(viewRayDir, dirToLight), so positive g glows around the light you look at. Forward peak
    (1 + g) / (4 pi (1 - g)^2): about 45 times isotropic at g = 0.8; the back is about 16 times darker."""
    v = _volume()
    for g in (0.3, 0.8, 0.95):
        assert abs(v.phaseHG(1.0, g) - (1 + g) / (4 * math.pi * (1 - g) ** 2)) < 1e-9 * v.phaseHG(1.0, g)
        assert abs(v.phaseHG(-1.0, g) - (1 - g) / (4 * math.pi * (1 + g) ** 2)) < 1e-12
    assert 44.0 < v.phaseHG(1.0, 0.8) / v.phaseIso() < 46.0
    assert 15.0 < v.phaseIso() / v.phaseHG(-1.0, 0.8) < 17.0
    mu = np.linspace(-1, 1, 101)
    assert np.allclose(v.phaseHG(mu, 0.0), v.phaseIso(), rtol=0, atol=1e-15)
    assert np.allclose(v.phaseHG(mu, -0.6), v.phaseHG(-mu, 0.6), rtol=1e-12, atol=0)


def test_henyey_greenstein_stays_finite_at_the_edges_in_float32():
    """The denominator is written as (1 - g mu)^2 + g^2 (1 - mu^2), a sum of squares, so 32-bit rounding cannot make it
    negative; 1 + g^2 - 2 g mu, the textbook spelling, can (and pow of a negative is NaN)."""
    v = _volume()
    g = np.float32(np.linspace(0.99, 0.99999, 200))[:, None]
    mu = np.float32(np.linspace(0.9999, 1.0, 200))[None, :]
    textbook = np.float32(1.0) + g * g - np.float32(2.0) * g * mu
    assert textbook.min() <= 0.0
    house = v.phaseHG32(mu, g)
    assert np.all(np.isfinite(house)) and house.min() > 0.0
    edges = v.phaseHG(np.array([-1.0, 1.0, 1.5, -2.0]), np.array([1.0, 1.0, -1.0, 0.5]))
    assert np.all(np.isfinite(edges)) and np.all(edges > 0)


# ---- density (volume/density.glsl)
def test_density_from_a_distance_field_ramps_inward_over_the_softness():
    v = _volume()
    sdf = np.array([2.0, 0.0, -0.05, -0.1, -0.2, -5.0])
    assert np.allclose(v.densFromSDF(sdf, 0.2), [0.0, 0.0, 0.25, 0.5, 1.0, 1.0])
    assert np.array_equal(v.densFromSDF(np.array([0.01, -0.01]), 0.0), [0.0, 1.0])     # softness 0 is a hard edge
    xs = np.linspace(-1, 1, 1001)
    d = v.densFromSDF(xs, 0.3)
    assert np.all(np.diff(d) <= 0) and d.min() == 0.0 and d.max() == 1.0


# ---- marching (volume/march.glsl)
def test_polynomial_layers_are_dense_low_and_sparse_high():
    v = _volume()
    ys = np.array([v.marchStepPoly(i, 0.7, 0.01, 1.4) for i in range(30)])
    assert ys[0] == 0.7 and abs(ys[10] - (0.7 + 0.01 * 10 ** 1.4)) < 1e-15
    gaps = np.diff(ys)
    assert np.all(np.diff(gaps) > 0), "gaps widen with height when power > 1"
    lin = np.diff([v.marchStepPoly(i, 0.0, 0.5, 1.0) for i in range(10)])
    assert np.allclose(lin, 0.5)
    assert v.marchStepPoly(-3, 0.7, 0.01, 1.4) == 0.7


def test_the_one_tap_light_is_beer_at_the_midpoint_with_a_floor():
    v = _volume()
    p, light = np.array([0.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0])

    def ramp(q):                                    # extinction growing linearly upward: 0.5 + 2 y
        return 0.5 + 2.0 * q[..., 1]
    for dist in (0.1, 1.0, 2.5):
        tau = 0.5 * dist + dist ** 2                    # the exact optical depth of the ramp over [0, dist]
        expect = 0.15 + 0.85 * math.exp(-tau)
        assert abs(v.volLightOneTap(p, light, dist, 0.15, ramp) - expect) < 1e-12   # midpoint rule: exact on a ramp
    assert v.volLightOneTap(p, light, 1.0, 0.15, lambda q: 0.0 * q[..., 0]) == 1.0
    assert abs(v.volLightOneTap(p, light, 1.0, 0.15, lambda q: 1e4 + 0.0 * q[..., 0]) - 0.15) < 1e-12
    calls = []
    v.volLightOneTap(p, light, 1.0, 0.0, lambda q: calls.append(q) or 1.0)
    assert len(calls) == 1 and np.allclose(calls[0], [0.0, 0.5, 0.0]), "one probe, at the segment's midpoint"


# ---- fog (atmos/fog.glsl)
def test_fog_is_transmittance_toward_a_colour_and_composes_over_distance():
    at = _atmos()
    col, fog = np.array([0.9, 0.2, 0.1]), np.array([0.1, 0.3, 0.6])
    assert np.allclose(at.fogExp(col, fog, 0.0, 0.5), col)
    assert np.allclose(at.fogExp(col, fog, 1e6, 0.5), fog)
    assert np.allclose(at.fogExp(col, fog, 3.0, 0.2), col + (fog - col) * (1 - math.exp(-0.6)))
    once = at.fogExp(col, fog, 5.0, 0.3)
    twice = at.fogExp(at.fogExp(col, fog, 2.0, 0.3), fog, 3.0, 0.3)
    assert np.allclose(once, twice, atol=1e-15), "fog over a then b equals fog over a + b (Beer's law composes)"
    assert np.allclose(at.fogExp(col, fog, -4.0, 0.3), col), "a point behind the eye takes no fog"


# ---- aurora (atmos/aurora.glsl)
def test_the_aurora_profile_has_a_sharp_hem_a_unit_peak_and_an_e_folding_top():
    at = _atmos()
    edge, h = 95.0, 40.0
    alts = np.linspace(60.0, 400.0, 34001)
    prof = at.auroraProfile(alts, edge, h)
    assert np.all(prof[alts <= edge] == 0.0) and prof.min() >= 0.0
    r = at.AURORA_RISE_KM
    z_peak = r * math.log((r + h) / r)
    assert abs(at.auroraProfile(edge + z_peak, edge, h) - 1.0) < 1e-12 and prof.max() <= 1.0 + 1e-12
    assert 10.0 <= z_peak <= 20.0, "VA 7.3: the brightest emission sits 10-20 km above the hem"
    assert at.auroraProfile(edge + 3.0, edge, h) > 0.35, "the hem is sharp: a third of the peak within 3 km"
    far = edge + 150.0
    assert abs(at.auroraProfile(far + h, edge, h) / at.auroraProfile(far, edge, h) - math.exp(-1)) < 1e-6
    taller = at.auroraProfile(edge + 120.0, edge, 80.0)
    assert taller > at.auroraProfile(edge + 120.0, edge, 30.0), "a longer scale height is a taller curtain"


def peak_heights_stated_wrongly(contract: str) -> list:
    """The '(a to b km for scaleH h1 to h2)' figures in a contract that the profile's own peak formula contradicts."""
    import re
    wrong = []
    for a, b, h1, h2 in re.findall(r"\(([\d.]+) to ([\d.]+) km for scaleH ([\d.]+) to ([\d.]+)\)", contract):
        for stated, h in ((float(a), float(h1)), (float(b), float(h2))):
            peak = 6.0 * math.log((6.0 + h) / 6.0)
            if abs(stated - peak) > 0.06:
                wrong.append((stated, h, round(peak, 2)))
    return wrong


def test_the_aurora_contract_states_the_peak_height_its_formula_gives():
    # Batch-B review, defect 10: the contract said the peak sits "12 to 16 km for scaleH 40 to 60" above the hem; its
    # own formula 6 ln((6 + scaleH) / 6) gives 12.2 to 14.4 km.
    import json
    text = (LIB / "atmos" / "aurora.glsl").read_text(encoding="utf-8")
    header = json.loads(" ".join(line[3:] for line in text.splitlines() if line.startswith("//!")))
    assert "km for scaleH" in header["contract"]
    assert peak_heights_stated_wrongly(header["contract"]) == []
    assert peak_heights_stated_wrongly("(12 to 16 km for scaleH 40 to 60)") == [(12.0, 40.0, 12.22),
                                                                                 (16.0, 60.0, 14.39)]   # the old words


def _cie_line_rgb(nm):
    """A second writing of each emission line's colour: Wyman, Sloan and Shirley's analytic fit of the CIE 1931 2-degree
    observer (JCGT 2(2), 2013), the sRGB matrix of IEC 61966-2-1, negative channels clipped, brightest channel 1."""
    def g(x, mu, s1, s2):
        return math.exp(-0.5 * ((x - mu) / (s1 if x < mu else s2)) ** 2)
    xyz = (1.056 * g(nm, 599.8, 37.9, 31.0) + 0.362 * g(nm, 442.0, 16.0, 26.7) - 0.065 * g(nm, 501.1, 20.4, 26.2),
           0.821 * g(nm, 568.8, 46.9, 40.5) + 0.286 * g(nm, 530.9, 16.3, 31.1),
           1.217 * g(nm, 437.0, 11.8, 36.0) + 0.681 * g(nm, 459.0, 26.0, 13.8))
    m = ((3.2406, -1.5372, -0.4986), (-0.9689, 1.8758, 0.0415), (0.0557, -0.2040, 1.0570))
    rgb = np.array([max(sum(m[i][j] * xyz[j] for j in range(3)), 0.0) for i in range(3)])
    return rgb / rgb.max()


def test_the_line_colours_are_the_spectral_lines_seen_by_the_cie_observer():
    at = _atmos()
    assert np.allclose(at.LINE_GREEN_5577, _cie_line_rgb(557.7), atol=0.02)
    assert np.allclose(at.LINE_RED_6300, _cie_line_rgb(630.0), atol=0.02)
    fringe = _cie_line_rgb(427.8) + at.FRINGE_N2_RED_SHARE * _cie_line_rgb(670.0)
    assert np.allclose(at.LINE_FRINGE, fringe, atol=0.02)


def test_the_aurora_colours_stack_in_physical_order():
    """Green body, red top, a purple fringe low that only an energetic display shows (VA 7.1)."""
    at = _atmos()
    body = at.auroraLineColor(130.0, 0.0)
    assert np.allclose(body, at.LINE_GREEN_5577)
    top = at.auroraLineColor(300.0, 1.0)
    assert np.allclose(top, at.LINE_RED_6300)
    quiet_hem, active_hem = at.auroraLineColor(96.0, 0.0), at.auroraLineColor(96.0, 1.0)
    assert active_hem[2] > 0.5 and active_hem[0] > 0.4 and quiet_hem[2] < 0.05
    assert np.allclose(at.auroraLineColor(96.0, 0.5) - quiet_hem, 0.5 * (active_hem - quiet_hem))
    reds = [at.auroraLineColor(a, 0.0)[0] / max(at.auroraLineColor(a, 0.0)[1], 1e-9) for a in (120, 180, 220, 260)]
    assert reds == sorted(reds), "red takes over from green with height"
    assert np.all(at.auroraLineColor(np.array([80.0, 150.0, 250.0]), 0.3) >= 0.0)


def test_rays_are_sparse_bright_columns_that_drift():
    at = _atmos()
    along = np.linspace(0.0, 4000.0, 400001)            # about 4000 coarse cells: the statistics, not one seed's luck
    r = at.auroraRays(along, 3.0, 11)
    assert r.min() >= 0.0 and r.max() <= 1.0
    assert 0.12 <= r.mean() <= 0.25, r.mean()
    assert 0.4 <= np.mean(r == 0.0) <= 0.6, "about half the curtain lies between rays"
    assert 0.03 <= np.mean(r > 0.8) <= 0.1, "about one place in sixteen is a bright core"
    # continuous across (no seam between noise cells): halving the sample spacing halves the largest step
    step, double = np.max(np.abs(np.diff(r))), np.max(np.abs(np.diff(r[::2])))
    spacing = along[1] - along[0]
    assert step / spacing < 15.0 and 1.8 < double / step < 2.2, (step, double)    # a ray's edge spans >= 1/15 unit
    later = at.auroraRays(along, 3.1, 11)
    much_later = at.auroraRays(along, 300.0, 11)
    assert 0.9 < np.corrcoef(r, later)[0, 1] < 1.0, "a tenth of a second later the rays have moved a little"
    assert abs(np.corrcoef(r, much_later)[0, 1]) < 0.1 and abs(np.corrcoef(r, at.auroraRays(along, 3.0, 12))[0, 1]) < 0.1


# ---- sky (atmos/sky.glsl)
def _dir(az, el):
    return np.stack([np.cos(el) * np.sin(az), np.sin(el), -np.cos(el) * np.cos(az)], axis=-1)


ZENITH, HORIZON, SUNTINT = np.array([0.05, 0.12, 0.35]), np.array([0.35, 0.45, 0.6]), np.array([1.0, 0.5, 0.2])


def test_the_sky_is_the_zenith_overhead_and_the_horizon_away_from_the_sun():
    at = _atmos()
    low_sun = _dir(0.0, math.radians(-3.0))
    assert np.allclose(at.skyGradient(np.array([0.0, 1.0, 0.0]), low_sun, ZENITH, HORIZON, SUNTINT), ZENITH)
    away = at.skyGradient(_dir(math.pi, 0.0), low_sun, ZENITH, HORIZON, SUNTINT)
    toward = at.skyGradient(_dir(0.0, 0.0), low_sun, ZENITH, HORIZON, SUNTINT)
    assert np.allclose(away, HORIZON, atol=0.02)
    assert np.allclose(toward, SUNTINT, atol=0.08), "the horizon under a low sun takes the sun's tint"
    below = at.skyGradient(_dir(0.0, math.radians(-20.0)), low_sun, ZENITH, HORIZON, SUNTINT)
    assert np.allclose(below, toward), "below the horizon the sky holds its horizon colour"


def test_the_warm_band_is_wider_toward_a_low_sun_and_fades_when_the_sun_is_high():
    at = _atmos()
    low_sun, high_sun = _dir(0.0, math.radians(2.0)), _dir(0.0, math.radians(60.0))
    el = math.radians(12.0)

    def horizon_share(rd, sun):        # how far from the zenith colour, along the blue channel
        c = at.skyGradient(rd, sun, ZENITH, HORIZON, HORIZON)
        return (c[2] - ZENITH[2]) / (HORIZON[2] - ZENITH[2])
    assert horizon_share(_dir(0.0, el), low_sun) > 1.5 * horizon_share(_dir(math.pi, el), low_sun)
    warm_low = at.skyGradient(_dir(0.0, 0.0), low_sun, ZENITH, HORIZON, SUNTINT)
    warm_high = at.skyGradient(_dir(0.0, 0.0), high_sun, ZENITH, HORIZON, SUNTINT)
    assert np.linalg.norm(warm_high - HORIZON) < 0.25 * np.linalg.norm(warm_low - HORIZON)
    rng = np.random.default_rng(8)
    rd = rng.normal(size=(5000, 3))
    rd /= np.linalg.norm(rd, axis=1, keepdims=True)
    sun = rng.normal(size=(5000, 3))
    sun /= np.linalg.norm(sun, axis=1, keepdims=True)
    c = at.skyGradient(rd, sun, ZENITH, HORIZON, SUNTINT)
    lo = np.minimum(np.minimum(ZENITH, HORIZON), SUNTINT) - 1e-12
    hi = np.maximum(np.maximum(ZENITH, HORIZON), SUNTINT) + 1e-12
    assert np.all((c >= lo) & (c <= hi)), "a mix of the three colours, never outside them"


# ------------------------------------------------------------------------------------------- GPU parity (SwiftShader)
PARITY_CARD = """//! {"card": "parity-volume-atmos", "uses": ["volume-integrate", "volume-phase", "volume-density",
//!  "volume-march", "atmos-fog", "atmos-aurora", "atmos-sky"], "t": [0], "size": [320, 64],
//!  "note": "test fixture: five 64x64 panels of numbers the CPU twin recomputes; not a picture for people"}
// Apache-2.0, Akashic Aurora. A parity fixture: every pixel is a number the numpy twin recomputes.
float densityAt(vec3 p) { return 0.5 + 2.0 * p.y; }
const vec3 PARITY_UP = vec3(0.0, 1.0, 0.0);

void mainImage(out vec4 color, in vec2 pixel) {
    int panel = int(pixel.x) / 64;
    vec2 local = vec2(mod(pixel.x, 64.0), pixel.y);
    vec3 v;
    if (panel == 0) {
        float tau = floor(local.x) / 12.0;
        int steps = 1 + int(mod(floor(local.y), 32.0)) / 4;
        vec3 sigmaT = vec3(1.0, 1.2, 1.5) * tau;
        VolAccum a = volAccumInit();
        for (int slice = 0; slice < 8; ++slice) {
            if (slice >= steps) break;
            if (local.y < 32.0) {
                volStepScatter(a, vec3(0.9, 0.85, 0.8) * sigmaT, sigmaT, vec3(0.8, 0.9, 1.0), 1.0 / float(steps));
            } else {
                volStepEmit(a, vec3(0.3, 0.6, 0.2), 0.5 * sigmaT, 1.0 / float(steps));
            }
        }
        v = volResolve(a, vec3(0.2, 0.3, 0.1));
        if (local.y >= 32.0) v.b = volSaturated(a, 0.3) ? 1.0 : 0.0;
    } else if (panel == 1) {
        float mu = local.x / 32.0 - 1.0;
        float g = local.y / 32.0 - 1.0;
        float p = phaseHG(mu, g);
        v = vec3(p / (p + 1.0), 3.0 * phaseIso(), densFromSDF((local.x - 32.0) / 16.0, floor(local.y) / 64.0));
    } else if (panel == 2) {
        float alt = 80.0 + 4.0 * local.y;
        float along = local.x / 8.0;
        vec3 line = auroraLineColor(alt, floor(local.x) / 63.0);
        v = vec3(auroraProfile(alt, 95.0 + 0.2 * local.x, 30.0 + 0.5 * local.x), auroraRays(along, 1.7, 5u),
                 dot(line, vec3(0.3, 0.5, 0.2)) / 1.2);
    } else if (panel == 3) {
        float az = local.x / 64.0 * 6.283185307179586 - 3.141592653589793;
        float el = local.y / 64.0 * 1.6 - 0.1;
        vec3 rd = vec3(cos(el) * sin(az), sin(el), -cos(el) * cos(az));
        vec3 toSun = normalize(vec3(0.3, 0.06, -1.0));
        v = skyGradient(rd, toSun, vec3(0.05, 0.12, 0.35), vec3(0.35, 0.45, 0.6), vec3(1.0, 0.5, 0.2));
    } else {
        vec3 fogged = fogExp(vec3(0.9, 0.2, 0.1), vec3(0.1, 0.3, 0.6), local.x * 0.5, local.y / 64.0);
        float layer = marchStepPoly(int(floor(local.x)) - 4, 0.1, 0.002, 1.0 + floor(local.y) / 32.0);
        float lit = volLightOneTap(PARITY_UP * (local.y / 64.0), PARITY_UP, local.x / 32.0, 0.15);
        v = vec3(fogged.r, layer, lit);
    }
    color = vec4(v, 1.0);
}
"""


def _twin_parity_image():
    v, at = _volume(), _atmos()
    ys, xs = np.mgrid[0:64, 0:64].astype(np.float64)
    lx, ly = xs + 0.5, ys + 0.5                                     # gl_FragCoord: pixel centres, y up
    out = np.zeros((64, 320, 3))
    # panel 0: integration
    tau = np.floor(lx) / 12.0
    steps = 1 + (np.mod(np.floor(ly), 32.0) // 4).astype(int)
    sigma_t = np.array([1.0, 1.2, 1.5]) * tau[..., None]
    a = v.volAccumInit((64, 64))
    scatter = (ly < 32.0)[..., None]
    for i in range(8):
        dt = np.where(i < steps, 1.0 / steps, 0.0)[..., None]
        s = v.volAccumInit((64, 64))
        s.L, s.T = a.L.copy(), a.T.copy()
        v.volStepScatter(s, np.array([0.9, 0.85, 0.8]) * sigma_t, sigma_t, np.array([0.8, 0.9, 1.0]), dt)
        e = v.volAccumInit((64, 64))
        e.L, e.T = a.L.copy(), a.T.copy()
        v.volStepEmit(e, np.array([0.3, 0.6, 0.2]), 0.5 * sigma_t, dt)
        a.L, a.T = np.where(scatter, s.L, e.L), np.where(scatter, s.T, e.T)
    p0 = v.volResolve(a, np.array([0.2, 0.3, 0.1]))
    p0[..., 2] = np.where(ly >= 32.0, v.volSaturated(a, 0.3).astype(float), p0[..., 2])
    out[:, 0:64] = p0
    # panel 1: phase and density
    p = v.phaseHG(lx / 32.0 - 1.0, ly / 32.0 - 1.0)
    out[:, 64:128] = np.stack([p / (p + 1.0), np.full_like(p, 3.0 * v.phaseIso()),
                               v.densFromSDF((lx - 32.0) / 16.0, np.floor(ly) / 64.0)], -1)
    # panel 2: aurora
    alt = 80.0 + 4.0 * ly
    line = at.auroraLineColor(alt, np.floor(lx) / 63.0)
    out[:, 128:192] = np.stack([at.auroraProfile(alt, 95.0 + 0.2 * lx, 30.0 + 0.5 * lx),
                                at.auroraRays(lx / 8.0, 1.7, 5), line @ np.array([0.3, 0.5, 0.2]) / 1.2], -1)
    # panel 3: sky
    az = lx / 64.0 * 2.0 * math.pi - math.pi
    el = ly / 64.0 * 1.6 - 0.1
    sun = np.array([0.3, 0.06, -1.0]) / np.linalg.norm([0.3, 0.06, -1.0])
    out[:, 192:256] = at.skyGradient(_dir(az, el), sun, np.array([0.05, 0.12, 0.35]), np.array([0.35, 0.45, 0.6]),
                                     np.array([1.0, 0.5, 0.2]))
    # panel 4: fog, layers, the one-tap light
    fogged = at.fogExp(np.array([0.9, 0.2, 0.1]), np.array([0.1, 0.3, 0.6]), lx * 0.5, ly / 64.0)
    layer = np.vectorize(v.marchStepPoly)(np.floor(lx).astype(int) - 4, 0.1, 0.002, 1.0 + np.floor(ly) / 32.0)
    pts = np.stack([np.zeros_like(ly), ly / 64.0, np.zeros_like(ly)], -1)
    lit = v.volLightOneTap(pts, np.array([0.0, 1.0, 0.0]), lx / 32.0, 0.15, lambda q: 0.5 + 2.0 * q[..., 1])
    out[:, 256:320] = np.stack([fogged[..., 0], layer, lit], -1)
    return np.round(np.clip(out, 0, 1) * 255.0)[::-1]            # PNG rows run top down


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH (the headless driver)")
def test_the_glsl_matches_its_twin_on_swiftshader(tmp_path):
    from PIL import Image
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "parity-volume-atmos.card").write_text(PARITY_CARD, encoding="utf-8", newline="\n")
    report = K.render_cards(["parity-volume-atmos"], cards_dir=cards_dir, out_root=tmp_path / "out",
                            allow_tracked=True, lock_wait_min=5, quiet=True)
    if report["driver"].get("error") and "lock" in str(report["driver"]["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {report['driver']['error']}")
    row = report["cards"][0]
    assert row["compile_ok"] is True and row["nan_pixels"] == 0, row
    png = sorted((tmp_path / "out" / "parity-volume-atmos").glob("t0*.png"))[0]
    gpu = np.asarray(Image.open(png).convert("RGB")).astype(np.float64)
    cpu = _twin_parity_image()
    miss = np.abs(gpu - cpu)
    for k, name in enumerate(("integrate", "phase-density", "aurora", "sky", "fog-march")):
        panel = miss[:, 64 * k:64 * (k + 1)]
        assert panel.max() <= 2 and np.mean(panel > 1) < 0.002, f"{name}: max {panel.max()}"
