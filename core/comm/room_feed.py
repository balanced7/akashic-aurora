"""Namespace-aware feed-stream discovery -- the backend half of readable side rooms.

A ROOM is a bus namespace. The console's ROOMS panel has always been able to LIST them
(a room exists when someone beats in it) while being unable to read one: the feed's
stream discovery hardcoded the default prefix, so every room rendered as the default
room's conversation. This module is the missing parameter, extracted rather than
inlined so the console keeps one import and two call sites (the ratified UI boundary:
claude authors modules and backend, deepseek owns bifrost_ui.py integration).

Deliberately narrow: stream discovery only. No HTTP, no rendering, no Bus construction,
no cursor state. Everything downstream of discovery (backfill, tail, SSE) already
threads a stream list correctly and needs no change.

THE VALIDATION IS LOAD-BEARING, not hygiene. The namespace arrives from a query string
and lands in a Redis KEYS pattern: ``ns=*`` would match the entire keyspace and leak
every room in a single request, and ``ns=bifrost:inbox`` would silently widen the scope.
Refusal is LOUD (ValueError) and happens BEFORE Redis is touched -- sanitize-and-continue
would hide the attempt, and a feed that quietly widens is worse than one that cannot open.
"""
from __future__ import annotations

import re
from typing import List

# A namespace is a bare token: the live shapes are 'bifrost' (default), the
# BIFROST_NAMESPACE env value, 'sandbox', and the 'test-*' drill convention.
# No ':' (it is the key separator -- allowing it lets a caller reach a deeper
# key family), no glob metacharacters, no whitespace, no control bytes.
_NS_RE = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")

# The two stream families the console renders as conversation. Everything else sharing
# the prefix -- cursor:, mailbox:, control:, worklive: -- is coordination state and must
# never appear in a feed (a pattern one character greedier renders bookkeeping as chat).
_INBOX_SUFFIX = "inbox"
_BROADCAST_SUFFIX = "broadcast"


def valid_namespace(ns) -> bool:
    """True iff `ns` is a well-formed room name. Total: never raises, accepts anything."""
    return isinstance(ns, str) and bool(_NS_RE.match(ns))


def streams_for(client, ns: str) -> List[str]:
    """Feed streams for room `ns`: its per-agent inboxes plus its broadcast.

    Returns [] for a well-formed room nobody is beating in -- an empty room is not a
    conversation, and that is a valid answer, not an error. Raises ValueError for a
    malformed room BEFORE touching Redis.

    The broadcast key is included only when it exists, so an unknown room is genuinely
    empty rather than a list of one dead stream.
    """
    if not valid_namespace(ns):
        raise ValueError(
            f"refusing namespace {ns!r}: a room name is a bare token "
            r"([A-Za-z0-9][A-Za-z0-9_-]{0,63}) -- no ':', no globs, no whitespace. "
            "An unvalidated namespace reaches Redis as a KEYS pattern.")
    out: List[str] = []
    try:
        out.extend(str(k) for k in (client.keys(f"{ns}:{_INBOX_SUFFIX}:*") or []))
        bc = f"{ns}:{_BROADCAST_SUFFIX}"
        if client.keys(bc):
            out.append(bc)
    except Exception:
        return []                      # a dead client is an empty feed, never a crash
    return out
