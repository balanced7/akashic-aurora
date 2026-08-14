"""world_savepoint -- a world's two planes under one name, or neither.

Daniil, 2026-08-14, stating the intent behind the whole three-world arc: "so that we can
test things that could be risky quicker and have A POINT TO RESTORE FROM. I think this
approach should allow us faster iteration even though it is more steps."

He is right about the economics, and the measurement backs it: the promotion ceremony cost
roughly 10% overhead across ten slices, while disposability bought eight operations in one
night that would otherwise have been avoided or agonised over -- three re-seeds, a
deliberate FLUSHDB, a full restore, 500 planted junk keys, a contamination probe, and a
historical-commit checkout to isolate a regression. The extra steps cost a FIXED amount;
caution costs in PROPORTION to the risk, so the riskier the work the more the tiers pay.

WHAT WAS MISSING IS THE HALF HE NAMED. Measured before building:

    code    git checkout <sha>     -> returns to a KNOWN state.
    memory  seed again from prod   -> returns to a FRESH state.

Alpha was seeded when prod held 6,624 carried keys; prod now holds 20,691. Re-seeding does
not put the twin back where it was, it puts it somewhere new. deepseek's round-3 distinction
made concrete: RE-CLONABLE means re-creatable to FRESH, DISCARDABLE means re-creatable to
KNOWN, and a restore POINT requires the second. Only the code plane had it.

Both halves already existed -- git, and scripts/ops/snapshot_knowledge.py (world-aware and
exercised 2026-08-14). This binds them to one name; it does not reimplement either.

BOTH PLANES OR NEITHER. W156h was a tool whose two planes addressed different worlds, and it
flushed production twice. A savepoint that restored code but not memory would be that defect
with a friendlier name: the checkout says one thing, the store says another, and the operator
believes the label. So both planes are verified available BEFORE either is touched, and any
missing half refuses the whole operation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, List, Optional, Tuple


#: Tracked paths this repo REWRITES as a side effect of being operated -- generator output
#: and derived projections. Measured 2026-08-14: a clean checkout goes dirty within one
#: commit, because docs/MAP.md and docs/DOORS.md declare themselves auto-generated and the
#: rest are projections of the store.
#:
#: This list exists because counting them as dirt made every savepoint PARTIAL and made
#: can_restore refuse FOREVER -- the feature was unusable on the repo it was built for. An
#: always-on caveat is an ignored caveat; a never-satisfiable guard is a disabled guard.
#: Third time that shape appeared in one arc, after W159's false alarms and the env guard.
GENERATED_PATHS = (
    "docs/MAP.md", "docs/DOORS.md", "docs/PHYSICS.md", "docs/PRIOR_ART.md",
    "docs/MODULE_INDEX.md", "docs/PORTS.md",
    "chronicles/memory.md",
    "data/corpus-digests/", "data/verb-registry/",
    "state/",
)


def authored_dirt(paths) -> list:
    """The subset of dirty paths a human actually wrote -- what a restore would destroy.

    Generated output is reproducible by definition, so losing it costs a regenerate, not
    work. Authored files are the ones worth refusing over.
    """
    out = []
    for p in paths:
        norm = str(p).replace("\\", "/").lstrip("./")
        if any(norm == g or norm.startswith(g) for g in GENERATED_PATHS):
            continue
        out.append(str(p))
    return out


@dataclass
class Savepoint:
    world: str
    label: str
    git_sha: str
    knowledge_snapshot: Optional[str]
    saved_at: str
    #: Tracked files modified at save time. git can only restore what was COMMITTED, so
    #: uncommitted work sits outside what this label is able to promise.
    dirty_at_save: int = 0
    #: Generated/derived files dirty at save time. Counted separately and NOT held against
    #: the point, because they are reproducible -- but reported, since a judgement nobody
    #: can see is one nobody can correct.
    generated_at_save: int = 0

    @property
    def complete(self) -> bool:
        return self.dirty_at_save == 0 and bool(self.knowledge_snapshot)

    @property
    def note(self) -> str:
        if not self.generated_at_save:
            return ""
        return (f"{self.generated_at_save} generated file(s) were dirty at save time and "
                f"deliberately ignored -- they are reproducible, so losing them costs a "
                f"regenerate rather than work")

    @property
    def caveat(self) -> str:
        if self.complete:
            return ""
        bits = []
        if self.dirty_at_save:
            bits.append(f"{self.dirty_at_save} uncommitted tracked file(s) at save time -- "
                        f"git restores only what was committed, so those edits are NOT in "
                        f"this point and restoring will not bring them back")
        if not self.knowledge_snapshot:
            bits.append("no knowledge snapshot -- the memory plane is not captured")
        return "; ".join(bits)

    def render(self) -> str:
        flag = "" if self.complete else "  [PARTIAL] " + self.caveat
        return (f"{self.label:<24} {self.world:<6} code {self.git_sha:<10} "
                f"memory {self.knowledge_snapshot or '(none)':<18} {self.saved_at[:16]}{flag}")


def can_restore(sp: Savepoint,
                snapshot_exists: Callable[[str], bool],
                tree_dirty: int,
                consent: bool = False,
                into_world: Optional[str] = None) -> Tuple[bool, str]:
    """Verify EVERYTHING before touching ANYTHING. Returns (ok, why-not).

    The ordering is the contract: a half-applied restore leaves a world whose code and
    memory disagree, which is strictly worse than a refused one because it looks done.
    """
    target = into_world or sp.world

    if target != sp.world:
        return False, (f"refusing: this savepoint belongs to '{sp.world}' and you are "
                       f"restoring into '{target}'. Crossing worlds by accident is the "
                       f"failure the whole arc exists to prevent.")

    if target == "prod" and not consent:
        return False, ("refusing: restoring a savepoint into PROD rewinds both its code and "
                       "its entire knowledge store, and stream ids regenerate so every bus "
                       "cursor dangles. Routing safety is not consent.\n"
                       "  If prod is genuinely what you mean, pass consent explicitly.")

    if not sp.knowledge_snapshot:
        return False, (f"refusing: savepoint '{sp.label}' has no memory half, so restoring "
                       f"it would move code to {sp.git_sha} and leave the store where it is "
                       f"-- both planes or neither.")

    if not snapshot_exists(sp.knowledge_snapshot):
        return False, (f"refusing: knowledge snapshot '{sp.knowledge_snapshot}' is gone "
                       f"(snapshots self-prune). The code half alone is not this point, so "
                       f"nothing will be touched.")

    if tree_dirty:
        return False, (f"refusing: {tree_dirty} uncommitted tracked file(s) in the working "
                       f"tree would be discarded by this restore. Commit or stash them "
                       f"first -- a savepoint is for rewinding deliberate work, not for "
                       f"silently deleting the work you have not landed yet.")

    return True, ""


# ------------------------------------------------------------------ persistence

def read(path: Path) -> List[Savepoint]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []
    return [Savepoint(**d) for d in raw]


def write(path: Path, points: List[Savepoint]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps([asdict(p) for p in points], indent=2),
                          encoding="utf-8")


def append(path: Path, sp: Savepoint) -> List[Savepoint]:
    """Add or SUPERSEDE by label -- two points sharing one name is a name that does not point."""
    points = [p for p in read(path) if p.label != sp.label]
    points.append(sp)
    write(path, points)
    return points
