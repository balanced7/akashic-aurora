"""Pins for the mem_watch per-process leak decision (T-mem, 2026-08-27).

Registered AFTER the fix, and the header says so plainly rather than claiming a
pre-registration it does not have: this organ was already live and mis-firing in
production, so the fix was the urgent half and these pins are the durable half.

WHAT PRODUCTION TAUGHT THAT THE DRILL COULD NOT. The 2026-08-26 drill
(state/drills/mem-watch-growth-2026-08-26.md) proved the alert FIRES: a deliberate
90-second ramp, watched while it climbed. It could not prove the alert ever STOPS,
because nothing in it ever stopped climbing. The first real firing, 2026-08-27,
alerted six times in three minutes on MemCompression -- while that process was
SHRINKING (4406.7 -> 4393.6MB) and the host sat at 46.7% used with 32.9GB free and
swap at 0.4%. Two defects, both invisible to the drill by construction.
"""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "mem_watch", Path(__file__).resolve().parents[1] / "scripts" / "ops" / "mem_watch.py")
mem_watch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mem_watch)

BIG, STEP = 4096.0, 512.0


def _call(**kw):
    base = dict(name="python.exe", pid=7, rss=5000.0, first_seen=4000.0, last_alert=None,
                peak=5000.0, proc_alert_mb=BIG, growth_alert_mb=STEP)
    base.update(kw)
    return mem_watch.process_alert(**base)


def test_a_big_and_climbing_process_alerts_once():
    assert _call() is not None


def test_a_flat_process_goes_SILENT_after_its_alert():
    """THE PRODUCTION BUG. growth was measured against first_seen on every sample, so
    a process that climbed once and plateaued re-alerted forever. A leak detector must
    report ACCELERATION, not a standing state."""
    assert _call(last_alert=5000.0) is None


def test_a_SHRINKING_process_never_alerts():
    """Observed firing on a process losing ~13MB across the run."""
    assert _call(rss=4900.0, last_alert=5000.0) is None


def test_it_re_arms_only_after_another_full_step():
    assert _call(rss=5511.0, last_alert=5000.0) is None, "just under a step must stay quiet"
    assert _call(rss=5512.0, last_alert=5000.0) is not None, "a full further step must speak"


def test_growth_alone_is_not_enough_below_the_size_floor():
    """A small process that doubles is not the 62GB this organ exists to name."""
    assert _call(rss=1000.0, first_seen=100.0) is None


def test_os_memory_accounting_processes_are_not_leak_candidates():
    """MemCompression's working set IS other processes' compressed pages: it grows when
    Windows is SAVING memory. Alerting on it as a leak says the opposite of the truth.
    Real pressure is still caught -- by the host warn-pct/alert-pct rule."""
    for name in ("MemCompression", "memcompression", "System"):
        assert _call(name=name, rss=9000.0, first_seen=1000.0) is None, name


def test_the_alert_line_carries_peak_so_a_post_mortem_sees_a_decline():
    line = _call(peak=6000.0)
    assert "peak=6000MB" in line and "rss=5000" in line
