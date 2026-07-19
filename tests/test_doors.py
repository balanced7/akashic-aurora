"""DOORS.md v0 pins (master-map M2): the CLI door reference is grounded in the real parser,
truthful about inputs, and deterministic. Run: py -m pytest tests/test_doors.py -q
"""
from scripts.gen_doors import cli_verbs, render


def test_known_verbs_present_with_inputs():
    verbs = cli_verbs()
    assert "boot" in verbs and "handoff" in verbs and "bifrost-send" in verbs
    # bifrost-send's declared inputs must include its real flags (the door's own truth)
    flags = {f for f, *_ in verbs["bifrost-send"]["args"]}
    assert "--text-file" in flags and "--to" in flags and "--broadcast" in flags
    # a required positional is marked required (agent_id is required on bifrost-send)
    assert any(f == "<agent_id>" and req for f, req, *_ in verbs["bifrost-send"]["args"])


def test_render_is_deterministic_and_stamped():
    one = render(cli_verbs())
    assert one == render(cli_verbs())          # same parser -> same doors
    assert "Status: current" in one            # doc-currency law
    assert "CLI door" in one and "KNOWN GAP" in one   # honest about what v0 does not cover
