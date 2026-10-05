"""G4.P2 latent: `python ai_setup_mcp.py --http` crashed with TypeError before serving.

The entry point called `mcp.run(transport="streamable-http", port=a.port)`, but FastMCP.run takes
only a transport and a mount path; the HTTP port lives in `mcp.settings.port`.
"""

import os
import runpy
import sys
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

os.environ.setdefault("REDIS_DB", "15")

SCRIPT = Path(__file__).resolve().parents[1] / "ai_setup_mcp.py"


def test_http_entry_point_serves_on_the_requested_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """--http --port N starts the streamable-HTTP transport with settings.port == N."""
    seen: list[tuple[str, int]] = []

    def fake_run(self: FastMCP, transport: str = "stdio", mount_path: str | None = None) -> None:
        """Stand in for FastMCP.run with its real signature; record what it would serve."""
        assert mount_path is None
        seen.append((transport, self.settings.port))

    monkeypatch.setattr(FastMCP, "run", fake_run)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--http", "--port", "18999"])

    runpy.run_path(str(SCRIPT), run_name="__main__")

    assert seen == [("streamable-http", 18999)]
