"""
S0-beta · storm auto-clear (lane-depth spike + repeat-delivery detection →
standby-hard ceremony WITH receipt).

Cites docs/recovery-arc-design-2026-07.md S0 (= deepseek BULKHEAD-0 ∪ kimi R4)
+ core/comm/storm_detect.py + core/comm/cursor_admin.py + core/comm/control.py.
The conveyor's first full auto-transit: a human ritual (standby-hard) graduates
to auto-detected. The detector is in-memory (no Redis); the clear action is pause
→ skip-to-now → resume WITH a broadcast receipt.

AUTHORSHIP: deepseek's build package (write-gated seat, night-run 2026-07-21),
pre-staged by claude. The RUNNER WIRING (edits A/B/C) is deliberately NOT applied
yet — it holds for kimi's second-observer read on the sharp-action adjacency
(deepseek's own rail). These pins cover the detector + the ceremony's parts.

Laws pinned (RED before core/comm/storm_detect.py exists):
  1. LANE-DEPTH SPIKE DETECTED — depth >= threshold for N consecutive samples.
  2. REPEAT-DELIVERY DETECTED — N consecutive same-id messages fire.
  3. BELOW-THRESHOLD SILENT — sub-threshold depths and empty batches never fire.
  4. RESET CLEARS WINDOWS — post-clear feeds start from empty windows.
  5. STORM CLEAR = PAUSE→SKIP→RESUME WITH RECEIPT (live, test-namespaced).
  6. FAIL-OPEN — a degraded clear (ok=False) never raises into the runner.

Run: py -m pytest tests/test_s0_beta_storm_clear.py -q
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _ns_env(monkeypatch):
    ns = f"t-s0b-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", ns)
    return ns


def _online():
    from core.comm.bus import Bus
    return Bus("t-storm").online


# --- L1: storm detection (pure, no Redis needed) ---------------------------

def test_lane_depth_spike_detected():
    """Three consecutive samples at threshold 50 fire a lane_depth_spike."""
    from core.comm.storm_detect import StormDetector
    d = StormDetector(depth_threshold=50, depth_window=3)
    assert d.feed(60, []) is None, "sample 1: window not full"
    assert d.feed(55, []) is None, "sample 2: window not full"
    sig = d.feed(70, [])
    assert sig is not None and sig["kind"] == "lane_depth_spike", \
        "sample 3: window full, all >= threshold => spike"
    assert sig["window"] == [60, 55, 70]


def test_repeat_delivery_storm_detected():
    """Five consecutive same ids fire a repeat_delivery_storm."""
    from core.comm.storm_detect import StormDetector
    d = StormDetector(repeat_threshold=5)
    assert d.feed(0, ["a", "a"]) is None
    assert d.feed(0, ["a"]) is None
    assert d.feed(0, ["a"]) is None
    sig = d.feed(0, ["a"])
    assert sig is not None and sig["kind"] == "repeat_delivery_storm", \
        "5 consecutive 'a' ids => repeat storm"
    assert sig["id"] == "a" and sig["count"] == 5


def test_below_threshold_silent():
    """Depths below threshold never fire, even with a full window."""
    from core.comm.storm_detect import StormDetector
    d = StormDetector(depth_threshold=50, depth_window=3)
    assert d.feed(10, []) is None
    assert d.feed(20, []) is None
    assert d.feed(30, []) is None, "all below 50 => no spike"


def test_healthy_drain_stays_silent():
    """K3 (kimi second-observer): a strictly-decreasing supra-threshold window is a
    HEALTHY boot-drain under the batch cap, not a storm -- it must never fire.
    (Without the guard, any >=150 backlog guaranteed a false ceremony: 300->250->200.)"""
    from core.comm.storm_detect import StormDetector
    d = StormDetector(depth_threshold=50, depth_window=3)
    assert d.feed(300, []) is None
    assert d.feed(250, []) is None
    assert d.feed(200, []) is None, "draining despite depth => silent (progress guard)"
    # flat/rising flood still fires -- refill >= consumption at depth IS the storm
    d2 = StormDetector(depth_threshold=50, depth_window=3)
    d2.feed(60, []); d2.feed(62, [])
    assert d2.feed(61, []) is not None, "no net drain across the window => fires"


def test_empty_batch_silent():
    """An empty message batch never fires repeat-delivery."""
    from core.comm.storm_detect import StormDetector
    d = StormDetector(repeat_threshold=5)
    for _ in range(10):
        assert d.feed(0, []) is None, "no ids => never a repeat storm"


def test_reset_clears_windows():
    """After reset, a fresh feed starts from empty windows."""
    from core.comm.storm_detect import StormDetector
    d = StormDetector(depth_threshold=50, depth_window=3, repeat_threshold=3)
    d.feed(80, [])
    d.feed(80, [])
    d.reset()
    assert d.feed(80, []) is None, "window reset: sample 1 after reset, not full"
    assert d.feed(80, []) is None, "sample 2"
    sig = d.feed(80, [])
    assert sig is not None, "sample 3: fresh window fires correctly after reset"


# --- L2: storm clear ceremony (needs Redis; test-namespaced control plane) --

def test_storm_clear_pause_skip_resume_with_receipt(monkeypatch):
    """Full ceremony: pause → skip-to-now → resume + broadcast receipt."""
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm import control, cursor_admin
    from core.comm.bus import Bus
    agent = f"t-storm-clr-{uuid.uuid4().hex[:6]}"
    control.resume()
    ok_pause = control.pause(reason="storm-auto-clear: lane_depth_spike",
                             by=f"{agent}-runner", ttl=120)
    assert ok_pause, "pause succeeded"
    assert control.is_paused(), "pause flag is set"
    result = cursor_admin.skip_to_now(agent, by=f"{agent}-runner",
                                      reason="storm-auto-clear: lane_depth_spike")
    assert result["ok"], f"skip-to-now succeeded: {result.get('refused', '')}"
    control.resume()
    assert not control.is_paused(), "resume cleared the pause"
    b = Bus(agent)
    b.broadcast("note",
                f"[storm-clear] {agent}-runner auto-cleared storm "
                f"(lane_depth_spike): pause->skip->resume. Receipt: standby-hard graduates.",
                meta={"via": "storm-auto-clear", "display_only": True})
    # Fence amendment A3: the broadcast streams are {ns}:broadcast (legacy) +
    # {ns}:work:broadcast (lane) -- not {ns}:bc as the original pin guessed.
    tail = (b._client.xrevrange(f"{ns}:work:broadcast", count=3)
            + b._client.xrevrange(f"{ns}:broadcast", count=3))
    joined = " ".join(str(f) for _sid, f in tail)
    assert "storm-clear" in joined, "receipt broadcast landed"


def test_storm_clear_fails_open_on_broken_bus(monkeypatch):
    """A degraded clear (bad agent) returns ok=False rather than raising --
    the runner's try/except plus this contract keep a stuck clear from wedging."""
    ns = _ns_env(monkeypatch)
    if not _online():
        pytest.skip("redis not available")
    from core.comm import control, cursor_admin
    control.resume()
    result = cursor_admin.skip_to_now("nonexistent-agent-xyz-123",
                                      by="test", reason="test")
    assert not result["ok"], "skip on nonexistent agent returns ok=False, not an exception"
    assert "refused" in result or not result["ok"], \
        "fail-open: runner continues even if clear is degraded"
