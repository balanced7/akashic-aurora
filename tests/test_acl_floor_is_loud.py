"""PRE-REGISTERED ACCEPTANCE (defer cf6fe59a4d) -- the bootstrap floor must be LOUD, not silent.

core/trust/registry.py::resolve() falls back to BOOTSTRAP_ROLES (claude=super_admin, deepseek=admin,
everyone else QUARANTINED) whenever security/acl.json is MISSING or CORRUPT. That policy is deliberate
and stays: it is the availability floor. The defect is the SILENCE around it -- `_load()` swallows the
OSError / parse error and returns None, `_bootstrap_or_quarantine()` answers with no output, and the
only loud line in the module (A2-1, may_run_runner) fires only when resolve() RAISES, which these two
paths never do. So an operator whose ACL vanished (t384 made the file instance-local; a clean clone
has none) runs two seats at elevated role with nothing anywhere saying the ACL is gone.

Same shape as T151 (grant expiry was a trapdoor until expiring_grants() + the doctor row). A fallback
WIDER than what it replaces must be observable at first use (stderr, once per process) and at
inspection (doctor row + acl_status()).

  F1  MISSING: floor policy pinned (claude super_admin, stranger quarantined) AND one stderr line
      naming BOOTSTRAP FLOOR, the fault kind 'missing' and the path
  F2  CORRUPT: same, kind 'corrupt'
  F3  ONCE: a second resolve() in the same process adds nothing (noise is how warnings get silenced)
  F4  QUIET-WHEN-VALID: a readable ACL -> no stderr, acl_status() ok, floor not in force
  F5  STATUS: acl_status() is read-only, never raises, and names the fault + the floor roles
  F6  DOCTOR: `doctor` prints an 'ACL MISSING' / 'ACL CORRUPT' row with BOOTSTRAP FLOOR + restore drill,
      and prints no such row when the file is valid
  F7  RE-WARN: valid -> missing -> valid -> missing warns twice (the once-flag resets on recovery)

Run: py -m pytest tests/test_acl_floor_is_loud.py -q -p no:cacheprovider
"""
import json
import os
import sys
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.trust import registry as REG  # noqa: E402

VALID = {
    "_comment": "test acl (cf6fe59a4d pin)",
    "schema_version": 1,
    "grants": [
        {"agent_id": "claude", "role": "super_admin", "caps": [], "path_scope": ["*"],
         "granted_by": "root", "granted_at": "2026-08-24T00:00:00Z", "reason": "t"},
        {"agent_id": "kimi", "role": "member", "caps": ["read"], "path_scope": [],
         "granted_by": "claude", "granted_at": "2026-08-24T00:00:00Z", "reason": "t"},
    ],
}


def _fresh_cache():
    return {"mtime": None, "grants": {}}


@pytest.fixture()
def floor_state(monkeypatch, tmp_path):
    """A fresh registry: empty mtime cache, once-flag cleared, ACL pointed into tmp_path.
    Returns the ACL path (not yet created -> MISSING)."""
    p = tmp_path / "acl.json"
    monkeypatch.setenv("AKASHIC_ACL_PATH", str(p))
    monkeypatch.setattr(REG, "_CACHE", _fresh_cache())
    monkeypatch.setattr(REG, "_FLOOR_WARNED", False, raising=False)
    monkeypatch.setattr(REG, "_ACL_FAULT", None, raising=False)
    return p


def _floor_roles_pinned():
    """The POLICY is not under test -- pin it so a fix that goes quiet by going closed is caught."""
    assert REG.resolve("claude").role == "super_admin"
    assert REG.resolve("deepseek").role == "admin"
    assert REG.resolve("stranger").role == "quarantined"


def test_f1_missing_acl_floor_is_loud_on_stderr(floor_state, capsys):
    _floor_roles_pinned()
    err = capsys.readouterr().err
    assert "BOOTSTRAP FLOOR" in err, (
        f"a MISSING ACL put two seats on the bootstrap floor and said nothing: stderr={err!r}")
    assert "missing" in err.lower(), f"the line must name the fault kind: {err!r}"
    assert str(floor_state) in err, f"the line must name the path it could not read: {err!r}"


def test_f2_corrupt_acl_floor_is_loud_on_stderr(floor_state, capsys):
    floor_state.write_text("{not json", encoding="utf-8")
    _floor_roles_pinned()
    err = capsys.readouterr().err
    assert "BOOTSTRAP FLOOR" in err, (
        f"a CORRUPT ACL put two seats on the bootstrap floor and said nothing: stderr={err!r}")
    assert "corrupt" in err.lower(), f"the line must name the fault kind: {err!r}"
    assert str(floor_state) in err, f"the line must name the path it could not parse: {err!r}"


def test_f3_the_notice_fires_once_per_process(floor_state, capsys):
    REG.resolve("claude")
    first = capsys.readouterr().err
    assert first.count("BOOTSTRAP FLOOR") == 1, f"precondition: first use warns exactly once: {first!r}"
    REG.resolve("stranger")
    REG.resolve("deepseek")
    assert capsys.readouterr().err == "", (
        "every later resolve() repeated the notice -- noise is how a warning gets silenced")


def test_f4_a_valid_acl_is_quiet_and_reports_ok(floor_state, capsys):
    floor_state.write_text(json.dumps(VALID), encoding="utf-8")
    assert REG.resolve("claude").role == "super_admin"
    assert REG.resolve("kimi").role == "member"
    assert REG.resolve("stranger").role == "quarantined"
    assert capsys.readouterr().err == "", "a readable ACL must not cry wolf"
    st = REG.acl_status()
    assert st["ok"] is True
    assert st["floor_in_force"] is False
    assert st["fault_kind"] is None


def test_f5_acl_status_names_the_fault_and_never_raises(floor_state, capsys):
    st = REG.acl_status()                         # before ANY resolve(): doctor must not depend on use
    assert st["ok"] is False
    assert st["fault_kind"] == "missing"
    assert st["floor_in_force"] is True
    assert st["path"] == str(floor_state)
    assert st["floor_roles"] == {"claude": "super_admin", "deepseek": "admin"}
    floor_state.write_text("{not json", encoding="utf-8")
    st2 = REG.acl_status()
    assert st2["fault_kind"] == "corrupt" and st2["floor_in_force"] is True
    capsys.readouterr()


def _doctor_stdout(monkeypatch, capsys):
    """Drive cmd_doctor with the fleet/services probes stubbed (H6 precedent: no Redis needed)."""
    import agent_cli
    from core.comm import doctor
    monkeypatch.setattr(doctor, "examine_fleet",
                        lambda agents, page_notes=False: {
                            "agents": [], "findings": [], "summary": "doctor: healthy"})
    monkeypatch.setattr(doctor, "known_agents", lambda: [])
    monkeypatch.setattr(doctor, "examine_services", lambda: [])
    try:
        import core.recall.at_action as _aa
        monkeypatch.setattr(_aa, "injections_by_family", lambda hours: {})
    except Exception:
        pass
    capsys.readouterr()
    rc = agent_cli.cmd_doctor(SimpleNamespace(agents=None, page=False, progress=False, json=False))
    assert rc == 0
    return capsys.readouterr().out


def test_f6_doctor_shows_the_floor_and_the_restore_drill(floor_state, monkeypatch, capsys):
    out = _doctor_stdout(monkeypatch, capsys)
    assert "ACL MISSING" in out, f"doctor has no row for a missing ACL:\n{out}"
    assert "BOOTSTRAP FLOOR" in out
    assert "ACL-MOVED-READ-ME" in out, "the row must carry the restore drill, not just the alarm"
    floor_state.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(REG, "_CACHE", _fresh_cache())
    out = _doctor_stdout(monkeypatch, capsys)
    assert "ACL CORRUPT" in out, f"doctor has no row for a corrupt ACL:\n{out}"
    floor_state.write_text(json.dumps(VALID), encoding="utf-8")
    monkeypatch.setattr(REG, "_CACHE", _fresh_cache())
    out = _doctor_stdout(monkeypatch, capsys)
    assert "## ACL" not in out and "BOOTSTRAP FLOOR" not in out, (
        f"a valid ACL must not raise a doctor row (no crying wolf):\n{out}")


def test_f7_recovery_then_loss_warns_again(floor_state, capsys):
    floor_state.write_text(json.dumps(VALID), encoding="utf-8")
    REG.resolve("claude")
    assert capsys.readouterr().err == ""
    floor_state.unlink()
    REG.resolve("claude")
    assert capsys.readouterr().err.count("BOOTSTRAP FLOOR") == 1, "first loss warns"
    floor_state.write_text(json.dumps(VALID), encoding="utf-8")
    REG._CACHE.clear()
    REG._CACHE.update(_fresh_cache())
    assert REG.resolve("kimi").role == "member"
    assert capsys.readouterr().err == "", "recovery is quiet"
    floor_state.unlink()
    REG.resolve("claude")
    assert capsys.readouterr().err.count("BOOTSTRAP FLOOR") == 1, (
        "a SECOND loss after recovery must warn again -- the once-flag resets when the file comes back")


def _drill_never_offers_the_example_copy_alone(text):
    """v2 refutation: acl.example.json ships ZERO grants and resolve() honours an EMPTY valid file, so a
    drill that offers the copy as a standalone step moves a fresh clone from the floor to a state where
    every seat (claude and deepseek included) is quarantined -- worse than what it warns about."""
    assert "acl.example.json AND add your own root" in text, (
        "the drill must bind the example copy to adding a root record: " + text)
    assert "or copy security/acl.example.json;" not in text and "(or copy" not in text, (
        "the drill must never offer the example copy as a standalone recovery: " + text)


def test_f8_the_restore_drill_never_offers_the_empty_example_alone(floor_state, capsys, monkeypatch):
    import core.trust.registry as registry
    registry.resolve("claude")
    err = capsys.readouterr().err
    assert "BOOTSTRAP FLOOR" in err, err
    _drill_never_offers_the_example_copy_alone(err)
    import contextlib, io, sys as _sys
    import agent_cli
    monkeypatch.setattr(_sys, "argv", ["agent_cli.py", "doctor"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            agent_cli.main()
        except SystemExit:
            pass
    out = buf.getvalue()
    assert "BOOTSTRAP FLOOR IN FORCE" in out, out[:600]
    _drill_never_offers_the_example_copy_alone(out)
