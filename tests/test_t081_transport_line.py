"""T081-W1 pins (pre-registered, method-baseline: pins before impl).

The boot transport line states THIS seat's door -- 'can I use tools?' -- before any
project context. The door is set by the invocation path (MCP tool server / runner /
bare CLI each stamp AKASHIC_SEAT_DOOR); an unset or unknown signal degrades to
cli-shell, the P1 fragility case, and the line must name its own remedy (T081-W2).
"""
import agent_cli


def _line(door=None, detail=None):
    return agent_cli._transport_line(door=door, detail=detail)


def test_mcp_door():
    assert _line("mcp").startswith("# door: MCP-native")


def test_toolbox_door_renders_detail():
    out = _line("toolbox", "20 tools, write=on, exec=on")
    assert out.startswith("# door: ToolBox-native")
    assert "20 tools, write=on, exec=on" in out


def test_cli_shell_names_the_remedy():
    out = _line("cli-shell")
    assert "CLI-shell" in out
    assert "W2" in out  # the remedy points at the user-scoped-MCP slice


def test_cli_shell_does_not_assert_what_it_cannot_observe():
    """W63 (2026-07-25): this pin used to require the line say tools are 'NOT attached'.

    That is a claim the process cannot make: a bare CLI boot from a seat that DOES hold
    the MCP door renders this same line. It happened live -- CLI boot said NOT attached
    while MCP boot, same seat same call, said MCP-native -- and the reader was sent to a
    remedy it did not need. The safe DEFAULT is still cli-shell; only the wording changes.
    """
    out = _line("cli-shell").lower()
    assert "cannot tell" in out or "if yours are attached" in out, \
        "the line must hedge a door it cannot observe, not assert its absence"


def test_unknown_door_degrades_to_cli_shell():
    # a garbage signal must never crash or mislead -- treat as cli-shell
    assert "CLI-shell" in _line("wat")


def test_unset_env_defaults_to_cli_shell(monkeypatch):
    monkeypatch.delenv("AKASHIC_SEAT_DOOR", raising=False)
    monkeypatch.delenv("AKASHIC_SEAT_DOOR_DETAIL", raising=False)
    assert "CLI-shell" in agent_cli._transport_line()


def test_env_signal_is_read(monkeypatch):
    monkeypatch.setenv("AKASHIC_SEAT_DOOR", "mcp")
    monkeypatch.delenv("AKASHIC_SEAT_DOOR_DETAIL", raising=False)
    assert "MCP-native" in agent_cli._transport_line()


def test_line_is_a_single_comment_line():
    # boot header lines are '#'-prefixed comments; the transport line must match and not wrap
    for door in ("mcp", "toolbox", "cli-shell", "wat"):
        out = _line(door)
        assert out.startswith("# ")
        assert "\n" not in out
