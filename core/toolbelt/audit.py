"""
audit — the belief-vs-belief photographer (deepseek build, kimi's v2 domain #1).

Born from the R2 taxonomy counter absorbed by kimi (2026-07-22): the toolbelt's VERBS
surface is self-contained enough to be the v1 domain, and the row schema renders
DIRECTION NEUTRALLY — photograph the front line, don't take sides.

ALTITUDE (why toolbelt, stated honestly): audit observes, it doesn't coordinate. Reads
across the boundary are free, only writes are gated (followup.py precedent). audit writes
NOTHING — not even a cache. It computes live at run time, never caches beliefs, never
becomes a sixth surface that itself drifts (claude's auditor-law, adopted from kimi).

ROW SCHEMA:
  Row = (belief_A, source_A) vs (belief_B, source_B)
  Verdict = MATCH | DRIFT | UNKNOWN

  MATCH:   both sources agree
  DRIFT:   the sources disagree — the row PHOTOGRAPHS the disagreement, doesn't resolve it
  UNKNOWN: one or both sources are silent / uncomputable

  The WORDING of which surface is "canonical" is a CONFIG CONSTANT (GROUND_TRUTH_SOURCE),
  not baked into the schema. Pre-ruling, rows render neutrally; post-ruling, one config
  constant flips all rows.

V1 DOMAIN: VERBS — the only domain that is (a) self-contained (registry <-> parser, no
third surface), (b) armed with a receipt that fires TODAY.

TWO FOUNDING RULES (adversarial targets for first run):
  Rule 1 (stale receipt): updated_at > tested_against_ts => INFER, not VERIFIED
  Rule 2 (argparse-eaten): bare "--" token in macro steps consumed by argparse separator
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

# ---------------------------------------------------------------------------
# Row schema
# ---------------------------------------------------------------------------

VERDICTS = ("MATCH", "DRIFT", "UNKNOWN")


@dataclass
class Row:
    """One belief-pair photograph. Direction-neutral: belief_a/source_a vs belief_b/source_b."""
    domain: str
    entry_ref: str               # e.g. "claude:ask-peer"
    belief_a: Any                # value from source A
    source_a: str                # name of source A
    belief_b: Any                # value from source B
    source_b: str                # name of source B
    verdict: str                 # MATCH | DRIFT | UNKNOWN
    detail: str = ""             # human explanation
    rule: str = ""               # which rule fired (empty for MATCH)

    def render(self, ground: str = "registry") -> str:
        """Render one row. `ground` names which source is canonical — only affects wording,
        not the verdict. Pre-ruling, both sources are named neutrally."""
        v = self.verdict
        if v == "MATCH":
            return f"  {v:<7} {self.entry_ref:<24} {self.detail}"
        elif v == "DRIFT":
            return f"  {v:<7} {self.entry_ref:<24} [{self.rule}] {self.detail}"
        else:  # UNKNOWN
            return f"  {v:<7} {self.entry_ref:<24} {self.detail}"


# ---------------------------------------------------------------------------
# Domain protocol
# ---------------------------------------------------------------------------

class Domain(Protocol):
    """A domain is a callable that returns rows. No state, no cache."""
    name: str

    def run(self) -> List[Row]:
        ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_kata_ts(tested_against: Optional[str]) -> Optional[float]:
    """Parse a kata pin like 'kata-20260721-005225' -> Unix timestamp (float).
    Returns None if unparseable or None."""
    if not tested_against:
        return None
    m = re.match(r"kata-(\d{8})-(\d{6})", str(tested_against))
    if not m:
        return None
    try:
        ts_str = f"{m.group(1)}T{m.group(2)[:2]}:{m.group(2)[2:4]}:{m.group(2)[4:6]}"
        return time.mktime(time.strptime(ts_str, "%Y%m%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def _parse_iso_ts(iso_str: Optional[str]) -> Optional[float]:
    """Parse an ISO timestamp like '2026-07-21T00:55:11' -> Unix timestamp."""
    if not iso_str:
        return None
    try:
        return time.mktime(time.strptime(str(iso_str)[:19], "%Y-%m-%dT%H:%M:%S"))
    except (ValueError, OverflowError):
        return None


def _load_agent_cli_verbs() -> set:
    """Live verb roster from agent_cli's own parser — the door's truth."""
    try:
        import agent_cli
        p = agent_cli.build_parser()
        # _subparsers._group_actions[0].choices keys are the registered verbs
        for action in p._actions:
            if hasattr(action, 'choices') and isinstance(action.choices, dict):
                return set(action.choices.keys())
    except Exception:
        pass
    # Fallback: scan the module for cmd_* functions (less precise, but works)
    try:
        import agent_cli
        return {n[4:] for n in dir(agent_cli) if n.startswith('cmd_')}
    except Exception:
        return set()


def _registry_dir() -> str:
    """Path to data/verb-registry/ relative to repo root."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "data", "verb-registry")


def _load_registry(agent: str) -> Optional[Dict[str, Any]]:
    """Load one agent's registry JSON. Returns None if absent or unparseable."""
    path = os.path.join(_registry_dir(), f"{agent}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _all_agents() -> List[str]:
    """Discover agents with registry files."""
    d = _registry_dir()
    if not os.path.isdir(d):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(d)
        if f.endswith(".json")
    )


def _detect_argparse_eaten_tokens(steps: List[List[str]]) -> List[Tuple[int, int, str]]:
    """Find bare '--' tokens in macro steps that argparse would consume as the
    positional separator. Returns list of (step_idx, token_idx, token)."""
    eaten = []
    for si, step in enumerate(steps):
        for ti, tok in enumerate(step):
            if tok == "--":
                eaten.append((si, ti, tok))
    return eaten


# ---------------------------------------------------------------------------
# VERBS domain
# ---------------------------------------------------------------------------

class VerbsDomain:
    """V1 domain: cross-read the verb registry against the live parser.

    Sources:
      A (registry): data/verb-registry/<agent>.json — the durable truth per entry
      B (parser):   agent_cli.build_parser() — the live door

    Rules:
      1. Stale receipt: evidence=VERIFIED but tested_against kata ts < updated_at => DRIFT
      2. Argparse-eaten: any step contains a bare "--" token => DRIFT
      3. Sugar-only: a step verb NOT in the live parser => DRIFT
      4. GUESS honesty: evidence=GUESS but tested_against is not None => DRIFT
    """

    name = "VERBS"

    def __init__(self, ground_truth_source: str = "registry"):
        self._ground = ground_truth_source
        self._verbs: Optional[set] = None  # lazy

    @property
    def verbs(self) -> set:
        if self._verbs is None:
            self._verbs = _load_agent_cli_verbs()
        return self._verbs

    def run(self) -> List[Row]:
        rows: List[Row] = []
        for agent in _all_agents():
            reg = _load_registry(agent)
            if not reg:
                rows.append(Row(
                    domain=self.name, entry_ref=f"{agent}:*",
                    belief_a="registry file exists", source_a="filesystem",
                    belief_b="unparseable or missing", source_b="json parser",
                    verdict="UNKNOWN",
                    detail=f"cannot load registry for {agent}",
                    rule="load-failure",
                ))
                continue

            entries = reg.get("entries", {})
            for name, entry in entries.items():
                ref = f"{agent}:{name}"
                rows.extend(self._check_entry(agent, name, entry))

        return rows

    def _check_entry(self, agent: str, name: str,
                     entry: Dict[str, Any]) -> List[Row]:
        """Run all rules against one registry entry. Returns 0-N rows."""
        rows: List[Row] = []
        ref = f"{agent}:{name}"

        evidence = entry.get("evidence", "GUESS")
        tested_against = entry.get("tested_against")
        updated_at = entry.get("updated_at")
        steps = entry.get("steps", [])
        kind = entry.get("kind", "alias")

        # ---- Rule 1: stale receipt ----
        if evidence == "VERIFIED" and tested_against:
            kata_ts = _parse_kata_ts(tested_against)
            updated_ts = _parse_iso_ts(updated_at)
            if kata_ts is not None and updated_ts is not None and updated_ts > kata_ts:
                rows.append(Row(
                    domain=self.name, entry_ref=ref,
                    belief_a="VERIFIED", source_a="registry",
                    belief_b="INFER (stale receipt)", source_b="kata timestamp",
                    verdict="DRIFT",
                    detail=(f"registry claims VERIFIED but kata receipt "
                            f"{tested_against} ({time.strftime('%H:%M:%S', time.localtime(kata_ts))}) "
                            f"is older than updated_at {updated_at}"),
                    rule="stale-receipt",
                ))

        # ---- Rule 2: argparse-eaten tokens ----
        eaten = _detect_argparse_eaten_tokens(steps)
        if eaten:
            locations = ", ".join(f"step[{si}][{ti}]" for si, ti, _ in eaten)
            rows.append(Row(
                domain=self.name, entry_ref=ref,
                belief_a="steps valid (argparse accepts them)", source_a="argparse",
                belief_b="steps contain bare '--' token(s)", source_b="step definition",
                verdict="DRIFT",
                detail=(f"argparse-eaten token(s): {locations} — "
                        f"the '--' positional separator is silently consumed; "
                        f"delivered text is not what was written"),
                rule="argparse-eaten",
            ))

        # ---- Rule 3: sugar-only (verb roster check) ----
        live_verbs = self.verbs
        for si, step in enumerate(steps):
            if step and live_verbs:
                verb = str(step[0])
                if verb not in live_verbs:
                    rows.append(Row(
                        domain=self.name, entry_ref=ref,
                        belief_a=f"verb '{verb}' in registry", source_a="registry",
                        belief_b=f"verb '{verb}' NOT in live parser", source_b="agent_cli",
                        verdict="DRIFT",
                        detail=(f"step[{si}] verb '{verb}' is not a known agent_cli verb "
                                f"({len(live_verbs)} verbs in parser)"),
                        rule="sugar-only",
                    ))

        # ---- Rule 4: GUESS honesty ----
        if evidence == "GUESS" and tested_against is not None:
            rows.append(Row(
                domain=self.name, entry_ref=ref,
                belief_a="GUESS (untested)", source_a="registry",
                belief_b=f"tested_against={tested_against}", source_b="registry",
                verdict="DRIFT",
                detail=(f"evidence=GUESS but tested_against is set to "
                        f"'{tested_against}' — confesses untested but has a receipt"),
                rule="guess-honesty",
            ))

        # ---- No rows emitted = all checks passed = MATCH ----
        if not rows:
            detail_parts = [f"{evidence}"]
            if tested_against:
                detail_parts.append(f"receipt {tested_against}")
            if updated_at:
                detail_parts.append(f"updated {updated_at[11:16]}")
            rows.append(Row(
                domain=self.name, entry_ref=ref,
                belief_a=evidence, source_a="registry",
                belief_b=evidence, source_b="parser",
                verdict="MATCH",
                detail=" ".join(detail_parts),
            ))

        return rows


# ---------------------------------------------------------------------------
# Audit runner
# ---------------------------------------------------------------------------

# Registered domains (append new domains here)
DOMAINS: List[Domain] = [VerbsDomain()]


def run(domains: Optional[List[Domain]] = None,
        ground_truth_source: str = "registry") -> List[Row]:
    """Run all domains (or a subset), collect rows. Read-only; no side effects."""
    doms = domains or DOMAINS
    rows: List[Row] = []
    for d in doms:
        try:
            rows.extend(d.run())
        except Exception as exc:
            rows.append(Row(
                domain=getattr(d, 'name', '?'),
                entry_ref="*",
                belief_a=None, source_a="domain",
                belief_b=str(exc), source_b="exception",
                verdict="UNKNOWN",
                detail=f"domain crashed: {type(exc).__name__}: {exc}",
                rule="domain-crash",
            ))
    return rows


def render(rows: Optional[List[Row]] = None,
           domains: Optional[List[Domain]] = None,
           ground_truth_source: str = "registry") -> str:
    """Render rows as a text table. If rows not provided, runs audit first."""
    if rows is None:
        rows = run(domains=domains, ground_truth_source=ground_truth_source)

    by_domain: Dict[str, List[Row]] = {}
    for r in rows:
        by_domain.setdefault(r.domain, []).append(r)

    verdict_counts: Dict[str, int] = {"MATCH": 0, "DRIFT": 0, "UNKNOWN": 0}
    for r in rows:
        if r.verdict in verdict_counts:
            verdict_counts[r.verdict] += 1

    lines = [
        f"# audit — {len(rows)} row(s) across {len(by_domain)} domain(s)",
        f"# verdicts: {verdict_counts['MATCH']} MATCH, "
        f"{verdict_counts['DRIFT']} DRIFT, {verdict_counts['UNKNOWN']} UNKNOWN",
        f"# ground-truth source: {ground_truth_source}",
        "",
    ]

    for domain_name, domain_rows in by_domain.items():
        d_m = sum(1 for r in domain_rows if r.verdict == "MATCH")
        d_d = sum(1 for r in domain_rows if r.verdict == "DRIFT")
        d_u = sum(1 for r in domain_rows if r.verdict == "UNKNOWN")
        lines.append(f"[{domain_name}] {len(domain_rows)} row(s) "
                     f"({d_m}M/{d_d}D/{d_u}U)")
        for r in domain_rows:
            lines.append(r.render(ground=ground_truth_source))
        lines.append("")

    return "\n".join(lines)


def json_result(rows: Optional[List[Row]] = None,
                domains: Optional[List[Domain]] = None,
                ground_truth_source: str = "registry") -> List[Dict[str, Any]]:
    """Render rows as a list of dicts (for --json output)."""
    if rows is None:
        rows = run(domains=domains, ground_truth_source=ground_truth_source)
    return [
        {
            "domain": r.domain,
            "entry_ref": r.entry_ref,
            "belief_a": r.belief_a,
            "source_a": r.source_a,
            "belief_b": r.belief_b,
            "source_b": r.source_b,
            "verdict": r.verdict,
            "detail": r.detail,
            "rule": r.rule,
        }
        for r in rows
    ]
