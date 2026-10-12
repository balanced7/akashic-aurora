"""AXI bench spec: `discord` -- the unconfigured bridge, offline.

`discord send` posts to a real webhook when one is configured, so the bench measures only the
unconfigured state: `status` (the setup steps, exit 0) and a `send` that has no seat lane and no
global webhook to go to (refused before any request). The guard below refuses to load this spec
at all when a webhook is reachable from the bench's environment, so a configured machine can
never turn the bench into a post.
"""

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_vault = Path(os.getenv("AKASHIC_SECRETS_DIR") or (_ROOT / ".secrets"))
if os.getenv("AKASHIC_DISCORD_WEBHOOK") or list(_vault.glob("discord_*.url")):
    raise SystemExit("discord bench refused: a webhook is configured here, and `discord send` would post")

VERB = "discord"
SEED = []
RUNS = {
    "status": ["discord", "status"],
    "send": ["discord", "send", "--text", "hello from the bench"],
}
EMPTY = None
QUESTIONS = [
    {"run": "status", "q": "Is the Discord bridge configured? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "status",
        "q": "What is the file name the webhook URL should be saved to? Give the file name only, not the path.",
        "a": "discord_webhook.url",
        "grade": "contains",
    },
    {
        "run": "status",
        "q": "What exact command posts a test line once the bridge is set up? Give the command only.",
        "a": ["discord test"],
        "grade": "contains",
    },
    {"run": "send", "q": "Was the message sent? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "send",
        "q": "Did the command fail, or succeed? Answer failed or succeeded.",
        "a": "failed",
        "grade": "exact",
    },
]
