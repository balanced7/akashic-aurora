"""One-off smoke check: does core/screenspace import cleanly and expose the surface?"""


def test_package_imports_and_surface():
    from core.screenspace import capture, shadow, peek, delta, refs, read_text
    from core.screenspace.capture import screen
    from core.screenspace.engine import (
        ObservationStream,
        ScreenResult,
        ScreenDelta,
        Ref,
        TextResult,
        peek as _peek,
    )

    assert callable(peek) and callable(delta) and callable(refs) and callable(read_text)
    assert callable(screen)
    assert hasattr(capture, "screen")
    assert callable(shadow.pulse)
    # type shapes exist
    for t in (ScreenResult, ScreenDelta, Ref, TextResult):
        assert t is not None


def test_verbs_return_structured_not_bare():
    from core.screenspace import peek, delta, refs, read_text

    r = peek(level="L0")
    assert r.level == "L0"
    assert r.source == "screen"
    assert isinstance(r.gen, int) and r.gen >= 0

    d = delta(since_gen=0)
    assert d.current_gen >= 0

    rr = refs(scope="foreground")
    assert isinstance(rr, list)

    t = read_text(scope="foreground", method="uia")
    assert t.source == "screen"


def test_gen_clock_is_monotone():
    from core.screenspace.engine import ObservationStream

    s = ObservationStream()
    g1 = s.observe("a")
    g2 = s.observe("b")
    assert g2 == g1 + 1


def test_delta_is_pure_fn_of_since_gen():
    from core.screenspace.engine import ObservationStream

    s = ObservationStream()
    s.observe("a")
    s.observe("b")
    d = s.delta_since(1)
    assert d.current_gen == 2
    # a future since_gen yields empty, not fabricated
    d2 = s.delta_since(999)
    assert d2.focus_trail == []


def test_capture_degrades_honestly_or_succeeds():
    from core.screenspace.capture import screen

    f = screen()
    # structured either way: available=True with pixels, or available=False with reason
    assert (f.available and f.pixels) or (not f.available and f.refuse_reason)
