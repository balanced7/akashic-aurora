"""D2 stale-mail gate + D3 send-door bound -- acceptance pins (kimi P1-P5 prereg, deepseek
fence verdict 2026-07-19).

D2's pure half lives in packet_spec (partition_stale/stale_notice); the deepseek runner
applies it at batch materialization, and the existing batch_next sweep commits cursors past
unprocessed entries -- P3's no-redelivery rides that proven seam (same one that steps past
filtered own-broadcasts). The clock is always passed in (repo law: the caller owns the clock).
Run: py -m pytest tests/test_d2_stale_gate.py -q
"""
import os

from core.comm import packet_spec as PS

NOW = 1_784_500_000_000                 # fixed epoch-ms
GATE = 6 * 3600 * 1000                  # the kimi-default 6h threshold
DAY3 = 3 * 24 * 3600 * 1000
S30 = 30 * 1000


class M:
    """Minimal message shape: stream id + kind + to (direct or broadcast)."""
    def __init__(self, age_ms, kind, to="claude"):
        self.id = f"{NOW - age_ms}-0"
        self.kind = kind
        self.to = to


def test_p1_mixed_inbox_partitions_three_ways():
    inbox = [M(DAY3, "inform"), M(DAY3, "question"), M(S30, "question")]
    fresh, asks, skips = PS.partition_stale(inbox, now_ms=NOW, stale_ms=GATE)
    assert [m.kind for m in fresh] == ["question"] and fresh[0].id == f"{NOW - S30}-0"
    assert [m.id for m in asks] == [f"{NOW - DAY3}-0"]      # stale ask surfaced, not dropped
    assert [m.kind for m in skips] == ["inform"]            # stale inform auto-skipped


def test_p2_zero_threshold_reproduces_today():
    inbox = [M(DAY3, "inform"), M(DAY3, "question"), M(S30, "chat")]
    fresh, asks, skips = PS.partition_stale(inbox, now_ms=NOW, stale_ms=0)
    assert len(fresh) == 3 and not asks and not skips       # the gate is opt-out


def test_p3_partition_is_deterministic_relabel():
    # The pure face of no-redelivery: re-partitioning the identical tail yields identical
    # skips (a crash-before-sweep redelivers, the gate re-labels the same way, the sweep
    # commits -- idempotent). Cursor monotonicity itself is the runner's batch_next seam.
    tail = [M(DAY3, "inform"), M(DAY3, "trace")]
    first = PS.partition_stale(tail, now_ms=NOW, stale_ms=GATE)
    second = PS.partition_stale(tail, now_ms=NOW, stale_ms=GATE)
    assert [m.id for m in first[2]] == [m.id for m in second[2]] == [t.id for t in tail]


def test_p4_notice_names_count_oldest_and_triage_and_never_acks():
    asks = [M(DAY3, "question"), M(2 * 3600 * 1000 + GATE, "handoff")]
    _, stale_asks, _ = PS.partition_stale(asks, now_ms=NOW, stale_ms=GATE)
    notice = PS.stale_notice(stale_asks, now_ms=NOW)
    assert "2 stale ask(s)" in notice
    assert "72.0h" in notice                                # oldest, in hours
    assert "--traces" in notice and "auto-acked" in notice  # triage instruction, no ack
    assert PS.stale_notice([], now_ms=NOW) == ""


def test_p5_direct_and_broadcast_gate_identically():
    pair = [M(DAY3, "inform", to="claude"), M(DAY3, "inform", to="*")]
    fresh, asks, skips = PS.partition_stale(pair, now_ms=NOW, stale_ms=GATE)
    assert not fresh and not asks and len(skips) == 2       # no un-gated broadcast seam


def test_unknown_age_reads_as_fresh():
    weird = [M(S30, "chat")]
    weird[0].id = "$"                                       # sentinel: age unknowable
    fresh, asks, skips = PS.partition_stale(weird, now_ms=NOW, stale_ms=GATE)
    assert len(fresh) == 1 and not asks and not skips       # fail toward showing


def test_env_threshold_reads_and_disables(monkeypatch):
    monkeypatch.setenv("BIFROST_STALE_MS", "0")
    assert PS.stale_gate_ms() == 0
    monkeypatch.delenv("BIFROST_STALE_MS", raising=False)
    assert PS.stale_gate_ms() == PS.DEFAULT_STALE_MS


def test_d3_bound_confesses_at_8000():
    assert PS.bound_tool_text("x" * 8000) == "x" * 8000     # at the bound: untouched
    clipped = PS.bound_tool_text("x" * 8001)
    assert len(clipped) < 8001 + 100
    assert clipped.endswith("resend in chunks]")
    assert "clipped at 8000 chars" in clipped               # confession names the NEW bound
    assert PS.bound_tool_text("short") == "short"
    assert PS.bound_tool_text(None) == ""
