"""PRE-REGISTERED ACCEPTANCE (T155) -- the fleet's liveness gauges must not contradict each other.

MEASURED 2026-08-03/04, one session, one seat. I asked four surfaces about `codex_root`:

  bifrost-sync   ->  "online: claude, codex_root, kimi"
  bifrost-send   ->  "UNATTENDED RECIPIENT: 'codex_root' has no live seat (no heartbeat on record)"
  pulse          ->  codex_root absent; a near-identical id `codex_root_019fab2d` CRITICAL, backlog 75
  roster         ->  no codex seat among 40

A directed brief addressed exactly as that seat itself requested was therefore queued where
nothing would read it. The opposite failure fired the same night: kimi paged HARD WEDGE --
phase "running" with a beating worklive key for 996s while the worker had died inside the turn.

ROOT CAUSE, and it is not a bug in either function -- it is TWO MEANINGS OF ONE WORD.
`Bus.presence()` (core/comm/bus.py) lists `{ns}:presence:*` REGISTRATION keys: it answers
"who registered recently". `Bus._recipient_liveness()` -- the send path -- answers "who is
ATTENDING right now", consulting the roster beat, then the progress pulse, then the worklive
beat, each addition bought by a real incident (T133/M4). `agent/bifrost_pull.py:42` feeds the
first into a line that says "online:", so a registration echo renders as attendance.

WHY IT BLOCKS THE SEASON. At 10-20 players a wedged seat keeps its heartbeat and scores zero,
and the scoreboard cannot distinguish that from a live player who found nothing. That is the
"unpopulated counter renders as a MEASURED zero" hazard promoted into the fitness function.

  L1  ONE verdict: a public attendance probe exists, and the send path uses it (not a private twin)
  L2  AGREEMENT: whatever bifrost-send would call unattended, the boot render must NOT call online
  L3  UNKNOWN, never LIVE: when the probe cannot determine attendance, it says so -- absence of
      evidence must not render as evidence of presence (pairs with T141 MEASURED/UNKNOWN/UNDEFINED)
  L4  NEVER RAISES: a liveness probe that throws must not take a caller down -- it degrades to
      UNKNOWN, because a transport that refuses to send because it cannot check is worse than one
      that sends blind (the existing _warn_if_unattended contract, preserved)
  L5  ID RECONCILIATION: an `agent_<session>` style id resolves to the same attendance answer as
      its bare agent id, so mail cannot queue into a void under a near-identical name

Run: py -m pytest tests/test_t155_one_liveness_verdict.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def test_l1_a_public_attendance_probe_exists():
    """The send path's verdict must be reusable. While it is private (`_recipient_liveness`),
    every other surface is forced to invent its own weaker answer -- which is exactly how
    presence-keys came to be printed as 'online'."""
    from core.comm import liveness
    assert hasattr(liveness, "attendance"), (
        "no public attendance probe: core.comm.liveness.attendance(agent) must exist so every "
        "surface can share ONE verdict instead of reimplementing a weaker one")


def test_l3_unknown_is_a_real_state_not_a_false_live():
    """The probe reports three states. A gauge that cannot check must say UNKNOWN."""
    from core.comm.liveness import attendance
    verdict = attendance("almost-certainly-not-a-real-agent-t155")
    assert hasattr(verdict, "state"), "attendance() must return a verdict carrying .state"
    assert verdict.state in ("ATTENDED", "UNATTENDED", "UNKNOWN"), \
        f"unexpected state {verdict.state!r}"
    assert verdict.state != "ATTENDED", "a nonexistent agent must never read as ATTENDED"


def test_l4_the_probe_never_raises(monkeypatch):
    """A probe that throws must degrade to UNKNOWN, never propagate. Behavioural, not textual:
    break the underlying roster read and demand a verdict anyway."""
    from core.comm import liveness

    def _boom(*a, **k):
        raise RuntimeError("probe exploded")

    monkeypatch.setattr(liveness, "worklive_beat_age", _boom, raising=False)
    monkeypatch.setattr(liveness, "progress_age", _boom, raising=False)
    verdict = liveness.attendance("any-agent-t155")
    assert verdict.state in ("UNATTENDED", "UNKNOWN"), \
        f"a broken probe must degrade, got {verdict.state!r}"


def test_l2_the_boot_render_agrees_with_the_send_path():
    """The defect, pinned directly: an agent the send path would warn about must not appear in
    the boot block's `agents_online`. Uses whatever the live bus reports -- if the fleet is
    quiet this is vacuously true, which is honest; it fails loudly the moment they diverge."""
    from agent.bifrost_pull import register_presence
    from core.comm.liveness import attendance

    block = register_presence("t155-probe")
    listed = list(block.get("agents_online") or [])
    disagreements = [a for a in listed if attendance(a).state == "UNATTENDED"]
    assert not disagreements, (
        f"boot prints 'online:' for agent(s) the send path would call UNATTENDED: {disagreements} "
        f"-- a registration echo is being rendered as attendance")


def test_l5_a_suffixed_incarnation_id_resolves_like_its_bare_agent():
    """`codex_root_019fab2d` and `codex_root` must not give different attendance answers, or
    directed mail queues into a void under a near-identical name (measured tonight)."""
    from core.comm.liveness import attendance
    bare = attendance("t155-ghost")
    suffixed = attendance("t155-ghost_019fab2d")
    assert bare.state == suffixed.state, (
        f"id form changes the verdict: bare={bare.state} suffixed={suffixed.state} -- mail "
        f"addressed to the suffixed form would queue where nothing reads it")
