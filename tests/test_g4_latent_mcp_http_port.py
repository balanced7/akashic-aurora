"""G4.P2 latent: `python ai_setup_mcp.py --http` crashed with TypeError before serving.

The entry point called `mcp.run(transport="streamable-http", port=a.port)`, but FastMCP.run takes
only a transport and a mount path; the HTTP port lives in `mcp.settings.port`.
"""

import os
import runpy
import subprocess
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
    # Re-executing the door re-installs its process-wide patches (a fresh _StdinSeveredPopen,
    # the stdout proxy, a sys.path entry, AKASHIC_SEAT_DOOR); snapshot them so teardown restores
    # them, or later tests see a Popen that is no longer the imported door's class.
    monkeypatch.setattr(subprocess, "Popen", subprocess.Popen)
    monkeypatch.setattr(sys, "stdout", sys.stdout)
    monkeypatch.setattr(sys, "path", list(sys.path))
    # setenv records the prior state (value or absence) and restores it; delenv on an absent
    # variable records nothing, and the door's setdefault would then outlive this test
    monkeypatch.setenv("AKASHIC_SEAT_DOOR", os.environ.get("AKASHIC_SEAT_DOOR", "mcp"))

    runpy.run_path(str(SCRIPT), run_name="__main__")

    assert seen == [("streamable-http", 18999)]
