"""R2 fence probes for deepseek's check_ui_contract.py (kimi, partner night 2026-07-23).

Exec-gated families only: pytest is allowlisted, so these ride the pytest door.
Each test probes one claim or seam from the R2 round:

  T1  TRUTH-IN-LABELING: the script's own docstring + the charter claim "exit 0/1",
      the greenlight says ADVISORY tonight. If the script exits 1 on the CURRENT
      incumbent, its "zero false positives" claim is false -> the ship.py wiring
      would page red on every ship. Run against the REAL file and report the verdict.
  T2  L8 GROUND-TRUTH: raw hex EXISTS at call sites in the current file (fence
      census found ~15: #39405a hovers, #0a0b0f badge text, #20232e scrollbar,
      #0c0e14/#0b0d13 code blocks, #dce0ea content, #fff send, rgba() literals,
      JS '#48e6bf' fallbacks). If the checker exits 0, the L8 check is not checking
      what the contract's token law says -- name the drift.
  T3  L8 SELF-CHECK SANITY: a KNOWN dirty fixture (raw hex at a call site) MUST
      fail; a clean fixture MUST pass. The guard's own TRUE/FALSE positive.
  T4  L3 SPEC-DRIFT: the charter's predicate list {runner===, workN>, legacyN>,
      pages>, allQuiet} grew in-file to include "blocked", "tripped", "offline",
      ">0", ">10", ">100" -- and "tripped" is BOTH an alarm class AND a predicate
      (self-authorizing). Probe: an alarm class whose only nearby "predicate" is
      the word 'tripped' itself must still be flagged (otherwise the check is
      vacuous for its own founding class).
  T5  L1 HONEST GAP: the axis law in the contract says aria-label + data-fresh;
      the checker checks data-agent + title (the deepseek charter's cheaper variant).
      Probe a gauge with data-agent+title but NO aria-label/data-fresh: the checker
      passes it. The report must NAME the gap between contract-v0-law-1 and
      checker-M-L1 (the checker enforces a weaker law than the contract states).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "checkers" / "check_ui_contract.py"  # T104-M1 moved it (owner-facet)
TARGET = ROOT / "scripts" / "bifrost_ui.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_ui_contract", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_ui_contract"] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- T1+T2
def test_t1_t2_incumbent_verdict_and_l8_truth():
    """Run the three checks against the REAL incumbent and report, honestly labeled."""
    mod = _load()
    lines = TARGET.read_text(encoding="utf-8").split("\n")
    l8 = mod._check_raw_hex(lines)
    l1 = mod._check_gauge_axes(lines)
    l3 = mod._check_earned_accent(lines)
    print(f"\n[fence-tally] M-L8 hits on incumbent: {len(l8)}")
    for h in l8[:20]:
        print("   ", h)
    print(f"[fence-tally] M-L1 hits on incumbent: {len(l1)}")
    for h in l1[:6]:
        print("   ", h)
    print(f"[fence-tally] M-L3 hits on incumbent: {len(l3)}")
    for h in l3[:10]:
        print("   ", h)
    # The fence's own census found raw hex at call sites (hovers, badges, JS).
    # If the checker found ZERO, its L8 is blind to a real class -> fail loudly.
    assert l8, ("M-L8 found ZERO raw-hex hits on the incumbent, but the fence census "
                "(grep) finds ~15 call-site hex values (#39405a, #0a0b0f, #20232e, "
                "#0c0e14, #0b0d13, #dce0ea, #fff, #48e6bf fallbacks, #e0915c in a "
                "conic-gradient). Either the census is wrong (then delete this pin) "
                "or the checker's L8 is NOT enforcing the contract's token law.")
    print("[T1/T2] checker DOES fire on the incumbent -- the charter's "
          "'zero false positives / exits 0 tonight' claim is FALSE. Advisory rail "
          "is load-bearing.")


# ---------------------------------------------------------------- T3
def test_t3_guard_true_and_false_positive():
    mod = _load()
    dirty = ["<style>", ".x{color:#abcdef; background:var(--panel)}", "</style>"]
    clean = ["<style>", ":root{--c:#abcdef}", ".x{color:var(--c)}", "</style>"]
    d = mod._check_raw_hex(dirty)
    c = mod._check_raw_hex(clean)
    print(f"\n[T3] dirty-fixture hits: {len(d)}; clean-fixture hits: {len(c)}")
    assert d, "TRUE positive missed: raw hex at a call site was NOT flagged"
    assert not c, f"FALSE positive: token-definition + var() use flagged: {c}"


# ---------------------------------------------------------------- T4
def test_t4_l3_tripped_self_authorization():
    """'tripped' is in BOTH ALARM_CLASSES and STATE_PREDICATES -- a line whose only
    nearby predicate is the word 'tripped' itself authorizes itself."""
    mod = _load()
    lines = [
        "var cls = someCondition ? 'tripped' : 'good';",
        "el.className = 'tripped';",
    ]
    hits = mod._check_earned_accent(lines)
    print(f"\n[T4] hits on self-authorizing 'tripped' lines: {len(hits)}")
    for h in hits:
        print("   ", h)
    # line 2 has no predicate at all except the alarm word itself -> MUST flag.
    assert any("L2" in h for h in hits), (
        "L3 vacuity: 'el.className = tripped' passed because 'tripped' is its own "
        "state predicate -- the founding class is self-authorizing.")


# ---------------------------------------------------------------- T5
def test_t5_l1_enforces_weaker_law_than_contract():
    """Contract law 1 says aria-label + data-fresh; the checker checks
    data-agent + title. A gauge passing the checker can still violate the contract."""
    mod = _load()
    lines = [
        'return \'<div class="er-gauge" data-agent="kimi" title="kimi">\'+',
    ]
    hits = mod._check_gauge_axes(lines)
    print(f"\n[T5] checker hits on gauge lacking aria-label/data-fresh: {len(hits)}")
    assert not hits, "unexpected: checker flags a gauge WITH data-agent+title"
    print("[T5] CONFIRMED: checker-M-L1 is a WEAKER law than contract law 1 "
          "(no aria-label / data-fresh / unit / freshness check). The report and "
          "the docstring must name the gap or the checker overclaims.")
