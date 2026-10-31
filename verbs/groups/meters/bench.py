"""The recall meter: grade the LIVE trigger against an answer key.

Its own cluster because it MEASURES rather than reports, and because its subject is the seam
itself (recall_at) rather than the store.
"""
from __future__ import annotations

from verbs.registry import verb


@verb(local=False, door_notes="CLI only; core.recall.bench. The one verb here that deliberately measures the LIVE trigger (recall_at), not the store.")
def cmd_recall_bench(args) -> int:
    """W0.3: grade recall against an answer key, by driving the REAL trigger.

    The 2026-08-08 dossier's finding is why this drives path/command and never a query: querying
    the store directly returns the right lesson first almost every time, so keying the bench on a
    query would measure the half that already works. The failure is in WHEN, not WHAT.
    """
    import json as _json
    from core.recall import bench as _b
    from core.recall.at_action import recall_at
    try:
        meta = _b.load(getattr(args, "set", None) or None)
    except Exception as e:                                                # noqa: BLE001
        print(f"ERROR: could not load the moment set ({type(e).__name__}: {e})")
        return 1
    k = int(getattr(args, "limit", None) or 5)
    # The ceiling probe must be GATE-FREE, or it measures the gate it exists to bound: with the
    # live floor applied, a lesson the gate rejects would read as UNMATCHABLE (a matching defect)
    # when it is really gate-suppressed. floor 0 keeps the two diagnoses separable.
    import functools as _ft
    _probe = _ft.partial(recall_at, min_relevance=0.0)
    d = _b.score(meta.get("moments") or [], recall_at, k=k, probe_fn=_probe)
    if getattr(args, "json", False):
        print(_json.dumps({"meta": {kk: vv for kk, vv in meta.items() if kk != "moments"},
                           "result": d}, indent=2, default=str))
    else:
        print(_b.render(d, meta))
    return 0
