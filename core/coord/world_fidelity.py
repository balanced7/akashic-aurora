"""world_fidelity -- what a twin CAN and CANNOT do, said out loud before it is discovered.

Two losses in one day, same shape, both found by hitting them:

  1. Suite failures in the twin traced to files prod carries UNCOMMITTED. A clone is faithful
     to HEAD; the source is not running HEAD.
  2. A five-lens model fanout died in one go -- `.secrets/` is gitignored, so a clone carries
     ZERO credentials and every credentialed door is closed. Measured: prod 10, beta 0, alpha 0.

Neither was a bug. Both were a twin being SILENTLY INCAPABLE rather than wrong, and the
silence is what costs: the work is planned, started and half-done before a door refuses.

THE PLANES. The real finding of the arc is that nobody enumerated them up front -- each was
discovered by a failure, in this order:

    code         arrives by git clone   -> faithful to HEAD, NOT to the source's working tree
    memory       arrives by seeding     -> knowledge only; transport refused on purpose
    file plane   arrives by NEITHER     -> state/, session_logs/ are gitignored and unseeded
    credentials  arrives by NEITHER     -> .secrets/ is gitignored BY DESIGN and must stay so

WHAT THIS MODULE REFUSES TO DO. It does not copy secrets into a twin, and does not offer to.
More copies of a credential is a real cost, and a twin that can spend money stops being cheap
to discard -- that is the operator's decision, not a convenience the tool should make easy.
This reports the closed door and the consequence; opening it is a human act.

UNKNOWN IS A REAL STATE. A capability report that guesses is worse than no report, because it
gets trusted. Any plane whose probe could not run reports UNKNOWN with the reason, never a
hopeful PRESENT.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

#: Loudest first -- ordering IS the feature in an at-a-glance render.
STATUS_ORDER = {"absent": 0, "partial": 1, "unknown": 2, "present": 3}


@dataclass(frozen=True)
class PlaneStatus:
    plane: str
    status: str            # absent | partial | unknown | present
    detail: str
    #: What this MEANS for work you might attempt. A status without a consequence is a fact
    #: rather than an answer, and the whole point here is to stop a human planning work the
    #: twin cannot do.
    consequence: str


def assess(root: str,
           secrets_count: Optional[int],
           state_count: Optional[int],
           head_sha: Optional[str],
           source_dirty: Optional[int],
           seeded_from: Optional[str] = None,
           is_source: bool = False) -> List[PlaneStatus]:
    """Report each plane. Counts are passed in rather than probed so this stays pure and
    the CLI owns every filesystem and git call -- the module can then be pinned without
    a repo, and the probe can be world-scoped by its caller."""
    out: List[PlaneStatus] = []

    # --- code -----------------------------------------------------------
    if head_sha is None or source_dirty is None:
        out.append(PlaneStatus("code", "unknown",
                               "could not read the source's HEAD or working-tree state",
                               "cannot tell how far this twin lags the source; treat suite "
                               "differences as unexplained rather than inherited"))
    elif source_dirty:
        out.append(PlaneStatus(
            "code", "partial", f"source carries {source_dirty} uncommitted tracked file(s)",
            f"this twin cannot contain those {source_dirty} edits -- each one can surface "
            f"here as a real-looking failure that does not exist in the source"))
    elif is_source:
        out.append(PlaneStatus("code", "present", f"at {head_sha}, this IS the source",
                               "nothing upstream to lag; this checkout defines the code"))
    else:
        out.append(PlaneStatus("code", "present", f"at {head_sha}, source tree clean",
                               "this twin and its source agree on code"))

    # --- memory ---------------------------------------------------------
    # Read from the seed manifest rather than asserted. The first cut hardcoded "seeded
    # knowledge plane", which is a claim about history, and it was FALSE in prod -- whose
    # memory is native and was never seeded by anyone. The organ built to report honestly
    # was itself responding without answering.
    if seeded_from:
        out.append(PlaneStatus(
            "memory", "present", f"seeded from {seeded_from}; transport deliberately refused",
            "recall, notes and lessons behave like the source; the bus does NOT -- no "
            "inherited cursors or presence, which is the point"))
    elif is_source:
        out.append(PlaneStatus("memory", "present", "native knowledge plane",
                               "this store is the original; nothing here was inherited"))
    else:
        out.append(PlaneStatus(
            "memory", "unknown", "no seed manifest found",
            "this checkout's memory is either native or was populated by some other door -- "
            "nothing on record can say which"))

    # --- file plane -----------------------------------------------------
    if state_count is None:
        out.append(PlaneStatus("file", "unknown", "could not read state/",
                               "untracked runtime state may or may not be here"))
    elif state_count <= 5:
        out.append(PlaneStatus(
            "file", "partial", f"state/ holds {state_count} entr(y|ies)",
            "gitignored runtime state does not ride with a clone; anything reading state/ "
            "may behave differently here than in the source"))
    else:
        out.append(PlaneStatus("file", "present", f"state/ holds {state_count} entries",
                               "runtime state is populated"))

    # --- credentials ----------------------------------------------------
    if secrets_count is None:
        out.append(PlaneStatus("credentials", "unknown", "could not read .secrets/",
                               "credentialed doors may or may not work here"))
    elif secrets_count == 0:
        out.append(PlaneStatus(
            "credentials", "absent", ".secrets/ is empty (gitignored, so a clone carries none)",
            "EVERY credentialed door is CLOSED here and will refuse as a configuration state: "
            "model asks (ask/fan), web search, any external API. Run those from the source, "
            "which is safe when the work is read-only"))
    else:
        out.append(PlaneStatus("credentials", "present",
                               f".secrets/ holds {secrets_count} file(s)",
                               "credentialed doors are available"))
    return out


def render(rows: List[PlaneStatus], world: str) -> str:
    ordered = sorted(rows, key=lambda r: STATUS_ORDER.get(r.status, 9))
    out = [f"WORLD FIDELITY  {world} -- what this checkout can and cannot do"]
    for r in ordered:
        tag = r.status.upper() if r.status in ("absent", "partial") else r.status
        out.append(f"  [{tag:>8}] {r.plane:<12} {r.detail}")
        out.append(f"             {'':<12} -> {r.consequence}")
    if any(r.plane == "credentials" and r.status == "absent" for r in rows):
        out.append("  NOTE: this report does not copy secrets into a twin and will not offer "
                   "to -- a twin that can spend money is no longer cheap to discard.")
    return "\n".join(out)
