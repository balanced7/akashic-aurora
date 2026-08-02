"""
Centralized Configuration - Akashic Aurora
=============================================

Single source of truth for all configuration values.
"""

from pathlib import Path
from dataclasses import dataclass

# Root DERIVED, never hardcoded: this file previously pinned one machine's absolute
# path, so a copy of the repo anywhere else resolved every path under it to nothing.
from core.paths import repo_root as _repo_root  # noqa: E402
BASE_DIR = _repo_root()
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

# =============================================================================
# PORT REGISTRY -- the single source of truth for what listens where.
# =============================================================================
# THE RULE (read the second digit-pair after 87 to know which world a port is):
#   87 8x  = PRODUCTION bifrost   (the one live fleet; harness-managed; stable forever)
#   87 9x  = SANDBOX              (the persistent E:\AI-Setup-Sandbox clone)
#   89 xx  = TEST / EPHEMERAL UIs (throwaway; may run many at once; never touches prod)
# Redis mirrors the same worlds: 16379 prod / 16380 sandbox / db 15 = test isolation.
#
# Born 2026-07-16 to end the 8787-vs-8788 churn: the console has ALWAYS bound 8787,
# but deepseek_chat.py documented the UI as "8788 (falls back to 8787)", so half the
# fleet looked in the wrong place. 8788 is now RESERVED prod-aux and MUST NOT be used
# as "the UI port". Test UIs get their own 89xx band so a stray test can never collide
# with the live console again.

# --- PRODUCTION (878x) -- the one live fleet ---
PORT_UI = 8787              # Bifrost live agent console (scripts/bifrost_ui.py). CANONICAL.
PORT_UI_RESERVED = 8788     # RESERVED prod-aux. NOT the console. Do not bind for tests.
PORT_MCP_HTTP = 18765       # ai_setup_mcp.py optional --http mode (MCP is stdio by default).

# --- SANDBOX (879x) -- E:\AI-Setup-Sandbox persistent clone ---
PORT_UI_SANDBOX = 8790      # sandbox console
REDIS_PORT_SANDBOX = 16380  # sandbox Redis (isolated from prod 16379)

# --- TEST / EPHEMERAL UIs (89xx) -- the dedicated throwaway band ---
PORT_TEST_UI_BASE = 8900    # first test-UI port; allocate upward (8900, 8901, ...).
PORT_TEST_UI_MAX = 8999     # last test-UI port. A test UI MUST live in [8900, 8999].


def allocate_test_ui_port(offset: int = 0) -> int:
    """Return a port in the reserved test-UI band [8900, 8999].

    Test/throwaway UIs MUST use this instead of hardcoding a port, so an
    ephemeral test can never collide with the live console (8787) or sandbox (8790).
    """
    port = PORT_TEST_UI_BASE + int(offset)
    if not (PORT_TEST_UI_BASE <= port <= PORT_TEST_UI_MAX):
        raise ValueError(
            f"test UI port {port} is outside the reserved band "
            f"[{PORT_TEST_UI_BASE}, {PORT_TEST_UI_MAX}] -- offset {offset} too large"
        )
    return port


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
