"""T081 W6/W7 pins -- claude's cross-verify of deepseek's runner-lane build.

DeepSeek authored the impl (ToolBox boot_sources + mem: arm + bifrost_dashboard) but has no
exec to run tests; these pins are the run-it-for-real half of the fenced cross-check.
"""
import sys
from pathlib import Path

_SCRIPTS = str(Path(__file__).resolve().parent.parent / "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
import deepseek_chat as dc  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def _tb(**kw):
    return dc.ToolBox(REPO, allow_exec=False, trust=False, allow_secrets=False,
                      confirm=lambda p: False, **kw)


def test_w6p2_boot_sources_used_directly_when_provided():
    # the sidecar path: a provided set is used verbatim, regex skipped
    tb = _tb(boot_sources={"learn:experiment:x", "learn:experiment:mem_a_b"})
    assert tb._boot_sources == {"learn:experiment:x", "learn:experiment:mem_a_b"}


def test_w6p2_none_falls_back_to_regex():
    tb = _tb(boot_text="learn:experiment:qual and (source: bare)")
    assert "learn:experiment:qual" in tb._boot_sources
    assert "learn:experiment:bare" in tb._boot_sources


def test_w6p1_mem_arm_normalizes_mem_namespace():
    # the R-P2 fix: mem:decision:ADR_071503 was missed by both old arms
    tb = _tb(boot_text="lesson (source: mem:decision:ADR_071503)")
    assert "learn:experiment:mem_decision_ADR_071503" in tb._boot_sources


def test_w6p1_mem_arm_does_not_false_match_bare():
    # the bare arm must NOT emit a bogus learn:experiment:mem from 'source: mem:...'
    tb = _tb(boot_text="(source: mem:x:y)")
    assert "learn:experiment:mem" not in tb._boot_sources
    assert "learn:experiment:mem_x_y" in tb._boot_sources


def test_w7_bifrost_dashboard_registered_in_toolbox():
    assert "bifrost_dashboard" in str(dc.TOOLS)


def test_w7_bifrost_dashboard_returns_nonempty_string_never_raises():
    d = _tb().bifrost_dashboard()
    assert isinstance(d, str) and d
