"""The scout -- the first calibrated role: read-only pre-flight, worn not owned.

Semantic Relationship: Scout wears Resident (assignment event); Scout remembers via Verdicts.

WHY THIS EXISTS (T292, fence r2 reconciled -- docs/library/design/20260812_fence-r2-reconciliation_825c9a.md):
the two questions whose wrong answers cost rebuilds and collisions are "is another seat
mid-flight in my area" and "has this been done already". Both are answerable from planes
that already exist -- the ledger, the locks, the scout's own filed verdicts -- but only if
someone assembles them at ask time. The scout is that assembly plus the discipline: cite
ids, never propose builds, say UNKNOWN past the pack's edge. Daniil's frame (2026-08-12):
"managing context and setting up helper functions and roles" -- this is both, made one verb.

THE LAWS, each from the round-2 fence:

  THE CUSTODIAN IS THE BUILDER (Navi C3, accepted amended). The pack is MECHANICAL --
  rebuilt from live sources on every call. A curated pack rots silently; a built pack
  cannot rot without a pin going red. Curated scout heuristics belong in verdicts and
  lessons, which the builder folds back in.

  ROLE-SCOPED MEMORY (Heimdall C3). The role's memory is verdicts(role="Scout"),
  whoever filed them. Wearer B reads wearer A's record; the role outlives every wearer.

  WEAR, DON'T OWN (T259's identity/role split). Any resident can wear Scout; wearing is
  an assignment EVENT recorded once per wearer (re-asks refresh nothing -- the sheet
  records the job, the verdict stream records the acts). A blind tier-0 branch may run
  the scout pipeline without an identity sheet: it files under agent='blind' and skips
  the ceremony -- there is nothing to wear it on.

  BOUNDS HONESTY (T120). The pack declares each section and its count; an empty section
  renders '(none)'; an unreadable source renders UNREADABLE. The charter tells the model
  the pack is the WHOLE world -- past its edge the honest answer is UNKNOWN.

NOT IN THIS MODULE, deliberately: mail routing to the role (T108's queue -- no rival
addressing scheme), cold-twin sampling and rate rendering (RC2/T291), and any write
capability at all -- the scout is read-only by charter, and the one thing it writes is
its own verdict, which is a record about itself.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional, Tuple

SCOUT_ROLE = "Scout"

#: The charter rides every scout ask as system context, ABOVE the pack. It is the role's
#: law stated to the model that wears it -- descriptive discipline, citation duty, and the
#: UNKNOWN-past-the-edge rule (the L1 danger zone: a scout that speculates is a hazard).
CHARTER = (
    "# SCOUT CHARTER -- you are the fleet's read-only pre-flight.\n"
    "# You answer exactly two kinds of question: 'is another seat mid-flight in this "
    "area' and 'has this been done already'.\n"
    "# RULES: cite ledger ids, lock paths+holders and verdict ask_ids FROM THE PACK "
    "below; never propose building anything; a DONE row is a closed answer, not a "
    "starting point. An absence claim must state what you searched ('no claimed row or "
    "lock mentions X in the sections below'). The pack is your WHOLE world: past its "
    "edge, answer UNKNOWN -- a scout that guesses is worse than no scout.\n"
)


def _section(title: str, rows) -> str:
    body = "\n".join(f"  {r}" for r in rows) if rows else "  (none)"
    return f"## {title}\n{body}"


def build_pack(*, for_wearer: str = "", done_limit: int = 12,
               memory_limit: int = 12) -> Tuple[str, Dict[str, Any]]:
    """The scout's world, rebuilt from live sources -- never cached, never curated.

    Returns (text, meta). meta["sections"] carries a count per section so the surface
    declares its bounds (T120); a source that cannot be read counts -1 and renders
    UNREADABLE -- an unreadable plane must never look like an empty one (T178).
    `for_wearer` is informational (it rides meta for the drills and the render); the
    pack's CONTENT is deliberately identical for every wearer -- that is what makes the
    role's knowledge the role's.
    """
    sections: Dict[str, int] = {}
    parts = []

    # IN FLIGHT + RECENTLY DONE -- the ledger, read the way the conductor reads it.
    try:
        from core.coord.task_ledger import read_ledger
        tasks = (read_ledger() or {}).get("tasks") or []
        inflight = [t for t in tasks if t.get("status") in ("claimed", "verifying")]
        done = [t for t in tasks if t.get("status") == "done"][-max(0, int(done_limit)):]
        inf_rows = [f"{t.get('id')} [{t.get('status')}] owner={t.get('owner') or '?'} -- "
                    f"{' '.join(str(t.get('title') or '').split())[:110]}" for t in inflight]
        done_rows = [f"{t.get('id')} [done] -- "
                     f"{' '.join(str(t.get('title') or '').split())[:110]}" for t in done]
        parts.append(_section("IN FLIGHT (claimed/verifying -- someone is HERE)", inf_rows))
        parts.append(_section(f"RECENTLY DONE (last {done_limit} -- closed, never redo)",
                              done_rows))
        sections["in_flight"] = len(inf_rows)
        sections["recently_done"] = len(done_rows)
    except Exception as e:
        parts.append(f"## IN FLIGHT\n  UNREADABLE ({type(e).__name__}: {e})")
        parts.append("## RECENTLY DONE\n  UNREADABLE (same fault)")
        sections["in_flight"] = sections["recently_done"] = -1

    # LIVE LOCKS -- who holds what right now, with the WHY the holder recorded.
    try:
        from core.comm.locks import LockManager
        lks = LockManager("scout_pack").list_locks() or []
        lk_rows = [f"{lk.get('path')} held by {lk.get('agent')}"
                   + (f" -- {lk.get('note')}" if lk.get("note") else "") for lk in lks]
        parts.append(_section("LIVE LOCKS (advisory -- a held path is a busy area)", lk_rows))
        sections["locks"] = len(lk_rows)
    except Exception as e:
        parts.append(f"## LIVE LOCKS\n  UNREADABLE ({type(e).__name__}: {e})")
        sections["locks"] = -1

    # SCOUT MEMORY -- the role's own record, whoever wore it (H-C3: role-scoped).
    try:
        from core.fleet.verdicts import verdicts
        mem = verdicts(role=SCOUT_ROLE)[-max(0, int(memory_limit)):]
        mem_rows = [f"{v.get('ask_id')} [{v.get('question_shape')}] by {v.get('agent_id')}"
                    f" -- {v.get('gist')}" for v in mem]
        parts.append(_section("SCOUT MEMORY (this role's past verdicts, any wearer)", mem_rows))
        sections["scout_memory"] = len(mem_rows)
    except Exception as e:
        parts.append(f"## SCOUT MEMORY\n  UNREADABLE ({type(e).__name__}: {e})")
        sections["scout_memory"] = -1

    meta = {"sections": sections, "for_wearer": for_wearer, "built_at": time.time()}
    return "\n\n".join(parts), meta


def scout_ask(question: str, *, wearer: str = "deepseek", by: str = "claude",
              blind: bool = False, question_shape: str = "descriptive",
              client=None, model: Optional[str] = None) -> Dict[str, Any]:
    """One door: wear the role, read the world, answer, file the verdict.

    Resident tier by default (the wearer's own archive rides via T261); blind=True runs
    tier-0 -- no identity, no ceremony, agent='blind' on the verdict. Either way the
    verdict files under role=Scout, so the ROLE accumulates regardless of who answered
    -- and stays visibly unadjudicated until an operator rules (T290).
    """
    question = str(question or "").strip()
    if not question:
        raise ValueError("scout_ask needs a question -- the scout answers, it does not roam")

    from core.comm import ask as ask_mod
    from core.fleet import verdicts as V

    pack_text, meta = build_pack(for_wearer=("" if blind else wearer))

    if not blind:
        # Wear the role ONCE per wearer: the sheet records the standing job; each act is
        # already a verdict record. Re-assigning per ask would flood the role log with
        # events that decide nothing (the T267 "records deciding nothing" smell).
        from core.fleet import residents as R
        cur = R.current_role(wearer)
        if not cur or cur.get("role") != SCOUT_ROLE:
            R.assign(agent=wearer, role=SCOUT_ROLE, by=by)

    o = ask_mod.ask(question, system=CHARTER + "\n" + pack_text, client=client,
                    model=model, as_resident=(None if blind else wearer))
    answer = str((o.detail or {}).get("answer") or "")

    # uuid4, not a counter: minting by counting-up is the T227 collision class, and the
    # verdict plane's dedup makes a collision a REFUSAL, so the id must be born unique.
    ask_id = f"scout-{uuid.uuid4().hex[:12]}"
    V.file_verdict(agent=("blind" if blind else wearer), ask_id=ask_id,
                   question_shape=question_shape,
                   gist=answer or "(no answer -- ask failed)",
                   role=SCOUT_ROLE)

    return {"answer": answer, "ask_id": ask_id, "ok": bool(o.ok),
            "tier": ("blind" if blind else "resident"), "pack_meta": meta,
            "why": ("" if o.ok else str(getattr(o, "why", "") or ""))}
