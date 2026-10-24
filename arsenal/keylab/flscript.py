"""Install, check and remove our FL Studio script (arsenal/keylab/fl/device_AuroraKeyLab.py).

The script goes in ONE folder FL scans for user scripts:
    <Documents>/Image-Line/FL Studio/Settings/Hardware/Aurora KeyLab/device_AuroraKeyLab.py
Nothing here writes anywhere else. Arturia's folder beside it is never opened for writing, and a target folder that
holds anything we did not put there is refused, never cleaned. Removal deletes our files one by one and then the
empty folder (os.rmdir, which cannot take a folder with anything left in it).

FL state is only ever READ: whether FL64.exe is running (tasklist) and which script FL last saved for the
KeyLab's DAW input (HKCU\\Software\\Image-Line\\FL Studio NN\\Devices\\MIDI input, winreg, read-only).
"""
from __future__ import annotations

import fnmatch
import hashlib
import os
import pathlib
import stat
import subprocess
import sys
from typing import List, Optional, Tuple

SCRIPT_NAME = "device_AuroraKeyLab.py"
SCRIPT_TITLE = "Aurora KeyLab"               # the script's "# name=" line, what FL lists as the Controller type
FOLDER_NAME = "Aurora KeyLab"
ARTURIA_FOLDER = "Arturia KeyLab mk3"
ARTURIA_TITLE = "KeyLab mk3"                 # Arturia's DAW-port script, as FL lists it
SOURCE = pathlib.Path(__file__).resolve().parent / "fl" / SCRIPT_NAME
INSTALL_DOC = "arsenal/keylab/fl/INSTALL.md"

_TEMP_NAME = "." + SCRIPT_NAME + ".tmp"      # the half-written copy during an install (atomic replace)
_PYC_PATTERN = SCRIPT_NAME[:-3] + ".*.pyc"   # what a Python might cache for our script, inside __pycache__


# ----------------------------------------------------------------------------------------------------------------------
# where FL's Hardware folder is
def documents_dir() -> pathlib.Path:
    """The user's Documents folder (honours a redirected Documents on Windows), else ~/Documents."""
    if sys.platform == "win32":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:   # CSIDL_PERSONAL
                return pathlib.Path(buf.value)
        except (OSError, AttributeError):
            pass
    return pathlib.Path.home() / "Documents"


def default_hardware_dir() -> pathlib.Path:
    return documents_dir() / "Image-Line" / "FL Studio" / "Settings" / "Hardware"


def hardware_dir(override: Optional[str]) -> pathlib.Path:
    return pathlib.Path(override) if override else default_hardware_dir()


# ----------------------------------------------------------------------------------------------------------------------
# what is ours
def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_reparse_point(path: pathlib.Path) -> bool:
    """A symlink or a Windows junction: refused, so a write can never land outside the Hardware folder."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def foreign_entries(target: pathlib.Path) -> List[str]:
    """Entries in our folder that we did not put there (relative names). Empty means the folder is all ours."""
    if not target.is_dir():
        return []
    foreign = []
    for entry in sorted(target.iterdir(), key=lambda p: p.name):
        if entry.name in (SCRIPT_NAME, _TEMP_NAME) and entry.is_file() and not _is_reparse_point(entry):
            continue
        if entry.name == "__pycache__" and entry.is_dir() and not _is_reparse_point(entry):
            for cached in sorted(entry.iterdir(), key=lambda p: p.name):
                if not (cached.is_file() and fnmatch.fnmatch(cached.name, _PYC_PATTERN)):
                    foreign.append("__pycache__/" + cached.name)
            continue
        foreign.append(entry.name + ("/" if entry.is_dir() else ""))
    return foreign


def _check_target(hw: pathlib.Path) -> Tuple[Optional[pathlib.Path], List[str]]:
    """(target folder, problems). Problems stop every verb that writes."""
    problems = []
    if not hw.is_dir():
        problems.append(f"FL's Hardware folder is not at {hw} (FL Studio not installed, or a custom user data folder:"
                        f" pass --hardware-dir)")
        return None, problems
    target = hw / FOLDER_NAME
    if _is_reparse_point(target):
        problems.append(f"{target} is a link or junction; refusing to write through it")
        return target, problems
    if target.exists() and not target.is_dir():
        problems.append(f"{target} exists and is not a folder; refusing to touch it")
        return target, problems
    if target.resolve().parent != hw.resolve():
        problems.append(f"{target} does not resolve inside {hw}; refusing")
        return target, problems
    foreign = foreign_entries(target)
    if foreign:
        problems.append(f"{target} holds files that are not ours: {', '.join(foreign)}. Nothing was changed;"
                        f" move them out by hand if they should not be there")
    return target, problems


# ----------------------------------------------------------------------------------------------------------------------
# read-only looks at FL
def fl_running() -> Optional[bool]:
    """True / False from tasklist; None when it cannot tell (not Windows, tasklist missing)."""
    if sys.platform != "win32":
        return None
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    names = {line.split(",")[0].strip('"').lower() for line in out.splitlines() if line.strip()}
    return bool(names & {"fl64.exe", "fl.exe"})


def daw_port_scripts() -> List[Tuple[str, str, str]]:
    """[(FL version key, MIDI input name, script name)] for every KeyLab DAW input FL has saved, read-only.
    The script name is the script's "# name=" line ("KeyLab mk3" for Arturia's, "Aurora KeyLab" for ours)."""
    if sys.platform != "win32":
        return []
    try:
        import winreg
    except ImportError:
        return []
    found = []
    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Image-Line")
    except OSError:
        return []
    with root:
        versions = []
        i = 0
        while True:
            try:
                versions.append(winreg.EnumKey(root, i))
            except OSError:
                break
            i += 1
        for version in sorted(v for v in versions if v.startswith("FL Studio")):
            try:
                inputs = winreg.OpenKey(root, version + r"\Devices\MIDI input")
            except OSError:
                continue
            with inputs:
                j = 0
                while True:
                    try:
                        name = winreg.EnumKey(inputs, j)
                    except OSError:
                        break
                    j += 1
                    if "keylab" in name.lower() and "daw" in name.lower():
                        try:
                            with winreg.OpenKey(inputs, name) as dev:
                                script = str(winreg.QueryValueEx(dev, "ScriptFolder")[0])
                        except OSError:
                            script = "?"
                        found.append((version, name, script))
    return found


# ----------------------------------------------------------------------------------------------------------------------
# the verbs' work (each returns (exit code, lines to print))
def next_steps() -> List[str]:
    return [
        "Next, in FL Studio:",
        '  1. Options > MIDI settings. Click "Update MIDI scripts" (or restart FL) so FL sees the new folder.',
        f'  2. In the Input list select "KeyLab 88 mk3 DAW" and set Controller type to "{SCRIPT_TITLE} (user)".',
        "     Keep its port number (236) and the matching output port.",
        f'  3. Leave "KeyLab 88 mk3 MIDI" on its own script ("KeyLab mk3 Arturia dev").',
        f'  4. View > Script output: the DAW tab should say "{SCRIPT_TITLE} v0".',
        f'  Back to Arturia\'s at any time: the same Controller type dropdown, pick "{ARTURIA_TITLE}".',
        f"  First-run drill: {INSTALL_DOC}",
    ]


def install(hw: pathlib.Path, dry_run: bool = False, source: pathlib.Path = SOURCE) -> Tuple[int, List[str]]:
    data = source.read_bytes()
    target, problems = _check_target(hw)
    if problems:
        return 2, ["fl-install refused:"] + ["  " + p for p in problems]
    dest = target / SCRIPT_NAME
    if dest.is_file() and dest.read_bytes() == data:
        return 0, [f"already installed, same bytes ({_sha(data)[:12]}): {dest}"] + next_steps()
    verb, done = ("replace", "replaced") if dest.exists() else ("install", "installed")
    if dry_run:
        lines = [f"dry run: would {verb} {dest} ({len(data)} bytes, sha256 {_sha(data)[:12]})"]
        if not target.exists():
            lines.append(f"dry run: would create the folder {target}")
        lines.append("dry run: nothing written; no other folder is touched")
        return 0, lines
    target.mkdir(exist_ok=True)
    tmp = target / _TEMP_NAME
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    lines = [f"{done} {dest} ({len(data)} bytes, sha256 {_sha(data)[:12]})"]
    if fl_running():
        lines.append("FL is running: after step 1 below it picks the file up; if the script was already selected,"
                     " re-pick it in the dropdown to reload it.")
    return 0, lines + next_steps()


def uninstall(hw: pathlib.Path, dry_run: bool = False, force: bool = False) -> Tuple[int, List[str]]:
    target, problems = _check_target(hw)
    if target is None:
        return 0, [f"nothing to remove: {problems[0]}"]
    if not problems and not target.exists():
        return 0, [f"not installed: {target} does not exist"]
    if problems:
        return 2, ["fl-uninstall refused:"] + ["  " + p for p in problems]
    ours = [p for p in (target / SCRIPT_NAME, target / _TEMP_NAME) if p.is_file()]
    cache = target / "__pycache__"
    cached = sorted(cache.iterdir()) if cache.is_dir() else []
    lines = []
    picked = [s for _, _, s in daw_port_scripts() if s == SCRIPT_TITLE]
    running = fl_running()
    if (picked or running) and not force:
        why = "FL has our script picked for the KeyLab 88 mk3 DAW input" if picked else "FL is running"
        return 2, [f"fl-uninstall refused: {why}.",
                   f'  First set that input back to "{ARTURIA_TITLE}" in Options > MIDI settings and close FL, so FL',
                   "  never starts looking for a script that is gone. --force removes it anyway."]
    if picked or running:
        lines.append(f'Before FL next starts, set the KeyLab 88 mk3 DAW input back to "{ARTURIA_TITLE}" in MIDI'
                     f" settings (FL keeps a loaded script running until then).")
    if dry_run:
        for p in ours + cached:
            lines.append(f"dry run: would remove {p}")
        if cache.is_dir():
            lines.append(f"dry run: would remove the folder {cache}")
        lines.append(f"dry run: would remove the folder {target}; nothing else is touched")
        return 0, lines
    for p in ours + cached:
        p.unlink()
    if cache.is_dir():
        os.rmdir(cache)
    os.rmdir(target)
    lines.append(f"removed {target} ({len(ours) + len(cached)} file(s)); Arturia's folder and everything else untouched")
    ini = hw / (FOLDER_NAME + ".ini")
    if ini.exists():
        lines.append(f"left in place: {ini} (FL's own bookkeeping file, not ours to delete)")
    return 0, lines


def status(hw: pathlib.Path, source: pathlib.Path = SOURCE) -> Tuple[int, List[str]]:
    data = source.read_bytes()
    target = hw / FOLDER_NAME
    dest = target / SCRIPT_NAME
    lines = [f"repo script:  {source} (sha256 {_sha(data)[:12]})",
             f"Hardware dir: {hw}" + ("" if hw.is_dir() else "  (NOT FOUND)")]
    if dest.is_file():
        same = dest.read_bytes() == data
        lines.append(f"installed:    yes, {dest}")
        lines.append("same bytes:   " + ("yes" if same else
                                         f"NO (installed sha256 {_sha(dest.read_bytes())[:12]}); run fl-install"))
    else:
        lines.append(f"installed:    no ({dest} absent)")
    foreign = foreign_entries(target)
    if foreign:
        lines.append(f"foreign files in our folder: {', '.join(foreign)}")
    arturia = hw / ARTURIA_FOLDER
    lines.append(f"Arturia's script folder: {'present' if arturia.is_dir() else 'absent'} ({arturia}), never written")
    running = fl_running()
    lines.append("FL running:   " + {True: "yes", False: "no", None: "unknown"}[running])
    picks = daw_port_scripts()
    for version, port, script in picks:
        whose = "ours" if script == SCRIPT_TITLE else ("Arturia's" if script == ARTURIA_TITLE else "other")
        lines.append(f"{version}, {port}: script \"{script}\" ({whose}; as FL last saved it)")
    if not picks:
        lines.append("FL's saved choice for the KeyLab DAW input: not found")
    return 0, lines
