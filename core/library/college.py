"""Unofficial College record -- source, voice, audit, teach-back, errata.

This module is deliberately an epistemic protocol, not an answer generator.  It
does not browse, call a model, or promote a locator to evidence.  Its job is to
keep the work that different people or seats perform in different, inspectable
planes:

* source records say what was gathered and who asserted its status;
* one lecturer seals exact authored bytes once;
* a different designated auditor records typed claim verdicts and receipts;
* learners append teach-backs;
* corrections append as errata and never rewrite the lecture.

``events.jsonl`` is the append-only truth.  Every event binds the previous event
hash, so a later read can distinguish an intact history from plausible-looking
edited evidence.  ``lecture.md`` is the human-readable sealed body and is checked
against the hash in the event chain on every ``show``.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from core.foundation import filelock
from core.paths import repo_root


SCHEMA = "college.record.v1"
EVENT_SCHEMA = "college.event.v1"
ROOT_ENV = "AURORA_COLLEGE_ROOT"
ZERO_HASH = "0" * 64

SOURCE_TYPES = ("primary", "secondary", "measurement", "analysis")
SOURCE_STATUSES = ("candidate", "retrieved", "verified", "rejected")
CLAIM_SPECIES = (
    "mechanism",
    "measurement",
    "vendor_attribution",
    "metaphor",
    "design_prescription",
    "continuity_provenance",
)
AUDIT_VERDICTS = (
    "supported", "qualified", "disputed", "unresolved", "metaphor", "prescription",
)

_COURSE_RE = re.compile(r"[a-z0-9](?:[a-z0-9._-]{0,78}[a-z0-9])?")
_ID_RE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._:-]{0,126}[A-Za-z0-9])?")
_MAX_LECTURE_BYTES = 2_000_000
_SECRET_NAMES = {".env", "id_rsa", "id_dsa", "credentials", "credentials.json"}
_SECRET_SUFFIXES = {".key", ".pem", ".crt", ".pfx", ".p12", ".der", ".kdbx"}


class CollegeError(ValueError):
    """A contract refusal.  No event is appended after this is raised."""


def college_root(root: Optional[os.PathLike | str] = None) -> Path:
    """Resolve the one bounded course root; an env override keeps tests isolated."""
    if root is not None:
        return Path(root)
    configured = os.environ.get(ROOT_ENV, "").strip()
    if configured:
        return Path(configured)
    return repo_root() / "artifacts" / "college"


def _course_dir(course: str, root: Optional[os.PathLike | str]) -> Path:
    ident = str(course or "").strip()
    if not _COURSE_RE.fullmatch(ident):
        raise CollegeError(
            "course id must be 1..80 lowercase letters, digits, dot, dash, or underscore"
        )
    return college_root(root) / ident


def _now(value: Optional[str]) -> str:
    if value is not None:
        stamp = str(value).strip()
        if not stamp:
            raise CollegeError("now must be a non-empty timestamp when supplied")
        return stamp
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _text(data: Mapping[str, Any], key: str, *, limit: int, required: bool = True) -> str:
    value = data.get(key)
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise CollegeError(f"{key} must be a string")
    value = value.strip()
    if required and not value:
        raise CollegeError(f"{key} is required")
    if len(value) > limit:
        raise CollegeError(f"{key} exceeds the {limit}-character bound")
    return value


def _ident(data: Mapping[str, Any], key: str) -> str:
    value = _text(data, key, limit=128)
    if not _ID_RE.fullmatch(value):
        raise CollegeError(f"{key} must be a stable 1..128 character identifier")
    return value


def _actor(value: str, *, required: bool = True) -> str:
    actor = str(value or "").strip()
    if required and not actor:
        raise CollegeError("actor is required for college writes")
    if len(actor) > 80:
        raise CollegeError("actor exceeds the 80-character bound")
    return actor


def _string_list(data: Mapping[str, Any], key: str) -> List[str]:
    raw = data.get(key, [])
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(v, str) for v in raw):
        raise CollegeError(f"{key} must be a JSON list of strings")
    values: List[str] = []
    for item in raw:
        item = item.strip()
        if not item:
            continue
        if not _ID_RE.fullmatch(item):
            raise CollegeError(f"{key} contains an invalid identifier {item!r}")
        if item not in values:
            values.append(item)
    if len(values) > 32:
        raise CollegeError(f"{key} exceeds the 32-item bound")
    return values


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _event_hash(event_without_hash: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(event_without_hash)).hexdigest()


def _read_events(path: Path, *, course: str) -> Tuple[List[Dict[str, Any]], bool, List[str]]:
    if not path.exists():
        return [], True, []
    rows: List[Dict[str, Any]] = []
    problems: List[str] = []
    expected_prev = ZERO_HASH
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        return [], False, [f"event log unreadable: {exc}"]
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            problems.append(f"event chain line {line_no} is invalid JSON: {exc.msg}")
            continue
        if not isinstance(row, dict):
            problems.append(f"event chain line {line_no} is not an object")
            continue
        rows.append(row)
        seq = len(rows)
        if row.get("schema") != EVENT_SCHEMA:
            problems.append(f"event chain line {line_no} has unknown schema")
        if row.get("course_id") != course:
            problems.append(f"event chain line {line_no} names another course")
        if row.get("seq") != seq or row.get("event_id") != f"e{seq:06d}":
            problems.append(f"event chain sequence breaks at line {line_no}")
        if row.get("previous_hash") != expected_prev:
            problems.append(f"event chain previous hash breaks at line {line_no}")
        stored_hash = str(row.get("event_hash") or "")
        unhashed = dict(row)
        unhashed.pop("event_hash", None)
        if stored_hash != _event_hash(unhashed):
            problems.append(f"event chain content hash breaks at line {line_no}")
        expected_prev = stored_hash
    return rows, not problems, problems


def _append_event(path: Path, events: List[Dict[str, Any]], *, course: str,
                  kind: str, actor: str, payload: Dict[str, Any], at: str) -> Dict[str, Any]:
    seq = len(events) + 1
    event: Dict[str, Any] = {
        "schema": EVENT_SCHEMA,
        "seq": seq,
        "event_id": f"e{seq:06d}",
        "course_id": course,
        "kind": kind,
        "at": at,
        "actor": actor,
        "payload": payload,
        "previous_hash": events[-1]["event_hash"] if events else ZERO_HASH,
    }
    event["event_hash"] = _event_hash(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    events.append(event)
    return event


def _fold(events: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    course: Optional[Dict[str, Any]] = None
    sources: Dict[str, Dict[str, Any]] = {}
    lecture: Optional[Dict[str, Any]] = None
    audits: List[Dict[str, Any]] = []
    teachbacks: List[Dict[str, Any]] = []
    errata: List[Dict[str, Any]] = []
    for event in events:
        payload = dict(event.get("payload") or {})
        payload.update({
            "actor": event.get("actor"), "at": event.get("at"),
            "event_id": event.get("event_id"),
        })
        kind = event.get("kind")
        if kind == "course.started":
            course = payload
        elif kind == "source.recorded":
            sources[str(payload.get("source_id"))] = payload
        elif kind == "lecture.sealed":
            lecture = payload
        elif kind == "audit.recorded":
            audits.append(payload)
        elif kind == "teachback.recorded":
            teachbacks.append(payload)
        elif kind == "erratum.recorded":
            errata.append(payload)
    return {
        "course": course,
        "sources": sources,
        "lecture": lecture,
        "audit": audits,
        "teachbacks": teachbacks,
        "errata": errata,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(128 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_lecture_path(raw: str, root: Optional[os.PathLike | str]) -> Path:
    """Resolve a lecture input without creating a new read/exfiltration door."""
    if not isinstance(raw, str) or not raw.strip():
        raise CollegeError("path must be a non-empty string")
    if len(raw) > 4000:
        raise CollegeError("path exceeds the 4000-character bound")
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root() / path
    path = path.resolve()
    allowed_roots = [repo_root().resolve(), college_root(root).resolve()]
    if root is not None:
        allowed_roots.append(Path(root).resolve())

    def _inside(base: Path) -> bool:
        try:
            return os.path.commonpath([str(base), str(path)]) == str(base)
        except ValueError:
            return False

    if not any(_inside(base) for base in allowed_roots):
        raise CollegeError("lecture path is outside the allowed root")
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if ".secrets" in parts or name in _SECRET_NAMES or name.startswith(".env.") \
            or path.suffix.lower() in _SECRET_SUFFIXES:
        raise CollegeError("refusing to copy a secret or credential-shaped lecture path")
    return path


def _view(course: str, course_dir: Path, events: List[Dict[str, Any]], *,
          chain_ok: bool, chain_problems: List[str], action: str,
          effects: Optional[List[Dict[str, Any]]] = None,
          subject: str = "") -> Dict[str, Any]:
    state = _fold(events)
    started = state["course"] or {}
    course_card = {
        "id": course,
        "title": started.get("title", ""),
        "topic": started.get("topic", ""),
        "lecturer": started.get("lecturer", ""),
        "auditor": started.get("auditor", ""),
        "started_by": started.get("actor", ""),
        "started_at": started.get("at", ""),
    }
    source_rows = sorted(state["sources"].values(), key=lambda row: str(row.get("source_id")))
    verified_primary = sum(
        1 for row in source_rows
        if row.get("source_kind") == "primary" and row.get("status") == "verified"
    )

    lecture_event = state["lecture"]
    lecture_path = course_dir / "lecture.md"
    lecture_integrity: Optional[bool] = None
    lecture_card: Dict[str, Any] = {"sealed": False, "path": str(lecture_path)}
    if lecture_event:
        actual_sha = _sha256(lecture_path) if lecture_path.is_file() else None
        lecture_integrity = actual_sha == lecture_event.get("sha256")
        lecture_card.update({
            "sealed": True,
            "sha256": lecture_event.get("sha256"),
            "bytes": lecture_event.get("bytes"),
            "actor": lecture_event.get("actor"),
            "at": lecture_event.get("at"),
            "event_id": lecture_event.get("event_id"),
            "source_path": lecture_event.get("source_path"),
        })

    gaps: List[str] = []
    if not chain_ok:
        gaps.append("event chain integrity failed: " + "; ".join(chain_problems[:3]))
    if verified_primary == 0:
        gaps.append("no verified primary source")
    if not lecture_event:
        gaps.append("lecture is not sealed")
    elif lecture_integrity is False:
        gaps.append("lecture hash mismatch or sealed file missing")
    if not state["audit"]:
        gaps.append("no claim audit recorded")
    elif not any(bool(row.get("coverage_complete")) for row in state["audit"]):
        gaps.append("audit coverage is not explicitly closed by the designated auditor")
    if not state["teachbacks"]:
        gaps.append("no teach-back recorded")

    return {
        "schema": SCHEMA,
        "action": action,
        "subject": subject or None,
        "course": course_card,
        "stages": {
            "sources": {"records": len(source_rows), "verified_primary": verified_primary},
            "lecture": {"sealed": bool(lecture_event)},
            "audit": {
                "records": len(state["audit"]),
                "coverage_declared": any(
                    bool(row.get("coverage_complete")) for row in state["audit"]
                ),
            },
            "teachback": {"records": len(state["teachbacks"])},
            "errata": {"records": len(state["errata"])},
        },
        "sources": source_rows,
        "lecture": lecture_card,
        "audit": state["audit"],
        "teachbacks": state["teachbacks"],
        "errata": state["errata"],
        "integrity": {"event_chain": chain_ok, "lecture": lecture_integrity},
        "bounds": {
            "events": len(events),
            "source_records_current": len(source_rows),
            "lecture_max_bytes": _MAX_LECTURE_BYTES,
        },
        "gaps": gaps,
        "blind": [
            "source status and receipts are actor assertions; college does not independently verify locators or source contents",
            "audit coverage is auditor-declared, not inferred from prose or independently proven by college",
            "teach-back records one explanation at one time; it is not proof of durable mastery",
        ],
        "effects": list(effects or []),
    }


def _require_course(state: Mapping[str, Any]) -> Mapping[str, Any]:
    course = state.get("course")
    if not course:
        raise CollegeError("course has no valid course.started event")
    return course


def _known_sources(state: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    return dict(state.get("sources") or {})


def _require_source_ids(state: Mapping[str, Any], ids: List[str]) -> None:
    known = _known_sources(state)
    missing = [source_id for source_id in ids if source_id not in known]
    if missing:
        raise CollegeError("unknown source_ids: " + ", ".join(missing))


def _require_verified_source_ids(state: Mapping[str, Any], ids: List[str]) -> None:
    _require_source_ids(state, ids)
    known = _known_sources(state)
    unverified = [source_id for source_id in ids if known[source_id].get("status") != "verified"]
    if unverified:
        raise CollegeError("audit receipts require verified source_ids: " + ", ".join(unverified))


def _require_intact_lecture(state: Mapping[str, Any], course_dir: Path) -> Tuple[Mapping[str, Any], str]:
    lecture = state.get("lecture")
    if not lecture:
        raise CollegeError("operation requires a sealed lecture")
    path = course_dir / "lecture.md"
    if not path.is_file() or _sha256(path) != lecture.get("sha256"):
        raise CollegeError("sealed lecture integrity failed; refusing to append evidence against changed bytes")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CollegeError("sealed lecture integrity failed: UTF-8 body is unreadable") from exc
    return lecture, text


def _atomic_write_new(path: Path, body: bytes) -> None:
    """Create one immutable file without a replace path that could rewrite voice."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "xb") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())
    except FileExistsError as exc:
        raise CollegeError("lecture is already sealed; corrections belong in errata") from exc


def run_college(action: str, course: str, data: Optional[Dict[str, Any]] = None, *,
                actor: str = "", root: Optional[os.PathLike | str] = None,
                now: Optional[str] = None) -> Dict[str, Any]:
    """Run one college action through the native structured provider.

    Write actions are serialized by a cross-process lock and append exactly one
    hash-linked event (plus the one-time lecture file for ``lecture``).  ``show``
    performs no write, lock, cursor advance, network call, or model call.
    """
    action = str(action or "").strip().lower().replace("-", "_")
    aliases = {"add_source": "source", "seal_lecture": "lecture",
               "add_audit": "audit", "teach_back": "teachback",
               "add_erratum": "erratum", "status": "show"}
    action = aliases.get(action, action)
    if action not in {"start", "source", "lecture", "audit", "teachback", "erratum", "show"}:
        raise CollegeError(
            "action must be start|source|lecture|audit|teachback|erratum|show"
        )
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise CollegeError("data must be one JSON object")

    course_dir = _course_dir(course, root)
    events_path = course_dir / "events.jsonl"
    if action == "show":
        events, chain_ok, problems = _read_events(events_path, course=course)
        if not events:
            raise CollegeError(f"unknown college course {course!r}")
        return _view(
            course, course_dir, events, chain_ok=chain_ok, chain_problems=problems,
            action="show", effects=[], subject=_actor(actor, required=False),
        )

    who = _actor(actor)
    stamp = _now(now)
    course_dir.mkdir(parents=True, exist_ok=True)
    with filelock.exclusive(events_path):
        events, chain_ok, problems = _read_events(events_path, course=course)
        if not chain_ok:
            raise CollegeError("refusing write because event chain integrity failed: " + problems[0])
        state = _fold(events)
        payload: Dict[str, Any]
        kind: str
        extra_effects: List[Dict[str, Any]] = []

        if action == "start":
            if events:
                raise CollegeError(f"college course {course!r} already exists")
            lecturer = _text(data, "lecturer", limit=80)
            auditor = _text(data, "auditor", limit=80)
            if lecturer.casefold() == auditor.casefold():
                raise CollegeError("lecturer and auditor must differ; self-audit is not independent review")
            payload = {
                "title": _text(data, "title", limit=240),
                "topic": _text(data, "topic", limit=2000),
                "lecturer": lecturer,
                "auditor": auditor,
            }
            kind = "course.started"

        else:
            started = _require_course(state)
            lecturer = str(started.get("lecturer") or "")
            auditor = str(started.get("auditor") or "")

            if action == "source":
                source_id = _ident(data, "source_id")
                source_kind = _text(data, "source_kind", limit=40)
                status = _text(data, "status", limit=40)
                if source_kind not in SOURCE_TYPES:
                    raise CollegeError(f"source_kind must be one of {SOURCE_TYPES}")
                if status not in SOURCE_STATUSES:
                    raise CollegeError(f"status must be one of {SOURCE_STATUSES}")
                receipt = _text(data, "receipt", limit=20_000, required=False)
                retrieved_at = _text(data, "retrieved_at", limit=80, required=False)
                if status == "verified":
                    if who.casefold() != auditor.casefold():
                        raise CollegeError("only the designated auditor may mark a source verified")
                    if not receipt:
                        raise CollegeError("receipt is required before a source can be verified")
                    if not retrieved_at:
                        raise CollegeError("retrieved_at is required before a source can be verified")
                previous = _known_sources(state).get(source_id)
                if previous:
                    if previous.get("locator") != _text(data, "locator", limit=2000):
                        raise CollegeError("source_id cannot be reassigned to another locator")
                    if previous.get("source_kind") != source_kind:
                        raise CollegeError("source_id cannot change source_kind")
                    order = {"candidate": 0, "retrieved": 1, "verified": 2, "rejected": 2}
                    if order[status] < order.get(str(previous.get("status")), 0):
                        raise CollegeError("source status cannot move backward; append a new source id")
                payload = {
                    "source_id": source_id,
                    "title": _text(data, "title", limit=500),
                    "locator": _text(data, "locator", limit=2000),
                    "source_kind": source_kind,
                    "status": status,
                    "receipt": receipt,
                    "retrieved_at": retrieved_at or None,
                }
                kind = "source.recorded"

            elif action == "lecture":
                if who.casefold() != lecturer.casefold():
                    raise CollegeError("only the designated lecturer may seal the lecture")
                verified_primary = [
                    row for row in _known_sources(state).values()
                    if row.get("source_kind") == "primary" and row.get("status") == "verified"
                ]
                if not verified_primary:
                    raise CollegeError("lecture requires at least one verified primary source")
                path_value = data.get("path")
                text_value = data.get("text")
                if path_value is not None and text_value is not None:
                    raise CollegeError("lecture accepts exactly one of path or text")
                if path_value is not None:
                    source_path = _safe_lecture_path(path_value, root)
                    if not source_path.is_file():
                        raise CollegeError(f"lecture path is not a file: {source_path}")
                    body = source_path.read_bytes()
                    source_label = str(source_path)
                elif text_value is not None:
                    if not isinstance(text_value, str) or not text_value:
                        raise CollegeError("text must be a non-empty string")
                    body = text_value.encode("utf-8")
                    source_label = "inline"
                else:
                    raise CollegeError("lecture requires path or text")
                if len(body) > _MAX_LECTURE_BYTES:
                    raise CollegeError(f"lecture exceeds the {_MAX_LECTURE_BYTES}-byte bound")
                try:
                    body.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise CollegeError("lecture must be UTF-8 text") from exc
                sealed_path = course_dir / "lecture.md"
                body_sha = hashlib.sha256(body).hexdigest()
                previous_seal = state.get("lecture")
                if previous_seal:
                    if previous_seal.get("sha256") != body_sha:
                        raise CollegeError(
                            "lecture is already sealed with different bytes; corrections belong in errata"
                        )
                    if sealed_path.is_file():
                        if _sha256(sealed_path) != body_sha:
                            raise CollegeError(
                                "sealed lecture hash mismatch; refusing to overwrite possible tampering"
                            )
                        return _view(
                            course, course_dir, events, chain_ok=True, chain_problems=[],
                            action="lecture", effects=[], subject=who,
                        )
                    _atomic_write_new(sealed_path, body)
                    return _view(
                        course, course_dir, events, chain_ok=True, chain_problems=[],
                        action="lecture",
                        effects=[{"kind": "create", "path": str(sealed_path)}],
                        subject=who,
                    )
                if sealed_path.exists():
                    if not sealed_path.is_file() or _sha256(sealed_path) != body_sha:
                        raise CollegeError(
                            "unrecorded lecture bytes already exist and differ; refusing to overwrite"
                        )
                else:
                    _atomic_write_new(sealed_path, body)
                    extra_effects.append({"kind": "create", "path": str(sealed_path)})
                payload = {
                    "sha256": body_sha,
                    "bytes": len(body),
                    "source_path": source_label,
                }
                kind = "lecture.sealed"

            elif action == "audit":
                if who.casefold() != auditor.casefold():
                    raise CollegeError("only the designated auditor may author the claim audit")
                lecture_event, lecture_text = _require_intact_lecture(state, course_dir)
                claim_id = _ident(data, "claim_id")
                if any(row.get("claim_id") == claim_id for row in state.get("audit") or []):
                    raise CollegeError("claim_id is already audited; append an erratum to correct it")
                anchor = _text(data, "anchor", limit=4000)
                if anchor not in lecture_text:
                    raise CollegeError("anchor must be an exact excerpt from the sealed lecture")
                species = _text(data, "species", limit=80)
                verdict = _text(data, "verdict", limit=80)
                if species not in CLAIM_SPECIES:
                    raise CollegeError(f"species must be one of {CLAIM_SPECIES}")
                if verdict not in AUDIT_VERDICTS:
                    raise CollegeError(f"verdict must be one of {AUDIT_VERDICTS}")
                if species == "metaphor" and verdict != "metaphor":
                    raise CollegeError("metaphor claims use the metaphor verdict")
                if species == "design_prescription" and verdict != "prescription":
                    raise CollegeError("design prescriptions use the prescription verdict")
                if species not in {"metaphor", "design_prescription"} and verdict in {"metaphor", "prescription"}:
                    raise CollegeError("metaphor/prescription verdict does not match this claim species")
                source_ids = _string_list(data, "source_ids")
                if species not in {"metaphor", "design_prescription"} and not source_ids:
                    raise CollegeError("evidence-bearing audit claims require source_ids")
                _require_verified_source_ids(state, source_ids)
                coverage_complete = data.get("coverage_complete", False)
                if not isinstance(coverage_complete, bool):
                    raise CollegeError("coverage_complete must be a boolean")
                coverage_receipt = _text(
                    data, "coverage_receipt", limit=20_000, required=coverage_complete
                )
                payload = {
                    "claim_id": claim_id,
                    "claim": _text(data, "claim", limit=8000),
                    "anchor": anchor,
                    "species": species,
                    "verdict": verdict,
                    "receipt": _text(data, "receipt", limit=20_000),
                    "source_ids": source_ids,
                    "coverage_complete": coverage_complete,
                    "coverage_receipt": coverage_receipt or None,
                    "lecture_sha256": lecture_event.get("sha256"),
                }
                kind = "audit.recorded"

            elif action == "teachback":
                lecture_event, _lecture_text = _require_intact_lecture(state, course_dir)
                payload = {
                    "question": _text(data, "question", limit=8000),
                    "answer": _text(data, "answer", limit=30_000),
                    "lecture_sha256": lecture_event.get("sha256"),
                }
                kind = "teachback.recorded"

            else:  # erratum
                lecture_event, _lecture_text = _require_intact_lecture(state, course_dir)
                claim_id = _ident(data, "claim_id")
                if not any(row.get("claim_id") == claim_id for row in state.get("audit") or []):
                    raise CollegeError("erratum claim_id must target an existing audit claim")
                source_ids = _string_list(data, "source_ids")
                _require_verified_source_ids(state, source_ids)
                payload = {
                    "claim_id": claim_id,
                    "correction": _text(data, "correction", limit=20_000),
                    "reason": _text(data, "reason", limit=20_000),
                    "source_ids": source_ids,
                    "lecture_sha256": lecture_event.get("sha256"),
                }
                kind = "erratum.recorded"

        event = _append_event(
            events_path, events, course=course, kind=kind, actor=who,
            payload=payload, at=stamp,
        )
        effects = extra_effects + [{
            "kind": "append", "path": str(events_path), "event_id": event["event_id"],
        }]
        return _view(
            course, course_dir, events, chain_ok=True, chain_problems=[],
            action=action, effects=effects, subject=who,
        )


def render_college(record: Mapping[str, Any]) -> str:
    """Compact human rendering; structured callers should consume the record directly."""
    course = record.get("course") or {}
    integrity = record.get("integrity") or {}
    stages = record.get("stages") or {}
    lines = [
        f"# college {course.get('id', '?')} -- {course.get('title') or '(untitled)'}",
        f"roles lecturer={course.get('lecturer') or '?'}  auditor={course.get('auditor') or '?'}",
        "stages " + "  ".join(
            f"{name}={row.get('records', 'sealed' if row.get('sealed') else 0)}"
            for name, row in stages.items()
        ),
        f"integrity events={'OK' if integrity.get('event_chain') else 'FAIL'}  "
        f"lecture={('OK' if integrity.get('lecture') else 'FAIL') if integrity.get('lecture') is not None else 'UNSEALED'}",
    ]
    gaps = list(record.get("gaps") or [])
    lines.append("gaps none" if not gaps else "gaps " + " | ".join(gaps))
    effects = list(record.get("effects") or [])
    lines.append("effects none" if not effects else "effects " + ", ".join(
        f"{row.get('kind')}:{row.get('path')}" for row in effects
    ))
    return "\n".join(lines)
