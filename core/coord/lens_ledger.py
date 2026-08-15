"""lens_ledger -- score fan lenses by what SURVIVED, not by whether the model replied.

Daniil asked for this on 2026-08-11 and the route journal's own docstring records the ask:
"the substrate for per-route funnel counters (fan vs solo tokens-per-confirmed-finding --
Daniil 2026-08-11, 'quantify the impact delta')". The substrate landed. The counters did not.

THE MOTIVATING EVIDENCE IS IN THE JOURNAL ITSELF, two lines apart on 2026-08-14:

    09:22:52  geometry=lens  n=5  n_ok=5  $0.0163   30s
    09:27:20  geometry=lens  n=5  n_ok=5  $0.0692  135s

The first is the fan whose evidence pack never reached its branches, so all five abstained
and it produced nothing. The second produced the extraction plan, the missing-seam hypothesis
and the game-engine analysis that settled an architecture decision. The journal scores them
IDENTICALLY -- and on its only signal the useless one looks BETTER, being four times faster
at a quarter the cost.

`n_ok` means the model replied. It has never meant the reply was worth anything. Same shape
as every other defect this arc turned up: a measurement that responds without answering.

WHAT THIS ADDS: per-LENS identity (a fan of five is five different questions) and an OUTCOME
per run. Four outcomes, and the two that are neither win nor loss are the load-bearing ones:

    confirmed   a finding that survived independent verification
    refuted     checked, and wrong
    abstained   declined for want of evidence -- NOT a miss, see below
    unverified  nobody checked -- the honest majority, and never a win

ABSTENTION IS NOT FAILURE. Those five branches were RIGHT to abstain: they refused to invent
file:line citations from the aggregate numbers quoted in their own question. A scorer that
counted that as a miss would train the fleet toward confident fabrication, which is precisely
what the findings contract exists to prevent. A lens that abstains repeatedly is reporting a
defect in the PACK, not in itself.

UNVERIFIED IS NEVER A WIN. The house already paid for this one (T254): "unscored claims
dilute the refuted rate to zero, so volume erases the penalty." Fifty unchecked findings must
not outrank two confirmed ones, so the rate is confirmed/VERIFIED and unverified is reported
separately as the coverage gap.

NO NUMBER ON THIN EVIDENCE. With one round per lens any rate is noise
(llm_player_recall_is_noise_at_n1_...). UNRATED is a verdict, not a placeholder for zero.

AND NOTHING IS GATED OFF FOREVER. A lens that stops running can never earn its way back, and
the sample that condemned it is exactly the sample that was too small to trust -- so gating
keeps an exploration floor, and it RECOMMENDS rather than enforces
(instrument_proposes_never_self_ratifies).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

#: The only outcomes that produce a rate. The other two are deliberately outside it.
SCORED = frozenset({"confirmed", "refuted"})
OUTCOMES = SCORED | {"abstained", "unverified"}

#: Below this many VERIFIED runs, a lens has no rate -- only a verdict of UNRATED.
MIN_VERIFIED = 5

#: Share of runs a deprioritised lens still gets, so it can earn its way back.
EXPLORATION_FLOOR = 0.15


@dataclass(frozen=True)
class LensRun:
    lens: str
    geometry: str
    outcome: str
    fan_id: str
    note: str = ""

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            # Coercing to "unverified" would hide a caller bug as a coverage gap.
            raise ValueError(
                f"unknown outcome {self.outcome!r} -- legal: {', '.join(sorted(OUTCOMES))}")


@dataclass(frozen=True)
class LensScore:
    lens: str
    confirmed_n: int
    refuted_n: int
    abstained_n: int
    unverified_n: int
    hit_rate: Optional[float]
    verdict: str            # RATED | UNRATED | UNSCORED | ABSTAINING
    why: str

    @property
    def verified_n(self) -> int:
        return self.confirmed_n + self.refuted_n

    @property
    def runs_n(self) -> int:
        return self.verified_n + self.abstained_n + self.unverified_n


def score(runs: List[LensRun], min_verified: int = MIN_VERIFIED) -> Dict[str, LensScore]:
    """Per-lens outcomes -> honest verdicts. Never invents a rate it has not earned."""
    # SUPERSESSION, last-writer-wins per (fan, lens). Storage is append-only -- a verdict is
    # written, never edited -- but a RUN has exactly one outcome, and the auto-recorded
    # `unverified` row is a placeholder that a later verification replaces.
    #
    # Found by using it: verifying a branch appended `confirmed` beside the existing
    # `unverified`, so one run counted twice and inflated the coverage gap it was supposed
    # to shrink. Two rows claiming one run's state is the same shape as any other dual
    # authority; the fix is that the newest wins at READ time, exactly like the notes plane.
    latest: Dict[tuple, LensRun] = {}
    for r in runs:
        latest[(r.fan_id, r.lens)] = r          # file order is chronological (append-only)

    by: Dict[str, Dict[str, int]] = {}
    for r in latest.values():
        d = by.setdefault(r.lens, {k: 0 for k in OUTCOMES})
        d[r.outcome] += 1

    out: Dict[str, LensScore] = {}
    for lens, d in by.items():
        ver = d["confirmed"] + d["refuted"]
        total = ver + d["abstained"] + d["unverified"]

        # ORDER MATTERS, and running it on real data is what fixed this. The first cut put
        # the abstention branch above the thin-evidence one, so a lens with 1 CONFIRMED and
        # 1 abstained rendered as ABSTAINING -- burying the only lens that had produced a
        # surviving finding. Verified evidence, however thin, outranks the abstention signal:
        # abstention describes the PACK, and a verified outcome describes the LENS.
        if ver >= min_verified:
            rate = d["confirmed"] / ver
            verdict, why = "RATED", (
                f"{d['confirmed']}/{ver} verified findings survived")
        elif ver > 0:
            verdict, rate = "UNRATED", None
            why = (f"only {ver} verified run(s), need {min_verified} -- too few to rate, and "
                   f"a number here would be noise"
                   + (f" ({d['abstained']} abstention(s) alongside, which describe the pack "
                      f"rather than the lens)" if d["abstained"] else ""))
        elif d["abstained"] and d["abstained"] >= max(1, total - ver):
            # Nothing verified AND mostly abstaining: the lens is reporting a bad PACK.
            verdict, rate = "ABSTAINING", None
            why = (f"{d['abstained']} of {total} runs abstained for want of evidence -- that "
                   f"is a finding about the PACK, not a miss by the lens")
        elif ver == 0:
            verdict, rate = "UNSCORED", None
            why = (f"{total} run(s), none verified -- nobody checked whether these findings "
                   f"held, so no rate can be earned. Verify some before trusting this lens")
        else:
            verdict, rate = "UNRATED", None
            why = (f"only {ver} verified run(s), need {min_verified} -- too few to rate, and "
                   f"a number here would be noise")

        out[lens] = LensScore(lens=lens, confirmed_n=d["confirmed"], refuted_n=d["refuted"],
                              abstained_n=d["abstained"], unverified_n=d["unverified"],
                              hit_rate=rate, verdict=verdict, why=why)
    return out


def gate(scores: Dict[str, LensScore], floor: float = EXPLORATION_FLOOR,
         keep_above: float = 0.34) -> Dict[str, str]:
    """Which lenses to run next time: run | explore | deprioritise. ADVISORY.

    Only a RATED lens can be moved off `run`, so a lens is never condemned by the sample
    that was too small to judge it. And `explore` exists so a deprioritised lens keeps
    getting a share of runs -- without it the ledger stops being a measurement and becomes
    a verdict that can never be revisited.
    """
    plan: Dict[str, str] = {}
    for lens, s in scores.items():
        if s.verdict != "RATED" or s.hit_rate is None:
            plan[lens] = "run"
        elif s.hit_rate >= keep_above:
            plan[lens] = "run"
        elif floor > 0:
            plan[lens] = "explore"
        else:
            plan[lens] = "deprioritise"
    return plan


def render(scores: Dict[str, LensScore], plan: Dict[str, str]) -> str:
    if not scores:
        return ("LENS LEDGER -- no runs recorded yet. Score a fan's branches with "
                "record() and outcomes become verdicts once enough are verified.")
    out = ["LENS LEDGER -- lenses scored by what SURVIVED, not by whether the model replied"]
    unver = sum(s.unverified_n for s in scores.values())
    total = sum(s.runs_n for s in scores.values())
    if unver:
        # Say "unverified", the outcome's own name, rather than a paraphrase -- the render
        # and the data must use one vocabulary or a reader cannot map one to the other.
        out.append(f"  COVERAGE GAP: {unver} of {total} run(s) are unverified -- nobody "
                   f"checked them, so they count toward no rate. Unscored claims would "
                   f"otherwise dilute every refutation to zero (T254)")
    for lens, s in sorted(scores.items(), key=lambda kv: (kv[1].hit_rate is None,
                                                          kv[1].hit_rate or 0)):
        rate = f"{s.hit_rate:.0%}" if s.hit_rate is not None else "  --"
        out.append(f"  [{s.verdict:>10}] {rate:>5}  {lens:<34} "
                   f"{s.confirmed_n}c/{s.refuted_n}r/{s.abstained_n}a/{s.unverified_n}u "
                   f"-> {plan.get(lens, 'run')}")
        out.append(f"               {s.why}")
    out.append("  Gating is a RECOMMENDATION and is not enforced -- a structural scorer has "
               "no business silencing a lens before a human has read its ledger.")
    return "\n".join(out)


def lens_identity(prompts: List[str], width: int = 60) -> List[str]:
    """Name each branch by the part of its prompt that DIFFERS from the others.

    A lens fan is defined as "same evidence, different questions" (the geometry vocabulary
    in ask.py), so the question is precisely the delta and the pack is precisely the shared
    prefix. Naming a branch by prompt[:300] cannot work once the pack rides inside each
    prompt -- which is the only arrangement that actually delivers the evidence, since
    --prompt-file does not compose with --lens. Every branch would carry the same name.

    Falls back to positional ids WHEN THERE IS NO DIFFERENCE (identical prompts -- a `panel`
    fan measuring self-consistency, not a lens fan), and says so in the name rather than
    pretending the branches were distinguishable.
    """
    if not prompts:
        return []
    if len(prompts) == 1:
        return [_slug(prompts[0], width)]

    shortest = min(len(p) for p in prompts)
    i = 0
    while i < shortest and len({p[i] for p in prompts}) == 1:
        i += 1
    # Trim the common tail too: lens text often sits between a shared pack and a shared
    # contract/footer, and including the footer buries the distinguishing part.
    j = 0
    while j < (shortest - i) and len({p[len(p) - 1 - j] for p in prompts}) == 1:
        j += 1

    out: List[str] = []
    for k, p in enumerate(prompts):
        delta = p[i:len(p) - j].strip()
        out.append(_slug(delta, width) if delta else f"indistinct-branch-{k}")
    return out


def _slug(text: str, width: int) -> str:
    keep = []
    for ch in str(text).lower()[:width * 3]:
        if ch.isalnum():
            keep.append(ch)
        elif keep and keep[-1] != "-":
            keep.append("-")
    return ("".join(keep).strip("-") or "unnamed")[:width]


# ------------------------------------------------------------------ persistence

def ledger_path(root: Path) -> Path:
    """Where the ledger lives. Honours AKASHIC_LENS_LEDGER, exactly like the route journal
    beside it honours AKASHIC_ROUTE_JOURNAL.

    THE NEIGHBOUR HAD ALREADY SOLVED THIS AND I DID NOT COPY IT. Without the override, the
    auto-record hook fired during the T281 fan tests and wrote their fixtures -- lenses
    literally named "1", "2", "p1" -- into the LIVE ledger. The route journal was untouched
    by the same tests precisely because they point its env var at a tmp path. Twelve junk
    rows before anyone looked.
    """
    import os
    env = os.environ.get("AKASHIC_LENS_LEDGER", "")
    if env:
        return Path(env)
    return Path(root) / "state" / "lens_ledger.jsonl"


def record(path: Path, run: LensRun) -> None:
    """Append one run. Fail-open like the route journal it sits beside: a dead ledger must
    never wedge a fan."""
    import os
    if os.environ.get("_AISETUP_TEST_ISOLATED"):
        return          # a test run must never write the live ledger
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(run), ensure_ascii=False) + "\n")
    except Exception:
        pass


def read(path: Path) -> List[LensRun]:
    out: List[LensRun] = []
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                out.append(LensRun(**json.loads(line)))
            except Exception:
                continue          # a malformed line is skipped, never fatal
    except Exception:
        return []
    return out
