"""W47 pins — clobber-scan: unconditional shared-control-key writes, flagged statically.

DESIGN: kimi (tools hunt #3, research/reviewed/kimi-tools-hunt-tonight-2026-07-21.md).
BUILD: claude (kimi's headless builder round stalled; built from their spec + credited,
fence invited). Born from K2: kimi's own pause-clobber race
(control.pause = unconditional c.set(_pause_key()) voiding a human pause) rested on one
lucky trace. This makes the class systematic: every mutating ceremony under fence review
is the audience, including claude's all night.

  P1  an unconditional write to a control-key family is FLAGGED
  P2  a write GUARDED by a same-family read within the window is NOT flagged (the
      was_paused pattern kimi's K2 amendment added must read CLEAN now -- the fix proves out)
  P3  a non-control write (a data/telemetry key) is ignored (scoped to control families)
  P4  empty input is clean; findings carry line_no + family + snippet
  P5  LIVE: control.pause's own set IS guarded at its callers via was_paused (the storm
      ceremony) -- but the primitive itself is unconditional by contract, so scanning the
      CALLER (storm block) reads clean, proving the amendment landed
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.toolbelt import clobber_scan as cs


def test_p1_unconditional_control_write_flagged():
    text = 'def f():\n    c.set(_pause_key(), "frozen")\n'
    findings = cs.scan(text)
    assert len(findings) == 1
    assert findings[0]["family"] == "pause" and findings[0]["line_no"] == 2


def test_p2_guarded_write_not_flagged():
    # the guard reads at the TOP of the function; the write is many lines below (the real
    # K2 ceremony shape) -- function-scope tracking clears it where a line-window couldn't.
    text = ('def ceremony():\n'
            '    was_paused = control.is_paused()\n'
            + '    log("step")\n' * 20 +
            '    c.set(_pause_key(), "frozen")\n'
            '    control.resume()\n')
    assert cs.scan(text) == [], "a same-family guard earlier in the DEF clears later writes"


def test_p2b_guard_does_not_leak_across_defs():
    # the guard in one function must NOT clear an unguarded write in the NEXT
    text = ('def guarded():\n    was_paused = control.is_paused()\n    control.pause()\n'
            'def naked():\n    control.pause()\n')
    findings = cs.scan(text)
    assert len(findings) == 1 and findings[0]["line_no"] == 5, \
        "def resets guard scope -- the second function's bare pause still flags"


def test_p3_non_control_write_ignored():
    text = 'c.set(f"{ns}:turn_metrics:{a}", "3")\nc.delete(f"{ns}:mailbox:pos")\n'
    assert cs.scan(text) == [], "telemetry/projection writes are not control-plane clobbers"


def test_p4_empty_and_shape():
    assert cs.scan("") == []
    f = cs.scan('c.delete(_halt_key(agent))\n')[0]
    assert set(f) >= {"line_no", "family", "snippet", "why"} and "halt" in f["family"]


def test_p5_live_storm_block_reads_clean():
    # THE REAL PROOF: scan the live storm auto-clear ceremony in the runner. kimi's K2
    # was_paused guard reads at the top and control.resume() fires ~30 lines below; the
    # function-scope tracking must find that guard so the fixed code reads CLEAN for the
    # pause/resume families (the fixed-window version cried wolf here -- the reason for A3).
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "scripts", "bifrost_runner_deepseek.py"), encoding="utf-8").read()
    # isolate the storm ceremony: from '_was_paused = control.is_paused()' to '_storm.reset()'
    start = src.find("_was_paused = control.is_paused()")
    end = src.find("_storm.reset()", start)
    assert start > 0 and end > start, "storm ceremony markers present in the runner"
    block = "def _storm_ceremony():\n" + src[start:end]
    pause_hits = [f for f in cs.scan(block) if cs._surface(f["family"]) == "pause"]
    assert pause_hits == [], \
        f"the K2 was_paused-guarded storm ceremony must read clean for the pause surface: {pause_hits}"
