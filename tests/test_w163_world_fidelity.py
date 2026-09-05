"""W163 pins: a twin declares what it CANNOT do, before you find out by failing.

Two losses in one day, same shape, both discovered by hitting them:

  1. Suite failures in the twin traced to files prod carries UNCOMMITTED. A clone is
     faithful to HEAD; the source is not running HEAD.
  2. A five-lens model fanout died at once -- `.secrets/` is gitignored, so a clone carries
     ZERO credentials and every credentialed door is closed. Measured: prod 10 files,
     beta 0, alpha 0.

Neither was a bug. Both were a twin being SILENTLY INCAPABLE rather than wrong, and silence
is the expensive part: an hour goes into the work before the door refuses.

THE PLANES, and the point is that nobody enumerated them up front -- each was discovered by
a failure:

    code         arrives by git clone       -> faithful to HEAD, not to the source's tree
    memory       arrives by seeding         -> knowledge only; transport deliberately refused
    file plane   arrives by NEITHER         -> state/, session_logs/: gitignored, unseeded
    credentials  arrives by NEITHER         -> .secrets/: gitignored BY DESIGN, must stay so

WHAT THIS SLICE REFUSES TO DO. It does not copy secrets into twins. More copies of a
credential is a real cost, and a twin that can spend money is no longer cheap to discard --
that is a decision for the operator, not a convenience for the tool. The report says the
door is closed and why; it does not open it.

HONEST ABOUT ITS OWN LIMITS: a capability report that guesses is worse than none, because it
would be trusted. Each plane reports PRESENT, ABSENT or UNKNOWN, and UNKNOWN is a real state
-- not a hopeful PRESENT.
"""
import pytest

from core.coord import world_fidelity as F
from scripts import world_fidelity as CLI


def test_p1_every_declared_plane_is_reported_even_when_healthy():
    """Absence of output is indistinguishable from a probe that did not run."""
    rows = F.assess(root="/nowhere", secrets_count=0, state_count=0,
                    head_sha="abc", source_dirty=0)
    assert {r.plane for r in rows} >= {"code", "memory", "file", "credentials"}


def test_p2_a_missing_credential_plane_names_the_CONSEQUENCE_not_just_the_absence():
    """'.secrets: 0 files' is a fact. 'model asks and web search will refuse' is the answer."""
    rows = {r.plane: r for r in F.assess(root="/x", secrets_count=0, state_count=5,
                                         head_sha="abc", source_dirty=0)}
    cred = rows["credentials"]
    assert cred.status == "absent"
    assert "refus" in cred.consequence.lower() or "closed" in cred.consequence.lower()


def test_p3_a_present_credential_plane_says_so():
    rows = {r.plane: r for r in F.assess(root="/x", secrets_count=10, state_count=5,
                                         head_sha="abc", source_dirty=0)}
    assert rows["credentials"].status == "present"


def test_p4_uncommitted_work_in_the_SOURCE_is_reported_as_a_fidelity_limit():
    """The first loss. A twin cannot contain what the source never committed, so the
    source's dirty count is a property of the TWIN's fidelity, not of the source."""
    rows = {r.plane: r for r in F.assess(root="/x", secrets_count=1, state_count=5,
                                         head_sha="abc", source_dirty=21)}
    code = rows["code"]
    assert code.status == "partial"
    assert "21" in code.consequence


def test_p5_a_clean_source_makes_the_code_plane_fully_faithful():
    rows = {r.plane: r for r in F.assess(root="/x", secrets_count=1, state_count=5,
                                         head_sha="abc", source_dirty=0)}
    assert rows["code"].status == "present"


def test_p6_unknown_is_a_real_state_and_never_optimistic():
    """A probe that could not run must not report PRESENT. Guessing here would be trusted."""
    rows = {r.plane: r for r in F.assess(root="/x", secrets_count=None, state_count=None,
                                         head_sha=None, source_dirty=None)}
    for plane in ("code", "file", "credentials"):
        assert rows[plane].status == "unknown", plane
        assert rows[plane].consequence, "an unknown with no explanation teaches nothing"


def test_p7_the_render_leads_with_what_is_BROKEN():
    """Same law as the world diff: at-a-glance means ordering is the feature."""
    rows = F.assess(root="/x", secrets_count=0, state_count=5, head_sha="abc", source_dirty=0)
    out = F.render(rows, world="alpha")
    assert out.index("credentials") < out.index("memory")


def test_p8_the_report_never_offers_an_ACTIONABLE_way_to_copy_secrets():
    """The tool states the closed door; opening it is the operator's decision, because a
    twin that can spend money is no longer cheap to discard.

    Written as a property rather than a phrase match -- the first version of this pin
    asserted the literal string 'do not copy' while the render said 'does not copy', which
    tested my spelling instead of the behaviour."""
    rows = F.assess(root="/x", secrets_count=0, state_count=5, head_sha="abc", source_dirty=0)
    out = F.render(rows, world="alpha").lower()
    for actionable in ("cp ", "copy-item", "xcopy", "copy the", "copy your", ".secrets/*"):
        assert actionable not in out, f"the report handed over a way to copy secrets: {actionable!r}"
    assert "not copy" in out, "the refusal should be stated, not merely implied by omission"


def test_p9_a_MISSING_plane_is_absent_not_unknown():
    """Found by running it: `.secrets/` does not exist in a clone, and reporting that as
    "unknown -- could not read" understates a fact that was established. Unknown is for
    what could not be determined, never for what was."""
    rows = {r.plane: r for r in F.assess(root="/x", secrets_count=0, state_count=5,
                                         head_sha="abc", source_dirty=0)}
    assert rows["credentials"].status == "absent"
    assert "unknown" not in rows["credentials"].status


def test_p10_the_memory_row_is_MEASURED_from_the_seed_manifest_not_asserted():
    """The first cut hardcoded 'seeded knowledge plane' for every world -- a claim about
    history the renderer never checked. It was FALSE in prod, whose store is native and was
    seeded by nobody. The organ built to report honestly was responding without answering."""
    seeded = {r.plane: r for r in F.assess(root="/x", secrets_count=1, state_count=9,
                                           head_sha="abc", source_dirty=0,
                                           seeded_from="prod")}["memory"]
    assert seeded.status == "present" and "seeded from prod" in seeded.detail


def test_p11_the_source_reports_a_NATIVE_store_never_a_seeded_one():
    native = {r.plane: r for r in F.assess(root="/x", secrets_count=1, state_count=9,
                                           head_sha="abc", source_dirty=0,
                                           is_source=True)}["memory"]
    assert native.status == "present"
    assert "native" in native.detail and "seeded" not in native.detail


def test_p12_no_manifest_and_not_the_source_is_UNKNOWN_never_a_guess():
    """A checkout with no manifest that is not the source cannot say where its memory came
    from, and must not pick the flattering answer."""
    row = {r.plane: r for r in F.assess(root="/x", secrets_count=1, state_count=9,
                                        head_sha="abc", source_dirty=0)}["memory"]
    assert row.status == "unknown"
    assert "seeded from" not in row.detail


def test_p13_the_file_plane_asks_whether_the_TRACKED_files_are_here_not_how_many():
    """CORRECTS THIS MODULE'S OWN EARLIER CLAIM, by measurement.

    The first cut called the file plane PARTIAL from a raw entry count, so every twin read
    as having a fidelity gap. Measured 2026-08-14: everything load-bearing in state/ is
    TRACKED and therefore rides with the clone -- state/coord (task ledger, defer queue,
    suite baseline) and state/ci, all present in alpha. What a clone lacks is untracked
    residue: daemon pid/log files, one-off migration scratch, spend counters, ask records.

    And some of that residue MUST NOT ride: daemon-*.pid and state/asks are IDENTITY, the
    same class as the bus cursors the seed already refuses."""
    present = {r.plane: r for r in F.assess(root="/x", secrets_count=1, state_count=5,
                                            head_sha="abc", source_dirty=0,
                                            tracked_state_present=True)}["file"]
    assert present.status == "present"
    assert "must NOT ride" in present.consequence


def test_p14_a_MISSING_tracked_state_file_is_a_real_gap():
    missing = {r.plane: r for r in F.assess(root="/x", secrets_count=1, state_count=99,
                                            head_sha="abc", source_dirty=0,
                                            tracked_state_present=False)}["file"]
    assert missing.status == "partial"
    assert "ledger" in missing.consequence


def test_p15_an_unchecked_tracked_set_is_unknown_not_a_count_guess():
    """A big entry count must not be read as health when the tracked set was never checked."""
    row = {r.plane: r for r in F.assess(root="/x", secrets_count=1, state_count=99,
                                        head_sha="abc", source_dirty=0)}["file"]
    assert row.status == "unknown"


def test_p16_the_production_checkout_is_the_source_not_its_own_lag(monkeypatch, tmp_path):
    """Dirty production code is work in progress, never evidence that prod lags prod."""
    calls = []
    monkeypatch.setattr(
        CLI,
        "_git",
        lambda repo, *args: calls.append((repo, args)) or " M changed.py",
    )
    assert CLI._source_dirty("prod", tmp_path) == 0
    assert calls == [], "production source-drift must not inspect and compare the source to itself"
