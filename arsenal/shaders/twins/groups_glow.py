"""CPU twin of the glow-xray group's recipe, arsenal/web/glsl/groups/glow-xray.glsl (glowXray: a pass-through march that
lights everything it passes near). Pinned by tests/test_glsl_twins_groups_g1.py.

WHY. The x-ray look rests on three promises a seat can measure without a screen: a ray that passes nothing gathers
nothing (black stays black), the skin's light is an integral over the step (so a finer march gathers the same light,
which the popular 1/d-per-step glow does not), and the step budget acts as opacity (more budget never dims a pixel, a
short budget stops rays before the back of the scene). This twin marches every pixel at once in numpy, with the host's
scene passed in as a Python function of points (the twin of the mapScene hook), one numpy line per GLSL line.

Apache-2.0, Akashic Aurora. Written fresh; no corpus code. The constants are the recipe's own.
"""
from __future__ import annotations

import numpy as np

from . import core as CR
from . import noise as N
from . import palette as PL

MAX_STEPS = 160
SCENE_REACH = 6.0                  # the scene lives within this many units of the origin
SKIN_GAIN = 0.08                   # glowEmitStep's k is SKIN_GAIN / sparkWidth
LOITER_SKINS = 4.0                 # a step within this many spark widths of a surface counts as loitering
WASH_POWER = 1.5                   # glowStepCount's k
# palette choice -> (a, b, c, d) cosine coefficients (display values), and the wash colour (linear)
PALETTES = [
    ((0.55, 0.45, 0.85), (0.40, 0.30, 0.15), (0.7, 0.7, 0.7), (0.497, 0.617, 0.917)),
    ((0.55, 0.25, 0.10), (0.45, 0.25, 0.10), (1.0, 1.0, 1.0), (0.0, 0.08, 0.18)),
    ((0.25, 0.60, 0.85), (0.25, 0.30, 0.15), (1.0, 1.0, 1.0), (0.55, 0.50, 0.45)),
]
WASH = [np.array([0.9331, 0.2330, 0.1473]), np.array([0.60, 0.06, 0.02]), np.array([0.10, 0.25, 0.90])]


def _choice(palette):
    p = int(palette)
    return p if p in (1, 2) else 0


def xrayHue(depth, palette, hueSpeed):
    """The colour of light gathered `depth` in front of (negative) or behind (positive) the origin's distance:
    palCosLinear(hueSpeed * depth) through the chosen palette. Linear light, shape (..., 3)."""
    a, b, c, d = PALETTES[_choice(palette)]
    return PL.palCosLinear(float(hueSpeed) * np.asarray(depth, dtype=np.float64), a, b, c, d)


def _rays(pixel, res, basis, focal):
    uv = np.asarray(CR.uvCentered(np.asarray(pixel, np.float32), np.asarray(res, np.float32)), np.float64)
    local = np.stack([uv[..., 0], uv[..., 1], np.full(uv.shape[:-1], -float(focal))], -1)
    through = local @ np.asarray(basis, dtype=np.float64).T
    return through / np.linalg.norm(through, axis=-1, keepdims=True)


def _pass_step(d, passthrough, density):
    return np.maximum(float(passthrough) + np.abs(d) / max(float(density), 1e-6), 1e-4)


def _march(pixel, res, ro, basis, focal, budget, passthrough, density, sparkWidth, palette, hueSpeed, scene):
    ro = np.asarray(ro, dtype=np.float64)
    rd = _rays(pixel, res, basis, focal)
    steps = min(max(int(budget), 1), MAX_STEPS)
    width = max(float(sparkWidth), 1e-4)
    centre = float(np.linalg.norm(ro))
    far = centre + SCENE_REACH
    first = float(np.asarray(scene(ro[None, :]), np.float64).reshape(-1)[0])
    t = 0.0 + N.dthIgn(pixel) * _pass_step(first, passthrough, density)
    spark = np.zeros(rd.shape)
    loiter = np.zeros(rd.shape[:-1])
    used = np.zeros(rd.shape[:-1])
    a, b, c, dd = PALETTES[_choice(palette)]
    for i in range(MAX_STEPS):
        live = (i < steps) & (t <= far)
        if not live.any():
            break
        d = np.asarray(scene(ro + rd * t[..., None]), dtype=np.float64)
        stride = _pass_step(d, passthrough, density)
        skin = np.exp(-np.abs(d) / width)
        emit = (SKIN_GAIN / width) * skin * np.maximum(stride, 0.0)          # glowEmitStep(skin, stride, k)
        hue = PL.palCosLinear(float(hueSpeed) * (t - centre), a, b, c, dd)
        spark = spark + np.where(live[..., None], hue * emit[..., None], 0.0)
        loiter = loiter + np.where(live & (np.abs(d) < LOITER_SKINS * width), 1.0, 0.0)
        used = used + np.where(live, 1.0, 0.0)
        t = np.where(live, t + stride, t)
    return spark, loiter, used, steps


def xraySteps(pixel, res, ro, basis, focal, budget, passthrough, density, scene):
    """How many steps each ray took (the steps-heat view's count)."""
    return _march(pixel, res, ro, basis, focal, budget, passthrough, density, 0.03, 0, 0.0, scene)[2]


def glowXray(pixel, res, ro, basis, focal, budget, passthrough, density, sparkWidth, palette, hueSpeed, rim, view,
             scene):
    """The twin of glowXray, scene-linear, shape (..., 3). `scene(points)` is the host's mapScene over (..., 3) points.
    View 2 (the field slice) reads screen derivatives and has no CPU twin."""
    if int(view) == 2:
        raise ValueError("view 2 (the field slice) reads screen derivatives: it has no CPU twin")
    spark, loiter, used, steps = _march(pixel, res, ro, basis, focal, budget, passthrough, density, sparkWidth,
                                        palette, hueSpeed, scene)
    if int(view) == 1:
        return np.asarray(CR.dbgHeatCount(used, float(steps)), np.float64)
    share = np.clip(loiter / max(float(steps), 1.0), 0.0, 1.0)
    wash = max(float(rim), 0.0) * (1.0 - np.power(1.0 - share, max(WASH_POWER, 1e-3)))     # glowStepCount
    return spark + wash[..., None] * WASH[_choice(palette)]
