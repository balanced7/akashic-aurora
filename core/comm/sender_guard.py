"""Is this string a seat id, or is it somebody's message wearing the sender slot?

Born 2026-09-04 from an hour of the operator's silence. Three replies to him went out as
`bifrost-send --to daniil --kind chat "<long text>" claude` -- text before sender, so
argparse bound the MESSAGE to agent_id and the word "claude" to text. Discord refused each
one with HTTP 400 (a webhook username cannot be a thousand characters), the operator saw
nothing, and the seat spent the hour diagnosing a pump defect that did not exist.

WHY THIS IS CODE AND NOT A THIRD LESSON. Two lessons already covered it --
`bifrost_send_variadic_text_requires_options_before_sender` (30 days old) and the
unconditional `bifrost_send_always_text_file` (48 days old). Recall SURFACED BOTH at the
moment of the mistake and they were violated anyway. That is a reading failure, and the
`repeat` verb's own verdict on a short gap is the design brief: prose is the wrong
instrument, a gate is the right one. Per the operator's principle -- the answer to a boulder
is not more hammers -- a rule that a seat must REMEMBER is a future incident with a delay
fuse; the mechanical form is a refusal at the door.

The rule: an agent id is a SLUG. Letters, digits, hyphen, underscore, dot. No whitespace,
no sentence punctuation, and never empty. Deliberately NOT a length police: self-registered
seats legitimately look like `codex_frontier_019f6e7e`, so shape decides, not size.
"""
from __future__ import annotations

import re
from typing import Optional

#: What a seat id may contain. Anything else is prose, a path, or a shell accident.
_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def check_sender(agent_id: Optional[str]) -> Optional[str]:
    """None when `agent_id` is a plausible seat id; else the refusal to print.

    Returns DATA, never raises: every caller is a door that must print one honest line and
    exit non-zero, not hand the operator a traceback."""
    if agent_id is None or not str(agent_id).strip():
        return ("refusing to send with an EMPTY sender -- the first positional argument is "
                "WHO IS SENDING (e.g. `claude`), not the message. Shape: "
                "bifrost-send --to <peer> --kind <kind> --text-file <path> <sender>")
    raw = str(agent_id)
    if _ID_RE.match(raw):
        return None
    # The overwhelmingly common cause, and the one that cost the hour: the body landed here.
    looks_like_prose = (" " in raw) or len(raw) > 64
    head = raw.strip().replace("\n", " ")[:60]
    if looks_like_prose:
        return (f"refusing to send: the sender slot holds what looks like a MESSAGE, not a "
                f"seat id -- it starts {head!r} ({len(raw)} chars).\n"
                f"This is the argv-ordering trap: options, then SENDER, then text --\n"
                f"  bifrost-send --to <peer> --kind chat --text-file <path> <sender>\n"
                f"Put every real body in --text-file (house rule, unconditional): a long or "
                f"flag-bearing message in argv misparses, and a message in the sender slot "
                f"is posted as a webhook USERNAME, which Discord rejects with HTTP 400 -- "
                f"silently, from the operator's side.")
    return (f"refusing to send: {head!r} is not a valid seat id (letters, digits, dot, "
            f"hyphen, underscore; no whitespace). The first positional is the SENDER.")
