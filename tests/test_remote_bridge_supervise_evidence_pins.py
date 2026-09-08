"""RED pins for defer [e935125f0e]: remote_bridge_supervise must SURFACE the child's death
evidence instead of discarding it, and the breaker message must point at a sink that
actually received that evidence.

THE LIVE INCIDENT (2026-08-26 12:05): the listener died three times in fifty seconds, the
breaker tripped correctly, the door stayed down -- and nothing the child printed survived.
ManagedChild parks the child's stdout in a 200-line ring and hands it to on_exit(code, tail),
but the supervisor never wired on_exit, so the ring died with the child. The breaker line
then sent the operator to state/logs/remote-bridge-listener.log, a file only peer_connect.py
writes (it hands the listener that file as stdout when IT launches the listener); under
supervision the child's stdout is ManagedChild's pipe and the file never receives a byte.

PORT-FREE: ManagedChild is replaced by a fake honouring the same public surface (on_exit
hook, tripped, pid, spawn(), poll()); door_open is stubbed shut; time.sleep is a no-op.
Safe to run in one pytest invocation with any other file.
"""
from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import scripts.remote_bridge_supervise as sup  # noqa: E402

SENTINEL = "evidence-of-death"

# A realistic ring: banner, a run of request lines, then the traceback -- with the sentinel on
# the LAST line. A "helpful" first-200-chars clip (the bifrost_daemon shape that destroyed the
# 2026-08-25 TIMEOUT receipts) would keep the banner and lose the cause.
TAIL = "\n".join(
    ["akashic remote-bridge listener on http://127.0.0.1:1/xfer  peer=serge-dsh"]
    + [f"[12:05:{10 + i:02d}] 100.86.106.36 POST /xfer 200 id=rb-{i:04d}" for i in range(24)]
    + ["Traceback (most recent call last):",
       "  File \"scripts/remote_bridge_listener.py\", line 340, in main",
       "    srv.serve_forever()",
       f"OSError: [WinError 10048] {SENTINEL}: only one usage of each socket address"]
)


class FakeChild:
    """ManagedChild's public surface, minus the process. poll() reports one crash per tick and
    delivers the ring tail EXACTLY the way ManagedChild.poll does -- through on_exit, and only
    if somebody wired it -- then trips the breaker on the third crash."""

    exit_code = 1

    def __init__(self, args, **kw):
        self.args = list(args)
        self.on_exit = None
        self.tripped = False
        self.pid = 4242
        self.polls = 0

    def spawn(self):
        return None

    def poll(self):
        self.polls += 1
        if self.on_exit:
            self.on_exit(self.exit_code, TAIL)
        if self.polls >= 3:
            self.tripped = True
        return self.exit_code


class HandoverChild(FakeChild):
    """N1: exit 0 is a deliberate handover -- never respawned, never trips. The supervisor
    would idle forever, so the operator's Ctrl-C ends the watch on the next tick."""

    exit_code = 0

    def poll(self):
        if self.polls >= 1:
            raise KeyboardInterrupt
        return super().poll()


def _run(monkeypatch, capsys, tmp_path, extra_argv=(), child_cls=FakeChild):
    monkeypatch.setattr(sup, "REPO", tmp_path)          # the default sink resolves under tmp
    monkeypatch.setattr(sup, "ManagedChild", child_cls)
    monkeypatch.setattr(sup, "door_open", lambda *a, **k: False)
    monkeypatch.setattr(sup.time, "sleep", lambda s: None)
    argv = ["--host", "127.0.0.1", "--port", "1", "--poll-sec", "0", *extra_argv]
    rc = sup.main(argv)
    return rc, capsys.readouterr().out


def test_child_death_evidence_reaches_the_supervisor_stdout_on_exit(monkeypatch, capsys, tmp_path):
    rc, out = _run(monkeypatch, capsys, tmp_path)
    assert rc == 1
    assert SENTINEL in out, "the child's last output was discarded on exit (on_exit never wired)"


def test_breaker_trip_prints_the_evidence_adjacent_to_the_trip_line(monkeypatch, capsys, tmp_path):
    rc, out = _run(monkeypatch, capsys, tmp_path)
    assert "BREAKER TRIPPED" in out
    after_trip = out[out.index("BREAKER TRIPPED"):]
    assert SENTINEL in after_trip, "the trip line and the death evidence must be adjacent"


def test_the_file_the_breaker_names_actually_receives_the_evidence(monkeypatch, capsys, tmp_path):
    rc, out = _run(monkeypatch, capsys, tmp_path)
    after_trip = out[out.index("BREAKER TRIPPED"):]
    assert "remote-bridge-listener.log" in after_trip
    log = tmp_path / "state" / "logs" / "remote-bridge-listener.log"
    assert log.exists(), "the breaker message names a file the supervised child never writes"
    assert SENTINEL in log.read_text(encoding="utf-8")


def test_child_log_flag_redirects_the_tee_and_the_breaker_names_it(monkeypatch, capsys, tmp_path):
    sink = tmp_path / "door.log"
    rc, out = _run(monkeypatch, capsys, tmp_path, extra_argv=["--child-log", str(sink)])
    assert rc == 1
    assert sink.exists(), "--child-log sink never written"
    assert SENTINEL in sink.read_text(encoding="utf-8")
    assert str(sink) in out[out.index("BREAKER TRIPPED"):], \
        "the breaker must name the sink that actually received the evidence"


def test_a_deliberate_exit_0_also_surfaces_the_tail(monkeypatch, capsys, tmp_path):
    rc, out = _run(monkeypatch, capsys, tmp_path, child_cls=HandoverChild)
    assert rc == 0                                   # Ctrl-C path: supervisor stops cleanly
    assert "code=0" in out, "an exit-0 handover must still be announced with its code"
    assert SENTINEL in out, "what the child said on its way out is owed on EVERY exit"
