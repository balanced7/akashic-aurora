"""T176 s1 -- the kind registry: total resolution, so a miss stops reading as a decision.

THE DEFECT THIS CLOSES. Every kind policy in this house is a membership test against a
hand-maintained set: `if kind in WAKE_WORTHY_KINDS`. A membership test has two answers and
the situation has three. When a kind is absent from the set, `in` returns False -- and False
is indistinguishable from a deliberate exclusion. So a kind nobody thought about is silently
not-wake-worthy, not-salient, not-an-answer, and no one is ever told. Census at filing: 31
kinds, 14 sets across 11 files, 17 of 31 kinds appearing in one set or fewer. Confirmed
casualty: bifrost_review_kind_is_silent_2026_07_29, and the standing lesson
open_vocabulary_plus_subset_policy_makes_new_kinds_born_silent says it in its title.

THE SAME LAW THE HOUSE ALREADY ENFORCES, one plane over:
    BoundaryOutcome (T170)  a boundary that fails without saying why is unrepresentable
    R14 pointer honesty     an evicted payload confesses; never renders as "no event"
    coverage frame          a count without its scope is not a coverage claim
    THIS                    an unlisted kind resolves UNCLASSIFIED, never a silent False

WHY THE VOCABULARY STAYS OPEN. A fenced adversarial pass (recorded on the T176 row) rejected
closing it: a closed vocabulary makes one registry the bottleneck for every new message type
and kills extensibility between independently developed agents. So kinds are never rejected
for being unknown -- they are RESOLVED as unknown, counted, and surfaced.

WHY REGISTRATION IS SPARSE AND PER-DIMENSION. The 14-set design has one real virtue:
orthogonality. `nudge` is wake-worthy and NOT salient, and those two facts are independently
maintained. A single "kind table" with a row of booleans would look tidier and would couple
every dimension to every other. Each dimension keeps its own membership; a kind declares
only the dimensions it participates in.

WHAT s1 DOES NOT DO. It does not rewire the 14 call sites. The sets below are SEEDED FROM
those live sets, so behaviour today is byte-identical and P3 pins that. Rewiring is s2, by
strangler fig, one door at a time with parity pins (the T044/T045 dual-write precedent).

AND IT PROPOSES, NEVER RATIFIES. Seeding surfaced a real fork -- `ask` is three sets that
disagree about `blocker`. This module reports that in forks(); it does not pick a winner,
because picking one is a policy ruling and rulings belong to the operator.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Set

# --------------------------------------------------------------------------- the verdict


@dataclass(frozen=True)
class KindVerdict:
    """What the taxonomy can say about (kind, dimension). Three states, never two.

    classified=True  + value=True/False  -- a real policy answer, the kind is known here
    classified=False + value=None        -- UNCLASSIFIED; `why` says which half was missing

    `value` is None (not False) when unclassified ON PURPOSE: the whole defect is that False
    and unknown were the same byte. A caller that does `if verdict.value:` gets falsy either
    way; a caller that does `if verdict.classified:` gets the truth. The type makes the
    honest read available -- it cannot make it mandatory, which is why s2 rewires call sites
    deliberately rather than by a global search-and-replace."""

    kind: str
    dimension: str
    classified: bool
    value: Optional[bool] = None
    why: str = ""

    def __post_init__(self) -> None:
        if not self.classified and not str(self.why).strip():
            raise ValueError("an UNCLASSIFIED verdict without a reason is the silence this "
                             "type exists to make unrepresentable")

    def __bool__(self) -> bool:  # pragma: no cover - guard, not behaviour
        raise TypeError(
            "KindVerdict is not a boolean -- that coercion IS the T176 defect. Read "
            ".classified first, then .value.")


# --------------------------------------------------------------------------- the registry
#
# Each entry: dimension -> {"members": the set, "universe": kinds this dimension has an
# opinion about, "source": where the live set lives}. `universe` is what separates "no, and
# we considered it" from "we never considered it" -- the distinction the organ is for. When
# universe is None the dimension's universe is the union of all known kinds.

_BUS_UNIVERSE: FrozenSet[str] = frozenset({
    # asks / answers
    "request", "question", "handoff", "blocker", "reply", "completion", "decision",
    # conversation
    "chat", "note", "inform", "hint", "status",
    # control
    "halt", "interrupt", "pause", "resume", "nudge", "steer",
    # telemetry / machine
    "trace", "thinking", "tool", "narration", "ledger_update", "resolved", "presence",
    "heartbeat", "review",
})

_DIMENSIONS: Dict[str, Dict[str, Any]] = {
    "wake_worthy": {
        "members": frozenset({"request", "handoff", "reply", "blocker", "question",
                              "completion", "nudge"}),
        "source": "scripts/bifrost_wake.py:WAKE_WORTHY_KINDS",
    },
    "wake_skip": {
        "members": frozenset({"trace", "steer", "resolved", "ledger_update"}),
        "source": "scripts/bifrost_wake.py:SKIP_KINDS",
    },
    "pending_skip": {
        "members": frozenset({"trace", "steer", "resolved", "ledger_update", "note",
                              "status"}),
        "source": "core/comm/bifrost_api.py:PENDING_SKIP_KINDS",
    },
    "answer": {
        "members": frozenset({"reply", "handoff", "completion"}),
        "source": "core/comm/expectations.py:ANSWER_KINDS",
    },
    "escalate": {
        "members": frozenset({"request", "handoff", "question", "blocker"}),
        "source": "core/comm/dispatcher.py:ESCALATE_KINDS",
    },
    "salient": {
        "members": frozenset({"handoff", "decision", "completion", "blocker"}),
        "source": "core/comm/promoter.py:SALIENT_KINDS",
    },
    "flaggable": {
        "members": frozenset({"handoff", "blocker"}),
        "source": "core/comm/promoter.py:FLAGGABLE_KINDS",
    },
    "long": {
        "members": frozenset({"handoff", "request", "question", "blocker"}),
        "source": "core/comm/mailbox.py:LONG_KINDS",
    },
    "trace": {
        "members": frozenset({"trace", "steer", "nudge", "ledger_update", "resolved"}),
        "source": "agent/bifrost_pull.py:_TRACE_KINDS",
    },
    "non_cargo": {
        "members": frozenset({"trace", "halt", "interrupt", "pause", "resume", "nudge",
                              "steer", "ledger_update", "presence", "heartbeat"}),
        "source": "scripts/checkers/check_bus_atom_pointers.py:NON_CARGO_KINDS",
    },
}

# FORKED CONCEPTS -- registered as variants, never merged. The registry's job here is to make
# the disagreement impossible to miss; choosing a winner is the operator's ruling.
_FORKS: Dict[str, List[Dict[str, Any]]] = {
    "ask": [
        {"source": "agent/bifrost_pull.py:_ASK_KINDS",
         "members": frozenset({"request", "question", "handoff", "blocker"})},
        {"source": "agent_cli.py:ASK_KINDS",
         "members": frozenset({"request", "handoff", "question"})},
        {"source": "core/comm/packet_spec.py:STALE_ASK_KINDS",
         "members": frozenset({"question", "request", "handoff"})},
    ],
}

# The three planes that all say "kind" and mean different taxonomies. `note` is a member of
# all three WITH OPPOSITE POLICIES, which is the collision the T176 row names.
_PLANES: Dict[str, FrozenSet[str]] = {
    "bus_kind": _BUS_UNIVERSE,
    "event_kind": frozenset({"tool_call", "file_edit", "command", "observation", "message",
                             "note"}),
    "beat_kind": frozenset({"session", "note", "commit", "learning", "decision",
                            "milestone", "mark"}),
}


# --------------------------------------------------------------------------- resolution


def dimensions() -> List[str]:
    return sorted(_DIMENSIONS)


def members(dimension: str) -> Set[str]:
    """The live membership of one dimension, as a plain set (parity surface for P3)."""
    d = _DIMENSIONS.get(dimension)
    if d is None:
        raise KeyError(f"unknown dimension {dimension!r} -- known: {dimensions()}")
    return set(d["members"])


def universe(dimension: str) -> Set[str]:
    d = _DIMENSIONS.get(dimension)
    if d is None:
        raise KeyError(f"unknown dimension {dimension!r}")
    u = d.get("universe")
    return set(u) if u else set(_BUS_UNIVERSE)


def resolve(kind: str, dimension: str) -> KindVerdict:
    """TOTAL resolution. Three answers, never two.

    A kind IN the dimension's universe but NOT in its members is a real, considered NO.
    A kind outside the universe is UNCLASSIFIED -- nobody ever decided, and the caller is
    told so rather than handed a False that looks like a decision."""
    d = _DIMENSIONS.get(dimension)
    if d is None:
        return KindVerdict(kind, dimension, False, None,
                           f"unknown dimension {dimension!r} (known: {dimensions()})")
    uni = universe(dimension)
    if kind in d["members"]:
        return KindVerdict(kind, dimension, True, True)
    if kind in uni:
        return KindVerdict(kind, dimension, True, False)
    return KindVerdict(
        kind, dimension, False, None,
        f"kind {kind!r} is not in the {dimension!r} universe -- nobody has decided this "
        f"kind's policy here; registered at {d['source']}")


def planes() -> Dict[str, Set[str]]:
    return {name: set(v) for name, v in _PLANES.items()}


def plane_collisions() -> Dict[str, List[str]]:
    """Kinds that exist on more than one plane. `note` is the load-bearing case: a bus note
    is skipped from pending, an event note is a captured record, a beat note is narrative --
    three policies, one word, and no duplicate identifier anywhere to grep for."""
    seen: Dict[str, List[str]] = {}
    for plane, ks in _PLANES.items():
        for k in ks:
            seen.setdefault(k, []).append(plane)
    return {k: sorted(v) for k, v in seen.items() if len(v) > 1}


def forks() -> Dict[str, Dict[str, Any]]:
    """Concepts registered more than once with DIFFERENT memberships. Reported, never
    merged: a fork is a question for the operator, and this organ proposes."""
    out: Dict[str, Dict[str, Any]] = {}
    for concept, variants in _FORKS.items():
        sets = [v["members"] for v in variants]
        union: Set[str] = set().union(*sets)
        intersection: Set[str] = set(sets[0]).intersection(*sets[1:])
        differs = sorted(union - intersection)
        if not differs:
            continue
        out[concept] = {
            "variants": [{"source": v["source"], "members": sorted(v["members"])}
                         for v in variants],
            "differs_on": differs,
            "why_it_matters": ("one concept, several memberships, no duplicate token -- "
                               "token- and AST-level checkers are structurally blind to "
                               "this class (W134)"),
        }
    return out


def coverage() -> Dict[str, Any]:
    """The frame that must ship with the number: per-dimension membership, the universe it
    was decided against, and where each live set actually lives."""
    dims = {}
    for name, d in _DIMENSIONS.items():
        uni = universe(name)
        dims[name] = {
            "members": len(d["members"]),
            "universe": len(uni),
            "undecided": sorted(uni - set(d["members"])),
            "source": d["source"],
        }
    return {
        "dimensions": dims,
        "kinds_total": len(_BUS_UNIVERSE),
        "planes": {p: len(v) for p, v in _PLANES.items()},
        "plane_collisions": plane_collisions(),
        "forks": forks(),
        "sources": sorted(d["source"] for d in _DIMENSIONS.values()),
        "scope": ("s1 seeds from the live sets and rewires nothing; call sites still use "
                  "their own constants until s2"),
    }
