"""RED PIN -- the 2026-07-27 learning-index blindness RECURRENCE.

WHAT THIS PINS
--------------
`HybridStore.heal_report()` runs at every agent cold-start boot. Its TRIGGER is narrow:

    drift = self.check_drift()
    if drift.get("missing_in_redis"):      # ANY single key missing in Redis
        rep = self.reconcile()             # ... rewrites EVERY list from the File snapshot

but `reconcile()`'s ACTION is global, and for lists it is destructive:

    for k, lst in snap["list"].items():
        self._redis.delete(k)              # <-- Redis's copy is destroyed
        self._redis.rpush(k, *lst)         # <-- rebuilt from File, whatever File happens to hold

The premise in the docstring is "File is source of truth". For the learning corpus that
premise is FALSE: measured 2026-07-27, the File plane held 20 lesson hashes and a 16-entry
`learn:experiments:all`, while Redis held 477 hashes and the full 475-entry index. So one
unrelated drifted key demotes the whole corpus to a 16-lesson fossil, and recall goes blind
to 96% of its own memory.

The hash branch uses `hset(mapping=...)`, which MERGES fields rather than replacing the key.
That asymmetry is why the 477 hashes survived every occurrence while only the list collapsed --
the data was never lost, only its membership. That detail is what made the bug so hard to see:
`repair_learning_index.py --apply` always "fixed" it, because the records were always there.

WHY IT KEPT COMING BACK
-----------------------
The prior arc fixed a DIFFERENT bug: `is_new` keyed on hash existence meant the index could
never SELF-HEAL through the normal write path. That is real and was fixed. It is not this.
Nothing stopped the CLOBBER. The note recall-index-blindness honestly recorded "WHAT I HAVE
NOT ESTABLISHED: the original truncation event" -- because there is no single event. It is
every boot that finds drift, which is why the same 16 survivors return each time and why they
interleave with the orphans in time.

THE ASSERTION
-------------
A heal must never make a backend LOSE data. Backfilling Redis from File is legitimate; deleting
a richer Redis list and replacing it with a File subset is not a heal, it is data loss with a
reassuring log line ("[heal] Redis was behind -- backfilled N key-structure(s)").
"""

import os
import sys
import tempfile
import time

# Full isolation BEFORE any foundation import: FILE store -> throwaway AI_SETUP, REDIS -> db 15.
_TMP_AI_SETUP = tempfile.mkdtemp(prefix="aisetup_test_")
os.makedirs(os.path.join(_TMP_AI_SETUP, "session_logs"), exist_ok=True)
os.environ["AI_SETUP"] = _TMP_AI_SETUP
os.environ.setdefault("REDIS_DB", "15")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import FileStore, RedisStore, HybridStore  # noqa: E402


def test_heal_must_not_clobber_a_richer_redis_list():
    """One unrelated File-only key must not destroy a Redis list that File holds only a subset of.

    This is the learning index's exact shape: File keeps a stale fossil, Redis keeps the truth.
    """
    rs = RedisStore.connect(timeout_seconds=2.0)
    if not rs.is_available():
        print("\n--- heal clobber pin ---\n  SKIPPED (Redis not running)")
        return

    ns = f"healpin:{int(time.time() * 1000)}"
    index_key = f"{ns}:experiments:all"
    try:
        with tempfile.TemporaryDirectory() as d:
            fs = FileStore(os.path.join(d, "s.json"))

            # The corpus index as it really is: File = stale 2-entry fossil, Redis = full 20.
            fs.rpush(index_key, "fossil_a", "fossil_b")
            rs.delete(index_key)
            rs.rpush(index_key, *[f"lesson_{i:02d}" for i in range(20)])

            # The ONLY thing the trigger needs: one unrelated key that File has and Redis does not.
            # In the live system this is any ordinary File-ahead drift -- the boot heal exists
            # precisely to backfill it, and that backfill is legitimate.
            fs.set(f"{ns}:unrelated_drifted_key", "1")

            hybrid = HybridStore(rs, fs)
            drift = hybrid.check_drift()
            assert any(k.startswith(ns) for k in drift["missing_in_redis"]), (
                "precondition: the unrelated key must register as File-ahead drift")

            before = rs.lrange(index_key, 0, -1)
            assert len(before) == 20, f"precondition: Redis holds the full index, got {len(before)}"

            hybrid.heal_report()          # <-- what every agent boot runs

            after = rs.lrange(index_key, 0, -1)
            assert len(after) == 20, (
                f"HEAL DESTROYED THE RICHER LIST: Redis held {len(before)} entries, "
                f"File held 2, and after heal_report() Redis holds {len(after)} -> {after}. "
                f"A heal must never make a backend lose data. This is the mechanism behind "
                f"the recall-index blindness recurrence of 2026-07-27.")
    finally:
        try:
            rs.delete(index_key)
        except Exception:
            pass


if __name__ == "__main__":
    test_heal_must_not_clobber_a_richer_redis_list()
    print("PASS")
