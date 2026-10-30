"""verbs -- the door's verb bodies, out of the door.

`agent_cli.py` was 11,220 lines and 61% of it was verb bodies (phase-0 census, 2026-10-30). That
is not a style complaint: it is why a sync between two forks collided in 40 hunks over functions
nobody had both touched. The out-of-tree position's attack A (2026-09-17) reframed the detector
that matters --

    "if two forks must both edit the same FILE for their own reasons, that file is holding more
    than one layer -- split the file even when no single line is contested."

This package is that split, done as a STRANGLER: verbs move out one at a time, `agent_cli.py`
keeps its argparse structure, and for each moved verb it binds the imported function instead of
the local body, so the CLI surface (every spelling, every flag, every help string) cannot drift
while the bodies move.

Layout, per the phase-0 design:

    verbs/
      registry.py        the ONE introspectable table: REGISTRY, list_verbs, get_spec, publish
      _legacy.py         every moved verb, re-exported under its ORIGINAL cmd_* name
      groups/<cluster>/  the bodies, grouped by the dispatch-table cluster they serve -- a group
                         is a row of the CLI surface, not a file type

The import that matters for compatibility is `verbs._legacy`: `import agent_cli` must keep
resolving `agent_cli.cmd_<verb>` for the out-of-tree bridge, the hooks, the MCP twin and the
tests, and a move that broke a name would be a version-skew silence at exactly the seam this
detangle exists to make safe.
"""
from verbs.registry import (  # noqa: F401  (re-exported API)
    REGISTRY,
    RegistryError,
    VerbSpec,
    declarations,
    get_spec,
    list_verbs,
    local_report,
    moved,
    names,
    publish,
    require_spec,
    resolve,
    verb,
)

__all__ = [
    "REGISTRY", "RegistryError", "VerbSpec", "declarations", "get_spec", "list_verbs",
    "local_report", "moved", "names", "publish", "require_spec", "resolve", "verb",
]
