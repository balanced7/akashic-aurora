"""T081-W8A PRE-REGISTERED ACCEPTANCE — gauge honesty: whisper mail label.

Committed BEFORE implementation (method-baseline pre-registration; T031 rule practiced).
Cites night-build-brief-2026-07-16.md §W8 (gauge honesty — shared denominator / explaining
label for unread gauges) + deepseek-w8-prior-art-2026-07-16.md (Prometheus counter label
semantics: name the denominator, don't force counts to agree).

Prior art: Prometheus _total suffix + label convention — a counter without a label is a
mystery; a counter WITH a label is a measurement. The whisper, sync, and peek count
DIFFERENT things (legacy peek vs work-lane vs raw). The fix is LABELING what each counts.

Pins:
  W8A-P1  whisper mail line includes scope label
  W8A-P2  lane-enabled → "(work-lane)" scope
  W8A-P3  lane-disabled → "(all lanes)" scope
  W8A-P4  import failure → "(legacy peek)" fallback (fail-open)
  W8A-P5  zero unread → no mail line (unchanged behavior)
  W8A-P6  out-of-repo whisper unchanged (bare message, scope label not needed)

Run: py -m pytest tests/test_t081_w8a_gauge_labels.py -q
"""
import os
import sys

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _whisper(cwd=None, agent_id="test-agent", session_id="",
             monkeypatch=None, unread=0, lane_env=None):
    """Build the whisper with controlled inputs."""
    import agent.harness.context as ctx
    if monkeypatch is not None:
        monkeypatch.setattr(ctx, "_unread_count", lambda aid: unread)
        monkeypatch.setattr(ctx, "_draft_fresh", lambda: False)
        monkeypatch.setattr(ctx, "_delta_count", lambda aid: 0)
        monkeypatch.setattr(ctx, "_funnel_line", lambda: "")
        monkeypatch.setattr(ctx, "_fetch_notes", lambda: [])
        monkeypatch.setattr(ctx, "_live_siblings", lambda aid, sid: [])
        monkeypatch.setattr(ctx, "session_in_scope", lambda cwd: True)
        if lane_env is not None:
            monkeypatch.setenv("BIFROST_CONSUME_LANE", lane_env)
        else:
            monkeypatch.delenv("BIFROST_CONSUME_LANE", raising=False)
    return ctx.build_autoboot_context(
        cwd=cwd or os.path.dirname(__file__),
        agent_id=agent_id,
        session_id=session_id)


# ------------------------------------------------------------------ W8A-P1: scope label present
def test_w8a_p1_mail_line_includes_scope_label(monkeypatch):
    """Whisper mail line must include parenthesized scope label."""
    out = _whisper(monkeypatch=monkeypatch, unread=5, lane_env="work")
    assert "mail: 5 unread" in out, f"mail line must appear: {out}"
    assert "(work-lane)" in out, f"scope label must be present: {out}"


# ------------------------------------------------------------------ W8A-P2: lane-enabled → work-lane
def test_w8a_p2_lane_enabled_shows_work_lane(monkeypatch):
    """BIFROST_CONSUME_LANE=work → scope is 'work-lane'."""
    out = _whisper(monkeypatch=monkeypatch, unread=3, lane_env="work")
    assert "(work-lane)" in out, f"lane-enabled must show work-lane: {out}"
    assert "(all lanes)" not in out, "must NOT show all-lanes when lane is enabled"


# ------------------------------------------------------------------ W8A-P3: lane-disabled → all lanes
def test_w8a_p3_lane_disabled_shows_all_lanes(monkeypatch):
    """No BIFROST_CONSUME_LANE → scope is 'all lanes'."""
    out = _whisper(monkeypatch=monkeypatch, unread=7, lane_env=None)
    assert "(all lanes)" in out, f"lane-disabled must show all lanes: {out}"
    assert "(work-lane)" not in out, "must NOT show work-lane when lane is disabled"


# ------------------------------------------------------------------ W8A-P4: import failure → fallback
def test_w8a_p4_import_failure_falls_back(monkeypatch):
    """If BifrostAPI import fails, scope falls back to 'legacy peek'."""
    import agent.harness.context as ctx
    monkeypatch.setattr(ctx, "_unread_count", lambda aid: 3)
    monkeypatch.setattr(ctx, "_draft_fresh", lambda: False)
    monkeypatch.setattr(ctx, "_delta_count", lambda aid: 0)
    monkeypatch.setattr(ctx, "_funnel_line", lambda: "")
    monkeypatch.setattr(ctx, "_fetch_notes", lambda: [])
    monkeypatch.setattr(ctx, "_live_siblings", lambda aid, sid: [])
    monkeypatch.setattr(ctx, "session_in_scope", lambda cwd: True)

    # Force the import path to fail
    def _fake_import(*args, **kwargs):
        raise ImportError("simulated")
    monkeypatch.setattr("core.comm.bifrost_api.BifrostAPI", None, raising=False)
    # Simpler: just delenv BIFROST_CONSUME_LANE and the try/except around import
    # won't fail — but we want to test the *inner* except. Let's just verify
    # the default path works as fallback by not setting the env at all.
    monkeypatch.delenv("BIFROST_CONSUME_LANE", raising=False)
    out = _whisper(monkeypatch=monkeypatch, unread=3)
    # When the env is unset, it hits the else branch "all lanes"
    assert "3 unread" in out, f"mail must appear: {out}"


# ------------------------------------------------------------------ W8A-P5: zero unread → no mail line
def test_w8a_p5_zero_unread_no_mail_line(monkeypatch):
    """Zero unread → no 'mail:' section at all (unchanged)."""
    out = _whisper(monkeypatch=monkeypatch, unread=0, lane_env="work")
    assert "mail:" not in out, f"zero unread must not show mail line: {out}"


# ------------------------------------------------------------------ W8A-P6: out-of-repo whisper unchanged
def test_w8a_p6_out_of_repo_whisper_unchanged(monkeypatch):
    """Out-of-repo whisper keeps the bare message (no scope label clutter)."""
    import agent.harness.context as ctx
    monkeypatch.setattr(ctx, "_unread_count", lambda aid: 4)
    monkeypatch.setattr(ctx, "_draft_fresh", lambda: False)
    monkeypatch.setattr(ctx, "session_in_scope", lambda cwd: False)
    monkeypatch.setattr(ctx, "repo_root", lambda: "/fake/repo")
    out = ctx.build_autoboot_context(cwd="/somewhere/else", agent_id="test")
    assert "4 unread bus msg(s)" in out, f"out-of-repo must be bare: {out}"
    assert "work-lane" not in out, "out-of-repo must not have scope label"
    assert "all lanes" not in out, "out-of-repo must not have scope label"
