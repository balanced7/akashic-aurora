"""present door:
    py -m arsenal.present check <scene.json> [--json]
    py -m arsenal.present targets [--scene X] [--json]
    py -m arsenal.present render <scene.json> --to slides|ui|pdf|3d [--out DIR] [--width N] [--slide ID]
                                 [--no-footnotes] [--autoplay] [--verify-cdn] [--allow-drops] [--dry]

`present` is NOT an agent_cli verb today (measured 2026-09-28: not among the 107 parser verbs),
and arsenal's own entry points (roll, performance, score_cli) are reached as `py -m arsenal ...`,
not as agent_cli doors, so this module is the family's door in the same shape. It may import
arsenal.registry (it is a door, not a primitive); scene.py may not.

A render refuses a scene the validator refuses (exit 1), prints lint warnings as notes, refuses
a target whose manifest covers none of preserves/degrades/drops for a kind the deck uses (I6),
and refuses -- unless --allow-drops -- a target that only DROPS a kind the deck uses. Every run
writes a take: <out>/takes/<timestamp>-<target>.json with the scene's sha256, the module id and
version, the files written, and per slide what was preserved, degraded and dropped. --dry
prints that table and executes nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

from . import scene as scene_mod


def _cmd_check(args) -> int:
    scene = scene_mod.load(args.scene)
    refusals = scene_mod.validate(scene)
    warnings = scene_mod.lint(scene) if not refusals else []
    if args.json:
        print(json.dumps({"schema": scene.get("schema"), "slides": len(scene.get("slides") or []),
                          "refusals": refusals, "warnings": warnings}, indent=1))
    else:
        for line in refusals:
            print(f"REFUSED {line}")
        for line in warnings:
            print(f"note: {line}")
        n = len(scene.get("slides") or [])
        print(f"{'REFUSED' if refusals else 'ok'}: {n} slide(s), {len(refusals)} refusal(s), {len(warnings)} warning(s)")
    return 1 if refusals else 0


def _present_manifests() -> Dict[str, dict]:
    from arsenal.registry import load_registry  # a door may reach the registry; scene.py may not
    reg = load_registry()
    return {mid: reg.get(mid) for mid in reg.ids() if mid.startswith("present.")}


def _cmd_targets(args) -> int:
    from .targets import TARGETS
    scene = scene_mod.load(args.scene) if args.scene else None
    rows = []
    for mid, m in _present_manifests().items():
        row = {"id": mid, "engine": m.get("engine"), "status": m.get("status", "unknown"),
               "receipts": len(m.get("receipts") or []), "built": mid in TARGETS,
               "atoms": sorted((m.get("atoms") or {}).keys())}
        if scene is not None:
            row["coverage"] = scene_mod.coverage(scene, m)
        rows.append(row)
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        for r in rows:
            receipt = f"{r['receipts']} receipt(s)" if r["receipts"] else "no receipt (presumed broken until one lands)"
            built = "renderer built" if r["built"] else "no renderer"
            print(f"{r['id']:<22} {str(r['engine']):<9} {r['status']:<9} {built:<15} {receipt}")
            for p in r.get("coverage") or []:
                print(f"    REFUSED {p}")
    return 0


def _slide_table(scene: dict, manifest: dict) -> Dict[str, Dict[str, List[str]]]:
    """Per slide: which of its atom kinds the target preserves, degrades and drops (from the
    manifest's atoms table). A kind may appear in more than one column: 'preserves as pixels,
    drops selectable text' is both."""
    table = manifest.get("atoms") or {}
    out: Dict[str, Dict[str, List[str]]] = {}
    for slide in scene.get("slides") or []:
        kinds = sorted({a.get("kind") for a in scene_mod.iter_atoms(slide) if isinstance(a.get("kind"), str)})
        row = {"preserved": [], "degraded": [], "dropped": []}
        for kind in kinds:
            spec = table.get(kind) or {}
            if spec.get("preserves"):
                row["preserved"].append(kind)
            if spec.get("degrades"):
                row["degraded"].append(kind)
            if spec.get("drops"):
                row["dropped"].append(kind)
        out[slide.get("id", "?")] = row
    return out


def _drop_only(scene: dict, manifest: dict) -> List[str]:
    table = manifest.get("atoms") or {}
    out = []
    for kind in sorted(scene_mod.used_kinds(scene)):
        spec = table.get(kind) or {}
        if spec.get("drops") and not (spec.get("preserves") or spec.get("degrades")):
            out.append(f"{manifest.get('id')} drops every {kind} atom ({spec['drops']}); pass --allow-drops to render without them")
    return out


def _cmd_render(args) -> int:
    from .targets import SUBDIR, TARGETS, resolve
    try:
        target = resolve(args.to)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    scene_path = Path(args.scene)
    scene = scene_mod.load(scene_path)
    refusals = scene_mod.validate(scene)
    if refusals:
        for line in refusals:
            print(f"REFUSED {line}")
        print(f"REFUSED: {len(refusals)} refusal(s); nothing rendered")
        return 1
    warnings = scene_mod.lint(scene)
    for line in warnings:
        print(f"note: {line}")
    manifest = _present_manifests().get(target) or {"id": target, "version": "?", "atoms": {}}
    problems = scene_mod.coverage(scene, manifest)
    if not args.allow_drops:
        problems += _drop_only(scene, manifest)
    if problems:
        for line in problems:
            print(f"REFUSED {line}")
        return 1
    per_slide = _slide_table(scene, manifest)
    if args.dry:
        print(f"{target} (manifest {manifest.get('version')}), dry: nothing written")
        for sid, row in per_slide.items():
            print(f"  {sid:<14} preserved {', '.join(row['preserved']) or '-'}"
                  + (f" | degraded {', '.join(row['degraded'])}" if row["degraded"] else "")
                  + (f" | dropped {', '.join(row['dropped'])}" if row["dropped"] else ""))
        return 0
    out_root = Path(args.out) if args.out else scene_path.parent / "render"
    out_dir = out_root / SUBDIR[target]
    opts = {}
    if args.width is not None:
        opts["width"] = args.width
    if args.slide:
        opts["slide"] = args.slide
    if args.no_footnotes:
        opts["footnotes"] = False
    if args.autoplay:
        opts["autoplay"] = True
    if args.verify_cdn:
        opts["verify_cdn"] = True
    t0 = time.perf_counter()
    written = TARGETS[target](scene, out_dir, **opts)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    take = {"take": "present.render/v0", "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "target": target, "module_version": manifest.get("version"),
            "scene": {"path": str(scene_path), "sha256": hashlib.sha256(scene_path.read_bytes()).hexdigest(),
                      "title": scene.get("title"), "slides": len(scene.get("slides") or [])},
            "opts": opts, "elapsed_ms": elapsed_ms, "written": [str(p) for p in written],
            "per_slide": per_slide, "warnings": warnings}
    takes = out_root / "takes"
    takes.mkdir(parents=True, exist_ok=True)
    take_path = takes / f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{target}.json"
    take_path.write_bytes((json.dumps(take, indent=1) + "\n").encode("utf-8"))
    print(f"{target}: {len(written)} file(s) under {out_dir} in {elapsed_ms} ms; take {take_path}")
    for p in written[:8]:
        print(f"  {p}")
    if len(written) > 8:
        print(f"  ... {len(written) - 8} more")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m arsenal.present", description="present.scene.v1 tools")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="validate + lint a scene; exit 1 on any refusal")
    c.add_argument("scene")
    c.add_argument("--json", action="store_true")
    t = sub.add_parser("targets", help="list present.* render targets with status; with --scene, check each one's atom coverage")
    t.add_argument("--scene")
    t.add_argument("--json", action="store_true")
    r = sub.add_parser("render", help="render a scene to one target; writes a take")
    r.add_argument("scene")
    r.add_argument("--to", required=True, help="slides | ui | pdf | 3d (or a present.* module id)")
    r.add_argument("--out", help="output root (default: <scene dir>/render); each target takes its own subdirectory")
    r.add_argument("--width", type=int, help="ui: the panel width in CSS pixels (default 400)")
    r.add_argument("--slide", help="ui: render this one slide id (default: every slide)")
    r.add_argument("--no-footnotes", action="store_true", help="pdf: full-bleed pages, notes dropped")
    r.add_argument("--autoplay", action="store_true", help="3d: advance by duration_s")
    r.add_argument("--verify-cdn", action="store_true", help="3d: HEAD-check the three.js URL (network)")
    r.add_argument("--allow-drops", action="store_true", help="render even where the target only drops a kind the deck uses")
    r.add_argument("--dry", action="store_true", help="print per slide what is preserved, degraded and dropped; write nothing")
    args = ap.parse_args(argv)
    return {"check": _cmd_check, "targets": _cmd_targets, "render": _cmd_render}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
