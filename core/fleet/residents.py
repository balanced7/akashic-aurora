"""The resident registry -- who a seat IS, and the receipts that earned the name.

Semantic Relationship: Resident derived_from Lessons (by authored receipt).

WHY THIS EXISTS, and it is a measured gap rather than a designed-in feature. Daniil's
designation scheme (2026-08-09) gives every permanent resident a callsign:

    Deepseek | Onyx | Red | 3 - Foxbat
    vendor   | family | team | number - callsign

kimi reviewed it and found the hole:

    "A callsign certifies a continuous self, but a resident is a sequence of boots over a fold
     that selects for narrative continuity and AGAINST contradiction-awareness. The name
     asserts an archive the current boot may not carry."

Measured before this module was written: of the eight receipts behind the first proposed
callsigns, ZERO appeared in their own seat's boot fold. The story lived in the archive and the
boot did not carry it, so a resident could not say why it was called what it was. That is the
difference between a name that is earned and a name that is decoration.

THE TWO CEREMONY RULES ARE ENFORCED HERE, NOT IN ETIQUETTE, because a rule that lives only in a
document needs someone to remember it -- which is the failure mode the fragmentation doctrine
describes:

  RULE 1  You do not name yourself. `by` may never equal `nominee`. A self-declared identity is
          the T255 class (a player-declared field nothing verifies), one level up.
  RULE 2  A receipt must be authored BY the nominee. deepseek's amendment, and it closes the
          error recorded in `the_M_tag_failed_first_contact_and_the_defect_was_routing_not_attention`:
          "[M] MUST MEAN 'I HAVE THE RECEIPT', NEVER 'I REMEMBER'". A receipt someone else wrote
          is a recollection about the nominee wearing a receipt's clothes.

RULE 4 was AMENDED by Daniil on 2026-08-09 ("feel free to amend rule 4"): a callsign may be
EARNED through contribution as well as SURVIVED through a screwup. Both registers are legal and
the receipt bar is identical, so this module does not care WHICH kind of moment a receipt
records -- only that it exists and that the nominee wrote it. Enforcing tone would be enforcing
taste, and taste is the ratifier's job.

AN UNRESOLVABLE RECEIPT IS REFUSED, NEVER ASSUMED. Absence must not read as success -- the same
invariant the guard-of-guards broke in T178, where a missing baseline returned {} and the
ratchet passed silently.

APPEND-ONLY, per the substrate's own physics. A superseded callsign is never deleted; it
becomes a `formerly:` entry and its record still resolves. The log is the truth and the current
designation is a PROJECTION over it -- the same shape as every other durable plane here.

NOT IN THIS MODULE, deliberately: routing tags (T108 owns addressing), role/side assignment
events (a resident's JOB at a timestamp is a separate append-only stream), and any claim that
persistence improves correctness. kimi's standing objection -- that persistence has never been
isolated as the cause of a win -- is unresolved, and this module buys LEGIBILITY only.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from core.foundation.store import create_store

#: One list per resident, oldest-first. Every nomination and ratification appends; nothing is
#: ever rewritten in place, so `formerly:` is derivable rather than maintained.
_LOG_KEY = "residents:log:{agent}"

#: The roster index -- which agent ids have ever been nominated. Kept so a caller can enumerate
#: residents without a keyspace scan (the census lesson: measure the distribution, don't guess).
_INDEX_KEY = "residents:all"

NOMINATED = "nominated"
RATIFIED = "ratified"


def _store():
    return create_store()


def _receipt_author(experiment: str) -> Optional[str]:
    """Who authored the lesson `experiment`, or None when it does not resolve.

    None means UNKNOWN -- the caller must refuse rather than assume. It never means "nobody",
    and it must never be coerced into one.
    """
    try:
        from core.learning.learning_store import get_learning_store
        # _load_experiment is the only exact-key read the store offers; every public accessor
        # searches. Noted as owed ergonomics rather than worked around silently.
        rec = get_learning_store()._load_experiment(experiment)
    except Exception:
        return None
    if not rec:
        return None
    return str(rec.get("agent_id") or rec.get("agent") or "") or None


def _records(agent_id: str) -> List[Dict[str, Any]]:
    raw = _store().lrange(_LOG_KEY.format(agent=agent_id), 0, -1) or []
    out: List[Dict[str, Any]] = []
    for r in raw:
        try:
            out.append(json.loads(r))
        except Exception:
            continue                      # a corrupt row must not hide the rest of the history
    return out


def _append(agent_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    st = _store()
    st.rpush(_LOG_KEY.format(agent=agent_id), json.dumps(record, ensure_ascii=False))
    try:
        if agent_id not in (st.lrange(_INDEX_KEY, 0, -1) or []):
            st.rpush(_INDEX_KEY, agent_id)
    except Exception:
        pass                              # the index is a convenience; the log is the truth
    return record


def nominate(*, nominee: str, callsign: str, receipts: List[str], by: str,
             vendor: str = "", family: str = "", team: str = "",
             number: Optional[int] = None, note: str = "") -> Dict[str, Any]:
    """Record a nomination. Raises ValueError when a ceremony rule is broken.

    Refusals are LOUD and NAMED -- they say which rule, which party, and which receipt, because
    a refusal that does not say why trains the reader to route around it.
    """
    nominee = str(nominee or "").strip()
    by = str(by or "").strip()
    callsign = str(callsign or "").strip()
    if not nominee or not callsign or not by:
        raise ValueError("nominate needs a nominee, a callsign and a nominator (`by`)")

    # RULE 1 -- you do not name yourself.
    if by.lower() == nominee.lower():
        raise ValueError(
            f"refused: '{by}' cannot nominate itself. Ceremony rule 1 -- you do not name "
            f"yourself, a peer confers it. A self-chosen callsign is a self-declared identity, "
            f"which is the defect class open at T255."
        )

    if not receipts:
        raise ValueError(
            f"refused: nominating '{nominee}' as '{callsign}' with no receipt. Ceremony rule 2 "
            f"-- a name must cite something that happened."
        )

    # RULE 2 -- every receipt must resolve, and must be authored BY the nominee.
    for r in receipts:
        author = _receipt_author(r)
        if author is None:
            raise ValueError(
                f"refused: receipt '{r}' does not resolve to any lesson. UNKNOWN is not "
                f"permission -- an unresolvable receipt is refused, never assumed."
            )
        if author.lower() != nominee.lower():
            raise ValueError(
                f"refused: receipt '{r}' was authored by '{author}', not by the nominee "
                f"'{nominee}'. Ceremony rule 2 -- the receipt must come from the RECIPIENT's "
                f"archive. A receipt someone else wrote is a recollection about them, which is "
                f"the [M]-tag error: it must mean 'I have the receipt', never 'I remember'."
            )

    return _append(nominee, {
        "state": NOMINATED, "agent_id": nominee, "callsign": callsign,
        "receipts": list(receipts), "by": by, "at": time.time(),
        "vendor": vendor, "family": family, "team": team, "number": number, "note": note,
    })


def ratify(*, nominee: str, callsign: str, by: str) -> Dict[str, Any]:
    """Promote a nomination to the active designation. Rule 3: a human ratifies.

    Refuses a callsign nobody nominated -- ratification confirms a draft, it does not author
    one, which is the T227 shape (the fan drafts, a human ratifies, a checker verifies forever).
    """
    nominee = str(nominee or "").strip()
    callsign = str(callsign or "").strip()
    draft = None
    for rec in _records(nominee):
        if rec.get("state") == NOMINATED and rec.get("callsign") == callsign:
            draft = rec
    if draft is None:
        raise ValueError(
            f"refused: '{callsign}' was never nominated for '{nominee}'. Ratification confirms "
            f"a draft; it does not author one."
        )
    out = dict(draft)
    out.update({"state": RATIFIED, "ratified_by": str(by or "").strip(), "at": time.time()})
    return _append(nominee, out)


def history(agent_id: str) -> List[Dict[str, Any]]:
    """Every record for this resident, oldest first. Nothing is ever removed."""
    return _records(agent_id)


def get(agent_id: str) -> Optional[Dict[str, Any]]:
    """The CURRENT designation, or None when this seat is not a resident.

    None is the ordinary answer for most seats and is not an error: residency is a deliberate
    status, not the default.
    """
    ratified = [r for r in _records(agent_id) if r.get("state") == RATIFIED]
    if not ratified:
        return None
    current = dict(ratified[-1])
    # `formerly:` is DERIVED from the log rather than maintained beside it, so the two can never
    # disagree. Order preserved, duplicates collapsed, the active name excluded.
    formerly: List[str] = []
    for r in ratified[:-1]:
        cs = r.get("callsign")
        if cs and cs != current.get("callsign") and cs not in formerly:
            formerly.append(cs)
    current["formerly"] = formerly
    return current


def designation(agent_id: str) -> str:
    """Render the full designation, omitting fields that were never set.

    'Deepseek | Onyx | Red | 3 - Foxbat' when complete; degrades to just the callsign when the
    family and team planes have not been decided yet -- which is the live state, and a renderer
    that demanded them would block the slice on a naming decision that is Daniil's to make.
    """
    rec = get(agent_id)
    if not rec:
        return ""
    parts = [p for p in (rec.get("vendor"), rec.get("family"), rec.get("team")) if p]
    tail = rec.get("callsign") or ""
    if rec.get("number") is not None:
        tail = f"{rec['number']} - {tail}"
    parts.append(tail)
    return " | ".join(parts)


def boot_block(agent_id: str) -> str:
    """The lines a resident's boot fold carries so it can answer 'who am I, and why'.

    This is the whole point of the slice. The callsign AND the receipts ride the fold, because
    a name whose evidence is only in the archive is a claim the resident cannot support at the
    moment it is asked. Returns "" for a non-resident -- absence of a designation is silence,
    never a warning, because most seats are not residents.
    """
    rec = get(agent_id)
    if not rec:
        return ""
    lines = [f"# YOU ARE: {designation(agent_id)}"]
    receipts = rec.get("receipts") or []
    if receipts:
        lines.append("#   earned by: " + ", ".join(str(r) for r in receipts))
        lines.append("#   (drill any of them: py agent_cli.py recall --full learn:experiment:<name>)")
    if rec.get("formerly"):
        lines.append("#   formerly: " + ", ".join(rec["formerly"]))
    return "\n".join(lines)
