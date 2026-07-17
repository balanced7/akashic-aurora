"""T093 pre-registered kill drills for controller-independent durable jobs.

This file intentionally lands before implementation (M3).  The battery is black-box: every
completion check comes from a fresh ``run_job.py status`` process reading an atomic receipt, never
from the supervised child's stdout pipe.  Durations stay small; the production deadline is a dial.

Governing build spec:
research/reviewed/t093-crash-path-reconciliation-2026-07-17.md section 7.
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


def _force_pid(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, text=True, timeout=5,
        )
    else:
        try:
            os.kill(pid, 9)
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
    _force_pid(int(running["supervisor_pid"]))
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
