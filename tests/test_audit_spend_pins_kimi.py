"""Pins for the SPEND domain — audit's second domain (kimi build, partner night R3).

RED-first: 5 pins pre-registered against the design in
docs/library/design/20260723_kimi-want-audit-the-fleet-s-mirror-that_86e0f6.md (domain 2) and claude's sequencing
(verbs → spend → baseline). Founding live row (the reason this domain exists):
the night brief rides "warn $80 / refuse $95" while scripts/kimi_chat.py:63
defaults REFUSE_AT to $95.0 from KIMI_SPEND_REFUSE — and state/kimi_spend.json's
budget reads $124.58. Three budget beliefs, one seat.

The domain cross-reads three surfaces, direction-neutral:
  A (brief/claim): an operator-supplied expected refuse line (--expect-refuse)
  B (config):      scripts/kimi_chat.py WARN_AT / REFUSE_AT (import or AST read)
  C (meter):       state/kimi_spend.json (the durable sidecar)

Rules (each = one DRIFT row):
  S1 brief-vs-config:  expected refuse != configured REFUSE_AT
  S2 config-vs-meter:  meter budget < REFUSE_AT (the wallet grants more headroom
                       than the refusal line — a seat that never warns is a lie
                       of silence) — UNKNOWN when budget is absent, DRIFT only
                       on a real inversion
  S3 reconcile-hygiene: meter seeded but last_reconcile_ts older than
                       STALE_RECONCILE_S (default 24h) => the fine meter is
                       running un-reconciled
  S4 seeded-honesty:   spent_usd > 0 while seeded is false => the meter confesses
                       it never reconciled; spent is a floor, not a figure

Plus a MATCH row when all surfaces agree (or only C is present and coherent).
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.toolbelt import audit as _audit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _meter(tmp_path, **over):
    state = {
        "spent_usd": 44.28, "turns": 568, "prompt_tokens": 25060973,
        "cached_tokens": 23932416, "completion_tokens": 242192,
        "last_reconcile_ts": time.time() - 100, "last_balance": 82.53,
        "seeded": True, "budget": 124.58, "spent_at_reconcile": 43.90,
    }
    state.update(over)
    p = tmp_path / "kimi_spend.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state), encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# Pin S0: the happy path — all surfaces agree -> MATCH
# ---------------------------------------------------------------------------

def test_s0_match_when_brief_config_meter_agree(tmp_path):
    from core.toolbelt.audit_spend import SpendDomain
    meter = _meter(tmp_path, budget=105.0)
    d = SpendDomain(meter_path=meter, warn_at=80.0, refuse_at=95.0,
                    expect_refuse=95.0)
    rows = d.run()
    verdicts = {r.rule or "match": r.verdict for r in rows}
    assert all(r.verdict == "MATCH" for r in rows), \
        f"expected all-MATCH on agreeing surfaces, got {[(r.rule, r.detail) for r in rows]}"


# ---------------------------------------------------------------------------
# Pin S1: brief-vs-config — the founding live row (80/95 brief vs 95 config)
# ---------------------------------------------------------------------------

def test_s1_brief_refuse_disagrees_with_config(tmp_path):
    from core.toolbelt.audit_spend import SpendDomain
    meter = _meter(tmp_path, budget=105.0)
    # the night brief's warn/refuse pair vs the code default refuse=95
    d = SpendDomain(meter_path=meter, warn_at=80.0, refuse_at=95.0,
                    expect_refuse=95.0)
    rows = d.run()
    s1 = [r for r in rows if r.rule == "brief-vs-config"]
    assert not s1, "same-value expectation must not drift"
    d2 = SpendDomain(meter_path=meter, warn_at=80.0, refuse_at=95.0,
                     expect_refuse=90.0)   # operator believes the line is 90
    rows2 = d2.run()
    s1b = [r for r in rows2 if r.rule == "brief-vs-config"]
    assert s1b and s1b[0].verdict == "DRIFT", \
        "operator belief ($90) vs config ($95) must photograph as DRIFT"


# ---------------------------------------------------------------------------
# Pin S2: config-vs-meter — wallet headroom inversion
# ---------------------------------------------------------------------------

def test_s2_meter_budget_below_refuse_line_is_drift(tmp_path):
    from core.toolbelt.audit_spend import SpendDomain
    # budget $90 but refuse line $95: the seat can never warn before the wallet
    # is past its own grant — inversion
    meter = _meter(tmp_path, budget=90.0)
    d = SpendDomain(meter_path=meter, warn_at=80.0, refuse_at=95.0)
    rows = d.run()
    s2 = [r for r in rows if r.rule == "config-vs-meter"]
    assert s2 and s2[0].verdict == "DRIFT", \
        f"budget ($90) < refuse ($95) must DRIFT, got {[(r.rule, r.verdict) for r in rows]}"
    # and the founding live shape: budget $124.58 >= refuse $95 -> NO drift on S2
    meter2 = _meter(tmp_path / "b", budget=124.58)
    d2 = SpendDomain(meter_path=meter2, warn_at=80.0, refuse_at=95.0)
    s2b = [r for r in d2.run() if r.rule == "config-vs-meter"]
    assert not s2b, "headroom present (budget 124.58 > refuse 95) must not fire S2"


# ---------------------------------------------------------------------------
# Pin S3: reconcile hygiene — stale reconcile photographs UNKNOWN/DRIFT
# ---------------------------------------------------------------------------

def test_s3_stale_reconcile_fires(tmp_path):
    from core.toolbelt.audit_spend import SpendDomain
    old = time.time() - (48 * 3600)   # 48h unreconciled
    meter = _meter(tmp_path, last_reconcile_ts=old)
    d = SpendDomain(meter_path=meter, warn_at=80.0, refuse_at=95.0)
    s3 = [r for r in d.run() if r.rule == "reconcile-hygiene"]
    assert s3 and s3[0].verdict in ("DRIFT", "UNKNOWN"), \
        "48h without a reconcile must photograph"
    fresh = _meter(tmp_path / "b")
    d2 = SpendDomain(meter_path=fresh, warn_at=80.0, refuse_at=95.0)
    assert not [r for r in d2.run() if r.rule == "reconcile-hygiene"], \
        "a reconcile 100s ago must not fire"


# ---------------------------------------------------------------------------
# Pin S4: seeded honesty — unseeded spend confesses, never claims precision
# ---------------------------------------------------------------------------

def test_s4_unseeded_spend_confesses(tmp_path):
    from core.toolbelt.audit_spend import SpendDomain
    meter = _meter(tmp_path, seeded=False, spent_usd=3.21)
    d = SpendDomain(meter_path=meter, warn_at=80.0, refuse_at=95.0)
    s4 = [r for r in d.run() if r.rule == "seeded-honesty"]
    assert s4 and s4[0].verdict == "UNKNOWN", \
        "unseeded meter with spend must read UNKNOWN (a floor, not a figure)"


# ---------------------------------------------------------------------------
# Pin S5: missing meter file -> UNKNOWN, never a crash (read-only law)
# ---------------------------------------------------------------------------

def test_s5_missing_meter_is_unknown_not_crash(tmp_path):
    from core.toolbelt.audit_spend import SpendDomain
    d = SpendDomain(meter_path=str(tmp_path / "nope.json"),
                    warn_at=80.0, refuse_at=95.0)
    rows = d.run()
    assert rows and all(r.verdict == "UNKNOWN" for r in rows), \
        "missing sidecar must degrade to UNKNOWN rows, never raise"
