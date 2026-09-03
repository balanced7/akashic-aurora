"""archive_ephemeral.py -- export the ephemeral planes, then archive them.

The transcript archive covered the operator's voice. This covers what was still
disappearing after it:

    py scripts/ops/archive_ephemeral.py                 # export the bus + archive state
    py scripts/ops/archive_ephemeral.py --search "..."  # read the exported bus back
    py scripts/ops/archive_ephemeral.py --status        # last run, no work

WHAT WAS EPHEMERAL, measured 2026-08-11:

  THE BUS. Streams are bounded transport BY DESIGN (bus.DEFAULT_MAXLEN=10_000); live
  retention measured ~3 days. Salient kinds are already promoted to the durable event log
  at send time (bus.py:593) -- but `chat`, `fyi` and `trace` are not, and that is where a
  peer's full diagnosis, a frontier agent's report and every narration actually live. The
  house covered this with manual discipline (`research_full_fidelity_preservation`:
  "persist frontier agents' FULL reports ... chat is disposable"). A rule that relies on
  someone remembering is not a mechanism; this is the mechanism.

  LOCAL-ONLY FILE PLANES. `session_logs/` (learnings.jsonl + store state), `state/spill/`
  (clipped note and handoff bodies -- 37 DURABLE records point into it BY PATH, so a
  durable record was depending on an unbacked-up file), `state/wire/` (API forensics).

THE COPY LAWS ARE NOT REIMPLEMENTED HERE. `archive` is imported verbatim from
archive_transcripts: additive-only (no delete path), refuse a shrinking source, SHA256
every copy, dated receipt, non-zero exit when anything is off. A second implementation of a
safety law is a second thing that can be wrong.

What IS new is the EXPORT. A Redis stream is not a file until someone writes it down, and
the export is incremental (per-stream last-id cursor) and APPEND-ONLY, so an entry the bus
has since trimmed stays readable forever. That is the whole point.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from scripts.ops.archive_transcripts import (  # noqa: E402
    DEFAULT_DESTS as _T_DESTS, archive, _render as _render_copy)

# The engine, re-exported so callers (and the pins) can see it is the SAME one.
archive = archive

BUS_EXPORT_DIR = _REPO_ROOT / "state" / "bus-export"
DEFAULT_CURSORS = BUS_EXPORT_DIR / ".cursors.json"
DEFAULT_RECEIPTS = _REPO_ROOT / "state" / "archive" / "receipts-ephemeral"
DEFAULT_DESTS: List[Path] = [
    Path(r"E:\Akashic Aurora\ephemeral"),
    Path(r"F:\Akashic Aurora\ephemeral"),
]

# Planes worth keeping, and the extensions that are the RECORD rather than scratch.
STATE_PLANES: Dict[str, Tuple[str, ...]] = {
    "state/spill": (".txt", ".md", ".json", ".jsonl"),
    "state/wire": (".jsonl", ".json"),
    "state/bus-export": (".jsonl",),
    "session_logs": (".jsonl",),
}
_SKIP_SUFFIXES = (".tmp", ".part", ".lock", ".pyc")


def _safe_name(stream: str) -> str:
    """Map a stream name to a filename that Windows will actually accept.

    2026-09-02: a literal stream `bifrost:inbox:*` (minted by a `to:"*"` send)
    crashed the WHOLE bus export for 5 days -- OSError EINVAL on `*` -- because
    this only stripped `:` and `/`. Harden the MEANING (any char invalid in a
    Windows filename), not the two characters we had met so far.
    """
    for ch in ':/\\*?"<>|':
        stream = stream.replace(ch, "_")
    return stream


def export_bus(client, out_dir: Path, cursor_file: Optional[Path] = None) -> Dict[str, Any]:
    """Write every stream's NEW entries to `<stream>.jsonl`, resuming from a per-stream
    cursor. Append-only: an entry the bus later trims stays in the file.

    The payload is kept WHOLE. A summarising exporter would make the archive a worse copy
    of the thing it is protecting, which is the failure mode the pyramid slice spent a
    fence round on."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cur_path = Path(cursor_file) if cursor_file else DEFAULT_CURSORS
    try:
        cursors = json.loads(cur_path.read_text(encoding="utf-8"))
    except Exception:
        cursors = {}

    streams, written = 0, 0
    failed_streams: list = []
    for key in sorted(client.scan_iter(match="*", count=3000)):
        try:
            if client.type(key) != "stream":
                continue
        except Exception:
            continue
        streams += 1
        # ONE stream's failure must never zero the whole plane. The 2026-09-02
        # incident: an unexportable stream name raised past this loop, aborting
        # every remaining stream AND the cursor save -- 5 days of bus history
        # silently unarchived while file archiving kept reporting green. A bad
        # stream is now a loud line in the report, and the loop continues.
        try:
            last = cursors.get(key)
            rows = client.xrange(key, min=(f"({last}" if last else "-"))
            if not rows:
                continue
            path = out_dir / f"{_safe_name(key)}.jsonl"
            with open(path, "a", encoding="utf-8") as fh:
                for mid, fields in rows:
                    fh.write(json.dumps({
                        "stream": key, "id": mid,
                        "exported_at": datetime.now(timezone.utc).isoformat(),
                        "fields": dict(fields),
                    }, ensure_ascii=False) + "\n")
                    written += 1
                    cursors[key] = mid
        except Exception as exc:  # noqa: BLE001 -- contained + confessed, never silent
            failed_streams.append({"stream": key, "error": f"{type(exc).__name__}: {exc}"})
    cur_path.parent.mkdir(parents=True, exist_ok=True)
    cur_path.write_text(json.dumps(cursors, indent=1), encoding="utf-8")
    report: Dict[str, Any] = {
        "streams": streams, "entries_written": written, "out_dir": str(out_dir),
    }
    if failed_streams:
        # surfacing in the receipt keeps the deadman honest: a partial export is
        # a FINDING, not a success and not an abort.
        report["failed_streams"] = failed_streams
    return report


def _sender(fields: Dict[str, Any]) -> str:
    """Who sent it. `frm` is the bifrost envelope's field; the others are the shapes the
    events streams and older records use. Checked against the live export, not assumed."""
    for k in ("frm", "from", "agent", "by", "from_agent"):
        v = fields.get(k)
        if v:
            return str(v)
    return ""


def search(out_dir: Path, *, q: str = "", who: str = "", kind: str = "",
           limit: int = 20) -> List[Dict[str, Any]]:
    """Read the exported bus back. Facets AND together; `q` is a substring within the
    faceted slice -- the query grammar's shape, at the cheapest door that can honour it.

    Saved without findable is a tarball, which is why this ships in the same slice."""
    hits: List[Dict[str, Any]] = []
    for f in sorted(Path(out_dir).glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            fields = rec.get("fields") or {}
            # The wire field is `frm`, NOT `from` -- verified against the live export.
            # v1 read `from` and returned silent-empty on every real record, because the
            # fixture supplied its own field name and so tested the mechanism rather than
            # the wiring (a_pin_that_supplies_its_own_input_tests_the_mechanism_not_the_
            # wiring). Alternatives are accepted because the events streams use a different
            # envelope from the bifrost ones.
            if who and str(_sender(fields)) != who:
                continue
            if kind and str(fields.get("kind", "")) != kind:
                continue
            if q and q.lower() not in json.dumps(fields, ensure_ascii=False).lower():
                continue
            hits.append(rec)
            if len(hits) >= limit:
                return hits
    return hits


def collect_state(root: Optional[Path] = None) -> Tuple[List[Path], Dict[str, int]]:
    """The files to archive, and a PER-PLANE count. The count rides the report because an
    archive that cannot say what it covered is how a plane goes quietly uncovered."""
    root = Path(root) if root else _REPO_ROOT
    files: List[Path] = []
    planes: Dict[str, int] = {}
    for plane, exts in STATE_PLANES.items():
        d = root / plane
        planes[plane] = 0
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if not p.is_file() or p.suffix in _SKIP_SUFFIXES:
                continue
            if exts and p.suffix not in exts:
                continue
            files.append(p)
            planes[plane] += 1
    return files, planes


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dest", action="append", default=[])
    ap.add_argument("--receipt-dir", default="")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--search", default="", metavar="TEXT")
    ap.add_argument("--who", default="")
    ap.add_argument("--kind", default="")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args(argv)

    rdir = Path(a.receipt_dir) if a.receipt_dir else DEFAULT_RECEIPTS

    if a.search or a.who or a.kind:
        hits = search(BUS_EXPORT_DIR, q=a.search, who=a.who, kind=a.kind)
        if not hits:
            print("[bus] no match in the export "
                  "(run without --search first if it has never been exported)")
            return 1
        for h in hits:
            f = h["fields"]
            body = str(f.get("content") or f.get("data", ""))[:150].replace("\n", " ")
            print(f"  [{f.get('kind','?')}] {_sender(f) or '?'} -> {f.get('to','*')}  "
                  f"{h['id']}\n      {body}")
        print(f"[bus] {len(hits)} hit(s) from the durable export")
        return 0

    if a.status:
        latest = rdir / "latest.json"
        if not latest.exists():
            print("[ephemeral] NEVER RUN -- no receipt on record", file=sys.stderr)
            return 1
        rep = json.loads(latest.read_text(encoding="utf-8"))
        print(f"[ephemeral] last run {rep['ran_at']}")
        _render_copy(rep)
        return 0 if rep.get("ok") else 1

    # 1) export the bus so it is a file at all
    bus = {"streams": 0, "entries_written": 0, "error": None}
    try:
        import redis
        # Bounded on purpose: an unresponsive Redis must fail this step in seconds, not
        # hang a scheduled task. The file archiving below does not depend on it.
        client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"),
                             port=int(os.getenv("REDIS_PORT", "16379")),
                             decode_responses=True,
                             socket_timeout=5, socket_connect_timeout=5)
        client.ping()
        bus = export_bus(client, BUS_EXPORT_DIR)
    except Exception as e:
        bus["error"] = f"{e.__class__.__name__}: {e}"
    if bus.get("error"):
        # Loud, and NOT fatal to the file archiving -- a down Redis must not cost the
        # spill/learnings copy, the same independence the two drives get.
        print(f"[bus] EXPORT FAILED: {bus['error']}", file=sys.stderr)
    else:
        print(f"[bus] {bus['streams']} stream(s), +{bus['entries_written']:,} entry(s) "
              f"exported -> {BUS_EXPORT_DIR}")

    # 2) archive every state plane (bus export included) with the proven engine
    files, planes = collect_state()
    if not files:
        print("[ephemeral] NO STATE FILES FOUND -- refusing to record a clean run over "
              "nothing", file=sys.stderr)
        return 1
    print("[ephemeral] planes: " + ", ".join(f"{k}={v}" for k, v in planes.items()))
    # rel_root keeps each plane's own shape in the archive. The wire journal is sharded
    # per agent, so flattening by basename collides five agents' shards onto one name.
    rep = archive(files, [Path(d) for d in a.dest] or DEFAULT_DESTS,
                  verify=a.verify, receipt_dir=rdir, rel_root=_REPO_ROOT)
    rep["bus_export"] = bus
    rep["planes"] = planes
    _render_copy(rep)
    try:
        (rdir / "latest.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    except Exception:
        pass
    return 0 if (rep["ok"] and not bus.get("error")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
