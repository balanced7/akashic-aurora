"""PRE-REGISTERED ACCEPTANCE (T151) -- a time-box must be a deadline, not a trapdoor.

SEASON 0. `core/trust/registry.py:184` drops an expired grant to QUARANTINED, correctly and
fail-closed. Nothing outside core/trust ever reads `expires_at` -- no boot line, no doctor row, no
warning anywhere. So a time-boxed seat simply stops working mid-arc, and whoever picks it up
debugs the symptom (refused writes, silent no-ops) instead of reading the cause.

This is a DOCUMENTED failure being re-run. security/acl.json says, in three separate records:

    "NOT time-boxed -- the 07-05 whole-grant time-box silently quarantined the entire admin role
     at expiry; revoke by editing this record, never by expiry."

LIVE INSTANCE, which is why this is Season 0 and not backlog: codex_root was granted at
2026-08-04T00:45Z with expires_at 2026-08-05T12:00:00Z. Nothing will announce the lapse.

TO BE FAIR TO THE GRANTING SEAT: time-boxing a NEW, unproven identity is prudent, and the same
record withheld core/trust/* write for a well-argued reason ("core/trust/ is the enforcement code
... so write there is functionally admin.grant"). The time-box is not the defect. Doing it SILENTLY
is the defect -- and the doctrine only says "never expire" BECAUSE expiry is unobserved. Make it
observed and the doctrine's own reason dissolves.

  X1  a grant expiring inside the window is reported, with its agent and deadline
  X2  an ALREADY-expired grant is reported and marked expired (worse than expiring, not equal)
  X3  a permanent grant (expires_at None) is never reported     -- no crying wolf at the fleet
  X4  the reporter is read-only and never raises                -- observability must not gate trust
  X5  the real ACL parses, and codex_root's live time-box is visible today

Run: py -m pytest tests/test_t151_grant_expiry_is_visible.py -q
"""
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.trust import registry as REG  # noqa: E402


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _recs(**over):
    now = datetime.now(timezone.utc)
    base = [
        {"agent_id": "perm", "role": "member", "caps": ["read"],
         "expires_at": None},
        {"agent_id": "soon", "role": "member", "caps": ["read", "write"],
         "expires_at": _iso(now + timedelta(hours=6))},
        {"agent_id": "gone", "role": "member", "caps": ["read", "write"],
         "expires_at": _iso(now - timedelta(hours=2))},
    ]
    base.append(over) if over else None
    return base


def test_x1_a_grant_expiring_inside_the_window_is_reported():
    rows = REG.expiring_grants(within_h=24, grants=_recs())
    ids = {r["agent_id"] for r in rows}
    assert "soon" in ids, "a grant lapsing in 6 hours is invisible to the fleet"
    row = [r for r in rows if r["agent_id"] == "soon"][0]
    assert row["expires_at"], "the report must name the deadline, not just the fact"
    assert row["expired"] is False


def test_x2_an_already_expired_grant_is_reported_as_expired():
    rows = REG.expiring_grants(within_h=24, grants=_recs())
    gone = [r for r in rows if r["agent_id"] == "gone"]
    assert gone, "an ALREADY-quarantined seat is the loudest case and must not be omitted"
    assert gone[0]["expired"] is True


def test_x3_a_permanent_grant_is_never_reported():
    """Every long-lived seat carries expires_at=None by doctrine. If those rendered, the notice
    would be pure noise and would be silenced -- the failure this repo's guards keep recording."""
    rows = REG.expiring_grants(within_h=24, grants=_recs())
    assert "perm" not in {r["agent_id"] for r in rows}


def test_x4_the_reporter_is_read_only_and_never_raises():
    """Observability must never be able to gate trust. Malformed input degrades to silence."""
    assert REG.expiring_grants(within_h=24, grants=[{"agent_id": "x", "expires_at": "not-a-date"}]) \
        is not None
    assert REG.expiring_grants(within_h=24, grants=None) == []
    assert REG.expiring_grants(within_h=24, grants=[{}]) == []


def test_x5_the_live_acl_shows_the_codex_root_time_box():
    """Against the REAL file: the one live time-box today must be visible, and permanent grants
    must not be. If codex_root's grant is later made permanent or revoked, this asserts only that
    the reporter runs clean over the real ACL."""
    rows = REG.expiring_grants(within_h=24 * 400)
    ids = {r["agent_id"] for r in rows}
    import json
    recs = json.load(open(os.path.join(ROOT, "security", "acl.json"), encoding="utf-8"))["grants"]
    boxed = {g["agent_id"] for g in recs if g.get("expires_at")}
    assert ids == boxed, f"reporter disagrees with the file: reported {ids}, time-boxed {boxed}"
