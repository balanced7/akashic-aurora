"""arsenal.floors -- visual FLOORS: pinned assertions on pixels, so an eye is never spent on
what a histogram can catch.

WHY. In 3D/shader work an agent cannot see its own work in the loop, so every visual defect
costs a render-look cycle. Two defects found by eye on this repo's own receipts are pure
statistics: a visualizer that goes near-black in silence, and a keyboard whose glow clips to
white. Both are cheap numpy checks. This module makes them mechanical; taste stays with the
eye.

HONEST BOUNDS. These are FLOORS, not a quality score: they fail when a frame is dead, blown
out, illegible or blank, and they pass plenty of ugly frames. Contrast uses relative-luminance
approximation over sRGB values -- adequate for a floor, not a standards-compliance check.
Regions are FRACTIONS of the frame (x, y, w, h in 0..1) so a floor survives a resolution change.

Standalone: numpy + av only, no arsenal.* imports (the analysis.py rule).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

import av

API = "arsenal.floors/v0"

# The Play page's canvas occupies the left ~60% of the frame; the piano-dev portrait frames
# put the keyboard in the bottom band. Fractions, because both page and viewport can change.
CANVAS_REGION = (0.0, 0.06, 0.60, 0.86)
KEYBOARD_REGION = (0.0, 0.72, 1.0, 0.24)


def load_rgb(path) -> np.ndarray:
    """Decode the first frame of an image or a video via PyAV (no Pillow dependency)."""
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            return frame.to_ndarray(format="rgb24")
    raise ValueError(f"no frame decoded from {path}")


def crop(rgb: np.ndarray, region: Optional[Tuple[float, float, float, float]]) -> np.ndarray:
    if region is None:
        return rgb
    h, w = rgb.shape[0], rgb.shape[1]
    x, y, rw, rh = region
    x0, y0 = int(np.clip(x, 0, 1) * w), int(np.clip(y, 0, 1) * h)
    x1 = int(np.clip(x + rw, 0, 1) * w) or w
    y1 = int(np.clip(y + rh, 0, 1) * h) or h
    return rgb[y0:max(y0 + 1, y1), x0:max(x0 + 1, x1)]


def luma(rgb: np.ndarray) -> np.ndarray:
    """Relative luminance, 0..1, from sRGB values (un-gamma'd values are NOT corrected here;
    a floor does not need the exact transfer function, and pretending otherwise would be worse)."""
    f = rgb[:, :, :3].astype(np.float32) / 255.0
    return 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]


# --------------------------------------------------------------------------- floors
def floor_not_dead(rgb: np.ndarray, *, region=None, min_mean: float = 0.020,
                   min_peak: float = 0.15) -> dict:
    """A frame with no content must not render as black. Caught live: the Play canvas in
    visualizer mode with silent input read as a void on the aurora-ribbons receipt."""
    lum = luma(crop(rgb, region))
    mean, peak = float(lum.mean()), float(lum.max())
    return {"floor": "not_dead", "region": region, "min_mean": min_mean, "min_peak": min_peak,
            "measured": {"mean": round(mean, 4), "peak": round(peak, 4)},
            "pass": bool(mean >= min_mean and peak >= min_peak)}


def floor_not_blown(rgb: np.ndarray, *, region=None, max_clipped: float = 0.08,
                    clip_at: int = 250) -> dict:
    """Bright objects must keep their edges. Caught live: the piano keyboard's glow clipped
    to white and dissolved the keys into haze."""
    patch = crop(rgb, region)
    clipped = float((patch[:, :, :3] >= clip_at).all(axis=2).mean())
    return {"floor": "not_blown", "region": region, "max_clipped": max_clipped,
            "measured": {"clipped_fraction": round(clipped, 4)},
            "pass": bool(clipped <= max_clipped)}


def floor_variety(rgb: np.ndarray, *, region=None, min_std: float = 0.010) -> dict:
    """A frame must contain something -- one flat colour is a rendering failure, not minimalism."""
    lum = luma(crop(rgb, region))
    std = float(lum.std())
    return {"floor": "variety", "region": region, "min_std": min_std,
            "measured": {"std": round(std, 4)}, "pass": bool(std >= min_std)}


def floor_legibility(rgb: np.ndarray, *, region=None, min_contrast: float = 4.5) -> dict:
    """Text/labels must stand off their background. Contrast is (Lhi+.05)/(Llo+.05) using the
    5th/95th luminance percentiles of the region -- percentile-based so one stray pixel cannot
    carry the verdict."""
    lum = luma(crop(rgb, region))
    lo = float(np.percentile(lum, 5))
    hi = float(np.percentile(lum, 95))
    ratio = (hi + 0.05) / (lo + 0.05)
    return {"floor": "legibility", "region": region, "min_contrast": min_contrast,
            "measured": {"contrast": round(ratio, 2)}, "pass": bool(ratio >= min_contrast)}


FLOORS = {
    "not_dead": floor_not_dead,
    "not_blown": floor_not_blown,
    "variety": floor_variety,
    "legibility": floor_legibility,
}

#: Floors belong to TARGETS, not to a single checklist: legibility on a canvas region is a
#: category error (a canvas is not text) and produced a 4.47-vs-4.5 false positive on a frame
#: that reads fine. Sample a gate on the frames it should PASS before trusting its red.
SETS = {
    "canvas": ["not_dead", "variety", "not_blown"],
    "label": ["legibility"],
    "frame": list(FLOORS),
}


# ----------------------------------------------------------------------- exemptions
#: Declared expected-absence. An exemption is NOT a floor exception: the floor still runs, its
#: number is still printed, and the frame is labelled `exempt` with the reason, owner and date
#: that justify it. It exists because a gate that cannot be told "this black frame is the
#: design" gets worked around somewhere invisible instead, and this house has paid for
#: invisible absences often enough to prefer a loud one.
#:
#: SHIPS EMPTY ON PURPOSE. An exemption is a judgement about someone else's expected output
#: (the visualizer-builtin blank canvas is the live candidate), so the SHAPE ships and the
#: first real entry is its owner's act -- pinned by tests/test_floors_exemptions.py, which goes
#: red when this table grows without a deliberate edit.
#:
#: Entry shape (every field required; an empty one is REFUSED, not ignored):
#:   {"<id>": {"match": ["presetbank/visualizer-builtin"],   # substring(s) of the frame path
#:             "floors": ["not_dead"],                       # scoped: never a mute button
#:             "reason": "why this absence is expected",
#:             "owner": "who says so", "date": "YYYY-MM-DD"}}
EXEMPTIONS: Dict[str, dict] = {}

_REQUIRED_DECLARATION_FIELDS = ("reason", "owner", "date")


def _as_declarations(declarations) -> Dict[str, dict]:
    """None means the shipped table; anything empty means NONE. Those are different requests,
    and the difference is what lets a lane ask for today's raw red."""
    if declarations is None:
        return dict(EXEMPTIONS)
    if isinstance(declarations, dict):
        return dict(declarations)
    out: Dict[str, dict] = {}
    for spec in declarations:
        if not isinstance(spec, dict) or "id" not in spec:
            raise ValueError("each exemption must be a dict carrying an 'id'")
        spec = dict(spec)
        out[str(spec.pop("id"))] = spec
    return out


def validate_declarations(declarations=None) -> Dict[str, dict]:
    """Refuse a declaration that cannot say WHY, WHO and WHEN, and refuse a floor name this
    module does not have. Both refusals are the same refusal: an exemption that silently
    exempts nothing, or silently explains nothing, is the disease the mechanism exists to cure
    -- an absence rendering as normal."""
    decls = _as_declarations(declarations)
    for did, spec in decls.items():
        if not isinstance(spec, dict):
            raise ValueError(f"exemption {did!r}: expected a mapping, got {type(spec).__name__}")
        for field in _REQUIRED_DECLARATION_FIELDS:
            if not str(spec.get(field) or "").strip():
                raise ValueError(
                    f"exemption {did!r}: {field} is required -- a declaration must say why the "
                    f"absence is expected, who says so, and when")
        match = spec.get("match")
        if isinstance(match, str) or not list(match or []):
            raise ValueError(f"exemption {did!r}: match must be a non-empty list of frame-path "
                             f"substrings, not {match!r}")
        floors = spec.get("floors")
        if isinstance(floors, str) or not list(floors or []):
            raise ValueError(f"exemption {did!r}: floors must be a non-empty list of floor names")
        unknown = [name for name in floors if name not in FLOORS]
        if unknown:
            raise ValueError(
                f"exemption {did!r}: unknown floor name(s) {unknown} -- a typo here would exempt "
                f"NOTHING while looking like it exempts something")
    return decls


def _declaration_for(path, floor: str, decls: Dict[str, dict]):
    """The first declaration (in table order) whose path substrings appear in this frame's path
    AND whose scope names this floor. Returns (id, spec) or None."""
    needle = str(path).replace("\\", "/")
    for did, spec in decls.items():
        if floor in spec["floors"] and any(str(m) in needle for m in spec["match"]):
            return did, spec
    return None


def check(path, *, region=None, floors: Optional[List[str]] = None, exemptions=None,
          **kw) -> dict:
    """Run the named floors (default: all) over one frame. Returns a receipt-shaped dict.

    Thresholds are filtered per floor by SIGNATURE (inspect), so passing min_contrast to a
    batch that also runs not_dead is legal -- an unknown kwarg is dropped, never raised.

    `exemptions`: None = the shipped table, [] = none at all (the raw red, for a lane that
    wants it or for a census that must report the unvarnished number)."""
    import inspect
    decls = validate_declarations(exemptions)
    rgb = load_rgb(path)
    names = floors or list(FLOORS)
    results = []
    for name in names:
        fn = FLOORS[name]
        accepted = inspect.signature(fn).parameters
        kwargs = {k: v for k, v in kw.items() if k in accepted}
        try:
            # region is ALWAYS passed: a receipt that prints a region it did not measure is
            # a label disagreeing with its own number (caught by the first evidence run).
            results.append(fn(rgb, region=region, **kwargs))
        except Exception as exc:                       # a broken floor is a FAILED floor, loudly
            results.append({"floor": name, "pass": False,
                            "error": f"{type(exc).__name__}: {exc}"})
    applied: List[str] = []
    for res in results:
        if res["pass"]:
            continue
        found = _declaration_for(path, res["floor"], decls)
        if found is None:
            continue
        did, spec = found
        # The MEASUREMENT is untouched and still prints: an exemption hides a red, never a
        # number. `pass` keeps the measured truth so the two can never be confused later.
        res["exempt"] = {"id": did, "reason": spec["reason"], "owner": spec["owner"],
                         "date": spec["date"]}
        if did not in applied:
            applied.append(did)
    ok = all(r["pass"] for r in results)
    # All-or-nothing at frame level: a frame is `exempt` only when EVERY floor that fired on it
    # is declared. Otherwise the honest word for it is `fail`.
    verdict = "pass" if ok else ("exempt" if all(r["pass"] or "exempt" in r for r in results)
                                 else "fail")
    return {"api": API, "frame": str(path), "size": [rgb.shape[1], rgb.shape[0]],
            "region": region, "results": results,
            "pass": ok, "verdict": verdict,
            "exemptions": {"declared": sorted(decls), "applied": sorted(applied)},
            "not_measured": ["taste, composition and intent -- these floors only catch dead, "
                             "blown, flat and illegible frames"]}


def check_many(paths, *, region=None, floors: Optional[List[str]] = None, exemptions=None,
               **kw) -> List[dict]:
    return [check(p, region=region, floors=floors, exemptions=exemptions, **kw) for p in paths]


def sweep(directory, *, pattern: str = "*.jpg", region=None, floors: Optional[List[str]] = None,
          exemptions=None, **kw) -> List[dict]:
    """Every matching frame under a directory (recursive), sorted -- the batch form a lane or
    a census report uses. Recursive because receipts live in per-run subdirectories."""
    d = Path(directory)
    if not d.is_dir():
        return []
    paths = sorted(list(d.rglob(pattern)) + list(d.rglob(pattern.replace("*.jpg", "*.png"))))
    return check_many(sorted(set(paths)), region=region, floors=floors, exemptions=exemptions,
                      **kw)


def summarise(receipts: List[dict]) -> dict:
    """Counts and the failure leaderboard. A census is only honest if it says how many frames
    it looked at, how many it could not read, and which floor does most of the failing.

    Exemptions get their OWN lines: folding them into `passed` would be the same disease one
    layer up, at the reporting surface."""
    failed = [r for r in receipts if not r["pass"]]
    unreadable = [r for r in receipts
                  if any("error" in res for res in r["results"])]
    by_floor: Dict[str, int] = {}
    for receipt in failed:
        for res in receipt["results"]:
            if not res["pass"]:
                by_floor[res["floor"]] = by_floor.get(res["floor"], 0) + 1
    exempt_frames = [r for r in receipts if r.get("verdict") == "exempt"]
    exempted_floors: Dict[str, int] = {}
    used: Dict[str, int] = {}
    declared: set = set()
    applied: set = set()
    for receipt in receipts:
        dec = receipt.get("exemptions") or {}
        declared.update(dec.get("declared") or [])
        for did in dec.get("applied") or []:
            applied.add(did)
            used[did] = used.get(did, 0) + 1            # per FRAME, not per excused floor
        for res in receipt["results"]:
            if "exempt" in res:
                exempted_floors[res["floor"]] = exempted_floors.get(res["floor"], 0) + 1
    return {
        "frames": len(receipts),
        "passed": len(receipts) - len(failed),
        "failed": len(failed),
        "unreadable": len(unreadable),
        "failures_by_floor": dict(sorted(by_floor.items(), key=lambda kv: -kv[1])),
        "exempt": len(exempt_frames),
        "exempted_floors": dict(sorted(exempted_floors.items(), key=lambda kv: -kv[1])),
        "declarations_used": dict(sorted(used.items())),
        "declarations_unused": sorted(declared - applied),
        "pass_rate": round((len(receipts) - len(failed)) / len(receipts), 3) if receipts else None,
        "blind": ["frames not matched by the pattern are not in this census",
                  "a pass means no floor fired, never that the frame is good",
                  "an exemption hides a red, never the measurement: the number is still in the "
                  "receipt, and a declaration whose reason has expired keeps silencing its "
                  "floor -- all this census can see is that it stopped matching anything"],
    }
