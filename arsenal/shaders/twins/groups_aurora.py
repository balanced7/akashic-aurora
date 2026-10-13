"""CPU twin of the aurora group's two P0 recipes, arsenal/web/glsl/groups/aurora-band.glsl (auroraBand, the curtains
painted on the sky) and groups/aurora-sheets.glsl (auroraSheets, a stack of sheets over one 2D footprint). Pinned by
tests/test_glsl_twins_groups_g1.py.

WHY. A recipe is a wiring diagram, and a wiring diagram's promises are measurable without a screen: nothing at all glows
under a hem, the hem is sharp and the top fades, colour climbs in physical order (or analogous with one coral accent)
and never goes silver or white (a hot spot is scaled down as a whole colour before the display curve can bleach it),
the energetic fringe is a thin coloured edge in short pieces at every clock, as thick on screen near as far, that
gives way to any drape behind it and to a fold seen edge-on (never an outline along every hem), a curtain's end fades
instead of standing as a wall, the glow lift bends magnitude and never hue, the motion is slow and never loops, a ray
stands up its own column, a quality tier changes cost and not exposure (its grain stays faint and unstructured), a far
curtain blurs instead of aliasing, the lake is the sky's exact mirror. This twin wires the batch-A and batch-B twins
exactly as the GLSL wires the modules, one numpy expression per GLSL line, vectorised over pixels (pixel arrays end in a
last axis of 2; colours come back with a last axis of 3), so a seat that cannot see can check every one of them, and the
slow test can match the GPU pixel for pixel.

Apache-2.0, Akashic Aurora. Written fresh; no corpus code. The constants below are the recipes' own; a change to
either side is a change to both.
"""
from __future__ import annotations

import numpy as np

from . import atmos as A
from . import core as CR
from . import envelope as E
from . import noise as N
from . import palette as PL
from . import shaping as S
from . import tone as TN
from . import triangle as T
from . import volume as V

# ------------------------------------------------------------------------------------------- shared by both tiers
SKY_ZENITH = np.array([0.0006, 0.0009, 0.0034])            # near black: no ambient wash
SKY_HORIZON = np.array([0.0016, 0.0024, 0.0068])
SKY_ROSE = np.array([0.0110, 0.0052, 0.0100])              # a sun a few degrees under the horizon, ahead right
TO_SUN = np.array([0.4741, -0.0569, -0.8786])
CORAL = np.array([0.7454, 0.1683, 0.0782])                 # the house accent token, linear (--wb-coral, #e0724f)
# palette choice -> (hem, body, crown) linear colours for palRamp3; choice 1 is the physical auroraLineColor
PALETTES = [
    (np.array([0.1873, 0.7106, 0.8689]), np.array([0.1960, 0.3672, 0.9331]), np.array([0.3424, 0.2049, 0.9331])),
    None,
    (np.array([0.0, 0.3801, 0.6921]), np.array([0.0072, 0.1193, 1.0]), np.array([0.0835, 0.0272, 0.8276])),
]
PHYSICAL = 1                                               # the default palette of both tiers: green body, red crown
GLOW_GAMMA = 1.25                                          # the glow lift (displayHueSafeGamma) of both tiers
LUMA = np.array([0.2126, 0.7152, 0.0722])                  # Rec. 709 luminance, for the fringe's yield
FRINGE_KM = 6.0                                            # the sheets' energetic layer is 6 fringe km thick
FRINGE_ALT_KM = 90.0                                       # auroraLineColor(90, 1) is the nitrogen fringe alone
FRINGE_SCALE_KM = 2.5                                      # its own auroraProfile scale height
FRINGE_GAIN = 1.6                                          # its brightness against the body's peak
FRINGE_YIELD = 0.05                                        # it gives way where other light passes this much of it
# the energetic stretches: the curtain cut into cells along it, each lit over a stretch of its own (never reaching the
# cell's ends) on its own slow life cycle, the whole drifting slowly along, so no piece outgrows its cell
STRETCH_LENGTH = (0.3, 0.4, 0.65)                          # a stretch is (0.3 + 0.4 dice) (0.65 + 0.35 fringe) cells
STRETCH_RAMP = 0.08                                        # its ends fade over this much of a cell
STRETCH_SHARE = (0.4, 0.4)                                 # a cell is lit for 0.4 + 0.4 fringe of its life cycle ...
STRETCH_FADE = 0.1                                         # ... fading in and out over this much of it
STRETCH_LIFE_S = 120.0                                     # a cell's life cycle, seconds of clock
STRETCH_DRIFT = 0.05                                       # cells per second the stretches drift along the curtain
STRETCH_SEED = 13.0                                        # hash33's third lane
WHITE_KNEE, WHITE_LIMIT = 0.2, 0.35                        # the lifted glow's weakest channel: knee and ceiling
WHITE_ARG_CAP = 10.0                                       # tanh's argument is clamped here (colour/tone.glsl, tmTanh)

# ------------------------------------------------------------------------------------------------- the band tier
BAND_GLOW_GAMMA = GLOW_GAMMA
BAND_KM_PER_UNIT = 300.0                                   # curtain units of height to kilometres, above the edge
BAND_EDGE_KM = 106.0                                       # the lower edge's altitude: oxygen's green is awake there
BAND_SCALE_H = 35.0                                        # the body fades by e every 35 km above the edge ...
BAND_RAY_SCALE_H = 70.0                                    # ... a ray's core by e every 70 km: rays outreach it
BAND_DEPTH_STOPS = 0.55                                    # the zoom gradient: 2^(0.55 x / aspect)
BAND_SWAY_FREQ = 0.7                                       # the hem's waves per curtain unit along it
BAND_SWAY_OCTAVES = 1                                      # one smooth octave: fabric on a line, not a skyline
BAND_HEM_SWAY = 0.08                                       # the hem wanders by at most this (warpFbm2 is within 1)
BAND_HEM_TILT = 0.18                                       # and drops by this per unit of depth beyond 1
BAND_CURTAIN_DROP = -0.42                                  # each curtain behind hangs this much lower: negative, higher
BAND_HEM_RAG_KM = 6.0                                      # creases hang at most this much lower than the hem
BAND_BORDER = (4.0, 1.5)                                   # the lower border: auroraProfile scale height, gain
BAND_BOW = (0.06, -0.25)                                   # the arc: how far its crest rises, where (u) it crests
BAND_STRAND_POWER = 2.4                                    # shpInvPower's steepness on the filament field
BAND_FABRIC_FLOOR = 0.08                                   # the faint drape between the filaments
BAND_RAY_GAIN = (0.08, 2.4)                                # between the rays, and in a ray's core: 0.08 + 2.4 ray
BAND_GAPS = (0.1, 0.75)                                    # envBreath through smoothstep: real gaps along it
BAND_GAP_RAMP = 0.2                                        # ... low-passed over this many frame units along x
BAND_GAP_WEIGHTS = (1.0, 2.0, 3.0, 4.0, 3.0, 2.0, 1.0)     # by seven samples, weighted as a triangle
BAND_FRINGE_KM = 3.0                                       # the fringe layer, fringe km at unit depth, times the scale:
#                                                            fringe / 200 of the frame's height at any depth (up to
#                                                            1.35 px at 270, at fringe 1)
BAND_STRETCH_FREQ = 3.0                                    # stretch cells per unit of frame x times the curtain's scale
BAND_FABRIC_KNEE = 0.25                                    # the fabric's soft cap: f / (1 + knee f)
BAND_GATHER_CAP = 2.2                                      # a fold seen edge-on gathers at most this much light
BAND_BREATH_SHIFT = 0.5                                    # each curtain breathes half a wave out of step
BAND_CHURN = 0.08                                          # the filament field's churn, per second of clock
BAND_RAY_PACE = 0.3                                        # auroraRays runs on 0.3 of the clock: rays drift slowly
BAND_HUE_KM = 110.0                                        # palRamp3 runs hem to crown over 106 to 216 km


def _smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=np.float64) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _sky(rd, sky):
    return max(float(sky), 0.0) * A.skyGradient(rd, TO_SUN, SKY_ZENITH, SKY_HORIZON, SKY_ROSE)


def _uv(pixel, res):
    return np.asarray(CR.uvCentered(np.asarray(pixel, dtype=np.float32), np.asarray(res, dtype=np.float32)),
                      dtype=np.float64)


def bandDepth(x, aspect):
    """The band's zoom gradient at frame x (a curtain recedes to the right: finer, shorter, lower)."""
    return np.exp2(BAND_DEPTH_STOPS * np.asarray(x, dtype=np.float64) / max(float(aspect), 1e-3))


def _band_hem(along, depth, u, clock, hemHeight, k):
    """The GLSL's inline `hem` for curtain k: where its lower edge hangs (frame y) at a place `along` it, u being the
    frame x over the aspect (-1 to 1 edge to edge)."""
    sway = N.warpFbm2(np.stack(np.broadcast_arrays(BAND_SWAY_FREQ * along + 0.013 * clock,
                                                   0.021 * clock + 1.7 + 0.0 * along), -1), 0.9, BAND_SWAY_OCTAVES, 7)
    bow = 1.0 - ((np.asarray(u, dtype=np.float64) - BAND_BOW[1]) / (1.0 + abs(BAND_BOW[1]))) ** 2
    return (-1.0 + hemHeight - BAND_CURTAIN_DROP * k + BAND_HEM_SWAY * sway / (1.0 + 0.8 * k)
            - BAND_HEM_TILT * (depth - 1.0) + BAND_BOW[0] * bow / (1.0 + 0.8 * k))


def bandHemLine(x, clock, hemHeight, curtainWidth, aspect=16.0 / 9.0, layer=0):
    """Where curtain `layer`'s hem hangs at frame x (uvCentered units, y from -1 at the bottom), before the creases rag
    it: the twin-only view of the GLSL's inline `hem`."""
    x = np.asarray(x, dtype=np.float64)
    k = float(layer)
    depth = bandDepth(x, aspect)
    along = x * depth * (1.0 + 0.8 * k) / max(float(curtainWidth), 0.05) + 17.3 * k
    return _band_hem(along, depth, x / max(float(aspect), 1e-3), clock, hemHeight, k)


def bandRag(x, aspect=16.0 / 9.0, layer=0):
    """How far below its hem line curtain `layer`'s ragged edge can reach at frame x (frame units)."""
    depth = bandDepth(x, aspect)
    return BAND_HEM_RAG_KM / BAND_KM_PER_UNIT / (depth * (1.0 + 0.8 * float(layer)))


def bandLowestHem(hemHeight, curtains, aspect=16.0 / 9.0):
    """A bound below every edge the band can hang (ragged creases included): no curtain emits anything lower."""
    lowest = []
    deepest = float(np.exp2(BAND_DEPTH_STOPS))
    for k in range(int(curtains)):
        lowest.append(-1.0 + hemHeight - BAND_CURTAIN_DROP * k - BAND_HEM_SWAY / (1.0 + 0.8 * k)
                      - BAND_HEM_TILT * (deepest - 1.0))
    rag = BAND_HEM_RAG_KM / BAND_KM_PER_UNIT / float(np.exp2(-BAND_DEPTH_STOPS))
    return min(lowest) - rag


def fringeKm(fringe, km=FRINGE_KM, scale=1.0):
    """The energetic layer's thickness under the body, in km above the lower edge: km x fringe x scale (a hair above 0
    at fringe 0). The sheets' layer is FRINGE_KM; the band's is BAND_FRINGE_KM times the curtain's scale (its depth),
    so it stands the same height on screen at every depth."""
    f = min(max(float(fringe), 0.0), 1.0)
    return np.maximum(float(km) * f * np.asarray(scale, dtype=np.float64), 1e-2)


def fringeLayer(zKm, fringe, km=FRINGE_KM, scale=1.0):
    """1 inside the energetic layer (the bottom half of its fringeKm), falling to 0 at its top; 0 everywhere at fringe
    0."""
    f = min(max(float(fringe), 0.0), 1.0)
    layer = fringeKm(fringe, km, scale)
    return _smoothstep(0.0, 0.25, f) * (1.0 - _smoothstep(0.5 * layer, layer, np.asarray(zKm, dtype=np.float64)))


def fringeEmission(zKm, fringe, km=FRINGE_KM, scale=1.0):
    """The energetic fringe's own brightness zKm above the curtain's lower edge: a thin emitter that rises at the edge
    (auroraProfile of zKm / scale, a 2.5 km scale height at unit depth) and is gone at the layer's top, where the body
    begins. A layer of its own UNDER the body, not a tint over it: summed with the body on the same pixels its
    near-complement colour would read as silver, so the two never share an altitude. With the band's scale, the layer
    and its profile both stretch with depth, so the fringe is the same shape on screen near and far."""
    z = np.asarray(zKm, dtype=np.float64)
    unit = z / np.asarray(scale, dtype=np.float64)
    return (FRINGE_GAIN * fringeLayer(z, fringe, km, scale)
            * np.asarray(A.auroraProfile(unit, 0.0, FRINGE_SCALE_KM), np.float64))


def fringeTint(palette):
    """The fringe's colour: the nitrogen purple for the physical palette (auroraLineColor at 90 km, where nothing else
    glows), else the house coral."""
    if int(palette) == PHYSICAL:
        return np.asarray(A.auroraLineColor(FRINGE_ALT_KM, 1.0), dtype=np.float64)
    return CORAL


def fringeStretches(at, lane, fringe, clock):
    """How energetic the curtain is at `at` (a coordinate along it, in cells), 0 to 1: the curtain is cut into cells,
    and each cell (dice from hash33 of (cell, lane, 13), lane being the curtain's or the arc's index) is lit over one
    stretch of its own, (0.3 + 0.4 dice) (0.65 + 0.35 fringe) of the cell long, placed at random but never reaching the
    cell's ends, its ends fading over 0.08 of a cell; each cell is lit for 0.4 + 0.4 fringe of its own 120 s life
    cycle (fading in and out over a tenth of it), and the whole drifts along at 0.05 cells a second. The stretches
    cover about 14 per cent of its length at 0.35, 30 at 1 (the mean over 4000 cells and ten minutes, measured: 13.5
    and 29.5). A piece is never longer than 0.7 of its cell at any clock, and two pieces never touch: a smooth noise
    through a threshold joined its lit runs into 40 to 70 per cent of the frame at most clocks. The lower border of a
    real display lights only under its energetic stretches: drawn the whole length of every hem, the fringe reads as a
    glowing outline."""
    from . import hash as HS
    f = min(max(float(fringe), 0.0), 1.0)
    at = np.asarray(at, dtype=np.float64) - STRETCH_DRIFT * float(clock)
    cell = np.floor(at)
    inside = at - cell
    lanes = np.broadcast_to(np.asarray(lane, dtype=np.float64), at.shape)
    dice = np.asarray(HS.hash33(np.stack([cell, lanes, np.full_like(at, STRETCH_SEED)], -1)), np.float64)
    length = ((STRETCH_LENGTH[0] + STRETCH_LENGTH[1] * dice[..., 1])
              * (STRETCH_LENGTH[2] + (1.0 - STRETCH_LENGTH[2]) * f))
    start = 0.5 + (dice[..., 2] - 0.5) * (0.8 - length) - 0.5 * length
    dash = (_smoothstep(start, start + STRETCH_RAMP, inside)
            * (1.0 - _smoothstep(start + length - STRETCH_RAMP, start + length, inside)))
    life = np.mod(dice[..., 0] + float(clock) / STRETCH_LIFE_S, 1.0)
    share = STRETCH_SHARE[0] + STRETCH_SHARE[1] * f
    lit = _smoothstep(0.0, STRETCH_FADE, life) * (1.0 - _smoothstep(share - STRETCH_FADE, share, life))
    return dash * lit


def fringeYield(otherLight, fringePeak, share=FRINGE_YIELD):
    """1 where the fringe's own peak brightness (luminance) outshines all the other aurora light on the pixel, falling
    to 0 where that light reaches `share` of it (the band's FRINGE_YIELD, the sheets' SHEET_FRINGE_YIELD).
    Near-complements summed on one pixel read as silver and then white (a near curtain's coral or purple edge across a
    far curtain's cyan or green body): the fringe shows against the dark sky and gives way to any drape behind it."""
    ratio = (np.asarray(otherLight, np.float64) @ LUMA) / np.maximum(np.asarray(fringePeak, np.float64), 1e-9)
    return 1.0 - _smoothstep(0.0, share, ratio)


def whiteCap(glow):
    """The ceiling under white: where the lifted glow's weakest channel passes WHITE_KNEE, the whole colour is scaled
    so that channel eases toward WHITE_LIMIT along a tanh shoulder (identity and slope 1 at the knee). Hue and
    saturation are kept; only a hot spot's magnitude gives way, so it stays coloured through the display curve. The
    tanh's argument is clamped at 10 (where tanh is 1 in a float), as the house's tmTanh does: some drivers build tanh
    from exponentials that overflow to NaN past about 88."""
    glow = np.asarray(glow, dtype=np.float64)
    weakest = glow.min(-1)
    span = WHITE_LIMIT - WHITE_KNEE
    eased = WHITE_KNEE + span * np.tanh(np.minimum(np.maximum(weakest - WHITE_KNEE, 0.0) / span, WHITE_ARG_CAP))
    return glow * np.where(weakest > WHITE_KNEE, eased / np.maximum(weakest, 1e-6), 1.0)[..., None]


def bandHue(altKm, palette):
    """The band body's hue at an altitude (before brightness): auroraLineColor (green body, red crown) for the physical
    palette, else palRamp3 from the edge's 106 km to 216 km."""
    alt = np.asarray(altKm, dtype=np.float64)
    if int(palette) == PHYSICAL:
        return np.asarray(A.auroraLineColor(alt, 0.0), dtype=np.float64)
    a, b, c = PALETTES[2 if int(palette) == 2 else 0]
    return PL.palRamp3((alt - BAND_EDGE_KM) / BAND_HUE_KM, a, b, c)


def _breath(x, clock):
    x = np.asarray(x, dtype=np.float64)
    once, back = np.unique(x, return_inverse=True)         # the breathing is a function of x alone: read each once
    values = np.array([E.envBreath(float(v), float(clock), (0.017, 0.053)) for v in once])
    return values[back].reshape(x.shape)


def bandGapGate(along, scale, curtainWidth, layer, clock):
    """The band's gaps along curtain `layer`: smoothstep(0.1, 0.75) of envBreath (real gaps, each curtain half a wave
    out of step), low-passed along the frame by seven samples spread over BAND_GAP_RAMP frame units and weighted as a
    triangle. The breathing alone climbs from a gap to half of full in 2 to 5 px at the card size where its fast
    patches cross the threshold (and in under a pixel at curtain width 0.3): straight walls the curtain's full height.
    Low-passed, a curtain's end fades over at least 8 px at 480 x 270."""
    centre = 0.31 * np.asarray(along, dtype=np.float64) + BAND_BREATH_SHIFT * float(layer)
    per_unit = 0.31 * np.asarray(scale, dtype=np.float64) / max(float(curtainWidth), 0.05)
    gate = 0.0
    taps = len(BAND_GAP_WEIGHTS)
    for tap, weight in enumerate(BAND_GAP_WEIGHTS):
        offset = (tap / (taps - 1) - 0.5) * BAND_GAP_RAMP
        gate = gate + weight * _smoothstep(BAND_GAPS[0], BAND_GAPS[1], _breath(centre + per_unit * offset, clock))
    return gate / sum(BAND_GAP_WEIGHTS)


def auroraBand(pixel, res, clock, intensity, hemHeight, curtainWidth, fold, rays, fringe, palette, sky, curtains,
               view):
    """The twin of auroraBand: the sky plus up to three painted curtains, scene-linear, shape (..., 3)."""
    res = np.asarray(res, dtype=np.float64)
    p = _uv(pixel, res)
    width = max(float(curtainWidth), 0.05)
    rd = np.stack([p[..., 0], p[..., 1] + 1.0, np.full(p.shape[:-1], -1.6)], -1)
    rd = rd / np.linalg.norm(rd, axis=-1, keepdims=True)
    backdrop = _sky(rd, sky)
    depth = bandDepth(p[..., 0], res[0] / res[1])
    push = 0.55 * float(fold)
    tint = fringeTint(palette)
    body_light = np.zeros(p.shape[:-1] + (3,))
    fringe_light = np.zeros_like(body_light)
    fringe_peak = np.zeros(p.shape[:-1])
    fabric_sum = np.zeros(p.shape[:-1])
    for layer in range(min(max(int(curtains), 0), 3)):
        k = float(layer)
        scale = depth * (1.0 + 0.8 * k)
        share = 1.0 / (1.0 + 1.5 * k)
        along = p[..., 0] * scale / width + 17.3 * k
        hem = _band_hem(along, depth, p[..., 0] / max(res[0] / res[1], 1e-3), clock, hemHeight, k)
        above = (p[..., 1] - hem) * scale
        fold_at = np.stack([0.9 * along - 0.017 * clock, 0.35 * above + 0.011 * clock + 3.7], -1)
        bend = N.warpFbm2(fold_at, 1.1, 3, 19)
        stretch = 1.0 + push * (N.warpFbm2(fold_at + np.array([0.027, 0.0]), 1.1, 3, 19) - bend) / 0.03
        gather = np.minimum(1.0 / np.maximum(np.abs(stretch), 1e-3), BAND_GATHER_CAP)
        folded = along + push * bend
        n = np.asarray(T.noiseTriangle2(np.stack([2.2 * folded, 0.8 * above], -1), BAND_CHURN * clock, 4),
                       np.float64)
        strands = np.asarray(S.shpInvPower(n + 0.02, 0.2, BAND_STRAND_POWER), np.float64)
        strands = strands / (1.0 + 0.3 * strands)
        ray = np.asarray(A.auroraRays(2.3 * folded, BAND_RAY_PACE * clock, 3), np.float64)
        ray_mix = min(max(float(rays), 0.0), 1.0)
        ray_gain = (1.0 - ray_mix) + ray_mix * (BAND_RAY_GAIN[0] + BAND_RAY_GAIN[1] * ray)
        fabric = (BAND_FABRIC_FLOOR + strands) * ray_gain * gather
        fabric = fabric / (1.0 + BAND_FABRIC_KNEE * fabric)
        fabric_sum = fabric_sum + share * fabric
        alt = BAND_EDGE_KM + BAND_KM_PER_UNIT * above
        edge = BAND_EDGE_KM + 2.0 * BAND_HEM_RAG_KM * (n - 0.5)
        tall = BAND_SCALE_H + (BAND_RAY_SCALE_H - BAND_SCALE_H) * (ray_mix * ray)
        # the body begins where the fringe layer ends; the layer is BAND_FRINGE_KM x fringe at unit depth, times the
        # scale, so it stands fringe / 200 of the frame's height at every depth
        start = edge + fringeKm(fringe, BAND_FRINGE_KM, scale)
        profile = (np.asarray(A.auroraProfile(alt, start, tall), np.float64)
                   + BAND_BORDER[1] * np.asarray(A.auroraProfile(alt, start, BAND_BORDER[0]), np.float64))
        hue = bandHue(alt, palette)
        low = fringeEmission(alt - edge, fringe, BAND_FRINGE_KM, scale)
        if int(view) == 2:
            body_light = body_light + share * hue * profile[..., None]
            fringe_light = fringe_light + share * tint * low[..., None]
            continue
        gate = bandGapGate(along, scale, width, k, clock)
        # the stretches are cells along frame x times the scale, not along `along`: a fixed length on screen at this
        # depth, whatever the curtain's width
        energetic = fringeStretches(BAND_STRETCH_FREQ * p[..., 0] * scale, k, fringe, clock)
        body_light = body_light + share * hue * (profile * fabric * gate)[..., None]
        energy = share * fabric * gate * energetic
        fringe_light = fringe_light + tint * (energy * low)[..., None]
        fringe_peak = fringe_peak + FRINGE_GAIN * float(tint @ LUMA) * energy
    if int(view) == 1:
        return np.repeat((0.25 * fabric_sum)[..., None], 3, axis=-1)
    if int(view) != 2:
        fringe_light = fringe_light * fringeYield(body_light, fringe_peak)[..., None]
    glow = TN.displayHueSafeGamma(max(float(intensity), 0.0) * (body_light + fringe_light), GLOW_GAMMA)
    return backdrop + whiteCap(glow)


# ------------------------------------------------------------------------------------------------ the sheet tier
SHEET_BOWL = (2.0, 0.4)                                    # the planes are met along (rd.x, 2 rd.y + 0.4, rd.z)
SHEET_TOP = 0.32                                           # the stack rises this fraction of the hem height
SHEET_POWER = 1.35                                         # marchStepPoly's spacing power
SHEET_EDGE_KM = BAND_EDGE_KM                               # the lowest sheet's altitude, as in the band
SHEET_KM = 160.0                                           # the stack's height in kilometres above it
SHEET_SCALE_H = 35.0
SHEET_KEEP_LAYERS = 16.0                                   # keep = 2^(-16 / layers): the running average's retention
SHEET_GAIN = 2.0
SHEET_HORIZON_FADE = 0.16
SHEET_HUE_RATE = 1.8                                       # palRamp3 reaches the crown colour at 1 / 1.8 of the stack
SHEET_CHURN = 0.035                                        # the filament field's churn, per second of clock
SHEET_RAY_PACE = 0.3                                       # auroraRays runs on 0.3 of the clock: rays drift slowly
SHEET_ARCS = (0.9, 0.009, 0.004)                           # arcs per curtain width of depth, thickness, drift / s
SHEET_ARC_RIPPLE = 0.5                                     # how far the filament field ripples an arc (x fold)
SHEET_ARC_GAIN = 1.5                                       # the arc's own thin curtain, under its creases
SHEET_BAND = 0.2                                           # the creases live within this of an arc (in periods)
SHEET_RAYS = (9.0, 0.08, 2.4)                              # rays per curtain width along, between, core gain
SHEET_LOD = (0.3, 0.8)                                     # crease cycles per pixel where the creases fade out
SHEET_STRAND_MEAN = 0.02                                   # the carved field's mean, what a fine footprint fades to
SHEET_STRETCH_FREQ = 3.0                                   # stretch cells per unit of plan x over the hem's height
SHEET_FRINGE_GAIN = 4.8                                    # the brightest fringe sheet's light (never the sheets' sum)
# The sheets' yield is a safety margin, not load-bearing: at 0.01 (its value before 1.3.0) every pin still holds. What
# 0.004 buys is the half-faded third pixel of edge where a drape lies behind the fringe. Measured with the pins' own
# mask over the 24 fringe clocks (2026-10-13): on the narrowest curtain 5 of 4977 fringe pixels stand 3 px across at
# 0.01, 0 of 3045 at 0.004; with every knob at its top (palette 2), 121 of 8387 against 6 of 5583, the 95th percentile
# at that pin's limit of 3 px at four clocks against one. It also draws a third fewer fringe pixels (2019 against 3038
# at the default width), so a change to it is a change to the look.
SHEET_FRINGE_YIELD = 0.004                                 # it gives way where the drape passes this share of its peak
SHEET_FOLD_GATE = (4.0, 6.0)                               # ... and where the arc's band at the hem stands this tall
#                                                            on screen, in 1 / 270 of the frame (a fold seen edge-on)
SHEET_FRINGE_RAYS = 0.5                                    # the fringe follows the rays this far (the body: fully)


def sheetHue(frac, palette):
    """A sheet's hue by its height in the stack (0 the hem, 1 the top sheet): auroraLineColor from 106 to 266 km for
    the physical palette, else palRamp3."""
    frac = np.asarray(frac, dtype=np.float64)
    if int(palette) == PHYSICAL:
        return np.asarray(A.auroraLineColor(SHEET_EDGE_KM + SHEET_KM * frac, 0.0), dtype=np.float64)
    a, b, c = PALETTES[2 if int(palette) == 2 else 0]
    return PL.palRamp3(SHEET_HUE_RATE * frac, a, b, c)


def _cam_ray(pixel, res, basis, focal):
    uv = _uv(pixel, res)
    local = np.stack([uv[..., 0], uv[..., 1], np.full(uv.shape[:-1], -float(focal))], -1)
    through = local @ np.asarray(basis, dtype=np.float64).T
    return through / np.linalg.norm(through, axis=-1, keepdims=True)


def _plane_t(ro, bowed, h):
    """ixPlane(ro, bowed, up, -h) for every pixel: (h - ro.y) / bowed.y, or -1 when parallel or behind."""
    facing = bowed[..., 1]
    safe = np.where(np.abs(facing) < 1e-8, 1.0, facing)
    t = (h - ro[1]) / safe
    return np.where((np.abs(facing) < 1e-8) | (t < 0.0), -1.0, t)


def _strands(n):
    s = np.maximum(np.asarray(S.shpRemap(np.asarray(S.shpInvPower(n + 0.012, 0.12, 3.0), np.float64),
                                         0.15, 1.15, 0.0, 1.0), np.float64), 0.0)
    return s / (1.0 + 0.3 * s)


def sheetJitter(pixel):
    """The static per-pixel fraction of a gap each sheet is read higher: dthIgn, its phase scrambled per 2 x 2 tile by
    hash22. Plain IGN is one long diagonal ramp folded 53 times, and in a static stack its lines show as a regular
    hatching; scrambled per tile they break into grain, while neighbours inside a tile keep IGN's spread."""
    from . import hash as HS
    pixel = np.asarray(pixel, dtype=np.float64)
    phase = np.floor(64.0 * np.asarray(HS.hash22(np.floor(pixel / 2.0).astype(np.float32)), np.float64))
    return np.asarray(N.dthIgn(pixel + phase), np.float64)


def sheetReach(look, bowed, ro, hem, width, res, focal):
    """How much plan depth (in curtain widths) one pixel spans on the hem's sheet: 2 |look.z| (hem - ro.y) / bowed.y^2
    / width, times the pixel's angle 2 / (res.y focal). Large near the horizon, where the bowl packs depth together."""
    pixel_angle = 2.0 / (float(res[1]) * float(focal))
    return (2.0 * np.abs(look[..., 2]) * (hem - ro[1]) / np.maximum(bowed[..., 1] * bowed[..., 1], 1e-6)
            / width * pixel_angle)


def sheetFine(reach):
    """1 where one pixel spans few of the footprint's creases, 0 where it spans more than SHEET_LOD[1] of one (the
    finest crease frequency is about 4 per curtain width)."""
    return 1.0 - _smoothstep(SHEET_LOD[0], SHEET_LOD[1], 4.0 * np.asarray(reach, dtype=np.float64))


def sheetFootprint(spot, bend, fold, clock, fine, reach, gap):
    """The footprint at a sheet point (spot in curtain widths on the ground plan): a few long arcs, each a thin curtain
    along a line of constant depth that meanders with the fold field and ripples with the filament field, with its own
    strength, and the filament field's creases lit only near the arcs. The arc is at least as thick as the plan depth
    one pixel spans (reach) and as the gap to the next sheet (gap), keeping its light as it widens, and the creases fade
    to their mean where a pixel spans too many (fine): a far curtain blurs instead of aliasing, and the stack shows one
    drape, not a pile of lines."""
    return _sheet_footprint(spot, bend, fold, clock, fine, reach, gap)[0]


def _sheet_footprint(spot, bend, fold, clock, fine, reach, gap):
    """sheetFootprint, and the arc coordinate there (it climbs by 1 from one arc to the next)."""
    from . import hash as HS
    spot = np.asarray(spot, dtype=np.float64)
    n = np.asarray(T.noiseTriangle2(np.stack([0.18 * spot[..., 0], 1.6 * spot[..., 1] + 0.9 * fold * bend], -1),
                                    SHEET_CHURN * clock, 3), np.float64)
    strands = SHEET_STRAND_MEAN + (_strands(n) - SHEET_STRAND_MEAN) * fine
    arc = (SHEET_ARCS[0] * spot[..., 1] + 0.5 * fold * bend + SHEET_ARC_RIPPLE * fold * (n - 0.5)
           + SHEET_ARCS[2] * clock)
    lane = np.abs(arc - np.floor(arc + 0.5))
    blur = np.sqrt(SHEET_ARCS[1] ** 2 + (SHEET_ARCS[0] * reach) ** 2 + (SHEET_ARCS[0] * gap) ** 2)
    curtain = (SHEET_ARCS[1] / blur) * np.exp(-(lane / blur) ** 2)
    band = np.exp(-(lane / SHEET_BAND) ** 2)
    which = np.stack([np.floor(arc + 0.5), np.full_like(arc, 3.0)], -1).astype(np.float32)
    strength = 0.35 + 0.65 * np.asarray(HS.hash21(which), np.float64)
    return (band * strands + SHEET_ARC_GAIN * curtain) * strength, arc


def sheetFoldGate(pixel, res, ro, basis, focal, water, hemSpot, bend, reach, hem, width, fold, clock):
    """1 where an arc's band at the hem's sheet is a thin line on screen, falling to 0 where it stands SHEET_FOLD_GATE
    (4 to 6) card pixels tall or more (a card pixel being 1 / 270 of the frame's height): a fold seen edge-on, where
    the arc runs along the line of sight. There its lower border is a floor seen from below, not an edge, and a fringe
    on it is a blob up to 10 px across. How tall: twice the band's own half-width at the hem, length(0.009, 0.9 reach),
    over how much its smooth part (0.9 spot.y + 0.5 fold bend, without the filament ripple) changes one card pixel up
    the frame (the ray there mirrored too below the horizon, met on the hem's sheet, its own bend read there)."""
    pixel = np.asarray(pixel, dtype=np.float64)
    up = _cam_ray(pixel + np.array([0.0, float(res[1]) / 270.0]), res, basis, focal)
    up = np.where(np.asarray(water)[..., None], up * np.array([1.0, -1.0, 1.0]), up)
    up_bowed = up * np.array([1.0, SHEET_BOWL[0], 1.0]) + np.array([0.0, SHEET_BOWL[1], 0.0])
    t_up = np.maximum(_plane_t(ro, up_bowed, hem), 0.0)
    up_spot = (ro[[0, 2]] + up[..., [0, 2]] * t_up[..., None]) / width
    up_bend = N.warpFbm2(np.stack([0.35 * up_spot[..., 0] + 0.011 * clock, 0.8 * up_spot[..., 1] - 0.007 * clock], -1),
                         1.0, 3, 23)
    here = SHEET_ARCS[0] * hemSpot[..., 1] + 0.5 * fold * bend
    above = SHEET_ARCS[0] * up_spot[..., 1] + 0.5 * fold * up_bend
    band = 2.0 * np.sqrt(SHEET_ARCS[1] ** 2 + (SHEET_ARCS[0] * np.asarray(reach, np.float64)) ** 2)
    standing = band / np.maximum(np.abs(above - here), 1e-6)
    return 1.0 - _smoothstep(SHEET_FOLD_GATE[0], SHEET_FOLD_GATE[1], standing)


def auroraSheets(pixel, res, ro, basis, focal, clock, intensity, hemHeight, curtainWidth, fold, rays, fringe, palette,
                 sky, lake, layers, view):
    """The twin of auroraSheets: the sky (or its mirror in the lake) plus the stacked curtains, shape (..., 3)."""
    ro = np.asarray(ro, dtype=np.float64)
    res = np.asarray(res, dtype=np.float64)
    rd = _cam_ray(pixel, res, basis, focal)
    water = rd[..., 1] < 0.0
    look = np.where(water[..., None], rd * np.array([1.0, -1.0, 1.0]), rd)
    reflect = np.where(water, float(lake), 1.0)
    backdrop = _sky(look, sky)
    bowed = look * np.array([1.0, SHEET_BOWL[0], 1.0]) + np.array([0.0, SHEET_BOWL[1], 0.0])
    count = min(max(int(layers), 1), 48)
    width = max(float(curtainWidth), 0.05)
    hem = max(float(hemHeight), 0.05)
    jitter = np.zeros(look.shape[:-1]) if int(view) in (2, 4) else sheetJitter(pixel)
    t_hem = np.maximum(_plane_t(ro, bowed, hem), 0.0)
    hem_spot = (ro[[0, 2]] + look[..., [0, 2]] * t_hem[..., None]) / width
    bend = N.warpFbm2(np.stack([0.35 * hem_spot[..., 0] + 0.011 * clock, 0.8 * hem_spot[..., 1] - 0.007 * clock], -1),
                      1.0, 3, 23)
    reach = sheetReach(look, bowed, ro, hem, width, res, focal)
    fine = sheetFine(reach)
    ray_mix = min(max(float(rays), 0.0), 1.0)
    top = SHEET_TOP * hem
    spacing = top / float(max(count - 1, 1)) ** SHEET_POWER
    keep = 2.0 ** (-SHEET_KEEP_LAYERS / count)
    tint = fringeTint(palette)
    fold_gate = 1.0
    if float(fringe) > 0.0:
        fold_gate = sheetFoldGate(pixel, res, ro, basis, focal, water, hem_spot, bend, reach, hem, width, fold, clock)
    drape = np.zeros(look.shape[:-1] + (3,))
    light = np.zeros_like(drape)
    fringe_light = np.zeros_like(drape)
    fringe_peak = np.zeros(look.shape[:-1])
    weights = np.zeros(look.shape[:-1])
    height_sum = np.zeros_like(weights)
    strand_sum = np.zeros_like(weights)
    for i in range(count):
        base = V.marchStepPoly(i, hem, spacing, SHEET_POWER)
        step = V.marchStepPoly(i + 1, hem, spacing, SHEET_POWER) - base
        h = base + jitter * step
        t = _plane_t(ro, bowed, h)
        spot = (ro[[0, 2]] + look[..., [0, 2]] * t[..., None]) / width
        gap = np.abs(look[..., 2]) * step / np.maximum(bowed[..., 1], 1e-6) / width
        foot, arc = _sheet_footprint(spot, bend, fold, clock, fine, reach, gap)
        if int(view) == 2:
            return _no_lake(np.repeat((0.3 * foot)[..., None], 3, axis=-1), water, rd, sky, lake)
        ray = np.asarray(A.auroraRays(SHEET_RAYS[0] * spot[..., 0], SHEET_RAY_PACE * clock, 5), np.float64)
        strands = foot * ((1.0 - ray_mix) + ray_mix * (SHEET_RAYS[1] + SHEET_RAYS[2] * ray))
        frac = (h - hem) / top
        alt = SHEET_EDGE_KM + SHEET_KM * frac
        layer = fringeLayer(alt - SHEET_EDGE_KM, fringe)
        sheet = sheetHue(frac, palette) * (strands * (1.0 - layer))[..., None]
        drape = sheet if int(view) == 3 else sheet * (1.0 - keep) + drape * keep
        w = A.auroraProfile(alt, SHEET_EDGE_KM, SHEET_SCALE_H)
        body = A.auroraProfile(alt, SHEET_EDGE_KM + fringeKm(fringe), SHEET_SCALE_H)
        light = light + drape * body[..., None]
        if np.any(layer > 0.0):                             # the GLSL reads the fringe only where the layer is
            # the brightest fringe sheet, never their sum: a fold seen edge-on stacks every fringe sheet on one pixel
            # (a hot blob), and a sum would make the fringe's exposure follow the layer count
            energetic = fringeStretches(SHEET_STRETCH_FREQ * spot[..., 0] * width / hem, np.floor(arc + 0.5), fringe,
                                        clock)
            # the rays only halfway: under full rays the fringe broke into crumbs a ray wide
            soft = SHEET_FRINGE_RAYS * ray_mix
            edge_lit = foot * ((1.0 - soft) + soft * (SHEET_RAYS[1] + SHEET_RAYS[2] * ray))
            energy = edge_lit * layer * energetic * fold_gate
            low = SHEET_FRINGE_GAIN * energy * np.asarray(A.auroraProfile(alt, SHEET_EDGE_KM, FRINGE_SCALE_KM),
                                                           np.float64)
            fringe_light = np.maximum(fringe_light, tint * low[..., None])
            fringe_peak = np.maximum(fringe_peak, SHEET_FRINGE_GAIN * float(tint @ LUMA) * energy)
        weights = weights + w
        height_sum = height_sum + frac * strands * w
        strand_sum = strand_sum + strands * w
    weights = np.maximum(weights, 1e-6)
    if int(view) == 1:
        heat = (np.asarray(CR.dbgHeatRamp(height_sum / np.maximum(strand_sum, 1e-6)), np.float64)
                * np.minimum(strand_sum / weights, 1.0)[..., None])
        return _no_lake(heat, water, rd, sky, lake)
    light = light + fringe_light * fringeYield(light, fringe_peak, SHEET_FRINGE_YIELD)[..., None]
    fade = _smoothstep(0.0, SHEET_HORIZON_FADE, look[..., 1])
    gain = SHEET_GAIN * max(float(intensity), 0.0) * fade / weights
    light = whiteCap(TN.displayHueSafeGamma(gain[..., None] * light, GLOW_GAMMA))
    return _no_lake(reflect[..., None] * (backdrop + light), water, rd, sky, lake)


def _no_lake(out, water, rd, sky, lake):
    """With no lake (lake <= 0) a pixel below the horizon is the sky's own colour there, whatever the view."""
    if float(lake) > 0.0:
        return out
    return np.where(water[..., None], _sky(rd, sky), out)
