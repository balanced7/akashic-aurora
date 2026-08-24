"""
Session supervisor — idempotent infra launch + status for MCP agents.

Uses ``stack_manager`` service definitions and dependency closure so launch order
matches the DAG. Does not start ``win-mcp`` (the MCP host process).

Env:
  BREAKTHROUGH_ALLOW_INFRA_START — if ``0``/``false``, ``ensure_infra`` refuses to launch (status-only).
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import redis

from config import (
    SESSION_EVENTS_STREAM,
    SESSION_STATE_FILE,
    get_docker_redis_config,
    get_redis_config,
)

ALLOW_INFRA_ENV = "BREAKTHROUGH_ALLOW_INFRA_START"


def allow_infra_start() -> bool:
    v = os.environ.get(ALLOW_INFRA_ENV, "1").strip().lower()
    return v in ("1", "true", "yes", "on")


def _compressor_running() -> bool:
    try:
        ps_cmd = (
            "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
            "| Where-Object { $_.CommandLine -match 'session_compressor' } "
            "| Measure-Object | Select-Object -ExpandProperty Count"
        )
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=25,
        )
        n = int((p.stdout or "0").strip() or "0")
        return n > 0
    except Exception:
        return False


def _http_ok(url: str, timeout: float = 4.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "session_supervisor/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def _wsl_redis_get(key: str) -> Optional[str]:
    try:
        p = subprocess.run(
            [
                "wsl",
                "-d",
                "Ubuntu-Migrate",
                "-e",
                "bash",
                "-c",
                f"redis-cli -p 6380 GET '{key}' 2>/dev/null",
            ],
            capture_output=True,
            text=True,
            timeout=12,
        )
        out = (p.stdout or "").strip()
        return out if out and out != "(nil)" else None
    except Exception:
        return None


def infra_status() -> Dict[str, Any]:
    """Lightweight health snapshot (no writes)."""
    out: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "allow_infra_start": allow_infra_start(),
        "wsl_redis_6380": False,
        "docker_redis_16379": False,
        "voice_5000": False,
        "compressor_python": _compressor_running(),
        "session_events_stream_length": None,
        "migration_summary_preview": None,
        "learning_decisions_count": None,
    }
    try:
        r = redis.Redis(**get_redis_config())
        r.ping()
        out["wsl_redis_6380"] = True
        out["session_events_stream_length"] = int(r.xlen(SESSION_EVENTS_STREAM))
        try:
            out["learning_decisions_count"] = int(r.zcard("learn:decisions:idx"))
        except Exception:
            pass
    except Exception as e:
        out["wsl_redis_error"] = str(e)

    try:
        rd = redis.Redis(**get_docker_redis_config())
        rd.ping()
        out["docker_redis_16379"] = True
    except Exception:
        out["docker_redis_16379"] = _tcp_open("127.0.0.1", 16379)

    out["voice_5000"] = _http_ok("http://127.0.0.1:5000/health")

    ms = _wsl_redis_get("migration:summary")
    if ms:
        out["migration_summary_preview"] = ms[:280]

    return out


def _service_closure(seed: Set[str]) -> Set[str]:
    from stack_manager.config import SERVICES

    out = set(seed)
    changed = True
    while changed:
        changed = False
        for name in list(out):
            cfg = SERVICES.get(name)
            if not cfg:
                continue
            for dep in cfg.get("depends", []):
                if dep not in out:
                    out.add(dep)
                    changed = True
    return out


def _launch_plan(closed: Set[str]) -> List[List[str]]:
    from stack_manager.dag import resolve_tiers

    skip = {"win-mcp"}
    plan: List[List[str]] = []
    for tier in resolve_tiers():
        batch = sorted((closed - skip) & tier)
        if batch:
            plan.append(batch)
    return plan


def ensure_infra(tier: str, agent: str = "") -> Dict[str, Any]:
    """
    Launch infra subset. ``tier``:
      - minimal — WSL keeper + Redis HA only
      - standard — minimal + Docker Redis mirror + ai-voice stack + session compressor
      - full — same as standard (reserved for future extras)
    """
    from stack_manager.config import SERVICES
    from stack_manager.launcher import launch_service, wait_for_healthy

    tier_l = (tier or "standard").strip().lower()
    report: Dict[str, Any] = {
        "tier_requested": tier_l,
        "agent": (agent or "").strip().lower(),
        "allowed": allow_infra_start(),
        "steps": [],
        "ok": False,
    }

    if not report["allowed"]:
        report["error"] = (
            f"Launch blocked: set {ALLOW_INFRA_ENV}=1 to allow starting services from MCP."
        )
        report["status"] = infra_status()
        return report

    if tier_l == "minimal":
        seed = {"wsl-redis-ha"}
    elif tier_l in ("standard", "full"):
        seed = {"docker-edge-redis", "win-compressor", "win-ai-watchdog", "win-stack-gui"}
    else:
        report["error"] = f"Unknown tier '{tier}'. Use minimal | standard | full."
        return report

    closed = _service_closure(seed)
    plan = _launch_plan(closed)
    report["plan"] = plan
    report["services_closed"] = sorted(closed)

    all_ok = True
    for batch in plan:
        for name in batch:
            cfg = SERVICES[name]
            step = {"service": name, "launch": False, "healthy": False}
            launch_service(name, cfg)
            step["launch"] = True
            ok = wait_for_healthy(name, cfg, routes=None)
            step["healthy"] = ok
            if not ok:
                all_ok = False
            report["steps"].append(step)

    report["ok"] = all_ok
    report["status"] = infra_status()
    return report


def bootstrap_context_snapshot(
    session_id: str = "",
    stream_tail: int = 6,
    decision_titles: int = 5,
) -> Dict[str, Any]:
    """Redis + WSL migration digest for MCP ``breakthrough_bootstrap``."""
    sid_eff = session_id.strip()
    if not sid_eff and SESSION_STATE_FILE.exists():
        try:
            sid_eff = str(
                json.loads(Path(SESSION_STATE_FILE).read_text(encoding="utf-8")).get(
                    "session_id"
                )
                or ""
            )
        except Exception:
            sid_eff = ""

    snap: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "session_id_effective": sid_eff,
        "migration_summary": _wsl_redis_get("migration:summary"),
        "context_wsl_infrastructure": _wsl_redis_get("context:wsl_infrastructure"),
        "recent_stream_events": [],
        "recent_decision_titles": [],
    }

    try:
        r = redis.Redis(**get_redis_config())
        rows = r.xrevrange(SESSION_EVENTS_STREAM, "+", "-", count=max(1, min(stream_tail, 30)))
        for mid, fields in rows:
            snap["recent_stream_events"].append(
                {
                    "id": mid,
                    "session_id": fields.get("session_id"),
                    "agent": fields.get("agent"),
                    "event_type": fields.get("event_type"),
                    "payload_preview": (fields.get("payload") or "")[:200],
                }
            )
    except Exception as e:
        snap["stream_error"] = str(e)

    try:
        r = redis.Redis(**get_redis_config())
        ids = r.zrevrange("learn:decisions:idx", 0, max(0, decision_titles - 1))
        for did in ids:
            raw = r.hget("learn:decisions", did)
            if raw:
                d = json.loads(raw)
                snap["recent_decision_titles"].append(d.get("title", "")[:120])
    except Exception:
        pass

    try:
        from project_context import get_context_manager

        mgr = get_context_manager()
        snap["project_current_task"] = mgr.get_current_task()
        snap["project_milestone_count"] = len(mgr.get_milestones())
    except Exception:
        pass

    return snap
