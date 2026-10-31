"""The `reachability` verb's pins: it must answer, and it must never touch the room while asking.

Vandor's 2026-10-30 wish (docs/WISHLIST.md) is the specification:

    "`reachability` verb: one command for gateway alive + its REAL log path (prod worktree), this
     seat's listener armed, who holds the consumer seat, last inbound/outbound to the operator,
     phone tunnel up. Today it took about 10 commands across two worktrees."

Three properties are load-bearing enough to pin, and each one is a mistake that was ALREADY made
once while building this verb:

  1. READ-ONLY. A stranded seat runs this. It must not consume a cursor, send mail, arm a listener
     or start a process -- running it twice must find the world unchanged. Pinned with a client
     that REFUSES anything except stream reads.
  2. UNKNOWN IS NOT DOWN. A probe that could not run (psutil missing, Redis unreachable) must say
     so. Collapsing it into "down" sends the reader hunting a fault that may not exist, which is
     the failure this whole verb is meant to end.
  3. MATCH THE ARGUMENT, NOT THE PROSE. The first draft of the gateway rung matched the marker as
     a substring of the whole command line and duly reported a gateway that did not exist: the
     seat's own task text contained the words "discord gateway". Both halves are pinned below.

Run: py tests/test_reachability.py   (or via pytest)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import reachability as R                                     # noqa: E402


# ------------------------------------------------------------------ 1. read-only by construction
class _ReadOnlyClient:
    """A Redis stand-in that ANSWERS stream reads and REFUSES every mutating call.

    This is the pin's whole mechanism: if `reachability` grows a cursor advance, an ack, a claim
    or an XADD tomorrow, the next run fails HERE with the method's name instead of quietly
    changing the state of a live bus.
    """

    def __init__(self, streams):
        self.streams = streams
        self.calls = []

    # -- allowed: reads only -------------------------------------------------
    def xrevrange(self, key, count=None, **_kw):
        self.calls.append(("xrevrange", key))
        return list(self.streams.get(key, []))[: (count or 10)]

    def get(self, key):
        self.calls.append(("get", key))
        return self.streams.get(key)

    def scan_iter(self, match=None, **_kw):
        self.calls.append(("scan_iter", match))
        return iter(())

    # -- forbidden: anything that could change the room ----------------------
    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        def _refuse(*_a, **_kw):
            raise AssertionError(
                f"reachability called {name!r} on the bus client -- this verb is READ-ONLY and "
                f"must never consume a cursor, send mail, claim a seat or arm a listener")
        return _refuse


def _fields(**kw):
    return [(k.encode(), str(v).encode()) for k, v in kw.items()]


def test_a_report_reads_streams_and_never_mutates(monkeypatch):
    """The operator-mail rung, against a refusing client: it must find both ends and mutate none."""
    from core.comm import packet_spec
    ns = os.environ.get("BIFROST_NAMESPACE", "bifrost")
    agent = "pin_agent"
    seat_stream = packet_spec.lane_stream_key(ns, "work", to=agent)
    op_stream = packet_spec.lane_stream_key(ns, "work", to="user")
    streams = {
        seat_stream: [("1700000000002-0", _fields(frm="user", to=agent, kind="chat",
                                                  ts="2026-10-30T10:00:00", content="ping"))],
        op_stream: [("1700000000003-0", _fields(frm=agent, to="user", kind="reply",
                                                ts="2026-10-30T10:01:00", content="pong"))],
    }
    client = _ReadOnlyClient(streams)
    monkeypatch.setattr(R, "_client", lambda: (client, None))
    out = R.operator_mail(agent)
    assert out["state"] == R.UP, out
    assert out["inbound"]["id"] == "1700000000002-0"
    assert out["inbound"]["frm"] == "user"
    assert out["outbound"]["id"] == "1700000000003-0"
    assert out["outbound"]["frm"] == agent
    # nothing but reads happened
    assert {c[0] for c in client.calls} <= {"xrevrange", "get", "scan_iter"}, client.calls


def test_a_full_report_survives_an_offline_bus(monkeypatch):
    """With no client at all, the mail rung is UNKNOWN with a reason -- and the screen still renders."""
    monkeypatch.setattr(R, "_client", lambda: (None, None))
    rep = R.report("pin_agent", "", phone=False)
    mail = rep["rungs"]["operator_mail"]
    assert mail["state"] == R.UNKNOWN, mail
    assert "offline" in mail["why"].lower() or "Redis" in mail["why"]
    text = R.render(rep)
    for rung in ("discord gateway", "wake listener", "consumer seat", "operator mail"):
        assert rung in text, f"the screen dropped the {rung!r} rung:\n{text}"
    assert "read-only" in text


# ------------------------------------------------------------------ 2. UNKNOWN is not DOWN
def test_no_psutil_is_unknown_not_down(monkeypatch):
    monkeypatch.setattr(R, "_psutil", lambda: None)
    g = R.gateway()
    assert g["state"] == R.UNKNOWN, g
    assert "NOT a claim" in g["why"], g["why"]
    p = R.phone_tunnel()
    assert p["state"] == R.UNKNOWN, p


def test_empty_but_readable_mail_is_down_not_up(monkeypatch):
    client = _ReadOnlyClient({})
    monkeypatch.setattr(R, "_client", lambda: (client, None))
    out = R.operator_mail("pin_agent")
    assert out["state"] == R.DOWN, out
    assert "no operator traffic" in out["why"], out


# ------------------------------------------------------------------ 3. match the argument
def test_gateway_marker_matches_the_script_argument_not_prose():
    """The regression pin for the false gateway this verb reported in its first draft."""
    markers = R.gateway_markers()
    assert markers, "the Local layer no longer names any gateway marker -- see local/reachability.json"
    prose = ["C:/Program Files/nodejs/node.exe", "bin.js", "--profile", "headless",
             "Boot as dsh_agent: reachability for the discord gateway and its log"]
    assert R._script_arg(prose, markers) == "", "prose in an argument is not a gateway"
    real = ["C:/Python311/pythonw.exe",
            "C:/worktrees/sunshine-discord-split/scripts/bifrost_runner_discord.py"]
    assert R._script_arg(real, markers).endswith("bifrost_runner_discord.py")


def test_ssh_forward_is_matched_by_executable_not_substring():
    """The regression pin for the phone rung's own first draft (it matched a task text too)."""
    assert R._is_ssh_client(["C:/Program Files/Git/usr/bin/ssh.exe", "-R", "8787:localhost:8787"])
    assert not R._is_ssh_client(["node.exe", "bin.js", "the phone tunnel's ssh -R process"])


def test_missing_local_data_is_unknown_never_a_default(monkeypatch):
    """The instance values live in the Local layer. Without them the rung must SAY so, not fall
    back to a plausible-looking address (a default phone host would be an invented fact)."""
    monkeypatch.setattr(R, "local_data", lambda: {})
    p = R.phone_tunnel()
    assert p["state"] == R.UNKNOWN, p
    assert "local/" in p["why"], p["why"]
    assert p["phone_answers"] is None, p
    g = R.gateway()
    assert g["state"] == R.UNKNOWN, g
    assert "local/" in g["why"], g["why"]


def test_the_gateway_log_is_resolved_from_the_gateways_own_worktree(tmp_path):
    """The wish's 'REAL log path (prod worktree)' clause: never this checkout's, never a guess."""
    os.makedirs(os.path.join(str(tmp_path), "state", "logs"))
    log = os.path.join(str(tmp_path), "state", "logs", "discord-gateway.log")
    with open(log, "w", encoding="utf-8") as fh:
        fh.write("[INFO] gateway up\n[INFO] shard resumed\n")
    got = R._gateway_log(str(tmp_path))
    assert got["state"] == R.UP, got
    assert got["path"] == log
    assert got["tail"].endswith("shard resumed")
    missing = R._gateway_log("")
    assert missing["state"] == R.UNKNOWN and "working directory" in missing["why"]


def main() -> int:
    import pytest
    return pytest.main([os.path.abspath(__file__), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
