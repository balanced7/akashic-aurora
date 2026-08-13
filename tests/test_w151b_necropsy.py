"""W151b pins: the necropsy organ -- unclean deaths detected, then distilled.

Arc: disaster-proofing, Slice 1b (fence-reconciled: claude build, Navi reviews,
Heimdall cross-weights). Lineage: the 2026-08-13 hand-salvage of two crashed
sessions proved the flow; the ad-hoc census found BOTH known disasters (the
shader crash and the reboot massacre trio) on its first breath. This slice
promotes heroics to organ.

The detection law (validated live): a session died UNCLEAN when its transcript
exists and is recent, no tombstone was ever written (clean deaths tombstone at
SessionEnd), and nothing about the session is live (no seat, no fresh marker).

Pins cover the PURE census classifier and the distiller's text digestion.
The LLM half of distillation (the death-delta ask) is a grounded-ask passthrough,
unpinned here -- its honesty comes from the ask door's own contract.
"""
import time

from types import SimpleNamespace as SN

from scripts.necropsy import classify_session, digest_transcript_text


NOW = 1_800_000_000.0
H = 3600.0


def _c(**kw):
    d = dict(transcript_mtime=NOW - 5 * H, tombstoned=False, seat_exists=False,
             marker_age_min=None, window_h=72.0, now=NOW)
    d.update(kw)
    return classify_session(**d)


def test_n1_unclean_death_detected():
    """The 08-12 shape: recent transcript, no tombstone, nothing live."""
    assert _c() == "unclean"


def test_n2_clean_death_is_not_a_candidate():
    """A tombstone means SessionEnd ran -- the death was clean, nothing to distill."""
    assert _c(tombstoned=True) == "clean"


def test_n3_live_sessions_are_never_candidates():
    """A seat file or a fresh activity marker = the session LIVES. A necropsy on
    a live patient is the wrongness-detection failure class, not a feature."""
    assert _c(seat_exists=True) == "live"
    assert _c(marker_age_min=5.0) == "live"


def test_n4_old_transcripts_age_out_of_the_window():
    """Beyond the window the tombstone signal is unreliable (Redis leg TTL,
    tempdir wipes) -- refuse to classify rather than guess. Honesty over reach."""
    assert _c(transcript_mtime=NOW - 100 * H) == "out-of-window"


def test_n5_stale_marker_does_not_confer_life():
    assert _c(marker_age_min=90.0) == "unclean"


def test_n6_digest_extracts_the_layers_a_savepoint_needs():
    """The distiller's text half: user words, assistant text, tool calls --
    chronological, labeled, clipped. (Port of the 08-13 salvage script that
    recovered the shader session, now with a contract.)"""
    lines = [
        '{"type":"user","timestamp":"2026-08-12T23:31:24.000Z","message":{"content":"Shader work sounds like fun!"}}',
        '{"type":"assistant","timestamp":"2026-08-12T23:31:51.000Z","message":{"content":[{"type":"text","text":"Fun direction, and a good bit of groundwork."}]}}',
        '{"type":"assistant","timestamp":"2026-08-12T23:32:17.000Z","message":{"content":[{"type":"tool_use","name":"WebFetch","input":{"url":"https://www.shadertoy.com/howto"}}]}}',
        'not json at all',
    ]
    rows = digest_transcript_text("\n".join(lines))
    kinds = [r[1] for r in rows]
    assert kinds == ["USER", "ASST", "TOOL"]
    assert "Shader work sounds like fun!" in rows[0][2]
    assert "WebFetch" in rows[2][2] and "shadertoy.com" in rows[2][2]


def test_n7_digest_never_raises_on_garbage():
    assert digest_transcript_text("") == []
    assert digest_transcript_text("{broken\njson}\n123") == []
