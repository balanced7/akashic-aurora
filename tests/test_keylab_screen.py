"""Pins for arsenal/keylab/screen.py: the KeyLab mk3 screen encoder, the gate, and the live readout.

Two independent pins for the encoder:
  1. hand-written hex, worked out by reading Arturia's FL script (KL3Display.py / KL3Buttons.py), for several strings
     and layouts, including the calls FL itself makes (SaveRefresh, MetronomeRefresh, the "Connected" card, MixerReturn's
     labels);
  2. when the script is installed on this machine, Arturia's own Display and CTXButton classes are run against stub FL
     modules and every frame is compared byte for byte over a matrix of inputs (skipped elsewhere).
Nothing here touches a keyboard: the sinks are fakes and the clocks are fake, so nothing can flake.
"""
from __future__ import annotations

import importlib
import json
import os
import queue
import socket
import sys
import threading
import time
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from arsenal.keylab import __main__ as CLI
from arsenal.keylab import protocol as P
from arsenal.keylab import screen as S
from arsenal.keylab.governor import BurstGovernor, max_in_window

HEAD = "F0 00 20 6B 7F 42 00 02 04"
ALB = [0, 108, 122]          # the script's ANALOG_LAB_BLUE
WHITE = [127, 127, 127]


def hx(*parts) -> bytes:
    """Hex pieces and plain ASCII strings ('"text"') joined into bytes, for readable pins."""
    out = b""
    for p in parts:
        if p.startswith('"') and p.endswith('"'):
            out += p[1:-1].encode("ascii")
        else:
            out += bytes.fromhex(p.replace(" ", ""))
    return out


# =====================================================================================================================
# 1. hand-written pins
# =====================================================================================================================
def test_two_line_full_screen_aurora_night_shift():
    # Screen_F2L: 00 line1 00 | 01 ct 00 | 02 rgb 00 | 03 LINE2 (upper) 00 | 04 ct 00 | 05 rgb 00
    got = S.f2l("Aurora", 1, ALB, "night shift", 1, WHITE)
    want = hx(HEAD, "0C", "00", '"Aurora"', "00", "01 01 00", "02 00 6C 7A 00",
              "03", '"NIGHT SHIFT"', "00", "04 01 00", "05 7F 7F 7F 00", "F7")
    assert got == want


def test_save_popup_is_screen_23_with_only_its_line():
    # KL3Navigation.SaveRefresh -> Screen_P1L: the colour it is given is never sent
    assert S.p1l("Saving project...") == hx(HEAD, "17", "00", '"Saving project..."', "00", "F7")


def test_metronome_card_icon_popup_27():
    # KL3Navigation.MetronomeRefresh: "Metronome" / "ON", icon ekIconsMetronome_image = 74
    got = S.pli2l("Metronome", 1, ALB, "ON", 1, WHITE, S.Icon.ICON_METRONOME)
    want = hx(HEAD, "1B", "00", '"Metronome"', "00", "01 01 00", "02 00 6C 7A 00",
              "03", '"ON"', "00", "04 01 00", "05 7F 7F 7F 00", "06 4A 00", "F7")
    assert got == want


def test_connected_title_card_31_upper_cases_line_2():
    # device_KL3.OnInit: SetCenterPage(31, ui.getProgTitle(), ..., "Connected", ..., icon=ekIconsFlStudio_image=71)
    got = S.ti2lfix("FL Studio 2024", 1, WHITE, "Connected", 1, WHITE, S.Icon.ICON_FL_STUDIO)
    want = hx(HEAD, "1F", "00", '"FL Studio 2024"', "00", "01 01 00", "02 7F 7F 7F 00",
              "03", '"CONNECTED"', "00", "04 01 00", "05 7F 7F 7F 00", "06 47 00", "F7")
    assert got == want


def test_knob_and_fader_send_the_value_line_first():
    # KL3Navigation.PanChRefresh -> Screen_K(line1='Pan - 3', line2='50%', hw 95, ct 1, ALB)
    body = hx("00", '"50%"', "00", "01", '"Pan - 3"', "00", "02 5F 00", "03 01 00", "04 00 6C 7A 00", "F7")
    assert S.knob("Pan - 3", "50%", 95, 1, ALB) == hx(HEAD, "1C") + body
    assert S.fader("Pan - 3", "50%", 95, 1, ALB) == hx(HEAD, "1D") + body


def test_pad_screen_sends_colour_before_the_bar():
    got = S.pad("Kick", "100", 127, 1, WHITE)
    want = hx(HEAD, "1E", "00", '"100"', "00", "01", '"Kick"', "00", "03 01 00", "04 7F 7F 7F 00", "02 7F 00", "F7")
    assert got == want


def test_icon_screens_leave_the_icon_out_when_none():
    assert S.li1l("Chords") == hx(HEAD, "0F", "00", '"Chords"', "00", "F7")
    assert S.li1l("Chords", 65) == hx(HEAD, "0F", "00", '"Chords"', "00", "01 41 00", "F7")
    assert S.li2l("Chords", "live", 65) == hx(HEAD, "10", "00", '"Chords"', "00", "01", '"LIVE"', "00", "02 41 00", "F7")
    assert S.pli1l("Tap") == hx(HEAD, "1A", "00", '"Tap"', "00", "F7")


def test_three_line_popup_upper_cases_lines_2_and_3():
    got = S.p3l("Scene", 1, WHITE, "laser", 1, ALB, "cathedral", 1, [127, 0, 0])
    want = hx(HEAD, "19", "00", '"Scene"', "00", "01 01 00", "02 7F 7F 7F 00",
              "03", '"LASER"', "00", "04 01 00", "05 00 6C 7A 00",
              "06", '"CATHEDRAL"', "00", "07 01 00", "08 7F 00 00 00", "F7")
    assert got == want


def test_one_line_screens_and_properties():
    assert S.f1l("No Selection", 0, [0, 0, 0]) == hx(HEAD, "0A", "00", '"No Selection"', "00", "01 00 00",
                                                     "02 00 00 00 00", "F7")
    assert S.f1l_inv("3 - Bass", 1, ALB)[len(hx(HEAD))] == 0x0B
    assert S.screen_prop(WHITE) == hx(HEAD, "00", "00 7F 7F 7F 00", "F7")
    assert S.f2l_inv("a", 1, WHITE, "b", 1, WHITE)[9] == 0x0D
    assert S.fb2l("a", 1, WHITE, "b", 1, WHITE)[9] == 0x0E


@pytest.mark.parametrize("text, shown", [
    ("x" * 32, "x" * 32),                       # exactly 32: untouched
    ("y" * 33, "y" * 28 + "..."),               # 33: first 28 + "..." = 31 characters (KL3Display.py:36-37)
    ("A long scene name that runs well past the edge", "A long scene name that runs ..."),
    ("", ""),
    ("Déjà vu", ".Undefined text."),  # any non-ASCII blanks the WHOLE line
])
def test_the_line_rule(text, shown):
    assert S.line_src(text) == shown
    assert S.f1l(text, 1, WHITE) == hx(HEAD, "0A", "00") + shown.encode() + hx("00", "01 01 00", "02 7F 7F 7F 00", "F7")


def test_line_two_of_an_undefined_line_is_upper_cased_too():
    assert S.line_src("café", upper=True) == ".UNDEFINED TEXT."


def test_mixer_labels_from_mixer_return():
    # KL3Return.MixerReturn: SetButton(4, 4, 1, 1, None, WHITE, "PLUGIN", "") -> slot 4 = screen id 5 (button 1)
    got = S.button_label(4, 4, 1, 1, None, WHITE, "PLUGIN", "")
    want = hx(HEAD, "05", "00 04 00", "01 01 00", "02 01 00", "04 7F 7F 7F 00", "05", '"PLUGIN"', "00", "06 00", "F7")
    assert got == want
    # SetButton(0, 11, 1, 1, ekPictosButtonMuteDefault_image=10, [16,16,16], "", "") -> slot 0 = screen id 1 (button 5)
    got = S.button_label(0, 11, 1, 1, S.SmallIcon.MUTE, [16, 16, 16], "", "")
    want = hx(HEAD, "01", "00 0B 00", "01 01 00", "02 01 00", "03 0A 00", "04 10 10 10 00", "05 00", "06 00", "F7")
    assert got == want


def test_label_slots_map_to_the_physical_buttons():
    assert [S.SLOT_FOR_BUTTON[b] + 1 for b in range(1, 9)] == [5, 6, 7, 8, 1, 2, 3, 4]   # eButton1..8 in ScreenId.py


def test_clean_button_is_faithful_to_the_scripts_off_by_one():
    assert S.clean_button(3) == hx(HEAD, "03 00 00 00", "F7")


# =====================================================================================================================
# 2. byte-for-byte against Arturia's own code, when it is installed here
# =====================================================================================================================
FL_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Image-Line", "FL Studio", "Settings", "Hardware",
                      "Arturia KeyLab mk3")
_FL_MODULES = ["KL3Display", "KL3Dispatch", "KL3Buttons", "ScreenId", "IntegrationPatchId", "ParamId",
               "channels", "transport", "mixer", "ui", "device"]


@pytest.fixture
def arturia():
    if not os.path.isfile(os.path.join(FL_DIR, "KL3Display.py")):
        pytest.skip("Arturia's FL script is not installed on this machine")
    saved = {m: sys.modules.get(m) for m in _FL_MODULES}
    sent = []
    for m in ("channels", "transport", "mixer", "ui"):
        sys.modules[m] = types.ModuleType(m)
    device = types.ModuleType("device")
    device.midiOutSysex = lambda data: sent.append(bytes(data))
    sys.modules["device"] = device
    for m in ("KL3Display", "KL3Dispatch", "KL3Buttons", "ScreenId", "IntegrationPatchId", "ParamId"):
        sys.modules.pop(m, None)
    # Arturia's folder is read-only for us: importing from it must never write a __pycache__ there (an earlier run of
    # this fixture did, on 2026-10-23 01:24: cpython-311 .pyc files that FL's own Python 3.12 would never write).
    saved_dont_write = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    sys.path.insert(0, FL_DIR)
    try:
        display_mod = importlib.import_module("KL3Display")
        buttons_mod = importlib.import_module("KL3Buttons")
        yield display_mod.Display(), buttons_mod.CTXButton, sent
    finally:
        sys.path.remove(FL_DIR)
        sys.dont_write_bytecode = saved_dont_write
        for m, mod in saved.items():
            if mod is None:
                sys.modules.pop(m, None)
            else:
                sys.modules[m] = mod


LINES = ["Aurora", "night shift", "", "x" * 32, "y" * 33, "A long scene name that runs well past the edge",
         "Dbmaj7/Ab", "128 BPM | Laser Cathedral", "café", "tab\there", "~!@#$%^&*()_+{}|:<>?"]
COLOURS = [[0, 0, 0], ALB, WHITE, [127, 0, 64]]


def _same(fl, sent, ours, call):
    sent.clear()
    call()
    assert len(sent) == 1
    assert sent[0] == ours, f"\n FL   {sent[0].hex(' ')}\n ours {ours.hex(' ')}"


def test_every_screen_matches_arturias_display_byte_for_byte(arturia):
    d, _, sent = arturia
    n = 0
    for i, a in enumerate(LINES):
        b = LINES[(i + 3) % len(LINES)]
        c = LINES[(i + 5) % len(LINES)]
        c1, c2, c3 = COLOURS[i % 4], COLOURS[(i + 1) % 4], COLOURS[(i + 2) % 4]
        ct = i % 2
        hw = (i * 37) % 128
        icon = None if i % 3 == 0 else (i * 11) % 86
        cases = [
            (lambda: d.Screen_Prop(c1), S.screen_prop(c1)),
            (lambda: d.Screen_F1L(a, ct, c1), S.f1l(a, ct, c1)),
            (lambda: d.Screen_F1LInv(a, ct, c1), S.f1l_inv(a, ct, c1)),
            (lambda: d.Screen_F2L(a, ct, c1, b, 1, c2), S.f2l(a, ct, c1, b, 1, c2)),
            (lambda: d.Screen_F2LInv(a, ct, c1, b, 1, c2), S.f2l_inv(a, ct, c1, b, 1, c2)),
            (lambda: d.Screen_FB2L(a, ct, c1, b, 1, c2), S.fb2l(a, ct, c1, b, 1, c2)),
            (lambda: d.Screen_LI1L(a, None, icon), S.li1l(a, icon)),
            (lambda: d.Screen_LI2L(a, b, None, icon), S.li2l(a, b, icon)),
            (lambda: d.Screen_P1L(a, c1), S.p1l(a)),
            (lambda: d.Screen_P2L(a, ct, c1, b, 1, c2), S.p2l(a, ct, c1, b, 1, c2)),
            (lambda: d.Screen_P3L(a, ct, c1, b, 1, c2, c, 0, c3), S.p3l(a, ct, c1, b, 1, c2, c, 0, c3)),
            (lambda: d.Screen_PLI1L(a, c1, icon), S.pli1l(a, icon)),
            (lambda: d.Screen_PLI2L(a, ct, c1, b, 1, c2, icon), S.pli2l(a, ct, c1, b, 1, c2, icon)),
            (lambda: d.Screen_K(a, b, hw, ct, c1), S.knob(a, b, hw, ct, c1)),
            (lambda: d.Screen_F(a, b, hw, ct, c1), S.fader(a, b, hw, ct, c1)),
            (lambda: d.Screen_P(a, b, hw, ct, c1), S.pad(a, b, hw, ct, c1)),
            (lambda: d.Screen_TI2LFIX(a, ct, c1, b, 1, c2, icon), S.ti2lfix(a, ct, c1, b, 1, c2, icon)),
        ]
        for call, ours in cases:
            _same(d, sent, ours, call)
            n += 1
    assert n == len(LINES) * 17


def test_every_label_matches_arturias_ctxbutton_byte_for_byte(arturia):
    d, CTXButton, sent = arturia
    rows = [  # (ID, type, line_number, color_type, icon, custom_color, line1, line2), from KL3Return.py and beyond
        (4, 4, 1, 1, None, WHITE, "PLUGIN", ""), (5, 6, 1, 1, None, WHITE, "MIXER", ""),
        (6, 0, 1, 1, None, WHITE, "", ""), (0, 11, 1, 1, 10, [16, 16, 16], "", ""),
        (1, 10, 1, 1, 13, WHITE, "", ""), (3, 11, 1, 1, 5, [127, 0, 0], "", ""),
        (6, 10, 2, 1, 3, WHITE, "", ""), (7, 10, 2, 1, 2, [32, 32, 32], "", ""),
        (2, 4, 2, 1, None, ALB, "Laser", "Cathedral"), (7, None, None, None, None, None, None, None),
        (5, 4, None, 1, 0, None, "Reactor", None),
    ]
    for row in rows:
        btn = CTXButton()
        btn.Update(*row[1:])
        sent.clear()
        d.CTXButtonScreen(btn.ButtonSysEx(row[0]))
        assert sent == [S.button_label(*row)], row
    for ident in range(8):
        sent.clear()
        d.CleanCTXButtonScreen(ident)
        assert sent == [S.clean_button(ident)]


# =====================================================================================================================
# 3. refusals
# =====================================================================================================================
@pytest.mark.parametrize("sid", [38, 43, 44])
def test_never_send_screens_cannot_be_built(sid):
    with pytest.raises(S.ScreenRefused):
        S.frame(sid, b"")


@pytest.mark.parametrize("sid", [38, 43, 44])
def test_the_gate_refuses_hand_made_never_send_frames(sid):
    raw = hx(HEAD) + bytes([sid]) + hx("00 00 F7")
    with pytest.raises(S.ScreenRefused):
        S.check(raw)
    sink = FakeOut(governed=True)
    with pytest.raises(S.ScreenRefused):
        S.ScreenWriter(sink).offer(raw)
    assert sink.sent == []


@pytest.mark.parametrize("raw", [P.daw_connect(True), P.daw_connect(False), P.set_led("A1", "green"),
                                 P.daw_connect(True, ctx=P.Ctx.ARTURIA), b"\x90\x3c\x40"])
def test_the_gate_sends_nothing_but_screen_frames(raw):
    sink = FakeOut(governed=True)
    with pytest.raises(S.ScreenRefused):
        S.ScreenWriter(sink).offer(raw)
    assert sink.sent == []


def test_bad_bytes_and_nul_are_refused():
    with pytest.raises(S.ScreenRefused):
        S.f2l("a", 1, [128, 0, 0], "b", 1, WHITE)          # colour channel over 127
    with pytest.raises(S.ScreenRefused):
        S.knob("a", "b", 200, 1, WHITE)                     # bar over 127
    with pytest.raises(S.ScreenRefused):
        S.f1l("nul\x00inside", 1, WHITE)
    with pytest.raises(S.ScreenRefused):
        S.button_label(0, line1="♯")                   # the script would raise UnicodeEncodeError
    with pytest.raises(S.ScreenRefused):
        S.button_label(8)


# =====================================================================================================================
# 4. the writer: change-only, newest-wins, paced, governed
# =====================================================================================================================
class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += max(0.0, s)


class FakeOut:
    def __init__(self, governed: bool, clock=None):
        self.sent, self.times, self.clock = [], [], clock
        if governed:
            self.governor = object()      # stands in for MidiOut's own governor

    def send_sysex(self, data):
        self.sent.append(bytes(data))
        self.times.append(self.clock() if self.clock else 0.0)


def _frames(n):
    return [S.f2l(f"chord {i}", 1, WHITE, "x", 1, WHITE) for i in range(n)]


def test_same_frame_twice_is_sent_once():
    clk = FakeClock()
    out = FakeOut(governed=True)
    w = S.ScreenWriter(out, clock=clk, sleep=clk.sleep)
    a = _frames(1)[0]
    assert w.offer(a) is True
    clk.t += 5
    assert w.offer(a) is False
    w.pump()
    assert out.sent == [a] and w.unchanged == 1


def test_newest_frame_wins_inside_the_interval():
    clk = FakeClock()
    out = FakeOut(governed=True, clock=clk)
    w = S.ScreenWriter(out, min_interval=0.1, clock=clk, sleep=clk.sleep)
    a, b, c = _frames(3)
    assert w.offer(a) is True                 # first frame goes at once
    clk.t += 0.03
    assert w.offer(b) is False                # held
    clk.t += 0.03
    assert w.offer(c) is False                # replaces b
    w.pump()
    assert out.sent == [a]
    clk.t += 0.05                             # 0.11 s after a
    assert w.pump() is True
    assert out.sent == [a, c] and w.coalesced == 1
    assert out.times[1] - out.times[0] >= 0.1


def test_back_to_what_is_shown_cancels_the_held_frame():
    clk = FakeClock()
    out = FakeOut(governed=True)
    w = S.ScreenWriter(out, clock=clk, sleep=clk.sleep)
    a, b = _frames(2)
    w.offer(a)
    clk.t += 0.01
    w.offer(b)
    clk.t += 0.01
    w.offer(a)                                # the screen already shows a
    clk.t += 1
    w.pump()
    assert out.sent == [a]


def test_a_flood_of_changes_never_beats_one_frame_per_interval():
    clk = FakeClock()
    out = FakeOut(governed=True, clock=clk)
    w = S.ScreenWriter(out, min_interval=0.1, clock=clk, sleep=clk.sleep)
    for i, f in enumerate(_frames(200)):      # a change every 5 ms for a second
        w.offer(f)
        w.pump()
        clk.t += 0.005
    gaps = [b - a for a, b in zip(out.times, out.times[1:])]
    assert min(gaps) >= 0.1 - 1e-9
    assert 9 <= len(out.sent) <= 11
    w.flush()                                 # the newest frame may still be held; flush sends it
    assert out.sent[-1] == _frames(200)[-1]


def test_an_ungoverned_sink_gets_the_writers_own_burst_governor():
    clk = FakeClock()
    gov = BurstGovernor(limit=12, window=0.1, clock=clk, sleep=clk.sleep)
    gov.record = True
    out = FakeOut(governed=False, clock=clk)
    w = S.ScreenWriter(out, min_interval=0.0, governor=gov, clock=clk, sleep=clk.sleep)
    for f in _frames(40):
        w.offer(f)
    assert len(out.sent) == 40 and gov.admitted == 40
    assert max_in_window(gov.log, 0.1) <= 12


def test_a_governed_sink_is_not_double_governed():
    out = FakeOut(governed=True)
    assert S.ScreenWriter(out).governor is None


def test_reassert_resends_the_current_frame_on_its_timer():
    clk = FakeClock()
    out = FakeOut(governed=True)
    w = S.ScreenWriter(out, reassert_s=2.0, clock=clk, sleep=clk.sleep)
    a = _frames(1)[0]
    w.offer(a)
    clk.t += 1.0
    assert w.pump() is False
    clk.t += 1.1
    assert w.pump() is True
    assert out.sent == [a, a] and w.reasserted == 1


# =====================================================================================================================
# 5. the readout
# =====================================================================================================================
def test_readout_before_the_engine_answers():
    r = S.Readout()
    assert r.view()[0] == "Aurora" and "waiting" in r.view()[2]


def test_readout_chord_bpm_scene():
    r = S.Readout(scene="Laser Cathedral")
    r.feed({"t": "hello", "v": 1}, 0.0)
    r.feed({"t": "chord", "src": "keys", "name": "Dbmaj7", "quality": "maj7"}, 0.1)
    r.feed({"t": "beat", "bpm": 127.8, "conf": 0.8, "n": 5, "due_ms": 240}, 0.2)
    line1, c1, line2, c2 = r.view()
    assert line1 == "Dbmaj7"
    assert line2 == "128 BPM | Laser Cathedral"
    assert c1 == S.rgb7((255, 0, 80))          # chordview's maj7 mood colour, halved like the script does
    assert c2 == S.WHITE7                       # locked
    frame = S.render(r.view())
    assert frame[9] == S.ScreenId.F2L and b"Dbmaj7" in frame and b"128 BPM | LASER CATHEDRAL" in frame


def test_minor_chord_keeps_its_lower_case_m_on_line_1():
    r = S.Readout()
    r.feed({"t": "_up"}, 0)
    r.feed({"t": "chord", "name": "Am", "quality": "m"}, 0)
    assert b"\x00Am\x00" in S.render(r.view())


def test_bpm_does_not_flap_between_neighbours():
    r = S.Readout()
    r.feed({"t": "_up"}, 0)
    for bpm in (127.4, 127.6, 127.45, 127.7, 127.3, 127.65):   # all within 0.75 of the shown 127
        r.feed({"t": "beat", "bpm": bpm, "conf": 0.9}, 0)
        assert r.bpm_shown == 127
    r.feed({"t": "beat", "bpm": 127.9, "conf": 0.9}, 0)          # 0.9 away: the tracker really moved
    assert r.bpm_shown == 128
    r.feed({"t": "beat", "bpm": 127.4, "conf": 0.9}, 0)          # and it does not fall straight back
    assert r.bpm_shown == 128


def test_lock_has_hysteresis():
    r = S.Readout()
    r.feed({"t": "_up"}, 0)
    r.feed({"t": "beat", "bpm": 120, "conf": 0.6}, 0)
    assert r.locked
    r.feed({"t": "beat", "bpm": 120, "conf": 0.5}, 0)
    assert r.locked
    r.feed({"t": "beat", "bpm": 120, "conf": 0.4}, 0)
    assert not r.locked


def test_played_chord_outranks_the_song_estimate_for_a_moment():
    r = S.Readout(prefer_keys_s=3.0)
    r.feed({"t": "_up"}, 0)
    r.feed({"t": "chord", "src": "keys", "name": "C", "quality": "maj"}, 10.0)
    r.feed({"t": "chord", "src": "audio", "name": "Am", "quality": "m"}, 11.0)
    assert r.view()[0] == "C"
    r.feed({"t": "chord", "src": "audio", "name": "Am", "quality": "m"}, 14.0)
    assert r.view()[0] == "Am  (song)"


def test_line_1_carries_the_roman_numeral_and_the_key_in_their_own_case():
    """vj --chords sense: chordsense's numeral and key ride with the chord on line 1 -- the only line the script leaves in
    its own case (line 2 would show 'vi' as 'VI' and 'Db' as 'DB')."""
    r = S.Readout()
    r.feed({"t": "hello", "v": 1, "chords": "sense"}, 0.0)
    r.feed({"t": "key", "name": "Db major", "conf": 0.8, "src": "keys"}, 0.1)
    r.feed({"t": "chord", "src": "keys", "name": "Gbmaj7", "root": 6, "quality": "maj7", "bass": 6, "roman": "IVmaj7",
            "key": "Db major", "conf": 1.0}, 0.2)
    r.feed({"t": "beat", "bpm": 150.2, "conf": 0.8, "n": 1}, 0.3)
    line1, _c1, line2, _c2 = r.view()
    assert line1 == "Gbmaj7  IVmaj7  in Db" and line2 == "150 BPM"
    frame = S.render(r.view())
    assert b"\x00Gbmaj7  IVmaj7  in Db\x00" in frame and b"150 BPM" in frame
    r.feed({"t": "chord", "src": "keys", "name": "Bbm", "root": 10, "quality": "m", "roman": "vi", "key": "Db major"}, 0.4)
    assert r.view()[0] == "Bbm  vi  in Db"                        # the lower-case numeral survives
    r.feed({"t": "chord", "src": "keys", "name": "Ab7/C", "root": 8, "quality": "7", "bass": 0, "roman": "V65",
            "key": "Db major"}, 0.5)
    assert r.view()[0] == "Ab7/C  V65  in Db"
    r.feed({"t": "key", "name": "Bb minor", "conf": 0.7}, 0.6)        # the key moved: the old numeral is not shown
    assert r.view()[0] == "Ab7/C  in Bbm"
    r.feed({"t": "chord", "src": "keys", "name": "Ebdim", "root": 3, "quality": "dim", "roman": "ii°",
            "key": "Bb minor"}, 0.7)
    assert r.view()[0] == "Ebdim  iio  in Bbm" and b"\x00Ebdim  iio  in Bbm\x00" in S.render(r.view())   # ASCII


def test_line_1_from_the_song_and_from_an_engine_with_no_numerals():
    r = S.Readout(prefer_keys_s=0.0)
    r.feed({"t": "_up"}, 0)
    r.feed({"t": "chord", "src": "audio", "name": "Am", "quality": "m", "roman": "i", "key": "A minor"}, 1.0)
    assert r.view()[0] == "Am  i  in Am  (song)"                   # no key event yet: the chord's own key
    r.feed({"t": "chord", "src": "audio", "name": "N", "root": None, "quality": None, "roman": None,
            "key": "A minor"}, 2.0)
    assert r.view()[0] == "--"                                     # no chord (drums, noise): nothing stale
    r.feed({"t": "chord", "src": "audio", "name": "F", "quality": "maj"}, 3.0)   # --chords basic: no numeral, no key
    assert r.view()[0] == "F  (song)"


def test_a_long_line_1_drops_song_then_key_never_the_chord_or_numeral():
    assert S.fit_line(["Gbmaj7", "IVmaj7", "in Db", "(song)"], drop=(3, 2)) == "Gbmaj7  IVmaj7  in Db  (song)"
    # 34 characters with two spaces: one space each fits (31), and nothing is left out
    assert S.fit_line(["Dbmaj7/Ab", "IVmaj64", "in Dbm", "(song)"], drop=(3, 2)) == "Dbmaj7/Ab IVmaj64 in Dbm (song)"
    long = ["C#m7b5/G", "#VIImaj65/V", "in C#m", "(song)"]
    line = S.fit_line(long, drop=(3, 2))
    assert len(line) <= S.LINE_LEN and line.startswith("C#m7b5/G") and "#VIImaj65/V" in line
    assert S.fit_line(["A" * 20, "B" * 10, "in Db", "(song)"], drop=(3, 2)) == "A" * 20 + "  " + "B" * 10
    assert S.key_short("F# minor") == "F#m" and S.key_short("Gb major") == "Gb" and S.key_short("nonsense") is None


def test_the_live_readout_redraws_only_when_the_chord_numeral_or_key_changes():
    q = queue.Queue()
    for evt in ({"t": "hello", "v": 1, "chords": "sense"}, {"t": "key", "name": "Db major", "conf": 0.8},
                {"t": "chord", "src": "keys", "name": "Gb", "root": 6, "quality": "maj", "roman": "IV", "key": "Db major"},
                {"t": "tension", "value": 0.3, "pedal_pc": None},                        # no change on the screen
                {"t": "chord", "src": "keys", "name": "Gb", "root": 6, "quality": "maj", "roman": "IV",
                 "key": "Db major", "changed": False},                                 # the same chord again
                {"t": "key", "name": "Db major", "conf": 0.9}):                        # the same key again
        q.put(evt)
    out = FakeOut(governed=True, clock=time.perf_counter)
    S.run_live(out, events=q, secs=0.5, verbose=False, goodbye=False)
    texts = [d.decode("ascii", "replace") for d in out.sent]
    assert texts and "Gb  IV  in Db" in texts[-1], texts
    assert sum("Gb  IV  in Db" in t for t in texts) == 1, texts


def test_scene_event_and_offline():
    r = S.Readout(scene="One")
    r.feed({"t": "_up"}, 0)
    r.feed({"t": "scene", "name": "Reactor · II", "color": "#ff0080"}, 0)
    assert r.view()[2].endswith("Reactor - II") and r.view()[3] == (127, 0, 64)
    r.feed({"t": "_down"}, 1)
    assert r.view()[2] == "VJ engine offline"


def test_pulse_marks_the_beat():
    r = S.Readout(pulse=True)
    r.feed({"t": "_up"}, 0)
    r.feed({"t": "beat", "bpm": 120, "conf": 0.9, "n": 6}, 0)
    assert "..*." in r.view()[2]


def test_ascii_clean_spells_music_symbols():
    assert S.ascii_clean("D♭maj7 / C♯\tm") == "Dbmaj7 / C# m"
    assert S.ascii_clean("é") == "?"


def test_sse_parser():
    p = S.SSEParser()
    lines = [": hb", 'data: {"t":"hello","v":1}', "", "data: not json", "", 'data: {"t":"chord",', 'data: "name":"C"}',
             "", "event: x", "", 'data:{"t":"beat","bpm":120}', ""]
    got = [e for e in (p.feed(x + "\n") for x in lines) if e is not None]
    assert got == [{"t": "hello", "v": 1}, {"t": "chord", "name": "C"}, {"t": "beat", "bpm": 120}]


# =====================================================================================================================
# 6. live, end to end: a fake VJ engine on a test-band port (8900-8999), a fake sink, a real clock
# =====================================================================================================================
def _free_test_port() -> int:
    for port in range(8960, 9000):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    pytest.skip("no free port in the 8960-8999 test band")


EVENTS = [{"t": "hello", "v": 1, "src": "keylab-vj"}, {"t": "status", "msg": "ok"},
          {"t": "chord", "src": "keys", "name": "F#m7", "root": 6, "quality": "m7", "pcs": [1, 4, 6, 9]},
          {"t": "beat", "due_ms": 200, "bpm": 124.2, "conf": 0.9, "n": 1, "on_beat": None},
          {"t": "energy", "bass": 0.5, "mid": 0.3, "high": 0.1, "level": 0.4}]


class _Engine(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/api/events":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(b": hb\n\n")
        for evt in EVENTS:
            self.wfile.write(b"data: " + json.dumps(evt).encode() + b"\n\n")
            self.wfile.flush()
            time.sleep(0.05)
        time.sleep(1.5)

    def log_message(self, *a):
        pass


def test_live_readout_from_a_fake_engine():
    port = _free_test_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), _Engine)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        out = FakeOut(governed=True, clock=time.perf_counter)
        stats = S.run_live(out, url=f"http://127.0.0.1:{port}/api/events", scene="Reactor", secs=1.2,
                           verbose=False)
    finally:
        server.shutdown()
        server.server_close()
    texts = [d.decode("ascii", "replace") for d in out.sent]
    assert any("F#m7" in t and "124 BPM | REACTOR" in t for t in texts), texts
    assert texts[-1].find("LIVE READOUT STOPPED") > 0
    assert all(S.check(d) == S.ScreenId.F2L for d in out.sent)
    gaps = [b - a for a, b in zip(out.times, out.times[1:])]
    assert not gaps or min(gaps) >= 0.1 - 1e-3
    assert stats["sent"] == len(out.sent)


def test_live_readout_says_offline_when_no_engine_answers():
    port = _free_test_port()                  # nothing listens here
    out = FakeOut(governed=True, clock=time.perf_counter)
    S.run_live(out, url=f"http://127.0.0.1:{port}/api/events", secs=0.4, verbose=False, goodbye=False)
    assert out.sent and b"WAITING FOR THE VJ ENGINE" in out.sent[0]


def test_live_readout_with_pulse_draws_the_beat_when_it_lands():
    q = queue.Queue()
    for evt in ({"t": "hello"}, {"t": "beat", "due_ms": 300, "bpm": 120, "conf": 0.9, "n": 2}):
        q.put(evt)
    out = FakeOut(governed=True, clock=time.perf_counter)
    t0 = time.perf_counter()
    S.run_live(out, events=q, pulse=True, secs=0.8, verbose=False, goodbye=False)
    marked = [t for d, t in zip(out.sent, out.times) if b"..*." in d]
    assert marked and marked[0] - t0 >= 0.28


# =====================================================================================================================
# 7. the CLI, dry-run only
# =====================================================================================================================
def test_cli_one_shot_dry_run(capsys):
    assert CLI.main(["screen", "Aurora", "--line2", "night shift", "--dry-run"]) == 0
    out = capsys.readouterr().out
    want = S.f2l("Aurora", 1, S.rgb7("teal"), "night shift", 1, S.rgb7("white")).hex(" ").upper()
    assert want in out
    assert "05 01 F7" not in out and "05 00 F7" not in out      # no DAW connect / disconnect in guest mode


def test_cli_labels_dry_run(capsys):
    assert CLI.main(["screen", "--labels", "Reactor,Laser,Curtains", "--active", "2", "--dry-run"]) == 0
    lines = [l for l in capsys.readouterr().out.splitlines() if "SysEx" in l]
    assert len(lines) == 8
    assert "52 65 61 63 74 6F 72" in lines[0]                   # "Reactor" on button 1 (screen id 5)
    assert lines[0].split()[10] == "05"


def test_cli_connect_is_refused_while_fl_runs(monkeypatch, capsys):
    monkeypatch.setattr(S, "fl_running", lambda: True)
    assert CLI.main(["screen", "hi", "--connect"]) == 2
    assert "refused" in capsys.readouterr().err
