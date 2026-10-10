"""build_bundle -- pack the Aurora release bundle the `aurora` launcher downloads.

The bundle is the repo tree at a commit (`git archive`, so only tracked files, never local
state), minus the docs website, as aurora-<version>.tar.gz with one top-level folder
aurora-<version>/ and an AURORA_BUNDLE.json naming the version and commit. Beside it goes
aurora-<version>.tar.gz.sha256, which the launcher checks before unpacking.

Symlinks are stored as copies of what they point at (.claude/skills -> .agents/skills), so
the bundle unpacks the same on Windows, where creating a symlink needs Developer Mode.
Entries are sorted and stamped with the commit time, so the same commit gives the same bytes.

Run:  uv run scripts/release/build_bundle.py                 # version from aurora-cli/pyproject.toml
      uv run scripts/release/build_bundle.py --out dist --ref v0.1.0
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from releases import cli_version  # noqa: E402  # sys.path bootstrap

#: Tracked paths that are not part of the program: the docs website has its own deploy.
EXCLUDE = ("apps",)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()


def _normalize(ti: tarfile.TarInfo, mtime: int) -> tarfile.TarInfo:
    ti.uid = ti.gid = 0
    ti.uname = ti.gname = ""
    ti.mtime = mtime
    ti.mode = 0o755 if ti.isdir() or ti.mode & 0o111 else 0o644
    return ti


def build(version: str, ref: str, out: Path) -> Path:
    commit = _git("rev-parse", f"{ref}^{{commit}}")
    mtime = int(_git("log", "-1", "--format=%ct", commit))
    top = f"aurora-{version}"
    out.mkdir(parents=True, exist_ok=True)
    archive = out / f"{top}.tar.gz"
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / top
        tree.mkdir()
        raw = subprocess.run(
            ["git", "archive", "--format=tar", commit, "--", ".", *[f":(exclude){e}" for e in EXCLUDE]],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            tf.extractall(tree, filter="tar")
        _materialize_links(tree)
        info = {"version": version, "commit": commit, "ref": ref, "excluded": list(EXCLUDE)}
        (tree / "AURORA_BUNDLE.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
        paths = sorted(tree.rglob("*"), key=lambda p: p.relative_to(tree).as_posix())

        def norm(t: tarfile.TarInfo) -> tarfile.TarInfo:
            return _normalize(t, mtime)

        # mtime=0 in the gzip header too, or the archive bytes change with the build clock
        with (
            open(archive, "wb") as fh,
            gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0) as gz,
            tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tar,
        ):
            tar.add(tree, arcname=top, recursive=False, filter=norm)
            for p in paths:
                tar.add(p, arcname=f"{top}/{p.relative_to(tree).as_posix()}", recursive=False, filter=norm)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (out / f"{archive.name}.sha256").write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive


def _materialize_links(tree: Path) -> None:
    """Replace every symlink with a copy of its target. A link that leaves the tree is an error:
    the bundle must not depend on the machine that built it."""
    for link in sorted((p for p in tree.rglob("*") if p.is_symlink()), key=lambda p: len(p.parts)):
        # Read the link's own text instead of resolve(): on Windows the temp dir can resolve to
        # its 8.3 short name (RUNNER~1) on one side and the long name on the other, and a
        # correct in-tree link would then look like it leaves the tree.
        rel = os.path.normpath(os.path.join(os.path.relpath(link.parent, tree), os.readlink(link)))
        if os.path.isabs(os.readlink(link)) or rel == os.pardir or rel.startswith(os.pardir + os.sep):
            raise SystemExit(f"build_bundle: {link.relative_to(tree)} points outside the repo ({os.readlink(link)})")
        target = tree / rel
        link.unlink()
        if target.is_dir():
            shutil.copytree(target, link)
        else:
            shutil.copy2(target, link)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pack the Aurora release bundle (aurora-<version>.tar.gz + .sha256).")
    ap.add_argument("--version", default=None, help="bundle version (default: aurora-cli/pyproject.toml)")
    ap.add_argument("--ref", default="HEAD", help="git ref to pack (default: HEAD)")
    ap.add_argument("--out", default="dist", help="output directory (default: dist)")
    a = ap.parse_args(argv)
    archive = build(a.version or cli_version(), a.ref, Path(a.out).resolve())
    size = archive.stat().st_size / 1e6
    print(f"{archive} ({size:.1f} MB)")
    print(f"{archive}.sha256")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
