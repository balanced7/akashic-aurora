"""Pin: bootstrap.py's status check is READ-ONLY (lesson bootstrap_status_is_stateful).

The defect (found by codex_frontier_019f6e7e on its FIRST boot, 2026-07-17): the docstring
promises an "honest status check" but every run called core.narrative.session.start_session(),
which CLOSES any still-open narrative session fleet-wide and re-chronicles it, then
promote_salient(). A stranger checking status mutated the incumbents' narrative state --
names-that-lie in the first file a newcomer touches; incumbents were blind because they
never run it. Fix: mutation moves behind an explicit --start-session flag.

Offline: fake narrative modules are injected into sys.modules; the pins prove presence or
absence of the mutation call, not narrative behavior itself.
"""
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bootstrap


class _Recorder:
    def __init__(self):
        self.start_calls = 0
        self.promote_calls = 0

    def install(self, monkeypatch):
        session = types.ModuleType("core.narrative.session")

        def start_session():
            self.start_calls += 1
            return {"closed_prior": False}

        session.start_session = start_session
        promoter = types.ModuleType("core.narrative.event_promoter")

        def promote_salient():
            self.promote_calls += 1
            return {"promoted": 0}

        promoter.promote_salient = promote_salient
        monkeypatch.setitem(sys.modules, "core.narrative.session", session)
        monkeypatch.setitem(sys.modules, "core.narrative.event_promoter", promoter)


def test_build_parser_defaults_are_read_only():
    args = bootstrap.build_parser().parse_args([])
    assert args.start_session is False
    assert args.brief is False


def test_status_run_never_touches_the_narrative_spine(monkeypatch, capsys):
    """THE PIN: a plain status run performs ZERO narrative mutation."""
    rec = _Recorder()
    rec.install(monkeypatch)
    bootstrap.run(bootstrap.build_parser().parse_args(["--brief"]))
    out = capsys.readouterr().out
    assert rec.start_calls == 0, "status check called start_session() -- the defect is back"
    assert rec.promote_calls == 0
    assert "read-only" in out.lower()


def test_start_session_flag_opts_into_the_mutation(monkeypatch, capsys):
    rec = _Recorder()
    rec.install(monkeypatch)
    bootstrap.run(bootstrap.build_parser().parse_args(["--brief", "--start-session"]))
    assert rec.start_calls == 1
    assert rec.promote_calls == 1


def test_agent_init_path_stays_pure(monkeypatch, capsys):
    rec = _Recorder()
    rec.install(monkeypatch)
    bootstrap.run(bootstrap.build_parser().parse_args(["--agent-init"]))
    out = capsys.readouterr().out
    assert rec.start_calls == 0
    assert '"you_are"' in out
