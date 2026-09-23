"""RED — the wishlist charter has three dispositions and only one of them has a door.

MEASURED 2026-09-23 on docs/WISHLIST.md: 226 wishes filed, 174 still open, `[x]` folded used
32 times, and `[~]` DECLINED used ZERO times in the ledger's entire history. Nothing has been
filed since 2026-08-24.

The charter at the top of that file names three outcomes -- each open wish either FOLDS into an
arc (record the T-number), stays OPEN, or is DECLINED with a reason; never delete, because
"declined wishes teach too". The `## Declined` section exists and reads, verbatim and unchanged
since it was written: "(none yet -- when one lands here, it keeps its reason.)"

WHY ONE SIDE STARVED. Filing is one frictionless command -- `py agent_cli.py wish`, auto-numbered,
W## echoed back, no approval. Curation is an unowned hand-edit of a 1,400-line tracked document
at a "natural gate" that names nobody. Traffic flows downhill exactly as you would predict, and
the consequence is not laziness: with decline unused, OPEN means two irreconcilable things --
"queued, your turn is coming" and "nobody will ever build this" -- and both render identically.
A filer reading 174 open wishes cannot tell which describes theirs, so the rational inference is
the pessimistic one. Filing stopped four weeks later.

This is the same law the rest of the house keeps relearning, at the ergonomics layer: a state
that cannot be expressed gets silently merged into its neighbour, and the reader is never told.

These pins hold the pure text transformation, because the risk here is mutating a long tracked
document rather than deciding anything clever.

  C1  decline MOVES the entry to ## Declined, keeps its full text, and records the reason
  C2  fold marks [x] in place and names the task that absorbed it
  C3  keep leaves it open and stamps a dated why-still, so "open" stops being the silent default
  C4  nothing is ever deleted -- every disposition preserves the original wish text verbatim
  C5  an unknown id refuses loudly rather than silently doing nothing
  C6  a duplicated id refuses, because the ledger's id space has COLLIDED (W00, W57..W69)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


DOC = """# Wishlist

**Convention:** file a wish the moment friction is felt.

---

## Open

- [ ] W159 (08-17, claude/Vandor) — **A GUARD THAT CHECKS THE FLAG.** Trigger: it hurt.
  Second line of the same wish.
- [ ] W05 (07-18, kimi F7) — re-derive triggers when source docs retract.
- [ ] W57 (07-19, claude) — first of a colliding pair.
- [ ] W57 (07-20, kimi) — second of a colliding pair.

## Folded (exemplars — the loop works)

- [x] W01 (07-18, kimi F8) — FOLDED night-run @abcb08b.

## Declined

*(none yet — when one lands here, it keeps its reason.)*
"""


def _apply(doc, wid, action, **kw):
    return agent_cli._wish_curate_apply(doc, wid, action, **kw)


# ------------------------------------------------------------------ C1 decline
def test_c1_decline_moves_to_declined_with_its_reason():
    out, msg = _apply(DOC, "W05", "decline", reason="superseded by the atlas rebuild",
                      seat="claude", today="09-23")
    assert "- [ ] W05" not in out, "C1: it must leave Open"
    assert "[~] W05" in out, "C1: it must land marked declined"
    assert "superseded by the atlas rebuild" in out, "C1: the reason is the whole point"
    assert "none yet" not in out, "C1: the placeholder retires when the first one lands"
    # and it lands under the Declined heading, not somewhere else
    tail = out.split("## Declined", 1)[1]
    assert "W05" in tail, "C1: it must be UNDER ## Declined"


def test_c4_decline_preserves_the_original_text_verbatim():
    out, _ = _apply(DOC, "W05", "decline", reason="r", seat="claude", today="09-23")
    assert "re-derive triggers when source docs retract" in out, \
        "C4: never delete -- declined wishes teach too"


def test_c4_multiline_wishes_survive_intact():
    out, _ = _apply(DOC, "W159", "decline", reason="r", seat="claude", today="09-23")
    assert "Second line of the same wish." in out, \
        "C4: a wish is a BLOCK, not a line; a curator must not truncate it"


# ------------------------------------------------------------------ C2 fold
def test_c2_fold_marks_in_place_and_names_the_task():
    out, msg = _apply(DOC, "W05", "fold", task="T401", seat="claude", today="09-23")
    assert "- [x] W05" in out
    assert "T401" in out
    assert "- [ ] W05" not in out


def test_c2_fold_without_a_task_refuses():
    with pytest.raises(ValueError):
        _apply(DOC, "W05", "fold", seat="claude", today="09-23")


# ------------------------------------------------------------------ C3 keep
def test_c3_keep_stays_open_but_stops_being_silent():
    out, msg = _apply(DOC, "W05", "keep", reason="still wanted, waiting on the eye slice",
                      seat="claude", today="09-23")
    assert "- [ ] W05" in out, "C3: keep means KEEP -- it stays open"
    assert "still wanted, waiting on the eye slice" in out
    assert "09-23" in out, "C3: a dated why-still is what makes 'open' a decision"


# ------------------------------------------------------------------ C5/C6 refusals
def test_c5_unknown_id_refuses_loudly():
    with pytest.raises(ValueError):
        _apply(DOC, "W999", "decline", reason="r", seat="claude", today="09-23")


def test_c6_a_colliding_id_refuses_rather_than_guessing():
    """The live ledger's id space has collided: W00 and W57..W69 each appear twice. Curating
    'W57' cannot know which one is meant, and picking one silently is how a ledger starts
    lying about its own history."""
    with pytest.raises(ValueError) as e:
        _apply(DOC, "W57", "decline", reason="r", seat="claude", today="09-23")
    assert "collid" in str(e.value).lower() or "ambiguous" in str(e.value).lower()


def test_decline_is_reported_as_a_success_not_a_failure():
    """The charter's own position: a declined wish is the loop WORKING. If the verb reports it
    as a loss, the zero stays zero for another five months."""
    _out, msg = _apply(DOC, "W05", "decline", reason="r", seat="claude", today="09-23")
    assert "declined" in msg.lower()
    assert "fail" not in msg.lower() and "error" not in msg.lower()
