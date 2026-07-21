"""W07 pins — decision + blocker join the lane router, and a completeness guard.

Wish W07 (lane-router self-report): a fleet broadcast of Daniel's T094 RULING rode
legacy-only with a loud warning because kind='decision' was unmapped in KIND_LANE. Same
for 'blocker' (a wake-worthy kind). Both are directed/salient coordination -> the work
(wake) lane. The completeness pin makes the census self-checking: every wake-worthy kind
and every ACL-grantable send-kind must be routed, so a new kind can't silently ride
legacy-only again (the W38 register-at-ship-time spirit, applied to lane kinds).

  P1  decision routes to work (was None -> legacy-only + warning)
  P2  blocker routes to work (wake-worthy, must ride the wake lane)
  P3  COMPLETENESS: every wake_worthy kind maps to a lane
  P4  COMPLETENESS: every ACL bus_send_kind maps to a lane (no legacy-only salient mail)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import packet_spec as ps


def test_p1_decision_routes_work():
    assert ps.lane_for("decision") == "work"


def test_p2_blocker_routes_work():
    assert ps.lane_for("blocker") == "work"


def test_p3_every_wake_worthy_kind_is_routed():
    from scripts.bifrost_wake import WAKE_WORTHY_KINDS
    unmapped = sorted(k for k in WAKE_WORTHY_KINDS if ps.lane_for(k) is None)
    assert unmapped == [], f"wake-worthy kinds routing legacy-only (they'd miss the wake lane): {unmapped}"


def test_p4_every_acl_send_kind_is_routed():
    # the kinds any admin seat may send (security/acl.json bus_send_kinds union) must all
    # route -- a salient kind on nobody's lane is the T094-ruling bug.
    acl_kinds = {"chat", "note", "request", "question", "reply", "nudge", "steer",
                 "inform", "hint", "handoff", "completion", "decision", "blocker"}
    unmapped = sorted(k for k in acl_kinds if ps.lane_for(k) is None)
    assert unmapped == [], f"ACL-grantable kinds routing legacy-only: {unmapped}"
