"""re triage CLI — registers `re triage` on the arsenal verb surface.

Mirrors arsenal/shaders/cli.py's pattern: modules add verbs via
`cli.VERBS[name] = register(sub)`, so a missing module is simply an absent verb,
never a hard import failure. This module is imported lazily by the arsenal CLI only
when the `re` family is requested, so optional dependencies (pefile/magic) never
block the rest of the arsenal.
"""
from __future__ import annotations

import argparse


def _register(sub: argparse.ArgumentParser) -> None:
    p = sub.add_parser("triage", help="identify a file read-only and route to the next door")
    p.add_argument("path", help="file to triage (read a bounded prefix, never executed)")
    p.add_argument("--max-prefix", type=int, default=4096,
                   help="bytes to read before any detector runs (default 4096)")
    p.add_argument("--json", action="store_true", help="emit the receipt as JSON")
    p.set_defaults(func=_run)


def _run(args) -> int:
    from .triage import triage, triage_json

    if args.json:
        print(triage_json(args.path, max_prefix=args.max_prefix))
        return 0
    r = triage(args.path, max_prefix=args.max_prefix)
    payload = r["payload"]
    best = payload["matches"][0] if payload["matches"] else None
    print(f"kind:   {payload['kind']}")
    print(f"route:  {payload['route'] or '(no door yet — loud, not silent)'}")
    if best:
        tag = best.get("tag")
        conf = "" if best.get("confidence") is None else f" ({best['confidence']:.0%})"
        print(f"best:   [{tag}]{conf} {best.get('claim')}")
    blind = r["blind"].get("unsearched") or []
    for b in blind:
        print(f"blind:  {b}")
    return 0
