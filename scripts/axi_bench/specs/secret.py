"""AXI bench spec: `secret` -- the vault listing (sizes only) and its error path.

The capture path (a popup window, or a value piped on stdin) is never run: it writes a credential.
The vault folder is AKASHIC_SECRETS_DIR, outside the sandbox reset, so this module makes a
temporary one holding two fake credentials when it is loaded, and every run inherits it. There
is no empty-state run for the same reason.
"""

import os
import tempfile
from pathlib import Path

from core.comm.secret_intake import TARGETS

_vault = Path(tempfile.mkdtemp(prefix="axi-secret-"))
(_vault / "openai.key").write_text("x" * 51, encoding="utf-8")
(_vault / "gemini.key").write_text("y" * 39, encoding="utf-8")
os.environ["AKASHIC_SECRETS_DIR"] = str(_vault)

VERB = "secret"
SEED = []
RUNS = {
    "list": ["secret"],
    "unknown": ["secret", "nope.key"],
}
EMPTY = None
QUESTIONS = [
    {"run": "list", "q": "How many credentials are present in the vault?", "a": 2, "grade": "number"},
    {"run": "list", "q": "How many bytes does openai.key hold?", "a": 51, "grade": "number"},
    {"run": "list", "q": "Is deepseek.key present in the vault? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "list",
        "q": "How many credential names does the vault accept in total?",
        "a": len(TARGETS),
        "grade": "number",
    },
    {
        "run": "list",
        "q": "What command captures kimi.key into the vault? Give the command only.",
        "a": ["secret kimi.key"],
        "grade": "contains",
    },
    {"run": "unknown", "q": "Did the command succeed? Answer yes or no.", "a": "no", "grade": "exact"},
]
