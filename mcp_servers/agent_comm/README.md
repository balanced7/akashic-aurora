# Agent Communication MCP Server

Exposes the Redis-based multi-agent communication system as MCP tools.

## Quick Start

### 1. Test the MCP Server Manually

```bash
cd E:\AI-Setup\mcp_servers\agent_comm
python -m agent_comm serve
```

### 2. Add to OpenCode (Interactive)

Run OpenCode and use the MCP command:

```bash
opencode mcp add agent_comm
# Then follow prompts to add python -m agent_comm
```

### 3. Alternative: Edit OpenCode Config

OpenCode stores MCP config at `C:\Users\L5\.config\opencode\`

Add this to your OpenCode config file:

```json
{
  "mcpServers": {
    "agent_comm": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "agent_comm"],
      "cwd": "E:\\AI-Setup\\mcp_servers\\agent_comm",
      "env": {
        "PYTHONPATH": "E:\\AI-Setup"
      }
    }
  }
}
```

### 4. For Claude Code

Add to `~/.claude.json` or project `.mcp.json`:

```json
{
  "mcpServers": {
    "agent_comm": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "agent_comm"],
      "cwd": "E:\\AI-Setup\\mcp_servers\\agent_comm",
      "env": {
        "PYTHONPATH": "E:\\AI-Setup"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `send_message` | Send message to another agent or broadcast |
| `check_messages` | Check inbox for new messages |
| `get_active_agents` | List all active agents |
| `get_my_status` | Get current agent status |
| `declare_operation` | Start an operation (updates manifest + creates alert) |
| `complete_operation` | Complete an ongoing operation |
| `search_messages` | Semantic search over message history |

## Usage Examples

### Python (Direct)

```python
import sys
sys.path.insert(0, r'E:\AI-Setup')

from agent_comm_helper import check_messages, send_via_fast_comm

# Check messages
result = check_messages()
print(f"Unread: {result['unread_count']}")

# Send a message
send_via_fast_comm('broadcast', 'status_update', {'status': 'working'})
```

### Via MCP (When integrated)

```
# Check messages
Use the check_messages tool

# Declare an operation
Use declare_operation with:
- intent: "Refactoring auth module"
- scope: "auth.py, models/user.py"
- alert_type: "file_write_in_progress"
- eta_minutes: 15
- risk_level: "medium"

# Send a message
Use send_message with:
- to_agent: "broadcast" or specific agent ID
- msg_type: "chat" or "coordinate"
- content: {"message": "Hello team"}
- priority: "normal"
```

## Architecture

```
OpenCode Instance
├── MCP Client ──────> MCP Server (agent_comm)
│                              │
│                              └── Redis Streams
│                              └── File Inbox
│                              └── Vector Store
│
└── Background Monitor (100ms polling)
         │
         └── Redis PubSub ───> Windows Notifications
```

## Files

- `server.py` - FastMCP server implementation
- `__init__.py` - Package exports
- `opencode_mcp.json` - OpenCode config template
- `README.md` - This file
