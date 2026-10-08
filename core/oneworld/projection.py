"""W0.1 -- the projection reader over the one-world journal.

Spec: atom art_20261008_one-world-ui-core-reconciled-spec_d622ac (H9), section 1. This is the second
half of the spine: the journal (W0) holds the authored truth; a PROJECTION is a derived surface
state folded from it, and it holds no state of its own. One journal -> N projections, each a pure
fold with its own reducer.

THE DRIFT-FREEDOM CLAIM, and why this module is small on purpose. A projection is rebuilt from the
journal on every call. It therefore cannot drift: there is no in-place surface state to fall out of
sync, and "if a surface drifts, replay it" is not a remedy bolted on afterward but the only way this
module ever produces a value. The one thing that could still drift -- a live surface double-counting
a crash-redelivered event -- is closed one layer down by the journal's content-hash idempotency
(a redelivered fact is the same line), so a projection folded over the journal counts it once. The
pin test_redelivered_fact_counts_once_not_twice is that guarantee made executable.

A projection carries `taken`/`unparsed` straight through from replay(), so a surface built over a
journal with corrupt lines knows it (the seed of the W1 bounds legend -- this slice does not build
the legend primitive, it just refuses to hide the number).

A reducer is `(state, fact) -> state` and MUST be pure (no shared mutation, no wall-clock, no order
dependence beyond the authored order it is handed). An impure reducer reintroduces the drift this
module exists to remove; latest_by and count_by below are the two pure starters every early surface
needs, and a surface supplies its own when it needs more.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from core.oneworld import journal

Reducer = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


def project(reducer: Reducer, initial: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fold the authored journal through `reducer` into a derived surface state.

    Returns {"state": <folded>, "taken": N, "unparsed": M}. The state is rebuilt from the journal
    every call -- this function holds nothing between calls, which is what makes the projection
    drift-free. `taken`/`unparsed` ride through from replay() so the surface never loses the
    found-vs-taken honesty the journal computed.
    """
    r = journal.replay()
    state: Dict[str, Any] = {} if initial is None else dict(initial)
    for fact in r["facts"]:
        state = reducer(state, fact)
    return {
        "state": state, "taken": r["taken"], "unparsed": r["unparsed"],
        # W1: the bounds legend is emitted BY CONSTRUCTION. There is no code path that returns a
        # projection without it, so a surface literally cannot render one without a declared
        # boundary. A reducer that knows surface-specific gaps passes them via a wrapping call to
        # bounds_legend; the journal-level found-vs-taken is always here.
        "legend": bounds_legend(r["taken"], r["unparsed"]),
    }


def latest_by(key_fn: Callable[[Dict[str, Any]], Any]) -> Reducer:
    """Reducer factory: keep the LATEST fact per key_fn(fact). The 'current state' projection --
    the most common surface shape (current mode per surface, latest value per channel). Authored
    order decides 'latest', and replay() preserves it, so the last-appended fact for a key wins."""
    def reducer(state: Dict[str, Any], fact: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(state)
        out[key_fn(fact)] = fact
        return out
    return reducer


def count_by(key_fn: Callable[[Dict[str, Any]], Any]) -> Reducer:
    """Reducer factory: count facts per key_fn(fact). Because it folds the DEDUPED journal, a
    redelivered fact is counted once -- the drift a live counter would suffer, closed by the
    journal's idempotency rather than by a de-dup the surface has to remember to do."""
    def reducer(state: Dict[str, Any], fact: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(state)
        k = key_fn(fact)
        out[k] = out.get(k, 0) + 1
        return out
    return reducer


# --- W1: the bounds legend -- the spec's anti-drift law made a reusable piece. "A surface declares
# its boundary before it issues a verdict about the whole." It lives here (not its own module) until
# a second consumer -- the floor, the mode schema -- reuses it; rule of three, then extract. ---

def bounds_legend(taken: int, unparsed: int, gaps: Optional[list] = None) -> str:
    """One line a human reads: what this surface could NOT see. The journal-level found-vs-taken
    (unparsed lines) is always folded in; `gaps` carries surface-specific unresolved things (a
    dangling reference, a window that rotated away). 'complete' is said ONLY when nothing was
    dropped and no gap was named -- silence never masquerades as completeness."""
    parts = []
    if unparsed:
        parts.append(f"{unparsed} journal line(s) unparsed and skipped")
    parts.extend(str(g) for g in (gaps or []) if str(g).strip())
    if not parts:
        return f"complete: {taken} fact(s) read, nothing dropped"
    return f"{taken} fact(s) read; could not see: " + "; ".join(parts)


def require_bounds(result: Dict[str, Any]) -> str:
    """The render-boundary guard a surface calls before it draws. A projection-shaped dict with no
    non-empty legend is REFUSED: you may not issue a verdict about the whole without declaring your
    boundary. Returns the legend so the call site renders it."""
    legend = result.get("legend") if isinstance(result, dict) else None
    if not isinstance(legend, str) or not legend.strip():
        raise ValueError(
            "a surface must declare its bounds (a non-empty legend) before it renders a verdict "
            "about the whole -- this projection has none")
    return legend
