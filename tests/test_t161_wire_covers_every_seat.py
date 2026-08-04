"""PRE-REGISTERED ACCEPTANCE (T161) -- wire capture reaches every seat, not just deepseek.

T156 shipped the journal wired into ONE seat (deepseek). kimi, gemini and sol have made model
calls ever since with no wire record at all, so `system_fingerprint` drift -- the silent
model-swap detector -- was observable for a quarter of the fleet. A tournament that compares a
champion against a challenger without it is silently invalid, which is why this is a Season 1
dependency and not a nicety.

This was correctly REFUSED while the write path was a known lock convoy (T157): propagating a
measured defect to three more runners multiplies it. T157 removed the convoy and T160 made
records attributable, so the extension is now safe and worth having.

  E1  the shared factory returns an INSTRUMENTED client -- kimi and gemini reach it through
      core.comm.runner_lib, so one seam covers both
  E2  INSTRUMENTING MUST NOT DROP THE ANTI-WEDGE TIMEOUT. runner_lib exists to turn a hung
      stream into a caught timeout; passing a custom http_client is exactly how that guarantee
      gets silently lost, because the SDK then takes its timeout from the client it was handed
      and ignores the one the factory would have set. A seat that is instrumented but wedge-prone
      is a worse trade than one that is blind.
  E3  it can be turned OFF per call -- the seam, so a seat can opt out without a revert
  E4  and globally, via AKASHIC_WIRE=0
  E5  STRUCTURAL: every seat chat module actually builds an instrumented client. Enumerated from
      the directory, the same shape as T160's A3 -- the defect being prevented is "a whole class
      of seat was forgotten", so the pin has to be able to notice a NEW seat.
  E6  a broken recorder NEVER prevents a client from being built. Telemetry must not be able to
      stop a runner from starting; the blindness it cures is far cheaper than a seat that will
      not boot.

Run: py -m pytest tests/test_t161_wire_covers_every_seat.py -q
"""
import glob
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

pytest.importorskip("httpx")
pytest.importorskip("openai")

SEATS = ("deepseek", "kimi", "gemini", "sol")


def _lib():
    import importlib
    from core.comm import runner_lib
    return importlib.reload(runner_lib)


def _is_recording(client) -> bool:
    """True if the OpenAI client's transport is our journaling transport."""
    http = getattr(client, "_client", None)
    if http is None:
        return False
    t = getattr(http, "_transport", None)
    return type(t).__name__ == "_RecordingTransport"


# --------------------------------------------------------------------------- E1

def test_e1_the_shared_factory_instruments_by_default():
    lib = _lib()
    c = lib.make_openai_compat_client("k", "https://example.invalid/v1")
    assert _is_recording(c), (
        "the shared factory returns an uninstrumented client, so kimi and gemini -- which both "
        "reach the wire only through this seam -- stay blind")


# --------------------------------------------------------------------------- E2

def test_e2_instrumenting_does_not_drop_the_anti_wedge_timeout():
    """The regression this slice is most likely to cause, so it is pinned before the code.

    runner_lib's whole reason to exist is that a hung streaming read becomes a caught
    httpx.ReadTimeout instead of an infinite wedge. Hand the SDK a custom http_client and the
    timeout travels with THAT client -- forget to set it there and the hardening is gone while
    every test still passes.
    """
    lib = _lib()
    c = lib.make_openai_compat_client("k", "https://example.invalid/v1",
                                      connect_timeout=3.0, read_timeout=7.0)
    http = getattr(c, "_client", None)
    assert http is not None
    to = http.timeout
    assert to.read == pytest.approx(7.0), (
        f"read timeout is {to.read!r}, not 7.0 -- instrumenting silently discarded the anti-wedge "
        f"hardening, and a wedged seat is worse than a blind one")
    assert to.connect == pytest.approx(3.0), f"connect timeout is {to.connect!r}, not 3.0"


# --------------------------------------------------------------------------- E3 / E4

def test_e3_instrumentation_can_be_declined_per_call():
    lib = _lib()
    c = lib.make_openai_compat_client("k", "https://example.invalid/v1", record_wire=False)
    assert not _is_recording(c)
    assert c._client.timeout.read == pytest.approx(120.0), (
        "the uninstrumented path lost its default timeout")


def test_e4_a_global_off_switch_exists(monkeypatch):
    monkeypatch.setenv("AKASHIC_WIRE", "0")
    lib = _lib()
    c = lib.make_openai_compat_client("k", "https://example.invalid/v1")
    assert not _is_recording(c), "AKASHIC_WIRE=0 did not disable capture"


# --------------------------------------------------------------------------- E5

def test_e5_every_seat_builds_an_instrumented_client():
    """Structural, over the seat FAMILY -- a new seat is covered the day it lands."""
    missing = []
    for seat in SEATS:
        path = os.path.join(ROOT, "scripts", f"{seat}_chat.py")
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8", errors="replace").read()
        m = re.search(r"def make_client\(.*?\n(?=\n\ndef |\n\n# |\Z)", src, re.S)
        body = m.group(0) if m else src
        # either it goes through the shared factory (instrumented by default) or it wires the
        # recorder itself -- both are honest; building a bare OpenAI() is not
        if not re.search(r"make_openai_compat_client|recording_http_client|wire_client", body):
            missing.append(f"{seat}_chat.py")
    assert not missing, (
        f"{len(missing)} seat(s) build a model client with no wire capture, so their traffic is "
        f"invisible -- including system_fingerprint, the silent model-swap detector: {missing}")


# --------------------------------------------------------------------------- E6

def test_e6_a_broken_recorder_never_blocks_a_launch(monkeypatch):
    lib = _lib()

    def boom(*a, **k):
        raise RuntimeError("recorder is broken")

    import scripts.wire_journal as WJ
    monkeypatch.setattr(WJ, "recording_http_client", boom)

    c = lib.make_openai_compat_client("k", "https://example.invalid/v1")
    assert c is not None, "a broken recorder prevented a client from being built"
    assert not _is_recording(c)
    assert c._client.timeout.read == pytest.approx(120.0), (
        "the fallback path lost the anti-wedge timeout as well -- the failure mode compounded")
