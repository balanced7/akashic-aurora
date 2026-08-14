"""world_diff -- what differs between two worlds, MINUS what should differ.

Daniil, 2026-08-14: "should we have some kind of snapshot delta comparison tool between
prod, beta and alpha? so we can tell at a glance what is the same and what isn't?"

THIS IS NOT A NEW PRIMITIVE. core/coord/compare.py already is the set-difference organ, and
it was born from Daniil's own words a week earlier ("at work I find a lot of value by seeing
what one system has and the other doesn't"). Its docstring predicted this slice: "so the
fifth instance costs a line instead of a module." What compare.py cannot know is which
differences are SUPPOSED to be there, and that is the entire contribution here.

WHY THE RAW DIFFERENCE IS WORSE THAN NOTHING, measured before this file was written:

    prefix       prod    alpha
    learn:       1061     1060     <- 1 key of real divergence
    mem:          563      559     <- 4
    narr:        3730     3725     <- 5
    bifrost:     8276        0     <- 8,276 of EXPECTED difference
    events:      4884        0     <- 4,884 of EXPECTED difference
    recall:       803        0     <-   803 of EXPECTED difference

~10 real findings under 13,963 expected ones. compare.py names that exact failure -- "a
large, confident, meaningless difference -- worse than an error, because it looks like a
finding" -- and a world differ that skipped this step would BE that failure.

THE ORACLE IS THE SEED MANIFEST, NOT A HAND-WRITTEN LIST. W156g made each seeded world
record which prefixes it carried and which it refused. So "expected" is derived from what
actually happened to this world, and it cannot rot the way a maintained constant would. A
world with no manifest has no oracle, and this module says so instead of guessing -- an
invented expectation is the same lie as an invented finding, wearing the opposite sign.

THE TWO-SIDED RULE, which is why this earns its keep rather than just tidying output:

    refused prefix, ABSENT in target   -> expected. Silent.
    refused prefix, PRESENT in target  -> ALARM. Something wrote around the seed.

The second case is not hypothetical. On 2026-08-14 a restore drill wrote prod's full
snapshot into alpha and imported 7,870 bifrost:* keys the seed exists to refuse -- transport
and identity, the class whose whole danger is that an inherited cursor makes a twin believe
it consumed mail it never saw. Nothing detected it; a human noticed by eye. A differ that
only reported "things that differ" would have stayed silent on it, because after the
contamination the two worlds AGREED on bifrost:. Agreement with prod is exactly the wrong
outcome for a plane the seed refuses, and only the manifest makes that legible.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

#: Severity vocabulary, ordered loudest-first for rendering.
SEVERITY_ORDER = {"alarm": 0, "report": 1, "unknown": 2, "silent": 3}


@dataclass(frozen=True)
class Verdict:
    expected: bool
    severity: str          # alarm | report | unknown | silent
    why: str


@dataclass(frozen=True)
class PlaneRow:
    prefix: str
    n_source: int
    n_target: int
    verdict: Verdict

    @property
    def identical(self) -> bool:
        return self.n_source == self.n_target


def classify(prefix: str, present_in_target: bool,
             manifest: Optional[Dict]) -> Verdict:
    """Is this prefix's state between two worlds expected, or news?

    `present_in_target` rather than a count on purpose: the question the manifest can
    answer is about PRESENCE (did this plane ride down at all), not about drift. Two
    institutions differing by a few keys on a carried plane is the normal condition and
    needs no oracle to interpret.
    """
    if not manifest:
        return Verdict(False, "unknown",
                       "no seed manifest in the target world, so nothing can vouch for "
                       "what SHOULD differ here -- run scripts/seed_world.py, or read this "
                       "row as raw difference and judge it yourself")

    refused = manifest.get("refused") or {}
    carried = manifest.get("carried") or {}

    if prefix in refused:
        if not present_in_target:
            return Verdict(True, "silent",
                           f"refused by the seed ({refused[prefix][:60]}) and correctly absent")
        return Verdict(False, "alarm",
                       f"REFUSED by the seed but PRESENT anyway -- something wrote around "
                       f"the seeding door (a full-fidelity restore does exactly this). "
                       f"Agreement with the source on a refused plane is the bug, not the fix")

    if prefix in carried:
        if present_in_target:
            return Verdict(False, "report",
                           "carried by the seed; two institutions drifting apart on a "
                           "shared plane is the normal condition, shown so it stays visible")
        return Verdict(False, "alarm",
                       "carried by the seed but now entirely ABSENT -- the twin lost a "
                       "plane it was given")

    return Verdict(False, "report",
                   "not named in the seed manifest (it postdates the seed, or arrived by "
                   "another door), so the manifest cannot vouch for it either way")


#: A prefix smaller than this, and unnamed by the manifest, is not a plane.
MINOR_FLOOR = 25


def collapse_minor(rows: List[PlaneRow], manifest: Optional[Dict],
                   floor: int = MINOR_FLOOR):
    """Fold tiny, manifest-unknown prefixes into one counted group. Returns (kept, group).

    FOUND BY RUNNING IT. The first live prod->alpha run put twenty rows of per-test
    namespaces (t-w43-3fd0a1e8, t-w16-c4916333, ...) above the three real findings -- this
    tool reproducing, one level up, the exact burial it was built to prevent. Writing the
    ordering rule was not enough; the row POPULATION had to be ruled on too.

    Two prefixes never collapse, however small:
      - anything the manifest names, because being vouched for is what makes a prefix a
        plane (knowledge_map: is two keys and is structural);
      - anything carrying an ALARM, because a single stray key on a refused plane is the
        entire finding.
    """
    named = set()
    if manifest:
        named |= set(manifest.get("carried") or {})
        named |= set(manifest.get("refused") or {})

    kept, minor = [], []
    for r in rows:
        big = max(r.n_source, r.n_target) >= floor
        if r.prefix in named or r.verdict.severity == "alarm" or big:
            kept.append(r)
        else:
            minor.append(r)

    group = {
        "n_prefixes": len(minor),
        "n_keys_source": sum(r.n_source for r in minor),
        "n_keys_target": sum(r.n_target for r in minor),
        "examples": [r.prefix for r in sorted(minor, key=lambda x: -x.n_source)[:3]],
    }
    return kept, group


def render(rows: List[PlaneRow], source: str, target: str,
           manifest: Optional[Dict] = None,
           collapsed: Optional[Dict] = None) -> str:
    """One screen: findings first, expected bulk collapsed but never hidden.

    "At a glance" is the requirement, so ordering IS the feature. Silence here means
    'not shouted', never 'not shown' -- a differ that omits what it chose to ignore
    cannot be audited, and then its quiet stops being evidence of anything.
    """
    out: List[str] = [f"WORLD DIFF  {source} -> {target}"]

    if manifest:
        out.append(f"  oracle: seed manifest, {source} -> {target} at "
                   f"{str(manifest.get('seeded_at'))[:16]} "
                   f"({manifest.get('total_carried', 0):,} keys carried)")
    else:
        out.append("  oracle: NO SEED MANIFEST -- nothing is called expected below; "
                   "every row is raw difference")

    ordered = sorted(rows, key=lambda r: (SEVERITY_ORDER.get(r.verdict.severity, 9),
                                          -abs(r.n_source - r.n_target)))
    for r in ordered:
        if r.verdict.severity == "alarm":
            tag = "ALARM  "
        elif r.verdict.severity == "silent":
            tag = "expected"
        elif r.verdict.severity == "unknown":
            tag = "unknown"
        else:
            tag = "differs" if not r.identical else "same"
        if r.identical and r.verdict.severity not in ("alarm",):
            tag = "identical"
        out.append(f"  [{tag:>9}] {r.prefix:<14} {r.n_source:>8,} vs {r.n_target:>8,}"
                   f"   {r.verdict.why}")

    if collapsed and collapsed.get("n_prefixes"):
        eg = ", ".join(collapsed.get("examples") or [])
        out.append(f"  [{'minor':>9}] {collapsed['n_prefixes']} ephemeral prefix(es) "
                   f"{collapsed['n_keys_source']:,} vs {collapsed['n_keys_target']:,}"
                   f"   below the plane floor and unnamed by the manifest "
                   f"(e.g. {eg}) -- counted, not dropped")
    return "\n".join(out)
