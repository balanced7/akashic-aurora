# Frontier report — Gemini (web) on MCP-door concurrency

Status: current · Type: report (frontier advisory, verbatim) · Arc: interface / System-5 door
Seats: gemini-web (author), claude (captor) · Date: 2026-07-23
Round: mcp-concurrency-and-boot-ergonomics-opening-claude-2026-07-23.md

**Capture honesty:** the web surface engaged the prompt as a greeting, not a deep answer —
it did NOT address the three specific questions (thread-local proxy pitfalls; better
patterns than the ones we rejected; SDK 1.27 cancellation behavior). Google AI Mode
FAILED to answer at all (`AI_MODE_ERROR: no AI Mode answer captured (region/login/UI
drift)`). Weight accordingly: ADVISORY, LOW ENGAGEMENT. Kept verbatim per
research-full-fidelity doctrine; the reconcile should lean on deepseek + kimi.

**What is usable (three grains):**
1. Independent confirmation of the pristine-stdout law: any stray `print()`/stdout write
   corrupts JSON-RPC framing and drops the connection — supports the opening's capture
   redesign and the Popen-DEVNULL fix.
2. Windows-specific: recommend `asyncio.WindowsProactorEventLoopPolicy()` on win32
   entrypoints when subprocesses/pipes are involved — check what policy `mcp.run()`
   inherits before O1 lands (our `_run_script` subprocesses will fire from worker threads
   post-O1, but the policy line is cheap insurance).
3. FastMCP 2.x/3.x standalone has import/interface shifts (parameter injection, transport
   setup) — an independent cost marker on O4 (swap), which the opening already rejects.

---

## VERBATIM CAPTURE (gemini web, invisible Chrome, 2026-07-23 ~01:40)

E:\AI-Setup\scripts\gemini_web.py:126: UserWarning: navigator_platform is False, but an override (navigator_platform_override) was provided, which is probably not what you intended to do
  _STEALTH = Stealth(
========================= GEMINI (web) =========================
Welcome, Fleet HQ! I see you've set up your multi-agent architecture on Windows 11 with Python 3.11 using stdio transport and the official Python MCP SDK (FastMCP v1.27.0).

[!NOTE]
Environment Snapshot:

OS: Windows 11 (Watch out for standard I/O buffer flushing, \r\n line-ending pollution, and non-blocking I/O quirks on Win32 event loops!)

Transport: stdio (Requires strictly pristine stdout stream reservation exclusively for JSON-RPC framing)

SDK: mcp.server.fastmcp (v1.27.0)

Key Operational Guidance for Stdio Fleets on Windows

Stdout Pollution Guardrails:
Ensure no worker agent, library, or logging statement writes directly to sys.stdout or uses plain print(). Any arbitrary text printed to stdout will corrupt the JSON-RPC packet stream and drop the MCP connection.

Mitigation: Explicitly redirect sys.stderr for all runtime/debug logging, or configure logging to use a dedicated file handler.

Windows Event Loop & Asyncio:
On Windows 11 under Python 3.11, ensure your entrypoints handle event loop policies gracefully—especially when subprocesses or pipes are involved:

Python
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


Subprocess/Stdio Non-Blocking I/O:
When running multiple agents communicating over pipes, ensure stdin/stdout streams are kept in binary/unbuffered mode or explicitly flushed if custom IO wrappers are used.

FastMCP Versioning Context:
Note that mcp.server.fastmcp in mcp==1.27.0 is the original bundled FastMCP 1.0 engine. If you plan on upgrading to FastMCP 2.x/3.x (fastmcp standalone package), be aware of import/interface shifts (e.g., parameter injection and transport execution setups).

How can I assist your dev fleet today? Are you working through a specific bug (e.g., JSON-RPC deserialization errors, pipe hanging, context passing), framing out custom dynamic tools/resources, or designing inter-agent communication flows?

========================= GOOGLE AI MODE =========================
AI_MODE_ERROR: no AI Mode answer captured (region/login/UI drift). Try --login or --headed.

[engine=playwright, stealth=True, browser_mode=invisible]
