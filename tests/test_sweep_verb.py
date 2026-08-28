"""sweep pins: the awareness snapshot -- bounded, fail-open, composite-of-parts.

The composite must call the SAME functions the individual verbs use (no copies to
drift), every section must fail open to UNAVAILABLE with a reason, and the block
must stay bounded -- this is the door the operator's boop-check used to cost four
to six tool calls.
"""
from agent_cli import build_sweep


def test_s1_all_four_sections_render_with_headers():
    out = build_sweep("dsh_agent")
    for header in ("bus", "bench", "health", "moved"):
        assert f"{header}" in out


def test_s2_broken_provider_fails_open_not_traceback():
    import agent_cli
    original = None
    try:
        from agent import bifrost_pull
        original = bifrost_pull.collect_boot_bifrost
        def _boom(*a, **k):
            raise RuntimeError("bus down")
        bifrost_pull.collect_boot_bifrost = _boom
        out = build_sweep("dsh_agent")
    finally:
        if original is not None:
            from agent import bifrost_pull
            bifrost_pull.collect_boot_bifrost = original
    assert "bus   : UNAVAILABLE" in out
    assert "Traceback" not in out


def test_s3_block_is_bounded():
    out = build_sweep("dsh_agent")
    assert len(out.splitlines()) <= 10


def test_s4_never_raises_for_any_agent_id():
    for agent in ("dsh_agent", "", "no_such_seat_xyz"):
        build_sweep(agent)
