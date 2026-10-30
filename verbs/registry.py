"""registry -- the ONE introspectable verb table, and the strangler rail that lets verbs move.

WHY A REGISTRY AND NOT "the parser is the registry"
---------------------------------------------------
It already was, implicitly: `list_verbs()` walked the live argparse subparsers and every consumer
that needed the verb table rebuilt it from that walk. The out-of-tree position's attack C
(2026-09-17) named the cost of extracting verb bodies without fixing that first:

    "Verb bodies are read not only by dispatch but by the door-parity checker, the advertised-verb
    checker, and the MCP twin surface. Extracting bodies must keep ONE introspectable registry
    that those checkers read, or we trade file collisions for checker blindness -- a worse trade,
    because collisions are loud and blind checkers are silent."

So this module publishes exactly one table, and every consumer reads it:

  * `build_parser()` fills it (`publish(parser)`) as its LAST act, so the table can never be
    stale against the parser that dispatches -- they are the same build, not two sources.
  * `list_verbs()` is the compat contract (`core/coord/{capability_search,compare}.py` and
    `tests/test_door.py` import it from `agent_cli`) and reads this table, not the parser.
  * checkers, the MCP twin and the door all ask here.

THE MIGRATION RAIL (the W169 mechanism, generalised)
----------------------------------------------------
`build_parser` KEEPS its argparse structure and its `set_defaults(fn=...)` bindings. A verb that
has moved out of `agent_cli.py` binds a function imported from `verbs._legacy`, which re-exports
it under its original `cmd_*` name. The CLI surface -- every spelling, every flag, every help
string -- is untouched, so the surface cannot drift while the bodies move. One `git revert` walks
it all back because the old bodies are only deleted as their replacement is proven.

THE `local` FLAG, and why it is declared rather than guessed
-----------------------------------------------------------
The design asks each spec to say whether the verb touches the Local layer (seats, instance paths,
ports, peer names) -- the thing a fork must adapt. It is DECLARED by the author (`@verb(local=...)`)
because a guess would be a measurement of the wrong thing: whether a body happens to contain a
seat-shaped string today is the purity gate's question (`scripts/checkers/check_core_purity.py`),
not this table's. `local=None` means "not declared", which is honest and visible;
`local_report()` re-measures the moved verbs against the gate's own patterns so a declaration that
has drifted from the code is something a reviewer can find.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = ["VerbSpec", "REGISTRY", "RegistryError", "verb", "publish", "list_verbs", "get_spec",
           "require_spec", "resolve", "names", "moved", "local_report", "declarations"]


class RegistryError(RuntimeError):
    """The table cannot answer -- e.g. it was never published. Raised, never returned empty."""


@dataclass(frozen=True)
class VerbSpec:
    """One row of the verb table.

    name        the CLI spelling (`knowledge-map`), i.e. what a human types.
    fn          the callable `build_parser` binds via `set_defaults(fn=...)`. None is honest and
                expected for a verb whose dispatch lives in NESTED subparsers (their own rows in
                `sa.choices` carry the fn); it never means "broken".
    help        the one-line purpose, exactly as the door advertises it.
    local       True if the verb reads or writes the Local layer; False if it is pure Core; None
                if nobody has declared it yet.
    door_notes  where else this verb surfaces (MCP twin, toolbox, hooks) -- a note for reviewers,
                not a live table.
    module      the module the body lives in, so `agent_cli`'s own verbs are visibly distinct from
                the extracted ones. This is the strangler's progress bar.
    """

    name: str
    fn: Optional[Callable[..., Any]] = None
    help: str = ""
    local: Optional[bool] = None
    door_notes: str = ""
    module: str = ""

    @property
    def moved(self) -> bool:
        """True when the body has left agent_cli.py (it lives under verbs/)."""
        return self.module.startswith("verbs.")

    def as_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "help": self.help, "local": self.local,
                "door_notes": self.door_notes, "module": self.module, "moved": self.moved,
                "fn": getattr(self.fn, "__name__", None)}


REGISTRY: Dict[str, VerbSpec] = {}

# fn -> declaration. Keyed by the FUNCTION, not the verb name, because one body can serve several
# CLI spellings (college's six sub-actions) and duplicating the spelling here would be a second
# place for it to drift from the parser.
_DECLARATIONS: Dict[Callable[..., Any], Dict[str, Any]] = {}

_PUBLISHED_FROM: Optional[int] = None      # id() of the parser most recently published


def verb(*, local: Optional[bool] = None, door_notes: str = "") -> Callable[[Callable], Callable]:
    """Declare a moved verb's spec metadata on the function itself.

        @verb(local=False, door_notes="MCP twin: knowledge_map")
        def cmd_knowledge_map(args): ...

    The decorator returns the function UNCHANGED, so nothing about dispatch, identity or
    `set_defaults(fn=...)` is affected -- `parsed.fn is agent_cli.cmd_knowledge_map` keeps holding.
    """

    def _wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        _DECLARATIONS[fn] = {"local": local, "door_notes": door_notes}
        return fn

    return _wrap


def declarations() -> Dict[str, Dict[str, Any]]:
    """The declarations, by function name (for reviews and tests)."""
    return {getattr(fn, "__name__", repr(fn)): dict(meta)
            for fn, meta in _DECLARATIONS.items()}


def _subparsers_action(parser):
    import argparse
    return next((a for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)


def publish(parser) -> Dict[str, VerbSpec]:
    """Fill REGISTRY from a BUILT parser. Called by `build_parser` as its last act.

    Every verb the door knows lands here -- moved or not -- because the rows come from the parser,
    which is the thing that actually dispatches. Extraction therefore cannot make a verb vanish
    from a consumer's view: it changes `spec.module`, and nothing else.
    """
    global _PUBLISHED_FROM
    sa = _subparsers_action(parser)
    if sa is None:
        raise RegistryError("publish() got a parser with no subcommands -- refusing to publish an "
                            "empty table, because an empty table reads as 'this door has no verbs'")
    rows = []
    for ca in sa._choices_actions:
        name = ca.dest
        sub = sa.choices.get(name)
        try:
            fn = sub.get_default("fn") if sub is not None else None
        except Exception:                                          # pragma: no cover
            fn = None
        declared = _DECLARATIONS.get(fn, {}) if callable(fn) else {}
        rows.append(VerbSpec(
            name=name,
            fn=fn,
            help=(ca.help or "").strip(),
            local=declared.get("local"),
            door_notes=declared.get("door_notes", ""),
            module=(getattr(fn, "__module__", "") or "") if callable(fn) else "",
        ))
    REGISTRY.clear()                              # in place: holders keep a live view
    REGISTRY.update({row.name: row for row in rows})
    _PUBLISHED_FROM = id(parser)
    return REGISTRY


def _require_published() -> None:
    if not REGISTRY:
        raise RegistryError(
            "the verb registry is empty, so it has never been published. The table is filled by "
            "build_parser(); a consumer that reads it before any parser exists would otherwise see "
            "'this door has no verbs' -- a silent blindness, not an empty door. Call "
            "agent_cli.build_parser() (or agent_cli.list_verbs()) first.")


def names() -> List[str]:
    _require_published()
    return list(REGISTRY)


def list_verbs(query: Optional[str] = "") -> List[Tuple[str, str]]:
    """[(verb, purpose)] -- the compat contract's exact shape, in parser order.

    Deliberately identical in behaviour to the function it replaces inside agent_cli: no filtering
    of silent verbs (the door test asserts there are none), substring filter over name+purpose, and
    parser order preserved so anything that diffs two runs still sees a deterministic list.
    """
    _require_published()
    rows = [(spec.name, spec.help) for spec in REGISTRY.values()]
    q = (query or "").strip().lower()
    if q:
        rows = [(n, h) for n, h in rows if q in n.lower() or q in h.lower()]
    return rows


def get_spec(name: str) -> Optional[VerbSpec]:
    """The row for one verb, or None. Never raises on an unknown name -- use require_spec to."""
    return REGISTRY.get(name)


def require_spec(name: str) -> VerbSpec:
    _require_published()
    try:
        return REGISTRY[name]
    except KeyError:
        raise RegistryError(f"no verb named {name!r}; {len(REGISTRY)} are registered") from None


def resolve(name: str) -> Optional[Callable[..., Any]]:
    """The callable the door would run for this verb (None when dispatch is nested)."""
    spec = require_spec(name)
    return spec.fn


def moved() -> List[VerbSpec]:
    """The verbs whose bodies have left agent_cli.py -- the extraction's own progress bar."""
    _require_published()
    return [s for s in REGISTRY.values() if s.moved]


def local_report() -> List[Dict[str, Any]]:
    """Measured Local-in-Core literals in each MOVED verb's source, beside its declaration.

    The audit that keeps the `local` flag honest. Imports the purity gate's patterns lazily and
    fails soft: if the checker is not importable this returns a single row explaining that, rather
    than an empty list that would read as "nothing to see".
    """
    try:
        import os
        import sys
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from scripts.checkers.check_core_purity import count_text, total_of
    except Exception as exc:                                       # noqa: BLE001
        return [{"error": f"cannot measure (purity checker not importable: {type(exc).__name__})"}]
    out = []
    for spec in moved():
        if not callable(spec.fn):
            continue
        try:
            src = inspect.getsource(spec.fn)
        except (OSError, TypeError):
            src = ""
        counts = count_text(src)
        out.append({"name": spec.name, "declared_local": spec.local,
                    "measured": counts, "total": total_of(counts),
                    "module": spec.module})
    return sorted(out, key=lambda r: (-r.get("total", 0), r.get("name", "")))
