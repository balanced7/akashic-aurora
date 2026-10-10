"""releases -- one release version, kept in step across every place that states it.

Modelled on openai/codex's release flow: master keeps working versions; a release is a commit
that bumps the version, then an annotated tag `vX.Y.Z` on it. The tag triggers
.github/workflows/release.yml, whose first job runs `check-tag` and stops the release if the
tag and the files disagree -- so a tag can never publish something its files do not say.

Where the version lives:
    aurora-cli/pyproject.toml     the `aurora` launcher; it fetches the bundle of ITS version
    aurora-rs/Cargo.toml          [workspace.package] version -- the Rust crates and, through
                                  maturin, the akashic-aurora-rs wheel

Run:  uv run scripts/release/releases.py version             # print the current version
      uv run scripts/release/releases.py check-tag v0.1.0    # exit 1 unless every file says 0.1.0
      uv run scripts/release/releases.py bump 0.2.0          # rewrite them all, then relock
      uv run scripts/release/releases.py notes v0.2.0        # release notes since the last tag
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI_PYPROJECT = ROOT / "aurora-cli" / "pyproject.toml"
RS_CARGO = ROOT / "aurora-rs" / "Cargo.toml"
# X.Y.Z only: one spelling that is valid semver (Cargo) and PEP 440 (PyPI) at once, and that
# the launcher can turn into its release URL (vX.Y.Z) without translation.
_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_PY_VERSION = re.compile(r'(?m)^(version\s*=\s*")([^"]+)(")')
_RS_VERSION = re.compile(r'(?ms)(^\[workspace\.package\][^\[]*?^version\s*=\s*")([^"]+)(")')


def cli_version() -> str:
    m = _PY_VERSION.search(CLI_PYPROJECT.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"releases: no version in {CLI_PYPROJECT}")
    return m.group(2)


def rs_version() -> str:
    m = _RS_VERSION.search(RS_CARGO.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"releases: no [workspace.package] version in {RS_CARGO}")
    return m.group(2)


def versions() -> dict[str, str]:
    return {str(CLI_PYPROJECT.relative_to(ROOT)): cli_version(), str(RS_CARGO.relative_to(ROOT)): rs_version()}


def check_tag(tag: str) -> int:
    want = tag.removeprefix("refs/tags/").removeprefix("v")
    if not _SEMVER.match(want):
        print(f"releases: tag {tag!r} is not vX.Y.Z")
        return 1
    bad = {f: v for f, v in versions().items() if v != want}
    for f, v in bad.items():
        print(f"releases: {f} says {v}, the tag says {want}")
    if bad:
        print(f"releases: run `uv run scripts/release/releases.py bump {want}`, commit, and tag again")
        return 1
    print(f"releases: tag v{want} matches every version file")
    return 0


def bump(new: str) -> int:
    if not _SEMVER.match(new):
        print(f"releases: {new!r} is not X.Y.Z")
        return 1
    text = CLI_PYPROJECT.read_text(encoding="utf-8")
    CLI_PYPROJECT.write_text(_PY_VERSION.sub(rf"\g<1>{new}\g<3>", text, count=1), encoding="utf-8")
    text = RS_CARGO.read_text(encoding="utf-8")
    RS_CARGO.write_text(_RS_VERSION.sub(rf"\g<1>{new}\g<3>", text, count=1), encoding="utf-8")
    subprocess.run(["uv", "lock"], cwd=ROOT, check=True)
    cargo = shutil.which("cargo")
    if cargo:
        subprocess.run([cargo, "update", "--workspace"], cwd=RS_CARGO.parent, check=True)
    else:
        print("releases: cargo not found -- run `cargo update --workspace` in aurora-rs/ before committing")
    print(f"releases: bumped to {new}. Next: commit, then `git tag -a v{new} -m v{new}` and push the tag.")
    return 0


def notes(tag: str) -> int:
    """Conventional-commit subjects since the previous tag, grouped -- the release body."""
    prev = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", f"{tag}^"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    rng = f"{prev}..{tag}" if prev else tag
    log = subprocess.run(
        ["git", "log", "--no-merges", "--format=%s", rng], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    groups = {"feat": "Features", "fix": "Fixes", "perf": "Performance", "docs": "Documentation"}
    out: dict[str, list[str]] = {}
    for subject in log:
        kind = re.match(r"^(\w+)(?:\([^)]*\))?!?:", subject)
        out.setdefault(groups.get(kind[1] if kind else "", "Other changes"), []).append(subject)
    print(f"## Aurora {tag}\n")
    print("Install or update: see https://github.com/balanced7/akashic-aurora#install\n")
    for title in (*groups.values(), "Other changes"):
        if out.get(title):
            print(f"### {title}\n")
            print("\n".join(f"- {s}" for s in out[title]) + "\n")
    if prev:
        print(f"Full diff: https://github.com/balanced7/akashic-aurora/compare/{prev}...{tag}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Keep the release version in step (see module docstring).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="print the release version")
    sub.add_parser("check-tag", help="fail unless every version file matches the tag").add_argument("tag")
    sub.add_parser("bump", help="set a new version everywhere and relock").add_argument("version")
    sub.add_parser("notes", help="release notes for a tag").add_argument("tag")
    a = ap.parse_args(argv)
    if a.cmd == "version":
        print(cli_version())
        return 0
    if a.cmd == "check-tag":
        return check_tag(a.tag)
    if a.cmd == "bump":
        return bump(a.version)
    return notes(a.tag)


if __name__ == "__main__":
    sys.exit(main())
