"""L5 proof: launcher.launch() honors the singleton lock (refuses a duplicate) and no longer
acquires-and-holds the lock itself (which starved the child it spawned). No real process spawned:
the refusal returns before Popen."""
import os, ast, sys, re

ROOT = r"E:/AI-Setup"
src = open(os.path.join(ROOT, "core/comm/launcher.py"), encoding="utf-8").read()
ast.parse(src); print("parse OK: core/comm/launcher.py")

# regression guard: the stray acquire-and-hold in launch() is gone (that token was never
# heartbeat/released, so the child could never acquire its own lock -> died on startup).
assert "acquire(spec.agent_id, token)" not in src, "the starving acquire() must be removed from launch()"
assert "runner_lock.holder(spec.agent_id)" in src, "launch() must now CHECK the holder, not acquire"
print("[PASS] starving acquire() removed; launch() now checks holder() only")

sys.path.insert(0, ROOT)
from core.comm import runner_lock
from core.comm.launcher import get_launcher

TAG = "deepseek"  # a python_runner spec
tok = runner_lock.instance_token(TAG)
assert runner_lock.acquire(TAG, tok), "precondition: acquire the free lock to simulate a live runner"
try:
    res = get_launcher().launch(TAG)
    print("launch while lock held ->", res)
    assert res.get("ok") is False, ("must REFUSE a duplicate while a live runner holds the lock", res)
    assert res.get("pid") == os.getpid(), ("must report the holder pid", res.get("pid"), os.getpid())
    print(f"[PASS] duplicate refused; reported holder pid {res.get('pid')} (no process spawned)")
finally:
    runner_lock.release(TAG, tok)

assert runner_lock.holder(TAG) is None, "lock released -> a subsequent relaunch would proceed"
print("[PASS] lock released; holder None (relaunch path open)")
print("\nL5 VERIFIED.")
