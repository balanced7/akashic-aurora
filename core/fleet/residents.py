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

#: T259 -- ONE global append-only stream of role assignments, each record carrying its agent.
#: One log rather than per-agent shards because the load-bearing query is CROSS-resident
#: ("All Jesters on Red of exercise 7") and a single scan cannot miss a shard. Projection cost
#: is O(assignments); at fleet scale that is tens of rows, and the posture is stated here so
#: the day it grows chatty the revisit has an address.
_ROLES_KEY = "residents:roles:log"

NOMINATED = "nominated"
RATIFIED = "ratified"
PLACED = "placed"


def _store():
    return create_store()


class ReceiptStoreUnavailable(RuntimeError):
    """The archive could not be consulted, so receipt authorship is UNKNOWN.

    T262, found by the kill-drill's resident arm: this used to be swallowed into a plain
    None, which `nominate` reads as "the receipt does not resolve" and refuses on. That made
    a store outage render a VERDICT about someone's callsign evidence. UNKNOWN and ABSENT
    are different answers and only one of them is about the receipt.
    """


def _corrupt_row(where: str, index: int, raw: str) -> None:
    """A dropped record announces itself. Never silent.

    T262: `except: continue` made a lost row invisible to every caller, in a module whose
    own docstring says absence must not read as success -- the T178 guard-of-guards shape,
    committed by the author of the lecture. stderr because it is the channel a human and a
    subprocess-capturing test both actually read; the good rows still return, so one bad row
    cannot hide the rest.
    """
    import sys as _sys
    print(f"[residents] CORRUPT ROW at {where}[{index}] -- unreadable and SKIPPED "
          f"({str(raw)[:60]!r}). The remaining rows are intact; this one is lost.",
          file=_sys.stderr)


def _receipt_author(experiment: str) -> Optional[str]:
    """Who authored the lesson `experiment`, or None when the lesson genuinely is not there.

    None means ABSENT -- a real answer about a real lookup. A store that could not be
    consulted raises ReceiptStoreUnavailable instead, because the caller must be able to
    tell "there is no such lesson" from "I could not look", and only the first is evidence
    about the nominee.
    """
    try:
        from core.learning.learning_store import get_learning_store
        # _load_experiment is the only exact-key read the store offers; every public accessor
        # searches. Noted as owed ergonomics rather than worked around silently.
        rec = get_learning_store()._load_experiment(experiment)
    except Exception as e:
        raise ReceiptStoreUnavailable(f"{type(e).__name__}: {e}") from e
    if not rec:
        return None
    # .strip() per deepseek's T258 review: a stored agent_id carrying stray whitespace would
    # otherwise refuse a VALID receipt -- erring strict, but still drift from the stated rule.
    # The nominee and nominator already get this treatment; the author must too.
    return str(rec.get("agent_id") or rec.get("agent") or "").strip() or None


def _records(agent_id: str) -> List[Dict[str, Any]]:
    key = _LOG_KEY.format(agent=agent_id)
    raw = _store().lrange(key, 0, -1) or []
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(raw):
        try:
            out.append(json.loads(r))
        except Exception:
            _corrupt_row(key, i, r)       # loud: a lost row must never be invisible (T262)
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
        try:
            author = _receipt_author(r)
        except ReceiptStoreUnavailable as e:
            # UNKNOWN, and it must not masquerade as a verdict about the receipt. Refusing is
            # still correct -- an unverified receipt may not mint a callsign -- but the reason
            # given is the outage, so nobody reads it as "your evidence is bad" (T262).
            raise ValueError(
                f"refused: could not verify receipt '{r}' -- the archive is UNAVAILABLE "
                f"({e}). This is UNKNOWN, not a judgement about the receipt: retry when the "
                f"store is reachable rather than treating this as a failed nomination."
            ) from e
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

    WHEN SEVERAL DRAFTS SHARE THE CALLSIGN (two nominators, different receipts), the LATEST
    nomination is the one confirmed -- the ceremony has one active draft per callsign and it is
    the newest. deepseek's T258 review named this as the only ceremony path where the door does
    something other than what the caller may have meant rather than refusing, so the choice is
    stated here, pinned, and the returned record carries the receipts it confirmed: the
    ratifier must be able to SEE what they signed.
    """
    nominee = str(nominee or "").strip()
    callsign = str(callsign or "").strip()
    records = _records(nominee)
    draft = None
    for rec in records:
        if rec.get("state") == NOMINATED and rec.get("callsign") == callsign:
            draft = rec                   # last match wins -- the newest draft is the live one
    if draft is None:
        # Distinguish "never nominated at all" from "nominated under a different name" -- a
        # refusal that names the open drafts saves the ratifier a lookup (review point 4).
        open_drafts = sorted({r.get("callsign") for r in records if r.get("state") == NOMINATED
                              and r.get("callsign")})
        hint = (f" Open draft(s) for '{nominee}': {', '.join(open_drafts)}."
                if open_drafts else "")
        raise ValueError(
            f"refused: '{callsign}' was never nominated for '{nominee}'. Ratification confirms "
            f"a draft; it does not author one.{hint}"
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
    # T267: the POSTING is projected onto the identity, not stored in it. The latest placement
    # wins; an unposted resident keeps whatever the nomination carried, which is usually
    # nothing -- and nothing must render as ABSENT rather than as an empty field.
    for rec in _records(agent_id):
        if rec.get("state") == PLACED:
            for f in ("family", "team", "number", "vendor"):
                v = rec.get(f)
                if v not in (None, ""):
                    current[f] = v
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


def place(*, agent: str, family: str = "", team: str = "", number: Optional[int] = None,
          vendor: str = "", by: str = "") -> Dict[str, Any]:
    """Post a resident to a family, a team and a number. NOT a re-naming.

    Naming and posting are different acts. Ceremony rule 1 forbids naming yourself; it says
    nothing about where you are POSTED, and posting is an org decision. Routing this through
    nominate+ratify would mean re-ratifying an identical callsign purely to set a field --
    filling the naming history with records that decide nothing, and minting a `formerly:`
    entry for a name that never changed.

    Appends, like everything else here. A re-posting leaves the prior posting intact, because
    "who was in Onyx during exercise 7" is a question about the past and an update-in-place
    would erase the only record that can answer it.

    THIS VERB IS DELIBERATELY CLI-ONLY, and the reason belongs here rather than only in the
    door-parity manifest where Heimdall's review found it hiding. Placing into a family has
    ROUTING consequences: once T108 addresses families, a seat that could place ITSELF into
    Onyx would be opting into work addressed to Onyx -- a capability grant by self-declaration,
    the T255 class wearing an org chart. `assign` is different and is allowed on the agent
    surface: the directive licenses a "declarable job title", and provenance is DERIVED from
    `by`, so a self-assigned role is legal AND labelled. A self-assigned Jester cannot redirect
    a work stream; a self-placed Onyx member could. That is the whole cut.
    """
    agent = str(agent or "").strip()
    by = str(by or "").strip()
    if not agent or not by:
        raise ValueError("place needs an agent and an actor (`by`)")
    if get(agent) is None:
        raise ValueError(
            f"refused: '{agent}' is not a resident (no ratified designation), so there is "
            f"nowhere to post them. Run the ceremony first: py agent_cli.py resident nominate "
            f"{agent} --callsign <name> --receipt <their lesson> --by <peer>"
        )
    # VENDOR IS SETTABLE HERE, and that is the substrate-change path the design promised. The
    # atom's rule is that vendor is a MUTABLE attribute so a model upgrade renders as a flagged
    # substrate change instead of orphaning the archive -- but until now it could only be set at
    # NOMINATION, which meant re-homing a resident required re-naming it. Found by a pin of this
    # slice failing for the "wrong" reason: the gap was real and the pin was right by accident.
    return _append(agent, {
        "state": PLACED, "agent_id": agent, "family": str(family or "").strip(),
        "team": str(team or "").strip(), "number": number,
        "vendor": str(vendor or "").strip(), "by": by, "at": time.time(),
    })


def placement_history(agent_id: str) -> List[Dict[str, Any]]:
    """Every posting this resident has held, oldest first. Nothing is removed."""
    return [r for r in _records(agent_id) if r.get("state") == PLACED]


def current_placement(agent_id: str) -> Optional[Dict[str, Any]]:
    """The latest posting, projected -- or None, which is the ordinary state."""
    h = placement_history(agent_id)
    return h[-1] if h else None


def family_members(family: str) -> List[str]:
    """Who is currently posted to `family`. Empty is empty, never everyone.

    A family you cannot enumerate is decoration: the family half of routing needs members to
    address, and a filter that fell back to the full roster would be the wider-than-the-thing-
    it-replaces defect wearing an org chart.
    """
    want = str(family or "").strip().lower()
    if not want:
        return []
    out = []
    try:
        for agent in (_store().lrange(_INDEX_KEY, 0, -1) or []):
            cur = current_placement(agent)
            if cur and str(cur.get("family") or "").strip().lower() == want:
                out.append(agent)
    except Exception:
        return []
    return sorted(out)


def team_members(team: str) -> List[str]:
    """Who is currently posted to `team`. The standing disposition, not the per-exercise side
    -- that is an assignment event (T259) and deliberately a different plane."""
    want = str(team or "").strip().lower()
    if not want:
        return []
    out = []
    try:
        for agent in (_store().lrange(_INDEX_KEY, 0, -1) or []):
            cur = current_placement(agent)
            if cur and str(cur.get("team") or "").strip().lower() == want:
                out.append(agent)
    except Exception:
        return []
    return sorted(out)


def catchup_pack(agent_id: str, topic: str, k: int = 6):
    """The T261 catch-up: what THIS resident already knows that bears on `topic`.

    Returns (text_block, meta) -- the identity block plus up to `k` of the resident's OWN
    archive lessons relevant to the topic, ready to ride a system context. Empty block when
    the seat is not a resident (the caller decides whether that refuses; this function only
    reports). The pack comes FROM THE STORE, which is the whole point: memory that crosses
    invocations lives where the fleet can inspect it (ask.py's own no-shadow-history law),
    and the branch READS it on the way in. T260's agent scope guarantees the pack contains
    only the named resident's lessons -- a resident is not a fleet-corpus reader.
    """
    rec = get(agent_id)
    if not rec:
        return "", {"resident": False}
    lines = [boot_block(agent_id)]
    ids = []
    try:
        from core.learning.learning_store import get_learning_store
        hits = get_learning_store().search_learnings_by_keyword(topic, agent=agent_id)[:max(0, int(k))]
        if hits:
            lines.append("# WHAT YOU ALREADY KNOW (your own archive, most relevant first):")
            for h in hits:
                ids.append(str(h.get("id")))
                gist = str(h.get("recommendation") or h.get("actual") or h.get("what_tried") or "")
                gist = " ".join(gist.split())[:240]
                lines.append(f"#   - {h.get('id')}: {gist}")
    except Exception:
        # A store fault must not turn a resident ask into a silent blind one WITHOUT saying
        # so -- the meta records that the pack could not be read; the identity still rides.
        return "\n".join(lines), {"resident": True, "catchup": [], "catchup_error": True}
    return "\n".join(lines), {"resident": True, "catchup": ids}


def assign(*, agent: str, role: str, side: str = "", exercise: str = "",
           by: str = "") -> Dict[str, Any]:
    """Record that a resident is OPERATING AS `role` -- an event, never a field.

    Identity is permanent; the job is situational. Rook stays Rook while operating as Jester
    on Red in exercise 7, and when the job changes the old assignment SURVIVES, because the
    query Daniil named -- who was operating as what, when -- is a question about the past and
    an update-in-place would erase the only record that can answer it.

    PROVENANCE IS DERIVED, NOT DECLARED: by == agent renders `self-declared`, anyone else
    renders `assigned`. His phrase was "declarable job title", so self-declaration is legal --
    but T255 is open one plane down on exactly the defect of a player-declared field nothing
    verifies, so the label must exist and must be filterable. Deriving it from `by` means it
    cannot be forged by passing a flag.

    Refuses a non-resident: roles live on the identity sheet, and a seat with no sheet has
    nowhere to wear one. The refusal points at the ceremony that fixes it.
    """
    agent = str(agent or "").strip()
    role = str(role or "").strip()
    by = str(by or "").strip()
    if not agent or not role or not by:
        raise ValueError("assign needs an agent, a role and an assigner (`by`)")
    if get(agent) is None:
        raise ValueError(
            f"refused: '{agent}' is not a resident (no ratified designation), so there is no "
            f"identity sheet to carry a role. Run the ceremony first: py agent_cli.py resident "
            f"nominate {agent} --callsign <name> --receipt <their lesson> --by <peer>"
        )
    rec = {
        "agent_id": agent, "role": role, "side": str(side or "").strip(),
        "exercise": str(exercise or "").strip(), "by": by, "at": time.time(),
        "provenance": "self-declared" if by.lower() == agent.lower() else "assigned",
    }
    _store().rpush(_ROLES_KEY, json.dumps(rec, ensure_ascii=False))
    return rec


def _role_records() -> List[Dict[str, Any]]:
    raw = _store().lrange(_ROLES_KEY, 0, -1) or []
    out: List[Dict[str, Any]] = []
    for i, r in enumerate(raw):
        try:
            out.append(json.loads(r))
        except Exception:
            _corrupt_row(_ROLES_KEY, i, r)   # loud: a lost assignment is a lost timeline (T262)
    return out


def roles(*, agent: Optional[str] = None, role: Optional[str] = None,
          side: Optional[str] = None, exercise: Optional[str] = None,
          provenance: Optional[str] = None) -> List[Dict[str, Any]]:
    """The projection: every assignment matching every given filter, oldest first.

    "All Jesters on Red of exercise 7" is roles(role="Jester", side="Red", exercise="E7").
    A filter nothing matches returns [] -- never the unfiltered log, because a fallback wider
    than the thing it replaces is the audited defect class (the degraded answer must be a
    SUBSET of the normal one).
    """
    out = []
    for rec in _role_records():
        if agent is not None and rec.get("agent_id") != agent:
            continue
        if role is not None and rec.get("role") != role:
            continue
        if side is not None and rec.get("side") != side:
            continue
        if exercise is not None and rec.get("exercise") != exercise:
            continue
        if provenance is not None and rec.get("provenance") != provenance:
            continue
        out.append(rec)
    return out


def role_history(agent_id: str) -> List[Dict[str, Any]]:
    """Every assignment this resident has ever held, oldest first. Nothing is ever removed."""
    return roles(agent=agent_id)


def current_role(agent_id: str) -> Optional[Dict[str, Any]]:
    """The LATEST assignment, projected -- or None, which is the ordinary state, not an error."""
    hist = role_history(agent_id)
    return hist[-1] if hist else None


def _default_lesson_lookup(slug: str) -> Dict[str, Any]:
    """The store read behind W150's inline receipts. Import-at-call so the module
    attribute is live (tests fake the store by patching learning_store); ANY failure
    is the caller's cue to render the bare slug -- never a boot cost."""
    import core.learning.learning_store as _ls
    return _ls.get_learning_store_instance()._load_experiment(slug) or {}


def boot_block(agent_id: str, lesson_lookup=None) -> str:
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
        # W150: a badge that names its lessons without their content is a claim the
        # resident cannot USE at the moment of identity -- the 08-12 seat walked into
        # the exact failure its own badge slug named. Inline each receipt's
        # recommendation clause (clipped, word-boundary); degrade to the bare slug on
        # ANY store trouble -- the badge never costs a boot (fence contract B2).
        for r in receipts:
            line = "#   earned by: " + str(r)
            try:
                rec_l = (lesson_lookup or _default_lesson_lookup)(str(r)) or {}
                tip = " ".join(str(rec_l.get("recommendation") or "").split())
                if tip:
                    from core.primitives.distiller import _clip_words
                    line += " -- " + _clip_words(tip, 130)
            except Exception:
                pass                       # slug alone; one bad slug breaks nothing
            lines.append(line)
        lines.append("#   (drill any of them: py agent_cli.py recall --full learn:experiment:<name>)")
    if rec.get("formerly"):
        lines.append("#   formerly: " + ", ".join(rec["formerly"]))
    # T259: the situational half of the sheet -- what this resident is DOING right now, beside
    # who it permanently IS. Absent when no assignment exists: no role is the ordinary state.
    job = current_role(agent_id)
    if job:
        where = " / ".join(p for p in (job.get("side"), job.get("exercise")) if p)
        tag = "" if job.get("provenance") == "assigned" else " [self-declared]"
        lines.append(f"#   operating as: {job['role']}" + (f" ({where})" if where else "") +
                     f" -- by {job.get('by')}{tag}")
    return "\n".join(lines)
