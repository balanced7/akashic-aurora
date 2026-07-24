"""
Health Check Engine — TCP, HTTP, Redis PING, Process, WSL-alive checks.
"""

import socket
import urllib.request


def _run_wsl(cmd: str, timeout: int = 5) -> tuple:
    import subprocess
    try:
        p = subprocess.run(
            ["wsl", "-d", "Ubuntu-Migrate", "-e", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.stdout.strip(), p.returncode == 0
    except Exception:
        return "", False


def _run_powershell(cmd: str, timeout: int = 10) -> tuple:
    import subprocess
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.stdout.strip(), p.returncode == 0
    except Exception:
        return "", False


def check_health(name: str, config: dict) -> bool:
    """Run the health check for a service. Returns True if healthy."""
    hc = config.get("health", {})
    htype = hc.get("type", "")

    try:
        if htype == "wsl_alive":
            out, ok = _run_wsl("echo ALIVE", timeout=5)
            return ok and "ALIVE" in out

        elif htype == "tcp":
            host = hc.get("host", "127.0.0.1")
            port = hc.get("port", 6379)
            s = socket.create_connection((host, port), timeout=3)
            s.close()
            return True

        elif htype == "redis_ping":
            port = hc.get("port", 6379)
            out, ok = _run_wsl(
                f"redis-cli -p {port} PING 2>/dev/null", timeout=5
            )
            return ok and "PONG" in out

        elif htype == "http":
            url = hc.get("url", "")
            contains = hc.get("contains")
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    if contains is not None:
                        return contains in resp.read().decode()
                    return True
            return False

        elif htype == "process":
            pattern = hc.get("name", "")
            out, ok = _run_powershell(
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
