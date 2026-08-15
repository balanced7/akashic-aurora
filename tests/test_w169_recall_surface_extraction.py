"""W169 slice 1: the recall surface leaves agent_cli.

THE DECIDING EVIDENCE, measured rather than argued (2026-08-15): of the eight verbs in the
recall cluster, exactly three reference NOTHING from agent_cli's module scope --
cmd_recall_at, cmd_recall_feedback, cmd_recall_curate. The other five reach for _clip,
_intake, _MAX, _MAX_NOTE, _collapsed_learn_fields or project_notes, and those helpers are
the actual seam. So this slice moves the three that are already free and leaves the
coupled five where they are; migrating a helper is a DIFFERENT slice with a different risk.

WHY THIS SHAPE CANNOT DROP A VERB, which is the whole fear behind extracting from an
8,336-line door: build_parser binds by OBJECT (`rf.set_defaults(fn=cmd_recall_feedback)`),
not by name lookup at dispatch time. Import the moved function at agent_cli's TOP level and
the name resolves to the same object it always did, so the binding is byte-identical work.
The pins below assert exactly that -- identity, not merely presence -- because a test that
only checked "some callable is bound" would pass against a re-implemented stub.

REVERT: delete one import line and one file.
"""
import ast
import importlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOVED = ("cmd_recall_at", "cmd_recall_feedback", "cmd_recall_curate")


def test_w169_a_the_surface_module_exists_and_exposes_the_three_moved_verbs():
    surface = importlib.import_module("core.recall.surface")
    missing = [n for n in MOVED if not callable(getattr(surface, n, None))]
    assert not missing, f"core.recall.surface is missing {missing}"


def test_w169_b_agent_cli_no_longer_defines_them_itself():
    """A MOVE, not a copy. Two definitions is how a fix lands in one of them and not the other."""
    tree = ast.parse((REPO / "agent_cli.py").read_text(encoding="utf-8"))
    defined = {
        n.name for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name in MOVED
    }
    assert not defined, f"agent_cli.py still defines {sorted(defined)} -- this is a copy, not a move"


@pytest.mark.parametrize("name", MOVED)
def test_w169_c_agent_cli_rebinds_the_very_same_object(name):
    """Identity, not presence. This is the pin that proves no verb silently changed meaning."""
    import agent_cli
    surface = importlib.import_module("core.recall.surface")
    assert getattr(agent_cli, name) is getattr(surface, name)


@pytest.mark.parametrize("verb,func", [
    ("recall-at", "cmd_recall_at"),
    ("recall-feedback", "cmd_recall_feedback"),
    ("recall-curate", "cmd_recall_curate"),
])
def test_w169_d_the_verb_still_dispatches_through_the_real_parser(verb, func):
    """Zero verb drop, asserted at the door the operator actually types into."""
    import agent_cli
    surface = importlib.import_module("core.recall.surface")
    parser = agent_cli.build_parser()
    args = parser.parse_args([verb] + (["--source", "x"] if verb == "recall-feedback" else []))
    assert getattr(args, "fn", None) is getattr(surface, func)
