# MCP Push Bridge — Design (kimi + deepseek, 2026-07-18)

Status: design filed; Daniel's gate for build approval
Context: Daniel wants the UI↔MCP tied so a seat needn't mechanically shell `bifrost-sync` to
read bus mail. kimi's key finding: the read verbs ALREADY exist on the MCP door; the gap is
PUSH (MCP is stdio pull-only).

## Current state

- **MCP read verbs:** `bifrost_inbox`, `bifrost_sync`, `bifrost_presence` already wired in
  `ai_setup_mcp.py` (lines ~400-488), wrapping `agent_cli` cmd_* functions — one source of
  truth, CLI+MCP never drift.
- **UI push:** Server-Sent Events over a blocking Redis tail (`scripts/bifrost_ui.py:39`
  `_client()` + `:247` `text/event-stream` + `:1539` `EventSource('/events')`). Zero-dependency
  stdlib, already running.
- **MCP transport:** `ai_setup_mcp.py` runs as stdio (default, spawned by MCP client) or
  `--http` (optional shared process, port 18765). FastMCP pinned version.

## The gap

MCP is PULL-ONLY over stdio: the client sends a request, the server responds. An agent must
CALL `bifrost_inbox()` / `bifrost_sync()` each turn to see new mail. The UI's SSE tail is the
push channel MCP lacks — but it only pushes to the browser, not to MCP clients.

## Push primitive: what FastMCP supports

**`session.send_notification(notification)`** — the `BaseSession` (shared/session.py) exposes
`send_notification(notification: SendNotificationT)`. For `ServerSession`, `SendNotificationT`
is bound to `types.ClientNotification`, which wraps any notification root type.

The spec-defined `notifications/message` notification:
```json
{
  "method": "notifications/message",
  "params": {
    "level": "info",
    "data": {"from": "claude", "kind": "handoff", "content": "..."}
  }
}
```

This is the spec-correct mechanism for server→client push. However, client support is
UNEQUAL: Claude Desktop documents support; Cursor may not. When unsupported, notifications
are silently ignored — push degrades gracefully to poll.

**Other mechanisms considered and ruled out:**
- `send_log_message(level, data, logger)` — meant for server logging, not general mail
- `send_progress_notification(...)` — per-request progress, not general-purpose
- Elicitation (`URL_ELICITATION_REQUIRED`) — a request-response "visit this URL" pattern,
  not push mail delivery
- `ToolListChangedNotification` — spec-defined but semantically wrong for new mail

**Verdict:** `notifications/message` via `session.send_notification` is the right mechanism.
It's spec-defined, present in our pinned FastMCP, and degrades gracefully.

## Architecture: bridge inside ai_setup_mcp.py

The bridge lives INSIDE `ai_setup_mcp.py` (zero new config — the agent already connects to
this server). Design:

```
ai_setup_mcp.py (existing)
  └─ lifespan: start a background task (anyio)
       └─ tail Redis bifrost:inbox:<agent> + bifrost:broadcast
            └─ on new mail: session.send_notification(
                 ClientNotification(root=MessageNotification(
                   level="info",
                   data={"from": frm, "kind": kind, "content": content[:300]}
                 ))
               )
```

For **stdio mode:** the notification arrives at the MCP client over the existing stdio
transport. If the client supports `notifications/message`, it renders the mail to the user.
If not, it's silently ignored — but the agent can still call `bifrost_inbox()` as a tool.
Push degrades gracefully to poll.

For **HTTP mode:** same mechanism, but the background task runs inside the FastMCP lifespan's
`anyio` task group.

**Why inside, not a sidecar:**
- Zero new config. The agent's MCP config already points at `ai_setup_mcp.py`.
- The `bifrost_inbox` tool already has access to the bus — the notification path reuses the
  same `Bus(agent)` connection.
- A sidecar would need its own agent identity, Redis connection, and process supervision —
  replicating infrastructure the MCP server already has.
- Design principle from the MCP header: "adding tools to the server an agent ALREADY connects
  to beats a new server."

**Threading concern:** The SSE tail blocks for 15 seconds (`tail(client, last_ids, block_ms=15000)`).
Running a blocking Redis `xread` inside the FastMCP `anyio` event loop requires wrapping it:
`await anyio.to_thread.run_sync(lambda: tail(...))`. FastMCP already uses `anyio` — this is a
thread pool dependency, not a new import.

## Safety properties

- **Mis-delivery never hides mail.** A notification that isn't rendered by the client is a
  cosmetic loss; the mail is still in Redis, still consumable via `bifrost_inbox()` tool call.
- **Fail-toward-showing.** If the notification bridge crashes, the MCP server's tools still
  work. The bridge is a background task; its failure doesn't affect tool calls.
- **No new lane, no new cursor.** The bridge tails the same Redis streams the runner consumes.
  It's a read-only observer, not a consumer.

## Sequencing

1. **Ship the floor first:** The `bifrost_sync` tool call at turn-start is already documented
   ("Call at turn-start in-session"). This is the answer for ALL MCP clients today.
2. **Add the notification bridge as an optimization** when we confirm a specific client
   (Claude Desktop) supports `notifications/message`.
3. **Never:** a parallel websocket stack, or a per-seat poller.

## Hammers explicitly avoided

- ❌ Giving every seat its own Redis poller (N Redis connections, N configs)
- ❌ A parallel WebSocket stack alongside SSE (two push substrates to maintain)
- ❌ Adding `bifrost_sync` to every tool call implicitly (adds latency to every turn)
- ❌ A sidecar process per seat (process supervision, identity management, config sprawl)

## Gate items for Daniel

| # | Decision | Recommendation |
|---|----------|---------------|
| P1 | Push primitive | `notifications/message` via `session.send_notification` — spec-defined, degrades gracefully |
| P2 | Bridge location | Inside `ai_setup_mcp.py` lifespan — zero new config |
| P3 | Sequencing | Ship `bifrost_sync` turn-start pattern as the floor; add notification bridge when client support is confirmed |
