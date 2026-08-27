"""Reproducible random sample of the LIVE learn:experiment corpus, for the magnitude-blind-spot brief.

Run: py -m pytest tests/test_corpus_sample_heimdall.py -q -s

This is a MEASUREMENT helper, not a permanent test. It draws a seeded sample of the
LIVE lesson corpus (via RedisStore, same store `recall` reaches) and prints name +
recommendation + root_cause so a reader can classify each as BINARY-correctness vs
MAGNITUDE (too much / too little / too long).

Seed + method are stated inline so the draw is reproducible.
"""
import random

import pytest

from core.foundation.store import RedisStore
from core.learning.learning_store import LearningStore


def test_print_seeded_sample():
    # Explicitly reach the LIVE store (RedisStore), NOT the isolated stub.
    # pytest's _AISETUP_TEST_ISOLATED env makes the bare get_learning_store()
    # return a fresh empty store; we bypass that by injecting the live backend.
    try:
        # db=0 EXPLICIT: the pytest family forces REDIS_DB=15 (isolated test db),
        # which holds only 6 legacy semantic_* records. The live corpus lives on db 0.
        redis = RedisStore.connect(timeout_seconds=2.0, db=0)
    except Exception as e:
        pytest.skip(f"redis not reachable: {type(e).__name__}: {e}")
    if not redis.is_available():
        pytest.skip("redis not available")

    ls = LearningStore(store=redis)
    lessons = ls.load_all_learnings_from_store()

    # Drop obvious non-lesson seed/test rows.
    DROP = {"newest", "t", "a", "r", "dup_exp", "dup"}
    lessons = [l for l in lessons if l.get("experiment_name") not in DROP]
    total = len(lessons)

    # Reproducible: fixed seed, sorted-by-name population, then sample names.
    SEED = 20260826
    N = 56
    names = sorted(l.get("experiment_name", "") for l in lessons)
    rng = random.Random(SEED)
    chosen = set(rng.sample(names, N))

    print(f"\n=== TOTAL {total} lessons (after dropping {sorted(DROP)}) ===")
    print(f"=== SAMPLE {N} of {total}, seed={SEED}, sorted-by-name population ===")

    # Print ALL 56 compactly: number + name + short REC. Full text readable, gist classifier-runable.
    shown = 0
    for l in lessons:
        if l.get("experiment_name") not in chosen:
            continue
        rec = (l.get("recommendation") or "").strip().replace("\n", " ")
        shown += 1
        print(f"[{shown:02d}] {l.get('experiment_name')} :: {rec[:160]}")
