"""A world's restore point: code and memory under one name.

    py scripts/world_savepoint.py save "before-risky-thing"
    py scripts/world_savepoint.py list
    py scripts/world_savepoint.py restore before-risky-thing

Run it from the checkout you mean. Both planes derive from where you are standing -- the
W156h incident was a tool whose two planes disagreed about that, and it flushed production
twice, so this one does not take a world argument at all.

Savepoints live in .aurora-savepoints.json, UNTRACKED for the same reason .aurora-world is:
a restore point is a property of THIS checkout, and anything that rides git would be
clobbered by the next promotion from prod.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.coord import world_savepoint as SP                        # noqa: E402
from core.paths import repo_root                                    # noqa: E402
from core.world import current                                      # noqa: E402

ROOT = repo_root()
STORE = ROOT / ".aurora-savepoints.json"
SNAPSHOTS = ROOT / "backups" / "snapshots"


def _git(*args) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True).stdout.strip()


def _status_lines():
    """Porcelain lines WITHOUT an outer strip.

    _git() strips its whole stdout, which eats the leading space of the FIRST line only --
    so fixed-width slicing shifted by one and turned `chronicles/memory.md` into
    `hronicles/memory.md`. Exactly one file misclassified, every time, silently: the shape
    of bug that makes a guard flaky rather than broken, so nobody chases it.
    """
    return subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"],
                          capture_output=True, text=True).stdout.splitlines()


def _dirty_split():
    """(authored, generated) counts. Only authored dirt is work a restore would destroy."""
    paths = [l[2:].strip() for l in _status_lines()
             if l and not l.lstrip().startswith("??")]
    authored = SP.authored_dirt(paths)
    return len(authored), len(paths) - len(authored)


def _dirty() -> int:
    return _dirty_split()[0]


def _snapshot_exists(name: str) -> bool:
    return (SNAPSHOTS / name).is_dir()


def cmd_save(label: str) -> int:
    world = current().name
    if world == "unknown":
        print("REFUSING: this checkout has not declared its world.\n"
              "  FIX: echo alpha > .aurora-world")
        return 2

    before = {p.name for p in SNAPSHOTS.iterdir()} if SNAPSHOTS.is_dir() else set()
    rc = subprocess.run([sys.executable, str(ROOT / "scripts" / "ops" /
                                             "snapshot_knowledge.py"),
                         "snapshot", f"world-savepoint:{world}:{label}"],
                        cwd=str(ROOT))
    after = {p.name for p in SNAPSHOTS.iterdir()} if SNAPSHOTS.is_dir() else set()
    fresh = sorted(after - before)
    snap = fresh[-1] if fresh else None
    if rc.returncode != 0 or not snap:
        # Recording a savepoint whose memory half silently failed is how a restore point
        # becomes a lie discovered at the worst moment.
        print("REFUSING to record the savepoint: the knowledge snapshot did not land, so "
              "this point would restore code without memory.")
        return 2

    authored, generated = _dirty_split()
    sp = SP.Savepoint(world=world, label=label, git_sha=_git("rev-parse", "--short", "HEAD"),
                      knowledge_snapshot=snap, dirty_at_save=authored,
                      generated_at_save=generated,
                      saved_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    SP.append(STORE, sp)
    print(f"[savepoint] {sp.render()}")
    print(f"  recover without this tool:  {sp.recovery}")
    if not sp.complete:
        print(f"  PARTIAL: {sp.caveat}")
    elif sp.note:
        print(f"  note: {sp.note}")
    return 0


def cmd_list() -> int:
    points = SP.read(STORE)
    if not points:
        print(f"no savepoints in {STORE.name} for this checkout "
              f"(world: {current().name})")
        return 0
    print(f"savepoints ({current().name}, {STORE.name}):")
    for p in points:
        alive = "" if _snapshot_exists(p.knowledge_snapshot or "") else "   [MEMORY PRUNED]"
        print(f"  {p.render()}{alive}")
        print(f"      recover: {p.recovery}")
    return 0


def cmd_restore(label: str, consent: bool) -> int:
    points = {p.label: p for p in SP.read(STORE)}
    sp = points.get(label)
    if not sp:
        print(f"no savepoint named '{label}'. Known: {', '.join(points) or '(none)'}")
        return 2

    ok, why = SP.can_restore(sp, snapshot_exists=_snapshot_exists,
                             tree_dirty=_dirty(), consent=consent,
                             into_world=current().name)
    if not ok:
        print(why)
        return 2

    print(f"[restore] {sp.label} -- code {sp.git_sha}, memory {sp.knowledge_snapshot}")
    subprocess.run(["git", "-C", str(ROOT), "checkout", "-q", sp.git_sha])
    subprocess.run([sys.executable, str(ROOT / "scripts" / "ops" /
                                        "snapshot_knowledge.py"),
                    "restore", sp.knowledge_snapshot], cwd=str(ROOT))
    print(f"[restore] DONE -- {current().name} is back at '{sp.label}'")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save"); s.add_argument("label")
    sub.add_parser("list")
    r = sub.add_parser("restore"); r.add_argument("label")
    r.add_argument("--yes-prod", action="store_true",
                   help="required only when the checkout is prod")
    a = ap.parse_args()

    if a.cmd == "save":
        return cmd_save(a.label)
    if a.cmd == "list":
        return cmd_list()
    return cmd_restore(a.label, consent=a.yes_prod)


if __name__ == "__main__":
    raise SystemExit(main())
