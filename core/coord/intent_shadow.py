"""Deterministic, renderer-neutral previews of proposed Aurora actions.

An intent shadow is a ghost, not an execution path.  ``build_intent_shadow``
normalizes a typed ToolBox action against the live advertised schema, asks the
same authority detector the real ToolBox method asks, and renders the action's
causal shape without importing the bus, nudge, or steer writers.

V1 deliberately covers one coherent family: Bifrost send, hard nudge, and soft
steer on the ToolBox door.  Other doors and actions refuse rather than inherit
effects by name.  The existing ``core.coord.intent`` remains peer-work
coordination; this module does not overload that separate authority region.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import inspect
import json
import math
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from core.primitives.epistemic import derive_epistemic_view


_SUPPORTED = ("bifrost_send", "bifrost_nudge", "bifrost_steer")
_SEND_KINDS = {"chat", "note", "request", "handoff", "nudge", "hint"}
_TEXT_PREVIEW_CHARS = 240


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_action(target: str) -> Tuple[str, str]:
    raw = str(target or "").strip()
    if ":" not in raw:
        raise ValueError("intent shadow action must be typed as toolbox:<verb>")
    door, name = (part.strip().lower().replace("-", "_")
                  for part in raw.split(":", 1))
    if door != "toolbox":
        raise ValueError("intent shadow v1 supports only toolbox:<verb> actions")
    if name not in _SUPPORTED:
        raise ValueError(
            f"unsupported intent-shadow action {raw!r}; supported: "
            + ", ".join(f"toolbox:{item}" for item in _SUPPORTED)
        )
    return door, name


def _toolbox_contract(name: str) -> Tuple[Mapping[str, Any], Any]:
    """Ask the advertised ToolBox schema and callable; never copy their args."""
    from core.comm.toolbox import TOOLS, ToolBox

    row = next((item.get("function", {}) for item in TOOLS
                if item.get("function", {}).get("name") == name), None)
    method = getattr(ToolBox, name, None)
    if not row or not callable(method):
        raise ValueError(f"unsupported ToolBox action {name!r}: schema or method is absent")
    return row, method


def _normalize_arguments(name: str, arguments: Mapping[str, Any] | None) -> Dict[str, Any]:
    if arguments is None:
        supplied: Dict[str, Any] = {}
    elif isinstance(arguments, Mapping):
        supplied = dict(arguments)
    else:
        raise ValueError("intent shadow arguments must be a JSON object")

    schema, method = _toolbox_contract(name)
    params = schema.get("parameters") or {}
    properties = dict(params.get("properties") or {})
    unknown = sorted(set(supplied) - set(properties))
    if unknown:
        raise ValueError(f"unsupported argument(s) for {name}: {', '.join(unknown)}")
    for required in params.get("required") or []:
        if required not in supplied:
            raise ValueError(f"required argument {required!r} is missing for {name}")

    normalized = dict(supplied)
    signature = inspect.signature(method)
    for param_name, param in signature.parameters.items():
        if param_name == "self" or param_name in normalized:
            continue
        if param.default is not inspect.Parameter.empty:
            normalized[param_name] = param.default

    # Match ToolBox.bifrost_send exactly: unsupported kinds degrade to chat.
    if name == "bifrost_send":
        kind = str(normalized.get("kind") or "chat")
        normalized["kind"] = kind if kind in _SEND_KINDS else "chat"
    return normalized


def _default_resolve_recipient(raw: str) -> str:
    from core.fleet.residents import resolve_agent

    try:
        return str(resolve_agent(raw) or raw)
    except Exception as exc:
        raise RuntimeError(
            f"intent shadow could not resolve load-bearing target {raw!r}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def _content_view(text: Any) -> Dict[str, Any]:
    raw = str(text or "")
    return {
        "chars": len(raw),
        "sha256": hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest(),
        "preview": raw[:_TEXT_PREVIEW_CHARS],
        "truncated": len(raw) > _TEXT_PREVIEW_CHARS,
    }


def _argument_view(arguments: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: (_content_view(value) if key == "text" else value)
            for key, value in arguments.items()}


def _effect(effect_id: str, certainty: str, claim: str, basis: str) -> Dict[str, str]:
    return {"id": effect_id, "certainty": certainty, "claim": claim, "basis": basis}


def _action_profile(name: str, arguments: Mapping[str, Any]) -> Dict[str, Any]:
    delivery = [
        _effect("bifrost.message.enqueue", "expected", "lane/legacy delivery is appended",
                "core.comm.bus.Bus._emit"),
        _effect("wake.bell.publish", "expected", "the recipient doorbell is rung",
                "core.comm.bus.Bus._ring_bell"),
        _effect("sender.presence.refresh", "expected", "sender presence is refreshed",
                "core.comm.bus.Bus._touch"),
    ]
    if name == "bifrost_nudge":
        return {
            "fidelity": "interrupt",
            "planes": ["bifrost.delivery", "peer.control", "recipient.attention"],
            "effects": [
                _effect("peer.control.interrupt_flag", "expected",
                        "a TTL-bounded barge-in flag is set", "core.comm.nudge.nudge"),
                *delivery,
                _effect("recipient.turn.interrupt", "conditional",
                        "a cooperating runner stops at its next round boundary",
                        "core.comm.nudge.is_nudged"),
            ],
            "risk": "high",
            "risk_reason": "hard interrupt can displace a peer's current work",
        }
    if name == "bifrost_steer":
        return {
            "fidelity": "steer",
            "planes": ["bifrost.delivery", "peer.control", "recipient.attention"],
            "effects": [
                _effect("peer.control.steer_queue", "expected",
                        "a fact is queued between tool rounds", "core.comm.nudge.steer_push"),
                *delivery,
                _effect("recipient.context.splice", "conditional",
                        "a cooperating runner folds the fact into its current task",
                        "core.comm.nudge.steer_drain"),
            ],
            "risk": "elevated",
            "risk_reason": "soft steer changes a peer's live task context",
        }

    kind = str(arguments.get("kind") or "chat")
    effects = list(delivery)
    if kind == "handoff":
        effects.append(_effect(
            "bifrost.salient.project", "conditional",
            "salient mail is projected to the durable event ledger",
            "core.comm.promoter.promote",
        ))
    effects.append(_effect(
        "recipient.turn.wake", "conditional",
        "an armed watcher may spend a recipient model turn",
        "scripts.bifrost_wake.watch",
    ))
    return {
        "fidelity": f"message:{kind}",
        "planes": ["bifrost.delivery", "recipient.attention"],
        "effects": effects,
        "risk": "elevated",
        "risk_reason": "a delivered message can wake a peer and cannot be unsent",
    }


def _epistemic(authority: Mapping[str, Any], name: str) -> Dict[str, Any]:
    sources = [str(item) for item in authority.get("source") or [] if str(item)]
    known = authority.get("state") in {"observed", "refused"} and bool(sources)
    risk = "blocked" if authority.get("allowed") is False else "attention_required"
    return derive_epistemic_view({
        "authority": {"value": "governed_source" if known else "unknown", "basis": sources},
        "claim_kind": {"value": "proposed", "basis": [f"core.coord.intent_shadow:{name}"]},
        "currency": {"value": "current", "basis": ["core.comm.toolbox:TOOLS+method"]},
        "identity_state": {"value": "unknown", "basis": []},
        "risk": {"value": risk, "basis": [f"core.coord.intent_shadow:{name}:risk"]},
    }).to_dict()


def build_intent_shadow(
    subject: str,
    target: str,
    arguments: Mapping[str, Any] | None = None,
    *,
    authorize: Optional[Callable[[str, str, Mapping[str, Any]], Mapping[str, Any]]] = None,
    resolve_recipient: Optional[Callable[[str], str]] = None,
    observed_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build one ``intent.shadow.v1`` without executing the proposed action."""
    subject = str(subject or "").strip()
    if not subject:
        raise ValueError("intent shadow subject is required")
    door, name = _parse_action(target)
    normalized = _normalize_arguments(name, arguments)

    addressed_as = str(normalized.get("to") or "")
    address = addressed_as.strip().lower()
    broadcast = name == "bifrost_send" and address in {"", "*", "all", "both"}
    if name in {"bifrost_nudge", "bifrost_steer"} and address in {"", "*", "all", "both"}:
        raise ValueError(f"{name} must target one seat; broadcasts are refused")
    resolver = resolve_recipient or _default_resolve_recipient
    resolved = "*" if broadcast else str(resolver(address) or address)
    target_row = {
        "kind": "broadcast" if broadcast else "seat",
        "addressed_as": addressed_as,
        "resolved": resolved,
    }

    authorizer = authorize
    if authorizer is None:
        from core.trust.action_authority import evaluate_toolbox_bus_action
        authorizer = evaluate_toolbox_bus_action
    authority = dict(authorizer(subject, name, normalized))
    # Execution needs its full teaching error; the shadow already carries the
    # same verdict structurally (state/missing_caps/kind_allowed).  Rendering
    # both spends tokens on one fact twice.  A universal allowlist (None) is
    # likewise represented by kind_allowed=True and needs no second spelling.
    authority.pop("execution_error", None)
    if authority.get("bus_send_kinds") is None:
        authority.pop("bus_send_kinds", None)
    profile = _action_profile(name, normalized)
    content = str(normalized.get("text") or "")
    commit_reason = str(profile["risk_reason"])

    out: Dict[str, Any] = {
        "schema": "intent.shadow.v1",
        "subject": subject,
        "observed_at": observed_at or _utc(),
        "action": {"door": door, "name": name, "address": f"{door}:{name}"},
        "target": target_row,
        "fidelity": profile["fidelity"],
        "scope": {"planes": list(profile["planes"]), "broadcast": broadcast},
        "arguments": _argument_view(normalized),
        "proposed_effects": list(profile["effects"]),
        "cost": {
            "verb_calls": 1,
            "content_chars": len(content),
            "rough_content_tokens": max(1, math.ceil(len(content) / 4)),
            "recipient_model_turns": {"state": "conditional", "range": [0, 1]},
            "latency": "unmeasured",
        },
        "reversibility": {
            "state": "irreversible_after_observation",
            "reason": "control TTLs expire, but delivered context and displaced work cannot be undone",
        },
        "authority": authority,
        # The causal reason lives once, under commit.  Repeating it under risk
        # made the supposedly compact shadow larger without adding information.
        "risk": {"level": profile["risk"]},
        "commit": {
            "required": True,
            "enforced": False,
            "state": "required_unenforced",
            "reason": commit_reason,
        },
        "epistemic": _epistemic(authority, name),
        "bounds": {
            "target_door": "toolbox",
            "supported_action_count": len(_SUPPORTED),
            "content_preview_chars": _TEXT_PREVIEW_CHARS,
        },
        "blind": [
            "preview does not prove bus availability, recipient attendance, or eventual adoption",
            "commit is disclosed but no execution token is enforced yet",
            "token estimate covers message content only, not prompt or tool overhead",
        ],
        # Effects of BUILDING THE SHADOW. Proposed effects live above and are never
        # allowed to masquerade as things this read actually did.
        "effects": [],
    }
    semantic = {key: value for key, value in out.items()
                if key not in {"observed_at", "fingerprint"}}
    out["fingerprint"] = hashlib.sha256(json.dumps(
        semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str,
    ).encode("utf-8", "replace")).hexdigest()
    return out


def render_intent_shadow(shadow: Mapping[str, Any]) -> str:
    """Compact human projection; structured JSON remains the renderer contract."""
    action = shadow.get("action") or {}
    target = shadow.get("target") or {}
    auth = shadow.get("authority") or {}
    commit = shadow.get("commit") or {}
    cost = shadow.get("cost") or {}
    lines = [
        f"# shadow subject={shadow.get('subject')} action={action.get('address')} "
        f"fingerprint={str(shadow.get('fingerprint') or '')[:12]}",
        f"  target {target.get('kind')}:{target.get('resolved')} "
        f"(addressed as {target.get('addressed_as')!r})",
        f"  fidelity {shadow.get('fidelity')} | authority={auth.get('state')} "
        f"allowed={auth.get('allowed')}",
        f"  risk {(shadow.get('risk') or {}).get('level')} | "
        f"commit={commit.get('state')}",
        f"  cost chars={cost.get('content_chars')} rough_tokens={cost.get('rough_content_tokens')} "
        f"recipient_turns={cost.get('recipient_model_turns', {}).get('range')}",
    ]
    for effect in shadow.get("proposed_effects") or []:
        lines.append(f"  -> [{effect.get('certainty')}] {effect.get('id')}: {effect.get('claim')}")
    lines.append("  preview effects=none")
    if shadow.get("blind"):
        lines.append("  blind: " + "; ".join(str(item) for item in shadow["blind"]))
    return "\n".join(lines)
