"""rust_gate -- the Rust half of `poe gate`: aurora-rs fmt, clippy, tests, cargo-deny and a fuzz smoke.

RFC #70's addendum puts cargo-deny (licences, RustSec advisories) and a fuzz smoke run in the gate,
beside CI. Most contributors only ever touch Python, so this step runs only when it matters and can
run: when aurora-rs/ differs from origin's default branch (or --force), and when cargo is installed.
Otherwise it says why it skipped and passes. CI always runs the full set (ci.yml, job `rust`).

Run:  uv run poe rust-gate            # inside the gate
      uv run python scripts/rust_gate.py --force --fuzz-seconds 10
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RS = ROOT / "aurora-rs"


def _changed() -> bool:
    """aurora-rs/ has edits, untracked files, or commits not on the upstream default branch."""
    status = subprocess.run(
        ["git", "status", "--porcelain", "--", "aurora-rs"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if status.stdout.strip():
        return True
    for base in ("origin/master", "origin/main"):
        diff = subprocess.run(["git", "diff", "--quiet", f"{base}...HEAD", "--", "aurora-rs"], cwd=ROOT, check=False)
        if diff.returncode in (0, 1):
            return diff.returncode == 1
    return True


def _run(cmd: list[str]) -> None:
    print(f"rust-gate: {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=RS, check=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="run even when aurora-rs/ is unchanged")
    ap.add_argument("--fuzz-seconds", type=int, default=10, help="per fuzz target (0 skips the smoke)")
    a = ap.parse_args(argv)
    if not shutil.which("cargo"):
        print("rust-gate: SKIP (no cargo here; CI's rust job runs it)")
        return 0
    if not a.force and not _changed():
        print("rust-gate: SKIP (aurora-rs/ is unchanged)")
        return 0
    try:
        _run(["cargo", "fmt", "--check"])
        _run(["cargo", "clippy", "--all-targets", "--", "-D", "warnings"])
        _run(["cargo", "test"])
        if shutil.which("cargo-deny"):
            _run(["cargo", "deny", "check"])
        else:
            print("rust-gate: cargo-deny is not installed (`cargo install cargo-deny`); CI runs it")
        if a.fuzz_seconds and shutil.which("cargo-fuzz"):
            _run(["sh", "link/fuzz/smoke.sh", str(a.fuzz_seconds)])
        elif a.fuzz_seconds:
            print("rust-gate: cargo-fuzz is not installed; CI runs the fuzz smoke")
    except subprocess.CalledProcessError as e:
        print(f"rust-gate: FAIL ({' '.join(e.cmd)} exited {e.returncode})")
        return 1
    print("rust-gate: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
