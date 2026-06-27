"""
Verify the migrated LearningStore (Pillar 0 / HybridStore) against the existing
on-disk learnings, with Redis DOWN (File fallback path).

Run: py -u tests/verify_learning_migration.py
"""

import sys
import os
import json
import tempfile

# NOTE: deliberately NOT isolated via isolate_canonical: this test injects its own
# temp HybridStore with Redis OFF (bogus port), so it never touches canonical, AND
# it must read the REAL session_logs/learnings.jsonl to verify the legacy-import path.

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.store import HybridStore
from core.learning.learning_store import LearningStore


def _count_legacy():
    """Count UNIQUE experiment_names (the Store keys by name, so repeated
    emits of the same experiment collapse to one -- this is the idempotency
    mechanism, not data loss)."""
    legacy = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "session_logs", "learnings.jsonl")
    names = set()
    if os.path.exists(legacy):
        with open(legacy, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    sig = json.loads(line)
                except json.JSONDecodeError:
                    continue
                name = sig.get("experiment_name")
                if name:
                    names.add(name)
    return len(names)


def main():
    print("=" * 60)
    print("LEARNING STORE MIGRATION VERIFICATION (Redis down)")
    print("=" * 60)

    legacy_count = _count_legacy()
    print(f"\nLegacy learnings.jsonl has {legacy_count} valid experiment(s)")

    # Use an isolated temp file store so we don't clobber real store_state.json,
    # but still exercise the real legacy import path (it reads session_logs/learnings.jsonl).
    with tempfile.TemporaryDirectory() as d:
        store = HybridStore.create(port=63999, file_path=os.path.join(d, "store.json"))
        assert store.redis_available is False, "expected Redis down on bogus port"
        print("Backend: HybridStore -> FileStore (Redis unavailable) OK")

        ls = LearningStore(store=store)

        # 1) legacy import
        all_learnings = ls.load_all_learnings_from_store()
        print(f"\n[1] load_all_learnings_from_store -> {len(all_learnings)} learnings")
        assert len(all_learnings) == legacy_count, \
            f"expected {legacy_count} imported, got {len(all_learnings)}"
        print("    legacy import count matches OK")

        # 2) idempotent re-import: build a second LearningStore on SAME store
        ls2 = LearningStore(store=store)
        all2 = ls2.load_all_learnings_from_store()
        print(f"\n[2] re-instantiate on same store -> {len(all2)} learnings")
        assert len(all2) == legacy_count, \
            f"idempotency broken: {legacy_count} -> {len(all2)}"
        print("    idempotent re-import (no duplicates) OK")

        # 3) record a new learning
        before = len(ls.load_all_learnings_from_store())
        ok = ls.persist_learning_derived_from_experiment({
            "experiment_name": "migration_verify_exp",
            "what_tried": "route LearningStore through HybridStore",
            "expected_outcome": "single code path, file fallback works",
            "actual_outcome": "verified",
            "category": "verification",
            "success": "yes",
            "confidence": "high",
            "recommendation": "swap Store to swap persistence",
            "agent_id": "migration_test",
        })
        after = len(ls.load_all_learnings_from_store())
        print(f"\n[3] persist new learning -> ok={ok}, count {before} -> {after}")
        assert ok and after == before + 1, "new learning did not index"
        print("    new learning indexed OK")

        # 4) search
        hits = ls.search_learnings_by_keyword("migration")
        print(f"\n[4] search 'migration' -> {len(hits)} hit(s)")
        assert any(h["id"] == "migration_verify_exp" for h in hits), "search miss"
        print("    search finds new learning OK")

        # 5) recommendations
        recs = ls.load_recommendations_for_task("verification")
        print(f"\n[5] recommendations for 'verification' -> {len(recs)}")
        assert any("swap Store" in r["recommendation"] for r in recs), "rec miss"
        print("    recommendation surfaced OK")

        # 6) category summary
        summary = ls.summarize_learnings_by_category()
        print(f"\n[6] category summary -> {len(summary)} categories: {sorted(summary)}")
        assert "verification" in summary, "verification category missing"
        print("    category summary OK")

        # 7) by-agent
        agent_learnings = ls.load_learnings_contributed_by_agent("migration_test")
        print(f"\n[7] learnings by 'migration_test' -> {len(agent_learnings)}")
        assert len(agent_learnings) == 1, "agent index wrong"
        print("    by-agent index OK")

        # 8) stats
        stats = ls.get_learning_store_stats()
        print(f"\n[8] stats -> {stats}")
        assert stats["total_experiments"] == after, "stats total mismatch"
        assert stats["redis_connected"] is False, "redis should be down"
        print("    stats OK")

        # 9) success vocabulary is canonical (no stray "True"/"False"/synonyms)
        canonical = {"yes", "partial", "no"}
        bad = [l["experiment_name"] for l in ls.load_all_learnings_from_store()
               if l.get("success") not in canonical]
        print(f"\n[9] success vocabulary check -> {len(bad)} non-canonical")
        assert not bad, f"non-canonical success values: {bad}"
        # normalizer maps the messy inputs we've actually seen
        assert LearningStore.normalize_success_to_vocabulary("True") == "yes"
        assert LearningStore.normalize_success_to_vocabulary(True) == "yes"
        assert LearningStore.normalize_success_to_vocabulary("failed") == "no"
        assert LearningStore.normalize_success_to_vocabulary(None) == "no"
        assert LearningStore.normalize_success_to_vocabulary("partial") == "partial"
        assert LearningStore.normalize_success_to_vocabulary("???") == "no"
        print("    canonical {yes,partial,no} + normalizer mappings OK")

    print("\n" + "=" * 60)
    print("ALL MIGRATION VERIFICATION CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
