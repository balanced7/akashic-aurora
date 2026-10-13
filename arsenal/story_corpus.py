"""Story corpus: the private cadence oracle that the piano page's live cadence judge is proven against.

    py -m arsenal.story_corpus oracle                     # every session (the default)
    py -m arsenal.story_corpus oracle --session <sid> ... # some sessions
    py -m arsenal.story_corpus oracle --out-dir <dir>     # somewhere else (default state/arsenal/story/oracle);
                                                          # inside the repo only under state/ (else exit 2)

For each practice session (state/arsenal/performance/<sid>/events.jsonl) it runs arsenal/practice.py exactly as the
practice verbs do (practice.load_session -> practice.analyze) and records, per session, one oracle file
(<out-dir>/<sid>.json, api arsenal.story.oracle/v1): the analysed chord windows with the fields practice._cadence
reads (root, pitch-class set and mask, bass, low bass, third, texture, key area), every cadence practice._cadence
finds between them BEFORE the deceptive-habit collapse (raw_cadences), and the collapsed list practice returns
(cadences). A manifest (<out-dir>/manifest.json) lists every session and the corpus totals. Every oracle file and
the manifest carry rules_sha (rules_sha(): the sha256 of the source of the practice rules judged), so a test can tell
an oracle built before a rule change from a fresh one.

It never forks or copies a rule of practice.py. The windows are captured by wrapping practice._findings for the
length of one analyze() call (the wrapper snapshots the rows' underscore fields, which analyze() strips afterwards,
asks practice._cadence itself for every n, then calls the original _findings and returns its answer unchanged); the
module attribute is restored afterwards, even on error.

PRIVATE OUTPUT: everything this module writes is derived from Daniel's playing. It goes under state/ (gitignored)
and nowhere else; never copy an oracle file, a count from it, or a progression from it into a tracked file. Tests
build their own synthetic sessions.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import inspect
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from arsenal import practice
from arsenal.performance import PerformanceStore

API = "arsenal.story.oracle/v1"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "state" / "arsenal" / "story" / "oracle"
PRIVATE_ROOT = ROOT / "state"
# the practice rules an oracle was judged by; rules_sha() fingerprints their source so a stale oracle is caught
RULES = ("_cadence", "_passing_moment", "_bass_dominant", "_chordal", "_rel")
RULE_CONSTANTS = ("CADENCE_GAP_MS", "CADENCE_ARRIVAL_MS", "DECEPTIVE_LEARNED")


def rules_sha() -> str:
    """sha256 of inspect.getsource of practice._cadence, _passing_moment, _bass_dominant, _chordal, _rel (that order),
    plus the module constants those rules read, so a changed threshold also marks the oracle stale."""
    src = "".join(inspect.getsource(getattr(practice, name)) for name in RULES)
    src += "".join(f"\n{name}={getattr(practice, name)!r}" for name in RULE_CONSTANTS)
    return hashlib.sha256(src.encode("utf-8")).hexdigest()


def refused_out_dir(out_dir: Path) -> Optional[str]:
    """Why out_dir may not hold private output (None when it may): inside the repo it must be under <repo>/state
    (gitignored); outside the repo it is the caller's own place."""
    target = Path(out_dir).resolve()
    root = ROOT.resolve()
    if target != root and root not in target.parents:
        return None
    private = PRIVATE_ROOT.resolve()
    if target == private or private in target.parents:
        return None
    return (f"refusing --out-dir {target}: the oracle is derived from private practice sessions and inside the repo "
            f"may only be written under {private} (gitignored); pick a folder there or outside the repo")


# ============================================================================================== capture
def _mask(pcs: Iterable[int]) -> int:
    m = 0
    for p in pcs:
        m |= 1 << (p % 12)
    return m


def oracle_body(rows: List[dict]) -> dict:
    """{areas, windows, raw_cadences} from analyze()'s rows while they still carry their underscore fields.
    Area ids follow the identity of the rows' _area dicts, in first-seen order (practice compares areas with 'is')."""
    area_ids: Dict[int, int] = {}
    areas: List[dict] = []
    windows: List[dict] = []
    for n, r in enumerate(rows):
        area = r["_area"]
        aid = None
        if area:
            aid = area_ids.get(id(area))
            if aid is None:
                aid = area_ids[id(area)] = len(areas)
                areas.append({"id": aid, "tonic": area["tonic"], "mode": area["mode"], "key": area["key"]})
        pcs = sorted({p % 12 for p in r["_pcs"]})
        windows.append({
            "n": n, "start_ms": r["start_ms"], "end_ms": r["end_ms"], "at": r["at"],
            "root_pc": r["_root_pc"], "pcs": pcs, "mask": _mask(pcs),
            "bass_pc": r["_bass_pc"], "low_bass": bool(r["_low_bass"]), "third": r["third"],
            "texture": r.get("texture", "chord"), "area": aid,
        })
    raw: List[dict] = []
    for n in range(1, len(rows)):
        cad = practice._cadence(rows, n)
        if cad:
            raw.append({"n": n, "kind": cad["kind"], "start_ms": cad["start_ms"], "end_ms": cad["end_ms"],
                        "key": cad["key"]})
    return {"areas": areas, "windows": windows, "raw_cadences": raw}


@contextlib.contextmanager
def capturing():
    """Wrap practice._findings for the duration: yields a dict that receives 'body' (oracle_body of the rows) for
    the analyze() call made inside the block. The original _findings runs and its answer is returned unchanged."""
    original = practice._findings
    seen: dict = {}

    def wrapper(rows, areas, ctx):
        seen["body"] = oracle_body(rows)  # before _findings, so nothing it adds to a row can leak in
        return original(rows, areas, ctx)

    practice._findings = wrapper
    try:
        yield seen
    finally:
        practice._findings = original


def _counts(body: dict, findings: dict) -> dict:
    sus = findings.get("suspensions") or []
    return {"windows": len(body["windows"]),
            "raw_cadence_kinds": dict(Counter(c["kind"] for c in body["raw_cadences"]).most_common()),
            "lydian_4": len(findings.get("lydian_4") or []),
            "suspensions": len(sus),
            "suspensions_resolved": sum(1 for s in sus if s.get("resolves"))}


def build_oracle(sid: str, body: dict, doc: dict) -> dict:
    findings = doc["findings"]
    return {"api": API, "sid": sid, "practice_api": practice.API, "rules_sha": rules_sha(),
            "areas": body["areas"], "windows": body["windows"], "raw_cadences": body["raw_cadences"],
            "cadences": findings["cadences"], "counts": _counts(body, findings)}


def oracle_from_events(events: List[dict], sid: str = "synthetic", end_ms: Optional[float] = None) -> Tuple[dict, dict]:
    """(oracle, doc) for an event list, through practice.analyze()."""
    with capturing() as seen:
        doc = practice.analyze(events, end_ms=end_ms)
    return build_oracle(sid, seen["body"], doc), doc


def oracle_for_session(store: PerformanceStore, sid: str) -> Tuple[dict, dict]:
    """(oracle, doc) for one stored session, through practice.load_session() as the practice verbs read it."""
    with capturing() as seen:
        sess = practice.load_session(store, sid)
    return build_oracle(sid, seen["body"], sess["doc"]), sess["doc"]


def has_notes(store: PerformanceStore, sid: str) -> bool:
    events, _ = practice.read_events(store, sid)
    return any(e.get("kind") == "on" for e in events)


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, indent=1, ensure_ascii=False, default=str))
        fh.write("\n")
    tmp.replace(path)


def run_oracle(sids: List[str], out_dir: Path, store: Optional[PerformanceStore] = None) -> dict:
    """Write <out_dir>/<sid>.json for each session with notes, and <out_dir>/manifest.json. Returns the manifest."""
    store = store or PerformanceStore()
    out_dir = Path(out_dir)
    t0 = time.time()
    sessions: Dict[str, dict] = {}
    skipped: List[str] = []
    failed: Dict[str, str] = {}
    kinds: Counter = Counter()
    seconds = 0.0
    windows = 0
    for sid in sids:
        try:
            if not has_notes(store, sid):
                skipped.append(sid)
                continue
            oracle, doc = oracle_for_session(store, sid)
        except Exception as exc:  # one broken session never hides the rest; it is named in the manifest
            failed[sid] = f"{type(exc).__name__}: {exc}"[:300]
            continue
        _write_json(out_dir / f"{sid}.json", oracle)
        c = oracle["counts"]
        sessions[sid] = {"seconds": doc.get("duration_s"), "windows": c["windows"],
                         "raw_cadences": len(oracle["raw_cadences"]), "cadences": len(oracle["cadences"]),
                         "raw_cadence_kinds": c["raw_cadence_kinds"]}
        kinds.update(c["raw_cadence_kinds"])
        seconds += doc.get("duration_s") or 0
        windows += c["windows"]
    manifest = {
        "api": API, "practice_api": practice.API, "rules_sha": rules_sha(), "elapsed_s": round(time.time() - t0, 1),
        "sessions": sessions, "skipped_no_notes": skipped, "failed": failed,
        "totals": {"sessions": len(sessions), "seconds": round(seconds, 1), "windows": windows,
                   "raw_cadences": sum(kinds.values()), "raw_cadence_kinds": dict(kinds.most_common())},
    }
    _write_json(out_dir / "manifest.json", manifest)
    return manifest


def all_sessions(store: PerformanceStore) -> List[str]:
    root = Path(store.root)
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "events.jsonl").is_file())


def summary_text(manifest: dict, out_dir: Path) -> str:
    t = manifest["totals"]
    lines = [f"oracle: {t['sessions']} sessions ({len(manifest['skipped_no_notes'])} without notes skipped, "
             f"{len(manifest['failed'])} failed), {t['seconds']} s of playing, {t['windows']} windows, "
             f"{manifest['elapsed_s']} s elapsed -> {out_dir}",
             f"raw cadences: {t['raw_cadences']}"]
    for kind, count in t["raw_cadence_kinds"].items():
        lines.append(f"  {count:6d}  {kind}")
    for sid, why in manifest["failed"].items():
        lines.append(f"FAILED {sid}: {why}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m arsenal.story_corpus", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="verb", required=True)
    o = sub.add_parser("oracle", help="write the private cadence oracle (one JSON per session + manifest.json)")
    which = o.add_mutually_exclusive_group()
    which.add_argument("--all", action="store_true", help="every session (the default)")
    which.add_argument("--session", nargs="+", metavar="SID", help="only these sessions")
    o.add_argument("--out-dir", default=str(DEFAULT_OUT), help=f"where to write (default {DEFAULT_OUT})")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    why = refused_out_dir(out_dir)
    if why:
        print(why, file=sys.stderr)
        return 2
    store = PerformanceStore()
    sids = args.session or all_sessions(store)
    manifest = run_oracle(sids, out_dir, store)
    print(summary_text(manifest, out_dir))
    return 1 if manifest["failed"] and not manifest["sessions"] else 0


if __name__ == "__main__":
    sys.exit(main())
