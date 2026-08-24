"""Arch-slice loader (Context pillar): boot-time ORIENTATION to the code region of the current task.

RENEW Strand E gap #2 / the design doc's deferred step #3 ("Surface->orientation",
docs/library/design/20260701_the-mediation-membrane-founding-design-n_4f941f.md). A cold-resuming agent already gets the task ledger, ranked
lessons, durable notes and the funnel -- but nothing pointing it at WHICH subsystem the current task
lives in, so it rediscovers the code layout by re-reading. This projects the STABLE architecture map
(docs/ARCHITECTURE.md) down to the few subsystems most relevant to the task, each with its code path.

Design (same discipline as recall-at-action):
- **Deterministic, no-LLM** -- keyword relevance via the shared Ranker.
- **A PROJECTION over a stable source**, not a hand-maintained manual that rots (the living-docs lesson).
- **Show-nothing below a relevance floor** -- an orientation that doesn't match the task is worse than
  silence (context-rot). We gate on the Ranker's RELEVANCE component specifically, not the blended
  score, so a merely-recent-or-important section never fires for an unrelated task.
- **Fail-soft** -- any error (missing/renamed doc, parse issue) degrades to [] and never bricks boot.

See docs/library/report/20260707_renew-strand-e-cold-resume-fidelity-empi_890e10.md.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

_HEADING_RE = re.compile(r"^##\s+(.*)$")
# a code path is a backtick-wrapped token ending in '/', e.g. `core/comm/` -- present in the heading
# or body of a genuine subsystem section, absent from meta sections (layer stack / where-to-start /
# anti-rot contract), which is exactly the filter we want (no hardcoded skip-list).
_PATH_RE = re.compile(r"`([\w./-]+/)`")


def _repo_docs_dir() -> str:
    # this file: <repo>/context/arch_loader.py -> <repo>/docs
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")


def _parse_sections(md_path: str) -> List[Dict[str, str]]:
    """Split an architecture markdown into its H2 sections: {heading, body, path}. Fail-soft -> []."""
    out: List[Dict[str, str]] = []
    try:
        with open(md_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return out
    cur: Optional[Dict[str, str]] = None
    for ln in lines:
        m = _HEADING_RE.match(ln.rstrip("\n"))
        if m:
            if cur:
                out.append(cur)
            cur = {"heading": m.group(1).strip(), "body": ""}
        elif cur is not None:
            cur["body"] += ln
    if cur:
        out.append(cur)
    for s in out:
        pm = _PATH_RE.search(s["heading"]) or _PATH_RE.search(s["body"])
        s["path"] = pm.group(1) if pm else ""
    return out


def load_arch_slice(task: str, *, top_k: int = 3, min_relevance: float = 0.2,
                    now: Optional[float] = None, docs_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """The few architecture subsystems most relevant to `task`, each with its code path.

    Returns a small list of {heading, path, source}, best-first. Empty task, no parseable sections, or
    nothing above the relevance floor -> [] (show-nothing). Deterministic + fail-soft.
    """
    if not task or not task.strip():
        return []
    docs_dir = docs_dir or _repo_docs_dir()
    sections = _parse_sections(os.path.join(docs_dir, "ARCHITECTURE.md"))
    # Only real subsystem sections are orientation targets: those carrying a code path DEEPER than the
    # whole tree (>=2 segments, e.g. `core/comm/`). Meta sections (layer stack, where-to-start) have no
    # path; the anti-rot contract mentions a bare `core/` -- both dropped by construction, no skip-list.
    subsystems = [s for s in sections if s["path"] and s["path"].count("/") >= 2]
    if not subsystems:
        return []
    try:
        from core.primitives.ranker import Ranker
    except Exception:
        return []
    items = [{"text": s["heading"] + "\n" + s["body"], "importance": 3,
              "heading": s["heading"], "path": s["path"]} for s in subsystems]
    out: List[Dict[str, Any]] = []
    for sc in Ranker().rank(items, query=task, now=now):
        if sc.components.get("relevance", 0.0) < min_relevance:
            continue   # show-nothing floor: the section must actually match THIS task
        it = sc.item
        out.append({"heading": it["heading"], "path": it.get("path", ""),
                    "source": "docs/ARCHITECTURE.md"})
        if len(out) >= top_k:
            break
    return out
