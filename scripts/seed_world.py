"""Seed a lower world from a higher one. Read-only on the source, always.

    py scripts/seed_world.py --from prod --to alpha              # dry run, the default
    py scripts/seed_world.py --from prod --to alpha --apply
    py scripts/seed_world.py --from prod --to alpha --include events,recall --apply

The default is a dry run because the report is the point: it names what will be REFUSED,
and the refused half is what determines whether the twin behaves. Reading that before
writing is the whole ergonomic.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import redis                                                    # noqa: E402

from core import world_seed as S                                # noqa: E402
from core.world import WORLDS                                   # noqa: E402


def _client(world: str):
    # redis_endpoint() rather than reading .redis_port: it REFUSES when a world cannot say
    # where it lives, so an unresolved world fails here with a remedy instead of silently
    # producing a client pointed at None.
    host, port, db = WORLDS[world].redis_endpoint()
    return redis.Redis(host=host, port=port, db=db, socket_timeout=15)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="source", required=True)
    ap.add_argument("--to", dest="target", required=True)
    ap.add_argument("--include", default="",
                    help="comma-separated opt-in classes: events, recall")
    ap.add_argument("--apply", action="store_true",
                    help="actually write; without it this is a dry run")
    args = ap.parse_args()

    include = [x.strip() for x in args.include.split(",") if x.strip()]
    try:
        plan = S.plan(args.source, args.target, include=include)
    except S.SeedRefusal as exc:
        print(f"REFUSED: {exc}")
        return 2

    src, dst = _client(plan.source), _client(plan.target)

    # Belt: the plan validated the WORLD names; this validates the ENDPOINTS actually
    # resolved to different servers. A config slip that pointed both at one Redis would
    # otherwise "succeed" by copying prod onto itself.
    if src.connection_pool.connection_kwargs["port"] == \
            dst.connection_pool.connection_kwargs["port"]:
        print(f"REFUSED: {plan.source} and {plan.target} resolved to the SAME endpoint "
              f"({WORLDS[plan.source].redis_port}). Refusing to seed a world from itself.")
        return 2

    counts = {}
    for prefix in plan.prefixes:
        counts[prefix] = S.copy_prefix(src, dst, prefix, apply=args.apply)
    for prefix in plan.excluded:
        counts[prefix] = sum(1 for _ in src.scan_iter(match=f"{prefix}*", count=500))

    print(plan.render(counts=counts, applied=args.apply))
    print(f"\n  source {plan.source} :{WORLDS[plan.source].redis_port} "
          f"({src.dbsize():,} keys, untouched -- reads only)")
    print(f"  target {plan.target} :{WORLDS[plan.target].redis_port} "
          f"({dst.dbsize():,} keys)")
    if not args.apply:
        print("\n  DRY RUN -- nothing was written. Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
