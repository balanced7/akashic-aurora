"""
BreakThrough Stack MCP Server
============================
An MCP server that exposes session context, Redis data, session logs,
and knowledge base to AI clients via the Model Context Protocol.

Works with:
- OpenCode (as MCP client)
- Claude Desktop
- Other MCP-compatible clients

Usage:
    python ai_setup_mcp.py                    # Run with stdio transport
    python ai_setup_mcp.py --http            # Run with HTTP transport
"""

import os
import sys
import json
import redis
from datetime import datetime
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP, Context

REDIS_HOST = "localhost"
REDIS_PORT = 6379
SESSION_LOG_DIR = r"E:\AI-Setup\session_logs"
APP_DIR = r"E:\AI-Setup"

mcp = FastMCP(
    "BreakThrough Stack",
    instructions="Session context, Redis data, session logs, and knowledge base for BreakThrough Stack AI harness system."
)


def get_redis_connection():
    """Get Redis connection"""
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=0,
            decode_responses=True,
            socket_connect_timeout=5
        )
        r.ping()
        return r, True
    except Exception as e:
        return None, False


def get_session_id():
    """Get current session ID from session logger"""
    state_file = os.path.join(APP_DIR, "blackboard_data", "session_state.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state = json.load(f)
                return state.get("session_id", "unknown")
        except:
            pass
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


redis_client, redis_available = get_redis_connection()
CURRENT_SESSION = get_session_id()


# ============ RESOURCES ============

@mcp.resource("session://current")
def get_current_session() -> str:
    """Get current session information"""
    return json.dumps({
        "session_id": CURRENT_SESSION,
        "timestamp": datetime.now().isoformat(),
        "redis_available": redis_available,
        "app_directory": APP_DIR
    })


@mcp.resource("redis://stats")
def get_redis_stats() -> str:
    """Get Redis statistics"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        info = redis_client.info()
        keys = redis_client.keys("*")
        return json.dumps({
            "connected": True,
            "total_keys": len(keys),
            "used_memory": info.get("used_memory_human", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0),
            "connected_clients": info.get("connected_clients", 0)
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("redis://keys")
def get_all_redis_keys() -> str:
    """Get all Redis keys"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        keys = redis_client.keys("*")
        key_list = sorted(keys)
        categorized = {
            "session_actions": [k for k in key_list if k.startswith("session:")],
            "knowledge_base": [k for k in key_list if k.startswith("kb:")],
            "learnings": [k for k in key_list if k.startswith("learnings:")],
            "messages": [k for k in key_list if k.startswith("msg:")],
            "chat": [k for k in key_list if k.startswith("chat:")],
            "errors": [k for k in key_list if k.startswith("errors:")],
            "other": [k for k in key_list if not any(k.startswith(p) for p in ["session:", "kb:", "learnings:", "msg:", "chat:", "errors:", "system:", "opencode:", "agent_comm:", "shared:"])]
        }
        return json.dumps(categorized, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("redis://key/{key_name}")
def get_redis_key(key_name: str) -> str:
    """Get a specific Redis key value"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        key_type = redis_client.type(key_name)
        if key_type == "none":
            return json.dumps({"error": "Key not found"})
        
        if key_type == "string":
            value = redis_client.get(key_name)
        elif key_type == "list":
            value = redis_client.lrange(key_name, 0, -1)
        elif key_type == "hash":
            value = redis_client.hgetall(key_name)
        else:
            value = f"Type: {key_type}"
        
        return json.dumps({
            "key": key_name,
            "type": key_type,
            "value": value
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("session://actions")
def get_session_actions() -> str:
    """Get current session actions"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        actions_key = f"session:{CURRENT_SESSION}:actions"
        actions = redis_client.lrange(actions_key, 0, -1)
        parsed = [json.loads(a) for a in actions if a]
        return json.dumps({
            "session_id": CURRENT_SESSION,
            "action_count": len(parsed),
            "actions": parsed[-20:]  # Last 20
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("session://log")
def get_session_log_entries() -> str:
    """Get recent session log entries from file"""
    log_file = os.path.join(SESSION_LOG_DIR, "session_all.jsonl")
    if not os.path.exists(log_file):
        return json.dumps({"error": "Session log not found"})
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        entries = []
        for line in lines[-50:]:  # Last 50 entries
            try:
                entries.append(json.loads(line.strip()))
            except:
                continue
        
        return json.dumps({
            "total_entries": len(lines),
            "recent_entries": entries
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("knowledge://recent")
def get_recent_knowledge() -> str:
    """Get recent knowledge base entries"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        kb_keys = [k for k in redis_client.keys("kb:*") if not k.endswith(":learnings")]
        recent = []
        for key in kb_keys[-10:]:
            data = redis_client.hgetall(key)
            if data:
                recent.append({"key": key, "data": data})
        
        return json.dumps({
            "knowledge_base_entries": len(kb_keys),
            "recent": recent
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("learnings://all")
def get_all_learnings() -> str:
    """Get all learnings"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        learning_keys = redis_client.keys("learnings:*")
        learnings = []
        for key in learning_keys:
            data = redis_client.hgetall(key)
            if data:
                learnings.append({"key": key, "data": data})
        
        return json.dumps({
            "total_learnings": len(learnings),
            "learnings": learnings
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("context://summary")
def get_context_summary() -> str:
    """Get a summary of current context state"""
    summary = {
        "timestamp": datetime.now().isoformat(),
        "session_id": CURRENT_SESSION,
        "redis_available": redis_available
    }
    
    if redis_available:
        try:
            summary["stats"] = {
                "total_keys": len(redis_client.keys("*")),
                "session_actions": len(redis_client.lrange(f"session:{CURRENT_SESSION}:actions", 0, -1)),
                "knowledge_entries": len(redis_client.keys("kb:*")),
                "learnings": len(redis_client.keys("learnings:*"))
            }
        except:
            pass
    
    return json.dumps(summary, indent=2)


# ============ TOOLS ============

@mcp.tool()
def get_session_info() -> str:
    """Get detailed information about the current session"""
    info = {
        "session_id": CURRENT_SESSION,
        "timestamp": datetime.now().isoformat(),
        "redis_connected": redis_available,
        "app_directory": APP_DIR,
        "session_log_dir": SESSION_LOG_DIR
    }
    
    if redis_available:
        try:
            info["redis_stats"] = {
                "total_keys": len(redis_client.keys("*")),
                "actions_in_session": redis_client.llen(f"session:{CURRENT_SESSION}:actions"),
                "active_sessions": len(redis_client.smembers("sessions:active")) if redis_client.exists("sessions:active") else 0
            }
        except:
            pass
    
    return json.dumps(info, indent=2)


@mcp.tool()
def search_knowledge(query: str) -> str:
    """Search the knowledge base for a topic"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        results = []
        all_keys = redis_client.keys("kb:*")
        query_lower = query.lower()
        
        for key in all_keys:
            data = redis_client.hgetall(key)
            key_str = json.dumps(data).lower()
            if query_lower in key_str:
                results.append({"key": key, "data": data})
        
        return json.dumps({
            "query": query,
            "results_count": len(results),
            "results": results
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_learnings(query: str) -> str:
    """Search learnings for a topic"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        results = []
        all_keys = redis_client.keys("learnings:*")
        query_lower = query.lower()
        
        for key in all_keys:
            data = redis_client.hgetall(key)
            key_str = json.dumps(data).lower()
            if query_lower in key_str:
                results.append({"key": key, "data": data})
        
        return json.dumps({
            "query": query,
            "results_count": len(results),
            "results": results
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_session_history(sessions: int = 5) -> str:
    """Get history from recent sessions"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        session_keys = sorted(redis_client.keys("session:*:actions"), reverse=True)[:sessions]
        history = []
        
        for key in session_keys:
            session_id = key.split(":")[1]
            actions = redis_client.lrange(key, 0, -1)
            history.append({
                "session_id": session_id,
                "action_count": len(actions)
            })
        
        return json.dumps({
            "sessions": history
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_chat_history(limit: int = 20) -> str:
    """Get recent chat history"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        chats = redis_client.lrange("chat:history", -limit, -1)
        parsed = []
        for chat in reversed(chats):
            try:
                parsed.append(json.loads(chat))
            except:
                continue
        
        return json.dumps({
            "total_in_history": redis_client.llen("chat:history"),
            "returned": len(parsed),
            "messages": parsed
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_errors(limit: int = 10) -> str:
    """Get recent errors"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        errors = redis_client.lrange("errors:faults", -limit, -1)
        parsed = []
        for error in reversed(errors):
            try:
                parsed.append(json.loads(error))
            except:
                continue
        
        return json.dumps({
            "total_errors": redis_client.llen("errors:faults"),
            "returned": len(parsed),
            "errors": parsed
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_session_logs(query: str, log_file: str = "session_all.jsonl") -> str:
    """Search session logs for a query"""
    log_path = os.path.join(SESSION_LOG_DIR, log_file)
    if not os.path.exists(log_path):
        return json.dumps({"error": f"Log file not found: {log_file}"})
    
    try:
        results = []
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_str = json.dumps(entry).lower()
                    if query.lower() in entry_str:
                        results.append(entry)
                except:
                    continue
        
        return json.dumps({
            "query": query,
            "log_file": log_file,
            "results_count": len(results),
            "results": results[-20:]  # Last 20 matches
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_current_task() -> str:
    """Get the current task/goal from context"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        context_key = "context:current"
        context = redis_client.get(context_key)
        if context:
            return context
        
        # Fallback: get last action from current session
        actions_key = f"session:{CURRENT_SESSION}:actions"
        actions = redis_client.lrange(actions_key, -5, -1)
        if actions:
            last = json.loads(actions[-1])
            return json.dumps({
                "current_task": "Recent activity",
                "last_action": last.get("description", "Unknown"),
                "timestamp": last.get("timestamp", "")
            }, indent=2)
        
        return json.dumps({"current_task": "No active task found"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_active_blockers() -> str:
    """Get current blockers from context"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        blockers_key = "context:blockers"
        blockers = redis_client.get(blockers_key)
        if blockers:
            return blockers
        
        return json.dumps({"blockers": []})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============ PROMPTS ============

@mcp.prompt()
def session_summary_prompt() -> str:
    """Generate a prompt for getting session summary"""
    return f"""Provide a summary of the current session:

Session ID: {CURRENT_SESSION}
Time: {datetime.now().isoformat()}

Include:
1. What we're currently working on
2. Recent actions taken
3. Any blockers or issues
4. Suggested next steps
"""


@mcp.prompt()
def debug_error_prompt(error: str) -> str:
    """Generate a prompt for debugging an error"""
    return f"""Help me debug this error:

Error: {error}

Consider:
1. What might have caused this
2. What was the last action before the error
3. How to fix it
4. How to prevent it in the future
"""


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BreakThrough Stack MCP Server")
    parser.add_argument("--http", action="store_true", help="Use HTTP transport instead of stdio")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    
    args = parser.parse_args()
    
    if args.http:
        print(f"Starting MCP server on HTTP port {args.port}")
        mcp.run(transport="streamable-http", port=args.port)
    else:
        print("Starting MCP server with stdio transport")
        mcp.run()
