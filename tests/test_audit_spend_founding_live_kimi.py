"""Founding live run: audit SPEND domain against the REAL meter + REAL config
(kimi, partner night 2026-07-23). The acceptance bar from my own charter:
the tool names its founding row on its first live run, or the night isn't done.
Rides the pytest door (exec allowlist); prints the row table for the receipt."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_founding_live_spend_run():
    from core.toolbelt.audit_spend import SpendDomain
    from core.toolbelt.audit import render

    # The night brief's belief: refuse $95 (warn $80). No --expect-refuse
    # disagreement to inject: brief and config agree on 95. The founding row
    # is the one the charter named: budget $124.58 vs the ladder the brief
    # believes binds — and any reconcile/seeded drift the live meter carries.
    d = SpendDomain(expect_refuse=95.0)
    rows = d.run()
    print()
    print(render(rows=rows, ground_truth_source="config"))
    for r in rows:
        print(f"  [row] {r.verdict:<7} {r.entry_ref:<20} rule={r.rule or '-':<18} {r.detail}")

    # Assertions: the run must DEGRADE GRACEFULLY and never crash (read-only law),
    # and every row must carry the honesty schema.
    assert rows, "no rows at all — the domain is blind"
    for r in rows:
        assert r.verdict in ("MATCH", "DRIFT", "UNKNOWN")
        assert r.detail, "a row without detail is a verdict without a receipt"

    # The founding CLAIMS to verify live:
    #  (a) config refuse default parses to 95.0 from scripts/kimi_chat.py
    from core.toolbelt.audit_spend import _read_config_defaults, DEFAULT_CONFIG
    cfg = _read_config_defaults(DEFAULT_CONFIG)
    print(f"  [config] parsed defaults: {cfg}")
    assert cfg["REFUSE_AT"] == 95.0, f"config parse drifted: {cfg}"
    assert cfg["WARN_AT"] == 80.0, f"config parse drifted: {cfg}"
    #  (b) meter sidecar reads its known live values (budget raised by credits)
    from core.toolbelt.audit_spend import _read_meter, DEFAULT_METER
    meter = _read_meter(DEFAULT_METER)
    assert meter is not None, "live meter unreadable"
    print(f"  [meter] spent=${meter.get('spent_usd')} budget=${meter.get('budget')} "
          f"seeded={meter.get('seeded')} last_reconcile_age_h="
          f"{(time.time() - float(meter.get('last_reconcile_ts') or 0)) / 3600:.1f}")
    # brief-vs-config must NOT fire (brief 95 == config 95)
    assert not [r for r in rows if r.rule == "brief-vs-config"], \
        "brief and config agree on 95 — an S1 row here would be a false positive"
