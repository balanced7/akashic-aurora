"""RED-first pins: the private-plane MESSAGE guard runs at git's commit-msg stage (dd0c36b406).

THE DEFECT. scripts/githooks/pre_commit.py scanned the commit message by reading git's
message file from the PRE-COMMIT stage. git writes that file AFTER pre-commit runs. Receipt
on this machine (git 2.53.0.windows.2, throwaway repo with printing hooks): first commit ->
pre-commit sees the file ABSENT while commit-msg's argv[1] holds the first message; second
commit -> pre-commit sees the FIRST message while commit-msg's argv[1] holds the second. So
the guard judged commit N by commit N-1's message: a marker-naming message passed its own
commit and the clean commit after it was refused (the defer's two failure modes). In a
linked worktree `.git` is a file, so the read failed silently and the scan never ran at all.

THE FIX. git's commit-msg stage receives the LIVE message path as argv[1]; the scan moves
there (scripts/githooks/commit-msg -> scripts/githooks/commit_msg.py). pre-commit keeps the
staged-FILE report. `git commit --no-verify` skips both stages, so the sanctioned emergency
bypass is unchanged.

  P1  a message naming a marker is refused, and the refusal names the marker and the remedy
  P2  a clean message passes silently; the comment lines and scissors tail git strips before
      recording the message are not scanned (a guard that fires on healthy commits gets
      routed around)
  P3  pre_commit.py no longer reads the stale message file (regression pin)
  P4  under REAL git stage order, with the tracked shim and module verbatim: the marker
      commit is refused AT ITS OWN COMMIT and nothing lands; a --no-verify'd marker-naming
      predecessor does not poison the clean commit after it (the defer's literal acceptance)
  P4b the same from a linked worktree, where git hands an absolute path into .git/worktrees/
  P5  the tracked shim delegates argv[1] to the module; the installer knows every stage
  P6  a guard that cannot run fails OPEN and says so; a finding fails CLOSED even if the
      refusal cannot be printed

Run: py -m pytest tests/test_commit_msg_hook_pins.py -q -p no:cacheprovider
"""
from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

HOOKS = ROOT / "scripts" / "githooks"
# SYNTHETIC identifiers on purpose (same shape as tests/test_private_plane_guard.py): a test
# that embeds a genuine private identifier is itself a leak vector.
MARKER = "synthetic-sample-dossier"


@pytest.fixture()
def plane(tmp_path):
    """A private plane holding one assessment, mirroring the live shape."""
    priv = tmp_path / "private" / "assessments"
    priv.mkdir(parents=True)
    (priv / f"20260101_{MARKER}_ff00aa.md").write_text(
        f"# A synthetic dossier\n\nname: {MARKER}\nfixture body, no real content.\n",
        encoding="utf-8")
    (priv / "atoms-private.jsonl").write_text(
        '{"id": "art_20260101_%s_ff00aa", "title": "%s"}\n' % (MARKER, MARKER),
        encoding="utf-8")
    return tmp_path


def _hook():
    from scripts.githooks import commit_msg
    return commit_msg


def _msgfile(tmp_path, text):
    p = tmp_path / "MSG"
    p.write_text(text, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------- P1: refuses, teaches
def test_p1_a_message_naming_a_marker_is_refused_and_teaches(plane, tmp_path, capsys):
    rc = _hook().main(["commit_msg.py", _msgfile(tmp_path, f"docs: index the {MARKER} atom\n")],
                      root=plane)
    err = capsys.readouterr().err
    assert rc == 1, "a marker-naming commit message must be refused at ITS OWN commit"
    assert "commit-msg BLOCKED" in err
    assert MARKER in err, "the refusal must name the marker it found"
    assert "commit message" in err, "the refusal must say WHERE the marker is (the message, not a file)"
    assert "--no-verify" in err, (
        "the sanctioned bypass is named, so it is used out loud rather than discovered")


# ---------------------------------------------------------------- P2: clean passes
def test_p2_a_clean_message_passes_silently(plane, tmp_path, capsys):
    rc = _hook().main(
        ["commit_msg.py", _msgfile(tmp_path, "fix: tighten the door probe timeout\n")],
        root=plane)
    assert rc == 0
    assert capsys.readouterr().err == "", (
        "a clean commit must not be nagged -- noise is what trains --no-verify")


def test_p2b_comment_lines_git_strips_are_not_scanned(plane, tmp_path):
    """git's status template lists branch names and paths under '#'. git removes those lines
    before the message is recorded, so they can never leak -- refusing on them would fire on
    healthy commits."""
    text = (f"fix: a clean subject\n\n# On branch feature/{MARKER}\n"
            f"# Changes to be committed:\n#\tmodified:   private/{MARKER}.md\n")
    assert _hook().main(["commit_msg.py", _msgfile(tmp_path, text)], root=plane) == 0


def test_p2c_the_scissors_tail_is_not_scanned(plane, tmp_path):
    """`git commit -v` appends the staged diff below a scissors line; git discards it."""
    text = ("fix: a clean subject\n"
            "# ------------------------ >8 ------------------------\n"
            f"+++ b/private/assessments/20260101_{MARKER}_ff00aa.md\n")
    assert _hook().main(["commit_msg.py", _msgfile(tmp_path, text)], root=plane) == 0


def test_p2d_a_marker_after_a_comment_line_is_still_caught(plane, tmp_path):
    """Stripping comments must not swallow the real message that follows them."""
    text = f"# a leading comment\nrelease notes for {MARKER}\n"
    assert _hook().main(["commit_msg.py", _msgfile(tmp_path, text)], root=plane) == 1


# ---------------------------------------------------------------- P3: the stale read is gone
def test_p3_pre_commit_no_longer_reads_the_message_file_git_has_not_written_yet():
    from scripts.githooks import pre_commit
    assert "COMMIT_EDITMSG" not in inspect.getsource(pre_commit), (
        "pre-commit reads git's message file before git writes it for THIS commit, so it "
        "scans the PREVIOUS commit's message (dd0c36b406); the message guard belongs to the "
        "commit-msg stage, which is handed the live path")


# ---------------------------------------------------------------- P4: real git stage order
def _git(repo, *args, env, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                       env=env, timeout=120)
    if check and r.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed rc={r.returncode}\n{r.stdout}{r.stderr}")
    return r


def _subjects(repo, env):
    """Landed commit subjects, newest first; [] on an unborn branch."""
    r = _git(repo, "log", "--format=%s", env=env, check=False)
    if r.returncode != 0:
        return []
    return [ln for ln in r.stdout.splitlines() if ln]


def _hermetic_repo(tmp_path, plane):
    """A throwaway repo whose ONLY hook is the tracked commit-msg shim, copied VERBATIM,
    driving the tracked module, copied verbatim to where the shim resolves it (relative to
    the worktree root -- exactly how git runs it). The pre-commit hook is deliberately
    absent: its generators and ratchet belong to the real repo, not to this one."""
    shim = HOOKS / "commit-msg"
    module = HOOKS / "commit_msg.py"
    assert shim.is_file(), (
        "scripts/githooks/commit-msg is missing: the message guard has no stage to run in")
    assert module.is_file(), "scripts/githooks/commit_msg.py is missing"
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    shutil.copy(shim, hooks / "commit-msg")
    repo = tmp_path / "repo"
    (repo / "scripts" / "githooks").mkdir(parents=True)
    shutil.copy(module, repo / "scripts" / "githooks" / "commit_msg.py")

    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    (tmp_path / "gitconfig-empty").write_text("", encoding="utf-8")
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(tmp_path / "gitconfig-empty"),
        # the copied module must still find core.trust.private_plane -- in THIS checkout
        "PYTHONPATH": os.pathsep.join(
            p for p in (str(ROOT), env.get("PYTHONPATH", "")) if p),
        # and derive its markers from the synthetic plane, never this repo's real one
        "AKASHIC_PRIVATE_PLANE_ROOT": str(plane),
    })
    _git(repo, "init", "-q", "-b", "main", env=env)
    _git(repo, "config", "user.name", "pin", env=env)
    _git(repo, "config", "user.email", "pin@example.invalid", env=env)
    _git(repo, "config", "core.hooksPath", str(hooks).replace("\\", "/"), env=env)
    _git(repo, "add", "-A", env=env)
    # the root commit goes THROUGH the hook: a clean message under real git must pass
    _git(repo, "commit", "-q", "-m", "root: hook module under test", env=env)
    return repo, env


def test_p4_git_refuses_the_marker_at_its_own_commit_and_passes_the_clean_successor(
        plane, tmp_path):
    repo, env = _hermetic_repo(tmp_path, plane)

    a = _git(repo, "commit", "-q", "--allow-empty", "-m", f"note the {MARKER} atom",
             env=env, check=False)
    assert a.returncode != 0, (
        "a marker-naming message must be refused AT ITS OWN commit -- at HEAD it passed, "
        "because pre-commit scanned the previous one:\n" + a.stdout + a.stderr)
    assert "commit-msg BLOCKED" in a.stderr and MARKER in a.stderr, a.stderr
    assert "Traceback" not in a.stderr, "refused by the guard, not by a crash"
    assert _subjects(repo, env) == ["root: hook module under test"], "nothing may land"

    # THE DEFER'S LITERAL ACCEPTANCE. A marker-naming predecessor lands via the sanctioned
    # bypass (a confession naming what it bypassed for is the live case); the clean commit
    # after it must pass. At HEAD it was refused, because pre-commit read the predecessor's
    # message and called it this commit's.
    _git(repo, "commit", "-q", "--allow-empty", "--no-verify",
         "-m", f"bypass: confessed, named {MARKER}", env=env)
    b = _git(repo, "commit", "-q", "--allow-empty",
             "-m", "clean follow-up: nothing private named", env=env, check=False)
    assert b.returncode == 0, (
        "a clean message after a marker-naming predecessor was refused -- the guard is "
        "reading the PREVIOUS message:\n" + b.stdout + b.stderr)
    assert _subjects(repo, env) == ["clean follow-up: nothing private named",
                                    f"bypass: confessed, named {MARKER}",
                                    "root: hook module under test"]


def test_p4b_a_linked_worktree_hands_the_guard_a_path_it_can_open(plane, tmp_path):
    """In a linked worktree `.git` is a FILE -- the old read failed there and the scan
    silently never ran. git hands commit-msg an absolute path into .git/worktrees/<name>/;
    the guard must open it, refuse the marker, then pass the clean successor."""
    repo, env = _hermetic_repo(tmp_path, plane)
    wt = tmp_path / "wt"
    _git(repo, "worktree", "add", "-q", str(wt), "-b", "side", env=env)
    a = _git(wt, "commit", "-q", "--allow-empty", "-m", f"wt: mentions {MARKER}",
             env=env, check=False)
    assert a.returncode != 0, a.stdout + a.stderr
    assert "commit-msg BLOCKED" in a.stderr and "Traceback" not in a.stderr, a.stderr
    b = _git(wt, "commit", "-q", "--allow-empty", "-m", "wt: clean", env=env, check=False)
    assert b.returncode == 0, b.stdout + b.stderr
    assert _subjects(wt, env)[0] == "wt: clean"


# ---------------------------------------------------------------- P5: wired, not just built
def test_p5_the_tracked_shim_delegates_the_live_message_path():
    shim = HOOKS / "commit-msg"
    assert shim.is_file(), (
        "no commit-msg hook is tracked: the message guard has no stage to run in")
    # splitlines() tolerates the CRLF working copy core.autocrlf=true produces here
    lines = shim.read_text(encoding="utf-8", errors="replace").splitlines()
    assert lines and lines[0] == "#!/bin/sh", (
        "git runs hooks through sh; the sibling shims do the same")
    body = "\n".join(lines)
    assert "scripts/githooks/commit_msg.py" in body and '"$1"' in body, (
        "the shim must hand git's argv[1] -- the LIVE message path -- to the module")


def test_p5b_the_installer_knows_every_stage(tmp_path):
    from scripts.githooks import install_git_hooks as ih
    assert "commit-msg" in ih.HOOKS
    assert ih.missing_hooks() == [], (
        "a hook the installer expects is absent from scripts/githooks")
    assert ih.missing_hooks(str(tmp_path)) == list(ih.HOOKS), (
        "an empty hooks dir must read as ALL missing, never as installed")


# ---------------------------------------------------------------- P6: fail-open, loudly
def test_p6_a_guard_that_cannot_run_fails_open_and_says_so(tmp_path, capsys):
    rc = _hook().main(["commit_msg.py", str(tmp_path / "no-such-message-file")])
    err = capsys.readouterr().err
    assert rc == 0, "a broken guard must never brick every commit"
    assert "WARNING" in err and "not protecting" in err, "absence must never look like success"


def test_p6b_no_message_path_fails_open_loudly(capsys):
    rc = _hook().main(["commit_msg.py"])
    assert rc == 0 and "WARNING" in capsys.readouterr().err


def test_p6c_a_finding_fails_closed_even_when_the_refusal_cannot_be_printed(
        plane, tmp_path, monkeypatch):
    class _Dead:
        def write(self, *_a, **_k):
            raise OSError("stderr is gone")
    monkeypatch.setattr(sys, "stderr", _Dead())
    rc = _hook().main(["commit_msg.py", _msgfile(tmp_path, f"names {MARKER}\n")], root=plane)
    assert rc == 1, "the decision must not depend on the console: refuse first, explain if you can"
