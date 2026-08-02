"""The hero avatar must not be lost to a race, and its SIZE must not depend on the GPU.

WHAT HAPPENED, 2026-08-02. Daniil screenshotted a composer still showing the 38px fallback
hexagon while the identical bytes rendered a two-inch avatar in my browser. Same commit, same
machine, different outcome -- which is the signature of a race, not of a cascade bug. I spent
four probes hunting the cascade anyway.

THE RACE. ``agent-avatar.js`` is a plain synchronous <script> at the END of <body>, after the
inline console script. ``mountHeroAvatar()`` was reachable ONLY through ``driveAvatars()``,
which runs on every status render -- and a status poll answered by localhost in well under a
millisecond can land DURING parse, before ``AgentAvatar`` is defined. The old guard was::

    if(typeof AgentAvatar === 'undefined' || !AgentAvatar.isSupported()){ _avatarsOff = true; return; }

so losing that race did not merely defer the avatar, it DISABLED it for the life of the page.
Three unlike conditions shared one latch: a script that has not parsed YET (transient), a host
with no WebGL2 (terminal), and a shader that will not compile (terminal).

THE SECOND DEFECT, which made the first invisible. Sizing ran AFTER the WebGL attempt, so every
bail left the frame at its base 38px -- identical to "the change was never deployed". A failure
that is indistinguishable from a no-op cannot be diagnosed from a screenshot, and that is
exactly what the round-trip cost.

THE FIX, in three parts:
  1. size first, unconditionally -- the shader is HOW the frame is beautiful, not WHETHER it
     exists, so a dead GPU yields a styled two-inch fallback rather than a hexagon;
  2. transient bails do not latch, and a DOMContentLoaded door mounts independently of the poll;
  3. the backing store is TOLD its size instead of measuring ``clientWidth``, which was a bet on
     layout having settled in the same tick that set the box.

SCOPE, stated plainly: these are STRUCTURAL pins over the served source, not behavioural ones.
This repo has no JS test harness, and a browser-driven test of a parse-time race would be
flakier than the defect. They cannot prove the avatar renders. They CAN prove nobody quietly
restores the single latch or moves sizing back behind the GPU check -- which is the regression
that actually happened and would otherwise recur silently.

Run::

    py -m pytest tests/test_hero_avatar_mount_is_race_free.py -q
"""
from __future__ import annotations

import io
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "scripts" / "bifrost_ui.py"
AV = ROOT / "scripts" / "agent-avatar.js"


@pytest.fixture(scope="module")
def ui() -> str:
    return io.open(UI, encoding="utf-8").read()


@pytest.fixture(scope="module")
def av() -> str:
    return io.open(AV, encoding="utf-8").read()


def _mount_body(ui: str) -> str:
    """The text of mountHeroAvatar(), which is where every one of these bugs lived."""
    i = ui.index("function mountHeroAvatar(")
    j = ui.index("\n}", i)
    return ui[i:j]


def test_a_missing_script_does_not_latch_avatars_off(ui):
    """THE RACE ITSELF. `typeof AgentAvatar === 'undefined'` is TRANSIENT -- the script is at the
    end of <body> and simply has not parsed yet. Latching on it converts a sub-millisecond
    ordering accident into a permanent verdict, and the loser of that race gets no avatar at all
    for the life of the page."""
    body = _mount_body(ui)
    m = re.search(r"typeof AgentAvatar === 'undefined'[^\n]*\n?[^\n]*", body)
    assert m, "the undefined-script guard vanished; this pin no longer guards anything"
    assert "_avatarsOff" not in m.group(0), (
        "the transient 'script has not parsed yet' guard latches _avatarsOff again -- a lost "
        f"parse race is once more permanent. Offending guard: {m.group(0)!r}")


def test_terminal_failures_still_latch(ui):
    """The converse, so the fix does not overshoot. No amount of waiting produces a GPU: a host
    without WebGL2 must latch, or every status poll retries a doomed context creation forever."""
    body = _mount_body(ui)
    i = body.index("isSupported()")
    assert "_avatarsOff = true" in body[i:i + 320], (
        "the no-WebGL2 path stopped latching -- a machine without WebGL2 will now retry context "
        "creation on every status poll")


def test_size_is_applied_before_the_webgl_guard(ui):
    """THE DEFECT THAT HID THE OTHER ONE. If sizing sits behind the GPU check, every failure
    renders as the original 38px frame -- indistinguishable from an undeployed change, and
    undiagnosable from a screenshot."""
    body = _mount_body(ui)
    assert body.index("sizeHeroFrame(frame)") < body.index("AgentAvatar"), (
        "sizing moved back behind the WebGL guard -- a shader failure is once again "
        "indistinguishable from 'the change never shipped'")


def test_there_is_a_mount_door_that_does_not_go_through_the_status_poll(ui):
    """The avatar is chrome, not data. Reaching it only via driveAvatars() meant a slow, failed
    or still-pending first poll decided whether the composer had a centrepiece."""
    assert re.search(r"DOMContentLoaded['\"]?\s*,\s*mountHeroAvatar", ui), (
        "the DOMContentLoaded mount door is gone; mounting depends on a status render again")


def test_a_dead_gpu_still_leaves_a_two_inch_frame(ui):
    """Both terminal bails must mark the frame so the degraded path is styled deliberately --
    a 14px glyph adrift in a 192px square reads as breakage, not as a fallback."""
    body = _mount_body(ui)
    assert body.count("av-fallback") >= 2, (
        f"expected both terminal bails to add .av-fallback, found {body.count('av-fallback')}")
    assert re.search(r"#ash-frame\.av-fallback\{[^}]*width:\s*192px", ui), (
        "the .av-fallback rule no longer holds the two-inch box")


def test_the_bail_reason_is_left_on_the_element(ui):
    """A silent permanent bail is what made this cost a screenshot and a round-trip. Every exit
    records WHY, and the success path clears it so a lost-then-won race leaves no stale reason."""
    body = _mount_body(ui)
    for reason in ("pending-script", "no-webgl2", "ctor: "):
        assert reason in body, f"bail reason {reason!r} no longer recorded on the frame"
    assert "delete frame.dataset.avOff" in body, (
        "the success path no longer clears avOff -- a frame that recovered from a lost race "
        "still advertises 'pending-script'")


def test_the_backing_store_is_told_its_size_not_asked_to_measure(ui, av):
    """clientWidth is only correct once layout has settled on a size set moments earlier. Losing
    that bet cuts a thumbnail-sized render target, and the backing store is re-cut only on
    resize -- so the blur persists no matter how many frames are drawn afterwards."""
    assert "_resize = function (cssSize)" in av, (
        "_resize no longer accepts an explicit size and is back to guessing from clientWidth")
    assert "this.cssSize ||" in av, "the explicit size is not preferred over the measurement"
    assert "_heroAv.shader._resize(SIZE)" in _mount_body(ui), (
        "the mount stopped passing the known size, reintroducing the layout-timing bet")
