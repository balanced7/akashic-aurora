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
