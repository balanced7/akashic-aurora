"""AXI bench spec: `link` -- fleet links: the read paths and the offline write actions.

Needs the aurora-linkd binary (AURORA_LINKD, PATH, or a dev build in aurora-rs/target). Every
action here is offline: the CLI starts a one-shot daemon child against the sandbox's data root.
Nothing serves, joins, syncs or touches the network: create, invite (a code, nobody joins),
verify, export and import (into a temporary folder), policy, rebuild and cert are all local.

The device identity lives in the secrets folder, not the data root, so the sandbox reset between
the two sides would not clear it and a second `link init` would be refused. This module therefore
makes one throwaway identity in a temporary secrets folder when it is loaded (AKASHIC_SECRETS_DIR,
which every run inherits), and the seed only creates links. Without aurora-linkd every run prints
the missing-daemon error instead, and the seed fails loudly.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_secrets = tempfile.mkdtemp(prefix="axi-link-secrets-")
_files = tempfile.mkdtemp(prefix="axi-link-files-")  # bundles and certificates the runs write
os.environ["AKASHIC_SECRETS_DIR"] = _secrets
subprocess.run(
    [sys.executable, str(ROOT / "agent_cli.py"), "link", "init", "--label", "benchfleet"],
    cwd=ROOT,
    env={
        **os.environ,
        "AI_SETUP": tempfile.mkdtemp(prefix="axi-link-home-"),
        "HOME": _secrets,
        # init never reads the bus; a sandbox db all the same (the bench's own default)
        "REDIS_DB": os.environ.get("REDIS_DB") or "15",
    },
    stdin=subprocess.DEVNULL,
    capture_output=True,  # the recovery phrase is printed once; it goes nowhere
    check=False,
)

VERB = "link"
SEED = [
    ["link", "create", "teamlink"],
    ["link", "create", "opslink", "--retention-days", "30"],
]
RUNS = {
    "list": ["link", "list"],
    "status": ["link", "status", "teamlink"],
    "whoami": ["link", "whoami"],
    "inbox": ["link", "inbox", "teamlink"],
    "usage": ["link", "inbox"],
    # The write actions run after the read paths, in this order, on the same seeded store.
    "create": ["link", "create", "newlink"],
    "invite": ["link", "invite", "teamlink", "--role", "reader", "--ttl", "2h", "--approval"],
    "verify": ["link", "verify", "teamlink"],
    "export": ["link", "export", "teamlink", "--out", f"{_files}/bundle.json"],
    "import": ["link", "import", f"{_files}/bundle.json"],
    "policy": ["link", "policy", "opslink"],
    "rebuild": ["link", "rebuild", "teamlink"],
    "cert": ["link", "cert", "--out", f"{_files}/cert.json"],
}
EMPTY = ["link", "list"]
QUESTIONS = [
    {"run": "list", "q": "How many links does this fleet have?", "a": 2, "grade": "number"},
    {"run": "list", "q": "What is our role in the link opslink?", "a": "owner", "grade": "exact"},
    {
        "run": "status",
        "q": "What is the label of our own fleet in the link teamlink?",
        "a": "benchfleet",
        "grade": "exact",
    },
    {
        "run": "status",
        "q": "How many records wait unpromoted in teamlink's quarantine?",
        "a": 0,
        "grade": "number",
    },
    {"run": "whoami", "q": "What is this device's label?", "a": "benchfleet", "grade": "exact"},
    {"run": "inbox", "q": "How many records are in teamlink's quarantine?", "a": 0, "grade": "number"},
    {"run": "usage", "q": "Did the command succeed? Answer yes or no.", "a": "no", "grade": "exact"},
    {
        "run": "create",
        "q": "What is the exact command to invite someone into the link that was just created?",
        "a": "link invite newlink",
        "grade": "contains",
    },
    {"run": "invite", "q": "What role does someone joining with this invite get?", "a": "reader", "grade": "exact"},
    {
        "run": "invite",
        "q": "Must the inviter approve the join after they join? Answer yes or no.",
        "a": "yes",
        "grade": "exact",
    },
    {"run": "verify", "q": "How many other fleets' safety numbers are listed?", "a": 0, "grade": "number"},
    {"run": "export", "q": "How many ACL entries went into the bundle?", "a": 2, "grade": "number"},
    {"run": "import", "q": "How many records did the import refuse?", "a": 0, "grade": "number"},
    {
        "run": "policy",
        "q": "Are these policy files synced to the link's other members? Answer yes or no.",
        "a": "no",
        "grade": "exact",
    },
    {
        "run": "cert",
        "q": "What is the file name the certificate was written to?",
        "a": "cert.json",
        "grade": "contains",
    },
]
