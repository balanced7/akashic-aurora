"""Redis client for orchestrator sidecars — uses WSL master from ``config.get_redis_config()``."""

from __future__ import annotations


def get_master_redis():
    try:
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        import redis as redis_lib

        from config import get_redis_config

        r = redis_lib.Redis(**get_redis_config())
        r.ping()
        return r
    except Exception:
        return None
