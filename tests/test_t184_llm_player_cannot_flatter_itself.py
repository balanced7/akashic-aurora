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


def test_k7_a_name_in_a_string_is_not_a_code_reference(monkeypatch, tmp_path):
    """T187, and it is a third way this instrument flattered itself. Counting raw word
    occurrences made the string-dispatch shape score THREE (def, key string, value) and fail the
    <=2 cut, so two of three undetectable canaries were never shown to the player -- and the
    round scored that as the player correctly DECLINING them. Restraint and blindness rendered
    identically. Discounting quoted hits is also the semantically right rule: a bare name inside
    a string is exactly the false wiring signal the A5 class is built from."""
    got = _candidates_over(monkeypatch, tmp_path, {
        "dispatch.py": """
            def string_dispatched():
                return 1


            _DISPATCH = {"string_dispatched": string_dispatched}
        """,
    })
    assert "string_dispatched" in got, (
        "the def, the quoted key and the value are three raw occurrences but only TWO code "
        "references; a filter that cannot tell them apart hides this canary class entirely")


def test_k8_the_filter_reports_what_it_never_showed_the_model(monkeypatch, tmp_path):
    """A candidate the pre-pass dropped was not judged LIVE and was not DECLINED -- it was
    UNSEEN. An adjudicator that cannot distinguish those scores blindness as restraint."""
    files = {"a.py": "def kept():\n    return 1\n",
             "b.py": "def popular():\n    return 2\n",
             "c.py": "from core.b import popular\npopular()\npopular()\npopular()\n"}
    targets = _tree(tmp_path, files)
    monkeypatch.setattr("scripts.canary_oracle._resolve_universe", lambda root: (targets, "test"))
    _fake_fan(monkeypatch, [{"ok": True, "answer": '{"name": "kept", "verdict": "DEAD"}'}])
    _dead, rep = P.llm_player(str(tmp_path), batch_size=99)
    assert rep["excluded_by_filter"] >= 1
    assert "popular" in rep["excluded_names"], (
        "the round must be able to say WHICH candidates the player never saw")


def test_k9_the_canary_fixtures_no_longer_state_their_own_answers():
    """T186. Every template docstring used to describe its class -- 'Registered in a table that
    nothing ever invokes', 'Fan-out path -- unreachable', 'Looks dead; is called below'. The
    first LLM player's correct verdict quoted one of them verbatim. A harness that grades on
    label-reading measures reading, not analysis."""
    from scripts import canary_oracle as C
    for pool in (C._CATCHABLE, C._UNDETECTABLE, C._BAIT):
        for tmpl, _shape in pool:
            assert '"""Helper."""' in tmpl, f"template still self-describes: {tmpl[:70]!r}"
    leaks = ("unreachable", "never invokes", "Looks dead", "string dispatch", "Fallback")
    blob = "".join(t for pool in (C._CATCHABLE, C._UNDETECTABLE, C._BAIT) for t, _ in pool)
    for word in leaks:
        assert word not in blob, f"{word!r} still leaks the class into the fixture"


def test_k6_only_dead_verdicts_become_claims(monkeypatch, tmp_path):
    files = {"f.py": "def alpha():\n    return 1\n\n\ndef beta():\n    return 2\n"}
    targets = _tree(tmp_path, files)
    monkeypatch.setattr("scripts.canary_oracle._resolve_universe", lambda root: (targets, "test"))
    _fake_fan(monkeypatch, [{"ok": True, "answer":
                             '{"name": "alpha", "verdict": "LIVE"}\n'
                             '{"name": "beta", "verdict": "DEAD"}'}])
    dead, _rep = P.llm_player(str(tmp_path), batch_size=99)
    assert dead == ["beta"], "a LIVE verdict is not a claim, and neither is silence"
