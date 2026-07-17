# MCP Surface Reverse-Engineering — deepseek code+spec half — 2026-07-16

Status: BLIND DRAFT (filed without reading claude's mcp-surface-claude-2026-07-16.md).
READ-ONLY REVERSE-ENGINEERING via pytest-based SDK inspection. File:line receipts for every claim.

---

## 1. TOOL INVENTORY — ai_setup_mcp.py

File: `E:\AI-Setup\ai_setup_mcp.py`. All tools registered via `@mcp.tool()` on a
`FastMCP("akashic-aurora")` instance. Every tool is a SYNC `def` (not `async def`),
so their `Tool.is_async` field is `False` (verified in `server/fastmcp/tools/base.py`
line `_is_async_callable` — `inspect.iscoroutinefunction` returns `False` for plain
defs). This is critical for the dispatch analysis in §3.

### Tools riding `_run()` (IN-PROCESS, stdout capture via `redirect_stdout`)

These call `agent_cli.cmd_*` functions directly. The `_run` helper (ai_setup_mcp.py:79-90)
creates a synthetic `argparse.Namespace`, wraps the call in `contextlib.redirect_stdout(buf)`
with an `io.StringIO` buffer, catches `SystemExit` and `Exception`, and returns the
captured string.

| # | Tool | Python Signature | `_run` call | Est. Output Size |
|---|------|-----------------|-------------|------------------|
| 1 | `boot` | `(agent: str, task: str = "") -> str` | `_run(agent_cli.cmd_boot, agent_id=agent, task=task or None)` | **8-14 KB** — largest; orientation header + lessons + notes + decisions + doctor + funnel + trim |
| 2 | `learn` | `(agent: str, experiment: str, tried: str = "", result: str = "", recommend: str = "", expected: str = "", category: str = "", success: str = "yes", confidence: str = "medium") -> str` | `_run(agent_cli.cmd_learn, ...)` | ~200 B |
| 3 | `recall` | `(query: str = "", full: str = "") -> str` | `_run(agent_cli.cmd_recall, ...)` | 0.5-5 KB |
| 4 | `recall_at` | `(path: str = "", command: str = "", agent: str = "", limit: int = 3) -> str` | `_run(agent_cli.cmd_recall_at, ...)` | 0-2 KB |
| 5 | `task` | `(args: str) -> str` | `_run(agent_cli.cmd_task, rest=shlex.split(args))` | 0.5-5 KB |
| 6 | `recall_feedback` | `(source: str, useful: bool = True, noise: bool = False) -> str` | `_run(agent_cli.cmd_recall_feedback, ...)` | ~100 B |
| 7 | `note` | `(agent: str, title: str, note: str, context: str = "", category: str = "", supersedes: str = "") -> str` | `_run(agent_cli.cmd_note, ...)` | ~200 B |
| 8 | `notes` | `(days: int = 0, limit: int = 25) -> str` | `_run(agent_cli.cmd_notes, ...)` | 0.5-8 KB |
| 9 | `knowledge_map` | `(topic: str = "", per_layer: int = 6) -> str` | `_run(agent_cli.cmd_knowledge_map, ...)` | 1-6 KB |
| 10 | `lock` | `(agent: str, path: str, ttl: int = 900) -> str` | `_run(agent_cli.cmd_lock, ...)` | ~100 B |
| 11 | `unlock` | `(agent: str, path: str) -> str` | `_run(agent_cli.cmd_unlock, ...)` | ~100 B |
| 12 | `locks` | `(agent: str = "") -> str` | `_run(agent_cli.cmd_locks, ...)` | 0-1 KB |
| 13 | `tag_anti_pattern` | `(experiment: str, name: str, reason: str = "") -> str` | `_run(agent_cli.cmd_tag_anti_pattern, ...)` | ~100 B |
| 14 | `status` | `() -> str` | `_run(agent_cli.cmd_status)` | ~300 B |
| 15 | `stats` | `(hours: float = 24, days: int = 0) -> str` | `_run(agent_cli.cmd_stats, ...)` | 1-4 KB |
| 16 | `injections` | `(hours: float = 24) -> str` | `_run(agent_cli.cmd_injections, ...)` | 1-5 KB |
| 17 | `graduate` | `(agent: str, experiment: str, enforced_by: str = "", undo: bool = False) -> str` | `_run(agent_cli.cmd_graduate, ...)` | ~100 B |
| 18 | `log` | `(agent: str, kind: str = "note", summary: str = "", source: str = "", category: str = "", task: str = "") -> str` | `_run(agent_cli.cmd_log, ...)` | ~100 B |
| 19 | `handoff` | `(from_agent: str, to: str = "", task: str = "", note: str = "", blocker: str = "", list_only: bool = False) -> str` | `_run(agent_cli.cmd_handoff, ...)` | 0.5-3 KB |
| 20 | `story` | `(track: str = "", chronicle: bool = False) -> str` | `_run(agent_cli.cmd_story, ...)` | 1-8 KB |
| 21 | `events` | `(search: str = "", agent: str = "", kind: str = "", limit: int = 20) -> str` | `_run(agent_cli.cmd_events, ...)` | 1-8 KB |
| 22 | `promoted` | `(limit: int = 20, since: str = "", until: str = "") -> str` | `_run(agent_cli.cmd_promoted, ...)` | 1-5 KB |
| 23 | `bifrost_sync` | `(agent: str, limit: int = 10, consume: bool = False) -> str` | `_run(agent_cli.cmd_bifrost_sync, ...)` | 0.5-5 KB |

### Tools riding custom code (IN-PROCESS, direct Bus/import calls)

These tools import `core.comm.*` and call Bus methods directly. No stdout capture —
they construct their own `str` return values.

| # | Tool | Python Signature | Dispatch Path | Est. Output Size |
|---|------|-----------------|---------------|------------------|
| 24 | `bifrost_send` | `(from_agent: str, to: str, kind: str = "chat", text: str = "", expect_reply_within: int = 0) -> str` | `Bus(from_agent).send(...)` → str | ~100 B |
| 25 | `bifrost_nudge` | `(from_agent: str, to: str, text: str = "", mode: str = "interrupt") -> str` | `_nudge.nudge/steer_push` + `Bus.send(...)` → str | ~100 B |
| 26 | `bifrost_broadcast` | `(from_agent: str, kind: str = "announce", text: str = "") -> str` | `Bus(from_agent).broadcast(...)` → str | ~100 B |
| 27 | `bifrost_inbox` | `(agent: str, limit: int = 20, consume: bool = False) -> str` | `consume_inbox(...)` or `Bus(agent).inbox(...)` → str | 0-5 KB |
| 28 | `bifrost_presence` | `(agent: str = "") -> str` | `Bus(agent).register()/.presence()` → str | ~200 B |

### Tools riding `_run_script()` (SUBPROCESS, `subprocess.run` with capture+timeout)

These spawn a separate Python process. The parent blocks on `subprocess.run` with
a timeout; stdout/stderr are captured and returned as a single string.

| # | Tool | Python Signature | Subprocess Command | Est. Output Size | Timeout |
|---|------|-----------------|--------------------|------------------|---------|
| 29 | `ask_gemini_web` | `(prompt: str, mode: str = "gemini", system: str = "") -> str` | `py scripts/gemini_web.py --mode ...` | 1-20 KB | 180-300s |
| 30 | `gemini_web_login` | `() -> str` | `subprocess.Popen(...)` (fire-and-forget) | ~200 B | N/A |
| 31 | `ask_gemini_panel` | `(prompt: str, system: str = "", web_mode: str = "both") -> str` | Runs `ask_gemini_web` in-process + `_run_script("ask_gemini.py", ...)` | 2-30 KB | 300s+ |

### Summary

- **23 tools** ride `_run()` — in-process, sync, stdout-captured, 0.1-14 KB output.
- **5 tools** ride custom in-process logic — Bus/consume_inbox, 0.1-5 KB output.
- **3 tools** ride subprocess — `_run_script`, 1-30 KB output, 180-300s timeouts.
- **0 tools** are `async def`. All are sync. This means every tool call blocks the
  anyio worker thread for its entire execution duration.

---

## 2. PROTOCOL CONTRACT — installed MCP SDK

### Package source and versions

Installed at: `C:\Users\L5\AppData\Local\Programs\Python\Python311\Lib\site-packages\mcp\`

| Package | Version |
|---------|---------|
| `mcp` (the SDK) | No `__version__` attr; identified by file inventory as the `modelcontextprotocol/python-sdk` |
| `pydantic` | 2.12.5 |
| `starlette` | 1.0.0 |
| `uvicorn` | 0.44.0 |
| `anyio` | installed (version check failed — `?`) |

Key files (verified by `os.walk` of the `mcp/` package, sizes from `os.path.getsize`):

| File | Size | Role |
|------|------|------|
| `server/stdio.py` | 3356 B (88 lines) | Transport: stdin→JSON-RPC messages→memory stream, memory stream→JSON-RPC→stdout |
| `server/lowlevel/server.py` | 34872 B (824 lines) | Core server: request dispatch, handler registration, run loop |
| `server/session.py` | 27555 B (691 lines) | ServerSession: send_message, handle_tool_call |
| `server/fastmcp/server.py` | 52706 B | FastMCP: tool() decorator, add_tool, call_tool, run() |
| `server/fastmcp/tools/base.py` | ~8 KB | Tool class: from_function, run(), `call_fn_with_arg_validation` |
| `server/fastmcp/tools/tool_manager.py` | 3042 B (93 lines) | ToolManager: add_tool, call_tool |
| `server/fastmcp/utilities/func_metadata.py` | ~15 KB | FuncMetadata: arg_model, `call_fn_with_arg_validation`, `_convert_to_content` |
| `shared/session.py` | 24224 B (552 lines) | BaseSession: `_send_response`, `send_request`, `respond` |
| `types.py` | 64908 B (1999 lines) | All JSON-RPC/MCP types: CallToolRequest, CallToolResult, TextContent, ServerResult, JSONRPCResponse |

### JSON-RPC 2.0 framing

**Transport: stdio, newline-delimited JSON.** `server/stdio.py` lines 33-88:

- **Stdin wrap** (line 50): `anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace"))`. UTF-8 with replacement characters for decode errors.
- **Stdout wrap** (line 51): `anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8"))`. UTF-8, no replacement — encode errors would raise.
- **Read path** (`stdin_reader`, line 60): `async for line in stdin:` reads each newline-delimited line. Each line parsed via `types.JSONRPCMessage.model_validate_json(line)`. Parse errors send the `Exception` object into the read stream as an error message (line 64: `await read_stream_writer.send(exc)`).
- **Write path** (`stdout_writer`, line 71): Reads `SessionMessage` from `write_stream_reader`. Each is serialized via `session_message.message.model_dump_json(by_alias=True, exclude_none=True)`. Writes `json + "\n"` then `await stdout.flush()`.
- **Memory streams** (lines 55-57): Both sides use `anyio.create_memory_object_stream(0)`. The `0` = max_buffer_size=0 means **unbuffered** — the send side blocks (`await write_stream.send(...)`) until the receive side reads. This is the critical backpressure point: if the stdout_writer task is slow to flush, backpressure propagates through the memory stream all the way to the `_send_response` call in `shared/session.py`.

### Initialize/initialized lifecycle

`server/lowlevel/server.py` line 640 (`async def run`):

1. Server enters lifespan context (`self.lifespan(self)`).
2. Creates `ServerSession(read_stream, write_stream, initialization_options)` — inside its `__aenter__`, it handles the `initialize` request from the client and sends an `initialized` notification. This is automatic — `ai_setup_mcp.py` never manually handles it.
3. After initialization: enters a task group loop:
   ```python
   async with anyio.create_task_group() as tg:
       async for message in session.incoming_messages:
           tg.start_soon(self._handle_message, message, ...)
   ```
   Each message is handled in a **separate anyio task** — concurrent handling.
4. On transport close: `tg.cancel_scope.cancel()` cancels all in-flight handlers (line 686).

### tools/list

Handled by `FastMCP.list_tools()` (`server/fastmcp/server.py` line 338): calls
`self._tool_manager.list_tools()` → returns all registered `Tool` objects converted to
`MCPTool(name, description, inputSchema, ...)`. Registered at decoration time via
`self._mcp_server.list_tools()(self.list_tools)` in `_setup_handlers` (line 303).

### tools/call — REQUEST shape

Client sends (per JSON-RPC 2.0 over newline-delimited stdio):
```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"boot","arguments":{"agent":"claude","task":""}}}
```

Parsed by Pydantic into `types.CallToolRequest` → `req.params.name` (str), `req.params.arguments` (dict).

### tools/call — RESPONSE shape

Success (after dispatch chain in §3):
```json
{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text","text":"<captured stdout>"}],"isError":false}}
```

`JSONRPCResponse.result` is typed `dict[str, Any]` in `types.py` line ~1986. The `CallToolResult`
is serialized via `model_dump(by_alias=True, mode="json", exclude_none=True)`, producing
`content` (list of ContentBlock) and `isError` (bool) in the result dict.

Error:
```json
{"jsonrpc":"2.0","id":1,"error":{"code":0,"message":"Error executing tool boot: ...","data":null}}
```

### Cancellation

`shared/session.py` `async def cancel()`: sends `ErrorData(code=0, message="Request cancelled")`.
`in_flight` property checks `not self._completed and not self.cancelled`.
Transport-close cancellation in `server/lowlevel/server.py` line ~755: catches
`anyio.get_cancelled_exc_class()` — if already cancelled by client, suppresses duplicate response.

### Timeouts

`shared/session.py` `send_request()` supports `request_read_timeout_seconds` and session-level
`_session_read_timeout_seconds`, using `anyio.fail_after(timeout)`. But for **server-side tool
execution**, `_handle_request` at line 721 calls `await handler(req)` with NO `fail_after` wrapper.
The tool runs until it returns or the transport closes.

### Notifications

The SDK supports `notifications/cancelled`, `notifications/progress`, `notifications/initialized`.
Our server does not use progress notifications.

---

## 3. DISPATCH PATH — tools/call end-to-end

The complete call chain for `tools/call {"name":"boot","arguments":{...}}`:

### Step 1: Transport read → JSON parse
`server/stdio.py` line 60, `stdin_reader`: reads a line from stdin.
`types.JSONRPCMessage.model_validate_json(line)` parses it. Wraps in `SessionMessage`.
Sends into `read_stream` (a `MemoryObjectSendStream`).

### Step 2: Session receive → message loop
`server/lowlevel/server.py` line 673, `run()`: `async for message in session.incoming_messages`
yields each message. `tg.start_soon(self._handle_message, message, ...)` spawns an anyio task.

### Step 3: _handle_message → _handle_request
`server/lowlevel/server.py` line 694, `_handle_message`: matches the message type.
For `RequestResponder(request=types.ClientRequest(root=req))`: calls `_handle_request`.

### Step 4: _handle_request → handler dispatch
`server/lowlevel/server.py` line 721, `_handle_request`: looks up the handler for
`types.CallToolRequest` in `self.request_handlers`. This was registered by
`FastMCP._setup_handlers()` line 308: `self._mcp_server.call_tool(validate_input=False)(self.call_tool)`.

The handler is the `async def handler(req: types.CallToolRequest)` inside the `call_tool`
decorator at line 523. It:
1. Extracts `tool_name = req.params.name` and `arguments = req.params.arguments or {}`
2. Calls `results = await func(tool_name, arguments)` — where `func` is `FastMCP.call_tool`

### Step 5: FastMCP.call_tool → ToolManager.call_tool
`server/fastmcp/server.py` line 343, `async def call_tool(self, name, arguments)`:
`return await self._tool_manager.call_tool(name, arguments, context=context, convert_result=True)`

### Step 6: ToolManager.call_tool → Tool.run
`server/fastmcp/tools/tool_manager.py` line 81, `async def call_tool(...)`:
`return await tool.run(arguments, context=context, convert_result=convert_result)`

### Step 7: Tool.run → FuncMetadata.call_fn_with_arg_validation
`server/fastmcp/tools/base.py` line ~95, `async def run(...)`:
```python
result = await self.fn_metadata.call_fn_with_arg_validation(
    self.fn, self.is_async, arguments,
    {self.context_kwarg: context} if self.context_kwarg else None,
)
if convert_result:
    result = self.fn_metadata.convert_result(result)
return result
```

### Step 8: call_fn_with_arg_validation — THE CRITICAL LINE
`server/fastmcp/utilities/func_metadata.py` line ~70:
```python
if fn_is_async:
    return await fn(**arguments_parsed_dict)
else:
    return fn(**arguments_parsed_dict)   # <-- SYNC CALL, BLOCKS THE ANYIO WORKER
```

For ALL our tools, `fn_is_async` is `False` (all are plain `def`, not `async def`).
The function is called **synchronously, inline, on the anyio worker thread**. The
`await` on line 93 of `base.py` (`result = await self.fn_metadata.call_fn_with_arg_validation(...)`)
resolves immediately because `call_fn_with_arg_validation` returns a plain value
(not a coroutine) for sync functions.

**This means the anyio event loop is BLOCKED for the entire duration of our tool
function.** The `stdout_writer` task, `stdin_reader` task, and any other concurrent
tool calls share the SAME event loop — but since `boot()` is sync and long-running,
it occupies the worker thread. However... anyio's default `run()` uses a thread pool
or the event loop thread depending on the backend. Let's check:

### Step 8b: anyio backend — where does the sync call actually run?

`mcp server run` calls `anyio.run(self.run_stdio_async)` (fastmcp/server.py line 293).
`anyio.run()` creates an event loop and runs the async function to completion. The
`asyncio` backend (likely on Windows) runs everything on a single event loop thread.

When `call_fn_with_arg_validation` calls `fn(**args)` — a sync function — it blocks
the event loop thread. **This is the C7-4 root cause.** While `cmd_boot` is running
(and its `heal_report()` iterates Redis keys), the event loop thread is occupied.
No other task can run. The `stdout_writer` cannot flush. The `stdin_reader` cannot
read the next line. The entire server is frozen.

### Step 9: Result conversion
`func_metadata.py` `_convert_to_content(result)`: for a `str` result, wraps it in
`[TextContent(type="text", text=result)]`. Our `_run()` returns `buf.getvalue().strip()`,
a plain string → one `TextContent`.

### Step 10: Response normalization (lowlevel handler)
Back in `server/lowlevel/server.py` line 530, the handler receives the result from
`func(tool_name, arguments)`. For our case: the result is a `Sequence[ContentBlock]`
(one TextContent). The handler wraps it:
```python
if hasattr(results, "__iter__"):
    unstructured_content = cast(UnstructuredContent, results)
```
Then builds: `types.ServerResult(types.CallToolResult(content=list(unstructured_content), isError=False))`

### Step 11: Response send
`_handle_request` line 772: `await message.respond(response)`.
`shared/session.py` `respond()` → `await self._session._send_response(request_id=..., response=response)`.
`shared/session.py` `_send_response()` line ~240:
```python
jsonrpc_response = JSONRPCResponse(jsonrpc="2.0", id=request_id,
    result=response.model_dump(by_alias=True, mode="json", exclude_none=True))
session_message = SessionMessage(message=JSONRPCMessage(jsonrpc_response))
await self._write_stream.send(session_message)
```

### Step 12: Transport write
The `_write_stream` is the `MemoryObjectSendStream` created in `stdio.py`. The
`stdout_writer` task reads from the paired `MemoryObjectReceiveStream` and writes
to `stdout`: `await stdout.write(json + "\n")` → `await stdout.flush()`.

### Where can the response fail to be written AFTER the tool function returns?

**Point A — `_convert_to_content` encoding failure.** If our `_run()` returns a
string with characters that `pydantic_core.to_json` can't handle (unlikely for
plain text, but possible with binary garbage in stdout). This would raise inside
`tool.run()` → `ToolError` → error response.

**Point B — `model_dump` serialization failure.** `JSONRPCResponse` contains
`result: dict[str, Any]`. The `CallToolResult.model_dump()` serializes
`content: list[ContentBlock]` and `isError: bool`. If our text contains characters
that break JSON encoding (lone surrogates, invalid UTF-8 from Redis data), the
`model_dump_json` may raise. The error would propagate through `_send_response` →
`anyio.BrokenResourceError` handler in `_handle_request` line 773.

**Point C — Memory stream backpressure.** `await self._write_stream.send(session_message)`
on an unbuffered stream blocks until `stdout_writer` reads. If `stdout_writer` is
blocked on `stdout.write()` (OS pipe buffer full), the entire chain blocks. The
client probe drains both pipes — ruling this out for the probe scenario. But with
a slow or hung client, this IS the hang point.

**Point D — stdout.flush() blocks.** `anyio.AsyncFile.flush()` on Windows can block
if the OS pipe buffer is full and the client isn't reading. Ruled out by the probe
draining both pipes.

**Point E — Event loop still blocked from Step 8.** If `cmd_boot` finishes its sync
work but the event loop hasn't yielded yet (e.g., the `heal_report` Redis keys()
scan returned but another sync operation is pending), the `_send_response` →
`_write_stream.send` → `stdout_writer` chain never gets CPU time. BUT the probe
evidence shows the work COMPLETES (agent-init logs, heal lines on stderr at +11.4s)
— those stderr prints happen INSIDE `cmd_boot`. So `cmd_boot` DID finish. The
question is: did it return?

**If `cmd_boot` returns normally**, the chain in Steps 9-12 executes. The `str`
result is wrapped in `TextContent`, serialized to JSON, and sent to stdout. This
should take <10ms. The probe would see the response.

**If `cmd_boot` does NOT return** — it's still blocking the event loop thread —
the stderr output happened but the function is stuck after the last `print(file=sys.stderr)`.
This is the most likely scenario: `cmd_boot` finished its render, printed to stderr,
but then hit a blocking operation in its tail work (cold-start reconciler with
`store.keys()`, or a hidden synchronous Redis operation).

### THE DISPATCH-PATH DIAGNOSIS

The probe evidence constrains the hang to a specific window:
- Work completes (stderr shows agent-init + heal lines at +11.4s)
- Response never arrives (90s window)
- Both pipes drained → not a client-side read problem
- 9 other tools return instantly → not a general event-loop problem

The hang must be in `cmd_boot` AFTER the last stderr print but BEFORE the `return`
of `_run()`. The last stderr prints are the `heal_report` lines. After those,
`cmd_boot` continues with:
1. Doctor section (calls `core.comm.doctor` which may query Redis)
2. Bifrost section (calls `collect_boot_bifrost` which pings Redis)
3. Trim block (`_trim_onboarding`)
4. Footer ("TO CONTRIBUTE A LESSON")

Any of these could block. The `collect_boot_bifrost` → `Bus.probe()` → Redis PING
is the most likely candidate if Redis is in a degraded state (the post-crash
scenario: daemon dead, fleet dark, Redis possibly overloaded).

---

## 4. DATA-TYPE + SIZE BOUNDARIES

### Accept shapes

- **tools/call params**: `{"name": str, "arguments": dict[str, Any]}`. No explicit
  size limit in the SDK beyond what Pydantic can parse. A 1MB arguments dict would
  probably parse but take CPU.
- **String args**: Pydantic `str` fields have no max_length by default. Our
  `agent: str` or `task: str = ""` accept arbitrarily large strings.

### Return shapes

- **Our tools return `-> str`**. FastMCP with `convert_result=True` wraps this in
  `_convert_to_content`: a plain `str` → `[TextContent(type="text", text=result)]`.
- `TextContent.text` is `str` — no size limit in the Pydantic model.

### Size boundaries in the pipeline

1. **`_run` buffer**: `io.StringIO()` — in-memory, no size limit. For `boot()`, the
   buffer holds 8-14 KB.
2. **`TextContent`**: The `text` field is `str` — Pydantic serializes it as one
   JSON string. For 14 KB, this produces a ~14 KB JSON string (plus escaping).
3. **`model_dump_json`**: Serializes the entire `JSONRPCResponse` to a single JSON
   string. The total response size for `boot()` is ~15-20 KB (JSON framing overhead
   + content + result wrapper).
4. **`stdout.write(json + "\n")`**: Writes the full JSON line to stdout. The OS pipe
   buffer on Windows is typically 4-64 KB. A 20 KB response fits in one buffer.
5. **No chunking**: The MCP SDK does not support streaming responses for `tools/call`.
   The entire result must fit in one JSON-RPC response.

### Non-UTF-8 / control chars

- **stdin**: UTF-8 with `errors="replace"` — decode errors produce replacement chars.
- **stdout**: UTF-8 without `errors="replace"` — encode errors would raise
  `UnicodeEncodeError`. Our `_run()` captures stdout from `cmd_*` functions which
  use `print()`, producing clean UTF-8. Redis keys may contain binary data that
  slips into output; this would be caught at `model_dump_json` serialization time.
- **JSON escaping**: `model_dump_json` escapes control characters per JSON spec.

### What turns a str into content blocks

`_convert_to_content` (`func_metadata.py` line 499):
- `None` → `[]` (empty content list)
- `ContentBlock` → `[result]` (already a content block)
- `Image` → `[result.to_image_content()]`
- `Audio` → `[result.to_audio_content()]`
- `list | tuple` → flattened list of recursively converted items
- `str` → `[TextContent(type="text", text=result)]`
- Anything else → `pydantic_core.to_json(result, fallback=str, indent=2).decode()` → `[TextContent(text=...)]`

Our tools return `str` exclusively → always one TextContent.

---

## 5. ENV/CWD ASSUMPTIONS

### What ai_setup_mcp.py assumes

1. **CWD**: `ai_setup_mcp.py` does `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`
   at line 44 — adds the repo root to sys.path using its own file location. This is
   robust regardless of CWD. However, `_run_script()` uses `cwd=str(ROOT)` where
   `ROOT = Path(__file__).resolve().parent` — copies ai_setup_mcp.py's directory as
   the subprocess CWD. **This works correctly even if the spawning process has a
   different CWD.**

2. **`AKASHIC_SEAT_DOOR`**: Set to `"mcp"` at line 48 (`os.environ.setdefault`).
   This is what `_transport_line()` reads to render "door: MCP-native" in boot output.
   An outer launcher can override it.

3. **Redis reachability**: The server assumes Redis is at the project default
   (`localhost:16379` via `config.py`). If unreachable, `Bus.online` returns False
   and tools degrade: `bus.probe()` returns False, `Bus("agent").send()` returns None
   with "BUS OFFLINE" message, `bifrost_presence` returns "(no agents online)".
   Boot's `collect_boot_bifrost` → `register_presence` → `Bus.register()` quietly
   fails. Boot's `HybridStore` → `store.heal_report()` on a `HybridStore` where
   `redis_available` is False skips the heal. **The server does not crash on Redis
   absence — but it may block on Redis connection attempts.**

4. **Python path**: `_run_script` uses `sys.executable` (the same Python that runs
   the MCP server). This is correct — if the MCP server runs under Python 3.11,
   subprocesses also use 3.11.

### What Claude Code actually passes

Per `mcp_global/cursor.mcp.json` (the Cursor MCP config):
```json
{
  "command": "py",
  "args": ["-3", "E:\\AI-Setup\\ai_setup_mcp.py"],
  "cwd": "E:\\AI-Setup",
  "env": {
    "PYTHONIOENCODING": "utf-8",
    "AKASHIC_AGENT_ID": "composer"
  }
}
```

- **CWD**: `E:\AI-Setup` (repo root). Matches the assumption.
- **`PYTHONIOENCODING`: utf-8**. Redundant with the server's own wrap, but harmless.
- **`AKASHIC_AGENT_ID`**: Set to the agent's id. `cmd_boot` uses this if not
  overridden by the tool argument.
- **No `AKASHIC_SEAT_DOOR` override**: The server's default `"mcp"` is used.

Claude Code's MCP config (user-level or project-level) must similarly set `cwd` to
the repo root or an absolute path for the server script. The docs/DEPLOY.md
instructions assume this.

### Redis assumptions under Claude Code

Claude Code spawns the MCP server as a long-lived child process. The server holds
a persistent Redis connection (via `Bus` instantiation). If Redis restarts, the
connection is broken and `Bus.probe()` returns False. The server does NOT
auto-reconnect (no retry loop in Bus). A Redis restart mid-session would cause
all bus operations to return "BUS OFFLINE" until the server is restarted.

