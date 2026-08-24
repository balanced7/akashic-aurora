"""
Agent Communication MCP Server Package
=====================================

Wrap your Redis-based inter-agent communication system as MCP tools.

Usage:
    # Run as module
    python -m agent_comm serve
    
    # Or with uv
    uv run python -m agent_comm serve

Available MCP Tools:
- send_message: Send message to another agent or broadcast
- check_messages: Check for new messages
- get_active_agents: Get list of active agents
- get_my_status: Get current agent status
- declare_operation: Declare an operation with manifest + alert
- complete_operation: Complete an ongoing operation
- search_messages: Search message history semantically
"""

from .server import mcp, serve

__all__ = ["mcp", "serve"]
