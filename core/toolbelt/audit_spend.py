"""audit_spend — the SPEND domain for core.toolbelt.audit (kimi build, partner night R3).

Born from the founding live row in kimi's charter (docs/library/design/20260723_kimi-want-audit-the-fleet-s-mirror-that_86e0f6.md,
domain 2): the night brief rides "warn $80 / refuse $95" while scripts/kimi_chat.py:63
defaults REFUSE_AT to $95.0 (env KIMI_SPEND_REFUSE) and state/kimi_spend.json's budget
reads $124.58 — three budget beliefs, one seat. This domain photographs the front line
between them; it never picks a winner (direction-neutral per the auditor-law: the row
is a photograph, the config constant names the wording).

ALTITUDE (why a sibling module, stated honestly): audit.py's DOMAINS registry imports
its domains; a sibling module keeps the core import graph free of runner-side imports
(kimi_chat pulls an SDK client at module scope — audit must NEVER import it). Config
truth is read by REGEX over the source file, not by import; meter truth is read from
the JSON sidecar. Reads across the boundary are free, only writes are gated; this
module writes nothing, caches nothing, computes live.

ROW SCHEMA: reuses audit.Row. Verdicts:
  MATCH    — the surfaces agree
  DRIFT    — two surfaces disagree (photographed, not resolved)
  UNKNOWN  — a surface is silent/uncomputable (missing sidecar, unseeded meter)

RULES:
  S1 brief-vs-config    — operator's expected refuse line (--expect-refuse) vs the
                          configured REFUSE_AT. The "the brief says $95, does the code?"
                          row.
  S2 config-vs-meter    — meter budget < REFUSE_AT: the wallet grants LESS headroom
                          than the refusal line — the warn/refuse ladder can never
                          fire before the grant is exceeded. Inversion only; budget
                          ABOVE the line is headroom, not drift.
  S3 reconcile-hygiene  — seeded meter whose last_reconcile_ts is older than
                          stale_reconcile_s (default 24h): the fine meter is running
                          un-reconciled against the balance endpoint.
  S4 seeded-honesty     — spent_usd > 0 with seeded false: the meter confesses it
                          never reconciled; the figure is a floor, not a figure.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from core.toolbelt.audit import Row

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_METER = os.path.join(_ROOT, "state", "kimi_spend.json")
DEFAULT_CONFIG = os.path.join(_ROOT, "scripts", "kimi_chat.py")
STALE_RECONCILE_S = 24 * 3600

_ASSIGN_RE = {
    "WARN_AT": re.compile(r"^WARN_AT\s*=\s*float\(os\.getenv\([^)]*?,\s*\"?([\d.]+)", re.M),
    "REFUSE_AT": re.compile(r"^REFUSE_AT\s*=\s*float\(os\.getenv\([^)]*?,\s*\"?([\d.]+)", re.M),
}


def _read_config_defaults(path: str) -> Dict[str, Optional[float]]:
    """WARN_AT / REFUSE_AT defaults from kimi_chat.py by source read (NEVER import —
    the module pulls an SDK client at import time; audit stays side-effect-free)."""
    out: Dict[str, Optional[float]] = {"WARN_AT": None, "REFUSE_AT": None}
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return out
    for key, rx in _ASSIGN_RE.items():
        m = rx.search(text)
        if m:
            try:
                out[key] = float(m.group(1))
            except ValueError:
                out[key] = None
    # generic fallback: plain `NAME = <float>` assignment
    for key in out:
        if out[key] is None:
            m = re.search(rf"^{key}\s*=\s*([\d.]+)\s*$", text, re.M)
            if m:
                try:
                    out[key] = float(m.group(1))
                except ValueError:
                    pass
    return out


def _read_meter(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


class SpendDomain:
    """Cross-read the spend surfaces: operator belief (brief) vs config defaults
    vs the durable meter sidecar. Read-only; computes live; caches nothing."""

    name = "SPEND"

    def __init__(self, *, meter_path: str = DEFAULT_METER,
                 config_path: str = DEFAULT_CONFIG,
                 warn_at: Optional[float] = None,
                 refuse_at: Optional[float] = None,
                 expect_refuse: Optional[float] = None,
                 stale_reconcile_s: float = STALE_RECONCILE_S,
                 now: Optional[float] = None):
        """warn_at/refuse_at: config OVERRIDE (tests inject; production reads the file).
        expect_refuse: the operator/brief's believed refuse line (None = row skipped)."""
        self._meter_path = meter_path
        self._config_path = config_path
        self._warn_override = warn_at
        self._refuse_override = refuse_at
        self._expect_refuse = expect_refuse
        self._stale_s = float(stale_reconcile_s)
        self._now = now

    # -- surfaces -----------------------------------------------------------
    def _config(self) -> Dict[str, Optional[float]]:
        cfg = _read_config_defaults(self._config_path)
        if self._warn_override is not None:
            cfg["WARN_AT"] = self._warn_override
        if self._refuse_override is not None:
            cfg["REFUSE_AT"] = self._refuse_override
        return cfg

    # -- domain entry -------------------------------------------------------
    def run(self) -> List[Row]:
        rows: List[Row] = []
        now = self._now if self._now is not None else time.time()
        cfg = self._config()
        meter = _read_meter(self._meter_path)
        refuse = cfg.get("REFUSE_AT")
        warn = cfg.get("WARN_AT")

        if meter is None:
            try:
                rel = os.path.relpath(self._meter_path, _ROOT)
            except ValueError:  # different drives (Windows tests) — show raw
                rel = self._meter_path
            rows.append(Row(
                domain=self.name, entry_ref="kimi:spend",
                belief_a=f"meter sidecar at {rel}",
                source_a="filesystem",
                belief_b="missing or unparseable", source_b="json parser",
                verdict="UNKNOWN",
                detail="spend meter sidecar unreadable — no spend rows computable",
                rule="meter-missing",
            ))
            return rows

        budget = meter.get("budget")
        spent = meter.get("spent_usd")
        seeded = bool(meter.get("seeded"))
        last_recon = meter.get("last_reconcile_ts")

        # ---- S1: brief-vs-config ------------------------------------------
        if self._expect_refuse is not None and refuse is not None:
            if abs(float(self._expect_refuse) - float(refuse)) > 1e-9:
                rows.append(Row(
                    domain=self.name, entry_ref="kimi:refuse-line",
                    belief_a=f"refuse line ${float(self._expect_refuse):.0f}",
                    source_a="operator belief (brief)",
                    belief_b=f"refuse line ${float(refuse):.0f}", source_b="kimi_chat.py",
                    verdict="DRIFT",
                    detail=(f"the brief rides refuse=${float(self._expect_refuse):.0f} "
                            f"but the config defaults to ${float(refuse):.0f} — the seat "
                            f"and its charter disagree on where the wall is"),
                    rule="brief-vs-config",
                ))

        # ---- S2: config-vs-meter ------------------------------------------
        if refuse is not None and budget is not None:
            if float(budget) < float(refuse):
                rows.append(Row(
                    domain=self.name, entry_ref="kimi:headroom",
                    belief_a=f"refuse at ${float(refuse):.0f}", source_b="kimi_chat.py",
                    belief_b=f"budget ${float(budget):.2f}", source_a="kimi_spend.json",
                    verdict="DRIFT",
                    detail=(f"meter budget ${float(budget):.2f} is BELOW the refuse "
                            f"line ${float(refuse):.0f} — the warn/refuse ladder can "
                            f"never fire before the grant itself is exceeded"),
                    rule="config-vs-meter",
                ))

        # ---- S3: reconcile-hygiene ----------------------------------------
        if seeded and last_recon:
            age = now - float(last_recon)
            if age > self._stale_s:
                rows.append(Row(
                    domain=self.name, entry_ref="kimi:reconcile",
                    belief_a=f"last reconcile {age/3600:.1f}h ago",
                    source_a="kimi_spend.json",
                    belief_b=f"reconcile within {self._stale_s/3600:.0f}h",
                    source_b="hygiene contract",
                    verdict="DRIFT",
                    detail=(f"the fine meter has run {age/3600:.1f}h without a "
                            f"balance-endpoint reconcile — spent=${float(spent or 0):.2f} "
                            f"is metered, not grounded"),
                    rule="reconcile-hygiene",
                ))

        # ---- S4: seeded-honesty -------------------------------------------
        if not seeded and float(spent or 0) > 0:
            rows.append(Row(
                domain=self.name, entry_ref="kimi:seeded",
                belief_a=f"spent=${float(spent):.2f}", source_a="kimi_spend.json",
                belief_b="seeded=false (never reconciled)", source_b="kimi_spend.json",
                verdict="UNKNOWN",
                detail=("the meter carries spend but confesses it never reconciled — "
                        "the figure is a floor, not a figure"),
                rule="seeded-honesty",
            ))

        # ---- MATCH row when nothing fired ----------------------------------
        if not rows:
            parts = []
            if spent is not None:
                parts.append(f"spent=${float(spent):.2f}")
            if budget is not None:
                parts.append(f"budget=${float(budget):.2f}")
            if warn is not None and refuse is not None:
                parts.append(f"ladder ${float(warn):.0f}/${float(refuse):.0f}")
            if seeded:
                parts.append("seeded")
            rows.append(Row(
                domain=self.name, entry_ref="kimi:spend",
                belief_a="coherent", source_a="kimi_spend.json",
                belief_b="coherent", source_b="kimi_chat.py",
                verdict="MATCH",
                detail=" ".join(parts) or "surfaces agree",
            ))

        return rows
