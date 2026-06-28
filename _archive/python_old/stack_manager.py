#!/usr/bin/env python3
"""
Stack Manager — Full Orchestrator for Akashic Aurora
=========================================================
Unified process supervisor, service discovery, resource tracker, and
network mapper across Windows, WSL2, and Docker.

Capabilities:
  • DAG-based dependency resolution → parallel launch within tiers
  • Port allocation + conflict detection (integrates with port_registry.py)
  • Routing table → Redis-based service discovery (service:<name>:endpoint)
  • Resource tracking → CPU, GPU VRAM, RAM, WSL memory, RAM disk
  • Memory monitoring → per-service RSS/VMS with limits and alerts
  • Health checks → TCP / HTTP / Redis / Process / WSL-alive
  • Auto-restart on failure (monitor mode)
  • Status dashboard via Redis keys + console

Usage:
  python stack_manager.py start        # Launch the full stack
  python stack_manager.py stop         # Stop all services
  python stack_manager.py status       # Show service + resource status
  python stack_manager.py monitor      # Start + continuous health + memory watch
  python stack_manager.py restart <n>  # Restart a specific service
  python stack_manager.py ports        # Show port allocation map
  python stack_manager.py routes       # Show service routing table

Architecture tiers:
  Tier 0: wsl-keeper, docker-redis
  Tier 1: wsl-redis-master
  Tier 2: wsl-redis-replica1, wsl-redis-replica2
  Tier 3: wsl-sentinel1/2/3, gemma-2b
  Tier 4: session-compressor
"""

import os
import sys
import json
import time
import signal
import socket
import shutil
import psutil
import threading
import subprocess
from collections import defaultdict, deque, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

# ── Platform setup ──
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7
        )
    except Exception:
        pass

sys.path.insert(0, r"E:\AI-Setup")

# ──────────────────────────────────────────────────────────────
# COLOR + LOGGING HELPERS
# ──────────────────────────────────────────────────────────────

C = {
    "R": "\033[91m", "G": "\033[92m", "Y": "\033[93m",
    "B": "\033[94m", "C": "\033[96m", "M": "\033[95m",
    "W": "\033[97m", "X": "\033[0m", "D": "\033[90m",
}


def c(color: str, text: str) -> str:
    return f"{C.get(color, '')}{text}{C['X']}"


def log(icon: str, name: str, msg: str, color: str = "W"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f" {c('D', ts)} {icon} {c(color, name):<28} {msg}")


# ──────────────────────────────────────────────────────────────
# WSL + POWERSHELL EXEC HELPERS
# ──────────────────────────────────────────────────────────────

def _run_wsl(cmd: str, timeout: int = 10) -> tuple:
    try:
        p = subprocess.run(
            ["wsl", "-d", "Ubuntu-Migrate", "-e", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.stdout.strip(), p.returncode == 0
    except subprocess.TimeoutExpired:
        return "", False
    except Exception:
        return "", False


def _run_ps(cmd: str, timeout: int = 15) -> tuple:
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.stdout.strip(), p.returncode == 0
    except subprocess.TimeoutExpired:
        return "", False
    except Exception:
        return "", False


def _run_cmd(cmd: str, timeout: int = 30, cwd: str = None) -> tuple:
    try:
        p = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd,
        )
        return p.stdout.strip(), p.returncode == 0
    except Exception:
        return "", False


# ──────────────────────────────────────────────────────────────
# REDIS CONNECTION (lazy, reconnects)
# ──────────────────────────────────────────────────────────────

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
        r = redis_lib.Redis(host="127.0.0.1", port=6379, decode_responses=True, socket_connect_timeout=3)
        r.ping()
        _redis_conn = r
        return r
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────
# SERVICE CONFIGURATION
# ──────────────────────────────────────────────────────────────

SERVICES = {
    # ── Tier 0: Infrastructure ──
    "wsl-keeper": {
        "description": "WSL2 VM keep-alive (prevents VM shutdown)",
        "runtime": "windows",
        "command": (
            'Start-Process -WindowStyle Hidden -FilePath wsl '
            '-ArgumentList "-d","Ubuntu-Migrate","-e","bash","-c","sleep infinity" '
            '-PassThru'
        ),
        "depends": [],
        "health": {"type": "wsl_alive"},
        "stop": "wsl --terminate Ubuntu-Migrate",
        "ports": [],
        "resources": {"cpu_cores": 0, "ram_mb": 0, "gpu_vram_mb": 0},
        "startup_timeout": 15,
    },
    "docker-redis": {
        "description": "Docker Redis Stack HA (6 containers)",
        "runtime": "docker",
        "command": (
            "docker compose -f E:\\AI-Setup\\dockerized-ai\\redis\\docker-compose-ha.yml "
            "up -d --remove-orphans"
        ),
        "cwd": r"E:\AI-Setup\dockerized-ai\redis",
        "depends": [],
        "health": {"type": "tcp", "host": "127.0.0.1", "port": 6379},
        "stop": (
            "docker compose -f E:\\AI-Setup\\dockerized-ai\\redis\\docker-compose-ha.yml down"
        ),
        "ports": [6379, 6380, 6381, 26379, 26380, 26381],
        "resources": {"cpu_cores": 2, "ram_mb": 1024, "gpu_vram_mb": 0},
        "startup_timeout": 60,
    },
    # ── Tier 1: WSL Redis Master ──
    "wsl-redis-master": {
        "description": "WSL Redis Stack Master (port 6379)",
        "runtime": "wsl",
        "command": (
            "pkill -f 'redis-server.*:6379' 2>/dev/null; sleep 0.5; "
            "redis-server /opt/redis/master/redis-master.conf --daemonize yes 2>/dev/null"
        ),
        "depends": ["wsl-keeper"],
        "health": {"type": "redis_ping", "port": 6379},
        "stop": "redis-cli -p 6379 SHUTDOWN NOSAVE 2>/dev/null",
        "ports": [6379],
        "resources": {"cpu_cores": 1, "ram_mb": 256, "gpu_vram_mb": 0},
        "endpoint": {"host": "127.0.0.1", "port": 6379, "protocol": "redis"},
        "startup_timeout": 15,
    },
    # ── Tier 2: WSL Redis Replicas ──
    "wsl-redis-replica1": {
        "description": "WSL Redis Replica 1 (port 6380)",
        "runtime": "wsl",
        "command": (
            "pkill -f 'redis-server.*:6380' 2>/dev/null; sleep 0.5; "
            "redis-server /opt/redis/replica1/redis-replica1.conf --daemonize yes 2>/dev/null"
        ),
        "depends": ["wsl-redis-master"],
        "health": {"type": "redis_ping", "port": 6380},
        "ports": [6380],
        "resources": {"cpu_cores": 0.5, "ram_mb": 128, "gpu_vram_mb": 0},
        "endpoint": {"host": "127.0.0.1", "port": 6380, "protocol": "redis"},
        "startup_timeout": 10,
    },
    "wsl-redis-replica2": {
        "description": "WSL Redis Replica 2 (port 6381)",
        "runtime": "wsl",
        "command": (
            "pkill -f 'redis-server.*:6381' 2>/dev/null; sleep 0.5; "
            "redis-server /opt/redis/replica2/redis-replica2.conf --daemonize yes 2>/dev/null"
        ),
        "depends": ["wsl-redis-master"],
        "health": {"type": "redis_ping", "port": 6381},
        "ports": [6381],
        "resources": {"cpu_cores": 0.5, "ram_mb": 128, "gpu_vram_mb": 0},
        "endpoint": {"host": "127.0.0.1", "port": 6381, "protocol": "redis"},
        "startup_timeout": 10,
    },
    # ── Tier 3: Sentinels + Gemma ──
    "wsl-sentinel1": {
        "description": "WSL Sentinel 1 (port 26379)",
        "runtime": "wsl",
        "command": (
            "pkill -f 'sentinel.*:26379' 2>/dev/null; sleep 0.5; "
            "redis-server /opt/redis/sentinel1/sentinel1.conf --sentinel --daemonize yes 2>/dev/null"
        ),
        "depends": ["wsl-redis-replica1", "wsl-redis-replica2"],
        "health": {"type": "redis_ping", "port": 26379},
        "ports": [26379],
        "resources": {"cpu_cores": 0.2, "ram_mb": 64, "gpu_vram_mb": 0},
        "startup_timeout": 10,
    },
    "wsl-sentinel2": {
        "description": "WSL Sentinel 2 (port 26380)",
        "runtime": "wsl",
        "command": (
            "pkill -f 'sentinel.*:26380' 2>/dev/null; sleep 0.5; "
            "redis-server /opt/redis/sentinel2/sentinel2.conf --sentinel --daemonize yes 2>/dev/null"
        ),
        "depends": ["wsl-redis-replica1", "wsl-redis-replica2"],
        "health": {"type": "redis_ping", "port": 26380},
        "ports": [26380],
        "resources": {"cpu_cores": 0.2, "ram_mb": 64, "gpu_vram_mb": 0},
        "startup_timeout": 10,
    },
    "wsl-sentinel3": {
        "description": "WSL Sentinel 3 (port 26381)",
        "runtime": "wsl",
        "command": (
            "pkill -f 'sentinel.*:26381' 2>/dev/null; sleep 0.5; "
            "redis-server /opt/redis/sentinel3/sentinel3.conf --sentinel --daemonize yes 2>/dev/null"
        ),
        "depends": ["wsl-redis-replica1", "wsl-redis-replica2"],
        "health": {"type": "redis_ping", "port": 26381},
        "ports": [26381],
        "resources": {"cpu_cores": 0.2, "ram_mb": 64, "gpu_vram_mb": 0},
        "startup_timeout": 10,
    },
    "gemma-2b": {
        "description": "Gemma 2B LLM service (localhost:5000)",
        "runtime": "wsl",
        "command": (
            "pkill -f 'python.*server.py' 2>/dev/null; sleep 0.5; "
            "source /etc/profile.d/rocm.sh 2>/dev/null; "
            "source /root/rocm-venv/bin/activate 2>/dev/null; "
            "cd /mnt/e/AI-Setup/gemma_realtime; "
            "nohup python server.py > /tmp/gemma.log 2>&1 &"
        ),
        "depends": ["wsl-keeper"],
        "health": {"type": "http", "url": "http://localhost:5000/health"},
        "ports": [5000],
        "resources": {"cpu_cores": 2, "ram_mb": 2048, "gpu_vram_mb": 0},
        "endpoint": {"host": "127.0.0.1", "port": 5000, "protocol": "http"},
        "memory_limit_mb": 4096,
        "startup_timeout": 60,
    },
    # ── Tier 4: Windows Services ──
    "session-compressor": {
        "description": "Session Compressor (auto-compresses logs)",
        "runtime": "windows",
        "command": (
            'if (Get-Process python -ErrorAction SilentlyContinue | Where-Object '
            '{$_.CommandLine -like "*session_compressor*"}) { exit 0 }; '
            'Start-Process -WindowStyle Hidden -FilePath python '
            '-ArgumentList "E:\\AI-Setup\\session_compressor.py","--daemon"'
        ),
        "depends": ["wsl-redis-master"],
        "health": {"type": "process", "name": "session_compressor"},
        "stop": (
            'Get-Process python -ErrorAction SilentlyContinue | '
            'Where-Object {$_.CommandLine -like "*session_compressor*"} | '
            'Stop-Process -Force'
        ),
        "ports": [],
        "resources": {"cpu_cores": 0.5, "ram_mb": 256, "gpu_vram_mb": 0},
        "memory_limit_mb": 512,
        "startup_timeout": 15,
    },
    # ── Tier 4: Stack GUI ──
    "stack-gui": {
        "description": "Stack Manager Web GUI (localhost:8090)",
        "runtime": "windows",
        "command": (
            'if (Get-Process python -ErrorAction SilentlyContinue | Where-Object '
            '{$_.CommandLine -like "*stack_gui*"}) { exit 0 }; '
            'Start-Process -WindowStyle Hidden -FilePath python '
            '-ArgumentList "E:\\AI-Setup\\stack_gui.py","--no-browser","--port","8090"'
        ),
        "depends": ["wsl-redis-master"],
        "health": {"type": "http", "url": "http://localhost:8090/api/dashboard"},
        "stop": (
            'Get-Process python -ErrorAction SilentlyContinue | '
            'Where-Object {$_.CommandLine -like "*stack_gui*"} | '
            'Stop-Process -Force'
        ),
        "ports": [8090],
        "resources": {"cpu_cores": 0.5, "ram_mb": 256, "gpu_vram_mb": 0},
        "endpoint": {"host": "127.0.0.1", "port": 8090, "protocol": "http"},
        "memory_limit_mb": 256,
        "startup_timeout": 15,
    },
}

# ──────────────────────────────────────────────────────────────
# DAG RESOLVER
# ──────────────────────────────────────────────────────────────

def resolve_tiers(services: dict = None) -> list:
    """Kahn's algorithm → list of parallel-safe launch tiers."""
    if services is None:
        services = SERVICES
    in_degree = {n: len(c["depends"]) for n, c in services.items()}
    dependents = defaultdict(set)
    for name, cfg in services.items():
        for dep in cfg["depends"]:
            dependents[dep].add(name)
    queue = deque([n for n, d in in_degree.items() if d == 0])
    tiers = []
    while queue:
        tier = set()
        for _ in range(len(queue)):
            node = queue.popleft()
            tier.add(node)
            for d in dependents[node]:
                in_degree[d] -= 1
                if in_degree[d] == 0:
                    queue.append(d)
        tiers.append(tier)
    if sum(len(t) for t in tiers) != len(services):
        raise RuntimeError("Circular dependency in service configuration")
    return tiers


# ══════════════════════════════════════════════════════════════
# SUBSYSTEM 1: PORT MANAGER — allocation, conflict detection
# ══════════════════════════════════════════════════════════════

class PortManager:
    """
    Manages port allocation across all services.
    Detects conflicts before launch, registers ports in Redis,
    provides a unified port map for the whole stack.
    """

    def __init__(self):
        self.allocations: dict[str, list[int]] = {}  # service_name → [ports]

    def scan_services(self, services: dict = None) -> dict[str, list[int]]:
        """Extract port assignments from service configs."""
        if services is None:
            services = SERVICES
        result = {}
        for name, cfg in services.items():
            ports = cfg.get("ports", [])
            if ports:
                result[name] = sorted(ports)
        return result

    def detect_conflicts(self, services: dict = None) -> list[str]:
        """
        Check for port conflicts across services.
        Shared-purpose services (same runtime type group: wsl/docker)
        using the same ports are treated as alternatives, not conflicts.
        """
        if services is None:
            services = SERVICES
        port_to_services = defaultdict(list)
        for name, cfg in services.items():
            for port in cfg.get("ports", []):
                port_to_services[port].append(name)

        conflicts = []
        for port, names in port_to_services.items():
            if len(names) > 1:
                # Check if all services sharing this port are in the same
                # purpose group (both runtimes for same logical service)
                runtimes = {services[n].get("runtime", "") for n in names}
                if len(runtimes) == 1:
                    # Same runtime = real conflict
                    conflicts.append(
                        f"Port {port}: {', '.join(names)} (same runtime={list(runtimes)[0]})"
                    )
                # Different runtimes = alternative backends (not a conflict)
        return conflicts

    def check_port_in_use(self, port: int, host: str = "127.0.0.1") -> bool:
        """Check if a TCP port is already bound on the host."""
        try:
            s = socket.create_connection((host, port), timeout=1)
            s.close()
            return True
        except Exception:
            return False

    def scan_host_ports(self) -> dict[int, str]:
        """Scan all declared ports and report which are already in use."""
        in_use = {}
        seen = set()
        for cfg in SERVICES.values():
            for port in cfg.get("ports", []):
                if port not in seen:
                    seen.add(port)
                    if self.check_port_in_use(port):
                        in_use[port] = "IN USE"
                    else:
                        in_use[port] = "free"
        return in_use

    def sync_to_redis(self):
        """Write current port allocations to Redis port registry."""
        r = _redis()
        if not r:
            return
        now = datetime.now().isoformat()
        for name, cfg in SERVICES.items():
            ports = cfg.get("ports", [])
            endpoint = cfg.get("endpoint", {})
            for port in ports:
                key = f"port:{name.replace('-', '_')}"
                if port != (endpoint.get("port") or ports[0]):
                    key = f"port:{name.replace('-', '_')}_{port}"
                r.hset(key, mapping={
                    "port": str(port),
                    "protocol": endpoint.get("protocol", "tcp"),
                    "description": cfg["description"],
                    "service": name,
                    "updated_at": now,
                })

    def print_map(self):
        """Print the full port allocation map."""
        print()
        print(f" {'PORT':<8} {'SERVICE':<26} {'STATUS':<10} {'DESCRIPTION'}")
        print(f" {'-'*8} {'-'*26} {'-'*10} {'-'*40}")
        seen = set()
        for name, cfg in SERVICES.items():
            for port in cfg.get("ports", []):
                if port in seen:
                    continue
                seen.add(port)
                status = "IN USE" if self.check_port_in_use(port) else "free"
                sc = "G" if status == "IN USE" else "D"
                print(f" {port:<8} {name:<26} {c(sc, status):<18} {cfg['description']}")


# ══════════════════════════════════════════════════════════════
# SUBSYSTEM 2: ROUTING TABLE — Redis-based service discovery
# ══════════════════════════════════════════════════════════════

class RoutingTable:
    """
    Maintains a Redis-backed service discovery table.
    Format: service:<name>:endpoint → {host, port, protocol, status, updated_at}
    Allows any tool in the stack to discover services without hardcoding URLs.
    """

    PREFIX = "service"
    ROUTING_KEY = "service:routing"

    def register(self, name: str, host: str, port: int, protocol: str, status: str = "starting"):
        """Register a service endpoint in Redis."""
        r = _redis()
        if not r:
            return
        key = f"{self.PREFIX}:{name}:endpoint"
        mapping = {
            "host": host,
            "port": str(port),
            "protocol": protocol,
            "status": status,
            "updated_at": datetime.now().isoformat(),
        }
        r.hset(key, mapping=mapping)
        # Also store in aggregated routing hash
        r.hset(self.ROUTING_KEY, name, json.dumps(mapping))

    def update_status(self, name: str, status: str):
        """Update a service's status in the routing table."""
        r = _redis()
        if not r:
            return
        key = f"{self.PREFIX}:{name}:endpoint"
        r.hset(key, "status", status)
        r.hset(key, "updated_at", datetime.now().isoformat())
        # Also update aggregated routing
        existing = r.hget(self.ROUTING_KEY, name)
        if existing:
            try:
                data = json.loads(existing)
                data["status"] = status
                data["updated_at"] = datetime.now().isoformat()
                r.hset(self.ROUTING_KEY, name, json.dumps(data))
            except Exception:
                pass

    def unregister(self, name: str):
        """Remove a service from the routing table."""
        r = _redis()
        if not r:
            return
        r.delete(f"{self.PREFIX}:{name}:endpoint")
        r.hdel(self.ROUTING_KEY, name)

    def discover(self, name: str) -> dict | None:
        """Look up a service endpoint."""
        r = _redis()
        if not r:
            return None
        data = r.hgetall(f"{self.PREFIX}:{name}:endpoint")
        return data if data else None

    def list_all(self) -> dict:
        """Return all registered service endpoints."""
        r = _redis()
        if not r:
            return {}
        raw = r.hgetall(self.ROUTING_KEY)
        return {k: json.loads(v) for k, v in raw.items()}

    def print_routes(self):
        """Print the routing table."""
        routes = self.list_all()
        if not routes:
            print("  (no routes registered — Redis not available)")
            return
        print()
        print(f" {'SERVICE':<26} {'ENDPOINT':<30} {'STATUS'}")
        print(f" {'-'*26} {'-'*30} {'-'*12}")
        for name, info in sorted(routes.items()):
            endpoint = f"{info.get('host', '?')}:{info.get('port', '?')} ({info.get('protocol', '?')})"
            status = info.get("status", "unknown")
            sc = "G" if status == "healthy" else ("Y" if status == "starting" else "R")
            print(f" {name:<26} {endpoint:<30} {c(sc, status)}")

    def sync_from_config(self, services: dict = None):
        """Register all services that have endpoint definitions."""
        if services is None:
            services = SERVICES
        for name, cfg in services.items():
            ep = cfg.get("endpoint")
            if ep:
                self.register(
                    name, ep.get("host", "127.0.0.1"),
                    ep.get("port", 0), ep.get("protocol", "tcp"),
                    status="defined",
                )


# ══════════════════════════════════════════════════════════════
# SUBSYSTEM 3: RESOURCE TRACKER — CPU, GPU, RAM, WSL, RAM disk
# ══════════════════════════════════════════════════════════════

class ResourceTracker:
    """
    Tracks system resource utilization and per-service allocations.
    Detects overallocation before launching services.
    """

    def __init__(self):
        self.allocations: dict[str, dict] = {}  # service → {"cpu": 1, "ram_mb": 256, ...}

    def system_info(self) -> dict:
        """Get host system resource info."""
        info = {
            "cpu_cores_logical": psutil.cpu_count(logical=True),
            "cpu_cores_physical": psutil.cpu_count(logical=False),
            "ram_total_mb": psutil.virtual_memory().total // (1024 * 1024),
            "ram_available_mb": psutil.virtual_memory().available // (1024 * 1024),
            "ram_used_pct": psutil.virtual_memory().percent,
            "disk_free_gb": {},
        }
        for part in psutil.disk_partitions():
            try:
                usage = shutil.disk_usage(part.mountpoint)
                info["disk_free_gb"][part.mountpoint] = usage.free // (1024**3)
            except Exception:
                pass
        return info

    def wsl_memory_mb(self) -> int | None:
        """Get WSL VM memory usage in MB (from inside WSL)."""
        out, ok = _run_wsl(
            "free -m 2>/dev/null | awk '/^Mem:/ {print $3}' || "
            "cat /proc/meminfo 2>/dev/null | grep MemTotal | awk '{print $2/1024}'",
            timeout=5,
        )
        if ok and out:
            try:
                return int(float(out.strip()))
            except Exception:
                pass
        return None

    def gpu_info(self) -> dict | None:
        """Get GPU info via WSL ROCm."""
        out, ok = _run_wsl(
            "source /etc/profile.d/rocm.sh 2>/dev/null; "
            "rocm-smi --showmeminfo vram --json 2>/dev/null || "
            "echo '{}'",
            timeout=10,
        )
        if ok and out:
            try:
                return json.loads(out)
            except Exception:
                pass
        return None

    def ram_disk_usage(self) -> dict:
        """Get RAM disk (X:) usage."""
        try:
            usage = shutil.disk_usage("X:\\")
            return {
                "total_mb": usage.total // (1024 * 1024),
                "used_mb": usage.used // (1024 * 1024),
                "free_mb": usage.free // (1024 * 1024),
                "used_pct": round(usage.used / usage.total * 100, 1),
            }
        except Exception:
            return {"total_mb": 0, "used_mb": 0, "free_mb": 0, "used_pct": 0}

    def check_capacity(self, services: dict = None) -> list[str]:
        """
        Check if system has enough resources for all declared services.
        Returns list of warnings (empty = all good).
        """
        if services is None:
            services = SERVICES

        system = self.system_info()
        total_cpu = 0.0
        total_ram = 0

        for cfg in services.values():
            res = cfg.get("resources", {})
            total_cpu += res.get("cpu_cores", 0)
            total_ram += res.get("ram_mb", 0)

        warnings = []
        if total_cpu > system["cpu_cores_logical"] * 0.85:
            warnings.append(
                f"CPU overallocation: {total_cpu:.0f} requested vs "
                f"{system['cpu_cores_logical']} available"
            )
        if total_ram > system["ram_available_mb"]:
            warnings.append(
                f"RAM overallocation: {total_ram} MB requested vs "
                f"{system['ram_available_mb']} MB available"
            )
        return warnings

    def print_resources(self):
        """Print system resource overview."""
        sysinfo = self.system_info()
        wsl_mem = self.wsl_memory_mb()
        ramdisk = self.ram_disk_usage()

        print()
        print(c("B", "  SYSTEM RESOURCES"))
        print(f"  CPU: {sysinfo['cpu_cores_physical']} physical / {sysinfo['cpu_cores_logical']} logical cores")
        print(f"  RAM: {sysinfo['ram_available_mb']} MB available / {sysinfo['ram_total_mb']} MB total ({sysinfo['ram_used_pct']}% used)")
        if wsl_mem:
            print(f"  WSL Memory: ~{wsl_mem} MB used")
        if ramdisk["total_mb"] > 0:
            print(f"  RAM Disk (X:\\): {ramdisk['free_mb']} MB free / {ramdisk['total_mb']} MB total")

        # Per-service allocation
        print()
        print(f" {'SERVICE':<26} {'CPU':>5} {'RAM':>8} {'GPU VRAM':>9}")
        print(f" {'-'*26} {'-'*5} {'-'*8} {'-'*9}")
        for name, cfg in SERVICES.items():
            res = cfg.get("resources", {})
            cpu = res.get("cpu_cores", 0)
            ram = res.get("ram_mb", 0)
            gpu = res.get("gpu_vram_mb", 0)
            print(f" {name:<26} {cpu:>4.1f}  {ram:>5} MB  {gpu:>4} MB")


# ══════════════════════════════════════════════════════════════
# SUBSYSTEM 4: MEMORY MONITOR — per-service RSS/VMS tracking
# ══════════════════════════════════════════════════════════════

class MemoryMonitor:
    """
    Tracks per-service memory usage (RSS, VMS) and alerts on limit breaches.
    Stores snapshots in Redis for trend analysis.
    """

    def __init__(self):
        self.snapshots: dict[str, list] = defaultdict(list)  # name → [snapshots]
        self.max_snapshots = 30  # rolling window

    def sample(self, services: dict = None) -> dict[str, dict]:
        """Take a memory sample for all active services."""
        if services is None:
            services = SERVICES
        samples = {}
        for name, cfg in services.items():
            mem = self._sample_service(name, cfg)
            if mem:
                samples[name] = mem
                self.snapshots[name].append(mem)
                if len(self.snapshots[name]) > self.max_snapshots:
                    self.snapshots[name] = self.snapshots[name][-self.max_snapshots:]
                # Store in Redis
                r = _redis()
                if r:
                    try:
                        r.hset(f"service:{name}:memory", mapping={
                            "rss_mb": str(mem.get("rss_mb", 0)),
                            "vms_mb": str(mem.get("vms_mb", 0)),
                            "cpu_pct": str(mem.get("cpu_pct", 0)),
                            "timestamp": datetime.now().isoformat(),
                        })
                    except Exception:
                        pass
        return samples

    def _sample_service(self, name: str, cfg: dict) -> dict | None:
        """Sample memory for a single service."""
        runtime = cfg.get("runtime", "")
        try:
            if runtime == "wsl":
                if name == "wsl-keeper":
                    return None
                # Match by process name patterns
                patterns = {
                    "wsl-redis-master": "redis-server.*:6379",
                    "wsl-redis-replica1": "redis-server.*:6380",
                    "wsl-redis-replica2": "redis-server.*:6381",
                    "wsl-sentinel1": "redis-sentinel.*:26379",
                    "wsl-sentinel2": "redis-sentinel.*:26380",
                    "wsl-sentinel3": "redis-sentinel.*:26381",
                    "gemma-2b": "python.*server\\.py",
                }
                pattern = patterns.get(name, name)
                out, ok = _run_wsl(
                    f"ps -eo rss,vsize,pcpu,comm --no-headers 2>/dev/null | "
                    f"grep -E '{pattern}' | grep -v grep | "
                    f"awk '{{rss+=$1; vsize+=$2; cpu+=$3}} END {{print rss, vsize, cpu}}'",
                    timeout=5,
                )
                if ok and out.strip():
                    parts = out.split()
                    return {
                        "rss_mb": round(float(parts[0]) / 1024, 1),
                        "vms_mb": round(float(parts[1]) / 1024, 1) if len(parts) > 1 else 0,
                        "cpu_pct": round(float(parts[2]), 1) if len(parts) > 2 else 0,
                    }

            elif runtime == "windows":
                match_name = {
                    "session-compressor": "python",
                }.get(name, name)
                out, ok = _run_ps(
                    f"(Get-Process -Name '{match_name}' -ErrorAction SilentlyContinue | "
                    f"Where-Object {{$_.CommandLine -like '*{name}*'}} | "
                    f"Measure-Object -Property WorkingSet64,VM,CPU -Sum | "
                    f"ForEach-Object {{ "
                    f"  '{0} {1} {2}' -f "
                    f"  [math]::Round($_.Sum[0]/1MB,1), "
                    f"  [math]::Round($_.Sum[1]/1MB,1), "
                    f"  [math]::Round($_.Sum[2],1) "
                    f"}})",
                    timeout=10,
                )
                if ok and out.strip():
                    parts = out.strip().split()
                    if len(parts) >= 2:
                        return {
                            "rss_mb": float(parts[0]) if parts[0] != "0" else 0,
                            "vms_mb": float(parts[1]) if len(parts) > 1 else 0,
                            "cpu_pct": float(parts[2]) if len(parts) > 2 else 0,
                        }

            elif runtime == "docker":
                out, ok = _run_cmd(
                    f"docker stats --no-stream --format "
                    f"\"{{{{.MemUsage}}}} {{{{.CPUPerc}}}}\" "
                    f"$(docker ps --filter \"name=redis|sentinel\" -q) 2>nul",
                    timeout=10,
                )
                if ok and out.strip():
                    total_rss = 0.0
                    total_cpu = 0.0
                    for line in out.strip().split("\n"):
                        parts = line.split()
                        if parts:
                            # MemUsage is like "50MiB / 1GiB"
                            mem_str = parts[0].replace("MiB", "").replace("GiB", "*1024")
                            try:
                                total_rss += float(eval(mem_str) if "*" in mem_str else mem_str)
                            except Exception:
                                pass
                            if len(parts) > 1:
                                try:
                                    total_cpu += float(parts[-1].replace("%", ""))
                                except Exception:
                                    pass
                    return {"rss_mb": round(total_rss, 1), "vms_mb": 0, "cpu_pct": round(total_cpu, 1)}

        except Exception:
            pass
        return None

    def check_limits(self, services: dict = None) -> list[str]:
        """Check if any service exceeds its memory limit. Returns alerts."""
        if services is None:
            services = SERVICES
        alerts = []
        samples = self.sample(services)
        for name, mem in samples.items():
            limit = services.get(name, {}).get("memory_limit_mb")
            if limit and mem.get("rss_mb", 0) > limit:
                alerts.append(
                    f"{name}: {mem['rss_mb']:.0f} MB RSS exceeds limit of {limit} MB"
                )
        return alerts

    def print_memory(self):
        """Print per-service memory snapshot."""
        samples = self.sample()
        if not samples:
            print("  (no memory samples available)")
            return
        print()
        print(f" {'SERVICE':<26} {'RSS':>8} {'VMS':>8} {'CPU%':>6} {'LIMIT':>8} {'ALERT'}")
        print(f" {'-'*26} {'-'*8} {'-'*8} {'-'*6} {'-'*8} {'-'*6}")
        for name in SERVICES:
            mem = samples.get(name, {})
            rss = mem.get("rss_mb", 0)
            vms = mem.get("vms_mb", 0)
            cpu = mem.get("cpu_pct", 0)
            limit = SERVICES[name].get("memory_limit_mb")
            limit_str = f"{limit} MB" if limit else "-"
            alert = c("R", "HIGH") if (limit and rss > limit) else c("G", "ok")
            print(f" {name:<26} {rss:>6.0f} MB {vms:>6.0f} MB {cpu:>5.1f}% {limit_str:>8} {alert}")


# ══════════════════════════════════════════════════════════════
# HEALTH CHECK ENGINE
# ══════════════════════════════════════════════════════════════

def check_health(name: str, cfg: dict) -> bool:
    hc = cfg.get("health", {})
    htype = hc.get("type", "")
    try:
        if htype == "wsl_alive":
            out, ok = _run_wsl("echo ALIVE", timeout=5)
            return ok and "ALIVE" in out
        elif htype == "tcp":
            s = socket.create_connection(
                (hc.get("host", "127.0.0.1"), hc.get("port", 6379)), timeout=3
            )
            s.close()
            return True
        elif htype == "redis_ping":
            out, ok = _run_wsl(
                f"redis-cli -p {hc.get('port', 6379)} PING 2>/dev/null", timeout=5
            )
            return ok and "PONG" in out
        elif htype == "http":
            import urllib.request
            req = urllib.request.Request(hc.get("url", ""))
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    contains = hc.get("contains")
                    if contains is not None:
                        return contains in resp.read().decode()
                    return True
            return False
        elif htype == "process":
            pattern = hc.get("name", "")
            out, ok = _run_ps(
                f"Get-Process python -ErrorAction SilentlyContinue | "
                f'Where-Object {{$_.CommandLine -like "*{pattern}*"}} | '
                f"Select-Object -First 1 | Measure-Object | %{{$_.Count}}",
                timeout=10,
            )
            return ok and out.strip() not in ("", "0")
        else:
            return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# SERVICE LAUNCHER
# ══════════════════════════════════════════════════════════════

def launch_service(name: str, cfg: dict) -> bool:
    runtime = cfg.get("runtime", "windows")
    command = cfg.get("command", "")
    cwd = cfg.get("cwd")
    try:
        if runtime == "windows":
            _run_ps(command, timeout=20)
        elif runtime == "docker":
            _run_cmd(command, timeout=60, cwd=cwd)
        elif runtime == "wsl":
            _run_wsl(command, timeout=30)
        return True
    except Exception as e:
        log("\u2717", name, f"Launch failed: {e}", "R")
        return False


def wait_for_healthy(name: str, cfg: dict, routes: "RoutingTable" = None) -> bool:
    deadline = time.time() + cfg.get("startup_timeout", 60)
    delay = 0.5
    while time.time() < deadline:
        if check_health(name, cfg):
            if routes:
                routes.update_status(name, "healthy")
            return True
        sys.stdout.write(c("D", "."))
        sys.stdout.flush()
        time.sleep(min(delay, 2))
        delay = min(delay * 1.5, 5)
    return False


# ══════════════════════════════════════════════════════════════
# COMMAND IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════

def cmd_start():
    """Full stack launch with pre-flight checks, DAG, parallel tiers."""
    ports = PortManager()
    resources = ResourceTracker()
    routes = RoutingTable()

    # ── Pre-flight checks ──
    print()
    print(c("B", "\u2501" * 60))
    print(c("C", "  AKASHIC AURORA — Full Orchestrated Launch"))
    print(c("B", "\u2501" * 60))

    # 1. Port conflict check
    print()
    log("\u25b6", "port-manager", "Checking port allocation...", "C")
    conflicts = ports.detect_conflicts()
    if conflicts:
        for conflict in conflicts:
            log("\u2717", "port-manager", conflict, "R")
        print(c("R", "\n  [ABORT] Fix port conflicts before launching."))
        sys.exit(1)
    log("\u2713", "port-manager", f"No conflicts across {len(SERVICES)} services", "G")

    # 2. Resource capacity check
    log("\u25b6", "resource-mgr", "Checking system capacity...", "C")
    warnings = resources.check_capacity()
    for w in warnings:
        log("\u26a0", "resource-mgr", w, "Y")
    if not warnings:
        log("\u2713", "resource-mgr", "Sufficient resources available", "G")

    # 3. Host port scan
    in_use = ports.scan_host_ports()
    stale = [(p, s) for p, s in in_use.items() if s == "IN USE"]
    if stale:
        log("\u26a0", "port-manager",
            f"Some ports already in use: {', '.join(str(p) for p, _ in stale)}", "Y")

    # 4. Sync routing table
    routes.sync_from_config()

    # ── Launch tiers ──
    tiers = resolve_tiers()
    print()
    print(c("M", f"  Launching {len(SERVICES)} services across {len(tiers)} tiers..."))

    stats = {"healthy": 0, "failed": 0, "skipped": 0}

    for i, tier in enumerate(tiers):
        tier_label = ", ".join(sorted(tier))
        print()
        print(c("M", f"\u2500\u2500 Tier {i}: {tier_label} \u2500\u2500"))

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(_launch_one, name, SERVICES[name], routes): name
                for name in tier
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    if result:
                        # Register endpoint in routing table
                        cfg = SERVICES[name]
                        ep = cfg.get("endpoint")
                        if ep:
                            routes.register(
                                name, ep.get("host", "127.0.0.1"),
                                ep.get("port", 0), ep.get("protocol", "tcp"),
                                status="healthy",
                            )
                        stats["healthy"] += 1
                    else:
                        stats["failed"] += 1
                except Exception as e:
                    log("\u2717", name, f"Exception: {e}", "R")
                    stats["failed"] += 1

    # Sync port registry to Redis
    ports.sync_to_redis()

    # ── Final summary ──
    print()
    print(c("B", "\u2501" * 60))
    sc = "G" if stats["failed"] == 0 else "Y"
    print(c(sc, f"  LAUNCH COMPLETE: {stats['healthy']} healthy, {stats['failed']} failed"))
    print(c("B", "\u2501" * 60))
    print()
    cmd_status()

    if stats["failed"] > 0:
        sys.exit(1)


def _launch_one(name: str, cfg: dict, routes: "RoutingTable" = None) -> bool:
    log("\u25b6", name, f"Starting ({cfg['description']})...", "C")
    launch_service(name, cfg)
    log("\u23f3", name, "Waiting for health check...", "Y")
    healthy = wait_for_healthy(name, cfg, routes)
    if healthy:
        log("\u2713", name, "Healthy", "G")
    else:
        log("\u2717", name, "Unhealthy after timeout", "R")
    return healthy


def cmd_status():
    """Show status of all services + resources + memory."""
    ports = PortManager()
    resources = ResourceTracker()
    memory = MemoryMonitor()
    routes = RoutingTable()

    print()
    print(c("B", "\u2501" * 60))
    print(c("C", "  STACK STATUS"))
    print(c("B", "\u2501" * 60))

    # Service health
    print()
    print(f" {'SERVICE':<24} {'HEALTH':<12} {'DESCRIPTION'}")
    print(f" {'-'*24} {'-'*12} {'-'*35}")
    for name, cfg in SERVICES.items():
        healthy = check_health(name, cfg)
        status_str = c("G", "  HEALTHY  ") if healthy else c("R", "  DOWN     ")
        print(f" {name:<24} {status_str}     {cfg['description']}")

    # Resources
    resources.print_resources()

    # Memory
    memory.print_memory()

    # Routing table
    routes.print_routes()


def cmd_stop():
    """Stop all services in reverse dependency order."""
    tiers = resolve_tiers()
    all_names = []
    for tier in tiers:
        all_names.extend(sorted(tier))
    all_names.reverse()

    print()
    print(c("Y", "\u2501" * 60))
    print(c("Y", "  STOPPING ALL SERVICES"))
    print(c("Y", "\u2501" * 60))

    for name in all_names:
        cfg = SERVICES[name]
        stop_cmd = cfg.get("stop", "")
        if stop_cmd:
            runtime = cfg.get("runtime", "")
            try:
                if runtime == "wsl":
                    out, ok = _run_wsl(stop_cmd, timeout=10)
                else:
                    out, ok = _run_ps(stop_cmd, timeout=10)
                icon = "\u2713" if ok else "\u26a0"
                log(icon, name, "Stopped", "G" if ok else "Y")
            except Exception as e:
                log("\u2717", name, f"Stop error: {e}", "R")
        else:
            log("\u25cb", name, "No stop command (terminated with WSL)", "D")

    # Unregister from routing
    routes = RoutingTable()
    for name in all_names:
        routes.unregister(name)

    # Terminate WSL
    log("\u25b6", "wsl-global", "Terminating WSL VM...", "Y")
    subprocess.run(["wsl", "--terminate", "Ubuntu-Migrate"], capture_output=True, timeout=15)
    log("\u2713", "wsl-global", "WSL terminated", "G")

    # Stop Docker
    docker_stop = SERVICES.get("docker-redis", {}).get("stop", "")
    if docker_stop:
        log("\u25b6", "docker-global", "Stopping Docker containers...", "Y")
        subprocess.run(
            docker_stop, shell=True, capture_output=True, timeout=30,
            cwd=r"E:\AI-Setup\dockerized-ai\redis",
        )
        log("\u2713", "docker-global", "Docker containers stopped", "G")

    print()
    log("\u2713", "ALL", "Stack stopped", "G")


def cmd_monitor():
    """Launch then continuously monitor health, memory, and auto-restart."""
    print()
    print(c("C", "  MONITOR MODE — Continuous health + memory watchdog"))
    print(c("C", "  Press Ctrl+C to stop"))
    cmd_start()

    memory = MemoryMonitor()
    routes = RoutingTable()
    fail_counts = defaultdict(int)
    interval = 10

    print()
    print(c("M", f"  [Watchdog active — checking every {interval}s]"))
    print(c("D", "  (. = healthy  ! = restarting  M = memory alert)"))

    while True:
        try:
            time.sleep(interval)
            for name, cfg in SERVICES.items():
                if not check_health(name, cfg):
                    fail_counts[name] += 1
                    log("!", name, f"Down (fail #{fail_counts[name]}) — restarting...", "R")
                    launch_service(name, cfg)
                    routes.update_status(name, "starting")
                    if wait_for_healthy(name, cfg, routes):
                        log("\u2713", name, "Recovered", "G")
                        fail_counts[name] = 0
                    else:
                        log("\u2717", name, "Recovery FAILED", "R")
                        routes.update_status(name, "failed")
                else:
                    sys.stdout.write(c("D", "."))
                    sys.stdout.flush()

            # Memory check
            alerts = memory.check_limits()
            for alert in alerts:
                log("M", "memory-alert", alert, "R")

        except KeyboardInterrupt:
            print()
            log("\u25a0", "MONITOR", "Shutdown requested", "Y")
            break

    cmd_stop()


def cmd_restart(name: str):
    """Restart a single service."""
    if name not in SERVICES:
        print(f"Unknown service: {name}")
        print(f"Available: {', '.join(SERVICES)}")
        return
    cfg = SERVICES[name]
    routes = RoutingTable()

    log("\u25b6", name, f"Restarting ({cfg['description']})...", "C")
    stop_cmd = cfg.get("stop", "")
    if stop_cmd:
        runtime = cfg.get("runtime", "")
        if runtime == "wsl":
            _run_wsl(stop_cmd, timeout=10)
        else:
            _run_ps(stop_cmd, timeout=10)
        time.sleep(1)
    routes.update_status(name, "restarting")
    launch_service(name, cfg)
    if wait_for_healthy(name, cfg, routes):
        log("\u2713", name, "Restarted successfully", "G")
    else:
        log("\u2717", name, "Restart failed", "R")


def cmd_ports():
    """Show port allocation map."""
    ports = PortManager()
    print()
    print(c("B", "\u2501" * 60))
    print(c("C", "  PORT ALLOCATION MAP"))
    print(c("B", "\u2501" * 60))
    ports.print_map()

    print()
    print(c("D", "  Host port scan:"))
    in_use = ports.scan_host_ports()
    for port, status in sorted(in_use.items()):
        sc = "G" if status == "IN USE" else "D"
        print(f"    {port:<6} {c(sc, status)}")


def cmd_routes():
    """Show service routing table."""
    routes = RoutingTable()
    print()
    print(c("B", "\u2501" * 60))
    print(c("C", "  SERVICE ROUTING TABLE (Redis-backed service discovery)"))
    print(c("B", "\u2501" * 60))
    routes.print_routes()


def cmd_resources():
    """Show system resource overview."""
    resources = ResourceTracker()
    resources.print_resources()


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

COMMANDS = {
    "start":     (cmd_start,     "Launch the full stack (pre-flight + DAG + parallel)"),
    "stop":      (cmd_stop,      "Stop all services in reverse dependency order"),
    "status":    (cmd_status,    "Show service health, resources, memory, routes"),
    "monitor":   (cmd_monitor,   "Start + continuous health/memory watchdog"),
    "restart":   ("args",        "Restart a specific service by name"),
    "ports":     (cmd_ports,     "Show port allocation map + host scan"),
    "routes":    (cmd_routes,    "Show service routing / discovery table"),
    "resources": (cmd_resources, "Show system resource overview"),
}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("Commands:")
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:<14} {desc}")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "restart":
        if len(sys.argv) < 3:
            print("Usage: python stack_manager.py restart <service-name>")
            sys.exit(1)
        cmd_restart(sys.argv[2])
    elif cmd in COMMANDS:
        handler = COMMANDS[cmd][0]
        if callable(handler):
            handler()
    else:
        print(f"Unknown command: {cmd}")
        print(f"Commands: {', '.join(COMMANDS)}")


if __name__ == "__main__":
    main()
