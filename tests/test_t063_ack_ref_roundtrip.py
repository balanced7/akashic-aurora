"""T063 completion pin -- RED first (M3).

THE GAP (T063 is marked DONE in the ledger and does not round-trip; lived twice on
2026-07-27/28): the MAILBOX renders messages by sha prefix (`[unhandled] ca13a5bad5
handoff ...`), but bifrost-ack resolves only stream-id forms. Acking the mailbox's own
printed ref is REFUSED with a doubly-misleading error ("has no promoted record -- only
salient messages carry acks") for a message that IS a handoff and IS promoted. The
operator's natural copy-paste from one organ's output into its sibling verb fails, and
the failure blames the wrong cause. Five kimi handoffs sat unacked behind exactly this,
pinning the wake watcher.

THE PIN: promoter.resolve_ack_ref(agent, ref) must resolve EVERY id form the sibling
verbs print -- raw stream id, 'bifrost:<id>', and the mailbox sha prefix -- to an
ackable stream id, and the door-level ack must then succeed on it.
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus  # noqa: E402

AGENT = "claude"          # a GRANTED id -- unknown ids are correctly quarantined by acl
TAG = uuid.uuid4().hex[:8]


def test_mailbox_sha_prefix_resolves_and_acks():
    # promote=True: auto-promotion is OFF under pytest by design (promoter-pollution
    # guard, bus.py:156); conftest isolation makes explicit promotion safe here.
    sender = Bus("kimi", promote=True)
    if not sender.online:
        print("SKIPPED (Redis not running)")
        return
    mid = sender.send(AGENT, "handoff", f"handoff-body-{TAG}")
    assert mid

    from core.comm import mailbox
    ns = sender.ns
    mailbox.catch_up(ns, AGENT)
    hit = mailbox.explain(ns, AGENT, mid)            # OUR entry, located by stream id
    assert hit.get("available") and hit.get("found"), f"mailbox must index the handoff: {hit}"
    sha_ref = str(hit["sha"])[:10]                   # exactly what the mailbox renders

    from core.comm.promoter import resolve_ack_ref, ack_verdict, ack
    resolved = resolve_ack_ref(AGENT, sha_ref)
    assert resolved, (
        f"ROUND-TRIP BROKEN: the mailbox's own printed ref '{sha_ref}' does not resolve to "
        f"an ackable stream id. The operator's copy-paste from mailbox output into "
        f"bifrost-ack fails, and the refusal blames message class instead of id form.")
    allowed, why = ack_verdict(AGENT, resolved)
    assert allowed, f"resolved id {resolved} must pass the ack verdict (got: {why})"
    assert ack(AGENT, resolved, note="t063 pin")

    # The other two printed forms keep working through the same resolver.
    assert resolve_ack_ref(AGENT, resolved) == resolved
    assert resolve_ack_ref(AGENT, f"bifrost:{resolved}") == resolved


def test_resolved_but_unackable_blames_content_not_form():
    """kimi fence-lite finding 1: when a sha ref RESOLVES but no id passes the verdict, the
    refusal must carry the TRUE content reason (not promoted / quarantined / wrong addressee)
    and must NOT append the id-form hint -- otherwise the fix launders a content refusal into
    a form refusal, re-creating the doubly-misleading class it exists to kill."""
    sender = Bus("kimi", promote=False)          # NOT promoted -> unackable by content
    if not sender.online:
        print("SKIPPED (Redis not running)")
        return
    mid = sender.send(AGENT, "handoff", f"unpromoted-{TAG}")
    from core.comm import mailbox
    ns = sender.ns
    mailbox.catch_up(ns, AGENT)
    hit = mailbox.explain(ns, AGENT, mid)
    assert hit.get("found")
    sha_ref = str(hit["sha"])[:10]

    from core.comm.promoter import resolve_ack_ref
    resolved = resolve_ack_ref(AGENT, sha_ref)
    assert resolved, "resolution itself must succeed -- the message exists in the mailbox"
    # The door-level contract: hint fires ONLY when resolution FAILED.
    from agent_cli import _ack_refusal_hint
    assert _ack_refusal_hint(sha_ref, resolved is None) == "", (
        "FORM-BLAME LAUNDERING: resolution succeeded but the door still appends the "
        "id-form hint, blaming the ref for a content refusal.")
    assert _ack_refusal_hint(sha_ref, True) != "", (
        "the hint must still fire when a hex ref genuinely fails to resolve")


if __name__ == "__main__":
    test_mailbox_sha_prefix_resolves_and_acks()
    print("PASS")
