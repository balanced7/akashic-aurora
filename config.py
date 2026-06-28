"""
Centralized Configuration - Akashic Aurora
=============================================

Single source of truth for all configuration values.
"""

from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(r"E:\AI-Setup")
COORD_DIR = BASE_DIR / "blackboard_data" / "agent_coordination"
DATA_DIR = BASE_DIR / "data"

# Canonical Redis endpoint (single source of truth; foundation resolves from here).
# Topology resolved 2026-06-20: the live master is the Docker Redis on 16379 — it
# holds the canonical knowledge stores. (The WSL 6379/6380 HA pair is a separate,
# currently-inactive server concern managed by services/redis_ha_manager.py.)
REDIS_HOST = "localhost"
REDIS_PORT = 16379
REDIS_DB = 0          # production logical DB
REDIS_TEST_DB = 15    # tests run here so they NEVER touch canonical data (db 0)
REDIS_TIMEOUT = 5

# Legacy WSL HA pair (separate server lifecycle; not the canonical app endpoint).
REDIS_WSL_MASTER_PORT = 6380
REDIS_WSL_REPLICA_PORT = 6379

REDIS_DOCKER_HOST = "localhost"
REDIS_DOCKER_PORT = 16379

SESSION_LOG_DIR = DATA_DIR / "sessions"
SESSION_LOG_DIR.mkdir(parents=True, exist_ok=True)

BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Canonical agent-agnostic session log (Redis Stream on WSL master)
SESSION_EVENTS_STREAM = "session:events"
SESSION_NOTE_SCHEMA_VERSION = "1"
SESSION_STATE_DIR = BASE_DIR / "blackboard_data"
SESSION_STATE_FILE = SESSION_STATE_DIR / "session_state.json"

# Mirrors stream appends on disk for forensics when Redis fails
LEGACY_JSONL_LOG = BASE_DIR / "session_logs" / "session_all.jsonl"
CANONICAL_EVENTS_JSONL = BASE_DIR / "session_logs" / "session_events_canonical.jsonl"


def get_redis_config():
    return {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": REDIS_DB,
        "decode_responses": True,
        "socket_connect_timeout": REDIS_TIMEOUT
    }


def get_docker_redis_config():
    return {
        "host": REDIS_DOCKER_HOST,
        "port": REDIS_DOCKER_PORT,
        "db": REDIS_DB,
        "decode_responses": True,
        "socket_connect_timeout": REDIS_TIMEOUT
    }
