"""T060 N0: pure route explanation and bounded shadow-delivery counters.

This module is observational.  ``route()`` explains the existing
``packet_spec.KIND_LANE`` decision; it does not select a lane for the transport.
The Bus continues to route through ``packet_spec.lane_for()``.  Counter writes are
best-effort and bounded to static fields so telemetry can never fail a send or
turn untrusted kind strings into unbounded Redis cardinality.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Optional, Tuple

from core.comm import packet_spec


MODE = "shadow"
UNKNOWN_RULE = "_unknown"
MIRROR_OUTCOMES = ("success", "failure", "unmapped", "disabled")
REPLY_OUTCOMES = ("success", "fallback", "failure")

_POLICY_CANONICAL = json.dumps(
    sorted((str(kind), str(lane)) for kind, lane in packet_spec.KIND_LANE.items()),
    separators=(",", ":"),
)
POLICY_VERSION = f"kind-lane:{hashlib.sha256(_POLICY_CANONICAL.encode('utf-8')).hexdigest()[:12]}"


@dataclass(frozen=True)
class RoutingDecision:
    kind: str
    lane: Optional[str]
    known: bool
    rule_id: str
    policy_version: str = POLICY_VERSION
    mode: str = MODE

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "lane": self.lane,
            "known": self.known,
            "rule_id": self.rule_id,
            "policy_version": self.policy_version,
            "mode": self.mode,
        }


def route(kind: Any) -> RoutingDecision:
    """Explain the current static kind-to-lane rule without enforcing anything."""
    normalized = str(kind)
    lane = packet_spec.lane_for(normalized)
    known = normalized in packet_spec.KIND_LANE
    label = normalized if known else UNKNOWN_RULE
    return RoutingDecision(
        kind=normalized,
        lane=lane,
        known=known,
        rule_id=f"kind:{label}",
    )


def metric_key(namespace: str) -> str:
    return f"{namespace}:route:shadow:stats"


def _labels() -> Tuple[str, ...]:
    return tuple(sorted(str(kind) for kind in packet_spec.KIND_LANE)) + (UNKNOWN_RULE,)


def metric_field_schema() -> Tuple[str, ...]:
    """All counter fields this module can create (a static cardinality ceiling)."""
    labels = _labels()
    fields = [f"decision:{label}" for label in labels]
    fields.extend(
        f"mirror:{label}:{outcome}"
        for label in labels
        for outcome in MIRROR_OUTCOMES
    )
    fields.extend(f"reply:reply:{outcome}" for outcome in REPLY_OUTCOMES)
    return tuple(fields)


_METRIC_FIELD_SCHEMA = frozenset(metric_field_schema())


def _label(decision: RoutingDecision) -> str:
    return decision.kind if decision.kind in packet_spec.KIND_LANE else UNKNOWN_RULE


def _observation_fields(decision: RoutingDecision, outcome: str,
                        family: str) -> Optional[Tuple[str, str]]:
    label = _label(decision)
    if family == "mirror" and outcome in MIRROR_OUTCOMES:
        outcome_field = f"mirror:{label}:{outcome}"
    elif family == "reply" and label == "reply" and outcome in REPLY_OUTCOMES:
        outcome_field = f"reply:reply:{outcome}"
    else:
        return None
    decision_field = f"decision:{label}"
    if decision_field not in _METRIC_FIELD_SCHEMA or outcome_field not in _METRIC_FIELD_SCHEMA:
        return None
    return decision_field, outcome_field


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_observation(client: Any, namespace: str, decision: RoutingDecision,
                       outcome: str, *, family: str = "mirror") -> bool:
    """Best-effort increment of one decision and one physical outcome.

    The field names are selected only from ``metric_field_schema``.  Unknown kinds
    collapse to ``_unknown``; caller-provided family/outcome strings outside the
    closed roster create no field.  All Redis failures return ``False`` and are
    deliberately swallowed because observation is never load-bearing.
    """
    fields = _observation_fields(decision, str(outcome), str(family))
    if client is None or fields is None:
        return False
    key = metric_key(str(namespace))
    started_at = _utc_now()
    try:
        pipeline = client.pipeline(transaction=False)
    except Exception:
        pipeline = None
    if pipeline is not None:
        try:
            pipeline.hsetnx(key, "_meta:started_at", started_at)
            pipeline.hsetnx(key, "_meta:policy_version", POLICY_VERSION)
            for field in fields:
                pipeline.hincrby(key, field, 1)
            pipeline.execute()
            return True
        except Exception:
            return False

    # Tiny test doubles and alternate Redis clients may not expose pipelines.
    # Keep the same fail-soft contract without requiring that optional surface.
    try:
        client.hsetnx(key, "_meta:started_at", started_at)
        client.hsetnx(key, "_meta:policy_version", POLICY_VERSION)
    except Exception:
        pass
    try:
        for field in fields:
            client.hincrby(key, field, 1)
        return True
    except Exception:
        return False


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def route_stats(client: Any, namespace: str) -> Dict[str, Any]:
    """Read the bounded counter hash as a stable JSON-friendly object."""
    raw: Dict[Any, Any] = {}
    online = client is not None
    if client is not None:
        try:
            raw = client.hgetall(metric_key(str(namespace))) or {}
        except Exception:
            online = False
    normalized = {_text(key): value for key, value in raw.items()}
    counts: Dict[str, int] = {}
    for field in metric_field_schema():
        if field not in normalized:
            continue
        try:
            counts[field] = int(normalized[field])
        except (TypeError, ValueError):
            continue
    stored_policy = _text(normalized.get("_meta:policy_version", ""))
    return {
        "mode": MODE,
        "policy_version": POLICY_VERSION,
        "stored_policy_version": stored_policy,
        "policy_matches": not stored_policy or stored_policy == POLICY_VERSION,
        "started_at": _text(normalized.get("_meta:started_at", "")),
        "metric_key": metric_key(str(namespace)),
        "counter_field_limit": len(_METRIC_FIELD_SCHEMA),
        "online": online,
        "counts": counts,
    }
