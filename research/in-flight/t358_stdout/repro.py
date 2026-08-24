"""Isolate the 'python parent inheriting stdout -> zero child bytes' defect (Daniil's pin 6ba50eab34)."""
import subprocess
import sys

print("== parent stdout isatty:", sys.stdout.isatty(), "encoding:", sys.stdout.encoding, flush=True)
print("== parent stdin  isatty:", sys.stdin.isatty(), flush=True)

def call_plain():
    print("\n[1] subprocess.call inherited handles:")
    rc = subprocess.call([sys.executable, "agent_cli.py", "flightdeck"])
    print("[1] rc =", rc, flush=True)

def call_capture():
    print("\n[2] subprocess.run capture_output=True:")
    p = subprocess.run([sys.executable, "agent_cli.py", "flightdeck"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("[2] rc =", p.returncode, "stdout_bytes =", len(p.stdout), "stderr_bytes =", len(p.stderr), flush=True)
    print("[2] stdout head:", repr(p.stdout[:120]), flush=True)

def call_run_inherit():
    print("\n[3] subprocess.run inheriting (no capture):")
    p = subprocess.run([sys.executable, "agent_cli.py", "flightdeck"])
    print("[3] rc =", p.returncode, flush=True)

if __name__ == "__main__":
    call_plain()
    call_capture()
    call_run_inherit()
