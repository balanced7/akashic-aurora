"""
T205 -- `ask --bg`: stop blocking on your own helpers. RED first.

THE FRICTION, measured on this session. Every fence today ran SERIALLY -- 24s, 43s, 48s,
54s of dead time each -- because `ask` blocks and its answer lands in the caller's context
whole. I had the primitive to fan out (ask_many, six workers) and could not afford to use
it, so I asked two helpers instead of six and took the wall-clock hit on both.

Backgrounding is the smaller half of the fix; the buffer is the bigger half, and T204
already removed the reason to keep answers small. With output going to a file and no token
ceiling, a background ask has no reason to hold anything back.

WHAT THIS IS NOT: a seat. No identity, no lock, no cursor, no mailbox, no heartbeat, no
reaper protection -- T171's law stands. A backgrounded ask is a CALL whose result lands
somewhere durable instead of in the caller's window.

THE FAILURE THIS DESIGN IS BUILT AGAINST: this system has 1,324 unopened mailbox items.
"Write it somewhere and check later" is exactly the pattern that produced them. So the
handle is printed immediately, `--get` is one hop, and an unfinished ask says RUNNING
rather than looking empty -- an empty result and a not-yet-finished result must never be
the same reading.

Run: py -m pytest tests/test_t205_ask_bg.py -q
"""
import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import ask_bg  # noqa: E402


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(ask_bg, "ASK_DIR", tmp_path)
    return tmp_path


def test_a_handle_is_minted_and_short_enough_to_type(store):
    h = ask_bg.new_handle()
    assert h and len(h) <= 12 and h.isalnum()


def test_record_round_trips(store):
    ask_bg.write_record("h1", {"status": "running", "prompt": "why"})
    r = ask_bg.read_record("h1")
    assert r["status"] == "running" and r["prompt"] == "why"


def test_unknown_handle_is_honest_not_empty(store):
    """An unknown handle and an empty answer must never read the same. The first is a
    typo; the second is a result."""
    r = ask_bg.read_record("nope")
    assert r is None


def test_running_is_distinguishable_from_finished_with_no_answer(store):
    """THE 1,324-INBOX GUARD. 'not done yet' and 'done, said nothing' are different
    facts, and a reader that renders both as blank teaches you to stop looking."""
    ask_bg.write_record("r1", {"status": "running"})
    ask_bg.write_record("d1", {"status": "done", "answer": ""})
    assert ask_bg.summarize(ask_bg.read_record("r1"))["state"] == "RUNNING"
    assert ask_bg.summarize(ask_bg.read_record("d1"))["state"] == "DONE"


def test_summary_carries_a_next_step(store):
    ask_bg.write_record("r2", {"status": "running", "prompt": "q"})
    s = ask_bg.summarize(ask_bg.read_record("r2"))
    assert s.get("next"), "every state says what the caller does now"


def test_listing_is_newest_first_and_bounded(store):
    for i in range(5):
        ask_bg.write_record(f"h{i}", {"status": "done", "answer": "a", "started": i})
    rows = ask_bg.list_records(limit=3)
    assert len(rows) == 3
    assert rows[0]["started"] >= rows[-1]["started"]


def test_a_crashed_child_does_not_read_as_running_forever(store):
    """A record whose process is gone but whose status never advanced is ORPHANED, not
    running. Without this, a dead child looks busy indefinitely -- the wedge shape this
    repo already knows well."""
    ask_bg.write_record("c1", {"status": "running", "pid": 999999,
                               "started": time.time() - 7200})
    s = ask_bg.summarize(ask_bg.read_record("c1"))
    assert s["state"] == "ORPHANED"
    assert "no longer running" in s["next"].lower() or "re-ask" in s["next"].lower()


def test_result_written_by_the_child_is_readable(store):
    """The child writes the same structured record `ask --json` produces, so the
    background path and the foreground path cannot report different shapes."""
    ask_bg.write_record("h9", {"status": "running"})
    ask_bg.finish("h9", {"ok": True, "answer": "hello", "usd": 0.001})
    r = ask_bg.read_record("h9")
    assert r["status"] == "done" and r["result"]["answer"] == "hello"
    assert ask_bg.summarize(r)["state"] == "DONE"


def test_finish_marks_failure_distinctly(store):
    ask_bg.write_record("h8", {"status": "running"})
    ask_bg.finish("h8", {"ok": False, "why": "STARVED: reasoning ate the budget"})
    s = ask_bg.summarize(ask_bg.read_record("h8"))
    assert s["state"] == "FAILED"
    assert "STARVED" in s.get("why", "")


def test_ask_bg_is_not_a_seat():
    """T171's law, carried to the background path: a call that survives the caller is
    still a call. The moment it takes a lock or a cursor it is a seat with extra steps."""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(ask_bg))
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                names.update(a.name.split("."))
        elif isinstance(n, ast.ImportFrom):
            names.update((n.module or "").split("."))
            for a in n.names:
                names.add(a.name)
        elif isinstance(n, ast.Attribute):
            names.add(n.attr)
        elif isinstance(n, ast.Name):
            names.add(n.id)
    for forbidden in ("runner_lock", "seed_cursor", "roster", "mailbox", "worklive",
                      "heartbeat", "role_queue", "expectations", "Bus"):
        assert forbidden not in names, f"{forbidden}: a background ask is still not a seat"
