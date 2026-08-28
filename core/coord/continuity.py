"""Bounded, non-authoritative continuity evidence for exactly one seat.

This module answers a recovery question, not an identity question.  The ratified
resident registry is the only source allowed to state a designation.  Authored
lessons, subject-scoped scratch notes, handoffs, artifact headers, and telemetry
remain separate regions because they carry different authority and different
failure modes.

Every default source is read-only.  No cursor, presence key, watcher, session,
resident record, lesson, note, atom, or event is written by this view.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional


_ROOT = Path(__file__).resolve().parents[2]
_REGION_ORDER = ("designation", "lessons", "notes", "handoffs", "artifacts", "movement")
_DEFAULT_LIMITS = {
    "designation": 1,
    "lessons": 5,
    "notes": 4,
    "handoffs": 5,
    "artifacts": 5,
    "movement": 5,
}
_AUTHORITIES = {
    "designation": "ratified_resident_registry",
    "lessons": "exact_lesson_authorship",
    "notes": "subject_scoped_not_author_verified",
    "handoffs": "directional_attribution",
    "artifacts": "header_attribution_not_authorship",
    "movement": "telemetry_attribution_not_identity",
}
_DRILLS = {
    "designation": "py agent_cli.py resident show {subject}",
    "lessons": "py agent_cli.py recall \"identity continuity\" --agent {subject} --json",
    "notes": "use the bound ToolBox memory_recall door for {subject}",
    "handoffs": ("inbound: py agent_cli.py handoff {subject} --list --to {subject} --json; "
                 "outbound has no dedicated CLI reader, so use this grounded region"),
    "artifacts": ("no dedicated exact atom read door; use the atom:<id> source shown by "
                  "this region"),
    "movement": "py agent_cli.py events --agent {subject} --limit 25 --json",
}
_CURRENCY = {
    "designation": "current resident projection at read time; registry history is append-only",
    "lessons": "current exact-agent lesson index at read time",
    "notes": "active scratch-note heads from the last 3650 days at read time",
    "handoffs": "bounded canonical signal-ledger replay at read time",
    "artifacts": "current atom corpus scan at read time",
    "movement": "retained per-agent raw-event stream at read time",
}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _same_subject(left: Any, right: Any) -> bool:
    # Seat ids are addresses. Do not case-fold, alias-resolve, or otherwise
    # normalize them here: recovery must refuse an ambiguous spelling rather
    # than merge two subjects for convenience.
    return str(left or "").strip() == str(right or "").strip()


def _mapping(value: Any) -> Dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {"_unreadable": repr(value)}


def _clip(value: Any, limit: int = 360) -> str:
    text = str(value or "").replace("\x00", "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + f" ... [{len(text) - limit} chars omitted]"


def _source_batch(items: Iterable[Any], source: str, *, total: Optional[int] = None,
                  scanned: Optional[int] = None, truncated: bool = False,
                  ordering: str = "source order", blind: Optional[Iterable[str]] = None
                  ) -> Dict[str, Any]:
    rows = [_mapping(item) for item in items]
    return {
        "items": rows,
        "total": len(rows) if total is None else int(total),
        "scanned": len(rows) if scanned is None else int(scanned),
        "truncated": bool(truncated),
        "source": str(source),
        "ordering": str(ordering),
        "blind": [str(item) for item in (blind or [])],
    }


def _read_designation(subject: str) -> Dict[str, Any]:
    from core.fleet import residents

    history = residents.history(subject)
    current = residents.get(subject)
    # If there is a current projection, do not return superseded ratifications as
    # peers.  If there is only a nomination, return it so the builder can exclude
    # it loudly rather than making the ceremony-incomplete state invisible.
    rows = [current] if current is not None else history
    return _source_batch(
        rows,
        "core/fleet/residents.py:get + history (exact seat key)",
        total=len(history),
        scanned=len(history),
        ordering="current projection; append-only history inspected for incomplete ceremony",
    )


def _read_lessons(subject: str) -> Dict[str, Any]:
    from core.learning.learning_store import get_learning_store

    rows = get_learning_store().load_learnings_contributed_by_agent(subject)
    return _source_batch(
        rows,
        f"LearningStore learn:agent:{subject} exact index",
        ordering="agent lesson index order; rendered newest timestamp first",
    )


def _read_notes(_subject: str) -> Dict[str, Any]:
    from core.learning.agent_memory import get_agent_memory

    rows = get_agent_memory().get_decisions(days=3650)
    return _source_batch(
        rows,
        "AgentMemory active decision heads, 3650-day read window",
        ordering="created_at descending after exact scratch prefix filter",
        blind=["scratch title prefix scopes a note but the record has no author field"],
    )


def _read_handoffs(_subject: str) -> Dict[str, Any]:
    from core.signals.agent_signal_ledger import AgentSignalLedger

    cap = 10_000
    rows = []
    for cursor_id, signal in AgentSignalLedger().replay_signals(after_id="0", count=cap):
        item = dict(signal)
        item.setdefault("_cursor_id", str(cursor_id))
        rows.append(item)
    at_cap = len(rows) >= cap
    blind = ([f"canonical signal replay reached its {cap}-row cap; older handoffs may be outside view"]
             if at_cap else [])
    return _source_batch(
        rows,
        f"AgentSignalLedger canonical replay (cap {cap})",
        truncated=at_cap,
        ordering="ledger order; rendered newest timestamp/cursor first",
        blind=blind,
    )


def _read_artifacts(_subject: str) -> Dict[str, Any]:
    from core.foundation.store import create_store
    from core.library.atoms import AtomFamily

    rows = AtomFamily(create_store(), repo_root=str(_ROOT)).find()
    return _source_batch(
        rows,
        "AtomFamily.find full current corpus; exact header.seats membership",
        ordering="created_ts descending",
    )


def _read_movement(subject: str) -> Dict[str, Any]:
    from core.events.event_log import PER_AGENT_MAXLEN, get_event_log

    rows = get_event_log().scan(agent=subject)
    at_cap = len(rows) >= PER_AGENT_MAXLEN
    blind = ([f"per-agent event stream is at its {PER_AGENT_MAXLEN}-row retention cap; older movement may be gone"]
             if at_cap else [])
    return _source_batch(
        rows,
        f"EventLog per-agent stream events:{subject}:raw",
        truncated=at_cap,
        ordering="stream order; rendered newest event first",
        blind=blind,
    )


def _default_sources() -> Dict[str, Callable[[str], Mapping[str, Any]]]:
    return {
        "designation": _read_designation,
        "lessons": _read_lessons,
        "notes": _read_notes,
        "handoffs": _read_handoffs,
        "artifacts": _read_artifacts,
        "movement": _read_movement,
    }


def _read_source(name: str, provider: Callable[[str], Mapping[str, Any]],
                 subject: str) -> Dict[str, Any]:
    try:
        raw = dict(provider(subject) or {})
        rows = [_mapping(item) for item in (raw.get("items") or [])]
        return {
            "items": rows,
            "total": int(raw.get("total", len(rows))),
            "scanned": int(raw.get("scanned", len(rows))),
            "truncated": bool(raw.get("truncated", False)),
            "source": str(raw.get("source") or f"{name} provider"),
            "ordering": str(raw.get("ordering") or "source order"),
            "blind": [str(item) for item in (raw.get("blind") or [])],
            "error": "",
        }
    except Exception as exc:
        return {
            "items": [], "total": 0, "scanned": 0, "truncated": False,
            "source": f"{name} provider",
            "ordering": "unavailable",
            "blind": [f"source unavailable: {type(exc).__name__}: {exc}"],
            "error": f"{type(exc).__name__}: {exc}",
        }


def _sort(rows: Iterable[Dict[str, Any]], *fields: str) -> List[Dict[str, Any]]:
    def key(row: Mapping[str, Any]):
        return tuple(str(row.get(field) or "") for field in fields)
    return sorted(rows, key=key, reverse=True)


def _designation_rows(rows: Iterable[Dict[str, Any]], subject: str
                      ) -> tuple[List[Dict[str, Any]], List[str]]:
    own = [row for row in rows if _same_subject(row.get("agent_id"), subject)]
    ratified = [row for row in own if str(row.get("state") or "").lower() == "ratified"]
    blind: List[str] = []
    unratified = len(own) - len(ratified)
    if unratified:
        blind.append(f"{unratified} unratified resident record(s) excluded; nomination is not designation")
    if not ratified:
        return [], blind
    chosen = _sort(ratified, "at")[:1]
    if len(ratified) > 1:
        blind.append(f"{len(ratified) - 1} superseded ratification(s) omitted by current-projection rule")
    row = chosen[0]
    receipts = []
    for receipt in row.get("receipts") or []:
        ref = str(receipt)
        receipts.append(ref if ref.startswith("learn:experiment:") else f"learn:experiment:{ref}")
    item = {
        "agent_id": subject,
        "callsign": row.get("callsign"),
        "vendor": row.get("vendor") or None,
        "family": row.get("family") or None,
        "team": row.get("team") or None,
        "number": row.get("number"),
        "formerly": list(row.get("formerly") or []),
        "receipts": receipts,
        "nominated_by": row.get("by"),
        "ratified_by": row.get("ratified_by"),
        "ratified_at": row.get("at"),
        "source": f"resident:{subject}",
    }
    return [item], blind


def _lesson_rows(rows: Iterable[Dict[str, Any]], subject: str) -> List[Dict[str, Any]]:
    own = [row for row in rows if _same_subject(row.get("agent_id") or row.get("agent"), subject)]
    own = _sort(own, "timestamp", "id")
    out = []
    for row in own:
        ident = str(row.get("id") or row.get("experiment") or "")
        experiment = str(row.get("experiment") or ident)
        gist = (row.get("recommendation") or row.get("recommend") or row.get("result")
                or row.get("what_tried") or row.get("tried") or "")
        out.append({
            "id": ident or experiment,
            "experiment": experiment,
            "timestamp": row.get("timestamp") or row.get("updated_at") or "",
            "category": row.get("category") or "",
            "success": row.get("success") or "",
            "gist": _clip(gist),
            "source": f"learn:experiment:{experiment}",
        })
    return out


def _note_rows(rows: Iterable[Dict[str, Any]], subject: str) -> List[Dict[str, Any]]:
    prefix = f"scratch:{subject}:"
    own = [row for row in rows if str(row.get("title") or "").startswith(prefix)]
    own = _sort(own, "created_at", "id")
    out = []
    for row in own:
        body = str(row.get("decision") or "")
        out.append({
            "id": str(row.get("id") or ""),
            "title": str(row.get("title") or ""),
            "note": _clip(body),
            "note_chars": len(body),
            "clipped": len(body) > 360,
            "created_at": row.get("created_at") or "",
            "curated": row.get("curated"),
            "source": f"mem:decision:{row.get('id') or ''}",
        })
    return out


def _handoff_rows(rows: Iterable[Dict[str, Any]], subject: str) -> List[Dict[str, Any]]:
    matched = []
    for row in rows:
        if str(row.get("signal_type") or "").lower() != "handoff":
            continue
        frm, to = row.get("agent_id"), row.get("target_agent")
        inbound, outbound = _same_subject(to, subject), _same_subject(frm, subject)
        if not inbound and not outbound:
            continue
        direction = "self" if inbound and outbound else ("inbound" if inbound else "outbound")
        context = row.get("context") if isinstance(row.get("context"), Mapping) else {}
        ident = str(row.get("signal_id") or row.get("_cursor_id") or "")
        matched.append({
            "id": ident,
            "direction": direction,
            "from": frm,
            "to": to,
            "task": _clip(row.get("task"), 500),
            "note": _clip(context.get("note"), 360),
            "blockers": [_clip(item, 240) for item in (row.get("blockers") or [])[:5]],
            "timestamp": row.get("timestamp") or row.get("at") or "",
            "source": f"agent-signal:{ident}",
        })
    return _sort(matched, "timestamp", "id")


def _artifact_rows(rows: Iterable[Dict[str, Any]], subject: str) -> List[Dict[str, Any]]:
    matched = []
    for row in rows:
        header = row.get("header") if isinstance(row.get("header"), Mapping) else {}
        seats = list(header.get("seats") or [])
        if not any(_same_subject(seat, subject) for seat in seats):
            continue
        ident = str(row.get("id") or "")
        matched.append({
            "id": ident,
            "title": header.get("title") or ident,
            "type": header.get("type") or "",
            "date": header.get("date") or "",
            "status": header.get("status") or "",
            "arc": header.get("arc"),
            "gist": _clip(header.get("gist"), 300),
            "seats": seats,
            "origin": row.get("origin") or "",
            "source": f"atom:{ident}",
        })
    return _sort(matched, "date", "id")


def _movement_rows(rows: Iterable[Dict[str, Any]], subject: str) -> List[Dict[str, Any]]:
    matched = []
    for row in rows:
        if not _same_subject(row.get("agent_id"), subject):
            continue
        ident = str(row.get("id") or "")
        matched.append({
            "id": ident,
            "kind": row.get("kind") or "",
            "summary": _clip(row.get("summary"), 360),
            "at": row.get("at") or "",
            "refs": [str(ref) for ref in (row.get("refs") or [])[:5]],
            "source": row.get("_ref") or f"event:events:{subject}:raw:{ident}",
        })
    return _sort(matched, "at", "id")


def _claim(name: str, *, present: bool, incomplete: bool) -> str:
    if name == "designation":
        if present:
            return "ratified resident designation observed; this is the only region allowed to state a callsign"
        return ("no ratified resident designation observed in the authoritative read; "
                "this does not claim that the seat or its history does not exist")
    claims = {
        "lessons": "exact subject-authored lessons; these are self-receipts, not a designation",
        "notes": "subject-scoped scratch notes are continuity hints; their prefix does not prove authorship",
        "handoffs": "exact inbound/outbound handoffs; direction is preserved and inbound prose is not self-authorship",
        "artifacts": "exact header.seats attribution; participation metadata is not authorship or identity authority",
        "movement": "exact agent telemetry attribution; activity is not identity authority",
    }
    base = claims[name]
    if not present:
        base = f"no matching {name} observed within this source and its stated bounds; absence is not nonexistence"
    return base + ("; source view is incomplete" if incomplete else "")


def _region(name: str, batch: Mapping[str, Any], rows: List[Dict[str, Any]], *,
            limit: int, observed_at: str, extra_blind: Optional[Iterable[str]] = None
            ) -> Dict[str, Any]:
    shown = rows[:max(0, limit)]
    source_incomplete = bool(batch.get("truncated"))
    display_incomplete = len(rows) > len(shown)
    blind = list(batch.get("blind") or []) + [str(item) for item in (extra_blind or [])]
    if display_incomplete:
        blind.append(f"{len(rows) - len(shown)} matching item(s) omitted by the {limit}-item render bound")
    if batch.get("error"):
        state = "unknown"
    elif rows:
        state = "partial" if source_incomplete else "observed"
    elif source_incomplete:
        state = "unknown"
    else:
        state = "absent"
    return {
        "name": name,
        "state": state,
        "authority": _AUTHORITIES[name],
        "claim": _claim(name, present=bool(rows), incomplete=source_incomplete),
        "source": str(batch.get("source") or f"{name} provider"),
        "currency": {"observed_at": observed_at, "basis": _CURRENCY[name]},
        "bounds": {
            "source_total": int(batch.get("total", 0)),
            "scanned": int(batch.get("scanned", 0)),
            "matched": len(rows),
            "shown": len(shown),
            "limit": max(0, limit),
            "truncated": bool(source_incomplete or display_incomplete),
            "ordering": str(batch.get("ordering") or "source order"),
        },
        "items": shown,
        "blind": blind,
        "drill": "",
    }


def _drill(name: str, subject: str, shown: List[Mapping[str, Any]]) -> str:
    """One bounded escape hatch; never expand a whole archive when an exact ref exists."""
    if name == "lessons" and shown:
        return f"py agent_cli.py recall --full {shown[0].get('source')} --json"
    if name == "movement" and shown:
        return f"py agent_cli.py events --get {shown[0].get('source')} --json"
    return _DRILLS[name].format(subject=subject)


def build_profile(subject: str, *,
                  sources: Optional[Mapping[str, Callable[[str], Mapping[str, Any]]]] = None,
                  limits: Optional[Mapping[str, int]] = None,
                  observed_at: Optional[str] = None) -> Dict[str, Any]:
    """Assemble one seat's bounded continuity profile without deciding who it is."""
    subject = str(subject or "").strip()
    if not subject:
        raise ValueError("continuity subject is required")
    when = observed_at or _utc()
    providers = _default_sources()
    if sources:
        providers.update(dict(sources))
    caps = dict(_DEFAULT_LIMITS)
    if limits:
        for name, value in limits.items():
            if name in caps:
                caps[name] = max(0, int(value))

    batches = {name: _read_source(name, providers[name], subject) for name in _REGION_ORDER}
    designation, designation_blind = _designation_rows(batches["designation"]["items"], subject)
    rows = {
        "designation": designation,
        "lessons": _lesson_rows(batches["lessons"]["items"], subject),
        "notes": _note_rows(batches["notes"]["items"], subject),
        "handoffs": _handoff_rows(batches["handoffs"]["items"], subject),
        "artifacts": _artifact_rows(batches["artifacts"]["items"], subject),
        "movement": _movement_rows(batches["movement"]["items"], subject),
    }
    regions = []
    for name in _REGION_ORDER:
        extra = designation_blind if name == "designation" else []
        region = _region(name, batches[name], rows[name], limit=caps[name],
                         observed_at=when, extra_blind=extra)
        region["drill"] = _drill(name, subject, region["items"])
        regions.append(region)

    top_blind: List[str] = []
    failed = 0
    for region in regions:
        if region["state"] == "unknown" and batches[region["name"]].get("error"):
            failed += 1
        for item in region["blind"]:
            top_blind.append(f"{region['name']}: {item}")
    if not designation:
        top_blind.append("designation: absent ratified registry projection; do not infer a name from any other region")

    return {
        "schema": "ground.result.v1",
        "mode": "continuity",
        "target": {"kind": "seat", "name": subject},
        "subject": subject,
        "observed_at": when,
        "identity_verdict": {
            "state": "not_computed",
            "claim": ("continuity evidence is not an identity verdict; only the ratified resident registry "
                      "may supply a designation, and no region can nominate or ratify one"),
        },
        "regions": regions,
        "bounds": {
            "regions_total": len(_REGION_ORDER),
            "sources_failed": failed,
            "ordering": list(_REGION_ORDER),
            "limits": caps,
        },
        "blind": top_blind,
        "effects": [],
    }


def _item_line(name: str, item: Mapping[str, Any]) -> str:
    if name == "designation":
        parts = [str(p) for p in (item.get("vendor"), item.get("family"), item.get("team")) if p]
        tail = str(item.get("callsign") or "")
        if item.get("number") is not None:
            tail = f"{item.get('number')} - {tail}"
        parts.append(tail)
        return " | ".join(parts) + f"  [{item.get('source')}]"
    if name == "lessons":
        return f"{item.get('experiment')}: {item.get('gist')}  [{item.get('source')}]"
    if name == "notes":
        return f"{item.get('title')}: {item.get('note')}  [{item.get('source')}]"
    if name == "handoffs":
        return f"{item.get('direction')} {item.get('from')} -> {item.get('to')}: {item.get('task')}  [{item.get('source')}]"
    if name == "artifacts":
        return f"{item.get('date')} {item.get('title')}: {item.get('gist')}  [{item.get('source')}]"
    return f"{item.get('at')} {item.get('kind')}: {item.get('summary')}  [{item.get('source')}]"


def render_profile(result: Mapping[str, Any]) -> str:
    """Compact human view; JSON retains every bound and blind spot."""
    target = result.get("target") or {}
    lines = [f"# ground seat:{target.get('name')} --continuity",
             f"  observed {result.get('observed_at')} | effects: none",
             f"  IDENTITY VERDICT: NOT COMPUTED -- {(result.get('identity_verdict') or {}).get('claim')}"]
    for region in result.get("regions") or []:
        bounds = region.get("bounds") or {}
        lines.append(
            f"\n## {str(region.get('name')).upper()}  {str(region.get('state')).upper()} "
            f"[{region.get('authority')}]  shown {bounds.get('shown')}/{bounds.get('matched')}"
        )
        lines.append(f"  {region.get('claim')}")
        lines.append(f"  source: {region.get('source')}")
        for item in region.get("items") or []:
            lines.append(f"  - {_item_line(str(region.get('name')), item)}")
        for blind in region.get("blind") or []:
            lines.append(f"  BLIND: {blind}")
        lines.append(f"  drill: {region.get('drill')}")
    return "\n".join(lines)


__all__ = ["build_profile", "render_profile"]
