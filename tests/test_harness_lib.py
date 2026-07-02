"""Units for the shared harness lib (agent/harness/*, Integration Tiers H0-H2): scope
policy, anti-repeat seen-state, payload capture, veto policy, nudge rate limit, registry.
The Claude adapters exercise these through their own suites (test_sessionstart_autoboot,
test_plan_recall, test_learn_nudge, test_git_guard, test_locks); this file pins the lib's
own contracts so a future adapter can't bend them silently."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.harness import capture as capmod
from agent.harness import guards, nudge, registry, seen
from agent.harness import scope


# --- scope: one policy, every adapter ---------------------------------------------------------

def test_repo_root_is_this_repo():
    assert os.path.isfile(os.path.join(scope.repo_root(), "agent_cli.py"))


def test_under_root_repo_child_and_elsewhere():
    assert scope.under_root(scope.repo_root())
    assert scope.under_root(os.path.join(scope.repo_root(), "core", "recall"))
    assert not scope.under_root("C:\\Somewhere\\Else" if os.name == "nt" else "/somewhere/else")
    assert not scope.under_root("")


def test_is_home_exact_only():
    home = os.path.expanduser("~")
    assert scope.is_home(home)
    assert not scope.is_home(os.path.join(home, "Desktop", "Projects", "other"))


def test_session_scope_is_repo_or_home():
    assert scope.session_in_scope(scope.repo_root())
    assert scope.session_in_scope(os.path.expanduser("~"))
    assert not scope.session_in_scope("C:\\Somewhere\\Else" if os.name == "nt" else "/somewhere/else")


def test_file_scope_by_target_only():
    assert scope.file_in_scope(os.path.join(scope.repo_root(), "README.md"))
    assert not scope.file_in_scope("")
    assert not scope.file_in_scope(os.path.expanduser("~"))


def test_shell_scope_cwd_or_command():
    elsewhere = "C:\\Somewhere\\Else" if os.name == "nt" else "/somewhere/else"
    assert scope.shell_in_scope(scope.repo_root(), "echo hi")
    assert scope.shell_in_scope(elsewhere, "py agent_cli.py list"), "the command names the repo's door"
    assert scope.shell_in_scope(elsewhere, "cd E:/AI-Setup && ls")
    assert not scope.shell_in_scope(elsewhere, "echo hi")


# --- seen: shared anti-repeat state ------------------------------------------------------------

def test_seen_roundtrip_and_empty_session():
    sid = "harness-lib-seen"
    assert seen.load_seen(sid) == set()
    seen.mark_seen(sid, ["learn:experiment:a", "", None])
    seen.mark_seen(sid, ["learn:experiment:b"])
    assert seen.load_seen(sid) == {"learn:experiment:a", "learn:experiment:b"}
    assert seen.load_seen("") == set()
    seen.mark_seen("", ["learn:experiment:x"])   # no session -> silently dropped, never a crash


# --- capture: payload truth, bounded and truncated ---------------------------------------------

def test_capture_writes_truncated_snapshot(tmp_path):
    d = str(tmp_path / "cap")
    capmod.capture({"tool": "Shell", "blob": "x" * 1000}, d, label="probe")
    files = os.listdir(d)
    assert len(files) == 1 and "_probe_" in files[0]
    with open(os.path.join(d, files[0]), encoding="utf-8") as f:
        rec = json.load(f)
    assert rec["blob"].endswith("...[+600 chars]"), "shape survives, content is cut"


def test_capture_prunes_to_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(capmod, "_CAP_MAX", 3)
    d = str(tmp_path / "cap")
    for i in range(5):
        capmod.capture({"i": i}, d, label=f"n{i}")
    assert len(os.listdir(d)) <= 3


def test_capture_kill_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("AKASHIC_PAYLOAD_CAPTURE", "0")
    d = str(tmp_path / "cap")
    capmod.capture({"x": 1}, d)
    assert not os.path.isdir(d)


# --- guards: one rulebook, fail-closed on unverifiable locks ------------------------------------

def test_git_veto_real_policy():
    assert guards.git_veto("git add -A") != ""
    assert guards.git_veto("git add foo.py") == ""
    assert guards.git_veto("") == ""


def test_lock_veto_unset_id_fails_closed_with_teaching(monkeypatch):
    import core.comm.locks as L
    monkeypatch.setattr(L, "path_conflict",
                        lambda p, a, client=None: {"conflict": True, "held_by": "cursor",
                                                   "reason": "locked by cursor"})
    msg = guards.lock_veto("scripts/x.py", None, "set it in <YOUR-HARNESS-CONFIG>")
    assert "AKASHIC_AGENT_ID" in msg and "cursor" in msg and "<YOUR-HARNESS-CONFIG>" in msg, \
        "the teaching must name a place THIS harness's reader can actually reach"


def test_lock_veto_peer_conflict_and_clean_path(monkeypatch):
    import core.comm.locks as L
    monkeypatch.setattr(L, "path_conflict",
                        lambda p, a, client=None: {"conflict": True, "held_by": "cursor",
                                                   "reason": "locked by cursor"})
    assert guards.lock_veto("scripts/x.py", "claude", "hint") == "locked by cursor"
    monkeypatch.setattr(L, "path_conflict",
                        lambda p, a, client=None: {"conflict": False, "held_by": None, "reason": ""})
    assert guards.lock_veto("scripts/x.py", "claude", "hint") == ""
    assert guards.lock_veto("", None, "hint") == ""


# --- nudge: three-way rate limit ----------------------------------------------------------------

def test_nudge_once_per_target_capped_and_killable(tmp_path, monkeypatch):
    d = str(tmp_path)
    assert nudge.nudge_allowed(d, "s", "c:a")
    nudge.mark_nudged(d, "s", "c:a")
    assert not nudge.nudge_allowed(d, "s", "c:a"), "same target never nudges twice"
    for t in ("c:b", "c:c"):
        assert nudge.nudge_allowed(d, "s", t)
        nudge.mark_nudged(d, "s", t)
    assert not nudge.nudge_allowed(d, "s", "c:d"), "session cap (default 3)"
    monkeypatch.setenv("AKASHIC_LEARN_NUDGE", "0")
    assert not nudge.nudge_allowed(d, "s2", "c:x")


# --- registry: the capability matrix can't drift into flattery ----------------------------------

def test_every_harness_declares_every_tier():
    for h in registry.harnesses():
        for t in registry.TIERS:
            assert registry.capability(h, t), f"{h} is silent on {t} -- the matrix must stay honest"


def test_supported_reflects_the_pinned_limitations():
    assert registry.supported("claude-code", "T5"), "plan-time recall exists on Claude Code"
    assert not registry.supported("cursor", "T5"), "beforeSubmitPrompt cannot inject (pinned 2026-07-02)"
    assert registry.supported("cursor", "T4"), "postToolUseFailure is a direct fail signal"
    assert not registry.supported("bare-cli", "T4"), "manual contract, not automation"
    assert registry.capability("no-such-harness", "T0") == ""
