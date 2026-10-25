"""Pins for our FL Studio script (arsenal/keylab/fl/device_AuroraKeyLab.py) and its install verbs (flscript.py).

The script runs here against stub FL modules that record every call, so each pin says exactly which FL function a
message reaches (or that it reaches none). Nothing touches a keyboard or FL. Arturia's folder and FL's own midi.py
are only READ, as text, and only to cross-check facts (those pins skip on a machine without them); nothing is
imported from them, so no bytecode cache can be written there. Install pins use a temporary Hardware folder.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import os
import pathlib
import re
import sys
import types

import pytest

from arsenal.keylab import __main__ as CLI
from arsenal.keylab import flscript as F
from arsenal.keylab import protocol as P
from arsenal.keylab.governor import max_in_window

SCRIPT = pathlib.Path(F.SOURCE)
ARTURIA_DIR = pathlib.Path(os.path.expanduser("~")) / "Documents" / "Image-Line" / "FL Studio" / "Settings" / \
    "Hardware" / "Arturia KeyLab mk3"
FL_MIDI_PY = pathlib.Path(r"C:\Program Files\Image-Line\FL Studio 2026\Shared\Python\Lib\midi.py")

# The values FL 2026 ships in Shared/Python/Lib/midi.py (pinned against that file below when it is present).
MIDI_CONSTANTS = {"SS_Stop": 0, "SS_Start": 2, "FPT_TapTempo": 106, "FPT_LoopRecord": 113, "FPT_Metronome": 110,
                  "FPT_Save": 92, "HW_Dirty_LEDs": 256, "HW_Dirty_Mixer_Controls": 4, "HW_Dirty_ControlValues": 4096}

# Every FL function the script may call: the P23 drill list. Changing it is a decision, not a refactor.
FL_CALLS = {"device.midiOutSysex", "transport.start", "transport.stop", "transport.record",
            "transport.continuousMove", "transport.globalTransport", "general.undoUp", "general.undoDown",
            "transport.isPlaying", "transport.isRecording", "ui.isLoopRecEnabled", "ui.isMetronomeEnabled"}
FL_MODULES = {"device", "general", "midi", "transport", "ui"}
ALLOWED_IMPORTS = FL_MODULES | {"time"}       # all imported by Arturia's own scripts, so FL's Python has them


# =====================================================================================================================
# the script under stub FL modules
# =====================================================================================================================
class Ev:
    """A stand-in for FL's FlMidiMsg: the fields the script reads, and handled."""

    def __init__(self, status, data1=0, data2=0):
        self.status, self.data1, self.data2 = status, data1, data2
        self.handled = False


class Rig:
    def __init__(self, mod, calls, sent, state, clock):
        self.mod, self.calls, self.sent, self.state, self.clock = mod, calls, sent, state, clock

    def fl_calls(self):
        """Calls other than the SysEx writes."""
        return [c for c in self.calls if c[0] != "device.midiOutSysex"]

    def msg(self, status, d1=0, d2=0):
        ev = Ev(status, d1, d2)
        self.mod.OnMidiMsg(ev)
        return ev

    def clear(self):
        self.calls.clear()
        self.sent.clear()


@pytest.fixture
def rig(monkeypatch):
    calls, sent = [], []
    state = {"playing": False, "recording": False, "looprec": False, "metronome": False}
    clock = {"t": 1000.0}

    def recorder(qual, result=None):
        def fn(*args):
            calls.append((qual,) + args)
            return result(*args) if callable(result) else result
        return fn

    def out_sysex(data):
        calls.append(("device.midiOutSysex", bytes(data)))
        sent.append((clock["t"], bytes(data)))

    device = types.ModuleType("device")
    device.midiOutSysex = out_sysex
    transport = types.ModuleType("transport")
    for name in ("start", "stop", "record", "continuousMove", "globalTransport"):
        setattr(transport, name, recorder("transport." + name))
    transport.isPlaying = recorder("transport.isPlaying", lambda: state["playing"])
    transport.isRecording = recorder("transport.isRecording", lambda: state["recording"])
    general = types.ModuleType("general")
    general.undoUp = recorder("general.undoUp", 0)
    general.undoDown = recorder("general.undoDown", 0)
    ui = types.ModuleType("ui")
    ui.isLoopRecEnabled = recorder("ui.isLoopRecEnabled", lambda: state["looprec"])
    ui.isMetronomeEnabled = recorder("ui.isMetronomeEnabled", lambda: state["metronome"])
    midi = types.ModuleType("midi")
    for k, v in MIDI_CONSTANTS.items():
        setattr(midi, k, v)
    for name, m in (("device", device), ("transport", transport), ("general", general), ("ui", ui),
                    ("midi", midi)):
        monkeypatch.setitem(sys.modules, name, m)
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    spec = importlib.util.spec_from_file_location("aurora_keylab_fl_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._clock = lambda: clock["t"]
    return Rig(mod, calls, sent, state, clock)


def led(lid, rgb):
    return P.sysex([0x00, P.Ctx.DAW, P.Param.SET_LED, lid, *rgb, 0x00])


# =====================================================================================================================
# header, handshake
# =====================================================================================================================
def test_first_line_names_the_script_and_it_never_auto_claims_the_keyboard():
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "# name=Aurora KeyLab"
    assert F.SCRIPT_TITLE == "Aurora KeyLab" and SCRIPT.name.startswith("device_")
    # no supportedHardwareIds / supportedDevices: FL never picks this script on its own; Daniel picks it
    assert "supportedHardwareIds" not in text and "supportedDevices" not in text


def test_oninit_sends_exactly_the_daw_connect_and_the_pad_port_and_calls_nothing_else(rig):
    rig.mod.OnInit()
    assert [d for _, d in rig.sent] == [P.daw_connect(True), rig.mod.PAD_PORT_PROPERTY]
    assert rig.mod.DAW_CONNECT == P.daw_connect(True) == bytes.fromhex("F0 00 20 6B 7F 42 00 02 05 01 F7")
    assert rig.fl_calls() == []


def test_ondeinit_sends_exactly_the_daw_disconnect(rig):
    rig.mod.OnInit()
    rig.clear()
    rig.mod.OnDeInit()
    assert [d for _, d in rig.sent] == [P.daw_connect(False)]
    assert rig.mod.DAW_DISCONNECT == bytes.fromhex("F0 00 20 6B 7F 42 00 02 05 00 F7")
    assert rig.fl_calls() == []


def test_oninit_twice_is_harmless(rig):
    # the stubs warn OnInit "may be called multiple times"; each one re-arms DAW mode and resets the LED memory
    rig.mod.OnInit()
    rig.mod.OnRefresh(0)
    rig.mod.OnInit()
    assert rig.mod._led_shown == {} and rig.mod._led_wanted == {}
    assert [d for _, d in rig.sent].count(P.daw_connect(True)) == 2


# =====================================================================================================================
# transport
# =====================================================================================================================
GT = MIDI_CONSTANTS
TRANSPORT_EXPECT = {   # control number: (calls on press, calls on release)
    20: ([("transport.stop",)], []),
    21: ([], [("transport.start",)]),
    22: ([], [("transport.record",)]),
    23: ([], []),          # Tap is tempo for the visuals only (Daniel, 2026-10-25): swallowed, FL's tempo never moves
    24: ([], [("transport.globalTransport", GT["FPT_LoopRecord"], 1)]),
    25: ([], []),          # Rewind / Fast forward step the VJ sets, always (Daniel, 2026-10-25): swallowed, no scrub
    26: ([], []),
    27: ([], [("transport.globalTransport", GT["FPT_Metronome"], 1)]),
    41: ([("transport.globalTransport", GT["FPT_Save"], 1)], []),
    43: ([("general.undoUp",)], []),
    44: ([("general.undoDown",)], []),
}


def test_the_transport_map_is_the_surface_maps_numbers(rig):
    # keylab-full-surface-map-2026-10-23.md T1-T12: Play 21, Stop 20, Record 22, Tap 23, Loop 24, Rewind 25,
    # Fast forward 26, Metronome 27, Save 41, Undo 43, Redo 44 (Quantize 42 and Back 40 are deliberately left out)
    names = {cc: v[0] for cc, v in rig.mod.TRANSPORT_BUTTONS.items()}
    assert names == {20: "stop", 21: "play", 22: "record", 23: "tap", 24: "loop", 25: "rewind", 26: "forward",
                     27: "metronome", 41: "save", 43: "undo", 44: "redo"}
    assert set(TRANSPORT_EXPECT) == set(names)


@pytest.mark.parametrize("cc", sorted(TRANSPORT_EXPECT))
@pytest.mark.parametrize("channel", [0, 9])
def test_each_transport_button_press_and_release(rig, cc, channel):
    rig.mod.OnInit()
    on_press, on_release = TRANSPORT_EXPECT[cc]
    rig.clear()
    ev = rig.msg(0xB0 | channel, cc, 127)
    assert ev.handled is True
    assert rig.calls == on_press
    rig.clear()
    ev = rig.msg(0xB0 | channel, cc, 0)
    assert ev.handled is True
    assert rig.calls == on_release


def test_tap_stays_with_the_visuals_unless_given_back_to_fl(rig):
    # Daniel, 2026-10-25, asked whether Tap should keep changing FL's tempo: "only tempo for vfx"
    assert rig.mod.TAP_TO_FL is False
    rig.mod.OnInit()
    rig.clear()
    for value in (127, 0, 127, 0):
        assert rig.msg(0xB0 | 9, 23, value).handled is True
    assert rig.fl_calls() == []
    rig.mod.TAP_TO_FL = True                                  # the switch gives the press back to FL's tap tempo
    rig.clear()
    rig.msg(0xB0 | 9, 23, 127)
    assert rig.calls == [("transport.globalTransport", GT["FPT_TapTempo"], 1)]


def test_any_nonzero_value_is_a_press(rig):
    rig.msg(0xB0, 20, 1)
    assert rig.calls == [("transport.stop",)]


def test_scrub_stays_with_the_sets_unless_given_back_to_fl(rig):
    # Daniel, 2026-10-25, on Rewind / Fast forward stepping the VJ sets: "lets try always we can make it an option"
    assert rig.mod.SCRUB_TO_FL is False
    rig.mod.OnInit()
    rig.clear()
    for cc in (25, 26):
        for value in (127, 0):
            assert rig.msg(0xB0 | 9, cc, value).handled is True
    assert rig.fl_calls() == []
    rig.mod.TAP_TO_FL = False
    rig.mod.SCRUB_TO_FL = True                                # the switch gives them back to FL's scrub
    rig.clear()
    rig.msg(0xB0, 26, 127)
    rig.msg(0xB0, 26, 0)
    assert rig.calls == [("transport.continuousMove", 2, GT["SS_Start"]), ("transport.continuousMove", 2, GT["SS_Stop"])]


def test_rewind_held_when_the_script_unloads_is_stopped_first(rig):
    rig.mod.SCRUB_TO_FL = True                                # only FL's scrub can be held
    rig.mod.OnInit()
    rig.msg(0xB0, 25, 127)
    rig.clear()
    rig.mod.OnDeInit()
    assert rig.calls == [("transport.continuousMove", -2, GT["SS_Stop"]), ("device.midiOutSysex", P.daw_connect(False))]
    rig.clear()
    rig.mod.OnDeInit()                                    # nothing held any more: only the disconnect
    assert rig.fl_calls() == []


# =====================================================================================================================
# everything else is swallowed, with no FL call
# =====================================================================================================================
FADERS = list(range(105, 114))
FADER_TOUCH = [28, 29, 30, 31, 33, 34, 35, 36, 37]
KNOBS = [91, 92, 94, 95, 96, 97, 102, 103, 104]
KNOB_TOUCH = list(range(8, 16)) + [38]
SCREEN_BUTTONS = list(range(45, 53))
DIAL = [116, 117]
BACK_AND_QUANTIZE = [40, 42]


def surface_messages():
    """Every surface message the evidence lists for the DAW port, plus a sweep of every other CC and message type."""
    out = []
    for cc in FADERS:
        out += [(0xB0, cc, v) for v in (0, 1, 64, 127)]
    for cc in FADER_TOUCH + KNOB_TOUCH + SCREEN_BUTTONS + BACK_AND_QUANTIZE + [117]:
        out += [(0xB0, cc, 127), (0xB0, cc, 0)]
    for cc in KNOBS + [116]:
        out += [(0xB0, cc, v) for v in (65, 72, 63, 55)]
    for note in range(12):                                # DAW-bank pads: notes 0-11 on channel 10
        out += [(0x99, note, 100), (0x89, note, 0), (0x99, note, 0), (0xA9, note, 50)]
    for cc in range(128):                                 # the sweep: every CC we do not drive, both channels
        if cc in TRANSPORT_EXPECT or cc == 1:
            continue
        out += [(0xB0, cc, 127), (0xB0, cc, 0), (0xB9, cc, 127)]
    out += [(0x90, 60, 90), (0x80, 60, 0)]                                   # notes on other channels
    out += [(0xD9, 40, 0), (0xD0, 40, 0), (0xC0, 5, 0), (0xF8, 0, 0), (0xFA, 0, 0)]
    return out


def test_every_surface_message_is_swallowed_with_no_fl_call(rig):
    rig.mod.OnInit()
    rig.clear()
    msgs = surface_messages()
    assert len(msgs) > 500
    for status, d1, d2 in msgs:
        ev = rig.msg(status, d1, d2)
        assert ev.handled is True, f"{status:02X} {d1} {d2} was left for FL"
    assert rig.calls == [] and rig.sent == []


def test_the_named_surface_groups_are_all_in_the_sweep():
    covered = {(s & 0xF0, d1) for s, d1, _ in surface_messages()}
    for cc in FADERS + FADER_TOUCH + KNOBS + KNOB_TOUCH + SCREEN_BUTTONS + DIAL + BACK_AND_QUANTIZE:
        assert (0xB0, cc) in covered
    for note in range(12):
        assert (0x90, note) in covered and (0x80, note) in covered


def test_bank_pads_pass_to_fl_untouched_and_daw_pads_never_do(rig):
    rig.mod.OnInit()
    rig.clear()
    for status, note, vel in [(0x99, 36, 100), (0x89, 36, 0), (0x99, 51, 90), (0xA9, 40, 30), (0x99, 12, 64)]:
        ev = rig.msg(status, note, vel)
        assert ev.handled is False, f"bank pad {status:02X} {note} was swallowed (FPC would go silent)"
    for note in range(12):                                            # the DAW-bank pads are always swallowed
        assert rig.msg(0x99, note, 100).handled is True
    assert rig.msg(0x90, 36, 100).handled is True                     # channel 1 on the DAW port: not a pad
    assert rig.calls == [] and rig.sent == []


def test_bank_pads_can_be_swallowed_too(rig):
    rig.mod.BANK_PADS_TO_FL = False
    assert rig.msg(0x99, 36, 100).handled is True


def test_oninit_asks_for_the_pads_on_the_daw_port_as_arturia_does(rig):
    assert rig.mod.PAD_PORT_PROPERTY == bytes.fromhex("F0 00 20 6B 7F 42 00 02 00 14 02 01 00 F7")
    rig.mod.SEND_PAD_PORT = False
    rig.mod.OnInit()
    assert [d for _, d in rig.sent] == [rig.mod.DAW_CONNECT]


def test_the_wheels_pass_to_fl_untouched(rig):
    for status, d1, d2 in [(0xE0, 0, 64), (0xE0, 127, 127), (0xE9, 0, 0), (0xB0, 1, 90), (0xB0, 1, 0)]:
        ev = rig.msg(status, d1, d2)
        assert ev.handled is False
    assert rig.calls == []


def test_the_wheels_can_be_swallowed_too(rig):
    rig.mod.WHEELS_TO_FL = False
    assert rig.msg(0xE0, 0, 64).handled is True and rig.msg(0xB0, 1, 9).handled is True
    assert rig.calls == []


def test_sysex_on_the_daw_port_is_swallowed(rig):
    ev = Ev(0xF0)
    rig.mod.OnSysEx(ev)
    assert ev.handled is True and rig.calls == []


# =====================================================================================================================
# the four transport state LEDs, and never a screen frame or a pad
# =====================================================================================================================
DIM = {6: (0, 13, 0), 5: (13, 0, 0), 8: (13, 10, 0), 11: (13, 13, 13)}
LIT = {6: (0, 127, 0), 5: (127, 0, 0), 8: (127, 72, 0), 11: (127, 127, 127)}


def test_led_ids_are_protocols_buttons(rig):
    m = rig.mod
    assert (m.LED_PLAY, m.LED_RECORD, m.LED_LOOP, m.LED_METRONOME) == (
        P.BUTTONS["play"], P.BUTTONS["record"], P.BUTTONS["repeat"], P.BUTTONS["metronome"]) == (6, 5, 8, 11)
    assert set(m.STATE_LEDS) == {6, 5, 8, 11}
    # the packet builder agrees with protocol's (8-bit in, 7-bit out) for full colours
    assert m._led_packet(m.LED_RECORD, True) == P.set_led("record", (255, 0, 0))
    assert m._led_packet(m.LED_PLAY, True) == P.set_led("play", (0, 255, 0))


def test_first_refresh_paints_the_four_leds_once(rig):
    rig.mod.OnInit()
    rig.clear()
    rig.mod.OnRefresh(GT["HW_Dirty_ControlValues"])       # any first refresh reads the state once
    assert [d for _, d in rig.sent] == [led(6, DIM[6]), led(5, DIM[5]), led(8, DIM[8]), led(11, DIM[11])]
    assert [c[0] for c in rig.fl_calls()] == ["transport.isPlaying", "transport.isRecording",
                                              "ui.isLoopRecEnabled", "ui.isMetronomeEnabled"]


def test_later_refreshes_read_fl_only_when_fl_flags_the_leds(rig):
    rig.mod.OnInit()
    rig.mod.OnRefresh(0)
    rig.clear()
    for flags in (GT["HW_Dirty_Mixer_Controls"], GT["HW_Dirty_ControlValues"], 1, 2, 1024, 65536):
        rig.mod.OnRefresh(flags)
    assert rig.calls == []
    rig.mod.OnRefresh(GT["HW_Dirty_LEDs"])                # flagged, nothing changed: four reads, no packet
    assert len(rig.fl_calls()) == 4 and rig.sent == []


def test_a_change_sends_only_that_led(rig):
    rig.mod.OnInit()
    rig.mod.OnRefresh(0)
    rig.clear()
    rig.state["playing"] = True
    rig.mod.OnRefresh(GT["HW_Dirty_LEDs"] | GT["HW_Dirty_ControlValues"])
    assert [d for _, d in rig.sent] == [led(6, LIT[6])]
    rig.clear()
    rig.state.update(playing=False, recording=True, metronome=True)
    rig.mod.OnRefresh(GT["HW_Dirty_LEDs"])
    assert [d for _, d in rig.sent] == [led(6, DIM[6]), led(5, LIT[5]), led(11, LIT[11])]


def test_full_refresh_repaints_all_four(rig):
    rig.mod.OnInit()
    rig.mod.OnRefresh(0)
    rig.clear()
    rig.mod.OnDoFullRefresh()
    assert len(rig.sent) == 4


def test_led_mirror_off_means_no_reads_and_no_packets(rig):
    rig.mod.MIRROR_TRANSPORT_LEDS = False
    rig.mod.OnInit()
    rig.clear()
    rig.mod.OnRefresh(GT["HW_Dirty_LEDs"])
    rig.mod.OnDoFullRefresh()
    rig.mod.OnIdle()
    assert rig.calls == []


def test_idle_with_nothing_held_back_does_nothing(rig):
    rig.mod.OnInit()
    rig.mod.OnRefresh(0)
    rig.clear()
    for _ in range(50):
        rig.mod.OnIdle()
    assert rig.calls == []


def test_led_storm_stays_inside_the_burst_rule_and_catches_up(rig):
    rig.mod.OnInit()
    for i in range(40):                                   # every LED flips on every refresh, all in one instant
        on = i % 2 == 0
        rig.state.update(playing=on, recording=on, looprec=on, metronome=on)
        rig.mod.OnRefresh(GT["HW_Dirty_LEDs"])
        rig.mod.OnIdle()
    times = [t for t, _ in rig.sent]
    assert len(rig.sent) <= rig.mod.BURST_LIMIT == 12
    assert max_in_window(times, rig.mod.BURST_WINDOW_S) <= 12
    assert rig.mod._led_backlog is True
    rig.clock["t"] += 0.2                                 # the window passes: idle sends what was held back
    rig.mod.OnIdle()
    final = {6: rig.state["playing"], 5: rig.state["recording"], 8: rig.state["looprec"], 11: rig.state["metronome"]}
    assert rig.mod._led_shown == final and rig.mod._led_backlog is False


def test_a_long_session_never_sends_a_screen_frame_or_a_pad(rig):
    rig.mod.OnInit()
    for step in range(300):
        rig.clock["t"] += 0.013
        rig.state.update(playing=step % 7 < 3, recording=step % 11 == 0, looprec=step % 5 == 0,
                         metronome=step % 3 == 0)
        rig.mod.OnRefresh(GT["HW_Dirty_LEDs"] if step % 2 else GT["HW_Dirty_ControlValues"])
        rig.mod.OnIdle()
        for status, d1, d2 in surface_messages()[step::300]:
            rig.msg(status, d1, d2)
        for cc in TRANSPORT_EXPECT:
            rig.msg(0xB0, cc, 127 if step % 2 else 0)
    rig.mod.OnDoFullRefresh()
    rig.mod.OnDeInit()
    handshake = {P.daw_connect(True), P.daw_connect(False), rig.mod.PAD_PORT_PROPERTY}
    for _, d in rig.sent:
        assert d.startswith(P.HEADER) and d.endswith(bytes([P.EOX]))
        if d in handshake:
            continue
        payload = d[len(P.HEADER):-1]
        assert payload[:3] == bytes([0x00, P.Ctx.DAW, P.Param.SET_LED]), f"not an LED packet: {d.hex(' ')}"
        assert payload[3] in (5, 6, 8, 11), f"LED {payload[3]} is not a transport state LED"
        assert len(payload) == 8
    assert not any(d[len(P.HEADER) + 2] == P.Param.DISPLAY for _, d in rig.sent)
    assert max_in_window([t for t, _ in rig.sent], 0.100) <= 12


# =====================================================================================================================
# what the script is allowed to be: imports, FL calls, Python
# =====================================================================================================================
def _tree():
    return ast.parse(SCRIPT.read_text(encoding="utf-8"))


def _fl_calls_in(tree, modules):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id in modules:
            found.add(node.func.value.id + "." + node.func.attr)
    return found


def test_imports_only_what_arturias_scripts_already_import():
    tree = _tree()
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        assert not isinstance(node, ast.ImportFrom), "no from-imports"
    assert imported == ALLOWED_IMPORTS
    banned = {"open", "exec", "eval", "compile", "__import__", "globals", "getattr", "setattr"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in banned, node.func.id


def test_the_fl_calls_are_exactly_the_drill_list():
    assert _fl_calls_in(_tree(), FL_MODULES - {"midi"}) == FL_CALLS
    # midi is only read for constants, never called
    assert _fl_calls_in(_tree(), {"midi"}) == set()
    commands = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "globalTransport":
            commands.add(node.args[0].attr)
    assert commands == {"FPT_TapTempo", "FPT_LoopRecord", "FPT_Metronome", "FPT_Save"}


def test_the_docstring_lists_every_fl_call():
    doc = ast.get_docstring(_tree())
    for call in FL_CALLS:
        assert call in doc, call


def test_the_script_compiles_and_defines_the_callbacks():
    compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec")
    defined = {n.name for n in _tree().body if isinstance(n, ast.FunctionDef)}
    assert {"OnInit", "OnDeInit", "OnMidiMsg", "OnSysEx", "OnRefresh", "OnDoFullRefresh", "OnIdle"} <= defined


def test_midi_constants_match_fl_2026s_own_midi_py():
    if not FL_MIDI_PY.is_file():
        pytest.skip("FL Studio 2026 is not installed here")
    text = FL_MIDI_PY.read_text(encoding="utf-8", errors="replace")
    for name, value in MIDI_CONSTANTS.items():
        m = re.search(r"^" + name + r"\s*=\s*(\d+)", text, re.M)
        assert m and int(m.group(1)) == value, name


# =====================================================================================================================
# against Arturia's files (read as text, facts only)
# =====================================================================================================================
def _arturia_files():
    if not (ARTURIA_DIR / "device_KL3.py").is_file():
        pytest.skip("Arturia's FL script is not installed on this machine")
    return sorted(ARTURIA_DIR.glob("*.py"))


def test_every_fl_call_but_one_is_already_made_by_arturias_script():
    # Arturia's script runs on Daniel's FL 26.1.3 today and calls these; transport.isPlaying is the one new call
    theirs = set()
    for path in _arturia_files():
        theirs |= _fl_calls_in(ast.parse(path.read_text(encoding="utf-8", errors="replace")), FL_MODULES)
    assert FL_CALLS - theirs == {"transport.isPlaying"}


def test_the_transport_facts_agree_with_arturias_dispatch_table():
    text = (_arturia_files()[0].parent / "KL3Process.py").read_text(encoding="utf-8", errors="replace")
    handlers = dict((int(cc), name) for cc, name in re.findall(r"\.NewHandler\((\d+),\s*self\.(\w+)", text))
    assert handlers[21] == "Start" and handlers[20] == "Stop" and handlers[22] == "Record"
    assert handlers[23] == "TapTempo" and handlers[27] == "SetClick" and handlers[24] == "Loop"
    assert handlers[25] == "Rewind" and handlers[26] == "FastForward" and handlers[41] == "Save"
    assert handlers[43] == "Undo" and handlers[44] == "Redo"
    # the edges: the release-only and press-only filters
    for cc in (21, 22, 27, 24):
        assert re.search(r"\.NewHandler\(" + str(cc) + r",\s*self\.\w+,\s*ignore_press\)", text), cc
    for cc in (43, 44):
        assert re.search(r"\.NewHandler\(" + str(cc) + r",\s*self\.\w+,\s*ignore_release\)", text), cc


def _normal_lines(text):
    """Code lines with whitespace collapsed, minus blanks, comments, imports and short lines (else:, pass, ...)."""
    out = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line or line.startswith("#") or line.startswith("import ") or line.startswith("from "):
            continue
        if len(line) < 12:
            continue
        out.append(line)
    return out


def test_licence_no_three_consecutive_lines_appear_in_arturias_files():
    ours = _normal_lines(SCRIPT.read_text(encoding="utf-8"))
    ours_triples = {tuple(ours[i:i + 3]) for i in range(len(ours) - 2)}
    for path in _arturia_files():
        theirs = _normal_lines(path.read_text(encoding="utf-8", errors="replace"))
        for i in range(len(theirs) - 2):
            assert tuple(theirs[i:i + 3]) not in ours_triples, f"{path.name}: {theirs[i:i + 3]}"


def test_licence_no_name_we_define_is_one_arturia_defines():
    ours = set()
    for node in _tree().body:                             # our module-level names (FL's callback names are FL's)
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("On"):
            ours.add(node.name)
        elif isinstance(node, ast.Assign):
            ours |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    assert len(ours) > 30
    for path in _arturia_files():
        theirs = set()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8", errors="replace"))):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                theirs.add(node.name)
            elif isinstance(node, ast.Assign):
                theirs |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        assert not ours & theirs, f"{path.name}: {sorted(ours & theirs)}"


# =====================================================================================================================
# install / status / uninstall against a temporary Hardware folder
# =====================================================================================================================
@pytest.fixture
def hw(tmp_path, monkeypatch):
    root = tmp_path / "Hardware"
    arturia = root / "Arturia KeyLab mk3"
    (arturia / "__pycache__").mkdir(parents=True)
    (arturia / "device_KL3.py").write_bytes(b"# name=KeyLab mk3\nprint('theirs')\n")
    (arturia / "KL3Process.py").write_bytes(b"x = 1\n")
    (arturia / "__pycache__" / "KL3Display.cpython-311.pyc").write_bytes(b"\x00\x01")
    (root / "Arturia KeyLab mk3.ini").write_bytes(b"[Ini]\r\nVersion=1\r\n")
    monkeypatch.setattr(F, "fl_running", lambda: False)
    monkeypatch.setattr(F, "daw_port_scripts", lambda: [("FL Studio 26", "KeyLab 88 mk3 DAW", "KeyLab mk3")])
    return root


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "dir")
            for p in sorted(folder.rglob("*"))}


def outside_ours(root):
    return {k: v for k, v in snapshot(root).items() if not k.startswith(F.FOLDER_NAME + "/") and k != F.FOLDER_NAME}


def test_install_status_reinstall_uninstall_leave_arturia_byte_identical(hw):
    before = outside_ours(hw)
    target = hw / F.FOLDER_NAME / F.SCRIPT_NAME

    code, lines = F.install(hw, dry_run=True)
    assert code == 0 and not (hw / F.FOLDER_NAME).exists()
    assert any("would install" in line for line in lines)

    code, lines = F.install(hw)
    assert code == 0 and target.read_bytes() == SCRIPT.read_bytes()
    assert any("Aurora KeyLab (user)" in line for line in lines) and any("KeyLab mk3" in line for line in lines)
    assert sorted(p.name for p in (hw / F.FOLDER_NAME).iterdir()) == [F.SCRIPT_NAME]

    code, lines = F.status(hw)
    text = "\n".join(lines)
    assert code == 0 and "installed:    yes" in text and "same bytes:   yes" in text
    assert "Arturia's" in text and "FL running:   no" in text

    mtime = target.stat().st_mtime_ns
    code, lines = F.install(hw)
    assert code == 0 and "already installed" in lines[0] and target.stat().st_mtime_ns == mtime

    target.write_bytes(b"# name=Aurora KeyLab\n# an older copy\n")
    assert any("NO" in line for line in F.status(hw)[1])
    code, lines = F.install(hw)
    assert code == 0 and lines[0].startswith("replaced") and target.read_bytes() == SCRIPT.read_bytes()

    code, lines = F.uninstall(hw, dry_run=True)
    assert code == 0 and target.exists()
    code, lines = F.uninstall(hw)
    assert code == 0 and not (hw / F.FOLDER_NAME).exists()
    assert outside_ours(hw) == before

    code, lines = F.uninstall(hw)
    assert code == 0 and lines[0].startswith("not installed")


def test_a_folder_with_foreign_files_is_refused_and_left_alone(hw):
    folder = hw / F.FOLDER_NAME
    folder.mkdir()
    (folder / "notes.txt").write_bytes(b"Daniel's")
    (folder / F.SCRIPT_NAME).write_bytes(b"old")
    before = snapshot(hw)
    code, lines = F.install(hw)
    assert code == 2 and "notes.txt" in "\n".join(lines)
    code, lines = F.uninstall(hw)
    assert code == 2 and "notes.txt" in "\n".join(lines)
    assert snapshot(hw) == before
    assert "foreign files" in "\n".join(F.status(hw)[1])


def test_a_stray_cache_file_is_foreign_but_our_own_cache_is_ours(hw):
    folder = hw / F.FOLDER_NAME
    (folder / "__pycache__").mkdir(parents=True)
    (folder / F.SCRIPT_NAME).write_bytes(SCRIPT.read_bytes())
    (folder / "__pycache__" / "device_AuroraKeyLab.cpython-312.pyc").write_bytes(b"\x00")
    assert F.foreign_entries(folder) == []
    (folder / "__pycache__" / "KL3Display.cpython-312.pyc").write_bytes(b"\x00")
    assert F.foreign_entries(folder) == ["__pycache__/KL3Display.cpython-312.pyc"]
    assert F.uninstall(hw)[0] == 2
    (folder / "__pycache__" / "KL3Display.cpython-312.pyc").unlink()
    assert F.uninstall(hw)[0] == 0 and not folder.exists()


def test_a_missing_hardware_folder_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "fl_running", lambda: False)
    monkeypatch.setattr(F, "daw_port_scripts", lambda: [])
    code, lines = F.install(tmp_path / "nope")
    assert code == 2 and "--hardware-dir" in "\n".join(lines)
    assert not (tmp_path / "nope").exists()
    assert F.uninstall(tmp_path / "nope")[0] == 0


def test_a_file_where_our_folder_should_be_is_refused(hw):
    (hw / F.FOLDER_NAME).write_bytes(b"not a folder")
    assert F.install(hw)[0] == 2 and F.uninstall(hw)[0] == 2
    assert (hw / F.FOLDER_NAME).read_bytes() == b"not a folder"


def test_a_link_in_place_of_our_folder_is_refused(hw, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    try:
        os.symlink(elsewhere, hw / F.FOLDER_NAME, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("cannot create a symlink here")
    assert F.install(hw)[0] == 2
    assert list(elsewhere.iterdir()) == []


def test_uninstall_refuses_while_fl_has_ours_picked_unless_forced(hw, monkeypatch):
    F.install(hw)
    monkeypatch.setattr(F, "daw_port_scripts", lambda: [("FL Studio 26", "KeyLab 88 mk3 DAW", "Aurora KeyLab")])
    assert "(ours" in "\n".join(F.status(hw)[1])
    code, lines = F.uninstall(hw)
    assert code == 2 and "refused" in lines[0] and '"KeyLab mk3"' in lines[1]
    assert (hw / F.FOLDER_NAME / F.SCRIPT_NAME).is_file()                 # nothing removed
    code, lines = F.uninstall(hw, force=True)
    assert code == 0 and '"KeyLab mk3"' in lines[0] and not (hw / F.FOLDER_NAME).exists()


def test_uninstall_refuses_while_fl_runs_unless_forced(hw, monkeypatch):
    F.install(hw)
    monkeypatch.setattr(F, "daw_port_scripts", lambda: [])
    monkeypatch.setattr(F, "fl_running", lambda: True)
    assert F.uninstall(hw)[0] == 2 and (hw / F.FOLDER_NAME).exists()
    assert F.uninstall(hw, force=True)[0] == 0 and not (hw / F.FOLDER_NAME).exists()


def test_uninstall_leaves_fls_own_ini_for_our_folder(hw):
    F.install(hw)
    ini = hw / (F.FOLDER_NAME + ".ini")
    ini.write_bytes(b"[Ini]\r\nVersion=1\r\n")
    code, lines = F.uninstall(hw)
    assert code == 0 and ini.read_bytes() == b"[Ini]\r\nVersion=1\r\n"
    assert any("left in place" in line for line in lines)


def test_the_cli_verbs(hw, capsys):
    assert CLI.main(["fl-install", "--hardware-dir", str(hw), "--dry-run"]) == 0
    assert not (hw / F.FOLDER_NAME).exists()
    assert CLI.main(["fl-install", "--hardware-dir", str(hw)]) == 0
    assert CLI.main(["fl-status", "--hardware-dir", str(hw)]) == 0
    out = capsys.readouterr().out
    assert "same bytes:   yes" in out and "Options > MIDI settings" in out
    assert CLI.main(["fl-uninstall", "--hardware-dir", str(hw)]) == 0
    assert not (hw / F.FOLDER_NAME).exists()


def test_the_default_hardware_dir_is_under_documents():
    d = F.default_hardware_dir()
    assert d.parts[-4:] == ("Image-Line", "FL Studio", "Settings", "Hardware")
    assert F.hardware_dir(None) == d and F.hardware_dir("X:/elsewhere") == pathlib.Path("X:/elsewhere")


def test_install_doc_exists_and_names_the_drill():
    doc = (SCRIPT.parent / "INSTALL.md").read_text(encoding="utf-8")
    assert "Aurora KeyLab" in doc and "KeyLab mk3" in doc and "freeze" in doc.lower()
    assert "Image-Line/FL Studio/Settings/Hardware/Aurora KeyLab" in doc.replace("\\", "/")
