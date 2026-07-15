"""T067 item 2 pins -- guarded exec: allowlisted command FAMILIES for unattended
runners (deepseek ergonomics retro 2026-07-14, research/reviewed/deepseek-ergonomics-
retro-2026-07-14.md item 2: "guarded exec -- allowlisted command families (pytest,
agent_cli read verbs) behind the guarded-write approval model, kills the
ask-Daniel-to-run-a-test asymmetry").

THE CUT (build refinements, T073 precedent):
  G1  UNATTENDED exec (trust=True, the runner's auto-approve mode) is FAMILIES-ONLY:
      pytest runs + agent_cli READ verbs. The generic shell survives only on the
      INTERACTIVE path (trust=False), where a human confirms each command.
  G2  Allowlisted commands run shell=False (shlex-split) -- metacharacters are not
      interpreted, and any ; | & > < ` $ ( ) newline in the string REFUSES loudly.
  G3  pytest family forces _AISETUP_TEST_ISOLATED=1 into the child env and caps the
      timeout (a verify run must never touch live backends by default).
  G4  agent_cli family allows READ verbs only; mutating verbs (note, learn, wrap,
      bifrost-send, task done/claim, lock...) REFUSE with teaching text.
  G5  Cap.EXEC is consulted at the DOOR when an agent identity is present -- the ACL
      (security/acl.json) is the authority; the flag alone is not enough in runner
      mode. (The write path has always had --allow-write + scope; exec now has
      --allow-exec + cap + families.)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

from scripts import deepseek_chat as dc

REPO = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _tb(trust=True, allow_exec=True, agent_id=None):
    return dc.ToolBox(REPO, allow_exec=allow_exec, trust=trust, allow_secrets=False,
                      confirm=lambda prompt: False, agent_id=agent_id)


# ---------------------------------------------------------------- G1 families allowed
def test_g1_unattended_pytest_family_runs():
    out = _tb().run_command("py -m pytest --version", timeout=60)
    assert "pytest" in out.lower() and "REFUSED" not in out, out


def test_g1_unattended_agent_cli_read_verb_runs():
    out = _tb().run_command("py agent_cli.py discover", timeout=120)
    assert "REFUSED" not in out and ("verb" in out.lower() or "boot" in out.lower()), out[:300]


def test_g1_unattended_generic_command_refused():
    out = _tb().run_command("git push origin master")
    assert "REFUSED" in out and "famil" in out.lower(), \
        f"unattended exec must be families-only, got: {out[:200]}"


def test_g1_unattended_arbitrary_python_refused():
    out = _tb().run_command('python -c "print(1)"')
    assert "REFUSED" in out


# ---------------------------------------------------------------- G2 metachar refusal
def test_g2_shell_metacharacters_refused_even_inside_a_family():
    for cmd in ("py -m pytest tests; git push",
                "py -m pytest tests && echo pwned",
                "py agent_cli.py notes | tee out.txt",
                "py -m pytest > secrets.txt",
                "py -m pytest `whoami`"):
        out = _tb().run_command(cmd)
        assert "REFUSED" in out, f"metachar survived: {cmd!r} -> {out[:120]}"


# ---------------------------------------------------------------- G3 isolated env forced
def test_g3_pytest_family_forces_isolation_env(monkeypatch):
    seen = {}
    import subprocess as sp

    def fake_run(argv, **kw):
        seen["argv"], seen["env"] = argv, kw.get("env")

        class R:
            stdout, stderr, returncode = "1 passed", "", 0
        return R()

    monkeypatch.setattr(dc.subprocess, "run", fake_run)
    _tb().run_command("py -m pytest tests/test_t073_wake_longlived.py -q", timeout=300)
    assert seen["argv"][0:3] == ["py", "-m", "pytest"], "shell=False argv split (G2)"
    assert (seen["env"] or {}).get("_AISETUP_TEST_ISOLATED") == "1", \
        "G3: an unattended verify run must never touch live backends"


# ---------------------------------------------------------------- G4 read verbs only
def test_g4_mutating_agent_cli_verbs_refused():
    for cmd in ("py agent_cli.py note claude --title x --note y",
                "py agent_cli.py learn claude --experiment e --tried t --result r --recommend c",
                "py agent_cli.py wrap --commit",
                "py agent_cli.py bifrost-send claude hi --to user",
                "py agent_cli.py lock deepseek somefile"):
        out = _tb().run_command(cmd)
        assert "REFUSED" in out and "read" in out.lower(), f"mutator survived: {cmd!r}"


# ---------------------------------------------------------------- G5 the ACL layer
def test_g5_exec_cap_checked_when_agent_identity_present(monkeypatch):
    from core.trust import registry
    from core.trust.capabilities import Cap

    class NoExecGrant:
        role = "member"

        def has(self, c):
            return c != Cap.EXEC

    monkeypatch.setattr(registry, "resolve", lambda agent_id, **k: NoExecGrant())
    out = _tb(agent_id="deepseek-ui").run_command("py -m pytest --version")
    assert "REFUSED" in out and "acl" in out.lower(), \
        "G5: without Cap.EXEC the door refuses regardless of the runner flag"


def test_g5_flagless_toolbox_still_fully_disabled():
    out = _tb(allow_exec=False).run_command("py -m pytest --version")
    assert "DISABLED" in out, "the original --allow-exec gate is unchanged"


# ---------------------------------------------------------------- G1 interactive path intact
def test_g1_interactive_generic_still_confirm_gated():
    asked = {}

    def confirm(prompt):
        asked["prompt"] = prompt
        return False

    tb = dc.ToolBox(REPO, allow_exec=True, trust=False, allow_secrets=False, confirm=confirm)
    out = tb.run_command("git status")
    assert "DENIED" in out and "git status" in asked.get("prompt", ""), \
        "interactive generic exec stays human-confirmed (Daniel's own /exec path)"
