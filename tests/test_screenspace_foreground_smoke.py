"""Smoke: ForegroundTracker pure seam (subscribe + on_foreground_change) is testable
without Windows — the event-wiring contract the RED pins will drive synthetically.
"""


def test_tracker_pure_seam_subscribe_and_deliver():
    from core.screenspace.foreground import ForegroundTracker

    t = ForegroundTracker()
    seen = []

    t.subscribe(lambda name: seen.append(name))

    assert t.focus is None
    assert t.gen == 0

    t.on_foreground_change("chrome.exe")
    assert t.focus == "chrome.exe"
    assert t.gen == 1
    assert seen == ["chrome.exe"]

    t.on_foreground_change("notepad.exe")
    assert t.focus == "notepad.exe"
    assert t.gen == 2
    assert seen == ["chrome.exe", "notepad.exe"]


def test_tracker_gen_is_monotone():
    from core.screenspace.foreground import ForegroundTracker

    t = ForegroundTracker()
    t.on_foreground_change("a")
    t.on_foreground_change("b")
    t.on_foreground_change("c")
    assert t.gen == 3


def test_tracker_none_delivery_is_legal():
    from core.screenspace.foreground import ForegroundTracker

    t = ForegroundTracker()
    seen = []
    t.subscribe(lambda n: seen.append(n))
    t.on_foreground_change(None)  # e.g. foreground lost — legal, delivered as None
    assert t.focus is None
    assert t.gen == 1
    assert seen == [None]
