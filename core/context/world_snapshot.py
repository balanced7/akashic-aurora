"""Read-only WorldSnapshot and SUBJECT / ATTENTION projection.

This module opens the first implementation slice of the settled fleet design
``art_20260729_world-snapshot-glance-projection-fleet-d_218aef`` after Daniil's
explicit 2026-09-02 build gate.  It is a high-level CQRS read model:

* named authorities remain authoritative; this module stores and settles none;
* every source declares its plane, authority, revision, and observation time;
* unsupported questions are loud ``UNCHECKABLE`` capabilities, never empties;
* snapshot identity is derived from source-state identities, never a counter;
* the compact operational brief explicitly carries no identity authority.

It is intentionally unrelated to ``scripts/snapshot.py`` (knowledge/WAL
snapshotting) and the ``core.world*`` family (runtime world resolution).
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from core.primitives.epistemic import derive_epistemic_view


SCHEMA_VERSION = "world-snapshot/v1"
PROJECTION_VERSION = "subject-attention/v1"
BRIEF_SCHEMA_VERSION = "operational-brief/v1"
ATTENTION_STATES = ("ATTENTION", "ACTING", "WAITING", "QUIET")
_ATTENTION_RANK = {state: index for index, state in enumerate(ATTENTION_STATES)}
_WAITING_STATUS_RANK = {"verifying": 0, "claimed": 1, "approved": 2}
_TASK_ATTENTION_POLICY = "policy:task-status-attention/v1"
_TASK_STATUS_VOCABULARY = frozenset(
    {
        "proposed",
        "approved",
        "claimed",
        "in_progress",
        "verifying",
        "done",
        "blocked",
        "abandoned",
        "parked",
    }
)


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _json_clone(value: Any) -> Any:
    """Detach caller-owned values and guarantee a JSON-shaped contract."""
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _hash_id(prefix: str, value: Any) -> str:
    return prefix + hashlib.sha256(_canonical_bytes(value)).hexdigest()[:24]


def _without_observation_clocks(value: Any) -> Any:
    """Remove observation clocks recursively for stable content identities."""
    if isinstance(value, Mapping):
        return {
            key: _without_observation_clocks(item)
            for key, item in value.items()
            if key not in {"generated_at", "checked_at", "valid_until"}
        }
    if isinstance(value, list):
        return [_without_observation_clocks(item) for item in value]
    return value


def _bounded_text(value: Any, limit: int = 240) -> tuple[str, int, bool]:
    text = _text(value)
    full_chars = len(text)
    if full_chars <= limit:
        return text, full_chars, False
    if limit <= 1:
        return "…"[:limit], full_chars, True
    return text[: limit - 1].rstrip() + "…", full_chars, True


def _bounded_text_list(
    values: Any, *, item_limit: int = 8, text_limit: int = 160
) -> tuple[List[str], int, bool]:
    if isinstance(values, (str, bytes)) or values is None:
        raw: List[Any] = [] if values is None else [values]
    else:
        try:
            raw = list(values)
        except TypeError:
            raw = []
    bounded = [_bounded_text(value, text_limit)[0] for value in raw[:item_limit]]
    was_truncated = len(raw) > item_limit or any(len(_text(value)) > text_limit for value in raw)
    return bounded, len(raw), was_truncated


def _normalize_source(raw: Mapping[str, Any], fallback_checked_at: str) -> Dict[str, Any]:
    source = _json_clone(raw)
    required = ("name", "plane", "authority", "revision")
    missing = [field for field in required if not _text(source.get(field))]
    if missing:
        raise ValueError(f"source missing required field(s): {', '.join(missing)}")
    normalized = {
        "name": _text(source["name"]),
        "plane": _text(source["plane"]),
        "authority": _text(source["authority"]),
        "revision": _text(source["revision"]),
        "checked_at": _text(source.get("checked_at")) or fallback_checked_at,
    }
    if _text(source.get("cursor")):
        normalized["cursor"] = _text(source["cursor"])
    if _text(source.get("drill")):
        normalized["drill"] = _text(source["drill"])
    return normalized


def _normalize_capability(name: str, raw: Any) -> Dict[str, Any]:
    capability = _json_clone(raw) if isinstance(raw, Mapping) else {}
    state = _text(capability.get("state")).upper()
    if state == "SUPPORTED":
        basis = sorted({_text(ref) for ref in capability.get("basis", []) if _text(ref)})
        if basis:
            return {"state": "SUPPORTED", "basis": basis}
        return {
            "state": "UNCHECKABLE",
            "blocked_by": "invalid-capability-declaration",
            "reason": f"{name} was declared SUPPORTED without a basis receipt",
        }
    if state == "UNCHECKABLE":
        return {
            "state": "UNCHECKABLE",
            "blocked_by": _text(capability.get("blocked_by")) or "unknown-blocker",
            "reason": _text(capability.get("reason")) or "no reason recorded",
        }
    return {
        "state": "UNCHECKABLE",
        "blocked_by": "invalid-capability-declaration",
        "reason": f"{name} did not declare SUPPORTED or UNCHECKABLE",
    }


def _normalize_item(raw: Mapping[str, Any], known_sources: set[str]) -> Dict[str, Any]:
    item = _json_clone(raw)
    organ = _text(item.get("organ"))
    if not organ:
        raise ValueError("snapshot item missing organ")
    attention = _text(item.get("attention")).upper()
    if attention not in _ATTENTION_RANK:
        raise ValueError(f"invalid attention state: {attention or '<empty>'}")
    source_refs = sorted({_text(ref) for ref in item.get("source_refs", []) if _text(ref)})
    unknown = [ref for ref in source_refs if ref not in known_sources]
    if unknown:
        raise ValueError(f"unknown source ref(s): {', '.join(unknown)}")
    if not source_refs:
        raise ValueError("snapshot item has no source refs")
    object_ref = item.get("object_ref")
    if object_ref is not None:
        object_ref = _text(object_ref) or None
    return {
        "object_ref": object_ref,
        "organ": organ,
        "attention": attention,
        "source_refs": source_refs,
        "data": _json_clone(item.get("data") if isinstance(item.get("data"), Mapping) else {}),
        "epistemic_view": derive_epistemic_view(
            item.get("epistemic_view") if isinstance(item.get("epistemic_view"), Mapping) else {}
        ).to_dict(),
    }


def _item_sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    data = item.get("data") if isinstance(item.get("data"), Mapping) else {}
    status = _text(data.get("status")).lower()
    return (
        _ATTENTION_RANK.get(_text(item.get("attention")).upper(), len(_ATTENTION_RANK)),
        _WAITING_STATUS_RANK.get(status, len(_WAITING_STATUS_RANK)),
        _text(item.get("organ")),
        _text(item.get("object_ref")),
    )


def _operator_sentence(
    subject: str,
    projection_label: str,
    counts: Mapping[str, int],
    total: int,
    shown: int,
    uncheckable: int,
) -> str:
    return (
        f"{subject} {projection_label}: {counts['ATTENTION']} need attention, "
        f"{counts['ACTING']} acting, "
        f"{counts['WAITING']} waiting, {counts['QUIET']} quiet; "
        f"{total} total, {shown} shown; {uncheckable} capabilities uncheckable."
    )


def assemble_world_snapshot(
    *,
    subject: str,
    sources: Sequence[Mapping[str, Any]],
    items: Sequence[Mapping[str, Any]],
    capabilities: Mapping[str, Any],
    generated_at: Optional[str] = None,
    max_items: int = 64,
    projection_label: str = "source projection",
) -> Dict[str, Any]:
    """Assemble one deterministic, bounded read model from named observations.

    The caller owns all reads.  This function performs no I/O and mutates none
    of its inputs.  ``snapshot_id`` identifies named source states, independent
    of observation clocks and rendering bounds; ``projection_id`` identifies
    the versioned projection contract over that state; ``render_id`` identifies
    these exact bounded bytes (apart from observation clocks).
    """
    subject_text = _text(subject)
    if not subject_text:
        raise ValueError("subject is required")
    if isinstance(max_items, bool) or int(max_items) < 0:
        raise ValueError("max_items must be a non-negative integer")
    max_items = int(max_items)
    observed_at = _text(generated_at) or _utc_now()

    normalized_sources = sorted(
        (_normalize_source(source, observed_at) for source in list(sources)),
        key=lambda source: source["name"],
    )
    source_names = [source["name"] for source in normalized_sources]
    if len(source_names) != len(set(source_names)):
        raise ValueError("duplicate source name")
    known_sources = set(source_names)

    normalized_capabilities = {
        name: _normalize_capability(name, capabilities[name])
        for name in sorted(capabilities)
    }
    normalized_items = sorted(
        (_normalize_item(item, known_sources) for item in list(items)),
        key=_item_sort_key,
    )
    total = len(normalized_items)
    bounded_items = normalized_items[:max_items]
    counts = {
        state: sum(1 for item in normalized_items if item["attention"] == state)
        for state in ATTENTION_STATES
    }
    unknown_capabilities = [
        name
        for name, capability in normalized_capabilities.items()
        if capability["state"] == "UNCHECKABLE"
    ]

    source_state = {
        "schema_version": SCHEMA_VERSION,
        "subject": subject_text,
        "sources": [
            {
                key: source[key]
                for key in ("name", "plane", "authority", "revision", "cursor")
                if key in source
            }
            for source in normalized_sources
        ],
    }
    snapshot: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "projection_version": PROJECTION_VERSION,
        "snapshot_id": _hash_id("ws_", source_state),
        "subject": subject_text,
        "generated_at": observed_at,
        "sources": normalized_sources,
        "capabilities": normalized_capabilities,
        "summary": {
            "operator_sentence": _operator_sentence(
                subject_text,
                _text(projection_label) or "source projection",
                counts,
                total,
                len(bounded_items),
                len(unknown_capabilities),
            ),
            "changed": [
                item["object_ref"]
                for item in normalized_items
                if item["organ"] == "change" and item["object_ref"] is not None
            ][:8],
            "needs_attention": [
                item["object_ref"]
                for item in normalized_items
                if item["attention"] == "ATTENTION" and item["object_ref"] is not None
            ][:8],
            "unknowns": unknown_capabilities[:16],
        },
        "bounds": {
            "item_limit": max_items,
            "total_items": total,
            "returned_items": len(bounded_items),
            "truncated": len(bounded_items) < total,
        },
        "items": bounded_items,
    }
    snapshot["projection_id"] = _hash_id(
        "gp_",
        {
            "snapshot_id": snapshot["snapshot_id"],
            "projection_version": PROJECTION_VERSION,
            "subject": subject_text,
        },
    )
    # A render identity is allowed to change with width/content.  Keeping it
    # separate prevents consumers from mistaking a narrow view for a new world
    # or a different projection contract.
    render_identity = _without_observation_clocks(copy.deepcopy(snapshot))
    snapshot["render_id"] = _hash_id("wr_", render_identity)
    return snapshot


def _task_attention(status: str) -> str:
    return {
        "blocked": "ATTENTION",
        "in_progress": "ACTING",
        "claimed": "WAITING",
        "approved": "WAITING",
        "verifying": "WAITING",
        "proposed": "QUIET",
        "done": "QUIET",
        "abandoned": "QUIET",
        "parked": "QUIET",
    }.get(status, "ATTENTION")


def _task_epistemic_view(source_basis: str, status: str, checked_at: str) -> Dict[str, Any]:
    if status == "blocked":
        risk = {"value": "blocked", "basis": ["field:task.status=blocked"]}
    elif status not in _TASK_STATUS_VOCABULARY:
        risk = {
            "value": "attention_required",
            "basis": ["policy:task-status-vocabulary/v1"],
        }
    else:
        risk = {"value": "unknown", "basis": []}
    return {
        "authority": {"value": "governed_source", "basis": [source_basis]},
        "claim_kind": {
            "value": "inferred",
            "basis": ["field:task.status", _TASK_ATTENTION_POLICY],
        },
        "currency": {
            "value": "current",
            "basis": [source_basis],
            "checked_at": checked_at,
        },
        "identity_state": {"value": "unknown", "basis": []},
        "risk": risk,
    }


def _uncheckable(blocked_by: str, reason: str) -> Dict[str, str]:
    return {"state": "UNCHECKABLE", "blocked_by": blocked_by, "reason": reason}


def _read_task_ledger_file(path: str, client: Any = None) -> Mapping[str, Any]:
    """Read exactly the named file authority; ``client`` exists for injected parity."""
    del client
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _program_capabilities(
    ledger_supported: bool, ledger_basis: str = "", ledger_error: str = ""
) -> Dict[str, Any]:
    if ledger_supported:
        task_state = {"state": "SUPPORTED", "basis": [ledger_basis]}
        attention = {
            "state": "SUPPORTED",
            "basis": [ledger_basis, "policy:task-status-attention/v1"],
        }
    else:
        task_state = _uncheckable(
            "task-ledger-git",
            ledger_error or "the durable task ledger could not be read",
        )
        attention = _uncheckable("task_state", "attention requires readable task state")
    return {
        "task_state": task_state,
        "subject_attention": attention,
        "arc_membership": _uncheckable(
            "estate-arc-register",
            "no authoritative machine-readable arc register is wired yet",
        ),
        "operator_queue": _uncheckable(
            "A15-operator-contract",
            "operator ownership and queue semantics are not yet settled substrate",
        ),
        "artifact_authority": _uncheckable(
            "adapter-not-wired", "the atom/projection authority adapter is not in slice one"
        ),
        "mail_state": _uncheckable(
            "adapter-not-wired", "the Bifrost plane adapter is not in slice one"
        ),
        "runtime_attention": _uncheckable(
            "adapter-not-wired",
            "ledger workflow state does not prove a seat is live, aware, or acting",
        ),
        "test_receipts": _uncheckable(
            "adapter-not-wired", "the verification receipt adapter is not in slice one"
        ),
        "git_changes": _uncheckable(
            "adapter-not-wired", "the Git change adapter is not in slice one"
        ),
        "deduplication": _uncheckable(
            "T116", "logical message identity is not yet authoritative"
        ),
        "lineage": _uncheckable(
            "T116", "complete original-to-redrive lineage is not yet authoritative"
        ),
        "settlement": _uncheckable(
            "T116", "settlement cannot be inferred where outcome pointers are absent"
        ),
    }


def build_program_world_snapshot(
    *,
    subject: str = "akashic-aurora-program",
    ledger_path: Optional[str] = None,
    ledger_reader: Optional[Callable[..., Mapping[str, Any]]] = None,
    checked_at: Optional[str] = None,
    generated_at: Optional[str] = None,
    max_items: int = 64,
) -> Dict[str, Any]:
    """Read the git-durable task ledger and build the first live projection.

    Redis is explicitly disabled for this authority read.  Unwired organs are
    represented as capabilities with blockers rather than silently omitted.
    """
    from core.coord import task_ledger

    one_clock = _text(generated_at) or _text(checked_at) or _utc_now()
    source_checked_at = _text(checked_at) or one_clock
    path = ledger_path or task_ledger.LEDGER_PATH
    reader = ledger_reader or _read_task_ledger_file
    sources: List[Dict[str, Any]] = []
    items: List[Dict[str, Any]] = []
    ledger_supported = False
    ledger_basis = ""
    ledger_error = ""
    ledger: Optional[Mapping[str, Any]] = None
    try:
        candidate = _json_clone(reader(path, client=None))
        if not isinstance(candidate, Mapping) or not isinstance(candidate.get("tasks", []), list):
            raise ValueError("task ledger did not return {tasks: [...]} shape")
        ledger = candidate
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        detail = _bounded_text(str(exc), 240)[0]
        ledger_error = f"{type(exc).__name__}: {detail}"

    if ledger is not None:
        revision = "sha256:" + hashlib.sha256(_canonical_bytes(ledger)).hexdigest()
        ledger_basis = f"source:task-ledger-git@{revision}"
        sources.append(
            {
                "name": "task-ledger-git",
                "plane": "durable-ledger",
                "authority": "governed_source",
                "revision": revision,
                "checked_at": source_checked_at,
                "drill": str(Path(path)),
            }
        )
        ledger_supported = True
        for task in ledger.get("tasks", []):
            if not isinstance(task, Mapping) or not _text(task.get("id")):
                continue
            status = _text(task.get("status")).lower() or "unknown"
            tid = _text(task["id"])
            title, title_full_chars, title_truncated = _bounded_text(task.get("title"), 240)
            deps, deps_total, deps_truncated = _bounded_text_list(task.get("deps"), item_limit=8)
            files, files_total, files_truncated = _bounded_text_list(
                task.get("files"), item_limit=8
            )
            items.append(
                {
                    "object_ref": f"task:{tid}",
                    "organ": "ledger",
                    "attention": _task_attention(status),
                    "source_refs": ["task-ledger-git"],
                    "data": {
                        "id": tid,
                        "title": title,
                        "title_full_chars": title_full_chars,
                        "title_truncated": title_truncated,
                        "status": status,
                        "status_valid": status in _TASK_STATUS_VOCABULARY,
                        "attention_basis": _TASK_ATTENTION_POLICY,
                        "owner": _text(task.get("owner")),
                        "deps": deps,
                        "deps_total": deps_total,
                        "deps_truncated": deps_truncated,
                        "files": files,
                        "files_total": files_total,
                        "files_truncated": files_truncated,
                        "commit": task.get("commit"),
                        "arc": _text(task.get("arc")) or "UNCLASSIFIED",
                    },
                    "epistemic_view": _task_epistemic_view(
                        ledger_basis, status, source_checked_at
                    ),
                }
            )
    return assemble_world_snapshot(
        subject=subject,
        sources=sources,
        items=items,
        capabilities=_program_capabilities(ledger_supported, ledger_basis, ledger_error),
        generated_at=one_clock,
        max_items=max_items,
        projection_label="ledger projection",
    )


def project_operational_brief(
    snapshot: Mapping[str, Any], *, max_items: int = 8
) -> Dict[str, Any]:
    """Project a compact operational orientation packet from one snapshot.

    This deliberately is *not* an identity or relationship-continuity capsule.
    It may help a seat resume work, but it has no authority to answer who that
    seat is, what it remembers phenomenologically, or whose history applies.
    """
    if _text(snapshot.get("schema_version")) != SCHEMA_VERSION:
        raise ValueError("operational brief requires a world-snapshot/v1 input")
    if isinstance(max_items, bool) or int(max_items) < 0:
        raise ValueError("max_items must be a non-negative integer")
    max_items = int(max_items)
    rows = _json_clone(snapshot.get("items") or [])
    focus = rows[:max_items]
    source_refs = sorted(
        {
            ref
            for item in focus
            for ref in item.get("source_refs", [])
            if _text(ref)
        }
    )
    sources = [
        _json_clone(source)
        for source in snapshot.get("sources", [])
        if source.get("name") in source_refs
    ]
    brief: Dict[str, Any] = {
        "schema_version": BRIEF_SCHEMA_VERSION,
        "purpose": "operational_orientation",
        "identity_authority": "none",
        "snapshot_id": _text(snapshot.get("snapshot_id")),
        "projection_id": _text(snapshot.get("projection_id")),
        "source_render_id": _text(snapshot.get("render_id")),
        "subject": _text(snapshot.get("subject")),
        "source_refs": source_refs,
        "sources": sources,
        "summary": _json_clone(snapshot.get("summary") or {}),
        "capabilities": _json_clone(snapshot.get("capabilities") or {}),
        "bounds": {
            "item_limit": max_items,
            "available_items": len(rows),
            "returned_items": len(focus),
            "truncated": len(focus) < len(rows),
            "source_snapshot_total": (snapshot.get("bounds") or {}).get("total_items"),
        },
        "focus": focus,
    }
    brief["brief_id"] = _hash_id("ob_", _without_observation_clocks(brief))
    return brief


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only WorldSnapshot SUBJECT / ATTENTION projection"
    )
    parser.add_argument("--subject", default="akashic-aurora-program")
    parser.add_argument("--ledger-path", default=None)
    parser.add_argument("--max-items", type=int, default=64)
    parser.add_argument("--brief", action="store_true", help="emit operational brief")
    args = parser.parse_args(list(argv) if argv is not None else None)
    snapshot = build_program_world_snapshot(
        subject=args.subject,
        ledger_path=args.ledger_path,
        max_items=args.max_items,
    )
    rendered = project_operational_brief(snapshot) if args.brief else snapshot
    print(json.dumps(rendered, ensure_ascii=False, indent=2))
    return 0


__all__ = [
    "BRIEF_SCHEMA_VERSION",
    "PROJECTION_VERSION",
    "SCHEMA_VERSION",
    "assemble_world_snapshot",
    "build_program_world_snapshot",
    "project_operational_brief",
]


if __name__ == "__main__":  # pragma: no cover - exercised as a live dogfood surface
    raise SystemExit(main())
