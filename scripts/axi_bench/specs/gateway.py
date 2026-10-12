"""AXI bench spec: `gateway` -- the inbound Discord ear's status, read-only.

`gateway restart` kills and relaunches a process, so the bench runs only `status`, which reads
the process table. The expected answers assume no Discord gateway runs on the bench machine (the
spec refuses to load if one does, rather than measure a different state on each side).
"""

import subprocess

try:
    _ps = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True, timeout=10).stdout
except Exception:  # no ps: let the run measure what it measures
    _ps = ""
if "bifrost_runner_discord.py" in _ps.replace("ps -eo args", ""):
    raise SystemExit("gateway bench refused: a Discord gateway is running here, and the answers assume none")

VERB = "gateway"
SEED = []
RUNS = {"status": ["gateway", "status"]}
EMPTY = None
QUESTIONS = [
    {"run": "status", "q": "Is the Discord gateway running? Answer yes or no.", "a": "no", "grade": "exact"},
    {"run": "status", "q": "How many gateway processes are live?", "a": 0, "grade": "number"},
    {
        "run": "status",
        "q": "What exact command would start the gateway? Give the command only.",
        "a": ["gateway restart"],
        "grade": "contains",
    },
    {
        "run": "status",
        "q": "Was the gateway state measured from the process table, or is it unknown? Answer measured or unknown.",
        "a": "measured",
        "grade": "exact",
    },
]
