"""Pin K0 (2026-07-18): the tool surface lives canonically in core.comm.toolbox and
scripts/deepseek_chat.py re-exports it COMPAT-identically -- same objects, not copies.
Guards against the extraction silently forking the security boundary (two ToolBoxes
drifting apart would let a guard fix land on one path and not the other)."""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))


def test_compat_reexport_is_identity():
    import deepseek_chat
    from core.comm import toolbox
    assert deepseek_chat.ToolBox is toolbox.ToolBox, "compat ToolBox must BE the canonical class"
    assert deepseek_chat.TOOLS is toolbox.TOOLS, "compat TOOLS must BE the canonical list"
    assert deepseek_chat.MAX_CMD_TIMEOUT == toolbox.MAX_CMD_TIMEOUT


def test_canonical_surface_complete():
    from core.comm.toolbox import (ToolBox, TOOLS, _fn, EXCLUDE_DIRS, BINARY_SUFFIXES,
                                   MAX_FILE_BYTES, MAX_MATCHES, MAX_LIST, MAX_CMD_OUT,
                                   MAX_CMD_TIMEOUT)
    assert len(TOOLS) >= 30, "tool schema roster went missing in the move"
    assert MAX_FILE_BYTES == 120_000 and MAX_CMD_OUT == 16_000, "caps drifted in the move"


def test_agent_loop_not_extracted():
    """The 'premature generalization' ruling: the Agent loop stays species-specific."""
    from core.comm import toolbox
    assert not hasattr(toolbox, "Agent"), "Agent must NOT ride the shared seam (fence ruling)"
