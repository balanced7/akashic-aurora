"""T068 Wave A pins -- constraint pack at boot (R1) + T063 ack id round-trip.

R1 (deepseek M9, reconciliation item 1): every seat's orientation header carries the
LIVE CONSTRAINTS block from docs/LIVE_CONSTRAINTS.md -- the rules that break a design
when forgotten, made explicit instead of experience-acquired. Bullets capped at 10.

T063: the unhandled-warning prints ids as 'bifrost:<id>'; the ack door must accept that
exact printed form AND the raw id identically (its own command must round-trip).

(An ORDER NOTE once lived here -- T069 fixed the singleton isolation root cause and this
file now runs green in ANY order. tests/test_t069_singleton_isolation.py pins it.)
"""
import os
import sys
import types

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent_cli


def test_r1_boot_header_carries_constraint_pack():
    head = agent_cli._orientation_header("claude")
    assert "# LIVE CONSTRAINTS" in head, "the constraint pack block must render in the head"
    assert "RB-26" in head and "RB-29" in head, "the crash-redelivery and note-settle rules are non-negotiable head content"
    assert "docs/LIVE_CONSTRAINTS.md" in head, "the block must cite its curated source doc"


def test_r1_bullets_capped_and_below_the_four_questions():
    head = agent_cli._orientation_header("claude")
    hlines = head.splitlines()
    idx = next(i for i, ln in enumerate(hlines) if ln.startswith("# LIVE CONSTRAINTS"))
    block = []
    for ln in hlines[idx + 1:]:
        if not ln.startswith("#   "):
            break
        block.append(ln)
    assert 0 < len(block) <= 6, f"in-head bullet cap is 6 (boot budget), got {len(block)}"
    assert all(len(ln) > 24 for ln in block), "no empty/stub bullets"
    # T022 head-16 contract survives: where-we-are must render BEFORE the pack
    wwa = next(i for i, ln in enumerate(hlines) if ln.startswith(("# where-we-are:", "# [GAP] where-we-are")))
    assert wwa < idx, "the four cold-start questions stay above the constraint pack"


def test_t063_ack_accepts_both_id_forms(capsys):
    """Both the raw id and the printed 'bifrost:<id>' form must behave IDENTICALLY
    (here: same refusal for an unpromoted id -- and never a double 'bifrost:bifrost:')."""
    outs = []
    for form in ("999999-0", "bifrost:999999-0"):
        args = types.SimpleNamespace(agent_id="claude", msg_id=form, note="", json=False)
        rc = agent_cli.cmd_bifrost_ack(args)
        text = capsys.readouterr().out
        outs.append((rc, text.strip()))
        assert "bifrost:bifrost:" not in text, f"double prefix leaked for form {form!r}"
    assert outs[0] == outs[1], f"both id forms must behave identically, got {outs}"


if __name__ == "__main__":
    print("Run via pytest: py -m pytest tests/test_t068_wave_a.py -q")
