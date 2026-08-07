"""compare -- the cross-domain set difference, with a name (T213).

Daniil, 2026-08-07: "at work I find a lot of value by seeing what one system has and the
other doesn't, cross matching account numbers, ip's, design documents, logs, timestamps."

HE NAMED THE SHAPE THAT WAS ALREADY OUR BEST GUARD FAMILY. Four of the instruments this
repo trusts most are one operation, each hand-built as a separate module:

    check_door_parity      CLI verbs      MINUS  MCP verbs  MINUS  ToolBox verbs
    check_wiring           tracked files  MINUS  reachable files
    suite_baseline.delta   baseline fails MINUS  current fails
    T122                   declared kinds MINUS kinds actually sent

A lens only SHOWS you something; a set difference FINDS it. This is that operation named
once, so the fifth instance costs a line instead of a module.

A SET DECLARES WHAT ITS ELEMENTS ARE. Comparing verb names against file paths produces a
large, confident, meaningless difference -- worse than an error, because it looks like a
finding. So every KeySet carries a key_type and diff() REFUSES a mismatch rather than
coercing: Principle 5 ("one vocabulary, names must not lie") applied to sets.

COVERAGE IS THE WHOLE BALLGAME. A MINUS B is only as true as the coverage of BOTH sides:
where B was partly collected, every uncollected element of B surfaces as a finding in A.
That is not hypothetical -- T208 shipped it and caught it four minutes later, when a
three-file test run reported ten baseline failures as "fixed" because they had merely not
been run, and "fixed" invites a re-record that would have deleted them. So a difference
against an incomplete side is UNRELIABLE and says so, and two empty sides prove nothing at
all.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _norm_verb(k: str) -> str:
    """`bifrost-send` and `bifrost_send` are ONE verb wearing two spellings -- the CLI
    hyphenates, the MCP door underscores. Caught on this module's first live run, where
    the raw difference reported each as missing from the other side, twice.

    This is the classic cross-matching problem Daniil named from his own work: the same
    entity formatted differently per system. Without a per-type normalizer, a difference
    between two systems measures their FORMATTING as much as their contents.
    """
    return str(k).strip().lower().replace("-", "_")


def _norm_path(k: str) -> str:
    return str(k).strip().replace("\\", "/").lstrip("./")


#: key_type -> how to compare two of them. A type with no normalizer compares literally,
#: which is a decision the type is making rather than an omission.
NORMALIZERS: Dict[str, Callable[[str], str]] = {
    "verb": _norm_verb, "path": _norm_path,
}


@dataclass
class KeySet:
    """A set of comparable keys, plus what it knows about its own completeness.

    `complete` is the load-bearing field: a KeySet that could not fully collect must not
    let a downstream difference read as a discovery.
    """
    name: str
    key_type: str
    keys: Set[str] = field(default_factory=set)
    complete: bool = True
    failed: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if self.failed:
            # A source that errored did not collect everything, whatever it returned.
            self.complete = False

    def view(self) -> Dict[str, Any]:
        return {"name": self.name, "key_type": self.key_type, "n": len(self.keys),
                "complete": self.complete, "failed": dict(self.failed)}


def diff(a: KeySet, b: KeySet) -> Dict[str, Any]:
    """A MINUS B, B MINUS A, and the intersection -- with both sides' provenance.

    Both directions are reported separately because they are DIFFERENT findings: "in the
    CLI but not on MCP" is tracked debt, while "on MCP but not in the CLI" is a rogue
    door. Collapsing them into one count loses the diagnosis.
    """
    base = {"a": a.view(), "b": b.view(), "key_type": a.key_type,
            "only_a": [], "only_b": [], "both": [], "identical": False}

    if a.key_type != b.key_type:
        return {**base, "ok": False, "reliable": False,
                "why": (f"refusing to compare '{a.name}' ({a.key_type}) with '{b.name}' "
                        f"({b.key_type}) -- different kinds of key, so any difference "
                        f"would be large, confident and meaningless")}

    # Normalize per key TYPE before differencing, or the result measures the two systems'
    # formatting as much as their contents. Originals are kept so a finding is reported
    # in the spelling its own system uses.
    nrm = NORMALIZERS.get(a.key_type, lambda k: str(k))
    a_map: Dict[str, str] = {}
    b_map: Dict[str, str] = {}
    for k in a.keys:
        a_map.setdefault(nrm(k), k)
    for k in b.keys:
        b_map.setdefault(nrm(k), k)

    only_a = sorted(a_map[n] for n in (set(a_map) - set(b_map)))
    only_b = sorted(b_map[n] for n in (set(b_map) - set(a_map)))
    both = sorted(a_map[n] for n in (set(a_map) & set(b_map)))
    identical = not only_a and not only_b

    reasons: List[str] = []
    if not a.complete:
        reasons.append(f"'{a.name}' is incomplete")
    if not b.complete:
        reasons.append(f"'{b.name}' is incomplete")
    if not a.keys and not b.keys:
        # 0 minus 0 = 0 is arithmetically true and diagnostically empty. Reporting it as
        # "no debt" when both collectors returned nothing is the confident-zero lie.
        reasons.append("both sides are EMPTY -- that proves nothing about the world, "
                       "only that nothing was collected")

    return {**base, "ok": True, "only_a": only_a, "only_b": only_b, "both": both,
            "identical": identical, "reliable": not reasons,
            "why": ("; ".join(reasons) + " -- every uncollected element of the incomplete "
                    "side surfaces as a false finding on the other" if reasons else "")}


# ----------------------------------------------------------------- domain collectors
def _verbs_cli(**_) -> Set[str]:
    from agent_cli import list_verbs
    return {n for n, _h in list_verbs(None)}


def _verbs_mcp(**_) -> Set[str]:
    import ast
    with open(os.path.join(_ROOT, "ai_setup_mcp.py"), encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                fn = dec.func if isinstance(dec, ast.Call) else dec
                if isinstance(fn, ast.Attribute) and fn.attr == "tool":
                    out.add(node.name)
    return out


def _files_tracked(**_) -> Set[str]:
    r = subprocess.run(["git", "ls-files"], cwd=_ROOT, capture_output=True, text=True,
                       timeout=60, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "git ls-files failed").strip()[:200])
    return {ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()}


def _files_touched(since: Optional[float] = None, **_) -> Set[str]:
    from core.coord.timeline import _file_rows
    return {r["summary"] for r in _file_rows(since=since)}


def _lessons_all(**_) -> Set[str]:
    from core.learning.store import get_learning_store_instance
    store = get_learning_store_instance()
    return {str(getattr(x, "experiment_name", None) or x.get("experiment_name", ""))
            for x in (store.list_experiments() if hasattr(store, "list_experiments")
                      else [])} - {""}


#: name -> (collector, key_type). The key_type is what makes a comparison legal; two
#: domains may only be diffed when they speak about the same kind of thing.
DOMAINS: Dict[str, Tuple[Callable, str]] = {
    "verbs:cli": (_verbs_cli, "verb"),
    "verbs:mcp": (_verbs_mcp, "verb"),
    "files:tracked": (_files_tracked, "path"),
    "files:touched": (_files_touched, "path"),
    "lessons:all": (_lessons_all, "lesson"),
}


def select(domain: str, **kw) -> KeySet:
    """Collect one domain into a KeySet. Never raises: a failed collection returns an
    INCOMPLETE set that names its failure, so a downstream difference is marked
    unreliable rather than silently reading an outage as absence."""
    entry = DOMAINS.get(domain)
    if entry is None:
        return KeySet(name=domain, key_type="?", keys=set(),
                      failed={"unknown-domain": f"no collector registered for "
                                                f"'{domain}' (have: "
                                                f"{', '.join(sorted(DOMAINS))})"})
    fn, key_type = entry
    try:
        return KeySet(name=domain, key_type=key_type, keys=set(fn(**kw) or set()))
    except Exception as e:
        return KeySet(name=domain, key_type=key_type, keys=set(),
                      failed={"collect": f"{e.__class__.__name__}: {e}"})


def run(a_domain: str, b_domain: str, **kw) -> Dict[str, Any]:
    """select + select + diff, the ordinary path."""
    return diff(select(a_domain, **kw), select(b_domain, **kw))
