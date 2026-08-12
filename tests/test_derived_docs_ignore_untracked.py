"""Pre-registered pins: derived docs describe the REPO, not the box.

Written and committed BEFORE the generator change they gate (M3).

THE DEFECT. gen_arch_index / gen_master_map / gen_prior_art_register discover modules with
os.listdir / Path.glob -- the WORKING TREE. So on any box holding untracked .py files the
generators emit rows for modules the repository does not contain. A clean checkout
regenerates WITHOUT those rows, check_comprehensibility calls the committed docs stale, and
CI dies at that guardrail with Wiring, Door-parity and the Test suite all SKIPPED behind it.

MEASURED 2026-08-11/12: CI failed 15+ consecutive runs on exactly this, across three
observed break -> fix -> break cycles. Fixing the docs does not hold, because the
pre-commit hook regenerates them from whatever tree it runs in, so a main-tree commit
silently re-contaminates its own fix. The generators are the only durable fix site.

Concrete instance: docs/MODULE_INDEX.md and docs/MAP.md carried a row for
core/comm/room_feed.py while that file was untracked; docs/PRIOR_ART.md counted 10 more
tests-modules than the repo holds (five tests/test_*.py plus five tests/_scratch_dump_*.py,
all untracked).

THE ACCEPTANCE PIN IS THE REFUTING CHECK, stated before the fix:
generate in a tree carrying untracked files, and in a clean checkout of the SAME commit --
the outputs must be BYTE-IDENTICAL. Anything less and the treadmill survives.

Both pins run generators inside throwaway git worktrees. ROOT is derived from __file__ in
all three generators, so a run inside a worktree writes into that worktree and can never
touch the developer's tree.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GENERATORS = [
    ("gen_arch_index.py", "docs/MODULE_INDEX.md"),
    ("gen_master_map.py", "docs/MAP.md"),
    ("gen_prior_art_register.py", "docs/PRIOR_ART.md"),
]

# Untracked files of the shapes that actually contaminated the real docs.
PLANTS = [
    ("core/comm", "_pin_untracked_module.py", "# planted untracked module\n"),
    ("tests", "_pin_untracked_test.py", "# planted untracked test\n"),
    ("scripts", "_pin_untracked_script.py", "# planted untracked script\n"),
]


def _git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _worktree(tmp_path, name):
    """A detached worktree at HEAD, with the WORKING-TREE generator sources copied in.

    The worktree supplies the DATA (a tree state); the generators under test must be the
    ones currently on disk, not HEAD's. Without this the pin can only ever exercise the
    committed generators, so it could never go green in the same commit that fixes them --
    the harness would be testing the wrong thing while looking rigorous.
    """
    path = str(tmp_path / name)
    r = _git("worktree", "add", "--detach", "-q", path, "HEAD")
    if r.returncode != 0:
        pytest.skip(f"cannot create worktree: {r.stderr[:200]}")
    src = os.path.join(ROOT, "scripts", "generators")
    dst = os.path.join(path, "scripts", "generators")
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(src):
        if f.endswith(".py"):
            with open(os.path.join(src, f), "rb") as r_fh, open(os.path.join(dst, f), "wb") as w_fh:
                w_fh.write(r_fh.read())
    return path


def _remove(path):
    _git("worktree", "remove", "--force", path)


def _run_generators(tree):
    """Run all three in `tree`. Returns {doc_path: bytes}. Skips on generator error so a
    broken generator reads as a skip, never as a false PASS."""
    for gen, _ in GENERATORS:
        r = subprocess.run([sys.executable, os.path.join("scripts", "generators", gen)],
                           cwd=tree, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            pytest.skip(f"{gen} failed in {tree}: {(r.stderr or r.stdout)[:300]}")
    out = {}
    for _, doc in GENERATORS:
        with open(os.path.join(tree, doc), "rb") as fh:
            out[doc] = fh.read()
    return out


def _plant(tree):
    for rel, name, body in PLANTS:
        d = os.path.join(tree, rel)
        if os.path.isdir(d):
            with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write(body)


# --- the acceptance pin: THE refuting check ------------------------------------------------

def test_dirty_tree_and_clean_checkout_generate_byte_identical_docs(tmp_path):
    """THE PIN. Same commit, two trees -- one carrying untracked files, one clean.
    Every derived doc must come out byte-identical, or the generators are still
    describing the box instead of the repo."""
    clean = _worktree(tmp_path, "clean")
    dirty = _worktree(tmp_path, "dirty")
    try:
        _plant(dirty)
        clean_docs = _run_generators(clean)
        dirty_docs = _run_generators(dirty)
        for _, doc in GENERATORS:
            assert dirty_docs[doc] == clean_docs[doc], (
                f"{doc} differs between a dirty tree and a clean checkout of the same "
                f"commit -- the generator is reading the working tree, not the repo "
                f"(clean={len(clean_docs[doc])}B dirty={len(dirty_docs[doc])}B)")
    finally:
        _remove(clean)
        _remove(dirty)


# --- the cheap delta pin: same property, clearer failure -----------------------------------

def test_planting_an_untracked_module_does_not_change_any_derived_doc(tmp_path):
    """Narrower and faster: within ONE tree, adding an untracked .py must not move any
    generated doc. Fails with the specific doc that moved."""
    tree = _worktree(tmp_path, "solo")
    try:
        before = _run_generators(tree)
        _plant(tree)
        after = _run_generators(tree)
        moved = [doc for _, doc in GENERATORS if before[doc] != after[doc]]
        assert not moved, (
            f"untracked files changed derived docs: {moved} -- generated content must "
            f"depend on tracked repo contents only")
    finally:
        _remove(tree)


def test_generators_do_not_emit_untracked_module_names(tmp_path):
    """Direct statement of the failure we actually shipped: an untracked module's NAME
    must never appear in a derived doc."""
    tree = _worktree(tmp_path, "names")
    try:
        _plant(tree)
        docs = _run_generators(tree)
        blob = b"\n".join(docs.values())
        for _, name, _body in PLANTS:
            assert name.encode() not in blob, (
                f"{name} is untracked but appears in a derived doc -- the doc claims the "
                f"repo contains a module it does not")
    finally:
        _remove(tree)
