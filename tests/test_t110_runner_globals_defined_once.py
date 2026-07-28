"""T110b -- A RUNNER'S SHARED STATE IS DEFINED EXACTLY ONCE. RED first (M3).

Found by the T110 sweep, in the one file with a documented history of exactly
this injury.

scripts/bifrost_runner_deepseek.py assigns three module-level shared-state
names TWICE, 1,240 lines apart:

    _token_deltas   line 146  and  line 1390
    _token_journal  line 151  and  line 1391
    _RUN_STATS      line 153  and  line 1392

Both blocks execute at import, top to bottom, so the LAST one wins. Today the
second block assigns the same empty values the first did, which is why nothing
is visibly broken -- `_token_deltas = {}` twice yields an empty dict either
way. It is inert, and it is a loaded gun:

  * the responder closure and _process_one both resolve these names at CALL
    time, so they follow whichever binding import finished with;
  * the moment anyone gives the FIRST block a real initial value -- loading
    today's journal at import, seeding _RUN_STATS from a resume file, wiring
    _token_deltas to a shared structure -- the trailing block silently discards
    it, and the failure surfaces as a meter that reads zero rather than as an
    error;
  * that is not hypothetical. tests/test_t078_w1_meter_actually_records.py
    exists because `_token_journal` in THIS FILE was once bound function-local
    while the module global stayed None, and the meter recorded 0 tokens for an
    entire process lifetime while printing healthy-looking lines. Same name,
    same file, same failure signature, different mechanism.

An inert defect in a file that has already been bitten by its exact failure
mode is a defect, not a curiosity. Daniel's standing rule is that a reproducible
defect gets fixed at the root rather than annotated as a known limitation.

  P1  NO MODULE-LEVEL NAME IS ASSIGNED TWICE in any runner. Structural and
      swept across all three runners at once -- kimi and sol are clean today
      and this keeps them that way, which is the whole lesson of
      fix_a_class_carry_it_to_every_sibling_file.
"""

import ast
import collections
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNERS = ["scripts/bifrost_runner_deepseek.py",
           "scripts/bifrost_runner_kimi.py",
           "scripts/bifrost_runner_sol.py"]


def _module_level_assignments(path):
    """name -> [line, ...] for every top-level assignment. Only module scope:
    re-binding inside a function is ordinary local behaviour."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    seen = collections.defaultdict(list)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for t in targets:
            if isinstance(t, ast.Name):
                seen[t.id].append(node.lineno)
    return seen


@pytest.mark.parametrize("rel", RUNNERS)
def test_p1_no_runner_global_is_defined_twice(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        pytest.skip(f"{rel} absent")
    dupes = {k: v for k, v in _module_level_assignments(path).items() if len(v) > 1}
    assert not dupes, (
        f"DUPLICATE MODULE-LEVEL STATE in {rel}: {dupes}. Both assignments run at "
        f"import and the last one wins, so any real initial value in the first block "
        f"is silently discarded -- surfacing later as a meter reading zero, not as an "
        f"error. This file has already lost a whole process's token accounting to a "
        f"binding mistake on one of these exact names (T078 W1). Keep one definition.")
