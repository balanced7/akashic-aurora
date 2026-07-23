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

---

## SECOND CAPTURE — narrow re-ask after Daniel widened the round (2026-07-23 ~02:10)

**Capture honesty:** HIGH ENGAGEMENT this time (direct answers to the three questions).
**CLIPPED — tail owed:** the capture ends mid-sentence in the singleton-concurrency
section ("Since all agent sessions share one Python process:"); everything after that
line was lost at the capture surface. Stamped per the W-a discipline (kimi R1 genus:
a doc that cites fine and is wrong at the tail). Prompt asked A (long-poll pitfalls),
B (lease-to-process-lifetime failure modes), C (singleton topology tradeoffs).

**Load-bearing takeaways for the reconcile:**
1. A1 must be WINDOWED, not parked: MCP clients enforce per-tool timeouts (~30–120s);
   an over-window block orphans the server task while the client aborts. Design:
   poll-with-short-timeout (redis xread block <= ~5s per call, hard ceiling below the
   client window), propagate CancelledError down to the xread, and mind to_thread pool
   depletion when many awaits park concurrently.
2. L3 lease design corrected (my "structurally impossible" was too strong): pure
   process-binding fails on SIGKILL/Task-Manager kills. Right shape = stdin-EOF death
   detection (graceful: XGROUP DELCONSUMER + DEL lease) PLUS ephemeral lease with ~2s
   heartbeat and ~5s TTL (violent: TTL clears, fleet reclaims via XPENDING/XCLAIM).
   Zombie window: 1800s today -> ~5s, not zero.
3. Singleton door makes IDENTITY MANDATORY (bearer/headers/_meta replace process-level
   isolation; contextvars for per-session state). This converges with SEC-01/S-0 and
   R001 Part B: a THIRD Daniel thread now points at the same missing primitive —
   enforced identity + caps. The singleton cannot ship before it.

### VERBATIM (second capture)

Here is the direct analysis and architectural path for your three concerns:

1. Long-Poll / Parked Calls Over MCP

Holding long-poll calls directly inside an MCP tool execution (e.g., waiting on Redis) introduces critical failure modes:

Client-Side Timeouts: MCP clients (Claude Desktop, Cursor, Custom SDK wrappers) enforce strict per-tool timeouts (typically 30–120s). If a tool execution blocks waiting on a Redis stream event longer than this window, the client aborts the JSON-RPC request at the transport layer, while the server continues holding thread/task resources (a orphan task).

Cancellation Semantics:

In stdio: Cancellation relies on the client sending a $/cancelRequest notification with the target requestId. FastMCP/official Python SDK exposes this via contextvars (ctx.session / ctx.request_context). If your long-poll function is not checking asyncio.CancelledError or passing a CancellationToken down to redis.xread(), the worker stays parked in the thread pool indefinitely.

In Streamable-HTTP: HTTP client disconnects (TCP aborts or client timeout) close the POST request stream. Unmanaged long-polls will leak server tasks unless bound to request.is_disconnected().

Known Failure Modes:

Thread Pool Starvation: Synchronous long-polling offloaded via asyncio.to_thread depletes the default thread pool executor if multiple agents park concurrently.

Backpressure & Memory Leaks: Uncollected tasks retaining closure frames.

Mitigation

Do not block directly in the tool call if the wait duration is unknown or >15 seconds. Use a poll-with-short-timeout model:

Python
async def poll_stream_tool(stream_key: str, last_id: str = "$", timeout_ms: int = 5000) -> dict:
    try:
        # Enforce hard ceiling below client timeout threshold
        events = await redis.xread({stream_key: last_id}, count=10, block=timeout_ms)
        return {"status": "ok", "events": events}
    except asyncio.CancelledError:
        # Proper MCP cancellation cleanup
        raise

2. Binding Consumer Lease Lifetime to Server Lifecycle

Relying on TTL exipration leaves "zombie" lease holders in Redis streams when an MCP subprocess crashes or gets killed non-gracefully (SIGKILL, Windows Task Manager, client unexpected exit).

Implementation Pattern

Pair a Process/Session Lifetime Guard with an Ephemeral Lease + Heartbeat Loop:

Process Death Binding (stdio): In stdio, the stdio pipe closes when the client or parent process terminates. Detect stdin EOF to trigger an immediate, graceful shutdown:

Python
import sys, asyncio

async def monitor_parent_death(cleanup_callback):
    loop = asyncio.get_running_loop()
    # Read stdin line-by-line; EOF indicates pipe broken/parent died
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:  # EOF reached
            await cleanup_callback()
            break


Redis Lease Design:

Upon connection, tool/server registers consumer consumer_id with a Redis Hash HSET lease:<consumer_id> heartbeat <timestamp>.

Run a background asyncio.Task that sends a PEXPIRE / timestamp refresh to Redis every 2 seconds.

On graceful exit (or stdin EOF detection), execute XGROUP DELCONSUMER and DEL lease:<consumer_id>.

If the process dies violently (SIGKILL), the 5-second TTL clears the consumer, allowing the fleet to claim pending messages via XPENDING/XCLAIM.

3. Migration: Stdio Subprocesses → Streamable-HTTP Singleton

Transitioning from local stdio subprocesses to a centralized Streamable-HTTP server requires handling state, security, and context propagation differently:

[ASCII topology diagram: Streamable-HTTP Singleton — FastMCP engine, session context
(agent/session mapping, bearer auth), shared thread pool (concurrent tools, async Redis
IO) over Redis Streams + UI/Runners/Fleet — reproduced in full in the raw capture file]

Protocol & State Shift Matrix
Dimension / stdio Per-Session / Streamable-HTTP Singleton
Lifecycle: Process bound to single agent lifecycle. / Long-running daemon; lives independently of agents.
Isolation: Hard OS process isolation per session. / Shared memory space; isolation must be enforced via contextvars or explicit session IDs.
Client Transport: OS Pipe (stdin/stdout). / Single /mcp HTTP endpoint (POST for requests, GET/SSE for streaming).
Authentication: Implicit (Local process ownership). / Mandatory (Bearer tokens, HTTP headers, or network binding).

Architectural Requirements for the Singleton

Session & Agent Mapping:
Pass the invoking agent_id or session context via custom HTTP Headers (e.g., X-Agent-ID: agent-42) or MCP Request Metadata (_meta). FastMCP captures these headers into request context (ctx.request_context.headers), replacing process-level isolation.

Concurrency Architecture:
Since all agent sessions share one Python process:
[CLIPPED — tail owed: capture ended here mid-sentence]
