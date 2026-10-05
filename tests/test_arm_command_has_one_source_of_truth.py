"""RED pins: boot and the stop hook must hand over the SAME arm command, and it must work.

DANIEL'S ASK, 2026-10-02: "I like your thoughts of making arming the watcher be a part of the boot
sequence. Would you mind building that?" Boot cannot arm the watcher itself, and a prior seat wrote
the reason into `agent/harness/context.py`: a watcher spawned detached prints into a void while
`any_armed()` answers "armed", which is a surface asserting reachability it does not have. So the
arming has to be done by the seat, on a channel the harness is watching, and boot's job is to hand
over the command.

IT HANDS OVER A COMMAND THAT DOES NOT WORK, AND THAT IS WHY THIS KEEPS RECURRING. Traced today:

    boot (agent/harness/context.py)
        py scripts/bifrost_wake.py --agent claude --min-tier 0

    the stop hook (agent/harness/hooks/claude_stop.py)
        BIFROST_CONSUME_LANE=work BIFROST_WAKE_LANE=work py agent_cli.py bifrost-standby claude
            --session <sid>

Two surfaces, two different commands for one job. And the difference is not cosmetic:

  * `scripts/bifrost_wake.py` stamps its origin from `BIFROST_WAKE_ORIGIN`, defaulting to
    "unknown" (scripts/bifrost_wake.py:742).
  * `bifrost-standby` sets `BIFROST_WAKE_ORIGIN: "harness"` (agent_cli.py:6658).
  * `WAKEABLE_ORIGINS` is {harness, direct}, so `harness_armed()` returns **False** for an
    "unknown" origin.

So a seat that follows BOOT's instruction arms a listener the STOP HOOK then rejects, blocking with
"holds the seat with no origin record (not wakeable by evidence)". The seat re-arms, and if it
consults boot again it gets the same bad command. The house's own memory records this failure
recurring three or more times and read it as carelessness. It is not: the instruction was wrong.

WHY THE STOP SEAM IS THE RIGHT MOMENT AND BOOT IS NOT, which is the part of the ask I am pushing
back on rather than silently implementing. The watcher is CONSUMED when it fires, which happens
mid-session -- it happened to this seat overnight. An arm performed at boot is already spent by the
time idleness matters. The stop hook fires exactly when the seat is about to go quiet, already
checks `harness_armed`, and already BLOCKS. The gate exists and it is at the better seam. What is
missing is that the two surfaces disagree about how to satisfy it.

SO THE FIX IS ONE SOURCE OF TRUTH, not a new mechanism: one function that builds the canonical arm
command, used by both surfaces, and which can only ever emit a command that stamps a wakeable
origin. These pins are about agreement and correctness, not about where the gate lives.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import wake_seat as WS  # noqa: E402

SESSION = "deadbeef-0000-1111-2222-333344445555"
AGENT = "claude"


def _canonical():
    assert hasattr(WS, "arm_command"), \
        "there is no single source of truth for the arm command; boot and the stop hook each " \
        "build their own, and they disagree"
    return WS.arm_command(AGENT, SESSION)


# ---------------------------------------------------------------- P1-P3: it must actually arm
def test_there_is_one_canonical_arm_command():
    cmd = _canonical()
    assert isinstance(cmd, str) and cmd.strip(), "arm_command returned nothing usable"


def test_the_command_stamps_a_WAKEABLE_origin():
    """The whole defect. A command that leaves BIFROST_WAKE_ORIGIN unset stamps "unknown", and
    harness_armed() rejects it, so the stop hook blocks the seat that obeyed the instruction."""
    cmd = _canonical()
    assert "bifrost-standby" in cmd, (
        "the advertised command is not the one that stamps origin=harness; "
        f"got {cmd!r}. scripts/bifrost_wake.py invoked bare stamps 'unknown'.")


def test_the_command_carries_the_session_so_the_seat_is_per_session():
    assert SESSION in _canonical(), \
        "wake seats are per-session (T029 Wave 2); a command without --session can arm the " \
        "wrong seat or none"


def test_the_armed_listener_consumes_the_RIGHT_LANE():
    """THE PROPERTY, kept; the mechanism that delivers it, moved.

    This pin asserted that BIFROST_CONSUME_LANE and BIFROST_WAKE_LANE appeared IN the command
    string, because "the listener consumes the wrong lane without it". That was exactly true
    when written and is no longer the mechanism: on 2026-10-05 the lane default moved from the
    instruction string into the code, because the prefix was compensating for a default that
    `cmd_bifrost_standby` -- the ARMING door -- never set. Its sibling `cmd_bifrost_sync` had
    it (T133) and `wake_lane()` follows the consume lane (T198), so the one door whose entire
    job is drain-then-arm was the one door that could not name its own lane. Measured before
    the fix: wake_lane() -> '' with no env, 'work' with it set.

    So the requirement is unchanged and the assertion follows it to where it now lives:
    bifrost_api.ensure_lane_defaults(), which runs at import. Deleting this pin because its
    string vanished would have discarded the guarantee along with the mechanism.
    """
    import os

    for var in ("BIFROST_CONSUME_LANE", "BIFROST_WAKE_LANE"):
        os.environ.pop(var, None)

    import importlib

    from core.comm import bifrost_api
    importlib.reload(bifrost_api)

    assert bifrost_api.wake_lane() == "work", (
        "a seat that runs the canonical arm command with nothing exported would watch lane "
        "%r -- the listener and the drain must address the same thing (T198)."
        % bifrost_api.wake_lane())

    os.environ["BIFROST_CONSUME_LANE"] = "legacy"
    assert bifrost_api.wake_lane() == "legacy", (
        "the default must be a FLOOR, not an override: a seat that deliberately splits the "
        "planes has to be able to.")
    os.environ.pop("BIFROST_CONSUME_LANE", None)


# ---------------------------------------------------------------- P5-P6: the two surfaces AGREE
def _norm(s):
    """Compare the command's SHAPE, not its whitespace or absolute paths."""
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    s = re.sub(r"[A-Za-z]:[\\/][^\s]*agent_cli\.py", "agent_cli.py", s)
    s = s.replace("\\", "/")
    return s


def test_boot_advertises_the_canonical_command(monkeypatch):
    """FORCE the unarmed state rather than reading the live one. A first draft of this pin SKIPPED
    whenever the seat happened to be armed, which means it would have been silently absent in the
    only condition it exists to check -- the house has a lesson for exactly that shape ("does this
    stay green after the first real user?"). Ambient state is never the fixture."""
    from agent.harness import context
    monkeypatch.setattr(WS, "any_armed", lambda *_a, **_k: "unarmed")
    line = context._reach_line(AGENT)
    assert "NO WATCHER ARMED" in line, f"the forced-unarmed state did not take: {line!r}"
    assert "bifrost-standby" in line, (
        "boot still advertises a command that stamps origin 'unknown', which the stop hook "
        f"rejects. boot said: {line!r}")


def test_the_stop_hook_and_boot_do_not_disagree(monkeypatch):
    """Whatever each surface prints, they must not hand a reader two different instructions for
    the same job. This is the pin that would have caught the live defect."""
    from agent.harness import context
    monkeypatch.setattr(WS, "any_armed", lambda *_a, **_k: "unarmed")
    boot = _norm(context._reach_line(AGENT))
    if "bifrost-standby" not in boot:
        raise AssertionError(f"boot does not advertise the canonical command. boot: {boot!r}")
    # The canonical command's distinctive tokens must all appear in whatever boot prints --
    # DERIVED from arm_command rather than hardcoded. The hardcoded list named
    # BIFROST_CONSUME_LANE, so when the lane moved from the prescription into the door
    # (2026-10-05) this pin failed for a change that made the house MORE correct. A pin on
    # "the two surfaces agree" should not also freeze WHAT they agree on.
    canon = _norm(_canonical())
    # Compare STRUCTURAL tokens only. The session id legitimately differs -- the canonical
    # command is built for this test's fixture session while boot reports the live ambient
    # one -- so including it compares two correct answers and calls them a disagreement.
    _toks, _skip = [], False
    for t in canon.split():
        if _skip:
            _skip = False
            continue
        if t == "--session":
            _skip = True                      # the id after it is per-session, not structural
        if "=" in t or t.endswith(".py"):
            continue
        _toks.append(t)
    for tok in _toks:
        assert tok in boot, (
            "boot's arm advice is missing %r from the canonical command -- "
            "boot=%r canon=%r" % (tok, boot, canon))


# ---------------------------------------------------------------- P7: it must be the real thing
def test_the_canonical_command_names_a_file_that_exists():
    """A perfectly-shaped command pointing at a moved file is the next version of this bug."""
    cmd = _canonical()
    m = re.search(r"([A-Za-z]:[\\/][^\s]*agent_cli\.py|agent_cli\.py)", cmd)
    assert m, f"no agent_cli.py in the command: {cmd!r}"
    path = m.group(1)
    if path == "agent_cli.py":
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "agent_cli.py")
    assert os.path.isfile(path), f"the advertised command points at a missing file: {path}"


def test_an_origin_of_unknown_is_not_wakeable_which_is_why_this_matters():
    """RATCHET on the fact that makes the whole file necessary. If 'unknown' ever becomes
    wakeable, these pins are arguing about nothing and should be revisited deliberately."""
    assert "unknown" not in WS.WAKEABLE_ORIGINS, \
        "an unstamped origin became wakeable; re-read this file's premise before changing it"
    assert WS.ORIGIN_HARNESS in WS.WAKEABLE_ORIGINS
