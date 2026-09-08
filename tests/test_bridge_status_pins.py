"""Pins: remote-bridge status and remediation, as a module the UI merely renders.

Daniil, 2026-08-25: "make the bifrost ui be remote aware and to allow for remediation."

TWO HALVES WITH DIFFERENT RULES, which is why they are pinned together and implemented apart:

  STATUS IS A READ and must never lie by omission. Every field says what it measured and
  when. A dashboard that shows a peer as "up" because a config row exists is the
  green-receipt-over-a-broken-path failure with better typography — and this fleet spent
  2h44m on that exact shape, so a status panel is the last place to repeat it.

  REMEDIATION IS AN ACT and must never be a side effect of looking. Every action is explicit,
  reports what it actually did, and refuses rather than guesses. The dangerous one is
  draining parked peer mail onto the live bus: that spends the parked-not-bussed defence, so
  it carries the Discord guest-tier posture (attributed, authority:none, no control kinds)
  and it must not be reachable by rendering a page.

THE RULE THAT SHAPES BOTH: a panel that can act is a door, and a door needs the same
discipline as the gate behind it. Nothing here trusts a name in a payload, and nothing here
does work because a page was loaded.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import bridge_status as BS  # noqa: E402
from core.comm import remote_relay as RR   # noqa: E402


@pytest.fixture(autouse=True)
def _world(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_INBOX", str(tmp_path / "inbox.jsonl"))
    monkeypatch.setenv("AKASHIC_REMOTE_BRIDGE_OUTBOX", str(tmp_path / "outbox.jsonl"))
    monkeypatch.delenv("AKASHIC_REMOTE_BRIDGE_PEER_URL", raising=False)
    sec = tmp_path / "secrets"
    sec.mkdir()
    (sec / "a_in.key").write_bytes(b"peer-a-inbound-key-aaaaaaaaaaaa")
    (sec / "a_out.key").write_bytes(b"peer-a-outbound-key-bbbbbbbbbb")
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(sec))
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"peers": [
        {"name": "peer-a", "url": "https://a.invalid/xfer",
         "inbound_secret_file": "a_in.key", "outbound_secret_file": "a_out.key"},
        {"name": "peer-unkeyed", "url": "", "inbound_secret_file": "missing.key"},
    ]}), encoding="utf-8")
    monkeypatch.setattr(RR, "CONFIG_FILE", cfg)
    RR._reset_cache()
    yield
    RR._reset_cache()


# ------------------------------------------------------------------ STATUS: a read that tells truth
def test_status_lists_every_configured_peer():
    st = BS.status(probe=False)
    names = [p["name"] for p in st["peers"]]
    assert "peer-a" in names and "peer-unkeyed" in names


def test_an_unkeyed_peer_is_reported_inert_not_broken():
    """Absent-is-not-broken, on the dashboard. A peer with no key yet is a CONFIGURATION
    STATE; painting it as a failure trains the reader to ignore red."""
    st = BS.status(probe=False)
    row = next(p for p in st["peers"] if p["name"] == "peer-unkeyed")
    assert row["keyed"] is False
    assert row["state"] == "inert", f"expected inert, got {row['state']!r}"
    row_a = next(p for p in st["peers"] if p["name"] == "peer-a")
    assert row_a["keyed"] is True


def test_reachability_is_absent_rather_than_guessed_when_not_probed():
    """The panel must never imply a measurement it did not take. `probe=False` is the cheap
    render; it may not report a peer as up."""
    st = BS.status(probe=False)
    for p in st["peers"]:
        assert p.get("reachable") is None, "unprobed reachability was reported as a verdict"
    assert st["probed"] is False


def test_status_reports_queue_depths_from_disk():
    RR.enqueue({"frm": "v", "kind": "chat", "content": "x", "id": "q1"}, peer="peer-a")
    st = BS.status(probe=False)
    assert st["outbox_pending"] == 1
    row = next(p for p in st["peers"] if p["name"] == "peer-a")
    assert row["queued_for_peer"] == 1, "per-peer depth is what tells you WHO is stuck"


def test_status_never_raises_on_a_broken_world(monkeypatch):
    """A dashboard that crashes on a malformed config takes the operator's eyes out at exactly
    the moment something is wrong."""
    monkeypatch.setattr(RR, "CONFIG_FILE", Path("does-not-exist.json"))
    RR._reset_cache()
    st = BS.status(probe=False)
    assert isinstance(st, dict) and "peers" in st


def test_status_carries_its_own_timestamp():
    """A rendered number with no age is a claim about now that may be about an hour ago."""
    st = BS.status(probe=False)
    assert abs(int(st["measured_at"]) - int(time.time())) < 5


# ------------------------------------------------------------------ REMEDIATION: acts, never side effects
def test_actions_are_enumerated_and_named():
    acts = BS.actions()
    names = {a["id"] for a in acts}
    assert {"tick_outbox", "drain_parked", "restart_listener"} <= names
    for a in acts:
        assert a.get("danger") in ("low", "medium", "high"), f"{a['id']} has no danger rating"
        assert a.get("what"), f"{a['id']} does not say what it does"


def test_an_unknown_action_is_refused():
    out = BS.act("rm_minus_rf", confirm=True)
    assert not out.ok and "unknown" in (out.why or "").lower()


def test_dangerous_actions_require_explicit_confirmation():
    """Rendering a page must never perform work. Anything that changes the world needs a
    caller who said so — a UI button posts confirm=true, a page load cannot."""
    for aid in ("drain_parked", "restart_listener"):
        out = BS.act(aid, confirm=False)
        assert not out.ok, f"{aid} ran without confirmation"
        assert "confirm" in (out.why or "").lower()


def test_drain_parked_carries_the_guest_tier_posture():
    """Draining spends the parked-not-bussed defence, so what lands must carry no power:
    attributed in the body, authority:none, provenance from the verified route."""
    posted = []
    RR._reset_cache()
    rows = RR._read_jsonl(RR.inbox_path())
    rows.append({"id": "p1", "frm": "remote:peer-a", "claimed_frm": "somebody",
                 "kind": "chat", "content": "hello", "sent_at": 0, "admitted_at": 0})
    RR._write_jsonl(RR.inbox_path(), rows)

    out = BS.act("drain_parked", confirm=True, bus_send=lambda **kw: posted.append(kw) or "id-1")
    assert out.ok, out.why
    assert posted, "nothing was drained"
    meta = posted[0].get("meta") or {}
    assert meta.get("authority") == "none", "drained remote mail carried authority"
    assert meta.get("route") == "remote:peer-a"
    assert "[remote" in str(posted[0].get("content")), "not attributed in the body"


def test_act_never_raises(monkeypatch):
    """NEVER RAISES holds for every action id -- and the restart path runs through the seams.
    This test used to reach the real discovery + taskkill, which is how it became the weapon
    in [5d2f0963e1]. A real subprocess from act() under test is a regression, not a detail."""
    spawned = []

    def recorder(argv, *_a, **_kw):
        spawned.append([str(x) for x in argv])

        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", recorder)
    for aid in ("tick_outbox", "drain_parked", "restart_listener", "", None, 123):
        try:
            BS.act(aid, confirm=True, bus_send=lambda **kw: None,
                   process_table=lambda: [], kill=lambda pid: True)
        except Exception as e:                                    # noqa: BLE001
            pytest.fail(f"act({aid!r}) raised {type(e).__name__}: {e}")
    assert spawned == [], f"act() reached the host from a test: {spawned}"


# ------------------------------------------------------------------ RESTART: a weapon must know its own face
# [5d2f0963e1] `py -m pytest tests/test_bridge_status_pins.py tests/test_remote_bridge_listener_pins.py`
# killed the ENTIRE shell with zero output. Not a signal path: _restart_listener discovered the
# listener with `CommandLine -like '*remote_bridge_listener*'` and taskkill /F-ed every match --
# and once the pytest command line names the listener's TEST file, the matches are pytest's own
# python.exe, the py launcher and the host shell carrying that command string. Alone, this file's
# command line lacks the substring, so nothing self-selected; the listener pins never call act().
# Together, test_act_never_raises was a weapon aimed at its own host. Three guarantees follow:
#   (a) discovery selects the listener PROCESS -- an interpreter whose PROGRAM is the listener
#       script -- never a command line that merely mentions the name (a test path, a shell, an
#       editor, a grep);
#   (b) self-protection is independent of the predicate: the caller's own pid, its ancestor chain
#       and anything running pytest are refused even when they LOOK like the listener, and the
#       refusal is reported by pid, not swallowed;
#   (c) discovery and kill are injectable seams (`process_table=`, `kill=`) exactly like
#       act(..., bus_send=), so no test in this house has to touch the host to pin the action.
def _rows(*specs):
    """(pid, ppid, exe name, command line) tuples -> the process-table rows the seam takes."""
    return [{"pid": pid, "ppid": ppid, "name": name, "cmdline": cmd}
            for pid, ppid, name, cmd in specs]


def _fake_run_speaking_both_dialects(rows, calls):
    """A stand-in for subprocess.run that answers the discovery query with `rows` and records
    every argv, so a pin can assert on the WEAPON (what taskkill was aimed at) rather than on a
    parser. It speaks both dialects on purpose -- the whitespace pid list the original query
    produced and the ConvertTo-Json table the fixed query asks for -- so the pin is red by
    mechanism at the defect and stays a mechanism pin after it. Nothing here reaches the host."""
    def fake_run(argv, *_a, **_kw):
        argv = [str(x) for x in argv]
        calls.append(argv)

        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        if argv and "powershell" in argv[0].lower():
            if "ConvertTo-Json" in " ".join(argv):
                R.stdout = json.dumps([{"ProcessId": r["pid"], "ParentProcessId": r["ppid"],
                                        "Name": r["name"], "CommandLine": r["cmdline"]}
                                       for r in rows])
            else:
                R.stdout = "\n".join(str(r["pid"]) for r in rows) + "\n"
        return R()
    return fake_run


def test_restart_listener_never_targets_its_own_process_tree(monkeypatch):
    """(b) at the weapon. The discovery answer contains the caller's own pid and its parent --
    exactly what the host returned when the pytest command line named the listener's test file.
    No taskkill may be aimed at either, whatever the query said, and the refusal is reported."""
    me, parent = os.getpid(), os.getppid()
    shape = r"C:\Python311\python.exe E:\AI-Setup\scripts\remote_bridge_listener.py --port 8791"
    rows = _rows((me, parent, "python.exe", shape), (parent, 1, "py.exe", shape))
    calls = []
    monkeypatch.setattr(subprocess, "run", _fake_run_speaking_both_dialects(rows, calls))
    out = BS._restart_listener()
    aimed = [c[2] for c in calls if len(c) > 2 and c[0].lower().startswith("taskkill")]
    assert str(me) not in aimed and str(parent) not in aimed, (
        f"taskkill was aimed at the caller's own process tree: {aimed} "
        f"(me={me}, parent={parent}); outcome={out}")
    assert out.ok, f"a refusal is a report, not an exception: {out.why}"
    assert "refused" in (out.why or "").lower(), f"self-refusal was swallowed: {out.why!r}"


def test_restart_listener_selects_the_listener_process_not_any_mention_of_its_name():
    """(a) the predicate, against a table shaped like the host that died. Only an interpreter
    whose PROGRAM is the listener script is the door. The pytest run naming the listener's test
    file, the shell carrying that command, the query's own powershell, an editor with the file
    open and a grep all MENTION the name; none of them may be stopped."""
    table = _rows(
        (101, 1, "py.exe", "py -m pytest tests/test_bridge_status_pins.py "
                           "tests/test_remote_bridge_listener_pins.py"),
        (102, 101, "python.exe", r"C:\Python311\python.exe -m pytest tests/test_bridge_status_pins.py "
                                 r"tests/test_remote_bridge_listener_pins.py"),
        (103, 1, "bash.exe", 'bash.exe -c "py -m pytest '
                             'tests/test_remote_bridge_listener_pins.py"'),
        (104, 102, "powershell.exe", "powershell -NoProfile -Command Get-CimInstance Win32_Process | "
                                     "Where-Object { $_.CommandLine -like '*remote_bridge_listener*' }"),
        (105, 1, "Code.exe", r'"C:\Users\x\AppData\Local\Programs\Microsoft VS Code\Code.exe" '
                             r"E:\AI-Setup\scripts\remote_bridge_listener.py"),
        (106, 103, "grep.exe", "grep -rn remote_bridge_listener scripts tests"),
        (107, 1, "python.exe", r"C:\Python311\python.exe E:\AI-Setup\scripts\remote_bridge_listener.py "
                               r"--host 127.0.0.1 --port 8791 --peer serge"),
        (108, 1, "py.exe", "py scripts/remote_bridge_listener.py --port 9000"),
        (109, 1, "python.exe", r"C:\Python311\python.exe E:\AI-Setup\scripts\remote_bridge_listener.py "
                               r"--port 0 --peer pytest-probe"),
    )
    killed = []
    out = BS._restart_listener(process_table=lambda: table,
                               kill=lambda pid: killed.append(pid) or True)
    assert sorted(killed) == [107, 108], (
        f"stopped {sorted(killed)}; only 107 (the supervisor's launch form) and 108 (the "
        f"documented `py scripts/...` form) are the door")
    assert out.ok, out.why
    why = out.why or ""
    assert "109" in why and "pytest" in why.lower(), (
        f"a listener-shaped process running under pytest must be refused BY PID in the report: "
        f"{why!r}")


def test_restart_listener_refuses_its_ancestors_even_when_they_look_like_the_listener():
    """(b) at the table. The caller, its parent and its grandparent all wear the listener's
    shape -- a door that asks the panel to bounce 'the listener' must not be handed its own
    head. They are refused by lineage, the unrelated listener is stopped, and every refused
    pid is in the report."""
    me, parent, grand = os.getpid(), os.getppid(), 424242
    shape = r"C:\Python311\python.exe E:\AI-Setup\scripts\remote_bridge_listener.py --port 8791"
    table = _rows((me, parent, "python.exe", shape), (parent, grand, "py.exe", shape),
                  (grand, 1, "python.exe", shape), (207, 1, "python.exe", shape + " --peer other"))
    killed = []
    out = BS._restart_listener(process_table=lambda: table,
                               kill=lambda pid: killed.append(pid) or True)
    assert killed == [207], (
        f"stopped {killed}; expected only the unrelated listener 207 "
        f"(me={me}, parent={parent}, grand={grand})")
    assert out.ok, out.why
    for pid in (me, parent, grand):
        assert str(pid) in (out.why or ""), f"refused pid {pid} missing from the report: {out.why!r}"


def test_restart_listener_reports_a_kill_that_failed_as_not_stopped():
    """Actions report what they ACTUALLY did. A taskkill that came back non-zero is not a stop,
    and 'stopped 2' over one dead and one living process is the green receipt this module's
    docstring exists to forbid."""
    shape = r"C:\Python311\python.exe E:\AI-Setup\scripts\remote_bridge_listener.py"
    table = _rows((301, 1, "python.exe", shape + " --port 8791"),
                  (302, 1, "python.exe", shape + " --port 8792"))
    out = BS._restart_listener(process_table=lambda: table, kill=lambda pid: pid == 301)
    assert out.ok, out.why
    why = out.why or ""
    assert "stopped [301]" in why and "failed to stop [302]" in why, why
