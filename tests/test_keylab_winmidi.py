"""winmidi against a fake winmm.dll: the four defects in section 4.1 of
research/reviewed/keylab-liberation-2026-10-22/keylab-dev-guidance-and-hang-guide-2026-10-27.md.

No keyboard and no MIDI port: winmidi._winmm is swapped for keylab_fake_winmm.FakeWinMM, which keeps the driver's
side of the contract and records every call, so each test can check bytes, order, thread and result codes.
  1. a captured SysEx keeps every byte (lpData was c_char_p and stopped at the first 00; Arturia's ID is 00 20 6B);
  2. a long-lived input never runs out of SysEx buffers, re-queues them off the callback thread, and start() waits
     ~20 ms after midiInStart before a probe may go (Windows MIDI Services drops replies stamped before the start);
  3. send_sysex reports a done-flag timeout and every result code, and never frees a header the driver still owns,
     not even when the caller drops the MidiOut without close() (vj.run did) or an interrupt lands mid-send;
  4. MidiIn.close stops before it resets and checks every result code.
"""
from __future__ import annotations

import ctypes
import gc
import sys
import time
import types
import weakref

import pytest

import keylab_fake_winmm as F
from arsenal.keylab import winmidi as W

IDENTITY_REPLY = bytes([0xF0, 0x7E, 0x7F, 0x06, 0x02, 0x00, 0x20, 0x6B, 0x02, 0x00, 0x0A, 0x08,
                        0x01, 0x05, 0x00, 0x00, 0xF7])          # 17 bytes; the maker ID starts with 00
LED = bytes([0xF0, 0x00, 0x20, 0x6B, 0x7F, 0x42, 0x00, 0x02, 0x03, 0x52, 0x7F, 0x00, 0x00, 0x00, 0xF7])


@pytest.fixture(autouse=True)
def _private_governor_dir(tmp_path, monkeypatch):
    # MidiOut's port-wide governor keeps its bucket on disk: never the real one from a test
    monkeypatch.setenv("AKASHIC_KEYLAB_GOVERNOR_DIR", str(tmp_path / "governor"))


@pytest.fixture
def fake(monkeypatch):
    f = F.FakeWinMM()
    monkeypatch.setattr(W, "_winmm", lambda: f)
    return f


def _sysex(midi_in):
    return [data for _t, data, kind in midi_in.events if kind == "sysex"]


# --- 1. every byte of a captured SysEx ------------------------------------------------------------------------------

def test_midihdr_lpdata_is_a_plain_pointer_and_the_layout_is_unchanged():
    assert W.MIDIHDR._fields_[0][1] is ctypes.c_void_p, "c_char_p reads a buffer only up to its first 00 byte"

    class Before(ctypes.Structure):              # the old declaration: same layout, only the pointer type differs
        _fields_ = [("lpData", ctypes.c_char_p)] + list(W.MIDIHDR._fields_[1:])

    assert ctypes.sizeof(W.MIDIHDR) == ctypes.sizeof(Before)
    assert [getattr(W.MIDIHDR, n).offset for n, _t in W.MIDIHDR._fields_] == \
        [getattr(Before, n).offset for n, _t in Before._fields_]
    if sys.platform == "win32":                  # Windows' own MIDIHDR: 120 bytes on x64, 64 on x86
        assert ctypes.sizeof(W.MIDIHDR) == (120 if ctypes.sizeof(ctypes.c_void_p) == 8 else 64)


def test_an_identity_reply_is_captured_whole(fake):
    m = W.MidiIn(prefer="daw", nbuf=4)
    m.start()
    assert fake.send_sysex(IDENTITY_REPLY)
    m.close()
    assert _sysex(m) == [IDENTITY_REPLY]


# --- 2. a long-lived input keeps its buffers queued ----------------------------------------------------------------

def test_a_long_lived_input_never_runs_out_of_sysex_buffers(fake):
    m = W.MidiIn(prefer="daw", nbuf=4)
    m.start()
    for i in range(30):                          # a watchdog's probes: far more replies than buffers
        reply = IDENTITY_REPLY[:12] + bytes([i]) + IDENTITY_REPLY[13:]
        assert fake.send_sysex(reply, wait=1.0), f"reply {i} found no queued buffer: the input ran dry"
    assert fake.wait_queued(4, timeout=1.0), "every buffer is back in the queue"
    m.close()
    assert len(_sysex(m)) == 30 and fake.dropped == 0
    assert fake.violations == [], "no WinMM call from inside the callback (MidiInProc deadlock rule)"


def test_buffers_are_requeued_off_the_callback_thread(fake):
    m = W.MidiIn(prefer="daw", nbuf=2)
    m.start()
    for _ in range(6):
        assert fake.send_sysex(IDENTITY_REPLY, wait=1.0)
    m.close()
    adds = [n for n in fake.names() if n == "midiInAddBuffer"]
    assert len(adds) >= 2 + 6 - 2, "the buffers handed back were queued again"
    assert fake.violations == []


def test_a_subclass_that_replaces_the_callback_still_gets_its_buffers_back(fake):
    class Pushing(W.MidiIn):                     # the shape of vj.LiveIn: keeps no events, ignores SysEx
        def _cb(self, h, msg, inst, p1, p2):
            pass

    m = Pushing(prefer="daw", nbuf=2)
    m.start()
    for _ in range(5):
        assert fake.send_sysex(IDENTITY_REPLY, wait=1.0)
    m.close()
    assert fake.dropped == 0 and fake.violations == []


def test_buffers_handed_back_by_close_are_not_queued_again(fake):
    m = W.MidiIn(prefer="daw", nbuf=3)
    m.start()
    m.close()
    assert fake.queued() == 0
    assert fake.violations == [] and fake.refused_unprepares == []
    assert not fake.in_open


def test_start_waits_before_a_probe_may_go(fake):
    m = W.MidiIn(prefer="daw", nbuf=2)
    m.start()
    returned = time.perf_counter()
    m.close()
    assert returned - fake.started_at >= 0.019, "replies stamped before the start settles are dropped (MIDI #1263)"


# --- 3. send_sysex reports what happened and never frees a buffer the driver owns ------------------------------------

def test_a_send_records_every_result_code(fake):
    out = W.MidiOut(prefer="daw")
    out.send_sysex(LED)
    rec = out.sends[-1]
    assert (rec["prepare"], rec["send"], rec["unprepare"], rec["done"]) == (0, 0, 0, True)
    assert rec["n"] == len(LED) and rec["wait_s"] >= 0
    assert fake.long_msgs[-1][1] == LED
    out.close()


def test_a_done_flag_timeout_is_reported_and_the_buffer_is_kept(fake):
    fake.out_done_on_send = False                # the driver takes the buffer and does not hand it back
    out = W.MidiOut(prefer="daw", done_timeout=0.05)
    with pytest.raises(RuntimeError, match="has not handed the buffer back"):
        out.send_sysex(LED)
    assert fake.refused_unprepares == [], "the header the driver still owns was let go"
    assert out.sends[-1]["done"] is False and out.parked == 1, "its header and buffer stay alive"
    fake.finish_output()                         # the driver lets go later
    fake.out_done_on_send = True
    out.send_sysex(LED)                          # the parked header is reclaimed on the next send
    assert len(fake.out_unprepared) == 2 and out.parked == 0
    out.close()
    assert fake.refused_unprepares == [] and not fake.out_open


def test_a_header_still_owned_at_close_is_reclaimed_after_the_reset(fake):
    fake.out_done_on_send = False
    out = W.MidiOut(prefer="daw", done_timeout=0.02)
    with pytest.raises(RuntimeError):
        out.send_sysex(LED)
    out.close()                                  # midiOutReset hands it back; then it may be unprepared
    assert fake.refused_unprepares == [] and not fake.out_open and len(fake.out_unprepared) == 1


def _kept(entry) -> bool:
    return any(e is entry for e in W._KEPT_ALIVE)


def test_a_header_the_driver_owns_outlives_a_midiout_dropped_without_close(fake):
    # vj.run did exactly this: a failed daw_connect send, then `led_out = None` with no close()
    fake.out_done_on_send = False
    led_out = W.MidiOut(prefer="daw", done_timeout=0.02)
    with pytest.raises(W.SysexTimeout):
        led_out.send_sysex(LED)
    alive = weakref.ref(led_out._parked[0][0])   # no strong reference from the test itself
    led_out = None
    fake.out_pending.clear()                     # the real driver holds only a raw pointer, never a Python reference
    gc.collect()
    assert alive() is not None, "the header the driver still owns was freed with the dropped MidiOut"
    assert any(e[0] is alive() for e in W._KEPT_ALIVE if isinstance(e, tuple) and e), "kept at module level"


def test_a_header_whose_unprepare_failed_outlives_a_dropped_midiout(fake):
    out = W.MidiOut(prefer="daw")
    fake.rc["midiOutUnprepareHeader"] = F.MMSYSERR_INVALPARAM
    with pytest.raises(W.WinMMError, match="midiOutUnprepareHeader"):
        out.send_sysex(LED)
    alive = weakref.ref(out._parked[0][0])
    out = None
    gc.collect()
    assert alive() is not None


def test_an_interrupt_while_waiting_for_the_done_flag_parks_the_header(fake, monkeypatch):
    class Interrupt(BaseException):              # Ctrl-C landing in the done-flag wait (a legacy driver still sending)
        pass

    def sleep(_s):
        raise Interrupt()

    fake.out_done_on_send = False
    out = W.MidiOut(prefer="daw", done_timeout=5.0)
    monkeypatch.setattr(W, "time", types.SimpleNamespace(perf_counter=time.perf_counter, sleep=sleep))
    with pytest.raises(Interrupt):
        out.send_sysex(LED)
    assert out.parked == 1 and _kept(out._parked[0]), "the queued header was kept, not dropped with the frame"
    assert fake.refused_unprepares == []


def test_a_parked_header_the_driver_hands_back_is_released(fake):
    fake.out_done_on_send = False
    out = W.MidiOut(prefer="daw", done_timeout=0.02)
    with pytest.raises(W.SysexTimeout):
        out.send_sysex(LED)
    entry = out._parked[0]
    fake.finish_output()
    fake.out_done_on_send = True
    out.send_sysex(LED)                          # reclaimed: unprepared, and no longer held for the process
    assert out.parked == 0 and not _kept(entry)
    out.close()


@pytest.mark.parametrize("fn, code", [("midiOutPrepareHeader", F.MMSYSERR_INVALPARAM),
                                      ("midiOutLongMsg", F.MMSYSERR_ERROR),
                                      ("midiOutUnprepareHeader", F.MMSYSERR_INVALPARAM)])
def test_every_failing_result_code_is_raised_with_its_name(fake, fn, code):
    out = W.MidiOut(prefer="daw")
    fake.rc[fn] = code
    with pytest.raises(RuntimeError, match=rf"{fn}.*MMRESULT={code}"):
        out.send_sysex(LED)
    del fake.rc[fn]
    out.close()


def test_a_send_that_failed_gives_its_header_back(fake):
    out = W.MidiOut(prefer="daw")
    fake.rc["midiOutLongMsg"] = F.MMSYSERR_ERROR   # Windows MIDI Services' send stall (MidiXProc, 1 s)
    with pytest.raises(RuntimeError):
        out.send_sysex(LED)
    assert out.sends[-1]["send"] == F.MMSYSERR_ERROR and out.sends[-1]["unprepare"] == 0
    del fake.rc["midiOutLongMsg"]
    out.close()


# --- 4. MidiIn.close: stop, then reset, then unprepare, then close; every code checked -------------------------------

def test_close_stops_before_it_resets(fake):
    m = W.MidiIn(prefer="daw", nbuf=3)
    m.start()
    m.close()
    names = fake.names()
    assert "midiInStop" in names, "close must stop the input before resetting it (NAudio PR #1478)"
    stop, reset = fake.first("midiInStop"), fake.first("midiInReset")
    unprep = names.index("midiInUnprepareHeader", reset)
    assert stop < reset < unprep < fake.first("midiInClose")


def test_close_reports_a_failing_result_code(fake):
    m = W.MidiIn(prefer="daw", nbuf=2)
    m.start()
    fake.rc["midiInClose"] = F.MIDIERR_STILLPLAYING   # the input-handle leak after a power cycle (MIDI #1157)
    with pytest.raises(RuntimeError, match="midiInClose.*65"):
        m.close()


def test_close_after_the_device_went_away_keeps_the_buffers_the_driver_holds(fake):
    m = W.MidiIn(prefer="daw", nbuf=2)
    m.start()
    for fn in ("midiInStop", "midiInReset"):
        fake.rc[fn] = F.MMSYSERR_NODRIVER          # a power cycle: the buffers never come back
    with pytest.raises(RuntimeError, match="midiInReset.*6"):
        m.close()
    assert fake.refused_unprepares == ["in", "in"], "the driver still owns both buffers"
    assert any(entry[0] == F.IN_HANDLE for entry in W._KEPT_ALIVE), "callback and buffers kept for the process"


def test_stop_does_not_raise_so_close_always_runs(fake):
    m = W.MidiIn(prefer="daw", nbuf=2)
    m.start()
    fake.rc["midiInStop"] = F.MMSYSERR_NODRIVER
    assert m.stop() == F.MMSYSERR_NODRIVER       # callers write `m.stop(); m.close()`
    del fake.rc["midiInStop"]
    m.close()
    assert not fake.in_open
