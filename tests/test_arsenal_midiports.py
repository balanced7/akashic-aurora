"""What Windows can see of MIDI, for the piano page's Rescan hint: arsenal/midiports.py and GET /api/midi/ports.

Acceptance: docs/library/map/20261007_design-night-roadmap-2026-10-07_fa48f2.md (H1, A3), pre-registered before the
module was written. The parser and fail-soft tests run anywhere; the live snapshot test runs only on Windows and reads
the real WinMM list without opening any port.
"""
import json
import sys
import threading
import urllib.request

import pytest

from arsenal import midiports
from arsenal.serve import App, Server


SC_RUNNING = """
SERVICE_NAME: midisrv
        TYPE               : 10  WIN32_OWN_PROCESS
        STATE              : 4  RUNNING
                                (STOPPABLE, NOT_PAUSABLE, ACCEPTS_SHUTDOWN)
        WIN32_EXIT_CODE    : 0  (0x0)
"""
SC_STOPPED = SC_RUNNING.replace("4  RUNNING", "1  STOPPED")
SC_ABSENT = "[SC] EnumQueryServicesStatus:OpenService FAILED 1060:\n\nThe specified service does not exist as an installed service."


@pytest.mark.parametrize("text, state", [
    (SC_RUNNING, "running"),
    (SC_STOPPED, "stopped"),
    (SC_RUNNING.replace("4  RUNNING", "2  START_PENDING"), "start_pending"),
    (SC_ABSENT, "absent"),
    ("", "unknown"),
    ("something else entirely", "unknown"),
])
def test_parse_sc_state(text, state):
    assert midiports.parse_sc_state(text) == state


def test_snapshot_fails_soft_with_a_reason(monkeypatch):
    def boom(kind):
        raise OSError("winmm unavailable")
    monkeypatch.setattr(midiports, "_winmm_names", boom)
    monkeypatch.setattr(midiports.sys, "platform", "win32")
    snap = midiports.snapshot()
    assert snap["ok"] is False
    assert "winmm unavailable" in snap["reason"]
    json.dumps(snap)  # always serialisable


def test_snapshot_off_windows_says_so(monkeypatch):
    monkeypatch.setattr(midiports.sys, "platform", "linux")
    snap = midiports.snapshot()
    assert snap == {"ok": False, "reason": "not windows"}


@pytest.mark.skipif(sys.platform != "win32", reason="reads the real WinMM list")
def test_live_snapshot_shape():
    snap = midiports.snapshot()
    assert snap["ok"] is True, snap
    assert isinstance(snap["inputs"], list) and all(isinstance(n, str) for n in snap["inputs"])
    assert isinstance(snap["outputs"], list)
    assert snap["service"]["name"] == "midisrv"
    assert snap["service"]["state"] in {"running", "stopped", "start_pending", "stop_pending", "absent", "unknown"}


def test_route_serves_the_snapshot_as_json(tmp_path, monkeypatch):
    fake = {"ok": True, "inputs": ["KeyLab 88 mk3 MIDI"], "outputs": [], "service": {"name": "midisrv", "state": "running"}}
    monkeypatch.setattr(midiports, "snapshot", lambda: fake)
    app = App([str(tmp_path / "library")], takes_root=tmp_path / "takes", performance_root=tmp_path / "perf")
    srv = Server(0, app)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}/api/midi/ports"
        with urllib.request.urlopen(url, timeout=5) as r:
            assert r.status == 200
            assert r.headers.get_content_type() == "application/json"
            assert json.loads(r.read()) == fake
    finally:
        srv.shutdown()
        srv.server_close()
