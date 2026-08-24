"""Smoke: the real (un-injected) detection paths import and run without raising.

These do NOT assert any particular verdict (they depend on live Redis / WMI state), only
that the real paths execute and return a string without crashing -- so a broken import or a
bad private-attribute access surfaces here rather than at first real activation.
"""
import core.comm.conductor_gate as cg


def test_real_conductor_two_factor_returns_a_string():
    v = cg._conductor_two_factor("claude")
    assert isinstance(v, str), v

def test_real_attendance_returns_a_string():
    s = cg._attendance("claude")
    assert isinstance(s, str), s

def test_real_succession_and_operator_order():
    assert cg.succession_order() == ("deepseek", "kimi")
    assert "daniil" in cg.operator_ids()

def test_real_evaluate_returns_verdict_obj():
    v = cg.evaluate_succession()
    # Real environment: conductor is likely ATTENDED (claude is up right now), so this
    # should NOT activate -- but we assert only shape, not the specific verdict.
    assert hasattr(v, "activate") and hasattr(v, "reason")
    assert isinstance(v.reason, str)
