"""PRE-REGISTERED ACCEPTANCE -- the write door must consult the ACL.

Committed RED before implementation (M3 pre-registration).

THE DEFECT, verified at the code 2026-08-02 (Codex Sol's finding, confirmed by reading
the call chain rather than arguing it):

  * ``ToolBox.run_command`` (toolbox.py:1034) checks the process flag AND THEN
    ``resolve(self.agent_id).has(Cap.EXEC)`` -- the ACL is consulted per call,
    fail-closed on trust errors.
  * ``ToolBox._prewrite`` (toolbox.py:851), the shared guard for write_file/edit_file,
    checks ``self.allow_write``, path resolution, protected surfaces and advisory
    locks -- and NEVER calls ``resolve()``.
  * ``Grant.can_write(rel_path)`` is DEFINED at core/trust/registry.py:51 and CALLED
    NOWHERE in core/ or scripts/.

So ``path_scope`` -- the per-grant field that exists precisely to bound where an agent
may write -- protects nothing. Any seat started with ``--allow-write`` writes anywhere
in-root regardless of its grant. Enforcement is ASYMMETRIC: exec is ACL-gated, writes
are flag-gated.

BLAST RADIUS, measured before writing these pins (not assumed): the live seats
(claude/deepseek/kimi) all hold ``path_scope: ['*']`` and are unaffected; scoped seats
(deepseek-red, deepseek-review, deepseek-plumbing, gemini) gain the bound their grant
already declares; unregistered ids resolve quarantined and are refused. fnmatch was
confirmed empirically to cross '/' , so 'research/*' does match
'research/in-flight/x.md'.

These pins monkeypatch ``resolve`` so the contract is tested, never the live acl.json
(a pin that asserts today's grant table would break every time an operator edits it --
the brittle-pin class this repo has paid for three times).

Run::

    py -m pytest tests/test_write_door_acl_scope.py -q
"""
from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.comm import toolbox as tb_mod          # noqa: E402
from core.trust.capabilities import Cap          # noqa: E402
from core.trust.registry import Grant            # noqa: E402


def _box(tmp_path: Path, agent_id="deepseek-red", allow_write=True):
    """A ToolBox rooted in a scratch dir. trust=False keeps the exec-family gate out of
    the way; these pins are about the WRITE door only."""
    return tb_mod.ToolBox(tmp_path, allow_exec=False, trust=False, allow_secrets=False,
                          confirm=lambda _p: True, agent_id=agent_id, allow_write=allow_write)


def _grant(agent_id, scope, caps=(Cap.READ, Cap.WRITE), role="member"):
    return Grant(agent_id=agent_id, role=role, caps=set(caps), path_scope=list(scope),
                 granted_by="test", reason="pin")


def _patch_resolve(monkeypatch, grant_or_raise):
    def _fake(agent_id, *, verified=True):
        if isinstance(grant_or_raise, Exception):
            raise grant_or_raise
        return grant_or_raise
    monkeypatch.setattr("core.trust.registry.resolve", _fake, raising=True)


# ---------------------------------------------------------------- pin 1
def test_write_outside_path_scope_is_refused(tmp_path, monkeypatch):
    """THE DEFECT. A grant scoped to research/ must not be able to write core/.

    RED before the fix: _prewrite never consults the ACL, so the write lands.
    """
    _patch_resolve(monkeypatch, _grant("deepseek-red", ["research/*"]))
    box = _box(tmp_path)
    (tmp_path / "core").mkdir()

    out = box.write_file("core/pwned.py", "# should never land")

    assert not (tmp_path / "core" / "pwned.py").exists(), (
        "the write door let a research/-scoped grant write into core/ -- path_scope "
        "protects nothing (Grant.can_write is dead code at registry.py:51)")
    assert "REFUSED" in str(out).upper(), f"the refusal must be loud and named; got: {out!r}"


# ---------------------------------------------------------------- pin 2
def test_write_inside_path_scope_still_works(tmp_path, monkeypatch):
    """NO REGRESSION for a scoped grant acting INSIDE its scope. Passes before and after;
    this is the guard that stops the fix being a blanket refusal."""
    _patch_resolve(monkeypatch, _grant("deepseek-red", ["research/*"]))
    box = _box(tmp_path)
    (tmp_path / "research").mkdir()

    box.write_file("research/note.md", "hello")

    assert (tmp_path / "research" / "note.md").read_text(encoding="utf-8") == "hello", (
        "a scoped grant lost access INSIDE its own scope -- fnmatch must cross '/'")


# ---------------------------------------------------------------- pin 3
def test_wildcard_scope_writes_anywhere(tmp_path, monkeypatch):
    """NO REGRESSION for the live seats. claude/deepseek/kimi hold path_scope ['*'];
    measured before these pins were written. If this fails, the fix broke the fleet."""
    _patch_resolve(monkeypatch, _grant("deepseek", ["*"], role="admin"))
    box = _box(tmp_path, agent_id="deepseek")
    (tmp_path / "core").mkdir()

    box.write_file("core/legit.py", "x = 1")

    assert (tmp_path / "core" / "legit.py").exists(), (
        "a '*'-scoped grant was refused -- this breaks every live runner")


# ---------------------------------------------------------------- pin 4
def test_quarantined_agent_is_refused(tmp_path, monkeypatch):
    """An unregistered id resolves to the quarantined template (no WRITE, empty scope).
    It must not write even with --allow-write."""
    _patch_resolve(monkeypatch, _grant("ghost", [], caps=(Cap.READ,), role="quarantined"))
    box = _box(tmp_path, agent_id="ghost")

    out = box.write_file("research/x.md", "nope")

    assert not (tmp_path / "research" / "x.md").exists(), (
        "a quarantined id wrote through --allow-write")
    assert "REFUSED" in str(out).upper()


# ---------------------------------------------------------------- pin 5
def test_trust_error_fails_closed(tmp_path, monkeypatch):
    """Mirrors run_command's contract at toolbox.py:1047: a trust-layer exception must
    REFUSE, never fall through to the write. A broken guard that fails open is the
    RB-25 F1 hole reopened on the write lane."""
    _patch_resolve(monkeypatch, RuntimeError("trust layer exploded"))
    box = _box(tmp_path)

    out = box.write_file("research/x.md", "nope")

    assert not (tmp_path / "research" / "x.md").exists(), (
        "a trust-layer error fell through to the write -- must fail CLOSED")
    assert "REFUSED" in str(out).upper()


# ---------------------------------------------------------------- pin 6
def test_no_agent_identity_skips_the_acl_check(tmp_path, monkeypatch):
    """NO REGRESSION for non-runner use. run_command gates its ACL check behind
    `if self.agent_id:` (toolbox.py:1039) so an identity-less ToolBox (CLI/interactive)
    still works. The write door must mirror that exactly -- otherwise every
    non-runner ToolBox loses writes."""
    def _boom(*a, **k):
        raise AssertionError("resolve() must not be called without an agent identity")
    monkeypatch.setattr("core.trust.registry.resolve", _boom, raising=True)
    box = _box(tmp_path, agent_id=None)

    box.write_file("anywhere.md", "ok")

    assert (tmp_path / "anywhere.md").exists()


# ---------------------------------------------------------------- pin 7
def test_protected_surface_block_survives(tmp_path, monkeypatch):
    """NO REGRESSION on the existing guard: security/ and AGENTS.md stay blocked even
    for a '*' grant (self-escalation block, toolbox.py:865). The ACL check must be
    ADDITIVE to that, never a replacement."""
    _patch_resolve(monkeypatch, _grant("claude", ["*"], role="super_admin"))
    box = _box(tmp_path, agent_id="claude")
    (tmp_path / "security").mkdir()

    out = box.write_file("security/acl.json", "{}")

    assert not (tmp_path / "security" / "acl.json").exists()
    assert "protected" in str(out).lower()
