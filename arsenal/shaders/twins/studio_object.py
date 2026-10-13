"""CPU twin of groups/studio-object.glsl, the studio-object group recipe (atlas section 16.5): studioObjectRig,
studioObjectBare, studioObjectSurface, studioObjectFloor and studioObject. Pinned by
tests/test_glsl_twins_groups_neon_studio_hex.py, which also holds the GLSL to this twin on SwiftShader.

WHY. A studio render can look plausible while lying: a floor lit where the object should shadow it, a horizon line
where the floor meets the backdrop, a glossy black object that reflects nothing, a silhouette cut by a hard step. Each
of those is a number this twin can produce and a test can check. It is built from the twins of the parts the recipe
calls (the camera, the march, the normal and the coverage from ray.py; the rig, the studio, the shadow and the occlusion
from light.py; the box from sdf.py; the fog from atmos.py; the debug views from core.py), so a change there reaches
this file the way it reaches the shader.

The host's hooks are Python callables passed LAST, as the ray and light twins take theirs: mapScene(p) -> float and
materialAt(p, n, id) -> rgb. One pixel per call (the march is a loop), in float64 around the float32 parts.

Apache-2.0, Akashic Aurora. Written fresh from the recipe's contract; no corpus code.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from arsenal.shaders.twins import atmos, colour, core, light, ray, sdf

UP = np.array([0.0, 1.0, 0.0])
SHADOW_STEPS = 48
AO_FALLOFF = 0.85


def _v(x):
    return np.asarray(x, dtype=np.float64)


def studioObjectRig(keyTurn, keyElevation, boxSize, poolRadius, floorDrop) -> light.StudioParams:
    """light-env's neutral studio with the key at keyTurn turns about y from +z and keyElevation degrees up; the fill
    0.51 turns round from it at 33.4 degrees."""
    yaw = 2.0 * math.pi * float(keyTurn)
    pitch = math.radians(min(max(float(keyElevation), 0.0), 89.0))
    key = np.array([math.cos(pitch) * math.sin(yaw), math.sin(pitch), math.cos(pitch) * math.cos(yaw)])
    fill_yaw = yaw + 0.51 * 2.0 * math.pi
    fill_pitch = math.radians(33.4)
    fill = np.array([math.cos(fill_pitch) * math.sin(fill_yaw), math.sin(fill_pitch),
                     math.cos(fill_pitch) * math.cos(fill_yaw)])
    size = min(max(float(boxSize), 0.05), 1.2)
    return light.StudioParams(keyDir=key, keyCol=_v([3.6, 3.3, 2.9]), fillDir=fill, fillCol=_v([0.55, 0.7, 1.0]),
                              boxSize=_v([size, 0.66 * size]), rimBright=0.8, skyCol=_v([0.008, 0.01, 0.016]),
                              horizonCol=_v([0.07, 0.075, 0.09]), floorCol=_v([0.32, 0.27, 0.22]),
                              floorDrop=max(float(floorDrop), 0.0), poolRadius=max(float(poolRadius), 1e-3),
                              keyWrap=0.3)


def studioObjectBare(sp: light.StudioParams) -> light.StudioParams:
    """The studio with its soft boxes and its floor pool off: the wall behind the object."""
    return replace(sp, keyCol=np.zeros(3), fillCol=np.zeros(3), floorCol=np.zeros(3))


def studioObjectSurface(p, n, toEye, sp, fresnelFloor, metal, roughness, shadow, ao, materialAt):
    """rigStudio on the host's colour: diffuse = colour (1 - metal), F0 = mix(fresnelFloor, colour, metal),
    alpha = roughness^2, the key scaled by the shadow."""
    base = np.maximum(_v(materialAt(_v(p), _v(n), 0.0)), 0.0)
    metalness = min(max(float(metal), 0.0), 1.0)
    rough = min(max(float(roughness), 0.0), 1.0)
    f0 = np.full(3, min(max(float(fresnelFloor), 0.0), 1.0)) * (1.0 - metalness) + base * metalness
    surface = light.LitSurface(diffuseColor=base * (1.0 - metalness), F0=f0, alpha=rough * rough)
    lit = replace(sp, keyCol=sp.keyCol * min(max(float(shadow), 0.0), 1.0))
    return _v(light.rigStudio(surface, _v(n), _v(toEye), ao, lit))


def studioObjectFloor(pf, toEye, target, sp, shadow, ao, materialAt):
    """A satin of the host's floor colour: key and fill reach as far as the pool, the key through the shadow; plus the
    studio's warm pool times the occlusion."""
    base = np.maximum(_v(materialAt(_v(pf), UP, 1.0)), 0.0)
    reach = float(light.litFloorPool(pf, target, sp.poolRadius, np.ones(3))[0])
    lit = replace(sp, keyCol=sp.keyCol * min(max(float(shadow), 0.0), 1.0) * reach, fillCol=sp.fillCol * reach)
    satin = light.LitSurface(diffuseColor=base, F0=np.full(3, 0.04), alpha=0.5)
    shade = _v(light.rigStudio(satin, UP, _v(toEye), ao, lit))
    return shade + base * _v(light.litFloorPool(pf, target, sp.poolRadius, sp.floorCol)) * min(max(float(ao), 0.0), 1.0)


def studioObject(ro, target, pixel, res, lens, keyTurn, keyElevation, boxSize, backdrop, fresnelFloor, metal, roughness,
                 shadowAngle, aoReach, poolRadius, floorDrop, bound, steps, omega, view, mapScene, materialAt):
    """Linear radiance for one pixel of a camera at ro looking at target, in the studio the knobs set."""
    ro, target = _v(ro), _v(target)
    basis = ray.camLookAt(ro, target, 0.0)
    focal = max(float(lens), 0.1)
    rd = _v(ray.camRay(_v(pixel), _v(res), basis, focal))
    pixel_angle = float(ray.camPixelAngle(2.0 * math.atan(1.0 / focal), float(res[1])))
    box_half = np.full(3, max(float(bound), 1e-3))
    if view == 5:
        half_height = float(np.linalg.norm(target - ro)) / focal
        b = _v(basis)

        def slice_at(px_, py_):
            uv = (2.0 * np.array([px_, py_]) - _v(res)) / float(res[1]) * half_height
            return float(mapScene(target + b[:, 0] * uv[0] + b[:, 1] * uv[1]))

        d = slice_at(pixel[0], pixel[1])
        fp = math.hypot(slice_at(pixel[0] + 1.0, pixel[1]) - d, slice_at(pixel[0], pixel[1] + 1.0) - d)
        return colour.srgbDecode(_v(core.dbgSlice(d, 0.1 * box_half[0], fp)))
    sp = studioObjectRig(keyTurn, keyElevation, boxSize, poolRadius, floorDrop)
    light_angle = math.radians(min(max(float(shadowAngle), 0.05), 60.0))
    budget = int(min(max(float(steps), 1.0), 256.0))

    behind = _v(light.litStudioEnv(rd, 0.0, studioObjectBare(sp))) * min(max(float(backdrop), 0.0), 1.0)
    t_floor = float(ray.ixPlane(ro, rd, UP, sp.floorDrop - target[1]))
    floor_shadow, floor_ao = 1.0, 1.0
    if t_floor > 0.0:
        pf = ro + rd * t_floor
        to_key = ray.rmClipToBox(pf, sp.keyDir, target, box_half, (1e-3, 1e3))
        if to_key[0] <= to_key[1]:
            floor_shadow = light.visSoftShadow(mapScene, pf, sp.keyDir, to_key, light_angle, SHADOW_STEPS)
        if float(sdf.sdBox(pf - target, box_half)) < max(float(aoReach), 0.0):
            floor_ao = light.visAO(mapScene, pf, UP, aoReach, AO_FALLOFF)
        ground = studioObjectFloor(pf, -rd, target, sp, floor_shadow, floor_ao, materialAt)
        past_pool = max(math.hypot(pf[0] - target[0], pf[2] - target[2]) - sp.poolRadius, 0.0)
        behind = _v(atmos.fogExp(ground, behind, past_pool, 0.45 / sp.poolRadius))

    span = ray.rmClipToBox(ro, rd, target, box_half, (0.0, t_floor if t_floor > 0.0 else 1e4))
    trace = np.array([0.0, 0.0, 1e10, 0.0])
    if span[0] <= span[1]:
        trace = _v(ray.rmSphereTrace(ro, rd, span, pixel_angle, omega, budget, mapScene))
    cover = 1.0 if trace[3] > 0.5 else float(ray.aaConeCoverage(trace[2], pixel_angle))
    n, shadow, ao, picture = UP, floor_shadow, floor_ao, behind
    if cover > 0.0:
        p = ro + rd * trace[0]
        n = _v(ray.nrmTetra(p, ray.nrmEps(trace[0], pixel_angle, 1.0), mapScene))
        lifted = p + n * (4.0 * float(ray.rmEpsilon(trace[0], pixel_angle, 1e-4)))
        to_key = ray.rmClipToBox(lifted, sp.keyDir, target, box_half, (1e-3, 1e3))
        obj_shadow = light.visSoftShadow(mapScene, lifted, sp.keyDir, to_key, light_angle, SHADOW_STEPS) \
            if to_key[0] <= to_key[1] else 1.0
        obj_ao = light.visAO(mapScene, p, n, aoReach, AO_FALLOFF)
        surface = studioObjectSurface(p, n, -rd, sp, fresnelFloor, metal, roughness, obj_shadow, obj_ao, materialAt)
        picture = behind + (surface - behind) * cover
        shadow = floor_shadow + (obj_shadow - floor_shadow) * cover
        ao = floor_ao + (obj_ao - floor_ao) * cover
    if view == 1:
        return colour.srgbDecode(_v(core.dbgHeatCount(trace[1], float(budget))))
    if view == 2:
        return colour.srgbDecode((0.5 + 0.5 * n) * cover)
    if view == 3:
        return colour.srgbDecode(np.full(3, min(max(ao, 0.0), 1.0)))
    if view == 4:
        return colour.srgbDecode(np.full(3, min(max(shadow, 0.0), 1.0)))
    return picture


__all__ = ["studioObjectRig", "studioObjectBare", "studioObjectSurface", "studioObjectFloor", "studioObject"]
