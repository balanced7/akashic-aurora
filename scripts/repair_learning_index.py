"""Repair `learn:experiments:all` -- the index that decides what recall can SEE.

THE DEFECT (found 2026-07-25, while designing tunable personas):
  406 lesson records existed. The index held 24. The other 382 -- 94% of the fleet's
  institutional memory -- were unreachable by every keyword search, because all three
  read paths in learning_store.py iterate this ONE list:

    search_learnings_by_keyword()   <- `recall "<query>"`, the documented mid-task door
    load_recommendations_for_task() <- task-shaped recall
    load_all_learnings_from_store() <- `recall` with no query, which claims "ALL lessons"

  The records were never lost and are still individually retrievable by exact source
  (`recall --full learn:experiment:NAME`), which is exactly why nobody noticed: every
  spot-check of a KNOWN lesson name succeeded, while search silently answered from 6%
  of the corpus. kimi's 2026-07-25 audit hit the symptom from the other side -- it
  reported the conductor_* lesson bodies "unreachable" by direct recall query.

  The WRITE path is correct (record_learning lpushes on is_new), so lessons filed since
  the loss are indexed; it is the older population that lost its entries. Suspected
  cause: scripts/harmonize_knowledge.py deletes this key and rewrites it from a
  hardcoded canonical set.

THE REPAIR: the index is a DERIVED projection over the records, so it is rebuildable.
This tool takes the UNION of what the index already holds and every record it can
discover, ordered newest-first by the record's own timestamp (the list's documented
semantic, learning_store.py:19). Union-only: it can add entries, never drop one --
so a record this tool cannot see is left alone rather than silently deleted.

Dry-run by default. `--apply` writes.

  py scripts/repair_learning_index.py            # report only
  py scripts/repair_learning_index.py --apply    # rebuild
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

INDEX = "learn:experiments:all"
PREFIX = "learn:experiment:"


def _discover(ls):
    """Every experiment name that has a record, however it is keyed in this backend."""
    names = set()
    try:
        for k in ls.store.keys(f"{PREFIX}*"):
            if PREFIX in k:
                n = k.split(PREFIX, 1)[1]
                if n:
                    names.add(n)
    except Exception as e:
        print(f"WARN: key discovery failed ({type(e).__name__}: {e}) -- "
              "repair will only re-order what the index already holds")
    return names


def _ts(ls, name):
    try:
        d = ls._load_experiment(name) or {}
        return str(d.get("timestamp") or "")
    except Exception:
        return ""


def plan(ls):
    """Compute the repair without writing: (current, found, missing, union).

    Split out from main() so the union-only guarantee is pinnable on a fake store --
    the property that matters is that a record this tool cannot see is KEPT, never
    silently dropped, because a repair that can lose data is worse than the defect."""
    current = list(ls.store.lrange(INDEX, 0, -1))
    have = set(current)
    found = _discover(ls)
    missing = sorted(found - have)
    union = sorted(have | found, key=lambda n: (_ts(ls, n) or "", n), reverse=True)
    return current, found, missing, union


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="write the rebuilt index (default: report only)")
    ap.add_argument("--check", action="store_true",
                    help="GUARD mode: exit non-zero if any record is missing from the "
                         "index (wire into ship gates -- check_doc_currency.py pattern). "
                         "A repair with no detector recurs silently, and this defect is "
                         "invisible from the outside: every spot-check of a known lesson "
                         "name passes while search answers from a fraction of the corpus.")
    args = ap.parse_args()

    from core.learning.learning_store import get_learning_store
    ls = get_learning_store()

    # Union, newest-first by the record's own timestamp. Unknown timestamps sort last
    # but are KEPT -- an unreadable record still deserves its index entry.
    current, found, missing, union = plan(ls)
    have = set(current)

    print(f"index entries now      : {len(current)}")
    print(f"records discovered     : {len(found)}")
    print(f"records NOT indexed    : {len(missing)}")
    print(f"index after repair     : {len(union)}")
    if missing:
        print("\nsample of what search cannot currently see:")
        for n in missing[:10]:
            print(f"   {n}")
    orphan_index = sorted(have - found)
    if orphan_index:
        print(f"\nindexed but no record discovered ({len(orphan_index)}) -- KEPT, not dropped:")
        for n in orphan_index[:5]:
            print(f"   {n}")

    if args.check:
        if missing:
            print(f"\nFAIL: {len(missing)} lesson(s) exist but are invisible to every "
                  f"keyword search ({100 * len(missing) // max(1, len(found))}% of the "
                  "corpus). Repair: py scripts/repair_learning_index.py --apply")
            return 1
        print("\n[OK] every discovered lesson record is reachable by search.")
        return 0

    if not args.apply:
        print("\n(dry run -- re-run with --apply to write)")
        return 0
    if not missing:
        print("\nnothing to repair; index already covers every discovered record.")
        return 0

    ls.store.delete(INDEX)
    ls.store.rpush(INDEX, *union)
    after = list(ls.store.lrange(INDEX, 0, -1))
    ok = len(after) == len(union) and set(after) == set(union)
    print(f"\n{'[OK]' if ok else 'ERROR'} index rebuilt: {len(current)} -> {len(after)} entries"
          f" ({len(missing)} lesson(s) returned to search)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
