"""One read-only authority detector shared by ToolBox execution and intent shadows.

The intent-shadow contract is only useful if the preview asks the same detector
as the action door.  A second permission table would eventually promise an
action that the real door refuses (or, worse, hide a refusal the real door
enforces).  This module therefore owns the small ToolBox Bifrost action family:
the actual methods call it immediately before acting and the shadow calls it
while remaining read-only.

Registry failures preserve the historical ToolBox fail-open execution policy,
but the returned preview state is ``unknown`` rather than an invented allow.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Tuple


# Values, not enum member names: these are also the strings rendered by ground
# and security/acl.json.  Nudge/steer require BUS_SEND as well as their special
# capability because the real door checks both the special gate and kind gate.
TOOLBOX_BUS_REQUIREMENTS: Dict[str, Tuple[str, ...]] = {
    "bifrost_send": ("bus.send",),
    "bifrost_nudge": ("bus.send", "bus.nudge"),
    "bifrost_steer": ("bus.send", "bus.steer"),
    "bifrost_hint": ("bus.send",),
}

_FIXED_KIND = {
    "bifrost_nudge": "nudge",
    "bifrost_steer": "steer",
    "bifrost_hint": "hint",
}


def requirements_for_toolbox_action(action: str) -> Tuple[str, ...]:
    """Mechanically declared capability requirements for one ToolBox action."""
    return TOOLBOX_BUS_REQUIREMENTS.get(str(action or ""), ())


def evaluate_toolbox_bus_action(
    subject: str,
    action: str,
    arguments: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return the real ToolBox Bifrost authorization decision without acting.

    ``execution_error`` is deliberately the exact string the ToolBox method
    returns on refusal.  On registry failure it is empty: execution keeps its
    existing fail-open behavior while the shadow exposes ``state=unknown``.
    """
    subject = str(subject or "").strip()
    action = str(action or "").strip()
    if not subject:
        raise ValueError("ToolBox bus authority subject is required")
    if action not in TOOLBOX_BUS_REQUIREMENTS:
        raise ValueError(f"unsupported ToolBox bus action {action!r}")

    args = dict(arguments or {})
    kind = str(_FIXED_KIND.get(action) or args.get("kind") or "chat")
    required = list(requirements_for_toolbox_action(action))
    source = [
        "security/acl.json via core.trust.registry.resolve",
        "core.trust.registry.Grant.can_send_kind",
    ]
    try:
        from core.trust import registry
        grant = registry.resolve(subject)
        caps = sorted(getattr(cap, "value", str(cap)) for cap in grant.caps)
        role = str(grant.role)
        kinds = None if grant.bus_send_kinds is None else sorted(grant.bus_send_kinds)
    except Exception as exc:
        return {
            "state": "unknown",
            "allowed": None,
            "role": "UNKNOWN",
            "required_caps": required,
            "missing_caps": [],
            "kind": kind,
            "kind_allowed": None,
            "source": source,
            "error": f"{type(exc).__name__}: {exc}",
            "execution_error": "",
        }

    missing = sorted(set(required) - set(caps))
    special = next((cap for cap in required if cap != "bus.send" and cap in missing), None)
    kind_allowed = "bus.send" in caps and (kinds is None or kind in kinds)
    execution_error = ""
    if special:
        execution_error = (
            f"ERROR: '{subject}' lacks the {special} capability (role={role}) -- "
            "this bus action is refused (deny-by-default). Ask a super-admin to grant it."
        )
    elif not kind_allowed:
        execution_error = (
            f"ERROR: '{subject}' (role={role}) may not send bus kind={kind!r} -- "
            "deny-by-default. Ask a super-admin to widen bus_send_kinds."
        )

    allowed = not bool(execution_error)
    return {
        "state": "observed" if allowed else "refused",
        "allowed": allowed,
        "role": role,
        "required_caps": required,
        "missing_caps": missing,
        "kind": kind,
        "kind_allowed": kind_allowed,
        "bus_send_kinds": kinds,
        "source": source,
        "execution_error": execution_error,
    }
