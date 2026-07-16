# UI-MCP Integration — DeepSeek Blind Half (2026-07-15)

Fence: Daniel wants the UI tied into MCP so agents don't mechanically shell-read messages.

## Problem Diagnosis

There are currently **three separate doors** into the system, and agents navigate
them independently:

| Door | Transport | What it gives | Agent uses it for |
|------|-----------|---------------|-------------------|
| `agent_cli.py` | Shell | boot, learn, recall, bifrost-sync, status | Claude: reading mail (bifrost-sync via Bash) |
| `ai_setup_mcp.py` | MCP (stdio) | Same verbs as CLI, thin wrappers | Claude: knowledge ops (boot, learn, recall) |
| `bifrost_ui.py` | HTTP :8787 | /status, /vitals, /send, /events | Daniel: visual dashboard; sending messages |

The mechanical read: Claude's wake→read pipeline is **shell-based**. `bifrost_wake.py`
exits → Claude Code runs `agent_cli.py bifrost-sync` via Bash → parses JSON. The MCP
`bifrost_sync()` tool EXISTS but the wake pipeline doesn't use it — because the wake
listener is a shell process that signals completion, not an MCP event.

**Root cause**: mail reading and UI state querying are not MCP-native. The agent has
to know about multiple doors and manually bridge between them.

## Design: "One MCP Surface" — the UI becomes MCP-discoverable

### Core insight
The MCP server (`ai_setup_mcp.py`) already wraps `agent_cli.py` verbs. It already
has `bifrost_inbox`/`bifrost_sync`/`bifrost_send` as tools. The missing step is
making the UI's **readable surface** (status, vitals, presence) and the **message
delivery path** MCP-native, so the agent never leaves the MCP door.

### Mechanism

**Three additions to `ai_setup_mcp.py`, zero new servers:**

| Addition | Type | What it exposes | Replaces |
|----------|------|-----------------|----------|
| `ui://status` | Resource | Bus state, paused, agent presence, online/offline | Shell `agent_cli.py status` |
| `ui://vitals` | Resource | Engine-room gauge_snapshot + lane_depths + fence_phase | Shell curl to :8787 |
| `operator_send(text, target)` | Tool | Send operator-class message with smart routing (T080) | The UI's /send being invisible to MCP agents |
| `boot()` enhanced | Tool | **Includes unread message count + first 3 message previews** | Separate `bifrost_sync` call after boot |

### Why this eliminates the mechanical read

1. **`boot()` surfaces mail natively.** When an agent boots, its startup context
   already says "You have 2 unread messages: [preview]...". No separate `bifrost_sync`
   call needed. The agent reads its mail as part of its natural startup.

2. **`ui://vitals` replaces shell polling.** Instead of `curl localhost:8787/vitals`,
   the agent reads `ui://vitals` as an MCP resource. Same data, MCP-native.

3. **`operator_send` closes the loop.** An agent that wants to respond to the operator
   uses the MCP tool directly — no shell, no Redis key construction.

4. **For Claude specifically**: the wake listener stays as-is (it's the right mechanism
   for signaling "mail arrived"), but instead of the harness running a Bash
   `bifrost-sync`, it invokes the MCP `boot()` call which now includes the unread
   messages. One call, not two.

### Architecture — how it connects

```
┌──────────┐   MCP (stdio)    ┌──────────────────┐   HTTP    ┌──────────┐
│  Agent   │ ◄──────────────► │ ai_setup_mcp.py  │ ◄───────► │ bifrost  │
│ (Claude) │   tools+resources│  + new resources  │  :8787    │  _ui.py  │
└──────────┘                  │  + boot enhanced  │           └──────────┘
                              └────────┬─────────┘
                                       │ Redis
                              ┌────────┴─────────┐
                              │   Bifrost Bus     │
                              └──────────────────┘
```

The MCP server becomes the **single front door** to everything: knowledge (boot/learn/recall),
mail (inbox/send/sync), and UI state (status/vitals). The UI is still served on :8787
for Daniel's browser, but its data surface is MCP-readable.

### The `boot()` enhancement — detailed

Current `boot()` output is: orientation header + where-we-are + lessons + proposed tasks + ...
It already "peeks unread Bifrost inbox" (AGENTS.md:93) but doesn't SHOW the messages.

Enhanced `boot()` gains a MAIL section (after the header, before lessons):

```
## UNREAD MAIL (2 messages)
[chat] from user (2m ago): "can you fix the lane depths bug?"
[handoff] from deepseek (15m ago): "FENCE: smart message routing — ..."
```

This is ALREADY being fetched (the code peeks the inbox). It's just not rendered.
Rendering it in `boot()` means the agent never needs a separate `bifrost_sync`.

Only the first 3 messages are shown (with character caps) — the full read is still
`bifrost_inbox` for deep inspection. But the common case (1 new message from Daniel)
is handled in the boot call itself. Zero extra tool calls.

### MCP Resources — implementation

The resources are thin proxies:

```python
@mcp.resource("ui://status")
def ui_status() -> str:
    """Live Bifrost UI status: paused state, agent presence, bus health."""
    return _run(agent_cli.cmd_status, json=True)  # already exists, just expose as resource

@mcp.resource("ui://vitals")  
def ui_vitals() -> str:
    """Engine-room vitals: heartbeat, runtimes, tokens, lanes, fence phases."""
    from core.comm.engine_vitals import gauge_snapshot
    from core.comm.lane_depths import lane_depths
    from core.comm.fence_phase import fence_phase
    # ... same logic as bifrost_ui.py:_vitals()
```

### The `operator_send` tool — detailed

This is the MCP-native version of the UI's `/send` endpoint. It uses the SAME
smart routing (T080 thread-anchor, intent-match, quick-claim) so an agent
responding to the operator gets the same routing logic as the UI.

```python
@mcp.tool()
def operator_send(from_agent: str, text: str, target: str = "auto") -> str:
    """Send an operator-class message. target='auto' uses smart routing
    (thread-anchor → intent-match → quick-claim → broadcast).
    Stamps meta.operator=1 so the recipient treats it as operator traffic."""
```

This is distinct from `bifrost_send` (agent-to-agent). `operator_send` is for
agent→operator communication, stamped with the operator class marker.

### What changes where

| File | Change | Complexity |
|------|--------|------------|
| `ai_setup_mcp.py` | Add `ui://status`, `ui://vitals` resources | ~15 lines each |
| `ai_setup_mcp.py` | Add `operator_send` tool (thin wrapper over T080 routing) | ~20 lines |
| `agent_cli.py cmd_boot()` | Render unread mail section (data already fetched) | ~15 lines |
| `ai_setup_mcp.py boot()` | Inherits the enhanced output automatically (thin wrapper) | 0 lines |

### What does NOT change

- The UI (bifrost_ui.py) — unchanged. It still serves :8787 for Daniel.
- The wake listener (bifrost_wake.py) — unchanged. It still detects mail arrival.
- The bus — unchanged. Messages still flow through Redis.
- The MCP's existing tools — unchanged. `bifrost_inbox`/`bifrost_sync` still work.

### Acceptance gates

1. **G1 — boot surfaces mail**: Agent calls `boot()` → sees unread message count + previews. No separate `bifrost_sync` needed.
2. **G2 — ui://vitals readable**: Agent reads `ui://vitals` resource → same data as `GET /vitals` on :8787.
3. **G3 — ui://status readable**: Agent reads `ui://status` resource → paused state, presence, bus health.
4. **G4 — operator_send routes**: Agent calls `operator_send("deepseek", "fix the bug", "auto")` → smart routing delivers to the right agent.
5. **G5 — zero new processes**: Only `ai_setup_mcp.py` is modified. No new servers, no new ports.
6. **G6 — no shell regression**: All existing shell paths (`agent_cli.py bifrost-sync`) continue to work.

### V-lines

V1. The MCP server is ALREADY the single source of truth for agent operations.
    Extending it with UI resources makes it the SINGLE door — the agent never
    leaves MCP. [PRINCIPLE]

V2. `boot()` already peeks the inbox — it just doesn't render it. Making it
    visible is a rendering change, not a new data path. [GROUNDED — the data
    is already there, line 1 of the boot code]

V3. Resources (ui://status, ui://vitals) are READ-ONLY projections over existing
    HTTP endpoints. They don't mutate state, add no new Redis keys, and can't
    break the UI. [SAFE]

V4. `operator_send` composes with our T080 routing design — same smart routing,
    different door. The UI's /send and MCP's operator_send share the routing
    logic through a common function. [DESIGN — the merge point with T080]
