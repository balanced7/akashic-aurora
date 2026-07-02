"""
ResourceTracker — CPU, GPU VRAM, RAM, WSL memory, RAM disk monitoring.
"""

import json
import shutil
import subprocess


def _run_wsl(cmd: str, timeout: int = 8) -> tuple:
    try:
        p = subprocess.run(
            ["wsl", "-d", "Ubuntu-Migrate", "-e", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.stdout.strip(), p.returncode == 0
    except Exception:
        return "", False


class ResourceTracker:
    def system_info(self) -> dict:
        import psutil
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
                info["disk_free_gb"][part.mountpoint] = usage.free // (1024 ** 3)
            except Exception:
                pass
        return info

    def wsl_memory_mb(self) -> int | None:
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
        out, ok = _run_wsl(
            "source /etc/profile.d/rocm.sh 2>/dev/null; "
            "rocm-smi --showmeminfo vram --json 2>/dev/null || echo '{}'",
            timeout=10,
        )
        if ok and out:
            try:
                return json.loads(out)
            except Exception:
                pass
        return None

    def ram_disk_usage(self) -> dict:
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
        if services is None:
            from .config import SERVICES as services
        sysinfo = self.system_info()
        total_cpu = sum(cfg.get("resources", {}).get("cpu_cores", 0) for cfg in services.values())
        total_ram = sum(cfg.get("resources", {}).get("ram_mb", 0) for cfg in services.values())

        warnings = []
        if total_cpu > sysinfo["cpu_cores_logical"] * 0.85:
            warnings.append(f"CPU overallocation: {total_cpu:.0f} requested vs {sysinfo['cpu_cores_logical']} available")
        if total_ram > sysinfo["ram_available_mb"]:
            warnings.append(f"RAM overallocation: {total_ram} MB requested vs {sysinfo['ram_available_mb']} MB available")
        return warnings
