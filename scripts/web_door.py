"""web_door -- CLI shim over core.web.door until the agent_cli verb wiring lands.

    py scripts/web_door.py fetch <url> [--raw] [--pdf-full] [--offset N] [--limit N]
    py scripts/web_door.py search <query...> [--count N]

Prints the JSON envelope, ascii-safe. Every call writes a receipt to
state/coord/web_fetch_receipts.jsonl. Served text is fenced UNTRUSTED.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from core.web import door  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(prog="web_door")
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch")
    f.add_argument("url")
    f.add_argument("--raw", action="store_true")
    f.add_argument("--pdf-full", action="store_true")
    f.add_argument("--offset", type=int, default=0)
    f.add_argument("--limit", type=int, default=door.DEFAULT_LIMIT)

    s = sub.add_parser("search")
    s.add_argument("query", nargs="+")
    s.add_argument("--count", type=int, default=8)

    a = ap.parse_args()
    if a.cmd == "fetch":
        env = door.fetch(a.url, offset=a.offset, limit=a.limit,
                         want_raw=a.raw, pdf_full=a.pdf_full)
    else:
        env = door.search(" ".join(a.query), count=a.count)
    print(json.dumps(env, ensure_ascii=True, indent=1))
    return 0 if env.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
