"""PRE-REGISTERED ACCEPTANCE (T162) -- the `grant` verb, promised in a docstring and never built.

scripts/checkers/check_advertised_verbs.py:47 carries `grant` on its PLANNED list: "S-3 of the
security schema; grants are currently edited in security/acl.json, no CLI door yet". That list
exists so a promise is a claim on the record instead of a hole nobody can see. This closes it.

WHAT THIS DOOR IS, STATED PLAINLY, BECAUSE A SILENT OVERCLAIM WOULD BE WORSE THAN NO DOOR.
`--by` is a string on a command line. Anyone who can run agent_cli.py can type `--by claude`, and
anyone who can run agent_cli.py can also open security/acl.json in an editor. So this verb is NOT
a new security boundary and must not be described as one. It is a SAFER PATH to a file that was
already writable: atomic and schema-validated instead of hand-edited, audited by construction
instead of by discipline, time-boxed by default, and revocable. It reduces the chance of a
MISTAKE. It does not reduce the chance of an ATTACK by someone who already has shell access.

That distinction is the whole reason the guards below are worth pinning: they are consistency
guards, and their value is that a tired operator at 2am cannot quietly widen the fleet's
authority by fumbling a JSON edit.

MEASURED STARTING STATE (11 grants): 10 are PERMANENT (expires_at=None) and granted_by=claude;
only codex_root is time-boxed. A guard that cannot reproduce the CURRENT state is a guard that
gets bypassed on its first real use, so a permanent grant must remain expressible -- deliberately,
with a flag, never by forgetting to pass --hours.

  V1  FAIL CLOSED ON AUTHORITY -- a granter without Cap.ADMIN_GRANT is refused, and authority is
      resolved through registry.resolve(), never from a role string handed in by the caller
  V2  NO SELF-GRANT -- the escalation primitive core/comm/toolbox.py:862 already names
  V3  NO GRANTING WHAT YOU DO NOT HOLD -- caps and path_scope are both bounded by the granter's
  V4  TIME-BOXED BY DEFAULT -- --hours or an explicit --permanent; a ceiling on --hours
  V5  AUDIT BY CONSTRUCTION -- granted_by / granted_at / reason present on every written record,
      so an unexplained grant cannot be produced through this door even carelessly
  V6  A FAILED WRITE NEVER CORRUPTS THE ACL. This is the highest-severity pin here and it is not
      about permissions at all: core/trust/registry.py falls back to BOOTSTRAP_ROLES when the
      file cannot be READ, so a torn write is a fleet-wide availability event -- and it would
      hand back a floor that is not the ACL's considered answer. Atomic replace, validated
      before the swap.
  V7  REVOCABLE -- the reversibility path, so a bad grant does not need a git revert
  V8  the verb is REGISTERED with argparse, so check_advertised_verbs stops carrying it as a
      promise and the docstring at :3439 can stop telling operators to hand-edit JSON

Run: py -m pytest tests/test_t162_grant_verb.py -q
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _cli(*args, **kw):
    return subprocess.run([sys.executable, "agent_cli.py", *args],
                          cwd=ROOT, capture_output=True, text=True, timeout=180, **kw)


@pytest.fixture
def acl(tmp_path, monkeypatch):
    """A COPY of the real ACL. The live file is never written by these pins."""
    src = os.path.join(ROOT, "security", "acl.json")
    dst = tmp_path / "acl.json"
    shutil.copyfile(src, dst)
    monkeypatch.setenv("AKASHIC_ACL_PATH", str(dst))
    return dst


def _load(p):
    return json.loads(open(p, encoding="utf-8").read())


def _grant_for(p, agent):
    return next((g for g in _load(p)["grants"] if g.get("agent_id") == agent), None)


def _mod():
    import importlib
    from core.trust import grant_writer
    return importlib.reload(grant_writer)


# --------------------------------------------------------------------------- V1

def test_v1_authority_is_resolved_not_asserted(acl):
    g = _mod()
    with pytest.raises(PermissionError):
        g.grant("newbie", role="admin", by="deepseek-ui", reason="r", hours=1)
    assert _grant_for(acl, "newbie") is None, "a refused grant still wrote to the ACL"


# --------------------------------------------------------------------------- V2

def test_v2_no_self_grant(acl):
    g = _mod()
    with pytest.raises(PermissionError):
        g.grant("claude", role="super_admin", by="claude", reason="r", hours=1)


# --------------------------------------------------------------------------- V3

def test_v3_cannot_grant_what_you_do_not_hold(acl):
    """deepseek is `admin` and does NOT hold admin.grant, so it cannot mint a super_admin."""
    g = _mod()
    with pytest.raises(PermissionError):
        g.grant("newbie", role="super_admin", by="deepseek", reason="r", hours=1)


# --------------------------------------------------------------------------- V4

def test_v4_time_boxed_by_default(acl):
    g = _mod()
    with pytest.raises(ValueError):
        g.grant("newbie", role="member", by="claude", reason="r")          # neither hours nor permanent

    rec = g.grant("newbie", role="member", by="claude", reason="r", hours=4)
    assert rec["expires_at"], "a time-boxed grant has no expiry"

    with pytest.raises(ValueError):
        g.grant("newbie2", role="member", by="claude", reason="r", hours=10 ** 6)

    perm = g.grant("newbie3", role="member", by="claude", reason="r", permanent=True)
    assert perm["expires_at"] is None, (
        "a permanent grant must stay expressible -- 10 of the 11 existing grants are permanent, "
        "and a guard that cannot reproduce the current state gets bypassed on first use")


# --------------------------------------------------------------------------- V5

def test_v5_audit_by_construction(acl):
    g = _mod()
    rec = g.grant("newbie", role="member", by="claude", reason="onboarding the seat", hours=2)
    for f in ("granted_by", "granted_at", "reason"):
        assert rec.get(f), f"a written grant is missing {f}"
    with pytest.raises(ValueError):
        g.grant("newbie4", role="member", by="claude", reason="", hours=2)


# --------------------------------------------------------------------------- V6

def test_v6_a_failed_write_never_corrupts_the_acl(acl, monkeypatch):
    """The highest-severity pin, and it is an AVAILABILITY property, not a permissions one.

    registry.py falls back to BOOTSTRAP_ROLES when the file cannot be READ. A torn write
    therefore does not fail closed -- it replaces the fleet's considered authority with a
    hardcoded floor, silently, at the worst possible moment.
    """
    g = _mod()
    before = open(acl, encoding="utf-8").read()

    real = os.replace

    def boom(src, dst):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(Exception):
        g.grant("newbie", role="member", by="claude", reason="r", hours=1)
    monkeypatch.setattr(os, "replace", real)

    after = open(acl, encoding="utf-8").read()
    assert after == before, "a failed write left the ACL modified"
    json.loads(after)                     # and still parseable -- the fallback must not trigger


# --------------------------------------------------------------------------- V7

def test_v7_revocable(acl):
    g = _mod()
    g.grant("newbie", role="member", by="claude", reason="r", hours=4)
    assert _grant_for(acl, "newbie") is not None
    g.revoke("newbie", by="claude", reason="no longer needed")
    rec = _grant_for(acl, "newbie")
    assert rec is None or rec.get("role") == "quarantined", (
        "revoke neither removed the grant nor quarantined it")


# --------------------------------------------------------------------------- V8

def test_v8_the_verb_is_registered_and_no_longer_merely_planned():
    r = _cli("grant", "--list")
    assert r.returncode == 0, f"`grant --list` did not run: {(r.stderr or r.stdout)[:300]}"

    from scripts.checkers import check_advertised_verbs as C
    assert "grant" in C.registered_verbs(), "argparse does not know the verb"
    assert "grant" not in C.PLANNED, (
        "grant is built but still listed as PLANNED -- the promise list must shrink when a "
        "promise is kept, or it becomes an amnesty instead of a backlog")
