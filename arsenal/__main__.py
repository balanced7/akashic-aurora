"""arsenal command line: serve | plan | inspect | probe | analyze | takes.

Run from the repo root (or with PYTHONPATH pointing at it):  py -m arsenal serve
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="py -m arsenal", description="Daniel's modular media suite")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="run the local First Light server on 127.0.0.1")
    s.add_argument("--port", type=int, default=8793)
    s.add_argument("--root", action="append", help="a library root; repeat for more (default: E:\\Video Output E)")

    p = sub.add_parser("plan", help="print the loud plan for a graph (.json, or the text form)")
    p.add_argument("graph")

    i = sub.add_parser("inspect", help="print a module manifest, or list the modules")
    i.add_argument("module", nargs="?")

    pr = sub.add_parser("probe", help="probe a media file with FFmpeg (via PyAV)")
    pr.add_argument("path")
    pr.add_argument("--hw", action="store_true", help="also test hardware decode")

    an = sub.add_parser("analyze", help="compute timestamped audio features")
    an.add_argument("path")
    an.add_argument("--out")

    sub.add_parser("takes", help="list recorded takes")

    args = ap.parse_args(argv)

    if args.cmd == "serve":
        from .serve import serve
        serve(port=args.port, roots=args.root)
        return 0

    if args.cmd == "plan":
        from .graph import GraphError, load_graph, parse_text
        from .plan import make_plan, render_plan
        from .registry import load_registry
        registry = load_registry()
        source = Path(args.graph).read_text(encoding="utf-8")
        try:
            obj = json.loads(source) if args.graph.lower().endswith(".json") else parse_text(source, registry)
            print(render_plan(make_plan(load_graph(obj), registry)))
        except GraphError as exc:
            print("the graph does not validate:", file=sys.stderr)
            for problem in exc.problems:
                print(f"  - {problem}", file=sys.stderr)
            return 2
        return 0

    if args.cmd == "inspect":
        from .registry import load_registry
        registry = load_registry()
        if not args.module:
            print("\n".join(registry.ids()))
            return 0
        try:
            print(json.dumps(registry.get(args.module), indent=2))
        except KeyError:
            print(f"no module {args.module!r}; try: py -m arsenal inspect", file=sys.stderr)
            return 2
        return 0

    if args.cmd == "probe":
        from . import analysis
        result = analysis.probe(args.path)
        if args.hw:
            result["hwdecode"] = analysis.hw_decode_evidence(args.path)
        print(json.dumps(result, indent=2))
        return 0

    if args.cmd == "analyze":
        from . import analysis
        features = analysis.audio_features(args.path)
        rows = len(features.get("frames") or [])
        if args.out:
            Path(args.out).write_text(json.dumps(features), encoding="utf-8")
            print(f"wrote {rows} rows to {args.out}")
        else:
            summary = {k: v for k, v in features.items() if k != "frames"}
            summary["rows"] = rows
            print(json.dumps(summary, indent=2))
        return 0

    if args.cmd == "takes":
        from .take import TakeLedger
        for take in TakeLedger().list():
            state = "closed" if take["closed"] else "open  "
            print(f"{take['take_id']}  {state}  {take['event_count']:>6} events  {take.get('clip') or ''}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
