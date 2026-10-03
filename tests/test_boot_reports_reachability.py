"""Boot must say whether a seat is REACHABLE, not only whether it is alive.

THE INCIDENT, 2026-09-24. Daniil sent "How'd setting up find go?" over Discord at 13:40:21. It
reached nobody. The seat was not down -- it was mid-turn, productive, in session the whole
morning. It had no armed watcher, because a watcher is a SEPARATE process and nobody had asked
for one until he did, nine minutes later. The message sat in the mailbox marked `unhandled`,
correctly stored and completely unannounced.

Storage was never the problem. NOTIFICATION was. Task T398 records 13 prior recurrences of this
shape, every one of them diagnosed as "no Claude Code session was open" -- and this one had a
session open the entire time, which is precisely why the diagnosis kept missing. Being in
session and being reachable are different facts, and boot reported neither.

WHY THIS REPORTS RATHER THAN ARMS, which is the design decision and the part most likely to be
"fixed" later by someone who has not read this. The operator asked for arming to be part of the
boot sequence. Arming from a hook is a trap: scripts/bifrost_wake.py delivers by PRINTING TO
STDOUT and exiting, so a wake only lands if something is reading that stream. A watcher spawned
detached by a hook prints into a void -- and any_armed() would then answer "armed".

That is a surface asserting presence where there is no reachability, which is strictly worse
than the silence it replaces: "no watcher" at least reads as no watcher. The arming has to
happen on a channel the harness is watching, so boot hands over the command rather than running
it. If a later change makes the hook arm a watcher, these pins should go red, and the right
response is to re-read this paragraph rather than relax them.

Run::

    py -m pytest tests/test_boot_reports_reachability.py -q
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.harness import context as ctxmod  # noqa: E402


def _line(monkeypatch, state):
    """Render the reach line for a given any_armed() verdict."""
    from core.comm import wake_seat
    monkeypatch.setattr(wake_seat, "any_armed", lambda *a, **k: state)
    return ctxmod._reach_line("claude")


def test_every_state_any_armed_can_return_renders_distinctly(monkeypatch):
    """FOUR STATES, FOUR SENTENCES. any_armed() distinguishes armed / unarmed / dead-seat /
    unknown, and collapsing any pair of them here would throw away the distinction the wake
    layer was built to preserve."""
    seen = {s: _line(monkeypatch, s) for s in ("armed", "unarmed", "dead-seat", "unknown")}
    assert len(set(seen.values())) == 4, (
        f"two or more states render identically: {seen}"
    )
    for state, text in seen.items():
        assert text.startswith("reach:"), f"{state} did not render a reach line: {text!r}"


def test_only_the_armed_state_reads_as_reachable(monkeypatch):
    """The load-bearing one. Every NOT-armed state must read as not-reachable -- including
    'unknown', because "I could not tell" rendering as "you are fine" is the whole defect."""
    armed = _line(monkeypatch, "armed")
    assert "ARMED" in armed and "UNREACHABLE" not in armed.upper()

    for state in ("unarmed", "dead-seat", "unknown"):
        text = _line(monkeypatch, state)
        low = text.lower()
        assert ("unreachable" in low or "nothing is listening" in low
                or "not armed" in low), f"{state!r} does not read as unreachable: {text!r}"


def test_a_not_armed_seat_is_handed_the_arming_command(monkeypatch):
    """Naming a problem without its remedy is how a warning becomes wallpaper.

    THE REMEDY CHANGED SHAPE ON 2026-10-02 AND THIS PIN WAS RIGHT TO GO RED. It used to
    demand `bifrost_wake.py --min-tier 0` -- the bare listener at the most selective floor.
    Boot now hands back `agent_cli.py bifrost-standby`, and the old assertions were dropped
    only after checking that the property they protected still holds, because a stale
    assertion and a real regression look identical from here.

    WHAT THE OLD FLOOR WAS FOR. Tier 0 is operator-only. A watcher armed over unconsumed mail
    fires immediately by construction (wake_tiers' SEED rule), so on 2026-09-23 every arm
    exited within seconds against a 1,383-message backlog and four operator messages went
    unanswered for five days. `--min-tier 0` bought durability by ignoring everything that
    was not the human.

    WHY IT IS NOT NEEDED NOW, MEASURED RATHER THAN ASSUMED. `bifrost-standby` DRAINS and
    THEN arms, so the backlog is gone before the listener blocks -- it does not need an
    ultra-selective floor to survive it. Live receipt from this seat's own watcher,
    2026-10-02 19:17-23:16:

        drained: inbox already clean
        standby: inbox clean -- handing off to the wake listener (blocking)
        [standby] floor: tier 2 (settlement) | wakes 24h: 30
                  (22 with mail, 0 quiet, 8 deadline cycles; 11 held below floor)

    Four hours blocked at floor 2, not the instant exit the old failure mode predicts, and
    "11 held below floor" is the floor doing its job rather than being absent. The durability
    property MOVED from "be very selective" to "drain first", so this pin now guards the new
    mechanism instead of the old flag. If a future change arms WITHOUT draining, floor 0
    becomes load-bearing again -- which is why the drain is asserted, not just the verb.
    """
    from core.comm import wake_seat

    for state in ("unarmed", "dead-seat", "unknown"):
        text = _line(monkeypatch, state)
        # ONE SOURCE OF TRUTH: the remedy boot prints IS the canonical arm command. Asserting
        # a hand-written string here is what let boot and the stop-hook gate contradict each
        # other for weeks -- boot advertised a form that stamped origin "unknown" and the hook
        # then refused it.
        # The session suffix comes from the live environment, so pin the session-INDEPENDENT
        # stem: the lane env, the interpreter, the resolved cli path, the verb and the agent.
        # That is the whole shape that can drift; the session id is the renderer's own.
        stem = wake_seat.arm_command("claude", None)
        assert stem in text, (
            f"{state!r} does not hand back the canonical arm command.\n"
            f"  expected to contain: {stem!r}\n  got: {text!r}"
        )
        assert "bifrost-standby" in text, (
            f"{state!r} names a bare listener rather than the drain-then-arm verb. Arming "
            f"without draining is the 2026-09-23 starvation incident: a watcher armed over "
            f"unconsumed mail fires immediately and the seat stays unreachable."
        )
        assert "harness-tracked" in text, (
            f"{state!r} does not warn that a detached watcher fires into nothing -- the exact "
            f"trap that makes 'just arm it from the hook' wrong"
        )


def test_a_broken_wake_layer_never_renders_as_armed(monkeypatch):
    """Fail-loud, not fail-reassuring. If the wake state cannot be read at all, that is not
    evidence of reachability."""
    from core.comm import wake_seat

    def _boom(*a, **k):
        raise RuntimeError("redis is down")

    monkeypatch.setattr(wake_seat, "any_armed", _boom)
    text = ctxmod._reach_line("claude")
    assert "UNKNOWN" in text.upper()
    assert "armed" not in text.lower().replace("not 'armed'", "").replace("unreachable", "")


def test_the_reach_line_outranks_mail_in_the_whisper():
    """Unread mail says what arrived; reach says whether anything CAN. A seat that learns it
    has 2 unread and cannot be woken has the less useful of the two facts -- and the whisper
    drops sections bottom-up under budget, so order is survival order."""
    src = (ROOT / "agent" / "harness" / "context.py").read_text(encoding="utf-8")
    reach_at = src.index('sections.append(("reach"')
    mail_at = src.index('sections.append(("mail"')
    assert reach_at < mail_at, "the reach section must be appended before mail to outrank it"
