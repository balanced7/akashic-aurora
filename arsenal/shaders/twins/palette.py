"""CPU twins of the house palette module, colour/palette.glsl.

WHY. A palette is a promise about colour that many surfaces share; the pitch palette above all, because "C is a
different colour on different surfaces" was the defect (nine copies with different starting angles, arc-piano-core).
Each GLSL palette function has a numpy twin with the same name and maths. tests/test_glsl_twins_colour.py holds the
pitch palette three ways: the GLSL rendered on SwiftShader, this twin, and the piano page's own JavaScript, within one
8-bit code per channel for all twelve pitch classes.

THE PITCH PALETTE, in plain words (piano.js, the colour section). Hue walks the circle of fifths: C at 200 degrees, each
fifth 30 degrees further, so a key's notes sit on one arc of hues. Each hue is taken near the lightness where sRGB lets
it be most colourful (its cusp), at 95% of the gamut's edge, so no note is a pastel. Then every colour is scaled most
of the way toward one shared luminance, so a note's name never decides how bright it is; velocity does. The GLSL finds
the cusp exactly (a bisection along the RGB cube's saturated edge) and then snaps it to the piano's 0.01 lightness grid,
so it reproduces the piano's scan without its 68-step loop.

Apache-2.0, Akashic Aurora. Written fresh from the mathematics; credits in colour/palette.glsl's header (Inigo Quilez's
cosine palettes; Bjorn Ottosson's OKLab; the piano's own palette, piano.js).
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .colour import (linearFromOklab, luminance, mixOklab, oklabFromLinear, oklabFromOklch, oklchClip,
                     oklchCusp, oklchMaxChroma, srgbDecode)

TAU = 2.0 * np.pi


def _v(x):
    return np.asarray(x, dtype=float)


@dataclass(frozen=True)
class PitchPalette:
    """The knobs of palPitchFifths, field for field as the GLSL struct PitchPalette declares them."""
    hueC: float        # hue of pitch class C, in turns (the piano: 200 degrees)
    hueStep: float     # hue added per fifth, in turns (1/12: twelve fifths close the circle)
    baseL: float       # the lightness every hue starts from
    cuspPull: float    # 0..1: how far each hue moves toward its own most colourful lightness
    cuspGrid: float    # the cusp lightness snaps to this grid (the piano scans in 0.01 steps); 0 = the exact cusp
    edge: float        # the fraction of the sRGB chroma edge used (0.95: near the wall, never on it)
    gamutEps: float    # the in-gamut tolerance of the chroma search (the piano's 1e-4)
    lumaTarget: float  # the shared luminance every colour is pulled toward; 0 = no pull
    lumaPull: float    # 0..1: how far toward it (the piano: 0.65)
    octaveL: float     # lightness added per octave above octave 4 (the piano: 0, it ignores the octave)


# The geometric mean luminance of the piano's twelve un-pulled pitch colours. palPitchLumaMean computes it; a test holds
# this constant (and the GLSL's copy of it) to that computation and to the piano's own pitchLumaMean.
PIANO_LUMA_TARGET = 0.37631920377545836


def palPitchPiano() -> PitchPalette:
    """The piano page's pitch palette (arsenal/web/piano.js, colour mode "pitch")."""
    return PitchPalette(hueC=200.0 / 360.0, hueStep=1.0 / 12.0, baseL=0.72, cuspPull=0.75, cuspGrid=0.01, edge=0.95,
                        gamutEps=1e-4, lumaTarget=PIANO_LUMA_TARGET, lumaPull=0.65, octaveL=0.0)


def palCos(t, a, b, c, d):
    """Quilez's cosine palette a + b cos(2 pi (c t + d)), per channel. DISPLAY values, as tuned on screen."""
    t = _v(t)[..., None]
    return _v(a) + _v(b) * np.cos(TAU * (_v(c) * t + _v(d)))


def palCosLinear(t, a, b, c, d):
    """The same palette decoded to linear light, for lit and blended pipelines."""
    return srgbDecode(palCos(t, a, b, c, d))


def palOklch(t, L, C, h0, turns):
    """A hue sweep at constant OKLab lightness and chroma, gamut-clipped; returns linear light."""
    t = _v(t)
    lch = np.stack(np.broadcast_arrays(_v(L) + 0.0 * t, _v(C) + 0.0 * t, _v(h0) + _v(turns) * t), axis=-1)
    return oklchClip(lch)


def palRamp3(t, linA, linB, linC):
    """A three-stop gradient interpolated in OKLab: A at t = 0, B at 0.5, C at 1 (t clamped); returns linear."""
    u = 2.0 * np.clip(_v(t), 0.0, 1.0)
    first = np.clip(u, 0.0, 1.0)[..., None]
    second = np.clip(u - 1.0, 0.0, 1.0)[..., None]
    a, b, c = oklabFromLinear(linA), oklabFromLinear(linB), oklabFromLinear(linC)
    lab = a + (b - a) * first
    lab = lab + (c - lab) * second
    return linearFromOklab(lab)


def palHeatPowers(x, exponents):
    """One intensity to a colour by a power per channel: x^e. For x < 1 the smallest exponent leads (dim is deep), at
    x = 1 every channel meets (white), past 1 the largest leads. Exponents > 0."""
    x = np.maximum(_v(x), 1e-20)[..., None]
    return np.power(x, _v(exponents))


def _pitch_hue(pitchClass, pp: PitchPalette):
    pc = np.mod(np.floor(_v(pitchClass) + 0.5), 12.0)
    h = pp.hueC + pp.hueStep * np.mod(pc * 7.0, 12.0)
    return h - np.floor(h)


def palPitchFifths(pitchClass, octave, pp: PitchPalette):
    """The house note colour (linear light). pitchClass is rounded to a whole semitone and taken mod 12 (C = 0)."""
    hue = _pitch_hue(pitchClass, pp)
    cusp_l = oklchCusp(hue)[..., 0]
    if pp.cuspGrid > 0.0:
        below = np.floor(cusp_l / pp.cuspGrid) * pp.cuspGrid
        above = below + pp.cuspGrid
        cusp_l = np.where(oklchMaxChroma(below, hue, pp.gamutEps) >= oklchMaxChroma(above, hue, pp.gamutEps),
                          below, above)
    base_l = pp.baseL + pp.octaveL * (_v(octave) - 4.0)
    L = np.clip(base_l * (1.0 - pp.cuspPull) + cusp_l * pp.cuspPull, 0.0, 1.0)
    c = pp.edge * oklchMaxChroma(L, hue, pp.gamutEps)
    rgb = np.maximum(linearFromOklab(oklabFromOklch(np.stack(np.broadcast_arrays(L, c, hue), axis=-1))), 0.0)
    if pp.lumaTarget > 0.0:
        rgb = rgb * np.power(pp.lumaTarget / np.maximum(luminance(rgb), 1e-4), pp.lumaPull)[..., None]
    return rgb


def palPitchLumaMean(pp: PitchPalette) -> float:
    """The geometric mean luminance of the twelve pitch colours before the luminance pull: the shared luminance the
    pull aims at. Twelve palette evaluations, so a host computes it once (here, or in a one-off pass), never per pixel."""
    raw = replace(pp, lumaTarget=0.0)
    lum = [float(luminance(palPitchFifths(float(p), 4.0, raw))) for p in range(12)]
    return float(np.exp(np.mean(np.log(lum))))


__all__ = ["PitchPalette", "palPitchPiano", "palCos", "palCosLinear", "palOklch", "palRamp3", "palHeatPowers",
           "palPitchFifths", "palPitchLumaMean"]
