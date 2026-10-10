"""The meta-harness: replay our own past tasks against candidate harnesses and keep what wins.

Plan: /plans/meta-harness/00-overview.md (outside the repo). Pieces, in build order:

  corpus      (task 03)  scenarios mined from work the agents really did
  replay      (task 04)  run one scenario against one candidate harness, isolated
  graders     (task 05)  functional / non-functional / quality verdicts with intervals
  review      (task 06)  the human final check-off, and the provisional watch
  loop        (task 07)  the candidate archive and the proposer
  memreplay   (task 08)  replay the memory system itself, before and after a lesson
  precompile  (task 09)  lessons into harness primitives
  modes       (task 10)  interpretive vs precompiled
  compress    (task 11)  find the pieces that carry the weight

Everything here writes under `core.paths.state_root()/metaharness/` (gitignored instance
state), never into the repo, and never into the live store from a test.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def home() -> Path:
    """Root of all meta-harness state. Follows state_root(), so AI_SETUP isolates it in tests.
    Trees that predate the per-world home (no state_root) use data_root, which AI_SETUP also
    overrides -- the same place their session_logs live."""
    import core.paths as paths

    root = getattr(paths, "state_root", paths.data_root)()
    p = root / "metaharness"
    p.mkdir(parents=True, exist_ok=True)
    return p
