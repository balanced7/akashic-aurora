"""Pins for the local authorship ledger -- who, in which session, harness and model, made a commit.

THE CHANGE (2026-10-12). The ledger was tracked in git, so every push published which agent seat
made each commit. A commit now shows only the operator, and the full story -- seat, session,
harness and version, model, effort, config fingerprints -- is recorded locally, in the world's
instance state, one row per commit, appended and never edited.

Run: uv run pytest tests/test_local_authorship_ledger.py -q
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import authorship_ledger as al  # noqa: E402
from scripts.githooks import post_commit  # noqa: E402


def _rows(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


@pytest.fixture
def no_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(al, "LEGACY", tmp_path / "no-legacy.jsonl")


# ---------------------------------------------------------------- where it lives


def test_the_env_names_the_ledger():
    assert al.ledger_path() == Path(os.environ[al.LEDGER_ENV])


def test_the_default_is_the_worlds_shared_state(tmp_path, monkeypatch):
    import core.paths

    monkeypatch.delenv(al.LEDGER_ENV)
    # raising=False: a tree without the per-world home (core.paths.shared_state_root) still pins
    # that the ledger asks for it.
    monkeypatch.setattr(core.paths, "shared_state_root", lambda: tmp_path, raising=False)
    assert al.ledger_path() == tmp_path / "state" / "authorship" / "seats.jsonl"


def test_without_a_shared_state_root_the_ledger_stays_in_ignored_state(monkeypatch):
    import core.paths

    monkeypatch.delenv(al.LEDGER_ENV)
    monkeypatch.delattr(core.paths, "shared_state_root", raising=False)
    assert al.ledger_path() == al.LEGACY


def test_the_ledger_is_not_tracked():
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "state/authorship"], capture_output=True, text=True
    ).stdout
    assert tracked.strip() == ""
    ignored = subprocess.run(
        ["git", "-C", str(ROOT), "check-ignore", "-q", "state/authorship/seats.jsonl"], capture_output=True
    )
    assert ignored.returncode == 0


# ---------------------------------------------------------------- append-only


def test_append_keeps_every_earlier_byte(no_legacy):
    al.append({"sha": "a" * 12, "seat": "claude"})
    before = al.ledger_path().read_bytes()
    al.append({"sha": "b" * 12, "seat": "codex"})
    after = al.ledger_path().read_bytes()
    assert after.startswith(before)
    assert [r["seat"] for r in _rows(al.ledger_path())] == ["claude", "codex"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_the_ledger_is_read_only_between_appends(no_legacy):
    al.append({"sha": "a" * 12, "seat": "claude"})
    assert not os.access(al.ledger_path(), os.W_OK) or os.geteuid() == 0
    al.append({"sha": "b" * 12, "seat": "claude"})  # append still works
    assert len(_rows(al.ledger_path())) == 2


def test_first_use_seeds_from_the_tracked_copy(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text(json.dumps({"sha": "c" * 12, "seat": "old"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(al, "LEGACY", legacy)
    al.append({"sha": "d" * 12, "seat": "new"})
    assert [r["seat"] for r in _rows(al.ledger_path())] == ["old", "new"]


def test_load_reads_the_tracked_copy_until_a_local_one_exists(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text(json.dumps({"sha": "e" * 12, "seat": "old"}) + "\n", encoding="utf-8")
    monkeypatch.setattr(al, "LEGACY", legacy)
    assert [r["seat"] for r in al.load()] == ["old"]
    assert al.seat_for("e" * 12)["seat"] == "old"


# ---------------------------------------------------------------- what a commit records


def _commit_env(monkeypatch):
    for k in list(os.environ):
        if k.startswith(("CLAUDE", "CODEX_", "CURSOR_", "AKASHIC_SESSION", "AKASHIC_HARNESS")):
            monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-1234")
    monkeypatch.setenv("AI_AGENT", "claude-code_2-1-296_agent")
    monkeypatch.setenv("AKASHIC_MODEL", "model-under-test")
    monkeypatch.setenv("CLAUDE_EFFORT", "high")


#: Session provenance (core/fleet/provenance.py, meta-harness 01) is what fills these rows. A tree
#: without it records the seat alone -- pinned by test_without_provenance_the_row_keeps_the_seat.
needs_provenance = pytest.mark.skipif(
    importlib.util.find_spec("core.fleet.provenance") is None, reason="needs core.fleet.provenance"
)


def test_without_provenance_the_row_keeps_the_seat(monkeypatch, no_legacy):
    _commit_env(monkeypatch)
    monkeypatch.setitem(sys.modules, "core.fleet.provenance", None)  # import fails
    assert post_commit.main() == 0
    (row,) = _rows(al.ledger_path())
    assert row["seat"] == "claude"
    assert "session_id" not in row


@needs_provenance
def test_a_commit_row_carries_session_harness_model_and_effort(monkeypatch, no_legacy):
    _commit_env(monkeypatch)
    assert post_commit.main() == 0
    (row,) = _rows(al.ledger_path())
    assert row["seat"] == "claude"
    assert row["session_id"] == "sess-1234"
    assert row["provenance"] == "prov:session:sess-1234"
    assert row["harness"] == "claude-code"
    assert row["harness_version"] == "2.1.296"
    assert row["model"] == "model-under-test"
    assert row["effort"] == "high"
    assert row["project_fingerprint"]
    assert len(row["sha"]) == 12


@needs_provenance
def test_an_unknown_field_is_left_out_not_guessed(monkeypatch, no_legacy):
    _commit_env(monkeypatch)
    monkeypatch.delenv("CLAUDE_EFFORT")
    post_commit.main()
    (row,) = _rows(al.ledger_path())
    assert "effort" not in row


def test_no_row_without_a_declared_seat(monkeypatch, no_legacy):
    for var in ("AKASHIC_AGENT_ID", "AKASHIC_SEAT", "AI_AGENT"):
        monkeypatch.delenv(var, raising=False)
    assert post_commit.main() == 0
    assert not al.ledger_path().exists()


def test_who_prints_the_provenance(monkeypatch, capsys, no_legacy):
    al.append({"sha": "f" * 12, "seat": "claude", "subject": "x", "model": "m1", "effort": "low", "session_id": "s9"})
    al.main(["who", "f" * 12])
    out = capsys.readouterr().out
    assert "session_id=s9" in out
    assert "model=m1" in out
    assert "effort=low" in out
