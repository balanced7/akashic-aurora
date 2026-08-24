"""
RoutingTable — Redis-backed service discovery.
Stores service endpoints so any tool can discover services dynamically.
"""

import json
from datetime import datetime


def _redis():
    from .redis_util import get_master_redis

    return get_master_redis()


class RoutingTable:
    PREFIX = "service"
    ROUTING_KEY = "service:routing"

    def register(self, name: str, host: str, port: int, protocol: str, status: str = "starting"):
        r = _redis()
        if not r:
            return
        key = f"{self.PREFIX}:{name}:endpoint"
        mapping = {
            "host": host, "port": str(port), "protocol": protocol,
            "status": status, "updated_at": datetime.now().isoformat(),
        }
        r.hset(key, mapping=mapping)
        r.hset(self.ROUTING_KEY, name, json.dumps(mapping))

    def update_status(self, name: str, status: str):
        r = _redis()
        if not r:
            return
        key = f"{self.PREFIX}:{name}:endpoint"
        r.hset(key, "status", status)
        r.hset(key, "updated_at", datetime.now().isoformat())
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
        r = _redis()
        if not r:
            return
        r.delete(f"{self.PREFIX}:{name}:endpoint")
        r.hdel(self.ROUTING_KEY, name)

    def discover(self, name: str) -> dict | None:
        r = _redis()
        if not r:
            return None
        data = r.hgetall(f"{self.PREFIX}:{name}:endpoint")
        return data if data else None

    def list_all(self) -> dict:
        r = _redis()
        if not r:
            return {}
        raw = r.hgetall(self.ROUTING_KEY)
        return {k: json.loads(v) for k, v in raw.items()}

    def sync_from_config(self, services: dict = None):
        if services is None:
            from .config import SERVICES as services
        for name, cfg in services.items():
            ep = cfg.get("endpoint")
            if ep:
                self.register(
                    name, ep.get("host", "127.0.0.1"),
                    ep.get("port", 0), ep.get("protocol", "tcp"),
                    status="defined",
                )
