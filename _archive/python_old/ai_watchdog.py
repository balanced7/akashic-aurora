#!/usr/bin/env python3
"""
AI Watchdog — unified infra observer for BreakThrough Stack.

Combines:
  • Port management — ``stack_manager.Ports.PortManager`` (conflicts, host scan, Redis registry sync)
  • Session logging — canonical ``session:events`` stream + JSONL mirror + legacy ``session:*:log`` hints
  • Launch alignment — optional one-shot ``session_supervisor.ensure_infra`` (gated by env)

Usage:
  python E:\\AI-Setup\\ai_watchdog.py --once [--json]
  python E:\\AI-Setup\\ai_watchdog.py --daemon [--interval 45] [--sync-ports]
  python E:\\AI-Setup\\ai_watchdog.py --once --ensure-infra --tier standard
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

STATE_FILE = ROOT / "blackboard_data" / "ai_watchdog_state.json"
REDIS_CONTEXT_KEY = "context:ai_watchdog_last"
DEFAULT_INTERVAL = float(os.environ.get("AI_WATCHDOG_INTERVAL", "45"))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            timeout=10,
        )
        n = int((p.stdout or "0").strip() or "0")
        return n > 0
    except Exception:
        return False


def _redis_client():
    try:
        import redis
        from config import get_redis_config

        r = redis.Redis(**get_redis_config())
        r.ping()
        return r
    except Exception:
        return None


def _canonical_stream_snapshot(r) -> Dict[str, Any]:
    from config import SESSION_EVENTS_STREAM

    out: Dict[str, Any] = {
        "stream": SESSION_EVENTS_STREAM,
        "reachable": False,
        "xlen": None,
        "last_event": None,
    }
    if r is None:
        return out
    try:
        out["reachable"] = True
        out["xlen"] = int(r.xlen(SESSION_EVENTS_STREAM))
        rows = r.xrevrange(SESSION_EVENTS_STREAM, max="+", min="-", count=1)
        if not rows:
            return out
        _mid, fields = rows[0]
        fd = dict(fields)
        raw_p = fd.get("payload") or "{}"
        try:
            env = json.loads(raw_p)
        except Exception:
            env = {}
        out["last_event"] = {
            "stream_id": str(rows[0][0]),
            "session_id": fd.get("session_id") or env.get("session_id"),
            "agent": fd.get("agent") or env.get("agent"),
            "event_type": fd.get("event_type") or env.get("event_type"),
            "utc_timestamp": env.get("utc_timestamp"),
            "intent_preview": (env.get("intent") or "")[:200],
        }
    except Exception as e:
        out["error"] = str(e)
    return out


def _canonical_jsonl_snapshot() -> Dict[str, Any]:
    from config import CANONICAL_EVENTS_JSONL

    p = CANONICAL_EVENTS_JSONL
    snap = {"path": str(p), "exists": p.exists(), "bytes": None, "last_line_preview": None}
    if p.exists():
        try:
            snap["bytes"] = p.stat().st_size
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                snap["last_line_preview"] = lines[-1][:400]
        except Exception as e:
            snap["error"] = str(e)
    return snap


def _legacy_opencode_log_hints(r) -> Dict[str, Any]:
    """Cheap hint: OpenCode sessions with empty legacy LIST logs."""
    out: Dict[str, Any] = {"scanned_keys": 0, "opencode_empty_logs": []}
    if r is None:
        return out
    empty: list[str] = []
    try:
        n = 0
        for key in r.scan_iter(match="session:*:log", count=80):
            n += 1
            if n > 150:
                break
            ks = key if isinstance(key, str) else key.decode("utf-8", errors="replace")
            parts = ks.split(":")
            sid = parts[1] if len(parts) > 1 else ""
            if "opencode" not in sid.lower():
                continue
            try:
                if int(r.llen(key)) == 0:
                    empty.append(sid)
            except Exception:
                continue
        out["scanned_keys"] = n
        out["opencode_empty_logs"] = empty[:25]
    except Exception as e:
        out["error"] = str(e)
    return out


def _port_section(sync_ports: bool) -> Dict[str, Any]:
    from stack_manager.ports import PortManager
    from stack_manager.config import SERVICES

    pm = PortManager()
    section: Dict[str, Any] = {
        "service_port_map": pm.scan_services(),
        "conflicts": pm.detect_conflicts(),
        "host_ports_declared": pm.scan_host_ports(),
    }
    if sync_ports:
        try:
            pm.sync_to_redis()
            section["redis_registry_sync"] = "ok"
        except Exception as e:
            section["redis_registry_sync"] = f"err:{e}"
    else:
        section["redis_registry_sync"] = "skipped"
    section["conflict_count"] = len(section["conflicts"])
    return section


def collect_report(
    *,
    sync_ports: bool = True,
    ensure_infra: bool = False,
    infra_tier: str = "standard",
    infra_agent: str = "ai_watchdog",
) -> Dict[str, Any]:
    """Single observability payload (ports + logging + infra)."""
    from session_supervisor import allow_infra_start, ensure_infra, infra_status

    report: Dict[str, Any] = {
        "timestamp": _utc_now_iso(),
        "compressor_process": _compressor_running(),
        "infra_status": infra_status(),
        "ports": _port_section(sync_ports),
        "logging": {},
        "ensure_infra": None,
    }

    r = _redis_client()
    report["logging"]["canonical_stream"] = _canonical_stream_snapshot(r)
    report["logging"]["canonical_jsonl"] = _canonical_jsonl_snapshot()
    report["logging"]["legacy_opencode_hints"] = _legacy_opencode_log_hints(r)

    if r is not None:
        try:
            r.close()
        except Exception:
            pass

    if ensure_infra:
        if allow_infra_start():
            report["ensure_infra"] = ensure_infra(infra_tier.strip().lower(), infra_agent)
        else:
            report["ensure_infra"] = {
                "ok": False,
                "skipped": True,
                "reason": "BREAKTHROUGH_ALLOW_INFRA_START disables auto-launch",
            }

    report["summary"] = {
        "wsl_redis_ok": bool(report["infra_status"].get("wsl_redis_6380")),
        "docker_mirror_ok": bool(report["infra_status"].get("docker_redis_16379")),
        "port_conflicts": report["ports"]["conflict_count"],
        "compressor_running": report["compressor_process"],
        "session_events_xlen": (report["logging"]["canonical_stream"] or {}).get("xlen"),
    }
    return report


def _persist(report: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    r = _redis_client()
    if r is None:
        return
    try:
        r.set(REDIS_CONTEXT_KEY, json.dumps(report, default=str))
    except Exception:
        pass
    finally:
        try:
            r.close()
        except Exception:
            pass


def run_daemon(interval: float, sync_ports: bool, ensure_on_start: bool) -> None:
    stop = False

    def _sig(*_a):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    if ensure_on_start:
        collect_report(sync_ports=sync_ports, ensure_infra=True)

    while not stop:
        rep = collect_report(sync_ports=sync_ports, ensure_infra=False)
        _persist(rep)
        if not sync_ports:
            print(f"[ai_watchdog] {_utc_now_iso()} summary={rep.get('summary')}", flush=True)
        else:
            print(
                f"[ai_watchdog] {_utc_now_iso()} conflicts={rep['ports']['conflict_count']} "
                f"events_xlen={rep['summary'].get('session_events_xlen')}",
                flush=True,
            )
        t0 = time.time()
        while time.time() - t0 < interval and not stop:
            time.sleep(min(1.0, interval))


def main() -> int:
    ap = argparse.ArgumentParser(description="AI Watchdog — ports, logging, infra snapshot")
    ap.add_argument("--once", action="store_true", help="Single collect + exit")
    ap.add_argument("--daemon", action="store_true", help="Loop forever")
    ap.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="Daemon poll seconds")
    ap.add_argument("--json", action="store_true", help="Stdout JSON (--once)")
    ap.add_argument("--no-sync-ports", action="store_true", help="Skip PortManager.sync_to_redis")
    ap.add_argument("--ensure-infra", action="store_true", help="Run session_supervisor.ensure_infra once")
    ap.add_argument("--tier", default="standard", help="ensure_infra tier: minimal|standard|full")
    ap.add_argument(
        "--ensure-on-start",
        action="store_true",
        help="With --daemon: run ensure_infra once before loop",
    )
    args = ap.parse_args()

    sync_ports = not args.no_sync_ports

    if args.daemon:
        run_daemon(args.interval, sync_ports, args.ensure_on_start)
        return 0

    rep = collect_report(
        sync_ports=sync_ports,
        ensure_infra=args.ensure_infra,
        infra_tier=args.tier,
    )
    _persist(rep)

    if args.json:
        print(json.dumps(rep, indent=2, default=str))
    else:
        print(json.dumps(rep["summary"], indent=2, default=str))
        if rep["ports"]["conflicts"]:
            print("PORT CONFLICTS:")
            for c in rep["ports"]["conflicts"]:
                print(" ", c)
    return 1 if rep["ports"]["conflict_count"] else 0


if __name__ == "__main__":
    sys.exit(main())
