"""
Supersession: a newer record retires an older one (temporal correctness).

Semantic Relationship: NewRecord supersedes OldRecord (the old becomes inactive)

First in the shared-primitive build order — the Ranker and the loaders honor it so
stale facts stop surfacing. The convention is tiny and field-based, so it works
across any record dict:

- a record is **active** unless it carries `superseded: True`
- a record that replaces another carries `supersedes: <old_id>` (the `supersedes`
  relationship from the 66-type vocabulary)

Writing a superseding record stamps the new one and retires the old one; reads
filter to active-only. Records that predate this convention simply lack the fields
and are treated as active — so it's safe to adopt incrementally.

See docs/shared-primitives-spec.md.
"""

from typing import Any, Dict, Iterable, List, Optional


def is_active(record: Dict[str, Any]) -> bool:
    """True unless this record has been superseded by a newer one."""
    return not record.get("superseded", False)


def mark_supersedes(new_record: Dict[str, Any], old_id: Optional[str]) -> Dict[str, Any]:
    """Stamp `new_record` as superseding `old_id` (no-op if old_id is falsy)."""
    if old_id:
        new_record["supersedes"] = old_id
    return new_record


def retire(record: Dict[str, Any]) -> Dict[str, Any]:
    """Flip a record to superseded (inactive)."""
    record["superseded"] = True
    return record


def active_only(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop superseded records — the default read filter."""
    return [r for r in records if is_active(r)]
