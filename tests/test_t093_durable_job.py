"""T093 pre-registered kill drills for controller-independent durable jobs.

This file intentionally lands before implementation (M3).  The battery is black-box: every
completion check comes from a fresh ``run_job.py status`` process reading an atomic receipt, never
from the supervised child's stdout pipe.  Durations stay small; the production deadline is a dial.

Governing build spec:
research/reviewed/t093-crash-path-reconciliation-2026-07-17.md sections 7-9.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import pytest

from scripts import run_job
from scripts import ship as ship_module


ROOT = Path(__file__).resolve().parents[1]
RUN_JOB = ROOT / "scripts" / "run_job.py"
SHIP = ROOT / "scripts" / "ship.py"
TERMINAL = {
    "succeeded", "failed", "cancelled", "deadline_exceeded", "child_killed",
    "launch_failed", "outcome_unknown", "supervision_lost",
}


def _job_id(prefix: str) -> str:
    return f"t093-{prefix}-{uuid.uuid4().hex[:10]}"


def _json_tail(text: str) -> dict:
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError(f"no JSON receipt in output: {text!r}")


def _cli(*args: str, timeout: float = 8.0) -> dict:
    proc = subprocess.run(
        [sys.executable, str(RUN_JOB), *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    assert proc.returncode == 0, (
        f"run_job rc={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    return _json_tail(proc.stdout)


def _launch(state_dir: Path, job_id: str, command: list[str], *,
            max_runtime: float = 4.0, grace: float = 0.2,
            heartbeat: float = 0.05, broker: str = "auto") -> dict:
    return _cli(
        "launch", "--state-dir", str(state_dir), "--job-id", job_id,
        "--max-runtime", str(max_runtime), "--grace-seconds", str(grace),
        "--heartbeat-seconds", str(heartbeat), "--broker", broker,
        "--", *command,
    )


def _status(state_dir: Path, job_id: str, *, stale_after: float = 0.3) -> dict:
    return _cli(
        "status", job_id, "--state-dir", str(state_dir),
        "--stale-after", str(stale_after),
    )


def _wait_terminal(state_dir: Path, job_id: str, timeout: float = 6.0) -> dict:
    deadline = time.monotonic() + timeout
    last = {}
    while time.monotonic() < deadline:
        last = _status(state_dir, job_id)
        if last.get("state") in TERMINAL:
            return last
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not terminate in {timeout}s; last={last}")


def _wait_running(state_dir: Path, job_id: str, timeout: float = 4.0) -> dict:
    deadline = time.monotonic() + timeout
    last = {}
    while time.monotonic() < deadline:
        last = _status(state_dir, job_id)
        if last.get("state") == "running" and last.get("child_pid"):
            return last
        if last.get("state") in TERMINAL:
            break
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} never reached running; last={last}")


def _force_tree(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True, text=True, timeout=5,
        )
    else:
        try:
            os.killpg(pid, 9)
        except ProcessLookupError:
            pass


def _seed_spec(state_dir: Path, job_id: str, command: list[str], *,
               max_runtime: float = 3.0, grace: float = 0.2,
               heartbeat: float = 0.05, broker: str = "detached",
               startup_expired: bool = False) -> dict[str, Path]:
    """Seed the immutable pre-broker receipt to reproduce a controller launch-gap death."""
    paths = run_job._paths(state_dir, job_id)
    paths["root"].mkdir(parents=True, exist_ok=True)
    now_mono = time.monotonic()
    now_epoch = time.time()
    startup_delta = -1.0 if startup_expired else 5.0
    run_job._atomic_json(paths["spec"], {
        "schema": 1,
        "job_id": job_id,
        "command": [str(x) for x in command],
        "cwd": str(ROOT.resolve()),
        "max_runtime": float(max_runtime),
        "grace_seconds": float(grace),
        "heartbeat_seconds": float(heartbeat),
        "broker_requested": broker,
        "created_at": "preregistered-drill",
        "created_epoch": now_epoch - 20,
        "created_monotonic": now_mono - 20,
        "startup_deadline_epoch": now_epoch + startup_delta,
        "startup_deadline_monotonic": now_mono + startup_delta,
        "environment": {},
        "log_path": str(paths["log"]),
        "cancel_path": str(paths["cancel"]),
    })
    return paths


def test_launch_is_immediate_and_fresh_status_recovers_result(tmp_path):
    job_id = _job_id("fresh")
    marker = tmp_path / "fresh.marker"
    code = (
        "import pathlib,sys,time; time.sleep(.35); "
        "pathlib.Path(sys.argv[1]).write_text('complete', encoding='utf-8')"
    )
    started = time.monotonic()
    launch = _launch(tmp_path, job_id, [sys.executable, "-c", code, str(marker)])
    assert time.monotonic() - started < 2.0, "launch must not wait for job completion"
    assert launch["job_id"] == job_id
    assert launch["state"] in {"launching", "running"}
    assert Path(launch["receipt_path"]).exists(), "launch receipt precedes model/tool return"

    final = _wait_terminal(tmp_path, job_id)
    assert final["state"] == "succeeded" and final["exit_code"] == 0
    assert marker.read_text(encoding="utf-8") == "complete"


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 invisible WMI broker")
def test_wmi_broker_launches_guards_without_visible_consoles(monkeypatch):
    captured = {}

    class BrokerResult:
        returncode = 0
        stderr = ""
        stdout = json.dumps([
            {"ReturnValue": 0, "ProcessId": 101},
            {"ReturnValue": 0, "ProcessId": 102},
        ])

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return BrokerResult()

    monkeypatch.setattr(run_job.subprocess, "run", fake_run)
    pids = run_job._wmi_create_pair([
        [sys.executable, "-c", "raise SystemExit(0)"],
        [sys.executable, "-c", "raise SystemExit(0)"],
    ])

    encoded = captured["argv"][captured["argv"].index("-EncodedCommand") + 1]
    broker_script = __import__("base64").b64decode(encoded).decode("utf-16le")
    compact = "".join(broker_script.split())
    assert pids == [101, 102]
    assert captured["kwargs"]["creationflags"] & subprocess.CREATE_NO_WINDOW
    assert "New-CimInstance-ClassNameWin32_ProcessStartup" in compact
    assert "-ClientOnly" in compact
    assert "ShowWindow=[uint16]0" in compact
    assert "CreateFlags=[uint32]8" in compact  # DETACHED_PROCESS
    assert "ProcessStartupInformation=$startup" in compact


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 controller-tree acceptance")
def test_wmi_broker_survives_recursive_controller_tree_kill(tmp_path):
    """The historical app-server restart bar: controller /T death must not own the supervisor."""
    job_id = _job_id("tree")
    ready = tmp_path / "controller-ready.json"
    marker = tmp_path / "tree.marker"
    child_code = (
        "import pathlib,sys,time; time.sleep(.8); "
        "pathlib.Path(sys.argv[1]).write_text('survived', encoding='utf-8')"
    )
    controller_code = r"""
import pathlib, subprocess, sys, time
run_job, state_dir, job_id, ready, marker, child_code = sys.argv[1:]
cmd = [sys.executable, run_job, 'launch', '--state-dir', state_dir, '--job-id', job_id,
       '--max-runtime', '4', '--grace-seconds', '.2', '--heartbeat-seconds', '.05',
       '--broker', 'wmi', '--', sys.executable, '-c', child_code, marker]
p = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=8)
pathlib.Path(ready).write_text(p.stdout if p.returncode == 0 else
    '{"launch_error": %r}' % (p.stderr,), encoding='utf-8')
time.sleep(30)
"""
    controller = subprocess.Popen(
        [sys.executable, "-c", controller_code, str(RUN_JOB), str(tmp_path), job_id,
         str(ready), str(marker), child_code],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready.exists(), "controller never produced the durable launch receipt"
        launch = _json_tail(ready.read_text(encoding="utf-8"))
        assert launch["survival_bar"] == "recursive-controller-tree"
        _force_tree(controller.pid)
        controller.wait(timeout=5)

        final = _wait_terminal(tmp_path, job_id)
        assert final["state"] == "succeeded"
        assert marker.read_text(encoding="utf-8") == "survived"
    finally:
        if controller.poll() is None:
            _force_tree(controller.pid)


def test_independent_deadline_resolves_wedged_child(tmp_path):
    job_id = _job_id("deadline")
    child_pid = tmp_path / "child.pid"
    code = (
        "import os,pathlib,sys,time; "
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid()), encoding='utf-8'); "
        "print('entered wedge', flush=True); time.sleep(60)"
    )
    _launch(tmp_path, job_id, [sys.executable, "-u", "-c", code, str(child_pid)],
            max_runtime=0.45, grace=0.15)
    final = _wait_terminal(tmp_path, job_id, timeout=5)
    assert final["state"] == "deadline_exceeded"
    assert final["reported_by"] == "watchdog"
    assert final["forced"] is True
    assert final["deadline_enforced"] is True
    assert final["child_alive"] is False
    assert "entered wedge" in Path(final["log_path"]).read_text(encoding="utf-8")


def test_watchdog_never_claims_enforcement_when_exact_kill_fails(tmp_path, monkeypatch):
    """An identity match is necessary but not sufficient: the tree must actually die."""
    job_id = _job_id("kill-refused")
    paths = run_job._paths(tmp_path, job_id)
    paths["root"].mkdir(parents=True)
    child_identity = run_job._process_info(os.getpid())[1]
    assert child_identity, "the kill drill requires a reusable process-creation identity"
    now = time.monotonic()
    run_job._atomic_json(paths["spec"], {
        "schema": 1,
        "job_id": job_id,
        "heartbeat_seconds": 0.01,
        "grace_seconds": 0.0,
        "startup_deadline_monotonic": now + 5,
    })
    run_job._atomic_json(paths["status"], {
        "schema": 1,
        "job_id": job_id,
        "state": "running",
        "supervisor_pid": 2_000_000_000,
        "heartbeat_epoch": 0.0,
        "child_pid": os.getpid(),
        "child_identity": child_identity,
        "deadline_monotonic": now + 60,
    })
    run_job._atomic_json(paths["cancel"], {
        "schema": 1,
        "job_id": job_id,
        "reason": "kill-refusal-drill",
        "requested_monotonic": now,
    })
    monkeypatch.setattr(run_job, "_kill_tree", lambda *_: {
        "killed": False,
        "identity_match": True,
        "detail": "injected taskkill refusal",
    })

    rc = run_job._watchdog(job_id, tmp_path)
    receipt = run_job._read_json(paths["watchdog"])
    assert rc != 0
    assert receipt["state"] == "supervision_lost"
    assert receipt["deadline_enforced"] is False
    assert receipt["child_alive"] is True
    assert receipt["kill_receipt"]["killed"] is False


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 direct-enforcer acceptance")
def test_exact_tree_kill_does_not_depend_on_taskkill_subprocess(monkeypatch):
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    identity = run_job._process_info(proc.pid)[1]
    assert identity
    real_run = run_job.subprocess.run

    def hung_taskkill(args, *pargs, **kwargs):
        if args and Path(str(args[0])).name.lower() == "taskkill":
            raise subprocess.TimeoutExpired(args, kwargs.get("timeout", 0))
        return real_run(args, *pargs, **kwargs)

    monkeypatch.setattr(run_job.subprocess, "run", hung_taskkill)
    try:
        receipt = run_job._kill_tree(proc.pid, identity)
        proc.wait(timeout=3)
        assert receipt["killed"] is True
        assert receipt["identity_match"] is True
        assert proc.poll() is not None
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=3)


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 complete Job Object membership receipt")
def test_job_membership_reader_retries_successful_partial_buffer(monkeypatch):
    class FakeQuery:
        def __init__(self):
            self.calls = 0
            self.argtypes = None
            self.restype = None

        def __call__(self, _handle, _info_class, buffer, _size, _returned):
            self.calls += 1
            value = buffer._obj
            value.NumberOfAssignedProcesses = 20
            listed = 16 if self.calls == 1 else 20
            value.NumberOfProcessIdsInList = listed
            for index in range(listed):
                value.ProcessIdList[index] = 10_000 + index
            return 1

    query = FakeQuery()

    class FakeKernel32:
        QueryInformationJobObject = query

    monkeypatch.setattr(run_job.ctypes, "WinDLL", lambda *_args, **_kwargs: FakeKernel32())
    members = run_job._win_job_members(object())
    assert query.calls == 2, "successful-but-partial membership must grow and retry"
    assert members == list(range(10_000, 10_020))


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 exact-handle assignment identity")
def test_job_assignment_validates_identity_on_the_assigned_handle(monkeypatch):
    class FakeCall:
        def __init__(self, result):
            self.result = result
            self.calls = []
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    open_process = FakeCall(0xCAFE)
    assign = FakeCall(1)
    close = FakeCall(1)

    class FakeKernel32:
        OpenProcess = open_process
        AssignProcessToJobObject = assign
        CloseHandle = close

    monkeypatch.setattr(run_job.ctypes, "WinDLL", lambda *_args, **_kwargs: FakeKernel32())
    monkeypatch.setattr(run_job, "_matches_identity", lambda *_args: True)
    monkeypatch.setattr(run_job, "_win_process_in_job", lambda *_args: False)
    monkeypatch.setattr(
        run_job,
        "_win_process_info_from_handle",
        lambda _handle: (True, "replacement-process"),
        raising=False,
    )

    receipt = run_job._win_assign_exact_to_job(object(), 4242, "expected-process")

    assert receipt["assigned"] is False
    assert receipt["identity_match"] is False
    assert receipt["reason"] == "pid_creation_identity_mismatch"
    assert assign.calls == [], "a replacement process handle must never be assigned"


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 exact-handle termination identity")
def test_termination_validates_identity_on_the_terminated_handle(monkeypatch):
    class FakeCall:
        def __init__(self, result):
            self.result = result
            self.calls = []
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            self.calls.append(args)
            return self.result

    open_process = FakeCall(0xBEEF)
    terminate = FakeCall(1)
    wait = FakeCall(0)
    close = FakeCall(1)

    class FakeKernel32:
        OpenProcess = open_process
        TerminateProcess = terminate
        WaitForSingleObject = wait
        CloseHandle = close

    monkeypatch.setattr(run_job.ctypes, "WinDLL", lambda *_args, **_kwargs: FakeKernel32())
    monkeypatch.setattr(run_job, "_win_process_info", lambda _pid: (True, "expected-process"))
    monkeypatch.setattr(
        run_job,
        "_win_process_info_from_handle",
        lambda _handle: (True, "replacement-process"),
        raising=False,
    )

    receipt = run_job._win_terminate_exact(4242, "expected-process")

    assert receipt["terminated"] is False
    assert receipt["identity_match"] is False
    assert receipt["reason"] == "pid_creation_identity_mismatch"
    assert terminate.calls == [], "a replacement process handle must never be terminated"


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 terminal Job Object quiescence")
def test_terminal_receipt_waits_for_retained_workload_quiescence(tmp_path):
    job_id = _job_id("terminal-quiescence")
    root_ready = tmp_path / "root.ready"
    release_root = tmp_path / "root.release"
    grandchild_pid_path = tmp_path / "grandchild.pid"
    terminal_seen = tmp_path / "terminal.seen"
    effect = tmp_path / "post-terminal.effect"
    grandchild_code = (
        "import pathlib,sys,time; "
        "terminal=pathlib.Path(sys.argv[1]); effect=pathlib.Path(sys.argv[2]); "
        "deadline=time.monotonic()+2.5; "
        "\nwhile not terminal.exists() and time.monotonic()<deadline: time.sleep(.005)"
        "\nif terminal.exists(): effect.write_text('post-terminal',encoding='utf-8')"
    )
    root_code = (
        "import pathlib,subprocess,sys,time; "
        "p=subprocess.Popen([sys.executable,'-c',sys.argv[5],sys.argv[3],sys.argv[4]],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
        "pathlib.Path(sys.argv[2]).write_text(str(p.pid),encoding='utf-8'); "
        "pathlib.Path(sys.argv[1]).write_text('ready',encoding='utf-8'); "
        "deadline=time.monotonic()+8; release=pathlib.Path(sys.argv[6]); "
        "\nwhile not release.exists() and time.monotonic()<deadline: time.sleep(.005)"
    )
    _launch(
        tmp_path,
        job_id,
        [
            sys.executable, "-c", root_code, str(root_ready), str(grandchild_pid_path),
            str(terminal_seen), str(effect), grandchild_code, str(release_root),
        ],
        max_runtime=8,
        grace=0.1,
        heartbeat=1.0,
    )
    _wait_running(tmp_path, job_id)
    deadline = time.monotonic() + 4
    while (
        (not root_ready.exists() or not grandchild_pid_path.exists())
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)
    assert root_ready.exists() and grandchild_pid_path.exists()
    grandchild_pid = int(grandchild_pid_path.read_text(encoding="utf-8"))
    grandchild_identity = run_job._process_info(grandchild_pid)[1]
    assert grandchild_identity

    try:
        watchdog_path = run_job._paths(tmp_path, job_id)["watchdog"]
        first_sequence = None
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            watchdog = run_job._read_json(watchdog_path)
            if watchdog.get("phase") == "watching_worker":
                sequence = int(watchdog.get("sequence", 0))
                if first_sequence is None:
                    first_sequence = sequence
                elif sequence > first_sequence:
                    break
            time.sleep(0.01)
        else:
            pytest.fail("watchdog never exposed a fresh watching_worker sleep boundary")

        release_root.write_text("release", encoding="utf-8")
        final = _wait_terminal(tmp_path, job_id, timeout=6)
        alive_at_terminal = run_job._matches_identity(grandchild_pid, grandchild_identity)
        terminal_seen.write_text("observed", encoding="utf-8")
        effect_deadline = time.monotonic() + 0.5
        while not effect.exists() and time.monotonic() < effect_deadline:
            time.sleep(0.01)

        assert alive_at_terminal is False, (
            f"terminal {final.get('state')} was exposed with retained workload still alive"
        )
        assert effect.exists() is False, "a retained descendant mutated state after terminal"
        assert final.get("job_quiescent") is True
        assert final.get("workload_member_pids_remaining") == []
    finally:
        if run_job._matches_identity(grandchild_pid, grandchild_identity):
            run_job._win_terminate_exact(grandchild_pid, grandchild_identity)


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 honest deadline attribution")
def test_natural_guard_loss_does_not_claim_deadline_enforcement(tmp_path):
    job_id = _job_id("natural-guard-loss")
    _launch(
        tmp_path,
        job_id,
        [sys.executable, "-c", "import time; time.sleep(.35)"],
        max_runtime=30,
        grace=0.1,
        heartbeat=0.05,
    )
    running = _wait_running(tmp_path, job_id)
    supervisor_pid = int(running["supervisor_pid"])
    supervisor_identity = str(running["supervisor_identity"])
    killed = run_job._win_terminate_exact(supervisor_pid, supervisor_identity)
    assert killed["terminated"] is True

    final = _wait_terminal(tmp_path, job_id, timeout=4)
    assert final["state"] == "outcome_unknown"
    assert final["termination_cause"] == "worker_gone_after_supervisor_loss"
    assert final.get("forced") in {None, False}
    assert not final.get("kill_receipt")
    assert final["deadline_enforced"] is False


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 dead-root tree evidence")
def test_dead_root_with_live_descendant_is_not_credited_as_killed(tmp_path):
    child_pid_path = tmp_path / "descendant.pid"
    child_code = "import time; time.sleep(60)"
    root_code = (
        "import pathlib,subprocess,sys; "
        "p=subprocess.Popen([sys.executable,'-c',sys.argv[2]],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,"
        "creationflags=subprocess.CREATE_NEW_PROCESS_GROUP); "
        "pathlib.Path(sys.argv[1]).write_text(str(p.pid),encoding='utf-8')"
    )
    root = subprocess.Popen(
        [sys.executable, "-c", root_code, str(child_pid_path), child_code],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )
    root_identity = run_job._process_info(root.pid)[1]
    assert root_identity
    deadline = time.monotonic() + 3
    while not child_pid_path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert child_pid_path.exists()
    descendant_pid = int(child_pid_path.read_text(encoding="utf-8"))
    descendant_identity = run_job._process_info(descendant_pid)[1]
    assert descendant_identity
    root.wait(timeout=3)
    try:
        receipt = run_job._kill_tree(root.pid, root_identity)
        assert receipt["killed"] is False
        assert receipt.get("force_applied") is False
        assert descendant_pid in receipt.get("remaining_pids", [])
    finally:
        run_job._win_terminate_exact(descendant_pid, descendant_identity)


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 retained-job-membership acceptance")
def test_deadline_kills_grandchild_after_intermediate_parent_exits(tmp_path):
    """Current PPID snapshots must not substitute for retained OS job membership."""
    job_id = _job_id("broken-ancestry")
    grandchild_pid_path = tmp_path / "grandchild.pid"
    grandchild_code = "import time; time.sleep(60)"
    intermediate_code = (
        "import pathlib,subprocess,sys; "
        "p=subprocess.Popen([sys.executable,'-c',sys.argv[2]],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,"
        "creationflags=subprocess.CREATE_NEW_PROCESS_GROUP); "
        "pathlib.Path(sys.argv[1]).write_text(str(p.pid),encoding='utf-8')"
    )
    root_code = (
        "import subprocess,sys,time; "
        "subprocess.run([sys.executable,'-c',sys.argv[2],sys.argv[1],sys.argv[3]],check=True); "
        "time.sleep(60)"
    )
    _launch(
        tmp_path,
        job_id,
        [
            sys.executable, "-c", root_code, str(grandchild_pid_path),
            intermediate_code, grandchild_code,
        ],
        max_runtime=1.0,
        grace=0.1,
        heartbeat=0.03,
    )

    deadline = time.monotonic() + 3
    while not grandchild_pid_path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert grandchild_pid_path.exists(), "intermediate never published the grandchild PID"
    grandchild_pid = int(grandchild_pid_path.read_text(encoding="utf-8"))
    grandchild_identity = run_job._process_info(grandchild_pid)[1]
    assert grandchild_identity, "kill drill requires the grandchild's creation identity"

    try:
        final = _wait_terminal(tmp_path, job_id, timeout=6)
        assert final["state"] == "deadline_exceeded"
        assert final.get("deadline_enforced") is True
        assert not run_job._matches_identity(grandchild_pid, grandchild_identity), (
            "a disconnected grandchild survived an allegedly exact job deadline"
        )
    finally:
        if run_job._matches_identity(grandchild_pid, grandchild_identity):
            run_job._win_terminate_exact(grandchild_pid, grandchild_identity)


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 retained workload deadline")
def test_deadline_kills_retained_descendant_after_root_exits(tmp_path):
    job_id = _job_id("dead-root-retained-workload")
    grandchild_pid_path = tmp_path / "grandchild.pid"
    grandchild_code = "import time; time.sleep(60)"
    root_code = (
        "import pathlib,subprocess,sys; "
        "p=subprocess.Popen([sys.executable,'-c',sys.argv[2]],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
        "pathlib.Path(sys.argv[1]).write_text(str(p.pid),encoding='utf-8')"
    )
    _launch(
        tmp_path,
        job_id,
        [sys.executable, "-c", root_code, str(grandchild_pid_path), grandchild_code],
        max_runtime=0.8,
        grace=0.1,
        heartbeat=0.03,
    )

    deadline = time.monotonic() + 3
    while not grandchild_pid_path.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    assert grandchild_pid_path.exists()
    grandchild_pid = int(grandchild_pid_path.read_text(encoding="utf-8"))
    grandchild_identity = run_job._process_info(grandchild_pid)[1]
    assert grandchild_identity

    try:
        final = _wait_terminal(tmp_path, job_id, timeout=4)
        assert final["state"] == "deadline_exceeded"
        assert final["deadline_enforced"] is True
        assert final["kill_receipt"]["remaining_pids"] == []
        assert not run_job._matches_identity(grandchild_pid, grandchild_identity)
    finally:
        if run_job._matches_identity(grandchild_pid, grandchild_identity):
            run_job._win_terminate_exact(grandchild_pid, grandchild_identity)


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 independent Job Object ownership")
def test_watchdog_death_does_not_collapse_healthy_owned_job(tmp_path):
    job_id = _job_id("watchdog-handle-loss")
    marker = tmp_path / "completed.marker"
    code = (
        "import pathlib,sys,time; time.sleep(.35); "
        "pathlib.Path(sys.argv[1]).write_text('complete',encoding='utf-8')"
    )
    _launch(
        tmp_path, job_id, [sys.executable, "-c", code, str(marker)],
        max_runtime=4.0, grace=0.1, heartbeat=0.03,
    )
    running = _wait_running(tmp_path, job_id)
    watchdog_pid = int(running["watchdog_pid"])
    watchdog_identity = run_job._process_info(watchdog_pid)[1]
    assert watchdog_identity
    killed = run_job._win_terminate_exact(watchdog_pid, watchdog_identity)
    assert killed["terminated"] is True

    final = _wait_terminal(tmp_path, job_id, timeout=5)
    assert final["state"] == "succeeded"
    assert marker.read_text(encoding="utf-8") == "complete"


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 publish fail-close exclusion")
def test_both_guard_deaths_cannot_kill_protected_publish(tmp_path):
    job_id = _job_id("publish-guard-loss")
    entered = tmp_path / "publish-entered.marker"
    completed = tmp_path / "publish-completed.marker"
    code = r"""
import os, pathlib, time
from scripts import run_job
fence = pathlib.Path(os.environ['AKASHIC_JOB_PUBLISH_FENCE'])
outcome = pathlib.Path(os.environ['AKASHIC_JOB_OUTCOME_FILE'])
entered = pathlib.Path(os.environ['AKASHIC_T093_ENTERED_MARKER'])
completed = pathlib.Path(os.environ['AKASHIC_T093_COMPLETED_MARKER'])
with run_job.protect_owned_job_during_publish():
    with run_job.publish_fence(fence, blocking=True):
        run_job.write_child_outcome(outcome, {
            'state': 'publish_active', 'primary_effect': 'unknown',
            'publish_may_have_occurred': True,
        })
        entered.write_text('inside', encoding='utf-8')
        time.sleep(.45)
        run_job.write_child_outcome(outcome, {
            'state': 'succeeded', 'primary_effect': 'pushed',
            'commit_sha': 'guard-loss-proof', 'branch': 'test',
        })
        completed.write_text('pushed', encoding='utf-8')
"""
    old_entered = os.environ.get("AKASHIC_T093_ENTERED_MARKER")
    old_completed = os.environ.get("AKASHIC_T093_COMPLETED_MARKER")
    os.environ["AKASHIC_T093_ENTERED_MARKER"] = str(entered)
    os.environ["AKASHIC_T093_COMPLETED_MARKER"] = str(completed)
    running = {}
    identities: list[tuple[int, str]] = []
    try:
        _launch(
            tmp_path, job_id, [sys.executable, "-u", "-c", code],
            max_runtime=5.0, grace=0.1, heartbeat=0.03,
        )
        running = _wait_running(tmp_path, job_id)
        deadline = time.monotonic() + 3
        while not entered.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert entered.exists(), "worker never entered the protected publish fence"
        for key in ("watchdog_pid", "supervisor_pid"):
            pid = int(running[key])
            identity = run_job._process_info(pid)[1]
            assert identity
            identities.append((pid, identity))
        for pid, identity in identities:
            result = run_job._win_terminate_exact(pid, identity)
            assert result["terminated"] is True
        deadline = time.monotonic() + 3
        while not completed.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert completed.exists(), "OS fail-close interrupted the protected publish"
        final = _wait_terminal(tmp_path, job_id, timeout=3)
        assert final["state"] == "succeeded"
        assert final["primary_effect"] == "pushed"
        assert final["commit_sha"] == "guard-loss-proof"
    finally:
        if old_entered is None:
            os.environ.pop("AKASHIC_T093_ENTERED_MARKER", None)
        else:
            os.environ["AKASHIC_T093_ENTERED_MARKER"] = old_entered
        if old_completed is None:
            os.environ.pop("AKASHIC_T093_COMPLETED_MARKER", None)
        else:
            os.environ["AKASHIC_T093_COMPLETED_MARKER"] = old_completed
        for pid, identity in identities:
            if run_job._matches_identity(pid, identity):
                run_job._win_terminate_exact(pid, identity)
        child_pid = running.get("child_pid")
        child_identity = running.get("child_identity")
        if child_pid and run_job._matches_identity(child_pid, child_identity):
            run_job._win_terminate_exact(int(child_pid), str(child_identity))


def test_already_dead_force_race_never_becomes_cancelled(tmp_path, monkeypatch):
    job_id = _job_id("already-dead-race")
    paths = _seed_spec(
        tmp_path, job_id, [sys.executable, "-c", "raise SystemExit(0)"],
        grace=0.0, heartbeat=0.01,
    )
    child_identity = run_job._process_info(os.getpid())[1]
    assert child_identity
    run_job._atomic_json(paths["status"], {
        "schema": 1,
        "job_id": job_id,
        "state": "running",
        "supervisor_pid": 2_000_000_000,
        "heartbeat_epoch": 0.0,
        "child_pid": os.getpid(),
        "child_identity": child_identity,
        "deadline_monotonic": time.monotonic() + 60,
    })
    run_job._atomic_json(paths["cancel"], {
        "schema": 1,
        "job_id": job_id,
        "reason": "already-dead-race",
        "requested_monotonic": time.monotonic(),
    })
    monkeypatch.setattr(run_job, "_kill_tree", lambda *_: {
        "killed": True,
        "already_dead": True,
        "identity_match": True,
        "force_applied": False,
    })
    rc = run_job._watchdog(job_id, tmp_path)
    receipt = run_job._read_json(paths["watchdog"])
    assert rc != 0
    assert receipt["state"] == "outcome_unknown"
    assert receipt["forced"] is False
    assert receipt["state"] not in {"cancelled", "deadline_exceeded"}


def test_post_publish_optional_failure_preserves_primary_success(tmp_path, monkeypatch):
    outcome = tmp_path / "outcome.json"
    fence = tmp_path / "publish.fence"
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    monkeypatch.setenv("AKASHIC_JOB_OUTCOME_FILE", str(outcome))
    monkeypatch.setenv("AKASHIC_JOB_PUBLISH_FENCE", str(fence))
    monkeypatch.delenv("AKASHIC_JOB_CANCEL_FILE", raising=False)
    monkeypatch.setattr(
        ship_module,
        "build_plan",
        lambda _args: [("commit + push", ["fake-publish"]), ("snapshot", ["fake-snapshot"])],
    )
    monkeypatch.setattr(ship_module, "_git_value", lambda *_: "receipt-value")
    monkeypatch.setattr(ship_module, "_run", lambda label, _cmd: label == "commit + push")

    rc = ship_module.main(["test publish", "scripts/ship.py", "--_durable-child"])
    receipt = json.loads(outcome.read_text(encoding="utf-8"))
    assert rc == 0
    assert receipt["state"] == "succeeded"
    assert receipt["primary_effect"] == "pushed"
    assert receipt["post_publish_incomplete"] is True
    assert receipt["post_publish_failure"] == "snapshot"


def test_watchdog_startup_expiry_clears_deadline_enforcement(tmp_path):
    job_id = _job_id("startup-expiry")
    paths = _seed_spec(
        tmp_path, job_id, [sys.executable, "-c", "raise SystemExit(0)"],
        startup_expired=True,
    )
    rc = run_job._watchdog(job_id, tmp_path)
    receipt = run_job._read_json(paths["watchdog"])
    assert rc != 0
    assert receipt["state"] == "launch_failed"
    assert receipt["deadline_enforced"] is False


def test_slow_work_below_hard_deadline_is_not_killed(tmp_path):
    job_id = _job_id("slow")
    code = (
        "import time; "
        "[(print(f'tick {i}', flush=True), time.sleep(.15)) for i in range(5)]"
    )
    _launch(tmp_path, job_id, [sys.executable, "-u", "-c", code], max_runtime=3)
    final = _wait_terminal(tmp_path, job_id)
    assert final["state"] == "succeeded"
    assert final["forced"] is False
    assert "tick 4" in Path(final["log_path"]).read_text(encoding="utf-8")


def test_cancel_is_quiesce_first_for_cooperating_child(tmp_path):
    job_id = _job_id("cancel")
    marker = tmp_path / "quiesced.marker"
    code = r"""
import os, pathlib, sys, time
cancel = pathlib.Path(os.environ['AKASHIC_JOB_CANCEL_FILE'])
marker = pathlib.Path(sys.argv[1])
while not cancel.exists():
    time.sleep(.03)
marker.write_text('quiesced', encoding='utf-8')
raise SystemExit(130)
"""
    _launch(tmp_path, job_id, [sys.executable, "-u", "-c", code, str(marker)],
            max_runtime=5, grace=1.0)
    _wait_running(tmp_path, job_id)
    cancel = _cli("cancel", job_id, "--state-dir", str(tmp_path), "--reason", "test")
    assert cancel["cancel_requested"] is True
    final = _wait_terminal(tmp_path, job_id)
    assert final["state"] == "cancelled"
    assert final["forced"] is False
    assert final["quiesce"] == "cooperative"
    assert marker.read_text(encoding="utf-8") == "quiesced"


def test_atomic_receipt_never_tears_during_heartbeats(tmp_path):
    job_id = _job_id("atomic")
    code = "import time; time.sleep(.6)"
    launch = _launch(tmp_path, job_id, [sys.executable, "-c", code],
                     max_runtime=3, heartbeat=0.02)
    receipt = Path(launch["receipt_path"])
    deadline = time.monotonic() + 2
    reads = 0
    while time.monotonic() < deadline:
        parsed = json.loads(receipt.read_text(encoding="utf-8"))
        reads += 1
        if parsed.get("state") in TERMINAL:
            break
        time.sleep(0.005)
    assert reads >= 10
    assert _wait_terminal(tmp_path, job_id)["state"] == "succeeded"


def test_forced_child_death_is_reported_without_inventing_attribution(tmp_path):
    job_id = _job_id("external-kill")
    _launch(tmp_path, job_id, [sys.executable, "-c", "import time; time.sleep(60)"],
            max_runtime=10)
    running = _wait_running(tmp_path, job_id)
    _force_tree(int(running["child_pid"]))
    final = _wait_terminal(tmp_path, job_id)
    assert final["state"] == "failed"
    assert final["reported_by"] == "supervisor", "a killed child cannot self-report"
    assert final["termination_cause"] == "unattributed_nonzero_exit"
    assert final["exit_code"] != 0


def test_stale_supervisor_is_loud_but_watchdog_still_enforces_deadline(tmp_path):
    job_id = _job_id("supervisor-loss")
    _launch(tmp_path, job_id, [sys.executable, "-c", "import time; time.sleep(60)"],
            max_runtime=0.75, heartbeat=0.03)
    running = _wait_running(tmp_path, job_id)
    assert running.get("watchdog_pid"), running
    supervisor_pid = int(running["supervisor_pid"])
    supervisor_identity = str(running["supervisor_identity"])
    killed = run_job._win_terminate_exact(supervisor_pid, supervisor_identity)
    assert killed["terminated"] is True
    final = _wait_terminal(tmp_path, job_id, timeout=5)
    assert final["state"] == "deadline_exceeded"
    assert final["reported_by"] == "watchdog"
    assert final["supervisor_lost"] is True
    assert final["deadline_enforced"] is True
    assert final["child_alive"] is False


def test_duplicate_deterministic_launch_executes_worker_once(tmp_path):
    job_id = _job_id("idempotent")
    marker = tmp_path / "executions.txt"
    code = (
        "import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
        "p.open('a', encoding='utf-8').write('one\\n'); time.sleep(.35)"
    )
    first = _launch(tmp_path, job_id, [sys.executable, "-c", code, str(marker)])
    second = _launch(tmp_path, job_id, [sys.executable, "-c", code, str(marker)])
    assert second["reused"] is True
    assert second["supervisor_pid"] == first["supervisor_pid"]
    assert second["watchdog_pid"] == first["watchdog_pid"]
    assert _wait_terminal(tmp_path, job_id)["state"] == "succeeded"
    assert marker.read_text(encoding="utf-8").splitlines() == ["one"]


def test_real_ship_dry_run_is_recoverable_from_fresh_process(tmp_path):
    job_id = _job_id("ship")
    proc = subprocess.run(
        [sys.executable, str(SHIP), "T093 durable dry-run", "scripts/ship.py",
         "--dry-run", "--durable", "--job-id", job_id,
         "--job-state-dir", str(tmp_path), "--deadline-seconds", "5",
         "--grace-seconds", ".2"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=8,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    launch = _json_tail(proc.stdout)
    assert launch["job_id"] == job_id
    final = _wait_terminal(tmp_path, job_id)
    assert final["state"] == "succeeded"
    log = Path(final["log_path"]).read_text(encoding="utf-8")
    assert "# ship plan (dry-run -- nothing executed)" in log


def test_expired_spec_only_retry_fails_loudly_without_rebrokering(tmp_path, monkeypatch):
    """A lost launch frame is recoverable, but v1 must not guess and execute twice."""
    job_id = _job_id("spec-gap")
    command = [sys.executable, "-c", "raise SystemExit('must not execute')"]
    _seed_spec(tmp_path, job_id, command, startup_expired=True)
    broker_calls: list[object] = []
    monkeypatch.setattr(run_job, "_detached_create", lambda *_: broker_calls.append(1))
    monkeypatch.setattr(run_job, "_wmi_create_pair", lambda *_: broker_calls.append(1))

    receipt = run_job.launch_job(
        command, job_id=job_id, state_dir=tmp_path, cwd=ROOT,
        max_runtime=3.0, grace_seconds=0.2, heartbeat_seconds=0.05,
        broker="detached",
    )
    assert broker_calls == []
    assert receipt["state"] == "launch_failed"
    assert receipt["deadline_enforced"] is False
    assert receipt["retry_with_new_job_id"] is True
    assert receipt["reused"] is True


def test_terminal_sticky_watchdog_ready_cannot_authorize_worker_start(tmp_path):
    job_id = _job_id("stale-ready")
    paths = _seed_spec(
        tmp_path, job_id, [sys.executable, "-c", "raise SystemExit(99)"],
    )
    identity = run_job._process_info(os.getpid())[1]
    assert identity
    run_job._atomic_json(paths["watchdog"], {
        "schema": 1,
        "job_id": job_id,
        "state": "complete_observed",
        "ready": True,
        "watchdog_pid": os.getpid(),
        "watchdog_identity": identity,
        "heartbeat_epoch": time.time(),
    })
    ready = run_job._wait_watchdog_ready(paths, time.monotonic() + 0.06)
    assert not ready, "historical ready=True is not a live deadline owner"


def test_running_receipt_failure_cleans_up_prearmed_child(tmp_path, monkeypatch):
    job_id = _job_id("arm-failure")
    paths = _seed_spec(
        tmp_path, job_id, [sys.executable, "-c", "import time; time.sleep(60)"],
        max_runtime=5.0, heartbeat=0.02,
    )
    identity = run_job._process_info(os.getpid())[1]
    assert identity
    run_job._atomic_json(paths["watchdog"], {
        "schema": 1,
        "job_id": job_id,
        "state": "watching",
        "ready": True,
        "watchdog_pid": os.getpid(),
        "watchdog_identity": identity,
        "heartbeat_epoch": time.time(),
    })
    real_atomic = run_job._atomic_json
    failed_once = False

    def fail_first_running(path, payload):
        nonlocal failed_once
        if path == paths["status"] and payload.get("state") == "running" and not failed_once:
            failed_once = True
            raise OSError("injected running-receipt failure")
        return real_atomic(path, payload)

    real_popen = run_job.subprocess.Popen
    children = []

    def capture_child(*args, **kwargs):
        proc = real_popen(*args, **kwargs)
        children.append(proc)
        return proc

    monkeypatch.setattr(run_job, "_atomic_json", fail_first_running)
    monkeypatch.setattr(run_job.subprocess, "Popen", capture_child)
    try:
        run_job._supervise(job_id, tmp_path)
        assert failed_once and children
        deadline = time.monotonic() + 2
        while children[0].poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        assert children[0].poll() is not None, "unreceipted worker escaped supervision"
    finally:
        if children and children[0].poll() is None:
            child_identity = run_job._process_info(children[0].pid)[1]
            run_job._kill_tree(children[0].pid, child_identity)


def test_exit_zero_after_deadline_intent_remains_success(tmp_path):
    job_id = _job_id("zero-wins")
    code = r"""
import os, pathlib, time
cancel = pathlib.Path(os.environ['AKASHIC_JOB_CANCEL_FILE'])
while not cancel.exists():
    time.sleep(.005)
raise SystemExit(0)
"""
    _launch(
        tmp_path, job_id, [sys.executable, "-u", "-c", code],
        max_runtime=0.2, grace=0.5, heartbeat=0.02,
    )
    final = _wait_terminal(tmp_path, job_id, timeout=4)
    assert final["state"] == "succeeded"
    assert final["exit_code"] == 0
    assert final["forced"] is False


def test_publish_fence_defers_force_and_pushed_outcome_wins_late_cancel(tmp_path):
    job_id = _job_id("publish-fence")
    entered = tmp_path / "publish-entered.marker"
    code = r"""
import os, pathlib, time
from scripts import run_job
fence = pathlib.Path(os.environ['AKASHIC_JOB_PUBLISH_FENCE'])
outcome = pathlib.Path(os.environ['AKASHIC_JOB_OUTCOME_FILE'])
entered = pathlib.Path(os.environ['AKASHIC_T093_ENTERED_MARKER'])
with run_job.publish_fence(fence, blocking=True):
    run_job.write_child_outcome(outcome, {'state': 'publish_active', 'head_before': 'abc'})
    entered.write_text('inside', encoding='utf-8')
    time.sleep(.45)
    run_job.write_child_outcome(outcome, {
        'state': 'succeeded', 'primary_effect': 'pushed',
        'commit_sha': 'def', 'branch': 'test',
    })
"""
    old = os.environ.get("AKASHIC_T093_ENTERED_MARKER")
    os.environ["AKASHIC_T093_ENTERED_MARKER"] = str(entered)
    try:
        _launch(
            tmp_path, job_id, [sys.executable, "-u", "-c", code],
            max_runtime=5, grace=0.05, heartbeat=0.02,
        )
        deadline = time.monotonic() + 3
        while not entered.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert entered.exists(), "worker never entered the publish fence"
        _cli("cancel", job_id, "--state-dir", str(tmp_path), "--reason", "late publish cancel")
        final = _wait_terminal(tmp_path, job_id, timeout=4)
    finally:
        if old is None:
            os.environ.pop("AKASHIC_T093_ENTERED_MARKER", None)
        else:
            os.environ["AKASHIC_T093_ENTERED_MARKER"] = old
    assert final["state"] == "succeeded"
    assert final["primary_effect"] == "pushed"
    assert final["forced"] is False
    assert final["cancel_disposition"] == "after_publish_commit_point"


def test_pushed_outcome_is_not_terminal_until_job_quiescent(tmp_path):
    job_id = _job_id("pushed-candidate")
    entered = tmp_path / "pushed.entered"
    release = tmp_path / "pushed.release"
    effect = tmp_path / "after-push.effect"
    code = r"""
import os, pathlib, time
from scripts import run_job
outcome = pathlib.Path(os.environ['AKASHIC_JOB_OUTCOME_FILE'])
entered = pathlib.Path(os.environ['AKASHIC_T093_ENTERED_MARKER'])
release = pathlib.Path(os.environ['AKASHIC_T093_RELEASE_MARKER'])
effect = pathlib.Path(os.environ['AKASHIC_T093_EFFECT_MARKER'])
run_job.write_child_outcome(outcome, {
    'state': 'succeeded', 'primary_effect': 'pushed',
    'commit_sha': 'candidate-only', 'branch': 'test',
})
entered.write_text('pushed', encoding='utf-8')
deadline = time.monotonic() + 5
while not release.exists() and time.monotonic() < deadline:
    time.sleep(.01)
effect.write_text('post-push-work', encoding='utf-8')
"""
    old_values = {
        key: os.environ.get(key)
        for key in (
            "AKASHIC_T093_ENTERED_MARKER",
            "AKASHIC_T093_RELEASE_MARKER",
            "AKASHIC_T093_EFFECT_MARKER",
        )
    }
    os.environ["AKASHIC_T093_ENTERED_MARKER"] = str(entered)
    os.environ["AKASHIC_T093_RELEASE_MARKER"] = str(release)
    os.environ["AKASHIC_T093_EFFECT_MARKER"] = str(effect)
    final = {}
    try:
        _launch(
            tmp_path,
            job_id,
            [sys.executable, "-u", "-c", code],
            max_runtime=8,
            heartbeat=0.03,
        )
        deadline = time.monotonic() + 3
        while not entered.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert entered.exists()
        observed = _status(tmp_path, job_id)
        assert observed["child_alive"] is True
        assert observed["state"] not in TERMINAL, (
            "the pushed effect is authoritative, but live post-push work is not terminal"
        )
        assert observed["primary_effect"] == "pushed"
        release.write_text("continue", encoding="utf-8")
        final = _wait_terminal(tmp_path, job_id, timeout=4)
    finally:
        if entered.exists() and not release.exists():
            release.write_text("cleanup", encoding="utf-8")
        if entered.exists() and not final:
            try:
                final = _wait_terminal(tmp_path, job_id, timeout=6)
            except AssertionError:
                pass
        for key, old in old_values.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
    assert effect.read_text(encoding="utf-8") == "post-push-work"
    assert final["state"] == "succeeded"
    assert final["job_quiescent"] is True


def test_abandoned_publish_active_is_outcome_unknown(tmp_path):
    job_id = _job_id("publish-unknown")
    code = r"""
import os, pathlib
from scripts import run_job
fence = pathlib.Path(os.environ['AKASHIC_JOB_PUBLISH_FENCE'])
outcome = pathlib.Path(os.environ['AKASHIC_JOB_OUTCOME_FILE'])
with run_job.publish_fence(fence, blocking=True):
    run_job.write_child_outcome(outcome, {
        'state': 'publish_active', 'head_before': 'abc',
        'publish_may_have_occurred': True,
    })
raise SystemExit(7)
"""
    _launch(tmp_path, job_id, [sys.executable, "-u", "-c", code], max_runtime=3)
    final = _wait_terminal(tmp_path, job_id)
    assert final["state"] == "outcome_unknown"
    assert final["publish_may_have_occurred"] is True
    assert final["primary_effect"] != "pushed"


def test_dead_guards_promote_primary_state_to_supervision_lost(tmp_path):
    job_id = _job_id("guards-gone")
    paths = _seed_spec(
        tmp_path, job_id, [sys.executable, "-c", "import time; time.sleep(60)"],
    )
    run_job._atomic_json(paths["launch"], {
        "schema": 1,
        "job_id": job_id,
        "state": "launching",
        "supervisor_pid": 2_000_000_000,
        "watchdog_pid": 2_000_000_001,
    })
    run_job._atomic_json(paths["status"], {
        "schema": 1,
        "job_id": job_id,
        "state": "running",
        "supervisor_pid": 2_000_000_000,
        "heartbeat_epoch": 0.0,
        "child_pid": 2_000_000_002,
        "child_identity": "definitely-not-live",
    })
    receipt = run_job.read_status(job_id, tmp_path, stale_after=0.01)
    assert receipt["state"] == "supervision_lost"
    assert receipt["last_reported_state"] == "running"
    assert receipt["deadline_enforced"] is False
