"""Pins for arsenal.keylab.probe, the guided W0 hardware session. No keyboard: fake ports, a fake clock, and a
scripted 'Daniel' who answers on the pads whenever the LCD asks something."""
from __future__ import annotations

import json

from arsenal.keylab import probe as PR
from arsenal.keylab.governor import BurstGovernor

PAD_NOTE = {1: 44, 2: 45, 4: 47}          # what the pads happen to send in this test (calibration must learn it)
PAD_STATUS = 0x99                         # note on, channel 10


class Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += max(s, 0.001)


class FakeOut:
    def __init__(self, clock):
        self.sysex, self.closed = [], False
        self.governor = BurstGovernor(clock=clock.now, sleep=clock.sleep)

    def send_sysex(self, data):
        if self.governor is not None:
            self.governor.admit()
        self.sysex.append(bytes(data))

    def close(self):
        self.closed = True


class FakeIn:
    """Releases scripted presses once the fake clock passes their time."""

    def __init__(self, clock):
        self.clock, self._pending, self._ready = clock, [], []

    def press(self, at, status, note, vel=100):
        self._pending.append((at, bytes([status, note, vel])))

    @property
    def events(self):
        due = [p for p in self._pending if p[0] <= self.clock.t]
        for p in due:
            self._pending.remove(p)
            self._ready.append((p[0], p[1], "short"))
        return self._ready

    def close(self):
        pass


class ScriptedRig(PR.Rig):
    """A Rig whose 'human' answers the next scripted pad 0.5 s after any prompt that waits for a pad."""

    def __init__(self, answers, clock, opens=None):
        self.clock_obj, self.answers, self.lcd_log, self.opens = clock, list(answers), [], opens or []
        self.inp = None

        def open_ports():
            self.opens.append(clock.t)
            out = FakeOut(clock)
            self.inp = FakeIn(clock)
            return out, {"midi": self.inp}

        super().__init__(open_ports, clock=clock.now, sleep=clock.sleep)

    def lcd(self, line1, line2="", c1=(0, 200, 160), c2=(255, 255, 255)):
        super().lcd(line1, line2, c1, c2)
        self.lcd_log.append((line1, line2))
        waits = "1 yes" in line2 or "hit pad" in line1 or "hit pad 1" in line2
        if waits and self.answers:
            pad = self.answers.pop(0)
            if pad is not None:
                self.inp.press(self.clock_obj.t + 0.5, PAD_STATUS, PAD_NOTE[pad])


def _session(tmp_path, answers, **kw):
    clock = Clock()
    rig = ScriptedRig(answers, clock, **kw)
    return PR.Session(rig, str(tmp_path / "probe.json"), log=lambda s: None), rig, clock


def test_calibration_learns_whatever_the_pads_send(tmp_path):
    s, rig, _ = _session(tmp_path, [1, 2, 4])
    assert s.calibrate()
    assert rig.answer_notes == {(PAD_STATUS, 44): "yes", (PAD_STATUS, 45): "no", (PAD_STATUS, 47): "skip"}


def test_calibration_without_hits_stops_cleanly(tmp_path):
    s, rig, _ = _session(tmp_path, [None])
    assert s.calibrate() is False
    assert s.record["steps"][-1] == {**s.record["steps"][-1], "ok": False, "missing": 1}


def test_ask_ignores_presses_made_before_the_question(tmp_path):
    s, rig, clock = _session(tmp_path, [1, 2, 4, 2])
    s.calibrate()
    rig.inp.press(clock.t, PAD_STATUS, 44)          # a stray YES already queued before the question
    assert rig.ask("Is this a test?") == "no"         # the scripted answer after the prompt wins


def test_ask_times_out_to_none(tmp_path):
    s, rig, _ = _session(tmp_path, [1, 2, 4, None])
    s.calibrate()
    assert rig.ask("Anyone there?", timeout=5) is None


def test_run_writes_receipts_with_every_answer(tmp_path):
    s, rig, _ = _session(tmp_path, [1, 2, 4, 1, 2, 1])
    path = s.run(["p5", "screens"])
    rec = json.load(open(path, encoding="utf-8"))
    steps = [(x["step"], x.get("answer")) for x in rec["steps"]]
    assert steps == [("calibrate", None), ("p5", "yes"), ("screens", "no"), ("screens", "yes")]
    assert rec["finished"]
    assert rig.out.closed, "the session must hand the ports back"


def test_a_broken_step_is_recorded_and_the_rest_still_run(tmp_path):
    s, rig, _ = _session(tmp_path, [1, 2, 4, 1])

    def boom():
        raise RuntimeError("device went away")

    s.colour = boom
    s.run(["colour", "p5"])
    names = [x["step"] for x in s.record["steps"]]
    assert names == ["calibrate", "colour", "p5"]
    assert "device went away" in s.record["steps"][1]["error"]


def test_census_summary_groups_by_port_and_control():
    evs = [{"port": "daw", "t": 1.0, "kind": "short", "data": [0xB0, 105, v]} for v in (0, 40, 127)]
    evs += [{"port": "midi", "t": 2.0, "kind": "short", "data": [0xB0, 116, 65]}]
    out = PR.summarize(evs)
    assert out[0]["port"] == "daw" and out[0]["d1"] == 105 and out[0]["count"] == 3 and out[0]["values"] == [0, 40, 127]
    assert out[1]["port"] == "midi" and out[1]["d1"] == 116


def test_burst_finds_the_freeze_reopens_the_ports_and_restores_the_governor(tmp_path):
    # calibrate, go, 120 ok, 160 ok, 200 NOT ok, then (after the reopen) 'DAW mode back' and 'rainbow back'
    s, rig, clock = _session(tmp_path, [1, 2, 4, 1, 1, 1, 2, 1, 1])
    s.calibrate()
    gov_before = rig.out.governor
    s.burst()
    burst = [x for x in s.record["steps"] if x["step"] == "burst"]
    rates = [x.get("rate") for x in burst if "rate" in x]
    assert rates == [120, 160, 200]
    assert 330 <= burst[0]["packets"] <= 400, "120/s for 3 s"
    final = burst[-1]
    assert final["froze_at"] == 200 and final["reopened"] is True and final["restored"] == "yes"
    assert len(rig.opens) == 2, "the ports are reopened once after the power cycle"
    assert gov_before is not None and rig.out.governor is not None, "the governor is back after the probe"


def test_the_same_governor_is_back_after_every_ramp_level(tmp_path):
    # No freeze anywhere and no kill drill, so the ports are never reopened: the governor seen afterwards must be
    # the very object from before, put back by the probe itself (a reopen would hide a missing restore).
    s, rig, _ = _session(tmp_path, [1, 2, 4, 1] + [1] * len(PR.RAMP_RATES) + [2])
    s.calibrate()
    gov_before = rig.out.governor
    s.burst()
    assert len(rig.opens) == 1, "nothing froze, so nothing was reopened"
    assert rig.out.governor is gov_before


def test_burst_is_skipped_unless_he_says_go(tmp_path):
    s, rig, _ = _session(tmp_path, [1, 2, 4, 2])
    s.calibrate()
    s.burst()
    assert s.record["steps"][-1] == {**s.record["steps"][-1], "step": "burst", "skipped": True}


def test_every_lcd_line_fits_the_screen(tmp_path):
    s, rig, _ = _session(tmp_path, [1, 2, 4] + [1] * 80)
    s.run([x for x in PR.STEPS if x != "calibrate"])          # the WHOLE session, burst and FL included
    assert len(rig.lcd_log) > 40
    too_long = [l for pair in rig.lcd_log for l in pair if len(l) > 32]
    assert not too_long, too_long
