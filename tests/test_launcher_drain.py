"""
T019 -- launcher pipe drainers: a chatty child must never freeze on a full pipe.

Bar: a child writing far more than any OS pipe buffer (~600KB) EXITS promptly when spawned
with the launcher's drainer pattern, and the live tail captures its final line. Without
drainers the same child blocks forever mid-print (the 2026-07-09 deepseek runner wedge:
~12 minutes of streamed thinking filled the undrained PIPE; even the runner's timeout
guard froze, because it printed before it sent).

Run: py -m pytest tests/test_launcher_drain.py -q
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.launcher import AgentProcess, _start_drainers

SPAM = "import sys\nfor i in range(3000):\n    print('x' * 200)\nprint('DRAIN-DONE')\n"


def test_chatty_child_exits_and_tail_captures_final_line():
    handle = subprocess.Popen(
        [sys.executable, "-c", SPAM],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    proc = AgentProcess(agent_id="drain-test", pid=handle.pid, handle=handle, status="running")
    proc.drainers = _start_drainers(handle, proc)
    try:
        code = handle.wait(timeout=15)   # without drainers this deadlocks at ~1 pipe buffer
    finally:
        if handle.poll() is None:
            handle.kill()
    assert code == 0, "600KB-of-stdout child must run to completion"
    for t in proc.drainers:
        t.join(timeout=3)
    assert "DRAIN-DONE" in (proc.stdout_tail or ""), "live tail holds the child's last words"
    assert len(proc.stdout_tail) <= 500, "tail stays bounded"


def test_quiet_child_unaffected():
    handle = subprocess.Popen(
        [sys.executable, "-c", "print('hello')"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace",
    )
    proc = AgentProcess(agent_id="drain-test-2", pid=handle.pid, handle=handle, status="running")
    proc.drainers = _start_drainers(handle, proc)
    assert handle.wait(timeout=10) == 0
    for t in proc.drainers:
        t.join(timeout=3)
    assert "hello" in (proc.stdout_tail or "")
