"""CPU twin of arsenal/web/glsl/motion/envelope.glsl (module motion-envelope): the house envelopes, the same maths in
float64, one function per GLSL function with the GLSL name.

WHY. An envelope is a promise about time (zero outside its act, three flashes a second at most), and a promise about
time is easiest to check by stepping a clock on the CPU. tests/test_glsl_twins_finish_io.py pins these to reference
values and to the contracts in the module's header. Apache-2.0, written fresh from the mathematics.
"""

from __future__ import annotations

import math


def _clamp(x: float, lo: float, hi: float) -> float:
    return min(max(x, lo), hi)


def _smoothstep(e0: float, e1: float, x: float) -> float:
    t = _clamp((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _fract(x: float) -> float:
    return x - math.floor(x)


def envRamp(t: float, start: float, dur: float) -> float:
    """clamp((t - start) / dur, 0, 1); dur <= 0 switches at once, just after start."""
    return _clamp((t - start) / max(dur, 1e-6), 0.0, 1.0)


def envWindow(t: float, a: float, b: float, soft: float) -> float:
    """In from a over soft seconds, out by b over soft seconds; exactly 0 outside [a, b]."""
    s = max(soft, 1e-6)
    return _smoothstep(a, a + s, t) * (1.0 - _smoothstep(b - s, b, t))


def envCubicEase(x: float) -> float:
    """Cubic in-out on a clamped 0..1 input."""
    u = _clamp(x, 0.0, 1.0)
    back = 2.0 - 2.0 * u
    return 4.0 * u * u * u if u < 0.5 else 1.0 - 0.5 * back * back * back


def envSineEase(x: float) -> float:
    """Sine in-out on a clamped 0..1 input."""
    u = _clamp(x, 0.0, 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * u)


def envFlashSafe(sinceLastFlash: float) -> float:
    """0 until a third of a second after the last flash, 1 from half a second on."""
    return _smoothstep(1.0 / 3.0, 0.5, sinceLastFlash)


def envBreath(x: float, t: float, rates) -> float:
    """A slow body plus a faster fringe travelling along x (body wavelengths) at rates = (body, fringe) cycles/s."""
    rb, rf = float(rates[0]), float(rates[1])
    tau = 2.0 * math.pi
    body_wave = 0.6 * math.sin(tau * _fract(x - rb * t)) + 0.4 * math.sin(tau * _fract(2.37 * x + 0.71 - 1.3 * rb * t))
    body = _smoothstep(-0.9, 0.0, body_wave)
    fringe_wave = 0.6 * math.sin(tau * _fract(3.1 * x - rf * t)) + 0.4 * math.sin(
        tau * _fract(5.3 * x + 0.29 + 0.7 * rf * t)
    )
    fringe = _smoothstep(0.35, 0.9, fringe_wave)
    return (body + 0.5 * fringe) / 1.5
