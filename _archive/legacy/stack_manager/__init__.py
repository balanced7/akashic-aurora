"""
stack_manager — Akashic Aurora Orchestrator
===============================================
Modular process supervisor, service discovery, resource tracker,
and network mapper across Windows, WSL2, and Docker.

Package structure:
  config.py    — Service definitions (ports, deps, health, resources)
  dag.py       — DAG resolver (topological sort → parallel launch tiers)
  launcher.py  — Process launcher (wsl/docker/windows subprocess)
  health.py    — Health check engine (TCP/HTTP/Redis/Process/WSL)
  ports.py     — PortManager (allocation, conflict detection, registry)
  routing.py   — RoutingTable (Redis-backed service discovery)
  resources.py — ResourceTracker (CPU/GPU/RAM/WSL memory)
  memory.py    — MemoryMonitor (per-service RSS/VMS tracking)
  cli.py       — CLI commands (start/stop/status/monitor)
"""

from datetime import datetime

from .config import SERVICES
from .dag import resolve_tiers
from .health import check_health
from .launcher import _run_cmd, _run_powershell, _run_wsl, launch_service, wait_for_healthy
from .ports import PortManager
from .routing import RoutingTable
from .resources import ResourceTracker
from .memory import MemoryMonitor

# Aliases for ``stack_gui.py`` (legacy import surface)
_run_ps = _run_powershell

_C = {
    "R": "\033[91m",
    "G": "\033[92m",
    "Y": "\033[93m",
    "B": "\033[94m",
    "C": "\033[96m",
    "M": "\033[95m",
    "W": "\033[97m",
    "X": "\033[0m",
    "D": "\033[90m",
}


def c(color: str, text: str) -> str:
    return f"{_C.get(color, '')}{text}{_C['X']}"


def log(icon: str, name: str, msg: str, color: str = "W"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f" {c('D', ts)} {icon} {c(color, name):<28} {msg}")
