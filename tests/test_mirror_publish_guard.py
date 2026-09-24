"""Publish-door pins for scripts/mirror.py: nothing reaches the public remote by accident.

THE INCIDENT (2026-09-15, about 14:24 EDT, commit 97b85ecd). The deepseek seat (Heimdall), running
unattended, ran `py scripts/mirror.py "count-plus-lines" <path>` believing it counted a file's lines.
mirror.py read the positional arguments as message + paths, committed a stale .patch file and a
docs/PHYSICS.md stamp as "count-plus-lines", and pushed to origin/master of the PUBLIC repo
balanced7/akashic-aurora. The push also published every unpushed local commit since 2026-09-13
(e127e263..97b85ecd). Seats' own mutating git verbs are refused under unattended exec; mirror.py
bypassed that because it runs git itself.

What must hold now:
  D1  positional arguments alone never commit or push: help plus the plan, exit 2 (incident argv replayed)
  D2  --help commits nothing (2026-08-02: `mirror.py --help` once committed the shared index)
  C1  --commit commits locally and never pushes
  U1  any seat but claude, and any process inside the toolbox door, is refused (exit 3) before git is
      touched, even with --push --yes
  U2  the toolbox's mirror family stamps AKASHIC_SEAT_DOOR=toolbox, which mirror.py refuses
  P1  --push without --yes and without a terminal is refused before anything is committed (exit 5)
  P2  --push --yes publishes, lists the commit first, and authors it as the seat
  P3  unpushed commits by another author block the push (exit 4) unless --include-others
  P4  Daniel (no seat id) publishing his own commits is not blocked

Offline: a copy of mirror.py in a temp repo with a local bare origin, so the push leg runs for real
with no network and nowhere near the real remote.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_IDENTITY_VARS = ("AKASHIC_AGENT_ID", "AKASHIC_SEAT_DOOR", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
                  "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")


def _git(cwd, *args, env=None):
    r = subprocess.run(["git", *[str(a) for a in args]], cwd=str(cwd), env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, f"git {args} failed:\n{r.stdout}\n{r.stderr}"
    return r.stdout.strip()


def _env(seat=None, door=None, **extra):
    env = {k: v for k, v in os.environ.items() if k not in _IDENTITY_VARS}
    if seat:
        env["AKASHIC_AGENT_ID"] = seat
    if door:
        env["AKASHIC_SEAT_DOOR"] = door
    env.update(extra)
    return env


@pytest.fixture()
def pub_repo(tmp_path):
    """(work, bare): a work repo whose origin is a local bare repo, seed commit published."""
    work, bare = tmp_path / "work", tmp_path / "origin.git"
    work.mkdir()
    _git(work, "init", "-q")
    _git(work, "config", "user.email", "operator@test")
    _git(work, "config", "user.name", "operator")
    _git(work, "init", "-q", "--bare", bare)
    _git(work, "remote", "add", "origin", bare)
    (work / "scripts").mkdir()
    shutil.copy(os.path.join(REPO, "scripts", "mirror.py"), work / "scripts" / "mirror.py")
    (work / "seed.txt").write_text("seed\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "seed")
    _git(work, "push", "-q", "-u", "origin", _branch(work))
    return work, bare


def _branch(work):
    return _git(work, "rev-parse", "--abbrev-ref", "HEAD")


def _head(work):
    return _git(work, "rev-parse", "HEAD")


def _published(work, bare):
    return _git(bare, "rev-parse", _branch(work))


def _staged(work):
    return _git(work, "diff", "--cached", "--name-only").split()


def _commit_as(work, author, name, subject):
    """A local, unpushed commit authored by `author` (None = the repo's git config, i.e. Daniel)."""
    (work / name).write_text(subject + "\n")
    extra = {} if author is None else {"GIT_AUTHOR_NAME": author,
                                       "GIT_AUTHOR_EMAIL": f"{author}@akashic-aurora.local"}
    _git(work, "add", name)
    _git(work, "commit", "-q", "-m", subject, env=_env(**extra))


def _mirror(work, *args, seat="claude", door=None):
    return subprocess.run([sys.executable, "scripts/mirror.py", *args], cwd=str(work),
                          env=_env(seat, door), stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=120)


def test_d1_incident_argv_is_only_a_dry_run(pub_repo):
    """THE INCIDENT, replayed: `mirror.py "count-plus-lines" <path>` with an unpushed commit waiting."""
    work, bare = pub_repo
    _commit_as(work, "claude", "waiting.txt", "local work from 2026-09-13, not yet published")
    (work / "stale.patch").write_text("diff --git a/x b/x\n")
    head, published = _head(work), _published(work, bare)

    r = _mirror(work, "count-plus-lines", "stale.patch")

    assert r.returncode == 2, r.stdout + r.stderr
    assert "usage:" in r.stdout and "DRY RUN" in r.stdout
    assert "stale.patch" in r.stdout, "the plan names the paths it would stage"
    assert "local work from 2026-09-13" in r.stdout, "the plan names what --push would publish"
    assert _head(work) == head, "a dry run committed"
    assert _staged(work) == [], "a dry run staged"
    assert _published(work, bare) == published, "a dry run pushed"


def test_d2_help_commits_nothing(pub_repo):
    work, bare = pub_repo
    (work / "staged.txt").write_text("someone's staged work\n")
    _git(work, "add", "staged.txt")
    head = _head(work)

    r = _mirror(work, "--help")

    assert r.returncode == 0 and "PUBLISH door" in _flat(r.stdout)
    assert _head(work) == head


def test_c1_commit_flag_commits_locally_and_never_pushes(pub_repo):
    work, bare = pub_repo
    (work / "mine.txt").write_text("mine\n")
    published = _published(work, bare)

    r = _mirror(work, "mine only", "mine.txt", "--commit")

    assert r.returncode == 0, r.stdout + r.stderr
    assert _git(work, "log", "-1", "--format=%s|%an") == "mine only|claude"
    assert _published(work, bare) == published



def _flat(text):
    """Collapse whitespace before matching prose.

    These pins assert on the refusal BANNER, which is hand-wrapped prose. The banner wraps as
    "It does\\n  not count lines", so a literal `"does not count lines" in stdout` is False
    while the sentence is plainly present -- the pin failed on a line break, not on behaviour.
    Four parametrised cases failed that way on 2026-09-24 while the guard itself was working
    perfectly (exit 3, nothing staged, committed or pushed -- all still asserted below).

    Matching the MEANING rather than the byte layout also means a future rewording of the
    banner's line breaks cannot silently turn this pin red and cost someone an hour proving
    the door still works.
    """
    return " ".join((text or "").split())


@pytest.mark.parametrize("seat,door", [("deepseek", None), ("kimi", None),
                                       ("claude", "toolbox"), (None, "toolbox")])
def test_u1_other_seats_and_the_toolbox_door_are_refused(pub_repo, seat, door):
    work, bare = pub_repo
    _commit_as(work, "claude", "waiting.txt", "waiting")
    (work / "stale.patch").write_text("diff --git a/x b/x\n")
    head, published = _head(work), _published(work, bare)

    # The PUBLISH leg is unchanged: --push is refused for every seat but claude and for
    # any process inside the toolbox door (exit 3), before git is touched. (The plain
    # positional-args dry-run leg for commit-authorized seats is covered by test_u1b.)
    r = _mirror(work, "count-plus-lines", "stale.patch", "--push", "--yes", "--include-others",
                seat=seat, door=door)
    assert r.returncode == 3, r.stdout + r.stderr
    flat = _flat(r.stdout)
    assert "PUBLISH door" in flat and "does not count lines" in flat
    assert "Nothing was staged, committed or pushed" in flat
    assert _head(work) == head and _staged(work) == [] and _published(work, bare) == published


def test_u1b_commit_authorized_seat_commits_dry_run_without_flag(pub_repo):
    """The commit leg needs an intent flag. A commit-authorized seat (deepseek) running
    POSITIONAL args only (the incident argv shape) must NOT commit -- the dry-run/usage
    path returns exit 2, nothing staged/committed/pushed. This is the D1 guard, unchanged;
    the amendment only opens the --commit flag for these seats."""
    work, bare = pub_repo
    _commit_as(work, "claude", "waiting.txt", "waiting")
    (work / "stale.patch").write_text("diff --git a/x b/x\n")
    head, published = _head(work), _published(work, bare)
    r = _mirror(work, "count-plus-lines", "stale.patch", seat="deepseek", door=None)
    assert r.returncode == 2, r.stdout + r.stderr   # usage/dry-run, not a commit
    assert _head(work) == head and _staged(work) == [] and _published(work, bare) == published


def test_u2_toolbox_mirror_family_stamps_the_door_mirror_refuses():
    sys.path.insert(0, REPO)
    from core.comm.toolbox import ToolBox
    box = ToolBox(Path(REPO), allow_exec=True, trust=True, allow_secrets=False,
                  confirm=lambda _p: False, agent_id="deepseek")
    argv, env_extra, why = box._exec_family("py scripts/mirror.py count-plus-lines research/x.patch")
    assert why is None and env_extra.get("AKASHIC_SEAT_DOOR") == "toolbox"

    spec = importlib.util.spec_from_file_location("mirror_under_test", os.path.join(REPO, "scripts", "mirror.py"))
    mirror = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mirror)

    # COMMIT leg (push=False): a commit-authorized seat (deepseek) may commit locally even
    # through the toolbox door (the verified-caller path). Daniel and claude always may.
    # An UNKNOWN seat and the claude-inside-toolbox inherited-id case stay refused.
    assert mirror.runner_refusal({**env_extra, "AKASHIC_AGENT_ID": "deepseek"}, push=False) is None
    assert mirror.runner_refusal({"AKASHIC_AGENT_ID": "claude"}, push=False) is None
    assert mirror.runner_refusal({}, push=False) is None, "Daniel at his own terminal"
    assert mirror.runner_refusal({**env_extra, "AKASHIC_AGENT_ID": "claude"}, push=False) is not None, \
        "a claude id inside the toolbox door is inherited from a launcher (2026-07-21) and refused"
    assert mirror.runner_refusal({**env_extra, "AKASHIC_AGENT_ID": "unknown-seat"}, push=False) is not None

    # PUSH leg (push=True): unchanged -- the toolbox door is refused for EVERYONE, and only
    # claude (outside the door) or Daniel may publish.
    for seat in ("deepseek", "claude", ""):
        assert mirror.runner_refusal({**env_extra, "AKASHIC_AGENT_ID": seat}, push=True) is not None
    assert mirror.runner_refusal({"AKASHIC_AGENT_ID": "claude"}, push=True) is None
    assert mirror.runner_refusal({}, push=True) is None, "Daniel at his own terminal"


def test_p1_push_without_yes_off_a_terminal_is_refused_before_committing(pub_repo):
    work, bare = pub_repo
    (work / "mine.txt").write_text("mine\n")
    head, published = _head(work), _published(work, bare)

    r = _mirror(work, "mine", "mine.txt", "--push")

    assert r.returncode == 5, r.stdout + r.stderr
    assert "--yes" in r.stdout
    assert _head(work) == head and _staged(work) == [] and _published(work, bare) == published


def test_p2_push_with_explicit_flags_publishes_and_lists_first(pub_repo):
    work, bare = pub_repo
    (work / "mine.txt").write_text("mine\n")

    r = _mirror(work, "publish mine", "mine.txt", "--push", "--yes")

    assert r.returncode == 0, r.stdout + r.stderr
    assert _published(work, bare) == _head(work)
    assert _git(work, "log", "-1", "--format=%an") == "claude"
    listed = r.stdout.index("1 commit(s) would be published")
    assert r.stdout.index("publish mine", listed) < r.stdout.index("pushed 1 commit(s)")


def test_p3_other_authors_block_the_push_unless_included(pub_repo):
    work, bare = pub_repo
    _commit_as(work, "sol", "sols.txt", "sol's unpushed work")
    (work / "mine.txt").write_text("mine\n")
    head, published = _head(work), _published(work, bare)

    r = _mirror(work, "mine", "mine.txt", "--push", "--yes")

    assert r.returncode == 4, r.stdout + r.stderr
    flat = _flat(r.stdout)
    assert "sol's unpushed work" in flat and "NOT YOURS" in flat and "--include-others" in flat
    assert _head(work) == head and _staged(work) == [] and _published(work, bare) == published

    r = _mirror(work, "mine", "mine.txt", "--push", "--yes", "--include-others")

    assert r.returncode == 0, r.stdout + r.stderr
    assert _published(work, bare) == _head(work)
    assert "pushed 2 commit(s)" in r.stdout


def test_p4_daniel_publishing_his_own_commits_is_not_blocked(pub_repo):
    work, bare = pub_repo
    _commit_as(work, None, "daniels.txt", "Daniel's own commit")

    r = _mirror(work, "--push", "--yes", seat=None)

    assert r.returncode == 0, r.stdout + r.stderr
    assert _published(work, bare) == _head(work)
    assert "NOT YOURS" not in r.stdout
