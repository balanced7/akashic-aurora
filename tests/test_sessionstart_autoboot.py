"""SessionStart light auto-boot (friction audit D2 / fix #2): the whisper is tiered by
where the session starts, silent-when-empty, killable, and never breaks session start."""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.hooks import claude_sessionstart as hook

_REPO = hook._ROOT_RAW
_HOME = os.path.expanduser("~")
_ELSEWHERE = "C:\\Somewhere\\Else" if os.name == "nt" else "/somewhere/else"


def _quiet_sources(monkeypatch, notes="notes: t1 [07-01]; t2 [06-30]",
                   funnel="funnel: 10 lessons | surfaced 5 | votes useful=1 noise=0 | helped 1 | last 7d: +2 lesson(s), 1 flip(s)",
                   unread=0, draft=False):
    monkeypatch.setattr(hook, "_notes_line", lambda limit=3: notes)
    monkeypatch.setattr(hook, "_funnel_line", lambda: funnel)
    monkeypatch.setattr(hook, "_unread_count", lambda agent_id: unread)
    monkeypatch.setattr(hook, "_draft_fresh", lambda: draft)


def test_repo_cwd_gets_the_compact_whisper(monkeypatch):
    _quiet_sources(monkeypatch)
    out = hook.build_autoboot_context(_REPO, "claude")
    assert "[akashic]" in out and "notes:" in out and "funnel:" in out
    assert "boot claude" in out, "the one-hop full-boot command is always taught"
    assert len(out.splitlines()) <= 10, "a whisper, not a wall (context rot)"


def test_home_cwd_counts_as_read_bootstrap_flow(monkeypatch):
    _quiet_sources(monkeypatch)
    assert "notes:" in hook.build_autoboot_context(_HOME, "claude")


def test_child_of_home_is_not_home(monkeypatch):
    """Desktop/Projects/... are OTHER projects -- only the home dir itself is the launch pad."""
    _quiet_sources(monkeypatch)
    child = os.path.join(_HOME, "Desktop", "Projects", "other")
    assert hook.build_autoboot_context(child, "claude") == ""


def test_elsewhere_is_silent_when_nothing_new(monkeypatch):
    _quiet_sources(monkeypatch, unread=0, draft=False)
    assert hook.build_autoboot_context(_ELSEWHERE, "claude") == ""


def test_elsewhere_whispers_one_line_when_mail_waits(monkeypatch):
    _quiet_sources(monkeypatch, unread=2, draft=True)
    out = hook.build_autoboot_context(_ELSEWHERE, "claude")
    assert out and len(out.splitlines()) == 1, "one line, pointing home"
    assert "2 unread" in out and "boot claude" in out


def test_kill_switch(monkeypatch):
    _quiet_sources(monkeypatch, unread=5, draft=True)
    monkeypatch.setenv("AKASHIC_AUTOBOOT", "0")
    assert hook.build_autoboot_context(_REPO, "claude") == ""


def test_broken_source_drops_out_not_blanks(monkeypatch):
    _quiet_sources(monkeypatch)
    monkeypatch.setattr(hook, "_funnel_line", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    out = hook.build_autoboot_context(_REPO, "claude")
    assert "notes:" in out and "funnel:" not in out


def test_all_sources_empty_stays_silent(monkeypatch):
    _quiet_sources(monkeypatch, notes="", funnel="", unread=0, draft=False)
    assert hook.build_autoboot_context(_REPO, "claude") == ""


def test_main_emits_valid_additional_context_json(monkeypatch, capsys):
    _quiet_sources(monkeypatch)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"cwd": _REPO})))
    assert hook.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "[akashic]" in payload["hookSpecificOutput"]["additionalContext"]


def test_main_survives_garbage_stdin(monkeypatch, capsys):
    """Unparseable stdin falls back to cwd; with every source empty the hook stays silent."""
    _quiet_sources(monkeypatch, notes="", funnel="", unread=0, draft=False)
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert hook.main() == 0
    assert capsys.readouterr().out.strip() == ""
