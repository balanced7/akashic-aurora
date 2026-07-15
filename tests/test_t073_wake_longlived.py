"""T073 Phase 3 pins -- the long-lived watcher (deepseek Design 3, adopted verbatim by
research/reviewed/t073-wake-reconciliation-2026-07-15.md): P7 (survives past the old
30-min deadline without re-arm), P8 (near-deadline exit writes the re-arm trigger),
P9 (stop hook stays the BACKSTOP -- dead watcher still blocks, message reworded to
re-launch-ONCE semantics).

BUILD REFINEMENTS (flagged, T073's own precedent):
  R17  The 4h deadline is the DEFAULT (BIFROST_WAKE_DEADLINE_S overrides;
       BIFROST_WAKE_LONGLIVED=0 reverts to the legacy 1800s) -- land kill-switched
       per the reconciliation's build order.
  R18  The trigger is written ONLY on a deadline self-cycle -- never on mail exits
       (the session is already waking for work) and never on stand-downs (the seat's
       owner re-arms via the backstop; a trigger there would double-arm).
  R19  Arm time clears any stale trigger for this seat (the re-arm it requested has
       happened).
"""
import json
import os
import subprocess
import sys
import time as real_time
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import bifrost_wake as bw

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FakeClock:
    def __init__(self, start=1_000_000.0):
        self.now = start

    def time(self):
        return self.now


class FakeApi:
    """wake_block advances the fake clock one chunk and serves the scripted mail."""

    online_now = True

    def __init__(self, clock, chunk_s, mail_at=None, mail=None):
        self.clock, self.chunk_s = clock, chunk_s
        self.mail_at, self.mail = mail_at, mail or []

    def online(self):
        pass

    def wake_block(self, timeout_ms=0):
        self.clock.now += self.chunk_s
        if self.mail_at is not None and self.clock.now >= self.mail_at:
            self.mail_at = None
            return list(self.mail)
        return []


def _msg(kind="handoff", frm="deepseek"):
    return SimpleNamespace(kind=kind, frm=frm, content="work", meta={})


def _seat(tmp_path, pid=4242):
    p = os.path.join(str(tmp_path), "bifrost_wake_claude_s1.pid")
    with open(p, "w") as f:
        f.write(str(pid))
    return p


# ---------------------------------------------------------------- P7 long-lived
def test_p7_watcher_survives_past_the_old_thirty_minute_deadline(tmp_path, monkeypatch, capsys):
    clock = FakeClock()
    monkeypatch.setattr(bw.time, "time", clock.time)
    seat = _seat(tmp_path)
    api = FakeApi(clock, chunk_s=120, mail_at=clock.now + 2400, mail=[_msg()])  # mail at t+40min
    rc = bw.watch("claude", 14400, 120_000, api=api, hb_path=seat, my_pid=4242, session_id="s1")
    out = capsys.readouterr().out
    assert rc == 0
    assert "BIFROST WAKE -- messages" in out, \
        "P7: a 4h watcher must still be LISTENING at t+40min (old default would have died at 30)"


# ---------------------------------------------------------------- P8 self-cycle trigger
def test_p8_near_deadline_exit_writes_rearm_trigger(tmp_path, monkeypatch, capsys):
    clock = FakeClock()
    monkeypatch.setattr(bw.time, "time", clock.time)
    monkeypatch.setattr(bw.tempfile, "gettempdir", lambda: str(tmp_path))
    seat = _seat(tmp_path)
    api = FakeApi(clock, chunk_s=120)                      # never any mail
    rc = bw.watch("claude", 300, 120_000, api=api, hb_path=seat, my_pid=4242, session_id="s1")
    out = capsys.readouterr().out
    assert rc == 0, "a deadline self-cycle is a BENIGN ending (exit 0, Wave-2 contract)"
    trig = bw.rearm_trigger_path("claude", "s1", tmp=str(tmp_path))
    assert os.path.exists(trig), "P8: the near-deadline exit must write the re-arm trigger"
    body = open(trig, encoding="utf-8").read()
    assert "re-arm" in body.lower() and "bifrost_wake" in body, \
        "the trigger carries the instruction, not just a timestamp"
    assert "self-cycle" in out.lower()


def test_r18_mail_exit_writes_no_trigger(tmp_path, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(bw.time, "time", clock.time)
    monkeypatch.setattr(bw.tempfile, "gettempdir", lambda: str(tmp_path))
    seat = _seat(tmp_path)
    api = FakeApi(clock, chunk_s=120, mail_at=clock.now + 240, mail=[_msg()])
    bw.watch("claude", 14400, 120_000, api=api, hb_path=seat, my_pid=4242, session_id="s1")
    assert not os.path.exists(bw.rearm_trigger_path("claude", "s1", tmp=str(tmp_path))), \
        "R18: waking FOR MAIL is not a deadline cycle -- no trigger"


def test_r18_stand_down_writes_no_trigger(tmp_path, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(bw.time, "time", clock.time)
    monkeypatch.setattr(bw.tempfile, "gettempdir", lambda: str(tmp_path))
    seat = _seat(tmp_path, pid=9999)                       # someone ELSE owns the seat
    api = FakeApi(clock, chunk_s=120)
    rc = bw.watch("claude", 14400, 120_000, api=api, hb_path=seat, my_pid=4242, session_id="s1")
    assert rc == 0
    assert not os.path.exists(bw.rearm_trigger_path("claude", "s1", tmp=str(tmp_path))), \
        "R18: a displaced watcher stands down silently -- the seat owner re-arms via backstop"


# ---------------------------------------------------------------- R17 deadline resolution
def test_r17_default_deadline_is_long_and_killswitch_reverts(monkeypatch):
    monkeypatch.delenv("BIFROST_WAKE_DEADLINE_S", raising=False)
    monkeypatch.delenv("BIFROST_WAKE_LONGLIVED", raising=False)
    assert bw.default_deadline_s() == 14400, "R17: 4 hours is the new default"
    monkeypatch.setenv("BIFROST_WAKE_LONGLIVED", "0")
    assert bw.default_deadline_s() == 1800, "R17: the kill-switch restores the legacy 30min"
    monkeypatch.delenv("BIFROST_WAKE_LONGLIVED", raising=False)
    monkeypatch.setenv("BIFROST_WAKE_DEADLINE_S", "7200")
    assert bw.default_deadline_s() == 7200, "R17: the env dial wins when set"


# ---------------------------------------------------------------- R19 arm clears trigger
def test_r19_arm_time_clears_stale_trigger(tmp_path, monkeypatch):
    monkeypatch.setattr(bw.tempfile, "gettempdir", lambda: str(tmp_path))
    trig = bw.rearm_trigger_path("claude", "s1", tmp=str(tmp_path))
    with open(trig, "w") as f:
        f.write("stale re-arm request")
    bw.clear_rearm_trigger("claude", "s1", tmp=str(tmp_path))
    assert not os.path.exists(trig), "R19: arming IS the requested re-arm -- the trigger clears"


# ---------------------------------------------------------------- P9 backstop reword
def test_p9_dead_watcher_still_blocks_with_backstop_wording(tmp_path):
    env = dict(os.environ)
    env["AKASHIC_AGENT_ID"] = "p9probe"                    # namespaced guard files, no seat
    payload = json.dumps({"session_id": f"p9-{real_time.time():.0f}", "transcript_path": ""})
    r = subprocess.run([sys.executable, os.path.join("scripts", "hooks", "claude_stop.py")],
                       input=payload, capture_output=True, text=True, timeout=60,
                       cwd=REPO, env=env)
    out = r.stdout.strip()
    assert out, "P9: an unarmed session's stop MUST still block (the backstop lives)"
    data = json.loads(out.splitlines()[-1])
    assert data.get("decision") == "block"
    reason = data.get("reason", "").lower()
    assert "once" in reason and ("died" in reason or "cycled" in reason), \
        f"P9: the block message carries re-launch-ONCE backstop semantics, got: {reason[:200]}"
