"""The plocate engine for `find` (core/tools/locate.py): Linux's answer to Everything.

Each pin runs a REAL plocate over a REAL index built from a temporary tree, because the
failures this engine exists to prevent live in the seam between the index and the disk: a
file the index remembers but the disk has lost, a sort the index cannot do, a miss that is
only as good as the index's age. Skipped where plocate is not installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time

import pytest

import core.tools.everything as ev
from core.tools import locate

pytestmark = pytest.mark.skipif(
    not (shutil.which("plocate") and shutil.which("updatedb")), reason="plocate is not installed"
)


@pytest.fixture
def indexed(tmp_path, monkeypatch):
    """A small tree, a plocate index of it, and the engine pointed at that index only."""
    tree = tmp_path / "tree"
    (tree / "proj" / "core").mkdir(parents=True)
    (tree / "proj" / "core" / "agent_cli.py").write_text("x" * 10, encoding="utf-8")
    (tree / "proj" / "my_agent_cli.py.bak").write_text("x" * 500, encoding="utf-8")
    (tree / "proj" / "agent_cli.py").write_text("x" * 100, encoding="utf-8")
    (tree / "shaders").mkdir()
    (tree / "shaders" / "orrery.frag").write_text("x", encoding="utf-8")
    (tree / "agent_dir").mkdir()
    db = tmp_path / "find.db"
    # The test tree lives under /tmp, which the distro prunes; an empty prune list keeps it.
    subprocess.run(
        ["updatedb", "-l", "no", "-U", str(tree), "-o", str(db), "--prunepaths", ""], check=True, capture_output=True
    )
    monkeypatch.setenv("AKASHIC_FIND_DB", str(db))
    monkeypatch.setattr(locate, "SYSTEM_INDEX", str(tmp_path / "no-system.db"))
    monkeypatch.setattr(ev, "resolve_es", lambda: None)
    started = []
    monkeypatch.setattr(locate, "refresh_index", lambda **kw: started.append(kw) or "index refresh started")
    return tree, started


def test_without_everything_the_index_answers_not_the_walk(indexed):
    tree, _ = indexed
    res = ev.search("agent_cli.py")
    assert res.ok
    assert res.engine == "plocate"
    assert str(tree / "proj" / "agent_cli.py") in res.paths
    assert res.index_age_s is not None, "an indexed answer must say how old its index is"


def test_exact_basename_matches_rank_first(indexed):
    tree, _ = indexed
    res = ev.search_page("agent_cli.py")
    exact = {str(tree / "proj" / "agent_cli.py"), str(tree / "proj" / "core" / "agent_cli.py")}
    assert set(res.paths[:2]) == exact, res.paths
    assert res.paths[2].endswith("my_agent_cli.py.bak")


def test_a_deleted_file_never_comes_back_from_the_index(indexed):
    tree, _ = indexed
    gone = tree / "proj" / "agent_cli.py"
    gone.unlink()
    res = ev.search_page("agent_cli.py")
    assert str(gone) not in res.paths
    assert any("no longer exist" in n for n in res.notes), res.notes


def test_every_hit_carries_size_and_mtime(indexed):
    res = ev.search_page("my_agent_cli")
    (hit,) = res.hits
    assert hit.size == 500
    assert hit.date_modified
    assert hit.extension == "bak"


def test_space_separated_terms_must_all_match_like_everything(indexed):
    res = ev.search_page("agent bak")
    assert [os.path.basename(p) for p in res.paths] == ["my_agent_cli.py.bak"]


def test_a_glob_matches_the_whole_name(indexed):
    res = ev.search_page("*.frag")
    assert [os.path.basename(p) for p in res.paths] == ["orrery.frag"]


def test_files_dirs_and_scope_filters(indexed):
    tree, _ = indexed
    assert [os.path.basename(p) for p in ev.search_page("agent", dirs_only=True).paths] == ["agent_dir"]
    assert "agent_dir" not in {os.path.basename(p) for p in ev.search_page("agent", files_only=True).paths}
    scoped = ev.search_page("agent_cli.py", scope=str(tree / "proj" / "core"))
    assert scoped.paths == [str(tree / "proj" / "core" / "agent_cli.py")]


def test_a_requested_sort_beats_the_exact_first_ranking(indexed):
    res = ev.search_page("agent_cli", sort="size-descending", files_only=True)
    assert [h.size for h in res.hits] == [500, 100, 10]


def test_paging_slices_the_ranked_answer(indexed):
    full = ev.search_page("agent").paths
    assert ev.search_page("agent", limit=2, offset=1).paths == full[1:3]


def test_windows_attributes_refuse_rather_than_silently_ignore(indexed):
    res = ev.search_page("agent", attributes="H")
    assert not res.ok
    assert "Windows" in (res.error or "")


def test_a_stale_index_starts_a_background_refresh_and_still_answers(indexed, monkeypatch):
    _, started = indexed
    old = time.time() - 3600
    os.utime(os.environ["AKASHIC_FIND_DB"], (old, old))
    monkeypatch.setenv("AKASHIC_FIND_INDEX_MAX_AGE", "600")
    res = ev.search_page("orrery")
    assert res.ok
    assert res.paths, "a stale index must still answer at once"
    assert started == [{}], "one background refresh, not a blocking one"
    assert (res.index_age_s or 0) >= 3500


def test_a_fresh_index_starts_no_refresh(indexed):
    _, started = indexed
    ev.search_page("orrery")
    assert started == []


def test_the_freshest_index_wins(tmp_path, monkeypatch):
    user, system = tmp_path / "user.db", tmp_path / "system.db"
    user.write_bytes(b"")
    system.write_bytes(b"")
    monkeypatch.setenv("AKASHIC_FIND_DB", str(user))
    monkeypatch.setattr(locate, "SYSTEM_INDEX", str(system))
    os.utime(user, (1000, 1000))
    assert locate.pick_index() == (None, os.path.getmtime(system)), "system is newer: use plocate's default"
    later = time.time() + 10
    os.utime(user, (later, later))
    assert locate.pick_index()[0] == str(user)


def test_no_index_yet_walks_and_starts_a_build(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_FIND_DB", str(tmp_path / "missing.db"))
    monkeypatch.setattr(locate, "SYSTEM_INDEX", str(tmp_path / "missing-system.db"))
    monkeypatch.setattr(ev, "resolve_es", lambda: None)
    monkeypatch.setattr(ev, "_WALK_ROOTS", (str(tmp_path),))
    started = []
    monkeypatch.setattr(locate, "refresh_index", lambda **kw: started.append(kw) or "started")
    (tmp_path / "needle.txt").write_text("x", encoding="utf-8")
    res = ev.search("needle")
    assert res.engine == "walk"
    assert res.paths
    assert started, "the first indexless query must start building the index"


def test_the_fast_door_prints_a_clean_path_list(indexed, capsys):
    tree, _ = indexed
    assert locate.main(["orrery"]) == 0
    out = capsys.readouterr()
    assert out.out == f"{tree / 'shaders' / 'orrery.frag'}\n", "stdout must be paths only, for pipes"
    assert "1 match(es)" in out.err


def test_the_render_names_the_engine_and_the_index_age(indexed):
    text = ev.format_result(ev.search_page("orrery"))
    assert "engine: plocate index" in text
    assert "old" in text
