"""t384 grant --bootstrap pins -- RED first (Rill's build lane, reconciliation RULING 1).

The peer-side ceremony: before pulling the split commit, the peer stamps an instance
marker into its LOCAL acl.json. The marker makes the file differ from the tracked blob,
so the upstream delete meets a local modify and git raises a modify/delete CONFLICT
instead of silently deleting the ACL (which would quarantine every non-bootstrap seat
through the availability floor -- the exact harm the fence exists to prevent, relocated).

  P1  PRESERVE: bootstrap touches NOTHING but the marker -- every grant survives
      byte-for-byte in content.
  P2  REFUSE-MISSING: no file -> loud refusal, nothing created (never mint from nothing).
  P3  REFUSE-CORRUPT: corrupt file -> loud refusal, original bytes untouched.
  P4  IDEMPOTENT: a second run updates the stamp, grants unchanged.
  P5  LOUD-CONFLICT: the marked file differs from the pre-bootstrap bytes (the local-
      modify guarantee the whole ceremony rests on).
  P6  FAR-SIDE DRILL: a real two-repo git simulation -- upstream deletes acl.json in the
      split commit; the bootstrapped peer's pull CONFLICTS (modify/delete) instead of
      deleting; keeping local leaves the grants serving.
"""
import json
import os
import shutil
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

SAMPLE = {
    "_comment": "test acl",
    "schema_version": 1,
    "grants": [
        {"agent_id": "claude", "role": "super_admin", "caps": [], "path_scope": ["*"],
         "granted_by": "root", "granted_at": "2026-08-24T00:00:00Z", "reason": "t"},
        {"agent_id": "dsh_agent", "role": "admin", "caps": [], "path_scope": ["*"],
         "granted_by": "daniil", "granted_at": "2026-08-24T07:30:00Z",
         "expires_at": "2026-08-31T07:30:00Z", "reason": "t"},
    ],
}


@pytest.fixture()
def acl_file(tmp_path, monkeypatch):
    p = tmp_path / "acl.json"
    p.write_text(json.dumps(SAMPLE, indent=2), encoding="utf-8")
    monkeypatch.setenv("AKASHIC_ACL_PATH", str(p))
    return p


def _grants_from(path):
    return json.loads(path.read_text(encoding="utf-8")).get("grants", [])


def test_p1_bootstrap_preserves_grants_and_stamps_marker(acl_file):
    from core.trust import grant_writer
    before = _grants_from(acl_file)
    rep = grant_writer.bootstrap(by="dsh_agent")
    doc = json.loads(acl_file.read_text(encoding="utf-8"))
    assert rep["grants_preserved"] == len(before) == 2
    assert doc["grants"] == before, (
        "P1: bootstrap must touch NOTHING but the marker -- grants changed")
    assert doc["_instance"]["hostname"] and doc["_instance"]["bootstrapped_at"], (
        f"P1: the instance marker is the ceremony's load-bearing stamp: {doc.get('_instance')}")


def test_p2_refuses_on_missing_file(tmp_path, monkeypatch):
    from core.trust import grant_writer
    missing = tmp_path / "nope.json"
    monkeypatch.setenv("AKASHIC_ACL_PATH", str(missing))
    with pytest.raises(ValueError, match="no ACL file to bootstrap"):
        grant_writer.bootstrap()
    assert not missing.exists(), "P2: refusal must create NOTHING -- never mint from nothing"


def test_p3_refuses_on_corrupt_and_touches_nothing(acl_file):
    from core.trust import grant_writer
    corrupt = "{ not json"
    acl_file.write_text(corrupt, encoding="utf-8")
    with pytest.raises(ValueError):
        grant_writer.bootstrap()
    assert acl_file.read_text(encoding="utf-8") == corrupt, (
        "P3: a corrupt ACL must survive the refusal byte-for-byte")


def test_p4_idempotent_second_run(acl_file):
    from core.trust import grant_writer
    first = grant_writer.bootstrap(by="dsh_agent")
    second = grant_writer.bootstrap(by="dsh_agent")
    assert second["grants_preserved"] == first["grants_preserved"] == 2
    assert second["bootstrapped_at"] >= first["bootstrapped_at"], (
        "P4: re-running is safe and re-stamps (second-resolution means same-second "
        "collisions are legitimate)")
    assert _grants_from(acl_file) == SAMPLE["grants"], "P4: grants still unchanged after re-run"


def test_p5_marked_file_differs_from_input_blob(acl_file):
    from core.trust import grant_writer
    blob = acl_file.read_bytes()
    grant_writer.bootstrap(by="dsh_agent")
    assert acl_file.read_bytes() != blob, (
        "P5: the marker MUST change the bytes -- identical content means git treats the "
        "peer's file as unmodified and the split commit deletes it silently")


@pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")
def test_p6_far_side_drill(tmp_path, monkeypatch):
    """The whole flow from Serge's side, in real git: upstream deletes the tracked ACL;
    a bootstrapped peer's pull must CONFLICT (modify/delete), and keeping local leaves
    the grants serving through the real resolve()."""
    from core.trust import grant_writer
    up = tmp_path / "upstream"
    peer = tmp_path / "peer"
    up.mkdir()
    (up / "security").mkdir()
    acl = up / "security" / "acl.json"
    acl.write_text(json.dumps(SAMPLE, indent=2), encoding="utf-8")

    def g(*args, cwd):
        return subprocess.run(["git", "-c", "user.name=drill", "-c", "user.email=drill@test"]
                              + list(args), cwd=str(cwd), capture_output=True, text=True)

    g("init", "-q", "-b", "master", cwd=up)
    g("add", "security/acl.json", cwd=up)
    g("commit", "-qm", "tracked acl", cwd=up)
    g("clone", "-q", str(up), str(peer), cwd=tmp_path)

    # (1) the peer ceremony BEFORE the pull
    monkeypatch.setenv("AKASHIC_ACL_PATH", str(peer / "security" / "acl.json"))
    rep = grant_writer.bootstrap(by="operator")
    assert rep["grants_preserved"] == 2

    # (2) upstream lands the split commit (untrack + delete)
    g("rm", "--cached", "-q", "security/acl.json", cwd=up)
    g("commit", "-qm", "split: acl.json untracked", cwd=up)

    # (3) the peer pulls with the marker UNCOMMITTED -- git must ABORT the merge loudly
    # (refusing to overwrite the local file), never silently delete
    pull = g("pull", "-q", "origin", "master", cwd=peer)
    assert "security/acl.json" in (pull.stdout + pull.stderr) and pull.returncode != 0, (
        f"P6: an uncommitted local ACL must ABORT the pull loudly; got rc={pull.returncode}\n"
        f"out={pull.stdout}\nerr={pull.stderr}")
    assert (peer / "security" / "acl.json").exists(), (
        "P6: the local ACL must survive the aborted pull")

    # (3b) commit the bootstrapped file locally, then pull -- now the true modify/delete
    # CONFLICT surfaces, and keeping local is one add+commit
    g("add", "security/acl.json", cwd=peer)
    g("commit", "-qm", "bootstrap marker", cwd=peer)
    pull2 = g("pull", "-q", "origin", "master", cwd=peer)
    assert "CONFLICT (modify/delete)" in (pull2.stdout + pull2.stderr), (
        f"P6: the committed-local pull must be the modify/delete CONFLICT; "
        f"got rc={pull2.returncode}\nout={pull2.stdout}\nerr={pull2.stderr}")

    # (4) keep local -- grants still serve through the REAL door
    g("add", "security/acl.json", cwd=peer)
    g("commit", "-qm", "keep local acl", cwd=peer)
    monkeypatch.chdir(peer)
    import core.trust.registry as registry
    registry._CACHE["mtime"] = None
    g1 = registry.resolve("claude", verified=True)
    g2 = registry.resolve("dsh_agent", verified=True)
    assert g1.role == "super_admin" and g2.role == "admin", (
        f"P6: keeping local must leave the grants SERVING: claude={g1.role}, "
        f"dsh_agent={g2.role}")
    monkeypatch.delenv("AKASHIC_ACL_PATH", raising=False)
