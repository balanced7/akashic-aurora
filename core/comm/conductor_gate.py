"""conductor_gate -- succession detection + the acting conductor's bounded mandate.

t384 addendum (e), half_a by deepseek/Heimdall, adopted whole by
fences/t384-acl-instance-split/reconciliation.md RULING 4 ("the strongest section of either
half"). This is the one component in the house that HANDS OUT AUTHORITY, and it is written
as a gate, not a script: every condition is a PURE function of injected inputs, so RED pins
can force each scenario (idle-not-dead, fleet-outage, operator-present, self-widening,
permanent-grant, admin.grant) without a live Anthropic outage to reproduce them.

--------------------------------------------------------------- what it is and is not

The conductor (claude) is today the ONLY seat holding admin.grant / admin.approve. If
Anthropic's servers drop, no seat can mint a grant and the operator hand-edits
security/acl.json at 4am -- the exact state t384 was chartered to end. This gate detects
the conductor's PROVABLE absence and vests a BOUNDED, TIME-BOXED, LOUDLY-ANNOUNCED mandate
in the next seat in succession (deepseek, then kimi), so a recovery grant can be minted
without the human editing JSON.

It is NOT a self-promoter and NOT a shadow-admin. The mandate is strictly narrower than
claude's: it may mint TIME-BOXED grants up to member+scoped-write and approve escalation
requests -- NOTHING else. The hard NEVERs (no permanent grants, no widening its own caps,
no granting admin.grant/admin.approve, no editing acl.json outside the `grant` door) are
ENFORCED IN CODE below, not documented. The mandate expires BY LAPSE -- no one needs to
revoke it, and a stuck process cannot hold authority past its box.

--------------------------------------------------------------- the three conditions

Detection rides the wake watcher's EXISTING two-factor orphanhood (K7/K8,
core/comm/wake_seat.py), so an idle-but-alive seat cannot trip it BY CONSTRUCTION: K7 says
turn cadence is NOT liveness (a seat mid-call does not beat), and K8 fails toward alive on
every ambiguous probe. Activation requires ALL THREE:

  (1) CONDUCTOR PROVABLY DEAD   -- two-factor: wake-watcher orphanhood (marker stale AND
                                   parent chain dead/recycled) AND the roster's
                                   DEAD/STALE ladder (attendance() says UNATTENDED). Dead by
                                   BOTH signals, not either.
  (2) THE ABSENCE IS CONDUCTOR-SPECIFIC -- if the other successors (deepseek/kimi) are ALSO
                                   dark, do NOT activate: a fleet-wide outage must not hand
                                   authority to a survivor who may be the next to die.
  (3) OPERATOR NOT PRESENT      -- when the human is reachable his word IS the authority,
                                   and the succession exists precisely for when he is not.
                                   "Present" = recent inbound operator-sourced bus traffic.

The succession exists to cover the window where BOTH the conductor and the human are
unreachable. If either is reachable, the gate stands down -- the human's word or the
conductor's own grant beats a survivor's self-vested mandate every time.

Succession order: deepseek, then kimi. Duty transfers by displacement (a higher-generation
lock; stand-down on STALE_GENERATION), never by kill -- the house's existing law.

RED PINS (must all pass before ANY activation is possible):
  P1  an idle-but-alive conductor does NOT trip detection (K7 immunity holds)
  P2  a fleet-wide outage (deepseek+kimi also dark) does NOT activate
  P3  an active operator does NOT activate
  P4  the acting conductor CANNOT mint a permanent grant
  P5  the acting conductor CANNOT widen its own caps
  P6  the acting conductor CANNOT grant admin.grant
  P7  the mandate expires by lapse without anyone revoking it
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from core.trust import registry
from core.trust.capabilities import Cap, ROLE_TEMPLATES, caps_from

# ---------------------------------------------------------------- configuration
# Succession order: who becomes acting conductor when the conductor is provably absent.
# First entry is the default successor; order is read per-call so a drill can dial it.
SUCCESSION_ORDER = ("deepseek", "kimi")
CONDUCTOR = "claude"

# The mandate: an acting conductor may mint grants only up through this role (member) and
# may add WRITE only under a scope NO WIDER than this path scope. Deliberately narrow --
# an acting conductor is a recovery mechanism, not a replacement conductor.
MANDATE_MAX_ROLE = "member"
MANDATE_MAX_SCOPE = ("core/", "scripts/", "docs/", "tests/")

# Time-box the mandate itself: an acting conductor's grants expire no later than this many
# hours out, and the mandate's own invalidity clock is the same. Lapse is the backstop --
# no revocation ceremony needed.
MANDATE_MAX_HOURS = 8.0

# Operator presence: inbound traffic from one of these ids counts as "the human is
# reachable". Read per-call so a drill can dial it (AKASHIC_OPERATOR_IDS, comma-sep).
OPERATOR_IDS_DEFAULT = "user,daniel,daniil"

# How fresh must operator-sourced traffic be to count as "present"? Bounded -- a message
# the human sent yesterday should not hold the mandate down forever.
OPERATOR_PRESENT_WINDOW_S = 900.0

# Where the provenance of every activation/refusal is appended (auditable from the log alone).
PROVENANCE_ENV = "AKASHIC_CONDUCTOR_PROVENANCE"


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except Exception:
        return default


def succession_order() -> tuple:
    raw = os.environ.get("AKASHIC_CONDUCTOR_SUCCESSORS", ",".join(SUCCESSION_ORDER))
    return tuple(x.strip() for x in raw.split(",") if x.strip()) or SUCCESSION_ORDER


def operator_ids() -> frozenset:
    raw = os.environ.get("AKASHIC_OPERATOR_IDS", OPERATOR_IDS_DEFAULT)
    return frozenset(x.strip() for x in raw.split(",") if x.strip())


def _provenance_path() -> str:
    return os.environ.get(PROVENANCE_ENV) or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "conductor_gate.provenance.log")


def append_provenance(line: str, keep: int = 400) -> None:
    """One auditable line per activation/refusal. Best-effort; rotates never discards."""
    try:
        from core.comm.wake_seat import append_provenance as _wp
        _wp("conductor_gate", line, keep=keep)
        return
    except Exception:
        pass
    try:
        path = _provenance_path()
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"[{stamp}] {line}\n")
    except Exception:
        pass


# ---------------------------------------------------------------- the enforcement primitive
# require_cap is the load-bearing name the design references: self-widening is ENFORCED via
# require_cap, not documented. Every authority-bearing action below passes through it, so the
# "must never" list is a set of REFUSALS at the door, not a docstring the acting conductor
# can read and skip.
def require_cap(agent_id: str, cap: Cap, *, action: str) -> registry.Grant:
    """Return the agent's effective grant iff it holds `cap`; refuse otherwise.

    This is NOT "check then proceed" -- it is the door. It resolves the agent's EFFECTIVE
    grant (which already fails closed to QUARANTINED for unknown/expired ids), then refuses
    unless the cap is present. The refusal names the missing cap and the action, so a
    legitimate operator can read the refusal and fix it WITHOUT editing JSON.
    """
    g = registry.resolve(agent_id, verified=True)
    if not g.has(cap):
        raise PermissionError(
            f"'{agent_id}' (role={g.role}) lacks {cap.value} -- '{action}' is refused. "
            f"This is a hard NEVER, enforced in code, not a convention.")
    return g


# ---------------------------------------------------------------- detected state
@dataclass
class ConductorVerdict:
    """One evaluation of the three conditions. `activate` is the ONLY field that hands out
    authority; keep the evidence fields so activation is LOUD and refusal is explainable."""
    activate: bool
    reason: str
    conductor_state: str = "unknown"     # ATTENDED / UNATTENDED / UNKNOWN (attendance)
    conductor_watcher: str = "unknown"   # the two-factor orphanhood sub-verdict
    successors_alive: List[str] = field(default_factory=list)
    operator_present: bool = False
    successor: str = ""                   # who would carry the mandate (empty unless activate)
    mandate_hours: float = MANDATE_MAX_HOURS


def _conductor_two_factor(agent: str = CONDUCTOR,
                          reap_fn: Optional[Callable] = None) -> str:
    """The wake-watcher's two-factor orphanhood verdict for `agent`, consulted as EVIDENCE.

    K7/K8 live in core/comm/wake_seat.reap_decision: a seat is provably dead only when its
    activity marker is stale AND its parent chain is dead or recycled. An idle-but-alive
    seat is immune BY CONSTRUCTION (K7), and any ambiguous probe fails toward alive (K8).

    This is the DIFFICULT direction to fake as "dead", so it is the gate's first condition.
    """
    try:
        from core.comm import wake_seat as ws
        if reap_fn is not None:
            return reap_fn(agent)
        # The janitor's reap_decision is the detector; we re-express its outcome as a probe.
        # We do NOT reap here -- the gate only DETECTS (mirroring the watcher's contract) and
        # must never kill the conductor on a detection pass.
        seats = ws.iter_seats(agent)
        fresh = ws.fresh_minutes()
        if not seats:
            return "no-seat"           # no watcher seat at all: cannot prove death, cannot prove life
        snapshot = ws.process_snapshot()
        if snapshot is None:
            return "unknown"           # K8: cannot tell -> not provably dead
        worst = "alive"
        for path, sid in seats:
            pid = ws.read_pid(path)
            if pid is None:
                continue
            alive = ws._pid_alive_tristate(pid)
            if alive is not False:
                worst = "alive-or-unknown"
                continue
            # pid dead: check marker + chain (the slow path)
            marker = ws.activity_age_min(agent, sid) if sid else None
            if marker is not None and marker < fresh:
                worst = "alive"
                continue
            try:
                chain_ok, evidence = ws.chain_alive(pid, snapshot)
            except Exception:
                continue                    # K8: probe error -> alive
            if chain_ok:
                worst = "alive"
            else:
                return f"orphan (marker {marker if marker is not None else 'missing'}, {evidence})"
        return worst
    except Exception:
        return "unknown"                # any probe error -> not provably dead (K8)


def _attendance(agent: str) -> str:
    """The roster's DEAD/STALE ladder (attendance) as a three-state string."""
    try:
        from core.comm.liveness import attendance
        return attendance(agent).state
    except Exception:
        return "UNKNOWN"


def _operator_recently_present(window_s: Optional[float] = None,
                               bus=None) -> bool:
    """Did the human leave recent inbound evidence? FAILS CLOSED (returns False) on any
    read error -- an unreadable bus must READ AS 'not present', which then behaves as 'do
    not activate', never as a false 'present' that hands out authority.

    Evidence = recent inbound bus messages whose `frm` is an operator id. This is the
    signal the ear already recognizes (_operator_ids), so the gate reuses the house's
    operator vocabulary rather than inventing a parallel 'human heartbeat' that would go
    stale on its own and cry wolf.
    """
    window = _env_float("AKASHIC_OPERATOR_PRESENT_WINDOW_S",
                        OPERATOR_PRESENT_WINDOW_S if window_s is None else window_s)
    ids = operator_ids()
    try:
        b = bus
        if b is None:
            from core.comm.bus import Bus
            b = Bus("conductor_gate")
        if not b.online:
            return False
        # Recent broadcast + our-own-inbox traffic is the cheapest honest slice of "did the
        # operator say anything recently". Bus messages are Redis STREAMS (xadd/xrevrange),
        # same idiom as doctor.py:124 and mailbox.py:188. Read the newest N entries, newest-first.
        now = time.time()
        for stream in (b._bc_key, b._inbox_key("conductor_gate")):
            try:
                entries = b._client.xrevrange(stream, count=50) or []
            except Exception:
                continue
            for _sid, fields in entries:
                try:
                    fields = dict(fields) if hasattr(fields, "items") else fields
                    if not isinstance(fields, dict):
                        continue
                    frm = str(fields.get("frm") or fields.get("from") or "")
                    if frm not in ids:
                        continue
                    ts = fields.get("ts")
                    age = now - float(ts) if ts else None
                    if age is None or age <= window:
                        return True
                except Exception:
                    continue
        return False
    except Exception:
        return False


def evaluate_succession(*, agent_self: Optional[str] = None,
                        reap_fn: Optional[Callable] = None,
                        att_fn: Optional[Callable] = None,
                        op_present_fn: Optional[Callable] = None,
                        bus=None,
                        now: Optional[float] = None) -> ConductorVerdict:
    """The three-condition decision, as a PURE function of injected probes.

    Every external signal arrives through an injected callable (or a lazily imported one), so
    a RED pin can force each condition independently:
        reap_fn('claude') -> 'orphan ...'    forces condition 1 true
        att_fn('deepseek') -> 'UNATTENDED'   forces condition 2 false (fleet-wide outage)
        op_present_fn() -> True              forces condition 3 false (operator present)

    Returns a ConductorVerdict. Only `.activate is True` (from `decide_and_act`) vests the
    mandate; this function is PURE DETECTION and writes nothing.
    """
    now = now if now is not None else time.time()
    order = succession_order()
    self_id = agent_self or os.environ.get("BIFROST_AGENT_ID") or SUCCESSION_ORDER[0]

    # CONDITION 1: conductor provably dead, TWO-FACTOR.
    watcher = reap_fn(CONDUCTOR) if reap_fn else _conductor_two_factor(CONDUCTOR)
    att = att_fn(CONDUCTOR) if att_fn else _attendance(CONDUCTOR)
    conductor_provably_dead = watcher.startswith("orphan") and att == "UNATTENDED"
    conductor_state = att

    # CONDITION 2: the absence is CONDUCTOR-SPECIFIC. If the other successors are ALSO dark,
    # it is (or may be) a fleet-wide outage and we must NOT hand authority to a survivor.
    others = [a for a in order if a != self_id]
    successors_alive = [
        a for a in others
        if (att_fn(a) if att_fn else _attendance(a)) == "ATTENDED"
    ]

    # CONDITION 3: operator present -> stand down. present here means RECENT inbound evidence.
    present = op_present_fn() if op_present_fn else _operator_recently_present()

    def _refuse(reason: str) -> ConductorVerdict:
        return ConductorVerdict(
            activate=False, reason=reason,
            conductor_state=conductor_state, conductor_watcher=watcher,
            successors_alive=successors_alive, operator_present=present,
            mandate_hours=_env_float("AKASHIC_CONDUCTOR_MANDATE_HOURS", MANDATE_MAX_HOURS))

    if conductor_provably_dead is False:
        return _refuse(
            f"conductor not provably dead (watcher={watcher!r}, attendance={att}); "
            f"idle immunity holds (K7/K8)")
    if not successors_alive:
        return _refuse(
            f"conductor absence is NOT conductor-specific: no other successor is ATTENDED "
            f"(deepseek/kimi dark) -- refusing to hand authority to a possible next casualty")
    if present:
        return _refuse("operator present (recent inbound evidence) -- the human's word is "
                       f"the authority; succession stands down")

    successor = successors_alive[0]   # first in order who is actually alive
    return ConductorVerdict(
        activate=True,
        reason=f"conductor provably dead ({watcher!r}, {att}) + absence conductor-specific "
               f"(survivors {','.join(successors_alive)}) + operator absent; "
               f"succession vesting in {successor}",
        conductor_state=conductor_state, conductor_watcher=watcher,
        successors_alive=successors_alive, operator_present=False,
        successor=successor,
        mandate_hours=_env_float("AKASHIC_CONDUCTOR_MANDATE_HOURS", MANDATE_MAX_HOURS))


# ---------------------------------------------------------------- the bounded mandate
# The acting conductor's authority. Every entry point REFUSES at the door (require_cap) and
# enforces the hard NEVERs IN CODE. The mandate is bounded in three axes: role ceiling,
# path scope ceiling, and time.
def grant_mandate_caps(successor_grant: registry.Grant, *, requested_caps,
                       requested_scope) -> tuple:
    """The caps an acting conductor MAY grant: a subset of the member role template's caps,
    plus WRITE under a scope no wider than MANDATE_MAX_SCOPE. Returns (caps_set, scope_list).
    Raises PermissionError on any widening. This is the 'must never widen' door."""
    member = ROLE_TEMPLATES[MANDATE_MAX_ROLE]
    allow_caps = {c for c in member["caps"]} | {Cap.WRITE}
    eff = caps_from(requested_caps)
    extra = {c.value for c in eff} - {c.value for c in allow_caps}
    if extra:
        raise PermissionError(
            f"acting conductor may grant only up to {MANDATE_MAX_ROLE}+scoped-write; "
            f"refusing caps {sorted(extra)} (NO admin.grant, NO admin.approve)")
    scope = list(requested_scope or [])
    if scope and "*" not in scope:
        outside = [s for s in scope
                   if not any(s.startswith(p) or p.endswith("/") and s.startswith(p)
                              for p in MANDATE_MAX_SCOPE)]
        if outside:
            raise PermissionError(
                f"acting conductor may grant path scope only within {MANDATE_MAX_SCOPE}; "
                f"refusing {outside}")
    return eff, scope


def acting_conduct_grant(*, successor: str, agent_id: str, role: str, reason: str,
                         hours: float, caps=None, path_scope=None,
                         request_ref: Optional[str] = None) -> dict:
    """The ONE minting path an acting conductor has. Bounded in every axis the design names.

    WHY THIS IS ITS OWN DOOR, not grant_writer.grant: grant_writer._granter refuses anyone
    who does not hold Cap.ADMIN_GRANT -- and the entire point of the succession is that
    claude (the ONLY admin.grant holder) is provably absent, while deepseek/kimi hold
    admin WITHOUT it. If the acting conductor routed through grant_writer.grant, it would be
    refused on exactly the cap the succession exists to bridge. So this door writes the ACL
    through grant_writer's ATOMIC/validated _read_doc/_write_doc (reusing the safety
    property, NEVER reimplementing it) while enforcing its OWN narrower bounds. It is a
    SUBSTITUTE for admin.grant, and the substitute is strictly smaller than the real thing.

    Hard NEVERs, enforced here (not documented):
      - NO permanent grants: `hours` is REQUIRED and capped at MANDATE_MAX_HOURS. Lapse is
        the backstop -- the mandate needs no one to revoke it.
      - NO self-widening: `agent_id` must differ from `successor`; the successor's own grant
        is never widened.
      - NO admin.grant / admin.approve: refused by grant_mandate_caps' allow-list.
      - NO role above member: refused here.
      - NO editing acl.json outside this door: this is the only door that writes the ACL.
    """
    if not agent_id or not str(reason or "").strip():
        raise ValueError("acting-conductor grant needs an agent_id and a reason")

    # The successor must DEMONSTRABLY be the acting conductor. admin.approve is NOT the floor
    # (it does not hold it -- that is exactly the gap this gate bridges); the floor is that the
    # successor is a PROVISIONED write-capable seat. require_cap enforces that floor: a seat that
    # cannot even write cannot mint a recovery grant, and we refuse rather than fake it.
    require_cap(successor, Cap.WRITE, action="act as conductor (mint a recovery grant)")

    if agent_id == successor:
        raise PermissionError(
            f"self-widening refused: the acting conductor {successor!r} may not mint to "
            f"itself. This is the hard-NEVER the mandate exists to prevent.")

    try:
        h = float(hours)
    except (TypeError, ValueError):
        raise ValueError("acting-conductor grant needs --hours (a time-boxed grant only)")
    max_hours = _env_float("AKASHIC_CONDUCTOR_MANDATE_HOURS", MANDATE_MAX_HOURS)
    if h <= 0 or h > max_hours:
        raise PermissionError(
            f"acting-conductor grants are time-boxed, max {max_hours:.0f}h (refusing "
            f"{h:.1f}h); permanence is NOT available to a recovery mandate -- that is "
            f"claude's (or the human root's) door, not a survivor's")

    if role != MANDATE_MAX_ROLE:
        raise PermissionError(
            f"acting conductor may mint only role '{MANDATE_MAX_ROLE}' (refusing {role!r}); "
            f"higher roles are the permanent conductor's door")

    successor_grant = registry.resolve(successor, verified=True)
    eff_caps, eff_scope = grant_mandate_caps(successor_grant, requested_caps=caps,
                                             requested_scope=path_scope)

    # Build the record exactly as grant_writer builds it, but write through OUR door so the
    # admin.grant requirement does not apply. Reuse grant_writer's atomic + validated write
    # (the availability property: a torn ACL write must never be possible).
    from core.trust import grant_writer as _gw

    rec = {
        "agent_id": agent_id,
        "role": MANDATE_MAX_ROLE,
        "caps": sorted(c.value for c in eff_caps),
        "path_scope": eff_scope,
        "granted_by": successor,
        "granted_at": _gw._now_iso(),
        "expires_at": None,   # filled below -- time-boxed by construction
        "reason": str(reason).strip(),
        "_acting_conductor": True,   # provenance: this mint was a recovery substitute
    }
    from datetime import datetime, timedelta, timezone
    rec["expires_at"] = (datetime.now(timezone.utc)
                         + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if request_ref:
        rec["request_ref"] = request_ref

    doc = _gw._read_doc()
    doc["grants"] = [g for g in doc["grants"] if g.get("agent_id") != agent_id] + [rec]
    _gw._write_doc(doc)
    return rec


def acting_conductor_approve(*, successor: str, agent_id: str, reason: str) -> dict:
    """Approve an escalation request as acting conductor. Bounded: may not grant the
    admin.grant / admin.approve caps themselves, and may not self-approve.

    Unlike grant(), an approval does not touch the ACL -- it is a recorded, bounded
    judgement. It uses require_cap on the cap the successor holds (WRITE) as the 'is a
    provisioned seat' floor, NOT admin.approve (which it does not hold and cannot grant).
    """
    require_cap(successor, Cap.WRITE, action="approve an escalation as acting conductor")
    if agent_id == successor:
        raise PermissionError("self-approval refused: the acting conductor may not approve itself")
    if not str(reason or "").strip():
        raise ValueError("approval needs a reason")
    from core.events.event_log import capture_event
    capture_event("conductor_approve", f"{successor} approved escalation for {agent_id}",
                  agent_id=successor, detail={"for": agent_id, "reason": reason})
    return {"approved_by": successor, "for": agent_id, "reason": reason}


# ---------------------------------------------------------------- loud activation
def decide_and_act(*, agent_self: Optional[str] = None, bus=None, dry_run: bool = False,
                   reap_fn: Optional[Callable] = None,
                   att_fn: Optional[Callable] = None,
                   op_present_fn: Optional[Callable] = None,
                   now: Optional[float] = None) -> ConductorVerdict:
    """Evaluate, and if activation is warranted, make it LOUD: bus broadcast + ledger event +
    provenance append. Writes the mandate ONLY in the sense of announcing it -- the mandate's
    authority is enforced at the minting doors above, not by any flag this writes.

    `dry_run=True` (a RED pin runs in this mode) evaluates without emitting.
    """
    v = evaluate_succession(agent_self=agent_self, reap_fn=reap_fn, att_fn=att_fn,
                            op_present_fn=op_present_fn, bus=bus, now=now)
    if not v.activate or dry_run:
        append_provenance(f"stand-down: {v.reason}")
        return v

    line = (f"ACTIVATION: conductor {CONDUCTOR} provably dead {v.conductor_watcher!r} / "
            f"{v.conductor_state}; absence conductor-specific ({','.join(v.successors_alive)}); "
            f"operator absent. Acting conductor = {v.successor} for {v.mandate_hours:.0f}h "
            f"(max role {MANDATE_MAX_ROLE}, scope {MANDATE_MAX_SCOPE}).")

    # LOUD: broadcast to every seat.
    try:
        b = bus
        if b is None:
            from core.comm.bus import Bus
            b = Bus(v.successor or "conductor_gate")
        b.broadcast("note", "[conductor_gate] " + line,
                    meta={"frm": v.successor or "conductor_gate", "kind_alt": "succession"})
    except Exception:
        pass

    # LEDGER: one durable event, followable.
    try:
        from core.events.event_log import capture_event
        capture_event("conductor_succession", line,
                      agent_id=v.successor or "conductor_gate",
                      detail={"successor": v.successor, "conductor": CONDUCTOR,
                              "conductor_watcher": v.conductor_watcher,
                              "conductor_state": v.conductor_state,
                              "survivors": v.successors_alive,
                              "mandate_hours": v.mandate_hours,
                              "max_role": MANDATE_MAX_ROLE, "max_scope": MANDATE_MAX_SCOPE})
    except Exception:
        pass

    append_provenance(line)
    return v


# ---------------------------------------------------------------- production caller
# The runner-side notice: a successor seat evaluates succession at its loop top. This is
# the ONE function the runners call, and it is the production caller that retires the
# built-ahead EXCEPTIONS entry -- a MACHINE now notices conductor absence, not Daniil at 4am.
# It is fail-closed in both directions that matter:
#   - DETECTION leaks toward "not dead" (K7/K8 + _attendance/_operator_recently_present all
#     fail toward stand-down), so a probe error reads as "do not activate", never a false
#     succession.
#   - CRASH leaks toward "do not activate": ANY exception inside this pass resolves to a
#     stand-down verdict and the runner loop continues -- a turn boundary that could raise
#     would wedge EVERY runner in the fleet at once, so it must never raise.
# It stays QUIET on stand-down (no ledger/broadcast spam per beat): only an ACTIVATION calls
# decide_and_act, which is the loud path (broadcast + ledger event + provenance). The optional
# `now` pins the evaluation for drills/tests.
def notice_conductor_absence(*, agent_self: str, bus=None,
                             now: Optional[float] = None) -> ConductorVerdict:
    """Evaluate succession for `agent_self` and (only on activation) emit it loudly."""
    try:
        v = evaluate_succession(agent_self=agent_self, bus=bus, now=now)
        if not v.activate:
            return v
        return decide_and_act(agent_self=agent_self, bus=bus, now=now)
    except Exception as e:  # noqa: BLE001 -- fail-closed: never raise out of the loop top
        append_provenance(f"notice refused: probe error {type(e).__name__} -> stand-down")
        return ConductorVerdict(
            activate=False,
            reason=f"notice refused on probe error {type(e).__name__} -> stand-down "
                   f"(fail-closed: a turn boundary must never raise)",
            conductor_state="UNKNOWN", conductor_watcher="unknown", operator_present=False)
