"""
Node lifecycle (Slice C2, delta E3) -- bi-temporal stamping + supersession as TYPE-AGNOSTIC
functions over the `BiTemporal` protocol, NOT a base class. Chapter and Resource each keep their
own id strategy and content; they share only this behavior.

Semantic Relationship: NewNode supersedes OldNode (valid_to closes; links forward)

Rules (deltas E1/E4):
- **regenerate in place** keeps the node's STABLE id and never moves `valid_from` (the origin);
  it refreshes `recorded_at`. Idempotent: an unchanged `version_hash` is a no-op write-or-skip.
- **supersede** is the only way a bi-temporal node goes inactive: it closes the old node's
  `valid_to`, adds the real `replaces` / `is_version_of` edges (66-type vocabulary), and persists
  BOTH (the old stays queryable; inbound links resolve to it and forward via `replaces`).
- `valid_to` is the single writer of "inactive" for bi-temporal nodes (E4); `is_active` here and
  `core/primitives/supersession.is_active` agree (open valid_to AND not field-superseded).
"""
import json
from typing import Any, Callable, Optional

from core.narrative.schema import Edge


def is_active(node: Any) -> bool:
    """Active while `valid_to` is open (and not field-superseded). One truth for both axes."""
    if getattr(node, "valid_to", None):
        return False
    return not getattr(node, "superseded", False)


def stamp(node: Any, *, now: str, origin: Optional[str] = None) -> Any:
    """Set `valid_from` once (the origin), refresh `recorded_at`. Never moves the origin."""
    if not getattr(node, "valid_from", None):
        node.valid_from = origin or now
    node.recorded_at = now
    return node


def regenerate_in_place(store, node: Any, key_fn: Callable[[str], str], *, now: str,
                        origin: Optional[str] = None) -> Any:
    """Persist `node` under its STABLE id, preserving a prior `valid_from`. Idempotent: if the
    stored node has the same `version_hash`, only `recorded_at` would change, so we skip the write
    to keep re-runs byte-stable."""
    raw = store.get(key_fn(node.id))
    if raw:
        try:
            prev = json.loads(raw)
            if prev.get("valid_from"):
                node.valid_from = prev["valid_from"]                  # never move the origin
            if (prev.get("version_hash") and getattr(node, "version_hash", "")
                    and prev["version_hash"] == node.version_hash and prev.get("valid_to") == node.valid_to):
                return node                                           # unchanged content -> no rewrite
        except (ValueError, TypeError):
            pass
    stamp(node, now=now, origin=origin)
    store.set(key_fn(node.id), json.dumps(node.to_dict()))
    return node


def supersede(store, old_node: Any, new_node: Any, key_fn: Callable[[str], str], *, now: str) -> Any:
    """`new_node` supersedes `old_node`: close the old's validity, link the two with real edges,
    persist both. The old node is NEVER deleted -- it stays queryable and forwards via `replaces`."""
    if is_active(old_node):
        old_node.valid_to = now
        old_node.relates = list(getattr(old_node, "relates", None) or [])
        if not any(e.type == "replaces" and e.target == new_node.id for e in old_node.relates):
            old_node.relates.append(Edge("replaces", new_node.id))
        store.set(key_fn(old_node.id), json.dumps(old_node.to_dict()))
    new_node.relates = list(getattr(new_node, "relates", None) or [])
    if not any(e.type == "is_version_of" and e.target == old_node.id for e in new_node.relates):
        new_node.relates.append(Edge("is_version_of", old_node.id))
    # ALWAYS persist the new node here: supersede mutates `relates`, which the version_hash does
    # not cover, so the regenerate skip-optimization must not be allowed to drop the edge.
    raw = store.get(key_fn(new_node.id))
    if raw:
        try:
            prev = json.loads(raw)
            if prev.get("valid_from"):
                new_node.valid_from = prev["valid_from"]       # never move the origin
        except (ValueError, TypeError):
            pass
    stamp(new_node, now=now)
    store.set(key_fn(new_node.id), json.dumps(new_node.to_dict()))
    return new_node
