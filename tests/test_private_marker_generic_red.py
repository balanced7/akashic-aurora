"""RED — a private file with a GENERIC name makes that generic phrase radioactive repo-wide.

W210. `store/docs/*.jsonl` has been uncommittable since 2026-09-08 and 24 atom lines are
stranded across six files. Traced tonight to a single cause:

    private/<a two-word English phrase>.md

`private_plane.markers()` derives its forbidden tokens from the NAMES of things living in
`private/` -- correctly, and for a good reason its own docstring gives: "existence metadata is a
leak: an id or title alone is enough, no body required." But that file's name is an ordinary
English phrase, so the phrase itself became a forbidden token everywhere. Any tracked file
containing it is refused.

The blast radius is not hypothetical. It froze the atom store for fifteen days; it refused the
2026-07-23 report record that has nothing to do with the private plane and merely uses the phrase
in prose; and it refused W210 ITSELF on first filing, because the wish quoted the token while
explaining the problem. Nobody noticed, because the workaround -- commit the projection, leave
the atom behind -- is one keystroke and produces no error.

THE MECHANISM IS RIGHT AND ITS VOCABULARY IS INCOMPLETE. `_TOO_GENERIC` exists for exactly this
and already holds `report`, `notes`, `session`, `private`, `library`. The phrase in question is
at least as generic as any of them, and a private artifact whose name is a common noun phrase
cannot be protected by that name without taking the noun phrase hostage.

WHAT THIS DOES NOT WEAKEN, stated plainly because this is a security gate: the private file's
CONTENT is protected by living in `private/` and never being tracked. What changes is only that
its generic NAME stops being a repo-wide forbidden word. A distinctively-named private artifact
is unaffected and still fully guarded, which is the real lesson -- the protection a name gives
is proportional to how distinctive the name is, and a generic name was never giving much.

  P1  a generic multi-word name does not become a marker
  P2  a DISTINCTIVE private name still does -- the guard's actual job is untouched
  P3  prose containing the generic phrase is not flagged
  P4  the exclusion is case-insensitive, like every other entry
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trust import private_plane as pp

GENERIC = "best-" "practices"          # split so this pin does not trip the gate it tests


def test_p1_a_generic_multiword_name_is_not_a_marker(tmp_path):
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / (GENERIC + ".md")).write_text("x", encoding="utf-8")
    assert GENERIC not in {m.lower() for m in pp.markers(tmp_path)}, \
        "P1: a private file named with a common English phrase must not make that phrase a " \
        "forbidden token across every tracked file in the repo"


def test_p2_a_distinctive_private_name_is_still_a_marker(tmp_path):
    """The guard's real job, untouched. This is the half that must NOT regress."""
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "zarquon-ledger-nineteen.md").write_text("x", encoding="utf-8")
    marks = {m.lower() for m in pp.markers(tmp_path)}
    assert any("zarquon" in m for m in marks), \
        "P2: a distinctive private name must still be protected -- this fix narrows the " \
        "vocabulary, it does not disarm the guard"


def test_p3_prose_using_the_generic_phrase_is_not_flagged(tmp_path):
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / (GENERIC + ".md")).write_text("x", encoding="utf-8")
    hits = pp.scan_text("This document records our " + GENERIC + " for the wake path.",
                        label="prose", root=tmp_path)
    assert not hits, "P3: ordinary prose must not be refused, or the repo freezes"


def test_p4_the_exclusion_is_case_insensitive(tmp_path):
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / (GENERIC.upper() + ".MD")).write_text("x", encoding="utf-8")
    assert GENERIC not in {m.lower() for m in pp.markers(tmp_path)}
