"""capability_search -- "does this system already do X?", asked at the level of MEANING.

THE WEAKNESS THIS OFFLOADS TO THE SUBSTRATE, measured on one conductor across two days.
Three times I concluded a capability was missing without checking, and all three were
wrong: I scoped a slice to build a peer-liveness reader while `liveness.attendance()` had
existed since T155; I hand-bisected four test failures while `suite_baseline` had recorded
one of them since 2026-07-24; and I filed a wish asserting the naming doctrine was
unguarded while `check_boundaries.py` had been enforcing it in CI since 2026-06-19.

One failure mode in three costumes: INFERRING ABSENCE INSTEAD OF VERIFYING IT. Not
laziness -- verification costs a turn AT THE MOMENT OF THE ASSUMPTION, while being wrong
costs nothing until much later. The only thing that changes that behaviour is making the
check cheaper than the assumption, at the moment of assuming. So this is deliberately one
call, ~20 seconds, under a cent.

WHY `discover` COULD NOT ANSWER IT. That verb is a SUBSTRING filter over verb names and
purposes. Asked "check whether a test failure is pre-existing" it returns 0 matches, with
`suite-baseline` sitting in the very list it searched. Same shape as every other gap this
session: check_boundaries matches duplicate TOKENS and misses forked MEANINGS; delta()
matched node-id SETS and missed attribution; the unread counter matched KINDS and missed
actionability. The substrate is token-strong and meaning-blind. This is a meaning layer
over inputs the substrate already publishes -- it invents no new source of truth.

THE REQUIREMENT THAT OUTRANKS EVERY OTHER ONE: a tool built to stop me fabricating absence
must never fabricate absence itself. A dead key, a timeout, a truncated reply, or an
answer that wandered off-format all render UNKNOWN -- never "no". "No such capability" is
reserved for a healthy call that produced a well-formed answer, and even then it is
labelled a MODEL READ rather than a lookup, because letting an inference inherit a
lookup's authority is exactly the laundering the relationship-plane design forbids one
level up.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[2]

#: What the model is allowed to reason from. Both are substrate-published surfaces: the
#: verb table is generated from the parser, the module index from the tree.
DEFAULT_FILES = ("docs/MODULE_INDEX.md",)

_SHAPE = """Answer ONLY from the attached files. Do not speculate about code you cannot \
see, and do not answer from memory of other repositories.

CAPABILITY WANTED: {query}

Reply in exactly this shape, nothing else:
EXISTS: yes | partially | no
WHAT: the verb or module that provides it, cited -- or "nothing in the attached files"
GAP: what it does not cover
NEAREST MISS: the closest thing that is NOT it, and why it is not"""


def _ask(prompt: str, files: List[str], **kw):
    """Seam. Injected in pins so the taxonomy is testable without spending a call."""
    from core.comm.ask import ask
    return ask(prompt, with_files=files, **kw)


def _field(text: str, name: str) -> str:
    m = re.search(rf"^{name}\s*:\s*(.+)$", text or "", re.I | re.M)
    return (m.group(1).strip() if m else "")


def _verb_table() -> Optional[str]:
    """The generated verb list, written where --with can reach it. Best-effort: if it
    cannot be produced, the module index alone still answers most questions."""
    try:
        from agent_cli import list_verbs
        rows = list_verbs(None)
        path = _ROOT / "research" / "in-flight" / "_verbs_snapshot.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        width = max((len(n) for n, _ in rows), default=0)
        path.write_text("\n".join(f"{n.ljust(width)}  {h}" for n, h in rows),
                        encoding="utf-8")
        return str(path.relative_to(_ROOT)).replace("\\", "/")
    except Exception:
        return None


def find(query: str, *, files: Optional[List[str]] = None) -> Dict[str, Any]:
    """Does this system already do X? Never raises; never invents an absence.

    Returns exists (yes|partially|no|UNKNOWN), what, gap, nearest_miss, confident,
    source, model, usd, why. `confident` is False whenever the answer was truncated,
    malformed, or the call failed -- so a caller can require confidence before acting on
    a "no", which is the only direction that can cost real work.
    """
    def _unknown(why: str, **extra) -> Dict[str, Any]:
        return {"exists": "UNKNOWN", "what": "", "gap": "", "nearest_miss": "",
                "confident": False, "source": "model", "why": why, "usd": None,
                "model": None, **extra}

    paths = list(files) if files else [p for p in DEFAULT_FILES
                                       if (_ROOT / p).exists()]
    if files is None:
        vt = _verb_table()
        if vt:
            paths.insert(0, vt)
    if not paths:
        return _unknown("no substrate surfaces available to search "
                        "(module index missing and verb table unbuildable)")

    try:
        o = _ask(_SHAPE.format(query=str(query)), paths)
    except Exception as e:
        return _unknown(f"capability search could not run ({e.__class__.__name__})")

    detail = getattr(o, "detail", None) or {}
    if not getattr(o, "ok", False):
        # A closed door, a timeout, a starved answer. NOT a statement about the world.
        return _unknown(f"could not be answered: {getattr(o, 'why', '') or 'unreported'}",
                        usd=detail.get("usd"), model=detail.get("model"))

    text = str(detail.get("answer") or "")
    raw = _field(text, "EXISTS").lower()
    exists = next((v for v in ("yes", "partially", "no") if raw.startswith(v)), None)
    if exists is None:
        # The model wandered off the format. A parsing failure must never become a claim.
        return _unknown("the answer did not follow the required shape, so its verdict "
                        "cannot be read -- re-ask rather than assuming absence",
                        usd=detail.get("usd"), model=detail.get("model"))

    return {"exists": exists, "what": _field(text, "WHAT"),
            "gap": _field(text, "GAP"), "nearest_miss": _field(text, "NEAREST MISS"),
            # A truncated answer may have been on its way to saying the opposite.
            "confident": not bool(getattr(o, "partial", False)),
            "source": "model", "model": detail.get("model"),
            "usd": detail.get("usd"),
            "why": (getattr(o, "why", "") if getattr(o, "partial", False) else ""),
            "answer": text}
