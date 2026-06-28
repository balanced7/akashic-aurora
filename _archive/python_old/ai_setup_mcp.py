"""
Akashic Aurora Unified MCP Server
====================================
Single MCP server for all Akashic Aurora tools:

- Session Context & Logging (Redis)
- Project Management  
- Screenspace Automation (Windows GUI)
- Vision & OCR
- Fast Cache (Redis + RAM)

Usage:
    python ai_setup_mcp.py                    # Stdio (OpenCode)
    python ai_setup_mcp.py --http --port 8080  # HTTP (Claude Desktop)
"""

import os
import sys
import json
import base64
import time
import redis
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Context
import fast_cache  # Fast cache module

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    BASE_DIR,
    CANONICAL_EVENTS_JSONL,
    get_redis_config,
    SESSION_EVENTS_STREAM,
    SESSION_STATE_FILE,
)

# Config
SESSION_LOG_DIR = str(BASE_DIR / "session_logs")
APP_DIR = str(BASE_DIR)
SCREENSHOT_DIR = str(BASE_DIR / "session_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

LAUNCH_CONTRACT_JSON = json.dumps(
    {
        "description": "Akashic Aurora agent boot contract",
        "resource_uri": "breakthrough://launch-contract",
        "redis_write_host": "localhost",
        "redis_write_port": 6380,
        "docker_redis_mirror_port": 16379,
        "canonical_stream": "session:events",
        "schema_tool": "session_append_event",
        "recommended_first_call": "breakthrough_bootstrap(agent, tier)",
        "tiers": {
            "minimal": "WSL keeper + Redis HA only",
            "standard": "minimal + Docker Redis mirror + ai-voice + session compressor",
            "full": "Same as standard (reserved)",
        },
        "sequence": [
            "1 breakthrough_bootstrap(agent, tier, intent, systems_worked) OR session_infra_ensure + session_register",
            "2 python E:\\\\AI-Setup\\\\catchup.py (optional deeper briefing)",
            "3 get_full_context / get_progress for big picture",
            "4 session_append_event on material changes; learning_record_decision for ADRs",
            "5 session_flush_summary before hand-off",
        ],
        "infra_gate_env": "BREAKTHROUGH_ALLOW_INFRA_START (default allows starts)",
    },
    indent=2,
)


SCREENSPACE_CATALOG_JSON = json.dumps(
    {
        "resource": "screenspace://catalog",
        "screenshots_dir": SCREENSHOT_DIR,
        "tools": {
            "vision_capture": [
                "screenshot(label) — full desktop PNG",
                "capture_window(window_title, label) — window by partial title",
                "capture_region(x, y, width, height, label) — bbox",
                "analyze_screen(task) — full screen + base64 snippet",
                "screenspace_capture_ocr(window_title, label) — capture_window + OCR in one call",
            ],
            "text_from_screen": [
                "ocr(image_path) — Tesseract on file or live grab if path omitted",
            ],
            "windows_ui": [
                "list_windows() — visible titles (short Redis/RAM cache)",
                "find_window(title) — hwnd + match",
                "activate_window(title) — foreground",
                "get_screen_size()",
            ],
            "clipboard_input": [
                "clipboard_read() / clipboard_write(text)",
                "click / double_click / type_text / press_key / hotkey / scroll / move_to / get_cursor_position",
            ],
            "helpers": ["run_powershell(command)", "list_files(directory, pattern)"],
        },
        "recommended_flow": [
            "1 list_windows()",
            "2 find_window('cmd') or activate_window('Windows Terminal')",
            "3 screenspace_capture_ocr('ZLUDA') or capture_window(...) then ocr(path)",
        ],
        "ocr_note": "Install Tesseract and ensure pytesseract can find it; else OCR returns a clear error string.",
    },
    indent=2,
)

mcp = FastMCP(
    "Akashic Aurora",
    instructions=(
        "Unified MCP for Akashic Aurora. FIRST on a new session: call breakthrough_bootstrap(agent, tier, intent, systems_worked) "
        "OR session_infra_ensure then session_register. Resource breakthrough://launch-contract has the full boot schema JSON. "
        "Then catchup / get_full_context. Log with session_append_event; ADRs with learning_record_decision. "
        "Ops health: ai_watchdog_report (ports + canonical logging + infra snapshot); optional ai_watchdog_ensure_infra. "
        "Redis WSL master localhost:6380, Docker Stack localhost:16379. "
        "SCREENSPACE (Windows): read resource screenspace://catalog. Tools: list_windows, find_window, activate_window, "
        "screenshot, capture_window, capture_region, screenspace_capture_ocr, ocr, analyze_screen, clipboard_read/write, click, type_text."
    ),
)


def get_redis_connection():
    try:
        r = redis.Redis(**get_redis_config())
        r.ping()
        return r, True
    except Exception:
        return None, False


def get_session_id():
    if os.path.exists(SESSION_STATE_FILE):
        try:
            with open(SESSION_STATE_FILE, "r", encoding="utf-8") as f:
                sid = json.load(f).get("session_id")
                if sid:
                    return str(sid)
        except Exception:
            pass
    return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


redis_client, redis_available = get_redis_connection()
CURRENT_SESSION = get_session_id()


# ============ UTILITIES ============

def save_screenshot(label: str = "mcp") -> dict:
    """Capture screenshot and save to session_screenshots"""
    try:
        from PIL import ImageGrab
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screen_{timestamp}_{label}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        img = ImageGrab.grab()
        img.save(filepath)
        return {"success": True, "path": filepath, "label": label}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _capture_region_impl(x: int, y: int, width: int, height: int, label: str = "region") -> dict:
    """Capture a region of the screen"""
    try:
        from PIL import ImageGrab
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"region_{timestamp}_{label}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        img = ImageGrab.grab(bbox=(x, y, x + width, y + height))
        img.save(filepath)
        return {"success": True, "path": filepath, "region": {"x": x, "y": y, "width": width, "height": height}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_image_base64(filepath: str) -> str:
    """Get base64 encoded image for LLM analysis"""
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return ""


def ocr_image(filepath: str) -> str:
    """OCR an image file"""
    try:
        from PIL import Image
        import pytesseract
        
        img = Image.open(filepath)
        text = pytesseract.image_to_string(img)
        return text.strip() if text else "No text found"
    except ImportError:
        return "pytesseract not installed"
    except Exception as e:
        return f"OCR error: {str(e)}"


# ============ RESOURCES ============

@mcp.resource("session://current")
def get_current_session() -> str:
    return json.dumps({
        "session_id": CURRENT_SESSION,
        "timestamp": datetime.now().isoformat(),
        "redis_available": redis_available,
        "app_directory": APP_DIR
    })


@mcp.resource("redis://stats")
def get_redis_stats() -> str:
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    try:
        info = redis_client.info()
        return json.dumps({
            "connected": True,
            "total_keys": len(redis_client.keys("*")),
            "used_memory": info.get("used_memory_human", "unknown"),
            "uptime_days": info.get("uptime_in_days", 0)
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("redis://keys")
def get_all_redis_keys() -> str:
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    try:
        keys = redis_client.keys("*")
        categorized = {
            "sessions": [k for k in keys if k.startswith("session:")],
            "knowledge": [k for k in keys if k.startswith("kb:")],
            "learnings": [k for k in keys if k.startswith("learnings:")],
            "patches": [k for k in keys if k.startswith("patches:")],
            "context": [k for k in keys if k.startswith("context:")],
        }
        return json.dumps(categorized, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.resource("breakthrough://launch-contract")
def breakthrough_launch_contract() -> str:
    """Machine-readable boot schema, tiers, and tool sequence for new agents."""
    return LAUNCH_CONTRACT_JSON


@mcp.resource("screenspace://catalog")
def screenspace_catalog() -> str:
    """Screenspace / Windows GUI: tool names, roles, and recommended capture→OCR flow."""
    return SCREENSPACE_CATALOG_JSON


@mcp.resource("context://summary")
def get_context_summary() -> str:
    summary = {"timestamp": datetime.now().isoformat(), "session_id": CURRENT_SESSION, "redis_available": redis_available}
    if redis_available:
        try:
            summary["stats"] = {
                "total_keys": len(redis_client.keys("*")),
                "knowledge_entries": len(redis_client.keys("kb:*")),
            }
        except:
            pass
    return json.dumps(summary, indent=2)


# ============ SESSION TOOLS ============

@mcp.tool()
def get_session_info() -> str:
    """Get current session information"""
    return json.dumps({
        "session_id": CURRENT_SESSION,
        "timestamp": datetime.now().isoformat(),
        "redis_connected": redis_available,
        "app_directory": APP_DIR
    })


@mcp.tool()
def search_knowledge(query: str) -> str:
    """Search knowledge base in Redis"""
    if not redis_available:
        return json.dumps({"error": "Redis not available"})
    try:
        results = []
        for key in redis_client.keys("kb:*"):
            data = redis_client.hgetall(key)
            if query.lower() in json.dumps(data).lower():
                results.append({"key": key, "data": data})
        return json.dumps({"query": query, "results": results, "count": len(results)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def search_session_logs(query: str, limit: int = 20) -> str:
    """Search compact session JSONL plus canonical events mirror (Redis stream is primary live copy)."""
    log_path = os.path.join(SESSION_LOG_DIR, "session_all.jsonl")
    ql = query.lower()
    try:
        results = []
        canon = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if ql in json.dumps(entry).lower():
                            results.append(entry)
                    except Exception:
                        continue
        if CANONICAL_EVENTS_JSONL.exists():
            with open(CANONICAL_EVENTS_JSONL, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if ql in json.dumps(entry).lower():
                            canon.append(entry)
                    except Exception:
                        continue
        tail = (results + canon)[-(limit * 2) :]
        return json.dumps(
            {
                "query": query,
                "session_all_count": len(results),
                "canonical_count": len(canon),
                "results": tail[-limit:],
                "count": len(tail[-limit:]),
            },
            default=str,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============ PROJECT CONTEXT TOOLS ============

@mcp.tool()
def get_full_context() -> str:
    """Get complete project context"""
    try:
        from project_context import get_context_manager
        return json.dumps(get_context_manager().get_full_context(), indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_progress() -> str:
    """Get project progress"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        milestones = mgr.get_milestones()
        tasks = mgr.get_tasks()
        completed = len([m for m in milestones if m.status == "completed"]) + len([t for t in tasks if t.status == "done"])
        total = len(milestones) + len(tasks)
        return json.dumps({
            "progress": int(100 * completed / total) if total > 0 else 0,
            "milestones": len(milestones),
            "tasks": len(tasks)
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def set_current_work(task: str) -> str:
    """Set current task"""
    try:
        from project_context import get_context_manager
        mgr = get_context_manager()
        mgr.set_current_task(task)
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def session_set_identity(session_id: str) -> str:
    """Persist the active Akashic Aurora session id (shared by Cursor / Claude / OpenCode)."""
    try:
        from session_canonical import persist_session_id

        sid = session_id.strip()
        if not sid:
            return json.dumps({"success": False, "error": "empty session_id"})
        persist_session_id(sid)
        global CURRENT_SESSION
        CURRENT_SESSION = sid
        return json.dumps({"success": True, "session_id": sid})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def session_append_event(
    agent: str,
    event_type: str = "note",
    session_id: str = "",
    intent: str = "",
    systems_worked: str = "",
    changes_made: str = "",
    milestones_update: str = "",
    decisions: str = "",
    blockers: str = "",
    next_steps: str = "",
) -> str:
    """
    Primary session documentation path: canonical Redis Stream (``session:events``) + JSONL mirror.
    Agents should call at session start (intent/systems), on material changes (changes/milestones), and close (next_steps/blockers).

    Args:
      agent: e.g. cursor, claude, opencode.
      event_type: start | note | change | milestone | decision | blocker | close | summary_request | flush_summary
      session_id: optional; defaults to persisted session identity.
      Other fields: short enterprise-style notes—multiline plain text OK.
    """
    try:
        from session_canonical import append_session_event

        sid = (session_id or "").strip() or get_session_id()
        res = append_session_event(
            redis_client=redis_client if redis_available else None,
            session_id=sid,
            agent=agent,
            event_type=event_type or "note",
            intent=intent,
            systems_worked=systems_worked,
            changes_made=changes_made,
            milestones_update=milestones_update,
            decisions=decisions,
            blockers=blockers,
            next_steps=next_steps,
        )
        global CURRENT_SESSION
        CURRENT_SESSION = sid
        return json.dumps(res, default=str)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
def session_flush_summary(session_id: str = "") -> str:
    """Aggregate canonical stream payloads + legacy LIST/string log into a fresh ``session:summary`` (WSL + Docker)."""
    try:
        from session_canonical import aggregated_text_for_session
        from session_compressor import SessionCompressor

        sid = (session_id or "").strip() or get_session_id()
        if not redis_available or redis_client is None:
            return json.dumps({"ok": False, "error": "Redis unavailable"})

        agg = aggregated_text_for_session(redis_client, sid)
        comp = SessionCompressor()
        raw = comp._gather_raw_log(sid)
        merged = agg
        if raw.strip():
            merged = (agg.rstrip() + "\n\n--- list/string log ---\n" + raw).strip()

        if not merged:
            return json.dumps({"ok": False, "session_id": sid, "reason": "no events or log"})

        ok = comp.compress_session_from_plaintext(sid, merged)
        return json.dumps({"ok": ok, "session_id": sid, "chars": len(merged)})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
def project_add_milestone(name: str, description: str = "", priority: int = 0) -> str:
    """Add a roadmap milestone (Redis project_context)."""
    try:
        from project_context import get_context_manager

        mid = get_context_manager().add_milestone(name, description, priority=int(priority))
        return json.dumps({"success": bool(mid), "milestone_id": mid})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def project_complete_milestone(milestone_id: str) -> str:
    """Mark a milestone completed by id."""
    try:
        from project_context import get_context_manager

        get_context_manager().complete_milestone(milestone_id.strip())
        return json.dumps({"success": True, "milestone_id": milestone_id})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def project_log_blocker(description: str, severity: str = "medium") -> str:
    """Record a project blocker."""
    try:
        from project_context import get_context_manager

        bid = get_context_manager().add_blocker(description, severity=severity or "medium")
        return json.dumps({"success": bool(bid), "blocker_id": bid})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def search_canonical_session_events(query: str, limit: int = 30) -> str:
    """Search JSONL mirror of canonical session events (stream overflow / offline forensics)."""
    q = (query or "").lower()
    matches = []
    if not CANONICAL_EVENTS_JSONL.exists():
        return json.dumps({"query": query, "results": [], "count": 0})
    try:
        with open(CANONICAL_EVENTS_JSONL, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            if q and q not in line.lower():
                continue
            try:
                matches.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(matches) >= int(limit):
                break
        return json.dumps({"query": query, "count": len(matches), "results": matches}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def stream_session_events_tail(count: int = 20) -> str:
    """Return the newest entries from Redis ``session:events`` (WSL master)."""
    if not redis_available or redis_client is None:
        return json.dumps({"error": "Redis unavailable"})
    try:
        n = max(1, min(int(count), 200))
        rows = redis_client.xrevrange(SESSION_EVENTS_STREAM, max="+", min="-", count=n)
        out = []
        for mid, fields in rows:
            row = {"id": mid, **dict(fields)}
            out.append(row)
        return json.dumps({"stream": SESSION_EVENTS_STREAM, "count": len(out), "entries": out}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def session_infra_status() -> str:
    """Redis / Docker mirror / voice / compressor snapshot (no side effects). Uses WSL master 6380."""
    try:
        from session_supervisor import infra_status

        return json.dumps(infra_status(), indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def session_infra_ensure(tier: str = "standard", agent: str = "manual") -> str:
    """
    Launch infra via DAG-aware supervisor (does not start win-mcp).
    tier: minimal | standard | full
    Set BREAKTHROUGH_ALLOW_INFRA_START=0 to block launches (inspect-only).
    """
    try:
        from session_supervisor import ensure_infra

        return json.dumps(ensure_infra(tier, agent), indent=2, default=str)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@mcp.tool()
def session_register(
    agent: str,
    session_id: str = "",
    intent: str = "",
    systems_worked: str = "",
) -> str:
    """
    Persist session id + emit canonical ``start`` event on ``session:events``.
    If session_id empty, generates ``{agent}_YYYYMMDD_HHMMSS``.
    """
    try:
        from session_canonical import append_session_event, persist_session_id

        sid = (session_id or "").strip()
        if not sid:
            sid = f"{(agent or 'manual').strip()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        persist_session_id(sid)
        global CURRENT_SESSION
        CURRENT_SESSION = sid
        res = append_session_event(
            redis_client=redis_client if redis_available else None,
            session_id=sid,
            agent=agent,
            event_type="start",
            intent=intent or f"Session start ({agent})",
            systems_worked=systems_worked,
        )
        return json.dumps({"success": True, "session_id": sid, "append": res}, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def breakthrough_bootstrap(
    agent: str,
    tier: str = "standard",
    session_id: str = "",
    intent: str = "",
    systems_worked: str = "",
    skip_infra: bool = False,
    skip_start_event: bool = False,
) -> str:
    """
    One-call onboarding: optional infra ensure → register session id → ``start`` stream event → Redis/WSL context snapshot.
    Read resource breakthrough://launch-contract for field meanings.
    """
    try:
        from session_canonical import append_session_event, persist_session_id
        from session_supervisor import bootstrap_context_snapshot, ensure_infra

        tier_l = (tier or "standard").strip().lower()
        ensure_report = None
        if not skip_infra:
            ensure_report = ensure_infra(tier_l, agent)

        sid = (session_id or "").strip()
        if not sid:
            sid = f"{(agent or 'manual').strip()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        persist_session_id(sid)
        global CURRENT_SESSION
        CURRENT_SESSION = sid

        start_evt = None
        if not skip_start_event:
            start_evt = append_session_event(
                redis_client=redis_client if redis_available else None,
                session_id=sid,
                agent=agent,
                event_type="start",
                intent=intent or f"Bootstrap ({agent})",
                systems_worked=systems_worked or "Akashic Aurora stack; see breakthrough://launch-contract",
            )

        snap = bootstrap_context_snapshot(session_id=sid)

        return json.dumps(
            {
                "success": True,
                "session_id": sid,
                "tier": tier_l,
                "infra_ensure": ensure_report,
                "start_event": start_evt,
                "snapshot": snap,
            },
            indent=2,
            default=str,
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def learning_record_decision(
    title: str,
    decision: str,
    context: str = "",
    rationale_json: str = "[]",
    session_id: str = "",
) -> str:
    """Persist an ADR-style decision to Redis learn:decisions (LearningStore)."""
    try:
        from learning.store import learn

        rationale = json.loads(rationale_json or "[]")
        if not isinstance(rationale, list):
            rationale = [str(rationale)]
        sid = (session_id or "").strip() or CURRENT_SESSION
        did = learn().decide(
            title=title,
            decision=decision,
            context=context,
            rationale=rationale,
            session_id=sid,
        )
        return json.dumps({"success": bool(did), "decision_id": did})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def learning_record_experience(
    task: str,
    success: bool,
    approach: str = "",
    result: str = "",
    learnings_json: str = "[]",
    session_id: str = "",
) -> str:
    """Record a task outcome in Redis learn:experiences."""
    try:
        from learning.store import learn

        le = json.loads(learnings_json or "[]")
        if not isinstance(le, list):
            le = [str(le)]
        sid = (session_id or "").strip() or CURRENT_SESSION
        eid = learn().record(
            task=task,
            success=success,
            approach=approach,
            result=result,
            learnings=le,
            session_id=sid,
        )
        return json.dumps({"success": bool(eid), "experience_id": eid})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def ai_watchdog_report(sync_ports: bool = True) -> str:
    """
    AI Watchdog snapshot: port conflicts + Redis port registry sync, canonical ``session:events`` / JSONL,
    legacy OpenCode log hints, infra_status-style Redis/voice/compressor flags.
    """
    try:
        from ai_watchdog import collect_report

        rep = collect_report(sync_ports=sync_ports, ensure_infra=False)
        return json.dumps(rep, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def ai_watchdog_ensure_infra(tier: str = "standard", agent: str = "mcp") -> str:
    """
    Run session_supervisor.ensure_infra once (DAG launches Docker mirror, voice, compressor, etc.).
    Respects BREAKTHROUGH_ALLOW_INFRA_START.
    """
    try:
        from ai_watchdog import collect_report

        rep = collect_report(sync_ports=True, ensure_infra=True, infra_tier=tier, infra_agent=agent)
        return json.dumps(rep, indent=2, default=str)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ============ SCREENSPACE TOOLS ============

@mcp.tool()
def screenshot(label: str = "capture") -> str:
    """Capture full screen screenshot"""
    result = save_screenshot(label)
    return json.dumps(result, indent=2)


@mcp.tool()
def capture_window(window_title: str, label: str = "window") -> str:
    """Capture a specific window by title - uses ctypes for speed"""
    try:
        from PIL import ImageGrab
        import ctypes
        from ctypes import wintypes
        from ctypes.wintypes import RECT
        
        # Find window by title
        EnumWindows = ctypes.windll.user32.EnumWindows
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        GetWindowRect = ctypes.windll.user32.GetWindowRect
        GetClientRect = ctypes.windll.user32.GetClientRect
        
        found_hwnd = None
        title_lower = window_title.lower()
        
        def enum_callback(hwnd, lparam):
            nonlocal found_hwnd
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buffer, length + 1)
                    wtitle = buffer.value
                    if title_lower in wtitle.lower():
                        found_hwnd = hwnd
                        return False
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        EnumWindows(EnumWindowsProc(enum_callback), 0)
        
        if not found_hwnd:
            return json.dumps({"success": False, "error": f"Window not found: {window_title}"})
        
        # Get window rect
        rect = RECT()
        GetWindowRect(found_hwnd, ctypes.byref(rect))
        
        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"window_{timestamp}_{label}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        
        img = ImageGrab.grab(bbox=(left, top, right, bottom))
        img.save(filepath)
        
        return json.dumps({"success": True, "path": filepath, "window": window_title, "bounds": f"{left},{top},{right},{bottom}"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def capture_region(x: int, y: int, width: int, height: int, label: str = "region") -> str:
    """Capture a screen region"""
    return json.dumps(_capture_region_impl(x, y, width, height, label), indent=2)


@mcp.tool()
def ocr(image_path: str = None) -> str:
    """OCR text from screenshot or image file"""
    try:
        if image_path and os.path.exists(image_path):
            text = ocr_image(image_path)
        else:
            # Capture and OCR
            result = save_screenshot("ocr_temp")
            if result["success"]:
                text = ocr_image(result["path"])
            else:
                return json.dumps({"error": result.get("error", "Screenshot failed")})
        
        return json.dumps({"text": text, "image": image_path})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def screenspace_capture_ocr(window_title: str, label: str = "ocr") -> str:
    """Windows: capture a visible window by partial title, then OCR it (one round-trip). Saves PNG under session_screenshots."""
    try:
        cap_raw = capture_window(window_title, label)
        cap = json.loads(cap_raw)
        if not cap.get("success"):
            return cap_raw
        path = cap["path"]
        text = ocr_image(path)
        return json.dumps(
            {
                "success": True,
                "image_path": path,
                "bounds": cap.get("bounds"),
                "window_query": window_title,
                "ocr_text": text,
            },
            indent=2,
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
def click(x: int, y: int, button: str = "left") -> str:
    """Click at coordinates"""
    try:
        import pyautogui
        pyautogui.click(x, y, button=button)
        return json.dumps({"success": True, "action": f"click({x}, {y}, button='{button}')"})
    except ImportError:
        return json.dumps({"error": "pyautogui not installed"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def double_click(x: int, y: int) -> str:
    """Double click at coordinates"""
    try:
        import pyautogui
        pyautogui.doubleClick(x, y)
        return json.dumps({"success": True, "action": f"doubleClick({x}, {y})"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def type_text(text: str) -> str:
    """Type text at current cursor position"""
    try:
        import pyautogui
        pyautogui.typewrite(text)
        return json.dumps({"success": True, "action": f"typewrite('{text[:50]}...')"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def press_key(key: str) -> str:
    """Press a keyboard key"""
    try:
        import pyautogui
        pyautogui.press(key)
        return json.dumps({"success": True, "action": f"press('{key}')"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def hotkey(key1: str, key2: str, *keys) -> str:
    """Press keyboard hotkey combination"""
    try:
        import pyautogui
        pyautogui.hotkey(key1, key2, *keys)
        return json.dumps({"success": True, "action": f"hotkey('{key1}', '{key2}', {keys})"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def scroll(clicks: int, x: int = None, y: int = None) -> str:
    """Scroll mouse wheel"""
    try:
        import pyautogui
        pyautogui.scroll(clicks, x=x, y=y)
        return json.dumps({"success": True, "action": f"scroll({clicks})"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def move_to(x: int, y: int, duration: float = 0.5) -> str:
    """Move mouse to coordinates"""
    try:
        import pyautogui
        pyautogui.moveTo(x, y, duration=duration)
        return json.dumps({"success": True, "action": f"moveTo({x}, {y})"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_cursor_position() -> str:
    """Get current mouse cursor position"""
    try:
        import pyautogui
        x, y = pyautogui.position()
        return json.dumps({"x": x, "y": y})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_windows() -> str:
    """List all visible windows - cached for speed"""
    # Check cache first
    cached = fast_cache.redis_get("windows:list")
    if cached:
        return json.dumps(cached)
    
    try:
        import subprocess
        import ctypes
        from ctypes import wintypes
        
        # Use ctypes directly - much faster than PowerShell
        EnumWindows = ctypes.windll.user32.EnumWindows
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        
        windows = []
        
        def enum_callback(hwnd, lparam):
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buffer, length + 1)
                    title = buffer.value
                    if title:
                        windows.append(title)
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        EnumWindows(EnumWindowsProc(enum_callback), 0)
        
        result = {"windows": windows, "count": len(windows)}
        
        # Cache for 10 seconds
        fast_cache.redis_set("windows:list", result, ttl=10)
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "fallback": "Try using capture_region instead"})


@mcp.tool()
def find_window(title: str) -> str:
    """Find window by partial title match - uses ctypes for speed"""
    try:
        import ctypes
        from ctypes import wintypes
        
        EnumWindows = ctypes.windll.user32.EnumWindows
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        
        found_hwnd = None
        title_lower = title.lower()
        
        def enum_callback(hwnd, lparam):
            nonlocal found_hwnd
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buffer, length + 1)
                    wtitle = buffer.value
                    if title_lower in wtitle.lower():
                        found_hwnd = hwnd
                        return False  # Stop enumeration
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        EnumWindows(EnumWindowsProc(enum_callback), 0)
        
        return json.dumps({"found": found_hwnd is not None, "hwnd": int(found_hwnd) if found_hwnd else None, "search": title})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def activate_window(title: str) -> str:
    """Bring window to foreground - uses ctypes for speed"""
    try:
        import ctypes
        from ctypes import wintypes
        
        EnumWindows = ctypes.windll.user32.EnumWindows
        GetWindowText = ctypes.windll.user32.GetWindowTextW
        IsWindowVisible = ctypes.windll.user32.IsWindowVisible
        GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
        SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow
        
        found_hwnd = None
        title_lower = title.lower()
        
        def enum_callback(hwnd, lparam):
            nonlocal found_hwnd
            if IsWindowVisible(hwnd):
                length = GetWindowTextLength(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    GetWindowText(hwnd, buffer, length + 1)
                    wtitle = buffer.value
                    if title_lower in wtitle.lower():
                        found_hwnd = hwnd
                        return False
            return True
        
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        EnumWindows(EnumWindowsProc(enum_callback), 0)
        
        if found_hwnd:
            SetForegroundWindow(found_hwnd)
            return json.dumps({"success": True, "window": title, "hwnd": int(found_hwnd)})
        
        return json.dumps({"success": False, "error": f"Window not found: {title}"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_screen_size() -> str:
    """Get primary screen dimensions"""
    try:
        import pyautogui
        width, height = pyautogui.size()
        return json.dumps({"width": width, "height": height})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def analyze_screen(task: str = "describe") -> str:
    """Capture screen and prepare for analysis"""
    result = save_screenshot("analysis")
    if result["success"]:
        b64 = get_image_base64(result["path"])
        return json.dumps({
            "success": True,
            "image_path": result["path"],
            "task": task,
            "image_base64": b64[:1000] + "..." if len(b64) > 1000 else b64,
            "note": "Use image_path for full analysis"
        })
    return json.dumps({"success": False, "error": result.get("error")})


@mcp.tool()
def clipboard_read() -> str:
    """Read text from clipboard"""
    try:
        import subprocess
        result = subprocess.run(["powershell", "-Command", "Get-Clipboard"], capture_output=True, text=True)
        return json.dumps({"text": result.stdout.strip()})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def clipboard_write(text: str) -> str:
    """Write text to clipboard"""
    try:
        import subprocess
        subprocess.run(["powershell", "-Command", f'Set-Clipboard -Value "{text.replace(chr(34), chr(34)+chr(34))}"'], capture_output=True)
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def run_powershell(command: str) -> str:
    """Run PowerShell command"""
    try:
        import subprocess
        result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, timeout=30)
        return json.dumps({
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def list_files(directory: str = None, pattern: str = "*") -> str:
    """List files in directory"""
    try:
        dir_path = Path(directory) if directory else Path(APP_DIR)
        files = [str(f) for f in dir_path.glob(pattern) if f.is_file()][:50]
        return json.dumps({"files": files, "count": len(files), "directory": str(dir_path)})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def run_python(code: str) -> str:
    """Execute Python code"""
    try:
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        output = io.StringIO()
        errors = io.StringIO()
        
        exec_globals = {"__name__": "__main__"}
        exec(code, exec_globals)
        
        return json.dumps({"success": True, "output": output.getvalue()})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


# ============ PROMPTS ============

@mcp.prompt()
def session_summary_prompt() -> str:
    return f"""Provide a summary of the current session:
    Session: {CURRENT_SESSION}
    Time: {datetime.now().isoformat()}
    Include: intent, systems touched, changes, milestones/decisions/blockers, next steps.
    Remind operator to persist notes via MCP session_append_event and session_flush_summary before hand-off."""


# ============ FAST EXECUTION TOOLS ============

@mcp.tool()
def exec_fast(code: str) -> str:
    """Execute Python code without file I/O - cached results
    
    Use this instead of writing .py files for quick operations.
    Available globals: redis_get, redis_set, cache, json, sys, time, datetime
    """
    return json.dumps(fast_cache.exec_fast(code), indent=2)


@mcp.tool()
def redis_fast_get(key: str) -> str:
    """Fast Redis get - uses RAM cache first"""
    result = fast_cache.redis_get(key)
    return json.dumps({"key": key, "value": result})


@mcp.tool()
def redis_fast_set(key: str, value: Any, ttl: int = 300) -> str:
    """Fast Redis set - updates both RAM and Redis"""
    fast_cache.redis_set(key, value, ttl)
    return json.dumps({"success": True, "key": key, "ttl": ttl})


@mcp.tool()
def redis_fast_hget(key: str, field: str) -> str:
    """Fast Redis hash get"""
    result = fast_cache.redis_hget(key, field)
    return json.dumps({"key": key, "field": field, "value": result})


@mcp.tool()
def redis_fast_hset(key: str, field: str, value: Any) -> str:
    """Fast Redis hash set"""
    fast_cache.redis_hset(key, field, value)
    return json.dumps({"success": True, "key": key, "field": field})


@mcp.tool()
def get_cached_result(key: str) -> str:
    """Get cached computation result"""
    result = fast_cache.redis_get(f"fast:fn:{key}")
    return json.dumps({"key": key, "cached": result is not None, "value": result})


@mcp.tool()
def cache_result(key: str, value: Any, ttl: int = 60) -> str:
    """Cache a computation result"""
    fast_cache.redis_set(f"fast:fn:{key}", value, ttl)
    return json.dumps({"success": True, "key": key, "ttl": ttl})


@mcp.tool()
def get_session_data() -> str:
    """Get pre-warmed session data - fastest way to get session info"""
    return json.dumps(fast_cache._session_data, indent=2, default=str)


@mcp.tool()
def ping_redis() -> str:
    """Quick Redis health check - cached"""
    cached = fast_cache.redis_get("health:ping")
    if cached:
        return json.dumps({"redis": "ok", "cached": True, "latency_ms": cached.get("latency")})
    
    start = time.time()
    if redis_available:
        try:
            redis_client.ping()
            latency = int((time.time() - start) * 1000)
            fast_cache.redis_set("health:ping", {"redis": "ok", "latency": latency}, ttl=30)
            return json.dumps({"redis": "ok", "latency_ms": latency, "cached": False})
        except:
            pass
    return json.dumps({"redis": "unavailable"})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Akashic Aurora Unified MCP")
    parser.add_argument("--http", action="store_true", help="HTTP transport")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    args = parser.parse_args()
    
    if args.http:
        print(f"MCP Server on HTTP port {args.port}")
        mcp.run(transport="streamable-http", port=args.port)
    else:
        print("MCP Server (stdio transport)")
        mcp.run()
