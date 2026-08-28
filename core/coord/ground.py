"""Truthful evidence ladders for Aurora subjects.

``ground`` is a view over existing authorities.  It never executes the target,
changes a cursor, registers presence, or mints a receipt.  The important
distinction is between a declared address, an authorization decision, a wired
handler, a lexical test reference, and fresh operational proof.

T084 S1 starts with ``verb:<name>``.  S3 adds the deliberately explicit
``seat:<id> --continuity`` form without overloading a bare word or allowing
continuity evidence to become an identity verdict.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


_ROOT = Path(__file__).resolve().parents[2]
_RUNG_ORDER = ("declared", "reachable", "authorized", "wired", "exercised", "proven")
_STATES = {"observed", "partial", "absent", "refused", "unknown"}


# These are not claims about every door.  They name gates mechanically observed
# in the current implementations.  A missing entry means UNKNOWN, never open.
# Keeping the map per-door is load-bearing: bifrost_send is ACL-gated on the
# ToolBox while its CLI and MCP twins currently send directly.
_DOOR_CAP_REQUIREMENTS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "bifrost_send": {"toolbox": ("bus.send",)},
    "bifrost_nudge": {"toolbox": ("bus.nudge",)},
    "learn": {"toolbox": ("kb.learn",)},
    "note": {"toolbox": ("kb.learn",)},
    "write_file": {"toolbox": ("write",)},
    "edit_file": {"toolbox": ("write",)},
    "run_command": {"toolbox": ("exec",)},
}

# Explicitly open read seams.  An empty requirement is different from an
# unknown requirement: it was checked, and no subject capability gate exists.
_OPEN_READ_DOORS: Dict[str, Tuple[str, ...]] = {
    "sweep": ("cli", "mcp", "toolbox"),
    "ground": ("cli", "mcp", "toolbox"),
}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _norm(value: str) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _rung(name: str, state: str, claim: str, source: str, observed_at: str,
          *, details: Optional[Mapping[str, Any]] = None, drill: str) -> Dict[str, Any]:
    if name not in _RUNG_ORDER:
        raise ValueError(f"unknown evidence rung {name!r}")
    if state not in _STATES:
        raise ValueError(f"unknown evidence state {state!r}")
    return {
        "name": name,
        "state": state,
        "claim": str(claim),
        "source": str(source),
        "observed_at": observed_at,
        "details": dict(details or {}),
        "drill": str(drill),
    }


def _parse_target(target: str) -> Tuple[str, str]:
    raw = str(target or "").strip()
    if ":" not in raw:
        raise ValueError("ground target must be typed, e.g. verb:sweep")
    raw_kind, raw_name = raw.split(":", 1)
    kind = _norm(raw_kind)
    # Verb addresses use the door census' underscore normalization.  Seat ids
    # are identities, not verbs: preserve their spelling and punctuation so two
    # subjects can never be merged by a convenience normalizer.
    name = _norm(raw_name) if kind == "verb" else str(raw_name or "").strip()
    if not name:
        raise ValueError("ground target name is required")
    if kind not in {"verb", "seat"}:
        raise ValueError(f"unsupported ground target kind {kind!r}; use verb:<name> or seat:<id>")
    return kind, name


def _surface_inventory() -> Dict[str, Any]:
    """Read the live door-parity authority, one source at a time.

    The checker remains the declared surface authority; importing its constants
    avoids creating a second manifest.  Individual readers fail independently so
    a moved ToolBox class cannot erase CLI/MCP evidence.
    """
    errors: Dict[str, str] = {}
    try:
        from scripts.checkers import check_door_parity as dp
    except Exception as exc:
        why = f"{type(exc).__name__}: {exc}"
        return {"manifest": {}, "aliases": {}, "exempt": {},
                "doors": {"cli": set(), "mcp": set(), "toolbox": set()},
                "errors": {"door_parity": why}}

    def _read(label: str, fn) -> set:
        try:
            return set(fn())
        except Exception as exc:
            errors[label] = f"{type(exc).__name__}: {exc}"
            return set()

    try:
        manifest = dict(dp.MANIFEST)
        aliases = {
            "mcp": dict(dp.CLI_MCP_ALIASES),
            "toolbox": dict(dp.TOOLBOX_ALIASES),
        }
        exempt = dict(dp.TOOLBOX_EXEMPT)
    except Exception as exc:
        manifest, aliases, exempt = {}, {"mcp": {}, "toolbox": {}}, {}
        errors["manifest"] = f"{type(exc).__name__}: {exc}"

    return {
        "manifest": manifest,
        "aliases": aliases,
        "exempt": exempt,
        "doors": {
            "cli": _read("cli", dp.cli_verbs),
            "mcp": _read("mcp", dp.mcp_tools),
            "toolbox": _read("toolbox", dp.toolbox_verbs),
        },
        "errors": errors,
    }


def _door_rows(name: str, inv: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    aliases = inv.get("aliases") or {}
    addresses = {
        "cli": name,
        "mcp": (aliases.get("mcp") or {}).get(name, name),
        "toolbox": (aliases.get("toolbox") or {}).get(name, name),
    }
    rows: Dict[str, Dict[str, Any]] = {}
    for door in ("cli", "mcp", "toolbox"):
        address = addresses[door]
        present = address in ((inv.get("doors") or {}).get(door) or set())
        relation = "native"
        if address != name:
            relation = "alias"
        if door == "toolbox" and name in (inv.get("exempt") or {}) and not present:
            relation = "exempt"
        rows[door] = {
            "address": address,
            "present": bool(present),
            "relation": relation if present or relation == "exempt" else "missing",
        }
        if relation == "exempt":
            rows[door]["reason"] = (inv.get("exempt") or {})[name]
    return rows


def _expected_doors(classification: Optional[str]) -> Tuple[str, ...]:
    return {
        "shared": ("cli", "mcp", "toolbox"),
        "cli_only": ("cli",),
        "mcp_only": ("mcp",),
        "toolbox_only": ("toolbox",),
    }.get(str(classification or ""), ())


def _wired_rows(doors: Mapping[str, Mapping[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, str]]:
    errors: Dict[str, str] = {}
    out: Dict[str, Any] = {}

    # CLI: the live parser's dispatch callable, not a regex hit.
    cli_row = dict(doors["cli"])
    cli_row["wired"] = False
    if cli_row["present"]:
        try:
            import agent_cli
            parser = agent_cli.build_parser()
            subs = next(a for a in parser._actions
                        if isinstance(a, argparse._SubParsersAction))
            choice = next((p for raw, p in subs.choices.items() if _norm(raw) == cli_row["address"]), None)
            fn = choice.get_default("fn") if choice is not None else None
            cli_row["wired"] = callable(fn)
            cli_row["handler"] = getattr(fn, "__name__", "") if callable(fn) else ""
        except Exception as exc:
            errors["cli"] = f"{type(exc).__name__}: {exc}"
    out["cli"] = cli_row

    # MCP: decorator census established the address; this proves a real callable
    # with that address is present in the loaded server module.
    mcp_row = dict(doors["mcp"])
    mcp_row["wired"] = False
    if mcp_row["present"]:
        try:
            import ai_setup_mcp
            fn = getattr(ai_setup_mcp, mcp_row["address"], None)
            mcp_row["wired"] = callable(fn)
            mcp_row["handler"] = getattr(fn, "__name__", "") if callable(fn) else ""
        except Exception as exc:
            errors["mcp"] = f"{type(exc).__name__}: {exc}"
    out["mcp"] = mcp_row

    tb_row = dict(doors["toolbox"])
    tb_row["wired"] = False
    if tb_row["present"]:
        try:
            from core.comm.toolbox import TOOLS, ToolBox
            fn = getattr(ToolBox, tb_row["address"], None)
            advertised = {r.get("function", {}).get("name") for r in TOOLS}
            tb_row["method_callable"] = callable(fn)
            tb_row["advertised"] = tb_row["address"] in advertised
            tb_row["wired"] = bool(tb_row["method_callable"] and tb_row["advertised"])
            tb_row["handler"] = getattr(fn, "__name__", "") if callable(fn) else ""
        except Exception as exc:
            errors["toolbox"] = f"{type(exc).__name__}: {exc}"
    out["toolbox"] = tb_row
    return out, errors


def _grant_details(name: str, subject: str, doors: Mapping[str, Mapping[str, Any]]) -> Tuple[str, Dict[str, Any], str]:
    errors = ""
    try:
        from core.trust import registry
        grant = registry.resolve(subject)
        caps = sorted(getattr(c, "value", str(c)) for c in grant.caps)
        role = grant.role
        path_scope = list(grant.path_scope)
        kinds = None if grant.bus_send_kinds is None else sorted(grant.bus_send_kinds)
        expires = grant.expires_at
    except Exception as exc:
        grant = None
        caps, role, path_scope, kinds, expires = [], "UNKNOWN", [], [], None
        errors = f"{type(exc).__name__}: {exc}"

    per_door: Dict[str, Any] = {}
    required_union: set[str] = set()
    missing_union: set[str] = set()
    known_states: List[str] = []
    reqs = _DOOR_CAP_REQUIREMENTS.get(name, {})
    opens = set(_OPEN_READ_DOORS.get(name, ()))
    for door in ("cli", "mcp", "toolbox"):
        if not doors[door]["present"]:
            per_door[door] = {"state": "absent", "required_caps": [],
                              "claim": "no address on this door"}
            continue
        required = list(reqs.get(door, ()))
        required_union.update(required)
        missing: List[str] = []
        if door in opens:
            state, claim = "observed", "read seam has no subject capability gate"
        elif required:
            missing = sorted(set(required) - set(caps))
            missing_union.update(missing)
            state = "refused" if missing else "observed"
            claim = (f"effective grant lacks {', '.join(missing)}" if missing
                     else "effective grant satisfies the observed gate")
        else:
            state = "unknown"
            claim = "no mechanically mapped subject capability gate for this door"
        known_states.append(state)
        per_door[door] = {"state": state, "required_caps": required,
                          "missing_caps": missing, "claim": claim}

    if errors:
        aggregate = "unknown"
    elif known_states and all(s == "observed" for s in known_states):
        aggregate = "observed"
    elif known_states and all(s == "refused" for s in known_states):
        aggregate = "refused"
    elif any(s in {"observed", "refused"} for s in known_states):
        aggregate = "partial"
    else:
        aggregate = "unknown"
    details = {
        "role": role,
        "caps": caps,
        "path_scope": path_scope,
        "bus_send_kinds": kinds,
        "expires_at": expires,
        "required_caps": sorted(required_union),
        "missing_caps": sorted(missing_union),
        "doors": per_door,
    }
    if errors:
        details["error"] = errors
    return aggregate, details, errors


def _test_references(name: str, *, cap_files: int = 500, cap_hits: int = 20) -> Dict[str, Any]:
    tests_dir = _ROOT / "tests"
    files = sorted(tests_dir.glob("test_*.py")) if tests_dir.exists() else []
    scanned = files[:max(0, int(cap_files))]
    needles = {name, name.replace("_", "-")}
    hits: List[str] = []
    failed: Dict[str, str] = {}
    total_hits = 0
    for path in scanned:
        try:
            text = path.read_text(encoding="utf-8", errors="replace").lower()
        except Exception as exc:
            failed[str(path.relative_to(_ROOT)).replace("\\", "/")] = type(exc).__name__
            continue
        if any(n in text for n in needles):
            total_hits += 1
            if len(hits) < cap_hits:
                hits.append(str(path.relative_to(_ROOT)).replace("\\", "/"))
    return {
        "files_total": len(files),
        "files_scanned": len(scanned),
        "files_failed": failed,
        "references_total": total_hits,
        "references_shown": hits,
        "truncated": len(files) > len(scanned) or total_hits > len(hits),
        "ordering": "path ascending",
    }


def ground(target: str, *, subject: str, continuity: bool = False) -> Dict[str, Any]:
    """Build one non-mutating, subject-bound evidence ladder."""
    subject = str(subject or "").strip()
    if not subject:
        raise ValueError("ground subject is required")
    kind, name = _parse_target(target)
    if kind == "seat":
        if not continuity:
            raise ValueError("seat grounding requires the explicit --continuity mode")
        if subject != name:
            raise ValueError(
                f"seat target must match the bound subject: target={name!r}, subject={subject!r}"
            )
        from core.coord import continuity as _continuity
        return _continuity.build_profile(name)
    if continuity:
        raise ValueError("--continuity is valid only for seat:<id>")

    observed_at = _utc()
    inv = _surface_inventory()
    manifest = inv.get("manifest") or {}
    classification = manifest.get(name)
    doors = _door_rows(name, inv)
    any_present = any(row["present"] for row in doors.values())
    expected = _expected_doors(classification)

    if classification:
        declared_state = "observed"
        declared_claim = f"door-parity manifest classifies {name} as {classification}"
    elif inv.get("errors", {}).get("manifest"):
        declared_state = "unknown"
        declared_claim = "door declaration could not be read"
    elif any_present:
        declared_state = "unknown"
        declared_claim = "address exists but is unclassified by the door manifest"
    else:
        declared_state = "absent"
        declared_claim = "healthy door census found no declaration or address"

    present_expected = [d for d in expected if doors[d]["present"]]
    if expected and len(present_expected) == len(expected):
        reachable_state = "observed"
        reachable_claim = f"all {len(expected)} declared door addresses are present"
    elif any_present:
        reachable_state = "partial"
        reachable_claim = "at least one door address is present; coverage is incomplete or unclassified"
    elif inv.get("errors"):
        reachable_state = "unknown"
        reachable_claim = "no address was observed, but one or more door readers failed"
    else:
        reachable_state = "absent"
        reachable_claim = "no CLI, MCP, or ToolBox address was observed"

    auth_state, auth_details, auth_error = _grant_details(name, subject, doors)
    wired, wired_errors = _wired_rows(doors)
    expected_for_wiring = list(expected) if expected else [d for d, row in doors.items() if row["present"]]
    wired_expected = [d for d in expected_for_wiring if wired[d].get("wired")]
    if expected_for_wiring and len(wired_expected) == len(expected_for_wiring):
        wired_state = "observed"
        wired_claim = "every declared endpoint resolves to a callable, advertised handler"
    elif wired_expected:
        wired_state = "partial"
        wired_claim = "some observed endpoints resolve; at least one declared endpoint does not"
    elif any_present or wired_errors:
        wired_state = "partial" if wired_errors else "absent"
        wired_claim = "no complete callable wiring was established"
    else:
        wired_state = "absent"
        wired_claim = "there is no observed endpoint to wire"

    refs = _test_references(name)
    if refs["references_total"]:
        exercised_state = "partial"
        exercised_claim = (f"{refs['references_total']} test file(s) reference the verb; "
                            "this scan does not establish that they ran or passed")
    else:
        exercised_state = "unknown"
        exercised_claim = "bounded lexical scan found no test reference; absence is not proof of no exercise"

    source_base = "scripts/checkers/check_door_parity.py (live manifest and AST census)"
    rungs = [
        _rung("declared", declared_state, declared_claim, source_base, observed_at,
              details={"classification": classification, "manifest_entry": name,
                       "reader_errors": inv.get("errors") or {}},
              drill="py scripts/checkers/check_door_parity.py --report"),
        _rung("reachable", reachable_state, reachable_claim, source_base, observed_at,
              details={"doors": doors, "expected_doors": list(expected)},
              drill="py scripts/checkers/check_door_parity.py --report"),
        _rung("authorized", auth_state,
              ("effective grant and per-door gate observations disagree or are incomplete"
               if auth_state == "partial" else
               "effective grant was compared only where a subject gate is mechanically known"),
              "security/acl.json via core.trust.registry.resolve + door implementations",
              observed_at, details=auth_details,
              drill=f"py agent_cli.py ground verb:{name} --agent {subject} --json"),
        _rung("wired", wired_state, wired_claim,
              "live parser defaults + MCP callables + ToolBox method/schema", observed_at,
              details={"doors": wired, "reader_errors": wired_errors},
              drill="py scripts/checkers/check_wiring.py"),
        _rung("exercised", exercised_state, exercised_claim,
              "tests/test_*.py bounded lexical reference scan (not execution)", observed_at,
              details=refs,
              drill=f"py -m pytest -q -k {name}"),
        _rung("proven", "unknown",
              "no canonical fresh runtime receipt resolver currently maps this verb to a successful execution",
              "canonical runtime receipt resolver: unavailable", observed_at,
              details={"receipt": None, "freshness": "unknown"},
              drill=f"exercise verb:{name} through the intended door and record an independent receipt"),
    ]

    blind = ["fresh runtime proof: no canonical verb-to-receipt resolver"]
    for label, why in sorted((inv.get("errors") or {}).items()):
        blind.append(f"door source {label}: {why}")
    for label, why in sorted(wired_errors.items()):
        blind.append(f"wiring source {label}: {why}")
    if auth_error:
        blind.append(f"effective grant: {auth_error}")
    if refs["truncated"]:
        blind.append("test reference scan was truncated")
    if refs["files_failed"]:
        blind.append(f"{len(refs['files_failed'])} test file(s) unreadable")

    sources_failed = len(inv.get("errors") or {}) + len(wired_errors) + bool(auth_error)
    return {
        "schema": "ground.result.v1",
        "target": {"kind": kind, "name": name},
        "subject": subject,
        "observed_at": observed_at,
        "rungs": rungs,
        "bounds": {
            "sources_total": 7,
            "sources_failed": int(sources_failed),
            "test_files_total": refs["files_total"],
            "test_files_scanned": refs["files_scanned"],
            "ordering": list(_RUNG_ORDER),
        },
        "blind": blind,
        "effects": [],
    }


def render(result: Mapping[str, Any]) -> str:
    """Compact human rendering; JSON remains the full-fidelity surface."""
    if result.get("mode") == "continuity":
        from core.coord.continuity import render_profile
        return render_profile(result)
    target = result.get("target") or {}
    lines = [f"# ground {target.get('kind')}:{target.get('name')} for {result.get('subject')}",
             f"  observed {result.get('observed_at')} | effects: none"]
    for row in result.get("rungs") or []:
        lines.append(f"  {str(row.get('name')).upper():<11} {str(row.get('state')).upper():<8} "
                     f"{row.get('claim')}")
        lines.append(f"              source: {row.get('source')}")
    for item in result.get("blind") or []:
        lines.append(f"  BLIND: {item}")
    return "\n".join(lines)


__all__ = ["ground", "render"]
