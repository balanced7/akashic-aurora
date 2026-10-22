"""arsenal.keylab.ledframe -- a stateful pad renderer that sends ONLY the pads that changed.

The device chokes on big bursts (~36 packets in one go freezes it; 12 is the measured safe ceiling, and tight
spacing drops packets). The lever that beats the hardware instead of fighting it: the device LATCHES each pad's
colour, so an unchanged pad never needs re-sending. Hold the current 12-pad buffer, diff it against the next
frame, and emit only the delta -- a walking dot is 1-2 packets/frame instead of 12, a pulse that only brightens
is 0 packets when nothing moved. That keeps every frame far under the burst ceiling AND multiplies the effective
frame rate we can sustain, because our real cost per frame is "pads that changed", not "12".

Use it with a winmidi.MidiOut (already in DAW mode). It also enforces a spacing budget so a big first frame
(all 12 pads) still paces itself safely.
"""
from __future__ import annotations

import time
from typing import List, Optional, Tuple

from . import protocol as P


class PadRenderer:
    def __init__(self, out, bank: str = "DAW", gap: float = 0.006, burst: int = 10):
        self.out = out
        self.bank = bank
        self.gap = gap            # spacing between packets
        self.burst = burst        # take an extra breath after this many packets in one frame
        self.state: List[Optional[Tuple[int, int, int]]] = [None] * 12
        self.sent = 0             # lifetime packets actually put on the wire
        self.frames = 0           # frames rendered
        self.asked = 0            # pad-updates requested (sent/asked = compression ratio)

    def set_frame(self, colors) -> int:
        """Paint up to 12 pad colours, sending only the pads whose colour changed. Returns packets sent."""
        target = [P.parse_color(c) for c in list(colors)[:12]]
        self.asked += len(target)
        n = 0
        for i, rgb in enumerate(target):
            if self.state[i] == rgb:
                continue
            self.out.send_sysex(P.set_led(P.pad_led(i + 1, self.bank), rgb, req=P.REQ_CTRL))
            self.state[i] = rgb
            self.sent += 1
            n += 1
            time.sleep(self.gap * (4 if n % self.burst == 0 else 1))
        self.frames += 1
        return n

    def clear(self) -> int:
        return self.set_frame([(0, 0, 0)] * 12)

    def resync(self) -> None:
        """Drop cached state so the next frame repaints every pad (after a bank/mode change or power cycle)."""
        self.state = [None] * 12

    def stats(self) -> dict:
        ratio = (self.sent / self.asked) if self.asked else 0.0
        return {"frames": self.frames, "packets_sent": self.sent, "pad_updates_asked": self.asked,
                "compression": round(1 - ratio, 3), "avg_packets_per_frame": round(self.sent / max(1, self.frames), 2)}


def _selftest() -> list:
    """Offline proof: a counting fake out shows the diff really suppresses unchanged pads."""
    fails = []

    class _Counter:
        def __init__(self): self.n = 0
        def send_sysex(self, data): self.n += 1

    out = _Counter()
    r = PadRenderer(out, gap=0.0)
    r.set_frame(["red"] * 12)            # first frame: all 12 change
    if out.n != 12:
        fails.append(f"first frame sent {out.n}, want 12")
    r.set_frame(["red"] * 12)            # identical frame: nothing should send
    if out.n != 12:
        fails.append(f"identical frame sent {out.n - 12} extra, want 0")
    r.set_frame(["red"] * 11 + ["blue"]) # one pad changes
    if out.n != 13:
        fails.append(f"one-pad change sent {out.n - 12}, want 1")
    return fails


if __name__ == "__main__":
    print("ledframe selftest:", "OK" if not _selftest() else _selftest())
