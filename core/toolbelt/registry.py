"""
Toolbelt registry (T099 · V0 self-tooling) -- agent-authored verb compositions.

Semantic Relationship: Toolbelt projects AgentVerbRegistry (durable JSON is truth)

The reconciled laws (docs/library/design/20260701_self-tooling-arc-reconciled-design-agent_29f578.md):
  SUGAR-ONLY   -- an alias is a SEQUENCE of existing agent_cli verbs (argv lists). Minting a
                  step whose verb the door doesn't know REFUSES loudly. Aliases execute only
                  via `run <agent> <name>`, so a real verb can never be shadowed.
  HONESTY      -- every entry carries evidence VERIFIED|INFER|GUESS (default GUESS: untested
                  sugar confesses it's untested) + tested_against (a pin id, or None).
  OBS/PROJ     -- the lesson-identity contract applies: re-mint same name with a changed
                  definition SUPERSEDES (version+1, prior retained in history); an exact
                  re-mint is a no-op; the JSON file is the durable source, the in-memory
                  object a projection (re-load = re-project).
  QUOTA        -- junk-drawer guard: per-agent active cap (default 20, env
                  AKASHIC_TOOLBELT_QUOTA); retire before minting past it.

Registry file: data/verb-registry/<agent>.json  (one file per agent; shared/ tier is V2).
Fail-open nowhere: this is an authoring surface, not an observability path -- errors raise.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, List, Optional

from core.foundation.timeutil import now_iso

EVIDENCE_LEVELS = ("VERIFIED", "INFER", "GUESS")
import re as _re
_SLOT = _re.compile(r"\$([1-9])")
DEFAULT_QUOTA = int(os.getenv("AKASHIC_TOOLBELT_QUOTA", "20"))


def default_root() -> str:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(here, "data", "verb-registry")


class Toolbelt:
    """One agent's authored-verb registry. Load-on-init (projection), save-on-write (truth)."""

    def __init__(self, agent: str, *, root: str = "", known_verbs: Optional[Callable[[], set]] = None,
                 quota: int = DEFAULT_QUOTA):
        self.agent = str(agent)
        self.root = root or default_root()
        self.quota = int(quota)
        self._known_verbs = known_verbs or _agent_cli_verbs
        self.path = os.path.join(self.root, f"{self.agent}.json")
        self._doc = self._load()

    # ---------------------------------------------------------------- persistence
    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {"agent": self.agent, "entries": {}, "history": []}
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _save(self) -> None:
        os.makedirs(self.root, exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._doc, f, indent=1, ensure_ascii=False)
        os.replace(tmp, self.path)          # atomic on the same volume

    # ---------------------------------------------------------------- authoring
    def mint(self, name: str, steps: List[List[str]], *, kind: str = "alias",
             evidence: str = "GUESS", tested_against: Optional[str] = None,
             why: str = "", family: str = "UNSORTED") -> Dict[str, Any]:
        """Create or supersede an authored verb. Sugar-only validated HERE, at mint time."""
        name = str(name).strip()
        if not name or " " in name:
            raise ValueError(f"bad alias name {name!r}")
        if evidence not in EVIDENCE_LEVELS:
            raise ValueError(f"evidence must be one of {EVIDENCE_LEVELS}")
        if not steps or not all(isinstance(s, list) and s for s in steps):
            raise ValueError("steps must be a non-empty list of argv lists")
        known = set(self._known_verbs())
        params = 0
        for s in steps:
            if str(s[0]) not in known:
                raise ValueError(f"unknown verb {s[0]!r} -- sugar-only: every step must be an "
                                 f"existing agent_cli verb (registry cannot mint capabilities)")
            for tok in s:                            # macro slots: $1..$9 (macro-expansion lineage)
                m = _SLOT.fullmatch(str(tok))
                if m:
                    params = max(params, int(m.group(1)))
        if params and kind == "alias":
            kind = "macro"                           # arity makes it a MACRO (expansion), not a combo
        entries = self._doc["entries"]
        prior = entries.get(name)
        if (prior and prior.get("status", "active") == "active" and prior["steps"] == steps
                and prior.get("evidence") == evidence
                and prior.get("tested_against") == tested_against
                and prior.get("family", "UNSORTED") == family
                and prior.get("kind", "alias") == kind):
            return prior     # exact re-mint = no-op. Evidence IS content (dogfood catch
                             # 2026-07-20), and so is FAMILY (the Halo-caste taxonomy):
                             # a label change supersedes, never silently no-ops.
        active = sum(1 for e in entries.values() if e.get("status", "active") == "active")
        if prior is None and active >= self.quota:
            raise ValueError(f"quota: {active}/{self.quota} active entries -- retire one first "
                             "(junk-drawer guard, T039 lineage)")
        version = (prior["version"] + 1) if prior else 1
        if prior:                                            # supersession: prior rides history
            self._doc["history"].append(dict(prior, superseded_at=_now()))
        entry = {"name": name, "kind": kind, "steps": steps, "version": version,
                 "params": params,
                 "evidence": evidence, "tested_against": tested_against, "why": why,
                 "family": family, "status": "active",
                 "created_at": prior["created_at"] if prior else _now(),
                 "updated_at": _now(), "author": self.agent}
        entries[name] = entry
        self._save()
        return entry

    def retire(self, name: str, reason: str = "") -> None:
        e = self._require(name)
        e["status"] = "retired"
        e["retired_reason"] = reason
        e["updated_at"] = _now()
        self._save()

    # ---------------------------------------------------------------- reading
    def _require(self, name: str) -> Dict[str, Any]:
        e = self._doc["entries"].get(str(name))
        if not e or e.get("status", "active") != "active":
            raise KeyError(f"no active toolbelt entry {name!r} for {self.agent} "
                           f"(have: {', '.join(sorted(self.active())) or 'none'})")
        return e

    def get(self, name: str) -> Dict[str, Any]:
        return self._require(name)

    def active(self) -> List[str]:
        return [n for n, e in self._doc["entries"].items()
                if e.get("status", "active") == "active"]

    def history(self, name: str) -> List[Dict[str, Any]]:
        return [h for h in self._doc["history"] if h["name"] == str(name)]

    def resolve(self, name: str, args: Optional[List[str]] = None) -> List[List[str]]:
        """Resolve a macro's steps: $SELF$ -> the running seat, then $1..$N positional slots.

        $SELF$ IS SUBSTITUTED HERE, AT THE ORGAN, and not at either call site. The shipped
        recovery-kit writes $SELF$ into its own ceremonies (kit.py: "$SELF$"), and until
        2026-08-20 nothing ever replaced it -- `run --dry` rendered `defer $SELF$ --list`
        literally. Worse, the downstream door ACCEPTED the literal token: `defer '$SELF$' --list`
        exits 0 and prints "queue empty", so an unsubstituted ceremony read a phantom seat's queue
        and reported nothing waiting, cheerfully, while the real queue filled. Locally true about
        that queue, false about the world. Closing it in resolve() means every path that resolves
        steps -- run, kits, and any future composer -- inherits the fix."""
        e = self._require(name)
        need = int(e.get("params", 0) or 0)
        args = list(args or [])
        steps = [[(self.agent if str(t) == "$SELF$" else t) for t in s] for s in e["steps"]]
        if need:
            if len(args) < need:
                raise ValueError(f"macro {name!r} expects {need} arg(s) "
                                 f"({'$' + ', $'.join(str(i) for i in range(1, need + 1))}); "
                                 f"got {len(args)}")
            def sub(tok):
                m = _SLOT.fullmatch(str(tok))
                return args[int(m.group(1)) - 1] if m else tok
            return [[sub(t) for t in s] for s in steps]
        return [list(s) for s in steps]

    def render_list(self) -> str:
        rows = [f"# toolbelt: {self.agent} -- {len(self.active())} active "
                f"(quota {self.quota}; evidence confesses: GUESS = never pinned)"]
        by_family: Dict[str, list] = {}
        for n in sorted(self.active()):
            by_family.setdefault(self._doc["entries"][n].get("family", "UNSORTED"), []).append(n)
        for fam in sorted(by_family):
            rows.append(f"  [{fam}]")
            for n in by_family[fam]:
                e = self._doc["entries"][n]
                rows.append(f"    {n:<20} v{e['version']}  [{e['evidence']}"
                            f"{' :' + e['tested_against'] if e.get('tested_against') else ''}]  "
                            f"{len(e['steps'])} step(s): " +
                            " -> ".join(s[0] for s in e["steps"]))
        return "\n".join(rows)

    # ---------------------------------------------------------------- execution
    def resolve_and_run(self, name: str, *, runner: Callable[[List[str]], int],
                        args: Optional[List[str]] = None) -> int:
        """Run each step through `runner(argv) -> rc`, stopping at the first non-zero rc.
        The runner is INJECTED (the CLI passes a subprocess invoker; pins pass a recorder)."""
        for argv in self.resolve(name, args=args):
            rc = int(runner(argv) or 0)
            if rc != 0:
                return rc
        return 0


def _now() -> str:
    return now_iso()   # T119: the one clock (aware UTC), not the machine's naive wall


_VERB_CACHE: set = set()


def _agent_cli_verbs() -> set:
    """The door's live verb roster, discovered from agent_cli's own parser (no hand list).
    Module-cached (deepseek fence FLAG 2): build_parser() is a heavy import; the roster only
    changes on a code change, which reloads the module anyway."""
    global _VERB_CACHE
    if _VERB_CACHE:
        return _VERB_CACHE
    import agent_cli
    p = agent_cli.build_parser()
    for a in p._actions:                                     # the subparsers action holds choices
        if hasattr(a, "choices") and a.choices:
            _VERB_CACHE = set(a.choices.keys())
            return _VERB_CACHE
    return set()
