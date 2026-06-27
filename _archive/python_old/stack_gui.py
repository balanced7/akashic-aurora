#!/usr/bin/env python3
"""
Stack GUI — Web Dashboard for BreakThrough Stack Manager
=========================================================
Modular panel architecture. Each panel is an isolated subsystem
that can fail independently without breaking the whole UI.

Panels:
  Home (/)     — Razer-styled AI console: chat, drag-drop files, mic + realtime speech option
  Dashboard    — Overview: all services, resource gauges, quick actions (/dashboard)
  Launcher     — Start/stop/restart services with dependency visualization
  Metrics      — Real-time memory/CPU charts, health history via Redis
  Troubleshoot — Log viewer, health check runner, dependency graph
  Moderation   — Manual controls, config overrides, maintenance mode

Architecture:
  stack_manager.py  ← Core library (PortManager, RoutingTable,
                       ResourceTracker, MemoryMonitor, health checks)
  stack_gui.py      ← FastAPI web server (reads from stack_manager)

Usage:
  python stack_gui.py                 # Start GUI on http://localhost:8090
  python stack_gui.py --port 9000     # Custom port
  python stack_gui.py --no-browser    # Don't open browser
"""

import os
import sys
import json
import time
import threading
import base64
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for Unicode box-drawing chars
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

_BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(_BASE))

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from stack_manager import (
    SERVICES, resolve_tiers, check_health, launch_service, wait_for_healthy,
    PortManager, RoutingTable, ResourceTracker, MemoryMonitor,
    _run_wsl, _run_ps, _run_cmd, c, log,
)

# ──────────────────────────────────────────────────────────────
# FASTAPI APP
# ──────────────────────────────────────────────────────────────

VOICE_BASE_URL = os.environ.get("AI_VOICE_URL", "http://127.0.0.1:5000").rstrip("/")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

app = FastAPI(
    title="BreakThrough Stack Manager",
    version="1.0.0",
    docs_url="/api/docs",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Instantiate subsystems (each is self-contained, failures isolated)
ports_mgr = PortManager()
routes_tbl = RoutingTable()
resource_tkr = ResourceTracker()
memory_mon = MemoryMonitor()


# ──────────────────────────────────────────────────────────────
# ERROR-SAFE WRAPPER — prevents one failing subsystem from
# taking down the whole API response
# ──────────────────────────────────────────────────────────────

def safe_call(func, default=None):
    """Wrap a subsystem call; returns default on failure."""
    try:
        result = func()
        return result if result is not None else default
    except Exception as e:
        return {"error": str(e), "available": False}


# ══════════════════════════════════════════════════════════════
# PANEL 1: DASHBOARD — overview, quick status, resource gauges
# ══════════════════════════════════════════════════════════════

@app.get("/api/dashboard")
async def api_dashboard():
    """Aggregated overview for the dashboard panel."""
    services_status = {}
    for name, cfg in SERVICES.items():
        services_status[name] = {
            "description": cfg["description"],
            "runtime": cfg["runtime"],
            "healthy": safe_call(lambda n=name, c=cfg: check_health(n, c), default=False),
            "depends": cfg.get("depends", []),
            "ports": cfg.get("ports", []),
            "tier": _get_tier(name),
        }

    return {
        "timestamp": datetime.now().isoformat(),
        "services": services_status,
        "summary": {
            "total": len(services_status),
            "healthy": sum(1 for s in services_status.values() if s["healthy"]),
            "down": sum(1 for s in services_status.values() if not s["healthy"]),
        },
        "resources": safe_call(resource_tkr.system_info, default={}),
        "ports": safe_call(lambda: ports_mgr.scan_host_ports(), default={}),
    }


def _get_tier(name: str) -> int:
    tiers = resolve_tiers()
    for i, tier in enumerate(tiers):
        if name in tier:
            return i
    return -1


# ══════════════════════════════════════════════════════════════
# PANEL 2: LAUNCHER — start/stop/restart, dependency viz
# ══════════════════════════════════════════════════════════════

@app.get("/api/launcher/tiers")
async def api_launcher_tiers():
    """Get the DAG tier structure for visualization."""
    tiers = resolve_tiers()
    return {
        "tiers": [
            {
                "index": i,
                "services": sorted(tier),
                "details": {
                    name: {
                        "depends": SERVICES[name].get("depends", []),
                        "healthy": safe_call(lambda n=name, c=SERVICES[name]: check_health(n, c), default=None),
                        "description": SERVICES[name]["description"],
                    }
                    for name in sorted(tier)
                },
            }
            for i, tier in enumerate(tiers)
        ]
    }


@app.post("/api/launcher/start/{name}")
async def api_start_service(name: str):
    """Start a single service."""
    if name not in SERVICES:
        raise HTTPException(404, f"Unknown service: {name}")
    cfg = SERVICES[name]
    success = launch_service(name, cfg)
    healthy = False
    if success:
        healthy = wait_for_healthy(name, cfg, routes_tbl)
    return {"service": name, "launched": success, "healthy": healthy}


@app.post("/api/launcher/stop/{name}")
async def api_stop_service(name: str):
    """Stop a single service."""
    if name not in SERVICES:
        raise HTTPException(404, f"Unknown service: {name}")
    cfg = SERVICES[name]
    stop_cmd = cfg.get("stop", "")
    if not stop_cmd:
        return {"service": name, "stopped": False, "reason": "No stop command defined"}
    runtime = cfg.get("runtime", "")
    try:
        if runtime == "wsl":
            _, ok = _run_wsl(stop_cmd, timeout=10)
        else:
            _, ok = _run_ps(stop_cmd, timeout=10)
        routes_tbl.update_status(name, "stopped")
        return {"service": name, "stopped": ok}
    except Exception as e:
        return {"service": name, "stopped": False, "error": str(e)}


@app.post("/api/launcher/restart/{name}")
async def api_restart_service(name: str):
    """Restart a single service."""
    if name not in SERVICES:
        raise HTTPException(404, f"Unknown service: {name}")
    cfg = SERVICES[name]
    stop_cmd = cfg.get("stop", "")
    if stop_cmd:
        runtime = cfg.get("runtime", "")
        if runtime == "wsl":
            _run_wsl(stop_cmd, timeout=10)
        else:
            _run_ps(stop_cmd, timeout=10)
        time.sleep(1)
    routes_tbl.update_status(name, "restarting")
    launch_service(name, cfg)
    healthy = wait_for_healthy(name, cfg, routes_tbl)
    return {"service": name, "healthy": healthy}


@app.post("/api/launcher/start-all")
async def api_start_all():
    """Launch all services tier by tier."""
    tiers = resolve_tiers()
    results = {}
    for tier in tiers:
        for name in tier:
            cfg = SERVICES[name]
            launch_service(name, cfg)
            healthy = wait_for_healthy(name, cfg, routes_tbl)
            results[name] = healthy
            if cfg.get("endpoint"):
                ep = cfg["endpoint"]
                routes_tbl.register(name, ep.get("host", "127.0.0.1"), ep.get("port", 0), ep.get("protocol", "tcp"), status="healthy" if healthy else "failed")
    ports_mgr.sync_to_redis()
    return {"results": results}


# ══════════════════════════════════════════════════════════════
# PANEL 3: METRICS — memory, CPU, health history
# ══════════════════════════════════════════════════════════════

@app.get("/api/metrics/memory")
async def api_metrics_memory():
    """Per-service memory snapshot."""
    samples = safe_call(lambda: memory_mon.sample(), default={})
    return {
        "timestamp": datetime.now().isoformat(),
        "services": {
            name: {
                "rss_mb": mem.get("rss_mb", 0),
                "vms_mb": mem.get("vms_mb", 0),
                "cpu_pct": mem.get("cpu_pct", 0),
                "limit_mb": SERVICES.get(name, {}).get("memory_limit_mb"),
            }
            for name, mem in samples.items()
        },
    }


@app.get("/api/metrics/history")
async def api_metrics_history(service: str = None, limit: int = 20):
    """Historical memory snapshots from Redis or in-memory."""
    try:
        r = _redis()
        if not r:
            return {"available": False, "error": "Redis not connected"}

        names = [service] if service else list(SERVICES.keys())
        history = {}
        for name in names:
            if not name:
                continue
            data = r.hgetall(f"service:{name}:memory")
            if data:
                history[name] = {
                    "rss_mb": float(data.get("rss_mb", 0)),
                    "vms_mb": float(data.get("vms_mb", 0)),
                    "cpu_pct": float(data.get("cpu_pct", 0)),
                    "timestamp": data.get("timestamp", ""),
                }
        return {"available": True, "history": history}
    except Exception as e:
        return {"available": False, "error": str(e)}


@app.get("/api/metrics/resources")
async def api_metrics_resources():
    """System resource overview."""
    return safe_call(resource_tkr.system_info, default={})


# ══════════════════════════════════════════════════════════════
# PANEL 4: TROUBLESHOOT — logs, health runner, dep graph
# ══════════════════════════════════════════════════════════════

@app.get("/api/troubleshoot/logs/{name}")
async def api_troubleshoot_logs(name: str, lines: int = 30):
    """Get recent logs for a service."""
    log_paths = {
        "wsl-redis-master": "/var/log/redis/master.log",
        "wsl-redis-replica1": "/var/log/redis/replica1.log",
        "wsl-redis-replica2": "/var/log/redis/replica2.log",
        "wsl-sentinel1": "/var/log/redis/sentinel1.log",
        "wsl-sentinel2": "/var/log/redis/sentinel2.log",
        "wsl-sentinel3": "/var/log/redis/sentinel3.log",
        "gemma-2b": "/tmp/gemma.log",
    }
    path = log_paths.get(name)
    if not path:
        return {"available": False, "error": f"No log path defined for {name}"}

    out, ok = _run_wsl(f"tail -{lines} {path} 2>/dev/null || echo 'Log not found'", timeout=10)
    return {"available": ok, "service": name, "log": out.split("\n") if out else []}


@app.get("/api/troubleshoot/health-check/{name}")
async def api_troubleshoot_health_check(name: str):
    """Run an on-demand health check for a service."""
    if name == "all":
        results = {}
        for n, cfg in SERVICES.items():
            results[n] = safe_call(lambda n=n, c=cfg: check_health(n, c), default=None)
        return {"results": results}

    if name not in SERVICES:
        raise HTTPException(404, f"Unknown service: {name}")
    healthy = check_health(name, SERVICES[name])
    return {"service": name, "healthy": healthy}


@app.get("/api/troubleshoot/dependency-graph")
async def api_troubleshoot_dep_graph():
    """Return dependency graph data for visualization."""
    tiers = resolve_tiers()
    nodes = []
    edges = []
    for name, cfg in SERVICES.items():
        healthy = safe_call(lambda n=name, c=cfg: check_health(n, c), default=False)
        nodes.append({
            "id": name,
            "label": name,
            "description": cfg["description"],
            "healthy": healthy,
            "tier": _get_tier(name),
            "ports": cfg.get("ports", []),
        })
        for dep in cfg.get("depends", []):
            edges.append({"from": dep, "to": name})

    return {"nodes": nodes, "edges": edges, "tiers": [sorted(t) for t in tiers]}


# ══════════════════════════════════════════════════════════════
# PANEL 5: MODERATION — manual controls, overrides, maintenance
# ══════════════════════════════════════════════════════════════

@app.get("/api/moderation/config")
async def api_moderation_config():
    """Get current service configurations (safe for display)."""
    safe_config = {}
    for name, cfg in SERVICES.items():
        safe_config[name] = {
            "description": cfg["description"],
            "runtime": cfg["runtime"],
            "depends": cfg.get("depends", []),
            "ports": cfg.get("ports", []),
            "resources": cfg.get("resources", {}),
            "memory_limit_mb": cfg.get("memory_limit_mb"),
            "startup_timeout": cfg.get("startup_timeout"),
            "has_stop": bool(cfg.get("stop")),
            "has_endpoint": bool(cfg.get("endpoint")),
        }
    return safe_config


@app.post("/api/moderation/maintenance/{name}")
async def api_maintenance_mode(name: str, enable: bool = True):
    """Enable/disable maintenance mode for a service (prevents auto-restart)."""
    # Store in Redis for the monitor to check
    try:
        r = _redis()
        if r:
            r.set(f"service:{name}:maintenance", "1" if enable else "0")
            return {"service": name, "maintenance": enable}
        return {"error": "Redis not available"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/moderation/status")
async def api_moderation_status():
    """Get moderation state for all services."""
    try:
        r = _redis()
        if r:
            status = {}
            for name in SERVICES:
                status[name] = {
                    "maintenance": r.get(f"service:{name}:maintenance") == "1",
                    "restart_count": int(r.get(f"service:{name}:restart_count") or 0),
                }
            return status
        return {"error": "Redis not available"}
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════
# REDIS HELPER (lazy)
# ══════════════════════════════════════════════════════════════

_redis_conn = None

def _redis():
    global _redis_conn
    if _redis_conn is not None:
        try:
            _redis_conn.ping()
            return _redis_conn
        except Exception:
            _redis_conn = None
    try:
        import redis as redis_lib
        from config import get_redis_config

        r = redis_lib.Redis(**get_redis_config())
        r.ping()
        _redis_conn = r
        return r
    except Exception:
        return None


def _load_chat_home_html() -> str:
    p = _BASE / "templates" / "stack_chat_home.html"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return (
        "<!DOCTYPE html><html><body style='background:#111;color:#888;font-family:sans-serif;"
        "padding:2rem'><p>Missing <code>templates/stack_chat_home.html</code></p></body></html>"
    )


def _http_post_json(url: str, payload: dict, timeout: float = 120.0):
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw), None
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = str(e)
        return None, err_body
    except Exception as e:
        return None, str(e)


def _http_post_form(url: str, fields: dict, timeout: float = 120.0):
    try:
        import urllib.parse

        body = urllib.parse.urlencode(fields).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw), None
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_body = str(e)
        return None, err_body
    except Exception as e:
        return None, str(e)


@app.post("/api/ai/chat")
async def api_ai_chat(request: Request):
    """
    Proxy to ai-voice (:5000) then Ollama (:11434). Attachments: base64 + filename from browser.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Expected JSON body")

    msg = (body.get("message") or "").strip()
    model = (body.get("model") or "gemma2:2b").strip()
    att = body.get("attachments") or []

    extra_parts = []
    for a in att:
        fn = str(a.get("filename") or "file")
        mime = str(a.get("mime") or "")
        b64 = a.get("data_b64") or ""
        textish = mime.startswith("text/") or fn.lower().endswith(
            (".txt", ".md", ".py", ".json", ".yaml", ".yml", ".toml", ".csv", ".log", ".ini", ".cfg")
        )
        try:
            raw = base64.b64decode(b64) if b64 else b""
        except Exception:
            raw = b""
        if textish:
            try:
                extra_parts.append(f"\n\n--- file:{fn} ---\n" + raw.decode("utf-8", errors="replace")[:80000])
            except Exception:
                extra_parts.append(f"\n\n--- file:{fn} (decode error) ---\n")
        else:
            extra_parts.append(f"\n\n--- file:{fn} ({mime or 'binary'}) omitted from prompt; describe if needed. ---\n")

    full_prompt = (msg + "".join(extra_parts)).strip()
    if not full_prompt:
        raise HTTPException(400, "Empty message and no usable attachment text")

    reply = ""
    backend = None

    data, err = _http_post_json(
        f"{VOICE_BASE_URL}/api/chat",
        {"prompt": full_prompt, "model": model},
        timeout=120.0,
    )
    if data:
        reply = str(data.get("response") or data.get("reply") or data.get("text") or "").strip()
        if reply:
            backend = "ai-voice-json"

    if not reply:
        data2, _ = _http_post_form(f"{VOICE_BASE_URL}/chat", {"message": full_prompt}, timeout=120.0)
        if data2:
            reply = str(data2.get("response") or "").strip()
            if reply:
                backend = "ai-voice-form"

    if not reply:
        ollama_body = {
            "model": model,
            "messages": [{"role": "user", "content": full_prompt}],
            "stream": False,
        }
        data3, err3 = _http_post_json(f"{OLLAMA_BASE_URL}/api/chat", ollama_body, timeout=120.0)
        if data3:
            msg_obj = data3.get("message") or {}
            reply = str(msg_obj.get("content") or data3.get("response") or "").strip()
            if reply:
                backend = "ollama"
        if not reply and err3:
            raise HTTPException(502, detail=f"No LLM reachable: voice_err={err!s}; ollama_err={err3!s}")

    if not reply:
        raise HTTPException(502, detail="Empty reply from backends")

    return {"reply": reply, "backend": backend}


# ══════════════════════════════════════════════════════════════
# HTML DASHBOARD — single-file, vanilla JS, modular panels
# ══════════════════════════════════════════════════════════════

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BreakThrough Stack Manager</title>
<style>
:root {
  --bg: #0d1117;
  --surface: #161b22;
  --border: #30363d;
  --text: #c9d1d9;
  --dim: #8b949e;
  --green: #3fb950;
  --red: #f85149;
  --yellow: #d2991d;
  --blue: #58a6ff;
  --purple: #bc8cff;
  --cyan: #39d2c0;
  --radius: 6px;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font:14px/1.5 'Segoe UI',system-ui,sans-serif; }
header {
  background:var(--surface); border-bottom:1px solid var(--border);
  padding:12px 24px; display:flex; align-items:center; gap:16px;
}
header h1 { font-size:18px; color:var(--cyan); }
nav { display:flex; gap:8px; }
nav button {
  background:transparent; border:1px solid var(--border); color:var(--dim);
  padding:6px 14px; border-radius:var(--radius); cursor:pointer; font-size:13px;
}
nav button:hover, nav button.active { color:var(--text); border-color:var(--dim); }
nav button.active { background:var(--border); }
.tab { display:none; padding:20px 24px; }
.tab.active { display:block; }
.card {
  background:var(--surface); border:1px solid var(--border);
  border-radius:var(--radius); padding:16px; margin-bottom:16px;
}
.card h3 { font-size:14px; color:var(--blue); margin-bottom:12px; }
.status-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }
.status-dot.up { background:var(--green); }
.status-dot.down { background:var(--red); }
.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
.grid-3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; }
table { width:100%; border-collapse:collapse; }
th, td { text-align:left; padding:6px 10px; border-bottom:1px solid var(--border); font-size:13px; }
th { color:var(--dim); font-weight:600; }
.service-row:hover { background:rgba(88,166,255,0.05); }
.btn {
  background:var(--surface); border:1px solid var(--border); color:var(--text);
  padding:4px 10px; border-radius:4px; cursor:pointer; font-size:12px; margin-right:4px;
}
.btn:hover { border-color:var(--dim); }
.btn.start { border-color:var(--green); color:var(--green); }
.btn.stop { border-color:var(--red); color:var(--red); }
.btn.restart { border-color:var(--yellow); color:var(--yellow); }
.btn.start-all { border-color:var(--cyan); color:var(--cyan); }
.gauge-bar { height:8px; background:var(--border); border-radius:4px; overflow:hidden; margin:4px 0; }
.gauge-fill { height:100%; border-radius:4px; transition:width .5s; }
.gauge-fill.good { background:var(--green); }
.gauge-fill.warn { background:var(--yellow); }
.gauge-fill.bad { background:var(--red); }
.tier-badge { display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; margin-left:8px; }
.tier-0 { background:rgba(57,210,192,0.15); color:var(--cyan); }
.tier-1 { background:rgba(88,166,255,0.15); color:var(--blue); }
.tier-2 { background:rgba(188,140,255,0.15); color:var(--purple); }
.tier-3 { background:rgba(210,153,29,0.15); color:var(--yellow); }
.tier-4 { background:rgba(139,148,158,0.15); color:var(--dim); }
.graph-box { height:200px; background:var(--bg); border-radius:var(--radius);
  display:flex; align-items:center; justify-content:center; color:var(--dim); }
.log-view { background:var(--bg); border-radius:var(--radius); padding:12px;
  font-family:'Cascadia Code',monospace; font-size:12px; max-height:400px; overflow-y:auto;
  white-space:pre-wrap; color:var(--dim); }
.summary-bar { display:flex; gap:24px; margin-bottom:20px; }
.summary-item { text-align:center; }
.summary-item .num { font-size:28px; font-weight:700; }
.summary-item .label { font-size:11px; color:var(--dim); }
</style>
</head>
<body>

<header>
  <h1>&#9883; BreakThrough Stack</h1>
  <nav>
    <a href="/" style="color:var(--dim);text-decoration:none;padding:6px 14px;border:1px solid var(--border);border-radius:var(--radius);font-size:13px;margin-right:8px;">AI Console</a>
    <button class="active" data-tab="dashboard">Dashboard</button>
    <button data-tab="launcher">Launcher</button>
    <button data-tab="metrics">Metrics</button>
    <button data-tab="troubleshoot">Troubleshoot</button>
    <button data-tab="moderation">Moderation</button>
  </nav>
  <span id="clock" style="margin-left:auto;color:var(--dim);font-size:12px;"></span>
</header>

<!-- ═══ DASHBOARD TAB ═══ -->
<div class="tab active" id="tab-dashboard">
  <div class="summary-bar" id="summary-bar"></div>
  <div class="grid-2">
    <div class="card">
      <h3>Services</h3>
      <table id="dashboard-services"></table>
    </div>
    <div class="card">
      <h3>System Resources</h3>
      <div id="dashboard-resources"></div>
    </div>
  </div>
  <div class="card"><h3>Dependency Tiers</h3><div id="dashboard-tiers"></div></div>
</div>

<!-- ═══ LAUNCHER TAB ═══ -->
<div class="tab" id="tab-launcher">
  <div class="card">
    <h3>Launch Control</h3>
    <div style="margin-bottom:12px">
      <button class="btn start-all" onclick="apiPost('/api/launcher/start-all').then(r=>refreshAll())">&#9654; Start All</button>
    </div>
    <div id="launcher-tiers"></div>
  </div>
</div>

<!-- ═══ METRICS TAB ═══ -->
<div class="tab" id="tab-metrics">
  <div class="card"><h3>Memory Usage</h3><div id="metrics-memory"></div></div>
  <div class="card"><h3>System Resources</h3><div id="metrics-resources"></div></div>
  <div class="card"><h3>Port Map</h3><table id="metrics-ports"></table></div>
</div>

<!-- ═══ TROUBLESHOOT TAB ═══ -->
<div class="tab" id="tab-troubleshoot">
  <div class="card">
    <h3>On-Demand Health Check</h3>
    <div style="margin-bottom:8px">
      <button class="btn" onclick="runHealthCheck()">Run All Checks</button>
    </div>
    <table id="troubleshoot-health"></table>
  </div>
  <div class="card">
    <h3>Log Viewer</h3>
    <select id="log-selector" onchange="loadLogs()">
      <option value="">Select service...</option>
    </select>
    <button class="btn" onclick="loadLogs()">Load</button>
    <div class="log-view" id="log-viewer">Select a service to view logs...</div>
  </div>
  <div class="card">
    <h3>Dependency Graph</h3>
    <div class="graph-box" id="dep-graph">Loading graph data...</div>
  </div>
</div>

<!-- ═══ MODERATION TAB ═══ -->
<div class="tab" id="tab-moderation">
  <div class="card"><h3>Service Configuration</h3><div id="moderation-config"></div></div>
  <div class="card"><h3>Maintenance Mode</h3><div id="moderation-maintenance"></div></div>
</div>

<script>
// ─── Tab switching ───
document.querySelectorAll('nav button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    refreshTab(btn.dataset.tab);
  });
});

// ─── Clock ───
setInterval(() => { document.getElementById('clock').textContent = new Date().toLocaleTimeString(); }, 1000);

// ─── API helpers ───
async function apiGet(path) {
  try { const r = await fetch(path); return r.ok ? r.json() : {error: r.status}; }
  catch(e) { return {error: e.message}; }
}
async function apiPost(path, body) {
  try { const r = await fetch(path, {method:'POST',body:body?JSON.stringify(body):null,headers:{'Content-Type':'application/json'}}); return r.ok ? r.json() : {error: r.status}; }
  catch(e) { return {error: e.message}; }
}

// ─── Refresh ───
function refreshAll() {
  refreshTab('dashboard');
  refreshTab('launcher');
  refreshTab('metrics');
  refreshTab('troubleshoot');
  refreshTab('moderation');
}
async function refreshTab(tab) {
  switch(tab) {
    case 'dashboard': await loadDashboard(); break;
    case 'launcher': await loadLauncher(); break;
    case 'metrics': await loadMetrics(); break;
    case 'troubleshoot': await loadTroubleshoot(); break;
    case 'moderation': await loadModeration(); break;
  }
}

// ═══ DASHBOARD ═══
async function loadDashboard() {
  const data = await apiGet('/api/dashboard');
  if (data.error) return;

  const s = data.summary;
  document.getElementById('summary-bar').innerHTML =
    `<div class="summary-item"><div class="num" style="color:var(--cyan)">${s.total}</div><div class="label">Total</div></div>
     <div class="summary-item"><div class="num" style="color:var(--green)">${s.healthy}</div><div class="label">Healthy</div></div>
     <div class="summary-item"><div class="num" style="color:var(--red)">${s.down}</div><div class="label">Down</div></div>`;

  let svcHtml = '<tr><th>Service</th><th>Status</th><th>Tier</th></tr>';
  for (const [name, info] of Object.entries(data.services)) {
    const dot = info.healthy ? '<span class="status-dot up"></span>' : '<span class="status-dot down"></span>';
    const status = info.healthy ? 'Healthy' : 'Down';
    svcHtml += `<tr class="service-row"><td>${dot}${name}</td><td>${status}</td><td><span class="tier-badge tier-${info.tier}">T${info.tier}</span></td></tr>`;
  }
  document.getElementById('dashboard-services').innerHTML = svcHtml;
}

// ═══ LAUNCHER ═══
async function loadLauncher() {
  const data = await apiGet('/api/launcher/tiers');
  if (data.error) return;
  let html = '';
  for (const tier of data.tiers) {
    html += `<h4>Tier ${tier.index}</h4>`;
    for (const [name, info] of Object.entries(tier.details)) {
      const dot = info.healthy ? '<span class="status-dot up"></span>' : '<span class="status-dot down"></span>';
      html += `<div style="display:flex;align-items:center;gap:8px;padding:4px 0">
        ${dot} <strong>${name}</strong> <span style="color:var(--dim);font-size:12px">${info.description}</span>
        <span style="flex:1"></span>
        <button class="btn start" onclick="apiPost('/api/launcher/start/${name}').then(r=>loadLauncher())">Start</button>
        <button class="btn stop" onclick="apiPost('/api/launcher/stop/${name}').then(r=>loadLauncher())">Stop</button>
        <button class="btn restart" onclick="apiPost('/api/launcher/restart/${name}').then(r=>loadLauncher())">Restart</button>
      </div>`;
    }
    html += '<br>';
  }
  document.getElementById('launcher-tiers').innerHTML = html;
}

// ═══ METRICS ═══
async function loadMetrics() {
  const mem = await apiGet('/api/metrics/memory');
  if (mem.services) {
    let html = '<table><tr><th>Service</th><th>RSS</th><th>CPU%</th><th>Limit</th></tr>';
    for (const [name, m] of Object.entries(mem.services)) {
      const alert = m.limit_mb && m.rss_mb > m.limit_mb ? 'color:var(--red)' : '';
      html += `<tr><td>${name}</td><td style="${alert}">${m.rss_mb} MB</td><td>${m.cpu_pct}%</td><td>${m.limit_mb||'-'} MB</td></tr>`;
    }
    html += '</table>';
    document.getElementById('metrics-memory').innerHTML = html;
  }

  const ports = await apiGet('/api/dashboard');
  if (ports.ports) {
    let ph = '<tr><th>Port</th><th>Status</th></tr>';
    for (const [port, status] of Object.entries(ports.ports)) {
      ph += `<tr><td>${port}</td><td style="color:${status==='IN USE'?'var(--green)':'var(--dim)'}">${status}</td></tr>`;
    }
    document.getElementById('metrics-ports').innerHTML = ph;
  }
}

// ═══ TROUBLESHOOT ═══
async function loadTroubleshoot() {
  const sel = document.getElementById('log-selector');
  if (!sel.options.length) {
    const dash = await apiGet('/api/dashboard');
    if (dash.services) {
      sel.innerHTML = '<option value="">Select service...</option>' +
        Object.keys(dash.services).map(n => `<option value="${n}">${n}</option>`).join('');
    }
  }
  const graph = await apiGet('/api/troubleshoot/dependency-graph');
  if (graph.nodes) {
    let ghtml = '';
    for (const tier of graph.tiers) {
      ghtml += `<strong>Tier ${graph.tiers.indexOf(tier)}:</strong> ${tier.join(' → ')}<br>`;
    }
    document.getElementById('dep-graph').innerHTML = ghtml;
  }
}

async function runHealthCheck() {
  const data = await apiGet('/api/troubleshoot/health-check/all');
  let html = '<tr><th>Service</th><th>Status</th></tr>';
  for (const [name, healthy] of Object.entries(data.results)) {
    const dot = healthy ? '<span class="status-dot up"></span>' : '<span class="status-dot down"></span>';
    html += `<tr><td>${dot}${name}</td><td>${healthy===null?'error':healthy?'Healthy':'Down'}</td></tr>`;
  }
  document.getElementById('troubleshoot-health').innerHTML = html;
}

async function loadLogs() {
  const name = document.getElementById('log-selector').value;
  if (!name) return;
  const data = await apiGet(`/api/troubleshoot/logs/${name}`);
  document.getElementById('log-viewer').textContent =
    data.available ? (data.log||[]).join('\n') : data.error;
}

// ═══ MODERATION ═══
async function loadModeration() {
  const cfg = await apiGet('/api/moderation/config');
  if (cfg && !cfg.error) {
    let html = '<table><tr><th>Service</th><th>Runtime</th><th>Ports</th><th>Memory Limit</th><th>Timeout</th></tr>';
    for (const [name, c] of Object.entries(cfg)) {
      html += `<tr><td>${name}</td><td>${c.runtime}</td><td>${(c.ports||[]).join(',')||'-'}</td><td>${c.memory_limit_mb||'-'} MB</td><td>${c.startup_timeout}s</td></tr>`;
    }
    html += '</table>';
    document.getElementById('moderation-config').innerHTML = html;
  }

  const status = await apiGet('/api/moderation/status');
  if (status && !status.error) {
    let html = '<table><tr><th>Service</th><th>Maintenance</th><th>Action</th></tr>';
    for (const [name, s] of Object.entries(status)) {
      html += `<tr><td>${name}</td><td>${s.maintenance?'ON':'off'}</td>
        <td><button class="btn" onclick="apiPost('/api/moderation/maintenance/${name}?enable=${!s.maintenance}').then(r=>loadModeration())">
        ${s.maintenance?'Disable':'Enable'}</button></td></tr>`;
    }
    html += '</table>';
    document.getElementById('moderation-maintenance').innerHTML = html;
  }
}

// ─── Auto-refresh dashboard on load ───
loadDashboard();
setInterval(refreshAll, 10000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def serve_chat_home():
    """Razer-styled AI console (text, files, mic)."""
    return HTMLResponse(content=_load_chat_home_html())


@app.get("/dashboard", response_class=HTMLResponse)
async def serve_stack_dashboard():
    """Stack Manager panels (services, launcher, metrics, …)."""
    return HTMLResponse(content=DASHBOARD_HTML)


# ──────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Stack Manager GUI Server")
    parser.add_argument("--port", type=int, default=8090, help="Server port (default: 8090)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    print()
    print("  " + "=" * 48)
    print(f"  AI Console -> http://{args.host}:{args.port}/")
    print(f"  Stack Status -> http://{args.host}:{args.port}/dashboard")
    print("  " + "=" * 48)
    print(f"  Stack panels: Dashboard | Launcher | Metrics | Troubleshoot | Moderation")
    print(f"  API docs: http://{args.host}:{args.port}/api/docs")
    print()

    if not args.no_browser:
        import webbrowser
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{args.host}:{args.port}")).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
