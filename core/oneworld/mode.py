"""W2 -- the mode primitive for the one-world UI core.

Spec: atom d622ac (H9), section 3 -- Heimdall's mode schema, the "opening move" of the one-world
core. A MODE is a surface's declaration of what it is PERMITTED and OBLIGATED to draw, in three
bounded fields:

  * regions   -- the named stance-slots the surface may fill (e.g. "fleet", "floor", "now_playing").
  * verbosity -- per-region, drawn from the shared SEVERITY vocabulary (one vocabulary end to end,
                 the same one the floor's per-category levels will use -- not two that drift).
  * reach     -- directions the surface may traverse, plus the edge CLASSES it recognises,
                 including Navi's `confessed`: an edge the surface knows it cannot see down and says
                 so, rather than rendering silence as completeness.

THE ANTI-DRIFT LAW, made testable: *a mode must declare its boundary before it issues a verdict
about the whole.* `verdict_guard(mode, region)` refuses a verdict about a region the mode never
declared -- you cannot judge what you did not declare you would draw. This is the mode-level twin of
projection.require_bounds (W1): regions ARE the declared boundary.

VOCABULARY NOTE (provisional house grammar, chosen here, one place, Daniel to bless or redraw):

  SEVERITY -- how loudly a region renders, ordered quiet -> loud. Aligned with the second-press
  ladder (whisper -> specific -> full) and the floor's silence budgets. The spec fixes that a shared
  severity vocabulary exists; the particular WORDS are this build's choice.

  EDGE_CLASSES -- grounded in routes.py's own resolution words (`current`/`dangling`) plus Navi's
  `confessed`. Here: resolved | dangling | confessed.

A renderer MUST order by SEVERITY and still show a value it does not recognise -- an unknown level
is exactly when a reader most needs to see it (the routes.py DEPTHS lesson: the record was right and
nothing read it). Adding a word is a one-line edit HERE and nowhere else.

W2 builds the SHAPE and its validation. The specific modes each surface declares arrive WITH that
surface (a later slice); this does not enumerate them.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional

# Ordered quiet -> loud. The ONE place these words live.
SEVERITY = ("silent", "whisper", "normal", "loud")

# resolved/dangling mirror routes.py's step resolution; confessed is Navi's fourth class.
EDGE_CLASSES = ("resolved", "dangling", "confessed")


def make_mode(regions: Iterable[str],
              verbosity: Optional[Mapping[str, str]] = None,
              reach: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Build and VALIDATE a mode. Refuses, rather than silently coercing:
      - a verbosity entry for a region not in `regions` (you cannot tune a region you do not draw);
      - a verbosity level outside SEVERITY;
      - a reach edge class outside EDGE_CLASSES.
    Directions are free-form declared strings (the spec constrains edge classes, not directions).
    """
    regs = tuple(dict.fromkeys(str(r) for r in regions))  # dedupe, keep order

    verb: Dict[str, str] = {}
    for region, level in (verbosity or {}).items():
        if region not in regs:
            raise ValueError(
                f"verbosity names region {region!r}, which is not declared in regions {regs} -- "
                "a mode cannot set how loudly to draw a region it never declared it would draw")
        if level not in SEVERITY:
            raise ValueError(f"verbosity level {level!r} not in SEVERITY {SEVERITY}")
        verb[region] = level

    reach = dict(reach or {})
    directions = tuple(str(d) for d in reach.get("directions", ()))
    edges = tuple(str(e) for e in reach.get("edges", ()))
    for e in edges:
        if e not in EDGE_CLASSES:
            raise ValueError(f"reach edge class {e!r} not in EDGE_CLASSES {EDGE_CLASSES}")

    return {"regions": regs, "verbosity": verb,
            "reach": {"directions": directions, "edges": edges}}


def permits(mode: Mapping[str, Any], region: str) -> bool:
    """Whether this mode declared it draws `region`."""
    return region in mode.get("regions", ())


def verdict_guard(mode: Mapping[str, Any], region: str) -> None:
    """The anti-drift law: refuse a verdict about a region the mode never declared. A surface calls
    this before it renders anything that asserts something about `region`."""
    if not permits(mode, region):
        raise ValueError(
            f"mode declares regions {tuple(mode.get('regions', ()))} and may not issue a verdict "
            f"about {region!r} -- declare the boundary before judging the whole")
