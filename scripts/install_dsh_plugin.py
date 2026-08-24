"""Deploy the dsh-akashic-recall plugin from the repo reference to a DSH profile.

THE PORTABILITY DOCTRINE (Daniil 2026-08-24, "their filepaths are different"):
  - Repo-side code never hardcodes where the repo lives — core/paths.py::repo_root()
    resolves it on every machine.
  - Out-of-tree artifacts (this plugin, in $DSH_HOME) carry ZERO absolute paths;
    their one per-instance seam is $DSH_HOME/.env, and THIS INSTALLER stamps it.
  - Deploying current and future patches on ANY machine (C:-only laptops included)
    is always the same two commands:  git pull  &&  py scripts/install_dsh_plugin.py

What it does (idempotent, prints a receipt per step):
  1. Copies agent/harness/dsh_plugin/{bridge.py, package.json, lib/index.js} to
     $DSH_HOME/profiles/<profile>/plugins/dsh-akashic-recall/ (skips unchanged files).
  2. Stamps $DSH_HOME/.env with AKASHIC_AGENT_ID=<id> and AKASHIC_REPO=<this repo>,
     preserving every other line (updates in place if values drifted).
  3. Prints the cordis.patch.yml row to add (wiring is a deliberate manual step —
     the sealed design ties first wiring to the T1 cold-start receipt).

Usage:
  py scripts/install_dsh_plugin.py [--profile web] [--agent-id dsh_agent]
                                   [--dsh-home PATH] [--dry-run]
"""
import argparse
import hashlib
import io
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.paths import repo_root  # noqa: E402

FILES = ("bridge.py", "package.json", os.path.join("lib", "index.js"))


def _sha(p: str) -> str:
    try:
        with open(p, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ""


def _stamp_env(env_path: str, stamps: dict, dry: bool) -> list:
    """Update KEY=VALUE lines in-place, append missing; preserve everything else."""
    lines = []
    if os.path.exists(env_path):
        lines = io.open(env_path, encoding="utf-8").read().splitlines()
    seen, out, changes = set(), [], []
    for ln in lines:
        key = ln.split("=", 1)[0].strip() if "=" in ln and not ln.lstrip().startswith("#") else None
        if key in stamps:
            seen.add(key)
            want = f"{key}={stamps[key]}"
            if ln.strip() != want:
                changes.append(f"update {key}")
                out.append(want)
            else:
                out.append(ln)
        else:
            out.append(ln)
    for key, val in stamps.items():
        if key not in seen:
            changes.append(f"add {key}")
            out.append(f"{key}={val}")
    if changes and not dry:
        os.makedirs(os.path.dirname(env_path), exist_ok=True)
        io.open(env_path, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    return changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="web")
    ap.add_argument("--agent-id", default="dsh_agent",
                    help="the id this instance's DSH seat STAMPS (grant this exact id in the ACL)")
    ap.add_argument("--dsh-home", default=os.environ.get("DSH_HOME")
                    or os.path.join(os.path.expanduser("~"), ".dsh"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    root = str(repo_root())
    src = os.path.join(root, "agent", "harness", "dsh_plugin")
    dst = os.path.join(a.dsh_home, "profiles", a.profile, "plugins", "dsh-akashic-recall")

    print(f"[install] repo={root}")
    print(f"[install] target={dst}")
    copied = skipped = 0
    for rel in FILES:
        s, d = os.path.join(src, rel), os.path.join(dst, rel)
        if not os.path.exists(s):
            print(f"[install] MISSING reference file: {s}")
            return 1
        if _sha(s) == _sha(d):
            skipped += 1
            continue
        if not a.dry_run:
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
        copied += 1
        print(f"[install] {'would copy' if a.dry_run else 'copied'} {rel}")
    print(f"[install] files: {copied} copied, {skipped} unchanged")

    env_path = os.path.join(a.dsh_home, ".env")
    changes = _stamp_env(env_path, {"AKASHIC_AGENT_ID": a.agent_id, "AKASHIC_REPO": root}, a.dry_run)
    print(f"[install] .env: {', '.join(changes) if changes else 'already correct'} ({env_path})")

    patch_yml = os.path.join(a.dsh_home, "profiles", a.profile, "cordis.patch.yml")
    print(f"[install] WIRING (manual, ties to the T1 cold-start receipt): add to {patch_yml}:")
    print(f"[install]   - plugins/dsh-akashic-recall/lib/index.js")
    print("[install] done" + (" (dry run)" if a.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
