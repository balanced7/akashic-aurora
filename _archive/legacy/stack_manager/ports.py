"""
PortManager — Port allocation, conflict detection, host scanning, Redis registry.
"""

import socket
from collections import defaultdict
from datetime import datetime


def _redis():
    from .redis_util import get_master_redis

    return get_master_redis()


class PortManager:
    def scan_services(self, services: dict = None) -> dict[str, list[int]]:
        """Extract port assignments from service configs."""
        if services is None:
            from .config import SERVICES as services
        result = {}
        for name, cfg in services.items():
            ports = cfg.get("ports", [])
            if ports:
                result[name] = sorted(ports)
        return result

    def detect_conflicts(self, services: dict = None) -> list[str]:
        """Check for port conflicts. Same-runtime conflicts are real errors."""
        if services is None:
            from .config import SERVICES as services
        port_to_services = defaultdict(list)
        for name, cfg in services.items():
            for port in cfg.get("ports", []):
                port_to_services[port].append(name)

        conflicts = []
        for port, names in port_to_services.items():
            if len(names) > 1:
                runtimes = {services[n].get("runtime", "") for n in names}
                if len(runtimes) == 1:
                    conflicts.append(
                        f"Port {port}: {', '.join(names)} (same runtime={list(runtimes)[0]})"
                    )
        return conflicts

    def check_port_in_use(self, port: int, host: str = "127.0.0.1") -> bool:
        try:
            s = socket.create_connection((host, port), timeout=2)
            s.close()
            return True
        except Exception:
            return False

    def scan_host_ports(self) -> dict[int, str]:
        seen = set()
        in_use = {}
        from .config import SERVICES
        for cfg in SERVICES.values():
            for port in cfg.get("ports", []):
                if port not in seen:
                    seen.add(port)
                    in_use[port] = "IN USE" if self.check_port_in_use(port) else "free"
        return in_use

    def sync_to_redis(self):
        r = _redis()
        if not r:
            return
        now = datetime.now().isoformat()
        from .config import SERVICES
        for name, cfg in SERVICES.items():
            ports = cfg.get("ports", [])
            endpoint = cfg.get("endpoint", {})
            for port in ports:
                key = f"port:{name.replace('-', '_')}"
                if port != (endpoint.get("port") or (ports[0] if ports else None)):
                    key = f"port:{name.replace('-', '_')}_{port}"
                r.hset(key, mapping={
                    "port": str(port),
                    "protocol": endpoint.get("protocol", "tcp"),
                    "description": cfg["description"],
                    "service": name,
                    "updated_at": now,
                })
