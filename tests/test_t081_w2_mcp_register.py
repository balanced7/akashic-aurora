"""T081-W2 pins: the MCP-registration helper emits a user-scoped, absolute-path command."""
import importlib.util
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "mcp_register", Path(__file__).resolve().parent.parent / "scripts" / "mcp_register.py")
mcp_register = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcp_register)


def test_command_is_user_scoped_and_absolute():
    cmd = mcp_register.registration_command()
    assert "claude mcp add --scope user akashic-aurora" in cmd
    assert "ai_setup_mcp.py" in cmd
    # the script path in the command must be absolute (the whole point of W2)
    path = cmd.split('py "', 1)[1].rstrip('"')
    assert os.path.isabs(path)


def test_json_snippet_shape():
    srv = mcp_register.registration_json()["mcpServers"]["akashic-aurora"]
    assert srv["command"] == "py"
    assert srv["args"][0].endswith("ai_setup_mcp.py")
    assert os.path.isabs(srv["args"][0])


def test_path_points_at_a_real_file():
    # portability: the computed path resolves to the actual server script in this repo
    assert mcp_register._mcp_path().is_file()
