"""W0.5/W0.6 pins (RED first): the scene, and the door that answers with one.

SPEC: `research/in-flight/context-system-navi-m2.md` (Navi, E1), rows W0.5 and W0.6 of
      `fences/context-system/reconciliation.md` section 4. Anchors are `context.target.v1` (W0.1).

WHY THIS EXISTS, in Daniel's words, and it is the acceptance test for the whole wave:

    "when the design is finished I won't have to remind you whats related to what and the
     importance of it, you will be able to see it."

A scene is the answer to one anchor across every plane that knows anything about it. The hard part
is not joining the planes; it is that a plane which knows nothing and a plane which CANNOT KNOW
must not render the same way. That is the entire reason the state field exists and why these pins
spend most of their weight on it.

THE FOUR STATES ARE THE SPEC'S OWN, and the distinction they protect has cost this house
repeatedly: `ok` (joined, has rows), `empty` (asked, genuinely nothing), `UNCHECKABLE` (could not
ask, with the reason), `error` (asked and it broke). Collapsing the middle two into "0 results" is
the failure the reach map measures and the one `touch_stats` committed against itself tonight.

TWO PLANES ARE LIVE IN THIS SLICE, git and touches, because those are the two with real data behind
them today. The other four resolve to UNCHECKABLE carrying the reason, which is the honest shape
rather than a stub: the scene is complete and says exactly what it could not reach.

Hermetic: resolvers are injected. The two live ones get their own pins against real repo data.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import target as T      # noqa: E402
from core.coord import scene as S       # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = T.Roots(main="E:/AI-Setup")


def plane(name, **kw):
    return {"plane": name, "state": "ok", "summary": "s", "rows": [],
            "cost": {"class": "o1", "note": "n"}, "fog": "", "receipts": [], **kw}


# ---------------------------------------------------------------- the envelope
def test_the_schema_name_is_the_sealed_one():
    assert S.SCHEMA == "context.scene.v1"


def test_the_state_set_is_closed_and_separates_empty_from_uncheckable():
    assert set(S.STATES) == {"ok", "empty", "UNCHECKABLE", "error"}


def test_a_scene_carries_every_field_the_spec_names():
    sc = S.build("file:core/coord/target.py", subject="claude", roots=ROOTS, resolvers={})
    for f in ("schema", "subject", "anchor", "level", "generated_at", "planes",
              "span", "fog", "epistemic", "drill", "effects"):
        assert f in sc, f


def test_effects_is_always_empty_because_a_context_read_performs_none():
    sc = S.build("file:core/coord/target.py", subject="claude", roots=ROOTS, resolvers={})
    assert sc["effects"] == []


def test_the_anchor_is_the_parsed_target_not_the_raw_string():
    sc = S.build("core/coord/target.py:42", subject="claude", roots=ROOTS, resolvers={})
    a = sc["anchor"]
    assert a["address"] == "core/coord/target.py:42"
    assert a["kind"] == "file_line"
    assert a["work"] is None


def test_a_question_anchor_is_named_and_routed_never_resolved_as_a_path():
    sc = S.build("why does recall miss at the moment of action?", subject="claude",
                 roots=ROOTS, resolvers={})
    assert sc["anchor"]["kind"] == "question"
    assert "cast" in sc["drill"]


def test_a_refused_anchor_fails_loudly_rather_than_producing_an_empty_scene():
    with pytest.raises(T.TargetError):
        S.build("sha:not-hex", subject="claude", roots=ROOTS, resolvers={})


# ---------------------------------------------------------------- the four states
def test_a_plane_with_rows_is_ok():
    r = {"git": lambda a, **k: plane("git", rows=[{"ref": "sha:" + "a" * 40, "at": "t",
                                                   "who": "w", "what": "x"}])}
    sc = S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, exists=lambda k: True)
    assert sc["planes"][0]["state"] == "ok"


def test_a_plane_that_was_asked_and_found_nothing_is_empty_not_uncheckable():
    r = {"git": lambda a, **k: plane("git", state="empty", rows=[])}
    sc = S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, exists=lambda k: True)
    p = sc["planes"][0]
    assert p["state"] == "empty" and p["rows"] == []


def test_a_plane_that_could_not_be_asked_is_uncheckable_and_carries_the_reason():
    r = {"lessons": lambda a, **k: plane("lessons", state="UNCHECKABLE", rows=[],
                                         fog="39 of 1,526 lessons carry files_affected")}
    sc = S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, exists=lambda k: True)
    p = sc["planes"][0]
    assert p["state"] == "UNCHECKABLE" and p["fog"]


def test_an_uncheckable_plane_without_a_reason_is_itself_refused():
    """A plane may say it could not look. It may not say so without saying why -- that is how
    UNCHECKABLE decays back into a silent zero."""
    r = {"lessons": lambda a, **k: plane("lessons", state="UNCHECKABLE", fog="")}
    with pytest.raises(ValueError):
        S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, exists=lambda k: True)


def test_a_resolver_that_raises_becomes_an_error_plane_never_a_missing_one():
    def boom(a, **k):
        raise RuntimeError("redis is down")
    sc = S.build("file:x.py", subject="c", roots=ROOTS, resolvers={"touches": boom},
                 exists=lambda k: True)
    p = sc["planes"][0]
    assert p["state"] == "error" and "redis is down" in p["fog"]


def test_an_unknown_state_is_refused_rather_than_passed_through():
    r = {"git": lambda a, **k: plane("git", state="probably fine")}
    with pytest.raises(ValueError):
        S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, exists=lambda k: True)


def test_every_plane_the_scene_knows_about_appears_even_when_it_cannot_answer():
    # A plane that is simply absent from the output is indistinguishable from one that does not
    # exist, and the reader cannot tell which planes were consulted.
    sc = S.build("file:core/coord/target.py", subject="c", roots=ROOTS, resolvers={})
    assert {p["plane"] for p in sc["planes"]} == set(S.PLANES)


# ---------------------------------------------------------------- rows carry refs, or go to fog
def test_every_row_carries_a_ref_the_doors_can_resolve():
    r = {"git": lambda a, **k: plane("git", rows=[
        {"ref": "sha:" + "b" * 40, "at": "t", "who": "w", "what": "x"}])}
    sc = S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, exists=lambda k: True)
    for row in sc["planes"][0]["rows"]:
        T.parse(row["ref"], roots=ROOTS, exists=lambda k: True)       # must not raise


def test_a_row_whose_ref_cannot_be_minted_goes_to_fog_never_into_rows():
    r = {"git": lambda a, **k: plane("git", rows=[
        {"ref": "", "at": "t", "who": "w", "what": "unaddressable"}])}
    sc = S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, exists=lambda k: True)
    p = sc["planes"][0]
    assert p["rows"] == [] and "unaddressable" in p["fog"]


# ---------------------------------------------------------------- levels
def test_level_zero_carries_summaries_and_no_rows():
    r = {"git": lambda a, **k: plane("git", rows=[{"ref": "sha:" + "c" * 40, "at": "t",
                                                   "who": "w", "what": "x"}])}
    sc = S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, level=0, exists=lambda k: True)
    assert sc["planes"][0]["summary"] and sc["planes"][0]["rows"] == []


def test_level_two_carries_the_receipts_level_one_omits():
    r = {"git": lambda a, **k: plane("git", rows=[{"ref": "sha:" + "d" * 40, "at": "t",
                                                   "who": "w", "what": "x"}],
                                     receipts=["git log -- x.py"])}
    one = S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, level=1, exists=lambda k: True)
    two = S.build("file:x.py", subject="c", roots=ROOTS, resolvers=r, level=2, exists=lambda k: True)
    assert one["planes"][0]["receipts"] == [] and two["planes"][0]["receipts"]


# ---------------------------------------------------------------- the two live planes
def test_the_git_plane_answers_for_a_real_tracked_file():
    sc = S.build("file:core/coord/target.py", subject="claude", roots=ROOTS, level=1)
    g = [p for p in sc["planes"] if p["plane"] == "git"][0]
    assert g["state"] == "ok", g
    assert g["rows"], "a file committed tonight must have git history"
    assert all(r["ref"].startswith("sha:") for r in g["rows"])


def test_the_git_plane_is_empty_not_error_for_a_path_with_no_history():
    sc = S.build("file:core/coord/this_file_does_not_exist_9f3a.py", subject="claude",
                 roots=ROOTS, level=1)
    g = [p for p in sc["planes"] if p["plane"] == "git"][0]
    assert g["state"] == "empty"


def test_the_touches_plane_reads_the_spine_and_refs_each_event():
    sc = S.build("file:core/coord/target.py", subject="claude", roots=ROOTS, level=1)
    t = [p for p in sc["planes"] if p["plane"] == "touches"][0]
    assert t["state"] in ("ok", "empty")
    for row in t["rows"]:
        assert row["ref"].startswith("event:")


# ---------------------------------------------------------------- the render
def test_the_level_zero_render_is_one_line_per_plane_and_names_every_state():
    sc = S.build("file:core/coord/target.py", subject="claude", roots=ROOTS, level=0)
    out = S.render(sc)
    for p in S.PLANES:
        assert p in out
    assert "UNCHECKABLE" in out, "a plane that could not be reached must be visible in the render"
