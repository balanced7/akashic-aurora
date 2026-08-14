"""What differs between two worlds, minus what should differ.

    py scripts/world_diff.py                     # prod -> alpha (this checkout's world)
    py scripts/world_diff.py --from prod --to beta
    py scripts/world_diff.py --from prod --to alpha --json

Reports two of an instance's three planes:

  MEMORY  Redis, classified against the target's seed manifest so 13,963 keys of expected
          difference cannot bury ~10 real ones.
  CODE    git, and specifically the distinction that cost a wrong diagnosis on 2026-08-14:
          a twin is faithful to HEAD, and a long-lived prod tree is usually NOT at HEAD, so
          uncommitted work upstream shows up as divergence downstream. Committed drift and
          uncommitted drift are different findings and are never summed.

The FILE plane (state/, research/) is deliberately absent rather than half-measured -- a
clone carries only tracked files, and a differ that reported those two things as one number
would repeat the exact error this tool exists to prevent.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import redis                                                        # noqa: E402

from core.coord import world_diff as WD                             # noqa: E402
from core.world import WORLDS, current                              # noqa: E402
from core.world_seed import read_manifest                           # noqa: E402

#: Where each world's checkout lives, so the CODE plane can be read without guessing.
CHECKOUTS = {"prod": "E:/AI-Setup", "beta": "E:/AI-Setup-Beta", "alpha": "E:/AI-Setup-Alpha"}


def _client(world: str):
    host, port, db = WORLDS[world].redis_endpoint()
    return redis.Redis(host=host, port=port, db=db, socket_timeout=15)


def _count(client, prefix: str) -> int:
    return sum(1 for _ in client.scan_iter(match=f"{prefix}*", count=2000))


def _prefixes(manifest, src, dst) -> list:
    """Every prefix worth a row: what the seed named, plus anything LIVE that it did not.

    Taking the union rather than only the manifest's list is the point -- a prefix that
    appeared after the seed is precisely the case the manifest cannot vouch for, and
    omitting it would let new state arrive invisibly.
    """
    named = set()
    if manifest:
        named |= set(manifest.get("carried") or {})
        named |= set(manifest.get("refused") or {})
    live = set()
    for c in (src, dst):
        for key in c.scan_iter(match="*", count=3000):
            k = key.decode() if isinstance(key, bytes) else key
            if ":" in k:
                live.add(k.split(":", 1)[0] + ":")
    return sorted(named | live)


def _git(world: str) -> dict:
    root = CHECKOUTS.get(world)
    if not root or not Path(root).exists():
        return {"ok": False, "why": f"no checkout registered for {world}"}

    def g(*args):
        return subprocess.run(["git", "-C", root, *args],
                              capture_output=True, text=True).stdout.strip()
    dirty = [l for l in g("status", "--porcelain").splitlines() if l and not l.startswith("??")]
    return {"ok": True, "head": g("rev-parse", "--short", "HEAD"),
            "subject": g("log", "-1", "--format=%s")[:60],
            "uncommitted": len(dirty), "untracked": len(
                [l for l in g("status", "--porcelain").splitlines() if l.startswith("??")])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="source", default="prod")
    ap.add_argument("--to", dest="target", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    target = args.target or current().name
    if target == "unknown":
        print("REFUSING: this checkout has not declared its world and no --to was given.\n"
              "  FIX: echo alpha > .aurora-world   (or pass --to alpha)")
        return 2
    if target == args.source:
        print(f"REFUSING: {args.source} and {target} are the same world.")
        return 2

    src, dst = _client(args.source), _client(target)
    manifest = read_manifest(dst)

    rows = []
    for prefix in _prefixes(manifest, src, dst):
        n_s, n_t = _count(src, prefix), _count(dst, prefix)
        rows.append(WD.PlaneRow(prefix, n_s, n_t,
                                WD.classify(prefix, present_in_target=n_t > 0,
                                            manifest=manifest)))

    rows, collapsed = WD.collapse_minor(rows, manifest=manifest)
    gs, gt = _git(args.source), _git(target)

    if args.json:
        print(json.dumps({"source": args.source, "target": target,
                          "manifest": manifest,
                          "memory": [{"prefix": r.prefix, "source": r.n_source,
                                      "target": r.n_target,
                                      "severity": r.verdict.severity,
                                      "expected": r.verdict.expected,
                                      "why": r.verdict.why} for r in rows],
                          "code": {"source": gs, "target": gt}}, indent=2))
        return 0

    print(WD.render(rows, source=args.source, target=target, manifest=manifest,
                    collapsed=collapsed))
    print()
    print(f"CODE  {args.source} -> {target}")
    if gs.get("ok") and gt.get("ok"):
        same = gs["head"] == gt["head"]
        print(f"  [{'identical' if same else '  differs':>9}] HEAD           "
              f"{gs['head']:>8} vs {gt['head']:>8}   "
              f"{'same commit' if same else gt['subject']}")
        # The 2026-08-14 lesson, rendered rather than remembered.
        print(f"  [{'context':>9}] uncommitted    {gs['uncommitted']:>8,} vs "
              f"{gt['uncommitted']:>8,}   a twin is faithful to HEAD; "
              f"{args.source} carries {gs['uncommitted']} tracked edits HEAD does not have, "
              f"and each one can surface downstream as a real-looking failure")
    else:
        print(f"  unavailable: {gs.get('why') or gt.get('why')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
