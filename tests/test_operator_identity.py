"""Pins for the configurable operator -- whose name goes on the commits agents make.

THE DEFECT (2026-10-12). T411 puts the operator in both git identity fields, and the pre-commit
guard refuses a seat commit under any other name. The operator was a constant naming balanced7, so
on a fork whose own author is s1-f0 every agent commit was refused, and the only way through was
to put another person's name on it. The committed .claude/settings.json made it worse: it still
stamped GIT_AUTHOR_* with the seat (the superseded t384 rule), so even balanced7's sessions failed
the guard.

What these pin: the default is unchanged; a machine's recorded operator replaces it everywhere the
operator is read (launcher env, the guard, the co-author trailer); bad input never becomes an
identity; setup records the git user by default; and the shared settings no longer stamp a seat.

Run: uv run pytest tests/test_operator_identity.py -q
"""

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.comm import seat_identity as si  # noqa: E402

DEFAULT = (si.OPERATOR_NAME, si.OPERATOR_EMAIL)


def _record(name, email):
    path = Path(os.environ[si.OPERATOR_FILE_ENV])
    path.write_text(json.dumps({"name": name, "email": email}), encoding="utf-8")
    return path


# ---------------------------------------------------------------- resolution


def test_default_is_unchanged_without_a_record():
    assert si.operator_identity() == DEFAULT


def test_a_recorded_operator_replaces_the_default():
    _record("s1-f0", "s1f0@proton.me")
    assert si.operator_identity() == ("s1-f0", "s1f0@proton.me")


def test_the_launcher_env_carries_the_recorded_operator_in_both_fields():
    _record("s1-f0", "s1f0@proton.me")
    env = si.git_identity_env("claude")
    assert env == {
        "GIT_AUTHOR_NAME": "s1-f0",
        "GIT_AUTHOR_EMAIL": "s1f0@proton.me",
        "GIT_COMMITTER_NAME": "s1-f0",
        "GIT_COMMITTER_EMAIL": "s1f0@proton.me",
    }


def test_both_env_names_outrank_the_record(monkeypatch):
    _record("s1-f0", "s1f0@proton.me")
    monkeypatch.setenv(si.OPERATOR_NAME_ENV, "runner op")
    monkeypatch.setenv(si.OPERATOR_EMAIL_ENV, "op@example.com")
    assert si.operator_identity() == ("runner op", "op@example.com")


def test_half_an_env_override_is_ignored(monkeypatch):
    monkeypatch.setenv(si.OPERATOR_NAME_ENV, "only a name")
    assert si.operator_identity() == DEFAULT


@pytest.mark.parametrize(
    ("name", "email"),
    [
        ("", "a@b.c"),
        ("x", ""),
        ("x", "no-at-sign"),
        ("x>evil", "a@b.c"),
        ("x", "a@b.c>\nGIT_AUTHOR_NAME=y"),
    ],
)
def test_a_malformed_record_never_becomes_an_identity(name, email):
    _record(name, email)
    assert si.operator_identity() == DEFAULT


def test_an_unreadable_record_falls_back_to_the_default():
    Path(os.environ[si.OPERATOR_FILE_ENV]).write_text("{not json", encoding="utf-8")
    assert si.operator_identity() == DEFAULT


def test_set_operator_writes_the_record_and_refuses_bad_input():
    path = si.set_operator("s1-f0", "s1f0@proton.me")
    assert json.loads(Path(path).read_text(encoding="utf-8")) == {"name": "s1-f0", "email": "s1f0@proton.me"}
    with pytest.raises(ValueError, match="not a usable git identity"):
        si.set_operator("bad<name", "x@y.z")


# ---------------------------------------------------------------- the readers


def test_the_guard_accepts_the_recorded_operator_and_refuses_the_default(monkeypatch):
    from scripts.githooks import pre_commit

    _record("s1-f0", "s1f0@proton.me")
    monkeypatch.setattr(pre_commit, "_git_committer_ident", lambda: "s1-f0 <s1f0@proton.me> 1 +0000")
    ok, msg = pre_commit.check_author_matches_seat("claude", "s1-f0 <s1f0@proton.me> 1 +0000")
    assert ok, msg
    ok, msg = pre_commit.check_author_matches_seat("claude", f"{DEFAULT[0]} <{DEFAULT[1]}> 1 +0000")
    assert not ok
    assert "setup --operator" in msg


def test_the_guard_names_the_stale_seat_stamp_as_a_cause():
    from scripts.githooks import pre_commit

    ok, msg = pre_commit.check_author_matches_seat("claude", "claude <claude@akashic-aurora.local> 1 +0000")
    assert not ok
    assert "GIT_AUTHOR_*" in msg


def test_the_coauthor_trailer_credits_the_recorded_operator(tmp_path):
    from scripts.githooks import coauthor

    _record("s1-f0", "s1f0@proton.me")
    msg = tmp_path / "MSG"
    msg.write_text("feat: x\n", encoding="utf-8")

    class _Out:
        stdout = "someone <someone@example.com> 1 +0000"

    assert coauthor.ensure_operator_coauthor(msg, run=lambda *a, **k: _Out())
    assert "Co-authored-by: s1-f0 <s1f0@proton.me>" in msg.read_text(encoding="utf-8")


def test_no_trailer_when_the_recorded_operator_is_the_author(tmp_path):
    from scripts.githooks import coauthor

    _record("s1-f0", "s1f0@proton.me")
    msg = tmp_path / "MSG"
    msg.write_text("feat: x\n", encoding="utf-8")

    class _Out:
        stdout = "s1-f0 <s1f0@proton.me> 1 +0000"

    assert coauthor.ensure_operator_coauthor(msg, run=lambda *a, **k: _Out()) is None
    assert "Co-authored-by" not in msg.read_text(encoding="utf-8")


# ---------------------------------------------------------------- setup and settings


def test_setup_records_the_git_user_by_default(monkeypatch, capsys):
    from agent.harness import onboard

    monkeypatch.setattr(onboard, "_git_user", lambda cwd: "s1-f0 <s1f0@proton.me>")
    onboard._ask_operator(onboard.Asker(True), ROOT, "aurora", dry=False, flag=None)
    assert si.operator_identity() == ("s1-f0", "s1f0@proton.me")


def test_setup_flag_wins_and_dry_run_writes_nothing(monkeypatch):
    from agent.harness import onboard

    monkeypatch.setattr(onboard, "_git_user", lambda cwd: "s1-f0 <s1f0@proton.me>")
    onboard._ask_operator(onboard.Asker(True), ROOT, "aurora", dry=True, flag="Op <op@example.com>")
    assert not Path(os.environ[si.OPERATOR_FILE_ENV]).exists()
    onboard._ask_operator(onboard.Asker(True), ROOT, "aurora", dry=False, flag="Op <op@example.com>")
    assert si.operator_identity() == ("Op", "op@example.com")


def test_setup_keeps_the_operator_when_the_answer_is_not_an_ident(monkeypatch):
    from agent.harness import onboard

    _record("s1-f0", "s1f0@proton.me")
    onboard._ask_operator(onboard.Asker(True), ROOT, "aurora", dry=False, flag="not an ident")
    assert si.operator_identity() == ("s1-f0", "s1f0@proton.me")


def test_shared_settings_no_longer_stamp_a_seat_as_git_author():
    """The committed .claude/settings.json sets AKASHIC_AGENT_ID, which turns the guard on. If it
    also stamps GIT_AUTHOR_* with the seat, every session in the repo fails that guard."""
    env = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")).get("env", {})
    assert not {k for k in env if k.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_"))}
