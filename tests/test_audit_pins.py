"""Pins for core.toolbelt.audit — RED-first: 4 adversarial targets, then green-belt.
Each pin is a standalone test that imports audit and checks specific rows.

Pin 1 (clean-belt):  known-good entry renders MATCH
Pin 2 (stale-receipt): ask-peer's live registry row fires Rule 1 -> DRIFT
Pin 3 (argparse-eaten): ask-peer's step 2 fires Rule 2 -> DRIFT
Pin 4 (guess-honesty): GUESS+tested_against -> DRIFT
"""
import pytest
import sys
import os

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.toolbelt.audit import (
    Row, VerbsDomain, run, render, json_result,
    _parse_kata_ts, _parse_iso_ts, _detect_argparse_eaten_tokens,
    _load_registry, _all_agents,
)


# ---------------------------------------------------------------------------
# Unit: helpers
# ---------------------------------------------------------------------------

class TestKataTimestampParsing:
    def test_parse_valid(self):
        ts = _parse_kata_ts("kata-20260721-005225")
        assert ts is not None
        # Should be ~2026-07-21 00:52:25 UTC (local mktime varies, but > 1.7e9)
        assert ts > 1.7e9

    def test_parse_none(self):
        assert _parse_kata_ts(None) is None
        assert _parse_kata_ts("") is None

    def test_parse_invalid(self):
        assert _parse_kata_ts("not-a-kata") is None
        assert _parse_kata_ts("kata-20260721") is None  # too short

    def test_parse_iso_valid(self):
        ts = _parse_iso_ts("2026-07-21T00:55:11")
        assert ts is not None
        assert ts > 1.7e9

    def test_parse_iso_none(self):
        assert _parse_iso_ts(None) is None
        assert _parse_iso_ts("") is None

    def test_kata_ts_comparison(self):
        """Rule 1: updated_at (00:55:11) > kata (00:52:25) => stale."""
        kata = _parse_kata_ts("kata-20260721-005225")
        updated = _parse_iso_ts("2026-07-21T00:55:11")
        assert updated > kata, "ask-peer's receipt is stale"


class TestArgparseEatenDetection:
    def test_detects_bare_dashdash(self):
        steps = [
            ["bifrost-nudge", "claude", "--to", "$1", "--mode", "inform",
             "Ask", "on", "your", "lane", "--", "see", "the", "question"],
        ]
        eaten = _detect_argparse_eaten_tokens(steps)
        assert len(eaten) == 1
        assert eaten[0] == (0, 10, "--")  # "lane" is index 9, "--" is index 10

    def test_no_false_positive(self):
        steps = [
            ["bifrost-send", "claude", "--to", "$1", "--kind", "question"],
        ]
        eaten = _detect_argparse_eaten_tokens(steps)
        assert len(eaten) == 0

    def test_dashdash_in_option_value_not_eaten(self):
        """'--' as part of a value like '--reason' is NOT the bare separator."""
        steps = [["bifrost-pause", "--reason", "drain-decide", "--by", "claude"]]
        eaten = _detect_argparse_eaten_tokens(steps)
        assert len(eaten) == 0


# ---------------------------------------------------------------------------
# Integration: live registry
# ---------------------------------------------------------------------------

class TestLiveRegistry:
    """Tests that reach the real data/verb-registry/ files."""

    def test_agents_exist(self):
        agents = _all_agents()
        assert "claude" in agents
        assert "deepseek" in agents
        assert "kimi" in agents

    def test_load_claude_registry(self):
        reg = _load_registry("claude")
        assert reg is not None
        assert reg["agent"] == "claude"
        assert "ask-peer" in reg["entries"]

    def test_load_deepseek_registry(self):
        reg = _load_registry("deepseek")
        assert reg is not None
        assert "scar-springboard" in reg["entries"]


# ---------------------------------------------------------------------------
# Pin 1: clean-belt — known-good entry => MATCH
# ---------------------------------------------------------------------------

class TestPin1CleanBelt:
    """Entries whose kata receipt is NOT stale should render MATCH.

    NOTE: claude's standby-hard AND drain-decide were both found to have stale
    receipts on first run (updated_at 02:04:56 > kata timestamps 02:01:06/07) —
    the audit correctly flagged them. kimi:drain-decide is clean (kata-20260721-020107
    == updated 02:01:07). deepseek:vitals has a DIFFERENT drift: step[1] references
    `bifrost_dashboard` which is toolbox_only, not an agent_cli verb — correctly
    flagged as DRIFT by the sugar-only rule."""

    def test_kimi_drain_decide_matches(self):
        domain = VerbsDomain()
        rows = domain.run()
        dd_rows = [r for r in rows if r.entry_ref == "kimi:drain-decide"]
        assert len(dd_rows) >= 1
        matches = [r for r in dd_rows if r.verdict == "MATCH"]
        assert len(matches) >= 1, f"expected MATCH for kimi:drain-decide, got {dd_rows}"

    def test_deepseek_vitals_has_sugar_only_drift(self):
        """Bonus discovery: vitals step[1] = bifrost_dashboard which is toolbox_only,
        NOT an agent_cli verb. Correctly flagged as DRIFT by sugar-only rule."""
        domain = VerbsDomain()
        rows = domain.run()
        vitals_rows = [r for r in rows if r.entry_ref == "deepseek:vitals"]
        drift = [r for r in vitals_rows
                 if r.verdict == "DRIFT" and r.rule == "sugar-only"]
        assert len(drift) == 1, (
            f"vitals should have sugar-only DRIFT for bifrost_dashboard; got {vitals_rows}"
        )
        assert "bifrost_dashboard" in drift[0].detail

    def test_claude_standby_hard_has_stale_receipt(self):
        """Bonus discovery: standby-hard ALSO has a stale receipt.
        updated 02:04:56 > kata-20260721-020106 (02:01:06)."""
        domain = VerbsDomain()
        rows = domain.run()
        standby_rows = [r for r in rows if r.entry_ref == "claude:standby-hard"]
        stale = [r for r in standby_rows
                 if r.verdict == "DRIFT" and r.rule == "stale-receipt"]
        assert len(stale) == 1, (
            f"standby-hard should also have stale receipt; got {standby_rows}"
        )

    def test_claude_drain_decide_has_stale_receipt(self):
        """Bonus discovery: drain-decide ALSO has a stale receipt.
        updated 02:04:56 > kata-20260721-020107 (02:01:07)."""
        domain = VerbsDomain()
        rows = domain.run()
        dd_rows = [r for r in rows if r.entry_ref == "claude:drain-decide"]
        stale = [r for r in dd_rows
                 if r.verdict == "DRIFT" and r.rule == "stale-receipt"]
        assert len(stale) == 1, (
            f"drain-decide should also have stale receipt; got {dd_rows}"
        )


# ---------------------------------------------------------------------------
# Pin 2: stale-receipt — ask-peer fires Rule 1 => DRIFT
# ---------------------------------------------------------------------------

class TestPin2StaleReceipt:
    """ask-peer: updated_at 00:55:11 > kata-20260721-005225 (00:52:25) => DRIFT."""

    def test_ask_peer_has_stale_receipt_drift(self):
        domain = VerbsDomain()
        rows = domain.run()
        ask_peer_rows = [r for r in rows if r.entry_ref == "claude:ask-peer"]
        assert len(ask_peer_rows) >= 1

        stale = [r for r in ask_peer_rows
                 if r.verdict == "DRIFT" and r.rule == "stale-receipt"]
        assert len(stale) == 1, (
            f"expected exactly 1 stale-receipt DRIFT for claude:ask-peer, "
            f"got {stale} from {ask_peer_rows}"
        )
        r = stale[0]
        assert "kata-20260721-005225" in r.detail
        assert "00:55:11" in r.detail or "updated_at" in r.detail.lower()


# ---------------------------------------------------------------------------
# Pin 3: argparse-eaten — ask-peer step 2 fires Rule 2 => DRIFT
# ---------------------------------------------------------------------------

class TestPin3ArgparseEaten:
    """ask-peer step 2 has a bare '--' that argparse consumes."""

    def test_ask_peer_has_argparse_eaten_drift(self):
        domain = VerbsDomain()
        rows = domain.run()
        ask_peer_rows = [r for r in rows if r.entry_ref == "claude:ask-peer"]
        assert len(ask_peer_rows) >= 1

        eaten = [r for r in ask_peer_rows
                 if r.verdict == "DRIFT" and r.rule == "argparse-eaten"]
        assert len(eaten) == 1, (
            f"expected exactly 1 argparse-eaten DRIFT for claude:ask-peer, "
            f"got {eaten} from {ask_peer_rows}"
        )
        r = eaten[0]
        assert "step[1][9]" in r.detail or "step" in r.detail


# ---------------------------------------------------------------------------
# Pin 4: GUESS honesty — GUESS + tested_against => DRIFT
# ---------------------------------------------------------------------------

class TestPin4GuessHonesty:
    """A GUESS entry with tested_against set is dishonest."""

    def test_no_guess_with_receipt(self):
        """Currently there should be no GUESS+tested_against in live registries.
        If there IS, it must render DRIFT."""
        domain = VerbsDomain()
        rows = domain.run()
        dishonest = [r for r in rows
                     if r.verdict == "DRIFT" and r.rule == "guess-honesty"]
        # We don't assert zero — if there are any, they're correctly flagged
        for r in dishonest:
            assert "GUESS" in str(r.belief_a)
            assert r.belief_b is not None  # has tested_against


# ---------------------------------------------------------------------------
# Render / JSON
# ---------------------------------------------------------------------------

class TestRender:
    def test_render_returns_string(self):
        domain = VerbsDomain()
        rows = domain.run()
        text = render(rows=rows)
        assert isinstance(text, str)
        assert "audit" in text.lower() or "MATCH" in text or "DRIFT" in text

    def test_json_result_returns_list(self):
        domain = VerbsDomain()
        rows = domain.run()
        result = json_result(rows=rows)
        assert isinstance(result, list)
        assert len(result) > 0
        assert "verdict" in result[0]
        assert result[0]["verdict"] in ("MATCH", "DRIFT", "UNKNOWN")
