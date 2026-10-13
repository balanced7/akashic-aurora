"""Pins for the hash-noise family of the house GLSL library (shader school batch A, 2026-10-13).

WHAT THIS FAMILY IS. The dice and the fabric under every procedural picture the house draws: integer hashes
(hash/pcg.glsl), the sine hash kept only so old surfaces can adopt the library without a pixel moving
(legacy/hash-sine.glsl), value and gradient noise (noise/value.glsl, noise/gradient.glsl), fractal sums
(noise/fbm.glsl), domain warps (noise/warp.glsl) and the static dither masks (noise/dither-masks.glsl).

WHY A CPU TWIN. A seat that cannot see a screen still has to know the shader does what its contract says. Each GLSL
function has a numpy twin (arsenal/shaders/twins/hash.py and noise.py) with the same name and the same maths, so its
promises can be measured here without a GPU: the integer hashes bit for bit, the noises by their properties (zero on
the lattice, range, normalisation, independence of seeds). The twin is checked two ways: against an ORACLE written a
second time below in plain Python integers and floats (two independent writings of one spec catch a slip in either), and
against the GPU itself in the slow test at the bottom, which renders a parity card on SwiftShader and compares pixels.

Like a chip design team: the twin is the golden model, the oracle is the second engineer's model, and the SwiftShader
render is the silicon. All three must agree.

TEST VECTORS. Jarzynski and Olano (JCGT 2020) publish their hashes as code, not as numeric test vectors, so the
vectors pinned here come from the oracle below, an independent integer re-writing of the paper's description; the slow
parity test then proves the GLSL produces the same bits on a real (software) GPU.

ONE SEED, ONE INDEPENDENT FIELD PER KIND. Value noise, gradient noise and the 3D hash wrappers all draw from pcg3d or
pcg4d. Until 2026-10-13 they fed the seed (or the cell's z) into the same lane untouched, so they read the SAME dice:
noiseValue2(p, 0) on the lattice was exactly 2 hash31(cell, 0) - 1, and a value corner's sign was the sign of the
gradient's y at that corner (correlation -0.80 on the lattice, -0.36 over the plane; batch-A review, defect 1). Now each
kind XORs its own tag into that lane (further 32-bit words of pi's fraction, after the three the warps use), and the
pins below measure the independence with the twins and check that no two tags meet on small lanes.

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
from arsenal.shaders.twins import hash as H
from arsenal.shaders.twins import noise as N

REPO = Path(__file__).resolve().parents[1]
LIB = REPO / "arsenal" / "web" / "glsl"
ATLAS = REPO / "arsenal" / "shaders" / "atlas.json"

# file (under arsenal/web/glsl/) -> module name. The atlas plans the files and their functions; the names are ours.
FAMILY = {
    "hash/pcg.glsl": "hash-pcg",
    "legacy/hash-sine.glsl": "hash-sine",
    "noise/value.glsl": "noise-value",
    "noise/gradient.glsl": "noise-gradient",
    "noise/fbm.glsl": "noise-fbm",
    "noise/warp.glsl": "noise-warp",
    "noise/dither-masks.glsl": "dither-masks",
}

# Every planned P0 function's return type and parameter types, read from the atlas signatures (atlas.json parts).
SIGNATURES = {
    "hashU1": [("uint", ["uint"])],
    "pcg3d": [("uvec3", ["uvec3"])],
    "pcg4d": [("uvec4", ["uvec4"])],
    "u01": [("float", ["uint"]), ("vec2", ["uvec2"]), ("vec3", ["uvec3"]), ("vec4", ["uvec4"])],
    "cellU2": [("uvec2", ["vec2"])],
    "cellU3": [("uvec3", ["vec3"])],
    "hash21": [("float", ["vec2"])],
    "hash22": [("vec2", ["vec2"])],
    "hash31": [("float", ["vec3"])],
    "hash33": [("vec3", ["vec3"])],
    "hashSine21": [("float", ["vec2"])],
    "hashSine31": [("float", ["vec3"])],
    "noiseValue2": [("float", ["vec2", "uint"])],
    "noiseValue3": [("float", ["vec3", "uint"])],
    "noiseGrad2": [("float", ["vec2", "uint"])],
    "noiseGrad3": [("float", ["vec3", "uint"])],
    "gainFromHurst": [("float", ["float", "float"])],
    "fbmGrad2": [("float", ["vec2", "int", "float", "float", "uint"])],
    "fbmGrad3": [("float", ["vec3", "int", "float", "float", "uint"])],
    "warpVec2": [("vec2", ["vec2", "int", "uint"])],
    "warpFbm2": [("float", ["vec2", "float", "int", "uint"])],
    "warpNested2": [("float", ["vec2", "float", "int", "uint", "out vec2", "out vec2"])],
    "dthIgn": [("float", ["vec2"])],
    "dthR2": [("float", ["vec2"])],
    "dthTriFromUniform": [("float", ["float"])],
}

MASK = 0xFFFFFFFF


# ------------------------------------------------------------------------------------------- the oracle (second writing)
# Plain Python integers and floats, one value at a time: slow, obvious, and written apart from the numpy twin.

def o_hash_u1(x: int) -> int:
    lcg = (x * 747796405 + 2891336453) & MASK
    mixed = (((lcg >> ((lcg >> 28) + 4)) ^ lcg) * 277803737) & MASK
    return ((mixed >> 22) ^ mixed) & MASK


def o_pcg3d(v):
    x, y, z = ((c * 1664525 + 1013904223) & MASK for c in v)
    x = (x + y * z) & MASK
    y = (y + z * x) & MASK
    z = (z + x * y) & MASK
    x, y, z = x ^ (x >> 16), y ^ (y >> 16), z ^ (z >> 16)
    x = (x + y * z) & MASK
    y = (y + z * x) & MASK
    z = (z + x * y) & MASK
    return x, y, z


def o_pcg4d(v):
    x, y, z, w = ((c * 1664525 + 1013904223) & MASK for c in v)
    x = (x + y * w) & MASK
    y = (y + z * x) & MASK
    z = (z + x * y) & MASK
    w = (w + y * z) & MASK
    x, y, z, w = x ^ (x >> 16), y ^ (y >> 16), z ^ (z >> 16), w ^ (w >> 16)
    x = (x + y * w) & MASK
    y = (y + z * x) & MASK
    z = (z + x * y) & MASK
    w = (w + y * z) & MASK
    return x, y, z, w


def o_u01(x: int) -> float:
    return (x >> 8) / 16777216.0


def o_cell(c: float) -> int:
    return math.floor(c) & MASK


# Every kind of dice its own lane tag: pi's fraction in 32-bit words, continuing after the warps' three (0x243F6A88,
# 0x85A308D3, 0x13198A2E). The 2D hash wrappers already hold 0x9E3779B9 as their whole third lane.
O_TAG_VALUE2 = 0x03707344        # noiseValue2: pcg3d(cell, seed ^ tag)
O_TAG_VALUE3 = 0xA4093822        # noiseValue3: pcg4d(cell, seed ^ tag)
O_TAG_GRAD2 = 0x299F31D0         # noiseGrad2:  pcg3d(cell + corner, seed ^ tag)
O_TAG_GRAD3 = 0x082EFA98         # noiseGrad3:  pcg4d(cell + corner, seed ^ tag)
O_TAG_HASH3 = 0xEC4E6C89         # hash31 / hash33: pcg3d(cell.x, cell.y, cell.z ^ tag)
O_LANE_2D = 0x9E3779B9           # hash21 / hash22: pcg3d(cell.x, cell.y, this)


def o_hash33(x, y, z):
    return tuple(o_u01(w) for w in o_pcg3d((o_cell(x), o_cell(y), o_cell(z) ^ O_TAG_HASH3)))


def o_fade(t: float) -> float:
    return (10.0 - 15.0 * t + 6.0 * t ** 2) * t ** 3     # Perlin's quintic, expanded


def o_value2(x, y, seed):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    lane = (seed & MASK) ^ O_TAG_VALUE2

    def corner(dx, dy):
        return 2.0 * o_u01(o_pcg3d(((ix + dx) & MASK, (iy + dy) & MASK, lane))[0]) - 1.0
    u, v = o_fade(fx), o_fade(fy)
    bottom = corner(0, 0) + (corner(1, 0) - corner(0, 0)) * u
    top = corner(0, 1) + (corner(1, 1) - corner(0, 1)) * u
    return bottom + (top - bottom) * v


def o_value3(x, y, z, seed):
    i = [math.floor(c) for c in (x, y, z)]
    f = [c - k for c, k in zip((x, y, z), i)]
    w = [o_fade(t) for t in f]
    lane = (seed & MASK) ^ O_TAG_VALUE3
    total = 0.0
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                h = o_pcg4d(((i[0] + dx) & MASK, (i[1] + dy) & MASK, (i[2] + dz) & MASK, lane))[0]
                weight = ((w[0] if dx else 1 - w[0]) * (w[1] if dy else 1 - w[1]) * (w[2] if dz else 1 - w[2]))
                total += weight * (2.0 * o_u01(h) - 1.0)
    return total


# The 2D gradient set: eight unit vectors at 22.5 + 45k degrees (never on an axis or a diagonal). The top three bits
# of the corner's hash pick one: bit 29 swaps the long and short component, bit 30 flips x, bit 31 flips y.
O_LONG, O_SHORT = math.cos(math.pi / 8), math.sin(math.pi / 8)
O_SCALE2, O_SCALE3 = 1.5132, 0.9649


def o_grad_ramp2(cx, cy, lane, dx, dy):
    h = o_pcg3d((cx, cy, lane))[0]
    gx, gy = (O_SHORT, O_LONG) if (h >> 29) & 1 else (O_LONG, O_SHORT)
    if (h >> 30) & 1:
        gx = -gx
    if (h >> 31) & 1:
        gy = -gy
    return gx * dx + gy * dy


def o_grad2(x, y, seed):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    lane = (seed & MASK) ^ O_TAG_GRAD2
    r = {(a, b): o_grad_ramp2((ix + a) & MASK, (iy + b) & MASK, lane, fx - a, fy - b) for a in (0, 1) for b in (0, 1)}
    u, v = o_fade(fx), o_fade(fy)
    bottom = r[0, 0] + (r[1, 0] - r[0, 0]) * u
    top = r[0, 1] + (r[1, 1] - r[0, 1]) * u
    return O_SCALE2 * (bottom + (top - bottom) * v)


def o_grad_ramp3(c, lane, d):
    # Perlin's twelve cube-edge midpoints, (+-1, +-1, 0) and its permutations, picked by the hash modulo 12.
    k = o_pcg4d((c[0], c[1], c[2], lane))[0] % 12
    plane, s0, s1 = k >> 2, -1.0 if k & 1 else 1.0, -1.0 if k & 2 else 1.0
    a, b = {0: (d[0], d[1]), 1: (d[0], d[2]), 2: (d[1], d[2])}[plane]
    return s0 * a + s1 * b


def o_grad3(x, y, z, seed):
    i = [math.floor(c) for c in (x, y, z)]
    f = [c - k for c, k in zip((x, y, z), i)]
    w = [o_fade(t) for t in f]
    lane = (seed & MASK) ^ O_TAG_GRAD3
    total = 0.0
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                ramp = o_grad_ramp3(((i[0] + dx) & MASK, (i[1] + dy) & MASK, (i[2] + dz) & MASK), lane,
                                    (f[0] - dx, f[1] - dy, f[2] - dz))
                total += ((w[0] if dx else 1 - w[0]) * (w[1] if dy else 1 - w[1]) * (w[2] if dz else 1 - w[2])) * ramp
    return O_SCALE3 * total


# fBm octave hygiene: turn every octave by the golden angle, detune the lacunarity by up to 2 per cent (an irregular,
# golden-ratio-stepped amount), step off the lattice by a fixed offset, and give every octave its own seed.
O_TURN_C, O_TURN_S = math.cos(math.pi * (3.0 - math.sqrt(5.0))), math.sin(math.pi * (3.0 - math.sqrt(5.0)))
O_OFFSET2 = (19.19, -7.31)
O_MAX_OCTAVES = 8


def o_detune(i: int) -> float:
    return 1.0 + 0.02 * ((0.6180339887 * (i + 1)) % 1.0)


def o_fbm2(x, y, octaves, lacunarity, gain, seed):
    total, amp, amps = 0.0, 1.0, 0.0
    for i in range(min(octaves, O_MAX_OCTAVES)):
        total += amp * o_grad2(x, y, (seed + i) & MASK)
        amps += amp
        amp *= gain
        step = lacunarity * o_detune(i)
        x, y = ((O_TURN_C * x - O_TURN_S * y) * step + O_OFFSET2[0], (O_TURN_S * x + O_TURN_C * y) * step + O_OFFSET2[1])
    return total / amps if amps > 0 else 0.0


# Roberts' R2: the plastic number rho (the real root of x^3 = x + 1) strides 1/rho along x and 1/rho^2 along y.
O_RHO = 1.324717957244746
O_R2 = (1.0 / O_RHO, 1.0 / O_RHO ** 2)


def o_r2(px, py):
    return (math.floor(px) * O_R2[0] + math.floor(py) * O_R2[1]) % 1.0


def o_ign(px, py):
    return (52.9829189 * ((0.06711056 * px + 0.00583715 * py) % 1.0)) % 1.0


def wrap_miss(a, b):
    """How far apart two values of a mask that wraps at 1.0 are: 0.9999 and 0.0001 are 0.0002 apart."""
    d = np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)) % 1.0
    return np.minimum(d, 1.0 - d)


# --------------------------------------------------------------------------------------------- the modules themselves

def _atlas():
    return json.loads(ATLAS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def library():
    return M.load_library(strict=False)


def _module(lib, file):
    name = FAMILY[file]
    assert name in lib.modules, f"no module named {name} (expected in arsenal/web/glsl/{file}); " \
                                f"quarantined: {[p for p in lib.problems if file in p['path'].replace(chr(92), '/')]}"
    m = lib.modules[name]
    assert Path(m.path).resolve() == (LIB / file).resolve(), f"{name} lives in {m.path}, not {file}"
    return m


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_every_planned_batch_a_function_is_in_its_planned_file(library, file):
    planned = [row for row in _atlas()["manifest"] if row["file"] == file]
    assert planned, f"the atlas plans no batch-A functions in {file}"
    m = _module(library, file)
    missing = sorted(set(planned[0]["functions"]) - set(m.functions))
    assert not missing, f"{file} lacks the planned {missing}"


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
        if fn in SIGNATURES:
            assert sorted(defs[fn]) == sorted(SIGNATURES[fn]), f"{fn}: {defs[fn]} != planned {SIGNATURES[fn]}"


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_headers_carry_every_library_field(library, file):
    m = _module(library, file)
    h = m.header
    atlas = _atlas()
    parts = [p for p in atlas["parts"] if p.get("module") == file]
    cat = {p["category"] for p in parts}
    assert h["cat"] in cat and h["family"] == h["cat"][0]
    assert h["kind"] in ("helper", "legacy") and re.fullmatch(r"\d+\.\d+\.\d+", h["version"])
    assert h["license"] == "Apache-2.0"
    assert isinstance(h["credits"], list) and h["credits"] and all("http" in c for c in h["credits"]), \
        "credits name who taught the technique, each with a link"
    assert h["cost"]["class"] in ("C0", "C1", "C2", "C3", "C4") and h["cost"]["tex"] == 0
    assert h["contract"] and h["note"] and h["status"] == "P0"
    assert h["targets"]["glsl"] in ("300es", "100")
    assert (LIB / "cards" / h["card"]).is_file() and h["card"] == f"{m.name}.card"
    twin = h["twin"].split(":")[0]
    assert (REPO / twin).is_file(), f"the twin {twin} does not exist"
    p0 = [p for p in parts if p["status"] == "P0"]
    assert sorted(h["exemplars"]) == sorted({e for p in p0 for e in p["exemplars"]})
    assert h["learn"] and set(h["learn"]) <= {x for p in parts for x in p["learn"]}
    assert 10 <= h["order"] <= 30


def test_the_dither_masks_and_the_sine_hash_run_on_webgl1(library):
    """The finish (post/dither.glsl) calls dthIgn and dthTriFromUniform, and the old surfaces include WebGL1 pages."""
    for file in ("noise/dither-masks.glsl", "legacy/hash-sine.glsl"):
        m = _module(library, file)
        assert m.header["targets"] == {"glsl": "100", "needs": []}
        library.compose([m.name], target="webgl1")


def test_the_sine_hash_is_a_private_legacy_twin(library):
    m = _module(library, "legacy/hash-sine.glsl")
    assert m.header["public"] is False and m.header.get("legacy") is True
    assert m.header["targets"] == {"glsl": "100", "needs": []}     # the old surfaces include WebGL1 pages


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_each_module_composes_and_lints_clean(library, file):
    m = _module(library, file)
    for target in ("toy", "webgl2", "three-r186"):
        text = library.compose([m.name], target=target)
        assert m.name in text.splitlines()[0]
    assert M.lint(m, library_module=True, library=library) == []
    if "uint" in m.target_needs:
        with pytest.raises(M.ModuleError, match="uint"):
            library.compose([m.name], target="webgl1")


@pytest.mark.parametrize("file", sorted(FAMILY))
def test_each_module_has_a_card_that_builds(library, file):
    m = _module(library, file)
    card = K.load_card(m.name)
    assert m.name in card.uses and card.note
    built = K.build_card(card, library=library)
    assert built["card"]["modules"] and m.name in built["card"]["modules"]


# ------------------------------------------------------------------------------------------------- the integer hashes
PINNED_HASH_U1 = {0: 0x07BB2FE2, 1: 0xA8BEEA3C, 2: 0x7A7ECC88, 12345: 0xF45EAD0E, 0xFFFFFFFF: 0xE62A4902}
PINNED_PCG3D = {
    (0, 0, 0): (0x9BAFD7C6, 0xA8E88A6B, 0x3F15482C),
    (1, 2, 3): (0xFA9F79A6, 0x48F2F44C, 0x596F5AB1),
    (0xFFFFFFFF, 0, 7): (0x3CC3DE4A, 0xC605F1CD, 0xA4D284E3),
}
PINNED_PCG4D = {
    (0, 0, 0, 0): (0x0F02F829, 0x2D568769, 0x32B0C43B, 0xD32548EA),
    (1, 2, 3, 4): (0x3622CD16, 0xF11471D8, 0xE1109B3F, 0x02B94C2F),
    (0xFFFFFFFF, 0, 7, 0x9E3779B9): (0x0A703176, 0x28A70CB7, 0x977B8A02, 0x8B727CAA),
}


def test_the_pinned_vectors_are_the_oracles_own():
    assert {x: o_hash_u1(x) for x in PINNED_HASH_U1} == PINNED_HASH_U1
    assert {v: o_pcg3d(v) for v in PINNED_PCG3D} == PINNED_PCG3D
    assert {v: o_pcg4d(v) for v in PINNED_PCG4D} == PINNED_PCG4D


def test_the_twin_hashes_match_the_pinned_vectors_bit_for_bit():
    xs = np.array(list(PINNED_HASH_U1), dtype=np.uint32)
    assert H.hashU1(xs).dtype == np.uint32
    assert H.hashU1(xs).tolist() == list(PINNED_HASH_U1.values())
    assert H.pcg3d(np.array(list(PINNED_PCG3D), dtype=np.uint32)).tolist() == [list(v) for v in PINNED_PCG3D.values()]
    assert H.pcg4d(np.array(list(PINNED_PCG4D), dtype=np.uint32)).tolist() == [list(v) for v in PINNED_PCG4D.values()]


def test_the_twin_hashes_match_the_oracle_on_random_inputs():
    rng = np.random.default_rng(20261013)
    x = rng.integers(0, 2 ** 32, 2000, dtype=np.uint64).astype(np.uint32)
    assert H.hashU1(x).tolist() == [o_hash_u1(int(v)) for v in x]
    v3 = rng.integers(0, 2 ** 32, (500, 3), dtype=np.uint64).astype(np.uint32)
    assert H.pcg3d(v3).tolist() == [list(o_pcg3d(tuple(int(c) for c in row))) for row in v3]
    v4 = rng.integers(0, 2 ** 32, (500, 4), dtype=np.uint64).astype(np.uint32)
    assert H.pcg4d(v4).tolist() == [list(o_pcg4d(tuple(int(c) for c in row))) for row in v4]


def _popcount(a):
    a = a.astype(np.uint64)
    return np.array([bin(int(v)).count("1") for v in a])


def test_one_flipped_input_bit_flips_about_half_the_output_bits():
    """The contract's "full avalanche on 32 bits": every input bit reaches every output bit about half the time."""
    rng = np.random.default_rng(1)
    x = rng.integers(0, 2 ** 32, 4096, dtype=np.uint64).astype(np.uint32)
    base = H.hashU1(x)
    for bit in range(32):
        diff = base ^ H.hashU1(x ^ np.uint32(1 << bit))
        assert 15.0 <= _popcount(diff).mean() <= 17.0, f"input bit {bit}"
        per_out = ((diff[:, None] >> np.arange(32, dtype=np.uint32)) & 1).mean(axis=0)
        assert per_out.min() >= 0.38 and per_out.max() <= 0.62, f"input bit {bit}: a stuck or copied output bit"


@pytest.mark.parametrize("fn,lanes", [(H.pcg3d, 3), (H.pcg4d, 4)])
def test_the_multi_lane_hashes_avalanche_on_the_bits_that_lattices_use(fn, lanes):
    """pcg3d and pcg4d: each of the low 17 bits of every input lane flips about half of ALL the output bits. The high
    input bits mix less (measured: bit 31 reaches about a quarter), a property of the design, not of this twin; lattice
    ids and seeds vary in their low bits, and a caller whose seed varies only in its high bits pre-hashes it with
    hashU1 (the warps do)."""
    rng = np.random.default_rng(4)
    v = rng.integers(0, 2 ** 32, (2048, lanes), dtype=np.uint64).astype(np.uint32)
    base = fn(v)
    total = 32 * lanes
    for lane in range(lanes):
        for bit in range(32):
            w = v.copy()
            w[:, lane] ^= np.uint32(1 << bit)
            diff = (fn(w) ^ base).reshape(len(v), -1)
            flips = sum(_popcount(diff[:, k]) for k in range(lanes)).mean()
            if bit < 17:
                assert 0.46 * total <= flips <= 0.54 * total, f"lane {lane} bit {bit}: {flips} of {total}"
            else:
                assert flips >= 0.2 * total, f"lane {lane} bit {bit}: {flips} of {total}"


def test_u01_keeps_the_top_24_bits_exactly_and_never_reaches_one():
    x = np.array([0, 255, 256, 0x80000000, 0xFFFFFFFF], dtype=np.uint32)
    got = H.u01(x)
    assert got.tolist() == [o_u01(int(v)) for v in x]
    assert got[0] == 0.0 and got[1] == 0.0 and got[2] == 2.0 ** -24 and got[3] == 0.5
    assert got[-1] == 1.0 - 2.0 ** -24 < 1.0
    assert np.all(got.astype(np.float32).astype(np.float64) == got)     # exact in a 32-bit float
    assert H.u01(np.array([[1 << 8, 2 << 8, 3 << 8]], dtype=np.uint32)).shape == (1, 3)


def test_cells_wrap_negative_coordinates_by_twos_complement():
    assert H.cellU2(np.array([-0.5, 1.5])).tolist() == [0xFFFFFFFF, 1]
    assert H.cellU3(np.array([-2.0, -1.0e-7, 3.999])).tolist() == [0xFFFFFFFE, 0xFFFFFFFF, 3]
    assert H.cellU2(np.array([-0.5, 1.5])).dtype == np.uint32


def test_the_float_wrappers_hash_the_cell_into_zero_to_one():
    rng = np.random.default_rng(2)
    p2 = rng.uniform(-1000, 1000, (5000, 2))
    p3 = rng.uniform(-1000, 1000, (5000, 3))
    for f, p in ((H.hash21, p2), (H.hash22, p2), (H.hash31, p3), (H.hash33, p3)):
        v = f(p)
        assert v.min() >= 0.0 and v.max() < 1.0
        assert np.array_equal(f(np.floor(p) + 0.25), v), f"{f.__name__} is not constant over a cell"
    assert np.array_equal(H.hash31(p3), H.hash33(p3)[:, 0])           # one hash, three dice: .x is hash31
    assert np.array_equal(H.hash21(p2), H.hash22(p2)[:, 0])
    flat = np.concatenate([p2, np.zeros((len(p2), 1))], axis=1)
    assert not np.array_equal(H.hash21(p2), H.hash31(flat)), "the 2D family must not repeat the z = 0 slice of 3D"
    x, y = 3, -4
    expect = o_u01(o_pcg3d(((x & MASK), (y & MASK), 0x9E3779B9))[0])
    assert H.hash21(np.array([x + 0.5, y + 0.5])) == expect
    assert tuple(H.hash33(np.array([x + 0.5, y + 0.5, -1.5]))) == o_hash33(x + 0.5, y + 0.5, -1.5)


def _spectral_flatness(img):
    power = np.abs(np.fft.fft2(img - img.mean())) ** 2
    power = power.reshape(-1)[1:] + 1e-30
    return float(np.exp(np.mean(np.log(power))) / np.mean(power))


def test_hash21_is_white_noise_by_spectral_flatness():
    """White noise has a flat spectrum: flatness about 0.561 (e to the minus Euler's constant), NP 2.5's probe."""
    ys, xs = np.mgrid[0:256, 0:256]
    img = H.hash21(np.stack([xs, ys], axis=-1).astype(np.float64))
    assert abs(img.mean() - 0.5) < 0.01
    assert 0.54 <= _spectral_flatness(img) <= 0.58
    far = H.hash21(np.stack([xs + 3.0e6, ys - 7.0e6], axis=-1))
    assert 0.54 <= _spectral_flatness(far) <= 0.58, "an integer hash must not degrade far from the origin"


def test_the_sine_hash_twin_is_the_house_expression_and_shows_why_it_is_legacy():
    p = np.array([[0.5, 0.25], [12.0, -3.0]])
    for row, got in zip(p, H.hashSine21(p)):
        phase = np.float32(np.float32(127.1) * np.float32(row[0]) + np.float32(311.7) * np.float32(row[1]))
        expect = np.float32(np.float32(np.sin(np.float64(phase))) * np.float32(43758.5453))
        assert abs(got - (expect - np.floor(expect))) < 1e-6
    ys, xs = np.mgrid[0:256, 0:256].astype(np.float64)
    near = H.hashSine21(np.stack([xs, ys], axis=-1))
    far = H.hashSine21(np.stack([xs + 1.0e6, ys + 1.0e6], axis=-1))
    assert near.min() >= 0 and near.max() < 1
    # far from the origin the float32 dot product steps coarsely: the "randomness" collapses into few values and the
    # spectrum is no longer flat (pcg at the same distance stays white: test_hash21_is_white_noise_by_spectral_flatness)
    assert 0.54 <= _spectral_flatness(near) <= 0.58
    assert len(np.unique(far)) < 0.5 * len(np.unique(near)) and _spectral_flatness(far) < 0.4
    v3 = H.hashSine31(np.array([[1.0, 2.0, 3.0]]))
    assert 0.0 <= v3[0] < 1.0


# ---------------------------------------------------------------------------------------------------- the noises
def _points(n, dims, lo=-50.0, hi=50.0, seed=3):
    return np.random.default_rng(seed).uniform(lo, hi, (n, dims))


def test_value_noise_matches_the_oracle():
    for x, y in _points(300, 2):
        assert abs(N.noiseValue2(np.array([x, y]), 5) - o_value2(x, y, 5)) < 1e-12
    for x, y, z in _points(150, 3):
        assert abs(N.noiseValue3(np.array([x, y, z]), 9) - o_value3(x, y, z, 9)) < 1e-12


def test_value_noise_equals_its_corner_value_on_the_lattice():
    ks = np.floor(_points(400, 2, -1e4, 1e4))
    seed = 77
    lane = np.full((len(ks), 1), seed ^ O_TAG_VALUE2, np.uint32)        # the seed lane carries value noise's own tag
    expect = 2.0 * H.u01(H.pcg3d(np.concatenate([H.cellU2(ks), lane], 1))[:, 0]) - 1
    assert np.array_equal(N.noiseValue2(ks, seed), expect)


def test_value_noise_stays_in_range_and_has_no_second_derivative_jump_at_cell_edges():
    v2 = N.noiseValue2(_points(200000, 2), 0)
    v3 = N.noiseValue3(_points(100000, 3), 0)
    assert v2.min() >= -1.0 and v2.max() < 1.0 and v3.min() >= -1.0 and v3.max() < 1.0
    assert abs(v2.mean()) < 0.02 and 0.2 < v2.std() < 0.5
    # the quintic fade: the second difference just left and just right of every integer x matches (a cubic would jump)
    h = 1e-4
    for x0 in range(-5, 6):
        for y in (0.3, 0.71):
            def f(x):
                return float(N.noiseValue2(np.array([x, y]), 1))
            left = (f(x0 - 2 * h) - 2 * f(x0 - h) + f(x0)) / h ** 2
            right = (f(x0) - 2 * f(x0 + h) + f(x0 + 2 * h)) / h ** 2
            assert abs(left - right) < 0.1, f"curvature jumps at x = {x0}: {left} vs {right}"


def test_gradient_noise_matches_the_oracle():
    for x, y in _points(300, 2):
        assert abs(N.noiseGrad2(np.array([x, y]), 4) - o_grad2(x, y, 4)) < 1e-12
    for x, y, z in _points(150, 3):
        assert abs(N.noiseGrad3(np.array([x, y, z]), 4) - o_grad3(x, y, z, 4)) < 1e-12


def test_gradient_noise_is_zero_on_every_lattice_point():
    k2 = np.floor(_points(1000, 2, -1e5, 1e5))
    k3 = np.floor(_points(1000, 3, -1e5, 1e5))
    assert np.all(N.noiseGrad2(k2, 11) == 0.0) and np.all(N.noiseGrad3(k3, 11) == 0.0)


def test_gradient_noise_never_leaves_minus_one_to_one_and_is_centred():
    """The scales are set from the exact supremum (2D: 0.6608 before scaling; 3D, Perlin's edge set: 1.0363), so the
    extreme is about 0.9999 and the bulk sits near zero."""
    rng = np.random.default_rng(5)
    p2 = np.concatenate([_points(300000, 2), np.floor(_points(100000, 2, -1e4, 1e4)) + 0.5
                         + rng.normal(0, 0.06, (100000, 2))])
    p3 = np.concatenate([_points(200000, 3), np.floor(_points(100000, 3, -1e4, 1e4)) + 0.5
                         + rng.normal(0, 0.06, (100000, 3))])
    n2, n3 = N.noiseGrad2(p2, 0), N.noiseGrad3(p3, 0)
    assert np.abs(n2).max() <= 1.0 and np.abs(n3).max() <= 1.0
    assert np.abs(n2).max() > 0.95 and np.abs(n3).max() > 0.85  # the scale is not wasted headroom either
    assert abs(n2.mean()) < 0.01 and abs(n3.mean()) < 0.01


def test_seeds_give_independent_fields():
    p2, p3 = _points(20000, 2), _points(20000, 3)
    for f, p in ((N.noiseValue2, p2), (N.noiseGrad2, p2), (N.noiseValue3, p3), (N.noiseGrad3, p3)):
        a, b = f(p, 0), f(p, 1)
        assert abs(np.corrcoef(a, b)[0, 1]) < 0.05, f.__name__


# ------------------------------------------------------------------------------- one seed, one field per kind (tags)
# Who feeds which lane of which hash, and with what tag. Two users read the same die when their lanes are equal.
LANE_USERS = {
    "pcg3d": {"noiseValue2 (seed lane)": O_TAG_VALUE2, "noiseGrad2 (seed lane)": O_TAG_GRAD2,
              "hash31/hash33 (z lane)": O_TAG_HASH3, "hash21/hash22 (third lane)": O_LANE_2D,
              "a direct caller of pcg3d": 0},
    "pcg4d": {"noiseValue3 (seed lane)": O_TAG_VALUE3, "noiseGrad3 (seed lane)": O_TAG_GRAD3,
              "a direct caller of pcg4d": 0},
}

# The tags as the GLSL writes them: each must appear, as a uint literal, in the function that feeds it into a lane.
GLSL_TAGS = [("noise/value.glsl", "noiseValue2", O_TAG_VALUE2), ("noise/value.glsl", "noiseValue3", O_TAG_VALUE3),
             ("noise/gradient.glsl", "noiseGrad2", O_TAG_GRAD2), ("noise/gradient.glsl", "noiseGrad3", O_TAG_GRAD3),
             ("hash/pcg.glsl", "hash31", O_TAG_HASH3), ("hash/pcg.glsl", "hash33", O_TAG_HASH3),
             ("hash/pcg.glsl", "hash21", O_LANE_2D), ("hash/pcg.glsl", "hash22", O_LANE_2D)]

# Reference vectors, from the oracle above (re-pinned 2026-10-13 when the tags went in). The dice as 24-bit integers
# (the top 24 bits of a hash word, what u01 keeps): hash33 at a cell, and value noise ON the lattice, where it equals its
# corner's die exactly: (n + 1) * 2^23. Off the lattice, both noises at the same point and seed, in float64.
PINNED_HASH33 = {
    (0, 0, 0): (2418250, 4963687, 8121762),
    (3, -4, 5): (7716335, 5744469, 6031093),
    (-1, -1, -1): (4124127, 13489288, 2442688),
    (100000, 7, -250000): (7539036, 3524453, 13085874),
}
PINNED_VALUE2 = {
    (0, (0, 0)): 7894635, (0, (3, -4)): 15838947, (0, (-1, 2)): 12089985, (0, (65536, -65536)): 6436615,
    (7, (0, 0)): 13018752, (7, (3, -4)): 16134488, (7, (-1, 2)): 4827530, (7, (65536, -65536)): 2285787,
}
PINNED_VALUE3 = {
    (0, (0, 0, 0)): 1158462, (0, (3, -4, 5)): 14070479, (0, (-1, 2, -3)): 8465068,
    (7, (0, 0, 0)): 6125288, (7, (3, -4, 5)): 4080668, (7, (-1, 2, -3)): 441932,
}
PINNED_FIELDS = [   # (point, seed, gradient noise, value noise)
    ((0.25, 0.75), 0, 0.26286053010240945, 0.4794919829355422),
    ((-3.6, 12.1), 0, 0.04665905203491453, -0.1887122966906038),
    ((1000.5, -0.3), 0, 0.08600640172437259, 0.46669585340738284),
    ((0.25, 0.75), 7, -0.5648244453839477, 0.4889821671918071),
    ((-3.6, 12.1), 7, -0.49089189051552967, 0.39945552670370776),
    ((1000.5, -0.3), 7, 0.24863772190840602, -0.18280269659757614),
    ((0.25, 0.75, 0.5), 0, -0.09830270266532898, -0.02176624289472784),
    ((-3.6, 12.1, 7.3), 0, 0.548768090634926, 0.15948498456687774),
    ((0.25, 0.75, 0.5), 7, 0.062063372564315794, 0.46561152491062785),
    ((-3.6, 12.1, 7.3), 7, -0.3595846657734389, -0.5216116773968396),
]


def test_every_kind_has_its_own_tag_and_no_two_kinds_meet_on_a_small_lane():
    """Lanes meet when s ^ tagA == t ^ tagB, i.e. s ^ t == tagA ^ tagB. Seeds and cell z vary in their low bits, and a
    small negative z is all ones above them, so two users' tags must differ in bits 16-31 by a pattern that is neither
    all zeros nor all ones: then no seed or z of magnitude below 2^16 ever reads another kind's dice."""
    for fn, users in LANE_USERS.items():
        names = list(users)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                high = ((users[a] ^ users[b]) >> 16) & 0xFFFF
                assert high not in (0, 0xFFFF), f"{fn}: {a} and {b} meet on small lanes (0x{users[a] ^ users[b]:08X})"
    assert (N.NOISE_TAG_VALUE2, N.NOISE_TAG_VALUE3, N.NOISE_TAG_GRAD2, N.NOISE_TAG_GRAD3) == \
        (O_TAG_VALUE2, O_TAG_VALUE3, O_TAG_GRAD2, O_TAG_GRAD3)
    assert (H.TAG_3D, H.TAG_2D) == (O_TAG_HASH3, O_LANE_2D)


def _glsl_body(code: str, fn: str) -> str:
    m = re.search(r"^\w+\s+" + fn + r"\s*\([^)]*\)\s*\{(.*?)^\}", code, re.M | re.S)
    assert m, f"no definition of {fn}"
    return m.group(1)


@pytest.mark.parametrize("file,fn,tag", GLSL_TAGS)
def test_the_glsl_feeds_the_twins_tag_into_its_lane(library, file, fn, tag):
    body = _glsl_body(M.strip_comments(_module(library, file).body), fn)
    assert re.search(rf"\b0x{tag:08X}u\b", body, re.I), f"{fn} ({file}) does not write its tag 0x{tag:08X}u"


def test_the_tag_pins_are_the_oracles_own():
    assert {c: tuple(int(v * 2 ** 24) for v in o_hash33(*c)) for c in PINNED_HASH33} == PINNED_HASH33
    assert {k: round((o_value2(*map(float, k[1]), k[0]) + 1) * 2 ** 23) for k in PINNED_VALUE2} == PINNED_VALUE2
    assert {k: round((o_value3(*map(float, k[1]), k[0]) + 1) * 2 ** 23) for k in PINNED_VALUE3} == PINNED_VALUE3
    for point, seed, grad, value in PINNED_FIELDS:
        if len(point) == 2:
            assert (o_grad2(*point, seed), o_value2(*point, seed)) == (grad, value)
        else:
            assert (o_grad3(*point, seed), o_value3(*point, seed)) == (grad, value)


def test_the_twins_match_the_tag_pins():
    cells = np.array(list(PINNED_HASH33), dtype=np.float64) + 0.5
    dice = H.hash33(cells) * 2 ** 24
    assert dice.astype(np.int64).tolist() == [list(v) for v in PINNED_HASH33.values()] and np.all(dice % 1 == 0)
    assert np.array_equal(H.hash31(cells), H.hash33(cells)[:, 0])
    for (seed, cell), word in PINNED_VALUE2.items():
        assert (N.noiseValue2(np.array(cell, dtype=np.float64), seed) + 1) * 2 ** 23 == word, (seed, cell)
    for (seed, cell), word in PINNED_VALUE3.items():
        assert (N.noiseValue3(np.array(cell, dtype=np.float64), seed) + 1) * 2 ** 23 == word, (seed, cell)
    for point, seed, grad, value in PINNED_FIELDS:
        p = np.array(point)
        g, v = (N.noiseGrad2, N.noiseValue2) if len(point) == 2 else (N.noiseGrad3, N.noiseValue3)
        assert abs(g(p, seed) - grad) < 1e-12 and abs(v(p, seed) - value) < 1e-12, (point, seed)


def _slope(f, p, axis, seed, h=1e-4):
    step = np.zeros(p.shape[-1])
    step[axis] = h
    return (f(p + step, seed) - f(p - step, seed)) / (2 * h)


@pytest.mark.parametrize("seed", [0, 1, 7, 12345])
def test_noise_kinds_and_hash_wrappers_are_uncorrelated_at_the_same_seed(seed):
    """The batch-A review's measurement, made a pin: at one seed, every pairing of the kinds (value noise, gradient
    noise and its slopes, the hash wrappers on the cell) correlates by less than 0.05 over 60 000 points. Shared dice
    showed as r = 1.0 (value noise on the lattice against hash31 of (cell, seed)), -0.80 (a value corner against the y
    slope of the gradient at the same corner) and -0.36 (the same over the whole plane). Independent fields give
    |r| of about 1 / sqrt(60 000) = 0.004."""
    rng = np.random.default_rng(1013 + seed)
    p2, p3 = rng.uniform(-300, 300, (60000, 2)), rng.uniform(-300, 300, (60000, 3))
    k2, k3 = np.floor(p2), np.floor(p3)
    at_seed = np.concatenate([k2, np.full((len(k2), 1), float(seed))], 1)   # hash31's cell (x, y, z = seed)
    v2, lv2 = N.noiseValue2(p2, seed), N.noiseValue2(k2, seed)
    v3, lv3 = N.noiseValue3(p3, seed), N.noiseValue3(k3, seed)
    lgy2 = _slope(N.noiseGrad2, k2, 1, seed)
    pairs = {
        "value2 ~ grad2": (v2, N.noiseGrad2(p2, seed)),
        "value2 ~ d grad2/dx": (v2, _slope(N.noiseGrad2, p2, 0, seed)),
        "value2 ~ d grad2/dy": (v2, _slope(N.noiseGrad2, p2, 1, seed)),
        "lattice value2 ~ lattice d grad2/dx": (lv2, _slope(N.noiseGrad2, k2, 0, seed)),
        "lattice value2 ~ lattice d grad2/dy": (lv2, lgy2),
        "lattice value2 ~ hash31(cell, seed)": (lv2, H.hash31(at_seed)),
        "lattice value2 ~ hash33(cell, seed).y": (lv2, H.hash33(at_seed)[:, 1]),
        "lattice d grad2/dy ~ hash31(cell, seed)": (lgy2, H.hash31(at_seed)),
        "lattice value2 ~ hash21(cell)": (lv2, H.hash21(k2)),
        "value3 ~ grad3": (v3, N.noiseGrad3(p3, seed)),
        "lattice value3 ~ hash31(cell)": (lv3, H.hash31(k3)),
    }
    for axis in range(3):
        pairs[f"value3 ~ d grad3/d{'xyz'[axis]}"] = (v3, _slope(N.noiseGrad3, p3, axis, seed))
        pairs[f"lattice value3 ~ lattice d grad3/d{'xyz'[axis]}"] = (lv3, _slope(N.noiseGrad3, k3, axis, seed))
    r = {name: float(np.corrcoef(a, b)[0, 1]) for name, (a, b) in pairs.items()}
    bad = {name: round(v, 3) for name, v in r.items() if not abs(v) < 0.05}
    assert not bad, f"seed {seed}: kinds share dice: {bad}"


def test_gain_from_hurst():
    assert N.gainFromHurst(1.0, 2.0) == 0.5
    assert abs(N.gainFromHurst(0.5, 2.0) - 1 / math.sqrt(2)) < 1e-12
    assert N.gainFromHurst(0.0, 2.0) == 1.0
    assert abs(N.gainFromHurst(1.0, 3.0) - 1 / 3) < 1e-12


def test_fbm_matches_the_oracle_and_one_octave_is_the_base_noise():
    for x, y in _points(60, 2):
        for octaves in (1, 3, 8):
            assert abs(N.fbmGrad2(np.array([x, y]), octaves, 2.0, 0.5, 6) - o_fbm2(x, y, octaves, 2.0, 0.5, 6)) < 1e-9
    p2, p3 = _points(500, 2), _points(500, 3)
    assert np.allclose(N.fbmGrad2(p2, 1, 2.0, 0.5, 21), N.noiseGrad2(p2, 21), atol=1e-15)
    assert np.allclose(N.fbmGrad3(p3, 1, 2.0, 0.5, 21), N.noiseGrad3(p3, 21), atol=1e-15)


def test_fbm_is_normalised_so_adding_octaves_does_not_brighten_it():
    p2, p3 = _points(40000, 2), _points(20000, 3)
    std2 = [N.fbmGrad2(p2, n, 2.0, 0.5, 0).std() for n in (1, 2, 4, 8)]
    std3 = [N.fbmGrad3(p3, n, 2.0, 0.5, 0).std() for n in (1, 2, 4, 8)]
    # independent octaves partly cancel, so the spread narrows by about 1/sqrt(3) at gain 0.5; it never grows
    for stds in (std2, std3):
        assert stds == sorted(stds, reverse=True) and stds[0] / stds[-1] < 2.0, stds
    for f, p in ((N.fbmGrad2, p2), (N.fbmGrad3, p3)):
        v = f(p, 8, 2.0, 0.707, 0)
        assert np.abs(v).max() <= 1.0


def test_fbm_octave_bounds_and_the_origin_pinch():
    p = _points(100, 2)
    assert np.array_equal(N.fbmGrad2(p, 0, 2.0, 0.5, 0), np.zeros(100))
    assert np.array_equal(N.fbmGrad2(p, -3, 2.0, 0.5, 0), np.zeros(100))
    assert np.array_equal(N.fbmGrad2(p, 12, 2.0, 0.5, 0), N.fbmGrad2(p, 8, 2.0, 0.5, 0))   # the loop's ceiling
    # gradient noise is zero at the origin for every octave unless each octave steps off the lattice
    assert abs(float(N.fbmGrad2(np.zeros(2), 4, 2.0, 0.5, 0))) > 1e-4
    assert abs(float(N.fbmGrad3(np.zeros(3), 4, 2.0, 0.5, 0))) > 1e-4
    a, b = N.fbmGrad3(_points(5000, 3), 5, 2.0, 0.5, 0), N.fbmGrad3(_points(5000, 3), 5, 2.0, 0.5, 1)
    assert abs(np.corrcoef(a, b)[0, 1]) < 0.05


def test_warp_vector_components_are_decorrelated_and_amount_zero_is_plain_fbm():
    p = _points(20000, 2, -20, 20)
    w = N.warpVec2(p, 4, 3)
    assert w.shape == (20000, 2) and abs(np.corrcoef(w[:, 0], w[:, 1])[0, 1]) < 0.05
    assert np.allclose(N.warpFbm2(p, 0.0, 4, 3), N.fbmGrad2(p, 4, 2.0, 0.5, N.warpFinalSeed(3)), atol=1e-15)
    value, q, r = N.warpNested2(p, 0.0, 4, 3)
    assert np.allclose(q, N.warpVec2(p, 4, 3)) and np.allclose(r, N.warpVec2(p, 4, 4))
    assert np.allclose(value, N.fbmGrad2(p, 4, 2.0, 0.5, N.warpFinalSeed(3)))


def test_warping_bends_the_field_and_stays_in_range():
    p = _points(20000, 2, -20, 20)
    plain = N.fbmGrad2(p, 4, 2.0, 0.5, N.warpFinalSeed(3))
    bent = N.warpFbm2(p, 2.0, 4, 3)
    nested, q, r = N.warpNested2(p, 2.0, 4, 3)
    assert np.abs(bent).max() <= 1.0 and np.abs(nested).max() <= 1.0
    assert np.corrcoef(plain, bent)[0, 1] < 0.9 and np.corrcoef(bent, nested)[0, 1] < 0.9
    assert np.allclose(nested, N.fbmGrad2(p + 2.0 * r, 4, 2.0, 0.5, N.warpFinalSeed(3)))
    assert np.allclose(r, N.warpVec2(p + 2.0 * q, 4, 4))


# ----------------------------------------------------------------------------------------------- the dither masks
def test_r2_is_roberts_mask_and_evenly_spread():
    ys, xs = np.mgrid[0:64, 0:64]
    pix = np.stack([xs, ys], axis=-1).astype(np.float64) + 0.5
    got = N.dthR2(pix)
    assert got.min() >= 0.0 and got.max() < 1.0
    assert wrap_miss(got[5, 9], o_r2(9.5, 5.5)) < 1e-5 and wrap_miss(got[63, 0], o_r2(0.5, 63.5)) < 1e-5
    # 32-bit floats keep it honest out to an 8K canvas: the products round by at most a few ten-thousandths
    far = _points(2000, 2, 0, 8192)
    assert wrap_miss(N.dthR2(far), [o_r2(x, y) for x, y in far]).max() < 1e-3
    counts = np.histogram(got, bins=16, range=(0, 1))[0]
    assert counts.min() >= 240 and counts.max() <= 272        # 256 per bin; a low-discrepancy mask stays close


def test_ign_is_jimenez_and_every_3x3_block_holds_nearly_all_ninths():
    ys, xs = np.mgrid[0:96, 0:96]
    pix = np.stack([xs, ys], axis=-1).astype(np.float64)
    got = N.dthIgn(pix)
    ref = [o_ign(x, y) for x, y in pix.reshape(-1, 2)]
    assert wrap_miss(got.reshape(-1), ref).max() < 2e-3      # the twin rounds like the GPU's 32-bit floats
    assert got.min() >= 0.0 and got.max() < 1.0
    ninths = np.floor(got * 9).astype(int)
    blocks = [len(set(ninths[y:y + 3, x:x + 3].ravel())) for y in range(0, 93, 3) for x in range(0, 93, 3)]
    assert np.mean(blocks) >= 7.0, np.mean(blocks)


def test_triangular_remap_keeps_rank_and_makes_a_triangle():
    u = (np.arange(200000) + 0.5) / 200000
    t = N.dthTriFromUniform(u)
    assert np.all(np.diff(t) > 0)                              # monotone: the mask's spatial spectrum is kept
    assert N.dthTriFromUniform(np.array(0.0)) == -1.0 and N.dthTriFromUniform(np.array(0.5)) == 0.0
    assert abs(N.dthTriFromUniform(np.array(1.0 - 1e-12)) - 1.0) < 1e-5
    assert abs(t.mean()) < 1e-6 and abs(t.var() - 1.0 / 6.0) < 1e-4   # triangular on [-1, 1]: variance 1/6


# ------------------------------------------------------------------------------------------- GPU parity (SwiftShader)
PARITY_CARD = """//! {"card": "parity-hash-noise", "uses": ["hash-pcg", "noise-value", "noise-gradient", "noise-fbm",
//!  "noise-warp", "dither-masks"], "t": [0], "size": [320, 64],
//!  "note": "test fixture: five 64x64 panels of numbers the CPU twin recomputes; not a picture for people"}
// Apache-2.0, Akashic Aurora. A parity fixture: every pixel is a number the numpy twin recomputes.
float parityByte(float die) {
    return floor(die * 256.0) / 255.0;          // the top 8 bits of a [0, 1) die, exactly one 8-bit code
}

void mainImage(out vec4 color, in vec2 pixel) {
    int panel = int(pixel.x) / 64;
    vec2 local = vec2(mod(pixel.x, 64.0), pixel.y);
    uvec2 at = uvec2(local);
    vec3 v;
    if (panel == 4) {
        // every tagged kind not drawn above: 3D value noise (red) and the float hash wrappers (green, blue, exact)
        vec2 p = local / 8.0 - 4.0;
        vec2 cell = floor(local) - 32.0;
        float noise = 0.5 + 0.5 * noiseValue3(vec3(p, -0.61), 3u);
        v = at.y < 32u ? vec3(noise, parityByte(hash31(vec3(cell, 5.0))), parityByte(hash33(vec3(cell, -3.0)).z))
                       : vec3(noise, parityByte(hash21(cell)), parityByte(hash22(cell + 0.5).y));
    } else if (panel == 0) {
        uvec3 a = pcg3d(uvec3(at, 0xC0FFEEu));
        uvec4 b = pcg4d(uvec4(at, 7u, 0x5EEDu));
        uint c = hashU1(at.x + 64u * at.y);
        v = at.y < 32u ? vec3(a.x >> 24u, (a.y >> 12u) & 255u, a.z & 255u)
                       : vec3(c >> 24u, (b.w >> 8u) & 255u, b.x & 255u);
        v /= 255.0;
    } else if (panel == 1) {
        vec2 p = local / 8.0 - 4.0;
        v = 0.5 + 0.5 * vec3(noiseValue2(p, 3u), noiseGrad2(p, 3u), noiseGrad3(vec3(p, 0.37), 3u));
    } else if (panel == 2) {
        vec2 p = local / 16.0 - 2.0;
        v = 0.5 + 0.5 * vec3(fbmGrad2(p, 5, 2.0, 0.5, 9u), fbmGrad3(vec3(p, 1.3), 4, 2.0, 0.55, 9u),
                             warpFbm2(p, 1.5, 3, 9u));
    } else {
        v = vec3(dthIgn(floor(local)), dthR2(floor(local)), 0.5 + 0.5 * dthTriFromUniform(dthR2(floor(local))));
    }
    color = vec4(v, 1.0);
}
"""


def _twin_parity_image():
    ys, xs = np.mgrid[0:64, 0:64]
    centre = np.stack([xs + 0.5, ys + 0.5], axis=-1)            # gl_FragCoord: pixel centres, y up
    at = np.stack([xs, ys], axis=-1).astype(np.uint32)
    out = np.zeros((64, 320, 3))
    a = H.pcg3d(np.concatenate([at, np.full((64, 64, 1), 0xC0FFEE, np.uint32)], -1))
    b = H.pcg4d(np.concatenate([at, np.full((64, 64, 1), 7, np.uint32), np.full((64, 64, 1), 0x5EED, np.uint32)], -1))
    c = H.hashU1((at[..., 0] + 64 * at[..., 1]).astype(np.uint32))
    low = np.stack([a[..., 0] >> 24, (a[..., 1] >> 12) & 255, a[..., 2] & 255], -1)
    high = np.stack([c >> 24, (b[..., 3] >> 8) & 255, b[..., 0] & 255], -1)
    out[:, 0:64] = np.where((at[..., 1] < 32)[..., None], low, high) / 255.0
    p = centre / 8.0 - 4.0
    p3 = np.concatenate([p, np.full((64, 64, 1), 0.37)], -1)
    out[:, 64:128] = 0.5 + 0.5 * np.stack([N.noiseValue2(p, 3), N.noiseGrad2(p, 3), N.noiseGrad3(p3, 3)], -1)
    p = centre / 16.0 - 2.0
    p3 = np.concatenate([p, np.full((64, 64, 1), 1.3)], -1)
    out[:, 128:192] = 0.5 + 0.5 * np.stack([N.fbmGrad2(p, 5, 2.0, 0.5, 9), N.fbmGrad3(p3, 4, 2.0, 0.55, 9),
                                            N.warpFbm2(p, 1.5, 3, 9)], -1)
    pix = np.floor(centre)
    r2 = N.dthR2(pix)
    out[:, 192:256] = np.stack([N.dthIgn(pix), r2, 0.5 + 0.5 * N.dthTriFromUniform(r2)], -1)
    p = centre / 8.0 - 4.0
    cell = pix - 32.0
    noise = 0.5 + 0.5 * N.noiseValue3(np.concatenate([p, np.full((64, 64, 1), -0.61)], -1), 3)
    low = np.stack([noise, _byte(H.hash31(np.concatenate([cell, np.full((64, 64, 1), 5.0)], -1))),
                    _byte(H.hash33(np.concatenate([cell, np.full((64, 64, 1), -3.0)], -1))[..., 2])], -1)
    high = np.stack([noise, _byte(H.hash21(cell)), _byte(H.hash22(cell + 0.5)[..., 1])], -1)
    out[:, 256:320] = np.where((at[..., 1] < 32)[..., None], low, high)
    return np.round(np.clip(out, 0, 1) * 255.0)[::-1]           # PNG rows run top down


def _byte(die):
    return np.floor(die * 256.0) / 255.0


@pytest.mark.slow
@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH (the headless driver)")
def test_the_glsl_matches_its_twin_on_swiftshader(tmp_path):
    from PIL import Image
    cards_dir = tmp_path / "cards"
    cards_dir.mkdir()
    (cards_dir / "parity-hash-noise.card").write_text(PARITY_CARD, encoding="utf-8", newline="\n")
    report = K.render_cards(["parity-hash-noise"], cards_dir=cards_dir, out_root=tmp_path / "out",
                            allow_tracked=True, lock_wait_min=5, quiet=True)
    if report["driver"].get("error") and "lock" in str(report["driver"]["error"]).lower():
        pytest.skip(f"the GPU lock stayed busy: {report['driver']['error']}")
    row = report["cards"][0]
    assert row["compile_ok"] is True and row["nan_pixels"] == 0, row
    png = sorted((tmp_path / "out" / "parity-hash-noise").glob("t0*.png"))[0]
    gpu = np.asarray(Image.open(png).convert("RGB")).astype(np.float64)
    cpu = _twin_parity_image()
    hashes = gpu[:, 0:64] - cpu[:, 0:64]
    assert np.count_nonzero(hashes) == 0, "the integer hashes are not bit-exact on the GPU"
    smooth = np.abs(gpu[:, 64:192] - cpu[:, 64:192])
    assert smooth.max() <= 2 and np.mean(smooth > 1) < 0.001, f"noise/fbm/warp drift: max {smooth.max()}"
    masks = np.abs(gpu[:, 192:256] - cpu[:, 192:256])
    masks = np.minimum(masks, 255 - masks)                         # a mask wraps at 1.0: 254/255 vs 0 is a near miss
    assert masks.max() <= 2 and np.mean(masks > 1) < 0.002
    # the tagged kinds: 3D value noise within the smooth tolerance, the float hash wrappers to the exact code
    value3 = np.abs(gpu[:, 256:320, 0] - cpu[:, 256:320, 0])
    assert value3.max() <= 2 and np.mean(value3 > 1) < 0.001, f"noiseValue3 drift: max {value3.max()}"
    wrappers = gpu[:, 256:320, 1:] - cpu[:, 256:320, 1:]
    assert np.count_nonzero(wrappers) == 0, "hash31/hash33/hash21/hash22 are not bit-exact on the GPU"
