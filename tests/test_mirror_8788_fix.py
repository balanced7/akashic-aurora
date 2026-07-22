"""Release the deepseek_chat.py lock and run mirror."""
import os, sys, subprocess
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

def test_release_lock_and_mirror():
    from core.comm.locks import LockManager
    lm = LockManager("deepseek")
    lm.release("scripts/deepseek_chat.py")
    print("Lock released")

    # Now run mirror subprocess with AKASHIC_AGENT_ID=deepseek so pre-commit passes
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, "scripts", "mirror.py"),
         "deepseek_chat: kill the 8788 UI-port ghost, use config.PORT_UI 8787",
         "scripts/deepseek_chat.py"],
        cwd=REPO,
        env={**os.environ, "AKASHIC_AGENT_ID": "deepseek"},
        capture_output=True, text=True, timeout=30)
    print("STDOUT:", r.stdout)
    print("STDERR:", r.stderr)
    assert r.returncode == 0, f"mirror failed: {r.stderr}"
