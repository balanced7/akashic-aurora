"""Stable entry point: runs agent/harness/hooks/claude_stop.py, the one canonical copy.

Kept because existing user-level registrations (e.g. `pyw E:/AI-Setup/scripts/hooks/claude_stop.py`)
point here. Behaviour lives ONLY in the canonical file; this shim must stay policy-free
(scripts/checkers/check_wiring.py enforces the shape). New installs: `agent_cli.py hooks install`.
"""

import os
import runpy

runpy.run_path(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "agent",
        "harness",
        "hooks",
        "claude_stop.py",
    ),
    run_name="__main__",
)
