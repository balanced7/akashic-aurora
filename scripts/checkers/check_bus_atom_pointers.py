#!/usr/bin/env python3
"""check_bus_atom_pointers.py -- the bus-side library lint (Daniel-gated 2026-07-24).

Born from a live leak: claude's atom-design round-2 counters rode the bus as a raw
design-shaped body with no durable home -- a lane the birth guard (mirror rule-13)
cannot see, because it only watches repo commits. The library law's spirit: any
position/design/report BODY longer than a pointer gets minted first (atom or note);
the bus carries the pointer, not the prose.

This checker PHOTOGRAPHS the gap (audit-domain posture: a lint row, never a send-time
block). A body is flagged when ALL hold:
  - its kind is conversational cargo (never trace/sig telemetry),
  - it is long (>= THRESHOLD chars),
  - it is design-shaped (markdown headings or heavy bullet structure),
  - it carries NO durable pointer (atom id, ADR note id, docs/library/ or research/ path).

Usage:
  py scripts/checkers/check_bus_atom_pointers.py --live [--per-stream 100]
  py scripts/checkers/check_bus_atom_pointers.py --self-test
Exit 0 = clean photograph; exit 1 = atomless bodies found (wrap/lint gateable).
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

THRESHOLD = 1500          # chars: below this a body is "a pointer with manners"
HEADING_MIN = 2           # markdown headings that make a body design-shaped
BULLET_MIN = 6            # or this many list items

# Durable-pointer roster: an atom id, a write-once note id, or a library/legacy path.
POINTER_RE = re.compile(
    r"\bart_\d{8}_[a-z0-9\-]+_[0-9a-f]{6}\b"
    r"|\bADR_\d{10}_[0-9a-f]{8}\b"
    r"|docs/library/[A-Za-z0-9_\-./]+"
    r"|research/[A-Za-z0-9_\-./]+\.md")
_HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s+\S", re.MULTILINE)

# Kinds that are telemetry or control -- never cargo that needs a library home.
SKIP_KINDS = {"trace", "halt", "interrupt", "pause", "resume", "nudge", "steer",
              "ledger_update", "presence", "heartbeat"}


def classify_body(text: str, kind: str = "") -> Optional[str]:
    """Return a flag-reason for an atomless design-shaped body, else None (clean)."""
    if not text or (kind or "").lower() in SKIP_KINDS:
        return None
    # Transport reality (founding-run find): stream envelopes carry newlines as literal
    # backslash-n escapes -- classify what the WIRE stores, or every line-anchored
    # heuristic reads a one-line body and the guard is blind by construction.
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    if len(text) < THRESHOLD:
        return None
    headings = len(_HEADING_RE.findall(text))
    bullets = len(_BULLET_RE.findall(text))
    if headings < HEADING_MIN and bullets < BULLET_MIN:
        return None                     # long prose, not a structured artifact
    if POINTER_RE.search(text):
        return None                     # carries its durable home
    return (f"design-shaped ({headings} heading(s), {bullets} bullet(s), "
            f"{len(text)} chars) with NO durable pointer")


def _body_of(fields: Dict[str, Any]) -> Tuple[str, str]:
    """(text, kind) from a stream envelope; field names vary across eras."""
    text = str(fields.get("text") or fields.get("content") or "")
    return text, str(fields.get("kind") or "")


def scan_live(per_stream: int = 100, hours: float = 0.0) -> List[str]:
    """Photograph recent messages on every non-telemetry stream in the namespace.
    hours > 0 bounds the window (stream ids are ms timestamps) -- the wrap-gate mode:
    history stays a one-time census; the gate judges only fresh sends."""
    import time as _time
    from core.comm.bus import get_bus
    bus = get_bus("claude")
    client, ns = bus._client, bus.ns
    min_id = f"{int((_time.time() - hours * 3600) * 1000)}-0" if hours > 0 else "-"
    rows: List[str] = []
    seen_keys: set = set()
    for key in client.scan_iter(match=f"{ns}:*", count=200):
        k = str(key)
        if k in seen_keys:
            continue
        seen_keys.add(k)
        if ":trace" in k or ":sig:" in k or "test" in k:
            continue
        try:
            if client.type(key) != "stream":
                continue
            entries = client.xrevrange(key, min=min_id, count=per_stream)
        except Exception:
            continue
        for mid, fields in entries:
            text, kind = _body_of(fields)
            reason = classify_body(text, kind)
            if reason:
                frm = fields.get("frm", "?")
                head = re.sub(r"\s+", " ", text)[:70]
                rows.append(f"[atomless] {k} {mid} frm={frm} kind={kind or '?'} -- {reason}\n"
                            f"           \"{head}...\"")
    return rows


def _self_test() -> int:
    """Inline sanity (the pytest pins are the real contract)."""
    long_doc = "# Plan\n" + "## Part\n" * 3 + ("word " * 400)
    assert classify_body(long_doc, "handoff")
    assert classify_body(long_doc + " art_20260724_x-y_abc123", "handoff") is None
    assert classify_body("short note", "handoff") is None
    assert classify_body(long_doc, "trace") is None
    print("self-test OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="scan the live namespace's streams")
    ap.add_argument("--per-stream", type=int, default=100)
    ap.add_argument("--hours", type=float, default=0.0,
                    help="only judge messages younger than this (wrap-gate mode); 0 = all history")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return _self_test()
    if not args.live:
        print("nothing to do: pass --live (or --self-test)")
        return 0
    rows = scan_live(args.per_stream, hours=args.hours)
    for r in rows:
        print(r)
    verdict = "CLEAN" if not rows else "ATOMLESS BODIES FOUND"
    print(f"[check_bus_atom_pointers] {verdict}: {len(rows)} row(s). "
          f"Law: mint first (doc new / note), the bus carries the pointer.")
    return 0 if not rows else 1


if __name__ == "__main__":
    sys.exit(main())
