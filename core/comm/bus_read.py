"""bus_read -- one message, by id, in full: the exception path behind every clipped preview.

WHY THIS EXISTS (2026-10-30 wish, phase 3 of the modular-core detangle): "plus `bus read <id>`",
filed next to "the WOKE BY preview is clipped". The preview is clipped because it is rendered
where it belongs (a status line), but a message id is a POINTER, and until now this house had no
way to follow one from a shell -- an agent holding "woke by 1793405184749-0" had to write a
python one-liner and guess which stream the packet landed on.

THE HARD PART IS NAMING THE STREAM, and it is worth being explicit about it: a Redis stream id is
unique only WITHIN its stream, so "read message 1793405184749-0" is not a well-formed question
until you say which streams to look in. This module answers it the only honest way -- it searches
every stream under the namespace that can CARRY a message (per-agent inboxes, per-seat inboxes,
the per-agent work/sig lane inboxes, and the broadcast streams), and when more than one stream
holds that id it says so and shows the caller how to disambiguate (`--stream KEY`) instead of
picking one. Silent disambiguation would be a wrong answer that looks like a right one.

READ-ONLY BY CONSTRUCTION: XRANGE and SCAN only. There is no cursor here to advance -- reading a
message by id is an inspection, and an inspection that changed the room would be a consume
wearing a read's clothes.

PROVENANCE IS PART OF THE MESSAGE NOW (phase 3, slice 5): each record carries `origin` from
`meta.origin` when the producing door stamped one, and "unknown" otherwise. It is NEVER guessed
from the sender's name -- "did this come from Discord?" answered by inference is exactly the
gateway-log archaeology this field exists to end.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

#: Stream-name shapes under the namespace that can carry a message. A FUNCTION rather than one
#: regex or a loose substring list, because the first draft used ":bc" as a marker and matched
#: every mailbox hash whose digest happened to contain those two characters.
def _is_carrier(key: str) -> bool:
    k = str(key)
    if ":inbox:" in k:
        return True
    if k.endswith(":broadcast") or k.endswith(":bc"):
        return True
    return False


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _client():
    try:
        from core.comm.bus import get_bus
        b = get_bus("control")
        if b is None or not b.online:
            return None
        return b._client
    except Exception:
        return None


def _decode(fields) -> Dict[str, str]:
    pairs = fields.items() if hasattr(fields, "items") else fields
    out = {}
    for k, v in pairs:
        kk = k.decode() if isinstance(k, bytes) else k
        vv = v.decode("utf-8", "replace") if isinstance(v, bytes) else v
        out[str(kk)] = vv
    return out


def candidate_streams(agent: Optional[str] = None, limit: int = 20000) -> List[str]:
    """Every stream under the namespace that can carry a message, or None-ish on a scan failure.

    `agent` narrows to that agent's own streams (its inbox, its seat inboxes, its lane inboxes,
    the broadcast channels) -- the fast path when the caller already knows who was addressed."""
    cli = _client()
    if cli is None:
        return []
    ns = _ns()
    if agent:
        keys = [f"{ns}:inbox:{agent}", f"{ns}:broadcast", f"{ns}:work:inbox:{agent}",
                f"{ns}:sig:inbox:{agent}", f"{ns}:work:broadcast", f"{ns}:sig:broadcast"]
        return keys
    out: List[str] = []
    try:
        for key in cli.scan_iter(match=f"{ns}:*", count=500):
            k = key.decode() if isinstance(key, bytes) else str(key)
            if _is_carrier(k):
                out.append(k)
            if len(out) >= limit:
                break
    except Exception:
        return []
    return out


def find_message(msg_id: str, *, agent: Optional[str] = None,
                 stream: Optional[str] = None) -> Dict[str, Any]:
    """The message with `msg_id`, plus the streams that hold it. Never raises.

    Returns {"found": bool, "record": {...} | None, "streams": [keys holding it],
             "searched": n, "why": str}
    """
    want = str(msg_id or "").strip()
    if not want:
        return {"found": False, "record": None, "streams": [], "searched": 0,
                "why": "no message id given"}
    cli = _client()
    if cli is None:
        return {"found": False, "record": None, "streams": [], "searched": 0,
                "why": "the bus is offline (Redis unreachable), so no stream can be read"}
    keys = [stream] if stream else candidate_streams(agent)
    hits: List[str] = []
    record = None
    for key in keys:
        try:
            rows = cli.xrange(key, min=want, max=want)
        except Exception:
            continue
        if not rows:
            continue
        hits.append(key)
        if record is None:
            sid, fields = rows[0]
            f = _decode(fields)
            record = {"id": str(sid), "stream": key,
                      "frm": f.get("frm", ""), "to": f.get("to", ""),
                      "kind": f.get("kind", ""), "ts": f.get("ts", ""),
                      "sha": f.get("sha", ""),
                      "content": _jsonish(f.get("content")),
                      "parts": _jsonish(f.get("parts")),
                      "meta": _jsonish(f.get("meta")) or {},
                      "raw": f}
            record["origin"] = _origin(record["meta"])
    if not hits:
        return {"found": False, "record": None, "streams": [], "searched": len(keys),
                "why": (f"no stream under '{_ns()}' holds id {want}. An id is unique only WITHIN "
                        f"its stream, so this search covered {len(keys)} carrier stream(s); if "
                        f"you know the stream pass --stream, and if the message was never on the "
                        f"bus look in the durable planes (`events --get {want}`)")}
    return {"found": True, "record": record, "streams": hits, "searched": len(keys), "why": ""}


def _origin(meta: Any) -> str:
    """Where the message came FROM, as stamped by the door that created it. Never inferred."""
    if isinstance(meta, dict):
        origin = meta.get("origin")
        if isinstance(origin, str) and origin.strip():
            return origin.strip()
    return "unknown"


def _jsonish(value):
    if value is None:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def render(found: Dict[str, Any]) -> str:
    if not found.get("found"):
        return f"bus read: NOT FOUND -- {found.get('why', '')}"
    rec = found["record"] or {}
    meta = rec.get("meta") or {}
    lines = [f"bus message {rec.get('id')}  (in {rec.get('stream')})",
             f"  from:       {rec.get('frm')}",
             f"  to:         {rec.get('to')}",
             f"  kind:       {rec.get('kind')}",
             f"  ts:         {rec.get('ts')}",
             f"  provenance: {rec.get('origin')}"
             + ("" if rec.get("origin") != "unknown" else
                "  (this message predates provenance stamping, or its door did not stamp one)")]
    if rec.get("sha"):
        lines.append(f"  sha:        {rec['sha']}")
    if meta:
        keep = {k: v for k, v in meta.items() if k not in ("origin",)}
        if keep:
            lines.append("  meta:       " + json.dumps(keep, ensure_ascii=False, default=str))
    parts = rec.get("parts")
    if parts:
        lines.append(f"  parts:      {json.dumps(parts, ensure_ascii=False, default=str)[:400]}")
    body = rec.get("content")
    if isinstance(body, (dict, list)):
        body = json.dumps(body, ensure_ascii=False, indent=2, default=str)
    lines.append("  content:")
    for ln in str(body if body is not None else "").splitlines() or [""]:
        lines.append("    " + ln)
    others = [s for s in (found.get("streams") or []) if s != rec.get("stream")]
    if others:
        lines.append(f"  ALSO held by {len(others)} other stream(s) (same id, dual-write or "
                     f"mirror): {', '.join(others)}")
    lines.append(f"  (searched {found.get('searched')} carrier stream(s); read-only -- nothing "
                 f"consumed, no cursor moved)")
    return "\n".join(lines)
