"""IR-4 pins: the audited MIRROR exec family (Daniel verdict 2026-07-16, recorded verbatim
in security/acl.json). Commit autonomy through OUR door -- canonical scripts/mirror.py,
repo root only, explicit repo-relative paths, no flags, trust surfaces excluded; raw git
stays refused. Pattern: t067 (_exec_family called directly on a trusted ToolBox)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import deepseek_chat as dc
from pathlib import Path

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tb():
    return dc.ToolBox(Path(REPO), allow_exec=True, trust=True, allow_secrets=False,
                      confirm=lambda *_: False)   # trusted path never prompts


def _family(cmd):
    return _tb()._exec_family(cmd)


def test_mirror_happy_path_allowed():
    argv, env, why = _family('py scripts/mirror.py "T086-S5 daemon slice" core/comm/daemon_state.py tests/test_s5.py')
    assert why is None and argv[:2] == ["py", "scripts/mirror.py"]


def test_mirror_without_paths_refused():
    argv, _, why = _family('py scripts/mirror.py "just a message"')
    assert argv is None and "EXPLICIT paths" in why


def test_mirror_flags_refused():
    argv, _, why = _family('py scripts/mirror.py "msg" --all')
    assert argv is None and "no --all" in why


def test_mirror_security_path_refused():
    argv, _, why = _family('py scripts/mirror.py "grant tweak" security/acl.json')
    assert argv is None and "outside your mirror scope" in why


def test_mirror_claude_config_refused():
    argv, _, why = _family('py scripts/mirror.py "hook tweak" .claude/settings.json')
    assert argv is None and "outside your mirror scope" in why


def test_mirror_absolute_or_dotdot_paths_refused():
    argv, _, why = _family('py scripts/mirror.py "msg" ../outside.txt')
    assert argv is None and "repo-relative" in why
    argv, _, why = _family(r'py scripts/mirror.py "msg" E:\AI-Setup\core\x.py')
    assert argv is None and "repo-relative" in why


def test_shadow_mirror_script_refused():
    argv, _, why = _family('py evil/mirror.py "msg" core/x.py')
    assert argv is None                       # not the canonical scripts/mirror.py


def test_mirror_working_dir_override_refused():
    out = _tb().run_command('py scripts/mirror.py "msg" core/x.py', working_dir="core")
    assert "repo root only" in out


def test_raw_git_still_refused():
    argv, _, why = _family("git commit -m x")
    assert argv is None and "families" in why


def test_pytest_family_regression():
    argv, env, why = _family("py -m pytest tests/test_ir4_mirror_family.py -q")
    assert why is None and env.get("_AISETUP_TEST_ISOLATED") == "1"
