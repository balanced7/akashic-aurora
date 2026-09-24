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
    """Naming a problem without its remedy is how a warning becomes wallpaper."""
    for state in ("unarmed", "dead-seat", "unknown"):
        text = _line(monkeypatch, state)
        assert "bifrost_wake.py" in text, f"{state!r} names no remedy: {text!r}"
        assert "--min-tier 0" in text, (
            f"{state!r} omits the tier floor. Tier 0 is operator-only and is what makes the "
            f"watcher DURABLE -- a tier-1 watcher is consumed instantly by ordinary peer mail, "
            f"which is how this looked broken on the first attempt."
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
