"""The fleet roster -- the single source of truth for local models (docs/library/design/20260709_fleet-dispatch-an-intelligent-easy-struc_303d15.md).

Semantic Relationship: Roster projects_over models.json (read-only data).

Model knowledge was FRAGMENTED across a PowerShell array, NOTES.md prose, and a scrubber regex, with
the bakeoff verdicts living only in a chronicle note. This module makes "which models do we have, what
are they good at, and which are disqualified and why" one queryable fact. It PROVIDES specs; it never
drives a process (the launcher scripts still own the environment) and never blocks (missing data -> []).

Pure-local and hermetic by default: models()/get()/select() read a bundled JSON file and touch no
network. Live availability (probe_availability) is opt-in and the only function that talks to Ollama.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models.json")

# Rank order for status when a caller asks broadly (best-first): in-use before proven-idle before
# not-yet-measured; gated never wins a selection (it's disqualified, surfaced only on explicit ask).
_STATUS_RANK = {"active": 0, "tested": 1, "candidate": 2, "gated": 3}


def _load() -> Dict[str, Any]:
    """The raw roster document. Fail-soft: any read/parse problem yields an empty roster, never a raise."""
    try:
        with open(_DATA, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        if isinstance(doc, dict) and isinstance(doc.get("models"), list):
            return doc
    except Exception:
        pass
    return {"models": [], "default_host": "http://127.0.0.1:11434"}


def default_host() -> str:
    return str(_load().get("default_host") or "http://127.0.0.1:11434")


def models(*, status: Optional[str] = None, capability: Optional[str] = None) -> List[Dict[str, Any]]:
    """The roster rows, optionally filtered by status and/or a single capability label. Best-first
    (status rank, then throughput desc). Read-only copies -- callers can't mutate the source."""
    rows = [dict(m) for m in _load().get("models", []) if isinstance(m, dict) and m.get("tag")]
    if status is not None:
        rows = [m for m in rows if m.get("status") == status]
    if capability is not None:
        rows = [m for m in rows if capability in (m.get("capabilities") or [])]
    rows.sort(key=lambda m: (_STATUS_RANK.get(m.get("status"), 9),
                             -(m.get("throughput_toks") or 0)))
    return rows


def get(tag: str) -> Optional[Dict[str, Any]]:
    """The spec for one tag, or None. Exact-match on the Ollama tag."""
    if not tag:
        return None
    for m in _load().get("models", []):
        if isinstance(m, dict) and m.get("tag") == tag:
            return dict(m)
    return None


def select(capability: Optional[str] = None, *, status: str = "active",
           max_vram: Optional[float] = None, min_context: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Pick the best model for a job by declared capability + hard constraints. Deterministic (ranks by
    throughput among those that fit), NOT learned -- a value-optimized router is future work gated on
    the R016 capability map + usage data (the F2 Goodhart caution). Fail-soft: None when nothing fits.

    select() never returns a gated model -- it answers "what should I RUN", and a gated model is
    disqualified (to SEE gated rows, use models(status='gated') or `fleet list`). The default
    status='active' means a pick is always safe to run now. max_vram excludes rows whose MEASURED
    footprint is known-too-big; unknown vram is not excluded, so an unmeasured candidate can still be
    surfaced for a first manual `fleet call`."""
    cands = models(status=status, capability=capability)
    out = []
    for m in cands:
        if m.get("status") == "gated":
            continue
        vram = m.get("vram_gb")
        if max_vram is not None and vram is not None and vram > max_vram:
            continue
        ctx = m.get("context")
        if min_context is not None and ctx is not None and ctx < min_context:
            continue
        out.append(m)
    return out[0] if out else None


def probe_availability(host: Optional[str] = None, *, opener: Any = None, timeout: float = 5.0) -> Dict[str, Any]:
    """OPT-IN live check: which roster tags are actually pulled into Ollama right now (`GET /api/tags`).
    The ONLY function here that touches the network. Fail-soft: on any error returns ok=False and an
    empty present set (the roster's declared specs remain usable). `opener` is injectable for tests."""
    host = host or default_host()
    present: set = set()
    try:
        import urllib.request
        opener = opener or urllib.request.urlopen
        req = urllib.request.Request(host.rstrip("/") + "/api/tags", method="GET")
        with opener(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for m in data.get("models", []):
            name = m.get("name") or m.get("model")
            if name:
                present.add(name)
                present.add(name.split(":")[0])   # bare family too, so 'qwen3-8b' matches 'qwen3-8b:latest'
    except Exception:
        return {"ok": False, "host": host, "present": []}
    declared = {m.get("tag") for m in _load().get("models", [])}
    return {"ok": True, "host": host, "present": sorted(present),
            "declared_present": sorted(t for t in declared if t in present or t.split(":")[0] in present)}
