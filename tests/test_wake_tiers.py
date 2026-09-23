"""WAKE TIERS -- tier 0 must not starve on tier 3 volume.

THE INCIDENT THESE PINS HOLD (2026-09-23). The operator sent four DIRECTED messages
(to=claude, kind=chat) over Discord across five days. Every one SHOULD have woken this seat:
wake_worthy() carries an operator override that outranks the kind allowlist, and because the
messages were directed rather than to="*" the 2026-08-31 lounge carve-out did not apply. The
predicate would have returned True on all four.

None woke anything, because nothing was armed to ask it. And nothing stayed armed because a
watcher armed over unconsumed mail fires immediately BY DESIGN (wake_block's SEED rule). With
~1,383 informational messages standing on the work lane, every arm exited within seconds.

The remedy is NOT to consume the backlog so a watcher can survive -- that would drain mail the
real reader has never seen, which is exactly what detect-without-consume exists to prevent. It
is a FLOOR: arm at tier 1 and the informational backlog cannot fire the watcher, while an
operator message still fires it instantly, and NOTHING IS CONSUMED.

  T1  a DIRECTED operator message is tier 0
  T2  an UNDIRECTED to="*" operator chat stays AMBIENT -- Daniil's own lounge ruling survives
  T3  the ladder ranks directed asks above settlements above ambient
  T4  a broadcast can never be tier 1 or 2, whatever its kind
  T5  THE INCIDENT: a floor lets a seat stay armed over a backlog and still wake for the
      operator -- consuming nothing
  T6  the default floor changes NOTHING (strangler discipline)
  T7  the floor CONFESSES what it held -- a floor that hid its own suppression would be the
      silence-reads-as-absence defect rebuilt inside the fix for it
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import wake_tiers as wt
from scripts import bifrost_wake as bw

OPS = frozenset({"user", "daniel", "daniil"})


def _m(kind="chat", frm="daniil", to="claude", meta=None):
    return SimpleNamespace(kind=kind, frm=frm, to=to, content="x", meta=meta or {})


def _tier(m, agent="claude", incarnation=""):
    return wt.wake_tier(m, agent=agent, incarnation=incarnation, operator_ids=OPS)


# ------------------------------------------------------------------ T1 / T2 operator
def test_t1_a_directed_operator_message_is_tier_zero():
    assert _tier(_m(kind="chat", frm="daniil", to="claude")) == wt.OPERATOR, \
        "T1: the four lost Discord messages were exactly this shape -- to=claude, kind=chat"


def test_t2_the_undirected_lounge_broadcast_stays_ambient():
    """Daniil, 2026-08-31: 'a space to talk to everyone without having to worry about waking
    everyone at once.' A tier that ignored his ruling would be a second opinion on a settled
    question."""
    assert _tier(_m(kind="chat", frm="daniil", to="*")) == wt.AMBIENT
    # ...but anything else he sends to everyone is NOT the lounge
    assert _tier(_m(kind="request", frm="daniil", to="*")) == wt.OPERATOR


# ------------------------------------------------------------------ T3 / T4 the ladder
def test_t3_the_ladder_ranks_asks_above_settlements_above_ambient():
    assert _tier(_m(kind="request", frm="deepseek")) == wt.DIRECTED_ASK
    assert _tier(_m(kind="handoff", frm="deepseek")) == wt.DIRECTED_ASK
    assert _tier(_m(kind="reply", frm="deepseek")) == wt.SETTLEMENT
    assert _tier(_m(kind="note", frm="deepseek")) == wt.AMBIENT
    assert wt.DIRECTED_ASK < wt.SETTLEMENT < wt.AMBIENT


def test_t4_a_broadcast_is_never_an_obligation():
    """broadcast-visibility is not directed-ownership: a to=* message opens no obligation on
    any one seat, so it cannot outrank directed mail whatever its kind."""
    for kind in ("request", "handoff", "reply", "question"):
        assert _tier(_m(kind=kind, frm="deepseek", to="*")) == wt.AMBIENT, \
            f"T4: a broadcast {kind} must stay ambient"


# ------------------------------------------------------------------ T5 THE INCIDENT
def test_t5_a_floor_survives_a_backlog_and_still_wakes_for_the_operator():
    """The reproduction. 200 ambient messages standing on the lane, one operator message
    behind them. At floor 1 the backlog is inert and the operator still gets through."""
    backlog = [_m(kind="note", frm="kimi") for _ in range(200)]
    backlog += [_m(kind="chat", frm="deepseek", to="*") for _ in range(200)]
    operator = _m(kind="chat", frm="daniil", to="claude")

    fired = [x for x in backlog if wt.admits(_tier(x), wt.DIRECTED_ASK)]
    assert fired == [], \
        "T5: 400 informational messages must not fire a watcher armed at the directed-ask floor"

    assert wt.admits(_tier(operator), wt.DIRECTED_ASK), \
        "T5: the operator must still get through the same floor -- otherwise the cure is the disease"

    # and the strictest floor still admits the operator, which is the whole point of tier 0
    assert wt.admits(_tier(operator), wt.OPERATOR)


# ------------------------------------------------------------------ T6 strangler
def test_t6_the_default_floor_changes_nothing():
    """AMBIENT is the default, so importing this module alters no existing behaviour."""
    for m in (_m(kind="note", frm="kimi"), _m(kind="reply", frm="sol"),
              _m(kind="chat", frm="daniil", to="*"), _m(kind="request", frm="deepseek")):
        assert wt.admits(_tier(m), wt.AMBIENT), \
            "T6: at the default floor every tier is admitted -- no silent narrowing"
    # the contract, not an implementation detail: watch() must DEFAULT to the ambient floor,
    # so an existing caller that knows nothing about tiers keeps its exact behaviour
    assert bw.watch.__kwdefaults__.get("min_tier") == wt.AMBIENT, \
        "T6: the default floor must be AMBIENT, or landing tiers silently narrows every seat"


# ------------------------------------------------------------------ T7 the floor confesses
def test_t7_the_watcher_names_its_floor_in_plain_words():
    """A floor that suppressed silently would rebuild tonight's defect inside tonight's fix."""
    assert wt.tier_name(wt.OPERATOR) == "operator"
    assert wt.tier_name(wt.DIRECTED_ASK) == "directed-ask"
    assert bw.wake_tiers_name(wt.OPERATOR) == "operator", \
        "T7: the watcher's report helper must resolve the same names"
    assert bw.wake_tiers_name(99) == "ambient", \
        "T7: an unknown tier resolves, never raises -- totality, per kinds.py's own law"


# ------------------------------------------------------------------ totality
def test_every_message_resolves_to_a_tier():
    """An unlisted kind loses PRIORITY; it must never lose VISIBILITY."""
    for kind in ("", "bizarre_new_kind", "trace", "steer"):
        t = _tier(_m(kind=kind, frm="whoever"))
        assert t in (wt.OPERATOR, wt.DIRECTED_ASK, wt.SETTLEMENT, wt.AMBIENT)
