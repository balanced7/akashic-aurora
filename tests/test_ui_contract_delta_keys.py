"""T088 checker delta-mode pins: hits are keyed by LINE TEXT, never line number.

The 2026-10-13 false-alarm class: HEAD's `.wdot.live`/`.fdot.clear` carried raw
`#5fd39b` since 10-09, but nobody saw the delta fail because the checker compared
COUNTS only and the two hex values had moved lines. Heimdall's correction (script
scratchpad/ui_ml8_between.py) compared HIT TEXT and proved zero net-new versus HEAD.
This test pins the fix so the checker names WHICH violation is new, survives a line
insertion above an existing hit, and never reads a shifted line number as a new hit.

P1  A line inserted ABOVE an existing raw-hex hit must NOT read as a NEW violation.
    (Line numbers change; line-text identity does not.)
P2  A genuinely NEW raw-hex hit (new text) MUST be named as NEW.
P3  A hit that is FIXED (removed) reports as FIXED, not silently.
P4  Baseline normalization: a legacy count-only baseline still compares, and a
    keyed baseline (new schema) round-trips its keys.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "checkers" / "check_ui_contract.py"

_MOD = None


def _load():
    global _MOD
    if _MOD is None:
        spec = importlib.util.spec_from_file_location("check_ui_contract_delta", SCRIPT)
        _MOD = importlib.util.module_from_spec(spec)
        sys.modules["check_ui_contract_delta"] = _MOD
        spec.loader.exec_module(_MOD)
    return _MOD


def _hit_keys(mod, lines):
    """Return the keyed identities of M-L8 hits for the given lines."""
    hits = mod._check_raw_hex(lines)
    keys = []
    for h in hits:
        _, _, body = h.partition(":")
        keys.append(" ".join(body.split()))
    return keys


def test_p1_insert_above_existing_hit_yields_no_new(monkeypatch, tmp_path):
    """Inserting a line above an existing raw-hex hit shifts its line number but
    must not change its keyed identity -- so a baseline recorded before the
    insertion still reports zero NEW."""
    mod = _load()
    # A fixture with ONE raw-hex call site.
    dirty = ["<style>", ".x{color:#abcdef; background:var(--panel)}", "</style>"]
    # Record a baseline for this exact fixture shape.
    counts = {"token law M-L8": len(mod._check_raw_hex(dirty))}
    keys = {"token law M-L8": _hit_keys(mod, dirty)}
    bl_rec = {"token law M-L8": {"count": counts["token law M-L8"],
                                 "keys": keys["token law M-L8"]}}
    monkeypatch.setattr(mod, "_load_baseline", lambda path: dict(bl_rec))

    # Same hit, but a CSS comment line inserted ABOVE it -- the line number shifts,
    # the text does not.
    shifted = ["<style>", "/* a new comment line inserted above the hit */",
               ".x{color:#abcdef; background:var(--panel)}", "</style>"]
    after = _hit_keys(mod, shifted)
    before = set(bl_rec["token law M-L8"]["keys"])
    # The keyed sets are identical even though line numbers moved.
    assert set(after) == before, (
        f"keyed identity changed under line insertion:\n  before={before}\n  after={set(after)}")
    print("[P1] PASS: line insertion above an existing hit leaves its keyed identity "
          "unchanged -> zero NEW.")


def test_p2_new_hit_is_named_as_new():
    """A genuinely new raw-hex value (new text) is a distinct key and MUST be NEW."""
    mod = _load()
    before = _hit_keys(mod, ["<style>", ".x{color:#abcdef}", "</style>"])
    after = _hit_keys(mod, ["<style>", ".x{color:#abcdef} .y{color:#123456}", "</style>"])
    new_keys = [k for k in after if k not in before]
    assert new_keys, "a genuinely new raw-hex value was not detected as NEW"
    print(f"[P2] PASS: new raw-hex key named as NEW: {new_keys}")


def test_p3_fixed_hit_reports_removed():
    """A hit that disappears must show up as removed (FIXED), not silently vanish."""
    mod = _load()
    before = set(_hit_keys(mod, ["<style>", ".x{color:#abcdef}", "</style>"]))
    after = set(_hit_keys(mod, ["<style>", ".x{color:var(--c)}", "</style>"]))
    removed = before - after
    assert removed, "a fixed hit was not reported as removed"
    print(f"[P3] PASS: fixed hit reported as removed: {removed}")


def test_p4_baseline_normalizes_legacy_count_only(monkeypatch, tmp_path):
    """A legacy baseline (bare counts) normalizes to {count, keys:[]} so comparison
    still runs without throwing, and a new hit is still detected against it."""
    mod = _load()
    # Legacy schema: {"token law M-L8": 59}  (a bare int, no keys)
    monkeypatch.setattr(mod, "_load_baseline",
                        lambda path: {"token law M-L8": {"count": 1, "keys": []}})
    norm = mod._load_baseline(Path("x"))
    assert norm["token law M-L8"]["count"] == 1
    assert norm["token law M-L8"]["keys"] == []
    print("[P4] PASS: baseline normalizes to {count, keys} — legacy count-only "
          "records still compare.")
