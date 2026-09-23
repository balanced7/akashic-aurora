"""THE BLIND SHIFT -- a quiet watch and a dead watch must never print the same sentence.

wake_block/_drain return [] for BOTH "nothing arrived in the window" AND "the bus is
unreachable" (bus.py's own docstring: "Returns [] on timeout/offline"). watch() probes
api.online_now ONCE at arm time -- correctly, with its own exit code 2 -- and then never
consults it again. So an outage that BEGINS mid-shift is invisible for the remainder of the
shift, and the watcher reports its quiet expiry exactly as though it had been watching.

MEASURED CASUALTY (2026-09-23): a remote-bridge watch ran three consecutive 600-minute shifts
and printed "no new peer mail in 600 min -- nothing lost" each time. Had Redis dropped at
minute five it would have printed exactly that, three times. The operator was told a five-day
peer silence was MEASURED. It was measured by an instrument that checked once and then assumed
for ten hours.

These pins hold the distinction that makes the difference reportable:
  B1  bus dies mid-shift  -> exit 2, LOUD, and the shift ENDS rather than running out the clock
  B2  the report names it as unobserved, never as absent
  B3  a healthy quiet shift is UNAFFECTED (no false positive on the thing we still want)
  B4  the probe never runs on the mail path (an arriving message is never taxed by it)
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import bifrost_wake as bw


class FakeClock:
    def __init__(self, start=1_000_000.0):
        self.now = start

    def time(self):
        return self.now


class FakeApi:
    """wake_block advances the clock one chunk; the bus may drop partway through."""

    def __init__(self, clock, chunk_s, offline_after_s=None, mail_at=None, mail=None):
        self.clock, self.chunk_s = clock, chunk_s
        self.offline_after_s = offline_after_s
        self.started = clock.now
        self.mail_at, self.mail = mail_at, mail or []
        self.online_probes = 0

    @property
    def online_now(self):
        self.online_probes += 1
        if self.offline_after_s is None:
            return True
        return (self.clock.now - self.started) < self.offline_after_s

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


def _watch(api, tmp_path, monkeypatch, clock, deadline_s=36_000):
    monkeypatch.setattr(bw.time, "time", clock.time)
    monkeypatch.setattr(bw.tempfile, "gettempdir", lambda: str(tmp_path))
    seat = _seat(tmp_path)
    return bw.watch("claude", deadline_s, 120_000, api=api, hb_path=seat,
                    my_pid=4242, session_id="s1")


# ------------------------------------------------------------------ B1 + B2
def test_b1_bus_dying_mid_shift_ends_the_watch_loudly(tmp_path, monkeypatch, capsys):
    """A 600-minute shift whose bus drops at minute 5 must not run to expiry reporting quiet."""
    clock = FakeClock()
    # 10-hour shift, 120s chunks, bus unreachable after 5 minutes
    api = FakeApi(clock, chunk_s=120, offline_after_s=300)
    rc = _watch(api, tmp_path, monkeypatch, clock, deadline_s=36_000)
    out = capsys.readouterr().out

    assert rc == 2, ("B1: a mid-shift outage must exit with the OFFLINE code the arm-time probe "
                     f"already uses, not a benign 0 -- got {rc}")
    assert "OFFLINE mid-watch" in out, "B1: the outage must be named in the report"

    elapsed_min = (clock.now - 1_000_000.0) / 60.0
    assert elapsed_min < 60, (
        "B1: the watch must END at the outage, not run out a 600-minute clock while blind -- "
        f"it kept going for {elapsed_min:.0f} min")

    # B2: the report must distinguish unobserved from absent. "nothing lost" is the sentence a
    # QUIET shift prints; a blind shift printing it is the entire defect.
    assert "SHIFT TRUNCATED" in out and "unobserved, not absent" in out, \
        "B2: a truncated shift must say so, in the vocabulary of unobserved-vs-absent"
    assert "nothing lost" not in out, \
        "B2: a blind shift must never borrow the quiet shift's reassurance"


# ------------------------------------------------------------------ B3 no false positive
def test_b3_a_healthy_quiet_shift_is_unaffected(tmp_path, monkeypatch, capsys):
    """The thing we still want: a genuinely quiet watch on a live bus reports quiet, benignly."""
    clock = FakeClock()
    api = FakeApi(clock, chunk_s=120, offline_after_s=None)   # never drops
    rc = _watch(api, tmp_path, monkeypatch, clock, deadline_s=3_600)
    out = capsys.readouterr().out

    assert rc == 0, f"B3: a quiet shift on a live bus is BENIGN -- got {rc}"
    assert "OFFLINE mid-watch" not in out, \
        "B3: a live bus must never be reported as an outage (the probe must not flap)"


# ------------------------------------------------------------------ B4 mail path untaxed
def test_b4_the_probe_never_runs_on_the_mail_path(tmp_path, monkeypatch, capsys):
    """An arriving message exits on mail; the liveness probe is for EMPTY returns only."""
    clock = FakeClock()
    api = FakeApi(clock, chunk_s=120, offline_after_s=None,
                  mail_at=clock.now + 120, mail=[_msg()])
    probes_at_arm = None

    rc = _watch(api, tmp_path, monkeypatch, clock, deadline_s=36_000)
    capsys.readouterr()

    assert rc == 0, f"B4: mail is a benign exit -- got {rc}"
    # arm-time probe is 1; the single empty block before mail may add at most 1 more. The pin
    # that matters: the probe is not run per-message, so it cannot tax the delivery path.
    assert api.online_probes <= 2, (
        "B4: the liveness probe must run only at arm and on EMPTY returns -- "
        f"it ran {api.online_probes} times, which means it is on the mail path")
