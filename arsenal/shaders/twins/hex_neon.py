"""CPU twin of groups/hex-neon.glsl, the hex-neon group recipe (atlas section 16.7): hexNeonStep, hexNeonSwell,
hexNeonPose, hexNeonColour, hexNeonCell and hexNeon. Pinned by tests/test_glsl_twins_groups_neon_studio_hex.py, which
also holds the GLSL to this twin on SwiftShader.

WHY. The group's promises are about whole cells and their borders: a cell's pose reads only its centre (so the wave
arrives tile by tile), a line keeps its pixel width at any cell size, and the seven-cell pass leaves no seam where
cells meet. None of that can be read from a screenshot with confidence, so it is pinned here. The parts the recipe calls
come from their own twins (the lattice, the hexagon, the coverages and the cell delay from draw2.py, the hash from
hash.py, the palettes from palette.py, the glow from light.py, cmpXor from parity.py, dbgCells from core.py), so a
change there reaches this file the way it reaches the shader. Points broadcast: p may be any array whose last axis is
xy; scalars stay scalars where the GLSL's do.

Apache-2.0, Akashic Aurora. Written fresh from the recipe's contract; no corpus code.
"""
from __future__ import annotations

import math

import numpy as np

from arsenal.shaders.twins import colour, core, draw2, hash as hashes, light, palette, parity

F32 = np.float32
TAU = 2.0 * math.pi
REST = 0.36                                      # a hexagon's rest inradius, in cells
SWING = 0.65                                     # the size swing at sizeAmp 1, as a share of the rest size
CORAL = np.array([0.745, 0.168, 0.078])          # #e0724f, the house accent, linear
COOL = dict(a=(0.35, 0.575, 0.9), b=(0.25, 0.275, 0.08), c=(0.5, 0.5, 0.5), d=(0.5, 0.0, 0.0))


def _v(x):
    return np.asarray(x, dtype=np.float64)


def _smoothstep(e0, e1, x):
    t = np.clip((_v(x) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def hexNeonStep(k):
    """The step to the k-th neighbour, counter-clockwise from +x: (cos k pi/3, sin k pi/3)."""
    angle = float(F32(k) * F32(math.pi / 3.0))
    return np.array([math.cos(angle), math.sin(angle)])


def hexNeonSwell(since, dice):
    """0.5 + 0.3 sin(TAU 0.23 since + 1.2 dice) + 0.2 sin(TAU 0.097 since + 2): in [0, 1]."""
    since, dice = _v(since), _v(dice)
    return 0.5 + 0.3 * np.sin(TAU * 0.23 * since + 1.2 * dice) + 0.2 * np.sin(TAU * 0.097 * since + 2.0)


def _dice(centre):
    return _v(hashes.hash21(draw2.latHexAxial(_v(centre).astype(F32))))


def hexNeonPose(centre, t, originLat, waveSpeed, sizeAmp, spin):
    """(inradius, turn, swell) of the cell whose centre is `centre`: the swell at the cell's own clock, t minus the
    centre's distance from the origin over the speed, detuned by the cell's die."""
    centre = _v(centre)
    delay = _v(draw2.patCellDelay(centre.astype(F32), _v(originLat).astype(F32), F32(waveSpeed)))
    swell = hexNeonSwell(float(t) - delay, _dice(centre))
    size = 1.0 + min(max(float(sizeAmp), 0.0), 1.0) * SWING * (2.0 * swell - 1.0)
    return np.stack(np.broadcast_arrays(REST * size, TAU * float(spin) * (size - 1.0), swell), -1)


def hexNeonColour(axial, dice, palette_choice, accent):
    """Linear colour: palette 1 the note colour of (7q + 4r) mod 12; else coral where the hash's low bits fall under
    `accent`, the cool cosine family elsewhere."""
    axial, dice = _v(axial), _v(dice)
    if palette_choice == 1:
        pitch = np.mod(7.0 * axial[..., 0] + 4.0 * axial[..., 1], 12.0)
        return palette.palPitchFifths(pitch, 4.0, palette.palPitchPiano())
    second = np.mod(dice * 64.0, 1.0)
    cool = palette.palCosLinear(dice, COOL["a"], COOL["b"], COOL["c"], COOL["d"])
    out = np.where((second < float(accent))[..., None], CORAL, cool)
    return out


def hexNeonCell(offset, centre, pxLat, t, originLat, lineWidth, haloPx, waveSpeed, sizeAmp, spin, palette_choice,
                accent, combine):
    """(light rgb, fill) of one cell seen from `offset` cells away from its centre; in XOR mode the rgb is the cell's
    colour at its energy. Its light and fill fade out between 0.8 and 1.15 cells from its centre."""
    offset, centre = _v(offset), _v(centre)
    reach = 1.0 - _smoothstep(0.8, 1.15, np.linalg.norm(offset, axis=-1))
    pose = hexNeonPose(centre, t, originLat, waveSpeed, sizeAmp, spin)
    c, s = np.cos(-pose[..., 1]), np.sin(-pose[..., 1])
    turned = np.stack([c * offset[..., 0] - s * offset[..., 1], s * offset[..., 0] + c * offset[..., 1]], -1)
    pixel = max(float(pxLat), 1e-6)
    d = _v(draw2.sd2Hexagon(turned.astype(F32), pose[..., 0].astype(F32)))
    fill = _v(draw2.aaFill(d, pixel)) * reach
    fill = np.where(reach > 0.0, fill, 0.0)
    energy = 0.04 + 0.96 * pose[..., 2] ** 3
    axial = draw2.latHexAxial(centre.astype(F32))
    hue = hexNeonColour(axial, _v(hashes.hash21(axial)), palette_choice, accent)
    if combine == 2:
        rgb = np.where((fill > 0.0)[..., None], hue * energy[..., None], 0.0)
        return rgb, fill
    line = _v(draw2.aaWire(d, lineWidth, pixel))
    beyond = np.maximum(np.abs(d) / pixel - 0.5 * max(float(lineWidth), 1.0), 0.0)
    glow = _v(light.glowExp(beyond * beyond, 1.0 / (haloPx * haloPx))) if haloPx > 0.0 else np.zeros_like(beyond)
    shine = reach * energy * (1.5 * line + 0.35 * glow)
    shine = np.where((reach > 0.0) & (shine > 1e-5), shine, 0.0)
    return hue * shine[..., None], fill


def hexNeon(p, px, t, origin, cellSize, lineWidth, haloPx, waveSpeed, sizeAmp, spin, palette_choice, accent, combine,
            view):
    """The hex-neon group at points p (pixel size px in p's units), time t, the wave starting at origin."""
    scale = max(float(cellSize), 1e-4)
    lat = _v(p) / scale
    pxLat = max(float(px), 1e-6) / scale
    home = _v(draw2.latHex(lat.astype(F32)))
    if view == 1:
        cells = _v(core.dbgCells(home[..., :2], draw2.latHexAxial(home[..., 2:]), np.array([1.0, 2.0 / math.sqrt(3.0)]),
                                 pxLat))
        border = _v(draw2.aaWire(draw2.latHexEdge(home[..., :2].astype(F32)), 1.0, pxLat))[..., None]
        cells = cells + (1.0 - cells) * border
        return colour.srgbDecode(np.clip(cells, 0.0, 1.0))
    originLat = _v(origin) / scale
    lit = np.zeros(lat.shape[:-1] + (3,))
    ink = np.zeros(lat.shape[:-1])
    ink_colour = np.zeros_like(lit)
    ink_weight = np.zeros_like(ink)
    for k in range(7):
        step = np.zeros(2) if k == 0 else hexNeonStep(k - 1)
        rgb, fill = hexNeonCell(home[..., :2] - step, home[..., 2:] + step, pxLat, t, originLat, lineWidth, haloPx,
                                waveSpeed, sizeAmp, spin, palette_choice, accent, combine)
        if combine == 2:
            ink = parity.cmpXor(ink, fill)
            ink_colour = ink_colour + rgb * fill[..., None]
            ink_weight = ink_weight + fill
        elif combine == 1:
            lit = np.maximum(lit, rgb)
        else:
            lit = lit + rgb
    if combine == 2:
        lit = ink_colour / np.maximum(ink_weight, 1e-6)[..., None] * _v(ink)[..., None]
    return lit


__all__ = ["hexNeonStep", "hexNeonSwell", "hexNeonPose", "hexNeonColour", "hexNeonCell", "hexNeon"]
