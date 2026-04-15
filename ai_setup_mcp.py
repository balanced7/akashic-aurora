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


# ============ PROJECT CONTEXT RESOURCES ============

@mcp.resource("project://architecture")
def get_project_architecture() -> str:
    """Get architectural documentation"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        data = redis_client.get("context:architecture")
        if data:
            return data
        return json.dumps({"error": "Architecture not yet documented"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("project://milestones")
def get_project_milestones() -> str:
    """Get all milestones"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        milestones = []
        data = redis_client.hgetall("context:milestones")
        for m_id, m_json in data.items():
            milestones.append(json.loads(m_json))
        
        # Group by status
        by_status = {"pending": [], "in_progress": [], "completed": [], "blocked": []}
        for m in milestones:
            by_status[m.get("status", "pending")].append(m)
        
        return json.dumps({
            "total": len(milestones),
            "by_status": by_status
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("project://tasks")
def get_project_tasks() -> str:
    """Get all tasks"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        tasks = []
        data = redis_client.hgetall("context:tasks")
        for t_id, t_json in data.items():
            tasks.append(json.loads(t_json))
        
        by_status = {"todo": [], "in_progress": [], "done": [], "blocked": []}
        for t in tasks:
            by_status[t.get("status", "todo")].append(t)
        
        return json.dumps({
            "total": len(tasks),
            "by_status": by_status
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("project://blockers")
def get_project_blockers() -> str:
    """Get all blockers"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        blockers = []
        data = redis_client.hgetall("context:blockers")
        for b_id, b_json in data.items():
            blockers.append(json.loads(b_json))
        
        active = [b for b in blockers if b.get("status") == "active"]
        resolved = [b for b in blockers if b.get("status") == "resolved"]
        
        return json.dumps({
            "total": len(blockers),
            "active": active,
            "resolved_count": len(resolved)
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("project://context")
def get_full_project_context() -> str:
    """Get complete project context for agent re-priming"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        # Import here to avoid circular dependency
        from project_context import get_context_manager
        return json.dumps(get_context_manager().get_full_context(), indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("project://summary")
def get_project_summary() -> str:
    """Get a quick project summary"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    
    try:
        arch = redis_client.get("context:architecture")
        arch_data = json.loads(arch) if arch else {}
        
        milestones = redis_client.hgetall("context:milestones")
        tasks = redis_client.hgetall("context:tasks")
        blockers = redis_client.hgetall("context:blockers")
        
        active_blockers = [b for b in blockers.values() if json.loads(b).get("status") == "active"]
        
        return json.dumps({
            "project": arch_data.get("name", "BreakThrough Stack"),
            "purpose": arch_data.get("purpose", ""),
            "milestones": {
                "total": len(milestones),
                "completed": len([m for m in milestones.values() if json.loads(m).get("status") == "completed"]),
                "in_progress": len([m for m in milestones.values() if json.loads(m).get("status") == "in_progress"])
            },
            "tasks": {
                "total": len(tasks),
                "todo": len([t for t in tasks.values() if json.loads(t).get("status") == "todo"]),
                "in_progress": len([t for t in tasks.values() if json.loads(t).get("status") == "in_progress"]),
                "done": len([t for t in tasks.values() if json.loads(t).get("status") == "done"])
            },
            "active_blockers": len(active_blockers)
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============ PROJECT CONTEXT TOOLS ============

@mcp.tool()
def get_full_context() -> str:
    """Get complete project context for agent re-priming (4 layers)"""
    try:
        from project_context import get_context_manager
        return json.dumps(get_context_manager().get_full_context(), indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def add_milestone(name: str, description: str = "", priority: int = 0) -> str:
    """Add a new milestone"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        mid = mgr.add_milestone(name, description, priority)
        return json.dumps({"success": True, "milestone_id": mid})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def update_milestone_status(milestone_id: str, status: str) -> str:
    """Update milestone status (pending|in_progress|completed|blocked)"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        mgr.update_milestone_status(milestone_id, status)
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def add_task(title: str, description: str = "", milestone_id: str = "") -> str:
    """Add a new task"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        tid = mgr.add_task(title, description, milestone_id or None)
        return json.dumps({"success": True, "task_id": tid})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def update_task_status(task_id: str, status: str) -> str:
    """Update task status (todo|in_progress|done|blocked)"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        mgr.update_task_status(task_id, status)
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def add_blocker(description: str, severity: str = "medium") -> str:
    """Add a blocker"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        bid = mgr.add_blocker(description, severity)
        return json.dumps({"success": True, "blocker_id": bid})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def resolve_blocker(blocker_id: str) -> str:
    """Resolve a blocker"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        mgr.resolve_blocker(blocker_id)
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def set_current_work(task: str, details: str = "") -> str:
    """Set what we're currently working on"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        mgr.set_current_task(task, details)
        mgr.add_to_work_log(f"Started: {task}")
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_progress() -> str:
    """Get project progress summary"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        
        milestones = mgr.get_milestones()
        tasks = mgr.get_tasks()
        blockers = mgr.get_blockers(status="active")
        
        completed_milestones = len([m for m in milestones if m.status == "completed"])
        done_tasks = len([t for t in tasks if t.status == "done"])
        
        progress = 0
        total_items = len(milestones) + len(tasks)
        if total_items > 0:
            progress = int(100 * (completed_milestones + done_tasks) / total_items)
        
        return json.dumps({
            "progress_percentage": progress,
            "milestones": {
                "total": len(milestones),
                "completed": completed_milestones,
                "in_progress": len([m for m in milestones if m.status == "in_progress"])
            },
            "tasks": {
                "total": len(tasks),
                "done": done_tasks,
                "in_progress": len([t for t in tasks if t.status == "in_progress"])
            },
            "active_blockers": len(blockers)
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def print_context() -> str:
    """Print human-readable full context to console"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        mgr.print_full_context()
        return json.dumps({"success": True})
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
