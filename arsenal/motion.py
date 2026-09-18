"""arsenal.motion -- the TEMPORAL twin of the pixel floors: read how a take MOVES out of the
storyboard manifest, so pacing is a number instead of a memory of having watched it.

WHY. arsenal.floors answers "is this frame dead, blown, flat or illegible". It says nothing
about TIME, and time is where much of a render's character lives: a preset that snaps between
six looks a second and one that breathes once every four seconds can both pass every pixel
floor. A seat that cannot watch video (this model cannot) is otherwise blind to that whole
axis, and even a seat that can watch twenty takes cannot compare them by eye -- which is the
ergonomic point: one number per take, cheap enough to run over a whole bank.

WHAT IT IS NOT. Not a quality score, and not a verdict on taste. `read` is a coarse banding of
one number (transitions per minute) against DECLARED thresholds, printed beside the numbers it
came from; there is no pass here to fail. The honest confession sits in `blind`, including the
one measurement this artefact deliberately refuses to fake: settle depth INSIDE a transition is
not recoverable from a stored segment table (it carries peaks and durations, not the per-frame
curve), so the fix for that belongs in storyboard.analyse(), where the times still exist.

Standalone: numpy only, no arsenal.* imports (the analysis.py rule). It reads a manifest; it
never decodes a frame, so a stored storyboard is profiled at file-read cost.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

import numpy as np

API = "arsenal.motion/v0"

#: The banding rule, in transitions per minute. DECLARED, because banding is a judgement --
#: and a judgement that is not written down is a taste pretending to be a number.
THRESHOLDS = {"calm": 6.0, "active": 20.0}


def load(manifest) -> dict:
    """A manifest dict, or a path to a storyboard JSON on disk."""
    if isinstance(manifest, (str, Path)):
        return json.loads(Path(manifest).read_text(encoding="utf-8"))
    return manifest


def _read(transitions: int, per_min: Optional[float]) -> str:
    if per_min is None:
        return "unknown"
    if transitions == 0:
        return "still"
    if per_min <= THRESHOLDS["calm"]:
        return "calm"
    if per_min <= THRESHOLDS["active"]:
        return "active"
    return "frantic"


def _median(values: List[float]) -> Optional[float]:
    return float(np.median(values)) if values else None


def profile(manifest) -> dict:
    """One take's motion profile, derived entirely from its storyboard segment table."""
    m = load(manifest)
    segs = [s for s in (m.get("segments") or []) if isinstance(s, dict)]
    fps = float((m.get("sampling") or {}).get("fps") or 0) or None
    trans = [s for s in segs if s.get("kind") == "transition"]
    settled = [s for s in segs if s.get("kind") == "settled"]
    end = max((float(s.get("end_s") or 0.0) for s in segs), default=0.0)
    duration = end if end > 0 else None
    durations = [int(s.get("duration_ms") or 0) for s in trans]
    calm_ms = [int(s.get("duration_ms") or 0) for s in settled]
    peaks = [float(s.get("peak_score") or 0.0) for s in trans]
    per_min = round(len(trans) / (duration / 60.0), 3) if duration else None

    blind = [
        "audio: the change score is visual only",
        "transitions_per_min is a RATE, so a SHORT take inflates it: one cut in a 7.8 s clip "
        "reads 7.7/min and bands as 'active' beside a 90 s take with three cuts (2/min). Read "
        "duration_s beside the rate, and treat 'read' as a hint on a whole bank, never a verdict "
        "on one short clip",
        "settle depth INSIDE a transition is not measurable from a stored manifest -- the "
        "segment table carries peaks and durations, not the curve per segment (the fix, when "
        "someone wants it, belongs in storyboard.analyse(), where the per-frame times live)",
        "a strobe can read as one very short transition and a slow fade as one very long one, "
        "so duration_ms is not by itself a violence measure -- read it beside peak_median",
    ]
    if duration is None:
        blind.insert(0, "no segments in this manifest -- a rate over no time is not zero, it is "
                        "unknown, and this profile reports None rather than a fake 0")
    elif fps:
        blind.insert(0, f"the sampling stride is {1000.0 / fps:.0f} ms -- any change shorter than "
                        f"that happened between two samples and was never seen at all")
    return {
        "api": API,
        "source": m.get("source"),
        "duration_s": duration,
        "frames_examined": m.get("frames_examined"),
        "stride_ms": round(1000.0 / fps, 1) if fps else None,
        "transitions": len(trans),
        "settled": len(settled),
        "transitions_per_min": per_min,
        "transition_fraction": round(sum(durations) / (duration * 1000.0), 4) if duration else None,
        "median_transition_ms": _median(durations),
        "p90_transition_ms": float(np.percentile(durations, 90)) if durations else None,
        "max_transition_ms": max(durations) if durations else None,
        "median_settled_ms": _median(calm_ms),
        "longest_calm_s": round(max(calm_ms) / 1000.0, 3) if calm_ms else None,
        "peak_median": _median(peaks),
        "peak_p90": float(np.percentile(peaks, 90)) if peaks else None,
        "read": _read(len(trans), per_min),
        "not_measured": ["whether any of this is GOOD -- pacing is character, not quality"],
        "blind": blind,
    }


def profile_many(directory, *, pattern: str = "storyboard.json") -> List[dict]:
    """Every stored storyboard under a directory (recursive) -- the bank-wide comparison."""
    d = Path(directory)
    if not d.is_dir():
        return []
    return [profile(p) for p in sorted(d.rglob(pattern))]
