"""The contract files stay LF -- BYTES, and ASKED OF GIT (Rill's wish 3, 2026-10-31).

WHY THIS EXISTS. `.gitattributes` pins `eol=lf` for most of the tree, and docs/TROUBLESHOOTING.md 7
records what happens when it does not: a fresh `git worktree add` or a `git apply` writes CRLF, a
test that slices a file by BYTES (`src.indexOf("\\n}\\n")`) comes back -1, and the failure surfaces
far from its cause. The policy was written from a measurement; nothing MEASURED the policy. This
pin does, and it does it in the two ways that can actually disagree:

  1. THE BYTES ON DISK -- read as bytes, never through a line splitter. A grep under Git Bash on
     this machine reports a CRLF file as clean (TROUBLESHOOTING 7), so a text-mode check would be
     a pin that cannot fail.
  2. WHAT GIT WILL DO ON THE NEXT CHECKOUT -- `git check-attr eol`. A file that is LF today and
     unbound by `.gitattributes` drifts back to CRLF in the NEXT clone; that is the failure this
     half catches and the byte check cannot. Asking git rather than re-deriving the patterns from
     `.gitattributes` matters: the pin must test the POLICY IN FORCE, not a copy of its rules.

THE SCOPE IS NAMED, deliberately. These are the files that constrain how work is done or that git
itself executes -- the contracts. It is not "every text file": 8 *.bat and 4 *.cmd files are CRLF
ON PURPOSE (cmd.exe's parser expects it) and archive/artifacts are not contracts. The boundary is
stated here instead of being silently implied, because a gate that does not say what it excludes
reads as a gate over everything.

Run: py tests/test_the_contract_files_stay_lf.py   (or via pytest)
"""
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The contract files: how work is done, and what git executes.
CONTRACT_FILES = (
    # the standing method documents every seat is bound by
    "AGENTS.md",
    "docs/method-baseline-2026-07.md",
    "docs/ARCHITECTURE.md",
    "docs/TROUBLESHOOTING.md",
    # git's own policy files -- read by git, and by humans who think they are text
    ".gitattributes",
    ".gitignore",
    # the hooks git EXECUTES: a CRLF here is `bad interpreter: /bin/sh^M`
    "scripts/githooks/pre-commit",
    "scripts/githooks/commit-msg",
    "scripts/githooks/post-commit",
    "scripts/githooks/pre-push",
    # the panel's public manifest: served to the phone, read as text by a pin
    "arsenal/panel/web/manifest.webmanifest",
)

GIT = shutil.which("git")


def _bytes(rel):
    with open(os.path.join(ROOT, rel.replace("/", os.sep)), "rb") as fh:
        return fh.read()


def _eol_attr(rel):
    """What `.gitattributes` says git will check out for this path: 'lf', 'crlf', or 'unspecified'."""
    if not GIT:
        pytest.skip("git is not on PATH -- the policy half of this pin cannot be asked")
    out = subprocess.run([GIT, "-C", ROOT, "check-attr", "eol", "--", rel],
                         capture_output=True, text=True, check=False)
    assert out.returncode == 0, f"git check-attr failed for {rel}: {out.stderr}"
    # "<path>: eol: lf"  /  "<path>: eol: unspecified"
    value = out.stdout.rsplit(":", 1)[-1].strip()
    return value


# ------------------------------------------------------------------- 1. the bytes on disk today
def test_no_contract_file_carries_a_crlf_byte():
    offenders = {}
    for rel in CONTRACT_FILES:
        data = _bytes(rel)
        crlf = data.count(b"\r\n")
        if crlf:
            offenders[rel] = crlf
    assert not offenders, (
        "contract file(s) carry CRLF in THIS working tree: {}. A byte-slicing reader (the score "
        "and piano tests, and every shell that sources these hooks) fails on that far from the "
        "cause. Fix with: py -c \"...\\r\\n -> \\n on the file's bytes\", then `git status` -- the "
        "blob is already LF, so this is a working-tree repair, not a history rewrite."
        .format(offenders))


def test_every_contract_file_exists():
    """A renamed or deleted contract file must fail HERE, not disappear from the pin's field of
    view -- the same absence-is-not-clean rule the checkers enforce."""
    missing = [rel for rel in CONTRACT_FILES if not os.path.isfile(os.path.join(ROOT, rel))]
    assert not missing, f"contract file(s) named in this pin do not exist: {missing}"


# ------------------------------------------- 2. what git will do in the next clone (the policy)
def test_gitattributes_pins_lf_for_every_contract_file():
    """The half that survives a fresh clone: an LF file with no policy drifts back to CRLF."""
    unbound = {}
    for rel in CONTRACT_FILES:
        value = _eol_attr(rel)
        if value != "lf":
            unbound[rel] = value
    assert not unbound, (
        "`.gitattributes` does not pin eol=lf for these contract files: {}. They are LF today by "
        "luck (the index is LF) and CRLF in the next `git worktree add` or `git apply` -- the "
        "2026-09-16 and 2026-09-17 incidents. Add a rule; the four hooks and *.webmanifest are "
        "named in .gitattributes because no pattern above reaches them."
        .format(unbound))


def test_the_pin_itself_is_bound_by_the_policy():
    """If the pin is exempt from the policy it enforces, a clone can break the pin by accident."""
    assert _eol_attr("tests/test_the_contract_files_stay_lf.py") == "lf"


# -------------------------------------------------------------------------------- 3. the boundary
def test_the_deliberate_crlf_exception_is_still_deliberate():
    """*.bat/*.cmd stay CRLF (`cmd.exe`'s parser). If this ever reads 'lf', someone applied a
    blanket rule and broke batch parsing -- a silent, remote, Windows-only failure."""
    assert _eol_attr("arsenal/tools/tiktok-ready.cmd") == "crlf", (
        "the batch exception in .gitattributes was lost: cmd.exe mis-parses LF-only batch files "
        "around labels and GOTO")
    assert _eol_attr("scripts/githooks/pre-commit") == "lf", (
        "the git hooks are NOT the batch exception -- they run under git's own sh")


def main():
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok    {name}")
            except AssertionError as exc:
                failures.append(name)
                print(f"  FAIL  {name}: {exc}")
    print("\nALL CONTRACT-FILE PINS PASSED" if not failures else f"\n{len(failures)} FAILURE(S)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
