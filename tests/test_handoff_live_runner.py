"""The handoff-to-a-live-runner pins: a written record is not a read receipt.

THE WISH (docs/WISHLIST.md, 2026-10-30, phase 3 of the modular-core detangle):

    "`handoff --to <seat with a live runner>`: warn, or also deliver live. A boot-only handoff to
     Heimdall's never-rebooting runner sat unseen for hours."

What makes this worth a pin rather than a printed hint: `handoff` ALREADY succeeded in that
incident. The signal was recorded, the door said OK, and the briefing sat on a plane the target
only walks at boot -- a runner holds its lock and works the lane without ever rebooting. So the
defect is not a failed write, it is a SUCCESSFUL write whose reader was never going to come. The
fix therefore cannot be "warn harder": it must (1) name the mismatch at the door, (2) leave the
durable record alone, and (3) offer a path that the runner can actually see this shift.

Three pins:
  1. a runner-served seat produces the warning AND a paste-ready live path, while the durable
     handoff is still recorded;
  2. `--deliver-live` sends the bus copy as well, and a REFUSED send is reported (a silent
     swallow would recreate the same silence one plane over);
  3. a seat with NO runner gets neither the warning nor a live send -- a door that cries wolf on
     every handoff teaches its reader to skip the line.

Run: py tests/test_handoff_live_runner.py   (or via pytest)
"""
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import agent_cli                                                             # noqa: E402
from core.comm import reachability as R                                     # noqa: E402


def _args(**kw):
    base = dict(agent_id="pin_sender", to="pin_target", task="verify the thing",
                note="", blocker="", list=False, json=False, deliver_live=False)
    base.update(kw)
    return types.SimpleNamespace(**base)


class _Stub:
    """The door's side effects, captured instead of performed."""

    def __init__(self, runner_state=R.DOWN, send_ok=True):
        self.runner_state = runner_state
        self.send_ok = send_ok
        self.sent = []


def _wire(monkeypatch, stub):
    """Record the handoff; stub the runner probe and the bus send. Nothing real is written."""
    class _Emitter:
        def __init__(self, *_a, **_kw):
            pass

        def emit_handoff_to_target_agent(self, *_a, **_kw):
            return None

    monkeypatch.setattr("core.signals.coordinator_api.SignalEmitter", _Emitter)
    monkeypatch.setattr(agent_cli, "_warn_unmirrored", lambda: None)

    def _live_runner(agent):
        if stub.runner_state == R.UP:
            return {"state": R.UP, "holder": {"token": "runner:pin", "ts": "2026-10-30T09:00:00"},
                    "runtimes": {"pin": {"pid": 1}}}
        if stub.runner_state == R.UNKNOWN:
            return {"state": R.UNKNOWN, "why": "runner lock unreadable: OSError"}
        return {"state": R.DOWN, "holder": None, "runtimes": {}}

    monkeypatch.setattr(R, "live_runner", _live_runner)

    class _Bus:
        def send(self, to, kind, content=None, **kw):
            stub.sent.append({"to": to, "kind": kind, "content": content, "meta": kw.get("meta")})
            return "pin-msg-1" if stub.send_ok else None

    monkeypatch.setattr("core.comm.bus.get_bus", lambda agent=None, *a, **k: _Bus())


def test_a_runner_served_seat_is_warned_and_the_record_is_still_written(monkeypatch, capsys):
    stub = _Stub(runner_state=R.UP)
    _wire(monkeypatch, stub)
    rc = agent_cli.cmd_handoff(_args())
    out = capsys.readouterr().out
    assert rc == 0
    assert "[OK] handoff pin_sender -> pin_target" in out, out
    assert "WARNING" in out and "NEXT BOOT" in out.upper(), out
    assert "live path" in out and "--kind inform" in out, out
    assert not stub.sent, "without --deliver-live nothing is pushed onto the bus"


def test_deliver_live_sends_the_copy_and_names_the_id(monkeypatch, capsys):
    stub = _Stub(runner_state=R.UP)
    _wire(monkeypatch, stub)
    rc = agent_cli.cmd_handoff(_args(deliver_live=True, note="context line"))
    out = capsys.readouterr().out
    assert rc == 0
    assert stub.sent, "--deliver-live must actually send"
    sent = stub.sent[0]
    assert sent["to"] == "pin_target" and sent["kind"] == "inform"
    assert "LIVE HANDOFF" in sent["content"] and "context line" in sent["content"]
    assert sent["meta"]["source"] == "handoff-live"
    assert "pin-msg-1" in out, out


def test_a_refused_live_send_is_reported_not_swallowed(monkeypatch, capsys):
    stub = _Stub(runner_state=R.UP, send_ok=False)
    _wire(monkeypatch, stub)
    rc = agent_cli.cmd_handoff(_args(deliver_live=True))
    out = capsys.readouterr().out
    assert rc == 0, "the durable handoff still landed -- a failed live copy is not a door failure"
    assert "NOT sent" in out, out


def test_a_seat_without_a_runner_gets_no_warning_and_no_live_send(monkeypatch, capsys):
    stub = _Stub(runner_state=R.DOWN)
    _wire(monkeypatch, stub)
    rc = agent_cli.cmd_handoff(_args(deliver_live=False))
    out = capsys.readouterr().out
    assert rc == 0
    assert "WARNING" not in out, out
    assert "live path" not in out, out
    assert not stub.sent


def test_an_unmeasurable_runner_reads_unknown_never_no_runner(monkeypatch, capsys):
    """The house rule at the door: could-not-look must not be reported as nothing-there."""
    stub = _Stub(runner_state=R.UNKNOWN)
    _wire(monkeypatch, stub)
    rc = agent_cli.cmd_handoff(_args(json=True))
    out = capsys.readouterr().out
    assert rc == 0
    assert '"state": "UNKNOWN"' in out, out
    assert "unmeasured, not 'no runner'" in out, out


def main() -> int:
    import pytest
    return pytest.main([os.path.abspath(__file__), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
