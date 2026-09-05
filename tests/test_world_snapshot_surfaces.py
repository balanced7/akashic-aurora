"""Door-parity pins for the read-only WorldSnapshot scaffold.

The MCP half runs in a fresh child process.  Importing ``ai_setup_mcp`` while
pytest capture owns stdio can cache fixture streams in the MCP runtime and
contaminate unrelated transport tests on Windows.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import agent_cli
from core.comm.toolbox import TOOLS, ToolBox


ROOT = Path(__file__).resolve().parents[1]


def test_glance_parser_names_the_projection_and_bounds():
    args = agent_cli.build_parser().parse_args(
        ["glance", "program", "--brief", "--max-items", "3", "--compact"]
    )

    assert args.fn is agent_cli.cmd_glance
    assert args.glance_projection == "program"
    assert args.brief is True
    assert args.max_items == 3
    assert args.compact is True


def test_real_cli_emits_the_versioned_snapshot_contract():
    result = subprocess.run(
        [
            sys.executable,
            "agent_cli.py",
            "glance",
            "program",
            "--max-items",
            "2",
            "--compact",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "world-snapshot/v1"
    assert payload["projection_version"] == "subject-attention/v1"
    assert payload["bounds"]["item_limit"] == 2
    assert payload["capabilities"]["runtime_attention"]["state"] == "UNCHECKABLE"


def test_mcp_glance_twin_emits_the_same_semantic_contract_in_fresh_process():
    code = (
        "import asyncio,sys,ai_setup_mcp;"
        "sys.__stdout__.write(asyncio.run(ai_setup_mcp.glance("
        "projection='program',max_items=2,brief=False,compact=True)))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "world-snapshot/v1"
    assert payload["projection_version"] == "subject-attention/v1"
    assert payload["bounds"]["item_limit"] == 2
    assert payload["capabilities"]["runtime_attention"]["state"] == "UNCHECKABLE"


def test_stdio_mcp_advertises_and_calls_glance_end_to_end():
    """Prove the real stdio membrane, not only the delegated Python wrapper."""
    async def flow():
        import asyncio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(
            command=sys.executable,
            args=[str(ROOT / "ai_setup_mcp.py")],
            cwd=str(ROOT),
            env={**os.environ, "_AISETUP_TEST_ISOLATED": "1", "REDIS_DB": "15"},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
                assert "glance" in names
                result = await asyncio.wait_for(
                    session.call_tool(
                        "glance",
                        {
                            "projection": "program",
                            "max_items": 1,
                            "brief": True,
                            "compact": True,
                        },
                    ),
                    timeout=10.0,
                )
                text = "".join(getattr(block, "text", "") for block in result.content)
                payload = json.loads(text)
                assert payload["schema_version"] == "operational-brief/v1"
                assert payload["identity_authority"] == "none"
                assert payload["bounds"]["returned_items"] <= 1

    import asyncio

    asyncio.run(flow())


def test_toolbox_glance_is_schema_visible_and_reads_its_bound_world(tmp_path):
    schema_names = {row["function"]["name"] for row in TOOLS}
    assert "glance" in schema_names

    ledger_path = tmp_path / "state" / "coord" / "tasks.json"
    ledger_path.parent.mkdir(parents=True)
    ledger_path.write_text(
        json.dumps(
            {
                "seq": 1,
                "tasks": [
                    {
                        "id": "T900",
                        "title": "Bound-world proof",
                        "status": "in_progress",
                        "owner": "test",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    toolbox = ToolBox(
        tmp_path,
        allow_exec=False,
        trust=False,
        allow_secrets=False,
        confirm=lambda _prompt: False,
    )

    payload = json.loads(toolbox.glance(max_items=1, brief=False))

    assert payload["items"][0]["object_ref"] == "task:T900"
    assert payload["sources"][0]["drill"] == str(ledger_path)


