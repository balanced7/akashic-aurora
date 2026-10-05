"""G4.P2 latent pin: the manual liveness probes reference only names core.comm.liveness defines.

The ns-isolation conversion replaced the module constant WORKLIVE_PREFIX with the per-call
_worklive_prefix(); three manual probes kept the old name and died with AttributeError at
their cleanup step. This reads each probe's source (it never runs them: they need Redis) and
checks every `liveness.<name>` it touches exists on the real module.
"""

import ast
from pathlib import Path

import pytest

from core.comm import liveness

_MANUAL = Path(__file__).resolve().parent / "manual"
_PROBES = ("l1_worklive_probe.py", "l3a_liveness_view_probe.py", "l3b_auto_revive_probe.py")


def _liveness_attrs(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "liveness"
    }


@pytest.mark.parametrize("probe", _PROBES)
def test_manual_probe_liveness_names_exist(probe: str) -> None:
    """Every liveness.<name> a manual probe touches is defined by core.comm.liveness."""
    attrs = _liveness_attrs(_MANUAL / probe)
    assert attrs, f"{probe} no longer uses core.comm.liveness; update this pin"
    missing = sorted(a for a in attrs if not hasattr(liveness, a))
    assert missing == [], f"{probe} references names core.comm.liveness does not define: {missing}"
