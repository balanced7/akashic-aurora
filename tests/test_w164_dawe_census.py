"""W164 pins: the Dawe bar, made mechanical -- and kept from overclaiming.

The house adopted the bar 2026-08-13 from the Clarke & Dawe Glenn Stevens sketches: a RESPONSE
that is not an ANSWER is a defect. This is the first tool built on it, and most of these pins
exist to stop the tool from committing the failure it is named after.

A fan branch proposed flagging verbs that print without returning a value. For a CLI verb that
is NORMAL -- print is the output channel, the exit code is the return. Calling those defective
would assert a quality judgement the evidence cannot carry. So the census reports
VERIFIABILITY: a large body with no helper seam and no value-returning path has fetch,
transform and render fused, which is not proof of a bad answer but is proof that no seam
exists at which an answer could be inspected, tested or reused.
"""
from core.coord import dawe_census as D

FUSED_BIG = "def cmd_big():\n" + "\n".join(f"    print({i})" for i in range(120))
SEAMED_BIG = ("def _helper():\n    return 1\n\n"
              "def cmd_seamed():\n    x = _helper()\n"
              + "\n".join(f"    print({i})" for i in range(120)))
ANSWERING_BIG = ("def cmd_answers():\n"
                 + "\n".join(f"    print({i})" for i in range(118))
                 + "\n    return {'rows': 1}\n")
FUSED_SMALL = "def cmd_small():\n    print(1)\n    print(2)\n"


def test_d1_a_large_fused_verb_is_flagged_unverifiable():
    s = D.survey(FUSED_BIG)[0]
    assert s.fused is True and s.unverifiable is True


def test_d2_a_helper_seam_clears_it_however_large():
    """One call to a local helper is a seam: the answer exists somewhere inspectable."""
    s = [v for v in D.survey(SEAMED_BIG) if v.name == "cmd_seamed"][0]
    assert s.helper_calls >= 1
    assert s.unverifiable is False


def test_d3_a_value_returning_path_clears_it_however_large():
    """Returning a value IS the answer seam -- something outside can consume and check it."""
    s = D.survey(ANSWERING_BIG)[0]
    assert s.value_returns == 1
    assert s.unverifiable is False


def test_d4_a_bare_return_or_return_None_is_an_EXIT_not_an_answer():
    """The distinction the whole census rests on: leaving a function is not answering."""
    src = "def cmd_x():\n    print(1)\n    if 1:\n        return\n    return None\n"
    s = D.survey(src)[0]
    assert s.value_returns == 0


def test_d5_a_SMALL_fused_verb_is_not_flagged():
    """Fusion only hides something when the body is too big to read whole. A 3-line verb
    with no seam is legible, and flagging it would be noise that trains readers to ignore
    the census -- the crying-wolf failure this arc hit three times."""
    s = D.survey(FUSED_SMALL)[0]
    assert s.fused is True
    assert s.unverifiable is False


def test_d6_the_render_states_that_it_measures_VERIFIABILITY_not_quality():
    """The tool must not assert what its evidence cannot carry -- that would be the exact
    Dawe failure, committed by the instrument named after it."""
    out = D.render(D.survey(FUSED_BIG)).lower()
    assert "verifiability" in out and "never quality" in out


def test_d7_an_empty_finding_says_so_rather_than_going_quiet():
    """Silence is indistinguishable from a census that failed to run."""
    out = D.render(D.survey(FUSED_SMALL))
    assert "nothing to report" in out


def test_d8_the_real_monolith_comes_back_CLEAN_and_that_is_the_finding():
    """RECORDS A DISPROVEN PREDICTION, deliberately.

    A fan branch predicted six verbs (991 lines) would flag: cmd_eye, cmd_resident,
    cmd_recall_curate, cmd_sift, cmd_mailbox, cmd_bifrost_send -- reasoning from a digest
    line that said 65 of 87 verbs "call no local helper". The census flags NONE of them.

    Because "no LOCAL helper" was never "no seam". Measured after the census disagreed:
    cmd_eye has 0 local helpers and 79 imported-function calls plus 50 method calls; it
    calls _UG, _render, Bus, ask_many. Those verbs are thin shells delegating into core/,
    which is the architecture you would want, not fused bodies hiding logic.

    The digest I fed the fan was accurate and its FRAMING was not: columns headed
    "self-contained; cheapest to extract" state a conclusion, and the fan reasoned from the
    conclusion rather than the number. This pin exists so the correction survives the
    conversation that produced it."""
    from core.paths import repo_root
    src = (repo_root() / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    shapes = D.survey(src)
    assert len(shapes) >= 80, f"expected ~87 cmd_* verbs, surveyed {len(shapes)}"
    flagged = [s.name for s in shapes if s.unverifiable]
    assert not flagged, (
        f"verbs are now structurally unverifiable: {flagged}. If that is real, good -- the "
        f"census earned its keep. Update this pin with the reason rather than deleting it.")


# --------------------------------------------------------------- silent degradation

GUARD_SILENT = "def f():\n    try:\n        from core.x import y\n    except Exception:\n        pass\n"
GUARD_LOUD = ("def g():\n    try:\n        from core.x import y\n"
              "    except Exception as e:\n        print('x unavailable', e)\n")
GUARD_RERAISE = ("def h():\n    try:\n        from core.x import y\n"
                 "    except Exception:\n        raise\n")


def test_s1_a_swallowed_import_is_classified_silent():
    g = D.survey_import_guards(GUARD_SILENT)[0]
    assert g.handler == "silent" and g.enclosing == "f"
    assert "core.x" in g.modules


def test_s2_a_handler_that_says_something_is_LOUD():
    """The distinction the census rests on: a loud handler classifies ITSELF as deliberate.
    A bare pass cannot, which is why the silent ones are the unauditable class."""
    assert D.survey_import_guards(GUARD_LOUD)[0].handler == "loud"


def test_s3_a_reraise_is_neither_silent_nor_loud():
    assert D.survey_import_guards(GUARD_RERAISE)[0].handler == "reraise"


def test_s4_a_try_block_with_no_import_is_not_surveyed():
    """Scope discipline: this census is about IMPORT guards, not every try in the file."""
    assert D.survey_import_guards("def f():\n    try:\n        x = 1\n    except Exception:\n        pass\n") == []


def test_s5_the_render_refuses_to_call_the_silent_ones_bugs():
    """Some are deliberate and correct -- 'boot must never fail' is a real design choice.
    The finding is that nothing distinguishes deliberate from accidental, not that 42 sites
    are wrong. A census that overclaimed here would be the failure it is named after."""
    out = D.render_import_guards(D.survey_import_guards(GUARD_SILENT)).lower()
    assert "deliberate" in out
    assert "bug" not in out


def test_s6_the_real_monolith_shows_BOTH_kinds_which_is_the_finding():
    """Measured 2026-08-14: 67 guards, 42 silent, 25 loud. The 25 are the argument -- the
    house already knows how to announce a failed optional import, so the 42 are drift rather
    than a uniform policy. If loud ever reaches 0 this pin should fail and be re-read."""
    from core.paths import repo_root
    src = (repo_root() / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    guards = D.survey_import_guards(src)
    silent = [g for g in guards if g.handler == "silent"]
    loud = [g for g in guards if g.handler == "loud"]
    assert len(guards) >= 40, f"only {len(guards)} import guards surveyed"
    assert silent and loud, "both kinds must exist for the drift argument to hold"
