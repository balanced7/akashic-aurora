"""PRE-REGISTERED ACCEPTANCE (T184) -- an LLM season player that cannot flatter itself.

season_dryrun already ran the whole chain -- plant sealed canaries in a shadow worktree, play,
shape claims, score, adjudicate against the key -- and stated its own limitation: "the default
player is MECHANICAL: it runs check_wiring and reports what the gate names... It cannot tell you
whether a model writes good claims." Season 1 was never blocked on machinery. It was blocked on
PLAYERS, and every prior attempt used seats, which is the path that produced nine seat-tasks and
two findings. This player is a FAN (T181): N stateless leaves, nothing to wedge.

THE TWO WAYS THIS INSTRUMENT COULD LIE TO US, and they are what K2 and K4 exist for:

  K2  by never being SHOWN the hard case. The pre-pass keeps functions whose name occurs at most
      twice. It would be very easy -- and it would look like a sensible optimisation -- to also
      drop candidates whose second reference is call-shaped. That single line would remove every
      `bait` canary (def X; _USED = X()) from the player's view and delete the precision test,
      producing a beautiful score by never asking the question.
  K4  by counting SILENCE as acquittal. A branch that dies on the token ceiling, or a model that
      returns 17 verdicts for 30 candidates, leaves candidates unjudged. Folding those into LIVE
      makes a truncated round look like a clean one -- the same defect as every other absence in
      this arc, wearing a scoreboard.

  K1  the pre-pass keeps low-reference functions and drops well-referenced ones
  K2  a call-shaped second reference is NOT filtered out -- bait must reach the player
  K3  verdicts parse from JSON lines; prose contributes nothing rather than a guess
  K4  candidates the model never mentioned are UNJUDGED, never LIVE
  K5  a dead branch shrinks coverage VISIBLY -- branches_ok < branches is reported
  K6  only DEAD verdicts become claims; LIVE and UNJUDGED never do

Run: py -m pytest tests/test_t184_llm_player_cannot_flatter_itself.py -q
"""
import os
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import season_llm_player as P  # noqa: E402


def _tree(tmp_path, files: dict):
    core = tmp_path / "core"
    core.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (core / name).write_text(textwrap.dedent(body), encoding="utf-8")
    return [str(core / n) for n in files]


def _candidates_over(monkeypatch, tmp_path, files):
    targets = _tree(tmp_path, files)
    monkeypatch.setattr("scripts.canary_oracle._resolve_universe",
                        lambda root: (targets, "test"))
    return {c["name"]: c for c in P.candidates(str(tmp_path))}


def test_k1_low_reference_functions_are_kept_and_popular_ones_dropped(monkeypatch, tmp_path):
    got = _candidates_over(monkeypatch, tmp_path, {
        "a.py": """
            def lonely_one():
                return 1

            def popular():
                return 2
        """,
        "b.py": """
            from core.a import popular
            popular()
            popular()
        """,
    })
    assert "lonely_one" in got, "a name that occurs once must reach the player"
    assert "popular" not in got, "a well-referenced function is not a candidate"


def test_k2_a_call_shaped_second_reference_is_NOT_filtered_out(monkeypatch, tmp_path):
    """THE FLATTERY PIN. Dropping call-shaped references would look like a sensible narrowing
    and would silently remove every bait canary, scoring the player high on a test it was never
    shown. Bait must reach the player and the player must reject it on its own judgment."""
    got = _candidates_over(monkeypatch, tmp_path, {
        "bait.py": """
            def looks_dead():
                return 3


            _USED = looks_dead()
        """,
        "registered.py": """
            def never_invoked():
                return 2


            _HANDLERS = [never_invoked]
        """,
    })
    assert "looks_dead" in got, (
        "bait (def + a real call) MUST be shown to the player -- filtering it out deletes the "
        "precision test and buys a good score by not asking the question")
    assert "never_invoked" in got, "the registered-never-invoked shape must be shown too"
    assert "_USED = looks_dead()" in got["looks_dead"]["window"], (
        "and the window must actually contain the evidence the verdict turns on")


def test_k3_prose_contributes_nothing_rather_than_a_guess():
    good = P._parse('{"name": "a", "verdict": "DEAD", "why": "never called"}\n'
                    '{"name": "b", "verdict": "LIVE", "why": "called below"}')
    assert good["a"]["verdict"] == "DEAD" and good["b"]["verdict"] == "LIVE"
    assert P._parse("I think function a might be dead, but honestly it is hard to say.") == {}
    assert P._parse('{"name": "c", "verdict": "MAYBE"}') == {}, "only DEAD/LIVE are verdicts"
    assert P._parse(None) == {}


def _fake_fan(monkeypatch, branches):
    """Stand in for ask_many with a scripted set of branch results."""
    class _O:
        detail = {"branches": branches, "n_ok": sum(1 for b in branches if b["ok"]),
                  "n": len(branches), "usd": 0.01, "elapsed_s": 1.0}
    monkeypatch.setattr("core.comm.ask.ask_many", lambda *a, **k: _O())


def test_k4_unmentioned_candidates_are_UNJUDGED_never_LIVE(monkeypatch, tmp_path):
    """A model that returns 17 verdicts for 30 candidates has not cleared 13 of them."""
    files = {f"f{i}.py": f"def fn_{i}():\n    return {i}\n" for i in range(4)}
    targets = _tree(tmp_path, files)
    monkeypatch.setattr("scripts.canary_oracle._resolve_universe", lambda root: (targets, "test"))
    _fake_fan(monkeypatch, [{"ok": True, "answer": '{"name": "fn_0", "verdict": "DEAD"}'}])

    dead, rep = P.llm_player(str(tmp_path), batch_size=99)
    assert dead == ["fn_0"]
    assert rep["verdicts_returned"] == 1
    assert rep["unjudged"] == 3, (
        "three candidates were never mentioned; counting them as LIVE would make a truncated "
        "round look like a clean sweep")


def test_k5_a_dead_branch_shrinks_coverage_visibly(monkeypatch, tmp_path):
    files = {f"f{i}.py": f"def fn_{i}():\n    return {i}\n" for i in range(2)}
    targets = _tree(tmp_path, files)
    monkeypatch.setattr("scripts.canary_oracle._resolve_universe", lambda root: (targets, "test"))
    _fake_fan(monkeypatch, [{"ok": False, "answer": None, "why": "length ceiling"},
                            {"ok": True, "answer": '{"name": "fn_1", "verdict": "DEAD"}'}])
    dead, rep = P.llm_player(str(tmp_path), batch_size=1)
    assert rep["branches_ok"] == 1 and rep["branches"] == 2, "the loss must be on the report"
    assert dead == ["fn_1"]


def test_k6_only_dead_verdicts_become_claims(monkeypatch, tmp_path):
    files = {"f.py": "def alpha():\n    return 1\n\n\ndef beta():\n    return 2\n"}
    targets = _tree(tmp_path, files)
    monkeypatch.setattr("scripts.canary_oracle._resolve_universe", lambda root: (targets, "test"))
    _fake_fan(monkeypatch, [{"ok": True, "answer":
                             '{"name": "alpha", "verdict": "LIVE"}\n'
                             '{"name": "beta", "verdict": "DEAD"}'}])
    dead, _rep = P.llm_player(str(tmp_path), batch_size=99)
    assert dead == ["beta"], "a LIVE verdict is not a claim, and neither is silence"
