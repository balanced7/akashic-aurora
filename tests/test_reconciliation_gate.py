"""
T031 hook 1 -- the RECONCILIATION GATE (deepseek's design; the method baseline's lead
forcing function). M1's contract, enforced: a ship that stages files under the
trust/coordination substrate must cite an existing reconciliation artifact, or carry a
LOUD [ungated: reason] escape hatch (auditable at wrap -- skipped-with-reason, never
silent). "Without it, we're just two agents chatting."

Trigger is PATH-BASED, not self-declared (P0's revert-cost anchor: protected prefixes
are where wrongness is expensive). Pre-registered per M3: this file commits before the
checker exists.

Run: py -m pytest tests/test_reconciliation_gate.py -q
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECKER = os.path.join(REPO, "scripts", "checkers", "check_reconciliation_gate.py")


def _run(message, paths, root):
    env = dict(os.environ, AKASHIC_GATE_NO_CEILING="1")   # hermetic: keep subprocess pins
    return subprocess.run(                                # off the production firehose
        [sys.executable, CHECKER, "--root", str(root), message, *paths],
        capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace",
        env=env)


def _spec_root(tmp_path, marker="GATE GREEN by convergence"):
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "some-tier.md").write_text(
        f"# spec\n\nreconciled BUILD SPEC -- {marker}\n", encoding="utf-8")
    (tmp_path / "docs" / "unrelated.md").write_text("just prose\n", encoding="utf-8")
    return tmp_path


def test_unprotected_paths_pass_untouched(tmp_path):
    p = _run("boot render tweak", ["agent_cli.py", "tests/test_x.py"], _spec_root(tmp_path))
    assert p.returncode == 0, p.stdout + p.stderr


def test_protected_path_without_citation_fails(tmp_path):
    p = _run("rework the fold guard", ["core/comm/bus.py"], _spec_root(tmp_path))
    assert p.returncode == 1, "a substrate ship with no reconciliation citation must FAIL"
    assert "core/comm/bus.py" in p.stdout and "reconcil" in p.stdout.lower()


def test_protected_path_with_valid_citation_passes(tmp_path):
    p = _run("L9 built per docs/some-tier.md (GATE GREEN)", ["core/comm/bus.py"],
             _spec_root(tmp_path))
    assert p.returncode == 0, p.stdout + p.stderr


def test_citation_to_missing_artifact_fails(tmp_path):
    p = _run("built per docs/ghost-spec.md", ["core/trust/registry.py"], _spec_root(tmp_path))
    assert p.returncode == 1, "a citation must point at an artifact that EXISTS"
    assert "ghost-spec" in p.stdout


def test_citation_without_reconciliation_marker_fails(tmp_path):
    p = _run("built per docs/unrelated.md", ["core/coord/conductor.py"], _spec_root(tmp_path))
    assert p.returncode == 1, "the cited artifact must actually carry a reconciliation/GATE record"


def test_ungated_escape_hatch_is_loud_not_silent(tmp_path):
    p = _run("hotfix [ungated: prod runner down, revert-clean one-liner]",
             ["core/comm/bus.py"], _spec_root(tmp_path))
    assert p.returncode == 0
    assert "UNGATED" in p.stdout, "the hatch prints an audit line the wrap scorecard reads"
    # an empty reason is not a reason
    p2 = _run("hotfix [ungated: ]", ["core/comm/bus.py"], _spec_root(tmp_path))
    assert p2.returncode == 1, "the hatch requires an actual reason"


def test_runner_scripts_are_substrate(tmp_path):
    """Deepseek verify catch: the runner IS the consume->outcome pipeline; it cannot
    fall outside the prefix net just because it lives under scripts/."""
    p = _run("tweak the fold logic", ["scripts/bifrost_runner_deepseek.py"],
             _spec_root(tmp_path))
    assert p.returncode == 1, "runner scripts are substrate"
    p2 = _run("per docs/some-tier.md (GATE GREEN)",
              ["scripts/bifrost_runner_deepseek.py"], _spec_root(tmp_path))
    assert p2.returncode == 0


def test_ungated_ceiling_holds_the_second_exception(tmp_path, monkeypatch):
    """Deepseek verify: the hatch gets a rate ceiling -- ONE per arc window; the second
    holds until a wrap ruling. In-process with a fake event layer (hermetic)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("recon_gate", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _spec_root(tmp_path)
    events = []

    class FakeEQ:
        def search(self, q, kind=None, since=None, top_k=5):
            return list(events)

    import core.events.event_query as eq_mod
    import core.events.event_log as el_mod
    monkeypatch.setattr(eq_mod, "get_event_query", lambda: FakeEQ())
    monkeypatch.setattr(el_mod, "capture_event",
                        lambda *a, **k: events.append(k) or None)
    monkeypatch.delenv("AKASHIC_GATE_NO_CEILING", raising=False)
    argv = ["prog", "--root", str(tmp_path), "fix [ungated: first exception]",
            "core/comm/bus.py"]
    monkeypatch.setattr(sys, "argv", argv)
    assert mod.main() == 0, "first hatch use passes and consumes the ceiling"
    assert len(events) == 1, "the use is captured durably for the wrap scorecard"
    assert mod.main() == 1, "the second within the window HOLDS -- wrap must rule"


def test_ship_plan_wires_the_gate_before_tests():
    from argparse import Namespace
    import ship
    args = Namespace(message="m", paths=["core/comm/bus.py"], agent="claude",
                     learn_exp=None, tried="", result="", recommend="", anti_pattern="",
                     no_test=False, no_snapshot=False, dry_run=False)
    plan = ship.build_plan(args)
    labels = [l for l, _ in plan]
    gate = next((l for l in labels if "reconciliation" in l), None)
    assert gate and "guard" in gate, f"gate step present as a guard: {labels}"
    assert labels.index(gate) < labels.index("tests (full suite)"), "gate runs BEFORE the suite"
    argv = dict(plan)[gate]
    assert "m" in argv and "core/comm/bus.py" in argv, \
        "the gate sees the ship's message and staged paths"
