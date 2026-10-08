"""W0 -- the authored world-state journal for the one-world UI core.

Spec: atom art_20261008_one-world-ui-core-reconciled-spec_d622ac (H9), section 1-2. This is the
settled, uncontested foundation (Heimdall's take): authored facts live in an append-only, tracked
journal; every surface is a rebuildable projection replayed from it; a surface is a projection,
never a store. If a surface drifts, you replay it -- you never diff it back into line.

NAME NOTE: this package is `core.oneworld`, not `core.world`. `core/world.py` is a different,
load-bearing module (prod/sandbox WORLD resolution). They must not be confused, and a `core/world/`
package would shadow that file. "world-state" here means the UI's model of what is happening, not
which environment the process is in.

Modeled directly on core/eye/routes.py, which already runs this discipline for routes:

    state/oneworld/world.jsonl   append-only, TRACKED   -- the authored truth (the Ledger half)
    replay()                     the rebuildable read    -- a projection, holds no state of its own

Two guards copied from the neighbour, not just its shape:

  * IDEMPOTENCY BY CONTENT HASH. A fact id is a hash of its content, so a crash-redelivered or
    double-written fact is the SAME line (routes.py P2). The id deliberately excludes `at`, so the
    same content is one fact however many times it is written. A caller that needs two
    genuinely-distinct facts with identical content puts a distinguishing value in the payload --
    the same contract routes.py has for identical-content routes.

  * HONEST REPLAY. replay() is explicit about drops: a line it cannot parse is COUNTED as
    `unparsed`, never silently discarded. A reader that counts only what it kept is a tautology
    (a_report_that_counts_survivors), and this house has paid for that silence repeatedly. So the
    arithmetic is `taken + unparsed`, and both are returned.

W0 deliberately does NOT include: a SQLite projection (routes.py keeps one; the world core does not
need one yet -- replay() is the projection read, and the journal is small); the mode schema (its
own slice, and it wants the reconciliation's ratification); the floor; the bounds-legend primitive
(W1). Those render on top of this.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Module-level so tests (and a future config pass) can repoint it. AKASHIC_ONEWORLD_JOURNAL
# overrides it live without an import-order dance; tests monkeypatch this constant directly, as
# routes.py's tests do with JOURNAL_PATH.
JOURNAL_PATH = _REPO_ROOT / "state" / "oneworld" / "world.jsonl"

SCHEMA_VERSION = 1


def _journal_path() -> Path:
    return Path(os.environ.get("AKASHIC_ONEWORLD_JOURNAL") or str(JOURNAL_PATH))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fact_id(kind: str, actor: str, payload: Dict[str, Any],
            session_id: Optional[str]) -> str:
    """Content-hash id (routes.py's physics answer). The SAME authored content is the SAME fact,
    however many times a crash or a double-write replays it. `at` is excluded on purpose, so the
    hash depends only on what was asserted, not when."""
    blob = json.dumps(
        {"kind": kind, "actor": actor, "payload": payload, "session_id": session_id},
        sort_keys=True, ensure_ascii=False)
    return "wf_" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def append(kind: str, actor: str, payload: Dict[str, Any], *,
           session_id: Optional[str] = None) -> str:
    """Record one authored world-fact: journal first (the durable truth), and nothing else -- the
    projection is replay(). Returns the content-hash id. Writing the same content twice is one
    fact (idempotency), so this is safe under crash-redelivery and double-write.

    An OPEN vocabulary: `kind` is any string. There is deliberately no allowed-kinds set to rot --
    the house rule is markers are derived, never declared, and a closed vocabulary becomes a
    classification bottleneck between independently built surfaces. Resolution is the reader's job
    (a later slice), and it is TOTAL there, never a silent default here.
    """
    kind = " ".join(str(kind).split())
    if not kind:
        raise ValueError("a world-fact needs a kind -- it is how a projection decides to draw it")
    actor = str(actor)
    payload = dict(payload or {})
    rid = fact_id(kind, actor, payload, session_id)
    rec = {
        "v": 1, "id": rid, "kind": kind, "actor": actor, "payload": payload,
        "session_id": session_id, "at": _now_iso(), "schema_version": SCHEMA_VERSION,
    }

    jp = _journal_path()
    jp.parent.mkdir(parents=True, exist_ok=True)

    # Dedup against the journal: an id already present means this exact content is already recorded.
    # A corrupt line in the file is not a reason to re-write a good fact, so bad lines are skipped
    # here the same way replay() counts them -- never fatal, never silent to the degree that it
    # drops a real write.
    already = False
    if jp.exists():
        for line in jp.read_text(encoding="utf-8").splitlines():
            try:
                if json.loads(line).get("id") == rid:
                    already = True
                    break
            except Exception:
                continue
    if not already:
        with open(jp, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rid


def replay() -> Dict[str, Any]:
    """Rebuild the world history from the journal alone -- a cold read that holds no state. This IS
    the projection: wiping any derived surface loses nothing authored, because the journal is the
    truth and this re-derives from it (routes.py P5, the replay-don't-diff law).

    Returns {"facts": [...in authored order, deduped by id...], "taken": N, "unparsed": M}. The two
    counts must account for every line: a line that does not parse, or carries no id, is COUNTED as
    unparsed, never dropped in silence.
    """
    jp = _journal_path()
    if not jp.exists():
        return {"facts": [], "taken": 0, "unparsed": 0}

    facts: List[Dict[str, Any]] = []
    seen = set()
    unparsed = 0
    for line in jp.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            unparsed += 1
            continue
        rid = rec.get("id")
        if not rid or "kind" not in rec:
            unparsed += 1
            continue
        if rid in seen:
            # A duplicate id is idempotency doing its job on replay; keep the first, don't recount.
            continue
        seen.add(rid)
        facts.append({
            "id": rid,
            "kind": rec.get("kind"),
            "actor": rec.get("actor", ""),
            "payload": rec.get("payload", {}),
            "at": rec.get("at", ""),
            "session_id": rec.get("session_id"),
        })
    return {"facts": facts, "taken": len(facts), "unparsed": unparsed}


def kinds() -> set:
    """The set of fact kinds present. Open vocabulary -- this reflects what has been recorded, it
    does not gate what may be."""
    return {f["kind"] for f in replay()["facts"]}
