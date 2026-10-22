"""HARD BOUNDARY: arsenal/keylab/tempo* must never import winmidi, protocol or ledframe.

The T4 beat/BPM lane is pure analysis. Nothing in it touches the KeyLab port. The hub (owned
elsewhere) subscribes to beat events; the port is spoken only by winmidi/protocol/ledframe. This
test scans the tempo module's AST and refuses ANY import of those three names -- top-level OR
inside a function -- so the boundary is a machine check, not a promise made in a docstring.

Also pins the GPL discipline: aubio must only be imported inside a function (never module top),
because the licence call is still open.
"""
from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN = {"winmidi", "protocol", "ledframe"}


def _imports_of(tree: ast.AST):
    """Yield every (module-dotted-name) imported anywhere in the tree, top-level or nested."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            # from . import winmidi  ->  module='' level relative; capture the imported names too
            if node.module:
                yield node.module
            for alias in node.names:
                yield alias.name


def _module_trees():
    root = Path(__file__).resolve().parents[1]
    tempo_dir = root / "arsenal" / "keylab"
    trees = {}
    for p in sorted(tempo_dir.glob("tempo*.py")):
        trees[p.name] = ast.parse(p.read_text(encoding="utf-8"))
    return trees


def test_tempo_boundary_no_port_imports():
    """No tempo* module imports winmidi/protocol/ledframe, in any scope."""
    trees = _module_trees()
    assert trees, "expected at least one arsenal/keylab/tempo*.py module"
    for name, tree in trees.items():
        for imported in _imports_of(tree):
            # a dotted import like 'arsenal.keylab.protocol' -> last segment is the guilty module
            last = imported.split(".")[-1]
            assert last not in FORBIDDEN, (
                f"{name} imports forbidden port module {imported!r}; "
                f"the T4 lane must not touch the KeyLab port"
            )


def test_tempo_boundary_aubio_is_lazy():
    """aubio may only be imported inside a function body, never at module top level."""
    trees = _module_trees()
    for name, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in getattr(node, "names", [])]
                if "aubio" in names or (getattr(node, "module", None) or "").endswith("aubio"):
                    # the import node must have a FunctionDef ancestor
                    for anc in ast.walk(tree):
                        if isinstance(anc, ast.FunctionDef) and _contains(anc, node):
                            break
                    else:
                        raise AssertionError(
                            f"{name} imports aubio at module top level; "
                            f"aubio (GPLv3+) must be imported lazily inside a function"
                        )


def _contains(outer: ast.AST, inner: ast.AST) -> bool:
    """True if inner is a descendant node of outer."""
    return any(inner is n for n in ast.walk(outer))


def test_tempo_package_reimports_cleanly():
    """The tempo module imports cleanly with no heavy deps present (aubio/numpy not yet imported)."""
    import importlib
    import arsenal.keylab.tempo as tempo  # noqa: F401  (proves the import itself is light)
    assert hasattr(tempo, "fold_to_band")
    assert hasattr(tempo, "snap_to_octave")
    assert hasattr(tempo, "fuse_bpm")
    assert hasattr(tempo, "BeatTracker")
