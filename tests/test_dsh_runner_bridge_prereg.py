"""PRE-REGISTERED pins for the DSH web-seat runner bridge (M3, registered 2026-08-26).

Registered BEFORE the implementation exists, and committed alone, per M3: no slice
ships whose acceptance postdates its implementation. Every assertion here is expected
to be RED at registration time. Do not weaken a pin to make it pass -- if a pin is
wrong, the fence reviews it and it changes by ruling, not by convenience.

THE PROBLEM. The DSH web seat (dsh_agent / Rill) cannot act on arriving mail. Mail
lands on his bus lane and sits there, because nothing turns a message into a TURN. He
has been reachable only when a human types into his browser. That is the gap this
bridge closes.

THE DESIGN under test is Rill's, authored 2026-08-26 from harness source and preserved
in note web-seat-runner-design-2026-08-26. Its load-bearing claim: a cordis plugin CAN
create a turn, because dsh-agent ships a per-agent Inbox whose 'next-turn' lane is
documented as "Prompts awaiting individual turns". append/prepend/splice are the public
writes, claim() is loop-internal, and every mutation persists as an agent/inbox/spliced
event -- so a queued turn survives a restart. Appending one UserMessage wakes an idle
seat through the loop's own inserted -> hasPending -> wakeDriver path.

WHY THESE PINS AND NOT OTHERS. Four of the six are SAFETY pins, not feature pins. A
mechanism that manufactures turns from network input is exactly the mechanism that
must never let network input choose what the turn SAYS. The fleet spent 2026-08-26
paying for absences that rendered as normal; this file exists so that this particular
mechanism cannot fail silently or fail open.

RED AT REGISTRATION: five of the six. The sixth
(test_the_bridge_never_restarts_its_own_host) is a PROHIBITION pin and is green from
birth -- nothing violates it because nothing exists yet. That is not evidence the rule
holds; it is a tripwire for the day someone reaches for the convenient thing. Read its
pass as "not yet violated", never as "verified".

THE LIVE PIN THIS FILE CANNOT CARRY: "append while idle -> turn/start appears" needs a
running host and belongs in a drill with a dated receipt (house doctrine: a recovery
path ships with an executed drill or is presumed broken). These static pins constrain
the SHAPE; the drill proves the BEHAVIOUR. Neither substitutes for the other.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "agent" / "harness" / "dsh_plugin" / "lib" / "index.js"


def _src() -> str:
    return PLUGIN.read_text(encoding="utf-8")


def test_wake_decision_is_spawned_not_reimplemented_in_js():
    """The ticker spawns scripts/bifrost_wake.py; it never re-decides wake in JS.

    Rill's must-not, and the sharpest one. The wake decision carries the ratchet,
    the operator override, seen-dedup, lane mode and the seat file. A JS copy would
    be a SECOND definition that drifts from the first, and drift in a wake decision
    means either a seat that never wakes or one that wakes on everything. One
    definition, spawned as a child, so `doctor` sees the seat armed by the same
    evidence it already knows how to read.
    """
    src = _src()
    assert "bifrost_wake" in src, (
        "no reference to bifrost_wake.py: the wake decision must be SPAWNED from the "
        "single Python definition, not reimplemented in the plugin")
    assert not re.search(r"\bwake_worthy\b|\bwakeWorthy\b", src), (
        "wake_worthy appears to be reimplemented in JS -- that is the forbidden "
        "second definition of the wake decision")


def test_arriving_mail_becomes_a_turn_via_the_next_turn_inbox():
    """The seam is the documented Inbox lane, not a synthesized keystroke."""
    src = _src()
    assert "next-turn" in src, (
        "no 'next-turn' lane write: the bridge must append through the harness's own "
        "durable Inbox primitive, which survives restarts, rather than driving the UI")
    assert re.search(r"\.inbox\b", src), (
        "no inbox handle: the design requires ctx.agents.get(sid).inbox")


def test_the_appended_prompt_is_harness_authored_and_peer_content_is_data():
    """PEER CONTENT IS DATA, NEVER INSTRUCTION -- the security pin of this file.

    A bridge that pastes an arriving message into a prompt hands every peer on the bus
    (and anything upstream of a peer) the ability to author this seat's instructions.
    The appended turn must be a FIXED harness-authored string that tells the seat to go
    READ its mail through its own door. What the mail says is then something the seat
    reads as data, with its own judgement intact, exactly as a human-typed 'check your
    inbox' would leave it.
    """
    src = _src()
    marker = re.search(
        r"(PEER CONTENT IS DATA|peer content is data|never instruction|"
        r"NEVER instruction|data, never instruction)", src)
    assert marker, (
        "the fixed-prompt law is not stated at the append site: the appended turn must "
        "be harness-authored, and arriving peer text must never become instruction")


def test_one_watcher_per_seat():
    """Duplicate watchers double every wake and race the same cursor.

    This house has already paid for duplicate long-lived processes twice today: four
    concurrent Discord gateways at 00:20, and two kimi daemons still running now. A
    spawner with no singleton guard is the known shape of that bug.
    """
    src = _src()
    assert re.search(
        r"(alreadyRunning|watcherAlive|singleton|oneWatcher|if\s*\(\s*watcher\s*\))", src), (
        "no singleton guard around the watcher spawn: nothing stops a second watcher "
        "from being armed for the same seat")


def test_the_bridge_never_restarts_its_own_host():
    """Rill's must-not: never restart the host from inside its own turn.

    A process that can restart the host it runs inside can kill the turn that decided
    to restart it, losing the reason. Restarts stay an outside-in operator lever.
    """
    src = _src()
    for forbidden in ("dsh web", "restartHost", "restart_host"):
        assert forbidden not in src, (
            f"{forbidden!r} appears in the plugin: the bridge must never restart the "
            f"host it is running inside")


def test_external_ui_driver_is_defibrillator_only():
    """Rill's ruling on my own afternoon's work, pinned so it cannot quietly regress.

    Driving the browser is legitimate ONLY when the host is down (the presence beat is
    stale). While the beat is healthy, turns come from the inbox seam. An external
    driver competing with a live host would interleave two writers on one session.
    """
    src = _src()
    assert re.search(r"(defibrillator|beat is stale|staleBeat|stale_beat)", src), (
        "the defibrillator boundary is not stated: an external UI driver must be gated "
        "on a STALE presence beat, never used against a healthy host")
