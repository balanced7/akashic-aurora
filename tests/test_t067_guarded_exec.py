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
  G6  RECOVERY family (2026-09-09, Daniil's standing exec-fix ask): `tasklist` (pure
      read) and `taskkill /PID <digits> /F` (exactly one numeric pid, no /IM, no
      wildcards) so Cap.EXEC seats can self-drive a kill+respawn without a
      super-admin doing it by hand every time. The runner_lock TTL means a
      force-killed seat's lock self-expires even without a graceful exit.
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


# ------------------------------------------------------- G4b recovery verbs reachable
def test_g4b_recovery_read_verbs_are_reachable():
    # operator-authorized 2026-08-31 (door_read_allowlist_gap): a live admin seat must be
    # able to inspect the fleet and drive recovery from inside a session. These are pure
    # reads that were ungated-absent, silently blocking the exact levers recovery needs.
    for verb in ("roster", "bench", "mailbox", "verbs", "help"):
        out = _tb().run_command(f"py agent_cli.py {verb}", timeout=120)
        assert "REFUSED" not in out, f"read verb {verb!r} still refused: {out[:200]}"


def test_g4b_recovery_verbs_do_not_open_mutations():
    # widening the READ allowlist must not reach a mutating verb riding the same word shape.
    out = _tb().run_command("py agent_cli.py bench --consume")
    assert "REFUSED" in out, f"mutating flag on a read verb survived: {out[:200]}"


# ------------------------------------------------- G6 recovery family (taskkill/tasklist)
# Daniil 2026-09-09 verbatim on the bus: "Please fix the exec for all the parties
# permanently so that everything doesn't fall to you every time something breaks."
# Runner seats holding Cap.EXEC (deepseek/navi/sol/kimi) can now self-drive a narrow
# process-recovery primitive without a super-admin doing every kill+respawn by hand.
def test_g6_recovery_tasklist_runs():
    out = _tb().run_command("tasklist", timeout=30)
    assert "REFUSED" not in out, out[:200]


def test_g6_recovery_tasklist_with_flags_refused():
    out = _tb().run_command("tasklist /FI \"foo\"")
    assert "REFUSED" in out


def test_g6_recovery_taskkill_narrow_shape_runs():
    # a PID that (almost certainly) does not exist -- exercises the ALLOW path without
    # touching a real process; taskkill returns its own "not found" text, never REFUSED.
    out = _tb().run_command("taskkill /PID 999999 /F", timeout=30)
    assert "REFUSED" not in out, out[:200]


def test_g6_recovery_taskkill_by_name_refused():
    out = _tb().run_command("taskkill /IM notepad.exe /F")
    assert "REFUSED" in out and "/IM" in out


def test_g6_recovery_taskkill_without_force_refused():
    out = _tb().run_command("taskkill /PID 999999")
    assert "REFUSED" in out


def test_g6_recovery_taskkill_multiple_pids_refused():
    out = _tb().run_command("taskkill /PID 111 /PID 222 /F")
    assert "REFUSED" in out


# ---------------------------------------------- G7 read-only git family (2026-09-09)
# Daniil 2026-09-09 verbatim: "I trust you guys, can you make that for yourself, heimdall,
# sunshine and rill?" -- widen the EXEC family gate (not the ACL) with READ-ONLY git verbs
# so Cap.EXEC seats can inspect/diff/log/status without a super-admin. git.read is already
# in every admin's caps; the family gate refused `git` outright, which is the whack-a-mole.
# SHAPE-CONSTRAINED exactly like the G6 recovery family: no metachars (G2 already refuses),
# a closed read-only verb whitelist, and every mutating git verb (commit/add/push/checkout/
# reset/mv/rm/...) stays refused. GETURI-0: scope, not --git-dir arbitrariness.
G7_READ_VERBS = ("status", "diff", "log", "show")

def test_g7_readonly_git_verbs_run():
    for v in G7_READ_VERBS:
        out = _tb().run_command(f"git {v}", timeout=30)
        assert "REFUSED" not in out, f"read-only git verb {v!r} refused: {out[:200]}"


def test_g7_diff_and_log_flags_accepted():
    # --no-pager keeps these non-interactive; plain-passthrough flags are fine (they are
    # still read-only), the MUTATION surface is what this family closes, not flag shapes.
    for cmd in ("git diff --stat", "git --no-pager log --oneline -5", "git status --short"):
        out = _tb().run_command(cmd, timeout=30)
        assert "REFUSED" not in out, f"{cmd!r} refused: {out[:200]}"


def test_g7_mutating_git_verbs_refused():
    for v in ("add", "commit", "push", "pull", "fetch", "checkout", "reset", "merge",
              "rebase", "cherry-pick", "stash", "mv", "rm", "branch", "tag", "clone",
              "switch", "restore"):
        out = _tb().run_command(f"git {v}", timeout=30)
        assert "REFUSED" in out, f"mutating git verb {v!r} survived the gate: {out[:200]}"


def test_g7_git_dir_flag_refused():
    # --git-dir / -C would let a caller point git at an ARBITRARY repository (or a bare
    # tree) to read outside the repo -- refused, not allowed, keeping this family scoped.
    out = _tb().run_command("git -C /tmp status")
    assert "REFUSED" in out, "git -C must be refused (scope escape)"


def test_g7_git_force_flag_refused():
    # -f/--force on an otherwise-read verb is still a mutation surface; refuse it.
    out = _tb().run_command("git diff -f")
    assert "REFUSED" in out, "git -f must be refused (force/mutate)"

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
