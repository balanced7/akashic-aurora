"""Pins for mem_watch's commit-side recorder (2026-09-24), registered BEFORE the fix.

WHY THESE EXIST. mem_watch was born 2026-08-26 to name the next memory culprit. On
2026-09-24 the machine froze again (1 fps cursor, hard power cut) and it named nothing,
for two reasons found that night:

1. It was not running. Launched by hand, it wrote its last sample at 2026-09-07 17:37,
   the minute of a reboot, and nothing ever started it again: 17 days blind, through the
   09-11 kernel-pool outage, the 09-16 hard reset and the 09-24 freeze.
2. It watched the wrong gauge. Its own trail covers two of the Resource-Exhaustion hits
   (09-04 01:53 and 09-06 02:33). At both, psutil said 21.2 GB and 14.0 GB of RAM were
   still AVAILABLE. The detector fires on COMMIT (virtual memory charged against RAM +
   pagefile, ~124 GB here), and an RSS-only recorder cannot see commit that is charged
   but not resident. Per-process private bytes, system commit, and kernel pools are the
   missing instruments.

These pins cover the pure decisions (commit alert levels, snapshot throttle, snapshot
retention) and one Windows smoke test that the new host fields are real numbers.
"""
import importlib.util
import os
import sys
import time
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "mem_watch", Path(__file__).resolve().parents[1] / "scripts" / "ops" / "mem_watch.py")
mem_watch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mem_watch)

TOP = [{"name": "hog.exe", "pid": 11, "private_mb": 50000.0},
       {"name": "small.exe", "pid": 12, "private_mb": 900.0}]


# ---- commit alert levels ---------------------------------------------------------

def test_commit_below_warn_is_silent():
    assert mem_watch.host_commit_alert(
        commit_mb=60000, limit_mb=124000, warn_pct=80, alert_pct=90, top_private=TOP) is None


def test_commit_between_warn_and_alert_warns_and_names_the_gauge():
    line = mem_watch.host_commit_alert(
        commit_mb=105000, limit_mb=124000, warn_pct=80, alert_pct=90, top_private=TOP)
    assert line.startswith("WARN host commit")
    assert "105000" in line and "124000" in line


def test_commit_above_alert_names_the_top_private_consumer():
    line = mem_watch.host_commit_alert(
        commit_mb=118000, limit_mb=124000, warn_pct=80, alert_pct=90, top_private=TOP)
    assert line.startswith("ALERT host commit")
    assert "hog.exe" in line  # an alert must point at a culprit, not just a total


def test_commit_alert_survives_a_missing_limit():
    # Non-Windows or a failed GetPerformanceInfo yields no limit: say nothing, never crash.
    assert mem_watch.host_commit_alert(
        commit_mb=0, limit_mb=0, warn_pct=80, alert_pct=90, top_private=TOP) is None


# ---- pressure snapshot throttle ---------------------------------------------------

def _snap(**kw):
    base = dict(now=10_000.0, last_snapshot_at=None, commit_pct=92.0, available_mb=20000,
                pct_threshold=88.0, min_available_mb=2048, min_gap_s=600)
    base.update(kw)
    return mem_watch.should_snapshot(**base)


def test_pressure_with_no_prior_snapshot_takes_one():
    assert _snap() is True


def test_calm_host_takes_no_snapshot():
    assert _snap(commit_pct=40.0, available_mb=30000) is False


def test_low_available_ram_triggers_even_when_commit_is_calm():
    assert _snap(commit_pct=40.0, available_mb=1500) is True


def test_snapshots_are_throttled_inside_the_gap():
    assert _snap(last_snapshot_at=10_000.0 - 300) is False


def test_throttle_releases_after_the_gap():
    assert _snap(last_snapshot_at=10_000.0 - 601) is True


# ---- snapshot retention -----------------------------------------------------------

def test_prune_snapshots_keeps_the_newest(tmp_path):
    for i in range(7):
        p = tmp_path / f"snap-2026092{i}-000000.json"
        p.write_text("{}")
        os.utime(p, (time.time() - (7 - i) * 60,) * 2)
    removed = mem_watch.prune_snapshots(str(tmp_path), keep=3)
    left = sorted(p.name for p in tmp_path.iterdir())
    assert removed == 4
    assert left == ["snap-20260924-000000.json", "snap-20260925-000000.json",
                    "snap-20260926-000000.json"]


# ---- the real gauges exist on this machine ----------------------------------------

@pytest.mark.skipif(sys.platform != "win32", reason="GetPerformanceInfo is Windows-only")
def test_sample_records_commit_pools_and_private_bytes():
    snap = mem_watch.sample(5, ["python"])
    host = snap["host"]
    assert host["commit_limit_mb"] > host["commit_mb"] > 0
    assert host["kernel_paged_mb"] > 0 and host["kernel_nonpaged_mb"] > 0
    assert host["handles"] > 0
    assert all("private_mb" in row for row in snap["top"])
    # the top list must include the biggest COMMIT holders, not only the biggest RSS
    biggest_private = max(snap["top"], key=lambda r: r["private_mb"])
    assert biggest_private["private_mb"] > 0
