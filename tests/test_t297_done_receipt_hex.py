"""T297 RED -- a done receipt is an immutable address, or it is not a receipt.

FOUND MINUTES AFTER IT HAPPENED: T292's first close passed `--commit HEAD`, and the gate --
whose own refusal says "needs a commit SHA" -- accepted the string. ~8 older rows carry the
same symbolic receipt. A ref dangles the moment the branch moves; the 1,483-citation repair
of 2026-08-12 was this class at repo scale, and the ledger was growing its own copy.

Pin: the done gate refuses a non-hex commit value WITH a teaching message (names hex and
rev-parse), and accepts a real short SHA. Driven through the real CLI door, because the
gate's meaning lives one function deep and every door must inherit it.

Run: py -m pytest tests/test_t297_done_receipt_hex.py -q
"""
import os
import re
import sys
import subprocess

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def run(*args, timeout=120):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def _drill_task():
    rc, out, err = run("task", "propose", "t297 drill: a closable slice")
    assert rc == 0, err or out
    tid = re.search(r"proposed (T\d+)", out).group(1)
    for step in (("approve", tid), ("claim", tid, "--by", "drill"), ("verify", tid)):
        rc, out, err = run("task", *step)
        assert rc == 0, f"{step}: {err or out}"
    return tid


def test_done_refuses_symbolic_refs_and_accepts_hex():
    tid = _drill_task()

    rc, out, err = run("task", "done", tid, "--commit", "HEAD",
                       "--verified-by", "t297 drill")
    blob = (out or "") + (err or "")
    assert rc != 0, "the gate must refuse 'HEAD' -- a symbolic ref dangles when the ref moves"
    assert "hex" in blob.lower() and "rev-parse" in blob.lower(), (
        "the refusal teaches: what a receipt is (hex) and how to get one (git rev-parse)")

    rc2, out2, err2 = run("task", "done", tid, "--commit", "deadbee1",
                          "--verified-by", "t297 drill")
    assert rc2 == 0, f"a real short SHA must close: {err2 or out2}"
