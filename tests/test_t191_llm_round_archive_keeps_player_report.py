"""PRE-REGISTERED ACCEPTANCE (T191) -- an LLM round archives its player report.

T190 made claims replayable, but the live LLM seam still attaches ``player_report`` only in
``main()`` *after* ``run()`` has already called ``archive_round``.  The external record therefore
loses branch coverage, exclusions, cost, and reasoning -- the fields a matched fan experiment
needs to explain its score.

The player boundary must carry both products together: ``(names, report)``.  ``run()`` owns the
archive boundary, so it must put the exact report in both the returned result and the record it
hands to the archive.  List-only players remain supported for the mechanical baseline.

  K1  a tuple-returning player places the exact report in the archive record
  K2  the returned round exposes the same report; archive and display cannot diverge
  K3  a legacy list-only player still runs and records no manufactured report

No model call, worktree, key write, or filesystem archive occurs in this pin.

Run: py -m pytest tests/test_t191_llm_round_archive_keeps_player_report.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import season_dryrun as D  # noqa: E402


def _manifest():
    return {
        "universe": {"source": "test", "size": 1},
        "canaries": [
            {"id": "c00_aaa", "cls": "catchable", "name": "dead_aaa", "shape": "test"},
        ],
    }


def _isolate(monkeypatch):
    """Replace every outward seam; retain only player -> run -> archive data flow."""
    from scripts import canary_oracle as C
    from scripts import round_archive as A
    from core.season import scoring as S

    monkeypatch.setattr(D, "_fresh_worktree", lambda _path: None)
    monkeypatch.setattr(C, "plant", lambda *_a, **_k: _manifest())
    monkeypatch.setattr(C, "seal", lambda *_a, **_k: "a" * 64)
    monkeypatch.setattr(C, "verify_seal", lambda *_a, **_k: True)
    monkeypatch.setattr(
        S,
        "score_round",
        lambda *_a, **_k: {"policy": "test", "totals": {"llm": 1}, "unscored": []},
    )

    captured = {}

    def archive(record):
        captured.update(record)
        return "outside-git/round.json"

    monkeypatch.setattr(A, "archive_round", archive)
    return captured


def test_k1_k2_tuple_player_report_reaches_archive_and_return_value(monkeypatch, tmp_path):
    captured = _isolate(monkeypatch)
    report = {
        "branches": 4,
        "branches_ok": 4,
        "shown_names": ["dead_aaa"],
        "verdicts": {"dead_aaa": {"verdict": "DEAD", "why": "no caller"}},
        "usd": 0.0123,
    }

    result = D.run(
        k=1,
        seed=191,
        shadow=str(tmp_path / "shadow"),
        key_path=str(tmp_path / "key.json"),
        player=lambda _shadow: (["dead_aaa"], report),
        player_name="llm",
    )

    assert captured["player_report"] == report, (
        "the archive is the durable evidence; attaching the report later to CLI output is too late"
    )
    assert result["player_report"] == report


def test_k3_list_only_player_remains_compatible(monkeypatch, tmp_path):
    captured = _isolate(monkeypatch)
    result = D.run(
        k=1,
        seed=191,
        shadow=str(tmp_path / "shadow"),
        key_path=str(tmp_path / "key.json"),
        player=lambda _shadow: ["dead_aaa"],
        player_name="mechanical",
    )

    assert "player_report" not in captured
    assert "player_report" not in result
