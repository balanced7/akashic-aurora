"""RED pins: the door that ARMS the watcher is the one door that cannot name its own lane.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

THE CLASS, THREE TIMES NOW. "Which lane does this door read" has been answered wrong three
times, each time by a door that did not self-default while its siblings did:

  T133 (bifrost-sync)  -- "The runners self-default onto `work`; this door did not, so the
                          harness seat read LEGACY ... from a cursor that drifted 22 HOURS
                          behind while real mail sat on `work` unread." Fixed in
                          cmd_bifrost_sync by `os.environ.setdefault("BIFROST_CONSUME_LANE",
                          "work")` (agent_cli.py:6641).

  T198 (wake_lane)     -- "this asked only for BIFROST_WAKE_LANE, which is set NOWHERE in the
                          house, while every consumer defaults to BIFROST_CONSUME_LANE=work.
                          So detection watched one lane and draining moved the other."
                          Live cost: "eight hand re-arms in one day." Found by chronos, in
                          Serge's fleet, reading our PUBLIC repo from the outside -- they
                          cannot see our working tree, which is why they catch what our own
                          probes step over (core/comm/bifrost_api.py:95-110).

  THIS ONE (bifrost-standby) -- the verb whose ENTIRE JOB is drain-then-arm never sets the
                          default at all. Measured 2026-10-05:

                              cmd_bifrost_sync      sets the default: YES
                              cmd_bifrost_standby   sets the default: NO

                              wake_lane() with no env                     -> ''
                              wake_lane() with BIFROST_CONSUME_LANE=work  -> 'work'

                          So a seat that arms with `py agent_cli.py bifrost-standby claude`
                          watches the EMPTY/legacy lane while its mail lands on `work`. That
                          is precisely the T198 failure, in the organ T198 was written for.

WHY NOBODY HAS BEEN BITTEN YET, and why that is not reassurance. The arm command the house
PRESCRIBES carries the lanes explicitly -- agent_cli.py:5840 and the stop hook both print
`BIFROST_CONSUME_LANE=work BIFROST_WAKE_LANE=work py ... bifrost-standby <seat> --session <id>`.
So the env vars are compensating, in the instruction string, for a default missing in the code.
The defect is invisible exactly as long as every seat types the long form every time -- and the
memory records three-plus recurrences of seats getting that long form subtly wrong, one of them
causing a measured outage. A prescription is not a default: it fails on the first seat that
trusts the verb's own signature.

THE LAW THIS SERVES: `when_a_fix_primitive_is_born_sweep_the_class_that_birthed_it`. T133
minted the primitive (`setdefault` on the consume lane) and applied it to ONE door. Naming is
not sweeping; two doors is not the class. These pins close it by asserting the property of
EVERY door rather than of the two we know about.

Run::

    py -m pytest tests/test_every_draining_door_names_its_lane.py -q
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

#: Doors that DRAIN the inbox or ARM the watcher. Each must resolve the consume lane itself;
#: none may rely on its caller having exported the variable. Kept as an explicit list so a new
#: draining verb is a deliberate addition here rather than a silent omission.
DRAINING_DOORS = ("cmd_bifrost_sync", "cmd_bifrost_standby")

LANE_VAR = "BIFROST_CONSUME_LANE"


def _functions() -> dict:
    tree = ast.parse((ROOT / "agent_cli.py").read_text(encoding="utf-8-sig"))
    return {n.name: n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _names_the_lane(fn: ast.AST) -> bool:
    """Does this function resolve the consume lane, directly or via a shared helper?

    Walks the AST rather than grepping the source, because a docstring that MENTIONS the
    variable is not the same as code that sets it -- the house's own
    `a_pin_that_reads_prose_measures_prose` defect, and the exact mistake an earlier pin in
    this repo made by using `in inspect.getsource(...)`.
    """
    body = list(fn.body)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]                                  # drop the docstring, keep the code
    code = "\n".join(ast.unparse(st) for st in body)
    return (LANE_VAR in code) or ("ensure_lane_defaults" in code)


def test_every_draining_door_resolves_the_consume_lane_itself():
    """THE PIN. A door that drains or arms must not depend on its caller's environment."""
    fns = _functions()
    missing = []
    for name in DRAINING_DOORS:
        assert name in fns, "%s no longer exists in agent_cli.py -- update DRAINING_DOORS" % name
        if not _names_the_lane(fns[name]):
            missing.append(name)
    assert not missing, (
        "%d draining/arming door(s) never resolve %s and so read whatever lane the caller "
        "happened to export: %s.\n"
        "That is T133 (22h cursor drift) and T198 (eight hand re-arms in one day) for a third "
        "time. The prescribed arm command carries the variable explicitly, which hides this "
        "for exactly as long as every seat types the long form correctly every time."
        % (len(missing), LANE_VAR, ", ".join(missing)))


def test_the_wake_lane_is_non_empty_for_a_seat_that_only_ran_the_verb():
    """BEHAVIOURAL. T198's rule is "the wake lane FOLLOWS the consume lane" -- but only if
    something set the consume lane. With neither variable exported, wake_lane() is empty, so
    detection and draining address different things again.

    Measured before the fix: wake_lane() -> '' with no env, 'work' with the consume lane set.
    """
    for var in ("BIFROST_WAKE_LANE", LANE_VAR):
        os.environ.pop(var, None)

    import importlib

    from core.comm import bifrost_api
    importlib.reload(bifrost_api)

    import agent_cli  # noqa: F401  -- importing the CLI must be enough to settle the default
    importlib.reload(bifrost_api)

    assert bifrost_api.wake_lane(), (
        "wake_lane() is empty for a seat that imported the CLI and exported nothing, so the "
        "watcher watches one lane while the drain moves another -- T198 verbatim. The consume "
        "lane default must live in the code, not in the instruction string.")


def test_the_prescribed_arm_command_matches_what_the_verb_actually_needs():
    """RATCHET ON THE PRESCRIPTION. Once the door self-defaults, the printed arm command must
    stop demanding the variables -- otherwise the house keeps teaching ceremony it no longer
    needs, and every extra token is another chance to get the arm subtly wrong (three-plus
    recorded recurrences, one measured outage).

    Deliberately scoped to the ENV PREFIX, not the whole command: `--session` and the seat id
    stay, because an explicit session is still worth printing for a seat that has several.
    """
    src = (ROOT / "agent_cli.py").read_text(encoding="utf-8-sig")
    hook = (ROOT / "scripts" / "hooks" / "claude_stop.py").read_text(encoding="utf-8-sig")
    offenders = [name for name, text in (("agent_cli.py", src), ("claude_stop.py", hook))
                 if "BIFROST_CONSUME_LANE=work BIFROST_WAKE_LANE=work" in text]
    assert not offenders, (
        "%s still print an arm command whose env prefix the verb now sets for itself: %s. "
        "A prescription that outlives its reason becomes ceremony, and ceremony is where the "
        "inline-& recurrence lives." % (len(offenders), ", ".join(offenders)))
