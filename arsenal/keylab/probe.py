"""arsenal.keylab.probe -- the guided W0 hardware session: the LCD asks, the pads answer, the receipts write themselves.

A16 W0 owes hardware receipts that only Daniel's eyes can give (fences/a16-charter/reconciliation.md V7). This
turns them into one sitting at the keyboard with nothing to type: every step shows its instruction on the LCD,
and he answers on the pads -- pad 1 (top left, green) = yes, pad 2 (beside it, red) = no, pad 4 (top right,
white) = skip (protocol.GRID; Daniel corrected the layout at the device, 2026-10-23). Calibration learns what those three pads actually send, so the answers work whatever note map
the pads carry. Everything heard and shown is written, with timestamps, to
state/arsenal/keylab/receipts/probe-<stamp>.json, so a photo sent to Discord can be matched to the frame on the pads.

Steps (each can be run alone with --only):
  calibrate  learn the yes / no / skip pads (and that DAW mode is on)
  p5         LED request byte 0x04 (Bitwig's) against our confirmed 0x00
  colour     the warm-to-white fix: root vs third in roles and quality (W0 d, with a photo)
  gamut      P4: six colour frames to photograph (hue wheel, warm ramp, saturation, levels, the palette)
  census     P2: every fader, knob, the dial, transport, screen and free buttons, logged per input port
  p17        do pad notes change with the pad selector position?
  screens    P15: the knob and fader screens (28, 29)
  lcdspeed   P14: LCD updates at 80 / 60 / 40 / 20 ms spacing
  webmidi    P25: does the piano page still hear the keys while we hold the input?
  burst      P24 + the kill drill: the sustained safe rate, a freeze, a power cycle, resync()
  fl         P1: FL Studio and our tools on the same DAW port
Freeze risk lives only in `burst`, which asks first.
"""
from __future__ import annotations

import json
import os
import time
from typing import Callable, Dict, List, Optional, Tuple

from . import protocol as P

YES, NO, SKIP = "yes", "no", "skip"
ANSWER_PADS = {1: YES, 2: NO, 4: SKIP}
ANSWER_COLOURS = {1: (0, 255, 0), 2: (255, 0, 0), 4: (255, 255, 255)}
OFF = (0, 0, 0)
STEPS = ["calibrate", "p5", "colour", "gamut", "census", "p17", "screens", "lcdspeed", "webmidi", "burst", "fl"]
RAMP_RATES = [120, 160, 200, 260, 330]     # packets per second, the P24 ladder


def default_receipt_path(now: Optional[float] = None) -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                        "state", "arsenal", "keylab", "receipts")
    return os.path.join(root, f"probe-{stamp}.json")


class Rig:
    """The device side of a session: one governed DAW output, the inputs, the current pad frame. Ports come from an
    injected `open_ports()` so tests run on fakes and the burst step can reopen them after a power cycle."""

    def __init__(self, open_ports: Callable[[], Tuple[object, Dict[str, object]]],
                 clock: Callable[[], float] = time.perf_counter, sleep: Callable[[float], None] = time.sleep):
        self._open_ports, self.clock, self.sleep = open_ports, clock, sleep
        self.out, self.inputs = open_ports()
        self.frame_now: List[Tuple[int, int, int]] = [OFF] * 12
        self._sent: List[Optional[Tuple[int, int, int]]] = [None] * 12
        self.answer_notes: Dict[Tuple[int, int], str] = {}   # (status & 0xF0 | channel, note) -> yes/no/skip

    # --- output ---
    def lcd(self, line1, line2="", c1=(0, 200, 160), c2=(255, 255, 255)) -> None:
        self.out.send_sysex(P.screen_full2(line1, line2, color1=c1, color2=c2))

    def pads(self, colours) -> int:
        """Show a 12-pad frame, sending only pads that changed (the governor on the output paces it)."""
        n = 0
        for i, c in enumerate(list(colours)[:12]):
            rgb = P.parse_color(c)
            self.frame_now[i] = rgb
            if self._sent[i] != rgb:
                self.out.send_sysex(P.set_led(P.pad_led(i + 1, "DAW"), rgb, req=P.REQ_CTRL))
                self._sent[i] = rgb
                n += 1
        return n

    def resync(self) -> None:
        self._sent = [None] * 12

    # --- input ---
    def drain(self) -> List[dict]:
        evs = []
        for port, inp in self.inputs.items():
            ev_list = getattr(inp, "events", [])
            while ev_list:
                t, data, kind = ev_list.pop(0)
                evs.append({"port": port, "t_dev": round(t, 4), "t": round(self.clock(), 4), "kind": kind,
                            "data": list(bytes(data))})
        return evs

    def listen(self, secs: float, until: Optional[Callable[[dict], bool]] = None) -> List[dict]:
        end, got = self.clock() + secs, []
        while self.clock() < end:
            for ev in self.drain():
                got.append(ev)
                if until and until(ev):
                    return got
            self.sleep(0.01)
        return got

    @staticmethod
    def note_on(ev: dict) -> Optional[Tuple[int, int]]:
        d = ev["data"]
        if ev["kind"] == "short" and len(d) >= 3 and d[0] & 0xF0 == 0x90 and d[2] > 0:
            return d[0], d[1]
        return None

    def ask(self, line1: str, timeout: float = 90.0, line2: str = "1 yes   2 no   4 skip") -> Optional[str]:
        """Show a question, light the answer pads over the current frame, wait for a calibrated answer pad."""
        shown = list(self.frame_now)
        for pad, rgb in ANSWER_COLOURS.items():
            shown[pad - 1] = rgb
        self.pads(shown)
        self.lcd(line1, line2, c1=(255, 255, 255), c2=(0, 200, 160))
        self.drain()                                    # stale presses do not count
        found: List[str] = []

        def is_answer(ev):
            key = self.note_on(ev)
            if key and key in self.answer_notes:
                found.append(self.answer_notes[key])
                return True
            return False

        self.listen(timeout, until=is_answer)
        return found[0] if found else None

    def reopen(self, timeout: float = 180.0) -> bool:
        """After a power cycle the old handles are dead: close them and retry opening until the device is back."""
        for h in [self.out, *self.inputs.values()]:
            try:
                h.close()
            except Exception:
                pass
        end = self.clock() + timeout
        while self.clock() < end:
            try:
                self.out, self.inputs = self._open_ports()
                self.resync()
                return True
            except Exception:
                self.sleep(2.0)
        return False

    def close(self) -> None:
        for h in [self.out, *self.inputs.values()]:
            try:
                h.close()
            except Exception:
                pass


class Session:
    def __init__(self, rig: Rig, receipt_path: str, log: Callable[[str], None] = print):
        self.rig, self.path, self.log = rig, receipt_path, log
        self.record = {"started": time.strftime("%Y-%m-%d %H:%M:%S"), "steps": []}

    def note(self, step: str, **data) -> dict:
        entry = {"step": step, "at": time.strftime("%Y-%m-%d %H:%M:%S"), **data}
        self.record["steps"].append(entry)
        self.save()
        self.log(f"[probe] {step}: " + json.dumps({k: v for k, v in data.items() if k != "events"})[:300])
        return entry

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.record, f, indent=1)
        os.replace(tmp, self.path)

    # --- steps ---------------------------------------------------------------------------------------------
    def calibrate(self) -> bool:
        r = self.rig
        r.out.send_sysex(P.daw_connect(True))
        r.sleep(0.2)
        r.resync()
        r.pads([OFF] * 12)
        learned = {}
        for pad, answer in ANSWER_PADS.items():
            frame = [OFF] * 12
            frame[pad - 1] = ANSWER_COLOURS[pad]
            r.pads(frame)
            r.lcd(f"PROBE: hit pad {pad}", f"the lit one = {answer}", c1=(0, 200, 160))
            r.drain()
            hit: List[Tuple[int, int]] = []
            r.listen(120.0, until=lambda ev: bool(r.note_on(ev)) and not hit.append(r.note_on(ev)))
            if not hit:
                self.note("calibrate", ok=False, missing=pad)
                return False
            learned[hit[0]] = answer
        r.answer_notes = learned
        r.pads([OFF] * 12)
        self.note("calibrate", ok=True, answer_notes={f"{s}:{n}": a for (s, n), a in learned.items()})
        return True

    def p5(self) -> None:
        r = self.rig
        frame = [OFF] * 12
        r.pads(frame)
        r.out.send_sysex(P.set_led(P.pad_led(5, "DAW"), (255, 0, 0), req=0x00))
        r.out.send_sysex(P.set_led(P.pad_led(6, "DAW"), (255, 0, 0), req=0x04))
        r._sent[4] = r._sent[5] = None                  # bypassed the renderer: forget what we think is lit
        r.frame_now[4] = r.frame_now[5] = (255, 0, 0)
        a = r.ask("P5: are pads 5 AND 6 both red?")
        self.note("p5", answer=a, pad5_req=0x00, pad6_req=0x04,
                  meaning="0x04 also works" if a == YES else "only 0x00 renders" if a == NO else "unknown")

    def colour(self) -> None:
        from . import chordview as CV
        from .theory import analyze
        r = self.rig
        for label, notes, scheme in (("Cmaj roles", [60, 64, 67], "roles"), ("Cmin roles", [60, 63, 67], "roles"),
                                     ("Cmaj mood", [60, 64, 67], "quality")):
            name, root, qual = analyze(notes)
            frame = CV.pad_colors(set(notes), root, qual, scheme, (0, 200, 160))
            r.pads(frame)
            r.lcd(f"{label}: photo now", "root=white, 3rd=red/magenta")
            r.sleep(4.0)
            a = r.ask(f"{label}: root vs 3rd clear?")
            self.note("colour", case=label, frame=frame, answer=a)

    def gamut(self) -> None:
        r = self.rig

        def hsv(h, s=1.0, v=1.0):
            import colorsys
            return tuple(int(round(c * 255)) for c in colorsys.hsv_to_rgb(h, s, v))

        frames = [
            ("hue wheel", [hsv(i / 12) for i in range(12)]),
            ("warm ramp 15-70 deg", [hsv((15 + i * 5) / 360) for i in range(12)]),
            ("orange saturation 100-10%", [hsv(30 / 360, 1 - i * 0.08) for i in range(12)]),
            ("red levels", [(int(255 * (1 - i / 12)), 0, 0) for i in range(12)]),
            ("white levels", [tuple([int(255 * (1 - i / 12))] * 3) for i in range(12)]),
        ]
        from . import chordview as CV
        palette = [CV.ROLE_COLORS[k] for k in (0, 3, 4, 7, 10, 11, 2, 1, 5, 6, 8, 9)]
        frames.append(("chord palette", palette))
        for i, (label, frame) in enumerate(frames, 1):
            r.pads(frame)
            r.lcd(label, f"gamut {i}/{len(frames)}: photo, then pad 1")
            r.drain()
            r.listen(120.0, until=lambda ev: r.answer_notes.get(r.note_on(ev) or (0, 0)) == YES)
            self.note("gamut", frame_no=i, label=label, frame=frame)

    def census(self) -> None:
        r = self.rig
        groups = [
            ("faders", "Faders 1-9, one by one", 14),
            ("fader_touch", "TOUCH fader 1, do not move it", 6),
            ("knobs", "Knobs 1-9, a little each", 14),
            ("dial_slow", "Dial: 5 clicks right, SLOWLY", 9),
            ("dial_fast", "Dial: spin right FAST", 5),
            ("dial_left", "Dial: 5 clicks left, slowly", 9),
            ("dial_click", "Click the dial 3 times", 6),
            ("transport", "Each transport button once", 14),
            ("edit_buttons", "Back Save Quantize Undo Redo", 10),
            ("screen_buttons", "Screen buttons 1-8, in order", 14),
            ("free_buttons", "Bank-/+ Settings MIDI Transp-/+", 14),
            ("long_press", "HOLD screen button 8 for 2s", 7),
            ("shift", "Press Shift if you have one", 6),
        ]
        r.pads([OFF] * 12)
        for n, (key, text, secs) in enumerate(groups, 1):
            r.lcd(text, f"census {n}/{len(groups)}: {secs} s, go")
            r.drain()
            evs = r.listen(float(secs))
            self.note("census", group=key, instruction=text, summary=summarize(evs), events=evs)
        r.lcd("Census done", "octave/transpose back to 0")
        r.sleep(3.0)

    def p17(self) -> None:
        r = self.rig
        r.pads([OFF] * 12)
        r.lcd("Pad switch LEFT>pad1 RIGHT>pad1", "then MIDDLE>pad1 (30 s)")
        r.drain()
        evs = r.listen(30.0)
        hits = [r.note_on(e) for e in evs if r.note_on(e)]
        self.note("p17", order="left, right, middle", note_ons=[list(h) for h in hits], events=evs)
        a = r.ask("Back in the MIDDLE (DAW)?")
        self.note("p17_back_in_daw", answer=a)

    def screens(self) -> None:
        r = self.rig
        for sid, label in ((P.Screen.KNOB, "knob"), (P.Screen.FADER, "fader")):
            r.out.send_sysex(P.screen_param(sid, "Intensity", "64%", 81, (0, 200, 160)))
            r.sleep(2.5)
            a = r.ask(f"Saw a {label} + bar + Intensity?")
            self.note("screens", screen=sid, kind=label, answer=a)

    def lcdspeed(self) -> None:
        r = self.rig
        for spacing in (0.080, 0.060, 0.040, 0.020):
            for n in range(1, 31):
                r.lcd(f"LCD speed {int(spacing * 1000)} ms", f"count {n}/30")
                r.sleep(spacing)
            r.sleep(0.5)
            a = r.ask(f"{int(spacing * 1000)}ms: smooth all the way to 30?")
            self.note("lcdspeed", spacing_ms=int(spacing * 1000), answer=a)

    def webmidi(self) -> None:
        r = self.rig
        r.lcd("Open the piano page,", "play some keys (25 s)")
        r.drain()
        evs = r.listen(25.0)
        keys = [e for e in evs if e["port"] == "midi" and r.note_on(e) and (e["data"][0] & 0x0F) == 0]
        a = r.ask("Did the piano page show them?")
        self.note("webmidi", our_side_heard=len(keys), page_heard=a,
                  meaning="shared" if a == YES and keys else "page blocked while we hold it" if a == NO else "unclear")

    def burst(self) -> None:
        r = self.rig
        if r.ask("Burst test may FREEZE it. Go?", timeout=120) != YES:
            self.note("burst", skipped=True)
            return
        froze_at = None
        for rate in RAMP_RATES:
            r.lcd(f"Sustained rate {rate}/s", "watch pads 5-12")
            sent = self._stream(rate, secs=3.0)
            a = r.ask(f"{rate}/s: all still updating?", timeout=25)
            self.note("burst", rate=rate, packets=sent, answer=a)
            if a != YES:
                froze_at = rate
                break
        if froze_at is None and r.ask("No freeze. Kill drill (40)?", timeout=60) == YES:
            gov, r.out.governor = getattr(r.out, "governor", None), None
            try:
                for i in range(40):
                    r.out.send_sysex(P.set_led(P.pad_led(5 + i % 8, "DAW"), P.hue(i, 8), req=P.REQ_CTRL))
            finally:
                r.out.governor = gov
            froze_at = "kill-40"
            self.note("burst", kill_drill_sent=40, answer=r.ask("Frozen now? (no answer = yes)", timeout=20))
        if froze_at is None:
            self.note("burst", summary="no freeze up to %d/s" % RAMP_RATES[-1])
            return
        self.log("[probe] POWER-CYCLE THE KEYLAB now; then set DAW mode (Prog + 6th screen button) and hit pad 1")
        try:
            r.lcd("Power-cycle me now", "(the screen may go dark)")
        except Exception:
            pass
        t0 = r.clock()
        back = r.reopen()
        restored = None
        if back:
            # The keyboard boots OUT of DAW mode, so nothing painted now would show. Wait for pad 1, which he hits
            # once DAW mode is back on, then repaint from scratch: this is the resync() half of the kill drill.
            r.out.send_sysex(P.daw_connect(True))
            r.lcd("Set DAW mode (Prog + 6th)", "then hit pad 1")
            r.drain()
            r.listen(300.0, until=lambda ev: r.answer_notes.get(r.note_on(ev) or (0, 0)) == YES)
            r.out.send_sysex(P.daw_connect(True))
            r.sleep(0.3)
            r.resync()
            r.pads([P.hue(i, 12) for i in range(12)])
            restored = r.ask("Rainbow back on the pads?", timeout=180)
        self.note("burst", froze_at=froze_at, reopened=back, restored=restored, recovery_s=round(r.clock() - t0, 1))

    def _stream(self, rate: int, secs: float) -> int:
        """Send pad colours on pads 5-12 at `rate` packets/s with the governor OFF (this is the probe of it)."""
        r = self.rig
        gov, r.out.governor = getattr(r.out, "governor", None), None
        n, period, t_end = 0, 1.0 / rate, r.clock() + secs
        try:
            nxt = r.clock()
            while r.clock() < t_end:
                pad = 5 + n % 8
                r.out.send_sysex(P.set_led(P.pad_led(pad, "DAW"), P.hue(n, 8), req=P.REQ_CTRL))
                n += 1
                nxt += period
                wait = nxt - r.clock()
                if wait > 0:
                    r.sleep(wait)
        finally:
            r.out.governor = gov
            r.resync()
        return n

    def fl(self) -> None:
        r = self.rig
        if r.ask("FL test: open FL, then pad 1", timeout=600) != YES:
            self.note("fl", skipped=True)
            return
        complained = r.ask("Did FL complain about a port?")
        frame = [OFF] * 12
        frame[4] = (0, 255, 0)
        r.pads(frame)
        r.sleep(3.0)
        stayed = r.ask("Is pad 5 still green?")
        self.note("fl", fl_port_error=complained, our_pad_survived=stayed)

    # --- run ---------------------------------------------------------------------------------------------
    def run(self, only: Optional[List[str]] = None) -> str:
        steps = only or STEPS
        if "calibrate" not in steps:
            steps = ["calibrate"] + list(steps)
        try:
            for name in steps:
                if name == "calibrate":
                    if not self.calibrate():
                        self.log("[probe] calibration got no pad hits: is the keyboard in DAW mode?")
                        break
                    continue
                try:
                    getattr(self, name)()
                except Exception as exc:                 # one broken step must not lose the others' receipts
                    self.note(name, error=f"{type(exc).__name__}: {exc}")
            try:
                self.rig.lcd("PROBE done. Thank you!", "receipts saved")
                self.rig.pads([OFF] * 12)
                self.rig.out.send_sysex(P.daw_connect(False))
            except Exception:
                pass
        finally:
            self.record["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.save()
            self.rig.close()
        return self.path


def summarize(evs: List[dict]) -> List[dict]:
    """Group a census window by (port, status, data1): which controls spoke, on which port, with what values."""
    groups: Dict[Tuple[str, int, int], dict] = {}
    for e in evs:
        d = e["data"]
        if e["kind"] != "short" or len(d) < 3:
            continue
        key = (e["port"], d[0], d[1])
        g = groups.setdefault(key, {"port": e["port"], "status": d[0], "d1": d[1], "count": 0, "values": set(),
                                    "first_t": e["t"], "last_t": e["t"]})
        g["count"] += 1
        g["values"].add(d[2])
        g["last_t"] = e["t"]
    out = []
    for g in sorted(groups.values(), key=lambda g: (g["port"], g["first_t"])):
        vals = sorted(g.pop("values"))
        out.append({**g, "values": vals if len(vals) <= 12 else vals[:6] + ["..."] + vals[-6:]})
    return out


def open_real_ports():
    """The real device: a governed DAW output, the MIDI input, and the DAW input only if Windows lists one."""
    from . import winmidi as W
    out = W.MidiOut(prefer="daw")
    inputs = {"midi": W.MidiIn(prefer="midi")}
    if any("daw" in n.lower() for n in W.inputs()):
        inputs["daw"] = W.MidiIn(prefer="daw")
    for inp in inputs.values():
        inp.start()
    return out, inputs
