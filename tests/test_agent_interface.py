"""
Failure-mode tests for the agent interface (the seam OpenCode touches).

These do NOT import the system -- they SHELL OUT to `agent_cli.py` exactly as an
external agent (OpenCode) would, then assert the system handles each way an agent
can be "dumb" or the environment can be degraded:

  * 50-line reader        -- the contract (AGENTS.md) + boot output are front-loaded
  * Redis down            -- everything still works off files
  * messy/huge/unicode    -- partial, None-ish, oversized, non-ASCII inputs are safe
  * re-recording          -- repeated lessons update, never duplicate the index
  * bad invocation        -- missing/unknown args give a helpful error + nonzero exit
  * ASCII-safe output     -- never crashes a cp1252 (Windows) console
  * isolation             -- none of this touches canonical data (db 0)

Run: py tests/test_agent_interface.py
"""
import os
import sys
import subprocess

import isolate_canonical  # noqa: F401 -- db 15 + temp AI_SETUP, flushed (child inherits via env)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PASS = []


def run(*args, redis_port=None, timeout=60):
    """Invoke the CLI as a subprocess, like OpenCode would. Returns (rc, out, err)."""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"          # clean capture; we separately assert ASCII
    if redis_port is not None:
        env["REDIS_PORT"] = str(redis_port)
    r = subprocess.run([sys.executable, "agent_cli.py", *args],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def ok(name):
    PASS.append(name); print(f"  [OK] {name}")


# --------------------------------------------------------------------------------
def test_agents_md_front_loaded():
    """A 50-line reader must get the whole contract from the top of AGENTS.md."""
    head = "\n".join(open(os.path.join(ROOT, "AGENTS.md"), encoding="utf-8").read().splitlines()[:40])
    assert "agent_cli.py boot" in head, "boot command must be in the first 40 lines"
    assert "agent_cli.py learn" in head, "learn command must be in the first 40 lines"
    ok("AGENTS.md contract is in the first 40 lines (50-line-reader safe)")


def test_boot_output_front_loaded_and_ascii():
    rc, out, _ = run("boot", "agent_x", "--task", "anything")
    assert rc == 0, f"boot should succeed, rc={rc}"
    assert out.isascii(), "boot output must be ASCII (cp1252-safe)"
    head = "\n".join(out.splitlines()[:8])
    assert "CONTEXT for agent_x" in head and "tokens" in head, "key info must be in first 8 lines"
    ok("boot output is front-loaded + ASCII-safe")


def test_full_loop_agent_a_to_b():
    """Agent A records a lesson; Agent B boots and sees it (episodic->semantic)."""
    run("learn", "agentA", "--experiment", "iface_loop_exp",
        "--tried", "wrote a lesson", "--result", "it persisted",
        "--recommend", "agent B should see this", "--category", "verification")
    rc, out, _ = run("recall", "iface_loop_exp")
    assert rc == 0 and "iface_loop_exp" in out, "recall must find the new lesson"
    rc, out, _ = run("boot", "agentB", "--task", "verification work")
    assert "agent B should see this" in out, "agent B's boot must surface agent A's lesson"
    ok("full loop: agent A learns -> agent B boots and sees it")


def test_learn_validation():
    rc, out, _ = run("learn", "agent_x", "--experiment", "no_body")   # no --tried/--result
    assert rc == 2 and "ERROR" in out and "Example" in out, "must reject + show usage"
    ok("learn rejects empty body with a helpful error + exit 2")


def test_messy_input_is_sanitized():
    """Unicode + oversized fields must not crash; they get clipped/encoded safely."""
    big = "x" * 9000
    rc, out, _ = run("learn", "messy_agent", "--experiment", "messy_exp",
                     "--tried", "café ☃ 日本語", "--result", big,
                     "--recommend", "handle me", "--category", "robustness")
    assert rc == 0, f"messy learn should still succeed, rc={rc}, out={out}"
    assert out.isascii(), "confirmation output must stay ASCII"
    # verify it stored, clipped (read the isolated store in-process)
    from core.learning.learning_store import get_learning_store
    rec = get_learning_store()._load_experiment("messy_exp")
    assert rec, "messy lesson must be stored"
    assert len(rec.get("actual", "")) <= 4100, "oversized field must be clipped"
    ok("messy/huge/unicode input is sanitized, not fatal")


def test_rerecord_does_not_duplicate_index():
    """Re-recording the same experiment updates it; the index must NOT grow."""
    for i in range(4):
        run("learn", "dup_agent", "--experiment", "dup_exp",
            "--tried", f"attempt {i}", "--result", "same name each time")
    from core.foundation.store import create_store
    store = create_store()                       # db 15 (isolated) per env
    alllist = store.lrange("learn:experiments:all", 0, -1)
    assert alllist.count("dup_exp") == 1, f"dup_exp must appear once, got {alllist.count('dup_exp')}"
    ok("re-recording updates in place (no duplicate index growth)")


def test_redis_down_file_fallback():
    """Point at a dead Redis port: boot + learn + recall must still work off files."""
    rc, out, _ = run("boot", "downagent", "--task", "x", redis_port=63999)
    assert rc == 0, f"boot must survive Redis down, rc={rc}"
    rc, out, _ = run("learn", "downagent", "--experiment", "offline_exp",
                     "--tried", "work while redis down", "--result", "file fallback held",
                     redis_port=63999)
    assert rc == 0, "learn must survive Redis down (file fallback)"
    rc, out, _ = run("recall", "offline", redis_port=63999)
    assert "offline_exp" in out, "recall must find the file-fallback lesson"
    ok("Redis down -> boot/learn/recall all work via File fallback")


def test_bad_invocation():
    rc, _, err = run()                       # no subcommand
    assert rc != 0, "no-subcommand must exit nonzero"
    rc, _, err = run("learn", "agent_x")     # missing required --experiment
    assert rc != 0, "missing --experiment must exit nonzero"
    rc, _, err = run("nonsense")             # unknown subcommand
    assert rc != 0, "unknown subcommand must exit nonzero"
    ok("bad invocations exit nonzero (don't silently no-op)")


def test_status_and_recall_ascii():
    for args in (("status",), ("recall", "anything")):
        rc, out, _ = run(*args)
        assert rc == 0 and out.isascii(), f"{args} must succeed + be ASCII"
    ok("status + recall are ASCII-safe and succeed")


def main():
    import redis
    db0_before = redis.Redis(port=16379, db=0).dbsize()
    print("=" * 60); print("AGENT INTERFACE FAILURE-MODE TESTS"); print("=" * 60)
    test_agents_md_front_loaded()
    test_boot_output_front_loaded_and_ascii()
    test_full_loop_agent_a_to_b()
    test_learn_validation()
    test_messy_input_is_sanitized()
    test_rerecord_does_not_duplicate_index()
    test_redis_down_file_fallback()
    test_bad_invocation()
    test_status_and_recall_ascii()
    db0_after = redis.Redis(port=16379, db=0).dbsize()
    assert db0_before == db0_after, f"CANONICAL TOUCHED: db0 {db0_before} -> {db0_after}"
    ok(f"canonical db0 unchanged ({db0_after}) -- interface tests fully isolated")
    print("\n" + "=" * 60); print(f"ALL AGENT INTERFACE TESTS PASSED ({len(PASS)})"); print("=" * 60)


if __name__ == "__main__":
    main()
