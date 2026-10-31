"""Pins for the PRIVATE OVERLAY half of the Local layer (Rill's A1, 2026-10-31).

WHAT THIS DEFENDS. `local/` is committed to a PUBLIC repo, so it may carry house defaults and
derivations and never this machine's address or a home path. The values that ARE this machine --
the phone's tailnet address, where an external tool is installed, which seat the panel reports on
-- live in a separate private repo and are laid over the defaults at read time. Three ways that can
go wrong, and each one renders as a CLEAN answer rather than as a failure:

  1. THE OVERLAY IS SILENTLY SKIPPED. A loader that ignores the profile returns the public
     defaults, and every machine value reads as UNKNOWN or as a default belonging to nobody.
     Fail-open is right for the work path; SILENT is not. Hence the one-loud-line pin.
  2. A BADLY CONFIGURED OVERLAY IS QUIETLY IGNORED. $AKASHIC_LOCAL set to the wrong directory is a
     misconfiguration, not an absent machine -- falling back to the marker walk would hide it and
     load some OTHER profile. Hence the refusal pin.
  3. A PROFILE OF AN UNKNOWN SHAPE IS MERGED ANYWAY. A half-understood overlay puts values of
     unknown structure into a live read, which is worse than no overlay. Hence the version pins.

Run: py tests/test_local_overlay.py   (or via pytest)
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import local                                            # noqa: E402

#: The real discovery function, captured before any fixture replaces it: the discovery pins must
#: exercise IT, while every other pin needs it OUT of the way (see the fixture).
_REAL_RESOLVE = local._resolve_profile


@pytest.fixture(autouse=True)
def _no_machine_profile(monkeypatch):
    """Every pin starts with NO profile and no memory of one.

    `_resolve_profile` is replaced rather than left alone on purpose: on this machine the private
    profile will eventually live at `E:\\dev\\akashic-local` and the marker walk would find it, so a
    pin that says 'an absent overlay fails open' would start passing only on machines without one.
    The discovery pins put the real function back, and they own their own tmp trees.
    """
    monkeypatch.setattr(local, "_resolve_profile", lambda: None)
    local._profile_cache.clear()
    local._ANNOUNCED.clear()
    monkeypatch.delenv(local.PROFILE_ENV, raising=False)
    yield
    local._profile_cache.clear()
    local._ANNOUNCED.clear()


def _discovery(monkeypatch, env=None):
    """Restore REAL discovery for one pin, with the instance root pinned to a tmp tree."""
    monkeypatch.setattr(local, "_resolve_profile", _REAL_RESOLVE)
    local._profile_cache.clear()
    if env is not None:
        monkeypatch.setenv(local.PROFILE_ENV, str(env))


def _make_profile(base, name="reachability", body=None, marker=True):
    """A throwaway private repo: <base>/akashic-local/{.akashic-local,profile/<name>.json}."""
    root = base / "akashic-local"
    (root / "profile").mkdir(parents=True)
    if marker:
        (root / local.PROFILE_MARKER).write_text("profile marker\n", encoding="utf-8")
    if body is not None:
        (root / "profile" / f"{name}.json").write_text(json.dumps(body, indent=1), encoding="utf-8")
    return root


# --------------------------------------------------------------- 1. absence is LOUD, never silent
def test_an_absent_overlay_fails_open_and_says_so_once(capsys, monkeypatch):
    """The contract: the read still succeeds, and the absence is LOUD exactly once.

    Discovery is neutered (empty candidate sets) rather than pointed at a tmp tree: the search is
    machine-level by design, so any tmp tree under pytest's root can legitimately contain a
    neighbouring test's `akashic-local`. What this pin is about is the ANNOUNCEMENT, so that is
    what it isolates.
    """
    monkeypatch.setattr(local, "_resolve_profile", _REAL_RESOLVE)
    monkeypatch.setattr(local, "_akashic_local_dirs", lambda parent: [])
    monkeypatch.setattr(local, "_one_level_below", lambda parent: [])
    doc = local.load("reachability")            # the work path still works
    assert doc["operator_ids"]["values"], doc.keys()
    err = capsys.readouterr().err
    lines = [ln for ln in err.splitlines() if ln.startswith("[local]")]
    assert len(lines) == 1, f"expected exactly ONE loud line, got {len(lines)}:\n{err}"
    assert "ABSENT" in lines[0] and "PUBLIC defaults" in lines[0], lines[0]
    # and the line is not repeated for the next file read (one per PROCESS, not per call)
    local.load("wiring")
    assert not [ln for ln in capsys.readouterr().err.splitlines() if ln.startswith("[local]")]


def test_the_public_file_is_returned_unchanged_when_absent():
    doc = local.public_only("reachability")
    assert "phone" in doc
    assert doc["phone"]["tailnet_host"] is None, (
        "the committed file must keep the NULL: a tailnet address is a routable address for one "
        "machine and belongs in the private profile, not in a public repo")
    assert "E:" not in json.dumps(doc) and "C:/Users" not in json.dumps(doc)


def test_every_shipped_local_file_declares_its_version():
    """The public defaults carry the schema version too, so the pair can be compared at a glance."""
    d = local.local_dir()
    for path in sorted(d.glob("*.json")):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        assert doc.get("version") == local.SCHEMA_VERSION, f"{path.name} version is {doc.get('version')!r}"


# --------------------------------------------------------------------- 2. discovery, and its refusals
def test_the_env_var_points_at_the_private_repo(tmp_path, monkeypatch):
    root = _make_profile(tmp_path, body={"version": 1, "phone": {"tailnet_host": "100.64.0.9"}})
    _discovery(monkeypatch, env=root)
    assert local.profile_dir() == root / "profile"
    doc = local.load("reachability")
    assert doc["phone"]["tailnet_host"] == "100.64.0.9"
    assert doc["phone"]["ssh_port"] == 8022, "the public default survives the overlay"
    assert doc["_overlay"]["path"].endswith("reachability.json")


def test_the_env_var_may_name_the_profile_directory_itself(tmp_path, monkeypatch):
    root = _make_profile(tmp_path, body={"version": 1, "phone": {"tailnet_host": "100.64.0.9"}})
    _discovery(monkeypatch, env=root / "profile")
    assert local.profile_dir() == root / "profile"


def test_a_bad_env_var_is_loud_and_never_silently_replaced_by_the_walk(tmp_path, monkeypatch, capsys):
    """A set-but-unusable AKASHIC_LOCAL is a MISCONFIGURATION. Falling back to the marker walk
    would load a different profile than the one the operator asked for, silently."""
    empty = tmp_path / "not-a-profile"
    empty.mkdir()
    _discovery(monkeypatch, env=empty)
    assert local.profile_dir() is None
    err = capsys.readouterr().err
    assert "MISCONFIGURATION" in err, err
    assert "NOT used as a silent fallback" in err, err


def test_the_marker_walk_finds_a_sibling_and_a_grandchild(tmp_path, monkeypatch):
    # grandchild: <parent>/dev/akashic-local -- the E:/dev/akashic-local shape
    root = _make_profile(tmp_path / "dev", body={"version": 1})
    fake_instance = tmp_path / "checkout"
    fake_instance.mkdir()
    (fake_instance / "agent_cli.py").write_text("", encoding="utf-8")
    _discovery(monkeypatch)
    monkeypatch.setattr(local, "instance_root", lambda: fake_instance)
    assert local.profile_dir() == root / "profile"


def test_a_directory_named_akashic_local_WITHOUT_the_marker_is_not_a_profile(tmp_path, monkeypatch):
    """The NAME is not the claim; the marker is.

    The assertion is deliberately about THIS directory rather than about `profile_dir() is None`:
    the walk is a machine-level search, so another marked `akashic-local` elsewhere on the path is
    a legitimate answer (under pytest, a neighbouring test's fixture) and asserting None would be
    asserting that no fixture anywhere above the tmp tree carries a marker. What must never happen
    is the unmarked directory being read, and that is what this pins.
    """
    bare = tmp_path / "akashic-local"
    (bare / "profile").mkdir(parents=True)
    (bare / "profile" / "reachability.json").write_text('{"version": 1}', encoding="utf-8")
    fake_instance = tmp_path / "checkout"
    fake_instance.mkdir()
    (fake_instance / "agent_cli.py").write_text("", encoding="utf-8")
    _discovery(monkeypatch)
    monkeypatch.setattr(local, "instance_root", lambda: fake_instance)
    assert not local._has_marker(bare)
    assert local.profile_dir() != bare / "profile"
    # and PASS 1 (beside the tree) never even offers it: an unmarked name is not a candidate
    assert local._akashic_local_dirs(tmp_path) == [bare]
    assert [c for c in local._akashic_local_dirs(tmp_path) if local._has_marker(c)] == []


def test_a_sibling_beats_the_one_level_bend(tmp_path, monkeypatch):
    """Two marked profiles within reach: the one BESIDE the tree wins over the one below an
    ancestor. The bend exists for the E:/dev/akashic-local shape; it is the weaker claim."""
    sibling = _make_profile(tmp_path, body={"version": 1, "phone": {"tailnet_host": "100.64.0.1"}})
    bent = _make_profile(tmp_path / "dev", body={"version": 1, "phone": {"tailnet_host": "100.64.0.2"}})
    fake_instance = tmp_path / "checkout"
    fake_instance.mkdir()
    (fake_instance / "agent_cli.py").write_text("", encoding="utf-8")
    _discovery(monkeypatch)
    monkeypatch.setattr(local, "instance_root", lambda: fake_instance)
    assert local.profile_dir() == sibling / "profile", bent


# ------------------------------------------------------------------------ 3. the version is a gate
@pytest.mark.parametrize("body,needle", [
    ({"phone": {"tailnet_host": "x"}}, "carries no 'version'"),
    ({"version": 99, "phone": {}}, "NEWER than the code reading it"),
    ({"version": "1", "phone": {}}, "not an integer"),
])
def test_an_unusable_overlay_is_REFUSED_not_merged(tmp_path, monkeypatch, body, needle):
    root = _make_profile(tmp_path, body=body)
    _discovery(monkeypatch, env=root)
    with pytest.raises(local.LocalDataMissing, match=needle):
        local.load("reachability")


def test_an_older_version_is_read_forward(tmp_path, monkeypatch):
    root = _make_profile(tmp_path, body={"version": local.SCHEMA_VERSION, "phone": {"ssh_port": 2222}})
    _discovery(monkeypatch, env=root)
    assert local.load("reachability")["phone"]["ssh_port"] == 2222


# --------------------------------------------------------------------------- 4. the merge rule
def test_objects_merge_key_wise_and_a_leaf_is_overridden():
    merged = local.merge({"a": 1, "n": {"x": 1, "y": 2}}, {"n": {"y": 20, "z": 3}})
    assert merged == {"a": 1, "n": {"x": 1, "y": 20, "z": 3}}


def test_a_list_of_id_rows_merges_BY_ID_and_keeps_public_order():
    """The property that lets a private profile carry only the two services it changes, instead of
    copying the whole allowlist (a copy is a second source of truth, and it drifts)."""
    pub = [{"id": "one", "v": 1, "keep": "p"}, {"id": "two", "v": 2}]
    over = [{"id": "two", "v": 22}, {"id": "three", "v": 3}]
    merged = local.merge(pub, over)
    assert [r["id"] for r in merged] == ["one", "two", "three"]
    assert merged[0] == {"id": "one", "v": 1, "keep": "p"}
    assert merged[1] == {"id": "two", "v": 22}
    assert merged[2] == {"id": "three", "v": 3}


def test_a_plain_list_is_REPLACED_never_merged_positionally():
    assert local.merge({"match": ["a", "b"]}, {"match": ["z"]})["match"] == ["z"]


def test_a_list_mixing_keyed_and_unkeyed_rows_is_replaced():
    """Half-keyed is not a row set; merging it by id would silently drop the unkeyed members."""
    merged = local.merge({"rows": [{"id": "a"}, "bare"]}, {"rows": [{"id": "a", "v": 1}]})
    assert merged["rows"] == [{"id": "a", "v": 1}]


def test_the_merged_document_says_WHICH_profile_produced_it(tmp_path, monkeypatch):
    root = _make_profile(tmp_path, body={"version": 1})
    _discovery(monkeypatch, env=root)
    doc = local.load("reachability")
    assert doc["_overlay"]["version"] == 1
    assert str(root) in doc["_overlay"]["path"]


# ------------------------------------------------------------------------------- 5. status() tells the truth
def test_status_reports_the_profile_as_its_own_block(tmp_path, monkeypatch):
    root = _make_profile(tmp_path, body={"version": 1, "phone": {"tailnet_host": "100.64.0.9"}})
    _discovery(monkeypatch, env=root)
    st = local.status()
    prof = st["profile"]
    assert prof["present"] is True and prof["env"] == str(root)
    assert prof["files"] == ["reachability.json"]
    assert prof["applied"] and prof["applied"]["reachability.json"].endswith("reachability.json")
    assert prof["unreadable"] == []


def test_status_calls_a_broken_profile_BROKEN_not_absent(tmp_path, monkeypatch):
    root = _make_profile(tmp_path, body={"phone": {}})          # no version: unusable
    _discovery(monkeypatch, env=root)
    st = local.status()
    assert st["profile"]["present"] is True
    assert [u["file"] for u in st["profile"]["unreadable"]] == ["reachability.json"]
