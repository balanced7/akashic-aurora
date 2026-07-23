"""MCP-door concurrency fence -- diagnosis pins for the parallel-batch wedge.

Context (2026-07-23, Daniel's charter: "Can we modify our mcp to allow concurrent
calls? do we need to swap it out"): akashic MCP calls inside a parallel tool batch
have been observed to wedge the whole batch until user interrupt, while solo calls
are healthy (harness memory, chasing since 2026-07-16).

Code-reading diagnosis to be CONFIRMED here (receipts, not assertions):
  - mcp SDK 1.27.0 lowlevel server spawns a task PER request (server.py:678
    tg.start_soon) -> batched calls arrive concurrently;
  - FastMCP dispatches SYNC tool fns INLINE on the event loop (no to_thread in the
    tools path) -> while any tool body runs, the loop is starved: no pings, no other
    responses, no cancellation handling;
  - ai_setup_mcp._run additionally swaps the process-global sys.stdout
    (contextlib.redirect_stdout) -> only safe BECAUSE dispatch is inline-serial; any
    move to threaded/async dispatch without a capture lock risks protocol corruption.

Pins (C1 must pass today; C2/C3 are the PRE-REGISTERED ACCEPTANCE for the fix and
are expected to FAIL before it lands -- marked xfail, flip to pass when the door
gains non-starving dispatch):
  C1  channel integrity: two concurrent call_tool on one session both return, each
      carries its OWN payload, and the session still answers afterwards (no wedge,
      no cross-contamination of captured stdout).
  C2  loop liveness: a fast call issued while a slow call runs completes BEFORE the
      slow one finishes (pre-fix: it queues behind = serialized dispatch).
  C3  ping under load: protocol ping answered <1s while a slow tool runs (pre-fix:
      starved until the tool returns).

Every await is wrapped in wait_for so a reproduced wedge FAILS LOUD instead of
hanging the suite.

Run: py -m pytest tests/test_mcp_concurrent_calls.py -q --timeout=120
"""
import asyncio
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SERVER = os.path.join(ROOT, "ai_setup_mcp.py")

SLOW_S = 2.0        # slow tool sleep
FAST_BUDGET = 1.5   # fast call must beat this once dispatch stops starving
CALL_CAP = 25.0     # hard per-await cap: a wedge fails loud here


async def _open_session():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(
        command=sys.executable, args=[SERVER], cwd=ROOT,
        env={**os.environ, "_AISETUP_TEST_ISOLATED": "1"},
    )
    return stdio_client(params)


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


async def _call(session, tag, seconds):
    t0 = time.monotonic()
    res = await asyncio.wait_for(
        session.call_tool("diag_echo_slow", {"tag": tag, "seconds": seconds}),
        timeout=CALL_CAP,
    )
    text = "".join(c.text for c in res.content if getattr(c, "text", None))
    return text, time.monotonic() - t0


# ------------------------------------------------------------------ C1: integrity
def test_c1_concurrent_batch_returns_intact():
    async def flow():
        from mcp import ClientSession
        client = await _open_session()
        async with client as (read, write):
            async with ClientSession(read, write) as s:
                await asyncio.wait_for(s.initialize(), timeout=CALL_CAP)
                (slow_txt, slow_dt), (fast_txt, fast_dt) = await asyncio.wait_for(
                    asyncio.gather(
                        _call(s, "SLOW", SLOW_S),
                        _call(s, "FAST", 0.1),
                    ),
                    timeout=CALL_CAP,
                )
                # each response carries its own payload, never the sibling's
                assert "DIAG[SLOW]" in slow_txt and "DIAG[FAST]" not in slow_txt
                assert "DIAG[FAST]" in fast_txt and "DIAG[SLOW]" not in fast_txt
                # session survives the batch (the wedge symptom = it would not)
                after, _ = await _call(s, "AFTER", 0.05)
                assert "DIAG[AFTER]" in after
                return slow_dt, fast_dt
    slow_dt, fast_dt = _run(flow())
    # diagnosis receipt, printed either way: serialized dispatch shows fast_dt ~= SLOW_S
    print(f"\n[fence receipt] slow={slow_dt:.2f}s fast={fast_dt:.2f}s "
          f"(fast waited behind slow: {fast_dt >= SLOW_S * 0.9})")


# ------------------------------------------------------- C2: pre-registered acceptance
# (xfail marker REMOVED 2026-07-23 when O1 landed -- this is now a hard requirement)
def test_c2_fast_call_not_starved_by_slow():
    async def flow():
        from mcp import ClientSession
        client = await _open_session()
        async with client as (read, write):
            async with ClientSession(read, write) as s:
                await asyncio.wait_for(s.initialize(), timeout=CALL_CAP)
                slow_task = asyncio.create_task(_call(s, "SLOW", SLOW_S))
                await asyncio.sleep(0.2)          # slow is in flight first
                _, fast_dt = await _call(s, "FAST", 0.1)
                await asyncio.wait_for(slow_task, timeout=CALL_CAP)
                return fast_dt
    fast_dt = _run(flow())
    assert fast_dt < FAST_BUDGET, (
        f"fast call took {fast_dt:.2f}s -- it queued behind the {SLOW_S}s tool "
        f"(loop-starving dispatch)")


def test_c3_ping_answered_under_load():
    async def flow():
        from mcp import ClientSession
        client = await _open_session()
        async with client as (read, write):
            async with ClientSession(read, write) as s:
                await asyncio.wait_for(s.initialize(), timeout=CALL_CAP)
                slow_task = asyncio.create_task(_call(s, "SLOW", SLOW_S))
                await asyncio.sleep(0.2)
                t0 = time.monotonic()
                await asyncio.wait_for(s.send_ping(), timeout=CALL_CAP)
                ping_dt = time.monotonic() - t0
                await asyncio.wait_for(slow_task, timeout=CALL_CAP)
                return ping_dt
    ping_dt = _run(flow())
    assert ping_dt < 1.0, f"ping took {ping_dt:.2f}s under a running sync tool"


# ------------------------------------------------ C4: N=20 mixed-batch integrity (O1 P-5)
def test_c4_twenty_way_mixed_batch_intact():
    N = 20
    async def flow():
        from mcp import ClientSession
        client = await _open_session()
        async with client as (read, write):
            async with ClientSession(read, write) as s:
                await asyncio.wait_for(s.initialize(), timeout=CALL_CAP)
                jobs = [
                    _call(s, f"T{i}", 1.0 if i % 5 == 0 else 0.05)
                    for i in range(N)
                ]
                results = await asyncio.wait_for(asyncio.gather(*jobs), timeout=60)
                for i, (text, _dt) in enumerate(results):
                    assert f"DIAG[T{i}]" in text, f"call {i} lost its own payload"
                    others = sum(1 for j in range(N) if j != i and f"DIAG[T{j}]" in text)
                    assert others == 0, f"call {i} contains {others} sibling payload(s)"
                after, _ = await _call(s, "FINAL", 0.05)
                assert "DIAG[FINAL]" in after
    _run(flow())
