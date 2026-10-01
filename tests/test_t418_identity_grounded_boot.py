"""T418 pins (2026-10-01): the boot door asserts the session's own identity before serving any
registry record, and refuses a subject that is not the caller's.

Two receipts the same day. 09:20 Sunshine's knowledge_boot returned "YOU ARE: Deepseek |
Heimdall" because core/comm/toolbox.py hardcoded `boot deepseek` for every ToolBox seat. 14:20
Rill's MCP boot(agent="deepseek") was answered as Heimdall because the CLI/MCP door trusted the
id the model typed while AKASHIC_AGENT_ID=dsh_agent sat in his environment the whole time.
Rill's phrasing is the acceptance: "Boot must assert the session's own stamp BEFORE serving any
registry record, and refuse a mismatch; the door currently answers as whoever I claim to be."

Hermetic: the pure check takes its environment and binding dir; the CLI pin runs the real door
with a fake stamp and reads the refusal; the ToolBox pin reads the source.
"""
import os
import re
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import seat_identity as si

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------- the pure check
def test_subject_check_refuses_a_foreign_id_when_the_env_stamp_is_set(tmp_path):
    r = si.subject_check("deepseek", session_id="s1", binding_dir=str(tmp_path),
                         env={"AKASHIC_AGENT_ID": "dsh_agent"})
    assert r["ok"] is False and r["resolved"] == "dsh_agent" and r["source"] == "env"
    assert "deepseek" in r["why"] and "dsh_agent" in r["why"]


def test_subject_check_accepts_the_sessions_own_id(tmp_path):
    r = si.subject_check("dsh_agent", session_id="s1", binding_dir=str(tmp_path),
                         env={"AKASHIC_AGENT_ID": "dsh_agent"})
    assert r["ok"] is True and r["resolved"] == "dsh_agent"


def test_subject_check_binding_beats_env_and_refuses_the_typed_id(tmp_path):
    assert si.declare("sol", "s2", str(tmp_path))        # declare(agent_id, session_id, dir)
    r = si.subject_check("deepseek", session_id="s2", binding_dir=str(tmp_path),
                         env={"AKASHIC_AGENT_ID": "deepseek"})
    assert r["ok"] is False and r["resolved"] == "sol" and r["source"] == "binding"


def test_subject_check_with_no_stamp_anywhere_accepts_and_says_so(tmp_path):
    r = si.subject_check("claude", session_id="s3", binding_dir=str(tmp_path), env={})
    assert r["ok"] is True and r["source"] == "unknown" and "no stamp" in r["why"]


def test_subject_check_explicit_override_is_allowed_and_named(tmp_path):
    r = si.subject_check("deepseek", session_id="s4", binding_dir=str(tmp_path),
                         env={"AKASHIC_AGENT_ID": "claude", "AKASHIC_BOOT_AS_OTHER": "1"})
    assert r["ok"] is True and r["override"] is True and "AKASHIC_BOOT_AS_OTHER" in r["why"]


# ---------------------------------------------------------------- the CLI door (MCP delegates to it)
def test_cli_boot_refuses_a_foreign_subject_and_names_both(tmp_path):
    env = {**os.environ, "AKASHIC_AGENT_ID": "t418sol", "CLAUDE_CODE_SESSION_ID": "t418sid",
           "AKASHIC_SEAT_BINDING_DIR": str(tmp_path)}
    env.pop("AKASHIC_BOOT_AS_OTHER", None)
    r = subprocess.run([sys.executable, os.path.join(REPO, "agent_cli.py"), "boot", "deepseek",
                        "--task", "t418 pin"], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180, cwd=REPO, env=env)
    out = (r.stdout or "") + (r.stderr or "")
    assert r.returncode != 0, out[-800:]
    assert "REFUSED" in out and "t418sol" in out and "deepseek" in out
    assert "YOU ARE:" not in out                      # no packet was assembled for the foreign id


# ---------------------------------------------------------------- the ToolBox door
def test_toolbox_knowledge_boot_boots_as_its_own_seat_never_a_hardcoded_id():
    src = open(os.path.join(REPO, "core", "comm", "toolbox.py"), encoding="utf-8").read()
    m = re.search(r"def knowledge_boot\(self, task\):(.*?)\n    def ", src, re.S)
    assert m, "knowledge_boot not found"
    body = m.group(1)
    assert '"deepseek"' not in body and "'deepseek'" not in body
    assert "self.agent_id" in body
