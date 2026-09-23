"""wake tiers -- the priority dimension the wake decision was missing.

WHY THIS EXISTS, and it is a measured incident rather than a theory.

On 2026-09-23 the operator sent four DIRECTED messages (to=claude, kind=chat) over Discord
across five days. Every one of them SHOULD have woken this seat: `wake_worthy()` carries an
operator override that outranks the kind allowlist, the messages were directed rather than
`to="*"` lounge broadcasts, so the carve-out did not apply, and the predicate would have
returned True on all four. None of them woke anything.

The predicate was never consulted, because nothing was armed to consult it. And nothing stayed
armed because of an ordering property that is DESIGNED, not broken: a watcher armed over
unconsumed mail fires immediately, by construction -- pending mail must wake a watcher armed
after it arrived (bifrost_api.wake_block's SEED rule). With ~1,383 messages standing on the
work lane, every arm exited within seconds, so no watcher persisted, so the operator override
was never reached.

TIER 0 STARVED ON TIER 3 VOLUME. The priority mechanism was built and correct; the queue it
lived in had become unusable, so it was never asked.

THE INSIGHT THIS MODULE ENCODES. The obvious remedy is "consume the backlog, then arm" -- and
the ordering lesson (wake_consume_then_arm) is right that handled mail should be consumed
before arming. But consuming mail you have NOT handled, purely to make a watcher armable, is
the one thing the detect-without-consume design exists to prevent: the watcher would drain mail
the real reader has never seen.

A TIER FLOOR SOLVES IT WITHOUT CONSUMING ANYTHING. Arm at `min_tier=1` and the informational
backlog -- 542 replies, 388 chats, 243 notes, none of them addressed asks -- cannot fire the
watcher, while an operator message or a directed ask still fires it instantly. The backlog stays
exactly where it is, unread and intact, for whoever actually reads it.

RELATIONSHIP TO wake_worthy(). This module does NOT replace or fork it. `wake_worthy()` remains
the sole wake GATE (the allowlist ratchet, the incarnation addressing, the operator override,
the echo rules). A tier is a second, independent question asked only of mail that already
passed that gate: not "does this wake a seat" but "how much does this outrank other mail".
Forking the gate would be the exact drift this house keeps paying for -- one meaning under two
implementations that diverge quietly.

STRANGLER DISCIPLINE. The default floor is AMBIENT (3), which admits everything `wake_worthy()`
already admits, so importing this module changes no behaviour anywhere. Tiering is opt-in per
arm.
"""
from __future__ import annotations

from typing import Any, Optional

# ---------------------------------------------------------------- the ladder
OPERATOR = 0      # the human. Never queues behind fleet traffic, never starved.
DIRECTED_ASK = 1  # an ask addressed to ME and awaiting my answer.
SETTLEMENT = 2    # an answer to something I asked -- closes my own open loop.
AMBIENT = 3       # everything else. Visible, never urgent.

NAMES = {OPERATOR: "operator", DIRECTED_ASK: "directed-ask",
         SETTLEMENT: "settlement", AMBIENT: "ambient"}

# Kinds that ASK something of the recipient (they open an obligation).
ASK_KINDS = frozenset({"request", "handoff", "question", "blocker"})
# Kinds that ANSWER something (they close one). Mirrors expectations.ANSWER_KINDS,
# which is the settlement vocabulary -- kept as a separate name because this module
# asks a priority question, not a settlement question, and merging them would make a
# later change to one silently retarget the other.
ANSWER_KINDS = frozenset({"reply", "completion"})


def _s(m: Any, attr: str) -> str:
    return str(getattr(m, attr, "") or "")


def wake_tier(m: Any, *, agent: str, incarnation: str = "",
              operator_ids: Optional[frozenset] = None) -> int:
    """How much does this message outrank other mail for THIS seat? Lower is louder.

    Deliberately total: every message resolves to a tier, and the unlisted case is
    AMBIENT rather than an error or a silent False. An unclassified kind loses priority;
    it never loses visibility.
    """
    meta = getattr(m, "meta", None) or {}

    # Explicit incarnation addressing is the sender naming THIS session on purpose.
    # wake_worthy() already treats it as outranking everything; a tier that disagreed
    # would be a second opinion on a settled question.
    target = str(meta.get("to_incarnation") or "")
    me = str(incarnation or "")
    if target and len(target) >= 8 and me and (me == target or me.startswith(target)):
        return OPERATOR

    kind, frm, to = _s(m, "kind"), _s(m, "frm"), _s(m, "to")

    # TIER 0 -- the operator, with the SAME carve-out wake_worthy() applies, quoted from
    # its own comment so the two cannot drift apart: an UNDIRECTED chat broadcast
    # (to="*", kind=chat) is the read-only lounge Daniil asked for on 2026-08-31 -- "a
    # space to talk to everyone without having to worry about waking everyone at once" --
    # and is ambient by his own ruling. A DIRECTED operator message is never ambient.
    if operator_ids and frm in operator_ids:
        if not (kind == "chat" and to == "*"):
            return OPERATOR

    # Broadcasts are visibility, never directed ownership. A broadcast cannot open an
    # obligation on one seat, so it can never be tier 1 or 2, whatever its kind.
    directed_to_me = bool(to) and to != "*" and to == agent
    if not directed_to_me:
        return AMBIENT

    if kind in ASK_KINDS:
        return DIRECTED_ASK
    if kind in ANSWER_KINDS:
        return SETTLEMENT
    return AMBIENT


def tier_name(tier: int) -> str:
    return NAMES.get(tier, "ambient")


def admits(tier: int, floor: int) -> bool:
    """Does a watcher armed at `floor` wake for a message of this `tier`?"""
    return tier <= floor
