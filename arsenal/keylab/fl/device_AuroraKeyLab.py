# name=Aurora KeyLab
"""Aurora KeyLab v0 ("Aurora drives"): the house's FL Studio script for the KeyLab 88 mk3 DAW port.

Pick it in FL (Options > MIDI settings) as the Controller type of the "KeyLab 88 mk3 DAW" input, in place of
Arturia's "KeyLab mk3". Leave the "KeyLab 88 mk3 MIDI" input on its own script, so keys and Analog Lab keep working.

What it does on the DAW port, and nothing more:
  * on load it arms the KeyLab's DAW mode and asks for the pads on the DAW port, as Arturia's script does (two
    SysEx); on unload it drops DAW mode (one SysEx);
  * the transport buttons drive FL: play/pause, stop, record, loop recording, metronome, save, undo, redo. Tap is
    swallowed: it is tap tempo for Aurora's visuals only (TAP_TO_FL = True gives it back to FL's tap tempo). Rewind and
    Fast forward are swallowed too: they step the VJ page's sets (SCRUB_TO_FL = True gives them back to FL's rewind /
    fast forward while held);
  * every other message on the DAW port is swallowed, so FL does nothing with it: faders, knobs, their touch
    sensors, the dial, Back, Quantize, the screen buttons and the DAW-bank pads (notes 0-11 on channel 10). Aurora's
    own programs read the same messages from the shared input and bind them to whatever you choose;
  * the bank A-D pads (channel 10, notes 12 and up) pass to FL untouched, so FPC, Addictive Drums or whatever channel
    is selected keeps playing them (BANK_PADS_TO_FL = False swallows them too);
  * the pitch and mod wheels, if they ever arrive on this port, pass through to FL untouched (plain MIDI, as any
    keyboard), because swallowing them would silence the wheels on the selected channel;
  * it never writes the screen and never colours a pad. The only lights it touches are the four transport
    state LEDs (play, record, loop, metronome), and only when one changes.

Every FL function this script can call (the list the P23 freeze drill walks, one button at a time):
  device.midiOutSysex           the handshake, the pad-port property and the four state LEDs
  transport.start               Play (on release)
  transport.stop                Stop (on press)
  transport.record              Record (on release)
  transport.continuousMove      Rewind / Fast forward (press starts, release stops), only with SCRUB_TO_FL
  transport.globalTransport     Loop (release), Metronome (release), Save (press); Tap (press) only with TAP_TO_FL
  general.undoUp                Undo (on press)
  general.undoDown              Redo (on press)
  transport.isPlaying           [state LEDs] these four are read only when FL says the LEDs changed
  transport.isRecording         [state LEDs] (OnRefresh with HW_Dirty_LEDs), or on the first refresh after
  ui.isLoopRecEnabled           [state LEDs] loading; MIRROR_TRANSPORT_LEDS = False turns all four off
  ui.isMetronomeEnabled         [state LEDs]

Attribution. Written for Akashic Aurora; no code was copied from anyone. Facts came from:
  * Arturia's KeyLab mk3 FL script, read for facts only (numbers, ids, message shapes): the SysEx envelope and the
    DAW connect / disconnect payloads (KL3Dispatch.py, KL3Connexion.py), the DAW-port control numbers and which FL
    function each transport button drives, on which edge (KL3Process.py), the LED ids (LedId.py) and the
    transport LED colours (KL3Return.py), and its DAW User Guide (ports 236 in and out, the two-script setup);
  * Image-Line's MIDI scripting manual (the device_ prefix, the "# name=" line, Controller type) and the
    IL-maintained API stubs (callbacks, FlMidiMsg.handled, the transport / general / ui / device functions);
  * FL Studio 2026's own Shared/Python/Lib/midi.py for the constant values (FPT_*, SS_*, HW_Dirty_LEDs).
"""

import device
import general
import midi
import time
import transport
import ui

VERSION = "v0"

# ------------------------------------------------------------------------------------------------------------------
# The DAW handshake. Equal to arsenal.keylab.protocol.daw_connect(True / False) (tests pin it).
ENVELOPE_OPEN = bytes((0xF0, 0x00, 0x20, 0x6B, 0x7F, 0x42))
ENVELOPE_CLOSE = bytes((0xF7,))
DAW_CONNECT = ENVELOPE_OPEN + bytes((0x00, 0x02, 0x05, 0x01)) + ENVELOPE_CLOSE
DAW_DISCONNECT = ENVELOPE_OPEN + bytes((0x00, 0x02, 0x05, 0x00)) + ENVELOPE_CLOSE
# The "Pad MIDI Port" property (DAW family, properties, item 0x14): the pads report on the DAW port. Arturia's script
# sends it at start-up; sending it too keeps the pads where they are today, after a power cycle as well.
SEND_PAD_PORT = True
PAD_PORT_PROPERTY = ENVELOPE_OPEN + bytes((0x00, 0x02, 0x00, 0x14, 0x02, 0x01, 0x00)) + ENVELOPE_CLOSE

# ------------------------------------------------------------------------------------------------------------------
# Transport buttons: control number on the DAW port -> (what it does, which edge acts).
# The edges are the ones FL users of this keyboard already know: Play, Record, Loop and Metronome act when the
# button comes back up; Stop, Tap, Save, Undo and Redo when it goes down; Rewind and Fast forward run while held.
PRESS = "press"
RELEASE = "release"
HELD = "held"

TRANSPORT_BUTTONS = {
    20: ("stop", PRESS),
    21: ("play", RELEASE),
    22: ("record", RELEASE),
    23: ("tap", PRESS),
    24: ("loop", RELEASE),
    25: ("rewind", HELD),
    26: ("forward", HELD),
    27: ("metronome", RELEASE),
    41: ("save", PRESS),
    43: ("undo", PRESS),
    44: ("redo", PRESS),
}
SCRUB_SPEED = {"rewind": -2, "forward": 2}

# Tap is tempo for the visuals only (Daniel, 2026-10-25: "only tempo for vfx"): the button is swallowed here, so FL's
# tempo never moves, and Aurora's VJ engine reads the same press from the shared input as its tap tempo. True gives
# the press back to FL's tap tempo.
TAP_TO_FL = False

# Rewind and Fast forward step the VJ page's sets, always (Daniel, 2026-10-25: "lets try always we can make it an
# option"): the buttons are swallowed here, so FL does not scrub while the page changes set. True gives them back to
# FL's rewind / fast forward while held (and ?transport=off on the page stops it listening).
SCRUB_TO_FL = False

# Plain-MIDI wheels go to FL untouched (set False to swallow them too).
WHEELS_TO_FL = True
MOD_WHEEL = 1

# Bank A-D pads (channel 10, notes 12 and up) go to FL untouched, so drum channels keep playing them. The DAW-bank pads
# (notes 0-11 on channel 10) are always swallowed: left to FL they would play notes 0-11 on the selected channel.
BANK_PADS_TO_FL = True
PAD_CHANNEL = 9            # channel 10, zero-based in the status byte
DAW_PAD_NOTES = 12

# ------------------------------------------------------------------------------------------------------------------
# The four transport state LEDs. LED id -> ((r, g, b) when off, (r, g, b) when on), 7-bit colour.
MIRROR_TRANSPORT_LEDS = True
LED_RECORD = 5
LED_PLAY = 6
LED_LOOP = 8
LED_METRONOME = 11
STATE_LEDS = (LED_PLAY, LED_RECORD, LED_LOOP, LED_METRONOME)
LED_LOOK = {
    LED_PLAY: ((0, 13, 0), (0, 127, 0)),
    LED_RECORD: ((13, 0, 0), (127, 0, 0)),
    LED_LOOP: ((13, 10, 0), (127, 72, 0)),
    LED_METRONOME: ((13, 13, 13), (127, 127, 127)),
}

# House burst rule for SysEx to the KeyLab: at most 12 in any 100 ms. The handshake is never held back, so the
# LED path stops one short of the limit and keeps a slot free for it.
BURST_LIMIT = 12
BURST_WINDOW_S = 0.100
LED_HEADROOM = 1

_clock = time.monotonic
_recent_writes = []        # clock readings of the SysEx this script sent inside the current window
_led_wanted = {}           # LED id -> True / False, FL's state at the last read
_led_shown = {}            # LED id -> True / False, what the KeyLab was last told
_led_backlog = False       # True when the burst rule held LED packets back; OnIdle sends them later
_scrubbing = set()         # control numbers of Rewind / Fast forward currently held


# ------------------------------------------------------------------------------------------------------------------
# Writing to the KeyLab
def _free_slots():
    now = _clock()
    while _recent_writes and now - _recent_writes[0] >= BURST_WINDOW_S:
        del _recent_writes[0]
    return BURST_LIMIT - len(_recent_writes)


def _send(packet):
    _free_slots()
    _recent_writes.append(_clock())
    device.midiOutSysex(packet)


def _led_packet(led, lit):
    r, g, b = LED_LOOK[led][1 if lit else 0]
    return ENVELOPE_OPEN + bytes((0x00, 0x02, 0x03, led, r, g, b, 0x00)) + ENVELOPE_CLOSE


def _flush_leds():
    global _led_backlog
    _led_backlog = False
    for led in STATE_LEDS:
        lit = _led_wanted.get(led)
        if lit is None or _led_shown.get(led) == lit:
            continue
        if _free_slots() <= LED_HEADROOM:
            _led_backlog = True
            return
        _send(_led_packet(led, lit))
        _led_shown[led] = lit


def _read_led_states():
    _led_wanted[LED_PLAY] = bool(transport.isPlaying())
    _led_wanted[LED_RECORD] = bool(transport.isRecording())
    _led_wanted[LED_LOOP] = bool(ui.isLoopRecEnabled())
    _led_wanted[LED_METRONOME] = bool(ui.isMetronomeEnabled())


# ------------------------------------------------------------------------------------------------------------------
# Driving FL
def _scrub(control, speed, down):
    if down:
        _scrubbing.add(control)
        transport.continuousMove(speed, midi.SS_Start)
    else:
        _scrubbing.discard(control)
        transport.continuousMove(speed, midi.SS_Stop)


def _do(action):
    if action == "play":
        transport.start()
    elif action == "stop":
        transport.stop()
    elif action == "record":
        transport.record()
    elif action == "tap":
        transport.globalTransport(midi.FPT_TapTempo, 1)
    elif action == "loop":
        transport.globalTransport(midi.FPT_LoopRecord, 1)
    elif action == "metronome":
        transport.globalTransport(midi.FPT_Metronome, 1)
    elif action == "save":
        transport.globalTransport(midi.FPT_Save, 1)
    elif action == "undo":
        general.undoUp()
    elif action == "redo":
        general.undoDown()


def _transport_button(control, value):
    action, edge = TRANSPORT_BUTTONS[control]
    down = value != 0
    if action == "tap" and not TAP_TO_FL:
        return
    if edge == HELD and not SCRUB_TO_FL:
        return
    if edge == HELD:
        _scrub(control, SCRUB_SPEED[action], down)
    elif down == (edge == PRESS):
        _do(action)


def _is_wheel(kind, control):
    return kind == 0xE0 or (kind == 0xB0 and control == MOD_WHEEL)


def _is_bank_pad(status, note):
    return status & 0xF0 in (0x80, 0x90, 0xA0) and status & 0x0F == PAD_CHANNEL and note >= DAW_PAD_NOTES


# ------------------------------------------------------------------------------------------------------------------
# FL's callbacks
def OnInit():
    global _led_backlog
    _led_wanted.clear()
    _led_shown.clear()
    _scrubbing.clear()
    _led_backlog = False
    _send(DAW_CONNECT)
    if SEND_PAD_PORT:
        _send(PAD_PORT_PROPERTY)
    print("Aurora KeyLab " + VERSION + ": FL keeps the transport; faders, knobs, pads and screen belong to Aurora.")


def OnDeInit():
    for control in sorted(_scrubbing):
        _scrub(control, SCRUB_SPEED[TRANSPORT_BUTTONS[control][0]], False)
    _send(DAW_DISCONNECT)


def OnMidiMsg(event):
    kind = event.status & 0xF0
    if kind == 0xB0 and event.data1 in TRANSPORT_BUTTONS:
        _transport_button(event.data1, event.data2)
        event.handled = True
        return
    if WHEELS_TO_FL and _is_wheel(kind, event.data1):
        return
    if BANK_PADS_TO_FL and _is_bank_pad(event.status, event.data1):
        return
    event.handled = True


def OnSysEx(event):
    event.handled = True


def OnRefresh(flags):
    if not MIRROR_TRANSPORT_LEDS:
        return
    if flags & midi.HW_Dirty_LEDs or not _led_wanted:
        _read_led_states()
        _flush_leds()


def OnDoFullRefresh():
    if not MIRROR_TRANSPORT_LEDS:
        return
    _led_shown.clear()
    _read_led_states()
    _flush_leds()


def OnIdle():
    if _led_backlog:
        _flush_leds()
