"""Real-repo pin: the unattended exec door can no longer commit or publish through mirror.py.

HISTORY. This file began as a one-off (deepseek, 2026-07): release the deepseek_chat.py lock, then
run the REAL scripts/mirror.py in the REAL repo as deepseek to commit the 8788 UI-port fix
("deepseek_chat: kill the 8788 UI-port ghost, use config.PORT_UI 8787"). Collected as a test, it
did that on every full-suite run, and mirror.py pushed whenever it ran -- so a suite run could
publish master to the public repo. On 2026-09-15 (commit 97b85ecd) the same door published
"count-plus-lines" and every unpushed commit since 2026-09-13. The lock release is dropped: it
was a one-time chore, not something a test should repeat against the live lock store.

It now drives the incident path itself -- the toolbox's unattended run_command, the deepseek
identity, positional arguments only -- against the real repo, and pins the refusal. Safe twice
over: mirror.py refuses before touching git, and positional arguments alone never commit or push.
"""
import os
import sys
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import core.comm.toolbox as tbmod


def test_unattended_mirror_is_refused_in_the_real_repo(monkeypatch):
    class _Trust:
        def has(self, cap):
            return True
    monkeypatch.setattr("core.trust.registry.resolve", lambda a: _Trust())
    box = tbmod.ToolBox(Path(REPO), allow_exec=True, trust=True, allow_secrets=False,
                        confirm=lambda _p: False, agent_id="deepseek")

    for command in ('py scripts/mirror.py "deepseek_chat: kill the 8788 UI-port ghost" scripts/deepseek_chat.py',
                    "py scripts/mirror.py count-plus-lines scripts/deepseek_chat.py"):
        out = box.run_command(command, timeout=60)
        assert "PUBLISH door" in out and "[exit 3]" in out, out
        assert "Nothing was staged, committed or pushed" in out, out
