"""archive_transcripts.py -- the durable copy of the plane git does not protect.

Git protects the code. snapshot_knowledge.py protects the Store and the curated chronicles.
NOTHING protected the session transcripts, and they are where the operator's voice actually
lives -- the raw record of what was asked, argued and decided.

    py scripts/ops/archive_transcripts.py              # copy to every default destination
    py scripts/ops/archive_transcripts.py --verify     # + hash every archived copy (deep)
    py scripts/ops/archive_transcripts.py --status     # what the last run did, no copying

WHY (2026-08-11): the harness rotates transcripts off disk silently. THE EYE's index was
wiped by a schema migration written on the belief that it was "a projection, rebuildable
from source", and events whose source had already rotated away were destroyed -- then
recovered from a Windows shadow copy with hours to spare before it would have been pruned.

THREE LAWS, each earned that day:

1. ADDITIVE-ONLY. This tool has no delete path. A sync that MIRRORS the source would remove
   the archived copy the instant a transcript rotates off disk -- the same disaster, on a
   schedule, unattended. `robocopy /MIR` at this job would be worse than no backup. What
   the source forgot is precisely what the archive is for.

2. REFUSE A SHRINKING SOURCE. Transcripts are append-only, so bigger is always better. A
   source smaller than its archived copy means truncation upstream, never an update. Keep
   the good copy, and say so loudly. A backup that faithfully replicates corruption destroys
   the last good copy on the day it matters.

3. BE LOUD. Every run leaves a dated receipt and exits non-zero on any refusal, failure or
   unreachable destination -- a scheduler only ever sees the exit code, and this house
   already owns the lesson `backup_door_never_ran`, about a backup door that had never once
   succeeded while memory called it proven. A silent backup manufactures confidence.

Destinations are separate PHYSICAL disks on purpose (C: source, E:, F:) -- two copies on one
drive is one failure domain wearing a disguise.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]

# Deliberately OUTSIDE the repo: these are UNREDACTED transcripts and the repo is public.
DEFAULT_DESTS: List[Path] = [
    Path(r"E:\Akashic Aurora\transcripts\rolling"),
    Path(r"F:\Akashic Aurora\transcripts\rolling"),
]
DEFAULT_RECEIPTS = _REPO_ROOT / "state" / "archive" / "receipts"

# A path no filesystem will give us, for the unreachable-destination pin. Named rather than
# improvised so the pin cannot accidentally test a path that later becomes creatable.
UNREACHABLE_PROBE = Path("\x00::unreachable::")

_SUBAGENT_MARKERS = ("subagents", "workflows")


def source_transcripts(root: Optional[Path] = None,
                       include_subagents: bool = False) -> Tuple[List[Path], int]:
    """The transcripts to archive, and HOW MANY WERE EXCLUDED.

    Returns the excluded count rather than swallowing it: a denominator that is itself a
    filter has to declare what it filtered, or "94 archived" quietly means something other
    than what the reader assumes. (The coverage lesson THE EYE paid for, applied here.)

    Top-level session transcripts are the operator's voice. Subagent and workflow
    transcripts nested under <session>/subagents/... are agent-to-agent working records --
    excluded by default, included on request, never silently dropped."""
    root = Path(root) if root else (Path.home() / ".claude" / "projects")
    if not root.is_dir():
        return [], 0
    picked: List[Path] = []
    excluded = 0
    for p in sorted(root.rglob("*.jsonl")):
        rel = p.relative_to(root).parts
        is_sub = len(rel) > 2 or any(m in rel for m in _SUBAGENT_MARKERS)
        if is_sub and not include_subagents:
            excluded += 1
            continue
        picked.append(p)
    return picked, excluded


def _sha256(p: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _copy_verified(src: Path, dst: Path) -> bool:
    """Copy and prove it. A copy nobody read back is not a copy."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".part")
    shutil.copy2(str(src), str(tmp))
    ok = _sha256(tmp) == _sha256(src)
    if ok:
        os.replace(str(tmp), str(dst))     # atomic: no half-written file is ever visible
    else:
        tmp.unlink(missing_ok=True)
    return ok


def _archive_one_dest(sources: List[Path], dest: Path, verify: bool,
                      rel_root: Optional[Path] = None) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"path": str(dest), "reachable": False, "copied": 0,
                           "skipped": 0, "repaired": 0, "deleted": 0, "bytes_copied": 0,
                           "refused": [], "failed": [], "present_total": 0}
    try:
        dest.mkdir(parents=True, exist_ok=True)
        rec["reachable"] = True
    except Exception as e:
        rec["failed"].append(f"destination unreachable: {e.__class__.__name__}: {e}")
        return rec

    for src in sources:
        # Flattening by basename is safe ONLY when names are globally unique (session
        # transcripts are UUIDs). It is NOT safe for sharded planes: the wire journal keeps
        # per-agent shards, so state/wire/deepseek/wire-20260804-001.jsonl and
        # state/wire/deepseek-red/wire-20260804-001.jsonl collide on the way in. Caught on
        # the first live run by the refuse-shrinking law, which declined the overwrite and
        # kept the first shard rather than silently destroying five agents' forensics --
        # the safety law catching a bug in the tool that carries it. Pass rel_root to keep
        # the source's own shape.
        try:
            target = (dest / src.relative_to(rel_root)) if rel_root else (dest / src.name)
        except ValueError:
            target = dest / src.name       # outside rel_root: fall back, never crash
        try:
            s_size = src.stat().st_size
            if target.exists():
                d_size = target.stat().st_size
                if s_size < d_size:
                    # LAW 2. Append-only means this cannot be a legitimate update.
                    rec["refused"].append(
                        f"{src.name}: source {s_size:,}B is SMALLER than archived "
                        f"{d_size:,}B -- kept the archived copy (upstream truncation?)")
                    continue
                if s_size == d_size:
                    if not verify or _sha256(target) == _sha256(src):
                        rec["skipped"] += 1
                        continue
                    # same size, different bytes: rot, or a same-length rewrite
                    if _copy_verified(src, target):
                        rec["repaired"] += 1
                        rec["bytes_copied"] += s_size
                    else:
                        rec["failed"].append(f"{src.name}: verification failed on repair")
                    continue
            if _copy_verified(src, target):
                rec["copied"] += 1
                rec["bytes_copied"] += s_size
            else:
                rec["failed"].append(f"{src.name}: hash mismatch after copy")
        except Exception as e:
            rec["failed"].append(f"{src.name}: {e.__class__.__name__}: {e}")

    # LAW 1: nothing here removes files. The count is reported so the pin can assert on it
    # and so a reader never has to infer the absence of a delete path from silence.
    rec["deleted"] = 0
    try:
        rec["present_total"] = sum(1 for _ in dest.rglob("*") if _.is_file())
    except Exception:
        pass
    return rec


def archive(sources: List[Path], dests: Optional[List[Path]] = None, *,
            verify: bool = False, receipt_dir: Optional[Path] = None,
            excluded: int = 0, rel_root: Optional[Path] = None) -> Dict[str, Any]:
    """Copy every source into every destination, additively. Returns the report.

    Destinations are independent: two drives exist so that one can die, so an unreachable
    one is recorded and stepped over, never allowed to abort the copy to the live one."""
    dests = list(dests if dests is not None else DEFAULT_DESTS)
    started = time.time()
    per_dest = [_archive_one_dest(sources, Path(d), verify, rel_root) for d in dests]
    ok = all(d["reachable"] and not d["refused"] and not d["failed"] for d in per_dest)
    report = {
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(time.time() - started, 2),
        "sources_seen": len(sources),
        "sources_excluded": excluded,
        "verify": bool(verify),
        "destinations": per_dest,
        "ok": ok,
    }
    rdir = Path(receipt_dir) if receipt_dir is not None else DEFAULT_RECEIPTS
    if receipt_dir is None and os.getenv("PYTEST_CURRENT_TEST"):
        # A test run must never overwrite the PRODUCTION receipt. Found live: the suite
        # wrote its tmp_path destinations into state/archive/receipts/latest.json, so
        # `--status` -- the operator's only window onto whether the backup is healthy --
        # reported a pytest fixture as the last real run. A monitoring surface showing test
        # data as production is worse than one that shows nothing.
        rdir = Path(os.getenv("TEMP", ".")) / "akashic-archive-receipts-test"
    try:
        rdir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        (rdir / f"archive-{stamp}.json").write_text(
            json.dumps(report, indent=1), encoding="utf-8")
        (rdir / "latest.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    except Exception as e:
        report["receipt_error"] = f"{e.__class__.__name__}: {e}"
        report["ok"] = False      # an unrecorded run is indistinguishable from no run
    return report


def _render(rep: Dict[str, Any]) -> None:
    print(f"[archive] {rep['sources_seen']} transcript(s) seen"
          + (f", {rep['sources_excluded']} subagent transcript(s) excluded"
             if rep["sources_excluded"] else "")
          + f" | {rep['elapsed_s']}s"
          + ("  [VERIFY]" if rep["verify"] else ""))
    for d in rep["destinations"]:
        if not d["reachable"]:
            print(f"  [UNREACHABLE] {d['path']}")
            for f in d["failed"]:
                print(f"      {f}")
            continue
        print(f"  {d['path']}: +{d['copied']} copied, {d['skipped']} unchanged"
              + (f", {d['repaired']} REPAIRED" if d["repaired"] else "")
              + f", {d['present_total']} held"
              + (f", {d['bytes_copied']:,} bytes" if d["bytes_copied"] else ""))
        for r in d["refused"]:
            print(f"      [REFUSED] {r}")
        for f in d["failed"]:
            print(f"      [FAILED] {f}")
    print("[archive] OK" if rep["ok"] else "[archive] NOT CLEAN -- see above")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source-dir", default="", help="transcript root (default: the "
                                                     "harness projects dir)")
    ap.add_argument("--dest", action="append", default=[],
                    help="destination (repeatable; default: E: and F: archives)")
    ap.add_argument("--receipt-dir", default="", help="where receipts land")
    ap.add_argument("--verify", action="store_true",
                    help="hash every archived copy, not just the size-changed ones "
                         "(catches silent rot; slower)")
    ap.add_argument("--include-subagents", action="store_true",
                    help="also archive subagent/workflow transcripts")
    ap.add_argument("--status", action="store_true",
                    help="print the last receipt and exit; copies nothing")
    a = ap.parse_args(argv)

    rdir = Path(a.receipt_dir) if a.receipt_dir else DEFAULT_RECEIPTS
    if a.status:
        latest = rdir / "latest.json"
        if not latest.exists():
            print("[archive] NEVER RUN -- no receipt on record", file=sys.stderr)
            return 1
        rep = json.loads(latest.read_text(encoding="utf-8"))
        age_h = (datetime.now(timezone.utc)
                 - datetime.fromisoformat(rep["ran_at"])).total_seconds() / 3600.0
        print(f"[archive] last run {age_h:.1f}h ago")
        _render(rep)
        return 0 if rep.get("ok") else 1

    sources, excluded = source_transcripts(
        Path(a.source_dir) if a.source_dir else None, a.include_subagents)
    if not sources:
        print("[archive] NO TRANSCRIPTS FOUND -- refusing to record a clean run over an "
              "empty source (an empty backup that reports OK is the failure mode this "
              "tool exists to prevent)", file=sys.stderr)
        return 1
    rep = archive(sources, [Path(d) for d in a.dest] or None,
                  verify=a.verify, receipt_dir=rdir, excluded=excluded)
    _render(rep)
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
