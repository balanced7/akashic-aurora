"""Where the Aurora program and its state live, and how a release bundle gets there.

Layout (AURORA_HOME, default ~/.aurora):

    versions/<X.Y.Z>/     the release bundle: the repo tree at tag vX.Y.Z, plus its .venv
    data/                 instance state -- lessons, session logs, the embedded Redis files.
                          Separate from versions/ so an upgrade never touches memory.
    world                 optional: the Aurora world this install is (prod | beta | alpha)

A bundle is fetched once per launcher version from the GitHub release (or AURORA_RELEASE_BASE),
checked against its published sha256, and unpacked. Its environment is built by `uv sync
--frozen` from the bundle's own uv.lock, so an installed Aurora runs the same locked
dependencies as a checkout. Nothing here imports anything outside the standard library.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

#: The GitHub repository that publishes releases.
REPO_SLUG = "balanced7/akashic-aurora"
#: The optional Rust acceleration wheel (aurora-rs/py), installed best-effort beside the bundle.
ACCEL_PACKAGE = "akashic-aurora-rs"
_MARKERS = ("agent_cli.py", "core")


def log(msg: str) -> None:
    """Progress goes to stderr: a hook's stdout is JSON its harness parses."""
    print(f"aurora: {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- locations
def home() -> Path:
    env = (os.environ.get("AURORA_HOME") or "").strip()
    return Path(env).expanduser() if env else Path.home() / ".aurora"


def versions_dir() -> Path:
    return home() / "versions"


def data_dir() -> Path:
    return home() / "data"


def bundle_dir(version: str) -> Path:
    return versions_dir() / version


def installed_versions() -> list[str]:
    d = versions_dir()
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if (p / "AURORA_BUNDLE.json").is_file())


def world() -> str:
    """The world this install is: AKASHIC_WORLD, else the `world` file, else prod.

    A bundle directory is named after its version, so core/world.py cannot derive a world from
    the directory name the way it does for a checkout; without this an install would resolve
    to `unknown`, which refuses every memory write.
    """
    env = (os.environ.get("AKASHIC_WORLD") or "").strip()
    if env:
        return env
    try:
        return (home() / "world").read_text(encoding="utf-8").strip() or "prod"
    except OSError:
        return "prod"


def looks_like_repo(p: Path) -> bool:
    return all((p / m).exists() for m in _MARKERS)


# --------------------------------------------------------------------------- release assets
def release_base(version: str) -> str:
    """Where the release assets of `version` live. AURORA_RELEASE_BASE overrides it: a URL or a
    local directory, with an optional {version} placeholder (CI smoke tests use a directory)."""
    env = (os.environ.get("AURORA_RELEASE_BASE") or "").strip()
    if env:
        return env.replace("{version}", version).rstrip("/")
    return f"https://github.com/{REPO_SLUG}/releases/download/v{version}"


def asset_name(version: str) -> str:
    return f"aurora-{version}.tar.gz"


def _open(url: str):
    if "://" not in url:
        return open(url, "rb")  # noqa: SIM115  # returned to a with-block in the caller
    req = urllib.request.Request(url, headers={"User-Agent": "aurora-cli"})
    return urllib.request.urlopen(req, timeout=60)  # noqa: S310  # https or file only, by construction


def download(url: str, dest: Path) -> str:
    """Stream url to dest; returns the sha256 of what was written."""
    h = hashlib.sha256()
    with _open(url) as src, dest.open("wb") as out:
        while chunk := src.read(1 << 20):
            h.update(chunk)
            out.write(chunk)
    return h.hexdigest()


def read_text(url: str) -> str:
    with _open(url) as src:
        return src.read().decode("utf-8")


def latest_version() -> str:
    """The newest published release, from the GitHub API (AURORA_LATEST overrides it)."""
    env = (os.environ.get("AURORA_LATEST") or "").strip()
    if env:
        return env.lstrip("v")
    doc = json.loads(read_text(f"https://api.github.com/repos/{REPO_SLUG}/releases/latest"))
    return str(doc["tag_name"]).lstrip("v")


# --------------------------------------------------------------------------- fetch + unpack
def ensure_bundle(version: str) -> Path:
    """The bundle for `version`, fetching and unpacking it on first use."""
    target = bundle_dir(version)
    if (target / "AURORA_BUNDLE.json").is_file():
        return target
    base = release_base(version)
    name = asset_name(version)
    versions_dir().mkdir(parents=True, exist_ok=True)
    log(f"fetching Aurora {version} from {base}/{name}")
    with tempfile.TemporaryDirectory(dir=versions_dir(), prefix=".fetch-") as tmp:
        archive = Path(tmp) / name
        try:
            got = download(f"{base}/{name}", archive)
            want = read_text(f"{base}/{name}.sha256").split()[0].strip().lower()
        except OSError as e:
            raise SystemExit(
                f"aurora: could not download Aurora {version} ({e}).\n"
                f"  Check your connection, or point AURORA_RELEASE_BASE at a directory holding {name}."
            ) from e
        if got != want:
            raise SystemExit(f"aurora: {name} failed its checksum (got {got}, published {want}); not installing it.")
        unpack = Path(tmp) / "unpacked"
        with tarfile.open(archive) as tf:
            tf.extractall(unpack, filter="data")
        tops = [p for p in unpack.iterdir() if p.is_dir()]
        if len(tops) != 1 or not looks_like_repo(tops[0]):
            raise SystemExit(
                f"aurora: {name} is not an Aurora bundle (expected one top-level folder with agent_cli.py)."
            )
        try:
            tops[0].rename(target)
        except OSError:
            # Another aurora process unpacked the same version first; theirs is identical.
            if not (target / "AURORA_BUNDLE.json").is_file():
                raise
    return target


# --------------------------------------------------------------------------- environment
def uv_bin() -> str:
    found = shutil.which("uv")
    if found:
        return found
    try:
        from uv import find_uv_bin  # the PyPI `uv` package this launcher depends on

        return find_uv_bin()
    except Exception as e:  # pragma: no cover - depends on the install
        raise SystemExit("aurora: uv is not available. Install it: https://docs.astral.sh/uv/") from e


def venv_python(root: Path, gui: bool = False) -> Path:
    if os.name == "nt":
        return root / ".venv" / "Scripts" / ("pythonw.exe" if gui else "python.exe")
    return root / ".venv" / "bin" / "python"


def _lock_digest(root: Path) -> str:
    try:
        return hashlib.sha256((root / "uv.lock").read_bytes()).hexdigest()
    except OSError:
        return "no-lock"


def _sync_marker(root: Path) -> Path:
    return root / ".venv" / ".aurora-synced"


def is_synced(root: Path) -> bool:
    try:
        return _sync_marker(root).read_text(encoding="utf-8").strip() == _lock_digest(root)
    except OSError:
        return False


def sync(root: Path, version: str) -> None:
    """Build the bundle's .venv from its uv.lock, then add the Rust acceleration if a wheel
    exists for this platform. Output goes to stderr (see log)."""
    log(f"preparing Aurora's Python environment in {root / '.venv'} (once per version; a minute or two)")
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT")}
    cmd = [uv_bin(), "sync", "--frozen", "--quiet", "--project", str(root)]
    rc = subprocess.call(cmd, stdout=sys.stderr, env=env)
    if rc != 0:
        raise SystemExit(f"aurora: `{' '.join(cmd)}` failed (exit {rc}).")
    install_accel(root, version)
    _sync_marker(root).write_text(_lock_digest(root), encoding="utf-8")


def install_accel(root: Path, version: str) -> bool:
    """Best effort: the aurora-rs wheel matching this release. Aurora runs the same without it
    (core/accel.py falls back to pure Python), so a miss is a note, never an error."""
    cmd = [uv_bin(), "pip", "install", "--quiet", "--python", str(venv_python(root)), "--only-binary", ":all:"]
    links = (os.environ.get("AURORA_RS_FIND_LINKS") or "").strip()
    if links:
        cmd += ["--find-links", links]
    cmd.append(f"{ACCEL_PACKAGE}=={version}")
    ok = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    if not ok:
        log(f"no {ACCEL_PACKAGE} {version} wheel for this platform; using the pure-Python paths (same results)")
    return ok
