"""T121/F3 post-dogfood regression pins for the first rendered surface.

The pre-registered contract and glyph batteries both passed while the composed
surface was still broken: ``_fmt`` kept typed evidence under ``meta`` but never
attached the top-level ``m.epistemic`` object that ``epiGlyph`` consumes.

This file does not pretend that discovery was pre-registered.  It preserves the
observed RED -> GREEN flip so the Python-to-JavaScript seam cannot silently
disappear again.
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.bifrost_ui import _fmt


ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "scripts" / "bifrost_ui.py"


def _fields(*, meta, ts="2026-07-29T01:45:00Z"):
    return {
        "frm": "codex_root_019fab2d",
        "to": "kimi",
        "kind": "inform",
        "content": json.dumps("typed contract payload"),
        "ts": ts,
        "meta": json.dumps(meta),
    }


def test_fmt_attaches_the_normalized_epistemic_product():
    message = _fmt(
        "1785289199397-0",
        _fields(
            meta={
                "epistemic": {
                    "claim_kind": {
                        "value": "inferred",
                        "basis": ["dogfood:claim"],
                    },
                    "currency": {
                        "value": "current",
                        "basis": ["dogfood:lifecycle"],
                    },
                }
            }
        ),
    )

    assert message["epistemic"]["claim_kind"] == {
        "value": "inferred",
        "basis": [{"ref": "dogfood:claim", "status": "recorded"}],
    }
    assert message["epistemic"]["currency"] == {
        "value": "current",
        "basis": [{"ref": "dogfood:lifecycle", "status": "recorded"}],
    }
    assert message["epistemic"]["authority"] == {
        "value": "unknown",
        "basis": [],
    }


def test_fresh_transport_timestamp_without_evidence_stays_unknown():
    message = _fmt(
        "1785289494862-0",
        _fields(meta={}, ts="2026-07-29T01:58:14Z"),
    )

    assert message["epistemic"]["currency"] == {
        "value": "unknown",
        "basis": [],
    }
    assert message["epistemic"]["claim_kind"] == {
        "value": "unknown",
        "basis": [],
    }


def test_glyph_block_consumes_only_the_typed_product_not_age_or_flat_meta():
    source = UI.read_text(encoding="utf-8")
    start = source.index("function epiGlyph(m)")
    end = source.index("const allMsgs", start)
    block = source[start:end]

    assert "m.epistemic" in block
    assert "m.ts" not in block
    assert "meta.currency" not in block
    assert "meta.claim_kind" not in block
    assert "EPI_TIER_HOURS" not in block

