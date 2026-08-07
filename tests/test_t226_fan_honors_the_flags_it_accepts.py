"""T226 RED: the continuation flags are accepted on the fan path and do nothing there.

FOUND BY THE FAN, AT ITS OWN DOOR, 2026-08-07. Lens 2 was pointed at the T216 class -- a flag
accepted by the parser and never read on a path it plausibly applies to -- and it traced
`ask_many` cleanly, then said: `ask_many` does not accept `continue_on_cut` or
`max_continuations`, but if a parser exposed them "Python would raise a TypeError, not silently
ignore them -- so it does not fit the class."

Its reasoning was right and its conclusion was wrong, for a reason that is my fault: the CLI
file was one of the three I refused into the fan (T225), so it could not see that agent_cli.py
never passes them at all. No TypeError. Silence. It is the T216 class exactly, one flag over.

  py agent_cli.py ask --prompts-file X --continuations 99 --no-continue
  -> runs, exits 0, and neither flag reaches anything. Measured.

WHY IT MATTERS MORE ON THE FAN THAN ON THE SINGLE ASK. A cut answer is the fan's characteristic
failure: N branches share one budget-shaped prompt, so when one cuts they tend to cut together,
and the caller who reaches for --continuations is a caller who has already been bitten. The
flag exists, reads as available, and is inert precisely where it was most wanted.

AND A SECOND, QUIETER CASE OF THE SAME LAW -- DEFAULT DRIFT ACROSS DOORS.

  ask()            continue_on_cut=False     (core/comm/ask.py:235)
  --no-continue    default=True              (agent_cli.py, store_false)

Same verb, two doors, opposite defaults. The CLI's own help explains at length why continuation
ON is correct -- "a cut means the model hit its OWN limit, and stitching costs one completion
while a re-ask pays for the whole prompt again" -- and every programmatic caller (the MCP twin,
the ToolBox, sift, any runner) gets the opposite. The argument for the default is written down
in exactly one of the two places the default is set. That is the check_door_parity concern
applied to behaviour rather than to surface: the doors match in what they OFFER and differ in
what they DO.

Lens 4 found the drift from the cost side and framed it as "the default is stingy", which is
true of the library door and false of the CLI. Both branches were right about the mechanism and
wrong about its scope, and neither could have known: I refused them the file that says so.
"""
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def test_ask_many_accepts_the_continuation_controls():
    """THE PIN. The fan must be able to express what the flag offers."""
    from core.comm.ask import ask_many

    params = inspect.signature(ask_many).parameters
    assert "continue_on_cut" in params, \
        "--continuations/--no-continue are accepted by the CLI and reach nothing"
    assert "max_continuations" in params


def test_the_cli_actually_threads_them_into_the_fan():
    """A signature that accepts and a call site that omits is the same defect with more steps.

    Read at the source rather than run: a live fan costs money, and what is under test is the
    wiring, not the model.
    """
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    i = src.index("o = ask_many(")
    call = src[i:i + 500]
    assert "continue_on_cut" in call, \
        "cmd_ask calls ask_many without the continuation controls -- the flags evaporate here"
    assert "max_continuations" in call or "continuations" in call


def test_fan_branches_continue_a_cut_answer_when_asked():
    """Behavioural pin, no network: a fake client that cuts once, then finishes.

    Proves the flag reaches the BRANCH, not merely the signature -- the T216 lesson is that a
    parameter can be accepted at every layer and still be dropped at the last one.
    """
    from core.comm.ask import ask_many

    class _Msg:
        def __init__(self, content): self.content = content

    class _Choice:
        def __init__(self, content, finish): self.message, self.finish_reason = _Msg(content), finish

    class _Usage:
        prompt_tokens = 10
        completion_tokens = 5
        completion_tokens_details = None

    class _Resp:
        def __init__(self, content, finish):
            self.choices, self.usage, self.model = [_Choice(content, finish)], _Usage(), "fake"

    class _Completions:
        def __init__(self): self.calls = 0

        def create(self, **kw):
            self.calls += 1
            return _Resp("part one", "length") if self.calls == 1 else _Resp(" and part two", "stop")

    class _Chat:
        def __init__(self): self.completions = _Completions()

    class _Client:
        def __init__(self): self.chat = _Chat()

    o = ask_many(["q"], client=_Client(), continue_on_cut=True, max_continuations=1)
    answer = (o.detail or {}).get("branches", [{}])[0].get("answer") or ""
    assert "part two" in answer, "the branch stopped at the cut -- continuation never reached it"


def _ask_parser_defaults():
    """Ask the PARSER what the CLI defaults are. Never grep for them.

    The first cut of this pin did `src.index('"--no-continue"')` and matched line 2130 --
    `child.append("--no-continue")` in the --bg spawn path -- not the argparse site 3400 lines
    later. It then read a default that was not there and PASSED, green, over a real drift.
    A locator that can silently address the wrong site is not evidence of anything
    (a_pin_that_passes_only_while_the_feature_is_broken, one step upstream).
    """
    import agent_cli
    ns = agent_cli.build_parser().parse_args(["ask", "q"])
    return ns


def test_the_library_never_continues_unasked():
    """T204's ruling, re-affirmed. Not drift -- a decision, and it stays.

    I nearly broke this. Lens 4 of the fan reported the False default as a cost defect ("the
    door is stingy where stinginess costs a whole retry"), the CLI's opposite default made it
    look like unreconciled drift, and I flipped it -- overriding a ratified decision I had not
    read, on a hypothesis from a helper with no tools. The full suite caught it by name:
    test_t204_untruncate.test_continuation_is_opt_in, whose docstring is one line long and says
    "Spending extra calls must be asked for."

    A programmatic caller has no human watching the spend line. That is the whole argument, and
    it is why the two doors SHOULD differ.
    """
    from core.comm.ask import ask, ask_many

    assert inspect.signature(ask).parameters["continue_on_cut"].default is False
    assert inspect.signature(ask_many).parameters["continue_on_cut"].default is False


def test_the_cli_passes_its_own_policy_to_every_path_it_owns():
    """THE REAL INVARIANT the drift-hunt was reaching for.

    The CLI may choose continuation FOR its human -- it has the spend line and a person reading
    it. What it may not do is apply that choice to one of its two paths. Before T226 the single
    ask got the CLI's True and the fan got the library's False, so the same command line meant
    two different things depending on whether --fan was present.
    """
    ns = _ask_parser_defaults()
    assert ns.continue_on_cut is True, "the CLI's own default is opt-IN, and that is deliberate"

    src = (REPO / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    fan = src[src.index("o = ask_many("):][:600]
    single = src[src.index("o = ask_helper("):][:600]
    for name, block in (("fan", fan), ("single", single)):
        assert "continue_on_cut" in block, f"the {name} path does not receive the CLI's choice"
        assert "continuations" in block, f"the {name} path does not receive max_continuations"


def test_every_ask_flag_is_forwarded_by_bg_or_explicitly_is_not():
    """THE STRUCTURAL PIN. A flag added tomorrow cannot be silently dropped by --bg.

    The hand-written forwarder knew four flags and dropped every one added after it. This
    asserts the two tables are TOTAL over the parser, so the next flag must be classified
    rather than forgotten.
    """
    import agent_cli

    sub = [a for a in agent_cli.build_parser()._subparsers._group_actions[0].choices.items()]
    ask_parser = dict(sub)["ask"]
    dests = {a.dest for a in ask_parser._actions if a.dest != "help"}

    known = set(agent_cli._BG_FORWARD) | set(agent_cli._BG_NOT_FORWARDED)
    unclassified = dests - known
    assert not unclassified, (
        f"--bg would silently drop these ask flags: {sorted(unclassified)}. Add each to "
        "_BG_FORWARD, or to _BG_NOT_FORWARDED with the reason it is excluded.")


def test_bg_forwards_the_fan():
    """The measured case. `--bg --fan 5` ran ONE ask and said nothing about the other four.

    Checked on the argv the parent builds, not by spawning: the defect was always in the
    argv, and a pin that costs five model calls will be deleted the first time it is slow.
    """
    import agent_cli

    ns = agent_cli.build_parser().parse_args(
        ["ask", "--bg", "--fan", "5", "--system", "S", "--continuations", "4", "q"])
    argv = agent_cli._bg_forward_argv(ns)

    assert "--fan" in argv and argv[argv.index("--fan") + 1] == "5", \
        "--bg dropped --fan: the caller asked for 5 branches and got 1, silently"
    assert "--system" in argv, "--bg dropped --system"
    assert "--continuations" in argv, "--bg dropped --continuations"


def test_the_fan_path_writes_the_background_record():
    """A backgrounded fan must be RETRIEVABLE, not merely executed.

    Found live, and only because --bg started forwarding --fan: three branches landed, were
    billed, and `ask --get` reported ORPHANED -- "never wrote a result -- re-ask; nothing will
    arrive" -- about a completed result sitting in the .out file. _bg.finish existed on the
    single-ask path only, and the fan returned above it.

    Pinned at the source: the finish call must appear BEFORE the fan's json return, or the
    record is written only for asks that are not fans.
    """
    src = (REPO / "agent_cli.py").read_text(encoding="utf-8", errors="replace")
    fan_call = src.index("o = ask_many(")
    fan_return = src.index("return 0 if o.ok else 1", fan_call)
    assert "_bg.finish(" in src[fan_call:fan_return], \
        "the fan path returns without writing the bg record -- --bg --fan reports ORPHANED"


def test_get_renders_a_backgrounded_fan():
    """`--get` on a fan must show the branches and the diversity verdict, not an empty DONE.

    summarize() read result["answer"], which only a single ask has, so a completed 3-branch
    fan rendered as DONE with no body. The T182 verdict is the whole reason to read a fan --
    "3 of 3 landed" without it lets one answer read as three findings.
    """
    from core.comm.ask_bg import summarize

    # `homogeneous` is explicit here because T227 made the PRESCRIPTION mode-aware: a collapsed
    # same-prompt fan and a collapsed different-prompts fan now say different (opposite) things,
    # and this pin is about the same-prompt one. Written before that distinction existed, it
    # relied on a default; naming the shape keeps it testing what it meant to test.
    rec = {"handle": "h", "status": "done", "result": {
        "n": 3, "n_ok": 3, "usd": 0.01, "diversity": "collapsed", "homogeneous": True,
        "branches": [{"i": i, "ok": True, "partial": False, "answer": f"A{i}"} for i in range(3)]}}
    s = summarize(rec)

    assert s["state"] == "DONE"
    assert "A0" in s["answer"] and "A2" in s["answer"], "the branch bodies must be readable"
    assert "3 of 3" in s["next"]
    assert "COLLAPSED" in s["next"], "a collapsed fan must say so, or it reads as 3 findings"


def test_get_still_renders_a_single_ask():
    """The fan branch must not swallow the ordinary case."""
    from core.comm.ask_bg import summarize

    s = summarize({"handle": "h", "status": "done", "result": {"answer": "just one"}})
    assert s["answer"] == "just one" and s["next"] == "read the answer"


def test_bg_never_forwards_bg_itself():
    """The one forwarding that must NOT happen: a child that respawns is unbounded."""
    import agent_cli

    ns = agent_cli.build_parser().parse_args(["ask", "--bg", "q"])
    argv = agent_cli._bg_forward_argv(ns)
    assert "--bg" not in argv and "--bg-child" not in argv


def test_the_flags_are_not_silently_swallowed_by_the_parser():
    """End-to-end, no model call: --prompts-file with an unreadable path exits 2 BEFORE spending.

    Guards the order that makes the other pins affordable: a typo must never cost a fan.
    """
    r = subprocess.run(
        [sys.executable, "agent_cli.py", "ask", "--prompts-file", "no/such/prompts/t226.txt",
         "--continuations", "99"],
        cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    assert r.returncode == 2
    assert "cannot read --prompts-file" in r.stderr
