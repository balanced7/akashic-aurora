"""Resolve the image/file Daniel just sent via chat to a local path -- fast, one command.

When he sends a photo from mobile, the Discord/Bifrost bridge drops it in a per-worktree inbound-media dir with a
snowflake-prefixed name, and the wake context shows only the bare filename. Finding it meant guessing and globbing.
This scans every worktree's inbound-media dir (and known fallbacks), newest first, so the flow becomes:

    py scripts/inbound_media.py                # absolute path of the newest inbound file  (then Read it)
    py scripts/inbound_media.py bb0531f3       # newest whose name contains this substring (paste from the wake tag)
    py scripts/inbound_media.py --n 5          # newest 5 paths
    py scripts/inbound_media.py --copy shot.jpg  # also copy the newest match to a stable path

stdout is paths only (one per line) so it reads/pipes clean; size+age go to stderr.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

# inbound media can land under whichever worktree the bridge runs from, so scan them all.
ROOTS = [
    r"C:\Users\L5\AppData\Local\AkashicAurora\worktrees\*\state\inbound-media",
    r"C:\Users\L5\AppData\Local\AkashicAurora\state\inbound-media",
    r"E:\AI-Setup\state\inbound-media",
]


def candidates():
    found = {}
    for pattern in ROOTS:
        for d in glob.glob(pattern):
            for f in glob.glob(os.path.join(d, "*")):
                if os.path.isfile(f):
                    try:
                        found[f] = os.path.getmtime(f)
                    except OSError:
                        pass
    return sorted(found.items(), key=lambda kv: kv[1], reverse=True)


def _age(mtime: float) -> str:
    s = max(0, time.time() - mtime)
    if s < 90:
        return f"{int(s)}s ago"
    if s < 5400:
        return f"{int(s // 60)}m ago"
    return f"{int(s // 3600)}h ago"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="newest inbound chat media, as local paths")
    ap.add_argument("name", nargs="?", help="substring filter on the filename (e.g. a uuid from the wake tag)")
    ap.add_argument("--n", type=int, default=1, help="how many newest to print (default 1)")
    ap.add_argument("--copy", help="copy the newest match to this path too")
    a = ap.parse_args(argv)

    items = candidates()
    if a.name:
        needle = a.name.lower()
        items = [(f, m) for (f, m) in items if needle in os.path.basename(f).lower()]
    if not items:
        print("no inbound media found (looked in: " + " | ".join(ROOTS) + ")", file=sys.stderr)
        return 1

    for f, m in items[:max(1, a.n)]:
        try:
            size = os.path.getsize(f)
        except OSError:
            size = 0
        print(f"  {os.path.basename(f)}  {size // 1024} KB  {_age(m)}", file=sys.stderr)
        print(f)  # stdout: the path, clean

    if a.copy:
        import shutil
        shutil.copy2(items[0][0], a.copy)
        print(f"copied newest -> {a.copy}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
