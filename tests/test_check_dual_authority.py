"""T118 pin: the dual-authority class-preventer catches the defect class B belongs to.

The board named the class (2026-07-28): "B is the second half-abandoned migration this
week to be found by accident. A checker that flags dual authorities with diverging
freshness ... would catch the class." These pins encode the live incident that proved
it: store_state.db frozen Jul-25 23:28 while store_state.json advanced to Jul-28 16:04,
found by a human reading a board, not by an instrument.

P1 is deliberately a replica of that incident. If check_dual_authority ever stops
firing on P1's shape, the class-preventer has regressed to decoration.
"""
import os
import time

import pytest

from scripts.checkers.check_dual_authority import classify


def _touch(path, mtime):
    path.write_text("x", encoding="utf-8")
    os.utime(path, (mtime, mtime))


HOUR = 3600.0
NOW = 1_800_000_000.0  # fixed epoch; classify() takes now= so wall clock never leaks in


def _codes(findings):
    return {f["code"] for f in findings}


def _fails(findings):
    return [f for f in findings if f["severity"] == "fail"]


def test_p1_the_live_incident_shape_fires(tmp_path):
    """JSON advancing, DB frozen 3 days, flag unset (file authority) -- the exact
    half-migration this checker exists to catch. Must FAIL loudly."""
    j, d = tmp_path / "s.json", tmp_path / "s.db"
    _touch(j, NOW - 1 * HOUR)          # live JSON moved an hour ago
    _touch(d, NOW - 72 * HOUR)         # DB froze three days ago
    findings = classify(j, d, backend_env="", now=NOW)
    assert "DIVERGENT-DUAL" in _codes(findings)
    assert _fails(findings), "the live incident shape must be fail-severity, not a whisper"


def test_p2_stale_authority_is_named_as_confidently_wrong(tmp_path):
    """Flag says sqlite but the DB is the frozen twin: reads are served from a store
    that stopped moving. The finding must say the AUTHORITY is the stale side."""
    j, d = tmp_path / "s.json", tmp_path / "s.db"
    _touch(j, NOW - 1 * HOUR)
    _touch(d, NOW - 72 * HOUR)
    findings = classify(j, d, backend_env="sqlite", now=NOW)
    stale_auth = [f for f in findings if f["code"] == "STALE-AUTHORITY"]
    assert stale_auth, "authority-side staleness is its own, louder finding"
    assert all(f["severity"] == "fail" for f in stale_auth)


def test_p3_converging_pair_inside_window_is_not_a_failure(tmp_path):
    """Both artifacts moving together (a deliberate dual-write window) is the one
    LEGITIMATE dual state -- report it, never fail it."""
    j, d = tmp_path / "s.json", tmp_path / "s.db"
    _touch(j, NOW - 1 * HOUR)
    _touch(d, NOW - 2 * HOUR)
    findings = classify(j, d, backend_env="", now=NOW)
    assert not _fails(findings)


def test_p4_single_artifact_is_single_authority(tmp_path):
    j = tmp_path / "s.json"
    _touch(j, NOW - 100 * HOUR)  # age alone is not divergence
    findings = classify(j, tmp_path / "s.db", backend_env="", now=NOW)
    assert not _fails(findings)


def test_p5_wal_growth_is_a_health_failure(tmp_path):
    """Rider 1 (measured 2026-07-26: 523,272-byte WAL under one held reader): WAL size
    is a health signal. Above threshold -> fail, citing the size."""
    j, d = tmp_path / "s.json", tmp_path / "s.db"
    _touch(j, NOW - 1 * HOUR)
    _touch(d, NOW - 1 * HOUR)
    wal = tmp_path / "s.db-wal"
    wal.write_bytes(b"\0" * 600_000)
    findings = classify(j, d, backend_env="sqlite", now=NOW,
                        wal_alert_bytes=524_288)
    wal_f = [f for f in findings if f["code"] == "WAL-GROWTH"]
    assert wal_f and wal_f[0]["severity"] == "fail"
    assert "600000" in wal_f[0]["line"] or "600,000" in wal_f[0]["line"]


def test_p6_missing_both_is_silence_not_crash(tmp_path):
    assert classify(tmp_path / "a.json", tmp_path / "a.db",
                    backend_env="", now=NOW) == []
