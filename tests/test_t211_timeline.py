"""
T211 -- one chronological set across domains. RED first.

THE SIX TURNS THIS WOULD HAVE SAVED, measured 2026-08-06. A wake watcher kept exiting
instantly and I chased it across six turns: arm, drain legacy, arm, ack handoffs, arm,
drain both lanes, arm, pause the fleet, skip cursors, arm. What I could not see from
inside was that MY OWN dogfood asks were manufacturing the pending mail I was draining.
The evidence was all recorded, in four separate domains, and nothing put it in one column:

    00:12  claude    ask --peer deepseek          (my own)
    00:12  deepseek  reply "ALIVE"                (lands in my inbox)
    00:13  claude    wake arm -> seeded over 7 undrainable
    00:14  claude    drain legacy -> parked 7
    00:15  claude    wake arm -> seeded over 10 undrainable   <- it GREW

The growth, in one column, IS the diagnosis. Forensics calls this a super timeline
(plaso/log2timeline): you do not search for the cause, you line the domains up by time
and the cause becomes visible.

IT EMITS A SET, NOT A RENDERING, and that is Daniil's correction adopted. He pushed back
on my "one result set, many lenses" framing: the value at his work comes from CROSS-
MATCHING what one system has and another does not -- and he is right, because almost every
guard in this repo is already a cross-domain set difference (check_door_parity: CLI verbs
minus MCP verbs; check_wiring: tracked files minus reachable files; suite_baseline.delta;
T122's unmapped kinds). Four of our best instruments, one shape, each hand-built. So this
returns rows a future `compare` can diff, never a pre-rendered string.

COVERAGE IS LOAD-BEARING, and more so here than anywhere. A set difference is only as true
as the coverage of BOTH sides: A minus B where B was partially collected manufactures
discoveries. I shipped exactly that bug four minutes before catching it today, when a
three-file test run made ten baseline failures look "fixed". So every result names which
domains were read, which failed, and the window -- and a domain that could not be read is
never silently absent.

Run: py -m pytest tests/test_t211_timeline.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import timeline as TL  # noqa: E402


def _src(name, rows, ok=True, why=""):
    """A fake domain source: (name, callable) -> rows or raise."""
    def _fn(**kw):
        if not ok:
            raise RuntimeError(why or "source down")
        return rows
    return (name, _fn)


def _row(ts, actor, kind, summary, ref="r1"):
    return {"ts": ts, "actor": actor, "kind": kind, "summary": summary, "ref": ref}


def test_rows_from_many_domains_merge_in_time_order():
    """The whole point: interleaving is what makes the cause visible."""
    r = TL.gather(sources=[
        _src("git", [_row(300, "claude", "commit", "T197")]),
        _src("events", [_row(100, "claude", "ask_completed", "handle a"),
                        _row(200, "deepseek", "reply", "ALIVE")]),
    ])
    assert [x["ts"] for x in r["rows"]] == [100, 200, 300]
    assert [x["domain"] for x in r["rows"]] == ["events", "events", "git"]


def test_every_row_carries_a_ref_so_it_can_be_pivoted():
    """Forensics pivoting: a row you cannot follow is a dead end. This is also what
    makes rows valid INPUT to a later compare."""
    r = TL.gather(sources=[_src("events", [_row(1, "a", "k", "s", ref="event:x")])])
    assert r["rows"][0]["ref"] == "event:x"
    assert r["rows"][0]["domain"] == "events"


def test_a_failed_domain_is_named_never_silently_absent():
    """THE LOAD-BEARING PIN. A timeline missing a domain looks like a timeline where
    nothing happened in that domain -- which is how a set difference invents findings.
    I shipped that exact bug today and caught it four minutes later."""
    r = TL.gather(sources=[
        _src("events", [_row(1, "a", "k", "s")]),
        _src("git", [], ok=False, why="git not reachable"),
    ])
    assert "git" in r["coverage"]["failed"]
    assert "events" in r["coverage"]["read"]
    assert "git" not in r["coverage"]["read"]
    assert any("git" in b for b in r["blind"])


def test_an_empty_domain_is_distinct_from_a_failed_one():
    """'Nothing happened there' and 'I could not look there' are different facts, and
    collapsing them is the one-word-two-meanings bug in a fifth costume."""
    r = TL.gather(sources=[
        _src("git", []),
        _src("events", [], ok=False),
    ])
    assert "git" in r["coverage"]["read"] and r["coverage"]["counts"]["git"] == 0
    assert "events" in r["coverage"]["failed"]


def test_the_window_is_reported_and_applied():
    r = TL.gather(sources=[_src("events", [_row(10, "a", "k", "old"),
                                           _row(1000, "a", "k", "new")])],
                  since=100)
    assert [x["summary"] for x in r["rows"]] == ["new"]
    assert r["coverage"]["since"] == 100


def test_rows_are_data_not_a_rendering():
    """Daniil's correction: this must compose with a future set-difference, so it
    returns rows a compare can diff -- never a pre-formatted string."""
    r = TL.gather(sources=[_src("events", [_row(1, "a", "k", "s")])])
    assert isinstance(r["rows"], list) and isinstance(r["rows"][0], dict)
    for field in ("ts", "domain", "actor", "kind", "summary", "ref"):
        assert field in r["rows"][0]


def test_a_row_missing_a_timestamp_is_kept_and_flagged():
    """Dropping undateable evidence is how a timeline lies by omission. Forensics keeps
    it and marks it, because 'when' unknown is not 'did not happen'."""
    r = TL.gather(sources=[_src("events", [{"actor": "a", "kind": "k",
                                            "summary": "no ts", "ref": "x"}])])
    assert len(r["rows"]) == 1
    assert r["rows"][0]["ts"] is None
    assert r["coverage"]["undated"] == 1


def test_undated_rows_sort_last_not_at_epoch():
    """Sorting a None to 0 would place unknown-time evidence at the dawn of the record
    and silently rewrite the story."""
    r = TL.gather(sources=[_src("events", [{"summary": "undated", "ref": "u"},
                                           _row(5, "a", "k", "dated")])])
    assert [x["summary"] for x in r["rows"]] == ["dated", "undated"]


@pytest.mark.parametrize("raw,expect", [
    ("1786079938", 1786079938.0),      # git's %at -- a BARE EPOCH STRING
    (1786079938, 1786079938.0),
    ("", None), (None, None), ("not a time", None),
    # 0 from ANY source means "could not read", never 1 Jan 1970 -- as an int, as a
    # string, or as a parser's failure return.
    (0, None), ("0", None), (0.0, None),
])
def test_epoch_parses_real_stamps_and_refuses_to_invent_1970(raw, expect):
    """CAUGHT LIVE on this module's first real run, one function below the pin that
    forbids exactly this. git's %at is a bare epoch STRING; to_epoch parses ISO and
    returned 0.0 for every commit, so the whole of git got stamped 1970 and the `since`
    filter dropped it -- coverage read git: 0 while six commits sat in the window.

    A 0 from a parser means 'could not read', never '1 Jan 1970'. Trusting it is how
    undateable evidence silently becomes the OLDEST evidence and rewrites the story.

    The original pins passed because they fed dicts straight in and never exercised the
    parse -- a pin that supplies its own inputs tests the mechanism, not the wiring.
    Third instance of that class today."""
    got = TL._epoch(raw)
    if expect is None:
        assert got is None, f"{raw!r} must be undateable, not {got}"
    else:
        assert got == expect


def test_iso_stamps_still_parse():
    """The other half: rejecting 0 must not break the format that DOES parse. Events
    carry ISO stamps and they have to survive the epoch-string branch above."""
    got = TL._epoch("2026-08-07T01:00:00Z")
    assert got is not None and got > 1_000_000_000


def test_git_rows_carry_readable_timestamps():
    """The end-to-end version of the pin above: real git output, real parse."""
    try:
        rows = TL._git_rows(limit=3)
    except Exception:
        pytest.skip("git not reachable here")
    assert rows, "git log produced no rows"
    stamps = [TL._epoch(r["ts"]) for r in rows]
    assert all(s is not None and s > 1_000_000_000 for s in stamps), stamps


def test_gather_never_raises_on_a_broken_source():
    def explode(**kw):
        raise ValueError("boom")
    r = TL.gather(sources=[("bad", explode)])
    assert r["rows"] == [] and "bad" in r["coverage"]["failed"]


def test_default_sources_name_the_real_domains():
    """Registered by name so a missing domain is visible in the coverage report rather
    than being absent from the design."""
    names = {n for n, _ in TL.default_sources()}
    assert {"events", "git", "tasks"} <= names
