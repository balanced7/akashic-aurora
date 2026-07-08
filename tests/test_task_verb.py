"""The `agent_cli task` verb: the coordination door over the ledger (arch-triage P1, 2026-07-07).

Wiring test only -- conductor's own lifecycle logic is covered by test_conductor.py. Here we pin that
agent_cli surfaces `task` and delegates verbatim to conductor.main (so the write path is on the ONE
door, not just a standalone script), and that argparse.REMAINDER passes flags through untouched.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import agent_cli


class _Args:
    def __init__(self, rest):
        self.rest = rest


def test_task_delegates_to_conductor(monkeypatch):
    seen = {}
    import core.coord.conductor as conductor

    def fake_main(argv):
        seen["argv"] = argv
        return 0

    monkeypatch.setattr(conductor, "main", fake_main)
    rc = agent_cli.cmd_task(_Args(["done", "T001", "--commit", "abc123", "--verified-by", "pytest"]))
    assert rc == 0
    # REMAINDER is forwarded verbatim -- flags and all -- so conductor owns the verb surface
    assert seen["argv"] == ["done", "T001", "--commit", "abc123", "--verified-by", "pytest"]


def test_task_empty_rest_is_safe(monkeypatch):
    import core.coord.conductor as conductor
    monkeypatch.setattr(conductor, "main", lambda argv: 0 if argv == [] else 99)
    assert agent_cli.cmd_task(_Args(None)) == 0        # None -> [] (no crash, conductor prints usage)


def test_task_verb_is_registered_in_parser():
    """The verb must be reachable through the door (introspect the live subparsers)."""
    verbs = dict(agent_cli.list_verbs())
    assert "task" in verbs
