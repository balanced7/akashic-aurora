"""
ns-isolation guardrail pin (2026-07-12) -- the acceptance test for the coordination-plane conversion
that generalizes Fix A (control.py). The 2026-07-12 finding: 6+ coordination modules hardcoded
NS="bifrost", so a drill in an isolated stream namespace still shared their keys -- and a drill that
tripped the rate-limit guard FROZE the live fleet.

Rule (fenced convergence, claude+deepseek): a key that coordinates the AGENTS in a namespace scopes to
BIFROST_NAMESPACE; a key that protects a SHARED RESOURCE across namespaces (the filesystem, the event
log, the launcher) stays GLOBAL.

This pin is PURE (no Redis) -- it checks the prefix FUNCTIONS directly, which also proves they read
the env PER-CALL (not baked at import): the modules import at collection time, the test sets the env
after, and a correctly-converted module still returns the scoped prefix.
"""
import pytest

from core.comm import expectations, runner_lock, liveness, nudge, doctor, turn_metrics
from core.comm import locks, launcher
from core.coord import intent, task_ledger

# The authoritative allowlist of modules whose bifrost:* keys are DELIBERATELY global (cross-namespace
# resources). Anything else writing a hardcoded bifrost:* coordination key is a regression.
GLOBAL_MODULES = {
    "locks",      # advisory path locks -> shared FILESYSTEM
    "promoter",   # bifrost:<msg_id> -> event-log ref convention (durable cross-ns ledger)
    "launcher",   # auto_revive -> one launcher spawns/revives for ALL namespaces
    "task_ledger", # git-durable governed task roster; one source of truth across namespaces
    "bus",        # NS is a fallback default only; Bus reads the env per-instance
}

# Every SCOPED module's namespace-forming prefix function.
SCOPED_PREFIXES = [
    ("expectations.expect", expectations._expect_prefix),
    ("runner_lock.lock", runner_lock._lock_prefix),
    ("runner_lock.generation", runner_lock._gen_prefix),
    ("liveness.worklive", liveness._worklive_prefix),
    ("liveness.progress", liveness._progress_prefix),
    ("nudge.nudge", nudge._nudge_prefix),
    ("nudge.steer", nudge._steer_prefix),
    ("doctor.stalled_since", doctor._stalled_since_prefix),
    ("doctor.doctor_paged", doctor._paged_prefix),
    ("turn_metrics", turn_metrics._key_prefix),
    ("intent.intent", intent._intent_prefix),
    ("intent.proposal", intent._proposal_ns),
]


def test_scoped_prefixes_follow_namespace(monkeypatch):
    """Under a non-default namespace, every scoped prefix lands under it and NOT under bifrost:*."""
    monkeypatch.setenv("BIFROST_NAMESPACE", "test_ns_iso")
    for name, fn in SCOPED_PREFIXES:
        p = fn()
        assert p.startswith("test_ns_iso:"), f"{name} did not scope to the namespace: {p!r}"
        assert not p.startswith("bifrost:"), f"{name} LEAKED to the live 'bifrost' keyspace: {p!r}"


def test_default_namespace_preserved(monkeypatch):
    """No BIFROST_NAMESPACE -> exact same keys as before the conversion (zero flag day)."""
    monkeypatch.delenv("BIFROST_NAMESPACE", raising=False)
    assert expectations._expect_prefix() == "bifrost:expect:"
    assert runner_lock._lock_prefix() == "bifrost:runner:"
    assert liveness._worklive_prefix() == "bifrost:worklive:"
    assert nudge._nudge_prefix() == "bifrost:control:nudge:"
    assert doctor._paged_prefix() == "bifrost:doctor_paged:"
    assert turn_metrics._key_prefix() == "bifrost:turn_metrics:"
    assert intent._intent_prefix() == "bifrost:intent:"
    assert intent._proposal_ns() == "bifrost:proposal"


def test_global_modules_stay_global(monkeypatch):
    """GLOBAL modules keep bifrost:* even under a non-default namespace -- scoping them would
    reintroduce a cross-namespace race (files) or fragment infrastructure (launcher/event log)."""
    monkeypatch.setenv("BIFROST_NAMESPACE", "test_ns_iso")
    assert locks.SEQ_KEY.startswith("bifrost:"), "locks path-lock seq MUST stay global (shared FS)"
    assert launcher.AUTO_REVIVE_KEY.startswith("bifrost:"), "launcher auto_revive MUST stay global"
    assert task_ledger.REDIS_LEDGER_KEY.startswith("bifrost:"), "task ledger MUST stay global (git-durable roster)"
