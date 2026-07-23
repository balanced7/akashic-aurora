"""Domain-filter check: --domain VERBS must still exclude SPEND rows after
registration (cmd_audit filters DOMAINS by name; pin the registry shape)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_domain_filter_verbs_excludes_spend():
    from core.toolbelt import audit as _audit
    names = {d.name for d in _audit.DOMAINS}
    assert "VERBS" in names and "SPEND" in names, f"registry drifted: {names}"
    wanted = {"VERBS"}
    domains = [d for d in _audit.DOMAINS if d.name.upper() in wanted]
    assert len(domains) == 1 and domains[0].name == "VERBS"


def test_full_sweep_runs_both_domains():
    from core.toolbelt import audit as _audit
    rows = _audit.run()
    domains_seen = {r.domain for r in rows}
    assert "VERBS" in domains_seen and "SPEND" in domains_seen, domains_seen
