"""
Grant registry -- the reader over security/acl.json (source of truth), mirroring core/fleet/model_roster.py (renamed from roster.py at f8510b6; T123 duplicate-basename class).

The one function the doors call is `resolve(agent_id, verified=...)`: it returns the EFFECTIVE Grant an
agent acts under, fail-closed to QUARANTINED for anything unknown, unverified, or expired. Enforcement
(ToolBox/Bus) reads caps off the returned Grant; it never trusts a raw role string.

Storage is a git-tracked JSON file. A small in-process mtime cache avoids re-reading on every check; a
Redis cache layer is a later optimization (the file is always the fallback truth).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.trust.capabilities import Cap, ROLE_TEMPLATES, DEFAULT_ROLE, caps_from

ACL_PATH = Path(__file__).resolve().parent.parent.parent / "security" / "acl.json"

# Code-level bootstrap: the trusted CORE agents keep these roles even if security/acl.json is missing or
# corrupt. This is the availability guarantee -- DeepSeek's admin does NOT depend on the file surviving,
# on Claude being online, or on anyone re-granting it. A VALID acl.json is still the source of truth (the
# human can demote/change these there); this floor only applies when the file cannot be read at all.
BOOTSTRAP_ROLES = {
    "claude": "super_admin",
    "deepseek": "admin",
}


@dataclass
class Grant:
    """One agent's effective permissions. Source of truth is security/acl.json."""
    agent_id: str
    role: str
    caps: set = field(default_factory=set)          # set[Cap]
    path_scope: list = field(default_factory=list)  # glob prefixes for WRITE ([]=none, ["*"]=full)
    bus_send_kinds: Optional[set] = None            # None = all kinds; a set = allowlist
    granted_by: str = "root"
    granted_at: str = ""
    expires_at: Optional[str] = None                # ISO ts; None = permanent
    reason: str = ""
    request_ref: Optional[str] = None

    def has(self, c: Cap) -> bool:
        return c in self.caps

    def can_write(self, rel_path: str) -> bool:
        """True iff WRITE is held AND rel_path (posix, repo-relative) is inside the path scope."""
        if Cap.WRITE not in self.caps or not self.path_scope:
            return False
        if "*" in self.path_scope:
            return True
        import fnmatch
        return any(fnmatch.fnmatch(rel_path, s) for s in self.path_scope)

    def can_send_kind(self, kind: str) -> bool:
        if Cap.BUS_SEND not in self.caps:
            return False
        return self.bus_send_kinds is None or str(kind) in self.bus_send_kinds


def _template_grant(agent_id: str, role: str) -> Grant:
    t = ROLE_TEMPLATES.get(role, ROLE_TEMPLATES[DEFAULT_ROLE])
    return Grant(agent_id=agent_id, role=role, caps=set(t["caps"]),
                 path_scope=list(t["path_scope"]), bus_send_kinds=(set(t["bus_send_kinds"])
                 if t["bus_send_kinds"] is not None else None),
                 granted_by="template", reason=f"role template: {role}")


def role_template(role: str) -> Grant:
    """The factory-default Grant for a role label (unknown role -> quarantined)."""
    return _template_grant(f"<{role}>", role if role in ROLE_TEMPLATES else DEFAULT_ROLE)


_CACHE: dict = {"mtime": None, "grants": {}}


def _load():
    """Parse security/acl.json into {agent_id: Grant}. Returns None when the file is MISSING or CORRUPT
    (a total failure -> callers fall back to BOOTSTRAP_ROLES for core agents, quarantine for the rest).
    Returns a dict (possibly empty) when the file was read successfully. In-process mtime cache."""
    try:
        mtime = os.path.getmtime(ACL_PATH)
    except OSError:
        return None                                   # file missing -> signal total failure
    if _CACHE["mtime"] == mtime:
        return _CACHE["grants"]
    out: dict = {}
    try:
        doc = json.loads(ACL_PATH.read_text(encoding="utf-8"))
        for rec in doc.get("grants", []):
            aid = rec.get("agent_id")
            if not aid:
                continue
            bsk = rec.get("bus_send_kinds", None)
            out[aid] = Grant(
                agent_id=aid, role=rec.get("role", DEFAULT_ROLE),
                caps=caps_from(rec.get("caps", [])),
                path_scope=list(rec.get("path_scope", [])),
                bus_send_kinds=(set(bsk) if bsk is not None else None),
                granted_by=rec.get("granted_by", "root"), granted_at=rec.get("granted_at", ""),
                expires_at=rec.get("expires_at"), reason=rec.get("reason", ""),
                request_ref=rec.get("request_ref"))
    except Exception:
        return None                                   # malformed file -> signal total failure
    _CACHE["mtime"], _CACHE["grants"] = mtime, out
    return out


def _bootstrap_or_quarantine(agent_id: str) -> Grant:
    """Fallback when the ACL file can't be read: trusted core agents keep their bootstrap role; everyone
    else is quarantined (fail-closed). This is what keeps DeepSeek admin through a lost/corrupt file."""
    role = BOOTSTRAP_ROLES.get(agent_id, DEFAULT_ROLE)
    return _template_grant(agent_id, role)


def expiring_grants(within_h: float = 48.0, grants=None) -> list:
    """[{agent_id, expires_at, hours_left, expired}] -- time-boxed grants at or near their lapse.

    T151: expiry was a TRAPDOOR. resolve() correctly drops an expired grant to QUARANTINED, and
    nothing outside this module ever read expires_at -- no boot line, no doctor row, no warning.
    A time-boxed seat just stopped working mid-arc and the next reader debugged refused writes
    instead of the cause. security/acl.json says in three separate records "NOT time-boxed -- the
    07-05 whole-grant time-box silently quarantined the entire admin role at expiry", and that
    doctrine exists ONLY because the lapse was unobserved. Observed, a time-box is a deadline.

    PERMANENT GRANTS ARE NEVER REPORTED. Every long-lived seat carries expires_at=None by that same
    doctrine, so including them would make this notice pure noise -- and noise is how a warning
    gets silenced, which this repo's guards keep re-learning.

    Read-only and never raises: observability must not be able to gate trust. A malformed record
    degrades to silence, EXCEPT an unparseable expiry, which resolve() already treats as expired
    and which is therefore reported as expired here too -- the two must not disagree.
    """
    try:
        recs = grants if grants is not None else (_load() or [])
        # _load() returns a DICT keyed by agent_id, not a list. Iterating it yielded KEYS, every
        # .get() raised on a string, the per-record `except` swallowed it, and this returned []
        # silently -- passing every unit pin (which inject lists) while reporting nothing against
        # the real ACL. Only X5, the pin that reads the actual file, caught it.
        if isinstance(recs, dict):
            recs = list(recs.values())
    except Exception:
        return []
    def _field(rec, name):
        """Records arrive in TWO shapes and both are legitimate: raw dicts (the file, and pins that
        inject fixtures) and Grant dataclasses (what _load returns). Reading only one shape is how
        the first cut of this function silently reported nothing."""
        if isinstance(rec, dict):
            return rec.get(name)
        return getattr(rec, name, None)

    out = []
    now = datetime.now(timezone.utc)
    for rec in recs or []:
        try:
            raw = _field(rec, "expires_at")
            agent = _field(rec, "agent_id")
            if not raw or not agent:
                continue                      # permanent, or nothing to name
            try:
                exp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                hours_left = (exp - now).total_seconds() / 3600.0
            except Exception:
                out.append({"agent_id": agent, "expires_at": str(raw),
                            "hours_left": None, "expired": True})   # matches _expired's fail-closed
                continue
            if hours_left <= float(within_h):
                out.append({"agent_id": agent, "expires_at": str(raw),
                            "hours_left": round(hours_left, 1),
                            "expired": hours_left <= 0})
        except Exception:
            continue
    return sorted(out, key=lambda r: (not r["expired"], r["agent_id"]))


def _expired(expires_at: Optional[str]) -> bool:
    if not expires_at:
        return False
    try:
        exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= exp
    except Exception:
        return True                                   # unparseable expiry -> treat as expired (fail closed)


def grants() -> list:
    """All grant records from a readable ACL file, or [] when the file is missing/corrupt."""
    loaded = _load()
    return list(loaded.values()) if loaded else []


def get(agent_id: str) -> Optional[Grant]:
    """One agent's STORED grant from the file, or None if unregistered / file unreadable."""
    loaded = _load()
    return loaded.get(agent_id) if loaded else None


def may_run_runner(agent_id: str) -> bool:
    """RB-25 F1: may `agent_id` legitimately run a bus RUNNER? A runner's reply + trace
    lanes reach the bus as infrastructure, NOT through the ACL-gated send tool -- so a
    quarantined id running a runner still narrates and replies (found live in the newborn
    gauntlet: 3 reply + 47 trace broadcasts from a quarantined id landed on the bus while
    every conscious door refused). The threat-model-correct cut: a quarantined id gets no
    runner at all. A broken door (resolve() raising unexpectedly) mirrors resolve()'s
    OWN fallback -- the bootstrap floor: core fleet keeps availability, everyone else
    refuses, and the decision is LOUD on stderr (A2-1 per
    docs/library/report/20260712_rb-25-amendment-2-deepseek-rulings-fence_7f1c14.md: the reply/trace
    lanes are exactly the ones the conscious doors do NOT gate, so blanket fail-open
    reopened the F1 hole under error conditions)."""
    try:
        return resolve(agent_id).role != "quarantined"
    except Exception as e:
        import sys
        # What resolve() would have returned had it caught this itself (its corrupt-file
        # path already lapses here); never blanket-allow on the ungated infrastructure lane.
        grant = _bootstrap_or_quarantine(agent_id)
        allowed = grant.role != "quarantined"
        print(f"[trust] may_run_runner: resolve() threw {type(e).__name__} for '{agent_id}' "
              f"-- bootstrap floor {'allowed' if allowed else 'REFUSED'} (role={grant.role})",
              file=sys.stderr)
        return allowed


def resolve(agent_id: str, *, verified: bool = True) -> Grant:
    """The EFFECTIVE grant `agent_id` acts under -- the single door-check entry. Fail-closed:
      - unverified identity or empty id  -> quarantined (identity-first);
      - ACL file missing/corrupt         -> BOOTSTRAP_ROLES for core agents, quarantined for the rest
                                            (availability floor: DeepSeek stays admin through file loss);
      - agent absent from a VALID file   -> quarantined (a deliberate removal is honored);
      - grant present but expired         -> quarantined (temporary escalations lapse to the role floor)."""
    if not verified or not agent_id:
        return _template_grant(agent_id or "<unknown>", DEFAULT_ROLE)
    loaded = _load()
    if loaded is None:                                # file unreadable -> code-level bootstrap floor
        return _bootstrap_or_quarantine(agent_id)
    g = loaded.get(agent_id)
    if g is None or _expired(g.expires_at):
        return _template_grant(agent_id, DEFAULT_ROLE)
    return g
