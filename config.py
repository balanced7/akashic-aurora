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
#   87 9x  = BETA                 (E:\AI-Setup-Beta -- longer-form integration)
#   88 0x  = ALPHA                (E:\AI-Setup-Alpha -- risky work, discardable by design)
#   89 xx  = TEST / EPHEMERAL UIs (throwaway; may run many at once; never touches prod)
# Redis mirrors the same worlds: 16379 prod / 16380 beta / 16381 alpha; db 15 = test.
#
# WHICH world a given PROCESS is in is decided by core/world.py, NOT by editing these
# constants per checkout. That distinction is the W156 slice: this file DECLARES what
# exists (shared, tracked, flows to every world); `.aurora-world` DECLARES WHO YOU ARE
# (per-checkout, untracked). The July 2026 sandbox conflated them -- it edited REDIS_PORT
# here to isolate itself -- and so its isolation was a permanent merge conflict on the
# most-imported file in the repo. It never got refreshed. Do not re-learn that.
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

# --- BETA (879x) -- E:\AI-Setup-Beta, longer-form integration; prod's waiting room ---
# Renamed from SANDBOX 2026-08-14 (W156). Same band, same ports, new name: the world
# gained a sibling, and "sandbox" stopped describing a TIER once there were two of them.
# `core.world.ALIASES` maps sandbox->beta so old docs and the July clone still resolve.
PORT_UI_BETA = 8790         # beta console
REDIS_PORT_BETA = 16380     # beta Redis (isolated from prod 16379)
PORT_UI_SANDBOX = PORT_UI_BETA          # lineage alias; prefer the BETA names
REDIS_PORT_SANDBOX = REDIS_PORT_BETA    # lineage alias; prefer the BETA names

# --- ALPHA (880x) -- E:\AI-Setup-Alpha, risky work; discardable by design ---
PORT_UI_ALPHA = 8800        # alpha console
REDIS_PORT_ALPHA = 16381    # alpha Redis (isolated from prod 16379 and beta 16380)

# --- TEST / EPHEMERAL UIs (89xx) -- the dedicated throwaway band ---
PORT_TEST_UI_BASE = 8900    # first test-UI port; allocate upward (8900, 8901, ...).
PORT_TEST_UI_MAX = 8999     # last test-UI port. A test UI MUST live in [8900, 8999].

# --- THE REGISTRY (T266) -- the constants above, as DATA a checker can read ---
#
# WHY THIS EXISTS AS DATA. docs/PORTS.md was the ONE hand-written map in a repo that
# generates PHYSICS.md, DOORS.md, MAP.md, MODULE_INDEX.md and PRIOR_ART.md from live state on
# every commit -- and it was the one that drifted. Measured 2026-08-10: every CONTAINER port
# (11434 ollama, 8888 searxng, 3000 open-webui, 5000/5001 voice) was ABSENT, because the doc
# described what PYTHON binds and was blind to what CONTAINERS bind. Worse, it listed 8080
# under "legacy/inactive -- never live" while ai-knowledge-api was bound to 8080 until it was
# removed that morning. A map that asserts DEAD about something RUNNING is worse than a map
# with a hole, because it is trusted. Daniil: "so we don't have to guess as to how things are
# built and routed."
#
# `bound_by` is the field the old doc could not express and the reason the gap was invisible:
#   app       -- a Python process in this repo opens it (grep-able, checkable against source)
#   container -- docker publishes it; NO source literal will ever mention it
#   external  -- neither; a service we merely coexist with
#
# NOT A REDESIGN. The 878x/879x/89xx band rules and config-wins-over-doc precedence are
# unchanged; this slice extends the schema's REACH to the plane it could not see.
PORT_REGISTRY = {
    PORT_UI:            {"world": "prod",     "bound_by": "app",
                         "what": "Bifrost live agent console",
                         "owner": "scripts/bifrost_ui.py"},
    PORT_UI_RESERVED:   {"world": "prod",     "bound_by": "app",
                         "what": "RESERVED prod-aux -- NOT the console; do not bind",
                         "owner": "(reserved)"},
    PORT_MCP_HTTP:      {"world": "prod",     "bound_by": "app",
                         "what": "MCP HTTP mode (stdio is the default, so usually silent)",
                         "owner": "ai_setup_mcp.py"},
    REDIS_PORT:         {"world": "prod",     "bound_by": "container",
                         "what": "canonical knowledge store + bus (db 0 prod / db 15 test)",
                         "owner": "akashic-redis"},
    PORT_UI_BETA:       {"world": "beta",     "bound_by": "app",
                         "what": "beta console (was: sandbox)",
                         "owner": "E:/AI-Setup-Beta scripts/bifrost_ui.py"},
    REDIS_PORT_BETA:    {"world": "beta",     "bound_by": "container",
                         "what": "beta Redis, isolated from prod and alpha",
                         "owner": "akashic-redis-beta"},
    PORT_UI_ALPHA:      {"world": "alpha",    "bound_by": "app",
                         "what": "alpha console",
                         "owner": "E:/AI-Setup-Alpha scripts/bifrost_ui.py"},
    REDIS_PORT_ALPHA:   {"world": "alpha",    "bound_by": "container",
                         "what": "alpha Redis, isolated from prod and beta",
                         "owner": "akashic-redis-alpha"},
    # The container plane -- invisible to any source grep, which is exactly why it went
    # undocumented and why "which of these do we need?" could not be answered from a map.
    11434:              {"world": "prod",     "bound_by": "container",
                         "what": "local model lane; core/fleet/caller.py calls /api/generate",
                         "owner": "ai-ollama"},
    8888:               {"world": "prod",     "bound_by": "container",
                         "what": "the fleet's ONLY web-search door (loopback only)",
                         "owner": "akashic-searxng / scripts/local/websearch.py"},
    3000:               {"world": "external", "bound_by": "container",
                         "what": "human chat front-end over the same ollama; no live repo refs",
                         "owner": "ai-open-webui"},
    5000:               {"world": "external", "bound_by": "container",
                         "what": "voice service; no live repo refs",
                         "owner": "ai-voice"},
    5001:               {"world": "external", "bound_by": "container",
                         "what": "voice service (second port)",
                         "owner": "ai-voice"},
    # Found by check_ports on its FIRST run, and it was live-broken rather than merely
    # undocumented: model_roster's default_host said 11435, nothing listens there, and a real
    # call to an installed model failed with WinError 10061. Registering the port is what
    # makes the off-by-one visible; the fix was pointing it at the ollama that exists.
    47100:              {"world": "prod",     "bound_by": "app",
                         "what": "runner control-channel BASE; each seat takes base+n on "
                                 "loopback, so the exact port is dynamic by design",
                         "owner": "core/comm/control_channel.py"},
}

#: Bands, as data rather than prose, so the report can name a port's WORLD from its digits.
PORT_BANDS = (
    (8780, 8789, "prod"),
    (8790, 8799, "beta"),          # renamed from "sandbox" 2026-08-14 (W156)
    (8800, 8809, "alpha"),         # W156: the third world
    (PORT_TEST_UI_BASE, PORT_TEST_UI_MAX, "test"),
)

#: Ports that were live once and must never be silently resurrected. Kept because deleting a
#: retirement makes it re-discoverable as a "free" port by the next person.
PORT_RETIRED = {
    8080: "ai-knowledge-api -- container REMOVED 2026-08-10 (exit 127 for 7 weeks; dead)",
    8000: "vllm-server -- container REMOVED 2026-08-10 (status Created; never ran)",
    6379: "WSL Redis HA replica -- separate lifecycle, not the app endpoint",
    6380: "WSL Redis HA master -- separate lifecycle, not the app endpoint",
}


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

# T313: the transcript archive, declared ONCE because two archives that do not know about each
# other is how ninety sessions went missing. scripts/ops/archive_transcripts.py WRITES here and
# core/eye/index.py READS here; a pin asserts they agree, so a destination added to one side only
# fails loudly instead of opening a silent gap.
#
# Deliberately OUTSIDE the repo: these are UNREDACTED transcripts and the repo is public. Separate
# PHYSICAL disks on purpose -- two copies on one drive is one failure domain wearing a disguise.
TRANSCRIPT_ARCHIVE_ROOTS = [
    Path(r"E:\Akashic Aurora\transcripts\rolling"),
    Path(r"F:\Akashic Aurora\transcripts\rolling"),
]

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
