"""Subject-bound, non-consuming Bifrost thread capture (T084 S2).

The archive reader sees exactly four streams for one subject: legacy/work inbox
and legacy/work broadcast.  It never enumerates another seat's inbox, advances a
cursor, registers presence, or touches a watcher.  Membership comes only from
explicit transport/thread links; body-text resemblance is never a link.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


_ROOT = Path(__file__).resolve().parents[2]
_LINK_FIELDS = (
    "thread_id", "source_thread", "answers", "reply_id", "ask_id",
    "redrive_of", "original_mid", "in_reply_to", "parent_id",
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value if value is not None else "")


def _loads(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(_text(value))
    except Exception:
        return default


def _content(value: Any) -> str:
    """Unwrap the bus's sometimes-double-encoded content without changing bytes."""
    current = _text(value)
    for _ in range(2):
        try:
            decoded = json.loads(current)
        except Exception:
            break
        if isinstance(decoded, str):
            current = decoded
        else:
            current = json.dumps(decoded, ensure_ascii=False, default=str)
            break
    return current


def _tokens(value: Any) -> Iterable[str]:
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _tokens(item)
        return
    if isinstance(value, dict):
        for item in value.values():
            yield from _tokens(item)
        return
    token = _text(value).strip()
    if token:
        yield token


def _fallback_sha(fields: Mapping[str, Any]) -> str:
    raw = "\x1f".join(_text(fields.get(k)) for k in
                       ("frm", "to", "kind", "content", "ts", "meta", "parts"))
    return "fallback:" + hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()


def _stream_keys(namespace: str, subject: str) -> Tuple[str, ...]:
    return (
        f"{namespace}:inbox:{subject}",
        f"{namespace}:work:inbox:{subject}",
        f"{namespace}:broadcast",
        f"{namespace}:work:broadcast",
    )


def _entry(stream: str, sid: Any, raw_fields: Mapping[str, Any]) -> Dict[str, Any]:
    fields = {_text(k): v for k, v in dict(raw_fields or {}).items()}
    meta = _loads(fields.get("meta"), {})
    if not isinstance(meta, dict):
        meta = {}
    parts = _loads(fields.get("parts"), [])
    if not isinstance(parts, list):
        parts = []
    sha = _text(fields.get("sha") or meta.get("sha")).strip() or _fallback_sha(fields)
    copy_id = _text(sid)
    links = {copy_id, sha}
    for key in _LINK_FIELDS:
        for token in _tokens(meta.get(key)):
            links.add(token)
    return {
        "sha": sha,
        "frm": _text(fields.get("frm")),
        "to": _text(fields.get("to")),
        "kind": _text(fields.get("kind")),
        "content": _content(fields.get("content") if "content" in fields else fields.get("text")),
        "ts": _text(fields.get("ts")),
        "meta": meta,
        "parts": parts,
        "links": links,
        "copy": {"stream": stream, "id": copy_id},
    }


def _copy_sort(row: Mapping[str, Any]) -> Tuple[str, str]:
    return (_text(row.get("stream")), _text(row.get("id")))


def _logical_sort(row: Mapping[str, Any]) -> Tuple[str, str]:
    copies = row.get("copies") or []
    first = min((_text(c.get("id")) for c in copies), default="")
    return (_text(row.get("ts")) or "9999", first)


def collect_thread(subject: str, thread_ref: str, *, client: Any = None,
                   namespace: str = "bifrost", per_stream: int = 1000) -> Dict[str, Any]:
    """Return a bounded ``capture.thread.v1`` observation.

    ``client`` is injectable for pins.  Production obtains the existing Redis
    client through ``Bus`` but calls only GET/XLEN/XREVRANGE.
    """
    subject = _text(subject).strip()
    ref = _text(thread_ref).strip()
    if not subject:
        raise ValueError("capture subject is required")
    if not ref:
        raise ValueError("thread reference is required")
    cap = max(1, min(int(per_stream or 1000), 5000))
    ns = _text(namespace).strip() or "bifrost"
    if client is None:
        from core.comm.bus import Bus
        bus = Bus(subject)
        client = bus._client
        ns = bus.ns
    if client is None:
        return {
            "schema": "capture.thread.v1", "subject": subject,
            "thread_ref": ref, "observed_at": _utc(), "found": False,
            "messages": [],
            "bounds": {"streams_total": 4, "streams_read": 0,
                       "streams_failed": 4, "per_stream": cap,
                       "entries_total": None, "entries_scanned": 0,
                       "logical_candidates": 0, "messages_matched": 0,
                       "copies_matched": 0, "duplicates_collapsed": 0,
                       "truncated": False,
                       "ordering": "timestamp then stream id ascending",
                       "stream_rows": []},
            "blind": ["bus offline: no archive streams were readable",
                      f"thread {ref} not found in the unreadable subject-bound archive view"],
            "effects": [],
        }

    stream_rows: List[Dict[str, Any]] = []
    candidates: List[Dict[str, Any]] = []
    failures: Dict[str, str] = {}
    entries_total = 0
    total_known = True
    for key in _stream_keys(ns, subject):
        try:
            total = int(client.xlen(key) or 0)
            raw_rows = list(client.xrevrange(key, count=cap) or [])
            scanned = len(raw_rows)
            entries_total += total
            truncated = total > scanned
            stream_rows.append({"stream": key, "total": total, "scanned": scanned,
                                "truncated": truncated})
            for sid, fields in raw_rows:
                candidates.append(_entry(key, sid, fields))
        except Exception as exc:
            total_known = False
            failures[key] = f"{type(exc).__name__}: {exc}"
            stream_rows.append({"stream": key, "total": None, "scanned": 0,
                                "truncated": None, "error": failures[key]})

    by_sha: Dict[str, Dict[str, Any]] = {}
    for row in candidates:
        sha = row["sha"]
        if sha not in by_sha:
            by_sha[sha] = {
                "sha": sha, "frm": row["frm"], "to": row["to"],
                "kind": row["kind"], "content": row["content"], "ts": row["ts"],
                "meta": row["meta"], "parts": row["parts"],
                "links": set(row["links"]), "copies": [row["copy"]],
            }
        else:
            by_sha[sha]["links"].update(row["links"])
            by_sha[sha]["copies"].append(row["copy"])

    seeds = {ref}
    try:
        alias = client.get(f"{ns}:idalias:{ref}")
        if alias:
            seeds.add(_text(alias))
    except Exception as exc:
        failures[f"{ns}:idalias:{ref}"] = f"{type(exc).__name__}: {exc}"

    chosen: set[str] = set()
    known = set(seeds)
    changed = True
    while changed:
        changed = False
        for sha, row in by_sha.items():
            if sha in chosen:
                continue
            if set(row["links"]) & known:
                chosen.add(sha)
                known.update(row["links"])
                changed = True

    messages: List[Dict[str, Any]] = []
    copies_matched = 0
    for sha in chosen:
        row = by_sha[sha]
        copies = sorted(row["copies"], key=_copy_sort)
        copies_matched += len(copies)
        messages.append({
            "id": copies[0]["id"] if copies else "",
            "sha": sha,
            "frm": row["frm"], "to": row["to"], "kind": row["kind"],
            "ts": row["ts"], "content": row["content"],
            "meta": row["meta"], "parts": row["parts"], "copies": copies,
        })
    messages.sort(key=_logical_sort)

    truncated_any = any(r.get("truncated") is True for r in stream_rows)
    blind: List[str] = []
    for key, why in sorted(failures.items()):
        blind.append(f"archive source {key} unreadable: {why}")
    if truncated_any:
        blind.append(f"TRUNCATED: one or more archive streams exceeded the per-stream cap {cap}; older links may be outside view")
    if not messages:
        blind.append(f"thread {ref} not found in the subject-bound archive view")

    return {
        "schema": "capture.thread.v1",
        "subject": subject,
        "thread_ref": ref,
        "observed_at": _utc(),
        "found": bool(messages),
        "messages": messages,
        "bounds": {
            "streams_total": 4,
            "streams_read": 4 - sum(1 for r in stream_rows if r.get("error")),
            "streams_failed": sum(1 for r in stream_rows if r.get("error")),
            "per_stream": cap,
            "entries_total": entries_total if total_known else None,
            "entries_scanned": len(candidates),
            "logical_candidates": len(by_sha),
            "messages_matched": len(messages),
            "copies_matched": copies_matched,
            "duplicates_collapsed": max(0, copies_matched - len(messages)),
            "truncated": truncated_any,
            "ordering": "timestamp then stream id ascending",
            "stream_rows": stream_rows,
        },
        "blind": blind,
        "effects": [],
    }


def render_transcript(snapshot: Mapping[str, Any], *, title: str) -> str:
    bounds = snapshot.get("bounds") or {}
    lines = [
        f"# {title}", "",
        (f"Captured verbatim from a subject-bound archive view for "
         f"`{snapshot.get('subject')}`. Thread membership uses explicit transport links; "
         "body-text resemblance is excluded."), "",
        f"- thread ref: `{snapshot.get('thread_ref')}`",
        f"- observed at: {snapshot.get('observed_at')}",
        (f"- coverage: {bounds.get('streams_read')}/{bounds.get('streams_total')} streams; "
         f"{bounds.get('entries_scanned')} entries scanned"
         + (f" of {bounds.get('entries_total')}" if bounds.get("entries_total") is not None else " (total unknown)")),
        f"- messages matched: {bounds.get('messages_matched')}",
        f"- duplicates collapsed: {bounds.get('duplicates_collapsed')}",
        f"- truncated: {'yes' if bounds.get('truncated') else 'no'}", "",
    ]
    for blind in snapshot.get("blind") or []:
        lines.append(f"> BLIND: {blind}")
    if snapshot.get("blind"):
        lines.append("")
    for row in snapshot.get("messages") or []:
        lines.extend([
            f"## {row.get('ts') or 'time unknown'} — {row.get('frm') or '?'} → {row.get('to') or '?'} [{row.get('kind') or '?'}]",
            "",
            "Copies: " + ", ".join(f"`{c.get('stream')}@{c.get('id')}`" for c in row.get("copies") or []),
            "",
            str(row.get("content") or ""),
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def atom_payload(snapshot: Mapping[str, Any], *, title: str,
                 cites: Optional[Sequence[str]] = None, type_: str = "chronicle",
                 arc: Optional[str] = None) -> Dict[str, Any]:
    if not snapshot.get("found"):
        raise ValueError("cannot mint an atom from a thread that was not found")
    title = _text(title).strip()
    if not title:
        raise ValueError("capture --as-doc needs --title")
    speakers: List[str] = []
    for row in snapshot.get("messages") or []:
        who = _text(row.get("frm")).strip()
        if who and who not in speakers:
            speakers.append(who)
    citations = []
    for target in cites or []:
        target = _text(target).strip()
        if target and target not in {c["target"] for c in citations}:
            citations.append({"target": target, "rel": "discusses"})
    return {
        "type_": _text(type_).strip() or "chronicle",
        "title": title,
        "body": render_transcript(snapshot, title=title),
        "arc": arc,
        "seats": list(speakers),
        "categories": ["bus", "coordination"],
        "citations": citations,
        "status": "draft",
        "origin": "conversation",
        "speakers": list(speakers),
        "source_thread": _text(snapshot.get("thread_ref")),
        "settled": "live",
        "body_type": "transcript",
        "body_type_source": "flag",
        "gist": f"Verbatim Bifrost thread {_text(snapshot.get('thread_ref'))} with bounded archive provenance.",
    }


def mint_thread_atom(snapshot: Mapping[str, Any], *, title: str,
                     cites: Optional[Sequence[str]] = None, type_: str = "chronicle",
                     arc: Optional[str] = None, family: Any = None,
                     render_fn: Any = None, repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Mint through ``AtomFamily`` and return the atom/projection receipt."""
    root = str(repo_root or _ROOT)
    payload = atom_payload(snapshot, title=title, cites=cites, type_=type_, arc=arc)
    if family is None:
        from core.foundation.store import create_store
        from core.library.atoms import AtomFamily
        family = AtomFamily(create_store(), repo_root=root)
    if render_fn is None:
        from core.library.projection import render_atom
        render_fn = render_atom
    positional = {k: payload.pop(k) for k in ("type_", "title", "body")}
    atom = family.mint(positional["type_"], positional["title"], positional["body"], **payload)
    projection = render_fn(atom, repo_root=root)
    return {
        "atom_id": atom["id"],
        "projection": str(projection).replace("\\", "/"),
        "status": "draft",
        "source_thread": _text(snapshot.get("thread_ref")),
    }


def render_capture(snapshot: Mapping[str, Any]) -> str:
    bounds = snapshot.get("bounds") or {}
    lines = [
        f"# capture thread {snapshot.get('thread_ref')} for {snapshot.get('subject')}",
        (f"  {bounds.get('messages_matched')} message(s), {bounds.get('copies_matched')} copy/copies, "
         f"{bounds.get('duplicates_collapsed')} duplicate(s) collapsed | "
         f"streams {bounds.get('streams_read')}/{bounds.get('streams_total')} | "
         f"truncated={'yes' if bounds.get('truncated') else 'no'}"),
    ]
    for row in snapshot.get("messages") or []:
        lines.append(f"  {row.get('ts') or '?'}  {row.get('frm') or '?'} -> "
                     f"{row.get('to') or '?'} [{row.get('kind') or '?'}] "
                     f"{str(row.get('content') or '')[:120]}")
    for blind in snapshot.get("blind") or []:
        lines.append(f"  BLIND: {blind}")
    return "\n".join(lines)


__all__ = ["collect_thread", "atom_payload", "mint_thread_atom",
           "render_capture", "render_transcript"]
