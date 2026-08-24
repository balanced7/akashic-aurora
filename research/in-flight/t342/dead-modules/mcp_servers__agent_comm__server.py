"""
Agent Communication MCP Server
==============================
MCP server that exposes Redis-based agent communication tools.

Usage:
    # Direct run
    python -m agent_comm serve
    
    # Or with uv (recommended)
    uv run python -m agent_comm serve

Tools Exposed:
- send_message: Send message to another agent or broadcast
- check_messages: Check for new messages (returns structured output)
- get_active_agents: Get list of active agents
- get_my_status: Get current agent status
- declare_operation: Declare an operation with manifest + alert
- complete_operation: Complete an ongoing operation
- search_messages: Search message history semantically
"""

import sys
import os
import json
from typing import Optional, List, Dict, Any

# Set up path BEFORE any other imports
sys.path.insert(0, r'E:\AI-Setup')

# CRITICAL: For STDIO transport, all logging must go to stderr
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(name)s: %(message)s',
    stream=sys.stderr  # STDIO servers MUST log to stderr
)

logger = logging.getLogger("agent_comm_mcp")

try:
    from mcp.server.fastmcp import FastMCP
    from fast_agent_comm import get_fast_comm, MessagePriority
    from multi_agent import get_agent_registry, get_message_bus
    from agent_coordinator_v2 import get_coordinator, declare_operation, complete_operation
    from operational_alerts import AlertManager, AlertType
    from agent_comm_helper import get_my_id, get_messages as get_inbox_messages, get_unread_count
    COMM_AVAILABLE = True
    logger.info("Communication system loaded successfully")
except ImportError as e:
    COMM_AVAILABLE = False
    logger.warning(f"Communication system not available: {e}")

# Initialize FastMCP server
mcp = FastMCP("agent_comm")

# =============================================================================
# TOOL: send_message
# =============================================================================

@mcp.tool()
def send_message(
    to_agent: str,
    msg_type: str,
    content: dict,
    priority: str = "normal"
) -> str:
    """
    Send a message to another agent or broadcast to all agents.
    
    Args:
        to_agent: Target agent ID, 'broadcast' for all agents
        msg_type: Message type (chat, task_assign, help_request, coordinate)
        content: Message content as key-value pairs
        priority: Message priority (low, normal, high, critical)
    
    Returns:
        JSON result with success status and message ID
    """
    if not COMM_AVAILABLE:
        return json.dumps({"success": False, "error": "Communication system not available"})
    
    try:
        comm = get_fast_comm()
        agent_id = get_my_id()
        comm.set_agent_id(agent_id)
        
        priority_map = {
            "low": MessagePriority.LOW,
            "normal": MessagePriority.NORMAL,
            "high": MessagePriority.HIGH,
            "critical": MessagePriority.CRITICAL
        }
        msg_priority = priority_map.get(priority, MessagePriority.NORMAL)
        
        if to_agent == "broadcast":
            msg_id = comm.send_broadcast(msg_type, content, msg_priority)
        else:
            msg_id = comm.send_direct(to_agent, msg_type, content, msg_priority)
        
        return json.dumps({"success": msg_id is not None, "msg_id": msg_id})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# =============================================================================
# TOOL: check_messages
# =============================================================================

@mcp.tool()
def check_messages(limit: int = 10, mark_read: bool = True) -> str:
    """
    Check for new messages directed at this agent.
    
    Args:
        limit: Maximum number of messages to return
        mark_read: Mark messages as read after checking
    
    Returns:
        JSON with unread_count, has_new, messages array
    """
    if not COMM_AVAILABLE:
        return json.dumps({"success": False, "error": "Communication system not available"})
    
    try:
        agent_id = get_my_id()
        messages = get_inbox_messages(limit=limit)
        unread_count = get_unread_count()
        
        if mark_read and unread_count > 0:
            inbox_dir = os.path.join(r"E:\AI-Setup\blackboard_data\agent_coordination\inbox", agent_id)
            unread_file = os.path.join(inbox_dir, "unread.json")
            try:
                with open(unread_file, 'w') as f:
                    json.dump([], f)
            except:
                pass
        
        message_list = []
        latest_type = None
        latest_from = None
        
        if messages:
            latest = messages[-1]
            latest_type = latest.get("msg_type")
            latest_from = latest.get("from_agent")
            
            for m in messages:
                message_list.append({
                    "msg_id": m.get("msg_id", ""),
                    "from_agent": m.get("from_agent", ""),
                    "to_agent": m.get("to_agent", ""),
                    "msg_type": m.get("msg_type", ""),
                    "content": m.get("content", {}),
                    "timestamp": m.get("timestamp", ""),
                    "priority": m.get("priority", 1)
                })
        
        return json.dumps({
            "unread_count": unread_count,
            "has_new": unread_count > 0,
            "latest_msg_type": latest_type,
            "latest_from": latest_from,
            "messages": message_list
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# =============================================================================
# TOOL: get_active_agents
# =============================================================================

@mcp.tool()
def get_active_agents() -> str:
    """
    Get list of all active agents in the system.
    
    Returns:
        JSON with agents array and my_agent_id
    """
    if not COMM_AVAILABLE:
        return json.dumps({"success": False, "error": "Communication system not available"})
    
    try:
        registry = get_agent_registry()
        my_id = get_my_id()
        agents = registry.get_active_agents(include_self=True)
        
        agent_list = []
        for a in agents:
            agent_list.append({
                "agent_id": a.agent_id,
                "role": a.role,
                "status": a.status,
                "is_self": a.agent_id == my_id
            })
        
        return json.dumps({
            "agents": agent_list,
            "count": len(agent_list),
            "my_agent_id": my_id
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# =============================================================================
# TOOL: get_my_status
# =============================================================================

@mcp.tool()
def get_my_status() -> str:
    """
    Get this agent's current status.
    
    Returns:
        JSON with agent_id, manifest, active_alerts
    """
    if not COMM_AVAILABLE:
        return json.dumps({"success": False, "error": "Communication system not available"})
    
    try:
        agent_id = get_my_id()
        coordinator = get_coordinator()
        
        manifest = coordinator.get_manifest() if coordinator else None
        alert_mgr = AlertManager()
        active_alerts = alert_mgr.get_all_active_alerts()
        my_alerts = [a for a in active_alerts if a.agent_id == agent_id]
        
        return json.dumps({
            "agent_id": agent_id,
            "manifest": manifest.to_dict() if manifest else None,
            "active_alerts": [a.to_dict() for a in my_alerts],
            "alert_count": len(my_alerts)
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# =============================================================================
# TOOL: declare_operation
# =============================================================================

@mcp.tool()
def declare_operation(
    intent: str,
    scope: str = "",
    alert_type: str = "intent_declared",
    eta_minutes: int = 0,
    risk_level: str = "low",
    operations: str = "working"
) -> str:
    """
    Declare an ongoing operation that other agents should be aware of.
    Updates manifest AND creates operational alert atomically.
    
    Args:
        intent: What you plan to do
        scope: Comma-separated list of files/resources affected
        alert_type: Type of operation
        eta_minutes: Estimated completion time
        risk_level: low, medium, high, critical
        operations: Comma-separated list of operations being performed
    
    Returns:
        JSON with success status, manifest, and alert
    """
    if not COMM_AVAILABLE:
        return json.dumps({"success": False, "error": "Communication system not available"})
    
    try:
        import agent_coordinator_v2
        
        scope_list = [s.strip() for s in scope.split(",") if s.strip()] if scope else []
        ops_list = [o.strip() for o in operations.split(",")] if operations else ["working"]
        
        result = agent_coordinator_v2.declare_operation(
            intent=intent,
            scope=scope_list,
            alert_type=alert_type,
            eta_minutes=eta_minutes,
            risk_level=risk_level,
            operations=ops_list
        )
        
        if result:
            return json.dumps({
                "success": True,
                "manifest": result.get("manifest"),
                "alert": result.get("alert")
            }, indent=2, default=str)
        else:
            return json.dumps({"success": False, "error": "Failed to declare operation"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# =============================================================================
# TOOL: complete_operation
# =============================================================================

@mcp.tool()
def complete_operation(alert_id: str = None, scope: str = None) -> str:
    """
    Mark an ongoing operation as completed.
    
    Args:
        alert_id: Specific alert ID to complete (optional)
        scope: Comma-separated scope to match if alert_id not provided
    
    Returns:
        JSON with success status
    """
    if not COMM_AVAILABLE:
        return json.dumps({"success": False, "error": "Communication system not available"})
    
    try:
        import agent_coordinator_v2
        
        scope_list = [s.strip() for s in scope.split(",")] if scope else None
        
        agent_coordinator_v2.complete_operation(alert_id=alert_id, scope=scope_list)
        
        return json.dumps({"success": True, "message": "Operation completed"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# =============================================================================
# TOOL: search_messages
# =============================================================================

@mcp.tool()
def search_messages(query: str, top_k: int = 5) -> str:
    """
    Search message history semantically using vector embeddings.
    
    Args:
        query: Search query
        top_k: Number of results
    
    Returns:
        JSON with search results
    """
    if not COMM_AVAILABLE:
        return json.dumps({"success": False, "error": "Communication system not available"})
    
    try:
        bus = get_message_bus()
        results = bus.search_messages(query, top_k=top_k)
        
        return json.dumps({
            "query": query,
            "results": results,
            "count": len(results)
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# =============================================================================
# MAIN
# =============================================================================

def serve():
    """Start the MCP server"""
    logger.info("Starting Agent Communication MCP Server v1.0.0")
    logger.info(f"Communication system available: {COMM_AVAILABLE}")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    serve()
