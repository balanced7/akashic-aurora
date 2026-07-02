"""
Process Launcher — Start services on Windows, WSL, or Docker.
"""

import subprocess
import time


def _run_wsl(cmd: str, timeout: int = 15) -> tuple:
    """Run a command inside WSL. Returns (stdout, success)."""
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


def _run_powershell(cmd: str, timeout: int = 20) -> tuple:
    """Run a PowerShell command. Returns (stdout, success)."""
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


def _run_cmd(cmd: str, timeout: int = 60, cwd: str = None) -> tuple:
    """Run a shell command. Returns (stdout, success)."""
    try:
        p = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd,
        )
        return p.stdout.strip(), p.returncode == 0
    except Exception:
        return "", False


def launch_service(name: str, config: dict) -> bool:
    """Launch a single service. Returns True if the launch command succeeded."""
    runtime = config.get("runtime", "windows")
    command = config.get("command", "")
    try:
        if runtime == "windows":
            _run_powershell(command, timeout=25)
        elif runtime == "docker":
            _run_cmd(command, timeout=90)
        elif runtime == "wsl":
            _run_wsl(command, timeout=30)
        return True
    except Exception:
        return False


def wait_for_healthy(name: str, config: dict, routes=None) -> bool:
    """Poll health check until healthy or timeout. Uses exponential backoff."""
    from .health import check_health

    deadline = time.time() + config.get("startup_timeout", 60)
    delay = 0.5
    while time.time() < deadline:
        if check_health(name, config):
            if routes:
                routes.update_status(name, "healthy")
            return True
        time.sleep(min(delay, 2))
        delay = min(delay * 1.5, 5)
    return False
