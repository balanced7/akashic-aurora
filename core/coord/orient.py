"""Renderer-neutral orientation scene over Aurora's native read verbs.

``orient`` is the first small build from the 2026-07-28 VR/GPS design that can
ship without a spatial renderer.  It treats ``sweep`` as peripheral vision and
``ground`` / continuity / ``capture`` as typed focus operations, then returns a
single scene model that CLI, MCP, ToolBox, Discord, or a future visual world can
render without deriving a second version of state.

The module is deliberately strict:

* the subject is explicit and a seat focus may only name that same subject;
* destinations are typed (``verb:``, ``seat:``, or ``thread:``), never guessed;
* every provider must report zero effects or the composition refuses;
* reducing density moves landmarks to a named periphery instead of dropping them;
* reducing depth leaves a drillable contour and never removes the epistemic floor.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Mapping, Optional

from core.primitives.epistemic import derive_epistemic_view


SCHEMA = "orient.scene.v1"
_DENSITY_NEARBY = {"compact": 1, "standard": 3, "wide": 4}
_DEPTHS = {"surface", "evidence"}
_TARGET_TYPES = {"verb", "seat", "thread"}


def _default_providers() -> Dict[str, Callable[..., Any]]:
    from core.comm.awareness import build_snapshot
    from core.comm.thread_capture import collect_thread
    from core.coord.ground import ground

    return {"snapshot": build_snapshot, "ground": ground, "capture": collect_thread}


def _parse_target(subject: str, target: str) -> Optional[Dict[str, str]]:
    raw = str(target or "").strip()
    if not raw:
        return None
    if ":" not in raw:
        raise ValueError(
            "orient destination must be typed: verb:<name>, seat:<your-id>, or thread:<ref>"
        )
    kind, name = raw.split(":", 1)
    kind = kind.strip().lower().replace("-", "_")
    name = name.strip()
    if kind not in _TARGET_TYPES:
        raise ValueError(
            f"unsupported orient destination kind {kind!r}; use verb, seat, or thread"
        )
    if not name:
        raise ValueError("orient destination name is required")
    if kind == "seat" and name != subject:
        raise ValueError(
            f"seat orientation cannot borrow a foreign identity; bound subject is {subject!r}"
        )
    normalized = name.lower().replace("-", "_") if kind == "verb" else name
    return {
        "kind": kind,
        "name": normalized,
        "address": f"{kind}:{normalized}",
        "interpretation": "typed",
    }


def _assert_pure(payload: Mapping[str, Any], label: str) -> None:
    effects = list(payload.get("effects") or [])
    if effects:
        raise RuntimeError(
            f"orient refuses an effectful {label} provider: {effects!r}; orientation is read-only"
        )


def _epistemic(sources: Any, *, effects: Any = ()) -> Dict[str, Any]:
    refs = [str(item) for item in (sources or []) if str(item or "").strip()]
    if not refs:
        refs = ["orient.scene:provider-result"]
    risk = "ordinary" if not list(effects or []) else "attention_required"
    evidence = {
        "authority": {"value": "mechanical_source", "basis": refs},
        "claim_kind": {"value": "observed", "basis": refs},
        # Wall-clock observation time is not lifecycle currency and aggregate
        # focus has no single delivery identity.  UNKNOWN is the truthful floor.
        "currency": {"value": "unknown", "basis": []},
        "identity_state": {"value": "unknown", "basis": []},
        "risk": {"value": risk, "basis": [f"{refs[0]}:effects"]},
    }
    return derive_epistemic_view(evidence).to_dict()


def _landmark(row: Mapping[str, Any]) -> Dict[str, Any]:
    sources = list(row.get("source") or [])
    effects = list(row.get("effects") or [])
    return {
        "name": str(row.get("name") or "unknown"),
        "status": str(row.get("status") or "UNKNOWN"),
        "summary": str(row.get("summary") or ""),
        "source": sources,
        "observed_at": row.get("observed_at"),
        "epistemic": _epistemic(sources, effects=effects),
        "epistemic_scope": "observation envelope, not nested claims",
        "effects": effects,
        "details": dict(row.get("details") or {}),
        "drill": str(row.get("drill") or ""),
    }


def _contour(card: Mapping[str, Any]) -> Dict[str, Any]:
    folded_fields = len(card.get("details") or {}) + len(card.get("source") or [])
    return {
        "name": card.get("name"),
        "status": card.get("status"),
        "summary": card.get("summary"),
        "epistemic": card.get("epistemic"),
        "epistemic_scope": card.get("epistemic_scope"),
        "effects": list(card.get("effects") or []),
        "drill": card.get("drill"),
        "folded": {"present": bool(folded_fields), "fields": folded_fields},
    }


def _focus_sources(result: Mapping[str, Any]) -> list[str]:
    sources = []
    for rung in result.get("rungs") or []:
        source = str((rung or {}).get("source") or "").strip()
        if source and source not in sources:
            sources.append(source)
    if not sources:
        schema = str(result.get("schema") or "focus-result")
        sources.append(f"orient.scene:{schema}")
    return sources


def _focus_drill(target: Mapping[str, str], result: Mapping[str, Any], subject: str,
                 per_stream: int) -> str:
    for rung in result.get("rungs") or []:
        drill = str((rung or {}).get("drill") or "").strip()
        if drill:
            return drill
    if target["kind"] == "thread":
        return (f"py agent_cli.py capture --thread {target['name']} --agent {subject} "
                f"--per-stream {per_stream} --json")
    continuity = " --continuity" if target["kind"] == "seat" else ""
    return (f"py agent_cli.py ground {target['address']} --agent {subject}"
            f"{continuity} --json")


def _focus_summary(target: Mapping[str, str], result: Mapping[str, Any]) -> str:
    if target["kind"] == "thread":
        count = len(result.get("messages") or [])
        found = "found" if result.get("found") else "not found"
        truncated = bool((result.get("bounds") or {}).get("truncated"))
        return f"thread {found}; messages={count}; truncated={'yes' if truncated else 'no'}"
    rungs = result.get("rungs") or []
    if rungs:
        return "; ".join(
            f"{row.get('name')}={row.get('state')}" for row in rungs[:4]
        )
    regions = result.get("regions") or []
    if regions:
        return f"continuity regions={len(regions)}"
    return str(result.get("schema") or result.get("mode") or "focus observed")


def _focus_route(target: Mapping[str, str], subject: str, per_stream: int) -> Dict[str, Any]:
    if target["kind"] == "thread":
        step = {
            "verb": "capture",
            "args": {"thread": target["name"], "as_doc": False,
                     "per_stream": per_stream},
        }
    else:
        step = {
            "verb": "ground",
            "args": {"target": target["address"], "agent": subject,
                     "continuity": target["kind"] == "seat"},
        }
    return {
        "name": "focus",
        "style": "direct",
        "steps": [step],
        "cost": {"verb_calls": 1, "writes": 0, "latency": "unmeasured"},
        "effects": [],
        "risk": "ordinary",
        "commit_required": False,
    }


def _return_route(subject: str) -> Dict[str, Any]:
    return {
        "name": "return",
        "style": "return_tether",
        "steps": [{"verb": "sweep", "args": {"agent": subject}}],
        "cost": {"verb_calls": 1, "writes": 0, "latency": "unmeasured"},
        "effects": [],
        "risk": "ordinary",
        "commit_required": False,
    }


def build_orientation(
    subject: str,
    target: str = "",
    *,
    density: str = "compact",
    depth: str = "surface",
    per_stream: int = 1000,
    providers: Optional[Mapping[str, Callable[..., Any]]] = None,
) -> Dict[str, Any]:
    """Build one pure ``orient.scene.v1`` view for an explicit subject."""
    subject = str(subject or "").strip()
    if not subject:
        raise ValueError("orient subject is required")
    density = str(density or "").strip().lower()
    depth = str(depth or "").strip().lower()
    if density not in _DENSITY_NEARBY:
        raise ValueError(f"unknown density {density!r}; choose {sorted(_DENSITY_NEARBY)}")
    if depth not in _DEPTHS:
        raise ValueError(f"unknown depth {depth!r}; choose {sorted(_DEPTHS)}")
    try:
        per_stream = max(1, min(int(per_stream), 5000))
    except (TypeError, ValueError):
        raise ValueError("per_stream must be an integer in 1..5000")

    target_row = _parse_target(subject, target)
    seams = _default_providers()
    seams.update(dict(providers or {}))

    snapshot = seams["snapshot"](subject)
    snapshot_payload = (snapshot.as_dict() if hasattr(snapshot, "as_dict")
                        else dict(snapshot or {}))
    if str(snapshot_payload.get("subject") or "") != subject:
        raise ValueError("snapshot provider returned a foreign subject")
    _assert_pure(snapshot_payload, "snapshot")

    landmarks = [_landmark(row) for row in (snapshot_payload.get("observations") or [])]
    for row in landmarks:
        _assert_pure(row, f"landmark:{row['name']}")
    nearby_count = min(_DENSITY_NEARBY[density], len(landmarks))
    nearby_full = landmarks[:nearby_count]
    nearby = (nearby_full if depth == "evidence"
              else [_contour(row) for row in nearby_full])
    periphery = [_contour(row) for row in landmarks[nearby_count:]]
    # The observations live exactly once, in nearby/periphery.  Position is the
    # stable scene stamp; embedding the full snapshot here would duplicate every
    # landmark and make the supposedly compact surface cost more than its inputs.
    position = {
        "schema_version": snapshot_payload.get("schema_version"),
        "kind": snapshot_payload.get("kind"),
        "subject": subject,
        "observed_at": snapshot_payload.get("observed_at"),
        "effects": list(snapshot_payload.get("effects") or []),
        "landmarks_total": len(landmarks),
    }

    focus = None
    routes = []
    aggregate_blind = []
    if target_row is not None:
        if target_row["kind"] == "thread":
            result = seams["capture"](
                subject, target_row["name"], per_stream=per_stream
            )
        else:
            result = seams["ground"](
                target_row["address"], subject=subject,
                continuity=target_row["kind"] == "seat",
            )
        result = dict(result or {})
        if str(result.get("subject") or "") != subject:
            raise ValueError("focus provider returned a foreign subject")
        _assert_pure(result, "focus")
        sources = _focus_sources(result)
        drill = _focus_drill(target_row, result, subject, per_stream)
        aggregate_blind.extend(str(item) for item in (result.get("blind") or []))
        focus = {
            "target": dict(target_row),
            "summary": _focus_summary(target_row, result),
            "epistemic": _epistemic(sources, effects=result.get("effects") or []),
            "epistemic_scope": "observation envelope, not nested claims",
            "blind": list(result.get("blind") or []),
            "drill": drill,
        }
        if depth == "evidence":
            focus["folded"] = {"present": False, "fields": 0, "drill": drill}
            focus["evidence"] = result
        else:
            focus["folded"] = {
                "present": True,
                "fields": len(result),
                "drill": drill,
            }
        routes.append(_focus_route(target_row, subject, per_stream))

    # A read-only orientation never moves the seat.  RETURN therefore means one
    # deterministic step back to ambient awareness rather than mutating Eye position.
    routes.append(_return_route(subject))
    return {
        "schema": SCHEMA,
        "subject": subject,
        "observed_at": position.get("observed_at"),
        "target": target_row,
        "aperture": {
            "density": density,
            "depth": depth,
            "truth_floor": "always",
            "out_of_focus": "contoured, never dropped",
        },
        "position": position,
        "focus": focus,
        "nearby": nearby,
        "periphery": periphery,
        "routes": routes,
        "bounds": {
            "landmarks_total": len(landmarks),
            "landmarks_shown_nearby": len(nearby),
            "landmarks_contoured": len(periphery),
            "focus_fields_folded": (focus or {}).get("folded", {}).get("fields", 0),
            "per_stream": per_stream,
        },
        "blind": aggregate_blind,
        "effects": [],
    }


def render_orientation(scene: Mapping[str, Any]) -> str:
    """Compact CLI projection of the renderer-neutral scene."""
    subject = scene.get("subject")
    target = (scene.get("target") or {}).get("address") or "ambient"
    aperture = scene.get("aperture") or {}
    effects = list(scene.get("effects") or [])
    lines = [
        f"# orient subject={subject} target={target} density={aperture.get('density')} "
        f"depth={aperture.get('depth')} effects={'none' if not effects else effects}"
    ]
    focus = scene.get("focus")
    if focus:
        lines.append(f"  focus {target} | {focus.get('summary')}")
        epi = focus.get("epistemic") or {}
        vals = " ".join(
            f"{axis}={(epi.get(axis) or {}).get('value', 'unknown')}"
            for axis in ("authority", "claim_kind", "currency", "identity_state", "risk")
        )
        lines.append(f"  truth {vals}")
        folded = focus.get("folded") or {}
        if folded.get("present"):
            lines.append(f"  folded {folded.get('fields', 0)} field(s) | drill: {folded.get('drill')}")
    else:
        lines.append("  focus ambient awareness (no destination supplied)")
    nearby = list(scene.get("nearby") or [])
    lines.append("  nearby " + (", ".join(str(row.get("name")) for row in nearby) or "none"))
    periphery = list(scene.get("periphery") or [])
    lines.append(
        f"  periphery {len(periphery)} contour(s): "
        + (", ".join(str(row.get("name")) for row in periphery) or "none")
    )
    return_step = next((r for r in scene.get("routes") or [] if r.get("name") == "return"), None)
    lines.append(f"  return {((return_step or {}).get('steps') or [{}])[0]}")
    lines.append(f"  blind={len(scene.get('blind') or [])} | truth floor={aperture.get('truth_floor')}")
    return "\n".join(lines)


__all__ = ["SCHEMA", "build_orientation", "render_orientation"]
