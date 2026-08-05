"""PRE-REGISTERED ACCEPTANCE (T177) -- the kind plane gets the guard the verb plane has.

check_door_parity guards the VERB surface against silent fragmentation: explicit manifest, fail on
a new unclassified verb, ratcheted debt. The KIND surface had no equivalent, which is how 31 kinds
accumulated 14 hand-maintained policy sets with 55% of kinds in one set or fewer, and how a peer
gate was lost to kind=review belonging to no set at all.

THIS FILE IS THE DOCTRINE MADE TESTABLE. A rule that lives only in prose requires someone to
REMEMBER it, which is the precise failure the rule describes.

  K1  two files defining the same *KINDS identifier with DIFFERENT membership is a FAIL   (T175)
  K2  ...and the same identifier with IDENTICAL membership is fine (duplication != conflict)
  K3  a kind appearing on two planes is a FAIL unless it is classified in the manifest    ('note')
  K4  bus-plane ORPHANS (a kind in <=1 policy set) are counted -- the born-silent population
  K5  redundancy candidates are REPORT-ONLY and can never change the exit code
  K6  the PLANES manifest must be TOTAL: a newly added *KINDS set with no plane FAILS
  K7  resolution is TOTAL -- an unknown kind resolves to UNCLASSIFIED, never a silent False

K5 exists because this instrument was WRONG. Run across planes, the identical-signature test
called 10 kinds redundant that were not: command/file_edit/tool_call share a blank row on every
bus axis, yet event_promoter weights them 3/2/1. A consumer does act on the difference. An
instrument that produced a confident false "merge these" may advise and may never gate.

K6 is the doctrine's own bedside test, automated: "when I add this, must I remember to tell
something else?" A new policy set must declare its plane, and the checker -- not a person's
memory -- is what asks.

Run: py -m pytest tests/test_t177_kind_policy_guard.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.checkers import check_kind_policy as C  # noqa: E402


# --- synthetic fixtures: the pins test the MECHANISM, not today's tree -------------------
def _sets(**kw):
    """{(file, NAME): set} keyed the way discovery returns it."""
    out = {}
    for key, members in kw.items():
        fname, _, name = key.partition("__")
        out[(f"{fname}.py", name)] = set(members)
    return out


PLANES = {"BUS_A": "bus", "BUS_B": "bus", "EVENT_A": "event"}


def test_k1_same_identifier_different_membership_is_a_conflict():
    s = _sets(alpha__SKIP_KINDS=["trace", "steer"], beta__SKIP_KINDS=["trace", "halt"])
    conflicts = C.duplicate_identifier_conflicts(s)
    assert len(conflicts) == 1, "one identifier, two memberships -- that is the T175 defect"
    name, detail = conflicts[0][0], str(conflicts[0])
    assert name == "SKIP_KINDS"
    assert "halt" in detail and "steer" in detail, "the conflict must NAME the disagreement"


def test_k2_same_identifier_identical_membership_is_not_a_conflict():
    s = _sets(alpha__SKIP_KINDS=["trace", "steer"], beta__SKIP_KINDS=["steer", "trace"])
    assert C.duplicate_identifier_conflicts(s) == [], (
        "duplication is not conflict -- two files may legitimately agree")


def test_k3_unclassified_cross_plane_collision_fails_but_a_classified_one_does_not():
    s = _sets(a__BUS_A=["handoff", "note"], c__EVENT_A=["note", "tool_call"])
    assert [c[0] for c in C.cross_plane_collisions(s, PLANES, allowed={})] == ["note"]
    ok = C.cross_plane_collisions(s, PLANES, allowed={"note": "bus cue vs durable record -- T176"})
    assert ok == [], "a collision with a written rationale is a recorded decision, not drift"


def test_k4_orphans_are_the_kinds_in_one_policy_set_or_fewer():
    s = _sets(a__BUS_A=["handoff", "lonely"], b__BUS_B=["handoff"])
    orphans = dict(C.orphans(s, PLANES, plane="bus"))
    assert "lonely" in orphans and orphans["lonely"] == 1
    assert "handoff" not in orphans, "two sets is not an orphan"


def test_k5_redundancy_is_advisory_and_cannot_gate():
    s = _sets(a__BUS_A=["question", "request"], b__BUS_B=["question", "request"])
    groups = C.redundancy_candidates(s, PLANES, plane="bus")
    assert sorted(groups[0]) == ["question", "request"], "identical signature = merge CANDIDATE"
    assert C.is_advisory("redundancy") is True, (
        "this instrument produced 10 confident false positives across planes; it may never gate")


def test_k6_the_planes_manifest_must_be_total():
    s = _sets(a__BUS_A=["handoff"], z__BRAND_NEW_KINDS=["surprise"])
    missing = C.unassigned_sets(s, PLANES)
    assert missing == ["BRAND_NEW_KINDS"], (
        "a new policy set with no declared plane must FAIL -- otherwise someone has to remember "
        "to classify it, which is the exact failure this guard exists to prevent")


def test_k7_resolution_is_total_unknown_is_never_a_silent_false():
    s = _sets(a__BUS_A=["handoff"])
    assert C.resolve("handoff", "BUS_A", s) == (True, "classified")
    verdict, why = C.resolve("never_seen", "BUS_A", s)
    assert verdict is False and why == "UNCLASSIFIED", (
        "an unregistered kind must resolve to UNCLASSIFIED, never to a bare False that reads "
        "identical to a deliberate exclusion -- the whole census finding in one assertion")


def test_k8_the_ratchet_can_actually_COUNT_this_checkers_output():
    """THE WIRING PIN, and it caught a real one.

    A checker is only as good as the number it hands the ratchet. pre_commit._count_violations
    enters counting mode on a line starting "VIOLATIONS", counts lines starting "- [", and stops
    at "PASS". The first cut of check_kind_policy printed its FAILs BEFORE the header and without
    the colon form -- so the hook parsed TWO real violations as ZERO. A guard against silent
    omission, silently omitted. Green in isolation, useless when wired.
    """
    import io
    import contextlib
    sys.path.insert(0, os.path.join(ROOT, "scripts", "githooks"))
    import pre_commit  # noqa: E402

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = C.main([])
    text = buf.getvalue()

    counted = pre_commit._count_violations(text)
    real = text.count("\n  - [")
    assert counted == real, (
        f"the hook counts {counted} but the checker reported {real} -- a ratchet fed a wrong "
        f"count is not a ratchet, it is a rubber stamp with room to absorb violations silently")
    assert (rc == 1) == (real > 0), "exit code and reported violations must agree"


def test_live_tree_smoke_the_guard_runs_and_reports_real_numbers():
    """One pin against the real tree: the mechanism above is synthetic by design, but a guard
    that cannot read its own repository is theatre."""
    found = C.discover_kind_sets(ROOT)
    assert len(found) >= 12, f"expected the known *KINDS population, found {len(found)}"
    names = {n for _, n in found}
    assert {"ANSWER_KINDS", "WAKE_WORTHY_KINDS", "SKIP_KINDS"} <= names
