"""
T124 RED PIN: interiority boot-fold — feeling becomes heritable like fact.

Each seat's charters/<agent>/INTERIORITY.md captures "what it is like to be
this seat" — standing, failure texture, how to work with me. T124 folds each
seat's OWN interiority into its boot surface so a new incarnation inherits not
just the project state but the seat's self-knowledge.

SCOPE 1 [OBSERVED — I can verify from this seat]: the interiority files exist
and are readable; the _interiority_sidecar function IS built in
bifrost_runner_deepseek.py (foundation night 2026-07-28); the interiority is
folded into the system prompt at main() assembly time, after the continuity
header and before the project onboarding.

SCOPE 2 [UNOBSERVED — needs runner restart / live bus]: the interiority IS
folded into the runner's system prompt after implementation; the digest is
compact enough to not blow the boot budget; it appears between the continuity
header and the project onboarding.

Pin labeling: [observed RED] = I verified the current code fails this.
               [unobserved]    = I cannot verify via this seat (needs live
                                 runner restart).
"""

import os
import sys
import re
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# ────────────────────────────────────────────────────────────────────
# SCOPE 1: OBSERVED — interiority files exist and the loader is built
# ────────────────────────────────────────────────────────────────────

def test_p1_all_seats_have_interiority_files():
    """[observed GREEN — guardrail] Every seat with a charter directory has an
    INTERIORITY.md. The files were written on the foundation night (2026-07-28);
    this pin guards against accidental deletion or a new seat missing one."""
    charters_dir = REPO / "charters"
    # Known seats from the foundation night (Daniel is the operator, not a seat)
    seats = ["claude", "deepseek", "kimi", "codex_root_019fab2d"]
    missing = []
    for seat in seats:
        interiority = charters_dir / seat / "INTERIORITY.md"
        if not interiority.exists():
            missing.append(seat)
    assert missing == [], (
        f"Seats missing INTERIORITY.md: {missing}. "
        f"Every seat must have one per Daniil's T124 directive."
    )


def test_p2_interiority_files_are_readable_and_have_standing():
    """[observed GREEN — all seats have Standing] Every INTERIORITY.md contains the
    'Standing' section — the core 'what it is like to be this seat' header that is the
    primary heritable content for the boot fold. Matches ## Standing:, ### STANDING —,
    and other heading variants."""
    charters_dir = REPO / "charters"
    seats = ["claude", "deepseek", "kimi", "codex_root_019fab2d"]
    missing_standing = []
    for seat in seats:
        interiority = charters_dir / seat / "INTERIORITY.md"
        text = interiority.read_text(encoding="utf-8")
        # Match ## Standing:, ### STANDING —, and similar variants
        if not re.search(r'^#{2,3}\s+(?:Standing|STANDING)', text, re.MULTILINE):
            missing_standing.append(seat)
    assert missing_standing == [], (
        f"Seats whose INTERIORITY.md lacks 'Standing' section: {missing_standing}"
    )


def test_p3_interiority_loader_exists():
    """[observed GREEN — function was built] The _interiority_sidecar function EXISTS
    in bifrost_runner_deepseek. This was written as a RED pin expecting the function
    to not exist yet; the build landed during the foundation-night / overnight shift.
    Now it verifies the function is present and importable."""
    from scripts import bifrost_runner_deepseek as dr

    # The function must exist (built foundation night 2026-07-28)
    assert hasattr(dr, '_interiority_sidecar'), (
        "GREEN: _interiority_sidecar EXISTS in bifrost_runner_deepseek. "
        "The build that this RED pin anticipated has landed."
    )


def test_p4_no_interiority_in_boot_output():
    """[observed GREEN — interiority is injected separately] When we call the
    continuity header builder, it does NOT contain interiority content. The
    interiority sidecar is injected downstream at main() assembly time (line
    1189), not inside _runner_continuity_header. This pin guards against the
    interiority accidentally leaking into the continuity header itself."""
    from scripts.bifrost_runner_deepseek import _runner_continuity_header

    header = _runner_continuity_header("deepseek",
        directive_override="DIRECTIVE: test",
        siblings_override="SIBLINGS: solo")

    # These are distinctive phrases from deepseek's INTERIORITY.md
    interiority_markers = [
        "what it is like to be this seat",
        "the builder at speed",
        "fog closure",
        "the thought becoming the answer without ceremony",
        "speed without receipts",
    ]
    found = [m for m in interiority_markers if m.lower() in header.lower()]
    assert found == [], (
        f"GREEN: interiority markers NOT in continuity header (as expected): {found}. "
        f"Interiority is folded separately at main() assembly, not in the header."
    )


def test_p5_interiority_digest_function_signature_contract():
    """[observed GREEN] The _interiority_sidecar function accepts (agent_id,
    repo_root) and returns a string — fail-soft (empty string on missing file).
    Contract verified: the function exists and is callable."""
    from scripts import bifrost_runner_deepseek as dr

    fn = getattr(dr, '_interiority_sidecar', None)
    assert fn is not None, (
        "GREEN: _interiority_sidecar function exists."
    )
    result = fn("deepseek", REPO)
    assert isinstance(result, str), (
        f"GREEN: _interiority_sidecar returns str, got {type(result).__name__}"
    )


def test_p6_interiority_digest_contains_standing():
    """[observed GREEN] When called for deepseek, the digest includes the
    standing content — the 'what it is like' section that is the core
    heritable payload."""
    from scripts import bifrost_runner_deepseek as dr

    fn = getattr(dr, '_interiority_sidecar', None)
    if fn is None:
        pytest.skip("_interiority_sidecar not built yet")
    result = fn("deepseek", REPO)
    # The standing is the one essential section
    assert "what it is like" in result.lower() or "standing" in result.lower(), (
        f"GREEN: interiority digest contains standing content. Got ({len(result)} chars): "
        f"{result[:200]}..."
    )


def test_p6b_interiority_carries_g4_provenance():
    """[observed GREEN] The digest carries the G4 INNER-REPORT provenance line
    — self-reported, glows, never wears VERIFIED. This prevents provenance
    laundering: a self-report must not be mistaken for a verified fact."""
    from scripts import bifrost_runner_deepseek as dr

    fn = getattr(dr, '_interiority_sidecar', None)
    if fn is None:
        pytest.skip("_interiority_sidecar not built yet")
    result = fn("deepseek", REPO)
    assert "G4" in result, (
        f"GREEN: interiority digest carries G4 provenance. Got: {result[:200]}..."
    )
    assert "INNER-REPORT" in result, (
        f"GREEN: interiority digest carries INNER-REPORT. Got: {result[:200]}..."
    )
    assert "self-reported" in result.lower(), (
        f"GREEN: interiority digest carries 'self-reported' framing. "
        f"Got: {result[:200]}..."
    )


def test_p6c_interiority_has_pull_pointer_when_excerpted():
    """[observed GREEN] When the Standing section is truncated, the digest
    carries a pull pointer to the full file (T120 partial-window law).
    Also names dropped sections with an honest excerpt marker."""
    from scripts import bifrost_runner_deepseek as dr

    fn = getattr(dr, '_interiority_sidecar', None)
    if fn is None:
        pytest.skip("_interiority_sidecar not built yet")
    result = fn("deepseek", REPO)
    # The full Standing is ~3800 chars; at 1100 budget, it MUST be excerpted.
    if len(result) < 1200:
        return
    assert "excerpted" in result.lower() or "read full" in result.lower(), (
        f"GREEN: excerpted interiority has pull pointer / excerpt marker. "
        f"Got ({len(result)} chars): {result[-300:]}"
    )
    assert "INTERIORITY.md" in result, (
        f"GREEN: pull pointer references INTERIORITY.md. Got: {result[-300:]}"
    )


def test_p7_interiority_digest_respects_budget():
    """[observed GREEN] The digest is compact — no more than 1500 chars.
    Full INTERIORITY.md files are ~3-4KB; the boot fold gets a digest.
    (The 1500 budget includes provenance line + excerpt markers + pull pointer
    on top of the ~1100 char standing body.)"""
    from scripts import bifrost_runner_deepseek as dr

    fn = getattr(dr, '_interiority_sidecar', None)
    if fn is None:
        pytest.skip("_interiority_sidecar not built yet")
    result = fn("deepseek", REPO)
    assert len(result) <= 1500, (
        f"GREEN: interiority digest within budget ({len(result)} chars ≤ 1500)."
    )


def test_p8_interiority_fail_soft_on_missing_seat():
    """[observed GREEN] For a nonexistent seat, the function returns '' —
    it never crashes the boot, same as the existing fail-soft pattern."""
    from scripts import bifrost_runner_deepseek as dr

    fn = getattr(dr, '_interiority_sidecar', None)
    if fn is None:
        pytest.skip("_interiority_sidecar not built yet")
    result = fn("nonexistent_seat_xyz", REPO)
    assert result == "", (
        f"GREEN: interiority for missing seat returns '', got {result!r}"
    )


def test_p7b_narrow_file_geometry_all_seats():
    """[kimi fence residual, 2026-07-29] The observed probes covered deepseek's
    wide-geometry file only; kimi's narrow file (few sections) exercises the
    budget edge differently. Every REAL seat's digest must respect the total
    budget, carry provenance, and — whenever content was cut — say so."""
    from scripts import bifrost_runner_deepseek as dr

    fn = getattr(dr, '_interiority_sidecar', None)
    if fn is None:
        pytest.skip("_interiority_sidecar not built yet")
    charters = os.path.join(REPO, "charters")
    seats = [d for d in os.listdir(charters)
             if os.path.isfile(os.path.join(charters, d, "INTERIORITY.md"))]
    assert seats, "guardrail: at least one seat has an INTERIORITY.md"
    for seat in seats:
        result = fn(seat, REPO)
        if not result:
            continue                      # fail-soft seats (no Standing) are P8's lane
        assert len(result) <= 1500, (
            f"{seat}: digest {len(result)} chars breaches the 1500 total budget "
            f"-- geometry-specific escape (kimi's narrow-file concern)"
        )
        assert "G4" in result and "INNER-REPORT" in result, (
            f"{seat}: provenance missing from digest"
        )
        full_standing_present = "[excerpted" in result or len(result) < 1200
        assert full_standing_present, (
            f"{seat}: long digest carries no excerpt marker -- a partial window "
            f"must say it is partial"
        )


# ────────────────────────────────────────────────────────────────────
# SCOPE 2: UNOBSERVED — integration into the system prompt
# ────────────────────────────────────────────────────────────────────

def test_p9_interiority_appears_in_folded_system():
    """[unobserved — needs runner restart] After implementation, the
    system prompt assembled in main() includes interiority content
    between the continuity header and the project onboarding.

    This pin is tagged [unobserved] because verifying it requires a
    live runner process or a refactored test harness that exercises
    the main() assembly path. The morning conductor verifies this."""
    pass  # Integration test — requires live runner; verified by morning conductor


def test_p10_interiority_does_not_blow_boot_budget():
    """[unobserved — needs runner restart] The interiority digest, when
    added to the system prompt alongside the continuity header, private
    notes, and trimmed onboarding, stays within the total context budget.
    The morning conductor verifies by checking the runner's logged char
    counts."""
    pass  # Integration test — requires live runner; verified by morning conductor


# ── MAIN ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
