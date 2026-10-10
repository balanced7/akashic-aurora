"""Phase 0 control (RFC #70): the PyPI iroh 1.1.0 binding, two endpoints on loopback, relays off."""

import asyncio
import json
import statistics
import time

import iroh  # pyright: ignore[reportMissingImports]  # ty: ignore[unresolved-import]  # the control runs in its own venv (see report.md)

ALPN = b"aurora/bench/0"
_TASKS: set[asyncio.Task] = set()


async def ep():
    opts = iroh.EndpointOptions(
        preset=iroh.preset_minimal(), bind_addr="127.0.0.1:0", alpns=[ALPN], relay_mode=iroh.RelayMode.disabled()
    )
    return await iroh.Endpoint.bind(opts)


async def handle(conn):
    try:
        while True:
            bi = await conn.accept_bi()
            recv, send = bi.recv(), bi.send()
            data = await recv.read_to_end(4 * 1024 * 1024)
            await send.write_all(len(data).to_bytes(8, "big"))
            await send.finish()
    except Exception:
        pass


_tasks: set = set()


async def serve(server):
    while True:
        inc = await server.accept_next()
        if inc is None:
            return
        accepting = await inc.accept()
        conn = await accepting.connect()
        task = asyncio.create_task(handle(conn))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)


async def roundtrip(conn, payload):
    bi = await conn.open_bi()
    send, recv = bi.send(), bi.recv()
    await send.write_all(payload)
    await send.finish()
    return int.from_bytes(await recv.read_to_end(8), "big")


async def main():
    server, client = await ep(), await ep()
    task = asyncio.create_task(serve(server))
    addr = server.addr()
    connects = []
    for _ in range(20):
        t = time.perf_counter()
        conn = await client.connect(addr, ALPN)
        await roundtrip(conn, b"x")
        connects.append((time.perf_counter() - t) * 1000)
        conn.close(0, b"")
    conn = await client.connect(addr, ALPN)
    out = {"binding": "iroh (PyPI) 1.1.0", "connect_ms_median": round(statistics.median(connects), 2)}
    for label, size, n in (("1KiB", 1024, 500), ("1MiB", 1 << 20, 20)):
        payload = b"\0" * size
        t = time.perf_counter()
        for _ in range(n):
            assert await roundtrip(conn, payload) == size
        dt = time.perf_counter() - t
        out[f"{label}_per_s"] = round(n / dt, 1)
        out[f"{label}_MBps"] = round(n * size / dt / 1e6, 2)
    print(json.dumps(out))
    task.cancel()


asyncio.run(main())
