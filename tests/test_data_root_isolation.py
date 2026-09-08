"""RED pin, defer 951a9944f6: a bare AI_SETUP must redirect INSTANCE STATE.

tests/isolate_canonical.py (imported by conftest for EVERY pytest process since T070) points
AI_SETUP at a fresh temp dir holding only session_logs/ -- no agent_cli.py, no core/. Since
e30a8517 (2026-08-24, "portability: retire every E:-drive fallback") the instance-state sites
resolve through core.paths.repo_root(), which VALIDATES the override against the repo markers
and silently falls through to the __file__-derived root when they are absent. A bare data dir
has no markers, so under test isolation the FILE half of isolation has been a no-op:
FileStore() lands in <code root>/session_logs/store_state.json and LearningStore() imports
<code root>/session_logs/learnings.jsonl into whatever store was injected. That file exists
(gitignored) in the live tree and not in a clean clone, which is why
test_learning_loader::test_top_k_and_empty and test_recall_acceptance::test_a2 are red in the
main tree ("empty" store returns live lessons; 156 where 150 were seeded) and green in CI.

Two different questions were merged into one resolver: "where is the CODE" (marker-validated,
derived from __file__) and "where does INSTANCE STATE live" (the AI_SETUP override, raw). The
pins below hold the second question to its documented contract -- "a relocated data dir, a
test harness pointing at a fixture tree" (core/paths.py docstring) -- and they are
machine-independent: the code-root-with-legacy-corpus shape is built in tmp_path rather than
depending on which tree they run in.

Run: py -m pytest tests/test_data_root_isolation.py -q -p no:cacheprovider
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _bare_data_dir(tmp_path: Path) -> Path:
    """Exactly what isolate_canonical creates: a data dir with NO repo markers."""
    bare = tmp_path / "bare"
    (bare / "session_logs").mkdir(parents=True)
    assert not (bare / "agent_cli.py").exists() and not (bare / "core").exists()
    return bare


def _under(path, root) -> bool:
    return Path(str(path)).resolve().is_relative_to(Path(root).resolve())


def _fake_code_root_with_legacy_corpus(tmp_path: Path) -> Path:
    """The live tree's shape: real markers AND a gitignored session_logs/learnings.jsonl."""
    code = tmp_path / "code"
    (code / "core").mkdir(parents=True)
    (code / "agent_cli.py").write_text("", encoding="utf-8")
    (code / "session_logs").mkdir()
    (code / "session_logs" / "learnings.jsonl").write_text(
        json.dumps({"experiment_name": "legacy_only", "category": "pin",
                    "what_tried": "x", "expected_outcome": "y", "actual_outcome": "z",
                    "success": "yes", "recommendation": "must never reach an isolated store"})
        + "\n", encoding="utf-8")
    return code


def test_p1_bare_ai_setup_redirects_the_default_file_store(tmp_path, monkeypatch):
    """The default FileStore is the artifact the 2026-06-20 incident destroyed."""
    bare = _bare_data_dir(tmp_path)
    monkeypatch.setenv("AI_SETUP", str(bare))
    from core.foundation.store import FileStore
    got = FileStore()._path
    assert _under(got, bare), (
        f"FileStore() ignored a bare AI_SETUP and resolved to {got} -- the CODE root's "
        f"session_logs/store_state.json, i.e. the LIVE store when run in the live tree")


def test_p2_bare_ai_setup_redirects_the_default_file_ledger(tmp_path, monkeypatch):
    """Same resolver, same class: the durable event record must not land in the code root."""
    bare = _bare_data_dir(tmp_path)
    monkeypatch.setenv("AI_SETUP", str(bare))
    from core.foundation.ledger import FileLedger
    got = FileLedger()._base
    assert _under(got, bare), f"FileLedger() ignored a bare AI_SETUP and resolved to {got}"


def test_p3_legacy_learnings_jsonl_is_read_from_the_data_root_not_the_code_root(
        tmp_path, monkeypatch):
    """The exact leak behind 951a9944f6, reproduced without depending on the live tree.

    Import the modules FIRST so only the construction under test sees the relocated root.
    Then make core.paths believe it lives in a fake code root that carries a legacy corpus
    (monkeypatch its __file__ and clear the derivation cache) and point AI_SETUP at a bare
    data dir. The isolated store must stay empty: the legacy file belongs to the code root,
    and a bare AI_SETUP says instance state lives elsewhere.
    """
    from core.foundation.store import FileStore
    from core.learning.learning_store import LearningStore
    import core.paths as paths

    code = _fake_code_root_with_legacy_corpus(tmp_path)
    bare = _bare_data_dir(tmp_path)
    monkeypatch.setenv("AI_SETUP", str(bare))
    monkeypatch.setattr(paths, "__file__", str(code / "core" / "paths.py"))
    monkeypatch.setattr(paths, "_cached", None)
    assert paths.repo_root().resolve() == code.resolve(), \
        "sanity: the derivation walk must land on the fake code root"

    ls = LearningStore(store=FileStore(str(tmp_path / "empty.json")))
    names = sorted(rec.get("experiment_name") for rec in ls.load_all_learnings_from_store())
    assert names == [], (
        f"an isolated, explicitly-empty store came back holding {names}: the legacy "
        f"session_logs/learnings.jsonl was read from the CODE root instead of the data root")


def test_p4_data_root_follows_ai_setup_while_repo_root_stays_derived(tmp_path, monkeypatch):
    """The contract, stated once: a set AI_SETUP always redirects instance state, whether or
    not it looks like a repo; the code root is still derived; unset, the two coincide."""
    bare = _bare_data_dir(tmp_path)
    monkeypatch.setenv("AI_SETUP", str(bare))
    from core.paths import data_root, repo_root
    assert data_root().resolve() == bare.resolve(), f"data_root() ignored AI_SETUP: {data_root()}"
    assert (repo_root() / "agent_cli.py").exists(), \
        f"repo_root() must stay the CODE root under a bare AI_SETUP, got {repo_root()}"
    monkeypatch.delenv("AI_SETUP")
    assert data_root() == repo_root(), "with no override the data root IS the repo root"
