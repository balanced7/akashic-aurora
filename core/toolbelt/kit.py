"""kit (T099 · KIT tier) — installable bundles of belt entries (kimi, PASS 2 build).

The concept model's top rung: verb (atom) → combo (fixed alias) → macro ($1..$9) →
tool (play script) → **KIT** (an installable bundle). This module is the KIT tier's v1:
define a bundle once, install it into any seat's belt in one call, with the registry's
own laws doing the refusing.

Laws (riding the seams that already exist, sugar-first):
  BUNDLE-IS-DATA   -- a kit is a plain dict (JSON-able): name, version, why, and a list
                      of entry specs in EXACTLY the shape Toolbelt.mint() takes. No new
                      file format, no new parser: kits can live in docs, bus notes, or
                      data/kits/*.json later; v1 ships the recovery-kit as a constant.
  MINT-RIDES       -- install = Toolbelt.mint() per entry. Sugar-only validation,
                      quota guard, evidence labels, supersession semantics ALL come
                      from the registry for free. A kit can never mint a capability
                      the door doesn't know, because mint can't.
  IDEMPOTENT       -- exact re-install is a no-op per entry (registry's exact-re-mint
                      rule); changed entries supersede with version+1. Install twice,
                      get one state. RB-26-safe by inheritance.
  HONESTY          -- kit entries carry their own evidence labels (the recovery-kit's
                      drain-decide is VERIFIED with its kata pin; the rest confess
                      GUESS until the exec seat fires them). A kit never upgrades a
                      label the entry didn't earn.
  CONFESS-INSTALL  -- install() returns a per-entry report: minted / superseded /
                      no-op / REFUSED (quota, unknown verb, bad name). Partial
                      installs are visible; a refused entry never silently skips.

Grounding (G1-G4): 'kit' is engineering vernacular (toolkit, kit-of-parts; G1). The
first kit's name, 'recovery-kit', is what a newcomer googles into (G4). The culture
layer can callsign it Operation TAHITI when the revive ceremony wants poetry (G3).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

# ---------------------------------------------------------------- the first kit
# The recovery-arc's floor, one install away. Every entry is a verb that already
# exists on some belt tonight (cross-seat harvest, authors attributed in `why`).
# Evidence labels are honest: only entries with a real kata pin claim VERIFIED.
RECOVERY_KIT: Dict[str, Any] = {
    "name": "recovery-kit",
    "version": 2,   # v2 2026-07-21: pause steps carry --ttl 120 (RB-30 self-heal) -- the
                    # first install-dogfood caught v1 SILENTLY STRIPPING the TTL graduation
                    # from an installed belt (deepseek's C1-8-genus find rode the belts but
                    # not the kit; a kit must never regress the ceremony it distributes).
    "why": ("the wake-loop/straggler/stall recovery floor, installable on any seat in "
            "one call. Harvested cross-seat 2026-07-21: claude's standby-hard (30+ live "
            "receipts), kimi's drain-decide (kata-VERIFIED), deepseek's vitals + "
            "premise-check (the eyes). The kit's thesis: recovery is a LOADOUT, not a "
            "memory -- a seat that has it installed never hand-types the ceremony."),
    "entries": [
        {"name": "standby-hard",
         "steps": [["bifrost-pause", "--reason", "kit-standby", "--by", "$SELF$",
                    "--ttl", "120"],
                   ["bifrost-skip-to-now", "$SELF$", "--by", "$SELF$",
                    "--reason", "kit-standby-ceremony"],
                   ["bifrost-resume"]],
         "evidence": "VERIFIED",
         "tested_against": "kata-20260721-020106",
         "why": ("claude's, 30+ live receipts: pause+skip+resume, the wake-loop breaker. "
                 "ttl 120 self-heals a mid-ceremony crash (deepseek find 2026-07-21)."),
         "family": "ENGINEERS"},
        {"name": "drain-decide",
         "steps": [["bifrost-sync", "$SELF$", "--consume"],
                   ["bifrost-pause", "--reason", "drain-decide", "--by", "$SELF$",
                    "--ttl", "120"],
                   ["bifrost-skip-to-now", "$SELF$", "--by", "$SELF$",
                    "--reason", "straggler-triage"],
                   ["bifrost-resume"]],
         "evidence": "VERIFIED",
         "tested_against": "kata-20260721-020107",
         "why": ("kimi's, kata-VERIFIED: consume-then-skip, the straggler triage. "
                 "ttl 120 self-heals (same graduation as standby-hard)."),
         "family": "ENGINEERS"},
        {"name": "vitals",
         "steps": [["doctor"], ["bifrost-dashboard"]],
         "evidence": "GUESS",
         "why": "deepseek's: is anyone dying silently. The kit's eyes-before-hands law.",
         "family": "LIFEWORKERS"},
        {"name": "premise-check",
         "steps": [["doctor"], ["delta", "$SELF$"], ["bifrost-inbox"]],
         "evidence": "GUESS",
         "why": "deepseek's: is the system's story about itself true. C9-1's killer.",
         "family": "SENTINELS"},
    ],
}


def _self_substitute(steps: List[List[str]], agent: str) -> List[List[str]]:
    """$SELF$ is the kit's one macro: the installing seat's name. Kits install the SAME
    ritual on every belt; the only thing that changes is who it's for. ($1..$9 stay
    reserved for MACROS; a kit is not a macro.)"""
    return [[agent if str(tok) == "$SELF$" else str(tok) for tok in s] for s in steps]


def install(kit: Dict[str, Any], belt: Any, *, agent: Optional[str] = None) -> Dict[str, Any]:
    """Install a kit into a Toolbelt. Returns a per-entry report; never raises on a
    refused entry (the refusal lands in the report, the rest still install).
    belt = a core.toolbelt.registry.Toolbelt for the installing seat (INJECTED, so
    tests pass a recorder belt)."""
    seat = str(agent or getattr(belt, "agent", "?"))
    report: Dict[str, Any] = {"kit": kit.get("name", "?"), "version": kit.get("version", 1),
                              "seat": seat, "entries": [], "ok": True}
    for spec in kit.get("entries", []):
        name = str(spec.get("name", ""))
        row: Dict[str, Any] = {"name": name}
        try:
            steps = _self_substitute(spec.get("steps", []), seat)
            prior = None
            try:
                prior = belt.get(name)                     # active entry exists?
            except Exception:
                prior = None
            entry = belt.mint(name, steps,
                              kind=str(spec.get("kind", "alias")),
                              evidence=str(spec.get("evidence", "GUESS")),
                              tested_against=spec.get("tested_against"),
                              why=str(spec.get("why", "")),
                              family=str(spec.get("family", "UNSORTED")))
            if prior is not None and entry is prior:
                row["result"] = "no-op (exact re-install)"
            elif prior is not None or int(entry.get("version", 1)) > 1:
                row["result"] = f"superseded -> v{entry.get('version')}"
            else:
                row["result"] = "minted"
            row["evidence"] = entry.get("evidence", "GUESS")
        except Exception as e:
            row["result"] = f"REFUSED ({type(e).__name__}: {e})"
            report["ok"] = False
        report["entries"].append(row)
    return report


def render_report(rep: Dict[str, Any]) -> str:
    rows = [f"# kit install: {rep['kit']} v{rep['version']} -> {rep['seat']}'s belt"]
    for e in rep["entries"]:
        mark = "ok" if not e["result"].startswith("REFUSED") else "REFUSED"
        rows.append(f"  [{mark}] {e['name']:<18} {e['result']}"
                    + (f"  [{e.get('evidence')}]" if e.get("evidence") else ""))
    rows.append("kit %s" % ("installed clean" if rep["ok"] else "installed with REFUSALS (see above)"))
    return "\n".join(rows)
