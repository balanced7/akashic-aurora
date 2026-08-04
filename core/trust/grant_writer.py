"""core.trust.grant_writer -- the WRITE side of security/acl.json (T163, S-3 of the security schema).

WHAT THIS IS, AND WHAT IT IS NOT. Stated first because a silent overclaim about a security
component is worse than the missing component was.

`by` is a plain string. Anyone who can call this can pass by="claude", and anyone who can call
this can already open security/acl.json in an editor. So this module is NOT a new security
boundary and must never be described as one in a doc, a commit, or a boot line. It is a SAFER
PATH to a file that was always writable:

    hand-edited          ->  atomic and schema-validated
    audited by discipline->  audited by construction (no record without granted_by/at/reason)
    permanent by default ->  time-boxed by default, permanent behind an explicit flag
    edit-to-undo         ->  revocable through the same door

It lowers the chance of a MISTAKE. It does not lower the chance of an ATTACK by someone who
already has shell access. The guards below are CONSISTENCY guards, and their worth is that a
tired operator cannot widen the fleet's authority at 2am by fumbling a JSON edit -- which is
exactly how codex_root's grant was made, because until now there was no other way.

THE HIGHEST-SEVERITY PROPERTY HERE IS NOT PERMISSIONS, IT IS AVAILABILITY. registry.py falls
back to BOOTSTRAP_ROLES when the ACL cannot be READ. So a torn write does not fail closed: it
silently replaces the fleet's considered authority with a hardcoded floor. Every write is
therefore validated in memory, written to a temp file in the same directory, and swapped with
os.replace -- and the original is restored if anything raises. "Corrupt the file" must never be
an available primitive, for an attacker OR for a full disk.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

from core.trust import registry
from core.trust.capabilities import Cap, ROLE_TEMPLATES, DEFAULT_ROLE, caps_from

#: A time box longer than this is almost certainly a typo for something shorter. It is not a
#: security limit -- --permanent exists one line away -- it is a guard against `--hours 24000`.
MAX_HOURS = 24 * 365


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_doc() -> dict:
    path = registry.acl_path()
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc.get("grants"), list):
        raise ValueError(f"{path} has no grants[] array -- refusing to write a file "
                         f"whose shape is not the one this module understands")
    return doc


def _write_doc(doc: dict) -> None:
    """Validate, then swap. Never leaves a partial file where the ACL used to be.

    The validation is deliberately a full re-parse of the SERIALISED bytes rather than a check of
    the in-memory dict: the thing the fleet will read is the bytes, and a dict that serialises to
    something unparseable is exactly the failure this guards.
    """
    path = registry.acl_path()
    payload = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    json.loads(payload)                       # parse what we are about to write, not what we meant

    d = os.path.dirname(str(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".acl-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())              # the swap is only atomic if the bytes are durable
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)                    # a failed write leaves NOTHING behind, not even litter
        except OSError:
            pass
        raise
    registry._CACHE["mtime"] = None           # the in-process cache must not serve the old answer


def _granter(by: str):
    """The granter's EFFECTIVE grant, resolved -- never a role string handed in by the caller."""
    if not by:
        raise PermissionError("a grant needs a granter (--by); an unattributed grant is not auditable")
    g = registry.resolve(by, verified=True)
    if not g.has(Cap.ADMIN_GRANT):
        raise PermissionError(
            f"'{by}' resolves to role '{g.role}', which does not hold {Cap.ADMIN_GRANT.value}. "
            f"Only a super-admin mints grants. (This door refuses; it does not authenticate -- "
            f"see the module docstring.)")
    return g


def _bounded_by_granter(granter, caps: set, path_scope: list) -> None:
    """No granting what you do not hold. Caps AND scope, because scope is a capability too."""
    extra = {c.value for c in caps} - {c.value for c in granter.caps}
    if extra:
        raise PermissionError(
            f"'{granter.agent_id}' cannot grant capabilities it does not hold: {sorted(extra)}")
    if path_scope and "*" not in granter.path_scope:
        outside = [s for s in path_scope if s not in granter.path_scope]
        if outside:
            raise PermissionError(
                f"'{granter.agent_id}' cannot grant a path scope wider than its own: {outside}")


def grant(agent_id: str, role: str, by: str, reason: str,
          hours: float = None, permanent: bool = False,
          caps=None, path_scope=None, request_ref: str = None) -> dict:
    """Write one grant. Returns the record written. Raises rather than half-writing.

    Time-boxed by default: pass `hours`, or say `permanent=True` out loud. 10 of the 11 grants
    that existed when this was built are permanent, so permanence has to stay expressible -- but
    it should be a decision, never the consequence of forgetting an argument.
    """
    if not agent_id:
        raise ValueError("grant needs an agent_id")
    if not str(reason or "").strip():
        raise ValueError("grant needs a reason -- an unexplained grant is the one nobody can "
                         "safely revoke later, because no one knows what it was for")
    if role not in ROLE_TEMPLATES:
        raise ValueError(f"unknown role '{role}' (known: {sorted(ROLE_TEMPLATES)})")
    if permanent and hours:
        raise ValueError("pass --hours or --permanent, not both")
    if not permanent:
        if hours is None:
            raise ValueError(
                "a grant must be time-boxed (--hours N) or explicitly --permanent. T151: an "
                "OBSERVED time box is a deadline; the danger was never the expiry, it was that "
                "nothing rendered it.")
        if hours <= 0 or hours > MAX_HOURS:
            raise ValueError(f"--hours must be in (0, {MAX_HOURS}]")

    granter = _granter(by)
    if agent_id == by:
        raise PermissionError(
            f"'{by}' may not grant to itself. Self-escalation through this file is the primitive "
            f"core/comm/toolbox.py:862 names by name; a second party mints your authority.")

    tmpl = ROLE_TEMPLATES[role]
    eff_caps = caps_from(caps) if caps is not None else set(tmpl["caps"])
    eff_scope = list(path_scope) if path_scope is not None else list(tmpl["path_scope"])
    _bounded_by_granter(granter, eff_caps, eff_scope)

    expires_at = None
    if not permanent:
        expires_at = (datetime.now(timezone.utc)
                      + timedelta(hours=float(hours))).strftime("%Y-%m-%dT%H:%M:%SZ")

    rec = {
        "agent_id": agent_id,
        "role": role,
        "caps": sorted(c.value for c in eff_caps),
        "path_scope": eff_scope,
        "granted_by": by,
        "granted_at": _now_iso(),
        "expires_at": expires_at,
        "reason": str(reason).strip(),
    }
    if request_ref:
        rec["request_ref"] = request_ref

    doc = _read_doc()
    doc["grants"] = [g for g in doc["grants"] if g.get("agent_id") != agent_id] + [rec]
    _write_doc(doc)
    return rec


def revoke(agent_id: str, by: str, reason: str) -> dict:
    """Remove a grant. The reversibility path -- a bad grant should not need a git revert.

    Removal rather than a quarantined stub: resolve() already fail-closes to QUARANTINED for
    anything unregistered, so an explicit quarantine record would state twice what absence
    states once, and the audit trail lives in git history rather than in a tombstone.
    """
    if not str(reason or "").strip():
        raise ValueError("revoke needs a reason")
    _granter(by)
    doc = _read_doc()
    before = len(doc["grants"])
    removed = [g for g in doc["grants"] if g.get("agent_id") == agent_id]
    if not removed:
        raise ValueError(f"no grant for '{agent_id}' to revoke")
    doc["grants"] = [g for g in doc["grants"] if g.get("agent_id") != agent_id]
    _write_doc(doc)
    return {"agent_id": agent_id, "removed": before - len(doc["grants"]),
            "was": removed[0], "revoked_by": by, "reason": reason, "at": _now_iso()}


def listing() -> list:
    """Every stored grant as a plain dict, newest-expiring first. Read-only."""
    doc = _read_doc()
    return sorted(doc.get("grants", []),
                  key=lambda g: (g.get("expires_at") is None, str(g.get("expires_at") or ""),
                                 str(g.get("agent_id"))))
