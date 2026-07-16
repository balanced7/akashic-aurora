"""T079-E2 PRE-REGISTERED ACCEPTANCE -- fence_phase + lane_depths (engine-room backends).

Spec: t079-engine-room-reconciliation-2026-07-15.md slice E2 (claude builds,
deepseek verifies). Two pure readers, one dict each, UI-poll cheap, never raise.

Pins:
  L1  lane_depths() returns {work, legacy, trace, sig} ints from XLEN; absent
      streams -> 0; hostile client -> all zeros
  F1  fence_phase() derives the CURRENT fence state from research/reviewed/
      file mtimes for a given arc slug: blind (one half) -> reconciling (both
      halves, no reconciliation) -> reconciled (reconciliation file present)
  F2  no matching files -> {"phase": "idle"}
  F3  hostile filesystem/client -> idle, never an exception

Run: py -m pytest tests/test_t079_e2_phase_lanes.py -q
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.comm import lane_depths as ld
    from core.comm import fence_phase as fp
except ImportError:
    ld = fp = None


def _built():
    assert ld is not None and fp is not None, \
        "E2 build targets core/comm/lane_depths.py + fence_phase.py missing (RED until built)"


class FakeRedis:
    def __init__(self, lens=None):
        self.lens = lens or {}
    def xlen(self, k):
        if k not in self.lens:
            raise Exception("no such key")
        return self.lens[k]


def test_l1_lane_depths():
    _built()
    c = FakeRedis({"bifrost:work:inbox:claude": 3, "bifrost:inbox:claude": 7,
                   "bifrost:trace": 100})
    d = ld.lane_depths("claude", c=c)
    assert d["work"] == 3 and d["legacy"] == 7 and d["trace"] == 100 and d["sig"] == 0
    class Hostile:
        def __getattr__(self, _):
            raise RuntimeError("boom")
    d2 = ld.lane_depths("claude", c=Hostile())
    assert d2 == {"work": 0, "legacy": 0, "trace": 0, "sig": 0}, "L1: hostile -> zeros"


def _touch(d, name, age_s=0):
    p = os.path.join(d, name)
    with open(p, "w") as f:
        f.write("x")
    t = time.time() - age_s
    os.utime(p, (t, t))


def test_f1_phase_ladder(tmp_path):
    _built()
    d = str(tmp_path)
    _touch(d, "claude-widget-2026-07-15.md", 300)
    assert fp.fence_phase("widget", reviewed_dir=d)["phase"] == "blind", \
        "F1: one half filed -> blind"
    _touch(d, "deepseek-widget-2026-07-15.md", 200)
    assert fp.fence_phase("widget", reviewed_dir=d)["phase"] == "reconciling", \
        "F1: both halves, no reconciliation -> reconciling"
    _touch(d, "widget-reconciliation-2026-07-15.md", 100)
    out = fp.fence_phase("widget", reviewed_dir=d)
    assert out["phase"] == "reconciled", "F1: reconciliation file -> reconciled"
    assert out.get("files"), "F1: the files that produced the verdict are named"


def test_f2_idle(tmp_path):
    _built()
    assert fp.fence_phase("nothing", reviewed_dir=str(tmp_path))["phase"] == "idle"


def test_f3_never_raises():
    _built()
    assert fp.fence_phase("x", reviewed_dir="Z:/does/not/exist")["phase"] == "idle"
