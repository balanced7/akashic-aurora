"""The licence firewall for the blind tracker pair (arsenal/keylab/beat_*.py), agreed with Heimdall 2026-10-22.

A clean tracker may import only the standard library, numpy and scipy. Nothing GPL/AGPL/non-commercial (aubio,
BTrack, essentia, TempoCNN, madmom's models), nothing heavier, and nothing that touches the KeyLab port. The
check reads the source (AST), so it holds even for a file that has never run. When no beat_*.py exists yet the
pin is trivially green, and the probe test proves the scanner would catch a violation.

Round 2's revision (reviewers, 2026-10-23) closes the doors a tracker could use to reach PAST the audio it is fed:
another contestant's module, the bench's ground truth, a file on disk, a subprocess or the network. In beat_*.py
these are banned outright: importlib, __import__, sys.modules, open(), os / pathlib / io / shutil (file access),
gc, inspect, subprocess, socket, ctypes; and with them the obvious ways around the list (builtins, eval, exec,
compile, globals(), the dunder escapes, numpy's and scipy's own file readers and writers).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

KEYLAB = Path(__file__).resolve().parents[1] / "arsenal" / "keylab"
ALLOWED_THIRD_PARTY = {"numpy", "scipy"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}

# modules a tracker may not import at all, even though they are stdlib: the ten the review named, then the other
# stdlib doors to the same places (loading code, reading files, spawning processes, the network)
BANNED_MODULES = {"importlib", "os", "pathlib", "io", "shutil", "gc", "inspect", "subprocess", "socket", "ctypes",
                  "builtins", "runpy", "pkgutil", "zipimport", "code", "codeop", "pdb", "trace",
                  "tempfile", "glob", "fileinput", "linecache", "tokenize", "codecs", "mmap", "pickle", "marshal",
                  "shelve", "dbm", "sqlite3", "zipfile", "tarfile", "gzip", "bz2", "lzma",
                  "multiprocessing", "concurrent", "urllib", "http", "ftplib", "ssl", "asyncio", "select",
                  "selectors"}
BANNED_SUBMODULES = {"scipy.io", "numpy.lib.format", "numpy.lib.npyio", "numpy.ctypeslib", "scipy.datasets"}
BANNED_CALLS = {"open", "__import__", "eval", "exec", "compile", "globals", "breakpoint"}
BANNED_NAMES = {"__builtins__", "__loader__", "__spec__"}
BANNED_ATTRS = {"__subclasses__", "__globals__", "__builtins__", "__code__", "__closure__", "__import__",
                "__loader__", "__spec__", "f_globals", "f_locals", "f_back", "gi_frame", "tb_frame"}
NUMPY_FILE_ATTRS = {"load", "save", "savez", "savez_compressed", "fromfile", "loadtxt", "savetxt", "genfromtxt",
                    "memmap", "fromregex", "DataSource", "ctypeslib", "lib"}
ANY_FILE_ATTRS = {"tofile", "dump"}                           # ndarray.tofile / ndarray.dump write to disk


def imported_roots(src: str) -> set:
    roots = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            roots |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            if node.level:                                    # relative import = something inside arsenal.keylab
                roots.add("." + (node.module or ""))
            elif node.module:
                roots.add(node.module.split(".")[0])
    return roots


def violations(src: str) -> set:
    return {r for r in imported_roots(src) if r not in STDLIB and r not in ALLOWED_THIRD_PARTY}


def reach_violations(src: str) -> set:
    """Everything in `src` that reaches past the audio: banned imports, calls, names and attributes. Each finding
    is a short label (e.g. 'import os', 'call open', 'sys.modules', 'np.load', 'attr __globals__')."""
    tree = ast.parse(src)
    found = set()
    numpy_names, sys_names = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                full, root = a.name, a.name.split(".")[0]
                bound = a.asname or root
                if root in BANNED_MODULES:
                    found.add(f"import {root}")
                if any(full == b or full.startswith(b + ".") for b in BANNED_SUBMODULES):
                    found.add(f"import {full}")
                if root == "numpy":
                    numpy_names.add(bound)
                if root == "sys":
                    sys_names.add(bound)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            root = node.module.split(".")[0]
            if root in BANNED_MODULES:
                found.add(f"import {root}")
            for b in BANNED_SUBMODULES:
                for a in node.names:
                    if node.module == b or node.module.startswith(b + ".") or f"{node.module}.{a.name}" == b:
                        found.add(f"import {b}")
            if root == "sys" and any(a.name == "modules" for a in node.names):
                found.add("sys.modules")
            if root == "numpy" and any(a.name in NUMPY_FILE_ATTRS for a in node.names):
                found.add("numpy file io")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
            found.add(f"call {node.func.id}")
        elif isinstance(node, ast.Name) and node.id in (BANNED_NAMES | BANNED_CALLS):
            found.add(f"name {node.id}")
        elif isinstance(node, ast.Attribute):
            base = node.value.id if isinstance(node.value, ast.Name) else None
            if node.attr in BANNED_ATTRS:
                found.add(f"attr {node.attr}")
            if node.attr == "modules" and base in sys_names | {"sys"}:
                found.add("sys.modules")
            if base in numpy_names and node.attr in NUMPY_FILE_ATTRS:
                found.add(f"np.{node.attr}")
            if node.attr in ANY_FILE_ATTRS:
                found.add(f"attr {node.attr}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in BANNED_ATTRS:
            found.add(f"string {node.value}")                 # getattr(x, "__globals__") and friends
    return found


def test_beat_trackers_import_only_stdlib_numpy_scipy():
    for path in sorted(KEYLAB.glob("beat_*.py")):
        bad = violations(path.read_text(encoding="utf-8"))
        assert not bad, f"{path.name} imports {sorted(bad)}: clean trackers may use stdlib, numpy and scipy only"


def test_beat_trackers_cannot_reach_past_the_audio():
    """No contestant may load modules dynamically, read sys.modules, open a file, walk the heap or the stack,
    spawn a process, open a socket or call into C: the only thing a tracker may know is the audio it is fed."""
    trackers = sorted(KEYLAB.glob("beat_*.py"))
    for path in trackers:
        bad = reach_violations(path.read_text(encoding="utf-8"))
        assert not bad, f"{path.name}: {sorted(bad)} -- a tracker may only see the audio it is fed"


def test_the_scanner_catches_every_forbidden_shape():
    probe = ("import aubio\nfrom madmom.features import beats\nfrom . import winmidi\nimport numpy as np\n"
             "def f():\n    import librosa\n")
    assert violations(probe) == {"aubio", "madmom", "librosa", "."}   # "." = any relative import into keylab
    assert violations("import numpy\nfrom scipy.signal import lfilter\nimport math\n") == set()


def test_the_reach_scanner_catches_every_banned_door():
    probes = {
        "import importlib\n": "import importlib",
        "from importlib import import_module\n": "import importlib",
        "m = __import__('arsenal.keylab.beatbench')\n": "call __import__",
        "import sys\nx = sys.modules['arsenal.keylab.beatbench']\n": "sys.modules",
        "import sys as s\nx = s.modules\n": "sys.modules",
        "from sys import modules\n": "sys.modules",
        "x = open('truth.json').read()\n": "call open",
        "import os\n": "import os",
        "import os.path\n": "import os",
        "from pathlib import Path\n": "import pathlib",
        "import io\n": "import io",
        "import shutil\n": "import shutil",
        "import gc\nx = gc.get_objects()\n": "import gc",
        "import inspect\n": "import inspect",
        "import subprocess\n": "import subprocess",
        "import socket\n": "import socket",
        "import ctypes\n": "import ctypes",
        "import builtins\n": "import builtins",
        "x = eval('1')\n": "call eval",
        "exec('import os')\n": "call exec",
        "g = globals()\n": "call globals",
        "x = (1).__class__.__base__.__subclasses__()\n": "attr __subclasses__",
        "def f():\n    return f.__globals__\n": "attr __globals__",
        "x = getattr(len, '__globals__', None)\n": "string __globals__",
        "b = __builtins__\n": "name __builtins__",
        "import numpy as np\nx = np.load('a.npy')\n": "np.load",
        "import numpy\nnumpy.save('a', 1)\n": "np.save",
        "from numpy import fromfile\n": "numpy file io",
        "import numpy as np\nnp.zeros(3).tofile('a')\n": "attr tofile",
        "from scipy.io import wavfile\n": "import scipy.io",
        "import scipy.io\n": "import scipy.io",
        "from scipy import io\n": "import scipy.io",
    }
    for src, label in probes.items():
        assert label in reach_violations(src), f"the scanner missed {label!r} in {src!r}"
    clean = ("from __future__ import annotations\nimport math\nfrom collections import deque\n"
             "from typing import List, Optional\nimport numpy as np\nfrom scipy.signal import lfilter\n"
             "class Tracker:\n    def __init__(self, rate, hop, seed_bpm=None):\n        self.x = np.zeros(4)\n"
             "    def feed(self, block):\n        return [float(np.mean(block))]\n")
    assert reach_violations(clean) == set()
