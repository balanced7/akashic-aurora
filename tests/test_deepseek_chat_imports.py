"""Pin: deepseek_chat must be able to RESOLVE every clarify-path name it uses (2026-08-01).

The runner died live -- 'NameError: CLARIFY_TIMEOUT_S is not defined', two attempts, no reply --
while holding the cold-question-battery RUNNER role. Root cause: the compat re-export imported
CLARIFY_MAX_PER_TASK from core.comm.toolbox but not CLARIFY_TIMEOUT_S, and the clarification
TIMEOUT branch references it. The happy path never touches the name, so the crash only fires
when a clarification goes unanswered -- a latent branch bomb that no smoke test walks.

Run: py -m pytest tests/test_deepseek_chat_imports.py -q
"""
import ast
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def test_every_toolbox_constant_used_is_imported():
    """Shape-proof: parse the source; any NAME used that toolbox exports must be imported.
    (Not literal-coupled to CLARIFY_TIMEOUT_S -- the defect class is 'compat re-export
    drifted behind its own callers', and the next missing name should fail here too.)"""
    import core.comm.toolbox as tb
    src_path = os.path.join(REPO, "scripts", "deepseek_chat.py")
    tree = ast.parse(open(src_path, encoding="utf-8").read())

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "core.comm.toolbox":
            imported |= {a.name for a in node.names}

    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    exported_constants = {n for n in dir(tb) if n.isupper()}

    missing = (used & exported_constants) - imported
    assert not missing, (
        f"deepseek_chat.py uses toolbox constant(s) it never imports: {sorted(missing)} -- "
        "this is the NameError class that killed the runner mid-battery"
    )
