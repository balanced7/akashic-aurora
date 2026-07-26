"""Generate docs/PRIOR_ART.md -- every subsystem we have, beside what the field already built.

WHY A GENERATOR AND NOT A DOCUMENT
-----------------------------------
Daniel's constraint was "that piece needs to stay up to date". A hand-written inventory rots,
and this week supplied four proofs of that in one day: suite-baseline was 44.7h stale, the
README's value rate had four defects, three derived docs went stale the moment modules landed,
and a chronicle's standing hazard had been retired hours earlier. Anything authored once and
trusted afterwards is a liability here.

So the split is:
  INVENTORY  -- DERIVED from live code every run. Cannot rot.
  PRIOR ART  -- AUTHORED (research is not generatable), stored in data/prior-art/register.json.
  COVERAGE   -- DERIVED. A subsystem with no entry renders GAP. An entry whose subsystem has
                changed size since it was surveyed renders DRIFT.

DRIFT is the honest staleness signal and it is deliberately weak on purpose: it does NOT claim
the research is current, only that the thing researched has moved since someone looked. A
strong claim we cannot back would be the same failure genus as everything else this week.

Run: py scripts/generators/gen_prior_art_register.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "data" / "prior-art" / "register.json"
OUT = ROOT / "docs" / "PRIOR_ART.md"

# Mirrors gen_master_map's AREAS so the two documents cannot disagree about what exists.
CORE_ORDER = ["foundation", "events", "signals", "comm", "coord", "learning", "recall",
              "primitives", "renew", "narrative", "trust", "fleet", "state", "codex",
              "perspectives"]
AREAS = [f"core/{a}" for a in CORE_ORDER] + ["agent/harness", "agent"]
# Subsystems that are real but are not python packages under core/. Named explicitly rather
# than globbed, so adding one is a deliberate act that shows up in review.
EXTRA_AREAS = ["scripts/hooks", "scripts/checkers", "scripts/generators", "scripts/ops", "tests"]


def _module_count(rel: str) -> int:
    d = ROOT / rel
    if not d.is_dir():
        return 0
    return len([p for p in d.glob("*.py") if p.name != "__init__.py"])


def _load_register() -> dict:
    if not REGISTER.exists():
        return {}
    try:
        return json.loads(REGISTER.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[prior-art] register unreadable ({type(e).__name__}: {e}) -- treating as empty")
        return {}


def build():
    reg = _load_register()
    rows = []
    for area in AREAS + EXTRA_AREAS:
        live = _module_count(area)
        if live == 0 and area not in reg:
            continue
        entry = reg.get(area)
        if not entry:
            state = "GAP"
        elif entry.get("module_count") != live:
            state = f"DRIFT ({entry.get('module_count')}->{live})"
        else:
            state = "current"
        rows.append({"area": area, "live": live, "entry": entry, "state": state})
    return rows


def render(rows) -> str:
    gaps = [r for r in rows if r["state"] == "GAP"]
    drift = [r for r in rows if r["state"].startswith("DRIFT")]
    covered = [r for r in rows if r["state"] == "current"]

    L = [
        "# PRIOR ART -- every subsystem, beside what the field already built",
        "",
        "Status: current",
        "Class: reference",
        "",
        "> Do NOT edit by hand. Regenerate with `py scripts/generators/gen_prior_art_register.py`.",
        "> INVENTORY is derived from live code and cannot rot. PRIOR ART is authored in",
        "> `data/prior-art/register.json`. COVERAGE is derived: **GAP** = no entry, **DRIFT** =",
        "> the subsystem changed size since it was surveyed. DRIFT does NOT claim the research",
        "> is wrong -- only that the thing researched has moved and nobody has looked since.",
        "> Companion: MAP.md (module census) - ARCHITECTURE.md (skeleton).",
        "",
        "## Why this file exists",
        "",
        "Daniel, 2026-07-26: *\"We keep finding gold when we do this but we rarely do it so I",
        "want a full comprehensive suite so we can actually start making informed decisions",
        "instead of stepping on every rake as it comes along.\"*",
        "",
        "The claim is empirical, not aspirational. In one night, five sweeps each paid:",
        "oxlint gave confidence-tiered gating; ruff already implemented a lint we were about to",
        "hand-write; pytest already shipped the entire mechanism for the CI-honesty slice;",
        "Letta's plain files beat a graph memory system; Wikidata's three ranks run at ~1.5B",
        "statements where ATMS dies around 100 beliefs. The cost of NOT sweeping is measured in",
        "rebuilt wheels and dead ends, so the sweep is now a standing artifact rather than a mood.",
        "",
        f"## Coverage: {len(covered)} current, {len(drift)} drift, {len(gaps)} gap "
        f"(of {len(rows)} subsystems)",
        "",
    ]

    if gaps:
        L += ["**GAP -- no prior-art entry yet.** The honest backlog, worst first:", ""]
        for r in sorted(gaps, key=lambda r: -r["live"]):
            L.append(f"- `{r['area']}` ({r['live']} modules)")
        L.append("")
    if drift:
        L += ["**DRIFT -- surveyed, but the subsystem has changed size since:**", ""]
        for r in drift:
            L.append(f"- `{r['area']}` -- {r['state']}, reviewed "
                     f"{(r['entry'] or {}).get('reviewed_at', '?')}")
        L.append("")

    L += ["---", ""]

    for r in rows:
        e = r["entry"]
        L.append(f"## `{r['area']}` -- {r['live']} modules  ·  {r['state']}")
        L.append("")
        if not e:
            L += ["_No entry. This subsystem has not been swept against the field._", ""]
            continue
        L.append(f"**What it does.** {e.get('what', '?')}")
        L.append("")
        L.append(f"**Connected to.** {e.get('connected', '?')}")
        L.append("")
        comps = e.get("comparable") or []
        if comps:
            L.append("**Comparable systems.**")
            L.append("")
            for c in comps:
                L.append(f"- **{c.get('name', '?')}** — {c.get('note', '')}")
            L.append("")
        if e.get("delta"):
            L += [f"**The delta.** {e['delta']}", ""]
        if e.get("import"):
            L += [f"**The import.** {e['import']}", ""]
        if e.get("anti_import"):
            L += [f"**The anti-import.** {e['anti_import']}", ""]
        if e.get("evidence"):
            L += [f"**Evidence.** {e['evidence']}", ""]
        L.append(f"_Reviewed {e.get('reviewed_at', '?')} by {e.get('reviewed_by', '?')}._")
        L.append("")

    return "\n".join(L) + "\n"


def main() -> int:
    rows = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(rows), encoding="utf-8")
    gaps = sum(1 for r in rows if r["state"] == "GAP")
    drift = sum(1 for r in rows if r["state"].startswith("DRIFT"))
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} subsystems "
          f"({len(rows) - gaps - drift} current, {drift} drift, {gaps} gap)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
