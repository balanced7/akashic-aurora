"""W152 pins: per-seat personal saves surface at boot.

Daniil, 2026-08-13 (verbatim): "we need to also make a way for individual seats like
you Vandor, Heimdall and Navi to also have personal saves and checkpoints."

The door is a CONVENTION over the existing notes plane -- house lineage: the 2026-06-29
checkpoint->note migration ("durable where-we-are state MIGRATED to write-once notes"),
now given per-seat identity. A save is a note titled `save:<agent>:<label>`; the write
door is the existing note verb; supersession and durability come free from the plane.
This slice adds ONLY the render: boot surfaces the seat's newest save with its restore
drill inline (the W146 law -- a pointed render carries its own drill).
"""
from types import SimpleNamespace as SN

import agent_cli


def _n(title, created="2026-08-13T01:00:00", body="x"):
    return SN(title=title, created_at=created, decision=body)


def test_s1_renders_newest_save_with_restore_drill():
    notes = [_n("save:claude:post-eye-arc")]
    line = agent_cli._boot_save_line("claude", notes)
    assert line.startswith("# personal save: save:claude:post-eye-arc")
    assert "[as of 2026-08-13]" in line
    assert "note claude --get save:claude:post-eye-arc" in line   # the restore drill


def test_s2_no_saves_no_line():
    notes = [_n("where-we-are"), _n("next-focus")]
    assert agent_cli._boot_save_line("claude", notes) == ""
    assert agent_cli._boot_save_line("claude", []) == ""
    assert agent_cli._boot_save_line("claude", None) == ""


def test_s3_newest_first_wins():
    """get_decisions returns newest-first; the FIRST matching save is the checkpoint
    a booting seat restores from. Older saves stay retrievable by title."""
    notes = [_n("save:claude:tonight", created="2026-08-13T02:00:00"),
             _n("save:claude:last-week", created="2026-08-06T02:00:00")]
    line = agent_cli._boot_save_line("claude", notes)
    assert "save:claude:tonight" in line
    assert "last-week" not in line


def test_s4_foreign_seat_saves_never_leak():
    """Vandor's boot never renders Heimdall's checkpoint, and vice versa -- identity
    is the point of a PERSONAL save."""
    notes = [_n("save:deepseek:heimdall-arc"), _n("save:kimi:navi-arc")]
    assert agent_cli._boot_save_line("claude", notes) == ""
    line = agent_cli._boot_save_line("deepseek", notes)
    assert "heimdall-arc" in line and "navi-arc" not in line


def test_s5_malformed_notes_never_break_boot():
    notes = [SN(title=None, created_at=None, decision=None),
             SN(title=123, created_at="", decision=""),
             _n("save:claude:ok", created="")]
    line = agent_cli._boot_save_line("claude", notes)
    assert "save:claude:ok" in line
    assert "[as of" not in line          # no created stamp when unknown -- never invent
