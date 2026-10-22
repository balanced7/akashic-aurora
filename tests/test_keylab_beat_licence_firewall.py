"""The licence firewall for the blind tracker pair (arsenal/keylab/beat_*.py), agreed with Heimdall 2026-10-22.

A clean tracker may import only the standard library, numpy and scipy. Nothing GPL/AGPL/non-commercial (aubio,
BTrack, essentia, TempoCNN, madmom's models), nothing heavier, and nothing that touches the KeyLab port. The
check reads the source (AST), so it holds even for a file that has never run. When no beat_*.py exists yet the
pin is trivially green, and the probe test proves the scanner would catch a violation.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

KEYLAB = Path(__file__).resolve().parents[1] / "arsenal" / "keylab"
ALLOWED_THIRD_PARTY = {"numpy", "scipy"}
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"__future__"}


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


def test_beat_trackers_import_only_stdlib_numpy_scipy():
    for path in sorted(KEYLAB.glob("beat_*.py")):
        bad = violations(path.read_text(encoding="utf-8"))
        assert not bad, f"{path.name} imports {sorted(bad)}: clean trackers may use stdlib, numpy and scipy only"


def test_the_scanner_catches_every_forbidden_shape():
    probe = ("import aubio\nfrom madmom.features import beats\nfrom . import winmidi\nimport numpy as np\n"
             "def f():\n    import librosa\n")
    assert violations(probe) == {"aubio", "madmom", "librosa", "."}   # "." = any relative import into keylab
    assert violations("import numpy\nfrom scipy.signal import lfilter\nimport math\n") == set()
