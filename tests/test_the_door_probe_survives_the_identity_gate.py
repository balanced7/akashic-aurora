"""RED pins: the identity gate refuses the door probe, and the door probe blocks every push.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

A GATE-ON-GATE COLLISION, found 2026-10-07 the moment Daniel said "lets push commits".

    [door-gate] the MCP door must answer before anything ships
    door: RED (1.01s) -- boot_render_broken: boot returned 356 chars without its CONTEXT header
    [door-gate] BLOCKED: the MCP door is not healthy.
    error: failed to push some refs to 'https://github.com/balanced7/akashic-aurora.git'

The MCP door is NOT broken. ``py agent_cli.py boot claude`` renders 16,300 characters with its
CONTEXT header, healthy, through the same code path the probe claims to share.

WHAT ACTUALLY HAPPENS. core/comm/door_probe.py:221 calls the boot tool as a hardcoded synthetic
resident::

    s.call_tool("boot", {"agent": "door-probe", "task": "door probe -- ..."})

and T418's identity gate refuses it, correctly and by design::

    REFUSED: this session is 'claude' (from its binding stamp) and asked to boot as 'door-probe'.
    The boot door serves a resident its OWN record only; a packet for 'door-probe' would hand you
    another resident's identity, mail and history (T418). Boot as 'claude'. If you really mean to
    read 'door-probe''s packet, set AKASHIC_BOOT_AS_OTHER=1 for that one call.

The probe then looks for ``# CONTEXT for door-probe``, does not find it in a refusal, and reports
``boot_render_broken``. A correct refusal is rendered as a broken door.

THE DATES SETTLE IT, and this is why it is worth a pin rather than a quiet patch:

    last successful push          2026-09-30   53a73fea
    GREEN: T418 identity-grounded boot  2026-10-01   90ae6f32

**The last push is the day before T418 landed.** 173 commits and seven days of work have been
dammed behind a health check that has been reporting a false RED since the hour a different,
correct gate shipped. Nobody noticed because the two organs are owned by different arcs and each
one is behaving exactly as its own author intended.

THE SHAPE, which is the transferable part: a HEALTH PROBE that impersonates a fake identity will
be refused the moment identity becomes real. The probe's assumption ("I may boot as anyone") was
true when it was written and silently became false. And its failure mode points at the wrong
organ -- its own remedy text says "compare against `py agent_cli.py boot <you>`, which shares the
code path", which is precisely the comparison that shows the door is FINE and sends the reader
hunting in the wrong subsystem.

WHAT A FIX MUST PRESERVE: the probe exists because `boot` is "a verb whose body spawns a child" --
it is the one call that proves the MCP door can execute a real nested boot rather than merely
answer tools/list. A fix that stops calling boot, or that accepts any output, throws away the only
thing the probe was for.

Run::

    py -m pytest tests/test_the_door_probe_survives_the_identity_gate.py -q
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PROBE = ROOT / "core" / "comm" / "door_probe.py"


def _src() -> str:
    return PROBE.read_text(encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ the defect
def test_the_boot_the_probe_asks_for_is_one_the_gate_allows():
    """THE PIN, measured against the live gate rather than asserted.

    Runs the real boot door with the identity the probe uses and requires it not to be refused.
    This is the whole bug in one call: the probe asks for a packet T418 exists to withhold.
    """
    src = _src()
    tree = ast.parse(src)
    asked = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = getattr(node.func, "attr", None)
        if fn != "call_tool":
            continue
        for a in node.args:
            if isinstance(a, ast.Dict):
                for k, v in zip(a.keys, a.values):
                    if getattr(k, "value", None) == "agent" and isinstance(v, ast.Constant):
                        asked = v.value
    if asked is None:
        # The literal is gone, which is the fix -- but a SKIP is not a PASS, and a pin that stops
        # asserting the moment its subject changes shape is how a defect comes back. Resolve the
        # identity the probe NOW uses and hold that to the same standard: whoever it boots as, the
        # gate must not refuse them.
        from core.comm import seat_identity as _si
        sid = os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("BIFROST_INCARNATION") or ""
        asked = _si.resolve(sid)
        if not asked or asked.startswith("unknown-"):
            # mirror the probe's own fallback chain exactly
            asked = (os.environ.get("AKASHIC_AGENT_ID") or "claude").strip()
        assert asked and not asked.startswith("unknown-"), (
            "the probe resolves its boot identity to %r, which the gate will refuse just as it "
            "refused 'door-probe'" % (asked,))

    env = dict(os.environ)
    env.pop("AKASHIC_BOOT_AS_OTHER", None)
    r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "agent_cli.py"),
                        "boot", str(asked), "--task", "door probe"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), timeout=300, env=env)
    out = r.stdout + r.stderr
    # ASSERT THE POSITIVE. A first draft of this checked `"REFUSED" not in out` and went red
    # against a WORKING boot, because the 16 KB render legitimately contains the word inside a
    # recalled lesson. Searching a document for a vocabulary item says nothing about what the
    # document IS -- the same mistake this file is about, one layer up. The header is the thing
    # the probe itself keys on, so it is the thing to require.
    refused_here = out.lstrip().startswith("REFUSED")
    assert ("# CONTEXT for %s" % asked) in out and not refused_here, (
        "the probe boots as %r and the identity gate REFUSES it, so the health check reports "
        "boot_render_broken against a door that is fine. `py agent_cli.py boot claude` renders "
        "16,300 chars with its CONTEXT header. Last successful push 2026-09-30; T418 landed "
        "2026-10-01; 173 commits have been dammed behind this since.\n%s" % (asked, out[:400]))


def test_the_probe_does_not_assert_a_header_for_an_identity_it_cannot_be():
    """The same defect from the assertion side. The probe requires `# CONTEXT for door-probe`,
    a string only producible by booting AS door-probe -- which is the thing the gate forbids. The
    check and the call have to agree about who is booting."""
    src = _src()
    if '"door-probe"' not in src and "'door-probe'" not in src:
        return                                        # the literal is gone; nothing to contradict
    assert "CONTEXT for door-probe" not in src, (
        "the probe still hardcodes the header `# CONTEXT for door-probe`, which only a boot AS "
        "door-probe can emit. T418 refuses that boot by design, so this assertion can never pass "
        "again on a seat with a binding stamp.")


# ------------------------------------------------------------------ ratchets
def test_the_probe_still_calls_boot():
    """RATCHET, and the one a lazy fix would break. The probe exists because boot is the verb
    whose body spawns a child -- the only call that proves the door can execute a real nested boot
    rather than just answer tools/list. Making the probe green by not calling boot is not a fix."""
    src = _src()
    assert '"boot"' in src or "'boot'" in src, (
        "the probe no longer calls the boot tool, so it no longer proves the MCP door can run a "
        "verb whose body spawns a child -- which is the only reason it exists")


def test_the_probe_still_fails_loudly_on_a_real_breakage():
    """RATCHET. boot_render_broken must survive as a verdict; the fix is to stop triggering it
    falsely, not to delete the detection."""
    src = _src()
    assert "boot_render_broken" in src, "the probe lost its render verdict entirely"
    assert "roster_drift" in src, "the probe lost its tools/list verdict"


def test_the_identity_gate_itself_is_untouched():
    """RATCHET ON THE OTHER GATE, and the important one. T418 is CORRECT: a seat must not be
    handed another resident's identity, mail and history. The fix belongs in the probe. If this
    goes red, someone 'fixed' the push by punching a hole in the thing that protects identity."""
    env = dict(os.environ)
    env.pop("AKASHIC_BOOT_AS_OTHER", None)
    r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "agent_cli.py"),
                        "boot", "some-other-resident", "--task", "probe"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), timeout=300, env=env)
    out = r.stdout + r.stderr
    assert "REFUSED" in out and "T418" in out, (
        "booting as an arbitrary other resident is no longer refused. T418 is not the bug here; "
        "the probe is. Output:\n%s" % out[:400])
