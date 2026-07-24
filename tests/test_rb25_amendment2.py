"""
RB-25 Amendment 2 -- pre-registered acceptance (committed BEFORE the impl, M3/T031).
Rulings: docs/library/report/20260712_rb-25-amendment-2-deepseek-rulings-fence_7f1c14.md (all six
AFFIRMED; A2-1 reverses deepseek's original fail-open ruling on the merits).
Reconciliation: docs/library/design/20260712_rb-25-f1-f2-fence-reconciliation-claude_436168.md.

Contract frozen:
  A2-1  may_run_runner's except path mirrors resolve()'s OWN fallback
        (_bootstrap_or_quarantine): core fleet stays available through a broken door,
        everyone else refuses -- and the decision is LOUD on stderr. Never blanket True.
  A2-2  both runner call-sites' guard except blocks print a LOUD "guard NOT active"
        line instead of silent pass (an ImportError must not silently disable F1).
  A2-3  seed_cursor_at_tail returns the TRUTH of the guarded commit: advance_to
        status in (OK, OK_NOOP) -> True, anything else (ERROR/BACKWARDS/STALE_
        GENERATION/OFFLINE) -> False. No "cursor seeded" log line on a failed write.
  A2-4  seed_cursor_at_tail must not rely on construction-time `self.online` alone
        (L5 doctrine, d6936f2): the advance path is exception-guarded (Option B per
        the ruling) so a Redis death mid-onboarding degrades to False, never a crash.
  A2-5  DEVIATION RECORD (per T030 L4 precedent): the original registration froze
        `seed_cursor_at_tail() -> None`; the impl returns bool and the bool is
        load-bearing (both runners print only on True). Deviation AFFIRMED -- the
        caller needs the truth. This paragraph is that record.
  A2-6  adversarial USE drill: baseline PASS 2026-07-12 (id rb25-adv-7319, both
        runners refuse a quarantined id, exit 3, zero bus writes). Rerun required
        after A2-1 lands -- the floor must not admit a NON-core quarantined id.

Run: py -m pytest tests/test_rb25_amendment2.py -q
"""
import inspect
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trust import registry
from core.comm.bus import Bus

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Feature-detection skip guards (pins land BEFORE impl; each flips live when its impl does)
_SRC_MRR = inspect.getsource(registry.may_run_runner)
_A21 = "_bootstrap_or_quarantine" in _SRC_MRR
_SRC_SEED = inspect.getsource(Bus.seed_cursor_at_tail)
_A23 = "OK_NOOP" in _SRC_SEED
_A24 = ("probe(" in _SRC_SEED) or ("except" in _SRC_SEED)


def _runner_src(name):
    return open(os.path.join(_ROOT, "scripts", name), encoding="utf-8").read()


# ---------------- A2-1: bootstrap floor on a broken trust door ----------------

@pytest.mark.skipif(not _A21, reason="A2-1 pre-registered; bootstrap-floor except pending")
def test_broken_door_keeps_core_fleet_available(monkeypatch, capsys):
    def _boom(agent_id, **kw):
        raise RuntimeError("trust door broken (drill)")
    monkeypatch.setattr(registry, "resolve", _boom)
    assert registry.may_run_runner("deepseek") is True, \
        "core fleet rides the bootstrap floor through a broken door (availability bar)"
    err = capsys.readouterr().err
    assert "may_run_runner" in err and "RuntimeError" in err, \
        "the broken door + the decision are LOUD on stderr (heal_report precedent)"


@pytest.mark.skipif(not _A21, reason="A2-1 pre-registered; bootstrap-floor except pending")
def test_broken_door_refuses_everyone_else(monkeypatch, capsys):
    def _boom(agent_id, **kw):
        raise RuntimeError("trust door broken (drill)")
    monkeypatch.setattr(registry, "resolve", _boom)
    assert registry.may_run_runner("rb25-a2-unknown-id") is False, \
        "a NON-core id never gets a runner through a broken door (deny-by-default bar)"
    assert "REFUSED" in capsys.readouterr().err, "the refusal is LOUD, not silent"


# ---------------- A2-2: call-site guard failure is LOUD ----------------

@pytest.mark.skipif(not _A21, reason="A2-2 lands with A2-1 (coupled commit)")
def test_both_runner_call_sites_are_loud_on_guard_failure():
    for runner in ("bifrost_runner_deepseek.py", "bifrost_runner.py"):
        src = _runner_src(runner)
        f1_block = src.split("may_run_runner", 1)[-1]
        assert "guard NOT active" in f1_block, \
            f"{runner}: a guard exception prints the LOUD skip line (never silent pass)"


# ---------------- A2-3: seed returns the truth of the guarded commit ----------------

class _SeedProbe(Bus):
    """Unit harness: virgin cursor + non-empty tail, advance_to outcome injectable."""
    def __init__(self, advance_status):
        self._advance_status = advance_status          # no super().__init__: pure unit probe
        self.online = True
    def probe(self):
        return True
    def _read_cursor(self):
        return {"inbox": "0", "bc": "0"}
    def tail(self):
        return {"inbox": "9-1", "bc": "9-1"}
    def advance_to(self, **kw):
        return self._advance_status


@pytest.mark.skipif(not _A23, reason="A2-3 pre-registered; truth-return pending")
@pytest.mark.parametrize("status,expected", [
    ("OK", True), ("OK_NOOP", True),
    ("ERROR", False), ("BACKWARDS", False), ("STALE_GENERATION", False), ("OFFLINE", False),
])
def test_seed_reports_only_a_committed_advance(status, expected):
    assert _SeedProbe(status).seed_cursor_at_tail() is expected, \
        "seed's bool == the guarded commit's truth; a failed write may NOT read as 'seeded'"


# ---------------- A2-4: no crash and no lie when Redis dies mid-onboarding ----------------

@pytest.mark.skipif(not _A24, reason="A2-4 pre-registered; exception guard pending")
def test_redis_death_mid_seed_degrades_to_false():
    probe = _SeedProbe("OK")
    def _die(**kw):
        raise ConnectionError("redis died between register and seed (drill)")
    probe.advance_to = _die
    assert probe.seed_cursor_at_tail() is False, \
        "a dead Redis mid-onboarding degrades to False (old behavior), never a runner crash"
