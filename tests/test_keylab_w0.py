"""A16 W0 pins for arsenal/keylab: sustain (CC 64), the pad grid, the burst ceiling, and the colour wash zone.

Acceptance pre-registered in fences/a16-charter/reconciliation.md V7(b) and (d). Everything here runs
without the keyboard: the MIDI sink is a fake, and the governor runs on a fake clock, so nothing can flake.
"""
from __future__ import annotations

import colorsys
import threading

import pytest

from arsenal.keylab import chordview as CV
from arsenal.keylab import protocol as P
from arsenal.keylab import winmidi as W
from arsenal.keylab.governor import SAFE_BURST, BurstGovernor, max_in_window
from arsenal.keylab.ledframe import PadRenderer

NOTE_ON, NOTE_OFF, CC = 0x90, 0x80, 0xB0


# --- sustain pedal (CC 64) -----------------------------------------------------------------------

def _play(events):
    v = CV.Voicing()
    for e in events:
        v.feed(*e)
    return v


def test_release_without_pedal_silences_the_note():
    assert _play([(NOTE_ON, 60, 100), (NOTE_OFF, 60, 0)]).sounding == set()


def test_pedal_holds_a_released_note_and_pedal_up_releases_it():
    v = _play([(CC, 64, 127), (NOTE_ON, 60, 100), (NOTE_OFF, 60, 0)])
    assert v.sounding == {60}, "the pedal must hold a note past key release"
    v.feed(CC, 64, 0)
    assert v.sounding == set(), "pedal up must release the sustained notes"


def test_note_on_velocity_zero_is_a_release_under_the_pedal():
    v = _play([(CC, 64, 127), (NOTE_ON, 64, 90), (NOTE_ON, 64, 0)])
    assert v.sounding == {64}


def test_restrike_under_the_pedal_moves_the_note_back_to_held():
    v = _play([(CC, 64, 127), (NOTE_ON, 60, 100), (NOTE_OFF, 60, 0), (NOTE_ON, 60, 100)])
    assert (v.down, v.sustained) == ({60}, set())


def test_pedal_on_any_channel_counts():
    v = _play([(CC | 0x03, 64, 127), (NOTE_ON | 0x03, 67, 80), (NOTE_OFF | 0x03, 67, 0)])
    assert v.sounding == {67}


# --- the pad grid ------------------------------------------------------------------------------

def test_grid_matches_the_unit():
    """Daniel at the device, 2026-10-23: "your pad representation shows pad 1 on the right when its actually the top
    left most pad, and itr goes to 4, then row 2 is 5-8 and bottom row is 9-12". 4 across x 3 down, reading order,
    rows top (farthest from the player) to bottom. The 2026-10-22 grid [[9, 5, 1], ...] was this one turned 90 degrees
    (erratum: research/reviewed/keylab-liberation-2026-10-22/erratum-pad-grid-2026-10-23.md)."""
    assert P.GRID == [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]
    assert (len(P.GRID), {len(r) for r in P.GRID}) == (3, {4}), "4 across x 3 down"


def test_grid_has_one_copy_and_every_pad_once():
    assert CV.GRID is P.GRID, "chordview must import the grid, not keep its own"
    flat = [p for row in P.GRID for p in row]
    assert sorted(flat) == list(range(1, 13))


def test_grid_derived_regions():
    assert CV.TOP_ROW == {1, 2, 3, 4}, "split paints the TOP row, pads 1-4 (it was lighting the left column 9 5 1)"
    assert CV.BORDER == set(range(1, 13)) - {6, 7}


def test_grid_agrees_with_the_mpc_note_rows():
    """Two independent facts, one layout: PAD_NOTE (bank A, MPC layout, from Default.keylab388) and GRID (Daniel's eyes).
    On an MPC layout the notes climb left to right along a row and up the rows, so the grid must read that way too."""
    notes = [[P.PAD_NOTE[pad] for pad in row] for row in P.GRID]
    for row in notes:
        assert row == list(range(row[0], row[0] + len(row))), f"a row's notes ascend by a semitone left to right: {row}"
    for upper, lower in zip(notes, notes[1:]):
        assert upper[0] - lower[0] == 4, f"each row sits 4 semitones above the row below it: {upper} over {lower}"
    assert P.GRID[-1][0] == 9 and P.PAD_NOTE[P.GRID[-1][0]] == 36 == min(P.PAD_NOTE.values()), \
        "the bottom-left pad (9) plays the lowest note, 36"


def test_the_page_mirror_equals_protocol_grid():
    """keylab-client.js keeps a copy of the grid for the browser (PAD_GRID). Read the JS text itself, so the mirror can
    never drift from protocol.GRID again: the desk's pad panel draws exactly these rows."""
    import json
    import pathlib
    import re
    js = (pathlib.Path(__file__).resolve().parents[1] / "arsenal" / "web" / "lib" / "keylab-client.js").read_text(encoding="utf-8")
    found = re.findall(r"export const PAD_GRID = Object\.freeze\((\[.*?\])\);", js)
    assert len(found) == 1, "exactly one PAD_GRID declaration in keylab-client.js"
    assert json.loads(found[0]) == P.GRID


def test_daw_bank_led_ids():
    assert [P.pad_led(n, "DAW") for n in range(1, 13)] == list(range(82, 94))


# --- the burst ceiling -------------------------------------------------------------------------

class FakeClock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += max(s, 1e-6)


def _governor(clock):
    g = BurstGovernor(clock=clock.now, sleep=clock.sleep)
    g.record = True
    return g


def test_interleaved_producers_never_exceed_the_ceiling():
    clock = FakeClock()
    g = _governor(clock)
    for i in range(3 * 40):                     # three producers, round-robin, 40 packets each, no pacing
        g.admit()
        clock.t += 0.0003 * (i % 3)             # producers jitter a little between sends
    assert g.admitted == 120
    assert max_in_window(g.log, g.window) <= SAFE_BURST
    assert g.waited_s > 0, "an unpaced 120-packet flood must have been held back"


def test_threads_sharing_one_governor_never_exceed_the_ceiling():
    g = BurstGovernor(limit=SAFE_BURST, window=0.02)
    g.record = True

    def producer():
        for _ in range(30):
            g.admit()

    threads = [threading.Thread(target=producer) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert g.admitted == 90
    assert max_in_window(g.log, g.window) <= SAFE_BURST


class GovernedSink:
    """A fake WinMM output that passes every SysEx through a governor, as MidiOut does."""

    def __init__(self, governor):
        self.governor, self.packets = governor, []

    def send_sysex(self, data):
        self.packets.append((self.governor.admit(), bytes(data)))


def test_two_renderers_on_one_port_stay_under_the_ceiling():
    clock = FakeClock()
    sink = GovernedSink(_governor(clock))
    chords, beat = PadRenderer(sink, gap=0.0), PadRenderer(sink, gap=0.0)
    for i in range(6):                          # a chord view and a beat march repaint every pad, alternately
        chords.set_frame([(i * 20 % 128, 0, 127)] * 12)
        beat.set_frame([(0, i * 20 % 128, 127)] * 12)
    times = [t for t, _ in sink.packets]
    assert len(times) == 144
    assert max_in_window(times, sink.governor.window) <= SAFE_BURST


def test_midiout_admits_before_touching_the_driver():
    class Refuse(Exception):
        pass

    class Gate:
        def admit(self):
            raise Refuse

    out = object.__new__(W.MidiOut)             # no device: the gate must fire before any WinMM call
    out.governor = Gate()
    with pytest.raises(Refuse):
        out.send_sysex(P.set_led(P.pad_led(1, "DAW"), (127, 0, 0)))


def test_max_in_window_counts_half_open_windows():
    assert max_in_window([0.0, 0.05, 0.0999, 0.1, 0.2], 0.1) == 3
    assert max_in_window([], 0.1) == 0


# --- colours stay out of the wash zone -----------------------------------------------------------

WASH_ZONE = (15.0, 100.0)   # hue degrees: orange through lime, which this device renders close to white


def _hue(rgb):
    r, g, b = (c / 255 for c in rgb)
    h, _l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s


@pytest.mark.parametrize("table", ["ROLE_COLORS", "QUALITY_COLORS"])
def test_no_chord_colour_in_the_wash_zone(table):
    for key, rgb in getattr(CV, table).items():
        if rgb == (255, 255, 255):
            continue
        h, s = _hue(rgb)
        assert s > 0.5, f"{table}[{key!r}] {rgb} is too unsaturated to read on the pads"
        assert not (WASH_ZONE[0] <= h <= WASH_ZONE[1]), f"{table}[{key!r}] {rgb} (hue {h:.0f}) washes to white"


def test_root_and_both_thirds_are_three_different_colours():
    root, minor3, major3 = CV.ROLE_COLORS[0], CV.ROLE_COLORS[3], CV.ROLE_COLORS[4]
    assert root == (255, 255, 255)
    assert len({root, minor3, major3}) == 3
    h3, _ = _hue(minor3)
    h4, _ = _hue(major3)
    assert min(abs(h3 - h4), 360 - abs(h3 - h4)) >= 30, "the two thirds must differ in hue, not just shade"
