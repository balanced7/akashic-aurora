"""
The VFX bench's live channel: claude's renders appear in the open page, and exactly ONE tab renders.

Two bars, both found by reproducing the failure rather than by reasoning about it:

  THE FEED. Daniil's chat box has always attached a snapshot so claude could LOOK at what he meant.
  The return path did not exist -- claude rendered constantly and could only report having done so,
  leaving Daniil a chat line and a PNG somewhere on disk. Bar: every finished job posts an entry
  carrying the image URL, its label and its reason, and FAILURES post too (a render that silently
  does not appear is indistinguishable from a renderer that died, and those need opposite answers).

  THE LEASE. Opening /vfx a second time made that tab a competing renderer, so jobs split at random
  between them -- and the second tab is usually a hidden pane, where rAF is throttled and nothing
  composites, so the job it wins stalls or captures a frame that was never drawn. Bar: one holder,
  renewed by polling, released after TTL, takeable by a tab that can actually draw from one that
  cannot.

No server, no Redis, no browser: the lease and feed are pure functions over module state, and the
clock is stepped by ageing the lease directly so the TTL case is deterministic.

Run: py -m pytest tests/test_vfx_feed_and_lease.py -q
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import pytest

import bifrost_ui as B


@pytest.fixture(autouse=True)
def clean():
    """The bench's live state is module-global by design (it is a channel, not a store), so each
    test starts from an empty one rather than inheriting the previous test's renderer."""
    B._VFX_LEASE.update({"worker": "", "at": 0.0, "visible": True})
    B._VFX_FEED[:] = []
    B._VFX_FEED_SEQ[0] = 0
    B._VFX_JOBS.clear()
    B._VFX_SEQ[0] = 0
    yield


def _age(seconds):
    """Push the lease back in time. Cheaper and steadier than sleeping through a 6s TTL."""
    B._VFX_LEASE["at"] -= seconds


# ---- the lease -------------------------------------------------------------------------------

def test_first_worker_takes_the_farm_and_keeps_it():
    assert B._vfx_lease("wA", True) is True
    assert B._vfx_lease("wA", True) is True          # renewal is not a takeover
    assert B._vfx_lease_state()["worker"] == "wA"


def test_second_visible_tab_is_refused_and_told_it_is_a_viewer():
    B._vfx_lease("wA", True)
    assert B._vfx_lease("wB", True) is False
    B._vfx_job_add("thumb", {"chunk": "swirl"})
    assert B._vfx_job_next("wB", True) == {"viewer": True}
    # ...and the job it did NOT take is still pending for the tab that may have it.
    assert (B._vfx_job_next("wA", True) or {}).get("op") == "thumb"


def test_only_one_of_two_tabs_gets_the_job():
    B._vfx_job_add("thumb", {"chunk": "swirl"})
    got = [B._vfx_job_next("wA", True), B._vfx_job_next("wB", True)]
    real = [g for g in got if g and g.get("id")]
    assert len(real) == 1, "two tabs rendered the same job -- the split-brain this lease exists to stop"


def test_a_visible_tab_takes_over_from_a_hidden_one():
    assert B._vfx_lease("wHidden", False) is True
    assert B._vfx_lease("wVisible", True) is True
    assert B._vfx_lease_state()["worker"] == "wVisible"


def test_a_hidden_tab_does_not_steal_from_a_working_one():
    B._vfx_lease("wVisible", True)
    assert B._vfx_lease("wHidden", False) is False
    # nor from another hidden one: with neither able to draw, first-come holds rather than thrashes
    B._VFX_LEASE.update({"worker": "wH1", "at": B._VFX_LEASE["at"], "visible": False})
    assert B._vfx_lease("wH2", False) is False


def test_lease_is_released_when_the_tab_stops_polling():
    B._vfx_lease("wGone", True)
    _age(B.VFX_LEASE_TTL + 1)
    assert B._vfx_lease_state()["attached"] is False
    assert B._vfx_lease("wNew", True) is True, "a closed tab must not hold the farm forever"


def test_a_page_predating_the_lease_still_renders_but_yields_to_a_named_tab():
    # Deploying mid-session must not stop a bench that is working...
    j = B._vfx_job_add("thumb", {"chunk": "swirl"})
    assert (B._vfx_job_next("", True) or {}).get("id") == j["id"]
    # ...and it must not be reported as nothing, or the CLI sends you to open a tab you already have
    assert B._vfx_lease_state()["attached"] is True
    assert B._vfx_lease_state()["worker"] == "legacy"
    # ...but its claim is weak: a reloaded tab that can name itself takes the farm immediately.
    assert B._vfx_lease("wNamed", True) is True
    assert B._vfx_lease_state()["worker"] == "wNamed"


def test_a_hidden_tab_cannot_steal_from_a_visible_legacy_page():
    """The regression that reproduced live, not in theory: a hidden pane and Daniil's visible
    (pre-lease) tab traded the farm twice a second, because 'legacy is weak' was checked BEFORE
    'a tab that can draw wins'. Every render became a coin flip on landing somewhere that
    composites. Weakness applies only between tabs that are equally able to draw."""
    assert B._vfx_lease("legacy", True) is True
    assert B._vfx_lease("wHiddenPane", False) is False
    assert B._vfx_lease_state()["worker"] == "legacy"
    # ten polls later it is still not thrashing
    for _ in range(10):
        B._vfx_lease("legacy", True)
        assert B._vfx_lease("wHiddenPane", False) is False
    assert B._vfx_lease_state()["worker"] == "legacy"


# ---- the feed --------------------------------------------------------------------------------

def test_every_finished_job_posts_its_picture_and_its_reason():
    B._vfx_job_add("thumb", {"chunk": "swirl", "say": "the reference, before I touch gap"})
    B._vfx_job_next("wA", True)
    B._vfx_job_result("j1", {"ok": True, "path": "design/vfx-snaps/x.png"})
    e = B._vfx_feed_since(0)["entries"][-1]
    assert e["kind"] == "render" and e["ok"] is True
    assert e["url"] == "/vfx/snap/x.png", "no URL means the page has nothing to put in an <img>"
    assert e["label"] == "thumb swirl", "the subject, not just the verb"
    assert e["text"] == "the reference, before I touch gap"


def test_a_failed_render_posts_too():
    B._vfx_job_add("thumb", {"chunk": "nope"})
    B._vfx_job_next("wA", True)
    B._vfx_job_result("j1", {"ok": False, "error": "no such chunk: nope"})
    e = B._vfx_feed_since(0)["entries"][-1]
    assert e["ok"] is False and "no such chunk" in e["error"]
    assert e["url"] == "", "a failure has no image, and must not render a broken one"


def test_thumbs_and_snaps_resolve_to_their_own_routes():
    assert B._vfx_feed_url("design/vfx-snaps/a.png") == "/vfx/snap/a.png"
    assert B._vfx_feed_url("design/vfx-thumbs/b.png") == "/vfx/thumb/b.png"
    assert B._vfx_feed_url("design\\vfx-snaps\\c.png") == "/vfx/snap/c.png"   # Windows path
    assert B._vfx_feed_url("") == "" and B._vfx_feed_url("notes.txt") == ""


def test_a_live_watcher_gets_only_what_it_has_not_seen():
    for i in range(3):
        B._vfx_feed_add({"kind": "say", "text": "n%d" % i})
    r = B._vfx_feed_since(1)
    assert [e["text"] for e in r["entries"]] == ["n1", "n2"]
    assert r["last"] == 3
    assert B._vfx_feed_since(3)["entries"] == []


def test_a_fresh_page_catches_up_without_replaying_the_day():
    for i in range(120):
        B._vfx_feed_add({"kind": "say", "text": "n%d" % i})
    entries = B._vfx_feed_since(0)["entries"]
    assert len(entries) == 30, "since=0 is a reload; 120 entries would fire 120 image requests"
    assert entries[-1]["text"] == "n119", "the catch-up must be the NEWEST, not the oldest"


# ---- what the bench is showing -----------------------------------------------------------------
# Daniil: "If I refresh the page your buffered demo gets lost." The bench had no notion of a current
# subject, so a reload always came back to the default avatar and threw away whatever claude had
# loaded. This is that notion, and it is durable because a server restart must not lose it either.

@pytest.fixture
def bench(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "VFX_BENCH", str(tmp_path / "vfx-bench.json"))
    return tmp_path / "vfx-bench.json"


def test_a_bench_that_has_never_been_used_still_opens(bench):
    d = B._vfx_bench_read()
    assert d["subject"] == "avatar" and d["sketch"] == ""


def test_what_it_was_showing_survives(bench):
    assert B._vfx_bench_write({"subject": "shader", "sketch": "geodesic-original"})["ok"]
    d = B._vfx_bench_read()
    assert d["subject"] == "shader" and d["sketch"] == "geodesic-original"


def test_a_partial_write_merges_rather_than_clobbers(bench):
    """Two callers write this file -- the page (subject/sketch) and the CLI (a note). A writer that
    replaced the keys it did not mention would make them fight over a file neither fully owns."""
    B._vfx_bench_write({"subject": "shader", "sketch": "ringpulse", "identity": "claude"})
    B._vfx_bench_write({"note": "looking at the gap bloom"})
    d = B._vfx_bench_read()
    assert d["sketch"] == "ringpulse" and d["identity"] == "claude"
    assert d["note"] == "looking at the gap bloom"


def test_an_unknown_subject_is_refused(bench):
    B._vfx_bench_write({"subject": "shader"})
    r = B._vfx_bench_write({"subject": "banana"})
    assert r["ok"] is False
    assert B._vfx_bench_read()["subject"] == "shader", "a refused write must not half-apply"
    assert B._vfx_bench_write("not a dict")["ok"] is False


def test_a_corrupt_bench_file_does_not_stop_the_bench_opening(bench):
    bench.write_text("{ this is not json", encoding="utf-8")
    assert B._vfx_bench_read()["subject"] == "avatar", "fail open: a bad file must not brick /vfx"


def test_the_feed_does_not_grow_without_bound():
    for i in range(400):
        B._vfx_feed_add({"kind": "say", "text": "n%d" % i})
    assert len(B._VFX_FEED) <= 300
    # ids keep climbing, so a watcher's cursor stays valid across a trim
    assert B._VFX_FEED[-1]["id"] == 400
