"""Quick IR-4 mirror family verification."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.deepseek_chat import ToolBox
from pathlib import Path

def test_ir4_mirror_family_present():
    """Verify the mirror family is in the exec gate and produces valid argv."""
    tb = ToolBox(Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                 allow_exec=True, trust=True, allow_secrets=False, confirm=lambda x: True,
                 agent_id='deepseek')
    argv, env_extra, why = tb._exec_family('py scripts/mirror.py "test msg" scripts/deepseek_chat.py')
    assert argv is not None, f"mirror family refused: {why}"
    assert argv[0] == "py"
    assert "mirror.py" in argv[1]
    assert "test msg" in argv
    assert "scripts/deepseek_chat.py" in argv
    print("IR-4 mirror family: LIVE")
