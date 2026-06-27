"""
CLI — Command-line interface for stack_manager.
Commands: start stop status ps recover kill restart monitor
"""

import os, sys, time, subprocess, psutil
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from .config import SERVICES
from .dag import resolve_tiers
from .health import check_health
from .launcher import launch_service, wait_for_healthy, _run_wsl, _run_powershell, _run_cmd
from .ports import PortManager
from .routing import RoutingTable
from .resources import ResourceTracker
from .memory import MemoryMonitor

C = {"R": "\033[91m", "G": "\033[92m", "Y": "\033[93m", "C": "\033[96m", "M": "\033[95m", "D": "\033[90m", "X": "\033[0m"}
def _c(color, text): return f"{C.get(color, '')}{text}{C['X']}"
def _log(icon, name, msg, color="W"):
    print(f" {_c('D', time.strftime('%H:%M:%S'))} {icon} {_c(color, name):<28} {msg}")

KILL_METHODS = {}  # populated on first use


def _get_kill_methods():
    """Map services to their external kill methods (works even when WSL is dead)."""
    global KILL_METHODS
    if KILL_METHODS:
        return KILL_METHODS

    KILL_METHODS = {
        "wsl-keeper": {
            "method": "wsl_terminate",
            "cmd": "wsl --terminate Ubuntu-Migrate",
            "type": "windows_cmd",
        },
        "wsl-redis-ha": {
            "method": "wsl_kill",
            "cmd": "pkill -9 redis-server 2>/dev/null; pkill -9 redis-sentinel 2>/dev/null; true",
            "type": "wsl",
            "fallback": "wsl_terminate",
        },
        "docker-edge-redis": {
            "method": "docker_stop",
            "cmd": "docker stop docker-redis-master",
            "type": "windows_cmd",
        },
        "docker-ai-voice": {
            "method": "docker_stop",
            "cmd": "docker stop ai-voice ai-ollama",
            "type": "windows_cmd",
        },
        "win-compressor": {
            "method": "windows_kill",
            "cmd": "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*session_compressor*'} | Stop-Process -Force",
            "type": "powershell",
        },
        "win-ai-watchdog": {
            "method": "windows_kill",
            "cmd": "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*ai_watchdog*'} | Stop-Process -Force",
            "type": "powershell",
        },
        "win-stack-gui": {
            "method": "windows_kill",
            "cmd": "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*stack_gui*'} | Stop-Process -Force",
            "type": "powershell",
        },
        "win-mcp": {
            "method": "windows_kill",
            "cmd": "Get-Process python -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*ai_setup_mcp*'} | Stop-Process -Force",
            "type": "powershell",
        },
    }
    return KILL_METHODS


# ══════════════════════════════════════════════
# START
# ══════════════════════════════════════════════

def cmd_start():
    ports = PortManager(); resources = ResourceTracker(); routes = RoutingTable()
    print(f"\n{_c('C','='*60)}")
    print(_c('C','  STACK LAUNCH — BreakThrough (DAG / E:\\AI-Setup)'))
    print(_c('C','='*60))

    conflicts = ports.detect_conflicts()
    if conflicts:
        for c in conflicts:
            _log("!", "port-conflict", c, "R")
        sys.exit(1)

    warnings = resources.check_capacity()
    for w in warnings:
        _log("WARN", "resources", w, "Y")
    if not warnings:
        _log("OK", "resources", "OK", "G")

    routes.sync_from_config()
    tiers = resolve_tiers()
    print(f"\n  {len(SERVICES)} services across {len(tiers)} tiers\n")

    stats = {"healthy": 0, "failed": 0}
    for i, tier in enumerate(tiers):
        print(_c("M", f"  -- Tier {i}: {', '.join(sorted(tier))} --"))
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(_launch_one, name, SERVICES[name], routes): name for name in tier}
            for future in as_completed(futures):
                name = futures[future]
                try:
                    if future.result():
                        cfg = SERVICES[name]; ep = cfg.get("endpoint")
                        if ep: routes.register(name, ep.get("host","127.0.0.1"), ep.get("port",0), ep.get("protocol","tcp"), status="healthy")
                        stats["healthy"] += 1
                    else: stats["failed"] += 1
                except Exception as e:
                    _log("X", name, str(e), "R"); stats["failed"] += 1

    ports.sync_to_redis()
    print(f"\n{_c('C','='*60)}")
    print(_c('G' if stats['failed']==0 else 'Y', f"  DONE: {stats['healthy']} up, {stats['failed']} down"))
    print(_c('C','='*60))
    cmd_status(verbose=False)
    if stats["failed"] > 0: sys.exit(1)


def _launch_one(name, cfg, routes):
    _log(">", name, cfg["description"], "C")
    launch_service(name, cfg)
    healthy = wait_for_healthy(name, cfg, routes)
    _log("OK" if healthy else "X", name, "Healthy" if healthy else "Timeout", "G" if healthy else "R")
    return healthy


# ══════════════════════════════════════════════
# STATUS (with process-level detail)
# ══════════════════════════════════════════════

def cmd_status(verbose=True):
    memory = MemoryMonitor()
    samples = memory.sample() if verbose else {}

    print()
    header = f" {'SERVICE':<22} {'HEALTH':<10} {'CPU%':>5} {'RAM':>7} {'RUNTIME':>10} {'RESTARTS':>9}  {'PORT'}"
    print(header)
    print(f" {'-'*22} {'-'*10} {'-'*5} {'-'*7} {'-'*10} {'-'*9}  {'-'*6}")

    for name, cfg in SERVICES.items():
        h = check_health(name, cfg)
        status = _c("G", "UP  ") if h else _c("R", "DOWN")
        mem = samples.get(name, {})
        cpu = f"{mem.get('cpu_pct',0):.0f}%"
        ram = f"{mem.get('rss_mb',0):.0f}MB"
        runtime = cfg.get("runtime", "?")
        ports = ','.join(str(p) for p in cfg.get("ports",[])) if cfg.get("ports") else "-"
        print(f" {name:<22} {status:<14} {cpu:>5} {ram:>7} {runtime:>10} {'-':>9}  {ports}")

    if verbose:
        resources = ResourceTracker()
        sysinfo = resources.system_info()
        print(f"\n{_c('D','  System:')} CPU {sysinfo.get('cpu_cores_physical',0)} cores | "
              f"RAM {sysinfo.get('ram_available_mb',0)}/{sysinfo.get('ram_total_mb',0)} MB free | "
              f"VRAM ~15.8 GB (9070 XT)")


# ══════════════════════════════════════════════
# PS — show actual OS processes
# ══════════════════════════════════════════════

def cmd_ps():
    """Show actual running processes for each service."""
    print(f"\n{_c('C','='*60)}")
    print(_c('C','  RUNNING PROCESSES'))
    print(_c('C','='*60))

    # Windows processes
    print(f"\n{_c('M','  --- Windows ---')}")
    windows_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'cmdline']):
        try:
            info = proc.info
            cmdline = ' '.join(info.get('cmdline', []) or [])
            if not cmdline:
                continue
            # Match with our services
            matched = None
            if 'session_compressor' in cmdline:
                matched = 'win-compressor'
            elif 'ai_setup_mcp' in cmdline:
                matched = 'win-mcp'
            elif "stack_gui" in cmdline:
                matched = "win-stack-gui"
            elif 'dashboard' in cmdline and 'server' in cmdline:
                matched = 'legacy-dashboard'
            elif 'wsl' in cmdline and 'sleep infinity' in cmdline:
                matched = 'wsl-keeper'

            if matched:
                rss_mb = info.get('memory_info', None)
                rss = rss_mb.rss // (1024*1024) if rss_mb else 0
                print(f"  {matched:<22} PID:{info['pid']:<6} CPU:{info['cpu_percent']:.0f}% RAM:{rss}MB")
        except Exception:
            pass

    # WSL processes
    print(f"\n{_c('M','  --- WSL ---')}")
    wsl_alive = False
    try:
        out = subprocess.run(
            ["wsl", "-d", "Ubuntu-Migrate", "-e", "bash", "-c",
             "echo ALIVE && (ps -eo pid,pcpu,rss,comm --no-headers 2>/dev/null | grep -E 'redis|ollama|gemma|python') || echo 'no WSL procs'"],
            capture_output=True, text=True, timeout=8
        )
        if "ALIVE" in out.stdout:
            wsl_alive = True
            for line in out.stdout.split('\n'):
                if line and 'ALIVE' not in line and 'no WSL' not in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        print(f"  PID:{parts[0]:<6} CPU:{parts[1]}% RAM:{int(int(parts[2])/1024)}MB {parts[3]}")
    except Exception as e:
        pass

    if not wsl_alive:
        print(f"  {_c('R','WSL NOT RUNNING — Ubuntu-Migrate is down')}")

    # Docker processes
    print(f"\n{_c('M','  --- Docker ---')}")
    try:
        out = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}} {{.Status}}"],
            capture_output=True, text=True, timeout=5
        )
        docker_procs = out.stdout.strip().split('\n')
        if docker_procs and docker_procs[0]:
            for line in docker_procs:
                parts = line.split(' ', 1)
                if len(parts) >= 2:
                    print(f"  {parts[0]:<22} {parts[1]}")
        else:
            print(f"  (no Docker containers running)")
    except Exception:
        print(f"  {_c('R','Docker not accessible')}")


# ══════════════════════════════════════════════
# KILL — external force kill
# ══════════════════════════════════════════════

def cmd_kill(name=None):
    """Force-kill a service externally, bypassing its own stop command."""
    methods = _get_kill_methods()

    if name and name not in SERVICES and name not in methods:
        print(f"Unknown service: {name}")
        return

    names = [name] if name else sorted(SERVICES.keys())
    print(f"\n{_c('R','='*60)}")
    print(_c('R',f"  FORCE KILL {' '.join(names) if name else 'ALL SERVICES'}"))
    print(_c('R','='*60))

    for n in names:
        method = methods.get(n, {})
        if not method:
            cfg = SERVICES.get(n, {})
            # Generic: try wsl kill first, then windows
            runtime = cfg.get("runtime", "")
            if runtime == "wsl":
                _force_wsl_kill(n)
            elif runtime == "windows":
                _force_windows_kill(n)
            else:
                _log("?", n, "No kill method defined", "Y")
            continue

        mtype = method.get("type", "")
        cmd = method.get("cmd", "")
        fallback = method.get("fallback", "")

        try:
            if mtype == "wsl":
                out, ok = _run_wsl(cmd, timeout=8)
                if not ok and fallback == "wsl_terminate":
                    _log("!", n, "WSL unreachable — terminating VM", "Y")
                    subprocess.run(["wsl", "--terminate", "Ubuntu-Migrate"], capture_output=True, timeout=10)
                    _log("OK", n, "WSL terminated", "G")
                else:
                    _log("OK", n, "Killed", "G")
            elif mtype in ("windows_cmd", "powershell"):
                _, ok = _run_powershell(cmd, timeout=10)
                _log("OK" if ok else "?", n, "Killed" if ok else "Kill may have failed", "G" if ok else "Y")
        except Exception as e:
            _log("X", n, str(e), "R")

    if not name:
        # Also terminate WSL as cleanup
        try:
            subprocess.run(["wsl", "--terminate", "Ubuntu-Migrate"], capture_output=True, timeout=10)
            _log("OK", "wsl", "WSL terminated", "G")
        except Exception:
            pass

    print()


def _force_wsl_kill(name):
    """Last-resort WSL process kill."""
    try:
        subprocess.run(["wsl", "--terminate", "Ubuntu-Migrate"], capture_output=True, timeout=10)
        _log("OK", name, "WSL terminated (all WSL services killed)", "G")
    except Exception as e:
        _log("X", name, str(e), "R")


def _force_windows_kill(name):
    """Last-resort Windows process kill."""
    patterns = {
        "win-compressor": "*session_compressor*",
        "win-mcp": "*ai_setup_mcp*",
        "wsl-keeper": "*sleep infinity*",
    }
    pattern = patterns.get(name, name)
    try:
        subprocess.run(
            ["powershell", "-Command",
             f"Get-Process python -ErrorAction SilentlyContinue | "
             f"Where-Object {{$_.CommandLine -like '{pattern}'}} | Stop-Process -Force"],
            capture_output=True, timeout=10
        )
        _log("OK", name, "Process killed", "G")
    except Exception as e:
        _log("X", name, str(e), "R")


# ══════════════════════════════════════════════
# RECOVER — restart crashed services
# ══════════════════════════════════════════════

def cmd_recover():
    """Detect and recover crashed services."""
    print(f"\n{_c('C','='*60)}")
    print(_c('C','  RECOVERY — detecting and restarting crashed services'))
    print(_c('C','='*60))

    routes = RoutingTable()
    recovered = 0
    failed = 0

    for name, cfg in SERVICES.items():
        if check_health(name, cfg):
            _log("OK", name, "Already healthy", "G")
            continue

        _log("!", name, f"Down — attempting restart", "Y")

        # Force kill first (clean state)
        methods = _get_kill_methods()
        method = methods.get(name, {})
        if method:
            ktype = method.get("type", "")
            kcmd = method.get("cmd", "")
            try:
                if ktype == "wsl":
                    _run_wsl(kcmd, timeout=5)
                elif ktype in ("windows_cmd", "powershell"):
                    _run_powershell(kcmd, timeout=5)
            except Exception:
                pass
            time.sleep(1)

        # Relaunch
        launch_service(name, cfg)
        if wait_for_healthy(name, cfg, routes):
            _log("OK", name, "Recovered!", "G")
            recovered += 1
        else:
            _log("X", name, "Recovery failed", "R")
            failed += 1

    print(f"\n{_c('G' if failed==0 else 'Y', f'  Recovered {recovered}, still down {failed}')}")


# ══════════════════════════════════════════════
# STOP / RESTART / MONITOR (existing)
# ══════════════════════════════════════════════

def cmd_stop():
    tiers = resolve_tiers(); all_names = []; [all_names.extend(sorted(t)) for t in tiers]; all_names.reverse()
    print(f"\n{_c('Y','='*60)}"); print(_c('Y','  STOPPING ALL')); print(_c('Y','='*60))
    for name in all_names:
        cfg = SERVICES[name]; stop_cmd = cfg.get("stop","")
        if stop_cmd:
            try:
                rt = cfg.get("runtime")
                if rt == "wsl":
                    _run_wsl(stop_cmd, timeout=10)
                elif rt == "docker":
                    _run_cmd(stop_cmd, timeout=90)
                else:
                    _run_powershell(stop_cmd, timeout=15)
                _log("OK", name, "Stopped", "G")
            except Exception as e: _log("X", name, str(e), "R")
    subprocess.run(["wsl","--terminate","Ubuntu-Migrate"], capture_output=True, timeout=15)
    _log("OK","wsl","WSL terminated","G")
    print(f"\n{_c('G','  Stack stopped')}")


def cmd_restart(name):
    if name not in SERVICES: print(f"Unknown: {name}"); return
    cfg = SERVICES[name]; routes = RoutingTable()
    _log(">", name, f"Restarting {cfg['description']}", "C")
    stop_cmd = cfg.get("stop","")
    if stop_cmd:
        if cfg.get("runtime")=="wsl": _run_wsl(stop_cmd, timeout=10)
        else: _run_powershell(stop_cmd, timeout=10)
        time.sleep(1)
    routes.update_status(name, "restarting")
    launch_service(name, cfg)
    healthy = wait_for_healthy(name, cfg, routes)
    _log("OK" if healthy else "X", name, "Restarted" if healthy else "Failed", "G" if healthy else "R")


def cmd_monitor():
    print(f"\n{_c('C','  MONITOR — watchdog active')}")
    cmd_start()
    memory = MemoryMonitor(); routes = RoutingTable(); fail_counts = defaultdict(int)
    print(f"\n{_c('M','  [Ctrl+C to stop]')}")
    while True:
        try:
            time.sleep(10)
            for name, cfg in SERVICES.items():
                if not check_health(name, cfg):
                    fail_counts[name] += 1
                    _log("!", name, f"Down (#{fail_counts[name]})", "R")
                    launch_service(name, cfg); routes.update_status(name,"starting")
                    if wait_for_healthy(name, cfg, routes):
                        _log("OK", name, "Recovered", "G"); fail_counts[name]=0
                    else:
                        _log("X", name, "Failed", "R"); routes.update_status(name,"failed")
            for a in memory.check_limits(): _log("MEM", "alert", a, "R")
        except KeyboardInterrupt: _log("!", "MONITOR", "Shutdown", "Y"); break
    cmd_stop()


# ══════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════

COMMANDS = {
    "start":   (cmd_start,   "Launch all services"),
    "stop":    (cmd_stop,    "Stop all services"),
    "status":  (cmd_status,  "Service health + resources"),
    "ps":      (cmd_ps,      "Show actual OS processes"),
    "recover": (cmd_recover, "Detect and restart crashed services"),
    "kill":    ("args",      "Force-kill service externally"),
    "restart": ("args",      "Restart a service"),
    "monitor": (cmd_monitor, "Continuous watchdog with auto-recovery"),
}


def main():
    if len(sys.argv) < 2:
        print("\nStack Manager CLI")
        print("Usage: python -m stack_manager.cli <command> [args]\n")
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:<12} {desc}")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "restart":
        if len(sys.argv) < 3: print("Usage: restart <name>"); return
        cmd_restart(sys.argv[2])
    elif cmd == "kill":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_kill(name)
    elif cmd in COMMANDS:
        handler = COMMANDS[cmd][0]
        if callable(handler): handler()
    else:
        print(f"Unknown: {cmd}. Commands: {', '.join(COMMANDS)}")


if __name__ == "__main__":
    main()
