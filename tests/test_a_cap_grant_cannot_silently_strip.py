"""RED pins: `grant --caps` REPLACES the cap set, so adding one cap silently strips the rest.

PRE-REGISTRATION (M3). RED at this commit; the fix follows separately.

W252, filed 2026-10-06 while building the screenspace actuator, and the one item in the whole
wishlist triage flagged as able to QUIETLY DAMAGE THE TRUST LAYER.

I needed four `screen.*` tiers on the claude seat and wrote the obvious command::

    grant claude --caps screen.observe,screen.focus,screen.type,screen.act --hours 12

That would have left the seat holding FOUR caps instead of seventeen. core/trust/grant_writer.py:144::

    eff_caps = caps_from(caps) if caps is not None else set(tmpl["caps"])

``--caps`` is a REPLACE. A command whose stated purpose was to ADD screen tiers would have
stripped ``write``, ``exec`` and ``admin.grant`` from the only seat that can commit.

THREE THINGS HID IT, and each is a separate defect:

1. NO ADD VERB. The common intent -- "this seat also needs X" -- has no spelling, so every caller
   reaches for the one flag that exists and gets a replace.

2. THE DRY RUN SHOWED THE NEW SET AND NOT THE LOSS. It printed ``"role": null`` and the four new
   caps without ever saying "and nothing else". A replace is only legible BESIDE what it replaces,
   so the destructive half was invisible in the preview that exists to make it visible. This is
   the typed-absence family again: the dry run answered "what will it be" when the reader was
   asking "what will change".

3. THE FIRST ERROR POINTED AT THE WRONG PROBLEM. The real call raises on the missing ``--role``,
   not on the replace -- so a reader fixes the error they were shown, adds ``--role super_admin``,
   runs it again, and THAT is the version that actually strips the caps. An error message that
   sends you to the wrong fix is worse than no message.

I found it only because my own refusal text printed the same dangerous command back to the
operator as the remedy. A remedy that breaks the thing it repairs is worse than no remedy.

THE ASYMMETRY THAT MAKES THIS WORTH A LOUD GUARD: ``--permanent`` already has to be said out loud,
because an unbounded grant is a decision someone should have to type. Removing a seat's ``exec``
and ``admin.grant`` is at least as consequential and currently requires typing nothing at all.

NOT PINNED HERE, deliberately: the self-grant guard beside it (``agent_id == by`` ->
PermissionError, "a second party mints your authority") is correct and caught me cleanly. This is
the sibling hazard, not a complaint about that.

Run::

    py -m pytest tests/test_a_cap_grant_cannot_silently_strip.py -q
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _writer_src() -> str:
    return (ROOT / "core" / "trust" / "grant_writer.py").read_text(encoding="utf-8",
                                                                   errors="replace")


# ------------------------------------------------------------------ the defect
def test_there_is_a_way_to_ADD_a_cap_without_replacing_the_set():
    """THE PIN. The common intent needs a spelling, or everyone reaches for the destructive one.

    Asserted on the writer's signature rather than on the CLI, because the CLI flag is only the
    outer half: a caller using the module directly has the same hazard.
    """
    from core.trust import grant_writer
    fn = getattr(grant_writer, "write_grant", None) or getattr(grant_writer, "grant", None)
    assert fn is not None, "no grant-writing entry point found to inspect"
    params = set(inspect.signature(fn).parameters)
    assert params & {"add_caps", "drop_caps", "caps_add", "caps_drop"}, (
        "the only cap parameter is a full-set REPLACE (%r). `grant <seat> --caps screen.observe` "
        "reads as 'also give it screen.observe' and means 'give it ONLY screen.observe' -- which "
        "on the claude seat is 17 caps down to 1, including write, exec and admin.grant."
        % (sorted(p for p in params if "cap" in p),))


def test_a_replace_that_drops_held_caps_must_be_said_out_loud():
    """THE PIN THAT MATTERS, and the asymmetry is the argument.

    `--permanent` must be typed because an unbounded grant is a decision. Removing exec and
    admin.grant from a seat is at least as consequential and currently requires typing nothing.
    A replace that only ADDS is harmless and should stay quiet; a replace that REMOVES something
    the seat currently holds must be explicit.

    THIS PIN WAS VACUOUS ON ITS FIRST DRAFT. It searched the source for "replace" plus one of
    confirm/explicit/force -- and "explicitly --permanent" appears in an unrelated ValueError two
    functions away, so it passed against the untouched defect. Fourth time this week I have
    matched prose instead of behaviour. It now inspects the writer's SIGNATURE instead.
    """
    from core.trust import grant_writer
    fn = getattr(grant_writer, "write_grant", None) or getattr(grant_writer, "grant", None)
    assert fn is not None, "no grant-writing entry point found"
    params = set(inspect.signature(fn).parameters)
    ack = params & {"replace", "allow_drop", "confirm_replace", "force"}
    if ack:
        return                                   # an acknowledgement knob exists; good enough
    pytest.fail(
        "grant_writer takes no parameter by which a caller acknowledges a SHRINKING cap set "
        "(signature: %r). `--permanent` must be typed out loud because an unbounded grant is a "
        "decision; stripping exec and admin.grant from a seat is at least as consequential and "
        "currently requires typing nothing. core/trust/grant_writer.py:144 computes eff_caps and "
        "writes it with no comparison against what the seat already holds." % (sorted(params),))


def test_the_dry_run_shows_what_is_LOST_not_only_what_is_set():
    """A preview that lists the new set answers "what will it be". The reader is asking "what
    will change". For a replace those are different questions and only one of them is dangerous."""
    import subprocess
    r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "agent_cli.py"),
                        "grant", "claude", "--caps", "screen.observe", "--by", "daniel",
                        "--reason", "pin probe", "--hours", "1", "--dry-run"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT), timeout=180)
    out = (r.stdout + r.stderr).lower()
    if "refused" in out and "dry" not in out:
        pytest.skip("the dry run refused before rendering a plan: %s" % out[:200])
    assert ("remov" in out or "losing" in out or "->" in out or "dropped" in out), (
        "the dry run previews a cap REPLACE without naming a single cap it removes. Output:\n%s"
        % out[:500])


# ------------------------------------------------------------------ ratchets
def test_the_self_grant_guard_still_refuses():
    """RATCHET on the guard that DID work. `agent_id == by` must stay a PermissionError -- a
    second party mints your authority. Nothing in this slice may loosen it."""
    from core.trust import grant_writer
    fn = getattr(grant_writer, "write_grant", None) or getattr(grant_writer, "grant", None)
    try:
        # hours= is required (T151: a grant must be time-boxed or explicitly permanent). My first
        # draft omitted it and the ValueError fired BEFORE the self-grant check, so the ratchet
        # failed for a fixture reason while reporting that the trust guard was gone -- exactly the
        # false alarm a ratchet must never raise.
        fn(agent_id="claude", role="super_admin", by="claude", reason="self-grant probe", hours=1)
    except PermissionError:
        return
    except TypeError:
        pytest.skip("grant signature differs on this checkout")
    pytest.fail("a seat granted itself authority; the second-party rule is gone")


def test_a_granter_cannot_exceed_its_own_bounds():
    """RATCHET. `_bounded_by_granter` is the other half of the trust layer and must survive any
    change to how caps are computed -- it runs on `eff_caps`, the exact variable this slice
    touches."""
    src = _writer_src()
    assert "_bounded_by_granter(granter, eff_caps" in src, (
        "the granter-bounds check no longer runs over the effective caps; a cap-arithmetic change "
        "must not route around it")
