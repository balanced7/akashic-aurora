"""Charter P0 pins: the gap ledger -- every restoration is honest about what it restored.

The arc's first property, three-way blind-converged (Heimdall's amnesia-masquerading-
as-continuity; Navi's every-recovered-seat-knows-it-has-recovered; the operator-side
replay finding). The wound, receipted: on 08-12/13 boots rendered confident fullness
while the ask verb was dead, memory roots invisible, the watcher dark -- every organ
fail-opened SILENTLY, and silence impersonated success.

The organ: core/context/gap_ledger.py -- a per-boot collector the boot organs report
into (loaded / absent / FAILED with why), rendered at the head ALWAYS: one line when
clean (so a clean render is distinguishable from a dead collector -- the
absence-reads-as-success law), expanded when gapped. Persistence and correctness
measured separately, per the charter invariant: a plane that LOADED a fragment
reports partial, not loaded.
"""
from core.context.gap_ledger import GapLedger


def test_g1_clean_boot_renders_one_honest_line():
    g = GapLedger()
    for plane in ("notes", "badge", "siblings"):
        g.report(plane, "loaded")
    line = g.render()
    assert line.startswith("# restored:")
    assert "3/3" in line
    assert "gap" not in line.lower()


def test_g2_failures_render_with_their_why():
    g = GapLedger()
    g.report("notes", "loaded")
    g.report("badge", "failed", why="ConnectionError: store down")
    g.report("save", "absent")
    line = g.render()
    assert "RECOVERED WITH GAPS" in line
    assert "badge FAILED (ConnectionError: store down)" in line
    assert "save absent" in line
    assert "1/3" in line          # loaded count is honest: absent and failed both gap


def test_g3_partial_is_not_loaded():
    """The persistence-vs-correctness invariant: a plane that loaded a FRAGMENT
    says so -- restoring 100% of a fragment is a persistence success and a
    correctness failure, and the ledger is the artifact that keeps them apart."""
    g = GapLedger()
    g.report("notes", "partial", why="60d window; older notes unreadable this boot")
    line = g.render()
    assert "RECOVERED WITH GAPS" in line
    assert "notes PARTIAL" in line
    assert "0/1" in line


def test_g4_empty_ledger_confesses_instrumentation_absence():
    """A ledger nobody reported into must NOT render as a clean boot -- that is
    the exact silence-impersonates-success defect this organ exists to end."""
    line = GapLedger().render()
    assert "uninstrumented" in line.lower()
    assert "restored" not in line.split(":")[0].lower() or "0/0" in line


def test_g5_reporting_never_raises_and_render_is_single_block():
    g = GapLedger()
    g.report("", "loaded")                      # nameless plane: tolerated
    g.report("x", "unknown-status")             # bad status: coerced to failed, honestly
    g.report("y", "failed", why="a\nmultiline\twhy")
    line = g.render()
    assert "\t" not in line
    assert line.count("# ") == len(line.splitlines())   # every line head-formatted
