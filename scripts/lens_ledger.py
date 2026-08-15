"""Score fan lenses by what survived, and recommend which to run next.

    py scripts/lens_ledger.py show
    py scripts/lens_ledger.py record --lens "<lens slug>" --outcome confirmed --fan <id> --note "..."

Outcomes: confirmed | refuted | abstained | unverified

The route journal beside this (state/route_journal.jsonl) records whether a fan RAN. This
records whether its branches were WORTH running -- the half Daniil asked for on 2026-08-11
that never got built. See core/coord/lens_ledger.py for why abstentions are not misses and
unverified findings are never wins.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.coord import lens_ledger as L                       # noqa: E402
from core.paths import repo_root                              # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    r = sub.add_parser("record")
    r.add_argument("--lens", required=True)
    r.add_argument("--outcome", required=True, choices=sorted(L.OUTCOMES))
    r.add_argument("--fan", required=True)
    r.add_argument("--geometry", default="lens")
    r.add_argument("--note", default="")
    a = ap.parse_args()

    path = L.ledger_path(repo_root())

    if a.cmd == "record":
        try:
            run = L.LensRun(lens=a.lens, geometry=a.geometry, outcome=a.outcome,
                            fan_id=a.fan, note=a.note)
        except ValueError as e:
            print(f"REFUSED: {e}")
            return 2
        L.record(path, run)
        print(f"[lens-ledger] {a.outcome:<11} {a.lens}  (fan {a.fan})")
        return 0

    runs = L.read(path)
    scores = L.score(runs)
    print(L.render(scores, L.gate(scores)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
