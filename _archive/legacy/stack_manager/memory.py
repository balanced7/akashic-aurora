"""
MemoryMonitor — Per-service RSS/VMS tracking with limit alerts.
"""

import subprocess
from collections import defaultdict
from datetime import datetime


def _run_wsl(cmd: str, timeout: int = 8) -> tuple:
    try:
        p = subprocess.run(
            ["wsl", "-d", "Ubuntu-Migrate", "-e", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.stdout.strip(), p.returncode == 0
    except Exception:
        return "", False


def _run_powershell(cmd: str, timeout: int = 12) -> tuple:
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return p.stdout.strip(), p.returncode == 0
    except Exception:
        return "", False


def _run_cmd(cmd: str, timeout: int = 10) -> tuple:
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip(), p.returncode == 0
    except Exception:
        return "", False


def _redis():
    from .redis_util import get_master_redis

    return get_master_redis()


class MemoryMonitor:
    def __init__(self):
        self.snapshots: dict[str, list] = defaultdict(list)

    def sample(self, services: dict = None) -> dict[str, dict]:
        if services is None:
            from .config import SERVICES as services
        samples = {}
        for name, cfg in services.items():
            mem = self._sample_one(name, cfg)
            if mem:
                samples[name] = mem
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

    def _sample_one(self, name: str, cfg: dict) -> dict | None:
        runtime = cfg.get("runtime", "")
        patterns = {
            "wsl-redis-ha": "redis-server",
            "docker-edge-redis": "redis-server",
            "docker-ai-voice": "python.*server",
            "gemma-2b": "python.*server\\.py",
        }
        try:
            if runtime == "wsl":
                if name == "wsl-keeper":
                    return None
                pattern = patterns.get(name, name)
                out, ok = _run_wsl(
                    f"ps -eo rss,vsize,pcpu,comm --no-headers 2>/dev/null | "
                    f"grep -E '{pattern}' | grep -v grep | "
                    f"awk '{{rss+=$1; vsize+=$2; cpu+=$3}} END {{print rss, vsize, cpu}}'",
                    timeout=5,
                )
                if ok and out.strip():
                    parts = out.split()
                    return {"rss_mb": round(float(parts[0]) / 1024, 1),
                            "vms_mb": round(float(parts[1]) / 1024, 1) if len(parts) > 1 else 0,
                            "cpu_pct": round(float(parts[2]), 1) if len(parts) > 2 else 0}
            elif runtime == "windows":
                out, ok = _run_powershell(
                    f"(Get-Process -Name 'python' -ErrorAction SilentlyContinue | "
                    f"Where-Object {{$_.CommandLine -like '*{name}*'}} | "
                    f"Measure-Object -Property WorkingSet64,VM,CPU -Sum | "
                    f"ForEach-Object {{ '{0} {1} {2}' -f "
                    f"[math]::Round($_.Sum[0]/1MB,1), [math]::Round($_.Sum[1]/1MB,1), [math]::Round($_.Sum[2],1) }})",
                    timeout=10,
                )
                if ok and out.strip():
                    parts = out.strip().split()
                    if len(parts) >= 2:
                        return {"rss_mb": float(parts[0]) if parts[0] != "0" else 0,
                                "vms_mb": float(parts[1]) if len(parts) > 1 else 0,
                                "cpu_pct": float(parts[2]) if len(parts) > 2 else 0}
            elif runtime == "docker":
                out, ok = _run_cmd(
                    "docker stats --no-stream --format \"{{.MemUsage}} {{.CPUPerc}}\" "
                    "$(docker ps --filter \"name=redis|sentinel\" -q) 2>nul",
                    timeout=10,
                )
                if ok and out.strip():
                    total_rss = 0.0; total_cpu = 0.0
                    for line in out.strip().split("\n"):
                        parts = line.split()
                        if parts:
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
        if services is None:
            from .config import SERVICES as services
        alerts = []
        samples = self.sample(services)
        for name, mem in samples.items():
            limit = services.get(name, {}).get("memory_limit_mb")
            if limit and mem.get("rss_mb", 0) > limit:
                alerts.append(f"{name}: {mem['rss_mb']:.0f} MB RSS exceeds {limit} MB limit")
        return alerts
