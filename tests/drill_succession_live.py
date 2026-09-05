"""LIVE SUCCESSION DRILL -- the conductor gate has 18 pins and has never fired.

Daniil, 2026-08-24: "I don't want to ... be hard stuck if anthropics servers go down again."

House law: a recovery path without an executed drill and a dated receipt is presumed
broken. This fires the gate for real against the REAL ACL, the REAL grant door and the
REAL bus. Only the three DETECTION probes are injected -- that is the honest seam: it
proves the decision AND the authority path in the world without requiring the conductor
to actually die (killing my own session would also make me unable to write the receipt).

Cleanup is part of the drill: the mandate grant minted here is revoked at the end, and
the drill asserts the revocation landed. A drill that leaves authority behind is a breach,
not a receipt.
"""
import sys, time, json, io
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core.comm.conductor_gate as cg
from core.trust import registry

TARGET = "drill_seat_t384"          # throwaway; no real seat's authority moves
rows = []


def rung(name, fn):
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    rows.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}\n         {detail}")


# probes that force each condition
DEAD = lambda a=None, **k: "orphan: marker stale + parent chain dead (DRILL)"

def ALIVE_SUCC(a=None, **k):
    """PER-AGENT, and the first drill run got this wrong: att_fn is asked about the
    CONDUCTOR as well as the successors. A blanket 'ATTENDED' told the gate the conductor
    was present, so the two-factor correctly refused to activate on a half-satisfied
    condition. The conductor must read UNATTENDED for condition 1; the successors must
    read ATTENDED for condition 2."""
    return "UNATTENDED" if str(a) == cg.CONDUCTOR else "ATTENDED"

NO_OP = lambda **k: False


def d1_baseline():
    v = cg.evaluate_succession()
    return (not v.activate), f"real probes, conductor alive -> activate={v.activate}; {v.reason[:110]}"


def d2_activates_when_all_three_hold():
    v = cg.decide_and_act(reap_fn=DEAD, att_fn=ALIVE_SUCC, op_present_fn=NO_OP)
    return v.activate, (f"activate={v.activate} successor={v.successor!r} "
                        f"alive={getattr(v,'successors_alive',None)} :: {v.reason[:120]}")


def d3_acting_conductor_can_mint_a_timeboxed_grant():
    v = cg.evaluate_succession(reap_fn=DEAD, att_fn=ALIVE_SUCC, op_present_fn=NO_OP)
    rep = cg.acting_conduct_grant(successor=v.successor, agent_id=TARGET, role="member",
                                  reason="LIVE SUCCESSION DRILL 2026-08-24 -- revoked at drill end",
                                  hours=1.0, caps=["read"])
    g = registry.resolve(TARGET)
    ok = g.role == "member" and any("read" in str(c).lower() for c in g.caps)
    return ok, f"minted by {v.successor!r}: resolve({TARGET}) -> role={g.role} caps={sorted(str(c) for c in g.caps)}"


def d4_permanent_is_unexpressible():
    import inspect
    sig = inspect.signature(cg.acting_conduct_grant)
    has_perm = any("permanent" in p for p in sig.parameters)
    if has_perm:
        return False, "a 'permanent' parameter EXISTS -- the dangerous state is expressible"
    try:
        cg.acting_conduct_grant(successor="deepseek", agent_id=TARGET, role="member",
                                reason="drill", hours=None, caps=["read"])
        return False, "hours=None was ACCEPTED -- lapse is not mandatory"
    except Exception as e:
        return True, f"no 'permanent' param, and hours=None refused ({type(e).__name__})"


def d5_self_widening_refused():
    try:
        cg.acting_conduct_grant(successor="deepseek", agent_id="deepseek", role="admin",
                                reason="drill self-widen", hours=1.0, caps=["admin.grant"])
        return False, "SECURITY: the acting conductor widened ITS OWN grant"
    except Exception as e:
        return True, f"refused ({type(e).__name__}: {str(e)[:90]})"


def d6_admin_grant_refused():
    try:
        cg.acting_conduct_grant(successor="deepseek", agent_id=TARGET, role="member",
                                reason="drill escalate", hours=1.0, caps=["admin.grant"])
        return False, "SECURITY: admin.grant was mintable by the acting conductor"
    except Exception as e:
        return True, f"refused ({type(e).__name__}: {str(e)[:90]})"


def d7_stands_down_when_conductor_returns():
    v = cg.decide_and_act(reap_fn=lambda a=None, **k: "alive-or-unknown",
                          att_fn=ALIVE_SUCC, op_present_fn=NO_OP)
    return (not v.activate), f"conductor alive again -> activate={v.activate}; {v.reason[:110]}"


def d8_cleanup_revokes_the_drill_grant():
    from core.trust import grant_writer
    try:
        grant_writer.revoke(TARGET, by="claude",
                            reason="LIVE SUCCESSION DRILL 2026-08-24 complete -- drill authority removed")
    except TypeError:
        grant_writer.revoke(TARGET, by="claude")
    g = registry.resolve(TARGET)
    ok = g.role == "quarantined"
    return ok, f"post-revoke resolve({TARGET}) -> role={g.role} (must be quarantined)"


print("LIVE SUCCESSION DRILL -- real ACL, real grant door, injected detection only\n")
rung("D1  baseline: conductor alive -> no activation", d1_baseline)
rung("D2  all three conditions hold -> ACTIVATES", d2_activates_when_all_three_hold)
rung("D3  acting conductor mints a time-boxed grant FOR REAL", d3_acting_conductor_can_mint_a_timeboxed_grant)
rung("D4  a permanent grant is UNEXPRESSIBLE", d4_permanent_is_unexpressible)
rung("D5  self-widening refused", d5_self_widening_refused)
rung("D6  admin.grant refused", d6_admin_grant_refused)
rung("D7  stands down when the conductor returns", d7_stands_down_when_conductor_returns)
rung("D8  CLEANUP: drill grant revoked", d8_cleanup_revokes_the_drill_grant)

p = sum(1 for _, ok, _ in rows if ok)
print(f"\nRESULT: {p}/{len(rows)} rungs passed")
sys.exit(0 if p == len(rows) else 1)
