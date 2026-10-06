"""The CREDIT JOIN is blind to 98% of failures, and the blindness is a key-shape bug.

THE DEFECT, measured on real data (scripts/measure_target_join.py, 2026-10-06):
17,606 of 18,024 distinct `recall:outcome` keys (97.7%) are `c:` COMMAND keys. A command
key is the WHOLE LITERAL command string, lowercased and whitespace-collapsed
(`normalize_target`, core/recall/at_action.py:988). The credit loop then joins on that key
three times -- `_set_outcome`, `_get_outcome`, `_impressions_for` -- all by exact equality.

So consider the only interesting case in the whole system, an agent fixing its own mistake:

    py agent_cli.py boot claude --taks "x"     -> FAIL   (key A)
    py agent_cli.py boot claude --task "x"     -> SUCCESS (key B, A != B)

The FAIL is filed under A and the SUCCESS asks about B. They never meet. No flip, no
credit, and -- worse -- no record that a lesson prevented anything. A FIXED COMMAND CAN
NEVER JOIN ITS OWN EARLIER FAILURE. The 115 failures in the session that motivated this,
113 of them on commands, could not close the loop even in principle.

WHY THE FIX IS A SECOND AXIS AND NOT A COARSER `normalize_target`. The obvious move --
make the primary key coarser -- is wrong, and a pinned contract already says so:
`core/recall/replay.py:128 parse_target` INVERTS `normalize_target` to replay a historical
target through the live matcher, and `tests/test_forge_replay.py:85` pins that inversion.
Coarsening the primary key would feed the replay bench truncated commands while reporting
success. Twenty-odd other call sites share that key shape too.

So `coarse_target` is an ADDITIONAL join axis, and every credit it wins is STAMPED with
the axis that won it (`join`: "exact" | "coarse"). That stamp is the point. Credit here is
already assigned "with no causal check" (core/recall/prevention.py:57); a coarser key
raises recall AND raises false joins, so a sensor that cannot say which axis fired would
trade one blindness for a quieter one. With the stamp, the coarse share is auditable and
the exact path stays byte-for-byte what it was.

  J1  coarse_target drops flags and their values -- the two spellings above agree
  J2  it drops the house `cd <repo> &&` prefix and pipeline tails
  J3  it drops heredoc BODIES (a 40-line heredoc is not an identity)
  J4  it keeps identity: different executable or different file argument NEVER join
  J5  a path key needs no second axis, and neither does an already-minimal command
  J6  THE LOOP CLOSES: fail on one spelling, succeed on another, the lesson is credited
  J7  the credit names the axis that won it, and the exact path still reports "exact"
  J8  consume-on-credit still holds across the axes -- one flip cannot be farmed twice
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall import at_action


def _sid():
    return "jointest-" + uuid.uuid4().hex[:10]


def _c(cmd):
    return at_action.normalize_target(command=cmd)


# ---------------------------------------------------------------- the coarsener

def test_j1_flags_and_their_values_are_dropped():
    """The typo case, which is the whole reason this slice exists."""
    bad = at_action.coarse_target(_c('py agent_cli.py boot claude --taks "memory reach"'))
    good = at_action.coarse_target(_c('py agent_cli.py boot claude --task "memory reach"'))
    assert bad and bad == good, "a flag typo must not change the join key"
    assert "--task" not in good and "--taks" not in good
    assert "memory" not in good, "a flag VALUE is not identity either"
    assert good.endswith("boot claude"), f"the action survives coarsening: {good!r}"


def test_j2_cd_prefix_and_pipeline_tail_are_dropped(monkeypatch):
    """`cd /e/AI-Setup && real-command | head -40` is the house's own idiom.

    This pin also covers the ASYMMETRIC case, which is the one that bites: the fix for a
    broken command is often its MINIMAL spelling, so a minimal command must still carry a
    coarse axis or it can never reach the record its dressed failure left behind.
    """
    plain = at_action.coarse_target(_c("py scripts/measure_target_join.py"))
    dressed = at_action.coarse_target(
        _c("cd /e/AI-Setup && py scripts/measure_target_join.py --json | tail -40"))
    assert plain and plain == dressed, f"{plain!r} != {dressed!r}"

    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid = _sid()
    at_action.mark_impression(sid, _c("cd /e/AI-Setup && py x.py --bad | tail -5"),
                              ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, _c("cd /e/AI-Setup && py x.py --bad | tail -5"), False)
    res = at_action.resolve_action_outcome(sid, _c("py x.py"), True)
    assert res["flipped"] is True and res["credited"] == 1, \
        "a minimal fix must join its own dressed failure"


def test_j3_heredoc_bodies_are_dropped():
    a = _c("cat > notes.txt <<'EOF'\nfirst body\nEOF")
    b = _c("cat > notes.txt <<'EOF'\na completely different body\nEOF")
    ca, cb = at_action.coarse_target(a), at_action.coarse_target(b)
    assert ca and ca == cb, "the heredoc BODY is payload, not identity"


def test_j4_identity_is_preserved_different_actions_never_join(monkeypatch):
    """The false-credit guard. Coarsening that collapses real actions is worse than
    blindness, because a false join credits a lesson for a success it never caused.

    Each pair carries flags so BOTH sides genuinely have a coarse axis -- comparing two
    axis-less keys would pass vacuously on "" == "" and prove nothing.
    """
    assert at_action.coarse_target(_c("py scripts/a.py --v 1")) \
        != at_action.coarse_target(_c("py scripts/b.py --v 1")), "different file args"
    assert at_action.coarse_target(_c("py agent_cli.py boot claude --j")) \
        != at_action.coarse_target(_c("py agent_cli.py learn claude --j")), "different subcommand"
    assert at_action.coarse_target(_c("pytest tests/x.py -q")) \
        != at_action.coarse_target(_c("py tests/x.py -q")), "different executable"

    # ...and the behaviour that actually matters: no flip across different actions.
    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid = _sid()
    at_action.mark_impression(sid, _c("py scripts/a.py --v 1"), ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, _c("py scripts/a.py --v 1"), False)
    res = at_action.resolve_action_outcome(sid, _c("py scripts/b.py --v 1"), True)
    assert res["flipped"] is False and res["credited"] == 0, \
        "succeeding at a DIFFERENT action must never credit the failed one's lesson"


def test_j5_only_keys_that_need_no_axis_get_none():
    """"" means "no second axis". It is for keys that already join exactly (paths) or
    that cannot be parsed -- NOT for minimal commands: suppressing the axis there was the
    bug test_j2 caught, because the fix for a broken command is often the minimal form."""
    assert at_action.coarse_target(at_action.normalize_target(path=__file__)) == "", \
        "a path key already joins exactly"
    assert at_action.coarse_target("") == ""
    assert at_action.coarse_target("garbage-with-no-tag") == ""
    assert at_action.coarse_target("c:") == ""
    assert at_action.coarse_target(_c("pytest")) == "k:pytest", \
        "a minimal command still needs an axis so a dressed sibling can reach it"


# ---------------------------------------------------------------- the loop closing

def test_j6_the_credit_loop_closes_across_two_spellings(monkeypatch):
    """THE SLICE. This is the assertion the whole night is for."""
    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid = _sid()
    failed = _c('py agent_cli.py boot claude --taks "x"')
    fixed = _c('py agent_cli.py boot claude --task "x"')
    assert failed != fixed, "precondition: the exact keys genuinely differ"

    at_action.mark_impression(sid, failed, ["learn:experiment:the_lesson"])
    at_action.resolve_action_outcome(sid, failed, False)        # the typo fails
    res = at_action.resolve_action_outcome(sid, fixed, True)    # the fix succeeds

    assert res["flipped"] is True, "a fixed command must join its own earlier failure"
    assert res["credited"] == 1, "and the lesson surfaced at the failure must be credited"
    assert res["sources"] == ["learn:experiment:the_lesson"]


def test_j7_the_credit_names_the_axis_that_won_it(monkeypatch):
    """Provenance. A coarse credit must be distinguishable from an exact one, forever."""
    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)

    sid = _sid()
    at_action.mark_impression(sid, _c("py x.py --a 1"), ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, _c("py x.py --a 1"), False)
    coarse = at_action.resolve_action_outcome(sid, _c("py x.py --a 2"), True)
    assert coarse["join"] == "coarse", f"won on the new axis: {coarse!r}"

    sid2 = _sid()
    tgt = _c("py y.py")
    at_action.mark_impression(sid2, tgt, ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid2, tgt, False)
    exact = at_action.resolve_action_outcome(sid2, tgt, True)
    assert exact["flipped"] is True and exact["join"] == "exact", \
        "the pre-existing path is unchanged and still says so"

    staged = at_action.session_outcomes(sid)
    assert staged and staged[-1].get("join") == "coarse", \
        "the durable outcome record carries the axis too, or the audit is impossible"


def test_j8_consume_on_credit_holds_across_the_axes(monkeypatch):
    """One flip, one credit. The coarse axis must not become a farm."""
    calls = []
    monkeypatch.setattr(at_action, "record_feedback",
                        lambda src, *a, **k: calls.append(src) or True)
    sid = _sid()
    at_action.mark_impression(sid, _c("py z.py --a 1"), ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, _c("py z.py --a 1"), False)
    at_action.resolve_action_outcome(sid, _c("py z.py --a 2"), True)
    at_action.resolve_action_outcome(sid, _c("py z.py --a 3"), False)
    at_action.resolve_action_outcome(sid, _c("py z.py --a 4"), True)
    assert calls == ["learn:experiment:l"], f"credited more than once: {calls}"


def test_j9_a_command_whose_identity_is_a_flag_value_gets_no_axis(monkeypatch):
    """FOUND BY DOGFOODING, not by thinking. While building this slice the live hook
    reported `[flip] FAIL->SUCCESS on: c:py -c "..."` and credited SIX unrelated lessons
    for a one-off throwaway script being fixed.

    `py -c "<script>"` carries its entire identity inside a flag VALUE, so dropping flags
    leaves bare "py" -- a CATEGORY, under which any failure joins any later success of the
    same interpreter. test_j4 passed vacuously here because every pair it compares has a
    path argument. A reduced-to-one-token key is refused; a genuinely minimal command,
    where nothing had to be dropped, still gets its axis (see test_j5).
    """
    assert at_action.coarse_target(_c('py -c "import io; io.open(1)"')) == "", \
        "the interpreter name alone must never be a join key"
    assert at_action.coarse_target(_c("pytest -q")) == "", \
        "reduced to one token by dropping flags -- the identity was in the flags"
    # ...and the floor is DISTINCT tokens, not token COUNT: this one slips any length
    # test while naming nothing but the interpreter, twice. From the live sample.
    assert at_action.coarse_target(
        _c("py -m arsenal.practice --help; py -m arsenal.practice moment 20260915")) == "", \
        "'py py' is two tokens and still only names the program being run"
    assert at_action.coarse_target(_c("py -c 'a'")) == at_action.coarse_target(_c("py -c 'b'")) == ""

    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid = _sid()
    at_action.mark_impression(sid, _c('py -c "first script"'), ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, _c('py -c "first script"'), False)
    res = at_action.resolve_action_outcome(sid, _c('py -c "a totally different script"'), True)
    assert res["flipped"] is False and res["credited"] == 0, \
        "fixing an unrelated one-off script must not credit anything"


def test_j10_a_shared_setup_preamble_does_not_collapse_distinct_actions(monkeypatch):
    """FOUND BY MEASUREMENT (scripts/measure_credit_join.py), on the live stream.

    Keying a compound command on its FIRST statement produced `k:$t = get-date` for
    `$t = get-date; node tests/score_export.test.mjs ...` -- a timing preamble. Three
    different actions in the sample (node vs py, different test files) all keyed to it.
    A compound command's identity is EVERY statement, not the first one.
    """
    a = at_action.coarse_target(_c("$t = get-date; node tests/score_export.test.mjs --sessions"))
    b = at_action.coarse_target(_c("$t = get-date; py tests/test_score_export.py --sessions"))
    assert a and b and a != b, f"preamble collapsed two actions: {a!r} == {b!r}"
    assert "score_export.test.mjs" in a and "node" in a, f"the real action must survive: {a!r}"

    # ...and the navigation prefix is still dropped, so the two spellings still agree.
    assert at_action.coarse_target(_c("cd e:/ai-setup; git log --oneline -3")) \
        == at_action.coarse_target(_c("git log --oneline -5"))

    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid = _sid()
    at_action.mark_impression(sid, _c("$t = get-date; node tests/a.mjs"), ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, _c("$t = get-date; node tests/a.mjs"), False)
    res = at_action.resolve_action_outcome(sid, _c("$t = get-date; py tests/b.py"), True)
    assert res["flipped"] is False, "a shared preamble is not a shared action"


def test_j11_a_heredoc_moves_the_program_into_the_body_so_there_is_nothing_to_join(monkeypatch):
    """FOUND BY A PEER'S HAND-LABELLED PRECISION PASS over the live stream, 2026-10-06.
    Seven of its nine FALSE joins were this one class, and it minted TWO of the only eight
    coarse-only credits that had a lesson surfaced.

    `payload.find("<<")` drops the heredoc body -- which for `py - <<PY` is the ENTIRE
    PROGRAM. What survives is an interpreter, and a PREAMBLE token then satisfies the
    distinct-token floor: `PYTHONUTF8=1 py`, `export PYTHONIOENCODING=utf-8 py`,
    `timeout 600 py`. Measured collision breadth of those keys on one sample: 105, 72 and
    60 distinct later successes. The floor's own docstring names `py -c "<script>"` as the
    case it refuses; every one of these routes around it with a prefix.
    """
    for cmd in ("PYTHONUTF8=1 py - <<PY",
                "export PYTHONIOENCODING=utf-8 && py - <<EOF",
                "timeout 600 py - <<py"):
        assert at_action.coarse_target(_c(cmd)) == "", f"preamble bought a key: {cmd!r}"

    # An env prefix is not identity, so stripping it EARNS a join rather than losing one.
    assert at_action.coarse_target(_c("PYTHONUTF8=1 py scripts/x.py")) \
        == at_action.coarse_target(_c("py scripts/x.py")) != ""
    # A heredoc whose command still names a FILE keeps its identity (see test_j3).
    assert at_action.coarse_target(_c("cat > notes.txt <<'EOF'\nbody\nEOF")) != ""

    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid = _sid()
    at_action.mark_impression(sid, _c("PYTHONUTF8=1 py - <<PY\nprobe a\nPY"),
                              ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, _c("PYTHONUTF8=1 py - <<PY\nprobe a\nPY"), False)
    res = at_action.resolve_action_outcome(sid, _c("PYTHONUTF8=1 py - <<PY\nunrelated\nPY"), True)
    assert res["flipped"] is False and res["credited"] == 0, \
        "two unrelated heredoc programs must not credit each other"


def test_j12_a_flag_before_the_program_must_not_erase_the_subcommand():
    """Class B from the same pass. `seen_flag` latched on the INTERPRETER flag, after which
    only path-like tokens survived -- so the subcommand died while the script path lived:
    `py -3.11 agent_cli.py bifrost-send --help` keyed as `k:py agent_cli.py`, collapsing
    the entire CLI into one key. In the sample that key gathered seven distinct later
    successes, one of them a mailbox WRITE. A file argument restarts the identity space."""
    send = at_action.coarse_target(_c("py -3.11 agent_cli.py bifrost-send --help"))
    mail = at_action.coarse_target(_c("py -3.11 agent_cli.py mailbox claude --as act --note x"))
    assert send and mail and send != mail, f"the CLI collapsed: {send!r} == {mail!r}"
    assert "bifrost-send" in send and "mailbox" in mail
    # ...and the flag's own VALUE is still not identity (test_j1 must keep holding).
    assert at_action.coarse_target(_c('py agent_cli.py boot claude --task "memory reach"')) \
        == at_action.coarse_target(_c('py agent_cli.py boot claude --task "other thing"'))


def test_j13_redirection_direction_is_part_of_the_action():
    """Latent class from the same pass: `>`, `>>` and `<` were all dropped as shell noise,
    so writing, appending and READING one path were a single key -- a failed write joined
    by a successful read would mint credit."""
    write = at_action.coarse_target(_c("cat > notes.txt <<MSG\nx\nMSG"))
    append = at_action.coarse_target(_c("cat >> notes.txt <<MSG\nx\nMSG"))
    read = at_action.coarse_target(_c("cat notes.txt"))
    assert len({write, append, read}) == 3, \
        f"write/append/read collapsed: {write!r} {append!r} {read!r}"


def test_j14_an_inline_program_has_no_identity_left_to_join_on(monkeypatch):
    """THE ONE THAT WAS STILL LIVE AFTER TWO FIXES. An adversarial replay of the whole
    stream (23,636 distinct command keys) found the 6-lesson false credit's key was STILL
    non-empty at HEAD: `k:py p='tests/fixtures/.../transcript_fail_then_success.jsonl`.

    Mechanism: tokens after `-c` are dropped unless they look pathy -- and a quoted path
    INSIDE the Python source looks pathy, so the script's own text supplied the identity
    the floor was asking for. One such live key held 23 distinct throwaway scripts. When
    the program arrives in an argument, that argument IS the identity and we drop it, so
    there is nothing left to join two different programs on.
    """
    for cmd in ('py -c "import json; p=\'state/coord/tasks.json\'; print(p)"',
                'py -c "import io; io.open(1)"',
                'node -e "require(\'./scripts/a.js\')"',
                'pwsh -Command "Get-ChildItem e:/ai-setup"'):
        assert at_action.coarse_target(_c(cmd)) == "", f"inline program kept a key: {cmd!r}"

    # ...but `-c` is NOT an inline program to everything: grep counts with it.
    assert at_action.coarse_target(_c("grep -c error logs/app.log")) != ""

    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid = _sid()
    a = _c("""py -c "p='tests/fixtures/x.jsonl'; print(open(p).read())" """)
    b = _c("""py -c "import shutil; shutil.rmtree('build')" """)
    at_action.mark_impression(sid, a, ["learn:experiment:l"])
    at_action.resolve_action_outcome(sid, a, False)
    res = at_action.resolve_action_outcome(sid, b, True)
    assert res["flipped"] is False and res["credited"] == 0, \
        "reading a fixture and deleting a build dir are not one action"


def test_j15_which_tree_is_part_of_the_action(monkeypatch):
    """`cd` was dropped wholesale, so `cd /e/AI-Setup && X` and `cd /e/AI-Setup-Sandbox && X`
    were one key. This box HAS a sandbox clone (redis 16380, UI 8790), persistent worktrees
    and sibling repos, and live groups were measured mixing them: one key spanned
    `worktrees/sunshine-discord-split` and `/e/ai-setup`, another `/e/ai-setup` and
    `/e/aurora-strings`. Navigating to where we already are stays free."""
    here = at_action.coarse_target(_c("cd /e/AI-Setup && npm run build"))
    sandbox = at_action.coarse_target(_c("cd /e/AI-Setup-Sandbox && npm run build"))
    sibling = at_action.coarse_target(_c("cd /e/akashiclabs-site && npm run build"))
    assert len({here, sandbox, sibling}) == 3, \
        f"three trees, one key: {here!r} {sandbox!r} {sibling!r}"
    # cd to the repo root is a no-op and must still join the bare spelling, in BOTH the
    # git-bash and the Windows spelling of the same directory.
    bare = at_action.coarse_target(_c("npm run build"))
    assert here == bare != ""
    assert at_action.coarse_target(_c("cd E:\\AI-Setup && npm run build")) == bare

    monkeypatch.setattr(at_action, "record_feedback", lambda *a, **k: True)
    sid = _sid()
    at_action.mark_impression(sid, _c("cd /e/AI-Setup-Sandbox && py agent_cli.py boot claude"),
                              ["learn:experiment:l"])
    at_action.resolve_action_outcome(
        sid, _c("cd /e/AI-Setup-Sandbox && py agent_cli.py boot claude"), False)
    res = at_action.resolve_action_outcome(
        sid, _c("cd /e/AI-Setup && py agent_cli.py boot claude"), True)
    assert res["flipped"] is False, "the sandbox and the live repo are different actions"


def test_j16_powershell_nav_and_line_continuations_are_not_identity():
    """Two one-line holes from the same replay. `Set-Location` was not in the nav set, so
    PowerShell's own idiom created the bypass `cd` was dropped to prevent (2 live false
    flips). And `_looks_pathy("\\\\")` was True, so a trailing line-continuation became a
    phantom `/` token that satisfied the identity floor by itself."""
    assert at_action.coarse_target(_c("Set-Location e:\\ai-setup; py -c \"import os\"")) == "", \
        "Set-Location must be nav, exactly as cd is"
    assert at_action.coarse_target(_c("$env:PYTHONUTF8='1'; py -c \"import os\"")) == "", \
        "an assignment-only statement performs nothing"
    assert at_action.coarse_target(_c("$t = Get-Date; py -c \"import os\"")) == ""
    assert at_action.coarse_target(_c('py -c "import os" \\\n 2>&1')) == "", \
        "a line continuation is not a path"


def test_j17_a_dressed_minimal_command_still_joins_its_bare_sibling():
    """The missed join test_j5 promises not to create. The old floor decided on
    `key != payload`, so `cd <repo> && pytest` was refused while bare `pytest` was allowed
    -- punishing the dressed spelling of a command that had lost nothing but navigation.
    The floor now asks what was DROPPED, not whether the string changed."""
    bare = at_action.coarse_target(_c("pytest"))
    assert bare == "k:pytest"
    assert at_action.coarse_target(_c("cd /e/AI-Setup && pytest")) == bare
    assert at_action.coarse_target(_c("pytest | tail -40")) == bare, \
        "a pipeline tail is not identity either"
    # ...while a dropped FLAG still refuses, because that is identity we cannot see.
    assert at_action.coarse_target(_c("pytest -q")) == ""


if __name__ == "__main__":
    sys.exit(pytest.main([os.path.abspath(__file__), "-q"]))
