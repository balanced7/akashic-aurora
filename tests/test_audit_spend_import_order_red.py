"""RED pin: core.toolbelt.audit_spend must be importable FIRST, in a fresh interpreter.

Mechanism under pin (defer suite:test_audit_spend_founding_live_kimi):
  audit_spend.py:44 ran `from core.toolbelt.audit import Row` at module scope, while
  audit.py:332 builds `DOMAINS = _default_domains()` in ITS module body -- and that
  imports SpendDomain straight back from audit_spend. Whichever module loads first
  the other one re-enters it half-built; when audit_spend goes first, audit.py asks a
  partially initialised audit_spend for SpendDomain and raises ImportError. The exact
  sibling of the lexicon_bindings cycle fixed in 0a36aa0e, and a green that depends on
  collection order (audit warmed by an earlier test) is the ambient-state trap.

Each pin runs a FRESH interpreter via subprocess so no earlier import in this pytest
process can warm `audit` and hide the cycle.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fresh(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT, capture_output=True, text=True, timeout=120,
    )


def test_audit_spend_imports_first_in_fresh_interpreter():
    """`import core.toolbelt.audit_spend` as the FIRST toolbelt import must succeed."""
    p = _fresh("import core.toolbelt.audit_spend as m; print(m.SpendDomain.__name__)")
    assert p.returncode == 0, (
        "audit_spend cannot be imported first (import cycle with audit.py):\n"
        + p.stderr[-2000:]
    )
    assert "SpendDomain" in p.stdout


def test_audit_spend_run_resolves_row_when_imported_first(tmp_path):
    """Importing first is not enough: SpendDomain.run() must still be able to build
    audit.Row at RUNTIME (a TYPE_CHECKING-only import would pass the pin above and
    NameError here). Injected config/meter so the pin needs no instance-local state."""
    cfg = tmp_path / "kimi_chat.py"
    cfg.write_text('WARN_AT = float(os.getenv("KIMI_SPEND_WARN", "80.0"))\n'
                   'REFUSE_AT = float(os.getenv("KIMI_SPEND_REFUSE", "95.0"))\n',
                   encoding="utf-8")
    meter = tmp_path / "kimi_spend.json"
    meter.write_text('{"spent_usd": 1.0, "budget": 124.58, "seeded": true, '
                     '"last_reconcile_ts": 4102444800}', encoding="utf-8")
    code = (
        "import core.toolbelt.audit_spend as m\n"
        f"d = m.SpendDomain(meter_path={str(meter)!r}, config_path={str(cfg)!r}, "
        "expect_refuse=95.0, now=4102444800.0)\n"
        "rows = d.run()\n"
        "assert rows, 'no rows'\n"
        "print(' '.join(sorted({r.verdict for r in rows})))\n"
    )
    p = _fresh(code)
    assert p.returncode == 0, "run() failed when audit_spend imported first:\n" + p.stderr[-2000:]
    assert p.stdout.strip(), p.stdout
