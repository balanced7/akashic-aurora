"""Benchmark: the recall tokenizer in Python vs Rust (aurora_rs).

Measures learning_store._tokens_of_py against aurora_rs.tokens_of on a synthetic corpus shaped
like stored lessons (a few hundred words of mixed prose, paths and identifiers each), the
work `recall` repeats over every lesson per query. Needs the wheel in the environment:

    uvx --from 'maturin>=1.9,<2' maturin develop --release -m aurora-rs/py/Cargo.toml --uv
    uv run python aurora-rs/bench.py [--lessons 2000]
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.learning.learning_store import _tokens_of_py  # sys.path bootstrap

WORDS = [
    "recall",
    "lesson",
    "promotion",
    "consolidation",
    "tracks",
    "salience",
    "redis",
    "embedded",
    "store",
    "ledger",
    "hooks",
    "install",
    "uninstall",
    "settings",
    "statement",
    "state",
    "states",
    "stating",
    "agent_cli.py",
    "core/learning",
    "learning_store.py",
    "boot",
    "learn",
    "note",
    "handoff",
    "bifrost",
    "presence",
    "world",
    "prod",
    "alpha",
    "beta",
]


def corpus(n: int, seed: int = 7) -> list[str]:
    rnd = random.Random(seed)
    return [" ".join(rnd.choice(WORDS) for _ in range(rnd.randint(120, 400))) for _ in range(n)]


def timed(fn, docs: list[str], rounds: int) -> float:
    best = float("inf")
    for _ in range(rounds):
        t0 = time.perf_counter()
        for d in docs:
            fn(d)
        best = min(best, time.perf_counter() - t0)
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description="Benchmark the recall tokenizer: Python vs Rust.")
    ap.add_argument("--lessons", type=int, default=2000)
    ap.add_argument("--rounds", type=int, default=5)
    a = ap.parse_args()
    try:
        import aurora_rs  # pyright: ignore[reportMissingImports]  # optional wheel
    except ImportError:
        print("aurora_rs is not installed; see the docstring for how to build it.")
        return 1
    docs = corpus(a.lessons)
    assert all(aurora_rs.tokens_of(d) == _tokens_of_py(d) for d in docs[:200]), "parity broke"
    py = timed(_tokens_of_py, docs, a.rounds)
    rs = timed(aurora_rs.tokens_of, docs, a.rounds)
    print(f"{a.lessons} lessons, best of {a.rounds}:")
    print(f"  python  {py * 1e3:8.1f} ms")
    print(f"  rust    {rs * 1e3:8.1f} ms   ({py / rs:.1f}x faster)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
